"""Testes vinculantes da §9 da spec (Task 3 do Plano 1) — cada regra de
segurança do Lab tem um teste automatizado que a garante, não uma promessa
de código review.

Hoje `app/templates/lab/` não existe e nenhum template de `app/templates/admin/`
cita "lab" (as telas do Lab são do Plano 2 — gate §12b). Os testes abaixo
passam vazios de propósito: eles existem para pegar a primeira vez que um
template do Lab nascer com `|safe` sobre dado de visitante, ou uma rota do
Lab ganhar um parâmetro `UploadFile`/`File`.
"""
import inspect
from pathlib import Path

from fastapi import UploadFile

from app.lab.protecao import varrer_safe_em_templates_lab
from app.main import app


def _rotas_efetivas(routes):
    """Achata a árvore de rotas do app.

    FastAPI >= 0.141 passou a incluir routers preguiçosamente: `app.routes`
    devolve nós `_IncludedRouter` (um wrapper em volta do `APIRouter`
    original) em vez da lista plana de `APIRoute` que versões antigas
    devolviam direto. Precisamos descer em `original_router.routes` para
    chegar nas rotas de verdade — sem isto a varredura roda vazia e o teste
    "passa" sem checar nada."""
    achatadas = []
    for rota in routes:
        if type(rota).__name__ == "_IncludedRouter":
            achatadas.extend(_rotas_efetivas(rota.original_router.routes))
        else:
            achatadas.append(rota)
    return achatadas


# --------------------------------------------------------- §9.1 zero upload

def test_nenhuma_rota_do_lab_aceita_upload():
    todas = _rotas_efetivas(app.routes)
    rotas_lab = [r for r in todas if getattr(r, "path", "").startswith("/lab")]
    assert rotas_lab, "esperava ao menos a rota /lab/_sandbox/ping (Task 2)"
    for rota in rotas_lab:
        sig = inspect.signature(rota.endpoint)
        for parametro in sig.parameters.values():
            assert parametro.annotation is not UploadFile, rota.path
            assert "UploadFile" not in str(parametro.annotation), rota.path


# --------------------------------------------------- §9.2 texto de visitante é texto morto

def test_nenhum_safe_sobre_dado_de_visitante_nos_templates_do_lab():
    # Hoje a varredura pode devolver lista vazia (nenhum template do Lab ou
    # do admin-que-cita-lab existe ainda) — é o comportamento esperado desta
    # task. Quando o Plano 2/Task 7 criar `app/templates/lab/*.html` e
    # `app/templates/admin/lab.html`, este mesmo teste passa a valer de
    # verdade contra eles, sem precisar ser reescrito.
    violacoes = varrer_safe_em_templates_lab()
    assert violacoes == [], violacoes


def test_a_varredura_encontra_ao_menos_um_template_do_lab():
    # Sentinela POSITIVA (pendência herdada da rodada de conserto da Task 3,
    # amarrada à Task 7 no ledger): o teste acima só prova algo de verdade
    # se a varredura de fato ENCONTRAR arquivo — passando vazio para sempre
    # ele não pegaria nada, nem um `|safe` novo. `admin/lab.html` (Task 7)
    # é o primeiro template do Lab a nascer, então a partir daqui a lista de
    # alvos não pode mais vir vazia. Reimplementa a MESMA lógica de busca de
    # `varrer_safe_em_templates_lab` (não a chama, porque aquela função só
    # devolve violações, não os alvos varridos) — arquivo autorizado a mexer
    # é só este teste, `varrer_safe_em_templates_lab` continua intocada.
    raiz = Path("app/templates")
    alvos: list[Path] = []
    pasta_lab = raiz / "lab"
    if pasta_lab.exists():
        alvos.extend(pasta_lab.rglob("*.html"))
    pasta_admin = raiz / "admin"
    if pasta_admin.exists():
        for caminho in pasta_admin.rglob("*.html"):
            if "lab" in caminho.read_text(encoding="utf-8"):
                alvos.append(caminho)
    assert len(alvos) >= 1, "esperava achar ao menos admin/lab.html citando 'lab'"
    assert any(p.name == "lab.html" for p in alvos)
