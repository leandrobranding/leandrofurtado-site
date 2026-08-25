"""De onde a pessoa está vendo o site.

Serve a duas coisas: mostrar a cidade de quem visita, no lugar de uma cidade
fixa que só falava de mim, e escolher o idioma na primeira visita.

A consulta é feita numa base local (DB-IP Lite, licença CC-BY), não num serviço
de terceiro. Isso importa por três motivos: não custa nada, não depende de um
serviço que pode sumir ou cobrar amanhã, e o IP de quem visita não sai daqui —
o que é bem diferente de mandar o endereço de cada visitante para uma empresa
que eu não controlo.

O IP nunca é guardado. Ele entra, vira "Lisboa, Portugal", e é esquecido.

Se a base não estiver no servidor, tudo aqui devolve vazio e o site funciona
como antes. Nada aqui pode derrubar uma página.
"""

from __future__ import annotations

import re
import threading

from ..config import settings

CAMINHO = "geo/cidades.mmdb"        # dentro de data/
_leitor = None
_tentado = False
_trava = threading.Lock()

# "Berlin (Charlottenburg-Wilmersdorf)" é bairro, não cidade: fora o parêntese
_PARENTESE = re.compile(r"\s*\([^)]*\)\s*$")


def _abrir():
    global _leitor, _tentado
    if _leitor is not None or _tentado:
        return _leitor
    with _trava:
        if _leitor is None and not _tentado:
            _tentado = True
            try:
                import maxminddb
                caminho = settings.data_dir / CAMINHO
                if caminho.exists():
                    # MODE_MMAP: a base tem 124 MB e fica no disco, não na memória
                    _leitor = maxminddb.open_database(str(caminho), maxminddb.MODE_MMAP)
            except Exception:
                _leitor = None
    return _leitor


def ip_confiavel(request) -> str:
    """IP real de quem fez o pedido.

    Ordem de prioridade: X-Real-IP, depois o ÚLTIMO item do X-Forwarded-For,
    depois request.client.host. O nginx sobrescreve X-Real-IP e anexa o IP
    real ao final do X-Forwarded-For antes de repassar o pedido, por isso o
    cliente não consegue forjar esses dois valores. O primeiro item do
    X-Forwarded-For é o que o cliente manda por conta própria e por isso
    nunca é usado como IP real. request.client.host só entra como último
    recurso: em produção o uvicorn roda com forwarded_allow_ips="*" e nesse
    modo confia cegamente no primeiro item do X-Forwarded-For, então esse
    valor só é seguro quando os dois cabeçalhos acima estão ausentes.
    """
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    encaminhado = request.headers.get("x-forwarded-for", "")
    if encaminhado:
        partes = [p.strip() for p in encaminhado.split(",") if p.strip()]
        if partes:
            return partes[-1]
    return (request.client.host if request.client else "") or ""


def ip_do_pedido(request) -> str:
    """IP real de quem pediu, atrás do nginx. Ver ip_confiavel para a lógica."""
    return ip_confiavel(request)


def onde(ip: str, lang: str = "pt") -> dict:
    """{'cidade','pais','iso','lat','lon'} ou dicionário vazio."""
    leitor = _abrir()
    if not leitor or not ip:
        return {}
    try:
        dado = leitor.get(ip)
    except Exception:
        return {}                      # IP malformado
    if not dado:
        return {}                      # rede privada, ou faixa sem registro

    idioma = "pt-BR" if lang == "pt" else "en"
    nomes_cidade = (dado.get("city") or {}).get("names") or {}
    cidade = nomes_cidade.get(idioma) or nomes_cidade.get("en") or ""
    cidade = _PARENTESE.sub("", cidade).strip()

    pais_bruto = dado.get("country") or {}
    nomes_pais = pais_bruto.get("names") or {}
    local = dado.get("location") or {}

    return {
        "cidade": cidade,
        "pais": nomes_pais.get(idioma) or nomes_pais.get("en") or "",
        "iso": pais_bruto.get("iso_code") or "",
        "lat": local.get("latitude"),
        "lon": local.get("longitude"),
    }


def pais_do_ip(ip: str) -> str:
    """Só a sigla do país. Usado para escolher o idioma, onde cidade não importa."""
    leitor = _abrir()
    if not leitor or not ip:
        return ""
    try:
        dado = leitor.get(ip) or {}
    except Exception:
        return ""
    return (dado.get("country") or {}).get("iso_code") or ""
