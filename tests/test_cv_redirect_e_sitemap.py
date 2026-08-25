"""Unificação Currículo + Sobre (pacote de lançamento, 19/08).

/cv virou 301 permanente para /about — preserva SEO e backlinks já indexados
em vez de aprender do zero. /en/cv precisa cair em /en/about pelo mesmo
motivo, e o sitemap não pode listar as duas URLs (isso mandaria o rastreador
para um redirecionamento em vez da página final).

Sobe o app de verdade com TestClient, como tests/test_tracking.py: o
DATA_DIR isolado (tests/conftest.py) garante que isto nunca toca o banco
real do site.
"""
from starlette.testclient import TestClient

from app.main import app as _app


def _subir() -> None:
    with TestClient(_app):
        pass


def test_cv_redireciona_permanentemente_para_about():
    _subir()
    with TestClient(_app, base_url="https://testserver", follow_redirects=False) as client:
        r = client.get("/cv")
    assert r.status_code == 301
    assert r.headers["location"] == "/about"


def test_en_cv_redireciona_permanentemente_para_en_about():
    """O LangMiddleware tira o prefixo /en antes da rota rodar: a rota devolve
    o caminho já prefixado de volta, então /en/cv precisa cair em /en/about,
    nunca em /about puro (perderia o idioma) nem em /cv (não sairia do inglês)."""
    _subir()
    with TestClient(_app, base_url="https://testserver", follow_redirects=False) as client:
        r = client.get("/en/cv")
    assert r.status_code == 301
    assert r.headers["location"] == "/en/about"


def test_cv_download_continua_funcionando_sem_redirecionar():
    """Só a página /cv virou redirect — a geração do PDF é outra rota e
    continua servindo o arquivo direto, sem passar pelo redirecionamento."""
    _subir()
    with TestClient(_app, base_url="https://testserver", follow_redirects=False) as client:
        r = client.get("/cv/download.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_sitemap_nao_lista_cv_mas_lista_about():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/sitemap.xml")
    assert "<loc>https://leandrofurtado.com.br/about</loc>" in r.text
    assert "/cv<" not in r.text
    assert "loc>https://leandrofurtado.com.br/cv<" not in r.text
