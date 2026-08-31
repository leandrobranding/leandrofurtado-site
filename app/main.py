from contextlib import asynccontextmanager

import markdown as md_lib
from fastapi import FastAPI, Request
from fastapi.responses import (HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import BASE_DIR, daqui, settings
from .database import Base, SessionLocal, engine
from .i18n import field, lp, t
import app.lab.models  # noqa: F401  — registra as tabelas do Lab
from .services import anti_spam, vitrine
from .services.formato import ErroDeValidacao, formatar_reais

# ------------------------------------------------------- Nodal opcional --
#
# O Nodal é um produto que roda DENTRO deste site, e desde 24/08/2026 ele é
# opcional: sem a pasta app/nodal/ o site sobe igual, sem as rotas do produto
# e sem erro nenhum. Duas razões:
#
# 1. A cópia pública do projeto no GitHub não leva o produto junto. Ele não
#    está lançado, e o modelo de negócio é do dono.
# 2. Produto embutido que impede o hospedeiro de subir não é produto
#    embutido, é acoplamento.
#
# `formatar_reais` e `ErroDeValidacao` moravam no Nodal e eram a única razão
# de este arquivo importar de lá; foram para services/formato.py. O resto das
# menções a "nodal" aqui é comparação de caminho em texto, que não precisa do
# módulo para funcionar.
try:
    import app.nodal.models  # noqa: F401  — registra as tabelas do Nodal
    TEM_NODAL = True
except ModuleNotFoundError:
    TEM_NODAL = False
from .services.migrations import run_migrations
from .services.seeds import run_seeds

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def _versao_assets() -> int:
    """Versão para o ?v= dos estáticos: o arquivo mais recente entre CSS e JS.

    Antes isto olhava só o main.js. Como o nginx guarda estático por sete dias,
    qualquer deploy que mexesse apenas no CSS ou noutro script saía com a mesma
    versão e o navegador continuava servindo o arquivo velho do cache — um
    recurso removido do código seguia aparecendo na tela por uma semana.
    """
    estaticos = BASE_DIR / "app" / "static"
    arquivos = list(estaticos.rglob("*.js")) + list(estaticos.rglob("*.css"))
    return int(max((a.stat().st_mtime for a in arquivos), default=0))


class _VersaoAssets:
    """Em produção a versão é fixa (o processo sobe uma vez por deploy).

    Em desenvolvimento ela é recalculada a cada uso: sem isso, editar um CSS e
    recarregar continua servindo o arquivo antigo do cache até reiniciar o
    servidor, e o tempo some caçando um bug que já estava corrigido.
    """
    def __init__(self):
        self.fixa = _versao_assets()

    def __str__(self):
        return str(_versao_assets() if settings.debug else self.fixa)


_asset_v = _VersaoAssets()
templates.env.globals.update(site_name=settings.site_name, base_url=settings.base_url,
                             asset_v=_asset_v)
# todo horário exibido passa por aqui: o banco é UTC, a tela é Curitiba
templates.env.filters["local"] = lambda d: daqui(d)
# formata com proteção: data vazia vira string vazia em vez de estourar
templates.env.filters["strftime_"] = lambda d, fmt: d.strftime(fmt) if d else ""
templates.env.filters["md"] = lambda text: md_lib.markdown(text or "", extensions=["extra"])
# nome de empresa vira endereço: "iOn live" -> "ion-live"
templates.env.filters["slug"] = lambda nome: _slugify(nome)
# centavos inteiros -> "R$ 1.234,56": um lugar só pra regra de moeda em tela
templates.env.filters["reais"] = formatar_reais


def _slugify(nome) -> str:
    from .services.images import slugify
    return slugify(str(nome or ""))


# Rodada 3, item 12 (19/08): na aba de certificações, o cabeçalho de cada
# empresa usa a logo dela se o arquivo existir em static/img/certifiers/ —
# sem inventar nada: nenhuma logo foi desenhada para este pacote (nenhum
# asset da Anthropic/FGV/Google existia no site, nem no sistema de logos de
# clientes). Onde não houver arquivo, o nome limpo (sem a linha decorativa)
# é o fallback elegante já combinado com o dono para este caso. Se um dia
# alguém soltar um SVG monocromático oficial nessa pasta, aparece sozinho —
# sem tocar no template.
def certifier_logo(org: str) -> str:
    caminho = BASE_DIR / "app" / "static" / "img" / "certifiers" / f"{_slugify(org)}.svg"
    return f"/static/img/certifiers/{_slugify(org)}.svg" if caminho.is_file() else ""


templates.env.globals["certifier_logo"] = certifier_logo


def _prop_img(rel) -> float:
    """Proporção limitada da imagem, ou 0 quando não dá para medir."""
    from .services.proporcao import de
    return de(settings.upload_dir / str(rel or ""))


def _img_vertical(rel) -> bool:
    from .services.proporcao import e_vertical
    return e_vertical(settings.upload_dir / str(rel or ""))


def _srcset(rel) -> str:
    from .services.responsivo import srcset
    return srcset(str(rel or ""))


def _img_cheia(rel) -> str:
    from .services.responsivo import cheia
    return cheia(str(rel or ""))


def _img_leve(rel) -> str:
    from .services.responsivo import leve
    return leve(str(rel or ""))


def _programas_de(case) -> list[tuple[str, str]]:
    from .services.programas import do_case
    return do_case(case)


def _og_img(rel) -> str:
    from .services.responsivo import og
    return og(str(rel or ""))


def _alt_de(legenda, titulo, cliente="", posicao=0) -> str:
    from .services.responsivo import alt
    return alt(legenda, titulo, cliente, posicao)


def _cases_da_casa(nome) -> int:
    """Cases publicados creditados a esta casa do currículo.

    Falha em zero de propósito: se a leitura der errado, a passagem pela agência
    aparece sem link, que é como ela sempre foi. Nunca vale derrubar a página do
    currículo por causa de um selo.
    """
    try:
        from .services.creditos import chave, contagem
        with SessionLocal() as db:
            return contagem(db).get(chave(nome), 0)
    except Exception:
        return 0


def _de_onde(request: Request, lang: str) -> dict:
    try:
        from .services.geo import ip_do_pedido, onde
        return onde(ip_do_pedido(request), lang)
    except Exception:
        return {}      # geolocalização é enfeite: nunca pode derrubar a página


# ---------- rastreamento com consentimento (pacote de 18/08) ----------

def _area_aluno_do_nodal(path: str) -> bool:
    """A tela é da área LOGADA do aluno (Nodal)? Produto pago — nem com
    consentimento dado o GTM entra aqui, é área de estudo, não de marketing.

    O catálogo público do Nodal (/nodal, /nodal/curso/<slug> sem mais nada
    depois, /nodal/situacao...) não entra nesta lista: esse segue a regra
    normal do site, herdando o comportamento do consentimento como qualquer
    outra página pública (ver rotas_publicas.py).
    """
    if path in ("/nodal/entrar", "/nodal/sair", "/nodal/meus-cursos"):
        return True
    if path.startswith("/nodal/entrar/"):
        return True
    if path.startswith("/nodal/curso/"):
        resto = path[len("/nodal/curso/"):]
        # aula, caderno e anotação de módulo são todas sub-rotas de
        # rotas_aluno.py; a landing pública é só "/nodal/curso/<slug>", sem
        # mais nada depois dela — essa não bate em nenhum dos três.
        return "/aula/" in resto or resto.endswith("/caderno") or "/modulo/" in resto
    return False


def _gtm_ativo(request: Request) -> str:
    """ID do GTM a carregar nesta resposta, ou "" quando não deve carregar.

    Três portões, os três precisam estar abertos: consentimento dado
    (`lf_consent=sim`, decidido no servidor — nunca "carrega e depois
    pergunta"), um `gtm_id` configurado no painel (campo vazio = ferramenta
    desligada), e a tela não ser da área logada do aluno do Nodal.
    """
    if request.cookies.get("lf_consent") != "sim":
        return ""
    if _area_aluno_do_nodal(request.state.clean_path):
        return ""
    from .models import SiteSetting
    try:
        with SessionLocal() as db:
            row = db.get(SiteSetting, "gtm_id")
            return (row.value or "").strip() if row else ""
    except Exception:
        return ""


def _trilha_do_painel(request: Request) -> list:
    try:
        from .services.trilha import montar
        return montar(request.url.path)
    except Exception:
        return []


def _avisos_do_painel() -> dict:
    try:
        from .routers.admin_avisos import nao_lidas, ultimas
        with SessionLocal() as db:
            return {"avisos_nao_lidos": nao_lidas(db), "avisos_recentes": ultimas(db, 8)}
    except Exception:
        return {"avisos_nao_lidos": 0, "avisos_recentes": []}


def render(request: Request, name: str, ctx: dict | None = None, status_code: int = 200) -> HTMLResponse:
    lang = getattr(request.state, "lang", "pt")
    base = {
        "request": request,
        "lang": lang,
        "t": lambda key: t(lang, key),
        "f": lambda obj, name_: field(obj, name_, lang),
        "lp": lambda path: lp(lang, path),
        # Site ou case: a pergunta que muda o link, a capa e o rótulo do botão
        # em todo card do site. Uma resposta só, para todas as telas.
        "eh_site": vitrine.eh_site,
        "host_de": vitrine.host,
        "capa_de": vitrine.capa,
        "destino": lambda case: vitrine.destino(case, lambda p: lp(lang, p)),
        # Quantos cases publicados saíram de uma casa do currículo. Zero quer
        # dizer "não vira link": prometer trabalho e entregar lista vazia é pior
        # do que não prometer nada.
        "cases_da_casa": _cases_da_casa,
        # proporção real da imagem, para a caixa se ajustar à peça
        "prop_img": _prop_img,
        # Carimbo anti-bot dos formulários públicos (services/anti_spam.py):
        # campo oculto `t`, assinado com a secret_key. Lambda e não valor,
        # para o timestamp ser o do render, não o da importação.
        "carimbo_anti_spam": lambda: anti_spam.carimbo(settings.secret_key),
        "img_vertical": _img_vertical,
        # escada de tamanhos e texto alternativo (ver services/responsivo.py)
        "srcset": _srcset,
        "img_cheia": _img_cheia,
        "img_leve": _img_leve,
        "alt_de": _alt_de,
        # ferramentas do case -> [(slug, nome)], para os selos de programa
        "programas_de": _programas_de,
        "og_img": _og_img,
        "path": request.state.clean_path,
        "is_admin": bool(request.session.get("user")),
        # De onde a pessoa está vendo. Sai daqui porque render() é o funil por
        # onde toda página passa; consulta local, ~0,7 ms, e o IP não é guardado.
        "visitante": _de_onde(request, lang),
        # Rastreamento com consentimento: "" quando não deve carregar (sem
        # aceite, sem ID no painel, ou área logada do aluno do Nodal).
        "gtm_id": _gtm_ativo(request),
        # Sem escolha registrada ainda = mostra o banner. Uma vez que a pessoa
        # decide (sim OU não), o cookie fica gravado e o banner não volta —
        # "mudar minha escolha", na Política de Privacidade, é o único jeito
        # de reabri-lo. Não aparece na área logada do aluno do Nodal pelo
        # mesmo motivo que o GTM não entra lá: nada de análise de marketing
        # importa numa tela de estudo de produto pago (mesma lista de
        # `_area_aluno_do_nodal` usada por `_gtm_ativo`, uma única fonte da
        # verdade em vez de duas listas que podem desalinhar).
        "mostrar_consentimento": (request.cookies.get("lf_consent") not in ("sim", "nao")
                                  and not _area_aluno_do_nodal(request.state.clean_path)),
        # Spec §17, adendo "nada de tela de carregamento no espaço do
        # aluno" (pedido do Leandro, chegou no fim da Tarefa 10): decide se
        # este é o mesmo "espaço do aluno" que já desliga GTM e o banner de
        # consentimento — REAPROVEITA `_area_aluno_do_nodal`, a fonte única
        # já usada duas linhas acima para as outras duas decisões, em vez
        # de uma terceira lista de rotas que poderia desalinhar das outras
        # duas. `base.html` usa isto para não renderizar `.preloader`
        # nessas páginas; `_base_nodal.html` usa para marcar
        # `data-preloader="off"` no `<body>` (segunda camada, mesmo padrão
        # de `data-tips`).
        "aluno_area": _area_aluno_do_nodal(request.state.clean_path),
    }
    # O CSRF só é semeado quando o banner realmente aparece: é a página que o
    # visitante anônimo vê ANTES de ter qualquer sessão, então o token precisa
    # nascer aqui para o POST sem JavaScript do banner ter o que conferir
    # (lição C1 — sessão nova não tem csrf até algo gravar um).
    if base["mostrar_consentimento"]:
        from .auth import csrf_token
        base["csrf"] = csrf_token(request)
    # O sino do painel precisa dos avisos em toda tela do admin. Sai daqui pelo
    # mesmo motivo do visitante: é o funil por onde tudo passa. Só consulta
    # quando é página do painel e há sessão — o site público não paga por isso.
    if request.state.clean_path.startswith("/admin") and base["is_admin"]:
        # O template do painel esconde header e lateral atrás de {% if user %}.
        # Sem esta linha, toda tela renderizada por aqui (a central de cases
        # inteira) aparecia sem barra lateral e sem header — era o que estava
        # fora do padrão do resto do admin.
        base["user"] = request.session.get("user")
        base.update(_avisos_do_painel())
        base["trilha"] = _trilha_do_painel(request)
    base.update(ctx or {})
    return templates.TemplateResponse(request, name, base, status_code=status_code)


class ConstructionMiddleware(BaseHTTPMiddleware):
    """Modo construção: o site inteiro vira uma página só, menos para o admin.

    Fica ligado por Configurações → Modo construção. Continuam passando: o painel,
    os arquivos estáticos, a API (que já tem token) e o POST da newsletter, porque é
    justamente ela que a página de construção precisa que funcione.
    """

    # "/e/" é o rastreio de e-mail: precisa responder mesmo com o site fechado,
    # senão campanha enviada durante a construção perde abertura e clique.
    # google5573662520e72392.html é o arquivo de verificação do Search Console:
    # com o site em construção o Google precisa receber o conteúdo dele, não a
    # tela de construção — senão a propriedade nunca fica verificada.
    # "/lab" é o Lab de Demos: sistema à parte, com identidade própria e
    # tela cheia sem chrome do site — o modo construção é do SITE, não faz
    # sentido derrubar as demos junto (Plano 2, Task 1).
    LIBERADO = ("/admin", "/static", "/media", "/api/", "/newsletter", "/e/",
                "/a11y", "/robots.txt", "/favicon.ico", "/.well-known",
                "/google5573662520e72392.html", "/consentimento", "/lab")

    @staticmethod
    def _case_publicado(path: str) -> bool:
        """O caminho é a página de um case que está publicado?"""
        if not path.startswith("/case/"):
            return False
        slug = path[len("/case/"):].strip("/")
        if not slug or "/" in slug:
            return False
        from .database import SessionLocal as _S
        from .models import Case
        try:
            with _S() as db:
                return bool(db.query(Case).filter_by(slug=slug, published=True).first())
        except Exception:
            return False

    async def dispatch(self, request: Request, call_next):
        path = request.state.clean_path
        if path.startswith(self.LIBERADO) or request.session.get("user"):
            return await call_next(request)

        from .database import SessionLocal as _S
        from .models import SiteSetting
        with _S() as db:
            row = db.get(SiteSetting, "construction_mode")
            ligado = bool(row and row.value == "1")
            liberar_cases = bool((r2 := db.get(SiteSetting, "cases_publicos")) and r2.value == "1")
        if not ligado:
            return await call_next(request)

        # Case publicado pode sair, quando o painel autorizar.
        #
        # Existe porque link compartilhado precisa abrir. Com tudo fechado, a
        # prévia que o WhatsApp e o LinkedIn montam é a da página de construção,
        # e nenhum ajuste de meta muda isso: o robô lê o que a página devolve.
        # Aqui o case sai e o resto do site continua fechado.
        if liberar_cases and self._case_publicado(path):
            return await call_next(request)

        # Devolver HTML em .xml confunde crawler: em construção o sitemap não existe.
        if path == "/sitemap.xml":
            return PlainTextResponse("404", status_code=404)

        from .routers.public import base_ctx
        with _S() as db:
            ctx = base_ctx(db)
        pct = str(ctx["site"].get("construction_progress", "") or "85").strip()
        ctx["progresso"] = min(100, max(0, int(pct))) if pct.isdigit() else 85
        return render(request, "construction.html", ctx)


class LangMiddleware(BaseHTTPMiddleware):
    """Idioma pela URL, com uma exceção: a primeira visita de fora do Brasil.

    Quem chega de outro país cai no inglês em vez do português. Só na primeira
    visita, e só se ainda não houver escolha registrada: o instante em que a
    pessoa clica em PT ou EN grava um cookie, e a partir daí a vontade dela
    vale mais que o IP dela.

    Redirecionar por IP tem um preço em SEO — o Google recomenda não fazer, e
    um buscador que sempre caísse no inglês nunca indexaria as páginas em
    português. Por isso robô nenhum é redirecionado: o rastreador vê exatamente
    o que a URL promete, e as tags hreflang continuam sendo a fonte da verdade.
    """

    # Um robô que se identifica; a lista cobre quem realmente indexa o site.
    ROBOS = ("bot", "crawler", "spider", "slurp", "facebookexternalhit",
             "whatsapp", "telegrambot", "embedly", "quora link preview",
             "pinterest", "vkshare", "developers.google.com/+/web/snippet",
             "lighthouse", "chrome-lighthouse", "headlesschrome")

    def _robo(self, request: Request) -> bool:
        ua = request.headers.get("user-agent", "").lower()
        return any(marca in ua for marca in self.ROBOS)

    async def dispatch(self, request: Request, call_next):
        path = request.scope["path"]
        if path == "/en" or path.startswith("/en/"):
            request.scope["path"] = path[3:] or "/"
            request.state.lang = "en"
        else:
            request.state.lang = "pt"
        request.state.clean_path = request.scope["path"]

        # Spec §9.4 (Leandro, 19/08): Nodal só em português, por enquanto —
        # o seletor PT/EN saiu do chrome (_base_nodal.html) e todo
        # /en/nodal/* vira redirect permanente para o equivalente sem /en.
        # Aqui, não nas rotas do Nodal, porque um único lugar cobre TUDO
        # debaixo de /nodal — catálogo público, área do aluno e fragmentos
        # (estudo.html busca pedaço por fetch) — sem espalhar a checagem
        # por cada router. 301 em GET/HEAD preserva o valor de SEO de um
        # link antigo; POST (concluir aula, sair, formulário) usa 308 para
        # não trocar o verbo nem perder o corpo no meio do redirect.
        if request.state.lang == "en" and self._sem_en_do_site(request.state.clean_path):
            destino = request.state.clean_path
            if request.url.query:
                destino += "?" + request.url.query
            status = 301 if request.method in ("GET", "HEAD") else 308
            return RedirectResponse(destino, status_code=status)

        if self._deve_mandar_para_ingles(request, path):
            destino = "/en" + (path if path != "/" else "/")
            if request.url.query:
                destino += "?" + request.url.query
            resp = RedirectResponse(destino, status_code=302)
            resp.set_cookie("lf_lang", "en", max_age=31536000, samesite="lax",
                            secure=not settings.debug, httponly=False)
            return resp

        return await call_next(request)

    @staticmethod
    def _e_nodal(clean_path: str) -> bool:
        return clean_path == "/nodal" or clean_path.startswith("/nodal/")

    @staticmethod
    def _e_lab(clean_path: str) -> bool:
        return clean_path == "/lab" or clean_path.startswith("/lab/")

    @classmethod
    def _sem_en_do_site(cls, clean_path: str) -> bool:
        """Os dois produtos que NÃO são traduzidos pelo `/en` do site.

        O Nodal está aqui desde a §9.4: ele só existe em português.

        O LAB ENTROU EM 26/08, e por um motivo diferente e mais afiado. Um
        redesign do Lab é uma peça feita para o cliente DELE, e a língua dele é
        propriedade da peça, não do portfólio em volta: o redesign do Grupo OM
        tem inglês próprio, escrito à mão, e o endereço dele é
        `/lab/sites/grupo-om/en`.

        Sem esta linha, `/en/lab/sites/grupo-om` respondia 200 e servia o
        PORTUGUÊS, porque o `/en` do site é retirado antes do roteamento e a
        rota do redesign nunca fica sabendo dele. Um endereço que diz "en" e
        entrega português é pior que um 404: ele promete uma tradução que não
        está ali, e ainda cria uma segunda URL para a mesma página, que é
        conteúdo duplicado escrito de propósito.

        O 301 resolve os dois de uma vez: `/en/lab/...` passa a apontar para
        `/lab/...`, e quem quer inglês usa o endereço que a própria peça
        publica.
        """
        return cls._e_nodal(clean_path) or cls._e_lab(clean_path)

    def _deve_mandar_para_ingles(self, request: Request, path: str) -> bool:
        if request.method != "GET" or request.state.lang == "en":
            return False
        if request.cookies.get("lf_lang"):        # a pessoa já escolheu
            return False
        if self._robo(request):
            return False
        limpo = request.state.clean_path
        # só páginas: estático, painel, API e rastreio de e-mail ficam de fora
        if limpo.startswith(("/static", "/media", "/admin", "/api/", "/e/", "/a11y",
                             "/robots.txt", "/sitemap.xml", "/favicon.ico", "/.well-known")):
            return False
        # §9.4: Nodal não tem versão em inglês — mandar um visitante
        # estrangeiro para /en/nodal só para o redirect acima trazer de
        # volta seria um ricochete inútil (e gravaria lf_lang=en por cima
        # de um produto que nunca vai honrar esse cookie).
        # E o Lab pela mesma lista: mandar um visitante de fora para
        # `/en/lab/sites/grupo-om` só para o 301 acima trazer de volta seria um
        # ricochete inútil, e gravaria `lf_lang=en` por causa de uma peça que
        # tem o próprio seletor de idioma dentro dela.
        if self._sem_en_do_site(limpo):
            return False
        from .services.geo import ip_do_pedido, pais_do_ip
        pais = pais_do_ip(ip_do_pedido(request))
        # sem país (rede local, base ausente) não muda nada: no escuro, fica em casa
        return bool(pais) and pais != "BR"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    # O tradutor de Libras é um player Unity hospedado no gov.br: exige script,
    # fonte, estilo e WebAssembly de fora, o que enfraquece a política. Em vez de
    # abrir isso para todo mundo por um recurso que a maioria nunca liga, a
    # exceção vale só para quem pediu Libras — o cookie é a marca desse pedido.
    LIBRAS = ("https://vlibras.gov.br https://www.vlibras.gov.br "
              "https://dicionario2.vlibras.gov.br https://traducao2.vlibras.gov.br "
              "https://cdn.jsdelivr.net")

    # Rastreamento com consentimento (pacote de 18/08): o GTM é o único script
    # que o site carrega — GA4 e o Pixel do Facebook são configurados DENTRO do
    # contêiner, no painel do Google, e saem de lá (por isso os domínios da
    # Google e do Facebook aqui, nunca gtag.js/fbevents.js próprios). A CSP só
    # diz quem PODE: o servidor é quem decide se algo é efetivamente carregado
    # — sem `lf_consent=sim` e sem `gtm_id` no painel, nenhum destes domínios
    # chega a aparecer no HTML (ver `_gtm_ativo` e o template base.html).
    # connect.facebook.net entra porque é de lá que o GTM carrega o script do
    # Pixel (fbevents.js) — sem ele aqui, o Pixel falha em silêncio: a CSP
    # bloqueia, nada aparece na tela e o Gerenciador de Eventos fica a zero.
    GTM_SCRIPT = "https://www.googletagmanager.com https://connect.facebook.net"
    GTM_CONNECT = ("https://www.google-analytics.com https://*.google-analytics.com "
                   "https://analytics.google.com https://stats.g.doubleclick.net "
                   "https://www.facebook.com")
    GTM_FRAME = "https://www.googletagmanager.com"

    def politica(self, com_libras: bool) -> str:
        extra = (" " + self.LIBRAS) if com_libras else ""
        # o Unity monta o próprio runtime como blob: e o avalia; sem blob: e sem
        # eval o player nunca sai da barra de carregamento
        wasm = " 'wasm-unsafe-eval' 'unsafe-eval' blob:" if com_libras else ""
        return (
            "default-src 'self'; "
            # img-src já libera "https:" (qualquer host por HTTPS) — o pixel de
            # imagem de fallback do Facebook e o do GA4 já passam por aqui, sem
            # precisar listar os domínios de novo.
            f"img-src 'self' data: blob: https:; media-src 'self' https:; "
            f"font-src 'self' data:{extra}; "
            f"style-src 'self' 'unsafe-inline'{extra}; "
            f"script-src 'self' 'unsafe-inline' {self.GTM_SCRIPT}{wasm}{extra}; "
            # iframe.videodelivery.net é o reprodutor da Cloudflare Stream: todo
            # vídeo de aula do Nodal passa por ele. Sem este domínio aqui, o
            # navegador bloqueia o próprio iframe (CSP barra a página de
            # carregar dentro de si, não o vídeo em si) e sobra legenda
            # flutuando sobre um quadro 0×0. googletagmanager.com entra pelo
            # mesmo motivo: é o iframe de noscript do GTM (ns.html).
            f"frame-src https://www.instagram.com https://www.youtube-nocookie.com "
            f"https://player.vimeo.com https://iframe.videodelivery.net {self.GTM_FRAME}; "
            f"worker-src 'self' blob:; connect-src 'self' blob: data: {self.GTM_CONNECT}{extra}; "
            "object-src 'none'; base-uri 'self'"
        )

    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # `microphone=()` proíbe até a própria origem, e foi isso que desligou a
        # busca por voz: o navegador barra o reconhecimento de fala antes de
        # pedir permissão. `(self)` libera só para este site, e continua negando
        # câmera e localização para todo mundo.
        resp.headers.setdefault("Permissions-Policy",
                                "camera=(), microphone=(self), geolocation=()")
        resp.headers.setdefault(
            "Content-Security-Policy",
            self.politica(request.cookies.get("lf_libras") == "1"),
        )
        # O HTML sempre revalida. Sem isto o navegador guarda a página por conta
        # própria e continua carregando scripts que já saíram do código. O custo
        # é um 304; o estático continua com cache longo, versionado pelo ?v=.
        if resp.headers.get("content-type", "").startswith("text/html"):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        # EM DESENVOLVIMENTO, NADA É GUARDADO. `no-cache` ainda permite que o
        # navegador sirva do disco depois de um 304, e um CSS já baixado
        # continua valendo enquanto o `?v=` não mudar. Enquanto se está
        # editando, isso vira meia hora caçando um bug que já está corrigido:
        # o dono passou por isso três vezes numa tarde. Com `no-store` cada
        # recarga vai buscar tudo de novo, HTML, CSS, JS e fonte.
        if settings.debug:
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            # sem ETag não há 304: a resposta vem inteira, sempre
            for cabecalho in ("etag", "last-modified"):
                if cabecalho in resp.headers:
                    del resp.headers[cabecalho]
        if not settings.debug:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return resp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Em produção o uvicorn sobe com 2 workers, e os dois executam este startup ao
    # mesmo tempo. Sem trava, ambos tentam criar as tabelas e um morre com
    # "table users already exists" — pior, os seeds poderiam duplicar usuário e
    # categorias. O lock exclusivo faz o primeiro criar e o segundo só conferir.
    import fcntl

    lock_path = settings.data_dir / ".init.lock"
    with open(lock_path, "w") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            Base.metadata.create_all(bind=engine)
            with SessionLocal() as db:
                if TEM_NODAL:
                    from .nodal.busca import criar_indice
                    criar_indice(db)
                aplicadas = run_migrations(db)
                if aplicadas:
                    print(f"migrações aplicadas: {', '.join(aplicadas)}", flush=True)
                run_seeds(db)
            # Marca enviada pelo painel antes desta regra existir também entra
            # aparada. É idempotente: quem já está encostado no desenho passa
            # batido, então isto não fica reescrevendo arquivo a cada boot.
            from .services.logos import normalizar

            pasta = settings.upload_dir / "clients"
            if pasta.is_dir():
                ajustadas = [f.name for f in sorted(pasta.glob("*.svg")) if normalizar(f)]
                if ajustadas:
                    print(f"logos aparadas: {', '.join(ajustadas)}", flush=True)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    yield


app = FastAPI(title=settings.site_name, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(ConstructionMiddleware)  # o mais interno: já tem sessão e idioma
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LangMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=not settings.debug,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(settings.upload_dir)), name="media")

from .routers import a11y as a11y_router  # noqa: E402
from .routers import admin as admin_router  # noqa: E402
from .routers import admin_avisos as admin_avisos_router  # noqa: E402
from .routers import admin_cases as admin_cases_router  # noqa: E402
from .routers import admin_nl as admin_nl_router  # noqa: E402
from .routers import api as api_router  # noqa: E402
from .routers import public as public_router  # noqa: E402
from .lab import rotas as lab_router  # noqa: E402
from .lab import rotas_sites as lab_sites_router  # noqa: E402

if TEM_NODAL:
    from .nodal import rotas_admin as nodal_admin_router  # noqa: E402
    if settings.nodal_publico:
        from .nodal import rotas_publicas as nodal_publico_router  # noqa: E402
        from .nodal import rotas_aluno as nodal_aluno_router  # noqa: E402

app.include_router(public_router.router)
# Antes do admin: /admin/cases/insights precisa vencer /admin/cases/{case_id},
# que espera número e devolveria erro para um caminho com nome.
app.include_router(admin_avisos_router.router)
app.include_router(admin_cases_router.router)
app.include_router(admin_nl_router.router)
app.include_router(admin_router.router)
app.include_router(api_router.router)
app.include_router(a11y_router.router)
if TEM_NODAL:
    app.include_router(nodal_admin_router.router)
    if settings.nodal_publico:
        app.include_router(nodal_publico_router.router)
        app.include_router(nodal_aluno_router.router)
app.include_router(lab_router.router)
app.include_router(lab_sites_router.router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if not hasattr(request.state, "clean_path"):
        request.state.lang = "pt"
        request.state.clean_path = request.url.path
    return render(request, "404.html", status_code=404)


@app.exception_handler(ErroDeValidacao)
async def erro_de_validacao(request: Request, exc: ErroDeValidacao):
    """Rede de segurança pra ErroDeValidacao que escapa de uma rota sem
    `except` próprio (M3 da revisão da Tarefa 6: reordenar_aulas e
    reordenar_modulos deixam a exceção subir crua de propósito — é o que o
    teste do brief exige ao chamar a função direto, `pytest.raises`, e
    virava 500 "Internal Server Error" sem mensagem nenhuma na rota HTTP de
    verdade). Um handler global não muda o contrato da função: só entra em
    jogo quando o Starlette já está processando a exceção que escapou da
    rota, nunca quando alguém chama a coroutine direto num teste (o que
    `asyncio.run(reordenar_aulas(...))` faz não passa pelo FastAPI nenhum).
    Toda rota que já captura ErroDeValidacao com o próprio `except`
    continua se comportando exatamente como antes — este handler só é
    alcançado por quem deixa escapar.
    """
    return JSONResponse({"ok": False, "erro": str(exc)}, status_code=400)
