"""Foto do perfil, fim a fim, com disco de verdade — sem monkeypatch.

Mesmo defeito da capa do case (ver
.superpowers/sdd/2026-08-15-nodal-3-camada-visual/conserto-apagar-familia.md),
achado por varredura depois do primeiro conserto: `profile_save`, campo
`photo`, tinha o mesmo `if thumb: delete_media_files(rel)` — apaga a
variante otimizada do MESMO envio um instante depois de ela virar
`data["photo"]`. O campo `cover`, logo abaixo na mesma rota, não tem esse
defeito: grava sempre `rel` (a versão grande), nunca chama
`delete_media_files(rel)`, então não tem irmão para preservar. Por isso só
`photo` ganha teste aqui.
"""
import asyncio

from app.config import settings
from app.models import Profile
from app.routers.admin import profile_save

from ._multipart_de_verdade import png_bytes, post_multipart


def test_foto_do_perfil_grava_e_apaga_no_disco_de_verdade(db):
    """O caminho que data["photo"] recebe precisa existir no disco depois de
    salvar — a mesma asserção que pegou o defeito da capa do case."""
    request = post_multipart(
        "/admin/profile",
        {"csrf": "teste-csrf"},
        {"photo": ("foto.png", png_bytes("green"), "image/png")},
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    caminho_gravado = prof.data.get("photo", "")
    assert caminho_gravado, "a foto precisa ter sido gravada no perfil"
    caminho = settings.upload_dir / caminho_gravado
    assert caminho.is_file(), (
        f"profile.data['photo'] aponta para {caminho_gravado}, "
        "que não existe no disco depois de salvar"
    )
