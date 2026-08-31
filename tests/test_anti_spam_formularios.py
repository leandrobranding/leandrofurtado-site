"""Barreiras anti-bot dos formulários públicos (services/anti_spam.py).

Origem: 21/08/2026, spam real recebido pelo formulário de contato — nome
"Hi http://leandrofurtado.com.br/fekal0911 Webmaster", texto-modelo, e-mail
pirduhina96@gmail.com. Passou pelo honeypot, pelo consentimento e pela
validação de e-mail, gravou lead e disparou e-mail para o Leandro.

O primeiro teste reproduz esse envio literalmente. Se alguém afrouxar uma
regra e ele voltar a passar, este arquivo acusa.
"""
from app.services import limite
import time

from app.config import settings
from app.services import anti_spam
from app.services.anti_spam import (carimbo, carimbo_valido, envio_permitido,
                                    motivo_de_spam)

CHAVE = "chave-de-teste"


# ------------------------------------------------------------- o spam real --

def test_o_spam_recebido_em_21_08_e_barrado():
    motivo = motivo_de_spam(
        "Hi http://leandrofurtado.com.br/fekal0911 Webmaster",
        "pirduhina96@gmail.com",
        "Hello http://leandrofurtado.com.br/fekal0911 Webmaster",
    )
    assert motivo == "URL no campo do nome"


# ---------------------------------------------------------------- conteúdo --

def test_nome_de_gente_passa():
    assert motivo_de_spam("Elis Domingues", "elis@example.com",
                          "Quero fechar o pacote de posts da campanha.") == ""


def test_cliente_pode_mandar_link_do_proprio_site():
    """Um link na mensagem é normal ("meu site é tal"). Três ou mais é spam."""
    assert motivo_de_spam("João Pereira", "joao@example.com",
                          "Meu site é https://exemplo.com.br e preciso de rebranding.") == ""


def test_mensagem_que_e_so_links_e_barrada():
    msg = ("Veja https://a.ru/x https://b.ru/y https://c.ru/z")
    assert motivo_de_spam("Promo", "x@y.com", msg) == "mensagem com 3+ links"


def test_dominio_nu_no_nome_tambem_e_barrado():
    assert motivo_de_spam("promo.seo-master.ru/ofertas", "x@y.com", "oi") != ""


def test_texto_em_ingles_nao_e_barrado_por_ser_ingles():
    """O site tem versão EN; cliente real escreve em inglês. O que barra é
    assinatura de campanha, nunca o idioma."""
    assert motivo_de_spam("Sarah Mills", "sarah@agency.com",
                          "Loved the Electrolux case. Are you available in October?") == ""


# ------------------------------------------------------------------- tempo --

def test_carimbo_recem_gerado_reprova_porque_humano_nao_digita_tao_rapido():
    agora = time.time()
    assert not carimbo_valido(carimbo(CHAVE, agora), CHAVE,
                              agora + anti_spam.MINIMO_SEGUNDOS - 1)


def test_carimbo_com_idade_humana_passa():
    agora = time.time()
    assert carimbo_valido(carimbo(CHAVE, agora), CHAVE, agora + 30)


def test_carimbo_de_ontem_reprova():
    agora = time.time()
    assert not carimbo_valido(carimbo(CHAVE, agora - 86400), CHAVE, agora)


def test_carimbo_ausente_ou_forjado_reprova():
    assert not carimbo_valido("", CHAVE)
    assert not carimbo_valido("1755900000.assinaturafalsa", CHAVE)
    # assinado com outra chave
    agora = time.time()
    assert not carimbo_valido(carimbo("outra-chave", agora), CHAVE, agora + 30)


# -------------------------------------------------------------------- taxa --

def test_o_envio_seguinte_ao_teto_do_mesmo_ip_e_barrado():
    """O teto e a janela vieram para `config.py` em 24/08/2026, junto com a
    publicação do repositório. O teste passou a derivar dos dois em vez de
    contar até três na mão: com número fixo aqui, mudar o limite no ambiente
    faria a suíte mentir sem falhar."""
    limite.limpar()
    agora = time.time()
    ip = "203.0.113.7"
    for i in range(anti_spam.MAX_ENVIOS):
        assert envio_permitido(ip, agora + i), f"envio {i + 1} devia passar"
    assert not envio_permitido(ip, agora + anti_spam.MAX_ENVIOS)
    # e libera quando a janela passa
    assert envio_permitido(ip, agora + anti_spam.JANELA + 60)


def test_ips_diferentes_nao_dividem_o_mesmo_teto():
    limite.limpar()
    agora = time.time()
    for i in range(anti_spam.MAX_ENVIOS):
        assert envio_permitido("198.51.100.1", agora + i)
    assert envio_permitido("198.51.100.2", agora + 5)


# -------------------------------------------------- comportamento da rota --

def test_bot_sem_carimbo_recebe_sucesso_falso_e_nada_e_gravado():
    """A resposta para spam é fingir que deu certo: erro ensina o operador a
    ajustar o payload; sucesso falso o manda embora. E nada entra no banco."""
    import os
    from starlette.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal
    from app.models import ContactMessage, Lead

    limite.limpar()
    with TestClient(app, base_url="https://testserver") as cliente:
        r = cliente.post("/contact", data={
            "name": "Hi http://leandrofurtado.com.br/x Webmaster",
            "email": "bot@spam.ru", "message": "Hello Webmaster",
            "consent": "on",
        }, follow_redirects=False)
    assert r.status_code == 303
    assert "sent=1" in r.headers["location"]          # o sucesso falso
    with SessionLocal() as db:
        assert db.query(Lead).filter_by(email="bot@spam.ru").count() == 0
        assert db.query(ContactMessage).filter_by(email="bot@spam.ru").count() == 0


def test_humano_com_carimbo_valido_continua_conseguindo_falar():
    """A barreira não pode custar um cliente: envio com carimbo de idade
    humana, nome de gente e uma mensagem normal entra como sempre entrou."""
    from starlette.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal
    from app.models import ContactMessage, Lead

    limite.limpar()
    t = carimbo(settings.secret_key, time.time() - 12)
    with TestClient(app, base_url="https://testserver") as cliente:
        r = cliente.post("/contact", data={
            "name": "Cliente de Teste Anti Spam",
            "email": "cliente-antispam@example.com",
            "message": "Quero um orçamento para identidade visual.",
            "consent": "on", "t": t,
        }, follow_redirects=False)
    assert r.status_code == 303
    assert "sent=1" in r.headers["location"]
    with SessionLocal() as db:
        assert db.query(Lead).filter_by(email="cliente-antispam@example.com").count() == 1
        # limpeza: teste não deixa lixo no banco de quem rodar depois
        db.query(Lead).filter_by(email="cliente-antispam@example.com").delete()
        db.query(ContactMessage).filter_by(email="cliente-antispam@example.com").delete()
        db.commit()


# ------------------------------------------------- limites configuráveis --

def test_os_limites_saem_do_ambiente_e_nao_do_codigo_fonte():
    """24/08/2026: o repositório do site virou público, e com ele iriam os
    números exatos em que cada defesa corta. Quem lê o código continua vendo o
    desenho inteiro, que é como tem que ser. O que ele deixa de receber de
    graça é o valor que está valendo no servidor, que mora no .env.

    Este teste falha se alguém escrever o número de volta no módulo.
    """
    from app.config import settings
    assert anti_spam.MINIMO_SEGUNDOS == settings.spam_minimo_segundos
    assert anti_spam.MAXIMO_SEGUNDOS == settings.spam_maximo_segundos
    assert anti_spam.MAX_ENVIOS == settings.spam_max_envios
    assert anti_spam.JANELA == settings.spam_janela_segundos

    from app import auth
    assert auth.MAX_ATTEMPTS == settings.login_max_tentativas
    assert auth.WINDOW == settings.login_janela_segundos

    from app.lab import protecao
    assert protecao.MAX_IA_POR_SANDBOX == settings.lab_max_ia_por_sandbox
    assert protecao.RATE_LIMIT_POR_MIN == settings.lab_rate_por_min


def test_o_env_esta_fora_do_rsync_do_deploy():
    """O .env do servidor guarda os limites que estão realmente valendo, e ele
    não existe na máquina local. `rsync --delete` apaga o que está no destino e
    não está na origem: sem esta exclusão, o primeiro deploy depois de criar o
    arquivo o apagaria, e as defesas voltariam ao padrão público sem nenhum
    aviso. Foi encontrado antes de acontecer, em 24/08/2026.
    """
    from app.config import BASE_DIR
    script = (BASE_DIR / "deploy" / "atualizar.sh").read_text(encoding="utf-8")
    assert "--exclude '.env'" in script, "o .env voltou a ser apagado pelo deploy"

    compose = (BASE_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    assert "env_file" in compose, "o container parou de ler o .env"
    assert "required: false" in compose, "sem .env o projeto deixou de subir"
