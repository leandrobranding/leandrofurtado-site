"""Rodada 3, item 4 (19/08) — área de download redesenhada.

DOCX morreu por decisão do dono ("pdf é universal"): a rota só serve PDF, e
qualquer outro `fmt` é 404 — não existe mais um branch DOCX escondido. O
idioma virou escolha explícita do usuário (dois botões "Português"/"English"
em /about, cada um mandando ?lang=pt|en) em vez de seguir o idioma da
página; sem o parâmetro (ou com um valor estranho), cai no idioma da página
atual como default sensato.
"""
from starlette.testclient import TestClient

from app.main import app as _app


def _subir() -> None:
    with TestClient(_app):
        pass


def test_docx_e_404():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/cv/download.docx")
    assert r.status_code == 404


def test_qualquer_formato_fora_de_pdf_e_404():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/cv/download.rtf")
    assert r.status_code == 404


def test_lang_query_pt_gera_o_pdf_em_portugues():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/cv/download.pdf?lang=pt")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "Leandro-Furtado-CV.pdf" in r.headers["content-disposition"]
    assert "-EN" not in r.headers["content-disposition"]


def test_lang_query_en_gera_o_pdf_em_ingles_com_sufixo_no_nome():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/cv/download.pdf?lang=en")
    assert r.status_code == 200
    assert "Leandro-Furtado-CV-EN.pdf" in r.headers["content-disposition"]


def test_sem_lang_na_query_usa_o_idioma_da_pagina_atual():
    """Quem chega direto em /cv/download.pdf (sem escolher) ou em
    /en/cv/download.pdf recebe o idioma da página como default sensato."""
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r_pt = client.get("/cv/download.pdf")
        r_en = client.get("/en/cv/download.pdf")
    assert "Leandro-Furtado-CV.pdf" in r_pt.headers["content-disposition"]
    assert "Leandro-Furtado-CV-EN.pdf" in r_en.headers["content-disposition"]


def test_lang_query_invalida_cai_no_idioma_da_pagina_em_vez_de_quebrar():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/cv/download.pdf?lang=fr")
    assert r.status_code == 200
    assert "Leandro-Furtado-CV.pdf" in r.headers["content-disposition"]


def test_lang_query_invalida_e_normalizada_nao_repassada_direto(monkeypatch):
    """Não basta o nome do arquivo dar certo por coincidência (um idioma
    inválido sem conteúdo "_fr" já degrada pra "_pt" dentro de build_pdf) —
    trava o valor de verdade que chega em build_pdf: precisa ser "pt", não
    "fr" repassado como veio da query."""
    _subir()
    import app.services.resume as resume_mod
    original = resume_mod.build_pdf
    capturado = {}

    def _espiao(profile, lang):
        capturado["lang"] = lang
        return original(profile, lang if lang in ("pt", "en") else "pt")

    monkeypatch.setattr(resume_mod, "build_pdf", _espiao)
    with TestClient(_app, base_url="https://testserver") as client:
        client.get("/cv/download.pdf?lang=fr")
    assert capturado["lang"] == "pt"


def test_lang_da_query_manda_mais_que_o_idioma_da_pagina():
    """O pedido do dono: escolha explícita do usuário, não mais o idioma que
    a página estava — mesmo em /en/about, pedir ?lang=pt tem que valer."""
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/en/cv/download.pdf?lang=pt")
    assert "Leandro-Furtado-CV.pdf" in r.headers["content-disposition"]
    assert "-EN" not in r.headers["content-disposition"]


def test_about_nao_tem_mais_botao_de_docx():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    assert r.status_code == 200
    assert "cv/download.docx" not in r.text
    assert "DOCX" not in r.text


def test_about_tem_os_dois_botoes_de_idioma_explicitos():
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    corpo = r.text
    assert "cv/download.pdf?lang=pt" in corpo
    assert "cv/download.pdf?lang=en" in corpo
    assert "Português" in corpo
    assert "English" in corpo
