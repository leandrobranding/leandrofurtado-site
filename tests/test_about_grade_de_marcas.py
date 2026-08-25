"""Item 3 do conserto pós-lançamento (19/08, pedido do dono com captura): a
grade de marcas do Sobre é `grid-template-columns: repeat(6, 1fr)` (6
colunas), mas o template recortava `clients[:8]` — com 8 marcas isso rende
6 na primeira linha e só 2 na segunda, uma linha capenga. Ordem do dono:
"deixe em uma linha apenas, ou preencha com mais 4 marcas".

Regra nova, server-side: com 12+ marcas mostra 12 (6×2 linhas cheias,
preferência dele); senão mostra exatamente 6 (uma linha cheia). Nunca uma
linha incompleta. A ordem/seleção de quais marcas entram continua a mesma
de sempre (o recorte de all_brands) — só o TAMANHO do corte mudou.
"""
from app.routers.public import _marcas_para_grade_sobre


def _marcas(n: int) -> list[dict]:
    return [{"name": f"Marca {i}", "slug": f"marca-{i}", "logo": f"/logo-{i}.svg"} for i in range(n)]


def test_com_8_marcas_mostra_exatamente_6_uma_linha_cheia():
    resultado = _marcas_para_grade_sobre(_marcas(8))
    assert len(resultado) == 6


def test_com_12_marcas_mostra_as_12_duas_linhas_cheias():
    resultado = _marcas_para_grade_sobre(_marcas(12))
    assert len(resultado) == 12


def test_com_15_marcas_mostra_12_nunca_mais_que_isso():
    resultado = _marcas_para_grade_sobre(_marcas(15))
    assert len(resultado) == 12


def test_com_exatamente_6_marcas_mostra_as_6():
    resultado = _marcas_para_grade_sobre(_marcas(6))
    assert len(resultado) == 6


def test_a_selecao_preserva_a_ordem_recebida_sem_reordenar():
    marcas = _marcas(12)
    resultado = _marcas_para_grade_sobre(marcas)
    assert resultado == marcas[:12]


def test_com_menos_de_6_marcas_mostra_todas_sem_forcar_seis():
    resultado = _marcas_para_grade_sobre(_marcas(3))
    assert len(resultado) == 3
