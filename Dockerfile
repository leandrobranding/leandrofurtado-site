FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# UID fixo: o volume ./data do host precisa pertencer a este mesmo uid,
# senão o container não consegue gravar o banco (veja deploy/DEPLOY.md, passo 4).
RUN useradd --create-home --uid 1000 appuser
WORKDIR /srv/app

# Chromium: é ele que gera a prévia dos sites da categoria "sites". Pesa uns
# 400 MB na imagem, e é o preço de não depender de um serviço de captura pago.
# Só roda quando um case é salvo ou no cron semanal; nunca numa visita.
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# rcssmin/rjsmin (pip, BSD) são só desta etapa de build — não entram no
# requirements.txt de runtime. Instalados ANTES de copiar app/: camada
# cacheável por si só (não invalida a cada mudança de código), e se o PyPI
# cair num deploy o build ainda pode reaproveitar esta camada do cache do
# Docker. Falha aqui derruba o build (pip install sai != 0 se não instalar).
RUN pip install --no-cache-dir rcssmin rjsmin

COPY app ./app
COPY scripts/minify_build.py ./scripts/minify_build.py

# Minifica CSS/JS só na imagem: os fontes ficam intactos no git, quem serve
# minificado é a imagem (descartável). rcssmin/rjsmin somem da imagem no fim
# desta camada. Desenvolvimento local (DEBUG) nunca passa por aqui, então
# continua servindo os fontes como estão.
RUN python scripts/minify_build.py \
    && pip uninstall -y --no-cache-dir rcssmin rjsmin \
    && rm -rf ./scripts

RUN mkdir -p /srv/app/data && chown -R appuser:appuser /srv/app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
