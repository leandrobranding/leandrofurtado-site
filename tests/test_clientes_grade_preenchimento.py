"""Item 2 do pacote de 19/08 (pedido do dono, depois dos prêmios): a página
/clientes (Galeria de Honra, grade COMPLETA de marcas) deixava a última
linha com células vazias no desktop quando o total não era múltiplo de 6 —
"fica vazio, sem graça; deixe mais uniforme, harmônico, bonito". Mesma
filosofia da regra das marcas do Sobre, com uma diferença importante: ali
(_marcas_para_grade_sobre) o corte reduz a lista até fechar a linha; aqui
NENHUMA marca pode ficar de fora, então quem se ajusta é o preenchimento,
não a seleção.

Solução: (a) para cada contagem de colunas que a grade usa em algum breakpoint
(6 desktop, 4/3/2 telas menores — ver .hall-grid em main.css),
`preenchimento_grade_clientes` calcula quantas células de preenchimento
fecham a última linha; (b) a primeira célula de preenchimento é um convite
discreto ("sua marca aqui →", link para /contato); as demais (quando sobra
mais de uma vaga) repetem o padrão gráfico da casa. Nunca uma célula vazia
crua.
"""
from starlette.testclient import TestClient

from app.main import app as _app
from app.routers.public import HALL_GRID_COLS, preenchimento_grade_clientes


# ---------- função pura ----------

def test_total_multiplo_de_6_nao_precisa_de_preenchimento_no_desktop():
    assert preenchimento_grade_clientes(12)[6] == 0
    assert preenchimento_grade_clientes(6)[6] == 0


def test_8_marcas_precisa_de_4_preenchimentos_para_fechar_6_colunas():
    # é exatamente o achado do dono: 8 marcas, 6 colunas, 2 na segunda linha
    # → falta 4 para fechar
    assert preenchimento_grade_clientes(8)[6] == 4


def test_preenchimento_nunca_alcanca_a_propria_contagem_de_colunas():
    # o preenchimento máximo possível pra fechar uma linha de C colunas é
    # C - 1 (uma marca sobrando já fecha sozinha com 0)
    for total in range(0, 30):
        for c in HALL_GRID_COLS:
            assert 0 <= preenchimento_grade_clientes(total)[c] < c


def test_cobre_as_quatro_contagens_de_colunas_da_grade():
    resultado = preenchimento_grade_clientes(8)
    assert set(resultado.keys()) == {6, 4, 3, 2}
    assert resultado == {6: 4, 4: 0, 3: 1, 2: 0}


def test_total_zero_nao_pede_preenchimento_nenhum():
    assert all(v == 0 for v in preenchimento_grade_clientes(0).values())


def test_a_soma_total_mais_preenchimento_e_sempre_multiplo_da_coluna():
    for total in range(1, 25):
        for c in HALL_GRID_COLS:
            assert (total + preenchimento_grade_clientes(total)[c]) % c == 0


# ---------- rota /clientes de verdade (TestClient) ----------

def _marcas(n: int) -> list[dict]:
    return [
        {"name": f"Marca {i}", "slug": f"marca-{i}", "logo": f"/logo-{i}.svg", "escala": 1,
         "has_cases": True, "chapa": False, "na_home": True}
        for i in range(n)
    ]


def _subir_com_marcas(monkeypatch, n):
    import app.routers.public as pub
    monkeypatch.setattr(pub, "all_brands", lambda db: _marcas(n))
    with TestClient(_app):
        pass


def _get_clientes():
    with TestClient(_app, base_url="https://testserver") as client:
        return client.get("/clientes")


def test_8_marcas_nunca_mostra_celula_vazia_crua(monkeypatch):
    _subir_com_marcas(monkeypatch, 8)
    r = _get_clientes()
    assert r.status_code == 200
    html = r.text
    # nenhuma marca sumiu
    assert html.count('class="brand-cell has-cases"') == 8
    # preenchimento do desktop (6 colunas, 8 marcas) = 4 células. Conta por
    # "data-fill-index=", que só existe nos <div> de preenchimento — o texto
    # do <style> injetado também contém "brand-cell--filler" (uma vez por
    # breakpoint), então contar por essa classe direto contaria os dois.
    assert html.count('data-fill-index="') == 4
    # a primeira é sempre o convite; as outras 3 (4 - 1) usam o padrão gráfico
    # — "brand-cell--padrao" conta as duas variantes (padrao e padrao-b, essa
    # última contém a primeira como substring) — nenhuma célula de
    # preenchimento fica sem classe de conteúdo nenhuma.
    assert html.count('brand-cell--convite') == 1
    assert html.count('brand-cell--padrao') == 3


def test_12_marcas_multiplo_de_6_nao_gera_preenchimento(monkeypatch):
    _subir_com_marcas(monkeypatch, 12)
    r = _get_clientes()
    html = r.text
    assert html.count('class="brand-cell has-cases"') == 12
    assert 'brand-cell--filler' not in html
    assert 'hall-grid .brand-cell--filler:nth-of-type' not in html


def test_convite_linka_para_contato(monkeypatch):
    _subir_com_marcas(monkeypatch, 8)
    r = _get_clientes()
    assert 'href="/contato"' in r.text
    assert 'bc-convite-link' in r.text


def test_style_de_preenchimento_usa_os_valores_calculados(monkeypatch):
    _subir_com_marcas(monkeypatch, 8)
    r = _get_clientes()
    html = r.text
    esperado = preenchimento_grade_clientes(8)
    assert f"nth-of-type(n+{esperado[6] + 1})" in html
    assert f"nth-of-type(n+{esperado[4] + 1})" in html
    assert f"nth-of-type(n+{esperado[3] + 1})" in html
    assert f"nth-of-type(n+{esperado[2] + 1})" in html


def test_1_marca_fecha_a_linha_de_2_colunas_sem_preenchimento_mas_precisa_no_desktop(monkeypatch):
    _subir_com_marcas(monkeypatch, 1)
    r = _get_clientes()
    html = r.text
    assert html.count('class="brand-cell has-cases"') == 1
    # 1 marca: desktop (6) precisa de 5 preenchimentos; mobile (2) precisa de 1
    esperado = preenchimento_grade_clientes(1)
    assert esperado[6] == 5
    assert esperado[2] == 1
    assert html.count('data-fill-index="') == max(esperado.values())
