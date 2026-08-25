"""Cobre o cabeçalho de segurança que só existe com o middleware no ar.

Todo outro teste do Nodal chama a função de rota direto, sem o `SecurityHeadersMiddleware`
no meio — nenhum deles seria capaz de flagrar uma CSP que bloqueia o vídeo da Cloudflare
Stream. Este arquivo sobe o app de verdade, com TestClient, para fechar essa classe de
regressão: qualquer domínio que falte em `frame-src` (ou em qualquer outra diretiva)
aparece aqui, não só no console do navegador de quem revisar manualmente.

Usa o `data/` isolado que tests/conftest.py monta antes de app.config carregar — nenhuma
consulta daqui toca data/site.db.
"""
from starlette.testclient import TestClient

from app.main import app


def _csp() -> str:
    with TestClient(app) as client:
        resposta = client.get("/nodal")
    return resposta.headers["content-security-policy"]


def test_frame_src_libera_o_player_da_cloudflare_stream():
    """iframe.videodelivery.net é o reprodutor da Cloudflare Stream: sem ele
    na CSP, o navegador bloqueia o próprio iframe do vídeo de aula — o defeito
    que a revisão flagrou abrindo o console (ver app/templates/nodal/_blocos.html)."""
    csp = _csp()
    frame_src = next(d for d in csp.split("; ") if d.startswith("frame-src"))
    assert "https://iframe.videodelivery.net" in frame_src.split()


def test_frame_src_continua_liberando_os_players_que_ja_existiam():
    """A adição não pode empurrar nenhum dos três domínios antigos para fora."""
    csp = _csp()
    frame_src = next(d for d in csp.split("; ") if d.startswith("frame-src"))
    dominios = frame_src.split()
    for esperado in ("https://www.instagram.com", "https://www.youtube-nocookie.com",
                     "https://player.vimeo.com"):
        assert esperado in dominios
