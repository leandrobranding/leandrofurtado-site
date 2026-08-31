"""Os selos do Grupo OM: quatro certificações e doze prêmios.

POR QUE SÃO DOIS GRUPOS, e por que eles não viram uma fileira só. Prêmio
ganho e certificação ativa não são a mesma afirmação: um diz "este trabalho
foi premiado em tal ano", o outro diz "esta empresa é reconhecida por esta
plataforma hoje". Empilhar os dezesseis numa fileira só apagaria a diferença
justamente na página que existe para provar as duas.

TODO SELO TEM ARQUIVO, e é essa a regra que faz "não invente prêmio" virar
algo que a máquina confere. O nome escrito é o nome daquele arquivo, e o
contrato mapeia um no outro em vez de derivar um do outro: o arquivo
`selo-new-york-festvals.webp` tem o nome escrito errado na origem, sem o "i"
de Festivals, e renomear ativo baixado é perder o rastro de onde ele veio.

A GPTW ENTROU EM 26/08. Ela ficou de fora do ciclo anterior porque a
certificação era real (o cliente lista "Great Place to Work" entre as práticas
de Governança do ESG) mas NÃO HAVIA ARQUIVO em lugar nenhum do site dele, e
desenhar um selo de certificação de terceiro é falsificar uma marca numa peça
que vai para o dono da empresa. O Leandro mandou o arquivo oficial, e com o
arquivo ela entra pela porta da frente, como certificação ativa e nunca como
prêmio.

AS MEDIDAS SÃO AS DO ARQUIVO. `width` e `height` errados num `<img>` são
reserva de espaço errada, que é salto de layout no celular enquanto os selos
carregam. A GPTW é a única VERTICAL (208x300); as outras são quadradas ou
deitadas, e é por isso que a fileira iguala por ALTURA e nunca por largura:
igualada por largura, ela apareceria com o dobro do peso visual das vizinhas.
"""
from __future__ import annotations

# (arquivo, nome exibido, largura, altura)
CERTIFICACOES = (
    ("selo-taan.webp", "TAAN", 300, 300),
    ("selo-premierpartner-rgb.webp", "Google Partner Premier", 291, 277),
    ("selo-meta-business-partner.webp", "Meta Business Partner", 300, 172),
    ("selo-gptw-certificada-2026.webp", "Great Place to Work, Certificada 2026", 208, 300),
)

PREMIOS = (
    ("selo-cannes-lions.webp", "Cannes Lions", 300, 300),
    ("selo-effie-awards.webp", "Effie Awards", 300, 300),
    ("selo-new-york-festvals.webp", "New York Festivals", 300, 300),
    ("selo-fiap.webp", "FIAP", 300, 300),
    ("selo-ampro-globe-awards.webp", "AMPRO Globe Awards", 300, 300),
    ("selo-festival-do-clube-de-criacao.webp", "Festival do Clube de Criação", 300, 300),
    ("selo-premio-abril-de-publicidade.webp", "Prêmio Abril de Publicidade", 300, 300),
    ("selo-premio-colunistas.webp", "Prêmio Colunistas", 300, 300),
    ("selo-globo-profissionais-do-ano.webp", "Globo Profissionais do Ano", 300, 300),
    ("selo-premio-voto-popular-about.webp", "Prêmio Voto Popular About", 300, 300),
    ("selo-abp.webp", "ABP", 300, 300),
    ("selo-archive.webp", "Archive", 300, 300),
)

TODOS = CERTIFICACOES + PREMIOS
