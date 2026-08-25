"""Motor de sandbox do Lab de Demos (§4/§8 da spec).

Cada visitante ganha um `LabSandbox` isolado no primeiro acesso a qualquer
rota do Lab: cookie `lf_lab_sandbox` (httponly, 24h) guarda um token opaco
(`secrets.token_urlsafe(24)` — sem dado pessoal, §9.8) que identifica a linha
em `lab_sandbox`. Cookie ausente ou apontando para um sandbox vencido ganha
um sandbox novo, transparente para o visitante — o velho só some na limpeza
diária (`limpar_expirados`), não na hora.

Datas em UTC (`dt.datetime.now(dt.timezone.utc)`), mesma convenção do resto
do módulo (ver docstring de `app/lab/models.py`). O SQLite do repo devolve
`datetime` sem tzinfo em leituras (mesmo comportamento documentado em
`app/services/previas.py`), por isso toda comparação abaixo normaliza o valor
lido antes de comparar com "agora".
"""
from __future__ import annotations

import datetime as dt
import secrets

from fastapi import Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from .models import LabSandbox
from .seeds_demo import semear_cenario

COOKIE_NOME = "lf_lab_sandbox"
COOKIE_MAX_AGE = 86400  # 24h — mesma janela do TTL do sandbox (§8 da spec)
TTL_HORAS = 24
MAX_SANDBOXES_ATIVOS = 200


def _sem_fuso_para_utc(quando: dt.datetime) -> dt.datetime:
    if quando.tzinfo is None:
        return quando.replace(tzinfo=dt.timezone.utc)
    return quando


def reciclar_se_lotado(db: Session, limite: int = MAX_SANDBOXES_ATIVOS) -> None:
    """Guarda-chuva do §8: se os sandboxes ativos já estão no teto (ou
    acima), apaga o mais antigo antes de abrir espaço para um novo. Chamada
    de dentro de `obter_ou_criar_sandbox`, sempre antes de inserir o
    sandbox novo — assim o total nunca ultrapassa `limite`."""
    ativos = db.query(LabSandbox).count()
    if ativos >= limite:
        mais_antigo = (
            db.query(LabSandbox).order_by(LabSandbox.criado_em.asc()).first()
        )
        if mais_antigo is not None:
            db.delete(mais_antigo)
            db.commit()


def limpar_expirados(db: Session) -> int:
    """Apaga todo `LabSandbox` vencido — e, por FK `ondelete="CASCADE"` com
    `PRAGMA foreign_keys=ON` (ver `app/database.py`), tudo que pende dele nas
    tabelas de demo. `LabLead` nunca tem `sandbox_id` (§5/§10 da spec) e por
    isso nunca é tocado aqui. Devolve quantos sandboxes foram removidos —
    é o número que o cron diário imprime no log."""
    agora = dt.datetime.now(dt.timezone.utc)
    vencidos = [
        s for s in db.query(LabSandbox).all()
        if _sem_fuso_para_utc(s.expira_em) <= agora
    ]
    for sandbox in vencidos:
        db.delete(sandbox)
    if vencidos:
        db.commit()
    return len(vencidos)


def _criar_sandbox(db: Session, demo: str) -> LabSandbox:
    reciclar_se_lotado(db, limite=MAX_SANDBOXES_ATIVOS)
    agora = dt.datetime.now(dt.timezone.utc)
    sandbox = LabSandbox(
        token=secrets.token_urlsafe(24),
        demo_origem=demo,
        expira_em=agora + dt.timedelta(hours=TTL_HORAS),
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    semear_cenario(db, sandbox)
    return sandbox


def obter_ou_criar_sandbox(
    request: Request, response: Response, db: Session, demo: str
) -> LabSandbox:
    """Ponto único de entrada do sandbox: toda rota do Lab que precisa de um
    visitante identificado chama isto primeiro (dentro do corpo da rota, com
    `request`/`response`/`db` já injetados por `Depends` e `demo` fixo do
    endpoint — não é usada como `Depends(...)` direto porque `demo` varia por
    rota, não por requisição).

    Lê o cookie `lf_lab_sandbox`; se ausente, inválido ou vencido, cria um
    sandbox novo (token opaco, TTL 24h) e regrava o cookie. Sempre regrava o
    cookie mesmo quando o sandbox já existia — renova a janela dos 24h a
    cada visita, como qualquer cookie de sessão "rolante"."""
    token = request.cookies.get(COOKIE_NOME)
    sandbox: LabSandbox | None = None
    if token:
        sandbox = (
            db.query(LabSandbox).filter(LabSandbox.token == token).one_or_none()
        )
        if sandbox is not None:
            agora = dt.datetime.now(dt.timezone.utc)
            if _sem_fuso_para_utc(sandbox.expira_em) <= agora:
                sandbox = None  # vencido: ganha um novo; o velho fica até a limpeza

    if sandbox is None:
        sandbox = _criar_sandbox(db, demo)

    response.set_cookie(
        COOKIE_NOME,
        sandbox.token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,  # mesma regra dos outros cookies do site (lf_consent/lf_lang)
    )
    return sandbox


if __name__ == "__main__":
    # Invocado pelo cron do servidor uma vez por dia — ver deploy/subir.sh,
    # mesmo padrão do `python -m app.services.previas` (renovar-previas).
    with SessionLocal() as _db:
        _apagados = limpar_expirados(_db)
    print(f"{_apagados} sandbox(es) expirado(s) removido(s)")
    # F1 (herança do Plano 1, resolvida na Task 2): NÃO chama
    # `podar_janelas_vazias()` aqui. O cron dispara este módulo como um
    # PROCESSO NOVO a cada execução (`python -m app.lab.sandbox`), com sua
    # própria memória vazia — o `_requisicoes` de `app.lab.protecao` que
    # este processo enxergaria é sempre `{}` aqui dentro, nunca o dict de
    # verdade que o servidor web (uvicorn, processo separado e de vida
    # longa) vem acumulando a cada requisição. Chamar a função neste ponto
    # seria podar um dict fantasma: um no-op garantido, disfarçado de
    # manutenção real. A poda de verdade agora é INLINE, dentro do próprio
    # `limitar_taxa` (a cada `INTERVALO_PODA_INLINE` chamadas, no mesmo
    # processo/memória que populou o dict) — `podar_janelas_vazias()`
    # continua exportada só para os testes chamarem direto
    # (`tests/lab/test_protecao.py`).
