"""Upload seguro + otimização de mídia.

Imagens são validadas com Pillow e ganham uma variante WebP otimizada.
Vídeos/áudios são validados por extensão e tamanho.
"""
import re
import secrets
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

from ..config import settings

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
ALLOWED = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

CHUNK = 1024 * 1024


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or secrets.token_hex(4)


def kind_for(ext: str) -> str:
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return "audio"


async def save_upload(file: UploadFile, subdir: str) -> tuple[str, str, str]:
    """Salva o upload validado. Retorna (kind, caminho relativo, thumb relativo)."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Formato não permitido: {ext or 'sem extensão'}")

    dest_dir = settings.upload_dir / slugify(subdir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(Path(file.filename or "arquivo").stem)[:60]
    name = f"{stem}-{secrets.token_hex(4)}{ext}"
    dest = dest_dir / name

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"Arquivo maior que {settings.max_upload_mb}MB")
            out.write(chunk)

    kind = kind_for(ext)
    rel = str(dest.relative_to(settings.upload_dir))
    thumb_rel = ""

    if kind == "image" and ext != ".gif":
        try:
            with Image.open(dest) as img:
                img.verify()  # arquivo realmente é uma imagem?
            thumb_rel = gerar_escada(dest)
        except HTTPException:
            raise
        except Exception:
            dest.unlink(missing_ok=True)
            raise HTTPException(400, "Imagem inválida ou corrompida")

    return kind, rel, thumb_rel


async def save_pdf(file: UploadFile, dest_dir: Path) -> str:
    """Salva um PDF validado dentro de `dest_dir`. Devolve só o NOME do
    arquivo gravado — quem chama decide o prefixo que a URL usa (`/media/…`
    para o público, `/nodal-privado/…` para o privado do Nodal); esta
    função não sabe qual dos dois é, e não precisa saber.

    Não reaproveita `save_upload`: PDF não passa pelo Pillow, não ganha
    escada de WebP, e `save_upload` nem reconhece a extensão — `kind_for`
    cairia em "audio" por eliminação, silenciosamente errado. Uma função
    própria, mais simples, em vez de um `if` a mais dentro da que já existe.

    Mesmo teto de tamanho (`settings.max_upload_mb`) e o mesmo nome
    anti-colisão (slug do nome original + token hex) de `save_upload` —
    duas cópias da MESMA regra de nomear arquivo, não duas regras
    diferentes por acidente.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext != ".pdf":
        raise HTTPException(400, f"Formato não permitido: {ext or 'sem extensão'}. Só PDF.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(Path(file.filename or "arquivo").stem)[:60]
    name = f"{stem}-{secrets.token_hex(4)}{ext}"
    dest = dest_dir / name

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"Arquivo maior que {settings.max_upload_mb}MB")
            out.write(chunk)

    return name


def gerar_escada(dest: Path) -> str:
    """Gera as versões em WebP de uma imagem já salva. Devolve a de exibição.

    O original fica onde está: é o arquivo do trabalho, e não cabe ao site
    apagá-lo. O que muda é que ele deixa de ser o que trafega. Antes o card de
    503px recebia 1920px e o modal abria o PNG original, que num dos cases tem
    7MB.

    Versão que já existe não é refeita, então rodar isto de novo numa pasta
    inteira custa só a leitura dos nomes.
    """
    from .responsivo import CHEIA, LARGURAS

    with Image.open(dest) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        largura_real = img.width
        exibicao = ""
        for alvo in (*LARGURAS, CHEIA):
            saida = dest.parent / f"{dest.stem}-{alvo}.webp"
            # Imagem menor que o degrau não é ampliada. A exceção é a versão do
            # modal: ela existe sempre, nem que seja do tamanho do original,
            # senão o modal cai no arquivo bruto. Era o caso de um PNG de
            # 1920px e 2,2MB que continuava sendo aberto inteiro.
            if alvo > largura_real and alvo not in (LARGURAS[0], CHEIA):
                continue
            if not saida.exists():
                copia = img.copy()
                copia.thumbnail((alvo, alvo * 4), Image.LANCZOS)
                copia.save(saida, "WEBP", quality=82, method=6)
            if alvo == 1600 or (not exibicao and alvo == LARGURAS[-1]):
                exibicao = str(saida.relative_to(settings.upload_dir))
        if not exibicao:
            # imagem pequena: a maior versão gerada vira a de exibição
            for alvo in reversed(LARGURAS):
                saida = dest.parent / f"{dest.stem}-{alvo}.webp"
                if saida.exists():
                    exibicao = str(saida.relative_to(settings.upload_dir))
                    break
    return exibicao


# nome de família: termina com o sufixo aleatório de 4 bytes de save_upload
_FAMILIA = re.compile(r"-[0-9a-f]{8}$")


def delete_media_files(*rels: str) -> None:
    """Apaga um arquivo e a família dele: as versões da escada e o cartão de OG.

    Uma imagem enviada vira seis arquivos — o original, quatro WebP da escada e
    o JPEG de compartilhamento. O que fica gravado no banco é um só, a versão de
    exibição. Apagar só esse deixava os outros cinco no disco para sempre, e
    trocar a capa de um case algumas vezes ia enchendo a pasta de arquivos que
    nada mais aponta.

    O parentesco é o nome: `foto-ab12-1600.webp`, `foto-ab12-480.webp` e
    `foto-ab12-1600-og.jpg` descendem todos de `foto-ab12`. O sufixo aleatório
    de quatro bytes que save_upload põe em cada envio garante que esse prefixo
    não colida com o de outra imagem.

    Cuidado: o original e o thumb de UM MESMO save_upload também são
    "família" um do outro, pelo mesmo motivo. Apagar o original de um envio
    que acabou de acontecer com esta função leva o thumb junto — mesmo que o
    thumb já esteja gravado no banco. Para esse caso use apagar_arquivo_exato,
    logo abaixo: o porquê das duas funções existirem está no docstring dela.
    """
    from .responsivo import CHEIA, LARGURAS  # import local, como em gerar_escada

    raiz = settings.upload_dir.resolve()
    for rel in rels:
        if not rel:
            continue
        path = (settings.upload_dir / rel).resolve()
        if raiz not in path.parents:
            continue  # nunca apagar fora da pasta de uploads

        # tira o sufixo de tamanho para chegar ao nome de família
        base = path.stem
        for suf in ("-og",):
            if base.endswith(suf):
                base = base[: -len(suf)]
        for largura in LARGURAS + (CHEIA,):
            if base.endswith(f"-{largura}"):
                base = base[: -len(f"-{largura}")]
                break

        # Varrer por prefixo só é seguro quando o prefixo é único, e quem
        # garante isso é o sufixo aleatório que save_upload carimba em todo
        # envio. Sem ele — arquivo antigo, semeado à mão — apaga só o que foi
        # pedido: levar junto um vizinho de nome parecido seria destruir
        # trabalho para economizar disco.
        if not _FAMILIA.search(base):
            if path.is_file():
                path.unlink(missing_ok=True)
            continue

        for irmao in (*path.parent.glob(f"{base}.*"), *path.parent.glob(f"{base}-*")):
            if irmao.is_file():
                irmao.unlink(missing_ok=True)


def apagar_arquivo_exato(rel: str) -> None:
    """Apaga só o arquivo pedido — nunca a família dele.

    Existem dois modos de apagar neste módulo porque existem duas situações
    diferentes, e confundi-las é o defeito que motivou esta função:

    - delete_media_files, acima, varre a família inteira. É o que se quer
      para um arquivo VELHO que ninguém mais aponta — a capa anterior de um
      case, por exemplo — porque nada das seis variantes precisa sobreviver.
    - apagar_arquivo_exato, aqui, apaga um arquivo só. É o que se quer para
      um arquivo IRMÃO recém-nascido do MESMO envio: save_upload devolve
      (kind, rel, thumb) em que `rel` (o original) e `thumb` (a variante
      otimizada da escada) nascem juntos e carregam o mesmo sufixo de hash
      de 8 caracteres — a mesma "família" que delete_media_files varre.
      Quando só a variante otimizada é gravada no banco (`case.cover_image
      = thumb or rel`) e o original devia sumir, chamar delete_media_files
      nele apaga a família inteira, inclusive o `thumb` que acabou de virar
      a capa. Reproduzido com arquivo real: 5 arquivos no disco depois do
      upload, zero depois da chamada, e o banco apontando para um arquivo
      que não existe mais (ver o relatório em .superpowers/sdd/
      2026-08-15-nodal-3-camada-visual/conserto-apagar-familia.md).

    Se alguém um dia juntar as duas numa função só "para simplificar", o
    defeito acima volta. Não junte.
    """
    if not rel:
        return
    raiz = settings.upload_dir.resolve()
    path = (settings.upload_dir / rel).resolve()
    if raiz not in path.parents:
        return  # nunca apagar fora da pasta de uploads
    if path.is_file():
        path.unlink(missing_ok=True)
