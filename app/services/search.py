"""Busca do site: índice em memória, scoring com pesos e busca por imagem.

O índice cobre cases publicados, categorias, páginas fixas, perfil (experiências,
skills, certificações, prêmio) e postagens do LinkedIn. Tolerante a acento e
caixa; título pesa mais que subtítulo, que pesa mais que corpo.

Nada aqui depende de serviço externo: texto e imagem são resolvidos no servidor,
sem chave de API e sem custo por consulta.
"""

import re
import unicodedata

from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models import Case, Category, LinkedInPost, Profile
from . import vitrine

_WORD_RE = re.compile(r"[\wÀ-ÿ]+")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _tokens(s: str) -> list[str]:
    return [t for t in _WORD_RE.findall(_norm(s)) if len(t) >= 2]


PAGES = {
    "pt": [
        ("Início", "Engenharia de IA e Direção de Arte", "/",
         "home inicio hero engenharia de ia direcao de arte diretor senior curitiba brasil portfolio"),
        ("Portfólio", "Todos os cases e projetos", "/portfolio",
         "portfolio trabalhos cases projetos key visual branding campanhas ui motion fotografia"),
        ("Sobre", "Trajetória, experiência, currículo e skills", "/about",
         "sobre biografia trajetoria experiencia carreira skills habilidades timeline historia "
         "curriculo cv resume pdf imprimir formacao download"),
        ("Contato", "Vamos conversar sobre o seu projeto", "/contato",
         "contato email whatsapp mensagem orcamento projeto briefing conversar"),
        ("Galeria de Honra", "Marcas e clientes atendidos", "/clientes",
         "clientes marcas logos coca-cola electrolux madeiramadeira hospital marcelino champagnat"),
        ("Política de Privacidade", "LGPD, cookies e dados", "/privacidade",
         "privacidade lgpd gdpr cookies dados pessoais politica"),
        ("Mapa do site", "Todas as páginas em um lugar", "/mapa-do-site",
         "mapa do site sitemap navegacao paginas links"),
    ],
    "en": [
        ("Home", "AI Engineering & Art Direction", "/",
         "home hero ai engineering art direction senior director curitiba brazil portfolio"),
        ("Portfolio", "All cases and projects", "/portfolio",
         "portfolio work cases projects key visual branding campaigns ui motion photography"),
        ("About", "Career, experience, résumé and skills", "/about",
         "about biography career experience skills timeline story "
         "resume cv pdf print education download"),
        ("Contact", "Let's talk about your project", "/contato",
         "contact email whatsapp message quote project briefing talk"),
        ("Hall of Honor", "Brands and clients", "/clientes",
         "clients brands logos coca-cola electrolux madeiramadeira hospital marcelino champagnat"),
        ("Privacy Policy", "LGPD, GDPR, cookies and data", "/privacidade",
         "privacy lgpd gdpr cookies personal data policy"),
        ("Sitemap", "Every page in one place", "/mapa-do-site",
         "sitemap navigation pages links"),
    ],
}


def _lp(lang: str, path: str) -> str:
    return ("/en" + (path if path != "/" else "")) if lang == "en" else path


def _field(obj, name: str, lang: str) -> str:
    if lang == "en":
        val = getattr(obj, f"{name}_en", "") or ""
        if val.strip():
            return val
    return getattr(obj, f"{name}_pt", "") or ""


def build_docs(db: Session, lang: str) -> list[dict]:
    docs: list[dict] = []

    cases = (
        db.query(Case)
        .options(joinedload(Case.category), joinedload(Case.tags))
        .filter(Case.published.is_(True))
        .order_by(Case.sort)
        .all()
    )
    for c in cases:
        tags = " ".join(t.name for t in c.tags)
        cat = _field(c.category, "name", lang) if c.category else ""
        # site abre em aba nova e aponta para o endereço do cliente: o resultado
        # da busca leva ao mesmo lugar que o card do portfólio levaria
        site = vitrine.eh_site(c)
        docs.append({
            "group": "cases",
            "title": _field(c, "title", lang),
            "sub": " ·︎ ".join(x for x in (c.client, cat, c.year) if x),
            "url": c.site_url if site else _lp(lang, f"/case/{c.slug}"),
            "external": bool(site),
            "thumb": vitrine.capa(c),
            "text": " ".join((_field(c, "subtitle", lang), _field(c, "role", lang),
                              _field(c, "body", lang), tags, cat, c.client,
                              vitrine.host(c))),
            "w": 1.3,
        })

    for cat in db.query(Category).order_by(Category.sort).all():
        name = _field(cat, "name", lang)
        docs.append({
            "group": "pages", "title": name,
            "sub": "Categoria de trabalhos" if lang == "pt" else "Work category",
            "url": _lp(lang, "/portfolio") + f"?c={cat.slug}", "thumb": "",
            "text": f"categoria category {name}", "w": 1.0,
        })

    for title, sub, path, text in PAGES.get(lang, PAGES["pt"]):
        docs.append({"group": "pages", "title": title, "sub": sub,
                     "url": _lp(lang, path), "thumb": "", "text": text, "w": 1.0})

    prof = db.get(Profile, 1)
    data = prof.data if prof else {}
    for xp in data.get("experience", []):
        role = xp.get(f"role_{lang}") or xp.get("role_pt", "")
        company = xp.get("company", "")
        docs.append({
            "group": "profile", "title": f"{role} ·︎ {company}" if company else role,
            "sub": xp.get("period", ""),
            "url": _lp(lang, "/about") + "#experiencia", "thumb": "",
            "text": " ".join((xp.get(f"desc_{lang}") or xp.get("desc_pt", ""),
                              str(xp.get("clients", "")))),
            "w": 1.0,
        })
    for grp in data.get("skills", []):
        items = grp.get("items", [])
        name = grp.get(f"group_{lang}") or grp.get("group_pt", "")
        if not items:
            continue
        docs.append({
            "group": "profile", "title": name,
            "sub": ", ".join(items[:6]) + ("…" if len(items) > 6 else ""),
            "url": _lp(lang, "/about"), "thumb": "",
            "text": "skills habilidades ferramentas tools " + " ".join(items), "w": 1.0,
        })
    for cert in data.get("certs", []):
        docs.append({
            "group": "profile",
            "title": cert.get("title", ""),
            "sub": " ·︎ ".join(x for x in (cert.get("org", ""), str(cert.get("year", ""))) if x),
            "url": _lp(lang, "/about") + "#certificacoes", "thumb": "",
            "text": "certificacao certification curso " + cert.get("org", ""), "w": 1.0,
        })
    for award in data.get("awards", []):
        title = award.get(f"title_{lang}") or award.get("title_pt", "")
        desc = award.get(f"desc_{lang}") or award.get("desc_pt", "")
        docs.append({
            "group": "profile", "title": title, "sub": desc,
            "url": _lp(lang, "/about") + "#certificacoes", "thumb": "",
            "text": "premio award " + desc, "w": 1.0,
        })

    for post in db.query(LinkedInPost).order_by(LinkedInPost.created_at.desc()).all():
        docs.append({
            "group": "linkedin", "title": post.tag or "LinkedIn",
            "sub": post.summary, "url": post.url, "thumb": "",
            "text": "linkedin post publicacao " + post.summary, "w": 0.9, "external": True,
        })

    return docs


def _match(term: str, words: set[str], raw: str, exact: float, prefix: float, sub: float) -> float:
    """Pontua um termo contra um campo: palavra exata > prefixo > substring (só p/ termos ≥4)."""
    if term in words:
        return exact
    if any(w.startswith(term) for w in words):
        return prefix
    if len(term) >= 4 and term in raw:
        return sub
    return 0.0


def _score(doc: dict, terms: list[str]) -> float:
    title, sub, text = _norm(doc["title"]), _norm(doc["sub"]), _norm(doc["text"])
    tw = set(_WORD_RE.findall(title))
    sw = set(_WORD_RE.findall(sub))
    xw = set(_WORD_RE.findall(text))
    score, hits = 0.0, 0
    for term in terms:
        best = _match(term, tw, title, 10.0, 7.0, 4.0)
        best = max(best, _match(term, sw, sub, 3.0, 2.5, 2.0))
        best = max(best, _match(term, xw, text, 1.5, 1.2, 1.0))
        if best:
            hits += 1
            score += best
    if not hits:
        return 0.0
    if hits == len(terms) and len(terms) > 1:
        score *= 1.6  # todos os termos presentes
    return score * doc["w"]


GROUP_LABELS = {
    "pt": {"cases": "Cases", "pages": "Páginas", "profile": "Perfil & Currículo", "linkedin": "LinkedIn"},
    "en": {"cases": "Cases", "pages": "Pages", "profile": "Profile & Résumé", "linkedin": "LinkedIn"},
}


def run_search(db: Session, q: str, lang: str, limit: int = 24) -> list[dict]:
    terms = _tokens(q)[:8]
    if not terms:
        return []
    scored = []
    for doc in build_docs(db, lang):
        s = _score(doc, terms)
        if s > 0:
            scored.append((s, doc))
    scored.sort(key=lambda x: -x[0])
    scored = scored[:limit]

    labels = GROUP_LABELS.get(lang, GROUP_LABELS["pt"])
    groups: dict[str, dict] = {}
    for s, doc in scored:
        g = groups.setdefault(doc["group"], {"key": doc["group"], "label": labels[doc["group"]], "items": []})
        g["items"].append({k: doc.get(k, "") for k in ("title", "sub", "url", "thumb", "external")})
    order = ("cases", "pages", "profile", "linkedin")
    return [groups[k] for k in order if k in groups]


IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
IMAGE_MAX_BYTES = 8 * 1024 * 1024


def buscar_por_imagem(db: Session, dados: bytes, lang: str, limite: int = 12) -> dict:
    """Acha os cases visualmente parecidos com a imagem enviada.

    Compara contra a capa e as imagens da galeria de cada case publicado, e fica
    com a melhor nota de cada um: basta uma peça bater para o case entrar.
    """
    from .imagem import CORTE, assinatura_de_arquivo, assinatura_de_bytes, semelhanca

    alvo = assinatura_de_bytes(dados)
    if not alvo:
        return {"ok": False, "erro": "ilegivel"}

    raiz = settings.upload_dir
    melhores: dict[int, float] = {}

    cases = (db.query(Case).options(joinedload(Case.category), joinedload(Case.media))
             .filter(Case.published.is_(True)).order_by(Case.sort).all())

    for c in cases:
        arquivos = [c.cover_image] if c.cover_image else []
        for m in c.media:
            if m.kind == "image":
                arquivos.append(m.thumb or m.src)
        for rel in arquivos:
            if not rel or "://" in rel:
                continue
            # o caminho vem do banco, mas confere-se que não escapa da pasta
            caminho = (raiz / rel).resolve()
            if not str(caminho).startswith(str(raiz.resolve())) or not caminho.is_file():
                continue
            assinatura = assinatura_de_arquivo(caminho)
            if not assinatura:
                continue
            nota = semelhanca(alvo, assinatura)
            if nota > melhores.get(c.id, 0.0):
                melhores[c.id] = nota

    achados = sorted(((n, c) for c in cases if (n := melhores.get(c.id, 0.0)) >= CORTE),
                     key=lambda x: -x[0])[:limite]
    if not achados:
        return {"ok": True, "grupos": [], "melhor": 0.0}

    labels = GROUP_LABELS.get(lang, GROUP_LABELS["pt"])
    itens = []
    for nota, c in achados:
        cat = _field(c.category, "name", lang) if c.category else ""
        site = vitrine.eh_site(c)
        itens.append({
            "title": _field(c, "title", lang),
            "sub": " ·︎ ".join(x for x in (c.client, cat, c.year) if x),
            "url": c.site_url if site else _lp(lang, f"/case/{c.slug}"),
            "thumb": vitrine.capa(c),
            "external": bool(site),
            "match": round(nota * 100),
        })
    return {"ok": True, "melhor": round(achados[0][0] * 100),
            "grupos": [{"key": "cases", "label": labels["cases"], "items": itens}]}
