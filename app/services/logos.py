"""Equilíbrio óptico dos logotipos numa fileira.

Uma fileira de logos alinhada pela altura mente. "Coca-Cola" é uma assinatura
horizontal: a 30px de altura ela ocupa 100px de largura e se lê. "Coca-Cola
FEMSA" é um lockup empilhado, quase quadrado: à mesma altura ocupa 42px e vira
um borrão.
Alinhar pela altura é fácil de programar e errado de olhar.

O que o olho compara é **área**, não altura. Então a altura de cada logo passa a
depender da proporção dele: quanto mais quadrado, mais alto ele precisa ser para
pesar o mesmo que um vizinho comprido.

Para área constante, altura ∝ 1/√proporção. A conta é essa, com dois limites,
só para o caso extremo: nada abaixo de 55% (senão uma faixa muito comprida vira
um fio) e nada acima de 2,1× (senão o quadrado vira um cartaz no meio da fila).

O piso já foi 90%, e era alto demais: assinatura muito comprida batia no limite
e entrava com quase 40% mais área que as vizinhas — a diferença que se via na
Galeria de Honra entre um lockup quadrado e um nome estendido.

A proporção sai do próprio arquivo, do viewBox. Isso quer dizer que um logo novo
enviado pelo painel entra equilibrado sozinho, sem ninguém ajustar número nenhum.

Só que o viewBox mente com frequência. Exportador de marca costuma cuspir uma
prancheta quadrada — `viewBox="0 0 500 500"` — com o desenho pequeno e centrado
no meio. Aí a conta acima usa a prancheta, não a marca, e o logo entra na fileira
menor que os vizinhos mesmo com a escala "certa". Foi o que aconteceu com o
Bradesco: o desenho ocupava 72% da largura e 60% da altura do quadrado.

Por isso, antes de medir a proporção, aparamos o viewBox até o desenho de fato
(`normalizar`). Roda no envio pelo painel, então marca nova já entra ajustada.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

# proporção de referência: a de uma assinatura horizontal comum. Logos com esta
# proporção ficam na altura base; os mais quadrados crescem a partir daqui.
REFERENCIA = 4.2
MINIMO, MAXIMO = 0.55, 2.1

_cache: dict[tuple[str, float], float] = {}

_VIEWBOX = re.compile(r'viewBox\s*=\s*"([-\d.\s,]+)"', re.I)
_LARGURA = re.compile(r'\bwidth\s*=\s*"([\d.]+)', re.I)
_ALTURA = re.compile(r'\bheight\s*=\s*"([\d.]+)', re.I)


def proporcao(caminho: Path) -> float:
    """Largura dividida por altura, lida do viewBox. 0 quando não dá para saber."""
    try:
        cabeca = caminho.read_text(errors="ignore")[:2000]
    except OSError:
        return 0.0
    m = _VIEWBOX.search(cabeca)
    if m:
        partes = [p for p in re.split(r"[\s,]+", m.group(1).strip()) if p]
        if len(partes) == 4:
            try:
                _, _, w, h = (float(x) for x in partes)
                if w > 0 and h > 0:
                    return w / h
            except ValueError:
                pass
    mw, mh = _LARGURA.search(cabeca), _ALTURA.search(cabeca)
    if mw and mh:
        try:
            w, h = float(mw.group(1)), float(mh.group(1))
            if w > 0 and h > 0:
                return w / h
        except ValueError:
            pass
    return 0.0


def escala(caminho: Path) -> float:
    """Multiplicador de altura para este logo pesar como os vizinhos.

    O resultado é guardado por caminho + data de modificação: trocar o arquivo
    pelo painel recalcula sozinho, e ler o mesmo arquivo mil vezes não custa.
    """
    try:
        chave = (str(caminho), caminho.stat().st_mtime)
    except OSError:
        return 1.0
    if chave in _cache:
        return _cache[chave]

    r = proporcao(caminho)
    valor = 1.0 if r <= 0 else min(MAXIMO, max(MINIMO, math.sqrt(REFERENCIA / r)))
    valor = round(valor, 3)
    _cache[chave] = valor
    return valor


# ---------------------------------------------------------------------------
# Marca reversa: logotipo branco dentro de campo de cor
#
# Estava numa lista fixa de dois slugs no roteador. Lista escrita à mão só
# protege o que já aconteceu: a próxima marca reversa que entrasse pelo painel
# apareceria quebrada até alguém reparar e editar o código. O arquivo já diz o
# que ele é, e é dele que a resposta sai.
#
# O sinal é simples e específico: o desenho usa branco puro E cor de verdade ao
# mesmo tempo. Logotipo comum é monocromático ou colorido sem branco — o branco
# dentro do desenho só existe quando alguma coisa foi vazada em cima de um campo.
# ---------------------------------------------------------------------------

_BRANCO = re.compile(r"(?:fill|stroke)\s*[:=]\s*\"?\s*(?:white\b|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))", re.I)
_HEX = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})\b", re.I)

# Branco de marca quase nunca é #ffffff: a Pravaler entrou com a palavra em
# #fffdf1 e o detector de branco puro respondeu False — a marca caiu no
# tratamento padrão e virou um retângulo sem letras na home, no ar. Qualquer
# canal ≥ 240 ainda é branco para quem olha, e fica longe do cinza claro de
# desenho (#e0e0e0 = 224), que continua sendo tinta comum.
_PISO_BRANCO = 240


def _branco(hexa: str) -> bool:
    if len(hexa) == 3:
        hexa = "".join(c * 2 for c in hexa)
    return min(int(hexa[i:i + 2], 16) for i in (0, 2, 4)) >= _PISO_BRANCO


def _cinza(hexa: str) -> bool:
    """True para preto, branco e qualquer cinza: R, G e B praticamente iguais."""
    if len(hexa) == 3:
        hexa = "".join(c * 2 for c in hexa)
    r, g, b = (int(hexa[i:i + 2], 16) for i in (0, 2, 4))
    return max(r, g, b) - min(r, g, b) <= 12


_cache_reversa: dict[tuple[str, float], bool] = {}


def reversa(caminho) -> bool:
    """O logotipo é vazado sobre campo de cor?

    Guardado por caminho + data de modificação, como a escala óptica: a resposta
    muda quando o arquivo é trocado, e não a cada marca desenhada numa página.

    Falha para o lado seguro: em qualquer dúvida devolve False, e a marca recebe
    o tratamento monocromático padrão do site, que funciona para a esmagadora
    maioria dos arquivos.
    """
    try:
        p = Path(caminho)
        if p.suffix.lower() != ".svg":
            return False
        chave = (str(p), p.stat().st_mtime)
    except OSError:
        return False
    if chave in _cache_reversa:
        return _cache_reversa[chave]

    try:
        texto = p.read_text(errors="ignore")
    except OSError:
        return False
    hexes = _HEX.findall(texto)
    tem_branco = bool(_BRANCO.search(texto)) or any(_branco(h) for h in hexes)
    valor = tem_branco and any(not _cinza(h) for h in hexes)
    _cache_reversa[chave] = valor
    return valor


# ---------------------------------------------------------------------------
# Aparo do viewBox: a prancheta vira a marca
# ---------------------------------------------------------------------------

# folga que sobra de cada lado depois do aparo. 2% dá um respiro para traço
# grosso e para o antialias sem soltar o desenho dentro da caixa.
FOLGA = 0.02

# abaixo disso o viewBox está encostado no desenho e não há o que aparar
JA_APARADO = 0.92

_TEXTO = re.compile(r"<\s*(text|tspan)\b", re.I)


def caixa_conteudo(caminho: Path) -> tuple[float, float, float, float] | None:
    """Retângulo que o desenho realmente ocupa, nas unidades do viewBox.

    Devolve None quando não dá para confiar na medida:

    - sem viewBox, não há sistema de coordenadas para devolver;
    - com <text>, porque medir texto exige a fonte instalada e o que sai é a
      caixa de um pedaço só do logo (foi assim que quase apaguei o nome de um
      cliente deixando só o ícone);
    - se o desenho medir mais que o viewBox, sinal de que o arquivo traz
      width/height em outra escala e a leitura saiu em outro sistema.
    """
    try:
        from svgelements import SVG  # dependência opcional: sem ela, nada muda
    except Exception:
        return None

    try:
        bruto = caminho.read_text(errors="ignore")
    except OSError:
        return None
    if _TEXTO.search(bruto):
        return None

    m = _VIEWBOX.search(bruto)
    if not m:
        return None
    partes = [p for p in re.split(r"[\s,]+", m.group(1).strip()) if p]
    if len(partes) != 4:
        return None
    try:
        vx, vy, vw, vh = (float(p) for p in partes)
    except ValueError:
        return None
    if vw <= 0 or vh <= 0:
        return None

    try:
        # a largura/altura do parse vira o viewport: assim o que volta já está
        # nas unidades do viewBox, só deslocado para a origem
        svg = SVG.parse(str(caminho), width=vw, height=vh)
        caixas = [e.bbox() for e in svg.elements() if hasattr(e, "bbox") and e.bbox()]
    except Exception:
        return None
    caixas = [c for c in caixas if c and all(v is not None for v in c)]
    if not caixas:
        return None

    x0 = min(c[0] for c in caixas)
    y0 = min(c[1] for c in caixas)
    largura = max(c[2] for c in caixas) - x0
    altura = max(c[3] for c in caixas) - y0
    if largura <= 0 or altura <= 0:
        return None
    if largura > vw * 1.02 or altura > vh * 1.02:
        return None

    return (x0 + vx, y0 + vy, largura, altura)


def normalizar(caminho: Path) -> bool:
    """Apara o viewBox até o desenho. True quando o arquivo mudou.

    Idempotente: depois de aparado sobra a folga de 2%, que já conta como
    encostado, então rodar de novo não mexe em nada.
    """
    caixa = caixa_conteudo(caminho)
    if not caixa:
        return False
    x, y, largura, altura = caixa

    bruto = caminho.read_text(errors="ignore")
    m = _VIEWBOX.search(bruto)
    if not m:
        return False
    vx, vy, vw, vh = (float(p) for p in re.split(r"[\s,]+", m.group(1).strip()) if p)
    if largura / vw >= JA_APARADO and altura / vh >= JA_APARADO:
        return False

    fx, fy = largura * FOLGA, altura * FOLGA
    novo = f'viewBox="{x - fx:.1f} {y - fy:.1f} {largura + 2 * fx:.1f} {altura + 2 * fy:.1f}"'

    saida = bruto[: m.start()] + novo + bruto[m.end():]
    # width/height fixos no arquivo brigam com o viewBox novo e voltam a
    # apertar o desenho; o CSS é quem manda no tamanho aqui
    saida = re.sub(r'(<svg\b[^>]*?)\s+width\s*=\s*"[^"]*"', r"\1", saida, count=1, flags=re.I)
    saida = re.sub(r'(<svg\b[^>]*?)\s+height\s*=\s*"[^"]*"', r"\1", saida, count=1, flags=re.I)
    caminho.write_text(saida)
    _cache.clear()
    _cache_reversa.clear()
    return True
