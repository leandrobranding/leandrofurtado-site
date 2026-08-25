"""Testes do motor de sandbox (Task 2 do Plano 1): criação com cookie,
isolamento entre visitantes, expiração transparente, limpeza diária e
reciclagem no teto de 200 (§4/§8 da spec).

Fixtures `client`/`client2`/`db_session` vêm de `tests/lab/conftest.py`
(sobem o app de verdade — precisa, porque `/lab/_sandbox/ping` é rota HTTP).
Os testes puros de `limpar_expirados`/`reciclar_se_lotado` usam o fixture
`db` de `tests/conftest.py` (SQLite em memória, isolado por teste sozinho).
"""
import datetime as dt

from app.lab.models import LabAluno, LabAvaliacao, LabLead, LabSandbox
from app.lab.sandbox import limpar_expirados, reciclar_se_lotado


# ------------------------------------------------------- criação/cookie ---

def test_primeiro_acesso_cria_sandbox_com_cookie(client):
    r = client.get("/lab/_sandbox/ping")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert "lf_lab_sandbox" in r.cookies


def test_cookie_tem_os_atributos_da_spec(client):
    r = client.get("/lab/_sandbox/ping")
    bruto = r.headers.get("set-cookie", "")
    assert "HttpOnly" in bruto
    assert "samesite=lax" in bruto.lower()
    assert "Max-Age=86400" in bruto


def test_segunda_visita_com_o_mesmo_cookie_reusa_o_sandbox(client, db_session):
    client.get("/lab/_sandbox/ping")
    client.get("/lab/_sandbox/ping")
    assert db_session.query(LabSandbox).count() == 1


# ------------------------------------------------------------ isolamento --

def test_sandboxes_sao_isolados(client, client2, db_session):
    client.get("/lab/_sandbox/ping")
    client2.get("/lab/_sandbox/ping")
    tokens = {s.token for s in db_session.query(LabSandbox).all()}
    assert len(tokens) == 2


# -------------------------------------------------------------- expiração -

def test_expirado_ganha_sandbox_novo(client, db_session):
    client.get("/lab/_sandbox/ping")
    s = db_session.query(LabSandbox).one()
    s.expira_em = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
    db_session.commit()
    client.get("/lab/_sandbox/ping")
    assert db_session.query(LabSandbox).count() == 2  # velho ainda lá até a limpeza


# --------------------------------------------------------------- limpeza --

def test_limpeza_apaga_expirados_e_filhos(db):
    agora = dt.datetime.now(dt.timezone.utc)
    vencido = LabSandbox(token="venceu", demo_origem="escola",
                         expira_em=agora - dt.timedelta(hours=1))
    vivo = LabSandbox(token="vivo", demo_origem="escola",
                      expira_em=agora + dt.timedelta(hours=1))
    db.add_all([vencido, vivo])
    db.commit()

    aluno = LabAluno(sandbox_id=vencido.id, nome="Fulano de Tal")
    db.add(aluno)
    db.commit()
    db.add(LabAvaliacao(sandbox_id=vencido.id, aluno_id=aluno.id, disciplina="Matemática"))
    db.commit()

    apagados = limpar_expirados(db)

    assert apagados == 1
    assert db.query(LabSandbox).count() == 1
    assert db.query(LabSandbox).one().token == "vivo"
    assert db.query(LabAluno).count() == 0
    assert db.query(LabAvaliacao).count() == 0


def test_limpeza_sem_nada_vencido_nao_apaga_nada(db):
    agora = dt.datetime.now(dt.timezone.utc)
    db.add(LabSandbox(token="vivo2", demo_origem="rh",
                      expira_em=agora + dt.timedelta(hours=1)))
    db.commit()

    assert limpar_expirados(db) == 0
    assert db.query(LabSandbox).count() == 1


# ------------------------------------------------------------ reciclagem --

def test_reciclagem_no_limite_200(db):
    agora = dt.datetime.now(dt.timezone.utc)
    for i in range(200):
        db.add(LabSandbox(token=f"tok-{i}", demo_origem="rh",
                          expira_em=agora + dt.timedelta(hours=24),
                          criado_em=agora + dt.timedelta(seconds=i)))
    db.commit()
    assert db.query(LabSandbox).count() == 200

    reciclar_se_lotado(db, limite=200)

    assert db.query(LabSandbox).count() == 199
    restantes = {s.token for s in db.query(LabSandbox).all()}
    assert "tok-0" not in restantes  # o mais antigo foi reciclado
    assert "tok-199" in restantes


def test_reciclagem_abaixo_do_limite_nao_mexe_em_nada(db):
    agora = dt.datetime.now(dt.timezone.utc)
    for i in range(5):
        db.add(LabSandbox(token=f"tok-{i}", demo_origem="rh",
                          expira_em=agora + dt.timedelta(hours=24)))
    db.commit()

    reciclar_se_lotado(db, limite=200)

    assert db.query(LabSandbox).count() == 5


# ----------------------------------------------------------------- leads --

def test_lead_sobrevive_a_limpeza(db):
    agora = dt.datetime.now(dt.timezone.utc)
    vencido = LabSandbox(token="venceu2", demo_origem="fin",
                         expira_em=agora - dt.timedelta(hours=1))
    db.add(vencido)
    db.commit()
    db.add(LabLead(nome="Visitante", email="v@exemplo.com.br",
                   demo="fin", momento="nf_email"))
    db.commit()

    limpar_expirados(db)

    assert db.query(LabLead).count() == 1
