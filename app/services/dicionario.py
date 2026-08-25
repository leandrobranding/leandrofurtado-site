"""Significados e sinônimos, para o recurso de acessibilidade.

Por que passa pelo servidor e não direto do navegador: a política de segurança
do site (CSP) só deixa o front falar com o próprio domínio, e abrir exceção para
domínios de terceiros enfraquece a proteção contra injeção de script. Buscando
aqui, a origem continua sendo "self", a resposta fica em cache no banco e o
visitante não é exposto a nenhum serviço externo.

Ordem das fontes, da mais confiável para a mais abrangente:
  1. Dicionário Aberto  — português de verdade, domínio público, ótimo para
     palavras comuns; ignora estrangeirismos ("design" não está lá).
  2. Wikcionário        — cobre estrangeirismo, gíria e termo técnico, e é a
     única das duas que traz sinônimo.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

TEMPO = 6.0  # nenhuma consulta pode segurar a página do visitante
CABECALHO = {"User-Agent": "leandrofurtado.com.br/1.0 (acessibilidade; contato@leandrofurtado.com.br)"}

# a palavra vem de duplo clique numa página, então pode vir suja
LIMPA = re.compile(r"[^\wÀ-ÿ-]+", re.UNICODE)


def normaliza(bruto: str) -> str:
    termo = LIMPA.sub("", (bruto or "").strip()).strip("-")
    return termo.lower()[:60]


def _do_dicionario_aberto(termo: str) -> dict:
    """O verbete vem como XML dentro do JSON. Interessa <def>, <gramGrp> e <etym>."""
    r = httpx.get(f"https://api.dicionario-aberto.net/word/{termo}",
                  timeout=TEMPO, headers=CABECALHO)
    r.raise_for_status()
    entradas = r.json() or []

    significados, classes = [], []
    for entrada in entradas[:4]:
        try:
            raiz = ET.fromstring(entrada.get("xml") or "")
        except ET.ParseError:
            continue
        for sense in raiz.iter("sense"):
            gram = sense.findtext("gramGrp")
            if gram and gram.strip() not in classes:
                classes.append(gram.strip())
            for d in sense.iter("def"):
                texto = " ".join((d.itertext()))
                texto = re.sub(r"\s+", " ", texto).strip(" .;")
                if texto and texto not in significados:
                    significados.append(texto)

    return {"significados": significados[:4], "classes": classes[:3], "sinonimos": []}


# O Wikcionário é lido em wikitexto, não no extrato em texto puro: o extrato
# descarta justamente as listas de sinônimos, que é o que mais interessa aqui.
_SECAO = re.compile(r"^=+\s*(.+?)\s*=+\s*$", re.M)
_SINONIMO = ("sinônimo", "sinónimo", "synonym")
_CLASSES = ("substantivo", "verbo", "adjetivo", "advérbio", "pronome", "preposição",
            "conjunção", "interjeição", "numeral", "artigo", "expressão", "locução",
            "noun", "verb", "adjective", "adverb", "pronoun", "preposition")
_ELO = re.compile(r"\[\[(?:[^\]|#]*\|)?([^\]|#]+)\]\]")   # [[a|b]] e [[a]]
_CHAVE = re.compile(r"\{\{[^{}]*\}\}")                     # {{modelo}}


def _limpa_wiki(linha: str) -> str:
    anterior = None
    while anterior != linha:            # modelos podem estar aninhados
        anterior, linha = linha, _CHAVE.sub("", linha)
    linha = _ELO.sub(r"\1", linha)
    linha = re.sub(r"'{2,}|<[^>]+>", "", linha)
    return re.sub(r"\s+", " ", linha).strip(" .;:,*#")


def _do_wikcionario(termo: str, lang: str) -> dict:
    site = "pt" if lang == "pt" else "en"
    r = httpx.get(f"https://{site}.wiktionary.org/w/api.php",
                  params={"action": "parse", "page": termo, "prop": "wikitext",
                          "redirects": "1", "format": "json", "formatversion": "2"},
                  timeout=TEMPO, headers=CABECALHO)
    r.raise_for_status()
    texto = ((r.json().get("parse") or {}).get("wikitext") or "")
    if not texto:
        return {"significados": [], "classes": [], "sinonimos": []}

    # split com grupo de captura devolve [antes, titulo1, corpo1, titulo2, corpo2...]
    partes = _SECAO.split(texto)
    significados, classes, sinonimos = [], [], []

    for i in range(1, len(partes) - 1, 2):
        titulo, corpo = partes[i].strip(), partes[i + 1]
        baixo = titulo.lower()

        if any(s in baixo for s in _SINONIMO):
            for achado in _ELO.findall(corpo):
                achado = achado.strip()
                # Wikisaurus é remissão para outra página, não é sinônimo
                if (achado and ":" not in achado and achado.lower() != termo
                        and achado not in sinonimos):
                    sinonimos.append(achado)
            continue

        if not any(c in baixo for c in _CLASSES):
            continue
        rotulo = re.sub(r"\d+$", "", titulo).strip()
        if rotulo and rotulo not in classes:
            classes.append(rotulo)
        for linha in corpo.splitlines():
            # "#" abre definição; "#:" e "#*" são exemplo e citação
            if not linha.startswith("#") or linha[1:2] in (":", "*"):
                continue
            limpo = _limpa_wiki(linha)
            if len(limpo) > 1 and limpo not in significados:
                significados.append(limpo)

    return {"significados": significados[:5], "classes": classes[:3], "sinonimos": sinonimos[:10]}


def buscar(termo: str, lang: str = "pt") -> dict:
    """Junta as fontes. Retorna sempre o mesmo formato, mesmo sem achar nada."""
    resposta = {"termo": termo, "significados": [], "classes": [], "sinonimos": [], "fontes": []}

    if lang == "pt":
        try:
            achado = _do_dicionario_aberto(termo)
            if achado["significados"]:
                resposta["significados"] = achado["significados"]
                resposta["classes"] = achado["classes"]
                resposta["fontes"].append("Dicionário Aberto")
        except Exception:
            pass  # fonte fora do ar não pode derrubar o recurso

    # o Wikcionário entra para completar sinônimo, ou sozinho quando o outro não achou
    precisa = not resposta["significados"] or not resposta["sinonimos"]
    if precisa:
        try:
            achado = _do_wikcionario(termo, lang)
            if achado["significados"] and not resposta["significados"]:
                resposta["significados"] = achado["significados"]
                resposta["classes"] = resposta["classes"] or achado["classes"]
            if achado["sinonimos"]:
                resposta["sinonimos"] = achado["sinonimos"]
            if achado["significados"] or achado["sinonimos"]:
                resposta["fontes"].append("Wikcionário")
        except Exception:
            pass

    return resposta
