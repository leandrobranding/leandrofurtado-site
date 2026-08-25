"""Ajuda a montar upload de verdade para testes sem TestClient nem servidor.

Sem prefixo `test_`: não é um arquivo de teste, é apoio para os que
exercitam upload com disco real (ver tests/test_admin_case_capa_disco.py,
tests/test_admin_profile_capa_disco.py, tests/test_api_capa_disco.py).
Nasceu de três cópias quase idênticas desse mesmo bloco de código — a
mesma lição de não duplicar regra que motivou apagar_arquivo_exato em
app/services/images.py se aplica aqui, ainda que isto seja teste, não
produção: três cópias de "como montar um multipart" seriam três lugares
para esquecer de atualizar se o formato mudar.

Duas formas de upload real aparecem na suíte:

- Rotas que leem `await request.form()` (o painel: apply_case_form,
  profile_save) precisam de um `Request` com corpo multipart de verdade —
  é o que `post_multipart` monta.
- Rotas que recebem `UploadFile` como parâmetro da própria função (a API:
  upload_cover, upload_media) não passam por `request.form()` nenhuma —
  um `fastapi.UploadFile` em cima de um `BytesIO` já basta, sem precisar
  de multipart nenhum. Ver `arquivo_upload` abaixo.
"""
import io

from fastapi import UploadFile
from PIL import Image
from starlette.requests import Request

BOUNDARY = "----teste-multipart-de-verdade"


def png_bytes(cor: str) -> bytes:
    """PNG de verdade, pequeno, gerado em memória — não um dublê de bytes."""
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), cor).save(buf, "PNG")
    return buf.getvalue()


def arquivo_upload(cor: str, nome: str = "arquivo.png") -> UploadFile:
    """UploadFile de verdade para rotas que recebem o arquivo como parâmetro
    da própria função (não passam por request.form())."""
    buf = io.BytesIO(png_bytes(cor))
    return UploadFile(buf, filename=nome)


def _corpo_multipart(campos: dict, arquivos: dict) -> bytes:
    """Monta um corpo multipart/form-data de verdade. `arquivos` é
    {nome_do_campo: (nome_do_arquivo, bytes, content_type)}.

    Um valor de `campos` ou `arquivos` pode ser uma LISTA em vez de um valor
    só — vira um `name=` repetido no corpo, uma parte por item da lista, na
    mesma ordem. É o que um formulário de verdade manda quando tem mais de
    uma linha dinâmica (award_title_pt de dois prêmios, por exemplo) ou um
    `<input type="file" multiple>` com mais de um arquivo escolhido — sem
    isso não dava para simular nem "duas linhas no mesmo POST" nem "duas
    fotos no mesmo campo" nos testes."""
    partes = []
    for nome, valor in campos.items():
        for item in (valor if isinstance(valor, list) else [valor]):
            partes.append(
                f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n'
                f"{item}\r\n".encode()
            )
    for nome, valor in arquivos.items():
        itens = valor if isinstance(valor, list) else [valor]
        for nome_arquivo, conteudo, tipo in itens:
            cabecalho = (
                f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{nome}"; '
                f'filename="{nome_arquivo}"\r\nContent-Type: {tipo}\r\n\r\n'
            ).encode()
            partes.append(cabecalho + conteudo + b"\r\n")
    partes.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(partes)


def post_multipart(caminho: str, campos: dict, arquivos: dict,
                   sessao: dict | None = None) -> Request:
    """Request POST com corpo multipart de verdade — sem TestClient, sem
    servidor. `sessao` padrão já traz o csrf que `campos["csrf"]` costuma
    repetir (check_csrf compara os dois)."""
    corpo = _corpo_multipart(campos, arquivos)
    scope = {
        "type": "http",
        "method": "POST",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "headers": [
            (b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode()),
            (b"content-length", str(len(corpo)).encode()),
        ],
        "state": {"clean_path": caminho, "lang": "pt"},
        "session": sessao or {"csrf": "teste-csrf", "user": "leandro"},
    }
    enviado = False

    async def receive():
        nonlocal enviado
        if enviado:
            return {"type": "http.request", "body": b"", "more_body": False}
        enviado = True
        return {"type": "http.request", "body": corpo, "more_body": False}

    return Request(scope, receive)
