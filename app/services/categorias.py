"""Ordem das categorias, calculada e não digitada.

A ordem do portfólio deixou de ser um número que alguém preenche: quem tem mais
trabalho aparece primeiro, e empate se resolve pelo alfabeto. Isso mantém a
vitrine honesta sozinha — uma categoria que cresce sobe, uma que ficou para trás
desce, sem ninguém lembrar de arrumar a lista.

O campo `sort` continua existindo porque é por ele que o site ordena; só passou a
ser preenchido aqui, sempre que o número de cases pode ter mudado.
"""

from __future__ import annotations

import unicodedata

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Case, Category


def _alfabetica(nome: str) -> str:
    plano = unicodedata.normalize("NFD", nome or "")
    return "".join(c for c in plano if unicodedata.category(c) != "Mn").lower()


def contagens(db: Session) -> dict[int, int]:
    """Quantos cases cada categoria tem, arquivados de fora."""
    linhas = (db.query(Case.category_id, func.count(Case.id))
              .filter(Case.category_id.isnot(None), Case.archived.is_(False))
              .group_by(Case.category_id).all())
    return {cid: int(n) for cid, n in linhas}


def contagens_publicas(db: Session) -> dict[int, int]:
    """Só o que o visitante consegue abrir: publicado e não arquivado."""
    linhas = (db.query(Case.category_id, func.count(Case.id))
              .filter(Case.category_id.isnot(None), Case.archived.is_(False),
                      Case.published.is_(True))
              .group_by(Case.category_id).all())
    return {cid: int(n) for cid, n in linhas}


def ordenadas(db: Session) -> list[Category]:
    """As categorias na ordem oficial: mais cases primeiro, depois A-Z.

    Devolve todas, inclusive as vazias — é a lista do painel, onde uma categoria
    recém-criada precisa aparecer para receber o primeiro case.
    """
    todas = db.query(Category).all()
    n = contagens(db)
    todas.sort(key=lambda c: (-n.get(c.id, 0), _alfabetica(c.name_pt)))
    return todas


def publicas(db: Session, lang: str = "pt") -> list[Category]:
    """A lista que o site mostra: categoria sem case publicado não existe, em
    ordem alfabética pelo nome no idioma da página.

    Filtro que não devolve nada é uma porta pintada na parede. A categoria só
    aparece no portfólio depois que tem trabalho para sustentar o clique.

    A ordem aqui não é a de `ordenadas()` (mais cases primeiro — essa
    continua sendo a ferramenta do painel, veja `reordenar`). No site
    público quem procura uma categoria pelo nome quer achar por nome, não
    por quantas peças ela tem.
    """
    from ..i18n import field

    n = contagens_publicas(db)
    cats = [c for c in db.query(Category).all() if n.get(c.id, 0) > 0]
    cats.sort(key=lambda c: _alfabetica(field(c, "name", lang)))
    return cats


def reordenar(db: Session) -> list[Category]:
    """Recalcula `sort` de todas as categorias. Não commita: quem chama decide."""
    todas = ordenadas(db)
    for i, c in enumerate(todas):
        if c.sort != i:
            c.sort = i
    return todas
