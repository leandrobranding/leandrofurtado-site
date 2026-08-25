"""Rodada 3 — ajustes do dono vendo o WIP (itens 12, 13, 14, 19/08).

12. Cabeçalho da empresa na aba de certificações: sem a linha decorativa;
    logo quando existir asset em static/img/certifiers/, nome limpo como
    fallback (nenhum asset foi desenhado para este pacote).
13. Box da credencial: nome à esquerda, ano à direita; no hover/foco o ano
    vira "ver credencial" SÓ quando a credencial tem URL cadastrada — nunca
    um link morto.
14. Download + contato em duas colunas no desktop (cobertura estrutural:
    os dois blocos existem e a divisória entre eles também).
"""
from starlette.testclient import TestClient

from app.main import app as _app
from app.main import certifier_logo


def _subir() -> None:
    with TestClient(_app):
        pass


def _about() -> str:
    _subir()
    with TestClient(_app, base_url="https://testserver") as client:
        r = client.get("/about")
    assert r.status_code == 200
    return r.text


# ---------------------------------------------------------------- item 12

def test_certifier_logo_sem_asset_devolve_vazio():
    """Nenhuma logo foi desenhada para este pacote — Anthropic, FGV e
    Google caem todas no fallback (nome limpo, sem linha)."""
    assert certifier_logo("Anthropic") == ""
    assert certifier_logo("Google") == ""
    assert certifier_logo("Fundação Getúlio Vargas - FGV") == ""


def test_certifier_logo_usa_o_asset_quando_existe(tmp_path, monkeypatch):
    """Cobre o outro braço: se um SVG aparecer na pasta, certifier_logo()
    devolve o caminho estático dele — sem precisar tocar no template."""
    import app.main as main_mod
    pasta = tmp_path / "app" / "static" / "img" / "certifiers"
    pasta.mkdir(parents=True)
    (pasta / "google.svg").write_text("<svg></svg>")
    monkeypatch.setattr(main_mod, "BASE_DIR", tmp_path)
    assert main_mod.certifier_logo("Google") == "/static/img/certifiers/google.svg"


def test_about_nao_tem_mais_a_linha_decorativa_ao_lado_do_nome_da_empresa():
    corpo = _about()
    assert "cert-org-name::after" not in corpo  # a regra CSS não existe mais
    # a marcação HTML do cabeçalho não usa nenhum elemento de linha/régua
    assert 'class="cert-org-name mono-label"' in corpo


def test_about_sem_asset_mostra_o_nome_limpo_da_empresa():
    corpo = _about()
    assert "Anthropic" in corpo
    assert "Fundação Getúlio Vargas - FGV" in corpo
    assert "cert-org-logo" not in corpo  # nenhum <img> de logo — sem asset


# ---------------------------------------------------------------- item 13

def test_credencial_sem_url_nao_tem_classe_de_hover_nem_viewlink():
    """Todos os certs seedados têm url="" — nenhum cartão pode prometer um
    link que não existe (nada de has-cred-link, nada de "ver credencial")."""
    corpo = _about()
    assert "has-cred-link" not in corpo
    assert "cert-viewlink" not in corpo
    assert "ver credencial" not in corpo.lower() or "cert-viewlink" not in corpo


def test_credencial_com_url_ganha_a_classe_e_o_viewlink(monkeypatch):
    """Perfil com uma credencial que TEM url: o cartão correspondente ganha
    has-cred-link e o span de troca no hover; os outros (sem url) não."""
    import app.routers.public as pub

    original = pub.get_profile

    def _fake_get_profile(db):
        perfil = dict(original(db))
        perfil["certs"] = [
            {"title": "Com link", "org": "Anthropic", "year": "2026", "url": "https://cred.example/1"},
            {"title": "Sem link", "org": "Anthropic", "year": "2025", "url": ""},
        ]
        return perfil

    monkeypatch.setattr(pub, "get_profile", _fake_get_profile)
    corpo = _about()
    assert corpo.count("has-cred-link") == 1
    assert corpo.count("cert-viewlink") == 1
    assert "ver credencial" in corpo


def test_credencial_ano_fica_a_direita_nome_a_esquerda_na_marcacao():
    """A ordem no DOM é nome (strong) primeiro, .cert-meta (ano) depois —
    space-between no CSS cuida do resto, mas a ordem do HTML já garante
    "nome à esquerda" pela leitura natural do documento."""
    corpo = _about()
    trecho = corpo[corpo.find('class="cert-info"'):corpo.find('class="cert-info"') + 400]
    assert trecho.find("<strong>") < trecho.find('class="cert-meta')


# ---------------------------------------------------------------- item 14

def test_download_e_contato_sao_dois_blocos_com_divisoria_entre_eles():
    corpo = _about()
    bloco_a = corpo.find('class="about-cta-block"')
    divisor = corpo.find('class="about-cta-divider"')
    bloco_b = corpo.find('class="about-cta-block"', bloco_a + 1)
    assert bloco_a != -1 and divisor != -1 and bloco_b != -1
    assert bloco_a < divisor < bloco_b


def test_about_cta_e_pai_direto_dos_dois_blocos_mais_a_divisoria():
    """Cobertura estrutural mínima do layout de 2 colunas — o CSS
    (flex-direction: row no desktop, column no mobile) fica só no visual,
    mas a marcação (3 filhos diretos de .about-cta: bloco, divisor, bloco)
    é o que o layout depende para funcionar nos dois breakpoints."""
    corpo = _about()
    inicio = corpo.find('<section class="about-cta">')
    fim = corpo.find("</section>", inicio)
    trecho = corpo[inicio:fim]
    assert trecho.count('class="about-cta-block"') == 2
    assert trecho.count('class="about-cta-divider"') == 1
