"""Testa a migração que leva o banco antigo até a garantia nova.

O banco de produção já está no ar. `create_all()` cria tabela que falta, mas
nunca acrescenta coluna nem índice a tabela que já existe — então a coluna
`nodal_aulas.curso_id` e o índice único de endereço só chegam lá por aqui.
Estes testes montam o esquema **antigo** à mão, com dados, e conferem que a
migração o transforma sem perder aula nenhuma.
"""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.config import settings
# O Nodal é opcional desde 24/08/2026 (ver app/main.py). Este arquivo importa
# o módulo, então ele inteiro é pulado quando a pasta app/nodal/ não existe.
# `importorskip` e não `pytestmark`: a marca pula os TESTES, mas o import do
# topo já teria estourado antes, na coleta.
pytest.importorskip("app.nodal", reason="módulo app.nodal ausente nesta cópia")

from app.nodal.models import Aula, Curso, Modulo, Situacao
from app.services.migrations import run_migrations


# nodal_aulas como era antes: sem curso_id, sem índice único
ESQUEMA_ANTIGO = [
    "CREATE TABLE nodal_cursos (id INTEGER PRIMARY KEY, slug VARCHAR(120), titulo VARCHAR(200))",
    "CREATE TABLE nodal_modulos (id INTEGER PRIMARY KEY, curso_id INTEGER, titulo VARCHAR(200))",
    "CREATE TABLE nodal_aulas (id INTEGER PRIMARY KEY, modulo_id INTEGER, "
    "  slug VARCHAR(120), titulo VARCHAR(200), ordem INTEGER DEFAULT 0)",
]


@pytest.fixture()
def banco_antigo():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    sessao = sessionmaker(bind=engine)()
    for comando in ESQUEMA_ANTIGO:
        sessao.execute(text(comando))
    sessao.commit()
    try:
        yield sessao
    finally:
        sessao.close()
        engine.dispose()


def _povoar(sessao, aulas):
    """aulas: lista de (curso_id, modulo_id, slug)."""
    cursos = {c for c, _, _ in aulas}
    modulos = {(c, m) for c, m, _ in aulas}
    for cid in cursos:
        sessao.execute(text("INSERT INTO nodal_cursos (id, slug, titulo) "
                            "VALUES (:i, :s, :t)"),
                       {"i": cid, "s": f"curso-{cid}", "t": f"Curso {cid}"})
    for cid, mid in modulos:
        sessao.execute(text("INSERT INTO nodal_modulos (id, curso_id, titulo) "
                            "VALUES (:i, :c, :t)"),
                       {"i": mid, "c": cid, "t": f"Módulo {mid}"})
    for i, (_, mid, slug) in enumerate(aulas, start=1):
        sessao.execute(text("INSERT INTO nodal_aulas (id, modulo_id, slug, titulo) "
                            "VALUES (:i, :m, :s, :t)"),
                       {"i": i, "m": mid, "s": slug, "t": f"Aula {i}"})
    sessao.commit()


def test_migracao_preenche_o_curso_das_aulas_que_ja_existiam(banco_antigo):
    _povoar(banco_antigo, [(1, 10, "introducao"), (1, 11, "briefing"), (2, 20, "introducao")])

    run_migrations(banco_antigo)

    linhas = banco_antigo.execute(text(
        "SELECT id, curso_id, slug FROM nodal_aulas ORDER BY id")).fetchall()
    assert [(l[1], l[2]) for l in linhas] == [
        (1, "introducao"), (1, "briefing"), (2, "introducao")]


def test_migracao_cria_o_indice_unico(banco_antigo):
    _povoar(banco_antigo, [(1, 10, "introducao")])

    run_migrations(banco_antigo)

    indices = {i["name"] for i in inspect(banco_antigo.get_bind()).get_indexes("nodal_aulas")}
    assert "uq_nodal_aulas_curso_slug" in indices

    # e ele impõe de verdade: segunda aula com o mesmo endereço no curso 1
    banco_antigo.execute(text("INSERT INTO nodal_modulos (id, curso_id, titulo) "
                              "VALUES (11, 1, 'M2')"))
    banco_antigo.commit()
    # o SQLite recusa já no INSERT, não espera o commit
    with pytest.raises(IntegrityError):
        banco_antigo.execute(text(
            "INSERT INTO nodal_aulas (modulo_id, curso_id, slug, titulo) "
            "VALUES (11, 1, 'introducao', 'Repetida')"))
        banco_antigo.commit()
    banco_antigo.rollback()


def test_migracao_desfaz_endereco_repetido_sem_perder_aula(banco_antigo):
    """Banco antigo pôde acumular duplicados — nada os impedia. Criar o índice
    sobre eles falharia, e falhar aqui deixaria a garantia desligada. Renomear
    é a única saída que não perde aula: o endereço muda, o conteúdo fica."""
    _povoar(banco_antigo, [(1, 10, "introducao"), (1, 11, "introducao"), (2, 20, "introducao")])

    aplicadas = run_migrations(banco_antigo)

    linhas = banco_antigo.execute(text(
        "SELECT id, curso_id, slug FROM nodal_aulas ORDER BY id")).fetchall()
    assert len(linhas) == 3, "nenhuma aula pode ter sumido"

    # a primeira do curso 1 fica com o endereço original; a repetida é renomeada
    assert (linhas[0][1], linhas[0][2]) == (1, "introducao")
    assert linhas[1][2] != "introducao"
    # curso diferente nunca foi conflito, então segue intacta
    assert (linhas[2][1], linhas[2][2]) == (2, "introducao")

    dentro_do_curso = [(l[1], l[2]) for l in linhas]
    assert len(dentro_do_curso) == len(set(dentro_do_curso))
    assert any("endereço repetido desfeito" in a for a in aplicadas)


def test_migracao_rodada_duas_vezes_nao_muda_nada(banco_antigo):
    """Ela roda a cada boot: a segunda vez tem que ser silenciosa."""
    _povoar(banco_antigo, [(1, 10, "introducao"), (1, 11, "introducao")])
    run_migrations(banco_antigo)
    antes = banco_antigo.execute(text(
        "SELECT id, curso_id, slug FROM nodal_aulas ORDER BY id")).fetchall()

    aplicadas = run_migrations(banco_antigo)

    depois = banco_antigo.execute(text(
        "SELECT id, curso_id, slug FROM nodal_aulas ORDER BY id")).fetchall()
    assert depois == antes
    assert aplicadas == []


def test_renomear_nao_atropela_endereco_legitimo(banco_antigo):
    """A numeração antiga contava por módulo, então um curso com dois módulos
    acumulava "aula" e "aula-2" repetidos. Renomear a segunda "aula" para
    "aula-2" cairia em cima de uma aula que nunca foi duplicata — e o índice
    falharia no boot, derrubando os dois workers."""
    _povoar(banco_antigo, [(1, 10, "aula"), (1, 11, "aula"),
                           (1, 10, "aula-2"), (1, 11, "aula-2")])

    run_migrations(banco_antigo)  # não pode levantar

    linhas = banco_antigo.execute(text(
        "SELECT curso_id, slug FROM nodal_aulas ORDER BY id")).fetchall()
    assert len(linhas) == 4, "nenhuma aula pode ter sumido"
    assert len(set(linhas)) == 4, f"endereço duplicado sobrou: {linhas}"


def test_slug_no_limite_da_coluna_ainda_e_desambiguado(banco_antigo):
    """f"{slug}-{id}"[:120] devolvia o próprio slug quando ele já tinha 120
    caracteres: a renomeação virava no-op, o índice falhava, e falhava em
    TODO boot seguinte — sem recuperação automática."""
    longo = "x" * 120
    _povoar(banco_antigo, [(1, 10, longo), (1, 11, longo)])

    run_migrations(banco_antigo)

    linhas = banco_antigo.execute(text(
        "SELECT curso_id, slug FROM nodal_aulas ORDER BY id")).fetchall()
    assert len(set(linhas)) == 2, "a desambiguação não aconteceu"
    assert all(len(slug) <= 120 for _, slug in linhas), "estourou a coluna"


def test_migracao_acrescenta_destaque_ordem_a_cases_existente():
    """`cases.destaque_ordem` é coluna nova (19/08): controla a ordem dos
    destaques na home. Um banco de produção já tem a tabela `cases` sem ela —
    monta esse esquema antigo à mão e confere que a migração acrescenta a
    coluna, com o default 999 (fim da fila) para quem já existia."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    sessao = sessionmaker(bind=engine)()
    try:
        sessao.execute(text(
            "CREATE TABLE cases (id INTEGER PRIMARY KEY, slug VARCHAR(140), "
            "  title_pt VARCHAR(200), featured BOOLEAN DEFAULT 0)"))
        sessao.execute(text(
            "INSERT INTO cases (id, slug, title_pt, featured) "
            "VALUES (1, 'antigo', 'Case antigo', 1)"))
        sessao.commit()

        aplicadas = run_migrations(sessao)

        colunas = {c["name"] for c in inspect(sessao.get_bind()).get_columns("cases")}
        assert "destaque_ordem" in colunas
        assert "cases.destaque_ordem" in aplicadas
        assert sessao.execute(text(
            "SELECT destaque_ordem FROM cases WHERE id = 1")).scalar() == 999
    finally:
        sessao.close()
        engine.dispose()


def test_aula_orfa_nao_faz_a_migracao_repetir_para_sempre(banco_antigo):
    """Aula cujo módulo não existe mais não tem curso de onde copiar. O
    UPDATE antigo gravava NULL em cima de NULL, contava a linha, e a migração
    voltava a "preencher" a cada boot, sem nunca silenciar."""
    _povoar(banco_antigo, [(1, 10, "a")])
    banco_antigo.execute(text(
        "INSERT INTO nodal_aulas (id, modulo_id, slug, titulo) "
        "VALUES (99, 777, 'orfa', 'Órfã')"))
    banco_antigo.commit()

    primeiro = run_migrations(banco_antigo)
    segundo = run_migrations(banco_antigo)

    assert any("sem módulo" in a for a in primeiro), "a órfã tem que ser dita em voz alta"
    assert segundo == [], f"a segunda passagem não silenciou: {segundo}"
    # a aula com módulo foi preenchida; a órfã ficou de fora, e é isso mesmo
    assert banco_antigo.execute(text(
        "SELECT curso_id FROM nodal_aulas WHERE id = 1")).scalar() == 1
    assert banco_antigo.execute(text(
        "SELECT curso_id FROM nodal_aulas WHERE id = 99")).scalar() is None


# --- Mini-tarefa de segurança (19/08): PDF de AULA sai do público ----------
#
# Usa o fixture `db` (tests/conftest.py) em vez de `banco_antigo`: aqui não
# se testa migração de ESQUEMA (a tabela já nasce com `blocos`, criada pelo
# ORM) — só migração de DADO, mover arquivo e reescrever o campo. `db` é o
# mesmo padrão que o resto da suíte do Nodal usa pra isso.
#
# Nomes de arquivo distintos por teste, de propósito: `settings.upload_dir`/
# `settings.nodal_private_dir` são pastas REAIS, compartilhadas por todo o
# processo de teste (isoladas por DATA_DIR, nunca por teste individual) —
# mesma disciplina que tests/nodal/test_painel_direito.py já segue
# (`_com_pdf_no_disco` recebe `nome_arquivo` explícito em cada chamada).

def _aula_com_pdf_publico(db, nome, conteudo=b"%PDF-1.4 fake"):
    """Uma aula com um bloco pdf ainda no formato ANTIGO (`/media/nodal/...`)
    e o arquivo de verdade em disco, no lugar que `save_pdf`/`save_upload`
    gravariam hoje — o estado que um banco de antes da rodada de segurança
    (19/08) tem."""
    c = Curso(slug=f"ia-{nome}", titulo="IA", publicado=True)
    db.add(c)
    db.commit()
    m = Modulo(curso_id=c.id, titulo="Fundamentos", ordem=0)
    db.add(m)
    db.commit()
    a = Aula(curso_id=c.id, modulo_id=m.id, titulo="Uma", slug="uma", ordem=0,
             blocos=[{"tipo": "pdf", "titulo": "Slides", "arquivo": f"/media/nodal/{nome}"}])
    db.add(a)
    db.commit()
    pasta = settings.upload_dir / "nodal"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_bytes(conteudo)
    return a


def test_migracao_move_o_pdf_da_aula_para_o_privado(db):
    aula = _aula_com_pdf_publico(db, "slides-migra-1.pdf")
    caminho_publico = settings.upload_dir / "nodal" / "slides-migra-1.pdf"
    assert caminho_publico.is_file()

    aplicadas = run_migrations(db)

    assert not caminho_publico.exists(), "o arquivo tinha que sair do público"
    assert any("PDF movido" in a for a in aplicadas)
    db.refresh(aula)
    novo_arquivo = aula.blocos[0]["arquivo"]
    assert novo_arquivo.startswith("/nodal-privado/")
    assert (settings.nodal_private_dir / novo_arquivo.removeprefix("/nodal-privado/")).is_file()


def test_migracao_do_pdf_e_idempotente(db):
    """Rodar duas vezes = mesmo estado — a segunda passagem não encontra
    mais nada pra mover."""
    _aula_com_pdf_publico(db, "slides-migra-2.pdf")
    primeiro = run_migrations(db)
    segundo = run_migrations(db)

    assert any("PDF movido" in a for a in primeiro)
    assert segundo == [], f"a segunda passagem não silenciou: {segundo}"


def test_migracao_com_arquivo_ausente_no_disco_nao_quebra_o_boot(db, capsys):
    """Upload perdido, ou um banco restaurado sem os arquivos junto: a
    linha é pulada com aviso no log, nunca derruba o boot."""
    aula = _aula_com_pdf_publico(db, "slides-sumiu.pdf")
    (settings.upload_dir / "nodal" / "slides-sumiu.pdf").unlink()

    aplicadas = run_migrations(db)  # não pode levantar

    assert not any("PDF movido" in a for a in aplicadas)
    saida = capsys.readouterr().out
    assert "não encontrado em disco" in saida
    db.refresh(aula)
    assert aula.blocos[0]["arquivo"] == "/media/nodal/slides-sumiu.pdf"  # nada tocado


def test_migracao_nunca_toca_pdf_de_situacao(db):
    """PDF de Situação é público por natureza (Ruling, 19/08) — a migração
    só lê `nodal_aulas`, nunca `nodal_situacoes`."""
    pasta = settings.upload_dir / "nodal"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "modelo-situacao-migra.pdf").write_bytes(b"%PDF-1.4 fake")
    s = Situacao(slug="briefing-migra", titulo="Briefing atrasado",
                blocos=[{"tipo": "pdf", "titulo": "Modelo",
                         "arquivo": "/media/nodal/modelo-situacao-migra.pdf"}])
    db.add(s)
    db.commit()

    run_migrations(db)

    db.refresh(s)
    assert s.blocos[0]["arquivo"] == "/media/nodal/modelo-situacao-migra.pdf"
    assert (pasta / "modelo-situacao-migra.pdf").is_file()


def test_migracao_ignora_bloco_ja_migrado(db):
    """Bloco cujo `arquivo` já começa com "/nodal-privado/" (migrado numa
    passagem anterior, ou aula nova criada já no formato certo) não é
    tocado — mesma garantia de idempotência, olhando o campo em vez do
    retorno da função inteira."""
    c = Curso(slug="ia-ja-migrado", titulo="IA", publicado=True)
    db.add(c)
    db.commit()
    m = Modulo(curso_id=c.id, titulo="Fundamentos", ordem=0)
    db.add(m)
    db.commit()
    a = Aula(curso_id=c.id, modulo_id=m.id, titulo="Uma", slug="uma", ordem=0,
             blocos=[{"tipo": "pdf", "titulo": "Slides",
                     "arquivo": "/nodal-privado/ja-migrado.pdf"}])
    db.add(a)
    db.commit()

    aplicadas = run_migrations(db)

    assert not any("PDF movido" in x for x in aplicadas)
    db.refresh(a)
    assert a.blocos[0]["arquivo"] == "/nodal-privado/ja-migrado.pdf"


# --- Rodada de correção 1 (revisão da mini-tarefa, 19/08) -------------------
#
# Achado (reproduzido pelo revisor): um crash NO MEIO da migração — depois
# do `rename` físico do arquivo, antes do commit que gravava o campo novo —
# deixava o bloco apontando pro público com o arquivo já fisicamente no
# privado. A passagem seguinte procurava a origem (que não existe mais,
# porque já foi movida), não achava, e desistia com o mesmo aviso de
# "arquivo perdido de verdade" — link morto PERMANENTE, nunca se curava
# sozinho. Ver o docstring de `_mover_pdfs_de_aula_para_privado` pro
# conserto duplo: commit por aula (encolhe a janela) + autocura (reconhece
# e conserta o estado que a janela, mesmo encolhida, ainda pode deixar).

def test_migracao_do_pdf_se_autocura_apos_crash_simulado(db, capsys):
    """Simula EXATAMENTE o estado do crash: o arquivo já está no diretório
    PRIVADO (o rename já rodou), mas o campo do bloco ainda diz
    "/media/..." (o commit daquela aula não chegou a acontecer). A origem
    pública NUNCA existiu nesta simulação — é o estado pós-rename, não
    pré-rename."""
    c = Curso(slug="ia-autocura", titulo="IA", publicado=True)
    db.add(c)
    db.commit()
    m = Modulo(curso_id=c.id, titulo="Fundamentos", ordem=0)
    db.add(m)
    db.commit()
    a = Aula(curso_id=c.id, modulo_id=m.id, titulo="Uma", slug="uma", ordem=0,
             blocos=[{"tipo": "pdf", "titulo": "Slides",
                     "arquivo": "/media/nodal/slides-crash.pdf"}])
    db.add(a)
    db.commit()

    settings.nodal_private_dir.mkdir(parents=True, exist_ok=True)
    (settings.nodal_private_dir / "slides-crash.pdf").write_bytes(b"%PDF-1.4 fake")

    aplicadas = run_migrations(db)

    assert any("autocura" in x for x in aplicadas), aplicadas
    db.refresh(a)
    assert a.blocos[0]["arquivo"] == "/nodal-privado/slides-crash.pdf"
    # nunca tratado como "arquivo perdido de verdade" — é outro caminho
    saida = capsys.readouterr().out
    assert "não encontrado em disco" not in saida


def test_migracao_do_pdf_e_idempotente_apos_autocura(db):
    """Depois de curado, o campo já aponta pro privado — o gatilho
    (prefixo "/media/") não bate mais, e uma segunda passagem não repete
    nada nem tenta mover de novo."""
    c = Curso(slug="ia-autocura-idem", titulo="IA", publicado=True)
    db.add(c)
    db.commit()
    m = Modulo(curso_id=c.id, titulo="Fundamentos", ordem=0)
    db.add(m)
    db.commit()
    a = Aula(curso_id=c.id, modulo_id=m.id, titulo="Uma", slug="uma", ordem=0,
             blocos=[{"tipo": "pdf", "titulo": "Slides",
                     "arquivo": "/media/nodal/slides-crash-idem.pdf"}])
    db.add(a)
    db.commit()
    settings.nodal_private_dir.mkdir(parents=True, exist_ok=True)
    (settings.nodal_private_dir / "slides-crash-idem.pdf").write_bytes(b"%PDF-1.4 fake")

    primeiro = run_migrations(db)
    segundo = run_migrations(db)

    assert any("autocura" in x for x in primeiro)
    assert segundo == [], f"a segunda passagem não silenciou: {segundo}"
