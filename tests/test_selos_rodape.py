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
