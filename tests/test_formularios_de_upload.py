"""A rede que faltava embaixo do `enctype` — nos seis formulários, não em um.

Por que este arquivo existe, com a medição que o motivou: apagar o
`enctype="multipart/form-data"` de `app/templates/nodal/admin/curso_form.html`
matava **0 de 434** testes, e trocar o `<input type="file" name="capa">` por
`type="text"` matava outros **0**. Sem o `enctype`, o navegador manda só o
*nome* do arquivo como texto: `form.get("capa")` devolve `str`,
`getattr(arquivo, "filename", "")` é `""`, o arquivo vira `None` e a rota cai
no ramo "capa atual mantida" respondendo **303 com `?ok=1`** — byte por byte o
sintoma do Crítico 1 da Tarefa 5, upload descartado em silêncio com resposta de
sucesso. É a terceira vez que esta branch encontra um defeito de produção numa
rota de upload, e era o único elo do caminho que nenhum teste atravessava.

Nenhum dos seis formulários de upload do site tinha essa afirmação. Um defeito
que volta apagando uma linha de HTML merece rede em todo lugar onde a linha
existe — por isso a varredura é do projeto inteiro, e não do formulário do
Nodal.

O que isto NÃO é: prova de que o navegador envia o arquivo. Isso só se mede com
navegador de verdade (está registrado no relatório desta rodada, com a medição
ao vivo). Isto é a estrutura do HTML que o navegador recebe: um formulário que
posta arquivo e não declara multipart é o defeito, e ele é visível aqui.
"""
import re
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

# Abre um <form ...>, com os atributos possivelmente em várias linhas —
# `[^>]` casa quebra de linha, e o formulário do Nodal quebra a linha no meio
# da tag exatamente por causa do `enctype`.
_FORM = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
_FIM_FORM = re.compile(r"</form\s*>", re.IGNORECASE)
_FILE = re.compile(r"<input\b[^>]*\btype=\"file\"[^>]*>", re.IGNORECASE)

# Os seis formulários que hoje mandam arquivo ao servidor. A lista é explícita
# de propósito: formulário de upload novo que não apareça aqui faz este teste
# falhar, e a decisão de incluí-lo vira consciente em vez de silenciosa — que é
# exatamente o que faltou nas três rodadas em que o upload quebrou.
FORMULARIOS_DE_UPLOAD = {
    "admin/brands.html",
    "admin/campaign_form.html",
    "admin/case_form.html",
    "admin/nl_editor.html",
    "admin/profile.html",
    "nodal/admin/curso_form.html",
}

# O Nodal é opcional desde 24/08/2026 (ver app/main.py): a cópia pública do
# projeto não leva o produto. A lista continua EXPLÍCITA, que é a razão de ela
# existir — só deixa de exigir os templates que não estão nesta cópia. Se a
# pasta voltar, a exigência volta com ela, sem ninguém precisar lembrar.
FORMULARIOS_DE_UPLOAD = {
    caminho for caminho in FORMULARIOS_DE_UPLOAD
    if (TEMPLATES / caminho).exists()
}


def _formularios_que_postam_arquivo() -> dict[str, list[str]]:
    """{caminho do template: [tag de abertura de cada <form> que posta arquivo]}.

    Só `method="post"` entra: `base.html` tem um `<input type="file">` dentro do
    `<form class="so-bar">` da busca por imagem, que nunca posta nada — é lido
    por JavaScript e enviado por `fetch`. Exigir `enctype` dele seria pedir uma
    declaração que o navegador jamais usa.
    """
    achados: dict[str, list[str]] = {}
    for arquivo in sorted(TEMPLATES.rglob("*.html")):
        texto = arquivo.read_text(encoding="utf-8")
        aberturas = list(_FORM.finditer(texto))
        for indice, abertura in enumerate(aberturas):
            # o corpo do formulário vai até o </form> seguinte (ou até o fim do
            # arquivo, para o template que fecha em outro bloco)
            fim = _FIM_FORM.search(texto, abertura.end())
            limite = fim.start() if fim else len(texto)
            # ...mas nunca invade o próximo <form> irmão
            if indice + 1 < len(aberturas):
                limite = min(limite, aberturas[indice + 1].start())
            corpo = texto[abertura.end():limite]
            if not _FILE.search(corpo):
                continue
            if not re.search(r'method="post"', abertura.group(0), re.IGNORECASE):
                continue
            relativo = arquivo.relative_to(TEMPLATES).as_posix()
            achados.setdefault(relativo, []).append(abertura.group(0))
    return achados


def test_a_varredura_encontra_exatamente_os_formularios_de_upload_conhecidos():
    """Guarda contra o pior defeito possível num teste de varredura: passar
    porque não encontrou nada.

    Também é o que mata a segunda mutação medida — trocar `type="file"` por
    `type="text"` no campo da capa tira `curso_form.html` deste conjunto.
    """
    assert set(_formularios_que_postam_arquivo()) == FORMULARIOS_DE_UPLOAD


@pytest.mark.parametrize("template", sorted(FORMULARIOS_DE_UPLOAD))
def test_formulario_que_posta_arquivo_declara_multipart(template):
    """Sem `enctype="multipart/form-data"` o arquivo não viaja — viaja o nome
    dele, como texto, e o servidor grava "capa mantida" com 303 de sucesso."""
    tags = _formularios_que_postam_arquivo().get(template, [])
    assert tags, f"{template} deixou de postar arquivo — atualize FORMULARIOS_DE_UPLOAD"
    for tag in tags:
        assert re.search(r'enctype="multipart/form-data"', tag, re.IGNORECASE), (
            f'{template}: <form method="post"> com campo de arquivo e sem '
            f"enctype — o upload seria descartado em silêncio.\n{tag}")
