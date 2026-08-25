"""Ordem do portfólio: mais novo primeiro por padrão, e o filtro ordem=az/za
pelo título no idioma da página — pedidos 1 e 2 do pacote de 17/08 (ver
.superpowers/sdd/2026-08-17-nodal-4-experiencia-do-aluno/pacote-portfolio-brief.md).

`Case.sort` (ordem manual do painel) deixa de valer aqui: é por isso que os
três cases abaixo nascem com um `sort` que discorda da data de cadastro — se
o portfólio ainda escutasse `Case.sort`, a ordem padrão sairia B, A, C em vez
de C, B, A.

A maioria dos testes chama a função da rota direto (padrão de
tests/test_sitemap.py: Request montada à mão, sem TestClient). O último
atravessa a rota HTTP de verdade, com querystring real, como o brief pede.
"""
import asyncio
import datetime as dt
import re
import secrets

from starlette.requests import Request

from app.models import Case
from app.routers.public import portfolio


def _get(caminho: str, lang: str = "pt") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": caminho,
        "raw_path": caminho.encode(), "query_string": b"", "headers": [],
        "state": {"clean_path": caminho, "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def _corpo(db, lang: str = "pt", **kwargs) -> str:
    resp = asyncio.run(portfolio(_get("/portfolio", lang), db, **kwargs))
    return resp.body.decode()


def _ordem_dos_slugs(corpo: str) -> list[str]:
    """A ordem em que os cases aparecem na grade, pelo href de cada card."""
    return re.findall(r'href="(?:/en)?/case/([a-z0-9-]+)"', corpo)


def _tres_cases(db):
    base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    a = Case(slug="a", title_pt="Álvaro", title_en="Alvaro", sort=2,
             created_at=base, published=True, archived=False)
    b = Case(slug="b", title_pt="Bruno", title_en="Bruno", sort=1,
             created_at=base + dt.timedelta(days=1), published=True, archived=False)
    c = Case(slug="c", title_pt="Carlos", title_en="Carlos", sort=3,
             created_at=base + dt.timedelta(days=2), published=True, archived=False)
    db.add_all([a, b, c])
    db.commit()
    return a, b, c


def test_ordem_padrao_e_o_mais_novo_primeiro_por_cadastro(db):
    _tres_cases(db)
    assert _ordem_dos_slugs(_corpo(db)) == ["c", "b", "a"]


def test_ordem_az_pelo_titulo_no_idioma_da_pagina(db):
    _tres_cases(db)
    assert _ordem_dos_slugs(_corpo(db, ordem="az")) == ["a", "b", "c"]


def test_ordem_za_e_o_inverso_do_az(db):
    _tres_cases(db)
    assert _ordem_dos_slugs(_corpo(db, ordem="za")) == ["c", "b", "a"]


def test_ordem_desconhecida_cai_no_padrao(db):
    _tres_cases(db)
    assert _ordem_dos_slugs(_corpo(db, ordem="alfabetica-de-mentirinha")) == ["c", "b", "a"]


def test_ordem_az_usa_o_titulo_em_ingles_na_pagina_em_ingles(db):
    """title_en diverge de title_pt o bastante para inverter a ordem: prova
    que é o idioma da página que decide qual título entra na régua alfabética,
    não sempre o português."""
    a = Case(slug="a", title_pt="Zebra", title_en="Antelope", published=True,
             archived=False, created_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    b = Case(slug="b", title_pt="Abelha", title_en="Zeppelin", published=True,
             archived=False, created_at=dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc))
    db.add_all([a, b])
    db.commit()
    assert _ordem_dos_slugs(_corpo(db, lang="pt", ordem="az")) == ["b", "a"]
    assert _ordem_dos_slugs(_corpo(db, lang="en", ordem="az")) == ["a", "b"]


def test_ordem_entra_no_base_qs_para_paginacao_nao_perder_o_filtro(db):
    corpo = _corpo(db, ordem="az")
    assert "ordem=az" in corpo
    # o padrão não precisa aparecer na querystring — é o padrão
    corpo_padrao = _corpo(db)
    assert "ordem=recentes" not in corpo_padrao


def test_portfolio_http_com_querystring_real_de_ordem():
    """Atravessa a rota do jeito que o navegador atravessa: TestClient, GET
    de verdade com `?ordem=az` na URL — não a função chamada direto com
    kwarg. Isolado por DATA_DIR (tests/conftest.py), nunca toca data/site.db."""
    from starlette.testclient import TestClient

    from app.database import SessionLocal as _SessionLocal
    from app.main import app as _app

    with TestClient(_app):
        pass  # dispara o lifespan (create_all) antes de qualquer INSERT

    sessao = _SessionLocal()
    sufixo = secrets.token_hex(4)
    base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    a = Case(slug=f"http-ordem-abelha-{sufixo}", title_pt="Abelha HTTP",
             published=True, archived=False, created_at=base)
    b = Case(slug=f"http-ordem-zebra-{sufixo}", title_pt="Zebra HTTP",
             published=True, archived=False, created_at=base + dt.timedelta(days=1))
    sessao.add_all([a, b])
    sessao.commit()
    ids = (a.id, b.id)
    try:
        with TestClient(_app) as client:
            resp = client.get("/portfolio?ordem=az")
        assert resp.status_code == 200
        pos_a = resp.text.index(f'href="/case/{a.slug}"')
        pos_b = resp.text.index(f'href="/case/{b.slug}"')
        assert pos_a < pos_b, "Abelha HTTP deveria vir antes de Zebra HTTP em ordem=az"
    finally:
        for cid in ids:
            obj = sessao.get(Case, cid)
            if obj:
                sessao.delete(obj)
        sessao.commit()
        sessao.close()
