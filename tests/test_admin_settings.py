"""Testa o cadastro das credenciais da Cloudflare Stream na tela Configurações.

Cobre a Tarefa 9 do Nodal: o plano manda configurar as quatro chaves no
painel, mas nenhuma tarefa criou os campos. Segue o mesmo padrão de
tests/nodal/test_admin_situacoes.py — monta a Request à mão, sem TestClient
nem servidor, e chama as funções da rota direto.
"""
import pytest
import asyncio
from urllib.parse import urlencode

from starlette.requests import Request

# O Nodal é opcional desde 24/08/2026 (ver app/main.py). Este arquivo importa
# o módulo, então ele inteiro é pulado quando a pasta app/nodal/ não existe.
# `importorskip` e não `pytestmark`: a marca pula os TESTES, mas o import do
# topo já teria estourado antes, na coleta.
pytest.importorskip("app.nodal", reason="módulo app.nodal ausente nesta cópia")

from app.nodal import stream
from app.routers.admin import settings_map, settings_page, settings_save, set_setting



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


PEM_FALSO = "-----BEGIN PRIVATE KEY-----\nMIIB...linha1\nlinha2\n-----END PRIVATE KEY-----"


def test_quatro_chaves_gravadas_quando_preenchidas(db):
    request = _post_de("/admin/settings", {
        "csrf": "teste-csrf",
        "cf_account_id": "conta-123",
        "cf_api_token": "token-abc",
        "cf_stream_key_id": "chave-id-1",
        "cf_stream_key_pem": PEM_FALSO,
    })
    resp = asyncio.run(settings_save(request, db))
    assert resp.status_code == 303
    smap = settings_map(db)
    assert smap["cf_account_id"] == "conta-123"
    assert smap["cf_api_token"] == "token-abc"
    assert smap["cf_stream_key_id"] == "chave-id-1"
    assert smap["cf_stream_key_pem"] == PEM_FALSO


def test_pem_vazio_ao_salvar_nao_apaga_a_chave_ja_guardada(db):
    set_setting(db, "cf_stream_key_pem", PEM_FALSO)
    db.commit()
    request = _post_de("/admin/settings", {
        "csrf": "teste-csrf",
        "cf_account_id": "conta-123",
        # cf_stream_key_pem ausente do formulário: campo textarea vazio
    })
    asyncio.run(settings_save(request, db))
    assert settings_map(db)["cf_stream_key_pem"] == PEM_FALSO


def test_caixa_de_remover_apaga_a_chave(db):
    set_setting(db, "cf_stream_key_pem", PEM_FALSO)
    db.commit()
    request = _post_de("/admin/settings", {
        "csrf": "teste-csrf",
        "cf_stream_key_pem_remover": "on",
    })
    asyncio.run(settings_save(request, db))
    assert settings_map(db)["cf_stream_key_pem"] == ""


def test_pem_nunca_aparece_no_html_da_tela_de_configuracoes(db):
    set_setting(db, "cf_stream_key_pem", PEM_FALSO)
    db.commit()
    resp = asyncio.run(settings_page(_get_de("/admin/settings"), db))
    corpo = resp.body.decode()
    assert PEM_FALSO not in corpo
    assert "MIIB...linha1" not in corpo


def test_quatro_chaves_preenchidas_deixam_o_stream_configurado(db):
    set_setting(db, "cf_account_id", "conta-123")
    set_setting(db, "cf_api_token", "token-abc")
    set_setting(db, "cf_stream_key_id", "chave-id-1")
    set_setting(db, "cf_stream_key_pem", PEM_FALSO)
    db.commit()
    assert stream.configurado(settings_map(db)) is True


# ---------- Segredos que ecoavam o valor completo em value= (descoberto na T7 do Lab) ----------
# smtp_password, cf_api_token e ig_access_token seguem agora o mesmo padrão de
# cf_stream_key_pem: indicador "configurado" + últimos 4 caracteres, campo
# vazio no GET, campo vazio no POST mantém, caixa "remover" apaga.

SEGREDOS = ("smtp_password", "cf_api_token", "ig_access_token")


def test_segredos_nunca_aparecem_no_html_da_tela_de_configuracoes(db):
    valores = {chave: f"valor-secreto-de-{chave}-{chave[:3]}9k7z" for chave in SEGREDOS}
    for chave, valor in valores.items():
        set_setting(db, chave, valor)
    db.commit()
    resp = asyncio.run(settings_page(_get_de("/admin/settings"), db))
    corpo = resp.body.decode()
    for chave, valor in valores.items():
        assert valor not in corpo, f"{chave} ecoou o valor completo no HTML"
        # o indicador "configurado" com os últimos 4 caracteres deve aparecer
        assert f"...{valor[-4:]}" in corpo, f"{chave}: indicador 'configurado' não apareceu"


def test_segredos_vazios_ao_salvar_nao_apagam_o_valor_ja_guardado(db):
    for chave in SEGREDOS:
        set_setting(db, chave, f"valor-atual-{chave}")
    db.commit()
    request = _post_de("/admin/settings", {
        "csrf": "teste-csrf",
        "cf_account_id": "conta-123",
        # os três segredos ausentes do formulário: campos type=password vazios
    })
    asyncio.run(settings_save(request, db))
    smap = settings_map(db)
    for chave in SEGREDOS:
        assert smap[chave] == f"valor-atual-{chave}"


def test_segredos_preenchidos_substituem_o_valor_guardado(db):
    for chave in SEGREDOS:
        set_setting(db, chave, f"valor-antigo-{chave}")
    db.commit()
    request = _post_de("/admin/settings", {
        "csrf": "teste-csrf",
        "smtp_password": "senha-nova",
        "cf_api_token": "token-novo",
        "ig_access_token": "ig-token-novo",
    })
    asyncio.run(settings_save(request, db))
    smap = settings_map(db)
    assert smap["smtp_password"] == "senha-nova"
    assert smap["cf_api_token"] == "token-novo"
    assert smap["ig_access_token"] == "ig-token-novo"


def test_caixa_de_remover_apaga_cada_segredo(db):
    for chave in SEGREDOS:
        set_setting(db, chave, f"valor-{chave}")
    db.commit()
    request = _post_de("/admin/settings", {
        "csrf": "teste-csrf",
        "smtp_password_remover": "on",
        "cf_api_token_remover": "on",
        "ig_access_token_remover": "on",
    })
    asyncio.run(settings_save(request, db))
    smap = settings_map(db)
    for chave in SEGREDOS:
        assert smap[chave] == ""
