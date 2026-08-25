"""O que é um case e o que é um site, decidido num lugar só.

A categoria "sites" não é um case com página: o trabalho é o site do cliente, e
o clique tem que chegar lá. Isso muda o destino do link, a imagem da capa, o
rótulo do botão e o alvo da aba em toda tela que mostra um card — home,
portfólio, página de cliente, relacionados, próximo case e busca.

Enquanto cada template respondia essa pergunta sozinho, era questão de tempo
até um deles esquecer: foi o que aconteceu no destaque da home, que renderizava
uma moldura vazia porque procurava `cover_image` num case que só tem captura.
"""

from __future__ import annotations


def eh_site(case) -> bool:
    """True quando o card deve levar ao site do cliente, e não a uma página."""
    cat = getattr(case, "category", None)
    return bool(cat and cat.kind == "sites" and getattr(case, "site_url", ""))


def host_de(url: str) -> str:
    """O endereço como se lê em voz alta: sem protocolo, sem www, sem barra."""
    return (url or "").replace("https://", "").replace("http://", "") \
                      .replace("www.", "").rstrip("/")


def host(case) -> str:
    return host_de(getattr(case, "site_url", ""))


def capa(case) -> str:
    """Caminho da imagem do card, ou vazio.

    A capa enviada à mão sempre ganha da captura automática. Nem todo site se
    deixa fotografar: o do Assaí responde com a tela de bloqueio do WAF, e o
    que a captura trouxe foi "Access denied" em vez do site. Quando isso
    acontece, quem resolve é uma imagem enviada pelo painel, e ela precisa
    valer mais que o robô.
    """
    if getattr(case, "cover_image", ""):
        return f"/media/{case.cover_image}"
    if eh_site(case) and getattr(case, "site_shot", ""):
        return f"/media/{case.site_shot}"
    return ""


def destino(case, lp) -> str:
    """Para onde o card leva. `lp` é a função de prefixo de idioma do render."""
    return case.site_url if eh_site(case) else lp(f"/case/{case.slug}")
