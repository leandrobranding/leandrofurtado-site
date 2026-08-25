"""Upload de imagem na newsletter, fim a fim, com corpo multipart de verdade.

O irmão do Crítico 1 da Tarefa 5 do Nodal (rodada 1 de revisão): as duas
rotas de upload de app/routers/admin_nl.py checavam
`isinstance(arquivo, UploadFile)` contra o `UploadFile` do FastAPI, e
`request.form()` só devolve `starlette.datastructures.UploadFile` — a mãe
da classe do FastAPI, nunca a filha. O `isinstance` dava False sempre:

- POST /admin/newsletter/salvar descartava a imagem da campanha em
  silêncio (`camp.image` continuava vazio, e a rota respondia 303 como se
  tivesse salvo).
- POST /admin/newsletter/upload (upload de dentro do editor) respondia
  sempre 400 "sem arquivo", mesmo com um arquivo de verdade no corpo.

Este arquivo prova o resultado certo com multipart de verdade, sem
monkeypatch em save_upload nem em request.form() — o mesmo padrão de
tests/test_admin_case_capa_disco.py.
"""
import asyncio
import json

from app.config import settings
from app.models import Campaign
from app.routers.admin_nl import salvar, upload_bloco

from ._multipart_de_verdade import png_bytes, post_multipart


def test_salvar_campanha_recebe_a_imagem_de_verdade(db):
    request = post_multipart(
        "/admin/newsletter/salvar",
        {"csrf": "teste-csrf", "subject": "Campanha de teste"},
        {"image": ("capa.png", png_bytes("red"), "image/png")},
    )
    resp = asyncio.run(salvar(request, db))
    assert resp.status_code == 303

    camp = db.query(Campaign).filter_by(subject="Campanha de teste").one()
    assert camp.image, "a imagem da campanha foi descartada em silêncio"
    caminho = settings.upload_dir / camp.image
    assert caminho.is_file(), (
        f"camp.image aponta para {camp.image}, que não existe no disco")


def test_upload_do_editor_aceita_um_arquivo_de_verdade(db):
    request = post_multipart(
        "/admin/newsletter/upload",
        {"csrf": "teste-csrf"},
        {"file": ("bloco.png", png_bytes("blue"), "image/png")},
    )
    resp = asyncio.run(upload_bloco(request, db))
    assert resp.status_code == 200, (
        "a rota respondia sempre 400 'sem arquivo', mesmo recebendo um")
    corpo = json.loads(resp.body)
    assert corpo["ok"] is True
    caminho = settings.upload_dir / corpo["src"]
    assert caminho.is_file()


def test_upload_do_editor_sem_arquivo_continua_recusando(db):
    """O outro lado: campo ausente de verdade (sem multipart, sem "file")
    continua sendo recusado — a correção não pode virar "aceita qualquer
    coisa"."""
    request = post_multipart(
        "/admin/newsletter/upload",
        {"csrf": "teste-csrf"},
        {},
    )
    resp = asyncio.run(upload_bloco(request, db))
    assert resp.status_code == 400
    assert json.loads(resp.body)["erro"] == "sem arquivo"
