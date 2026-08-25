"""Formação acadêmica (item novo do dono, 19/08, dados reais do LinkedIn).

Campo aditivo em Profile.data (education), sem existir antes em nenhum
Profile — cobre o backfill idempotente (só entra na primeira run_seeds,
nunca sobrescreve edição/esvaziamento do admin depois) e a renderização em
/about nos dois idiomas.
"""
from starlette.testclient import TestClient

from app.main import app as _app
from app.models import Profile
from app.services.seeds import PROFILE, run_seeds


def _subir() -> None:
    with TestClient(_app):
        pass


# ---------------------------------------------------------------- seed / backfill

def test_instalacao_nova_ja_nasce_com_as_duas_formacoes(db):
    run_seeds(db)
    perfil = db.query(Profile).filter_by(id=1).first()
    assert len(perfil.data["education"]) == 2
    assert perfil.data["education"][0]["institution_pt"] == "Universidade Tecnológica Federal do Paraná"


def test_perfil_pre_existente_sem_a_chave_recebe_o_backfill_uma_vez(db):
    perfil = Profile(id=1, data={"name": "Leandro Furtado", "experience": []})  # sem "education"
    db.add(perfil)
    db.commit()

    run_seeds(db)

    perfil = db.query(Profile).filter_by(id=1).first()
    assert len(perfil.data["education"]) == 2


def test_segunda_run_seeds_nao_duplica(db):
    run_seeds(db)
    run_seeds(db)
    perfil = db.query(Profile).filter_by(id=1).first()
    assert len(perfil.data["education"]) == 2


def test_admin_que_esvaziou_a_lista_de_proposito_nao_leva_backfill_de_volta(db):
    """O backfill só olha se a CHAVE existe — uma vez que existe (mesmo
    vazia, porque o admin removeu as duas entradas), run_seeds nunca mais
    reimpõe os dados reais por cima."""
    perfil = Profile(id=1, data={"name": "Leandro Furtado", "education": []})
    db.add(perfil)
    db.commit()

    run_seeds(db)

    perfil = db.query(Profile).filter_by(id=1).first()
    assert perfil.data["education"] == []


def test_admin_que_editou_uma_entrada_nao_e_sobrescrito(db):
    editado = [{"institution_pt": "Editado", "institution_en": "Edited",
                "course_pt": "Curso", "course_en": "Course", "period": "2000 — 2001"}]
    perfil = Profile(id=1, data={"name": "Leandro Furtado", "education": editado})
    db.add(perfil)
    db.commit()

    run_seeds(db)

    perfil = db.query(Profile).filter_by(id=1).first()
    assert perfil.data["education"] == editado


# ---------------------------------------------------------------- /about

def test_about_pt_mostra_as_duas_formacoes():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    assert r.status_code == 200
    assert "FORMA" in r.text.upper() and "ACAD" in r.text.upper()
    assert "Universidade Tecnológica Federal do Paraná" in r.text
    assert "Centro Universitário Adventista de São Paulo" in r.text
    assert "Ensino Técnico" in r.text


def test_about_en_mostra_as_traducoes():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/en/about")
    assert r.status_code == 200
    assert "EDUCATION" in r.text.upper()
    assert "Federal University of Technology" in r.text
    assert "Technical Degree" in r.text


def test_about_sem_formacao_cadastrada_nao_mostra_a_secao(monkeypatch):
    import app.routers.public as pub
    original = pub.get_profile

    def _sem_educacao(db):
        perfil = dict(original(db))
        perfil["education"] = []
        return perfil

    monkeypatch.setattr(pub, "get_profile", _sem_educacao)
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    assert 'class="cv-section edu-section"' not in r.text
