import datetime as dt

from app.database import Base
from app.lab.models import LabCandidato, LabLead, LabSandbox


def test_sandbox_tem_campos_e_defaults(db):
    s = LabSandbox(token="tok-teste", demo_origem="rh",
                    expira_em=dt.datetime.now(dt.UTC) + dt.timedelta(hours=24))
    db.add(s); db.commit()
    assert s.chamadas_ia == 0 and s.emails_enviados == 0 and s.pdfs_gerados == 0


def test_tabelas_de_demo_tem_sandbox_id():
    for t in ("lab_candidato", "lab_nota", "lab_aluno", "lab_avaliacao",
              "lab_documento_status", "lab_auditoria", "lab_cliente_fiscal",
              "lab_lancamento", "lab_parecer"):
        cols = {c.name for c in Base.metadata.tables[t].columns}
        assert "sandbox_id" in cols, t


def test_lead_sobrevive_sem_sandbox(db):
    l = LabLead(nome="Teste", email="t@exemplo.com.br", demo="fin", momento="nf_email")
    db.add(l); db.commit()
    assert l.id


def test_tabelas_de_demo_tem_campo_de_origem_visitante_ou_seed():
    # Ruling da rodada de conserto da Task 3: "Seeds não contam" (§8) — as 9
    # tabelas de demo ganham `origem` default "visitante"; `LabParecer` é a
    # única exceção de NOME (já usava `origem` para 'ia'/'fallback' desde a
    # Task 1), o campo equivalente lá é `origem_registro`.
    tabelas_com_origem = {
        "lab_candidato": "origem", "lab_documento_status": "origem",
        "lab_auditoria": "origem", "lab_cliente_fiscal": "origem",
        "lab_nota": "origem", "lab_lancamento": "origem",
        "lab_aluno": "origem", "lab_avaliacao": "origem",
        "lab_parecer": "origem_registro",
    }
    assert len(tabelas_com_origem) == 9
    for tabela, coluna in tabelas_com_origem.items():
        cols = {c.name for c in Base.metadata.tables[tabela].columns}
        assert coluna in cols, tabela


def test_registro_de_demo_nasce_com_origem_visitante_por_padrao(db):
    s = LabSandbox(token="tok-origem", demo_origem="rh",
                    expira_em=dt.datetime.now(dt.UTC) + dt.timedelta(hours=24))
    db.add(s); db.commit()
    c = LabCandidato(sandbox_id=s.id, nome="Fulano")
    db.add(c); db.commit()
    assert c.origem == "visitante"
