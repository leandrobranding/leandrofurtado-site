"""Cobre delete_media_files e a primitiva de apagar exato — hoje sem nenhum
teste, e é por isso que o defeito da capa do case chegou em produção (ver
.superpowers/sdd/2026-08-15-nodal-3-camada-visual/conserto-apagar-familia.md).

Dois modos de apagar, duas situações diferentes:

- delete_media_files: arquivo VELHO que ninguém mais aponta (a capa
  anterior, por exemplo) — varrer a família inteira é o comportamento
  certo, porque nada dela precisa sobreviver.
- apagar_arquivo_exato: arquivo IRMÃO recém-nascido do mesmo envio (o
  original ao lado do WebP otimizado que acabou de virar a capa) — a
  família precisa ser preservada, só o arquivo pedido some.

Os dois testes de família/exato usam disco de verdade, isolado pelo DATA_DIR
que tests/conftest.py já exporta antes de app.config carregar.
"""
from app.config import settings
from app.services.images import apagar_arquivo_exato, delete_media_files


def _familia(tmp_subdir: str, prefixo: str) -> list:
    """Cria no disco de teste os arquivos de uma família de upload: o
    original e as quatro variantes da escada, com o sufixo de hash de 8
    caracteres que save_upload carimba em todo envio."""
    pasta = settings.upload_dir / tmp_subdir
    pasta.mkdir(parents=True, exist_ok=True)
    nomes = [
        f"{prefixo}.png",
        f"{prefixo}-480.webp",
        f"{prefixo}-960.webp",
        f"{prefixo}-1600.webp",
        f"{prefixo}-2400.webp",
        f"{prefixo}-1600-og.jpg",
    ]
    caminhos = [pasta / n for n in nomes]
    for c in caminhos:
        c.write_bytes(b"conteudo de teste")
    return caminhos


def test_delete_media_files_apaga_a_familia_inteira():
    """Trava o comportamento que PRECISA continuar existindo: apagar uma
    capa antiga leva junto as seis variantes que vieram do mesmo envio —
    senão trocar de capa várias vezes enche a pasta de uploads de lixo."""
    caminhos = _familia("caso-familia", "foto-ab12ef34")

    delete_media_files(f"caso-familia/{caminhos[0].name}")

    for c in caminhos:
        assert not c.exists(), f"{c.name} devia ter sido varrido com a família"


def test_delete_media_files_sem_sufixo_de_hash_apaga_so_o_pedido():
    """Arquivo semeado à mão, sem o sufixo aleatório de save_upload, não tem
    família comprovada — varrer por prefixo aqui destruiria um vizinho de
    nome parecido só para economizar disco."""
    pasta = settings.upload_dir / "caso-manual"
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / "logo.png"
    vizinho = pasta / "logo-960.webp"
    alvo.write_bytes(b"x")
    vizinho.write_bytes(b"x")

    delete_media_files("caso-manual/logo.png")

    assert not alvo.exists()
    assert vizinho.exists(), "sem sufixo de hash, não é família comprovada"


def test_apagar_arquivo_exato_preserva_os_irmaos():
    """A primitiva nova: apaga só o arquivo pedido, mesmo quando ele tem o
    sufixo de hash que faria delete_media_files varrer tudo em volta."""
    caminhos = _familia("caso-exato", "foto-cd56ab78")
    original = caminhos[0]

    apagar_arquivo_exato(f"caso-exato/{original.name}")

    assert not original.exists(), "o arquivo pedido precisa sumir"
    for irmao in caminhos[1:]:
        assert irmao.exists(), f"{irmao.name} não devia ter sido tocado"


def test_apagar_arquivo_exato_nao_sai_da_pasta_de_uploads():
    """Mesma trava de segurança de delete_media_files: caminho relativo que
    escapa da pasta de uploads (../../etc/passwd) é ignorado, não seguido."""
    fora = settings.upload_dir.parent / "fora-do-upload.txt"
    fora.write_bytes(b"nao pode sumir")
    try:
        apagar_arquivo_exato("../fora-do-upload.txt")
        assert fora.exists()
    finally:
        fora.unlink(missing_ok=True)
