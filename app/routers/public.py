import datetime as dt
import re

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, Request, UploadFile)
from fastapi.responses import (FileResponse, PlainTextResponse,
                               RedirectResponse, Response)
from sqlalchemy.orm import Session, joinedload

from ..auth import check_csrf
from ..config import BASE_DIR, settings
from ..i18n import field as campo_bilingue
from ..database import get_db
from ..models import (Case, Category, ContactMessage, Lead, LinkedInPost,
                      NewsletterSub, Profile, SiteSetting, Tag)
from ..services import anti_spam
from ..services import categorias as cats_svc
from ..services import seo as seo_svc
from ..services import logos as logos_svc
from ..services import vitrine
from ..services.atividade import registrar
from ..services.geo import ip_confiavel

router = APIRouter()


def get_settings_map(db: Session) -> dict:
    return {s.key: s.value for s in db.query(SiteSetting).all()}


def get_profile(db: Session) -> dict:
    prof = db.get(Profile, 1)
    return prof.data if prof else {}


def published_cases(db: Session):
    """Cases que o site mostra: publicados e não arquivados.

    O arquivamento já tira a publicação, mas o filtro fica aqui também: é este
    o ponto por onde todo o site pergunta "o que está no ar", e depender de dois
    campos concordarem é como um trabalho arquivado reaparece um dia.
    """
    return (
        db.query(Case)
        .options(joinedload(Case.category), joinedload(Case.client_ref), joinedload(Case.tags))
        .filter(Case.published.is_(True), Case.archived.is_(False))
        .order_by(Case.sort, Case.created_at.desc())
    )


def base_ctx(db: Session) -> dict:
    return {"site": get_settings_map(db), "profile": get_profile(db)}


# Rodada 3 (19/08, item 7): abaixo do limiar o trilho some por inteiro — uma
# fileira pela metade parece abandono, não vitrine.
IG_MIN_POSTS = 6


def posts_completos(items: list[dict]) -> list[dict]:
    """Um post "completo" tem os dois dados que o trilho precisa para
    desenhar um tile clicável de verdade: a imagem e o link do próprio post
    (não um link genérico de reserva). Os tiles de marcação usados antes de
    o Instagram estar configurado sempre passam neste filtro — cada um leva
    ao perfil, que é o link que existe até o primeiro post real chegar."""
    return [i for i in items if i.get("img") and i.get("link")]


async def get_ig_feed(db: Session, smap: dict) -> list[dict]:
    """Feed real da conta (cache de 1h) ou tiles de marcação até o token existir.

    Rodada 3, item 7: o trilho só aparece com 6+ posts completos. Isso vale
    para o feed real vindo da API — hoje a conta tem só 2 posts publicados,
    então o trilho fica ausente até o sexto chegar, em vez de mostrar uma
    fileira capenga. Os tiles de marcação (sem token/ig_user_id configurado
    ainda) continuam os de sempre: já são 6, e sempre foram decorativos, não
    posts reais — não fazem sentido também sumir por terem "poucos posts".
    """
    import json as _json
    import time
    placeholder = [{"img": f"/static/img/ig/tile{i}.webp",
                    "link": smap.get("social_instagram", "#")} for i in range(6)]
    if not (smap.get("ig_user_id") and smap.get("ig_access_token")):
        return placeholder

    def _limiar(items: list[dict]) -> list[dict]:
        completos = posts_completos(items)
        return completos if len(completos) >= IG_MIN_POSTS else []

    cache_row = db.get(SiteSetting, "ig_feed_cache")
    if cache_row:
        try:
            cached = _json.loads(cache_row.value)
            if time.time() - cached.get("ts", 0) < 3600 and "items" in cached:
                return _limiar(cached["items"])
        except Exception:
            pass
    try:
        from ..services.instagram import fetch_feed
        items = await fetch_feed(smap["ig_user_id"], smap["ig_access_token"], limit=6)
        payload = _json.dumps({"ts": time.time(), "items": items})
        if cache_row:
            cache_row.value = payload
        else:
            db.add(SiteSetting(key="ig_feed_cache", value=payload))
        db.commit()
        return _limiar(items)
    except Exception:
        # API fora do ar: melhor o trilho ausente que um erro visível ou um
        # fallback de marcação por cima de uma conta já conectada.
        return []


# Rodada 3, item 11 (19/08): mosaico de capas na home, uma fita densa de
# ~20 colunas numa linha só (o dono corrigiu o próprio pedido de 2 linhas
# depois de ver o WIP: "ficaria mais bonito, viajei falando duas linhas").
MOSAIC_TILES = 20


def mosaic_covers(cases: list) -> list[str]:
    """Capas dos cases publicados para o mosaico decorativo da home.

    Com menos capas que ladrilhos, repete em loop até preencher a fita —
    com mais, usa só as N primeiras. Sem capa nenhuma cadastrada, devolve
    lista vazia (o template não desenha a fita, só o botão continua).
    """
    from itertools import cycle, islice
    capas = [c.cover_image for c in cases if c.cover_image]
    if not capas:
        return []
    return list(islice(cycle(capas), MOSAIC_TILES))


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    from ..config import BASE_DIR
    from ..main import render
    from ..services.images import slugify
    cases = published_cases(db).all()
    # Site não vai para o destaque da home. O destaque é uma vitrine de trabalho
    # autoral com página própria; um card que joga a pessoa para fora do site na
    # primeira dobra é uma saída, não uma vitrine. O painel também não deixa
    # marcar, e o template ainda sabe desenhar o card de site caso um chegue
    # aqui por dado antigo — melhor mostrar a prévia certa que um vão preto.
    proprios = [c for c in cases if not vitrine.eh_site(c)]
    # `destaque_ordem` é a ordem que o dono escolhe a dedo no painel. `sorted`
    # é estável, então quem empata (a maioria: default 999) mantém a ordem que
    # já vinha de `cases` — sort/created_at — em vez de embaralhar.
    featured = sorted((c for c in proprios if c.featured),
                      key=lambda c: c.destaque_ordem) or proprios[:6]
    ctx = base_ctx(db)
    # marca=cliente: perfil + clientes de cases, logo SVG ou wordmark no template.
    # No trilho da home entram só as marcadas para isso no painel.
    clients = [b for b in all_brands(db) if b.get("na_home", True)]
    return render(request, "home.html", {
        **ctx, "featured": featured[:6], "total_cases": len(cases),
        "categories": cats_svc.publicas(db, getattr(request.state, "lang", "pt")),
        "clients": clients, "ig_feed": await get_ig_feed(db, ctx["site"]),
        "li_posts": db.query(LinkedInPost).order_by(LinkedInPost.created_at.desc()).limit(6).all(),
        "mosaic_covers": mosaic_covers(cases),
    })


PER_PAGE = 20  # acima disso a listagem pagina

ORDENS_VALIDAS = ("recentes", "az", "za")


def ordenar_portfolio(cases: list, ordem: str, lang: str) -> list:
    """A ordem de exibição do portfólio, escolhida pela querystring `ordem`.

    `recentes` (padrão) é o mais novo cadastrado primeiro — por `created_at`,
    não por `Case.sort`: a ordem manual do painel continua valendo fora do
    portfólio (home, destaques), mas aqui quem decide é a data de cadastro ou
    o alfabeto, nunca mais um número escondido no painel. `az`/`za` comparam
    o título no idioma da própria página (`field()`), então a régua alfabética
    muda com o idioma — "Zebra" em pt pode ser "Antelope" em en.

    Ordem desconhecida cai no padrão, do mesmo jeito que uma categoria que não
    existe na querystring vira "todas" em vez de erro: link velho ou digitado
    errado não pode quebrar a página.
    """
    from ..i18n import field
    if ordem == "az":
        return sorted(cases, key=lambda x: _alfabetica(field(x, "title", lang)))
    if ordem == "za":
        return sorted(cases, key=lambda x: _alfabetica(field(x, "title", lang)), reverse=True)
    return sorted(cases, key=lambda x: x.created_at, reverse=True)


@router.get("/portfolio")
async def portfolio(request: Request, db: Session = Depends(get_db),
                    c: str = "", tag: str = "", cliente: str = "",
                    agencia: str = "", ordem: str = "recentes", p: int = 1):
    from ..main import render
    lang = getattr(request.state, "lang", "pt")
    if ordem not in ORDENS_VALIDAS:
        ordem = "recentes"
    all_published = published_cases(db).all()
    counts = {}
    for case in all_published:
        if case.category_id:
            counts[case.category_id] = counts.get(case.category_id, 0) + 1
    cat_obj = db.query(Category).filter_by(slug=c).first() if c else None
    filtered = [x for x in all_published if not cat_obj or x.category_id == cat_obj.id]
    if tag:
        filtered = [x for x in filtered if any(t.slug == tag for t in x.tags)]
    if cliente:
        filtered = [x for x in filtered
                    if (x.client_ref and x.client_ref.slug == cliente)]
    # filtro por casa onde o trabalho foi feito. O crédito vem da ficha técnica
    # do case, não de um campo de cadastro (ver services/creditos.py).
    if agencia:
        from ..services.creditos import agencia_do_case, chave
        filtered = [x for x in filtered if chave(agencia_do_case(x)) == chave(agencia)]
    filtered = ordenar_portfolio(filtered, ordem, lang)

    pages = max(1, -(-len(filtered) // PER_PAGE))  # divisão para cima
    page = min(max(p, 1), pages)
    start = (page - 1) * PER_PAGE
    cases = filtered[start:start + PER_PAGE]

    # querystring dos filtros ativos (sem a ordem), para os links de ordenação
    # não perderem o contexto dos outros filtros
    filtros_qs = "".join(f"&{k}={v}" for k, v in
                         (("c", c), ("tag", tag), ("cliente", cliente),
                          ("agencia", agencia)) if v)
    # querystring completa, para os links de página não perderem filtro nem ordem
    base_qs = filtros_qs + (f"&ordem={ordem}" if ordem != "recentes" else "")
    # só o que existe entre os cases publicados vira opção: filtro que não
    # devolve nada é uma promessa quebrada na cara de quem clicou
    vistos_cli = {}
    for x in all_published:
        if x.client_ref:
            vistos_cli[x.client_ref.slug] = x.client_ref.name
    return render(request, "portfolio.html", {
        **base_ctx(db), "cases": cases, "counts": counts, "total": len(all_published),
        "categories": cats_svc.publicas(db, lang),
        "active_cat": c, "active_cat_obj": cat_obj, "active_tag": tag,
        "clientes": sorted(vistos_cli.items(), key=lambda kv: kv[1]),
        "active_cliente": cliente, "active_agencia": agencia, "ordem": ordem,
        "filtered_total": len(filtered), "page": page, "pages": pages,
        "base_qs": base_qs, "filtros_qs": filtros_qs,
        "range_from": start + 1 if cases else 0,
        "range_to": start + len(cases),
    })


def registrar_acesso(db: Session, case_id: int) -> None:
    """Soma um acesso ao case no dia de hoje.

    Uma linha por case por dia. Não guarda IP, não identifica quem entrou e não
    liga uma visita à seguinte: para saber que um case teve 40 aberturas numa
    terça não é preciso saber quem foram as 40 pessoas.

    Falha em silêncio de propósito: uma contagem que não gravou é um número
    ligeiramente menor no painel, e isso nunca justifica derrubar a página que
    a pessoa veio ver.
    """
    from ..config import agora_daqui
    from ..models import CaseView
    hoje = agora_daqui().date().isoformat()
    try:
        linha = db.query(CaseView).filter_by(case_id=case_id, day=hoje).first()
        if linha:
            linha.hits += 1
        else:
            db.add(CaseView(case_id=case_id, day=hoje, hits=1))
        db.commit()
    except Exception:
        db.rollback()


# Marca reversa sobre chapa de cor: as letras são brancas DENTRO de um campo
# colorido. O tratamento padrão do site (brightness(0) + invert) pinta tudo de
# branco e o logo vira um borrão — campo e letra ficam da mesma cor. Estas
# recebem outro tratamento, que preserva o contraste interno do desenho.
#
# Quem responde é o próprio arquivo (services/logos.reversa). Era uma lista de
# dois slugs escrita à mão, e lista à mão só protege o que já aconteceu: a marca
# reversa seguinte entraria quebrada até alguém reparar e editar o código.
# O conjunto abaixo continua valendo como exceção manual, para o caso de um
# arquivo que a leitura não consiga classificar sozinha.
LOGOS_CHAPA: set[str] = set()


def eh_chapa(slug: str) -> bool:
    """A marca deste slug é reversa sobre campo de cor?"""
    if slug in LOGOS_CHAPA:
        return True
    arquivo = _arquivo_do_logo(slug)
    return bool(arquivo) and logos_svc.reversa(arquivo)


def logo_do_slug(slug: str) -> str:
    """Endereço do logotipo, procurando nos dois lugares onde ele pode estar.

    Um logo enviado pelo painel mora em `data/uploads/clients` e sobrevive ao
    deploy; um versionado no repositório mora em `app/static/img/clients`. O
    enviado ganha, porque é a ação mais recente e deliberada de quem administra.

    O envio ia para dentro do código, e o `rsync --delete` do deploy apagava
    tudo que tinha sido enviado pelo painel. Um upload que some no próximo
    deploy é pior que um upload que não existe.
    """
    return logo_e_escala(slug)[0]


def logo_e_escala(slug: str) -> tuple[str, float]:
    """Endereço do logotipo e o quanto ele precisa crescer para pesar igual.

    A escala sai da proporção do próprio arquivo (ver services/logos.py): a
    fileira alinha por altura, e um logo empilhado à mesma altura de uma
    assinatura horizontal fica ilegível.
    """
    from ..config import BASE_DIR, settings
    from ..services.logos import escala
    if not slug:
        return "", 1.0
    enviado = settings.upload_dir / "clients" / f"{slug}.svg"
    if enviado.exists():
        return f"/media/clients/{slug}.svg", escala(enviado)
    versionado = BASE_DIR / "app" / "static" / "img" / "clients" / f"{slug}.svg"
    if versionado.exists():
        return f"/static/img/clients/{slug}.svg", escala(versionado)
    return "", 1.0


# Acima disto a marca é uma assinatura horizontal; abaixo, um lockup compacto.
# O corte cai num vão real do acervo: as compactas param em 1,83 e as
# horizontais começam em 2,60, então nenhuma marca fica em cima da linha.
PROP_HORIZONTAL = 2.2


def marca_do_cliente(client: str) -> dict:
    """Tudo que a tela precisa para desenhar a marca de um cliente.

    Reunido num lugar só porque antes cada página montava o seu: a do cliente
    passava escala e chapa, a do case passava só o endereço do arquivo, e o
    mesmo logotipo aparecia sem equilíbrio óptico e sem tratamento de cor
    dependendo de onde estivesse.
    """
    from ..services.images import slugify
    from ..services.logos import proporcao

    slug = slugify(client) if client else ""
    logo, escala = logo_e_escala(slug)
    prop = proporcao(_arquivo_do_logo(slug)) if logo else 0.0
    return {
        "slug": slug, "logo": logo, "escala": escala,
        "chapa": eh_chapa(slug),
        "prop": prop,
        "formato": "larga" if prop >= PROP_HORIZONTAL else "compacta",
    }


def _arquivo_do_logo(slug: str):
    # mesmo par de caminhos de `logo_e_escala`: enviado pelo painel primeiro,
    # versionado no repositório depois
    from ..config import BASE_DIR, settings

    enviado = settings.upload_dir / "clients" / f"{slug}.svg"
    if enviado.exists():
        return enviado
    return BASE_DIR / "app" / "static" / "img" / "clients" / f"{slug}.svg"


def client_slug_logo(client: str) -> tuple[str, str]:
    """Compatibilidade: só o slug e o endereço."""
    m = marca_do_cliente(client)
    return m["slug"], m["logo"]


@router.get("/case/{slug}")
async def case_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    from ..main import render
    case = (
        db.query(Case)
        .options(joinedload(Case.media), joinedload(Case.category), joinedload(Case.tags))
        .filter_by(slug=slug, published=True)
        .first()
    )
    if not case:
        raise HTTPException(404)

    # Categoria "sites" não tem página de case: o trabalho é o site em si, e
    # uma página intermediária só atrasaria quem quer ver o resultado. Quem
    # chegar aqui por link antigo ou por busca vai direto ao endereço real.
    if case.category and case.category.kind == "sites" and case.site_url:
        return RedirectResponse(case.site_url, status_code=307)

    registrar_acesso(db, case.id)

    cases = published_cases(db).all()
    ids = [x.id for x in cases]
    nxt = cases[(ids.index(case.id) + 1) % len(cases)] if case.id in ids and len(cases) > 1 else None
    # Relacionados.
    #
    # Card sem imagem é card vazio, então imagem de prévia é condição, não
    # preferência: quem não tem, não entra.
    #
    # Depois disso a regra muda com o que está aberto. Num site, o que interessa
    # é ver mais trabalho, de qualquer tipo. Fora dos sites, mostrar outro tipo
    # de case abre o leque em vez de repetir a mesma categoria que a pessoa
    # acabou de ver. Se não houver de outro tipo, vale qualquer um: melhor
    # relacionado repetido que espaço vazio.
    #
    # A ordem é sorteada a cada visita. Fixa, os mesmos quatro cases ficariam
    # para sempre no rodapé de todos os outros.
    import random

    candidatos = [c for c in cases if c.id != case.id and vitrine.capa(c)]
    if vitrine.eh_site(case):
        related = candidatos
    else:
        related = [c for c in candidatos if c.category_id != case.category_id] or candidatos
    random.shuffle(related)
    marca = marca_do_cliente(case.client)
    # `seo_title` e `seo_desc` são campos ÚNICOS, gravados em português pelo
    # painel. Enquanto title_en/subtitle_en estavam vazios isso não aparecia;
    # com o inglês preenchido (23/08/2026) a página /en passaria a servir
    # título e descrição em português. Aqui os dois saem no idioma da página,
    # da mesma fórmula, e o campo gravado segue alimentando a prévia do painel.
    _lang = getattr(request.state, "lang", "pt")
    if _lang == "pt":
        _seo_t, _seo_d = case.seo_title, case.seo_desc
    else:
        _seo_t = seo_svc.titulo_para_busca(
            campo_bilingue(case, "title", _lang), case.client or "")
        _seo_d = seo_svc.descricao_para_busca(
            campo_bilingue(case, "subtitle", _lang) or seo_svc.resumo_do_case(case),
            (case.category.name_pt if case.category else ""),
            case.client or "", case.year or "", _lang)
    return render(request, "case.html", {
        "seo_titulo": _seo_t, "seo_descricao": _seo_d,
        **base_ctx(db), "case": case, "next_case": nxt, "related": related[:4],
        "client_slug": marca["slug"], "client_logo": marca["logo"],
        "client_escala": marca["escala"], "client_chapa": marca["chapa"],
        "client_formato": marca["formato"],
    })


@router.get("/work")
async def work_redirect(request: Request):
    """URL antiga: 301 permanente para /portfolio, preservando filtros."""
    qs = request.url.query
    prefix = "/en" if getattr(request.state, "lang", "pt") == "en" else ""
    return RedirectResponse(f"{prefix}/portfolio" + (f"?{qs}" if qs else ""), status_code=301)


@router.get("/work/{slug}")
async def work_case_redirect(slug: str, request: Request):
    prefix = "/en" if getattr(request.state, "lang", "pt") == "en" else ""
    return RedirectResponse(f"{prefix}/case/{slug}", status_code=301)


@router.get("/cliente/{slug}")
async def client_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    """Busca reversa: tudo que foi feito para um cliente específico."""
    from ..main import render
    from ..services.images import slugify
    all_cases = published_cases(db).all()
    brands = {b["slug"]: b for b in all_brands(db)}
    cases = [c for c in all_cases if c.client and slugify(c.client) == slug]
    if cases:
        name = cases[0].client
    elif slug in brands:
        name = brands[slug]["name"]  # marca conhecida sem case ainda: página com estado vazio
    else:
        raise HTTPException(404)
    marca = marca_do_cliente(name)
    # Foto do hero: a capa do trabalho mais recente deste cliente. Sai do próprio
    # acervo em vez de uma arte fixa, então cada marca abre com o que foi feito
    # para ela, e a página nunca mostra imagem que não seja do trabalho.
    foto = next((c for c in cases if vitrine.capa(c)), None)
    # a ordem já vem alfabética de all_brands; aqui só tiramos a marca da própria página
    others = [b for b in brands.values() if b["slug"] != slug]
    return render(request, "client_detail.html", {
        # Descrição do Google montada aqui e não no template: a regra tem
        # orçamento de caracteres e três saídas (ver services/seo.py), e isso
        # em Jinja vira uma linha ilegível que ninguém consegue testar.
        "seo_desc_cliente": seo_svc.descricao_de_cliente(
            name,
            [campo_bilingue(c, "title", getattr(request.state, "lang", "pt")) for c in cases],
            getattr(request.state, "lang", "pt")),
        **base_ctx(db), "client_name": name, "client_logo": marca["logo"],
        "client_escala": marca["escala"], "client_chapa": marca["chapa"],
        "client_formato": marca["formato"], "hero_case": foto,
        "cases": cases, "others": others,
    })


@router.get("/cases/{case_id}/votes")
async def case_votes(case_id: int, db: Session = Depends(get_db)):
    import json as _json
    row = db.get(SiteSetting, "case_votes")
    try:
        data = _json.loads(row.value) if row else {}
    except Exception:
        data = {}
    return data.get(str(case_id), {"up": 0, "down": 0})


@router.post("/cases/vote")
async def case_vote(request: Request, db: Session = Depends(get_db)):
    import json as _json
    try:
        body = await request.json()
        case_id = int(body.get("id", -1))
        vote = str(body.get("vote", ""))
    except Exception:
        case_id, vote = -1, ""
    if vote not in ("up", "down") or not db.query(Case.id).filter_by(id=case_id, published=True).first():
        return {"ok": False}
    row = db.get(SiteSetting, "case_votes")
    try:
        data = _json.loads(row.value) if row else {}
    except Exception:
        data = {}
    entry = data.setdefault(str(case_id), {"up": 0, "down": 0})
    entry[vote] = entry.get(vote, 0) + 1
    payload = _json.dumps(data)
    if row:
        row.value = payload
    else:
        db.add(SiteSetting(key="case_votes", value=payload))
    db.commit()
    return {"ok": True, "votes": entry}


def _marcas_para_grade_sobre(marcas: list[dict]) -> list[dict]:
    """Recorte da grade de marcas do Sobre (item 3, 19/08): a grade é fixa em
    6 colunas (ver `.brands-grid` em main.css), então o corte nunca pode
    deixar uma linha pela metade. Com 12 ou mais marcas mostra 12 (duas
    linhas cheias — preferência do dono); com menos, mostra até 6 (uma linha
    cheia). A ordem/seleção de QUAIS marcas entram é a de `marcas` (mesmo
    critério de sempre, de all_brands); aqui só se decide o tamanho do
    corte.
    """
    if len(marcas) >= 12:
        return marcas[:12]
    return marcas[:6]


@router.get("/about")
async def about(request: Request, db: Session = Depends(get_db)):
    from ..main import render
    lang = getattr(request.state, "lang", "pt")
    today = dt.date.today()
    stamp = today.strftime("%d/%m/%Y") if lang == "pt" else today.strftime("%b %d, %Y")
    clients = _marcas_para_grade_sobre(all_brands(db))
    return render(request, "about.html", {**base_ctx(db), "clients": clients, "today": stamp})


@router.get("/cv")
async def cv(request: Request):
    """A página de currículo virou uma seção de /about (pacote de lançamento, ago/2026).

    301 permanente: quem tinha o link antigo (backlink, favorito, resultado já
    indexado) chega no mesmo lugar, e o Google transfere o valor de SEO para a
    URL nova em vez de aprender do zero. `/en/cv` cai aqui do mesmo jeito — o
    LangMiddleware já tirou o prefixo antes da rota, então basta devolver o
    caminho no idioma certo.
    """
    lang = getattr(request.state, "lang", "pt")
    from ..i18n import lp
    return RedirectResponse(lp(lang, "/about"), status_code=301)


@router.get("/cv/download.{fmt}")
async def cv_download(fmt: str, request: Request, db: Session = Depends(get_db), lang: str | None = None):
    """Currículo em PDF, gerado na hora a partir do Profile.

    Rodada 3 (19/08, item 4): o DOCX saiu de vez — decisão do dono ("pdf é
    universal") — qualquer `fmt` que não seja "pdf" é 404, sem exceção.
    O idioma virou escolha explícita do usuário na área de download do
    /about (os dois botões "Português"/"English" mandam ?lang=pt|en na
    própria URL); sem o parâmetro, ou com um valor que não seja pt/en,
    cai no idioma da página atual — o comportamento de antes, como
    default sensato para quem chega direto na rota.
    """
    from ..services.resume import build_pdf
    if fmt != "pdf":
        raise HTTPException(404)
    pagina_lang = getattr(request.state, "lang", "pt")
    lang = lang if lang in ("pt", "en") else pagina_lang
    profile = get_profile(db)
    name = "Leandro-Furtado-CV" + ("-EN" if lang == "en" else "")
    data = build_pdf(profile, lang)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{name}.pdf"',
        "Cache-Control": "no-store",
    })


def clients_case_slugs(db: Session) -> set[str]:
    """Slugs de clientes que têm case publicado (viram link de busca reversa)."""
    from ..services.images import slugify
    return {slugify(c.client) for c in published_cases(db).all() if c.client}


def clients_with_logos(db: Session) -> list[dict]:
    from ..config import BASE_DIR
    from ..services.images import slugify
    with_cases = clients_case_slugs(db)
    clients = []
    for name in get_profile(db).get("clients", []):
        slug = slugify(name)
        logo, esc = logo_e_escala(slug)
        if logo:
            clients.append({"name": name, "logo": logo, "escala": esc,
                            "slug": slug, "has_cases": slug in with_cases,
                            "chapa": eh_chapa(slug)})
    return clients


def _alfabetica(nome: str) -> str:
    """Chave de ordenação que ignora acento e caixa: Á vem junto de A."""
    import unicodedata
    plano = unicodedata.normalize("NFD", nome or "")
    return "".join(c for c in plano if unicodedata.category(c) != "Mn").lower()


def all_brands(db: Session, com_logo: bool = True) -> list[dict]:
    """Lógica marca=cliente: união dos clientes do perfil com os clientes de cases.

    Sempre em ordem alfabética. Antes saía na ordem em que foram cadastradas, o
    que não é ordem nenhuma para quem olha de fora — e mudava de lugar toda vez
    que uma marca nova entrava.

    `na_home` diz se a marca entra no trilho da primeira dobra. O padrão é sim;
    quem sai é escolhido no painel e fica guardado em `home_ocultos`.

    Marca sem arquivo de logotipo não sai daqui para o site. A alternativa que
    existia — desenhar o nome em tipografia no lugar da marca — é pior que não
    mostrar: numa fileira de logotipos reais, um nome escrito parece marca
    provisória e enfraquece as que estão ao lado. Só o painel vê essas
    (`com_logo=False`), justamente para poder enviar o arquivo que falta.
    """
    from ..services.images import slugify
    with_cases = clients_case_slugs(db)
    perfil = get_profile(db)
    ocultos = set(perfil.get("home_ocultos", []))

    brands: dict[str, dict] = {}
    for name in perfil.get("clients", []):
        s = slugify(name)
        logo, esc = logo_e_escala(s)
        brands[s] = {"name": name, "slug": s, "logo": logo, "escala": esc,
                     "has_cases": s in with_cases, "chapa": eh_chapa(s),
                     "na_home": s not in ocultos}
    for case in published_cases(db).all():
        if case.client:
            s = slugify(case.client)
            if s not in brands:
                logo, esc = logo_e_escala(s)
                brands[s] = {"name": case.client, "slug": s, "logo": logo, "escala": esc,
                             "has_cases": True, "chapa": eh_chapa(s),
                             "na_home": s not in ocultos}
    marcas = sorted(brands.values(), key=lambda b: _alfabetica(b["name"]))
    if not com_logo:
        return marcas
    # No site, marca precisa de logotipo E de trabalho publicado. Logotipo sem
    # case é uma promessa sem lastro: a pessoa clica esperando ver o que foi
    # feito e chega numa página vazia. No painel elas continuam todas.
    return [m for m in marcas if m["logo"] and m["has_cases"]]


# Colunas que a grade da Galeria de Honra usa em cada faixa de largura — ver
# `.hall-grid` e os media queries logo abaixo dela em main.css (desktop 6,
# 901–1200px 4, 561–900px 3, ≤560px 2). O preenchimento abaixo precisa
# conhecer exatamente essas contagens para fechar a última linha em TODAS
# elas, não só no desktop.
HALL_GRID_COLS = (6, 4, 3, 2)


def preenchimento_grade_clientes(total: int, colunas: tuple[int, ...] = HALL_GRID_COLS) -> dict[int, int]:
    """Quantas células de preenchimento a Galeria de Honra (/clientes) precisa
    em cada contagem de colunas para a ÚLTIMA LINHA nunca ficar pela metade
    (item 2 do pacote de 19/08, achado do dono: "fica vazio, sem graça").

    Diferente da grade de marcas do Sobre (`_marcas_para_grade_sobre`, que
    CORTA a lista pro tamanho que fecha a linha): aqui é a galeria COMPLETA
    — nenhuma marca pode ficar de fora. O que se ajusta é o preenchimento,
    não a seleção. `(-total) % c` dá a distância até o próximo múltiplo de
    `c` (0 quando `total` já é múltiplo — a linha fecha sozinha, nenhum
    preenchimento).
    """
    return {c: (-total) % c for c in colunas}


@router.get("/clientes")
async def clients_page(request: Request, db: Session = Depends(get_db)):
    from ..main import render
    clients = all_brands(db)
    preenchimento = preenchimento_grade_clientes(len(clients))
    return render(request, "clients.html", {
        **base_ctx(db), "clients": clients,
        "hall_fill": preenchimento, "hall_fill_max": max(preenchimento.values(), default=0),
    })


@router.get("/contato")
async def contact_page(request: Request, db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "contact.html", base_ctx(db))


# Validação de e-mail: o "tem arroba e ponto" deixava passar endereço com espaço,
# que grava no banco e depois falha no envio. Aqui é estrita o bastante para barrar
# lixo e frouxa o bastante para não recusar endereço válido esquisito.
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", re.I)

NL_CONSENT_TEXT = {
    "pt": ("Autorizo o cadastro do meu e-mail e o envio de novidades do site, conforme a "
           "LGPD (Lei 13.709/2018) e o GDPR (UE 2016/679). Posso pedir acesso, correção ou "
           "exclusão quando quiser, e todo e-mail traz link de descadastro."),
    "en": ("I authorize registering my email and receiving site updates, under LGPD "
           "(Law 13.709/2018) and GDPR (EU 2016/679). I may request access, correction or "
           "deletion at any time, and every email carries an unsubscribe link."),
}

CONSENT_TEXT = {
    "pt": ("Autorizo o contato e o tratamento dos meus dados para retorno desta mensagem e "
           "cadastro como contato, conforme a LGPD (Lei 13.709/2018) e o GDPR (UE 2016/679). "
           "Posso solicitar acesso, correção ou exclusão a qualquer momento."),
    "en": ("I authorize contact and the processing of my data to reply to this message and be "
           "registered as a contact, under LGPD (Law 13.709/2018) and GDPR (EU 2016/679). "
           "I may request access, correction or deletion at any time."),
}


@router.post("/contact")
async def contact(
    request: Request, background: BackgroundTasks, db: Session = Depends(get_db),
    name: str = Form(...), email: str = Form(...), message: str = Form(...),
    whatsapp: str = Form(""), consent: str = Form(""),
    website: str = Form(""),  # honeypot anti-spam
    t: str = Form(""),        # carimbo de tempo assinado (services/anti_spam.py)
):
    from ..config import daqui, settings as cfg
    from ..services.mailer import send_lead_email
    lang = request.state.lang
    lang_prefix = "/en" if lang == "en" else ""
    if website.strip():
        return RedirectResponse(f"{lang_prefix}/contato", status_code=303)

    # Camadas anti-bot (22/08/2026, depois do spam "Webmaster quer conversar"
    # que passou pelo honeypot). Spam detectado FINGE sucesso e não grava:
    # erro ensina o operador do bot a ajustar; sucesso falso o manda embora.
    # Cada barrado deixa rastro no registro de atividades, então uma decisão
    # errada é visível no painel e o texto perdido está lá.
    ip_bot = ip_confiavel(request)
    fingir_sucesso = RedirectResponse(f"{lang_prefix}/contato?sent=1", status_code=303)
    if not anti_spam.envio_permitido(ip_bot or "?"):
        registrar(db, "barrou", "spam", (name or "")[:80],
                  detalhe=f"contato: 4º envio em 15 min do IP {ip_bot}", do_site=True)
        db.commit()
        return fingir_sucesso
    if not anti_spam.carimbo_valido(t, cfg.secret_key):
        registrar(db, "barrou", "spam", (name or "")[:80],
                  detalhe="contato: enviado em menos de 4s ou sem abrir a página",
                  do_site=True)
        db.commit()
        return fingir_sucesso
    motivo = anti_spam.motivo_de_spam(name, email, message)
    if motivo:
        registrar(db, "barrou", "spam", (name or "")[:80],
                  detalhe=f"contato: {motivo} · {(message or '')[:80]}", do_site=True)
        db.commit()
        return fingir_sucesso

    name, email = name.strip()[:160], email.strip()[:200]
    message, whatsapp = message.strip()[:5000], whatsapp.strip()[:60]
    if not (name and email and message):
        return RedirectResponse(f"{lang_prefix}/contato?erro=1", status_code=303)
    if consent not in ("on", "1", "true"):  # sem aceite não há base legal para guardar
        return RedirectResponse(f"{lang_prefix}/contato?consent=1", status_code=303)

    now = dt.datetime.now(dt.timezone.utc)
    consent_text = CONSENT_TEXT.get(lang, CONSENT_TEXT["pt"])
    ip = ip_confiavel(request)
    lead = Lead(
        name=name, email=email, whatsapp=whatsapp, message=message, lang=lang,
        consent=True, consent_text=consent_text, consent_at=now,
        ip=ip[:64], user_agent=request.headers.get("user-agent", "")[:300],
    )
    db.add(lead)
    db.add(ContactMessage(name=name, email=email, message=message))  # caixa de mensagens
    registrar(db, "recebeu", "lead", name,
              detalhe=(message or "")[:160], url="/admin/leads", do_site=True)
    db.commit()
    db.refresh(lead)

    smap = get_settings_map(db)
    payload = {
        "name": name, "email": email, "whatsapp": whatsapp, "message": message,
        "when": daqui(now).strftime("%d/%m/%Y %H:%M"), "source": "contato",
        "lang": lang, "consent_text": consent_text, "ip": ip, "user_agent": lead.user_agent,
    }
    background.add_task(_notify_lead, lead.id, smap, payload, cfg.base_url)
    return RedirectResponse(f"{lang_prefix}/contato?sent=1", status_code=303)


def _notify_lead(lead_id: int, smap: dict, payload: dict, site_url: str) -> None:
    """Envio fora do ciclo da requisição: o visitante nunca espera pelo SMTP."""
    from ..database import SessionLocal
    from ..services.mailer import send_lead_email
    ok = send_lead_email(smap, payload, site_url)
    if not ok:
        return
    with SessionLocal() as db:
        lead = db.get(Lead, lead_id)
        if lead:
            lead.notified = True
            db.commit()


@router.post("/newsletter")
async def newsletter(request: Request, background: BackgroundTasks,
                     db: Session = Depends(get_db),
                     email: str = Form(...), website: str = Form(""),
                     consent: str = Form(""), t: str = Form("")):
    """Cadastro na newsletter, guardando a prova de consentimento igual aos leads."""
    from ..config import settings as cfg
    lang = request.state.lang
    lang_prefix = "/en" if lang == "en" else ""

    # Mesmas camadas de tempo e taxa do /contact (o filtro de conteúdo não se
    # aplica: aqui só existe e-mail). Pedido do Leandro em 22/08/2026, na
    # mesma conversa do spam do formulário de contato.
    ip_nl = ip_confiavel(request)
    fingir_ok = RedirectResponse(f"{lang_prefix}/?nl=1", status_code=303)
    if not anti_spam.envio_permitido(ip_nl or "?"):
        registrar(db, "barrou", "spam", (email or "")[:80],
                  detalhe=f"newsletter: 4º envio em 15 min do IP {ip_nl}", do_site=True)
        db.commit()
        return fingir_ok
    if not anti_spam.carimbo_valido(t, cfg.secret_key):
        registrar(db, "barrou", "spam", (email or "")[:80],
                  detalhe="newsletter: enviado em menos de 4s ou sem abrir a página",
                  do_site=True)
        db.commit()
        return fingir_ok
    email = email.strip().lower()[:200]
    valido = bool(EMAIL_RE.fullmatch(email))

    # o formulário da página de construção exige o aceite; o do rodapé não tem o campo
    tem_campo_consent = "consent" in (await request.form())
    if tem_campo_consent and not consent:
        return RedirectResponse(f"{lang_prefix}/?nl_consent=1", status_code=303)

    # já cadastrado: avisa em vez de fingir que gravou de novo
    if valido and db.query(NewsletterSub).filter_by(email=email).first():
        return RedirectResponse(f"{lang_prefix}/?nl=ja#newsletter", status_code=303)

    # Dizer "obrigado por se inscrever" para um endereço inválido é mentira: a pessoa
    # sai achando que vai receber e nunca recebe. Melhor avisar e deixar corrigir.
    if not valido:
        return RedirectResponse(f"{lang_prefix}/?nl_invalido=1", status_code=303)

    if not website.strip():
        db.add(NewsletterSub(
            email=email,
            consent=bool(consent) or not tem_campo_consent,
            consent_text=NL_CONSENT_TEXT[lang] if consent else "",
            consent_at=dt.datetime.now(dt.timezone.utc) if consent else None,
            ip=ip_confiavel(request)[:64],
            user_agent=request.headers.get("user-agent", "")[:300],
            lang=lang,
        ))
        registrar(db, "recebeu", "newsletter", email,
                  detalhe="inscrição na newsletter",
                  url="/admin/newsletter/leads", do_site=True)
        db.commit()
        background.add_task(_enviar_boas_vindas, email)
    return RedirectResponse(f"{lang_prefix}/?nl=1#newsletter", status_code=303)


def _enviar_boas_vindas(email: str) -> None:
    """Dispara o e-mail de boas-vindas em segundo plano.

    Roda fora da requisição e com sessão própria: se o SMTP estiver fora do ar, o
    cadastro do assinante já está gravado e nada se perde.
    """
    from ..config import settings as cfg
    from ..database import SessionLocal
    from ..main import templates
    from ..models import Campaign
    from ..models import EmailEvent
    from ..services.campanha import payload as payload_campanha
    from ..services.mailer import send_campaign

    with SessionLocal() as db:
        camp = db.query(Campaign).filter_by(is_welcome=True).first()
        if not camp:
            return
        smap = get_settings_map(db)
        # o payload precisa vir com o id: é ele que liga o rastreio de abertura e clique
        dados = payload_campanha(camp, db, cfg.base_url)

        def registrar(destino: str, kind: str, detalhe: str) -> None:
            db.add(EmailEvent(campaign_id=camp.id, email=destino, kind=kind, detail=detalhe))
            db.commit()

        try:
            enviados, _f, erro = send_campaign(
                smap, dados, [{"email": email, "name": ""}],
                cfg.base_url, cfg.secret_key, registrar)
            print(f"boas-vindas para {email}: "
                  f"{'enviada' if enviados else 'nao enviada ' + (erro or '')}", flush=True)
        except Exception as exc:
            print(f"boas-vindas para {email}: erro {type(exc).__name__}: {exc}", flush=True)


# PNG transparente de 1x1. É PNG mesmo, e não um GIF disfarçado: a rota termina em
# .png e proxy de imagem que confere o tipo pode recusar o que não bate.
PIXEL = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d4944415478da636460600000000500017f7ed2a600"
    "00000049454e44ae426082")


@router.get("/e/o/{token}.png")
async def rastreio_abertura(token: str, db: Session = Depends(get_db)):
    """Pixel de abertura. Registra uma vez por destinatário e devolve a imagem."""
    from ..config import settings as cfg
    from ..models import EmailEvent
    from ..services.mailer import ler_token
    # o pixel nunca pode falhar: e-mail já entregue continua sendo aberto mesmo
    # depois de a campanha ser apagada, e imagem quebrada na caixa é pior que
    # estatística perdida
    try:
        lido = ler_token(token, cfg.secret_key)
        if lido:
            cid, email = lido
            _registrar_evento(db, cid, email, "abriu", unico=True)
    except Exception:
        db.rollback()
    return Response(content=PIXEL, media_type="image/png",
                    headers={"Cache-Control": "no-store, max-age=0"})


@router.get("/e/c/{token}")
async def rastreio_clique(token: str, u: str = "", db: Session = Depends(get_db)):
    """Redireciona para o destino registrando o clique."""
    from ..config import settings as cfg
    from ..models import EmailEvent
    from ..services.mailer import ler_token
    destino = u if u.startswith(("http://", "https://")) else cfg.base_url
    try:
        lido = ler_token(token, cfg.secret_key)
        if lido:
            cid, email = lido
            _registrar_evento(db, cid, email, "clicou", detail=destino[:400])
    except Exception:
        db.rollback()
    # o clique sempre chega ao destino, com ou sem estatística
    return RedirectResponse(destino, status_code=302)


def _registrar_evento(db: Session, cid: int | None, email: str, kind: str,
                      detail: str = "", unico: bool = False) -> None:
    """Grava o evento se a campanha ainda existir. Campanha apagada não vira erro."""
    from ..models import Campaign, EmailEvent
    if cid and not db.get(Campaign, cid):
        return
    if unico and db.query(EmailEvent).filter_by(campaign_id=cid, email=email, kind=kind).first():
        return
    db.add(EmailEvent(campaign_id=cid, email=email, kind=kind, detail=detail))
    db.commit()


@router.get("/newsletter/cancelar")
async def newsletter_unsub(request: Request, db: Session = Depends(get_db),
                           e: str = "", t: str = ""):
    """Descadastro em um clique, exigido pela LGPD e pelo GDPR.

    O link vem assinado com HMAC, então ninguém consegue descadastrar terceiros
    só chutando endereços.
    """
    from ..config import settings
    from ..main import render
    from ..services.mailer import unsub_token
    email = (e or "").strip().lower()
    ok = bool(email) and t == unsub_token(email, settings.secret_key)
    if ok:
        sub = db.query(NewsletterSub).filter_by(email=email).first()
        if sub:
            db.delete(sub)
        for lead in db.query(Lead).filter(Lead.email.ilike(email)).all():
            lead.consent = False
        from ..models import EmailEvent
        db.add(EmailEvent(campaign_id=None, email=email, kind="descadastrou"))
        db.commit()
    ctx = base_ctx(db)
    ctx.update({"unsub_ok": ok, "unsub_email": email})
    return render(request, "unsubscribe.html", ctx)


@router.post("/newsletter/cancelar")
async def newsletter_unsub_post(request: Request, db: Session = Depends(get_db),
                                e: str = "", t: str = ""):
    return await newsletter_unsub(request, db, e, t)


@router.get("/tips/votes")
async def tips_votes(db: Session = Depends(get_db)):
    import json as _json
    row = db.get(SiteSetting, "tip_votes")
    try:
        return _json.loads(row.value) if row else {}
    except Exception:
        return {}


@router.post("/tips/vote")
async def tips_vote(request: Request, db: Session = Depends(get_db)):
    import json as _json
    try:
        body = await request.json()
        tip = int(body.get("tip", -1))
        vote = str(body.get("vote", ""))
    except Exception:
        tip, vote = -1, ""
    if not (0 <= tip < 40) or vote not in ("up", "down"):
        return {"ok": False}
    row = db.get(SiteSetting, "tip_votes")
    try:
        data = _json.loads(row.value) if row else {}
    except Exception:
        data = {}
    entry = data.setdefault(str(tip), {"up": 0, "down": 0})
    entry[vote] = entry.get(vote, 0) + 1
    payload = _json.dumps(data)
    if row:
        row.value = payload
    else:
        db.add(SiteSetting(key="tip_votes", value=payload))
    db.commit()
    return {"ok": True, "votes": entry}


@router.get("/api/search")
async def api_search(request: Request, db: Session = Depends(get_db), q: str = "", lang: str = ""):
    from ..services.search import run_search
    lang = lang if lang in ("pt", "en") else getattr(request.state, "lang", "pt")
    return {"query": q, "groups": run_search(db, q.strip()[:120], lang)}


@router.post("/api/search/image")
async def api_search_image(request: Request, db: Session = Depends(get_db),
                           file: UploadFile = File(...), lang: str = Form("")):
    from ..services.search import (IMAGE_MAX_BYTES, IMAGE_MEDIA_TYPES,
                                   buscar_por_imagem)
    lang = lang if lang in ("pt", "en") else getattr(request.state, "lang", "pt")
    media_type = (file.content_type or "").lower()
    if media_type not in IMAGE_MEDIA_TYPES:
        return {"ok": False, "error": "bad_type"}
    data = await file.read()
    if not data or len(data) > IMAGE_MAX_BYTES:
        return {"ok": False, "error": "too_big"}

    # comparação de imagem é trabalho de CPU: fora do laço de eventos, senão
    # segura as outras requisições enquanto processa
    from starlette.concurrency import run_in_threadpool
    achado = await run_in_threadpool(buscar_por_imagem, db, data, lang)
    if not achado.get("ok"):
        return {"ok": False, "error": achado.get("erro", "bad_type")}
    return {"ok": True, "groups": achado["grupos"], "match": achado.get("melhor", 0)}


@router.post("/api/search/image-url")
async def api_search_image_url(request: Request, db: Session = Depends(get_db),
                               url: str = Form(""), lang: str = Form("")):
    """Mesma busca por imagem, com o endereço no lugar do arquivo.

    Quem cola a URL decide para onde o servidor vai falar, então o download
    passa por `services/baixar.py`, que recusa esquema estranho e qualquer IP
    que não seja da internet aberta. Ver os comentários de lá.
    """
    from ..services import baixar
    from ..services.search import buscar_por_imagem
    lang = lang if lang in ("pt", "en") else getattr(request.state, "lang", "pt")

    from starlette.concurrency import run_in_threadpool
    try:
        data = await run_in_threadpool(baixar.imagem, url)
    except baixar.RecusadoError as e:
        return {"ok": False, "error": str(e)}
    except Exception:
        return {"ok": False, "error": "resposta"}

    achado = await run_in_threadpool(buscar_por_imagem, db, data, lang)
    if not achado.get("ok"):
        return {"ok": False, "error": achado.get("erro", "bad_type")}
    return {"ok": True, "groups": achado["grupos"], "match": achado.get("melhor", 0)}


@router.get("/privacidade")
async def privacy(request: Request, db: Session = Depends(get_db)):
    from ..main import render
    return render(request, "privacy.html", base_ctx(db))


@router.get("/mapa-do-site")
async def sitemap_page(request: Request, db: Session = Depends(get_db)):
    from ..config import settings
    from ..main import TEM_NODAL, render
    cases = published_cases(db).all()
    # Sem o módulo do Nodal o mapa do site continua existindo, só sem a seção
    # do produto — o template já trata lista vazia (ver sitemap_page.html).
    cursos, situacoes = [], []
    if TEM_NODAL and settings.nodal_publico:
        from ..nodal import vitrine as nodal_vitrine
        cursos = nodal_vitrine.cursos_publicados(db)
        situacoes = nodal_vitrine.situacoes_publicas(db)
    return render(request, "sitemap_page.html", {
        **base_ctx(db), "cases": cases,
        "categories": cats_svc.publicas(db, getattr(request.state, "lang", "pt")),
        "nodal_cursos": cursos,
        "nodal_situacoes": situacoes,
    })


def _proximo_seguro(valor: str, reserva: str) -> str:
    """Só aceita caminho do próprio site: nunca reabre a página noutro domínio.

    Open redirect real, achado na revisão final do corte 4: `not
    valor.startswith("//")` barrava a barra dupla, mas não a barra
    INVERTIDA — `/\\evil.com` (ou `/\\\\evil.com`, duas) passava direto por
    começar com uma barra normal só. O navegador NORMALIZA `\\` para `/`
    antes de resolver o endereço, então `/\\evil.com` vira `//evil.com` na
    hora de abrir — o mesmo endereço relativo ao protocolo que a checagem de
    `//` já existe para barrar, só que disfarçado. Um caminho de verdade
    deste site nunca tem barra invertida, então recusar qualquer uma fecha
    os dois disfarces (uma barra, duas) sem precisar prever quantas o
    navegador aceita.
    """
    if valor.startswith("/") and not valor.startswith("//") and "\\" not in valor:
        return valor
    return reserva


@router.post("/consentimento")
async def consentimento_salvar(request: Request):
    """Grava a escolha do visitante sobre cookies de análise (LGPD, opt-in real).

    POST comum, sem JavaScript — as duas ações do banner ("Aceitar análise" e
    "Só o essencial") são o mesmo formulário, só o valor do botão muda. O CSRF
    já chega semeado na página: render() grava `csrf` no contexto sempre que o
    banner está visível (lição C1 — visitante anônimo tem sessão nova, e sem
    semear na própria página o token não existe pra conferir).
    """
    form = await request.form()
    check_csrf(request, str(form.get("csrf", "")))
    escolha = "sim" if str(form.get("escolha", "")) == "sim" else "nao"
    resp = RedirectResponse(_proximo_seguro(str(form.get("proximo", "")), "/"), status_code=303)
    # 12 meses, como o cookie de idioma (lf_lang) — a mesma régua de validade
    # já usada no site para preferência de visitante.
    resp.set_cookie("lf_consent", escolha, max_age=31536000, samesite="lax",
                    secure=not settings.debug, httponly=False)
    return resp


@router.get("/consentimento/mudar")
async def consentimento_mudar(request: Request, proximo: str = "/privacidade"):
    """Reabre o banner: apaga a escolha guardada e volta para a página.

    GET simples — mesmo padrão do próprio troca de idioma do site (nenhuma
    rota aqui te exige senha ou expõe dado; é a decisão de apagar um cookie
    de preferência, refeita a qualquer momento). Fica ao lado do texto sobre
    análise, na Política de Privacidade.
    """
    resp = RedirectResponse(_proximo_seguro(proximo, "/privacidade"), status_code=302)
    resp.delete_cookie("lf_consent")
    return resp


@router.get("/google5573662520e72392.html")
async def google_site_verification():
    """Prova de posse do site para o Google Search Console.

    O arquivo tem que continuar respondendo para sempre: o Google reconfere
    de tempos em tempos, e removê-lo derruba a verificação da propriedade —
    com ela, o acesso ao Search Console. O conteúdo é o formato padronizado
    do próprio Google, não um segredo.
    """
    return PlainTextResponse("google-site-verification: google5573662520e72392.html")


@router.get("/.well-known/security.txt")
async def security_txt():
    return PlainTextResponse(
        "Contact: mailto:contatoleandrofurtado@gmail.com\n"
        "Preferred-Languages: pt-BR, en\n"
        "Expires: 2027-12-31T23:59:59.000Z\n"
    )


_FAVICON = BASE_DIR / "app" / "static" / "img" / "favicon.ico"


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """O `<link rel="icon">` do HTML resolve para navegador, mas robô, agregador
    e leitor de feed pedem /favicon.ico na raiz direto, sem ler a página. Sem esta
    rota vira 404 no log (três só em 22/08/2026).

    O arquivo é um .ico de verdade com 16, 32 e 48px dentro, gerado a partir das
    MESMAS coordenadas de favicon.svg — ver o teste, que compara os dois. Um ano
    de cache: o ícone muda quando a marca mudar, e aí o nome do arquivo muda junto.
    """
    return FileResponse(
        _FAVICON,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/robots.txt")
async def robots(db: Session = Depends(get_db)):
    """Em construção o sitemap não existe, então nem é anunciado.

    Apontar o robots para uma URL que devolve 404 é o tipo de inconsistência que o
    Search Console reclama e que não traz nada em troca.
    """
    from ..config import settings
    em_construcao = (db.get(SiteSetting, "construction_mode") or SiteSetting(value="0")).value == "1"
    linhas = ["User-agent: *", "Allow: /", "Disallow: /admin", "Disallow: /e/"]
    if not em_construcao:
        linhas.append(f"Sitemap: {settings.base_url.rstrip('/')}/sitemap.xml")
    return PlainTextResponse("\n".join(linhas) + "\n")


@router.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)):
    from xml.sax.saxutils import escape

    from ..config import settings
    base = settings.base_url.rstrip("/")
    today = dt.date.today().isoformat()

    def url(loc: str, priority: str = "0.7", tem_ingles: bool = True) -> str:
        # `loc` nasce de dado do banco (slug de case, de marca, de curso, de
        # Situação). Hoje todo caminho de cadastro passa por slugify e nunca
        # produz &, <, > ou aspas — mas esta função não pode depender disso
        # continuar verdade para sempre: um `&` cru aqui vira ParseError no
        # buscador, e um XML malformado é descartado inteiro, não só a URL
        # com o caractere estranho.
        full_pt = f"{base}{loc}"
        loc_txt = escape(full_pt)
        href_pt = escape(full_pt, {'"': "&quot;"})
        # O Nodal ainda não tem tradução (tem_ingles=False): declarar uma
        # alternativa em inglês que devolve o mesmo português diria ao
        # buscador que as duas URLs são versões idiomáticas uma da outra —
        # sinal de conteúdo duplicado. Ver o mesmo raciocínio no bloco
        # `hreflang` de app/templates/base.html.
        alt_en = ""
        if tem_ingles:
            full_en = f"{base}/en{loc if loc != '/' else ''}"
            href_en = escape(full_en, {'"': "&quot;"})
            alt_en = f'<xhtml:link rel="alternate" hreflang="en" href="{href_en}"/>'
        return (
            "<url>"
            f"<loc>{loc_txt}</loc><lastmod>{today}</lastmod><priority>{priority}</priority>"
            f'<xhtml:link rel="alternate" hreflang="pt-BR" href="{href_pt}"/>'
            f"{alt_en}"
            "</url>"
        )

    # /cv não entra: virou 301 permanente para /about (unificação do pacote de
    # lançamento). Listar as duas seria mandar o rastreador para um redirect.
    # /lab entrou no Plano 2/Task 3: a vitrine é indexável (as três telas
    # internas de demo continuam noindex, meta em lab/_base_demo.html) —
    # prioridade alta porque é a peça que mais aparece em divulgação/busca de
    # recrutador. Não existe /en/lab (Lab é PT-only, §12 "fora de escopo" da
    # spec): esta função sempre emprega hreflang alternativo para /en, e como
    # /en/lab estritamente devolve o mesmo HTML em português (nenhum template
    # do Lab ramifica por `lang`), o alternate aponta para uma página que
    # existe de fato, só que ainda não traduzida — melhor que apontar hreflang
    # para um 404.
    parts = [url("/", "1.0"), url("/portfolio", "0.9"), url("/about", "0.8"),
             url("/lab", "0.8"), url("/contato", "0.7"), url("/clientes", "0.6"),
             url("/mapa-do-site", "0.4"), url("/privacidade", "0.3")]
    # Fora do sitemap: arquivado, marcado como noindex, e case de categoria
    # "sites" — este último não tem página própria, o endereço dele é o do
    # cliente, e apontar o buscador para um redirecionamento é ruído.
    for case in published_cases(db).all():
        if case.noindex:
            continue
        if case.category and case.category.kind == "sites" and case.site_url:
            continue
        parts.append(url(f"/case/{case.slug}", "0.8"))
    # A vitrine do módulo entra no sitemap quando ele existe e está ligado; a
    # aula em si continua fora, atrás de matrícula.
    from ..config import settings
    from ..main import TEM_NODAL
    if TEM_NODAL and settings.nodal_publico:
        from ..nodal import vitrine as nodal_vitrine
        parts.append(url("/nodal", "0.9", tem_ingles=False))
        for curso in nodal_vitrine.cursos_publicados(db):
            parts.append(url(f"/nodal/curso/{curso.slug}", "0.8", tem_ingles=False))
        for situacao in nodal_vitrine.situacoes_publicas(db):
            parts.append(url(f"/nodal/situacao/{situacao.slug}", "0.7", tem_ingles=False))
    for brand in sorted(all_brands(db), key=lambda b: b["slug"]):
        parts.append(url(f"/cliente/{brand['slug']}", "0.5"))
    # Redesigns (§6 da spec de Sites): só `publico`. `pitch` é proposta para
    # uma pessoa e o endereço dela é secreto; `aprovado` migrou para o
    # portfólio, e quem merece indexação passa a ser o `Case`. O endereço do
    # token (/lab/p/<token>) NUNCA entra: um segredo no sitemap deixa de ser
    # segredo.
    #
    # `tem_ingles=False` CONTINUA CERTO depois do item 11, e por um motivo que
    # vale escrever: o inglês de um redesign NÃO mora em `/en/lab/sites/<slug>`
    # (esse endereço é 301 desde 26/08, ver `LangMiddleware._sem_en_do_site`).
    # Ele mora em `/lab/sites/<slug>/en`, que é convenção da PEÇA, e não do
    # site. Declarar aqui a alternativa no formato do site mandaria o buscador
    # a um redirect e diria que duas URLs são versões idiomáticas uma da outra
    # quando uma delas nem existe.
    #
    # PENDÊNCIA, e ela só morde quando um redesign bilíngue virar `publico`:
    # listar também `/lab/sites/<slug>/en`, com as duas se declarando por
    # `hreflang`. Isso exige saber QUAIS redesigns têm inglês, e hoje o modelo
    # `Redesign` não guarda isso: o Grupo OM tem, a Padaria Aurora não, e
    # declarar `/en` para quem não tem seria pôr um 404 no sitemap. Enquanto
    # não houver o campo, as tags `hreflang` dentro das próprias páginas são o
    # que faz o par ser descoberto.
    from ..models import Redesign
    for r in db.query(Redesign).filter(Redesign.estado == "publico").all():
        parts.append(url(f"/lab/sites/{r.slug}", "0.6", tem_ingles=False))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(parts) + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")
