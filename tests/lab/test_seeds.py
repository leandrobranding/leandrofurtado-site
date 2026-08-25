"""Testes dos seeds dos três cenários fictícios do Lab (Task 6 do Plano 1 —
§6/§9.9 da spec).

Usa o fixture `db` de `tests/conftest.py` (SQLite em memória, isolado por
teste) — `semear_cenario` só recebe `db`/`sandbox`, não sobe HTTP nem app."""
import datetime as dt

import pytest

from app.lab.models import (
    LabAluno,
    LabAuditoria,
    LabAvaliacao,
    LabCandidato,
    LabClienteFiscal,
    LabDocumentoStatus,
    LabLancamento,
    LabNota,
    LabParecer,
    LabSandbox,
)
from app.lab.protecao import checar_limite_registros
from app.lab.seeds_demo import (
    _cnpj_ficticio,
    _cpf_ficticio,
    _dv_modulo11,
    semear_cenario,
)


def _novo_sandbox(db, token="tok-seed-teste") -> LabSandbox:
    sandbox = LabSandbox(
        token=token, demo_origem="rh",
        expira_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24),
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    return sandbox


# ------------------------------------------------------------ idempotência --

def test_semear_duas_vezes_no_mesmo_sandbox_nao_duplica(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)
    semear_cenario(db, sandbox)

    assert db.query(LabCandidato).filter(LabCandidato.sandbox_id == sandbox.id).count() == 6
    assert db.query(LabClienteFiscal).filter(LabClienteFiscal.sandbox_id == sandbox.id).count() == 4
    assert db.query(LabAluno).filter(LabAluno.sandbox_id == sandbox.id).count() == 8


# --------------------------------------------------------- contagens exatas --

def test_contagens_exatas_rh(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    assert db.query(LabCandidato).filter(LabCandidato.sandbox_id == sandbox.id).count() == 6
    assert db.query(LabDocumentoStatus).filter(LabDocumentoStatus.sandbox_id == sandbox.id).count() == 15
    assert db.query(LabAuditoria).filter(LabAuditoria.sandbox_id == sandbox.id).count() == 8


def test_contagens_exatas_financeiro(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    assert db.query(LabClienteFiscal).filter(LabClienteFiscal.sandbox_id == sandbox.id).count() == 4
    notas = db.query(LabNota).filter(LabNota.sandbox_id == sandbox.id).order_by(LabNota.numero).all()
    assert len(notas) == 6
    assert [n.numero for n in notas] == [1, 2, 3, 4, 5, 6]
    assert db.query(LabLancamento).filter(LabLancamento.sandbox_id == sandbox.id).count() == 12


def test_contagens_exatas_escola(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    assert db.query(LabAluno).filter(LabAluno.sandbox_id == sandbox.id).count() == 8
    assert db.query(LabAvaliacao).filter(LabAvaliacao.sandbox_id == sandbox.id).count() == 32
    assert db.query(LabParecer).filter(LabParecer.sandbox_id == sandbox.id).count() == 2


# --------------------------------------------------------------- isolamento --

def test_seed_de_um_sandbox_invisivel_ao_outro(db):
    a = _novo_sandbox(db, token="tok-a")
    b = _novo_sandbox(db, token="tok-b")
    semear_cenario(db, a)
    semear_cenario(db, b)

    candidatos_a = db.query(LabCandidato).filter(LabCandidato.sandbox_id == a.id).count()
    candidatos_b = db.query(LabCandidato).filter(LabCandidato.sandbox_id == b.id).count()
    assert candidatos_a == 6
    assert candidatos_b == 6
    assert db.query(LabCandidato).count() == 12  # nada vazou de um pro outro

    nomes_a = {c.nome for c in db.query(LabCandidato).filter(LabCandidato.sandbox_id == a.id)}
    nomes_b = {c.nome for c in db.query(LabCandidato).filter(LabCandidato.sandbox_id == b.id)}
    assert nomes_a == nomes_b  # mesmo elenco fictício, linhas diferentes


# ------------------------------------------------------------------ e-mails --

def test_todo_email_semeado_termina_em_exemplo_com_br(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    clientes = db.query(LabClienteFiscal).filter(LabClienteFiscal.sandbox_id == sandbox.id).all()
    assert clientes
    for cliente in clientes:
        assert cliente.email.endswith("@exemplo.com.br"), cliente.email


# ---------------------------------------------------------------- origem=seed

def test_todos_os_registros_semeados_tem_origem_seed(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    modelos_origem = (
        LabCandidato, LabDocumentoStatus, LabAuditoria, LabClienteFiscal,
        LabNota, LabLancamento, LabAluno, LabAvaliacao,
    )
    for modelo in modelos_origem:
        registros = db.query(modelo).filter(modelo.sandbox_id == sandbox.id).all()
        assert registros, modelo
        for registro in registros:
            assert registro.origem == "seed", (modelo, registro.id)

    pareceres = db.query(LabParecer).filter(LabParecer.sandbox_id == sandbox.id).all()
    assert pareceres
    for parecer in pareceres:
        assert parecer.origem_registro == "seed"
        assert parecer.origem == "fallback"


# ------------------------------------------------ visitante ainda tem 10 slots

def test_visitante_ainda_tem_os_10_slots_apos_seed(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    # não levanta ValueError -- checar_limite_registros ignora os seeds
    checar_limite_registros(db, sandbox, "rh")
    checar_limite_registros(db, sandbox, "fin")
    checar_limite_registros(db, sandbox, "escola")

    # e o teto real ainda é alcançável: adicionar 10 "de visitante" agora
    # estoura, confirmando que os 6 candidatos do seed não contam para isso
    for _ in range(10):
        db.add(LabCandidato(sandbox_id=sandbox.id, origem="visitante", nome="X", cargo="Y"))
    db.commit()
    with pytest.raises(ValueError):
        checar_limite_registros(db, sandbox, "rh")


# ---------------------------------------------------------------- substância

def test_rh_cobre_as_regras_da_esteira(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    candidatos = {
        c.nome: c for c in db.query(LabCandidato).filter(LabCandidato.sandbox_id == sandbox.id)
    }

    # travado em Documentos com pendência real no checklist
    travado = candidatos["Adriana Souza Lima"]
    assert travado.etapa == "documentos"
    pendencias = (
        db.query(LabDocumentoStatus)
        .filter(LabDocumentoStatus.candidato_id == travado.id, LabDocumentoStatus.conferido.is_(False))
        .count()
    )
    assert pendencias >= 1

    # aguardando gestor com o aval do RH já dado
    aguardando_gestor = candidatos["Bruno Andrade Costa"]
    assert aguardando_gestor.etapa == "aprovacao_gestor"
    assert aguardando_gestor.aprovado_rh is True
    assert aguardando_gestor.aprovado_gestor is False

    # admitido
    admitido = candidatos["Camila Ferreira Dias"]
    assert admitido.etapa == "admitido"
    assert admitido.aprovado_rh is True and admitido.aprovado_gestor is True

    # prazo estourado (SLA) existe, e nem todo prazo está estourado
    agora = dt.datetime.now(dt.timezone.utc)
    prazos = [c.prazo_em for c in candidatos.values() if c.prazo_em is not None]
    prazos_normalizados = [
        p if p.tzinfo else p.replace(tzinfo=dt.timezone.utc) for p in prazos
    ]
    assert any(p <= agora for p in prazos_normalizados), "esperava ao menos um prazo estourado"
    assert any(p > agora for p in prazos_normalizados), "esperava ao menos um prazo no prazo"


def test_financeiro_tem_uma_nota_cancelada_e_contrato_json_valido(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    notas = db.query(LabNota).filter(LabNota.sandbox_id == sandbox.id).all()
    canceladas = [n for n in notas if n.status == "cancelada"]
    emitidas = [n for n in notas if n.status == "emitida"]
    assert len(canceladas) == 1
    assert len(emitidas) == 5

    for nota in notas:
        assert isinstance(nota.itens, list) and nota.itens
        for item in nota.itens:
            assert set(item.keys()) >= {"descricao", "quantidade", "valor_unit_centavos"}
            assert isinstance(item["valor_unit_centavos"], int)
        assert isinstance(nota.impostos, dict) and nota.impostos
        for categoria, valor in nota.impostos.items():
            assert isinstance(categoria, str)
            assert isinstance(valor, int)
        assert nota.total_centavos > 0
        assert nota.total_centavos % 100 == 0  # valores redondos (múltiplo de R$1,00)


def test_financeiro_lancamentos_usam_categorias_fechadas(db):
    from app.lab.ia import CATEGORIAS_FECHADAS

    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    lancamentos = db.query(LabLancamento).filter(LabLancamento.sandbox_id == sandbox.id).all()
    assert len(lancamentos) == 12
    for lancamento in lancamentos:
        assert lancamento.categoria in CATEGORIAS_FECHADAS


def test_escola_cobre_as_tres_situacoes(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    alunos = db.query(LabAluno).filter(LabAluno.sandbox_id == sandbox.id).all()
    situacoes = set()
    for aluno in alunos:
        avaliacoes = (
            db.query(LabAvaliacao)
            .filter(LabAvaliacao.sandbox_id == sandbox.id, LabAvaliacao.aluno_id == aluno.id)
            .all()
        )
        assert len(avaliacoes) == 4
        media = sum(a.nota for a in avaliacoes) / len(avaliacoes)
        faltas_totais = sum(a.faltas for a in avaliacoes)
        if faltas_totais > 20:
            situacoes.add("reprovado")
        elif media >= 6:
            situacoes.add("aprovado")
        elif media >= 4:
            situacoes.add("recuperacao")
        else:
            situacoes.add("reprovado")

    assert situacoes == {"aprovado", "recuperacao", "reprovado"}


def test_escola_turma_e_pareceres_marcados_fallback(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    alunos = db.query(LabAluno).filter(LabAluno.sandbox_id == sandbox.id).all()
    assert all(a.turma == "3º B (fictícia)" for a in alunos)

    pareceres = db.query(LabParecer).filter(LabParecer.sandbox_id == sandbox.id).all()
    assert len(pareceres) == 2
    for parecer in pareceres:
        assert parecer.origem == "fallback"
        assert parecer.texto_ia


# -------------------------------------------------------- fictício por design

def test_cpfs_e_cnpjs_semeados_sao_invalidos_por_design(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    clientes = db.query(LabClienteFiscal).filter(LabClienteFiscal.sandbox_id == sandbox.id).all()
    assert clientes
    for cliente in clientes:
        documento = cliente.documento
        digitos = [int(c) for c in documento if c.isdigit()]
        assert len(digitos) == 14  # CNPJ

        base = digitos[:12]
        dv1_gravado, dv2_gravado = digitos[12], digitos[13]

        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        dv1_correto = _dv_modulo11(base, pesos1)
        dv2_correto = _dv_modulo11(base + [dv1_correto], pesos2)

        assert dv1_gravado == dv1_correto  # só o segundo dígito é quebrado
        assert dv2_gravado != dv2_correto  # inválido por design


def test_cpf_ficticio_helper_e_invalido_por_design():
    documento = _cpf_ficticio("111444777")
    digitos = [int(c) for c in documento if c.isdigit()]
    assert len(digitos) == 11
    base, dv1_gravado, dv2_gravado = digitos[:9], digitos[9], digitos[10]
    dv1_correto = _dv_modulo11(base, range(10, 1, -1))
    dv2_correto = _dv_modulo11(base + [dv1_correto], range(11, 1, -1))
    assert dv1_gravado == dv1_correto
    assert dv2_gravado != dv2_correto


def test_empresa_rh_e_declarada_ficticia(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    auditoria = db.query(LabAuditoria).filter(LabAuditoria.sandbox_id == sandbox.id).all()
    assert any("empresa fictícia" in a.acao for a in auditoria)


def test_nenhum_texto_semeado_contem_caractere_de_controle(db):
    sandbox = _novo_sandbox(db)
    semear_cenario(db, sandbox)

    textos = []
    for c in db.query(LabCandidato).filter(LabCandidato.sandbox_id == sandbox.id):
        textos += [c.nome, c.cargo, c.curriculo, c.justificativa_ia]
    for a in db.query(LabAuditoria).filter(LabAuditoria.sandbox_id == sandbox.id):
        textos += [a.quem, a.acao]
    for cli in db.query(LabClienteFiscal).filter(LabClienteFiscal.sandbox_id == sandbox.id):
        textos += [cli.nome, cli.documento, cli.email]
    for al in db.query(LabAluno).filter(LabAluno.sandbox_id == sandbox.id):
        textos += [al.nome, al.turma]
    for p in db.query(LabParecer).filter(LabParecer.sandbox_id == sandbox.id):
        textos += [p.texto_ia]

    import unicodedata
    for texto in textos:
        for caractere in texto or "":
            assert unicodedata.category(caractere) not in ("Cc", "Cf", "Cs"), repr(texto)
