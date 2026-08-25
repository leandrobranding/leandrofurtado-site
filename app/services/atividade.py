"""Registro do que acontece, para o sino do painel.

Uma função só, chamada de onde a coisa acontece. É de propósito que ela engula
os próprios erros: um histórico que falha ao gravar não pode impedir alguém de
salvar um case ou de mandar uma mensagem pelo site. O registro é sobre o fato,
nunca o fato em si.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Activity

LIMITE = 500       # acima disto o histórico vira peso morto no banco


def registrar(db: Session, verbo: str, area: str, titulo: str,
              detalhe: str = "", url: str = "", do_site: bool = False) -> None:
    try:
        db.add(Activity(verbo=verbo, area=area, titulo=titulo[:220],
                        detalhe=detalhe[:400], url=url[:300], do_site=do_site))
        db.flush()
        # poda: mantém as últimas LIMITE e descarta o resto de uma vez
        total = db.query(Activity).count()
        if total > LIMITE + 100:
            corte = (db.query(Activity.id)
                     .order_by(Activity.created_at.desc())
                     .offset(LIMITE).limit(1).scalar())
            if corte:
                db.query(Activity).filter(Activity.id <= corte).delete(synchronize_session=False)
    except Exception:
        db.rollback()
