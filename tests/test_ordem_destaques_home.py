"""Ordem dos cases em destaque na home (19/08).

Até aqui não havia como o dono escolher a ordem dos destaques pelo painel:
o bloco "CASES EM DESTAQUE" (`.fwork`) saía na ordem que os cases vinham do
banco, sem campo nenhum para arranjar. `Case.destaque_ordem` é esse campo —
editável em `/admin/cases/{id}` — e a home passa a ordenar os destaques por
ele, menor primeiro, com empate resolvido pelo critério que já existia
(a ordem de `cases`, vinda de `Case.sort`/`created_at`).

Segue o padrão de tests/test_mosaico_de_cases_home.py: `Request` montada à
mão, sem TestClient nem servidor, chamando a rota `home` direto.
"""
import asyncio
import datetime as dt

from starlette.requests import Request

from app.models import Case
from app.routers.public import home


def _get(lang: str = "pt") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "raw_path": b"/", "query_string": b"", "headers": [],
        "state": {"clean_path": "/", "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def _home(db, lang: str = "pt") -> str:
    resp = asyncio.run(home(_get(lang), db))
    return resp.body.decode()


def _case(slug: str, **kw) -> Case:
    base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    campos = {"published": True, "archived": False, "featured": True,
              "created_at": base, **kw}
    return Case(slug=slug, title_pt=slug, title_en=slug, **campos)


def _ordem_dos_titulos(corpo: str, slugs: list[str]) -> list[str]:
    """A posição de cada título de destaque no HTML, na ordem em que aparecem.

    O título do case é o próprio slug (`_case` monta assim), então basta achar
    onde cada um aparece pela primeira vez no corpo — ele só aparece uma vez,
    no `<a class="fwork-title">` — e ordenar pela posição."""
    posicoes = [(corpo.index(s), s) for s in slugs]
    return [s for _, s in sorted(posicoes)]


def test_destaques_renderizam_na_ordem_do_campo_nao_do_cadastro(db):
    """Três cases cadastrados como 3, 1, 2 (id de criação) mas com
    destaque_ordem 2, 1, 3 — o HTML tem que sair 1, 2, 3."""
    db.add_all([
        _case("terceiro", destaque_ordem=2),
        _case("primeiro", destaque_ordem=1),
        _case("segundo", destaque_ordem=3),
    ])
    db.commit()

    corpo = _home(db)

    assert _ordem_dos_titulos(corpo, ["primeiro", "terceiro", "segundo"]) == [
        "primeiro", "terceiro", "segundo"]


def test_empate_na_ordem_mantem_o_criterio_atual(db):
    """Dois destaques sem ordem explícita (default 999, empatados) mantêm a
    ordem que já valia antes — a de `Case.sort`/`created_at`, vinda de
    `published_cases`."""
    mais_novo = dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc)
    mais_velho = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    db.add_all([
        _case("velho", created_at=mais_velho, sort=0),
        _case("novo", created_at=mais_novo, sort=0),
    ])
    db.commit()

    corpo = _home(db)

    # sort igual (0) para os dois: o desempate é created_at desc — o mais
    # novo primeiro — como published_cases já fazia antes deste campo existir
    assert _ordem_dos_titulos(corpo, ["novo", "velho"]) == ["novo", "velho"]


def test_ordem_explicita_vence_case_mais_recente(db):
    """Um destaque com ordem explícita alta (fim da fila) não passa na frente
    de quem tem ordem baixa, mesmo cadastrado depois."""
    mais_novo = dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc)
    mais_velho = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    db.add_all([
        _case("recente-sem-prioridade", created_at=mais_novo, destaque_ordem=999),
        _case("antigo-priorizado", created_at=mais_velho, destaque_ordem=1),
    ])
    db.commit()

    corpo = _home(db)

    assert _ordem_dos_titulos(corpo, ["antigo-priorizado", "recente-sem-prioridade"]) == [
        "antigo-priorizado", "recente-sem-prioridade"]
