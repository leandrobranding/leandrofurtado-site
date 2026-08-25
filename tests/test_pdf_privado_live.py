"""Mini-tarefa de segurança (19/08): depois da migração, a URL pública
ANTIGA de um PDF de aula devolve 404 de verdade.

Precisa do app inteiro, com `StaticFiles` montado em `/media` (`app/main.py`)
— nenhum outro teste do Nodal sobe o ASGI de verdade, então este arquivo
segue o MESMO padrão de tests/test_tracking.py: `SessionLocal` real (isolado
por `DATA_DIR`, tests/conftest.py) e `TestClient(app)` pra disparar o
`lifespan` (que chama `run_migrations` a cada boot).

`Base.metadata.create_all` é chamado À MÃO, ANTES de qualquer
`TestClient(app)`: cada `with TestClient(app):` dispara o lifespan inteiro
(create_all + run_migrations) de novo — entrar duas vezes migraria a aula
ANTES da primeira leitura "de antes" acontecer. Por isso este teste semeia
o banco de uma vez só e entra no TestClient uma única vez: a migração e a
requisição acontecem na mesma passagem, e o estado "antes" é conferido no
disco (o arquivo existe onde `/media` o serviria), não por HTTP.
"""
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.database import Base, SessionLocal as _SessionLocal, engine
from app.main import app as _app
# O Nodal é opcional desde 24/08/2026 (ver app/main.py). Este arquivo importa
# o módulo, então ele inteiro é pulado quando a pasta app/nodal/ não existe.
# `importorskip` e não `pytestmark`: a marca pula os TESTES, mas o import do
# topo já teria estourado antes, na coleta.
pytest.importorskip("app.nodal", reason="módulo app.nodal ausente nesta cópia")

from app.nodal.models import Aula, Curso, Modulo



def test_get_no_media_do_caminho_antigo_da_404_apos_a_migracao():
    Base.metadata.create_all(bind=engine)  # tabelas prontas, sem passar pelo lifespan ainda

    pasta = settings.upload_dir / "nodal"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "slides-live.pdf").write_bytes(b"%PDF-1.4 fake")
    assert (pasta / "slides-live.pdf").is_file()  # o estado ANTES da migração

    db = _SessionLocal()
    try:
        c = Curso(slug="ia-live", titulo="IA", publicado=True)
        db.add(c)
        db.commit()
        m = Modulo(curso_id=c.id, titulo="Fundamentos", ordem=0)
        db.add(m)
        db.commit()
        db.add(Aula(curso_id=c.id, modulo_id=m.id, titulo="Uma", slug="uma", ordem=0,
                    blocos=[{"tipo": "pdf", "titulo": "Slides",
                             "arquivo": "/media/nodal/slides-live.pdf"}]))
        db.commit()
    finally:
        db.close()

    # um boot só: o lifespan roda run_migrations (que encontra a aula recém
    # criada e move o arquivo) ANTES desta mesma sessão de cliente pedir o
    # caminho antigo — é a MESMA garantia que vale em produção: a migração
    # roda no startup, antes de qualquer requisição ser atendida.
    with TestClient(_app, base_url="https://testserver") as client:
        resposta = client.get("/media/nodal/slides-live.pdf")

    assert resposta.status_code == 404
    assert not (pasta / "slides-live.pdf").exists(), "o arquivo tinha que sair do público"
    assert any(settings.nodal_private_dir.glob("slides-live*.pdf")), \
        "e continuar existindo, só que no diretório privado"
