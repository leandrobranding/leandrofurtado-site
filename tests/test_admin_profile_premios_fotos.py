"""Última peça do lançamento (19/08): galeria de fotos por prêmio, editável no
admin. Diagnóstico completo em
.superpowers/sdd/2026-08-19-lancamento-site/premios-fotos-report.md.

O que muda em app/routers/admin.py (profile_save):
- cada prêmio ganha `images` (lista de caminhos) no Profile.data, aditivo;
- pareamento foto↔prêmio por ID ESTÁVEL (`award_id` escondido por linha,
  `award_images_{id}` no input de arquivo, `award_img_del_{id}` na checkbox
  de excluir) — não por posição, porque posição não sobrevive a remover uma
  linha do meio (ver o comentário longo em profile_save);
- limite de 6 fotos por prêmio (AWARD_IMAGES_MAX);
- prêmio removido (id que não volta no POST) apaga as fotos dele do disco.
"""
import asyncio

from app.config import settings
from app.models import Profile
from app.routers.admin import AWARD_IMAGES_MAX, profile_save

from ._multipart_de_verdade import png_bytes, post_multipart


def _campo_arquivo(nome: str, cor: str = "green", n: str = "foto.png") -> dict:
    return {nome: (n, png_bytes(cor), "image/png")}


def _campos_um_premio(aid: str = "p1", titulo: str = "Top de Marketing") -> dict:
    return {
        "csrf": "teste-csrf",
        "award_id": aid,
        "award_title_pt": titulo, "award_title_en": titulo,
        "award_year": "2026", "award_desc_pt": "", "award_desc_en": "",
    }


def test_upload_de_foto_entra_na_galeria_do_premio_certo(db):
    request = post_multipart(
        "/admin/profile", _campos_um_premio(),
        _campo_arquivo("award_images_p1"),
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    awards = prof.data["awards"]
    assert len(awards) == 1
    assert awards[0]["id"] == "p1"
    assert len(awards[0]["images"]) == 1
    assert (settings.upload_dir / awards[0]["images"][0]).is_file()


def test_duas_fotos_no_mesmo_upload_entram_as_duas(db):
    request = post_multipart(
        "/admin/profile", _campos_um_premio(),
        {"award_images_p1": [
            ("a.png", png_bytes("green"), "image/png"),
            ("b.png", png_bytes("blue"), "image/png"),
        ]},
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert len(prof.data["awards"][0]["images"]) == 2


def test_excluir_uma_foto_individual_mantem_as_outras(db):
    r1 = post_multipart(
        "/admin/profile", _campos_um_premio(),
        {"award_images_p1": [
            ("a.png", png_bytes("green"), "image/png"),
            ("b.png", png_bytes("blue"), "image/png"),
        ]},
    )
    asyncio.run(profile_save(r1, db, None))
    prof = db.get(Profile, 1)
    imagens = prof.data["awards"][0]["images"]
    assert len(imagens) == 2
    apagar, sobrevive = imagens[0], imagens[1]
    caminho_apagado = settings.upload_dir / apagar

    campos = _campos_um_premio()
    campos["award_img_del_p1"] = apagar
    r2 = post_multipart("/admin/profile", campos, {})
    asyncio.run(profile_save(r2, db, None))

    prof = db.get(Profile, 1)
    imagens_finais = prof.data["awards"][0]["images"]
    assert imagens_finais == [sobrevive]
    assert not caminho_apagado.is_file(), "a foto excluída precisa sumir do disco"
    assert (settings.upload_dir / sobrevive).is_file(), "a foto que ficou não pode ser tocada"


def test_upload_respeita_o_limite_de_seis_fotos_por_premio(db):
    campos = _campos_um_premio()
    arquivos = {"award_images_p1": [
        (f"foto{i}.png", png_bytes("green"), "image/png") for i in range(8)
    ]}
    request = post_multipart("/admin/profile", campos, arquivos)
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert len(prof.data["awards"][0]["images"]) == AWARD_IMAGES_MAX == 6


def test_remover_premio_no_admin_apaga_as_fotos_dele_do_disco(db):
    r1 = post_multipart(
        "/admin/profile", _campos_um_premio(),
        _campo_arquivo("award_images_p1"),
    )
    asyncio.run(profile_save(r1, db, None))
    prof = db.get(Profile, 1)
    caminho = settings.upload_dir / prof.data["awards"][0]["images"][0]
    assert caminho.is_file()

    # o form não manda mais award_id nenhum para "p1" — o del-row do JS
    # simplesmente remove a linha inteira do DOM antes de submeter.
    r2 = post_multipart("/admin/profile", {"csrf": "teste-csrf"}, {})
    asyncio.run(profile_save(r2, db, None))

    prof = db.get(Profile, 1)
    assert prof.data["awards"] == []
    assert not caminho.is_file(), "as fotos do prêmio removido não podem ficar órfãs no disco"


def test_pareamento_por_id_nao_vaza_foto_entre_premios_ao_remover_linha_do_meio(db):
    """O cenário perigoso do desenho: três prêmios A, B, C, cada um com uma
    foto própria. O admin remove a linha do MEIO (B) — igual ao del-row do
    JS, puro DOM, sem re-render do servidor — e submete só A e C. Se o
    pareamento fosse por posição (award_images repetido, casado pelo índice
    da linha), a foto que era de C herdaria o índice que era de B. Pareado
    por id, cada prêmio some ou sobrevive com a foto que é dele."""
    r1 = post_multipart(
        "/admin/profile",
        {
            "csrf": "teste-csrf",
            "award_id": ["a", "b", "c"],
            "award_title_pt": ["Prêmio A", "Prêmio B", "Prêmio C"],
            "award_title_en": ["Award A", "Award B", "Award C"],
            "award_year": ["2024", "2025", "2026"],
            "award_desc_pt": ["", "", ""],
            "award_desc_en": ["", "", ""],
        },
        {
            "award_images_a": ("a.png", png_bytes("red"), "image/png"),
            "award_images_b": ("b.png", png_bytes("green"), "image/png"),
            "award_images_c": ("c.png", png_bytes("blue"), "image/png"),
        },
    )
    asyncio.run(profile_save(r1, db, None))
    prof = db.get(Profile, 1)
    por_id = {a["id"]: a for a in prof.data["awards"]}
    assert len(por_id["a"]["images"]) == 1
    assert len(por_id["b"]["images"]) == 1
    assert len(por_id["c"]["images"]) == 1
    foto_a, foto_b, foto_c = (
        por_id["a"]["images"][0], por_id["b"]["images"][0], por_id["c"]["images"][0],
    )
    caminho_b = settings.upload_dir / foto_b

    # remove a linha do meio (B) — só A e C voltam no POST seguinte
    r2 = post_multipart(
        "/admin/profile",
        {
            "csrf": "teste-csrf",
            "award_id": ["a", "c"],
            "award_title_pt": ["Prêmio A", "Prêmio C"],
            "award_title_en": ["Award A", "Award C"],
            "award_year": ["2024", "2026"],
            "award_desc_pt": ["", ""],
            "award_desc_en": ["", ""],
        },
        {},
    )
    asyncio.run(profile_save(r2, db, None))

    prof = db.get(Profile, 1)
    por_id = {a["id"]: a for a in prof.data["awards"]}
    assert set(por_id.keys()) == {"a", "c"}
    assert por_id["a"]["images"] == [foto_a], "a foto de A não pode ter virado a de outro prêmio"
    assert por_id["c"]["images"] == [foto_c], "a foto de C não pode ter virado a de outro prêmio"
    assert (settings.upload_dir / foto_a).is_file()
    assert (settings.upload_dir / foto_c).is_file()
    assert not caminho_b.is_file(), "a foto do prêmio B (removido) precisa sumir do disco"


def test_form_sem_award_id_nenhum_ainda_gera_id_e_nao_quebra(db):
    """Formulário antigo em cache (antes deste deploy) não manda award_id
    nenhum — zip_longest com fillvalue='' cobre isso, e o save gera um id
    novo na hora, sem perder a linha."""
    campos = _campos_um_premio()
    del campos["award_id"]
    request = post_multipart("/admin/profile", campos, {})
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert len(prof.data["awards"]) == 1
    assert prof.data["awards"][0]["id"], "um id precisa ter sido gerado"
    assert prof.data["awards"][0]["images"] == []
