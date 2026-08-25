"""Router público do Lab de Demos (`/lab`, §4 da spec).

A Task 2 abriu a vitrine como placeholder (texto cru, sem template). A
Task 3 substitui por `lab/vitrine.html` — página DO SITE (herda o
`base.html` do site, não `lab/_base_demo.html`: §3 da spec, "a vitrine não
é tela de demo") — e as três rotas de entrada das demos (Admita/Notável/
Caderneta). Cada rota de demo cria o sandbox do visitante com o
`demo_origem` REAL ("rh"/"fin"/"escola" — ver docstring de `LabSandbox` em
`app/lab/models.py` e `_MODELO_POR_DEMO` em `app/lab/protecao.py`); os
nomes públicos da URL ("admita"/"notavel"/"caderneta") são os nomes de
marca aprovados, usados só pelo template (`_base_demo.html`, contexto
`demo`) e pela faixa de conversão. Por ora as três só renderizam um
conteúdo mínimo "em construção interna" — as telas completas (esteira,
painel, diário) chegam nas Tasks 4-9.

`limitar_taxa` (F1/F2 do rate limiter, `app/lab/protecao.py`) é dependency
do ROUTER inteiro (`dependencies=[Depends(limitar_taxa)]` no construtor de
`APIRouter`), não de cada rota isolada: toda rota que nascer aqui, inclusive
nas tasks futuras, herda a proteção automaticamente sem que quem escreve a
rota precise lembrar de declarar de novo. O FastAPI mescla essa dependency
de router em `route.dependant.dependencies` de CADA rota individual — não é
um atalho que escapa da varredura programática de
`tests/lab/test_rotas_protegidas.py`, que confere isso rota por rota.

F3 (herança do Plano 1, fechada nesta task): `/lab/_sandbox/ping` também
passou a carregar `limitar_taxa` — sem isso, um script batendo nela sem
parar cria (e, no teto de 200, recicla) um `LabSandbox` por requisição,
uma via de DoS de reciclagem que o rate limit das outras rotas nunca
cobriu."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from . import admita as _admita_dados
from .models import LabSandbox
from .protecao import limitar_taxa
from .sandbox import COOKIE_NOME, obter_ou_criar_sandbox

router = APIRouter(prefix="/lab", dependencies=[Depends(limitar_taxa)])

# demo pública (nome de marca, usado na URL e no contexto `demo` de
# `_base_demo.html`) -> demo_origem interno gravado em `LabSandbox`
# (mesmo vocabulário "rh"/"fin"/"escola" de `_MODELO_POR_DEMO`, em
# `app/lab/protecao.py`).
_DEMO_ORIGEM = {"admita": "rh", "notavel": "fin", "caderneta": "escola"}


@router.get("", response_class=HTMLResponse)
async def vitrine(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Vitrine do Lab: página DO SITE, indexável (Task 3, §3/§10 da spec).

    Renderiza por `render()` de `app.main` (mesmo funil de toda página
    pública do site — `base_ctx` traz `site`/`profile` para o cabeçalho e
    rodapé herdados) e não por `templates.TemplateResponse` direto: ao
    contrário das rotas de demo abaixo, esta tela não cria sandbox (a
    vitrine não é tela de demo, só os 3 cliques para dentro dela)."""
    # Import tardio pelo mesmo motivo do `_tela_da_demo`: evitar ciclo entre
    # `app.main` (que importa este router) e este módulo.
    from ..main import render
    from ..routers.public import base_ctx

    return render(request, "lab/vitrine.html", base_ctx(db))


async def _tela_da_demo(demo: str, request: Request, db: Session) -> HTMLResponse:
    # Import tardio: `app.main` importa este router em nível de módulo
    # (`from .lab import rotas as lab_router`) — importar `templates` daqui
    # de cima criaria um ciclo na primeira carga do processo. Mesmo padrão
    # já usado por `app/nodal/rotas_admin.py` com `from ..main import render`.
    from ..main import templates

    resposta = templates.TemplateResponse(
        request, "lab/_em_construcao.html", {"demo": demo}
    )
    # O cookie do sandbox precisa ser gravado NESTA resposta, não num
    # `Response` injetado por `Depends` à parte: o FastAPI só copia os
    # cabeçalhos do `Response` injetado para a resposta final quando a rota
    # devolve um valor "cru" (dict, etc.) que ELE monta numa resposta nova —
    # quando a rota já devolve um objeto `Response` (como `TemplateResponse`
    # aqui), esse objeto SAI como está, sem merge nenhum, e um `set_cookie`
    # no `Response` injetado seria descartado (achado ao vivo: o cookie
    # simplesmente não aparecia na resposta HTTP das rotas de demo). Por
    # isso `obter_ou_criar_sandbox` recebe `resposta` diretamente aqui, e
    # não um `response: Response` de `Depends`.
    obter_ou_criar_sandbox(request, resposta, db, demo=_DEMO_ORIGEM[demo])
    return resposta


def _exigir_sandbox(request: Request, db: Session = Depends(get_db)) -> LabSandbox:
    """Dependency das rotas de MUTAÇÃO do Admita (POST, Task 4): exige um
    sandbox JÁ EXISTENTE e válido — nunca cria um aqui. Uma rota de mutação
    devolve um FRAGMENTO html (o corpo que o `fetch` do admita.js troca na
    tela), não a página inteira: o navegador nunca aplicaria um
    `Set-Cookie` "escondido" dentro dessa resposta do jeito que aplicaria
    numa navegação normal, então criar sandbox aqui só produziria um
    cookie que o visitante nunca de fato recebe. O primeiro `GET
    /lab/admita` (que já roda `obter_ou_criar_sandbox`) é sempre o passo
    anterior obrigatório de qualquer visitante."""
    token = request.cookies.get(COOKIE_NOME)
    sandbox: LabSandbox | None = None
    if token:
        sandbox = db.query(LabSandbox).filter(LabSandbox.token == token).one_or_none()
    if sandbox is None:
        raise HTTPException(
            status_code=400,
            detail="Sessão da demonstração expirada. Recarregue a página para continuar.",
        )
    agora = dt.datetime.now(dt.timezone.utc)
    expira = sandbox.expira_em
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=dt.timezone.utc)
    if expira <= agora:
        raise HTTPException(
            status_code=400,
            detail="Sua demonstração expirou. Recarregue a página para começar outra.",
        )
    return sandbox


def _renderizar_shell_admita(db: Session, sandbox: LabSandbox) -> str:
    """Renderiza `lab/admita/_shell.html` — o fragmento que TODA rota de
    mutação do Admita devolve (mesmo miolo que `esteira.html` também
    inclui no primeiro carregamento): sidebar com contadores reais,
    quadro kanban completo e a trilha de auditoria mais recente, todos
    recalculados do banco depois da mutação que acabou de acontecer."""
    from ..main import templates

    ctx = _admita_dados.montar_contexto(db, sandbox)
    return templates.get_template("lab/admita/_shell.html").render(**ctx)


@router.get("/admita")
async def admita(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Esteira de admissão (Task 4, §6.1 da spec) — tela cheia de verdade,
    não mais o placeholder "em construção". Precisa do sandbox ANTES de
    montar o contexto (a tela mostra os candidatos DELE), por isso não usa
    `_tela_da_demo` (que renderiza sem olhar pro banco): grava o cookie
    numa `Response` descartável primeiro, copia só o cabeçalho
    `set-cookie` para a resposta de verdade depois — o mesmo motivo já
    documentado em `_tela_da_demo` (um `Response` de `Depends` à parte não
    seria mesclado à resposta final de uma rota que devolve
    `TemplateResponse` pronta)."""
    from ..main import templates

    resposta_cookie = Response()
    sandbox = obter_ou_criar_sandbox(request, resposta_cookie, db, demo="rh")
    ctx = _admita_dados.montar_contexto(db, sandbox)
    resposta = templates.TemplateResponse(
        request, "lab/admita/esteira.html", {"demo": "admita", **ctx}
    )
    cookie = resposta_cookie.headers.get("set-cookie")
    if cookie:
        resposta.headers["set-cookie"] = cookie
    return resposta


@router.post("/admita/candidatos")
async def admita_criar_candidato(
    nome: str = Form(...),
    cargo: str = Form(...),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Nova candidatura, via o modal (Task 4). `origem="visitante"` e
    `checar_limite_registros` (teto de 10) acontecem dentro de
    `admita.criar_candidato`."""
    try:
        _admita_dados.criar_candidato(db, sandbox, nome, cargo)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/candidatos/{candidato_id}/mover")
async def admita_mover_candidato(
    candidato_id: int,
    direcao: str = Form(...),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Seta de mover (§6.1): `direcao` é `"proxima"` ou `"anterior"` — o
    lado que a seta aponta, não um índice numérico, para o bug do dono (a
    seta que move para a esquerda apontava para a direita) nunca poder se
    repetir aqui: o nome do parâmetro já é a direção visual."""
    try:
        _admita_dados.mover_candidato(db, sandbox, candidato_id, direcao)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/candidatos/{candidato_id}/aprovar-rh")
async def admita_aprovar_rh(
    candidato_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        _admita_dados.aprovar_rh(db, sandbox, candidato_id)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/candidatos/{candidato_id}/aprovar-gestor")
async def admita_aprovar_gestor(
    candidato_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        _admita_dados.aprovar_gestor(db, sandbox, candidato_id)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/candidatos/{candidato_id}/documentos/{documento_id}/alternar")
async def admita_alternar_documento(
    candidato_id: int,
    documento_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        _admita_dados.alternar_documento(db, sandbox, candidato_id, documento_id)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/candidatos/{candidato_id}/entrevista")
async def admita_agendar_entrevista(
    candidato_id: int,
    data: str = Form(""),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Marca, remarca ou desmarca a entrevista pelo calendário do painel de
    agenda. `data` vazio desmarca; qualquer outro valor é validado como data
    ISO dentro da janela permitida em `admita.agendar_entrevista`."""
    try:
        _admita_dados.agendar_entrevista(db, sandbox, candidato_id, data)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/cargos")
async def admita_criar_cargo(
    nome: str = Form(...),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Cria um cargo na lista DESTE sandbox (dropdown de nova candidatura)."""
    try:
        _admita_dados.criar_cargo(db, sandbox, nome)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/cargos/{cargo_id}")
async def admita_renomear_cargo(
    cargo_id: int,
    nome: str = Form(...),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        _admita_dados.renomear_cargo(db, sandbox, cargo_id, nome)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.post("/admita/cargos/{cargo_id}/excluir")
async def admita_excluir_cargo(
    cargo_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Excluir um cargo NÃO mexe no cargo de quem já foi cadastrado com ele:
    a ficha do candidato guarda o que valia no dia."""
    try:
        _admita_dados.excluir_cargo(db, sandbox, cargo_id)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_admita(db, sandbox))


@router.get("/notavel")
async def notavel(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return await _tela_da_demo("notavel", request, db)


@router.get("/caderneta")
async def caderneta(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return await _tela_da_demo("caderneta", request, db)


@router.get("/_sandbox/ping")
async def sandbox_ping(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    """Garante que o visitante tem um sandbox válido (cria um se faltar ou
    se o cookie apontar para um vencido) e devolve `{"ok": true}`.

    `demo="lab"` aqui é só um marcador genérico de origem — esta rota não
    pertence a nenhuma das três demos; as rotas de entrada de cada demo
    (`/lab/admita`, `/lab/notavel`, `/lab/caderneta`, acima) é que passam o
    `demo_origem` real ("rh"/"fin"/"escola")."""
    obter_ou_criar_sandbox(request, response, db, demo="lab")
    return {"ok": True}
