"""Correção de segurança (20/08): o IP do visitante era forjável, o que
tornava contornável todo rate limit da casa, inclusive o de login do admin.

Duas falhas independentes levavam a isso: geo.py e auth.py liam o PRIMEIRO
item do X-Forwarded-For (o que o cliente manda por conta própria), e três das
quatro locations do nginx que fazem proxy_pass não setavam X-Real-IP nem
X-Forwarded-For, deixando o cliente forjar os dois cabeçalhos livremente.

Este arquivo cobre o helper único, `app.services.geo.ip_confiavel`, que
substituiu as duas implementações duplicadas. tests/test_login_rate_limit.py
cobre a ponta a ponta: o rate limit do login do admin resistindo a um
X-Forwarded-For rotativo.
"""
from starlette.requests import Request

from app.services.geo import ip_confiavel


def _req(headers: list[tuple[bytes, bytes]], client=("198.51.100.7", 54321)) -> Request:
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "raw_path": b"/", "query_string": b"", "headers": headers,
        "client": client, "state": {}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def test_xff_forjado_na_posicao_0_nao_vira_o_ip_resolvido():
    """O item que o cliente escreve por conta própria é o primeiro da lista;
    ele nunca pode ser o IP usado para rate limit ou geolocalização."""
    req = _req([(b"x-forwarded-for", b"1.2.3.4, 203.0.113.9")])
    ip = ip_confiavel(req)
    assert ip != "1.2.3.4"
    assert ip == "203.0.113.9"


def test_x_real_ip_presente_vence_o_xff():
    """X-Real-IP é escrito pelo nginx com $remote_addr, incondicional. Mesmo
    com um X-Forwarded-For presente (e possivelmente forjado), X-Real-IP
    ganha."""
    req = _req([
        (b"x-forwarded-for", b"9.9.9.9, 8.8.8.8"),
        (b"x-real-ip", b"203.0.113.9"),
    ])
    assert ip_confiavel(req) == "203.0.113.9"


def test_xff_com_cadeia_de_proxies_resolve_o_ultimo():
    """Cadeia real de proxies: cada um anexa ao final. O nginx da casa é o
    último a mexer no cabeçalho, então o último item é o dele."""
    req = _req([(b"x-forwarded-for", b"forjado, 10.1.1.1, 203.0.113.9")])
    assert ip_confiavel(req) == "203.0.113.9"


def test_sem_cabecalho_nenhum_cai_em_client_host():
    req = _req([], client=("198.51.100.7", 54321))
    assert ip_confiavel(req) == "198.51.100.7"


def test_sem_cabecalho_e_sem_client_devolve_vazio():
    req = _req([], client=None)
    assert ip_confiavel(req) == ""


def test_regressao_geolocalizacao_com_xff_legitimo_de_proxy_real():
    """Cuidado de regressão pedido na correção: um proxy real (não uma cadeia
    forjada) manda um único IP no X-Forwarded-For, e isso continua resolvendo
    normalmente, alimentando o "você está em <cidade>" da home."""
    req = _req([(b"x-forwarded-for", b"203.0.113.42")])
    assert ip_confiavel(req) == "203.0.113.42"


def test_regressao_geolocalizacao_sem_cabecalho_usa_client_host():
    req = _req([], client=("203.0.113.42", 443))
    assert ip_confiavel(req) == "203.0.113.42"


def test_ip_do_pedido_e_client_ip_usam_o_mesmo_helper():
    """A duplicação que causou o bug original (geo.py e auth.py cada um com
    sua própria leitura de XFF) não pode voltar: as duas funções públicas
    resolvem para o mesmo valor do helper único."""
    from app.auth import client_ip
    from app.services.geo import ip_do_pedido

    req = _req([(b"x-forwarded-for", b"forjado, 203.0.113.9")])
    assert ip_do_pedido(req) == "203.0.113.9"
    assert client_ip(req) == "203.0.113.9"
