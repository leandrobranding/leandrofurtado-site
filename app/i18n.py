"""Bilíngue PT-BR (padrão) / EN via prefixo /en. Helpers usados nos templates."""

STRINGS = {
    "pt": {
        "work": "Portfólio", "about": "Sobre", "contact": "Contato", "cv": "Currículo",
        "featured": "Cases em destaque", "all_work": "Todos os cases", "view_case": "Ver case",
        "next_case": "Próximo case", "all": "Todos", "filter_by": "Filtrar",
        "get_in_touch": "Vamos conversar", "send": "Enviar mensagem", "name": "Nome",
        "email": "E-mail", "message": "Mensagem", "sent_ok": "Mensagem enviada. Obrigado!",
        "role": "Papel", "client": "Cliente", "year": "Ano", "category": "Categoria",
        "tags_label": "Tags", "ia_label": "Inteligência artificial",
        "experience": "Experiência", "education": "Formação acadêmica", "skills": "Habilidades", "awards": "Prêmios",
        "certs": "Certificações", "clients_brands": "Marcas & clientes", "clients_served": "Marcas e clientes que atendi",
        "download_cv": "Baixar currículo (PDF)", "open_to_work": "Disponível para projetos",
        "not_found": "Página não encontrada", "back_home": "Voltar ao início",
        "scroll": "Role para explorar", "based_in": "Curitiba ·︎ Brasil",
        "you_are_in": "Você está em", "somewhere": "Em algum lugar do mundo",
        "site_theme": "Engenharia de IA e Direção de Arte, do conceito ao código.",
        "welcome_kicker": "Seja bem-vindo(a) ao meu site.",
        "portfolio_sub": "Cases de direção de arte, branding, campanhas, UI, motion e IA generativa. Cada projeto, uma história contada do conceito ao código.",
        "filter_cat": "Categoria", "cases_label": "cases",
        "order_by": "Ordenar", "order_recent": "Recentes",
        "order_az": "A →︎ Z", "order_za": "Z →︎ A",
        "view_hint": "Escolha como quer visualizar os cases",
        "view_hint_sites": "Escolha como quer visualizar os sites",
        "view_hint_cliente": "Escolha como quer visualizar os projetos desse cliente",
        "showing": "Exibindo", "of_total": "de", "page_label": "Página",
        "prev_page": "Anterior", "next_page": "Próxima",
        "results_found": "resultados encontrados",
        "result_found": "resultado encontrado",
        "start_project": "Iniciar projeto", "selected_work": "Cases em destaque",
        "see_all_work": "Ver o portfólio completo", "summary": "Resumo",
        "privacy": "Política de Privacidade", "sitemap_page": "Mapa do site",
        "cta_band": "Tem um projeto em mente?", "talk_whatsapp": "Chamar no WhatsApp",
        "wip_eyebrow": "Em construção",
        "wip_title": "Está vindo algo f#da!",
        "wip_role": "Prazer, Leandro, sou engenheiro de IA e diretor de arte sênior.",
        "wip_text": ("Este site está sendo construído com calma, case por case, porque prefiro "
                     "mostrar trabalho de verdade a encher a página de qualquer coisa. "
                     "Enquanto isso, falo com você pelo LinkedIn ou pelo WhatsApp."),
        "wip_progress": "do site pronto",
        "wip_nl_title": "Quer saber quando fica pronto?",
        "wip_nl_desc": "Deixe seu e-mail e eu aviso na hora que o portfólio entrar no ar. Sem spam, prometo.",
        "wip_consent": ("Autorizo o cadastro do meu e-mail e o envio de novidades do site, conforme "
                        "a LGPD e o GDPR. Posso sair da lista quando quiser."),
        "wip_consent_req": "Marque o aceite para eu poder te avisar.",
        "nl_sending_1": "Guardando seu e-mail…",
        "nl_sending_2": "Confirmando o cadastro…",
        "nl_sending_3": "Quase lá…",
        "nl_sending_done": "Obrigado por se inscrever!",
        "nl_ok_text": ("Fica de olho em seu e-mail que eu aviso na hora quando o site "
                       "entrar no ar. Sem spam, prometo!"),
        "nl_ok_bye": "Um abraço, jovem!",
        "nl_ja": "Ei, você já se cadastrou jovem!",
        "nl_ja_text": "Em breve você terá novidades em seu e-mail. Fique de olho!",
        "nl_ja_bye": "Um abraço,",
        "nl_invalido": "Esse e-mail não parece certo. Confere e tenta de novo?",
        "unsub_titulo": "Poxa, que pena",
        "unsub_texto": "Sinto muito que você não queira mais receber meus e-mails.",
        "unsub_porta": "Se quiser voltar, sem ressentimentos, a porta fica aberta.",
        "unsub_abraco": "Um abraço,",
        "unsub_erro_titulo": "Link inválido",
        "unsub_erro_texto": ("Esse link de cancelamento não confere. Se quiser sair da lista, "
                             "me escreva que eu removo na hora."),

        "wip_signature": "Curitiba/PR, Brasil",
        "wip_meta_desc": ("Portfólio de Leandro Furtado, engenheiro de IA e diretor de arte "
                          "sênior em Curitiba. O site está em construção: deixe seu e-mail e "
                          "seja avisado quando os cases entrarem no ar."),
        "nl_title": "Fique por dentro",
        "nl_desc": "Cases novos e experimentos com IA direto no seu e-mail.",
        "nl_placeholder": "seu@email.com", "nl_btn": "Assinar", "nl_ok": "Obrigado por se inscrever!",
        "col_site": "Site", "col_social": "Social Media", "col_legal": "Aspectos Legais",
        "read_more": "Ler mais", "li_latest": "Últimas no LinkedIn",
        "unique_brands": "Marcas que realizei projetos únicos", "see_all": "Ver todas",
        "hall_title": "Galeria de Honra",
        "hall_desc": "Marcas que confiaram em projetos únicos de direção de arte, branding, campanhas e fotografia.",
        # Célula-convite que fecha a última linha da grade quando sobra vaga
        # (item 2, 19/08) — discreta, não um anúncio.
        "hall_invite": "Sua marca aqui",
        # 79 caracteres cortavam em ~60 no Google e "Curitiba" nunca aparecia
        # (medido no SERP em 22/08/2026). Sai "Sênior", que só interessa a quem
        # já chegou; fica a cidade, que é o que traz gente nova. O cargo completo
        # continua no /about e no jobTitle do JSON-LD.
        #
        # 24/08/2026: a ordem inverteu. "Diretor de Arte e IA" vinha de quando o
        # site era portfólio de direção de arte; hoje o alvo é vaga de
        # engenharia, e o título é o único lugar onde a ordem antiga tinha
        # sobrado. A direção de arte não sai do site: continua na descrição,
        # em toda página de case e no /about. Sai só da primeira linha.
        "meta_title": "Leandro Furtado ·︎ Engenheiro de IA e Dev em Curitiba",
        "cookie_msg": "Este site usa apenas cookies essenciais e guarda sua preferência de tema no navegador.",
        "cookie_ok": "Entendi", "legal": "Legal",
        # Banner de consentimento (LGPD, opt-in real): duas ações do mesmo peso
        # visual, decidido no servidor — ver ConstructionMiddleware/render() em
        # app/main.py e a rota /consentimento em app/routers/public.py.
        "an_consent_msg": ("Uso cookies essenciais para o site funcionar. Com sua permissão, "
                           "uso também cookies de análise (Google Tag Manager) para entender "
                           "como o site é usado."),
        "an_consent_accept": "Aceitar análise",
        "an_consent_essential": "Só o essencial",
        "an_consent_change": "mudar minha escolha",
        "an_consent_section_title": "3.2. Análise de audiência (com sua permissão)",
        "an_consent_section_body": ("Só entram em ação quando você clica em \"Aceitar análise\" "
                                    "no aviso de cookies. Recusar não bloqueia nada do site."),
        "sending_1": "Enviando sua mensagem…",
        "sending_2": "Registrando seu contato com segurança…",
        "sending_3": "Avisando o Leandro…",
        "sending_done": "Mensagem enviada!",
        "contact_title": "Vamos conversar?",
        "contact_sub": "Conta o que você tem em mente: uma marca para construir, uma campanha para dirigir, uma interface para desenhar ou um fluxo criativo para acelerar com IA. Respondo pessoalmente, com uma leitura honesta do que dá para fazer.",
        # Meta separada do texto da página: a de cima é boa como leitura e
        # longa demais para o SERP, onde o corte vem aos ~155 caracteres.
        "contact_meta": "Uma marca para construir, uma campanha para dirigir ou um fluxo criativo para acelerar com IA. Resposta pessoal, com leitura honesta do que dá para fazer.",
        "leave_message": "Deixe aqui sua mensagem",
        "message_hint": "Fale do projeto, do prazo e do que precisa acontecer. Quanto mais contexto, melhor a primeira resposta.",
        "phone": "Telefone",
        "consent_label": "Autorizo o contato e o tratamento dos meus dados para retorno desta mensagem e cadastro como contato, conforme a LGPD (Lei 13.709/2018) e o GDPR (UE 2016/679). Posso pedir acesso, correção ou exclusão quando quiser. Veja a",
        "consent_required": "Para enviar, é preciso autorizar o tratamento dos dados.",
        "form_error": "Faltou preencher nome, e-mail ou mensagem.",
        "sent_detail": "Recebi seus dados e respondo em breve, normalmente em até 1 dia útil.",
        "reply_time": "Resposta em até 1 dia útil ·︎ seus dados não são compartilhados com terceiros",
        "search": "Buscar", "search_placeholder": "Busque cases, skills, páginas…",
        "search_hint": "Digite, fale ou envie uma imagem para a IA analisar",
        "search_no_results": "Nada encontrado para",
        "search_listening": "Ouvindo… pode falar",
        "search_analyzing": "Comparando com os cases…",
        "search_img_kw": "Cases parecidos com a sua imagem",
        "search_ai_off": "Não achei nada parecido com essa imagem. Tente por texto ou voz.",
        "search_voice_off": "Busca por voz não é suportada neste navegador.",
        "voice_title": "Pode falar",
        "voice_sub": "Diga o que procura. O texto aparece aqui enquanto você fala.",
        "voice_wait": "Preparando o microfone…",
        "voice_use": "Buscar isto",
        "voice_cancel": "Cancelar",
        "voice_again": "Falar de novo",
        "voice_denied": "O microfone foi bloqueado. Libere o acesso na barra do navegador e tente de novo.",
        "voice_nothing": "Não consegui ouvir nada. Tente de novo, mais perto do microfone.",
        "voice_done": "Pronto. Confira o texto e busque.",
        "img_title": "Buscar por imagem",
        "img_sub": "A comparação roda aqui no servidor, sem IA e sem enviar a imagem para ninguém.",
        "img_drop": "Arraste uma imagem para cá ou",
        "img_pick": "escolha um arquivo",
        "img_or": "ou",
        "img_url_ph": "Cole o link de uma imagem",
        "img_err_esquema": "Esse endereço não é uma página da web.",
        "img_err_privado": "Esse endereço aponta para dentro de uma rede, não para a internet.",
        "img_err_host": "Não encontrei esse endereço.",
        "img_err_tipo": "O link não é de uma imagem.",
        "img_err_tamanho": "A imagem passa de 8 MB.",
        "img_err_resposta": "Não consegui baixar essa imagem.",
        "share_case": "Compartilhar case", "copy_link": "Copiar link", "link_copied": "Link copiado!",
        "share_prompt": "Achou interessante esse case? Compartilhe",
        "like_case": "Curtiu esse case?", "related_cases": "Cases relacionados",
        "back_to_work": "Voltar para o portfólio", "see_case": "Ver case",
        "see_site": "Ver site", "open_site": "Abrir site", "next_site": "Próximo site",
        "view_mode": "Visualização", "view_editorial": "Editorial", "view_grid": "Grade",
        "view_masonry": "Masonry",
        "client_everything": "Tudo o que foi feito para", "client_projects": "projetos",
        "review_cta": "Deixe sua avaliação", "review_on": "no Google",
        "secure_title": "Conexão segura",
        # Cada item é medido e conferível por quem quiser: TLS 1.3 no handshake,
        # HSTS de dois anos, CSP e o consentimento real no cookie. Selo de
        # terceiro (Norton, McAfee) afirma auditoria que este site não tem;
        # este afirma só o que é verdade, em nome próprio.
        "secure_detail": "TLS 1.3 ·︎ HSTS ·︎ CSP ·︎ LGPD",
        "zoom_img": "Zoom", "fullscreen_img": "Tela cheia",
        "other_clients": "Veja o que foi feito para outros clientes",
        "see_all_clients": "Ver todos os clientes",
        "client_empty": "Os cases deste cliente chegam em breve.",
        # 224 caracteres viravam ~155 no SERP: sumiam "IA generativa" e "+10 anos".
        # Além disso abria repetindo o nome, que já está no título logo acima, e
        # seguia como lista de palavras separadas por vírgula — o Google reescreve
        # descrições assim, e aí se perde o controle do texto. Esta cabe inteira e
        # gasta o espaço com prova, não com palavra-chave.
        "meta_desc": "Engenharia de IA e direção de arte no mesmo par de mãos. Python, FastAPI e sistemas em produção. Direção criativa e branding para Coca-Cola e Bradesco.",
    },
    "en": {
        "work": "Portfolio", "about": "About", "contact": "Contact", "cv": "Résumé",
        "featured": "Featured cases", "all_work": "All cases", "view_case": "View case",
        "next_case": "Next case", "all": "All", "filter_by": "Filter",
        "get_in_touch": "Let's talk", "send": "Send message", "name": "Name",
        "email": "Email", "message": "Message", "sent_ok": "Message sent. Thank you!",
        "role": "Role", "client": "Client", "year": "Year", "category": "Category",
        "tags_label": "Tags", "ia_label": "Artificial intelligence",
        "experience": "Experience", "education": "Education", "skills": "Skills", "awards": "Awards",
        "certs": "Certifications", "clients_brands": "Brands & clients", "clients_served": "Brands and clients I served",
        "download_cv": "Download résumé (PDF)", "open_to_work": "Open to projects",
        "not_found": "Page not found", "back_home": "Back home",
        "scroll": "Scroll to explore", "based_in": "Curitiba ·︎ Brazil",
        "you_are_in": "You are in", "somewhere": "Somewhere in the world",
        "site_theme": "AI Engineering & Art Direction, from concept to code.",
        "welcome_kicker": "Welcome to my site.",
        "portfolio_sub": "Cases in art direction, branding, campaigns, UI, motion and generative AI. Every project, a story told from concept to code.",
        "filter_cat": "Category", "cases_label": "cases",
        "order_by": "Sort", "order_recent": "Recent",
        "order_az": "A →︎ Z", "order_za": "Z →︎ A",
        "view_hint": "Choose how you want to view the cases",
        "view_hint_sites": "Choose how you want to view the sites",
        "view_hint_cliente": "Choose how you want to view this client's projects",
        "showing": "Showing", "of_total": "of", "page_label": "Page",
        "prev_page": "Previous", "next_page": "Next",
        "results_found": "results found",
        "result_found": "result found",
        "start_project": "Start a project", "selected_work": "Selected cases",
        "see_all_work": "See the full portfolio", "summary": "Summary",
        "privacy": "Privacy Policy", "sitemap_page": "Sitemap",
        "cta_band": "Have a project in mind?", "talk_whatsapp": "Chat on WhatsApp",
        "wip_eyebrow": "Under construction",
        "wip_title": "Something damn good is coming!",
        "wip_role": "Nice to meet you, I am Leandro, AI engineer and senior art director.",
        "wip_text": ("This site is being built slowly, case by case, because I would rather "
                     "show real work than fill the page with anything. "
                     "In the meantime, reach me on LinkedIn or WhatsApp."),
        "wip_progress": "of the site is done",
        "wip_nl_title": "Want to know when it is ready?",
        "wip_nl_desc": "Leave your email and I will tell you the moment the portfolio goes live. No spam, promise.",
        "wip_consent": ("I authorize registering my email and receiving site updates, under "
                        "LGPD and GDPR. I can leave the list whenever I want."),
        "wip_consent_req": "Tick the box so I can let you know.",
        "nl_sending_1": "Saving your email…",
        "nl_sending_2": "Confirming your signup…",
        "nl_sending_3": "Almost there…",
        "nl_sending_done": "Thanks for subscribing!",
        "nl_ok_text": ("Keep an eye on your inbox: I will tell you the moment the site "
                       "goes live. No spam, promise!"),
        "nl_ok_bye": "A hug, young one!",
        "nl_ja": "Hey, you are already in!",
        "nl_ja_text": "News is coming to your inbox soon. Keep an eye out!",
        "nl_ja_bye": "A hug,",
        "nl_invalido": "That email does not look right. Mind checking it?",
        "unsub_titulo": "Well, that is a shame",
        "unsub_texto": "Sorry to hear you do not want my emails anymore.",
        "unsub_porta": "If you ever want to come back, no hard feelings, the door stays open.",
        "unsub_abraco": "A hug,",
        "unsub_erro_titulo": "Invalid link",
        "unsub_erro_texto": ("This unsubscribe link does not check out. Write to me and I will "
                             "remove you right away."),

        "wip_signature": "Curitiba/PR, Brazil",
        "wip_meta_desc": ("Portfolio of Leandro Furtado, AI engineer and senior art director "
                          "in Curitiba, Brazil. The site is under construction: leave your "
                          "email and be the first to know when the cases go live."),
        "nl_title": "Stay in the loop",
        "nl_desc": "New cases and AI experiments straight to your inbox.",
        "nl_placeholder": "you@email.com", "nl_btn": "Subscribe", "nl_ok": "Thanks for subscribing!",
        "col_site": "Site", "col_social": "Social Media", "col_legal": "Legal",
        "read_more": "Read more", "li_latest": "Latest on LinkedIn",
        "unique_brands": "Brands I've built unique projects for", "see_all": "See all",
        "hall_title": "Hall of Honor",
        "hall_desc": "Brands that trusted unique projects in art direction, branding, campaigns and photography.",
        "hall_invite": "Your brand here",
        "meta_title": "Leandro Furtado ·︎ AI Engineer & Developer ·︎ Brazil",
        "cookie_msg": "This site uses only essential cookies and stores your theme preference in the browser.",
        "cookie_ok": "Got it", "legal": "Legal",
        "an_consent_msg": ("I use essential cookies to run the site. With your permission, I "
                           "also use analytics cookies (Google Tag Manager) to understand how "
                           "the site is used."),
        "an_consent_accept": "Accept analytics",
        "an_consent_essential": "Essential only",
        "an_consent_change": "change my choice",
        "an_consent_section_title": "3.2. Audience analytics (with your permission)",
        "an_consent_section_body": ("Only run once you click \"Accept analytics\" on the cookie "
                                    "notice. Declining does not block anything on the site."),
        "sending_1": "Sending your message…",
        "sending_2": "Securely registering your contact…",
        "sending_3": "Notifying Leandro…",
        "sending_done": "Message sent!",
        "contact_title": "Shall we talk?",
        "contact_sub": "Tell me what you have in mind: a brand to build, a campaign to direct, an interface to design or a creative workflow to speed up with AI. I answer personally, with an honest read on what can be done.",
        "contact_meta": "A brand to build, a campaign to direct or a creative workflow to speed up with AI. I answer personally, with an honest read on what can be done.",
        "leave_message": "Leave your message here",
        "message_hint": "Tell me about the project, the deadline and what needs to happen. The more context, the better the first reply.",
        "phone": "Phone",
        "consent_label": "I authorize contact and the processing of my data to reply to this message and be registered as a contact, under LGPD (Law 13.709/2018) and GDPR (EU 2016/679). I may request access, correction or deletion at any time. See the",
        "consent_required": "To send the form, you must authorize the processing of your data.",
        "form_error": "Name, email or message is missing.",
        "sent_detail": "I got your details and will reply shortly, usually within 1 business day.",
        "reply_time": "Reply within 1 business day ·︎ your data is never shared with third parties",
        "search": "Search", "search_placeholder": "Search cases, skills, pages…",
        "search_hint": "Type, speak or upload an image for AI analysis",
        "search_no_results": "Nothing found for",
        "search_listening": "Listening… go ahead",
        "search_analyzing": "Comparing with the cases…",
        "search_img_kw": "Cases that look like your image",
        "search_ai_off": "Nothing here looks like that image. Try text or voice.",
        "search_voice_off": "Voice search is not supported in this browser.",
        "voice_title": "Go ahead",
        "voice_sub": "Say what you are looking for. The text appears here as you speak.",
        "voice_wait": "Getting the microphone ready…",
        "voice_use": "Search this",
        "voice_cancel": "Cancel",
        "voice_again": "Speak again",
        "voice_denied": "The microphone was blocked. Allow access in the browser bar and try again.",
        "voice_nothing": "I could not hear anything. Try again, closer to the microphone.",
        "voice_done": "Done. Check the text and search.",
        "img_title": "Search by image",
        "img_sub": "The comparison runs on this server, with no AI and without sending your image anywhere.",
        "img_drop": "Drag an image here or",
        "img_pick": "pick a file",
        "img_or": "or",
        "img_url_ph": "Paste an image link",
        "img_err_esquema": "That address is not a web page.",
        "img_err_privado": "That address points inside a network, not to the internet.",
        "img_err_host": "I could not find that address.",
        "img_err_tipo": "That link is not an image.",
        "img_err_tamanho": "The image is over 8 MB.",
        "img_err_resposta": "I could not download that image.",
        "share_case": "Share case", "copy_link": "Copy link", "link_copied": "Link copied!",
        "share_prompt": "Found this case interesting? Share it",
        "like_case": "Liked this case?", "related_cases": "Related cases",
        "back_to_work": "Back to the portfolio", "see_case": "View case",
        "see_site": "View site", "open_site": "Open site", "next_site": "Next site",
        "view_mode": "View", "view_editorial": "Editorial", "view_grid": "Grid",
        "view_masonry": "Masonry",
        "client_everything": "Everything made for", "client_projects": "projects",
        "review_cta": "Leave a review", "review_on": "on Google",
        "secure_title": "Secure connection",
        "secure_detail": "TLS 1.3 ·︎ HSTS ·︎ CSP ·︎ LGPD",
        "zoom_img": "Zoom", "fullscreen_img": "Fullscreen",
        "other_clients": "See what was made for other clients",
        "see_all_clients": "See all clients",
        "client_empty": "Cases for this client are coming soon.",
        "meta_desc": "AI engineering and art direction from one pair of hands. Python, FastAPI and shipped systems. Creative direction and branding for Coca-Cola and Bradesco.",
    },
}


def t(lang: str, key: str) -> str:
    return STRINGS.get(lang, STRINGS["pt"]).get(key, key)


def field(obj, name: str, lang: str) -> str:
    """Campo bilíngue: usa _en quando lang=en e houver conteúdo; senão _pt."""
    if lang == "en":
        val = getattr(obj, f"{name}_en", "") or ""
        if val.strip():
            return val
    return getattr(obj, f"{name}_pt", "") or ""


def lp(lang: str, path: str) -> str:
    """Prefixa o caminho com /en quando necessário."""
    if lang == "en":
        return "/en" + (path if path.startswith("/") else "/" + path)
    return path
