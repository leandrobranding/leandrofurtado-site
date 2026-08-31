"""Autenticação do admin: Argon2 + sessão assinada + CSRF + rate limit de login."""
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from .config import settings
from .services import limite

ph = PasswordHasher()

# Rate limit por IP, COMPARTILHADO entre os workers (services/limite.py). Os
# dois números vêm de `config.py`, que os lê do ambiente: o valor em produção
# não é o padrão do repositório.
#
# Era um dicionário na memória do processo até 24/08/2026. Com `--workers 2`
# no contêiner isso dobrava o teto real sem ninguém perceber, e num limite de
# LOGIN o efeito é direto: quem tenta adivinhar senha ganhava o dobro de
# chances por janela.
MAX_ATTEMPTS = settings.login_max_tentativas
WINDOW = settings.login_janela_segundos


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def client_ip(request: Request) -> str:
    from .services.geo import ip_confiavel
    return ip_confiavel(request) or "?"


def login_allowed(request: Request) -> bool:
    return limite.quantos(f"login:{client_ip(request)}", WINDOW) < MAX_ATTEMPTS


def register_attempt(request: Request) -> None:
    limite.registrar(f"login:{client_ip(request)}")


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def check_csrf(request: Request, token: str) -> None:
    expected = request.session.get("csrf", "")
    if not expected or not secrets.compare_digest(expected, token or ""):
        raise HTTPException(status_code=403, detail="CSRF inválido")


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_admin(request: Request):
    """Dependency: exige sessão de admin; redireciona ao login se ausente."""
    user = current_user(request)
    if not user:
        raise HTTPException(
            status_code=307,
            headers={"Location": "/admin/login?next=" + request.url.path},
        )
    return user


def admin_or_redirect(request: Request):
    if not current_user(request):
        return RedirectResponse("/admin/login", status_code=302)
    return None
