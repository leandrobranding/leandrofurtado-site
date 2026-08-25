"""Fixtures comuns da suíte.

O banco de teste é em memória e nasce vazio a cada teste: teste que depende do
estado deixado por outro é teste que passa sozinho e falha em conjunto.
"""
import atexit
import os
import shutil
import tempfile

# Isola o data/ que app.config vai usar antes de qualquer teste importar o
# módulo. A maioria dos testes nem chega perto disso — chamam função de rota
# direto com o fixture `db` abaixo, que é um SQLite em memória à parte. Mas
# quem sobe o app inteiro com TestClient (ver tests/test_seguranca.py) passa
# pelo SessionLocal real de app.database, e sem isto o processo inteiro fica
# preso no data/site.db do projeto — exatamente o banco que não pode ser
# tocado por teste nenhum.
#
# Atribuição direta, não `setdefault`: com `setdefault`, um DATA_DIR já
# exportado no shell de quem roda a suíte (apontando, por exemplo, pro
# diretório real do projeto) seria respeitado — o oposto da garantia que
# este bloco existe para dar. O isolamento não pode depender do ambiente de
# quem chama `pytest`.
_data_dir_testes = tempfile.mkdtemp(prefix="lf-testes-data-")
os.environ["DATA_DIR"] = _data_dir_testes
# Sem isto, cada execução da suíte deixava um diretório órfão em /tmp — o
# `mkdtemp` roda uma vez por processo (import do conftest), então a limpeza
# também só precisa rodar uma vez, na saída.
atexit.register(shutil.rmtree, _data_dir_testes, ignore_errors=True)

import os

# A vitrine pública do Nodal nasce DESLIGADA em produção (settings.nodal_publico,
# ver app/config.py): o produto não foi lançado. A suíte, ao contrário, precisa
# exercitar o produto inteiro — ela é o lugar onde ele existe por completo.
# Ligada aqui, ANTES de qualquer import de `app`, porque as configurações são
# lidas uma vez no import.
os.environ.setdefault("NODAL_PUBLICO", "true")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
# importar os modelos registra as tabelas no metadata antes do create_all
import app.models  # noqa: F401
import app.lab.models  # noqa: F401

# O Nodal é opcional desde 24/08/2026 (ver o comentário em app/main.py): sem a
# pasta app/nodal/ o projeto sobe e a suíte roda, só sem os testes do produto.
try:
    import app.nodal.models  # noqa: F401
except ModuleNotFoundError:
    pass


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragma(conexao, _):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    sessao = Sessao()
    try:
        yield sessao
    finally:
        sessao.close()
        engine.dispose()
