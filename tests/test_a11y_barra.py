"""Remoção do "Leitor de Site" da barra de acessibilidade (rodada 2, 19/08,
adendo final).

Palavras do Leandro: "é ruim, não tem dinâmica, didática, fonética". O botão
some e, com ele, todo código que só existia para servi-lo (síntese de voz no
a11y.js, o marcador `.a11y-lendo`, os textareas de transporte ler/pausar/
parar). O resto da barra — Libras/VLibras, A+ (fonte), contraste — continua
no ar, sem mudança de comportamento.
"""
import asyncio

from starlette.requests import Request

from app.routers.public import home


def _get(lang: str = "pt") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "raw_path": b"/", "query_string": b"", "headers": [],
        "state": {"clean_path": "/", "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def _home(db, lang: str = "pt") -> str:
    resp = asyncio.run(home(_get(lang), db))
    return resp.body.decode()


def test_leitor_de_site_nao_aparece_mais_na_barra_pt(db):
    corpo = _home(db, "pt")
    assert "Leitor de site" not in corpo
    assert "leitor" not in corpo  # nem o data-a11y-quick="leitor" nem data-a11y-alterna="leitor"


def test_screen_reader_nao_aparece_mais_na_barra_en(db):
    corpo = _home(db, "en")
    assert "Screen reader" not in corpo


def test_resto_da_barra_continua_no_ar(db):
    """Libras, tamanho de fonte (A+) e contraste — os três atalhos diretos
    que sobraram — continuam presentes e funcionais no HTML."""
    corpo = _home(db, "pt")
    assert 'data-a11y-quick="libras"' in corpo
    assert 'data-a11y-quick="fonte"' in corpo
    assert 'data-a11y-quick="contraste"' in corpo
    assert 'data-a11y-alterna="libras"' in corpo
    # a estrutura da página e o destaque de links, no grupo de navegação, também seguem
    assert 'data-a11y-alterna="estrutura"' in corpo
    assert 'data-a11y-alterna="links"' in corpo


def test_nenhum_gancho_orfao_de_leitor_no_js_ou_css():
    js = open("app/static/js/a11y.js", encoding="utf-8").read()
    css = open("app/static/css/a11y.css", encoding="utf-8").read()
    for termo in ("leitor", "speechSynthesis", "SpeechSynthesis", "a11y-lendo",
                  "a11y-transporte", "vozBoa", "juntarBlocos", "comecarLeitura",
                  "pararLeitura"):
        assert termo not in js, f"'{termo}' ainda referenciado em a11y.js"
    assert "a11y-transporte" not in css
    assert "a11y-lendo" not in css
