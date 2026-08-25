"""Testes da camada de proteção do Lab (Task 3 do Plano 1: §8 + §9 da spec).

`validar_texto`, `checar_limite_registros` e o rate limiter (`limitar_taxa`)
são a blindagem de entrada; os testes vinculantes de §9 (upload zero, `|safe`
zero) ficam em `tests/lab/test_regras_seguranca.py`.
"""
import collections
import datetime as dt
import time

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from app.database import SessionLocal as _SessionLocal
from app.lab.models import LabCandidato, LabSandbox
from app.lab.sandbox import COOKIE_NOME
from app.lab.protecao import (
    MAX_CAMPO,
    MAX_CURRICULO,
    MAX_EMAILS,
    MAX_EXTRATO,
    MAX_IA_POR_SANDBOX,
    MAX_PDFS,
    MAX_REGISTROS_POR_DEMO,
    MAX_SANDBOXES,
    RATE_LIMIT_POR_MIN,
    _requisicoes,
    checar_limite_registros,
    limitar_taxa,
    podar_janelas_vazias,
    validar_texto,
)


# ------------------------------------------------------------- constantes --

def test_constantes_batem_com_a_spec_8():
    assert MAX_CURRICULO == 5000
    assert MAX_EXTRATO == 2000
    assert MAX_CAMPO == 200
    assert MAX_REGISTROS_POR_DEMO == 10
    assert MAX_IA_POR_SANDBOX == 3
    assert MAX_EMAILS == 2
    assert MAX_PDFS == 5
    assert MAX_SANDBOXES == 200
    assert RATE_LIMIT_POR_MIN == 30


# ------------------------------------------------------------- validar_texto

def test_texto_dentro_do_limite_e_aceito():
    assert validar_texto("abc", 200) == "abc"


def test_texto_com_quebra_de_linha_e_tab_e_aceito():
    assert validar_texto("linha1\nlinha2\tfim", 200) == "linha1\nlinha2\tfim"


def test_texto_com_caractere_de_controle_e_rejeitado():
    with pytest.raises(ValueError):
        validar_texto("abc\x00def", 200)


def test_texto_acima_do_limite_e_rejeitado_nao_truncado():
    with pytest.raises(ValueError) as exc:
        validar_texto("a" * 201, 200)
    assert "200" in str(exc.value)


def test_texto_no_limite_exato_e_aceito():
    texto = "a" * 200
    assert validar_texto(texto, 200) == texto


def test_texto_com_invisivel_cf_e_rejeitado():
    # U+200B ZERO WIDTH SPACE — categoria Cf, não está na lista de exceção
    with pytest.raises(ValueError):
        validar_texto("abc​def", 200)


def test_mensagem_de_erro_e_em_portugues():
    with pytest.raises(ValueError) as exc:
        validar_texto("a" * 201, 200)
    assert "excede" in str(exc.value).lower()

    with pytest.raises(ValueError) as exc2:
        validar_texto("abc\x00def", 200)
    assert "controle" in str(exc2.value).lower() or "invisível" in str(exc2.value).lower()


# ------------------------------------------------ §1 [ALTO] par substituto --
# Achado do revisor: "abc\ud800def" passava (categoria Cs ficava fora do
# filtro Cc/Cf) e quebrava a gravação no banco mais tarde com
# UnicodeEncodeError (500). Fix duplo: Cs entrou na lista de categorias
# rejeitadas E validar_texto tenta `texto.encode("utf-8", errors="strict")`
# antes de devolver — qualquer um dos dois pegaria isto sozinho.

def test_par_substituto_solto_e_rejeitado_caso_exato_do_revisor():
    with pytest.raises(ValueError):
        validar_texto("abc\ud800def", 200)


def test_par_substituto_solto_no_inicio_e_rejeitado():
    with pytest.raises(ValueError):
        validar_texto("\ud800abc", 200)


def test_par_substituto_solto_no_fim_e_rejeitado():
    with pytest.raises(ValueError):
        validar_texto("abc\ud800", 200)


def test_pares_substitutos_consecutivos_sao_rejeitados():
    # dois \uXXXX escapados na faixa de substituto NÃO se combinam num
    # caractere astral em Python — ficam dois code points Cs soltos, lado a
    # lado, exatamente o caso de um encoder malcomportado colando os dois
    # metades de um par sem os combinar.
    texto = "abc" + "\ud800" + "\udc00" + "def"
    with pytest.raises(ValueError):
        validar_texto(texto, 200)


def test_texto_que_falha_a_codificacao_utf8_vira_valueerror_nao_excecao_crua():
    # cinto e suspensório: mesmo que a categoria Cs um dia deixe de cobrir
    # algum caso, o encode() no fim continua barrando antes de chegar ao
    # banco — a mensagem sai em PT-BR, nunca um UnicodeEncodeError cru.
    with pytest.raises(ValueError) as exc:
        validar_texto("abc\ud800def", 200)
    assert isinstance(exc.value, ValueError)
    assert not isinstance(exc.value, UnicodeEncodeError)


# --------------------------------------------- §4 [MÉDIO, ruling] \r e \r\n --
# "textarea via form clássico reinsere \r\n e quebraria toda colagem" —
# validar_texto normaliza ANTES do filtro de controle (\r sozinho é Cc).

def test_quebra_de_linha_estilo_windows_passa_e_sai_normalizada():
    resultado = validar_texto("linha1\r\nlinha2", 200)
    assert resultado == "linha1\nlinha2"
    assert "\r" not in resultado


def test_carriage_return_solto_estilo_mac_classico_e_normalizado():
    resultado = validar_texto("linha1\rlinha2", 200)
    assert resultado == "linha1\nlinha2"


def test_normalizacao_de_r_n_conta_para_o_limite_depois_de_normalizar():
    # "linha1\r\nlinha2" tem 14 caracteres crus mas 13 depois de normalizar
    # \r\n -> \n; o limite deve valer sobre o texto que de fato é gravado —
    # por isso max_chars=13 aceita, mesmo o texto cru tendo 14.
    texto_cru = "linha1\r\nlinha2"
    assert len(texto_cru) == 14
    assert validar_texto(texto_cru, 13) == "linha1\nlinha2"


# ------------------------------------------------------- checar_limite_registros

def _sandbox(db) -> LabSandbox:
    s = LabSandbox(token="tok-protecao", demo_origem="rh",
                    expira_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24))
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_ate_dez_registros_e_aceito(db):
    sandbox = _sandbox(db)
    for i in range(10):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Candidato {i}"))
    db.commit()
    with pytest.raises(ValueError):
        checar_limite_registros(db, sandbox, "rh")


def test_abaixo_do_limite_nao_levanta(db):
    sandbox = _sandbox(db)
    for i in range(9):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Candidato {i}"))
    db.commit()
    checar_limite_registros(db, sandbox, "rh")  # não levanta


def test_decimo_primeiro_registro_e_rejeitado(db):
    sandbox = _sandbox(db)
    for i in range(10):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Candidato {i}"))
    db.commit()
    with pytest.raises(ValueError):
        checar_limite_registros(db, sandbox, "rh")


def test_limite_de_registros_e_por_demo_e_por_sandbox(db):
    sandbox = _sandbox(db)
    outro = LabSandbox(token="tok-outro", demo_origem="rh",
                        expira_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24))
    db.add(outro)
    db.commit()
    db.refresh(outro)

    for i in range(10):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Candidato {i}"))
    db.commit()

    # outro sandbox, mesma demo: não é afetado pelo limite do primeiro
    checar_limite_registros(db, outro, "rh")

    # mesmo sandbox, outra demo (financeiro conta notas, não candidatos): livre
    checar_limite_registros(db, sandbox, "fin")


# --------------------------------- §2 [MÉDIO-ALTO, ruling] seeds não contam --

def test_registros_com_origem_seed_nao_contam_para_o_teto(db):
    sandbox = _sandbox(db)
    for i in range(10):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Seed {i}", origem="seed"))
    db.commit()
    checar_limite_registros(db, sandbox, "rh")  # 10 seeds, 0 visitante: não levanta


def test_seeds_e_visitante_contam_separado_no_mesmo_sandbox(db):
    sandbox = _sandbox(db)
    for i in range(10):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Seed {i}", origem="seed"))
    for i in range(9):
        db.add(LabCandidato(sandbox_id=sandbox.id, nome=f"Visitante {i}"))  # default "visitante"
    db.commit()
    checar_limite_registros(db, sandbox, "rh")  # só 9 de origem visitante: não levanta

    db.add(LabCandidato(sandbox_id=sandbox.id, nome="Visitante 10"))
    db.commit()
    with pytest.raises(ValueError):
        checar_limite_registros(db, sandbox, "rh")  # agora são 10 de origem visitante


# ------------------------------------------------------------- limitar_taxa

def _app_de_teste() -> FastAPI:
    """App isolado só para exercitar a dependency — não altera
    `app/lab/rotas.py` (sob revisão paralela da Task 2 nesta rodada). A
    integração real do rate limiter numa rota do Lab é para quando o Plano 2
    abrir as rotas de cada demo."""
    app = FastAPI()

    @app.get("/_teste_taxa")
    def _rota(_=Depends(limitar_taxa)):
        return {"ok": True}

    return app


def _sandbox_real(token: str) -> None:
    """Grava um `LabSandbox` de verdade, com este token, no banco que
    `limitar_taxa` de fato consulta (`app.database.SessionLocal` — o mesmo
    engine de `app/database.py`, NÃO o fixture `db` isolado em memória de
    `tests/conftest.py`).

    F2 (herança do Plano 1): desde que `_chave_taxa` passou a só deixar o
    token entrar na chave quando ele bate com um `LabSandbox` real (consulta
    indexada), um cookie que não existe no banco não abre mais um balde
    próprio — cai junto com todo mundo sem cookie na chave só-IP. Os testes
    de isolamento por sandbox abaixo, portanto, PRECISAM de um sandbox de
    verdade para provar que dois visitantes diferentes ficam em baldes
    diferentes; sem isto todos cairiam na mesma chave `ip:testclient` e o
    teste de isolamento pegaria um falso positivo (ou um falso negativo,
    dependendo da ordem)."""
    with _SessionLocal() as db:
        if db.query(LabSandbox).filter_by(token=token).first() is not None:
            return
        db.add(LabSandbox(
            token=token, demo_origem="rh",
            expira_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24),
        ))
        db.commit()


def _cliente_com_token(token: str) -> TestClient:
    # `_requisicoes` é um dict em memória compartilhado pelo processo inteiro
    # (documentado em protecao.py) — cada teste usa um token de cookie único
    # para não herdar contagem de outro teste rodado antes na mesma sessão
    # (o fixture `_lab_rate_limit_limpo`, autouse em `tests/lab/conftest.py`,
    # também limpa o dict inteiro entre testes desde a Task 2 do Plano 2).
    _sandbox_real(token)
    c = TestClient(_app_de_teste())
    c.cookies.set(COOKIE_NOME, token)
    return c


def test_ate_trinta_requisicoes_por_minuto_passam():
    cliente = _cliente_com_token("tok-taxa-1")
    for _ in range(RATE_LIMIT_POR_MIN):
        r = cliente.get("/_teste_taxa")
        assert r.status_code == 200


def test_trigesima_primeira_requisicao_no_minuto_recebe_429():
    cliente = _cliente_com_token("tok-taxa-2")
    for _ in range(RATE_LIMIT_POR_MIN):
        assert cliente.get("/_teste_taxa").status_code == 200
    r = cliente.get("/_teste_taxa")
    assert r.status_code == 429


def test_rate_limit_e_isolado_por_sandbox():
    # dois tokens diferentes = dois baldes diferentes: estourar um não afeta
    # o outro (§8 — "30 requisições/min por sandbox", não por processo).
    esgotado = _cliente_com_token("tok-taxa-esgotado")
    for _ in range(RATE_LIMIT_POR_MIN):
        esgotado.get("/_teste_taxa")
    assert esgotado.get("/_teste_taxa").status_code == 429

    outro = _cliente_com_token("tok-taxa-fresco")
    assert outro.get("/_teste_taxa").status_code == 200


# ------------------------------------------ §3 [MÉDIO] poda de rate limit --
# Leak achado na revisão: uma chave que faz 1 requisição e nunca mais volta
# fica pendurada em `_requisicoes` para sempre (nada dispara a limpeza dela
# quando não há requisição nova naquela chave). `podar_janelas_vazias()` é a
# varredura pensada para a limpeza diária existente (Task 2) chamar.

def test_podar_janelas_vazias_remove_chave_cujo_deque_esvaziou():
    chave = "tok-poda-velha"
    _requisicoes[chave] = collections.deque([time.monotonic() - 120])  # > 60s atrás
    assert chave in _requisicoes

    removidas = podar_janelas_vazias()

    assert chave not in _requisicoes
    assert removidas >= 1


def test_podar_janelas_vazias_preserva_chave_com_requisicao_recente():
    chave = "tok-poda-recente"
    _requisicoes[chave] = collections.deque([time.monotonic()])

    podar_janelas_vazias()

    assert chave in _requisicoes
    del _requisicoes[chave]  # não vaza para o próximo teste
