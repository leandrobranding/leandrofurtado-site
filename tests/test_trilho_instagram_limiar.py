"""Trilho do Instagram na home (rodada 3, item 7, 19/08).

Regra do dono: o trilho só aparece com 6+ posts *completos* (imagem própria
+ link do próprio post) vindos do feed real da conta. Hoje em produção a
conta só tem 2 posts publicados — o trilho deve estar ausente por inteiro,
não mostrar uma fileira pela metade. A partir de 6 ele volta sozinho.

Dois níveis de teste:
  - `posts_completos`: a função pura que decide o que conta como "completo".
  - `get_ig_feed`: aplica o limiar sobre o que `fetch_feed` (mockado, sem
    rede) devolve — os dois lados da fronteira (5 e 6).
  - a home renderizada de verdade: a seção inteira (cabeçalho "Instagram"
    incluso) some do HTML abaixo do limiar.
"""
import asyncio

import pytest
from starlette.requests import Request

from app.models import SiteSetting
from app.routers.public import IG_MIN_POSTS, get_ig_feed, home, posts_completos


def _post(n: int) -> dict:
    return {"img": f"https://cdn.example/post-{n}.jpg", "link": f"https://instagram.com/p/{n}/"}


# ---------------------------------------------------------------- posts_completos

def test_post_completo_precisa_de_imagem_e_link():
    assert posts_completos([{"img": "x.jpg", "link": "https://x/"}]) == [
        {"img": "x.jpg", "link": "https://x/"}]


def test_post_sem_link_nao_e_completo():
    assert posts_completos([{"img": "x.jpg", "link": ""}]) == []


def test_post_sem_imagem_nao_e_completo():
    assert posts_completos([{"img": "", "link": "https://x/"}]) == []


def test_post_sem_nenhum_dos_dois_nao_e_completo():
    assert posts_completos([{}]) == []


def test_filtra_so_os_incompletos_mantendo_os_bons():
    itens = [_post(1), {"img": "", "link": "https://x/"}, _post(2)]
    assert posts_completos(itens) == [_post(1), _post(2)]


# ---------------------------------------------------------------- get_ig_feed

def _smap(db) -> dict:
    db.add(SiteSetting(key="ig_user_id", value="123"))
    db.add(SiteSetting(key="ig_access_token", value="tok"))
    db.commit()
    return {"ig_user_id": "123", "ig_access_token": "tok", "social_instagram": "https://instagram.com/leandrobranding"}


def test_limiar_e_seis_a_constante_nao_pode_derivar(db):
    assert IG_MIN_POSTS == 6


def test_cinco_posts_completos_trilho_ausente(monkeypatch, db):
    async def _fake_fetch(*a, **kw):
        return [_post(n) for n in range(5)]
    monkeypatch.setattr("app.services.instagram.fetch_feed", _fake_fetch)
    itens = asyncio.run(get_ig_feed(db, _smap(db)))
    assert itens == []


def test_seis_posts_completos_trilho_presente(monkeypatch, db):
    async def _fake_fetch(*a, **kw):
        return [_post(n) for n in range(6)]
    monkeypatch.setattr("app.services.instagram.fetch_feed", _fake_fetch)
    itens = asyncio.run(get_ig_feed(db, _smap(db)))
    assert len(itens) == 6


def test_seis_no_feed_mas_um_incompleto_fica_so_com_cinco_e_some(monkeypatch, db):
    """6 posts na resposta da API, mas um deles sem link (foto apagada, por
    exemplo): só 5 são completos — abaixo do limiar, some por inteiro."""
    async def _fake_fetch(*a, **kw):
        itens = [_post(n) for n in range(6)]
        itens[0] = {"img": itens[0]["img"], "link": ""}
        return itens
    monkeypatch.setattr("app.services.instagram.fetch_feed", _fake_fetch)
    itens = asyncio.run(get_ig_feed(db, _smap(db)))
    assert itens == []


def test_sem_token_configurado_mantem_os_seis_tiles_de_marcacao(db):
    """Sem ig_user_id/token, o trilho continua com os 6 tiles de marcação de
    sempre — decorativos, não posts reais, não entram na regra "posts
    completos"."""
    itens = asyncio.run(get_ig_feed(db, {"social_instagram": "https://instagram.com/leandrobranding"}))
    assert len(itens) == 6


def test_erro_na_api_deixa_o_trilho_ausente_em_vez_de_marcacao(monkeypatch, db):
    async def _fake_fetch(*a, **kw):
        raise RuntimeError("Meta fora do ar")
    monkeypatch.setattr("app.services.instagram.fetch_feed", _fake_fetch)
    itens = asyncio.run(get_ig_feed(db, _smap(db)))
    assert itens == []


# ---------------------------------------------------------------- home renderizada

def _get(lang: str = "pt") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "raw_path": b"/", "query_string": b"", "headers": [],
        "state": {"clean_path": "/", "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def test_home_sem_instagram_configurado_mostra_o_trilho_de_marcacao(db):
    corpo = asyncio.run(home(_get(), db)).body.decode()
    assert 'class="ig-feed"' in corpo
    assert corpo.count('class="ig-tile"') == 6


def test_home_com_cinco_posts_reais_nao_mostra_secao_nenhuma(monkeypatch, db):
    """Ponta a ponta: 5 posts vindos da API (via fetch_feed mockado, sem
    rede) — get_ig_feed aplica o limiar de verdade, e o cabeçalho
    "Instagram" some junto com a grade."""
    async def _fake_fetch(*a, **kw):
        return [_post(n) for n in range(5)]
    monkeypatch.setattr("app.services.instagram.fetch_feed", _fake_fetch)
    _smap(db)
    corpo = asyncio.run(home(_get(), db)).body.decode()
    assert 'class="ig-feed"' not in corpo
    assert 'class="ig-tile"' not in corpo
    assert "Instagram" not in corpo


def test_home_com_seis_posts_reais_mostra_a_secao_inteira(monkeypatch, db):
    async def _fake_fetch(*a, **kw):
        return [_post(n) for n in range(6)]
    monkeypatch.setattr("app.services.instagram.fetch_feed", _fake_fetch)
    _smap(db)
    corpo = asyncio.run(home(_get(), db)).body.decode()
    assert 'class="ig-feed"' in corpo
    assert corpo.count('class="ig-tile"') == 6


def test_home_com_ig_feed_vazio_nao_mostra_secao(monkeypatch, db):
    """Cobre só a metade do template: `{% if ig_feed %}` some com a lista
    vazia que get_ig_feed devolve abaixo do limiar (ou tiles poderiam
    reaparecer aqui se alguém reintroduzisse um `or placeholder` por engano
    no template)."""
    async def _fake_get_ig_feed(db_, smap_):
        return []
    monkeypatch.setattr("app.routers.public.get_ig_feed", _fake_get_ig_feed)
    corpo = asyncio.run(home(_get(), db)).body.decode()
    assert 'class="ig-feed"' not in corpo
