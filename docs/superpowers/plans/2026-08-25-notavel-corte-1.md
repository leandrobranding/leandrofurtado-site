# Notável, corte 1: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** entregar o painel financeiro do Notável no Lab, com as seis regiões da tela heroína, emissão de nota fiscal com PDF, fila de despachos que recusa aprovação acima do saldo, câmbio do Banco Central com cache diário, saldos fictícios, as três camadas de motion e modo aplicativo no celular.

**Architecture:** módulo `app/lab/` do site FastAPI que já está no ar. Três serviços novos e sem estado de módulo (`fiscal.py`, `cambio.py`, `notavel.py`), três tabelas novas e uma coluna nova nos modelos existentes, rotas dentro do router `/lab` que já existe (e que já herda o rate limit), telas Jinja2 renderizadas no servidor com troca de fragmento por `fetch` (o mesmo padrão do Admita), e um `notavel.js` sem dependência externa.

**Tech Stack:** Python 3.13, FastAPI 0.141.1, SQLAlchemy 2.0.51, SQLite (WAL), Jinja2 3.1.6, fpdf2 2.8.8, httpx 0.28.1, pytest 8.3.4. CSS e JavaScript escritos à mão, sem framework, sem CDN.

**Spec:** `docs/superpowers/specs/2026-08-25-notavel-design.md`

**Baseline da suíte antes da primeira task: 1455 testes passando, zero falha.** Rode `./.venv/bin/python -m pytest` na raiz do projeto e confirme esse número antes de começar. Toda task termina com a suíte inteira verde, nunca só com os testes novos.

---

## Global Constraints

Toda task herda estas regras. Elas não são estilo: cada uma tem um teste que já existe na suíte, ou ganha um nesta entrega.

1. **Escopo do corte 1 é o da §12 da spec**, e só ele: painel com as seis regiões, motion nas três camadas, emissão de nota com PDF, despachos, câmbio, saldos, semente da empresa e modo aplicativo no celular. **Calculadora do Simples com CNAE, categorização de extrato por IA, aba de folha e o caso de rescisão são corte 2** e não entram aqui. Onde este plano prepara terreno para o corte 2 (tabelas de anexo, Fator R semeado), ele diz isso no comentário.
2. **PROIBIDO travessão como pontuação em copy visível.** Vale para todo texto que uma pessoa lê na tela, no `<title>`, na `description` e no PDF. Use vírgula, dois-pontos ou ponto. `tests/lab/test_base_demo.py` e `tests/lab/test_vitrine.py` já varrem isso.
3. **PROIBIDO `|safe` sobre dado de visitante** em qualquer template dentro de `app/templates/lab/`. Varrido por `tests/lab/test_regras_seguranca.py`.
4. **Nenhuma rota do Lab aceita upload**, de nenhum tipo, em nenhuma tela. Varrido por `tests/lab/test_regras_seguranca.py`.
5. **Nada em `app/lab/` importa de `app/nodal/`.** O Nodal é módulo opcional desde 24/08/2026 e pode não existir no disco.
6. **Dinheiro em centavos inteiros**, sempre, com o sufixo `_centavos` no nome do campo. Ponto flutuante erra centavo em soma. Cotação de câmbio não é dinheiro e tem regra própria (Task 4).
7. **Todo registro semeado grava `origem="seed"`.** Sem isso o cenário fictício consome o teto de `MAX_REGISTROS_POR_DEMO` antes do visitante clicar em qualquer coisa (`checar_limite_registros` filtra por `origem == "visitante"`).
8. **Zero rolagem de página** (§13b da spec do Lab). O shell é travado em `100dvh`. Excedente rola só dentro de um box com a utilitária `.rola-interno`, nunca como barra de rolagem da página.
9. **Sem GSAP e sem biblioteca externa dentro do Lab.** Motion é keyframes em CSS mais `requestAnimationFrame`, com easing `cubic-bezier(.2,.75,.3,1)`.
10. **Os valores do painel nascem renderizados pelo servidor.** A chegada anima do zero até eles. Sem JavaScript o painel aparece completo e correto, só sem a contagem.
11. **`prefers-reduced-motion: reduce` desliga a chegada e o pulso** e mantém as transições de estado curtas.
12. **Os cinco recursos modernos de CSS são melhoria progressiva.** `subgrid`, `@container` e `:has()` entram atrás de `@supports`; View Transitions entra atrás de teste de capacidade em JavaScript; `@starting-style` degrada sozinho porque uma at-rule desconhecida é ignorada. O painel funciona inteiro, com os cinco fluxos, sem nenhum dos cinco.
13. **Toda tabela de alíquota vive em `app/lab/fiscal.py`, datada, e a tela mostra de quando ela é.** Onde o valor for ilustrativo e não calculado, a tela diz isso.
14. **CNPJ e documentos fictícios por design**, com dígito verificador errado de propósito, via os helpers `_cnpj_ficticio`/`_cpf_ficticio` de `app/lab/seeds_demo.py`.
15. **Nenhum host externo de fonte, script ou imagem.** As fontes do Notável (Source Serif 4, IBM Plex Sans, IBM Plex Mono) já estão em `app/static/lab/fonts/` e já são declaradas em `lab-base.css`.
16. **Todo caractere com apresentação emoji leva `&#xFE0E;`** (ou vira SVG). Regra permanente da casa. As setas e sinais do painel são SVG do sprite `app/static/lab/icones/notavel.svg`, que já existe com 34 símbolos.
17. **Toda rota nova nasce dentro do `router` de `app/lab/rotas.py`**, que já declara `dependencies=[Depends(limitar_taxa)]` no construtor. Não redeclare a dependency por rota. `tests/lab/test_rotas_protegidas.py` confere rota por rota.
18. **Prefixo de classe CSS do Notável é `nt-`.** O Admita usa `admita-`; misturar os dois num arquivo é o começo do vazamento de estilo entre demos.
19. Rode a suíte com `./.venv/bin/python -m pytest` a partir de `/Users/leandrofurtado/LEANDRO FURTADO/leandrofurtado-site`.
20. Os totais de teste que cada task declara ("1474 passed") são conferência, não contrato: eles somam os casos escritos aqui ao baseline de 1455. Se o seu total divergir por um ou dois porque você quebrou um caso em dois, siga em frente. O que é contrato é **zero falha e zero xfail inesperado** ao fim de cada task.

---

## Estrutura de arquivos

**Criados:**

| Arquivo | Responsabilidade |
| --- | --- |
| `app/lab/fiscal.py` | tabelas de alíquota datadas e o cálculo dos impostos da nota. Só aritmética, sem banco e sem rede. |
| `app/lab/cambio.py` | cotação PTAX do Banco Central: leitura do cache, decisão de atualizar, e a busca em si. |
| `app/lab/auditoria.py` | `registrar()`, a linha de trilha compartilhada pelas demos. |
| `app/lab/notavel.py` | domínio do painel: saldos, série do KPI, contexto da tela, emitir e cancelar nota, aprovar e recusar despacho, quitar recebível. |
| `app/templates/lab/notavel/painel.html` | página cheia, estende `_base_demo.html`. |
| `app/templates/lab/notavel/_shell.html` | o fragmento que toda mutação devolve: as seis regiões. |
| `app/templates/lab/notavel/_emitir.html` | o modal de emissão em três passos, fora do fragmento trocado. |
| `app/static/lab/notavel.js` | troca de fragmento, motion, modo aplicativo. |
| `tests/lab/test_fiscal.py` | Task 1 |
| `tests/lab/test_cambio.py` | Task 4 |
| `tests/lab/test_notavel.py` | domínio e rotas (Tasks 5 a 8) |
| `tests/lab/test_notavel_tela.py` | tela, CSS, JavaScript e motion (Tasks 9 a 12) |

**Modificados:**

| Arquivo | O quê |
| --- | --- |
| `app/lab/models.py` | `LabEmpresaFin`, `LabDespacho`, `LabCotacao`, coluna `LabNota.pago_em` |
| `app/services/migrations.py` | uma entrada em `COLUNAS` para `lab_nota.pago_em` |
| `app/lab/seeds_demo.py` | semente da casa de software, dos despachos e do câmbio de partida |
| `app/lab/pdf.py` | `gerar_nf_pdf` passa a aceitar um emitente; `ROTULOS_IMPOSTO` ganha o DAS |
| `app/lab/admita.py` | `_registrar` delega para `app/lab/auditoria.py` |
| `app/lab/rotas.py` | sete rotas novas do Notável |
| `app/static/lab/notavel.css` | camada de layout abaixo dos tokens que já existem |
| `app/templates/lab/_base_demo.html` | descrição e capa do Notável |
| `app/templates/_cabecalho.html` | Notável vira link |
| `app/templates/lab/vitrine.html` | cartão do Notável vira clicável |
| `tests/lab/test_base_demo.py`, `tests/lab/test_vitrine.py`, `tests/lab/test_rotas_protegidas.py`, `tests/lab/test_pdf.py` | os travamentos do "em breve" saem (Task 12) |

---

### Task 1: Tabelas fiscais datadas

A §7 da spec pede que toda tabela de alíquota viva num arquivo único e datado, e que a tela mostre de quando ela é. Este módulo é esse arquivo. Ele é aritmética pura: não abre banco, não faz rede, não importa nada de `app/lab/`.

**Files:**
- Create: `app/lab/fiscal.py`
- Create: `tests/lab/test_fiscal.py`
- Modify: `app/lab/pdf.py` (acrescenta uma entrada em `ROTULOS_IMPOSTO`)

**Interfaces:**
- Consumes: nada.
- Produces:
  - `VIGENCIA: dt.date` e `VIGENCIA_ROTULO: str`
  - `ANEXO_III` e `ANEXO_V`: `tuple[tuple[int, int, int], ...]`, cada faixa `(teto_centavos, nominal_bps, deduzir_centavos)`
  - `LIMITE_FATOR_R_BPS: int`
  - `ISS_SIMULADO_BPS: int`
  - `faixa_do_anexo(rbt12_centavos: int, anexo: str) -> tuple[int, int, int, int]` devolvendo `(indice_1_based, teto_centavos, nominal_bps, deduzir_centavos)`
  - `aliquota_efetiva_bps(rbt12_centavos: int, anexo: str) -> int`
  - `fator_r_bps(folha12_centavos: int, rbt12_centavos: int) -> int`
  - `anexo_pelo_fator_r(folha12_centavos: int, rbt12_centavos: int) -> str` devolvendo `"III"` ou `"V"`
  - `formatar_aliquota(bps: int) -> str`, exemplo `1359 -> "13,59%"`
  - `memoria_de_calculo(subtotal_centavos: int, rbt12_centavos: int, anexo: str) -> list[dict]`
  - `impostos_para_json(memoria: list[dict]) -> dict[str, int]`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/lab/test_fiscal.py`:

```python
"""Tabelas fiscais datadas do Notável (§7 da spec).

Aritmética pura: nenhum teste aqui sobe app, banco ou rede.
"""
import datetime as dt

import pytest

from app.lab import fiscal
from app.lab.pdf import ROTULOS_IMPOSTO, rotulo_humano_imposto

REAL = 100  # centavos, só para as constantes abaixo lerem como dinheiro


def test_vigencia_e_uma_data_e_o_rotulo_diz_o_ano():
    assert isinstance(fiscal.VIGENCIA, dt.date)
    assert str(fiscal.VIGENCIA.year) in fiscal.VIGENCIA_ROTULO


def test_faixas_sobem_e_nao_tem_buraco():
    """Teto de cada faixa maior que o da anterior, nas duas tabelas: uma
    faixa fora de ordem faria `faixa_do_anexo` devolver a errada em
    silêncio."""
    for tabela in (fiscal.ANEXO_III, fiscal.ANEXO_V):
        tetos = [t for t, _, _ in tabela]
        assert tetos == sorted(tetos)
        assert len(set(tetos)) == len(tetos)
        assert len(tabela) == 6


def test_primeira_faixa_do_anexo_iii_nao_tem_deducao():
    _, teto, nominal, deduzir = fiscal.faixa_do_anexo(100_000 * REAL, "III")
    assert teto == 180_000 * REAL
    assert nominal == 600
    assert deduzir == 0


def test_faixa_pega_o_limite_exato_e_nao_a_seguinte():
    """RBT12 igual ao teto da faixa 1 ainda é faixa 1: a lei diz 'até
    180.000,00', e o centavo seguinte é que vira faixa 2."""
    indice, _, _, _ = fiscal.faixa_do_anexo(180_000 * REAL, "III")
    assert indice == 1
    indice, _, _, _ = fiscal.faixa_do_anexo(180_000 * REAL + 1, "III")
    assert indice == 2


def test_aliquota_efetiva_da_empresa_da_demo():
    """A casa de software semeada fatura R$ 1.480.000,00 em 12 meses e
    está no Anexo III, faixa 4 (16,00% nominal, dedução de R$ 35.640,00).
    Efetiva = (1.480.000 x 0,16 - 35.640) / 1.480.000 = 13,59%.

    Este número aparece na tela, então ele tem um teste com o valor
    escrito à mão, não recalculado pela mesma fórmula que ele testa."""
    assert fiscal.aliquota_efetiva_bps(1_480_000 * REAL, "III") == 1359


def test_aliquota_efetiva_da_primeira_faixa_e_a_nominal():
    """Sem dedução, efetiva e nominal coincidem. É o caso que pega um erro
    de sinal na subtração da parcela a deduzir."""
    assert fiscal.aliquota_efetiva_bps(120_000 * REAL, "III") == 600
    assert fiscal.aliquota_efetiva_bps(120_000 * REAL, "V") == 1550


def test_anexo_v_e_mais_caro_que_o_iii_na_mesma_receita():
    """O dilema inteiro do Fator R existe porque isto é verdade. Se um dia
    deixar de ser, a tabela foi digitada errada."""
    for rbt12 in (150_000 * REAL, 900_000 * REAL, 3_000_000 * REAL):
        assert fiscal.aliquota_efetiva_bps(rbt12, "V") > fiscal.aliquota_efetiva_bps(rbt12, "III")


def test_receita_acima_do_teto_do_simples_e_recusada():
    """Acima de R$ 4.800.000,00 a empresa sai do Simples. A demo nunca
    chega lá (a receita é semente e o corte 1 não deixa mudar), mas
    devolver a última faixa em silêncio seria mostrar um número errado com
    cara de certo, que é justamente o que a §7 proíbe."""
    with pytest.raises(ValueError):
        fiscal.aliquota_efetiva_bps(5_000_000 * REAL, "III")


def test_anexo_desconhecido_e_recusado():
    with pytest.raises(ValueError):
        fiscal.faixa_do_anexo(100_000 * REAL, "IV")


def test_fator_r_da_empresa_da_demo():
    """Folha de R$ 520.000,00 sobre receita de R$ 1.480.000,00 = 35,13%."""
    assert fiscal.fator_r_bps(520_000 * REAL, 1_480_000 * REAL) == 3513


def test_fator_r_decide_entre_anexo_iii_e_v():
    """O corte é 28%: no limite exato ainda é Anexo III (a lei diz 'igual
    ou superior'), um centésimo abaixo já é Anexo V."""
    assert fiscal.LIMITE_FATOR_R_BPS == 2800
    assert fiscal.anexo_pelo_fator_r(280_000 * REAL, 1_000_000 * REAL) == "III"
    assert fiscal.anexo_pelo_fator_r(279_000 * REAL, 1_000_000 * REAL) == "V"
    assert fiscal.anexo_pelo_fator_r(520_000 * REAL, 1_480_000 * REAL) == "III"


def test_fator_r_com_receita_zero_nao_divide_por_zero():
    """Sandbox recém-criado antes da semente, ou empresa sem faturamento:
    a tela não pode quebrar com ZeroDivisionError."""
    assert fiscal.fator_r_bps(1000, 0) == 0
    assert fiscal.anexo_pelo_fator_r(1000, 0) == "V"


def test_formatar_aliquota_usa_virgula_decimal():
    assert fiscal.formatar_aliquota(1359) == "13,59%"
    assert fiscal.formatar_aliquota(600) == "6,00%"
    assert fiscal.formatar_aliquota(0) == "0,00%"


def test_memoria_de_calculo_explica_cada_imposto():
    """§5.1: os impostos aparecem 'explicados na tela', com base, alíquota
    e valor. A memória é o que a tela desenha, então ela carrega os quatro
    campos por linha, mais o rótulo humano."""
    memoria = fiscal.memoria_de_calculo(10_000 * REAL, 1_480_000 * REAL, "III")
    assert len(memoria) == 2
    for linha in memoria:
        assert set(linha) == {"codigo", "rotulo", "base_centavos",
                              "aliquota_bps", "valor_centavos", "observacao"}
        assert linha["base_centavos"] == 10_000 * REAL
        assert linha["valor_centavos"] > 0
        assert linha["rotulo"] and linha["observacao"]


def test_memoria_calcula_iss_e_das_sobre_o_subtotal():
    """R$ 10.000,00 de serviço: ISS ilustrativo de 5% = R$ 500,00, DAS a
    13,59% = R$ 1.359,00."""
    memoria = fiscal.memoria_de_calculo(10_000 * REAL, 1_480_000 * REAL, "III")
    por_codigo = {linha["codigo"]: linha for linha in memoria}
    assert por_codigo["iss_simulado_5_por_cento"]["valor_centavos"] == 500 * REAL
    assert por_codigo["iss_simulado_5_por_cento"]["aliquota_bps"] == 500
    assert por_codigo["das_simples_nacional"]["valor_centavos"] == 1_359 * REAL
    assert por_codigo["das_simples_nacional"]["aliquota_bps"] == 1359


def test_observacao_do_iss_avisa_que_a_aliquota_e_ilustrativa():
    """§7: 'onde o valor for ilustrativo e não calculado, a tela diz
    isso'. O ISS do Notável não sai de tabela de município nenhum."""
    memoria = fiscal.memoria_de_calculo(10_000 * REAL, 1_480_000 * REAL, "III")
    iss = next(l for l in memoria if l["codigo"] == "iss_simulado_5_por_cento")
    assert "ilustrativa" in iss["observacao"].lower()


def test_impostos_para_json_bate_com_o_contrato_de_lab_nota():
    """`LabNota.impostos` é `{codigo: valor_centavos}` (contrato fixado no
    topo de app/lab/pdf.py). Chave string, valor int, nada além disso."""
    memoria = fiscal.memoria_de_calculo(10_000 * REAL, 1_480_000 * REAL, "III")
    json_impostos = fiscal.impostos_para_json(memoria)
    assert json_impostos == {
        "iss_simulado_5_por_cento": 500 * REAL,
        "das_simples_nacional": 1_359 * REAL,
    }
    assert all(isinstance(k, str) and isinstance(v, int)
               for k, v in json_impostos.items())


def test_todo_codigo_de_imposto_tem_rotulo_humano_no_pdf():
    """F8 do Plano 1: a CHAVE de `impostos` é código interno, e o PDF nunca
    pode imprimir 'das_simples_nacional' cru. Este teste amarra os dois
    módulos: código novo em fiscal.py sem entrada em ROTULOS_IMPOSTO
    quebra aqui, não na frente de um visitante."""
    memoria = fiscal.memoria_de_calculo(10_000 * REAL, 1_480_000 * REAL, "III")
    for linha in memoria:
        assert linha["codigo"] in ROTULOS_IMPOSTO, linha["codigo"]
        assert rotulo_humano_imposto(linha["codigo"]) == linha["rotulo"]


def test_subtotal_zero_nao_gera_imposto_negativo():
    memoria = fiscal.memoria_de_calculo(0, 1_480_000 * REAL, "III")
    assert all(linha["valor_centavos"] == 0 for linha in memoria)
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_fiscal.py -q`
Expected: FAIL na coleta, com `ModuleNotFoundError: No module named 'app.lab.fiscal'`.

- [ ] **Step 3: Escrever `app/lab/fiscal.py`**

```python
"""Tabelas fiscais do Notável, todas datadas num lugar só (§7 da spec).

POR QUE UM ARQUIVO SÓ, E DATADO

Alíquota do Simples, teto do INSS e tabela do IRRF mudam por lei todo ano.
Uma demo que mostra número velho para um gestor financeiro perde a
credibilidade que o Lab inteiro existe para construir. Com a data na tela,
o número velho vira "tabela de 2026" em vez de "erro".

Espalhar essas tabelas pelo código faria o painel mostrar 2026 numa região e
2025 na outra no ano em que alguém atualizasse metade. Aqui elas ficam
juntas, e `VIGENCIA` é o único lugar que precisa mudar de valor.

O QUE ESTE MODULO NAO FAZ

Não abre banco, não faz rede e não importa nada de `app/lab/`. É aritmética
sobre inteiros, para poder ser testada sozinha e chamada de qualquer lugar.

UNIDADES

- dinheiro em centavos inteiros (regra da casa, ver `app/lab/models.py`)
- alíquota em pontos-base (`bps`), que é centésimo de por cento: 13,59% é
  1359. Guardar alíquota como float traria de volta o mesmo erro de centavo
  que os centavos existem para evitar, e "13.59" digitado como 13.59 num
  lugar e 0.1359 em outro é o bug clássico desse domínio.

CORTE 1 E CORTE 2

O corte 1 usa `memoria_de_calculo` na emissão da nota. `fator_r_bps` e
`anexo_pelo_fator_r` já vivem aqui porque a empresa semeada declara Anexo III
por causa deles, e o cabeçalho do painel mostra o anexo. A calculadora que
deixa o visitante TROCAR o CNAE e ver o anexo mudar é corte 2 (§5.4) e vai
consumir estas mesmas funções, sem tabela nova.
"""
from __future__ import annotations

import datetime as dt

# Data de vigência das tabelas abaixo. Trocou tabela, troca esta data:
# ela é o que a tela mostra.
VIGENCIA = dt.date(2026, 1, 1)
VIGENCIA_ROTULO = "tabelas de 2026"

# Simples Nacional, Anexo III (prestação de serviços). Cada faixa é
# (teto de receita bruta em 12 meses, alíquota nominal em bps, parcela a
# deduzir em centavos). Valores da Lei Complementar 123, Anexo III.
ANEXO_III = (
    (  180_000_00,   600,          0),
    (  360_000_00,  1120,    9_360_00),
    (  720_000_00,  1350,   17_640_00),
    (1_800_000_00,  1600,   35_640_00),
    (3_600_000_00,  2100,  125_640_00),
    (4_800_000_00,  3300,  648_000_00),
)

# Anexo V: mesma prestação de serviços, para quem NÃO alcança o Fator R.
ANEXO_V = (
    (  180_000_00,  1550,          0),
    (  360_000_00,  1800,    4_500_00),
    (  720_000_00,  1950,    9_900_00),
    (1_800_000_00,  2050,   17_100_00),
    (3_600_000_00,  2300,   62_100_00),
    (4_800_000_00,  3050,  540_000_00),
)

_TABELAS = {"III": ANEXO_III, "V": ANEXO_V}

# Razão folha sobre receita que joga a empresa de serviço do Anexo V para o
# Anexo III. "Igual ou superior a 28%" na lei, por isso a comparação abaixo
# é `>=` e não `>`.
LIMITE_FATOR_R_BPS = 2800

# ISS do Notável: alíquota ILUSTRATIVA, não calculada por tabela de
# município nenhum (§7 manda a tela dizer isso, e `memoria_de_calculo`
# abaixo escreve a observação). 5% é o teto constitucional do ISS e o mesmo
# número que os seeds do Plano 1 já gravaram em
# `iss_simulado_5_por_cento`, então trocar aqui divergiria da semente.
ISS_SIMULADO_BPS = 500

CODIGO_ISS = "iss_simulado_5_por_cento"
CODIGO_DAS = "das_simples_nacional"


def faixa_do_anexo(rbt12_centavos: int, anexo: str) -> tuple[int, int, int, int]:
    """Devolve `(indice, teto_centavos, nominal_bps, deduzir_centavos)` da
    faixa em que a receita cai. `indice` é 1-based, que é como a faixa é
    chamada em qualquer conversa de contador ("faixa 4 do Anexo III").

    Levanta `ValueError` se o anexo não existe, se a receita é negativa, ou
    se ela passa do teto do Simples: acima de R$ 4.800.000,00 a empresa não
    está mais no regime, e devolver a última faixa em silêncio mostraria um
    número errado com cara de certo.
    """
    tabela = _TABELAS.get(anexo)
    if tabela is None:
        raise ValueError(f"anexo desconhecido: {anexo!r} (esperado 'III' ou 'V')")
    if rbt12_centavos < 0:
        raise ValueError("receita bruta não pode ser negativa")
    for indice, (teto, nominal, deduzir) in enumerate(tabela, start=1):
        if rbt12_centavos <= teto:
            return indice, teto, nominal, deduzir
    raise ValueError(
        "receita bruta acima do teto do Simples Nacional; a empresa "
        "estaria em outro regime tributário"
    )


def aliquota_efetiva_bps(rbt12_centavos: int, anexo: str) -> int:
    """Alíquota EFETIVA da faixa, em bps.

    A fórmula da lei é `(RBT12 x nominal - parcela a deduzir) / RBT12`. É a
    alíquota nominal descontada da parcela, e é sempre menor que a nominal a
    partir da segunda faixa. Quem mostra a nominal na tela mostra um imposto
    maior do que a empresa paga.

    Receita zero devolve a nominal da primeira faixa: sem faturamento não há
    o que deduzir, e dividir por zero na tela do painel não é opção.
    """
    _, _, nominal, deduzir = faixa_do_anexo(rbt12_centavos, anexo)
    if rbt12_centavos == 0:
        return nominal
    devido = rbt12_centavos * nominal // 10_000 - deduzir
    if devido <= 0:
        return 0
    return devido * 10_000 // rbt12_centavos


def fator_r_bps(folha12_centavos: int, rbt12_centavos: int) -> int:
    """Razão entre folha e faturamento dos últimos 12 meses, em bps.

    Receita zero devolve 0 em vez de estourar: é o estado de um sandbox no
    instante entre nascer e ser semeado, e o painel não pode quebrar nele.
    """
    if rbt12_centavos <= 0:
        return 0
    return max(0, folha12_centavos) * 10_000 // rbt12_centavos


def anexo_pelo_fator_r(folha12_centavos: int, rbt12_centavos: int) -> str:
    """O dilema clássico da casa de software: folha alta o bastante em
    relação ao faturamento leva a empresa de serviço para o Anexo III, que
    é mais barato; folha baixa a deixa no Anexo V.

    É a regra que faz o CNAE valer alguma coisa na tela em vez de ser
    enfeite (§2 da spec).
    """
    return "III" if fator_r_bps(folha12_centavos, rbt12_centavos) >= LIMITE_FATOR_R_BPS else "V"


def formatar_aliquota(bps: int) -> str:
    """1359 -> "13,59%". Vírgula decimal, como todo número em português."""
    inteiro, resto = divmod(int(bps), 100)
    return f"{inteiro},{resto:02d}%"


def memoria_de_calculo(subtotal_centavos: int, rbt12_centavos: int,
                       anexo: str) -> list[dict]:
    """Os impostos da nota, um por linha, com o que a tela precisa desenhar
    (§5.1: "impostos calculados e EXPLICADOS na tela, com base, alíquota,
    valor e rótulo humano de cada imposto").

    Ordem fixa: ISS primeiro, DAS depois. A tela lê a lista na ordem em que
    ela vem, e imposto que troca de lugar entre duas emissões parece bug.

    `codigo` é a chave interna, a mesma que vai para `LabNota.impostos`;
    `rotulo` é o texto que a pessoa lê, vindo de `ROTULOS_IMPOSTO` em
    `app/lab/pdf.py`, para tela e PDF nunca divergirem.
    """
    # Import tardio: mantém este módulo carregável sozinho, sem arrastar
    # `pdf` (e a cadeia protecao/models/sandbox/seeds) só para somar dois
    # inteiros. É a mesma razão de não haver import de banco aqui em cima.
    from .pdf import rotulo_humano_imposto

    subtotal_centavos = max(0, int(subtotal_centavos))
    das_bps = aliquota_efetiva_bps(rbt12_centavos, anexo)
    indice, _, _, _ = faixa_do_anexo(rbt12_centavos, anexo)

    return [
        {
            "codigo": CODIGO_ISS,
            "rotulo": rotulo_humano_imposto(CODIGO_ISS),
            "base_centavos": subtotal_centavos,
            "aliquota_bps": ISS_SIMULADO_BPS,
            "valor_centavos": subtotal_centavos * ISS_SIMULADO_BPS // 10_000,
            "observacao": ("Alíquota ilustrativa de demonstração, não calculada "
                           "pela tabela de nenhum município."),
        },
        {
            "codigo": CODIGO_DAS,
            "rotulo": rotulo_humano_imposto(CODIGO_DAS),
            "base_centavos": subtotal_centavos,
            "aliquota_bps": das_bps,
            "valor_centavos": subtotal_centavos * das_bps // 10_000,
            "observacao": (f"Alíquota efetiva da faixa {indice} do Anexo {anexo}, "
                           f"calculada sobre a receita dos últimos 12 meses "
                           f"({VIGENCIA_ROTULO})."),
        },
    ]


def impostos_para_json(memoria: list[dict]) -> dict[str, int]:
    """A memória vira o `{codigo: valor_centavos}` que `LabNota.impostos`
    guarda (contrato fixado no topo de `app/lab/pdf.py`). A memória inteira
    não é gravada de propósito: rótulo e observação são texto de
    APRESENTAÇÃO, que muda quando a redação muda, e nota emitida ontem não
    pode carregar a redação de ontem para sempre.
    """
    return {linha["codigo"]: int(linha["valor_centavos"]) for linha in memoria}
```

- [ ] **Step 4: Acrescentar o DAS ao mapa de rótulos do PDF**

Em `app/lab/pdf.py`, dentro de `ROTULOS_IMPOSTO`, some uma linha logo depois de `"iss_simulado_5_por_cento"`:

```python
ROTULOS_IMPOSTO = {
    "iss_simulado_5_por_cento": "ISS (5% simulado)",
    # DAS do Simples: entrou com a emissão de NF de verdade do Notável
    # (`app/lab/fiscal.py`). O topo deste módulo já mandava somar códigos
    # novos NESTE dict em vez de espalhar um segundo mapa.
    "das_simples_nacional": "DAS do Simples Nacional",
    "icms_simulado": "ICMS (simulado)",
    "irrf_simulado": "IRRF (simulado)",
    "pis_simulado": "PIS (simulado)",
    "cofins_simulado": "COFINS (simulado)",
}
```

- [ ] **Step 5: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_fiscal.py -q`
Expected: PASS, 19 testes.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1474 passed (1455 de base mais os 19 novos), zero falha.

- [ ] **Step 7: Commit**

```bash
git add app/lab/fiscal.py app/lab/pdf.py tests/lab/test_fiscal.py
git commit -m "Notavel: tabelas fiscais datadas e memoria de calculo da nota"
```

---

### Task 2: Modelos e migração do Notável

Três tabelas novas e uma coluna nova. `create_all()` cria tabela que não existe, mas nunca acrescenta coluna a tabela que já existe, e o banco de produção já está no ar com dados: por isso a coluna nova passa por `app/services/migrations.py`.

**Files:**
- Modify: `app/lab/models.py` (acrescenta três classes e uma coluna)
- Modify: `app/services/migrations.py` (uma entrada em `COLUNAS`)
- Modify: `tests/lab/conftest.py` (as três tabelas entram na limpeza entre testes)
- Test: `tests/lab/test_models.py` (acrescenta casos ao arquivo que já existe)
- Test: `tests/test_migrations.py` (acrescenta um caso ao arquivo que já existe)

**Interfaces:**
- Consumes: nada.
- Produces:
  - `LabEmpresaFin` com `sandbox_id`, `origem`, `nome`, `cnpj`, `cnae`, `cnae_descricao`, `regime`, `anexo`, `rbt12_centavos`, `folha12_centavos`, `saldo_corrente_centavos`, `saldo_aplicacao_centavos`, `criado_em`
  - `LabDespacho` com `sandbox_id`, `origem`, `fornecedor`, `valor_centavos`, `vence_em`, `categoria`, `status`, `motivo`, `decidido_em`, `criado_em`
  - `LabCotacao` com `moeda` (única), `venda_dezmilesimos`, `dia_cotacao`, `buscado_em`
  - `LabNota.pago_em: dt.datetime | None`

- [ ] **Step 1: Escrever os testes que falham**

`tests/lab/test_models.py` importa os modelos pelo nome (`from app.lab.models import LabCandidato, LabLead, LabSandbox`), não como módulo. Troque essa linha por:

```python
from app.lab.models import (
    LabClienteFiscal,
    LabCotacao,
    LabDespacho,
    LabEmpresaFin,
    LabNota,
    LabSandbox,
)
from app.lab.models import LabCandidato, LabLead  # noqa: F401  (testes que já existiam)
```

e acrescente `import pytest` e `from sqlalchemy.exc import IntegrityError` ao topo.

**Dois testes que já existem passam a estar errados e precisam ser atualizados na mesma task**, porque `LabEmpresaFin` e `LabDespacho` são tabelas de demo e carregam `sandbox_id` e `origem` como todas as outras:

Em `test_tabelas_de_demo_tem_sandbox_id`, acrescente as duas à tupla:

```python
    for t in ("lab_candidato", "lab_nota", "lab_aluno", "lab_avaliacao",
              "lab_documento_status", "lab_auditoria", "lab_cliente_fiscal",
              "lab_lancamento", "lab_parecer",
              "lab_empresa_fin", "lab_despacho"):
```

Em `test_tabelas_de_demo_tem_campo_de_origem_visitante_ou_seed`, acrescente as duas ao dicionário e troque o `9` por `11`:

```python
        "lab_parecer": "origem_registro",
        # painel financeiro do Notável: as duas nasceram com o corte 1 e
        # seguem a mesma regra ("seeds não contam" para o teto do visitante)
        "lab_empresa_fin": "origem", "lab_despacho": "origem",
    }
    assert len(tabelas_com_origem) == 11
```

Acrescente o helper de sandbox logo abaixo dos imports (o arquivo ainda não tem um):

```python
def _sandbox(db):
    """Sandbox mínimo para pendurar registro de demo."""
    sandbox = LabSandbox(
        token=f"t{db.query(LabSandbox).count()}",
        demo_origem="fin",
        expira_em=dt.datetime.now(dt.UTC) + dt.timedelta(hours=24),
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    return sandbox
```

E acrescente ao final do arquivo:

```python
# ------------------------------------------------------ Notável (corte 1) --

def test_empresa_fin_pende_do_sandbox_e_some_com_ele(db):
    """Como toda tabela de demo: `ondelete=CASCADE` mais o
    `PRAGMA foreign_keys=ON` de `app/database.py` apagam a empresa junto
    com o sandbox, sem laço em Python."""
    sandbox = _sandbox(db)
    db.add(LabEmpresaFin(
        sandbox_id=sandbox.id, origem="seed", nome="Casa de Software Ltda",
        cnpj="00.000.000/0001-00", cnae="6201-5/01",
        cnae_descricao="Desenvolvimento de programas sob encomenda",
        regime="Simples Nacional", anexo="III",
        rbt12_centavos=148_000_000, folha12_centavos=52_000_000,
        saldo_corrente_centavos=8_432_000, saldo_aplicacao_centavos=21_000_000,
    ))
    db.commit()
    assert db.query(LabEmpresaFin).count() == 1
    db.delete(sandbox)
    db.commit()
    assert db.query(LabEmpresaFin).count() == 0


def test_empresa_fin_nasce_como_visitante_se_ninguem_disser(db):
    """O default de `origem` é "visitante" em toda tabela de demo. A
    semente é OBRIGADA a passar "seed" explicitamente, senão o cenário
    fictício consome o teto do visitante."""
    sandbox = _sandbox(db)
    empresa = LabEmpresaFin(
        sandbox_id=sandbox.id, nome="X", cnpj="0", cnae="0",
        cnae_descricao="", regime="", anexo="III",
    )
    db.add(empresa)
    db.commit()
    assert empresa.origem == "visitante"


def test_despacho_nasce_pendente_sem_motivo_e_sem_decisao(db):
    sandbox = _sandbox(db)
    despacho = LabDespacho(
        sandbox_id=sandbox.id, origem="seed", fornecedor="Provedor de nuvem",
        valor_centavos=648_000, vence_em=dt.date(2026, 8, 28),
        categoria="Fornecedor",
    )
    db.add(despacho)
    db.commit()
    assert despacho.status == "pendente"
    assert despacho.motivo == ""
    assert despacho.decidido_em is None


def test_despacho_some_com_o_sandbox(db):
    sandbox = _sandbox(db)
    db.add(LabDespacho(
        sandbox_id=sandbox.id, origem="seed", fornecedor="Aluguel",
        valor_centavos=720_000, vence_em=dt.date(2026, 8, 27),
        categoria="Aluguel",
    ))
    db.commit()
    db.delete(sandbox)
    db.commit()
    assert db.query(LabDespacho).count() == 0


def test_nota_nasce_sem_pagamento(db):
    """`pago_em` nulo é o que faz a nota contar em "a receber". O pulso
    (§4 da spec) preenche este campo e o número desce na tela."""
    sandbox = _sandbox(db)
    cliente = LabClienteFiscal(sandbox_id=sandbox.id, origem="seed", nome="C")
    db.add(cliente)
    db.flush()
    nota = LabNota(sandbox_id=sandbox.id, cliente_id=cliente.id,
                   origem="seed", numero=1, total_centavos=1000)
    db.add(nota)
    db.commit()
    assert nota.pago_em is None


def test_cotacao_nao_pende_de_sandbox_nenhum(db):
    """Cotação do dia é dado PÚBLICO do Banco Central, igual para todo
    visitante. Se pendesse do sandbox, cada visitante novo dispararia uma
    chamada à API de um serviço público, que é justamente o que a §8 da
    spec do Lab proíbe. Mesma decisão de `LabIaGasto`, que também é
    global."""
    assert "sandbox_id" not in {c.name for c in LabCotacao.__table__.columns}
    sandbox = _sandbox(db)
    db.add(LabCotacao(moeda="USD", venda_dezmilesimos=51512,
                      dia_cotacao=dt.date(2026, 8, 24)))
    db.commit()
    db.delete(sandbox)
    db.commit()
    assert db.query(LabCotacao).count() == 1


def test_uma_linha_de_cotacao_por_moeda(db):
    """A tabela guarda a ÚLTIMA cotação conhecida de cada moeda, não um
    histórico: três linhas para sempre. O índice único é o que impede a
    atualização diária de virar um log que cresce sem fim."""
    db.add(LabCotacao(moeda="USD", venda_dezmilesimos=51512,
                      dia_cotacao=dt.date(2026, 8, 24)))
    db.commit()
    db.add(LabCotacao(moeda="USD", venda_dezmilesimos=51600,
                      dia_cotacao=dt.date(2026, 8, 25)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
```

E acrescente a `tests/test_migrations.py`:

```python
def test_migracao_acrescenta_pago_em_em_banco_antigo(tmp_path):
    """Banco criado antes do Notável não tem `lab_nota.pago_em`. Sem a
    migração, o painel quebraria com "no such column" no primeiro acesso,
    que é exatamente o cenário que este módulo existe para evitar."""
    from app.services.migrations import COLUNAS
    assert ("pago_em", "DATETIME") in COLUNAS["lab_nota"]
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_models.py tests/test_migrations.py -q`
Expected: FAIL com `AttributeError: module 'app.lab.models' has no attribute 'LabEmpresaFin'` e `KeyError: 'lab_nota'`.

- [ ] **Step 3: Acrescentar a coluna a `LabNota`**

Em `app/lab/models.py`, dentro de `class LabNota`, logo depois de `status`:

```python
    status: Mapped[str] = mapped_column(String(20), default="emitida")  # emitida | cancelada
    # Quando o dinheiro entrou. Nulo é o que faz a nota contar em "a
    # receber" no painel do Notável. Não virou um terceiro valor de
    # `status` de propósito: uma nota paga continua EMITIDA (o documento
    # fiscal não muda de estado porque o cliente pagou), e misturar as duas
    # coisas no mesmo campo obrigaria toda consulta de nota emitida a
    # lembrar de aceitar dois valores.
    pago_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Acrescentar as três classes**

Em `app/lab/models.py`, dentro da seção `# --------- Financeiro ----`, depois de `LabLancamento`:

```python
class LabEmpresaFin(Base):
    """A empresa que o painel do Notável mostra: uma casa de
    desenvolvimento de software de porte pequeno, fictícia (§2 da spec).

    POR QUE UMA TABELA, E NÃO CONSTANTES DE MÓDULO

    O corte 2 (§5.4) deixa o visitante TROCAR o CNAE e ver o anexo, a
    alíquota e o imposto mudarem na frente dele. Isso é estado por
    visitante, e estado por visitante mora no sandbox como qualquer outro
    registro da demo. Nascer como tabela agora evita uma migração de dado
    depois, quando já houver sandbox no ar.

    POR QUE SERVIÇO, E NÃO COMÉRCIO

    É em serviço que existem o Anexo III, o Anexo V e o Fator R. Sem isso o
    CNAE seria enfeite na tela. `rbt12_centavos` e `folha12_centavos` são a
    base do Fator R (`app/lab/fiscal.py`), e é a razão entre os dois que
    decide o `anexo` gravado aqui.

    `saldo_aplicacao_centavos` NÃO é saldo disponível para pagar despacho:
    a regra de disponibilidade vive em `app/lab/notavel.py::saldos` e olha
    só a conta corrente. É essa distinção que dá o fluxo da §5.3, em que o
    sistema recusa a aprovação com o número da diferença na tela.
    """

    __tablename__ = "lab_empresa_fin"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    nome: Mapped[str] = mapped_column(String(200))
    # CNPJ fictício, inválido por design (§9.9) — nunca um documento real
    cnpj: Mapped[str] = mapped_column(String(20), default="")
    cnae: Mapped[str] = mapped_column(String(20), default="")
    cnae_descricao: Mapped[str] = mapped_column(String(200), default="")
    regime: Mapped[str] = mapped_column(String(60), default="")
    # "III" ou "V" — o vocabulário de `app/lab/fiscal.py`
    anexo: Mapped[str] = mapped_column(String(4), default="III")
    # receita bruta dos últimos 12 meses: base da faixa e do Fator R
    rbt12_centavos: Mapped[int] = mapped_column(Integer, default=0)
    # folha dos últimos 12 meses: a outra metade do Fator R
    folha12_centavos: Mapped[int] = mapped_column(Integer, default=0)
    saldo_corrente_centavos: Mapped[int] = mapped_column(Integer, default=0)
    saldo_aplicacao_centavos: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabDespacho(Base):
    """Um pagamento aguardando aprovação na fila do painel (§5.2).

    A fila é onde o visitante AGE, e por isso ela ocupa a área nobre que o
    gráfico de entradas contra saídas ocupava no desenho antigo: movimento
    em gráfico é enfeite, movimento numa fila que responde a clique é prova.

    `status` é "pendente", "aprovado" ou "recusado". Aprovar baixa o saldo
    corrente da empresa; recusar devolve o item com o `motivo` na tela. Os
    dois registram na trilha de auditoria (`app/lab/auditoria.py`).

    Aprovação ACIMA do saldo disponível é recusada pelo serviço, com quanto
    falta (§5.3) — e essa recusa não grava nada aqui: o despacho continua
    pendente, porque nada aconteceu com ele.
    """

    __tablename__ = "lab_despacho"

    id: Mapped[int] = mapped_column(primary_key=True)
    sandbox_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sandbox.id", ondelete="CASCADE"), index=True)
    # "visitante" (default) ou "seed" — mesmo ruling de LabCandidato acima
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    fornecedor: Mapped[str] = mapped_column(String(200))
    valor_centavos: Mapped[int] = mapped_column(Integer, default=0)
    vence_em: Mapped[dt.date] = mapped_column(Date)
    categoria: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    # motivo da recusa, digitado por quem recusou; vazio enquanto pendente
    motivo: Mapped[str] = mapped_column(String(200), default="")
    decidido_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LabCotacao(Base):
    """A última cotação conhecida de uma moeda (§8 da spec).

    GLOBAL, sem `sandbox_id`, pelo mesmo motivo de `LabIaGasto`: a cotação
    do Banco Central é a mesma para todo mundo, e pendurá-la no sandbox
    faria cada visitante novo bater na API de um serviço público.

    UMA LINHA POR MOEDA, não um histórico. `moeda` é única: a atualização
    diária reescreve a linha no lugar. Três linhas para sempre, em vez de
    uma tabela que cresce todo dia útil para servir sempre a última.

    `venda_dezmilesimos` guarda a cotação em décimos de milésimo (5,1512
    vira 51512). Cotação não é dinheiro e não vai para centavos, mas
    também não vai para float: a mesma razão que manda dinheiro ser inteiro
    (soma de float erra) manda aqui um inteiro com escala declarada no
    nome, para ninguém dividir por 100 achando que é centavo.

    `dia_cotacao` é a data DA COTAÇÃO (o que a tela mostra), e `buscado_em`
    é quando a API foi chamada (o que decide se chama de novo hoje). Os dois
    são diferentes em todo sábado do ano.
    """

    __tablename__ = "lab_cotacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    moeda: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    venda_dezmilesimos: Mapped[int] = mapped_column(Integer, default=0)
    dia_cotacao: Mapped[dt.date] = mapped_column(Date)
    buscado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora)
```

- [ ] **Step 5: Acrescentar a migração**

Em `app/services/migrations.py`, dentro de `COLUNAS`, logo depois do bloco `"lab_candidato"`:

```python
    # painel financeiro do Notável (Lab de Demos): a nota passou a saber
    # quando foi paga, e é o nulo desta coluna que faz ela contar em "a
    # receber". Banco criado antes disso quebraria com "no such column"
    # no primeiro acesso ao painel.
    "lab_nota": [
        ("pago_em", "DATETIME"),
    ],
```

- [ ] **Step 6: Somar as três tabelas à limpeza entre testes**

Em `tests/lab/conftest.py`, dentro de `_TABELAS_LAB`, acrescente as três. Ordem importa, filhas antes de `lab_sandbox`:

```python
_TABELAS_LAB = (
    _m.LabDocumentoStatus, _m.LabAuditoria, _m.LabCandidato,
    _m.LabNota, _m.LabLancamento, _m.LabClienteFiscal,
    _m.LabDespacho, _m.LabEmpresaFin,
    _m.LabAvaliacao, _m.LabParecer, _m.LabAluno,
    _m.LabIaGasto, _m.LabLead, _m.LabCotacao,
    _m.LabSandbox,
)
```

`LabCotacao` entra na limpeza mesmo sem pender de sandbox nenhum: sem isso, um teste que grava uma cotação falsa a deixaria de pé para o próximo, e o teste do câmbio da Task 4 passaria ou falharia dependendo da ordem em que a suíte rodou.

- [ ] **Step 7: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_models.py tests/test_migrations.py -q`
Expected: PASS.

- [ ] **Step 8: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1483 passed (1474 mais os 9 novos), zero falha.

- [ ] **Step 9: Commit**

```bash
git add app/lab/models.py app/services/migrations.py tests/lab/conftest.py tests/lab/test_models.py tests/test_migrations.py
git commit -m "Notavel: empresa, despachos, cotacao e a coluna de pagamento da nota"
```

---

### Task 3: A casa de software e a fila de despachos, semeadas

A §2 da spec pede uma casa de desenvolvimento de software de porte pequeno. Os seeds financeiros que já existem descrevem uma agência de branding ("Consultoria de branding", "identidade visual", "gestão de tráfego pago"). Esta task troca a ficção inteira para software, acrescenta a empresa e a fila de despachos.

Serviço, e não comércio, é o que dá o Anexo III, o Anexo V e o Fator R. Software, e não clínica ou arquitetura, é o caso clássico que todo contador brasileiro reconhece. Sem essa troca, o CNAE no cabeçalho seria enfeite.

**Files:**
- Modify: `app/lab/seeds_demo.py` (`_semear_financeiro` e as constantes do topo)
- Test: `tests/lab/test_seeds.py`

**Interfaces:**
- Consumes: `LabEmpresaFin`, `LabDespacho` (Task 2); `_cnpj_ficticio` (já existe no módulo).
- Produces: `semear_empresa_fin(db, sandbox_id) -> LabEmpresaFin` (pública, consumida pela Task 5); constantes exportadas `EMPRESA_FIN_NOME`, `EMPRESA_FIN_CNAE`, `EMPRESA_FIN_CNAE_DESCRICAO`, `EMPRESA_FIN_REGIME`, `EMPRESA_FIN_RBT12_CENTAVOS`, `EMPRESA_FIN_FOLHA12_CENTAVOS`, `EMPRESA_FIN_SALDO_CORRENTE_CENTAVOS`, `EMPRESA_FIN_SALDO_APLICACAO_CENTAVOS`. Uma `LabEmpresaFin` e cinco `LabDespacho` por sandbox.

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/lab/test_seeds.py` (e some `LabDespacho` e `LabEmpresaFin` aos imports do topo):

```python
def test_a_empresa_do_notavel_e_uma_casa_de_software_no_simples(db):
    """§2 da spec. Serviço, e não comércio, é o que faz o Anexo III, o
    Anexo V e o Fator R existirem. Software, e não outra prestação de
    serviço, é o caso clássico do Fator R que um contador reconhece na
    hora, e reconhecer o dilema na tela é o que faz o visitante da área
    concluir que quem construiu entende do ofício."""
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    empresa = db.query(LabEmpresaFin).filter(
        LabEmpresaFin.sandbox_id == sandbox.id).one()
    assert empresa.origem == "seed"
    assert "fictícia" in empresa.nome
    assert empresa.cnae.startswith("6201")
    assert "software" in empresa.cnae_descricao.lower() or \
           "programas" in empresa.cnae_descricao.lower()
    assert empresa.regime == "Simples Nacional"


def test_o_anexo_semeado_e_o_que_o_fator_r_manda(db):
    """A empresa não declara "III" porque alguém digitou: ela declara o que
    a razão entre folha e faturamento decide. Se um dia os dois números
    mudarem sem o anexo mudar junto, o cabeçalho do painel mostraria um
    anexo que a própria calculadora do corte 2 contradiz."""
    from app.lab import fiscal

    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    empresa = db.query(LabEmpresaFin).filter(
        LabEmpresaFin.sandbox_id == sandbox.id).one()
    assert empresa.anexo == fiscal.anexo_pelo_fator_r(
        empresa.folha12_centavos, empresa.rbt12_centavos)
    assert empresa.anexo == "III"


def test_a_fila_nasce_com_cinco_despachos_pendentes(db):
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    despachos = db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id).all()
    assert len(despachos) == 5
    assert all(d.status == "pendente" for d in despachos)
    assert all(d.origem == "seed" for d in despachos)
    assert all(d.valor_centavos > 0 for d in despachos)
    assert all(d.categoria for d in despachos)


def test_um_despacho_da_fila_nao_cabe_no_saldo_disponivel(db):
    """§5.3 é a peça central da demonstração, e ela só acontece se houver
    um despacho ACIMA do saldo em conta corrente esperando na fila. Sem
    este teste, alguém ajusta um valor da semente um dia e o fluxo mais
    importante do Notável desaparece em silêncio."""
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    empresa = db.query(LabEmpresaFin).filter(
        LabEmpresaFin.sandbox_id == sandbox.id).one()
    despachos = db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id).all()
    acima = [d for d in despachos
             if d.valor_centavos > empresa.saldo_corrente_centavos]
    assert len(acima) == 1, "a fila precisa de exatamente um despacho impagável"


def test_o_resto_da_fila_cabe_no_saldo_um_por_um(db):
    """O contrário também importa: se todos coubessem, não haveria recusa;
    se nenhum coubesse, aprovar nunca funcionaria e a recusa pareceria o
    comportamento normal em vez da exceção que ela é."""
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    empresa = db.query(LabEmpresaFin).filter(
        LabEmpresaFin.sandbox_id == sandbox.id).one()
    despachos = db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id).all()
    cabem = [d for d in despachos
             if d.valor_centavos <= empresa.saldo_corrente_centavos]
    assert len(cabem) == 4


def test_o_pulso_tem_um_recebivel_para_quitar(db):
    """§4: o pulso quita um recebível que está VISÍVEL na tela. Ele só
    existe se a semente deixar pelo menos uma nota emitida e não paga."""
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    abertas = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id,
        LabNota.status == "emitida",
        LabNota.pago_em.is_(None),
    ).count()
    assert abertas >= 2


def test_a_ficcao_financeira_fala_de_software_e_nao_de_agencia(db):
    """A empresa é casa de software: item de nota e lançamento não podem
    continuar falando de branding e identidade visual, senão o cabeçalho
    diz uma coisa e o extrato diz outra."""
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    textos = []
    for nota in db.query(LabNota).filter(LabNota.sandbox_id == sandbox.id):
        textos.extend(item["descricao"] for item in nota.itens)
    for lanc in db.query(LabLancamento).filter(
            LabLancamento.sandbox_id == sandbox.id):
        textos.append(lanc.descricao)
    junto = " ".join(textos).lower()
    for palavra in ("branding", "identidade visual", "tráfego pago", "fotos"):
        assert palavra not in junto, palavra
```

Some `LabEmpresaFin` e `LabDespacho` à lista de `test_todos_os_registros_semeados_tem_origem_seed`.

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_seeds.py -q`
Expected: FAIL, `NoResultFound` na consulta da empresa e zero despachos.

- [ ] **Step 3: Constantes da empresa**

Em `app/lab/seeds_demo.py`, junto das constantes do topo (perto de `EMPRESA_RH`):

```python
# ------------------------------------------------- empresa do Notável ----
# Casa de desenvolvimento de software de porte pequeno (§2 da spec do
# Notável). Os dois números de 12 meses não são decorativos: a razão entre
# eles é o Fator R, e é ela que decide o anexo declarado abaixo.
#
#   Fator R = 520.000 / 1.480.000 = 35,13%, acima do corte de 28%
#   logo: Anexo III, faixa 4, alíquota efetiva de 13,59%
#
# Trocar um destes números sem recalcular o anexo faz o cabeçalho do painel
# contradizer a calculadora do corte 2. `tests/lab/test_seeds.py` amarra os
# dois com `fiscal.anexo_pelo_fator_r`.
EMPRESA_FIN_NOME = "Marco Zero Software Ltda (empresa fictícia)"
EMPRESA_FIN_CNAE = "6201-5/01"
EMPRESA_FIN_CNAE_DESCRICAO = (
    "Desenvolvimento de programas de computador sob encomenda")
EMPRESA_FIN_REGIME = "Simples Nacional"
EMPRESA_FIN_RBT12_CENTAVOS = 1_480_000_00
EMPRESA_FIN_FOLHA12_CENTAVOS = 520_000_00
# Conta corrente é o único saldo DISPONÍVEL para aprovar despacho
# (`app/lab/notavel.py::saldos`). A aplicação aparece na faixa de saldos e
# não entra nessa conta: é essa distinção que dá o fluxo da §5.3.
EMPRESA_FIN_SALDO_CORRENTE_CENTAVOS = 84_320_00
EMPRESA_FIN_SALDO_APLICACAO_CENTAVOS = 210_000_00
```

- [ ] **Step 4: Semear a empresa e os despachos**

Em `app/lab/seeds_demo.py`, a empresa nasce numa função PRÓPRIA e pública (sem sublinhado), logo acima de `_semear_financeiro`. Pública porque a Task 5 vai chamá-la de fora: um sandbox criado antes deste deploy existe no ar sem empresa, e o painel precisa poder criar a que falta em vez de estourar.

```python
def semear_empresa_fin(db: Session, sandbox_id: int) -> LabEmpresaFin:
    """A empresa do Notável, criada e devolvida.

    Pública, e chamada de dois lugares: de `_semear_financeiro` no
    nascimento normal do sandbox, e de `app/lab/notavel.py` quando o painel
    encontra um sandbox SEM empresa. O segundo caso é real e não é
    hipótese: quando este código subir, já haverá sandbox de 24h no ar,
    criado por uma versão que não semeava empresa nenhuma, e o visitante
    dele não pode receber um erro por ter chegado cedo demais.

    Não comita: quem chama decide a transação.
    """
    empresa = LabEmpresaFin(
        sandbox_id=sandbox_id, origem="seed",
        nome=EMPRESA_FIN_NOME,
        cnpj=_cnpj_ficticio("321654980001"),
        cnae=EMPRESA_FIN_CNAE,
        cnae_descricao=EMPRESA_FIN_CNAE_DESCRICAO,
        regime=EMPRESA_FIN_REGIME,
        # o anexo é DERIVADO do Fator R, nunca digitado: ver o comentário
        # das constantes acima
        anexo=anexo_pelo_fator_r(EMPRESA_FIN_FOLHA12_CENTAVOS,
                                 EMPRESA_FIN_RBT12_CENTAVOS),
        rbt12_centavos=EMPRESA_FIN_RBT12_CENTAVOS,
        folha12_centavos=EMPRESA_FIN_FOLHA12_CENTAVOS,
        saldo_corrente_centavos=EMPRESA_FIN_SALDO_CORRENTE_CENTAVOS,
        saldo_aplicacao_centavos=EMPRESA_FIN_SALDO_APLICACAO_CENTAVOS,
    )
    db.add(empresa)
    db.flush()
    return empresa
```

E as duas primeiras linhas de `_semear_financeiro` passam a ser:

```python
def _semear_financeiro(db: Session, sandbox_id: int) -> None:
    agora = _agora()
    hoje = agora.date()
    semear_empresa_fin(db, sandbox_id)
```

E, ao final da função, depois dos lançamentos:

```python
    # Fila de despachos (§5.2). Quatro cabem no saldo em conta corrente
    # (R$ 84.320,00) e o quinto não cabe DE PROPÓSITO: é ele que dá o fluxo
    # da §5.3, em que o visitante clica achando que vai passar e o sistema
    # recusa com a diferença na tela. Faltam R$ 12.180,00.
    #
    # O pulso da chegada quita a nota mais antiga (R$ 3.500,00) e o saldo
    # sobe para R$ 87.820,00: continua abaixo do quinto despacho, então a
    # recusa sobrevive ao pulso. Mexeu num destes números, confira o outro.
    despachos_dados = [
        ("Provedor de nuvem, fatura mensal", 6_480_00, 3, "Fornecedor"),
        ("Aluguel da sala comercial", 7_200_00, 2, "Aluguel"),
        ("Licenças de ferramentas da equipe", 3_940_00, 8, "Fornecedor"),
        ("DAS do Simples Nacional, competência 07/2026", 19_870_00, 5, "Imposto"),
        ("Adiantamento de 13º da equipe", 96_500_00, 12, "Folha"),
    ]
    db.add_all([
        LabDespacho(
            sandbox_id=sandbox_id, origem="seed",
            fornecedor=fornecedor, valor_centavos=valor,
            vence_em=hoje + dt.timedelta(days=dias),
            categoria=categoria,
            criado_em=agora - dt.timedelta(days=1),
        )
        for fornecedor, valor, dias, categoria in despachos_dados
    ])
```

Some `LabDespacho` e `LabEmpresaFin` ao bloco de imports de `.models`, e `from .fiscal import anexo_pelo_fator_r` aos imports do módulo.

- [ ] **Step 5: Trocar a ficção de agência por ficção de software**

Ainda em `_semear_financeiro`, troque as descrições dos itens de nota:

```python
    notas_dados = [
        (aurora, [_item("Sustentação de aplicação, mensalidade", 1, 350000)], "emitida", 5),
        (nordeste, [_item("Desenvolvimento de módulo de integração", 1, 480000)], "emitida", 4),
        (vetor, [_item("Consultoria técnica, hora avulsa", 4, 60000)], "emitida", 3),
        (mercado_search, [
            _item("Squad dedicado, mensalidade", 1, 220000),
            _item("Ambiente de homologação, mensalidade", 1, 30000),
        ], "emitida", 2),
        (aurora, [_item("Prova de conceito, escopo revisado", 1, 180000)], "cancelada", 1),
        (nordeste, [
            _item("Manutenção evolutiva, pacote trimestral", 1, 90000),
            _item("Chamado fora do escopo contratado", 2, 15000),
        ], "emitida", 0),
    ]
```

E as três descrições de lançamento que ainda falam de agência:

```python
        ("Recebimento de cliente, desenvolvimento de módulo", 550000,
         "receita_de_servico",
         "Entrada compatível com pagamento de serviço prestado, valor positivo e descrição de cliente."),
        ...
        ("Recebimento de cliente, squad dedicado do mês", 220000,
         "receita_de_servico",
         "Pagamento de cliente por serviço de desenvolvimento prestado no período."),
        ...
        ("Assinatura de ferramentas de desenvolvimento e infraestrutura", -29000,
         "despesa_operacional",
         "Ferramenta usada na operação do negócio, despesa recorrente necessária à atividade."),
```

A segunda linha ("consultoria estratégica mensal") já serve a uma casa de software e fica como está.

- [ ] **Step 6: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_seeds.py -q`
Expected: PASS.

- [ ] **Step 7: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1490 passed, zero falha.

- [ ] **Step 8: Commit**

```bash
git add app/lab/seeds_demo.py tests/lab/test_seeds.py
git commit -m "Notavel: semente da casa de software e da fila de despachos"
```

---

### Task 4: Câmbio do Banco Central

Duas regras, as duas achadas testando a API em 25/08/2026 (§8 da spec, mais um achado novo desta medição): **uma chamada por dia, guardada**, e **queda para a última cotação conhecida**. A medição mostrou que a lista vem vazia não só no sábado e no domingo, mas também na manhã de um dia útil, antes de o PTAX do dia fechar. A queda, portanto, não é caso de borda de fim de semana: é o caso comum.

O painel **nunca espera a rede**. A tela lê o cache e renderiza; a atualização acontece em segundo plano, depois da resposta ter saído. É o que garante o "abre em menos de um segundo" da §14.

**Files:**
- Create: `app/lab/cambio.py`
- Create: `tests/lab/test_cambio.py`

**Interfaces:**
- Consumes: `LabCotacao` (Task 2).
- Produces:
  - `MOEDAS: tuple[str, ...]` = `("USD", "EUR", "GBP")`
  - `COTACOES_DE_PARTIDA: dict[str, tuple[int, dt.date]]`
  - `cotacoes(db: Session) -> list[dict]` com as chaves `moeda`, `nome`, `valor`, `dia_cotacao`, `de_partida`
  - `precisa_atualizar(db: Session, hoje: dt.date | None = None) -> bool`
  - `async atualizar(db: Session, hoje: dt.date | None = None) -> int`
  - `formatar(venda_dezmilesimos: int) -> str`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/lab/test_cambio.py`:

```python
"""Câmbio do Notável (§8 da spec).

Nenhum teste aqui toca a rede: `atualizar` recebe a resposta por um cliente
httpx falso, montado com `httpx.MockTransport`. Teste que depende do Banco
Central estar no ar é teste que falha por motivo alheio ao código.

`asyncio.run` em teste síncrono é a convenção deste repo para função
assíncrona (ver `tests/test_ordem_destaques_home.py` e
`tests/test_admin_profile_about_imgs.py`): a suíte não tem pytest-asyncio
nem o plugin do anyio ligado, e acrescentar um por causa de um arquivo
seria trazer dependência de teste para dentro do `requirements.txt`.
"""
import asyncio
import datetime as dt

import httpx

from app.lab import cambio
from app.lab.models import LabCotacao

HOJE = dt.date(2026, 8, 25)


def _resposta(valor: float, quando: str):
    return {"value": [{"cotacaoVenda": valor, "dataHoraCotacao": quando,
                       "tipoBoletim": "Fechamento"}]}


def _transporte(por_moeda: dict):
    """MockTransport que devolve a cotação de cada moeda pela query, e uma
    lista vazia para moeda que não estiver no dicionário (que é o que a API
    de verdade faz em sábado, domingo, feriado e manhã de dia útil)."""
    def responder(request: httpx.Request) -> httpx.Response:
        alvo = next((m for m in cambio.MOEDAS if f"'{m}'" in str(request.url)), None)
        corpo = por_moeda.get(alvo, {"value": []})
        return httpx.Response(200, json=corpo)
    return httpx.MockTransport(responder)


# ------------------------------------------------------------- leitura ---

def test_sem_nenhuma_linha_no_banco_o_painel_ainda_tem_cambio(db):
    """§8: "o painel nunca fica sem câmbio". Banco vazio cai nas cotações
    de partida, que são medições reais com a data delas, e a tela mostra
    essa data. Sem esse piso, o primeiro visitante do dia veria a região
    de câmbio em branco enquanto a atualização em segundo plano roda."""
    linhas = cambio.cotacoes(db)
    assert [l["moeda"] for l in linhas] == list(cambio.MOEDAS)
    assert all(l["de_partida"] is True for l in linhas)
    assert all(l["valor"] for l in linhas)
    assert all(isinstance(l["dia_cotacao"], dt.date) for l in linhas)


def test_o_que_esta_guardado_ganha_da_cotacao_de_partida(db):
    db.add(LabCotacao(moeda="USD", venda_dezmilesimos=52000,
                      dia_cotacao=dt.date(2026, 8, 24)))
    db.commit()
    por_moeda = {l["moeda"]: l for l in cambio.cotacoes(db)}
    assert por_moeda["USD"]["valor"] == "5,2000"
    assert por_moeda["USD"]["de_partida"] is False
    assert por_moeda["EUR"]["de_partida"] is True


def test_a_ordem_das_moedas_e_sempre_a_mesma(db):
    """Moeda que troca de lugar entre duas visitas parece bug. A ordem vem
    de `MOEDAS`, nunca do que o banco devolveu primeiro."""
    db.add(LabCotacao(moeda="GBP", venda_dezmilesimos=70216,
                      dia_cotacao=dt.date(2026, 8, 24)))
    db.commit()
    assert [l["moeda"] for l in cambio.cotacoes(db)] == ["USD", "EUR", "GBP"]


def test_formatar_usa_virgula_e_quatro_casas():
    assert cambio.formatar(51512) == "5,1512"
    assert cambio.formatar(60089) == "6,0089"
    assert cambio.formatar(100000) == "10,0000"


# --------------------------------------------------------- quando buscar --

def test_banco_vazio_precisa_atualizar(db):
    assert cambio.precisa_atualizar(db, HOJE) is True


def test_buscado_hoje_nao_busca_de_novo(db):
    """Uma chamada por dia (§8): chamar a cada visita é lento para o
    visitante e rude com um serviço público."""
    for moeda in cambio.MOEDAS:
        db.add(LabCotacao(
            moeda=moeda, venda_dezmilesimos=50000,
            dia_cotacao=dt.date(2026, 8, 24),
            buscado_em=dt.datetime(2026, 8, 25, 9, 0, tzinfo=dt.timezone.utc),
        ))
    db.commit()
    assert cambio.precisa_atualizar(db, HOJE) is False


def test_buscado_ontem_busca_de_novo(db):
    for moeda in cambio.MOEDAS:
        db.add(LabCotacao(
            moeda=moeda, venda_dezmilesimos=50000,
            dia_cotacao=dt.date(2026, 8, 23),
            buscado_em=dt.datetime(2026, 8, 24, 9, 0, tzinfo=dt.timezone.utc),
        ))
    db.commit()
    assert cambio.precisa_atualizar(db, HOJE) is True


def test_uma_moeda_faltando_ja_manda_buscar(db):
    """Uma tentativa parcial (a rede caiu no meio) não pode ser tratada
    como dia resolvido, senão a moeda que faltou espera até amanhã."""
    db.add(LabCotacao(
        moeda="USD", venda_dezmilesimos=51512, dia_cotacao=dt.date(2026, 8, 24),
        buscado_em=dt.datetime(2026, 8, 25, 9, 0, tzinfo=dt.timezone.utc),
    ))
    db.commit()
    assert cambio.precisa_atualizar(db, HOJE) is True


# ------------------------------------------------------------ atualizar ---

def test_atualizar_grava_as_tres_moedas(db):
    transporte = _transporte({
        "USD": _resposta(5.1512, "2026-08-24 13:04:14.216099"),
        "EUR": _resposta(6.0089, "2026-08-24 13:04:14.216099"),
        "GBP": _resposta(7.0216, "2026-08-24 13:04:14.216099"),
    })
    gravadas = asyncio.run(cambio.atualizar(db, HOJE, transporte=transporte))
    assert gravadas == 3
    por_moeda = {c.moeda: c for c in db.query(LabCotacao).all()}
    assert por_moeda["USD"].venda_dezmilesimos == 51512
    assert por_moeda["GBP"].venda_dezmilesimos == 70216
    assert por_moeda["EUR"].dia_cotacao == dt.date(2026, 8, 24)


def test_atualizar_reescreve_a_linha_em_vez_de_empilhar(db):
    """Uma linha por moeda, para sempre. Empilhar viraria um log que cresce
    todo dia útil para servir sempre a última linha."""
    transporte = _transporte({"USD": _resposta(5.1512, "2026-08-24 13:04:14.2")})
    asyncio.run(cambio.atualizar(db, HOJE, transporte=transporte))
    transporte2 = _transporte({"USD": _resposta(5.2000, "2026-08-25 13:04:14.2")})
    asyncio.run(cambio.atualizar(db, dt.date(2026, 8, 26), transporte=transporte2))
    linhas = db.query(LabCotacao).filter(LabCotacao.moeda == "USD").all()
    assert len(linhas) == 1
    assert linhas[0].venda_dezmilesimos == 52000


def test_lista_vazia_no_fim_de_semana_preserva_a_ultima_conhecida(db):
    """A API responde `{"value": []}` em sábado, domingo, feriado e na
    manhã de dia útil, antes de o PTAX fechar. Medido em 25/08/2026: nesse
    dia útil, às 15h UTC, USD veio vazio e a última cotação era de 24/08.

    Sem esta queda, o painel abriria em branco justamente no fim de semana,
    que é quando alguém navega portfólio."""
    db.add(LabCotacao(moeda="USD", venda_dezmilesimos=51512,
                      dia_cotacao=dt.date(2026, 8, 24)))
    db.commit()
    gravadas = asyncio.run(cambio.atualizar(db, dt.date(2026, 8, 29),
                                            transporte=_transporte({})))
    assert gravadas == 0
    guardada = db.query(LabCotacao).filter(LabCotacao.moeda == "USD").one()
    assert guardada.venda_dezmilesimos == 51512
    assert guardada.dia_cotacao == dt.date(2026, 8, 24)


def test_api_fora_do_ar_nao_derruba_nada(db):
    """Erro de rede, 500 ou JSON quebrado não podem virar exceção: esta
    função roda depois da resposta ter saído, e uma exceção aqui
    apareceria no log do servidor como se o painel tivesse falhado."""
    def cair(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede")

    gravadas = asyncio.run(cambio.atualizar(db, HOJE,
                                            transporte=httpx.MockTransport(cair)))
    assert gravadas == 0
    assert cambio.cotacoes(db)  # o painel continua com câmbio


def test_resposta_com_corpo_estranho_nao_derruba_nada(db):
    def estranho(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>manutenção</html>")

    gravadas = asyncio.run(cambio.atualizar(db, HOJE,
                                            transporte=httpx.MockTransport(estranho)))
    assert gravadas == 0


def test_cotacao_negativa_ou_zero_e_descartada(db):
    """Valor que não faz sentido é dado corrompido, e gravar dado
    corrompido por cima de uma cotação boa é pior do que não atualizar."""
    transporte = _transporte({"USD": _resposta(0, "2026-08-24 13:04:14.2")})
    assert asyncio.run(cambio.atualizar(db, HOJE, transporte=transporte)) == 0
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_cambio.py -q`
Expected: FAIL na coleta, `ModuleNotFoundError: No module named 'app.lab.cambio'`.

- [ ] **Step 3: Escrever `app/lab/cambio.py`**

```python
"""Cotação do dia no painel do Notável (§8 da spec).

FONTE

API PTAX do Banco Central, aberta, sem chave e sem cadastro:
`olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/`. Um serviço
público, o que impõe uma obrigação: não bater nele a cada visita.

AS DUAS REGRAS, AS DUAS ACHADAS TESTANDO A API

1. UMA CHAMADA POR DIA, GUARDADA. A cotação do dia é gravada e servida do
   banco. `precisa_atualizar` é quem decide, e ele olha `buscado_em`, não
   `dia_cotacao`: em sábado a cotação continua sendo a de sexta, e ainda
   assim a busca do sábado já aconteceu.

2. QUEDA PARA A ÚLTIMA CONHECIDA. A API responde `{"value": []}` quando não
   há PTAX para o período pedido. Medido em 25/08/2026: sábado e domingo
   vazios, como esperado, MAS a manhã do próprio dia útil também vem vazia,
   porque o boletim de fechamento sai por volta das 13h. A queda não é caso
   de borda de fim de semana, é o caso comum de metade do dia.

   A consulta usa `CotacaoMoedaPeriodo` numa janela de dez dias, ordenada
   por data decrescente, pedindo um registro só. Assim uma única chamada
   por moeda já resolve fim de semana, feriado e manhã de dia útil, sem
   laço andando para trás dia a dia.

O PAINEL NUNCA ESPERA A REDE

`cotacoes()` é síncrona e lê só o banco: é o que a tela chama, e ela
responde no tempo de uma consulta indexada. `atualizar()` é assíncrona e
roda em `BackgroundTasks`, DEPOIS da resposta ter saído. Um Banco Central
lento não pode atrasar a chegada do painel, que a §14 exige em menos de um
segundo.

Banco vazio cai em `COTACOES_DE_PARTIDA`, medições reais com a data delas.
É o piso que faz "o painel nunca fica sem câmbio" ser verdade inclusive no
primeiro acesso de uma instalação nova.
"""
from __future__ import annotations

import datetime as dt

import httpx
from sqlalchemy.orm import Session

from .models import LabCotacao

MOEDAS = ("USD", "EUR", "GBP")

NOMES = {
    "USD": "Dólar americano",
    "EUR": "Euro",
    "GBP": "Libra esterlina",
}

# Cotações medidas na API em 25/08/2026, boletim de fechamento de
# 24/08/2026. Piso para banco vazio: a tela mostra o valor E a data, então
# um número de partida antigo nunca é apresentado como se fosse de hoje.
COTACOES_DE_PARTIDA: dict[str, tuple[int, dt.date]] = {
    "USD": (51512, dt.date(2026, 8, 24)),
    "EUR": (60089, dt.date(2026, 8, 24)),
    "GBP": (70216, dt.date(2026, 8, 24)),
}

_BASE = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
         "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
         "dataFinalCotacao=@dataFinalCotacao)")

# Dez dias cobrem fim de semana emendado com feriado prolongado e ainda
# sobra folga. Mais que isso só faria a API filtrar mais linhas para
# devolver a mesma única.
JANELA_DIAS = 10
TIMEOUT_SEGUNDOS = 6.0


def formatar(venda_dezmilesimos: int) -> str:
    """51512 -> "5,1512". Quatro casas, vírgula decimal, que é como o
    próprio Banco Central publica."""
    inteiro, resto = divmod(int(venda_dezmilesimos), 10_000)
    return f"{inteiro},{resto:04d}"


def cotacoes(db: Session) -> list[dict]:
    """O que a região de câmbio do painel desenha, na ordem de `MOEDAS`.

    Síncrona e sem rede de propósito: ver o cabeçalho do módulo.
    """
    guardadas = {c.moeda: c for c in db.query(LabCotacao).all()}
    linhas = []
    for moeda in MOEDAS:
        guardada = guardadas.get(moeda)
        if guardada is not None and guardada.venda_dezmilesimos > 0:
            valor, dia, de_partida = (guardada.venda_dezmilesimos,
                                      guardada.dia_cotacao, False)
        else:
            valor, dia = COTACOES_DE_PARTIDA[moeda]
            de_partida = True
        linhas.append({
            "moeda": moeda,
            "nome": NOMES[moeda],
            "valor": formatar(valor),
            "dia_cotacao": dia,
            "de_partida": de_partida,
        })
    return linhas


def precisa_atualizar(db: Session, hoje: dt.date | None = None) -> bool:
    """True quando falta moeda no banco ou quando a busca de hoje ainda não
    aconteceu. Olha `buscado_em`, não `dia_cotacao`, pelo motivo do
    cabeçalho do módulo.

    Uma moeda faltando já manda buscar: uma tentativa parcial (a rede caiu
    no meio) não pode ser tratada como dia resolvido, senão a moeda que
    faltou espera até amanhã.
    """
    hoje = hoje or dt.datetime.now(dt.timezone.utc).date()
    guardadas = {c.moeda: c for c in db.query(LabCotacao).all()}
    for moeda in MOEDAS:
        guardada = guardadas.get(moeda)
        if guardada is None:
            return True
        buscado = guardada.buscado_em
        if buscado is None:
            return True
        if buscado.tzinfo is None:
            buscado = buscado.replace(tzinfo=dt.timezone.utc)
        if buscado.date() < hoje:
            return True
    return False


def _url(moeda: str, hoje: dt.date) -> str:
    inicio = hoje - dt.timedelta(days=JANELA_DIAS)
    return (
        f"{_BASE}?@moeda='{moeda}'"
        f"&@dataInicial='{inicio:%m-%d-%Y}'"
        f"&@dataFinalCotacao='{hoje:%m-%d-%Y}'"
        "&$format=json"
        "&$select=cotacaoVenda,dataHoraCotacao"
        "&$orderby=dataHoraCotacao desc"
        "&$top=1"
    )


def _ler_resposta(corpo: dict) -> tuple[int, dt.date] | None:
    """Extrai `(venda_dezmilesimos, dia)` do primeiro registro, ou None.

    None cobre tudo que não é uma cotação utilizável: lista vazia (fim de
    semana, feriado, manhã de dia útil), campo ausente, formato de data
    diferente do esperado e valor zero ou negativo. Quem chama trata None
    como "não atualiza", e a última cotação conhecida continua valendo.
    """
    registros = corpo.get("value") or []
    if not registros:
        return None
    registro = registros[0]
    try:
        venda = float(registro["cotacaoVenda"])
        quando = str(registro["dataHoraCotacao"])[:10]
        dia = dt.date.fromisoformat(quando)
    except (KeyError, TypeError, ValueError):
        return None
    if venda <= 0:
        return None
    return round(venda * 10_000), dia


async def atualizar(db: Session, hoje: dt.date | None = None,
                    transporte: httpx.BaseTransport | None = None) -> int:
    """Busca as três moedas e grava o que vier de útil. Devolve quantas
    foram gravadas.

    NUNCA levanta. Roda em `BackgroundTasks`, depois da resposta ter saído:
    uma exceção aqui apareceria no log como se o painel tivesse falhado,
    quando na verdade o visitante recebeu a tela inteira e correta, com a
    cotação anterior. `transporte` existe só para o teste injetar um
    `httpx.MockTransport`; em produção fica None.
    """
    hoje = hoje or dt.datetime.now(dt.timezone.utc).date()
    agora = dt.datetime.now(dt.timezone.utc)
    gravadas = 0
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEGUNDOS,
                                     transport=transporte) as cliente:
            for moeda in MOEDAS:
                try:
                    resposta = await cliente.get(_url(moeda, hoje))
                    lida = _ler_resposta(resposta.json())
                except Exception:
                    lida = None  # rede, status, JSON: o mesmo desfecho
                if lida is None:
                    continue
                venda, dia = lida
                linha = (db.query(LabCotacao)
                         .filter(LabCotacao.moeda == moeda).one_or_none())
                if linha is None:
                    linha = LabCotacao(moeda=moeda)
                    db.add(linha)
                linha.venda_dezmilesimos = venda
                linha.dia_cotacao = dia
                linha.buscado_em = agora
                gravadas += 1
        if gravadas:
            db.commit()
    except Exception:
        db.rollback()
        return 0
    return gravadas
```

- [ ] **Step 4: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_cambio.py -q`
Expected: PASS, 13 testes.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1503 passed, zero falha.

- [ ] **Step 6: Commit**

```bash
git add app/lab/cambio.py tests/lab/test_cambio.py
git commit -m "Notavel: cambio do Banco Central com cache diario e queda para a ultima conhecida"
```

---

### Task 5: Trilha compartilhada e a leitura do painel

O painel lê. Esta task entrega tudo que a tela desenha antes de qualquer clique: saldos, série do KPI, fila, lançamentos, cabeçalho fiscal. As escritas vêm nas Tasks 6 e 7.

A trilha de auditoria sai de `admita.py` para um módulo próprio no mesmo movimento, porque agora ela tem dois donos. Quatro linhas duplicadas entre duas demos seria a primeira das duas divergirem no dia em que uma ganhasse um campo.

**Files:**
- Create: `app/lab/auditoria.py`
- Create: `app/lab/notavel.py`
- Create: `tests/lab/test_notavel.py`
- Modify: `app/lab/admita.py` (`_registrar` delega)

**Interfaces:**
- Consumes: `LabEmpresaFin`, `LabDespacho` (Task 2); `semear_empresa_fin` (Task 3); `cambio.cotacoes` (Task 4); `fiscal.aliquota_efetiva_bps`, `fiscal.formatar_aliquota`, `fiscal.VIGENCIA_ROTULO` (Task 1); `formatar_reais` de `app/services/formato.py`.
- Produces:
  - `auditoria.registrar(db, sandbox, quem: str, acao: str) -> None`
  - `auditoria.ultimas(db, sandbox, quantas: int = 8) -> list[LabAuditoria]`
  - `notavel.USUARIO_FIN: str`, `notavel.USUARIO_FIN_PERFIL: str`
  - `notavel.empresa_da_sandbox(db, sandbox) -> LabEmpresaFin`
  - `notavel.saldos(db, sandbox) -> dict`
  - `notavel.serie_saldo(db, sandbox, dias=30, hoje=None) -> list[int]`
  - `notavel.montar_contexto(db, sandbox, linhas_de_cambio) -> dict`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/lab/test_notavel.py`:

```python
"""Domínio e rotas do Notável (Tasks 5 a 7).

Os testes de leitura usam o fixture `db` de `tests/conftest.py` (SQLite em
memória, isolado por teste). Os de rota usam `client`/`db_session` de
`tests/lab/conftest.py`, que sobem o app de verdade.
"""
import datetime as dt

from app.lab import auditoria, cambio, notavel
from app.lab.models import (
    LabAuditoria,
    LabClienteFiscal,
    LabDespacho,
    LabEmpresaFin,
    LabLancamento,
    LabNota,
    LabSandbox,
)
from app.lab.seeds_demo import semear_cenario


def _sandbox(db, demo="fin"):
    sandbox = LabSandbox(
        token=f"tok{db.query(LabSandbox).count()}",
        demo_origem=demo,
        expira_em=dt.datetime.now(dt.UTC) + dt.timedelta(hours=24),
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    return sandbox


def _semeado(db):
    sandbox = _sandbox(db)
    semear_cenario(db, sandbox)
    return sandbox


# ------------------------------------------------------------ auditoria --

def test_registrar_grava_uma_linha_com_quem_e_o_que(db):
    sandbox = _sandbox(db)
    auditoria.registrar(db, sandbox, "Fulano", "aprovou o despacho 3")
    db.commit()
    linha = db.query(LabAuditoria).one()
    assert linha.quem == "Fulano"
    assert linha.acao == "aprovou o despacho 3"
    assert linha.origem == "visitante"


def test_registrar_corta_acao_comprida_em_vez_de_estourar(db):
    """A coluna é String(200). Texto maior chegaria ao banco e quebraria a
    ação inteira que o visitante acabou de fazer, por causa do texto do
    LOG dela."""
    sandbox = _sandbox(db)
    auditoria.registrar(db, sandbox, "F", "x" * 500)
    db.commit()
    assert len(db.query(LabAuditoria).one().acao) == 200


def test_ultimas_vem_da_mais_nova_para_a_mais_velha(db):
    sandbox = _sandbox(db)
    for i in range(12):
        auditoria.registrar(db, sandbox, "F", f"acao {i}")
    db.commit()
    linhas = auditoria.ultimas(db, sandbox, quantas=5)
    assert len(linhas) == 5
    assert linhas[0].acao == "acao 11"


def test_a_trilha_de_um_sandbox_e_invisivel_ao_outro(db):
    a, b = _sandbox(db), _sandbox(db)
    auditoria.registrar(db, a, "F", "só do A")
    db.commit()
    assert auditoria.ultimas(db, b) == []


def test_admita_continua_registrando_pelo_modulo_novo(db):
    """`admita._registrar` virou um repasse. Se ele parar de gravar, a
    esteira perde a trilha em silêncio."""
    from app.lab import admita as admita_dados

    sandbox = _sandbox(db, demo="rh")
    admita_dados._registrar(db, sandbox, "RH", "moveu alguém")
    db.commit()
    assert db.query(LabAuditoria).count() == 1


# --------------------------------------------------------------- saldos --

def test_empresa_da_sandbox_cria_a_que_falta(db):
    """Sandbox criado antes deste deploy não tem empresa. O painel não pode
    estourar para quem chegou cedo demais: ele semeia a que falta."""
    sandbox = _sandbox(db)
    assert db.query(LabEmpresaFin).count() == 0
    empresa = notavel.empresa_da_sandbox(db, sandbox)
    assert empresa.sandbox_id == sandbox.id
    assert empresa.origem == "seed"
    # e não cria uma segunda na chamada seguinte
    notavel.empresa_da_sandbox(db, sandbox)
    assert db.query(LabEmpresaFin).count() == 1


def test_a_receber_soma_so_nota_emitida_e_nao_paga(db):
    """Nota cancelada não é recebível, e nota já paga também não. Este é o
    número grande do KPI: errar aqui é errar a primeira coisa que o
    visitante lê."""
    sandbox = _semeado(db)
    esperado = sum(
        n.total_centavos for n in db.query(LabNota).filter(
            LabNota.sandbox_id == sandbox.id,
            LabNota.status == "emitida",
            LabNota.pago_em.is_(None),
        )
    )
    assert notavel.saldos(db, sandbox)["a_receber_centavos"] == esperado
    assert esperado == 1_440_00


def test_nota_cancelada_fica_de_fora_do_a_receber(db):
    sandbox = _semeado(db)
    antes = notavel.saldos(db, sandbox)["a_receber_centavos"]
    nota = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "emitida").first()
    nota.status = "cancelada"
    db.commit()
    assert notavel.saldos(db, sandbox)["a_receber_centavos"] == \
        antes - nota.total_centavos


def test_a_pagar_soma_so_despacho_pendente(db):
    sandbox = _semeado(db)
    saldos = notavel.saldos(db, sandbox)
    assert saldos["a_pagar_centavos"] == 133_990_00
    despacho = db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id).first()
    despacho.status = "recusado"
    db.commit()
    assert notavel.saldos(db, sandbox)["a_pagar_centavos"] == \
        133_990_00 - despacho.valor_centavos


def test_disponivel_e_a_conta_corrente_e_nao_soma_a_aplicacao(db):
    """A regra que dá o fluxo da §5.3. Aplicação é dinheiro da empresa, mas
    não é dinheiro disponível para aprovar pagamento: resgatar leva dias e
    tem custo. Se `disponivel` somasse a aplicação, o despacho impagável da
    semente passaria e a peça central da demonstração sumiria.

    A regra é do DOMÍNIO, não da tela: ela vive aqui, é testada aqui, e a
    interface só exibe o resultado."""
    sandbox = _semeado(db)
    saldos = notavel.saldos(db, sandbox)
    assert saldos["corrente_centavos"] == 84_320_00
    assert saldos["aplicacao_centavos"] == 210_000_00
    assert saldos["disponivel_centavos"] == saldos["corrente_centavos"]


def test_saldo_de_um_sandbox_nao_vaza_para_o_outro(db):
    a, b = _semeado(db), _semeado(db)
    db.query(LabDespacho).filter(LabDespacho.sandbox_id == a.id).delete()
    db.commit()
    assert notavel.saldos(db, a)["a_pagar_centavos"] == 0
    assert notavel.saldos(db, b)["a_pagar_centavos"] == 133_990_00


# ------------------------------------------------------- série do KPI ----

def test_serie_do_saldo_tem_um_ponto_por_dia_e_termina_no_saldo_de_hoje(db):
    sandbox = _semeado(db)
    serie = notavel.serie_saldo(db, sandbox, dias=30)
    assert len(serie) == 30
    assert serie[-1] == notavel.saldos(db, sandbox)["corrente_centavos"]
    assert all(isinstance(p, int) for p in serie)


def test_a_serie_anda_para_tras_pelos_lancamentos(db):
    """A linha do KPI não é enfeite gerado no navegador: ela sai do
    extrato. Um lançamento de ontem tem que aparecer como degrau entre o
    penúltimo e o último ponto."""
    sandbox = _sandbox(db)
    notavel.empresa_da_sandbox(db, sandbox)
    ontem = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
    db.add(LabLancamento(sandbox_id=sandbox.id, origem="seed",
                         descricao="Recebimento", valor_centavos=1_000_00,
                         criado_em=ontem))
    db.commit()
    serie = notavel.serie_saldo(db, sandbox, dias=30)
    assert serie[-2] - serie[-3] == -1_000_00 or serie[-2] == serie[-3]
    assert serie[-1] - serie[-2] == 0


def test_serie_com_um_dia_so_nao_quebra(db):
    sandbox = _semeado(db)
    assert len(notavel.serie_saldo(db, sandbox, dias=1)) == 1


# ------------------------------------------------------------ contexto ---

def test_contexto_traz_as_seis_regioes(db):
    """§3 da spec: cabeçalho, faixa de saldos, KPI, câmbio, despachos e
    lançamentos. Uma chave faltando aqui é uma região vazia na tela."""
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    for chave in ("empresa", "saldos", "kpi", "cotacoes",
                  "despachos", "movimentos"):
        assert chave in ctx, chave


def test_contexto_traz_o_cabecalho_fiscal_com_a_data_da_tabela(db):
    """§7: a tela mostra de quando a tabela é. O contexto carrega o rótulo
    pronto, para o template não precisar saber de vigência nenhuma."""
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    assert ctx["empresa"].anexo == "III"
    assert ctx["aliquota_efetiva"] == "13,59%"
    assert "2026" in ctx["vigencia_rotulo"]


def test_contexto_traz_valores_ja_formatados_em_reais(db):
    """O painel nasce renderizado pelo servidor (§4): o valor final vai no
    HTML pronto para ler. O template não formata dinheiro, porque
    formatação de moeda espalhada por template é como a mesma tela mostra
    R$ 197.00 numa linha e R$ 197,00 na de baixo."""
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    assert ctx["kpi"]["valor"].startswith("R$ ")
    assert ctx["kpi"]["centavos"] == 1_440_00
    assert ctx["saldos_exibidos"][0]["valor"].startswith("R$ ")


def test_contexto_ordena_despachos_por_vencimento(db):
    """Fila de pagamento se lê pelo que vence primeiro. Ordem por id seria
    ordem de digitação, que não quer dizer nada para quem paga contas."""
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    vencimentos = [d.vence_em for d in ctx["despachos"]]
    assert vencimentos == sorted(vencimentos)


def test_contexto_marca_o_despacho_que_nao_cabe_no_saldo(db):
    """A fila precisa poder se vestir sozinha (`:has()` no CSS) sem que o
    JavaScript classifique nada. Quem sabe se cabe é o domínio."""
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    fora = [d for d in ctx["despachos"] if d.cabe_no_saldo is False]
    assert len(fora) == 1
    assert fora[0].valor_centavos == 96_500_00


def test_contexto_so_traz_despacho_pendente_na_fila(db):
    sandbox = _semeado(db)
    db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id).first().status = "aprovado"
    db.commit()
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    assert len(ctx["despachos"]) == 4


def test_movimentos_misturam_nota_emitida_e_extrato(db):
    """§3: a região de movimentos reage a nota emitida E a extrato. As duas
    origens aparecem na mesma lista, ordenadas pelo tempo."""
    sandbox = _semeado(db)
    linhas = notavel.movimentos(db, sandbox)
    tipos = {l["tipo"] for l in linhas}
    assert "nota" in tipos
    assert len(linhas) == 8


def test_movimentos_nao_mostram_nota_cancelada(db):
    sandbox = _semeado(db)
    chaves = {l["chave"] for l in notavel.movimentos(db, sandbox, quantos=99)}
    canceladas = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "cancelada").all()
    assert canceladas
    for nota in canceladas:
        assert f"nota-{nota.id}" not in chaves


def test_movimentos_nao_gravam_nada_no_extrato(db):
    """A mistura acontece na LEITURA. Se nota emitida virasse
    `LabLancamento`, a série do KPI passaria a somar competência com caixa
    e mostraria um saldo que nunca existiu."""
    sandbox = _semeado(db)
    antes = db.query(LabLancamento).filter(
        LabLancamento.sandbox_id == sandbox.id).count()
    notavel.movimentos(db, sandbox)
    assert db.query(LabLancamento).filter(
        LabLancamento.sandbox_id == sandbox.id).count() == antes


def test_movimentos_ordenam_do_mais_novo_para_o_mais_velho(db):
    """Datas do SQLite voltam sem fuso e as recém-criadas vêm com: ordenar
    os dois juntos sem normalizar levanta TypeError, e é exatamente essa
    mistura que esta lista faz."""
    sandbox = _semeado(db)
    linhas = notavel.movimentos(db, sandbox, quantos=99)
    ordenadas = [l["quando"].replace(tzinfo=None) if l["quando"].tzinfo
                 else l["quando"] for l in linhas]
    assert ordenadas == sorted(ordenadas, reverse=True)


def test_contexto_traz_os_clientes_para_o_modal_de_emissao(db):
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    assert len(ctx["clientes"]) == 4


def test_contexto_diz_quantos_registros_o_visitante_ainda_pode_criar(db):
    """Mesmo contrato do Admita: a tela avisa antes de o teto bater, em vez
    de recusar de surpresa no décimo primeiro clique."""
    sandbox = _semeado(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    assert ctx["registros_usados"] == 0
    assert ctx["max_registros"] == 10
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py -q`
Expected: FAIL na coleta, `ModuleNotFoundError: No module named 'app.lab.auditoria'`.

- [ ] **Step 3: Escrever `app/lab/auditoria.py`**

```python
"""Trilha de auditoria das demos do Lab.

Nasceu dentro de `app/lab/admita.py`, como `_registrar`, quando só a
esteira registrava. O Notável passou a registrar aprovação e recusa de
despacho (§5.2), e duas cópias de quatro linhas entre duas demos são duas
cópias que divergem no dia em que uma delas ganhar um campo.

`LabAuditoria` já carrega `sandbox_id` e `origem`, então isolamento entre
visitantes e a regra de "seeds não contam" vêm de graça do modelo.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models import LabAuditoria, LabSandbox

# `LabAuditoria.acao` é String(200). Texto maior é cortado aqui, e não
# rejeitado: a auditoria descreve uma ação que JÁ aconteceu, e derrubar a
# ação do visitante por causa do tamanho do texto que a descreve seria o
# rabo abanando o cachorro.
MAX_ACAO = 200


def registrar(db: Session, sandbox: LabSandbox, quem: str, acao: str) -> None:
    """Acrescenta uma linha à trilha. NÃO comita: quem chama decide a
    transação, para o registro entrar junto com a mutação que ele descreve
    (ou não entrar, se ela for desfeita)."""
    db.add(LabAuditoria(
        sandbox_id=sandbox.id, origem="visitante",
        quem=quem[:100], acao=acao[:MAX_ACAO],
    ))


def ultimas(db: Session, sandbox: LabSandbox, quantas: int = 8) -> list[LabAuditoria]:
    """As linhas mais recentes primeiro. Trilha se lê de cima para baixo,
    do que acabou de acontecer para trás."""
    return (
        db.query(LabAuditoria)
        .filter(LabAuditoria.sandbox_id == sandbox.id)
        .order_by(LabAuditoria.id.desc())
        .limit(quantas)
        .all()
    )
```

- [ ] **Step 4: `admita._registrar` vira repasse**

Em `app/lab/admita.py`, troque o corpo de `_registrar` e acrescente o import:

```python
from .auditoria import registrar as _registrar_auditoria


def _registrar(db: Session, sandbox: LabSandbox, quem: str, acao: str) -> None:
    """Repasse para `app/lab/auditoria.py`, que passou a ser o dono da
    trilha quando o Notável também virou cliente dela. O nome antigo fica
    porque ele é chamado em dez lugares deste arquivo, e renomear tudo
    seria ruído numa entrega que não é sobre a esteira."""
    _registrar_auditoria(db, sandbox, quem, acao)
```

- [ ] **Step 5: Escrever a parte de leitura de `app/lab/notavel.py`**

```python
"""Domínio do painel financeiro do Notável (§3 a §5 da spec).

O QUE ESTE MODULO É

O lugar onde as regras do Notável vivem, longe da tela. A interface exibe;
ela não decide. O caso mais importante disso é a §5.3: aprovar um despacho
acima do saldo disponível é recusado, e essa recusa é uma regra de negócio
testada sozinha (`recusar_por_saldo`, Task 7), não uma validação de
formulário.

A LEITURA E A ESCRITA

`montar_contexto` é o ponto único que monta tudo que a tela desenha, e é
chamado tanto pelo GET da página inteira quanto por TODA rota de mutação:
cada mutação devolve o MESMO fragmento recém-calculado, nunca um pedaço
parcialmente atualizado. É o padrão que o Admita já usa
(`app/lab/admita.py::montar_contexto`) e que existe para as seis regiões
nunca saírem inconsistentes entre si.

O PAINEL NASCE PRONTO

O contexto entrega VALOR JÁ FORMATADO ("R$ 14.400,00") junto do inteiro em
centavos. O template escreve o texto no HTML e o JavaScript da chegada usa
o inteiro para contar do zero até ele. Sem JavaScript, o painel aparece
completo e correto, só sem a contagem (§4).

DINHEIRO

Centavos inteiros em toda a travessia. Formatação num lugar só,
`app/services/formato.py::formatar_reais`, o mesmo do resto do site.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from ..services.formato import formatar_reais
from . import fiscal
from .auditoria import registrar, ultimas
from .models import (
    LabClienteFiscal,
    LabDespacho,
    LabEmpresaFin,
    LabLancamento,
    LabNota,
    LabSandbox,
)
from .protecao import MAX_REGISTROS_POR_DEMO
from .seeds_demo import semear_empresa_fin

# Quem a demonstração finge que está com a sessão aberta, no mesmo espírito
# do `USUARIO_RH` do Admita: a trilha de auditoria precisa de um nome, e
# "sistema" não conta a história de um painel que gente usa.
USUARIO_FIN = "Usuário Teste"
USUARIO_FIN_PERFIL = "Financeiro"

DIAS_DA_SERIE = 30
QUANTOS_MOVIMENTOS = 8


def _quando_ordenavel(quando: dt.datetime) -> dt.datetime:
    """Datas do SQLite voltam sem tzinfo e datas recém-criadas em Python vêm
    com. Misturar os dois num `sort` levanta TypeError, e a linha do tempo
    do painel mistura exatamente esses dois casos."""
    return quando if quando.tzinfo else quando.replace(tzinfo=dt.timezone.utc)


def _dia(quando: dt.datetime | None) -> dt.date | None:
    """O SQLite deste repo devolve `datetime` sem tzinfo em leitura (mesma
    observação de `app/lab/sandbox.py`), então normaliza antes de comparar."""
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=dt.timezone.utc)
    return quando.date()


# ------------------------------------------------------------- empresa ---

def empresa_da_sandbox(db: Session, sandbox: LabSandbox) -> LabEmpresaFin:
    """A empresa deste visitante, criando a que faltar.

    Sandbox nascido antes deste deploy não tem empresa: quando o código
    subir já haverá sandbox de 24h no ar, semeado por uma versão que não
    conhecia `LabEmpresaFin`. Estourar para esse visitante seria puni-lo
    por ter chegado antes.
    """
    empresa = (
        db.query(LabEmpresaFin)
        .filter(LabEmpresaFin.sandbox_id == sandbox.id)
        .order_by(LabEmpresaFin.id.asc())
        .first()
    )
    if empresa is None:
        empresa = semear_empresa_fin(db, sandbox.id)
        db.commit()
    return empresa


# -------------------------------------------------------------- saldos ---

def saldos(db: Session, sandbox: LabSandbox) -> dict:
    """Os quatro números da faixa de saldos, mais o disponível.

    `disponivel_centavos` é a CONTA CORRENTE, e não a soma dela com a
    aplicação. Dinheiro aplicado é dinheiro da empresa, mas não é dinheiro
    que se usa para aprovar um pagamento hoje: resgatar leva dias e tem
    custo. É essa distinção que dá o fluxo da §5.3.

    Ele existe como chave própria, e não como um segundo nome de
    `corrente_centavos`, porque é o nome da REGRA. No dia em que a regra
    mudar (por exemplo, passar a considerar um limite de crédito), muda
    aqui, num lugar só, e a tela e a aprovação seguem juntas.
    """
    empresa = empresa_da_sandbox(db, sandbox)

    a_receber = sum(
        n.total_centavos
        for n in db.query(LabNota).filter(
            LabNota.sandbox_id == sandbox.id,
            LabNota.status == "emitida",
            LabNota.pago_em.is_(None),
        )
    )
    a_pagar = sum(
        d.valor_centavos
        for d in db.query(LabDespacho).filter(
            LabDespacho.sandbox_id == sandbox.id,
            LabDespacho.status == "pendente",
        )
    )
    return {
        "corrente_centavos": empresa.saldo_corrente_centavos,
        "aplicacao_centavos": empresa.saldo_aplicacao_centavos,
        "a_receber_centavos": a_receber,
        "a_pagar_centavos": a_pagar,
        "disponivel_centavos": empresa.saldo_corrente_centavos,
    }


def serie_saldo(db: Session, sandbox: LabSandbox, dias: int = DIAS_DA_SERIE,
                hoje: dt.date | None = None) -> list[int]:
    """Saldo em conta corrente dia a dia, do mais antigo ao de hoje.

    É a linha mínima dentro do KPI, o único gráfico que sobrou no desenho.
    Ela sai do EXTRATO, andando para trás a partir do saldo de hoje e
    desfazendo os lançamentos de cada dia. Números inventados no navegador
    seriam mais fáceis e seriam enfeite, que é justamente o que a §3 tirou
    da tela ao cortar o gráfico grande.
    """
    empresa = empresa_da_sandbox(db, sandbox)
    hoje = hoje or dt.datetime.now(dt.timezone.utc).date()
    inicio = hoje - dt.timedelta(days=dias - 1)

    por_dia: dict[dt.date, int] = {}
    for lancamento in db.query(LabLancamento).filter(
            LabLancamento.sandbox_id == sandbox.id):
        quando = _dia(lancamento.criado_em)
        if quando is not None and inicio <= quando <= hoje:
            por_dia[quando] = por_dia.get(quando, 0) + lancamento.valor_centavos

    serie = [0] * dias
    saldo = empresa.saldo_corrente_centavos
    for passo in range(dias - 1, -1, -1):
        serie[passo] = saldo
        saldo -= por_dia.get(inicio + dt.timedelta(days=passo), 0)
    return serie


# ---------------------------------------------------------- movimentos ---

def movimentos(db: Session, sandbox: LabSandbox,
               quantos: int = QUANTOS_MOVIMENTOS) -> list[dict]:
    """A região de "últimos movimentos" do painel, em ordem decrescente.

    POR QUE UMA LINHA DO TEMPO MISTURADA, E NÃO A TABELA DE LANCAMENTOS

    A §3 diz que esta região reage a nota emitida E a extrato categorizado.
    A saída fácil seria gravar um `LabLancamento` toda vez que uma nota
    sai, mas nota emitida ainda não é dinheiro em conta: é competência, não
    caixa. Gravar isso no extrato corromperia a série do KPI, que
    reconstrói o saldo andando para trás pelos lançamentos, e o painel
    passaria a mostrar um saldo que nunca existiu.

    Então o extrato continua sendo só caixa, e esta função MISTURA na
    leitura três origens: nota emitida (competência), nota paga (caixa) e
    linha de extrato (caixa). É o que um painel financeiro de verdade
    mostra, e nada aqui é gravado duas vezes.

    `chave` é estável e serve ao JavaScript para saber qual linha acabou de
    aparecer e qual acabou de mudar de estado (§4, reação com causa).
    """
    eventos: list[dict] = []

    for nota in db.query(LabNota).filter(LabNota.sandbox_id == sandbox.id):
        if nota.status == "cancelada":
            continue
        eventos.append({
            "quando": nota.criado_em,
            "tipo": "nota",
            "chave": f"nota-{nota.id}",
            "descricao": f"Nota n.º {nota.numero:06d} emitida",
            "categoria": "Receita de serviço",
            "valor": formatar_reais(nota.total_centavos),
            "valor_centavos": nota.total_centavos,
            "entrada": True,
        })
        if nota.pago_em is not None:
            eventos.append({
                "quando": nota.pago_em,
                "tipo": "pagamento",
                "chave": f"pago-{nota.id}",
                "descricao": f"Nota n.º {nota.numero:06d} recebida",
                "categoria": "Recebimento",
                "valor": formatar_reais(nota.total_centavos),
                "valor_centavos": nota.total_centavos,
                "entrada": True,
            })

    for lancamento in db.query(LabLancamento).filter(
            LabLancamento.sandbox_id == sandbox.id):
        eventos.append({
            "quando": lancamento.criado_em,
            "tipo": "extrato",
            "chave": f"lanc-{lancamento.id}",
            "descricao": lancamento.descricao,
            "categoria": lancamento.categoria.replace("_", " ").capitalize(),
            "valor": formatar_reais(lancamento.valor_centavos),
            "valor_centavos": lancamento.valor_centavos,
            "entrada": lancamento.valor_centavos >= 0,
        })

    eventos.sort(key=lambda e: (_quando_ordenavel(e["quando"]), e["chave"]),
                 reverse=True)
    return eventos[:quantos]


# ------------------------------------------------------------ contexto ---

def montar_contexto(db: Session, sandbox: LabSandbox,
                    linhas_de_cambio: list[dict]) -> dict:
    """Tudo que `_shell.html` desenha, num dicionário só.

    `linhas_de_cambio` chega de fora (`app/lab/cambio.py::cotacoes`) em vez
    de ser buscado aqui: câmbio é dado global, não é do sandbox, e mantê-lo
    como parâmetro deixa este módulo sem nenhuma dependência de rede,
    inclusive indireta.
    """
    empresa = empresa_da_sandbox(db, sandbox)
    numeros = saldos(db, sandbox)
    disponivel = numeros["disponivel_centavos"]

    despachos = (
        db.query(LabDespacho)
        .filter(LabDespacho.sandbox_id == sandbox.id,
                LabDespacho.status == "pendente")
        .order_by(LabDespacho.vence_em.asc(), LabDespacho.id.asc())
        .all()
    )
    for despacho in despachos:
        # Quem sabe se cabe é o domínio, nunca o template nem o JavaScript.
        # A fila usa esta marca para se vestir sozinha no CSS (`:has()`).
        despacho.cabe_no_saldo = despacho.valor_centavos <= disponivel  # type: ignore[attr-defined]
        despacho.valor = formatar_reais(despacho.valor_centavos)  # type: ignore[attr-defined]

    notas = (
        db.query(LabNota)
        .filter(LabNota.sandbox_id == sandbox.id)
        .order_by(LabNota.numero.desc())
        .limit(QUANTOS_MOVIMENTOS)
        .all()
    )
    for nota in notas:
        nota.valor = formatar_reais(nota.total_centavos)  # type: ignore[attr-defined]
        nota.paga = nota.pago_em is not None  # type: ignore[attr-defined]

    aliquota_bps = fiscal.aliquota_efetiva_bps(empresa.rbt12_centavos, empresa.anexo)

    # "R$ 14.400,00" e 1440000 lado a lado: o template escreve o texto e o
    # JavaScript da chegada conta do zero até o inteiro (§4).
    saldos_exibidos = [
        {"rotulo": "Conta corrente", "valor": formatar_reais(numeros["corrente_centavos"]),
         "centavos": numeros["corrente_centavos"], "chave": "corrente"},
        {"rotulo": "Aplicação", "valor": formatar_reais(numeros["aplicacao_centavos"]),
         "centavos": numeros["aplicacao_centavos"], "chave": "aplicacao"},
        {"rotulo": "A receber", "valor": formatar_reais(numeros["a_receber_centavos"]),
         "centavos": numeros["a_receber_centavos"], "chave": "a_receber"},
        {"rotulo": "A pagar", "valor": formatar_reais(numeros["a_pagar_centavos"]),
         "centavos": numeros["a_pagar_centavos"], "chave": "a_pagar"},
    ]

    return {
        "empresa": empresa,
        "saldos": numeros,
        "saldos_exibidos": saldos_exibidos,
        "kpi": {
            "rotulo": "A receber",
            "valor": formatar_reais(numeros["a_receber_centavos"]),
            "centavos": numeros["a_receber_centavos"],
            "serie": serie_saldo(db, sandbox),
        },
        "cotacoes": linhas_de_cambio,
        "despachos": despachos,
        "movimentos": movimentos(db, sandbox),
        "notas": notas,
        "clientes": (
            db.query(LabClienteFiscal)
            .filter(LabClienteFiscal.sandbox_id == sandbox.id)
            .order_by(LabClienteFiscal.nome.asc())
            .all()
        ),
        "auditoria": ultimas(db, sandbox),
        "aliquota_efetiva": fiscal.formatar_aliquota(aliquota_bps),
        "aliquota_efetiva_bps": aliquota_bps,
        "vigencia_rotulo": fiscal.VIGENCIA_ROTULO,
        "usuario": USUARIO_FIN,
        "usuario_perfil": USUARIO_FIN_PERFIL,
        "max_registros": MAX_REGISTROS_POR_DEMO,
        "registros_usados": (
            db.query(LabNota)
            .filter(LabNota.sandbox_id == sandbox.id,
                    LabNota.origem == "visitante")
            .count()
        ),
    }
```

- [ ] **Step 6: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py -q`
Expected: PASS, 26 testes.

- [ ] **Step 7: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1529 passed, zero falha. Se `tests/lab/test_admita.py` falhar, o repasse do Step 4 quebrou a trilha da esteira: conserte antes de seguir.

- [ ] **Step 8: Commit**

```bash
git add app/lab/auditoria.py app/lab/notavel.py app/lab/admita.py tests/lab/test_notavel.py
git commit -m "Notavel: trilha compartilhada, saldos e o contexto do painel"
```

---

### Task 6: Emitir, cancelar e receber nota

O primeiro dos cinco fluxos (§5.1), mais o pulso da §4. O PDF já existe (`gerar_nf_pdf`); falta a tela, a rota e a regra.

O pulso não é animação: é uma escrita de verdade. Ele quita **um recebível que está visível na tela**, o número desce, a linha muda de estado e o visitante vê o ciclo se fechar. Evento solto é enfeite; evento que fecha algo que a pessoa estava olhando é sistema.

**Files:**
- Modify: `app/lab/notavel.py` (parte de escrita)
- Modify: `app/lab/pdf.py` (`gerar_nf_pdf` passa a aceitar um emitente)
- Modify: `app/lab/rotas.py` (quatro rotas)
- Test: `tests/lab/test_notavel.py`
- Test: `tests/lab/test_pdf.py` (um caso novo)

**Interfaces:**
- Consumes: `montar_contexto`, `empresa_da_sandbox`, `saldos` (Task 5); `fiscal.memoria_de_calculo`, `fiscal.impostos_para_json` (Task 1); `_exigir_sandbox` (já existe em `app/lab/rotas.py`); `checar_limite_registros`, `validar_texto`, `MAX_CAMPO` (`app/lab/protecao.py`).
- Produces:
  - `notavel.MAX_ITENS: int` = 3
  - `notavel.emitir_nota(db, sandbox, cliente_id: int, itens: list[dict]) -> LabNota`
  - `notavel.cancelar_nota(db, sandbox, nota_id: int) -> LabNota`
  - `notavel.quitar_recebivel(db, sandbox) -> LabNota | None`
  - `notavel.pdf_da_nota(db, sandbox, nota_id: int) -> tuple[bytes, str]`
  - `pdf.gerar_nf_pdf(nota, cliente, sandbox, emitente: dict | None = None) -> bytes`
  - rotas `POST /lab/notavel/notas`, `POST /lab/notavel/notas/{id}/cancelar`, `GET /lab/notavel/notas/{id}/pdf`, `POST /lab/notavel/pulso`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/lab/test_notavel.py` (`import pytest` sobe para o topo do arquivo):

```python
# -------------------------------------------------------------- emissão --

def _item(descricao="Hora de desenvolvimento", quantidade=2, valor=15_000_00):
    return {"descricao": descricao, "quantidade": quantidade,
            "valor_unit_centavos": valor}


def test_emitir_nota_numera_em_sequencia_dentro_do_sandbox(db):
    """§5.1: numeração sequencial POR sandbox. A semente já usou 1 a 6, e a
    primeira do visitante é a 7. Numeração global vazaria o número de notas
    de outros visitantes, que é informação de outra pessoa."""
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    nota = notavel.emitir_nota(db, sandbox, cliente.id, [_item()])
    assert nota.numero == 7
    outra = notavel.emitir_nota(db, sandbox, cliente.id, [_item()])
    assert outra.numero == 8


def test_a_numeracao_de_um_sandbox_nao_conhece_a_do_outro(db):
    a, b = _semeado(db), _semeado(db)
    cliente_a = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == a.id).first()
    cliente_b = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == b.id).first()
    notavel.emitir_nota(db, a, cliente_a.id, [_item()])
    notavel.emitir_nota(db, a, cliente_a.id, [_item()])
    assert notavel.emitir_nota(db, b, cliente_b.id, [_item()]).numero == 7


def test_emitir_nota_grava_origem_visitante(db):
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    assert notavel.emitir_nota(db, sandbox, cliente.id, [_item()]).origem == "visitante"


def test_emitir_nota_calcula_o_total_pelos_itens(db):
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    nota = notavel.emitir_nota(db, sandbox, cliente.id, [
        _item(quantidade=2, valor=15_000_00),
        _item("Ambiente de homologação", quantidade=1, valor=3_000_00),
    ])
    assert nota.total_centavos == 33_000_00


def test_emitir_nota_grava_os_impostos_no_contrato_do_pdf(db):
    """`LabNota.impostos` é `{codigo: valor_centavos}`, e todo código tem
    rótulo humano em `ROTULOS_IMPOSTO`. Sem isso o PDF imprimiria
    "das_simples_nacional" cru na tabela."""
    from app.lab.pdf import ROTULOS_IMPOSTO

    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    nota = notavel.emitir_nota(db, sandbox, cliente.id,
                              [_item(quantidade=1, valor=10_000_00)])
    assert nota.impostos == {"iss_simulado_5_por_cento": 500_00,
                             "das_simples_nacional": 1_359_00}
    assert all(codigo in ROTULOS_IMPOSTO for codigo in nota.impostos)


def test_emitir_nota_faz_o_a_receber_subir(db):
    """§4: reação com causa. A ação move o que depende dela, e só isso."""
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    antes = notavel.saldos(db, sandbox)
    nota = notavel.emitir_nota(db, sandbox, cliente.id, [_item()])
    depois = notavel.saldos(db, sandbox)
    assert depois["a_receber_centavos"] == antes["a_receber_centavos"] + nota.total_centavos
    assert depois["corrente_centavos"] == antes["corrente_centavos"]


def test_emitir_nota_registra_na_trilha(db):
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    notavel.emitir_nota(db, sandbox, cliente.id, [_item()])
    assert any("emitiu" in l.acao.lower() for l in auditoria.ultimas(db, sandbox))


def test_emitir_nota_recusa_cliente_de_outro_sandbox(db):
    """Isolamento: `cliente_id` chega de fora, e um id de outro visitante
    não pode virar uma nota emitida em nome dele."""
    a, b = _semeado(db), _semeado(db)
    cliente_b = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == b.id).first()
    with pytest.raises(ValueError):
        notavel.emitir_nota(db, a, cliente_b.id, [_item()])


def test_emitir_nota_recusa_lista_vazia_e_lista_grande_demais(db):
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    with pytest.raises(ValueError):
        notavel.emitir_nota(db, sandbox, cliente.id, [])
    with pytest.raises(ValueError):
        notavel.emitir_nota(db, sandbox, cliente.id,
                            [_item()] * (notavel.MAX_ITENS + 1))


def test_emitir_nota_recusa_valor_e_quantidade_sem_sentido(db):
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    for ruim in (_item(valor=0), _item(valor=-100), _item(quantidade=0),
                 _item(quantidade=1000), _item(descricao="")):
        with pytest.raises(ValueError):
            notavel.emitir_nota(db, sandbox, cliente.id, [ruim])


def test_emitir_nota_recusa_descricao_com_caractere_de_controle(db):
    """§9.3/§9.6: nada interpretável entra, e nada interpretável chega à
    biblioteca de PDF. A validação é a mesma do resto do Lab."""
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    hostil = "Hora de dev" + chr(0)  # nulo: categoria Unicode Cc
    with pytest.raises(ValueError):
        notavel.emitir_nota(db, sandbox, cliente.id, [_item(descricao=hostil)])


def test_o_teto_de_dez_notas_por_visitante_vale(db):
    """§8: dez registros por demo, e seeds não contam. As seis notas da
    semente estão fora da conta; a décima primeira do visitante é
    recusada."""
    sandbox = _semeado(db)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.sandbox_id == sandbox.id).first()
    for _ in range(10):
        notavel.emitir_nota(db, sandbox, cliente.id, [_item()])
    with pytest.raises(ValueError):
        notavel.emitir_nota(db, sandbox, cliente.id, [_item()])


# ---------------------------------------------------------- cancelamento --

def test_cancelar_nota_derruba_o_a_receber(db):
    sandbox = _semeado(db)
    nota = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "emitida").first()
    antes = notavel.saldos(db, sandbox)["a_receber_centavos"]
    notavel.cancelar_nota(db, sandbox, nota.id)
    assert notavel.saldos(db, sandbox)["a_receber_centavos"] == \
        antes - nota.total_centavos
    assert nota.status == "cancelada"


def test_cancelar_nota_ja_paga_e_recusado(db):
    """Nota recebida não se cancela: o dinheiro entrou. Cancelar depois do
    recebimento deixaria o saldo em conta sem origem nenhuma."""
    sandbox = _semeado(db)
    paga = notavel.quitar_recebivel(db, sandbox)
    with pytest.raises(ValueError):
        notavel.cancelar_nota(db, sandbox, paga.id)


def test_cancelar_nota_de_outro_sandbox_e_recusado(db):
    a, b = _semeado(db), _semeado(db)
    nota_b = db.query(LabNota).filter(LabNota.sandbox_id == b.id).first()
    with pytest.raises(ValueError):
        notavel.cancelar_nota(db, a, nota_b.id)


def test_cancelar_duas_vezes_e_recusado(db):
    sandbox = _semeado(db)
    nota = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "emitida").first()
    notavel.cancelar_nota(db, sandbox, nota.id)
    with pytest.raises(ValueError):
        notavel.cancelar_nota(db, sandbox, nota.id)


# -------------------------------------------------------------- o pulso --

def test_o_pulso_quita_a_nota_aberta_mais_antiga(db):
    """§4: um pulso só, e amarrado a um recebível VISÍVEL. Ele escolhe a
    nota aberta mais antiga porque é a que qualquer financeiro cobraria
    primeiro, e a que está na lista que o visitante acabou de ver chegar."""
    sandbox = _semeado(db)
    abertas = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "emitida",
        LabNota.pago_em.is_(None)).order_by(LabNota.criado_em.asc()).all()
    quitada = notavel.quitar_recebivel(db, sandbox)
    assert quitada.id == abertas[0].id
    assert quitada.pago_em is not None


def test_o_pulso_move_os_dois_numeros_que_ele_deve_mover(db):
    """O ciclo se fecha na frente do visitante: sai de "a receber" e entra
    em conta corrente, pelo mesmo valor."""
    sandbox = _semeado(db)
    antes = notavel.saldos(db, sandbox)
    quitada = notavel.quitar_recebivel(db, sandbox)
    depois = notavel.saldos(db, sandbox)
    assert depois["a_receber_centavos"] == antes["a_receber_centavos"] - quitada.total_centavos
    assert depois["corrente_centavos"] == antes["corrente_centavos"] + quitada.total_centavos


def test_o_pulso_aparece_na_linha_do_tempo(db):
    sandbox = _semeado(db)
    quitada = notavel.quitar_recebivel(db, sandbox)
    chaves = {m["chave"] for m in notavel.movimentos(db, sandbox, quantos=99)}
    assert f"pago-{quitada.id}" in chaves


def test_o_pulso_nao_faz_o_despacho_impagavel_passar_a_caber(db):
    """A recusa da §5.3 é a peça central e não pode ser desarmada pelo
    próprio pulso: R$ 84.320,00 mais R$ 3.500,00 continuam abaixo dos
    R$ 96.500,00 do adiantamento de 13º."""
    sandbox = _semeado(db)
    notavel.quitar_recebivel(db, sandbox)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    assert any(d.cabe_no_saldo is False for d in ctx["despachos"])


def test_sem_recebivel_aberto_o_pulso_nao_faz_nada(db):
    """Visitante que cancelou tudo, ou que voltou depois de o pulso já ter
    acontecido. Devolver None em vez de estourar é o que deixa a rota do
    pulso ser idempotente na prática."""
    sandbox = _sandbox(db)
    notavel.empresa_da_sandbox(db, sandbox)
    assert notavel.quitar_recebivel(db, sandbox) is None


# ----------------------------------------------------------------- PDF ---

def test_pdf_da_nota_sai_com_o_emitente_da_empresa_do_painel(db):
    """O cabeçalho do painel e o emitente do PDF são a MESMA empresa. Com o
    emitente fixo antigo de `app/lab/pdf.py`, a tela diria "Marco Zero
    Software" e o documento diria "Estúdio Fictício de Demonstração"."""
    sandbox = _semeado(db)
    nota = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "emitida").first()
    dados, nome = notavel.pdf_da_nota(db, sandbox, nota.id)
    assert dados[:4] == b"%PDF"
    assert nome.endswith(".pdf")
    assert str(nota.numero) in nome


def test_pdf_de_nota_de_outro_sandbox_e_recusado(db):
    a, b = _semeado(db), _semeado(db)
    nota_b = db.query(LabNota).filter(LabNota.sandbox_id == b.id).first()
    with pytest.raises(ValueError):
        notavel.pdf_da_nota(db, a, nota_b.id)


def test_pdf_conta_no_teto_de_pdfs_do_sandbox(db):
    """§8: `MAX_PDFS` por sandbox, NF e boletim somados. `gerar_nf_pdf` só
    checa; quem persiste o contador é quem chama, e é aqui."""
    from app.lab.protecao import MAX_PDFS

    sandbox = _semeado(db)
    nota = db.query(LabNota).filter(
        LabNota.sandbox_id == sandbox.id, LabNota.status == "emitida").first()
    for _ in range(MAX_PDFS):
        notavel.pdf_da_nota(db, sandbox, nota.id)
    assert sandbox.pdfs_gerados == MAX_PDFS
    with pytest.raises(ValueError):
        notavel.pdf_da_nota(db, sandbox, nota.id)


# ----------------------------------------------------------------- rotas --

def test_painel_responde_200_e_grava_o_cookie_do_sandbox(client):
    r = client.get("/lab/notavel")
    assert r.status_code == 200
    assert "lf_lab_sandbox" in r.cookies or "set-cookie" in r.headers


def test_emitir_pela_rota_devolve_o_fragmento_recalculado(client, db_session):
    from app.lab.models import LabClienteFiscal as _C
    from app.lab.models import LabSandbox as _S

    client.get("/lab/notavel")
    sandbox = db_session.query(_S).order_by(_S.id.desc()).first()
    cliente = db_session.query(_C).filter(_C.sandbox_id == sandbox.id).first()
    r = client.post("/lab/notavel/notas", data={
        "cliente_id": str(cliente.id),
        "descricao": ["Hora de desenvolvimento"],
        "quantidade": ["2"],
        "valor": ["150,00"],
    })
    assert r.status_code == 200
    assert "nt-shell" in r.text


def test_rota_de_mutacao_sem_sandbox_devolve_400(client2):
    """Mesma regra do Admita: rota de mutação devolve FRAGMENTO, e o
    navegador não aplicaria um `Set-Cookie` escondido dentro dele. O
    primeiro GET da tela é o passo anterior obrigatório de todo
    visitante."""
    r = client2.post("/lab/notavel/despachos/1/aprovar")
    assert r.status_code == 400


def test_pdf_pela_rota_sai_como_anexo(client, db_session):
    from app.lab.models import LabNota as _N
    from app.lab.models import LabSandbox as _S

    client.get("/lab/notavel")
    sandbox = db_session.query(_S).order_by(_S.id.desc()).first()
    nota = db_session.query(_N).filter(
        _N.sandbox_id == sandbox.id, _N.status == "emitida").first()
    r = client.get(f"/lab/notavel/notas/{nota.id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
```

E acrescente a `tests/lab/test_pdf.py`:

```python
def test_gerar_nf_aceita_um_emitente_e_mantem_o_fixo_como_padrao():
    """O emitente virou parâmetro para o PDF do Notável sair em nome da
    empresa do painel. Sem argumento, continua o fixo do módulo: os testes
    e as chamadas que já existiam não mudam de comportamento."""
    padrao = gerar_nf_pdf(_nota(), _cliente(), _sandbox())
    proprio = gerar_nf_pdf(_nota(), _cliente(), _sandbox(), emitente={
        "nome": "Marco Zero Software Ltda (empresa fictícia)",
        "cnpj": "32.165.498/0001-00",
        "endereco": "Rua das Demonstrações, 100, Curitiba/PR (endereço fictício)",
    })
    assert padrao[:4] == b"%PDF" and proprio[:4] == b"%PDF"
    assert padrao != proprio
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py tests/lab/test_pdf.py -q`
Expected: FAIL com `AttributeError: module 'app.lab.notavel' has no attribute 'emitir_nota'`.

- [ ] **Step 3: `gerar_nf_pdf` passa a aceitar um emitente**

Em `app/lab/pdf.py`, troque a assinatura:

```python
def gerar_nf_pdf(nota: "LabNota", cliente: "LabClienteFiscal",
                 sandbox: "LabSandbox", emitente: dict | None = None) -> bytes:
```

Dentro, logo depois das validações de texto do cliente e antes de `pdf = _novo_pdf()`, monte o emitente:

```python
    # `emitente` é `{"nome", "cnpj", "endereco"}`, vindo da empresa do painel
    # do Notável (`app/lab/notavel.py::pdf_da_nota`). Sem ele, o fixo do
    # módulo: as chamadas anteriores a esta mudança continuam com o
    # comportamento que tinham. Passa pela MESMA `validar_texto` do resto
    # (§9.6): dado que vem de registro nunca chega cru ao fpdf2.
    dados_emitente = emitente or {
        "nome": EMITENTE_NOME, "cnpj": EMITENTE_CNPJ,
        "endereco": EMITENTE_ENDERECO,
    }
    emitente_nome = validar_texto(str(dados_emitente.get("nome", "")), MAX_CAMPO)
    emitente_cnpj = validar_texto(str(dados_emitente.get("cnpj", "")), MAX_CAMPO)
    emitente_endereco = validar_texto(str(dados_emitente.get("endereco", "")), MAX_CAMPO)
```

E troque a linha do bloco do emitente:

```python
    _bloco("Emitente", [emitente_nome, f"CNPJ (fictício): {emitente_cnpj}",
                        emitente_endereco])
```

- [ ] **Step 4: Escrever a parte de escrita de `app/lab/notavel.py`**

Acrescente ao final do módulo:

```python
# -------------------------------------------------------------- escrita --

# Três itens é o que cabe no modal sem ele virar planilha, e é o bastante
# para uma nota de serviço parecer uma nota de serviço. O corte 1 não tem
# tela de item avulso.
MAX_ITENS = 3
MAX_QUANTIDADE = 999


def _nota_da_sandbox(db: Session, sandbox: LabSandbox, nota_id: int) -> LabNota:
    nota = (
        db.query(LabNota)
        .filter(LabNota.id == nota_id, LabNota.sandbox_id == sandbox.id)
        .one_or_none()
    )
    if nota is None:
        raise ValueError("Nota não encontrada nesta demonstração.")
    return nota


def _validar_itens(itens: list[dict]) -> list[dict]:
    """Devolve os itens limpos, ou levanta `ValueError` com mensagem em
    português pronta para a tela.

    Rejeição, nunca truncamento (§8), e a mesma `validar_texto` do resto do
    Lab: o que for gravado aqui vai parar dentro de um PDF, e a §9.6 manda
    nada interpretável chegar à biblioteca.
    """
    if not itens:
        raise ValueError("A nota precisa de pelo menos um item.")
    if len(itens) > MAX_ITENS:
        raise ValueError(f"A nota aceita no máximo {MAX_ITENS} itens.")

    limpos = []
    for item in itens:
        descricao = validar_texto(str(item.get("descricao", "")), MAX_CAMPO).strip()
        if not descricao:
            raise ValueError("Todo item precisa de uma descrição.")
        try:
            quantidade = int(item.get("quantidade", 0))
            valor = int(item.get("valor_unit_centavos", 0))
        except (TypeError, ValueError) as erro:
            raise ValueError("Quantidade e valor precisam ser números.") from erro
        if not 1 <= quantidade <= MAX_QUANTIDADE:
            raise ValueError(f"A quantidade vai de 1 a {MAX_QUANTIDADE}.")
        if valor <= 0:
            raise ValueError("O valor do item precisa ser maior que zero.")
        limpos.append({"descricao": descricao, "quantidade": quantidade,
                       "valor_unit_centavos": valor})
    return limpos


def emitir_nota(db: Session, sandbox: LabSandbox, cliente_id: int,
                itens: list[dict]) -> LabNota:
    """Emite uma nota de demonstração e devolve o registro (§5.1).

    Numeração sequencial POR SANDBOX: `max(numero) + 1` dentro deste
    visitante. Numeração global vazaria quantas notas os OUTROS visitantes
    emitiram, que é informação de outra pessoa.

    O total é o subtotal dos itens. O ISS é tratado como retenção, já
    embutida no preço do serviço (prática comum de nota de serviço no
    Brasil) e não somado por cima; é a mesma convenção que a semente já
    usa. Os impostos ficam informativos, explicados na tela pela memória de
    cálculo de `app/lab/fiscal.py`.
    """
    checar_limite_registros(db, sandbox, "fin")

    cliente = (
        db.query(LabClienteFiscal)
        .filter(LabClienteFiscal.id == cliente_id,
                LabClienteFiscal.sandbox_id == sandbox.id)
        .one_or_none()
    )
    if cliente is None:
        raise ValueError("Cliente não encontrado nesta demonstração.")

    limpos = _validar_itens(itens)
    subtotal = sum(i["quantidade"] * i["valor_unit_centavos"] for i in limpos)

    empresa = empresa_da_sandbox(db, sandbox)
    memoria = fiscal.memoria_de_calculo(subtotal, empresa.rbt12_centavos,
                                        empresa.anexo)

    ultimo = (
        db.query(LabNota.numero)
        .filter(LabNota.sandbox_id == sandbox.id)
        .order_by(LabNota.numero.desc())
        .first()
    )
    nota = LabNota(
        sandbox_id=sandbox.id, cliente_id=cliente.id, origem="visitante",
        numero=(ultimo[0] if ultimo else 0) + 1,
        itens=limpos, impostos=fiscal.impostos_para_json(memoria),
        total_centavos=subtotal, status="emitida",
    )
    db.add(nota)
    registrar(db, sandbox, USUARIO_FIN,
              f"emitiu a nota n.º {nota.numero:06d} para {cliente.nome}")
    db.commit()
    db.refresh(nota)
    return nota


def cancelar_nota(db: Session, sandbox: LabSandbox, nota_id: int) -> LabNota:
    """Cancela uma nota emitida: o "a receber" desce e a linha muda de
    estado no painel (§5.1).

    Nota JÁ RECEBIDA não se cancela. O dinheiro entrou em conta, e cancelar
    depois disso deixaria o saldo corrente sem origem: o painel mostraria
    um valor que nenhum documento explica.
    """
    nota = _nota_da_sandbox(db, sandbox, nota_id)
    if nota.status != "emitida":
        raise ValueError("Esta nota já está cancelada.")
    if nota.pago_em is not None:
        raise ValueError(
            "Esta nota já foi recebida e não pode ser cancelada. "
            "O valor já entrou na conta corrente.")
    nota.status = "cancelada"
    registrar(db, sandbox, USUARIO_FIN, f"cancelou a nota n.º {nota.numero:06d}")
    db.commit()
    return nota


def quitar_recebivel(db: Session, sandbox: LabSandbox) -> LabNota | None:
    """O pulso da §4: um pagamento compensa, e ele quita um recebível que
    está VISÍVEL na tela.

    Escolhe a nota aberta MAIS ANTIGA: é a que qualquer financeiro cobraria
    primeiro. Devolve None quando não há recebível aberto, para a rota
    poder ser chamada duas vezes sem estourar (o JavaScript dispara o pulso
    na chegada, e uma recarga rápida chamaria de novo).

    Isto é uma escrita de verdade, não uma animação: o número desce porque
    o dado mudou. Evento solto é enfeite; evento que fecha algo que a
    pessoa estava olhando é sistema.
    """
    nota = (
        db.query(LabNota)
        .filter(LabNota.sandbox_id == sandbox.id,
                LabNota.status == "emitida",
                LabNota.pago_em.is_(None))
        .order_by(LabNota.criado_em.asc(), LabNota.numero.asc())
        .first()
    )
    if nota is None:
        return None

    empresa = empresa_da_sandbox(db, sandbox)
    nota.pago_em = dt.datetime.now(dt.timezone.utc)
    empresa.saldo_corrente_centavos += nota.total_centavos
    registrar(db, sandbox, "Compensação bancária",
              f"recebeu a nota n.º {nota.numero:06d}")
    db.commit()
    db.refresh(nota)
    return nota


def pdf_da_nota(db: Session, sandbox: LabSandbox, nota_id: int) -> tuple[bytes, str]:
    """Devolve `(bytes, nome_do_arquivo)` do PDF da nota.

    O emitente é a empresa DO PAINEL, não o fixo de `app/lab/pdf.py`: o
    cabeçalho da tela e o documento precisam dizer o mesmo nome.

    `gerar_nf_pdf` checa o teto de PDFs do sandbox mas não persiste o
    contador (ela não recebe `db`); persistir é responsabilidade de quem
    chama, e é aqui.
    """
    from .pdf import gerar_nf_pdf

    nota = _nota_da_sandbox(db, sandbox, nota_id)
    cliente = db.query(LabClienteFiscal).filter(
        LabClienteFiscal.id == nota.cliente_id).one()
    empresa = empresa_da_sandbox(db, sandbox)

    dados = gerar_nf_pdf(nota, cliente, sandbox, emitente={
        "nome": empresa.nome,
        "cnpj": empresa.cnpj,
        "endereco": "Rua das Demonstrações, 100, Curitiba/PR (endereço fictício)",
    })
    sandbox.pdfs_gerados += 1
    db.commit()
    return dados, f"nota-{nota.numero:06d}-demonstracao.pdf"
```

E ajuste os imports do módulo:

```python
from .protecao import (
    MAX_CAMPO,
    MAX_REGISTROS_POR_DEMO,
    checar_limite_registros,
    validar_texto,
)
```

- [ ] **Step 5: As quatro rotas**

Em `app/lab/rotas.py`, troque a rota `notavel` placeholder por estas. `_exigir_sandbox` e o truque do cookie já existem no arquivo, com o comentário que explica o porquê.

```python
def _renderizar_shell_notavel(db: Session, sandbox: LabSandbox) -> str:
    """Renderiza `lab/notavel/_shell.html`, o fragmento que TODA rota de
    mutação do Notável devolve (e que `painel.html` também inclui no
    primeiro carregamento): as seis regiões recalculadas do banco depois da
    mutação que acabou de acontecer. Mesmo padrão de
    `_renderizar_shell_admita` acima."""
    from ..main import templates

    ctx = _notavel_dados.montar_contexto(db, sandbox, _cambio.cotacoes(db))
    return templates.get_template("lab/notavel/_shell.html").render(**ctx)


async def _atualizar_cambio_em_segundo_plano() -> None:
    """Sessão PRÓPRIA, e não a da requisição: a sessão injetada por
    `Depends(get_db)` já foi fechada quando a tarefa de fundo roda, e usá-la
    aqui levantaria erro no log de um painel que o visitante recebeu
    inteiro e correto."""
    from ..database import SessionLocal

    with SessionLocal() as db:
        await _cambio.atualizar(db)


@router.get("/notavel")
async def notavel(request: Request, tarefas: BackgroundTasks,
                  db: Session = Depends(get_db)) -> HTMLResponse:
    """Painel financeiro (§3 da spec). Mesmo cuidado com o cookie da rota
    do Admita: o `Set-Cookie` é gravado numa `Response` descartável e
    copiado à mão, porque um `Response` injetado por `Depends` não é
    mesclado a um `TemplateResponse` já pronto.

    A atualização do câmbio entra em `BackgroundTasks`: ela roda DEPOIS de
    a resposta sair, então um Banco Central lento nunca atrasa a chegada do
    painel, que a §14 exige em menos de um segundo."""
    from ..main import templates

    resposta_cookie = Response()
    sandbox = obter_ou_criar_sandbox(request, resposta_cookie, db, demo="fin")
    ctx = _notavel_dados.montar_contexto(db, sandbox, _cambio.cotacoes(db))
    if _cambio.precisa_atualizar(db):
        tarefas.add_task(_atualizar_cambio_em_segundo_plano)
    resposta = templates.TemplateResponse(
        request, "lab/notavel/painel.html", {"demo": "notavel", **ctx}
    )
    cookie = resposta_cookie.headers.get("set-cookie")
    if cookie:
        resposta.headers["set-cookie"] = cookie
    return resposta


def _centavos_do_texto(texto: str) -> int:
    """"1.500,00", "1500.00" e "1500" viram 150000. Formato brasileiro e
    formato de máquina, porque o mesmo campo recebe digitação de gente e
    valor preenchido por script no teste.

    Texto que não vira número devolve 0, e `_validar_itens` recusa com uma
    mensagem em português. Levantar aqui daria um 500 em vez de um aviso."""
    limpo = "".join(c for c in str(texto) if c.isdigit() or c in ",.")
    if not limpo:
        return 0
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        return int(round(float(limpo) * 100))
    except ValueError:
        return 0


@router.post("/notavel/notas")
async def notavel_emitir_nota(
    cliente_id: int = Form(...),
    descricao: list[str] = Form(default=[]),
    quantidade: list[str] = Form(default=[]),
    valor: list[str] = Form(default=[]),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Emissão em três passos (§5.1). Os três campos chegam como listas
    paralelas, uma posição por linha de item do modal.

    `valor` vem como o visitante digitou ("1.500,00") e vira centavos aqui,
    na borda: o domínio só conhece inteiro."""
    itens = [
        {
            "descricao": texto,
            "quantidade": quantidade[i] if i < len(quantidade) else 0,
            "valor_unit_centavos": _centavos_do_texto(
                valor[i] if i < len(valor) else ""),
        }
        for i, texto in enumerate(descricao)
    ]
    try:
        _notavel_dados.emitir_nota(db, sandbox, cliente_id, itens)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_notavel(db, sandbox))


@router.post("/notavel/notas/{nota_id}/cancelar")
async def notavel_cancelar_nota(
    nota_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        _notavel_dados.cancelar_nota(db, sandbox, nota_id)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_notavel(db, sandbox))


@router.get("/notavel/notas/{nota_id}/pdf")
async def notavel_pdf_da_nota(
    nota_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> Response:
    try:
        dados, nome = _notavel_dados.pdf_da_nota(db, sandbox, nota_id)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return Response(
        content=dados, media_type="application/pdf",
        headers={"content-disposition": f'attachment; filename="{nome}"'},
    )


@router.post("/notavel/pulso")
async def notavel_pulso(
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """O pulso da chegada (§4). Disparado pelo `notavel.js` alguns segundos
    depois de a tela assentar, e idempotente na prática: sem recebível
    aberto, `quitar_recebivel` devolve None e o fragmento volta igual."""
    _notavel_dados.quitar_recebivel(db, sandbox)
    return HTMLResponse(_renderizar_shell_notavel(db, sandbox))
```

Ajuste os imports do topo de `app/lab/rotas.py`:

```python
from fastapi import (
    APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, Response,
)

from . import cambio as _cambio
from . import notavel as _notavel_dados
```

- [ ] **Step 6: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py tests/lab/test_pdf.py -q`
Expected: os de domínio e de PDF passam. Os quatro de rota ainda falham, porque `lab/notavel/painel.html` e `_shell.html` só nascem na Task 8.

**Marque os quatro testes de rota com `@pytest.mark.xfail(reason="templates chegam na Task 8", strict=True)` e tire a marca na Task 8.** `strict=True` é o que importa: assim que os templates existirem, um xfail que passa vira falha, e ninguém esquece de tirar a marca.

- [ ] **Step 7: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1560 passed, 4 xfailed, zero falha.

- [ ] **Step 8: Commit**

```bash
git add app/lab/notavel.py app/lab/pdf.py app/lab/rotas.py tests/lab/test_notavel.py tests/lab/test_pdf.py
git commit -m "Notavel: emitir, cancelar e receber nota, com PDF em nome da empresa do painel"
```

---

### Task 7: Despachos e o lugar onde o sistema recusa

A §5.3 é a peça central da demonstração. O visitante clica achando que vai passar, e a recusa vem com o número: saldo disponível, valor do despacho, diferença. Sem ela o painel é bonito e mudo.

A regra é do domínio, não da tela: vive no serviço, é testada sozinha, e a interface só a exibe.

**Files:**
- Modify: `app/lab/notavel.py`
- Modify: `app/lab/rotas.py` (duas rotas)
- Test: `tests/lab/test_notavel.py`

**Interfaces:**
- Consumes: `saldos`, `empresa_da_sandbox`, `registrar` (Task 5).
- Produces:
  - `notavel.SaldoInsuficiente(ValueError)` com `disponivel_centavos`, `valor_centavos`, `faltam_centavos` e `como_dict() -> dict`
  - `notavel.aprovar_despacho(db, sandbox, despacho_id) -> LabDespacho`
  - `notavel.recusar_despacho(db, sandbox, despacho_id, motivo: str) -> LabDespacho`
  - rotas `POST /lab/notavel/despachos/{id}/aprovar` e `POST /lab/notavel/despachos/{id}/recusar`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/lab/test_notavel.py`:

```python
# ----------------------------------------------------------- despachos ---

def _despacho_que_cabe(db, sandbox):
    disponivel = notavel.saldos(db, sandbox)["disponivel_centavos"]
    return db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id,
        LabDespacho.status == "pendente",
        LabDespacho.valor_centavos <= disponivel).first()


def _despacho_que_nao_cabe(db, sandbox):
    disponivel = notavel.saldos(db, sandbox)["disponivel_centavos"]
    return db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id,
        LabDespacho.status == "pendente",
        LabDespacho.valor_centavos > disponivel).first()


def test_aprovar_despacho_baixa_o_saldo_e_tira_da_fila(db):
    sandbox = _semeado(db)
    despacho = _despacho_que_cabe(db, sandbox)
    antes = notavel.saldos(db, sandbox)
    notavel.aprovar_despacho(db, sandbox, despacho.id)
    depois = notavel.saldos(db, sandbox)
    assert despacho.status == "aprovado"
    assert despacho.decidido_em is not None
    assert depois["corrente_centavos"] == antes["corrente_centavos"] - despacho.valor_centavos
    assert depois["a_pagar_centavos"] == antes["a_pagar_centavos"] - despacho.valor_centavos


def test_aprovar_despacho_registra_na_trilha_e_no_extrato(db):
    """A aprovação move dinheiro de verdade, então ela deixa rastro nos
    dois lugares onde dinheiro deixa rastro: a trilha de auditoria e o
    extrato que alimenta a linha do KPI."""
    sandbox = _semeado(db)
    despacho = _despacho_que_cabe(db, sandbox)
    antes = db.query(LabLancamento).filter(
        LabLancamento.sandbox_id == sandbox.id).count()
    notavel.aprovar_despacho(db, sandbox, despacho.id)
    assert any("aprovou" in l.acao.lower() for l in auditoria.ultimas(db, sandbox))
    assert db.query(LabLancamento).filter(
        LabLancamento.sandbox_id == sandbox.id).count() == antes + 1


def test_aprovar_acima_do_saldo_e_recusado_com_os_tres_numeros(db):
    """§5.3, a peça central. A recusa não é um "não": ela diz quanto tem,
    quanto foi pedido e quanto falta. É o que separa sistema de maquete, e
    o visitante técnico sente em três segundos."""
    sandbox = _semeado(db)
    despacho = _despacho_que_nao_cabe(db, sandbox)
    disponivel = notavel.saldos(db, sandbox)["disponivel_centavos"]

    with pytest.raises(notavel.SaldoInsuficiente) as capturado:
        notavel.aprovar_despacho(db, sandbox, despacho.id)

    erro = capturado.value
    assert erro.disponivel_centavos == disponivel
    assert erro.valor_centavos == despacho.valor_centavos
    assert erro.faltam_centavos == despacho.valor_centavos - disponivel
    assert erro.faltam_centavos == 12_180_00


def test_a_recusa_por_saldo_leva_os_valores_formatados_para_a_tela(db):
    """A tela mostra dinheiro, não centavos. O domínio entrega os dois:
    inteiro para quem calcula, texto para quem lê."""
    sandbox = _semeado(db)
    despacho = _despacho_que_nao_cabe(db, sandbox)
    with pytest.raises(notavel.SaldoInsuficiente) as capturado:
        notavel.aprovar_despacho(db, sandbox, despacho.id)
    dados = capturado.value.como_dict()
    assert dados["faltam"] == "R$ 12.180,00"
    assert dados["disponivel"] == "R$ 84.320,00"
    assert dados["valor"] == "R$ 96.500,00"
    assert dados["faltam_centavos"] == 12_180_00


def test_a_recusa_por_saldo_nao_muda_nada(db):
    """Nada aconteceu com o despacho, então nada é gravado: ele continua
    pendente, o saldo continua o mesmo, e a trilha não registra uma
    aprovação que não houve."""
    sandbox = _semeado(db)
    despacho = _despacho_que_nao_cabe(db, sandbox)
    antes = notavel.saldos(db, sandbox)
    linhas_antes = len(auditoria.ultimas(db, sandbox, quantas=99))
    with pytest.raises(notavel.SaldoInsuficiente):
        notavel.aprovar_despacho(db, sandbox, despacho.id)
    db.refresh(despacho)
    assert despacho.status == "pendente"
    assert notavel.saldos(db, sandbox) == antes
    assert len(auditoria.ultimas(db, sandbox, quantas=99)) == linhas_antes


def test_o_saldo_encolhe_e_um_despacho_que_cabia_deixa_de_caber(db):
    """A regra não é sobre um valor mágico: é sobre o saldo DO MOMENTO.
    Aprovar tudo que cabe faz o próximo deixar de caber, e é isso que faz o
    visitante entender que o sistema está CONTANDO, não conferindo uma
    lista."""
    sandbox = _semeado(db)
    while True:
        despacho = _despacho_que_cabe(db, sandbox)
        if despacho is None:
            break
        notavel.aprovar_despacho(db, sandbox, despacho.id)
    restantes = db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == sandbox.id,
        LabDespacho.status == "pendente").all()
    assert restantes
    for despacho in restantes:
        with pytest.raises(notavel.SaldoInsuficiente):
            notavel.aprovar_despacho(db, sandbox, despacho.id)


def test_saldo_insuficiente_e_um_valueerror():
    """Quem já trata `ValueError` nas rotas do Lab continua tratando. A
    subclasse existe para quem QUER os três números, não para obrigar todo
    mundo a conhecê-la."""
    assert issubclass(notavel.SaldoInsuficiente, ValueError)


def test_recusar_despacho_guarda_o_motivo_e_nao_mexe_no_saldo(db):
    sandbox = _semeado(db)
    despacho = _despacho_que_cabe(db, sandbox)
    antes = notavel.saldos(db, sandbox)["corrente_centavos"]
    notavel.recusar_despacho(db, sandbox, despacho.id, "Fora do orçamento do mês")
    assert despacho.status == "recusado"
    assert despacho.motivo == "Fora do orçamento do mês"
    assert notavel.saldos(db, sandbox)["corrente_centavos"] == antes


def test_recusar_sem_motivo_e_recusado(db):
    """Recusa sem motivo é o que faz uma fila de aprovação virar caixa
    preta: quem recebe a recusa não sabe o que corrigir."""
    sandbox = _semeado(db)
    despacho = _despacho_que_cabe(db, sandbox)
    with pytest.raises(ValueError):
        notavel.recusar_despacho(db, sandbox, despacho.id, "   ")


def test_decidir_duas_vezes_e_recusado(db):
    sandbox = _semeado(db)
    despacho = _despacho_que_cabe(db, sandbox)
    notavel.aprovar_despacho(db, sandbox, despacho.id)
    with pytest.raises(ValueError):
        notavel.aprovar_despacho(db, sandbox, despacho.id)
    with pytest.raises(ValueError):
        notavel.recusar_despacho(db, sandbox, despacho.id, "tarde demais")


def test_despacho_de_outro_sandbox_e_recusado(db):
    a, b = _semeado(db), _semeado(db)
    despacho_b = db.query(LabDespacho).filter(
        LabDespacho.sandbox_id == b.id).first()
    with pytest.raises(ValueError):
        notavel.aprovar_despacho(db, a, despacho_b.id)


def test_rota_de_aprovar_acima_do_saldo_devolve_409_com_os_numeros(client, db_session):
    """A tela desenha a recusa a partir do corpo da resposta. Os três
    valores viajam no `detail`, não só uma frase: quem monta a tela não
    pode ter que extrair número de texto."""
    from app.lab.models import LabDespacho as _D
    from app.lab.models import LabSandbox as _S

    client.get("/lab/notavel")
    sandbox = db_session.query(_S).order_by(_S.id.desc()).first()
    impagavel = db_session.query(_D).filter(
        _D.sandbox_id == sandbox.id).order_by(_D.valor_centavos.desc()).first()

    r = client.post(f"/lab/notavel/despachos/{impagavel.id}/aprovar")
    assert r.status_code == 409
    corpo = r.json()["detail"]
    assert corpo["motivo"] == "saldo_insuficiente"
    assert corpo["faltam"] == "R$ 12.180,00"
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py -q -k despacho`
Expected: FAIL, `AttributeError: module 'app.lab.notavel' has no attribute 'SaldoInsuficiente'`.

- [ ] **Step 3: A regra, em `app/lab/notavel.py`**

```python
# ------------------------------------------------------- §5.3 a recusa ---

class SaldoInsuficiente(ValueError):
    """Aprovação recusada porque o despacho passa do saldo disponível.

    Subclasse de `ValueError` de propósito: as rotas do Lab já traduzem
    `ValueError` em 409, então quem não se importa com os detalhes continua
    funcionando sem saber que esta classe existe. Quem se importa (a tela
    da recusa) pega os três números.

    Os três números são o ponto. "Saldo insuficiente" sozinho é a resposta
    de uma maquete; "tem R$ 84.320,00, o despacho é R$ 96.500,00, faltam
    R$ 12.180,00" é a resposta de um sistema.
    """

    def __init__(self, disponivel_centavos: int, valor_centavos: int) -> None:
        self.disponivel_centavos = disponivel_centavos
        self.valor_centavos = valor_centavos
        self.faltam_centavos = valor_centavos - disponivel_centavos
        super().__init__(
            f"Saldo insuficiente: faltam {formatar_reais(self.faltam_centavos)} "
            "para aprovar este despacho."
        )

    def como_dict(self) -> dict:
        """O que a rota devolve no `detail` do 409 e a tela desenha. Texto
        e inteiro lado a lado: a pessoa lê o texto, o JavaScript anima o
        inteiro."""
        return {
            "motivo": "saldo_insuficiente",
            "disponivel": formatar_reais(self.disponivel_centavos),
            "disponivel_centavos": self.disponivel_centavos,
            "valor": formatar_reais(self.valor_centavos),
            "valor_centavos": self.valor_centavos,
            "faltam": formatar_reais(self.faltam_centavos),
            "faltam_centavos": self.faltam_centavos,
            "mensagem": str(self),
        }


def _despacho_da_sandbox(db: Session, sandbox: LabSandbox,
                         despacho_id: int) -> LabDespacho:
    despacho = (
        db.query(LabDespacho)
        .filter(LabDespacho.id == despacho_id,
                LabDespacho.sandbox_id == sandbox.id)
        .one_or_none()
    )
    if despacho is None:
        raise ValueError("Despacho não encontrado nesta demonstração.")
    if despacho.status != "pendente":
        raise ValueError("Este despacho já foi decidido.")
    return despacho


def aprovar_despacho(db: Session, sandbox: LabSandbox,
                     despacho_id: int) -> LabDespacho:
    """Aprova um pagamento da fila: o saldo em conta corrente baixa e o
    item sai da fila (§5.2).

    ACIMA DO SALDO DISPONÍVEL, RECUSA (§5.3). A conta é feita com o saldo
    DO MOMENTO, não com um número fixo: aprovar os que cabem faz o próximo
    deixar de caber, e é isso que mostra ao visitante que o sistema está
    contando, e não conferindo uma lista.

    Recusa não grava nada. Nada aconteceu com o despacho: ele continua
    pendente, o saldo continua o mesmo, e a trilha não registra uma
    aprovação que não houve.
    """
    despacho = _despacho_da_sandbox(db, sandbox, despacho_id)
    disponivel = saldos(db, sandbox)["disponivel_centavos"]
    if despacho.valor_centavos > disponivel:
        raise SaldoInsuficiente(disponivel, despacho.valor_centavos)

    empresa = empresa_da_sandbox(db, sandbox)
    empresa.saldo_corrente_centavos -= despacho.valor_centavos
    despacho.status = "aprovado"
    despacho.decidido_em = dt.datetime.now(dt.timezone.utc)
    db.add(LabLancamento(
        sandbox_id=sandbox.id, origem="visitante",
        descricao=f"Pagamento a {despacho.fornecedor}",
        valor_centavos=-despacho.valor_centavos,
        categoria="despesa_operacional",
    ))
    registrar(db, sandbox, USUARIO_FIN,
              f"aprovou o despacho de {formatar_reais(despacho.valor_centavos)} "
              f"para {despacho.fornecedor}")
    db.commit()
    return despacho


def recusar_despacho(db: Session, sandbox: LabSandbox, despacho_id: int,
                     motivo: str) -> LabDespacho:
    """Recusa um pagamento COM MOTIVO (§5.2).

    Motivo é obrigatório: fila de aprovação que recusa sem dizer por quê é
    caixa preta, e quem recebe a recusa não sabe o que corrigir.
    """
    despacho = _despacho_da_sandbox(db, sandbox, despacho_id)
    motivo = validar_texto(str(motivo), MAX_CAMPO).strip()
    if not motivo:
        raise ValueError("Diga o motivo da recusa para quem pediu o pagamento.")

    despacho.status = "recusado"
    despacho.motivo = motivo
    despacho.decidido_em = dt.datetime.now(dt.timezone.utc)
    registrar(db, sandbox, USUARIO_FIN,
              f"recusou o despacho para {despacho.fornecedor}: {motivo}")
    db.commit()
    return despacho
```

- [ ] **Step 4: As duas rotas**

Em `app/lab/rotas.py`:

```python
@router.post("/notavel/despachos/{despacho_id}/aprovar")
async def notavel_aprovar_despacho(
    despacho_id: int,
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """§5.3: a recusa por saldo devolve 409 com os TRÊS números no
    `detail`, não só uma frase. A tela desenha a recusa a partir desse
    corpo, e quem monta a tela não pode ter que extrair número de texto."""
    try:
        _notavel_dados.aprovar_despacho(db, sandbox, despacho_id)
    except _notavel_dados.SaldoInsuficiente as erro:
        raise HTTPException(status_code=409, detail=erro.como_dict()) from erro
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_notavel(db, sandbox))


@router.post("/notavel/despachos/{despacho_id}/recusar")
async def notavel_recusar_despacho(
    despacho_id: int,
    motivo: str = Form(...),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        _notavel_dados.recusar_despacho(db, sandbox, despacho_id, motivo)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(_renderizar_shell_notavel(db, sandbox))
```

- [ ] **Step 5: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py -q`
Expected: os de domínio passam. `test_rota_de_aprovar_acima_do_saldo_devolve_409_com_os_numeros` depende do `GET /lab/notavel` renderizar, então marque também com `@pytest.mark.xfail(reason="templates chegam na Task 8", strict=True)`.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1572 passed, 5 xfailed, zero falha.

- [ ] **Step 7: Commit**

```bash
git add app/lab/notavel.py app/lab/rotas.py tests/lab/test_notavel.py
git commit -m "Notavel: fila de despachos e a recusa por saldo com os tres numeros"
```

---

### Task 8: A tela heroína, as seis regiões

Uma tela só, sem rolagem obrigatória no desktop. É aqui que o Notável passa a parecer outro sistema, e não o Admita pintado de outra cor: a metáfora é painel de instrumentos, a unidade é o número que muda, e o topo ganha a barra de comando escura.

Os cinco recursos modernos de CSS entram nesta task, todos como melhoria progressiva. O piso é o vocabulário de keyframes que o Admita já provou.

**Files:**
- Create: `app/templates/lab/notavel/painel.html`
- Create: `app/templates/lab/notavel/_shell.html`
- Create: `tests/lab/test_notavel_tela.py`
- Modify: `app/static/lab/notavel.css` (camada de layout abaixo dos tokens que já existem)
- Modify: `app/lab/notavel.py` (`pontos_da_linha`)
- Modify: `tests/lab/test_notavel.py` (tira os cinco `xfail` das Tasks 6 e 7)

**Interfaces:**
- Consumes: todo o contexto de `montar_contexto` (Task 5); o sprite `/static/lab/icones/notavel.svg`; as marcas `/static/lab/img/marca-notavel.svg` e `simbolo-notavel.svg`; os tokens que já existem em `notavel.css`.
- Produces:
  - `notavel.pontos_da_linha(serie: list[int], largura: int = 220, altura: int = 48) -> str`
  - `kpi["linha"]` no contexto, o atributo `points` pronto do `<polyline>`
  - marcadores de DOM que a Task 9 consome: `#nt-app`, `#nt-shell`, `[data-regiao]`, `[data-valor]`, `[data-despacho]`, `[data-acao]`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/lab/test_notavel_tela.py`:

```python
"""Tela do Notável: as seis regiões, o CSS e o JavaScript do painel.

Renderiza o template pelo ambiente Jinja do app, com um contexto de
verdade montado a partir de um sandbox semeado. Testar a tela pelo HTML
renderizado, e não por captura de imagem, é a mesma escolha já feita em
`tests/lab/test_base_demo.py`.
"""
import re
from pathlib import Path

from app.lab import cambio, notavel
from app.lab.models import LabSandbox
from app.lab.seeds_demo import semear_cenario

RAIZ_LAB = Path(__file__).resolve().parents[2] / "app" / "static" / "lab"
CSS = RAIZ_LAB / "notavel.css"


def _sandbox(db):
    import datetime as dt

    sandbox = LabSandbox(
        token=f"tela{db.query(LabSandbox).count()}", demo_origem="fin",
        expira_em=dt.datetime.now(dt.UTC) + dt.timedelta(hours=24),
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    semear_cenario(db, sandbox)
    return sandbox


def _html(db, template="lab/notavel/_shell.html"):
    from app.main import templates

    sandbox = _sandbox(db)
    ctx = notavel.montar_contexto(db, sandbox, cambio.cotacoes(db))
    return templates.get_template(template).render(demo="notavel", **ctx)


# ------------------------------------------------------- as seis regiões --

def test_as_seis_regioes_estao_na_tela(db):
    """§3: cabeçalho, faixa de saldos, KPI, câmbio, despachos e
    movimentos. `data-regiao` é o contrato entre o template e o
    `notavel.js`, que escalona a entrada de cada uma na chegada."""
    html = _html(db)
    for regiao in ("comando", "saldos", "kpi", "cambio", "despachos", "movimentos"):
        assert f'data-regiao="{regiao}"' in html, regiao


def test_o_cabecalho_traz_empresa_cnpj_cnae_e_regime(db):
    html = _html(db)
    assert "Marco Zero Software" in html
    assert "6201-5/01" in html
    assert "Simples Nacional" in html
    assert "Anexo III" in html


def test_o_cabecalho_diz_de_quando_e_a_tabela_de_aliquota(db):
    """§7: alíquota do Simples muda por lei todo ano. Com a data na tela,
    o número velho vira "tabela de 2026" em vez de "erro"."""
    html = _html(db)
    assert "13,59%" in html
    assert "2026" in html


def test_nao_existe_grafico_de_entradas_contra_saidas(db):
    """§3: ele foi cortado no desenho. Bonito na chegada e mudo depois, e
    ocupava a área nobre sem dizer nada que os números ao lado já não
    digam. O espaço foi para a fila de despachos, que é onde o visitante
    age."""
    html = _html(db)
    assert html.count("<svg") >= 1  # ícones e a linha do KPI existem
    assert "nt-grafico-barras" not in html
    assert "entradas contra saídas" not in html.lower()


def test_o_kpi_tem_a_linha_dos_trinta_dias_desenhada_no_servidor(db):
    """A linha mínima que sobrou (§3), e ela nasce pronta: sem JavaScript o
    painel aparece completo, só sem a animação de desenho."""
    html = _html(db)
    assert "<polyline" in html
    pontos = re.search(r'points="([^"]+)"', html).group(1)
    assert len(pontos.split()) == 30


def test_o_cambio_mostra_as_tres_moedas_com_a_data_da_cotacao(db):
    html = _html(db)
    for moeda in ("USD", "EUR", "GBP"):
        assert moeda in html
    assert "24/08/2026" in html


# --------------------------------------------- valores prontos e tabulares --

def test_todo_numero_animavel_carrega_o_valor_final_no_html(db):
    """§4: o painel nasce renderizado pelo servidor e a chegada conta do
    zero ATÉ ele. O contrário deixa a tela piscar vazia enquanto o
    JavaScript busca dados, e em trinta segundos de julgamento essa piscada
    é metade da primeira impressão.

    `data-valor` é o inteiro em centavos que o JavaScript usa para contar;
    o texto do elemento já é o valor final formatado."""
    html = _html(db)
    assert 'data-valor="1440000"' in html      # A receber
    assert 'data-valor="8432000"' in html      # Conta corrente
    assert "R$ 14.400,00" in html
    assert "R$ 84.320,00" in html


def test_os_valores_usam_numero_tabular(db):
    """§3: números tabulares em toda parte. Sem isso, os dígitos dançam de
    largura entre um valor e outro e a coluna deixa de alinhar, que é
    exatamente o oposto do que software financeiro precisa parecer."""
    css = CSS.read_text(encoding="utf-8")
    assert "font-variant-numeric: tabular-nums" in css
    assert "--marca-fonte-mono" in css


def test_o_shell_nunca_rola_a_pagina(db):
    """§13b, lei da tela cheia: excedente rola DENTRO de um box com
    `.rola-interno`, nunca como barra de rolagem de página."""
    html = _html(db)
    assert "rola-interno" in html
    css = CSS.read_text(encoding="utf-8")
    assert "100dvh" in css or "min-height: 0" in css


# ----------------------------------------------- os cinco recursos novos --

def test_os_tres_recursos_que_precisam_de_guarda_estao_atras_de_supports():
    """§4.1, o piso inegociável: tudo é melhoria progressiva. `subgrid`,
    `@container` e `:has()` mudam o layout de verdade, então cada um entra
    atrás de `@supports` com uma alternativa que já funciona embaixo.

    View Transitions e `@starting-style` não aparecem aqui porque
    degradam sozinhos: propriedade e at-rule desconhecidas são ignoradas
    pelo navegador, e o JavaScript testa `document.startViewTransition`
    antes de usar."""
    css = CSS.read_text(encoding="utf-8")
    assert "@supports (grid-template-columns: subgrid)" in css
    assert "@supports (container-type: inline-size)" in css
    assert "@supports selector(:has(*))" in css


def test_os_cinco_recursos_modernos_aparecem_no_css():
    css = CSS.read_text(encoding="utf-8")
    for recurso in ("subgrid", "@container", ":has(", "view-transition-name",
                    "@starting-style"):
        assert recurso in css, recurso
    assert "transition-behavior: allow-discrete" in css


def test_o_piso_de_keyframes_existe_sem_nenhum_recurso_novo():
    """A alternativa precisa estar FORA de qualquer `@supports`, senão o
    piso não é piso. Easing da casa, o mesmo do Admita."""
    css = CSS.read_text(encoding="utf-8")
    fora_de_supports = re.sub(r"@supports[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css)
    assert "@keyframes nt-entra" in fora_de_supports
    assert "cubic-bezier(.2,.75,.3,1)" in fora_de_supports


def test_nenhuma_cor_nova_foi_inventada():
    """§4.1: a barra de comando escura usa `--marca-faixa-fundo` (#101828),
    que já está na prancha aprovada. Hex solto no layout é identidade
    saindo do controle."""
    css = CSS.read_text(encoding="utf-8")
    corpo = css.split(".lab-demo.demo-notavel {", 1)[1]
    corpo = corpo.split("\n}", 1)[1]  # tudo DEPOIS do bloco de tokens
    hexes = set(re.findall(r"#[0-9A-Fa-f]{3,8}\b", corpo))
    permitidos = {"#E7F3EC", "#DCEBEA", "#FBF1DC"}  # os três da §ícones, já existentes
    assert hexes <= permitidos, f"cor nova fora dos tokens: {hexes - permitidos}"


# ------------------------------------------------ a fila e a marca dela --

def test_a_fila_mostra_fornecedor_valor_vencimento_e_categoria(db):
    html = _html(db)
    assert "Provedor de nuvem" in html
    assert "R$ 6.480,00" in html
    assert "Aluguel" in html


def test_o_despacho_que_nao_cabe_vem_marcado_pelo_servidor(db):
    """A fila se veste sozinha no CSS (`:has()`), sem classe de JavaScript.
    Quem sabe se cabe é o domínio, e a marca já vem no HTML."""
    html = _html(db)
    assert 'data-cabe="false"' in html
    assert html.count('data-cabe="false"') == 1
    assert html.count('data-cabe="true"') == 4


def test_cada_despacho_traz_os_botoes_de_aprovar_e_recusar(db):
    html = _html(db)
    assert 'data-acao="aprovar"' in html
    assert 'data-acao="recusar"' in html


# --------------------------------------------------------- página cheia --

def test_a_pagina_cheia_estende_a_moldura_e_carrega_o_script(db):
    html = _html(db, "lab/notavel/painel.html")
    assert 'class="site-header"' in html          # moldura do site
    assert "lab-faixa" in html                    # faixa de conversão
    assert "/static/lab/notavel.js" in html
    assert 'id="nt-app"' in html


def test_a_pagina_cheia_nao_usa_travessao_no_texto_visivel(db):
    """Regra permanente do Leandro. Varre o texto entre tags, ignorando
    atributos e comentários."""
    html = _html(db, "lab/notavel/painel.html")
    sem_comentario = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    visivel = re.sub(r"<[^>]+>", " ", sem_comentario)
    assert "—" not in visivel
    assert "–" not in visivel


def test_nenhum_safe_sobre_dado_de_visitante_nos_templates_do_notavel():
    """§9.2, e `tests/lab/test_regras_seguranca.py` já varre a pasta
    inteira. Este teste existe para a falha apontar o arquivo certo."""
    pasta = Path(__file__).resolve().parents[2] / "app" / "templates" / "lab" / "notavel"
    for caminho in pasta.rglob("*.html"):
        assert "|safe" not in caminho.read_text(encoding="utf-8"), caminho
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel_tela.py -q`
Expected: FAIL, `jinja2.exceptions.TemplateNotFound: lab/notavel/_shell.html`.

- [ ] **Step 3: `pontos_da_linha`, em `app/lab/notavel.py`**

```python
def pontos_da_linha(serie: list[int], largura: int = 220,
                    altura: int = 48) -> str:
    """A série vira o atributo `points` de um `<polyline>`, pronto.

    Desenhada NO SERVIDOR de propósito (§4): sem JavaScript o painel
    aparece completo, e a animação de chegada só anima o traço de uma linha
    que já está lá. Calcular isto no navegador exigiria mandar a série como
    JSON e desenhar depois, que é a piscada de tela vazia que a §4 proíbe.

    Série constante (ninguém movimentou a conta) vira uma reta no meio, em
    vez de dividir por zero na normalização.
    """
    if not serie:
        return ""
    menor, maior = min(serie), max(serie)
    intervalo = maior - menor
    passo = largura / (len(serie) - 1) if len(serie) > 1 else 0.0
    pontos = []
    for i, valor in enumerate(serie):
        if intervalo == 0:
            y = altura / 2
        else:
            y = altura - (valor - menor) * altura / intervalo
        pontos.append(f"{i * passo:.1f},{y:.1f}")
    return " ".join(pontos)
```

E dentro de `montar_contexto`, no bloco `"kpi"`, acrescente a chave:

```python
        "kpi": {
            "rotulo": "A receber",
            "valor": formatar_reais(numeros["a_receber_centavos"]),
            "centavos": numeros["a_receber_centavos"],
            "serie": serie_saldo(db, sandbox),
            "linha": pontos_da_linha(serie_saldo(db, sandbox)),
        },
```

Calcule a série uma vez só, numa variável local acima do `return`, para não consultar o extrato duas vezes:

```python
    serie = serie_saldo(db, sandbox)
```

e use `serie` nas duas chaves.

- [ ] **Step 4: `app/templates/lab/notavel/_shell.html`**

```html
{# ============================================================
   Fragmento trocado por TODA rota de mutação do Notável (emitir,
   cancelar, aprovar, recusar, pulso) e também incluído dentro de
   `painel.html` no primeiro carregamento. Mesmo contexto dos dois lados
   (`app/lab/notavel.py::montar_contexto`), pelo mesmo motivo do Admita: as
   seis regiões nunca saem inconsistentes entre si.

   AS SEIS REGIÕES (§3 da spec), cada uma com `data-regiao`, que é o
   contrato com `notavel.js`: é por ele que a chegada escalona a entrada e
   que a reação sabe o que mover.

   O PAINEL NASCE PRONTO (§4): todo número animável carrega o valor final
   NO TEXTO e o inteiro em centavos em `data-valor`. Sem JavaScript, a tela
   aparece completa e correta, só sem a contagem.

   ZERO ROLAGEM (§13b): a página nunca rola. As duas listas (fila e
   movimentos) rolam DENTRO delas, com `.rola-interno` de lab-base.css.
   ============================================================ #}
<div class="nt-shell" id="nt-shell">

  {# ---------- 1. barra de comando (§4.1: a faixa grave do topo) ------- #}
  <header class="nt-comando" data-regiao="comando">
    <span class="nt-comando-marca">
      <img src="/static/lab/img/simbolo-notavel.svg?v={{ asset_v }}" alt="" width="22" height="22">
      <img class="nt-comando-palavra" src="/static/lab/img/marca-notavel.svg?v={{ asset_v }}"
           alt="Notável" width="92" height="18">
    </span>
    <div class="nt-comando-empresa">
      <strong>{{ empresa.nome }}</strong>
      <span class="num-documento">{{ empresa.cnpj }}</span>
    </div>
    <dl class="nt-comando-fiscal">
      <div><dt>CNAE</dt><dd class="num-documento">{{ empresa.cnae }}</dd></div>
      <div><dt>Regime</dt><dd>{{ empresa.regime }}, Anexo {{ empresa.anexo }}</dd></div>
      <div><dt>Alíquota efetiva</dt><dd class="num-documento">{{ aliquota_efetiva }}</dd></div>
    </dl>
    <p class="nt-comando-vigencia" title="{{ empresa.cnae_descricao }}">
      {{ vigencia_rotulo }}
    </p>
    <span class="nt-comando-usuario">{{ usuario }}<em>{{ usuario_perfil }}</em></span>
  </header>

  <div class="nt-grade">

    {# ---------- 2. faixa de saldos ---------- #}
    <section class="nt-saldos" data-regiao="saldos" aria-label="Saldos">
      {% for saldo in saldos_exibidos %}
      <div class="nt-saldo" data-saldo="{{ saldo.chave }}">
        <span class="nt-saldo-rotulo">{{ saldo.rotulo }}</span>
        <strong class="nt-numero" data-valor="{{ saldo.centavos }}">{{ saldo.valor }}</strong>
      </div>
      {% endfor %}
    </section>

    {# ---------- 3. KPI grande, com a linha dos 30 dias ---------- #}
    <section class="nt-kpi" data-regiao="kpi" aria-label="{{ kpi.rotulo }}">
      <span class="nt-kpi-rotulo">{{ kpi.rotulo }}</span>
      <strong class="nt-kpi-valor nt-numero" data-valor="{{ kpi.centavos }}">{{ kpi.valor }}</strong>
      {# Desenhada no servidor: sem JavaScript ela já está aqui, inteira.
         A chegada só anima o traço dela. #}
      <svg class="nt-kpi-linha" viewBox="0 0 220 48" preserveAspectRatio="none"
           aria-hidden="true" focusable="false">
        <polyline points="{{ kpi.linha }}" fill="none" stroke="currentColor"
                  stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
      </svg>
      <span class="nt-kpi-nota">saldo em conta, últimos 30 dias</span>
    </section>

    {# ---------- 4. câmbio do dia ---------- #}
    <section class="nt-cambio" data-regiao="cambio" aria-label="Câmbio do dia">
      <h2 class="nt-titulo">Câmbio do dia</h2>
      <ul class="nt-cambio-lista">
        {% for cotacao in cotacoes %}
        <li>
          <span class="nt-cambio-moeda num-documento">{{ cotacao.moeda }}</span>
          <span class="nt-cambio-nome">{{ cotacao.nome }}</span>
          <strong class="num-documento">R$ {{ cotacao.valor }}</strong>
        </li>
        {% endfor %}
      </ul>
      <p class="nt-cambio-fonte">
        PTAX do Banco Central, cotação de
        <time datetime="{{ cotacoes[0].dia_cotacao }}">{{ cotacoes[0].dia_cotacao.strftime('%d/%m/%Y') }}</time>
      </p>
    </section>

    {# ---------- 5. fila de despachos: onde o visitante age ---------- #}
    <section class="nt-despachos" data-regiao="despachos" aria-label="Despachos para pagamento">
      <h2 class="nt-titulo">
        Despachos
        <span class="pill pill-neutra">{{ despachos|length }} na fila</span>
      </h2>
      <ul class="nt-fila rola-interno">
        {% for despacho in despachos %}
        {# `data-cabe` vem do DOMÍNIO (`montar_contexto`), nunca do
           JavaScript: é ele que deixa a fila se vestir sozinha no CSS. #}
        <li class="nt-despacho" data-despacho="{{ despacho.id }}"
            data-cabe="{{ 'true' if despacho.cabe_no_saldo else 'false' }}">
          <div class="nt-despacho-quem">
            <strong>{{ despacho.fornecedor }}</strong>
            <span>{{ despacho.categoria }} · vence {{ despacho.vence_em.strftime('%d/%m') }}</span>
          </div>
          <strong class="nt-despacho-valor num-documento">{{ despacho.valor }}</strong>
          <div class="nt-despacho-acoes">
            <button type="button" class="botao botao-primario"
                    data-acao="aprovar" data-despacho-id="{{ despacho.id }}">
              <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-check"/></svg>
              Aprovar
            </button>
            <button type="button" class="botao botao-secundario"
                    data-acao="recusar" data-despacho-id="{{ despacho.id }}">
              <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-cancelar"/></svg>
              Recusar
            </button>
          </div>
          {# A recusa por saldo é escrita AQUI pelo notavel.js, com os três
             números que a rota devolve no 409. Fica dentro da linha, e não
             num toast que some: a §5.3 é a peça central, e peça central
             não desaparece em quatro segundos. #}
          <p class="nt-despacho-recusa" data-recusa hidden role="alert"></p>
        </li>
        {% else %}
        <li class="nt-vazio">Nenhum pagamento aguardando aprovação.</li>
        {% endfor %}
      </ul>
    </section>

    {# ---------- 6. últimos movimentos ---------- #}
    <section class="nt-movimentos" data-regiao="movimentos" aria-label="Últimos movimentos">
      <h2 class="nt-titulo">
        Últimos movimentos
        <button type="button" class="botao botao-primario nt-emitir"
                data-acao="abrir-emissao">
          <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-nota-mais"/></svg>
          Emitir nota
        </button>
      </h2>
      <ul class="nt-lista rola-interno">
        {% for movimento in movimentos %}
        <li class="nt-movimento" data-movimento="{{ movimento.chave }}"
            data-entrada="{{ 'true' if movimento.entrada else 'false' }}">
          <span class="icone-caixa categoria-{{ 'nota' if movimento.tipo == 'nota' else ('receita' if movimento.entrada else 'tarifa') }}">
            <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#{{ 'i-nota' if movimento.tipo == 'nota' else ('i-cifrao' if movimento.entrada else 'i-cartao') }}"/></svg>
          </span>
          <div class="nt-movimento-texto">
            <strong>{{ movimento.descricao }}</strong>
            <span>{{ movimento.categoria }}</span>
          </div>
          <strong class="nt-movimento-valor num-documento">{{ movimento.valor }}</strong>
        </li>
        {% else %}
        <li class="nt-vazio">Nenhum movimento ainda.</li>
        {% endfor %}
      </ul>
    </section>

  </div>
</div>
```

- [ ] **Step 5: `app/templates/lab/notavel/painel.html`**

```html
{# ============================================================
   Notável, painel financeiro (§3 da spec). Estende
   `lab/_base_demo.html`: a moldura é do site, o miolo é território da
   marca do Notável.

   O miolo de verdade vive em `_shell.html`, que TODA rota de mutação
   devolve e que `notavel.js` troca dentro de `#nt-app` sem recarregar a
   página. O modal de emissão e o toast ficam FORA do fragmento trocado,
   para sobreviverem ao swap sem perder o foco.
   ============================================================ #}
{% extends "lab/_base_demo.html" %}

{% block demo_titulo %}Notável ·︎ Painel financeiro ·︎ Lab de Demos ·︎ {{ site_name }}{% endblock %}
{% block demo_descricao %}Painel financeiro que você usa agora, sem cadastro: emita nota fiscal de demonstração com o imposto explicado, aprove ou recuse pagamentos da fila, acompanhe saldos, câmbio do dia e os últimos movimentos.{% endblock %}

{% block demo_conteudo %}
<div class="nt-app" id="nt-app"
     data-max-registros="{{ max_registros }}"
     data-usuario="{{ usuario }}">
  {% include "lab/notavel/_shell.html" %}
</div>

{% include "lab/notavel/_emitir.html" %}

<div class="nt-toast" id="nt-toast" role="status" aria-live="polite" hidden></div>
{% endblock %}

{% block demo_scripts %}
<script src="/static/lab/notavel.js?v={{ asset_v }}" defer></script>
{% endblock %}
```

`_emitir.html` nasce vazio nesta task, com só o esqueleto do modal, e ganha o conteúdo na Task 9. Crie-o agora com o mínimo para o `include` não quebrar:

```html
{# Modal de emissão em três passos (§5.1). O conteúdo chega na Task 9;
   este arquivo nasce aqui porque `painel.html` já o inclui. #}
<div class="nt-modal-fundo" id="nt-modal-emitir" hidden></div>
```

- [ ] **Step 6: A camada de layout em `app/static/lab/notavel.css`**

Acrescente ABAIXO do bloco de tokens que já existe. Não mexa nos tokens: eles são a prancha aprovada.

```css
/* ============================================================
   LAYOUT DO PAINEL (§3 e §4.1 da spec do Notável).

   A gramática aqui é a de PAINEL DE INSTRUMENTOS, e não a de quadro de
   trabalho do Admita: a unidade é o número que muda, a densidade é alta,
   os blocos alinham entre si numa grade que os atravessa, e o topo tem
   uma faixa grave. É o que faz o visitante ver dois sistemas diferentes
   sem que nenhuma cor nova tenha sido inventada.

   O PISO É INEGOCIÁVEL. Tudo abaixo funciona num navegador que não tenha
   `subgrid`, `@container`, `:has()`, View Transitions nem
   `@starting-style`. Cada um dos três primeiros entra atrás de
   `@supports`, com a alternativa escrita ANTES; os dois últimos degradam
   sozinhos, porque propriedade e at-rule desconhecidas são ignoradas.
   Demo que quebra em navegador desatualizado convence do contrário do que
   o Lab existe para provar.
   ============================================================ */

.lab-demo.demo-notavel .nt-app {
  width: 100%;
  height: 100%;
  min-height: 0;   /* filho de grid: sem isto, a lista interna empurra a página */
  display: flex;
  flex-direction: column;
}

.lab-demo.demo-notavel .nt-shell {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 12px;
  min-height: 0;
  height: 100%;
}

/* --------------------------------------------- 1. barra de comando --- */
/* A faixa grave do topo, com o `--marca-faixa-fundo` que já existe na
   prancha. É o que muda o reconhecimento no primeiro olhar: o Admita é
   claro de ponta a ponta, o Notável tem um terminal no topo. */
.lab-demo.demo-notavel .nt-comando {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 18px;
  border-radius: 10px;
  background: var(--marca-faixa-fundo);
  color: var(--marca-faixa-texto);
  font-size: 0.82rem;
}

.lab-demo.demo-notavel .nt-comando-marca { display: flex; align-items: center; gap: 8px; }
.lab-demo.demo-notavel .nt-comando-empresa { display: grid; line-height: 1.25; }
.lab-demo.demo-notavel .nt-comando-empresa strong { font-family: var(--marca-fonte-display); }
.lab-demo.demo-notavel .nt-comando-empresa span { opacity: .72; font-size: .76rem; }

.lab-demo.demo-notavel .nt-comando-fiscal { display: flex; gap: 20px; margin: 0; }
.lab-demo.demo-notavel .nt-comando-fiscal dt {
  font-size: .66rem; letter-spacing: .08em; text-transform: uppercase; opacity: .6;
}
.lab-demo.demo-notavel .nt-comando-fiscal dd { margin: 0; }
.lab-demo.demo-notavel .nt-comando-vigencia {
  margin: 0; margin-left: auto; opacity: .6; font-size: .72rem;
}
.lab-demo.demo-notavel .nt-comando-usuario { display: grid; text-align: right; }
.lab-demo.demo-notavel .nt-comando-usuario em { opacity: .6; font-style: normal; font-size: .72rem; }

/* ------------------------------------------------------- 2 a 6. grade --- */
/* Piso: grade explícita de 12 colunas. A altura vem de `1fr`, então o
   painel inteiro cabe numa tela e nada rola fora das listas. */
.lab-demo.demo-notavel .nt-grade {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: minmax(0, auto);
  gap: 12px;
  min-height: 0;
}

.lab-demo.demo-notavel .nt-saldos { grid-column: span 8; display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.lab-demo.demo-notavel .nt-kpi { grid-column: span 4; grid-row: span 2; }
.lab-demo.demo-notavel .nt-cambio { grid-column: span 8; }
.lab-demo.demo-notavel .nt-despachos { grid-column: span 7; min-height: 0; }
.lab-demo.demo-notavel .nt-movimentos { grid-column: span 5; min-height: 0; }

.lab-demo.demo-notavel .nt-saldo,
.lab-demo.demo-notavel .nt-kpi,
.lab-demo.demo-notavel .nt-cambio,
.lab-demo.demo-notavel .nt-despachos,
.lab-demo.demo-notavel .nt-movimentos {
  background: var(--marca-superficie);
  border: 1px solid var(--marca-borda);
  border-radius: 10px;
  padding: 14px 16px;
}

/* Todo número do painel é tabular e monoespaçado: precisão visual É a
   identidade de software financeiro, e dígito que dança de largura
   destrói o alinhamento de uma coluna de valores. */
.lab-demo.demo-notavel .nt-numero,
.lab-demo.demo-notavel .nt-movimento-valor,
.lab-demo.demo-notavel .nt-despacho-valor {
  font-family: var(--marca-fonte-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.lab-demo.demo-notavel .nt-saldo { display: grid; gap: 4px; }
.lab-demo.demo-notavel .nt-saldo-rotulo {
  font-size: .68rem; letter-spacing: .08em; text-transform: uppercase;
  color: var(--marca-texto-suave);
}
.lab-demo.demo-notavel .nt-kpi-valor { font-size: clamp(1.8rem, 3.4vw, 2.8rem); display: block; }
.lab-demo.demo-notavel .nt-kpi-linha { width: 100%; height: 48px; color: var(--marca-primaria); }
.lab-demo.demo-notavel .nt-kpi-nota { color: var(--marca-texto-suave); font-size: .72rem; }

.lab-demo.demo-notavel .nt-fila,
.lab-demo.demo-notavel .nt-lista { list-style: none; margin: 0; padding: 0; min-height: 0; }

.lab-demo.demo-notavel .nt-despacho {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--marca-borda);
}
.lab-demo.demo-notavel .nt-despacho-recusa {
  grid-column: 1 / -1;
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--marca-negativo-fundo);
  color: var(--marca-negativo);
  font-size: .8rem;
}

.lab-demo.demo-notavel .nt-movimento {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}
.lab-demo.demo-notavel .nt-movimento[data-entrada="true"] .nt-movimento-valor { color: var(--marca-positivo); }
.lab-demo.demo-notavel .nt-movimento[data-entrada="false"] .nt-movimento-valor { color: var(--marca-negativo); }

/* ------------------------------------------------------------ PISO ---- */
/* O vocabulário de motion que o Admita já provou. Toda animação da Task
   10 cai aqui quando um recurso novo não existir. */
@keyframes nt-entra {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: none; }
}
@keyframes nt-sai {
  to { opacity: 0; transform: translateX(14px); }
}
@keyframes nt-pulso {
  0%, 100% { box-shadow: 0 0 0 0 transparent; }
  40%      { box-shadow: 0 0 0 6px var(--marca-superficie-ia); }
}

.lab-demo.demo-notavel [data-regiao] {
  animation: nt-entra .42s cubic-bezier(.2,.75,.3,1) both;
}

/* ======================= MELHORIA PROGRESSIVA ======================= */

/* subgrid: os números alinham ATRAVÉS dos blocos independentes, não só
   dentro de cada um. Sem ele, o alinhamento entre a faixa de saldos e o
   KPI exigiria medida fixa, que quebra em outro idioma ou com zoom. */
@supports (grid-template-columns: subgrid) {
  .lab-demo.demo-notavel .nt-saldos {
    grid-column: span 8;
    grid-template-columns: subgrid;
  }
  .lab-demo.demo-notavel .nt-saldo { grid-column: span 2; }
}

/* @container: cada região se dimensiona pela PRÓPRIA largura, não pela
   janela. É o que faz a mesma região servir ao painel no desktop e ao
   modo aplicativo no celular sem CSS duplicado (Task 11). */
@supports (container-type: inline-size) {
  .lab-demo.demo-notavel .nt-despachos,
  .lab-demo.demo-notavel .nt-movimentos,
  .lab-demo.demo-notavel .nt-kpi {
    container-type: inline-size;
  }
  @container (max-width: 380px) {
    .lab-demo.demo-notavel .nt-despacho { grid-template-columns: 1fr auto; }
    .lab-demo.demo-notavel .nt-despacho-acoes { grid-column: 1 / -1; }
  }
}

/* :has(): estado sem classe de JavaScript. A fila que contém um item
   bloqueado se estiliza sozinha, e o valor negativo se veste sozinho.
   Menos JavaScript é menos lugar para dessincronizar. */
@supports selector(:has(*)) {
  .lab-demo.demo-notavel .nt-fila:has([data-cabe="false"]) {
    border-left: 2px solid var(--marca-alerta);
    padding-left: 10px;
  }
  .lab-demo.demo-notavel .nt-despacho:has([data-recusa]:not([hidden])) {
    background: var(--marca-negativo-fundo);
  }
  .lab-demo.demo-notavel .nt-despacho[data-cabe="false"] .nt-despacho-valor {
    color: var(--marca-alerta);
  }
}

/* View Transitions: a saída do despacho da fila e a entrada da nota na
   lista com transição nativa, curta e física, em vez de dois keyframes
   coordenados na mão. Degrada sozinho: `view-transition-name` é ignorado
   por quem não conhece, e `notavel.js` testa
   `document.startViewTransition` antes de usar. */
.lab-demo.demo-notavel .nt-despacho { view-transition-name: none; }
.lab-demo.demo-notavel .nt-despacho.nt-saindo { view-transition-name: nt-despacho-saindo; }

/* @starting-style: entrada de elemento que acabou de existir, sem truque
   de JavaScript. `allow-discrete` é o que faz a transição valer também
   para `display`, que muda de forma discreta. */
.lab-demo.demo-notavel .nt-despacho-recusa {
  opacity: 1;
  transition: opacity .28s cubic-bezier(.2,.75,.3,1), display .28s allow-discrete;
  transition-behavior: allow-discrete;
}
@starting-style {
  .lab-demo.demo-notavel .nt-despacho-recusa { opacity: 0; }
}

/* Regra da casa, não exceção desta demo. */
@media (prefers-reduced-motion: reduce) {
  .lab-demo.demo-notavel [data-regiao],
  .lab-demo.demo-notavel .nt-despacho,
  .lab-demo.demo-notavel .nt-movimento {
    animation: none !important;
  }
  .lab-demo.demo-notavel * { transition-duration: .01ms !important; }
}
```

- [ ] **Step 7: Tirar os cinco `xfail` das Tasks 6 e 7**

Em `tests/lab/test_notavel.py`, remova as marcas `@pytest.mark.xfail(reason="templates chegam na Task 8", strict=True)` dos cinco testes de rota. Com `strict=True`, deixá-las agora quebra a suíte, que é exatamente o efeito desejado.

- [ ] **Step 8: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel_tela.py tests/lab/test_notavel.py -q`
Expected: PASS. Se `test_nenhuma_cor_nova_foi_inventada` falhar, algum hex entrou no layout: troque por um token.

- [ ] **Step 9: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1594 passed, zero falha, zero xfail.

- [ ] **Step 10: Commit**

```bash
git add app/templates/lab/notavel app/static/lab/notavel.css app/lab/notavel.py tests/lab/test_notavel_tela.py tests/lab/test_notavel.py
git commit -m "Notavel: a tela heroina com as seis regioes e a barra de comando"
```

---

### Task 9: Emitir em três passos, e a recusa desenhada na tela

O modal da §5.1 e o `notavel.js` que troca o fragmento. Duas decisões governam esta task:

**A prévia do imposto vem do servidor.** O passo 3 mostra base, alíquota, valor e rótulo humano de cada imposto. Calcular isso no navegador criaria uma segunda implementação da mesma regra, e o dia em que as duas divergissem o visitante veria uma conta na prévia e outra na nota emitida. Uma volta ao servidor local custa milissegundos e garante uma regra só.

**A recusa por saldo não é toast.** Ela é escrita dentro da linha do despacho, com os três números, e fica lá. A §5.3 é a peça central; peça central não desaparece em quatro segundos.

**Files:**
- Create: `app/templates/lab/notavel/_memoria.html`
- Create: `app/static/lab/notavel.js`
- Modify: `app/templates/lab/notavel/_emitir.html` (o esqueleto da Task 8 ganha conteúdo)
- Modify: `app/lab/rotas.py` (a rota da prévia)
- Test: `tests/lab/test_notavel_tela.py`, `tests/lab/test_notavel.py`

**Interfaces:**
- Consumes: `fiscal.memoria_de_calculo` (Task 1); `_centavos_do_texto`, `_renderizar_shell_notavel` (Task 6); os marcadores de DOM da Task 8.
- Produces:
  - rota `POST /lab/notavel/notas/previa` devolvendo o fragmento `_memoria.html`
  - `notavel.js` com `trocarFragmento`, `mostrarToast`, `desenharRecusa`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/lab/test_notavel.py`:

```python
def test_a_previa_do_imposto_vem_do_servidor(client, db_session):
    """§5.1: os impostos aparecem explicados na tela, com base, alíquota e
    valor. A conta é feita no MESMO lugar que a emissão faz, e não repetida
    em JavaScript: duas implementações da mesma regra divergem, e o dia em
    que divergirem o visitante vê uma conta na prévia e outra na nota."""
    client.get("/lab/notavel")
    r = client.post("/lab/notavel/notas/previa", data={
        "descricao": ["Hora de desenvolvimento"],
        "quantidade": ["1"],
        "valor": ["10.000,00"],
    })
    assert r.status_code == 200
    assert "ISS (5% simulado)" in r.text
    assert "DAS do Simples Nacional" in r.text
    assert "13,59%" in r.text
    assert "R$ 1.359,00" in r.text
    assert "R$ 10.000,00" in r.text


def test_a_previa_nunca_grava_nota_nenhuma(client, db_session):
    from app.lab.models import LabNota as _N

    client.get("/lab/notavel")
    antes = db_session.query(_N).count()
    client.post("/lab/notavel/notas/previa", data={
        "descricao": ["X"], "quantidade": ["1"], "valor": ["100,00"],
    })
    assert db_session.query(_N).count() == antes


def test_a_previa_com_item_invalido_devolve_o_aviso_e_nao_estoura(client):
    client.get("/lab/notavel")
    r = client.post("/lab/notavel/notas/previa", data={
        "descricao": [""], "quantidade": ["1"], "valor": ["0"],
    })
    assert r.status_code == 409
```

E acrescente a `tests/lab/test_notavel_tela.py`:

```python
JS = RAIZ_LAB / "notavel.js"


# --------------------------------------------------- modal de emissão --

def test_o_modal_tem_os_tres_passos(db):
    html = _html(db, "lab/notavel/painel.html")
    assert 'data-passo="1"' in html
    assert 'data-passo="2"' in html
    assert 'data-passo="3"' in html


def test_o_passo_um_lista_os_clientes_do_sandbox(db):
    html = _html(db, "lab/notavel/painel.html")
    assert "Estúdio Aurora" in html
    assert html.count('name="cliente_id"') == 1


def test_o_passo_dois_tem_tres_linhas_de_item(db):
    """Três itens é o que cabe no modal sem ele virar planilha, e bate com
    `notavel.MAX_ITENS`."""
    html = _html(db, "lab/notavel/painel.html")
    assert html.count('name="descricao"') == notavel.MAX_ITENS
    assert html.count('name="quantidade"') == notavel.MAX_ITENS
    assert html.count('name="valor"') == notavel.MAX_ITENS


def test_o_modal_avisa_que_o_documento_nao_tem_valor_fiscal(db):
    """A tarja está no PDF desde o Plano 1. Ela precisa estar na TELA
    também: quem clica em "emitir" tem que saber antes, não depois de
    abrir o arquivo."""
    html = _html(db, "lab/notavel/painel.html")
    assert "SEM VALOR FISCAL" in html


# ------------------------------------------------------ JavaScript ----

def test_o_js_nao_carrega_biblioteca_externa():
    """§4: sem GSAP dentro do Lab, e sem host externo nenhum (§15 das
    Global Constraints)."""
    js = JS.read_text(encoding="utf-8")
    assert "gsap" not in js.lower()
    assert "http://" not in js
    assert "https://" not in js
    assert "import " not in js


def test_o_js_troca_o_fragmento_em_vez_de_recarregar_a_pagina():
    js = JS.read_text(encoding="utf-8")
    assert "nt-shell" in js
    assert "fetch(" in js
    assert "location.reload" not in js


def test_o_js_desenha_a_recusa_por_saldo_com_os_tres_numeros():
    """§5.3: a recusa vem com saldo disponível, valor do despacho e
    diferença, e fica NA LINHA do despacho, não num toast que some."""
    js = JS.read_text(encoding="utf-8")
    assert "saldo_insuficiente" in js
    assert "data-recusa" in js
    for chave in ("disponivel", "valor", "faltam"):
        assert chave in js, chave


def test_o_js_respeita_quem_pediu_menos_movimento():
    js = JS.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in js
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel_tela.py -q`
Expected: FAIL, `FileNotFoundError` em `notavel.js` e `data-passo` ausente.

- [ ] **Step 3: A rota da prévia, em `app/lab/rotas.py`**

```python
@router.post("/notavel/notas/previa")
async def notavel_previa_dos_impostos(
    descricao: list[str] = Form(default=[]),
    quantidade: list[str] = Form(default=[]),
    valor: list[str] = Form(default=[]),
    sandbox: LabSandbox = Depends(_exigir_sandbox),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Passo 3 do modal: os impostos explicados, calculados AQUI.

    Uma volta ao servidor local custa milissegundos e garante uma regra só.
    Repetir a conta em JavaScript criaria uma segunda implementação da
    mesma alíquota, e o dia em que as duas divergissem o visitante veria
    uma conta na prévia e outra na nota emitida."""
    from ..main import templates

    itens = [
        {
            "descricao": texto,
            "quantidade": quantidade[i] if i < len(quantidade) else 0,
            "valor_unit_centavos": _centavos_do_texto(
                valor[i] if i < len(valor) else ""),
        }
        for i, texto in enumerate(descricao)
        if str(texto).strip()
    ]
    try:
        contexto = _notavel_dados.previa_dos_impostos(db, sandbox, itens)
    except ValueError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return HTMLResponse(
        templates.get_template("lab/notavel/_memoria.html").render(**contexto)
    )
```

E em `app/lab/notavel.py`:

```python
def previa_dos_impostos(db: Session, sandbox: LabSandbox,
                        itens: list[dict]) -> dict:
    """A memória de cálculo do que o visitante acabou de digitar, sem
    gravar nada. Passa pelas MESMAS validações da emissão: prévia que
    aceita o que a emissão recusa é prévia mentirosa."""
    limpos = _validar_itens(itens)
    subtotal = sum(i["quantidade"] * i["valor_unit_centavos"] for i in limpos)
    empresa = empresa_da_sandbox(db, sandbox)
    memoria = fiscal.memoria_de_calculo(subtotal, empresa.rbt12_centavos,
                                        empresa.anexo)
    for linha in memoria:
        linha["base"] = formatar_reais(linha["base_centavos"])
        linha["valor"] = formatar_reais(linha["valor_centavos"])
        linha["aliquota"] = fiscal.formatar_aliquota(linha["aliquota_bps"])
    return {
        "itens": limpos,
        "subtotal": formatar_reais(subtotal),
        "subtotal_centavos": subtotal,
        "memoria": memoria,
        "vigencia_rotulo": fiscal.VIGENCIA_ROTULO,
    }
```

- [ ] **Step 4: `app/templates/lab/notavel/_memoria.html`**

```html
{# Passo 3 do modal: os impostos EXPLICADOS (§5.1). Fragmento devolvido
   por `POST /lab/notavel/notas/previa` e escrito dentro do passo 3 pelo
   `notavel.js`. Cada linha diz base, alíquota, valor e o rótulo humano do
   imposto: um painel que só mostra o total pede confiança; um que mostra a
   conta a merece. #}
<table class="nt-memoria">
  <caption class="nt-memoria-titulo">Memória de cálculo, {{ vigencia_rotulo }}</caption>
  <thead>
    <tr><th scope="col">Imposto</th><th scope="col">Base</th>
        <th scope="col">Alíquota</th><th scope="col">Valor</th></tr>
  </thead>
  <tbody>
    {% for linha in memoria %}
    <tr>
      <th scope="row">
        {{ linha.rotulo }}
        <em class="nt-memoria-nota">{{ linha.observacao }}</em>
      </th>
      <td class="num-documento">{{ linha.base }}</td>
      <td class="num-documento">{{ linha.aliquota }}</td>
      <td class="num-documento">{{ linha.valor }}</td>
    </tr>
    {% endfor %}
  </tbody>
  <tfoot>
    <tr>
      <th scope="row" colspan="3">Total da nota</th>
      <td class="num-documento">{{ subtotal }}</td>
    </tr>
  </tfoot>
</table>
```

- [ ] **Step 5: `app/templates/lab/notavel/_emitir.html`**

```html
{# Emissão em três passos (§5.1): cliente, itens, impostos explicados.
   FORA do fragmento trocado (`_shell.html`), para sobreviver ao swap sem
   perder o foco de quem está digitando.

   O passo 3 é preenchido pelo `notavel.js` com o fragmento que
   `POST /lab/notavel/notas/previa` devolve: a conta do imposto é feita no
   servidor, num lugar só. #}
<div class="nt-modal-fundo" id="nt-modal-emitir" hidden>
  <form class="nt-modal" id="nt-form-emitir" aria-labelledby="nt-modal-titulo" novalidate>
    <header class="nt-modal-topo">
      <span class="nt-modal-ic">
        <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-nota-mais"/></svg>
      </span>
      <div>
        <h2 id="nt-modal-titulo">Emitir nota</h2>
        <p class="nt-modal-sub">Três passos: o cliente, os itens e o imposto explicado.</p>
      </div>
      <p class="nt-modal-tarja">DEMONSTRAÇÃO, SEM VALOR FISCAL</p>
    </header>

    <ol class="nt-passos" aria-label="Passos da emissão">
      <li data-passo-marca="1" class="ativo">Cliente</li>
      <li data-passo-marca="2">Itens</li>
      <li data-passo-marca="3">Impostos</li>
    </ol>

    <section data-passo="1">
      <label class="nt-campo">
        <span>Cliente</span>
        <select name="cliente_id" required>
          <option value="" disabled selected>Selecione um cliente</option>
          {% for cliente in clientes %}
          <option value="{{ cliente.id }}">{{ cliente.nome }}</option>
          {% endfor %}
        </select>
      </label>
    </section>

    <section data-passo="2" hidden>
      {% for i in range(3) %}
      <div class="nt-item">
        <label class="nt-campo">
          <span>Descrição do serviço</span>
          <input type="text" name="descricao" maxlength="200" autocomplete="off"
                 placeholder="{{ 'Ex.: Hora de desenvolvimento' if i == 0 else 'Opcional' }}">
        </label>
        <label class="nt-campo nt-campo-curto">
          <span>Qtd.</span>
          <input type="text" name="quantidade" inputmode="numeric" value="{{ 1 if i == 0 else '' }}">
        </label>
        <label class="nt-campo nt-campo-curto">
          <span>Valor unitário</span>
          <input type="text" name="valor" inputmode="decimal" placeholder="0,00">
        </label>
      </div>
      {% endfor %}
    </section>

    <section data-passo="3" hidden>
      <div data-memoria><!-- preenchido por notavel.js --></div>
    </section>

    <p class="nt-modal-erro" id="nt-modal-erro" role="alert" hidden></p>

    <div class="nt-modal-acoes">
      <button type="button" class="botao botao-secundario" data-acao="modal-voltar">Voltar</button>
      <button type="button" class="botao botao-primario" data-acao="modal-avancar">Avançar</button>
      <button type="submit" class="botao botao-primario" data-acao="modal-emitir" hidden>
        <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-nota-check"/></svg>
        Emitir nota
      </button>
    </div>
  </form>
</div>
```

Acrescente ao CSS o mínimo para o modal e a memória: `.nt-modal-fundo` cobrindo a tela, `.nt-modal` centralizado na superfície, `.nt-passos` em linha com o passo ativo em destaque, `.nt-memoria` com `font-variant-numeric: tabular-nums` nas células de valor e `.nt-memoria-nota` menor e em `--marca-texto-suave`. Nada de hex novo: só tokens.

- [ ] **Step 6: `app/static/lab/notavel.js`**

```javascript
/* ============================================================
   Notável, painel financeiro (Task 9 do plano do corte 1).

   PADRÃO DE INTERAÇÃO, o mesmo do Admita e pelos mesmos motivos:
   - Toda mutação faz um `fetch` POST e recebe de volta o MESMO fragmento
     (`lab/notavel/_shell.html`), que substitui `#nt-shell` inteiro. As
     seis regiões saem sempre consistentes entre si, nunca meia atualizada.
   - Estado que não é do servidor (passo do modal, região ativa no modo
     aplicativo) vive só aqui e é reaplicado depois de cada troca.
   - Nada recarrega a página.

   A RECUSA POR SALDO (§5.3) É A EXCEÇÃO DELIBERADA. Ela não vira toast:
   é escrita DENTRO da linha do despacho, com os três números que a rota
   devolve no 409, e fica lá. Peça central de demonstração não desaparece
   em quatro segundos.
   ============================================================ */
(function () {
  "use strict";

  var app = document.getElementById("nt-app");
  if (!app) return;

  var estado = { passo: 1 };

  function menosMovimento() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  // ------------------------------------------------------------ toast --
  function mostrarToast(mensagem) {
    var toast = document.getElementById("nt-toast");
    if (!toast) return;
    toast.textContent = mensagem;
    toast.hidden = false;
    requestAnimationFrame(function () { toast.classList.add("visivel"); });
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(function () {
      toast.classList.remove("visivel");
      window.setTimeout(function () { toast.hidden = true; }, 220);
    }, 4200);
  }

  // ------------------------------------------------- troca de fragmento --
  function trocarFragmento(html) {
    var atual = document.getElementById("nt-shell");
    if (!atual) return;
    var caixa = document.createElement("div");
    caixa.innerHTML = html;
    var novo = caixa.querySelector("#nt-shell") || caixa.firstElementChild;
    // View Transitions quando existir; keyframes do CSS quando não. O
    // painel é o mesmo nos dois casos, só a passagem entre um estado e o
    // outro é mais física com a API nativa.
    if (document.startViewTransition && !menosMovimento()) {
      document.startViewTransition(function () { atual.replaceWith(novo); });
    } else {
      atual.replaceWith(novo);
    }
    aoTrocar(novo);
  }

  function aoTrocar(shell) {
    aplicarModoApp();          // Task 11
    animarReacao(shell);       // Task 10
  }

  function desenharRecusa(despachoId, dados) {
    var linha = document.querySelector('[data-despacho="' + despachoId + '"]');
    if (!linha) { mostrarToast(dados.mensagem || "Não foi possível aprovar."); return; }
    var caixa = linha.querySelector("[data-recusa]");
    if (!caixa) return;
    caixa.textContent =
      "Recusado: o saldo disponível é " + dados.disponivel +
      " e este despacho é de " + dados.valor +
      ". Faltam " + dados.faltam + ".";
    caixa.hidden = false;
    linha.setAttribute("data-cabe", "false");
  }

  async function enviar(url, corpo, despachoId) {
    var resposta;
    try {
      resposta = await fetch(url, { method: "POST", body: corpo });
    } catch (e) {
      mostrarToast("Sem conexão com o servidor. Tente de novo.");
      return null;
    }
    if (resposta.ok) {
      trocarFragmento(await resposta.text());
      return true;
    }
    var detalhe = "";
    try { detalhe = (await resposta.json()).detail; } catch (e) { detalhe = ""; }
    if (detalhe && detalhe.motivo === "saldo_insuficiente") {
      desenharRecusa(despachoId, detalhe);
    } else {
      mostrarToast(typeof detalhe === "string" && detalhe
        ? detalhe : "Não foi possível concluir a ação.");
    }
    return false;
  }

  // ------------------------------------------------------ fila e ações --
  app.addEventListener("click", function (evento) {
    var botao = evento.target.closest("[data-acao]");
    if (!botao) return;
    var acao = botao.getAttribute("data-acao");
    var id = botao.getAttribute("data-despacho-id");

    if (acao === "aprovar") {
      enviar("/lab/notavel/despachos/" + id + "/aprovar", new FormData(), id);
    } else if (acao === "recusar") {
      var motivo = window.prompt("Por que este pagamento está sendo recusado?");
      if (!motivo) return;
      var corpo = new FormData();
      corpo.append("motivo", motivo);
      enviar("/lab/notavel/despachos/" + id + "/recusar", corpo, id);
    } else if (acao === "abrir-emissao") {
      abrirModal();
    }
  });

  // ------------------------------------------------- modal em 3 passos --
  var modal = document.getElementById("nt-modal-emitir");
  var form = document.getElementById("nt-form-emitir");

  function mostrarPasso(numero) {
    estado.passo = numero;
    form.querySelectorAll("[data-passo]").forEach(function (secao) {
      secao.hidden = Number(secao.getAttribute("data-passo")) !== numero;
    });
    form.querySelectorAll("[data-passo-marca]").forEach(function (marca) {
      marca.classList.toggle("ativo",
        Number(marca.getAttribute("data-passo-marca")) <= numero);
    });
    form.querySelector('[data-acao="modal-voltar"]').hidden = numero === 1;
    form.querySelector('[data-acao="modal-avancar"]').hidden = numero === 3;
    form.querySelector('[data-acao="modal-emitir"]').hidden = numero !== 3;
  }

  function abrirModal() {
    if (!modal) return;
    modal.hidden = false;
    mostrarPasso(1);
    var primeiro = form.querySelector("select, input");
    if (primeiro) primeiro.focus();
  }

  function fecharModal() { if (modal) modal.hidden = true; }

  async function carregarMemoria() {
    // A conta do imposto é do servidor, num lugar só: repetir a alíquota
    // aqui criaria uma segunda implementação da mesma regra.
    var corpo = new FormData(form);
    corpo.delete("cliente_id");
    var resposta = await fetch("/lab/notavel/notas/previa",
                               { method: "POST", body: corpo });
    var alvo = form.querySelector("[data-memoria]");
    if (!resposta.ok) {
      var detalhe = "";
      try { detalhe = (await resposta.json()).detail; } catch (e) {}
      avisar(detalhe || "Confira os itens antes de avançar.");
      return false;
    }
    alvo.innerHTML = await resposta.text();
    return true;
  }

  function avisar(texto) {
    var erro = document.getElementById("nt-modal-erro");
    if (!erro) return;
    erro.textContent = texto;
    erro.hidden = !texto;
  }

  if (form) {
    form.addEventListener("click", async function (evento) {
      var botao = evento.target.closest("[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao");
      if (acao === "modal-voltar") {
        if (estado.passo === 1) { fecharModal(); return; }
        mostrarPasso(estado.passo - 1);
      } else if (acao === "modal-avancar") {
        avisar("");
        if (estado.passo === 1 && !form.cliente_id.value) {
          avisar("Escolha o cliente da nota.");
          return;
        }
        if (estado.passo === 2 && !(await carregarMemoria())) return;
        mostrarPasso(estado.passo + 1);
      }
    });

    form.addEventListener("submit", async function (evento) {
      evento.preventDefault();
      avisar("");
      var ok = await enviar("/lab/notavel/notas", new FormData(form), null);
      if (ok) { fecharModal(); form.reset(); }
    });
  }

  if (modal) {
    modal.addEventListener("click", function (e) { if (e.target === modal) fecharModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal && !modal.hidden) fecharModal();
    });
  }

  // Definidas nas Tasks 10 e 11; declaradas aqui para `aoTrocar` existir
  // desde já sem referência solta.
  function animarReacao() {}
  function aplicarModoApp() {}
})();
```

- [ ] **Step 7: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel.py tests/lab/test_notavel_tela.py -q`
Expected: PASS.

- [ ] **Step 8: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1607 passed, zero falha.

- [ ] **Step 9: Commit**

```bash
git add app/templates/lab/notavel app/static/lab/notavel.js app/static/lab/notavel.css app/lab/notavel.py app/lab/rotas.py tests/lab
git commit -m "Notavel: emissao em tres passos e a recusa desenhada na linha do despacho"
```

---

### Task 10: Motion em três camadas

Chegada orquestrada, reação com causa e um pulso só, amarrado. Nada além disso: painel que se mexe sozinho é protetor de tela.

**Files:**
- Modify: `app/static/lab/notavel.js` (as funções `animarChegada`, `animarReacao`, `dispararPulso`)
- Modify: `app/static/lab/notavel.css` (o traço da linha e o realce do pulso)
- Test: `tests/lab/test_notavel_tela.py`

**Interfaces:**
- Consumes: `[data-valor]`, `[data-regiao]`, `[data-movimento]`, `.nt-kpi-linha polyline` (Task 8); `trocarFragmento`, `menosMovimento` (Task 9); rota `POST /lab/notavel/pulso` (Task 6).
- Produces: `animarChegada()`, `animarReacao(shell)`, `dispararPulso()`, `contarAte(elemento, centavos, duracao)`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/lab/test_notavel_tela.py`:

```python
# ----------------------------------------------------------- motion ----

def test_a_chegada_conta_ate_o_valor_que_ja_esta_no_html():
    """§4: os valores finais vêm renderizados pelo servidor e a chegada
    anima do zero ATÉ eles. O contrário deixa a tela piscar vazia enquanto
    o JavaScript busca dados, e em trinta segundos de julgamento essa
    piscada é metade da primeira impressão."""
    js = JS.read_text(encoding="utf-8")
    assert "data-valor" in js
    assert "contarAte" in js
    assert "requestAnimationFrame" in js


def test_a_chegada_e_o_pulso_somem_para_quem_pediu_menos_movimento():
    js = JS.read_text(encoding="utf-8")
    trecho = js[js.index("function animarChegada"):]
    assert "menosMovimento()" in trecho
    trecho_pulso = js[js.index("function dispararPulso"):]
    assert "menosMovimento()" in trecho_pulso


def test_o_pulso_e_uma_escrita_no_servidor_e_nao_uma_animacao():
    """§4: o pulso quita um recebível de verdade. O número desce porque o
    dado mudou, não porque o JavaScript mentiu por dois segundos."""
    js = JS.read_text(encoding="utf-8")
    assert "/lab/notavel/pulso" in js


def test_existe_um_pulso_so_e_nao_uma_sequencia():
    """"Um, não uma sequência." Um `setInterval` aqui seria protetor de
    tela: o painel se mexendo sozinho para sempre."""
    js = JS.read_text(encoding="utf-8")
    trecho = js[js.index("function dispararPulso"):]
    assert "setInterval" not in trecho
    assert js.count("/lab/notavel/pulso") == 1


def test_a_linha_do_kpi_e_desenhada_por_stroke_e_nao_redesenhada():
    css = CSS.read_text(encoding="utf-8")
    assert "stroke-dasharray" in css
    assert "@keyframes nt-traco" in css


def test_o_realce_do_recebivel_quitado_existe():
    """O pulso precisa MOSTRAR o que fechou: a linha do recebimento entra
    realçada na lista de movimentos, senão o número desceu e ninguém sabe
    por quê."""
    js = JS.read_text(encoding="utf-8")
    assert "pago-" in js
    css = CSS.read_text(encoding="utf-8")
    assert "nt-quitado" in css
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel_tela.py -q -k "motion or chegada or pulso or linha or realce"`
Expected: FAIL, `ValueError: substring not found` ao procurar `function animarChegada`.

- [ ] **Step 3: As três camadas, em `notavel.js`**

Troque as duas funções vazias do fim do arquivo por estas, e chame `animarChegada()` no fim do módulo:

```javascript
  // ==================================================== motion (§4) ====
  //
  // Três camadas, e só três. Painel que se mexe sozinho é protetor de
  // tela: o que se move, se move porque o visitante fez algo, ou porque a
  // página acabou de chegar.

  var DURACAO_CONTAGEM = 900;
  var ATRASO_ENTRE_REGIOES = 90;
  var ATRASO_DO_PULSO = 5200;

  function formatarReais(centavos) {
    // Mesma regra de `app/services/formato.py`: milhar com ponto, decimal
    // com vírgula. Só a CONTAGEM passa por aqui; o valor final que fica na
    // tela é sempre o texto que o servidor mandou, restaurado no fim.
    var sinal = centavos < 0 ? "-" : "";
    var absoluto = Math.abs(Math.round(centavos));
    var inteiro = Math.floor(absoluto / 100);
    var resto = absoluto % 100;
    var milhar = String(inteiro).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return "R$ " + sinal + milhar + "," + (resto < 10 ? "0" : "") + resto;
  }

  function contarAte(elemento, centavos, duracao) {
    // O texto final JÁ está no elemento (o servidor o renderizou). Ele é
    // guardado e restaurado no último quadro, para a contagem nunca poder
    // deixar na tela um número formatado por esta função em vez do que o
    // servidor mandou.
    var textoFinal = elemento.textContent;
    var comeco = null;
    function quadro(agora) {
      if (comeco === null) comeco = agora;
      var t = Math.min(1, (agora - comeco) / duracao);
      var suave = 1 - Math.pow(1 - t, 3);   // saída cúbica, a da casa
      if (t >= 1) { elemento.textContent = textoFinal; return; }
      elemento.textContent = formatarReais(centavos * suave);
      requestAnimationFrame(quadro);
    }
    requestAnimationFrame(quadro);
  }

  // ---------------------------------------- camada 1: chegada ----------
  function animarChegada() {
    var shell = document.getElementById("nt-shell");
    if (!shell) return;
    if (menosMovimento()) return;   // e a tela já está inteira e correta

    shell.querySelectorAll("[data-regiao]").forEach(function (regiao, i) {
      regiao.style.animationDelay = (i * ATRASO_ENTRE_REGIOES) + "ms";
    });
    shell.querySelectorAll("[data-valor]").forEach(function (elemento) {
      contarAte(elemento, Number(elemento.getAttribute("data-valor")),
                DURACAO_CONTAGEM);
    });
    var linha = shell.querySelector(".nt-kpi-linha polyline");
    if (linha && linha.getTotalLength) {
      var comprimento = linha.getTotalLength();
      linha.style.setProperty("--nt-traco", comprimento);
      linha.classList.add("nt-desenhando");
    }
    window.setTimeout(dispararPulso, ATRASO_DO_PULSO);
  }

  // ---------------------------------------- camada 2: reação -----------
  function animarReacao(shell) {
    // Depois de uma troca de fragmento, os números já estão certos no
    // HTML: a contagem aqui é curta e serve só para o olho seguir a
    // mudança. Quem pediu menos movimento vê o valor novo direto.
    if (!shell || menosMovimento()) return;
    shell.querySelectorAll("[data-valor]").forEach(function (elemento) {
      contarAte(elemento, Number(elemento.getAttribute("data-valor")), 420);
    });
  }

  // ---------------------------------------- camada 3: o pulso ----------
  async function dispararPulso() {
    // UM evento, e amarrado: um pagamento compensa e QUITA um recebível
    // que está visível na tela. Escrita de verdade no servidor, não
    // animação: o número desce porque o dado mudou.
    //
    // Sem laço e sem repetição. "Um, não uma sequência."
    if (menosMovimento()) return;
    var resposta;
    try {
      resposta = await fetch("/lab/notavel/pulso", { method: "POST" });
    } catch (e) { return; }        // sem rede, o painel fica como está
    if (!resposta.ok) return;
    trocarFragmento(await resposta.text());
    var quitado = document.querySelector('[data-movimento^="pago-"]');
    if (quitado) {
      quitado.classList.add("nt-quitado");
      mostrarToast("Um recebimento compensou. O saldo em conta subiu.");
    }
  }

  animarChegada();
})();
```

Tire a declaração vazia `function animarReacao() {}` do fim do arquivo, que agora tem corpo. **Deixe `function aplicarModoApp() {}` como está**: ela só ganha corpo na Task 11, e `aoTrocar` a chama desde a Task 9. Declaração de função em JavaScript é içada, então a ordem no arquivo não importa.

- [ ] **Step 4: O traço e o realce, em `notavel.css`**

Acrescente à seção de piso, fora de qualquer `@supports`:

```css
/* O traço da linha do KPI: ela JÁ está desenhada no HTML (o servidor
   calculou os pontos). Isto só esconde o traço e o revela, então sem
   JavaScript a linha aparece inteira e correta. */
@keyframes nt-traco {
  from { stroke-dashoffset: var(--nt-traco, 240); }
  to   { stroke-dashoffset: 0; }
}
.lab-demo.demo-notavel .nt-kpi-linha polyline.nt-desenhando {
  stroke-dasharray: var(--nt-traco, 240);
  animation: nt-traco 1.1s cubic-bezier(.2,.75,.3,1) both;
}

/* O recebível que o pulso quitou. Halo contido, uma vez só. */
.lab-demo.demo-notavel .nt-movimento.nt-quitado {
  animation: nt-pulso 1.4s cubic-bezier(.2,.75,.3,1) 1;
  background: var(--marca-positivo-fundo);
  border-radius: 6px;
}

@media (prefers-reduced-motion: reduce) {
  .lab-demo.demo-notavel .nt-kpi-linha polyline.nt-desenhando,
  .lab-demo.demo-notavel .nt-movimento.nt-quitado { animation: none !important; }
}
```

- [ ] **Step 5: Rodar os testes da task**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel_tela.py -q`
Expected: PASS.

- [ ] **Step 6: Conferir no navegador**

Abra `http://127.0.0.1:8000/lab/notavel` com o servidor local e confira, nesta ordem:

1. os KPIs contam do zero e param no valor certo, em cerca de um segundo;
2. a linha do KPI se desenha uma vez;
3. as regiões entram escalonadas e a tela FICA QUIETA depois;
4. por volta de cinco segundos, um recebimento compensa: o "a receber" desce, a conta corrente sobe e a linha nova entra realçada;
5. com `prefers-reduced-motion: reduce` ligado no sistema, nada disso acontece e o painel aparece inteiro e correto;
6. com o JavaScript desligado, o painel aparece inteiro e correto, sem contagem e sem pulso.

O item 6 é o que a §4 exige e é o único que nenhum teste automático deste plano cobre.

- [ ] **Step 7: Rodar a suíte inteira e commitar**

Run: `./.venv/bin/python -m pytest`
Expected: 1613 passed, zero falha.

```bash
git add app/static/lab/notavel.js app/static/lab/notavel.css tests/lab/test_notavel_tela.py
git commit -m "Notavel: chegada orquestrada, reacao com causa e um pulso amarrado"
```

---

### Task 11: Modo aplicativo no celular

Foco é o desktop, onde o painel inteiro cabe numa tela e o motion tem espaço. No celular, a mesma decisão já tomada no Admita: cara de aplicativo, navegação inferior, uma região por vez, e os dois fluxos que valem no dedo.

**Files:**
- Modify: `app/static/lab/notavel.js` (`aplicarModoApp`)
- Modify: `app/static/lab/notavel.css`
- Modify: `app/templates/lab/notavel/_shell.html` (a barra de abas)
- Test: `tests/lab/test_notavel_tela.py`

**Interfaces:**
- Consumes: `[data-regiao]` (Task 8); `aoTrocar` (Task 9).
- Produces: `aplicarModoApp()`, `modoApp()`, o atributo `data-regiao-ativa` no `#nt-shell`, a barra `.nt-abas`.

- [ ] **Step 1: Escrever os testes que falham**

```python
# ------------------------------------------------- modo aplicativo ----

def test_o_shell_tem_a_barra_de_abas_do_celular(db):
    """§9: no celular, cara de aplicativo, com navegação inferior. As abas
    existem no HTML sempre e o CSS as esconde no desktop, para a troca de
    fragmento não precisar recriá-las."""
    html = _html(db)
    assert 'class="nt-abas"' in html
    assert 'data-aba="despachos"' in html
    assert 'data-aba="movimentos"' in html


def test_o_js_usa_o_mesmo_corte_de_largura_do_admita():
    """860px é o corte que o Admita já usa (`modoApp()` em admita.js). Dois
    cortes diferentes fariam as duas demos virarem aplicativo em larguras
    diferentes na mesma sessão de quem está avaliando."""
    js = JS.read_text(encoding="utf-8")
    assert "(max-width: 860px)" in js
    admita = (RAIZ_LAB / "admita.js").read_text(encoding="utf-8")
    assert "(max-width: 860px)" in admita


def test_o_js_mostra_uma_regiao_por_vez_no_celular():
    js = JS.read_text(encoding="utf-8")
    assert "data-regiao-ativa" in js
    assert "modoApp" in js


def test_os_dois_fluxos_que_valem_no_celular_continuam_alcancaveis(db):
    """§9: emitir nota e aprovar despacho. As duas ações vivem em regiões
    que a barra de abas alcança."""
    html = _html(db)
    assert 'data-acao="abrir-emissao"' in html
    assert 'data-acao="aprovar"' in html


def test_o_css_tem_a_faixa_de_celular_e_esconde_as_abas_no_desktop():
    css = CSS.read_text(encoding="utf-8")
    assert "@media (max-width: 860px)" in css
    assert ".nt-abas" in css
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_notavel_tela.py -q -k "aba or celular or regiao_por_vez or largura"`
Expected: FAIL, `nt-abas` ausente.

- [ ] **Step 3: A barra de abas, no fim de `_shell.html`**

Dentro de `.nt-shell`, depois de `.nt-grade`:

```html
  {# Navegação inferior do modo aplicativo (§9). Existe no HTML SEMPRE e o
     CSS a esconde no desktop: assim a troca de fragmento não precisa
     recriá-la, e a região ativa é reaplicada por `aplicarModoApp` depois
     de cada swap. #}
  <nav class="nt-abas" aria-label="Regiões do painel">
    <button type="button" data-aba="saldos">
      <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-carteira"/></svg>
      Saldos
    </button>
    <button type="button" data-aba="despachos">
      <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-enviar"/></svg>
      Despachos
    </button>
    <button type="button" data-aba="movimentos">
      <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-recibo"/></svg>
      Movimentos
    </button>
    <button type="button" data-aba="cambio">
      <svg class="icone" aria-hidden="true"><use href="/static/lab/icones/notavel.svg#i-moeda"/></svg>
      Câmbio
    </button>
  </nav>
```

- [ ] **Step 4: `aplicarModoApp`, em `notavel.js`**

Troque a função vazia por:

```javascript
  // =============================================== modo aplicativo (§9) ==
  //
  // 860px é o MESMO corte do Admita (`modoApp()` em admita.js). Dois
  // cortes diferentes fariam as duas demos virarem aplicativo em larguras
  // diferentes na mesma sessão de quem está avaliando, e essa incoerência
  // aparece.
  var REGIAO_PADRAO = "despachos";   // onde o visitante AGE

  function modoApp() {
    return window.matchMedia("(max-width: 860px)").matches;
  }

  function aplicarModoApp() {
    var shell = document.getElementById("nt-shell");
    if (!shell) return;
    if (!modoApp()) {
      shell.removeAttribute("data-regiao-ativa");
      return;
    }
    var ativa = estado.regiaoAtiva || REGIAO_PADRAO;
    shell.setAttribute("data-regiao-ativa", ativa);
    shell.querySelectorAll("[data-aba]").forEach(function (botao) {
      botao.classList.toggle("ativa", botao.getAttribute("data-aba") === ativa);
    });
  }

  app.addEventListener("click", function (evento) {
    var aba = evento.target.closest("[data-aba]");
    if (!aba) return;
    estado.regiaoAtiva = aba.getAttribute("data-aba");
    aplicarModoApp();
  });

  window.addEventListener("resize", aplicarModoApp);
  aplicarModoApp();
```

E acrescente `regiaoAtiva: null` ao objeto `estado` no topo do arquivo.

- [ ] **Step 5: O CSS do modo aplicativo**

```css
/* ------------------------------------------------- modo aplicativo --- */
/* Desktop: as abas não existem visualmente. */
.lab-demo.demo-notavel .nt-abas { display: none; }

@media (max-width: 860px) {
  .lab-demo.demo-notavel .nt-shell { grid-template-rows: auto 1fr auto; }
  .lab-demo.demo-notavel .nt-grade { grid-template-columns: 1fr; }

  /* Uma região por vez. O cabeçalho e o KPI ficam sempre: são o contexto
     que faz as outras regiões significarem alguma coisa. */
  .lab-demo.demo-notavel .nt-grade > [data-regiao] { display: none; }
  .lab-demo.demo-notavel .nt-kpi { display: block; grid-column: 1 / -1; grid-row: auto; }
  .lab-demo.demo-notavel [data-regiao-ativa="saldos"] .nt-saldos,
  .lab-demo.demo-notavel [data-regiao-ativa="despachos"] .nt-despachos,
  .lab-demo.demo-notavel [data-regiao-ativa="movimentos"] .nt-movimentos,
  .lab-demo.demo-notavel [data-regiao-ativa="cambio"] .nt-cambio { display: block; }

  .lab-demo.demo-notavel .nt-saldos { grid-template-columns: repeat(2, 1fr); }

  /* A barra de comando encolhe para caber: some o que é detalhe e fica o
     que identifica a empresa. */
  .lab-demo.demo-notavel .nt-comando-fiscal,
  .lab-demo.demo-notavel .nt-comando-usuario,
  .lab-demo.demo-notavel .nt-comando-palavra { display: none; }

  .lab-demo.demo-notavel .nt-abas {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 2px;
    padding: 6px 4px calc(6px + env(safe-area-inset-bottom, 0px));
    background: var(--marca-superficie);
    border-top: 1px solid var(--marca-borda);
  }
  .lab-demo.demo-notavel .nt-abas button {
    display: grid; justify-items: center; gap: 2px;
    padding: 6px 0; border: 0; background: none;
    color: var(--marca-texto-suave); font-size: .68rem;
  }
  .lab-demo.demo-notavel .nt-abas button.ativa { color: var(--marca-primaria); }

  /* Alvo de toque de 44px nos botões da fila: no dedo, botão de 28px é
     recusa disfarçada de erro do visitante. */
  .lab-demo.demo-notavel .nt-despacho-acoes .botao { min-height: 44px; }
}
```

- [ ] **Step 6: Conferir no navegador**

Com o painel aberto, reduza a janela para 375px de largura e confira: a barra de abas aparece embaixo, uma região por vez, o cabeçalho encolhe, os botões da fila dão para acertar com o polegar, e a página continua sem barra de rolagem.

- [ ] **Step 7: Rodar a suíte inteira e commitar**

Run: `./.venv/bin/python -m pytest`
Expected: 1618 passed, zero falha.

```bash
git add app/static/lab/notavel.js app/static/lab/notavel.css app/templates/lab/notavel/_shell.html tests/lab/test_notavel_tela.py
git commit -m "Notavel: modo aplicativo no celular, com navegacao inferior"
```

---

### Task 12: Abrir o Notável

Até aqui o painel funciona mas ninguém chega nele: a vitrine mostra "em desenvolvimento" e o cabeçalho mostra "em breve". Esta task abre a porta, e mexe nos testes que travam o estado antigo.

Esses testes não estão errados: eles foram escritos para garantir que ninguém prometesse uma demo que não existia. Agora ela existe, e o que eles protegem passou a ser o contrário.

**Files:**
- Modify: `app/templates/lab/vitrine.html`
- Modify: `app/templates/_cabecalho.html`
- Modify: `app/templates/lab/_base_demo.html` (descrição e capa do Notável)
- Test: `tests/lab/test_vitrine.py`, `tests/lab/test_base_demo.py`

**Interfaces:**
- Consumes: a rota `GET /lab/notavel` (Task 6).
- Produces: nada de código; o Notável passa a ser alcançável.

- [ ] **Step 1: Atualizar os testes que travam o estado antigo**

Em `tests/lab/test_vitrine.py`, `test_vitrine_abre_so_o_que_esta_pronto` vira:

```python
def test_vitrine_abre_o_que_esta_pronto_e_avisa_o_que_nao_esta(client):
    """No lançamento só o Admita abria. Com o corte 1 do Notável no ar, são
    dois sistemas clicáveis, e só a Caderneta continua como aviso: prometer
    uma demo que não existe é pior do que não mostrar o sistema."""
    r = client.get("/lab")
    assert 'href="/lab/admita"' in r.text
    assert 'href="/lab/notavel"' in r.text
    assert 'href="/lab/caderneta"' not in r.text
    assert r.text.count("lab-vt-card-breve") == 1
    assert r.text.count("em desenvolvimento") >= 1
```

Em `tests/lab/test_base_demo.py`, no teste do cabeçalho:

```python
    assert 'href="/lab/admita"' in html
    assert 'href="/lab/notavel"' in html
    # A Caderneta ainda não abriu: aparece como aviso, não como link, para
    # ninguém cair numa tela vazia a partir do cabeçalho.
    assert 'href="/lab/caderneta"' not in html
    assert html.count("nav-link-breve") == 1
```

E acrescente um teste novo ao mesmo arquivo:

```python
def test_a_descricao_do_notavel_descreve_o_que_ele_faz_hoje(db=None):
    """A `descricao` é o que aparece no preview de quem recebe o link.
    Promessa em cartão de compartilhamento é a pior espécie, porque a
    pessoa só descobre depois de clicar. A antiga dizia "em
    desenvolvimento" e prometia conciliação, que é corte 2."""
    html = _render("notavel")
    assert "Em breve" not in html
    assert "em desenvolvimento" not in html.lower()
    assert "conciliação" not in html.lower()
    assert "nota fiscal" in html.lower()
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `./.venv/bin/python -m pytest tests/lab/test_vitrine.py tests/lab/test_base_demo.py -q`
Expected: FAIL, `assert 'href="/lab/notavel"' in r.text`.

- [ ] **Step 3: O cabeçalho**

Em `app/templates/_cabecalho.html`, troque a linha do Notável:

```html
    <a class="nav-link {{ 'active' if demo is defined and demo == 'notavel' }}" href="/lab/notavel">Notável</a>
    <span class="nav-link nav-link-breve" aria-disabled="true">Caderneta <i>em breve</i></span>
```

- [ ] **Step 4: A descrição e a capa, em `_base_demo.html`**

No dicionário `_DEMOS`, o Notável passa a descrever o que ele faz HOJE:

```python
  "notavel": {
    "nome": "Notável",
    "tagline": "A nota sai, o dinheiro entra, você vê tudo.",
    "css": "notavel.css",
    "og": "/static/lab/img/og-notavel.jpg",
    "descricao": "Painel financeiro que você usa agora, sem cadastro: emita nota fiscal de demonstração com o imposto explicado, aprove ou recuse pagamentos da fila, e acompanhe saldos, câmbio do dia e os últimos movimentos.",
  },
```

**Se `og-notavel.jpg` ainda não existir**, deixe a chave `"og"` FORA do dicionário: o template já cai no cartão padrão do site quando ela falta, e um preview quebrado é pior do que um preview genérico. A capa é peça de arte e não entra num plano de código.

- [ ] **Step 5: A vitrine**

Em `app/templates/lab/vitrine.html`, o cartão do Notável vira um `<a href="/lab/notavel">`, no mesmo formato do cartão do Admita:

- troque `<div class="lab-vt-card lab-vt-card-breve" data-reveal aria-label="Notável. Sistema em desenvolvimento, ainda sem demonstração.">` por `<a class="lab-vt-card" data-reveal href="/lab/notavel" aria-label="Notável. Abrir a demonstração do painel financeiro.">`, e o `</div>` de fechamento por `</a>`;
- troque `<span class="lab-vt-ver lab-vt-ver-breve" aria-hidden="true"><i class="lab-vt-ponto"></i>em desenvolvimento</span>` por `<span class="lab-vt-ver" aria-hidden="true">ver demonstração <i>→︎</i></span>`;
- na linha de tags, troque `<span class="lab-vt-estado lab-vt-estado-obra">` por `<span class="lab-vt-estado lab-vt-estado-ativo">`, com o texto "sistema ativo";
- troque a tag "Conciliação" por "Impostos": conciliação é corte 2, e tag é promessa igual à descrição;
- o `<em>` da linha de aplicativo passa a ser "Nota fiscal, despachos e saldo no mesmo lugar."

O bloco comentado da captura de tela (`vitrine-notavel.webp`) fica como está: a arte é da mesma leva da capa OG e não entra aqui.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `./.venv/bin/python -m pytest`
Expected: 1619 passed, zero falha.

Se `test_vitrine_sem_travessao_no_html_renderizado` falhar, alguma copy nova entrou com travessão: troque por vírgula ou dois-pontos.

- [ ] **Step 7: Commit**

```bash
git add app/templates/lab/vitrine.html app/templates/_cabecalho.html app/templates/lab/_base_demo.html tests/lab
git commit -m "Notavel: o painel abre na vitrine e no cabecalho do Lab"
```

---

## Depois do plano

O corte 1 está entregue quando os seis itens da §14 da spec forem verdade:

- [ ] o painel abre em menos de um segundo e a chegada termina em cerca de dois;
- [ ] emitir uma nota move o KPI e a lista, e o PDF sai correto, com numeração sequencial por sandbox;
- [ ] aprovar um despacho move o saldo e registra na auditoria;
- [ ] o câmbio aparece com data, inclusive no sábado;
- [ ] `prefers-reduced-motion` desliga chegada e pulso;
- [ ] a suíte cobre ciclo da nota, numeração, despachos, queda do câmbio, isolamento entre sandboxes e os tetos;
- [ ] nada no Lab importa do Nodal.

O último item tem um teste que já existe (`tests/test_produto_opcional.py`): rode a suíte com a pasta `app/nodal/` fora do caminho antes de fechar a entrega.

**Antes de subir para o servidor:** o deploy passa por `deploy/atualizar.sh`, que faz o backup. O VPS não tem backup pago, e o cron dele já falhou calado uma vez.

**O corte 2** (§12 da spec) é a próxima conversa, não parte deste plano: calculadora do Simples com CNAE e Fator R, categorização de extrato por IA, aba de folha e o caso de rescisão. As tabelas do Anexo III e V, o Fator R e o guardião de IA já estão de pé para ele.
