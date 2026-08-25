"""Banco de respostas pré-computadas do guardião de IA (`app/lab/ia.py`).

Entra em ação sempre que `chamar_ia` não pode (ou não deve) gastar uma
chamada real: teto de sandbox, teto diário, API fora do ar ou saída fora do
schema (§7 da spec — "a demo nunca quebra"). A tela mostra o selo discreto
"exemplo pré-computado" quando `RespostaIA.origem == 'fallback'"; o conteúdo
aqui embaixo é o que sustenta esse selo — por isso a exigência da Task 4 do
plano: qualidade de escrita alta, porque quem lê é recrutador avaliando o
autor do site, não só o visitante da demo.

Nenhuma função aqui faz IO nem conhece `LabSandbox`/`SiteSetting` — só texto
e a seleção estável por hash de uma `chave` (§7: "selo discreto...
selecionadas por hash do sandbox — estável por visitante"), para o mesmo
visitante ver sempre a mesma resposta se cair em fallback mais de uma vez.

A `chave` recebida por toda função pública aqui já vem composta por quem
chama (`ia._chave_fallback` = `token do sandbox` + `instancia_id` do
registro) — não é só o token puro. Isto conserta um achado da rodada de
conserto 1: com `chave == token`, todo registro do MESMO sandbox caía na
MESMA variação (8 alunos de uma turma recebendo o idêntico parecer). Este
módulo não sabe nem precisa saber o que compõe a `chave` — só que ela é
estável para a mesma combinação (sandbox, instância).
"""
from __future__ import annotations

import hashlib
import unicodedata

# Lista fechada de categorias contábeis usadas por "categorizar_extrato"
# (§6.2/§9.3 — "categorias só da lista fechada"). Vive aqui, não em `ia.py`,
# porque os exemplos de fallback abaixo precisam dela e `ia.py` importa este
# módulo (não o contrário) — reexportada por `ia.py` para quem só conhece
# `app.lab.ia.CATEGORIAS_FECHADAS`.
CATEGORIAS_FECHADAS = (
    "receita_de_servico",
    "imposto_e_taxas",
    "despesa_operacional",
    "despesa_com_pessoal",
    "despesa_financeira",
    "transferencia_entre_contas",
    "outros",
)


def _indice_estavel(chave: str, quantidade: int) -> int:
    """Mesma `chave` sempre devolve o mesmo índice — hash determinístico,
    não `hash()` do Python (que varia por processo com `PYTHONHASHSEED`)."""
    digest = hashlib.sha256(chave.encode("utf-8")).hexdigest()
    return int(digest, 16) % quantidade


# --------------------------------------------------- triagem de currículo --

# Três perfis de candidato plausíveis, cobrindo os critérios padrão de
# `ia.CRITERIOS_PADRAO_TRIAGEM`. Cada valor é (nota, justificativa) — a
# mesma forma que a validação do recurso real exige.
_PERFIS_TRIAGEM: tuple[dict[str, tuple[int, str]], ...] = (
    {  # perfil 1 — candidato forte, poucos pontos de atenção
        "aderencia_experiencia": (9, "Trajetória muito alinhada ao cargo: experiências recentes na mesma área, com responsabilidades crescentes e resultados mensuráveis."),
        "formacao_academica": (8, "Formação compatível com o requisito da vaga, reforçada por cursos complementares recentes na área."),
        "habilidades_tecnicas": (9, "Domínio claro das ferramentas citadas na vaga, com evidências de uso prático em projetos reais."),
        "comunicacao_e_clareza": (8, "Currículo objetivo e bem estruturado, com resultados quantificados em vez de apenas listar tarefas."),
    },
    {  # perfil 2 — candidato mediano, mistura de pontos fortes e lacunas
        "aderencia_experiencia": (6, "Experiência parcialmente alinhada: parte da trajetória é em área correlata, não idêntica ao cargo."),
        "formacao_academica": (7, "Formação adequada ao nível da vaga, sem especialização direta no tema principal do cargo."),
        "habilidades_tecnicas": (6, "Conhece as ferramentas centrais pedidas na vaga, mas o currículo não detalha profundidade de uso."),
        "comunicacao_e_clareza": (7, "Texto compreensível, ainda que genérico em alguns trechos — falta especificar o impacto das entregas."),
    },
    {  # perfil 3 — candidato júnior, potencial alto
        "aderencia_experiencia": (5, "Pouca experiência direta no cargo, mas a trajetória mostra progressão rápida em funções próximas."),
        "formacao_academica": (8, "Formação recente e alinhada, com bom aproveitamento acadêmico citado no currículo."),
        "habilidades_tecnicas": (6, "Base técnica sólida para o nível júnior, com abertura clara para aprender as ferramentas específicas da vaga."),
        "comunicacao_e_clareza": (8, "Currículo bem escrito, direto, com boa organização cronológica das experiências."),
    },
)

# Quando o recurso pede um critério fora dos quatro padrão (ex.: "ingles",
# vindo de `contexto["criterios"]`), a nota vira a média do perfil e a
# justificativa é uma destas — também selecionadas pelo mesmo índice, para
# não quebrar a estabilidade por sandbox.
_JUSTIFICATIVAS_GENERICAS_TRIAGEM = (
    "Critério dentro da faixa esperada para o perfil, sem alertas relevantes no material analisado.",
    "Avaliação equilibrada: pontos fortes visíveis, com espaço de desenvolvimento nesse aspecto específico.",
    "Critério atendido de forma consistente, compatível com o nível de senioridade da vaga.",
)


def escolher_triagem_curriculo(chave: str, criterios: tuple[str, ...]) -> dict[str, dict]:
    indice = _indice_estavel(f"{chave}:triagem_curriculo", len(_PERFIS_TRIAGEM))
    perfil = _PERFIS_TRIAGEM[indice]
    media = round(sum(nota for nota, _ in perfil.values()) / len(perfil))
    generica = _JUSTIFICATIVAS_GENERICAS_TRIAGEM[indice % len(_JUSTIFICATIVAS_GENERICAS_TRIAGEM)]

    resultado: dict[str, dict] = {}
    for criterio in criterios:
        if criterio in perfil:
            nota, justificativa = perfil[criterio]
        else:
            nota, justificativa = media, generica
        resultado[criterio] = {"nota": nota, "justificativa": justificativa}
    return resultado


# ---------------------------------------------------- categorização de extrato

_VARIACOES_EXTRATO: tuple[tuple[dict, ...], ...] = (
    (
        {"lancamento": "Recebimento de cliente — projeto de consultoria", "categoria": "receita_de_servico",
         "justificativa": "Entrada compatível com pagamento de serviço prestado, valor positivo e descrição de cliente."},
        {"lancamento": "DARF — Simples Nacional", "categoria": "imposto_e_taxas",
         "justificativa": "Guia de recolhimento de tributo federal — enquadra-se diretamente como imposto."},
        {"lancamento": "Assinatura de software de gestão", "categoria": "despesa_operacional",
         "justificativa": "Ferramenta usada na operação do negócio, despesa recorrente necessária à atividade."},
        {"lancamento": "Folha de pagamento — quinzena", "categoria": "despesa_com_pessoal",
         "justificativa": "Pagamento a colaboradores, enquadra-se diretamente em despesa de pessoal."},
        {"lancamento": "Tarifa bancária mensal", "categoria": "despesa_financeira",
         "justificativa": "Cobrança do banco pela manutenção da conta, típica despesa financeira."},
    ),
    (
        {"lancamento": "Recebimento de cliente — mensalidade de contrato", "categoria": "receita_de_servico",
         "justificativa": "Entrada recorrente ligada a contrato de prestação de serviço em vigor."},
        {"lancamento": "Transferência entre contas da empresa", "categoria": "transferencia_entre_contas",
         "justificativa": "Movimentação entre contas do próprio titular, sem efeito de receita ou despesa."},
        {"lancamento": "Compra de material de escritório", "categoria": "despesa_operacional",
         "justificativa": "Insumo consumido na operação diária do negócio, sem vínculo com pessoal ou tributo."},
        {"lancamento": "ISS retido na fonte", "categoria": "imposto_e_taxas",
         "justificativa": "Retenção de imposto municipal sobre serviço, categoria tributária por definição."},
        {"lancamento": "Juros de empréstimo bancário", "categoria": "despesa_financeira",
         "justificativa": "Encargo financeiro sobre linha de crédito, não é despesa operacional do negócio."},
    ),
    (
        {"lancamento": "Recebimento de cliente — venda avulsa de serviço", "categoria": "receita_de_servico",
         "justificativa": "Pagamento único de cliente por serviço pontual prestado no período."},
        {"lancamento": "Pró-labore dos sócios", "categoria": "despesa_com_pessoal",
         "justificativa": "Remuneração de sócios pelo trabalho na empresa, tratada como despesa de pessoal."},
        {"lancamento": "Aluguel do escritório", "categoria": "despesa_operacional",
         "justificativa": "Custo fixo necessário à operação do negócio, sem relação com tributo ou pessoal."},
        {"lancamento": "Estorno de tarifa cobrada indevidamente", "categoria": "outros",
         "justificativa": "Ajuste que não se encaixa nas demais categorias fechadas — lançamento administrativo."},
        {"lancamento": "COFINS e PIS do período", "categoria": "imposto_e_taxas",
         "justificativa": "Tributos federais sobre o faturamento, categoria de imposto por definição."},
    ),
)


def escolher_categorizar_extrato(chave: str) -> list[dict]:
    indice = _indice_estavel(f"{chave}:categorizar_extrato", len(_VARIACOES_EXTRATO))
    # cópia — quem chama pode mutar/serializar sem afetar a próxima seleção
    return [dict(item) for item in _VARIACOES_EXTRATO[indice]]


# ---------------------------------------------------------- parecer pedagógico
# CONSERTO (rodada 1, achado MÉDIO do revisor, segunda metade): o fallback
# tem que ser COERENTE com a situação do aluno (aprovado/recuperação/
# reprovado, §6.3) — nada de parecer elogioso para quem foi reprovado. Por
# isso os textos abaixo são organizados POR SITUAÇÃO, com 3 variações cada
# (tom sempre compatível), e só caem no pool neutro quando `contexto` não
# informa `situacao` nenhuma.

_SITUACOES_VALIDAS = ("aprovado", "recuperacao", "reprovado")

_PARECERES_POR_SITUACAO: dict[str, tuple[str, ...]] = {
    "aprovado": (
        "{nome} encerra o bimestre aprovado, com participação ativa nas aulas e entrega pontual das "
        "atividades propostas. {situacao} Recomenda-se manter o ritmo de estudos atual, aproveitando o "
        "bom desempenho já demonstrado como base para os próximos desafios.",

        "O desempenho de {nome} no período confirma que está aprovado, com resultados consistentes na "
        "maior parte das disciplinas. {situacao} Um acompanhamento leve nas áreas de menor destaque ajuda "
        "a consolidar ainda mais o aproveitamento já alcançado.",

        "{nome} está aprovado neste bimestre, com um perfil dedicado e boa participação nas atividades "
        "em grupo. {situacao} A recomendação é dar continuidade ao suporte pedagógico atual, valorizando "
        "os pontos fortes já consolidados.",
    ),
    "recuperacao": (
        "{nome} está em recuperação neste bimestre: o desempenho oscila entre disciplinas, com bons "
        "resultados em algumas áreas e notas abaixo do esperado em outras. {situacao} Um plano de "
        "estudos direcionado às disciplinas em recuperação, com acompanhamento próximo da família, pode "
        "reverter o quadro ainda neste ano letivo.",

        "O boletim de {nome} aponta recuperação: parte do conteúdo foi bem assimilada, mas a frequência "
        "irregular prejudicou o aproveitamento em outras disciplinas. {situacao} Recomenda-se retomada "
        "guiada dos tópicos com menor rendimento antes da próxima avaliação.",

        "{nome} precisa de atenção nas próximas semanas — está em recuperação, com lacunas pontuais que "
        "ainda podem ser resolvidas com reforço direcionado. {situacao} O acompanhamento pedagógico "
        "próximo é o que evita que o quadro se agrave até o fechamento do ano.",
    ),
    "reprovado": (
        "{nome} está reprovado neste bimestre — não atingiu os critérios mínimos de aprovação. {situacao} "
        "O caso pede um plano de recuperação estruturado e conversa com a família antes do próximo ciclo, "
        "para reorganizar o acompanhamento pedagógico do aluno.",

        "Ao final do bimestre, {nome} está reprovado, com lacunas relevantes acumuladas ao longo do "
        "período. {situacao} Recomenda-se reforço escolar formal e revisão do plano de estudos junto à "
        "coordenação pedagógica.",

        "{nome} está reprovado no fechamento deste bimestre. {situacao} É importante alinhar com a "
        "família um plano de recuperação intensivo, priorizando as disciplinas com maior defasagem antes "
        "do próximo período.",
    ),
}

# pool neutro — só usado quando `contexto["situacao"]` não vem preenchida
# (ou vem com um valor fora de `_SITUACOES_VALIDAS`): nenhuma das frases
# abaixo afirma aprovação nem reprovação, exatamente por não ter como saber
# qual das duas é verdade.
_PARECERES_GERAL = (
    "{nome} demonstra evolução ao longo do bimestre, com participação nas aulas e entrega das atividades "
    "propostas. {situacao} Recomenda-se manter o acompanhamento e reforçar os pontos de maior "
    "dificuldade, aproveitando o engajamento já demonstrado em sala.",

    "O desempenho de {nome} no período varia entre disciplinas, com resultados melhores em algumas áreas "
    "do que em outras. {situacao} Um acompanhamento mais próximo nas próximas semanas ajuda a equilibrar "
    "esse quadro.",

    "{nome} apresenta um perfil dedicado, com organização e participação nas atividades em grupo. "
    "{situacao} O parecer recomenda continuidade do suporte pedagógico atual, com desafios graduais nas "
    "disciplinas em que o aluno tem mais facilidade.",
)

_SITUACAO_PADRAO = "O quadro geral de notas e frequência está descrito a seguir."


def _sanear_sem_levantar(texto: str) -> str:
    """Mesma regra de `protecao.validar_texto` (rejeita `Cc`/`Cf` fora de
    `\\n`/`\\t`), mas silenciosa: um fallback nunca pode levantar exceção —
    caracteres inválidos em `contexto` (que pode carregar dado que passou
    por um caminho fora do controle deste módulo) são descartados, não
    motivo de falha."""
    return "".join(
        c for c in texto
        if c in ("\n", "\t") or unicodedata.category(c) not in ("Cc", "Cf")
    )


def _normalizar_situacao(bruto) -> str | None:
    if not isinstance(bruto, str):
        return None
    valor = bruto.strip().lower()
    return valor if valor in _SITUACOES_VALIDAS else None


def escolher_parecer_pedagogico(chave: str, contexto: dict | None) -> str:
    contexto = contexto or {}
    situacao = _normalizar_situacao(contexto.get("situacao"))
    pool = _PARECERES_POR_SITUACAO[situacao] if situacao else _PARECERES_GERAL
    indice = _indice_estavel(f"{chave}:parecer_pedagogico:{situacao or 'geral'}", len(pool))

    nome = _sanear_sem_levantar(str(contexto.get("aluno_nome") or "O aluno")).strip() or "O aluno"
    situacao_resumo = _sanear_sem_levantar(
        str(contexto.get("situacao_resumo") or _SITUACAO_PADRAO)
    ).strip() or _SITUACAO_PADRAO

    texto = pool[indice].format(nome=nome, situacao=situacao_resumo)
    # rede de segurança: os textos acima já nascem bem abaixo de 900
    # caracteres, mas um `aluno_nome`/`situacao_resumo` gigante não deveria
    # conseguir estourar o limite do próprio schema que este módulo alimenta
    return texto[:900]
