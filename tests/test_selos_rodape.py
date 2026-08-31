"""Selos do rodapé e do menu de tela cheia (23/08/2026).

O selo de segurança é uma AFIRMAÇÃO em nome próprio, não um adesivo comprado
de terceiro. Isso é uma escolha deliberada — selo estilo Norton ou McAfee
alega auditoria externa que este site não contratou, e um visitante que
percebe a imitação perde a confiança justamente por causa dela.

O preço dessa escolha é que a afirmação precisa continuar verdadeira. Estes
testes existem para isso: se alguém desligar a CSP ou o HSTS e esquecer o
selo aceso, a suíte quebra antes de o site sair mentindo.
"""
import re

from starlette.testclient import TestClient

from app.i18n import STRINGS
from app.main import app


def _home(**cookies):
    with TestClient(app, cookies=cookies or None) as c:
        return c.get("/")


# ------------------------------------------------ o selo não pode mentir --

def test_o_selo_declara_hsts_e_o_site_entrega_hsts():
    r = _home()
    assert "HSTS" in STRINGS["pt"]["secure_detail"]
    assert "strict-transport-security" in {k.lower() for k in r.headers}, (
        "o selo diz HSTS e a resposta não traz o cabeçalho")


def test_o_selo_declara_csp_e_o_site_entrega_csp():
    r = _home()
    assert "CSP" in STRINGS["pt"]["secure_detail"]
    assert "content-security-policy" in {k.lower() for k in r.headers}, (
        "o selo diz CSP e a resposta não traz o cabeçalho")


def test_o_selo_declara_lgpd_e_o_consentimento_existe_de_verdade():
    """LGPD no selo só vale se houver escolha real, e não banner decorativo."""
    assert "LGPD" in STRINGS["pt"]["secure_detail"]
    r = _home()
    assert 'action="/consentimento"' in r.text, (
        "o selo diz LGPD e a home não oferece a escolha")


def test_o_selo_de_seguranca_nao_imita_certificadora():
    """Nome de certificadora no selo passaria a impressão de auditoria
    externa. O texto tem que falar de tecnologia, não de marca."""
    for lang in ("pt", "en"):
        texto = (STRINGS[lang]["secure_title"] + STRINGS[lang]["secure_detail"]).lower()
        for marca in ("norton", "mcafee", "sectigo", "digicert", "verisign",
                      "trustwave", "geotrust", "comodo"):
            assert marca not in texto, f"{marca} no selo alega auditoria inexistente"


# --------------------------------------------------------- selo do Google --

def test_selo_do_google_some_quando_nao_ha_link_cadastrado():
    """Sem link no painel o selo não pode renderizar quebrado nem apontar
    para lugar nenhum: ele simplesmente não existe."""
    r = _home()
    if "selo-google" in r.text:
        achou = re.search(r'class="selo selo-google[^"]*" href="([^"]+)"', r.text)
        assert achou and achou.group(1).strip(), "selo do Google sem destino"


def test_selo_de_seguranca_aparece_sempre():
    r = _home()
    assert "selo-seguro" in r.text
    assert STRINGS["pt"]["secure_title"] in r.text


def test_textos_dos_selos_existem_nos_dois_idiomas():
    for chave in ("review_cta", "review_on", "secure_title", "secure_detail"):
        for lang in ("pt", "en"):
            assert STRINGS[lang].get(chave), f"falta {chave} em {lang}"


# --------------------------------- a colisão de nome que apagou os ícones --
# 25/08/2026: os selos deste componente nasceram (23/08) com a classe `.selo`,
# que JÁ pertencia a outro componente — os ícones de ferramenta dos cases
# (`<img class="selo">`, 18px, estilizados por `.selos .selo` desde 14/08).
#
# `.selos .selo` (0,2,0) vence `.selo` (0,1,0) nas propriedades que os DOIS
# declaram. O estrago veio das que só o segundo declarava: `padding: 11px 16px`
# e `border: 1px`. Com o `box-sizing: border-box` global, 32px de padding
# horizontal não cabem numa caixa de 18px — a caixa de conteúdo colapsa para
# 0x0 e o ícone some, sobrando a moldura vazia.
#
# Sumiram os ícones de ferramenta de TODO case, na home, no portfólio, na
# página do case e na do cliente, e nenhum teste acusou: a suíte olhava se o
# HTML tinha a classe, nunca se o CSS a estava destruindo.

import pathlib

CSS = pathlib.Path(__file__).resolve().parent.parent / "app/static/css/main.css"

# Um seletor cujo ÚLTIMO passo é `.selo` sem nada antes limitando o alcance.
# `.selos .selo` e `.selos-ficha .selo` passam; `.selo`, `a.selo` e
# `.qualquer-coisa, .selo` não.
_SELO_CRU = re.compile(r"(?:^|[,{}])\s*[a-z]*\.selo\s*(?=[,{:])", re.M)


def test_nenhuma_regra_de_css_usa_selo_sem_escopo():
    """`.selo` é a classe dos ícones de ferramenta. Qualquer outro componente
    que a use precisa de escopo próprio, senão volta a destruí-los.

    Os selos do rodapé sempre carregam `selo-google` ou `selo-seguro`, então é
    por elas que o CSS deles deve mirar."""
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    achados = [
        css[: m.start()].count("\n") + 1
        for m in _SELO_CRU.finditer(css)
        if not re.search(r"\.selos(-ficha)?\s+[a-z]*\.selo\s*$",
                         css[max(0, m.start() - 60):m.end()].strip())
    ]
    assert not achados, (
        "seletor `.selo` sem escopo em main.css, linha(s) "
        f"{achados}: isso apaga os ícones de ferramenta dos cases"
    )


def test_o_icone_de_ferramenta_nao_recebe_padding_nem_borda():
    """A regra que dimensiona os ícones não declara padding nem borda, e é
    exatamente por isso que uma regra alheia conseguiu injetá-los. Este teste
    prova que a regra continua existindo e com o tamanho que ela promete."""
    css = CSS.read_text(encoding="utf-8")
    regra = re.search(r"\.selos \.selo \{([^}]*)\}", css)
    assert regra, "a regra .selos .selo sumiu de main.css"
    corpo = regra.group(1)
    assert "width: 18px" in corpo and "height: 18px" in corpo
    assert "padding" not in corpo and "border:" not in corpo


def test_os_svgs_de_todos_os_programas_existem():
    """O selo aponta para `/static/img/programas/<slug>.svg`. Slug na lista sem
    arquivo no disco é ícone quebrado em produção."""
    from app.services.programas import PROGRAMAS

    pasta = CSS.parent.parent / "img" / "programas"
    faltando = [s for s in PROGRAMAS if not (pasta / f"{s}.svg").is_file()]
    assert not faltando, f"SVG ausente para: {faltando}"
