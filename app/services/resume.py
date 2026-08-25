"""Geração do currículo em PDF a partir do mesmo Profile do site.

Rodada 3 (19/08, item 5 — "mega e super importante" pro dono: "não adianta
o recrutador ver um site lindo e um PDF feio"). Redesenho completo: as
mesmas duas fontes da casa embutidas de verdade (Space Grotesk pro nome e
kickers grandes, Montserrat pro corpo e rótulos — os TTF estáticos em
app/static/fonts/pdf/ vêm dos woff2 variáveis do site, convertidos uma
vez com fontTools+brotli, ver o comentário no fim do arquivo), a mesma
paleta clara de impressão do tema claro do site, a mesma hierarquia
(nome em display grande, rótulos de seção em mono caps estilo kicker,
timeline de experiência com as tags em chip, grid editorial de duas
colunas em habilidades e certificações — eco direto do redesenho do
/about na mesma rodada).

Como o TTF é Unicode de verdade (não a Helvetica core do PDF, presa a
latin-1), acentuação e "·" saem direto — acabou o `_latin()` que trocava
caractere por caractere.

Sem dependências de sistema (fpdf2 é Python puro), então roda igual no VPS.
"""

import io
import re
from pathlib import Path

# ---------------------------------------------------------------- paleta
# Os mesmos tokens do tema claro do site (:root[data-theme="light"] em
# app/static/css/main.css) — um PDF não herda CSS, os valores são copiados
# a mão aqui, não importados.
INK = (18, 18, 17)          # --ink
MUTED = (109, 107, 102)     # --muted
LINE = (217, 215, 209)      # --line
SUB = (53, 51, 47)          # --sub
CHIP_BG = (231, 229, 224)   # --bg-2 (fundo dos chips de tag)

FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts" / "pdf"

# nomes internos: "SG" = Space Grotesk (display), "MS" = Montserrat (texto
# e kickers). Cada peso vira uma família fpdf2 própria — style "" e "B" do
# fpdf2 não bastam pra 3 pesos de Montserrat (regular/semibold/bold).
FONTS = {
    "SG": ("SpaceGrotesk-Medium.ttf", "SpaceGrotesk-Bold.ttf"),
    "MS": ("Montserrat-Regular.ttf", "Montserrat-Bold.ttf"),
    "MSsb": ("Montserrat-SemiBold.ttf", "Montserrat-SemiBold.ttf"),
}


def _fields(profile: dict, lang: str) -> dict:
    """Achata o Profile no que os documentos precisam, no idioma pedido."""
    def pick(base: str) -> str:
        return profile.get(f"{base}_{lang}") or profile.get(f"{base}_pt") or ""

    links = profile.get("links", {}) or {}
    return {
        "name": profile.get("name", "Leandro Furtado"),
        "title": pick("title"),
        "location": pick("location"),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "summary": pick("summary"),
        "highlight": pick("highlight"),
        "site": "leandrofurtado.com.br",
        "linkedin": links.get("linkedin", ""),
        "whatsapp": links.get("whatsapp", ""),
        "photo": profile.get("photo", ""),
        "experience": profile.get("experience", []),
        "education": profile.get("education", []),
        "skills": profile.get("skills", []),
        "awards": profile.get("awards", []),
        "certs": profile.get("certs", []),
        "clients": profile.get("clients", []),
    }


def _labels(lang: str) -> dict:
    if lang == "en":
        return {"summary": "Summary", "experience": "Experience", "education": "Education", "skills": "Skills",
                "awards": "Awards", "certs": "Certifications", "clients": "Brands and clients I served",
                "contact": "Contact", "updated": "Résumé updated on"}
    return {"summary": "Resumo", "experience": "Experiência", "education": "Formação acadêmica", "skills": "Habilidades",
            "awards": "Prêmios", "certs": "Certificações", "clients": "Marcas e clientes que atendi",
            "contact": "Contato", "updated": "Currículo atualizado em"}


def _certs_by_org(certs: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for cert in certs:
        groups.setdefault(cert.get("org", "—"), []).append(cert)
    return groups


def _photo_stream(photo_rel: str) -> io.BytesIO | None:
    """Carrega a foto do Profile (a mesma do site/admin: Perfil → foto) pro
    cabeçalho do PDF. Corta pro quadrado central — o mesmo object-fit:cover
    do `.about-photo` no site — e converte pra JPEG em memória (a lib de PDF
    só embute JPEG/PNG; se o arquivo cadastrado for WebP, o Pillow, já
    dependência do projeto, resolve). Tons de cinza: o mesmo estado de
    repouso do `.about-photo` (colorido só no hover, que não existe em
    papel). Sem foto cadastrada, ou se o arquivo não abrir por qualquer
    motivo, devolve None — o cabeçalho degrada pro layout só-texto, nunca
    um buraco."""
    if not photo_rel:
        return None
    from ..config import settings
    caminho = settings.upload_dir / photo_rel
    if not caminho.is_file():
        return None
    try:
        from PIL import Image
        img = Image.open(caminho).convert("RGB")
        lado = min(img.size)
        esquerda = (img.width - lado) // 2
        topo = (img.height - lado) // 2
        img = img.crop((esquerda, topo, esquerda + lado, topo + lado)).convert("L").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _desenhar(profile: dict, lang: str = "pt") -> bytes:
    from fpdf import FPDF
    from fpdf.enums import Align, MethodReturnValue, XPos, YPos

    d, L = _fields(profile, lang), _labels(lang)
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(17, 16, 17)
    pdf.set_title(f"{d['name']} — {d['title']}")
    pdf.set_lang("pt-BR" if lang == "pt" else "en")

    for fam, (regular, bold) in FONTS.items():
        pdf.add_font(fam, "", str(FONT_DIR / regular))
        pdf.add_font(fam, "B", str(FONT_DIR / bold))

    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin
    L_MARGIN = pdf.l_margin

    # -------------------------------------------------------- utilitários

    KICKER_H = 17  # gap_before(8) + linha(5) + gap_after(4) — pro cálculo de keep_together

    def kicker(text: str, gap_before=8, gap_after=4):
        """Rótulo de seção: mono caps, letter-spacing, cor --muted — o
        mesmo tratamento de .mono-label no site."""
        pdf.ln(gap_before)
        pdf.set_font("MSsb", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_char_spacing(0.9)
        pdf.set_x(L_MARGIN)
        pdf.cell(0, 5, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_char_spacing(0)
        pdf.ln(gap_after)

    def rule(gap_before=3, gap_after=5, color=LINE):
        pdf.ln(gap_before)
        pdf.set_draw_color(*color)
        pdf.set_line_width(.2)
        y = pdf.get_y()
        pdf.line(L_MARGIN, y, L_MARGIN + W, y)
        pdf.ln(gap_after)

    def body(text: str, size=9.7, style="", color=INK, height=4.7, x=None, w=None, align=Align.L):
        pdf.set_font("MS", style, size)
        pdf.set_text_color(*color)
        pdf.set_xy(x if x is not None else L_MARGIN, pdf.get_y())
        pdf.multi_cell(w if w is not None else W, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)

    def icon(kind: str, x: float, y: float, size: float = 3.0, color=MUTED):
        """Ícones desenhados a traço: sem fonte externa, sempre nítidos —
        o mesmo conjunto que já existia, só recolorido pra paleta clara."""
        pdf.set_draw_color(*color)
        pdf.set_line_width(.25)
        s_ = size
        if kind == "company":
            pdf.rect(x, y, s_ * .78, s_)
            pdf.line(x + s_ * .22, y + s_ * .3, x + s_ * .34, y + s_ * .3)
            pdf.line(x + s_ * .22, y + s_ * .58, x + s_ * .34, y + s_ * .58)
            pdf.line(x + s_ * .48, y + s_ * .3, x + s_ * .6, y + s_ * .3)
            pdf.line(x + s_ * .48, y + s_ * .58, x + s_ * .6, y + s_ * .58)
        elif kind == "period":
            pdf.rect(x, y + s_ * .16, s_ * .9, s_ * .84)
            pdf.line(x, y + s_ * .44, x + s_ * .9, y + s_ * .44)
            pdf.line(x + s_ * .26, y, x + s_ * .26, y + s_ * .3)
            pdf.line(x + s_ * .64, y, x + s_ * .64, y + s_ * .3)
        elif kind == "award":
            pdf.rect(x + s_ * .2, y, s_ * .55, s_ * .5)
            pdf.line(x + s_ * .47, y + s_ * .5, x + s_ * .47, y + s_ * .78)
            pdf.line(x + s_ * .2, y + s_ * .95, x + s_ * .75, y + s_ * .95)
        elif kind == "cert":
            pdf.circle(x + s_ * .45, y + s_ * .4, s_ * .38)
            pdf.line(x + s_ * .25, y + s_ * .72, x + s_ * .3, y + s_ * 1)
            pdf.line(x + s_ * .65, y + s_ * .72, x + s_ * .6, y + s_ * 1)
        elif kind == "edu":     # capelo de formatura, visto de cima
            pdf.line(x, y + s_ * .35, x + s_ * .5, y)
            pdf.line(x + s_ * .5, y, x + s_, y + s_ * .35)
            pdf.line(x + s_, y + s_ * .35, x + s_ * .5, y + s_ * .7)
            pdf.line(x + s_ * .5, y + s_ * .7, x, y + s_ * .35)
            pdf.line(x + s_ * .5, y + s_ * .7, x + s_ * .5, y + s_ * 1.05)

    def chips(tags: list[str], x: float, y: float, max_w: float) -> float:
        """Fileira de chips que quebra linha sozinha quando não cabe mais —
        o mesmo desenho do .xp-tag do site: pílula com fundo --bg-2, mono
        caps pequeno. Devolve o y depois do último chip."""
        pdf.set_font("MSsb", "", 7)
        pdf.set_char_spacing(0.4)
        gap, pad_x, h = 2.2, 2.6, 5.4
        cx, cy = x, y
        for tag in tags:
            tw = pdf.get_string_width(tag.upper()) + pad_x * 2
            if cx + tw > x + max_w and cx > x:
                cx = x
                cy += h + gap
            pdf.set_fill_color(*CHIP_BG)
            pdf.set_draw_color(*CHIP_BG)
            pdf.rect(cx, cy, tw, h, style="F", round_corners=True, corner_radius=h / 2)
            pdf.set_text_color(*SUB)
            pdf.set_xy(cx, cy + 1.15)
            pdf.cell(tw, h - 2, tag.upper(), align=Align.C)
            cx += tw + gap
        pdf.set_char_spacing(0)
        return cy + h

    def chips_height(tags: list[str], max_w: float) -> float:
        """Mesma conta de `chips()`, sem desenhar nada — só pra saber
        quantas linhas a fileira vai usar antes de decidir se cabe."""
        pdf.set_font("MSsb", "", 7)
        gap, pad_x, h = 2.2, 2.6, 5.4
        cx = 0.0
        rows = 1
        for tag in tags:
            tw = pdf.get_string_width(tag.upper()) + pad_x * 2
            if cx + tw > max_w and cx > 0:
                cx = 0
                rows += 1
            cx += tw + gap
        return rows * h + (rows - 1) * gap

    def keep_together(height: float):
        """Bloco que não pode ser cortado ao meio por uma quebra de página
        (um cargo inteiro, um prêmio inteiro) — se não cabe no que sobra da
        página, pula pra próxima ANTES de desenhar, em vez de deixar o
        motor de auto-quebra do fpdf2 cortar no meio do bloco."""
        if pdf.will_page_break(height):
            pdf.add_page()

    GRID_GUTTER = 10

    def two_columns(items, render, top_y: float, gutter=GRID_GUTTER) -> float:
        """Grid editorial de 2 colunas: cada item vai pra coluna mais curta
        no momento (balanceamento guloso) — o mesmo espírito do
        `.cert-groups`/`.skills-grid` em colunas no site (about.html,
        mesma rodada). `render(item, x, y, col_w) -> y_final` desenha um
        item e devolve onde parou; devolve o maior y das duas colunas.

        Fica de fora do controle de quebra de página do fpdf2 (não sabe
        que existem 2 colunas, só empurraria tudo pra próxima igual):
        por isso quem chama precisa garantir com `keep_together`/
        `grid_height` que a grade inteira cabe no que sobra da página
        ANTES de desenhar — nunca no meio."""
        col_w = (W - gutter) / 2
        xs = [L_MARGIN, L_MARGIN + col_w + gutter]
        ys = [top_y, top_y]
        for item in items:
            i = 0 if ys[0] <= ys[1] else 1
            ys[i] = render(item, xs[i], ys[i], col_w) + 6
        return max(ys)

    def grid_height(items, item_h) -> float:
        """Estimativa CONSERVADORA (soma de todos os itens, sem dividir
        pelas 2 colunas) do espaço que uma `two_columns()` vai precisar —
        de propósito mais alta que o necessário: garante que a grade
        inteira cabe na página mesmo no pior caso de desbalanceamento,
        em troca de, às vezes, uma quebra de página um pouco cedo demais.
        Confiável importa mais que aproveitar cada milímetro aqui."""
        col_w = (W - GRID_GUTTER) / 2
        return sum(item_h(item, col_w) + 6 for item in items)

    # -------------------------------------------------------- cabeçalho

    # Foto de perfil (item novo, 19/08): a mesma do site/admin, quadrada e
    # em tons de cinza — o repouso do `.about-photo` no site (colorido só
    # no hover, que papel não tem). Sem foto cadastrada, `foto_buf` é None
    # e o cabeçalho degrada pro layout só-texto de largura cheia, sem buraco.
    foto_buf = _photo_stream(d["photo"])
    PHOTO_SIZE = 28.0
    header_y0 = pdf.get_y()
    header_w = W - (PHOTO_SIZE + 8) if foto_buf else W

    if foto_buf:
        photo_x = L_MARGIN + W - PHOTO_SIZE
        pdf.image(foto_buf, x=photo_x, y=header_y0, w=PHOTO_SIZE, h=PHOTO_SIZE)
        pdf.set_draw_color(*LINE)
        pdf.set_line_width(.3)
        pdf.rect(photo_x, header_y0, PHOTO_SIZE, PHOTO_SIZE)

    pdf.set_font("SG", "B", 27)
    pdf.set_text_color(*INK)
    pdf.set_char_spacing(0.15)
    pdf.set_xy(L_MARGIN, header_y0)
    pdf.multi_cell(header_w, 10.5, d["name"].upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    pdf.set_char_spacing(0)

    pdf.set_font("MS", "", 12)
    pdf.set_text_color(*SUB)
    pdf.set_x(L_MARGIN)
    pdf.multi_cell(header_w, 6.4, d["title"], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)

    # Contato e redes: URLs completas ("https://www.linkedin.com/in/...")
    # não cabem numa linha de A4 mesmo em corpo pequeno — mesmo tratamento
    # do site (vitrine.host_de: sem protocolo, sem www, sem barra final) e
    # multi_cell no lugar de cell, pra quebrar linha sozinho se ainda assim
    # sobrar texto (perfil com mais redes um dia, por exemplo).
    from ..services.vitrine import host_de

    pdf.set_font("MSsb", "", 8.4)
    pdf.set_text_color(*MUTED)
    pdf.set_char_spacing(.3)
    contato = "  ·  ".join(x for x in (d["location"], d["email"], d["phone"], d["site"]) if x)
    pdf.set_x(L_MARGIN)
    pdf.multi_cell(header_w, 5.4, contato.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    # Instagram fora do currículo (ajuste do dono, 19/08): rede social
    # criativa não soma pro recrutador de um currículo de dev/engenharia de
    # IA — LinkedIn e WhatsApp continuam, são canais profissionais.
    social = "  ·  ".join(host_de(x) for x in (d["linkedin"], d["whatsapp"]) if x)
    if social:
        pdf.set_x(L_MARGIN)
        pdf.multi_cell(header_w, 5.4, social.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    pdf.set_char_spacing(0)
    if foto_buf:
        pdf.set_y(max(pdf.get_y(), header_y0 + PHOTO_SIZE + 2))
    rule(gap_before=4, gap_after=2)

    # -------------------------------------------------------- resumo

    if d["summary"]:
        kicker(L["summary"])
        if d["highlight"]:
            # citação de abertura: filete vertical à esquerda (o mesmo
            # gesto do .serif de destaque no site), texto maior, --sub
            y0 = pdf.get_y()
            pdf.set_font("SG", "", 12.5)
            pdf.set_text_color(*SUB)
            pdf.set_xy(L_MARGIN + 4, y0)
            pdf.multi_cell(W - 4, 5.6, d["highlight"], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
            y1 = pdf.get_y()
            pdf.set_draw_color(*LINE)
            pdf.set_line_width(.9)
            pdf.line(L_MARGIN, y0 + 1, L_MARGIN, y1 - 1.5)
            pdf.ln(2.6)
        body(d["summary"])

    # -------------------------------------------------------- experiência

    def _multi_h(text: str, fam: str, style: str, size: float, height: float, w: float) -> float:
        pdf.set_font(fam, style, size)
        return pdf.multi_cell(w, height, text, dry_run=True, output=MethodReturnValue.HEIGHT)

    if d["experience"]:
        kicker(L["experience"])
        for i, xp in enumerate(d["experience"]):
            role = xp.get(f"role_{lang}") or xp.get("role_pt", "")
            linha = xp.get("company", "")
            # `period_en` entrou em 24/08/2026: o campo era único e imprimia
            # "Mar 2024 — Fev 2026" no currículo em inglês. Metade das
            # abreviações de mês coincide nos dois idiomas e a outra metade
            # não, então o defeito passava despercebido numa leitura rápida.
            periodo = xp.get(f"period_{lang}") or xp.get("period", "")
            if periodo:
                linha = f"{linha}   ·   {periodo}" if linha else periodo
            desc = xp.get(f"desc_{lang}") or xp.get("desc_pt", "")
            # Estimativa de altura do bloco inteiro (cargo + empresa/período +
            # descrição + chips), pra decidir ANTES de desenhar se cabe no
            # que sobra da página — um cargo cortado ao meio pela quebra
            # automática do fpdf2 não é diagramação impecável.
            estimativa = _multi_h(role, "MS", "B", 10.6, 5.1, W)
            if linha:
                estimativa += _multi_h(linha.upper(), "MSsb", "", 8, 5, W)
            if desc:
                estimativa += .8 + _multi_h(desc, "MS", "", 9.2, 4.4, W)
            if xp.get("tags"):
                estimativa += 1.6 + chips_height(xp["tags"], W)
            keep_together(estimativa + 4)

            body(role, size=10.6, style="B", height=5.1)
            if linha:
                pdf.set_font("MSsb", "", 8)
                pdf.set_text_color(*MUTED)
                pdf.set_char_spacing(.25)
                pdf.set_x(L_MARGIN)
                pdf.multi_cell(W, 5, linha.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
                pdf.set_char_spacing(0)
            if desc:
                pdf.ln(.8)
                body(desc, size=9.2, color=SUB, height=4.4)
            if xp.get("tags"):
                pdf.ln(1.6)
                y_fim = chips(xp["tags"], L_MARGIN, pdf.get_y(), W)
                pdf.set_y(y_fim)
            if i < len(d["experience"]) - 1:
                rule(gap_before=3.4, gap_after=3.4)

    # -------------------------------------------------------- formação acadêmica
    # Mesmo padrão de prêmios/certificações (ícone + linha em negrito com o
    # período, subtítulo abaixo) — harmônico com a régua da experiência,
    # sem o mecanismo pesado da timeline (2 entradas não pedem).

    if d["education"]:
        kicker(L["education"])
        for edu in d["education"]:
            instituicao = edu.get(f"institution_{lang}") or edu.get("institution_pt", "")
            per_edu = edu.get(f"period_{lang}") or edu.get("period", "")
            linha = instituicao + (f"   ·   {per_edu}" if per_edu else "")
            curso = edu.get(f"course_{lang}") or edu.get("course_pt", "")
            estimativa = _multi_h(linha, "MS", "B", 9.8, 4.8, W - 6.6)
            if curso:
                estimativa += .6 + _multi_h(curso, "MS", "", 8.8, 4.2, W - 6.6)
            keep_together(estimativa + 4)

            y = pdf.get_y()
            icon("edu", L_MARGIN, y + .6, 3.6, INK)
            body(linha, size=9.8, style="B", height=4.8, x=L_MARGIN + 6.6, w=W - 6.6)
            if curso:
                pdf.ln(.6)
                body(curso, size=8.8, color=MUTED, x=L_MARGIN + 6.6, w=W - 6.6, height=4.2)
            pdf.ln(2.4)

    # -------------------------------------------------------- habilidades
    # Grid editorial de 2 colunas — o mesmo `.skills-grid` do site.

    if d["skills"]:
        def _skill_group(group, x, y, col_w):
            pdf.set_font("MS", "B", 9.4)
            pdf.set_text_color(*INK)
            pdf.set_xy(x, y)
            pdf.multi_cell(col_w, 4.6, group.get(f"group_{lang}") or group.get("group_pt", ""),
                            new_x=XPos.LEFT, new_y=YPos.NEXT, align=Align.L)
            y2 = pdf.get_y() + 1.4
            return chips(group.get("items", []), x, y2, col_w)

        def _skill_group_h(group, col_w):
            h = _multi_h(group.get(f"group_{lang}") or group.get("group_pt", ""), "MS", "B", 9.4, 4.6, col_w)
            return h + 1.4 + chips_height(group.get("items", []), col_w)

        # o kicker entra no MESMO cálculo: sem isto, "HABILIDADES" podia
        # ficar sozinho no fim de uma página com a grade inteira na
        # próxima — órfão do jeito que o resto do arquivo evita.
        keep_together(KICKER_H + grid_height(d["skills"], _skill_group_h))
        kicker(L["skills"])
        pdf.set_y(two_columns(d["skills"], _skill_group, pdf.get_y()))

    # -------------------------------------------------------- prêmios

    if d["awards"]:
        kicker(L["awards"])
        for aw in d["awards"]:
            title = aw.get(f"title_{lang}") or aw.get("title_pt", "")
            linha = title + (f"   ·   {aw['year']}" if aw.get("year") else "")
            desc = aw.get(f"desc_{lang}") or aw.get("desc_pt", "")
            estimativa = _multi_h(linha, "MS", "B", 9.8, 4.8, W - 6.6)
            if desc:
                estimativa += .6 + _multi_h(desc, "MS", "", 8.8, 4.2, W - 6.6)
            keep_together(estimativa + 4)

            y = pdf.get_y()
            icon("award", L_MARGIN, y + .8, 3.6, INK)
            body(linha, size=9.8, style="B", height=4.8, x=L_MARGIN + 6.6, w=W - 6.6)
            if desc:
                pdf.ln(.6)
                body(desc, size=8.8, color=MUTED, x=L_MARGIN + 6.6, w=W - 6.6, height=4.2)
            pdf.ln(2.4)

    # -------------------------------------------------------- certificações
    # Mesma ideia do redesenho do /about na mesma rodada: colunas por
    # empresa em vez de uma lista corrida.

    if d["certs"]:
        orgs = list(_certs_by_org(d["certs"]).items())

        def _cert_org(org_items, x, y, col_w):
            org, items = org_items
            pdf.set_font("MSsb", "", 8.6)
            pdf.set_text_color(*INK)
            pdf.set_char_spacing(.3)
            pdf.set_xy(x, y)
            pdf.multi_cell(col_w, 4.6, org.upper(), new_x=XPos.LEFT, new_y=YPos.NEXT, align=Align.L)
            pdf.set_char_spacing(0)
            yy = pdf.get_y() + 1.2
            for cert in items:
                icon("cert", x, yy + .3, 2.6, MUTED)
                linha = cert.get("title", "")
                if cert.get("year"):
                    linha += f"  ·  {cert['year']}"
                pdf.set_font("MS", "", 8.6)
                pdf.set_text_color(*SUB)
                pdf.set_xy(x + 4.6, yy)
                pdf.multi_cell(col_w - 4.6, 4.1, linha, new_x=XPos.LEFT, new_y=YPos.TOP, align=Align.L)
                yy = max(yy + 4.1, pdf.get_y()) + 1.6
            return yy

        def _cert_org_h(org_items, col_w):
            org, items = org_items
            h = _multi_h(org.upper(), "MSsb", "", 8.6, 4.6, col_w) + 1.2
            for cert in items:
                linha = cert.get("title", "") + (f"  ·  {cert['year']}" if cert.get("year") else "")
                h += max(4.1, _multi_h(linha, "MS", "", 8.6, 4.1, col_w - 4.6)) + 1.6
            return h

        keep_together(KICKER_H + grid_height(orgs, _cert_org_h))
        kicker(L["certs"])
        pdf.set_y(two_columns(orgs, _cert_org, pdf.get_y()))

    # -------------------------------------------------------- clientes

    if d["clients"]:
        kicker(L["clients"])
        body("   ·   ".join(d["clients"]), size=9, color=MUTED)

    # -------------------------------------------------------- rodapé

    rule(gap_before=6, gap_after=3)
    pdf.set_font("MSsb", "", 7.4)
    pdf.set_text_color(*MUTED)
    pdf.set_char_spacing(.3)
    hoje = __import__("datetime").date.today().strftime("%d/%m/%Y" if lang == "pt" else "%m/%d/%Y")
    pdf.set_x(L_MARGIN)
    pdf.cell(0, 4.4, f"{L['updated'].upper()} {hoje}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_char_spacing(0)

    out = pdf.output()
    return bytes(out)


# ---------------------------------------------------------------------------

LIMITE_PAGINAS = 3

# Quantas experiências mantêm descrição, em cada tentativa. A primeira é
# "todas"; as seguintes vão cortando das mais antigas para as mais recentes.
DEGRAUS = (None, 10, 8, 6)


def _paginas(pdf_bytes: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf_bytes))


def _sem_descricao_alem_de(profile: dict, quantas: int) -> dict:
    """Cópia do perfil em que só as `quantas` experiências mais recentes
    mantêm descrição. As outras continuam listadas com empresa, cargo e
    período — que é como currículo de verdade trata emprego antigo."""
    copia = dict(profile)
    exps = []
    for i, xp in enumerate(profile.get("experience") or []):
        if i < quantas:
            exps.append(xp)
            continue
        magro = dict(xp)
        magro["desc_pt"] = magro["desc_en"] = ""
        exps.append(magro)
    copia["experience"] = exps
    return copia


def build_pdf(profile: dict, lang: str = "pt") -> bytes:
    """Currículo em PDF, garantido em no máximo três páginas.

    Por que existe este laço, e não um número fixo de experiências:

    Em 24/08/2026 entrou a experiência atual e o currículo foi para QUATRO
    páginas, com a quarta contendo 133 caracteres — só o rodapé. Página quase
    vazia num currículo lê como descuido, e é a última coisa que o recrutador
    vê. Já tinha acontecido de manhã, quando as competências cresceram.

    Cortar texto no perfil resolveria o PDF e empobreceria a página /about, que
    tem espaço de sobra. O corte é decisão de FORMATO, então mora aqui.

    A ordem do sacrifício é a de um currículo bem escrito: emprego recente vem
    descrito, emprego antigo vem listado. Se um dia nem isso bastar, o
    documento sai com quatro páginas em vez de sair errado — melhor uma página
    a mais do que uma experiência amputada no meio.
    """
    saida = _desenhar(profile, lang)
    if _paginas(saida) <= LIMITE_PAGINAS:
        return saida

    for quantas in DEGRAUS[1:]:
        tentativa = _desenhar(_sem_descricao_alem_de(profile, quantas), lang)
        if _paginas(tentativa) <= LIMITE_PAGINAS:
            return tentativa
        saida = tentativa
    return saida



# ---------------------------------------------------------------------------
# FONTES (registro do que foi feito, pra não perder o porquê)
#
# app/static/fonts/{Montserrat,SpaceGrotesk}.woff2 são fontes VARIÁVEIS (eixo
# wght) — o formato certo pra web (@font-face no CSS), mas fpdf2 precisa de
# TTF estático por peso. A conversão (fontTools.varLib.instancer + brotli
# pra descomprimir o woff2) rodou uma vez, offline, e os 5 arquivos gerados
# foram commitados em app/static/fonts/pdf/:
#   Montserrat-Regular.ttf   (wght 400)
#   Montserrat-SemiBold.ttf  (wght 600) — rótulos/kickers
#   Montserrat-Bold.ttf      (wght 700)
#   SpaceGrotesk-Medium.ttf  (wght 500) — nome/títulos
#   SpaceGrotesk-Bold.ttf    (wght 700)
# fontTools e brotli são só ferramenta de build (não entram no requirements.txt
# de produção — o PDF em runtime só usa os .ttf já prontos via fpdf2).
# Licença das fontes: SIL Open Font License 1.1 (Google Fonts), a mesma que já
# valia pros woff2 usados no site — a conversão de formato não muda a licença.
# ---------------------------------------------------------------------------
