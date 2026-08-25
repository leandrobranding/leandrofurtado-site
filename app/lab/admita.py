"""Regras e dados da esteira de admissão (Admita — Task 4 do Plano 2, §6.1
da spec). `app/lab/rotas.py` só faz o fiapo HTTP (validar entrada, chamar
uma função daqui, devolver resposta); toda a substância mora aqui para ser
testável sem TestClient.

Etapas nomeadas e validadas por 3 fontes do estudo setorial
(`.superpowers/sdd/2026-08-20-lab-demos/referencias-rh-estudo.md`, Síntese
Final): Cadastro enviado -> Documentos -> Aprovação do RH -> Aprovação do
gestor -> Admitido. As chaves internas (`candidato`/`documentos`/
`aprovacao_rh`/`aprovacao_gestor`/`admitido`) são as mesmas que
`app/lab/models.py::LabCandidato.etapa` e `app/lab/seeds_demo.py` já usam —
este módulo não inventa vocabulário novo de etapa, só rotula para exibição.

REGRAS DE NEGÓCIO REAIS (§6.1, "é o que separa demo séria de brinquedo"):
- Documentos -> Aprovação do RH exige todo item do checklist conferido.
- Aprovação do gestor exige a aprovação do RH ANTES (`aprovado_rh=True`).
- Toda ação grava uma linha em `LabAuditoria` (quem, quando, o quê).
Cada regra levanta `ValueError` com mensagem em PT-BR pronta para o
visitante (explica o que fazer, nunca um erro técnico cru) — a rota
converte para `HTTPException(409, detail=str(erro))`.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from .models import LabAuditoria, LabCandidato, LabCargo, LabDocumentoStatus, LabSandbox
from .protecao import MAX_CAMPO, checar_limite_registros, validar_texto
from .seeds_demo import (
    EMPRESA_RH,
    EMPRESA_RH_NOTA,
    USUARIO_RH,
    USUARIO_RH_EMAIL,
    USUARIO_RH_PERFIL,
)

# Ordem canônica da esteira — a mesma usada pelo seed (`seeds_demo.py`).
ETAPAS: tuple[str, ...] = (
    "candidato", "documentos", "aprovacao_rh", "aprovacao_gestor", "admitido",
)

ETAPA_LABEL: dict[str, str] = {
    "candidato": "Cadastro enviado",
    "documentos": "Documentos",
    "aprovacao_rh": "Aprovação do RH",
    "aprovacao_gestor": "Aprovação do gestor",
    "admitido": "Admitido",
}

# Ícone de cada etapa no sprite admita.svg (ver app/static/lab/icones/admita.svg)
ETAPA_ICONE: dict[str, str] = {
    "candidato": "i-usuario",
    "documentos": "i-documentos",
    "aprovacao_rh": "i-aprovacao",
    "aprovacao_gestor": "i-checagem",
    "admitido": "i-aprovados",
}

# Mesmos 3 itens que o seed usa (seeds_demo.py::_TIPOS_DOCUMENTO) — repetido
# aqui de propósito (é uma constante privada lá, e os dois módulos podem
# evoluir com listas de documento diferentes um dia sem se atrapalharem).
TIPOS_DOCUMENTO: tuple[str, ...] = (
    "RG ou CNH", "Comprovante de residência", "Certificado de escolaridade",
)

# Lista histórica de cargos. A verdade agora é a tabela `lab_cargo`, uma
# por sandbox (o visitante cria e exclui nas configurações), semeada por
# `seeds_demo.CARGOS_PADRAO`. Mantida só para bancos antigos que ainda não
# tenham cargos semeados: `listar_cargos` cai nela nesse caso.
CARGOS_NOVA_CANDIDATURA: tuple[str, ...] = (
    "Analista de Recrutamento e Seleção",
    "Assistente Administrativo",
    "Analista Financeiro Júnior",
    "Designer Gráfico Pleno",
    "Desenvolvedor Front-end Pleno",
    "Analista de Marketing Digital",
    "Coordenador de Atendimento ao Cliente",
    "Analista de Suporte Técnico",
    "Assistente de Recursos Humanos",
    "Analista Contábil Júnior",
    "Social Media Pleno",
    "Recepcionista",
)

# SLA citado pela própria pesquisa de mercado (Gupy: "120min SLA para
# validar todos os documentos enviados") — usado como o texto padrão do
# chip "no prazo" (índigo), o mesmo vocabulário que um RH real reconhece.
SLA_PADRAO_MIN = 120
# Janela de urgência do chip (coral): vencido OU a menos de 48h do prazo.
URGENTE_LIMITE_HORAS = 48


def _sem_fuso_para_utc(quando: dt.datetime) -> dt.datetime:
    if quando.tzinfo is None:
        return quando.replace(tzinfo=dt.timezone.utc)
    return quando


def chip_prazo(prazo_em: dt.datetime | None, agora: dt.datetime | None = None) -> dict | None:
    """Devolve `{"texto", "classe", "urgente"}` para o chip de prazo do
    card, ou `None` quando o candidato não tem prazo (ex.: já admitido).

    `classe` é `"coral"` (urgente/vencido) ou `"indigo"` (no prazo) — o
    DIFERENCIAL DE MARCA do Admita: prazo/urgência visível por item
    pendente, recurso que a pesquisa não encontrou em nenhuma referência
    (Senior/LG/Convenia/Sólides/Gupy citam duração TOTAL do processo, nunca
    status por item pendente com prazo individual na tela)."""
    if prazo_em is None:
        return None
    agora = agora or dt.datetime.now(dt.timezone.utc)
    prazo_em = _sem_fuso_para_utc(prazo_em)
    delta_seg = (prazo_em - agora).total_seconds()

    if delta_seg <= 0:
        horas = int(abs(delta_seg) // 3600)
        if horas < 1:
            texto = "prazo estourado há minutos"
        elif horas < 24:
            texto = f"prazo estourado há {horas}h"
        else:
            dias = horas // 24
            texto = f"prazo estourado há {dias} dia{'s' if dias != 1 else ''}"
        return {"texto": texto, "classe": "coral", "urgente": True}

    horas_restantes = delta_seg / 3600
    if horas_restantes <= URGENTE_LIMITE_HORAS:
        if horas_restantes < 1:
            texto = "vence em minutos"
        elif horas_restantes < 24:
            texto = f"vence em {int(horas_restantes)}h"
        else:
            dias = int(horas_restantes // 24)
            texto = f"vence em {dias} dia{'s' if dias != 1 else ''}"
        return {"texto": texto, "classe": "coral", "urgente": True}

    return {
        "texto": f"no prazo · SLA {SLA_PADRAO_MIN}min",
        "classe": "indigo",
        "urgente": False,
    }


def iniciais(nome: str) -> str:
    partes = [p for p in nome.strip().split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _registrar(db: Session, sandbox: LabSandbox, quem: str, acao: str) -> None:
    db.add(LabAuditoria(sandbox_id=sandbox.id, origem="visitante", quem=quem, acao=acao[:200]))


# ------------------------------------------------------------- leitura ----

def montar_contexto(db: Session, sandbox: LabSandbox) -> dict:
    """Monta todo o dado que `_shell.html` (e a página cheia `esteira.html`)
    precisa: candidatos por etapa (com chip de prazo/iniciais já
    calculados), contagens, estado do sidebar e as últimas linhas da
    trilha de auditoria. Um ponto único, chamado tanto pelo GET da tela
    inteira quanto por TODA rota de mutação (mover, aprovar, checklist,
    criar candidato) — cada uma devolve o MESMO fragmento `_shell.html`
    recém calculado, nunca um pedaço parcialmente atualizado."""
    agora = dt.datetime.now(dt.timezone.utc)

    candidatos_todos = (
        db.query(LabCandidato)
        .filter(LabCandidato.sandbox_id == sandbox.id)
        .order_by(LabCandidato.criado_em.asc())
        .all()
    )

    por_etapa: dict[str, list[LabCandidato]] = {e: [] for e in ETAPAS}
    prazos_estourando = 0
    for i, candidato in enumerate(candidatos_todos):
        chip = chip_prazo(candidato.prazo_em, agora)
        candidato.chip_prazo = chip  # type: ignore[attr-defined]
        candidato.iniciais_nome = iniciais(candidato.nome)  # type: ignore[attr-defined]
        candidato.avatar_classe = "avatar-1" if i % 2 == 0 else "avatar-2"  # type: ignore[attr-defined]
        if chip is not None and chip["urgente"] and candidato.etapa != "admitido":
            prazos_estourando += 1
        por_etapa.setdefault(candidato.etapa, []).append(candidato)

    for candidato in por_etapa.get("documentos", []):
        docs = (
            db.query(LabDocumentoStatus)
            .filter(LabDocumentoStatus.candidato_id == candidato.id)
            .order_by(LabDocumentoStatus.id.asc())
            .all()
        )
        candidato.checklist = docs  # type: ignore[attr-defined]
        candidato.checklist_conferidos = sum(1 for d in docs if d.conferido)  # type: ignore[attr-defined]
        candidato.checklist_total = len(docs)  # type: ignore[attr-defined]

    # candidatos fora de "documentos" também podem ter checklist (ex.: já
    # passou dessa etapa) — usado só pelo painel de checklist sob demanda,
    # não pela contagem do card do kanban.
    for etapa in ETAPAS:
        if etapa == "documentos":
            continue
        for candidato in por_etapa.get(etapa, []):
            docs = (
                db.query(LabDocumentoStatus)
                .filter(LabDocumentoStatus.candidato_id == candidato.id)
                .order_by(LabDocumentoStatus.id.asc())
                .all()
            )
            candidato.checklist = docs  # type: ignore[attr-defined]
            candidato.checklist_conferidos = sum(1 for d in docs if d.conferido)  # type: ignore[attr-defined]
            candidato.checklist_total = len(docs)  # type: ignore[attr-defined]

    documentos_pendentes = (
        db.query(LabDocumentoStatus)
        .join(LabCandidato, LabDocumentoStatus.candidato_id == LabCandidato.id)
        .filter(LabCandidato.sandbox_id == sandbox.id, LabDocumentoStatus.conferido.is_(False))
        .count()
    )

    # ------------------------------------------------------------- agenda --
    # Lista única para o painel de entrevistas: TODO candidato aparece, com
    # ou sem data. Quem já tem entrevista vem primeiro, em ordem de data;
    # quem não tem vem depois, em ordem de esteira. O calendário do painel é
    # montado no navegador a partir destes mesmos dados (admita.js), então a
    # data vai formatada de duas maneiras: ISO para a máquina comparar e
    # texto curto para a pessoa ler.
    agenda = []
    for candidato in candidatos_todos:
        quando = candidato.entrevista_em
        if quando is not None and quando.tzinfo is None:
            quando = quando.replace(tzinfo=dt.timezone.utc)
        agenda.append({
            "id": candidato.id,
            "nome": candidato.nome,
            "cargo": candidato.cargo,
            "iniciais": iniciais(candidato.nome),
            "etapa": ETAPA_LABEL.get(candidato.etapa, candidato.etapa),
            "avatar_classe": getattr(candidato, "avatar_classe", "avatar-1"),
            "iso": quando.date().isoformat() if quando else "",
            "legivel": _data_legivel(quando) if quando else "",
            "passou": bool(quando and quando.date() < agora.date()),
        })
    agenda.sort(key=lambda item: (item["iso"] == "", item["iso"]))
    entrevistas_marcadas = sum(1 for item in agenda if item["iso"])

    # "Prontos para folha": admitidos com o checklist inteiro conferido. É o
    # recorte que interessa a quem faz fechamento de folha, e é diferente da
    # contagem da etapa "Admitido" (que inclui quem ainda tem documento em
    # aberto). Antes a sidebar repetia a etapa, o que não informava nada.
    prontos_folha = 0
    for candidato in por_etapa.get("admitido", []):
        docs = (
            db.query(LabDocumentoStatus)
            .filter(LabDocumentoStatus.candidato_id == candidato.id)
            .all()
        )
        if docs and all(d.conferido for d in docs):
            prontos_folha += 1

    auditoria_total = (
        db.query(LabAuditoria).filter(LabAuditoria.sandbox_id == sandbox.id).count()
    )
    auditoria_recente = (
        db.query(LabAuditoria)
        .filter(LabAuditoria.sandbox_id == sandbox.id)
        .order_by(LabAuditoria.quando.desc())
        .limit(8)
        .all()
    )

    total_ativos = sum(len(por_etapa[e]) for e in ETAPAS if e != "admitido")

    return {
        "etapas": ETAPAS,
        "etapa_label": ETAPA_LABEL,
        "etapa_icone": ETAPA_ICONE,
        "candidatos": por_etapa,
        "contagens": {e: len(por_etapa[e]) for e in ETAPAS},
        "total_ativos": total_ativos,
        "sidebar": {
            "documentos_pendentes": documentos_pendentes,
            "aguardando_gestor": len(por_etapa["aprovacao_gestor"]),
            "prazos_estourando": prazos_estourando,
            "prontos_folha": prontos_folha,
        },
        "agenda": agenda,
        "entrevistas_marcadas": entrevistas_marcadas,
        "hoje_iso": agora.date().isoformat(),
        "auditoria": auditoria_recente,
        "auditoria_total": auditoria_total,
        "auditoria_mais": max(0, auditoria_total - len(auditoria_recente)),
        "cargos": listar_cargos(db, sandbox),
        "empresa_rh": EMPRESA_RH,
        "empresa_rh_nota": EMPRESA_RH_NOTA,
        "usuario_rh": USUARIO_RH,
        "usuario_rh_perfil": USUARIO_RH_PERFIL,
        "usuario_rh_email": USUARIO_RH_EMAIL,
        "max_registros": 10,
        "registros_usados": (
            db.query(LabCandidato)
            .filter(LabCandidato.sandbox_id == sandbox.id, LabCandidato.origem == "visitante")
            .count()
        ),
    }


# -------------------------------------------------------------- cargos ----
# O dropdown de nova candidatura sai daqui, e o visitante manda nele: pode
# criar, renomear e excluir. Três cuidados que a tela não pode terceirizar:
# o texto passa pelo validador (§9.2), o nome é único por sandbox (senão o
# dropdown vira uma lista de repetidos), e excluir um cargo NUNCA mexe no
# `cargo` de quem já foi cadastrado com ele, porque isso seria reescrever
# a ficha de um candidato.

MAX_CARGOS = 24
MAX_CARGO_CHARS = 80


def listar_cargos(db: Session, sandbox: LabSandbox) -> list[LabCargo]:
    cargos = (
        db.query(LabCargo)
        .filter(LabCargo.sandbox_id == sandbox.id)
        .order_by(LabCargo.ordem.asc(), LabCargo.id.asc())
        .all()
    )
    if cargos:
        return cargos
    # sandbox criado antes desta tabela existir: semeia agora, uma vez, em
    # vez de devolver um dropdown vazio na cara de quem abriu a demo
    for ordem, nome in enumerate(CARGOS_NOVA_CANDIDATURA):
        db.add(LabCargo(sandbox_id=sandbox.id, origem="seed", nome=nome, ordem=ordem))
    db.commit()
    return (
        db.query(LabCargo)
        .filter(LabCargo.sandbox_id == sandbox.id)
        .order_by(LabCargo.ordem.asc(), LabCargo.id.asc())
        .all()
    )


def _cargo_da_sandbox(db: Session, sandbox: LabSandbox, cargo_id: int) -> LabCargo:
    cargo = (
        db.query(LabCargo)
        .filter(LabCargo.id == cargo_id, LabCargo.sandbox_id == sandbox.id)
        .first()
    )
    if cargo is None:
        raise ValueError("Cargo não encontrado nesta demonstração.")
    return cargo


def _nome_de_cargo(texto: str) -> str:
    nome = validar_texto(texto, MAX_CARGO_CHARS).strip()
    if len(nome) < 2:
        raise ValueError("Escreva o nome do cargo.")
    return nome


def _cargo_repetido(db, sandbox, nome: str, ignorar_id: int | None = None) -> bool:
    consulta = db.query(LabCargo).filter(
        LabCargo.sandbox_id == sandbox.id,
        LabCargo.nome == nome,
    )
    if ignorar_id is not None:
        consulta = consulta.filter(LabCargo.id != ignorar_id)
    return consulta.first() is not None


def criar_cargo(db: Session, sandbox: LabSandbox, texto: str) -> LabCargo:
    nome = _nome_de_cargo(texto)
    if _cargo_repetido(db, sandbox, nome):
        raise ValueError("Esse cargo já está na lista.")
    quantos = db.query(LabCargo).filter(LabCargo.sandbox_id == sandbox.id).count()
    if quantos >= MAX_CARGOS:
        raise ValueError(
            f"A lista chegou a {MAX_CARGOS} cargos nesta demonstração. "
            "Exclua um para incluir outro."
        )
    ordem = (
        db.query(LabCargo)
        .filter(LabCargo.sandbox_id == sandbox.id)
        .order_by(LabCargo.ordem.desc())
        .first()
    )
    cargo = LabCargo(
        sandbox_id=sandbox.id,
        origem="visitante",
        nome=nome,
        ordem=(ordem.ordem + 1) if ordem else 0,
    )
    db.add(cargo)
    _registrar(db, sandbox, "Você", f"criou o cargo {nome}"[:200])
    db.commit()
    return cargo


def renomear_cargo(db: Session, sandbox: LabSandbox, cargo_id: int, texto: str) -> LabCargo:
    cargo = _cargo_da_sandbox(db, sandbox, cargo_id)
    nome = _nome_de_cargo(texto)
    if nome == cargo.nome:
        return cargo
    if _cargo_repetido(db, sandbox, nome, ignorar_id=cargo.id):
        raise ValueError("Esse cargo já está na lista.")
    antigo = cargo.nome
    cargo.nome = nome
    _registrar(db, sandbox, "Você", f"renomeou o cargo {antigo} para {nome}"[:200])
    db.commit()
    return cargo


def excluir_cargo(db: Session, sandbox: LabSandbox, cargo_id: int) -> None:
    cargo = _cargo_da_sandbox(db, sandbox, cargo_id)
    quantos = db.query(LabCargo).filter(LabCargo.sandbox_id == sandbox.id).count()
    if quantos <= 1:
        raise ValueError("Deixe pelo menos um cargo na lista.")
    nome = cargo.nome
    # de propósito: quem já foi cadastrado com este cargo continua com ele,
    # porque a ficha do candidato registra o que valia no dia
    db.delete(cargo)
    _registrar(db, sandbox, "Você", f"excluiu o cargo {nome}"[:200])
    db.commit()


# ------------------------------------------------------------- escrita ----

def _candidato_da_sandbox(db: Session, sandbox: LabSandbox, candidato_id: int) -> LabCandidato:
    candidato = (
        db.query(LabCandidato)
        .filter(LabCandidato.id == candidato_id, LabCandidato.sandbox_id == sandbox.id)
        .one_or_none()
    )
    if candidato is None:
        raise ValueError("Candidato não encontrado nesta demonstração.")
    return candidato


def criar_candidato(db: Session, sandbox: LabSandbox, nome: str, cargo: str) -> LabCandidato:
    """Cria um candidato novo a partir do modal "Nova candidatura"
    (origem="visitante", §8/§9.3). `cargo` só aceita um valor da lista de
    cargos DESTE sandbox (dropdown, nunca texto livre): a lista virou dado,
    porque o visitante pode criar e excluir cargos nas configurações."""
    nome = validar_texto(nome.strip(), MAX_CAMPO)
    if not nome:
        raise ValueError("Informe o nome do candidato.")
    if cargo not in {c.nome for c in listar_cargos(db, sandbox)}:
        raise ValueError("Escolha um cargo válido na lista.")

    checar_limite_registros(db, sandbox, "rh")

    candidato = LabCandidato(
        sandbox_id=sandbox.id, origem="visitante",
        nome=nome, cargo=cargo, etapa="candidato",
        prazo_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=72),
    )
    db.add(candidato)
    db.flush()
    _registrar(
        db, sandbox, "Sistema",
        f"Candidatura de {nome} recebida para vaga na {EMPRESA_RH} {EMPRESA_RH_NOTA}.",
    )
    db.commit()
    return candidato


def mover_candidato(db: Session, sandbox: LabSandbox, candidato_id: int, direcao: str) -> LabCandidato:
    """Move um candidato uma etapa para frente ou para trás. Levanta
    `ValueError` (mensagem pronta para o visitante) quando a regra de
    negócio bloqueia o avanço (§6.1) ou quando já está na ponta da esteira
    — a MESMA mensagem que faz a seta "sumir/desabilitar" na primeira e na
    última etapa fazer sentido no lado do servidor também."""
    if direcao not in ("proxima", "anterior"):
        raise ValueError("Direção de movimento inválida.")

    candidato = _candidato_da_sandbox(db, sandbox, candidato_id)
    idx = ETAPAS.index(candidato.etapa)

    if direcao == "proxima":
        if idx >= len(ETAPAS) - 1:
            raise ValueError("Este candidato já está na última etapa da esteira.")
        if candidato.etapa == "documentos":
            docs = (
                db.query(LabDocumentoStatus)
                .filter(LabDocumentoStatus.candidato_id == candidato.id)
                .all()
            )
            if not docs or any(not d.conferido for d in docs):
                raise ValueError(
                    "Confira todos os documentos antes de avançar para a aprovação do RH."
                )
        elif candidato.etapa == "aprovacao_rh":
            if not candidato.aprovado_rh:
                raise ValueError(
                    "Aprove o RH antes de avançar este candidato para o gestor."
                )
        elif candidato.etapa == "aprovacao_gestor":
            if not candidato.aprovado_gestor:
                raise ValueError(
                    "Aprove o gestor antes de admitir este candidato."
                )
        nova_etapa = ETAPAS[idx + 1]
        candidato.etapa = nova_etapa
        if nova_etapa == "documentos":
            ja_tem = (
                db.query(LabDocumentoStatus)
                .filter(LabDocumentoStatus.candidato_id == candidato.id)
                .first()
            )
            if ja_tem is None:
                for tipo in TIPOS_DOCUMENTO:
                    db.add(LabDocumentoStatus(
                        sandbox_id=sandbox.id, origem="visitante",
                        candidato_id=candidato.id, tipo=tipo, conferido=False,
                    ))
                _registrar(
                    db, sandbox, "Sistema",
                    f"Documentos solicitados a {candidato.nome}: RG ou CNH, comprovante "
                    "de residência e certificado de escolaridade.",
                )
        _registrar(
            db, sandbox, "RH" if nova_etapa != "documentos" else "Sistema",
            f"Candidatura de {candidato.nome} avançou para {ETAPA_LABEL[nova_etapa]}.",
        )
    else:
        if idx <= 0:
            raise ValueError("Este candidato já está na primeira etapa da esteira.")
        nova_etapa = ETAPAS[idx - 1]
        candidato.etapa = nova_etapa
        _registrar(
            db, sandbox, "RH",
            f"Candidatura de {candidato.nome} devolvida para {ETAPA_LABEL[nova_etapa]}.",
        )

    db.commit()
    return candidato


def aprovar_rh(db: Session, sandbox: LabSandbox, candidato_id: int) -> LabCandidato:
    candidato = _candidato_da_sandbox(db, sandbox, candidato_id)
    if candidato.etapa != "aprovacao_rh":
        raise ValueError("Este candidato não está aguardando aprovação do RH.")
    docs = (
        db.query(LabDocumentoStatus)
        .filter(LabDocumentoStatus.candidato_id == candidato.id)
        .all()
    )
    if any(not d.conferido for d in docs):
        raise ValueError("Confira todos os documentos antes de aprovar pelo RH.")
    candidato.aprovado_rh = True
    candidato.etapa = "aprovacao_gestor"
    _registrar(
        db, sandbox, "RH",
        f"Aprovação do RH concedida para {candidato.nome}. Segue para aprovação do gestor.",
    )
    db.commit()
    return candidato


def aprovar_gestor(db: Session, sandbox: LabSandbox, candidato_id: int) -> LabCandidato:
    candidato = _candidato_da_sandbox(db, sandbox, candidato_id)
    if candidato.etapa != "aprovacao_gestor":
        raise ValueError("Este candidato não está aguardando aprovação do gestor.")
    if not candidato.aprovado_rh:
        raise ValueError("A aprovação do RH precisa vir antes da aprovação do gestor.")
    candidato.aprovado_gestor = True
    candidato.etapa = "admitido"
    _registrar(
        db, sandbox, "Gestor",
        f"Aprovação do gestor concedida para {candidato.nome}. Candidato admitido.",
    )
    db.commit()
    return candidato


def alternar_documento(db: Session, sandbox: LabSandbox, candidato_id: int, documento_id: int) -> LabCandidato:
    candidato = _candidato_da_sandbox(db, sandbox, candidato_id)
    documento = (
        db.query(LabDocumentoStatus)
        .filter(LabDocumentoStatus.id == documento_id, LabDocumentoStatus.candidato_id == candidato.id)
        .one_or_none()
    )
    if documento is None:
        raise ValueError("Documento não encontrado para este candidato.")
    documento.conferido = not documento.conferido
    estado = "conferido" if documento.conferido else "pendente"
    _registrar(
        db, sandbox, "RH",
        f"{documento.tipo} de {candidato.nome} marcado como {estado}.",
    )
    db.commit()
    return candidato


# ------------------------------------------------------------- agenda ----

_MES_CURTO = (
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
)

# Janela em que a entrevista pode cair. Passado não entra (marcar entrevista
# para ontem é erro de digitação, não intenção) e um ano à frente já é mais
# do que qualquer processo seletivo de verdade precisa.
DIAS_AGENDA_FUTURO = 365


def _data_legivel(quando: dt.datetime) -> str:
    return f"{quando.day} de {_MES_CURTO[quando.month - 1]}"


def agendar_entrevista(
    db: Session, sandbox: LabSandbox, candidato_id: int, data_iso: str
) -> LabCandidato:
    """Marca (ou remarca) a entrevista do candidato no dia `data_iso`.

    `data_iso` vazio DESMARCA. Qualquer outro valor precisa ser uma data
    ISO válida, de hoje em diante e dentro de um ano: o campo chega do
    navegador e o navegador não é autoridade sobre nada."""
    candidato = _candidato_da_sandbox(db, sandbox, candidato_id)

    if not (data_iso or "").strip():
        candidato.entrevista_em = None
        _registrar(db, sandbox, "Você", f"desmarcou a entrevista de {candidato.nome}"[:200])
        db.commit()
        return candidato

    try:
        dia = dt.date.fromisoformat(data_iso.strip())
    except ValueError:
        raise ValueError("Essa data não parece válida. Escolha um dia no calendário.")

    hoje = dt.datetime.now(dt.timezone.utc).date()
    if dia < hoje:
        raise ValueError("Entrevista só para hoje em diante.")
    if dia > hoje + dt.timedelta(days=DIAS_AGENDA_FUTURO):
        raise ValueError("Escolha uma data dentro do próximo ano.")

    candidato.entrevista_em = dt.datetime.combine(
        dia, dt.time(9, 0), tzinfo=dt.timezone.utc
    )
    _registrar(
        db, sandbox, "Você",
        f"marcou entrevista de {candidato.nome} para {_data_legivel(candidato.entrevista_em)}"[:200],
    )
    db.commit()
    return candidato
