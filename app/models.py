import datetime as dt

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Table, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


case_tags = Table(
    "case_tags",
    Base.metadata,
    Column("case_id", ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # verificação em duas etapas. O segredo só vale depois de confirmado com um
    # código, senão dá para se trancar do lado de fora com um QR nunca escaneado.
    totp_secret: Mapped[str] = mapped_column(String(64), default="")
    totp_ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_backup: Mapped[list] = mapped_column(JSON, default=list)   # hashes, uso único
    totp_desde: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name_pt: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    # "" = categoria comum, com página de case. "sites" = cada item é um site:
    # sem página própria, o clique vai direto ao endereço e o card mostra a prévia.
    kind: Mapped[str] = mapped_column(String(20), default="")

    cases: Mapped[list["Case"]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))

    cases: Mapped[list["Case"]] = relationship(secondary=case_tags, back_populates="tags")


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    title_pt: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200), default="")
    subtitle_pt: Mapped[str] = mapped_column(String(300), default="")
    subtitle_en: Mapped[str] = mapped_column(String(300), default="")
    client: Mapped[str] = mapped_column(String(160), default="")
    year: Mapped[str] = mapped_column(String(20), default="")
    # Inteligência artificial no processo: "" (não informado), "nao" ou "sim".
    # Três estados de propósito: um booleano diria "não" para todo case antigo
    # que nunca foi perguntado, e isso é diferente de responder que não usou.
    ia: Mapped[str] = mapped_column(String(4), default="")
    # Ficha técnica na página: nem todo trabalho tem crédito que valha a régua.
    ficha_on: Mapped[bool] = mapped_column(Boolean, default=True)
    # Ferramentas usadas no case, como slugs separados por vírgula ("photoshop,
    # claude"). Viram selos com o ícone oficial ao lado do case. A lista válida
    # mora em services/programas.py.
    programas: Mapped[str] = mapped_column(Text, default="")
    role_pt: Mapped[str] = mapped_column(String(200), default="")
    role_en: Mapped[str] = mapped_column(String(200), default="")
    body_pt: Mapped[str] = mapped_column(Text, default="")  # Markdown
    body_en: Mapped[str] = mapped_column(Text, default="")
    cover_image: Mapped[str] = mapped_column(String(300), default="")   # caminho relativo em uploads
    cover_video: Mapped[str] = mapped_column(String(300), default="")   # vídeo curto para hover/hero
    # Categoria "sites": o case não tem página própria, o link leva ao site real.
    # A prévia é capturada do próprio endereço, e site_shot_at diz quando foi.
    site_url: Mapped[str] = mapped_column(String(500), default="")
    site_shot: Mapped[str] = mapped_column(String(300), default="")   # captura em uploads
    site_shot_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cliente como relação. O campo de texto continua existindo por enquanto,
    # preenchido a partir do relacionado, para não quebrar o que já lê case.client.
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    client_ref: Mapped["Client | None"] = relationship(back_populates="cases")

    # Arquivado sai do site sem ser apagado: o trabalho existiu, só não está
    # mais em exibição. Excluir de vez é outra coisa, e continua sendo outra.
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # SEO por case. Vazio significa "usa o título e o subtítulo", que é o certo
    # na maioria das vezes; o campo existe para quando não for.
    seo_title: Mapped[str] = mapped_column(String(200), default="")
    seo_desc: Mapped[str] = mapped_column(String(320), default="")
    seo_image: Mapped[str] = mapped_column(String(300), default="")
    noindex: Mapped[bool] = mapped_column(Boolean, default=False)

    comments: Mapped[list["CaseComment"]] = relationship(
        back_populates="case", cascade="all, delete-orphan")
    accent: Mapped[str] = mapped_column(String(16), default="")          # cor de destaque opcional (#hex)

    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[Category | None] = relationship(back_populates="cases")
    tags: Mapped[list[Tag]] = relationship(secondary=case_tags, back_populates="cases")
    media: Mapped[list["MediaItem"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="MediaItem.sort"
    )

    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    # Ordem entre os destaques da home. Default alto (999): quem nunca recebeu
    # uma ordem explícita cai no fim da fila, atrás de quem foi arranjado a
    # dedo — e não na frente, que seria o que um default 0 faria.
    destaque_ordem: Mapped[int] = mapped_column(Integer, default=999)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ig_publish: Mapped[bool] = mapped_column(Boolean, default=False)      # publicar no IG ao publicar o case
    ig_status: Mapped[str] = mapped_column(String(40), default="")        # "", pending, done, error
    ig_detail: Mapped[str] = mapped_column(Text, default="")              # id do post ou mensagem de erro


class MediaItem(Base):
    __tablename__ = "media_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    case: Mapped[Case] = relationship(back_populates="media")

    kind: Mapped[str] = mapped_column(String(20))  # image | video | audio | embed
    src: Mapped[str] = mapped_column(String(500), default="")   # arquivo em uploads OU URL do embed
    thumb: Mapped[str] = mapped_column(String(300), default="")  # variante otimizada (imagens)
    caption_pt: Mapped[str] = mapped_column(String(500), default="")
    caption_en: Mapped[str] = mapped_column(String(500), default="")
    layout: Mapped[str] = mapped_column(String(20), default="full")  # full | half | tall
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # embed: provider, html, og:*
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Profile(Base):
    """Singleton: o currículo completo, bilíngue, editável no admin."""
    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class SiteSetting(Base):
    __tablename__ = "site_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class LinkedInPost(Base):
    """Vitrine de postagens do LinkedIn — texto resumido + link direto ao post."""
    __tablename__ = "linkedin_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    summary: Mapped[str] = mapped_column(String(400))
    tag: Mapped[str] = mapped_column(String(80), default="")
    url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)


class Campaign(Base):
    """Newsletter/e-mail marketing disparado pelo admin.

    O corpo é Markdown (vira HTML no envio), com imagem opcional no topo e
    botão de ação. Guarda o resultado do disparo para histórico.
    """
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(200))
    preheader: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")          # Markdown
    image: Mapped[str] = mapped_column(String(300), default="")  # caminho em uploads
    cta_label: Mapped[str] = mapped_column(String(80), default="")
    cta_url: Mapped[str] = mapped_column(String(400), default="")

    # blocos do editor visual: [{"t":"texto","v":"..."}, {"t":"botao","v":"...","url":"..."}]
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    theme_id: Mapped[int | None] = mapped_column(ForeignKey("themes.id", ondelete="SET NULL"), nullable=True)
    theme: Mapped["Theme | None"] = relationship()

    audience: Mapped[str] = mapped_column(String(30), default="todos")  # todos|assinantes|leads|clientes
    # a campanha marcada aqui é disparada sozinha quando alguém assina a newsletter
    is_welcome: Mapped[bool] = mapped_column(Boolean, default=False)
    # marcador estável de quem criou a campanha ("site_welcome" = a de boas-vindas
    # que a seed entrega). Não confundir com is_welcome: is_welcome é a flag que
    # manda no disparo e pode ser trocada de campanha pelo admin a qualquer hora;
    # `origem` é o que a seed usa para saber se JÁ criou a campanha do site, e por
    # isso nunca muda depois de gravado — nem quando o admin desmarca is_welcome.
    origem: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="rascunho")  # rascunho|enviando|enviado
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Theme(Base):
    """Tema visual do e-mail: as cores do template padrão, trocáveis por campanha."""
    __tablename__ = "themes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    pagina: Mapped[str] = mapped_column(String(16), default="#ecebe6")   # fundo fora do card
    card: Mapped[str] = mapped_column(String(16), default="#0d0d0d")     # o box
    ink: Mapped[str] = mapped_column(String(16), default="#f4f2ed")      # títulos
    body: Mapped[str] = mapped_column(String(16), default="#e6e4df")     # corpo
    muted: Mapped[str] = mapped_column(String(16), default="#8f8d87")    # apoio
    line: Mapped[str] = mapped_column(String(16), default="#252523")     # contornos
    destaque: Mapped[str] = mapped_column(String(16), default="#161615")  # caixas
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)

    def cores(self) -> dict:
        return {"PAGINA": self.pagina, "CARD": self.card, "INK": self.ink,
                "BODY": self.body, "MUTED": self.muted, "LINE": self.line,
                "DESTAQUE": self.destaque}


class EmailEvent(Base):
    """Cada coisa que acontece com um e-mail enviado: base das estatísticas.

    Abertura depende de o cliente carregar a imagem de rastreio, então o número é
    indicativo, nunca exato. Clique é confiável, porque passa por redirecionamento.
    """
    __tablename__ = "email_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    email: Mapped[str] = mapped_column(String(200), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # enviado|abriu|clicou|descadastrou|falhou
    detail: Mapped[str] = mapped_column(String(400), default="")
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)


class NewsletterSub(Base):
    """Assinante da newsletter, com a mesma prova de consentimento dos leads.

    A LGPD não distingue formulário de contato de formulário de newsletter: se vou
    mandar e-mail para a pessoa, preciso saber o que ela aceitou, quando e de onde.
    """
    __tablename__ = "newsletter_subs"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_text: Mapped[str] = mapped_column(Text, default="")
    consent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    lang: Mapped[str] = mapped_column(String(5), default="pt")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class Lead(Base):
    """Contato cadastrado a partir do formulário: base da futura área de clientes.

    Guarda a prova de consentimento (texto aceito, data, IP e user agent) para
    atender LGPD/GDPR — é o que comprova a base legal do tratamento.
    """
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(200), index=True)
    whatsapp: Mapped[str] = mapped_column(String(60), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(60), default="contato")

    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_text: Mapped[str] = mapped_column(Text, default="")
    consent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    lang: Mapped[str] = mapped_column(String(5), default="pt")

    status: Mapped[str] = mapped_column(String(30), default="novo")  # novo|contatado|cliente
    notified: Mapped[bool] = mapped_column(Boolean, default=False)   # e-mail avisado?
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)


class WordCache(Base):
    """Cache de verbetes do recurso "sinônimos e significados".

    Consultar dicionário externo a cada duplo clique seria lento e abusivo com o
    serviço de terceiro. Aqui a palavra é buscada uma vez e fica guardada; a
    resposta seguinte sai do banco em milissegundos.
    """
    __tablename__ = "word_cache"
    term: Mapped[str] = mapped_column(String(80), primary_key=True)
    lang: Mapped[str] = mapped_column(String(5), primary_key=True, default="pt")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)


class Client(Base):
    """Cliente/marca como tabela, não mais texto solto no case.

    Antes o cliente era uma string digitada em cada case, então "Klabin",
    "klabin" e "Klabin S.A." viravam três clientes diferentes na hora de
    filtrar. Aqui ele é uma entidade: o case aponta para o registro, e mudar o
    nome num lugar muda em todos.
    """
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    site: Mapped[str] = mapped_column(String(300), default="")
    logo: Mapped[str] = mapped_column(String(300), default="")   # arquivo em uploads
    note: Mapped[str] = mapped_column(Text, default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)

    cases: Mapped[list["Case"]] = relationship(back_populates="client_ref")


class CaseView(Base):
    """Acessos por case e por dia.

    Guardado agregado, nunca visita a visita: para saber que um case teve 40
    acessos numa terça não é preciso registrar quem entrou, quando e de onde.
    Uma linha por case por dia, sem IP, sem identificador de pessoa.
    """
    __tablename__ = "case_views"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)      # AAAA-MM-DD
    hits: Mapped[int] = mapped_column(Integer, default=0)


class CaseComment(Base):
    """Comentário num case, moderado antes de aparecer.

    Nasce pendente sempre. Portfólio público com comentário aberto vira alvo de
    robô de spam em questão de dias, e um comentário indevido no case de um
    cliente é problema do cliente, não só meu.
    """
    __tablename__ = "case_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    case: Mapped["Case"] = relationship(back_populates="comments")
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), default="")   # nunca exibido
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pendente", index=True)  # pendente|aprovado|spam
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now)


# ------------------------------------------------------------ Redesign --

ESTADOS_REDESIGN = ("pitch", "publico", "aprovado")


def novo_token() -> str:
    """Endereço secreto de um pitch.

    `token_urlsafe(16)` dá 22 caracteres de 128 bits de entropia: curto o
    bastante para ser colado no WhatsApp e às vezes lido em voz alta, e longe
    demais de ser adivinhado.

    Opaco de propósito. Um token derivado do nome da marca deixaria de ser
    secreto no instante em que alguém lesse a URL por cima do ombro do dono.
    """
    import secrets

    return secrets.token_urlsafe(16)


class Redesign(Base):
    """Uma home refeita por conta própria, para mostrar e vender.

    POR QUE AQUI, E NÃO EM app/lab/models.py

    Todo modelo do Lab pendura em `sandbox_id` e some na limpeza diária,
    porque é dado de visitante que vive 24 horas. Um redesign é o oposto:
    conteúdo editorial do Leandro, permanente, irmão de `Case`. Ele mora no
    endereço /lab porque é lá que o visitante o encontra, e endereço não
    dita onde o dado vive.

    OS TRÊS ESTADOS (§6 da spec)

    `pitch`     só existe pelo token. O endereço público responde 404.
    `publico`   na vitrine e no sitemap. Marca grande, ou cliente que
                autorizou.
    `aprovado`  virou trabalho real: sai da vitrine e do sitemap, e o
                portfólio passa a ter o `Case`. A página continua servindo
                como registro de que aquilo começou como pitch.

    AS DUAS CAPTURAS

    Saem do mesmo `app/services/captura.py` que já fotografa o site de um
    case. O "antes" vem de `antes_url`, o "depois" vem da própria página do
    Leandro. A cortina da vitrine nunca desatualiza porque é recapturada.
    """

    __tablename__ = "redesigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    marca: Mapped[str] = mapped_column(String(200), default="")
    setor: Mapped[str] = mapped_column(String(120), default="")
    estado: Mapped[str] = mapped_column(String(20), default="pitch", index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # o site atual, de verdade
    antes_url: Mapped[str] = mapped_column(String(500), default="")
    antes_shot: Mapped[str] = mapped_column(String(300), default="")
    antes_shot_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # a página deste redesign, fotografada pelo mesmo serviço
    depois_shot: Mapped[str] = mapped_column(String(300), default="")
    depois_shot_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # o dossiê da §4, colhido do site original
    insumos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    insumos_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # texto do Leandro: o argumento, e o que falta perguntar
    diagnostico: Mapped[str] = mapped_column(Text, default="")
    pendencias: Mapped[str] = mapped_column(Text, default="")

    criado_em: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=now)
    enviado_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # carimbado na PRIMEIRA abertura por visitante de verdade. Ver a regra do
    # loopback em app/lab/rotas_sites.py: sem ela, a captura do "depois"
    # marcaria o cliente como tendo visto antes de o link ser enviado.
    visto_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)


class Activity(Base):
    """Tudo que acontece no painel e no site, em uma linha do tempo só.

    Serve para responder "o que mudou aqui?" sem ter que lembrar. Registra o
    que eu faço (criar, editar, arquivar, excluir) e o que o visitante faz
    (mensagem, lead, inscrição, comentário), porque as duas coisas competem
    pela mesma atenção quando se abre o painel.

    Guarda o texto já pronto, não o objeto: assim um case excluído continua
    aparecendo no histórico com o nome que tinha, em vez de virar uma linha
    órfã apontando para o nada.
    """
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    # o que aconteceu: criou|editou|publicou|arquivou|excluiu|recebeu
    verbo: Mapped[str] = mapped_column(String(20), index=True)
    # onde: case|categoria|cliente|mensagem|lead|newsletter|comentario|campanha
    area: Mapped[str] = mapped_column(String(24), index=True)
    titulo: Mapped[str] = mapped_column(String(220))
    detalhe: Mapped[str] = mapped_column(String(400), default="")
    url: Mapped[str] = mapped_column(String(300), default="")   # para onde levar o clique
    # do visitante ou meu: separa "alguém falou comigo" de "eu mexi em algo"
    do_site: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    lida: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
