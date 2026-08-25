"""Item 2 do conserto pós-lançamento (19/08): as duas imagens decorativas da
página /about (listras diagonais, ao lado de "Há mais de 10 anos...", e
meio-tom de bolinhas, ao lado de "Atuo na direção de arte...") eram assets
estáticos fixos (`/static/img/about-1.webp` e `about-2.webp`), sem campo
nenhum no admin — o dono não tinha como trocar.

Viram dois campos de imagem do Profile (`about_img_1`, `about_img_2`), no
mesmo pipeline de upload do resto do admin (save_upload/delete_media_files),
com fallback para o asset estático quando vazios — nada quebra sem upload.
"""
import asyncio

from app.config import settings
from app.models import Profile
from app.routers.admin import profile_save

from ._multipart_de_verdade import png_bytes, post_multipart


def _campo_arquivo(nome: str, cor: str = "green") -> dict:
    return {nome: (f"{nome}.png", png_bytes(cor), "image/png")}


def test_upload_about_img_1_grava_no_perfil_e_no_disco(db):
    request = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, _campo_arquivo("about_img_1"))
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    caminho_gravado = prof.data.get("about_img_1", "")
    assert caminho_gravado, "about_img_1 precisa ter sido gravado no perfil"
    assert (settings.upload_dir / caminho_gravado).is_file()


def test_upload_about_img_2_grava_no_perfil_e_no_disco(db):
    request = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, _campo_arquivo("about_img_2", "blue"))
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    caminho_gravado = prof.data.get("about_img_2", "")
    assert caminho_gravado, "about_img_2 precisa ter sido gravado no perfil"
    assert (settings.upload_dir / caminho_gravado).is_file()


def test_trocar_about_img_1_apaga_a_versao_anterior_do_disco(db):
    r1 = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, _campo_arquivo("about_img_1", "green"))
    asyncio.run(profile_save(r1, db, None))
    prof = db.get(Profile, 1)
    caminho_antigo = settings.upload_dir / prof.data["about_img_1"]
    assert caminho_antigo.is_file()

    r2 = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, _campo_arquivo("about_img_1", "red"))
    asyncio.run(profile_save(r2, db, None))

    prof = db.get(Profile, 1)
    caminho_novo = settings.upload_dir / prof.data["about_img_1"]
    assert caminho_novo != caminho_antigo
    assert caminho_novo.is_file()
    assert not caminho_antigo.is_file(), "a versão anterior tem que sumir do disco"


def test_excluir_about_img_1_volta_o_campo_a_vazio_e_apaga_do_disco(db):
    r1 = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, _campo_arquivo("about_img_1"))
    asyncio.run(profile_save(r1, db, None))
    prof = db.get(Profile, 1)
    caminho_antigo = settings.upload_dir / prof.data["about_img_1"]
    assert caminho_antigo.is_file()

    r2 = post_multipart("/admin/profile", {"csrf": "teste-csrf", "about_img_1_limpar": "1"}, {})
    asyncio.run(profile_save(r2, db, None))

    prof = db.get(Profile, 1)
    assert prof.data.get("about_img_1", "") == ""
    assert not caminho_antigo.is_file()


def test_excluir_about_img_2_volta_o_campo_a_vazio(db):
    r1 = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, _campo_arquivo("about_img_2"))
    asyncio.run(profile_save(r1, db, None))

    r2 = post_multipart("/admin/profile", {"csrf": "teste-csrf", "about_img_2_limpar": "1"}, {})
    asyncio.run(profile_save(r2, db, None))

    prof = db.get(Profile, 1)
    assert prof.data.get("about_img_2", "") == ""


def test_enviar_arquivo_novo_vence_marca_de_excluir_no_mesmo_envio(db):
    """Enviar um arquivo novo e marcar 'excluir' no mesmo request é
    contradição — quem escolheu o arquivo quer o arquivo (mesma regra da
    capa do case, ver app/routers/admin.py)."""
    request = post_multipart(
        "/admin/profile",
        {"csrf": "teste-csrf", "about_img_1_limpar": "1"},
        _campo_arquivo("about_img_1"),
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert prof.data.get("about_img_1", ""), "o envio vence a marca de excluir"
