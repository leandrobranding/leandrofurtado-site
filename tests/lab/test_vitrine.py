"""Testes da Task 3 do Plano 2: vitrine `/lab` (`app/templates/lab/vitrine.html`,
`app/static/lab/vitrine.css`).

Ao contrário das telas de demo (Task 1/2, `lab/_base_demo.html`), a vitrine
HERDA `base.html` do site — cabeçalho/rodapé/JSON-LD padrão, indexável — e
por isso os testes daqui sobem o app de verdade (`client`, de
`tests/lab/conftest.py`) em vez de renderizar o template isolado."""
import re


def test_vitrine_responde_200(client):
    r = client.get("/lab")
    assert r.status_code == 200


def test_vitrine_e_indexavel_sem_noindex(client):
    """Ao contrário das 3 telas internas de demo (noindex em
    `lab/_base_demo.html`), a vitrine herda o `robots` padrão do site
    ("index, follow ...") — ela é a única página do Lab que o Google deve
    ver (§10 da spec)."""
    r = client.get("/lab")
    assert 'name="robots"' in r.text
    assert "noindex" not in r.text


def test_vitrine_abre_so_o_que_esta_pronto(client):
    """No lançamento só o Admita abre. Notável e Caderneta aparecem no grid,
    com a marca e as tags, mas sem clique e dizendo que estão em
    desenvolvimento: prometer uma demo que não existe seria pior do que não
    mostrar o sistema."""
    r = client.get("/lab")
    assert 'href="/lab/admita"' in r.text
    assert 'href="/lab/notavel"' not in r.text
    assert 'href="/lab/caderneta"' not in r.text
    assert r.text.count("lab-vt-card-breve") == 2
    assert r.text.count("em desenvolvimento") >= 2


def test_vitrine_titulo_e_descricao_cruzam_termos_da_pesquisa_de_mercado(client):
    """§10 da spec: title/description cruzam cargo + domínio + técnica +
    geografia (seção 5 de .superpowers/sdd/2026-08-20-lab-demos/
    pesquisa-mercado.md) — smoke test com uma amostra de cada eixo, não a
    lista inteira de termos."""
    r = client.get("/lab")
    titulo = re.search(r"<title>(.*?)</title>", r.text, re.S).group(1)
    descricao = re.search(r'<meta name="description" content="([^"]*)"', r.text).group(1)
    # O DONO trocou o título por um humano ("Lab | Minha sala de
    # demonstrações"), e isso é decisão dele: title é o que a pessoa lê na
    # aba e no resultado da busca, e "Lab de Demos · IA aplicada em RH,
    # financeiro e escola" lia como etiqueta de SEO, não como convite.
    # Os termos da pesquisa continuam obrigatórios, agora na DESCRIPTION,
    # que é onde o buscador os encontra sem custo de leitura para ninguém.
    assert "Lab" in titulo
    assert "sala de demonstrações" in titulo
    assert "engenheiro de IA" in descricao
    assert "Curitiba" in descricao
    assert any(termo in descricao for termo in ("RH", "financeiro", "escola"))


def test_vitrine_tem_jsonld_com_collectionpage_e_itemlist(client):
    r = client.get("/lab")
    assert '"@type": "CollectionPage"' in r.text
    assert '"@type": "ItemList"' in r.text
    assert "/lab/admita" in r.text and "/lab/notavel" in r.text and "/lab/caderneta" in r.text


def test_vitrine_sem_travessao_no_html_renderizado(client):
    """Regra do Leandro (Global Constraints + Task 3): PROIBIDO travessão
    como pontuação na copy nova da vitrine. Mesmo padrão de
    tests/lab/test_base_demo.py: varre <title>, description e o texto
    visível do <body> (fora de tags)."""
    r = client.get("/lab")
    html = r.text
    titulo = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    descricao = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
    assert "—" not in titulo, f"travessão no <title>: {titulo!r}"
    assert "—" not in descricao, f"travessão na description: {descricao!r}"
    corpo = html.split("<body", 1)[1].split(">", 1)[1]
    texto_visivel = re.sub(r"<[^>]+>", " ", corpo)
    assert "—" not in texto_visivel, "travessão no texto visível da vitrine"


def test_vitrine_nao_usa_safe_sobre_dado_de_visitante():
    """A vitrine não tem dado de visitante nenhum (é conteúdo fixo), mas a
    regra da §9.2 é absoluta: nenhum `|safe` em template do Lab, ponto.
    `test_regras_seguranca.py::test_nenhum_safe_sobre_dado_de_visitante_nos_templates_do_lab`
    já cobre isto varrendo `app/templates/lab/*.html` inteiro; este teste
    fixa a garantia específica deste arquivo para não depender só da
    varredura genérica."""
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent.parent
    caminho = raiz / "app" / "templates" / "lab" / "vitrine.html"
    assert "|safe" not in caminho.read_text(encoding="utf-8")


def test_sitemap_contem_lab(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "<loc>" in r.text
    assert re.search(r"<loc>https://[^<]*/lab</loc>", r.text), r.text


def test_menu_do_site_linka_o_lab(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'href="/lab"' in r.text
    assert ">Lab<" in r.text


def test_vitrine_copyright_em_portugues_nunca_em_ingles(client):
    """Bug reportado pelo dono (20/08): o parcial compartilhado
    app/templates/_copyright.html decidia o idioma com `lang == 'pt'`; nas
    rotas do Lab que não passam por `lang` no contexto, isso caía sempre
    no inglês. O Lab é só português (decisão do dono, igual ao Nodal) —
    a faixa de copyright tem que sair em pt-BR sempre, nunca em inglês."""
    r = client.get("/lab")
    assert "Todos os direitos reservados" in r.text
    assert "All rights reserved" not in r.text
    assert "Purely built with" not in r.text


def test_vitrine_css_trava_tema_escuro_e_esconde_o_alternador():
    """Decisão do dono (21/08): "Faça a vitrine ficar SEMPRE no tema
    escuro, independente da preferência do site... o mesmo componente do
    alternador de tema, se aparecer na vitrine, não deixe a página num
    estado meio-claro quebrado." Solução: `body[data-page="lab"]`
    redeclara os tokens escuros (cascateiam por herança normal, vencendo
    o que `:root[data-theme="light"]` tiver setado no `<html>`) e esconde
    `.theme-fab` (clicar não teria efeito nenhum com o tema travado)."""
    import pathlib

    css = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "app" / "static" / "lab" / "vitrine.css"
    ).read_text(encoding="utf-8")
    assert 'body[data-page="lab"] {' in css
    assert "--bg: #0d0d0d;" in css
    assert "--ink: #f4f2ed;" in css
    assert 'body[data-page="lab"] .theme-fab { display: none; }' in css


def test_rota_vitrine_nao_cria_sandbox():
    """Diferente das rotas `/lab/admita`, `/lab/notavel` e `/lab/caderneta`
    (que chamam `obter_ou_criar_sandbox`), a rota raiz `/lab` é só a
    vitrine: não recebe visitante dentro de sandbox nenhum, só mostra os 3
    cards. Confere pela assinatura da função, sem precisar de HTTP."""
    import inspect

    from app.lab.rotas import vitrine as vitrine_fn

    fonte = inspect.getsource(vitrine_fn)
    assert "obter_ou_criar_sandbox" not in fonte
