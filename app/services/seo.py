"""Título e descrição de case para o Google, derivados do conteúdo.

Por que derivar e não pedir num formulário: decisão de 2026, registrada em
`apply_case_form` — "SEO deixou de ser formulário: sai do que já foi escrito,
toda vez que se salva". Digitar de novo o título numa caixa chamada "título no
Google" era trabalho dobrado que, na prática, ficava vazio ou repetia a linha
de cima. Este módulo mantém essa decisão e só troca a fórmula.

O que a fórmula antiga produzia, medido no SERP em 22/08/2026:

    título:    "Linha Celebre 100 Anos — Leandro Furtado"
    descrição: "Evento de 100 Anos da Linha Celebre de Electrolux."   (50 car.)

O Google mostra ~60 caracteres de título e ~155 de descrição. Dois terços do
espaço estavam vazios em 24 páginas de case, e o nome do CLIENTE — que é o
termo que alguém realmente busca ("campanha electrolux 100 anos") — não
aparecia no título.

O que passa a valer:

    título:    "Electrolux ·︎ Linha Celebre 100 Anos ·︎ Leandro Furtado"
    descrição: "Evento de 100 Anos da Linha Celebre de Electrolux. Projeto de
                live marketing. Direção de arte por Leandro Furtado,
                Curitiba, 2026."

Duas regras que evitam o texto robótico:

1. Nada se repete. Se o subtítulo já diz "DAF Caminhões", o cliente não é
   acrescentado; se já diz "Key visual", a categoria não é. Sem isso saía
   "Key visual para evento da DAF. Projeto de key visual para DAF."

2. Cada pedaço só entra se couber. A frase é montada em ordem de importância e
   para quando o orçamento acaba, em vez de ser cortada no meio de um nome
   próprio — o que é pior do que não citar.
"""
import re

# O que o Google mostra antes de cortar. Não é limite rígido dele (o corte é
# por pixel, não por caractere), é o ponto onde o corte começa a aparecer em
# português — medido no resultado real do site.
LIMITE_TITULO = 60
LIMITE_DESCRICAO = 155

SEPARADOR = " ·︎ "          # mesmo separador do title da home (i18n.py)
MARCA = "Leandro Furtado"
CIDADE = "Curitiba"

# U+FE0E é seletor de apresentação: ocupa um code point e nenhum pixel. Contar
# ele estouraria o orçamento por engano. Ver [[glifos-sem-emoji]].
_INVISIVEL = "︎"


def _visivel(texto: str) -> int:
    """Caracteres que o Google realmente desenha."""
    return len(texto.replace(_INVISIVEL, ""))


def _contem(agulha: str, palheiro: str) -> bool:
    """Comparação frouxa: ignora caixa e acento não importa aqui porque os dois
    lados vêm do mesmo cadastro. Serve para não repetir o que já foi dito."""
    return bool(agulha) and agulha.strip().lower() in (palheiro or "").lower()


def _cortar(texto: str, limite: int) -> str:
    """Corta na palavra, nunca no meio dela, e sem deixar pontuação órfã."""
    if _visivel(texto) <= limite:
        return texto
    corte = texto[:limite]
    espaco = corte.rfind(" ")
    if espaco > limite * 0.6:      # só vale se não amputar quase tudo
        corte = corte[:espaco]
    return corte.rstrip(" ,;:.-·") + "…"


def titulo_para_busca(titulo: str, cliente: str = "") -> str:
    """Título do case no Google.

    Ordem de preferência, sempre respeitando os 60 caracteres:
      1. cliente + título + marca
      2. cliente + título
      3. título + marca
      4. título cortado

    O cliente vem antes do título porque é o termo com volume de busca; a
    marca vem por último porque o domínio já aparece logo acima do título no
    resultado, então perdê-la custa pouco.
    """
    titulo = (titulo or "").strip()
    cliente = (cliente or "").strip()
    if not titulo:
        return MARCA

    com_cliente = titulo
    if cliente and not _contem(cliente, titulo):
        com_cliente = f"{cliente}{SEPARADOR}{titulo}"

    for candidato in (f"{com_cliente}{SEPARADOR}{MARCA}",
                      com_cliente,
                      f"{titulo}{SEPARADOR}{MARCA}",
                      titulo):
        if _visivel(candidato) <= LIMITE_TITULO:
            return candidato
    return _cortar(titulo, LIMITE_TITULO)


def descricao_para_busca(resumo: str, categoria: str = "", cliente: str = "",
                         ano: str = "", lang: str = "pt") -> str:
    """Descrição do case no Google.

    Monta em três camadas e para quando o orçamento acaba:
      1. o resumo (subtítulo do case), que é a frase já pensada;
      2. o que o projeto é e para quem, pulando o que o resumo já disse;
      3. a assinatura, que carrega a cidade — 24 páginas reforçando "Curitiba"
         valem mais para busca local do que a home sozinha.
    """
    resumo = re.sub(r"\s+", " ", (resumo or "")).strip()
    categoria = (categoria or "").strip()
    cliente = (cliente or "").strip()
    ano = (ano or "").strip()

    if not resumo:
        resumo = ""
    elif resumo[-1] not in ".!?…":
        resumo += "."

    partes = [resumo] if resumo else []

    # camada 2: só o que ainda não foi dito
    en = lang == "en"
    categoria_frase = categoria.replace(" & ", " and " if en else " e ")
    diz_categoria = categoria and not _contem(categoria, resumo)
    diz_cliente = cliente and not _contem(cliente, resumo)
    if diz_categoria and diz_cliente:
        meio = (f"A {categoria_frase.lower()} project for {cliente}." if en
                else f"Projeto de {categoria_frase.lower()} para {cliente}.")
    elif diz_categoria:
        meio = (f"A {categoria_frase.lower()} project." if en
                else f"Projeto de {categoria_frase.lower()}.")
    elif diz_cliente:
        meio = f"A project for {cliente}." if en else f"Projeto para {cliente}."
    else:
        meio = ""

    # camada 3: assinatura, do mais completo ao mais curto. O subtítulo do
    # "Primeira conta" tem 110 caracteres sozinho: sem uma versão enxuta, ele
    # ficaria sem assinatura nenhuma e desperdiçaria os 45 que sobram.
    if en:
        assinatura = f"Art direction by {MARCA}, {CIDADE}, Brazil"
        assinatura_curta = f"By {MARCA}, {CIDADE}."
        assinatura_minima = f"By {MARCA}."
    else:
        assinatura = f"Direção de arte por {MARCA}, {CIDADE}"
        assinatura_curta = f"Por {MARCA}, {CIDADE}."
        assinatura_minima = f"Por {MARCA}."
    assinatura_com_ano = f"{assinatura}, {ano}." if ano else f"{assinatura}."
    assinatura += "."

    for cauda in ([meio, assinatura_com_ano], [meio, assinatura],
                  [assinatura_com_ano], [assinatura],
                  [meio, assinatura_curta], [assinatura_curta],
                  [assinatura_minima], []):
        candidato = " ".join(p for p in (partes + cauda) if p)
        if _visivel(candidato) <= LIMITE_DESCRICAO:
            return candidato
    return _cortar(resumo, LIMITE_DESCRICAO)


def resumo_do_case(case) -> str:
    """A frase de partida da descrição: o subtítulo, ou o começo do corpo.

    Veio de `admin.py` em 22/08/2026 para o script de recálculo
    (scripts/recalcular_seo.py) poder usar exatamente a mesma regra do
    painel — duas cópias divergiriam no primeiro ajuste.

    Preferência para o subtítulo, que já é uma frase pensada para resumir. Sem
    ele, valem as primeiras palavras do resumo, com a marcação do Markdown
    limpa: asterisco e cerquilha no resultado de busca não ajudam ninguém.
    """
    if (case.subtitle_pt or "").strip():
        return case.subtitle_pt.strip()
    corpo = re.sub(r"[#*_>`\[\]]+", " ", case.body_pt or "")
    corpo = re.sub(r"\s+", " ", corpo).strip()
    if len(corpo) <= LIMITE_DESCRICAO:
        return corpo
    corte = corpo[:LIMITE_DESCRICAO]
    return corte[:corte.rfind(" ")].rstrip(",;:") + "…"


def descricao_de_cliente(cliente: str, titulos: list[str], lang: str = "pt") -> str:
    """Descrição da página de um cliente.

    Lista os TÍTULOS dos projetos daquele cliente, e não uma frase genérica,
    por um motivo prático: são 22 páginas de cliente, e 22 descrições idênticas
    a menos do nome são conteúdo duplicado aos olhos do Google. Com os títulos,
    cada página difere das outras sem ninguém escrever nada.

    A fórmula antiga era "Tudo o que foi feito para {cliente}: N projetos." —
    48 caracteres onde cabem 155, e com erro de plural em toda página de um
    projeto só ("1 projetos"), visível no resultado de busca do Bradesco, da
    Electrolux e de mais quatro em 22/08/2026.

    Três saídas, nesta ordem:
      1. todos os títulos, quando cabem;
      2. os que couberem, cortados na VÍRGULA, mais "e outros";
      3. nenhum título, quando nem o primeiro cabe — nome de cliente longo com
         projeto de nome longo ("Hospital Marcelino Champagnat" +
         "Dia do profissional do Secretariado"). Fragmento cortado no meio da
         palavra lê como página quebrada, e é pior que não citar.

    O fecho nunca é sacrificado: é onde estão as palavras que alguém busca.
    """
    titulos = [t.strip() for t in (titulos or []) if t and t.strip()]
    n = len(titulos)
    if lang == "en":
        abre = f"{'Project' if n == 1 else 'Projects'} for {cliente}: "
        fecha = ". Key visual, branding, live marketing and motion by Leandro Furtado."
        mais = " and more"
        sem_lista = (f"Art direction, key visual, branding and live marketing "
                     f"for {cliente}. By Leandro Furtado, Curitiba, Brazil.")
    else:
        abre = f"{'Projeto' if n == 1 else 'Projetos'} de direção de arte para {cliente}: "
        fecha = ". Key visual, branding, live marketing e motion por Leandro Furtado."
        mais = " e outros"
        sem_lista = (f"Direção de arte, key visual, branding e live marketing "
                     f"para {cliente}. Por Leandro Furtado, Curitiba.")

    if not titulos:
        return _cortar(sem_lista, LIMITE_DESCRICAO)

    lista = ", ".join(titulos)
    sobra = LIMITE_DESCRICAO - len(abre) - len(fecha)
    if len(lista) <= sobra:
        return abre + lista + fecha

    # corta na última vírgula que ainda deixa espaço para o " e outros"
    corte = lista[:max(0, sobra - len(mais))]
    virgula = corte.rfind(",")
    if virgula > 0:
        return abre + corte[:virgula] + mais + fecha
    return _cortar(sem_lista, LIMITE_DESCRICAO)
