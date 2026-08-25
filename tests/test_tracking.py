"""Pacote de rastreamento (18/08): GTM só com consentimento real, decidido no
servidor — nunca "carrega e depois pergunta". Cobre também a CSP nova e a
liberação da verificação do Google Search Console durante o modo construção.

Sobe o app de verdade com TestClient e `base_url="https://testserver"`: o
cookie de sessão sai `Secure` fora de debug (`https_only=not settings.debug`),
e sobre HTTP puro o httpx nem guarda o cookie — o mesmo cuidado documentado em
tests/nodal/test_login_aluno.py. Usa o SessionLocal real (isolado por
DATA_DIR, ver tests/conftest.py) porque `_gtm_ativo` em app/main.py consulta o
banco direto — o fixture `db` em memória não é o mesmo banco que a rota vê.
"""
import importlib.util
import re

import pytest

from starlette.testclient import TestClient

from app.database import SessionLocal as _SessionLocal
from app.main import app as _app
from app.models import SiteSetting


def _subir() -> None:
    """Dispara o lifespan (create_all) antes do primeiro uso do SessionLocal real."""
    with TestClient(_app):
        pass


def _set_setting(chave: str, valor: str) -> None:
    db = _SessionLocal()
    try:
        row = db.get(SiteSetting, chave)
        if row:
            row.value = valor
        else:
            db.add(SiteSetting(key=chave, value=valor))
        db.commit()
    finally:
        db.close()


def _limpar_setting(chave: str) -> None:
    db = _SessionLocal()
    try:
        db.query(SiteSetting).filter_by(key=chave).delete()
        db.commit()
    finally:
        db.close()


# ---------- sem escolha registrada: banner presente, nada de GTM ----------

def test_sem_cookie_nao_ha_gtm_em_lugar_nenhum_e_o_banner_aparece():
    _subir()
    _set_setting("gtm_id", "GTM-ABC1234")
    try:
        with TestClient(_app, base_url="https://testserver") as client:
            r = client.get("/")
        assert "googletagmanager" not in r.text
        assert 'name="gtm-id" content=""' in r.text
        assert 'class="cookie-note"' in r.text
        assert 'name="escolha" value="sim"' in r.text
        assert 'name="escolha" value="nao"' in r.text
    finally:
        _limpar_setting("gtm_id")


# ---------- recusar é respeitado: sem GTM, sem banner de novo ----------

def test_recusar_nao_mostra_gtm_nem_reabre_o_banner():
    _subir()
    _set_setting("gtm_id", "GTM-ABC1234")
    try:
        with TestClient(_app, base_url="https://testserver") as client:
            client.cookies.set("lf_consent", "nao")
            r = client.get("/")
        assert "googletagmanager" not in r.text
        assert 'class="cookie-note"' not in r.text
    finally:
        _limpar_setting("gtm_id")


# ---------- aceitar carrega o ID do PAINEL, nunca um valor cravado ----------

def test_aceitar_carrega_o_id_configurado_no_painel():
    _subir()
    _set_setting("gtm_id", "GTM-DOPAINEL")
    try:
        with TestClient(_app, base_url="https://testserver") as client:
            client.cookies.set("lf_consent", "sim")
            r = client.get("/")
        assert 'name="gtm-id" content="GTM-DOPAINEL"' in r.text
        assert "ns.html?id=GTM-DOPAINEL" in r.text
        assert "/static/js/consentimento.js" in r.text
        assert 'class="cookie-note"' not in r.text  # já decidiu, não reaparece
    finally:
        _limpar_setting("gtm_id")


# ---------- painel sem ID configurado desliga a ferramenta ----------

def test_gtm_id_vazio_no_painel_desliga_mesmo_com_consentimento():
    _subir()
    _limpar_setting("gtm_id")  # garante painel sem nada configurado
    with TestClient(_app, base_url="https://testserver") as client:
        client.cookies.set("lf_consent", "sim")
        r = client.get("/")
    assert "googletagmanager" not in r.text
    assert 'name="gtm-id" content=""' in r.text


# ---------- Nodal: a área logada do aluno nunca carrega GTM ----------

# NESTA BRANCH (produção) as rotas de aluno do corte 4 ainda não existem —
# o teste roda inteiro na main e volta a valer aqui no deploy do corte. O skip
# é por importabilidade, não por marca fixa: quando app.nodal.rotas_aluno
# chegar, o teste liga sozinho.
# `find_spec` de submódulo IMPORTA o pacote pai, então perguntar direto por
# "app.nodal.rotas_aluno" estoura quando a pasta app/nodal/ não existe. O
# curto-circuito do `or` pergunta primeiro pelo pai. (24/08/2026, quando o
# Nodal virou opcional.)
def _sem_rotas_de_aluno() -> bool:
    return (importlib.util.find_spec("app.nodal") is None
            or importlib.util.find_spec("app.nodal.rotas_aluno") is None)


@pytest.mark.skipif(_sem_rotas_de_aluno(),
                    reason="rotas de aluno do corte 4 ainda não existem nesta branch")
def test_tela_de_estudo_do_aluno_nunca_carrega_gtm_mesmo_com_consentimento():
    """Área logada de produto pago não é lugar de pixel de marketing — vale
    mesmo com `lf_consent=sim` e um `gtm_id` configurado no painel."""
    from starlette.responses import Response as _Resp

    from app.nodal import sessao
    from app.nodal.models import Aluno, Aula, Curso, Matricula, Modulo

    _subir()
    _set_setting("gtm_id", "GTM-ABC1234")
    real_db = _SessionLocal()
    curso = aluno = None
    try:
        curso = Curso(slug="rastreio-ia", titulo="IA", publicado=True)
        real_db.add(curso)
        real_db.commit()
        modulo = Modulo(curso_id=curso.id, titulo="M", ordem=0)
        real_db.add(modulo)
        real_db.commit()
        real_db.add(Aula(curso_id=curso.id, modulo_id=modulo.id, titulo="Abertura",
                         slug="abertura", ordem=0, publicado=True,
                         blocos=[{"tipo": "texto", "corpo": "conteúdo real"}]))
        real_db.commit()
        aluno = Aluno(email="rastreio@exemplo.com", nome="Rastreio")
        real_db.add(aluno)
        real_db.commit()
        real_db.add(Matricula(aluno_id=aluno.id, curso_id=curso.id, liberada_por="teste"))
        real_db.commit()

        resposta_cookie = _Resp()
        sessao.gravar_sessao(resposta_cookie, aluno.id)
        valor = resposta_cookie.headers["set-cookie"].split(";")[0].split("=", 1)[1]
        with TestClient(_app, base_url="https://testserver") as client:
            client.cookies.set(sessao.COOKIE, valor)
            client.cookies.set("lf_consent", "sim")
            r = client.get("/nodal/curso/rastreio-ia/aula/abertura")
        assert r.status_code == 200
        assert "googletagmanager" not in r.text
        assert 'class="cookie-note"' not in r.text
    finally:
        if aluno is not None:
            real_db.query(Matricula).filter_by(aluno_id=aluno.id).delete()
            real_db.query(Aluno).filter_by(id=aluno.id).delete()
        if curso is not None:
            real_db.query(Aula).filter_by(curso_id=curso.id).delete()
            real_db.query(Modulo).filter_by(curso_id=curso.id).delete()
            real_db.query(Curso).filter_by(id=curso.id).delete()
        real_db.commit()
        real_db.close()
        _limpar_setting("gtm_id")


# ---------- o banner funciona sem JavaScript: POST comum, csrf semeado ----------

def test_o_banner_funciona_sem_javascript_visitante_real_sem_sessao_forjada():
    """Visitante de sessão nova: o csrf precisa estar semeado na PRÓPRIA
    página que mostra o banner (lição C1) — sem isso, `check_csrf` recusaria
    todo visitante real, e só passaria quem forjasse a sessão no teste."""
    _subir()
    _set_setting("gtm_id", "GTM-ABC1234")
    try:
        with TestClient(_app, base_url="https://testserver") as client:
            pagina = client.get("/")
            assert 'class="cookie-note"' in pagina.text
            m = re.search(r'name="csrf" value="([^"]*)"', pagina.text)
            assert m and m.group(1), "csrf vazio no banner: nenhum visitante real conseguiria aceitar"

            resp = client.post("/consentimento",
                               data={"csrf": m.group(1), "escolha": "sim", "proximo": "/"})
        assert resp.status_code == 200  # o TestClient segue o redirect (303) sozinho
        assert resp.history and resp.history[0].status_code == 303
        assert client.cookies.get("lf_consent") == "sim"
        assert 'name="gtm-id" content="GTM-ABC1234"' in resp.text
    finally:
        _limpar_setting("gtm_id")


def test_csrf_errado_nao_grava_a_escolha():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        client.get("/")  # só para ter uma sessão válida, sem usar o csrf dela
        resp = client.post("/consentimento",
                           data={"csrf": "chute-qualquer", "escolha": "sim", "proximo": "/"})
    assert resp.status_code == 403


# ---------- CSP: os domínios do pacote de rastreamento ----------

def _csp(client) -> str:
    return client.get("/").headers["content-security-policy"]


def test_csp_libera_googletagmanager_em_script_src_e_frame_src():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        csp = _csp(client)
    script_src = next(d for d in csp.split("; ") if d.startswith("script-src"))
    frame_src = next(d for d in csp.split("; ") if d.startswith("frame-src"))
    assert "https://www.googletagmanager.com" in script_src.split()
    assert "https://www.googletagmanager.com" in frame_src.split()


def test_csp_frame_src_continua_liberando_os_players_que_ja_existiam():
    """A adição não pode empurrar nenhum player antigo pra fora — mesma
    checagem de tests/test_seguranca.py, agora com o domínio novo no meio."""
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        csp = _csp(client)
    frame_src = next(d for d in csp.split("; ") if d.startswith("frame-src")).split()
    for esperado in ("https://www.instagram.com", "https://www.youtube-nocookie.com",
                     "https://player.vimeo.com", "https://iframe.videodelivery.net"):
        assert esperado in frame_src


def test_csp_libera_os_dominios_de_analise_em_connect_src():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        csp = _csp(client)
    connect_src = next(d for d in csp.split("; ") if d.startswith("connect-src")).split()
    for esperado in ("https://www.google-analytics.com", "https://*.google-analytics.com",
                     "https://analytics.google.com", "https://stats.g.doubleclick.net",
                     "https://www.facebook.com"):
        assert esperado in connect_src


def test_csp_img_src_ja_libera_https_qualquer_dominio():
    """img-src já tem o coringa https: — o pixel de imagem de fallback do
    Facebook e o do GA4 passam por aqui sem precisar listar domínio nenhum."""
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        csp = _csp(client)
    img_src = next(d for d in csp.split("; ") if d.startswith("img-src")).split()
    assert "https:" in img_src


# ---------- Search Console: liberado mesmo em modo construção ----------

def test_verificacao_do_google_responde_em_construcao_pagina_comum_nao():
    _subir()
    _set_setting("construction_mode", "1")
    try:
        with TestClient(_app, base_url="https://testserver") as client:
            verif = client.get("/google5573662520e72392.html")
            comum = client.get("/portfolio")
        assert verif.status_code == 200
        assert "google-site-verification" in verif.text
        assert comum.status_code == 200
        assert 'class="wip"' in comum.text  # caiu na tela de construção
        assert "google-site-verification" not in comum.text
    finally:
        _limpar_setting("construction_mode")
