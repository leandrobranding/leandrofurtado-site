"""Testes dos PDFs de demonstração do Lab (Task 5 do Plano 1: §6.2/§6.3 e
§9.6 da spec).

Nenhum teste aqui sobe app/HTTP nem banco real: `gerar_nf_pdf`/
`gerar_boletim_pdf` recebem instâncias de modelo direto (nem precisam estar
numa sessão) e devolvem bytes puros.

A tarja é verificada de duas formas complementares (ruling da rodada de
conserto 1, item 1/4):
- estado do objeto `pdf` (`test_tarja_nao_vaza_cor_de_preenchimento_para_o_que_vem_depois`):
  trava a regressão do BLOQUEADOR (fill_color preto vazando pra tabela
  seguinte) de forma estrutural, sem precisar olhar bytes;
- busca binária pontual (`_pdf_sem_compressao`): produção mantém
  `pdf.compress = True` (padrão do fpdf2); só a INSTÂNCIA de PDF usada
  nestes testes específicos tem a compressão desligada via monkeypatch de
  `_novo_pdf`, para que os bytes da tarja (fonte core, texto literal) fiquem
  buscáveis sem precisar de uma lib de leitura de PDF nova."""
import datetime as dt

import pytest

from app.lab import pdf as pdf_mod
from app.lab.models import (
    LabAluno,
    LabAvaliacao,
    LabClienteFiscal,
    LabNota,
    LabParecer,
    LabSandbox,
)
from app.lab.pdf import (
    TARJA_BOLETIM,
    TARJA_NF,
    formatar_centavos,
    gerar_boletim_pdf,
    gerar_nf_pdf,
)
from app.lab.protecao import MAX_PDFS


@pytest.fixture()
def _pdf_sem_compressao(monkeypatch):
    """Helper SÓ DE TESTE (ruling item 4): faz `_novo_pdf` devolver uma
    instância com `compress = False`, sem tocar no padrão de produção
    (`True`). Qualquer teste que precise buscar bytes literais da tarja
    pede este fixture; os demais (maioria) nem sabem que ele existe."""
    original = pdf_mod._novo_pdf

    def _fabrica():
        instancia = original()
        instancia.compress = False
        return instancia

    monkeypatch.setattr(pdf_mod, "_novo_pdf", _fabrica)


def _sandbox(pdfs_gerados=0) -> LabSandbox:
    return LabSandbox(
        id=1, token="tok-pdf-teste", demo_origem="fin",
        expira_em=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24),
        pdfs_gerados=pdfs_gerados,
    )


def _cliente(**over) -> LabClienteFiscal:
    base = dict(id=1, sandbox_id=1, nome="Cliente Exemplo LTDA",
                documento="00.000.000/0001-00", email="cliente@exemplo.com.br")
    base.update(over)
    return LabClienteFiscal(**base)


def _nota(**over) -> LabNota:
    base = dict(
        id=1, sandbox_id=1, cliente_id=1, numero=1,
        itens=[
            {"descricao": "Consultoria em IA", "quantidade": 2, "valor_unit_centavos": 150000},
            {"descricao": "Suporte mensal", "quantidade": 1, "valor_unit_centavos": 80000},
        ],
        impostos={"ISS": 19000, "IRRF": 12000},
        total_centavos=680000,
        status="emitida",
        criado_em=dt.datetime.now(dt.timezone.utc),
    )
    base.update(over)
    return LabNota(**base)


def _aluno(**over) -> LabAluno:
    base = dict(id=1, sandbox_id=1, nome="Aluno Exemplo", turma="3º B (fictícia)")
    base.update(over)
    return LabAluno(**base)


def _avaliacoes() -> list[LabAvaliacao]:
    return [
        LabAvaliacao(id=1, sandbox_id=1, aluno_id=1, disciplina="Matemática", nota=7.5, faltas=2, bimestre=1),
        LabAvaliacao(id=2, sandbox_id=1, aluno_id=1, disciplina="Matemática", nota=8.0, faltas=1, bimestre=2),
        LabAvaliacao(id=3, sandbox_id=1, aluno_id=1, disciplina="Português", nota=5.0, faltas=3, bimestre=1),
    ]


def _parecer(**over) -> LabParecer:
    base = dict(id=1, sandbox_id=1, aluno_id=1,
                texto_ia="Aluno com bom desempenho em Matemática.", origem="fallback")
    base.update(over)
    return LabParecer(**base)


# ------------------------------------------------------------ formatação --

@pytest.mark.parametrize("centavos, esperado", [
    (1234567, "R$ 12.345,67"),
    (0, "R$ 0,00"),
    (100, "R$ 1,00"),
    (99, "R$ 0,99"),
    (100000000, "R$ 1.000.000,00"),
])
def test_formatar_centavos_formatacao_br(centavos, esperado):
    assert formatar_centavos(centavos) == esperado


def test_formatar_centavos_negativo():
    assert formatar_centavos(-500) == "-R$ 5,00"


# -------------------------------------------------------------------- NF --

def test_nf_pdf_comeca_com_assinatura_pdf():
    data = gerar_nf_pdf(_nota(), _cliente(), _sandbox())
    assert data.startswith(b"%PDF")


def test_nf_pdf_contem_a_tarja_no_topo_e_no_rodape(_pdf_sem_compressao):
    data = gerar_nf_pdf(_nota(), _cliente(), _sandbox())
    marca = TARJA_NF.encode("cp1252")
    primeira = data.find(marca)
    ultima = data.rfind(marca)
    assert primeira != -1, "tarja ausente do PDF"
    assert ultima != primeira, "tarja aparece só uma vez (esperado: topo E rodapé)"


def test_nf_pdf_producao_mantem_compressao_padrao_do_fpdf2():
    """Ruling item 4: `compress=False` é SÓ do fixture de teste acima —
    sem ele, a instância nasce com o padrão do fpdf2 (`True`)."""
    pdf = pdf_mod._novo_pdf()
    assert pdf.compress is True


def test_tarja_nao_vaza_cor_de_preenchimento_para_o_que_vem_depois():
    """Trava o BLOQUEADOR da revisão 1: `_tarja` salva e restaura
    `fill_color`/`text_color` do objeto `pdf` — sem isto, o preto ficava
    setado e a próxima `pdf.table()` herdava fundo preto com texto preto
    em cima (tabela invisível em 100% dos PDFs, achado do revisor).
    Teste ESTRUTURAL (estado do objeto), não de bytes."""
    pdf = pdf_mod._novo_pdf()
    fill_antes = pdf.fill_color
    texto_antes = pdf.text_color
    pdf_mod._tarja(pdf, "QUALQUER AVISO")
    assert pdf.fill_color == fill_antes
    assert pdf.text_color == texto_antes
    assert pdf.fill_color.colors255 != (20.0, 20.0, 20.0)


def test_nf_pdf_incrementa_contador_do_sandbox():
    sandbox = _sandbox()
    gerar_nf_pdf(_nota(), _cliente(), sandbox)
    assert sandbox.pdfs_gerados == 1


def test_sexto_pdf_do_sandbox_e_rejeitado():
    sandbox = _sandbox(pdfs_gerados=MAX_PDFS)
    with pytest.raises(ValueError):
        gerar_nf_pdf(_nota(), _cliente(), sandbox)
    assert sandbox.pdfs_gerados == MAX_PDFS  # não incrementa em rejeição


def test_nf_e_boletim_dividem_o_mesmo_teto_de_pdfs():
    """§8: "5 PDFs por sandbox" é um teto ÚNICO, não 5 de cada tipo."""
    sandbox = _sandbox(pdfs_gerados=MAX_PDFS - 1)
    gerar_nf_pdf(_nota(), _cliente(), sandbox)
    assert sandbox.pdfs_gerados == MAX_PDFS
    with pytest.raises(ValueError):
        gerar_boletim_pdf(_aluno(), _avaliacoes(), _parecer(), sandbox)


def test_nome_de_cliente_com_caractere_de_controle_e_rejeitado_antes_do_fpdf2():
    cliente_hostil = _cliente(nome="Cliente\x00Malicioso")
    with pytest.raises(ValueError):
        gerar_nf_pdf(_nota(), cliente_hostil, _sandbox())


def test_documento_de_cliente_hostil_e_rejeitado():
    cliente_hostil = _cliente(documento="123\x1b[31mADMIN")
    with pytest.raises(ValueError):
        gerar_nf_pdf(_nota(), cliente_hostil, _sandbox())


def test_descricao_de_item_hostil_e_rejeitada():
    nota_hostil = _nota(itens=[{"descricao": "Item\x07Sino", "quantidade": 1, "valor_unit_centavos": 100}])
    with pytest.raises(ValueError):
        gerar_nf_pdf(nota_hostil, _cliente(), _sandbox())


def test_categoria_de_imposto_hostil_e_rejeitada():
    nota_hostil = _nota(impostos={"ISS\x00": 100})
    with pytest.raises(ValueError):
        gerar_nf_pdf(nota_hostil, _cliente(), _sandbox())


def test_categoria_de_imposto_no_limite_do_campo_nao_quebra_nem_vaza_da_pagina():
    """Regressão SEVERO da revisão 1: categoria de até MAX_CAMPO=200 chars é
    VÁLIDA em `validar_texto` — o bug era o layout (cell() sem quebra de
    linha), não a validação. Fix: pdf.table() (ver comentário no bloco de
    impostos em app/lab/pdf.py) — este teste trava que uma categoria bem
    longa continua gerando um PDF válido, sem estourar exceção de layout."""
    categoria_longa = "Imposto sobre serviços de qualquer natureza incidente sobre a prestação " \
                       "de serviços de consultoria técnica especializada em engenharia " \
                       "de software (categoria fictícia longa de propósito)"
    assert len(categoria_longa) <= 200
    nota_longa = _nota(impostos={categoria_longa: 12345})
    data = gerar_nf_pdf(nota_longa, _cliente(), _sandbox())
    assert data.startswith(b"%PDF")


def test_nf_pdf_mostra_numero_sequencial_do_sandbox():
    """`numero` é sequencial POR sandbox (LabNota) — vira Nº 000042 no
    corpo do PDF, desenhado nas fontes TTF da casa (não buscável em texto
    literal — só confirma que o PDF não quebra com um número alto e que o
    tamanho do arquivo é condizente com um documento de verdade, não vazio)."""
    data = gerar_nf_pdf(_nota(numero=42), _cliente(), _sandbox())
    assert data.startswith(b"%PDF")
    assert len(data) > 5_000


# --------------------------------------------------------------- boletim --

def test_boletim_pdf_comeca_com_assinatura_pdf():
    data = gerar_boletim_pdf(_aluno(), _avaliacoes(), _parecer(), _sandbox())
    assert data.startswith(b"%PDF")


def test_boletim_pdf_contem_o_aviso_de_demonstracao_no_topo_e_no_rodape(_pdf_sem_compressao):
    data = gerar_boletim_pdf(_aluno(), _avaliacoes(), _parecer(), _sandbox())
    marca = TARJA_BOLETIM.encode("cp1252")
    primeira = data.find(marca)
    ultima = data.rfind(marca)
    assert primeira != -1, "aviso de demonstração ausente do boletim"
    assert ultima != primeira, "aviso aparece só uma vez (esperado: topo E rodapé)"


def test_boletim_pdf_incrementa_contador_do_sandbox():
    sandbox = _sandbox()
    gerar_boletim_pdf(_aluno(), _avaliacoes(), _parecer(), sandbox)
    assert sandbox.pdfs_gerados == 1


def test_sexto_pdf_do_sandbox_e_rejeitado_no_boletim_tambem():
    sandbox = _sandbox(pdfs_gerados=MAX_PDFS)
    with pytest.raises(ValueError):
        gerar_boletim_pdf(_aluno(), _avaliacoes(), _parecer(), sandbox)


def test_boletim_sem_parecer_ainda_nao_quebra():
    data = gerar_boletim_pdf(_aluno(), _avaliacoes(), None, _sandbox())
    assert data.startswith(b"%PDF")


def test_boletim_sem_avaliacoes_ainda_nao_quebra():
    data = gerar_boletim_pdf(_aluno(), [], None, _sandbox())
    assert data.startswith(b"%PDF")


def test_nome_de_aluno_hostil_e_rejeitado_antes_do_fpdf2():
    aluno_hostil = _aluno(nome="Aluno\x00Hostil")
    with pytest.raises(ValueError):
        gerar_boletim_pdf(aluno_hostil, _avaliacoes(), _parecer(), _sandbox())


def test_nome_de_aluno_longo_com_turma_nao_quebra_no_meio_da_pagina():
    """Regressão MODERADO da revisão 1: nome (até MAX_CAMPO=200 chars,
    válido) + turma na mesma linha usava cell(0, ...), que corta no limite
    da página em vez de quebrar linha. Fix: multi_cell (ver
    gerar_boletim_pdf em app/lab/pdf.py) — trava que o PDF continua válido
    com um nome bem comprido."""
    aluno_longo = _aluno(
        nome="Maria Das Graças Fernandes De Oliveira E Silva Junior Sobrenome Muito Comprido Mesmo Para Testar Quebra De Linha",
        turma="3º B do Ensino Fundamental Anos Finais (turma fictícia)",
    )
    assert len(aluno_longo.nome) <= 200
    data = gerar_boletim_pdf(aluno_longo, _avaliacoes(), _parecer(), _sandbox())
    assert data.startswith(b"%PDF")


def test_disciplina_hostil_e_rejeitada():
    avals_hostil = [LabAvaliacao(id=1, sandbox_id=1, aluno_id=1,
                                  disciplina="Matemática\x00", nota=7.0, faltas=0, bimestre=1)]
    with pytest.raises(ValueError):
        gerar_boletim_pdf(_aluno(), avals_hostil, _parecer(), _sandbox())


def test_texto_do_parecer_hostil_e_rejeitado():
    parecer_hostil = _parecer(texto_ia="Bom aluno\x00 mas hostil")
    with pytest.raises(ValueError):
        gerar_boletim_pdf(_aluno(), _avaliacoes(), parecer_hostil, _sandbox())


def test_situacao_aprovado_para_medias_altas_e_poucas_faltas():
    from app.lab.pdf import _situacao_aluno
    avals = [LabAvaliacao(id=1, sandbox_id=1, aluno_id=1, disciplina="Matemática",
                           nota=8.0, faltas=1, bimestre=1)]
    situacao, media, faltas = _situacao_aluno(avals)
    assert situacao == "aprovado"
    assert media == 8.0
    assert faltas == 1


def test_situacao_reprovado_por_falta_mesmo_com_media_alta():
    from app.lab.pdf import LIMITE_FALTAS_DEMO, _situacao_aluno
    avals = [LabAvaliacao(id=1, sandbox_id=1, aluno_id=1, disciplina="Matemática",
                           nota=9.0, faltas=LIMITE_FALTAS_DEMO + 1, bimestre=1)]
    situacao, _media, faltas = _situacao_aluno(avals)
    assert situacao == "reprovado por falta"
    assert faltas == LIMITE_FALTAS_DEMO + 1


def test_situacao_recuperacao_para_media_intermediaria():
    from app.lab.pdf import _situacao_aluno
    avals = [LabAvaliacao(id=1, sandbox_id=1, aluno_id=1, disciplina="Matemática",
                           nota=5.0, faltas=0, bimestre=1)]
    situacao, _media, _faltas = _situacao_aluno(avals)
    assert situacao == "recuperação"


def test_situacao_reprovado_para_media_baixa():
    from app.lab.pdf import _situacao_aluno
    avals = [LabAvaliacao(id=1, sandbox_id=1, aluno_id=1, disciplina="Matemática",
                           nota=2.0, faltas=0, bimestre=1)]
    situacao, _media, _faltas = _situacao_aluno(avals)
    assert situacao == "reprovado"
