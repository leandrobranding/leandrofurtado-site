"""smtp_password também ecoava o valor completo em /admin/newsletter/config —
tela separada de /admin/settings, mesmo SiteSetting (descoberto varrendo os
templates do admin durante o conserto da T7 do Lab, 20/08).

Mesmo padrão dos testes de tests/test_admin_settings.py: monta a Request à
mão e chama as funções da rota direto, sem TestClient nem servidor.
"""
import asyncio
from urllib.parse import urlencode

from starlette.requests import Request

from app.routers.admin import set_setting, settings_map
from app.routers.admin_nl import config, config_salvar


def _post_de(caminho: str, dados: dict) -> Request:
    corpo = urlencode(dados).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": {"csrf": "teste-csrf", "user": "leandro"},
    }
    enviado = False

    async def receive():
        nonlocal enviado
        if enviado:
            return {"type": "http.disconnect"}
        enviado = True
        return {"type": "http.request", "body": corpo, "more_body": False}

    return Request(scope, receive)


def _get_de(caminho: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "headers": [],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": {"csrf": "teste-csrf", "user": "leandro"},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_smtp_password_nunca_aparece_no_html_da_config_de_newsletter(db):
    set_setting(db, "smtp_password", "senha-secreta-9k7z")
    db.commit()
    resp = asyncio.run(config(_get_de("/admin/newsletter/config"), db))
    corpo = resp.body.decode()
    assert "senha-secreta-9k7z" not in corpo
    assert "...9k7z" in corpo


def test_smtp_password_vazio_ao_salvar_config_de_newsletter_mantem(db):
    set_setting(db, "smtp_password", "senha-atual")
    db.commit()
    request = _post_de("/admin/newsletter/config", {
        "csrf": "teste-csrf",
        "smtp_host": "smtp.gmail.com",
        # smtp_password ausente: campo type=password vazio
    })
    asyncio.run(config_salvar(request, db))
    assert settings_map(db)["smtp_password"] == "senha-atual"


def test_smtp_password_preenchido_na_config_de_newsletter_substitui(db):
    set_setting(db, "smtp_password", "senha-antiga")
    db.commit()
    request = _post_de("/admin/newsletter/config", {
        "csrf": "teste-csrf",
        "smtp_password": "senha-nova",
    })
    asyncio.run(config_salvar(request, db))
    assert settings_map(db)["smtp_password"] == "senha-nova"


def test_caixa_de_remover_apaga_smtp_password_na_config_de_newsletter(db):
    set_setting(db, "smtp_password", "senha-atual")
    db.commit()
    request = _post_de("/admin/newsletter/config", {
        "csrf": "teste-csrf",
        "smtp_password_remover": "on",
    })
    asyncio.run(config_salvar(request, db))
    assert settings_map(db)["smtp_password"] == ""
