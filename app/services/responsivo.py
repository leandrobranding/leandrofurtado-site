"""Escada de tamanhos das imagens, e o texto alternativo que falta.

Duas coisas que o site pagava caro e ninguém via.

A primeira é peso. O card de um case tem 503px de largura e recebia um arquivo
de 1920px; o modal abria o original, que num dos cases é um PNG de 7MB. Um case
com catorze peças somava 47MB em disco e mandava alguns megabytes por visita.
Aqui cada imagem enviada ganha versões em 480, 960 e 1600, mais uma cópia
"cheia" em 2400 para o modal, todas em WebP. O navegador escolhe pelo `srcset` e
baixa a que serve, não a maior que existe.

O original continua no disco, intocado. Ele é o arquivo do trabalho e não é o
site que decide apagá-lo; só deixa de ser o que trafega.

A segunda é o texto alternativo. Imagem sem `alt` não é lida por leitor de tela
e não diz nada para o buscador. O compositor tem campo de legenda, mas legenda é
opcional e quase sempre fica vazia. Então quando falta, o texto é montado com o
que o case já sabe: título, cliente e a posição da peça.
"""

from __future__ import annotations

from pathlib import Path

from ..config import settings

# larguras da escada. 480 cobre o card no celular, 960 o card no desktop,
# 1600 a peça de largura cheia, 2400 o modal.
LARGURAS = (480, 960, 1600)
CHEIA = 2400

_cache: dict[tuple[str, float], list[tuple[str, int]]] = {}


def _base(rel: str) -> tuple[Path, str, str] | None:
    """Pasta, prefixo e extensão de uma imagem, ou None se o caminho não serve."""
    if not rel:
        return None
    caminho = settings.upload_dir / rel
    return caminho.parent, caminho.stem, caminho.suffix


def variantes(rel: str) -> list[tuple[str, int]]:
    """As versões existentes desta imagem, como (caminho relativo, largura).

    Guardado por caminho + data de modificação: a lista muda quando a imagem é
    substituída, e não a cada visita.
    """
    if not rel:
        return []
    try:
        original = settings.upload_dir / rel
        chave = (rel, original.stat().st_mtime)
    except OSError:
        return []
    if chave in _cache:
        return _cache[chave]

    partes = _base(rel)
    saida: list[tuple[str, int]] = []
    if partes:
        pasta, prefixo, _ = partes
        # o prefixo já pode ser de uma variante: "foto-ab12-960" vira "foto-ab12"
        for largura in LARGURAS:
            if prefixo.endswith(f"-{largura}"):
                prefixo = prefixo[: -len(f"-{largura}")]
                break
        for largura in LARGURAS + (CHEIA,):
            arquivo = pasta / f"{prefixo}-{largura}.webp"
            if arquivo.exists():
                saida.append((str(arquivo.relative_to(settings.upload_dir)), largura))
    _cache[chave] = saida
    return saida


def srcset(rel: str) -> str:
    """Atributo `srcset` pronto, ou string vazia quando não há escada."""
    v = [(c, l) for c, l in variantes(rel) if l in LARGURAS]
    return ", ".join(f"/media/{c} {l}w" for c, l in v)


def leve(rel: str) -> str:
    """A menor versão existente. Para fundo desfocado, onde nitidez não conta.

    O hero da página de cliente usa a capa borrada em 46px como atmosfera. Servir
    ali a mesma imagem grande da coluna da esquerda é pagar duas vezes por um
    pixel que ninguém vai ver: a de 480 borra igual e pesa uma fração.
    """
    v = [(c, l) for c, l in variantes(rel) if l in LARGURAS]
    if v:
        return f"/media/{min(v, key=lambda cl: cl[1])[0]}"
    return f"/media/{rel}" if rel else ""


def cheia(rel: str) -> str:
    """Endereço da versão para o modal. Cai no original quando não existe."""
    for caminho, largura in variantes(rel):
        if largura == CHEIA:
            return f"/media/{caminho}"
    return f"/media/{rel}" if rel else ""


def alt(legenda: str, titulo: str, cliente: str = "", posicao: int = 0) -> str:
    """Texto alternativo: a legenda quando existe, senão montado do que se sabe.

    Nunca devolve vazio para uma peça de conteúdo. `alt=""` é correto para
    enfeite, e nenhuma imagem que passa por aqui é enfeite.
    """
    legenda = (legenda or "").strip()
    if legenda:
        return legenda
    partes = [p for p in (titulo or "").strip().split() if p]
    base = " ".join(partes) or "Peça do projeto"
    if cliente and cliente.strip().lower() not in base.lower():
        base = f"{base} para {cliente.strip()}"
    return f"{base}, imagem {posicao}" if posicao else base


# ---------------------------------------------------------------------------
# Imagem do card de compartilhamento
# ---------------------------------------------------------------------------

# 1200x630 é o formato que Facebook, LinkedIn, X e WhatsApp esperam. Fora dele
# cada um corta por conta própria, e o corte de cada um é diferente.
OG_W, OG_H = 1200, 630


def og(rel: str) -> str:
    """Caminho da imagem de compartilhamento, gerada sob demanda.

    JPEG e não WebP de propósito: o WhatsApp ainda tropeça em WebP na prévia, e
    prévia que não aparece é pior que arquivo 30% maior.

    Gera uma vez e reaproveita; se algo falhar, devolve o original, que é o
    comportamento de antes.
    """
    if not rel:
        return ""
    origem = settings.upload_dir / rel
    destino = origem.parent / f"{origem.stem}-og.jpg"
    if destino.exists():
        return str(destino.relative_to(settings.upload_dir))
    try:
        from PIL import Image, ImageOps

        with Image.open(origem) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
            # cobre o quadro e corta o excedente, em vez de deformar
            ImageOps.fit(img, (OG_W, OG_H), Image.LANCZOS, centering=(.5, .45)) \
                .save(destino, "JPEG", quality=86, optimize=True, progressive=True)
        return str(destino.relative_to(settings.upload_dir))
    except Exception:
        return rel
