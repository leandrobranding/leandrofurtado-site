# O sistema de nós do Magnific, e a página de exercícios da aula de Nodes

**Data:** 2026-08-17 · **Para:** o curso "Fluxos com nós" (curadoria aprovada),
aula de Nodes. **Fonte:** a documentação pública de Spaces
(`magnific.com/ai/docs/nodes-and-connections`, lida por inteiro) e o Space
"CONCEITO NODAL" que o Leandro abriu ao vivo para inspeção.

## 1. Como o Magnific Spaces funciona — o modelo mental para ensinar

**Um nó faz um trabalho só.** Uns trazem conteúdo para dentro (Upload, Media,
Text), outros geram (Image/Video Generator, Voiceover, Music), outros
transformam (Upscaler, Camera Angles) ou combinam (Video Audio Mix). Nós
utilitários (List, Sticky Note, Group) organizam em vez de gerar.

**Portas.** Todo nó tem círculos nas bordas: saída à direita, entrada à
esquerda. Ligar uma saída a uma entrada cria a conexão, e é por ela que o dado
anda. Regras que valem ouro didático:

- entrada aceita **uma** conexão por padrão (a nova substitui a velha);
- saída é **ilimitada** — um prompt pode alimentar dez geradores;
- algumas entradas são obrigatórias: sem elas o nó não roda;
- **nunca** do avesso (entrada→saída), **nunca** ciclo.

**Tipos têm cor.** Imagem = roxo, Texto = azul, Vídeo = verde, Áudio =
laranja. Porta só aceita porta do mesmo tipo — a linha **não gruda** em tipo
errado. O erro é impedido antes de existir, e o aluno rastreia o fluxo pela
cor.

**Execução.** Run Node (só este), Run Workflow (a cadeia toda), Run
Downstream (daqui para frente — economiza créditos ao iterar no meio). A
ordem é automática: fontes primeiro, geradores quando os insumos chegam,
ramos independentes em paralelo. Estados visíveis por nó (idle, pending,
running, completed, failed, paused, cancelled). Todo run fica no histórico do
nó, com as configurações que o produziram. List = lote (10 prompts → 10
imagens, linha tracejada). Créditos: o custo aparece **no botão Run antes de
rodar**, e muda ao vivo com modelo/resolução/duração.

**Catálogo visto ao vivo no Space:** Basics (Text, Image Generator, Video
Generator, Assistant, Image Upscaler, List) · Media (Add Creation, Upload,
Assets, Stock) · Library (Add Reference, Characters, Styles, Elements,
Locations, Color palettes, Templates) · Video (Extend video, Speak, Video
Combiner, Video Upscaler, Media Extractor) · Audio (Voiceover, Sound Effects,
Music Generator). Interface: barra de ação flutuante sobre o nó selecionado,
prompt dentro do próprio nó, contagem ×N, modelo "Auto", proporção 1:1,
conexão como curva suave entre círculos com o ícone do tipo.

## 2. Como a página deles ensina (a pedagogia a imitar)

1. Primeiro o **vocabulário** (tipos de nó, um parágrafo cada, com convite a
   template guiado);
2. depois a **mecânica** (portas → tipos/cores → jeitos de conectar);
3. depois a **tabela de compatibilidade** ("o que liga no quê") como
   referência rápida;
4. depois **execução e economia** (rodar, estados, histórico, créditos);
5. fecha com **dicas** que são regras de ofício ("puxe da porta para o vazio e
   o Spotlight já vem filtrado", "siga as cores", "ramifique para comparar").

A prática mora em templates que abrem um canvas real. É isso que a nossa
página de exercícios substitui — sem depender do produto deles.

## 3. A página de exercícios do Nodal — o desenho

**O que é:** um playground de nós **didático e client-side**, como novo tipo
de bloco do compositor (`fluxo`), usado dentro da aula de Nodes. Não gera
nada: ensina a *pensar* em fluxo. É "praticamente igual" na mecânica —
arrastar conexão de porta a porta, cor por tipo, recusa de tipo errado — sem
clonar o produto (sem créditos, sem Spotlight, sem geração).

**Como cabe nas regras do projeto:**

- **Custo zero e 1 vCPU:** tudo roda no navegador do aluno — SVG + JS puro,
  sem biblioteca, sem servidor no laço. O peso no VPS é servir um JSON.
- **Sem JavaScript:** a página mostra o diagrama estático da resposta com a
  explicação passo a passo — o conteúdo didático não some, some só o
  interativo (acréscimo, não requisito — a regra de sempre).
- **Identidade:** a linguagem do Nodal já É nó e aresta (círculo vazado +
  linha de 1px). Aqui ela deixa de ser só identidade e vira **função** — o
  playground desenha com a mesma gramática visual do site. (A proibição do
  corte 3 é nó como *decoração* de painel/botão; isto é conteúdo.)
- **O exercício é dado, não código:** um JSON declara os nós disponíveis,
  as portas com tipo, e o gabarito (que conexões contam como certas). Criar
  exercício novo = escrever JSON no painel, não programar.

**Nós do playground (fictícios, de agência — não os do Magnific):**
Briefing (saída: texto) · Referência (saída: imagem) · Gerador de Imagem
(entradas: texto obrigatório, imagem opcional; saída: imagem) · Gerador de
Vídeo (texto, imagem opcional; saída: vídeo) · Ampliador (imagem→imagem) ·
Locução (texto→áudio) · Mixagem (vídeo+áudio→vídeo). Mesmas cores de tipo do
Magnific para o aluno transferir o aprendizado direto.

**Três degraus de exercício, na aula:**

1. **Ligar certo** — dois nós, uma conexão possível; feedback imediato quando
   gruda (e a linha recusando quando o tipo não casa — o aluno *sente* a
   regra).
2. **Consertar o fluxo** — um workflow montado com um erro (texto ligado em
   porta de imagem, entrada obrigatória vazia); o aluno acha e conserta.
3. **Montar do briefing** — um pedido de cliente em texto ("banner e versão
   em vídeo com a mesma direção") e a paleta de nós soltos; vale qualquer
   solução que satisfaça o gabarito (um Briefing alimentando dois geradores —
   a lição da saída ilimitada).

Acertou os três: a página diz em quantas tentativas, e o botão "marcar
concluída" continua **manual**, como a spec do corte 4 manda — o exercício
não conclui a aula sozinho.

**Custo estimado:** uma tarefa de plano própria (o playground + o bloco
`fluxo` no compositor + os três exercícios da aula), quando formos construir
as aulas depois do beta. O risco técnico é baixo: arrastar linha em SVG com
`pointerdown/move/up` é bem menor que o drag & drop já entregue no painel.

## 4. O que NÃO copiar do Magnific

Créditos e custo (não há geração), Spotlight (a paleta do exercício é fixa e
pequena de propósito), multi-página/colaboração, e a estética deles — a
mecânica é igual, a pele é a do Nodal. O Space "CONCEITO NODAL" do Leandro
fica como fonte de capturas para os blocos de texto da aula (mostrando o
sistema real que o aluno vai operar depois).
