"""As rotas que servem um redesign (§10 da spec de Sites).

    GET /lab/sites/<slug>                 o endereço público. 404 enquanto for `pitch`.
    GET /lab/sites/<slug>/<pagina>        uma interna do mesmo redesign.
    GET /lab/sites/<slug>/case/<case>     a página de um case.
    GET /lab/sites/<slug>/en              as mesmas três, em inglês.
    GET /lab/sites/<slug>/en/<pagina>
    GET /lab/sites/<slug>/en/case/<case>
    GET /lab/p/<token>                    o endereço do pitch. Serve em qualquer estado.
    GET /lab/p/<token>/<pagina>           a mesma interna, pelo link do pitch.
    GET /lab/p/<token>/case/<case>        o mesmo case, pelo link do pitch.
    GET /lab/p/<token>/en                 as mesmas três, em inglês.
    GET /lab/p/<token>/en/<pagina>
    GET /lab/p/<token>/en/case/<case>

Router PRÓPRIO, e não mais rotas dentro de `app/lab/rotas.py`: aquele arquivo
já tem 14 KB e vai receber sete rotas do Notável. Ele carrega `limitar_taxa`
no construtor, igual ao outro, então toda rota que nascer aqui herda a
proteção sem quem escreve precisar lembrar.

POR QUE EXISTEM AS INTERNAS. Um redesign de uma página é um cartaz; uma
proposta comercial para uma agência de comunicação precisa mostrar o SITE. As
quatro rotas acima são o mesmo `_servir`, com um nome de arquivo a mais, e as
duas regras que já existiam continuam valendo em todas: `pitch` responde 404
no endereço público (inclusive nas internas) e o endereço do token é sempre
`noindex`.

POR QUE A LÍNGUA É UM SEGMENTO DA URL, e não um `?lang=en`, um cookie ou um
cabeçalho `Accept-Language`. O item 11 pede "site multilingual", e um site
multilíngue de verdade é aquele em que a página em inglês TEM ENDEREÇO: é o
que se manda por e-mail, o que se marca com `hreflang`, e o que o buscador
consegue guardar como uma segunda página em vez de uma variação invisível da
primeira. `?lang=en` faz as três coisas pior, e um cookie não faz nenhuma.

O prefixo `/en` é o mesmo do site do Leandro (`app/i18n.py`, primeira linha:
"Bilíngue PT-BR (padrão) / EN via prefixo /en"). Um segundo formato para a
mesma ideia, no mesmo repositório, seria só uma segunda coisa para lembrar.

E o PORTUGUÊS NÃO TEM PREFIXO. Ele é a língua da agência, do material e do
cliente; o inglês é a tradução. Um `/pt` simétrico daria a entender que o
endereço sem prefixo é uma terceira coisa, e ainda criaria duas URLs para a
mesma página em português, que é conteúdo duplicado escrito de propósito.
"""
from __future__ import annotations

import datetime as dt
import re

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Redesign
from ..services.geo import ip_do_pedido
from . import cases_grupo_om as om
from . import conteudo_grupo_om as conteudo_om
from . import selos_grupo_om as selos
from .protecao import limitar_taxa
from .textos_grupo_om import tradutor

router = APIRouter(prefix="/lab", dependencies=[Depends(limitar_taxa)])

# Endereços que são a PRÓPRIA máquina. O Chromium de `app/services/captura.py`
# roda aqui dentro e bate em 127.0.0.1 para fotografar o "depois", e como o
# endereço público responde 404 enquanto o redesign é `pitch`, essa captura
# precisa passar pelo link do token. Sem esta lista, ela carimbaria
# `visto_em` e o Leandro veria "o cliente abriu" antes de ter mandado o link.
#
# Visitante de verdade nunca chega assim: o nginx repassa o IP real e
# `app/services/geo.py::ip_do_pedido` já resolve isso.
#
# NÃO inclui "testclient": esse é o host que o `TestClient` do Starlette usa
# por padrão quando o teste não simula um IP (`client=`) explícito, e é
# assim que a suíte testa o caso comum de "visitante de verdade abriu o
# link" (`test_o_primeiro_acesso_carimba_visto_em` e companhia). Quem quer
# simular a máquina local em teste passa `client=("127.0.0.1", ...)`.
LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


# O NOME DE UMA PÁGINA INTERNA, e este `fullmatch` é a única coisa entre a
# URL e o carregador de templates. Sem ele, `/lab/sites/grupo-om/..%2f..%2f
# ..%2fetc/passwd` viraria caminho de arquivo, e o Jinja leria o que
# encontrasse: leitura de arquivo arbitrária, num servidor que também hospeda
# o portfólio inteiro do Leandro.
#
# Minúscula e hífen, e mais nada: sem ponto (nada de `.` nem de `..`), sem
# barra, sem `%`, sem maiúscula, sem acento. Precisa COMEÇAR por letra, senão
# `-foo` passaria. E o teto de 40 caracteres existe para o nome não virar
# vetor de log gigante.
_NOME_DE_PAGINA = re.compile(r"[a-z][a-z-]{0,39}")

# `home` tem endereço próprio (`/lab/sites/<slug>`), e servi-la também em
# `/lab/sites/<slug>/home` seria a mesma página em dois endereços indexáveis.
# Conteúdo duplicado é exatamente o que a docstring de `_servir` já se dá ao
# trabalho de evitar entre o token e o público.
#
# `en` entra aqui desde o item 11: ele é o PREFIXO DE LÍNGUA, e as rotas que o
# servem estão declaradas antes desta. Sem a reserva, o dia em que alguém
# criasse um `en.html` no diretório do redesign teria duas coisas diferentes
# disputando o mesmo endereço, e quem ganharia seria a ordem de declaração
# neste arquivo, que é o pior lugar para uma regra de conteúdo morar.
_SEM_ENDERECO_PROPRIO = frozenset({"home", "en"})


def _pagina(r: Redesign, nome: str = "home") -> str:
    """O template desta página deste redesign. Um por marca, escrito à mão."""
    return f"lab/sites/{r.slug}/{nome}.html"


def _raiz(r: Redesign, *, pelo_token: bool) -> str:
    """O endereço do redesign SEM a língua. Os dois prefixos saem daqui."""
    return f"/lab/p/{r.token}" if pelo_token else f"/lab/sites/{r.slug}"


def _prefixo(r: Redesign, *, pelo_token: bool, lang: str = "pt") -> str:
    """A RAIZ dos links do menu, e ela é decidida aqui, não no template.

    O mesmo HTML é servido em dois endereços, e o menu do topo precisa manter
    o visitante no endereço em que ele entrou: quem abriu pelo link do pitch
    não pode ser jogado no endereço público (que responde 404 enquanto o
    redesign é `pitch`), e quem abriu pelo público não pode receber o token
    secreto colado num `href`.

    O template só interpola `{{ base }}`. Montar isso lá dentro com um `if`
    sobre `r.estado` espalharia a regra por cinco arquivos, e o dia em que ela
    mudasse quatro deles ficariam para trás.

    A LÍNGUA ENTRA AQUI PELO MESMO MOTIVO (item 11). Quem abriu a página em
    inglês precisa continuar em inglês ao clicar em qualquer item do menu, e
    isso é uma propriedade do PREFIXO, não de cada link. Com a língua nesta
    função, os doze arquivos de template continuam interpolando só
    `{{ base }}`, e nenhum deles sabe que existe um segundo idioma.
    """
    raiz = _raiz(r, pelo_token=pelo_token)
    return f"{raiz}/en" if lang == "en" else raiz


def _caso(r: Redesign, nome: str) -> str:
    """Valida o nome de um CASE e devolve o template dele, ou 404.

    Mesmas três peneiras de `_interna`, e de propósito: um segundo formato de
    nome, mais frouxo, seria uma segunda porta para a mesma travessia de
    diretório, e a segunda porta é sempre a que fica sem tranca. `..%2f..%2f`
    reprova aqui pela mesma regra que reprova lá.

    A diferença é só o lugar no disco: um case mora em `case/`, e não na raiz
    do redesign. Isso mantém `sobre.html` e `ninfa.html` em pastas diferentes,
    e é o que impede `/lab/sites/grupo-om/case/sobre` de servir a página do
    grupo por um endereço que não é o dela.
    """
    from ..main import templates

    if not _NOME_DE_PAGINA.fullmatch(nome):
        raise HTTPException(status_code=404)
    alvo = f"lab/sites/{r.slug}/case/{nome}.html"
    try:
        templates.env.get_template(alvo)
    except jinja2.TemplateNotFound:
        raise HTTPException(status_code=404) from None
    return alvo


def _interna(r: Redesign, nome: str) -> str:
    """Valida o nome de uma interna e devolve o template dela, ou 404.

    Três peneiras, e a ordem importa: forma do nome, nome reservado, e só
    então o disco. A última é o que faz um redesign de página única (a
    Padaria Aurora, por exemplo) responder 404 em qualquer interna sem
    precisar de lista nenhuma neste arquivo.
    """
    from ..main import templates

    if not _NOME_DE_PAGINA.fullmatch(nome) or nome in _SEM_ENDERECO_PROPRIO:
        raise HTTPException(status_code=404)
    alvo = _pagina(r, nome)
    try:
        templates.env.get_template(alvo)
    except jinja2.TemplateNotFound:
        raise HTTPException(status_code=404) from None
    return alvo


def _filtros(request: Request) -> dict:
    """Lê `?empresa=` e `?categoria=` da URL, ou responde 404 (item 27).

    O FILTRO É RESOLVIDO NO SERVIDOR, e por três razões que decidiram o
    desenho inteiro da página de cases:

    1. A Global Constraint 4 proíbe `<form>` que envie para este servidor, e
       um `<select>` com botão seria exatamente isso. Link com parâmetro não é
       formulário: é navegação, e o navegador já sabe fazer.
    2. Filtro que só existe em JavaScript é filtro que some quando o script
       falha, e a grade fica sem nenhuma forma de recorte. Aqui a grade nasce
       completa e legível sem script, e o recorte é um endereço.
    3. Um recorte com endereço PRÓPRIO é um recorte que o Leandro pode mandar
       por e-mail: "veja os cases da OpusMúltipla" é um link, não uma
       instrução de clique.

    A BUSCA POR TEXTO é o contrário e fica no cliente, escondida até o script
    chegar: uma caixa de busca sem `<form>` e sem JS é um campo que não faz
    nada, e controle que não faz nada é pior que controle nenhum.

    E O VALOR É PENEIRADO, com a mesma severidade de `{pagina}` e `{case}`:
    parâmetro de URL é entrada de fora como qualquer outra. Fora da lista
    fechada é 404, e não "ignora e mostra tudo": ignorar em silêncio serve uma
    página cujo endereço promete um recorte que ela não fez.
    """
    empresa = request.query_params.get("empresa") or None
    categoria = request.query_params.get("categoria") or None
    if empresa is not None and empresa not in om.CHAVES_DE_EMPRESA:
        raise HTTPException(status_code=404)
    if categoria is not None and categoria not in om.CHAVES_DE_CATEGORIA:
        raise HTTPException(status_code=404)
    return {"empresa": empresa, "categoria": categoria}


def _consulta(filtros: dict) -> str:
    """A query string REESCRITA a partir dos valores já validados.

    Ela vai nos links de idioma, para quem troca de língua no meio de um
    recorte não voltar para a grade inteira. Reescrever em vez de repassar
    `request.url.query` é o que impede um parâmetro estranho de atravessar a
    validação de carona num `href` que a página desenha.
    """
    partes = [f"{chave}={valor}" for chave, valor in sorted(filtros.items()) if valor]
    return "?" + "&".join(partes) if partes else ""


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


def _servir(request: Request, r: Redesign, *, pelo_token: bool,
            template: str | None = None, lang: str = "pt",
            sufixo: str = "") -> HTMLResponse:
    """Renderiza a página do redesign.

    `pelo_token` diz se esta resposta saiu pelo endereço secreto
    (`/lab/p/<token>`), e não pelo público (`/lab/sites/<slug>`).

    `lang` e `sufixo` são o item 11. O primeiro escolhe o dicionário de
    tradução e a etiqueta de `<html lang>`; o segundo é o caminho DESTA página
    dentro do redesign ("", "/sobre", "/case/ninfa"), e existe por uma razão
    só: sem ele o seletor de idioma não sabe para onde mandar a pessoa. Um
    seletor que sempre volta para a capa é um seletor que faz o leitor perder
    o lugar onde estava, e um leitor que perde o lugar fecha a proposta.

    Cada rota passa o seu, em vez de este arquivo remontar o caminho a partir
    de `request.url.path`: remontar exigiria desfazer o prefixo (que varia
    entre slug e token) e a língua, e um erro nessa conta não aparece como
    erro, aparece como um link de idioma apontando para 404.

    O `noindex` NÃO pode depender só de `r.estado`: ele é propriedade do
    ENDEREÇO, não do estado do redesign. Três razões:

    1. O token é secreto por desenho. Se a indexabilidade dele dependesse do
       estado, bastaria o Leandro tornar um redesign público e voltar para
       `pitch` para o token já ter sido visitado (e guardado) por rastreador.
    2. Os dois endereços servem o MESMO conteúdo. O canônico é
       `/lab/sites/<slug>`; indexar os dois é conteúdo duplicado, e quem
       perde posição no buscador é justamente o endereço que deveria
       aparecer.
    3. Se o link do token vazar (por exemplo, colado num WhatsApp público),
       o buscador não pode achá-lo — mesmo que o redesign já esteja
       `publico` ou `aprovado`.

    Por isso: o endereço do token é sempre `noindex, nofollow`, e o
    endereço público segue `index, follow` quando o estado permite (regra
    inalterada). O template recebe essa decisão pronta em `noindex`, em vez
    de repetir `r.estado == 'pitch'` sozinho.
    """
    from ..main import templates

    noindex = pelo_token or r.estado == "pitch"
    raiz = _raiz(r, pelo_token=pelo_token)
    filtros = _filtros(request)
    consulta = _consulta(filtros)
    resposta = templates.TemplateResponse(
        request, template or _pagina(r), {
            "r": r,
            "noindex": noindex,
            "base": _prefixo(r, pelo_token=pelo_token, lang=lang),
            # ITEM 11. Três coisas, e as três já resolvidas aqui para nenhum
            # template precisar decidir nada sobre idioma:
            #   `lang`       "pt" ou "en", para o template ligar o que for
            #                próprio de uma língua (o seletor, por exemplo).
            #   `lang_html`  a etiqueta de `<html lang>`, que não é a mesma
            #                coisa: "pt-BR" tem região e "pt" não, e leitor de
            #                tela troca de voz por causa dessa diferença.
            #   `T`          o tradutor. Em português ele é a identidade, e é
            #                por isso que o texto dos templates continua sendo
            #                o português legível, e não uma chave.
            #   `enderecos`  ESTA página nas duas línguas, para o seletor.
            "lang": lang,
            "lang_html": "en" if lang == "en" else "pt-BR",
            "T": tradutor(lang),
            "enderecos": {"pt": raiz + sufixo + consulta,
                          "en": f"{raiz}/en{sufixo}{consulta}"},
            # O ENDEREÇO ABSOLUTO DESTA PÁGINA, para os botões de partilha do
            # case. Eles são links para o endereço de intenção de cada rede, e
            # uma rede não tem o que fazer com `/lab/p/<token>/case/x`: o que
            # ela recebe precisa ser um endereço que o navegador de outra
            # pessoa consiga abrir.
            #
            # Sai de `request.base_url` e não de uma constante: em produção o
            # nginx repassa o host real, e uma constante escrita aqui viraria
            # um link quebrado no dia em que o domínio mudasse.
            "endereco_raiz": str(request.base_url).rstrip("/"),
            "endereco_abs": (str(request.base_url).rstrip("/")
                             + _prefixo(r, pelo_token=pelo_token, lang=lang) + sufixo),
            # ITENS 19 e 27. O material do cliente entra pelo CONTEXTO, e não
            # por um `{% set %}` de template: o filtro é validado no servidor,
            # e dado que o servidor valida não pode viver só dentro do Jinja.
            # Ver `app/lab/cases_grupo_om.py`.
            "cases": om.CASES,
            # O mapa serviço→case do hover dos sete serviços (27/08); as
            # justificativas moram ao lado dele, em `cases_grupo_om.py`.
            "caso_do_servico": om.CASO_DO_SERVICO,
            # A central de conteúdo e a página de serviços (27/08).
            "servicos": conteudo_om.SERVICOS,
            "artigos": conteudo_om.ARTIGOS,
            "videos": conteudo_om.VIDEOS,
            "artigo_por_slug": conteudo_om.POR_SLUG_ARTIGO,
            "cases_filtrados": om.filtrar(**filtros),
            "filtros": filtros,
            "empresas": om.EMPRESAS,
            "empresas_com_case": om.EMPRESAS_COM_CASE,
            "categorias_com_case": om.CATEGORIAS_COM_CASE,
            "nome_da_categoria": om.NOME_DA_CATEGORIA,
            "assinante": om.assinante,
            "por_slug": om.POR_SLUG,
            # ITEM 23: os selos, nos dois grupos que o rodapé e a página de
            # certificações desenham. Eles saem do mesmo lugar para as duas,
            # senão a página diz quinze e o rodapé diz dezesseis.
            "certificacoes": selos.CERTIFICACOES,
            "premios": selos.PREMIOS,
        })
    if noindex:
        # Cinto e suspensório com a meta do template: cabeçalho HTTP cobre
        # o caso de o buscador ler a resposta sem executar o HTML.
        resposta.headers["x-robots-tag"] = "noindex, nofollow"
    return resposta


# ==========================================================================
# AS SEIS ROTAS EM INGLÊS (item 11)
#
# ELAS VÊM PRIMEIRO, e a ordem NÃO é estilo: o Starlette casa na ordem de
# declaração, e `/sites/{slug}/{pagina}` casaria com `/sites/grupo-om/en`
# tratando "en" como nome de página. O resultado seria um 404 na home em
# inglês, que é o tipo de defeito que só aparece depois de o link já ter sido
# mandado. Pelo mesmo motivo, `/en/case/{caso}` vem antes de `/en/{pagina}`.
#
# Cada uma é a irmã de uma rota que já existia, com `lang="en"` e o `sufixo`
# desta página. NADA MAIS MUDA: as mesmas peneiras de nome, o mesmo
# `_publico_ou_404`, o mesmo `marcar_visto`. Se um dia a regra do `pitch`
# mudar, ela muda em `_publico_ou_404` e as doze obedecem juntas, que é o
# contrário do que aconteceria se a versão em inglês tivesse virado um
# segundo arquivo de rotas.
# ==========================================================================

@router.get("/sites/{slug}/en", response_class=HTMLResponse)
async def redesign_publico_en(slug: str, request: Request,
                              db: Session = Depends(get_db)) -> HTMLResponse:
    """A home em inglês, pelo endereço público."""
    return _servir(request, _publico_ou_404(db, slug), pelo_token=False, lang="en")


@router.get("/sites/{slug}/en/case/{caso}", response_class=HTMLResponse)
async def redesign_publico_case_en(slug: str, caso: str, request: Request,
                                   db: Session = Depends(get_db)) -> HTMLResponse:
    """A página de um case em inglês, pelo endereço público."""
    r = _publico_ou_404(db, slug)
    return _servir(request, r, pelo_token=False, template=_caso(r, caso),
                   lang="en", sufixo=f"/case/{caso}")


@router.get("/sites/{slug}/en/{pagina}", response_class=HTMLResponse)
async def redesign_publico_interna_en(slug: str, pagina: str, request: Request,
                                      db: Session = Depends(get_db)) -> HTMLResponse:
    """Uma interna em inglês, pelo endereço público."""
    r = _publico_ou_404(db, slug)
    return _servir(request, r, pelo_token=False, template=_interna(r, pagina),
                   lang="en", sufixo=f"/{pagina}")


@router.get("/sites/{slug}", response_class=HTMLResponse)
async def redesign_publico(slug: str, request: Request,
                           db: Session = Depends(get_db)) -> HTMLResponse:
    """O endereço público. Enquanto o redesign é `pitch`, ele NÃO EXISTE:
    404, e não 403. Um 403 confirmaria que o endereço existe, que é
    exatamente o que não interessa contar a quem está tentando adivinhar."""
    return _servir(request, _publico_ou_404(db, slug), pelo_token=False)


@router.get("/sites/{slug}/{pagina}", response_class=HTMLResponse)
async def redesign_publico_interna(slug: str, pagina: str, request: Request,
                                   db: Session = Depends(get_db)) -> HTMLResponse:
    """Uma interna pelo endereço público. As MESMAS regras da home: enquanto
    o redesign é `pitch`, ela também não existe. Fosse diferente, o recorte
    do estado `pitch` cairia por uma porta lateral, que é sempre por onde ele
    cairia mesmo."""
    r = _publico_ou_404(db, slug)
    return _servir(request, r, pelo_token=False, template=_interna(r, pagina),
                   sufixo=f"/{pagina}")


@router.get("/sites/{slug}/case/{caso}", response_class=HTMLResponse)
async def redesign_publico_case(slug: str, caso: str, request: Request,
                                db: Session = Depends(get_db)) -> HTMLResponse:
    """A página interna de um case, pelo endereço público.

    A regra do estado `pitch` vale AQUI TAMBÉM, e é por isso que esta rota
    chama o mesmo `_publico_ou_404`: uma proposta que ainda não foi mostrada
    ao cliente não pode ter os cases dela abertos por um endereço mais fundo.
    Um recorte que vale na home e não vale a dois níveis de profundidade não
    é recorte, é sugestão.
    """
    r = _publico_ou_404(db, slug)
    return _servir(request, r, pelo_token=False, template=_caso(r, caso),
                   sufixo=f"/case/{caso}")


def _publico_ou_404(db: Session, slug: str) -> Redesign:
    r = db.query(Redesign).filter(Redesign.slug == slug).one_or_none()
    if r is None or r.estado == "pitch":
        raise HTTPException(status_code=404)
    return r


def _por_token_ou_404(db: Session, token: str) -> Redesign:
    r = db.query(Redesign).filter(Redesign.token == token).one_or_none()
    if r is None:
        raise HTTPException(status_code=404)
    return r


@router.get("/p/{token}/en", response_class=HTMLResponse)
async def redesign_pitch_en(token: str, request: Request,
                            db: Session = Depends(get_db)) -> HTMLResponse:
    """A home em inglês, pelo link do pitch. Carimba `visto_em` como a
    portuguesa: abrir a proposta em inglês é abrir a proposta."""
    r = _por_token_ou_404(db, token)
    marcar_visto(db, r, request)
    return _servir(request, r, pelo_token=True, lang="en")


@router.get("/p/{token}/en/case/{caso}", response_class=HTMLResponse)
async def redesign_pitch_case_en(token: str, caso: str, request: Request,
                                 db: Session = Depends(get_db)) -> HTMLResponse:
    """A página de um case em inglês, pelo link do pitch. A ORDEM é a mesma
    das outras: valida o nome antes de carimbar."""
    r = _por_token_ou_404(db, token)
    alvo = _caso(r, caso)
    marcar_visto(db, r, request)
    return _servir(request, r, pelo_token=True, template=alvo,
                   lang="en", sufixo=f"/case/{caso}")


@router.get("/p/{token}/en/{pagina}", response_class=HTMLResponse)
async def redesign_pitch_interna_en(token: str, pagina: str, request: Request,
                                    db: Session = Depends(get_db)) -> HTMLResponse:
    """Uma interna em inglês, pelo link do pitch."""
    r = _por_token_ou_404(db, token)
    alvo = _interna(r, pagina)
    marcar_visto(db, r, request)
    return _servir(request, r, pelo_token=True, template=alvo,
                   lang="en", sufixo=f"/{pagina}")


@router.get("/p/{token}", response_class=HTMLResponse)
async def redesign_pitch(token: str, request: Request,
                         db: Session = Depends(get_db)) -> HTMLResponse:
    """O endereço do pitch. Serve em qualquer estado, e é o único que serve
    enquanto o redesign é `pitch`."""
    r = _por_token_ou_404(db, token)
    marcar_visto(db, r, request)
    return _servir(request, r, pelo_token=True)


@router.get("/p/{token}/{pagina}", response_class=HTMLResponse)
async def redesign_pitch_interna(token: str, pagina: str, request: Request,
                                 db: Session = Depends(get_db)) -> HTMLResponse:
    """Uma interna pelo link do pitch. Carimba `visto_em` igual à home: o
    cliente pode ter recebido o link e aberto direto numa interna, e isso é
    tão "o cliente abriu a proposta" quanto abrir a capa. As duas guardas de
    `marcar_visto` continuam de pé: nunca reescreve, e nunca carimba vindo do
    loopback (a captura do 'depois')."""
    r = _por_token_ou_404(db, token)
    alvo = _interna(r, pagina)
    marcar_visto(db, r, request)
    return _servir(request, r, pelo_token=True, template=alvo, sufixo=f"/{pagina}")


@router.get("/p/{token}/case/{caso}", response_class=HTMLResponse)
async def redesign_pitch_case(token: str, caso: str, request: Request,
                              db: Session = Depends(get_db)) -> HTMLResponse:
    """A página de um case pelo link do pitch. Carimba `visto_em` como as
    outras: o Leandro pode ter mandado o link direto de um case, e abrir esse
    link é tão "o cliente abriu a proposta" quanto abrir a capa.

    A ORDEM É A MESMA das outras duas, e ela não é acidental: valida o nome
    ANTES de carimbar. Assim um endereço de case que não existe responde 404
    sem marcar a proposta como vista, e um rastreador que chutasse nomes não
    conseguiria dizer ao Leandro que o cliente leu o que ninguém leu.
    """
    r = _por_token_ou_404(db, token)
    alvo = _caso(r, caso)
    marcar_visto(db, r, request)
    return _servir(request, r, pelo_token=True, template=alvo, sufixo=f"/case/{caso}")
