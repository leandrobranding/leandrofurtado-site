"""Modelos do Lab de Demos.

Cada tabela de demonstração carrega `sandbox_id` (index, FK para
`lab_sandbox.id`, `ondelete="CASCADE"`) porque o dado inteiro é descartável:
a limpeza diária (Task 2) apaga o sandbox vencido, e o `PRAGMA
foreign_keys=ON` já ligado em `database.py` derruba junto tudo que pende
dele — sem precisar de laço Python nem de `relationship(cascade=...)` aqui.

A exceção é `LabLead`: o contato captado num momento de valor (§10 da spec)
sobrevive à limpeza do sandbox que o gerou, por isso não tem `sandbox_id`
nem FK nenhuma para `lab_sandbox`.

Dinheiro entra em centavos inteiros (`total_centavos`, `valor_centavos`,
`custo_estimado_centavos`) pelo mesmo motivo do `preco_centavos` do Nodal
(ver `app/nodal/models.py`): ponto flutuante erra centavo em soma. A spec
(§5) nomeia os campos de forma curta ("total", "valor", "custo_estimado");
o sufixo `_centavos` é a mesma convenção monetária já em uso no repo, não
um campo a mais.

Conteúdo semeado (nomes, e-mails @exemplo.com.br, CPF/CNPJ inválidos por
design) é responsabilidade do `seeds_demo.py` (Plano 1, task futura) — este
módulo só declara forma, nunca dado (§9.9 da spec).

Cada uma das 9 tabelas de demo (todas exceto `LabSandbox`, `LabLead` e
`LabIaGasto`) carrega um campo `origem` com default `"visitante"` (ruling da
rodada de conserto da Task 3: "Seeds não contam" para o teto de
`MAX_REGISTROS_POR_DEMO` — §8 da spec). `checar_limite_registros`
(`app/lab/protecao.py`) filtra por `origem == "visitante"`; a Task 6
(`seeds_demo.py`) é OBRIGADA a gravar `origem="seed"` em todo registro que
semear, senão o cenário fictício consome o teto do visitante antes dele
clicar em qualquer coisa. Exceção de nome: `LabParecer` já usava `origem`
para 'ia'/'fallback' desde a Task 1 — o campo equivalente lá se chama
`origem_registro` para não colidir (ver comentário na própria classe).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def agora() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class LabSandbox(Base):
    """Uma sessão de visitante: nasce no primeiro acesso a qualquer demo e
    expira em 24h (§4/§8 da spec). Os contadores (`chamadas_ia`,
    `emails_enviados`, `pdfs_gerados`) são os tetos de segurança da §8 —
    cada guardião de recurso soma neles antes de agir, nunca recalcula na
    hora a partir das tabelas filhas."""

    __tablename__ = "lab_sandbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)
    expira_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    # demo pela qual o visitante entrou primeiro: "rh" | "fin" | "escola"
    demo_origem: Mapped[str] = mapped_column(String(20))
    chamadas_ia: Mapped[int] = mapped_column(Integer, default=0)
    emails_enviados: Mapped[int] = mapped_column(Integer, default=0)
    pdfs_gerados: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------- RH -----

class LabCandidato(Base):
    """Candidato da esteira de admissão (§6.1)."""

    __tablename__ = "lab_candidato"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — "Seeds não contam" para o teto de
    # MAX_REGISTROS_POR_DEMO (§8; ruling da revisão da Task 3). A Task 6
    # (seeds_demo.py) É OBRIGADA a gravar origem="seed" em tudo que semear.
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    nome: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[str] = mapped_column(String(200), default="")
    # esteira: candidato -> documentos -> aprovacao_rh -> aprovacao_gestor -> admitido
    etapa: Mapped[str] = mapped_column(String(30), default="candidato")
    # aprovação do gestor exige a do RH antes (§6.1) — a ordem é imposta na
    # rota (Plano 2), estes dois booleanos só guardam o estado
    aprovado_rh: Mapped[bool] = mapped_column(Boolean, default=False)
    aprovado_gestor: Mapped[bool] = mapped_column(Boolean, default=False)
    # currículo colado pelo visitante (texto morto, §9.2) ou um dos exemplos prontos
    curriculo: Mapped[str] = mapped_column(Text, default="")
    score_ia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    justificativa_ia: Mapped[str] = mapped_column(Text, default="")
    # 'ia' quando veio de chamada real ao guardião, 'fallback' quando estourou teto (§7)
    origem_ia: Mapped[str] = mapped_column(String(20), default="")
    # prazo/urgência visível por candidato (§6.1)
    prazo_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # data da entrevista marcada na agenda (nulo = ainda sem entrevista). O
    # visitante marca e desmarca pelo calendário do painel de agenda.
    entrevista_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabCargo(Base):
    """Cargo que aparece no dropdown de nova candidatura (§6.1).

    Vive por sandbox porque o visitante pode criar, renomear e excluir os
    seus. O cargo do candidato continua gravado como TEXTO em
    `LabCandidato.cargo`: excluir um cargo da lista não pode reescrever a
    história de quem já foi cadastrado com ele.
    """

    __tablename__ = "lab_cargo"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    nome: Mapped[str] = mapped_column(String(80))
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabDocumentoStatus(Base):
    """Um item do checklist de documentos SIMULADOS de um candidato —
    conferido/pendente, nunca upload de verdade (§9.1)."""

    __tablename__ = "lab_documento_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    candidato_id: Mapped[int] = mapped_column(
        ForeignKey("lab_candidato.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    tipo: Mapped[str] = mapped_column(String(60))
    conferido: Mapped[bool] = mapped_column(Boolean, default=False)


class LabAuditoria(Base):
    """Trilha de auditoria da esteira: quem, quando, o quê (§6.1)."""

    __tablename__ = "lab_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    quem: Mapped[str] = mapped_column(String(100))
    acao: Mapped[str] = mapped_column(String(200))
    quando: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


# --------------------------------------------------------- Financeiro ----

class LabClienteFiscal(Base):
    """Cliente fictício ao qual uma nota fiscal de demonstração é emitida."""

    __tablename__ = "lab_cliente_fiscal"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    nome: Mapped[str] = mapped_column(String(200))
    # CNPJ/CPF fictício, inválido por design (§9.9) — nunca um documento real
    documento: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabNota(Base):
    """Nota fiscal de demonstração — tarja 'SEM VALOR FISCAL' fica na tela,
    não no dado (§6.2). `numero` é sequencial POR sandbox, não global."""

    __tablename__ = "lab_nota"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("lab_cliente_fiscal.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    numero: Mapped[int] = mapped_column(Integer)
    # contrato de itens/impostos: ver docstring de app/lab/pdf.py
    itens: Mapped[list] = mapped_column(JSON, default=list)
    impostos: Mapped[dict] = mapped_column(JSON, default=dict)
    total_centavos: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="emitida")  # emitida | cancelada
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabLancamento(Base):
    """Linha do extrato categorizado pela IA (ou fallback) em categoria
    contábil de lista fechada (§6.2)."""

    __tablename__ = "lab_lancamento"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    descricao: Mapped[str] = mapped_column(String(200))
    valor_centavos: Mapped[int] = mapped_column(Integer, default=0)
    categoria: Mapped[str] = mapped_column(String(40), default="")
    justificativa_ia: Mapped[str] = mapped_column(Text, default="")
    origem_ia: Mapped[str] = mapped_column(String(20), default="")
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


# -------------------------------------------------------------- Escola ---

class LabAluno(Base):
    """Aluno da turma do diário de classe (§6.3)."""

    __tablename__ = "lab_aluno"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    nome: Mapped[str] = mapped_column(String(200))
    turma: Mapped[str] = mapped_column(String(40), default="")
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabAvaliacao(Base):
    """Nota e faltas de um aluno numa disciplina — a base da média
    ponderada e da situação (aprovado/recuperação/reprovado) da §6.3."""

    __tablename__ = "lab_avaliacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("lab_aluno.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    disciplina: Mapped[str] = mapped_column(String(60))
    # 0-10; formato exato validado em protecao.py (Task 3), não aqui
    nota: Mapped[float] = mapped_column(Float, default=0.0)
    faltas: Mapped[int] = mapped_column(Integer, default=0)
    bimestre: Mapped[int] = mapped_column(Integer, default=1)


class LabParecer(Base):
    """Parecer pedagógico por aluno, gerado pela IA ou pelo fallback
    pré-computado (§6.3/§7)."""

    __tablename__ = "lab_parecer"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("lab_aluno.id", ondelete="CASCADE"), index=True)
    texto_ia: Mapped[str] = mapped_column(Text, default="")
    origem: Mapped[str] = mapped_column(String(20), default="")  # 'ia' | 'fallback'
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima.
    # Nome DIFERENTE de propósito: esta classe já usava `origem` (acima) para
    # 'ia'/'fallback' desde a Task 1 — reaproveitar o nome colidiria os dois
    # sentidos na mesma tabela. `origem_registro` é o equivalente de
    # "visitante"/"seed" só para LabParecer; nas outras 8 tabelas de demo o
    # campo se chama `origem` mesmo (sem colisão nelas).
    origem_registro: Mapped[str] = mapped_column(String(20), default="visitante")
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


# -------------------------------------------------------------- Global ---

class LabLead(Base):
    """Contato captado num momento de valor (§10 da spec).

    Sobrevive à limpeza do sandbox que o gerou — por isso, ao contrário de
    toda outra tabela deste módulo, NÃO tem `sandbox_id` nem FK para
    `lab_sandbox`: apagar o sandbox não pode apagar o lead que ele rendeu.
    """

    __tablename__ = "lab_lead"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    demo: Mapped[str] = mapped_column(String(20))
    momento: Mapped[str] = mapped_column(String(60))
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabIaGasto(Base):
    """Acumulador diário de gasto de IA — o teto diário GLOBAL do guardião
    (§7) soma aqui; o teto POR SANDBOX é `LabSandbox.chamadas_ia`."""

    __tablename__ = "lab_ia_gasto"

    id: Mapped[int] = mapped_column(primary_key=True)
    dia: Mapped[dt.date] = mapped_column(Date, unique=True, index=True)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    custo_estimado_centavos: Mapped[int] = mapped_column(Integer, default=0)
