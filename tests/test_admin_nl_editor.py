"""Testa o editor de newsletter contra os mesmos dois defeitos do case.

O compositor de blocos da campanha tinha a mesma dupla de problemas, com uma
diferença: aqui a perda era ainda mais silenciosa, porque o json.loads("")
estourava e o except gravava lista vazia sem dizer nada.
"""
import asyncio
import html
import json
import re

import pytest
from starlette.requests import Request

from app.models import Campaign
from app.routers.admin_nl import editar

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
def campanha(db):
    camp = Campaign(subject="Campanha de teste",
                    blocks=[{"t": "texto", "v": VENENO}, {"t": "texto", "v": "segundo"}])
    db.add(camp)
    db.commit()
    return camp


def _corpo(resposta) -> str:
    return resposta.body.decode()


def test_conteudo_com_closing_script_nao_fecha_a_tag_cedo(db, campanha):
    corpo = _corpo(asyncio.run(editar(campanha.id, _get_de("/admin/newsletter/editar/1"), db)))

    tag = re.search(r'<script[^>]*id="blocosIniciais"[^>]*>(.*?)</script>', corpo, re.S)
    assert tag, "a tag do estado inicial sumiu do editor"

    blocos = json.loads(tag.group(1))
    assert blocos[0]["v"] == VENENO
    assert "<script>alert(1)</script>" not in corpo


def test_campo_oculto_de_blocos_nasce_com_o_conteudo_real(db, campanha):
    """Campo vazio virava json.loads("") -> except -> blocos zerados, sem aviso."""
    corpo = _corpo(asyncio.run(editar(campanha.id, _get_de("/admin/newsletter/editar/1"), db)))

    campo = re.search(r'name="blocks"[^>]*value="([^"]*)"', corpo)
    assert campo, "o campo escondido dos blocos sumiu do editor"
    assert campo.group(1) != "", "o campo nasceu vazio: salvar sem JavaScript zeraria a campanha"

    enviado = json.loads(html.unescape(campo.group(1)))
    assert len(enviado) == 2
    assert enviado[0]["v"] == VENENO
