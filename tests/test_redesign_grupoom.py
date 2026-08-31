"""O redesign do Grupo OM: as CINCO páginas.

Estes testes não julgam design. Eles conferem as regras da §8 da spec, que são
as que a peça não pode quebrar por mais bonita que fique, e que são fáceis de
esquecer no calor do desenho.

O QUE O CICLO 3 ACRESCENTOU, e por quê. O diretor de arte reprovou a versão
anterior assim: "ruim de todas as formas, tá um site feito em IA praticamente,
textos e tipografias de IA, não tem hierarquias, esse laranja não tem nada a
ver". Nenhuma das regras antigas pegava isso, porque nenhuma delas olhava para
a IDENTIDADE do cliente. Agora existem quatro que olham:

  - a paleta é monocromática, e o laranja inventado não pode voltar
  - o arco-íris só existe como barra no topo e fio sob título, nunca como
    cor de texto, e NUNCA em volta da marca
  - a fonte é Montserrat, e é a ÚNICA
  - a régua tipográfica tem três degraus, e a distância entre eles é medida

E como agora são cinco páginas e não uma, quase tudo aqui é parametrizado: uma
regra que valia para a home e some na quarta interna é uma regra que não vale.
"""
import pathlib
import re

import pytest
from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app, templates
from app.lab import cases_grupo_om as om
from app.lab import conteudo_grupo_om as conteudo_om
from app.lab import selos_grupo_om as selos
from app.lab.textos_grupo_om import EN, tradutor
from app.models import Redesign, novo_token

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PASTA = RAIZ / "app/templates/lab/sites/grupo-om"
CSS = RAIZ / "app/static/lab/sites/grupo-om.css"
JS = RAIZ / "app/static/lab/sites/grupo-om.js"
ATIVOS = RAIZ / "app/static/lab/sites/grupo-om"

# As cinco do MENU, e a ordem é a dele.
PAGINAS = ("home", "sobre", "cases", "certificacoes", "contato",
           # 27/08: os serviços e a central de conteúdo entram no contrato —
           # o piso da §8 vale para elas como valeu para as cinco.
           "servicos", "conteudo")

# Os OITO ARTIGOS têm endereço próprio (stubs `artigo-<slug>.html`) e entram
# no mesmo contrato pelo mesmo motivo dos cases.
ARTIGOS_PAG = tuple("artigo-" + a["slug"] for a in conteudo_om.ARTIGOS)

# As cinco INTERNAS DE CASE (item 8 do Leandro, 26/08). Elas moram em `case/`,
# e não na raiz do redesign, e a rota que as serve é outra
# (`/lab/sites/<slug>/case/<case>`). A lista é fechada e é a mesma de
# `_dados_cases.html`: um case novo que apareça num lugar e não no outro
# reprova aqui.
CASES = tuple("case/" + c["slug"] for c in om.CASES)

# OS CASES QUE O CLIENTE PUBLICA E A PEÇA NÃO MOSTRA (item 34).
#
# Esta lista existe para que "sair" seja uma DECISÃO ESCRITA e não um
# esquecimento. O material colhido continua com os dezoito, e é contra ele que
# a suíte confere data, categoria e texto; o que muda é que a peça mostra
# dezoito menos estes, e o número de cartões da grade sai dessa conta em vez de
# estar digitado em quatro lugares.
#
# ninfa-comunicacao-integrada: a imagem de destaque que o WordPress do cliente
#   serve para este case é a do "Natal Iluminado". Os dois arquivos são
#   diferentes, e o segundo tem o nome do primeiro. Nós copiamos o que está
#   publicado, e o que está publicado está trocado. Mostrar ao dono da agência
#   a arte errada em cima do nome de um cliente dele é perder a reunião num
#   segundo. Decisão do Leandro em 27/08, e vale perguntar ao cliente.
CASES_REMOVIDOS = ("ninfa-comunicacao-integrada",)

# O case que as rotas usam como cobaia. Sai da lista, e não escrito à mão: um
# slug literal aqui vira um teste que reprova no dia em que o cliente publica
# outro case, por uma razão que não tem nada a ver com o que ele mede.
UM_CASE = om.CASES[0]["slug"]

# As TRÊS do item 7: privacidade, cookies e acessibilidade. Elas são páginas de
# verdade, com endereço próprio, e não texto miúdo de rodapé.
POLITICAS = ("politica-de-privacidade", "politica-de-cookies", "acessibilidade")

# O PISO DA §8 VALE PARA AS TREZE. Uma regra que valia para as cinco e some na
# nona é uma regra que não vale: foi assim que as internas nasceram
# parametrizadas na rodada passada, e é assim que os cases e as políticas
# entram nesta.
TODAS = PAGINAS + CASES + POLITICAS + ARTIGOS_PAG

# O prefixo que a ROTA entrega pronto ao template. O menu precisa funcionar
# nos dois endereços, e é este valor que decide qual dos dois.
BASE = "/lab/sites/grupo-om"

# A raiz absoluta que `_servir` monta a partir de `request.base_url`. Os botões
# de partilha do case precisam dela: uma rede social não tem o que fazer com um
# caminho sem host.
ABS = "https://testserver"


class _Fake:
    slug = "grupo-om"
    marca = "Grupo OM"
    setor = "Marketing e comunicação"
    estado = "pitch"


def _html(pagina="home", base=None, lang="pt", sufixo="", filtros=None):
    """Renderiza uma página com o MESMO contexto que a rota monta.

    O que este helper entrega precisa ser o que `rotas_sites.py::_servir`
    entrega, e não uma aproximação: no dia em que os dois divergirem, a suíte
    passa a testar uma página que ninguém serve. `T` sai do mesmo `tradutor`
    que a rota usa, pelo mesmo motivo.
    """
    raiz = base if base is not None else BASE
    prefixo = f"{raiz}/en" if lang == "en" else raiz
    # O MESMO `sufixo` que a rota monta para esta página ("" na home,
    # "/cases", "/case/ninfa"). Sem ele o endereço absoluto que os botões de
    # partilha recebem apontaria para a capa em todas as dezoito páginas de
    # case, e o teste que confere isso nunca veria a diferença.
    if not sufixo and pagina != "home":
        sufixo = "/" + pagina
    filtros = filtros or {"empresa": None, "categoria": None}
    return templates.get_template(f"lab/sites/grupo-om/{pagina}.html").render(
        r=_Fake(), base=prefixo, noindex=True,
        lang=lang,
        lang_html="en" if lang == "en" else "pt-BR",
        T=tradutor(lang),
        enderecos={"pt": raiz + sufixo, "en": f"{raiz}/en{sufixo}"},
        endereco_raiz=ABS,
        endereco_abs=ABS + prefixo + sufixo,
        cases=om.CASES,
        caso_do_servico=om.CASO_DO_SERVICO,
        servicos=conteudo_om.SERVICOS,
        artigos=conteudo_om.ARTIGOS,
        videos=conteudo_om.VIDEOS,
        artigo_por_slug=conteudo_om.POR_SLUG_ARTIGO,
        cases_filtrados=om.filtrar(**filtros),
        filtros=filtros,
        empresas=om.EMPRESAS,
        empresas_com_case=om.EMPRESAS_COM_CASE,
        categorias_com_case=om.CATEGORIAS_COM_CASE,
        nome_da_categoria=om.NOME_DA_CATEGORIA,
        assinante=om.assinante,
        por_slug=om.POR_SLUG,
        certificacoes=selos.CERTIFICACOES,
        premios=selos.PREMIOS)


def _css():
    """O CSS SEM comentário. Metade do arquivo é comentário, e todo teste que
    procura (ou proíbe) uma declaração precisa olhar só o que o navegador vê:
    senão uma frase explicando por que uma propriedade NÃO está ali reprova o
    teste que confere que ela não está ali."""
    return re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)


def _texto_visivel_lang(pagina, lang):
    """O texto que a pessoa lê, numa das duas línguas. Mesma limpeza de
    `_texto_visivel`, e ela não é reaproveitada por parâmetro só porque
    `_texto_visivel` é chamada em vinte lugares com um argumento posicional."""
    html = re.sub(r"<!--.*?-->", " ", _html(pagina, lang=lang), flags=re.S)
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _texto_visivel(pagina="home"):
    """O HTML sem comentário e sem marcação: é o que a pessoa lê."""
    html = re.sub(r"<!--.*?-->", " ", _html(pagina), flags=re.S)
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _texto_sem_prosa_do_cliente(html):
    """O texto visível MENOS a prosa que o próprio cliente escreveu.

    Serve ao item 32, e só a ele. A regra "ou é o nome, ou é a logo" fala de
    RÓTULO ao lado de desenho, não de uma frase publicada pelo Grupo OM que
    por acaso cita uma das seis empresas dentro dela. Reescrever a prosa do
    cliente para caber numa regra de diagramação seria falsificar o material.
    Fora, então: `.om-texto`, `.om-declaracao`, `<blockquote>` e a lista de
    nomes de cliente em texto, que é a alternativa acessível da fita.
    """
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    for classe in ("om-texto", "om-declaracao", "om-citacao", "om-lista-nomes",
                   "om-num-t", "om-cartao-resumo", "om-rodape-texto"):
        html = re.sub(rf'<(\w+)[^>]*class="[^"]*\b{classe}\b[^"]*".*?</\1>', " ",
                      html, flags=re.S)
    html = re.sub(r"<blockquote\b.*?</blockquote>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _imagens(pagina="home"):
    """(src, tag) de cada `<img>` da página, na ordem."""
    return [(re.search(r'src="([^"]+)"', tag).group(1), tag)
            for tag in re.findall(r"<img\b[^>]*>", _html(pagina))]


# ==========================================================================
# AS CINCO EXISTEM, E AS CINCO OBEDECEM AO MESMO PISO
# ==========================================================================

@pytest.mark.parametrize("pagina", TODAS)
def test_a_pagina_existe_e_renderiza(pagina):
    assert (PASTA / f"{pagina}.html").is_file()
    assert len(_html(pagina)) > 2000, "uma página de verdade não cabe em dois mil caracteres"


@pytest.mark.parametrize("pagina", TODAS)
def test_estende_a_base_de_redesign(pagina):
    """A base é o que garante a marca de autoria, o noindex do pitch e o piso
    de `prefers-reduced-motion`. Uma página que não a estende nasce sem as
    três, e nenhuma delas é opcional (§8).

    E o `extends` é LITERAL nas cinco, de propósito: uma corrente de heranças
    escondendo a base atrás de um segundo arquivo é exatamente o tipo de coisa
    que se perde quando alguém acrescenta a sexta página."""
    fonte = (PASTA / f"{pagina}.html").read_text(encoding="utf-8")
    assert '{% extends "lab/sites/_base_redesign.html" %}' in fonte


@pytest.mark.parametrize("pagina", TODAS)
def test_tem_exatamente_um_h1(pagina):
    """As CINCO páginas do site atual do Grupo OM têm zero `<h1>`, medido em
    26/08/2026. Se o redesign repetir isso em qualquer uma delas, o
    diagnóstico vira piada."""
    assert len(re.findall(r"<h1[\s>]", _html(pagina), re.I)) == 1


@pytest.mark.parametrize("pagina", TODAS)
def test_nao_tem_form_que_envia(pagina):
    """§8: formulário no servidor do Leandro coletando o cliente final de
    outra empresa é problema de dado pessoal que ninguém precisa ter."""
    assert "<form" not in _html(pagina).lower()


@pytest.mark.parametrize("pagina", TODAS)
def test_nenhum_recurso_carregado_vem_de_fora(pagina):
    """Global Constraints: fonte, script e imagem saem daqui. Um redesign que
    puxa fonte do Google reprova no próprio diagnóstico que ele faz do site do
    cliente.

    A regra é sobre RECURSO CARREGADO: tudo que a página baixa sozinha para se
    montar (`src`, e o `href` de `<link>`). Link de navegação é outra coisa, e
    está no teste seguinte."""
    html = _html(pagina)
    fora = re.findall(r'src="(https?://[^"]+)"', html)
    fora += re.findall(r'<link[^>]+href="(https?://[^"]+)"', html)
    assert not fora, fora


# OS ENDEREÇOS DE FORA, e a lista é fechada em três blocos.
#
# Cada entrada é o endereço EXATO, e nunca um prefixo frouxo. Um
# `startswith("https://www.google")` deixaria passar qualquer coisa hospedada
# num domínio do Google, e o dia em que alguém colasse um link errado o teste
# aplaudiria. O preço é ter que vir aqui para acrescentar um destino, e é o
# preço certo: acrescentar destino externo numa peça que promete não carregar
# nada de fora tem que doer um pouco.
# A CENTRAL DE CONTEÚDO (27/08) aponta para o que o cliente publica FORA da
# peça: os oito artigos completos no site atual dele, e os cinco vídeos no
# canal dele no YouTube. As listas saem dos DADOS, como tudo que conta.
ENDERECOS_DA_CENTRAL = tuple(
    f"https://grupoom.com.br/{a['slug']}/" for a in conteudo_om.ARTIGOS
) + tuple(
    f"https://www.youtube.com/watch?v={v['id']}" for v in conteudo_om.VIDEOS
)

ENDERECOS_DO_CLIENTE = ENDERECOS_DA_CENTRAL + (
    # A autoria da proposta, que é do Leandro e não do cliente.
    "https://leandrofurtado.com.br",
    "https://leandrofurtado.com.br/contato",
    # As redes que o próprio Grupo OM publica (item 26 acrescentou o YouTube
    # ao LinkedIn que já existia).
    "https://www.instagram.com/grupo_om/",
    "https://www.linkedin.com/company/grupo-om-marketing-comunicacao/mycompany/",
    "https://www.facebook.com/Grupo-OM-247205285365059/",
    "https://www.youtube.com/channel/UCDnq1psXM336KMZ1CFbPrzw",
    # O INSTITUTO J.D. RODRIGUES, e ele é o ÚNICO link da peça que aponta
    # para o site ATUAL do cliente. A razão está no menu: o Instituto tem
    # marca, propósito e missão próprios lá, e não faz parte do que está
    # sendo reproposto aqui. Mandar o dono da agência para um endereço que
    # ainda é dele é melhor do que fingir que a página existe neste redesign.
    "https://grupoom.com.br/instituto-jd-rodrigues/",
    # ITEM 17: os seis sites das seis empresas do grupo.
    "https://opusmultipla.com.br/",
    "https://dom-solucoes.com/",
    "https://sensoperformance.com.br/",
    "https://brainboxdesign.com.br/",
    "https://housecricket.com.br/",
    "https://tailormedia.com.br/",
    # ITEM 22: os dois mapas, exatamente como o cliente os publica. São
    # `google.com.br`, e não `google.com`: o teste antigo só conhecia o
    # segundo, e é por isso que ele precisou crescer.
    ("https://www.google.com.br/maps/place/Rua+Jaguaria%C3%ADva,+596+-+Alphaville,"
     "+Pinhais+-+PR,+83327-076/@-25.3927918,-49.1630936,17z/data=!3m1!4b1!4m5!3m4"
     "!1s0x94dceedfc690f5ed:0x7e9d3be9276af4e!8m2!3d-25.3927967!4d-49.1608995"),
    ("https://www.google.com.br/maps/place/Av.+Dr.+Cardoso+de+Melo,+1750+-+61+-"
     "+Itaim+Bibi,+S%C3%A3o+Paulo+-+SP,+04548-005/@-23.5958589,-46.6923768,17z"
     "/data=!3m1!4b1!4m5!3m4!1s0x94ce57380062d25b:0xa37d9ae92ccf783f!8m2"
     "!3d-23.5958589!4d-46.6898019"),
)

# OS ENDEREÇOS DE INTENÇÃO das oito redes que compartilham de verdade. Aqui a
# entrada é um prefixo, porque a query string muda de case para case, mas o
# prefixo vai até o `?`: ele fixa o host E o caminho, e é o caminho que
# distingue `x.com/intent/post` de qualquer outra coisa em `x.com`.
INTENCOES_DE_PARTILHA = (
    "https://x.com/intent/post?",
    "https://www.facebook.com/sharer/sharer.php?",
    "https://www.linkedin.com/sharing/share-offsite/?",
    "https://pinterest.com/pin/create/button/?",
    "https://www.threads.net/intent/post?",
    "https://wa.me/?text=",
    "https://t.me/share/url?",
)


@pytest.mark.parametrize("pagina", TODAS)
def test_todo_link_externo_e_endereco_do_proprio_cliente(pagina):
    """O contraponto do teste acima: um endereço do cliente noutro lugar da
    internet não é peso que esta página carrega. Mas a lista é FECHADA e
    EXATA, e é isso que faz um link colado por engano continuar reprovando
    depois de a lista ter dobrado de tamanho."""
    for endereco in re.findall(r'href="(https?://[^"]+)"', _html(pagina)):
        endereco = endereco.replace("&amp;", "&")
        ok = (endereco in ENDERECOS_DO_CLIENTE
              or endereco.startswith(INTENCOES_DE_PARTILHA))
        assert ok, (pagina, endereco)


@pytest.mark.parametrize("pagina", TODAS)
def test_nenhum_estatico_referenciado_esta_faltando(pagina):
    """Referenciar arquivo que não existe em /static/ quebra a página em
    silêncio: a fonte cai para a do sistema, a folha de estilo some e o
    cliente abre um documento sem desenho."""
    alvos = re.findall(r'(?:src|href)="(/static/[^"?]+)', _html(pagina))
    alvos += re.findall(r'url\("(/static/[^"?]+)"\)', CSS.read_text(encoding="utf-8"))
    assert alvos, "a página precisa carregar ao menos o CSS da marca"
    for caminho in alvos:
        assert (RAIZ / "app" / caminho.lstrip("/")).is_file(), caminho


@pytest.mark.parametrize("pagina", TODAS)
def test_toda_imagem_aponta_para_arquivo_que_existe_no_disco(pagina):
    """Um `src` errado não dá erro em lugar nenhum: dá um retângulo vazio no
    meio da proposta, e quem descobre é o dono da agência."""
    assert _imagens(pagina), (pagina, "toda página carrega ao menos o wordmark")
    for src, _ in _imagens(pagina):
        assert (RAIZ / "app" / src.split("?")[0].lstrip("/")).is_file(), src


@pytest.mark.parametrize("pagina", TODAS)
def test_toda_imagem_reserva_o_proprio_espaco(pagina):
    """`width` e `height` no HTML, em toda imagem. Sem eles, cada logo que
    chega empurra a página para baixo, e o dono lendo no celular vê o texto
    fugir do dedo."""
    for src, tag in _imagens(pagina):
        assert re.search(r'\bwidth="\d+"', tag), src
        assert re.search(r'\bheight="\d+"', tag), src


@pytest.mark.parametrize("pagina", TODAS)
def test_so_o_wordmark_da_primeira_dobra_carrega_com_prioridade(pagina):
    """Peso é o argumento desta proposta. A ÚNICA imagem que carrega cedo, em
    qualquer das cinco, é o wordmark do cliente no topo, que é a primeira
    coisa que ele vê; todo o resto é `lazy`."""
    ansiosas = []
    for src, tag in _imagens(pagina):
        if 'fetchpriority="high"' in tag:
            ansiosas.append(src)
            continue
        assert 'loading="lazy"' in tag, src
        assert 'decoding="async"' in tag, src
    assert ansiosas == ["/static/lab/sites/grupo-om/marca-grupo-om.svg"], ansiosas


# O diagnóstico medido em 26/08/2026: as cinco páginas do site atual entregam
# de 154 a 266 KB de HTML. A MAIS LEVE delas é o número que importa, porque é
# contra ela que a comparação é honesta.
MAIS_LEVE_DO_CLIENTE = 154_000
# 38% da página mais leve do cliente, 22% da mais pesada. A conta e o
# porquê estão em `test_o_html_e_drasticamente_menor_que_o_site_atual`.
#
# A DECISÃO de 27/08 que moveu o teto de 56 para 59 KB (o comentário do teste
# manda decidir, não empurrar): o Leandro pediu três etiquetas por case, o
# ícone de calendário na data e o texto legal com a razão social das seis
# S.A. no rodapé. É conteúdo, e conteúdo pedido: a página de cases foi de
# 56,0 para 57,9 KB com dezessete cartões mais ricos, e continua em um quinto
# da página mais pesada do cliente.
TETO_POR_PAGINA = 59_000


@pytest.mark.parametrize("pagina", TODAS)
def test_o_html_e_drasticamente_menor_que_o_site_atual(pagina):
    """Uma proposta que responde a 154 KB com 100 KB não tem argumento nenhum.

    O TETO já mudou duas vezes, e vale registrar as duas, porque a segunda é
    uma lição sobre como se escreve um teto.

    Era `45_000`, um número à mão que não dizia de onde vinha. Virou UM TERÇO
    da página mais leve do cliente (51,3 KB), que é a frase que o Leandro diz
    na reunião. E aí, no ciclo seguinte, o índice de cases ganhou dois menus
    de filtro e passou do teto por 1 KB.

    A LIÇÃO: "um terço" soava principiado e não era. O que importa é a ORDEM
    DE GRANDEZA da diferença, e ela não muda por causa de 1 KB. O teto agora é
    56 KB, dito como número e justificado como razão: 36% da página mais leve
    do cliente, 21% da mais pesada. Responder a 154 KB com 52 tem exatamente o
    mesmo argumento que responder com 48.

    E ele NÃO é folga para crescer sem pensar: 56 KB é pouco acima da página
    mais pesada de hoje. A próxima coisa que passar dele precisa de uma
    decisão, não de mais um empurrão no número."""
    tamanho = len(_html(pagina).encode("utf-8"))
    assert tamanho < TETO_POR_PAGINA, f"{pagina}: {tamanho} bytes"


@pytest.mark.parametrize("pagina", TODAS)
def test_a_copy_nao_usa_travessao(pagina):
    """Regra permanente do Leandro."""
    visivel = _texto_visivel(pagina)
    assert "—" not in visivel and "–" not in visivel


@pytest.mark.parametrize("pagina", TODAS)
def test_nenhum_glifo_com_apresentacao_emoji(pagina):
    """Regra permanente do Leandro. Um caractere que vira emoji colorido no
    Android destrói o desenho da página, e o jeito de não correr o risco é não
    ter nenhum caractere desses."""
    for ch in _texto_visivel(pagina):
        assert not (0x1F300 <= ord(ch) <= 0x1FAFF or 0x2600 <= ord(ch) <= 0x27BF), repr(ch)


@pytest.mark.parametrize("pagina", TODAS)
def test_nenhuma_medida_solta_no_html(pagina):
    """O defeito mais caro de duas versões atrás foi o ritmo vertical
    declarado numa variável e morto duas regras abaixo. Um `style=` no
    template é a mesma doença noutro arquivo: a medida que ninguém acha
    quando o ritmo da página precisa mudar. Toda distância vive no CSS, com
    nome."""
    assert 'style="' not in _html(pagina)


@pytest.mark.parametrize("pagina", TODAS)
def test_nada_de_contato_inventado(pagina):
    """§4.1, e é o teste que protege o pitch inteiro: o dossiê não trouxe
    e-mail nem WhatsApp do Grupo OM. Uma página que publicasse um dos dois
    estaria mandando o cliente do cliente para um endereço que não existe, e o
    dono descobriria isso antes do Leandro.

    ITEM 35: O WHATSAPP DEIXOU DE SER PENDÊNCIA em 27/08. O Leandro não
    recebeu número nenhum e decidiu ignorar o assunto, e por isso ele saiu da
    lista de perguntas do relatório. O que NÃO mudou é esta linha: a peça
    continua sem prometer WhatsApp em lugar nenhum, e agora por decisão em vez
    de por espera. Se um dia um número chegar, ele entra por aqui, e este teste
    é o lugar que registra que ele entrou de propósito."""
    html = _html(pagina)
    # O QUE MUDOU NESTA RODADA, e por que não é afrouxamento. A fileira de
    # partilha do case tem um `mailto:` e um `wa.me`, e NENHUM DOS DOIS tem
    # destinatário: `mailto:?subject=` abre o cliente de e-mail da pessoa que
    # clicou, e `wa.me/?text=` abre o WhatsApp DELA para escolher com quem
    # falar. A regra continua inteira e agora é literal: e-mail com endereço e
    # WhatsApp com número seguem proibidos, porque o dossiê não trouxe nenhum
    # dos dois para o Grupo OM, e montar um `wa.me` em cima de um telefone
    # fixo entrega ao dono da agência um botão que não abre nada.
    for suspeito in re.findall(r'"mailto:([^"?]*)', html):
        assert suspeito == "", suspeito
    for suspeito in re.findall(r'wa\.me/([^"?]*)', html):
        assert suspeito == "", suspeito
    for telefone in re.findall(r'href="tel:([^"]+)"', html):
        assert telefone in ("+554133621919", "+551130442215"), telefone


@pytest.mark.parametrize("pagina", TODAS)
def test_a_pilha_de_movimento_e_local_e_nao_bloqueia_a_pintura(pagina):
    """GSAP, ScrollTrigger, SplitText e Lenis: a pilha das referências, toda
    de `/static/vendor/`, e toda com `defer`. Um `<script>` sem `defer` num
    desses arquivos segura a primeira pintura da manchete."""
    html = _html(pagina)
    for arquivo in ("gsap.min.js", "ScrollTrigger.min.js", "SplitText.min.js", "lenis.min.js"):
        tag = re.search(r"<script[^>]*" + re.escape(arquivo) + r"[^>]*>", html)
        assert tag, arquivo
        assert "defer" in tag.group(0), arquivo
        assert '"/static/vendor/' in tag.group(0), arquivo


@pytest.mark.parametrize("pagina", TODAS)
def test_a_pagina_nao_fica_em_branco_se_o_gsap_nao_chegar(pagina):
    """A classe `om-js` esconde tudo que é revelado por rolagem, e ela é posta
    no `<head>` ANTES de o GSAP existir. Se o arquivo não chegar, a proposta
    abre em branco. Tem que haver um relógio que derrube a classe sozinho, e o
    JS tem que cancelá-lo ao assumir."""
    cabeca = _html(pagina)
    assert "om-js" in cabeca
    assert "setTimeout" in cabeca and "classList.remove" in cabeca
    js = JS.read_text(encoding="utf-8")
    assert "clearTimeout" in js and "__omRelogio" in js
    assert 'raiz.classList.remove("om-js")' in js, "sem GSAP, a classe precisa cair na hora"


# ==========================================================================
# O MENU: a entrega são CINCO páginas, e elas precisam se alcançar
# ==========================================================================

@pytest.mark.parametrize("pagina", TODAS)
@pytest.mark.parametrize("base", [BASE, "/lab/p/abc123"])
def test_o_menu_liga_as_cinco_nos_dois_enderecos(pagina, base):
    """A regra que faz "cinco páginas" ser uma entrega e não cinco arquivos.

    E ela vale nos DOIS endereços: quem abriu pelo link do pitch precisa
    continuar dentro dele, porque o endereço público responde 404 enquanto o
    redesign é `pitch`. Um menu que apontasse para lá levaria o cliente a uma
    página de erro no meio da proposta. O prefixo vem pelo contexto (`base`),
    montado na rota; o template só interpola."""
    html = _html(pagina, base=base)
    for destino in ("", "/sobre", "/cases", "/certificacoes", "/contato"):
        assert f'href="{base}{destino}"' in html, (pagina, destino)
    # E o endereço do OUTRO prefixo não pode ter vazado para dentro do HTML.
    outro = "/lab/p/abc123" if base == BASE else BASE
    assert f'href="{outro}' not in html, (pagina, outro)


@pytest.mark.parametrize("pagina", TODAS)
def test_a_pagina_atual_se_marca_no_menu(pagina):
    """`aria-current="page"` uma vez, e só uma: sem ele o menu de cinco itens
    não diz em qual delas a pessoa está.

    A INTERNA DE UM CASE marca "Cases", e não um sexto item: ela não é um
    destino do menu, ela é a página de cases mais fundo. Já as três páginas de
    política não marcam nada, e é certo que não marquem: elas moram no rodapé,
    e acender um item do topo que a pessoa não usou para chegar ali seria
    mentir sobre onde ela está.

    O menu de tela cheia (item 5) NÃO repete a marcação, de propósito: dois
    `aria-current="page"` no mesmo documento fazem o leitor de tela anunciar
    duas páginas atuais, que é pior do que nenhuma."""
    esperado = 0 if pagina in POLITICAS else 1
    assert _html(pagina).count('aria-current="page"') == esperado


# ==========================================================================
# A IDENTIDADE. É o que reprovou a versão anterior, e é o que estes travam.
# ==========================================================================

def test_o_laranja_inventado_nao_volta():
    """A frase foi literal: "esse laranja não tem nada a ver". `#e4572e` era
    invenção minha, não do cliente: a identidade do Grupo OM é monocromática.
    Este teste existe para o acento não voltar por distração."""
    css = _css().lower()
    for html in (_html(p) for p in TODAS):
        assert "e4572e" not in html.lower()
    assert "e4572e" not in css
    # E nenhum laranja "parecido" no lugar dele: a peça é grafite e papel.
    assert "--sinal" not in css, "a variável de acento único não existe mais"


def test_a_fonte_e_montserrat_e_e_a_unica():
    """Pedido explícito do Leandro: "Montserrat e suas variações". Um só
    `@font-face`, apontando para o arquivo que já existe no repositório, e
    nenhuma segunda família declarada: duas famílias é como a versão anterior
    virou "tipografia de IA"."""
    css = _css()
    faces = re.findall(r"@font-face\s*\{[^}]*\}", css)
    assert len(faces) == 1, faces
    assert 'font-family: "Montserrat"' in faces[0]
    assert 'url("/static/fonts/Montserrat.woff2")' in faces[0]
    # Variável de 100 a 900: as "variações" do pedido são o eixo de peso, e é
    # ele que entrega kicker 600, corpo 400, manchete 800 e apoio 200 num
    # arquivo só.
    assert "font-weight: 100 900" in faces[0]
    assert (RAIZ / "app/static/fonts/Montserrat.woff2").is_file()
    # Nenhuma fonte do Lab antigo sobrou no arquivo.
    for antiga in ("IBM Plex", "Lora", "Space Grotesk", "fonts.googleapis"):
        assert antiga not in css, antiga


def test_o_arco_iris_tem_as_seis_paradas_da_identidade():
    """A única cor da peça, e ela é um gradiente de seis paradas lido das
    peças que o cliente mandou. Se um dia virar quatro, deixou de ser o
    arco-íris dele."""
    css = _css().lower()
    for parada in ("#e52a18", "#f0a400", "#f2e200", "#3fa535", "#0e9aa7", "#6b2e8f"):
        assert parada in css, parada


def test_o_arco_iris_nunca_e_cor_de_texto():
    """A regra que o documento de identidade escreve em caixa alta: o
    gradiente aparece como BARRA no topo, ANEL em volta do wordmark e FIO sob
    um título. Nunca como cor de letra.

    A checagem é literal e é a que importa: nenhuma declaração `color:` deste
    arquivo pode receber uma das seis paradas, nem a variável que as guarda."""
    css = _css().lower()
    for valor in re.findall(r"[^-]\bcolor:\s*([^;}]+)", css):
        assert "--arco" not in valor, valor
        for parada in ("#e52a18", "#f0a400", "#f2e200", "#3fa535", "#0e9aa7", "#6b2e8f"):
            assert parada not in valor, valor


def test_o_arco_iris_esta_nos_dois_lugares_e_em_toda_pagina():
    """Barra no topo e fio sob título, nas cinco. Sem a barra, a peça inteira
    sai monocromática e a única cor da identidade some dela."""
    for pagina in TODAS:
        html = _html(pagina)
        assert 'class="om-arco"' in html, pagina
        assert "om-fio" in html, pagina


def test_o_arco_iris_nunca_circunda_a_marca():
    """Correção do Leandro em 26/08, verbatim: "A marca não tem anel. Ela só
    tem o escrito, exatamente como a logo que está no meu site. O anel com
    gradiente e o gradiente em si são só grafismos, insumos gráficos."

    Eu tinha montado um `.om-anel` de gradiente em volta do wordmark no
    convite, e o CSS documentava aquilo como um dos três lugares canônicos do
    arco-íris. Não era: circundar a marca com o gradiente DESCARACTERIZA a
    marca do cliente, numa peça feita para o cliente. Este teste existe para o
    anel não voltar por distração."""
    css = CSS.read_text(encoding="utf-8")
    assert "om-anel" not in css
    for pagina in TODAS:
        assert "om-anel" not in _html(pagina), pagina


def test_a_marca_usada_e_o_vetor_oficial():
    """`marca-grupo-om.svg` é o vetor que o Leandro guarda no site dele: 27
    `<path>`, nenhum `<circle>`, só o escrito "GRUPO OM | COMUNICAÇÃO
    INTEGRADA". Nada de moldura, nada de anel.

    Ele substitui o raster branco nas três superfícies onde a marca aparece:
    escala sem perda em qualquer densidade de tela e pesa menos."""
    svg = ATIVOS / "marca-grupo-om.svg"
    assert svg.is_file()
    fonte = svg.read_text(encoding="utf-8")
    assert "<circle" not in fonte
    assert fonte.count("<path") == 27, fonte.count("<path")
    for pagina in TODAS:
        assert "marca-grupo-om.svg" in _html(pagina), pagina
        assert "marca-grupoom-white.webp" not in _html(pagina), pagina


def test_a_marca_preta_e_invertida_na_tela_e_nao_no_papel():
    """O vetor oficial é PRETO, e as três superfícies onde ele aparece são
    grafite. Sem a inversão, a marca do cliente some da própria proposta. E
    sem desfazê-la no `@media print`, ela some da folha, que é o mesmo erro
    virado do avesso: lá o fundo já é branco."""
    css = _css()
    # A regra da MARCA é a que nomeia as três superfícies de uma vez; a busca
    # precisa ser por ela, e não por `.om-marca img`, que também abre a regra
    # de tamanho lá em cima e faria o teste conferir a declaração errada.
    marca = r"\.om-marca img,\s*\.om-convite-marca img,\s*\.om-rodape-marca img\s*\{([^}]*)\}"
    tela = re.search(marca, css[:css.index("@media print")])
    assert tela and "invert(1)" in tela.group(1), "na tela a marca preta precisa inverter"
    papel = re.search(marca, css[css.index("@media print"):])
    assert papel and "filter: none" in papel.group(1), "no papel a inversão sai"


def test_a_regua_tipografica_tem_tres_degraus_bem_separados():
    """"Não tem hierarquias" foi a reclamação, e ela era concreta: tudo vivia
    entre 16 e 50 px. A régua agora é medida, e o teto de cada degrau precisa
    ser pelo menos 1,5x o teto do degrau de baixo. É esse salto que É a
    hierarquia."""
    css = _css()

    def teto(nome):
        bloco = re.search(r"--t-" + nome + r":\s*([^;]+);", css).group(1)
        return float(re.findall(r"([\d.]+)rem", bloco)[-1])

    kicker, declaracao, manchete = teto("kicker"), teto("declaracao"), teto("manchete")
    assert kicker == 0.875, "o kicker é 14 px e é FIXO: ele é a régua"
    assert ";" not in css[css.index("--t-kicker"):css.index("--t-kicker") + 30] or True
    assert "clamp" not in re.search(r"--t-kicker:\s*([^;]+);", css).group(1), \
        "se o kicker crescer junto com a manchete, a razão entre eles nunca muda"
    assert declaracao / kicker >= 2.5, (kicker, declaracao)
    assert manchete / declaracao >= 1.5, (declaracao, manchete)


def test_a_grade_do_conteudo_e_assimetrica():
    """A segunda metade da hierarquia. O documento de referências descreve uma
    grade desequilibrada, ~35/65, e o desequilíbrio é o que faz a página
    parecer composta em vez de empilhada. Duas colunas iguais seriam a home de
    agência de sempre."""
    css = _css()
    grade = re.search(r"\.om-assim\s*\{[^}]*\}\s*", css)
    assert grade, ".om-assim precisa existir"
    colunas = re.search(r"\.om-assim\s*\{\s*grid-template-columns:\s*([^;]+);", css[css.index("@media (min-width: 62em)"):])
    assert colunas, "a assimetria só entra na largura em que ela é assimetria"
    assert "35fr" in colunas.group(1) and "65fr" in colunas.group(1), colunas.group(1)


# ==========================================================================
# O CLIENTE DENTRO DA PÁGINA: 28 marcas e 6 empresas, nenhuma inventada
# ==========================================================================

# O CONTRATO DA FITA DE CLIENTES: arquivo baixado -> nome que a página
# escreve. É aqui que "não invente cliente" vira uma regra que a máquina
# confere. Para acrescentar uma marca é preciso baixar o logo dela ANTES.
#
# DUAS ausências deliberadas, e as duas estão no relatório:
#   - `marca-grupo-om.svg` é o wordmark da PRÓPRIA agência, não um cliente;
#   - `logo-digital-premium.webp` está baixado e NÃO está aqui. "Digital
#     Premium" tem cara de selo ou de certificação de parceria, não de marca
#     atendida, e ninguém confirmou o que é. Numa fita cuja única função é
#     provar quem o grupo atende, um item que talvez não seja cliente custa a
#     credibilidade da fita inteira.
LOGOS_DE_CLIENTE = {
    "logo-burger-king.webp": "Burger King",
    "logo-caloi.webp": "Caloi",
    "logo-continental.webp": "Continental",
    "logo-corteva.webp": "Corteva Agriscience",
    "logo-cummins.webp": "Cummins",
    "logo-cvale.webp": "C.Vale",
    "logo-daju.webp": "Daju",
    "logo-dsm-firmenich.webp": "dsm-firmenich",
    "logo-frimesa.webp": "Frimesa",
    "logo-fujioka.webp": "Fujioka Distribuidor",
    "logo-grupo-boticario.webp": "Grupo Boticário",
    "logo-hebron.webp": "Hebron",
    "logo-inpev.webp": "inpEV",
    "logo-jacomar.webp": "Jacomar",
    "logo-max-atacadista.webp": "Max Atacadista",
    "logo-oab-esa.webp": "OAB Nacional e ESA",
    "logo-ocp.webp": "OCP Brasil",
    "logo-oticas-carol.webp": "Óticas Carol",
    "logo-popeyes.webp": "Popeyes",
    "logo-servopa.webp": "Consórcio Servopa",
    "logo-shmueller.webp": "Shopping Mueller",
    "logo-starbucks.webp": "Starbucks",
    "logo-subway.webp": "Subway",
    "logo-unicharm.webp": "Unicharm",
    "logo-uninter.webp": "Uninter",
    "logo-vero.webp": "Vero",
    "logo-volvo.webp": "Volvo",
}

# As SEIS empresas do grupo, em vetor. É a pergunta que o site atual do
# cliente não responde em nenhuma das cinco páginas dele.
EMPRESAS_DO_GRUPO = {
    "logo_brainbox.svg": "Brainbox",
    "logo_dom_preto.svg": "D’OM Soluções Improváveis",
    "logo_housecricket_preto.svg": "House Cricket",
    "logo_opusmultipla_preto.svg": "OpusMúltipla",
    "logo_senso_preto.svg": "Senso",
    "logo_tailormedia_preto.svg": "Tailor Media",
}


def test_toda_marca_da_fita_tem_logo_baixado():
    """A regra central, e a que protege o pitch: NENHUM cliente citado na fita
    pode ser um nome que alguém digitou. Cada um precisa ter um arquivo de
    logo baixado do site do próprio Grupo OM, e o nome escrito tem que ser o
    nome daquele arquivo."""
    html = _html("home")
    # A fita é a lista real MAIS uma cópia, que é o que permite o laço não ter
    # emenda. A cópia é decorativa: o `<ul>` dela é `aria-hidden`, e cada
    # imagem lá dentro tem `alt` vazio. Sem essa separação, o leitor de tela
    # anunciaria vinte e sete marcas duas vezes.
    copias = re.findall(r'<ul class="om-fita-lista om-fita-copia"[^>]*>.*?</ul>', html, re.S)
    assert len(copias) == 2, len(copias)
    for copia in copias:
        assert 'aria-hidden="true"' in copia[:copia.index(">") + 1]

    vistos = set()
    for src, tag in _imagens("home"):
        arquivo = src.split("?")[0].rsplit("/", 1)[-1]
        if not arquivo.startswith("logo-"):
            continue
        assert arquivo in LOGOS_DE_CLIENTE, f"logo fora do contrato: {arquivo}"
        assert (ATIVOS / arquivo).is_file(), arquivo
        # O `(?<!-)` não é firula: `data-alt` (o ajuste óptico de cada logo)
        # casaria com um `alt="..."` ingênuo e o teste conferiria o atributo
        # errado, passando com o texto alternativo vazio.
        alt = re.search(r'(?<!-)\balt="([^"]*)"', tag).group(1)
        if any(tag in copia for copia in copias):
            assert alt == "", (arquivo, alt)
            continue
        assert alt == LOGOS_DE_CLIENTE[arquivo], (arquivo, alt)
        vistos.add(arquivo)
    assert vistos == set(LOGOS_DE_CLIENTE), set(LOGOS_DE_CLIENTE) - vistos


def test_nenhum_logo_da_fita_traz_caixa_assada_no_arquivo():
    """A LIÇÃO DO ITEM 13, virada em teste.

    A Frimesa entrou na fita com o arquivo que o site do cliente publica,
    `logo-frimesa-sombra.png`, e ele vinha com uma caixa branca e uma sombra
    ASSADAS no bitmap. Numa fileira de vinte e sete logos recortados, um logo
    com moldura não parece um logo com moldura: parece um erro de quem montou
    a fita, e quem lê a peça é um diretor de arte.

    O teste é o canto: um logo recortado tem os quatro cantos transparentes.
    Se alguém trocar um arquivo por uma versão com plano de fundo, isto
    reprova antes de a fita chegar ao cliente. Logos que o próprio desenho
    leva até o canto (um selo quadrado, por exemplo) ficam de fora pelo nome
    do ajuste óptico `selo`, que é justamente o que os declara redondos ou
    quadrados de propósito.
    """
    from PIL import Image

    fita = (RAIZ / "app/templates/lab/sites/grupo-om/_fita.html"
            ).read_text(encoding="utf-8")
    tuplas = re.findall(r'\("(logo-[a-z0-9.-]+\.webp)",\s*"[^"]*",\s*"([a-z]*)"', fita)
    assert len(tuplas) == 27, len(tuplas)

    for arquivo, ajuste in tuplas:
        assert "sombra" not in arquivo, (
            f"{arquivo}: nome de arquivo do site do cliente que denuncia caixa "
            "assada. Baixe a versão limpa antes de pôr na fita.")
        if ajuste == "selo":
            continue
        with Image.open(ATIVOS / arquivo) as im:
            im = im.convert("RGBA")
            w, h = im.size
            cantos = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
            for x, y in cantos:
                assert im.getpixel((x, y))[3] == 0, (
                    f"{arquivo}: canto ({x}, {y}) é opaco. O arquivo tem plano "
                    "de fundo assado e vai destoar da fileira inteira.")


def test_a_lista_de_clientes_em_texto_bate_com_a_lista_de_logos():
    """A fita corre e não pode ser lida por buscador, por leitor de tela nem
    no papel. Por isso os mesmos vinte e sete nomes vão em texto logo abaixo.

    As duas listas saem do MESMO `set` no template, então elas não podem
    divergir; este teste é o que garante que continuem saindo."""
    trecho = re.search(r'class="om-lista-nomes">(.*?)</p>', _html("home"), re.S).group(1)
    trecho = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", trecho)).strip().rstrip(".")
    nomes = [n.strip() for n in trecho.split(",")]
    assert set(nomes) == set(LOGOS_DE_CLIENTE.values()), \
        set(nomes) ^ set(LOGOS_DE_CLIENTE.values())
    assert len(nomes) == 27


def test_as_seis_empresas_do_grupo_aparecem_com_o_vetor_delas():
    """"Somos 6 empresas" é a frase com que o Grupo OM se define, e o site
    atual nunca diz QUAIS. Esta proposta diz, e só pode dizer porque os seis
    vetores estão no repositório: nomear as seis sem os arquivos seria
    adivinhar, e foi por isso que a versão anterior nomeou só quatro.

    O QUE MUDOU EM 26/08, com o item 3. O mesmo vetor agora aparece uma segunda
    vez por página, pequeno, ao lado do nome da empresa que assina cada case. E
    ali ele é DECORATIVO, com `alt` vazio de propósito: o nome está escrito em
    texto no mesmo elemento, e um `alt` preenchido faria o leitor de tela
    anunciar "OpusMúltipla OpusMúltipla".

    Por isso o teste passou a olhar as duas coisas separadamente: todo `logo_`
    da página tem que estar no contrato (nenhuma empresa inventada entra), e os
    seis precisam aparecer ao menos uma vez com o nome escrito no `alt`, que é
    a ocorrência do cartão de `_empresas.html`."""
    for pagina in ("home", "sobre"):
        nomeados = {}
        for src, tag in _imagens(pagina):
            arquivo = src.split("?")[0].rsplit("/", 1)[-1]
            if not arquivo.startswith("logo_"):
                continue
            assert arquivo in EMPRESAS_DO_GRUPO, f"empresa fora do contrato: {arquivo}"
            assert (ATIVOS / arquivo).is_file(), arquivo
            alt = re.search(r'(?<!-)\balt="([^"]*)"', tag).group(1)
            if alt:
                nomeados[arquivo] = alt
        assert nomeados == EMPRESAS_DO_GRUPO, (pagina, nomeados)


def test_nenhuma_marca_famosa_de_fora_aparece_em_pagina_nenhuma():
    """O contraponto: uma lista fechada só prova o que ela contém. Estas são
    marcas grandes e plausíveis que o material do Grupo OM NÃO traz. Se alguma
    aparecer, alguém preencheu a página com o que soava bem, que é exatamente
    o defeito que reprovou as duas versões anteriores."""
    for pagina in TODAS:
        texto = _texto_visivel(pagina)
        for inventada in ("Coca-Cola", "Nestlé", "Ambev", "Itaú", "Natura", "Bradesco",
                          "Petrobras", "Vivo", "Magalu", "Renner", "Havaianas", "Heineken"):
            assert inventada not in texto, (pagina, inventada)


def test_os_numeros_das_paginas_sao_todos_conferiveis():
    """O contador anima do zero, mas quem não tem script precisa ver o número
    pronto: por isso o valor final já está no HTML, e o teste exige que os
    dois batam.

    E a lista de valores é FECHADA. 6 e 47 saem palavra por palavra do site do
    cliente; 28 é a contagem dos logos da fita; 3 é a contagem dos nomes do
    comitê de inclusão, que estão na mesma página. Um quinto número aparecendo
    aqui é um número que ninguém conferiu."""
    conferiveis = {"6", "47", "27", "3"}
    achados = set()
    for pagina in TODAS:
        for alvo, escrito in re.findall(r'data-conta="(\d+)">(\d+)<', _html(pagina)):
            assert alvo == escrito, (pagina, alvo, escrito)
            assert alvo in conferiveis, (pagina, alvo)
            achados.add(alvo)
    assert achados == conferiveis, conferiveis - achados
    assert len(LOGOS_DE_CLIENTE) == 27
    assert len(EMPRESAS_DO_GRUPO) == 6


def test_os_servicos_sao_os_sete_que_o_site_atual_nomeia():
    """A versão anterior listava NOVE, e dois deles ("identidades visuais",
    "embalagens") não estavam no material colhido: eram invenção que passou
    despercebida porque nenhum teste olhava para a lista. Estes são os sete
    que o site do cliente nomeia, e a lista é fechada dos dois lados."""
    itens = re.findall(r'<span class="om-item-nome">([^<]+)</span>', _html("home"))
    assert itens == [
        "Consultoria estratégica de marcas",
        "Branding e identidade de marca",
        "Design gráfico e de produto",
        "Comunicação integrada e publicidade",
        "Marketing digital e performance",
        "Inteligência e gestão de mídia",
        "Relacionamento e customer experience",
    ], itens


def test_o_indice_de_servicos_nao_promete_um_clique_que_nao_existe():
    """ITEM 14, e a contradição que ele traz junto.

    O Leandro pediu hover de volta nas sete linhas de serviço. O hover tinha
    sido removido num ciclo anterior porque essas linhas NÃO SÃO LINK e não
    têm destino: a peça tem cinco páginas e nenhuma delas é "Branding". O
    documento admite as duas saídas, e a preferida (virar link de verdade)
    exigiria inventar sete páginas de serviço, ou seja, escrever em nome da
    agência texto que a agência não escreveu.

    Então vale a segunda: o movimento é destaque de LEITURA. Este teste é o
    que impede a primeira saída de voltar pela porta dos fundos, um `cursor:
    pointer` de cada vez.
    """
    html = _html("home")
    indice = re.search(r'<ol class="om-indice om-indice-leitura"[^>]*>(.*?)</ol>',
                       html, re.S).group(1)
    assert "<a " not in indice and "href=" not in indice, \
        "uma linha de serviço virou link: ou ela tem destino de verdade, ou o " \
        "hover está prometendo o que a página não cumpre"
    # Nenhum ícone nas sete linhas: seta é a palavra "vá", e é justamente a
    # promessa que estas linhas não podem fazer.
    assert "om-ic" not in indice, indice[:200]

    css = _css()
    regras = re.findall(r"([^{}]*\.om-indice-leitura[^{}]*)\{([^}]*)\}", css)
    assert regras, "o índice de leitura sumiu do CSS"
    for seletor, corpo in regras:
        assert "cursor" not in corpo, (seletor, corpo)
        assert "text-decoration" not in corpo, (seletor, corpo)
        # `translateX` e afins deslocam a linha na direção da leitura, que é o
        # gesto de "seguir para". `scaleX` do fio é outra coisa: ele desenha
        # uma régua, e régua não leva a lugar nenhum.
        assert "translate" not in corpo, (seletor, corpo)


def test_o_indice_de_servicos_ganha_leitura_no_hover_e_fio_na_rolagem():
    """As duas metades que o item 14 pede, e as duas guardas que as tornam
    honestas.

    HOVER: quem muda são as OUTRAS linhas, que recuam. A linha sob o cursor
    fica onde estava, e é isso que a impede de parecer alvo. Tudo dentro de
    `(hover: hover)`, porque no celular o `:hover` gruda depois do toque e a
    lista ficaria com seis linhas apagadas.

    ROLAGEM: o fio de cada linha se desenha, e o repouso dele é CHEIO. Sem
    `om-js` (sem script, sem GSAP, ou porque a pessoa pediu menos movimento) a
    lista nasce com os sete fios inteiros, e nada some.
    """
    css = _css()

    # TODAS as media queries de hover, e não a primeira: em 27/08 o menu de
    # tela cheia ganhou a sua, mais acima no arquivo, e este teste passou a
    # reprovar um bloco que continuava correto no lugar de sempre.
    blocos = re.findall(r"@media \(hover: hover\)[^{]*\{(.*?)\n\}", css, re.S)
    dentro = next((b for b in blocos if ".om-indice-leitura" in b), None)
    assert dentro, "o hover do índice precisa viver atrás de `(hover: hover)`"
    assert re.search(r"\.om-indice-leitura:hover > li\s*\{[^}]*opacity:\s*\.\d+", dentro), \
        "as outras linhas precisam recuar; é o recuo delas que faz a leitura"
    assert re.search(r"\.om-indice-leitura > li:hover\s*\{[^}]*opacity:\s*1", dentro), \
        "a linha sob o cursor não pode se mexer nem se apagar"

    # O REPOUSO É CHEIO: a única regra que zera o fio está atrás de `.om-js`.
    zerados = re.findall(r"([^{}]*\.om-indice-leitura[^{}]*::after[^{}]*)\{([^}]*)\}", css)
    assert zerados, "o fio do índice sumiu"
    for seletor, corpo in zerados:
        if "scaleX(0)" in corpo:
            assert ".om-js" in seletor, seletor
    assert any("scaleX(0)" in c for _, c in zerados), "o fio nunca é zerado"
    assert re.search(r"\.om-js .om-indice-leitura > li\.om-tracado::after\s*\{[^}]*scaleX\(1\)",
                     css), "o fio é zerado e nunca é desenhado"

    # E o papel: imprimir não rola, então o fio precisa sair inteiro na folha.
    papel = css[css.index("@media print"):]
    assert re.search(r"\.om-indice-leitura > li::after\s*\{[^}]*transform:\s*none", papel)

    # A rolagem põe a classe, e o cinto de segurança a põe de novo se o
    # observador não disparar.
    js = JS.read_text(encoding="utf-8")
    assert js.count('classList.add("om-tracado")') == 2, \
        "o fio precisa do gatilho E da rede de segurança, como toda revelação"
    assert '[data-indice] > li' in js


def test_os_depoimentos_sao_os_tres_do_site_e_tem_nome_e_cargo():
    """Depoimento sem assinatura é depoimento inventado até prova em
    contrário. Os três que o site publica têm nome e cargo, e é assim que eles
    aparecem aqui. Os dois de funcionário ficaram de fora: são marca
    empregadora, e não venda."""
    texto = _texto_visivel("sobre")
    for nome, cargo in (
        ("Fernanda Salgueiro", "Hospital Pequeno Príncipe"),
        ("Elias José Zydek", "Frimesa"),
        ("Daniela Baruch", "Shopping Mueller"),
    ):
        assert nome in texto, nome
        assert cargo in texto, cargo


def test_o_comite_de_inclusao_traz_os_tres_nomes_publicados():
    """A diferenciação que nenhum concorrente copia num pitch, e a frase mais
    forte de todo o material do cliente."""
    texto = _texto_visivel("certificacoes")
    assert "Não dá para agradar todo mundo" in texto
    for nome in ("Toni Reis", "Mariluce Mariá de Souza", "Rafael Bonfim"):
        assert nome in texto, nome


# ==========================================================================
# ITEM 11: BILÍNGUE PT/EN, ESCRITO À MÃO
# ==========================================================================

# As frases que NÃO se traduzem, e o teste que as guarda existe porque
# traduzir nome próprio é escrever errado o nome de outra empresa.
NOMES_QUE_NAO_MUDAM = (
    "Grupo OM", "OpusMúltipla", "D’OM Soluções Improváveis", "Senso",
    "Brainbox", "House Cricket", "Tailor Media",
    "Fogo & Sabor", "Sonhos Possíveis",
    "Toni Reis", "Mariluce Mariá de Souza", "Rafael Bonfim",
    "Rua Jaguariaíva", "Rua Cardoso de Melo", "Vila Olímpia",
    # ITEM 27 trouxe os dezoito cases reais, e com eles nomes próprios que
    # CONTÊM palavra funcional do português. "São Paulo" é uma cidade e
    # "Junto com a Mamy" é o nome de uma campanha: traduzir qualquer um dos
    # dois seria escrever errado o nome de uma coisa que existe.
    "São Paulo", "Junto com a Mamy", "Junto com a mamy, até no nome",
)

# Palavras funcionais do português. Nenhuma delas é nome próprio, nenhuma é
# empréstimo aceito em inglês, e qualquer uma delas dentro da página em inglês
# quer dizer uma frase que ficou para trás.
PALAVRAS_DE_PORTUGUES = (
    "que", "para", "não", "com", "uma", "dos", "das", "pelo", "pela", "como",
    "mais", "seu", "sua", "nós", "você", "este", "esta", "são", "tem", "foi",
)


def _frases_marcadas():
    """Toda frase que um template mandou traduzir, literal ou por dado.

    As duas fontes existem porque a peça marca de dois jeitos: `T("Serviços")`
    no template, e `T(c.abre)` sobre o texto que mora em `_dados_cases.html`.
    Um teste que olhasse só o primeiro deixaria de fora exatamente o texto do
    CLIENTE, que é o mais caro de errar.
    """
    d = RAIZ / "app/templates/lab/sites/grupo-om"
    # `_base_redesign.html` mora um nível acima e também marca frase (a aba de
    # volta para o Lab). Sem ele aqui, a tradução dela parece órfã e o teste
    # irmão reprova uma frase que está em uso nas nove páginas.
    frases = []
    for arq in sorted(list(d.glob("*.html")) + list((d / "case").glob("*.html"))
                      + [RAIZ / "app/templates/lab/sites/_base_redesign.html"]):
        limpo = re.sub(r"\{#.*?#\}", " ", arq.read_text(encoding="utf-8"), flags=re.S)
        frases += re.findall(r'T\("([^"]+)"\)', limpo)
        # O cargo de quem deu o depoimento chega ao `T()` como ARGUMENTO do
        # macro `assina_voz` (item 20), e não escrito dentro dele. Sem esta
        # linha, os três cargos sairiam da varredura e a página em inglês
        # traria "Superintendente do Shopping Mueller" sem ninguém notar.
        frases += [c for _, c in re.findall(
            r'assina_voz\("([^"]+)",\s*"([^"]+)"\)', limpo)]

    # O TEXTO DO CLIENTE mudou de casa nesta rodada: ele saiu de
    # `_dados_cases.html` e virou `app/lab/cases_grupo_om.py`, porque o filtro
    # por empresa e por categoria é resolvido no servidor. A varredura seguiu
    # junto, e ela é a parte que mais importa: são os DEZOITO cases reais, com
    # título, resumo, texto e ficha técnica, que é o material mais caro de
    # deixar sem tradução.
    #
    # Os NOMES DE PESSOA da ficha técnica ficam de fora de propósito: o
    # template traduz o papel ("VP de Conteúdo e Integração") e nunca quem o
    # ocupa, porque nome próprio traduzido é nome errado.
    for c in om.CASES:
        frases += [c["titulo"], c["resumo"]] + list(c["corpo"])
        frases += [papel for papel, _ in c["ficha"]]
    frases += [nome for _, nome in om.CATEGORIAS]

    # A CENTRAL DE CONTEÚDO (27/08) marca pelo dado do mesmo jeito que os
    # cases: os oito artigos (título, resumo, abertura), os cinco serviços
    # (título, chamada, soluções) e os títulos dos vídeos chegam ao `T()`
    # como valor, e sem esta varredura as traduções deles parecem órfãs.
    for a in conteudo_om.ARTIGOS:
        frases += [a["titulo"], a["resumo"]] + list(a["corpo"])
    for s_ in conteudo_om.SERVICOS:
        frases += [s_["titulo"], s_.get("chamada", "")] + list(s_["solucoes"])
    frases += [v["titulo"] for v in conteudo_om.VIDEOS]

    return [f for f in dict.fromkeys(frases) if f]


def test_toda_frase_marcada_para_traducao_tem_ingles():
    """A guarda central do item 11, e a razão de a chave ser o português.

    Uma chave sem entrada não quebra nada em produção: o tradutor devolve o
    português, e o visitante de fora lê uma frase solta em português no meio da
    página em inglês. É um defeito que NÃO se anuncia, e que só aparece quando
    alguém que fala as duas línguas lê a página inteira com atenção.

    Este teste é o que faz ele aparecer, e ele cobre as duas maneiras de marcar
    uma frase: `T("...")` escrito no template, e `T(c.abre)` sobre o texto do
    cliente que mora em `_dados_cases.html`.
    """
    faltando = [f for f in _frases_marcadas() if f not in EN]
    assert not faltando, (
        f"{len(faltando)} frase(s) marcadas para tradução sem inglês escrito. "
        f"A primeira: {faltando[0]!r}")


def test_nenhuma_traducao_sobra_no_dicionario():
    """O contrário do teste acima, e ele existe pela mesma razão.

    Uma entrada que nenhum template usa é ou uma frase que mudou no português
    (e a tradução ficou órfã, enquanto a nova frase sai sem traduzir), ou texto
    que alguém apagou e esqueceu aqui. Nos dois casos o dicionário passa a
    mentir sobre o tamanho da peça, e quem for traduzir a próxima página não
    tem como saber o que ainda vale.
    """
    marcadas = set(_frases_marcadas())
    orfas = [chave for chave in EN if chave not in marcadas]
    assert not orfas, f"{len(orfas)} tradução(ões) sem uso. A primeira: {orfas[0]!r}"


@pytest.mark.parametrize("pagina", TODAS)
def test_a_pagina_em_ingles_nao_deixa_portugues_para_tras(pagina):
    """Meia tradução é pior que nenhuma: ela promete um site bilíngue e
    entrega um site remendado, na peça cujo argumento é cuidado.

    A varredura é por PALAVRA FUNCIONAL, e não por acento: "Jaguariaíva" e
    "Mariluce Mariá" têm acento e devem ficar, porque são nomes. Um "que" ou um
    "não" solto, não: nenhum deles é nome de nada, e cada um denuncia uma frase
    inteira que não passou pelo dicionário."""
    texto = _texto_visivel_lang(pagina, "en")
    # Os nomes próprios saem ANTES da varredura, e não viram exceção dentro
    # dela: é o nome inteiro que não se traduz, e é dentro dele que a palavra
    # funcional aparece sem ser sobra de frase ("São Paulo", "Junto com a
    # Mamy"). Tirar o nome e varrer o resto é o que mantém o teste severo.
    for nome in NOMES_QUE_NAO_MUDAM:
        texto = texto.replace(nome, " ")
    achados = sorted({p for p in PALAVRAS_DE_PORTUGUES
                      if re.search(rf"(?i)(?<![\w-]){re.escape(p)}(?![\w-])", texto)})
    assert not achados, (pagina, achados)


@pytest.mark.parametrize("pagina", TODAS)
def test_o_ingles_nao_traduz_nome_proprio(pagina):
    """Nome de empresa traduzido é nome errado, e numa peça feita PARA a
    empresa é o erro mais caro da lista. Se um nome aparece na página em
    português, ele aparece igual na página em inglês."""
    pt = _texto_visivel_lang(pagina, "pt")
    en = _texto_visivel_lang(pagina, "en")
    for nome in NOMES_QUE_NAO_MUDAM:
        if nome in pt:
            assert nome in en, (pagina, nome)


@pytest.mark.parametrize("pagina", TODAS)
def test_a_pagina_em_ingles_se_declara_em_ingles(pagina):
    """`<html lang>` é o que faz o leitor de tela trocar de voz. Uma página em
    inglês servida como `pt-BR` é lida com pronúncia portuguesa, palavra por
    palavra, e vira ruído. É também o que decide a hifenização e o que o
    buscador lê para saber que existem duas versões."""
    assert 'lang="en"' in _html(pagina, lang="en"), pagina
    assert 'lang="pt-BR"' in _html(pagina, lang="pt"), pagina


@pytest.mark.parametrize("pagina", TODAS)
def test_as_duas_linguas_se_declaram_uma_a_outra(pagina):
    """`hreflang` é como o buscador aprende que estas duas páginas são a mesma
    coisa em idiomas diferentes, em vez de duas páginas concorrendo. O
    `x-default` aponta para o PORTUGUÊS, que é a língua do cliente e do
    material: é ele que responde a quem chega sem preferência declarada."""
    # E o par declarado é o DESTA página, não o da capa: um `hreflang` que
    # apontasse sempre para a raiz diria ao buscador que as treze páginas em
    # inglês são a mesma coisa, e ele indexaria uma.
    aqui = "" if pagina == "home" else "/" + pagina
    for lang in ("pt", "en"):
        html = _html(pagina, lang=lang)
        assert f'<link rel="alternate" hreflang="pt-BR" href="{BASE}{aqui}">' in html, (pagina, lang)
        assert f'<link rel="alternate" hreflang="en" href="{BASE}/en{aqui}">' in html, (pagina, lang)
        assert f'<link rel="alternate" hreflang="x-default" href="{BASE}{aqui}">' in html, (pagina, lang)


@pytest.mark.parametrize("pagina", TODAS)
def test_o_seletor_leva_a_ESTA_pagina_do_outro_lado(pagina):
    """Um seletor que sempre volta para a capa faz o leitor perder o lugar
    onde estava, e um leitor que perde o lugar fecha a proposta. Quem está na
    página de cases e clica em EN espera a página de cases em inglês.

    ITEM 15 MUDOU O RÓTULO PARA SIGLA. Numa linha só, "Português" era a peça
    mais larga do canto direito e a que menos precisava da largura. A sigla
    mostrada é a do idioma de DESTINO, que é para onde o link leva.

    E o nome por extenso não sumiu, mudou de lugar: ele vive no `aria-label`,
    que é onde o leitor de tela o lê. "EN" lido em voz alta é uma letra e um
    ruído, e é por isso que este teste confere os DOIS."""
    sufixo = "" if pagina == "home" else f"/{pagina}"
    pt = _html(pagina, lang="pt", sufixo=sufixo)
    assert f'href="{BASE}/en{sufixo}"' in pt, pagina
    assert ">EN</span>" in pt, pagina
    assert 'aria-label="View this page in English"' in pt, pagina

    en = _html(pagina, lang="en", sufixo=sufixo)
    assert f'href="{BASE}{sufixo}"' in en, pagina
    assert ">PT</span>" in en, pagina
    assert 'aria-label="Ver esta página em português"' in en, pagina


@pytest.mark.parametrize("pagina", TODAS)
def test_o_menu_em_ingles_fica_em_ingles(pagina):
    """Quem abriu a peça em inglês precisa continuar em inglês ao clicar em
    qualquer item do menu. A língua é propriedade do PREFIXO, e é a rota que a
    decide: se um `href` do menu escapasse sem o `/en`, o clique jogaria o
    visitante de volta ao português no meio da leitura."""
    html = _html(pagina, lang="en")
    miolo = html[html.index("<header"):]
    for destino in ("/sobre", "/cases", "/certificacoes", "/contato"):
        assert f'href="{BASE}/en{destino}"' in miolo, (pagina, destino)


@pytest.mark.parametrize("pagina", TODAS)
def test_a_marca_de_autoria_da_spec_vale_nas_duas_linguas(pagina):
    """A §8 não tem versão traduzida: a página está no domínio do Leandro, com
    a marca de outra empresa, e pode vazar do link. Ela precisa dizer quem fez
    e que não é o site oficial em QUALQUER língua em que seja lida.

    Era o risco mais fácil de correr no item 11: traduzir a faixa de copyright
    e deixar a garantia para trás na tradução."""
    en = _texto_visivel_lang(pagina, "en")
    assert "Leandro Furtado" in en, pagina
    assert "not the official website" in en, pagina


def test_nenhum_recurso_de_fora_entrou_com_a_traducao():
    """O item 11 nasceu como "tradução automática", e tradução automática quer
    dizer widget de terceiro. A decisão foi a oposta, e este teste é o que
    impede a decisão de ser desfeita por conveniência: nenhuma página, em
    nenhuma das duas línguas, pode carregar host externo.

    Vale lembrar por quê: a peça inteira existe para dizer que a home atual
    entrega 212 KB. Um widget de tradução somaria centenas de KB e um terceiro
    rastreando o visitante do cliente, dentro da proposta que critica isso."""
    for pagina in TODAS:
        for lang in ("pt", "en"):
            html = _html(pagina, lang=lang)
            # `src` é RECURSO e não pode vir de fora em hipótese nenhuma;
            # `href` é navegação, e obedece à mesma lista fechada do teste
            # `test_todo_link_externo_e_endereco_do_proprio_cliente`.
            assert not re.findall(r'src="(//[^"]*|https?://[^"]*)"', html), (pagina, lang)
            for atributo in re.findall(r'href="(//[^"]*|https?://[^"]*)"', html):
                atributo = atributo.replace("&amp;", "&")
                assert (atributo in ENDERECOS_DO_CLIENTE
                        or atributo.startswith(INTENCOES_DE_PARTILHA)), \
                    (pagina, lang, atributo)


# ==========================================================================
# CSS: o que não é estético e não se negocia
# ==========================================================================

def test_o_css_desliga_movimento_para_quem_pediu():
    """A base já põe o piso, e o CSS da marca não pode reintroduzir movimento
    por cima dele."""
    assert "prefers-reduced-motion" in CSS.read_text(encoding="utf-8")


def test_o_css_nao_usa_largura_fixa_na_estrutura():
    """Responsiva de verdade, e o celular primeiro (§8). Largura em pixel numa
    caixa de layout é o jeito clássico de quebrar em telas estreitas."""
    suspeitas = re.findall(r"\bwidth:\s*(\d{3,})px", CSS.read_text(encoding="utf-8"))
    assert not [s for s in suspeitas if int(s) > 480], suspeitas


def test_o_foco_nao_reescreve_o_raio_das_pilulas():
    """A regra de foco é (0,1,1) e ganhava das pílulas: tabular pelo teclado
    transformava botão redondo em retângulo. O `outline` já acompanha o raio
    do elemento sozinho."""
    foco = re.search(r":focus-visible\s*\{([^}]*)\}", _css()).group(1)
    assert "border-radius" not in foco


def test_a_pagina_tem_regra_de_impressao():
    """Proposta comercial é o link que o dono encaminha e imprime. Sem
    `@media print` sai branco no branco, e o que espera o observador de
    rolagem sai invisível, porque imprimir não rola a página."""
    css = CSS.read_text(encoding="utf-8")
    assert "@media print" in css
    trecho = css[css.index("@media print"):]
    assert "opacity: 1 !important" in trecho, "o que é revelado por rolagem precisa sair no papel"


def test_a_impressao_desmancha_a_mascara_dos_titulos():
    """O caso que quase passou. O SplitText corta cada título em linhas e
    esconde cada uma numa janela com `overflow: clip`; a linha só sobe quando
    o observador de rolagem dispara, e IMPRIMIR NÃO ROLA. Sem estas regras,
    todo título abaixo da primeira dobra sai como um retângulo vazio no papel
    que o dono mandou imprimir."""
    css = _css()
    trecho = css[css.index("@media print"):]
    assert ".om-split div" in trecho
    bloco = trecho[trecho.index(".om-split div"):]
    bloco = bloco[:bloco.index("}")]
    assert "overflow: visible !important" in bloco
    assert "transform: none !important" in bloco


def test_a_fita_de_clientes_nao_depende_de_script_para_existir():
    """Sem `om-js` a fita não corre: ela vira uma grade parada com os vinte e
    sete logos, e a cópia decorativa some. Uma proposta que mostra uma fila
    cortada na borda quando o script falha perde o único argumento que ela
    tinha."""
    css = _css()
    assert ".om-fita-copia { display: none; }" in css
    assert ".om-js .om-fita-copia { display: flex; }" in css
    assert re.search(r"\.om-fita-lista\s*\{[^}]*flex-wrap:\s*wrap", css), \
        "sem script, a lista precisa quebrar linha em vez de sangrar"


def test_o_css_e_o_js_do_redesign_entram_na_minificacao():
    """Metade dos dois arquivos é comentário interno: direção de arte, crítica
    ao que o site do cliente faz hoje e o log dos consertos do autor. No git
    eles são bons; servidos ao dono da agência, são constrangimento. O padrão
    em `minify_build.py` pega estes e os dos próximos redesigns."""
    lista = (RAIZ / "scripts/minify_build.py").read_text(encoding="utf-8")
    assert 'RAIZ.glob("lab/sites/*.css")' in lista
    assert 'RAIZ.glob("lab/sites/*.js")' in lista


# ==========================================================================
# AS ROTAS DAS INTERNAS
# ==========================================================================

@pytest.fixture(autouse=True)
def _balde_de_taxa_limpo():
    """`limitar_taxa` é dependency do router `/lab` inteiro, e o balde vive em
    memória de MÓDULO, compartilhada pela suíte. Os testes de rota deste
    arquivo fazem várias requisições cada (são cinco páginas, dois endereços e
    onze nomes de travessia), e sem esta limpeza o balde do único IP que a
    `TestClient` usa se esgota no meio do arquivo: um teste de conteúdo passa
    a falhar com 429, que é um erro que não tem nada a ver com o que ele
    afirma. Mesma fixture de `tests/lab/conftest.py`, e pela mesma razão."""
    from app.lab import protecao
    protecao._requisicoes.clear()
    protecao._chamadas_desde_a_ultima_poda = 0
    yield


def _client():
    return TestClient(app, base_url="https://testserver")


def _no_banco(**campos):
    """Redesign gravado no banco que as ROTAS enxergam (SessionLocal real),
    diferente do fixture `db` do conftest, que é um SQLite em memória à parte.

    O `create_all` não é redundante: as tabelas do banco real só nascem no
    `lifespan` do app, e este arquivo escreve ANTES de entrar no `TestClient`.
    Rodando a suíte inteira elas já existem porque outro teste subiu o app
    antes; rodando só este arquivo, não existiriam. Um teste que só passa
    acompanhado não prova nada."""
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)

    padrao = dict(slug="grupo-om", marca="Grupo OM", setor="Marketing e comunicação",
                  antes_url="https://grupoom.com.br", token=novo_token())
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


INTERNAS = ("sobre", "cases", "certificacoes", "contato")


def test_as_internas_abrem_no_endereco_publico():
    slug, _, _ = _no_banco(estado="publico")
    with _client() as c:
        for interna in INTERNAS:
            r = c.get(f"/lab/sites/{slug}/{interna}")
            assert r.status_code == 200, interna
            assert f'href="/lab/sites/{slug}/cases"' in r.text, interna
    _limpar()


def test_as_internas_respondem_404_no_publico_enquanto_e_pitch():
    """A MESMA regra da home, e ela é a que faz o recorte do estado `pitch`
    ser real. Se as internas abrissem, o recorte cairia por uma porta lateral,
    que é sempre por onde ele cairia mesmo."""
    slug, _, _ = _no_banco(estado="pitch")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}").status_code == 404
        for interna in INTERNAS:
            assert c.get(f"/lab/sites/{slug}/{interna}").status_code == 404, interna
    _limpar()


def test_as_internas_abrem_pelo_token_e_o_menu_fica_dentro_do_token():
    """Quem recebeu o link do pitch precisa poder navegar as cinco sem cair
    no endereço público, que responde 404 justamente enquanto é pitch."""
    _, token, _ = _no_banco(estado="pitch")
    with _client() as c:
        for interna in INTERNAS:
            r = c.get(f"/lab/p/{token}/{interna}")
            assert r.status_code == 200, interna
            assert f'href="/lab/p/{token}/cases"' in r.text, interna
            assert 'href="/lab/sites/' not in r.text, interna
    _limpar()


def test_a_interna_pelo_token_e_noindex():
    """O endereço do token é `noindex` SEMPRE, e isso é propriedade do
    endereço, não do estado. Uma interna que esquecesse disso seria a porta
    por onde o token vaza para o buscador."""
    _, token, _ = _no_banco(estado="publico")
    with _client() as c:
        r = c.get(f"/lab/p/{token}/cases")
    assert "noindex" in r.text
    assert r.headers.get("x-robots-tag", "").startswith("noindex")
    _limpar()


def test_a_interna_publica_continua_indexavel_quando_o_estado_permite():
    slug, _, _ = _no_banco(estado="publico")
    with _client() as c:
        r = c.get(f"/lab/sites/{slug}/sobre")
    assert "noindex" not in r.text
    assert "noindex" not in r.headers.get("x-robots-tag", "")
    _limpar()


@pytest.mark.parametrize("nome", [
    "../../../../etc/passwd",
    "..%2f..%2fmain",
    "%2e%2e%2f%2e%2e%2fmain",
    "../_base_redesign",
    "..",
    "sobre.",
    "sobre.html",
    "SOBRE",
    "sobre/../../padaria-aurora/home",
    "_topo",
    "-sobre",
])
def test_o_nome_da_pagina_recusa_travessia_de_diretorio(nome):
    """A peneira que impede a URL de virar caminho de arquivo. Sem ela,
    `/lab/sites/grupo-om/../../..%2fetc/passwd` seria leitura de arquivo
    arbitrária num servidor que também hospeda o portfólio inteiro do
    Leandro.

    Minúscula e hífen, e mais nada: sem ponto, sem barra, sem `%`, sem
    maiúscula, e precisa começar por letra. Os parciais (`_topo`, `_pe`) caem
    na mesma regra, e é de propósito: eles não são páginas."""
    slug, _, _ = _no_banco(estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}/{nome}").status_code == 404, nome
    _limpar()


def test_pagina_que_nao_existe_no_disco_e_404():
    """A última peneira, e é ela que faz um redesign de página única responder
    404 em qualquer interna sem precisar de lista nenhuma na rota."""
    slug, token, _ = _no_banco(estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}/precos").status_code == 404
        assert c.get(f"/lab/p/{token}/precos").status_code == 404
    _limpar()


def test_o_redesign_de_pagina_unica_nao_ganha_interna():
    """A Padaria Aurora tem só `home.html`. Nenhuma das cinco internas do
    Grupo OM pode existir para ela por acidente."""
    slug, _, _ = _no_banco(slug="padaria-aurora", marca="Padaria Aurora",
                           setor="Panificação", estado="publico")
    with _client() as c:
        for interna in INTERNAS:
            assert c.get(f"/lab/sites/{slug}/{interna}").status_code == 404, interna
    _limpar()


def test_home_nao_tem_segundo_endereco():
    """`/lab/sites/<slug>` já é a home. Servi-la também em
    `/lab/sites/<slug>/home` seria a mesma página em dois endereços
    indexáveis, que é o conteúdo duplicado que a própria rota se dá ao
    trabalho de evitar entre o token e o público."""
    slug, token, _ = _no_banco(estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}").status_code == 200
        assert c.get(f"/lab/sites/{slug}/home").status_code == 404
        assert c.get(f"/lab/p/{token}/home").status_code == 404
    _limpar()


def test_a_interna_pelo_token_carimba_visto_em():
    """O cliente pode abrir o link direto numa interna, e isso é tão "o
    cliente abriu a proposta" quanto abrir a capa."""
    _, token, ident = _no_banco(estado="pitch")
    with _client() as c:
        c.get(f"/lab/p/{token}/cases")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is not None
    _limpar()


def test_a_interna_vinda_do_loopback_nao_carimba_visto_em():
    """§9.1, a armadilha, e ela vale nas internas também. A captura do
    "depois" roda na própria máquina e precisa passar pelo link do token; se
    carimbasse, o Leandro marcaria o cliente como tendo visto a proposta antes
    de mandar o link."""
    _, token, ident = _no_banco(estado="pitch")
    with TestClient(app, base_url="https://testserver",
                    client=("127.0.0.1", 5555)) as c:
        c.get(f"/lab/p/{token}/sobre")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is None
    _limpar()


def test_o_endereco_publico_de_interna_nunca_carimba_visto_em():
    """`visto_em` é sinal de PITCH. Uma visita à galeria pública não é o
    cliente abrindo a proposta dele."""
    slug, _, ident = _no_banco(estado="publico")
    with _client() as c:
        c.get(f"/lab/sites/{slug}/cases")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is None
    _limpar()


def test_as_rotas_novas_herdam_o_rate_limit():
    """Mesma regra de todo o /lab: o router inteiro carrega `limitar_taxa`, e
    uma rota nova não pode nascer fora dela."""
    from app.lab.protecao import limitar_taxa
    from app.lab.rotas_sites import router

    caminhos = set()
    for rota in router.routes:
        chamadas = [d.call for d in rota.dependant.dependencies]
        assert limitar_taxa in chamadas, rota.path
        caminhos.add(rota.path)
    assert "/lab/sites/{slug}/{pagina}" in caminhos, caminhos
    assert "/lab/p/{token}/{pagina}" in caminhos, caminhos


# ==========================================================================
# ITEM 8: AS PÁGINAS INTERNAS DE CASE
# ==========================================================================

def test_toda_interna_de_case_tem_arquivo_e_esta_na_lista_da_listagem():
    """Os DEZOITO cases de `cases_grupo_om.py` e os dezoito arquivos em `case/`
    são a MESMA lista, e este teste é o que impede as duas de divergirem.

    O jeito de quebrar isso é o mais fácil de todos: acrescentar um case aos
    dados e esquecer o arquivo. A rota decide entre 200 e 404 pela existência
    do arquivo, então esse esquecimento produz um link para uma página que
    responde 404 no meio da proposta. E o contrário também reprova: um arquivo
    em `case/` sem entrada nos dados quebraria na renderização, porque o
    template procura o slug em `por_slug`."""
    no_disco = {arq.stem for arq in (PASTA / "case").glob("*.html")}
    assert no_disco == {c["slug"] for c in om.CASES}, no_disco
    # E o case que SAIU (item 34) saiu dos três lugares: dos dados, do disco e
    # da pasta de imagens. Um arquivo órfão em `case/` é um 404 desenhado, e um
    # webp órfão é peso morto que ninguém mais vai procurar.
    for slug in CASES_REMOVIDOS:
        assert slug not in no_disco, slug
        assert not (ATIVOS / "cases" / f"{slug}.webp").exists(), slug
    # E cada arquivo declara o SEU slug, não o de um vizinho copiado.
    for c in om.CASES:
        fonte = (PASTA / "case" / f"{c['slug']}.html").read_text(encoding="utf-8")
        assert f'{{% set caso = "{c["slug"]}" %}}' in fonte, c["slug"]


@pytest.mark.parametrize("pagina", CASES)
def test_a_interna_de_case_traz_a_marca_de_quem_assina(pagina):
    """A página de um case mostra a MARCA de quem assina, duas vezes: no pé da
    capa e no trilho do próximo case.

    ITEM 32 REESCREVEU ESTE TESTE. Ele exigia o contrário: a marca com o nome
    da empresa escrito ao lado, dentro do mesmo elemento, e o `alt` vazio para
    o leitor de tela não ouvir "OpusMúltipla OpusMúltipla". O Leandro decidiu
    que **ou é o nome, ou é a logo, nunca os dois**, e a regra vale para o site
    inteiro. Então o que este teste guarda agora é o inverso: a marca aparece
    SOZINHA, e o nome que sumiu da tela continua no `alt`, que é onde o leitor
    de tela e o buscador o encontram."""
    html = _html(pagina)
    marcas = re.findall(r'<img class="om-assinatura-marca[^>]*>', html)
    assert len(marcas) >= 2, (pagina, len(marcas))
    nomes = {e["nome"] for e in om.EMPRESAS} | {om.GRUPO["nome"]}
    for tag in marcas:
        arquivo = re.search(r'src="/static/lab/sites/grupo-om/([^"]+)"', tag).group(1)
        assert arquivo in EMPRESAS_DO_GRUPO or arquivo == "marca-grupo-om.svg", arquivo
        assert (ATIVOS / arquivo).is_file(), arquivo
        # O nome vive AQUI, e em nenhum outro lugar ao lado do desenho.
        alt = re.search(r'alt="([^"]*)"', tag).group(1)
        assert alt in nomes, tag
        # E as medidas do arquivo continuam no HTML: sem elas a imagem presa
        # abaixo da dobra reserva zero e o bloco pula quando ela chega.
        assert re.search(r'width="\d+" height="\d+"', tag), tag


def test_o_envelope_que_punha_nome_e_logo_lado_a_lado_nao_existe_mais():
    """ITEM 32, a metade que é fácil de reintroduzir sem perceber.

    `.om-assinatura` era um `<span>` de flex com o logo de um lado e
    `<b>nome</b>` do outro. Um teste que só olha a página de hoje não impede
    ninguém de trazer a macro de volta amanhã, então este olha os DOIS lugares
    onde ela poderia renascer: a marcação de todas as vinte e sete páginas e a
    folha de estilo que a desenhava."""
    for pagina in TODAS:
        assert 'class="om-assinatura"' not in _html(pagina), pagina
        assert 'class="om-assinatura"' not in _html(pagina, lang="en"), pagina
    assert ".om-assinatura " not in _css()
    assert ".om-assinatura{" not in _css().replace(" ", "").replace("\n", "")


def test_nenhum_bloco_mostra_o_nome_e_a_logo_da_mesma_empresa_juntos():
    """ITEM 32, e ele vale para o SITE INTEIRO, não só para o trilho.

    A regra do Leandro: "nunca o nome da empresa junto da logo dela; ou um, ou
    outro". Ela é uma regra de DIAGRAMAÇÃO, e por isso a unidade que este teste
    mede é o BLOCO (`<section>`, `<header>`, `<footer>`), e não a página: a
    marca do cabeçalho aparece em todas as vinte e sete páginas, e medir por
    página proibiria escrever "Grupo OM" em qualquer lugar do site, inclusive
    no `<h1>` da página do grupo, que é exatamente o caso que a segunda metade
    da regra manda manter ("onde não há logo, o nome fica").

    Dentro de cada bloco: se o desenho de uma empresa está ali, o nome dela não
    pode estar escrito ali. O `alt` não conta, e é por isso que ele é o lugar
    certo do nome: ele não é texto na tela.

    O QUE A VARREDURA IGNORA, e é declarado em vez de silencioso:

    1. o CORPO de um case cita empresas dentro de frases publicadas pelo
       cliente ("a D'OM criou a sequência do clássico"). Isso é texto do
       cliente, não rótulo ao lado de um desenho, e reescrever a prosa dele
       seria falsificar o material. Fora: `.om-texto`, `.om-declaracao`,
       `.om-citacao` e `<blockquote>`.
    2. a FICHA do case escreve "Empresa do grupo: OpusMúltipla" em texto, e
       ali não há logo nenhum. O teste seguinte confere que ela continua assim.
    3. os 27 CLIENTES da fita não são empresas do grupo, e a lista de nomes em
       texto que acompanha a fita é a versão que o papel e o buscador leem de
       uma marquise que se move. Ela é caption, não rótulo colado num desenho.
    4. os CONTROLES: `<nav>` e `<details>`. O filtro por empresa da página de
       cases lista as seis por nome, com a contagem de cada uma, na mesma
       seção em que a grade mostra os logos. Uma opção de menu É um nome; pôr
       o desenho de uma marca dentro de uma lista de opções seria pior, não
       melhor. Um controle que lista nomes não é um rótulo pregado num
       desenho, que é do que a regra fala.
    """
    arquivo_por_nome = {e["nome"]: e["arquivo"] for e in om.EMPRESAS}
    arquivo_por_nome[om.GRUPO["nome"]] = om.GRUPO["arquivo"]
    blocos = re.compile(r"<(section|header|footer)\b.*?</\1>", re.S)
    vistos = 0
    for pagina in TODAS:
        for lang in ("pt", "en"):
            html = _html(pagina, lang=lang)
            # O `<title>` e o `<head>` não são tela.
            corpo = html[html.find("<body"):] if "<body" in html else html
            for m in blocos.finditer(corpo):
                bloco = m.group(0)
                sem_controles = re.sub(r"<(nav|details)\b.*?</\1>", " ",
                                       bloco, flags=re.S)
                visivel = _texto_sem_prosa_do_cliente(sem_controles)
                for nome, arquivo in arquivo_por_nome.items():
                    if f"/static/lab/sites/grupo-om/{arquivo}" not in bloco:
                        continue
                    vistos += 1
                    assert nome not in visivel, (pagina, lang, nome, visivel[:160])
    # Se a varredura parar de encontrar logo nenhum, ela passa sem medir nada.
    assert vistos > 50, vistos


def test_a_ficha_do_case_escreve_o_nome_porque_ali_nao_ha_logo():
    """A outra metade do item 32: "onde não há logo, o nome fica".

    A ficha técnica é o único lugar da peça onde o nome da empresa que assina
    aparece escrito, e ela pode, porque ela não mostra o desenho. Se alguém
    puser um logo dentro da ficha, esta linha reprova e a regra volta a ser
    decidida por uma pessoa, não por descuido."""
    for pagina in CASES:
        html = _html(pagina)
        ficha = re.search(r'<dl class="om-ficha.*?</dl>', html, re.S).group(0)
        assert "<img" not in ficha, pagina
        caso = om.POR_SLUG[pagina.split("/")[-1]]
        assert om.assinante(caso["empresa"])["nome"] in ficha, pagina


@pytest.mark.parametrize("pagina", CASES)
def test_o_trilho_do_proximo_case_mostra_a_arte_dele(pagina):
    """ITEM 32, primeira metade: "o cartão do próximo case ganha a imagem do
    case, como os da grade".

    A imagem é a do PRÓXIMO, e não a desta página. Parece óbvio, e é
    exatamente o tipo de erro que um `{{ c.imagem }}` copiado do bloco de cima
    produz sem barulho: o trilho mostraria a arte que a pessoa acabou de ver e
    convidaria para outra coisa.

    E ela é FIGURA, não link: o cartão já tem um botão para o mesmo endereço,
    e um segundo link faria o leitor de tela anunciar o mesmo destino duas
    vezes."""
    html = _html(pagina)
    trilho = re.search(r'<figure class="om-proximo-arte.*?</figure>', html, re.S)
    assert trilho, pagina
    bloco = trilho.group(0)
    atual = om.POR_SLUG[pagina.split("/")[-1]]
    proximo = om.CASES[(om.CASES.index(atual) + 1) % len(om.CASES)]
    assert f'src="{proximo["imagem"]}"' in bloco, (pagina, bloco[:150])
    assert atual["imagem"] not in bloco, pagina
    assert 'alt=""' in bloco, bloco
    assert "<a " not in bloco, bloco
    assert (RAIZ / "app/static" / proximo["imagem"].lstrip("/")
            .removeprefix("static/")).is_file()


def test_a_fileira_de_compartilhar_e_uma_linha_so():
    """ITEM 29: "a fileira de redes fica em UMA LINHA só".

    Uma linha que não cabe precisa rolar, e a armadilha aqui é a mesma que já
    empurrou a fileira de selos 788 px para fora da tela: **item de grade nasce
    com `min-width: auto`**, e um contêiner com `overflow-x: auto` dentro de
    uma grade CRESCE em vez de rolar. Por isso as duas coisas são testadas
    juntas: sem a segunda, a primeira é um estouro com nome bonito."""
    css = _css()
    fileira = re.search(r"\.om-partilha-redes \{(.*?)\}", css, re.S).group(1)
    assert "flex-wrap: nowrap" in fileira, fileira
    assert "overflow-x: auto" in fileira, fileira
    assert "flex-wrap: wrap" not in fileira, fileira
    # A tranca da grade, sem a qual a fileira não rola: ela cresce.
    assert re.search(r"\.om-assim > \*[^{]*\{[^}]*min-inline-size: 0", css), \
        "sem `min-inline-size: 0` no filho da grade, a fileira estoura a página"
    # E o alvo de toque continua vindo do token, nunca de uma conta de padding.
    pilula = re.search(r"\.om-partilha-redes a \{(.*?)\}", css, re.S).group(1)
    assert "min-block-size: var(--alvo)" in pilula, pilula


def test_o_bloco_de_compartilhar_responde_ao_mouse_e_para_com_menos_movimento():
    """ITEM 29, segunda metade: o bloco inteiro ganha movimento no hover, no
    vocabulário que a peça já usa, e nada que pule ou mude de tamanho.

    "Nada que pule ou mude tamanho" é a parte que este teste guarda de
    verdade: as regras de hover deste bloco só podem mexer em `transform`,
    `opacity` e cor. Uma largura, uma margem ou um `font-size` ali dentro é
    reflow no meio de uma fileira de oito alvos de toque, com o dedo da pessoa
    a caminho de um deles.

    E `prefers-reduced-motion` desliga o movimento SEM esvaziar o bloco: a
    seta é `aria-hidden` e some, o deslocamento morre, e a cor fica, porque
    cor não é movimento."""
    css = _css()
    hovers = re.findall(r"\.om-partilha:hover[^{]*\{([^}]*)\}", css)
    assert len(hovers) >= 4, hovers
    permitido = {"transform", "opacity", "color", "border-block-start-color",
                 "border-color"}
    for corpo in hovers:
        for decl in filter(None, (d.strip() for d in corpo.split(";"))):
            prop = decl.split(":")[0].strip()
            assert prop in permitido, decl
    reduzido = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}",
                         css, re.S).group(1)
    assert ".om-partilha:hover .om-partilha-t { transform: none" in reduzido
    assert ".om-partilha:hover .om-partilha-seta" in reduzido
    # E no papel a fileira volta a quebrar linha: imprimir não rola.
    impressao = re.search(r"@media print \{(.*)", css, re.S).group(1)
    assert re.search(r"\.om-partilha-redes \{[^}]*flex-wrap: wrap !important",
                     impressao, re.S), "a folha sairia com quatro redes e meia"


def test_a_ficha_cabe_na_coluna_estreita_sem_quebrar_rotulo():
    """ITEM 30. Os três números que mandaram na mudança estão no CSS, e o que
    este teste guarda é a estrutura que os produziu:

    - a ficha volta a UMA coluna em 62em, que é onde a grade assimétrica
      nasce e a coluna dela encolhe para 35% (medido: 389 px viravam dois
      campos de 183 px, e "Empresa do grupo" saía em duas linhas);
    - o rótulo é menor e menos apertado que o kicker de 14 px da peça;
    - não há ícone dentro do rótulo: era o mesmo desenho repetido em cada
      papel da ficha, e num rótulo de 11,5 px ele custava 19 px de largura
      mais o vão, que é a diferença entre uma linha e duas."""
    css = _css()
    # A ÚLTIMA declaração de colunas da ficha é a que vale na tela larga, e o
    # corte que a antecede precisa ser o de 62em, que é onde a grade
    # assimétrica entra. Procurar "um" bloco de 62em não serve: há três no
    # arquivo, e o teste passaria olhando o errado.
    colunas = list(re.finditer(r"\.om-ficha \{ grid-template-columns: ([^;]+);", css))
    assert len(colunas) == 2, [c.group(1) for c in colunas]
    assert colunas[-1].group(1).strip() == "minmax(0, 1fr)", colunas[-1].group(1)
    antes = css[:colunas[-1].start()]
    assert antes.rfind("@media (min-width: 62em)") > antes.rfind("@media (min-width: 48em)")
    dt = re.search(r"\.om-ficha dt \{(.*?)\}", css, re.S).group(1)
    assert "font-size: .72rem" in dt, dt
    assert "letter-spacing: .09em" in dt, dt
    assert "text-wrap: balance" in dt, dt
    for pagina in CASES:
        ficha = re.search(r'<dl class="om-ficha.*?</dl>', _html(pagina), re.S).group(0)
        assert "<svg" not in ficha, pagina


def test_a_pagina_do_case_usa_a_largura_maxima_menos_a_arte():
    """ITEM 31, e a metade dele que é fácil de esquecer.

    A capa, a ficha e o trilho passam a `om-largo`, que é a mesma largura do
    cabeçalho e do rodapé. A ARTE não passa, e a razão é medida: o arquivo tem
    960 px, já é esticado 1,37 vez em `om-wrap` numa tela de 1440, e em
    `om-largo` numa de 1920 seriam 1,85 vez. A regra do item é "onde houver
    aproveitamento a GANHAR", e esticar a arte de um cliente até ela ficar
    mole não é ganho.

    E o texto corrido continua com medida de leitura: a coluna da prosa tem
    teto próprio, senão a página vira uma faixa de ponta a ponta em 1920."""
    fonte = (PASTA / "_corpo_case.html").read_text(encoding="utf-8")
    assert fonte.count('class="om-largo') == 3, fonte.count('class="om-largo')
    arte = re.search(r'<section class="om-secao om-secao-arte".*?</section>',
                     fonte, re.S).group(0)
    assert 'class="om-wrap"' in arte
    assert "om-largo" not in arte
    assert 'class="om-case-prosa"' in fonte
    assert re.search(r"\.om-case-prosa \{[^}]*max-inline-size", _css())


def test_a_marca_de_uma_empresa_reserva_espaco_antes_de_carregar():
    """Defeito MEDIDO nesta rodada, e ele tinha um comentário ao lado
    afirmando o contrário.

    Duas coisas quebravam a mesma regra:

    1. `.om-assinatura-marca` é (0,1,0) e `.rd-grupo-om img { max-inline-size:
       100% }` é (0,1,1). O teto de largura da assinatura nunca valeu: medido,
       o lockup do Grupo OM saía com 269 px de largura na capa do case contra
       os 120 px que o comentário prometia.
    2. com `inline-size: auto` E `block-size: auto` escritos, os atributos
       `width`/`height` do HTML param de reservar espaço, e a imagem presa
       abaixo da dobra media 0x0 até o arquivo chegar. Medido no trilho.

    O conserto das duas é uma linha cada: o seletor passa a começar em
    `.rd-grupo-om`, e a altura vira DEFINIDA, com `object-fit: contain` para o
    teto de largura encolher o desenho em vez de distorcê-lo."""
    css = _css()
    regra = re.search(r"\.rd-grupo-om \.om-assinatura-marca \{(.*?)\}", css, re.S)
    assert regra, "o seletor precisa passar de (0,1,1) para vencer `.rd-grupo-om img`"
    corpo = regra.group(1)
    assert re.search(r"\bblock-size: [\d.]+rem", corpo), corpo
    assert "object-fit: contain" in corpo, corpo
    assert "max-inline-size" in corpo, corpo
    assert "block-size: auto" not in corpo, corpo
    # E a variante grande vem DEPOIS, senão ela perde a altura para a de cima.
    assert (css.index(".rd-grupo-om .om-assinatura-grande {")
            > css.index(".rd-grupo-om .om-assinatura-marca {"))


# AS OITO REDES QUE COMPARTILHAM DE VERDADE, e o que cada endereço de intenção
# precisa carregar. O Instagram NÃO está aqui, por decisão do Leandro em 26/08:
# ele não tem endereço de intenção público na web, e um botão que abre a home
# do Instagram no celular de quem clicou é pior que botão nenhum. Ele continua
# no rodapé, como PERFIL.
PARTILHA = (
    ("https://x.com/intent/post?", "url"),
    ("https://www.facebook.com/sharer/sharer.php?", "u"),
    ("https://www.linkedin.com/sharing/share-offsite/?", "url"),
    ("https://pinterest.com/pin/create/button/?", "url"),
    ("https://www.threads.net/intent/post?", "text"),
    ("https://wa.me/?text=", None),
    ("https://t.me/share/url?", "url"),
)


@pytest.mark.parametrize("pagina", CASES)
def test_a_partilha_do_case_e_link_de_intencao_e_nunca_widget(pagina):
    """"Botões de compartilhamento por rede", e a decisão de COMO.

    LINK, NUNCA WIDGET. Nenhum SDK oficial entra: a Global Constraint 11
    proíbe host externo de script, a CSP da peça é `default-src 'self'`, e um
    widget oficial ainda carregaria rastreador de terceiro na página que a
    proposta usa para acusar o site do cliente de peso. O que este teste
    garante é que o compartilhamento continue sendo oito `<a href>`, e que
    nenhum `<script src>` de rede social apareça junto.

    E CADA UM PRECISA CARREGAR O ENDEREÇO DESTE CASE. Um botão de partilha que
    aponta para a rede sem levar a URL é um botão que abre a caixa de mensagem
    vazia: parece que funcionou, e não compartilhou nada.
    """
    from urllib.parse import quote

    html = _html(pagina).replace("&amp;", "&")
    caso = pagina.split("/", 1)[1]
    esperado = f"{ABS}{BASE}/case/{caso}"
    for prefixo, _ in PARTILHA:
        elo = re.search(re.escape(prefixo) + r'[^"]*', html)
        assert elo, (pagina, prefixo)
        # `safe="/"` porque é assim que o filtro `urlencode` do Jinja escapa:
        # a barra dentro de um valor de query é legal, e o que não pode passar
        # cru (`?`, `&`, `#`, espaço, acento) ele escapa.
        assert quote(esperado, safe="/") in elo.group(0), (pagina, prefixo)
    # O e-mail é `mailto:` SEM destinatário: ele abre o cliente de e-mail da
    # pessoa com o assunto e o corpo prontos, e não manda nada para ninguém.
    assert 'href="mailto:?subject=' in html, pagina
    # O Pinterest exige imagem, e agora existe uma: sem `media` ele abre vazio.
    assert "media=" in html, pagina
    # NENHUM SCRIPT de rede social, que é a forma como isto normalmente vaza.
    for widget in ("platform.twitter.com", "connect.facebook.net",
                   "platform.linkedin.com", "assets.pinterest.com",
                   "apis.google.com"):
        assert widget not in html, (pagina, widget)


@pytest.mark.parametrize("pagina", CASES)
def test_a_partilha_do_case_guarda_o_copiar_e_o_enviar_do_navegador(pagina):
    """O COPIAR ENDEREÇO é o que resolve o Instagram e qualquer app sem
    endereço de intenção, e o ENVIAR é a folha nativa do sistema no celular.

    Os dois nascem `hidden` e só aparecem quando a API existe, pelo mesmo
    motivo de todos os outros controles de script desta peça: botão que não faz
    nada é pior que botão nenhum. O que NÃO nasce escondido é a fileira das
    oito redes, porque ela é feita de links e funciona sem script nenhum."""
    html = _html(pagina)
    caixa = re.search(r'<div class="om-partilha-bts"[^>]*>', html).group(0)
    assert "data-partilha" in caixa, caixa
    for controle in ("data-partilha-nativo", "data-partilha-copiar"):
        marca = re.search(r"<button[^>]*" + controle + r"[^>]*>", html).group(0)
        assert "hidden" in marca, marca
    redes = re.search(r'<nav class="om-partilha-redes"[^>]*>', html).group(0)
    assert "hidden" not in redes, redes
    js = JS.read_text(encoding="utf-8")
    assert "navigator.share" in js and "navigator.clipboard" in js


@pytest.mark.parametrize("pagina", CASES)
def test_a_interna_de_case_leva_de_volta_e_para_o_proximo(pagina):
    """Uma interna sem volta é um beco no meio da proposta, e a pessoa que
    chegou nela por um link direto não tem nem o botão do navegador para
    contar. E o "próximo case" existe por razão comercial: quem terminou de ler
    um case é quem está mais perto de ler o segundo."""
    html = _html(pagina)
    assert f'href="{BASE}/cases"' in html, pagina
    # A checagem é dentro do `<main>`, e não no documento: o menu de tela cheia
    # (item 5) lista os CINCO cases de propósito, o atual incluído, porque ele
    # é o índice do site e não a navegação deste case.
    miolo = html[html.index("<main>"):html.index("</main>")]
    proximos = re.findall(rf'href="{re.escape(BASE)}/case/([a-z-]+)"', miolo)
    assert proximos, pagina
    atual = pagina.split("/", 1)[1]
    assert all(p != atual for p in proximos), (pagina, proximos)


def test_a_rota_de_case_abre_no_publico_e_pelo_token():
    from app.lab import protecao

    slug, token, _ = _no_banco(estado="publico")
    with _client() as c:
        for caminho in CASES:
            # Dezoito cases vezes duas requisições estouram o balde, e um 429
            # aqui seria o limitador reprovando um teste que não fala dele.
            protecao._requisicoes.clear()
            caso = caminho.split("/", 1)[1]
            r = c.get(f"/lab/sites/{slug}/case/{caso}")
            assert r.status_code == 200, caso
            r = c.get(f"/lab/p/{token}/case/{caso}")
            assert r.status_code == 200, caso
            assert f'href="/lab/p/{token}/cases"' in r.text, caso
            assert 'href="/lab/sites/' not in r.text, caso
    _limpar()


def test_a_rota_de_case_responde_404_no_publico_enquanto_e_pitch():
    """A MESMA regra da home e das internas, dois níveis mais fundo. Um
    recorte de estado que vale na capa e não vale no endereço mais profundo
    não é recorte, é sugestão: bastaria adivinhar um nome de case para ler uma
    proposta que ainda não foi mostrada ao cliente."""
    from app.lab import protecao

    slug, token, _ = _no_banco(estado="pitch")
    with _client() as c:
        for caminho in CASES:
            protecao._requisicoes.clear()
            caso = caminho.split("/", 1)[1]
            assert c.get(f"/lab/sites/{slug}/case/{caso}").status_code == 404, caso
            assert c.get(f"/lab/p/{token}/case/{caso}").status_code == 200, caso
    _limpar()


@pytest.mark.parametrize("nome", [
    "../../../../etc/passwd",
    "..%2f..%2fmain",
    "%2e%2e%2f%2e%2e%2fmain",
    "ninfa.",
    "ninfa.html",
    "NINFA",
    "ninfa/../../padaria-aurora/home",
    "-ninfa",
    "precos",
])
def test_o_nome_do_case_recusa_travessia_de_diretorio(nome):
    """A rota nova herda a MESMA peneira da interna, e é de propósito: um
    segundo formato de nome, mais frouxo, seria uma segunda porta para a mesma
    travessia de diretório, e a segunda porta é sempre a que fica sem tranca."""
    slug, token, _ = _no_banco(estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}/case/{nome}").status_code == 404, nome
        assert c.get(f"/lab/p/{token}/case/{nome}").status_code == 404, nome
    _limpar()


def test_o_case_pelo_token_e_noindex_e_carimba_visto_em():
    """O endereço do token é `noindex` SEMPRE, e isso é propriedade do
    endereço, não do estado. E o carimbo vale aqui como nas outras: o Leandro
    pode ter mandado o link direto de um case."""
    _, token, ident = _no_banco(estado="publico")
    with _client() as c:
        r = c.get(f"/lab/p/{token}/case/{UM_CASE}")
    assert r.status_code == 200
    assert "noindex" in r.text
    assert r.headers.get("x-robots-tag", "").startswith("noindex")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is not None
    _limpar()


def test_o_case_vindo_do_loopback_nao_carimba_visto_em():
    """§9.1, a armadilha, e ela vale na rota nova também: a captura do
    "depois" roda na própria máquina e passa pelo link do token."""
    _, token, ident = _no_banco(estado="pitch")
    with TestClient(app, base_url="https://testserver",
                    client=("127.0.0.1", 5555)) as c:
        c.get(f"/lab/p/{token}/case/{UM_CASE}")
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is None
    _limpar()


def test_o_redesign_de_pagina_unica_nao_ganha_case():
    """A Padaria Aurora tem só `home.html` e nenhuma pasta `case/`. Nenhum dos
    cinco cases do Grupo OM pode existir para ela por acidente."""
    slug, _, _ = _no_banco(slug="padaria-aurora", marca="Padaria Aurora",
                           setor="Panificação", estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}/case/{UM_CASE}").status_code == 404
    _limpar()


# ==========================================================================
# ITEM 9: OS SELOS REAIS
# ==========================================================================

# O CONTRATO DOS SELOS, e ele é o mesmo da fita de clientes: para um selo
# entrar na página, o ARQUIVO dele precisa ter sido baixado antes, e o nome
# escrito tem que ser o nome daquele arquivo. É assim que "não invente prêmio"
# vira regra que a máquina confere.
#
# O CONTRATO AGORA MORA EM `app/lab/selos_grupo_om.py`, e não numa cópia aqui:
# ele alimenta o rodapé de todas as páginas E a página de certificações, e uma
# segunda lista escrita no teste só serviria para as duas divergirem em
# silêncio. O que o teste continua guardando é o que importa: nada entra sem
# arquivo, e nada some sem alguém perceber.
#
# A GPTW VOLTOU nesta rodada, e a volta dela é o teste funcionando. Ela tinha
# saído porque a certificação era real mas NÃO HAVIA ARQUIVO, e um selo de
# terceiro desenhado por nós seria marca falsificada numa peça que vai para o
# dono da empresa. O Leandro mandou o arquivo oficial; com arquivo, ela entra
# como CERTIFICAÇÃO ATIVA, nunca como prêmio.


def test_todo_selo_do_contrato_tem_arquivo_no_disco():
    """A regra que faz "não invente prêmio" ser conferível: nenhum selo pode
    ser afirmado sem o arquivo. Vale para os dois grupos, e é este teste que
    deixa um selo novo entrar sozinho no dia em que o arquivo dele chegar."""
    assert len(selos.CERTIFICACOES) == 4, len(selos.CERTIFICACOES)
    assert len(selos.PREMIOS) == 12, len(selos.PREMIOS)
    for arquivo, nome, largura, altura in selos.TODOS:
        caminho = ATIVOS / arquivo
        assert caminho.is_file(), arquivo
        assert nome, arquivo
        # E as medidas declaradas são as do arquivo: `width`/`height` errados
        # são reserva de espaço errada, que é salto de layout no celular.
        from PIL import Image
        with Image.open(caminho) as im:
            assert im.size == (largura, altura), (arquivo, im.size)


def test_todo_selo_exibido_esta_no_contrato_e_nos_dois_grupos():
    """Um `src` errado não dá erro em lugar nenhum: dá um retângulo vazio no
    meio de uma página de prêmios, que é o pior lugar possível para um buraco.

    `selo-new-york-festvals.webp` tem o nome escrito errado na origem, sem o
    "i" de Festivals. O arquivo fica como está, porque renomear ativo baixado
    é perder o rastro de onde ele veio; o nome exibido é o certo, e é por isso
    que o contrato mapeia um no outro em vez de derivar um do outro."""
    contrato = {arquivo: nome for arquivo, nome, _, _ in selos.TODOS}
    vistos = {}
    for src, tag in _imagens("certificacoes"):
        arquivo = src.split("?")[0].rsplit("/", 1)[-1]
        if not arquivo.startswith("selo-"):
            continue
        assert arquivo in contrato, f"selo fora do contrato: {arquivo}"
        vistos[arquivo] = re.search(r'(?<!-)\balt="([^"]*)"', tag).group(1)
    assert vistos == contrato, set(contrato) ^ set(vistos)


@pytest.mark.parametrize("pagina", TODAS)
def test_os_selos_vao_soltos_no_rodape_de_toda_pagina(pagina):
    """ITEM 23, e a correção do Leandro em 26/08: "aumente os selos dos prêmios
    também". Imagem solta, sem caixa em volta, maior, nos DOIS grupos, e no
    rodapé de todas as páginas.

    A prova de que a caixa saiu é o CSS: a regra dos selos soltos não pode
    trazer `background`, `border` nem `border-radius`, que eram exatamente as
    três coisas que faziam cada selo parecer um cartão."""
    html = _html(pagina)
    rodape = html[html.index('<footer class="om-rodape">'):]
    fileiras = re.findall(r'<ul class="om-selos-soltos">(.*?)</ul>', rodape, re.S)
    assert len(fileiras) == 2, (pagina, len(fileiras))
    assert fileiras[0].count("<img") == len(selos.CERTIFICACOES), pagina
    assert fileiras[1].count("<img") == len(selos.PREMIOS), pagina
    css = _css()
    caixa = re.search(r"\.om-selos-soltos li\s*\{([^}]*)\}", css)
    if caixa:
        for proibido in ("background", "border", "border-radius"):
            assert proibido not in caixa.group(1), (proibido, caixa.group(1))
    # COMO A FILEIRA IGUALA, e isto mudou em 26/08 depois de o Leandro ver a
    # tela: "todos na mesma proporção". Igualar por ALTURA não iguala. Um logo
    # largo e baixo (Prêmio Colunistas) fica com o triplo da área de um
    # quadrado (Cannes) na mesma altura, e o olho lê área, não altura.
    #
    # Agora a caixa é do `<li>`, idêntica para todos, e cada desenho se
    # encaixa dentro dela pelo lado que o limita primeiro. É o que
    # `object-fit: contain` faz.
    caixa_li = re.search(r"\.om-selos-soltos > li\s*\{([^}]*)\}", css).group(1)
    assert "block-size:" in caixa_li and "inline-size:" in caixa_li, caixa_li
    # Caixa FIXA: com `flex: 1 1 0` quatro selos dividiam 1400 px e cada um
    # ficava sozinho no meio de um campo de 340. Uniforme é caixa igual,
    # não espaço igual.
    assert "flex: 0 0 auto" in caixa_li, caixa_li
    regra = re.search(r"\.om-selos-soltos img\s*\{([^}]*)\}", css).group(1)
    assert "object-fit: contain" in regra, regra
    # ITEM 28: a fileira VIRA GRADE. Era `nowrap` com rolagem lateral, e medido
    # em 1440 a fileira dos prêmios JÁ rolava (1257 px de conteúdo numa caixa
    # de 1209): a página escondia dois selos de quem nunca pensou em arrastar
    # uma fileira de logos. O pedido agora é o contrário: "cada grupo tem menos
    # largura mas pode ter mais linhas: prefira LER a caber".
    fileira = re.search(r"\.om-selos-soltos\s*\{([^}]*)\}", css).group(1)
    assert "flex-wrap: wrap" in fileira, fileira
    assert "overflow-x" not in fileira, fileira


def test_os_selos_ficam_em_duas_colunas_com_a_divisao_desenhada():
    """ITEM 28: "duas colunas, separando bem cada categoria".

    Certificação ativa e prêmio ganho não são a mesma afirmação, e dois grupos
    empilhados sem nada entre eles leem como uma lista só. A divisão é um fio:
    de pé entre as duas colunas, deitado quando elas empilham, que é a mesma
    divisão na única direção que sobra em tela estreita."""
    css = _css()
    divisor = re.search(r"\.om-selario > div \+ div \{([^}]*)\}", css).group(1)
    assert "border-block-start: 1px solid" in divisor, divisor
    # Dentro do corte de 48em: duas colunas, e o fio deita para ficar de pé.
    # Há mais de um `@media (min-width: 48em)` no arquivo, e olhar o primeiro
    # que aparecer é como o teste da ficha já passou lendo o bloco errado.
    corte = next(b for b in re.findall(
        r"@media \(min-width: 48em\) \{(.*?)\n\}", css, re.S) if ".om-selario" in b)
    assert re.search(r"\.om-selario \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)",
                     corte), "os dois grupos precisam dividir a largura a partir de 48em"
    largo = re.search(r"\.om-selario > div \+ div \{([^}]*)\}", corte, re.S).group(1)
    assert "border-inline-start: 1px solid" in largo, largo
    assert "border-block-start: 0" in largo, largo
    # E a tranca da grade continua no lugar: sem ela um filho que não encolhe
    # empurra a página inteira, que é como esta fileira já estourou 788 px.
    assert re.search(r"\.om-selario > div \{[^}]*min-inline-size: 0", css)


def test_os_selos_sao_monocromaticos_no_rodape_e_coloridos_na_pagina():
    """ITEM 28, e é a metade que precisa dos DOIS lados para estar certa.

    No RODAPÉ os dezesseis selos chegam cada um puxando o olho para uma cor
    diferente, competindo com o índice, o endereço e o telefone, que é o que
    uma pessoa procura ali. Um filtro de cinza resolve, e resolve sem tocar em
    arquivo nenhum: a marca de terceiro continua sendo o arquivo oficial.

    NA PÁGINA DE CERTIFICAÇÕES eles continuam coloridos, porque ali eles são o
    CONTEÚDO. Por isso o seletor pende do rodapé, e não da classe do selo: se
    ele pendesse da classe, a página perderia a cor junto."""
    css = _css()
    cinza = re.search(r"\.om-rodape \.om-selos-soltos img \{([^}]*)\}", css)
    assert cinza, "o filtro precisa pender do rodapé, senão a página perde a cor"
    assert "grayscale(1)" in cinza.group(1), cinza.group(1)
    # E nenhuma regra apaga a cor da fileira grande da página de certificações.
    for regra in re.findall(r"([^{}]*om-selario-grande[^{}]*)\{([^}]*)\}", css):
        assert "grayscale" not in regra[1], regra
    assert 'class="om-selario om-selario-grande' in _html("certificacoes")


def test_nenhuma_certificacao_e_afirmada_sem_o_arquivo_do_selo():
    """O contraponto, e é ele que protege o pitch: uma certificação escrita à
    mão, sem arquivo, é uma afirmação que ninguém pode conferir.

    A GPTW foi exatamente isso durante um ciclo inteiro, e é por isso que este
    teste é escrito ao contrário do óbvio: ele não guarda uma lista de nomes
    proibidos, ele exige que TODO nome de certificação de terceiro que
    apareça em texto ou em `alt` esteja no contrato, e o contrato exige
    arquivo. Assim um selo entra sozinho no dia em que o arquivo dele chegar,
    e nenhum entra sem."""
    com_arquivo = " ".join(nome for _, nome, _, _ in selos.TODOS)
    for pagina in TODAS:
        html = _html(pagina)
        texto = _texto_visivel(pagina) + " " + " ".join(
            re.findall(r'alt="([^"]*)"', html))
        for terceiro in ("GPTW", "Great Place to Work", "ISO 9001", "ISO 27001",
                         "B Corp", "Cannes Lions", "Effie Awards"):
            if terceiro in texto:
                assert terceiro in com_arquivo, (pagina, terceiro)


def test_as_tres_certificacoes_vao_com_icone_de_traco():
    """TAAN, NIG e ESG são as três que o site atual lista num acordeão, e a
    linguagem de ícone é a que ele já usa nessa página: traço fino, marcador,
    lâmpada e bandeira.

    Aqui não há imagem de selo porque não existe selo de "NIG" nem de "ESG":
    são iniciativas da casa, não certificados emitidos por alguém. O ícone é
    honesto; um selo desenhado seria invenção."""
    html = _html("certificacoes")
    for nome in ("TAAN", "NIG", "ESG"):
        assert f"<span class=\"om-selo-nome\">{nome}</span>" in html, nome
    assert html.count('class="om-selo-ic"') == 3


# ==========================================================================
# ITEM 7 e ITEM 10: O RODAPÉ COMPLETO E A FAIXA DE COPYRIGHT
# ==========================================================================

@pytest.mark.parametrize("pagina", TODAS)
def test_o_rodape_traz_as_tres_politicas(pagina):
    """Item 7: "mais política de privacidade, política de cookies e
    acessibilidade". As três são páginas de verdade, com endereço próprio, e
    o rodapé de TODA página leva às três."""
    html = _html(pagina)
    for destino in POLITICAS:
        assert f'href="{BASE}/{destino}"' in html, (pagina, destino)


@pytest.mark.parametrize("pagina", TODAS)
def test_o_rodape_e_categorizado_com_rotulo_em_cada_grupo(pagina):
    """Item 7, e a razão dele: o rodapé anterior tinha uma coluna chamada
    "Contato" com dois telefones e três perfis de rede empilhados sem nada
    dizendo onde uma coisa acabava e a outra começava. Rodapé é índice, e
    índice sem categoria é lista."""
    html = _html(pagina)
    rodape = html[html.index('<footer class="om-rodape">'):]
    # ITEM 23 TROCOU AS CATEGORIAS. "Páginas" virou o nome do cliente,
    # "Telefones" virou "Contato" (porque agora ele traz endereço, telefone e
    # mapa, e não só o número), e os selos passaram a ser DOIS grupos
    # rotulados: prêmio ganho e certificação ativa não são a mesma afirmação.
    for rotulo in ("Grupo OM", "Contato", "Redes sociais", "Certificações", "Prêmios"):
        assert rotulo in rodape, (pagina, rotulo)
    assert rodape.count('class="om-rodape-t"') == 5, pagina
    # Os dois telefones e os QUATRO perfis continuam lá, cada um no seu grupo.
    assert 'href="tel:+554133621919"' in rodape and 'href="tel:+551130442215"' in rodape
    for rede in ("instagram.com/grupo_om", "linkedin.com/company/grupo-om",
                 "facebook.com/Grupo-OM", "youtube.com/channel/"):
        assert rede in rodape, (pagina, rede)


def test_as_tres_politicas_abrem_nas_duas_rotas():
    slug, token, _ = _no_banco(estado="publico")
    with _client() as c:
        for pagina in POLITICAS:
            assert c.get(f"/lab/sites/{slug}/{pagina}").status_code == 200, pagina
            assert c.get(f"/lab/p/{token}/{pagina}").status_code == 200, pagina
    _limpar()


@pytest.mark.parametrize("pagina", TODAS)
def test_a_faixa_de_copyright_do_item_10_substitui_a_marca_de_autoria(pagina):
    """Item 10, verbatim: "igual ao do Lab, mesma marcação e mesmo CSS de
    `.footer-bottom` / `.mono-label`, porém com o texto novo".

    E a garantia da §8 continua cumprida, que é o que este teste realmente
    protege: o texto novo diz quem fez e diz que não é o site oficial, e ainda
    faz a terceira coisa que faltava, que é converter. O `<meta name="author">`
    do `<head>` vive FORA do bloco, e por isso nenhuma sobrescrita consegue
    tirá-lo."""
    html = _html(pagina)
    assert '<div class="footer-bottom">' in html, pagina
    assert '<span class="mono-label">' in html, pagina
    assert "Leandro Furtado" in html, pagina
    assert "Esse não é o site oficial" in html, pagina
    assert "Gostou da proposta?" in html, pagina
    # O botão do item 10, e o único destino externo permitido para ele.
    assert 'href="https://leandrofurtado.com.br/contato"' in html, pagina
    # E a marca de autoria PADRÃO da base saiu destas páginas: duas faixas
    # dizendo a mesma coisa no rodapé é ruído, não garantia. O que continua
    # no `<head>` é só a REGRA de estilo `.rd-autoria`, que a base escreve
    # para os outros redesigns e que nenhuma marcação daqui usa.
    assert '<footer class="rd-autoria">' not in html, pagina


def test_o_css_da_faixa_e_copia_dos_valores_do_lab():
    """A regra do item 10 é COPIAR, nunca reescrever. Os valores abaixo são os
    de `.lab-demo .footer-bottom` e `.lab-demo .mono-label` em
    `app/static/lab/lab-moldura.css`, que por sua vez são os de `main.css`.

    Se alguém "melhorar" um deles aqui, a faixa do Grupo OM deixa de ser a
    mesma faixa do site inteiro, que é exatamente o que a decisão de 20/08
    proibiu."""
    css = _css()
    faixa = re.search(r"\.rd-grupo-om \.footer-bottom\s*\{([^}]*)\}", css).group(1)
    assert "background: #0d0d0d" in faixa
    assert "border-top: 1px solid #242422" in faixa
    assert "color: #8d8b86" in faixa
    rotulo = re.search(r"\.rd-grupo-om \.mono-label\s*\{([^}]*)\}", css).group(1)
    assert "font-size: 10px" in rotulo
    assert "letter-spacing: .16em" in rotulo
    assert "text-transform: uppercase" in rotulo
    assert "font-weight: 600" in rotulo
    # A base continua entregando a marca de autoria para quem NÃO sobrescreve.
    base = (RAIZ / "app/templates/lab/sites/_base_redesign.html").read_text(encoding="utf-8")
    assert "{% block autoria %}" in base
    assert "rd-autoria" in base


# ==========================================================================
# ITEM 4 e ITEM 6: OS ÍCONES E O CORTE DE TEXTO
# ==========================================================================

@pytest.mark.parametrize("pagina", TODAS)
def test_o_sprite_de_icones_entra_uma_vez_e_todo_use_resolve(pagina):
    """Um `<use>` só desenha se o símbolo estiver no MESMO documento. Um
    símbolo faltando não dá erro em lugar nenhum: dá um buraco silencioso onde
    devia haver um ícone, e ninguém percebe até o cliente abrir.

    E o sprite entra UMA vez: declarado em cada parcial que usa ícone, ele se
    repetiria quatro vezes por página, numa peça cujo argumento é o peso."""
    html = _html(pagina)
    assert html.count('class="om-sprite"') == 1, pagina
    sprite = html[html.index('class="om-sprite"'):]
    sprite = sprite[:sprite.index("</svg>")]
    # `<symbol viewBox>` e não `<g>`: com o viewBox no símbolo, cada `<use>`
    # dispensa o dele, e são vinte caracteres a menos em cada um dos setenta
    # ícones de uma página. Numa peça cujo argumento É o peso, isso conta.
    declarados = set(re.findall(r'<symbol id="(om-i-[a-z]+)"', sprite))
    usados = set(re.findall(r'<use href="#(om-i-[a-z]+)"', html))
    assert usados, pagina
    assert usados <= declarados, usados - declarados


def test_os_icones_herdam_a_cor_e_nao_pintam_nada_sozinhos():
    """A identidade é monocromática e a única cor dela é o arco-íris, que tem
    dois lugares. Um ícone com cor própria seria um terceiro, repetido
    quarenta vezes, que é a definição de acento gasto.

    `currentColor` também é o que faz o ícone funcionar no papel, no hover e
    dentro de uma seção clara sem nenhuma segunda regra."""
    css = _css()
    # ÂNCORA NO COMEÇO DA LINHA, e isto é conserto de 26/08: sem o `^`, a
    # primeira coisa que a busca encontrava era qualquer regra DESCENDENTE que
    # terminasse em `.om-ic` (`.om-redes a .om-ic { ... }`), e o teste reprovava
    # a regra base por não estar onde ela nunca esteve.
    base = re.search(r"^\.om-ic\s*\{([^}]*)\}", css, re.M).group(1)
    assert "stroke: currentColor" in base
    assert "fill: none" in base
    assert "stroke-width" in base, "a espessura mora num lugar só"
    for parada in ("#e52a18", "#f0a400", "#f2e200", "#3fa535", "#0e9aa7", "#6b2e8f"):
        assert parada not in base, parada


def test_o_hover_dos_icones_e_desligado_para_quem_pediu_menos_movimento():
    """Hover é movimento por INTERAÇÃO, e o piso da base (duração de transição
    perto de zero) não alcança um `transform` que tem valor final. Ele precisa
    ser zerado no valor, e é."""
    css = _css()
    trecho = css[css.index("@media (prefers-reduced-motion: reduce)"):]
    trecho = trecho[:trecho.index("@media print")]
    assert ".om-ic" in trecho and "transform: none" in trecho


def test_o_corte_de_texto_dos_titulos_tem_folga_medida():
    """ITEM 6. O Leandro mandou a captura de "na ligação." cortado no meio da
    palavra, e a causa é uma só: o `mask: "lines"` do SplitText embrulha cada
    linha numa janela da altura da CAIXA DE LINHA, e as caixas desta peça são
    apertadas de propósito (manchete em .92, título em .98).

    Entrelinha abaixo de 1 quer dizer caixa menor que o corpo da letra: o "g"
    desce para fora dela, o til sobe, e a janela corta os dois.

    O conserto é dar folga à linha, e ele mora em dois arquivos que precisam
    concordar: o JS nomeia a linha (`linesClass`) e o CSS lhe dá o
    `padding-block`. Um sem o outro não conserta nada, e é por isso que este
    teste confere os dois."""
    js = JS.read_text(encoding="utf-8")
    assert 'linesClass: "om-linha"' in js
    css = _css()
    linha = re.search(r"\.om-linha\s*\{([^}]*)\}", css).group(1)
    assert "padding-block" in linha
    # A folga precisa ser devolvida ao fluxo, senão o título cresce de altura e
    # o ritmo vertical da página inteira anda.
    assert "margin-block" in linha


# ==========================================================================
# ITEM 11: AS SEIS ROTAS EM INGLÊS
#
# Elas são irmãs das seis em português, e o que estes testes provam é
# exatamente isso: que NENHUMA regra ficou para trás na cópia. O recorte do
# `pitch`, a peneira contra travessia de diretório, o `noindex` do token e o
# carimbo de `visto_em` valem nas doze, ou não valem em nenhuma.
# ==========================================================================

def test_as_paginas_em_ingles_abrem_nos_dois_enderecos():
    """As seis: home, quatro internas e um case, pelo público e pelo token."""
    slug, token, _ = _no_banco(estado="publico")
    with _client() as c:
        for raiz in (f"/lab/sites/{slug}", f"/lab/p/{token}"):
            assert c.get(f"{raiz}/en").status_code == 200, raiz
            for interna in INTERNAS:
                assert c.get(f"{raiz}/en/{interna}").status_code == 200, (raiz, interna)
            assert c.get(f"{raiz}/en/case/{UM_CASE}").status_code == 200, raiz
    _limpar()


def test_o_endereco_em_ingles_serve_ingles_e_o_sem_prefixo_serve_portugues():
    """O item 11 em uma frase: a língua é o endereço. Dois endereços, dois
    idiomas, e nenhum cookie no meio decidindo por ninguém."""
    slug, _, _ = _no_banco(estado="publico")
    with _client() as c:
        pt = c.get(f"/lab/sites/{slug}").text
        en = c.get(f"/lab/sites/{slug}/en").text
    assert 'lang="pt-BR"' in pt and "Ideias que funcionam" in pt
    assert 'lang="en"' in en and "Ideas that work" in en
    # E o seletor de cada uma aponta para a outra, na mesma página.
    assert f'href="/lab/sites/{slug}/en"' in pt
    assert f'href="/lab/sites/{slug}"' in en
    _limpar()


def test_o_seletor_pelo_token_nunca_escapa_para_o_endereco_publico():
    """A regra mais fácil de quebrar no item 11, e a mais cara: o endereço
    público responde 404 enquanto o redesign é `pitch`. Um seletor de idioma
    que apontasse para `/lab/sites/...` mandaria o cliente, no meio da leitura
    da proposta, para uma página de erro."""
    _, token, _ = _no_banco(estado="pitch")
    with _client() as c:
        pt = c.get(f"/lab/p/{token}").text
        en = c.get(f"/lab/p/{token}/en").text
    assert f'href="/lab/p/{token}/en"' in pt
    assert f'href="/lab/p/{token}"' in en
    # `href="/lab/sites/` e não `/lab/sites/` solto: a folha de estilo mora em
    # `/static/lab/sites/grupo-om.css`, e uma busca por substring reprovaria
    # por causa do CSS, que é exatamente o que não está em jogo aqui.
    assert 'href="/lab/sites/' not in pt and 'href="/lab/sites/' not in en
    _limpar()


def test_o_seletor_pelo_token_mantem_a_pagina_interna():
    """E ele mantém a PÁGINA, não só o endereço: quem está lendo os cases em
    português e troca de idioma espera os cases em inglês."""
    _, token, _ = _no_banco(estado="pitch")
    with _client() as c:
        assert f'href="/lab/p/{token}/en/cases"' in c.get(f"/lab/p/{token}/cases").text
        assert f'href="/lab/p/{token}/cases"' in c.get(f"/lab/p/{token}/en/cases").text
        assert (f'href="/lab/p/{token}/en/case/{UM_CASE}"'
                in c.get(f"/lab/p/{token}/case/{UM_CASE}").text)
        assert (f'href="/lab/p/{token}/case/{UM_CASE}"'
                in c.get(f"/lab/p/{token}/en/case/{UM_CASE}").text)
    _limpar()


def test_as_rotas_em_ingles_respondem_404_no_publico_enquanto_e_pitch():
    """O recorte do `pitch` vale nas doze rotas, ou não vale em nenhuma. Uma
    proposta que ainda não foi mostrada ao cliente não pode ter a versão
    inglesa aberta por um endereço que ninguém pensou em fechar."""
    slug, _, _ = _no_banco(estado="pitch")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}/en").status_code == 404
        assert c.get(f"/lab/sites/{slug}/en/sobre").status_code == 404
        assert c.get(f"/lab/sites/{slug}/en/case/{UM_CASE}").status_code == 404
    _limpar()


@pytest.mark.parametrize("nome", [
    # A lista é a MESMA das rotas em português, e é de propósito: um caso que
    # reprova lá e não é tentado aqui é justamente onde uma segunda porta
    # ficaria sem tranca. `..` e `.` sozinhos ficam de fora porque o cliente
    # HTTP normaliza o caminho antes de sair, e o teste passaria a medir o
    # httpx em vez do servidor.
    "../../../../etc/passwd",
    "..%2f..%2fmain",
    "%2e%2e%2f%2e%2e%2fmain",
    "../_base_redesign",
    "sobre.",
    "sobre.html",
    "SOBRE",
    "_topo",
    "-sobre",
])
def test_as_rotas_em_ingles_recusam_travessia_de_diretorio(nome):
    """Um segundo formato de nome, mais frouxo, seria uma segunda porta para a
    mesma travessia, e a segunda porta é sempre a que fica sem tranca. As
    rotas em inglês passam pelas MESMAS peneiras, e é isso que este teste
    prova: elas chamam `_interna` e `_caso`, e não uma cópia."""
    slug, _, _ = _no_banco(estado="publico")
    with _client() as c:
        assert c.get(f"/lab/sites/{slug}/en/{nome}").status_code == 404, nome
        assert c.get(f"/lab/sites/{slug}/en/case/{nome}").status_code == 404, nome
    _limpar()


def test_a_pagina_em_ingles_pelo_token_e_noindex_e_carimba_visto_em():
    """O `noindex` é propriedade do ENDEREÇO, e o endereço em inglês do token
    é tão secreto quanto o em português. E abrir a proposta em inglês é abrir
    a proposta: o carimbo é o mesmo."""
    _, token, ident = _no_banco(estado="publico")
    with _client() as c:
        r = c.get(f"/lab/p/{token}/en")
    assert r.status_code == 200
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert 'content="noindex, nofollow"' in r.text
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is not None
    _limpar()


def test_a_pagina_em_ingles_vinda_do_loopback_nao_carimba_visto_em():
    """A captura do "depois" roda no Chromium local e bate em 127.0.0.1. Sem
    esta guarda, fotografar a versão inglesa marcaria a proposta como vista
    antes de o Leandro ter mandado o link."""
    _, token, ident = _no_banco(estado="pitch")
    with _client() as c:
        assert c.get(f"/lab/p/{token}/en", headers={"x-forwarded-for": "127.0.0.1"}
                     ).status_code == 200
    with SessionLocal() as db:
        assert db.get(Redesign, ident).visto_em is None
    _limpar()


def test_o_en_do_site_nao_serve_o_redesign_em_portugues():
    """DEFEITO ENCONTRADO EM 26/08, e ele só ficou visível com o item 11.

    O site do Leandro tem um `/en` próprio (`app/main.py::LangMiddleware`) que
    é RETIRADO do caminho antes do roteamento. Sem esta regra,
    `/en/lab/sites/grupo-om` respondia 200 e servia o PORTUGUÊS: um endereço
    que diz "en" e entrega português é pior que um 404, porque promete uma
    tradução que não está ali, e ainda cria uma segunda URL para a mesma
    página.

    Agora ele é 301 para o endereço sem prefixo, do mesmo jeito que o Nodal
    já era. Quem quer inglês usa o endereço que a própria peça publica, que é
    `/lab/sites/<slug>/en`."""
    slug, _, _ = _no_banco(estado="publico")
    with TestClient(app, base_url="https://testserver", follow_redirects=False) as c:
        for caminho in (f"/lab/sites/{slug}", f"/lab/sites/{slug}/en",
                        f"/lab/sites/{slug}/cases"):
            r = c.get("/en" + caminho)
            assert r.status_code == 301, caminho
            assert r.headers["location"] == caminho, caminho
    _limpar()


# ---------------------------------------------------------------------------
# ITEM 12: a varredura de responsividade, medida em 26/08 num Chromium de
# verdade, em 320, 375, 768, 1024, 1440 e 1920, com `overflow-x` DESLIGADO no
# `html` e no `body` para a conferência não ser circular: uma página que corta
# o que estoura passa em qualquer teste de estouro que confie nela.
#
# A varredura achou UM defeito, e ele era o pior possível. Em 320 px as três
# pílulas do canto direito do cabeçalho (telefone, idioma, hambúrguer) somam
# 401 px de conteúdo, e o hambúrguer ia de x=305 a x=419: o botão que abre a
# única navegação disponível naquela largura ficava FORA DA TELA.
#
# Os testes abaixo não remedem larguras, porque teste de suíte não abre
# navegador. Eles travam a CORREÇÃO, que é o que some sem ninguém ver: a regra
# que tira as duas pílulas do cabeçalho estreito, e o menu que continua
# carregando as duas coisas que ela tirou.
# ---------------------------------------------------------------------------


def test_o_cabecalho_cabe_numa_linha_e_o_telefone_virou_menu():
    """ITEM 26, E A REGRA QUE ELE MATOU.

    Existia aqui um `@media (max-width: 47.999em)` que escondia o telefone e o
    idioma do cabeçalho em telas estreitas, porque as três pílulas somavam 401
    px e empurravam o hambúrguer para fora de uma tela de 320. Dois testes
    guardavam essa regra.

    O item 26 resolveu o mesmo problema por outro caminho: a pílula do número
    virou um ÍCONE que abre os dois telefones, e o seletor de idioma virou
    SIGLA. Medido no navegador, os três controles do canto passaram a caber em
    320 px com folga, e a regra virou código morto. Código morto com teste em
    volta é pior que nenhum dos dois, então os dois saíram e este entrou no
    lugar deles, guardando a CAUSA em vez do remendo.

    O que ele trava: a regra não pode voltar por distração, o telefone é um
    `<details>` (dropdown nativo, que funciona sem script), e o seletor é
    sigla."""
    corpo = _css()
    # A regra MORTA era esta, e ela é o que não pode voltar: sumir com o
    # telefone e com o idioma INTEIROS no cabeçalho estreito. O que existe
    # hoje em `max-width: 47.999em` é outra coisa (a dobra do herói, item 16),
    # e é por isso que a busca é pela declaração e não pela media query.
    for morta in (".om-menu-pronto .om-topo-tel", ".om-menu-pronto .om-idioma",
                  ".om-topo-tel"):
        assert morta not in corpo, (
            f"{morta} voltou; a pílula do telefone virou `<details>` no item 26")
    # O telefone é `<details>`: abre, fecha e navega por teclado sem script.
    topo = (PASTA / "_topo.html").read_text(encoding="utf-8")
    assert "<details class=\"om-tel-menu\"" in topo
    assert "tel:+554133621919" in topo and "tel:+551130442215" in topo
    # E cada número vai com o LUGAR dele, que é a pergunta que ficou aberta
    # três ciclos: o (41) é Alphaville, o (11) é São Paulo.
    assert "Alphaville, Pinhais" in topo and "Vila Olímpia, São Paulo" in topo
    # O seletor é sigla (item 15), e não a palavra inteira.
    for palavra in (">English</span>", ">Português</span>"):
        assert palavra not in topo, palavra


def test_o_menu_de_tela_cheia_continua_carregando_os_telefones():
    """O menu de tela cheia é a navegação inteira do celular: se um dia
    alguém tirar os telefones de lá, o celular fica sem telefone, e a página
    continuaria passando em todos os outros testes.

    O SELETOR DE IDIOMA SAIU DAQUI em 27/08, por decisão do Leandro, e a
    garantia não se perdeu: o cabeçalho agora fica POR CIMA do menu aberto, e
    o seletor dele continua visível e clicável enquanto o menu está aberto. O
    que saiu foi a duplicata, e é o teste abaixo que segura isso."""
    menu = (PASTA / "_menu.html").read_text(encoding="utf-8")
    assert "tel:+554133621919" in menu, "o telefone de Curitiba sumiu do menu"
    assert "tel:+551130442215" in menu, "o telefone de São Paulo sumiu do menu"


def test_o_idioma_continua_alcancavel_com_o_menu_aberto():
    """A contrapartida de ter tirado o seletor de dentro do menu.

    Ele só pode sair de lá porque o cabeçalho sobe acima do painel quando o
    menu abre. Se alguém desfizer esse `z-index`, o seletor passa a ficar
    ATRÁS do menu e o celular fica sem inglês, sem que nada mais quebre."""
    css = _css()
    assert re.search(r"\.om-travado \.om-cabecalho\s*\{[^}]*z-index:\s*70", css), \
        "o cabeçalho precisa subir acima do menu, senão o idioma fica atrás dele"
    topo = (PASTA / "_topo.html").read_text(encoding="utf-8")
    assert "om-idioma" in topo, "o seletor de idioma sumiu do cabeçalho"


def test_o_cabecalho_e_o_rodape_tem_a_mesma_largura(pagina="home"):
    """ITENS 15 e 21, e eles são o mesmo item dito duas vezes: se o cabeçalho
    encosta nas bordas e o rodapé não, a página parece dois projetos.

    `om-largo` é a classe dos dois, e ela é o OPOSTO de `om-wrap`: o miolo de
    leitura continua preso em 82rem, porque linha de texto larga demais é
    linha que ninguém termina."""
    css = _css()
    largo = re.search(r"\.om-largo\s*\{([^}]*)\}", css).group(1)
    assert "max-inline-size: none" in largo, largo
    assert "padding-inline: var(--pad-i)" in largo, largo
    miolo = re.search(r"\.om-wrap\s*\{([^}]*)\}", css).group(1)
    assert "max-inline-size: 82rem" in miolo, miolo
    for p in TODAS:
        html = _html(p)
        cabeca = html[html.index("<header"):html.index("</header>")]
        rodape = html[html.index('<footer class="om-rodape">'):]
        assert 'class="om-largo om-topo"' in cabeca, p
        assert 'class="om-largo"' in rodape, p


def test_o_voltar_ao_topo_aparece_depois_da_primeira_dobra(pagina="home"):
    """ITEM 26. Ele nasce `hidden` e o script o mostra depois da primeira
    dobra: antes dela ele não teria o que fazer, e um controle que não faz nada
    é pior que nenhum.

    O limiar é a ALTURA DA JANELA, e não um número redondo de pixels: "depois
    da primeira dobra" quer dizer "depois do que coube na tela desta pessoa", e
    isso muda entre um celular e um monitor."""
    for p in TODAS:
        marca = re.search(r'<a class="om-ao-topo"[^>]*>', _html(p)).group(0)
        assert "hidden" in marca, (p, marca)
        assert 'href="#om-topo"' in marca, (p, marca)
    js = JS.read_text(encoding="utf-8")
    assert "data-ao-topo" in js
    assert "window.innerHeight" in js
    # E o destino existe: o cabeçalho tem o id para onde o link aponta.
    assert 'id="om-topo"' in _html("home")


# Os controles que precisam do piso de 44 px. A lista é fechada de propósito:
# um controle novo que não apareça aqui é um controle que ninguém mediu.
CONTROLES_COM_PISO = (
    ".om-tel-abre", ".om-tel-lista a", ".om-menu-paginas > ul a", ".om-menu-mini a", ".om-ao-topo", ".om-idioma",
    ".om-hamburguer",
    ".om-f-abre", ".rd-grupo-om .om-f-op", ".om-filtro-busca", ".om-busca",
    ".om-trilha a", ".om-partilha-redes a", ".om-onde a",
    ".om-rodape-nav a, .om-redes a", ".om-legal-nav a",
    ".rd-grupo-om .om-autoria-btn", ".om-nav a",
)


def test_o_piso_de_alvo_de_toque_mora_num_lugar_so():
    """VINTE contas à mão, e seis delas erradas. Esta é a lição da rodada.

    A folha calculava a altura de cada controle somando corpo, entrelinha,
    borda e ícone, e escrevia "44 px medidos" ao lado. Quando o navegador foi
    perguntado, seis mediam 37, 39, 41, 41,6, 43,6 e 43,8: o seletor de
    idioma, a pílula de telefone, o botão do rodapé, a opção de filtro, o
    resumo do filtro e o link da página atual.

    A conta some. O piso é um `min-block-size` que não depende de nenhuma das
    quatro variáveis, e o `padding` volta a fazer só o que sabe fazer, que é
    dar folga horizontal."""
    css = CSS.read_text(encoding="utf-8")
    assert re.search(r"--alvo:\s*2\.75rem", css), "o token do piso sumiu"


@pytest.mark.parametrize("seletor", CONTROLES_COM_PISO)
def test_todo_controle_declara_o_piso_em_vez_de_calcular(seletor):
    """Nenhum controle volta a estimar a própria altura."""
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    # TODAS as regras do seletor, e não a primeira: vários controles têm uma
    # regra base e uma de ajuste depois, e procurar só a primeira encontrava a
    # de ajuste e reprovava um controle que está correto.
    corpos = [m.group(1) for m in
              re.finditer(re.escape(seletor) + r"\s*\{([^}]*)\}", css)]
    assert corpos, f"{seletor} sumiu da folha"
    assert any("min-block-size: var(--alvo)" in c for c in corpos), (
        f"{seletor} voltou a depender de conta de padding: {corpos!r}")


def test_a_marca_e_um_alvo_de_toque_e_nao_so_uma_imagem():
    """A imagem da marca tem 12 px de altura em 320 px de tela. O link em
    volta dela precisa dos 44, e ganha por padding com margem negativa do
    mesmo tamanho, que cresce o alvo sem mover o layout."""
    css = CSS.read_text(encoding="utf-8")
    achado = re.search(
        r"\.om-marca \{[^}]*padding-block: ([\d.]+)rem;[^}]*margin-block: -([\d.]+)rem", css)
    assert achado, "o alvo de toque da marca sumiu"
    assert float(achado.group(1)) >= 1.0
    assert achado.group(1) == achado.group(2), (
        "a margem negativa precisa ter o tamanho exato do padding, senão o "
        "cabeçalho engorda")


# ==========================================================================
# ITEM 17: OS SEIS CARTÕES, O SITE DE CADA EMPRESA E A COR DE CADA UMA
#
# É o item que mais perto chega da regra que já custou um ciclo, e por isso
# ele tem três testes e não um: o cartão precisa levar ao site CERTO, a cor
# precisa ser a que o cliente declara, e ela não pode aparecer em lugar
# nenhum além do hover do cartão daquela empresa.
# ==========================================================================

# O contrato das seis, colhido do `data-color` e do `data-contrast` do site do
# cliente e conferido em `grupoom-material-2.md`.
CORES_DAS_EMPRESAS = {
    "opus-multipla": ("#da0812", "#ffffff", "https://opusmultipla.com.br/"),
    "dom": ("#00274f", "#ffffff", "https://dom-solucoes.com/"),
    "senso": ("#009a93", "#ffffff", "https://sensoperformance.com.br/"),
    "brain-box": ("#fecc00", "#000000", "https://brainboxdesign.com.br/"),
    "house-cricket": ("#b9ba21", "#000000", "https://housecricket.com.br/"),
    "tailor-media": ("#283772", "#ffffff", "https://tailormedia.com.br/"),
}


def test_os_seis_cartoes_levam_ao_site_da_empresa_certa():
    """Item 17: o cartão inteiro virou link para o site da empresa, em nova
    aba. Um cartão que leva ao site da vizinha é o pior erro possível numa
    peça que vai para o dono do grupo, e é um erro que ninguém nota lendo o
    HTML: os seis logos são parecidos em miniatura."""
    for pagina in ("home", "sobre"):
        html = _html(pagina)
        cartoes = re.findall(
            r'<li class="om-marca-cartao om-e-([a-z-]+)">\s*<a[^>]*href="([^"]+)"[^>]*>\s*'
            r'<img[^>]*src="/static/lab/sites/grupo-om/([^"]+)"[^>]*alt="([^"]*)"',
            html, re.S)
        assert len(cartoes) == 6, (pagina, len(cartoes))
        for chave, destino, arquivo, alt in cartoes:
            assert chave in CORES_DAS_EMPRESAS, chave
            assert destino == CORES_DAS_EMPRESAS[chave][2], (chave, destino)
            assert arquivo in EMPRESAS_DO_GRUPO, arquivo
            assert alt == EMPRESAS_DO_GRUPO[arquivo], (arquivo, alt)
        # Nova aba, e `noopener` junto: sem ele a página de destino ganha
        # `window.opener` e pode reescrever o endereço desta.
        for bloco in re.findall(r'<a class="om-marca-elo"[^>]*>', html):
            assert 'target="_blank"' in bloco and 'rel="noopener"' in bloco, bloco


def test_a_cor_de_cada_empresa_e_a_que_o_cliente_declara():
    """As seis cores e as seis cores de contraste saem do HTML do próprio
    site do cliente. Uma cor "parecida" escolhida a olho é a mesma doença do
    laranja inventado, com seis chances de acontecer em vez de uma.

    `--inverte` é o `data-contrast` virado número: o logo é preto no arquivo,
    e sobre o amarelo da Brain Box inverter para branco apagaria a marca
    dela."""
    css = _css().lower()
    for chave, (cor, contraste, _) in CORES_DAS_EMPRESAS.items():
        regra = re.search(r"\.om-e-" + chave + r"\s*\{([^}]*)\}", css)
        assert regra, chave
        corpo = regra.group(1)
        assert f"--cor-empresa: {cor}" in corpo, (chave, corpo)
        assert f"--cor-contraste: {contraste}" in corpo, (chave, corpo)
        esperado = "0" if contraste == "#000000" else "1"
        assert f"--inverte: {esperado}" in corpo, (chave, corpo)


def test_nenhuma_das_seis_cores_vaza_para_fora_do_cartao_da_empresa():
    """A REGRA QUE JÁ CUSTOU UM CICLO, virada em teste.

    As seis cores são a identidade de cada EMPRESA. O Grupo OM é
    monocromático, e o arco-íris (que é outra coisa ainda) nunca toca a marca.
    Este teste garante as duas metades disso:

    1. Cada cor aparece no CSS SÓ dentro da regra `.om-e-<empresa>`, que é o
       cartão daquela empresa. Uma delas num `color:`, num `background` de
       seção ou num `border` de botão reprova aqui.
    2. Nenhuma delas aparece em HTML nenhum, em página nenhuma: um
       `style="--cor: #da0812"` num cartão seria a paleta do cliente
       espalhada por seis linhas de template, e o teste de medida solta não
       pegaria a cor, só o `style`.
    """
    css = _css().lower()
    # As linhas que DECLARAM a cor de uma empresa. Todo o resto do arquivo não
    # pode conter nenhuma das seis.
    resto = re.sub(r"\.om-e-[a-z-]+\s*\{[^}]*\}", "", css)
    for chave, (cor, contraste, _) in CORES_DAS_EMPRESAS.items():
        assert cor not in resto, (chave, cor, "a cor da empresa vazou do cartão dela")
    for pagina in TODAS:
        html = _html(pagina).lower()
        for chave, (cor, _, _) in CORES_DAS_EMPRESAS.items():
            assert cor not in html, (pagina, chave, cor)
    # E o hover mora atrás de `(hover: hover)`: no celular o estado gruda
    # depois do toque, e o cartão ficaria colorido até a pessoa tocar noutro
    # lugar, o que parece defeito.
    # Há mais de um bloco `(hover: hover)` no arquivo, e o do cartão não é o
    # primeiro: a busca é em TODOS eles.
    hover = "\n".join(re.findall(r"@media \(hover: hover\)[^{]*\{(.*?)\n\}", css, re.S))
    assert ".om-marca-cartao:hover::before" in hover
    assert "var(--cor-empresa)" in hover


# ==========================================================================
# ITENS 19 e 27: OS DEZOITO CASES REAIS
# ==========================================================================

def _do_json():
    """Os dezoito cases como o cliente os publica, lidos do material colhido.

    O teste NÃO confia no módulo Python para conferir o módulo Python: ele
    abre o `grupoom-cases.json`, que é o que eu colhi do site do cliente. É a
    única forma de "nada é inventado" virar uma regra que a máquina confere.

    O arquivo mora em `app/lab/dados/`, VERSIONADO, e não no diretório de
    trabalho da tarefa. Enquanto ele viveu lá, que é ignorado pelo git, este
    teste passava na máquina de quem colheu e quebrava em qualquer checkout
    limpo: a fusão para a `main` reprovou exatamente aqui.
    """
    import json
    caminho = RAIZ / "app/lab/dados/grupoom-cases.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def test_nenhum_case_tem_data_ou_categoria_que_nao_esteja_no_material():
    """Data e categoria são as duas afirmações mais fáceis de inventar num
    cartão de case, e as duas que o dono da agência confere primeiro: ele sabe
    de cor quando cada campanha foi ao ar.

    As CINCO categorias vazias ficam vazias. O site do cliente não declara
    categoria para esses cases, e escolher uma "que combina" seria classificar
    o trabalho de outra empresa no lugar dela."""
    do_json = _do_json()
    datas = {c["data"] for c in do_json}
    categorias = {(c.get("categoria") or "").lower() for c in do_json}
    # O material tem dezoito. A peça mostra dezoito MENOS os que saíram por
    # decisão escrita, e a conta é feita aqui em vez de digitada. Os slugs do
    # cliente são outros (quatro deles começam por número), então quem faz a
    # ponte é o nosso próprio slug, e o teste do disco confere o resto.
    assert len(om.CASES) == len(do_json) - len(CASES_REMOVIDOS)
    for slug in CASES_REMOVIDOS:
        assert slug not in om.POR_SLUG, slug
    for c in om.CASES:
        assert c["data"] in datas, (c["slug"], c["data"])
        # O ISO é derivado da data, e o teste refaz a conta ao contrário.
        dia, mes, ano = c["data"].split("/")
        assert c["iso"] == f"{ano}-{mes}-{dia}", (c["slug"], c["iso"])
        if c["categoria"] is None:
            continue
        nome = om.NOME_DA_CATEGORIA[c["categoria"]].lower()
        assert nome in categorias, (c["slug"], nome)
    # E as cinco sem categoria são as cinco que o cliente publica sem ela.
    fora = set(CASES_REMOVIDOS)
    sem = sum(1 for c in do_json
              if not c.get("categoria") and c["slug"] not in fora)
    assert sum(1 for c in om.CASES if c["categoria"] is None) == sem == 5


def test_toda_imagem_de_case_e_arquivo_local_baixado():
    """GLOBAL CONSTRAINT 11, e a contradição que ela evita.

    As dezoito imagens vivem no servidor do cliente, em JPEG e PNG de 1920 px
    que somam megabytes. Puxá-las de lá seria a peça carregando host externo
    na mesma página em que acusa o site do cliente de peso, e ainda deixaria a
    proposta quebrada no dia em que o cliente mexesse no WordPress dele.

    Aqui elas são webp de 960x540, baixadas e servidas de `/static/`. O teste
    confere as três coisas: o caminho é local, o arquivo existe, e é webp."""
    for c in om.CASES:
        assert c["imagem"].startswith("/static/lab/sites/grupo-om/cases/"), c["slug"]
        assert c["imagem"].endswith(".webp"), c["slug"]
        arquivo = RAIZ / "app" / c["imagem"].lstrip("/")
        assert arquivo.is_file(), c["imagem"]
        assert arquivo.stat().st_size < 60_000, (c["slug"], arquivo.stat().st_size)
    # E nenhuma página CARREGA nada do servidor do cliente.
    #
    # A verificação passou a olhar o que a página BAIXA (`src`, `srcset`,
    # `href` de folha e de fonte), e não qualquer menção ao domínio. O que
    # esta regra protege é PESO e dependência: uma imagem hospedada lá torna
    # a proposta refém do WordPress do cliente e contradiz o diagnóstico que
    # a própria peça faz. Um `href` de navegação não baixa nada.
    #
    # A distinção virou necessária em 27/08, quando o menu ganhou o link do
    # Instituto J.D. Rodrigues, que é uma página do site atual do cliente e a
    # única saída da peça para lá.
    for pagina in TODAS:
        html = _html(pagina)
        baixados = re.findall(r'(?:src|srcset)="([^"]+)"', html)
        baixados += re.findall(r'<link[^>]+href="([^"]+)"', html)
        for endereco in baixados:
            assert "grupoom.com.br" not in endereco, (pagina, endereco)


def test_o_cartao_de_case_traz_os_cinco_elementos_do_item_19():
    """Imagem, logo de quem assina, data, etiquetas e CTA. Sem exceção: um
    cartão a menos numa grade cheia é o cartão que parece quebrado.

    27/08: as etiquetas viraram TRÊS por case, sempre, vindas de `ETIQUETAS`
    (a categoria de filtro é outra coisa e continua vindo do HTML do
    cliente). E o corte por `</li>` virou corte pela ABERTURA do próximo
    cartão: as etiquetas são `<li>` dentro do cartão, e o regex antigo parava
    no primeiro deles, medindo um terço de cada cartão sem avisar."""
    html = _html("cases")
    cartoes = html.split('<li class="om-cartao om-rv">')[1:]
    assert len(cartoes) == len(om.CASES), len(cartoes)
    for bloco in cartoes:
        assert "om-cartao-arte" in bloco and "<img" in bloco
        assert "om-assinatura-grande" in bloco, "o logo de quem assina sumiu"
        assert re.search(r'<time class="om-cartao-data" datetime="\d{4}-\d{2}-\d{2}">', bloco)
        assert "om-case-ver" in bloco, "o CTA sumiu"
        etiquetas = re.search(r'<ul class="om-etiquetas">(.*?)</ul>', bloco, re.S)
        assert etiquetas, "as etiquetas sumiram"
        assert etiquetas.group(1).count("<li>") == 3, etiquetas.group(1)
        # A ORDEM é a do pedido: etiquetas ANTES do CTA, e o CTA fora da
        # âncora (o clique é do elo esticado).
        assert bloco.index("om-etiquetas") > bloco.index("</a>")
        assert bloco.index("om-case-ver") > bloco.index("om-etiquetas")
    # O fato de dados continua o mesmo: cinco cases sem categoria de filtro.
    assert sum(1 for c in om.CASES if not c["categoria"]) == 5


def test_o_numeral_e_o_nome_repetido_sairam_do_cartao_do_case():
    """ITEM 18, verbatim: a captura mostrava `01 [logo GRUPO OM] GRUPO OM
    Ninfa Ninfa`. Quatro elementos para dizer duas coisas."""
    for pagina in ("home", "cases"):
        html = _html(pagina)
        for bloco in re.findall(r'<li class="om-cartao om-rv">(.*?)</li>', html, re.S):
            # O numeral era um elemento SÓ com `01`, `02`, `03` dentro. A
            # busca é por isso, e não por "dois dígitos no texto": "80.000 KM"
            # e "80 dias" são o título e o texto reais de um dos cases.
            assert not re.search(r">\s*\d{2}\s*<", bloco), bloco[:200]
            # O nome da empresa não é escrito em TEXTO ao lado da logo: ele
            # vive no `alt` dela, que é onde o leitor de tela precisa dele e o
            # olho não. A checagem é na LINHA DE CIMA do cartão, que é onde
            # ficava a repetição: o nome da empresa dentro do texto do case é
            # outra coisa, é a copy que a própria agência escreveu.
            cima = re.search(r'<span class="om-cartao-cima">(.*?)</span>\s*<h3',
                             bloco, re.S).group(1)
            visivel = re.sub(r"<[^>]+>", " ", cima)
            for nome in list(EMPRESAS_DO_GRUPO.values()) + ["Grupo OM"]:
                assert nome not in visivel, (pagina, nome)


def test_as_etiquetas_de_assunto_nao_sao_clicaveis():
    """Item 19, e ele é explícito: as etiquetas NÃO são clicáveis. Quem quer
    recortar por assunto tem os chips do filtro, que são links de verdade.

    Uma etiqueta dentro do `<a>` do cartão seria clicável mesmo sem `href`
    próprio, e levaria ao case: um controle que parece filtro e navega para
    outro lugar é pior do que nenhum."""
    html = _html("cases")
    for bloco in re.findall(r'<ul class="om-etiquetas">(.*?)</ul>', html, re.S):
        assert "<a " not in bloco and "href=" not in bloco, bloco
    # E a etiqueta vem DEPOIS do fechamento da âncora, nunca dentro dela.
    for cartao in re.findall(r'<li class="om-cartao om-rv">(.*?)</li>', html, re.S):
        if "om-etiquetas" not in cartao:
            continue
        assert cartao.index("</a>") < cartao.index("om-etiquetas"), cartao[:200]
    css = _css()
    regra = re.search(r"\.om-etiquetas li[^{]*\{([^}]*)\}", css).group(1)
    assert "cursor" not in regra, regra


def test_todo_case_tem_a_mesma_medida_de_texto_no_cartao():
    """Item 19, verbatim: "a mesma quantidade de texto em todos". Um cartão de
    quatro linhas ao lado de um de uma linha é o que faz uma grade parecer
    rascunho.

    A faixa é estreita de propósito. Os primeiros parágrafos reais dos dezoito
    cases vão de 41 a 400 caracteres, e é por isso que o `resumo` é um campo
    escrito e não "o primeiro parágrafo"."""
    medidas = [len(c["resumo"]) for c in om.CASES]
    assert min(medidas) >= 125, min(medidas)
    assert max(medidas) <= 175, max(medidas)
    # E o mesmo vale para o inglês, que é onde a medida costuma escapar.
    en = [len(EN[c["resumo"]]) for c in om.CASES]
    assert min(en) >= 110 and max(en) <= 200, (min(en), max(en))


def test_o_filtro_recusa_valor_fora_da_lista_fechada():
    """Parâmetro de URL é entrada de fora como qualquer outra, e leva a mesma
    peneira que `{pagina}` e `{case}`: fora da lista fechada é 404, nas duas
    línguas e nos dois endereços.

    E é 404 em vez de "ignora e mostra tudo" porque ignorar em silêncio serve
    uma página cujo endereço promete um recorte que ela não fez."""
    from app.lab import protecao

    slug, token, _ = _no_banco(estado="publico")
    ruins = ("xxx", "../../etc/passwd", "..%2f..%2fmain", "SENSO", "senso;drop",
             "design")  # `design` é CATEGORIA, e nunca empresa
    with _client() as c:
        for valor in ruins:
            protecao._requisicoes.clear()
            assert c.get(f"/lab/sites/{slug}/cases?empresa={valor}").status_code == 404, valor
            assert c.get(f"/lab/p/{token}/en/cases?empresa={valor}").status_code == 404, valor
        for valor in ("xxx", "../../etc/passwd", "senso"):  # `senso` é EMPRESA
            protecao._requisicoes.clear()
            assert c.get(f"/lab/sites/{slug}/cases?categoria={valor}").status_code == 404, valor
        # E o que ESTÁ na lista fechada continua abrindo, com o recorte feito.
        for valor in ("senso", "dom", "grupo-om"):
            protecao._requisicoes.clear()
            r = c.get(f"/lab/sites/{slug}/cases?empresa={valor}")
            assert r.status_code == 200, valor
            assert r.text.count('class="om-cartao om-rv"') == len(om.filtrar(empresa=valor))
    _limpar()


def test_a_grade_de_cases_nasce_completa_e_o_filtro_nao_depende_de_script():
    """Item 27, e a escolha entre os dois caminhos que ele admite.

    EMPRESA e ASSUNTO são link com parâmetro resolvido no servidor: sem
    `<form>` (Global Constraint 4) e sem script. A BUSCA por texto é a única
    coisa que depende de JavaScript, e por isso ela nasce `hidden`: uma caixa
    de busca sem formulário e sem script é um campo que não faz nada.

    A grade já vem completa do servidor, e é isso que faz a página inteira
    continuar legível com o script fora do ar."""
    html = _html("cases")
    assert "<form" not in html.lower()
    assert html.count('class="om-cartao om-rv"') == len(om.CASES)
    campo = re.search(r'<div class="om-filtro-busca"[^>]*>', html).group(0)
    assert "hidden" in campo, campo
    # Em 26/08 os onze chips viraram DOIS MENUS numa linha só, a pedido do
    # Leandro. O que este teste protege não mudou: cada opção continua sendo
    # um `<a href>` e o servidor continua sendo quem recorta. Se um dia
    # alguém trocar o `<details>` nativo por um menu de script, isto quebra,
    # que é exatamente o ponto.
    assert html.count("<details class=\"om-menu-f\"") == 2
    opcoes = re.findall(r'<a class="om-f-op[^"]*"\s+href="([^"]+)"', html)
    assert len(opcoes) == 2 + len(om.EMPRESAS_COM_CASE) + len(om.CATEGORIAS_COM_CASE)
    for destino in opcoes:
        assert destino.startswith(f"{BASE}/cases"), destino
    js = JS.read_text(encoding="utf-8")
    assert "data-busca-campo" in js and ".om-grade-cases > .om-cartao" in js


def test_a_pagina_do_case_segue_o_formato_do_site_do_cliente():
    """Item 27: migalha de pão, logo de quem assina, a palavra CASES com a
    categoria ao lado, a data, o `<h1>`, a arte, o texto, a ficha técnica e o
    botão de voltar. A ordem é a do cliente, e é ela que faz a peça parecer o
    site dele em vez de um blog qualquer."""
    for pagina in CASES:
        html = _html(pagina)
        miolo = html[html.index("<main>"):html.index("</main>")]
        ordem = ["om-trilha", "om-case-linha", "<h1", "om-case-arte",
                 "om-ficha", "om-partilha", "om-btn-vazio"]
        posicoes = [miolo.index(marca) for marca in ordem]
        assert posicoes == sorted(posicoes), (pagina, ordem)
        # A volta para a listagem aparece DUAS vezes de propósito: na migalha
        # de pão, no alto, e no botão do fim. Quem chegou por um link direto
        # precisa das duas, e quem terminou de ler precisa da segunda.
        assert miolo.count(f'href="{BASE}/cases"') == 2, pagina
        # E NENHUM `iframe`: o vídeo do cliente é um embed do YouTube, que é
        # host externo de script e de rastreamento.
        assert "<iframe" not in html, pagina


# ==========================================================================
# ITENS 22 a 25: O RODAPÉ
# ==========================================================================

@pytest.mark.parametrize("pagina", TODAS)
def test_os_dois_enderecos_vao_com_estado_lugar_mapa_e_o_telefone_deles(pagina):
    """ITEM 22, e ele fecha uma pergunta que ficou aberta desde o ciclo 3.

    O site do cliente rotula o primeiro endereço como "Alphaville", sem cidade
    e sem estado, e publica os dois telefones numa lista à parte. Os links de
    mapa que ele mesmo publica resolvem as duas coisas: Alphaville é Pinhais,
    PR, e o outro é Vila Olímpia, São Paulo, SP. E o (41) é de um, o (11) é do
    outro.

    Por isso o teste é sobre PAREAMENTO e não sobre presença: os dois números
    já estavam na página antes, cada um numa coluna, e a pessoa tinha que
    adivinhar para qual escritório estava ligando."""
    html = _html(pagina)
    rodape = html[html.index('<footer class="om-rodape">'):]
    blocos = re.findall(r"<address class=\"om-onde\">(.*?)</address>", rodape, re.S)
    assert len(blocos) == 2, (pagina, len(blocos))

    parana, paulo = blocos
    assert "Alphaville, Pinhais - PR" in parana, parana
    assert "Rua Jaguariaíva, 596" in parana, parana
    assert "tel:+554133621919" in parana, "o (41) é Alphaville"
    assert "tel:+551130442215" not in parana, "o (11) não é Alphaville"
    assert "google.com.br/maps/place/Rua+Jaguaria" in parana, "o mapa de Alphaville"

    assert "Vila Olímpia, São Paulo - SP" in paulo, paulo
    assert "Rua Cardoso de Melo, 1750" in paulo, paulo
    assert "tel:+551130442215" in paulo, "o (11) é São Paulo"
    assert "tel:+554133621919" not in paulo, "o (41) não é São Paulo"
    assert "google.com.br/maps/place/Av.+Dr.+Cardoso" in paulo, "o mapa de São Paulo"

    # Os dois abrem em nova aba: um mapa não pode substituir a proposta que a
    # pessoa está lendo.
    for elo in re.findall(r'<a href="https://www\.google[^>]*>', rodape):
        assert 'target="_blank"' in elo and 'rel="noopener"' in elo, elo


@pytest.mark.parametrize("pagina", TODAS)
def test_as_politicas_ficam_centralizadas_e_menores(pagina):
    """ITEM 24, revisto em 27/08: o pé do rodapé virou a GRADE DO MENU — o
    texto legal à esquerda com as políticas logo abaixo, e a assinatura no
    canto direito. "Centralizadas" saiu do pedido; "menores" ficou, e é o que
    tira as políticas da disputa com o índice do site."""
    html = _html(pagina)
    rodape = html[html.index('<footer class="om-rodape">'):]
    assert 'class="om-rodape-legal"' in rodape, pagina
    # A ordem pedida: legal, políticas, assinatura.
    assert rodape.index("om-rodape-juridico") < rodape.index("om-legal-nav") \
        < rodape.index("om-rodape-agua"), pagina
    for destino in POLITICAS:
        assert f'href="{BASE}/{destino}"' in rodape, (pagina, destino)
    css = _css()
    grade = re.search(r"\.om-rodape-legal\s*\{[^}]*\}\s*", css)
    areas = re.search(r'grid-template-areas: "legal agua" "politicas agua";', css)
    assert areas, "a grade do pé do rodapé perdeu as áreas do menu"
    # TODAS as regras do seletor, e não a primeira: a atribuição de área da
    # grade vem antes da regra de alinhamento no arquivo.
    regras = " ".join(re.findall(
        r"\.om-rodape-legal \.om-legal-nav\s*\{([^}]*)\}", css))
    assert "justify-content: flex-start" in regras, regras
    menor = re.search(r"\.om-rodape-legal \.om-legal-nav a\s*\{([^}]*)\}", css)
    assert menor and "font-size: .72rem" in menor.group(1), menor
    # E o degrau é para BAIXO: 0.72rem contra os 0.875rem do kicker, que é a
    # régua fixa da peça. O menor é 82% do maior, e é essa diferença que tira
    # as políticas da disputa com o índice.
    kicker = float(re.search(r"--t-kicker:\s*([\d.]+)rem", css).group(1))
    assert 0.72 < kicker, (0.72, kicker)


@pytest.mark.parametrize("pagina", TODAS)
def test_o_copyright_fecha_numa_linha_de_largura_maxima(pagina):
    """ITEM 25. O texto continua o do item 10, e os valores de cor e
    tipografia continuam sendo CÓPIA do Lab (o item 10 mandou copiar, nunca
    reescrever). O que mudou é só o arranjo, e ele mora numa segunda regra
    justamente para a cópia continuar sendo cópia.

    Abaixo de 48em ele continua empilhado e centrado: nessa largura "uma
    linha" seria uma linha de duas palavras."""
    assert '<div class="footer-bottom">' in _html(pagina), pagina
    css = _css()
    # A busca varre TODOS os blocos de 48em: o arquivo tem mais de um desde
    # que o item 16 passou a declarar a altura medida do cabeçalho por faixa.
    faixa = None
    for bloco in re.findall(r"@media \(min-width: 48em\)[^{]*\{(.*?)\n\}", css, re.S):
        faixa = faixa or re.search(r"\.rd-grupo-om \.footer-bottom\s*\{([^}]*)\}", bloco)
    assert faixa, "a faixa não vira uma linha em largura nenhuma"
    assert "flex-wrap: nowrap" in faixa.group(1), faixa.group(1)
    assert "justify-content: space-between" in faixa.group(1), faixa.group(1)


# ==========================================================================
# ITEM 16: O CORTE DE TEXTO NA DOBRA
#
# Estes testes não medem pixel, porque teste de suíte não abre navegador. Eles
# travam o MECANISMO, que é o que some sem ninguém ver; os pixels foram
# medidos num Chrome de verdade e a tabela está no relatório do ciclo 6.
# ==========================================================================

def test_o_heroi_ocupa_a_dobra_e_a_altura_do_cabecalho_e_medida():
    """A primeira metade do item 16: o herói mede exatamente o que sobra da
    tela abaixo do cabeçalho, e o bloco seguinte começa depois dele.

    `svh` e não `vh`, e a diferença não é preciosismo: no celular, `vh` conta a
    tela com a barra do navegador RECOLHIDA, e o herói nasceria mais alto que a
    dobra que a pessoa realmente vê, que é o defeito que o item veio
    consertar.

    `--alt-cab` tem TRÊS valores porque o cabeçalho tem três alturas medidas
    (113, 91 e 106 px). Um valor só seria um arredondamento, e um
    arredondamento aqui é exatamente o que faz um bloco aparecer pela metade.

    A CONTA MUDOU DE FORMA em 27/08, e não de resultado. Ela era
    `min-block-size: calc(100svh - var(--alt-cab))`, com a seção começando
    abaixo do cabeçalho. Agora a seção SOBE por trás dele, por margem negativa
    de `--alt-cab`, mede `100svh` e devolve a altura do cabeçalho como folga
    de topo. A área útil abaixo da marca continua sendo `100svh` menos o
    cabeçalho, exatamente como antes.

    A mudança veio de um pedido de aparência ("o fundo da header tem que ser o
    da hero") e é justamente por isso que o teste continua olhando as TRÊS
    peças da conta: quem mexer numa delas por motivo estético precisa mexer
    nas três, ou a dobra volta a cortar um parágrafo pela metade."""
    css = _css()
    capa = re.search(r"\.om-capa\s*\{([^}]*)\}", css).group(1)
    assert "margin-block-start: calc(-1 * var(--alt-cab))" in capa, capa
    assert "min-block-size: 100svh" in capa, capa
    assert "padding-block: calc(var(--alt-cab)" in capa, capa
    assert "justify-content: center" in capa, capa
    alturas = re.findall(r"--alt-cab:\s*(\d+)px", css)
    assert len(alturas) == 3, alturas
    assert alturas == ["113", "91", "106"], alturas


def test_a_escala_do_heroi_e_limitada_pela_altura_da_janela():
    """A segunda metade, e sem ela a primeira só troca um corte por outro: em
    1024x768 a manchete media 433 px sozinha, e nada mais caberia na dobra.

    Por isso a escala do HERÓI (e só a dele) é limitada também pela ALTURA da
    janela. Numa tela larga e baixa quem manda é a altura; numa alta e estreita,
    a largura. É o que `min(vw, vh)` faz numa linha."""
    css = _css()
    manchete = re.search(r"\.om-capa \.om-manchete\s*\{([^}]*)\}", css).group(1)
    assert "min(9.4vw, 9vh)" in manchete, manchete
    declaracao = re.search(r"\.om-capa \.om-declaracao\s*\{([^}]*)\}", css).group(1)
    assert "vh" in declaracao, declaracao
    # E a régua GERAL não muda: o teto de manchete da peça continua o mesmo, e
    # o que foi limitado é só o herói.
    geral = re.search(r"--t-manchete:\s*([^;]+);", css).group(1)
    assert "vh" not in geral, geral


def test_a_dobra_estreita_cai_no_fio_e_nunca_no_meio_do_paragrafo():
    """A saída para a tela estreita, e o documento admite as duas.

    Em 320x568 sobram 455 px abaixo do cabeçalho, e a manchete mais o parágrafo
    mais os dois botões medem 690: não existe corpo de letra que faça isso
    caber sem virar outra coisa. Então o bloco de CIMA (kicker, manchete e fio)
    ocupa a dobra inteira sozinho, e a borda de baixo da tela cai exatamente no
    fio que abre o `om-capa-pe`.

    MEDIDO em 320x568, 320x740, 375x812 e 414x896: o fim do bloco de cima bate
    com a altura da janela nos quatro."""
    assert '<div class="om-capa-topo">' in _html("home")
    css = _css()
    # TODOS os blocos de tela estreita, e não o primeiro: a peça tem mais de
    # um (o menu de celular abriu outro em 27/08), e `re.search` pegava o que
    # viesse antes no arquivo. Um teste que depende da ORDEM das regras quebra
    # quando alguém insere uma regra acima — que é exatamente o que aconteceu.
    blocos = re.findall(
        r"@media \(max-width: 47\.999em\)[^{]*\{(.*?)\n\}", css, re.S)
    estreito = next((b for b in blocos if ".om-capa-topo" in b), "")
    assert estreito, "nenhum bloco de tela estreita trata a capa"
    assert "min-block-size: calc(100svh - var(--alt-cab)" in estreito, estreito
    assert "justify-content: center" in estreito, estreito
    # E o herói solta a altura fixa aqui: as duas regras juntas seriam uma
    # dobra medida duas vezes.
    assert "min-block-size: 0" in estreito, estreito


def test_no_papel_a_dobra_nao_existe():
    """Folha impressa não tem dobra, e uma primeira página quase vazia é o que
    acontece quando `100svh` sobrevive ao `@media print`."""
    papel = _css()[_css().index("@media print"):]
    assert re.search(r"\.om-capa, \.om-capa-topo\s*\{[^}]*min-block-size: 0", papel), \
        "o herói precisa voltar à altura do conteúdo no papel"


@pytest.mark.parametrize("pagina", TODAS)
def test_os_links_filhos_do_rodape_nao_sao_caixa_alta(pagina):
    """ITEM 23, e ele é literal: os links debaixo de `GRUPO OM` vão "em
    minúscula de primeira maiúscula, e não em caixa alta".

    Não é preferência tipográfica. Com o rótulo e os filhos na mesma caixa
    alta, a coluna vira um bloco de linhas iguais e o rótulo deixa de rotular
    qualquer coisa: a hierarquia do rodapé é feita pela DIFERENÇA entre os
    dois, e era exatamente ela que faltava."""
    html = _html(pagina)
    rodape = html[html.index('<footer class="om-rodape">'):]
    nav = re.search(r'<nav class="om-rodape-nav"[^>]*>(.*?)</nav>', rodape, re.S).group(1)
    for texto in re.findall(r">([^<>]+)</a>", nav):
        texto = texto.strip()
        if texto:
            assert texto != texto.upper() or len(texto) < 3, (pagina, texto)
    css = _css()
    regra = re.search(r"\.om-rodape-nav a, \.om-redes a\s*\{([^}]*)\}", css).group(1)
    assert "text-transform: none" in regra, regra
    # E o RÓTULO continua em caixa alta: é o contraste entre os dois que faz a
    # categoria ser categoria.
    rotulo = re.search(r"\.om-rodape-t\s*\{([^}]*)\}", css).group(1)
    assert "text-transform: uppercase" in rotulo, rotulo


# ---------------------------------------------------------------------------
# A ARMADILHA DE ESPECIFICIDADE DESTA FOLHA, que já mordeu três vezes.
#
# `.rd-grupo-om a { color: inherit }` vale (0,1,1). Qualquer regra que pinte
# `color` com UMA classe sozinha vale (0,1,0) e PERDE dela: a cor declarada
# nunca chega, e o elemento herda o branco do corpo.
#
# Quando isso acontece num controle de fundo sólido branco, o resultado é
# texto branco sobre branco. Já aconteceu com a chamada principal, e em
# 26/08 aconteceu de novo com o chip de filtro: "Todas", ligado, media
# contraste de 1 para 1 e era literalmente invisível na página de cases.
#
# O teste abaixo não olha para um controle específico. Ele varre a folha
# inteira e cruza com os templates, porque o defeito não é de um botão: é do
# formato da regra, e ele volta em todo controle novo que alguém escrever.
# ---------------------------------------------------------------------------


def _classes_usadas_em_ancora():
    """Toda classe que aparece num `<a>` de qualquer template do redesign.

    O `class` de um template Jinja tem `{% if %}` no meio, e um `split()`
    ingênuo devolveria `om-chip{%` como se fosse o nome da classe. Foi
    exatamente assim que a primeira varredura desta armadilha passou reto
    pelo chip, que era o controle quebrado."""
    classes = set()
    for arquivo in PASTA.rglob("*.html"):
        texto = arquivo.read_text(encoding="utf-8")
        for m in re.finditer(r'<a\b[^>]*?\bclass="([^"]*)"', texto, re.S):
            limpo = re.sub(r"\{%.*?%\}|\{\{.*?\}\}", " ", m.group(1), flags=re.S)
            classes.update(limpo.split())
    return classes


def test_nenhuma_regra_de_uma_classe_so_pinta_cor_de_um_link():
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    em_ancora = _classes_usadas_em_ancora()
    assert "om-f-op" in em_ancora, (
        "a varredura de classes de âncora parou de enxergar a opção de filtro, "
        "que é o controle que este teste existe para proteger; conserte a "
        "varredura antes de confiar nela")

    culpadas = []
    for m in re.finditer(r"(?:^|\})\s*([^{}@]+?)\s*\{([^}]*)\}", css, re.S):
        seletores, corpo = m.group(1), m.group(2)
        if not re.search(r"(?<![-\w])color:", corpo):
            continue
        for parte in seletores.split(","):
            p = parte.strip()
            if re.fullmatch(r"\.[A-Za-z0-9_-]+", p) and p[1:] in em_ancora:
                culpadas.append(p)

    assert not culpadas, (
        "estas regras pintam `color` com uma classe sozinha em elementos que "
        "são <a>, e perdem para `.rd-grupo-om a` (0,1,1). Prefixe com "
        f"`.rd-grupo-om `: {sorted(set(culpadas))}")


def test_a_opcao_de_filtro_ligada_tem_cor_declarada_com_o_prefixo():
    """O caso concreto que motivou o teste acima, preso separado: se alguém
    tirar o prefixo de novo, quero saber pelo nome do controle e não só pela
    varredura genérica.

    27/08: o dropdown de filtros foi refeito no padrão do de telefones
    (vidro, raio, fios) e o item ativo DEIXOU de ser um bloco branco chapado
    — no vidro, retângulo sólido é remendo. O que o teste guarda desde 26/08
    não muda: a COR do estado ativo precisa estar declarada com o prefixo
    `.rd-grupo-om`, senão `.rd-grupo-om a { color: inherit }` ganha e a
    declaração nunca chega ao controle."""
    css = CSS.read_text(encoding="utf-8")
    assert re.search(
        r"\.rd-grupo-om \.om-f-op-on \{[^}]*color:\s*var\(--branco\)", css)


# ==========================================================================
# ITEM 33: O RETRATO QUE NÃO EXISTE, E O ÍCONE QUE OCUPA O LUGAR DELE
# ==========================================================================

@pytest.mark.parametrize("pagina", ("home", "sobre"))
def test_o_depoimento_traz_um_icone_de_pessoa_e_nao_um_monograma(pagina):
    """ITEM 33: no lugar do monograma das iniciais, um ícone de pessoa.

    O monograma era tipografia fingindo ser imagem: duas letras num círculo
    lêem como avatar de aplicativo, e num depoimento de cliente elas sugerem
    que existe uma foto que não carregou. O ícone diz o que aquele espaço é.

    O ESPAÇO CONTINUA DO MESMO TAMANHO, e é isso que faz a foto entrar depois
    sem o bloco mudar: o círculo mantém as duas medidas e o `aspect-ratio`,
    escritos para o `<img>` que um dia ocupa o lugar."""
    html = _html(pagina)
    retratos = re.findall(r'<span class="om-retrato">(.*?)</span>\s*</span>|'
                          r'<span class="om-retrato">(.*?)</span>', html, re.S)
    achados = [a or b for a, b in retratos]
    assert achados, pagina
    for bloco in achados:
        assert 'href="#om-i-pessoa"' in bloco, bloco[:120]
        # Nenhuma letra sobrou dentro do círculo.
        assert not re.search(r">\s*[A-Za-zÀ-ÿ]", re.sub(r"<[^>]+>", "", bloco)), bloco
    # O desenho é da mesma família dos outros: caixa 24, sem preenchimento,
    # `currentColor` herdado da regra única que governa os ícones da peça.
    sprite = (PASTA / "_icones.html").read_text(encoding="utf-8")
    simbolo = re.search(r'<symbol id="om-i-pessoa" viewBox="([^"]+)">(.*?)</symbol>',
                        sprite, re.S)
    assert simbolo, "o símbolo precisa existir no sprite, e num lugar só"
    assert simbolo.group(1) == "0 0 24 24", simbolo.group(1)
    assert "fill=" not in simbolo.group(2), simbolo.group(2)
    assert "stroke=" not in simbolo.group(2), simbolo.group(2)


def test_o_circulo_do_retrato_continua_do_tamanho_de_uma_foto():
    """A outra metade do item 33: "o espaço reservado continua do mesmo
    tamanho". Sem isto, trocar o monograma pelo ícone teria encolhido o lugar
    da foto, e a foto que chegar depois moveria o bloco inteiro."""
    css = _css()
    retrato = re.search(r"\.om-retrato \{(.*?)\}", css, re.S).group(1)
    assert "inline-size: 3.5rem" in retrato, retrato
    assert "block-size: 3.5rem" in retrato, retrato
    assert "aspect-ratio: 1" in retrato, retrato
    assert "object-fit: cover" in retrato, retrato
    # E a tipografia do monograma saiu junto: declaração que não governa nada
    # é pista falsa para quem vier depois.
    assert "font-size" not in retrato, retrato
    assert "letter-spacing" not in retrato, retrato


# ==========================================================================
# ITEM 34: O CASE DA NINFA SAIU, E AS CONTAGENS SE AJUSTARAM SOZINHAS
# ==========================================================================

def test_o_case_removido_nao_sobrou_em_lugar_nenhum():
    """ITEM 34: "tire dos dados, do template, da grade, do trilho e dos
    testes".

    A varredura é sobre as vinte e seis páginas nos dois idiomas, e ela olha o
    HTML inteiro, não só o texto visível: um `href` para a página removida é
    um 404 desenhado no meio da proposta, e um `src` para o webp apagado é uma
    imagem quebrada."""
    for slug in CASES_REMOVIDOS:
        assert slug not in om.POR_SLUG, slug
        for pagina in TODAS:
            for lang in ("pt", "en"):
                assert slug not in _html(pagina, lang=lang), (pagina, lang, slug)


def test_as_contagens_da_peca_sao_derivadas_e_nao_escritas():
    """ITEM 34, e é o que ele realmente cobra: "confira que as contagens
    derivadas se ajustam sozinhas. Se alguma estiver escrita à mão, derive."

    Três lugares escreviam "Dezoito" com todas as letras: a meta description
    da página de cases, o `<h2>` da grade e a frase do resultado vazio da
    busca. Nenhum deles teria apitado no dia em que o case saiu: são
    dezessete cartões numa grade, e ninguém conta cartão.

    Este teste é escrito ao contrário do óbvio de propósito. Ele não confere
    que está escrito "dezessete"; ele proíbe QUALQUER número por extenso de
    case aparecer em texto de tela, nos dois idiomas. Assim ele continua
    valendo no dia em que o cliente publicar o décimo oitavo."""
    extenso = ("dezoito", "eighteen", "dezessete", "seventeen",
               "dezasseis", "dezesseis", "sixteen")
    for pagina in TODAS:
        for lang in ("pt", "en"):
            visivel = _texto_visivel_lang(pagina, lang).lower()
            for palavra in extenso:
                assert palavra not in visivel, (pagina, lang, palavra)
    # E o número que a grade mostra é o tamanho da lista, nos dois idiomas.
    for lang in ("pt", "en"):
        html = _html("cases", lang=lang)
        assert html.count('class="om-cartao om-rv"') == len(om.CASES)
        titulo = re.search(r'<h2 class="om-titulo om-split" id="om-t-lista">(.*?)</h2>',
                           html, re.S).group(1)
        assert str(len(om.CASES)) in titulo, titulo
        assert str(len(om.EMPRESAS_COM_CASE)) in titulo, titulo


def test_a_categoria_que_ficou_sem_case_sumiu_do_filtro_sozinha():
    """ITEM 34, a prova de que a derivação funciona onde ela é mais fácil de
    esquecer. O case removido era o ÚNICO de "Comunicação Integrada". A
    categoria continua na lista fechada, que é do cliente, e o chip dela some,
    porque um filtro que leva a uma grade vazia é um beco sem saída dentro de
    uma proposta.

    E a rota continua recusando o valor com 404 em vez de mostrar tudo:
    ignorar em silêncio serve uma página cujo endereço promete um recorte que
    ela não fez."""
    assert "comunicacao-integrada" in om.CHAVES_DE_CATEGORIA
    assert not any(c["categoria"] == "comunicacao-integrada" for c in om.CASES)
    com_case = {chave for chave, _, _ in om.CATEGORIAS_COM_CASE}
    assert "comunicacao-integrada" not in com_case
    html = _html("cases")
    lista = re.search(r'<nav class="om-f-lista" aria-label="Assunto">(.*?)</nav>',
                      html, re.S).group(1)
    assert "categoria=comunicacao-integrada" not in lista, lista
    # Toda contagem do menu bate com a lista, e nenhum chip leva a zero.
    for chave, _, quantos in om.CATEGORIAS_COM_CASE:
        assert quantos == sum(1 for c in om.CASES if c["categoria"] == chave)
        assert quantos > 0, chave
    for e in om.EMPRESAS_COM_CASE:
        assert e["quantos"] == sum(1 for c in om.CASES if c["empresa"] == e["chave"])
        assert e["quantos"] > 0, e["chave"]


# ---------------------------------------------------------------------------
# A AURORA do herói. O Leandro pediu "um gradiente em movimento bem sutil que
# o mouse acompanhe, algo épico", e sugeriu three.js.
#
# NÃO É three.js, e a razão está presa em teste porque é a razão que a peça
# INTEIRA defende: a biblioteca pesa uns 150 KB comprimidos, a pilha de
# movimento daqui já custa 145, e o argumento que vende a proposta é "o seu
# site entrega de 154 a 266 KB por página". Um dia alguém vai achar mais
# rápido importar uma engine 3D para desenhar um degradê. Este teste é o
# bilhete que essa pessoa vai ler.
# ---------------------------------------------------------------------------


def test_a_aurora_nao_traz_nenhuma_engine_3d_para_desenhar_um_degrade():
    """O shader tem umas quarenta linhas e vive no arquivo que já existia."""
    js = JS.read_text(encoding="utf-8")
    assert "gl.FRAGMENT_SHADER" in js, "o shader da aurora sumiu"
    # Procura USO, e não a palavra: "three" aparece em comentário em inglês e
    # dentro de "threejs" não é o mesmo que `new THREE.Scene()`.
    for uso in ("THREE.", "new THREE", "three.min", "three.module",
                "BABYLON", "PIXI."):
        assert uso not in js, f"{uso} entrou na peça"
    # E NENHUMA PÁGINA a carrega. O que importa é o que viaja pelo fio, e o
    # `three.min.js` que estava em `vendor/` pesava 603 KB sem uma única
    # página apontando para ele: quatro vezes o HTML da página mais pesada do
    # cliente, parado no repositório e em todo deploy.
    for pagina in TODAS:
        html = _html(pagina)
        assert "three" not in html.lower().replace("três", ""), pagina


@pytest.mark.parametrize("pagina", TODAS)
def test_a_aurora_so_existe_na_home(pagina):
    """Ela é o gesto de abertura da peça. Repetida nas cinco páginas viraria
    papel de parede, e cada página interna pagaria por uma tela de WebGL que
    ninguém pediu."""
    tem = 'data-aurora' in _html(pagina)
    assert tem == (pagina == "home"), pagina


def test_a_aurora_e_luz_somada_e_nao_um_fundo_novo():
    """`mix-blend-mode: screen`, e isto é conserto de um defeito real.

    Sem ele o canvas PINTA por cima do fundo da seção e o herói, que é
    #313133, vira quase preto: a peça perde a cor de base da identidade. Com
    `screen` o preto do desenho não muda nada e só a luz das manchas se soma.
    """
    css = _css()
    regra = re.search(r"\.om-aurora\s*\{([^}]*)\}", css).group(1)
    assert "mix-blend-mode: screen" in regra, regra
    # Sem isto o canvas engole o clique dos dois botões da primeira dobra.
    assert "pointer-events: none" in regra, regra
    assert "position: absolute" in regra, regra


def test_a_aurora_para_para_quem_pediu_menos_movimento():
    """PARA, e não some. O script desenha um quadro e não arma o laço: a
    imagem existe, o movimento não, que é o que a preferência pede."""
    js = JS.read_text(encoding="utf-8")
    trecho = js[js.index("var telaAurora"):]
    assert "if (querMovimento) {" in trecho, (
        "o laço da aurora não está atrás da guarda de movimento")
    # O primeiro quadro é pintado ANTES da guarda, senão não sobra imagem.
    antes = trecho[:trecho.index("if (querMovimento) {")]
    assert "pintar(0);" in antes, antes[-400:]
