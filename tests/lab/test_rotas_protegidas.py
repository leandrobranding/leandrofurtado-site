"""Testes da Task 2 do Plano 2: estrutura de rotas públicas do Lab
(`app/lab/rotas.py`) e F1/F2 do rate limiter (`app/lab/protecao.py`).

Fixtures `client`/`db_session` vêm de `tests/lab/conftest.py` (sobem o app
de verdade — as rotas cobertas aqui são todas HTTP). O fixture autouse
`_lab_rate_limit_limpo` (mesmo arquivo) zera `_requisicoes` e o contador da
poda inline entre testes, então cada teste começa com o balde de taxa
vazio.
"""
import collections
import random
import string
import time

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from app.lab import protecao as _protecao
from app.lab.models import LabSandbox
from app.lab.protecao import INTERVALO_PODA_INLINE, RATE_LIMIT_POR_MIN, limitar_taxa
from app.lab.sandbox import COOKIE_NOME
from app.main import app


def _rotas_efetivas(routes):
    """Achata a árvore de rotas do app — FastAPI >= 0.141 inclui routers
    preguiçosamente (`_IncludedRouter`); é preciso descer em
    `original_router.routes` para chegar nas `APIRoute` de verdade. Mesma
    lógica de `tests/lab/test_regras_seguranca.py::_rotas_efetivas`,
    duplicada aqui de propósito (convenção já usada naquele arquivo: cada
    teste que precisa disto reimplementa, em vez de importar de outro
    módulo de teste)."""
    achatadas = []
    for rota in routes:
        if type(rota).__name__ == "_IncludedRouter":
            achatadas.extend(_rotas_efetivas(rota.original_router.routes))
        else:
            achatadas.append(rota)
    return achatadas


def _rotas_do_lab():
    return [r for r in _rotas_efetivas(app.routes) if getattr(r, "path", "").startswith("/lab")]


# ------------------------------------------- varredura: limitar_taxa em TODAS

def test_toda_rota_do_lab_tem_limitar_taxa():
    rotas_lab = _rotas_do_lab()
    # Sentinela: se um dia a lista vier vazia (rota renomeada, prefixo
    # mudado), o teste abaixo passaria vazio e não provaria nada — trava
    # aqui primeiro, contra pelo menos as 5 rotas desta task (vitrine +
    # admita + notavel + caderneta + ping).
    assert len(rotas_lab) >= 5, [r.path for r in rotas_lab]
    for rota in rotas_lab:
        chamadas = [d.call for d in rota.dependant.dependencies]
        assert limitar_taxa in chamadas, f"{rota.path} sem limitar_taxa: {chamadas}"


def test_rotas_esperadas_estao_todas_registradas():
    caminhos = {r.path for r in _rotas_do_lab()}
    for esperado in ("/lab", "/lab/admita", "/lab/notavel", "/lab/caderneta", "/lab/_sandbox/ping"):
        assert esperado in caminhos, caminhos


# ------------------------------------------------------------ vitrine /lab --

def test_vitrine_responde_200_e_linka_as_tres_demos(client):
    r = client.get("/lab")
    assert r.status_code == 200
    for caminho in ("/lab/admita", "/lab/notavel", "/lab/caderneta"):
        assert caminho in r.text


# ------------------------------------------------- rotas de demo + sandbox --

@pytest.mark.parametrize(
    "caminho,demo_esperado,demo_origem_esperado",
    [
        # /lab/admita SAIU desta lista na Task 4 do Plano 2: a esteira de
        # admissão deixou de ser o placeholder "Em construção interna" —
        # tem teste próprio e completo em tests/lab/test_admita.py.
        # Notável e Caderneta continuam placeholder até as Tasks 6-9.
        ("/lab/notavel", "notavel", "fin"),
        ("/lab/caderneta", "caderneta", "escola"),
    ],
)
def test_rota_de_demo_renderiza_base_demo_e_cria_sandbox_com_origem_certa(
    client, db_session, caminho, demo_esperado, demo_origem_esperado
):
    r = client.get(caminho)
    assert r.status_code == 200
    assert f'class="lab-demo demo-{demo_esperado}"' in r.text
    assert "Em construção interna" in r.text
    # regra do Leandro: nada de travessão como pontuação no texto visível.
    # `<body ...>` (não `<body>` cru): um middleware de acessibilidade do
    # site injeta atributo/classe na tag antes de a resposta sair.
    import re as _re
    corpo_visivel = _re.split(r"<body[^>]*>", r.text, maxsplit=1)[1]
    assert "—" not in _re.sub(r"<[^>]+>", " ", corpo_visivel)

    # Bug do dono (20/08): a faixa de copyright compartilhada
    # (app/templates/_copyright.html) decidia o idioma com `lang == 'pt'`
    # — como esta rota renderiza com contexto mínimo (Princípio do Enxuto,
    # sem `lang`), caía sempre em inglês. O Lab é só português; a faixa
    # tem que sair em pt-BR sempre, nunca em inglês.
    assert "Todos os direitos reservados" in r.text
    assert "All rights reserved" not in r.text
    assert "Purely built with" not in r.text

    token = client.cookies.get(COOKIE_NOME)
    assert token
    sandbox = db_session.query(LabSandbox).filter_by(token=token).one()
    assert sandbox.demo_origem == demo_origem_esperado


# ---------------------------------------------- F3: ping também é limitado --

def test_ping_tambem_esta_protegido_por_limitar_taxa():
    rota_ping = next(r for r in _rotas_do_lab() if r.path == "/lab/_sandbox/ping")
    chamadas = [d.call for d in rota_ping.dependant.dependencies]
    assert limitar_taxa in chamadas


# --------------------------------------- F2: cookie forjado cai na chave IP --

def _token_aleatorio() -> str:
    # 24 caracteres aleatórios — do mesmo comprimento "razoável" de um
    # token de verdade (secrets.token_urlsafe(24) tem mais bytes de
    # entropia, mas o formato não importa aqui: o ponto do teste é que
    # NENHUM destes tokens existe em lab_sandbox).
    return "".join(random.choices(string.ascii_letters + string.digits, k=24))


def test_cem_cookies_forjados_diferentes_caem_na_mesma_chave_ip_e_tomam_429(client):
    respostas = []
    for _ in range(100):
        client.cookies.clear()
        client.cookies.set(COOKIE_NOME, _token_aleatorio())
        respostas.append(client.get("/lab/_sandbox/ping").status_code)

    # as primeiras RATE_LIMIT_POR_MIN passam (mesma chave só-IP, balde
    # ainda não estourado); TODAS as seguintes tomam 429, mesmo cada uma
    # trazendo um cookie forjado DIFERENTE das anteriores — se a chave
    # dependesse do cookie cru (comportamento pré-F2), cada forjado abriria
    # um balde novo e vazio, e isto aqui passaria de 200 sempre.
    assert respostas[:RATE_LIMIT_POR_MIN] == [200] * RATE_LIMIT_POR_MIN
    assert all(codigo == 429 for codigo in respostas[RATE_LIMIT_POR_MIN:]), respostas


def test_token_valido_de_sandbox_real_abre_chave_propria_distinta_do_ip_puro(client, db_session):
    # visitante de verdade: ganha um cookie real de sandbox numa rota de demo
    r0 = client.get("/lab/admita")
    assert r0.status_code == 200
    token_real = client.cookies.get(COOKIE_NOME)
    assert token_real

    # agora um tanto de tráfego com cookie FORJADO, do mesmo IP (mesmo
    # `client` de teste), esgota o balde só-IP até tomar 429
    esgotou = False
    for _ in range(RATE_LIMIT_POR_MIN + 5):
        client.cookies.clear()
        client.cookies.set(COOKIE_NOME, _token_aleatorio())
        if client.get("/lab/_sandbox/ping").status_code == 429:
            esgotou = True
            break
    assert esgotou, "esperava que o balde só-IP estourasse antes disso"

    # o visitante de verdade, com o cookie REAL, continua livre: a chave
    # dele é ip:token_real (F2) — um balde à parte do balde só-IP que os
    # forjados acabaram de esgotar.
    client.cookies.clear()
    client.cookies.set(COOKIE_NOME, token_real)
    assert client.get("/lab/admita").status_code == 200


# ------------------------------------------------------ F1: poda inline ----
# Harness mínimo (mesmo padrão de tests/lab/test_protecao.py::_app_de_teste):
# uma rota que só existe para exercitar `limitar_taxa` isoladamente, sem
# passar pela criação de sandbox/seed das rotas reais — o alvo aqui é o
# comportamento do rate limiter, não o resto da pilha.

def _app_so_com_limitar_taxa() -> FastAPI:
    app_teste = FastAPI()

    @app_teste.get("/_so_taxa")
    def _rota(_=Depends(limitar_taxa)):
        return {"ok": True}

    return app_teste


def test_poda_inline_nao_dispara_antes_do_intervalo_completo():
    cliente = TestClient(_app_so_com_limitar_taxa())
    chave_antiga = "ip:antigo-parcial"
    _protecao._requisicoes[chave_antiga] = collections.deque([time.monotonic() - 120])

    for i in range(INTERVALO_PODA_INLINE - 1):
        cliente.get("/_so_taxa", headers={"x-forwarded-for": f"203.0.{i // 256}.{i % 256}"})

    assert chave_antiga in _protecao._requisicoes


def test_poda_inline_dispara_no_intervalo_e_remove_janelas_vazias_sem_o_dict_crescer_sem_limite():
    cliente = TestClient(_app_so_com_limitar_taxa())

    # semeia várias chaves cujo deque já esvaziou de tempo (> 60s atrás) —
    # o mesmo cenário do leak que podar_janelas_vazias existe para consertar.
    chaves_antigas = [f"ip:antigo-{i}" for i in range(50)]
    agora = time.monotonic()
    for chave in chaves_antigas:
        _protecao._requisicoes[chave] = collections.deque([agora - 120])
    assert len(_protecao._requisicoes) == 50

    for i in range(INTERVALO_PODA_INLINE - 1):
        cliente.get("/_so_taxa", headers={"x-forwarded-for": f"203.0.{i // 256}.{i % 256}"})
    # a chamada de número INTERVALO_PODA_INLINE fecha o intervalo e dispara a poda
    cliente.get("/_so_taxa", headers={"x-forwarded-for": "203.255.255.255"})

    for chave in chaves_antigas:
        assert chave not in _protecao._requisicoes
    # só sobram as INTERVALO_PODA_INLINE chaves frescas desta rodada: o dict
    # não ficou com 50 (velhas) + 500 (novas) — as velhas foram podadas.
    assert len(_protecao._requisicoes) == INTERVALO_PODA_INLINE
