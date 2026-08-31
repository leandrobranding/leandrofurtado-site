"""A tradução ESCRITA do redesign do Grupo OM (item 11).

O Leandro pediu "site multilingual com tradução automática". O coordenador
decidiu o contrário do "automática", e a decisão está registrada no documento
de ajustes: tradução ESTÁTICA, escrita, sem widget. Dois motivos, e os dois
valem mais que a conveniência de um `<script>` de uma linha:

1. **A regra da spec.** Nenhuma página de redesign carrega host externo. Um
   widget de tradução (o Google Translate, que é o que o site atual do cliente
   usa) é host externo por definição.

2. **O argumento da própria proposta.** A peça inteira existe para dizer que a
   home atual entrega 212 KB. Chegar com um widget que soma centenas de KB, e
   ainda põe um terceiro rastreando o visitante do cliente, seria contradizer o
   diagnóstico dentro da própria proposta. É o tipo de incoerência que o dono
   da agência não precisa saber explicar para sentir.

E há um terceiro, que não é técnico: tradução de máquina erra em texto de
marca. "Soluções Improváveis" é o nome de uma empresa, não uma frase.


COMO ESTE ARQUIVO É INDEXADO, e por que o PORTUGUÊS É A CHAVE
-------------------------------------------------------------
O dicionário é `português -> inglês`, e não `chave_curta -> texto`. A diferença
importa em duas horas do dia:

- **Lendo o template.** Com chave curta, `{{ T("servicos_kicker") }}` obriga
  quem lê a abrir um segundo arquivo para saber o que está escrito na tela.
  Com o português como chave, `{{ T("Serviços") }}` se lê sozinho, e a página
  em português continua legível linha por linha, exatamente como era antes do
  item 11.
- **Errando.** Uma chave curta escrita errado devolve a chave, e o cliente vê
  `servicos_kicker` na tela. O português escrito errado devolve o português: o
  pior caso é uma palavra não traduzida, e não um identificador vazando.

O preço é que mudar o texto em português exige mudar a chave aqui junto. É um
preço que o teste cobra: `test_toda_frase_marcada_para_traducao_tem_ingles`
varre os templates e reprova qualquer `T("...")` sem entrada aqui. Uma frase
solta em português no meio da página em inglês não é um erro que apareça
sozinho, e este é o mecanismo que faz aparecer.


O QUE ESTA TRADUÇÃO NÃO DECIDE
------------------------------
Os textos do CLIENTE (as frases dos cases, os depoimentos, a descrição do
grupo) são palavras que a agência escreveu em português, sobre trabalho que
ela fez para clientes com nome. A versão inglesa deles está aqui porque uma
página pela metade não se mostra a ninguém, mas ela é PROPOSTA DE TEXTO, e
quem aprova é a agência. Isso está registrado em Pendências, no relatório, e é
a primeira coisa a levar à reunião.

Nomes próprios NÃO se traduzem, e a lista é literal: Grupo OM, OpusMúltipla,
D'OM Soluções Improváveis, Senso, Brainbox, House Cricket, Tailor Media,
"Fogo & Sabor", "Sonhos Possíveis", e os 27 clientes da fita. Um nome de
empresa traduzido é um nome errado.
"""
from __future__ import annotations

from typing import Callable

# A língua padrão é a do material, do cliente e da agência. O inglês é a
# tradução, e é por isso que ele é o único que tem prefixo de URL.
PADRAO = "pt"
LINGUAS = ("pt", "en")

# As 309 frases da peça, na ordem em que o Jinja as encontra.
EN: dict[str, str] = {
    "Proposta de redesign do site do {}":
        "Redesign proposal for the {} website",
    "por Leandro Furtado. Esse não é o site oficial.":
        "by Leandro Furtado. This is not the official website. Like the proposal?",
    "Gostou da proposta? Entre em contato.":
        "Like this proposal? Get in touch.",
    "Você está aqui":
        "You are here",
    "Cases":
        "Cases",
    "Assina":
        "Signed by",
    "A ficha":
        "The facts",
    "Cliente":
        "Client",
    "Empresa do grupo":
        "Group company",
    "O trabalho,":
        "The work,",
    "como o grupo o publica.":
        "as the group publishes it.",
    "Compartilhar este case":
        "Share this case",
    "Enviar":
        "Send",
    "Copiar endereço":
        "Copy link",
    "Próximo case":
        "Next case",
    "de":
        "of",
    "Ver o case":
        "See the case",
    "Clientes":
        "Clients",
    "marcas":
        "brands",
    "Marcas atendidas":
        "Brands served",
    "pelas empresas do grupo.":
        "by the companies in the group.",
    "Menu do site":
        "Site menu",
    "Fechar":
        "Close",
    "Páginas, menu de tela cheia":
        "Pages, full screen menu",
    "Páginas":
        "Pages",
    "Home":
        "Home",
    "O grupo":
        "The group",
    "Certificações":
        "Certifications",
    "Contato":
        "Contact",
    "Telefones":
        "Phone numbers",
    "Redes sociais":
        "Social media",
    "Políticas, menu de tela cheia":
        "Policies, full screen menu",
    "Política de Privacidade":
        "Privacy Policy",
    "Política de Cookies":
        "Cookie Policy",
    "Acessibilidade":
        "Accessibility",
    "Grupo OM, comunicação integrada":
        "Grupo OM, integrated communications",
    "Vamos conversar":
        "Let us talk",
    "Ideias que funcionam":
        "Ideas that work",
    "começam por uma ligação.":
        "start with a phone call.",
    "Ligar para o {}":
        "Call {}",
    "Ligar agora":
        "Call now",
    "Ver todos os contatos":
        "See every way to reach us",
    "Seis empresas que combinam especialistas das diversas disciplinas do marketing e da comunicação, com planejamento integrado.":
        "Six companies that bring together specialists from every discipline of marketing and communications, under one integrated plan.",
    "Rua Jaguariaíva, 596, 5º andar":
        "Rua Jaguariaíva 596, 5th floor",
    "Páginas do site, rodapé":
        "Site pages, footer",
    "Telefones do Grupo OM":
        "Grupo OM phone numbers",
    "Redes sociais do Grupo OM":
        "Grupo OM on social media",
    "Políticas e acessibilidade":
        "Policies and accessibility",
    "{}, início":
        "{}, home",
    "{}, comunicação integrada":
        "{}, integrated communications",
    "Páginas do site":
        "Site pages",
    "Menu":
        "Menu",
    "O que esta proposta faz para ser usável por teclado, por leitor de tela e por quem pediu menos movimento.":
        "What this proposal does to be usable by keyboard, by screen reader and by anyone who asked for less motion.",
    "Respeitar todo mundo":
        "Respecting everyone",
    "também é código.":
        "is also a matter of code.",
    "O alvo":
        "The target",
    "As":
        "We take",
    "WCAG 2.1, nível AA":
        "WCAG 2.1, level AA",
    ", como referência de trabalho. O que segue é o que já está feito, e o que não estiver, você nos conta.":
        " is the working reference. What follows is what is already done, and whatever is not, you tell us.",
    "O que já está feito":
        "What is already done",
    "8 medidas":
        "8 measures",
    "Oito decisões,":
        "Eight decisions,",
    "todas conferíveis nesta página.":
        "every one of them checkable on this page.",
    "Um título principal por página, e a hierarquia em ordem":
        "One main heading per page, with the hierarchy in order",
    "Contraste medido: nenhum texto abaixo de 4,5 para 1":
        "Measured contrast: no text below 4.5 to 1",
    "Foco visível em tudo que recebe o teclado":
        "Visible focus on everything the keyboard can reach",
    "Quem pede menos movimento recebe a página parada e inteira":
        "Anyone who asks for less motion gets the page still and complete",
    "Alvos de toque de 44 pixels, medidos em telas de 320 a 1920":
        "Touch targets of 44 pixels, measured from 320 to 1920 wide",
    "Texto alternativo em toda imagem que informa, e vazio na que decora":
        "Alternative text on every image that informs, and empty on every image that decorates",
    "A fita de logos tem os mesmos nomes em texto, logo abaixo dela":
        "The logo ribbon carries the same names in text, right below it",
    "Sem script, a página continua completa e navegável":
        "With no script at all, the page stays complete and navigable",
    "Movimento":
        "Motion",
    "O movimento":
        "Motion here",
    "é um convite, nunca uma condição.":
        "is an invitation, never a condition.",
    "A página tem revelação por rolagem, fitas que correm e uma barra que acompanha a leitura. Nada disso é necessário para ler o conteúdo: quem liga":
        "The page has scroll reveals, ribbons that run and a bar that follows your reading. None of it is needed to read the content: anyone who turns on",
    "reduzir movimento":
        "reduce motion",
    "no sistema recebe a página inteira, parada, sem perder uma palavra.":
        "in the operating system gets the whole page, still, without losing a word.",
    "A mesma decisão vale quando o navegador não executa scripts, ou quando eles não chegam: o conteúdo nasce visível, e nenhuma informação depende de uma animação para aparecer.":
        "The same decision holds when the browser runs no scripts, or when they never arrive: the content is born visible, and no information depends on an animation to appear.",
    "Encontrou uma barreira":
        "Found a barrier",
    "Conte para a gente,":
        "Tell us,",
    "que a gente conserta.":
        "and we fix it.",
    "Acessibilidade não termina numa entrega: ela é mantida. Se alguma coisa nesta página não funcionou com o seu leitor de tela, com o seu teclado ou com a sua ampliação, o telefone abaixo é o caminho mais curto.":
        "Accessibility does not end at delivery: it is maintained. If something on this page did not work with your screen reader, your keyboard or your magnification, the number below is the shortest way to us.",
    "Conhecer o Núcleo de Inclusão Geral":
        "Learn about the General Inclusion Board",
    "Cases e campanhas":
        "Cases and campaigns",
    "O trabalho":
        "The work",
    "com nome e assinatura.":
        "with a name and a signature.",
    "Cada campanha aqui é assinada por":
        "Every campaign here is signed by",
    "uma das seis empresas":
        "one of the six companies",
    "do grupo, e é essa assinatura que prova que o planejamento integrado não é retórica.":
        "in the group, and it is that signature that proves integrated planning is not rhetoric.",
    "Em alta":
        "Trending now",
    "Peça de ESG do Grupo OM: as letras E, S e G ilustradas, com a frase transformamos ideias em práticas que ajudam a melhorar o mundo":
        "An ESG piece by Grupo OM: the letters E, S and G illustrated, with the line we turn ideas into practices that help make the world better",
    "Peça da Cartilha Pense Verde do Grupo OM, com o subtítulo sustentabilidade começa com pequenas atitudes":
        "A piece from the Cartilha Pense Verde by Grupo OM, with the subtitle sustainability starts with small attitudes",
    "Nossas certificações":
        "Our certifications",
    "Os selos do Grupo OM, a rede mundial de agências independentes em 47 mercados e o Núcleo de Inclusão Geral.":
        "The badges of Grupo OM, the worldwide network of independent agencies across 47 markets, and the General Inclusion Board.",
    "Independentes aqui,":
        "Independent here,",
    "em 47 mercados lá fora.":
        "in 47 markets out there.",
    "O que isso significa":
        "What that means",
    "Certificação aqui não é selo de parede: é":
        "Certification here is not a plaque on a wall: it is",
    "a rede que dá suporte internacional":
        "the network that provides international support",
    "aos clientes do grupo, e o comitê que revisa o que o grupo produz.":
        "to the group’s clients, and the board that reviews what the group produces.",
    "Reconhecimento":
        "Recognition",
    "selos":
        "badges",
    "Os prêmios":
        "The awards",
    "que o site atual esconde.":
        "the current site keeps hidden.",
    "Hoje eles vivem numa página interna que quase ninguém alcança. Aqui eles ficam onde uma prova precisa ficar: no caminho de quem está decidindo.":
        "Today they live on an inner page almost nobody reaches. Here they sit where proof belongs: in the path of the person making the decision.",
    "certificações": "certifications",
    "O que o grupo":
        "What the group",
    "assume como compromisso.":
        "takes on as a commitment.",
    "A rede mundial de agências independentes, presente em 47 mercados.":
        "The worldwide network of independent agencies, present in 47 markets.",
    "O Núcleo de Inclusão Geral, com um comitê de especialistas de fora da casa.":
        "The General Inclusion Board, with a committee of specialists from outside the company.",
    "Ideias transformadas em práticas, com cartilha própria publicada pelo grupo.":
        "Ideas turned into practice, with a guide published by the group itself.",
    "Rede mundial":
        "Worldwide network",
    "A mais antiga rede":
        "The oldest network",
    "de agências independentes.":
        "of independent agencies.",
    "O Grupo OM faz parte da":
        "Grupo OM is part of the",
    "mais antiga rede mundial de agências independentes":
        "oldest worldwide network of independent agencies",
    ", presente em 47 mercados em todos os continentes. A rede nos permite conhecer como será o futuro da comunicação mundial e dar suporte internacional aos nossos clientes.":
        ", present in 47 markets across every continent. The network lets us see what the future of global communications will look like, and give our clients international support.",
    "mercados atendidos pela rede":
        "markets served by the network",
    "empresas no grupo, aqui":
        "companies in the group, here",
    "especialistas no comitê de inclusão":
        "specialists on the inclusion board",
    "Núcleo de Inclusão Geral":
        "General Inclusion Board",
    "Não dá para agradar todo mundo.":
        "You cannot please everyone.",
    "Mas dá para respeitar todo mundo.":
        "But you can respect everyone.",
    "O":
        "The",
    "Núcleo de Inclusão Geral (NIG)":
        "General Inclusion Board (NIG)",
    "é uma iniciativa inédita no mercado brasileiro que tem o objetivo de incluir diferentes perspectivas de mundo nos projetos do Grupo OM.":
        "is an initiative without precedent in the Brazilian market, created to bring different views of the world into the projects of Grupo OM.",
    "Assim, formamos um comitê de especialistas que representam diversas frentes da diversidade para nos ajudar na avaliação e adaptação do nosso trabalho à realidade de todos.":
        "So we formed a committee of specialists representing many fronts of diversity, to help us assess and adapt our work to everyone’s reality.",
    "Diretor-executivo do Grupo Dignidade e presidente da Aliança Nacional LGBTI+":
        "Executive director of Grupo Dignidade and president of Aliança Nacional LGBTI+",
    "Artista plástica e fundadora do Favela Art":
        "Visual artist and founder of Favela Art",
    "Especialista em diversidade e inclusão para a área empresarial":
        "Specialist in diversity and inclusion for the corporate world",
    "Telefones, endereços e redes sociais do Grupo OM.":
        "Phone numbers, addresses and social media of Grupo OM.",
    "Fale com o":
        "Talk to",
    "Sem formulário":
        "No form",
    "Os dois números abaixo são":
        "The two numbers below are",
    "links de verdade":
        "real links",
    ": no celular, um toque disca.":
        ": on a phone, one tap dials.",
    "2 telefones":
        "2 phone numbers",
    "Ligue agora":
        "Call now",
    "para uma das duas centrais.":
        "one of the two switchboards.",
    "2 endereços":
        "2 addresses",
    "Onde o grupo":
        "Where the group",
    "trabalha.":
        "works.",
    "Endereço 1":
        "Address 1",
    "5º andar":
        "5th floor",
    "Endereço 2":
        "Address 2",
    "Redes":
        "Social",
    "O grupo,":
        "The group,",
    "todo dia.":
        "every day.",
    "Marketing e comunicação":
        "Marketing and communications",
    "Comunicação integrada desde a estratégia":
        "Integrated communications, starting from strategy",
    "para construir marcas e mercados.":
        "to build brands and markets.",
    "Quem faz":
        "Who does it",
    "Somos":
        "We are",
    "6 empresas":
        "6 companies",
    "que combinam especialistas das diversas disciplinas do marketing e da comunicação, mas que trabalham de forma sinérgica, com planejamento integrado.":
        "that bring together specialists from every discipline of marketing and communications, working in sync, under one integrated plan.",
    "Ver os cases":
        "See the cases",
    "Falar com o {}":
        "Talk to {}",
    "Serviços":
        "Services",
    "Da estratégia de marca":
        "From brand strategy",
    "à gestão de mídia.":
        "to media management.",
    "Consultoria estratégica de marcas":
        "Strategic brand consulting",
    "Branding e identidade de marca":
        "Branding and brand identity",
    "Design gráfico e de produto":
        "Graphic and product design",
    "Comunicação integrada e publicidade":
        "Integrated communications and advertising",
    "Marketing digital e performance":
        "Digital marketing and performance",
    "Inteligência e gestão de mídia":
        "Media intelligence and management",
    "Relacionamento e customer experience":
        "Relationship and customer experience",
    "Seis empresas,":
        "Six companies,",
    "um planejamento só.":
        "one single plan.",
    "Analisamos mercados e desenvolvemos campanhas completas de comunicação, em todas as plataformas, on e off line.":
        "We analyse markets and develop complete communications campaigns, on every platform, online and offline.",
    "empresas, com planejamento integrado":
        "companies, under one integrated plan",
    "mercados, em todos os continentes":
        "markets, on every continent",
    "marcas de clientes atendidas":
        "client brands served",
    "Campanhas assinadas":
        "Campaigns signed",
    "Depoimentos":
        "Testimonials",
    "O que dizem":
        "What they say,",
    "os clientes.":
        "the clients themselves.",
    "O Grupo OM é uma referência. Nós somos muito fãs do trabalho que é realizado por eles.":
        "Grupo OM is a benchmark. We are huge fans of the work they do.",
    "Gerente de Marketing do Hospital Pequeno Príncipe":
        "Marketing manager at Hospital Pequeno Príncipe",
    "O Grupo teve a competência de captar a nossa origem como produtor, nosso envolvimento com a natureza, nosso cooperativismo e associativismo.":
        "The Group had the skill to capture our origin as producers, our bond with nature, our cooperative and associative spirit.",
    "Diretor-executivo da Frimesa":
        "Executive director at Frimesa",
    "O Grupo OM nos oferece, por meio de suas empresas, um trabalho diferenciado, fortemente embasado em dados, estratégico e muito bem planejado. Por isso, os resultados aparecem.":
        "Through its companies, Grupo OM gives us work that stands apart: strongly grounded in data, strategic and very well planned. That is why the results show.",
    "Superintendente do Shopping Mueller":
        "Superintendent at Shopping Mueller",
    "Esta proposta não põe cookie nenhum: nem de medição, nem de publicidade, nem de idioma. O idioma é um segmento do endereço.":
        "This proposal sets no cookie at all: none for analytics, none for advertising, none for language. The language is a segment of the address.",
    "Nenhum cookie,":
        "No cookie,",
    "e nada para consentir.":
        "and nothing to consent to.",
    "Por isso não há aviso":
        "Which is why there is no banner",
    "Sem cookie de medição e sem cookie de publicidade,":
        "With no analytics cookie and no advertising cookie,",
    "não há consentimento a pedir":
        "there is no consent to ask for",
    ". A página abre no conteúdo, e não numa faixa.":
        ". The page opens on the content, not on a bar across it.",
    "A conta inteira":
        "The whole count",
    "Zero,":
        "Zero,",
    "e isso é conferível agora.":
        "and you can check that right now.",
    "De primeira parte":
        "First party",
    "nenhum":
        "none",
    "De terceiro":
        "Third party",
    "De idioma":
        "Language",
    "nenhum: o idioma é o endereço":
        "none: the language is the address",
    "Consentimento a pedir":
        "Consent to ask for",
    "A versão em inglês desta proposta tem endereço próprio, terminado em barra en, e é assim que ela é lembrada: pelo link. Um endereço não precisa de cookie para saber quem é, e é por isso que a lista acima é a lista inteira. Abra o painel do navegador nesta página e confira.":
        "The English version of this proposal has an address of its own, ending in slash en, and that is how it is remembered: by the link. An address does not need a cookie to know who it is, and that is why the list above is the whole list. Open your browser panel on this page and check.",
    "O que não existe":
        "What does not exist",
    "Nenhum de terceiro,":
        "None from a third party,",
    "porque nada vem de fora.":
        "because nothing comes from outside.",
    "Nenhum cookie de medição de audiência":
        "No audience measurement cookie",
    "Nenhum cookie de publicidade ou remarketing":
        "No advertising or remarketing cookie",
    "Nenhum widget de tradução de terceiro":
        "No third party translation widget",
    "Nenhum botão de rede social que carrega script":
        "No social media button that loads a script",
    "O idioma desta proposta é":
        "The language of this proposal is",
    "tradução escrita":
        "written translation",
    ", servida por este mesmo endereço, e não um tradutor automático de outra empresa. É por isso que não há terceiro nenhum para pôr cookie aqui.":
        ", served from this same address, and not an automatic translator from another company. That is why there is no third party here to set a cookie.",
    "Fora do escopo":
        "Out of scope",
    "O texto oficial":
        "The official text",
    "é do grupo.":
        "belongs to the group.",
    "Esta é uma proposta de redesign, e não o site oficial do":
        "This is a redesign proposal, and not the official website of",
    ". Quando o site definitivo entrar no ar com as ferramentas que a agência decidir usar, a política de cookies dela é que vale. Este endereço declara o que":
        ". When the final site goes live with whatever tools the agency chooses, it is the agency’s cookie policy that applies. This address declares what",
    "esta peça":
        "this piece",
    "faz.":
        "does.",
    "O que esta proposta de redesign coleta, o que ela não coleta, e a estrutura da política definitiva.":
        "What this redesign proposal collects, what it does not collect, and the shape of the definitive policy.",
    "Esta página":
        "This page",
    "não coleta nada.":
        "collects nothing.",
    "Em uma frase":
        "In one sentence",
    "Não há formulário, não há rastreador e":
        "There is no form, no tracker and",
    "nenhum recurso vem de fora":
        "nothing is loaded from outside",
    ". Nada que você faz aqui vira dado de ninguém.":
        ". Nothing you do here becomes anybody’s data.",
    "O que não acontece":
        "What does not happen",
    "Quatro coisas":
        "Four things",
    "que esta peça não faz.":
        "this piece does not do.",
    "Não existe formulário em nenhuma página":
        "There is no form on any page",
    "Nenhum recurso é carregado de outro domínio":
        "No resource is loaded from another domain",
    "Nenhuma medição de audiência, nenhum pixel":
        "No audience measurement, no pixel",
    "Nenhum perfil de navegação é montado":
        "No browsing profile is built",
    "A fonte, os quatro arquivos de movimento, os logos e os selos são servidos pelo mesmo endereço desta página. É por isso que ela pesa uma fração do site atual, e é o mesmo motivo pelo qual não há o que coletar.":
        "The typeface, the four motion files, the logos and the badges are all served from the same address as this page. That is why it weighs a fraction of the current site, and it is the same reason there is nothing to collect.",
    "O que o servidor registra":
        "What the server records",
    "O mínimo":
        "The minimum",
    "que qualquer servidor registra.":
        "that any server records.",
    "Como todo servidor web, este anota o pedido que recebe: o endereço solicitado, a data e a hora, e o endereço de rede de onde o pedido veio. Isso existe para o site funcionar e para conter abuso, e não alimenta nenhum perfil.":
        "Like every web server, this one notes the request it receives: the address asked for, the date and time, and the network address it came from. That exists so the site works and so abuse can be contained, and it feeds no profile.",
    "Esta proposta guarda também":
        "This proposal also stores",
    "a data em que o link foi aberto pela primeira vez":
        "the date the link was first opened",
    ". É um único carimbo, por proposta, e serve para o Leandro saber que ela chegou. Não é um contador de visitas e não identifica ninguém.":
        ". It is a single timestamp, one per proposal, and it is there so Leandro knows it arrived. It is not a visit counter and it identifies nobody.",
    "A política do grupo":
        "The group’s own policy",
    "quem escreve é o grupo.":
        "is written by the group.",
    ". O texto definitivo da política de privacidade da agência, com as bases legais da LGPD, os prazos de guarda e o canal do encarregado de dados, é da agência e do jurídico dela. Este endereço existe para mostrar":
        ". The definitive text of the agency’s privacy policy, with the legal bases under the LGPD, the retention periods and the data officer’s channel, belongs to the agency and its legal team. This address exists to show",
    "o lugar dela no desenho":
        "where that policy sits in the design",
    ", e para declarar, com honestidade, o que esta peça faz.":
        ", and to declare, honestly, what this piece does.",
    "Quem somos":
        "Who we are",
    "O que fazemos":
        "What we do",
    "Campanhas completas,":
        "Complete campaigns,",
    "on e off line.":
        "online and offline.",
    "Nosso principal objetivo é":
        "Our main goal is to",
    "gerar ideias que funcionam":
        "generate ideas that work",
    "para ajudar a construir marcas e mercados.":
        "to help build brands and markets.",
    "As seis empresas":
        "The six companies",
    "que formam o grupo.":
        "that make up the group.",
    "marcas com logo na home":
        "brands with a logo on the home page",
    "O Grupo OM é uma referência. Nós somos muito fãs do trabalho que é realizado por eles. Que alegria saber que somos importantes para o Grupo e que fazemos parte dessa história, assim como eles fazem parte da nossa!":
        "Grupo OM is a benchmark. We are huge fans of the work they do. What a joy to know that we matter to the Group and that we are part of this story, just as they are part of ours!",
    "O Grupo OM nos oferece, por meio de suas empresas, um trabalho diferenciado, fortemente embasado em dados, estratégico e muito bem planejado. Por isso, os resultados aparecem. Compartilham conosco informações relevantes que nos ajudam na tomada de decisão. Uma relação de respeito e amizade.":
        "Through its companies, Grupo OM gives us work that stands apart: strongly grounded in data, strategic and very well planned. That is why the results show. They share relevant information with us that helps our decision making. A relationship of respect and friendship.",
    "Sonhos Possíveis":
        "Sonhos Possíveis",
    "A Senso entrou em ação para ajudar a Frimesa a aumentar as vendas destinadas ao segmento de food service, aumentando as vendas para restaurantes, lanchonetes e cozinhas industriais.":
        "Senso went into action to help Frimesa grow the sales aimed at the food service segment, increasing sales to restaurants, snack bars and industrial kitchens.",
    "Desenvolvida para apresentar os novos produtos da linha premium da marca, a campanha faz uma analogia entre a descoberta do fogo e a experiência de sabor proporcionada pelos produtos da linha.":
        "Created to introduce the new products in the brand’s premium line, the campaign draws an analogy between the discovery of fire and the taste experience the line delivers.",
    "A marca fez uma grande surpresa para dois atletas mirins, a Heloiza e o Pedro, que sonham em jogar futebol profissionalmente e puderam acompanhar a final do campeonato no estádio, com toda a emoção e inspiração.":
        "The brand pulled off a big surprise for two young athletes, Heloiza and Pedro, who dream of playing football professionally and got to watch the final of the championship at the stadium, with all the emotion and inspiration that brings.",
    "Nós unimos estratégias de branding, visual merchandising e embalagem para fazer a magia acontecer no PDV, alavancar resultados B2B e B2C e construir marcas fortes em seus respectivos segmentos.":
        "We combined branding, visual merchandising and packaging strategies to make the magic happen at the point of sale, drive B2B and B2C results and build strong brands in their segments.",
    "Branding":
        "Branding",
    "Arte do case":
        "Case artwork",
    "Quadro de destaque do case":
        "Featured frame of the case",
    "Publicado em":
        "Published on",
    "Assunto":
        "Subject",
    "E-mail":
        "Email",
    "Voltar para os cases":
        "Back to the cases",
    "Os cases assinados pelas empresas do Grupo OM, com data, assunto e a empresa que assina cada um.":
        "The cases signed by the Grupo OM companies, each with its date, subject and signing company.",
    "campanhas,":
        "campaigns,",
    "assinaturas.":
        "signatures.",
    "Nenhum case com esse texto. Limpe a busca para ver todos.":
        "No case matches that text. Clear the search to see them all.",
    "cases publicados":
        "published cases",
    "Todos os cases":
        "Every case",
    "Empresa":
        "Company",
    "Todas":
        "All",
    "Todos":
        "All",
    "Voltar para o Lab": "Back to the Lab",
    "Voltar para o Lab de Demos de Leandro Furtado":
        "Back to Leandro Furtado's demo Lab",
    "Páginas de cases": "Case pages",
    "Página anterior": "Previous page",
    "Próxima página": "Next page",
    "Página": "Page",
    # A frase legal que o PRÓPRIO cliente publica na política de privacidade
    # dele. A razão social das seis empresas não se traduz: é nome de empresa
    # registrada, e traduzir um nome registrado é inventar outra empresa.
    "O Grupo OM é formado pela conjugação de esforços das empresas OpusMúltipla Comunicação Integrada S.A., Brainbox Design Estratégico S.A., Senso Estratégia Multicanais S.A., Tailor Media Branded Content S.A., Housecricket Inteligência Digital S.A. e D’OM Soluções Improváveis S.A.":
        "Grupo OM is formed by the combined efforts of OpusMúltipla Comunicação Integrada S.A., Brainbox Design Estratégico S.A., Senso Estratégia Multicanais S.A., Tailor Media Branded Content S.A., Housecricket Inteligência Digital S.A. and D’OM Soluções Improváveis S.A.",
    "Ver todos os cases": "See all cases",
    # A missão do Instituto, encurtada da frase que o próprio site dele
    # publica. O nome "Instituto J.D. Rodrigues" não entra aqui: é nome
    # próprio e vive no `alt` da marca.
    "Zelar pela cultura da Comunicação Integrada de Marketing e disseminar esse conhecimento pelo mercado.":
        "To uphold the culture of Integrated Marketing Communication and spread that knowledge across the market.",
    "Conhecer": "Visit",
    "Desenvolvido e certificado por": "Built and certified by",
    "Buscar no texto":
        "Search the text",
    "cases":
        "cases",
    "{n} de {total} cases":
        "{n} of {total} cases",
    "VP de Conteúdo e Integração":
        "VP of Content and Integration",
    "Produção gráfica e arte-final":
        "Graphic production and artwork",
    "Produção e art buyer":
        "Production and art buying",
    "Diretora de Comunicação Corporativa":
        "Corporate Communications Director",
    "Coordenador de Comunicação Corporativa":
        "Corporate Communications Coordinator",
    "Gestão Estratégica de Marcas":
        "Strategic Brand Management",
    "Gerente de Estratégia e Consumer Insights":
        "Strategy and Consumer Insights Manager",
    "Supervisor de Atendimento":
        "Account Supervisor",
    "Diretor de Estratégia e Consumer Insights":
        "Strategy and Consumer Insights Director",
    "Agência":
        "Agency",
    "Filmes":
        "Films",
    "Diretor da Unidade de Negócios OTC":
        "OTC Business Unit Director",
    "Diretor de Gestão Estratégica de Marcas":
        "Strategic Brand Management Director",
    "Produção eletrônica e fotos":
        "Electronic production and stills",
    "Coordenação de pós-produção":
        "Post-production coordination",
    "Atendimento e coordenação":
        "Account handling and coordination",
    "Head of Creative Strategy":
        "Head of Creative Strategy",
    "Campanhas":
        "Campaigns",
    "Comunicação Integrada":
        "Integrated Communications",
    "Design":
        "Design",
    "Digital":
        "Digital",
    "Marketing":
        "Marketing",
    "Motion":
        "Motion",
    "Ilha Urbana Malbec Ultra Bleu":
        "Ilha Urbana Malbec Ultra Bleu",
    "O case da Ilha Urbana que divulgou o Malbec Ultra Bleu, do Boticário, uniu impacto e criatividade num espaço que chamou a atenção nas ruas de São Paulo.":
        "The Ilha Urbana case behind Malbec Ultra Bleu, by Boticário, joined impact and creativity in a space that turned heads on the streets of São Paulo.",
    "Como comunicar com impacto e criatividade?":
        "How do you communicate with impact and creativity?",
    "O case da Ilha Urbana que divulgou o Malbec Ultra Bleu, do Boticário, soube unir esses dois aspectos com maestria.":
        "The Ilha Urbana case behind Malbec Ultra Bleu, by Boticário, brought both together masterfully.",
    "A OpusMúltipla criou um espaço que chamou a atenção nas ruas de São Paulo e elevou a outro patamar a veiculação da campanha.":
        "OpusMúltipla built a space that turned heads on the streets of São Paulo and lifted the campaign to another level.",
    "Essa estratégia garantiu o Bronze na categoria Media dos Prémios Lusófonos da Criatividade 2025.":
        "The strategy took Bronze in the Media category at the 2025 Prémios Lusófonos da Criatividade.",
    "A Volta Ao Mundo em 80.000 KM":
        "Around the World in 80,000 KM",
    "O novo UltraContact da Continental foi lançado com garantia de 80 mil km, e a D’OM criou a sequência do clássico “A volta ao mundo em 80 dias”, de Júlio Verne.":
        "Continental launched the new UltraContact with an 80,000 km warranty, and D’OM wrote the sequel to Jules Verne’s classic “Around the World in 80 Days”.",
    "O novo UltraContact da Continental foi lançado com garantia de 80 mil km, algo nunca visto no mercado. Para marcar esse lançamento, algo também nunca visto: a D’OM criou a sequência do clássico “A volta ao mundo em 80 dias”, de Júlio Verne.":
        "Continental launched the new UltraContact with an 80,000 km warranty, unheard of in the market. To mark the launch, something equally unheard of: D’OM wrote the sequel to Jules Verne’s classic “Around the World in 80 Days”.",
    "O novo livro “A volta ao mundo em 80 mil km” foi escrito e inspirado no estilo e linguagem do autor, com ajuda do ChatGPT. São 310 páginas de aventura, romance, tecnologia e arte.":
        "The new book “Around the World in 80,000 km” was written in the author’s own style and language, with help from ChatGPT. It runs 310 pages of adventure, romance, technology and art.",
    "Nove meses de trabalho, versão audiobook, versão digital, versão em inglês, dicas das centenas de localidades visitadas pelos personagens, seu carro e seus pneus UltraContact. E ainda uma sobrecapa com mapa-múndi especial mostrando todo o trajeto pelos vários continentes.":
        "Nine months of work, an audiobook edition, a digital edition, an English edition, tips on the hundreds of places visited by the characters, their car and their UltraContact tyres. Plus a dust jacket carrying a world map of the whole route across the continents.",
    "A D’OM acredita nisso: ideias que vão além das fronteiras da propaganda e criam conversas entre marcas e pessoas.":
        "D’OM believes in exactly this: ideas that reach beyond the borders of advertising and start conversations between brands and people.",
    "Contrastes":
        "Contrastes",
    "A campanha pro bono da Afece reforça a importância de abrir caminhos para o desenvolvimento e a autonomia de pessoas com deficiências múltiplas.":
        "The pro bono campaign for Afece underlines how much it matters to open paths toward development and autonomy for people with multiple disabilities.",
    "A publicidade tem o poder de transformar realidades.":
        "Advertising has the power to transform realities.",
    "Foi com esse propósito que criamos a nova campanha pro bono da Afece, “Contrastes”, que reforça a importância de abrir caminhos para o desenvolvimento e a autonomia de pessoas com deficiências múltiplas. Com produção da The Youth, pós-produção da Colossal e trilha e finalização de áudio assinadas pela Canja, o filme transforma o “não” em convite à inclusão e mostra como o suporte transforma histórias.":
        "That is the purpose behind “Contrastes”, the new pro bono campaign for Afece, which underlines how much it matters to open paths toward development and autonomy for people with multiple disabilities. Produced by The Youth, with post-production by Colossal and score and audio finishing by Canja, the film turns “no” into an invitation to inclusion and shows how support rewrites lives.",
    "Clash no Catamarã":
        "Clash on the Catamaran",
    "O case de ativação do Clash, do Boticário, uniu comunicação regional e criatividade: pela primeira vez, o Catamarã de Porto Alegre virou mídia.":
        "The brand activation case for Clash, by Boticário, joined regional communication and creativity: for the first time, the Porto Alegre catamaran became a media channel.",
    "Como levar uma marca onde ninguém chegou ainda?":
        "How do you take a brand where nobody has been yet?",
    "O case de ativação de marca do Clash, do Boticário, uniu comunicação regional e criatividade para fazer isso. Pela primeira vez, o Catamarã de Porto Alegre virou mídia e estampou o novo perfume da marca.":
        "The brand activation case for Clash, by Boticário, joined regional communication and creativity to do it. For the first time, the Porto Alegre catamaran became a media channel and carried the brand’s new fragrance.",
    "Tudo isso com estratégia, planejamento e execução da OpusMúltipla. O case conquistou a Prata na categoria Ativação de Marca dos Prémios Lusófonos da Criatividade.":
        "All of it strategised, planned and executed by OpusMúltipla. The case took Silver in the Brand Activation category at the Prémios Lusófonos da Criatividade.",
    "Frimesa Fogo & Sabor":
        "Frimesa Fogo & Sabor",
    "A campanha faz uma analogia entre a descoberta do fogo e a experiência de sabor dos produtos da linha premium da Frimesa, divulgada de maneira integrada.":
        "The campaign draws an analogy between the discovery of fire and the taste experience of Frimesa’s premium line, rolled out across integrated channels.",
    "A campanha “Fogo & Sabor” foi criada pela OpusMúltipla para a Frimesa.":
        "The “Fogo & Sabor” campaign was created by OpusMúltipla for Frimesa.",
    "A divulgação foi realizada de maneira integrada, por diferentes canais e com ações e ativações variadas para fortalecer a marca e enfatizar os atributos de inovação, versatilidade e praticidade.":
        "The rollout ran across integrated channels, with varied actions and activations to strengthen the brand and stress its innovation, versatility and convenience.",
    "Gargantas Valda":
        "Gargantas Valda",
    "Uma maneira criativa e cômica de mostrar que as pastilhas Valda são a salvação para qualquer hora, em três filmes criados pela D’OM.":
        "A creative, comic way to show that Valda lozenges are the rescue at any hour, across three films created by D’OM.",
    "Conheça as Gargantas Valda, criadas pela D’OM.":
        "Meet the Gargantas Valda, created by D’OM.",
    "Uma maneira criativa e cômica de mostrar que as pastilhas Valda são a salvação para qualquer hora.":
        "A creative, comic way to show that Valda lozenges are the rescue at any hour.",
    "Geração de fluxo em lojas no Dia dos Pais":
        "Driving store traffic on Father’s Day",
    "A OpusMúltipla e o Google combinaram vídeos no YouTube e Performance Max Offline, com redução de 14% no custo por visita e crescimento nas vendas.":
        "OpusMúltipla and Google combined YouTube video and Performance Max Offline, cutting cost per visit by 14% and lifting sales.",
    "Como uma estratégia de mídia bem executada pode fazer diferença nas vendas?":
        "Can a well-run media strategy move the sales needle?",
    "A OpusMúltipla e o Google se uniram com o objetivo de gerar fluxo de loja no Dia dos Pais para as praças do Rio de Janeiro do Boticário.":
        "OpusMúltipla and Google joined forces to drive store traffic on Father’s Day across Boticário’s Rio de Janeiro markets.",
    "A estratégia combinou o uso de vídeos no YouTube e Performance Max Offline no Google Ads.":
        "The strategy combined YouTube video and Performance Max Offline on Google Ads.",
    "O resultado: redução de 14% no custo por visita e um crescimento de 2 pontos percentuais nas vendas do Rio de Janeiro em comparação com o Dia das Mães.":
        "The result: cost per visit down 14%, and Rio de Janeiro sales up 2 percentage points against Mother’s Day.",
    "O case completo entrou para a galeria do Google.":
        "The full case made it into Google’s own gallery.",
    "Junto com a Mamy":
        "Junto com a Mamy",
    "A campanha do novo posicionamento da MamyPoko foge da comunicação da categoria e coloca o holofote em quem está por trás de todo o cuidado: a mãe.":
        "The campaign behind MamyPoko’s new positioning breaks away from category convention and puts the spotlight on the person behind all the caring: the mother.",
    "A exaustão materna é uma realidade para a maioria das mulheres, e foi com esse olhar que a D’OM Soluções Improváveis desenvolveu a campanha que marca o novo posicionamento da MamyPoko.":
        "Maternal exhaustion is a reality for most women, and D’OM Soluções Improváveis built MamyPoko’s new positioning campaign from that starting point.",
    "Fugindo da comunicação tradicional da categoria, que costuma focar exclusivamente no bebê, a campanha “Junto com a mamy, até no nome” coloca o holofote em quem está por trás de todo o cuidado: a mãe.":
        "Breaking away from category convention, which tends to focus on the baby alone, the campaign “Junto com a mamy, até no nome” puts the spotlight on the person behind all the caring: the mother.",
    "O conceito busca desmistificar a ideia de perfeição, abraçando as dúvidas, os desafios e as imperfeições que fazem parte do dia a dia das famílias.":
        "The idea sets out to dismantle the myth of perfection, embracing the doubts, the challenges and the imperfections of everyday family life.",
    "A estratégia une o apoio emocional ao benefício funcional, destacando que produtos que garantem noites secas para o bebê proporcionam o descanso que a mãe tanto precisa.":
        "The strategy ties emotional support to functional benefit: products that keep the baby dry all night give the mother the rest she badly needs.",
    "Com um tom de voz humano e próximo, a marca reafirma que as mães não estão sozinhas nessa jornada.":
        "In a human, close tone of voice, the brand restates its promise: mothers are never alone on this journey.",
    "M Possibilidades":
        "M Possibilidades",
    "A campanha institucional do Shopping Mueller usou inteligência artificial para criar texturas, movimentos e cores, e transformar o icônico M do mall.":
        "Shopping Mueller’s brand campaign used artificial intelligence to build textures, movement and colour, reshaping the mall’s iconic M.",
    "Esta é a campanha institucional do Shopping Mueller.":
        "This is Shopping Mueller’s brand campaign.",
    "Intitulada de “M possibilidades”, a campanha criada pela OpusMúltipla utilizou recursos da inteligência artificial para criar diferentes texturas, movimentos e cores.":
        "Titled “M possibilidades”, the campaign created by OpusMúltipla used artificial intelligence to build different textures, movement and colour.",
    "Assim, transformamos o icônico M que simboliza o mall em uma marca ainda mais potente e diversa.":
        "The iconic M that stands for the mall became a stronger, more diverse brand.",
    "Memes Unidos":
        "Memes Unidos",
    "A campanha da Vero Internet é uma passeata de memes tomando conta da cidade, numa mistura de inteligência artificial e muita criatividade.":
        "The Vero Internet campaign is a meme march taking over the city, mixing artificial intelligence and plenty of creativity.",
    "Já imaginou uma passeata de memes tomando conta da cidade?":
        "Ever pictured a meme march taking over the city?",
    "Essa é a proposta da nova campanha da Vero Internet, criada pela D’OM: uma manifestação com os memes mais quentes do mundo online, em uma mistura de inteligência artificial e muita criatividade.":
        "That is the idea behind Vero Internet’s new campaign, created by D’OM: a rally of the hottest memes online, mixing artificial intelligence and plenty of creativity.",
    "Natal Iluminado":
        "Natal Iluminado",
    "O filme de fim de ano da Uninter narra a história de uma menina que cresce num vilarejo sem eletricidade e busca na Engenharia Elétrica o conhecimento.":
        "Uninter’s end-of-year film follows a girl growing up in a village without electricity who turns to Electrical Engineering for the knowledge to change it.",
    "A OpusMúltipla apresenta “Natal Iluminado”, o novo filme de fim de ano criado para a Uninter.":
        "OpusMúltipla presents “Natal Iluminado”, the new end-of-year film created for Uninter.",
    "Nesta produção emocionante, narramos a história de uma menina que cresce em um vilarejo sem eletricidade e, movida pelo desejo de aprender, busca na Engenharia Elétrica o conhecimento para transformar a realidade de sua comunidade.":
        "In this moving production, a girl grows up in a village without electricity and, driven by the wish to learn, turns to Electrical Engineering for the knowledge to change her community.",
    "Mais do que uma campanha, esta obra simboliza a crença da OpusMúltipla no poder das boas histórias e a missão da Uninter em mostrar que a educação é a força mais potente de transformação individual e coletiva.":
        "Beyond a campaign, the film stands for OpusMúltipla’s belief in good storytelling and Uninter’s mission to show that education is the strongest force of individual and collective change.",
    "O futuro é agora ou agora":
        "The future is now, or now",
    "Para os 35 anos da Fundação Grupo Boticário, o Canal Off saiu do ar em uma ação inédita e um mapa exclusivo no Fortnite conversou com a Geração Z.":
        "For the 35th anniversary of Fundação Grupo Boticário, Canal Off went off air in an unprecedented move and an exclusive Fortnite map spoke straight to Gen Z.",
    "Para comemorar os 35 anos da Fundação Grupo Boticário, criamos uma campanha que se transformou em um verdadeiro chamado pela natureza.":
        "To mark the 35th anniversary of Fundação Grupo Boticário, we built a campaign that became a genuine call on behalf of nature.",
    "Deixamos o Canal Off, um dos maiores canais de natureza do Brasil, fora do ar em uma ação inédita.":
        "We took Canal Off, one of the largest nature channels in Brazil, off air in an unprecedented move.",
    "Criamos um mapa exclusivo com missões especiais dentro do Fortnite, em uma conversa direta com a Geração Z.":
        "We built an exclusive map with special missions inside Fortnite, speaking straight to Gen Z.",
    "O resultado foi além dos números e deixou clara a importância de ações que evidenciam o pedido de socorro do meio ambiente.":
        "The result went past the numbers and made the case for work that puts the environment’s cry for help in plain sight.",
    "Play no Enem":
        "Play no Enem",
    "As peças dão enfoque à facilidade de usar as notas do Enem para conquistar uma graduação, em TV aberta, digital, mídia exterior e rádio em Curitiba.":
        "The work highlights how easily an Enem score turns into a degree, across broadcast TV, digital, outdoor and radio in Curitiba.",
    "A OpusMúltipla e a Uninter apresentam a nova campanha Play no Enem.":
        "OpusMúltipla and Uninter present the new Play no Enem campaign.",
    "As peças dão enfoque à facilidade de usar as notas do Exame Nacional do Ensino Médio para conquistar uma graduação e mudar o futuro por meio da educação.":
        "The work highlights how easily a score in the Brazilian national secondary exam turns into a degree, and a future changed through education.",
    "Além de o filme figurar na TV aberta e no meio digital, criamos peças de comunicação exterior e spot de rádio para as praças de Curitiba.":
        "Beyond the film on broadcast TV and digital, we created outdoor pieces and a radio spot for the Curitiba market.",
    "A Continental Pneus fez uma surpresa para dois atletas mirins que sonham em jogar futebol e acompanharam a final da Copa do Brasil no estádio.":
        "Continental Pneus surprised two young athletes who dream of playing football, taking them to the Copa do Brasil final at the stadium.",
    "O case “Sonhos Possíveis” foi criado pela D’OM Soluções Improváveis para a Continental Pneus, patrocinadora da Copa do Brasil.":
        "The “Sonhos Possíveis” case was created by D’OM Soluções Improváveis for Continental Pneus, a sponsor of the Copa do Brasil.",
    "A ação contou com a participação da FIFA Legend Formiga, uma das mais consagradas jogadoras do futebol feminino do país e a única do mundo a atuar em todas as edições da Olimpíada.":
        "The action featured FIFA Legend Formiga, one of the most celebrated names in Brazilian women’s football and the only player in the world to have played at every Olympic edition.",
    "Tarja Violeta":
        "Tarja Violeta",
    "Remédios sem comprimido dentro, com bula e desenho de uma criança atendida, para ampliar as doações ao tratamento oncológico infantil.":
        "Medicine boxes with no pills inside, carrying a leaflet and a drawing by a child in treatment, to raise donations for childhood cancer care.",
    "Conheça os remédios Tarja Violeta.":
        "Meet the Tarja Violeta medicines.",
    "A iniciativa, idealizada pela OpusMúltipla, tem o objetivo de ampliar as doações para o tratamento oncológico de crianças e adolescentes do Hospital Erastinho e da APACN.":
        "The initiative, conceived by OpusMúltipla, sets out to raise donations for the cancer treatment of children and teenagers at Hospital Erastinho and APACN.",
    "Os remédios não possuem nenhum comprimido dentro, mas contam com uma bula e um desenho especial de uma das crianças atendidas pelas instituições. Além disso, você pode ler um QR Code e conhecer a trajetória dessa criança.":
        "The boxes hold no pills at all. Inside there is a leaflet and a drawing by one of the children cared for by the two institutions, plus a QR Code that opens that child’s story.",
    "Videocase Cymco":
        "Cymco video case",
    "A Brainbox une branding, visual merchandising e embalagem para fazer a magia acontecer no PDV e construir marcas fortes em seus segmentos.":
        "Brainbox joins branding, visual merchandising and packaging to make the magic happen at the point of sale and build strong brands in their segments.",
    "Quer saber onde está a Brainbox? Vá às compras.":
        "Want to know where Brainbox is? Go shopping.",
    "Videocase Frimesa":
        "Frimesa video case",
    "A Senso entrou em ação para ajudar a Frimesa a aumentar as vendas destinadas ao segmento de food service, restaurantes e cozinhas industriais.":
        "Senso went to work helping Frimesa grow sales into the food service segment: restaurants, snack bars and industrial kitchens.",
    "Alphaville, Pinhais - PR":
        "Alphaville, Pinhais - PR",
    "Vila Olímpia, São Paulo - SP":
        "Vila Olímpia, São Paulo - SP",
    "Alphaville, Pinhais":
        "Alphaville, Pinhais",
    "Vila Olímpia, São Paulo":
        "Vila Olímpia, São Paulo",
    "Rua Cardoso de Melo, 1750":
        "Rua Cardoso de Melo, 1750",
    "Ver no mapa":
        "Open in Maps",
    "Prêmios":
        "Awards",
    # ------------------------------------------------------------
    # A CENTRAL DE CONTEÚDO E OS SERVIÇOS (27/08): moldura das páginas
    # novas, os cinco serviços das LPs, os oito artigos (título, resumo
    # e abertura) e os cinco vídeos do canal.
    # ------------------------------------------------------------
    'Artigo':
        'Article',
    'Esta é a abertura do artigo. O texto completo está publicado no site atual do grupo.':
        "This is the article's opening. The full text is published on the group's current website.",
    'Ler o artigo completo':
        'Read the full article',
    'Voltar à central':
        'Back to the hub',
    'Conteúdo':
        'Content',
    'Central de conteúdo':
        'Content hub',
    'Cases, artigos, vídeos e o áudio do Grupo OM, num lugar só.':
        "Grupo OM's cases, articles, videos and audio, all in one place.",
    'Tudo que o grupo publica,':
        'Everything the group publishes,',
    'num lugar só.':
        'in one place.',
    'Tipos de conteúdo':
        'Content types',
    'Artigos':
        'Articles',
    'Vídeos':
        'Videos',
    'Áudio':
        'Audio',
    'Nas redes':
        'On social',
    'O que o grupo escreve':
        'What the group writes',
    'sobre marketing e gestão.':
        'about marketing and management.',
    'Ler o artigo':
        'Read the article',
    'O canal de vídeos,':
        'The video channel,',
    'produzido pelas empresas.':
        'produced by the companies.',
    'A marca também':
        'A brand can also',
    'se ouve.':
        'be heard.',
    'A identidade sonora do grupo: o soundbrand oficial, publicado no canal do YouTube.':
        "The group's sound identity: the official soundbrand, published on the YouTube channel.",
    'Ouvir':
        'Listen',
    'O dia a dia':
        'The day-to-day',
    'é publicado lá.':
        'is published there.',
    'Posts, reels e bastidores não têm como morar numa proposta: moram nos perfis do grupo, e é para lá que estes cartões levam.':
        "Posts, reels and behind-the-scenes can't live inside a proposal: they live on the group's profiles, and that is where these cards lead.",
    'Posts no LinkedIn':
        'Posts on LinkedIn',
    'Reels no Instagram':
        'Reels on Instagram',
    'Canal no YouTube':
        'YouTube channel',
    'Conhecer os serviços':
        'Explore the services',
    'Os cinco serviços do Grupo OM, com as soluções de cada um e o case que o comprova.':
        "Grupo OM's five services, each with its solutions and the case that proves it.",
    'Cinco frentes,':
        'Five fronts,',
    'Como ler esta página':
        'How to read this page',
    'Cada serviço traz as soluções que o grupo publica e':
        'Each service lists the solutions the group publishes and',
    'um case real que o comprova':
        'a real case that proves it',
    ': promessa aqui vem com prova ao lado.':
        ': every promise here comes with proof beside it.',
    'O case que comprova':
        'The case that proves it',
    'Falar com o Grupo OM':
        'Talk to Grupo OM',
    'Marketing digital e de performance':
        'Digital and performance marketing',
    'Sua marca em todos os lugares que importam':
        'Your brand everywhere it matters',
    'Resultados que vão além do clique':
        'Results that go beyond the click',
    'Decisões guiadas por dados e estratégia':
        'Decisions guided by data and strategy',
    'Conexões que fidelizam e engajam':
        'Connections that build loyalty and engagement',
    'Projetos completos de branding':
        'End-to-end branding projects',
    'Consultoria de propósito e posicionamento':
        'Purpose and positioning consulting',
    'Identidade visual e verbal':
        'Visual and verbal identity',
    'Design de embalagens':
        'Packaging design',
    'Projetos de lojas e jornada do consumidor':
        'Store design and consumer journey',
    'Visual merchandising e PDV':
        'Visual merchandising and point of sale',
    'Stands para feiras e eventos':
        'Stands for fairs and events',
    'Planejamento e consultoria em comunicação':
        'Communications planning and consulting',
    'Criação de campanhas integradas':
        'Integrated campaign creation',
    'Planejamento, gestão e checking de mídia':
        'Media planning, management and checking',
    'Campanhas regionais e nacionais':
        'Regional and national campaigns',
    'Gestão de mesas de performance':
        'Performance desk management',
    'SEO':
        'SEO',
    'Criação e gestão de conteúdo digital':
        'Digital content creation and management',
    'Estratégias de inbound marketing':
        'Inbound marketing strategies',
    'Data strategy & analytics':
        'Data strategy & analytics',
    'Suporte à digitalização de vendas':
        'Sales digitalisation support',
    'Estudos e diagnósticos de mídia':
        'Media studies and diagnostics',
    'Planejamento orientado por dados':
        'Data-driven planning',
    'Regionalização de campanhas':
        'Campaign regionalisation',
    'Consultoria em comunicação para agências e empresas':
        'Communications consulting for agencies and companies',
    'Programas de relacionamento e incentivo':
        'Loyalty and incentive programmes',
    'Endomarketing':
        'Internal marketing',
    'Desenvolvimento de plataformas digitais':
        'Digital platform development',
    'Experiências digitais interativas':
        'Interactive digital experiences',
    'Criação e gestão de mídias proprietárias':
        'Owned media creation and management',
    'Videocase O Boticário :: comunicação regional':
        'Video case O Boticário :: regional communications',
    'Brainbox :: Videocase Ítalo Supermercados':
        'Brainbox :: Ítalo Supermercados video case',
    'ESG :: Três letras que fazem toda a diferença':
        'ESG :: Three letters that make all the difference',
    'Retail Trends :: Pós-NRF':
        'Retail Trends :: Post-NRF',
    'Soundbrand Grupo OM':
        'Grupo OM Soundbrand',
    'Agência de marketing para indústrias: como escolher?':
        'A marketing agency for industry: how to choose one?',
    'Saiba como escolher uma agência de marketing para indústrias capaz de integrar estratégia, branding, mídia, performance e geração de demanda.':
        'Learn how to choose a marketing agency for industry able to integrate strategy, branding, media, performance and demand generation.',
    'COO (Chief Operating Officer): o que faz?':
        'COO (Chief Operating Officer): what do they do?',
    'Entenda o que faz um COO, como atua na operação da empresa e por que esse cargo é estratégico para marketing, vendas e crescimento.':
        "Understand what a COO does, how they run the company's operation and why the role is strategic for marketing, sales and growth.",
    'Founder-Led Growth: como transformar a autoridade do fundador em crescimento':
        "Founder-Led Growth: turning the founder's authority into growth",
    'ICE Score: como priorizar ações de marketing e growth':
        'ICE Score: how to prioritise marketing and growth initiatives',
    'Entenda o que é ICE Score, como calcular, quando usar e como adaptar essa matriz para priorizar ações de marketing.':
        'Understand what the ICE Score is, how to calculate it, when to use it and how to adapt the matrix to prioritise marketing initiatives.',
    'Marketing no PDV: como aumentar as vendas?':
        'Point-of-sale marketing: how to increase sales?',
    'Conheça métodos e estratégias do marketing no PDV para melhorar a experiência de compra, aumentar a conversão e impulsionar as vendas.':
        'Discover point-of-sale marketing methods and strategies to improve the shopping experience, raise conversion and drive sales.',
    'NCT: O que é?':
        'NCT: what is it?',
    'Entenda o que é NCT, como funciona o framework de Narrativa, Compromissos e Tarefas e como aplicá-lo à gestão de marketing.':
        'Understand what NCT is, how the Narratives, Commitments and Tasks framework works and how to apply it to marketing management.',
    'Social Selling: como vender mais nas redes sociais':
        'Social Selling: how to sell more on social networks',
    'Entenda o que é Social Selling, seus benefícios e como usar conteúdo, relacionamento e dados para gerar leads, reduzir o CPL e vender mais.':
        'Understand what Social Selling is, its benefits and how to use content, relationships and data to generate leads, cut CPL and sell more.',
    'Value Proposition Canvas: como alinhar cliente, proposta de valor e crescimento do negócio':
        'Value Proposition Canvas: aligning customer, value proposition and business growth',
    'Processos industriais estão cada vez mais conectados, automatizados e orientados por dados. Segundo a Pesquisa de Inovação Semestral do IBGE, 89,1% das empresas industriais brasileiras com 100 ou mais pessoas ocupadas utilizaram ao menos uma tecnologia digital avançada em 2024. Entre elas, 42% já empregavam inteligência artificial em suas atividades.':
        "Industrial processes are increasingly connected, automated and data-driven. According to IBGE's Semi-annual Innovation Survey, 89.1% of Brazilian industrial companies with 100 or more employees used at least one advanced digital technology in 2024. Among them, 42% were already employing artificial intelligence in their activities.",
    'Apesar desse avanço, a comunicação de muitas indústrias ainda permanece concentrada em materiais institucionais, catálogos técnicos, feiras e ações pontuais de geração de leads. O resultado costuma ser um marketing fragmentado, com pouco reconhecimento de marca, dificuldade para demonstrar diferenciais e uma dependência excessiva da equipe comercial.':
        'Despite that progress, many industrial companies still concentrate their communications on institutional materials, technical catalogues, trade fairs and one-off lead-generation efforts. The usual result is fragmented marketing, with little brand recognition, difficulty demonstrating differentiators and an excessive dependence on the sales team.',
    'Por isso, escolher uma agência de marketing para indústrias exige mais do que analisar campanhas criativas ou comparar propostas de mídia. A indústria precisa de um parceiro capaz de compreender seu modelo comercial, organizar a comunicação e transformar conhecimento técnico em argumentos relevantes para diferentes públicos.':
        'Choosing a marketing agency for industry therefore takes more than reviewing creative campaigns or comparing media proposals. Industry needs a partner able to understand its commercial model, organise its communications and turn technical knowledge into arguments that matter to different audiences.',
    'Toda empresa que cresce chega a um ponto em que a operação precisa acompanhar a ambição do negócio. No início, muitos processos funcionam porque as equipes são menores, as decisões estão concentradas em poucas pessoas e os ajustes acontecem de forma mais rápida. Com o tempo, esse modelo começa a mostrar limites.':
        "Every growing company reaches a point where the operation must keep pace with the business's ambition. Early on, many processes work because teams are smaller, decisions sit with a few people and adjustments happen quickly. Over time, that model starts to show its limits.",
    'As áreas se multiplicam, os canais de venda aumentam, o marketing passa a lidar com mais campanhas, o comercial precisa de previsibilidade, a tecnologia entra com mais força e a marca começa a ser cobrada por uma entrega mais consistente. Nesse cenário, o crescimento passa a exigir coordenação.':
        'Departments multiply, sales channels grow, marketing juggles more campaigns, sales needs predictability, technology gains weight and the brand is pressed for a more consistent delivery. In that scenario, growth starts to demand coordination.',
    'A sigla aparece com frequência em empresas em expansão, mas ainda gera dúvidas. Afinal, COO: o que faz ? Esse profissional cuida apenas de processos internos? Atua como braço direito do CEO? Participa de decisões estratégicas? Tem relação com marketing e vendas?':
        "The title appears often in expanding companies, yet it still raises questions. After all, what does a COO do? Does this professional only handle internal processes? Act as the CEO's right hand? Take part in strategic decisions? Touch marketing and sales?",
    'Durante muito tempo, a comunicação empresarial concentrou sua atenção na marca institucional. Campanhas, anúncios, conteúdos e pronunciamentos eram desenvolvidos para representar a empresa, enquanto fundadores e CEOs permaneciam principalmente nos bastidores.':
        'For a long time, corporate communications focused on the institutional brand. Campaigns, ads, content and statements were built to represent the company, while founders and CEOs stayed mostly backstage.',
    'As redes sociais mudaram essa dinâmica. Hoje, clientes, investidores, parceiros e profissionais conseguem acompanhar diretamente quem toma decisões, define prioridades e conduz os negócios. Nesse ambiente, a presença pública do fundador pode ampliar o alcance da empresa, fortalecer sua reputação e abrir conversas comerciais que dificilmente começariam por um anúncio tradicional.':
        "Social networks changed that dynamic. Today, clients, investors, partners and professionals can directly follow whoever makes the decisions, sets the priorities and runs the business. In that environment, the founder's public presence can extend the company's reach, strengthen its reputation and open commercial conversations that would hardly start from a traditional ad.",
    'Toda equipe de marketing conhece bem esse cenário: há dezenas de ideias na mesa, várias campanhas possíveis, múltiplos canais para testar, melhorias pendentes no site, demandas de vendas, oportunidades em SEO , ajustes em mídia paga e, claro, aquela sensação de que tudo é urgente. O problema é que nem tudo pode ser feito ao mesmo tempo, e escolher no “feeling” pode custar tempo, dinheiro e foco estratégico.':
        'Every marketing team knows the scene: dozens of ideas on the table, several possible campaigns, multiple channels to test, pending site improvements, sales requests, SEO opportunities, paid-media adjustments and, of course, the feeling that everything is urgent. The problem is that not everything can be done at once, and choosing by gut feel can cost time, money and strategic focus.',
    'É nesse contexto que o ICE Score aparece como a metodologia que ajuda a organizar ideias, comparar oportunidades e definir prioridades com base em critérios simples: impacto, confiança e facilidade.':
        'That is where the ICE Score comes in: a methodology that helps organise ideas, compare opportunities and set priorities based on simple criteria — impact, confidence and ease.',
    'Mais do que uma fórmula, o ICE Score funciona como uma lente para transformar hipóteses em decisões mais claras. Ele não elimina a intuição, mas evita que ela dirija sozinha sem GPS. Para gerentes de growth marketing e analistas de marketing, essa matriz pode apoiar desde a priorização de testes de conversão até a escolha de pautas de marketing de conteúdo , campanhas de mídia paga, melhorias de SEO e ações integradas com vendas.':
        'More than a formula, the ICE Score works as a lens for turning hypotheses into clearer decisions. It does not remove intuition, but it keeps intuition from driving alone without a GPS. For growth managers and marketing analysts, the matrix can support anything from prioritising conversion tests to choosing content topics, paid-media campaigns, SEO improvements and initiatives integrated with sales.',
    'O ponto de venda concentra uma etapa decisiva da jornada de compra. É nele que a intenção construída por campanhas, conteúdos e recomendações encontra fatores concretos como preço, disponibilidade, exposição, atendimento e facilidade para concluir o pedido.':
        'The point of sale concentrates a decisive stage of the purchase journey. It is where the intent built by campaigns, content and recommendations meets concrete factors such as price, availability, display, service and how easy it is to complete the order.',
    'Por isso, o marketing no PDV reúne estratégias utilizadas para tornar produtos e marcas mais visíveis, relevantes e convincentes no momento da decisão. A atuação envolve a organização do espaço, os materiais de comunicação, as promoções, a experiência sensorial, o treinamento das equipes e a integração com canais digitais.':
        'Point-of-sale marketing therefore gathers the strategies used to make products and brands more visible, relevant and convincing at the moment of decision. The work spans store layout, communication materials, promotions, sensory experience, staff training and integration with digital channels.',
    'Essa disciplina está diretamente ligada ao trade marketing , responsável por conectar indústria, distribuidores, varejistas e consumidores. Enquanto campanhas publicitárias ajudam a gerar interesse, o trabalho no PDV prepara o canal para transformar essa demanda em vendas.':
        'The discipline is directly tied to trade marketing, which connects industry, distributors, retailers and consumers. While advertising campaigns help generate interest, the work at the point of sale prepares the channel to turn that demand into sales.',
    'Em ambientes de marketing cada vez mais pressionados por performance, eficiência e clareza estratégica, um dos maiores desafios está em transformar essas metas em uma direção compreensível, acionável e acompanhável por todo o time.':
        'In marketing environments under growing pressure for performance, efficiency and strategic clarity, one of the biggest challenges is turning those goals into a direction the whole team can understand, act on and track.',
    'A sigla NCT vem de Narratives, Commitments and Tasks , ou, em português, Narrativas, Compromissos e Tarefas . Trata-se de um framework de definição e acompanhamento de objetivos que conecta a estratégia ao trabalho do dia a dia, criando uma linha clara entre o motivo pelo qual uma empresa quer avançar, os compromissos que precisa assumir e as tarefas necessárias para chegar lá.':
        'NCT stands for Narratives, Commitments and Tasks. It is a goal-setting and tracking framework that connects strategy to everyday work, drawing a clear line between why a company wants to move, the commitments it must make and the tasks required to get there.',
    'Esse modelo pode ser especialmente útil porque ajuda a organizar prioridades em um cenário cheio de frentes simultâneas: marca, mídia, conteúdo, CRM , SEO , vendas, dados, eventos, campanhas e relacionamento com o cliente. Sem uma estrutura clara, o time corre o risco de confundir movimento com progresso.':
        'The model is especially useful because it helps organise priorities in a scenario full of simultaneous fronts: brand, media, content, CRM, SEO, sales, data, events, campaigns and customer relationships. Without a clear structure, the team risks mistaking motion for progress.',
    'As redes sociais deixaram de ocupar apenas o início da jornada de compra. Hoje, uma pessoa pode conhecer um produto no TikTok, pesquisar avaliações no YouTube, tirar dúvidas pelo Instagram, pedir uma recomendação pelo WhatsApp e concluir a compra sem passar por uma loja física.':
        'Social networks no longer occupy only the start of the purchase journey. Today a person can discover a product on TikTok, research reviews on YouTube, ask questions on Instagram, request a recommendation on WhatsApp and complete the purchase without stepping into a physical store.',
    'No mercado B2B , o percurso muda de formato, mas segue a mesma lógica. Um gestor pode acompanhar especialistas da empresa, consumir conteúdos técnicos, participar de um webinar e iniciar uma conversa comercial somente depois de reconhecer que aquela marca compreende o seu desafio.':
        "In the B2B market the route changes shape but follows the same logic. A manager may follow the company's specialists, consume technical content, join a webinar and only start a commercial conversation after recognising that the brand understands their challenge.",
    'Essas jornadas mostram que a venda pode ser construída ao longo de diferentes interações. É justamente esse processo que orienta o Social Selling .':
        'These journeys show that a sale can be built across different interactions. That process is precisely what guides Social Selling.',
    'Toda empresa quer vender mais, conquistar clientes melhores e se diferenciar em um mercado cada vez mais competitivo. Porém, quando olhamos para a rotina de gerentes comerciais e gerentes de marketing, percebemos que boa parte dos desafios não começa exatamente na venda, na campanha ou na negociação.':
        'Every company wants to sell more, win better clients and stand out in an ever more competitive market. Yet when we look at the routine of sales and marketing managers, much of the challenge does not exactly start at the sale, the campaign or the negotiation.',
    'Muitas vezes, o problema está antes: na forma como a empresa compreende o cliente e transforma essa compreensão em uma proposta de valor clara.':
        'Often the problem comes earlier: in how the company understands the customer and turns that understanding into a clear value proposition.',
    'Entenda como o Founder-Led Growth usa a autoridade do fundador para fortalecer a marca, gerar demanda e reduzir indicadores como CPL e CAC.':
        "Understand how Founder-Led Growth uses the founder's authority to strengthen the brand, generate demand and reduce indicators such as CAC.",
    'Entenda como usar o Value Proposition Canvas para alinhar marketing e vendas, fortalecer sua proposta de valor e avançar rumo ao Product Market Fit.':
        'Understand how to use the Value Proposition Canvas to align marketing and sales, strengthen your value proposition and advance towards Product-Market Fit.',
    "Ao topo":
        "Back to top",
    "Voltar ao topo":
        "Back to the top",
    "Certificações e parcerias":
        "Certifications and partnerships",
}


def tradutor(lang: str) -> Callable[[str], str]:
    """Devolve a função que os templates chamam de `T`.

    Em português ela é a IDENTIDADE, de propósito: o texto dos templates já é o
    português final, e fazer o caminho de ida e volta por um dicionário para
    devolver a mesma frase seria trabalho por página, em toda página, para
    nunca mudar nada.

    Em inglês ela cai no português quando a entrada falta. É a escolha certa
    para o visitante (uma palavra não traduzida é melhor que um buraco) e a
    errada para quem escreve, e por isso ela não é a única guarda: o teste que
    varre os templates é quem impede a falta de chegar até aqui.
    """
    if lang != "en":
        return lambda frase: frase
    return lambda frase: EN.get(frase, frase)
