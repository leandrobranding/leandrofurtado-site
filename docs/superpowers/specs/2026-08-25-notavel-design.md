# Notável, o painel financeiro do Lab

**Data:** 25/08/2026
**Escopo:** segunda demo do Lab de Demos, depois do Admita.
**Spec anterior:** `2026-08-20-lab-demos-design.md` §6.2. Este documento a
SUBSTITUI para o Notável e mantém tudo o que ela diz sobre fundação, sandbox,
guardião de IA e moldura.

---

## 1. A decisão que governa tudo

**O Notável existe para impressionar em trinta segundos.** Decisão do Leandro
em 25/08, quando a alternativa oferecida era "alguém usar por dez minutos".

Isso não afrouxa o rigor, muda onde ele é aplicado. As consequências, e todas
elas são vinculantes:

- A **tela heroína é o painel**, não um formulário. O visitante chega e o
  sistema já está mostrando um negócio funcionando.
- **Profundidade concentrada.** Cinco fluxos funcionam de verdade. O resto é
  cenário assumido, legível e honesto. Sete módulos rasos provariam o oposto
  do que o Lab existe para provar.
- **Movimento com causa.** Painel que se mexe sozinho é protetor de tela. O
  que se move, se move porque o visitante fez algo, ou porque a página acabou
  de chegar.

## 2. A empresa da demo

Uma **casa de desenvolvimento de software** de porte pequeno, fictícia, com
nome, CNPJ inválido por design (§9.9 da spec do Lab), CNAE e regime tributário
visíveis no cabeçalho do painel.

**Serviço e não comércio, de propósito:** é em serviço que existem o Anexo III,
o Anexo V e o **Fator R** do Simples Nacional. Sem isso o CNAE seria enfeite na
tela; com isso, trocar a atividade muda o anexo, muda a alíquota e muda o
imposto na frente do visitante.

**Software e não clínica ou arquitetura**, por um motivo de reconhecimento:
empresa de tecnologia é o caso clássico do Fator R, em que a razão entre folha
e faturamento decide entre o Anexo III e o Anexo V. Todo contador brasileiro
conhece esse dilema, e reconhecê-lo na tela é o que faz o visitante da área
concluir que quem construiu entende do ofício.

Os dados da empresa são semente (`origem="seed"`) e vivem no sandbox como
qualquer outro registro da demo.

## 3. A tela heroína

Uma tela só, sem rolagem obrigatória no desktop, com seis regiões:

| Região | Conteúdo | Reage a |
| --- | --- | --- |
| Cabeçalho | empresa, CNPJ, CNAE, regime | troca de CNAE (corte 2) |
| Faixa de saldos | conta corrente, aplicação, a receber, a pagar | despacho aprovado, nota emitida |
| KPI grande | A RECEBER, número tabular | nota emitida ou cancelada |
| Câmbio do dia | USD, EUR, GBP, com a data da cotação | nada; atualiza uma vez por dia |
| Despachos | fila de pagamentos aguardando aprovação | aprovar ou recusar |
| Lançamentos | últimos movimentos, com categoria | nota emitida, extrato categorizado |

**Não há gráfico de entradas contra saídas.** Ele foi cortado no desenho: é
bonito na chegada e mudo depois, e ocupava a área nobre sem dizer nada que os
números ao lado já não digam. O espaço vai para a fila de despachos, que é
onde o visitante age. Movimento em gráfico é enfeite; movimento numa fila que
responde a clique é prova.

O que fica de gráfico é uma linha mínima **dentro do KPI**, com o saldo dos
últimos trinta dias, desenhada na chegada.

**Números tabulares em toda parte** (`font-variant-numeric: tabular-nums`), com
a IBM Plex Mono da identidade do Notável nos valores, no número da nota e no
CNPJ. Isso já está definido em `app/static/lab/notavel.css`.

## 4. Motion

Vocabulário: o mesmo do Admita. Keyframes em CSS, easing
`cubic-bezier(.2,.75,.3,1)`, entrada e saída de cartão, linha que cresce, halo
e pulso contidos, toast para confirmar. **Sem GSAP dentro do Lab**: ele existe
no site, não aqui.

Três camadas, e só três:

**Chegada orquestrada.** Ao abrir: os KPIs contam do zero ao valor, a linha do
saldo se desenha, as listas entram escalonadas com atraso crescente. Dura cerca
de dois segundos e termina. Depois a tela fica quieta.

**O painel nasce pronto, e a animação conta até ele.** Os valores finais vêm
renderizados pelo servidor, no HTML. A chegada anima do zero ATÉ eles. O
contrário, que é o comum, deixa a tela piscar vazia enquanto o JavaScript
busca dados, e em trinta segundos de julgamento essa piscada é metade da
primeira impressão. Sem JavaScript, o painel aparece completo e correto, só
sem a contagem.

**Reação com causa.** Toda ação do visitante move o que depende dela, e só
isso: emitir nota faz o "a receber" subir com transição incremental e insere a
linha com a entrada de cartão; aprovar despacho baixa o saldo e remove a linha
com a saída de cartão.

**Um pulso só, e amarrado.** Passados alguns segundos da chegada, **um** evento
simulado: um pagamento compensa. E ele **quita um recebível que está visível na
tela**: o número desce, a linha muda de estado, e o visitante vê o ciclo se
fechar. Um, não uma sequência.

Evento solto é enfeite. Evento que fecha algo que a pessoa estava olhando é
sistema.

`prefers-reduced-motion: reduce` desliga a chegada e o pulso, e mantém as
transições de estado curtas. Regra da casa, não exceção desta demo.

## 4.1 Linguagem visual: instrumento, não quadro

Pedido do Leandro em 25/08: o Notável tem que parecer **outro sistema**, não o
Admita pintado de outra cor. A paleta já ajuda (coral quente sobre `#FAFAFA`
contra petróleo frio sobre `#F7F9FB`), mas cor não é linguagem.

A diferença é de gramática:

| | Admita | Notável |
| --- | --- | --- |
| Metáfora | quadro de trabalho | painel de instrumentos |
| Unidade | cartão que se move | número que muda |
| Densidade | arejada, uma coluna por etapa | densa, tudo à vista de uma vez |
| Tipografia | serifa humanista, avatares | serifa documental, monoespaçada nos valores |
| Alinhamento | cartões independentes | grade que atravessa os blocos |
| Temperatura | quente | fria, com barra de comando escura |

**A barra de comando escura** usa `--marca-faixa-fundo: #101828`, que já existe
na prancha aprovada. É o que muda o reconhecimento no primeiro olhar sem
inventar cor nova: o Admita é claro de ponta a ponta, o Notável tem uma faixa
grave no topo, como terminal financeiro.

### O que "moderno" significa aqui

Moderno não é efeito, é usar as capacidades atuais da plataforma **onde elas
resolvem o problema melhor que a alternativa**. Cinco, todas com motivo:

**`subgrid`.** Os números alinham ATRAVÉS dos blocos independentes, não só
dentro de cada um. Precisão visual é a identidade de software financeiro, e
sem subgrid isso exigiria medidas fixas que quebram em outro idioma ou zoom.

**`@container`.** Cada região se dimensiona pela própria largura, não pela
janela. É o que faz a mesma região servir ao painel no desktop e ao modo
aplicativo no celular sem CSS duplicado.

**`:has()`.** Estado sem classe de JavaScript: a fila que contém um item
bloqueado se estiliza sozinha, o KPI negativo se veste sozinho. Menos
JavaScript é menos lugar para dessincronizar.

**View Transitions.** A saída do despacho da fila e a entrada da nota na lista
com transição nativa, curta e física, em vez de dois keyframes coordenados na
mão.

**`@starting-style` com `transition-behavior: allow-discrete`.** Entrada de
elemento que acabou de existir, sem truque de JavaScript.

### O piso, que não é negociável

**Tudo isso é melhoria progressiva.** O painel funciona inteiro, com todos os
cinco fluxos, num navegador que não tenha nenhuma das cinco. Cada uma entra
atrás de `@supports` ou de teste de capacidade, e a alternativa é o vocabulário
de keyframes que o Admita já usa e que já está provado.

O motivo é o de sempre nesta casa: a demo existe para convencer, e demo que
quebra num navegador desatualizado convence do contrário. Recurso novo entra
para melhorar o topo, nunca para sustentar o piso.

## 5. Os cinco fluxos que funcionam

### 5.1 Emitir nota em três passos

Cliente → itens → impostos calculados e **explicados na tela** (base, alíquota,
valor, com rótulo humano de cada imposto). Numeração sequencial por sandbox.
Emitir gera o PDF na hora, com tarja "DEMONSTRAÇÃO — SEM VALOR FISCAL".

`gerar_nf_pdf()` em `app/lab/pdf.py` já existe e já faz isso. Falta a tela.

Cancelar uma nota emitida reflete no painel: o "a receber" desce, a linha muda
de estado.

### 5.2 Despachos de pagamento

Fila de pagamentos aguardando aprovação, cada um com fornecedor, valor,
vencimento e categoria. Aprovar baixa o saldo e some da fila; recusar devolve
para pendente com motivo. Ambos registram na trilha de auditoria, que o Admita
já tem e que é reaproveitada.

### 5.3 O lugar onde o sistema recusa

**Aprovar um despacho acima do saldo disponível é recusado**, com o motivo na
tela e quanto falta.

Isto não é validação de formulário, é a peça central da demonstração. O Admita
convence num detalhe: você tenta avançar sem documento conferido e ele não
deixa. É o que separa sistema de maquete, e o visitante técnico sente em três
segundos.

O visitante clica achando que vai passar. A recusa vem com o número: saldo
disponível, valor do despacho, diferença. Sem ela o painel é bonito e mudo.

A regra é do domínio, não da tela: vive no serviço, é testada sozinha, e a
interface só a exibe.

### 5.4 Calculadora do Simples com CNAE *(corte 2)*

O visitante troca a atividade e vê o anexo mudar, a alíquota efetiva
recalcular e o Fator R decidir entre Anexo III e Anexo V. Com a memória de
cálculo aberta ao lado: base, parcela a deduzir, resultado.

### 5.5 Categorização de extrato por IA *(corte 2)*

Texto colado ou exemplo pronto → lançamentos classificados em categorias de
**lista fechada** com justificativa curta. O guardião
(`app/lab/ia.py::chamar_ia`, recurso `categorizar_extrato`) e os fallbacks já
existem. Falta a tela.

## 6. O que é cenário, e assumidamente

**Folha de pagamento:** uma aba com um fechamento pronto e aberto, mostrando
proventos, descontos e encargos de um mês. Leitura, não digitação. Ela existe
para o visitante reconhecer o vocabulário do ofício, não para calcular folha.

**Rescisão:** um caso montado, exibido como leitura, no mesmo espírito.

Cenário não é desculpa para número errado: os valores exibidos batem entre si
e com as regras que a tela declara.

## 7. Honestidade dos números fiscais

**Toda tabela de alíquota, teto e faixa vive num arquivo único e datado**, e a
tela mostra de quando ela é.

O motivo é prático, não jurídico: alíquota do Simples, teto do INSS e tabela
do IRRF mudam por lei todo ano. Uma demo que mostra número desatualizado para
um gestor financeiro perde a credibilidade que o Lab inteiro existe para
construir. Com a data na tela, o número velho vira "tabela de 2026" em vez de
"erro".

Onde o valor for ilustrativo e não calculado, a tela diz isso.

## 8. Câmbio

Fonte: **API PTAX do Banco Central**, aberta, sem chave e sem cadastro
(`olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/`). Testada em
25/08/2026: responde USD, EUR, GBP e mais sete moedas.

Duas regras, as duas achadas testando:

**Uma chamada por dia, guardada.** Chamar a API a cada visita é lento e rude
com um serviço público. A cotação do dia é gravada e servida do banco.

**Queda para o último dia útil.** Em sábado, domingo e feriado a API responde
com lista vazia, porque não há PTAX nesses dias. Sem essa queda, o painel abriria em
branco justamente no fim de semana, que é quando alguém navega portfólio.

Falha de rede ou API fora: usa a última cotação guardada, com a data dela na
tela. O painel nunca fica sem câmbio.

## 9. Responsividade

**Foco no desktop**, onde o painel inteiro cabe numa tela e o motion tem
espaço para acontecer.

**No celular, cara de aplicativo:** a mesma decisão já tomada no Admita
(`modoApp()` em `admita.js`). Navegação inferior, uma região por vez, e os
dois fluxos que valem no celular: emitir nota e aprovar despacho. O resto é
visita guiada.

## 10. O que já existe e não será refeito

| Peça | Onde | Estado |
| --- | --- | --- |
| Modelos | `LabClienteFiscal`, `LabNota`, `LabLancamento` | prontos |
| PDF da nota | `app/lab/pdf.py::gerar_nf_pdf` | pronto |
| Guardião de IA | `app/lab/ia.py`, recurso `categorizar_extrato` | pronto |
| Categorias fechadas e fallbacks | `app/lab/ia_fallbacks.py` | prontos |
| Identidade | `app/static/lab/notavel.css`, ícones, marca, símbolo | pronta |
| Moldura | `app/templates/lab/_base_demo.html` | pronta |
| Sandbox, tetos, auditoria | `app/lab/sandbox.py`, `protecao.py` | prontos |

**O que falta é a camada de aplicação:** rotas, telas, o JavaScript do painel,
o serviço de câmbio, as tabelas fiscais datadas e a semente da empresa.

## 11. Mudanças no projeto desde a spec de 20/08

Registradas aqui para o plano não tropeçar nelas:

- `formatar_reais` e `ErroDeValidacao` saíram do Nodal para
  `app/services/formato.py`.
- Os limites do Lab viraram configuração (`settings.lab_max_ia_por_sandbox`,
  `lab_max_pdfs`, `lab_rate_por_min`), não constantes de módulo.
- O contador por IP é compartilhado entre os workers
  (`app/services/limite.py`), e não mais um dicionário em memória.
- O Nodal virou módulo opcional; nada no Lab pode importar dele.

## 12. Os dois cortes

**Corte 1, os trinta segundos.** Painel completo com as seis regiões, motion
nas três camadas, emissão de nota com PDF, despachos, câmbio, saldos, semente
da empresa e o modo aplicativo no celular.

**Corte 2, os dez minutos.** Calculadora do Simples com CNAE e Fator R,
categorização de extrato por IA, aba de folha e o caso de rescisão.

O corte 1 entrega sozinho a promessa da vitrine. O corte 2 é o que faz alguém
ficar.

## 13. Fora de escopo, explicitamente

- Emissão fiscal real, integração com prefeitura ou SEFAZ.
- Upload de arquivo de qualquer tipo, em qualquer tela.
- Conciliação bancária, estoque, pedidos, boletos.
- Cálculo de folha de verdade, com digitação.
- Persistência além das 24 horas do sandbox.

## 14. Como se sabe que ficou pronto

- O painel abre em menos de um segundo e a chegada termina em cerca de dois.
- Emitir uma nota move o KPI, a lista e o PDF sai correto, com numeração
  sequencial por sandbox.
- Aprovar um despacho move o saldo e registra na auditoria.
- O câmbio aparece com data, inclusive no sábado.
- `prefers-reduced-motion` desliga chegada e pulso.
- A suíte cobre: ciclo da nota, numeração, despachos, queda do câmbio,
  isolamento entre sandboxes e os tetos.
- Nada no Lab importa do Nodal.
