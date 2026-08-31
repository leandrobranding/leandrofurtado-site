"""Contador de eventos por chave, compartilhado entre os processos do servidor.

POR QUE EXISTE

Até 24/08/2026 os dois limites do site contavam num dicionário na memória do
processo: `_envios` no anti-spam e `_attempts` no login do admin. O contêiner
roda `uvicorn --workers 2`, e cada worker tem a sua própria memória.

O efeito era silencioso e sempre a favor de quem ataca: com dois workers e o
balanceamento alternando entre eles, o limite REAL era o dobro do escrito. Um
teto de 3 envios por IP aceitava 6; 6 tentativas de login aceitavam 12. Nada
disso aparecia em teste, porque teste roda num processo só.

COMO RESOLVE

Um SQLite próprio, em `data/limites.db`, em modo WAL. Os workers são processos
do mesmo contêiner, no mesmo disco: um arquivo é a memória compartilhada mais
simples que existe aqui, sem subir serviço nenhum (custo zero é restrição do
projeto, não preferência).

Banco à parte, e não uma tabela no `site.db`, por dois motivos: escrita de
limite não entra na transação de quem chamou, e um arquivo de contadores pode
ser apagado a qualquer momento sem perder nada que importe.

O QUE ELE NÃO É

Não é rate limit de borda. Requisição que nunca chega à aplicação (enxurrada
em cima de arquivo estático, por exemplo) é problema do nginx. Isto conta
eventos de negócio: envio de formulário e tentativa de login.
"""
import sqlite3
import time
from pathlib import Path

from ..config import settings

_ARQUIVO = "limites.db"
_conexoes: dict[int, sqlite3.Connection] = {}


def _caminho() -> Path:
    return settings.data_dir / _ARQUIVO


def _conexao() -> sqlite3.Connection:
    """Uma conexão por processo, reaproveitada.

    `check_same_thread=False` porque o uvicorn atende em threads dentro do
    mesmo worker; o `timeout` cobre o instante em que outro worker está
    escrevendo, que em WAL é curto e raro no volume deste site.
    """
    chave = id(settings)
    con = _conexoes.get(chave)
    if con is not None:
        return con
    _caminho().parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(_caminho(), timeout=5, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("CREATE TABLE IF NOT EXISTS eventos "
                "(chave TEXT NOT NULL, quando REAL NOT NULL)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_eventos_chave "
                "ON eventos (chave, quando)")
    con.commit()
    _conexoes[chave] = con
    return con


def permitir(chave: str, maximo: int, janela: int,
             agora: float | None = None) -> bool:
    """Registra um evento e diz se ele cabe no teto da janela.

    Devolve True e GRAVA quando cabe; devolve False e não grava quando não
    cabe — assim uma rajada bloqueada não empurra a janela para frente, que
    faria o bloqueio durar mais do que o combinado a cada nova tentativa.
    """
    agora = time.time() if agora is None else agora
    corte = agora - janela
    con = _conexao()
    with con:
        con.execute("DELETE FROM eventos WHERE quando < ?", (corte,))
        (quantos,) = con.execute(
            "SELECT COUNT(*) FROM eventos WHERE chave = ? AND quando >= ?",
            (chave, corte)).fetchone()
        if quantos >= maximo:
            return False
        con.execute("INSERT INTO eventos (chave, quando) VALUES (?, ?)",
                    (chave, agora))
    return True


def registrar(chave: str, agora: float | None = None) -> None:
    """Grava um evento sem perguntar se cabe.

    Existe porque o login tem DUAS etapas separadas: `login_allowed` decide
    antes de tentar autenticar, e `register_attempt` grava só quando a senha
    erra. Acerto não gasta cota — quem entra na primeira não fica perto do
    teto por ter entrado.
    """
    agora = time.time() if agora is None else agora
    con = _conexao()
    with con:
        con.execute("INSERT INTO eventos (chave, quando) VALUES (?, ?)",
                    (chave, agora))


def quantos(chave: str, janela: int, agora: float | None = None) -> int:
    """Eventos da chave dentro da janela. Só para teste e diagnóstico."""
    agora = time.time() if agora is None else agora
    con = _conexao()
    (n,) = con.execute(
        "SELECT COUNT(*) FROM eventos WHERE chave = ? AND quando >= ?",
        (chave, agora - janela)).fetchone()
    return n


def limpar() -> None:
    """Zera o contador. Usado pelos testes entre um caso e outro."""
    con = _conexao()
    with con:
        con.execute("DELETE FROM eventos")


def esquecer_conexao() -> None:
    """Fecha a conexão do processo. Só para teste, quando o `data_dir` muda."""
    for con in _conexoes.values():
        con.close()
    _conexoes.clear()
