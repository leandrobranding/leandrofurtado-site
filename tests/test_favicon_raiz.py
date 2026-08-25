"""/favicon.ico na raiz (22/08/2026).

O site declarava o ícone só por `<link rel="icon">`, que resolve para
navegador. Robô, agregador e leitor de feed pedem /favicon.ico direto, sem
ler a página — e caíam em 404 (três aparições no log de 22/08).

O teste guarda duas coisas que uma pessoa quebraria sem perceber: que a
rota existe e devolve um .ico de verdade, e que o desenho dentro dele é o
MESMO do favicon.svg. São dois arquivos com a mesma marca em formatos
diferentes; se a marca mudar num e não no outro, o site fica com dois
ícones distintos e ninguém nota.
"""
import re
import struct

from starlette.testclient import TestClient

from app.config import BASE_DIR
from app.main import app

ICO = BASE_DIR / "app" / "static" / "img" / "favicon.ico"
SVG = BASE_DIR / "app" / "static" / "img" / "favicon.svg"


def test_favicon_responde_na_raiz():
    with TestClient(app) as cliente:
        r = cliente.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/x-icon"
    # ICO real começa com 00 00 01 00 (reservado, tipo=1 ícone)
    assert r.content[:4] == b"\x00\x00\x01\x00"


def test_favicon_tem_os_tres_tamanhos():
    """16, 32 e 48. Um .ico com uma imagem só fica serrilhado na aba."""
    dados = ICO.read_bytes()
    (quantidade,) = struct.unpack_from("<H", dados, 4)
    larguras = set()
    for i in range(quantidade):
        largura = dados[6 + i * 16]
        larguras.add(largura or 256)   # 0 no formato ICO significa 256
    assert larguras == {16, 32, 48}


def test_favicon_ico_e_svg_desenham_a_mesma_marca():
    """O .ico foi gerado das coordenadas do .svg. Se alguém redesenhar o SVG
    e esquecer o ICO, este teste avisa antes de o site sair com dois ícones."""
    esperados = {
        "57.6 73.8 30.6 73.8 30.6 35.7 40 35.7 40 63.9 59.5 63.9 57.6 73.8",
        "64.9 54.5 49.4 54.5 49.4 45.1 66.6 45.1 64.9 54.5",
        "67.6 35.7 49.4 35.7 49.4 26.3 69.4 26.3 67.6 35.7",
    }
    achados = set(re.findall(r'points="([^"]+)"', SVG.read_text(encoding="utf-8")))
    assert achados == esperados, (
        "favicon.svg mudou. Regere o favicon.ico das novas coordenadas "
        "(o gerador está no commit que criou este teste) e atualize a lista acima."
    )


def test_a_marca_ocupa_o_icone_o_bastante_para_ler_em_16px():
    """Medido em 22/08/2026: sem escala a marca ficava com 39% da largura, o
    que num favicon de 16px vira 6,2 pixels de desenho — no resultado de busca
    em tema escuro isso lia como um círculo apagado. O `transform` do
    favicon.svg leva a altura a 76% do quadrado (12,2px em 16). Este teste
    impede que a escala volte a sumir numa edição futura."""
    svg = SVG.read_text(encoding="utf-8")
    assert "scale(1.6)" in svg, "a escala de apresentação do favicon sumiu"

    # o mesmo desenho, contado nos pixels do .ico de 48
    from PIL import Image
    ico = Image.open(ICO)
    ico.size = (48, 48)
    px = ico.convert("RGB").load()
    linhas = [y for y in range(48)
              if any(px[x, y][0] > 128 for x in range(48))]
    altura = (max(linhas) - min(linhas) + 1) / 48
    assert altura > 0.6, f"marca ocupa só {altura:.0%} da altura do ícone"
