"""Conserto pós-lançamento, item 1 (19/08): a seed antiga identificava "a
campanha de boas-vindas do site" pelo critério `is_welcome=True` — e o banco
de produção já tinha UMA campanha assim, a da página de construção
("Meu site está quase pronto! 🤩 🖥", status 'enviado'), que usava o
mecanismo antigo. Resultado: `run_seeds` nunca criava a campanha nova, ela
ficava invisível no admin, e um assinante novo receberia o e-mail de
construção como boas-vindas.

O critério novo identifica a campanha DO SITE por um marcador próprio
(WELCOME_ORIGIN, gravado em Campaign.origem), não por is_welcome — esse
campo continua existindo e continua sendo o que manda no disparo e na
listagem do admin, mas deixa de ser o critério de "já existe?" da seed.
"""
from app.models import Campaign
from app.services.seeds import WELCOME_ORIGIN, WELCOME_SUBJECT, run_seeds


def _campanha_antiga_de_construcao() -> Campaign:
    """Reproduz exatamente o registro real de produção (id=1, is_welcome=1,
    'enviado') que motivou o conserto."""
    return Campaign(
        subject="Meu site está quase pronto! 🤩 🖥",
        body="Em breve, novidades.",
        audience="assinantes",
        is_welcome=True,
        status="enviado",
    )


def test_cenario_de_producao_cria_a_campanha_do_site_e_rebaixa_a_antiga(db):
    antiga = _campanha_antiga_de_construcao()
    db.add(antiga)
    db.commit()
    antiga_id = antiga.id

    run_seeds(db)

    todas = db.query(Campaign).all()
    assert len(todas) == 2, "a campanha antiga tem que sobreviver, e a nova tem que nascer"

    nova = db.query(Campaign).filter_by(origem=WELCOME_ORIGIN).first()
    assert nova is not None, "a campanha do site precisa existir, marcada por origem"
    assert nova.subject == WELCOME_SUBJECT
    assert nova.is_welcome is True

    antiga_recarregada = db.get(Campaign, antiga_id)
    assert antiga_recarregada.is_welcome is False, "só uma boas-vindas por vez"
    # intacta no resto: nada além da flag muda
    assert antiga_recarregada.subject == "Meu site está quase pronto! 🤩 🖥"
    assert antiga_recarregada.status == "enviado"
    assert antiga_recarregada.audience == "assinantes"

    # a garantia de "só uma boas-vindas" vale pro banco inteiro
    assert db.query(Campaign).filter_by(is_welcome=True).count() == 1

    # o admin lista e edita a campanha nova pela mesma regra que já usa hoje
    # (Campaign.is_welcome=True) — ver app/routers/admin_nl.py
    listada = next((c for c in todas if c.is_welcome), None)
    assert listada is not None and listada.id == nova.id


def test_idempotente_rodar_duas_vezes_nao_duplica(db):
    antiga = _campanha_antiga_de_construcao()
    db.add(antiga)
    db.commit()

    run_seeds(db)
    run_seeds(db)

    assert db.query(Campaign).filter_by(origem=WELCOME_ORIGIN).count() == 1
    assert db.query(Campaign).filter_by(is_welcome=True).count() == 1


def test_edicao_do_dono_sobrevive_a_novo_boot(db):
    """Depois que a campanha do site já existe, run_seeds nunca mais
    sobrescreve subject/body/preheader — nem a flag is_welcome, mesmo que o
    dono a tenha desmarcado no admin."""
    run_seeds(db)
    nova = db.query(Campaign).filter_by(origem=WELCOME_ORIGIN).first()
    nova.subject = "Assunto editado pelo dono"
    nova.body = "Corpo editado pelo dono"
    nova.is_welcome = False
    db.commit()

    run_seeds(db)

    editada = db.query(Campaign).filter_by(origem=WELCOME_ORIGIN).first()
    assert editada.subject == "Assunto editado pelo dono"
    assert editada.body == "Corpo editado pelo dono"
    assert editada.is_welcome is False, "seed não reimpõe a flag depois que o dono mexeu"
    # e não nasce uma segunda campanha de origem site_welcome
    assert db.query(Campaign).filter_by(origem=WELCOME_ORIGIN).count() == 1


def test_instalacao_nova_sem_campanha_nenhuma_tambem_cria_a_do_site(db):
    run_seeds(db)
    camps = db.query(Campaign).filter_by(is_welcome=True).all()
    assert len(camps) == 1
    assert camps[0].subject == WELCOME_SUBJECT
    assert camps[0].origem == WELCOME_ORIGIN
