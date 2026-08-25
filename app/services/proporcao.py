"""Proporção real de cada imagem, para a caixa se ajustar a ela.

A galeria do case forçava 16:10 em todo bloco de largura cheia. Numa foto
horizontal isso não aparece. Num cartaz vertical aparece muito: uma peça
2871x4267 entrando numa caixa 16:10 perde 58% da altura, e o que sobra é uma
tira do meio. Sete das catorze peças do primeiro case estavam assim, duas delas
perdendo 72%.

A saída é a caixa seguir a imagem em vez do contrário. Como CSS não lê a
proporção de um arquivo, ela é medida aqui e entra na página como variável.

Duas decisões que evitam o extremo oposto:

- a proporção é limitada. Sem limite, um banner 6:1 vira um fio e uma peça 1:5
  vira uma coluna de três telas de altura.
- peça vertical não ocupa a largura inteira. Um cartaz 2:3 numa coluna de 796px
  teria 1188px de altura, mais que a tela toda. Na metade da largura ele fica
  em 583px e aparece por completo, que é o ponto.
"""

from __future__ import annotations

import struct
from pathlib import Path

# limites da caixa: nem fio, nem torre
MIN, MAX = 0.62, 2.40

# abaixo disto a peça é vertical e vai para meia largura
VERTICAL = 1.15

_cache: dict[tuple[str, float], float] = {}


def _dimensoes(caminho: Path) -> tuple[int, int] | None:
    """Largura e altura lendo só o cabeçalho do arquivo.

    Sem Pillow de propósito: abrir a imagem inteira para saber dois números
    custa memória a cada render, e o cabeçalho já tem o que interessa.
    """
    try:
        with open(caminho, "rb") as f:
            cabeca = f.read(32)
            if cabeca[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", cabeca[16:24])
                return int(w), int(h)
            if cabeca[:2] == b"\xff\xd8":                     # JPEG
                f.seek(2)
                while True:
                    marcador = f.read(2)
                    if len(marcador) < 2 or marcador[0] != 0xFF:
                        return None
                    if marcador[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                                       0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return int(w), int(h)
                    tamanho = struct.unpack(">H", f.read(2))[0]
                    f.seek(tamanho - 2, 1)
            if cabeca[:4] == b"RIFF" and cabeca[8:12] == b"WEBP":
                f.seek(12)
                bloco = f.read(8)
                tipo = bloco[:4]
                dados = f.read(24)
                if tipo == b"VP8X":
                    w = int.from_bytes(dados[4:7], "little") + 1
                    h = int.from_bytes(dados[7:10], "little") + 1
                    return w, h
                if tipo == b"VP8 ":
                    return (int.from_bytes(dados[6:8], "little") & 0x3FFF,
                            int.from_bytes(dados[8:10], "little") & 0x3FFF)
                if tipo == b"VP8L":
                    b = int.from_bytes(dados[1:5], "little")
                    return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    except (OSError, struct.error, IndexError):
        return None
    return None


def de(caminho: Path) -> float:
    """Proporção já limitada, pronta para virar `aspect-ratio`.

    Devolve 0 quando não dá para medir, e aí o template mantém o padrão antigo.
    Guardado por caminho + data de modificação, como as escalas de logotipo.
    """
    try:
        chave = (str(caminho), caminho.stat().st_mtime)
    except OSError:
        return 0.0
    if chave in _cache:
        return _cache[chave]

    dim = _dimensoes(caminho)
    valor = 0.0
    if dim and dim[1] > 0:
        valor = round(min(MAX, max(MIN, dim[0] / dim[1])), 3)
    _cache[chave] = valor
    return valor


def e_vertical(caminho: Path) -> bool:
    """Peça que só cabe inteira em meia largura."""
    p = de(caminho)
    return 0 < p < VERTICAL
