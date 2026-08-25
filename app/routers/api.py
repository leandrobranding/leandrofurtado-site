"""API de conteúdo: alimenta o site de fora do painel.

Serve para eu (Claude) publicar cases, posts e rascunhos de newsletter direto no
site em produção, sem o Leandro ter que recortar e colar no admin.

Autenticação por token fixo (`Authorization: Bearer …` ou `X-API-Key`), gerado em
Configurações → API e revogável a qualquer momento. O token é separado da senha do
admin de propósito: se vazar, revoga só ele e a conta continua intacta.

Limite deliberado: a API **não dispara** newsletter. Cria rascunho; o envio para
pessoas reais continua sendo um clique humano no painel.
"""
import datetime as dt
import secrets

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..database import get_db
from ..models import (Campaign, Case, Category, LinkedInPost, MediaItem,
                      NewsletterSub, Lead, Profile, SiteSetting, Tag)
from ..services.images import (apagar_arquivo_exato, delete_media_files,
                               save_upload, slugify)

router = APIRouter(prefix="/api/v1")

TOKEN_KEY = "api_token"


def get_api_token(db: Session) -> str:
    row = db.get(SiteSetting, TOKEN_KEY)
    return row.value if row else ""


def new_api_token() -> str:
    return "lf_" + secrets.token_urlsafe(40)


def require_token(request: Request, db: Session = Depends(get_db),
                  authorization: str = Header(""), x_api_key: str = Header("")) -> None:
    """Confere o token em tempo constante, para não vazar prefixo por timing."""
    expected = get_api_token(db)
    if not expected:
        raise HTTPException(503, "API desligada: gere um token em Configurações → API.")
    sent = x_api_key.strip()
    if not sent and authorization.lower().startswith("bearer "):
        sent = authorization[7:].strip()
    if not sent or not secrets.compare_digest(sent, expected):
        raise HTTPException(401, "Token inválido.")


Auth = Depends(require_token)


# ---------- leitura ----------

@router.get("/status")
async def status(db: Session = Depends(get_db), _=Auth):
    """Retrato do site: o que existe, o que falta e se os integrações estão de pé."""
    from .public import all_brands
    smap = {s.key: s.value for s in db.query(SiteSetting).all()}
    cases = db.query(Case).all()
    brands = all_brands(db)
    return {
        "ok": True,
        "base_url": settings.base_url,
        "now": dt.datetime.now(dt.timezone.utc).isoformat(),
        "conteudo": {
            "cases_publicados": sum(1 for c in cases if c.published),
            "cases_rascunho": sum(1 for c in cases if not c.published),
            "cases_sem_capa": [c.slug for c in cases if not c.cover_image],
            "marcas": len(brands),
            "marcas_sem_logo": [b["name"] for b in brands if not b["logo"]],
            "linkedin_posts": db.query(LinkedInPost).count(),
            "campanhas": db.query(Campaign).count(),
        },
        "audiencia": {
            "assinantes": db.query(NewsletterSub).count(),
            "leads": db.query(Lead).count(),
            "leads_novos": db.query(Lead).filter_by(status="novo").count(),
        },
        # "configurado" = as credenciais existem. Se elas valem, só a chamada real diz.
        "integracoes_configuradas": {
            "smtp": bool(smap.get("smtp_host") and smap.get("smtp_user") and smap.get("smtp_password")),
            "instagram": bool(smap.get("ig_user_id") and smap.get("ig_access_token")),
        },
    }


def case_json(c: Case) -> dict:
    return {
        "slug": c.slug, "titulo_pt": c.title_pt, "titulo_en": c.title_en,
        "subtitulo_pt": c.subtitle_pt, "subtitulo_en": c.subtitle_en,
        "cliente": c.client, "ano": c.year,
        "categoria": c.category.slug if c.category else "",
        "tags": [t.name for t in c.tags],
        "capa": c.cover_image, "midias": len(c.media),
        "publicado": c.published, "destaque": c.featured,
        "url": f"{settings.base_url.rstrip('/')}/case/{c.slug}",
    }


@router.get("/cases")
async def list_cases(db: Session = Depends(get_db), _=Auth):
    cases = (db.query(Case).options(joinedload(Case.category), joinedload(Case.tags))
             .order_by(Case.sort, Case.created_at.desc()).all())
    return {"total": len(cases), "cases": [case_json(c) for c in cases]}


@router.get("/cases/{slug}")
async def get_case(slug: str, db: Session = Depends(get_db), _=Auth):
    case = db.query(Case).filter_by(slug=slug).first()
    if not case:
        raise HTTPException(404, "Case não encontrado.")
    data = case_json(case)
    data["corpo_pt"] = case.body_pt
    data["corpo_en"] = case.body_en
    data["midia"] = [{"id": m.id, "tipo": m.kind, "src": m.src,
                      "legenda_pt": m.caption_pt, "layout": m.layout} for m in case.media]
    return data


# ---------- escrita: cases ----------

FIELDS = {
    "titulo_pt": "title_pt", "titulo_en": "title_en",
    "subtitulo_pt": "subtitle_pt", "subtitulo_en": "subtitle_en",
    "cliente": "client", "ano": "year",
    "funcao_pt": "role_pt", "funcao_en": "role_en",
    "corpo_pt": "body_pt", "corpo_en": "body_en",
}


@router.post("/cases")
async def upsert_case(payload: dict, db: Session = Depends(get_db), _=Auth):
    """Cria ou atualiza um case. A chave é o slug; sem slug, ele nasce do título.

    Só mexe no que vier no corpo, então dá para mandar uma atualização parcial sem
    apagar o resto sem querer.
    """
    # slugify() devolve hex aleatório para string vazia, então só chama se veio algo
    raw_slug = str(payload.get("slug", "")).strip()
    slug = slugify(raw_slug) if raw_slug else ""
    case = db.query(Case).filter_by(slug=slug).first() if slug else None
    criado = case is None
    if case is None:
        case = Case(slug="", title_pt="")
        db.add(case)

    for chave, coluna in FIELDS.items():
        if chave in payload:
            setattr(case, coluna, str(payload[chave] or "").strip())

    if not case.title_pt and criado:
        raise HTTPException(400, "titulo_pt é obrigatório para criar um case.")

    if "categoria" in payload:
        cat = db.query(Category).filter_by(slug=slugify(str(payload["categoria"]))).first()
        if not cat and payload["categoria"]:
            raise HTTPException(400, f"Categoria '{payload['categoria']}' não existe.")
        case.category_id = cat.id if cat else None

    if "tags" in payload:
        tags = []
        for name in payload["tags"] or []:
            name = str(name).strip()
            if not name:
                continue
            s = slugify(name)
            tags.append(db.query(Tag).filter_by(slug=s).first() or Tag(slug=s, name=name))
        case.tags = tags

    if "destaque" in payload:
        case.featured = bool(payload["destaque"])

    if not case.slug:
        base = slug or slugify(case.title_pt or "case")
        s, i = base, 2
        while db.query(Case).filter(Case.slug == s, Case.id != case.id).first():
            s, i = f"{base}-{i}", i + 1
        case.slug = s

    # publicar é o último passo: só deixa se o case estiver apresentável
    if "publicado" in payload:
        quer_publicar = bool(payload["publicado"])
        if quer_publicar and not case.cover_image:
            raise HTTPException(400, "Não dá para publicar sem imagem de capa. "
                                     "Suba a capa primeiro em POST /cases/{slug}/capa.")
        if quer_publicar and not case.published:
            case.published_at = dt.datetime.now(dt.timezone.utc)
        case.published = quer_publicar

    db.commit()
    db.refresh(case)
    return {"ok": True, "criado": criado, "case": case_json(case)}


@router.post("/cases/{slug}/capa")
async def upload_cover(slug: str, db: Session = Depends(get_db), _=Auth,
                       file: UploadFile = File(...)):
    case = db.query(Case).filter_by(slug=slug).first()
    if not case:
        raise HTTPException(404, "Case não encontrado.")
    kind, rel, thumb = await save_upload(file, case.slug)
    if kind != "image":
        delete_media_files(rel, thumb)
        raise HTTPException(400, "A capa precisa ser uma imagem.")
    delete_media_files(case.cover_image)
    if thumb:
        # rel (o original) e thumb nascem do MESMO envio — mesma família.
        # delete_media_files varreria o thumb junto; só o original exato
        # precisa sumir. Porquê completo em apagar_arquivo_exato, em
        # app/services/images.py.
        apagar_arquivo_exato(rel)
    case.cover_image = thumb or rel
    db.commit()
    return {"ok": True, "capa": case.cover_image}


@router.post("/cases/{slug}/midia")
async def upload_media(slug: str, db: Session = Depends(get_db), _=Auth,
                       file: UploadFile = File(...),
                       legenda_pt: str = "", legenda_en: str = "", layout: str = "full"):
    case = db.query(Case).filter_by(slug=slug).first()
    if not case:
        raise HTTPException(404, "Case não encontrado.")
    kind, rel, thumb = await save_upload(file, case.slug)
    item = MediaItem(case_id=case.id, kind=kind, src=rel, thumb=thumb,
                     caption_pt=legenda_pt.strip(), caption_en=legenda_en.strip(),
                     layout=layout if layout in ("full", "half", "tall") else "full",
                     sort=len(case.media))
    db.add(item)
    db.commit()
    return {"ok": True, "id": item.id, "tipo": kind, "src": rel}


@router.delete("/cases/{slug}")
async def delete_case(slug: str, db: Session = Depends(get_db), _=Auth):
    case = db.query(Case).filter_by(slug=slug).first()
    if not case:
        raise HTTPException(404, "Case não encontrado.")
    for m in case.media:
        delete_media_files(m.src, m.thumb)
    delete_media_files(case.cover_image, case.cover_video)
    db.delete(case)
    db.commit()
    return {"ok": True, "removido": slug}


# ---------- escrita: LinkedIn ----------

@router.get("/linkedin")
async def list_linkedin(db: Session = Depends(get_db), _=Auth):
    posts = db.query(LinkedInPost).order_by(LinkedInPost.created_at.desc()).all()
    return {"total": len(posts),
            "posts": [{"id": p.id, "resumo": p.summary, "tag": p.tag, "url": p.url} for p in posts]}


@router.post("/linkedin")
async def create_linkedin(payload: dict, db: Session = Depends(get_db), _=Auth):
    resumo = str(payload.get("resumo", "")).strip()
    url = str(payload.get("url", "")).strip()
    if not resumo or not url:
        raise HTTPException(400, "resumo e url são obrigatórios.")
    post = LinkedInPost(summary=resumo[:400], tag=str(payload.get("tag", "")).strip()[:80], url=url[:500])
    db.add(post)
    db.commit()
    return {"ok": True, "id": post.id}


@router.delete("/linkedin/{post_id}")
async def delete_linkedin(post_id: int, db: Session = Depends(get_db), _=Auth):
    post = db.get(LinkedInPost, post_id)
    if not post:
        raise HTTPException(404, "Post não encontrado.")
    db.delete(post)
    db.commit()
    return {"ok": True}


# ---------- escrita: perfil / currículo ----------

@router.get("/perfil")
async def get_profile_api(db: Session = Depends(get_db), _=Auth):
    prof = db.get(Profile, 1)
    return prof.data if prof else {}


@router.patch("/perfil")
async def patch_profile(payload: dict, db: Session = Depends(get_db), _=Auth):
    """Mescla no primeiro nível: manda só a chave que mudou, o resto fica."""
    prof = db.get(Profile, 1)
    if not prof:
        prof = Profile(id=1, data={})
        db.add(prof)
    data = dict(prof.data or {})
    data.update(payload)
    prof.data = data
    db.commit()
    return {"ok": True, "chaves": sorted(data.keys())}


# ---------- escrita: newsletter (rascunho apenas) ----------

@router.post("/campanhas")
async def create_campaign(payload: dict, db: Session = Depends(get_db), _=Auth):
    """Cria a campanha como rascunho. O disparo continua sendo manual no painel."""
    assunto = str(payload.get("assunto", "")).strip()
    if not assunto:
        raise HTTPException(400, "assunto é obrigatório.")
    aud = str(payload.get("publico", "todos"))
    camp = Campaign(
        subject=assunto[:200],
        preheader=str(payload.get("previa", "")).strip()[:200],
        body=str(payload.get("corpo", "")),
        cta_label=str(payload.get("botao_texto", "")).strip()[:80],
        cta_url=str(payload.get("botao_url", "")).strip()[:400],
        audience=aud if aud in ("todos", "assinantes", "leads", "clientes") else "todos",
        status="rascunho",
    )
    db.add(camp)
    db.commit()
    return {"ok": True, "id": camp.id, "status": "rascunho",
            "revisar_em": f"{settings.base_url.rstrip('/')}/admin/newsletter/{camp.id}",
            "nota": "Criada como rascunho. O envio é um clique humano no painel."}
