"""Migrações leves de esquema para SQLite.

`create_all()` cria tabela que não existe, mas nunca acrescenta coluna em tabela que
já existe. Como o banco de produção já está no ar com dados, adicionar um campo a um
modelo quebraria tudo com "no such column" no primeiro acesso.

Aqui ficam só adições de coluna, que é o que o SQLite faz sem dor. Mudança de tipo ou
remoção exigiria recriar a tabela, e nesse dia vale trazer o Alembic.
"""
import json

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

# tabela -> [(coluna, definição SQL)]
COLUNAS = {
    # agenda de entrevistas do Admita (Lab de Demos): bancos criados antes
    # dela precisam da coluna, senão a esteira quebra na primeira consulta.
    "lab_candidato": [
        ("entrevista_em", "DATETIME"),
    ],
    "cases": [
        ("client_id", "INTEGER"),
        ("ia", "VARCHAR(4) DEFAULT ''"),
        ("ficha_on", "BOOLEAN DEFAULT 1"),
        ("archived", "BOOLEAN DEFAULT 0"),
        ("seo_title", "VARCHAR(200) DEFAULT ''"),
        ("seo_desc", "VARCHAR(320) DEFAULT ''"),
        ("seo_image", "VARCHAR(300) DEFAULT ''"),
        ("noindex", "BOOLEAN DEFAULT 0"),
        ("site_url", "VARCHAR(500) DEFAULT ''"),
        ("site_shot", "VARCHAR(300) DEFAULT ''"),
        ("site_shot_at", "DATETIME"),
        ("programas", "TEXT DEFAULT ''"),
        ("destaque_ordem", "INTEGER DEFAULT 999"),
    ],
    "categories": [
        ("kind", "VARCHAR(20) DEFAULT ''"),
    ],
    "users": [
        ("totp_secret", "VARCHAR(64) DEFAULT ''"),
        ("totp_ativo", "BOOLEAN DEFAULT 0"),
        ("totp_backup", "JSON"),
        ("totp_desde", "DATETIME"),
    ],
    "campaigns": [
        ("is_welcome", "BOOLEAN DEFAULT 0"),
        ("blocks", "JSON"),
        ("theme_id", "INTEGER"),
        ("origem", "VARCHAR(20) DEFAULT ''"),
    ],
    "newsletter_subs": [
        ("consent", "BOOLEAN DEFAULT 0"),
        ("consent_text", "TEXT DEFAULT ''"),
        ("consent_at", "DATETIME"),
        ("ip", "VARCHAR(64) DEFAULT ''"),
        ("user_agent", "VARCHAR(300) DEFAULT ''"),
        ("lang", "VARCHAR(5) DEFAULT 'pt'"),
    ],
    "nodal_aulas": [
        # o curso da aula, repetido aqui só para o banco conseguir impor
        # "endereço único dentro do curso" (ver o docstring de Aula)
        ("curso_id", "INTEGER"),
    ],
    "nodal_cursos": [
        ("para_quem", "VARCHAR(600) DEFAULT ''"),
        ("nao_e_para", "VARCHAR(600) DEFAULT ''"),
        ("preco_sobe_em", "DATE"),
        ("preco_depois_centavos", "INTEGER DEFAULT 0"),
        # o alvo da meta "Conclua N itens" da v2 — bancos no ar já têm cursos
        ("meta_diaria", "INTEGER DEFAULT 3"),
    ],
    "nodal_modulos": [
        # o cadeado manual da v2 — bancos de produção já têm módulos
        ("trancado", "BOOLEAN DEFAULT 0"),
    ],
}

# tabela -> [(nome do índice, colunas)] — únicos, criados depois das colunas
INDICES_UNICOS = {
    "nodal_aulas": [("uq_nodal_aulas_curso_slug", "curso_id, slug")],
}


LIMITE_SLUG_AULA = 120  # o mesmo String(120) declarado no modelo


def _preencher_curso_das_aulas(db: Session) -> int:
    """Copia o curso do módulo para as aulas que ainda não o têm.

    Roda antes de criar o índice único: um banco que já tinha aulas vem com
    `curso_id` nulo, e índice único sobre coluna nula não impõe nada.

    Só toca em aula cujo módulo ainda existe. Aula órfã — módulo apagado sem
    a cascata, coisa que um banco antigo pode ter — não tem curso de onde
    copiar, e tentar mesmo assim gravaria NULL em cima de NULL: a migração
    contaria a linha como preenchida e voltaria a "preencher" a cada boot,
    para sempre, sem nunca silenciar.
    """
    resultado = db.execute(text(
        "UPDATE nodal_aulas SET curso_id = ("
        "  SELECT curso_id FROM nodal_modulos WHERE nodal_modulos.id = nodal_aulas.modulo_id"
        ") WHERE curso_id IS NULL"
        "  AND modulo_id IN (SELECT id FROM nodal_modulos)"))
    return resultado.rowcount or 0


def _orfas_sem_curso(db: Session) -> int:
    """Quantas aulas ficaram sem curso porque o módulo delas não existe mais."""
    return db.execute(text(
        "SELECT COUNT(*) FROM nodal_aulas WHERE curso_id IS NULL")).scalar() or 0


def _desambiguar_slugs_repetidos(db: Session) -> list[str]:
    """Renomeia aulas que já nasceram com o mesmo endereço no mesmo curso.

    Sem isto, criar o índice único falha num banco que já acumulou duplicados
    — e falhar aqui deixaria a garantia desligada justamente onde ela mais
    faz falta. Renomear é a única saída que não perde aula: o endereço muda,
    o conteúdo fica.

    Duas armadilhas, as duas descobertas na revisão e as duas capazes de
    derrubar o boot:

    O nome novo pode cair em cima de um endereço legítimo. A numeração antiga
    contava por módulo, então um curso com dois módulos tinha "aula", "aula-2"
    repetidos; renomear a segunda "aula" para "aula-2" colidiria com uma aula
    que nunca foi duplicata. Por isso o sufixo sobe até achar um livre, e o
    conjunto dos ocupados inclui o que esta mesma passagem acabou de criar.

    E o corte no limite da coluna tem que comer a BASE, nunca o resultado:
    com slug de exatamente 120 caracteres, `f"{slug}-{id}"[:120]` devolve o
    slug original, a renomeação vira no-op e o índice falha em todo boot,
    sem recuperação.
    """
    ocupados = {(curso_id, slug) for curso_id, slug in db.execute(text(
        "SELECT curso_id, slug FROM nodal_aulas")).fetchall()}
    repetidas = db.execute(text(
        "SELECT id, curso_id, slug FROM nodal_aulas WHERE rowid NOT IN ("
        "  SELECT MIN(rowid) FROM nodal_aulas GROUP BY curso_id, slug"
        ") ORDER BY id")).fetchall()

    renomeadas: list[str] = []
    for aula_id, curso_id, slug in repetidas:
        sufixo, tentativa = aula_id, 0
        while True:
            marca = f"-{sufixo}"
            novo = f"{slug[:LIMITE_SLUG_AULA - len(marca)]}{marca}"
            if (curso_id, novo) not in ocupados:
                break
            tentativa += 1
            sufixo = f"{aula_id}-{tentativa}"
        # o endereço antigo continua ocupado: quem fica com ele é a primeira
        # aula do grupo, a que não foi renomeada
        ocupados.add((curso_id, novo))
        db.execute(text("UPDATE nodal_aulas SET slug = :s WHERE id = :i"),
                   {"s": novo, "i": aula_id})
        renomeadas.append(f"aula {aula_id}: {slug} -> {novo}")
    return renomeadas


def _mover_pdfs_de_aula_para_privado(db: Session) -> list[str]:
    """Move os PDFs de AULA (nunca Situação, que não tem tabela própria
    tocada aqui) do diretório PÚBLICO (`settings.upload_dir`, o que
    `/media` serve) para o PRIVADO (`settings.nodal_private_dir`), e
    reescreve o campo `arquivo` do bloco pra apontar pra lá — o achado da
    revisão da Tarefa 6 fechado na raiz (ver o Ruling da mini-tarefa de
    segurança, 19/08): o PDF pago não pode continuar num lugar que
    qualquer visitante alcança sem entrar.

    Trabalha em SQL cru sobre a coluna JSON `blocos`, como o resto deste
    arquivo — sem importar `app.nodal.models` (evita puxar o módulo do
    Nodal inteiro pra dentro de uma migração de schema/dado que hoje só
    conhece nomes de tabela e coluna).

    Idempotente por construção: só mexe em bloco cujo `arquivo` AINDA
    começa com "/media/" — depois de migrado uma vez, o campo passa a
    começar com "/nodal-privado/", e a passagem seguinte não encontra mais
    nada pra mover. Roda a cada boot (`run_migrations`) e a segunda vez em
    diante é sempre uma volta vazia.

    Arquivo ausente no disco (upload perdido, ou um banco restaurado sem os
    arquivos junto) NUNCA quebra o boot: a linha é pulada com um aviso no
    log, e o bloco continua apontando pro caminho antigo até alguém
    resolver à mão — um PDF quebrado é preferível ao site inteiro fora do
    ar por causa de um arquivo perdido. O Nodal não está em produção hoje
    (Ruling, 19/08); mesmo assim a migração é escrita como se estivesse,
    porque é o padrão da casa (ver o resto deste arquivo) e porque este
    banco pode virar produção amanhã sem ninguém revisar a migração de novo.

    Rodada de correção 1 (revisão, 19/08) — dois consertos, do mesmo achado
    reproduzido pelo revisor: um crash NO MEIO da migração podia deixar um
    link morto pra sempre.

    (a) COMMIT POR AULA processada, não um commit único no fim (que era
    responsabilidade de `run_migrations`, chamado só se `aplicadas` não
    viesse vazio). Antes, um crash entre o `rename` no disco de uma aula
    (arquivo já fisicamente no privado) e aquele commit único — que cobria
    TODAS as aulas já processadas na passagem — deixava o campo `arquivo`
    ainda em "/media/..." enquanto o arquivo físico já não estava mais lá.
    Committar aula por aula encolhe essa janela de inconsistência pro
    tamanho de UM arquivo: se o processo cair, no máximo a aula em
    andamento fica capenga, nunca as que já foram commitadas antes dela.

    (b) AUTOCURA: exatamente o estado que (a) deixava incompleto quando o
    crash acontece DENTRO da janela (o rename já rodou, o commit daquela
    aula ainda não) — a origem pública não existe mais (foi movida), mas
    `nodal_private_dir / origem.name` existe. Antes, isso caía no mesmo
    ramo de "upload perdido de verdade" (linha pulada, aviso no log, campo
    intocado) e NUNCA se curava sozinho — toda passagem seguinte repetia o
    mesmo "não encontrado", pra sempre, porque a origem realmente não
    volta a existir. Agora esse caso ganha um ramo próprio: reconhece o
    arquivo já no destino e reescreve o campo, sem mover nada (já está no
    lugar certo). A suposição por trás — dois PDFs de aulas DIFERENTES
    batendo no MESMO nome de arquivo público é uma coincidência que o
    token hex de `save_pdf` (4 bytes) já torna improvável — é a MESMA que o
    sufixo de colisão, logo abaixo, já fazia pro caso comum (origem
    presente); autocura nunca inventa arquivo, só reconhece um que já está
    exatamente onde o nome batido apontaria.
    """
    from ..config import settings  # import local: só esta função usa Path/disco

    # tests/test_migrations.py monta um `nodal_aulas` deliberadamente antigo
    # e incompleto (ESQUEMA_ANTIGO) pra testar SÓ a migração de curso_id —
    # sem coluna `blocos` nenhuma. Sem esta guarda, o SELECT abaixo estoura
    # "no such column: blocos" nesse cenário (e em qualquer banco real de
    # antes da Tarefa 1, que criou a tabela sem essa coluna também). Coluna
    # ausente não tem PDF nenhum pra mover — sai cedo, sem aplicar nada.
    colunas_existentes = {c["name"] for c in inspect(db.get_bind()).get_columns("nodal_aulas")}
    if "blocos" not in colunas_existentes:
        return []

    linhas = db.execute(text("SELECT id, blocos FROM nodal_aulas")).fetchall()
    aplicadas: list[str] = []
    raiz_publica = settings.upload_dir.resolve()

    for aula_id, blocos_json in linhas:
        try:
            blocos_atuais = json.loads(blocos_json) if blocos_json else []
        except (TypeError, ValueError):
            continue  # JSON corrompido: fora do escopo desta migração, não é dela consertar
        if not isinstance(blocos_atuais, list):
            continue

        mudou = False
        curou = False
        for bloco in blocos_atuais:
            if not isinstance(bloco, dict) or bloco.get("tipo") != "pdf":
                continue
            arquivo = bloco.get("arquivo")
            if not isinstance(arquivo, str) or not arquivo.startswith("/media/"):
                continue  # já migrado (prefixo novo), ou nunca foi um PDF público de verdade

            origem = (settings.upload_dir / arquivo[len("/media/"):]).resolve()
            if not str(origem).startswith(str(raiz_publica) + "/"):
                # "/media/../alguma-coisa" — não é um caminho que save_pdf/
                # save_upload jamais gravou; nada de tentar mover
                continue
            if not origem.is_file():
                # (b) Autocura: o nome batido já existe no privado — não é
                # arquivo perdido, é passagem anterior interrompida ENTRE o
                # rename e o commit desta MESMA aula. Só reescreve o campo.
                candidato_curado = settings.nodal_private_dir / origem.name
                if candidato_curado.is_file():
                    bloco["arquivo"] = f"/nodal-privado/{candidato_curado.name}"
                    mudou = True
                    curou = True
                    continue
                print(f"migração: PDF da aula {aula_id} não encontrado em disco "
                     f"({arquivo}) — bloco mantido como está, pulando", flush=True)
                continue

            settings.nodal_private_dir.mkdir(parents=True, exist_ok=True)
            destino = settings.nodal_private_dir / origem.name
            sufixo = 2
            while destino.exists():
                # dois PDFs públicos de aulas diferentes podem ter o MESMO
                # nome de arquivo (o token hex de save_pdf reduz a chance,
                # mas não a zera) — o destino ganha um sufixo em vez de um
                # sobrescrever o outro em silêncio
                destino = settings.nodal_private_dir / f"{origem.stem}-{sufixo}{origem.suffix}"
                sufixo += 1
            origem.rename(destino)
            bloco["arquivo"] = f"/nodal-privado/{destino.name}"
            mudou = True

        if mudou:
            db.execute(text("UPDATE nodal_aulas SET blocos = :b WHERE id = :i"),
                      {"b": json.dumps(blocos_atuais), "i": aula_id})
            # (a) commit POR AULA — não espera as outras linhas da mesma
            # passagem, nem o commit único que run_migrations fazia no fim.
            # Um crash logo depois desta linha não perde o que já foi
            # gravado até aqui; na pior hipótese, só ESTA aula fica pra
            # (b) autocurar na próxima passagem.
            db.commit()
            mensagem = ("PDF recuperado no diretório privado (autocura de passagem "
                       "interrompida)" if curou else "PDF movido pro diretório privado")
            aplicadas.append(f"nodal_aulas.blocos (aula {aula_id}): {mensagem}")

    return aplicadas


def run_migrations(db: Session) -> list[str]:
    """Acrescenta as colunas que faltarem. Devolve o que foi aplicado."""
    aplicadas: list[str] = []
    inspector = inspect(db.get_bind())
    tabelas = set(inspector.get_table_names())

    for tabela, colunas in COLUNAS.items():
        if tabela not in tabelas:
            continue  # create_all() já criou com tudo
        existentes = {c["name"] for c in inspector.get_columns(tabela)}
        for nome, definicao in colunas:
            if nome not in existentes:
                db.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}"))
                aplicadas.append(f"{tabela}.{nome}")

    # Fecha a fase das colunas antes de mexer em dado, porque daqui pra baixo
    # o código volta a consultar o `inspector` — e consultar o Inspector no
    # meio de uma transação aberta desfaz o que ela ainda não commitou.
    #
    # O Inspector pede uma conexão ao pool e a devolve, e a devolução emite
    # ROLLBACK. Num banco em arquivo (produção) ele recebe uma conexão
    # própria e o rollback não atinge ninguém; num banco em memória (os
    # testes) o pool tem uma conexão só, a mesma da sessão, e o UPDATE
    # pendente morre. O sintoma era cruel: a migração relatava "preenchido em
    # 3 aulas", com o número certo de linhas afetadas, e o banco ficava com as
    # três em NULL.
    #
    # (Registro a causa certa porque eu já errei o diagnóstico aqui uma vez,
    # e culpei o ALTER TABLE junto com o CREATE INDEX. Não é isso: os dois
    # convivem na mesma transação sem problema — testado nos dois modos.)
    if aplicadas:
        db.commit()

    # a coluna nova da aula só serve depois de preenchida, e o índice único
    # só pode nascer depois que os duplicados de antes forem desfeitos
    if "nodal_aulas" in tabelas:
        preenchidas = _preencher_curso_das_aulas(db)
        if preenchidas:
            aplicadas.append(f"nodal_aulas.curso_id preenchido em {preenchidas} aula(s)")
        for renomeada in _desambiguar_slugs_repetidos(db):
            aplicadas.append(f"endereço repetido desfeito — {renomeada}")
        orfas = _orfas_sem_curso(db) if aplicadas else 0
        if orfas:
            # aula cujo módulo sumiu: fica de fora da garantia (NULL não
            # conflita com NULL em índice único), e é melhor dizer isso em voz
            # alta no boot do que deixar quieto — é dado inconsistente que
            # alguém precisa olhar
            aplicadas.append(f"{orfas} aula(s) sem módulo, fora do índice único")
        db.commit()  # o índice único abaixo precisa do dado já arrumado

    for tabela, indices in INDICES_UNICOS.items():
        if tabela not in tabelas:
            continue  # create_all() já criou com o índice do __table_args__
        existentes = {i["name"] for i in inspector.get_indexes(tabela)}
        for nome, colunas_do_indice in indices:
            if nome not in existentes:
                db.execute(text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {nome} "
                    f"ON {tabela} ({colunas_do_indice})"))
                aplicadas.append(f"índice único {nome}")

    if aplicadas:
        db.commit()

    # Mini-tarefa de segurança (19/08): PDF de AULA sai do público — bloco
    # próprio, fora do "if aplicadas" de cima de propósito, porque ele
    # sempre precisa RODAR (é a própria função que decide, sozinha, se há
    # algo pra mover) mesmo num boot onde nenhuma coluna/índice mudou.
    #
    # Sem `db.commit()` aqui desde a rodada de correção 1 (19/08):
    # `_mover_pdfs_de_aula_para_privado` passou a committar POR AULA
    # processada (não um commit único no fim) — ver o docstring dela pro
    # porquê (um crash entre o commit único e o rename físico do arquivo
    # deixava link morto permanente). Um commit aqui seria só redundante.
    if "nodal_aulas" in tabelas:
        aplicadas.extend(_mover_pdfs_de_aula_para_privado(db))

    return aplicadas
