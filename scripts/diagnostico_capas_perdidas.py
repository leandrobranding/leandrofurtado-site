"""Diagnóstico: quais campos de imagem no banco apontam para arquivo que não
existe mais no disco.

Motivo de existir: o defeito descrito em .superpowers/sdd/
2026-08-15-nodal-3-camada-visual/conserto-apagar-familia.md apagava, desde
que os dois commits envolvidos se encontraram, o arquivo que acabara de ser
gravado como capa de case (e, pelo mesmo padrão, a prévia do site enviada à
mão). O banco continuou de pé com um caminho que não existe mais — nada no
salvamento acusava o problema, e a imagem só quebrava quando alguém abria a
página. Este script varre banco e disco para achar, sem adivinhar, quais
registros já estão nesse estado.

SÓ LÊ. Não apaga, não conserta, não grava nada em lugar nenhum — nem no
banco, nem no disco, nem em arquivo de saída. O que fizer com cada capa
perdida (recuperar de outro lugar, limpar o campo, subir de novo) é decisão
de quem lê o relatório, não deste script.

Uso:
    .venv/bin/python scripts/diagnostico_capas_perdidas.py

Por padrão lê o banco e a pasta de upload que app.config resolve a partir do
.env do processo (o mesmo que o site usa em produção). Para apontar para
outro lugar — por exemplo, para conferir uma cópia do banco de produção sem
tocar no `data/` deste checkout — exporte DATA_DIR antes de rodar:

    DATA_DIR=/caminho/para/uma/copia .venv/bin/python scripts/diagnostico_capas_perdidas.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Case, MediaItem, Profile  # noqa: E402
from app.nodal.models import Curso  # noqa: E402


def _existe(rel: str) -> bool:
    """True se o caminho relativo existir dentro da pasta de upload.

    Só leitura: is_file() não cria, não abre para escrita, não move nada.
    """
    if not rel:
        return True  # campo vazio não é capa perdida, é capa que nunca existiu
    caminho = settings.upload_dir / rel
    return caminho.is_file()


def _relativo(bruto: str) -> str:
    """Os caminhos no banco ora vêm com o prefixo `/media/` (Nodal, que grava
    pronto para <img src>), ora sem ele (cases, que gravam relativo à pasta
    de upload). Normaliza para o formato que settings.upload_dir espera."""
    return bruto.removeprefix("/media/") if bruto else bruto


def diagnosticar() -> list[tuple[str, str]]:
    """Devolve [(descrição do registro, caminho ausente), ...]. Não modifica
    nada — abre a sessão só para consultar (nenhum add/delete/commit)."""
    perdidos: list[tuple[str, str]] = []
    db = SessionLocal()
    try:
        for case in db.query(Case).all():
            candidatos = [
                ("cover_image (capa)", case.cover_image),
                ("cover_video (vídeo de capa)", case.cover_video),
                ("seo_image (compartilhamento)", case.seo_image),
                ("site_shot (captura automática)", case.site_shot),
            ]
            for campo, bruto in candidatos:
                rel = _relativo(bruto)
                if rel and not _existe(rel):
                    perdidos.append(
                        (f"case #{case.id} ({case.slug or 'sem slug'}) — {campo}", rel))

        for item in db.query(MediaItem).all():
            if item.kind == "embed":
                continue  # src de embed é URL de terceiro, não arquivo em uploads
            for campo, bruto in (("src", item.src), ("thumb", item.thumb)):
                rel = _relativo(bruto)
                if rel and not _existe(rel):
                    perdidos.append((
                        f"media_item #{item.id} (case #{item.case_id}) — {campo}", rel))

        perfil = db.get(Profile, 1)
        if perfil and perfil.data:
            for campo in ("photo", "cover"):
                bruto = str(perfil.data.get(campo, "") or "")
                rel = _relativo(bruto)
                if rel and not _existe(rel):
                    perdidos.append((f"profile — {campo}", rel))

        for curso in db.query(Curso).all():
            rel = _relativo(curso.capa)
            if rel and not _existe(rel):
                perdidos.append((
                    f"nodal_curso #{curso.id} ({curso.slug or 'sem slug'}) — capa", rel))
    finally:
        db.close()  # nenhum commit — a sessão só leu
    return perdidos


def main() -> None:
    print(f"Banco:  {settings.db_url}")
    print(f"Uploads: {settings.upload_dir}")
    print()

    perdidos = diagnosticar()
    if not perdidos:
        print("Nada encontrado: todo caminho gravado no banco existe no disco.")
        return

    print(f"{len(perdidos)} referência(s) para arquivo ausente:\n")
    for descricao, rel in perdidos:
        print(f"  - {descricao}\n    caminho ausente: {rel}")
    print("\nEste script não alterou nada. A decisão sobre cada item acima "
          "(recuperar, limpar o campo, subir de novo) fica para quem for agir.")


if __name__ == "__main__":
    main()
