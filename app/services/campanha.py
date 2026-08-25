"""Monta o que o mailer precisa para renderizar uma campanha.

Existe para ser o único lugar que faz isso. Antes o admin montava de um jeito e o
envio automático de boas-vindas montava de outro, e o de boas-vindas esquecia o id
da campanha, o que desligava o rastreio de abertura e clique sem ninguém perceber.
"""
from sqlalchemy.orm import Session

from ..models import Campaign, Theme
from . import mailer


def tema_padrao(db: Session) -> Theme | None:
    return (db.query(Theme).filter_by(is_default=True).first()
            or db.query(Theme).order_by(Theme.id).first())


def cores_da(camp: Campaign, db: Session) -> dict:
    tema = camp.theme or tema_padrao(db)
    return tema.cores() if tema else {}


def payload(camp: Campaign, db: Session, site_url: str, rotulo: str | None = None) -> dict:
    """Payload completo, com id (que liga o rastreio) e as cores do tema.

    O corpo sai dos blocos do editor visual; campanha antiga, criada antes do editor,
    cai no Markdown do campo body.
    """
    from ..main import templates

    cores = cores_da(camp, db)
    if camp.blocks:
        corpo = mailer.blocks_to_html(camp.blocks, cores, site_url)
    else:
        corpo = mailer.markdown_to_email(templates.env.filters["md"](camp.body))

    if rotulo is None:
        rotulo = "Newsletter / Boas-vindas" if camp.is_welcome else "Newsletter"

    return {
        "id": camp.id,
        "subject": camp.subject,
        "preheader": camp.preheader,
        "body_html": corpo,
        "image": camp.image,
        "cta_label": camp.cta_label,
        "cta_url": camp.cta_url,
        "cores": cores,
        "rotulo": rotulo,
    }
