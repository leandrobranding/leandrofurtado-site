"""Dados iniciais: admin, categorias e o currículo completo (bilíngue).

Tudo é editável depois no admin — datas/períodos ficam em branco para você preencher.
"""
import secrets

from sqlalchemy.orm import Session

from ..auth import hash_password
from ..config import settings
from ..models import Campaign, Category, LinkedInPost, Profile, SiteSetting, User

# O quarto valor é o tipo. "sites" muda o comportamento da categoria inteira:
# os itens não ganham página de case e o card mostra a prévia do endereço.
CATEGORIES = [
    ("key-visual", "Key Visual", "Key Visual", ""),
    ("branding", "Identidade Visual", "Branding", ""),
    ("campanha", "Campanhas", "Campaigns", ""),
    ("digital-ui", "Digital & UI", "Digital & UI", ""),
    ("motion-video", "Motion & Vídeo", "Motion & Video", ""),
    ("social-media", "Social Media", "Social Media", ""),
    ("fotografia", "Fotografia", "Photography", ""),
    ("sites", "Sites", "Websites", "sites"),
    ("ia-criativa", "IA Criativa", "Creative AI", ""),
]

PROFILE = {
    "name": "Leandro Furtado",
    "title_pt": "Engenheiro de IA e Diretor de Arte Sênior",
    "title_en": "AI Engineer & Senior Art Director",
    "location_pt": "Curitiba/PR - Brasil",
    "location_en": "Curitiba/PR - Brazil",
    "email": "contatoleandrofurtado@gmail.com",
    "links": {"linkedin": "https://www.linkedin.com/in/leandrofurtad/",
              "instagram": "https://instagram.com/leandrobranding",
              "whatsapp": "https://wa.me/5541996758984"},
    "summary_pt": (
        "Há mais de 10 anos construo marcas, campanhas e experiências visuais dentro de agências de "
        "publicidade em Curitiba. Minha atuação sempre teve um fio condutor: transformar conceito em "
        "algo que as pessoas realmente sintam: um key visual, uma interface digital ou uma "
        "ativação de marca ao vivo. Atuo na direção de arte de campanhas on e offline, na construção "
        "de identidades visuais do zero e na produção de interfaces digitais focadas em experiência do "
        "usuário, com experiência consolidada em fotografia comercial e editorial e gestão de equipes "
        "criativas em diferentes contextos. Nos últimos anos, passei a integrar inteligência artificial "
        "generativa ao meu fluxo de produção criativa, com ferramentas como Claude e modelos de geração "
        "de imagem, para acelerar conceituação, manter consistência visual de marca e reduzir tempo de "
        "entrega em projetos de Live Marketing. O que me move é trabalhar onde criatividade e "
        "tecnologia se encontram para gerar resultado real: não tecnologia pela tecnologia, mas como "
        "ferramenta que potencializa o que já sei fazer bem."
    ),
    "summary_en": (
        "For over 10 years I've been building brands, campaigns and visual experiences inside "
        "advertising agencies in Curitiba, Brazil. My work has always had one common thread: turning "
        "concept into something people actually feel: a key visual, a digital interface or "
        "a live brand activation. I art-direct on/offline campaigns, build visual identities from "
        "scratch and craft user-centred digital interfaces, with solid experience in commercial and "
        "editorial photography and creative team management. In recent years I've integrated "
        "generative AI into my creative production workflow, with tools like Claude and image "
        "generation models, to speed up concepting, keep brand consistency and cut delivery time in Live "
        "Marketing projects. What drives me is working where creativity and technology meet to "
        "generate real results: not technology for its own sake, but as a tool that amplifies craft."
    ),
    "highlight_pt": "Contar a história certa, da forma certa, para a marca certa. Onde criatividade e tecnologia se encontram.",
    "highlight_en": "Telling the right story, the right way, for the right brand. Where creativity and technology meet.",
    "experience": [
        {"company": "Gosh", "tags": ["Key Visual", "IA Generativa", "Live Marketing", "Direção de Arte", "Web"], "role_pt": "Diretor de Arte Sênior | Especialista em IA Generativa",
         "role_en": "Senior Art Director | Generative AI Specialist", "period": "Mar 2026 — Ago 2026",
         "desc_pt": "Live Marketing e ativações no segmento esportivo: liderança criativa em Key Visuals com unidade estética em todos os pontos de contato, integração de IA generativa no fluxo de produção (ativos visuais e vídeos com consistência de personagem e marca) e desenvolvimento web de alta performance orientado a conversão.",
         "desc_en": "Live Marketing and activations in the sports segment: creative leadership on Key Visuals with aesthetic unity across every touchpoint, generative AI integrated into the production workflow (visual assets and videos with character and brand consistency) and high-performance, conversion-driven web development."},
        {"company": "iOn live", "tags": ["Direção de Arte", "UI/UX", "Fotografia", "Motion", "IA Aplicada"], "role_pt": "Diretor de Arte Sênior e Fotógrafo",
         "role_en": "Senior Art Director & Photographer", "period": "Mar 2024 — Fev 2026",
         "desc_pt": "Conceitos visuais e desdobramentos estratégicos para campanhas on e offline, interfaces digitais (UI/UX), cobertura fotográfica de eventos corporativos e ativações, e edição avançada de foto e vídeo com IA no fluxo de trabalho.",
         "desc_en": "Visual concepts and strategic rollouts for on/offline campaigns, digital interfaces (UI/UX), photographic coverage of corporate events and brand activations, and advanced photo/video post-production with AI in the workflow."},
        {"company": "ATAIF Brasil", "tags": ["Branding", "Naming", "Identidade Visual", "PDV", "Go-to-market"], "role_pt": "Gerente de Desenvolvimento de Marca (Branding Manager)",
         "role_en": "Branding Manager", "period": "Out 2022 — Ago 2023",
         "desc_pt": "Gestão integral da marca ATAIF, primeira loja exclusiva de Qatayef (doce árabe) do mundo: naming, storytelling, identidade visual completa, PDV, embalagens e estratégia de go-to-market do lançamento em Curitiba.",
         "desc_en": "End-to-end management of the ATAIF brand, the world's first Qatayef-exclusive store: naming, storytelling, complete visual identity, POS, packaging and go-to-market strategy for the Curitiba launch."},
        {"company": "United Nations Volunteers (ONU)", "tags": ["Design Social", "Direção de Arte", "Voluntariado"], "role_pt": "Designer Voluntário",
         "role_en": "Volunteer Designer", "period": "2016 — 2022",
         "desc_pt": "Sete anos de direção de arte e design voluntário para escolas, hospitais e comunidades em vulnerabilidade ao redor do mundo, via UNV Online Volunteering.",
         "desc_en": "Seven years of volunteer art direction and design for schools, hospitals and vulnerable communities around the world, through UNV Online Volunteering."},
        {"company": "Explay Web Agency", "tags": ["UI/UX", "Web Design", "Landing Pages", "Performance"], "role_pt": "Diretor de Arte Sênior",
         "role_en": "Senior Art Director", "period": "Nov 2019 — Set 2021",
         "desc_pt": "UI/UX e direção de arte para sites complexos, landing pages focadas em conversão e performance criativa para tráfego pago. Clientes: Brainbox, Grupo OM, Aliança Francesa.",
         "desc_en": "UI/UX and art direction for complex websites, conversion-focused landing pages and creative performance for paid media. Clients: Brainbox, Grupo OM, Alliance Française."},
        {"company": "iProspect (Dentsu)", "tags": ["Campanhas 360°", "Key Visual", "Mídia Digital"], "role_pt": "Diretor de Arte Sênior",
         "role_en": "Senior Art Director", "period": "Ago 2018 — Jan 2019",
         "desc_pt": "Grandes contas na multinacional: campanha de lançamento do LIO+ da Cielo com Luciano Huck, key visual do site da Klabin e materiais digitais da Wap.",
         "desc_en": "Major accounts at the multinational: Cielo's LIO+ launch campaign with TV host Luciano Huck, Klabin's website key visual and Wap's digital assets."},
        {"company": "Pátio Batel", "tags": ["Fotografia", "Editorial", "Eventos", "Retrato"], "role_pt": "Fotógrafo Comercial (freelance)",
         "role_en": "Commercial Photographer (freelance)", "period": "Abr 2017 — Dez 2018",
         "desc_pt": "Fotografia oficial de eventos dos lojistas do shopping: lançamentos de coleção, desfiles e coquetéis, incluindo fotografia de produto para a Louis Vuitton e retrato de Donata Meirelles.",
         "desc_en": "Official event photography for the luxury mall's stores: collection launches, runway shows and receptions, including product photography for Louis Vuitton and a portrait of fashion icon Donata Meirelles."},
        {"company": "MegaMidia Group", "tags": ["Direção de Arte", "Social Media", "Campanhas"], "role_pt": "Diretor de Criação",
         "role_en": "Creative Director", "period": "Out 2017 — Ago 2018",
         "desc_pt": "Gestão completa da equipe de criação, planejamento estratégico digital e UI/App design para clientes corporativos. Clientes: Assaí Atacadista, Academia Assaí, MartMinas.",
         "desc_en": "Full creative team management, digital strategic planning and UI/app design for corporate clients. Clients: Assaí Atacadista, Academia Assaí, MartMinas."},
        {"company": "PontoCom Comunicação", "tags": ["Direção de Arte", "Campanhas"], "role_pt": "Diretor de Arte Pleno (freelance)",
         "role_en": "Art Director (freelance)", "period": "Ago 2017 — Out 2017",
         "desc_pt": "Key visuals para social media, landing pages e e-mail marketing sazonal. Clientes: Centro Europeu, Secovi/PR, Maxipas.",
         "desc_en": "Social media key visuals, landing pages and seasonal e-mail marketing. Clients: Centro Europeu, Secovi/PR, Maxipas."},
        {"company": "UmQuatroQuatro Comunicação", "tags": ["Direção de Arte", "Social Media"], "role_pt": "Diretor de Arte Pleno (freelance)",
         "role_en": "Art Director (freelance)", "period": "Jun 2016 — Ago 2016",
         "desc_pt": "Campanhas, key visuals para social media e cobertura fotográfica de eventos, incluindo o lançamento da Revista One.",
         "desc_en": "Campaigns, social media key visuals and event photography, including the launch of Revista One."},
        {"company": "Heads Propaganda", "tags": ["Direção de Arte", "Campanhas", "Key Visual"], "role_pt": "Diretor de Arte Pleno",
         "role_en": "Art Director", "period": "Dez 2015 — Mai 2016",
         "desc_pt": "Key visuals e desdobramentos digitais de campanhas. Clientes: Caixa Econômica Federal (campanha de Natal), Caixa Seguradora, Copel Telecom.",
         "desc_en": "Key visuals and digital campaign rollouts. Clients: Caixa Econômica Federal (Christmas campaign), Caixa Seguradora, Copel Telecom."},
        {"company": "Grupo Excom", "tags": ["Direção de Arte", "Campanhas", "Branding", "Prêmio ADVB"], "role_pt": "Diretor de Arte Júnior",
         "role_en": "Junior Art Director", "period": "Jun 2015 — Dez 2015",
         "desc_pt": "Gestão de equipe de criação e social media de clientes. Case VCG Empreendimentos (Parque das Artes), vencedor do Top de Marketing ADVB/PR 2015.",
         "desc_en": "Creative team management and client social media. The VCG Empreendimentos case (Parque das Artes) won the ADVB/PR Top de Marketing 2015 award."},
        {"company": "Grupo Excom", "tags": ["Direção de Arte", "Campanhas", "Branding", "Prêmio ADVB"], "role_pt": "Designer",
         "role_en": "Designer", "period": "Fev 2014 — Jun 2015",
         "desc_pt": "Campanhas digitais, key visuals e desdobramentos de materiais de agências parceiras.",
         "desc_en": "Digital campaigns, key visuals and asset rollouts for partner agencies."},
    ],
    # Formação acadêmica (item novo do dono, 19/08 — dados reais transcritos
    # do LinkedIn dele). Curiosidade que vale o peso da seção: a formação já
    # inclui Web/Digital (UTFPR) — reforça o reposicionamento como dev, não
    # é só o currículo recente que aponta pra lá. Período compartilhado
    # (sem _pt/_en), mesma convenção de experience.period; instituição e
    # curso têm o par bilíngue porque o nome oficial muda mesmo de idioma.
    "education": [
        {"institution_pt": "Universidade Tecnológica Federal do Paraná",
         "institution_en": "Federal University of Technology – Paraná",
         "course_pt": "Ensino Técnico — Web Page, Digital/Multimedia and Information Resources Design",
         "course_en": "Technical Degree — Web Page, Digital/Multimedia and Information Resources Design",
         "period": "Jan 2007 — Dez 2009"},
        {"institution_pt": "Centro Universitário Adventista de São Paulo",
         "institution_en": "São Paulo Adventist University Center",
         "course_pt": "Comunicação Social — Publicidade e Propaganda",
         "course_en": "Social Communication — Advertising",
         "period": "Jan 2010 — Dez 2013"},
    ],
    # Nomenclaturas encurtadas na rodada 2 (19/08, item 3): o pedido foi
    # "diagrame as tags de modo que fique harmônica a altura das mesmas,
    # nem que você tenha que alterar as nomenclaturas" — o grupo "IA
    # Aplicada" tem quase o dobro de itens dos outros e frases bem mais
    # longas, o que empurrava a altura das colunas do `.skills-grid` para
    # bem longe uma da outra. Ver RENOMEIA_TAGS logo abaixo: a mesma troca
    # é aplicada a um Perfil que já existia no banco, não só a instalação
    # nova.
    "skills": [
        {"group_pt": "IA Aplicada", "group_en": "Applied AI",
         "items": ["Claude", "Geração de Imagem", "Prompt Engineering", "Brainstorm com IA",
                   "Engenharia de Código", "Sistemas Complexos",
                   "Python", "CSS aplicado", "HTML", "Fluxos com IA"]},
        {"group_pt": "Direção & Estratégia", "group_en": "Direction & Strategy",
         "items": ["Direção de Arte", "Direção de Criação", "Branding", "Key Visual", "Campanhas 360°", "Live Marketing", "Go-to-Market", "Liderança de Equipes"]},
        {"group_pt": "Design & Digital", "group_en": "Design & Digital",
         "items": ["Identidade Visual", "UI/UX Design", "Landing Pages", "Social Media", "Editorial", "Fotografia & Eventos"]},
        {"group_pt": "Motion & Web", "group_en": "Motion & Web",
         "items": ["Motion Design", "Vídeo", "Dev Web", "WordPress", "HTML/CSS/JS"]},
    ],
    "awards": [
        {"title_pt": "Top de Marketing ADVB/PR", "title_en": "ADVB/PR Top de Marketing Award", "year": "2015",
         "desc_pt": "Case VCG Empreendimentos (Parque das Artes), pelo Grupo Excom. Emitido pela Associação dos Dirigentes de Vendas e Marketing do Brasil.",
         "desc_en": "VCG Empreendimentos case (Parque das Artes), with Grupo Excom. Issued by the Brazilian Sales & Marketing Executives Association."},
    ],
    "certs": [
        {"title": "Claude 101 - LLM", "org": "Anthropic", "year": "2026",
         "code": "NGRD3JR7O2IO", "url": ""},
        {"title": "Direitos Autorais na Produção de Material Didático", "org": "FGV", "year": "2025",
         "code": "14558447.22184.OCWDAPEAD_1-1", "url": ""},
        {"title": "Google AI Essentials", "org": "Google", "year": "2024", "code": "", "url": ""},
        {"title": "Google AI Ethics", "org": "Google", "year": "2024", "code": "", "url": ""},
        {"title": "Google AI Prompts", "org": "Google", "year": "2024", "code": "", "url": ""},
        {"title": "Google AI Curve", "org": "Google", "year": "2024", "code": "", "url": ""},
    ],
    "photo": "",
    "clients": ["Coca-Cola", "Electrolux", "Hospital Marcelino Champagnat", "MadeiraMadeira"],
}

# Newsletter de boas-vindas (item 2 do pacote de lançamento, 19/08). Mesmo
# motor da newsletter que já funciona em produção — Markdown vira HTML pelo
# mesmo mailer.markdown_to_email() que a campanha em massa usa — só que
# disparada sozinha para quem acabou de assinar (ver
# app/routers/public.py:_enviar_boas_vindas).
# Marcador estável de "esta é a campanha de boas-vindas do site" — ver o
# comentário de Campaign.origem em app/models.py. Não é o assunto
# (WELCOME_SUBJECT) porque o dono pode editar o assunto livremente depois de
# criada, e o critério de "já existe?" não pode depender de um texto editável
# — se dependesse, editar o assunto faria a seed achar que a campanha não
# existe mais e criar uma segunda.
WELCOME_ORIGIN = "site_welcome"

WELCOME_SUBJECT = "Seja bem-vindo(a) à lista"
WELCOME_PREHEADER = ("Direção de arte, branding e IA aplicada à criação, direto da mesa "
                     "pra sua caixa de entrada.")
WELCOME_BODY = """## Que bom te ter por aqui

Eu sou o Leandro: diretor de arte sênior há mais de 10 anos, e nos últimos
tempos também engenheiro de IA — na prática, não em teoria de LinkedIn.

A partir de agora chega novidade direto de mim: case novo no ar, bastidor de
como uso IA generativa sem abrir mão do olho de quem desenha marca há mais de
uma década, e aviso em primeira mão do que estou construindo (tem coisa
grande a caminho).

**Nada de fórmula de "cresça 10x" nem textão de guru.** Se um e-mail meu não
tiver nada de verdade pra te mostrar, ele simplesmente não sai.

> Quer trocar ideia, mandar um case seu ou só dizer oi? Responde este
> e-mail — do outro lado tem eu, não um bot.
"""

# Rodada 2 (19/08, item 3): mesma troca de nome aplicada às tags de um Perfil
# que já existia no banco (produção), não só à instalação nova — ver o `else`
# em run_seeds(). Chave é o nome antigo, valor o novo; só troca texto, a
# tag continua reconhecida pelos ícones de sk_icon() em about.html.
#
# Rodada 3 (19/08, item 9): "Liderança Criativa" e "Fotografia Comercial" —
# nomes que a própria rodada 2 introduziu — levaram objeção na revisão
# (perdiam palavra-chave de recrutamento) e o coordenador trocou de novo,
# para "Liderança de Equipes" e "Fotografia & Eventos". Cada lookup aqui é
# de um hop só (`RENOMEIA_TAGS.get(item, item)`, sem encadear), então os
# dois nomes que já existiram em produção — o ORIGINAL de antes da rodada 2
# e o INTERMEDIÁRIO que ela deixou — precisam apontar direto para o nome
# final, sem elo perdido no meio da cadeia.
RENOMEIA_TAGS = {
    "Geração de imagem (difusão)": "Geração de Imagem",
    "Organização e engenharia de código": "Engenharia de Código",
    "Criação complexa de sistemas": "Sistemas Complexos",
    "Fluxos criativos com IA": "Fluxos com IA",
    "Liderança de equipes criativas": "Liderança de Equipes",   # original (pré-rodada 2)
    "Liderança Criativa": "Liderança de Equipes",                # intermediário (rodada 2)
    "Fotografia comercial e de eventos": "Fotografia & Eventos",  # original (pré-rodada 2)
    "Fotografia Comercial": "Fotografia & Eventos",               # intermediário (rodada 2)
    # Esta troca não é por comprimento médio do grupo, e sim porque a tag
    # sozinha (202,9px no layout medido ao vivo) já não cabia na coluna mais
    # estreita do `.skills-grid` sem quebrar em duas linhas no meio da
    # palavra — o único chip “gordo” dentro de uma fileira de chips finos.
    "Desenvolvimento Web": "Dev Web",
}

DEFAULT_SETTINGS = {
    "ig_user_id": "", "ig_access_token": "", "ig_auto_publish": "0",
    "social_instagram": "https://instagram.com/leandrobranding",
    "social_facebook": "https://facebook.com/leandrobranding",
    "social_github": "https://github.com/leandrobranding",
    "social_linkedin": "https://www.linkedin.com/in/leandrofurtad/",
    "social_whatsapp": "https://wa.me/5541996758984",
    "contact_email": "contatoleandrofurtado@gmail.com",
    "cnpj": "59.375.755/0001-13",
    "analytics_head": "",
    "smtp_host": "", "smtp_port": "587", "smtp_user": "", "smtp_password": "",
    "smtp_from": "", "lead_email": "contatoleandrofurtado@gmail.com",
    # Barra animada antes de "vamos conversar" (item 8, 19/08): uma
    # palavra/frase por linha, editável em Configurações → Geral. Os valores
    # abaixo são os que já estavam fixos no template.
    "marquee_words_pt": "Key Visual\nBranding\nCampanhas\nUI Design\nMotion\nFotografia\nSocial Media\nWeb\nIA Criativa",
    "marquee_words_en": "Key Visual\nBranding\nCampaigns\nUI Design\nMotion\nPhotography\nSocial Media\nWeb\nCreative AI",
}


def run_seeds(db: Session) -> None:
    if not db.query(User).first():
        password = settings.admin_password or secrets.token_urlsafe(12)
        db.add(User(username=settings.admin_username, password_hash=hash_password(password)))
        if not settings.admin_password:
            cred = settings.data_dir / "ADMIN_CREDENTIALS.txt"
            cred.write_text(
                "Credenciais do admin (troque a senha no painel depois do primeiro login):\n"
                f"usuário: {settings.admin_username}\nsenha: {password}\n"
            )
            cred.chmod(0o600)

    if not db.query(Category).first():
        for i, (slug, pt, en, kind) in enumerate(CATEGORIES):
            db.add(Category(slug=slug, name_pt=pt, name_en=en, sort=i, kind=kind))
    else:
        # Banco que já existia: a antiga "Web" vira "Sites" e ganha o tipo. Os
        # tipos são recolocados sempre, porque é o código que manda neles, não
        # o banco: sem isto, um servidor que subiu antes desta versão ficaria
        # com a categoria certa e o comportamento errado.
        antiga = db.query(Category).filter_by(slug="web").first()
        if antiga and not db.query(Category).filter_by(slug="sites").first():
            antiga.slug, antiga.name_pt, antiga.name_en = "sites", "Sites", "Websites"
        for slug, pt, en, kind in CATEGORIES:
            cat = db.query(Category).filter_by(slug=slug).first()
            if cat and cat.kind != kind:
                cat.kind = kind

    # Clientes que existiam como texto solto viram registros, uma vez só. O
    # texto continua no case (nada que lê case.client quebra), mas agora há um
    # dono: renomear o cliente passa a valer para todos os cases dele.
    from ..models import Case as _Case, Client as _Client
    from .images import slugify as _slug
    nomes = {c.client.strip() for c in db.query(_Case).all() if (c.client or "").strip()}
    perfil = db.query(Profile).first()
    if perfil:
        nomes |= {n.strip() for n in (perfil.data or {}).get("clients", []) if n and n.strip()}
    for i, nome in enumerate(sorted(nomes)):
        chave = _slug(nome)
        if chave and not db.query(_Client).filter_by(slug=chave).first():
            db.add(_Client(slug=chave, name=nome, sort=i))
    db.flush()
    por_slug = {c.slug: c for c in db.query(_Client).all()}
    for case in db.query(_Case).filter(_Case.client_id.is_(None)).all():
        alvo_cli = por_slug.get(_slug(case.client or ""))
        if alvo_cli:
            case.client_id = alvo_cli.id

    if not db.query(Profile).first():
        db.add(Profile(id=1, data=PROFILE))
    else:
        # Perfil que já existia no banco (produção): recebe só o renomeio das
        # tags de habilidade (RENOMEIA_TAGS), idempotente e sem tocar em mais
        # nada do conteúdo já editado no admin.
        perfil = db.query(Profile).first()
        dados = dict(perfil.data or {})
        skills = dados.get("skills")
        if skills:
            mudou = False
            novos_grupos = []
            for grupo in skills:
                itens = grupo.get("items") or []
                novos_itens = [RENOMEIA_TAGS.get(item, item) for item in itens]
                if novos_itens != itens:
                    mudou = True
                novos_grupos.append({**grupo, "items": novos_itens})
            if mudou:
                dados["skills"] = novos_grupos
                perfil.data = dados

        # Formação acadêmica (item novo, 19/08): campo que não existia antes
        # em NENHUM Profile, nem no seed antigo — backfill de uma vez só,
        # só quando a chave está totalmente ausente. Depois da primeira vez
        # (mesmo que o admin edite ou esvazie a lista dele), a chave passa a
        # existir e este bloco nunca mais mexe nela — aditivo de verdade,
        # não reimpõe o dado de novo a cada `run_seeds`.
        if "education" not in dados:
            dados["education"] = PROFILE["education"]
            perfil.data = dados

    # Newsletter de boas-vindas: aditiva e idempotente. O critério de "já
    # existe?" é `origem == WELCOME_ORIGIN`, não `is_welcome=True` — o banco
    # de produção já tinha uma campanha com is_welcome=1 antes desta seed
    # existir (a da página de construção, mecanismo antigo), e o critério
    # antigo achava essa campanha e nunca criava a do site: ela ficava
    # invisível no admin, e quem assinasse a newsletter recebia o e-mail de
    # construção como boas-vindas. Depois que a campanha do site existe, esta
    # seed nunca mais toca nela — nem em is_welcome, mesmo que o dono tenha
    # desmarcado no admin — para não pisar em edição alguma.
    if not db.query(Campaign).filter_by(origem=WELCOME_ORIGIN).first():
        perfil = db.query(Profile).first()
        imagem_perfil = (perfil.data or {}).get("cover") or (perfil.data or {}).get("photo") if perfil else ""
        base = settings.base_url.rstrip("/")
        imagem = f"{base}/media/{imagem_perfil}" if imagem_perfil else f"{base}/static/img/og-default.png"
        # Só uma boas-vindas por vez (mesma invariante que o admin já impõe em
        # admin_nl.py ao marcar a caixinha): qualquer outra campanha que
        # estivesse com is_welcome=True — a de construção, no caso de
        # produção — é rebaixada, mas fica intacta em tudo o mais. Histórico
        # preservado, só perde a flag que não faz mais sentido nela.
        for outra in db.query(Campaign).filter(Campaign.is_welcome.is_(True)).all():
            outra.is_welcome = False
        db.add(Campaign(
            subject=WELCOME_SUBJECT,
            preheader=WELCOME_PREHEADER,
            body=WELCOME_BODY,
            image=imagem,
            cta_label="Ver o portfólio",
            cta_url=f"{base}/portfolio",
            audience="assinantes",
            is_welcome=True,
            status="rascunho",
            origem=WELCOME_ORIGIN,
        ))

    # Posts de demonstração do LinkedIn (troque pelos reais em Admin → LinkedIn).
    if not db.query(LinkedInPost).first():
        profile_url = DEFAULT_SETTINGS["social_linkedin"]
        for tag, summary in [
            ("#IAnaCriação", "Como incorporei IA generativa ao fluxo de criação sem perder a assinatura visual da marca, e por que curadoria virou a habilidade mais importante do diretor de arte."),
            ("#LiveMarketing", "Bastidores de uma ativação: do conceito aprovado em mockup de IA à execução física no evento. O que mudou no prazo e no orçamento."),
            ("#DireçãoDeArte", "Key Visual não é uma imagem bonita, é um sistema. Como estruturo KVs que desdobram para OOH, social e palco sem perder força."),
            ("#Branding", "Identidade visual que sobrevive ao mundo real: os 3 testes que aplico antes de aprovar qualquer sistema de marca."),
            ("#Publicidade", "O que 10 anos de agência me ensinaram sobre apresentar criação para cliente, e como a IA mudou a etapa de vendas da ideia."),
            ("#Fotografia", "Direção de fotografia comercial: o que muda quando você fotografa para uma marca de luxo versus varejo."),
        ]:
            db.add(LinkedInPost(summary=summary, tag=tag, url=profile_url))

    existing = {s.key for s in db.query(SiteSetting).all()}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.add(SiteSetting(key=key, value=value))

    db.commit()
