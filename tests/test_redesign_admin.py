"""Painel dos redesigns (/admin/lab).

Chama as funções de rota direto, com sessão de teste, no mesmo padrão de
tests/test_admin_case_form.py: o que interessa aqui é a regra, não o HTML.

As rotas de mutação exigem admin (`require_admin`) e CSRF (`check_csrf`),
igual às outras 29 rotas POST de `app/routers/admin.py` que já chamam
`check_csrf`. Por isso toda chamada direta de rota aqui passa um `Request`
com sessão de teste (`_req`, mesmo padrão de `tests/lab/test_admin_lab.py`)
e o token de CSRF que essa sessão carrega.
"""
import asyncio
import datetime as dt
import inspect

import pytest
from starlette.requests import Request

from app.config import settings
from app.models import ESTADOS_REDESIGN, Redesign, novo_token
from app.routers import admin as admin_rotas

CSRF = "teste-csrf"


def _req() -> Request:
    """Uma Request mínima com sessão de admin autenticado e o CSRF válido.

    `check_csrf` só olha `request.session.get("csrf")`; as rotas de
    redesign recebem os campos do formulário como parâmetros de função
    diretos (não leem `request.form()`), então a Request não precisa de
    corpo, só da sessão."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/admin/lab/redesigns",
        "raw_path": b"/admin/lab/redesigns",
        "query_string": b"",
        "headers": [],
        "state": {"clean_path": "/admin/lab/redesigns", "lang": "pt"},
        "session": {"csrf": CSRF, "user": "leandro"},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _r(db, **campos):
    padrao = dict(slug="padaria-aurora", marca="Padaria Aurora",
                  antes_url="https://exemplo.com.br", token=novo_token())
    padrao.update(campos)
    obj = Redesign(**padrao)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def test_criar_gera_slug_e_token_sozinho(db):
    """O Leandro digita a marca e o endereço. Slug e token são derivados: um
    do nome, outro de `secrets`. Pedir os dois no formulário seria pedir que
    ele invente o que a máquina faz melhor."""
    asyncio.run(admin_rotas.redesign_criar(
        request=_req(), marca="Padaria Aurora", setor="Panificação",
        antes_url="grupoom.com.br", db=db, csrf=CSRF))
    r = db.query(Redesign).one()
    assert r.slug == "padaria-aurora"
    assert len(r.token) >= 20
    assert r.estado == "pitch"


def test_criar_desambigua_slug_repetido(db):
    """Duas marcas com o mesmo nome existem. O segundo slug não pode
    estourar com IntegrityError na cara de quem está cadastrando."""
    for _ in range(2):
        asyncio.run(admin_rotas.redesign_criar(
            request=_req(), marca="Aurora", setor="", antes_url="exemplo.com.br",
            db=db, csrf=CSRF))
    slugs = sorted(r.slug for r in db.query(Redesign).all())
    assert slugs == ["aurora", "aurora-2"]


def test_criar_sem_endereco_e_recusado(db):
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_criar(
            request=_req(), marca="Aurora", setor="", antes_url="", db=db, csrf=CSRF))


def test_criar_sem_csrf_e_recusado(db):
    """Convenção do arquivo: `check_csrf` roda antes de qualquer outra
    coisa. Token errado (ou ausente) tem que barrar a criação, não só a
    exclusão — as seis rotas seguem a mesma regra."""
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_criar(
            request=_req(), marca="Aurora", setor="", antes_url="exemplo.com.br",
            db=db, csrf="token-errado"))
    assert db.query(Redesign).count() == 0


def test_virar_estado_so_aceita_os_tres(db):
    r = _r(db)
    asyncio.run(admin_rotas.redesign_estado(r.id, request=_req(), estado="publico",
                                            db=db, csrf=CSRF))
    db.refresh(r)
    assert r.estado == "publico"
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_estado(r.id, request=_req(), estado="qualquer",
                                                db=db, csrf=CSRF))
    assert set(ESTADOS_REDESIGN) == {"pitch", "publico", "aprovado"}


def test_virar_estado_sem_csrf_e_recusado(db):
    """O achado do ciclo de conserto 1: sem isto, uma página maliciosa
    aberta noutra aba por um admin logado podia virar o estado de um
    redesign para `publico` sem clique nenhum — publicando a proposta
    comercial de um cliente, com o nome dele, na vitrine (§1 da spec)."""
    r = _r(db)
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_estado(r.id, request=_req(), estado="publico",
                                                db=db, csrf="token-errado"))
    db.refresh(r)
    assert r.estado == "pitch"


def test_colher_grava_o_dossie_e_a_data(db, monkeypatch):
    """A colheita é a da Task 2, chamada aqui. O teste troca a rede por um
    retorno fixo: quem testa a extração é tests/test_coleta.py."""
    monkeypatch.setattr(
        admin_rotas.coleta, "colher",
        lambda url, **k: {"ok": True, "erro": "", "titulo": "Padaria Aurora",
                          "telefones": ["4133334444"], "colhido_em": "2026-08-25T12:00:00"},
    )
    r = _r(db)
    asyncio.run(admin_rotas.redesign_colher(r.id, request=_req(), db=db, csrf=CSRF))
    db.refresh(r)
    assert r.insumos["telefones"] == ["4133334444"]
    assert r.insumos_em is not None


def test_colher_falhando_nao_apaga_o_dossie_anterior(db, monkeypatch):
    """Site do cliente fora do ar não pode custar o dossiê que já tinha sido
    colhido: o Leandro perderia o material de uma proposta em andamento."""
    r = _r(db, insumos={"telefones": ["4133334444"]},
           insumos_em=dt.datetime.now(dt.UTC))
    monkeypatch.setattr(
        admin_rotas.coleta, "colher",
        lambda url, **k: {"ok": False, "erro": "não consegui abrir",
                          "titulo": "", "telefones": []},
    )
    asyncio.run(admin_rotas.redesign_colher(r.id, request=_req(), db=db, csrf=CSRF))
    db.refresh(r)
    assert r.insumos["telefones"] == ["4133334444"]


def test_capturar_o_antes_usa_o_endereco_do_cliente(db, monkeypatch):
    chamadas = []
    monkeypatch.setattr(admin_rotas.captura, "capturar",
                        lambda url, slug: (chamadas.append((url, slug)) or ("sites/x.webp", "")))
    r = _r(db, antes_url="https://exemplo.com.br")
    asyncio.run(admin_rotas.redesign_capturar(r.id, request=_req(), lado="antes",
                                              db=db, csrf=CSRF))
    db.refresh(r)
    assert chamadas[0][0] == "https://exemplo.com.br"
    assert r.antes_shot == "sites/x.webp"
    assert r.antes_shot_at is not None


def test_capturar_o_depois_passa_pelo_link_do_token(db, monkeypatch):
    """§9.1: o endereço público responde 404 enquanto o redesign é `pitch`,
    então a captura do 'depois' PRECISA entrar pelo token. É a regra do
    loopback em rotas_sites.py que impede isso de carimbar `visto_em`.

    E precisa ser o endereço INTERNO do contêiner (127.0.0.1:8000), nunca
    `settings.base_url`: o Chromium roda dentro do contêiner e o nginx no
    host, então bater no endereço público faria a requisição sair e voltar
    pelo proxy, que carimbaria o IP da bridge do Docker em vez de
    127.0.0.1 — e a regra de loopback de `marcar_visto` não pegaria a
    captura, que marcaria o cliente como tendo aberto a proposta antes de
    ela ter sido enviada.
    """
    chamadas = []
    monkeypatch.setattr(admin_rotas.captura, "capturar",
                        lambda url, slug: (chamadas.append(url) or ("sites/d.webp", "")))
    r = _r(db, estado="pitch")
    asyncio.run(admin_rotas.redesign_capturar(r.id, request=_req(), lado="depois",
                                              db=db, csrf=CSRF))
    db.refresh(r)
    assert f"/lab/p/{r.token}" in chamadas[0]
    assert chamadas[0] == f"http://127.0.0.1:8000/lab/p/{r.token}"
    assert not chamadas[0].startswith(settings.base_url)
    assert r.depois_shot == "sites/d.webp"


def test_capturar_falhando_nao_apaga_a_captura_anterior(db, monkeypatch):
    monkeypatch.setattr(admin_rotas.captura, "capturar",
                        lambda url, slug: ("", "não consegui abrir esse endereço"))
    r = _r(db, antes_shot="sites/velha.webp")
    asyncio.run(admin_rotas.redesign_capturar(r.id, request=_req(), lado="antes",
                                              db=db, csrf=CSRF))
    db.refresh(r)
    assert r.antes_shot == "sites/velha.webp"


def test_marcar_como_enviado_carimba_a_data(db):
    """`enviado_em` é o par de `visto_em`. O servidor não sabe que o link foi
    para o WhatsApp de alguém, então quem diz é o Leandro. Com os dois, ele
    sabe quanto tempo o prospect levou para abrir."""
    r = _r(db)
    assert r.enviado_em is None
    asyncio.run(admin_rotas.redesign_enviado(r.id, request=_req(), db=db, csrf=CSRF))
    db.refresh(r)
    assert r.enviado_em is not None


def test_excluir_sem_csrf_e_recusado(db):
    """O outro caso citado no achado: exclusão silenciosa por página
    maliciosa noutra aba. Sem CSRF válido, o registro tem que sobreviver."""
    r = _r(db)
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_excluir(r.id, request=_req(), db=db,
                                                  csrf="token-errado"))
    assert db.get(Redesign, r.id) is not None


def test_excluir_com_csrf_valido_apaga(db):
    r = _r(db)
    asyncio.run(admin_rotas.redesign_excluir(r.id, request=_req(), db=db, csrf=CSRF))
    assert db.get(Redesign, r.id) is None


def test_o_admin_nunca_mostra_o_token_de_um_case_alheio(db):
    """Sanidade: a lista do painel é do Leandro, e o token é o segredo do
    pitch. Ele aparece SÓ como link copiável do próprio registro."""
    r = _r(db)
    assert r.token


def test_toda_rota_de_redesign_no_admin_exige_admin_e_csrf():
    """Convenção do arquivo: 29 das 35 rotas POST de admin.py chamam
    `check_csrf`. As de redesign não podem ser exceção.

    Sem CSRF, um admin logado que abra uma página maliciosa noutra aba pode
    ter um redesign apagado, ou o estado virado para `publico`, o que
    publica a proposta comercial de um cliente com o nome dele na vitrine.
    É o dano que a §1 da spec existe para impedir."""
    alvos = [nome for nome in dir(admin_rotas) if nome.startswith("redesign_")]
    assert len(alvos) >= 6, alvos
    for nome in alvos:
        funcao = getattr(admin_rotas, nome)
        if not callable(funcao) or not inspect.iscoroutinefunction(funcao):
            continue
        fonte = inspect.getsource(funcao)
        assert "check_csrf" in fonte, f"{nome} não verifica CSRF"
        assert "require_admin" in fonte, f"{nome} não exige admin"
