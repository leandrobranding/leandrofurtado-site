"""Dois pedidos do pacote de 17/08 que vivem em app/templates/base.html:

- item 4: no menu fullscreen, ÁREA DO CLIENTE entra na mesma régua dos itens
  01–05 (continua <span>, não vira link — ver o comentário no próprio
  template). A régua tipográfica de verdade (altura de linha, gap, alinhamento
  do selo e do cadeado) foi medida no navegador, não aqui; este teste cobre
  só a estrutura: o item 06 continua dentro da mesma lista, na mesma posição,
  como <span>.
- item 5: "Galeria de Honra" entra no bloco de navegação do rodapé, nos dois
  idiomas.

Ver .superpowers/sdd/2026-08-17-nodal-4-experiencia-do-aluno/pacote-portfolio-brief.md.
"""
import asyncio
import re

from starlette.requests import Request

from app.routers.public import portfolio


def _get(caminho: str, lang: str = "pt") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": caminho,
        "raw_path": caminho.encode(), "query_string": b"", "headers": [],
        "state": {"clean_path": caminho, "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def _corpo(db, lang: str = "pt") -> str:
    resp = asyncio.run(portfolio(_get("/portfolio", lang), db))
    return resp.body.decode()


def test_rodape_copyright_pt_e_en_nao_regrediu_com_o_parcial_compartilhado(db):
    """Rodada de 20/08: a faixa de copyright virou o parcial compartilhado
    app/templates/_copyright.html (site + vitrine + as 3 demos, dono:
    "o mesmo rodapé copyright que tem no site inteiro"), decidindo o
    idioma com `lang != 'en'` (robusto a contexto sem `lang`, caso das
    rotas do Lab). Este teste prova que a extração não mudou nada no
    site: pt continua pt, en continua en."""
    corpo_pt = _corpo(db, "pt")
    assert "Todos os direitos reservados" in corpo_pt
    assert "All rights reserved" not in corpo_pt

    corpo_en = _corpo(db, "en")
    assert "All rights reserved" in corpo_en
    assert "Todos os direitos reservados" not in corpo_en


def test_rodape_tem_o_link_da_galeria_de_honra_em_pt(db):
    corpo = _corpo(db, "pt")
    assert 'href="/clientes"' in corpo
    assert "Galeria de Honra" in corpo


def test_rodape_tem_o_link_da_galeria_de_honra_em_en(db):
    corpo = _corpo(db, "en")
    assert 'href="/en/clientes"' in corpo
    assert "Hall of Honor" in corpo


def test_menu_itens_06_e_07_continuam_span_apos_a_entrada_do_lab(db):
    """Atualizado no Plano 2/Task 3: o Lab de Demos entrou como item 05 do
    menu fullscreen, um <a> real (as demos já estão de pé) — ver comentário
    em app/templates/base.html sobre `nth-child(5)` já esperar este quinto
    link. Nodal e Área do cliente, que antes eram 05/06, viraram 06/07 e
    continuam <span> (promessa, não link ainda)."""
    corpo = _corpo(db)
    nav = re.search(r'<nav class="mm-nav">(.*?)</nav>', corpo, re.S)
    assert nav, "nav.mm-nav não encontrado no menu fullscreen"
    # cada item começa por <a ...> ou pelo <span class="mm-breve" ...>,
    # seguido do número em <em>: a sequência tem que ser 01..07 em ordem,
    # sem nenhum item pulado ou fora do bloco.
    itens = re.findall(r'<(a|span class="mm-breve")[^>]*>\s*<em>(0[1-7])</em>', nav.group(1))
    assert [n for _, n in itens] == ["01", "02", "03", "04", "05", "06", "07"]
    assert itens[4][0] == "a", "item 05 (Lab) precisa ser link, as demos já estão no ar"
    assert itens[5][0] == 'span class="mm-breve"', (
        "item 06 (Nodal) precisa continuar <span>, não virar <a>")
    assert itens[6][0] == 'span class="mm-breve"', (
        "item 07 (Área do cliente) precisa continuar <span>, não virar <a>")


# ---------- pacote de correções mobile (18/08) ----------

def test_bloco_legal_do_rodape_tem_os_quatro_itens_na_mesma_fileira(db):
    """Defeito 2b do print do Leandro (23:57): a regra de CSS que dá padding
    e tamanho de fonte uniforme aos itens do rodapé (`.footer-col:last-child
    a, .footer-col:last-child .foot-breve` em main.css) só funciona se os
    quatro — Privacidade, Mapa do site, Galeria de Honra e o <span> "Área do
    cliente" — forem filhos diretos do MESMO .footer-col, nesta ordem. A
    medição do respiro em si é de navegador (ver relatório); isto aqui
    garante a estrutura de que a regra depende, pra um item sair do bloco
    sem que ninguém perceba o rodapé quebrar torto de novo."""
    corpo = _corpo(db)
    bloco = re.search(r'<h3[^>]*>Aspectos Legais</h3>(.*?)</div>', corpo, re.S)
    assert bloco, "coluna 'Aspectos Legais' não encontrada no rodapé"
    itens = re.findall(r'<(a|span class="foot-breve")', bloco.group(1))
    assert itens == ["a", "a", "a", 'span class="foot-breve"']


# ---------------------------------------------------------------- GitHub --
#
# Entrou em 24/08/2026, quando o Leandro publicou o perfil e o README em
# github.com/leandrobranding. Até então `social_github` existia no painel de
# configurações e não era lido por template nenhum: preencher o campo não
# fazia absolutamente nada aparecer. Estes testes existem para que ninguém
# volte a esse estado sem perceber.

def _com_github(db):
    # A sessão do projeto roda com autoflush desligado: sem o flush, a
    # consulta de `get_settings_map` não enxerga o que acabou de ser gravado.
    from app.routers.admin import set_setting
    set_setting(db, "social_github", "https://github.com/leandrobranding")
    db.flush()
    return _corpo(db)


def test_o_github_aparece_no_trilho_e_no_menu(db):
    """O trilho lateral e o menu em tela cheia leem a mesma lista
    (`rail_socials`), então uma alteração vale para os dois. Duas ocorrências
    do link é o esperado, não um bug."""
    corpo = _com_github(db)
    assert corpo.count('href="https://github.com/leandrobranding"') >= 2
    assert 'aria-label="github"' in corpo


def test_o_github_entra_no_sameAs_do_json_ld(db):
    """É o `sameAs` que diz ao Google que o Leandro Furtado do GitHub é o
    mesmo do site. Sem isso o perfil novo é só mais uma página solta, e o
    reposicionamento para engenharia não chega ao buscador."""
    corpo = _com_github(db)
    bloco = corpo.split('"sameAs"', 1)[1].split("]", 1)[0]
    assert "github.com/leandrobranding" in bloco


def test_o_github_aparece_na_coluna_social_do_rodape(db):
    corpo = _com_github(db)
    assert ">GitHub<" in corpo


def test_sem_o_campo_preenchido_o_site_nao_ganha_link_vazio(db):
    """O campo em branco tem que sumir por inteiro, não virar href="" nem
    um ícone que não leva a lugar nenhum."""
    from app.routers.admin import set_setting
    set_setting(db, "social_github", "")
    db.flush()
    corpo = _corpo(db)
    assert 'aria-label="github"' not in corpo
    assert ">GitHub<" not in corpo
