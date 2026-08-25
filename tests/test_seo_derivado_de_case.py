"""Título e descrição de case derivados do conteúdo (services/seo.py, 22/08/2026).

O que esses testes protegem, e por que cada um existe:

O SERP foi medido em 22/08/2026 e mostrava, para 24 páginas de case, títulos
sem o nome do cliente e descrições de 42 a 50 caracteres onde o Google desenha
~155. Dois terços do espaço vazios em 85% do site.

A correção não foi escrever 24 textos à mão: `apply_case_form` recalcula o SEO
a cada save (decisão registrada lá, para não ter formulário de SEO), então
texto manual seria apagado no save seguinte. A correção foi trocar a FÓRMULA.
Estes testes existem para que a fórmula não regrida sem alguém perceber.
"""
from app.services.seo import (LIMITE_DESCRICAO, LIMITE_TITULO,
                              _visivel, descricao_de_cliente,
                              descricao_para_busca, titulo_para_busca)

# Casos reais do banco em 22/08/2026: título, cliente, categoria, ano, subtítulo.
REAIS = [
    ("Linha Celebre 100 Anos", "Electrolux", "Live Marketing", "2026",
     "Evento de 100 Anos da Linha Celebre de Electrolux."),
    ("Junte Seus Heróis Marvel", "Coca-Cola", "Live Marketing", "2024",
     "Ativação Coca-Cola e Marvel na Convenção Shell"),
    ("Sucesso sem fronteiras", "DAF", "Key Visual", "2025",
     "Key visual para evento de Live Marketing da DAF Caminhões"),
    ("Dia do profissional do Secretariado", "Hospital Marcelino Champagnat",
     "Live Marketing", "2025",
     "Ação para o dia do(a) Secretário(a) no Hospital Marcelino Champagnat"),
    ("Primeira conta", "Bradesco", "Live Marketing", "2026",
     "A Primeira Conta é um evento itinerante que transforma a abertura da "
     "primeira conta bancária em cerimônia real."),
    ("Wandy Luz", "Wandy Luz", "Identidade Visual", "",
     "Identidade visual e marca pessoal"),
]


# ---------------------------------------------------------------- orçamento --

def test_nenhum_titulo_real_estoura_o_corte_do_google():
    for titulo, cliente, _, _, _ in REAIS:
        saida = titulo_para_busca(titulo, cliente)
        assert _visivel(saida) <= LIMITE_TITULO, saida


def test_nenhuma_descricao_real_estoura_o_corte_do_google():
    for _, cliente, cat, ano, sub in REAIS:
        saida = descricao_para_busca(sub, cat, cliente, ano)
        assert _visivel(saida) <= LIMITE_DESCRICAO, saida


def test_o_seletor_invisivel_nao_conta_no_orcamento():
    """U+FE0E ocupa um code point e nenhum pixel. Contar ele faria a fórmula
    desistir da marca cedo demais e devolver títulos mais pobres que o
    necessário."""
    assert _visivel("a ·︎ b") == len("a · b")


# ------------------------------------------------------------------ título --

def test_titulo_ganha_o_cliente_na_frente():
    """O nome do cliente é o termo com volume de busca ("campanha electrolux
    100 anos"). Sem ele o título não é achável por quem não conhece o Leandro."""
    assert titulo_para_busca("Linha Celebre 100 Anos", "Electrolux") == \
        "Electrolux ·︎ Linha Celebre 100 Anos ·︎ Leandro Furtado"


def test_titulo_nao_repete_cliente_que_ja_esta_no_titulo():
    saida = titulo_para_busca("Wandy Luz", "Wandy Luz")
    assert saida.count("Wandy Luz") == 1
    assert saida == "Wandy Luz ·︎ Leandro Furtado"


def test_titulo_longo_sacrifica_a_marca_antes_do_cliente():
    """Quando não cabe tudo, o que sai é "Leandro Furtado" — o domínio já
    aparece logo acima do título no resultado, então perder a marca custa
    pouco; perder o cliente custa a busca inteira."""
    saida = titulo_para_busca("Ação Cinema - Divertidamente", "Colégios Maristas")
    assert saida.startswith("Colégios Maristas")
    assert "Leandro Furtado" not in saida


def test_titulo_muito_longo_abre_mao_do_cliente_por_ultimo():
    saida = titulo_para_busca("Dia do profissional do Secretariado",
                              "Hospital Marcelino Champagnat")
    assert _visivel(saida) <= LIMITE_TITULO
    assert "Dia do profissional do Secretariado" in saida


def test_titulo_sem_titulo_nao_devolve_vazio():
    assert titulo_para_busca("", "Electrolux") == "Leandro Furtado"


# --------------------------------------------------------------- descrição --

def test_descricao_usa_o_espaco_que_antes_ficava_vazio():
    """A fórmula antiga devolvia só o subtítulo: 50 caracteres de 155."""
    antiga = "Evento de 100 Anos da Linha Celebre de Electrolux."
    nova = descricao_para_busca(antiga, "Live Marketing", "Electrolux", "2026")
    assert _visivel(nova) > _visivel(antiga) * 2
    assert nova.startswith(antiga)


def test_descricao_nao_repete_o_que_o_subtitulo_ja_disse():
    """Sem esta regra saía "Key visual para evento da DAF. Projeto de key
    visual para DAF." — o tipo de texto que faz o Google reescrever a
    descrição por conta própria."""
    saida = descricao_para_busca(
        "Key visual para evento de Live Marketing da DAF Caminhões",
        "Key Visual", "DAF", "2025")
    assert saida.lower().count("key visual") == 1
    assert "Projeto de" not in saida


def test_descricao_acrescenta_categoria_e_cliente_quando_faltam():
    saida = descricao_para_busca("Navigate the new.", "Key Visual", "Impress", "2025")
    assert "Projeto de key visual para Impress." in saida


def test_descricao_carrega_a_cidade_em_toda_pagina_de_case():
    """24 páginas repetindo "Curitiba" pesam mais na busca local que a home
    sozinha."""
    for _, cliente, cat, ano, sub in REAIS:
        assert "Curitiba" in descricao_para_busca(sub, cat, cliente, ano)


def test_subtitulo_longo_ainda_recebe_assinatura_curta():
    """O "Primeira conta" tem 110 caracteres de subtítulo. Sem a versão enxuta
    da assinatura ele ficaria sem nada e perderia os 45 que sobram."""
    sub = ("A Primeira Conta é um evento itinerante que transforma a abertura "
           "da primeira conta bancária em cerimônia real.")
    saida = descricao_para_busca(sub, "Live Marketing", "Bradesco", "2026")
    assert "Leandro Furtado" in saida
    assert _visivel(saida) <= LIMITE_DESCRICAO


def test_e_comercial_da_categoria_vira_conjuncao():
    """"Projeto de motion & vídeo" lê como nome de estúdio no meio da frase."""
    saida = descricao_para_busca("Cover do ator Cillian Murphy.",
                                 "Motion & Vídeo", "", "2026")
    assert "motion e vídeo" in saida
    assert "&" not in saida


def test_descricao_sem_resumo_nao_comeca_com_espaco_nem_ponto():
    saida = descricao_para_busca("", "Key Visual", "Impress", "2025")
    assert saida == saida.strip()
    assert not saida.startswith(".")
    assert "Impress" in saida


# ------------------------------------------------- descrição de cliente --

# Os seis clientes que estouraram o limite na auditoria de 22/08/2026, quando
# a regra contava títulos em vez de medir caracteres.
CLIENTES_DIFICEIS = [
    ("Colégios Maristas", ["Ação Cinema - Divertidamente", "Pesquisa de Satisfação"]),
    ("Maratona Internacional do Paraná", ["Medalhas da Maratona Internacional do Paraná"]),
    ("Hospital Marcelino Champagnat", ["Dia do profissional do Secretariado"]),
    ("Associação Comercial do Paraná", ["SITE Associação Comercial do Paraná"]),
    ("Pravaler", ["Realizar o sonho da facul não é sorte, é escolha."]),
    ("Coca-Cola", ["Junte Seus Heróis Marvel", "Museu do silêncio"]),
]


def test_nenhuma_pagina_de_cliente_estoura_o_corte():
    for nome, titulos in CLIENTES_DIFICEIS:
        saida = descricao_de_cliente(nome, titulos)
        assert len(saida) <= LIMITE_DESCRICAO, f"{nome}: {len(saida)}"


def test_cliente_de_um_projeto_diz_projeto_no_singular():
    """"Tudo o que foi feito para Bradesco: 1 projetos." estava no resultado
    de busca de seis clientes."""
    saida = descricao_de_cliente("Electrolux", ["Linha Celebre 100 Anos"])
    assert saida.startswith("Projeto de")
    assert "1 projetos" not in saida


def test_cliente_de_varios_projetos_lista_os_titulos():
    """Descrição igual em 22 páginas é conteúdo duplicado; os títulos são o
    que diferencia uma da outra sem trabalho manual."""
    saida = descricao_de_cliente("Coca-Cola", ["Junte Seus Heróis Marvel",
                                               "Museu do silêncio"])
    assert "Junte Seus Heróis Marvel" in saida and "Museu do silêncio" in saida
    assert saida.startswith("Projetos de")


def test_titulo_que_nao_cabe_inteiro_some_em_vez_de_virar_fragmento():
    """Cortar no meio da palavra ("Dia do profissi e outros") lê como página
    quebrada. Quando nem o primeiro título cabe, a lista inteira sai."""
    saida = descricao_de_cliente("Hospital Marcelino Champagnat",
                                 ["Dia do profissional do Secretariado"])
    assert "Dia do profissi " not in saida
    assert "Hospital Marcelino Champagnat" in saida
    assert "Curitiba" in saida


def test_corte_da_lista_acontece_na_virgula():
    saida = descricao_de_cliente(
        "Cliente", ["Um projeto de nome médio", "Outro projeto de nome médio",
                    "Um terceiro projeto com nome bem mais longo ainda"])
    assert len(saida) <= LIMITE_DESCRICAO
    if "e outros" in saida:
        antes = saida.split(":", 1)[1].split(" e outros")[0]
        assert not antes.endswith(",")


def test_cliente_sem_projeto_nao_quebra():
    saida = descricao_de_cliente("Marca Nova", [])
    assert "Marca Nova" in saida and len(saida) <= LIMITE_DESCRICAO


# ----------------------------------------------------------------- inglês --

def test_descricao_em_ingles_nao_deixa_cauda_em_portugues():
    """Bug real de 23/08/2026: com title_en/subtitle_en preenchidos, a página
    /en servia "100 years of the Electrolux Linha Celebre range. Projeto de
    live marketing. Direção de arte por Leandro Furtado" — metade traduzida."""
    saida = descricao_para_busca(
        "100 years of the Electrolux Linha Celebre range.",
        "Live Marketing", "Electrolux", "2026", "en")
    for palavra in ("Projeto", "Direção de arte", "por "):
        assert palavra not in saida, saida
    assert "Art direction by" in saida and "Brazil" in saida


def test_descricao_em_ingles_respeita_o_mesmo_orcamento():
    for _, cliente, cat, ano, sub in REAIS:
        assert _visivel(descricao_para_busca(sub, cat, cliente, ano, "en")) <= LIMITE_DESCRICAO


def test_e_comercial_vira_and_em_ingles():
    saida = descricao_para_busca("A cover of Cillian Murphy.", "Motion & Vídeo",
                                 "", "2026", "en")
    assert "motion and vídeo" in saida and "&" not in saida


def test_descricao_de_cliente_em_ingles_nao_mistura_idioma():
    saida = descricao_de_cliente("Electrolux", ["Linha Celebre 100 Years"], "en")
    assert "Project for Electrolux" in saida
    assert "Direção" not in saida and "por " not in saida
