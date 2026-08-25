"""As ferramentas de cada case, como selos.

Um case diz com o que foi feito: cada programa marcado no painel vira um selo
com o ícone oficial ao lado do case, nas listagens e na página. É informação de
ficha técnica com cara de assinatura — quem é do ofício lê os ícones de longe,
quem não é tem o nome no tooltip.

Os arquivos vivem em app/static/img/programas/, um SVG oficial por programa
(Adobe e ChatGPT vindos do acervo da Wikimedia, Claude do Simple Icons,
Magnific do favicon oficial). Entram dessaturados e ganham a cor original no
hover, que é a regra de toda imagem deste site.

A ordem daqui é a ordem em que os selos aparecem: primeiro o parque Adobe na
ordem clássica do ofício, depois o Figma e as IAs.
"""

from __future__ import annotations

# slug -> nome por extenso (o slug também é o nome do arquivo SVG)
PROGRAMAS: dict[str, str] = {
    "photoshop":    "Adobe Photoshop",
    "illustrator":  "Adobe Illustrator",
    "indesign":     "Adobe InDesign",
    "premiere":     "Adobe Premiere",
    "aftereffects": "Adobe After Effects",
    "audition":     "Adobe Audition",
    "lightroom":    "Adobe Lightroom",
    "figma":        "Figma",
    "claude":       "Claude",
    "chatgpt":      "ChatGPT",
    "magnific":     "Magnific",
}


def do_case(case) -> list[tuple[str, str]]:
    """Os programas de um case, na ordem oficial: [(slug, nome), ...].

    O campo guarda slugs separados por vírgula. Slug desconhecido é ignorado em
    silêncio: um programa que um dia sair da lista não pode quebrar case antigo.
    """
    crus = {p.strip() for p in (getattr(case, "programas", "") or "").split(",")}
    return [(slug, nome) for slug, nome in PROGRAMAS.items() if slug in crus]


def normalizar(valores: list[str]) -> str:
    """O que o formulário mandou, filtrado e na ordem oficial, pronto p/ gravar."""
    marcados = {v.strip() for v in valores}
    return ",".join(slug for slug in PROGRAMAS if slug in marcados)
