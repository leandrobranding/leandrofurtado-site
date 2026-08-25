# Lab de Demos — Plano 2: Identidades, Vitrine e as Três Demos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir tudo que o visitante vê: a vitrine /lab e as três demos completas (Admita, Notável, Caderneta) vestindo as identidades aprovadas, sobre a fundação selada do Plano 1.

**Architecture:** Rotas públicas em `app/lab/rotas.py` consumindo os contratos prontos da fundação (sandbox, guardião de IA, PDFs, seeds, proteção). SSR + troca de fragmentos por fetch (padrão Nodal) para interações; um CSS por demo com tokens de marca; fontes servidas localmente; ícones vendorizados como sprites SVG por demo.

**Tech Stack:** FastAPI + Jinja2 + CSS/JS vanilla; fontes Google baixadas e servidas do próprio site (custo zero, sem host externo); Phosphor/Lucide (MIT/ISC) vendorizados.

**Spec:** `docs/superpowers/specs/2026-08-20-lab-demos-design.md`
**Leituras obrigatórias por tarefa (fontes de verdade além da spec):**
- Identidades aprovadas (nomes, paletas, fontes, ícones, taglines, amostras): scratchpad publicado como Artifact v4 + resumo em `.superpowers/sdd/2026-08-20-lab-demos/referencias-do-leandro.md`
- Kit de padrões de UI: `.superpowers/sdd/2026-08-20-lab-demos/referencias-ui-behance-estudo.md`
- Tipografia e regras anti-IA de espaçamento: `.superpowers/sdd/2026-08-20-lab-demos/pesquisa-tipografia-v3.md`
- Vitrine (ritmo Einar): `.superpowers/sdd/2026-08-20-lab-demos/referencia-vitrine-einar.md`
- Setoriais (vocabulário e lições): `referencias-rh-estudo.md`, `referencias-fin-estudo.md`, `referencias-escola-estudo.md`
- Microinterações/performance: `pesquisa-uiux.md` §5
- Herança da fundação (F1-F8 + obrigações + contratos): `.superpowers/sdd/2026-08-20-lab-demos-fundacao/progress.md` (bloco final) e os `task-*-report.md`

## Global Constraints

- Identidades FIXAS (aprovadas pelo Leandro): Admita = Alegreya+Karla, coral #CF4227/#EF6351 + índigo #4338CA, Phosphor Duotone; Notável = Source Serif 4 + IBM Plex Sans (+Mono só em nº/CNPJ), petróleo #1F6F6B + âmbar #E0A526, Lucide; Caderneta = Lora + Nunito Sans, esmeralda #0B7A55 + amarelo #F5A623, Phosphor Bold. Fundos e AA conforme pranchas.
- Taglines: "Contratou? A gente cuida do resto." · "A nota sai, o dinheiro entra, você vê tudo." · "Você lança a nota. O boletim se resolve."
- COPY: cada demo fala com seu público profissional (RH: recrutadores/folha/gestores; Financeiro: gestores financeiros/contadores/CEOs; Escola: diretores/professores/secretaria/reitores). Linguagem acessível, humana e prática. PROIBIDO travessão/hífen como pontuação. Vocabulário do ofício vem dos estudos setoriais.
- UI: cantos arredondados em tudo, pegada Apple, ÍCONES EM TUDO (sempre em container circular/pill, nunca soltos), célula-padrão avatar/ícone+nome+valor, KPI numeral bold + rótulo pequeno, cartão de IA "decidiu e explica o porquê", cor fixa por categoria. PROIBIDO: rótulo uppercase com tracking largo (eyebrow de IA), dark neon, tab bar mobile, mascote.
- Espaçamento anti-IA: display com entrelinha 1.05-1.15, corpo 1.55-1.65; contraste de tamanho editorial; nada de leading único.
- LEI DA TELA CHEIA (§13b da spec, decisão dele 20/08): dentro das demos a página NUNCA rola; shell 100dvh com moldura fixa e miolo encaixado; excedente rola DENTRO do próprio box com scrollbar invisível/discreta; responsivo por composição em qualquer tamanho. Teste vinculante por tela em 390/768/1280/1920: scrollHeight <= viewport e zero overflow horizontal.
- Performance (§14 da spec): interação <200ms percebidos, fragmento-swap (padrão Nodal), feedback otimista, skeleton com formato do conteúdo só entre 400ms-3s, IA com estado de carregando bonito, Lighthouse mobile ≥90 por demo.
- Segurança herdada INEGOCIÁVEL: zero upload; |safe proibido sobre visitante; limitar_taxa em TODAS as rotas /lab (F1: poda inline no próprio limitar_taxa a cada N chamadas, removendo a linha ilusória do cron; F2: chave por IP+token validado); contexto["instancia_id"] em TODA chamada de IA; motivo_fallback NUNCA cru para visitante; não acumular pendentes na Session antes de chamar_ia (commit interno); pdfs_gerados persistido pela rota; registros de visitante com origem="visitante".
- F4: unificar MAX_SANDBOXES (protecao) e MAX_SANDBOXES_ATIVOS (sandbox) numa constante só. F5: mover avisos para docstrings de RespostaIA/chamar_ia. F8: rótulo humano para chaves de imposto no PDF.
- /lab entra em ConstructionMiddleware.LIBERADO (app/main.py:296): modo construção do site não derruba as demos.
- Assets: todo CSS/JS novo com `?v={{ asset_v }}` E adicionado a `scripts/minify_build.py`; fontes woff2 baixadas para app/static/lab/fonts/ (servidas locais, sem host externo); ícones vendorizados como sprite SVG por demo (licenças MIT/ISC citadas em comentário).
- Anti-emoji U+FE0E em todo símbolo textual. Páginas internas de demo com noindex; vitrine indexável + sitemap.
- data/site.db real intocável; verificação DATA_DIR=$(mktemp -d); kill por PID próprio; 8055 intocável. Branch: worktree de `conserto-capa` (a lab-fundacao será mergeada nela na Task 1). NENHUM deploy sem OK explícito do Leandro (Lab sobe completo).

---

### Task 1: Merge da fundação + tokens das três identidades + assets

**Files:**
- Merge: branch `lab-fundacao` (2e34115) na branch de trabalho (worktree novo de conserto-capa) — a revisão final já provou merge limpo (628 testes).
- Create: `app/static/lab/lab-base.css` (reset da demo, barra fina, faixa contrate, tokens compartilhados), `app/static/lab/admita.css`, `app/static/lab/notavel.css`, `app/static/lab/caderneta.css` (tokens de marca: cores/AA das pranchas, fontes, raios 16/22/28, sombras suaves), `app/static/lab/fonts/*.woff2` (Alegreya 500/600/700+ital, Karla 400/600/700, Source Serif 4 600/700, IBM Plex Sans 400/600, IBM Plex Mono 400/600, Lora 500/600+ital, Nunito Sans 400/700/800 — baixadas do Google Fonts, @font-face local, font-display swap), `app/static/lab/icones/{admita,notavel,caderneta}.svg` (sprites com 25-40 ícones selecionados por demo das libs aprovadas, símbolos citados nos fluxos das Tasks 4-9), `app/templates/lab/_base_demo.html` (tela cheia sem chrome do site; barra fina "Demo do Lab · por Leandro Furtado · voltar"; faixa de conversão com tagline da marca + botão contato `?origem=lab-<demo>`; slot de conteúdo; carrega lab-base.css + css da demo com ?v=).
- Modify: `scripts/minify_build.py` (adicionar os 4 CSS novos e futuros JS do lab), `app/main.py:296` (/lab em LIBERADO), `app/lab/protecao.py`+`app/lab/sandbox.py` (F4 constante única), `app/lab/ia.py` (F5 docstrings), `app/lab/pdf.py` (F8 rótulos humanos de imposto).
- Test: `tests/lab/test_base_demo.py` (base renderiza com css/?v= corretos por demo; faixa presente; fontes locais existem nos caminhos; sprites existem e contêm os ids esperados), ajustes de F4 nos testes existentes.

**Interfaces — Produces:** template pai `lab/_base_demo.html` com blocos `{% block demo_conteudo %}`, contexto exigido `{demo: 'admita'|'notavel'|'caderneta'}`; classes utilitárias de lab-base.css: `.celula` (ícone/avatar+nome+valor), `.kpi`, `.cartao-ia`, `.pill`, `.botao`, `.skeleton` — nomeadas aqui e usadas por TODAS as telas.

- [ ] Merge + testes verdes (628 esperados) e commit; [ ] tokens/fonts/sprites com testes; [ ] F4/F5/F8 + LIBERADO com testes; [ ] suíte completa; [ ] commits pequenos PT-BR.

### Task 2: Rotas públicas seguras + F1/F2 do rate limiter

**Files:** Modify: `app/lab/rotas.py` (estrutura de rotas das 3 demos + vitrine, todas com dependencies=[limitar_taxa]; ping incluído), `app/lab/protecao.py` (F1: poda inline dentro de limitar_taxa a cada 500 chamadas; F2: chave `ip:token-validado` — token só entra na chave se existir em lab_sandbox, senão só IP; remover chamada de podar_janelas_vazias do cron em sandbox.py com comentário do porquê).
**Test:** `tests/lab/test_rotas_protegidas.py`: TODA rota /lab registrada tem limitar_taxa (varredura programática com sentinela ≥N rotas); rotação de cookie forjado NÃO escapa do 429 (100 requests com cookies aleatórios inválidos → mesma chave IP → 429); poda inline comprovada (dict não cresce após janelas expiradas + 500 chamadas).

- [ ] Testes → falhar → implementar → suíte verde → commit.

### Task 3: Vitrine /lab (ritmo Einar, identidade do site)

**Files:** Create: `app/templates/lab/vitrine.html` (herda base.html DO SITE, header padrão Nodal com links do site), `app/static/lab/vitrine.css` + `vitrine.js` (reveals GSAP no padrão do main.js). Modify: rotas (GET /lab), sitemap (vitrine entra; internas noindex via meta no _base_demo), menu/rodapé do site (link "Lab" — remover "em breve" se houver), `scripts/minify_build.py`.
**Conteúdo:** manifesto curto (voz do Leandro, sem travessão), lista VERTICAL dos 3 cards em imagem cheia (img-slot placeholder até a Task 12; título modesto abaixo; tags pill "IA aplicada · <setor>"; card inteiro é link), CTA texto+seta para /contato?origem=lab. SEO: title/description com termos da pesquisa de mercado §5, JSON-LD.
**Test:** vitrine 200 + indexável; internas com noindex; sitemap contém /lab; cards apontam para as 3 demos; menu do site linka.

- [ ] Testes → implementar → verificação visual viva (desktop+mobile) → suíte → commit.

### Task 4: Admita — esteira kanban completa

**Files:** Create: `app/templates/lab/admita/esteira.html` + fragmentos (`_card_candidato.html`, `_checklist.html`, `_auditoria.html`), `app/static/lab/admita.js`. Modify: rotas (GET /lab/admita; POST mover etapa, aprovar RH/gestor, marcar documento — fragmento-swap; regras de negócio da spec §6.1: não avança sem docs conferidos, gestor exige RH antes, tudo auditado), contadores origem="visitante" e checar_limite_registros ao criar candidato novo (formulário simples de texto validado).
**UI:** colunas kanban arredondadas; célula avatar+nome+cargo; chips de SLA por item pendente (a assinatura: prazo visível, cor índigo/coral por urgência); drag com fallback por botão; feedback otimista com desfazer; trilha de auditoria em painel lateral com ícones; copy na voz de RH (estudo setorial: admissão digital, eSocial, trilha de auditoria).
**Test:** regras de esteira (bloqueios), auditoria gravada, limite do 11º candidato, fragmentos 200, |safe ausente, rate limit na rota.

- [ ] Testes → implementar → verificação visual viva → suíte → commit.

### Task 5: Admita — triagem por IA + captura

**Files:** fragmento `_triagem.html`, rota POST /lab/admita/triagem (texto colado validado MAX_CURRICULO ou exemplo pronto; chamar_ia("triagem_curriculo", contexto={"instancia_id": candidato_id}); skeleton com formato do resultado; score com contagem incremental 200-400ms; cartão-IA com justificativa por critério; selo discreto quando origem="fallback"), captura opcional de e-mail ("receber esta análise por e-mail") → lab_lead + envio via SMTP existente respeitando MAX_EMAILS.
**Test:** fluxo com API falsa (ia e fallback), motivo_fallback nunca no HTML, validação de texto hostil na rota, lead gravado com demo/momento, teto de e-mails.

- [ ] Testes → implementar → verificação visual viva → suíte → commit.

### Task 6: Notável — NF em 3 passos + contas a receber

**Files:** `app/templates/lab/notavel/painel.html` + fragmentos (`_passo1_cliente.html`, `_passo2_itens.html`, `_passo3_impostos.html`, `_recebiveis.html`), `app/static/lab/notavel.js`, rotas GET/POST.
**Regras (§6.2 + estudo fin):** 3 passos com stepper; impostos calculados e EXPLICADOS na tela (base, alíquota, valor, rótulos humanos da F8); numeração sequencial por sandbox (helper próprio na rota, herança registrada); emitir → PDF (gerar_nf_pdf, pdfs_gerados persistido) + linha em recebíveis com status; cancelar nota reflete no painel; KPI grande "A receber" com números tabulares e transição incremental; vocabulário NF-e/NFS-e/DANFE/DRE.
**Test:** ciclo emitir→receber→cancelar, numeração 7+ (seeds 1-6), teto de PDFs, valores centavos→R$ vírgula, rate limit, |safe.

- [ ] Testes → implementar → verificação visual viva → suíte → commit.

### Task 7: Notável — categorização de extrato por IA + captura

**Files:** fragmento `_categorizar.html`, rota POST (texto MAX_EXTRATO ou exemplo; chamar_ia("categorizar_extrato", instancia_id=hash do lote); feed com ícone em container por categoria, estado por item, justificativa curta, confirmar/corrigir com UI otimista + desfazer), captura "receber o relatório por e-mail".
**Test:** categorias só da lista fechada renderizadas, fallback selado, hostil rejeitado, lead/momento, e-mail teto.

- [ ] Testes → implementar → verificação visual viva → suíte → commit.

### Task 8: Caderneta — grade da turma + fechamento de bimestre

**Files:** `app/templates/lab/caderneta/diario.html` + fragmentos (`_celula_nota.html`, `_situacao.html`), `app/static/lab/caderneta.js`, rotas.
**Regras (§6.3 + estudo escola):** grade alunos×disciplinas com lançamento célula a célula (tab navega, salva no blur com feedback otimista); médias ponderadas ao vivo; RÉGUA VISÍVEL (média ≥ da tela e frequência mínima explicitadas ao lado da grade); situação por média E frequência com chips; FECHAR BIMESTRE como gesto formal (confirmação, trava lançamentos, libera boletins) — o padrão que o setor inteiro usa; copy na voz de professor/secretaria (bimestre, recuperação, conselho de classe).
**Test:** média ponderada correta, situação nas 3 vias (incluindo reprovado por falta com média alta), fechamento trava edição, limite de alunos novos, rate limit, |safe.

- [ ] Testes → implementar → verificação visual viva → suíte → commit.

### Task 9: Caderneta — boletim PDF + parecer por IA + captura

**Files:** fragmento `_boletim.html`, rotas (gerar boletim: gerar_boletim_pdf com a situação CANÔNICA calculada na rota — substitui a heurística de exibição do pdf.py, herança T5; parecer: chamar_ia("parecer_pedagogico", contexto={"instancia_id": aluno_id, "situacao": ...}) com efeito de texto surgindo linha a linha; pill IA; professor pode regenerar 1x dentro do teto), captura "enviar este boletim por e-mail".
**Test:** situação canônica bate com a da grade, parecer coerente com situação (fallback por pool), pdfs/emails tetos, lead.

- [ ] Testes → implementar → verificação visual viva → suíte → commit.

### Task 10: Painéis "Como foi feito" + polimento de conversão

**Files:** `app/templates/lab/_como_foi_feito.html` (parcial por demo, conteúdo próprio: problema→solução→resultado SEM travessão na prosa, stack nomeando LLM/prompts estruturados/validação de saída/fallback determinístico, os diferenciais de cada demo), integrado às 3 demos como painel/rota; lapidação final da faixa contrate por demo (copy na voz do público).
**Test:** painel presente nas 3, termos técnicos presentes (grep), links de contato com origem correta.

- [ ] Testes → implementar → suíte → commit.

### Task 11: Mobile (módulo-chave responsivo + tour) + varredura de copy

**Files:** media queries nos 4 CSS; `_tour.html` (telas secundárias no mobile: tour visual elegante + convite "abra no computador"); varredura FINAL de copy: sem travessão, U+FE0E em símbolos, voz por persona (checklist contra os estudos setoriais).
**Módulos-chave no mobile:** esteira+triagem (Admita), 3 passos+PDF (Notável), lançar nota+boletim (Caderneta).
**Test:** viewports 390/360 sem overflow horizontal nas telas-chave; teste automatizado de travessão em templates do lab (varre — e – como pontuação em texto visível, com sentinela); anti-emoji.


**Achados herdados da revisão da T3 (obrigatórios nesta tarefa):**
- **A1 (MÉDIO, WCAG 2.2 SC 2.5.8):** em 390x844 os links do cabeçalho do Lab (`app/static/css/main.css:194` `.nav-link` + `app/static/lab/vitrine.css:147`) ficam com alvo de toque de 17.6px de altura e 6px de gap, sem fallback de hambúrguer. Elevar para **24x24px no mínimo** via padding vertical e gap, na vitrine e nas demos (o cabeçalho é componente único). **Não alterar as medidas do cabeçalho no desktop**, que o dono aprovou como idênticas às do Nodal.
- **A2:** travar em teste a estrutura da vitrine que o dono mais corrigiu à mão: hero com exatamente 3 linhas (título/subtítulo/descritivo), grid de 3 colunas, tags em uma linha com divisória superior.
- **A3:** travar em teste o guard de `app/static/js/main.js:223` que desliga as dicas de IA no Lab sem desligá-las na home.

- [ ] Testes → implementar → verificação visual viva mobile → suíte → commit.

### Task 12: Performance, imagens e GIFs

**Files:** capturas reais das demos prontas para os img-slots da vitrine (gerar via navegador, salvar em app/static/lab/img/ com escada responsiva pelo pipeline existente + srcset); GIFs de ~10s por demo (gravar fluxo matador; ferramenta local gratuita; otimizar peso); auditoria Lighthouse mobile das 3 demos + vitrine (meta ≥90) com correções; conferir minify list completa e ?v= em tudo.
**Test:** pesos máximos definidos (GIF ≤ 2.5MB), srcset presente, Lighthouse registrado no relatório.

- [ ] Gerar → medir → corrigir → suíte → commit.

### Task 13: Revisão final de branch + pacote de lançamento

Revisão final no modelo mais capaz (interações, segurança de ponta a ponta com as rotas REAIS agora expostas, jornada completa nas 3 demos, herança F1-F8 fechada). Depois: verificação visual do Leandro (veredito dele nas telas) e, SÓ com o OK explícito dele, deploy único do Lab completo + post de divulgação (segundo momento).

- [ ] Pacote de revisão → revisor final → consertos se houver → veredito do Leandro → aguardar OK para deploy.

## Self-review (feito na escrita)

- Cobertura: §3 (T3, T10), §6.1 (T4-5), §6.2 (T6-7), §6.3 (T8-9), §10 (T5/7/9/10, leads e SEO em T3), §14 (transversal + T12), §12b (identidades fixadas nas Global Constraints), herança F1-F8 (T1-T2 e Global), regras novas dele (ícones/rounded/voz/travessão — Global + T11). Sem órfãos.
- Sem placeholders: valores exatos vivem nas Global Constraints e nos arquivos-fonte nomeados (pranchas aprovadas, estudos) que cada dispatch entrega ao implementador; interfaces de template/rota nomeadas por task.
- Consistência: nomes de arquivos/classes utilitárias (.celula/.kpi/.cartao-ia) definidos na T1 e consumidos nas T4-T11 com a mesma grafia.
