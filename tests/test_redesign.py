"""Redesign: modelo, rotas e presença nas superfícies públicas.

Spec: docs/superpowers/specs/2026-08-25-lab-sites-design.md
"""
import datetime as dt
import re

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


def test_o_token_e_noindex_mesmo_quando_o_redesign_e_publico():
    """O token é endereço secreto por desenho, e a indexabilidade dele não
    pode depender de um estado que volta atrás. Os dois endereços servem o
    MESMO conteúdo, e o canônico é /lab/sites/<slug>."""
    slug, token, _ = _no_banco_real(estado="publico")
    with _client() as c:
        r = c.get(f"/lab/p/{token}")
    assert r.headers.get("x-robots-tag", "").startswith("noindex")
    assert "noindex" in r.text
    _limpar()


def test_o_endereco_publico_continua_indexavel_quando_o_estado_permite():
    """A rede de segurança do teste acima: tornar o token sempre noindex não
    pode custar a indexação do endereço que DEVE aparecer na busca."""
    slug, _, _ = _no_banco_real(estado="publico")
    with _client() as c:
        r = c.get(f"/lab/sites/{slug}")
    assert "noindex" not in r.text
    assert "noindex" not in r.headers.get("x-robots-tag", "")
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


# ==========================================================================
# ITEM 36: A FILEIRA DE SITES DA VITRINE EXPÕE O REDESIGN DE VERDADE
# ==========================================================================

def _css_vitrine():
    """O CSS da vitrine sem comentário: é o que o navegador enxerga."""
    import pathlib
    import re as _re
    caminho = (pathlib.Path(__file__).resolve().parent.parent
               / "app/static/lab/vitrine.css")
    return _re.sub(r"/\*.*?\*/", "", caminho.read_text(encoding="utf-8"), flags=_re.S)


def test_a_fileira_de_sites_tem_o_css_que_ela_nunca_teve():
    """ITEM 36, e o diagnóstico que o produziu.

    A fileira existia no `vitrine.html` desde a §7 da spec de Sites e NÃO
    EXISTIA em `vitrine.css`: nenhuma das classes dela tinha uma regra.
    Medido no navegador antes de mexer, `.lab-vt-grade` computava
    `display: block` e `grid-template-columns: none`, e na tela isto era um
    `<h2>` na fonte do corpo com um nome em negrito solto embaixo, no meio de
    uma página cujos outros três cartões têm capa 16:9, wordmark e botão.

    Uma classe usada no template e ausente da folha é um defeito que nenhum
    teste pega e nenhum olho encontra até a fileira aparecer na tela de
    alguém. Este é o teste que pega."""
    css = _css_vitrine()
    for classe in (".lab-vt-fileira", ".lab-vt-fileira-topo",
                   ".lab-vt-fileira-titulo", ".lab-vt-fileira-sub",
                   ".lab-vt-grade", ".lab-vt-capa-site", ".lab-vt-capa-tipo"):
        assert classe + " {" in css or classe + "," in css, classe
    grade = re.search(r"\.lab-vt-grade \{([^}]*)\}", css).group(1)
    assert "display: grid" in grade, grade
    assert "grid-template-columns" in grade, grade


def test_o_cartao_de_site_reusa_a_moldura_dos_cartoes_de_sistema():
    """A moldura e a lógica dos cartões da fileira de sistemas são o contrato.
    O cartão de site se encaixa nelas em vez de trazer um segundo sistema
    parecido ao lado: mesma classe de cartão, mesma chamada de canto, mesma
    faixa de etiquetas."""
    _no_banco_real(estado="publico")
    with _client() as c:
        html = c.get("/lab").text
    cartao = re.search(r'<a class="lab-vt-card lab-vt-card-site".*?</a>', html, re.S)
    assert cartao, "o cartão de site precisa carregar a classe dos sistemas"
    bloco = cartao.group(0)
    assert 'class="lab-vt-ver"' in bloco, bloco[:200]
    assert 'class="lab-vt-tags"' in bloco, bloco[:200]
    assert 'href="/lab/sites/padaria-aurora"' in bloco
    _limpar()


def test_a_capa_do_cartao_de_site_existe_mesmo_sem_captura_nenhuma():
    """O ESTADO QUE FALTAVA, e é o que faz a fileira funcionar no primeiro
    dia.

    A cortina precisa das DUAS capturas, e uma captura é produto do serviço do
    painel: até alguém apertar o botão, o registro não tem nenhuma. Sem uma
    capa para esse caso, o cartão nasce sem imagem justamente no dia em que o
    Leandro quer mandar o link.

    A capa sem captura é TIPOGRÁFICA e genérica de propósito: a vitrine vale
    para qualquer redesign, e pendurar o vetor de um cliente aqui amarraria a
    fileira inteira a esse cliente."""
    _no_banco_real(estado="publico", antes_shot="", depois_shot="")
    with _client() as c:
        html = c.get("/lab").text
    assert "lab-vt-capa-tipo" in html
    assert "lab-vt-cortina" not in html
    # O nome está na capa, em tipo display, e por isso NÃO se repete embaixo.
    assert "lab-vt-site-nome" not in html
    _limpar()

    # Com as duas capturas, a cortina volta e a capa tipográfica sai de cena.
    _no_banco_real(estado="publico", antes_shot="sites/a.webp",
                   depois_shot="sites/d.webp")
    with _client() as c:
        html = c.get("/lab").text
    assert "lab-vt-cortina" in html
    assert "lab-vt-capa-tipo" not in html
    _limpar()


def test_a_legenda_so_promete_o_arrasto_quando_ha_o_que_arrastar():
    """A legenda dizia "Arraste para comparar" com nada para arrastar: a
    cortina só é renderizada com as duas capturas, e o registro nasce sem
    nenhuma. Prometer um gesto que a página não faz é o tipo de detalhe que o
    visitante testa em dois segundos."""
    _no_banco_real(estado="publico")
    with _client() as c:
        html = c.get("/lab").text
    assert "Arraste para comparar" not in html
    assert "no ar para clicar" in html
    _limpar()

    _no_banco_real(estado="publico", antes_shot="sites/a.webp",
                   depois_shot="sites/d.webp")
    with _client() as c:
        html = c.get("/lab").text
    assert "Arraste para comparar" in html
    _limpar()


def test_o_miolo_da_vitrine_cede_e_o_heroi_e_o_fecho_nunca():
    """A LEI DA TELA CHEIA, e o que a fileira de Sites fez com ela.

    Medido no navegador, com a fileira no ar: o conteúdo do `.lab-vt-shell`
    mede 846 px numa janela de 1440x900 (caixa de 843), 812 numa de 800
    (caixa de 743) e 755 numa de 700 (caixa de 643). Com `overflow: hidden` e
    `justify-content: center`, o excedente era cortado NAS DUAS PONTAS e sem
    barra: em 1440x800 a manchete do herói subia para trás do cabeçalho fixo e
    o botão de conversão saía cortado ao meio pela faixa de copyright.

    A Lei diz "nenhuma barra de rolagem", e é o que continua valendo: a barra
    é escondida. O que muda é que o excesso passa a ser ALCANÇÁVEL em vez de
    apagado. E não é leitura nova: é a que o arquivo já aplica no celular
    desde a rodada de direção de arte, com o comentário "o fecho é a última
    coisa a ceder espaço: quem rola é a lista"."""
    css = _css_vitrine()
    shell = re.search(r'body\[data-page="lab"\] \.lab-vt-shell \{(.*?)\}', css, re.S).group(1)
    assert "justify-content: safe center" in shell, shell
    assert "overflow-y: auto" in shell, shell
    assert "scrollbar-width: none" in shell, shell
    assert "overflow: hidden" not in shell, shell
    # O herói e o fecho não cedem altura em largura nenhuma.
    assert re.search(r'\.lab-vt-hero,\s*body\[data-page="lab"\] \.lab-vt-cta \{[^}]*flex-shrink: 0',
                     css), "o fecho é a última coisa a ceder espaço"
    # E acima do corte de celular nada é esmagado: medido, a fileira nascia
    # com `flex-shrink: 1` e media 4 px numa janela de 700 de altura.
    corte = next(b for b in re.findall(r"@media \(min-width: 901px\) \{(.*?)\n\}", css, re.S)
                 if "lab-vt-shell" in b)
    assert "flex: none" in corte, corte
