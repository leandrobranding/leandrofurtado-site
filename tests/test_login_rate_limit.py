"""Ponta a ponta da correção de segurança (20/08): o rate limit de login do
admin (MAX_ATTEMPTS por IP, ver app/auth.py) tinha que resistir a um
X-Forwarded-For rotativo, coisa que antes bastava para um script de força
bruta contornar o bloqueio inteiro. Ver também tests/test_ip_confiavel.py.

Sobe o app de verdade com TestClient e base_url="https://testserver": o
cookie de sessão sai Secure fora de debug, e sobre HTTP puro o httpx não
guarda o cookie (mesmo cuidado de tests/test_tracking.py).
"""
import re

from starlette.testclient import TestClient

from app import auth as auth_module
from app.main import app as _app

_CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')


def _csrf(html: str) -> str:
    m = _CSRF_RE.search(html)
    assert m, "campo csrf não encontrado no formulário de login"
    return m.group(1)


def test_rate_limit_do_login_admin_bloqueia_apesar_do_xff_rotativo():
    auth_module._attempts.clear()
    ip_real = "203.0.113.55"

    with TestClient(_app, base_url="https://testserver") as client:
        pagina = client.get("/admin/login")
        csrf = _csrf(pagina.text)

        # MAX_ATTEMPTS tentativas erradas, cada uma com um IP forjado
        # DIFERENTE na posição 0 do X-Forwarded-For, simulando um script que
        # gira o cabeçalho para tentar escapar do rate limit. O IP real (o
        # que o nginx anexaria por último) é sempre o mesmo.
        for i in range(auth_module.MAX_ATTEMPTS):
            resp = client.post(
                "/admin/login",
                data={"csrf": csrf, "username": "nao-existe", "password": "errada"},
                headers={"X-Forwarded-For": f"10.0.0.{i}, {ip_real}"},
            )
            assert "Muitas tentativas" not in resp.text
            assert "Usuário ou senha inválidos" in resp.text

        # a tentativa MAX_ATTEMPTS + 1, com mais um IP forjado novo na
        # posição 0, tem que ser bloqueada: o rate limit segue o último item
        # do XFF (o que o nginx escreveu), não o primeiro (o que o cliente
        # escolheu)
        bloqueada = client.post(
            "/admin/login",
            data={"csrf": csrf, "username": "nao-existe", "password": "errada"},
            headers={"X-Forwarded-For": f"10.0.0.999, {ip_real}"},
        )
        assert "Muitas tentativas" in bloqueada.text


def test_rate_limit_do_login_admin_nao_bloqueia_ip_real_diferente():
    """Controle: um IP real diferente (último item do XFF diferente) não
    herda o bloqueio do teste anterior, provando que o rate limit segue o
    IP de verdade e não algum estado global."""
    auth_module._attempts.clear()
    ip_real = "203.0.113.56"

    with TestClient(_app, base_url="https://testserver") as client:
        pagina = client.get("/admin/login")
        csrf = _csrf(pagina.text)

        resp = client.post(
            "/admin/login",
            data={"csrf": csrf, "username": "nao-existe", "password": "errada"},
            headers={"X-Forwarded-For": f"1.1.1.1, {ip_real}"},
        )
        assert "Muitas tentativas" not in resp.text
        assert "Usuário ou senha inválidos" in resp.text
