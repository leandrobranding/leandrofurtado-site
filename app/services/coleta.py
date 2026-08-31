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

# Tag que vive DENTRO de um bloco de texto e não o encerra. Fechar uma
# destas não pode zerar o buffer do parágrafo: `<p>Ligue: (41)
# <strong>99999</strong>-8888</p>` perderia tudo antes do negrito, e negrito
# no meio de telefone é padrão de site de PME.
INLINE = {"a", "strong", "b", "em", "i", "span", "small", "u", "mark",
          "code", "sup", "sub", "abbr", "time", "label", "font", "br"}

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
        # Todo texto visível, sem filtro de tag: a varredura de contato,
        # endereço e horário usa isto, não só p/li, porque site feito em
        # construtor (Wix, Webflow, React sem SSR semântico) põe telefone e
        # endereço dentro de div/span, e um coletor que só lê p/li fica cego
        # justamente no site ruim que ele existe para ler.
        self.texto_todo: list[str] = []
        self._buffer_link = ""

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
            # Buffer PRÓPRIO do link, separado do buffer do bloco pai (ex.:
            # <p>). Zerar self._buffer aqui decapitava o texto do parágrafo
            # que já tinha sido lido antes do <a> abrir.
            self._buffer_link = ""
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
        self._buffer_link += dado
        self.texto_todo.append(dado)

    # ------------------------------------------------------ fechamento --
    def handle_endtag(self, tag):
        texto = " ".join(self._buffer.split()).strip()
        if tag == "a":
            # Texto do link vem do buffer PRÓPRIO, não do buffer do bloco
            # pai: um <a> no meio de um <p> não pode decapitar a frase que
            # já tinha sido lida antes dele.
            texto_link = " ".join(self._buffer_link.split()).strip()
            if self._href:
                self.links.append((self._href, texto_link))
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
        # O buffer do bloco pai (<p>, <li>, ...) segue acumulando através de
        # qualquer tag INLINE aninhada (<a>, <strong>, <span>, ...): só é
        # zerado quando o próprio bloco fecha.
        if tag not in INLINE:
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

    # Segmentos de texto para a QUEDA de endereço/horário (elas varrem
    # trecho a trecho e caem para um fragmento só quando o bloco inteiro não
    # tem o que procuram; ver mais abaixo). A junção usa "\n": cada chamada
    # de `handle_data` já é um nó de texto isolado do HTML (um <div> de
    # menu, um <span> de rodapé), e colar tudo com espaço vira um parágrafo
    # só sem pontuação nenhuma no meio. Medido ao vivo em
    # brainboxdesign.com.br: sem esse cuidado o endereço cai num segmento de
    # 328 caracteres e o corte por tamanho descarta ele inteiro.
    corpo_bruto = "\n".join(
        leitor.paragrafos + leitor.itens +
        ([leitor.endereco] if leitor.endereco else []) +
        leitor.texto_todo
    )
    segmentos = [" ".join(t.split()) for t in re.split(r"[\n.;|]+", corpo_bruto)]
    segmentos = [t for t in segmentos if t]

    for href, _ in leitor.links:
        baixo = href.lower()
        if "wa.me/" in baixo or "api.whatsapp.com" in baixo:
            # Corta a query ANTES de tirar os dígitos: `?text=...` com número
            # dentro grudaria no telefone e produziria um contato errado, que
            # é pior que contato ausente porque parece certo. Mas quando o
            # número vem DENTRO da query (`?phone=55...`), ele precisa ser
            # extraído antes do corte, senão some.
            if "phone=" in baixo:
                alvo = baixo.split("phone=")[-1].split("&")[0]
            else:
                alvo = baixo.split("wa.me/")[-1].split("?")[0]
            numero = re.sub(r"\D", "", alvo)
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

    # Blocos de texto, cada um varrido POR SI. Emendar tudo numa string só
    # (que foi o que este módulo fez até 25/08/2026) deixa o `[\s.-]?` do
    # regex de telefone casar ATRAVÉS da emenda: um `<div>99998888</div>` no
    # topo da página e um `<li>` terminando em "41" lá embaixo viravam
    # '4199998888', um número que não existe em lugar nenhum do HTML.
    #
    # Telefone e e-mail nunca atravessam dois blocos de texto num documento
    # real, então varrer por bloco não perde nada, e torna impossível
    # fabricar contato por vizinhança acidental. Dado inventado numa
    # proposta comercial é o defeito que este módulo não pode ter.
    blocos = leitor.paragrafos + leitor.itens + leitor.texto_todo
    if leitor.endereco:
        blocos.append(leitor.endereco)

    for bloco in blocos:
        for achado in _TELEFONE.findall(bloco):
            numero = re.sub(r"\D", "", achado)
            if len(numero) >= 10 and numero not in dossie["telefones"]:
                dossie["telefones"].append(numero)
        for achado in _EMAIL.findall(bloco):
            if achado not in dossie["emails"]:
                dossie["emails"].append(achado)

    dossie["endereco"] = leitor.endereco
    if not dossie["endereco"]:
        # Blocos INTEIROS primeiro: num site semântico o endereço vem num
        # `<p>` só, e `texto_todo` o quebraria em cada `<br>`, entregando
        # rua sem bairro nem CEP. Os fragmentos são a queda seguinte, para
        # o site de construtor, onde não existe parágrafo nenhum.
        for fonte in (leitor.paragrafos + leitor.itens, segmentos):
            for trecho in fonte:
                trecho = " ".join(trecho.split())
                if 10 < len(trecho) < 400 and _LOGRADOURO.search(trecho) and re.search(r"\d", trecho):
                    dossie["endereco"] = trecho
                    break
            if dossie["endereco"]:
                break

    # Mesma ordem do endereço, e pelo mesmo motivo: horário costuma vir num
    # bloco só, quebrado por <br>, e cair direto nos fragmentos entregaria
    # só o primeiro dia da semana.
    for fonte in (leitor.paragrafos + leitor.itens, segmentos):
        for trecho in fonte:
            trecho = " ".join(trecho.split())
            if _DIA.search(trecho) and _HORA.search(trecho):
                if trecho not in dossie["horarios"]:
                    dossie["horarios"].append(trecho)
        if dossie["horarios"]:
            break

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
