"""Redesenho do currículo em PDF (Rodada 3, item 5, 19/08).

Cobertura estrutural do gerador (app/services/resume.py) — a diagramação em
si (hierarquia, grid editorial, fontes da casa) foi conferida visualmente
página a página, convertendo os PDFs gerados em imagem (ver relatório); aqui
trava o que é razoável testar automatizado: não quebra com perfis variados,
fontes da casa embutidas de verdade, DOCX morreu, Instagram fora do
currículo, foto degrada elegante sem quebrar.
"""
from app.services.resume import _photo_stream, build_pdf
from app.services.seeds import PROFILE


def test_pdf_pt_e_en_sao_pdfs_validos():
    for lang in ("pt", "en"):
        data = build_pdf(PROFILE, lang)
        assert data.startswith(b"%PDF-")
        assert len(data) > 20_000  # um PDF vazio/quebrado não passa de poucos KB


def test_pdf_nao_quebra_com_perfil_vazio():
    for lang in ("pt", "en"):
        data = build_pdf({}, lang)
        assert data.startswith(b"%PDF-")


def test_pdf_nao_quebra_com_perfil_minimo_so_nome_e_um_cargo():
    minimo = {
        "name": "Ana Souza",
        "title_pt": "Designer",
        "experience": [{"company": "Empresa X", "role_pt": "Designer Jr", "period": "2020 — 2021"}],
    }
    data = build_pdf(minimo, "pt")
    assert data.startswith(b"%PDF-")


def test_pdf_nao_quebra_com_nome_titulo_e_link_extremamente_longos():
    """A causa raiz do bug real encontrado na primeira geração: URLs
    completas e nome/título compridos estouravam a largura da página com
    `cell()` (não quebra linha) — hoje é `multi_cell` em tudo isso."""
    extremo = {
        "name": "Maria Das Graças Fernandes De Oliveira E Silva Junior Sobrenome Bem Comprido Mesmo",
        "title_pt": ("Diretora de Arte Sênior, Engenheira de Inteligência Artificial Aplicada e "
                     "Especialista em Fluxos Criativos com Inteligência Artificial Generativa"),
        "links": {"linkedin": "https://www.linkedin.com/in/um-usuario-com-nome-extremamente-longo-mesmo/"},
    }
    data = build_pdf(extremo, "pt")
    assert data.startswith(b"%PDF-")


def test_titulo_do_documento_tem_nome_e_cargo():
    """/Title vai no dicionário do PDF em UTF-16BE hex — decodifica pra
    conferir que carrega o nome (sem exigir suporte a texto comprimido)."""
    data = build_pdf(PROFILE, "pt")
    inicio = data.find(b"/Title <")
    assert inicio != -1
    fim = data.find(b">", inicio)
    hexstr = data[inicio + len("/Title <"):fim].decode("ascii")
    texto = bytes.fromhex(hexstr).decode("utf-16-be")
    assert PROFILE["name"] in texto


def test_docx_nao_existe_mais_no_modulo():
    import app.services.resume as resume_mod
    assert not hasattr(resume_mod, "build_docx")


def test_instagram_fora_do_pdf_linkedin_e_whatsapp_ficam():
    """Ajuste do dono, 19/08: rede social criativa não soma pro recrutador
    de currículo de dev/engenharia de IA."""
    from app.services.resume import _fields
    d = _fields(PROFILE, "pt")
    assert "instagram" not in d
    assert d["linkedin"]
    assert d["whatsapp"]


# ---------------------------------------------------------------- foto

def test_photo_stream_sem_foto_cadastrada_devolve_none():
    assert _photo_stream("") is None
    assert _photo_stream(None) is None


def test_photo_stream_arquivo_inexistente_devolve_none_sem_quebrar():
    assert _photo_stream("nao-existe-de-jeito-nenhum.webp") is None


def test_pdf_com_foto_cadastrada_mas_arquivo_ausente_nao_quebra():
    """Profile.photo aponta pra um nome de arquivo que não existe no
    DATA_DIR deste ambiente (comum em teste/dev) — o cabeçalho tem que
    degradar pro layout só-texto, nunca estourar."""
    perfil = dict(PROFILE)
    perfil["photo"] = "arquivo-que-nao-existe.webp"
    data = build_pdf(perfil, "pt")
    assert data.startswith(b"%PDF-")


def test_photo_stream_converte_webp_real_em_jpeg_em_memoria(tmp_path, monkeypatch):
    """Ponta a ponta do braço "COM foto": grava um WebP de verdade (Pillow
    já é dependência), aponta settings.upload_dir pra lá, confirma que
    _photo_stream devolve bytes de um JPEG válido (assinatura JFIF)."""
    from PIL import Image
    import app.config as config_mod

    img = Image.new("RGB", (400, 250), (120, 80, 40))
    caminho = tmp_path / "avatar-teste.webp"
    img.save(caminho, format="WEBP")

    monkeypatch.setattr(type(config_mod.settings), "upload_dir",
                         property(lambda self: tmp_path))

    buf = _photo_stream("avatar-teste.webp")
    assert buf is not None
    conteudo = buf.read()
    assert conteudo[:2] == b"\xff\xd8"  # assinatura JPEG


def test_pdf_com_foto_real_embutida_nao_quebra_e_cresce_de_tamanho(tmp_path, monkeypatch):
    from PIL import Image
    import app.config as config_mod

    img = Image.new("RGB", (400, 400), (60, 60, 60))
    (tmp_path / "avatar-teste.webp").write_bytes(b"")  # garante o arquivo, sobrescrito abaixo
    img.save(tmp_path / "avatar-teste.webp", format="WEBP")
    monkeypatch.setattr(type(config_mod.settings), "upload_dir",
                         property(lambda self: tmp_path))

    perfil = dict(PROFILE)
    perfil["photo"] = "avatar-teste.webp"
    sem_foto = build_pdf(PROFILE, "pt")
    com_foto = build_pdf(perfil, "pt")
    assert com_foto.startswith(b"%PDF-")
    assert len(com_foto) > len(sem_foto)  # a imagem embutida pesa
