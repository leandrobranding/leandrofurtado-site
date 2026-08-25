"""Open redirect real, achado na revisão final do corte 4 (Triagem, item 8):
`app.routers.public._proximo_seguro` aceita `?proximo=` das rotas de
consentimento (`/consentimento`, `/consentimento/mudar`) e devolvia o valor
cru sempre que ele começasse com uma única barra — mas navegadores
NORMALIZAM barra invertida (`\\`) para barra normal (`/`) antes de resolver
o endereço, então `/\\evil.com` vira `//evil.com` na hora de abrir: um
endereço relativo ao protocolo que abre `evil.com`, o mesmo ataque que a
checagem de `//` já existe para impedir, só disfarçado.

Arquivo isolado de propósito: este achado é candidato a cherry-pick direto
para produção, então o commit que o corrige (`app/routers/public.py` + este
teste) fica sozinho, sem nenhuma outra mudança da rodada junto.
"""
import pytest

from app.routers.public import _proximo_seguro


@pytest.mark.parametrize("payload", [
    "/\\evil.com",     # uma barra invertida — o navegador normaliza para //evil.com
    "/\\\\evil.com",   # duas — mesmo disfarce, uma camada a mais
])
def test_barra_invertida_nao_escapa_para_outro_dominio(payload):
    assert _proximo_seguro(payload, "/reserva") == "/reserva"


def test_barra_dupla_continua_recusada():
    """A checagem original — não regredir o que já funcionava."""
    assert _proximo_seguro("//evil.com", "/reserva") == "/reserva"


def test_endereco_absoluto_continua_recusado():
    assert _proximo_seguro("https://evil.com", "/reserva") == "/reserva"


def test_caminho_relativo_de_verdade_continua_aceito():
    """A correção não pode apertar demais: um caminho comum do site, sem
    barra invertida nenhuma, continua passando."""
    assert _proximo_seguro("/privacidade", "/reserva") == "/privacidade"


def test_string_vazia_cai_na_reserva():
    assert _proximo_seguro("", "/reserva") == "/reserva"
