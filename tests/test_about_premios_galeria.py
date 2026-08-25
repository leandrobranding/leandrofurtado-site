"""Última peça do lançamento (19/08): galeria de fotos por prêmio no /about.

Antes: só o PRIMEIRO prêmio mostrava galeria, e sempre com as 4 imagens
estáticas fixas (/static/img/award/award-1..4.webp), presas ao primeiro —
os outros prêmios nunca tinham galeria nenhuma, upload ou não.

Agora: cada prêmio mostra a PRÓPRIA galeria (profile.awards[].images,
editável no admin). Retrocompatibilidade: enquanto NENHUM prêmio tiver foto
enviada, o primeiro mantém as 4 estáticas de sempre — assim que qualquer
prêmio ganha foto de verdade, o estático some por inteiro (mesmo do
primeiro, se for ele quem ficou sem foto própria).

Mesmo padrão de test_about_imagens_decorativas.py: monkeypatch em
app.routers.public.get_profile em vez de escrever no Profile de verdade —
a suíte roda contra o banco isolado por DATA_DIR e profile_save reescreveria
campos que esta requisição de teste não estaria enviando.
"""
from starlette.testclient import TestClient

from app.main import app as _app

UM_PREMIO_SEM_FOTOS = [
    {"id": "p1", "title_pt": "Top de Marketing", "title_en": "Top Marketing",
     "year": "2024", "desc_pt": "", "desc_en": "", "images": []},
]


def _subir_com_awards(monkeypatch, awards):
    import app.routers.public as pub
    original = pub.get_profile

    def _com_awards(db):
        perfil = dict(original(db))
        perfil["awards"] = awards
        return perfil

    monkeypatch.setattr(pub, "get_profile", _com_awards)
    with TestClient(_app):
        pass


def _get_about():
    with TestClient(_app, base_url="https://testserver") as client:
        return client.get("/about")


def test_sem_nenhuma_foto_enviada_primeiro_premio_mostra_as_4_estaticas(monkeypatch):
    _subir_com_awards(monkeypatch, UM_PREMIO_SEM_FOTOS)
    r = _get_about()
    assert r.status_code == 200
    for n in range(1, 5):
        assert f"/static/img/award/award-{n}.webp" in r.text


def test_premio_com_fotos_proprias_mostra_as_fotos_e_nao_o_estatico(monkeypatch):
    awards = [
        {"id": "p1", "title_pt": "Top de Marketing", "title_en": "Top Marketing",
         "year": "2024", "desc_pt": "", "desc_en": "",
         "images": ["profile/premio1-aaa.webp", "profile/premio2-bbb.webp"]},
    ]
    _subir_com_awards(monkeypatch, awards)
    r = _get_about()
    assert r.status_code == 200
    assert "/media/profile/premio1-aaa.webp" in r.text
    assert "/media/profile/premio2-bbb.webp" in r.text
    assert "/static/img/award/award-1.webp" not in r.text
    assert "/static/img/award/award-2.webp" not in r.text


def test_segundo_premio_com_fotos_aparece_na_galeria_dele_e_nao_no_primeiro(monkeypatch):
    """Regressão direta do bug original: a galeria só renderizava para
    loop.first — um upload no SEGUNDO prêmio não aparecia em lugar nenhum."""
    awards = [
        {"id": "p1", "title_pt": "Prêmio Sem Foto", "title_en": "No Photo Award",
         "year": "2023", "desc_pt": "", "desc_en": "", "images": []},
        {"id": "p2", "title_pt": "Prêmio Com Foto", "title_en": "Photo Award",
         "year": "2024", "desc_pt": "", "desc_en": "",
         "images": ["profile/premio-do-segundo-ccc.webp"]},
    ]
    _subir_com_awards(monkeypatch, awards)
    r = _get_about()
    assert r.status_code == 200
    assert "/media/profile/premio-do-segundo-ccc.webp" in r.text
    # já existe UM prêmio com foto de verdade: o estático não pode mais
    # aparecer nem no primeiro, que ficou sem galeria própria (limpo).
    assert "/static/img/award/award-1.webp" not in r.text


def test_premio_sem_fotos_nao_mostra_galeria_quando_outro_premio_tem(monkeypatch):
    awards = [
        {"id": "p1", "title_pt": "Prêmio Sem Foto", "title_en": "No Photo Award",
         "year": "2023", "desc_pt": "", "desc_en": "", "images": []},
        {"id": "p2", "title_pt": "Prêmio Com Foto", "title_en": "Photo Award",
         "year": "2024", "desc_pt": "", "desc_en": "",
         "images": ["profile/so-do-p2.webp"]},
    ]
    _subir_com_awards(monkeypatch, awards)
    r = _get_about()
    html = r.text
    # o card do primeiro prêmio existe (título aparece) mas nenhuma classe de
    # galeria pode estar associada a ele — checagem indireta: só existe UMA
    # ocorrência de "award-gallery" na página inteira (a do p2).
    assert html.count("award-gallery") == 1
    assert "Prêmio Sem Foto" in html


def test_lightbox_continua_funcionando_com_as_fotos_novas(monkeypatch):
    """Os botões award-thumb com data-img (o gancho do lightbox em
    app/static/js/main.js) precisam existir para as imagens novas, do
    mesmo jeito que existiam para as estáticas."""
    awards = [
        {"id": "p1", "title_pt": "Prêmio", "title_en": "Award", "year": "2024",
         "desc_pt": "", "desc_en": "", "images": ["profile/foto-lightbox.webp"]},
    ]
    _subir_com_awards(monkeypatch, awards)
    r = _get_about()
    assert 'class="award-thumb"' in r.text
    assert 'data-img="/media/profile/foto-lightbox.webp"' in r.text
