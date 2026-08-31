"""Os DEZOITO cases reais do Grupo OM, as seis empresas e as sete categorias.

POR QUE ISTO SAIU DO TEMPLATE (itens 19 e 27). Até o ciclo anterior os cases
moravam num `{% set %}` dentro de `_dados_cases.html`, e cinco cases escritos à
mão cabiam ali. Dezoito cases com data, categoria, imagem, ficha técnica e
filtro não cabem: o filtro por empresa e por categoria é resolvido NO SERVIDOR,
e um dado que o servidor precisa validar não pode viver só dentro do Jinja.

A lista fechada de valores aceitos pelo filtro sai daqui, e é a MESMA lista que
alimenta a grade. Se as duas morassem em arquivos diferentes, o dia em que uma
categoria mudasse de nome produziria um filtro que responde 404 para um chip
que a própria página desenhou.

TUDO AQUI FOI COLHIDO DO SITE DO CLIENTE, e está conferido em
`grupoom-material-2.md` e `grupoom-cases.json`. Nada é inventado:

  - as seis cores são as que o site do cliente carrega em `data-color`, e a
    cor de contraste é a que ele mesmo declara em `data-contrast`;
  - as datas e as categorias são as do HTML do cliente. CINCO cases não trazem
    categoria nenhuma, e para esses `categoria` é `None`: eles entram na grade
    sem etiqueta e somem do filtro, que é o comportamento honesto;
  - o texto é o texto publicado. O `resumo` é uma condensação dele, com a
    MESMA medida em todos os dezoito (item 19), porque um cartão de quatro
    linhas ao lado de um de uma linha é o que faz uma grade parecer rascunho.

O SLUG É NOSSO, e não o do cliente. Quatro dos slugs originais começam por
número ou trazem dígitos (`38777`, `tarja-violeta-2`), e a peneira de
`rotas_sites.py::_NOME_DE_PAGINA` só aceita minúscula e hífen, começando por
letra. Inventar uma segunda peneira mais frouxa para caber o slug do cliente
seria abrir uma segunda porta para a travessia de diretório, e a segunda porta
é sempre a que fica sem tranca.

A ARTE DO CASE VEM DAQUI, não do servidor do cliente. Cada imagem foi baixada,
convertida para webp de 960x540 e servida de
`/static/lab/sites/grupo-om/cases/`. A Global Constraint 11 proíbe host
externo, e a peça se contradiria se acusasse o site do cliente de peso enquanto
puxa dezoito JPEGs de 1920 px do servidor dele.

O VÍDEO NÃO ENTRA, e a ausência é decisão, não esquecimento: os dezoito cases
do cliente embutem um `iframe` do YouTube, que é host externo de script e de
rastreamento. A imagem que entra no lugar É o quadro de destaque que o próprio
cliente publica para aquele filme. Está em Pendências.
"""
from __future__ import annotations

# ==========================================================================
# AS SEIS EMPRESAS
#
# `cor` e `contraste` são do site do cliente, e valem SÓ no hover do cartão
# desta empresa. Elas não viram cor de texto, de título, de link nem de fundo
# de seção em lugar nenhum da peça: o Grupo OM é monocromático, e o arco-íris
# nunca toca a marca. É a regra que já custou um ciclo.
#
# `contraste` é "branco" ou "preto", e decide DUAS coisas de uma vez: a cor do
# texto sobre a cor da empresa, e se o logo (que é preto no arquivo) continua
# invertido no hover ou volta ao preto original.
# ==========================================================================
EMPRESAS = (
    {"chave": "opus-multipla", "nome": "OpusMúltipla",
     "arquivo": "logo_opusmultipla_preto.svg", "w": 420, "h": 113,
     "cor": "#da0812", "contraste": "branco",
     "site": "https://opusmultipla.com.br/"},
    {"chave": "dom", "nome": "D’OM Soluções Improváveis",
     "arquivo": "logo_dom_preto.svg", "w": 373, "h": 119,
     "cor": "#00274f", "contraste": "branco",
     "site": "https://dom-solucoes.com/"},
    {"chave": "senso", "nome": "Senso",
     "arquivo": "logo_senso_preto.svg", "w": 244, "h": 102,
     "cor": "#009a93", "contraste": "branco",
     "site": "https://sensoperformance.com.br/"},
    {"chave": "brain-box", "nome": "Brainbox",
     "arquivo": "logo_brainbox.svg", "w": 503, "h": 136,
     "cor": "#fecc00", "contraste": "preto",
     "site": "https://brainboxdesign.com.br/"},
    {"chave": "house-cricket", "nome": "House Cricket",
     "arquivo": "logo_housecricket_preto.svg", "w": 343, "h": 100,
     "cor": "#b9ba21", "contraste": "preto",
     "site": "https://housecricket.com.br/"},
    {"chave": "tailor-media", "nome": "Tailor Media",
     "arquivo": "logo_tailormedia_preto.svg", "w": 477, "h": 99,
     "cor": "#283772", "contraste": "branco",
     "site": "https://tailormedia.com.br/"},
)

# O GRUPO NÃO É UMA SÉTIMA EMPRESA, e por isso ele não está na tupla acima: ele
# não tem cor, não tem cartão e não tem site próprio para linkar de dentro da
# peça. Ele assina cinco dos dezoito cases, e para esses a assinatura é o
# wordmark, monocromático como sempre.
GRUPO = {"chave": "grupo-om", "nome": "Grupo OM",
         "arquivo": "marca-grupo-om.svg", "w": 1147, "h": 104}

_POR_CHAVE = {e["chave"]: e for e in EMPRESAS}
_POR_CHAVE[GRUPO["chave"]] = GRUPO


def assinante(chave: str) -> dict:
    """Quem assina um case: uma das seis, ou o próprio grupo."""
    return _POR_CHAVE[chave]


# ==========================================================================
# AS SETE CATEGORIAS
#
# São as do filtro do site do cliente, com o nome EXATO que ele escreve. Três
# delas (Design, Marketing, Motion) não têm nenhum case entre os dezoito
# publicados: elas continuam na lista fechada, porque a lista é do cliente, e
# o chip delas não é desenhado, porque um filtro que leva a uma grade vazia é
# um beco sem saída dentro de uma proposta comercial.
# ==========================================================================
CATEGORIAS = (
    ("branding", "Branding"),
    ("campanhas", "Campanhas"),
    ("comunicacao-integrada", "Comunicação Integrada"),
    ("design", "Design"),
    ("digital", "Digital"),
    ("marketing", "Marketing"),
    ("motion", "Motion"),
)
NOME_DA_CATEGORIA = dict(CATEGORIAS)


def _c(slug, titulo, empresa, categoria, data, resumo, corpo, ficha=()):
    return {
        "slug": slug,
        "titulo": titulo,
        "empresa": empresa,
        "categoria": categoria,
        "data": data,
        # A MESMA data em dois formatos, e o segundo não é firula: `01/07/2025`
        # é dia/mês para quem lê a página em português e vira 7 de janeiro na
        # cabeça de quem lê em inglês. O `<time datetime>` recebe o ISO, que é
        # o que a máquina lê, e a página em inglês MOSTRA o ISO, que é o único
        # formato numérico que não tem duas leituras.
        "iso": f"{data[6:10]}-{data[3:5]}-{data[0:2]}",
        "imagem": f"/static/lab/sites/grupo-om/cases/{slug}.webp",
        "resumo": resumo,
        "corpo": list(corpo),
        "ficha": list(ficha),
    }


CASES = (
    _c("ilha-urbana-malbec-ultra-bleu", "Ilha Urbana Malbec Ultra Bleu",
       "opus-multipla", "campanhas", "01/07/2025",
       "O case da Ilha Urbana que divulgou o Malbec Ultra Bleu, do Boticário, "
       "uniu impacto e criatividade num espaço que chamou a atenção nas ruas "
       "de São Paulo.",
       ["Como comunicar com impacto e criatividade?",
        "O case da Ilha Urbana que divulgou o Malbec Ultra Bleu, do Boticário, "
        "soube unir esses dois aspectos com maestria.",
        "A OpusMúltipla criou um espaço que chamou a atenção nas ruas de São "
        "Paulo e elevou a outro patamar a veiculação da campanha.",
        "Essa estratégia garantiu o Bronze na categoria Media dos Prémios "
        "Lusófonos da Criatividade 2025."],
       [("VP de Conteúdo e Integração", "Mário D’Andrea")]),

    _c("a-volta-ao-mundo", "A Volta Ao Mundo em 80.000 KM",
       "grupo-om", "campanhas", "08/05/2025",
       "O novo UltraContact da Continental foi lançado com garantia de 80 mil "
       "km, e a D’OM criou a sequência do clássico “A volta ao mundo em 80 "
       "dias”, de Júlio Verne.",
       ["O novo UltraContact da Continental foi lançado com garantia de 80 mil "
        "km, algo nunca visto no mercado. Para marcar esse lançamento, algo "
        "também nunca visto: a D’OM criou a sequência do clássico “A volta ao "
        "mundo em 80 dias”, de Júlio Verne.",
        "O novo livro “A volta ao mundo em 80 mil km” foi escrito e inspirado "
        "no estilo e linguagem do autor, com ajuda do ChatGPT. São 310 páginas "
        "de aventura, romance, tecnologia e arte.",
        "Nove meses de trabalho, versão audiobook, versão digital, versão em "
        "inglês, dicas das centenas de localidades visitadas pelos personagens, "
        "seu carro e seus pneus UltraContact. E ainda uma sobrecapa com "
        "mapa-múndi especial mostrando todo o trajeto pelos vários continentes.",
        "A D’OM acredita nisso: ideias que vão além das fronteiras da "
        "propaganda e criam conversas entre marcas e pessoas."],
       [("Produção gráfica e arte-final",
         "Marcos Miranda, Luciano Rodrigues, Helton Schnitzler, "
         "Maria Paula Mosimann, Cibele Cardozo"),
        ("Produção e art buyer", "Bianca Mascarenhas, Michele Franco")]),

    _c("contrastes-afece", "Contrastes",
       "opus-multipla", None, "12/08/2026",
       "A campanha pro bono da Afece reforça a importância de abrir caminhos "
       "para o desenvolvimento e a autonomia de pessoas com deficiências "
       "múltiplas.",
       ["A publicidade tem o poder de transformar realidades.",
        "Foi com esse propósito que criamos a nova campanha pro bono da Afece, "
        "“Contrastes”, que reforça a importância de abrir caminhos para o "
        "desenvolvimento e a autonomia de pessoas com deficiências múltiplas. "
        "Com produção da The Youth, pós-produção da Colossal e trilha e "
        "finalização de áudio assinadas pela Canja, o filme transforma o “não” "
        "em convite à inclusão e mostra como o suporte transforma histórias."],
       [("Diretora de Comunicação Corporativa", "Camila Rodrigues Guedes"),
        ("Coordenador de Comunicação Corporativa", "Leonardo Hideki Tonooka"),
        ("Gestão Estratégica de Marcas", "Cecília Godoy"),
        ("Gerente de Estratégia e Consumer Insights", "Guilherme Silveira")]),

    _c("clash-no-catamara", "Clash no Catamarã",
       "opus-multipla", "campanhas", "01/07/2025",
       "O case de ativação do Clash, do Boticário, uniu comunicação regional e "
       "criatividade: pela primeira vez, o Catamarã de Porto Alegre virou "
       "mídia.",
       ["Como levar uma marca onde ninguém chegou ainda?",
        "O case de ativação de marca do Clash, do Boticário, uniu comunicação "
        "regional e criatividade para fazer isso. Pela primeira vez, o Catamarã "
        "de Porto Alegre virou mídia e estampou o novo perfume da marca.",
        "Tudo isso com estratégia, planejamento e execução da OpusMúltipla. O "
        "case conquistou a Prata na categoria Ativação de Marca dos Prémios "
        "Lusófonos da Criatividade."],
       [("VP de Conteúdo e Integração", "Mário D’Andrea"),
        ("Supervisor de Atendimento", "Felippe Brana")]),

    _c("frimesa-fogo-sabor", "Frimesa Fogo & Sabor",
       "grupo-om", "campanhas", "02/05/2025",
       "A campanha faz uma analogia entre a descoberta do fogo e a experiência "
       "de sabor dos produtos da linha premium da Frimesa, divulgada de "
       "maneira integrada.",
       ["A campanha “Fogo & Sabor” foi criada pela OpusMúltipla para a Frimesa.",
        "Desenvolvida para apresentar os novos produtos da linha premium da "
        "marca, a campanha faz uma analogia entre a descoberta do fogo e a "
        "experiência de sabor proporcionada pelos produtos da linha.",
        "A divulgação foi realizada de maneira integrada, por diferentes canais "
        "e com ações e ativações variadas para fortalecer a marca e enfatizar "
        "os atributos de inovação, versatilidade e praticidade."],
       [("Diretor de Estratégia e Consumer Insights", "Rodrigo Rodrigues")]),

    _c("gargantas-valda", "Gargantas Valda",
       "grupo-om", None, "08/05/2025",
       "Uma maneira criativa e cômica de mostrar que as pastilhas Valda são a "
       "salvação para qualquer hora, em três filmes criados pela D’OM.",
       ["Conheça as Gargantas Valda, criadas pela D’OM.",
        "Uma maneira criativa e cômica de mostrar que as pastilhas Valda são a "
        "salvação para qualquer hora."],
       [("Agência", "D’OM"),
        ("Cliente", "Valda, do Grupo Eurofarma"),
        ("Filmes", "Frente Fria, Call, Futebol"),
        ("Diretor da Unidade de Negócios OTC", "Donino Scherer Neto")]),

    _c("geracao-de-fluxo-no-dia-dos-pais",
       "Geração de fluxo em lojas no Dia dos Pais",
       "opus-multipla", "campanhas", "17/11/2025",
       "A OpusMúltipla e o Google combinaram vídeos no YouTube e Performance "
       "Max Offline, com redução de 14% no custo por visita e crescimento nas "
       "vendas.",
       ["Como uma estratégia de mídia bem executada pode fazer diferença nas "
        "vendas?",
        "A OpusMúltipla e o Google se uniram com o objetivo de gerar fluxo de "
        "loja no Dia dos Pais para as praças do Rio de Janeiro do Boticário.",
        "A estratégia combinou o uso de vídeos no YouTube e Performance Max "
        "Offline no Google Ads.",
        "O resultado: redução de 14% no custo por visita e um crescimento de 2 "
        "pontos percentuais nas vendas do Rio de Janeiro em comparação com o "
        "Dia das Mães.",
        "O case completo entrou para a galeria do Google."]),

    _c("junto-com-a-mamy", "Junto com a Mamy",
       "dom", None, "07/05/2026",
       "A campanha do novo posicionamento da MamyPoko foge da comunicação da "
       "categoria e coloca o holofote em quem está por trás de todo o cuidado: "
       "a mãe.",
       ["A exaustão materna é uma realidade para a maioria das mulheres, e foi "
        "com esse olhar que a D’OM Soluções Improváveis desenvolveu a campanha "
        "que marca o novo posicionamento da MamyPoko.",
        "Fugindo da comunicação tradicional da categoria, que costuma focar "
        "exclusivamente no bebê, a campanha “Junto com a mamy, até no nome” "
        "coloca o holofote em quem está por trás de todo o cuidado: a mãe.",
        "O conceito busca desmistificar a ideia de perfeição, abraçando as "
        "dúvidas, os desafios e as imperfeições que fazem parte do dia a dia "
        "das famílias.",
        "A estratégia une o apoio emocional ao benefício funcional, destacando "
        "que produtos que garantem noites secas para o bebê proporcionam o "
        "descanso que a mãe tanto precisa.",
        "Com um tom de voz humano e próximo, a marca reafirma que as mães não "
        "estão sozinhas nessa jornada."]),

    _c("m-possibilidades", "M Possibilidades",
       "opus-multipla", "campanhas", "12/03/2025",
       "A campanha institucional do Shopping Mueller usou inteligência "
       "artificial para criar texturas, movimentos e cores, e transformar o "
       "icônico M do mall.",
       ["Esta é a campanha institucional do Shopping Mueller.",
        "Intitulada de “M possibilidades”, a campanha criada pela OpusMúltipla "
        "utilizou recursos da inteligência artificial para criar diferentes "
        "texturas, movimentos e cores.",
        "Assim, transformamos o icônico M que simboliza o mall em uma marca "
        "ainda mais potente e diversa."],
       [("Diretor de Gestão Estratégica de Marcas", "Dino Camargo"),
        ("Gestão Estratégica de Marcas",
         "Ana Carolina Grevinski, Samarine Neves, Naomi Nozu")]),

    _c("memes-unidos", "Memes Unidos",
       "grupo-om", "campanhas", "08/05/2025",
       "A campanha da Vero Internet é uma passeata de memes tomando conta da "
       "cidade, numa mistura de inteligência artificial e muita criatividade.",
       ["Já imaginou uma passeata de memes tomando conta da cidade?",
        "Essa é a proposta da nova campanha da Vero Internet, criada pela "
        "D’OM: uma manifestação com os memes mais quentes do mundo online, em "
        "uma mistura de inteligência artificial e muita criatividade."],
       [("Produção eletrônica e fotos",
         "Bianca Mascarenhas, Michele Franco"),
        ("Coordenação de pós-produção", "Ale Cois, Sabrina Comar"),
        ("Atendimento e coordenação", "Nic Bonnet")]),

    _c("natal-iluminado", "Natal Iluminado",
       "opus-multipla", "campanhas", "16/12/2025",
       "O filme de fim de ano da Uninter narra a história de uma menina que "
       "cresce num vilarejo sem eletricidade e busca na Engenharia Elétrica o "
       "conhecimento.",
       ["A OpusMúltipla apresenta “Natal Iluminado”, o novo filme de fim de ano "
        "criado para a Uninter.",
        "Nesta produção emocionante, narramos a história de uma menina que "
        "cresce em um vilarejo sem eletricidade e, movida pelo desejo de "
        "aprender, busca na Engenharia Elétrica o conhecimento para transformar "
        "a realidade de sua comunidade.",
        "Mais do que uma campanha, esta obra simboliza a crença da "
        "OpusMúltipla no poder das boas histórias e a missão da Uninter em "
        "mostrar que a educação é a força mais potente de transformação "
        "individual e coletiva."]),

    # O CASE "NINFA" SAIU EM 27/08, por decisão do Leandro (item 34). Ele
    # continua publicado no site do cliente, e a peça não o mostra: a imagem
    # de destaque que o WordPress do cliente serve para ele é a do "Natal
    # Iluminado", com o nome do primeiro
    # (`OPU-0068-25_-Natal-Uninter-Site-GOM.png`, numa pasta de fevereiro de
    # 2026). Nós copiamos o que está publicado, e o que está publicado está
    # trocado: uma proposta que mostra ao dono da agência a arte errada em
    # cima do nome de um cliente dele perde a reunião num segundo. Vale
    # perguntar, e enquanto não houver resposta o case não existe aqui.
    #
    # NADA MAIS PRECISOU MUDAR POR CAUSA DISTO, e é essa a prova de que as
    # contagens são derivadas: `EMPRESAS_COM_CASE`, `CATEGORIAS_COM_CASE` e
    # tudo que a grade, o filtro e o trilho contam saem desta tupla. A
    # categoria "Comunicação Integrada" perdeu o único case que a assinava e
    # o chip dela sumiu sozinho, que é exatamente o que a regra manda.

    _c("o-futuro-e-agora-ou-agora", "O futuro é agora ou agora",
       "opus-multipla", None, "06/08/2026",
       "Para os 35 anos da Fundação Grupo Boticário, o Canal Off saiu do ar em "
       "uma ação inédita e um mapa exclusivo no Fortnite conversou com a "
       "Geração Z.",
       ["Para comemorar os 35 anos da Fundação Grupo Boticário, criamos uma "
        "campanha que se transformou em um verdadeiro chamado pela natureza.",
        "Deixamos o Canal Off, um dos maiores canais de natureza do Brasil, "
        "fora do ar em uma ação inédita.",
        "Criamos um mapa exclusivo com missões especiais dentro do Fortnite, em "
        "uma conversa direta com a Geração Z.",
        "O resultado foi além dos números e deixou clara a importância de ações "
        "que evidenciam o pedido de socorro do meio ambiente."]),

    _c("play-no-enem", "Play no Enem",
       "opus-multipla", None, "20/01/2026",
       "As peças dão enfoque à facilidade de usar as notas do Enem para "
       "conquistar uma graduação, em TV aberta, digital, mídia exterior e "
       "rádio em Curitiba.",
       ["A OpusMúltipla e a Uninter apresentam a nova campanha Play no Enem.",
        "As peças dão enfoque à facilidade de usar as notas do Exame Nacional "
        "do Ensino Médio para conquistar uma graduação e mudar o futuro por "
        "meio da educação.",
        "Além de o filme figurar na TV aberta e no meio digital, criamos peças "
        "de comunicação exterior e spot de rádio para as praças de Curitiba."]),

    _c("sonhos-possiveis", "Sonhos Possíveis",
       "dom", "campanhas", "03/01/2024",
       "A Continental Pneus fez uma surpresa para dois atletas mirins que "
       "sonham em jogar futebol e acompanharam a final da Copa do Brasil no "
       "estádio.",
       ["O case “Sonhos Possíveis” foi criado pela D’OM Soluções Improváveis "
        "para a Continental Pneus, patrocinadora da Copa do Brasil.",
        "A marca fez uma grande surpresa para dois atletas mirins, a Heloiza e "
        "o Pedro, que sonham em jogar futebol profissionalmente e puderam "
        "acompanhar a final do campeonato no estádio, com toda a emoção e "
        "inspiração.",
        "A ação contou com a participação da FIFA Legend Formiga, uma das mais "
        "consagradas jogadoras do futebol feminino do país e a única do mundo a "
        "atuar em todas as edições da Olimpíada."]),

    _c("tarja-violeta", "Tarja Violeta",
       "opus-multipla", "campanhas", "14/07/2025",
       "Remédios sem comprimido dentro, com bula e desenho de uma criança "
       "atendida, para ampliar as doações ao tratamento oncológico infantil.",
       ["Conheça os remédios Tarja Violeta.",
        "A iniciativa, idealizada pela OpusMúltipla, tem o objetivo de ampliar "
        "as doações para o tratamento oncológico de crianças e adolescentes do "
        "Hospital Erastinho e da APACN.",
        "Os remédios não possuem nenhum comprimido dentro, mas contam com uma "
        "bula e um desenho especial de uma das crianças atendidas pelas "
        "instituições. Além disso, você pode ler um QR Code e conhecer a "
        "trajetória dessa criança."],
       [("Head of Creative Strategy", "Renato Cavalher"),
        ("Gestão Estratégica de Marcas",
         "Leonardo Hideki Tonooka, Laura Sferelli, Cecilia Godoy, "
         "Camila Rodrigues Guedes, Christine Brum")]),

    _c("videocase-cymco", "Videocase Cymco",
       "brain-box", "branding", "03/01/2024",
       "A Brainbox une branding, visual merchandising e embalagem para fazer a "
       "magia acontecer no PDV e construir marcas fortes em seus segmentos.",
       ["Quer saber onde está a Brainbox? Vá às compras.",
        "Nós unimos estratégias de branding, visual merchandising e embalagem "
        "para fazer a magia acontecer no PDV, alavancar resultados B2B e B2C e "
        "construir marcas fortes em seus respectivos segmentos."]),

    _c("videocase-frimesa", "Videocase Frimesa",
       "senso", "digital", "03/01/2024",
       "A Senso entrou em ação para ajudar a Frimesa a aumentar as vendas "
       "destinadas ao segmento de food service, restaurantes e cozinhas "
       "industriais.",
       ["A Senso entrou em ação para ajudar a Frimesa a aumentar as vendas "
        "destinadas ao segmento de food service, aumentando as vendas para "
        "restaurantes, lanchonetes e cozinhas industriais."]),
)

# Índice por slug, para a página do case não varrer a lista inteira.
POR_SLUG = {c["slug"]: c for c in CASES}

# ==========================================================================
# OS FILTROS (item 27)
#
# São LISTA FECHADA, e a validação mora no servidor: `rotas_sites.py` recusa
# com 404 qualquer valor que não esteja aqui. Um parâmetro de URL é entrada de
# fora como qualquer outra, e o mesmo raciocínio que peneira `{pagina}` e
# `{case}` contra travessia de diretório vale para ele.
#
# Só entram nos chips as chaves que TÊM case. As três categorias vazias e as
# duas empresas sem case publicado continuam na lista fechada acima (ela é do
# cliente), mas nenhum chip leva a uma grade vazia dentro de uma proposta.
# ==========================================================================
EMPRESAS_COM_CASE = tuple(
    dict(e, quantos=sum(1 for c in CASES if c["empresa"] == e["chave"]))
    for e in (GRUPO,) + EMPRESAS
    if any(c["empresa"] == e["chave"] for c in CASES))

CATEGORIAS_COM_CASE = tuple(
    (chave, nome, sum(1 for c in CASES if c["categoria"] == chave))
    for chave, nome in CATEGORIAS
    if any(c["categoria"] == chave for c in CASES))

CHAVES_DE_EMPRESA = frozenset(e["chave"] for e in EMPRESAS) | {GRUPO["chave"]}
CHAVES_DE_CATEGORIA = frozenset(chave for chave, _ in CATEGORIAS)


# ---------------------------------------------------------------------------
# AS TRÊS ETIQUETAS DE CADA CASE (Leandro, 27/08: "3 tags diferentes em cada
# case, bem pequenas, antes do botão").
#
# Elas NÃO são as categorias de filtro — aquelas vêm do HTML do cliente e
# cinco cases não têm nenhuma. Estas são rótulos DESCRITIVOS, e cada palavra
# sai do próprio texto publicado do case: o meio ("OOH", "Filme"), a natureza
# ("Pro bono", "Posicionamento") e o território ("Farma", "Telecom"). Nada
# aqui afirma serviço nem resultado que o texto não afirme — a regra é a
# mesma do resto da peça: o que não está no material do cliente não entra.
#
# Ficam num mapa próprio, e não em mais um argumento posicional em `_c`:
# dezoito chamadas com nove argumentos posicionais são ilegíveis, e o mapa
# deixa o conjunto conferível de uma olhada. O laço abaixo cobra completude:
# case sem etiqueta quebra na importação, não na tela.
ETIQUETAS = {
    "ilha-urbana-malbec-ultra-bleu": ("OOH", "Ativação", "Beleza"),
    "a-volta-ao-mundo": ("Conteúdo", "Design editorial", "Automotivo"),
    "contrastes-afece": ("Pro bono", "Institucional", "Inclusão"),
    "clash-no-catamara": ("Ativação", "Mídia inédita", "Beleza"),
    "frimesa-fogo-sabor": ("Integrada", "Lançamento", "Alimentos"),
    "gargantas-valda": ("Filme", "Humor", "Farma"),
    "geracao-de-fluxo-no-dia-dos-pais": ("Performance", "YouTube", "Varejo"),
    "junto-com-a-mamy": ("Posicionamento", "Campanha", "Consumo"),
    "m-possibilidades": ("IA", "Institucional", "Varejo"),
    "memes-unidos": ("IA", "Humor", "Telecom"),
    "natal-iluminado": ("Filme", "Natal", "Educação"),
    "o-futuro-e-agora-ou-agora": ("Gaming", "Geração Z", "Ambiental"),
    "play-no-enem": ("TV", "OOH", "Educação"),
    "sonhos-possiveis": ("Experiência", "Esporte", "Automotivo"),
    "tarja-violeta": ("Causa social", "Design", "Saúde"),
    "videocase-cymco": ("Branding", "Embalagem", "PDV"),
    "videocase-frimesa": ("B2B", "Food service", "Alimentos"),
}
for _caso in CASES:
    _caso["etiquetas"] = ETIQUETAS[_caso["slug"]]

# O CASE QUE ILUSTRA CADA SERVIÇO (Leandro, 27/08: "no hover, adicione uma
# imagem de um case relacionado àquele assunto. Precisa ser inteligente").
# A relação é defensável linha a linha, pelo texto do próprio case:
#   consultoria  -> Junto com a Mamy ("campanha do NOVO POSICIONAMENTO")
#   branding     -> Videocase Cymco ("a Brainbox une BRANDING...")
#   design       -> A Volta ao Mundo (o livro-objeto da Continental)
#   integrada    -> Frimesa Fogo & Sabor ("divulgada de maneira INTEGRADA")
#   performance  -> Geração de fluxo ("PERFORMANCE Max, -14% no custo")
#   midia        -> Clash no Catamarã ("o Catamarã VIROU MÍDIA")
#   relacionamento -> Sonhos Possíveis (a experiência dos atletas mirins)
CASO_DO_SERVICO = {
    "consultoria": "junto-com-a-mamy",
    "branding": "videocase-cymco",
    "design": "a-volta-ao-mundo",
    "integrada": "frimesa-fogo-sabor",
    "performance": "geracao-de-fluxo-no-dia-dos-pais",
    "midia": "clash-no-catamara",
    "relacionamento": "sonhos-possiveis",
}
assert set(CASO_DO_SERVICO.values()) <= set(ETIQUETAS)


def filtrar(empresa: str | None = None, categoria: str | None = None) -> list[dict]:
    """Os cases que sobram depois dos filtros. Sem filtro, os dezoito."""
    return [c for c in CASES
            if (empresa is None or c["empresa"] == empresa)
            and (categoria is None or c["categoria"] == categoria)]
