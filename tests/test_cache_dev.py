"""A regra de cache do modo desenvolvimento.

Editar um CSS, recarregar e continuar vendo a versão antiga custou horas
nesta sessão. `no-cache` não resolve: ele ainda permite servir do disco
depois de um 304, e um estático já baixado continua valendo enquanto o
`?v=` não mudar. Em desenvolvimento a resposta passa a ser `no-store`, sem
ETag e sem Last-Modified, para não existir 304 nenhum.

Em produção nada disso vale: o estático continua com cache longo, que é o
que sustenta a nota de performance do site.
"""
import importlib

from starlette.testclient import TestClient


def _app_com_debug(monkeypatch, ligado):
    from app.config import settings

    monkeypatch.setattr(settings, "debug", ligado, raising=False)
    import app.main as main

    importlib.reload  # o middleware lê settings.debug em tempo de resposta
    return main.app


def test_em_desenvolvimento_nada_e_guardado(monkeypatch):
    app = _app_com_debug(monkeypatch, True)
    with TestClient(app) as cliente:
        r = cliente.get("/lab")
        assert "no-store" in r.headers.get("cache-control", "")
        assert "etag" not in {k.lower() for k in r.headers}

        estatico = cliente.get("/static/lab/admita.css")
        assert "no-store" in estatico.headers.get("cache-control", "")
        assert "etag" not in {k.lower() for k in estatico.headers}


def test_em_producao_o_estatico_continua_com_cache(monkeypatch):
    app = _app_com_debug(monkeypatch, False)
    with TestClient(app) as cliente:
        estatico = cliente.get("/static/lab/admita.css")
        assert "no-store" not in estatico.headers.get("cache-control", "")

        pagina = cliente.get("/lab")
        # o HTML sempre revalida, mesmo em produção
        assert "no-cache" in pagina.headers.get("cache-control", "")
