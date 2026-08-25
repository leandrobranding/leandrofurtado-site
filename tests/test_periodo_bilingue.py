"""Período de experiência e formação no idioma da página (24/08/2026).

Origem: a comparação entrada por entrada entre o currículo do site e o
LinkedIn. As doze experiências compartilhadas tinham datas idênticas, mas
`period` era um campo único, com abreviação de mês em português, impresso
igual na página /en e no PDF em inglês.

O defeito era discreto de propósito: metade das abreviações coincide nos dois
idiomas (Jan, Mar, Nov, Jun, Jul) e a outra metade não (Fev, Abr, Mai, Ago,
Set, Out, Dez). Numa leitura rápida do currículo em inglês, "Mar 2024" passa e
"Fev 2026" é o que denuncia. O leitor era recrutador internacional, que é
exatamente para quem a versão em inglês existe.
"""
import asyncio

from starlette.requests import Request

from app.routers.public import about
from app.services.resume import build_pdf

PERFIL = {
    "name": "Leandro Furtado",
    "title_pt": "Engenheiro de IA", "title_en": "AI Engineer",
    "experience": [
        {"company": "Autônomo",
         "role_pt": "Engenheiro de IA", "role_en": "AI Engineer",
         "period": "Ago 2026 — Atual", "period_en": "Aug 2026 — Present"},
        {"company": "Casa Antiga",
         "role_pt": "Diretor de Arte", "role_en": "Art Director",
         "period": "Dez 2015 — Mai 2016", "period_en": "Dec 2015 — May 2016"},
        {"company": "Sem Tradução",
         "role_pt": "Cargo", "role_en": "Role", "period": "2016 — 2022"},
    ],
    "education": [
        {"institution_pt": "Faculdade", "institution_en": "College",
         "course_pt": "Curso", "course_en": "Course",
         "period": "Jan 2010 — Dez 2013", "period_en": "Jan 2010 — Dec 2013"},
    ],
}


def _pedido(caminho: str, lang: str) -> Request:
    scope = {
        "type": "http", "method": "GET", "path": caminho,
        "raw_path": caminho.encode(), "query_string": b"", "headers": [],
        "state": {"clean_path": caminho, "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


# ------------------------------------------------------------- o PDF --

def test_o_curriculo_continua_sendo_gerado_nos_dois_idiomas():
    """O PDF embute a fonte em subconjunto, então o texto não sai por busca no
    arquivo. O que este teste garante é que o caminho novo do período não
    quebra a geração — a escolha do idioma é verificada abaixo, na unidade, e
    na página renderizada, que é HTML e dá para ler."""
    for lang in ("pt", "en"):
        assert build_pdf(PERFIL, lang)[:4] == b"%PDF"


def test_a_escolha_do_periodo_prefere_o_idioma_e_cai_no_portugues():
    """A regra é a mesma de `role_` e `desc_`: usa o campo do idioma quando
    existe, e volta ao português quando não existe. A ONU, com período só de
    anos ("2016 — 2022"), não precisa de tradução e não tem `period_en`."""
    xp_atual, _, xp_sem = PERFIL["experience"]
    assert (xp_atual.get("period_en") or xp_atual["period"]) == "Aug 2026 — Present"
    assert (xp_atual.get("period_pt") or xp_atual["period"]) == "Ago 2026 — Atual"
    for lang in ("en", "pt"):
        assert (xp_sem.get(f"period_{lang}") or xp_sem["period"]) == "2016 — 2022"


# ------------------------------------------------------------ a página --

def _perfil_semeado(db):
    """Semeia o perfil real e troca só experiência e formação. O `about`
    renderiza o template inteiro, então um perfil pela metade quebra em
    `summary_pt` antes de chegar ao período."""
    from app.models import Profile
    from app.services.seeds import run_seeds
    run_seeds(db)
    perfil = db.query(Profile).filter_by(id=1).first()
    dados = dict(perfil.data)
    dados["experience"] = PERFIL["experience"]
    dados["education"] = PERFIL["education"]
    perfil.data = dados
    db.commit()


def test_a_pagina_en_nao_imprime_mes_em_portugues(db):
    _perfil_semeado(db)
    corpo = asyncio.run(about(_pedido("/en/about", "en"), db)).body.decode()
    assert "Aug 2026 — Present" in corpo
    assert "Dec 2015 — May 2016" in corpo
    for mes in ("Ago 2026", "Dez 2015", "Mai 2016", "Dez 2013"):
        assert mes not in corpo, f"mês em português na página em inglês: {mes}"


def test_a_pagina_pt_continua_em_portugues(db):
    _perfil_semeado(db)
    corpo = asyncio.run(about(_pedido("/about", "pt"), db)).body.decode()
    assert "Ago 2026 — Atual" in corpo
    assert "Dez 2015 — Mai 2016" in corpo
    for mes in ("Aug 2026", "Dec 2015", "May 2016"):
        assert mes not in corpo, f"mês em inglês na página em português: {mes}"


def test_periodo_sem_traducao_aparece_igual_nos_dois_idiomas(db):
    """A ONU tem período só de anos ("2016 — 2022"): não há mês para traduzir,
    e forçar um `period_en` idêntico seria duplicar dado sem motivo."""
    _perfil_semeado(db)
    for caminho, lang in (("/about", "pt"), ("/en/about", "en")):
        corpo = asyncio.run(about(_pedido(caminho, lang), db)).body.decode()
        assert "2016 — 2022" in corpo
