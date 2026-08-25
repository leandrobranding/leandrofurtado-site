"""Capa de case pela API de conteúdo, fim a fim, com disco de verdade.

Mesmo defeito da capa do case no painel (ver
.superpowers/sdd/2026-08-15-nodal-3-camada-visual/conserto-apagar-familia.md),
achado por varredura depois do primeiro conserto: `app/routers/api.py`,
rota `POST /api/v1/cases/{slug}/capa` (função `upload_cover`), tinha o
mesmo `if thumb: delete_media_files(rel)` — apaga a variante otimizada do
MESMO envio um instante depois de ela virar `case.cover_image`. Essa rota
está montada em produção (é a que este agente usa para publicar case sem
o Leandro precisar mexer no painel), então o defeito ali apagava a capa no
instante em que a gravava, exatamente como no formulário do painel.

`upload_cover` recebe o arquivo como `UploadFile` direto (parâmetro da
própria função), não via `request.form()` — não precisa de multipart de
verdade, só de um UploadFile de verdade (ver arquivo_upload).
"""
import asyncio

from app.config import settings
from app.models import Case
from app.routers.api import upload_cover

from ._multipart_de_verdade import arquivo_upload


def test_capa_pela_api_grava_e_apaga_no_disco_de_verdade(db):
    """O caminho que case.cover_image recebe pela rota da API precisa
    existir no disco depois de salvar."""
    case = Case(slug="case-api", title_pt="Case via API")
    db.add(case)
    db.commit()

    asyncio.run(upload_cover(slug=case.slug, db=db, _=None,
                             file=arquivo_upload("red", "capa.png")))

    assert case.cover_image, "a capa precisa ter sido gravada no case"
    caminho = settings.upload_dir / case.cover_image
    assert caminho.is_file(), (
        f"case.cover_image aponta para {case.cover_image}, "
        "que não existe no disco depois de salvar"
    )
