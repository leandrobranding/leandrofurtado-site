"""Renovação semanal das prévias dos sites.

Um site muda sem avisar, e uma prévia de um ano atrás mostra um trabalho que
não existe mais. Isto roda pelo cron, de madrugada, e recaptura o que estiver
velho. Uma captura de cada vez: o servidor tem um núcleo só, e duas instâncias
do Chromium ao mesmo tempo derrubariam o site no ar.
"""

from __future__ import annotations

import datetime as dt

from ..database import SessionLocal
from ..models import Case
from .captura import atualizar

IDADE_DIAS = 7


def renovar(forcar: bool = False) -> list[str]:
    linhas = []
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=IDADE_DIAS)
    with SessionLocal() as db:
        cases = db.query(Case).filter(Case.site_url != "").all()
        for case in cases:
            quando = case.site_shot_at
            if quando and quando.tzinfo is None:
                quando = quando.replace(tzinfo=dt.timezone.utc)
            if not forcar and quando and quando > limite:
                continue
            erro = atualizar(case)
            linhas.append(f"{case.slug}: {'ok' if not erro else erro}")
            db.commit()
    return linhas


if __name__ == "__main__":
    import sys
    for linha in renovar(forcar="--forcar" in sys.argv):
        print(linha)
