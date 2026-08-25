"""Camada de proteção do Lab de Demos — §8 (limites) e §9 (segurança) da
spec, cada regra com seu teste (`tests/lab/test_protecao.py` e
`tests/lab/test_regras_seguranca.py`).

Este módulo NÃO cria rotas nem sobe servidor: é biblioteca pura + uma
dependency FastAPI (`limitar_taxa`), consumida pelas rotas de cada demo
(Plano 2) e pelos guardiões de IA/PDF/e-mail (Tasks 4/5/7 — que enforçam
`MAX_IA_POR_SANDBOX`, `MAX_PDFS` e `MAX_EMAILS` contra os contadores de
`LabSandbox`; este módulo só declara os números)."""
from __future__ import annotations

import collections
import time
import unicodedata
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.geo import ip_do_pedido
from .models import LabAluno, LabCandidato, LabNota, LabSandbox
# F4 (herança do Plano 1): MAX_SANDBOXES_ATIVOS já existia em sandbox.py
# (é lá que o teto é de fato aplicado, em `reciclar_se_lotado`) antes deste
# módulo nascer — a duplicata `MAX_SANDBOXES = 200` que existia aqui virou
# um segundo número que só coincidia com o de lá por acaso. Agora só existe
# a constante de sandbox.py; este módulo reexporta com o nome MAX_SANDBOXES
# porque é o nome que a documentação de limites deste arquivo (e os
# importadores existentes, ex. tests/lab/test_protecao.py) já usam.
from .sandbox import COOKIE_NOME, MAX_SANDBOXES_ATIVOS as MAX_SANDBOXES

from ..config import settings

# ---------------------------------------------------------------- limites --
# Números verbatim da §8 da spec — "o limite precisa ser baixo para o
# usuário não abusar dos testes" (palavras do Leandro, §2 item 8). Rejeição,
# nunca truncamento.

MAX_CURRICULO = 5000
MAX_EXTRATO = 2000
MAX_CAMPO = 200
MAX_REGISTROS_POR_DEMO = settings.lab_max_registros_por_demo
MAX_IA_POR_SANDBOX = settings.lab_max_ia_por_sandbox
MAX_EMAILS = settings.lab_max_emails
MAX_PDFS = settings.lab_max_pdfs
RATE_LIMIT_POR_MIN = settings.lab_rate_por_min


# ------------------------------------------------------------- §9.3 texto --

def validar_texto(texto: str, max_chars: int) -> str:
    """Levanta `ValueError` (mensagem em PT-BR) se `texto`:

    - exceder `max_chars` (rejeição, nunca truncamento — §8);
    - contiver caractere de controle ou invisível fora de `\\n`/`\\t`
      (categorias Unicode `Cc`/`Cf`/`Cs` — cobre nulo, ESC, zero-width space,
      par substituto solto etc.; `\\n` e `\\t` também são `Cc` mas ficam
      liberados por serem os únicos formatadores de texto simples que um
      campo do Lab aceita);
    - não puder ser codificado como UTF-8 (cinto e suspensório da checagem
      acima: um par substituto solto — ex.: `"\\ud800"` — passa pela
      categoria `Cs` só se o filtro acima falhar por qualquer motivo, mas
      SEMPRE quebraria a gravação no banco com `UnicodeEncodeError` mais
      tarde, 500 em vez de mensagem elegante; por isso a checagem dupla).

    Quebras de linha são normalizadas ANTES de qualquer outra checagem:
    `\\r\\n` (Windows) e `\\r` solto (Mac clássico) viram `\\n`. Um textarea
    de formulário HTML clássico reinsere `\\r\\n` na colagem independente do
    sistema operacional do visitante, e `\\r` sozinho é categoria Unicode
    `Cc` — sem esta normalização primeiro, colar um texto vindo do Windows
    seria sempre rejeitado pelo filtro de controle abaixo. A normalização
    acontece antes da checagem de tamanho também, para que o limite reflita
    o texto que de fato vai ser gravado.

    Devolve o texto normalizado quando válido."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    if len(texto) > max_chars:
        raise ValueError(
            f"texto excede o máximo de {max_chars} caracteres (recebido {len(texto)})."
        )
    for caractere in texto:
        if caractere in ("\n", "\t"):
            continue
        categoria = unicodedata.category(caractere)
        if categoria in ("Cc", "Cf", "Cs"):
            raise ValueError(
                "texto contém caractere de controle ou invisível não permitido."
            )
    try:
        texto.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "texto contém um caractere inválido e não pode ser salvo."
        ) from exc
    return texto


# ------------------------------------------------- §8 registros por demo --

# "Registros criados por visitante" (§8): o que cada demo deixa o visitante
# ADICIONAR (não o que o seed já povoou). RH conta candidatos, Financeiro
# conta notas emitidas, Escola conta alunos adicionados — mesmos exemplos
# citados literalmente na spec.
_MODELO_POR_DEMO: dict[str, type] = {
    "rh": LabCandidato,
    "fin": LabNota,
    "escola": LabAluno,
}


def checar_limite_registros(db: Session, sandbox: LabSandbox, demo: str) -> None:
    """Levanta `ValueError` se `sandbox` já tem `MAX_REGISTROS_POR_DEMO`
    registros do tipo que `demo` cria (§8) — chamar ANTES de inserir o
    registro novo; se não levantar, a inserção pode prosseguir.

    Conta só `origem == "visitante"` (ruling da revisão da Task 3): "Seeds
    não contam" (§8) — o cenário fictício que `semear_cenario`/`seeds_demo`
    (Task 6) povoa no nascimento do sandbox não deve consumir o teto que
    existe para limitar o que o VISITANTE cria. A Task 6, ao gravar os
    registros do seed, é OBRIGADA a passar `origem="seed"` explicitamente —
    sem isso, o seed conta contra o próprio teto que deveria estar isento."""
    modelo = _MODELO_POR_DEMO.get(demo)
    if modelo is None:
        raise ValueError(f"demo desconhecida: {demo!r}")
    total = (
        db.query(modelo)
        .filter(modelo.sandbox_id == sandbox.id)
        .filter(modelo.origem == "visitante")
        .count()
    )
    if total >= MAX_REGISTROS_POR_DEMO:
        raise ValueError(
            f"limite de {MAX_REGISTROS_POR_DEMO} registros desta demo atingido "
            "neste sandbox. Apague algo antes de criar outro."
        )


# --------------------------------------------------------- §8 rate limit --
# Janela deslizante em memória de processo (dict de chave -> deque de
# timestamps), o mesmo padrão do rate limit de login em `app/auth.py`.
#
# LIMITAÇÃO DOCUMENTADA: isto vive na memória de UM processo/worker (§15 da
# spec — "1 vCPU", sem worker novo). Não sobrevive a reinício do processo e
# não é compartilhado entre múltiplos workers caso o deploy um dia ganhe
# mais de um. Aceitável aqui: o site roda um único processo, e um reinício
# apagar contadores de rate limit é o pior caso "o visitante ganha mais
# 30 requisições de graça" — não é uma falha de segurança, é folga.

_JANELA_SEGUNDOS = 60
_requisicoes: dict[str, collections.deque] = {}

# F1 (herança do Plano 1, Task 2): a cada INTERVALO_PODA_INLINE chamadas de
# `limitar_taxa` NESTE processo, varre `_requisicoes` e descarta as chaves
# cujo deque esvaziou (ver `podar_janelas_vazias` abaixo). "Inline" porque é
# a única forma de podar o dict de verdade: o cron diário roda como um
# PROCESSO NOVO (`python -m app.lab.sandbox`), com sua própria memória vazia
# — ele nunca enxerga o `_requisicoes` do servidor web (uvicorn, processo
# de vida longa). Um número redondo, não um valor da spec: alto o bastante
# para a varredura (O(chaves)) não rodar a cada requisição, baixo o
# bastante para o dict nunca crescer sem controle entre duas podas.
INTERVALO_PODA_INLINE = 500
_chamadas_desde_a_ultima_poda = 0


def _chave_taxa(request: Request, db: Session) -> str:
    """Chave do balde de taxa: IP de quem pediu (mesmo padrão da casa atrás
    do nginx, `app.services.geo.ip_do_pedido`) e, só quando o cookie do
    sandbox aponta para um `LabSandbox` que EXISTE de verdade (consulta
    indexada pela `unique`/`index` de `LabSandbox.token`), o token entra
    junto na chave — separando visitantes diferentes atrás do mesmo IP.

    F2 (herança do Plano 1): a chave antiga era só o token cru do cookie,
    sem checar nada — um cookie forjado (qualquer string) ou reescrito a
    cada requisição abria um balde NOVO e vazio toda vez, escapando do teto
    por minuto de graça. Agora um token que não bate com nenhum sandbox real
    cai na MESMA chave que "sem cookie nenhum" (só IP): forjar ou trocar o
    cookie não multiplica baldes."""
    ip = ip_do_pedido(request) or "desconhecido"
    token = request.cookies.get(COOKIE_NOME)
    if token:
        token_valido = (
            db.query(LabSandbox.id).filter(LabSandbox.token == token).first()
            is not None
        )
        if token_valido:
            return f"{ip}:{token}"
    return f"ip:{ip}"


def limitar_taxa(request: Request, db: Session = Depends(get_db)) -> None:
    """Dependency FastAPI: `RATE_LIMIT_POR_MIN` requisições por minuto por
    chave (IP+token validado, ou só IP — ver `_chave_taxa`). Acima disso,
    levanta `HTTPException(429)` (§8 — "excedeu -> 429 com tela amigável"; a
    tela amigável é responsabilidade de quem chama, aqui só o status).

    Poda inline (F1): a cada `INTERVALO_PODA_INLINE` chamadas desta função
    neste processo, varre e descarta do dict as chaves cujo deque esvaziou —
    ver comentário acima de `INTERVALO_PODA_INLINE` sobre por que isto não
    pode viver no cron diário."""
    global _chamadas_desde_a_ultima_poda

    chave = _chave_taxa(request, db)
    agora = time.monotonic()
    fila = _requisicoes.setdefault(chave, collections.deque())
    while fila and agora - fila[0] > _JANELA_SEGUNDOS:
        fila.popleft()
    if len(fila) >= RATE_LIMIT_POR_MIN:
        raise HTTPException(
            status_code=429,
            detail="Muitas requisições em pouco tempo. Espere um instante e tente de novo.",
        )
    fila.append(agora)

    _chamadas_desde_a_ultima_poda += 1
    if _chamadas_desde_a_ultima_poda >= INTERVALO_PODA_INLINE:
        _chamadas_desde_a_ultima_poda = 0
        podar_janelas_vazias()


def podar_janelas_vazias() -> int:
    """Remove de `_requisicoes` as chaves cujo deque esvaziou de vez (nenhuma
    requisição nos últimos `_JANELA_SEGUNDOS`).

    LEAK que isto conserta: `limitar_taxa` só poda timestamps VELHOS de
    dentro do deque de uma chave quando essa chave faz uma requisição nova —
    um visitante que fez 1 requisição e nunca mais voltou deixa a entrada
    dele (chave -> deque, mesmo que o deque acabe ficando vazio depois de
    podado por outra rota que reusasse a chave) pendurada em `_requisicoes`
    para sempre; o processo não tem outro jeito de saber que aquele
    visitante foi embora. Isto é memória, não segurança: o teto em si nunca
    falha, só o dict cresce sem limite ao longo dos dias.

    F1 (herança do Plano 1): chamada de dentro do próprio `limitar_taxa`, a
    cada `INTERVALO_PODA_INLINE` requisições NESTE processo — não do cron
    diário (`python -m app.lab.sandbox`), que roda como processo novo e por
    isso nunca teria acesso ao `_requisicoes` de verdade (ver comentário em
    `app/lab/sandbox.py::__main__`). Continua exportada standalone porque os
    testes (`tests/lab/test_protecao.py`) chamam direto, sem esperar
    `INTERVALO_PODA_INLINE` requisições de verdade."""
    agora = time.monotonic()
    vazias = []
    for chave, fila in _requisicoes.items():
        while fila and agora - fila[0] > _JANELA_SEGUNDOS:
            fila.popleft()
        if not fila:
            vazias.append(chave)
    for chave in vazias:
        del _requisicoes[chave]
    return len(vazias)


# ------------------------------------------------------- §9.2 texto morto --

_RAIZ_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def varrer_safe_em_templates_lab() -> list[Path]:
    """Devolve os templates que violam a §9.2 ("PROIBIDO `|safe` sobre dado
    de visitante — inclusive nas telas do ADMIN"): todo `.html` dentro de
    `app/templates/lab/` (quando existir) mais todo `.html` de
    `app/templates/admin/` que cite "lab" (telas de admin que exibem leads
    ou gasto do Lab).

    Hoje devolve lista vazia (nenhum template nasceu ainda — Plano 2/Task 7)
    de propósito: o teste que chama isto (`test_regras_seguranca.py`) passa
    vazio agora e passa a valer de verdade assim que os templates surgirem,
    sem precisar ser reescrito."""
    alvos: list[Path] = []

    pasta_lab = _RAIZ_TEMPLATES / "lab"
    if pasta_lab.exists():
        alvos.extend(pasta_lab.rglob("*.html"))

    pasta_admin = _RAIZ_TEMPLATES / "admin"
    if pasta_admin.exists():
        for caminho in pasta_admin.rglob("*.html"):
            if "lab" in caminho.read_text(encoding="utf-8"):
                alvos.append(caminho)

    return [p for p in alvos if "|safe" in p.read_text(encoding="utf-8")]
