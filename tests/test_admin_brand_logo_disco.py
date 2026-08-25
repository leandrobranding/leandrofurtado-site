"""Upload de logo de marca, com um UploadFile de verdade.

`brand_logo_upload` recebe o arquivo como parâmetro da própria função
(`file: UploadFile = File(...)`), não via `request.form()` — então não
precisa de corpo multipart: um `fastapi.UploadFile` sobre `BytesIO` já basta
(o mesmo caso de `tests/_multipart_de_verdade.py::arquivo_upload`, só que
com conteúdo de SVG em vez de PNG).

Cobertura que faltava, apontada pela revisão da rodada 1 de correção da
Tarefa 5 do Nodal: nenhum teste até aqui exercitava esta rota com um
arquivo de verdade chegando pelo caminho que o navegador faz — a mesma
categoria de buraco que produziu os três defeitos da sequência.
"""
import asyncio
import io

from fastapi import UploadFile
from starlette.requests import Request

from app.config import settings
from app.routers.admin import brand_logo_upload

SVG_VALIDO = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
    b'<rect width="100" height="60"/></svg>'
)


def _svg_upload(nome_arquivo: str, conteudo: bytes = SVG_VALIDO) -> UploadFile:
    return UploadFile(io.BytesIO(conteudo), filename=nome_arquivo)


def _post_de(caminho: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "headers": [],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": {"csrf": "teste-csrf", "user": "leandro"},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_logo_da_marca_grava_no_disco_de_verdade(db):
    resp = asyncio.run(brand_logo_upload(
        _post_de("/admin/brands/logo"), db, csrf="teste-csrf",
        name="Marca de Teste", file=_svg_upload("marca-de-teste.svg")))
    assert resp.status_code == 303
    assert "logo_err" not in resp.headers.get("location", "")

    caminho = settings.upload_dir / "clients" / "marca-de-teste.svg"
    assert caminho.is_file(), "o logo não chegou a ser gravado no disco"
    assert "<svg" in caminho.read_text()[:200]


def test_logo_invalido_nao_grava_nada(db):
    """O outro lado: um arquivo que não é SVG (falta "<svg") continua sendo
    recusado — a rota não vira "aceita qualquer coisa" para o svg passar."""
    resp = asyncio.run(brand_logo_upload(
        _post_de("/admin/brands/logo"), db, csrf="teste-csrf",
        name="Marca Ruim", file=_svg_upload("marca-ruim.svg", b"nao e svg nenhum")))
    assert "logo_err" in resp.headers.get("location", "")
    assert not (settings.upload_dir / "clients" / "marca-ruim.svg").exists()
