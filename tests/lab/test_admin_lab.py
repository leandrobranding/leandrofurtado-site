"""Testa o painel `/admin/lab` (Task 7 do Plano 1 — Fundação).

Segue os dois padrões já em uso na suíte de admin do repo:
- `_get_de`/`_post_de` (mesmo de `tests/test_admin_settings.py`, `tests/nodal/
  test_admin_situacoes.py`): monta a `Request` à mão com sessão de admin já
  presente e chama a função da rota direto, sem TestClient nem servidor —
  usado para os testes de conteúdo/persistência (mais rápido, sem overhead
  de HTTP de verdade).
- `client` (fixture de `tests/lab/conftest.py`, TestClient sobre o app real):
  usado só para o teste de login, porque montar a `Request` à mão pula por
  cima do `Depends(require_admin)` — só uma requisição HTTP de verdade prova
  que a rota está protegida.
"""
import asyncio
import datetime as dt
from urllib.parse import urlencode

from starlette.requests import Request

from app.lab.models import LabIaGasto, LabLead, LabSandbox
from app.services.formato import formatar_reais
from app.routers.admin import lab_painel, lab_salvar, set_setting, settings_map


def _get_de(caminho: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "headers": [],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": {"csrf": "teste-csrf", "user": "leandro"},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _post_de(caminho: str, dados: dict) -> Request:
    corpo = urlencode(dados).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": {"csrf": "teste-csrf", "user": "leandro"},
    }
    enviado = False

    async def receive():
        nonlocal enviado
        if enviado:
            return {"type": "http.disconnect"}
        enviado = True
        return {"type": "http.request", "body": corpo, "more_body": False}

    return Request(scope, receive)


# ------------------------------------------------------------- login exigido

def test_rota_exige_login_admin(client):
    r = client.get("/admin/lab", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    assert "/admin/login" in r.headers.get("location", "")


# ---------------------------------------------------------------- gasto de IA

def test_gasto_do_dia_aparece_na_tela(db):
    hoje = dt.date.today()
    db.add(LabIaGasto(dia=hoje, tokens=1234, custo_estimado_centavos=37))
    db.commit()
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    # formato PT-BR (vírgula decimal), mesmo filtro `reais` usado no Nodal —
    # não "R$ 0.37" (achado de polimento da revisão da T7)
    assert formatar_reais(37) in corpo
    assert "1234" in corpo


def test_gasto_do_mes_soma_os_dias_do_mes(db):
    hoje = dt.date.today()
    ontem = hoje - dt.timedelta(days=1)
    if ontem.month != hoje.month:
        ontem = hoje.replace(day=1)  # evita virar mês no dia 1 do teste
    db.add(LabIaGasto(dia=hoje, tokens=100, custo_estimado_centavos=20))
    if ontem != hoje:
        db.add(LabIaGasto(dia=ontem, tokens=50, custo_estimado_centavos=10))
    db.commit()
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    esperado_centavos = 20 if ontem == hoje else 30
    assert formatar_reais(esperado_centavos) in corpo


# ------------------------------------------------------------------- sandboxes

def test_sandboxes_ativos_contados(db):
    for i in range(3):
        db.add(LabSandbox(
            token=f"tok-{i}", demo_origem="rh",
            expira_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)))
    db.commit()
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    assert ">3<" in corpo or ">3 <" in corpo or "3</span>" in corpo


# ------------------------------------------------------------------------ leads

def test_lead_com_script_no_nome_sai_escapado(db):
    db.add(LabLead(nome="<script>alert(1)</script>", email="visitante@exemplo.com.br",
                   demo="fin", momento="nf_email"))
    db.commit()
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    assert "<script>alert(1)</script>" not in corpo
    assert "&lt;script&gt;" in corpo
    assert "|safe" not in corpo


def test_lead_aparece_com_demo_e_momento(db):
    db.add(LabLead(nome="Visitante Teste", email="visitante@exemplo.com.br",
                   demo="escola", momento="boletim_email"))
    db.commit()
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    assert "Visitante Teste" in corpo
    assert "escola" in corpo
    assert "boletim_email" in corpo


# ---------------------------------------------------------- salvar teto/modelo

def test_salvar_teto_persiste_e_converte_reais_para_centavos(db):
    resp = asyncio.run(lab_salvar(_post_de("/admin/lab", {
        "csrf": "teste-csrf",
        "lab_ia_teto_dia_reais": "1,50",
    }), db))
    assert resp.status_code == 303
    assert settings_map(db)["lab_ia_teto_dia"] == "150"


def test_salvar_teto_aceita_ponto_decimal(db):
    asyncio.run(lab_salvar(_post_de("/admin/lab", {
        "csrf": "teste-csrf",
        "lab_ia_teto_dia_reais": "2.00",
    }), db))
    assert settings_map(db)["lab_ia_teto_dia"] == "200"


def test_salvar_teto_invalido_nao_grava_e_mostra_erro(db):
    set_setting(db, "lab_ia_teto_dia", "50")
    db.commit()
    resp = asyncio.run(lab_salvar(_post_de("/admin/lab", {
        "csrf": "teste-csrf",
        "lab_ia_teto_dia_reais": "não é número",
    }), db))
    assert settings_map(db)["lab_ia_teto_dia"] == "50"
    assert resp.status_code == 200
    assert "inválid" in resp.body.decode().lower()


def test_salvar_modelo_persiste(db):
    asyncio.run(lab_salvar(_post_de("/admin/lab", {
        "csrf": "teste-csrf",
        "lab_ia_modelo": "claude-haiku-4-5-outro",
    }), db))
    assert settings_map(db)["lab_ia_modelo"] == "claude-haiku-4-5-outro"


# ------------------------------------------------------------------- chave API

def test_api_key_nunca_ecoa_valor_completo_na_tela(db):
    set_setting(db, "anthropic_api_key", "sk-ant-segredo-1234")
    db.commit()
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    assert "sk-ant-segredo-1234" not in corpo
    assert "1234" in corpo  # só os últimos 4 chars, como indicador


def test_api_key_sem_chave_configurada_mostra_aviso(db):
    resp = asyncio.run(lab_painel(_get_de("/admin/lab"), db))
    corpo = resp.body.decode()
    assert "nenhuma chave configurada" in corpo.lower()


def test_api_key_preenchida_persiste(db):
    resp = asyncio.run(lab_salvar(_post_de("/admin/lab", {
        "csrf": "teste-csrf",
        "anthropic_api_key": "sk-ant-nova-chave",
    }), db))
    assert resp.status_code == 303
    assert settings_map(db)["anthropic_api_key"] == "sk-ant-nova-chave"


def test_api_key_vazia_no_post_mantem_a_atual(db):
    set_setting(db, "anthropic_api_key", "sk-ant-ja-configurada")
    db.commit()
    asyncio.run(lab_salvar(_post_de("/admin/lab", {"csrf": "teste-csrf"}), db))
    assert settings_map(db)["anthropic_api_key"] == "sk-ant-ja-configurada"


def test_caixa_de_remover_apaga_a_chave_api(db):
    set_setting(db, "anthropic_api_key", "sk-ant-ja-configurada")
    db.commit()
    asyncio.run(lab_salvar(_post_de("/admin/lab", {
        "csrf": "teste-csrf",
        "anthropic_api_key_remover": "on",
    }), db))
    assert settings_map(db)["anthropic_api_key"] == ""


# --------------------------------------------------------------------- menu

def test_entrada_do_lab_no_menu_do_admin():
    conteudo = open("app/templates/admin/base.html", encoding="utf-8").read()
    assert '/admin/lab' in conteudo
