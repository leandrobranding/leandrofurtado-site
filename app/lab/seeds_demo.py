"""Seeds dos três cenários fictícios do Lab de Demos (Task 6 do Plano 1 —
§6/§9.9 da spec).

`semear_cenario(db, sandbox)` povoa, de uma vez só, os três sistemas que o
MESMO sandbox serve (RH, Financeiro, Escola) — o visitante nunca abre uma
tela vazia ("textos ricos o bastante para as telas do Plano 2 nunca
nascerem vazias", brief da Task 6). É chamada uma única vez, na criação do
sandbox (`app/lab/sandbox.py::_criar_sandbox`), substituindo o stub da
Task 2.

IDEMPOTÊNCIA: se o sandbox já tem algum `LabCandidato` com `origem="seed"`,
a função retorna sem inserir nada de novo — chamar duas vezes no mesmo
sandbox não duplica. `LabCandidato` é escolhido como sentinela por ser
sempre a primeira tabela povoada aqui, mas os três cenários nascem sempre
juntos (mesma chamada), então checar só ele já garante o cenário inteiro.

ORIGEM (ruling da revisão da Task 3 — ver `app/lab/models.py`): TODO
registro que este módulo grava carrega `origem="seed"` (`LabParecer` usa o
nome `origem_registro`, porque `origem` já significa 'ia'/'fallback'
naquela tabela desde a Task 1). Sem isso, o cenário fictício consumiria o
teto de `MAX_REGISTROS_POR_DEMO` (§8) que existe para limitar o que o
VISITANTE cria — `checar_limite_registros` (`app/lab/protecao.py`) já
filtra por `origem == "visitante"`, então os 10 slots de cada demo
continuam inteiros para quem visita.

FICTÍCIO VISÍVEL (§9.9): nomes neutros e diversos, e-mails
`@exemplo.com.br`, empresa "Admita Studio RH (empresa fictícia)" no RH e
clientes com razão social claramente fictícia no Financeiro, e todo
documento (CPF/CNPJ) com o SEGUNDO dígito verificador ERRADO DE PROPÓSITO —
ver `_dv_modulo11`/`_cpf_ficticio`/`_cnpj_ficticio` abaixo: o algoritmo
oficial roda CORRETO até o fim e só depois o segundo dígito é deslocado em
+1 (mod 10). Isso garante duas coisas ao mesmo tempo: (1) o documento nunca
passa numa validação de dígito verificador de verdade — é inválido por
construção, não por acidente; (2) por sair de um cálculo real deslocado (e
não de dígitos aleatórios), nunca colide por acaso com um CPF/CNPJ válido
de alguém de verdade.

Nenhum símbolo textual é usado nos dados semeados (regra anti-emoji do
site) — só letras, números e pontuação comum (vírgula, ponto, travessão,
parênteses); não há necessidade de `&#xFE0E;` porque nenhum caractere com
apresentação emoji aparece em nenhum campo abaixo.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from .models import (
    LabAluno,
    LabAuditoria,
    LabAvaliacao,
    LabCandidato,
    LabCargo,
    LabClienteFiscal,
    LabDocumentoStatus,
    LabLancamento,
    LabNota,
    LabParecer,
)

EMPRESA_RH = "Admita Studio RH"
EMPRESA_RH_NOTA = "(empresa fictícia)"
# Quem a demonstração finge que está com a sessão aberta. Mesma pessoa
# que aparece na lista de acessos do painel de configurações.
USUARIO_RH = "Usuário Teste"
USUARIO_RH_PERFIL = "Coordenação de RH"
USUARIO_RH_EMAIL = "teste@leandrofurtado.com.br"
TURMA_ESCOLA = "3º B (fictícia)"


def _agora() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# --------------------------------------------------- documentos fictícios --

def _dv_modulo11(digitos: list[int], pesos) -> int:
    """Dígito verificador módulo 11 — mesmo algoritmo oficial de CPF/CNPJ.
    `pesos` é iterável (range ou lista) do mesmo tamanho de `digitos`."""
    soma = sum(d * p for d, p in zip(digitos, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def _cpf_ficticio(nove_digitos: str) -> str:
    """CPF fictício por design (§9.9): dígitos verificadores calculados
    CORRETAMENTE pelo algoritmo oficial e só então o segundo é deslocado em
    +1 (mod 10) — inválido de propósito, documentado, nunca um CPF real."""
    digitos = [int(c) for c in nove_digitos]
    dv1 = _dv_modulo11(digitos, range(10, 1, -1))
    dv2_correto = _dv_modulo11(digitos + [dv1], range(11, 1, -1))
    dv2_errado = (dv2_correto + 1) % 10
    return f"{nove_digitos[0:3]}.{nove_digitos[3:6]}.{nove_digitos[6:9]}-{dv1}{dv2_errado}"


def _cnpj_ficticio(doze_digitos: str) -> str:
    """CNPJ fictício por design — mesma ideia de `_cpf_ficticio` acima, com
    os pesos oficiais do algoritmo de CNPJ."""
    digitos = [int(c) for c in doze_digitos]
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    dv1 = _dv_modulo11(digitos, pesos1)
    dv2_correto = _dv_modulo11(digitos + [dv1], pesos2)
    dv2_errado = (dv2_correto + 1) % 10
    d = doze_digitos
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{dv1}{dv2_errado}"


# ------------------------------------------------------------------- RH ---
# Esteira: candidato -> documentos -> aprovacao_rh -> aprovacao_gestor ->
# admitido (§6.1). Os 6 candidatos cobrem, de propósito: alguém travado em
# Documentos por pendência, alguém aguardando o gestor já com o aval do RH,
# alguém admitido, alguém recém-chegado (esteira ainda não começou), e um
# prazo ESTOURADO (SLA) ao lado de prazos no prazo — o diferencial de
# compliance/SLA que a trilha de auditoria existe para provar (§6.1).

_TIPOS_DOCUMENTO = ("RG ou CNH", "Comprovante de residência", "Certificado de escolaridade")


CARGOS_PADRAO = (
    "Analista de Recrutamento e Seleção Pleno",
    "Analista de Dados Pleno",
    "Analista de Marketing de Performance",
    "Assistente Financeiro Júnior",
    "Coordenador de Operações",
    "Designer de Produto Pleno",
    "Analista de Suporte Júnior",
    "Especialista em Departamento Pessoal",
    "Gerente de Contas Sênior",
    "Estagiário de Comunicação",
    "Técnico de Segurança do Trabalho",
    "Auxiliar Administrativo",
)


def _semear_cargos(db: Session, sandbox_id: int) -> None:
    """Cargos que nascem no dropdown. O visitante pode renomear e excluir,
    então eles precisam existir como linha, não como constante no código."""
    for ordem, nome in enumerate(CARGOS_PADRAO):
        db.add(LabCargo(sandbox_id=sandbox_id, origem="seed", nome=nome, ordem=ordem))


def _semear_rh(db: Session, sandbox_id: int) -> None:
    agora = _agora()
    _semear_cargos(db, sandbox_id)

    candidatos = [
        LabCandidato(
            sandbox_id=sandbox_id, origem="seed",
            nome="Adriana Souza Lima",
            cargo="Analista de Recrutamento e Seleção Pleno",
            etapa="documentos", aprovado_rh=False, aprovado_gestor=False,
            curriculo=(
                "Seis anos de experiência em recrutamento e seleção para empresas de médio "
                "porte, com atuação tanto em processos de volume quanto em posições "
                "especializadas. Liderou a implantação de um funil de triagem estruturado que "
                "reduziu o tempo médio de contratação em cerca de um terço. Formação em "
                "Psicologia, com pós-graduação em Gestão de Pessoas (perfil fictício, gerado "
                "para demonstração)."
            ),
            score_ia=None, justificativa_ia="", origem_ia="",
            prazo_em=agora + dt.timedelta(hours=72),
            entrevista_em=agora + dt.timedelta(days=2, hours=3),
        ),
        LabCandidato(
            sandbox_id=sandbox_id, origem="seed",
            nome="Bruno Andrade Costa",
            cargo="Coordenador de Operações",
            etapa="aprovacao_gestor", aprovado_rh=True, aprovado_gestor=False,
            curriculo=(
                "Nove anos coordenando times operacionais em empresas de serviços, com foco em "
                "padronização de processos e redução de retrabalho. Já reportou diretamente a "
                "diretoria em ciclos de revisão trimestral de indicadores. Certificação em "
                "gestão de projetos e vivência prévia como analista antes de assumir a "
                "coordenação (perfil fictício, gerado para demonstração)."
            ),
            score_ia=8, justificativa_ia=(
                "Aderência forte ao cargo: trajetória de crescimento consistente na área e "
                "experiência direta com o tipo de rotina que a vaga exige."
            ), origem_ia="fallback",
            prazo_em=agora + dt.timedelta(hours=20),
            entrevista_em=agora + dt.timedelta(days=1, hours=5),
        ),
        LabCandidato(
            sandbox_id=sandbox_id, origem="seed",
            nome="Camila Ferreira Dias",
            cargo="Designer de Produto Pleno",
            etapa="admitido", aprovado_rh=True, aprovado_gestor=True,
            curriculo=(
                "Cinco anos desenhando produtos digitais de ponta a ponta, de pesquisa com "
                "usuário a especificação de interface, em times multidisciplinares pequenos. "
                "Portfólio com estudos de caso publicados e participação ativa em crítica de "
                "design entre pares (perfil fictício, gerado para demonstração)."
            ),
            score_ia=9, justificativa_ia=(
                "Portfólio consistente e processo de trabalho bem documentado, com aderência alta "
                "ao nível pleno da vaga."
            ), origem_ia="fallback",
            prazo_em=None,
        ),
        LabCandidato(
            sandbox_id=sandbox_id, origem="seed",
            nome="Diego Martins Rocha",
            cargo="Assistente Financeiro Júnior",
            etapa="candidato", aprovado_rh=False, aprovado_gestor=False,
            curriculo=(
                "Recém-formado em Ciências Contábeis, com estágio de dois anos em rotina "
                "financeira: conciliação bancária, apoio a fechamento mensal e emissão de "
                "relatórios simples. Busca a primeira posição efetiva na área (perfil "
                "fictício, gerado para demonstração)."
            ),
            score_ia=None, justificativa_ia="", origem_ia="",
            prazo_em=agora + dt.timedelta(hours=120),
        ),
        LabCandidato(
            sandbox_id=sandbox_id, origem="seed",
            nome="Elisa Tavares Nogueira",
            cargo="Analista de Dados Pleno",
            etapa="aprovacao_rh", aprovado_rh=False, aprovado_gestor=False,
            curriculo=(
                "Quatro anos como analista de dados em empresas de varejo, construindo "
                "painéis de indicadores e automatizando relatórios antes feitos manualmente em "
                "planilha. Já apresentou resultados de análise diretamente a lideranças de "
                "área (perfil fictício, gerado para demonstração)."
            ),
            score_ia=7, justificativa_ia=(
                "Boa base técnica e experiência prática relevante; documentação enviada está "
                "completa, falta apenas a decisão do RH."
            ), origem_ia="fallback",
            # ESTOURADO de propósito: prazo já vencido, candidata ainda parada
            # em "aprovacao_rh" — o diferencial de SLA que a esteira expõe.
            prazo_em=agora - dt.timedelta(hours=30),
            entrevista_em=agora + dt.timedelta(days=6, hours=2),
        ),
        LabCandidato(
            sandbox_id=sandbox_id, origem="seed",
            nome="Felipe Nakashima Alves",
            cargo="Analista de Marketing de Performance",
            etapa="documentos", aprovado_rh=False, aprovado_gestor=False,
            curriculo=(
                "Três anos em marketing de performance, gerindo campanhas em múltiplos canais "
                "com foco em custo de aquisição. Acompanhou de perto a migração de um cliente "
                "de planilhas manuais para um painel de métricas automatizado (perfil "
                "fictício, gerado para demonstração)."
            ),
            score_ia=6, justificativa_ia=(
                "Experiência relevante para o cargo, ainda em fase de conferência documental."
            ), origem_ia="fallback",
            prazo_em=agora + dt.timedelta(hours=48),
        ),
    ]
    db.add_all(candidatos)
    db.flush()  # popula candidatos[i].id para os documentos abaixo

    adriana, bruno, camila, diego, elisa, felipe = candidatos

    documentos: list[LabDocumentoStatus] = []

    def _checklist(candidato: LabCandidato, pendencias: set[str]) -> None:
        for tipo in _TIPOS_DOCUMENTO:
            documentos.append(LabDocumentoStatus(
                sandbox_id=sandbox_id, origem="seed",
                candidato_id=candidato.id, tipo=tipo,
                conferido=tipo not in pendencias,
            ))

    # Adriana: travada em Documentos — falta o certificado de escolaridade.
    _checklist(adriana, {"Certificado de escolaridade"})
    # Bruno: RH já deu aval, documentos todos conferidos, aguarda o gestor.
    _checklist(bruno, set())
    # Camila: processo concluído, tudo conferido.
    _checklist(camila, set())
    # Diego: esteira ainda não chegou em Documentos — checklist nem existe.
    # Elisa: documentos ok, aguardando só a decisão do RH (prazo estourado).
    _checklist(elisa, set())
    # Felipe: também travado em Documentos, pendência num item diferente de
    # Adriana — mostra que a trava vale para qualquer item do checklist.
    _checklist(felipe, {"Comprovante de residência"})

    db.add_all(documentos)

    auditoria = [
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="Sistema",
            acao=f"Candidatura de Diego Martins Rocha recebida para vaga na {EMPRESA_RH} {EMPRESA_RH_NOTA}.",
            quando=agora - dt.timedelta(hours=96),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="RH",
            acao="Documentos de Adriana Souza Lima conferidos: RG ou CNH e comprovante de "
                 "residência aprovados.",
            quando=agora - dt.timedelta(hours=50),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="RH",
            acao="Pendência sinalizada para Adriana Souza Lima: certificado de escolaridade "
                 "ainda não enviado.",
            quando=agora - dt.timedelta(hours=49),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="RH",
            acao="Aprovação do RH concedida para Bruno Andrade Costa.",
            quando=agora - dt.timedelta(hours=40),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="Sistema",
            acao="Candidatura de Bruno Andrade Costa avançou para aprovação do gestor.",
            quando=agora - dt.timedelta(hours=40),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="Gestor",
            acao="Aprovação do gestor concedida para Camila Ferreira Dias, candidata "
                 "admitida.",
            quando=agora - dt.timedelta(hours=30),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="RH",
            acao="Todos os documentos de Elisa Tavares Nogueira conferidos, processo "
                 "aguardando decisão do RH.",
            quando=agora - dt.timedelta(hours=31),
        ),
        LabAuditoria(
            sandbox_id=sandbox_id, origem="seed", quem="Sistema",
            acao="Prazo de decisão do RH estourado para Elisa Tavares Nogueira: candidata "
                 "aguardando há mais tempo que o previsto.",
            quando=agora - dt.timedelta(hours=6),
        ),
    ]
    db.add_all(auditoria)


# --------------------------------------------------------- Financeiro ----
# 4 clientes fiscais, 6 notas numeradas 1-6 (uma cancelada, para exercitar o
# status), 12 lançamentos cobrindo as 7 categorias fechadas de
# `ia_fallbacks.CATEGORIAS_FECHADAS` (§6.2). Contrato JSON de `itens`/
# `impostos` é o definido na Task 5 (`app/lab/pdf.py`): itens = [{descricao,
# quantidade, valor_unit_centavos}], impostos = {categoria: valor_centavos}.
# `total_centavos` aqui é o subtotal dos itens — o ISS simulado é tratado
# como retenção (já embutida no preço do serviço, prática comum de nota de
# serviço no Brasil), não somado por cima; é só informativo na tela.

def _semear_financeiro(db: Session, sandbox_id: int) -> None:
    agora = _agora()

    clientes = [
        LabClienteFiscal(
            sandbox_id=sandbox_id, origem="seed",
            nome="Estúdio Aurora Design Ltda (cliente fictício)",
            documento=_cnpj_ficticio("123456780001"),
            email="financeiro.aurora@exemplo.com.br",
        ),
        LabClienteFiscal(
            sandbox_id=sandbox_id, origem="seed",
            nome="Comércio Nordeste Distribuidora Eireli (cliente fictício)",
            documento=_cnpj_ficticio("234567890001"),
            email="contas.nordeste@exemplo.com.br",
        ),
        LabClienteFiscal(
            sandbox_id=sandbox_id, origem="seed",
            nome="Consultoria Vetor Estratégico Ltda (cliente fictício)",
            documento=_cnpj_ficticio("345678900001"),
            email="fiscal.vetor@exemplo.com.br",
        ),
        LabClienteFiscal(
            sandbox_id=sandbox_id, origem="seed",
            nome="Mercado Search Digital Ltda (cliente fictício)",
            documento=_cnpj_ficticio("456789010001"),
            email="pagamentos.mercadosearch@exemplo.com.br",
        ),
    ]
    db.add_all(clientes)
    db.flush()  # popula clientes[i].id

    aurora, nordeste, vetor, mercado_search = clientes

    def _item(descricao: str, quantidade, valor_unit_centavos: int) -> dict:
        return {"descricao": descricao, "quantidade": quantidade,
                "valor_unit_centavos": valor_unit_centavos}

    def _subtotal(itens: list[dict]) -> int:
        return sum(round(float(i["quantidade"]) * i["valor_unit_centavos"]) for i in itens)

    def _iss(subtotal: int) -> dict:
        return {"iss_simulado_5_por_cento": round(subtotal * 0.05)}

    notas_dados = [
        (aurora, [_item("Consultoria de branding, pacote mensal", 1, 350000)], "emitida", 5),
        (nordeste, [_item("Desenvolvimento de identidade visual", 1, 480000)], "emitida", 4),
        (vetor, [_item("Consultoria estratégica, sessão avulsa", 4, 60000)], "emitida", 3),
        (mercado_search, [
            _item("Gestão de tráfego pago, mensalidade", 1, 220000),
            _item("Relatório de performance mensal", 1, 30000),
        ], "emitida", 2),
        (aurora, [_item("Sessão de fotos institucional", 1, 180000)], "cancelada", 1),
        (nordeste, [
            _item("Manutenção de identidade visual, pacote trimestral", 1, 90000),
            _item("Peça publicitária adicional", 2, 15000),
        ], "emitida", 0),
    ]

    notas: list[LabNota] = []
    for numero, (cliente, itens, status, dias_atras) in enumerate(notas_dados, start=1):
        subtotal = _subtotal(itens)
        notas.append(LabNota(
            sandbox_id=sandbox_id, origem="seed",
            cliente_id=cliente.id, numero=numero,
            itens=itens, impostos=_iss(subtotal),
            total_centavos=subtotal, status=status,
            criado_em=agora - dt.timedelta(days=dias_atras),
        ))
    db.add_all(notas)

    lancamentos_dados = [
        ("Recebimento de cliente, projeto de identidade visual", 550000,
         "receita_de_servico",
         "Entrada compatível com pagamento de serviço prestado, valor positivo e descrição de cliente."),
        ("Recebimento de cliente, consultoria estratégica mensal", 350000,
         "receita_de_servico",
         "Entrada recorrente ligada a contrato de prestação de serviço em vigor."),
        ("Recebimento de cliente, gestão de tráfego pago", 220000,
         "receita_de_servico",
         "Pagamento de cliente por serviço de mídia paga prestado no período."),
        ("DARF do Simples Nacional", -45000,
         "imposto_e_taxas",
         "Guia de recolhimento de tributo federal, enquadra-se diretamente como imposto."),
        ("ISS retido na fonte sobre serviço prestado", -18000,
         "imposto_e_taxas",
         "Retenção de imposto municipal sobre serviço, categoria tributária por definição."),
        ("Assinatura de ferramentas de design e produtividade", -29000,
         "despesa_operacional",
         "Ferramenta usada na operação do negócio, despesa recorrente necessária à atividade."),
        ("Aluguel do escritório", -180000,
         "despesa_operacional",
         "Custo fixo necessário à operação do negócio, sem relação com tributo ou pessoal."),
        ("Transferência entre contas da empresa", -100000,
         "transferencia_entre_contas",
         "Movimentação entre contas do próprio titular, sem efeito de receita ou despesa."),
        ("Folha de pagamento da quinzena", -420000,
         "despesa_com_pessoal",
         "Pagamento a colaboradores, enquadra-se diretamente em despesa de pessoal."),
        ("Pró-labore dos sócios", -300000,
         "despesa_com_pessoal",
         "Remuneração de sócios pelo trabalho na empresa, tratada como despesa de pessoal."),
        ("Tarifa bancária mensal de manutenção de conta", -3900,
         "despesa_financeira",
         "Cobrança do banco pela manutenção da conta, típica despesa financeira."),
        ("Estorno de tarifa cobrada indevidamente", 3900,
         "outros",
         "Ajuste que não se encaixa nas demais categorias fechadas, lançamento administrativo."),
    ]
    lancamentos = [
        LabLancamento(
            sandbox_id=sandbox_id, origem="seed",
            descricao=descricao, valor_centavos=valor, categoria=categoria,
            justificativa_ia=justificativa, origem_ia="fallback",
            criado_em=agora - dt.timedelta(days=(12 - i)),
        )
        for i, (descricao, valor, categoria, justificativa) in enumerate(lancamentos_dados)
    ]
    db.add_all(lancamentos)


# -------------------------------------------------------------- Escola ----
# Turma "3º B (fictícia)", 8 alunos x 4 disciplinas reais, 1 bimestre.
# Notas/faltas calculadas para que as três situações (aprovado, recuperação,
# reprovado) existam de fato — regra usada aqui SÓ para montar o seed
# (documentada, local a este módulo; a regra "canônica" de exibição é do
# Plano 2/telas, que pode recalcular): média simples das 4 disciplinas
# (aprovado >= 6, recuperação entre 4 e 6, reprovado < 4) E reprovação por
# falta acima de 20 no total do bimestre, mesmo com média de aprovação —
# a mecânica "por média E frequência" do §6.3.

_DISCIPLINAS = ("Matemática", "Língua Portuguesa", "Ciências", "História")


def _semear_escola(db: Session, sandbox_id: int) -> None:
    agora = _agora()

    # nome -> [(nota, faltas) por disciplina, na ordem de _DISCIPLINAS]
    alunos_dados = [
        ("Ana Beatriz Souza", [(8.5, 1), (9.0, 0), (8.0, 2), (8.5, 1)]),      # aprovada
        ("Bruno Henrique Lima", [(7.5, 3), (8.0, 2), (7.0, 3), (8.5, 2)]),    # aprovado
        ("Carla Eduarda Martins", [(5.0, 4), (6.5, 3), (4.5, 5), (5.5, 4)]),  # recuperação
        ("Daniel Costa Pereira", [(4.0, 4), (5.0, 4), (4.5, 4), (5.0, 4)]),   # recuperação
        ("Eduarda Ramos Silva", [(3.0, 5), (3.5, 4), (2.5, 6), (3.0, 5)]),    # reprovada por nota
        ("Fábio Augusto Teixeira", [(7.0, 7), (7.5, 7), (6.5, 6), (7.0, 6)]), # reprovado por falta (média>=6)
        ("Gabriela Nunes Rocha", [(7.5, 2), (8.0, 1), (7.0, 3), (7.5, 2)]),   # aprovada
        ("Henrique Vinícius Alves", [(3.5, 3), (4.0, 2), (3.0, 4), (3.5, 3)]),# reprovado por nota
    ]

    alunos = [
        LabAluno(sandbox_id=sandbox_id, origem="seed", nome=nome, turma=TURMA_ESCOLA)
        for nome, _notas in alunos_dados
    ]
    db.add_all(alunos)
    db.flush()  # popula alunos[i].id

    avaliacoes: list[LabAvaliacao] = []
    situacoes: dict[int, str] = {}
    for aluno, (_nome, notas_faltas) in zip(alunos, alunos_dados):
        faltas_totais = 0
        soma_notas = 0.0
        for disciplina, (nota, faltas) in zip(_DISCIPLINAS, notas_faltas):
            avaliacoes.append(LabAvaliacao(
                sandbox_id=sandbox_id, origem="seed",
                aluno_id=aluno.id, disciplina=disciplina,
                nota=nota, faltas=faltas, bimestre=1,
            ))
            soma_notas += nota
            faltas_totais += faltas
        media = soma_notas / len(notas_faltas)
        if faltas_totais > 20:
            situacao = "reprovado"
        elif media >= 6:
            situacao = "aprovado"
        elif media >= 4:
            situacao = "recuperacao"
        else:
            situacao = "reprovado"
        situacoes[aluno.id] = situacao
    db.add_all(avaliacoes)

    # 2 pareceres pré-existentes (§ Task 6): origem 'fallback' — como se o
    # visitante já tivesse gerado o parecer pedagógico antes de chegar, um
    # aluno aprovado e um reprovado, para a tela do boletim nunca abrir
    # vazia mesmo antes de qualquer clique.
    ana = alunos[0]
    eduarda = alunos[4]
    pareceres = [
        LabParecer(
            sandbox_id=sandbox_id, aluno_id=ana.id,
            texto_ia=(
                "Ana Beatriz encerra o bimestre aprovada, com participação ativa nas aulas e "
                "entrega pontual das atividades propostas em todas as disciplinas. A "
                "frequência é regular e as notas se mantêm consistentes ao longo do período. "
                "Recomenda-se manter o ritmo de estudos atual, aproveitando o bom desempenho "
                "já demonstrado como base para os próximos desafios."
            ),
            origem="fallback", origem_registro="seed",
            criado_em=agora - dt.timedelta(days=2),
        ),
        LabParecer(
            sandbox_id=sandbox_id, aluno_id=eduarda.id,
            texto_ia=(
                "Eduarda encerra o bimestre reprovada, com notas abaixo do esperado na maior "
                "parte das disciplinas. O quadro pede um plano de recuperação estruturado, com "
                "reforço direcionado nos conteúdos de maior dificuldade e conversa com a "
                "família antes do próximo ciclo, para reorganizar o acompanhamento pedagógico "
                "da aluna."
            ),
            origem="fallback", origem_registro="seed",
            criado_em=agora - dt.timedelta(days=1),
        ),
    ]
    db.add_all(pareceres)


# ------------------------------------------------------------- entrada ----

def semear_cenario(db: Session, sandbox) -> None:
    """Ponto único de entrada (chamado por `app/lab/sandbox.py::_criar_sandbox`).

    Idempotente por sandbox: se `sandbox` já tem algum `LabCandidato` com
    `origem="seed"`, não faz nada (ver docstring do módulo). Insere os três
    cenários (RH, Financeiro, Escola) e comita uma única vez ao final —
    tudo ou nada."""
    ja_semeado = (
        db.query(LabCandidato)
        .filter(LabCandidato.sandbox_id == sandbox.id, LabCandidato.origem == "seed")
        .first()
    )
    if ja_semeado is not None:
        return

    _semear_rh(db, sandbox.id)
    _semear_financeiro(db, sandbox.id)
    _semear_escola(db, sandbox.id)
    db.commit()
