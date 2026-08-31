# Sites, a segunda fileira do Lab

**Data:** 25/08/2026
**Escopo:** seção de redesigns dentro do Lab, abaixo da vitrine de sistemas.
**Spec relacionada:** `2026-08-20-lab-demos-design.md`, que define fundação,
moldura e vitrine. Esta acrescenta uma fileira e não altera nada do que aquela
diz sobre os sistemas.

---

## 1. A decisão que governa tudo

A ideia original do Leandro era: achar sites ruins de clientes e marcas na
internet, refazer do jeito dele, e publicar para apresentar e vender.

A primeira versão desta spec separou isso em duas coisas, porque **eram dois
públicos diferentes tentando ocupar a mesma tela**:

- **O prospect**, que precisa ver o site DELE refeito, com o nome dele, e não
  precisa que mais ninguém veja.
- **O visitante do Lab**, que precisa entender em cinco segundos que o Leandro
  refaz sites, e não tem nada a ver com o negócio de terceiros.

Servir os dois na mesma galeria pública tem um custo que ninguém paga de bom
grado: você anuncia publicamente que o site do sujeito é ruim e, na mesma
semana, pede para ele te contratar. Começar uma relação comercial com uma
humilhação pública é ruim de venda e desnecessário. Curitiba é mercado pequeno,
e quem fez aquele site circula nele.

A saída não é abrandar a crítica, é **mudar onde ela acontece**:

| Superfície | Conteúdo | Quem vê |
| --- | --- | --- |
| Galeria pública | marcas grandes e conhecidas | qualquer visitante |
| Link de pitch | o site do prospect, com nome | só quem recebeu o endereço |
| Portfólio | o que virou trabalho aprovado | qualquer visitante |

Redesign não solicitado de marca nacional é exercício reconhecido no ofício e
não constrange ninguém: mostra ambição. Redesign de negócio local vive no link
privado, que é onde ele vende de verdade.

**E vende mais assim.** Um endereço só dele, com o nome dele na tela, aberto no
celular no meio do expediente, é impossível de ignorar. Na galeria pública ele
seria mais um entre trinta.

## 2. O que é um redesign

**Uma página: a home.** Não um site de várias páginas.

A venda se decide na home, e se decide na primeira dobra. Página interna não
soma nada nessa decisão e multiplica o trabalho por quatro. Uma home com
direção de arte de verdade vence um site raso de cinco páginas, e mantém a
unidade pequena o bastante para existirem várias: um pitch que custa duas
semanas vira três por ano, e o Lab morre.

Exceção prevista, e por caso, nunca por regra: quando o negócio exigir uma
segunda tela para fazer sentido (cardápio, catálogo, agendamento), ela entra.

**Ela abre e funciona.** É página de verdade servida pelo servidor, não imagem,
não vídeo de rolagem. É a tese do Lab inteiro: o Admita convence porque a
pessoa usa. Um redesign em imagem seria a única peça do Lab que só se olha, e
morreria ao lado de sistemas que funcionam.

**Ela não veste a marca do Leandro.** Não estende `lab/_base_demo.html`. A
moldura compartilhada existe para os sistemas parecerem parte do universo do
Leandro; um redesign precisa parecer o site do cliente. Carrega só o que ela
mesma pede.

## 3. Como um redesign nasce

**Código no repositório**, não registro num construtor do admin:

```
app/templates/lab/sites/<slug>/home.html
app/static/lab/sites/<slug>.css
```

Um construtor de blocos no painel foi considerado e recusado. A home da padaria
precisa parecer a padaria e a da clínica precisa parecer a clínica; um
construtor faz todas parecerem o construtor. "Direção de arte própria" e
"template configurável" são objetivos opostos, e aqui vale o primeiro.

O preço é que publicar exige deploy, o que é aceitável: `deploy/atualizar.sh`
leva minutos e já faz backup antes.

**GSAP é permitido aqui.** A regra "sem GSAP dentro do Lab" (spec do Notável,
§4) vale para os SISTEMAS de demonstração, onde biblioteca de animação seria
peso sem função. Estes são sites, e GSAP, ScrollTrigger, SplitText e Lenis já
vivem em `app/static/vendor/`. Aplicar a regra errada aqui empobreceria a peça
sem motivo.

## 4. O dossiê de insumos

Ao cadastrar o redesign com o endereço do site atual, o servidor colhe dele
tudo que der, na mesma passagem em que tira a captura:

```
título, descrição e OG           o que a marca diz de si
telefones, WhatsApp, e-mails     contato real, para as chamadas funcionarem
endereço e horários              os dois que mais somem em site ruim
redes sociais                    onde a marca já está
serviços e produtos              títulos e listas da página
textos                           os parágrafos, na ordem em que apareciam
logo e imagens                   o que dá para reaproveitar
```

Guardado como JSON no registro (`insumos`, `insumos_em`). O padrão de buscar
uma URL e extrair metadado já existe em `app/services/oembed.py`; isto é a
versão completa dele.

**Colheita mecânica no corte 1.** Determinística, testável e sem custo por uso.
A camada de IA (`app/lab/ia.py`) está construída e sem tela desde o Plano 1, e
um recurso `briefing_de_site` que resuma o negócio e sugira a hierarquia da
home é corte 2 natural. Ela não entra agora.

### 4.1 A regra que vem junto

**Nada na home é inventado.** Nenhum lorem ipsum, nenhum serviço que o negócio
não presta, nenhum preço, nenhum depoimento, nenhum número. Todo fato na tela
sai do dossiê ou de algo que o Leandro confirmou.

Isto não é preciosismo, é o que sustenta a peça. Um pitch com um serviço que a
padaria não oferece se destrói sozinho: o dono lê, conclui que ninguém olhou o
negócio dele, e tudo que veio antes vira enfeite.

Onde faltar informação, a home **não preenche com invenção**. Ou o bloco não
existe, ou fica registrado como pendência visível só no admin, para virar
pergunta ao cliente. Perguntar é melhor que chutar, e perguntar já é conversa
de venda.

O efeito na tela do pitch é o argumento inteiro: o dono reconhece o telefone
dele, o horário dele, o nome dos produtos dele. Não é conteúdo novo, é o mesmo
conteúdo finalmente respeitado.

## 5. O momento do pitch

O dono recebe o endereço no WhatsApp e toca. **Cai direto no site refeito, sem
capa e sem explicação.** Rola a home dele, inteira, como se já estivesse no ar.
No fim descobre de quem é.

A capa de contexto foi recusada porque a mensagem que acompanha o link já faz
esse trabalho: "refiz a home da sua empresa, dá uma olhada". O contexto vem da
conversa, e aí a tela pode ser só o trabalho.

**A cortina antes/depois não abre o pitch.** Começar por "olha como o seu está
ruim" é a mesma humilhação que a §1 tirou do caminho, agora em versão privada.
A cortina é excelente na galeria pública, onde não há ninguém para constranger.

## 6. Os três estados

| Estado | `/lab/sites/<slug>` | `/lab/p/<token>` | Galeria | Sitemap |
| --- | --- | --- | --- | --- |
| `pitch` | **404** | serve, `noindex` | não | não |
| `publico` | serve | serve | sim | sim |
| `aprovado` | serve | serve | não, vai ao portfólio | não |

O **404** do estado `pitch` é o que faz o recorte da §1 ser real e não uma
promessa. Enquanto o redesign é proposta para uma pessoa, só existe o endereço
secreto: adivinhar o slug não abre nada e o buscador não acha. Tornar público
é uma chave no admin, não um deploy.

`aprovado` fecha o ciclo: o cliente contratou e o trabalho virou real. Ele sai
da vitrine do Lab e entra no portfólio como `Case`, que é onde trabalho
aprovado mora e onde `site_url` e a macro `moldura_site` já sabem mostrar o
site no ar. Sai também do sitemap, porque quem passa a merecer indexação é o
case, não a proposta que o originou.

A página do redesign continua servindo, e não é redundância: ela é o registro
de que aquele trabalho começou como pitch não solicitado, e é a peça que o
Leandro mostra ao PRÓXIMO prospect para provar que o método funciona.

## 7. A vitrine ganha uma fileira

`/lab` passa a ter duas seções:

**Sistemas.** Admita, Notável, Caderneta. Sem alteração.

**Sites.** Os redesigns em estado `publico`.

Mesma gramática de cartão (marca, o que é, estado) e uma diferença que é o
argumento inteiro: no cartão de site a imagem é a **cortina antes/depois**.
Arrasta e o site atual da marca vira o do Leandro. É a coisa mais imediatamente
compreensível do Lab, e vive só aqui.

Sem redesign público, a fileira não existe. Sem "em breve", sem placeholder.

## 8. As regras da própria página

Cada home é livre em direção de arte. Quatro coisas não são negociáveis, porque
são as que separam site moderno de site que parece moderno.

**Marca de autoria, permanente.** A página está no domínio do Leandro, com a
marca de outra empresa, e pode vazar do link. Precisa dizer sem ambiguidade que
é uma proposta feita por ele, e não o site oficial daquele negócio: no rodapé,
discreta, e em `<meta name="author">`. Não enfraquece o pitch, fortalece: o dono
rola, se impressiona, e no fim descobre de quem é.

**As chamadas funcionam de verdade.** O botão de WhatsApp abre o WhatsApp do
cliente, o telefone disca, o endereço abre o mapa. É o que transforma "bonito"
em "pronto". O que NÃO existe é formulário que envia: formulário no servidor do
Leandro coletando o cliente final de outra empresa é problema de dado pessoal
que ninguém precisa ter. Contato é link direto, nunca captura.

**Responsiva de verdade, e o celular primeiro.** Não é a home de desktop
encolhida. O dono abre no celular, no meio do expediente, e é ali que a venda
acontece.

**Orçamento de peso.** Movimento é o argumento, e site que demora a aparecer
perde o argumento. Primeira dobra pintando rápido em conexão móvel, motion
entrando depois, e `prefers-reduced-motion` desligando o que se move. Um
redesign lento provaria o contrário do que existe para provar.

## 9. O modelo

Um modelo novo, e ele **não** entra em `app/lab/models.py`: todo modelo de lá
pendura em `sandbox_id` e morre em 24 horas, porque é dado de visitante. Isto é
conteúdo editorial permanente, irmão de `Case`, e vai para `app/models.py`.

```
Redesign
  slug              único; o endereço público
  marca, setor      "Padaria Aurora", "Panificação"
  estado            "pitch" | "publico" | "aprovado"
  token             único, opaco; o endereço do pitch

  antes_url                    o site atual, de verdade
  antes_shot, antes_shot_at    capturado por captura.py
  depois_shot, depois_shot_at  capturado da própria página do Leandro

  insumos, insumos_em          o dossiê da §4, em JSON
  diagnostico                  o que estava errado, em texto
  pendencias                   o que falta perguntar ao cliente

  criado_em, enviado_em, visto_em
```

**As duas capturas saem do mesmo serviço.** `captura.py` fotografa qualquer
endereço com Chromium headless. O "antes" vem do site do cliente e o "depois"
vem de `/lab/sites/<slug>`. A cortina nunca desatualiza porque é recapturada,
igual ao que já acontece com `Case.site_shot`.

**`visto_em`** é carimbado na primeira abertura do link privado. É a informação
mais útil que um pitch pode dar, e custa uma linha.

### 9.1 A armadilha do carimbo

Um redesign em estado `pitch` responde 404 no endereço público, então a captura
do "depois" precisa passar pelo endereço do token. **E a captura não pode
carimbar `visto_em`**, senão o próprio Leandro marca o cliente como tendo visto
antes de o link ser enviado, e o sinal que justifica o campo vira ruído.

A regra: `visto_em` só é carimbado quando a requisição **não** vem do
endereço de loopback. O Chromium da captura roda na mesma máquina e bate em
`127.0.0.1`; visitante de verdade nunca chega assim, porque o nginx repassa o
IP real e `app/services/geo.py::ip_do_pedido` já resolve isso.

## 10. As rotas

```
GET  /lab                  a vitrine, agora com a segunda fileira
GET  /lab/sites/<slug>     o redesign público (404 quando estado == "pitch")
GET  /lab/p/<token>        o pitch privado, noindex, carimba visto_em
```

`/lab/p/` é curto de propósito: esse endereço vai ser colado no WhatsApp e às
vezes lido em voz alta.

No admin, `/admin/lab` (que já existe) ganha a lista de redesigns: criar o
registro, colar o endereço atual, disparar colheita e capturas, virar o estado,
copiar o link do pitch e ver quando foi aberto.

## 11. O que já existe e não será refeito

| Peça | Onde | Estado |
| --- | --- | --- |
| Captura de tela | `app/services/captura.py` | pronta, Chromium headless, 1440x900 |
| Busca de URL e OG | `app/services/oembed.py` | padrão a estender |
| Moldura de navegador | `_bits.html::moldura_site` | pronta |
| Case com site no ar | `Case.site_url`, `site_shot` | pronto |
| Vitrine do Lab | `app/templates/lab/vitrine.html` | pronta, ganha uma fileira |
| Admin do Lab | `/admin/lab`, `admin/lab.html` | pronto, ganha uma lista |
| IP real atrás do nginx | `app/services/geo.py::ip_do_pedido` | pronto |

## 12. Fora de escopo, explicitamente

- Construtor de página no admin, em qualquer forma.
- Formulário que envia dado, em qualquer página de redesign.
- Hospedar o site do cliente depois de aprovado. Aprovado vira `Case`, e a
  hospedagem é conversa comercial, não função do Lab.
- Comparar automaticamente desempenho do antes contra o depois. É atraente e é
  outra spec.
- Qualquer coisa que dependa de serviço pago.

## 13. Os dois cortes

**Corte 1.** Modelo, três estados, as três rotas, colheita mecânica de insumos,
as duas capturas, a fileira na vitrine com a cortina, a lista no admin, e **um**
redesign de verdade construído do começo ao fim, para provar o caminho inteiro.

**Corte 2.** O recurso `briefing_de_site` na camada de IA que já existe, e o
que a operação pedir depois de alguns pitches reais terem acontecido.

O corte 1 entrega sozinho a promessa: dá para prospectar com ele no dia
seguinte.

## 14. Como se sabe que ficou pronto

- Um redesign em `pitch` responde 404 no endereço público e abre pelo token.
- O token carrega `noindex`, está fora do sitemap e fora da vitrine.
- `visto_em` é carimbado na primeira abertura por visitante, e **não** pela
  captura.
- A colheita traz contato, endereço e horário de um site real de teste.
- A cortina antes/depois funciona na vitrine, com as duas capturas.
- Toda página de redesign carrega a marca de autoria e nenhum `<form>` que
  envia.
- A home construída abre rápido no celular e respeita `prefers-reduced-motion`.
- Nada em `app/lab/` importa do Nodal.
