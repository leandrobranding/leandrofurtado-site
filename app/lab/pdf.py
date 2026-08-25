"""PDFs de demonstração do Lab (Task 5 do Plano 1: NF fiscal e boletim
escolar — §6.2/§6.3 e §9.6 da spec).

Layout NEUTRO nesta task (§2 item 2 da spec: identidade visual própria de
cada demo só entra no Plano 2, depois do veredito do Leandro) — tipografia
limpa, escala de cinza pura, sem cor de marca. Reaproveita o MESMO padrão de
registro de fonte do currículo em PDF (`app/services/resume.py`): as fontes
TTF já commitadas em `app/static/fonts/pdf/` (Space Grotesk para títulos,
Montserrat para corpo), Unicode de verdade — acento e "·" saem direto, sem
precisar de tabela de substituição caractere a caractere.

ÚNICA exceção de fonte: a tarja de aviso ("DEMONSTRAÇÃO — SEM VALOR FISCAL"
no NF / "DOCUMENTO DE DEMONSTRAÇÃO" no boletim) é desenhada com a fonte core
Helvetica (`pdf.core_fonts_encoding = "cp1252"`, que cobre Ç/Ã/— nativamente)
em vez das TTF da casa. Motivo: com fonte TTF Unicode, o fpdf2 grava o texto
no content stream como índices de glifo (CID), não como bytes ASCII/latin —
fonte core grava texto literal. O resto do documento (títulos, tabelas,
valores) segue nas fontes TTF da casa.

Compressão do stream (`pdf.compress`) fica no padrão do fpdf2 (`True`) em
produção — ruling da rodada de conserto 1: desligar compressão só para o
teste achar a tarja nos bytes inflaria ~5% todo PDF que um visitante baixa,
por causa de um detalhe de teste. Os testes que precisam inspecionar a
tarja byte a byte (`tests/lab/test_pdf.py`) usam um helper que desliga a
compressão SÓ na instância do teste (monkeypatch de `_novo_pdf`), nunca em
produção — ver `_novo_pdf` abaixo e o fixture correspondente no teste.

Todo texto que chega de um registro (nome/documento/e-mail de cliente,
descrição de item, categoria de imposto, nome/turma de aluno, disciplina,
texto do parecer) passa por `protecao.validar_texto` ANTES do fpdf2 — mesma
política da entrada (§9.6): nada interpretável chega à biblioteca de PDF.

Contrato de `LabNota.itens`/`LabNota.impostos` (JSON — definido aqui porque
nenhuma task anterior fixou o formato; Task 6/Plano 2 devem produzir isto):
    itens: [{"descricao": str, "quantidade": int|float,
              "valor_unit_centavos": int}, ...]
    impostos: {categoria_str: valor_centavos_int, ...}

F8 (herança do Plano 1 para o Plano 2): a CHAVE de `impostos` é o código
interno usado no cálculo (ex. "iss_simulado_5_por_cento", como os seeds da
Task 6 já gravam) — nunca o texto que o visitante lê no PDF. `rotulo_humano_imposto`
abaixo traduz o código para o rótulo humano (ex. "ISS (5% simulado)") só na
hora de desenhar a tabela; a Task 6 do Plano 2, ao explicar o imposto na
tela (base, alíquota, valor), deve reusar o mesmo mapa em vez de inventar um
segundo rótulo para a mesma categoria.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING

from fpdf import FPDF
from fpdf.enums import Align, XPos, YPos

from .protecao import MAX_CAMPO, MAX_PDFS, validar_texto

if TYPE_CHECKING:
    from .models import (
        LabAluno,
        LabAvaliacao,
        LabClienteFiscal,
        LabNota,
        LabParecer,
        LabSandbox,
    )

# Mesmo diretório e mesmo par de famílias do currículo (app/services/resume.py)
FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts" / "pdf"
FONTS = {
    "SG": ("SpaceGrotesk-Medium.ttf", "SpaceGrotesk-Bold.ttf"),
    "MS": ("Montserrat-Regular.ttf", "Montserrat-Bold.ttf"),
    "MSsb": ("Montserrat-SemiBold.ttf", "Montserrat-SemiBold.ttf"),
}

# Paleta neutra desta task: escala de cinza pura, sem matiz de marca nenhuma
# (Plano 2 troca pela identidade própria de cada demo).
PRETO = (20, 20, 20)
CINZA_ESCURO = (60, 58, 54)
CINZA = (110, 108, 103)
CINZA_CLARO = (215, 213, 208)
BRANCO = (255, 255, 255)

TARJA_NF = "DEMONSTRAÇÃO — SEM VALOR FISCAL"
TARJA_BOLETIM = "DOCUMENTO DE DEMONSTRAÇÃO"

# Emitente fictício fixo do módulo Financeiro: toda NF do Lab sai em nome
# dele. §9.9 da spec — dado semeado visivelmente fictício, CNPJ com dígito
# verificador errado DE PROPÓSITO (nunca coincide com um documento real).
EMITENTE_NOME = "Estúdio Fictício de Demonstração LTDA (empresa fictícia)"
EMITENTE_CNPJ = "00.000.000/0001-00"  # inválido por design — DV não confere
EMITENTE_ENDERECO = "Rua das Demonstrações, 100 — Curitiba/PR (endereço fictício)"

# "situação" do boletim é uma heurística de EXIBIÇÃO desta task (a regra
# "canônica" de aprovado/recuperação/reprovado por média E frequência,
# §6.3, é tela/rota do Plano 2 — que pode recalcular e passar dados
# equivalentes). Documentado aqui porque o PDF precisa mostrar *alguma*
# situação e o limite de faltas não existe em `LabAvaliacao` (só a
# contagem, sem "total de aulas" para calcular percentual).
LIMITE_FALTAS_DEMO = 20

# ------------------------------------------------------- F8: rótulo humano --
# Mapa código interno -> texto que o visitante lê no PDF (e, pela Task 6 do
# Plano 2, na tela também — ver contrato no topo do módulo). Só os códigos
# que os seeds da Task 6 do Plano 1 já gravam (`app/lab/seeds_demo.py`)
# entram aqui de saída; a rota que emite NF de verdade no Plano 2 deve somar
# entradas novas neste MESMO dict em vez de espalhar um segundo mapa.
ROTULOS_IMPOSTO = {
    "iss_simulado_5_por_cento": "ISS (5% simulado)",
    "icms_simulado": "ICMS (simulado)",
    "irrf_simulado": "IRRF (simulado)",
    "pis_simulado": "PIS (simulado)",
    "cofins_simulado": "COFINS (simulado)",
}


def rotulo_humano_imposto(categoria: str) -> str:
    """Traduz a CHAVE de `LabNota.impostos` para o rótulo que o visitante lê
    (F8: nunca o código cru tipo "iss_simulado_5_por_cento" na tabela do
    PDF). Código conhecido -> texto do `ROTULOS_IMPOSTO` acima. Código
    desconhecido que PARECE máquina (tem "_" ou é só minúsculas sem espaço)
    -> humanizado na hora ("nova_taxa" -> "Nova Taxa"). Qualquer outra coisa
    (ex. "ISS", uma sigla já pronta para leitura, ou o texto de um teste)
    passa direto — só normaliza o que de fato parece código, nunca reformata
    um texto que já está bom."""
    if categoria in ROTULOS_IMPOSTO:
        return ROTULOS_IMPOSTO[categoria]
    parece_codigo = "_" in categoria or (categoria == categoria.lower() and " " not in categoria)
    if not parece_codigo:
        return categoria
    return " ".join(parte.capitalize() for parte in categoria.replace("_", " ").split())


def formatar_centavos(centavos: int) -> str:
    """1234567 -> "R$ 12.345,67" (formatação BR: milhar com ponto, decimal
    com vírgula) — sem `locale` (não confiável entre SO/contêiner)."""
    centavos = int(centavos)
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    milhar = f"{reais:,}".replace(",", ".")
    return f"{sinal}R$ {milhar},{resto:02d}"


def _checar_teto_pdf(sandbox: "LabSandbox") -> None:
    """§8: máx `MAX_PDFS` PDFs por sandbox (NF e boletim somados — o
    contador é único em `LabSandbox.pdfs_gerados`). `ValueError` PT-BR
    acima do teto, chamar ANTES de montar o documento."""
    if sandbox.pdfs_gerados >= MAX_PDFS:
        raise ValueError(
            f"limite de {MAX_PDFS} PDFs deste sandbox atingido — "
            "espere a demonstração expirar ou volte mais tarde."
        )


def _novo_pdf() -> FPDF:
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(18, 14, 18)
    # cp1252 (WinAnsi) cobre Ç/Ã/— na fonte core — ver docstring do módulo.
    pdf.core_fonts_encoding = "cp1252"
    # compress fica no padrão do fpdf2 (True) — ver docstring do módulo.
    for fam, (regular, bold) in FONTS.items():
        pdf.add_font(fam, "", str(FONT_DIR / regular))
        pdf.add_font(fam, "B", str(FONT_DIR / bold))
    pdf.add_page()
    return pdf


def _tarja(pdf: FPDF, texto: str) -> None:
    """Banda preta de aviso, largura cheia da página, fonte core (texto
    literal e buscável nos bytes — ver docstring do módulo).

    BLOQUEADOR consertado na rodada de revisão 1: `set_fill_color`/
    `set_text_color` são estado do OBJETO `pdf`, não escopados a esta
    função — sem salvar e restaurar o que já estava setado antes de entrar
    aqui, o preto da tarja vazava para o próximo elemento que usasse fill
    (a tabela de itens, por exemplo: texto preto sobre fundo que a tabela
    herdava preto = tabela invisível). Salva os dois ANTES de mexer,
    restaura os dois no fim — simétrico, nenhum hardcode de cor."""
    fill_anterior = pdf.fill_color
    texto_anterior = pdf.text_color
    largura = pdf.w
    altura = 8.0
    y = pdf.get_y()
    pdf.set_fill_color(*PRETO)
    pdf.rect(0, y, largura, altura, style="F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*BRANCO)
    pdf.set_xy(0, y + 1.7)
    pdf.cell(largura, 5, texto, align=Align.C)
    pdf.set_xy(pdf.l_margin, y + altura + 4)
    pdf.set_fill_color(fill_anterior)
    pdf.set_text_color(texto_anterior)


def _rule(pdf: FPDF, largura: float, esquerda: float, gap_antes=2.0, gap_depois=3.0) -> None:
    pdf.ln(gap_antes)
    pdf.set_draw_color(*CINZA_CLARO)
    pdf.set_line_width(.2)
    y = pdf.get_y()
    pdf.line(esquerda, y, esquerda + largura, y)
    pdf.ln(gap_depois)


def _rodape(pdf: FPDF, esquerda: float, tarja_texto: str, disclaimer: str) -> None:
    """Tarja + linha de aviso no rodapé da ÚLTIMA página do documento.

    Achado na verificação visual da rodada de conserto 1 (não estava na
    lista de rulings, mas é o mesmo tipo de defeito): `pdf.set_y(-26)`
    coloca o cursor a 26mm do fim da página — perto o bastante do
    `page_break_trigger` do auto page break (`h - b_margin`) para que o
    PRÓPRIO `cell()` da tarja disparasse uma quebra de página automática no
    meio do rodapé. Resultado real visto em `nf_normal.pdf`: a banda preta
    (`rect()`, que não olha pra auto page break) ficava na página 1, o
    texto branco por cima ia pra uma página 2 quase em branco, e a linha de
    disclaimer ainda ia parar numa página 3 — três páginas em vez de uma,
    tarja partida ao meio. Fix: desliga `auto_page_break` só para desenhar
    o rodapé (nada mais é desenhado depois dele nesta função, então não
    precisa religar)."""
    pdf.set_auto_page_break(False)
    pdf.set_y(-26)
    _tarja(pdf, tarja_texto)
    pdf.set_font("MS", "", 7)
    pdf.set_text_color(*CINZA)
    pdf.set_x(esquerda)
    pdf.cell(0, 4, disclaimer, align=Align.C)
    pdf.set_text_color(*PRETO)


def _kicker(pdf: FPDF, esquerda: float, texto: str) -> None:
    pdf.set_font("MSsb", "", 8.2)
    pdf.set_text_color(*CINZA)
    pdf.set_char_spacing(.6)
    pdf.set_x(esquerda)
    pdf.cell(0, 5, texto.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_char_spacing(0)
    pdf.set_text_color(*PRETO)


# --------------------------------------------------------------------- NF --

def gerar_nf_pdf(nota: "LabNota", cliente: "LabClienteFiscal", sandbox: "LabSandbox") -> bytes:
    """Documento fiscal de demonstração: emitente fictício, destinatário,
    itens, impostos, total, numeração sequencial POR sandbox (`nota.numero`
    — §6.2), tarja "DEMONSTRAÇÃO — SEM VALOR FISCAL" no topo e no rodapé.

    Levanta `ValueError` (mensagem PT-BR) se o sandbox já gerou `MAX_PDFS`
    PDFs (§8), ou se qualquer texto do registro falhar em
    `protecao.validar_texto` — checado ANTES de qualquer chamada ao fpdf2
    (§9.6). Incrementa `sandbox.pdfs_gerados` só depois de montar o PDF com
    sucesso; esta função não recebe `db` — persistir o contador é
    responsabilidade de quem chama (rota do Plano 2)."""
    _checar_teto_pdf(sandbox)

    nome_cliente = validar_texto(cliente.nome or "", MAX_CAMPO)
    documento_cliente = validar_texto(cliente.documento or "", MAX_CAMPO)
    email_cliente = validar_texto(cliente.email or "", MAX_CAMPO)

    itens: list[dict] = []
    for item in (nota.itens or []):
        itens.append({
            "descricao": validar_texto(str(item.get("descricao", "")), MAX_CAMPO),
            "quantidade": item.get("quantidade", 1),
            "valor_unit_centavos": int(item.get("valor_unit_centavos", 0)),
        })

    impostos: list[tuple[str, int]] = []
    for categoria, valor in (nota.impostos or {}).items():
        categoria_validada = validar_texto(str(categoria), MAX_CAMPO)
        impostos.append((rotulo_humano_imposto(categoria_validada), int(valor)))

    pdf = _novo_pdf()
    L = pdf.l_margin
    W = pdf.w - pdf.l_margin - pdf.r_margin

    _tarja(pdf, TARJA_NF)

    pdf.set_font("SG", "B", 17)
    pdf.set_x(L)
    pdf.cell(0, 8, "NOTA FISCAL DE DEMONSTRAÇÃO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    emitida_em = nota.criado_em.strftime("%d/%m/%Y") if nota.criado_em else "—"
    pdf.set_font("MSsb", "", 9.5)
    pdf.set_text_color(*CINZA)
    pdf.set_x(L)
    pdf.cell(0, 6, f"Nº {nota.numero:06d}   ·   emitida em {emitida_em}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PRETO)
    pdf.ln(3)

    def _bloco(titulo: str, linhas: list[str]) -> None:
        _kicker(pdf, L, titulo)
        pdf.set_font("MS", "", 9.8)
        for linha in linhas:
            if not linha:
                continue
            pdf.set_x(L)
            pdf.multi_cell(W, 5, linha, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    _bloco("Emitente", [EMITENTE_NOME, f"CNPJ (fictício): {EMITENTE_CNPJ}", EMITENTE_ENDERECO])
    documento_linha = f"Documento (fictício): {documento_cliente}" if documento_cliente else ""
    _bloco("Destinatário", [nome_cliente, documento_linha, email_cliente])
    _rule(pdf, W, L)

    # ------------------------------------------------------------ itens --
    _kicker(pdf, L, "Itens")
    with pdf.table(
        col_widths=(5, 2, 3, 3),
        text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT"),
        borders_layout="SINGLE_TOP_LINE",
        line_height=6,
        first_row_as_headings=True,
    ) as table:
        pdf.set_font("MSsb", "", 8.6)
        linha = table.row()
        for cabecalho in ("Item", "Qtd", "Valor unit.", "Subtotal"):
            linha.cell(cabecalho)
        pdf.set_font("MS", "", 9)
        for item in itens:
            subtotal_centavos = round(float(item["quantidade"]) * item["valor_unit_centavos"])
            linha = table.row()
            linha.cell(item["descricao"])
            linha.cell(str(item["quantidade"]))
            linha.cell(formatar_centavos(item["valor_unit_centavos"]))
            linha.cell(formatar_centavos(subtotal_centavos))
    pdf.ln(2)

    # --------------------------------------------------------- impostos --
    # Tabela (não cell() solto) DE PROPÓSITO: categoria é validada só contra
    # MAX_CAMPO (200 chars — válida!), e cell() não quebra linha — uma
    # categoria longa vazava da coluna, invadia o valor e saía da página
    # (achado da revisão 1, nf_categoria_longa.pdf). pdf.table() quebra o
    # texto dentro da largura da coluna e calcula a altura da linha sozinho,
    # o mesmo mecanismo já usado na tabela de itens acima.
    if impostos:
        _kicker(pdf, L, "Impostos (simulados)")
        with pdf.table(
            col_widths=(7, 3),
            text_align=("LEFT", "RIGHT"),
            borders_layout="SINGLE_TOP_LINE",
            line_height=5.6,
            first_row_as_headings=False,
        ) as table:
            pdf.set_font("MS", "", 9.5)
            for categoria, valor in impostos:
                linha = table.row()
                linha.cell(categoria)
                linha.cell(formatar_centavos(valor))
        pdf.ln(2)

    _rule(pdf, W, L)

    pdf.set_font("SG", "B", 13)
    pdf.set_x(L)
    pdf.cell(W * .7, 8, "TOTAL")
    pdf.cell(W * .3, 8, formatar_centavos(nota.total_centavos), align=Align.R,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    status_rotulo = "CANCELADA" if nota.status == "cancelada" else "EMITIDA"
    pdf.set_font("MSsb", "", 8.5)
    pdf.set_text_color(*CINZA)
    pdf.set_x(L)
    pdf.cell(0, 6, f"Status: {status_rotulo}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PRETO)

    _rodape(pdf, L, TARJA_NF,
            "Documento gerado pelo Lab de Demos de leandrofurtado.com.br — sem qualquer validade fiscal.")

    sandbox.pdfs_gerados += 1
    return bytes(pdf.output())


# --------------------------------------------------------------- boletim --

def _situacao_aluno(avaliacoes: list["LabAvaliacao"]) -> tuple[str, float, int]:
    """Heurística de EXIBIÇÃO desta task (ver `LIMITE_FALTAS_DEMO` acima) —
    devolve (situação, média geral, faltas totais)."""
    if not avaliacoes:
        return "sem avaliações lançadas", 0.0, 0

    por_disciplina: dict[str, list[float]] = {}
    faltas_totais = 0
    for av in avaliacoes:
        por_disciplina.setdefault(av.disciplina, []).append(av.nota)
        faltas_totais += av.faltas or 0

    medias = [sum(notas) / len(notas) for notas in por_disciplina.values()]
    media_geral = sum(medias) / len(medias) if medias else 0.0

    if faltas_totais > LIMITE_FALTAS_DEMO:
        situacao = "reprovado por falta"
    elif media_geral >= 6:
        situacao = "aprovado"
    elif media_geral >= 4:
        situacao = "recuperação"
    else:
        situacao = "reprovado"
    return situacao, media_geral, faltas_totais


def gerar_boletim_pdf(
    aluno: "LabAluno",
    avaliacoes: list["LabAvaliacao"],
    parecer: "LabParecer | None",
    sandbox: "LabSandbox",
) -> bytes:
    """Boletim de demonstração: grade de notas por disciplina/bimestre,
    situação do aluno (heurística de exibição — ver `_situacao_aluno`),
    parecer pedagógico, aviso "DOCUMENTO DE DEMONSTRAÇÃO" no topo e no
    rodapé (§6.3).

    Mesmas regras de `gerar_nf_pdf`: `ValueError` acima do teto de
    `MAX_PDFS` ou se algum texto do registro falhar em `validar_texto`;
    contador incrementado só após sucesso; sem `db` — persistir é tarefa de
    quem chama."""
    _checar_teto_pdf(sandbox)

    nome_aluno = validar_texto(aluno.nome or "", MAX_CAMPO)
    turma_aluno = validar_texto(aluno.turma or "", MAX_CAMPO)

    linhas_grade: list[dict] = []
    for av in avaliacoes:
        linhas_grade.append({
            "disciplina": validar_texto(av.disciplina or "", MAX_CAMPO),
            "bimestre": av.bimestre,
            "nota": av.nota,
            "faltas": av.faltas,
        })

    texto_parecer = ""
    origem_parecer = ""
    if parecer is not None:
        texto_parecer = validar_texto(parecer.texto_ia or "", 900)
        origem_parecer = parecer.origem or ""

    situacao, media_geral, faltas_totais = _situacao_aluno(avaliacoes)

    pdf = _novo_pdf()
    L = pdf.l_margin
    W = pdf.w - pdf.l_margin - pdf.r_margin

    _tarja(pdf, TARJA_BOLETIM)

    pdf.set_font("SG", "B", 17)
    pdf.set_x(L)
    pdf.cell(0, 8, "BOLETIM ESCOLAR DE DEMONSTRAÇÃO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("MSsb", "", 9.5)
    pdf.set_text_color(*CINZA)
    pdf.set_x(L)
    turma_txt = f"   ·   Turma {turma_aluno}" if turma_aluno else ""
    # multi_cell, não cell(0, ...): nome de aluno (até MAX_CAMPO=200 chars,
    # válido) mais turma podia cortar no meio da palavra na borda da página
    # (achado da revisão 1) — cell() não quebra linha, multi_cell quebra.
    pdf.multi_cell(W, 6, f"{nome_aluno}{turma_txt}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PRETO)
    pdf.ln(3)

    _kicker(pdf, L, "Notas e faltas")
    if linhas_grade:
        with pdf.table(
            col_widths=(4, 2, 2, 2),
            text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT"),
            borders_layout="SINGLE_TOP_LINE",
            line_height=6,
            first_row_as_headings=True,
        ) as table:
            pdf.set_font("MSsb", "", 8.6)
            linha = table.row()
            for cabecalho in ("Disciplina", "Bimestre", "Nota", "Faltas"):
                linha.cell(cabecalho)
            pdf.set_font("MS", "", 9)
            for item in linhas_grade:
                linha = table.row()
                linha.cell(item["disciplina"])
                linha.cell(str(item["bimestre"]))
                linha.cell(f"{item['nota']:.1f}")
                linha.cell(str(item["faltas"]))
    else:
        pdf.set_font("MS", "", 9.5)
        pdf.set_x(L)
        pdf.cell(0, 5.5, "Nenhuma avaliação lançada ainda.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    _rule(pdf, W, L)

    _kicker(pdf, L, "Situação")
    pdf.set_font("SG", "B", 13)
    pdf.set_x(L)
    pdf.cell(0, 7, situacao.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("MS", "", 9)
    pdf.set_text_color(*CINZA)
    pdf.set_x(L)
    pdf.cell(0, 5.5, f"Média geral: {media_geral:.1f}   ·   Faltas totais: {faltas_totais}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PRETO)
    pdf.ln(2)

    _rule(pdf, W, L)

    _kicker(pdf, L, "Parecer pedagógico")
    pdf.set_font("MS", "", 9.7)
    pdf.set_x(L)
    if texto_parecer:
        pdf.multi_cell(W, 5, texto_parecer, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if origem_parecer == "fallback":
            pdf.set_font("MSsb", "", 7.4)
            pdf.set_text_color(*CINZA)
            pdf.set_x(L)
            pdf.cell(0, 4.4, "· exemplo pré-computado ·", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*PRETO)
    else:
        pdf.multi_cell(W, 5, "Parecer ainda não gerado para este aluno.",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    _rodape(pdf, L, TARJA_BOLETIM,
            "Documento gerado pelo Lab de Demos de leandrofurtado.com.br — uso ilustrativo, sem valor oficial.")

    sandbox.pdfs_gerados += 1
    return bytes(pdf.output())
