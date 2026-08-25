"""Testa o compositor de blocos do case contra dois defeitos que custaram caro.

Os dois já aconteceram de verdade neste projeto e foram corrigidos na branch
main; esta cobertura existe para eles não voltarem. Segue o padrão de
tests/test_admin_settings.py — monta a Request à mão, sem TestClient nem
servidor, e chama a função da rota direto.
"""
import asyncio
import html
import json
import re

import pytest
from starlette.requests import Request

from app.models import Case, MediaItem
from app.routers.admin import case_edit_page

# Texto que um case de portfólio de quem faz web tem toda chance de conter.
# Não é ataque: é alguém explicando como se fecha uma tag.
VENENO = 'para fechar escreve </script><script>alert(1)</script> e pronto'


def _get_de(caminho: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
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


@pytest.fixture()
def case_com_pagina(db):
    """Um case com três blocos, o primeiro com texto hostil na legenda."""
    case = Case(slug="case-de-teste", title_pt="Case de teste")
    db.add(case)
    db.flush()
    for i in range(3):
        db.add(MediaItem(case_id=case.id, kind="image", src=f"/media/f{i}.jpg",
                         caption_pt=(VENENO if i == 0 else f"foto {i}")))
    db.commit()
    return case


def _corpo(resposta) -> str:
    return resposta.body.decode()


def test_conteudo_com_closing_script_nao_fecha_a_tag_cedo(db, case_com_pagina):
    """A tag que carrega o estado inicial precisa sobreviver ao próprio conteúdo.

    Com `| safe`, o `</script>` da legenda fechava a tag no meio: o resto do
    JSON virava HTML solto e o navegador executava o que viesse depois.
    """
    corpo = _corpo(asyncio.run(case_edit_page(case_com_pagina.id, _get_de("/admin/cases/1"), db)))

    tag = re.search(r'<script[^>]*data-cp-inicial[^>]*>(.*?)</script>', corpo, re.S)
    assert tag, "a tag do estado inicial sumiu do formulário"

    # o conteúdo da tag ainda é JSON íntegro, com a legenda inteira dentro
    blocos = json.loads(tag.group(1))
    assert blocos[0]["caption"] == VENENO

    # e o script hostil não sobrou solto na página
    assert "<script>alert(1)</script>" not in corpo


def test_campo_oculto_de_blocos_nasce_com_o_conteudo_real(db, case_com_pagina):
    """Sem JavaScript, o formulário tem que devolver a página que recebeu.

    O campo nascia com "[]" fixo e só o JavaScript escrevia o valor de verdade.
    Se o script não rodasse, salvar mandava lista vazia — e a rota entende
    lista vazia como ordem legítima: troca a página do case e apaga os
    arquivos do disco. Corrigir um título podia destruir o case inteiro.
    """
    corpo = _corpo(asyncio.run(case_edit_page(case_com_pagina.id, _get_de("/admin/cases/1"), db)))

    campo = re.search(r'name="blocos"[^>]*value="([^"]*)"', corpo)
    assert campo, "o campo escondido dos blocos sumiu do formulário"

    # o navegador desescapa o atributo antes de enviar; fazemos o mesmo
    enviado = json.loads(html.unescape(campo.group(1)))
    assert len(enviado) == 3, "o campo não nasceu com a página que já existe"
    assert enviado[0]["caption"] == VENENO

    # e as aspas do texto não escapam do atributo
    assert "&#34;" in campo.group(1) or '\\"' in campo.group(1)
