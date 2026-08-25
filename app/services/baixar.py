"""Baixar uma imagem de um endereço colado pelo visitante.

Pedir ao servidor que busque uma URL que o visitante escolheu é um pedido
perigoso por natureza: quem cola o endereço decide para onde o servidor vai
falar. Sem cuidado, isso vira uma porta para varrer a rede interna do próprio
VPS — o navegador da pessoa não alcança `127.0.0.1` nem `10.x`, mas o servidor
alcança.

Por isso aqui há três cercas, nesta ordem:

1. só http e https, mais nada (nada de `file://`, `gopher://`, `data:`);
2. o endereço é resolvido antes de conectar, e todo IP privado, de loopback,
   de link-local ou reservado é recusado — inclusive quando aparece só depois
   de um redirecionamento;
3. o que volta tem que ser imagem, e cabe num teto de tamanho, com prazo curto.

O arquivo nunca é gravado em disco: os bytes vão direto para a comparação e
morrem ali.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

TIPOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
TETO = 8 * 1024 * 1024      # 8 MB, o mesmo limite do upload
PRAZO = 8.0                 # segundos; endereço lento não trava a busca
REDIRECIONAMENTOS = 3


class RecusadoError(Exception):
    """Motivo em uma palavra, para o front escolher a mensagem."""


def _ip_publico(host: str) -> None:
    """Levanta se o host resolver para qualquer coisa que não seja internet."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise RecusadoError("host")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise RecusadoError("privado")


def _confere(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise RecusadoError("esquema")
    _ip_publico(p.hostname)
    return url


def imagem(url: str) -> bytes:
    """Bytes da imagem, ou RecusadoError com o motivo."""
    alvo = _confere((url or "").strip())

    # os redirecionamentos são seguidos à mão para conferir cada salto: seguir
    # automático deixaria um endereço público apontar para um interno no segundo pulo
    with httpx.Client(timeout=PRAZO, follow_redirects=False,
                      headers={"User-Agent": "leandrofurtado.com.br/busca-por-imagem"}) as c:
        for _ in range(REDIRECIONAMENTOS + 1):
            r = c.get(alvo)
            if r.is_redirect and r.headers.get("location"):
                alvo = _confere(str(r.next_request.url))
                continue

            if r.status_code != 200:
                raise RecusadoError("resposta")
            if (r.headers.get("content-type", "").split(";")[0].strip().lower()) not in TIPOS:
                raise RecusadoError("tipo")
            dados = r.content
            if not dados or len(dados) > TETO:
                raise RecusadoError("tamanho")
            return dados

    raise RecusadoError("redirecionamentos")
