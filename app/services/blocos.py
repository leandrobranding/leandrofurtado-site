"""Os blocos que montam a página de um case.

Um case deixou de ser "um texto e uma pilha de imagens": é uma sequência de
blocos que a pessoa monta na ordem que quiser — texto, foto, galeria, vídeo,
reels, áudio, ficha técnica, números, citação. Cada bloco é uma linha em
`media_items`, com o tipo em `kind`, o arquivo ou endereço em `src` e o resto
do conteúdo em `meta`.

O formulário do painel envia a lista inteira em JSON num campo só. É de
propósito: com um único campo, salvar é atômico (ou entra tudo, ou nada muda),
arrastar para reordenar não precisa falar com o servidor, e não existe estado
intermediário em que metade dos blocos foi gravada e a outra metade não.

Este módulo é o contrato entre os dois lados: define os tipos que existem e
limpa o que chega, porque JSON vindo do navegador é entrada de usuário como
qualquer outra.
"""

from __future__ import annotations

# tipo -> (rótulo, ícone do painel, dica curta)
CATALOGO = {
    "texto":    ("Texto", "texto", "Parágrafos, com um título opcional acima."),
    "image":    ("Foto", "imagem", "Uma imagem, com legenda e largura."),
    "galeria":  ("Galeria", "galeria", "Várias fotos numa grade de 2, 3 ou 4 colunas."),
    "video":    ("Vídeo", "video", "Arquivo de vídeo ou link do YouTube/Vimeo."),
    "reels":    ("Reels", "reels", "Vídeo em pé, 9:16. Arquivo ou link do Instagram."),
    "audio":    ("Áudio", "audio", "Arquivo de áudio ou link do Spotify/SoundCloud."),
    "embed":    ("Link", "elo", "Matéria, post ou qualquer endereço com prévia."),
    "hashtags": ("Hashtags", "hashtag", "As tags da campanha, como pílulas."),
    "ficha":    ("Ficha técnica", "ficha", "Quem fez o quê: função e nome, em pares."),
    "numeros":  ("Números", "barras", "Resultados: o valor grande e o que ele mede."),
    "citacao":  ("Citação", "aspas", "Uma frase em destaque, com autor."),
    "divisor":  ("Divisor", "divisor", "Um respiro entre capítulos, com título opcional."),
}

# blocos que carregam arquivo ou endereço e entram na grade visual
VISUAIS = {"image", "galeria", "video", "reels", "audio", "embed"}

LAYOUTS = ("full", "half", "tall")
COLUNAS = (2, 3, 4)


def _texto(valor, limite: int = 500) -> str:
    return str(valor or "").strip()[:limite]


def _lista(valor) -> list:
    return valor if isinstance(valor, list) else []


def normalizar(bruto) -> list[dict]:
    """Peneira a lista de blocos que veio do formulário.

    Descarta o que não tem tipo conhecido e corta cada campo no tamanho da
    coluna. Devolve dicionários prontos para virar linha de `media_items`.
    """
    saida: list[dict] = []
    for i, item in enumerate(_lista(bruto)):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", ""))
        if kind not in CATALOGO:
            continue

        layout = str(item.get("layout", "full"))
        bloco = {
            "kind": kind,
            "src": _texto(item.get("src"), 500),
            "thumb": _texto(item.get("thumb"), 300),
            "caption_pt": _texto(item.get("caption"), 500),
            "layout": layout if layout in LAYOUTS else "full",
            "sort": i,
            "meta": _meta(kind, item.get("meta") or {}),
        }
        # bloco visual sem arquivo nem endereço é casca vazia: não vai para o ar
        if kind in VISUAIS and kind != "galeria" and not bloco["src"]:
            continue
        if kind == "galeria" and not bloco["meta"].get("fotos"):
            continue
        saida.append(bloco)
    return saida


def _meta(kind: str, meta: dict) -> dict:
    """O conteúdo próprio de cada tipo, cada um com a sua forma."""
    if not isinstance(meta, dict):
        meta = {}

    if kind == "texto":
        return {"titulo": _texto(meta.get("titulo"), 160),
                "corpo": _texto(meta.get("corpo"), 6000)}

    if kind == "galeria":
        fotos = []
        for f in _lista(meta.get("fotos"))[:40]:
            if not isinstance(f, dict) or not f.get("src"):
                continue
            fotos.append({"src": _texto(f.get("src"), 500),
                          "thumb": _texto(f.get("thumb"), 300),
                          "legenda": _texto(f.get("legenda"), 200)})
        col = meta.get("colunas")
        return {"fotos": fotos, "colunas": col if col in COLUNAS else 3}

    if kind == "hashtags":
        tags = []
        for t in _lista(meta.get("tags"))[:40]:
            limpo = _texto(t, 60).lstrip("#").strip()
            if limpo:
                tags.append(limpo)
        return {"tags": tags}

    if kind == "ficha":
        linhas = []
        for linha in _lista(meta.get("linhas"))[:40]:
            if not isinstance(linha, dict):
                continue
            rotulo, valor = _texto(linha.get("rotulo"), 80), _texto(linha.get("valor"), 200)
            if rotulo or valor:
                linhas.append({"rotulo": rotulo, "valor": valor})
        return {"titulo": _texto(meta.get("titulo"), 120), "linhas": linhas}

    if kind == "numeros":
        itens = []
        for n in _lista(meta.get("itens"))[:6]:
            if not isinstance(n, dict):
                continue
            valor, rotulo = _texto(n.get("valor"), 30), _texto(n.get("rotulo"), 80)
            if valor or rotulo:
                itens.append({"valor": valor, "rotulo": rotulo})
        return {"itens": itens}

    if kind == "citacao":
        return {"frase": _texto(meta.get("frase"), 600),
                "autor": _texto(meta.get("autor"), 120)}

    if kind == "divisor":
        return {"rotulo": _texto(meta.get("rotulo"), 80)}

    if kind in ("video", "reels", "audio", "embed"):
        # `fonte` diz de onde vem: "arquivo" (src é caminho em /media) ou
        # "link" (src é endereço externo, e o resto veio do resolvedor de embed)
        fonte = "link" if str(meta.get("fonte")) == "link" else "arquivo"
        guardado = {k: _texto(meta.get(k), 600) for k in
                    ("provider", "embed_url", "title", "image", "site", "url")
                    if meta.get(k)}
        guardado["fonte"] = fonte
        if kind == "audio" and meta.get("capa"):
            guardado["capa"] = _texto(meta.get("capa"), 500)
        return guardado

    return {}


def arquivos_usados(blocos: list[dict]) -> set[str]:
    """Todo caminho de /media citado pelos blocos, para achar o que sobrou."""
    usados: set[str] = set()
    for b in blocos:
        if (b.get("meta") or {}).get("fonte") != "link":
            for chave in ("src", "thumb"):
                if b.get(chave) and not str(b[chave]).startswith("http"):
                    usados.add(b[chave])
        for foto in (b.get("meta") or {}).get("fotos", []):
            for chave in ("src", "thumb"):
                if foto.get(chave):
                    usados.add(foto[chave])
        capa = (b.get("meta") or {}).get("capa")
        if capa and not str(capa).startswith("http"):
            usados.add(capa)
    return usados
