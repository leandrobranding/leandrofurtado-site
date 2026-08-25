"""Notificações do painel: o sino, a janelinha e a página cheia.

Uma linha do tempo só, misturando o que eu faço no painel com o que o visitante
faz no site. Separar em duas listas obrigaria a olhar dois lugares para
responder a mesma pergunta: o que aconteceu desde a última vez que entrei.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import check_csrf, csrf_token, require_admin
from ..database import get_db
from ..models import Activity

router = APIRouter(prefix="/admin/avisos", tags=["avisos"])

# rótulo e ícone por área, para a lista não ser um paredão de texto igual
AREAS = {
    "case": ("Case", "caso"),
    "categoria": ("Categoria", "cat"),
    "cliente": ("Cliente", "cli"),
    "lead": ("Contato pelo site", "lead"),
    "newsletter": ("Newsletter", "mail"),
    "comentario": ("Comentário", "fala"),
    "mensagem": ("Mensagem", "mail"),
    "campanha": ("Campanha", "mail"),
}


def nao_lidas(db: Session) -> int:
    return db.query(Activity).filter(Activity.lida.is_(False)).count()


def ultimas(db: Session, quantas: int = 5) -> list[Activity]:
    return (db.query(Activity).order_by(Activity.created_at.desc())
            .limit(quantas).all())


@router.get("")
async def pagina(request: Request, db: Session = Depends(get_db), _=Depends(require_admin),
                 area: str = "", origem: str = ""):
    q = db.query(Activity)
    if area in AREAS:
        q = q.filter(Activity.area == area)
    if origem == "site":
        q = q.filter(Activity.do_site.is_(True))
    elif origem == "painel":
        q = q.filter(Activity.do_site.is_(False))

    itens = q.order_by(Activity.created_at.desc()).limit(300).all()

    # agrupado por dia: uma lista corrida de 300 linhas não se lê
    dias: list[tuple[str, list[Activity]]] = []
    for it in itens:
        from ..config import daqui
        chave = daqui(it.created_at).strftime("%d/%m/%Y")
        if not dias or dias[-1][0] != chave:
            dias.append((chave, []))
        dias[-1][1].append(it)

    from ..main import render
    return render(request, "admin/avisos.html", {
        "dias": dias, "total": len(itens), "areas": AREAS,
        "f": {"area": area, "origem": origem},
        "csrf": csrf_token(request),
        "contagens": {
            "site": db.query(Activity).filter(Activity.do_site.is_(True)).count(),
            "painel": db.query(Activity).filter(Activity.do_site.is_(False)).count(),
        },
    })


@router.post("/lidas")
async def marcar_lidas(request: Request, db: Session = Depends(get_db),
                       _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    db.query(Activity).filter(Activity.lida.is_(False)).update({"lida": True})
    db.commit()
    return RedirectResponse(request.headers.get("referer", "/admin/avisos"), status_code=303)


@router.post("/limpar")
async def limpar(request: Request, db: Session = Depends(get_db),
                 _=Depends(require_admin), csrf: str = Form("")):
    check_csrf(request, csrf)
    db.query(Activity).delete()
    db.commit()
    return RedirectResponse("/admin/avisos", status_code=303)
