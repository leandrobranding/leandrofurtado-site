"""Configuração central do site — tudo pode ser sobrescrito por variáveis de ambiente ou .env."""
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    site_name: str = "Leandro Furtado"
    base_url: str = "https://leandrofurtado.com.br"
    debug: bool = False

    data_dir: Path = BASE_DIR / "data"
    secret_key: str = ""

    admin_username: str = "leandro"
    # Se vazio, uma senha forte é gerada no primeiro boot e gravada em data/ADMIN_CREDENTIALS.txt
    admin_password: str = ""

    session_max_age: int = 60 * 60 * 8  # 8 horas
    max_upload_mb: int = 300

    # A vitrine PÚBLICA do Nodal (/nodal, /nodal/curso/..., área do aluno).
    # Nasce desligada: o produto não foi lançado, e o painel administrativo
    # continua ligado para ele ser construído. Foi o que a branch de produção
    # já fazia na prática antes do merge de 24/08/2026, registrando só o
    # router do admin; aqui isso vira decisão explícita em vez de consequência
    # de duas branches separadas.
    nodal_publico: bool = False

    # ------------------------------------------------- parâmetros de defesa --
    #
    # Saíram do código-fonte em 24/08/2026, quando o repositório passou a ser
    # público. Duas razões, e a segunda é a que motivou:
    #
    # 1. Apertar um limite deixou de exigir deploy. Vira variável de ambiente.
    # 2. O que está escrito aqui é o PADRÃO, e o padrão é público. O valor que
    #    está valendo no servidor mora no .env, que nunca foi versionado.
    #
    # Isso não substitui defesa nenhuma: quem lê o código continua vendo o
    # desenho inteiro, que é como tem que ser — segurança que depende de o
    # atacante não ler o código não é segurança. O que muda é que ele deixa de
    # receber os números exatos de graça, e a distância entre "sei como
    # funciona" e "sei em que ponto ele corta" é o que compra tempo.
    login_max_tentativas: int = 8
    login_janela_segundos: int = 15 * 60

    spam_minimo_segundos: int = 4          # abaixo disso não é gente digitando
    spam_maximo_segundos: int = 6 * 60 * 60
    spam_max_envios: int = 3
    spam_janela_segundos: int = 15 * 60

    lab_rate_por_min: int = 30
    lab_max_registros_por_demo: int = 10
    lab_max_ia_por_sandbox: int = 3
    lab_max_emails: int = 2
    lab_max_pdfs: int = 5

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def nodal_private_dir(self) -> Path:
        """PDFs de AULA do Nodal moram aqui — fora de `upload_dir`, que
        `app.main` monta em `/media` via StaticFiles. Nunca dentro dele: o
        que está aqui só pode sair pela rota autenticada de download
        (app/nodal/rotas_aluno.py::baixar_arquivo), nunca por URL direta.

        PDF de SITUAÇÃO (conteúdo público por natureza) continua em
        `upload_dir` como sempre — só o de AULA mora aqui.
        """
        return self.data_dir / "nodal_privado"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'site.db'}"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.nodal_private_dir.mkdir(parents=True, exist_ok=True)

# Chave secreta persistente (assina cookies de sessão) — gerada uma única vez.
if not settings.secret_key:
    _key_file = settings.data_dir / "secret_key"
    if _key_file.exists():
        settings.secret_key = _key_file.read_text().strip()
    else:
        settings.secret_key = secrets.token_urlsafe(64)
        _key_file.write_text(settings.secret_key)
        _key_file.chmod(0o600)


# Fuso do negócio. O servidor roda em UTC e é assim que os dados são gravados, mas
# tudo que uma pessoa lê precisa estar na hora de Curitiba: depois das 21h daqui já
# é o dia seguinte lá, e a newsletter chegou datada de amanhã por causa disso.
try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:  # imagem sem base de fusos: o Brasil não usa horário de verão desde 2019
    import datetime as _dt
    FUSO = _dt.timezone(_dt.timedelta(hours=-3), "America/Sao_Paulo")


def daqui(quando):
    """Converte para a hora de Curitiba. Datas sem fuso são tratadas como UTC."""
    import datetime as _dt
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=_dt.timezone.utc)
    return quando.astimezone(FUSO)


def agora_daqui():
    import datetime as _dt
    return _dt.datetime.now(FUSO)
