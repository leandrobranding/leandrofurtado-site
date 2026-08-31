"""Coleta do site original (§4 da spec de Sites).

Nenhum teste toca a rede: `buscar` recebe o cliente por `httpx.MockTransport`,
e `extrair` é função pura sobre uma string de HTML.
"""
import re

import httpx

from app.services import coleta

PAGINA = """
<!doctype html><html lang="pt-BR"><head>
<title>Padaria Aurora | Pães artesanais em Curitiba</title>
<meta name="description" content="Padaria de bairro desde 1998.">
<meta property="og:image" content="/img/fachada.jpg">
</head><body>
<header><img src="/img/logo.svg" alt="Padaria Aurora"></header>
<h2>Nossos produtos</h2>
<ul><li>Pão sovado</li><li>Broa de milho</li><li>Bolo de fubá</li></ul>
<p>Somos uma padaria de bairro desde 1998, com fermentação natural.</p>
<p>Atendemos de Segunda a Sexta, 7h às 19h, e Sábado, 7h às 13h.</p>
<address>Rua das Flores, 210, Curitiba/PR</address>
<a href="https://wa.me/5541999998888">Fale no WhatsApp</a>
<a href="tel:+554133334444">(41) 3333-4444</a>
<a href="mailto:contato@aurora.com.br">contato@aurora.com.br</a>
<a href="https://www.instagram.com/padariaaurora">Instagram</a>
<a href="https://facebook.com/padariaaurora">Facebook</a>
<img src="/img/pao.jpg" alt="Pão"><img src="data:image/gif;base64,R0lGOD" alt="">
<script>var x = "Rua Falsa, 0";</script>
<style>.a{content:"nada"}</style>
</body></html>
"""


def _transporte(html=PAGINA, status=200):
    def responder(request):
        return httpx.Response(status, text=html,
                              headers={"content-type": "text/html; charset=utf-8"})
    return httpx.MockTransport(responder)


# ------------------------------------------------------------- buscar ----

def test_buscar_devolve_html_status_e_cabecalhos():
    """As três coisas juntas porque a ferramenta de análise da próxima spec
    precisa das três, e ela vai chamar ESTA função em vez de baixar o site
    de novo. É por isso que `buscar` e `extrair` são separadas."""
    r = coleta.buscar("padaria.com.br", transporte=_transporte())
    assert r["ok"] is True
    assert r["status"] == 200
    assert "<title>" in r["html"]
    assert r["cabecalhos"]["content-type"].startswith("text/html")
    assert r["url"].startswith("https://")


def test_buscar_recusa_endereco_invalido():
    """Reaproveita `url_valida` de captura.py: só http e https, sempre com
    host. Sem isso, file:// e afins viram porta de leitura de disco."""
    r = coleta.buscar("file:///etc/passwd", transporte=_transporte())
    assert r["ok"] is False and r["erro"]
    assert r["html"] == ""


def test_buscar_sem_rede_nao_estoura():
    def cair(request):
        raise httpx.ConnectError("sem rede")
    r = coleta.buscar("padaria.com.br", transporte=httpx.MockTransport(cair))
    assert r["ok"] is False and r["erro"]


def test_buscar_status_de_erro_nao_e_ok():
    r = coleta.buscar("padaria.com.br", transporte=_transporte(status=503))
    assert r["ok"] is False and r["status"] == 503


# ------------------------------------------------------------ extrair ----

def test_extrai_titulo_e_descricao():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["titulo"] == "Padaria Aurora | Pães artesanais em Curitiba"
    assert d["descricao"] == "Padaria de bairro desde 1998."


def test_extrai_contato_real():
    """É o que faz as chamadas da home funcionarem de verdade (§8)."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "5541999998888" in d["whatsapp"]
    assert "contato@aurora.com.br" in d["emails"]
    assert any("3333" in t for t in d["telefones"])


def test_extrai_endereco_e_horarios():
    """Os dois que mais somem em site ruim, e os dois que o dono mais
    reconhece quando aparecem certos."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "Rua das Flores, 210" in d["endereco"]
    assert any("Sábado" in h or "Segunda" in h for h in d["horarios"])


def test_extrai_redes_sociais_sem_repetir():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["redes"]["instagram"].endswith("padariaaurora")
    assert "facebook" in d["redes"]


def test_extrai_listas_como_servicos():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "Pão sovado" in d["servicos"]
    assert len(d["servicos"]) == 3


def test_extrai_paragrafos_na_ordem_em_que_apareciam():
    """A ordem é informação: ela diz o que o negócio considera mais
    importante, e é ponto de partida da hierarquia da home nova."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["textos"][0].startswith("Somos uma padaria")


def test_nao_extrai_texto_de_script_nem_de_style():
    """Endereço dentro de `<script>` não é endereço, é código. Sem este
    filtro o dossiê enche de lixo e o Leandro perde tempo separando."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    junto = " ".join(d["textos"]) + d["endereco"]
    assert "Rua Falsa" not in junto
    assert "content:" not in junto


def test_imagens_viram_endereco_absoluto_e_data_uri_fica_de_fora():
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert "https://padaria.com.br/img/pao.jpg" in d["imagens"]
    assert not any(i.startswith("data:") for i in d["imagens"])
    assert d["logo"] == "https://padaria.com.br/img/logo.svg"


def test_registra_que_nao_ha_h1():
    """O primeiro achado real dos dois alvos do Leandro: nem grupoom.com.br
    nem brainboxdesign.com.br têm h1. Isso é diagnóstico e é argumento de
    venda, então o dossiê guarda."""
    d = coleta.extrair(PAGINA, "https://padaria.com.br")
    assert d["h1"] == []
    assert "Nossos produtos" in d["h2"]


def test_html_vazio_nao_estoura():
    d = coleta.extrair("", "https://padaria.com.br")
    assert d["titulo"] == "" and d["textos"] == []


def test_html_quebrado_nao_estoura():
    """Site ruim costuma ter HTML ruim, e é justamente o site ruim que este
    serviço existe para ler."""
    d = coleta.extrair("<html><p>solto<div><a href=", "https://x.com.br")
    assert isinstance(d["textos"], list)


def test_acha_contato_dentro_de_div_e_span():
    """Site feito em construtor põe telefone e e-mail em `div`/`span`, nunca
    em `<p>`. Um coletor que só lê `p` fica cego justamente no site ruim que
    ele existe para ler. Medido em 25/08/2026: grupoom.com.br tem dois
    telefones no HTML e a versão anterior deste extrator achava zero."""
    html = ('<div><span>Telefone: (41) 3333-4444</span>'
            '<div>contato@padaria.com.br</div>'
            '<div>Rua das Acacias, 88, Curitiba</div>'
            '<div>Segunda a Sexta, 8h as 18h</div></div>')
    d = coleta.extrair(html, "https://x.com.br")
    assert any("3333" in t for t in d["telefones"])
    assert "contato@padaria.com.br" in d["emails"]
    assert "Acacias" in d["endereco"]
    assert d["horarios"]


def test_paragrafo_com_link_no_meio_nao_perde_o_texto_anterior():
    """`textos` é o ponto de partida da hierarquia da home nova. Frase
    decapitada ali é pior que texto ausente."""
    html = ('<p>Estamos na Rua das Palmeiras, 45, ou '
            '<a href="tel:+554199990000">ligue</a> '
            'para saber mais sobre nossos servicos de panificacao.</p>')
    d = coleta.extrair(html, "https://x.com.br")
    assert d["textos"], "o parágrafo sumiu inteiro"
    assert "Palmeiras" in d["textos"][0]
    assert "Palmeiras" in d["endereco"]


def test_whatsapp_nao_absorve_digito_da_query():
    """Número corrompido numa proposta comercial é pior que número ausente,
    porque parece certo (§4.1: nada inventado)."""
    html = '<a href="https://wa.me/5541999998888?text=Preciso+de+2+paes">Zap</a>'
    d = coleta.extrair(html, "https://x.com.br")
    assert d["whatsapp"] == ["5541999998888"]


def test_endereco_em_bloco_quebrado_por_br_vem_completo():
    """Site semântico põe o endereço num `<p>` só, quebrado por `<br>`.
    Entregar a rua sem bairro nem CEP é pior que não entregar: o Leandro
    escreveria o endereço incompleto na home e o dono notaria."""
    html = ('<p>Rua Jaguariaíva, 596 - 4º andar<br> Alphaville - Pinhais - PR'
            '<br> 83327-076</p>')
    d = coleta.extrair(html, "https://x.com.br")
    assert "Jaguariaíva" in d["endereco"]
    assert "83327-076" in d["endereco"], f"endereço truncado: {d['endereco']!r}"


def test_tag_inline_no_meio_do_paragrafo_nao_decapita_a_frase():
    """`<strong>` dentro de parágrafo é o caso comum, e negrito no meio de
    telefone é padrão de site de PME. Consertar só `<a>` deixava o defeito
    de pé para todas as outras."""
    html = '<p>Ligue: (41) <strong>99999</strong>-8888 para falar com a gente hoje.</p>'
    d = coleta.extrair(html, "https://x.com.br")
    assert d["textos"] and d["textos"][0].startswith("Ligue"), d["textos"]
    assert any("99999" in t for t in d["telefones"]), d["telefones"]


def test_nao_fabrica_telefone_juntando_trechos_distantes():
    """O defeito mais grave que este módulo pode ter (§4.1: nada inventado).

    Até 25/08/2026 a varredura emendava todos os blocos numa string só, e o
    `[\\s.-]?` do regex casava ATRAVÉS da emenda: um número solto no topo da
    página e um "41" no fim de um item lá embaixo viravam um telefone que não
    existe. Um `tel:` errado numa proposta parece certo, e o dono liga para
    descobrir que é o número de outra pessoa."""
    html = ("<div>99998888</div>"
            "<p>Texto de enchimento qualquer so para nao contar como nada aqui.</p>"
            "<li>Atendemos das 8 as 18h de segunda a sexta feira 41</li>")
    d = coleta.extrair(html, "https://x.com.br")
    for numero in d["telefones"]:
        assert numero in re.sub(r"\D", "", html), (
            f"telefone {numero!r} não existe no HTML: foi fabricado na junção")
    assert "4199998888" not in d["telefones"]


def test_telefone_dentro_de_um_bloco_continua_sendo_achado():
    """A rede de segurança do teste acima: varrer bloco a bloco não pode
    fazer o módulo deixar de achar o que está legitimamente lá."""
    html = '<div>Central de atendimento: (41) 3362-1919 e (11) 3044-2215</div>'
    d = coleta.extrair(html, "https://x.com.br")
    assert "4133621919" in d["telefones"]
    assert "1130442215" in d["telefones"]


# -------------------------------------------------------------- colher ---

def test_colher_junta_as_duas_metades():
    d = coleta.colher("padaria.com.br", transporte=_transporte())
    assert d["ok"] is True
    assert d["titulo"].startswith("Padaria Aurora")
    assert d["colhido_em"]


def test_colher_falhando_devolve_dossie_vazio_e_o_erro():
    def cair(request):
        raise httpx.ConnectError("sem rede")
    d = coleta.colher("padaria.com.br", transporte=httpx.MockTransport(cair))
    assert d["ok"] is False and d["erro"]
    assert d["titulo"] == "" and d["telefones"] == []
