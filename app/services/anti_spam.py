"""Barreiras anti-bot do formulário de contato.

Por que existe (22/08/2026): o Leandro recebeu spam de robô pelo formulário —
nome "Hi http://leandrofurtado.com.br/fekal0911 Webmaster", texto-modelo em
inglês, WhatsApp de nove dígitos. O formulário tinha honeypot, consentimento e
validação de e-mail, e o bot passou pelos três: honeypot é a primeira coisa que
gerador de spam modernо aprende a pular.

O site não foi invadido. O bot fez o que qualquer visitante pode fazer: digitou
num formulário público. A defesa portanto não é firewall (o VPS já tem UFW,
fail2ban e SSH só por chave); é reconhecer texto de robô ANTES de gravar e de
mandar e-mail.

Três camadas, nesta ordem, cada uma pegando o que a anterior deixa passar:

1. CONTEÚDO (`motivo_de_spam`) — pessoa real não tem URL no nome. Era
   literalmente o caso do spam recebido. Também barra mensagem que é só links.

2. TEMPO (`carimbo`/`carimbo_valido`) — o formulário leva segundos para um
   humano preencher; robô envia na hora. O carimbo vai assinado com a
   secret_key do site (a mesma dos cookies de sessão), então não dá para
   forjar nem reaproveitar de ontem.

3. TAXA (`envio_permitido`) — mesmo desenho do rate limit do login
   (app/auth.py): memória, por IP, sem dependência nova. Um humano manda uma
   mensagem, talvez duas; dez num quarto de hora é ferramenta.

O que se faz com spam detectado: FINGE QUE DEU CERTO (redirect para ?sent=1)
e não grava nada. Devolver erro ensina o operador do bot a ajustar o payload;
sucesso falso o faz ir embora achando que funcionou. Fica um rastro no
registro de atividades para o Leandro ver o que foi barrado no painel.

O que NÃO tem aqui, de propósito:
- CAPTCHA: pune o visitante real, e o Leandro quer contato sem atrito.
- Bloqueio por idioma ou país: cliente real pode escrever em inglês (o site
  tem versão EN) e estar em qualquer lugar.
- Serviço externo de reputação: custo zero é regra do projeto.
"""
import hashlib
import hmac
import re
import time

from ..config import settings
from . import limite

# ---------------------------------------------------------------- conteúdo --

# URL em qualquer forma que apareça em campo de NOME: http(s), www., ou
# domínio nu com TLD ("promo.site.ru"). No nome, qualquer um deles é robô.
_URL = re.compile(r"https?://|www\.|\b[a-z0-9-]{2,}\.[a-z]{2,6}/", re.I)
_LINK = re.compile(r"https?://", re.I)

# Frases-assinatura de spam de formulário: aparecem no começo do texto-modelo
# de campanhas de "web design", "SEO services" e afins. Lista curta e literal
# de propósito — cada entrada barra uma família inteira de campanha, e uma
# lista longa de palavras soltas começaria a pegar gente de verdade.
_MODELOS = (
    "webmaster quer conversar",
    "quer conversar com o webmaster",
    "increase your website traffic",
    "boost your seo",
    "we noticed your website",
)


def motivo_de_spam(nome: str, email: str, mensagem: str) -> str:
    """"" quando parece gente; senão, o motivo — que vai para o registro de
    atividades, para uma decisão errada ser visível e reversível."""
    nome = (nome or "").strip()
    mensagem = (mensagem or "").strip()

    if _URL.search(nome):
        return "URL no campo do nome"

    if len(_LINK.findall(mensagem)) >= 3:
        return "mensagem com 3+ links"

    baixo = f"{nome} {mensagem}".lower()
    for frase in _MODELOS:
        if frase in baixo:
            return f"texto-modelo de campanha ({frase[:30]})"

    return ""


# ------------------------------------------------------------------- tempo --

# Rápido demais é robô; velho demais é replay de um carimbo capturado.
MINIMO_SEGUNDOS = settings.spam_minimo_segundos
MAXIMO_SEGUNDOS = settings.spam_maximo_segundos


def _assinar(ts: str, chave: str) -> str:
    return hmac.new(chave.encode(), ts.encode(), hashlib.sha256).hexdigest()[:24]


def carimbo(chave: str, agora: float | None = None) -> str:
    """Valor do campo oculto `t` do formulário: "timestamp.assinatura"."""
    ts = str(int(agora if agora is not None else time.time()))
    return f"{ts}.{_assinar(ts, chave)}"


def carimbo_valido(valor: str, chave: str, agora: float | None = None) -> bool:
    """Aceita só carimbo assinado por nós, com idade humana.

    Carimbo ausente ou malformado REPROVA: o campo está no template, então só
    não vem quando o robô envia o POST sem nunca ter carregado a página.
    """
    agora = agora if agora is not None else time.time()
    ts, _, assinatura = (valor or "").partition(".")
    if not ts.isdigit() or not assinatura:
        return False
    if not hmac.compare_digest(assinatura, _assinar(ts, chave)):
        return False
    idade = agora - int(ts)
    return MINIMO_SEGUNDOS <= idade <= MAXIMO_SEGUNDOS


# -------------------------------------------------------------------- taxa --

# O contador é COMPARTILHADO entre os workers (services/limite.py). Até
# 24/08/2026 era um dicionário na memória do processo, e com `--workers 2` no
# contêiner o teto efetivo era o dobro do escrito: 3 envios por IP aceitavam
# 6. O comentário antigo aqui chamava isso de "aceito, o objetivo é parar
# rajada" — o que é verdade para rajada e falso para quem tenta de propósito,
# que é justamente o caso que apareceu em 21/08.
MAX_ENVIOS = settings.spam_max_envios
JANELA = settings.spam_janela_segundos


def envio_permitido(ip: str, agora: float | None = None) -> bool:
    return limite.permitir(f"envio:{ip}", MAX_ENVIOS, JANELA, agora)
