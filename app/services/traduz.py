"""Tradução PT→EN dos nomes de categoria, sem depender de serviço externo.

O site em inglês precisa do nome da categoria em inglês, mas digitar isso a cada
cadastro era um campo a mais para preencher e esquecer. O vocabulário de um
portfólio de direção de arte é pequeno e fechado, então uma tabela resolve com
exatidão o que uma tradução automática resolveria por aproximação — e continua
funcionando offline, de graça e para sempre.

Quando o termo não está na tabela, o nome em português vale para os dois idiomas:
melhor repetir do que inventar uma tradução errada. Para ensinar um termo novo,
acrescente uma linha em TERMOS.
"""

from __future__ import annotations

import unicodedata

# frases inteiras primeiro: "identidade visual" não é "identity visual"
FRASES = {
    # "Branding" e não "Visual Identity": é o termo que já está no ar em inglês,
    # e mudar a tradução mudaria o rótulo do portfólio sem ninguém pedir
    "identidade visual": "Branding",
    "direcao de arte": "Art Direction",
    "key visual": "Key Visual",
    "social media": "Social Media",
    "midia social": "Social Media",
    "redes sociais": "Social Media",
    "motion e video": "Motion & Video",
    "motion & video": "Motion & Video",
    "design grafico": "Graphic Design",
    "design de embalagem": "Packaging Design",
    "material de ponto de venda": "Point of Sale",
    "ponto de venda": "Point of Sale",
    "peca grafica": "Print",
    "pecas graficas": "Print",
    "digital e ui": "Digital & UI",
    "digital & ui": "Digital & UI",
    "inteligencia artificial": "Artificial Intelligence",
    "experiencia do usuario": "User Experience",
    "interface do usuario": "User Interface",
    "livro de marca": "Brand Book",
    "manual de marca": "Brand Guidelines",
    "video institucional": "Corporate Video",
    "producao audiovisual": "Audiovisual Production",
}

# palavra a palavra, para o que a tabela de frases não cobre
TERMOS = {
    "embalagem": "Packaging",
    "embalagens": "Packaging",
    "campanha": "Campaign",
    "campanhas": "Campaigns",
    "fotografia": "Photography",
    "foto": "Photo",
    "video": "Video",
    "videos": "Videos",
    "audiovisual": "Audiovisual",
    "marca": "Branding",
    "marcas": "Branding",
    "branding": "Branding",
    "identidade": "Identity",
    "visual": "Visual",
    "grafico": "Graphic",
    "grafica": "Graphic",
    "graficos": "Graphics",
    "graficas": "Graphics",
    "impresso": "Print",
    "impressos": "Print",
    "editorial": "Editorial",
    "ilustracao": "Illustration",
    "ilustracoes": "Illustrations",
    "animacao": "Animation",
    "tipografia": "Typography",
    "logotipo": "Logo",
    "logotipos": "Logos",
    "cartaz": "Poster",
    "cartazes": "Posters",
    "anuncio": "Ad",
    "anuncios": "Ads",
    "publicidade": "Advertising",
    "propaganda": "Advertising",
    "site": "Website",
    "sites": "Websites",
    "digital": "Digital",
    "interface": "Interface",
    "produto": "Product",
    "produtos": "Products",
    "evento": "Event",
    "eventos": "Events",
    "exposicao": "Exhibition",
    "arquitetura": "Architecture",
    "interiores": "Interiors",
    "moda": "Fashion",
    "beleza": "Beauty",
    "alimentos": "Food",
    "bebidas": "Beverages",
    "varejo": "Retail",
    "servico": "Service",
    "servicos": "Services",
    "estrategia": "Strategy",
    "posicionamento": "Positioning",
    "nomeacao": "Naming",
    "roteiro": "Script",
    "direcao": "Direction",
    "arte": "Art",
    "design": "Design",
    "motion": "Motion",
    "social": "Social",
    "media": "Media",
    "conteudo": "Content",
    "lancamento": "Launch",
    "institucional": "Corporate",
    "interno": "Internal",
    "outros": "Other",
    "diversos": "Miscellaneous",
}

# conectores atravessam a tradução sem virar palavra solta
LIGACOES = {"e": "&", "&": "&", "de": "of", "da": "of the", "do": "of the",
            "para": "for", "com": "with", "em": "in", "//": "//", "+": "+", "/": "/"}


def _sem_acento(texto: str) -> str:
    plano = unicodedata.normalize("NFD", texto)
    return "".join(c for c in plano if unicodedata.category(c) != "Mn").lower().strip()


def categoria(nome_pt: str) -> str:
    """Nome em inglês para uma categoria escrita em português.

    Devolve o próprio nome quando não sabe traduzir, que é o comportamento certo
    para nomes próprios: uma categoria chamada "Brasa" continua "Brasa".
    """
    nome = (nome_pt or "").strip()
    if not nome:
        return ""

    chave = _sem_acento(nome)
    if chave in FRASES:
        return FRASES[chave]

    palavras = chave.split()
    traduzidas, acertou = [], False
    for i, p in enumerate(palavras):
        if p in TERMOS:
            traduzidas.append(TERMOS[p])
            acertou = True
        elif p in LIGACOES:
            # "de" no meio de "Design de Embalagem" some: em inglês a ordem já diz
            if p in ("de", "da", "do") and 0 < i < len(palavras) - 1:
                continue
            traduzidas.append(LIGACOES[p])
        else:
            # palavra desconhecida volta como veio, com a caixa original
            traduzidas.append(nome.split()[i] if i < len(nome.split()) else p)

    if not acertou:
        return nome
    return " ".join(traduzidas)
