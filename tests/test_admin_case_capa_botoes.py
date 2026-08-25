"""Excluir capa e excluir vídeo — os dois caminhos que faltavam no formulário.

Até aqui só existia trocar: quem subia a capa errada não tinha volta, e o vídeo
do hover não tinha nem como sair nem como saber qual estava lá.

Os testes usam disco de verdade, sem monkeypatch, pelo mesmo motivo dos vizinhos
em test_admin_case_capa_disco.py: o defeito que apagava a capa no instante em
que ela era salva passou por uma suíte verde porque nenhum teste tocava em
arquivo real.
"""
import asyncio

import pytest

from app.config import settings
from app.models import Case
from app.routers.admin import apply_case_form

from ._multipart_de_verdade import png_bytes, post_multipart


def _case_com_capa(db) -> Case:
    """Um case já salvo com capa no disco — o estado de quem vai excluir."""
    case = Case(title_pt="", slug="")
    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/new",
                       {"csrf": "teste-csrf", "title_pt": "Case de teste"},
                       {"cover_image": ("capa.png", png_bytes("red"), "image/png")}),
        db, case))
    assert (settings.upload_dir / case.cover_image).is_file()
    return case


def test_excluir_capa_limpa_o_campo_e_o_disco(db):
    case = _case_com_capa(db)
    antiga = case.cover_image

    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/1",
                       {"csrf": "teste-csrf", "title_pt": "Case de teste",
                        "capa_limpar": "1"}, {}),
        db, case))

    assert case.cover_image == ""
    assert not (settings.upload_dir / antiga).exists(), (
        "o arquivo continuou no disco: excluir a capa que ninguém mais aponta "
        "e deixar os seis arquivos lá é o vazamento que delete_media_files existe "
        "para evitar")


def test_excluir_capa_leva_junto_a_imagem_de_compartilhamento(db):
    """`seo_image` é a capa. Se a capa sai e a de compartilhamento fica, o
    WhatsApp continua mostrando uma imagem que o case não tem mais."""
    case = _case_com_capa(db)
    assert case.seo_image == case.cover_image

    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/1",
                       {"csrf": "teste-csrf", "title_pt": "Case de teste",
                        "capa_limpar": "1"}, {}),
        db, case))

    assert case.seo_image == ""


def test_enviar_e_marcar_excluir_no_mesmo_envio_vence_o_envio(db):
    """Quem escolheu um arquivo novo quer o arquivo novo. Deixar a exclusão
    ganhar apagaria justamente o que a pessoa acabou de escolher — e ela veria
    a tela voltar vazia sem entender por quê."""
    case = _case_com_capa(db)

    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/1",
                       {"csrf": "teste-csrf", "title_pt": "Case de teste",
                        "capa_limpar": "1"},
                       {"cover_image": ("nova.png", png_bytes("blue"), "image/png")}),
        db, case))

    assert case.cover_image, "a capa nova sumiu"
    assert (settings.upload_dir / case.cover_image).is_file()


def test_excluir_video_limpa_o_campo_e_o_disco(db):
    """O vídeo do hover não tinha caminho de saída nenhum."""
    case = _case_com_capa(db)
    case.cover_video = "casos/video-antigo-aabbccdd.mp4"
    caminho = settings.upload_dir / case.cover_video
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"nao e video de verdade, e um arquivo de verdade")

    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/1",
                       {"csrf": "teste-csrf", "title_pt": "Case de teste",
                        "video_limpar": "1"}, {}),
        db, case))

    assert case.cover_video == ""
    assert not caminho.exists()


def test_excluir_video_nao_toca_na_capa(db):
    """Botões vizinhos que fazem a mesma coisa é o defeito clássico de um bloco
    com quatro ações — e o estado inicial tem capa de verdade, não vazia, para
    o teste não passar por coincidência."""
    case = _case_com_capa(db)
    capa = case.cover_image
    case.cover_video = "casos/video-antigo-aabbccdd.mp4"
    caminho = settings.upload_dir / case.cover_video
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"conteudo")

    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/1",
                       {"csrf": "teste-csrf", "title_pt": "Case de teste",
                        "video_limpar": "1"}, {}),
        db, case))

    assert case.cover_image == capa
    assert (settings.upload_dir / capa).is_file()


def test_excluir_capa_de_case_que_nao_tem_capa_nao_estoura(db):
    """Marcar excluir num case sem capa é clique inofensivo, não erro 500."""
    case = Case(title_pt="", slug="")
    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/new",
                       {"csrf": "teste-csrf", "title_pt": "Sem capa",
                        "capa_limpar": "1", "video_limpar": "1"}, {}),
        db, case))
    # falsy, e não `== ""`: um Case recém-criado nasce com None nesses campos,
    # e exigir string vazia aqui testaria o valor padrão do modelo em vez do
    # que este teste existe para provar — que marcar excluir sem ter o que
    # excluir não derruba a rota
    assert not case.cover_image
    assert not case.cover_video


def test_formulario_recusado_nao_apaga_a_capa_que_o_botao_pediu_para_excluir(db):
    """A exclusão é intenção, não execução imediata: se qualquer outro campo do
    formulário for recusado, o banco faz rollback e o disco não — então o
    arquivo tem que continuar lá, como a capa antiga já continua."""
    case = _case_com_capa(db)
    antiga = case.cover_image

    with pytest.raises(ValueError):
        asyncio.run(apply_case_form(
            post_multipart("/admin/cases/1",
                           {"csrf": "teste-csrf", "title_pt": "Case de teste",
                            "capa_limpar": "1"},
                           # vídeo que não é vídeo: recusa o formulário inteiro
                           {"cover_video": ("nao.png", png_bytes("green"), "image/png")}),
            db, case))

    assert (settings.upload_dir / antiga).is_file(), (
        "a capa foi apagada mesmo com o formulário recusado — o banco volta "
        "atrás e passa a apontar para um arquivo que não existe mais")


def test_capa_que_sumiu_do_disco_e_avisada_na_tela(db):
    """O defeito já consertado deixou cases apontando para arquivo que não
    existe mais — o `maratona-internacional-do-parana`, medido no servidor.

    Sem este aviso a tela mostra o ícone de imagem quebrada do navegador, que a
    pessoa lê como "a internet falhou" e não como "este arquivo não existe".
    """
    from app.routers.admin import case_form_ctx

    case = _case_com_capa(db)
    assert case_form_ctx(db, case)["capa_sumiu"] is False

    (settings.upload_dir / case.cover_image).unlink()
    assert case_form_ctx(db, case)["capa_sumiu"] is True


def test_case_sem_capa_nao_e_confundido_com_capa_sumida(db):
    """São dois estados diferentes e a tela diz coisas diferentes: "sem capa"
    é normal, "arquivo não encontrado" é problema."""
    from app.models import Case
    from app.routers.admin import case_form_ctx

    assert case_form_ctx(db, Case(title_pt="Novo", slug="novo"))["capa_sumiu"] is False
    assert case_form_ctx(db, None)["capa_sumiu"] is False
