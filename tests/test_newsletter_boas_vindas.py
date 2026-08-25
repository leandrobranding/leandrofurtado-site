"""Newsletter de boas-vindas (pacote de lançamento, item 2, 19/08).

O mecanismo de disparo (BackgroundTasks, mesmo mailer da campanha em massa,
falha de SMTP nunca derruba a inscrição) já existia — este pacote entrega o
conteúdo: a campanha marcada is_welcome=True que estava faltando. Cobre a
seed (aditiva e idempotente) e a regra de não reenviar em caso de assinatura
duplicada.
"""
from starlette.testclient import TestClient

from app.database import SessionLocal as _SessionLocal
from app.main import app as _app
from app.models import Campaign, NewsletterSub
from app.services.seeds import WELCOME_SUBJECT, run_seeds


def _subir() -> None:
    with TestClient(_app):
        pass


def _limpar(email: str) -> None:
    db = _SessionLocal()
    try:
        db.query(NewsletterSub).filter_by(email=email).delete()
        db.commit()
    finally:
        db.close()


def test_seed_cria_uma_campanha_de_boas_vindas_com_o_texto_aprovado(db):
    run_seeds(db)
    camps = db.query(Campaign).filter_by(is_welcome=True).all()
    assert len(camps) == 1
    assert camps[0].subject == WELCOME_SUBJECT
    assert camps[0].image  # sempre tem imagem: capa/foto do perfil ou o og-default do site


def test_seed_e_idempotente_rodar_duas_vezes_nao_duplica_a_campanha(db):
    run_seeds(db)
    run_seeds(db)
    assert db.query(Campaign).filter_by(is_welcome=True).count() == 1


def test_assinar_duas_vezes_nao_dispara_boas_vindas_na_segunda(monkeypatch):
    """A segunda inscrição do mesmo e-mail nem chega a gravar de novo (ver
    app/routers/public.py:newsletter) — então o disparo também não pode
    acontecer duas vezes."""
    _subir()
    chamadas = []
    import app.routers.public as public_router
    monkeypatch.setattr(public_router, "_enviar_boas_vindas", lambda email: chamadas.append(email))

    email = "duplicata-boas-vindas@example.com"
    _limpar(email)
    try:
        with TestClient(_app, base_url="https://testserver") as client:
            # Desde 22/08/2026 o formulário exige o carimbo anti-bot
            # (services/anti_spam.py). O teste envia um carimbo válido com
            # idade de 10s — o que um humano de verdade enviaria.
            import time as _time
            from app.config import settings as _cfg
            from app.services import anti_spam as _anti
            _t = _anti.carimbo(_cfg.secret_key, agora=_time.time() - 10)
            r1 = client.post("/newsletter", data={"email": email, "t": _t})
            r2 = client.post("/newsletter", data={"email": email, "t": _t})
        assert r1.status_code in (200, 303)
        assert r2.status_code in (200, 303)
        assert chamadas == [email]
    finally:
        _limpar(email)
