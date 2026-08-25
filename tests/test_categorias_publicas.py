"""publicas() vira alfabética por nome no idioma — pedido 3 do pacote de
17/08 (ver .superpowers/sdd/2026-08-17-nodal-4-experiencia-do-aluno/
pacote-portfolio-brief.md). `ordenadas()` (a ferramenta do painel) continua
por contagem: quem muda é só a lista pública.
"""
from app.models import Case, Category
from app.services import categorias as cats_svc


def _tres_categorias_com_contagem_que_discorda_do_alfabeto(db):
    """Zebra tem mais cases publicados que Abelha e Manga juntas — se
    publicas() ainda herdasse a ordem de ordenadas() (mais cases primeiro),
    Zebra viria primeiro. Alfabética, ela vem por último."""
    zebra = Category(slug="zebra", name_pt="Zebra", name_en="Zebra")
    abelha = Category(slug="abelha", name_pt="Abelha", name_en="Bee")
    manga = Category(slug="manga", name_pt="Manga", name_en="Mango")
    db.add_all([zebra, abelha, manga])
    db.flush()
    for i in range(3):
        db.add(Case(slug=f"z{i}", title_pt=f"Z{i}", category_id=zebra.id,
                    published=True, archived=False))
    db.add(Case(slug="a0", title_pt="A0", category_id=abelha.id, published=True, archived=False))
    db.add(Case(slug="m0", title_pt="M0", category_id=manga.id, published=True, archived=False))
    db.commit()
    return abelha, manga, zebra


def test_publicas_vem_em_ordem_alfabetica_por_nome_pt(db):
    _tres_categorias_com_contagem_que_discorda_do_alfabeto(db)
    nomes = [c.name_pt for c in cats_svc.publicas(db, lang="pt")]
    assert nomes == ["Abelha", "Manga", "Zebra"]


def test_publicas_ordena_pelo_nome_em_ingles_na_pagina_em_ingles(db):
    """name_en diverge de name_pt o bastante para inverter a ordem."""
    a = Category(slug="a", name_pt="Abelha-PT", name_en="Zzz-EN")
    b = Category(slug="b", name_pt="Zzz-PT", name_en="Abelha-EN")
    db.add_all([a, b])
    db.flush()
    db.add(Case(slug="ca", title_pt="Ca", category_id=a.id, published=True, archived=False))
    db.add(Case(slug="cb", title_pt="Cb", category_id=b.id, published=True, archived=False))
    db.commit()
    nomes_en = [c.name_en for c in cats_svc.publicas(db, lang="en")]
    assert nomes_en == ["Abelha-EN", "Zzz-EN"]


def test_categoria_sem_case_publicado_continua_de_fora(db):
    vazia = Category(slug="vazia", name_pt="Vazia", name_en="Empty")
    db.add(vazia)
    db.commit()
    assert "vazia" not in [c.slug for c in cats_svc.publicas(db)]


def test_ordenadas_continua_por_contagem_o_painel_nao_muda(db):
    _tres_categorias_com_contagem_que_discorda_do_alfabeto(db)
    nomes = [c.name_pt for c in cats_svc.ordenadas(db)]
    assert nomes[0] == "Zebra"  # mais cases primeiro continua valendo no painel
