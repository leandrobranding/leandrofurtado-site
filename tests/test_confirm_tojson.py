"""Parte 3 do pacote unificado: sete confirm() com escape de JS errado.

Autoescape de HTML não escapa apóstrofo para contexto JS — um nome com aspas
simples ("O'Brien") quebrava o onsubmit com SyntaxError, e o botão morria em
silêncio (sem erro nenhum visível pra quem clicou). O conserto é `| tojson`,
que já devolve as aspas (dupla, formato JSON) — por isso o atributo vira
`onsubmit='...'` com aspas SIMPLES por fora: o `| tojson` escapa apóstrofo
como `\\u0027`, então nunca sobra um `'` cru para quebrar o atributo.
Referência do padrão certo: app/templates/nodal/admin/alunos.html (Tarefa 8).

Inventário fechado no brief (sete instâncias, os demais confirm() do painel
são texto fixo e não entram):
  nl_leads.html:88, nl_temas.html:41, case_form.html:375,
  cases_categorias.html:67, brands.html:79, brands.html:86,
  campaign_form.html:126 (numérico, entra por consistência).

Um teste paramétrico por template (não um por confirm()): cada caso
renderiza o template de verdade — pela rota real sempre que ela existe — com
um registro cujo campo interpolado tem apóstrofo, e prova que o literal
entre `confirm(` e `)` é JSON válido: é o próprio "é parseável" que o brief
aceita como prova, e cobre ao mesmo tempo o caso de escape (sem apóstrofo
cru) e o de troca de valor (o texto original precisa estar dentro do JSON).
"""
import asyncio
import json
import re

import pytest
from starlette.requests import Request

from app.config import settings
from app.models import Campaign, Category, NewsletterSub, Profile, Theme
from app.routers.admin import brands_page, case_edit_page
from app.routers.admin_cases import categorias
from app.routers.admin_nl import leads, temas


def _get_de(caminho: str) -> Request:
    """Mesmo padrão de tests/test_admin_case_form.py: Request à mão, sessão
    de admin já pronta, sem TestClient nem servidor."""
    scope = {
        "type": "http", "method": "GET", "path": caminho,
        "raw_path": caminho.encode(), "query_string": b"", "headers": [],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": {"csrf": "teste-csrf", "user": "leandro"},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _corpo(resposta) -> str:
    return resposta.body.decode()


def _json_do_confirm(corpo: str, pista_da_acao: str) -> str:
    """Isola o literal entre `confirm(` e `)` do <form> cuja action contém
    `pista_da_acao`. Falha alto (não em silêncio) se o padrão não bater —
    é o próprio sinal de que o template mudou de forma inesperada, ou que a
    reintrodução da aspa simples crua quebrou o atributo (a mutação do
    brief: reverter um `| tojson` faz o regex de aspas simples nem casar
    mais, e este assert é quem acusa)."""
    padrao = (r'<form[^>]*action="[^"]*' + re.escape(pista_da_acao)
              + r'[^"]*"[^>]*onsubmit=\'return confirm\((.*?)\)\'')
    m = re.search(padrao, corpo, re.S)
    assert m, f"onsubmit com confirm() em aspas simples não encontrado para ação {pista_da_acao!r}"
    return m.group(1)


# ---------- um construtor de HTML por template afetado ----------

def _html_nl_leads(db):
    sub = NewsletterSub(email="o'brien@exemplo.com", consent=True, ip="1.2.3.4", lang="pt")
    db.add(sub)
    db.commit()
    resp = asyncio.run(leads(_get_de("/admin/newsletter/leads"), db, aba="assinantes"))
    return _corpo(resp), sub.email


def _html_nl_temas(db):
    tema = Theme(name="Natal's", slug="natals")
    db.add(tema)
    db.commit()
    resp = asyncio.run(temas(_get_de("/admin/newsletter/temas"), db))
    return _corpo(resp), tema.name


def _html_cases_categorias(db):
    # categoria sem case nenhum: é o ramo (n.total falso) que mostra Excluir
    cat = Category(name_pt="Moda & Cia's", slug="moda-cias")
    db.add(cat)
    db.commit()
    resp = asyncio.run(categorias(_get_de("/admin/cases/categorias"), db))
    return _corpo(resp), cat.name_pt


def _html_case_form(db):
    from app.models import Case
    case = Case(slug="case-de-teste-confirm", title_pt="D'Angelo & Filhos")
    db.add(case)
    db.commit()
    resp = asyncio.run(case_edit_page(case.id, _get_de(f"/admin/cases/{case.id}"), db))
    return _corpo(resp), case.title_pt


def _html_brands_remover(db):
    """Segunda confirm() de brands.html: from_profile e sem case nenhum —
    o ramo que mostra "Remover {{ b.name }} da lista de marcas?"."""
    nome = "L'Atelier"
    db.add(Profile(id=1, data={"clients": [nome]}))
    db.commit()
    resp = asyncio.run(brands_page(_get_de("/admin/brands"), db))
    return _corpo(resp), nome


def _html_brands_logo(db):
    """Primeira confirm() de brands.html: só aparece com b.logo truthy, e
    isso exige um arquivo de verdade no disco (ver logo_e_escala em
    app/routers/public.py) — não dá para simular só com o registro no banco."""
    from app.services.images import slugify

    nome = "O'Brien & Co"
    slug = slugify(nome)
    db.add(Profile(id=1, data={"clients": [nome]}))
    db.commit()
    pasta = settings.upload_dir / "clients"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{slug}.svg"
    caminho.write_bytes(
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
        b'<rect width="100" height="60"/></svg>'
    )
    try:
        resp = asyncio.run(brands_page(_get_de("/admin/brands"), db))
        return _corpo(resp), nome
    finally:
        caminho.unlink(missing_ok=True)


CASOS = [
    ("nl_leads.html", _html_nl_leads, "/excluir"),
    ("nl_temas.html", _html_nl_temas, "/excluir"),
    ("cases_categorias.html", _html_cases_categorias, "/excluir"),
    ("case_form.html", _html_case_form, "/delete"),
    ("brands.html (remover marca)", _html_brands_remover, "/brands/remove"),
    ("brands.html (remover logo)", _html_brands_logo, "/brands/logo/delete"),
]


@pytest.mark.parametrize("construtor,pista_acao", [(c[1], c[2]) for c in CASOS],
                         ids=[c[0] for c in CASOS])
def test_confirm_com_apostrofo_vira_tojson_valido(db, construtor, pista_acao):
    corpo, valor_original = construtor(db)
    literal = _json_do_confirm(corpo, pista_acao)
    # tojson escapa apóstrofo como ' — não pode sobrar apóstrofo cru
    # dentro da string JS, que era exatamente o que quebrava o onsubmit
    # (SyntaxError silencioso, botão morto) antes do conserto.
    assert "'" not in literal, f"apóstrofo cru sobrou no literal JS: {literal!r}"
    mensagem = json.loads(literal)  # levanta ValueError se não for JSON válido
    assert valor_original in mensagem, "o valor do painel sumiu da mensagem do confirm()"


# ---------- campaign_form.html: caso numérico, à parte (sem apóstrofo) ----------

def test_confirm_da_campanha_usa_a_contagem_do_contexto_nao_um_numero_cravado():
    """campaign_form.html não tem rota que a sirva mais — nl_editor.html
    tomou o lugar dela — mas o coordenador conferiu a linha mesmo assim, e o
    arquivo continua no repositório respondendo se algo voltar a apontar
    para ele. Renderiza direto pelo Environment real (mesmos filtros do
    app.main: local, strftime_, tojson embutido), sem rota nem banco."""
    from app.main import templates

    class _QP:
        def get(self, *_a, **_k):
            return None

    class _Req:
        query_params = _QP()

    camp = Campaign(subject="Assunto de teste", audience="todos", status="rascunho")
    camp.id = 1
    tmpl = templates.env.get_template("admin/campaign_form.html")
    corpo = tmpl.render(
        request=_Req(), csrf="teste-csrf", camp=camp,
        counts={"todos": 37, "assinantes": 1, "leads": 1, "clientes": 1},
        audiences={"todos": "Todos os contatos"}, smtp_ok=True, preview=None,
    )
    literal = _json_do_confirm(corpo, "/enviar")
    mensagem = json.loads(literal)  # levanta ValueError se não for JSON válido
    assert "37" in mensagem, "o número de contatos não veio do contexto (counts[camp.audience])"
