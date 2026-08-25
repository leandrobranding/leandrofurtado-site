"""Upload de capa de case, fim a fim, com disco de verdade — sem monkeypatch
em save_upload nem em delete_media_files.

É exatamente o caminho que faltava: hoje não existia nenhum teste cobrindo
`apply_case_form` com um arquivo real chegando pelo formulário multipart, e
foi assim que o defeito (a capa salva no banco apontando para um arquivo que
a própria rota acabara de apagar) chegou em produção. Ver o porquê completo
em .superpowers/sdd/2026-08-15-nodal-3-camada-visual/conserto-apagar-familia.md

Segue o padrão de referência de
tests/nodal/test_admin_cursos.py::test_upload_de_capa_grava_e_apaga_no_disco_de_verdade
adaptado para `apply_case_form`, que só lê `request.form()` — não tem
parâmetro de UploadFile direto — então o upload aqui precisa ser um corpo
multipart de verdade, não um dublê.
"""
import asyncio

import pytest

from app.config import settings
from app.models import Case
from app.routers.admin import apply_case_form

from ._multipart_de_verdade import png_bytes, post_multipart


def test_capa_do_case_grava_e_apaga_no_disco_de_verdade(db):
    """O caminho que `case.cover_image` recebe precisa existir no disco depois
    de salvar. É a asserção que faltava: antes do conserto, o defeito em
    `apply_case_form` apagava exatamente esse arquivo um instante depois de
    gravá-lo no banco (rel e thumb nascem do mesmo envio, mesma família)."""
    case = Case(title_pt="", slug="")
    request = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case de teste"},
        {"cover_image": ("capa.png", png_bytes("red"), "image/png")},
    )
    asyncio.run(apply_case_form(request, db, case))

    assert case.cover_image, "a capa precisa ter sido gravada no case"
    caminho = settings.upload_dir / case.cover_image
    assert caminho.is_file(), (
        f"case.cover_image aponta para {case.cover_image}, "
        "que não existe no disco depois de salvar"
    )


def test_previa_do_site_grava_e_apaga_no_disco_de_verdade(db):
    """Mesmo defeito, segundo lugar onde ele vivia: o upload manual da prévia
    do site também grava em `case.cover_image` pelo mesmo padrão
    `if thumb: apaga o original` — e tinha o mesmo bug."""
    case = Case(title_pt="", slug="")
    request = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case de teste"},
        {"site_previa": ("previa.png", png_bytes("blue"), "image/png")},
    )
    asyncio.run(apply_case_form(request, db, case))

    assert case.cover_image, "a prévia precisa ter virado a capa"
    caminho = settings.upload_dir / case.cover_image
    assert caminho.is_file(), (
        f"case.cover_image aponta para {case.cover_image}, "
        "que não existe no disco depois de salvar"
    )


# --- o irmão do Crítico 2 do Nodal: apply_case_form apagava a capa antiga --
# antes de validar o resto do formulário (achado pela revisão da rodada 1
# de correção da Tarefa 5 do Nodal, aplicado aqui por autorização explícita)


def test_capa_valida_com_video_invalido_nao_apaga_a_capa_antiga(db):
    """O mesmo defeito do Crítico 2, num lugar diferente: cover_image e
    cover_video eram apagados assim que o PRÓPRIO upload validava — antes
    de qualquer validação mais adiante na MESMA função (o outro campo, os
    blocos, a captura do site). Uma capa nova válida chegando junto com um
    cover_video que não é vídeo nenhum recusa o POST inteiro, mas a capa
    ANTIGA (que não tinha nada a ver com o motivo da recusa) sumia do
    disco mesmo assim, com o banco continuando a apontar para ela.

    `db.add` + `db.commit` depois do primeiro envio, e `db.rollback()` depois
    da recusa do segundo, reproduzem exatamente o que `case_edit` faz de
    verdade ao capturar ValueError — sem isso, `case.cover_image` em memória
    nunca reverteria, e a asserção sobre o banco não provaria nada."""
    case = Case(title_pt="Case com capa", slug="case-com-capa-video")
    primeiro = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case com capa"},
        {"cover_image": ("boa.png", png_bytes("red"), "image/png")},
    )
    asyncio.run(apply_case_form(primeiro, db, case))
    db.add(case)
    db.commit()
    capa_boa = case.cover_image
    caminho_bom = settings.upload_dir / capa_boa
    assert caminho_bom.is_file()

    segundo = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case com capa"},
        {"cover_image": ("nova.png", png_bytes("blue"), "image/png"),
         # ".png" no campo de vídeo: kind_for classifica pela extensão, não
         # pelo conteúdo — é exatamente o que faz save_upload devolver
         # kind="image" (não "video") aqui, disparando a recusa
         "cover_video": ("nao-e-video.png", png_bytes("green"), "image/png")},
    )
    with pytest.raises(ValueError, match="vídeo"):
        asyncio.run(apply_case_form(segundo, db, case))
    db.rollback()  # o mesmo que case_edit faz ao capturar a ValueError

    assert case.cover_image == capa_boa, "o banco não pode passar a apontar pra outro lugar"
    assert caminho_bom.is_file(), "a capa antiga não pode sumir do disco numa recusa"


def test_sucesso_com_capa_nova_ainda_apaga_a_antiga_do_disco(db):
    """O caminho simétrico do teste acima: quando o formulário inteiro é
    válido, a capa antiga precisa continuar saindo do disco de verdade —
    trocar perda de dado por vazamento de disco não seria conserto."""
    case = Case(title_pt="Case troca capa", slug="case-troca-capa")
    primeiro = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case troca capa"},
        {"cover_image": ("antiga.png", png_bytes("red"), "image/png")},
    )
    asyncio.run(apply_case_form(primeiro, db, case))
    capa_antiga = case.cover_image
    caminho_antigo = settings.upload_dir / capa_antiga
    assert caminho_antigo.is_file()

    segundo = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case troca capa"},
        {"cover_image": ("nova.png", png_bytes("blue"), "image/png")},
    )
    asyncio.run(apply_case_form(segundo, db, case))

    assert case.cover_image != capa_antiga
    assert not caminho_antigo.exists(), "sucesso precisa continuar apagando a capa antiga"
    assert (settings.upload_dir / case.cover_image).is_file()


def test_video_de_capa_grava_no_disco_de_verdade(db):
    """Cobertura que faltava (apontada pela revisão): cover_video nunca
    tinha um teste passando pela rota com multipart real."""
    case = Case(title_pt="Case com vídeo", slug="case-com-video")
    request = post_multipart(
        "/admin/cases/new",
        {"csrf": "teste-csrf", "title_pt": "Case com vídeo"},
        {"cover_video": ("clipe.mp4", b"conteudo de video de mentira", "video/mp4")},
    )
    asyncio.run(apply_case_form(request, db, case))

    assert case.cover_video, "o vídeo de capa foi descartado"
    caminho = settings.upload_dir / case.cover_video
    assert caminho.is_file(), (
        f"case.cover_video aponta para {case.cover_video}, que não existe no disco")
