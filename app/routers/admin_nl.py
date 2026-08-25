"""Central de e-mail marketing do admin.

Fica separada do admin.py porque virou um módulo com vida própria: editor visual,
campanhas com estatísticas, base de contatos, temas e configurações.
"""
import datetime as dt
import json

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..auth import check_csrf, require_admin
from ..config import settings
from ..database import get_db
from ..models import (Campaign, EmailEvent, Lead, NewsletterSub, SiteSetting,
                      Theme)
from ..services import mailer
from ..services.images import save_upload, slugify

router = APIRouter(prefix="/admin/newsletter")

AUDIENCES = {
    "todos": "Todos os contatos",
    "assinantes": "Assinantes da newsletter",
    "leads": "Leads do formulário",
    "clientes": "Somente clientes",
}


def render(request: Request, nome: str, ctx: dict):
    from .admin import render_admin
    return render_admin(request, nome, ctx)


def smap_de(db: Session) -> dict:
    return {s.key: s.value for s in db.query(SiteSetting).all()}


def tema_padrao(db: Session) -> Theme | None:
    return (db.query(Theme).filter_by(is_default=True).first()
            or db.query(Theme).order_by(Theme.id).first())


def cores_da(camp: Campaign, db: Session) -> dict:
    tema = camp.theme or tema_padrao(db)
    return tema.cores() if tema else {}


def audience_recipients(db: Session, audience: str) -> list[dict]:
    """Resolve o público sem repetir endereço. Leads só entram com aceite."""
    out: dict[str, dict] = {}
    if audience in ("todos", "assinantes"):
        for sub in db.query(NewsletterSub).all():
            k = (sub.email or "").strip().lower()
            if k:
                out.setdefault(k, {"email": sub.email.strip(), "name": "", "kind": "assinante"})
    if audience in ("todos", "leads", "clientes"):
        q = db.query(Lead).filter(Lead.consent.is_(True))
        if audience == "clientes":
            q = q.filter(Lead.status == "cliente")
        for lead in q.all():
            k = (lead.email or "").strip().lower()
            if not k:
                continue
            if k in out:
                out[k]["name"] = out[k]["name"] or lead.name
            else:
                out[k] = {"email": lead.email.strip(), "name": lead.name, "kind": lead.status}
    return list(out.values())


def payload_de(camp: Campaign, db: Session) -> dict:
    from ..services.campanha import payload
    return payload(camp, db, settings.base_url)


def stats_de(db: Session, camp: Campaign) -> dict:
    """Números da campanha. Abertura é indicativa; clique e descadastro são exatos."""
    ev = db.query(EmailEvent).filter_by(campaign_id=camp.id)
    enviados = ev.filter_by(kind="enviado").count() or camp.sent_count
    abriu = len({e.email for e in ev.filter_by(kind="abriu").all()})
    clicou = len({e.email for e in ev.filter_by(kind="clicou").all()})
    falhou = ev.filter_by(kind="falhou").count() or camp.fail_count
    pct = lambda n: round(n * 100 / enviados) if enviados else 0  # noqa: E731
    return {"enviados": enviados, "abriu": abriu, "clicou": clicou, "falhou": falhou,
            "pct_abriu": pct(abriu), "pct_clicou": pct(clicou), "pct_falhou": pct(falhou)}


# ---------- 1. Central ----------

@router.get("")
async def hub(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    smap = smap_de(db)
    camps = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    enviadas = [c for c in camps if c.status == "enviado"]
    total_ev = db.query(EmailEvent)
    return render(request, "admin/nl_hub.html", {
        "camps": camps,
        "resumo": {
            "contatos": len(audience_recipients(db, "todos")),
            "assinantes": db.query(NewsletterSub).count(),
            "leads": db.query(Lead).count(),
            "clientes": db.query(Lead).filter_by(status="cliente").count(),
            "campanhas": len(camps),
            "enviadas": len(enviadas),
            "aberturas": total_ev.filter_by(kind="abriu").count(),
            "cliques": total_ev.filter_by(kind="clicou").count(),
        },
        "smtp_ok": mailer.smtp_ready(smap),
        "welcome": next((c for c in camps if c.is_welcome), None),
    })


# ---------- 2. Editor visual ----------

@router.get("/nova")
async def nova(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    return render(request, "admin/nl_editor.html", {
        "camp": None, "audiences": AUDIENCES, "blocos": mailer.BLOCOS,
        "temas": db.query(Theme).order_by(Theme.name).all(),
        "counts": {k: len(audience_recipients(db, k)) for k in AUDIENCES},
        "blocos_iniciais": [], "blocos_json": "[]",
    })


@router.get("/editar/{camp_id}")
async def editar(camp_id: int, request: Request, db: Session = Depends(get_db),
                 _=Depends(require_admin)):
    camp = db.get(Campaign, camp_id)
    if not camp:
        return RedirectResponse("/admin/newsletter", status_code=303)
    blocos = camp.blocks or ([{"t": "texto", "v": camp.body}] if camp.body else [])
    return render(request, "admin/nl_editor.html", {
        "camp": camp, "audiences": AUDIENCES, "blocos": mailer.BLOCOS,
        "temas": db.query(Theme).order_by(Theme.name).all(),
        "counts": {k: len(audience_recipients(db, k)) for k in AUDIENCES},
        # o objeto, não o JSON pronto: o filtro tojson escapa "</script>", que
        # em texto de campanha fechava a tag no meio e derrubava o editor
        "blocos_iniciais": blocos,
        # e o mesmo conteúdo em texto, para o campo escondido nascer com a
        # campanha que já existe: sem isso, salvar com o JavaScript fora do
        # ar mandava vazio e o except zerava os blocos sem avisar
        "blocos_json": json.dumps(blocos, ensure_ascii=False),
        "stats": stats_de(db, camp),
    })


@router.post("/salvar")
async def salvar(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    cid = str(form.get("id", "")).strip()
    camp = db.get(Campaign, int(cid)) if cid.isdigit() else None
    if camp is None:
        camp = Campaign(subject="")
        db.add(camp)

    camp.subject = str(form.get("subject", "")).strip()[:200]
    camp.preheader = str(form.get("preheader", "")).strip()[:200]
    try:
        camp.blocks = json.loads(str(form.get("blocks", "[]")))
    except Exception:
        camp.blocks = []
    aud = str(form.get("audience", "todos"))
    camp.audience = aud if aud in AUDIENCES else "todos"

    tid = str(form.get("theme_id", "")).strip()
    camp.theme_id = int(tid) if tid.isdigit() else None

    quer_welcome = form.get("is_welcome") == "on"
    if quer_welcome:
        for outra in db.query(Campaign).filter(Campaign.is_welcome.is_(True)).all():
            outra.is_welcome = False
    camp.is_welcome = quer_welcome

    # Duck typing, não isinstance: request.form() é sempre parseado pelo
    # Starlette, que constrói starlette.datastructures.UploadFile — nunca
    # fastapi.UploadFile, que é SUBCLASSE dela. isinstance(arquivo, UploadFile)
    # com a classe do FastAPI dava False sempre, e a imagem da campanha era
    # descartada em silêncio (o irmão do Crítico 1 da Tarefa 5 do Nodal).
    img: UploadFile | None = form.get("image")  # type: ignore[assignment]
    if getattr(img, "filename", ""):
        _, rel, thumb = await save_upload(img, "newsletter")
        camp.image = thumb or rel
    if form.get("remove_image"):
        camp.image = ""

    db.commit()
    return RedirectResponse(f"/admin/newsletter/editar/{camp.id}?salva=1", status_code=303)


@router.post("/upload")
async def upload_bloco(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Upload de imagem de dentro do editor, sem sair da página."""
    from fastapi.responses import JSONResponse
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    # mesmo duck typing do ponto acima, mesmo motivo: isinstance com o
    # UploadFile do FastAPI nunca bate no que request.form() devolve, e a
    # rota respondia sempre "sem arquivo" a qualquer envio real
    arq: UploadFile | None = form.get("file")  # type: ignore[assignment]
    if not getattr(arq, "filename", ""):
        return JSONResponse({"erro": "sem arquivo"}, status_code=400)
    kind, rel, thumb = await save_upload(arq, "newsletter")
    if kind != "image":
        return JSONResponse({"erro": "precisa ser imagem"}, status_code=400)
    return JSONResponse({"ok": True, "src": thumb or rel,
                         "url": f"/media/{thumb or rel}"})


@router.get("/preview/{camp_id}")
async def preview(camp_id: int, request: Request, db: Session = Depends(get_db),
                  _=Depends(require_admin)):
    camp = db.get(Campaign, camp_id)
    if not camp:
        return RedirectResponse("/admin/newsletter", status_code=303)
    html = mailer.campaign_email_html(
        payload_de(camp, db), settings.base_url, "#", "", smap_de(db))
    return HTMLResponse(html)


@router.post("/preview-ao-vivo")
async def preview_ao_vivo(request: Request, db: Session = Depends(get_db),
                          _=Depends(require_admin)):
    """Renderiza o e-mail a partir dos blocos que estão na tela, sem salvar."""
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    try:
        blocos = json.loads(str(form.get("blocks", "[]")))
    except Exception:
        blocos = []
    tid = str(form.get("theme_id", "")).strip()
    tema = db.get(Theme, int(tid)) if tid.isdigit() else tema_padrao(db)
    cores = tema.cores() if tema else {}
    payload = {
        "subject": str(form.get("subject", "")), "preheader": str(form.get("preheader", "")),
        "body_html": mailer.blocks_to_html(blocos, cores, settings.base_url),
        "image": str(form.get("image", "")), "cta_label": "", "cta_url": "",
        "cores": cores,
        "rotulo": "Newsletter / Boas-vindas" if form.get("is_welcome") == "on" else "Newsletter",
    }
    html = mailer.campaign_email_html(payload, settings.base_url, "#", "", smap_de(db))
    return HTMLResponse(html)


# ---------- 3. Campanhas ----------

@router.get("/campanhas")
async def campanhas(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                    ver: int = 0):
    todas = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    atual = db.get(Campaign, ver) if ver else (todas[0] if todas else None)
    detalhe = None
    if atual:
        ev = db.query(EmailEvent).filter_by(campaign_id=atual.id)
        cliques: dict[str, int] = {}
        for e in ev.filter_by(kind="clicou").all():
            cliques[e.detail] = cliques.get(e.detail, 0) + 1
        detalhe = {
            "stats": stats_de(db, atual),
            "cliques": sorted(cliques.items(), key=lambda x: -x[1])[:8],
            "linha_do_tempo": (ev.order_by(EmailEvent.at.desc()).limit(25).all()),
        }
    return render(request, "admin/nl_campanhas.html", {
        "camps": todas, "atual": atual, "d": detalhe, "audiences": AUDIENCES,
    })


@router.post("/{camp_id}/enviar")
async def enviar(camp_id: int, request: Request, db: Session = Depends(get_db),
                 _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    camp = db.get(Campaign, camp_id)
    if not camp:
        return RedirectResponse("/admin/newsletter/campanhas", status_code=303)

    smap = smap_de(db)
    payload = payload_de(camp, db)
    teste = str(form.get("test_email", "")).strip()

    def registrar(email: str, kind: str, detail: str) -> None:
        db.add(EmailEvent(campaign_id=camp.id, email=email, kind=kind, detail=detail))

    if teste:
        enviados, _f, erro = mailer.send_campaign(
            smap, payload, [{"email": teste, "name": ""}], settings.base_url, settings.secret_key)
        flag = "teste=1" if enviados else f"erro={erro or 'falhou'}"
        return RedirectResponse(f"/admin/newsletter/editar/{camp.id}?{flag}", status_code=303)

    destinos = audience_recipients(db, camp.audience)
    if not destinos:
        return RedirectResponse(f"/admin/newsletter/editar/{camp.id}?erro=Sem+destinatários",
                                status_code=303)
    enviados, falhas, erro = mailer.send_campaign(
        smap, payload, destinos, settings.base_url, settings.secret_key, registrar)
    camp.sent_count, camp.fail_count, camp.error = enviados, falhas, erro
    camp.status = "enviado" if enviados else "rascunho"
    camp.sent_at = dt.datetime.now(dt.timezone.utc) if enviados else None
    db.commit()
    return RedirectResponse(f"/admin/newsletter/campanhas?ver={camp.id}&enviado={enviados}",
                            status_code=303)


@router.post("/{camp_id}/excluir")
async def excluir(camp_id: int, request: Request, db: Session = Depends(get_db),
                  _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    camp = db.get(Campaign, camp_id)
    if camp:
        db.delete(camp)
        db.commit()
    return RedirectResponse("/admin/newsletter/campanhas", status_code=303)


@router.post("/{camp_id}/duplicar")
async def duplicar(camp_id: int, request: Request, db: Session = Depends(get_db),
                   _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    o = db.get(Campaign, camp_id)
    if not o:
        return RedirectResponse("/admin/newsletter/campanhas", status_code=303)
    nova = Campaign(subject=f"{o.subject} (cópia)", preheader=o.preheader, body=o.body,
                    blocks=o.blocks, image=o.image, cta_label=o.cta_label, cta_url=o.cta_url,
                    audience=o.audience, theme_id=o.theme_id, status="rascunho")
    db.add(nova)
    db.commit()
    return RedirectResponse(f"/admin/newsletter/editar/{nova.id}", status_code=303)


# ---------- 4. Contatos ----------

@router.get("/leads")
async def leads(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                aba: str = "leads"):
    todos_leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    subs = db.query(NewsletterSub).order_by(NewsletterSub.created_at.desc()).all()
    emails_lead = {(l.email or "").lower() for l in todos_leads}
    return render(request, "admin/nl_leads.html", {
        "aba": aba if aba in ("leads", "assinantes", "clientes") else "leads",
        "leads": [x for x in todos_leads if x.status != "cliente"],
        "clientes": [x for x in todos_leads if x.status == "cliente"],
        "subs": subs,
        "so_newsletter": [s for s in subs if (s.email or "").lower() not in emails_lead],
        "total_leads": len(todos_leads),
    })


@router.post("/leads/{lead_id}/status")
async def lead_status(lead_id: int, request: Request, db: Session = Depends(get_db),
                      _=Depends(require_admin), csrf: str = Form(""), status: str = Form(""),
                      aba: str = Form("leads")):
    check_csrf(request, csrf)
    lead = db.get(Lead, lead_id)
    if lead and status in ("novo", "contatado", "cliente"):
        lead.status = status
        db.commit()
    return RedirectResponse(f"/admin/newsletter/leads?aba={aba}", status_code=303)


@router.post("/subs/{sub_id}/excluir")
async def sub_excluir(sub_id: int, request: Request, db: Session = Depends(get_db),
                      _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    sub = db.get(NewsletterSub, sub_id)
    if sub:
        db.delete(sub)
        db.commit()
    return RedirectResponse("/admin/newsletter/leads?aba=assinantes", status_code=303)


# ---------- 5. Temas ----------

CAMPOS_TEMA = ("pagina", "card", "ink", "body", "muted", "line", "destaque")


@router.get("/temas")
async def temas(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    return render(request, "admin/nl_temas.html", {
        "temas": db.query(Theme).order_by(Theme.is_default.desc(), Theme.name).all(),
    })


@router.post("/temas/salvar")
async def tema_salvar(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    tid = str(form.get("id", "")).strip()
    tema = db.get(Theme, int(tid)) if tid.isdigit() else None
    if tema is None:
        tema = Theme(name="", slug="")
        db.add(tema)
    tema.name = str(form.get("name", "")).strip()[:80] or "Sem nome"
    base = slugify(tema.name)
    slug, i = base, 2
    while db.query(Theme).filter(Theme.slug == slug, Theme.id != tema.id).first():
        slug, i = f"{base}-{i}", i + 1
    tema.slug = slug
    for campo in CAMPOS_TEMA:
        valor = str(form.get(campo, "")).strip()
        if valor.startswith("#") and len(valor) in (4, 7):
            setattr(tema, campo, valor)
    if form.get("is_default") == "on":
        for outro in db.query(Theme).filter(Theme.is_default.is_(True)).all():
            outro.is_default = False
        tema.is_default = True
    db.commit()
    return RedirectResponse("/admin/newsletter/temas?salvo=1", status_code=303)


@router.post("/temas/{tema_id}/excluir")
async def tema_excluir(tema_id: int, request: Request, db: Session = Depends(get_db),
                       _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    tema = db.get(Theme, tema_id)
    if tema:
        db.delete(tema)
        db.commit()
    return RedirectResponse("/admin/newsletter/temas", status_code=303)


@router.get("/temas/{tema_id}/preview")
async def tema_preview(tema_id: int, request: Request, db: Session = Depends(get_db),
                       _=Depends(require_admin)):
    tema = db.get(Theme, tema_id)
    cores = tema.cores() if tema else {}
    exemplo = [
        {"t": "texto", "v": "Assim fica o corpo do e-mail neste tema, com **negrito** no meio."},
        {"t": "destaque", "v": "Uma faixa de destaque\npara separar o que importa"},
        {"t": "lista", "v": ["Primeiro item;", "Segundo item;", "Terceiro item."]},
        {"t": "botao", "v": "Botão de ação", "url": settings.base_url},
    ]
    payload = {"subject": tema.name if tema else "Tema", "preheader": "",
               "body_html": mailer.blocks_to_html(exemplo, cores, settings.base_url),
               "image": "", "cta_label": "", "cta_url": "", "cores": cores}
    return HTMLResponse(mailer.campaign_email_html(payload, settings.base_url, "#", "", smap_de(db)))


# ---------- 6. Configurações ----------

CHAVES_NL = ("smtp_host", "smtp_port", "smtp_user", "smtp_from", "lead_email")
# smtp_password fica de fora: é o mesmo segredo de /admin/settings (ver
# SEGREDOS_ECOADOS em admin.py) e "campo vazio" aqui também não pode apagar a
# senha já guardada — mesma semântica, mesma tela repetida (ver config_salvar).


@router.get("/config")
async def config(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    from .admin import indicador_segredo
    smap = smap_de(db)
    return render(request, "admin/nl_config.html", {
        "s": smap, "smtp_ok": mailer.smtp_ready(smap),
        "assinantes": db.query(NewsletterSub).count(),
        "smtp_password_ind": indicador_segredo(smap.get("smtp_password")),
    })


@router.post("/config")
async def config_salvar(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    from .admin import set_setting
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    for chave in CHAVES_NL:
        if chave in form:
            set_setting(db, chave, str(form.get(chave, "")).strip())
    # smtp_password: mesmo padrão de /admin/settings — vazio mantém a senha
    # atual, a caixa "remover" apaga.
    if form.get("smtp_password_remover") == "on":
        set_setting(db, "smtp_password", "")
    else:
        senha = str(form.get("smtp_password", "")).strip()
        if senha:
            set_setting(db, "smtp_password", senha)
    db.commit()
    return RedirectResponse("/admin/newsletter/config?salvo=1", status_code=303)


@router.post("/config/testar")
async def config_testar(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Teste de e-mail: confere a conexão e manda uma mensagem real."""
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    para = str(form.get("para", "")).strip()
    smap = smap_de(db)
    if not para:
        return RedirectResponse("/admin/newsletter/config?erro=Informe+um+e-mail", status_code=303)

    exemplo = [
        {"t": "texto", "v": "Se você está lendo isto, o SMTP do site está funcionando."},
        {"t": "lista", "v": ["Conexão estabelecida;", "Autenticação aceita;", "Entrega concluída."]},
        {"t": "botao", "v": "Abrir o painel", "url": f"{settings.base_url}/admin"},
    ]
    tema = tema_padrao(db)
    cores = tema.cores() if tema else {}
    payload = {"subject": "Teste de envio", "preheader": "Conferindo o SMTP do site",
               "body_html": mailer.blocks_to_html(exemplo, cores, settings.base_url),
               "image": "", "cta_label": "", "cta_url": "", "cores": cores,
               "rotulo": "Teste"}
    enviados, _f, erro = mailer.send_campaign(
        smap, payload, [{"email": para, "name": ""}], settings.base_url, settings.secret_key)
    if enviados:
        return RedirectResponse("/admin/newsletter/config?teste=1", status_code=303)
    return RedirectResponse(f"/admin/newsletter/config?erro={erro or 'Falhou o envio'}",
                            status_code=303)
