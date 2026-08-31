"""O CONTEÚDO do Grupo OM além dos cases: serviços, artigos e vídeos.

Colhido em 27/08/2026, e a regra é a mesma de `cases_grupo_om.py`: NADA aqui
foi escrito por nós. Os cinco serviços são as cinco LPs que o menu SERVIÇOS
do site atual abre (lp-branding-identidade-marca etc.), com o título e a
lista de soluções verbatim. Os oito artigos são o blog inteiro publicado, com
título, data, resumo (a meta description deles) e os três primeiros
parágrafos verbatim — a peça mostra a abertura e manda para o artigo
completo no site atual, como o cartão do Instituto já faz. Os cinco vídeos
são os do Canal de Vídeos de /publicacoes/ que ESTÃO NO AR: os outros quatro
embeds da página do cliente apontam para vídeos privados no YouTube e
aparecem quebrados lá — está em pendências, e é argumento de venda.

As capas dos vídeos foram baixadas para `videos/` pela mesma razão das artes
de case: nenhum pedido a servidor de terceiro sai da peça.
"""

SERVICOS = (
    {
        "chave": "branding",
        "titulo": "Branding e identidade de marca",
        "solucoes": ("Projetos completos de branding",
                     "Consultoria de propósito e posicionamento",
                     "Identidade visual e verbal",
                     "Design de embalagens",
                     "Projetos de lojas e jornada do consumidor",
                     "Visual merchandising e PDV",
                     "Stands para feiras e eventos"),
        "caso": "videocase-cymco",
    },
    {
        "chave": "integrada",
        "titulo": "Comunicação integrada e publicidade",
        "chamada": "Sua marca em todos os lugares que importam",
        "solucoes": ("Planejamento e consultoria em comunicação",
                     "Criação de campanhas integradas",
                     "Planejamento, gestão e checking de mídia",
                     "Campanhas regionais e nacionais"),
        "caso": "frimesa-fogo-sabor",
    },
    {
        "chave": "performance",
        "titulo": "Marketing digital e de performance",
        "chamada": "Resultados que vão além do clique",
        "solucoes": ("Planejamento, gestão e checking de mídia",
                     "Gestão de mesas de performance",
                     "SEO",
                     "Criação e gestão de conteúdo digital",
                     "Estratégias de inbound marketing",
                     "Data strategy & analytics",
                     "Suporte à digitalização de vendas"),
        "caso": "geracao-de-fluxo-no-dia-dos-pais",
    },
    {
        "chave": "midia",
        "titulo": "Inteligência e gestão de mídia",
        "chamada": "Decisões guiadas por dados e estratégia",
        "solucoes": ("Estudos e diagnósticos de mídia",
                     "Planejamento orientado por dados",
                     "Regionalização de campanhas",
                     "Consultoria em comunicação para agências e empresas"),
        "caso": "clash-no-catamara",
    },
    {
        "chave": "relacionamento",
        "titulo": "Relacionamento e customer experience",
        "chamada": "Conexões que fidelizam e engajam",
        "solucoes": ("Programas de relacionamento e incentivo",
                     "Endomarketing",
                     "Desenvolvimento de plataformas digitais",
                     "Experiências digitais interativas",
                     "Criação e gestão de mídias proprietárias"),
        "caso": "sonhos-possiveis",
    },
)
# A LP de branding não traz chamada além do título; as outras quatro trazem.

# Os cinco vídeos NO AR do Canal de Vídeos, com o título que o YouTube
# devolve. O Soundbrand é ÁUDIO de verdade — identidade sonora do grupo — e é
# ele que responde pela categoria de áudios da central.
VIDEOS = (
    {"id": "2XRPs2qf2l8", "titulo": "Videocase O Boticário :: comunicação regional", "tipo": "video"},
    {"id": "lq-9TTYjoSU", "titulo": "Brainbox :: Videocase Ítalo Supermercados", "tipo": "video"},
    {"id": "UhHKWtMMBIo", "titulo": "ESG :: Três letras que fazem toda a diferença", "tipo": "video"},
    {"id": "bQzbAYc20Io", "titulo": "Retail Trends :: Pós-NRF", "tipo": "video"},
    {"id": "osYxayeaTS4", "titulo": "Soundbrand Grupo OM", "tipo": "audio"},
)

ARTIGOS = [
{
 "slug": "agencia-de-marketing-para-industrias",
 "titulo": "Agência de marketing para indústrias: como escolher?",
 "iso": "2026-07-21",
 "resumo": "Saiba como escolher uma agência de marketing para indústrias capaz de integrar estratégia, branding, mídia, performance e geração de demanda.",
 "corpo": [
  "Processos industriais estão cada vez mais conectados, automatizados e orientados por dados. Segundo a Pesquisa de Inovação Semestral do IBGE, 89,1% das empresas industriais brasileiras com 100 ou mais pessoas ocupadas utilizaram ao menos uma tecnologia digital avançada em 2024. Entre elas, 42% já empregavam inteligência artificial em suas atividades.",
  "Apesar desse avanço, a comunicação de muitas indústrias ainda permanece concentrada em materiais institucionais, catálogos técnicos, feiras e ações pontuais de geração de leads. O resultado costuma ser um marketing fragmentado, com pouco reconhecimento de marca, dificuldade para demonstrar diferenciais e uma dependência excessiva da equipe comercial.",
  "Por isso, escolher uma agência de marketing para indústrias exige mais do que analisar campanhas criativas ou comparar propostas de mídia. A indústria precisa de um parceiro capaz de compreender seu modelo comercial, organizar a comunicação e transformar conhecimento técnico em argumentos relevantes para diferentes públicos."
 ]
} ,
{
 "slug": "coo-chief-operating-officer-o-que-faz",
 "titulo": "COO (Chief Operating Officer): o que faz?",
 "iso": "2026-05-28",
 "resumo": "Entenda o que faz um COO, como atua na operação da empresa e por que esse cargo é estratégico para marketing, vendas e crescimento.",
 "corpo": [
  "Toda empresa que cresce chega a um ponto em que a operação precisa acompanhar a ambição do negócio. No início, muitos processos funcionam porque as equipes são menores, as decisões estão concentradas em poucas pessoas e os ajustes acontecem de forma mais rápida. Com o tempo, esse modelo começa a mostrar limites.",
  "As áreas se multiplicam, os canais de venda aumentam, o marketing passa a lidar com mais campanhas, o comercial precisa de previsibilidade, a tecnologia entra com mais força e a marca começa a ser cobrada por uma entrega mais consistente. Nesse cenário, o crescimento passa a exigir coordenação.",
  "A sigla aparece com frequência em empresas em expansão, mas ainda gera dúvidas. Afinal, COO: o que faz ? Esse profissional cuida apenas de processos internos? Atua como braço direito do CEO? Participa de decisões estratégicas? Tem relação com marketing e vendas?"
 ]
} ,
{
 "slug": "founder-led-growth-flg",
 "titulo": "Founder-Led Growth: como transformar a autoridade do fundador em crescimento",
 "iso": "2026-07-12",
 "resumo": "Entenda como o Founder-Led Growth usa a autoridade do fundador para fortalecer a marca, gerar demanda e reduzir indicadores como CPL e CAC.",
 "corpo": [
  "Durante muito tempo, a comunicação empresarial concentrou sua atenção na marca institucional. Campanhas, anúncios, conteúdos e pronunciamentos eram desenvolvidos para representar a empresa, enquanto fundadores e CEOs permaneciam principalmente nos bastidores.",
  "As redes sociais mudaram essa dinâmica. Hoje, clientes, investidores, parceiros e profissionais conseguem acompanhar diretamente quem toma decisões, define prioridades e conduz os negócios. Nesse ambiente, a presença pública do fundador pode ampliar o alcance da empresa, fortalecer sua reputação e abrir conversas comerciais que dificilmente começariam por um anúncio tradicional."
 ]
} ,
{
 "slug": "ice-score-como-priorizar-acoes-de-marketing-e-growth",
 "titulo": "ICE Score: como priorizar ações de marketing e growth",
 "iso": "2026-05-19",
 "resumo": "Entenda o que é ICE Score, como calcular, quando usar e como adaptar essa matriz para priorizar ações de marketing.",
 "corpo": [
  "Toda equipe de marketing conhece bem esse cenário: há dezenas de ideias na mesa, várias campanhas possíveis, múltiplos canais para testar, melhorias pendentes no site, demandas de vendas, oportunidades em SEO , ajustes em mídia paga e, claro, aquela sensação de que tudo é urgente. O problema é que nem tudo pode ser feito ao mesmo tempo, e escolher no “feeling” pode custar tempo, dinheiro e foco estratégico.",
  "É nesse contexto que o ICE Score aparece como a metodologia que ajuda a organizar ideias, comparar oportunidades e definir prioridades com base em critérios simples: impacto, confiança e facilidade.",
  "Mais do que uma fórmula, o ICE Score funciona como uma lente para transformar hipóteses em decisões mais claras. Ele não elimina a intuição, mas evita que ela dirija sozinha sem GPS. Para gerentes de growth marketing e analistas de marketing, essa matriz pode apoiar desde a priorização de testes de conversão até a escolha de pautas de marketing de conteúdo , campanhas de mídia paga, melhorias de SEO e ações integradas com vendas."
 ]
} ,
{
 "slug": "marketing-no-pdv",
 "titulo": "Marketing no PDV: como aumentar as vendas?",
 "iso": "2026-08-03",
 "resumo": "Conheça métodos e estratégias do marketing no PDV para melhorar a experiência de compra, aumentar a conversão e impulsionar as vendas.",
 "corpo": [
  "O ponto de venda concentra uma etapa decisiva da jornada de compra. É nele que a intenção construída por campanhas, conteúdos e recomendações encontra fatores concretos como preço, disponibilidade, exposição, atendimento e facilidade para concluir o pedido.",
  "Por isso, o marketing no PDV reúne estratégias utilizadas para tornar produtos e marcas mais visíveis, relevantes e convincentes no momento da decisão. A atuação envolve a organização do espaço, os materiais de comunicação, as promoções, a experiência sensorial, o treinamento das equipes e a integração com canais digitais.",
  "Essa disciplina está diretamente ligada ao trade marketing , responsável por conectar indústria, distribuidores, varejistas e consumidores. Enquanto campanhas publicitárias ajudam a gerar interesse, o trabalho no PDV prepara o canal para transformar essa demanda em vendas."
 ]
} ,
{
 "slug": "nct-o-que-e",
 "titulo": "NCT: O que é?",
 "iso": "2026-05-26",
 "resumo": "Entenda o que é NCT, como funciona o framework de Narrativa, Compromissos e Tarefas e como aplicá-lo à gestão de marketing.",
 "corpo": [
  "Em ambientes de marketing cada vez mais pressionados por performance, eficiência e clareza estratégica, um dos maiores desafios está em transformar essas metas em uma direção compreensível, acionável e acompanhável por todo o time.",
  "A sigla NCT vem de Narratives, Commitments and Tasks , ou, em português, Narrativas, Compromissos e Tarefas . Trata-se de um framework de definição e acompanhamento de objetivos que conecta a estratégia ao trabalho do dia a dia, criando uma linha clara entre o motivo pelo qual uma empresa quer avançar, os compromissos que precisa assumir e as tarefas necessárias para chegar lá.",
  "Esse modelo pode ser especialmente útil porque ajuda a organizar prioridades em um cenário cheio de frentes simultâneas: marca, mídia, conteúdo, CRM , SEO , vendas, dados, eventos, campanhas e relacionamento com o cliente. Sem uma estrutura clara, o time corre o risco de confundir movimento com progresso."
 ]
} ,
{
 "slug": "social-selling",
 "titulo": "Social Selling: como vender mais nas redes sociais",
 "iso": "2026-07-20",
 "resumo": "Entenda o que é Social Selling, seus benefícios e como usar conteúdo, relacionamento e dados para gerar leads, reduzir o CPL e vender mais.",
 "corpo": [
  "As redes sociais deixaram de ocupar apenas o início da jornada de compra. Hoje, uma pessoa pode conhecer um produto no TikTok, pesquisar avaliações no YouTube, tirar dúvidas pelo Instagram, pedir uma recomendação pelo WhatsApp e concluir a compra sem passar por uma loja física.",
  "No mercado B2B , o percurso muda de formato, mas segue a mesma lógica. Um gestor pode acompanhar especialistas da empresa, consumir conteúdos técnicos, participar de um webinar e iniciar uma conversa comercial somente depois de reconhecer que aquela marca compreende o seu desafio.",
  "Essas jornadas mostram que a venda pode ser construída ao longo de diferentes interações. É justamente esse processo que orienta o Social Selling ."
 ]
} ,
{
 "slug": "value-proposition-canvas",
 "titulo": "Value Proposition Canvas: como alinhar cliente, proposta de valor e crescimento do negócio",
 "iso": "2026-05-12",
 "resumo": "Entenda como usar o Value Proposition Canvas para alinhar marketing e vendas, fortalecer sua proposta de valor e avançar rumo ao Product Market Fit.",
 "corpo": [
  "Toda empresa quer vender mais, conquistar clientes melhores e se diferenciar em um mercado cada vez mais competitivo. Porém, quando olhamos para a rotina de gerentes comerciais e gerentes de marketing, percebemos que boa parte dos desafios não começa exatamente na venda, na campanha ou na negociação.",
  "Muitas vezes, o problema está antes: na forma como a empresa compreende o cliente e transforma essa compreensão em uma proposta de valor clara."
 ]
} ,
]


POR_SLUG_ARTIGO = {a["slug"]: a for a in ARTIGOS}
