"""Apoio de servidor para a barra de acessibilidade.

Só existe uma rota: a consulta de palavra. Todo o resto da barra roda no
navegador, sem servidor e sem rede.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WordCache
from ..services import dicionario
from ..services.geo import ip_confiavel

router = APIRouter(prefix="/a11y", tags=["acessibilidade"])

# A rota chama serviço de terceiro, então precisa de freio: sem isto, um script
# apontado para cá viraria um proxy de consultas em nome do meu servidor.
JANELA = 60.0
TETO = 25
_visitas: dict[str, list[float]] = {}


def _liberado(ip: str) -> bool:
    agora = time.monotonic()
    marcas = [t for t in _visitas.get(ip, []) if agora - t < JANELA]
    if len(marcas) >= TETO:
        _visitas[ip] = marcas
        return False
    marcas.append(agora)
    _visitas[ip] = marcas
    if len(_visitas) > 2000:  # o dicionário de controle não pode crescer sem fim
        for chave in [k for k, v in _visitas.items() if not v or agora - v[-1] > JANELA]:
            _visitas.pop(chave, None)
    return True


@router.get("/palavra")
def palavra(request: Request, q: str = "", db: Session = Depends(get_db)):
    lang = "en" if getattr(request.state, "lang", "pt") == "en" else "pt"
    termo = dicionario.normaliza(q)
    if not termo or len(termo) < 2:
        return JSONResponse({"erro": "termo"}, status_code=400)

    guardado = db.get(WordCache, (termo, lang))
    if guardado:
        return guardado.payload

    ip = ip_confiavel(request) or "?"
    if not _liberado(ip):
        return JSONResponse({"erro": "limite"}, status_code=429)

    achado = dicionario.buscar(termo, lang)

    # guarda inclusive o "não achei": evita bater no serviço externo de novo pela
    # mesma palavra inexistente, que é justamente o caso mais repetido
    try:
        db.merge(WordCache(term=termo, lang=lang, payload=achado))
        db.commit()
    except Exception:
        db.rollback()

    return achado
