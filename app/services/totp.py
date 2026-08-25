"""Verificação em duas etapas (TOTP), compatível com o Google Authenticator.

Implementado à mão em vez de trazer biblioteca: são trinta linhas de RFC 6238 e o
resultado é conferido contra os seis vetores oficiais da própria RFC no teste. Menos
uma dependência para atualizar e auditar num projeto que roda sozinho num VPS.

O segredo fica no banco. Quem tomar o banco toma o segundo fator junto, então isto
protege contra senha vazada e força bruta, não contra invasão do servidor.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PASSO = 30          # segundos por código, o padrão que o app espera
DIGITOS = 6
JANELA = 1          # aceita o código anterior e o seguinte, para relógio desalinhado


def novo_segredo() -> str:
    """Segredo em base32, formato que o Google Authenticator entende."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def codigo_em(segredo: str, momento: float, deslocamento: int = 0) -> str:
    chave = base64.b32decode(segredo.upper() + "=" * (-len(segredo) % 8))
    contador = struct.pack(">Q", int(momento // PASSO) + deslocamento)
    digest = hmac.new(chave, contador, hashlib.sha1).digest()
    inicio = digest[-1] & 0x0F
    trecho = struct.unpack(">I", digest[inicio:inicio + 4])[0] & 0x7FFFFFFF
    return str(trecho % (10 ** DIGITOS)).zfill(DIGITOS)


def confere(segredo: str, codigo: str, momento: float | None = None) -> bool:
    """Compara em tempo constante e aceita a janela de tolerância."""
    if not segredo or not codigo:
        return False
    codigo = "".join(c for c in codigo if c.isdigit())
    if len(codigo) != DIGITOS:
        return False
    agora = momento if momento is not None else time.time()
    for deslocamento in range(-JANELA, JANELA + 1):
        if secrets.compare_digest(codigo_em(segredo, agora, deslocamento), codigo):
            return True
    return False


def uri(segredo: str, usuario: str, emissor: str = "leandrofurtado.com.br") -> str:
    """URI otpauth:// que vira o QR Code lido pelo aplicativo."""
    rotulo = quote(f"{emissor}:{usuario}")
    return (f"otpauth://totp/{rotulo}?secret={segredo}"
            f"&issuer={quote(emissor)}&algorithm=SHA1&digits={DIGITOS}&period={PASSO}")


# ---------- códigos de recuperação ----------
#
# Sem isto, perder o celular é perder o painel para sempre. São guardados com hash,
# como senha, e cada um serve uma vez só.

def novos_codigos_recuperacao(quantos: int = 8) -> list[str]:
    return ["-".join(secrets.token_hex(2) for _ in range(2)) for _ in range(quantos)]


def hash_codigo(codigo: str) -> str:
    return hashlib.sha256(codigo.strip().lower().encode()).hexdigest()


def confere_recuperacao(codigo: str, hashes: list[str]) -> str | None:
    """Retorna o hash consumido quando o código bate, para quem chamou removê-lo."""
    alvo = hash_codigo(codigo)
    for h in hashes:
        if secrets.compare_digest(h, alvo):
            return h
    return None
