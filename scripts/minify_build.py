"""Minifica CSS/JS in-place — só roda dentro do build da imagem Docker.

O repositório continua com os fontes legíveis; é a IMAGEM que fica com estes
seis arquivos trocados pela versão minificada, no mesmo caminho (sem mudar
nome nem template). Nunca toca em app/static/vendor/: lenis.min.js já chega
minificado por quem o publicou, re-minificar arrisca quebrar sem ganho.

Uso (dentro do Dockerfile, depois de `COPY app ./app`):
    RUN pip install --no-cache-dir rcssmin rjsmin \
        && python scripts/minify_build.py \
        && pip uninstall -y rcssmin rjsmin
"""
import pathlib

import rcssmin
import rjsmin

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "app" / "static"

CSS = [
    "css/main.css", "css/a11y.css",
    # Lab de Demos (Plano 2) — admin.css fica de fora por decisão pré-
    # existente do repo (admin não é superfície pública de perf); estes
    # 5 são o CSS público do Lab: 4 das demos + vitrine.css (Task 3), a
    # única tela do Lab que é página DO SITE, não das demos.
    "lab/lab-base.css", "lab/lab-moldura.css", "lab/admita.css", "lab/notavel.css", "lab/caderneta.css",
    "lab/vitrine.css",
]
JS = [
    "js/main.js", "js/a11y.js", "js/assinatura.js", "js/consentimento.js",
    # Lab de Demos (Plano 2, Task 4) — miolo da esteira do Admita.
    "lab/admita.js",
]


def _minificar(rel: str, funcao) -> None:
    caminho = RAIZ / rel
    fonte = caminho.read_text(encoding="utf-8")
    antes = len(fonte.encode("utf-8"))
    minificado = funcao(fonte)
    caminho.write_text(minificado, encoding="utf-8")
    depois = len(minificado.encode("utf-8"))
    print(f"  {rel}: {antes:,} -> {depois:,} bytes ({100 - depois * 100 // antes}% menor)")


def main() -> None:
    print("minificando CSS/JS na imagem (fontes no git continuam intactos):")
    for rel in CSS:
        _minificar(rel, rcssmin.cssmin)
    for rel in JS:
        _minificar(rel, rjsmin.jsmin)


if __name__ == "__main__":
    main()
