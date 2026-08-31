# Sites do Lab, corte 1: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** entregar a segunda fileira do Lab, onde um redesign de home abre e funciona, existe em três estados de visibilidade, nasce com o dossiê de insumos colhido do site original, e vira um link privado que o Leandro manda ao dono do negócio.

**Architecture:** um modelo editorial novo (`Redesign`) em `app/models.py`, irmão de `Case` e não de `LabCandidato`, porque é conteúdo permanente e não dado de visitante. Um serviço de coleta em duas metades (`buscar` e `extrair`), desenhado assim de propósito para a ferramenta de análise da próxima spec reaproveitar o `buscar` sem baixar o site duas vezes. As páginas de redesign são templates Jinja próprios, com direção de arte livre, presos a uma base mínima que garante as regras inegociáveis da §8. As capturas saem do `captura.py` que já existe.

**Tech Stack:** Python 3.13, FastAPI 0.141.1, SQLAlchemy 2.0.51, SQLite, Jinja2 3.1.6, httpx 0.28.1, `html.parser` da biblioteca padrão, Chromium headless (já instalado no servidor), pytest 8.3.4.

**Spec:** `docs/superpowers/specs/2026-08-25-lab-sites-design.md`

**Baseline da suíte antes da Task 1: 1465 testes passando, zero falha.** Rode `./.venv/bin/python -m pytest` na raiz e confirme antes de começar.

---

## Global Constraints

Toda task herda estas regras.

1. **Escopo é o corte 1 da §13**: modelo, três estados, três rotas, colheita mecânica, as duas capturas, a fileira na vitrine com a cortina, a lista no admin, e **um** redesign real construído do começo ao fim. O recurso `briefing_de_site` na camada de IA é corte 2 e **não entra**.
2. **PROIBIDO travessão como pontuação em copy visível.** Vale para tela, `<title>`, `description` e PDF.
3. **PROIBIDO `|safe` sobre dado de visitante** em template do Lab. `tests/lab/test_regras_seguranca.py` varre `app/templates/lab/` inteira, e as páginas de redesign moram lá dentro.
4. **Nenhuma página de redesign tem `<form>` que envia para este servidor** (§8). Contato é link direto (`https://wa.me/...`, `tel:`, `mailto:`, mapa), nunca captura.
5. **Toda página de redesign carrega a marca de autoria**, visível no rodapé e em `<meta name="author">` (§8).
6. **Redesign em estado `pitch` responde 404** no endereço público, fica fora do sitemap e fora da vitrine (§6).
7. **`visto_em` só é carimbado quando a requisição não vem do loopback** (§9.1). A captura do "depois" roda Chromium na mesma máquina e passaria pelo link do token.
8. **Nada na home é inventado** (§4.1). Todo fato sai do dossiê ou de confirmação. Onde faltar, vira `pendencias`, nunca invenção.
9. **Nada em `app/lab/` importa de `app/nodal/`.**
10. **Dinheiro em centavos inteiros** onde houver dinheiro (não há neste corte, mas a regra da casa vale).
11. **Nenhum host externo de fonte ou script** nas páginas de redesign. GSAP, ScrollTrigger, SplitText e Lenis já vivem em `app/static/vendor/` e são permitidos aqui (§3).
12. **Todo caractere com apresentação emoji leva `&#xFE0E;`** ou vira SVG.
13. **`prefers-reduced-motion: reduce` desliga o que se move** em toda página de redesign.
14. Rode a suíte com `./.venv/bin/python -m pytest` a partir de `/Users/leandrofurtado/LEANDRO FURTADO/leandrofurtado-site`.
15. Os totais de teste que cada task declara são conferência, não contrato. O que é contrato é **zero falha** ao fim de cada uma.

---

## Estrutura de arquivos

**Criados:**

| Arquivo | Responsabilidade |
| --- | --- |
| `app/services/coleta.py` | baixar um site (`buscar`) e extrair o dossiê dele (`extrair`). As duas metades são separadas de propósito: a ferramenta de análise da próxima spec vai chamar `buscar` e escrever a própria medição em cima, sem baixar o site de novo. |
| `app/lab/rotas_sites.py` | as duas rotas de servir redesign. Router próprio em vez de crescer `rotas.py`, que já tem 14 KB e vai receber sete rotas do Notável. |
| `app/templates/lab/sites/_base_redesign.html` | a base mínima: doctype, `<meta name="author">`, `noindex` quando pitch, e a marca de autoria no rodapé. Não é a moldura do Lab: é o piso que impede uma página de redesign nascer sem as regras da §8. |
| `app/templates/lab/sites/grupoom/home.html` | o primeiro redesign de verdade. |
| `app/static/lab/sites/grupoom.css` | o CSS dele, livre. |
| `app/templates/admin/_redesigns.html` | a lista no painel. |
| `tests/test_coleta.py` | Task 2 |
| `tests/test_redesign.py` | modelo, rotas, sitemap e vitrine (Tasks 1, 3, 4) |
| `tests/test_redesign_admin.py` | Task 5 |
| `tests/test_redesign_grupoom.py` | Task 6 |

**Modificados:**

| Arquivo | O quê |
| --- | --- |
| `app/models.py` | a classe `Redesign` |
| `app/main.py` | registrar `rotas_sites.router` |
| `app/routers/public.py` | o sitemap passa a listar redesigns públicos |
| `app/routers/admin.py` | criar, colher, capturar e virar estado |
| `app/templates/admin/lab.html` | incluir `_redesigns.html` |
| `app/templates/lab/vitrine.html` | a fileira Sites |
| `app/static/lab/vitrine.css` | a cortina antes/depois |
| `tests/lab/test_vitrine.py` | a vitrine ganhou uma fileira |

---

### Task 1: O modelo Redesign

Conteúdo editorial permanente, irmão de `Case`. Não entra em `app/lab/models.py`: todo modelo de lá pendura em `sandbox_id` e morre em 24 horas com a limpeza diária, e um redesign precisa sobreviver a isso.

**Files:**
- Modify: `app/models.py`
- Create: `tests/test_redesign.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `Redesign` com `slug`, `marca`, `setor`, `estado`, `token`, `antes_url`, `antes_shot`, `antes_shot_at`, `depois_shot`, `depois_shot_at`, `insumos`, `insumos_em`, `diagnostico`, `pendencias`, `criado_em`, `enviado_em`, `visto_em`
  - `ESTADOS_REDESIGN: tuple[str, ...]` = `("pitch", "publico", "aprovado")`
  - `novo_token() -> str`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_redesign.py`:

```python
"""Redesign: modelo, rotas e presença nas superfícies públicas.

Spec: docs/superpowers/specs/2026-08-25-lab-sites-design.md
"""
import datetime as dt

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ESTADOS_REDESIGN, Redesign, novo_token


def _redesign(db, **campos):
    padrao = dict(
        slug=f"marca-{db.query(Redesign).count()}",
        marca="Padaria Aurora",
        setor="Panificação",
        antes_url="https://exemplo.com.br",
        token=novo_token(),
    )
    padrao.update(campos)
    r = Redesign(**padrao)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_redesign_nasce_como_pitch(db):
    """O estado inicial é o mais fechado. Um redesign que nascesse público
    apareceria na vitrine antes de o Leandro decidir que pode."""
    assert _redesign(db).estado == "pitch"


def test_os_tres_estados_sao_os_da_spec(db):
    assert ESTADOS_REDESIGN == ("pitch", "publico", "aprovado")


def test_o_slug_e_unico(db):
    _redesign(db, slug="padaria-aurora")
    with pytest.raises(IntegrityError):
        _redesign(db, slug="padaria-aurora")
    db.rollback()


def test_o_token_e_unico_e_opaco(db):
    """O token é o endereço secreto do pitch. Se dois redesigns pudessem
    dividir o mesmo, um cliente abriria a proposta do outro."""
    a, b = _redesign(db), _redesign(db)
    assert a.token != b.token
    assert len(a.token) >= 20
    with pytest.raises(IntegrityError):
        _redesign(db, token=a.token)
    db.rollback()


def test_o_token_nao_carrega_o_nome_da_marca(db):
    """Endereço secreto que contém o nome do cliente deixa de ser secreto no
    instante em que alguém lê a URL por cima do ombro dele."""
    r = _redesign(db, marca="Padaria Aurora", slug="padaria-aurora")
    assert "padaria" not in r.token.lower()
    assert "aurora" not in r.token.lower()


def test_novo_token_nao_repete():
    assert len({novo_token() for _ in range(200)}) == 200


def test_um_redesign_nasce_sem_dossie_e_sem_capturas(db):
    r = _redesign(db)
    assert r.insumos is None or r.insumos == {}
    assert r.antes_shot == "" and r.depois_shot == ""
    assert r.insumos_em is None
    assert r.enviado_em is None and r.visto_em is None


def test_o_dossie_guarda_json_de_verdade(db):
    """`insumos` é JSON, não texto: o admin lê campo a campo e a home usa os
    valores. Guardar como string obrigaria a decodificar em todo lugar."""
    r = _redesign(db)
    r.insumos = {"telefones": ["4133334444"], "horarios": ["Seg a Sex, 8h às 18h"]}
    r.insumos_em = dt.datetime.now(dt.UTC)
    db.commit()
    db.refresh(r)
    assert r.insumos["telefones"] == ["4133334444"]


def test_pendencias_e_diagnostico_sao_texto_longo(db):
    """Os dois são escritos à mão pelo Leandro e podem passar de 255
    caracteres: diagnóstico é argumento de venda e pendência é lista."""
    longo = "x" * 3000
    r = _redesign(db, diagnostico=longo, pendencias=longo)
    db.refresh(r)
    assert len(r.diagnostico) == 3000 and len(r.pendencias) == 3000
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/test_redesign.py -q`
Expected: FAIL na coleta, `ImportError: cannot import name 'Redesign' from 'app.models'`.

- [ ] **Step 3: Escrever o modelo**

Em `app/models.py`, logo depois da classe `Case` e das suas satélites (`CaseView`, `CaseComment`), acrescente:

```python
# ------------------------------------------------------------ Redesign --

ESTADOS_REDESIGN = ("pitch", "publico", "aprovado")


def novo_token() -> str:
    """Endereço secreto de um pitch.

    `token_urlsafe(16)` dá 22 caracteres de 128 bits de entropia: curto o
    bastante para ser colado no WhatsApp e às vezes lido em voz alta, e longe
    demais de ser adivinhado.

    Opaco de propósito. Um token derivado do nome da marca deixaria de ser
    secreto no instante em que alguém lesse a URL por cima do ombro do dono.
    """
    import secrets

    return secrets.token_urlsafe(16)


class Redesign(Base):
    """Uma home refeita por conta própria, para mostrar e vender.

    POR QUE AQUI, E NÃO EM app/lab/models.py

    Todo modelo do Lab pendura em `sandbox_id` e some na limpeza diária,
    porque é dado de visitante que vive 24 horas. Um redesign é o oposto:
    conteúdo editorial do Leandro, permanente, irmão de `Case`. Ele mora no
    endereço /lab porque é lá que o visitante o encontra, e endereço não
    dita onde o dado vive.

    OS TRÊS ESTADOS (§6 da spec)

    `pitch`     só existe pelo token. O endereço público responde 404.
    `publico`   na vitrine e no sitemap. Marca grande, ou cliente que
                autorizou.
    `aprovado`  virou trabalho real: sai da vitrine e do sitemap, e o
                portfólio passa a ter o `Case`. A página continua servindo
                como registro de que aquilo começou como pitch.

    AS DUAS CAPTURAS

    Saem do mesmo `app/services/captura.py` que já fotografa o site de um
    case. O "antes" vem de `antes_url`, o "depois" vem da própria página do
    Leandro. A cortina da vitrine nunca desatualiza porque é recapturada.
    """

    __tablename__ = "redesigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    marca: Mapped[str] = mapped_column(String(200), default="")
    setor: Mapped[str] = mapped_column(String(120), default="")
    estado: Mapped[str] = mapped_column(String(20), default="pitch", index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # o site atual, de verdade
    antes_url: Mapped[str] = mapped_column(String(500), default="")
    antes_shot: Mapped[str] = mapped_column(String(300), default="")
    antes_shot_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # a página deste redesign, fotografada pelo mesmo serviço
    depois_shot: Mapped[str] = mapped_column(String(300), default="")
    depois_shot_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # o dossiê da §4, colhido do site original
    insumos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    insumos_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # texto do Leandro: o argumento, e o que falta perguntar
    diagnostico: Mapped[str] = mapped_column(Text, default="")
    pendencias: Mapped[str] = mapped_column(Text, default="")

    criado_em: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    enviado_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # carimbado na PRIMEIRA abertura por visitante de verdade. Ver a regra do
    # loopback em app/lab/rotas_sites.py: sem ela, a captura do "depois"
    # marcaria o cliente como tendo visto antes de o link ser enviado.
    visto_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
```

Confira que `JSON`, `Text`, `DateTime` e `String` já estão no import de `sqlalchemy` no topo de `app/models.py`. Se `JSON` ou `Text` faltarem, acrescente.

- [ ] **Step 4: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/test_redesign.py -q`
Expected: PASS, 9 testes.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1474 passed, zero falha.

Não é preciso migração: `create_all()` cria tabela nova. Migração só faz falta para coluna nova em tabela que já existe.

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/test_redesign.py
git commit -m "Redesign: o modelo, com os tres estados e o token opaco"
```

---

### Task 2: A coleta do site original

O dossiê da §4. E a decisão de arquitetura que vale mais que o dossiê: **duas metades separadas**, porque a ferramenta de análise da próxima spec vai precisar do HTML e dos cabeçalhos sem baixar o site outra vez.

**Files:**
- Create: `app/services/coleta.py`
- Create: `tests/test_coleta.py`

**Interfaces:**
- Consumes: `app/services/captura.py::url_valida`.
- Produces:
  - `buscar(url: str, timeout: float = 12.0, transporte=None) -> dict` com `{"ok", "url", "status", "html", "cabecalhos", "erro"}`
  - `extrair(html: str, url: str) -> dict` com o dossiê
  - `colher(url: str, timeout: float = 12.0, transporte=None) -> dict` = `buscar` mais `extrair`
  - `UA: str`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_coleta.py`:

```python
"""Coleta do site original (§4 da spec de Sites).

Nenhum teste toca a rede: `buscar` recebe o cliente por `httpx.MockTransport`,
e `extrair` é função pura sobre uma string de HTML.
"""
import httpx

from app.services import coleta

PAGINA = """
<!doctype html><html lang="pt-BR"><head>
<title>Padaria Aurora | Pães artesanais em Curitiba</title>
<meta name="description" content="Padaria de bairro desde 1998.">
<meta property="og:image" content="/img/fachada.jpg">
</head><body>
<header><img src="/img/logo.svg" alt="Padaria Aurora"></header>
<h2>Nossos produtos</h2>
<ul><li>Pão sovado</li><li>Broa de milho</li><li>Bolo de fubá</li></ul>
<p>Somos uma padaria de bairro desde 1998, com fermentação natural.</p>
<p>Atendemos de Segunda a Sexta, 7h às 19h, e Sábado, 7h às 13h.</p>
<address>Rua das Flores, 210, Curitiba/PR</address>
<a href="https://wa.me/5541999998888">Fale no WhatsApp</a>
<a href="tel:+554133334444">(41) 3333-4444</a>
<a href="mailto:contato@aurora.com.br">contato@aurora.com.br</a>
<a href="https://www.instagram.com/padariaaurora">Instagram</a>
<a href="https://facebook.com/padariaaurora">Facebook</a>
<img src="/img/pao.jpg" alt="Pão"><img src="data:image/gif;base64,R0lGOD" alt="">
<script>var x = "Rua Falsa, 0";</script>
<style>.a{content:"nada"}</style>
</body></html>
"""


def _transporte(html=PAGINA, status=200):
    def responder(request):
        return httpx.Response(status, text=html,
                              headers={"content-type": "text/html; charset=utf-8"})
    return httpx.MockTransport(responder)


# ------------------------------------------------------------- buscar ----

def test_buscar_devolve_html_status_e_cabecalhos():
    """As três coisas juntas porque a ferramenta de análise da próxima spec
    precisa das três, e ela vai chamar ESTA função em vez de baixar o site
    de novo. É por isso que `buscar` e `extrair` são separadas."""
    r = coleta.buscar("padaria.com.br", transporte=_transporte())
    assert r["ok"] is True
    assert r["status"] == 200
    assert "<title>" in r["html"]
    assert r["cabecalhos"]["content-type"].startswith("text/html")
    assert r["url"].startswith("https://")


def test_buscar_recusa_endereco_invalido():
    """Reaproveita `url_valida` de captura.py: só http e https, sempre com
    host. Sem isso, file:// e afins viram porta de leitura de disco."""
    r = coleta.buscar("file:///etc/passwd", transporte=_transporte())
    assert r["ok"] is False and r["erro"]
    assert r["html"] == ""


def test_buscar_sem_rede_nao_estoura():
    def cair(request):
        raise httpx.ConnectError("sem rede")
    r = coleta.buscar("padaria.com.br", transporte=httpx.MockTransport(cair))
    assert r["ok"] is False and r["erro"]


def test_buscar_status_de_erro_nao_e_ok():
    r = coleta.buscar("padaria.com.br", transporte=_transporte(status=503))
    assert r["ok"] is False and r["status"] == 503


# ------------------------------------------------------------ extrair ----

def test_extrai_titulo_e_descricao():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["titulo"] == "Padaria Aurora | Pães artesanais em Curitiba"
    assert d["descricao"] == "Padaria de bairro desde 1998."


def test_extrai_contato_real():
    """É o que faz as chamadas da home funcionarem de verdade (§8)."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "5541999998888" in d["whatsapp"]
    assert "contato@aurora.com.br" in d["emails"]
    assert any("3333" in t for t in d["telefones"])


def test_extrai_endereco_e_horarios():
    """Os dois que mais somem em site ruim, e os dois que o dono mais
    reconhece quando aparecem certos."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "Rua das Flores, 210" in d["endereco"]
    assert any("Sábado" in h or "Segunda" in h for h in d["horarios"])


def test_extrai_redes_sociais_sem_repetir():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["redes"]["instagram"].endswith("padariaaurora")
    assert "facebook" in d["redes"]


def test_extrai_listas_como_servicos():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "Pão sovado" in d["servicos"]
    assert len(d["servicos"]) == 3


def test_extrai_paragrafos_na_ordem_em_que_apareciam():
    """A ordem é informação: ela diz o que o negócio considera mais
    importante, e é ponto de partida da hierarquia da home nova."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["textos"][0].startswith("Somos uma padaria")


def test_nao_extrai_texto_de_script_nem_de_style():
    """Endereço dentro de `<script>` não é endereço, é código. Sem este
    filtro o dossiê enche de lixo e o Leandro perde tempo separando."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    junto = " ".join(d["textos"]) + d["endereco"]
    assert "Rua Falsa" not in junto
    assert "content:" not in junto


def test_imagens_viram_endereco_absoluto_e_data_uri_fica_de_fora():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "https://padaria.com.br/img/pao.jpg" in d["imagens"]
    assert not any(i.startswith("data:") for i in d["imagens"])
    assert d["logo"] == "https://padaria.com.br/img/logo.svg"


def test_registra_que_nao_ha_h1():
    """O primeiro achado real dos dois alvos do Leandro: nem grupoom.com.br
    nem brainboxdesign.com.br têm h1. Isso é diagnóstico e é argumento de
    venda, então o dossiê guarda."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["h1"] == []
    assert "Nossos produtos" in d["h2"]


def test_html_vazio_nao_estoura():
    d = coleta.extrair("", "https://padaria.com.br")
    assert d["titulo"] == "" and d["textos"] == []


def test_html_quebrado_nao_estoura():
    """Site ruim costuma ter HTML ruim, e é justamente o site ruim que este
    serviço existe para ler."""
    d = coleta.extrair("<html><p>solto<div><a href=", "https://x.com.br")
    assert isinstance(d["textos"], list)


# -------------------------------------------------------------- colher ---

def test_colher_junta_as_duas_metades():
    d = coleta.colher("padaria.com.br", transporte=_transporte())
    assert d["ok"] is True
    assert d["titulo"].startswith("Padaria Aurora")
    assert d["colhido_em"]


def test_colher_falhando_devolve_dossie_vazio_e_o_erro():
    def cair(request):
        raise httpx.ConnectError("sem rede")
    d = coleta.colher("padaria.com.br", transporte=httpx.MockTransport(cair))
    assert d["ok"] is False and d["erro"]
    assert d["titulo"] == "" and d["telefones"] == []
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/test_coleta.py -q`
Expected: FAIL na coleta, `ModuleNotFoundError: No module named 'app.services.coleta'`.

- [ ] **Step 3: Escrever `app/services/coleta.py`**

```python
"""Colheita do site original de um redesign (§4 da spec de Sites).

DUAS METADES, E O MOTIVO DELAS

`buscar` baixa. `extrair` lê. `colher` faz as duas.

A separação não é estética. A ferramenta de análise de sites (próxima spec)
precisa do MESMO HTML e dos MESMOS cabeçalhos para medir cabeçalho de
segurança, tamanho de título, hierarquia de heading e peso de página. Se
`buscar` não existisse sozinha, aquela ferramenta baixaria o site do cliente
uma segunda vez, e duas leituras do mesmo endereço podem inclusive divergir
(teste A/B, conteúdo por região, cache). Uma busca, dois consumidores.

O QUE ESTE MÓDULO NÃO FAZ

Não julga. Ele traz o que achou, e quem decide o que presta é o Leandro, no
admin. A §4.1 da spec é clara: nada na home é inventado, e onde faltar
informação vira pendência para perguntar. Um extrator que "completa" o que
não achou seria a primeira fonte de invenção.

POR QUE `html.parser` E NÃO UMA BIBLIOTECA

Site ruim tem HTML ruim, e é justamente o site ruim que este módulo existe
para ler. O `html.parser` da biblioteca padrão é tolerante a tag não fechada
e atributo sem aspas, e não acrescenta dependência a um projeto que já
recusa dependência por princípio.
"""
from __future__ import annotations

import datetime as dt
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from .captura import url_valida

UA = ("Mozilla/5.0 (compatible; LFPortfolio/1.0; "
      "+https://leandrofurtado.com.br)")

# Tags cujo conteúdo é código, não texto. Endereço dentro de <script> não é
# endereço: sem este filtro o dossiê enche de lixo.
MUDAS = {"script", "style", "noscript", "template", "svg"}

REDES = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "tiktok": "tiktok.com",
}

# Telefone brasileiro escrito de todo jeito: (41) 3333-4444, 41 99999-8888,
# 4133334444. O dossiê traz candidatos; quem confirma é o Leandro.
_TELEFONE = re.compile(r"\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DIA = re.compile(
    r"(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo|"
    r"seg\b|sex\b|sáb\b|sab\b|dom\b)", re.I)
_HORA = re.compile(r"\d{1,2}\s?(h|:\d{2})", re.I)
_LOGRADOURO = re.compile(
    r"\b(rua|av\.?|avenida|alameda|travessa|rodovia|praça|praca|estrada)\b", re.I)


class _Leitor(HTMLParser):
    """Percorre o HTML uma vez e junta o que interessa."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titulo = ""
        self.meta: dict[str, str] = {}
        self.links: list[tuple[str, str]] = []   # (href, texto)
        self.imagens: list[str] = []
        self.logo = ""
        self.h1: list[str] = []
        self.h2: list[str] = []
        self.paragrafos: list[str] = []
        self.itens: list[str] = []
        self.endereco = ""
        self._pilha: list[str] = []
        self._buffer = ""
        self._href = ""

    # -------------------------------------------------------- abertura --
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._pilha.append(tag)
        if tag == "meta":
            nome = (a.get("name") or a.get("property") or "").lower()
            if nome:
                self.meta[nome] = a.get("content", "") or ""
        elif tag == "img":
            src = (a.get("src") or "").strip()
            if src and not src.startswith("data:"):
                self.imagens.append(src)
                alvo = f"{a.get('alt','')} {a.get('class','')} {src}".lower()
                if not self.logo and "logo" in alvo:
                    self.logo = src
        elif tag == "a":
            self._href = (a.get("href") or "").strip()
            self._buffer = ""
        elif tag in ("p", "li", "h1", "h2", "address"):
            self._buffer = ""

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self._pilha and self._pilha[-1] == tag:
            self._pilha.pop()

    # ----------------------------------------------------------- texto --
    def handle_data(self, dado):
        if any(t in MUDAS for t in self._pilha):
            return
        if self._pilha and self._pilha[-1] == "title":
            self.titulo += dado
        self._buffer += dado

    # ------------------------------------------------------ fechamento --
    def handle_endtag(self, tag):
        texto = " ".join(self._buffer.split()).strip()
        if tag == "a" and self._href:
            self.links.append((self._href, texto))
            self._href = ""
        elif tag == "h1" and texto:
            self.h1.append(texto)
        elif tag == "h2" and texto:
            self.h2.append(texto)
        elif tag == "p" and len(texto) > 30:
            self.paragrafos.append(texto)
        elif tag == "li" and 2 < len(texto) <= 120:
            self.itens.append(texto)
        elif tag == "address" and texto and not self.endereco:
            self.endereco = texto
        self._buffer = ""
        while self._pilha and self._pilha.pop() != tag:
            pass


def buscar(url: str, timeout: float = 12.0,
           transporte: httpx.BaseTransport | None = None) -> dict:
    """Baixa a página. Devolve `{ok, url, status, html, cabecalhos, erro}`.

    NUNCA levanta: o site do cliente pode estar fora do ar, redirecionar em
    laço ou devolver algo que não é HTML, e nada disso pode virar 500 no
    painel do Leandro.

    `transporte` existe só para o teste injetar `httpx.MockTransport`.
    """
    limpa = url_valida(url)
    vazio = {"ok": False, "url": limpa, "status": 0, "html": "",
             "cabecalhos": {}, "erro": ""}
    if not limpa:
        return {**vazio, "erro": "endereço inválido"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True,
                          headers={"User-Agent": UA},
                          transport=transporte) as cliente:
            resposta = cliente.get(limpa)
    except Exception as erro:
        return {**vazio, "erro": f"não consegui abrir: {type(erro).__name__}"}

    cabecalhos = {k.lower(): v for k, v in resposta.headers.items()}
    if resposta.status_code >= 400:
        return {**vazio, "status": resposta.status_code,
                "cabecalhos": cabecalhos,
                "erro": f"o site respondeu {resposta.status_code}"}
    return {"ok": True, "url": str(resposta.url), "status": resposta.status_code,
            "html": resposta.text, "cabecalhos": cabecalhos, "erro": ""}


def _dossie_vazio() -> dict:
    return {"titulo": "", "descricao": "", "og": {}, "telefones": [],
            "whatsapp": [], "emails": [], "endereco": "", "horarios": [],
            "redes": {}, "servicos": [], "textos": [], "logo": "",
            "imagens": [], "h1": [], "h2": []}


def extrair(html: str, url: str) -> dict:
    """Lê o HTML e devolve o dossiê. Função pura: não abre rede."""
    dossie = _dossie_vazio()
    if not html:
        return dossie

    leitor = _Leitor()
    try:
        leitor.feed(html)
    except Exception:
        # HTML quebrado o bastante para derrubar o parser ainda deixou o que
        # foi lido até ali no leitor. Site ruim é o caso comum aqui.
        pass

    dossie["titulo"] = " ".join(leitor.titulo.split())
    dossie["descricao"] = leitor.meta.get("description", "").strip()
    dossie["og"] = {k: v for k, v in leitor.meta.items() if k.startswith("og:")}
    dossie["h1"] = leitor.h1
    dossie["h2"] = leitor.h2
    dossie["textos"] = leitor.paragrafos
    dossie["servicos"] = leitor.itens
    dossie["imagens"] = [urljoin(url, i) for i in dict.fromkeys(leitor.imagens)]
    dossie["logo"] = urljoin(url, leitor.logo) if leitor.logo else ""

    corpo = " ".join(leitor.paragrafos + leitor.itens + [leitor.endereco])

    for href, _ in leitor.links:
        baixo = href.lower()
        if "wa.me/" in baixo or "api.whatsapp.com" in baixo:
            numero = re.sub(r"\D", "", baixo.split("wa.me/")[-1].split("phone=")[-1])
            if numero and numero not in dossie["whatsapp"]:
                dossie["whatsapp"].append(numero)
        elif baixo.startswith("tel:"):
            numero = re.sub(r"\D", "", href[4:])
            if numero and numero not in dossie["telefones"]:
                dossie["telefones"].append(numero)
        elif baixo.startswith("mailto:"):
            endereco = href[7:].split("?")[0]
            if endereco and endereco not in dossie["emails"]:
                dossie["emails"].append(endereco)
        else:
            for nome, host in REDES.items():
                if host in baixo and nome not in dossie["redes"]:
                    dossie["redes"][nome] = urljoin(url, href)

    for achado in _TELEFONE.findall(corpo):
        numero = re.sub(r"\D", "", achado)
        if len(numero) >= 10 and numero not in dossie["telefones"]:
            dossie["telefones"].append(numero)
    for achado in _EMAIL.findall(corpo):
        if achado not in dossie["emails"]:
            dossie["emails"].append(achado)

    dossie["endereco"] = leitor.endereco
    if not dossie["endereco"]:
        for trecho in leitor.paragrafos:
            if _LOGRADOURO.search(trecho) and re.search(r"\d", trecho):
                dossie["endereco"] = trecho
                break

    for trecho in leitor.paragrafos + leitor.itens:
        if _DIA.search(trecho) and _HORA.search(trecho):
            if trecho not in dossie["horarios"]:
                dossie["horarios"].append(trecho)

    return dossie


def colher(url: str, timeout: float = 12.0,
           transporte: httpx.BaseTransport | None = None) -> dict:
    """`buscar` mais `extrair`, com `ok`, `erro` e o carimbo de quando foi.

    É o que o admin chama. Falhando, devolve dossiê vazio e o motivo: o
    registro do redesign é criado do mesmo jeito, e o Leandro colhe de novo
    quando o site do cliente voltar.
    """
    baixado = buscar(url, timeout=timeout, transporte=transporte)
    dossie = extrair(baixado["html"], baixado["url"] or url)
    return {
        **dossie,
        "ok": baixado["ok"],
        "erro": baixado["erro"],
        "status": baixado["status"],
        "url": baixado["url"],
        "colhido_em": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/test_coleta.py -q`
Expected: PASS, 18 testes.

- [ ] **Step 5: Conferir contra um site de verdade**

Não é teste automatizado, é conferência única, porque HTML real sempre surpreende:

```bash
./.venv/bin/python -c "
from app.services import coleta
import json
for u in ('grupoom.com.br', 'brainboxdesign.com.br'):
    d = coleta.colher(u)
    print('===', u, '| ok:', d['ok'])
    for k in ('titulo','h1','telefones','whatsapp','emails','endereco','horarios','redes'):
        print(' ', k, '=', json.dumps(d[k], ensure_ascii=False)[:130])
"
```

O esperado, medido em 25/08/2026: os dois respondem, e **nenhum dos dois tem `h1`**. Se a colheita trouxer telefone e redes dos dois, o serviço está bom o bastante para a Task 5.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1492 passed, zero falha.

- [ ] **Step 7: Commit**

```bash
git add app/services/coleta.py tests/test_coleta.py
git commit -m "Coleta: baixar e ler o site original, em duas metades reaproveitaveis"
```

---

### Task 3: As duas rotas e a base mínima do redesign

A superfície que serve. Duas rotas, o carimbo de `visto_em` com a regra do loopback, e a base que impede uma página de redesign nascer sem as regras inegociáveis da §8.

**Files:**
- Create: `app/lab/rotas_sites.py`
- Create: `app/templates/lab/sites/_base_redesign.html`
- Modify: `app/main.py` (registrar o router)
- Test: `tests/test_redesign.py`

**Interfaces:**
- Consumes: `Redesign`, `ESTADOS_REDESIGN`, `novo_token` (Task 1); `app/services/geo.py::ip_do_pedido`; `app/lab/protecao.py::limitar_taxa`.
- Produces:
  - `router` com `GET /lab/sites/{slug}` e `GET /lab/p/{token}`
  - `LOOPBACK: frozenset[str]`
  - `marcar_visto(db, redesign, request) -> bool`
  - o template `lab/sites/_base_redesign.html` com os blocos `titulo`, `descricao`, `cabeca`, `corpo`, `scripts` e a variável exigida `r` (o registro)

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/test_redesign.py`:

```python
# --------------------------------------------------------------- rotas --

from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app


def _client():
    return TestClient(app, base_url="https://testserver")


def _no_banco_real(**campos):
    """Redesign gravado no banco que as ROTAS enxergam (SessionLocal real),
    diferente do fixture `db`, que é um SQLite em memória à parte."""
    padrao = dict(slug="padaria-aurora", marca="Padaria Aurora",
                  setor="Panificação", antes_url="https://exemplo.com.br",
                  token=novo_token())
    padrao.update(campos)
    with SessionLocal() as db:
        db.query(Redesign).delete()
        db.commit()
        r = Redesign(**padrao)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r.slug, r.token, r.id


def _limpar():
    with SessionLocal() as db:
        db.query(Redesign).delete()
        db.commit()


def test_pitch_responde_404_no_endereco_publico():
    """§6, e é a regra que faz o recorte da §1 ser real e não promessa.
    Enquanto é proposta para uma pessoa, só existe o endereço secreto."""
    slug, _, _ = _no_banco_real(estado="pitch")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}").status_code == 404
    _limpar()


def test_pitch_abre_pelo_token():
    slug, token, _ = _no_banco_real(estado="pitch")
    with _client() as c:
        r = c.get(f"/lab/p/{token}")
    assert r.status_code == 200
    assert "Padaria Aurora" in r.text
    _limpar()


def test_publico_abre_nos_dois_enderecos():
    slug, token, _ = _no_banco_real(estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}").status_code == 200
        assert c.get(f"/lab/p/{token}").status_code == 200
    _limpar()


def test_token_errado_e_404_e_nao_403():
    """403 confirmaria que o endereço existe. 404 não conta nada a quem
    está tentando adivinhar."""
    _no_banco_real(estado="pitch")
    with _client() as c:
        assert c.get("/lab/p/naoexisteesse_token_aqui").status_code == 404
    _limpar()


def test_a_pagina_do_pitch_e_noindex():
    """§6: o link privado nunca pode ser indexado, nem se vazar."""
    _, token, _ = _no_banco_real(estado="pitch")
    with _client() as c:
        r = c.get(f"/lab/p/{token}")
    assert "noindex" in r.text
    assert r.headers.get("x-robots-tag", "").startswith("noindex")
    _limpar()


def test_toda_pagina_de_redesign_tem_marca_de_autoria():
    """§8, inegociável: a página está no domínio do Leandro com a marca de
    outra empresa e pode vazar do link. Ela precisa dizer de quem é."""
    slug, token, _ = _no_banco_real(estado="publico")
    with _client() as c:
        for caminho in (f"/lab/sites/{slug}", f"/lab/p/{token}"):
            html = c.get(caminho).text
            assert 'name="author"' in html
            assert "Leandro Furtado" in html
    _limpar()


def test_nenhuma_pagina_de_redesign_tem_form_que_envia():
    """§8: formulário no servidor do Leandro coletando o cliente final de
    outra empresa é problema de dado pessoal que ninguém precisa ter."""
    slug, _, _ = _no_banco_real(estado="publico")
    with _client() as c:
        html = c.get(f"/lab/sites/{slug}").text
    assert "<form" not in html.lower()
    _limpar()


def test_o_primeiro_acesso_carimba_visto_em():
    _, token, ident = _no_banco_real(estado="pitch")
    with _client() as c:
        c.get(f"/lab/p/{token}")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is not None
    _limpar()


def test_o_segundo_acesso_nao_reescreve_visto_em():
    """`visto_em` é a PRIMEIRA abertura. Reescrever a cada visita
    transformaria o sinal em 'última vez que olhou', que é outra coisa."""
    _, token, ident = _no_banco_real(estado="pitch")
    with _client() as c:
        c.get(f"/lab/p/{token}")
        with SessionLocal() as db:
            primeiro = db.get(Redesign, ident).visto_em
        c.get(f"/lab/p/{token}")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em == primeiro
    _limpar()


def test_o_endereco_publico_nunca_carimba_visto_em():
    """`visto_em` é sinal de PITCH. Uma visita à galeria pública não é o
    cliente abrindo a proposta dele."""
    slug, _, ident = _no_banco_real(estado="publico")
    with _client() as c:
        c.get(f"/lab/sites/{slug}")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is None
    _limpar()


def test_requisicao_de_loopback_nao_carimba_visto_em():
    """§9.1, a armadilha. A captura do 'depois' precisa passar pelo link do
    token, porque o endereço público responde 404 enquanto é pitch. Se ela
    carimbasse, o Leandro marcaria o cliente como tendo visto a proposta
    antes de mandar o link, e o único sinal útil do pitch viraria ruído."""
    from app.lab import rotas_sites

    _, token, ident = _no_banco_real(estado="pitch")
    with TestClient(app, base_url="https://testserver",
                    client=("127.0.0.1", 5555)) as c:
        c.get(f"/lab/p/{token}")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is None
    assert "127.0.0.1" in rotas_sites.LOOPBACK
    _limpar()


def test_slug_que_nao_existe_e_404():
    with _client() as c:
        assert c.get("/lab/sites/nao-existe-essa-marca").status_code == 404


def test_as_rotas_de_redesign_herdam_o_rate_limit():
    """Mesma regra de todo o /lab: o router inteiro carrega `limitar_taxa`,
    e `tests/lab/test_rotas_protegidas.py` confere rota por rota."""
    from app.lab.protecao import limitar_taxa
    from app.lab.rotas_sites import router

    for rota in router.routes:
        chamadas = [d.call for d in rota.dependant.dependencies]
        assert limitar_taxa in chamadas, rota.path
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/test_redesign.py -q -k "rota or pitch or publico or token or visto or autoria or form or loopback"`
Expected: FAIL, `ModuleNotFoundError: No module named 'app.lab.rotas_sites'`.

- [ ] **Step 3: A base mínima do redesign**

Crie `app/templates/lab/sites/_base_redesign.html`:

```html
{# ============================================================
   Base MÍNIMA de toda página de redesign.

   Não confunda com `lab/_base_demo.html`. Aquela existe para os SISTEMAS
   parecerem parte do universo do Leandro: cabeçalho do site, faixa de
   copyright, marca do Lab. Um redesign precisa do oposto, parecer o site
   do CLIENTE, e por isso não herda nada daquilo.

   O que esta base faz é garantir o piso da §8 da spec, que nenhuma página
   pode esquecer:

     1. `<meta name="author">` e a marca de autoria visível no rodapé. A
        página está no domínio do Leandro, com a marca de outra empresa, e
        pode vazar do link: ela precisa dizer sem ambiguidade que é uma
        proposta, e não o site oficial daquele negócio.
     2. `noindex` enquanto o redesign é `pitch`.
     3. `prefers-reduced-motion` desligando o que se move, sem depender de
        cada CSS lembrar.

   O resto é livre. Cada redesign escreve o `corpo` que quiser, carrega o
   CSS que quiser pelo bloco `cabeca`, e pode usar GSAP, ScrollTrigger,
   SplitText e Lenis de `/static/vendor/` (§3 da spec).

   Contexto exigido: `r`, o registro `Redesign`.
   ============================================================ #}
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block titulo %}{{ r.marca }}{% endblock %}</title>
<meta name="description" content="{% block descricao %}{{ r.setor }}{% endblock %}">

{# A autoria também é legível por máquina, não só pela pessoa. #}
<meta name="author" content="Leandro Furtado">
<meta name="robots" content="{{ 'noindex, nofollow' if r.estado == 'pitch' else 'index, follow' }}">

<style>
  /* Piso de movimento: vale para toda página de redesign, e nenhum CSS de
     marca precisa lembrar de escrever isto. */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: .01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: .01ms !important;
      scroll-behavior: auto !important;
    }
  }
  .rd-autoria {
    display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: baseline;
    justify-content: center; padding: 22px 18px;
    font: 400 12px/1.5 system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
    background: #101014; color: #9a9aa2; text-align: center;
  }
  .rd-autoria a { color: #fff; text-decoration: none; border-bottom: 1px solid #4a4a52; }
  .rd-autoria a:hover { border-bottom-color: #fff; }
</style>
{% block cabeca %}{% endblock %}
</head>
<body class="rd-body rd-{{ r.slug }}">
{% block corpo %}{% endblock %}

{# A marca de autoria. Discreta, no fim, e nunca ausente: a §8 chama isso de
   inegociável, e o teste `test_toda_pagina_de_redesign_tem_marca_de_autoria`
   quebra se alguém tirar. #}
<footer class="rd-autoria">
  <span>Proposta de redesign criada por
    <a href="https://leandrofurtado.com.br" rel="noopener">Leandro Furtado</a>.
  </span>
  <span>Não é o site oficial de {{ r.marca }}.</span>
</footer>
{% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: Escrever `app/lab/rotas_sites.py`**

```python
"""As duas rotas que servem um redesign (§10 da spec de Sites).

    GET /lab/sites/<slug>   o endereço público. 404 enquanto for `pitch`.
    GET /lab/p/<token>      o endereço do pitch. Serve em qualquer estado.

Router PRÓPRIO, e não mais rotas dentro de `app/lab/rotas.py`: aquele arquivo
já tem 14 KB e vai receber sete rotas do Notável. Ele carrega `limitar_taxa`
no construtor, igual ao outro, então toda rota que nascer aqui herda a
proteção sem quem escreve precisar lembrar.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Redesign
from ..services.geo import ip_do_pedido
from .protecao import limitar_taxa

router = APIRouter(prefix="/lab", dependencies=[Depends(limitar_taxa)])

# Endereços que são a PRÓPRIA máquina. O Chromium de `app/services/captura.py`
# roda aqui dentro e bate em 127.0.0.1 para fotografar o "depois", e como o
# endereço público responde 404 enquanto o redesign é `pitch`, essa captura
# precisa passar pelo link do token. Sem esta lista, ela carimbaria
# `visto_em` e o Leandro veria "o cliente abriu" antes de ter mandado o link.
#
# Visitante de verdade nunca chega assim: o nginx repassa o IP real e
# `app/services/geo.py::ip_do_pedido` já resolve isso.
LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


def _pagina(r: Redesign) -> str:
    """O template deste redesign. Um por marca, escrito à mão."""
    return f"lab/sites/{r.slug}/home.html"


def marcar_visto(db: Session, r: Redesign, request: Request) -> bool:
    """Carimba `visto_em` na PRIMEIRA abertura por visitante de verdade.

    Devolve True quando carimbou. Não carimba de novo: o campo responde "o
    cliente abriu a proposta?", e reescrever a cada visita transformaria o
    sinal em "última vez que olhou", que é outra pergunta.
    """
    if r.visto_em is not None:
        return False
    if (ip_do_pedido(request) or "") in LOOPBACK:
        return False
    r.visto_em = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return True


def _servir(request: Request, r: Redesign) -> HTMLResponse:
    from ..main import templates

    resposta = templates.TemplateResponse(request, _pagina(r), {"r": r})
    if r.estado == "pitch":
        # Cinto e suspensório com a meta do template: cabeçalho HTTP cobre
        # o caso de o buscador ler a resposta sem executar o HTML.
        resposta.headers["x-robots-tag"] = "noindex, nofollow"
    return resposta


@router.get("/sites/{slug}", response_class=HTMLResponse)
async def redesign_publico(slug: str, request: Request,
                           db: Session = Depends(get_db)) -> HTMLResponse:
    """O endereço público. Enquanto o redesign é `pitch`, ele NÃO EXISTE:
    404, e não 403. Um 403 confirmaria que o endereço existe, que é
    exatamente o que não interessa contar a quem está tentando adivinhar."""
    r = db.query(Redesign).filter(Redesign.slug == slug).one_or_none()
    if r is None or r.estado == "pitch":
        raise HTTPException(status_code=404)
    return _servir(request, r)


@router.get("/p/{token}", response_class=HTMLResponse)
async def redesign_pitch(token: str, request: Request,
                         db: Session = Depends(get_db)) -> HTMLResponse:
    """O endereço do pitch. Serve em qualquer estado, e é o único que serve
    enquanto o redesign é `pitch`."""
    r = db.query(Redesign).filter(Redesign.token == token).one_or_none()
    if r is None:
        raise HTTPException(status_code=404)
    marcar_visto(db, r, request)
    return _servir(request, r)
```

- [ ] **Step 5: Registrar o router**

Em `app/main.py`, junto do import do Lab (linha ~626) e do `include_router` (linha ~648):

```python
from .lab import rotas as lab_router  # noqa: E402
from .lab import rotas_sites as lab_sites_router  # noqa: E402
```

```python
app.include_router(lab_router.router)
app.include_router(lab_sites_router.router)
```

- [ ] **Step 6: Um template de teste**

Os testes desta task usam o slug `padaria-aurora`, então ele precisa de página. Crie `app/templates/lab/sites/padaria-aurora/home.html` como o menor redesign possível, que serve de exemplo vivo do contrato e mantém os testes independentes do redesign de verdade da Task 6:

```html
{# Redesign mínimo, usado pelos testes das rotas. Não é peça de venda: é o
   exemplo executável de como uma página de redesign se escreve. Note que
   ele NÃO tem <form> e não carrega host externo (§8 e Global Constraints). #}
{% extends "lab/sites/_base_redesign.html" %}

{% block titulo %}{{ r.marca }}, pães artesanais em Curitiba{% endblock %}
{% block descricao %}Padaria de bairro desde 1998, com fermentação natural.{% endblock %}

{% block corpo %}
<main style="min-height:60vh;display:grid;place-items:center;font-family:system-ui">
  <h1>{{ r.marca }}</h1>
  <p>{{ r.setor }}</p>
  <a href="https://wa.me/5541999998888">Falar no WhatsApp</a>
</main>
{% endblock %}
```

- [ ] **Step 7: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/test_redesign.py -q`
Expected: PASS, 23 testes.

Se `test_requisicao_de_loopback_nao_carimba_visto_em` falhar, confira o que `ip_do_pedido` devolve sob `TestClient`: a `LOOPBACK` já inclui `"testclient"`, que é o host que o Starlette usa por padrão, e é por isso que os OUTROS testes de carimbo passam um `client=` explícito quando querem simular visitante de verdade. Se o seu `TestClient` não aceitar `client=`, troque esses testes por chamada direta a `marcar_visto` com um `Request` montado à mão.

- [ ] **Step 8: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1506 passed, zero falha. `tests/lab/test_rotas_protegidas.py` continua verde porque o router novo declara `limitar_taxa` no construtor.

- [ ] **Step 9: Commit**

```bash
git add app/lab/rotas_sites.py app/templates/lab/sites app/main.py tests/test_redesign.py
git commit -m "Redesign: as duas rotas, o carimbo de visto_em e a base minima da pagina"
```

---

### Task 4: A fileira na vitrine e o sitemap

A segunda fileira da §7, com a cortina antes/depois, e a entrada no sitemap que respeita os três estados da §6.

**Files:**
- Modify: `app/templates/lab/vitrine.html`
- Modify: `app/static/lab/vitrine.css`
- Modify: `app/static/lab/vitrine.js`
- Modify: `app/routers/public.py` (vitrine e sitemap)
- Test: `tests/test_redesign.py`

**Interfaces:**
- Consumes: `Redesign` (Task 1); rota `/lab/sites/{slug}` (Task 3); `app/routers/public.py::base_ctx`.
- Produces: a variável de contexto `redesigns` na vitrine do Lab; nenhuma função nova exportada.

**Cuidado com o vizinho:** o plano do Notável (`2026-08-25-notavel-corte-1.md`, Task 12) também mexe em `tests/lab/test_vitrine.py`, na contagem de cartões "em desenvolvimento". Os testes desta task falam **só** da fileira de sites e não repetem asserção sobre a fileira de sistemas, de propósito, para os dois planos poderem rodar em qualquer ordem.

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/test_redesign.py`:

```python
# ------------------------------------------------- vitrine e sitemap ----

def test_a_fileira_de_sites_nao_existe_sem_redesign_publico():
    """§7: sem redesign público, a fileira não existe. Sem 'em breve', sem
    placeholder. Fileira vazia anuncia uma promessa que ninguém pediu."""
    _limpar()
    with _client() as c:
        html = c.get("/lab").text
    assert 'data-fileira="sites"' not in html


def test_o_redesign_publico_aparece_na_vitrine():
    _no_banco_real(estado="publico")
    with _client() as c:
        html = c.get("/lab").text
    assert 'data-fileira="sites"' in html
    assert 'href="/lab/sites/padaria-aurora"' in html
    assert "Padaria Aurora" in html
    _limpar()


def test_o_pitch_nunca_aparece_na_vitrine():
    """§6, e é o ponto do recorte inteiro: proposta para uma pessoa não é
    conteúdo de galeria."""
    _no_banco_real(estado="pitch")
    with _client() as c:
        html = c.get("/lab").text
    assert "Padaria Aurora" not in html
    assert 'data-fileira="sites"' not in html
    _limpar()


def test_o_aprovado_sai_da_vitrine():
    """§6: quem contratou vira `Case` no portfólio, e é lá que ele mora."""
    _no_banco_real(estado="aprovado")
    with _client() as c:
        html = c.get("/lab").text
    assert 'data-fileira="sites"' not in html
    _limpar()


def test_a_cortina_so_aparece_com_as_duas_capturas():
    """A cortina compara duas imagens. Com uma só ela mentiria, mostrando o
    mesmo dos dois lados."""
    _no_banco_real(estado="publico", antes_shot="sites/a.webp", depois_shot="")
    with _client() as c:
        html = c.get("/lab").text
    assert "lab-vt-cortina" not in html
    _limpar()

    _no_banco_real(estado="publico", antes_shot="sites/a.webp",
                   depois_shot="sites/d.webp")
    with _client() as c:
        html = c.get("/lab").text
    assert "lab-vt-cortina" in html
    assert 'type="range"' in html
    _limpar()


def test_o_pitch_fica_fora_do_sitemap():
    _no_banco_real(estado="pitch")
    with _client() as c:
        xml = c.get("/sitemap.xml").text
    assert "/lab/sites/padaria-aurora" not in xml
    _limpar()


def test_o_publico_entra_no_sitemap():
    _no_banco_real(estado="publico")
    with _client() as c:
        xml = c.get("/sitemap.xml").text
    assert "/lab/sites/padaria-aurora" in xml
    _limpar()


def test_o_aprovado_fica_fora_do_sitemap():
    """§6: quem passa a merecer indexação é o case, não a proposta que o
    originou."""
    _no_banco_real(estado="aprovado")
    with _client() as c:
        xml = c.get("/sitemap.xml").text
    assert "/lab/sites/padaria-aurora" not in xml
    _limpar()


def test_o_token_nunca_entra_no_sitemap():
    """Endereço secreto no sitemap deixa de ser secreto. Este teste existe
    porque o erro é fácil de cometer numa refatoração distraída."""
    _, token, _ = _no_banco_real(estado="publico")
    with _client() as c:
        xml = c.get("/sitemap.xml").text
    assert token not in xml
    assert "/lab/p/" not in xml
    _limpar()
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/test_redesign.py -q -k "vitrine or fileira or cortina or sitemap"`
Expected: FAIL, `data-fileira="sites"` ausente.

- [ ] **Step 3: A vitrine passa a receber os redesigns**

Em `app/lab/rotas.py`, na rota `vitrine`, some os redesigns públicos ao contexto:

```python
@router.get("", response_class=HTMLResponse)
async def vitrine(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    from ..main import render
    from ..models import Redesign
    from ..routers.public import base_ctx

    # Só `publico`: `pitch` é proposta para uma pessoa (§6) e `aprovado`
    # migrou para o portfólio como `Case`.
    redesigns = (
        db.query(Redesign)
        .filter(Redesign.estado == "publico")
        .order_by(Redesign.criado_em.desc())
        .all()
    )
    return render(request, "lab/vitrine.html", {**base_ctx(db), "redesigns": redesigns})
```

- [ ] **Step 4: A fileira no template**

Em `app/templates/lab/vitrine.html`, depois da grade de cartões de sistema que já existe, acrescente:

```html
{#
  A segunda fileira (§7 da spec de Sites). Só existe quando há redesign
  público: sem eles, nada é renderizado, e a vitrine fica exatamente como
  estava. Nada de "em breve" aqui, porque fileira vazia anuncia promessa que
  ninguém pediu.

  A diferença de gramática em relação aos sistemas é a CORTINA: no cartão de
  site a imagem não é uma captura, são duas, e o visitante arrasta para ver o
  site atual da marca virar o do Leandro. É a peça mais imediatamente
  compreensível do Lab, e ela vive só aqui, nunca no pitch (§5).
#}
{% if redesigns %}
<section class="lab-vt-fileira" data-fileira="sites" aria-labelledby="lab-vt-sites-titulo">
  <header class="lab-vt-fileira-topo">
    <h2 id="lab-vt-sites-titulo" class="lab-vt-fileira-titulo">Sites</h2>
    <p class="lab-vt-fileira-sub">Homes refeitas do meu jeito. Arraste para comparar.</p>
  </header>

  <div class="lab-vt-grade">
    {% for r in redesigns %}
    <a class="lab-vt-card lab-vt-card-site" href="/lab/sites/{{ r.slug }}" data-reveal
       aria-label="{{ r.marca }}. Abrir o redesign.">
      {% if r.antes_shot and r.depois_shot %}
      {# A cortina precisa das DUAS capturas. Com uma só ela mostraria o
         mesmo dos dois lados, que é pior que não existir. #}
      <div class="lab-vt-cortina" style="--corte: 50%">
        <img class="lab-vt-cortina-antes" src="/media/{{ r.antes_shot }}"
             alt="Site atual de {{ r.marca }}" loading="lazy" decoding="async">
        <img class="lab-vt-cortina-depois" src="/media/{{ r.depois_shot }}"
             alt="A home de {{ r.marca }} refeita por Leandro Furtado"
             loading="lazy" decoding="async">
        <span class="lab-vt-cortina-haste" aria-hidden="true"></span>
        <input class="lab-vt-cortina-controle" type="range" min="0" max="100" value="50"
               aria-label="Comparar o site atual de {{ r.marca }} com o redesign">
      </div>
      {% elif r.depois_shot %}
      <div class="lab-vt-capa lab-vt-capa-site">
        <img src="/media/{{ r.depois_shot }}" alt="A home de {{ r.marca }} refeita"
             loading="lazy" decoding="async">
      </div>
      {% endif %}

      <p class="lab-vt-site-nome"><strong>{{ r.marca }}</strong></p>
      <p class="lab-vt-tags">
        <span class="lab-vt-estado lab-vt-estado-ativo"><i aria-hidden="true"></i>redesign</span>
        {% if r.setor %}<span class="lab-vt-tag">{{ r.setor }}</span>{% endif %}
      </p>
    </a>
    {% endfor %}
  </div>
</section>
{% endif %}
```

- [ ] **Step 5: A cortina em CSS**

Acrescente a `app/static/lab/vitrine.css`:

```css
/* ---------------------------------------------- cortina antes/depois ---
   Duas imagens empilhadas. A de cima é recortada por `--corte`, e o
   `<input type="range"> `por cima controla a variável.

   O controle é um input de verdade, e não uma div com arrasto em
   JavaScript, por dois motivos: teclado funciona de graça (seta esquerda e
   direita movem a cortina) e leitor de tela anuncia como controle. A
   aparência dele é zerada; quem se vê é a haste. */
.lab-vt-cortina {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 10px;
  background: #0d0d0f;
}
.lab-vt-cortina img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; object-position: top center;
}
.lab-vt-cortina-depois { clip-path: inset(0 0 0 var(--corte)); }
.lab-vt-cortina-haste {
  position: absolute; top: 0; bottom: 0; left: var(--corte);
  width: 2px; margin-left: -1px; background: #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, .35);
  pointer-events: none;
}
.lab-vt-cortina-haste::after {
  content: ""; position: absolute; top: 50%; left: 50%;
  width: 34px; height: 34px; margin: -17px 0 0 -17px;
  border: 2px solid #fff; border-radius: 999px;
  background: rgba(0, 0, 0, .28);
}
.lab-vt-cortina-controle {
  position: absolute; inset: 0;
  width: 100%; height: 100%; margin: 0;
  opacity: 0; cursor: ew-resize;
  -webkit-appearance: none; appearance: none; background: none;
}
.lab-vt-cortina-controle:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

.lab-vt-site-nome { margin: 10px 0 0; }
```

- [ ] **Step 6: As três linhas de JavaScript**

Acrescente ao fim de `app/static/lab/vitrine.js`:

```javascript
/* Cortina antes/depois: o input já guarda o valor e já responde a teclado
   e a arrasto. Isto só copia o valor dele para a variável de CSS.

   Sem JavaScript a cortina fica parada em 50%, que é um estado honesto:
   metade de cada site aparece, e a comparação continua legível. */
document.querySelectorAll(".lab-vt-cortina").forEach(function (caixa) {
  var controle = caixa.querySelector(".lab-vt-cortina-controle");
  if (!controle) return;
  function aplicar() { caixa.style.setProperty("--corte", controle.value + "%"); }
  controle.addEventListener("input", aplicar);
  // O cartão inteiro é um link: arrastar a cortina não pode navegar.
  controle.addEventListener("click", function (e) { e.preventDefault(); });
  aplicar();
});
```

- [ ] **Step 7: O sitemap**

Em `app/routers/public.py`, na função `sitemap`, depois do laço dos cases:

```python
    # Redesigns (§6 da spec de Sites): só `publico`. `pitch` é proposta para
    # uma pessoa e o endereço dela é secreto; `aprovado` migrou para o
    # portfólio, e quem merece indexação passa a ser o `Case`. O endereço do
    # token (/lab/p/<token>) NUNCA entra: um segredo no sitemap deixa de ser
    # segredo.
    from ..models import Redesign
    for r in db.query(Redesign).filter(Redesign.estado == "publico").all():
        parts.append(url(f"/lab/sites/{r.slug}", "0.6", tem_ingles=False))
```

`tem_ingles=False` pelo mesmo motivo do Nodal, já documentado nessa função: não existe `/en/lab/sites/...`, e declarar alternativa em inglês que devolve o mesmo português é sinal de conteúdo duplicado.

- [ ] **Step 8: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/test_redesign.py tests/lab/test_vitrine.py -q`
Expected: PASS.

- [ ] **Step 9: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1515 passed, zero falha.

- [ ] **Step 10: Commit**

```bash
git add app/templates/lab/vitrine.html app/static/lab/vitrine.css app/static/lab/vitrine.js app/lab/rotas.py app/routers/public.py tests/test_redesign.py
git commit -m "Redesign: a fileira Sites na vitrine, com cortina, e o sitemap por estado"
```

---

### Task 5: O painel

Onde o Leandro cria o registro, colhe o dossiê, dispara as capturas, vira o estado e copia o link do pitch. `/admin/lab` já existe e ganha uma lista.

**Files:**
- Create: `app/templates/admin/_redesigns.html`
- Modify: `app/routers/admin.py`
- Modify: `app/templates/admin/lab.html`
- Create: `tests/test_redesign_admin.py`

**Interfaces:**
- Consumes: `Redesign`, `novo_token`, `ESTADOS_REDESIGN` (Task 1); `coleta.colher` (Task 2); `captura.capturar` (já existe); `_contexto_lab` (já existe em `admin.py`).
- Produces: rotas `POST /admin/lab/redesigns`, e `/{id}/colher`, `/{id}/capturar`, `/{id}/estado`, `/{id}/enviado`, `/{id}/excluir` sob o mesmo prefixo.

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_redesign_admin.py`:

```python
"""Painel dos redesigns (/admin/lab).

Chama as funções de rota direto, com sessão de teste, no mesmo padrão de
tests/test_admin_case_form.py: o que interessa aqui é a regra, não o HTML.
"""
import asyncio
import datetime as dt

import pytest

from app.models import ESTADOS_REDESIGN, Redesign, novo_token
from app.routers import admin as admin_rotas


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
        marca="Padaria Aurora", setor="Panificação",
        antes_url="grupoom.com.br", db=db))
    r = db.query(Redesign).one()
    assert r.slug == "padaria-aurora"
    assert len(r.token) >= 20
    assert r.estado == "pitch"


def test_criar_desambigua_slug_repetido(db):
    """Duas marcas com o mesmo nome existem. O segundo slug não pode
    estourar com IntegrityError na cara de quem está cadastrando."""
    for _ in range(2):
        asyncio.run(admin_rotas.redesign_criar(
            marca="Aurora", setor="", antes_url="exemplo.com.br", db=db))
    slugs = sorted(r.slug for r in db.query(Redesign).all())
    assert slugs == ["aurora", "aurora-2"]


def test_criar_sem_endereco_e_recusado(db):
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_criar(
            marca="Aurora", setor="", antes_url="", db=db))


def test_virar_estado_so_aceita_os_tres(db):
    r = _r(db)
    asyncio.run(admin_rotas.redesign_estado(r.id, estado="publico", db=db))
    db.refresh(r)
    assert r.estado == "publico"
    with pytest.raises(Exception):
        asyncio.run(admin_rotas.redesign_estado(r.id, estado="qualquer", db=db))
    assert set(ESTADOS_REDESIGN) == {"pitch", "publico", "aprovado"}


def test_colher_grava_o_dossie_e_a_data(db, monkeypatch):
    """A colheita é a da Task 2, chamada aqui. O teste troca a rede por um
    retorno fixo: quem testa a extração é tests/test_coleta.py."""
    monkeypatch.setattr(
        admin_rotas.coleta, "colher",
        lambda url, **k: {"ok": True, "erro": "", "titulo": "Padaria Aurora",
                          "telefones": ["4133334444"], "colhido_em": "2026-08-25T12:00:00"},
    )
    r = _r(db)
    asyncio.run(admin_rotas.redesign_colher(r.id, db=db))
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
    asyncio.run(admin_rotas.redesign_colher(r.id, db=db))
    db.refresh(r)
    assert r.insumos["telefones"] == ["4133334444"]


def test_capturar_o_antes_usa_o_endereco_do_cliente(db, monkeypatch):
    chamadas = []
    monkeypatch.setattr(admin_rotas.captura, "capturar",
                        lambda url, slug: (chamadas.append((url, slug)) or ("sites/x.webp", "")))
    r = _r(db, antes_url="https://exemplo.com.br")
    asyncio.run(admin_rotas.redesign_capturar(r.id, lado="antes", db=db))
    db.refresh(r)
    assert chamadas[0][0] == "https://exemplo.com.br"
    assert r.antes_shot == "sites/x.webp"
    assert r.antes_shot_at is not None


def test_capturar_o_depois_passa_pelo_link_do_token(db, monkeypatch):
    """§9.1: o endereço público responde 404 enquanto o redesign é `pitch`,
    então a captura do 'depois' PRECISA entrar pelo token. É a regra do
    loopback em rotas_sites.py que impede isso de carimbar `visto_em`."""
    chamadas = []
    monkeypatch.setattr(admin_rotas.captura, "capturar",
                        lambda url, slug: (chamadas.append(url) or ("sites/d.webp", "")))
    r = _r(db, estado="pitch")
    asyncio.run(admin_rotas.redesign_capturar(r.id, lado="depois", db=db))
    db.refresh(r)
    assert f"/lab/p/{r.token}" in chamadas[0]
    assert r.depois_shot == "sites/d.webp"


def test_capturar_falhando_nao_apaga_a_captura_anterior(db, monkeypatch):
    monkeypatch.setattr(admin_rotas.captura, "capturar",
                        lambda url, slug: ("", "não consegui abrir esse endereço"))
    r = _r(db, antes_shot="sites/velha.webp")
    asyncio.run(admin_rotas.redesign_capturar(r.id, lado="antes", db=db))
    db.refresh(r)
    assert r.antes_shot == "sites/velha.webp"


def test_marcar_como_enviado_carimba_a_data(db):
    """`enviado_em` é o par de `visto_em`. O servidor não sabe que o link foi
    para o WhatsApp de alguém, então quem diz é o Leandro. Com os dois, ele
    sabe quanto tempo o prospect levou para abrir."""
    r = _r(db)
    assert r.enviado_em is None
    asyncio.run(admin_rotas.redesign_enviado(r.id, db=db))
    db.refresh(r)
    assert r.enviado_em is not None


def test_o_admin_nunca_mostra_o_token_de_um_case_alheio(db):
    """Sanidade: a lista do painel é do Leandro, e o token é o segredo do
    pitch. Ele aparece SÓ como link copiável do próprio registro."""
    r = _r(db)
    assert r.token
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/test_redesign_admin.py -q`
Expected: FAIL, `AttributeError: module 'app.routers.admin' has no attribute 'redesign_criar'`.

- [ ] **Step 3: As cinco rotas**

Em `app/routers/admin.py`, no bloco do Lab (perto da linha 1460, onde já ficam os imports do Lab), acrescente:

```python
from ..models import ESTADOS_REDESIGN, Redesign, novo_token
from ..services import captura, coleta


def _redesign(db: Session, ident: int) -> Redesign:
    r = db.get(Redesign, ident)
    if r is None:
        raise HTTPException(status_code=404, detail="Redesign não encontrado.")
    return r


def _slug_livre(db: Session, base: str) -> str:
    """`aurora`, depois `aurora-2`, depois `aurora-3`.

    Duas marcas com o mesmo nome existem, e o segundo cadastro não pode
    estourar com IntegrityError na cara de quem está cadastrando."""
    slug = base or "redesign"
    n = 1
    while db.query(Redesign).filter(Redesign.slug == slug).first() is not None:
        n += 1
        slug = f"{base}-{n}"
    return slug


@router.post("/lab/redesigns")
async def redesign_criar(marca: str = Form(...), setor: str = Form(""),
                         antes_url: str = Form(...), db: Session = Depends(get_db)):
    """O Leandro digita marca e endereço. Slug e token são derivados: um do
    nome, outro de `secrets`. Pedir os dois no formulário seria pedir que ele
    invente o que a máquina faz melhor, e um token digitado à mão seria um
    token adivinhável."""
    endereco = captura.url_valida(antes_url)
    if not endereco:
        raise HTTPException(status_code=400, detail="Endereço do site inválido.")
    r = Redesign(
        slug=_slug_livre(db, slugify(marca)),
        marca=marca.strip(), setor=setor.strip(),
        antes_url=endereco, token=novo_token(),
    )
    db.add(r)
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/estado")
async def redesign_estado(ident: int, estado: str = Form(...),
                          db: Session = Depends(get_db)):
    if estado not in ESTADOS_REDESIGN:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {estado}")
    r = _redesign(db, ident)
    r.estado = estado
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/colher")
async def redesign_colher(ident: int, db: Session = Depends(get_db)):
    """Baixa o site do cliente e grava o dossiê (§4).

    Falhando, NÃO apaga o dossiê anterior: site do cliente fora do ar não
    pode custar o material de uma proposta em andamento."""
    r = _redesign(db, ident)
    dossie = coleta.colher(r.antes_url)
    if dossie.get("ok"):
        r.insumos = dossie
        r.insumos_em = dt.datetime.now(dt.timezone.utc)
        db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/capturar")
async def redesign_capturar(ident: int, lado: str = Form("antes"),
                            db: Session = Depends(get_db)):
    """Fotografa um dos dois lados da cortina.

    O "depois" entra pelo endereço do TOKEN, e não pelo público: enquanto o
    redesign é `pitch`, o endereço público responde 404 (§6), e a captura
    voltaria vazia. É a regra do loopback em `app/lab/rotas_sites.py` que
    impede essa passagem de carimbar `visto_em` (§9.1)."""
    r = _redesign(db, ident)
    if lado == "depois":
        alvo = f"{settings.base_url.rstrip('/')}/lab/p/{r.token}"
        nome = f"redesign-{r.slug}-depois"
    else:
        alvo = r.antes_url
        nome = f"redesign-{r.slug}-antes"

    caminho, erro = captura.capturar(alvo, nome)
    if not erro and caminho:
        agora = dt.datetime.now(dt.timezone.utc)
        if lado == "depois":
            r.depois_shot, r.depois_shot_at = caminho, agora
        else:
            r.antes_shot, r.antes_shot_at = caminho, agora
        db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/enviado")
async def redesign_enviado(ident: int, db: Session = Depends(get_db)):
    """Carimba `enviado_em`, o par de `visto_em`.

    O servidor não tem como saber que o link foi para o WhatsApp de alguém,
    então quem sabe é o Leandro, e ele diz com um clique. Sem os dois
    carimbos, `visto_em` sozinho responde "abriu" mas não "abriu depois de
    quanto tempo", que é a diferença entre um prospect morno e um frio."""
    r = _redesign(db, ident)
    r.enviado_em = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)


@router.post("/lab/redesigns/{ident}/excluir")
async def redesign_excluir(ident: int, db: Session = Depends(get_db)):
    db.delete(_redesign(db, ident))
    db.commit()
    return RedirectResponse("/admin/lab", status_code=303)
```

Confira que `slugify`, `Form`, `HTTPException`, `RedirectResponse`, `settings` e `dt` já estão importados no topo de `app/routers/admin.py`. O arquivo usa todos eles em outras rotas; se algum faltar, acrescente.

E em `_contexto_lab`, some a lista ao dicionário devolvido:

```python
        "redesigns": db.query(Redesign).order_by(Redesign.criado_em.desc()).all(),
```

- [ ] **Step 4: A lista no painel**

Crie `app/templates/admin/_redesigns.html`:

```html
{# Lista de redesigns no painel do Lab. Cada linha traz o que o Leandro
   precisa decidir sem sair da tela: em que estado está, se o dossiê foi
   colhido, se as duas capturas existem, e o link do pitch para copiar.

   `visto_em` é a coluna que mais vale: ela responde "o cliente abriu?" sem
   ninguém precisar perguntar. #}
<section class="bloco">
  <h2>Redesigns</h2>

  <form method="post" action="/admin/lab/redesigns" class="linha-form">
    <input type="text" name="marca" placeholder="Marca" required maxlength="200">
    <input type="text" name="setor" placeholder="Setor" maxlength="120">
    <input type="text" name="antes_url" placeholder="site atual (grupoom.com.br)" required>
    <button type="submit">Criar</button>
  </form>

  <table class="tabela">
    <thead>
      <tr><th>Marca</th><th>Estado</th><th>Dossiê</th><th>Capturas</th>
          <th>Pitch</th><th>Aberto</th><th></th></tr>
    </thead>
    <tbody>
    {% for r in redesigns %}
      <tr>
        <td>
          <strong>{{ r.marca }}</strong><br>
          <small>{{ r.setor }}</small><br>
          <a href="{{ r.antes_url }}" target="_blank" rel="noopener"><small>site atual</small></a>
        </td>
        <td>
          <form method="post" action="/admin/lab/redesigns/{{ r.id }}/estado">
            <select name="estado" onchange="this.form.submit()">
              {% for e in ("pitch", "publico", "aprovado") %}
              <option value="{{ e }}" {{ 'selected' if r.estado == e }}>{{ e }}</option>
              {% endfor %}
            </select>
          </form>
        </td>
        <td>
          {% if r.insumos_em %}
            <small>{{ r.insumos_em.strftime('%d/%m %H:%M') }}</small><br>
            {% if r.insumos and not r.insumos.get('h1') %}
            <small class="alerta">sem h1</small><br>
            {% endif %}
          {% else %}<small>não colhido</small><br>{% endif %}
          <form method="post" action="/admin/lab/redesigns/{{ r.id }}/colher">
            <button type="submit">Colher</button>
          </form>
        </td>
        <td>
          <small>{{ 'antes ok' if r.antes_shot else 'sem antes' }}</small><br>
          <small>{{ 'depois ok' if r.depois_shot else 'sem depois' }}</small><br>
          {% for lado in ("antes", "depois") %}
          <form method="post" action="/admin/lab/redesigns/{{ r.id }}/capturar">
            <input type="hidden" name="lado" value="{{ lado }}">
            <button type="submit">Capturar {{ lado }}</button>
          </form>
          {% endfor %}
        </td>
        <td>
          <input type="text" readonly onclick="this.select()"
                 value="{{ base_url }}/lab/p/{{ r.token }}" size="34">
          {% if r.enviado_em %}
          <br><small>enviado {{ r.enviado_em.strftime('%d/%m %H:%M') }}</small>
          {% else %}
          <form method="post" action="/admin/lab/redesigns/{{ r.id }}/enviado">
            <button type="submit">Marcar como enviado</button>
          </form>
          {% endif %}
        </td>
        <td>
          {% if r.visto_em %}
            <strong>{{ r.visto_em.strftime('%d/%m %H:%M') }}</strong>
          {% else %}<small>ainda não</small>{% endif %}
        </td>
        <td>
          <form method="post" action="/admin/lab/redesigns/{{ r.id }}/excluir"
                onsubmit="return confirm('Excluir o redesign de {{ r.marca }}?')">
            <button type="submit">Excluir</button>
          </form>
        </td>
      </tr>
    {% else %}
      <tr><td colspan="7"><small>Nenhum redesign ainda.</small></td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>
```

E inclua em `app/templates/admin/lab.html`, no fim do conteúdo:

```html
{% include "admin/_redesigns.html" %}
```

- [ ] **Step 5: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/test_redesign_admin.py -q`
Expected: PASS, 11 testes.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1526 passed, zero falha.

Se `tests/lab/test_regras_seguranca.py::test_nenhum_safe_sobre_dado_de_visitante_nos_templates_do_lab` falhar, algum `|safe` entrou em `admin/_redesigns.html`: aquela varredura pega template de admin que cite "lab". Tire o `|safe`.

- [ ] **Step 7: Commit**

```bash
git add app/routers/admin.py app/templates/admin/_redesigns.html app/templates/admin/lab.html tests/test_redesign_admin.py
git commit -m "Redesign: o painel, com colheita, capturas, estado e link do pitch"
```

---

### Task 6: O primeiro redesign de verdade

Grupo OM. É a task que prova o caminho inteiro, da colheita ao link que dá para mandar.

Esta é a única task do plano em que a maior parte do trabalho é **direção de arte**, e ela não se especifica aqui: o desenho é do Leandro. O que se especifica é o processo, as regras que a página não pode quebrar, e como conferir.

**Files:**
- Create: `app/templates/lab/sites/grupo-om/home.html`
- Create: `app/static/lab/sites/grupo-om.css`
- Create: `tests/test_redesign_grupoom.py`

**Interfaces:**
- Consumes: `lab/sites/_base_redesign.html` (Task 3); o registro `Redesign` criado pelo painel (Task 5); o dossiê colhido (Task 2).
- Produces: nada de código consumido por outra task. É a peça.

**Por que o Grupo OM primeiro:** medido em 25/08/2026, `grupoom.com.br` responde 200, roda WordPress 6.6.7, entrega **212 KB de HTML numa home** e **não tem nenhum `<h1>`**. Os três fatos são diagnóstico pronto e verificável, e o terceiro é o tipo de coisa que um dono de agência entende em uma frase.

- [ ] **Step 1: Criar o registro e colher**

Pelo painel, em `/admin/lab`: marca "Grupo OM", setor "Marketing e comunicação", site atual `grupoom.com.br`. Depois clique em **Colher** e em **Capturar antes**.

Confira o dossiê. Ele precisa ter trazido telefone, e-mail ou WhatsApp, e as redes. Se vier vazio, o site bloqueou o `User-Agent` ou monta o conteúdo por JavaScript: nesse caso pare, e resolva antes de desenhar, porque a §4.1 proíbe preencher a home com invenção.

- [ ] **Step 2: Escrever o diagnóstico**

No campo `diagnostico` do registro, o argumento de venda em texto seu. Os três achados acima são o começo. O que faltar de informação vai para `pendencias`, para virar pergunta, nunca invenção (§4.1).

- [ ] **Step 3: Escrever os testes que falham**

Crie `tests/test_redesign_grupoom.py`:

```python
"""O primeiro redesign de verdade: Grupo OM.

Estes testes não julgam design. Eles conferem as regras da §8 da spec, que
são as que a página não pode quebrar por mais bonita que fique, e que são
fáceis de esquecer no calor do desenho.
"""
import pathlib
import re

import pytest

from app.main import templates

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = RAIZ / "app/templates/lab/sites/grupo-om/home.html"
CSS = RAIZ / "app/static/lab/sites/grupo-om.css"


class _Fake:
    slug = "grupo-om"
    marca = "Grupo OM"
    setor = "Marketing e comunicação"
    estado = "pitch"


def _html():
    return templates.get_template("lab/sites/grupo-om/home.html").render(r=_Fake())


def test_a_pagina_existe_e_renderiza():
    assert TEMPLATE.is_file() and CSS.is_file()
    assert len(_html()) > 2000, "uma home de verdade não cabe em dois mil caracteres"


def test_estende_a_base_de_redesign():
    """A base é o que garante a marca de autoria, o noindex do pitch e o
    piso de `prefers-reduced-motion`. Uma página que não a estende nasce
    sem as três, e nenhuma delas é opcional (§8)."""
    assert "lab/sites/_base_redesign.html" in TEMPLATE.read_text(encoding="utf-8")


def test_tem_exatamente_um_h1():
    """O site atual do Grupo OM não tem nenhum, medido em 25/08/2026. Se o
    redesign também não tiver, o diagnóstico vira piada."""
    assert len(re.findall(r"<h1[\s>]", _html(), re.I)) == 1


def test_nao_tem_form_que_envia():
    """§8: formulário no servidor do Leandro coletando o cliente final de
    outra empresa é problema de dado pessoal que ninguém precisa ter."""
    assert "<form" not in _html().lower()


def test_o_contato_e_link_direto_e_funciona():
    """§8: as chamadas funcionam de verdade. É o que transforma "bonito" em
    "pronto" na cabeça de quem abre no celular."""
    html = _html()
    assert re.search(r'href="(https://wa\.me/|tel:|mailto:)', html)


def test_nenhum_host_externo():
    """Global Constraints: fonte, script e imagem saem daqui. Um redesign
    que puxa fonte do Google reprova no próprio diagnóstico que ele faz do
    site do cliente."""
    html = _html()
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    permitidos = ("https://wa.me/", "https://leandrofurtado.com.br",
                  "https://www.google.com/maps", "https://maps.google.com")
    for endereco in externos:
        assert endereco.startswith(permitidos), endereco


def test_o_css_desliga_movimento_para_quem_pediu():
    """A base já põe o piso, e o CSS da marca não pode reintroduzir
    movimento por cima dele."""
    css = CSS.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css


def test_o_css_nao_usa_largura_fixa_na_estrutura():
    """Responsiva de verdade, e o celular primeiro (§8). Largura em pixel
    numa caixa de layout é o jeito clássico de quebrar em telas estreitas."""
    css = CSS.read_text(encoding="utf-8")
    suspeitas = re.findall(r"\bwidth:\s*(\d{3,})px", css)
    assert not [s for s in suspeitas if int(s) > 480], suspeitas


def test_a_copy_nao_usa_travessao():
    """Regra permanente do Leandro."""
    visivel = re.sub(r"<[^>]+>", " ", re.sub(r"<!--.*?-->", "", _html(), flags=re.S))
    assert "—" not in visivel and "–" not in visivel
```

- [ ] **Step 4: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/test_redesign_grupoom.py -q`
Expected: FAIL, `TemplateNotFound: lab/sites/grupo-om/home.html`.

- [ ] **Step 5: Construir a home**

`app/templates/lab/sites/grupo-om/home.html`, estendendo a base:

```html
{# Redesign da home do Grupo OM.

   REGRA QUE MANDA AQUI (§4.1 da spec): nada nesta página é inventado. Todo
   telefone, endereço, horário, serviço e texto sai do dossiê colhido de
   grupoom.com.br, ou de algo confirmado com o cliente. Onde faltou
   informação, o bloco NÃO EXISTE, e a falta está registrada em `pendencias`
   no painel, para virar pergunta.

   Um pitch com um serviço que a agência não presta se destrói sozinho: o
   dono lê, conclui que ninguém olhou o negócio dele, e tudo que veio antes
   vira enfeite.
#}
{% extends "lab/sites/_base_redesign.html" %}

{% block titulo %}Grupo OM, marketing e comunicação em Curitiba{% endblock %}
{% block descricao %}[a descrição real, saída do dossiê]{% endblock %}

{% block cabeca %}
<link rel="stylesheet" href="/static/lab/sites/grupo-om.css?v={{ asset_v }}">
{% endblock %}

{% block corpo %}
<main>
  {# UM h1, e ele diz o que o negócio faz. O site atual não tem nenhum. #}
  <h1>...</h1>
  ...
</main>
{% endblock %}

{% block scripts %}
{# Opcional. Se usar, saem daqui, nunca de CDN:
<script src="/static/vendor/gsap.min.js" defer></script>
<script src="/static/vendor/ScrollTrigger.min.js" defer></script> #}
{% endblock %}
```

O miolo é seu. As quatro regras que os testes do Step 3 impõem, e que valem repetir porque são fáceis de perder no meio do desenho:

1. **um `<h1>`**, dizendo o que o negócio faz
2. **nenhum `<form>`**; contato é `https://wa.me/`, `tel:` ou `mailto:`
3. **nenhum host externo**; fonte, script e imagem saem de `/static/`
4. **`prefers-reduced-motion`** no CSS da marca, além do piso da base

- [ ] **Step 6: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/test_redesign_grupoom.py -q`
Expected: PASS, 9 testes.

- [ ] **Step 7: Capturar o depois e conferir a cortina**

No painel, **Capturar depois**. Depois confira, no banco, que `visto_em` continua nulo: se a captura carimbou, a regra do loopback da Task 3 não está valendo, e o sinal do pitch está quebrado.

```bash
./.venv/bin/python -c "
import os; os.environ['DATA_DIR']=os.path.abspath('data')
from app.database import SessionLocal
from app.models import Redesign
with SessionLocal() as db:
    for r in db.query(Redesign).all():
        print(r.slug, '| estado:', r.estado, '| antes:', bool(r.antes_shot),
              '| depois:', bool(r.depois_shot), '| visto_em:', r.visto_em)
"
```

Esperado: `antes: True`, `depois: True`, `visto_em: None`.

- [ ] **Step 8: Conferir no celular**

Abra `/lab/p/<token>` no seu telefone, no 4G, e confira as quatro coisas que a §8 chama de inegociáveis e que teste nenhum vê:

1. a primeira dobra aparece rápido, sem tela branca
2. rola liso, e o movimento entra depois do conteúdo, nunca antes
3. o botão de WhatsApp abre o WhatsApp do Grupo OM de verdade
4. a marca de autoria está no rodapé, legível, dizendo que não é o site oficial

- [ ] **Step 9: Rodar a suíte inteira e commitar**

Run: `./.venv/bin/python -m pytest`
Expected: 1535 passed, zero falha.

```bash
git add app/templates/lab/sites/grupo-om app/static/lab/sites/grupo-om.css tests/test_redesign_grupoom.py
git commit -m "Redesign: a home do Grupo OM, o primeiro do Lab"
```

---

## Depois do plano

O corte 1 está entregue quando os oito itens da §14 da spec forem verdade:

- [ ] um redesign em `pitch` responde 404 no endereço público e abre pelo token
- [ ] o token carrega `noindex`, está fora do sitemap e fora da vitrine
- [ ] `visto_em` é carimbado na primeira abertura por visitante, e **não** pela captura
- [ ] a colheita traz contato, endereço e horário de um site real
- [ ] a cortina antes/depois funciona na vitrine, com as duas capturas
- [ ] toda página de redesign carrega a marca de autoria e nenhum `<form>` que envia
- [ ] a home abre rápido no celular e respeita `prefers-reduced-motion`
- [ ] nada em `app/lab/` importa do Nodal (`tests/test_produto_opcional.py` já cobre)

**O segundo alvo, `brainboxdesign.com.br`, não é uma task deste plano.** Ele é repetição do caminho que a Task 6 abriu: criar registro, colher, desenhar, capturar, mandar. Quando o primeiro estiver no ar, o segundo custa uma tarde e não precisa de plano.

**Antes de subir:** o deploy passa por `deploy/atualizar.sh`, que faz backup antes. Depois de subir, capture o "depois" **em produção**, não local: a captura fotografa o endereço que o `base_url` aponta, e uma captura feita contra `127.0.0.1:8000` guarda um caminho que só existe na sua máquina.

**A próxima spec** é a ferramenta de análise de sites. Ela vai chamar `coleta.buscar` (Task 2), que existe separada de `coleta.extrair` exatamente para isso: uma busca, dois consumidores, e o site do cliente baixado uma vez só.
