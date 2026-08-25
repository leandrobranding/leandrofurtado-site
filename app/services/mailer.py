"""Envio de e-mail por SMTP, configurado no admin.

Sem credenciais o site não quebra: o lead continua salvo no banco e aparece no
painel; o envio apenas fica pendente (Lead.notified = False).
"""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate


def smtp_ready(smap: dict) -> bool:
    return bool(smap.get("smtp_host") and smap.get("smtp_user") and smap.get("smtp_password"))


def _esc(text: str) -> str:
    return (str(text or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def lead_email_html(lead: dict, site_url: str = "https://leandrofurtado.com.br",
                    socials: dict | None = None) -> str:
    """Aviso de lead novo, no mesmo layout padrão da newsletter.

    Vai para o Leandro, não para o visitante: por isso o rótulo do topo muda e o
    rodapé traz a prova de consentimento em vez do link de descadastro.
    """
    linhas = [("Nome", _esc(lead["name"])),
              ("E-mail", f'<a href="mailto:{_esc(lead["email"])}" style="color:{INK};text-decoration:underline">{_esc(lead["email"])}</a>')]
    if lead.get("whatsapp"):
        digitos = "".join(c for c in lead["whatsapp"] if c.isdigit())
        valor = _esc(lead["whatsapp"])
        if len(digitos) >= 10:
            valor = f'<a href="https://wa.me/{digitos}" style="color:{INK};text-decoration:underline">{valor}</a>'
        linhas.append(("WhatsApp", valor))
    linhas.append(("Recebido em", _esc(lead.get("when", ""))))
    linhas.append(("Origem", _esc(lead.get("source", "contato")) + " · " + _esc(lead.get("lang", "pt")).upper()))

    tabela = "".join(
        f'<tr>'
        f'<td style="padding:7px 0;font:400 10px/1.5 {F_CORPO};color:{MUTED};'
        f'letter-spacing:.14em;text-transform:uppercase;text-align:center">{rot}</td></tr>'
        f'<tr><td style="padding:0 0 12px;font:400 15px/1.5 {F_CORPO};color:{BODY};'
        f'text-align:center">{val}</td></tr>'
        for rot, val in linhas
    )

    mensagem = _esc(lead.get("message", "")).replace("\n", "<br>")
    corpo = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        f' style="margin:0 0 20px">{tabela}</table>'
        f'<div style="margin:0 0 20px;padding:22px 20px;background:{DESTAQUE};'
        f'border:1px solid {LINE};border-radius:12px;font:400 14.5px/1.7 {F_CORPO};'
        f'color:{BODY};text-align:center">{mensagem}</div>'
    )

    rodape = (f'Consentimento registrado: {_esc(lead.get("consent_text", ""))}<br>'
              f'IP {_esc(lead.get("ip", "—"))} · {_esc(lead.get("user_agent", "—"))[:110]}')

    return email_shell(
        f'{lead["name"]} quer conversar', corpo, site_url,
        rotulo="Novo contato", saudacao="Olá jovem!",
        cta_label="Responder agora", cta_url=f'mailto:{lead["email"]}',
        rodape_html=rodape, socials=socials,
        preheader=f'Novo lead pelo site: {lead["name"]}',
    )


def lead_email_text(lead: dict) -> str:
    parts = [
        "NOVO CONTATO PELO SITE",
        "",
        f"Nome: {lead['name']}",
        f"E-mail: {lead['email']}",
    ]
    if lead.get("whatsapp"):
        parts.append(f"WhatsApp: {lead['whatsapp']}")
    parts += [
        f"Recebido em: {lead.get('when', '')}",
        f"Origem: {lead.get('source', 'contato')} · {lead.get('lang', 'pt').upper()}",
        "",
        "MENSAGEM",
        lead.get("message", ""),
        "",
        f"Consentimento: {lead.get('consent_text', '')}",
        f"IP {lead.get('ip', '—')} · {lead.get('user_agent', '—')[:110]}",
    ]
    return "\n".join(parts)


def send_lead_email(smap: dict, lead: dict, site_url: str) -> bool:
    """Envia o lead para o e-mail de cadastro. Retorna False se não configurado/falhou."""
    if not smtp_ready(smap):
        return False
    to_addr = smap.get("lead_email") or smap.get("contact_email") or smap["smtp_user"]
    msg = EmailMessage()
    msg["Subject"] = f"[Site] {lead['name']} quer conversar"
    msg["From"] = formataddr(("Leandro Furtado · Site", smap.get("smtp_from") or smap["smtp_user"]))
    msg["To"] = to_addr
    msg["Reply-To"] = lead["email"]
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(lead_email_text(lead))
    msg.add_alternative(lead_email_html(lead, site_url, smap), subtype="html")

    host = smap["smtp_host"]
    port = int(smap.get("smtp_port") or 587)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as s:
                s.login(smap["smtp_user"], smap["smtp_password"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(smap["smtp_user"], smap["smtp_password"])
                s.send_message(msg)
        return True
    except Exception:
        return False


# ---------- Newsletter / e-mail marketing ----------

# ---------------------------------------------------------------------------
# TEMPLATE PADRÃO DE E-MAIL
#
# Este é o layout oficial de toda comunicação que sai do site: newsletter, aviso
# de lead, e o que vier depois (senha de acesso, área de cliente). O cabeçalho e o
# rodapé são os mesmos em todos, montados por email_shell(). Para criar um e-mail
# novo, monte o miolo em HTML e passe para o shell; não duplique a moldura.
#
# A página é clara porque é assim que Gmail, Outlook e Apple Mail aparecem por
# padrão: o card preto flutua sobre o claro em vez de brigar com ele.
# ---------------------------------------------------------------------------
PAGINA = "#ecebe6"       # fundo da página, fora do card
CARD = "#0d0d0d"         # o box
INK = "#f4f2ed"          # títulos
BODY = "#e6e4df"         # corpo: cinza claro, quase branco
MUTED = "#8f8d87"        # apoio
LINE = "#252523"         # divisores e contornos
DESTAQUE = "#161615"     # fundo de faixa e caixa, quase o preto do card

# As fontes do site. Gmail e Outlook descartam @font-face e caem no fallback, então
# a pilha precisa se sustentar sem elas. Apple Mail e iOS renderizam as reais.
F_TITULO = "'Space Grotesk', Montserrat, 'Helvetica Neue', Arial, sans-serif"
F_CORPO = "Montserrat, 'Helvetica Neue', Arial, sans-serif"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]

# Cliente de e-mail ignora folha de estilo: cada tag do Markdown vira HTML com
# estilo embutido. É por isso que a conversão passa por esta tabela.
_INLINE = {
    "<p>": f'<p style="margin:0 0 16px;font:400 14.5px/1.75 {F_CORPO};color:{BODY};text-align:center">',
    "<h1>": f'<h1 style="margin:28px 0 12px;font:600 20px/1.25 {F_TITULO};color:{INK};letter-spacing:-.01em;text-transform:uppercase;text-align:center">',
    "<h2>": f'<h2 style="margin:28px 0 12px;font:600 17px/1.3 {F_TITULO};color:{INK};letter-spacing:-.01em;text-transform:uppercase;text-align:center">',
    "<h3>": f'<h3 style="margin:22px 0 10px;font:600 12px/1.4 {F_TITULO};color:{MUTED};text-transform:uppercase;letter-spacing:.16em;text-align:center">',
    # lista vira caixa com contorno e fundo escuro, no mesmo espírito dos boxes do site
    "<ul>": (f'<ul style="margin:0 0 20px;padding:22px 20px;list-style:none;'
             f'background:{DESTAQUE};border:1px solid {LINE};border-radius:12px;'
             f'color:{BODY};text-align:center">'),
    "<ol>": (f'<ol style="margin:0 0 20px;padding:22px 20px;list-style:none;'
             f'background:{DESTAQUE};border:1px solid {LINE};border-radius:12px;'
             f'color:{BODY};text-align:center">'),
    # o marcador entra como texto: pseudo-elemento não é confiável em e-mail
    "<li>": f'<li style="margin:0 0 10px;font:400 14.5px/1.7 {F_CORPO};color:{BODY};text-align:center">&bull;&nbsp;',
    # destaque de verdade: sem borda, sem respiro lateral, a faixa toma a coluna inteira
    "<blockquote>": (f'<blockquote style="margin:0 0 22px;padding:22px 0 6px;background:{DESTAQUE};'
                     f'border:0;font:400 14.5px/1.7 {F_CORPO};color:{BODY};text-align:center">'),
    "<strong>": f'<strong style="color:{INK};font-weight:700">',
    "<hr>": f'<hr style="border:0;border-top:1px solid {LINE};margin:26px 0">',
    "<hr />": f'<hr style="border:0;border-top:1px solid {LINE};margin:26px 0">',
    "<code>": f'<code style="background:{DESTAQUE};border-radius:4px;padding:1px 6px;font:400 13px/1.5 Menlo,Consolas,monospace;color:{INK}">',
    '<a href="': f'<a style="color:{INK};text-decoration:underline" href="',
    "<img ": '<img style="max-width:100%;height:auto;border-radius:10px;display:block;margin:0 auto 18px" ',
}


def markdown_to_email(html: str) -> str:
    """Aplica estilo embutido no HTML já convertido do Markdown."""
    for tag, styled in _INLINE.items():
        html = html.replace(tag, styled)
    return html


def unsub_token(email: str, secret: str) -> str:
    import hashlib
    import hmac
    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()[:32]


def _social_row(site_url: str, socials: dict) -> str:
    """Ícones em PNG: cliente de e-mail descarta SVG, então tem que ser bitmap."""
    base = site_url.rstrip("/")
    itens = [("linkedin", socials.get("social_linkedin")),
             ("instagram", socials.get("social_instagram")),
             ("whatsapp", socials.get("social_whatsapp"))]
    celulas = [
        f'<td style="padding:0 8px"><a href="{_esc(url)}" target="_blank">'
        f'<img src="{base}/static/img/mail/{nome}-tile.png" width="26" height="26" alt="{nome}"'
        f' style="display:block;border:0"></a></td>'
        for nome, url in itens if url
    ]
    if not celulas:
        return ""
    return ('<table role="presentation" cellpadding="0" cellspacing="0" align="center"'
            ' style="margin:0 auto"><tr>' + "".join(celulas) + "</tr></table>")


def botao(label: str, url: str) -> str:
    """CTA padrão: pílula clara, larga, centralizada, com seta."""
    if not (label and url):
        return ""
    return (f'<tr><td align="center" style="padding:12px 34px 4px">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" align="center"><tr>'
            f'<td align="center" style="background:{INK};border-radius:999px;min-width:240px">'
            f'<a href="{_esc(url)}" target="_blank" style="display:block;padding:16px 54px;'
            f'font:700 11.5px/1 {F_CORPO};color:{CARD};text-decoration:none;'
            f'letter-spacing:.12em;text-transform:uppercase;white-space:nowrap">{_esc(label)}'
            f'<span style="font-size:14px">&nbsp;&rarr;</span></a>'
            f'</td></tr></table></td></tr>')


# ---------------------------------------------------------------------------
# EDITOR VISUAL: blocos -> HTML
#
# O editor do admin monta uma lista de blocos; aqui cada um vira HTML com o mesmo
# estilo embutido do template padrão. É a única fonte de verdade do visual: o que o
# editor mostra na tela é o que este código gera.
# ---------------------------------------------------------------------------

BLOCOS = {
    "titulo": "Título",
    "texto": "Parágrafo",
    "destaque": "Destaque",
    "lista": "Lista em caixa",
    "imagem": "Imagem",
    "botao": "Botão",
    "divisor": "Divisor",
    "espaco": "Espaço",
}


def bloco_html(b: dict, cores: dict, site_url: str = "") -> str:
    """Um bloco do editor vira HTML pronto para e-mail."""
    ink = cores.get("INK", INK)
    body = cores.get("BODY", BODY)
    muted = cores.get("MUTED", MUTED)
    line = cores.get("LINE", LINE)
    destaque = cores.get("DESTAQUE", DESTAQUE)
    card = cores.get("CARD", CARD)
    tipo = b.get("t", "texto")
    valor = b.get("v", "")

    if tipo == "titulo":
        return (f'<h2 style="margin:26px 0 12px;font:600 17px/1.3 {F_TITULO};color:{ink};'
                f'letter-spacing:-.01em;text-transform:uppercase;text-align:center">{_esc(valor)}</h2>')

    if tipo == "texto":
        # negrito e link em markdown simples, sem trazer o parser inteiro para cá
        import re as _re
        txt = _esc(valor)
        txt = _re.sub(r"\*\*(.+?)\*\*", rf'<strong style="color:{ink};font-weight:700">\1</strong>', txt)
        txt = _re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)",
                      rf'<a href="\2" style="color:{ink};text-decoration:underline">\1</a>', txt)
        txt = txt.replace("\n", "<br>")
        return (f'<p style="margin:0 0 16px;font:400 14.5px/1.75 {F_CORPO};'
                f'color:{body};text-align:center">{txt}</p>')

    if tipo == "destaque":
        linhas = "".join(
            f'<p style="margin:0 0 10px;font:400 14.5px/1.7 {F_CORPO};color:{body};'
            f'text-align:center">{_esc(l)}</p>'
            for l in str(valor).split("\n") if l.strip()
        )
        return (f'<div style="margin:0 0 22px;padding:22px 0 12px;background:{destaque};'
                f'border:0">{linhas}</div>')

    if tipo == "lista":
        itens = valor if isinstance(valor, list) else str(valor).split("\n")
        li = "".join(
            f'<li style="margin:0 0 10px;font:400 14.5px/1.7 {F_CORPO};color:{body};'
            f'text-align:center">&bull;&nbsp;{_esc(i.strip())}</li>'
            for i in itens if str(i).strip()
        )
        return (f'<ul style="margin:0 0 20px;padding:22px 20px;list-style:none;'
                f'background:{destaque};border:1px solid {line};border-radius:12px;'
                f'color:{body};text-align:center">{li}</ul>')

    if tipo == "imagem":
        if not valor:
            return ""
        src = valor if str(valor).startswith("http") else f'{site_url.rstrip("/")}/media/{str(valor).lstrip("/")}'
        return (f'<img src="{_esc(src)}" alt="{_esc(b.get("alt", ""))}" width="520"'
                f' style="width:100%;max-width:520px;height:auto;display:block;'
                f'margin:0 auto 20px;border:0;border-radius:10px">')

    if tipo == "botao":
        url = b.get("url", "")
        if not (valor and url):
            return ""
        return (f'<table role="presentation" cellpadding="0" cellspacing="0" align="center"'
                f' style="margin:6px auto 22px"><tr>'
                f'<td align="center" style="background:{ink};border-radius:999px;min-width:240px">'
                f'<a href="{_esc(url)}" target="_blank" style="display:block;padding:16px 54px;'
                f'font:700 11.5px/1 {F_CORPO};color:{card};text-decoration:none;'
                f'letter-spacing:.12em;text-transform:uppercase;white-space:nowrap">{_esc(valor)}'
                f'<span style="font-size:14px">&nbsp;&rarr;</span></a></td></tr></table>')

    if tipo == "divisor":
        return f'<hr style="border:0;border-top:1px solid {line};margin:24px 0">'

    if tipo == "espaco":
        return '<div style="height:22px;line-height:22px">&nbsp;</div>'

    return ""


def blocks_to_html(blocks: list, cores: dict | None = None, site_url: str = "") -> str:
    """Lista de blocos do editor vira o miolo do e-mail."""
    cores = cores or {}
    return "".join(bloco_html(b, cores, site_url) for b in (blocks or []))


# ---------------------------------------------------------------------------
# RASTREIO
#
# Abertura: imagem de 1px no fim do corpo. Depende do cliente carregar imagem, e
# Gmail e Apple Mail fazem cache ou pré-carregam, então o número serve para
# comparar campanhas, não como verdade absoluta.
# Clique: o link passa por um redirecionamento antes de ir ao destino.
# ---------------------------------------------------------------------------

def track_token(campaign_id: int, email: str, secret: str) -> str:
    import base64
    import hashlib
    import hmac
    cru = f"{campaign_id}:{email}"
    assinatura = hmac.new(secret.encode(), cru.encode(), hashlib.sha256).hexdigest()[:16]
    return base64.urlsafe_b64encode(f"{cru}:{assinatura}".encode()).decode().rstrip("=")


def ler_token(token: str, secret: str) -> tuple[int, str] | None:
    import base64
    import hashlib
    import hmac
    try:
        faltando = "=" * (-len(token) % 4)
        cru = base64.urlsafe_b64decode(token + faltando).decode()
        cid, email, assinatura = cru.rsplit(":", 2)
        esperado = hmac.new(secret.encode(), f"{cid}:{email}".encode(),
                            hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(assinatura, esperado):
            return None
        return int(cid), email
    except Exception:
        return None


def aplicar_rastreio(html: str, campaign_id: int, email: str, site_url: str, secret: str) -> str:
    """Troca os links por redirecionamento e crava o pixel de abertura."""
    import re as _re
    if not campaign_id:
        return html
    base = site_url.rstrip("/")
    token = track_token(campaign_id, email, secret)

    def trocar(m):
        url = m.group(1)
        # descadastro e mailto ficam de fora: não são conteúdo da campanha
        if url.startswith("mailto:") or "/newsletter/cancelar" in url:
            return m.group(0)
        from urllib.parse import quote
        return f'href="{base}/e/c/{token}?u={quote(url, safe="")}"'

    html = _re.sub(r'href="(https?://[^"]+)"', trocar, html)
    pixel = (f'<img src="{base}/e/o/{token}.png" width="1" height="1" alt=""'
             f' style="display:block;width:1px;height:1px;border:0;opacity:0">')
    return html.replace("</body>", f"{pixel}</body>")


def email_shell(titulo: str, corpo_html: str, site_url: str, *,
                rotulo: str = "Newsletter", saudacao: str = "", cta_label: str = "",
                cta_url: str = "", topo_img: str = "", rodape_html: str = "",
                socials: dict | None = None, preheader: str = "", quando=None,
                cores: dict | None = None) -> str:
    """Monta o e-mail no layout padrão. Todo envio do site passa por aqui.

    O miolo (corpo_html) já vem em HTML com estilo embutido; a moldura, o cabeçalho
    com a marca e a data, a assinatura e os ícones são responsabilidade daqui.
    """
    from ..config import agora_daqui
    c = cores or {}
    PAGINA_, CARD_, INK_ = c.get("PAGINA", PAGINA), c.get("CARD", CARD), c.get("INK", INK)
    BODY_, MUTED_, LINE_ = c.get("BODY", BODY), c.get("MUTED", MUTED), c.get("LINE", LINE)
    agora = quando or agora_daqui()   # UTC no servidor dataria o e-mail de amanhã
    data_topo = f"{agora.day:02d} {MESES[agora.month - 1]} {agora.year}"
    base = site_url.rstrip("/")

    saud = (f'<p style="margin:0 0 14px;font:400 15px/1.5 {F_CORPO};color:{MUTED_};'
            f'text-align:center">{_esc(saudacao)}</p>') if saudacao else ""

    imagem = ""
    if topo_img:
        src = topo_img if topo_img.startswith("http") else f'{base}/media/{topo_img.lstrip("/")}'
        imagem = (f'<tr><td style="padding:0"><img src="{_esc(src)}" alt="" width="600"'
                  f' style="width:100%;max-width:600px;height:auto;display:block;border:0"></td></tr>')

    sociais = _social_row(base, socials or {})
    sociais_bloco = (f'<tr><td align="center" style="padding:18px 34px 0">{sociais}</td></tr>'
                     if sociais else "")

    rodape = rodape_html or "Esse é um e-mail automático, não precisa responder."

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{_esc(titulo)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  @font-face {{ font-family:'Space Grotesk'; font-weight:600; font-display:swap;
    src:url('{base}/static/fonts/SpaceGrotesk.woff2') format('woff2'); }}
  @font-face {{ font-family:'Montserrat'; font-weight:400; font-display:swap;
    src:url('{base}/static/fonts/Montserrat.woff2') format('woff2'); }}
  @media only screen and (max-width:620px) {{
    .lf-wrap {{ padding:16px 10px !important; }}
    .lf-pad {{ padding-left:22px !important; padding-right:22px !important; }}
    .lf-title {{ font-size:22px !important; }}
    .lf-head {{ padding:20px 22px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:{PAGINA_};-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{_esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:{PAGINA_}">
<tr><td class="lf-wrap" align="center" style="padding:30px 16px">

  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
         style="max-width:600px;width:100%;background:{CARD_};border-radius:16px;overflow:hidden">

    <!-- CABEÇALHO PADRÃO: marca de um lado, rótulo e data do outro -->
    <tr><td class="lf-head" style="padding:24px 34px;border-bottom:1px solid {LINE_}">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
        <td align="left" style="vertical-align:middle">
          <img src="{base}/static/img/mail/lf-tile.png" width="46" height="46" alt="Leandro Furtado"
               style="display:block;border:0">
        </td>
        <td align="right" style="vertical-align:middle;font:400 10px/1.7 {F_CORPO};
            color:{MUTED_};letter-spacing:.18em;text-transform:uppercase">
          {_esc(rotulo)}<br>
          <span style="color:{INK_};font-weight:700;letter-spacing:.12em">{data_topo}</span>
        </td>
      </tr></table>
    </td></tr>

    {imagem}

    <tr><td class="lf-pad" align="center" style="padding:34px 34px 0;text-align:center">
      {saud}
      <h1 class="lf-title" style="margin:0 0 20px;font:600 26px/1.18 {F_TITULO};
          color:{INK_};letter-spacing:-.02em;text-transform:uppercase;text-align:center">{_esc(titulo)}</h1>
    </td></tr>

    <tr><td class="lf-pad" align="center" style="padding:0 34px 6px;text-align:center">{corpo_html}</td></tr>

    {botao(cta_label, cta_url)}

    <!-- RODAPÉ PADRÃO: divisor, assinatura, redes e aviso -->
    <tr><td class="lf-pad" style="padding:26px 34px 0">
      <hr style="border:0;border-top:1px solid {LINE_};margin:0">
    </td></tr>

    <tr><td align="center" class="lf-pad" style="padding:20px 34px 0;text-align:center">
      <p style="margin:0;font:400 12px/1.7 {F_CORPO};color:{MUTED_};text-align:center">
        <strong style="color:{INK_};font-weight:700">Leandro Furtado</strong> //
        Engenheiro de IA e Diretor de Arte
      </p>
    </td></tr>

    {sociais_bloco}

    <tr><td align="center" class="lf-pad" style="padding:22px 34px 28px;text-align:center">
      <p style="margin:0;font:400 11px/1.7 {F_CORPO};color:#6a6862;text-align:center">{rodape}</p>
    </td></tr>

  </table>

</td></tr></table>
</body></html>"""


def campaign_email_html(camp: dict, site_url: str, unsub_url: str, name: str = "",
                        socials: dict | None = None, quando=None) -> str:
    """Newsletter. O parâmetro name é ignorado: o cadastro só pede o e-mail."""
    rotulo = camp.get("rotulo") or "Newsletter"
    cores = camp.get("cores") or {}
    rodape = (f'Esse é um e-mail automático, não precisa responder.<br>'
              f'<a href="{unsub_url}" style="color:{MUTED};text-decoration:underline">'
              f'Cancelar inscrição</a> a qualquer momento.')
    return email_shell(
        camp.get("subject", ""), camp.get("body_html", ""), site_url,
        rotulo=rotulo, saudacao="Olá jovem!",
        cta_label=camp.get("cta_label", ""), cta_url=camp.get("cta_url", ""),
        topo_img=camp.get("image", ""), rodape_html=rodape,
        socials=socials, preheader=camp.get("preheader", ""), quando=quando,
        cores=cores,
    )


def campaign_email_text(camp: dict, unsub_url: str, name: str = "") -> str:
    """Versão em texto puro. name existe só por compatibilidade e é ignorado."""
    import re
    plain = re.sub(r"<[^>]+>", "", camp.get("body_html", ""))
    plain = plain.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    plain = plain.replace("&bull;", "-").replace("&nbsp;", " ")
    plain = "\n".join(line.strip() for line in plain.splitlines() if line.strip())
    return "\n".join([
        "Olá jovem!", "", camp.get("subject", ""), "", plain, "",
        (f'{camp["cta_label"]}: {camp["cta_url"]}' if camp.get("cta_url") else ""),
        "", "---",
        "Leandro Furtado // Engenheiro de IA e Diretor de Arte",
        "Esse é um e-mail automático, não precisa responder.",
        f"Cancelar inscrição: {unsub_url}",
    ])


def _connect(smap: dict):
    host = smap["smtp_host"]
    port = int(smap.get("smtp_port") or 587)
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, timeout=25, context=ssl.create_default_context())
    else:
        s = smtplib.SMTP(host, port, timeout=25)
        s.starttls(context=ssl.create_default_context())
    s.login(smap["smtp_user"], smap["smtp_password"])
    return s


def send_campaign(smap: dict, camp: dict, recipients: list[dict], site_url: str,
                  secret: str, registrar=None) -> tuple[int, int, str]:
    """Dispara a campanha numa única conexão SMTP.

    recipients: [{"email": ..., "name": ...}]. Retorna (enviados, falhas, erro).
    """
    if not smtp_ready(smap):
        return 0, len(recipients), "SMTP não configurado."
    sender = smap.get("smtp_from") or smap["smtp_user"]
    sent = failed = 0
    try:
        server = _connect(smap)
    except Exception as exc:
        return 0, len(recipients), f"Não consegui conectar no SMTP: {exc}"

    try:
        for r in recipients:
            email = (r.get("email") or "").strip()
            if not email:
                continue
            token = unsub_token(email, secret)
            unsub = f'{site_url.rstrip("/")}/newsletter/cancelar?e={email}&t={token}'
            msg = EmailMessage()
            msg["Subject"] = camp.get("subject", "")
            msg["From"] = formataddr(("Leandro Furtado", sender))
            msg["To"] = email
            msg["Date"] = formatdate(localtime=True)
            msg["List-Unsubscribe"] = f"<{unsub}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
            msg.set_content(campaign_email_text(camp, unsub))
            corpo = campaign_email_html(camp, site_url, unsub, "", smap)
            if camp.get("id"):
                corpo = aplicar_rastreio(corpo, camp["id"], email, site_url, secret)
            msg.add_alternative(corpo, subtype="html")
            try:
                server.send_message(msg)
                sent += 1
                if registrar:
                    registrar(email, "enviado", "")
            except Exception as exc:
                failed += 1
                if registrar:
                    registrar(email, "falhou", str(exc)[:200])
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return sent, failed, ""


def send_welcome_email(smap: dict, camp: dict, para: str, site_url: str, secret: str) -> bool:
    """Manda o e-mail de boas-vindas para quem acabou de assinar.

    É o mesmo motor do disparo em massa, só que para um destinatário: abre a conexão,
    envia e fecha. Retorna False sem barulho se o SMTP não estiver configurado, para
    o cadastro nunca falhar por causa do e-mail.
    """
    if not smtp_ready(smap) or not para:
        return False
    enviados, _, _ = send_campaign(smap, camp, [{"email": para, "name": ""}], site_url, secret)
    return enviados > 0
