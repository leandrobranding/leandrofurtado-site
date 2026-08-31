"""Sanidade estrutural dos arquivos estáticos e dos templates.

POR QUE ESTE ARQUIVO EXISTE

Em 25/08/2026 o site subiu com um `=======` solto na linha 6795 de
`app/static/css/main.css`, sobra de um conflito de merge em que os dois
lados foram resolvidos à mão e o separador ficou para trás.

O estrago não foi cosmético e não foi local. Na recuperação de erro do
parser de CSS, um token inesperado em nível de topo faz o navegador
consumir e DESCARTAR a regra inteira que vem depois. A regra que veio
depois era `.lab-trilho`, a seção do Lab na home. Com ela fora:

  - a seção perdeu `padding`, `margin` e as bordas, e os cartões dos
    sistemas encostaram na barra animada;
  - a seção perdeu `position: relative`, e aí `.lab-trilho-textura`
    (`position: absolute; inset: 0; z-index: -1`) escapou do bloco de
    contenção dela e foi parar ancorada no `<body>`, pintando o degradê
    escuro e o grão atrás dos primeiros 720px da PÁGINA INTEIRA, longe da
    seção a que pertence.

Um caractere, duas partes do site quebradas, e a suíte inteira verde: os
1455 testes daquele dia olhavam rota, template renderizado e regra de
negócio, e nenhum olhava se o CSS era CSS.

O que este arquivo cobre é exatamente essa lacuna, e nada além dela. Não é
um linter de estilo: não opina sobre ordem de propriedade, nome de classe
nem cor. Ele responde a três perguntas que só têm uma resposta certa:

  1. sobrou marcador de conflito em algum arquivo?
  2. as chaves e os comentários de cada CSS fecham?
  3. existe token solto em nível de topo de algum CSS?
"""
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PASTAS = ("app/static", "app/templates")
EXTENSOES = (".css", ".js", ".html", ".svg")

# `git checkout --conflict` e o merge padrão escrevem estes três, sempre no
# começo da linha e sempre com sete caracteres. Um banner de comentário do
# repo (`/* ======...===== */`) tem MUITO mais que sete, então a âncora de
# fim de linha em `=======` é o que separa um do outro sem falso positivo.
MARCADORES = re.compile(r"^(<{7} |={7}$|>{7} )", re.M)


def _arquivos():
    for pasta in PASTAS:
        base = RAIZ / pasta
        if not base.exists():
            continue
        for caminho in sorted(base.rglob("*")):
            if caminho.is_file() and caminho.suffix in EXTENSOES:
                # vendor é código de terceiro, minificado, e não é nosso
                if "vendor" in caminho.parts:
                    continue
                yield caminho


def _sem_comentarios(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _cssses():
    return [c for c in _arquivos() if c.suffix == ".css"]


def test_nenhum_marcador_de_conflito_sobrou():
    """A varredura que faltava em 25/08/2026.

    Vale para CSS, JavaScript, template e SVG: em qualquer um deles um
    marcador ou quebra o arquivo, ou vaza para a tela do visitante.
    """
    sujos = []
    for caminho in _arquivos():
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        for achado in MARCADORES.finditer(texto):
            linha = texto[: achado.start()].count("\n") + 1
            sujos.append(f"{caminho.relative_to(RAIZ)}:{linha}")
    assert not sujos, "marcador de conflito de merge em: " + ", ".join(sujos)


def test_todo_css_tem_as_chaves_fechadas():
    """Chave a mais ou a menos muda onde cada regra termina, e o efeito
    aparece longe do erro: uma regra some numa seção, outra passa a valer
    onde não devia."""
    problemas = []
    for caminho in _cssses():
        limpo = _sem_comentarios(caminho.read_text(encoding="utf-8"))
        limpo = re.sub(r'"(?:[^"\\]|\\.)*"', '""', limpo)
        limpo = re.sub(r"'(?:[^'\\]|\\.)*'", "''", limpo)
        abre, fecha = limpo.count("{"), limpo.count("}")
        if abre != fecha:
            problemas.append(
                f"{caminho.relative_to(RAIZ)}: {abre} '{{' contra {fecha} '}}'"
            )
    assert not problemas, "; ".join(problemas)


def test_todo_css_tem_os_comentarios_fechados():
    """`/*` sem `*/` engole o resto do arquivo em silêncio. Este repo tem
    CSS muito comentado, então o risco é real."""
    problemas = []
    for caminho in _cssses():
        texto = caminho.read_text(encoding="utf-8")
        if texto.count("/*") != texto.count("*/"):
            problemas.append(
                f"{caminho.relative_to(RAIZ)}: {texto.count('/*')} '/*' "
                f"contra {texto.count('*/')} '*/'"
            )
    assert not problemas, "; ".join(problemas)


def test_nenhum_css_tem_token_solto_em_nivel_de_topo():
    """O teste que teria pego o `=======` de 25/08.

    Em nível de topo, um CSS só admite seletor, at-rule ou comentário. Um
    token que não começa como nenhum dos três faz o navegador descartar a
    PRÓXIMA regra inteira, e é isso que torna esta classe de erro tão cara:
    a linha errada e o sintoma ficam em lugares diferentes do arquivo.
    """
    # Começo válido: classe, id, at-rule, atributo, tag, universal,
    # pseudo-elemento, combinador de continuação, vírgula, aspas.
    INICIO_VALIDO = re.compile(r'^[.#@\[\]a-zA-Z*:>~+&,%_"\'()0-9-]')
    problemas = []
    for caminho in _cssses():
        limpo = _sem_comentarios(caminho.read_text(encoding="utf-8"))
        profundidade = 0
        for numero, linha in enumerate(limpo.split("\n"), 1):
            crua = linha.strip()
            if profundidade == 0 and crua and not INICIO_VALIDO.match(crua):
                problemas.append(
                    f"{caminho.relative_to(RAIZ)}:{numero}: {crua[:60]!r}"
                )
            profundidade += linha.count("{") - linha.count("}")
            profundidade = max(0, profundidade)
    assert not problemas, "token solto em nível de topo: " + "; ".join(problemas)


def test_a_regra_da_secao_do_lab_na_home_existe_de_verdade():
    """A vítima do incidente, com nome e sobrenome.

    Os testes acima pegam a CLASSE do erro. Este pega a CONSEQUÊNCIA
    específica que apareceu no site em produção, porque a seção do Lab é a
    peça da home que leva o visitante para as demonstrações, e ela quebrar
    calada de novo custa caro.

    `position: relative` é o que prende `.lab-trilho-textura` à seção. Sem
    ele o fundo não some: ele MUDA DE LUGAR, e vai pintar atrás do topo da
    página.
    """
    css = (RAIZ / "app/static/css/main.css").read_text(encoding="utf-8")
    regra = re.search(r"(?<![\w=-])\.lab-trilho\s*\{([^}]*)\}", css)
    assert regra, "a regra .lab-trilho sumiu de main.css"
    corpo = regra.group(1)
    for propriedade in ("position: relative", "padding:", "border-top:"):
        assert propriedade in corpo, f".lab-trilho perdeu {propriedade!r}"


@pytest.mark.parametrize("arquivo", ["main.css", "a11y.css"])
def test_o_css_que_toda_pagina_carrega_nao_esta_vazio(arquivo):
    """Sentinela: se um dos dois um dia vier vazio ou minúsculo, os testes
    acima passariam sem provar nada."""
    caminho = RAIZ / "app/static/css" / arquivo
    assert caminho.stat().st_size > 5_000, f"{arquivo} está pequeno demais"
