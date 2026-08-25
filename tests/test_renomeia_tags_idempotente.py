"""Cobertura do RENOMEIA_TAGS num Profile pré-existente (rodada 3, item 10).

Achado da revisão da rodada 2: o comportamento já era correto (renomeia na
primeira `run_seeds`, não duplica nem reverte na segunda, preserva tags que
o usuário criou por conta própria), mas não havia teste travando isso — só
a seed de instalação nova era coberta. Este arquivo fecha a lacuna: simula
o Profile como ele existe em produção (tags já com os nomes ORIGINAIS,
anteriores à rodada 2) e roda `run_seeds` duas vezes.
"""
from app.models import Profile
from app.services.seeds import RENOMEIA_TAGS, run_seeds


def _perfil_pre_existente(db, items: list[str]) -> Profile:
    perfil = Profile(id=1, data={
        "name": "Leandro Furtado",
        "skills": [
            {"group_pt": "Direção & Estratégia", "group_en": "Direction & Strategy",
             "items": items},
        ],
    })
    db.add(perfil)
    db.commit()
    return perfil


def test_renomeia_tags_originais_na_primeira_execucao(db):
    originais = list(RENOMEIA_TAGS.keys())
    _perfil_pre_existente(db, originais)

    run_seeds(db)

    perfil = db.query(Profile).filter_by(id=1).first()
    itens = perfil.data["skills"][0]["items"]
    assert itens == [RENOMEIA_TAGS[nome] for nome in originais]
    # nenhum nome antigo sobrevive
    assert not (set(itens) & set(originais))


def test_segunda_execucao_nao_duplica_nem_reverte(db):
    originais = list(RENOMEIA_TAGS.keys())
    _perfil_pre_existente(db, originais)

    run_seeds(db)
    esperado = db.query(Profile).filter_by(id=1).first().data["skills"][0]["items"][:]

    run_seeds(db)

    perfil = db.query(Profile).filter_by(id=1).first()
    itens = perfil.data["skills"][0]["items"]
    assert itens == esperado
    assert len(itens) == len(originais)  # sem duplicar nenhum item


def test_tags_customizadas_do_usuario_sobrevivem_ao_renomeio(db):
    """Uma tag que o Leandro escreveu no admin, sem correspondência nenhuma em
    RENOMEIA_TAGS, precisa sair exatamente igual — a seed só troca os nomes
    que ela reconhece, nunca toca no resto do conteúdo editado."""
    customizada = "Direção de Fotografia Publicitária"
    _perfil_pre_existente(db, ["Liderança Criativa", customizada, "Branding"])

    run_seeds(db)
    run_seeds(db)

    itens = db.query(Profile).filter_by(id=1).first().data["skills"][0]["items"]
    assert itens == ["Liderança de Equipes", customizada, "Branding"]


def test_nomes_intermediarios_da_rodada_2_tambem_convergem_para_o_final(db):
    """Perfis que já tinham passado pela rodada 2 (nomes "Liderança Criativa"
    e "Fotografia Comercial") precisam chegar ao nome final da rodada 3 sem
    elo perdido — mesmo sem nunca ter visto o nome ORIGINAL de antes da
    rodada 2."""
    _perfil_pre_existente(db, ["Liderança Criativa", "Fotografia Comercial"])

    run_seeds(db)

    itens = db.query(Profile).filter_by(id=1).first().data["skills"][0]["items"]
    assert itens == ["Liderança de Equipes", "Fotografia & Eventos"]
