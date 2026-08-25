"""Testes da Task 4 do Plano 2: esteira de admissão do Admita
(`app/lab/admita.py`, `app/lab/rotas.py`, `app/templates/lab/admita/*`).

Usa as fixtures de `tests/lab/conftest.py` (app de verdade + banco real
isolado por processo de teste) e se apoia no CENÁRIO SEMEADO por
`app/lab/seeds_demo.py::_semear_rh` (6 candidatos com nome e etapa
conhecidos) em vez de recriar candidatos do zero em todo teste — os nomes
usados abaixo (Adriana/Bruno/Camila/Diego/Elisa/Felipe) e seus estados de
partida são os documentados naquele módulo."""
import datetime as dt
import re

import pytest

from app.lab.models import LabAuditoria, LabCandidato, LabDocumentoStatus
from app.lab.protecao import MAX_REGISTROS_POR_DEMO
from app.lab.sandbox import COOKIE_NOME


def _entrar(client):
    r = client.get("/lab/admita")
    assert r.status_code == 200
    return r


def _candidato(db_session, nome):
    return db_session.query(LabCandidato).filter(LabCandidato.nome == nome).one()


def _docs(db_session, candidato_id):
    return (
        db_session.query(LabDocumentoStatus)
        .filter(LabDocumentoStatus.candidato_id == candidato_id)
        .all()
    )


# ------------------------------------------------------------- tela cheia --

def test_get_admita_renderiza_esteira_de_verdade_nao_mais_em_construcao(client):
    r = _entrar(client)
    assert "Em construção interna" not in r.text
    assert "Esteira de admissão" in r.text
    assert 'id="admita-shell"' in r.text
    assert 'id="admita-sidebar"' in r.text
    assert 'id="admita-board"' in r.text
    # os 5 nomes de etapa validados pelo estudo setorial (§6.1)
    for rotulo in ("Cadastro enviado", "Documentos", "Aprovação do RH",
                   "Aprovação do gestor", "Admitido"):
        assert rotulo in r.text


def test_get_admita_mostra_os_candidatos_semeados_nas_etapas_certas(client):
    r = _entrar(client)
    assert "Adriana Souza Lima" in r.text
    assert "Bruno Andrade Costa" in r.text
    assert "Camila Ferreira Dias" in r.text


def test_modal_nova_candidatura_presente_com_botoes_com_icone(client):
    r = _entrar(client)
    assert 'id="admita-modal-novo"' in r.text
    assert 'name="nome"' in r.text
    assert "<select" in r.text and 'name="cargo"' in r.text
    # todos os botões do modal têm <svg class="icone">
    bloco = r.text.split('id="admita-modal-novo"', 1)[1].split("</form>", 1)[0]
    assert bloco.count('<svg class="icone"') >= 2  # salvar + cancelar


# --------------------------------------------------- bug do dono: as setas --

def test_seta_esquerda_espelha_a_mesma_seta_da_direita_por_css_nunca_um_simbolo_proprio(client):
    """O bug reportado (seta da esquerda apontando para a direita) não pode
    voltar: a seta esquerda usa o MESMO símbolo `#i-seta-direita` do
    sprite, mirado pela classe `.icone-esq` (CSS `transform: scaleX(-1)`),
    nunca um `#i-seta-esquerda` que não existe no sprite."""
    r = _entrar(client)
    assert "icone-esq" in r.text
    import pathlib
    css = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "app" / "static" / "lab" / "admita.css"
    ).read_text(encoding="utf-8")
    assert re.search(r"\.icone-esq\s*\{[^}]*transform:\s*scaleX\(-1\)", css)


def _botao(html, aria_prefixo, nome):
    """Devolve a tag <button> inteira cujo aria-label é `<prefixo> <nome> ...`.

    Casar pelo aria-label é o que permite afirmar `disabled` no botão CERTO:
    procurar a string "disabled" no HTML da página passaria mesmo com a seta
    do candidato errado desabilitada."""
    padrao = r"<button[^>]*aria-label=\"" + aria_prefixo + " " + re.escape(nome) + r"[^\"]*\"[^>]*>"
    achado = re.search(padrao, html)
    if achado:
        return achado.group(0)
    # o atributo aria-label vem depois de `disabled` no template, então
    # procura também a forma "abre a tag, atributos, aria-label no fim"
    padrao2 = r"<button(?:(?!</button>).)*?" + re.escape(nome) + r"(?:(?!</button>).)*?>"
    achado2 = re.search(padrao2, html, re.S)
    return achado2.group(0) if achado2 else None


def test_seta_de_voltar_esta_desabilitada_na_primeira_etapa(client, db_session):
    """Diego está em "candidato", a primeira etapa: não há para onde voltar.

    O dono relatou este bug de olho na tela, então o teste afirma o atributo
    `disabled` na seta dele, e afirma que a MESMA seta de quem está no meio
    da esteira continua habilitada (senão "tudo desabilitado" passaria)."""
    _entrar(client)
    r = client.get("/lab/admita")

    seta_diego = _botao(r.text, "Voltar", "Diego Martins Rocha")
    assert seta_diego is not None, "seta de voltar do Diego não encontrada"
    assert "disabled" in seta_diego, seta_diego

    seta_adriana = _botao(r.text, "Voltar", "Adriana Souza Lima")
    assert seta_adriana is not None, "seta de voltar da Adriana não encontrada"
    assert "disabled" not in seta_adriana, seta_adriana


def test_seta_de_avancar_esta_desabilitada_na_ultima_etapa(client, db_session):
    """Camila já está admitida: a esteira acabou para ela."""
    _entrar(client)
    r = client.get("/lab/admita")

    seta_camila = _botao(r.text, "Avançar", "Camila Ferreira Dias")
    assert seta_camila is not None, "seta de avançar da Camila não encontrada"
    assert "disabled" in seta_camila, seta_camila

    seta_diego = _botao(r.text, "Avançar", "Diego Martins Rocha")
    assert seta_diego is not None
    assert "disabled" not in seta_diego, seta_diego


def test_seta_da_esquerda_usa_o_icone_espelhado_e_nao_o_da_direita_cru(client):
    """O bug original do dono: a seta de voltar apontava para a direita.

    O template reusa `#i-seta-direita` espelhado por CSS, então o que prova
    o conserto é a classe `icone-esq` DENTRO do botão de voltar."""
    _entrar(client)
    r = client.get("/lab/admita")
    botoes_voltar = re.findall(
        r"<button[^>]*data-mover=\"anterior\".*?</button>", r.text, re.S
    )
    assert botoes_voltar, "nenhum botão de voltar encontrado"
    for botao in botoes_voltar:
        assert "icone-esq" in botao, botao


# --------------------------------------------------- regras de bloqueio ----

def test_nao_avanca_de_documentos_sem_todos_os_itens_conferidos(client, db_session):
    _entrar(client)
    adriana = _candidato(db_session, "Adriana Souza Lima")
    assert adriana.etapa == "documentos"

    r = client.post(f"/lab/admita/candidatos/{adriana.id}/mover", data={"direcao": "proxima"})
    assert r.status_code == 409
    assert "documento" in r.json()["detail"].lower()

    db_session.refresh(adriana)
    assert adriana.etapa == "documentos"  # não avançou


def test_confere_todos_os_documentos_e_entao_avanca(client, db_session):
    _entrar(client)
    adriana = _candidato(db_session, "Adriana Souza Lima")
    pendente = next(d for d in _docs(db_session, adriana.id) if not d.conferido)

    r = client.post(
        f"/lab/admita/candidatos/{adriana.id}/documentos/{pendente.id}/alternar"
    )
    assert r.status_code == 200
    assert "Em construção interna" not in r.text

    r2 = client.post(f"/lab/admita/candidatos/{adriana.id}/mover", data={"direcao": "proxima"})
    assert r2.status_code == 200

    db_session.expire_all()
    adriana2 = _candidato(db_session, "Adriana Souza Lima")
    assert adriana2.etapa == "aprovacao_rh"


def test_nao_avanca_de_aprovacao_rh_sem_aprovar_rh_antes(client, db_session):
    _entrar(client)
    elisa = _candidato(db_session, "Elisa Tavares Nogueira")
    assert elisa.etapa == "aprovacao_rh"
    assert elisa.aprovado_rh is False

    r = client.post(f"/lab/admita/candidatos/{elisa.id}/mover", data={"direcao": "proxima"})
    assert r.status_code == 409
    assert "rh" in r.json()["detail"].lower()


def test_aprovar_rh_com_1_clique_avanca_para_aprovacao_do_gestor(client, db_session):
    _entrar(client)
    elisa = _candidato(db_session, "Elisa Tavares Nogueira")

    r = client.post(f"/lab/admita/candidatos/{elisa.id}/aprovar-rh")
    assert r.status_code == 200

    db_session.expire_all()
    elisa2 = _candidato(db_session, "Elisa Tavares Nogueira")
    assert elisa2.aprovado_rh is True
    assert elisa2.etapa == "aprovacao_gestor"


def test_aprovacao_do_gestor_exige_a_aprovacao_do_rh_antes(client, db_session):
    """A REGRA DE OURO do §6.1: "Aprovação do gestor exige a do RH antes" —
    forçamos o estado inconsistente direto no banco (aprovado_rh=False
    numa etapa de gestor) para provar que a rota BLOQUEIA mesmo assim, não
    confia só no fluxo normal da UI para nunca deixar isso acontecer."""
    _entrar(client)
    bruno = _candidato(db_session, "Bruno Andrade Costa")
    assert bruno.etapa == "aprovacao_gestor"
    bruno.aprovado_rh = False
    db_session.commit()

    r = client.post(f"/lab/admita/candidatos/{bruno.id}/aprovar-gestor")
    assert r.status_code == 409
    assert "rh" in r.json()["detail"].lower()


def test_aprovar_gestor_com_rh_ja_aprovado_admite_o_candidato(client, db_session):
    _entrar(client)
    bruno = _candidato(db_session, "Bruno Andrade Costa")
    assert bruno.aprovado_rh is True

    r = client.post(f"/lab/admita/candidatos/{bruno.id}/aprovar-gestor")
    assert r.status_code == 200

    db_session.expire_all()
    bruno2 = _candidato(db_session, "Bruno Andrade Costa")
    assert bruno2.aprovado_gestor is True
    assert bruno2.etapa == "admitido"


def test_nao_recua_antes_da_primeira_nem_avanca_depois_da_ultima(client, db_session):
    _entrar(client)
    diego = _candidato(db_session, "Diego Martins Rocha")
    assert diego.etapa == "candidato"
    r = client.post(f"/lab/admita/candidatos/{diego.id}/mover", data={"direcao": "anterior"})
    assert r.status_code == 409
    assert "primeira etapa" in r.json()["detail"].lower()

    camila = _candidato(db_session, "Camila Ferreira Dias")
    assert camila.etapa == "admitido"
    r2 = client.post(f"/lab/admita/candidatos/{camila.id}/mover", data={"direcao": "proxima"})
    assert r2.status_code == 409
    assert "última etapa" in r2.json()["detail"].lower()


# ------------------------------------------------------------- auditoria --

def test_toda_acao_grava_trilha_de_auditoria(client, db_session):
    _entrar(client)
    antes = db_session.query(LabAuditoria).count()

    elisa = _candidato(db_session, "Elisa Tavares Nogueira")
    client.post(f"/lab/admita/candidatos/{elisa.id}/aprovar-rh")

    depois = db_session.query(LabAuditoria).count()
    assert depois == antes + 1
    ultima = (
        db_session.query(LabAuditoria)
        .order_by(LabAuditoria.id.desc())
        .first()
    )
    assert "Elisa Tavares Nogueira" in ultima.acao
    assert ultima.quem == "RH"
    assert "—" not in ultima.acao  # regra do Leandro: nunca travessão


def test_auditoria_aparece_no_fragmento(client, db_session):
    r = _entrar(client)
    assert "Trilha de auditoria" in r.text
    assert "evento" in r.text.lower()


# ------------------------------------------------- nova candidatura/modal --

def test_criar_candidato_valido_aparece_na_esteira_com_origem_visitante(client, db_session):
    _entrar(client)
    r = client.post(
        "/lab/admita/candidatos",
        data={"nome": "Marina Alves Torres", "cargo": "Designer de Produto Pleno"},
    )
    assert r.status_code == 200
    assert "Marina Alves Torres" in r.text
    assert "Em construção interna" not in r.text

    criado = _candidato(db_session, "Marina Alves Torres")
    assert criado.origem == "visitante"
    assert criado.etapa == "candidato"


def test_criar_candidato_com_cargo_fora_da_lista_e_rejeitado(client):
    _entrar(client)
    r = client.post(
        "/lab/admita/candidatos",
        data={"nome": "Alguém", "cargo": "Cargo Inventado Que Não Existe"},
    )
    assert r.status_code == 409


def test_criar_candidato_com_nome_vazio_e_rejeitado(client):
    _entrar(client)
    r = client.post("/lab/admita/candidatos", data={"nome": "   ", "cargo": "Auxiliar Administrativo"})
    assert r.status_code == 409


def test_decimo_primeiro_candidato_do_visitante_e_rejeitado_seeds_nao_contam(client, db_session):
    """§8: teto de MAX_REGISTROS_POR_DEMO (10) por sandbox, só contando
    `origem="visitante"` — os 6 candidatos SEMEADOS não consomem o teto."""
    _entrar(client)
    assert MAX_REGISTROS_POR_DEMO == 10
    for i in range(MAX_REGISTROS_POR_DEMO):
        r = client.post(
            "/lab/admita/candidatos",
            data={"nome": f"Candidato Visitante {i}", "cargo": "Auxiliar Administrativo"},
        )
        assert r.status_code == 200, r.text

    r11 = client.post(
        "/lab/admita/candidatos",
        data={"nome": "Décimo Primeiro Visitante", "cargo": "Auxiliar Administrativo"},
    )
    assert r11.status_code == 409
    assert "limite" in r11.json()["detail"].lower()

    total_visitante = (
        db_session.query(LabCandidato)
        .filter(LabCandidato.origem == "visitante")
        .count()
    )
    assert total_visitante == MAX_REGISTROS_POR_DEMO


# --------------------------------------------------------- sandbox exigido --

def test_mutacao_sem_sandbox_valido_devolve_400(client):
    # nenhum GET /lab/admita antes: client não tem cookie de sandbox nenhum
    r = client.post(
        "/lab/admita/candidatos", data={"nome": "Fulano", "cargo": "Auxiliar Administrativo"}
    )
    assert r.status_code == 400


def test_candidato_de_outro_sandbox_nao_e_acessivel(client, client2, db_session):
    _entrar(client)
    _entrar(client2)
    # os dois sandboxes semeiam o MESMO conjunto de nomes fictícios — pega
    # o registro mais ANTIGO com esse nome (o do client1, criado primeiro)
    # e ataca com o cookie do client2, que não pode enxergá-lo.
    candidato_do_client1 = (
        db_session.query(LabCandidato)
        .filter(LabCandidato.nome == "Adriana Souza Lima")
        .order_by(LabCandidato.id.asc())
        .first()
    )
    assert candidato_do_client1 is not None

    # TODAS as rotas que recebem `candidato_id` precisam recusar, não só uma:
    # sem isto, uma refatoração que esqueça o filtro de sandbox numa delas
    # passa despercebida, e um visitante mexe na esteira de outro.
    ataques = [
        (f"/lab/admita/candidatos/{candidato_do_client1.id}/aprovar-rh", {}),
        (f"/lab/admita/candidatos/{candidato_do_client1.id}/aprovar-gestor", {}),
        (
            f"/lab/admita/candidatos/{candidato_do_client1.id}/mover",
            {"direcao": "proxima"},
        ),
        (
            f"/lab/admita/candidatos/{candidato_do_client1.id}/entrevista",
            {"data": "2030-01-15"},
        ),
    ]
    for url, dados in ataques:
        r = client2.post(url, data=dados) if dados else client2.post(url)
        assert r.status_code == 409, f"{url} devolveu {r.status_code}"
        assert "não encontrado" in r.json()["detail"].lower(), url

    # a rota de documento precisa de um id de documento que também pertence
    # ao sandbox do client1
    doc = (
        db_session.query(LabDocumentoStatus)
        .filter(LabDocumentoStatus.candidato_id == candidato_do_client1.id)
        .first()
    )
    if doc is not None:
        r = client2.post(
            f"/lab/admita/candidatos/{candidato_do_client1.id}/documentos/{doc.id}/alternar"
        )
        assert r.status_code == 409, r.status_code
        assert "não encontrado" in r.json()["detail"].lower()

    # e nada do sandbox do client1 pode ter mudado depois da rajada
    db_session.expire_all()
    intacto = db_session.get(LabCandidato, candidato_do_client1.id)
    assert intacto.aprovado_rh is False
    assert intacto.etapa == "documentos"


# ------------------------------------------------------------- fragmentos --

@pytest.mark.parametrize("rota,dados", [
    ("aprovar-rh", None),
])
def test_fragmentos_de_mutacao_devolvem_200_e_html_do_shell(client, db_session, rota, dados):
    _entrar(client)
    elisa = _candidato(db_session, "Elisa Tavares Nogueira")
    r = client.post(f"/lab/admita/candidatos/{elisa.id}/{rota}", data=dados or {})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert 'id="admita-shell"' in r.text


# --------------------------------------------------------------- §9.2 |safe --

def test_nenhum_safe_nos_templates_do_admita():
    import pathlib
    raiz = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "app" / "templates" / "lab" / "admita"
    )
    assert raiz.is_dir()
    for caminho in raiz.rglob("*.html"):
        assert "|safe" not in caminho.read_text(encoding="utf-8"), caminho


# ------------------------------------------------------------ rate limit --

def test_rotas_de_mutacao_do_admita_tem_limitar_taxa():
    from app.lab.protecao import limitar_taxa
    from app.main import app as _app

    def _achatar(rotas):
        out = []
        for r in rotas:
            if type(r).__name__ == "_IncludedRouter":
                out.extend(_achatar(r.original_router.routes))
            else:
                out.append(r)
        return out

    rotas = [
        r for r in _achatar(_app.routes)
        if getattr(r, "path", "").startswith("/lab/admita")
    ]
    assert len(rotas) >= 6, [r.path for r in rotas]  # GET + 5 rotas de mutação
    for rota in rotas:
        chamadas = [d.call for d in rota.dependant.dependencies]
        assert limitar_taxa in chamadas, rota.path


# -------------------------------------------------- §13b: proibido .rola-interno --

def test_rola_interno_nao_e_usado_em_nenhum_template_ou_css_do_admita(client):
    """A classe existe em `lab-base.css` (Task 1, outro território) e os
    comentários Jinja deste módulo CITAM o nome dela por escrito (para
    explicar por que não é usada) — o que a REGRA ENDURECIDA proíbe é o
    USO de verdade: `class="...rola-interno..."` no HTML renderizado (que
    já não tem comentário Jinja nenhum, o Jinja os descarta antes de
    devolver a resposta) e a declaração `.rola-interno {` em admita.css."""
    import pathlib
    r = _entrar(client)
    assert "rola-interno" not in r.text

    css = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "app" / "static" / "lab" / "admita.css"
    ).read_text(encoding="utf-8")
    css_sem_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert ".rola-interno" not in css_sem_comentarios


# --------------------------------------------------------------- copy PT-BR --

def test_texto_visivel_do_admita_sem_travessao(client):
    r = _entrar(client)
    corpo = r.text.split("<body", 1)[1].split(">", 1)[1]
    texto_visivel = re.sub(r"<[^>]+>", " ", corpo)
    assert "—" not in texto_visivel


def test_sidebar_mostra_estado_com_numeros_reais(client, db_session):
    r = _entrar(client)
    assert "Prazos estourando" in r.text
    assert "Documentos pendentes" in r.text
    # "Prontos para folha" é o recorte de quem faz fechamento de folha:
    # admitido COM a documentação inteira conferida. É de propósito diferente
    # da contagem da etapa "Admitido", que inclui quem ainda tem pendência.
    assert "Prontos para folha" in r.text
    assert "Admitidos" not in r.text, "a sidebar voltou a repetir a etapa"

    bruno = _candidato(db_session, "Bruno Andrade Costa")
    client.post(f"/lab/admita/candidatos/{bruno.id}/aprovar-gestor")
    db_session.expire_all()

    bruno2 = _candidato(db_session, "Bruno Andrade Costa")
    assert bruno2.etapa == "admitido"
    docs_bruno = _docs(db_session, bruno2.id)
    conferidos = docs_bruno and all(d.conferido for d in docs_bruno)

    esperado = 1 + (1 if conferidos else 0)  # Camila (seed) + Bruno se completo
    r2 = client.get("/lab/admita")
    achado = re.search(
        r"Prontos para folha.{0,120}?(\d+) sem pendência", r2.text, re.S
    )
    assert achado, "contador de prontos para folha não encontrado"
    assert int(achado.group(1)) == esperado, achado.group(0)


# --------------------------------------------------- agenda de entrevistas --

def _amanha_iso():
    return (dt.date.today() + dt.timedelta(days=1)).isoformat()


def test_agenda_lista_todos_os_candidatos_com_e_sem_data(client):
    r = _entrar(client)
    assert "Agenda de entrevistas" in r.text
    # os 6 do cenário aparecem no painel, não só os que têm entrevista
    for nome in (
        "Adriana Souza Lima", "Bruno Andrade Costa", "Camila Ferreira Dias",
        "Diego Martins Rocha", "Elisa Tavares Nogueira", "Felipe Nakashima Alves",
    ):
        assert nome in r.text
    assert "sem data" in r.text, "quem não tem entrevista precisa aparecer assim"
    assert 'data-agenda-data="' in r.text


def test_marcar_entrevista_grava_data_e_registra_na_auditoria(client, db_session):
    _entrar(client)
    diego = _candidato(db_session, "Diego Martins Rocha")
    assert diego.entrevista_em is None

    quando = _amanha_iso()
    r = client.post(
        f"/lab/admita/candidatos/{diego.id}/entrevista", data={"data": quando}
    )
    assert r.status_code == 200

    db_session.expire_all()
    diego2 = _candidato(db_session, "Diego Martins Rocha")
    assert diego2.entrevista_em is not None
    assert diego2.entrevista_em.date().isoformat() == quando

    linhas = db_session.query(LabAuditoria).all()
    assert any("entrevista" in linha.acao.lower() and "Diego" in linha.acao for linha in linhas)


def test_desmarcar_entrevista_com_data_vazia(client, db_session):
    _entrar(client)
    adriana = _candidato(db_session, "Adriana Souza Lima")
    assert adriana.entrevista_em is not None, "o seed marca a entrevista da Adriana"

    r = client.post(f"/lab/admita/candidatos/{adriana.id}/entrevista", data={"data": ""})
    assert r.status_code == 200

    db_session.expire_all()
    assert _candidato(db_session, "Adriana Souza Lima").entrevista_em is None


def test_entrevista_no_passado_e_recusada(client, db_session):
    _entrar(client)
    diego = _candidato(db_session, "Diego Martins Rocha")
    ontem = (dt.date.today() - dt.timedelta(days=1)).isoformat()

    r = client.post(f"/lab/admita/candidatos/{diego.id}/entrevista", data={"data": ontem})
    assert r.status_code == 409
    assert "hoje em diante" in r.json()["detail"].lower()

    db_session.expire_all()
    assert _candidato(db_session, "Diego Martins Rocha").entrevista_em is None


def test_entrevista_com_data_hostil_ou_distante_demais_e_recusada(client, db_session):
    _entrar(client)
    diego = _candidato(db_session, "Diego Martins Rocha")

    for valor in ("amanhã", "2026-13-45", "<script>", "9999-01-01"):
        r = client.post(
            f"/lab/admita/candidatos/{diego.id}/entrevista", data={"data": valor}
        )
        assert r.status_code == 409, f"{valor} devolveu {r.status_code}"

    db_session.expire_all()
    assert _candidato(db_session, "Diego Martins Rocha").entrevista_em is None


def test_menu_tem_divisor_e_as_duas_ferramentas(client):
    """A coluna deixou de repetir as 5 etapas (que já são as 5 colunas do
    quadro no desktop e as fichas no aplicativo) e ficou com o que só existe
    ali: as situações da esteira e as ferramentas do sistema."""
    r = _entrar(client)
    assert r.text.count("admita-sidebar-divisor") >= 1
    assert "data-abrir-agenda" in r.text
    assert "data-abrir-config" in r.text
    assert "Configurações" in r.text


def test_painel_de_configuracoes_avisa_que_e_ficticio(client):
    r = _entrar(client)
    assert "Configurações do Admita" in r.text
    # a tela não pode fingir que salva: o aviso é parte do requisito
    assert "não gravam nada" in r.text


# --------------------------------------------------- título e chamadas UI --

def test_titulo_traz_saudacao_tela_e_contagem_viva(client):
    r = _entrar(client)
    # a saudação tem fallback no HTML e é corrigida pelo relógio do visitante
    assert "data-saudacao" in r.text
    assert "time de RH" in r.text
    assert "Esteira de admissão" in r.text
    # empresa fictícia declarada como tal, e o número em destaque
    assert "Admita Studio RH" in r.text
    assert "(empresa fictícia)" in r.text
    assert 'class="admita-numero"' in r.text
    assert "candidatos em andamento" in r.text
    # os três pontinhos animados fecham a frase
    assert "admita-reticencias" in r.text


def test_animacoes_respeitam_quem_pediu_menos_movimento():
    from pathlib import Path

    css = (
        Path(__file__).resolve().parents[2]
        / "app" / "static" / "lab" / "admita.css"
    ).read_text(encoding="utf-8")
    assert "admita-chamada" in css, "o botão de nova candidatura precisa pulsar"
    assert "prefers-reduced-motion" in css
    # a regra de movimento reduzido tem que desligar AS DUAS animações novas
    bloco = css.split("prefers-reduced-motion")[1]
    assert "admita-reticencias" in bloco
    assert "botao-primario" in bloco
    assert "animation: none" in bloco


def test_assinatura_central_traz_marca_selo_e_slogan(client):
    r = _entrar(client)
    assert "admita-assinatura" in r.text
    assert "v. beta" in r.text
    assert "do currículo ao crachá" in r.text
    # o dono pediu o selo nos DOIS lugares: ao lado da marca no topo do menu
    # (some junto com os rótulos quando a barra recolhe) e na assinatura
    assert r.text.count("v. beta") == 2
    assert "admita-selo-menu" in r.text


def test_painel_de_configuracoes_fecha_pelo_x_e_nao_so_pelo_esc():
    """O painel vive fora de `#admita-app`, então o listener do app não o
    alcança. Sem um listener no documento, o X não fecha e as chaves não
    viram, que foi exatamente o que o dono relatou."""
    from pathlib import Path

    js = (
        Path(__file__).resolve().parents[2]
        / "app" / "static" / "lab" / "admita.js"
    ).read_text(encoding="utf-8")
    depois_do_documento = js.split('document.addEventListener("click"')[1]
    assert "data-fechar-config" in depois_do_documento
    assert "admita-chave" in depois_do_documento


def test_configuracoes_tem_as_seis_abas_pedidas(client):
    r = _entrar(client)
    for aba in ("Prazos", "Documentos", "Aprovações", "Avisos", "Auditoria", "Acessos"):
        assert f'data-aba="{aba.lower().replace("ç", "c").replace("õ", "o").replace("é", "e")}"' in r.text \
            or aba in r.text, aba
    # a de acessos tem cor própria (classe própria), como o dono pediu
    assert "admita-aba-acessos" in r.text
    # e traz o CRUD de quem enxerga o sistema
    assert "Cadastrar" in r.text
    assert "data-acesso-editar" in r.text
    assert "data-acesso-excluir" in r.text


def test_acessos_nunca_injeta_texto_do_visitante_como_html():
    """A lista de acessos é montada no navegador com o que a pessoa digita.

    Texto de visitante é texto morto (§9.2): nome e e-mail têm que entrar
    por `textContent`. Um `innerHTML` com esses valores seria XSS mesmo numa
    tela que não grava nada, porque o texto continua na página."""
    from pathlib import Path

    js = (
        Path(__file__).resolve().parents[2]
        / "app" / "static" / "lab" / "admita.js"
    ).read_text(encoding="utf-8")
    corpo = js.split("function criarLinhaDeAcesso")[1].split("\n  var formAcesso")[0]
    assert "textContent = nome" in corpo
    assert "textContent = email" in corpo
    for linha in corpo.split("\n"):
        if "innerHTML" in linha:
            # os únicos innerHTML permitidos aqui são de ícone, que é
            # marcação constante: nome e e-mail nunca entram por essa via
            assert "svg" in linha, linha
            assert "nome" not in linha and "email" not in linha, linha


def test_admita_js_nao_tem_erro_de_sintaxe():
    """Um `}` a mais mata o arquivo inteiro e a demo vira HTML morto, sem
    nenhum aviso na tela. Já aconteceu nesta rodada, então vira trava."""
    import re
    import shutil
    import subprocess
    from pathlib import Path

    caminho = (
        Path(__file__).resolve().parents[2]
        / "app" / "static" / "lab" / "admita.js"
    )
    fonte = caminho.read_text(encoding="utf-8")

    node = shutil.which("node")
    if node:
        pronto = subprocess.run(
            [node, "--check", str(caminho)], capture_output=True, text=True
        )
        assert pronto.returncode == 0, pronto.stderr

    # sem node por perto, o mínimo: blocos e parênteses fechados fora de
    # strings e comentários
    limpo = re.sub(
        r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|/\*.*?\*/|//[^\n]*',
        "", fonte, flags=re.S,
    )
    assert limpo.count("{") == limpo.count("}"), "chaves desbalanceadas"
    assert limpo.count("(") == limpo.count(")"), "parênteses desbalanceados"


# ------------------------------------------------------ entrada e saída --

def test_entrada_tem_splash_login_e_aviso_honesto(client):
    r = _entrar(client)
    assert 'id="admita-entrada"' in r.text
    assert "Entrar no sistema" in r.text
    assert "toque para pular" in r.text
    # a tela de acesso não pode fingir que guarda senha
    assert "nenhuma senha é digitada, enviada ou guardada" in r.text


def test_entrada_nao_tem_campo_de_senha_de_verdade(client):
    """Os pontinhos são desenhados. Um `<input type=password>` numa demo
    convidaria alguém a digitar a senha real de outro lugar, e isso não
    pode existir aqui nem desativado."""
    r = _entrar(client)
    assert 'type="password"' not in r.text


def test_saida_do_sistema_leva_para_a_vitrine(client):
    r = _entrar(client)
    # os três gestos de sair apontam para a vitrine do Lab
    assert 'class="admita-usuario-sair" href="/lab"' in r.text
    assert 'class="admita-sair" href="/lab"' in r.text
    assert "fechar demonstração" in r.text


def test_botao_de_fechar_usa_o_pill_padrao_do_site(client):
    """O dono pediu o botão do cabeçalho no padrão do site, e não um link
    solto: é a mesma classe `.cta-pill` do cabeçalho das outras páginas."""
    r = _entrar(client)
    assert "cta-pill cta-forte lab-nav-voltar" in r.text


# ---------------------------------------------------------------- cargos --

def _cargos(db_session, sandbox_id=None):
    from app.lab.models import LabCargo

    consulta = db_session.query(LabCargo)
    if sandbox_id is not None:
        consulta = consulta.filter(LabCargo.sandbox_id == sandbox_id)
    return consulta.order_by(LabCargo.ordem.asc(), LabCargo.id.asc()).all()


def test_cargos_nascem_semeados_e_aparecem_no_dropdown(client, db_session):
    r = _entrar(client)
    cargos = _cargos(db_session)
    assert len(cargos) >= 10
    assert f'<option value="{cargos[0].nome}">' in r.text


def test_criar_renomear_e_excluir_cargo(client, db_session):
    _entrar(client)

    r = client.post("/lab/admita/cargos", data={"nome": "Analista de Remuneração Pleno"})
    assert r.status_code == 200
    db_session.expire_all()
    novo = [c for c in _cargos(db_session) if c.nome == "Analista de Remuneração Pleno"]
    assert novo, "o cargo novo tem que existir no banco"

    from app.lab.models import LabCargo

    novo_id = novo[0].id
    r = client.post(f"/lab/admita/cargos/{novo_id}", data={"nome": "Analista de Remuneração Sênior"})
    assert r.status_code == 200
    db_session.expire_all()
    assert db_session.get(LabCargo, novo_id).nome == "Analista de Remuneração Sênior"

    r = client.post(f"/lab/admita/cargos/{novo_id}/excluir")
    assert r.status_code == 200
    db_session.expire_all()
    assert db_session.get(LabCargo, novo_id) is None


def test_cargo_repetido_e_recusado(client, db_session):
    _entrar(client)
    existente = _cargos(db_session)[0].nome
    r = client.post("/lab/admita/cargos", data={"nome": existente})
    assert r.status_code == 409
    assert "já está na lista" in r.json()["detail"]


def test_excluir_cargo_nao_mexe_em_quem_ja_foi_cadastrado(client, db_session):
    """A ficha do candidato guarda o cargo que valia no dia. Excluir da
    lista não pode reescrever a história de ninguém."""
    _entrar(client)
    cargo = _cargos(db_session)[0]
    nome_do_cargo, cargo_id = cargo.nome, cargo.id
    client.post("/lab/admita/candidatos", data={"nome": "Teste Da Silva", "cargo": nome_do_cargo})
    db_session.expire_all()
    assert _candidato(db_session, "Teste Da Silva").cargo == nome_do_cargo

    client.post(f"/lab/admita/cargos/{cargo_id}/excluir")
    db_session.expire_all()
    assert _candidato(db_session, "Teste Da Silva").cargo == nome_do_cargo


def test_cargo_de_outro_sandbox_nao_pode_ser_mexido(client, client2, db_session):
    from app.lab.models import LabCargo

    _entrar(client)
    _entrar(client2)
    do_client1 = (
        db_session.query(LabCargo).order_by(LabCargo.id.asc()).first()
    )
    r = client2.post(f"/lab/admita/cargos/{do_client1.id}", data={"nome": "Invadido"})
    assert r.status_code == 409
    r = client2.post(f"/lab/admita/cargos/{do_client1.id}/excluir")
    assert r.status_code == 409


def test_modal_do_selo_beta_e_comercial_e_honesto(client):
    r = _entrar(client)
    assert 'id="admita-modal-beta"' in r.text
    assert "Leandro Furtado" in r.text
    assert "sistema da sua empresa" in r.text
    # a parte honesta: dado fictício, sessão curta, nenhuma senha
    assert "somem sozinhos em 24 horas" in r.text
    assert "Nenhuma senha é digitada" in r.text
