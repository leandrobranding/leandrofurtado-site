"""Central de cases: listar, filtrar, medir, moderar e organizar.

Fica em arquivo próprio, com prefixo /admin/cases, e é montado antes do router
do admin. A ordem importa: /admin/cases/{case_id} espera um número, e sem esta
precedência um caminho como /admin/cases/insights seria lido como um id
inválido e devolveria erro em vez de página.

O cadastro e a edição de um case continuam no admin.py, junto do upload de
mídia e da publicação no Instagram, que já funcionavam. Aqui está tudo que é
sobre o conjunto: a visão geral, os números, os comentários e as categorias.
"""

from __future__ import annotations

import datetime as dt
import unicodedata

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..auth import check_csrf, csrf_token, require_admin
from ..config import agora_daqui
from ..database import get_db
from ..models import (Case, CaseComment, CaseView, Category, Client, MediaItem,
                      Tag)
from ..services import categorias as cats_svc
from ..services import traduz
from ..services.atividade import registrar
from ..services.images import slugify

router = APIRouter(prefix="/admin/cases", tags=["cases"])


def _render(request: Request, nome: str, ctx: dict):
    from ..main import render
    return render(request, nome, ctx)


# ---------------------------------------------------------------- listagem

ORDENS = {
    "recentes": "Mais recentes",
    "antigos": "Mais antigos",
    "ordem": "Ordem do site",
    "vistos": "Mais vistos",
    "titulo": "Título (A-Z)",
}


def _plano(texto: str) -> str:
    """Sem acento e sem caixa: "video" acha "Vídeo", "sao" acha "São"."""
    normal = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in normal if unicodedata.category(c) != "Mn").lower()


def _texto_do_case(case: Case) -> str:
    """Tudo que a busca enxerga num case, num campo só."""
    cliente = case.client_ref.name if case.client_ref else (case.client or "")
    partes = [case.title_pt or "", cliente, case.category.name_pt if case.category else "",
              case.year or "", case.slug or "", case.site_url or ""]
    return _plano(" ".join(partes))


def _contagem_views(db: Session) -> dict[int, int]:
    linhas = db.query(CaseView.case_id, func.sum(CaseView.hits)).group_by(CaseView.case_id).all()
    return {cid: int(total or 0) for cid, total in linhas}


@router.get("/lista")
async def lista(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
              q: str = "", cat: str = "", cli: str = "", ano: str = "",
              estado: str = "publicados", ordem: str = "recentes"):
    cases = (db.query(Case)
             .options(joinedload(Case.category), joinedload(Case.client_ref),
                      joinedload(Case.tags))
             .all())

    vistos = _contagem_views(db)
    comentarios = dict(db.query(CaseComment.case_id, func.count(CaseComment.id))
                       .group_by(CaseComment.case_id).all())
    pendentes = dict(db.query(CaseComment.case_id, func.count(CaseComment.id))
                     .filter(CaseComment.status == "pendente")
                     .group_by(CaseComment.case_id).all())

    filtrados = cases
    if q:
        # Os mesmos campos e as mesmas regras da busca ao vivo da tela: cada
        # palavra tem que aparecer em algum lugar, sem acento e sem caixa. Se as
        # duas peneiras discordassem, recarregar a página mudaria o resultado.
        termos = [t for t in _plano(q).split() if t]
        filtrados = [c for c in filtrados
                     if all(t in _texto_do_case(c) for t in termos)]
    if cat == "_sem":
        # case sem categoria não aparece em filtro nenhum do portfólio, então
        # precisa de um filtro próprio aqui para ser achado e resolvido
        filtrados = [c for c in filtrados if not c.category_id]
    elif cat:
        filtrados = [c for c in filtrados if c.category and c.category.slug == cat]
    if cli:
        filtrados = [c for c in filtrados if c.client_ref and c.client_ref.slug == cli]
    if ano:
        filtrados = [c for c in filtrados if (c.year or "") == ano]

    # As contagens das abas saem daqui, antes do estado entrar: com um filtro de
    # categoria ou de cliente aplicado, "Rascunhos 2" tem que significar dois
    # rascunhos daquele recorte, e não do portfólio inteiro.
    contagens = {
        "publicados": len([c for c in filtrados if c.published and not c.archived]),
        "rascunhos": len([c for c in filtrados if not c.published and not c.archived]),
        "arquivados": len([c for c in filtrados if c.archived]),
    }

    if estado == "rascunhos":
        filtrados = [c for c in filtrados if not c.published and not c.archived]
    elif estado == "arquivados":
        filtrados = [c for c in filtrados if c.archived]
    else:
        # publicado é o padrão: é a lista do que está no ar, que é o que se olha
        estado = "publicados"
        filtrados = [c for c in filtrados if c.published and not c.archived]

    chaves = {
        "recentes": lambda c: (c.created_at is None, -(c.created_at.timestamp() if c.created_at else 0)),
        "antigos": lambda c: (c.created_at is None, c.created_at.timestamp() if c.created_at else 0),
        "ordem": lambda c: (c.sort, c.id),
        "vistos": lambda c: -vistos.get(c.id, 0),
        "titulo": lambda c: (c.title_pt or "").lower(),
    }
    filtrados.sort(key=chaves.get(ordem, chaves["recentes"]))

    anos = sorted({c.year for c in cases if c.year}, reverse=True)

    # Régua do desempenho: a barra de cada case é lida contra o mais visto, e a
    # cor sai da média. Sem uma referência, "12 acessos" não diz se é bom.
    no_ar = [c for c in cases if c.published and not c.archived]
    numeros_no_ar = [vistos.get(c.id, 0) for c in no_ar]
    media = (sum(numeros_no_ar) / len(numeros_no_ar)) if numeros_no_ar else 0

    return _render(request, "admin/cases_lista.html", {
        "cases": filtrados, "todos": cases, "vistos": vistos,
        "comentarios": comentarios, "pendentes": pendentes,
        "categories": cats_svc.ordenadas(db),
        "clientes": db.query(Client).order_by(Client.name).all(),
        "anos": anos, "ordens": ORDENS,
        "f": {"q": q, "cat": cat, "cli": cli, "ano": ano, "estado": estado, "ordem": ordem},
        "contagens": contagens,
        "pico": max(numeros_no_ar or [0]),
        "media": media,
        "csrf": csrf_token(request),
        "total_pendentes": db.query(CaseComment).filter_by(status="pendente").count(),
    })


@router.get("")
async def central(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    """A porta de entrada: o que existe, quanto tem, e o que pede atenção."""
    cases = db.query(Case).options(joinedload(Case.category)).all()
    vistos = _contagem_views(db)
    pendentes = db.query(CaseComment).filter_by(status="pendente").count()
    publicados = [c for c in cases if c.published and not c.archived]

    hoje = agora_daqui().date()
    desde = (hoje - dt.timedelta(days=29)).isoformat()
    mes = (db.query(func.sum(CaseView.hits)).filter(CaseView.day >= desde).scalar() or 0)

    return _render(request, "admin/cases_hub.html", {
        "resumo": {
            "total": len(cases),
            "publicados": len(publicados),
            "rascunhos": len([c for c in cases if not c.published and not c.archived]),
            "arquivados": len([c for c in cases if c.archived]),
            "vistos": sum(vistos.values()),
            "mes": int(mes),
            "categorias": db.query(Category).count(),
            "clientes": db.query(Client).count(),
            "comentarios": db.query(CaseComment).count(),
            "sem_categoria": len([c for c in cases if not c.category_id]),
            "sem_acesso": len([c for c in publicados if not vistos.get(c.id)]),
        },
        "recentes": sorted(cases, key=lambda c: -(c.created_at.timestamp() if c.created_at else 0))[:5],
        "total_pendentes": pendentes,
        "csrf": csrf_token(request),
    })


# ---------------------------------------------------------------- ações em lote

@router.post("/{case_id}/arquivar")
async def arquivar(case_id: int, request: Request, db: Session = Depends(get_db),
                   _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    case = db.get(Case, case_id)
    if case:
        case.archived = not case.archived
        # arquivar tira do ar; desarquivar não republica sozinho, para não
        # devolver ao site um trabalho que talvez tenha saído por um motivo
        if case.archived:
            case.published = False
        registrar(db, "arquivou" if case.archived else "desarquivou", "case",
                  case.title_pt or "(sem título)", url=f"/admin/cases/{case.id}")
        db.commit()
    return RedirectResponse(request.headers.get("referer", "/admin/cases/lista"), status_code=303)


@router.post("/{case_id}/duplicar")
async def duplicar(case_id: int, request: Request, db: Session = Depends(get_db),
                   _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    orig = (db.query(Case).options(joinedload(Case.media), joinedload(Case.tags))
            .filter_by(id=case_id).first())
    if not orig:
        return RedirectResponse("/admin/cases/lista", status_code=303)

    base = f"{orig.slug}-copia"
    slug, n = base, 2
    while db.query(Case).filter_by(slug=slug).first():
        slug, n = f"{base}-{n}", n + 1

    novo = Case(
        slug=slug, title_pt=f"{orig.title_pt} (cópia)", title_en=orig.title_en,
        subtitle_pt=orig.subtitle_pt, subtitle_en=orig.subtitle_en,
        client=orig.client, client_id=orig.client_id, year=orig.year,
        role_pt=orig.role_pt, role_en=orig.role_en,
        body_pt=orig.body_pt, body_en=orig.body_en,
        cover_image=orig.cover_image, cover_video=orig.cover_video, accent=orig.accent,
        category_id=orig.category_id, site_url=orig.site_url,
        seo_title=orig.seo_title, seo_desc=orig.seo_desc, seo_image=orig.seo_image,
        published=False, featured=False, sort=orig.sort,
    )
    novo.tags = list(orig.tags)
    db.add(novo)
    db.flush()
    # a mídia é copiada por referência: os arquivos são os mesmos no disco, e
    # duplicar bytes de vídeo para uma cópia que talvez seja descartada é caro
    for m in orig.media:
        db.add(MediaItem(case_id=novo.id, kind=m.kind, src=m.src, thumb=m.thumb,
                         caption_pt=m.caption_pt, caption_en=m.caption_en,
                         layout=m.layout, meta=m.meta, sort=m.sort))
    registrar(db, "criou", "case", novo.title_pt,
              detalhe=f"cópia de {orig.title_pt}", url=f"/admin/cases/{novo.id}")
    db.commit()
    return RedirectResponse(f"/admin/cases/{novo.id}", status_code=303)


# ---------------------------------------------------------------- números

@router.get("/insights")
async def insights(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    cases = (db.query(Case).options(joinedload(Case.category), joinedload(Case.client_ref)).all())
    vistos = _contagem_views(db)

    hoje = agora_daqui().date()
    dias = [(hoje - dt.timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    por_dia = dict(db.query(CaseView.day, func.sum(CaseView.hits))
                   .filter(CaseView.day >= dias[0]).group_by(CaseView.day).all())
    serie = [{"dia": d, "hits": int(por_dia.get(d, 0) or 0)} for d in dias]
    pico = max([s["hits"] for s in serie] + [1])

    def agrupar(chave):
        saida: dict[str, dict] = {}
        for c in cases:
            nome = chave(c)
            if not nome:
                continue
            alvo = saida.setdefault(nome, {"nome": nome, "cases": 0, "vistos": 0})
            alvo["cases"] += 1
            alvo["vistos"] += vistos.get(c.id, 0)
        return sorted(saida.values(), key=lambda x: -x["vistos"])

    ranking = sorted(cases, key=lambda c: -vistos.get(c.id, 0))
    publicados = [c for c in cases if c.published and not c.archived]
    return _render(request, "admin/cases_insights.html", {
        "cases": cases, "vistos": vistos, "serie": serie, "pico": pico,
        "ranking": ranking[:12],
        "sem_acesso": [c for c in publicados if not vistos.get(c.id)],
        "por_categoria": agrupar(lambda c: c.category.name_pt if c.category else ""),
        "por_cliente": agrupar(lambda c: c.client_ref.name if c.client_ref else (c.client or "")),
        "por_ano": sorted(agrupar(lambda c: c.year), key=lambda x: x["nome"], reverse=True),
        "totais": {
            "cases": len(cases),
            "publicados": len(publicados),
            "rascunhos": len([c for c in cases if not c.published and not c.archived]),
            "arquivados": len([c for c in cases if c.archived]),
            "vistos": sum(vistos.values()),
            "mes": sum(s["hits"] for s in serie),
            "comentarios": db.query(CaseComment).count(),
        },
        "csrf": csrf_token(request),
    })


# ---------------------------------------------------------------- comentários

@router.get("/comentarios")
async def comentarios(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                      status: str = "pendente"):
    q = db.query(CaseComment).options(joinedload(CaseComment.case))
    if status in ("pendente", "aprovado", "spam"):
        q = q.filter(CaseComment.status == status)
    lista = q.order_by(CaseComment.created_at.desc()).limit(300).all()
    contagens = dict(db.query(CaseComment.status, func.count(CaseComment.id))
                     .group_by(CaseComment.status).all())
    return _render(request, "admin/cases_comentarios.html", {
        "comentarios": lista, "status": status, "contagens": contagens,
        "csrf": csrf_token(request),
    })


@router.post("/comentarios/{cid}/{acao}")
async def moderar(cid: int, acao: str, request: Request, db: Session = Depends(get_db),
                  _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    c = db.get(CaseComment, cid)
    if c:
        if acao == "excluir":
            db.delete(c)
        elif acao in ("aprovado", "pendente", "spam"):
            c.status = acao
            registrar(db, acao, "comentario", c.name,
                      detalhe=(c.case.title_pt if c.case else ""),
                      url="/admin/cases/comentarios")
        db.commit()
    return RedirectResponse(request.headers.get("referer", "/admin/cases/comentarios"),
                            status_code=303)


# ---------------------------------------------------------------- categorias

@router.get("/categorias")
async def categorias(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    # a ordem é calculada, não digitada: mais cases primeiro, empate no alfabeto
    cats = cats_svc.reordenar(db)
    db.commit()

    vistos = _contagem_views(db)
    numeros = {}
    for cat in cats:
        seus = list(cat.cases)
        numeros[cat.id] = {
            "total": len(seus),
            "publicados": len([c for c in seus if c.published and not c.archived]),
            "rascunhos": len([c for c in seus if not c.published and not c.archived]),
            "vistos": sum(vistos.get(c.id, 0) for c in seus),
        }
    topo = max([n["total"] for n in numeros.values()] or [0])
    return _render(request, "admin/cases_categorias.html", {
        "categories": cats, "numeros": numeros, "topo": topo, "csrf": csrf_token(request),
        "sem_categoria": db.query(Case).filter(Case.category_id.is_(None)).count(),
    })


@router.post("/categorias/salvar")
async def categoria_salvar(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                           id: str = Form(""), name_pt: str = Form(...),
                           kind: str = Form(""), csrf: str = Form("")):
    check_csrf(request, csrf)
    nome = name_pt.strip()
    if nome:
        cat = db.get(Category, int(id)) if id.isdigit() else None
        if not cat:
            base = slugify(nome) or "categoria"
            chave, n = base, 2
            while db.query(Category).filter_by(slug=chave).first():
                chave, n = f"{base}-{n}", n + 1
            cat = Category(slug=chave)
            db.add(cat)
        cat.name_pt = nome
        # o nome em inglês deixou de ser campo: sai da tabela de tradução, e o
        # que ela não conhece continua valendo em português nos dois idiomas
        cat.name_en = traduz.categoria(nome)
        cat.kind = "sites" if kind == "sites" else ""
        registrar(db, "editou" if id.isdigit() else "criou", "categoria", cat.name_pt,
                  url="/admin/cases/categorias")
        db.flush()
        cats_svc.reordenar(db)
        db.commit()
    return RedirectResponse("/admin/cases/categorias?salva=1", status_code=303)


@router.post("/categorias/{cat_id}/excluir")
async def categoria_excluir(cat_id: int, request: Request, db: Session = Depends(get_db),
                            _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    cat = db.get(Category, cat_id)
    if cat:
        # os cases não somem junto: ficam sem categoria, esperando outra
        for c in cat.cases:
            c.category_id = None
        registrar(db, "excluiu", "categoria", cat.name_pt, url="/admin/cases/categorias")
        db.delete(cat)
        db.flush()
        cats_svc.reordenar(db)
        db.commit()
    return RedirectResponse("/admin/cases/categorias?apagada=1", status_code=303)


# ---------------------------------------------------------------- clientes

@router.post("/clientes/novo")
async def cliente_novo(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                       name: str = Form(...), site: str = Form(""), volta: str = Form(""),
                       csrf: str = Form("")):
    """Cadastro rápido, chamado de dentro do formulário do case."""
    check_csrf(request, csrf)
    nome = name.strip()
    if nome:
        chave = slugify(nome)
        existente = db.query(Client).filter_by(slug=chave).first()
        if not existente and chave:
            db.add(Client(slug=chave, name=nome, site=site.strip()))
            registrar(db, "criou", "cliente", nome, url="/admin/brands")
            db.commit()
    return RedirectResponse(volta or "/admin/cases/lista", status_code=303)
