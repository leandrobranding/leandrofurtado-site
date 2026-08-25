"""Prévia de um site, capturada pelo próprio servidor.

Por que aqui e não num serviço de captura: os pagos cobram por imagem e os
gratuitos somem, mudam de regra ou pedem cadastro. O Chromium já sabe fazer
isso sozinho, e rodando aqui a prévia não depende de ninguém.

O peso fica todo no momento da captura, que acontece quando o case é salvo no
painel ou uma vez por semana pelo cron. Para quem visita o site é uma imagem
comum: nenhum custo a mais que uma foto de case.

A captura é do primeiro quadro, em 1440x900, e não da página inteira. Para
capturar a página toda seria preciso abrir o navegador com uma janela de vários
milhares de pixels de altura, e aí todo hero feito com 100vh estica junto: o
site apareceria no portfólio com uma proporção que ele não tem. Entre mostrar
mais e mostrar certo, aqui vale mostrar certo.
"""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import time
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from ..config import settings

PASTA = "sites"           # dentro de uploads
LARGURA = 1440            # viewport de desktop: é assim que o site foi desenhado
ALTURA_JANELA = 900
ALTURA_MAX = 4200         # página muito longa vira um card impossível de rolar
ESPERA_MS = 12000         # tempo para fontes, imagens, vídeo de topo e animação de entrada
LIMITE_S = 75             # se passar disso, o site não vai carregar mesmo


def _chromium() -> str | None:
    for nome in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        caminho = shutil.which(nome)
        if caminho:
            return caminho
    # caminho do Chrome no macOS, para conseguir testar fora do container
    mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return str(mac) if mac.exists() else None


def url_valida(bruto: str) -> str:
    """Só http e https, e sempre com host. Evita file:// e afins."""
    bruto = (bruto or "").strip()
    if not bruto:
        return ""
    if "://" not in bruto:
        bruto = "https://" + bruto
    partes = urlparse(bruto)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return ""
    return bruto


def capturar(url: str, slug: str) -> tuple[str, str]:
    """Devolve (caminho_relativo, erro). Caminho vazio quando não deu."""
    url = url_valida(url)
    if not url:
        return "", "endereço inválido"

    navegador = _chromium()
    if not navegador:
        return "", "Chromium não está instalado neste servidor"

    destino = settings.upload_dir / PASTA
    destino.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        bruto = Path(tmp) / "shot.png"
        comando = [
            navegador, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", "--hide-scrollbars", "--force-color-profile=srgb",
            "--window-size=%d,%d" % (LARGURA, ALTURA_JANELA),
            # Sem isto, herói em <video> nunca começa a tocar no headless e a
            # captura sai com um retângulo preto no lugar da primeira dobra.
            # Foi o que aconteceu com a Coevo.
            "--autoplay-policy=no-user-gesture-required",
            "--screenshot=%s" % bruto,
            "--virtual-time-budget=%d" % ESPERA_MS,
            # sem isto o Chromium tenta escrever no home do usuário do container
            "--user-data-dir=%s" % tmp,
            url,
        ]
        # O Chromium grava a imagem e às vezes não encerra sozinho, ficando
        # pendurado até ser morto. Esperar o processo terminar jogava fora uma
        # captura que já estava pronta no disco. Aqui se espera o arquivo, não
        # o processo: assim que o tamanho para de crescer, a captura acabou.
        proc = subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            anterior, estavel, limite = -1, 0, time.monotonic() + LIMITE_S
            while time.monotonic() < limite:
                if proc.poll() is not None:
                    break                          # encerrou por conta própria
                agora = bruto.stat().st_size if bruto.exists() else 0
                if agora > 1000 and agora == anterior:
                    estavel += 1
                    if estavel >= 2:
                        break                      # duas leituras iguais: pronto
                else:
                    estavel = 0
                anterior = agora
                time.sleep(0.4)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

        if not bruto.exists() or bruto.stat().st_size < 1000:
            return "", "não consegui abrir esse endereço"

        try:
            img = Image.open(bruto).convert("RGB")
        except Exception:
            return "", "a captura saiu ilegível"

        # página muito longa vira um card que ninguém termina de rolar
        if img.height > ALTURA_MAX:
            img = img.crop((0, 0, img.width, ALTURA_MAX))

        nome = f"{slug}.webp"
        img.save(destino / nome, "WEBP", quality=82, method=5)

    return f"{PASTA}/{nome}", ""


def atualizar(case) -> str:
    """Captura e grava no case. Devolve o erro, ou string vazia se deu certo."""
    caminho, erro = capturar(case.site_url, case.slug)
    if erro:
        return erro
    case.site_shot = caminho
    case.site_shot_at = dt.datetime.now(dt.timezone.utc)
    return ""
