"""Item 2 (19/08): a página /about lê about_img_1/about_img_2 do Profile,
com fallback para o asset estático quando o campo está vazio.

`get_profile` é trocado por monkeypatch (mesmo padrão de
test_formacao_academica.py) em vez de gravar no Profile de verdade: a
suíte inteira roda contra o mesmo banco real isolado por DATA_DIR
(ver tests/conftest.py), e escrever ali por `profile_save` reescreve TODOS
os campos do formulário — inclusive `education`, que esta requisição de
teste não estaria enviando — derrubando dado de outro teste.
"""
from starlette.testclient import TestClient

from app.main import app as _app


def _subir() -> None:
    with TestClient(_app):
        pass


def test_sem_about_img_usa_os_assets_padrao():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    assert r.status_code == 200
    assert "/static/img/about-1.webp" in r.text
    assert "/static/img/about-2.webp" in r.text


def test_com_about_img_cadastrado_usa_a_imagem_do_perfil(monkeypatch):
    import app.routers.public as pub
    original = pub.get_profile

    def _com_imagens(db):
        perfil = dict(original(db))
        perfil["about_img_1"] = "profile/about1-teste.webp"
        perfil["about_img_2"] = "profile/about2-teste.webp"
        return perfil

    monkeypatch.setattr(pub, "get_profile", _com_imagens)
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    assert r.status_code == 200
    assert "/media/profile/about1-teste.webp" in r.text
    assert "/media/profile/about2-teste.webp" in r.text
    assert "/static/img/about-1.webp" not in r.text
    assert "/static/img/about-2.webp" not in r.text
