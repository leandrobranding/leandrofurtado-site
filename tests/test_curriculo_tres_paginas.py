"""O currículo cabe em três páginas, sempre (24/08/2026).

Aconteceu duas vezes no mesmo dia. De manhã as competências cresceram e o PDF
foi para quatro páginas, com 34 caracteres na quarta. À tarde entrou a
experiência atual e voltou a acontecer, agora com 133. Página quase vazia num
currículo lê como descuido, e é a última coisa que o recrutador vê.

A correção não foi apagar texto do perfil: a página /about tem espaço de sobra
e não deve empobrecer para o PDF caber. O corte é decisão de FORMATO, e mora em
`build_pdf`, que degrada na ordem de um currículo bem escrito — emprego recente
descrito, emprego antigo listado.

Estes testes guardam as duas pontas: que o limite é respeitado quando há
conteúdo demais, e que ele não corta nada quando não precisa.
"""
import re

from app.services.resume import DEGRAUS, LIMITE_PAGINAS, build_pdf

BASE = {
    "name": "Leandro Furtado",
    "title_pt": "Engenheiro de IA e Desenvolvedor",
    "title_en": "AI Engineer & Developer",
    "location_pt": "Curitiba/PR", "location_en": "Curitiba/PR",
    "email": "contatoleandrofurtado@gmail.com",
    "summary_pt": "Resumo curto.", "summary_en": "Short summary.",
}

LONGA = ("Descrição longa o suficiente para ocupar várias linhas do documento, "
         "repetida em cada experiência para forçar o estouro de página que este "
         "teste precisa reproduzir. ") * 3


def _paginas(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


def _perfil(n_experiencias: int, desc: str) -> dict:
    p = dict(BASE)
    p["experience"] = [
        {"company": f"Empresa {i}", "role_pt": "Cargo", "role_en": "Role",
         "period": f"Jan 20{10 + i % 15} — Dez 20{11 + i % 15}", "desc_pt": desc,
         "desc_en": desc, "tags": ["Python", "FastAPI"]}
        for i in range(n_experiencias)
    ]
    return p


def test_curriculo_curto_nao_perde_nada():
    """Com pouco conteúdo o laço não roda: o documento sai na primeira
    tentativa, com todas as descrições."""
    pdf = build_pdf(_perfil(3, "Descrição curta."), "pt")
    assert _paginas(pdf) <= LIMITE_PAGINAS


def test_curriculo_grande_demais_e_espremido_ate_caber():
    for lang in ("pt", "en"):
        pdf = build_pdf(_perfil(20, LONGA), lang)
        assert _paginas(pdf) <= LIMITE_PAGINAS, \
            f"{lang}: saiu com {_paginas(pdf)} páginas"


def test_o_corte_sacrifica_a_experiencia_antiga_e_nao_a_recente():
    """A ordem importa: quem lê decide nos primeiros cargos. Um currículo que
    corta o emprego atual para caber inverteu a própria razão de existir."""
    from app.services.resume import _sem_descricao_alem_de
    p = _perfil(12, "Uma descrição qualquer.")
    magro = _sem_descricao_alem_de(p, 6)
    assert magro["experience"][0]["desc_pt"], "a experiência mais recente perdeu a descrição"
    assert magro["experience"][5]["desc_pt"]
    assert magro["experience"][6]["desc_pt"] == ""
    assert magro["experience"][11]["desc_pt"] == ""
    # empresa, cargo e período continuam: emprego antigo fica LISTADO, não some
    for xp in magro["experience"]:
        assert xp["company"] and xp["role_pt"] and xp["period"]


def test_o_perfil_original_nao_e_alterado():
    """`_sem_descricao_alem_de` devolve cópia. Se mexesse no dicionário
    recebido, a primeira geração do PDF apagaria as descrições do perfil em
    memória e a página /about sairia vazia na requisição seguinte."""
    from app.services.resume import _sem_descricao_alem_de
    p = _perfil(12, "Texto original.")
    _sem_descricao_alem_de(p, 2)
    assert all(xp["desc_pt"] == "Texto original." for xp in p["experience"])


def test_os_degraus_vao_do_maior_para_o_menor():
    assert DEGRAUS[0] is None
    numeros = [d for d in DEGRAUS if d is not None]
    assert numeros == sorted(numeros, reverse=True)
    assert numeros[-1] >= 5, "cortar abaixo de cinco descrições esvazia o currículo"
