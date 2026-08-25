"""Mosaico de capas na home (Rodada 3, item 11, 19/08).

Fita densa de ~20 colunas numa linha só com as capas de TODOS os cases
publicados (repete em loop com menos de 20; corta com mais), gradiente
radial por cima e um botão central "ver todos os cases (x)" — x é a
contagem real de cases publicados, vinda do servidor. No mobile só o
botão sobrevive (a fita de imagens some do HTML por inteiro).
"""
import asyncio
import datetime as dt

from starlette.requests import Request

from app.models import Case, Category
from app.routers.public import MOSAIC_TILES, home, mosaic_covers


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


def _case(slug: str, cover: str = "", **kw) -> Case:
    base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    campos = {"published": True, "archived": False, "created_at": base, **kw}
    return Case(slug=slug, title_pt=slug, title_en=slug, cover_image=cover, **campos)


# ---------------------------------------------------------------- mosaic_covers (unidade)

def test_sem_cases_devolve_lista_vazia():
    assert mosaic_covers([]) == []


def test_cases_sem_capa_nao_entram_e_lista_fica_vazia():
    class Falso:
        cover_image = ""
    assert mosaic_covers([Falso(), Falso()]) == []


def test_menos_capas_que_ladrilhos_repete_em_loop():
    class Falso:
        def __init__(self, cover):
            self.cover_image = cover
    capas = mosaic_covers([Falso("a.jpg"), Falso("b.jpg")])
    assert len(capas) == 20  # hardcoded de propósito: não compara MOSAIC_TILES
    assert capas[:4] == ["a.jpg", "b.jpg", "a.jpg", "b.jpg"]         # contra ele mesmo


def test_mais_capas_que_ladrilhos_corta_nas_primeiras_n():
    class Falso:
        def __init__(self, cover):
            self.cover_image = cover
    muitas = [Falso(f"{i}.jpg") for i in range(30)]
    capas = mosaic_covers(muitas)
    assert len(capas) == 20  # idem: hardcoded, não MOSAIC_TILES
    assert capas == [f"{i}.jpg" for i in range(20)]


# ---------------------------------------------------------------- home renderizada

def test_home_sem_case_nenhum_nao_mostra_o_mosaico(db):
    corpo = _home(db)
    assert 'class="case-mosaic"' not in corpo


def test_home_com_cases_mostra_o_mosaico_e_o_botao_com_a_contagem_real(db):
    db.add_all([_case("a", "a.jpg"), _case("b", "b.jpg"), _case("c", "c.jpg")])
    db.commit()
    corpo = _home(db)
    assert 'class="case-mosaic"' in corpo
    assert "Ver todos os cases" in corpo
    assert "(3)" in corpo


def test_contagem_do_botao_muda_com_o_numero_real_de_cases_publicados(db):
    """A contagem não pode ser um número fixo no template — precisa vir do
    mesmo total que a home já usa (`total_cases`). Cobre com duas
    quantidades diferentes para travar que o número acompanha o banco."""
    db.add_all([_case("a", "a.jpg")])
    db.commit()
    assert "(1)" in _home(db)

    db.add_all([_case("b", "b.jpg"), _case("c", "c.jpg")])
    db.commit()
    assert "(3)" in _home(db)


def test_case_arquivado_ou_despublicado_nao_entra_na_contagem_nem_no_mosaico(db):
    db.add_all([
        _case("publicado", "pub.jpg"),
        _case("arquivado", "arq.jpg", archived=True),
        _case("rascunho", "rasc.jpg", published=False),
    ])
    db.commit()
    corpo = _home(db)
    assert "(1)" in corpo
    assert "arq.jpg" not in corpo
    assert "rasc.jpg" not in corpo


def test_mosaico_tem_exatamente_vinte_ladrilhos(db):
    db.add_all([_case("a", "a.jpg")])
    db.commit()
    assert _home(db).count('class="cm-tile"') == 20  # hardcoded, não MOSAIC_TILES


def test_case_de_categoria_sites_tambem_entra_no_mosaico(db):
    """O mosaico é "capas de TODOS os cases publicados" — inclusive os que
    levam a um site de cliente (category.kind == "sites"), que a home
    exclui só do bloco de DESTAQUE (vitrine autoral), não do mosaico."""
    cat = Category(slug="sites", name_pt="Sites", kind="sites")
    db.add(cat)
    db.flush()
    db.add(_case("um-site", "capa-do-site.jpg", category_id=cat.id, site_url="https://exemplo.com"))
    db.commit()
    corpo = _home(db)
    assert "capa-do-site.jpg" in corpo


def test_mosaico_e_aria_hidden_e_imagens_sao_decorativas(db):
    """O mosaico não tem link próprio por ladrilho — só o botão central é
    navegável. `.cm-grid` inteiro sai da árvore de acessibilidade, e cada
    imagem tem alt vazio (decorativa, sem informação nova pro leitor de
    tela — capas se repetem em loop)."""
    db.add_all([_case("a", "a.jpg")])
    db.commit()
    corpo = _home(db)
    assert 'class="cm-grid" aria-hidden="true"' in corpo
    assert 'alt=""' in corpo


def test_imagens_do_mosaico_sao_lazy_e_decoding_async(db):
    db.add_all([_case("a", "a.jpg")])
    db.commit()
    corpo = _home(db)
    trecho = corpo[corpo.find('class="cm-grid"'):corpo.find('class="cm-fade"')]
    assert 'loading="lazy"' in trecho
    assert 'decoding="async"' in trecho


def test_botao_do_mosaico_leva_ao_portfolio(db):
    db.add_all([_case("a", "a.jpg")])
    db.commit()
    corpo = _home(db)
    assert 'class="cm-cta cta-pill big" href="/portfolio"' in corpo


def test_botao_do_mosaico_em_ingles(db):
    db.add_all([_case("a", "a.jpg")])
    db.commit()
    corpo = _home(db, "en")
    assert "See all cases" in corpo
    assert 'href="/en/portfolio"' in corpo
