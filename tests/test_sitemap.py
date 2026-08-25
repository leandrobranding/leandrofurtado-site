"""O sitemap é o que faz o Nodal existir para o buscador."""
import asyncio
import re
import xml.etree.ElementTree as ET

import pytest
from starlette.requests import Request

# O Nodal é opcional desde 24/08/2026 (ver app/main.py). Este arquivo importa
# o módulo, então ele inteiro é pulado quando a pasta app/nodal/ não existe.
# `importorskip` e não `pytestmark`: a marca pula os TESTES, mas o import do
# topo já teria estourado antes, na coleta.
pytest.importorskip("app.nodal", reason="módulo app.nodal ausente nesta cópia")

from app.nodal.models import Curso, Situacao
from app.routers.public import sitemap, sitemap_page



def _xml(db) -> str:
    return asyncio.run(sitemap(db)).body.decode()


def _get(caminho: str) -> Request:
    escopo = {"type": "http", "method": "GET", "path": caminho,
              "raw_path": caminho.encode(), "query_string": b"", "headers": [],
              "state": {"clean_path": caminho, "lang": "pt"}, "session": {}}

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(escopo, receber)


def _mapa(db) -> str:
    return asyncio.run(sitemap_page(_get("/mapa-do-site"), db)).body.decode()


def test_curso_publicado_entra_no_sitemap(db):
    db.add(Curso(slug="ia-na-agencia", titulo="IA", publicado=True))
    db.commit()
    assert "/nodal/curso/ia-na-agencia" in _xml(db)


def test_curso_em_rascunho_fica_de_fora(db):
    db.add(Curso(slug="rascunho", titulo="R", publicado=False))
    db.commit()
    assert "/nodal/curso/rascunho" not in _xml(db)


@pytest.mark.parametrize("publicado,publica,deve_aparecer", [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, False),
])
def test_situacao_so_entra_publicada_e_publica(db, publicado, publica, deve_aparecer):
    """As quatro combinações de (publicado, publica): só a dupla True/True entra."""
    db.add(Situacao(slug="s", titulo="S", dor="x", publicado=publicado,
                    publica=publica, blocos=[]))
    db.commit()
    xml = _xml(db)
    assert ("/nodal/situacao/s" in xml) == deve_aparecer


def test_o_catalogo_entra_no_sitemap(db):
    """A porta de entrada do Nodal precisa estar lá, e uma vez só."""
    xml = _xml(db)
    assert xml.count("/nodal</loc>") == 1


def test_slug_com_caractere_especial_nao_quebra_o_xml_inteiro(db):
    """Defesa em profundidade.

    Hoje todo cadastro passa por slugify e nunca produz &, <, > ou aspas —
    mas url() não pode depender disso continuar verdade para sempre. Um `&`
    cru quebra o XML inteiro (não só a entrada estranha), e o buscador
    descarta o arquivo por completo: parece que não existe sitemap nenhum.
    """
    db.add(Curso(slug='a&b<c>"d', titulo="Especial", publicado=True))
    db.commit()
    xml = _xml(db)
    ET.fromstring(xml)  # levanta ParseError se o XML estiver malformado
    assert "<c>" not in xml  # o caractere cru não pode sobreviver ao escape


def _blocos_url(xml: str) -> list[str]:
    return re.findall(r"<url>.*?</url>", xml)


def test_nodal_nao_declara_alternativa_em_ingles_no_sitemap(db):
    """O Nodal não tem tradução: as entradas dele no sitemap não podem
    emitir `xhtml:link` para uma versão em inglês que não existe — o resto
    do site continua declarando a alternativa normalmente."""
    db.add(Curso(slug="ia-na-agencia", titulo="IA", publicado=True))
    db.add(Situacao(slug="aberta", titulo="Aberta", dor="x",
                    publicado=True, publica=True, blocos=[]))
    db.commit()
    xml = _xml(db)
    blocos = _blocos_url(xml)
    blocos_nodal = [b for b in blocos if "/nodal" in b]
    assert len(blocos_nodal) == 3  # catálogo + o curso + a Situação
    assert all('hreflang="en"' not in b for b in blocos_nodal)
    assert all('hreflang="pt-BR"' in b for b in blocos_nodal)  # o pt continua lá
    blocos_resto = [b for b in blocos if "/nodal" not in b]
    assert blocos_resto and all('hreflang="en"' in b for b in blocos_resto)


def test_mapa_do_site_mostra_o_nodal(db):
    db.add(Curso(slug="ia-na-agencia", titulo="Curso Publicado", publicado=True))
    db.add(Situacao(slug="aberta", titulo="Situação Aberta", dor="x",
                    publicado=True, publica=True, blocos=[]))
    db.commit()
    html = _mapa(db)
    assert "/nodal/curso/ia-na-agencia" in html
    assert "Curso Publicado" in html
    assert "/nodal/situacao/aberta" in html
    assert "Situação Aberta" in html


def test_mapa_do_site_esconde_rascunho_e_acervo(db):
    """Rascunho não vaza: nem no texto do link, nem no href."""
    db.add(Curso(slug="rascunho-curso", titulo="Curso Rascunho", publicado=False))
    db.add(Situacao(slug="acervo", titulo="Situação De Acervo", dor="x",
                    publicado=True, publica=False, blocos=[]))
    db.add(Situacao(slug="rascunho-situacao", titulo="Situação Rascunho", dor="x",
                    publicado=False, publica=True, blocos=[]))
    db.commit()
    html = _mapa(db)
    assert "rascunho-curso" not in html
    assert "Curso Rascunho" not in html
    assert "acervo" not in html
    assert "Situação De Acervo" not in html
    assert "rascunho-situacao" not in html
    assert "Situação Rascunho" not in html
