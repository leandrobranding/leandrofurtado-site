"""Fixtures dos testes do Lab que precisam do app de verdade (TestClient).

`tests/conftest.py` já isola `DATA_DIR` num diretório temporário por processo
de teste (ver o bloco `lf-testes-data-` lá) — o `data/site.db` real nunca é
tocado. Mas dentro desse isolamento o arquivo é UM SÓ, compartilhado por toda
a suíte (mesmo padrão de `tests/test_tracking.py`, que sobe o app de verdade
porque a rota consulta o `SessionLocal` real, não o fixture `db` em memória).
Sandbox de um teste vazaria contagem para o próximo sem limpeza — por isso o
fixture `_lab_tabelas_limpas` abaixo, autouse só neste diretório.

Os testes que não passam por HTTP (limpeza, reciclagem, sobrevivência do
lead) usam o fixture `db` de `tests/conftest.py` — em memória, isolado por
teste sozinho, sem precisar deste arquivo."""
import pytest
from starlette.testclient import TestClient

from app.database import Base as _Base
from app.database import SessionLocal as _SessionLocal
from app.database import engine as _engine
from app.lab import models as _m
from app.lab import protecao as _protecao
from app.main import app as _app

# Ordem importa: tabelas-filha antes de lab_sandbox (embora o
# `PRAGMA foreign_keys=ON` cuidasse disso também via cascade).
_TABELAS_LAB = (
    _m.LabDocumentoStatus, _m.LabAuditoria, _m.LabCandidato,
    _m.LabNota, _m.LabLancamento, _m.LabClienteFiscal,
    _m.LabAvaliacao, _m.LabParecer, _m.LabAluno,
    _m.LabIaGasto, _m.LabLead,
    _m.LabSandbox,
)


def _limpar_tabelas_lab() -> None:
    # Testes deste diretório que não usam TestClient (ex.: tests/lab/test_models.py)
    # nunca disparam o lifespan do app — sem isto, a primeira limpeza bateria
    # num site.db real ainda sem as tabelas do Lab ("no such table").
    _Base.metadata.create_all(bind=_engine)
    db = _SessionLocal()
    try:
        for modelo in _TABELAS_LAB:
            db.query(modelo).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _lab_tabelas_limpas():
    _limpar_tabelas_lab()
    yield
    _limpar_tabelas_lab()


@pytest.fixture(autouse=True)
def _lab_rate_limit_limpo():
    """`limitar_taxa` (F1/F2, Task 2 do Plano 2) virou dependency do router
    `/lab` inteiro, inclusive `/lab/_sandbox/ping` — a rota que quase todo
    teste deste diretório usa para conseguir um sandbox. O balde de
    requisições (`_requisicoes`) e o contador da poda inline vivem em
    memória de MÓDULO, compartilhada pela suíte inteira (mesma limitação
    documentada em `app/lab/protecao.py`); sem limpar entre testes, o balde
    do único IP que a `TestClient` usa ("testclient", sempre o mesmo) foi se
    esgotando ao longo da suíte e derrubando com 429 testes que não têm
    nada a ver com rate limit (ex.: `tests/lab/test_sandbox.py`)."""
    _protecao._requisicoes.clear()
    _protecao._chamadas_desde_a_ultima_poda = 0
    yield
    _protecao._requisicoes.clear()
    _protecao._chamadas_desde_a_ultima_poda = 0


@pytest.fixture()
def client():
    """TestClient sobre o app de verdade. `base_url="https://testserver"`
    porque o cookie do sandbox sai `Secure` fora de debug — em HTTP puro o
    httpx nem guardaria o cookie (mesmo cuidado de test_tracking.py)."""
    with TestClient(_app, base_url="https://testserver") as c:
        yield c


@pytest.fixture()
def client2():
    """Segundo visitante: um `httpx.Client` novo já nasce sem os cookies do
    primeiro (cada instância tem seu próprio jar) — não precisa de nada além
    de ser uma instância separada de `client`."""
    with TestClient(_app, base_url="https://testserver") as c:
        yield c


@pytest.fixture()
def db_session():
    """A mesma base que as rotas enxergam (`app.database.SessionLocal`) —
    diferente do fixture `db` de `tests/conftest.py`, que é um SQLite em
    memória à parte e não vê o que uma requisição HTTP gravou."""
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
