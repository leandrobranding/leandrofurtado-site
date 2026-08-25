"""Testes da Task 1 do Plano 2: template pai das demos, fontes locais e
sprites de ícones (`app/templates/lab/_base_demo.html`,
`app/static/lab/lab-base.css`, `app/static/lab/fonts/`,
`app/static/lab/icones/`).

Nenhum teste aqui sobe rota HTTP (as rotas de tela nascem só na Task 3+):
o template pai é renderizado direto pelo ambiente Jinja do app
(`app.main.templates`), do mesmo jeito que qualquer rota futura vai usar."""
import pathlib
import re

import pytest

from app.main import templates

RAIZ_STATIC = pathlib.Path(__file__).resolve().parent.parent.parent / "app" / "static"
RAIZ_LAB = RAIZ_STATIC / "lab"

DEMOS = ("admita", "notavel", "caderneta")

CSS_POR_DEMO = {
    "admita": "admita.css",
    "notavel": "notavel.css",
    "caderneta": "caderneta.css",
}


def _render(demo: str) -> str:
    return templates.get_template("lab/_base_demo.html").render(demo=demo)


# --------------------------------------------------------- _base_demo.html --

@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_renderiza_sem_erro(demo):
    html = _render(demo)
    assert "<!doctype html>" in html.lower()
    assert f'class="lab-demo demo-{demo}"' in html


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_carrega_lab_base_e_css_da_marca_com_v(demo):
    html = _render(demo)
    assert re.search(r'/static/lab/lab-base\.css\?v=\d+', html)
    css_marca = CSS_POR_DEMO[demo]
    assert re.search(rf'/static/lab/{re.escape(css_marca)}\?v=\d+', html)


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_meta_noindex(demo):
    html = _render(demo)
    assert '<meta name="robots" content="noindex, nofollow">' in html


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_sem_barra_de_acessibilidade_do_site(demo):
    """CONSERTO 2 (decisão do dono, revendo §3): a barra de acessibilidade
    do site SAIU da moldura das demos, verbatim: "As demonstrações não
    precisam ter a barra de acessibilidade... Como são demonstrações,
    precisam ter o básico para demonstração." A moldura agora tem só 2
    elementos fixos: cabeçalho + rodapé — sem `_a11y.html` incluído."""
    html = _render(demo)
    assert 'class="a11y"' not in html
    assert 'class="a11y-bar"' not in html
    assert 'a11y-trigger' not in html
    assert '/static/css/a11y.css' not in html  # nenhum link do CSS de a11y no head
    assert 'a11y-pular' not in html  # o skip link também vem só de _a11y.html
    assert 'vw-plugin-wrapper' not in html  # nó do VLibras — outro sinal de _a11y.html incluído


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_sem_peso_institucional_do_site_principio_do_enxuto(demo):
    """§3 PRINCÍPIO DO ENXUTO (nascido junto com o conserto 2): nada de
    tracking, consentimento ou geolocalização do site dentro das demos —
    só o básico para demonstração."""
    html = _render(demo)
    for termo in ("gtm", "googletagmanager", "gtag", "analytics",
                  "consentimento", "geoloc", "lf_consent", "ga4"):
        assert termo not in html.lower(), f"resquício de peso institucional ({termo!r}) em {demo}"


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_cabecalho_padrao_do_site_com_logo_lab(demo):
    """Rodada de direção de arte de 20/08 (reforço do dono): o cabeçalho
    das demos é o MESMO componente do site inteiro (app/templates/
    _cabecalho.html, `.site-header`/`.brand`), não uma recriação — troca
    só a marca ("Leandro Furtado | LAB") e os links, fixo na identidade
    do Leandro, nunca na cor da marca da demo."""
    html = _render(demo)
    assert 'class="site-header" id="top"' in html
    assert 'brand-lab-word">LAB<' in html
    assert "Leandro Furtado" in html
    # sem PT/EN e sem botão de fechar dentro do Lab (§3)
    assert 'lang-toggle' not in html
    assert 'class="menu-btn"' not in html
    # as 3 demos + a saída — links mínimos do cabeçalho (§3)
    assert 'href="/lab/admita"' in html
    # Notável e Caderneta ainda não abriram: aparecem como aviso, não como
    # link, para ninguém cair numa tela vazia a partir do cabeçalho.
    assert 'href="/lab/notavel"' not in html
    assert 'href="/lab/caderneta"' not in html
    assert html.count("nav-link-breve") == 2
    # a saída volta para a VITRINE do lab, não para a home do site: quem está
    # numa demo quer as outras demos, não o portfólio (decisão do dono).
    assert 'fechar demonstração' in html
    assert 'href="/lab"' in html
    assert 'lab-nav-x' in html, "o X da saída precisa vir junto com o texto"


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_faixa_de_conversao_com_tagline_e_origem_correta(demo):
    html = _render(demo)
    assert 'class="lab-faixa"' in html
    assert 'lab-faixa-tagline' in html
    assert "Gostou? Eu construo isso para a sua empresa." in html  # voz do Leandro, §3
    assert f'/contato?origem=lab-{demo}' in html


TAGLINES = {
    "admita": "Contratou? A gente cuida do resto.",
    "notavel": "A nota sai, o dinheiro entra, você vê tudo.",
    "caderneta": "Você lança a nota. O boletim se resolve.",
}


@pytest.mark.parametrize("demo", DEMOS)
def test_base_demo_tagline_exata_da_global_constraints(demo):
    html = _render(demo)
    assert TAGLINES[demo] in html


def test_base_demo_nunca_usa_travessao_no_texto_visivel():
    """Regra do Leandro (Global Constraints): PROIBIDO travessão/hífen como
    pontuação na copy. O template só tem texto fixo de chrome (cabeçalho +
    rodapé) nesta task — varredura completa de copy fica para a Task 11,
    mas o que já existe aqui não pode nascer violando a regra."""
    for demo in DEMOS:
        html = _render(demo)
        # extrai só o texto visível (fora de <head>/<script>/<style>/atributos)
        corpo = html.split("<body", 1)[1].split(">", 1)[1]
        texto_visivel = re.sub(r"<[^>]+>", " ", corpo)
        assert "—" not in texto_visivel, f"travessão em {demo}"


def test_base_demo_titulo_e_descricao_sem_travessao():
    """Achado da rodada de conserto 1: o <title> usava travessão como
    separador ("X — Lab de Demos — Y") — a varredura acima olha só o texto
    do <body> e não pegava isto. Teste dedicado para <title> e
    <meta name="description"> não deixar essa lacuna se repetir."""
    for demo in DEMOS:
        html = _render(demo)
        titulo = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        descricao = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        assert "—" not in titulo, f"travessão no <title> de {demo}: {titulo!r}"
        assert "—" not in descricao, f"travessão na description de {demo}: {descricao!r}"


def test_base_demo_titulo_usa_separador_ponto_medio_com_fe0e():
    """O separador do <title> é '·' + U+FE0E (seletor de apresentação
    textual — regra anti-emoji do Leandro), nunca travessão nem hífen
    solto como pontuação."""
    for demo in DEMOS:
        html = _render(demo)
        titulo = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        assert "·︎" in titulo, f"separador '·' + U+FE0E ausente no <title> de {demo}: {titulo!r}"


def test_base_demo_bloco_demo_conteudo_e_sobrescrevivel():
    """Contrato da task: quem estende passa `demo` e sobrescreve
    `demo_conteudo` — confere que o bloco existe e que o conteúdo
    sobrescrito aparece no HTML final, no lugar certo (dentro de <main>)."""
    modelo = templates.env.from_string(
        '{% extends "lab/_base_demo.html" %}'
        '{% block demo_conteudo %}<p id="sonda">conteúdo da esteira</p>{% endblock %}'
    )
    html = modelo.render(demo="admita")
    assert re.search(r'<main class="lab-conteudo" id="main">', html)
    assert '<p id="sonda">conteúdo da esteira</p>' in html
    # o conteúdo sobrescrito fica DENTRO de <main>, não fora dele
    assert html.index('id="sonda"') < html.index("</main>")
    assert html.index("<main") < html.index('id="sonda"')


# ------------------------------------------------- §13b Lei da tela cheia --

def test_lab_base_css_trava_o_shell_em_100dvh_sem_rolagem_de_pagina():
    """Teste estrutural (não de viewport real — esse fica para as tarefas
    de tela, quando existir conteúdo de verdade para medir). Aqui só
    confere que o CSS do shell DECLARA a Lei da tela cheia: altura travada
    em 100dvh e overflow controlado tanto no `body` quanto no `.lab-demo`.

    Rodada de 20/08 (reforço do dono): o cabeçalho passou a ser o MESMO
    `.site-header` do site (`position: fixed`, ver lab-moldura.css) — não
    ocupa mais linha de grid, então `.lab-demo` caiu para 2 linhas reais
    (miolo 1fr + copyright auto), com o respiro do cabeçalho virando
    padding-top em `.lab-conteudo`. Sem a barra a11y (conserto 2: saiu da
    moldura, não é mais irmã de `.lab-demo` dentro do `body`)."""
    css_texto = (RAIZ_LAB / "lab-base.css").read_text(encoding="utf-8")

    # `body.lab-body` pode aparecer em mais de um bloco de regra (ex.: um
    # reset básico + o bloco do grid) — agrega todos antes de checar, para
    # o teste não depender de qual bloco físico carrega qual propriedade.
    corpo_regra = " ".join(re.findall(r"body\.lab-body\s*\{([^}]*)\}", css_texto))
    assert corpo_regra, "nenhuma regra body.lab-body encontrada"
    assert "100dvh" in corpo_regra
    assert "overflow: hidden" in corpo_regra

    regra_lab_demo = re.search(r"\.lab-demo\s*\{([^}]*)\}", css_texto).group(1)
    assert "overflow: hidden" in regra_lab_demo
    assert "display: grid" in regra_lab_demo
    assert re.search(r"grid-template-rows:\s*1fr auto", regra_lab_demo)

    # a barra a11y não existe mais na moldura — nenhum override de posição
    # dela deveria sobrar no CSS (era só um remendo pra ela virar faixa
    # normal do fluxo quando ainda fazia parte do shell).
    assert ".a11y-bar {" not in css_texto
    assert ".a11y {" not in css_texto


def test_rola_interno_e_a_unica_utilitaria_de_scroll_do_lab_base():
    """`.rola-interno` existe, com scrollbar fina e cor de marca (Firefox
    via `scrollbar-*`, WebKit/Chromium via `::-webkit-scrollbar*`) — é o
    único lugar declarado onde conteúdo excedente pode rolar (§13b)."""
    css_texto = (RAIZ_LAB / "lab-base.css").read_text(encoding="utf-8")
    assert ".rola-interno {" in css_texto
    assert "scrollbar-width: thin" in css_texto
    assert "::-webkit-scrollbar" in css_texto


# -------------------------------------------------------------- fontes --

_FAMILIAS_ESPERADAS = {
    "Alegreya": [(500, 700, "normal"), (500, 500, "italic")],
    "Karla": [(400, 700, "normal")],
    "Source Serif 4": [(600, 700, "normal")],
    "IBM Plex Sans": [(400, 600, "normal")],
    "IBM Plex Mono": [(400, 400, "normal"), (600, 600, "normal")],
    "Lora": [(500, 600, "normal"), (400, 400, "italic")],
    "Nunito Sans": [(400, 800, "normal")],
}


def _blocos_font_face(css_texto: str) -> list[dict]:
    blocos = []
    for corpo in re.findall(r"@font-face\s*\{([^}]*)\}", css_texto):
        familia = re.search(r'font-family:\s*"([^"]+)"', corpo).group(1)
        pesos = re.search(r"font-weight:\s*([0-9]+)(?:\s+([0-9]+))?;", corpo)
        peso_min = int(pesos.group(1))
        peso_max = int(pesos.group(2)) if pesos.group(2) else peso_min
        estilo = re.search(r"font-style:\s*(\w+);", corpo).group(1)
        url = re.search(r'url\("([^"]+)"\)', corpo).group(1)
        blocos.append({
            "familia": familia, "peso_min": peso_min, "peso_max": peso_max,
            "estilo": estilo, "url": url,
        })
    return blocos


def test_lab_base_css_declara_as_7_familias_nos_pesos_das_global_constraints():
    css_texto = (RAIZ_LAB / "lab-base.css").read_text(encoding="utf-8")
    blocos = _blocos_font_face(css_texto)
    for familia, faixas_esperadas in _FAMILIAS_ESPERADAS.items():
        blocos_familia = [b for b in blocos if b["familia"] == familia]
        assert blocos_familia, f"nenhum @font-face para {familia!r}"
        for peso_min_esp, peso_max_esp, estilo_esp in faixas_esperadas:
            achou = any(
                b["estilo"] == estilo_esp
                and b["peso_min"] <= peso_min_esp
                and b["peso_max"] >= peso_max_esp
                for b in blocos_familia
            )
            assert achou, (
                f"{familia} não cobre peso {peso_min_esp}-{peso_max_esp} "
                f"estilo {estilo_esp!r}"
            )


def test_fontes_dos_font_face_existem_como_arquivo_local_woff2():
    """Todo @font-face é local (mesma origem) e aponta para um woff2 de
    verdade. As 7 famílias das identidades vivem em `/static/lab/fonts/`
    (baixadas nesta task); Space Grotesk do cabeçalho é a ÚNICA exceção
    esperada — reaproveita `/static/fonts/SpaceGrotesk.woff2`, o mesmo
    arquivo que o SITE já baixa (zero KB extra, ver comentário no CSS)."""
    css_texto = (RAIZ_LAB / "lab-base.css").read_text(encoding="utf-8")
    blocos = _blocos_font_face(css_texto)
    assert blocos, "nenhum @font-face encontrado em lab-base.css"
    for bloco in blocos:
        url = bloco["url"]
        assert url.startswith("/static/lab/fonts/") or url == "/static/fonts/SpaceGrotesk.woff2", url
        assert url.endswith(".woff2"), url
        assert "fonts.gstatic.com" not in url and "fonts.googleapis.com" not in url, (
            "host externo em produção — PROIBIDO (custo zero do site)"
        )
        caminho = RAIZ_STATIC / url.removeprefix("/static/")
        assert caminho.is_file(), f"arquivo de fonte ausente: {caminho}"
        # magia do woff2 (assinatura "wOF2") — arquivo não é lixo/HTML de erro
        assert caminho.read_bytes()[:4] == b"wOF2", f"{caminho} não é woff2 válido"


def test_sete_familias_da_identidade_vivem_em_static_lab_fonts():
    """Só a exceção documentada (Space Grotesk) sai de `/static/lab/fonts/`
    — as 7 famílias das Global Constraints (Alegreya, Karla, Source Serif
    4, IBM Plex Sans, IBM Plex Mono, Lora, Nunito Sans) são todas locais e
    exclusivas do Lab."""
    css_texto = (RAIZ_LAB / "lab-base.css").read_text(encoding="utf-8")
    blocos = _blocos_font_face(css_texto)
    for familia in _FAMILIAS_ESPERADAS:
        for bloco in blocos:
            if bloco["familia"] == familia:
                assert bloco["url"].startswith("/static/lab/fonts/"), (
                    f"{familia} deveria viver em /static/lab/fonts/, achei {bloco['url']!r}"
                )


def test_nenhum_host_externo_de_fonte_em_lab_base_css():
    css_texto = (RAIZ_LAB / "lab-base.css").read_text(encoding="utf-8")
    assert "http://" not in css_texto
    assert "https://" not in css_texto


# ------------------------------------------------------------- sprites --

_IDS_ESPERADOS = {
    "admita": {"i-usuario", "i-documento", "i-checagem", "i-relogio",
               "i-auditoria", "i-kanban", "i-email", "i-alerta"},
    "notavel": {"i-nota", "i-banco", "i-calculadora", "i-grafico",
                "i-recibo", "i-alerta", "i-check"},
    "caderneta": {"i-caderno", "i-lapis", "i-aluno", "i-turma",
                  "i-calendario", "i-boletim", "i-medalha", "i-alerta"},
}


@pytest.mark.parametrize("demo", DEMOS)
def test_sprite_da_demo_existe_e_e_svg_valido(demo):
    caminho = RAIZ_LAB / "icones" / f"{demo}.svg"
    assert caminho.is_file(), f"sprite ausente: {caminho}"
    import xml.dom.minidom as minidom
    minidom.parse(str(caminho))  # levanta se não for XML bem formado


@pytest.mark.parametrize("demo", DEMOS)
def test_sprite_da_demo_contem_os_ids_esperados_dos_fluxos(demo):
    texto = (RAIZ_LAB / "icones" / f"{demo}.svg").read_text(encoding="utf-8")
    ids_no_arquivo = set(re.findall(r'<symbol id="([^"]+)"', texto))
    faltando = _IDS_ESPERADOS[demo] - ids_no_arquivo
    assert not faltando, f"ids esperados ausentes em {demo}.svg: {faltando}"


@pytest.mark.parametrize("demo", DEMOS)
def test_sprite_da_demo_tem_entre_25_e_40_icones(demo):
    texto = (RAIZ_LAB / "icones" / f"{demo}.svg").read_text(encoding="utf-8")
    ids_no_arquivo = re.findall(r'<symbol id="([^"]+)"', texto)
    assert 25 <= len(ids_no_arquivo) <= 40, (
        f"{demo}.svg tem {len(ids_no_arquivo)} ícones, fora da faixa 25-40"
    )
    # ids em PT-BR, todos únicos, todos com o prefixo i-
    assert len(ids_no_arquivo) == len(set(ids_no_arquivo)), "id duplicado no sprite"
    assert all(i.startswith("i-") for i in ids_no_arquivo)


@pytest.mark.parametrize("demo", DEMOS)
def test_sprite_da_demo_cita_a_licenca_no_comentario_do_topo(demo):
    texto = (RAIZ_LAB / "icones" / f"{demo}.svg").read_text(encoding="utf-8")
    inicio = texto[:600]
    assert "<!--" in inicio
    assert ("MIT" in inicio) or ("ISC" in inicio), (
        f"comentário de licença ausente/incompleto no topo de {demo}.svg"
    )
