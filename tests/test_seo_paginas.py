"""SEO impecável (pacote de lançamento, item 4, 19/08).

O grosso do SEO (canonical, hreflang, OG/Twitter, JSON-LD Person+WebSite)
já vinha pronto em base.html — este pacote fecha as pontas soltas: alt
inteligente no card de destaque da home (que usava só o título, sem o
cliente), e a palavra-chave de contratação "direção criativa" nos metas
globais, sem virar keyword stuffing.
"""
import asyncio

from starlette.requests import Request

from app.i18n import STRINGS
from app.models import Case, Category
from app.routers.public import home


def _get(lang: str = "pt") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "raw_path": b"/", "query_string": b"", "headers": [],
        "state": {"clean_path": "/", "lang": lang}, "session": {},
    }

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receber)


def test_card_de_destaque_da_home_usa_alt_inteligente_com_o_cliente(db):
    """Antes o <img> do card levava só o título do case; alt_de() acrescenta o
    cliente quando existe, o mesmo padrão já usado no portfólio e no case."""
    cat = Category(slug="branding", name_pt="Branding", name_en="Branding")
    db.add(cat)
    db.flush()
    db.add(Case(slug="marca-x", title_pt="Case Marca X", category_id=cat.id,
                client="Cliente Exemplo", cover_image="x.jpg",
                published=True, archived=False, featured=True))
    db.commit()

    resp = asyncio.run(home(_get("pt"), db))
    corpo = resp.body.decode()
    assert 'alt="Case Marca X para Cliente Exemplo"' in corpo


def test_meta_desc_tem_a_palavra_chave_direcao_criativa_sem_stuffing():
    pt = STRINGS["pt"]["meta_desc"]
    en = STRINGS["en"]["meta_desc"]
    assert "direção criativa" in pt.lower()
    assert "creative direction" in en.lower()
    # honesto, não empilhado: a mesma palavra não se repete dentro do próprio meta
    assert pt.lower().count("direção criativa") == 1
    assert en.lower().count("creative direction") == 1


def test_sameas_inclui_o_perfil_da_empresa_no_google():
    """23/08/2026: o Perfil da Empresa foi verificado e entrou no `sameAs`.

    É o que diz ao Google, explicitamente, que leandrofurtado.com.br e aquele
    perfil são a MESMA entidade. Sem a declaração ele infere pela coincidência
    de nome e endereço, que é sinal mais fraco e demora mais.

    O teste guarda a ligação nos dois pontos onde ela pode se perder: a chave
    tem que continuar salvável pelo painel, e tem que continuar entrando na
    lista do JSON-LD.
    """
    from app.routers.admin import SETTING_KEYS
    assert "social_google" in SETTING_KEYS, "o painel deixou de salvar o campo"

    from app.config import BASE_DIR
    base = (BASE_DIR / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    linha = [l for l in base.splitlines() if "set links" in l]
    assert linha, "o bloco sameAs sumiu do base.html"
    assert "site.social_google" in linha[0], "o Google saiu do sameAs"


# ------------------------------------------------- ordem do reposicionamento --
#
# 24/08/2026. O site nasceu portfólio de direção de arte e virou vitrine de
# engenharia, e a virada aconteceu campo a campo ao longo de uma semana:
# currículo, LinkedIn, competências, README do GitHub. O `meta_title` foi o
# último a mudar, e era o pior lugar para ficar para trás — é a primeira linha
# que o Google desenha. Estes testes existem para que a ordem não volte sozinha
# num ajuste futuro de palavra-chave.

def test_o_titulo_do_site_comeca_pela_engenharia_nos_dois_idiomas():
    pt = STRINGS["pt"]["meta_title"].lower()
    en = STRINGS["en"]["meta_title"].lower()
    assert pt.index("engenheiro de ia") < len(pt)
    assert "diretor de arte" not in pt, "a ordem antiga voltou ao título em pt"
    assert en.index("ai engineer") < len(en)
    assert "art director" not in en, "a ordem antiga voltou ao título em en"


def test_a_direcao_de_arte_continua_na_descricao():
    """Inverter a ordem não é apagar dez anos: a direção de arte é o que traz
    cliente de projeto, que é a receita de hoje. Ela sai da primeira linha e
    continua na descrição, no /about e em toda página de case."""
    assert "direção de arte" in STRINGS["pt"]["meta_desc"].lower()
    assert "art direction" in STRINGS["en"]["meta_desc"].lower()


def test_a_cidade_continua_no_titulo_em_portugues():
    """Curitiba é o termo que traz busca local, tanto de cliente quanto de
    recrutador da região. Foi o motivo de o cargo completo ter saído do título
    em primeiro lugar, e continua valendo."""
    assert "Curitiba" in STRINGS["pt"]["meta_title"]


def test_titulo_e_descricao_cabem_no_que_o_google_desenha():
    from app.services.seo import LIMITE_DESCRICAO, LIMITE_TITULO, _visivel
    for lang in ("pt", "en"):
        titulo = STRINGS[lang]["meta_title"]
        desc = STRINGS[lang]["meta_desc"]
        assert _visivel(titulo) <= LIMITE_TITULO, f"{lang}: título com {_visivel(titulo)}"
        assert _visivel(desc) <= LIMITE_DESCRICAO, f"{lang}: descrição com {_visivel(desc)}"
