"""Busca por imagem sem IA e sem custo: comparação visual feita no servidor.

Antes isto mandava a imagem para um modelo de visão, que devolvia palavras-chave
e a busca textual seguia com elas. Funcionava, mas dependia de chave paga e de
uma chamada de rede a cada busca, e o que ele devolvia era uma descrição, não
uma semelhança: uma foto de embalagem azul virava "packaging, blue, product" e
achava qualquer case com essas palavras no texto.

Aqui a comparação é direta, entre a imagem enviada e as imagens dos cases. Duas
medidas se completam:

  Estrutura (dHash) — a imagem vira 9x8 em tons de cinza e cada pixel é comparado
  com o vizinho da direita, gerando 64 bits. O que sobra é o desenho de claro e
  escuro: enquadramento, silhueta, composição. Sobrevive a redimensionamento,
  compressão e mudança de brilho, que é justamente o que muda entre a foto que
  alguém tem na mão e a versão publicada no site.

  Cor — a imagem vira uma grade 4x4 em RGB, 48 números. É a paleta e onde cada
  cor está. Duas peças da mesma campanha batem aqui mesmo com recorte diferente.

Só Pillow, que o projeto já usa para as miniaturas. Nada de numpy, nada de rede.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

LADO_COR = 4          # grade de cor: 4x4 = 48 números
PESO_ESTRUTURA = 0.55  # o desenho pesa um pouco mais que a paleta
PESO_COR = 0.45
# Calibrado contra as 34 imagens que já estão no site. Imagem sem relação
# nenhuma (ruído, cor chapada, formas) não passou de 0.33; a mesma imagem
# recortada ou fotografada da tela ficou em 0.56. O corte fica no meio.
CORTE = 0.55

# Assinatura é cara de calcular e as imagens do site quase nunca mudam.
# A chave leva o mtime junto: trocar o arquivo invalida sozinho.
_cache: dict[str, tuple[float, dict]] = {}


def _abrir(fonte) -> Image.Image:
    img = Image.open(fonte)
    # foto de celular vem com a rotação na EXIF; sem isso a mesma imagem
    # deitada e em pé viram assinaturas diferentes
    return ImageOps.exif_transpose(img)


def assinatura_de(img: Image.Image) -> dict:
    cinza = img.convert("L").resize((9, 8), Image.LANCZOS)
    px = cinza.load()
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)

    cor = img.convert("RGB").resize((LADO_COR, LADO_COR), Image.LANCZOS)
    return {"d": bits, "c": list(cor.tobytes())}


def assinatura_de_bytes(dados: bytes) -> dict | None:
    try:
        return assinatura_de(_abrir(io.BytesIO(dados)))
    except Exception:
        return None       # arquivo corrompido ou formato que o Pillow não abre


def assinatura_de_arquivo(caminho: Path) -> dict | None:
    try:
        mtime = caminho.stat().st_mtime
    except OSError:
        return None
    chave = str(caminho)
    guardado = _cache.get(chave)
    if guardado and guardado[0] == mtime:
        return guardado[1]
    try:
        assinatura = assinatura_de(_abrir(caminho))
    except Exception:
        return None
    _cache[chave] = (mtime, assinatura)
    return assinatura


def semelhanca(a: dict, b: dict) -> float:
    """0 a 1, calibrado com o acervo real do site.

    Duas correções que a versão ingênua deste cálculo não tinha, e sem as quais
    ruído aleatório pontuava mais alto que duas fotos de verdade:

    Estrutura — dois hashes quaisquer já concordam em metade dos bits por puro
    acaso. Tratar isso como "50% parecido" era o erro. Aqui o acaso vale zero:
    a escala vai de 32 bits iguais (nada) a 64 (idêntico).

    Cor — a média das diferenças perdoa demais, porque um desvio grande em
    poucas casas some no meio das outras. A raiz do erro quadrático pune quem
    erra feio numa região, que é justamente o que distingue paletas.
    """
    diferentes = bin(a["d"] ^ b["d"]).count("1")           # distância de Hamming
    estrutura = max(0.0, 2.0 * (1.0 - diferentes / 64.0) - 1.0)

    ca, cb = a["c"], b["c"]
    if len(ca) != len(cb):
        return 0.0
    rms = (sum((x - y) ** 2 for x, y in zip(ca, cb)) / len(ca)) ** 0.5
    cor = max(0.0, 1.0 - rms / 96.0)

    return PESO_ESTRUTURA * estrutura + PESO_COR * cor
