"""Salvar `destaque_ordem` pelo formulário do case (19/08).

Campo numérico "Ordem no destaque" em `/admin/cases/{id}` — a alternativa
robusta ao arrasto, escolhida porque o padrão de arrasto de todo o case
(`#caseList` -> `/admin/cases/reorder`) já ficou órfão desde a reorganização
do painel (commit ee40961: `admin/cases.html` saiu, `cases_lista.html`
entrou, e nada mais aponta `#caseList`) — reaproveitá-lo hoje reordenaria a
lista inteira de cases, não só os destaques, por um caminho que a tela atual
nem desenha mais.

Segue o padrão de tests/test_admin_case_capa_botoes.py: `apply_case_form`
chamado direto, sem TestClient nem servidor.
"""
import asyncio

from app.models import Case
from app.routers.admin import apply_case_form

from ._multipart_de_verdade import post_multipart


def _salvar(db, case: Case, **campos) -> None:
    base = {"csrf": "teste-csrf", "title_pt": "Case de teste"}
    asyncio.run(apply_case_form(
        post_multipart("/admin/cases/1", {**base, **campos}, {}), db, case))


def test_ordem_digitada_e_salva(db):
    case = Case(title_pt="", slug="")
    _salvar(db, case, featured="on", destaque_ordem="2")
    assert case.destaque_ordem == 2


def test_campo_vazio_cai_no_default_999(db):
    """Quem nunca mexeu no campo não pode ficar com erro nem com 0 — 0
    passaria na frente de todo mundo que já tem uma ordem escolhida a dedo."""
    case = Case(title_pt="", slug="")
    _salvar(db, case, featured="on", destaque_ordem="")
    assert case.destaque_ordem == 999


def test_valor_nao_numerico_nao_derruba_o_formulario_e_cai_no_default(db):
    """Campo number do navegador já barra letra, mas a rota não pode confiar
    só nisso — um POST direto (ou um navegador furando o próprio input) com
    texto no campo tem que cair no default, não estourar 500."""
    case = Case(title_pt="", slug="")
    _salvar(db, case, featured="on", destaque_ordem="abc")
    assert case.destaque_ordem == 999


def test_ordem_negativa_e_aceita_para_furar_a_fila(db):
    """Número negativo é válido: é como o dono coloca um destaque na frente de
    tudo sem precisar renumerar os que já tinham ordem 1, 2, 3."""
    case = Case(title_pt="", slug="")
    _salvar(db, case, featured="on", destaque_ordem="-1")
    assert case.destaque_ordem == -1


def test_ordem_e_independente_do_sort_geral_do_painel(db):
    """`destaque_ordem` não é o mesmo campo que `Case.sort` (a ordem geral do
    painel, usada no dashboard e como desempate) — salvar um não pode mexer
    no outro."""
    case = Case(title_pt="", slug="", sort=7)
    _salvar(db, case, featured="on", destaque_ordem="3")
    assert case.destaque_ordem == 3
    assert case.sort == 7
