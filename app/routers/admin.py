import datetime as dt
import json
import secrets
from itertools import zip_longest

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     UploadFile)
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from ..auth import (check_csrf, csrf_token, current_user, hash_password,
                    login_allowed, register_attempt, require_admin,
                    verify_password)
from ..config import settings
from ..database import get_db
from ..services.atividade import registrar
from ..models import (Campaign, Case, Category, Client, ContactMessage, Lead,
                      LinkedInPost, MediaItem, NewsletterSub, Profile,
                      SiteSetting, Tag, User)
from ..services import blocos as blocos_svc
from ..services import seo
from ..services import instagram as ig
from ..services import mailer
from ..services.mailer import smtp_ready
from ..services.images import (apagar_arquivo_exato, delete_media_files,
                               save_upload, slugify)
from ..services.oembed import resolve_embed

router = APIRouter(prefix="/admin")

# Limite de fotos por prêmio (item novo, 19/08). Seis enche uma linha e meia
# da grade de 4 colunas do Sobre (4 + 2) — dá para mostrar o suficiente de um
# prêmio sem a seção virar um álbum de fotos, e mantém o disco/upload
# limitado por prêmio sem precisar negociar um número com o dono.
AWARD_IMAGES_MAX = 6


def render_admin(request: Request, name: str, ctx: dict | None = None):
    # Esta função monta o próprio contexto e não passa pelo render() do main,
    # então o sino precisa ser servido aqui também. Sem isto ele aparecia vazio
    # em metade do painel, e um sino que às vezes mente é pior que nenhum.
    from ..main import _avisos_do_painel, _trilha_do_painel, templates
    base = {"request": request, "csrf": csrf_token(request), "user": current_user(request)}
    base.update(_avisos_do_painel())
    base["trilha"] = _trilha_do_painel(request)
    base.update(ctx or {})
    return templates.TemplateResponse(request, name, base)


def settings_map(db: Session) -> dict:
    return {s.key: s.value for s in db.query(SiteSetting).all()}


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(SiteSetting, key)
    if row:
        row.value = value
    else:
        db.add(SiteSetting(key=key, value=value))


def indicador_segredo(valor: str | None) -> dict:
    """Para segredos que não podem voltar pro HTML (ver SEGREDOS_ECOADOS):
    mesmo padrão de cf_stream_key_pem/anthropic_api_key (/admin/lab) — indicador
    "configurado" + últimos 4 caracteres, nunca o valor inteiro."""
    v = valor or ""
    return {"configurado": bool(v), "final4": v[-4:] if len(v) >= 4 else ""}


# ---------- Login ----------

@router.get("/login")
async def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/admin", status_code=302)
    return render_admin(request, "admin/login.html", {"error": ""})


def _abrir_sessao(request: Request, user: User, nxt: str):
    request.session.clear()
    request.session["user"] = user.username
    csrf_token(request)
    destino = nxt if nxt.startswith("/admin") else "/admin"
    return RedirectResponse(destino, status_code=303)


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    if not login_allowed(request):
        return render_admin(request, "admin/login.html",
                            {"error": "Muitas tentativas. Aguarde 15 minutos."})
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    nxt = str(form.get("next", "")) or "/admin"

    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(user.password_hash, password):
        register_attempt(request)
        return render_admin(request, "admin/login.html", {"error": "Usuário ou senha inválidos."})

    if not user.totp_ativo:
        return _abrir_sessao(request, user, nxt)

    # senha certa não abre nada: guarda só a intenção, com prazo, e pede o código.
    # A sessão de verdade só nasce depois do segundo fator.
    request.session.clear()
    request.session["pendente"] = user.username
    request.session["pendente_ate"] = int(dt.datetime.now(dt.timezone.utc).timestamp()) + 300
    request.session["pendente_next"] = nxt
    csrf_token(request)
    return RedirectResponse("/admin/login/codigo", status_code=303)


@router.get("/login/codigo")
async def login_codigo_page(request: Request):
    if not request.session.get("pendente"):
        return RedirectResponse("/admin/login", status_code=303)
    return render_admin(request, "admin/login_2fa.html", {"error": ""})


@router.post("/login/codigo")
async def login_codigo(request: Request, db: Session = Depends(get_db)):
    from ..services import totp as t2
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))

    pendente = request.session.get("pendente")
    prazo = request.session.get("pendente_ate", 0)
    agora = int(dt.datetime.now(dt.timezone.utc).timestamp())
    if not pendente or agora > prazo:
        request.session.clear()
        return RedirectResponse("/admin/login?expirou=1", status_code=303)

    if not login_allowed(request):
        return render_admin(request, "admin/login_2fa.html",
                            {"error": "Muitas tentativas. Aguarde 15 minutos."})

    user = db.query(User).filter_by(username=pendente).first()
    if not user:
        request.session.clear()
        return RedirectResponse("/admin/login", status_code=303)

    codigo = str(form.get("codigo", "")).strip()
    nxt = request.session.get("pendente_next", "/admin")

    if t2.confere(user.totp_secret, codigo):
        return _abrir_sessao(request, user, nxt)

    # código de recuperação: vale uma vez e some da lista
    usado = t2.confere_recuperacao(codigo, list(user.totp_backup or []))
    if usado:
        user.totp_backup = [h for h in (user.totp_backup or []) if h != usado]
        db.commit()
        return _abrir_sessao(request, user, nxt)

    register_attempt(request)
    return render_admin(request, "admin/login_2fa.html",
                        {"error": "Código inválido. Confira o aplicativo e tente de novo."})


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)


# ---------- Dashboard ----------

def _publico_total(db: Session) -> list:
    from .admin_nl import audience_recipients
    return audience_recipients(db, "todos")


def _votes_map(db: Session, key: str) -> dict:
    row = db.get(SiteSetting, key)
    try:
        return json.loads(row.value) if row else {}
    except Exception:
        return {}


@router.get("")
async def dashboard(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    from .public import all_brands
    cases = (db.query(Case).options(joinedload(Case.category))
             .order_by(Case.sort, Case.created_at.desc()).all())
    published = [c for c in cases if c.published]
    unread = db.query(ContactMessage).filter_by(read=False).count()
    msgs = (db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(3).all())
    case_votes = _votes_map(db, "case_votes")
    tip_votes = _votes_map(db, "tip_votes")
    # o painel enxerga também as que não têm logotipo: é aqui que se resolve
    brands = all_brands(db, com_logo=False)
    no_logo = [b for b in brands if not b["logo"]]
    smap = settings_map(db)

    # pendências: o que falta para o site rodar 100%
    pending = []
    if not (smap.get("ig_user_id") and smap.get("ig_access_token")):
        pending.append(("Conectar o Instagram (feed real + publicação automática)", "/admin/settings"))
    else:
        try:
            est = json.loads(smap.get("ig_token_status") or "{}")
        except Exception:
            est = {}
        if est and not est.get("ok"):
            pending.append(("Token do Instagram com problema: o feed parou", "/admin/settings"))
        elif est.get("ok") and not est.get("permanente"):
            pending.append((f"Token do Instagram vence em {est.get('dias', '?')} dia(s): "
                            "verifique para trocar pelo permanente", "/admin/settings"))
    if not smtp_ready(smap):
        pending.append(("Configurar o SMTP (aviso de lead e envio da newsletter)", "/admin/settings"))
    if no_logo:
        pending.append((f"{len(no_logo)} marca{'s' if len(no_logo) > 1 else ''} sem logotipo SVG", "/admin/brands"))
    if not published:
        pending.append(("Publicar o primeiro case", "/admin/cases/new"))

    return render_admin(request, "admin/dashboard.html", {
        "stats": {
            "published": len(published), "drafts": len(cases) - len(published),
            "likes": sum(v.get("up", 0) for v in case_votes.values()),
            "dislikes": sum(v.get("down", 0) for v in case_votes.values()),
            "tips_up": sum(v.get("up", 0) for v in tip_votes.values()),
            "tips_down": sum(v.get("down", 0) for v in tip_votes.values()),
            "unread": unread,
            "messages": db.query(ContactMessage).count(),
            "subs": db.query(NewsletterSub).count(),
            "leads": db.query(Lead).count(),
            "leads_new": db.query(Lead).filter_by(status="novo").count(),
            "li_posts": db.query(LinkedInPost).count(),
            "brands": len(brands), "brands_no_logo": len(no_logo),
            "campaigns": db.query(Campaign).count(),
            "campaigns_sent": db.query(Campaign).filter_by(status="enviado").count(),
            "audience": len(_publico_total(db)),
        },
        "recent_cases": cases[:5], "recent_msgs": msgs,
        "case_votes": case_votes, "pending": pending, "unread": unread,
    })


# A lista de cases mora na central (routers/admin_cases.py), que é montada antes
# deste router. A rota antiga que existia aqui nunca mais era alcançada, e manter
# duas telas de lista competindo pelo mesmo endereço só criava divergência.


@router.get("/leads")
async def leads_page(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return render_admin(request, "admin/leads.html", {
        "leads": leads, "smtp_ok": bool(settings_map(db).get("smtp_host")),
    })


@router.post("/leads/{lead_id}/status")
async def lead_status(lead_id: int, request: Request, db: Session = Depends(get_db),
                      _=Depends(require_admin), csrf: str = Form(""), status: str = Form("")):
    check_csrf(request, csrf)
    lead = db.get(Lead, lead_id)
    if lead and status in ("novo", "contatado", "cliente"):
        lead.status = status
        db.commit()
    return RedirectResponse("/admin/leads?ok=1", status_code=303)


@router.post("/leads/{lead_id}/delete")
async def lead_delete(lead_id: int, request: Request, db: Session = Depends(get_db),
                      _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    lead = db.get(Lead, lead_id)
    if lead:
        db.delete(lead)
        db.commit()
    return RedirectResponse("/admin/leads?ok=1", status_code=303)


# ---------- Marcas & Clientes ----------

BRAND_LOGO_MAX = 400_000  # 400KB de SVG é mais que suficiente


def _brands_ctx(db: Session) -> dict:
    from .public import all_brands
    profile_names = set(db.get(Profile, 1).data.get("clients", []) if db.get(Profile, 1) else [])
    counts: dict[str, int] = {}
    for c in db.query(Case).filter(Case.published.is_(True)).all():
        if c.client:
            counts[slugify(c.client)] = counts.get(slugify(c.client), 0) + 1
    # `all_brands` já devolve em ordem alfabética ignorando acento; reordenar
    # aqui por `.lower()` só reintroduzia a diferença entre "São" e "Sao".
    # `com_logo=False`: sem logotipo a marca não vai para o site, mas precisa
    # aparecer aqui — senão não há por onde enviar o arquivo que falta.
    brands = all_brands(db, com_logo=False)
    for b in brands:
        b["count"] = counts.get(b["slug"], 0)
        b["from_profile"] = b["name"] in profile_names
    return {"brands": brands}


@router.get("/brands")
async def brands_page(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    return render_admin(request, "admin/brands.html", _brands_ctx(db))


def _save_profile_clients(db: Session, clients: list[str]) -> None:
    prof = db.get(Profile, 1)
    if not prof:
        return
    data = dict(prof.data or {})
    data["clients"] = clients
    prof.data = data
    db.commit()


@router.post("/brands/home")
async def brand_home(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                     csrf: str = Form(""), slug: str = Form("")):
    """Liga/desliga a marca no trilho da primeira dobra da home.

    Guardamos quem está FORA, não quem está dentro: marca nova entra aparecendo,
    que é o que se espera de quem acabou de cadastrar um cliente.
    """
    check_csrf(request, csrf)
    prof = db.get(Profile, 1)
    if prof and slug:
        data = dict(prof.data or {})
        fora = set(data.get("home_ocultos", []))
        fora.symmetric_difference_update({slug})
        data["home_ocultos"] = sorted(fora)
        prof.data = data
        db.commit()
    return RedirectResponse("/admin/brands?ok=1", status_code=303)


@router.post("/brands/add")
async def brand_add(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                    csrf: str = Form(""), name: str = Form("")):
    check_csrf(request, csrf)
    name = name.strip()[:120]
    prof = db.get(Profile, 1)
    clients = list((prof.data or {}).get("clients", [])) if prof else []
    if name and name not in clients:
        clients.append(name)
        _save_profile_clients(db, clients)
    return RedirectResponse("/admin/brands?ok=1", status_code=303)


@router.post("/brands/remove")
async def brand_remove(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                       csrf: str = Form(""), name: str = Form("")):
    check_csrf(request, csrf)
    prof = db.get(Profile, 1)
    clients = list((prof.data or {}).get("clients", [])) if prof else []
    if name in clients:
        clients.remove(name)
        _save_profile_clients(db, clients)
    return RedirectResponse("/admin/brands?ok=1", status_code=303)


def _brand_logo_path(name: str):
    """Onde um logo enviado pelo painel é gravado.

    Em `data/uploads`, e não dentro do código: o deploy roda `rsync --delete` e
    limparia tudo que estivesse na árvore da aplicação. Já aconteceu — um logo
    enviado aqui sumia no deploy seguinte, sem aviso. `data/` fica de fora do
    rsync e entra no backup diário.
    """
    from ..config import settings
    slug = slugify(name)
    if not slug:
        return None
    return settings.upload_dir / "clients" / f"{slug}.svg"


@router.post("/brands/logo")
async def brand_logo_upload(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                            csrf: str = Form(""), name: str = Form(""), file: UploadFile = File(...)):
    check_csrf(request, csrf)
    path = _brand_logo_path(name)
    data = await file.read()
    text = data.decode("utf-8", errors="ignore")
    lower = text.lower()
    ok = (path is not None and 0 < len(data) <= BRAND_LOGO_MAX
          and "<svg" in lower[:2000] and "<script" not in lower and "javascript:" not in lower)
    if ok:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        # Exportador de marca costuma entregar uma prancheta quadrada com o
        # desenho pequeno no meio. Sem aparar isso, o logo entra na fileira
        # menor que os vizinhos por mais que a escala óptica esteja certa.
        from ..services.logos import normalizar
        normalizar(path)
        return RedirectResponse("/admin/brands?ok=1", status_code=303)
    return RedirectResponse("/admin/brands?logo_err=1", status_code=303)


@router.post("/brands/logo/delete")
async def brand_logo_delete(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                            csrf: str = Form(""), name: str = Form("")):
    check_csrf(request, csrf)
    path = _brand_logo_path(name)
    if path and path.exists():
        path.unlink()
    return RedirectResponse("/admin/brands?ok=1", status_code=303)


# ---------- Cases ----------

def case_form_ctx(db: Session, case: Case | None) -> dict:
    # A página do case sai daqui já em JSON, no formato que o compositor usa.
    # Ler o estado inicial de um <script type="application/json"> evita escapar
    # aspas dentro de atributo, que é onde esse tipo de campo costuma quebrar.
    pagina = [{
        "kind": m.kind,
        "src": m.src,
        "thumb": m.thumb,
        "caption": m.caption_pt,
        "layout": m.layout,
        "meta": m.meta or {},
    } for m in (case.media if case else [])]

    from ..services.programas import PROGRAMAS
    return {
        "programas_lista": list(PROGRAMAS.items()),
        "case": case,
        "categories": db.query(Category).order_by(Category.sort).all(),
        "clientes": db.query(Client).order_by(Client.name).all(),
        # devolve com "#" porque é assim que ele digita e espera reler
        "tags_str": ", ".join("#" + t.name for t in case.tags) if case else "",
        # o formulário muda de cara conforme a categoria, e precisa saber quais
        # delas são do tipo "sites" para decidir isso já no primeiro desenho
        "cats_sites": [c.id for c in db.query(Category).filter_by(kind="sites").all()],
        "catalogo": blocos_svc.CATALOGO,
        # o objeto, não o JSON pronto: quem serializa é o filtro tojson do
        # Jinja, que escapa "</script>" — texto de case que fale de HTML
        # fechava a tag no meio e derrubava o editor
        "blocos_iniciais": pagina,
        # o mesmo conteúdo em texto, para o campo escondido nascer com a
        # página que já existe. Se o JavaScript não rodar, o formulário
        # devolve o que recebeu; antes ele mandava "[]" e o salvamento
        # apagava a página inteira do case, com os arquivos junto
        "blocos_json": json.dumps(pagina, ensure_ascii=False),
        # Capa gravada no banco que não existe mais no disco.
        #
        # Não é hipótese: o defeito que apagava a capa no instante do salvamento
        # deixou cases apontando para arquivo que sumiu, e a tela mostrava só o
        # ícone de imagem quebrada do navegador — que a pessoa lê como "a
        # internet falhou", não como "este arquivo não existe".
        #
        # Decidido aqui, e não por `onerror` no script, porque precisa valer com
        # JavaScript desligado: é a diferença entre saber e adivinhar.
        "capa_sumiu": bool(
            case and case.cover_image
            and not (settings.upload_dir / case.cover_image).is_file()),
    }


async def apply_case_form(request: Request, db: Session, case: Case) -> None:
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))

    # Só português. O inglês do site fica por conta da tradução, e manter dois
    # campos por texto fazia o cadastro custar o dobro para render metade: na
    # prática o _en ficava vazio ou repetia o português.
    for name in ("title_pt", "subtitle_pt", "year", "body_pt"):
        setattr(case, name, str(form.get(name, "")).strip())

    # Cor de destaque saiu do cadastro: o site é monocromático por decisão, e um
    # campo que injeta cor num projeto sem cor só existia para ser esquecido.
    case.accent = ""

    # Papel e entregas saíram: isso é o que a categoria já diz.
    case.role_pt = case.role_en = ""

    cat_id = str(form.get("category_id", ""))
    case.category_id = int(cat_id) if cat_id.isdigit() else None

    # Cliente vem da tabela. O campo de texto continua preenchido a partir do
    # relacionado, porque muita coisa no site ainda lê case.client — assim os
    # dois nunca divergem, e quem renomear o cliente renomeia em todo lugar.
    # Cliente novo criado no próprio formulário do case. Vem antes de ler o
    # client_id porque, se a pessoa digitou um nome aqui, é esse que ela quer.
    nome_novo = str(form.get("cliente_novo", "")).strip()
    if nome_novo:
        chave = slugify(nome_novo)
        existente = db.query(Client).filter_by(slug=chave).first()
        if existente:
            novo_cli = existente
        else:
            novo_cli = Client(slug=chave, name=nome_novo,
                              site=str(form.get("cliente_novo_site", "")).strip())
            db.add(novo_cli)
            db.flush()
        cli_id = str(novo_cli.id)
    else:
        cli_id = str(form.get("client_id", ""))

    if cli_id.isdigit():
        cliente = db.get(Client, int(cli_id))
        case.client_id = cliente.id if cliente else None
        case.client = cliente.name if cliente else ""
    else:
        case.client_id, case.client = None, ""

    # SEO deixou de ser formulário: sai do que já foi escrito, toda vez que se
    # salva. Digitar de novo o título numa caixa chamada "título no Google" era
    # trabalho dobrado que, na prática, ficava vazio ou repetia a linha de cima.
    #
    # A FÓRMULA mudou em 22/08/2026 (services/seo.py). Antes o título era só o
    # title_pt e a descrição só o subtítulo — 42 a 50 caracteres onde o Google
    # mostra 155, em 24 páginas de case, e sem o nome do cliente no título.
    # Agora o cliente entra no título e a descrição ganha categoria, cliente e
    # ano, pulando o que o subtítulo já disser. Continua sem formulário.
    _cat = db.get(Category, case.category_id) if case.category_id else None
    case.seo_title = seo.titulo_para_busca(case.title_pt or "", case.client or "")[:200]
    case.seo_desc = seo.descricao_para_busca(
        seo.resumo_do_case(case), (_cat.name_pt if _cat else ""),
        case.client or "", case.year or "")[:320]
    case.noindex = form.get("noindex") == "on"

    was_published = case.published
    # Site nunca é destaque da home: o destaque leva a uma página de case, e um
    # site não tem página. A regra mora aqui, e não só no formulário, porque uma
    # categoria trocada depois transformaria um destaque válido num card quebrado.
    cat_atual = db.get(Category, case.category_id) if case.category_id else None
    eh_site = bool(cat_atual and cat_atual.kind == "sites")
    case.featured = (form.get("featured") == "on") and not eh_site
    # Ordem entre os destaques: número digitado à mão, não arrasto — o campo
    # vazio ou inválido cai no default (999, fim da fila), nunca em erro 500.
    ordem = str(form.get("destaque_ordem", "")).strip()
    case.destaque_ordem = int(ordem) if ordem.lstrip("-").isdigit() else 999
    case.published = form.get("published") == "on"
    case.ig_publish = form.get("ig_publish") == "on"

    if not case.slug:
        base = slugify(case.title_pt or "case")
        slug, i = base, 2
        while db.query(Case).filter(Case.slug == slug, Case.id != case.id).first():
            slug, i = f"{base}-{i}", i + 1
        case.slug = slug

    # Tags: no painel elas são digitadas como hashtag, que é como ele pensa
    # nelas. No banco e no site ficam limpas, porque ali são substantivo e não
    # marcação. O "#" some aqui, na entrada, e não em cada lugar que exibe.
    names = [t.strip().lstrip("#").strip()
             for t in str(form.get("tags", "")).replace("#", ", #").split(",")]
    tags, vistos = [], set()
    for name in [n for n in names if n]:
        slug = slugify(name)
        if not slug or slug in vistos:
            continue                      # a mesma tag digitada duas vezes entra uma
        vistos.add(slug)
        tag = db.query(Tag).filter_by(slug=slug).first() or Tag(slug=slug, name=name)
        tags.append(tag)
    case.tags = tags

    # uso de IA: campo próprio, não mais uma linha digitada na ficha técnica
    ia = str(form.get("ia", "")).strip()
    case.ia = ia if ia in ("sim", "nao") else ""
    case.ficha_on = str(form.get("ficha_on", "")) == "1"

    # ferramentas: só slugs conhecidos entram, na ordem oficial da lista
    from ..services.programas import normalizar as normalizar_programas
    case.programas = normalizar_programas([str(v) for v in form.getlist("programas")])

    # covers (opcionais)
    #
    # Tudo daqui até o fim dos blocos, mais abaixo, pode recusar o formulário
    # (tipo de arquivo errado, vídeo que não é vídeo, JSON de blocos
    # corrompido, captura de site que falhou sem imagem nenhuma) — e uma
    # recusa vira `db.rollback()` lá no chamador (case_new/case_edit). O
    # banco tem rollback; o disco não. Apagar um arquivo que já existia
    # (a capa antiga, o vídeo antigo) ANTES de saber que o RESTO do
    # formulário também é válido significa que uma recusa em QUALQUER outro
    # campo — o vídeo de capa recusado por causa da capa que acabou de
    # validar, os blocos corrompidos, a captura do site — destrói um arquivo
    # bom que não tinha nada a ver com o motivo da recusa, e o banco volta a
    # apontar para ele porque nada foi commitado.
    #
    # `capas_a_apagar` guarda o que só pode sumir depois que a função inteira
    # chegar ao fim sem levantar. `lixo_do_envio` é o caminho simétrico:
    # guarda o que ESTE request criou (a variante otimizada de um upload que
    # já foi aceito) e que fica órfão se uma validação mais adiante recusar o
    # formulário — sem isto, o conserto trocaria perda de dado por vazamento
    # de disco, o que não é conserto nenhum.
    capas_a_apagar: list[str] = []
    lixo_do_envio: list[str] = []
    # Enviar um arquivo novo e marcar "excluir" no mesmo envio é contradição, e
    # quem escolheu o arquivo quer o arquivo: sem esta marca, a exclusão
    # apagaria exatamente o que a pessoa acabou de escolher, e a tela voltaria
    # vazia sem explicação.
    capa_enviada = False

    try:
        cover: UploadFile | None = form.get("cover_image")  # type: ignore[assignment]
        if cover is not None and getattr(cover, "filename", ""):
            kind, rel, thumb = await save_upload(cover, case.slug)
            if kind != "image":
                delete_media_files(rel, thumb)
                raise ValueError("A capa precisa ser uma imagem")
            if thumb:
                # rel (o original) e thumb nascem do MESMO envio — mesma
                # família. delete_media_files varreria o thumb junto; aqui
                # só o original exato precisa sumir, dê certo ou não o resto
                # do formulário — ele nunca chega a ser referenciado em
                # lugar nenhum. Porquê completo em apagar_arquivo_exato, em
                # app/services/images.py.
                apagar_arquivo_exato(rel)
            if case.cover_image:
                capas_a_apagar.append(case.cover_image)
            lixo_do_envio.append(thumb or rel)  # órfão se o formulário for recusado adiante
            case.cover_image = thumb or rel
            capa_enviada = True
        # Prévia do site enviada à mão.
        #
        # A captura automática abre um navegador e fotografa o site, e há site que
        # não se deixa fotografar: o do Assaí devolve a tela de bloqueio do WAF, o da
        # Coevo tem um vídeo de fundo que ainda não pintou na hora do clique. Nesses
        # casos o robô entrega uma imagem — só que a imagem errada, o que é pior que
        # nenhuma, porque nada no sistema acusa o problema.
        #
        # O arquivo enviado aqui grava na capa, e não no campo da captura, porque é
        # a capa que vence a captura em vitrine.capa(): mão sempre ganha de robô, e
        # recapturar depois não desfaz a escolha de quem olhou.
        #
        # Passa pelo mesmo save_upload de qualquer imagem do site, então já sai com
        # a escada de 480/960/1600/2400 em WebP e o cartão de compartilhamento.
        previa: UploadFile | None = form.get("site_previa")  # type: ignore[assignment]
        if previa is not None and getattr(previa, "filename", ""):
            kind, rel, thumb = await save_upload(previa, case.slug)
            if kind != "image":
                delete_media_files(rel, thumb)
                raise ValueError("A prévia do site precisa ser uma imagem")
            if thumb:
                # mesmo caso da capa acima: rel e thumb são família do mesmo
                # envio, e é a família que não pode ser varrida aqui.
                apagar_arquivo_exato(rel)
            if case.cover_image:
                capas_a_apagar.append(case.cover_image)
            lixo_do_envio.append(thumb or rel)
            case.cover_image = thumb or rel
            capa_enviada = True

        # Excluir a capa.
        #
        # Dois nomes de campo para a mesma coisa porque são dois blocos de tela
        # com dois sentidos: nas categorias comuns o botão diz "excluir capa";
        # na categoria "sites" ele diz "voltar para a captura automática", já
        # que lá sumir com a imagem enviada à mão é devolver a vez ao robô. UM
        # caminho de código, e não dois — a mesma regra escrita em dois lugares
        # é o defeito que este projeto vem cortando em toda revisão.
        #
        # Só MARCA para apagar: a remoção acontece no fim, com o resto do
        # formulário já validado, porque uma recusa mais adiante vira
        # `db.rollback()` no chamador e o disco não tem rollback.
        pediu_limpar = any(str(form.get(campo, "")) == "1"
                           for campo in ("capa_limpar", "previa_limpar"))
        if pediu_limpar and not capa_enviada and case.cover_image:
            capas_a_apagar.append(case.cover_image)
            case.cover_image = ""

        # A imagem de compartilhamento é a capa. Existia um campo só para ela, e o
        # resultado era ou vazio (caindo na capa de qualquer jeito) ou a mesma foto
        # enviada duas vezes. Se a capa muda, o que vai para o WhatsApp muda junto.
        if case.seo_image and case.seo_image != case.cover_image:
            capas_a_apagar.append(case.seo_image)
        case.seo_image = case.cover_image

        cover_v: UploadFile | None = form.get("cover_video")  # type: ignore[assignment]
        if cover_v is not None and getattr(cover_v, "filename", ""):
            kind, rel, _ = await save_upload(cover_v, case.slug)
            if kind != "video":
                delete_media_files(rel)  # o envio errado não fica no disco
                raise ValueError("O vídeo de capa precisa ser um vídeo")
            if case.cover_video:
                capas_a_apagar.append(case.cover_video)
            lixo_do_envio.append(rel)
            case.cover_video = rel
        elif str(form.get("video_limpar", "")) == "1" and case.cover_video:
            # o vídeo do hover não tinha caminho de saída nenhum: quem subiu o
            # errado convivia com ele. Mesmo adiamento da capa — marca aqui,
            # apaga no fim
            capas_a_apagar.append(case.cover_video)
            case.cover_video = ""

        # Site da categoria "sites". A captura roda fora do laço de eventos porque
        # abre um navegador de verdade e leva alguns segundos.
        from ..services.captura import atualizar as capturar_site, url_valida
        antes_url = case.site_url
        case.site_url = url_valida(str(form.get("site_url") or ""))
        precisa = case.site_url and (case.site_url != antes_url or form.get("recapturar")
                                     or not case.site_shot)
        if precisa:
            from starlette.concurrency import run_in_threadpool
            erro = await run_in_threadpool(capturar_site, case)
            # Só derruba o salvamento se o case ficaria sem imagem nenhuma. Com uma
            # prévia enviada à mão, a captura é opcional: perder o formulário
            # inteiro porque o robô não conseguiu fotografar um site que já tem
            # imagem escolhida seria trocar um problema resolvido por outro.
            if erro and not case.cover_image:
                raise ValueError("Não consegui capturar a prévia do site: " + erro)
        elif not case.site_url:
            case.site_shot, case.site_shot_at = "", None

        # A página do case, montada no compositor. Vem inteira num campo JSON e é
        # regravada de uma vez: a lista que está na tela vira exatamente a lista que
        # fica no banco. Salvar assim é atômico e dispensa guardar id de bloco.
        if "blocos" in form:
            import json as _json
            try:
                crus = _json.loads(str(form.get("blocos") or "[]"))
            except ValueError:
                raise ValueError("Não consegui ler os blocos da página. Recarregue e tente de novo.")
            novos = blocos_svc.normalizar(crus)

            antes = blocos_svc.arquivos_usados(
                [{"src": m.src, "thumb": m.thumb, "meta": m.meta or {}} for m in case.media])
            # a lista da tela substitui a do banco; pela relação, o FK sai certo
            # tanto no case que já existe quanto no que está nascendo agora
            case.media = [MediaItem(**b) for b in novos]

            # arquivo que saiu da página não fica ocupando disco para sempre —
            # este loop não precisa esperar o fim da função porque nada depois
            # dele pode recusar o formulário (ver o comentário no fim de
            # try_publish_instagram: ele só registra erro, nunca levanta)
            protegidos = {case.cover_image, case.seo_image, case.cover_video, case.site_shot}
            for rel in antes - blocos_svc.arquivos_usados(novos):
                if rel and rel not in protegidos:
                    delete_media_files(rel)
    except ValueError:
        # o formulário inteiro foi recusado — nenhum arquivo que já existia
        # antes deste request pode ter sido tocado (capas_a_apagar nunca foi
        # executado); só o lixo deste envio, que ninguém vai usar porque
        # nada foi commitado, é limpo
        for rel in lixo_do_envio:
            delete_media_files(rel)
        raise

    # só agora, com todo o resto do formulário validado, é seguro apagar o
    # que ficou para trás — o caminho de sucesso continua apagando a capa
    # (e o vídeo, e a imagem de SEO) antigos, exatamente como antes
    for rel in capas_a_apagar:
        delete_media_files(rel)

    eh_novo = case.id is None
    registrar(db, "criou" if eh_novo else "editou", "case",
              case.title_pt or "(sem título)",
              detalhe=(case.category.name_pt if case.category else "") +
                      (" ·︎ publicado" if case.published else " ·︎ rascunho"),
              url=f"/admin/cases/{case.id}" if case.id else "/admin/cases")

    if case.published and not was_published:
        case.published_at = dt.datetime.now(dt.timezone.utc)
        registrar(db, "publicou", "case", case.title_pt or "(sem título)",
                  url=f"/admin/cases/{case.id}" if case.id else "/admin/cases")
        smap = settings_map(db)
        if case.ig_publish and smap.get("ig_auto_publish") == "1":
            await try_publish_instagram(db, case, smap)


async def try_publish_instagram(db: Session, case: Case, smap: dict) -> None:
    link = f"{settings.base_url.rstrip('/')}/case/{case.slug}"
    image_url = ""
    if case.cover_image:
        image_url = f"{settings.base_url.rstrip('/')}/media/{case.cover_image}"
    try:
        if not image_url:
            raise ig.InstagramError("O case precisa de uma imagem de capa para publicar no Instagram.")
        caption = ig.build_caption(case.title_pt, case.subtitle_pt,
                                   [t.slug for t in case.tags], link)
        post_id = await ig.publish_image(smap.get("ig_user_id", ""),
                                         smap.get("ig_access_token", ""), image_url, caption)
        case.ig_status, case.ig_detail = "done", post_id
    except ig.InstagramError as e:
        case.ig_status, case.ig_detail = "error", str(e)
    except Exception as e:  # rede fora etc.
        case.ig_status, case.ig_detail = "error", str(e)[:900]


@router.post("/cases/reorder")
async def cases_reorder(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    data = await request.json()
    check_csrf(request, str(data.get("csrf", "")))
    for i, case_id in enumerate(data.get("order", [])):
        case = db.get(Case, int(case_id))
        if case:
            case.sort = i
    db.commit()
    return JSONResponse({"ok": True})


@router.get("/cases/new")
async def case_new_page(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    return render_admin(request, "admin/case_form.html", case_form_ctx(db, None))


@router.post("/cases/new")
async def case_new(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    case = Case(title_pt="", slug="")
    try:
        await apply_case_form(request, db, case)
    except ValueError as e:
        db.rollback()
        return render_admin(request, "admin/case_form.html",
                            {**case_form_ctx(db, None), "error": str(e)})
    max_sort = db.query(Case).count()
    case.sort = max_sort
    db.add(case)
    db.commit()
    return RedirectResponse(f"/admin/cases/{case.id}", status_code=303)


@router.get("/cases/{case_id}")
async def case_edit_page(case_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    case = db.get(Case, case_id)
    if not case:
        return RedirectResponse("/admin", status_code=302)
    return render_admin(request, "admin/case_form.html", case_form_ctx(db, case))


@router.post("/cases/{case_id}")
async def case_edit(case_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    case = db.get(Case, case_id)
    if not case:
        return RedirectResponse("/admin", status_code=302)
    try:
        await apply_case_form(request, db, case)
    except ValueError as e:
        db.rollback()
        return render_admin(request, "admin/case_form.html",
                            {**case_form_ctx(db, case), "error": str(e)})
    db.commit()
    return RedirectResponse(f"/admin/cases/{case.id}?salvo=1", status_code=303)


@router.post("/cases/{case_id}/delete")
async def case_delete(case_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    case = db.get(Case, case_id)
    if case:
        for m in case.media:
            delete_media_files(m.src if m.kind != "embed" else "", m.thumb)
        delete_media_files(case.cover_image, case.cover_video)
        db.delete(case)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/cases/{case_id}/instagram")
async def case_instagram(case_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    case = db.get(Case, case_id)
    if case:
        await try_publish_instagram(db, case, settings_map(db))
        db.commit()
    return RedirectResponse(f"/admin/cases/{case_id}", status_code=303)


# ---------- Mídia do compositor de blocos ----------
#
# O compositor guarda a página inteira num campo JSON e salva junto com o resto
# do formulário. Estas duas rotas existem só para o que não cabe em JSON: subir
# um arquivo e perguntar ao provedor como incorporar um endereço. Nenhuma das
# duas grava bloco — quem grava é o Salvar do formulário, de uma vez só.

@router.post("/cases/{case_id}/arquivo")
async def bloco_arquivo(case_id: int, request: Request, db: Session = Depends(get_db),
                        _=Depends(require_admin)):
    """Recebe arquivos e devolve os caminhos. O bloco em si nasce no navegador."""
    case = db.get(Case, case_id)
    if not case:
        return JSONResponse({"error": "case não existe"}, status_code=404)
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    saida = []
    for file in form.getlist("files"):
        if not getattr(file, "filename", ""):
            continue
        try:
            kind, rel, thumb = await save_upload(file, case.slug)
        except Exception as e:
            return JSONResponse({"error": str(getattr(e, "detail", e))}, status_code=400)
        saida.append({"kind": kind, "src": rel, "thumb": thumb,
                      "nome": file.filename})
    return JSONResponse({"ok": True, "arquivos": saida})


@router.post("/embed/resolver")
async def bloco_embed(request: Request, _=Depends(require_admin)):
    """Pergunta ao provedor como incorporar um endereço (YouTube, Spotify, IG…)."""
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    url = str(form.get("url", "")).strip()
    try:
        meta = await resolve_embed(url)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    meta["fonte"] = "link"
    return JSONResponse({"ok": True, "url": url, "meta": meta})


# ---------- Perfil / CV ----------

def _com_award_ids(awards: list) -> list:
    """Garante que todo prêmio tenha um `id` estável antes de ir para o
    template. Prêmio já salvo antes desta funcionalidade não tem `id` no
    banco ainda — como nenhum tinha fotos antes dela existir, não há nada
    para casar por id nesse primeiro render; o id novo é o que o form vai
    devolver no próximo salvamento (ver profile_save), e a partir daí fica
    estável (o valor persistido vence o gerado aqui)."""
    saida = []
    for award in awards:
        award = dict(award)
        if not award.get("id"):
            award["id"] = secrets.token_hex(4)
        saida.append(award)
    return saida


@router.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    prof = db.get(Profile, 1)
    data = dict(prof.data) if prof else {}
    data["awards"] = _com_award_ids(data.get("awards", []))
    return render_admin(request, "admin/profile.html", {"p": data})


@router.post("/profile")
async def profile_save(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    prof = db.get(Profile, 1) or Profile(id=1, data={})
    data = dict(prof.data)

    photo: UploadFile | None = form.get("photo")  # type: ignore[assignment]
    if photo is not None and getattr(photo, "filename", ""):
        kind, rel, thumb = await save_upload(photo, "profile")
        if kind == "image":
            delete_media_files(data.get("photo", ""))
            if thumb:
                # rel e thumb são família do mesmo envio — mesmo caso da
                # capa do case, ver apagar_arquivo_exato em
                # app/services/images.py.
                apagar_arquivo_exato(rel)
            data["photo"] = thumb or rel

    cover: UploadFile | None = form.get("cover")  # type: ignore[assignment]
    if cover is not None and getattr(cover, "filename", ""):
        kind, rel, thumb = await save_upload(cover, "profile")
        if kind == "image":
            delete_media_files(data.get("cover", ""))
            data["cover"] = rel  # capa usa a versão grande

    # As duas imagens decorativas da página Sobre (item 2, 19/08): mesmo
    # pipeline de upload de cover/photo acima. Sem upload nenhum, o campo
    # fica vazio e o front cai no asset estático padrão (about-1.webp/
    # about-2.webp) — nada quebra. Enviar um arquivo novo e marcar "excluir"
    # no mesmo request é contradição (mesma regra de capas_a_apagar em
    # apply_case_form): quem escolheu o arquivo quer o arquivo, então o
    # upload é resolvido primeiro e só olhamos a marca de excluir se NENHUM
    # arquivo novo chegou para aquele campo.
    for campo in ("about_img_1", "about_img_2"):
        enviado: UploadFile | None = form.get(campo)  # type: ignore[assignment]
        if enviado is not None and getattr(enviado, "filename", ""):
            kind, rel, thumb = await save_upload(enviado, "profile")
            if kind == "image":
                delete_media_files(data.get(campo, ""))
                data[campo] = rel
        elif str(form.get(f"{campo}_limpar", "")) == "1" and data.get(campo):
            delete_media_files(data[campo])
            data[campo] = ""

    for key in ("name", "title_pt", "title_en", "location_pt", "location_en", "email",
                "summary_pt", "summary_en", "highlight_pt", "highlight_en"):
        data[key] = str(form.get(key, "")).strip()

    data["links"] = {
        "linkedin": str(form.get("link_linkedin", "")).strip(),
        "instagram": str(form.get("link_instagram", "")).strip(),
        "whatsapp": str(form.get("link_whatsapp", "")).strip(),
    }

    # exp_tags é opcional (campo novo — ver o achado da revisão do pacote de
    # lançamento, 19/08): formulário antigo em cache, ou algum outro cliente
    # da rota, pode não mandar o campo. zip_longest com fillvalue="" evita que
    # a ausência dele derrube a linha inteira ou desalinhe as outras colunas
    # (zip puro, com uma lista mais curta que as outras, truncaria TODAS elas).
    data["experience"] = [
        {"company": c, "role_pt": rp, "role_en": re_, "period": p, "desc_pt": dp, "desc_en": de,
         "tags": [t.strip() for t in tags.split(",") if t.strip()]}
        for c, rp, re_, p, dp, de, tags in zip_longest(
            form.getlist("exp_company"), form.getlist("exp_role_pt"), form.getlist("exp_role_en"),
            form.getlist("exp_period"), form.getlist("exp_desc_pt"), form.getlist("exp_desc_en"),
            form.getlist("exp_tags"), fillvalue="",
        ) if c.strip()
    ]
    # Formação acadêmica (item novo, 19/08): mesmo padrão de exp_* acima —
    # instituição bilíngue (institution_pt/en, o nome oficial muda mesmo de
    # um idioma pro outro), curso bilíngue, período compartilhado (mesma
    # convenção de experience.period: só um valor, sem _pt/_en).
    data["education"] = [
        {"institution_pt": ip, "institution_en": ie, "course_pt": cp, "course_en": ce, "period": p}
        for ip, ie, cp, ce, p in zip_longest(
            form.getlist("edu_institution_pt"), form.getlist("edu_institution_en"),
            form.getlist("edu_course_pt"), form.getlist("edu_course_en"),
            form.getlist("edu_period"), fillvalue="",
        ) if ip.strip()
    ]
    data["skills"] = [
        {"group_pt": gp, "group_en": ge, "items": [i.strip() for i in items.split(",") if i.strip()]}
        for gp, ge, items in zip(
            form.getlist("skill_group_pt"), form.getlist("skill_group_en"), form.getlist("skill_items"),
        ) if gp.strip()
    ]
    # Galeria de fotos por prêmio (item novo, 19/08 — conserto pré-fechamento).
    #
    # Pareamento foto↔prêmio por ID ESTÁVEL, não por posição. As demais
    # seções (experience, education, skills) casam colunas puramente pela
    # ordem em que o form manda cada campo, o que é seguro porque nenhuma
    # delas tem upload de arquivo numa linha dinâmica: reordenar/remover uma
    # linha no meio só desloca texto, e texto desalinhado por um campo
    # ausente já tem a defesa do zip_longest (ver a lição do exp_tags acima).
    #
    # Arquivo é outra história: se o pareamento fosse por posição
    # (`award_images` repetido em toda linha, tipo os campos de texto), remover
    # a linha do MEIO em admin/profile.html (del-row, puro DOM, sem re-render
    # do servidor) deixaria o navegador mandar os arquivos das linhas
    # restantes na ordem em que elas ficaram no DOM — a foto que era do
    # prêmio C herdaria o índice que era do B. campo de arquivo teria que
    # migrar de posição sozinho para não vazar, e nada faz isso.
    #
    # Por isso todo award_row leva um <input type="hidden" name="award_id">
    # com um id opaco (persistido a partir do primeiro save; a linha nova do
    # botão "+ adicionar" ganha um id único no cliente, ver admin.js) e os
    # campos de arquivo/exclusão levam esse id no PRÓPRIO NOME:
    # `award_images_{id}` (upload múltiplo) e `award_img_del_{id}` (uma
    # checkbox por foto existente, valor = caminho da foto a excluir). Não é
    # mais "pegue o N-ésimo valor de cada lista": é "pegue os campos cujo
    # nome termina no id desta linha" — sobrevive a qualquer remoção/reordenação
    # no meio da lista porque não depende de posição nenhuma.
    old_awards = {a.get("id"): a for a in data.get("awards", []) if a.get("id")}
    kept_award_ids: set[str] = set()
    data["awards"] = []
    for tp, te, y, dp, de, aid in zip_longest(
        form.getlist("award_title_pt"), form.getlist("award_title_en"),
        form.getlist("award_year"), form.getlist("award_desc_pt"), form.getlist("award_desc_en"),
        form.getlist("award_id"), fillvalue="",
    ):
        if not tp.strip():
            continue
        aid = aid.strip() or secrets.token_hex(4)
        kept_award_ids.add(aid)
        images: list[str] = list(old_awards.get(aid, {}).get("images", []))

        apagar = set(form.getlist(f"award_img_del_{aid}"))
        if apagar:
            for caminho in apagar:
                delete_media_files(caminho)
            images = [img for img in images if img not in apagar]

        for arquivo in form.getlist(f"award_images_{aid}"):
            if not getattr(arquivo, "filename", ""):
                continue
            if len(images) >= AWARD_IMAGES_MAX:
                break
            kind, rel, thumb = await save_upload(arquivo, "profile")
            if kind != "image":
                delete_media_files(rel, thumb)
                continue
            if thumb:
                # rel e thumb são família do mesmo envio (ver about_img acima
                # e apagar_arquivo_exato em app/services/images.py) — só o
                # thumb otimizado fica gravado, o original solto não pode
                # sumir junto se algum dia a família for varrida.
                apagar_arquivo_exato(rel)
            images.append(thumb or rel)

        data["awards"].append({
            "id": aid, "title_pt": tp, "title_en": te, "year": y, "desc_pt": dp, "desc_en": de,
            "images": images,
        })

    # Prêmio removido no admin (del-row) não manda mais award_id nenhum: as
    # fotos dele ficariam órfãs no disco para sempre se não fossem apagadas
    # aqui.
    for aid, antigo in old_awards.items():
        if aid not in kept_award_ids:
            for caminho in antigo.get("images", []):
                delete_media_files(caminho)
    data["certs"] = [
        {"title": t_, "org": o, "year": y, "code": cd, "url": u}
        for t_, o, y, cd, u in zip(form.getlist("cert_title"), form.getlist("cert_org"),
                                   form.getlist("cert_year"), form.getlist("cert_code"),
                                   form.getlist("cert_url"))
        if t_.strip()
    ]
    data["clients"] = [c.strip() for c in str(form.get("clients", "")).split(",") if c.strip()]

    prof.data = data
    db.add(prof)
    db.commit()
    return RedirectResponse("/admin/profile?ok=1", status_code=303)


INLINE_FIELDS = ("summary_pt", "summary_en", "highlight_pt", "highlight_en")


@router.post("/profile/inline")
async def profile_inline(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Edição em tempo real pelo front (modal na página Sobre)."""
    data = await request.json()
    check_csrf(request, str(data.get("csrf", "")))
    field = str(data.get("field", ""))
    value = str(data.get("value", "")).strip()[:4000]
    if field not in INLINE_FIELDS or not value:
        return JSONResponse({"ok": False}, status_code=400)
    prof = db.get(Profile, 1)
    pdata = dict(prof.data)
    pdata[field] = value
    prof.data = pdata
    db.commit()
    return JSONResponse({"ok": True})


# ---------- Configurações ----------

SETTING_KEYS = ("construction_mode", "construction_progress", "cases_publicos",
                "ig_user_id", "ig_auto_publish", "social_instagram",
                "social_facebook", "social_github",
                # Perfil da Empresa no Google, verificado em 23/08/2026. Entra no
                # `sameAs` do JSON-LD: é o que diz ao Google, explicitamente, que o
                # site e aquele perfil são a MESMA entidade. Sem isso ele infere pela
                # coincidência de nome e endereço, que é mais fraco.
                "social_google",
                # Link "deixe sua avaliação" do Perfil da Empresa. É diferente do
                # `social_google` acima: aquele aponta para o perfil, este abre a
                # caixa de avaliação direto. Sai do painel para trocar de perfil um
                # dia não exigir deploy.
                "social_google_review",
                "social_linkedin", "social_whatsapp", "contact_email", "cnpj", "analytics_head",
                "smtp_host", "smtp_port", "smtp_user", "smtp_from", "lead_email",
                "cf_account_id", "cf_stream_key_id",
                # Rastreamento (pacote de 18/08): só o gtm_id é usado pelo site — GA4 e
                # o Pixel do Facebook são configurados DENTRO do contêiner do GTM, no
                # painel do Google. Os dois ficam guardados aqui só como referência e
                # para uso futuro (ver brief da tarefa).
                "gtm_id", "ga4_id", "fb_pixel_id",
                # Barra animada antes de "vamos conversar" na home (item 8, 19/08)
                "marquee_words_pt", "marquee_words_en")
# cf_stream_key_pem fica de fora: é chave privada, multilinha, e "campo vazio"
# significa "mantenha a atual" em vez de "apague" (ver settings_save). Tratar
# ela igual às outras apagaria a chave em silêncio a cada salvamento comum.

SEGREDOS_ECOADOS = ("smtp_password", "cf_api_token", "ig_access_token")
# Os três de cima também ficam fora de SETTING_KEYS, pelo mesmo motivo do
# cf_stream_key_pem: são segredos que não voltam pro HTML (ver settings_page/
# indicador_segredo), então "campo vazio" no POST não pode significar
# "apague" — precisa significar "mantenha o atual" (ver settings_save).
# Até 20/08 eles ecoavam o valor completo em value= a cada GET; corrigido
# para o mesmo padrão de cf_stream_key_pem/anthropic_api_key (/admin/lab).


# ---------- verificação em duas etapas ----------

@router.get("/seguranca")
async def seguranca(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter_by(username=current_user(request)).first()
    return render_admin(request, "admin/seguranca.html", {
        "u": user,
        "restantes": len(user.totp_backup or []) if user else 0,
        "novos_codigos": request.session.pop("codigos_novos", None),
    })


@router.post("/seguranca/preparar")
async def seguranca_preparar(request: Request, db: Session = Depends(get_db),
                             _=Depends(require_admin), csrf: str = Form("")):
    """Gera o segredo e mostra o QR. Só vira ativo depois de confirmar com um código."""
    from ..services import totp as t2
    check_csrf(request, csrf)
    user = db.query(User).filter_by(username=current_user(request)).first()
    if user and not user.totp_ativo:
        user.totp_secret = t2.novo_segredo()
        db.commit()
    return RedirectResponse("/admin/seguranca#configurar", status_code=303)


@router.get("/seguranca/qr.png")
async def seguranca_qr(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    """QR do segredo pendente. Some assim que o 2FA fica ativo."""
    import io

    import segno
    from fastapi.responses import Response

    from ..services import totp as t2
    user = db.query(User).filter_by(username=current_user(request)).first()
    if not user or not user.totp_secret or user.totp_ativo:
        return Response(status_code=404)
    buf = io.BytesIO()
    segno.make(t2.uri(user.totp_secret, user.username), error="m").save(
        buf, kind="png", scale=7, border=2, dark="#f0efec", light="#111110")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@router.post("/seguranca/ativar")
async def seguranca_ativar(request: Request, db: Session = Depends(get_db),
                           _=Depends(require_admin), csrf: str = Form(""), codigo: str = Form("")):
    from ..services import totp as t2
    check_csrf(request, csrf)
    user = db.query(User).filter_by(username=current_user(request)).first()
    if not user or not user.totp_secret:
        return RedirectResponse("/admin/seguranca", status_code=303)
    if not t2.confere(user.totp_secret, codigo):
        return RedirectResponse("/admin/seguranca?erro=codigo#configurar", status_code=303)

    codigos = t2.novos_codigos_recuperacao()
    user.totp_backup = [t2.hash_codigo(c) for c in codigos]
    user.totp_ativo = True
    user.totp_desde = dt.datetime.now(dt.timezone.utc)
    db.commit()
    # mostrados uma única vez: em texto puro eles não voltam para o banco
    request.session["codigos_novos"] = codigos
    return RedirectResponse("/admin/seguranca?ativado=1", status_code=303)


@router.post("/seguranca/desligar")
async def seguranca_desligar(request: Request, db: Session = Depends(get_db),
                             _=Depends(require_admin), csrf: str = Form(""),
                             senha: str = Form("")):
    """Desligar exige a senha: sessão sequestrada não desarma a proteção sozinha."""
    check_csrf(request, csrf)
    user = db.query(User).filter_by(username=current_user(request)).first()
    if not user or not verify_password(user.password_hash, senha):
        return RedirectResponse("/admin/seguranca?erro=senha", status_code=303)
    user.totp_ativo = False
    user.totp_secret = ""
    user.totp_backup = []
    user.totp_desde = None
    db.commit()
    return RedirectResponse("/admin/seguranca?desligado=1", status_code=303)


@router.post("/seguranca/novos-codigos")
async def seguranca_novos_codigos(request: Request, db: Session = Depends(get_db),
                                  _=Depends(require_admin), csrf: str = Form(""),
                                  senha: str = Form("")):
    from ..services import totp as t2
    check_csrf(request, csrf)
    user = db.query(User).filter_by(username=current_user(request)).first()
    if not user or not verify_password(user.password_hash, senha):
        return RedirectResponse("/admin/seguranca?erro=senha", status_code=303)
    codigos = t2.novos_codigos_recuperacao()
    user.totp_backup = [t2.hash_codigo(c) for c in codigos]
    db.commit()
    request.session["codigos_novos"] = codigos
    return RedirectResponse("/admin/seguranca?codigos=1", status_code=303)


@router.post("/settings/api-token")
async def settings_api_token(request: Request, db: Session = Depends(get_db),
                             _=Depends(require_admin), csrf: str = Form(""), acao: str = Form("")):
    """Gera ou revoga o token da API de conteúdo."""
    from .api import TOKEN_KEY, new_api_token
    check_csrf(request, csrf)
    set_setting(db, TOKEN_KEY, "" if acao == "revogar" else new_api_token())
    db.commit()
    return RedirectResponse("/admin/settings?ok=1#api", status_code=303)


@router.get("/settings")
async def settings_page(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    smap = settings_map(db)
    try:
        estado = json.loads(smap.get("ig_token_status") or "{}")
    except Exception:
        estado = {}
    return render_admin(request, "admin/settings.html", {
        "s": smap, "ig_estado": estado,
        "smtp_password_ind": indicador_segredo(smap.get("smtp_password")),
        "cf_api_token_ind": indicador_segredo(smap.get("cf_api_token")),
        "ig_access_token_ind": indicador_segredo(smap.get("ig_access_token")),
    })


@router.post("/settings")
async def settings_save(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    for key in SETTING_KEYS:
        if key in ("ig_auto_publish", "construction_mode", "cases_publicos"):
            set_setting(db, key, "1" if form.get(key) == "on" else "0")
        elif key in form:
            set_setting(db, key, str(form.get(key, "")).strip())

    # A chave privada da Cloudflare Stream não segue o padrão acima: ela nunca
    # volta pro HTML (ver settings_page), então o textarea chega vazio a cada
    # carregamento mesmo quando já existe uma chave guardada. Se tratássemos
    # "vazio" como "apague", qualquer salvamento comum da tela — trocar só o
    # e-mail de contato, por exemplo — apagaria a chave em silêncio. Por isso
    # vazio aqui significa "mantenha a atual"; apagar exige marcar a caixa.
    if form.get("cf_stream_key_pem_remover") == "on":
        set_setting(db, "cf_stream_key_pem", "")
    else:
        pem = str(form.get("cf_stream_key_pem", "")).strip()
        if pem:
            set_setting(db, "cf_stream_key_pem", pem)

    # smtp_password/cf_api_token/ig_access_token: mesma semântica acima —
    # a caixa "remover" apaga, campo vazio mantém o segredo já guardado.
    for chave in SEGREDOS_ECOADOS:
        if form.get(f"{chave}_remover") == "on":
            set_setting(db, chave, "")
        else:
            valor = str(form.get(chave, "")).strip()
            if valor:
                set_setting(db, chave, valor)

    db.commit()

    # troca de usuário e senha (as duas opcionais)
    def erro(msg: str):
        smap_erro = settings_map(db)
        return render_admin(request, "admin/settings.html", {
            "s": smap_erro, "error": msg, "ig_estado": {},
            "smtp_password_ind": indicador_segredo(smap_erro.get("smtp_password")),
            "cf_api_token_ind": indicador_segredo(smap_erro.get("cf_api_token")),
            "ig_access_token_ind": indicador_segredo(smap_erro.get("ig_access_token")),
        })

    user = db.query(User).filter_by(username=current_user(request)).first()

    novo_user = str(form.get("new_username", "")).strip()
    if novo_user and user and novo_user != user.username:
        if len(novo_user) < 4:
            return erro("O nome de usuário precisa de ao menos 4 caracteres.")
        if db.query(User).filter(User.username == novo_user, User.id != user.id).first():
            return erro("Já existe um usuário com esse nome.")
        user.username = novo_user
        db.commit()
        # a sessão guarda o nome antigo: sem isto, o próximo clique cai no login
        request.session["user"] = novo_user

    new_pass = str(form.get("new_password", ""))
    if new_pass:
        if len(new_pass) < 10:
            return erro("A nova senha precisa de ao menos 10 caracteres.")
        if user:
            user.password_hash = hash_password(new_pass)
            db.commit()

    # Token de usuário expira em 60 dias e morre em silêncio. O da Página não expira,
    # então a troca acontece aqui, sem o Leandro precisar saber que isso existe.
    smap = settings_map(db)
    aviso = ""
    if smap.get("ig_user_id") and smap.get("ig_access_token"):
        novo, aviso = await ig.garantir_token_permanente(
            smap["ig_user_id"], smap["ig_access_token"])
        if novo != smap["ig_access_token"]:
            set_setting(db, "ig_access_token", novo)
            db.commit()
            aviso = "trocado"
        await _guardar_estado_ig(db)
    destino = "/admin/settings?ok=1"
    if aviso == "trocado":
        destino += "&ig=permanente"
    elif aviso:
        destino += f"&ig_erro={aviso[:160]}"
    return RedirectResponse(destino, status_code=303)


async def _guardar_estado_ig(db: Session) -> dict:
    """Guarda o retrato do token para o painel mostrar sem chamar a Meta toda hora."""
    smap = settings_map(db)
    estado = await ig.estado_do_token(smap.get("ig_user_id", ""),
                                      smap.get("ig_access_token", ""))
    set_setting(db, "ig_token_status", json.dumps(estado))
    db.commit()
    return estado


@router.post("/settings/instagram-verificar")
async def instagram_verificar(request: Request, db: Session = Depends(get_db),
                              _=Depends(require_admin), csrf: str = Form("")):
    """Confere o token agora e, se ainda for de usuário, troca pelo da Página."""
    check_csrf(request, csrf)
    smap = settings_map(db)
    novo, aviso = await ig.garantir_token_permanente(
        smap.get("ig_user_id", ""), smap.get("ig_access_token", ""))
    if novo and novo != smap.get("ig_access_token"):
        set_setting(db, "ig_access_token", novo)
        db.commit()
        aviso = "trocado"
    estado = await _guardar_estado_ig(db)
    if aviso == "trocado":
        return RedirectResponse("/admin/settings?ok=1&ig=permanente", status_code=303)
    if aviso:
        return RedirectResponse(f"/admin/settings?ig_erro={aviso[:160]}", status_code=303)
    return RedirectResponse("/admin/settings?ig=ok", status_code=303)


# ---------- Mensagens ----------

@router.get("/messages")
async def messages(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    msgs = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()
    for m in msgs:
        m.read = True
    db.commit()
    return render_admin(request, "admin/messages.html", {"messages": msgs})


@router.get("/linkedin")
async def linkedin_list(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    posts = db.query(LinkedInPost).order_by(LinkedInPost.created_at.desc()).all()
    return render_admin(request, "admin/linkedin.html", {"posts": posts})


@router.post("/linkedin")
async def linkedin_add(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    summary = str(form.get("summary", "")).strip()[:400]
    url = str(form.get("url", "")).strip()[:500]
    tag = str(form.get("tag", "")).strip()[:80]
    if summary and url.startswith("http"):
        db.add(LinkedInPost(summary=summary, tag=tag, url=url))
        db.commit()
    return RedirectResponse("/admin/linkedin?ok=1", status_code=303)


@router.post("/linkedin/{post_id}/delete")
async def linkedin_delete(post_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    post = db.get(LinkedInPost, post_id)
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse("/admin/linkedin", status_code=303)


@router.post("/messages/{msg_id}/delete")
async def message_delete(msg_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    msg = db.get(ContactMessage, msg_id)
    if msg:
        db.delete(msg)
        db.commit()
    return RedirectResponse("/admin/messages", status_code=303)


# ---------- Lab de Demos (Task 7 do Plano 1 — Fundação) ----------
# Painel único (§7/§10 da spec): gasto de IA do dia/mês, sandboxes ativos,
# leads captados nas demos e os configuráveis do guardião de IA
# (anthropic_api_key/lab_ia_teto_dia/lab_ia_modelo, chaves criadas na Task 4
# mas sem tela até aqui — sem elas `chamar_ia` sempre cai em fallback).
# As telas públicas do Lab (Plano 2) ainda não existem, então os números
# ficam em zero em produção até lá — a tela já nasce correta para quando
# passarem a existir.

from ..lab import ia as lab_ia
from ..lab.models import LabIaGasto, LabLead, LabSandbox
from ..lab.protecao import MAX_IA_POR_SANDBOX


def _lab_gasto_dia_mes(db: Session) -> dict:
    hoje = dt.date.today()
    registro_hoje = db.query(LabIaGasto).filter(LabIaGasto.dia == hoje).one_or_none()
    inicio_mes = hoje.replace(day=1)
    registros_mes = (
        db.query(LabIaGasto)
        .filter(LabIaGasto.dia >= inicio_mes, LabIaGasto.dia <= hoje)
        .all()
    )
    return {
        "dia_centavos": registro_hoje.custo_estimado_centavos if registro_hoje else 0,
        "dia_tokens": registro_hoje.tokens if registro_hoje else 0,
        "mes_centavos": sum(r.custo_estimado_centavos for r in registros_mes),
        "mes_tokens": sum(r.tokens for r in registros_mes),
    }


def _contexto_lab(db: Session) -> dict:
    smap = settings_map(db)
    gasto = _lab_gasto_dia_mes(db)

    # "ativos" segue o mesmo invariante fixado na revisão da Task 2 do Lab
    # (ver ledger .superpowers/sdd/2026-08-20-lab-demos-fundacao/progress.md):
    # total de linhas em lab_sandbox, sem filtrar por expira_em — os vencidos
    # ainda contam até a limpeza diária (cron) apagá-los. Mesma leitura que
    # `reciclar_se_lotado` já usa em app/lab/sandbox.py.
    sandboxes_ativos = db.query(LabSandbox).count()
    sandboxes_com_ia = db.query(LabSandbox).filter(LabSandbox.chamadas_ia > 0).count()
    sandboxes_no_teto = (
        db.query(LabSandbox).filter(LabSandbox.chamadas_ia >= MAX_IA_POR_SANDBOX).count()
    )

    leads = db.query(LabLead).order_by(LabLead.criado_em.desc()).limit(200).all()

    chave = smap.get("anthropic_api_key") or ""

    bruto_teto = smap.get("lab_ia_teto_dia")
    try:
        teto_centavos = (
            int(bruto_teto) if bruto_teto not in (None, "") else lab_ia.TETO_DIA_PADRAO_CENTAVOS
        )
    except (TypeError, ValueError):
        teto_centavos = lab_ia.TETO_DIA_PADRAO_CENTAVOS

    return {
        "gasto": gasto,
        "sandboxes_ativos": sandboxes_ativos,
        "sandboxes_com_ia": sandboxes_com_ia,
        "sandboxes_no_teto": sandboxes_no_teto,
        "max_ia_por_sandbox": MAX_IA_POR_SANDBOX,
        "leads": leads,
        # a chave NUNCA volta inteira pro HTML (§9.2 vale para segredo do
        # dono também) — só se está configurada e os 4 últimos caracteres,
        # mesmo padrão de "mantenha a atual se vazio" do cf_stream_key_pem
        # em settings.html/settings_save.
        "api_key_configurada": bool(chave),
        "api_key_final4": chave[-4:] if len(chave) >= 4 else "",
        "lab_ia_modelo": smap.get("lab_ia_modelo") or lab_ia.MODELO_PADRAO,
        # "reais" (float, formato com PONTO) só alimenta o value= do input
        # type=number, que HTML sempre espera em ponto independente de locale;
        # "centavos" (int) alimenta o filtro `reais` (vírgula PT-BR) na exibição.
        "teto_dia_reais": teto_centavos / 100,
        "teto_dia_centavos": teto_centavos,
        "redesigns": db.query(Redesign).order_by(Redesign.criado_em.desc()).all(),
    }


@router.get("/lab")
async def lab_painel(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    return render_admin(request, "admin/lab.html", _contexto_lab(db))


@router.post("/lab")
async def lab_salvar(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))

    modelo = str(form.get("lab_ia_modelo", "")).strip()
    if modelo:
        set_setting(db, "lab_ia_modelo", modelo[:80])

    # Mesmo padrão de cf_stream_key_pem: campo vazio no POST significa
    # "mantenha a chave atual", não "apague" — apagar exige a caixa marcada.
    if form.get("anthropic_api_key_remover") == "on":
        set_setting(db, "anthropic_api_key", "")
    else:
        chave = str(form.get("anthropic_api_key", "")).strip()
        if chave:
            set_setting(db, "anthropic_api_key", chave[:200])

    teto_bruto = str(form.get("lab_ia_teto_dia_reais", "")).strip()
    if teto_bruto:
        try:
            reais = float(teto_bruto.replace(",", "."))
            if reais < 0:
                raise ValueError("teto negativo")
        except ValueError:
            db.commit()
            ctx = _contexto_lab(db)
            ctx["error"] = "Teto diário inválido — use um valor em reais, ex.: 0,50."
            return render_admin(request, "admin/lab.html", ctx)
        set_setting(db, "lab_ia_teto_dia", str(round(reais * 100)))

    db.commit()
    return RedirectResponse("/admin/lab?ok=1", status_code=303)


# ---------- Redesigns do Lab (Task 5 do corte 1 de Sites) ----------
# O painel onde o Leandro cria o registro, colhe o dossiê do site do
# cliente, dispara as duas capturas de tela, vira o estado e copia o link
# do pitch. Cinco rotas, todas sob /admin/lab, para o mesmo modelo.

from ..models import ESTADOS_REDESIGN, Redesign, novo_token
from ..services import captura, coleta


def _redesign(db: Session, ident: int) -> Redesign:
    r = db.get(Redesign, ident)
    if r is None:
        raise HTTPException(status_code=404, detail="Redesign não encontrado.")
    return r


def _slug_livre(db: Session, base: str) -> str:
    """`aurora`, depois `aurora-2`, depois `aurora-3`.

    Duas marcas com o mesmo nome existem, e o segundo cadastro não pode
    estourar com IntegrityError na cara de quem está cadastrando."""
    slug = base or "redesign"
    n = 1
    while db.query(Redesign).filter(Redesign.slug == slug).first() is not None:
        n += 1
        slug = f"{base}-{n}"
    return slug


@router.post("/lab/redesigns")
async def redesign_criar(request: Request, marca: str = Form(...), setor: str = Form(""),
                         antes_url: str = Form(...), db: Session = Depends(get_db),
                         _admin=Depends(require_admin), csrf: str = Form("")):
    """O Leandro digita marca e endereço. Slug e token são derivados: um do
    nome, outro de `secrets`. Pedir os dois no formulário seria pedir que ele
    invente o que a máquina faz melhor, e um token digitado à mão seria um
    token adivinhável."""
    check_csrf(request, csrf)
    endereco = captura.url_valida(antes_url)
    if not endereco:
        raise HTTPException(status_code=400, detail="Endereço do site inválido.")
    r = Redesign(
        slug=_slug_livre(db, slugify(marca)),
        marca=marca.strip(), setor=setor.strip(),
        antes_url=endereco, token=novo_token(),
    )
    db.add(r)
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/estado")
async def redesign_estado(ident: int, request: Request, estado: str = Form(...),
                          db: Session = Depends(get_db),
                          _admin=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    if estado not in ESTADOS_REDESIGN:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {estado}")
    r = _redesign(db, ident)
    r.estado = estado
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/colher")
async def redesign_colher(ident: int, request: Request, db: Session = Depends(get_db),
                          _admin=Depends(require_admin), csrf: str = Form("")):
    """Baixa o site do cliente e grava o dossiê (§4).

    Falhando, NÃO apaga o dossiê anterior: site do cliente fora do ar não
    pode custar o material de uma proposta em andamento."""
    check_csrf(request, csrf)
    r = _redesign(db, ident)
    dossie = coleta.colher(r.antes_url)
    if dossie.get("ok"):
        r.insumos = dossie
        r.insumos_em = dt.datetime.now(dt.timezone.utc)
        db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/capturar")
async def redesign_capturar(ident: int, request: Request, lado: str = Form("antes"),
                            db: Session = Depends(get_db),
                            _admin=Depends(require_admin), csrf: str = Form("")):
    """Fotografa um dos dois lados da cortina.

    O "depois" entra pelo endereço INTERNO do contêiner, e não por
    `settings.base_url`. O Chromium de `app/services/captura.py` roda AQUI
    DENTRO (Dockerfile, linha 14) e o nginx roda no host. Se a captura
    batesse no endereço público, a requisição sairia do contêiner e
    voltaria pelo nginx, que carimbaria o IP da bridge do Docker (172.x.x.x)
    em vez de 127.0.0.1 — e a regra de loopback em
    `app/lab/rotas_sites.py::marcar_visto` NÃO pegaria essa captura, que
    marcaria o cliente como tendo aberto a proposta antes de ela ter sido
    enviada (§9.1 da spec). O uvicorn escuta em 0.0.0.0:8000 dentro do
    contêiner (Dockerfile, CMD), daí o endereço fixo abaixo.

    Além disso, o "depois" só existe pelo link do TOKEN: enquanto o
    redesign é `pitch`, o endereço público responde 404 (§6), e a captura
    voltaria vazia."""
    check_csrf(request, csrf)
    r = _redesign(db, ident)
    if lado == "depois":
        # Endereço INTERNO do contêiner, e não `settings.base_url`. O
        # Chromium roda aqui dentro e o nginx roda no host: bater no
        # endereço público faria a requisição sair e voltar pelo proxy, que
        # carimbaria o IP da bridge do Docker em vez de 127.0.0.1 — e aí a
        # regra de loopback de `marcar_visto` não pegaria a captura, que
        # marcaria o cliente como tendo aberto a proposta antes de ela ser
        # enviada (§9.1 da spec).
        alvo = f"http://127.0.0.1:8000/lab/p/{r.token}"
        nome = f"redesign-{r.slug}-depois"
    else:
        alvo = r.antes_url
        nome = f"redesign-{r.slug}-antes"

    caminho, erro = captura.capturar(alvo, nome)
    if not erro and caminho:
        agora = dt.datetime.now(dt.timezone.utc)
        if lado == "depois":
            r.depois_shot, r.depois_shot_at = caminho, agora
        else:
            r.antes_shot, r.antes_shot_at = caminho, agora
        db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/enviado")
async def redesign_enviado(ident: int, request: Request, db: Session = Depends(get_db),
                           _admin=Depends(require_admin), csrf: str = Form("")):
    """Carimba `enviado_em`, o par de `visto_em`.

    O servidor não tem como saber que o link foi para o WhatsApp de alguém,
    então quem sabe é o Leandro, e ele diz com um clique. Sem os dois
    carimbos, `visto_em` sozinho responde "abriu" mas não "abriu depois de
    quanto tempo", que é a diferença entre um prospect morno e um frio."""
    check_csrf(request, csrf)
    r = _redesign(db, ident)
    r.enviado_em = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/excluir")
async def redesign_excluir(ident: int, request: Request, db: Session = Depends(get_db),
                           _admin=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    db.delete(_redesign(db, ident))
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)
