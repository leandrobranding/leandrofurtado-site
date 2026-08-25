# Lab de Demos — Spec de design

**Data:** 2026-08-20 · **Aprovada em brainstorm com o Leandro** (decisões dele registradas ao longo)
**Pesquisa de mercado anexa:** `.superpowers/sdd/2026-08-20-lab-demos/pesquisa-mercado.md` (ranking de demanda, padrões de portfólio que convertem, recursos de IA com mais impacto, termos de SEO — com fontes)

## 1. Visão

Seção do site leandrofurtado.com.br com sistemas SaaS **funcionais, rodando ao vivo**, que provam a empresas o que o Leandro entrega como engenheiro de IA. Não é galeria de prints: o visitante entra no produto e usa. Frase-guia dele: "Não vou te CONTAR o que sei construir. Vou te deixar CLICAR."

O Lab entra no ar **completo** (as 3 demos da 1ª leva juntas) como segundo momento de divulgação do site.

## 2. Decisões fixadas (não rediscutir na implementação)

1. **Um módulo matador por sistema** — nunca sistemas completos.
2. **Identidade visual própria por demo** — nunca a do site; processo: Claude propõe 3 marcas completas (nome fictício do produto, paleta, tipografia, tom), Leandro dá o veredito no navegador ANTES de qualquer tela ser construída.
3. **Faixa de conversão em toda tela de demo** — "Gostou? Eu construo isso para a sua empresa → entre em contato" (copy a lapidar na implementação, aprovação dele).
4. **Sandbox por visitante** — isolado, pré-povoado, expira em 24h.
5. **IA híbrida com teto de gasto** — chamadas reais (chave Anthropic do admin, modelo barato) com tetos duros; estourou, entra resposta pré-gerada de qualidade com selo discreto "exemplo pré-computado". A demo nunca quebra.
6. **Atrito zero na entrada + captura opcional em momentos de valor** — nunca portão de cadastro.
7. **Mobile: módulo-chave responsivo + tour elegante no resto** — telas secundárias mostram tour visual + "abra no computador para a experiência completa".
8. **Limites BAIXOS e rígidos** (palavras dele: "O limite precisa ser baixo para o usuário não abusar dos testes") — números na §8.
9. **ZERO uploads, em qualquer demo, em qualquer leva futura** (decisão de segurança dele) — só texto curto e cliques; PDFs só saem, nunca entram.
10. **Texto de visitante é texto morto** (decisão de segurança dele) — blindagem completa na §9.
11. **Regra anti-emoji absoluta do site vale no Lab** — todo símbolo com U+FE0E ou SVG.
12. **Custo zero em serviços** — nada além do que já existe (VPS, chave Anthropic com teto).
13. **UI/UX no estado da arte (pedido dele, 20/08):** antes da fase de identidades, PESQUISA dedicada do que há de mais moderno, ágil e bonito em UI/UX de SaaS — ícones modernos, fontes modernas que combinem entre si, cores complementares — alimentando as 3 propostas de marca. Nada de visual "de sistema antigo".
14. **Rapidez é requisito de produto (pedido dele):** a navegação dentro das demos precisa ser ÁGIL — orçamento de performance na §14.
15. **Sistemas com substância (pedido dele):** as demos devem demonstrar sistemas EFICAZES que resolvem problemas de verdade — não brinquedos simples. Cada módulo matador carrega regras de negócio reais e visíveis (§6 detalha por demo).
16. **Referências dele pendentes:** o Leandro vai enviar sistemas que são cases de sucesso como referência — elas se somam à pesquisa de mercado e à pesquisa de UI/UX (§2.13) antes da fase de identidades. A fase de identidades NÃO começa sem elas (ou sem ele liberar sem).

## 3. Jornada do visitante

- **`/lab` (vitrine):** manifesto curto; um card por demo com o nome do produto fictício, GIF de ~10s do fluxo matador (pesquisa: recrutador decide em ~15s) e botão "Entrar na demo". Link no menu do site e no rodapé. **Direção de design (dele, 20/08): layout/ritmo seguindo a referência do tema Einar (estudo em `.superpowers/sdd/2026-08-20-lab-demos/referencia-vitrine-einar.md`), com a pele na identidade DO SITE e header no padrão Nodal (mesma estrutura, mudam links) — a vitrine não é tela de demo, as identidades próprias valem só DENTRO das demos.**
- **Entrada:** 1 clique → sandbox criado e semeado → visitante cai dentro do produto com a identidade própria da demo.
- **CONCEITO DA MOLDURA (decisão do Leandro, 20/08, verbatim: "É um hub de sistemas dentro do universo do leandro"):** cada demo vive DENTRO do universo do site, emoldurada por DOIS elementos FIXOS na identidade do Leandro: (1) o cabeçalho padrão (mesma estrutura do padrão Nodal, mudam os links) com a logo Lab; (2) o rodapé com o CTA de contato ("Gostou? Eu construo isso para a sua empresa" com a tagline/voz aprovadas). A identidade própria de cada marca vale para TODO o miolo da demo; a moldura é do Leandro.
- **PRINCÍPIO DO ENXUTO (correção dele, 20/08, verbatim: "Como são demonstrações, precisam ter o básico para demonstração"):** as demos NÃO levam a barra de acessibilidade do site (decisão revista por ele), NÃO têm geolocalização, NÃO têm banner/registro de consentimento LGPD, NÃO carregam tracking. Nada de peso institucional do site dentro do Lab: só a moldura mínima (cabeçalho e rodapé) e o sistema demonstrado. Toda vez que surgir a dúvida "essa peça do site entra na demo?", a resposta padrão é NÃO, salvo pedido explícito dele.
- **Painel "Como foi feito"** (1 por demo): case Problema→Solução→Resultado, stack, onde a IA entra, nomeando técnicas (LLM, prompts estruturados, validação de saída, fallback determinístico) — vocabulário que recrutador de "engenheiro de IA" busca.

## 4. Arquitetura

Padrão do módulo Nodal, já provado no repo:

- **`app/lab/`**: `models.py`, `rotas.py` (router público `/lab`), `sandbox.py` (criação/seed/expiração), `ia.py` (guardião + prompts), `pdf.py` (NF e boletim via fpdf2, mesmo padrão do CV), `seeds_demo.py` (cenários fictícios).
- **Templates:** `app/templates/lab/` — `vitrine.html`, base própria `lab/_base_demo.html` (NÃO herda o base.html do site) e um diretório por demo.
- **CSS:** um arquivo por demo (`lab-<demo>.css`) + `lab.css` (vitrine e barra comum). Sem tocar no main.css do site. ATENÇÃO (achado da rodada PageSpeed): a minificação do build Docker (scripts/minify_build.py) deve incluir os CSS/JS novos do Lab, e todo asset novo referenciado leva `?v={{ asset_v }}`.
- **Banco:** mesmas SQLite/engine, tabelas prefixadas `lab_`, TODAS com coluna `sandbox_id` indexada. Migrações pelo padrão existente (migrations.py COLUNAS / create_all).
- **Sandbox:** cookie `lf_lab_sandbox` (httponly, samesite=lax, 24h). Primeiro acesso a qualquer demo cria o registro `lab_sandbox` + roda o seed do cenário. Requisições com cookie de sandbox inexistente/expirado ganham sandbox novo, transparente.
- **Limpeza:** rotina diária (mesmo mecanismo de tarefas agendadas já usado no site) apaga sandboxes com mais de 24h e todos os seus registros. Guarda-chuva: se `lab_sandbox` ativos > 200, o mais antigo é reciclado ao criar o novo.

## 5. Modelo de dados (tabelas novas)

- `lab_sandbox`: id, token (=cookie), criado_em, expira_em, demo_origem, chamadas_ia (int), emails_enviados (int).
- RH: `lab_candidato` (sandbox_id, nome, cargo, etapa, dados fictícios), `lab_documento_status` (candidato_id, tipo, conferido bool), `lab_auditoria` (sandbox_id, quem, acao, quando).
- Financeiro: `lab_cliente_fiscal`, `lab_nota` (sandbox_id, cliente_id, itens JSON, impostos JSON, total, numero sequencial POR sandbox), `lab_lancamento` (extrato categorizado).
- Escola: `lab_aluno`, `lab_avaliacao` (aluno_id, disciplina, nota, faltas), `lab_parecer` (aluno_id, texto_ia, origem 'ia'|'fallback').
- Global: `lab_lead` (nome, email, demo, momento, criado_em) — leads NÃO expiram com o sandbox; `lab_ia_gasto` (dia, tokens, custo_estimado).

## 6. As três demos (1ª leva — validada pela pesquisa: manter as três)

**Substância obrigatória (§2.15):** cada demo mostra que resolve problema de verdade — regras de negócio reais funcionando diante do visitante, não CRUD raso. Por demo:
- RH: etapas com pré-requisitos de verdade (não avança sem documentos conferidos; aprovação de gestor exige a do RH antes), prazo/urgência visível por candidato, e a trilha de auditoria como recurso de compliance — dor real de RH.
- Financeiro: impostos calculados com regras visíveis e explicadas na tela (ISS/retenções simplificados mas corretos conceitualmente), numeração sequencial, status da nota (emitida/cancelada) refletindo no contas a receber — o ciclo, não só o formulário.
- Escola: médias ponderadas configuráveis por disciplina, situação do aluno derivada de regra visível (aprovado/recuperação/reprovado por média E frequência), fechamento de bimestre — a mecânica real de secretaria escolar.

### 6.1 RH — esteira de admissão
- **Fluxo matador:** esteira visual (Candidato → Documentos → Aprovação RH → Aprovação gestor → Admitido). Arrastar candidato entre etapas (com fallback por botão — acessibilidade e mobile), checklist de documentos SIMULADOS (itens fictícios prontos, visitante marca conferido/pendente — sem upload jamais), aprovações com 1 clique.
- **Trilha de auditoria** visível: quem, quando, o quê — em linguagem de RH.
- **IA real:** triagem de currículo com **score explicável** — texto colado (máx §8) ou 3 exemplos prontos → nota por critério + justificativa curta ("aderência de experiência: 8/10 porque…"). Recurso nº 1 da pesquisa.
- **Responsivo no mobile:** a esteira + triagem IA. Tour no resto.

### 6.2 Financeiro — emissão de NF
- **Fluxo matador:** emitir nota em 3 passos (cliente → itens/serviço → impostos calculados na tela) → **PDF na hora** com visual de documento fiscal real e tarja clara "DEMONSTRAÇÃO — SEM VALOR FISCAL". Numeração sequencial por sandbox.
- **Mini-dashboard** de contas a receber que reage à nota emitida.
- **IA real:** categorização de extrato — texto colado (ou "usar exemplo") → lançamentos classificados em categorias contábeis de lista FECHADA + justificativa.
- **Responsivo no mobile:** os 3 passos da emissão + PDF. Tour no resto.

### 6.3 Escola — diário de classe e boletim
- **Fluxo matador:** grade da turma (alunos × disciplinas), lançar notas e faltas nas células, médias ao vivo, **boletim em PDF** por aluno com 1 clique.
- **IA real:** **parecer pedagógico por aluno** — a partir de notas/faltas, texto descritivo em tom de professor. Diferencial de nicho apontado pela pesquisa (quase inexistente em portfólios).
- **Responsivo no mobile:** lançar nota + gerar boletim. Tour no resto.

## 7. Guardião de IA

Módulo único (`app/lab/ia.py`) por onde TODA chamada passa:
- Teto **por sandbox**: 3 chamadas (todas as demos somadas). Teto **diário global**: configurável no admin, default equivalente a ~R$0,50/dia; contagem em `lab_ia_gasto`.
- Modelo barato (Haiku; id configurável no admin junto da chave já existente).
- Estourou qualquer teto OU a API falhou → **fallback pré-gerado**: banco de respostas de alta qualidade por recurso (≥3 variações), selo discreto "exemplo pré-computado". Mesma tela, mesma qualidade percebida.
- **Prompt como dado:** texto do visitante entra delimitado como documento, nunca como instrução; prompt instrui explicitamente a ignorar comandos embutidos; saída VALIDADA antes da tela (score numérico no intervalo, categorias só da lista fechada, parecer com tamanho máximo) e escapada como qualquer texto.
- Painel no admin: gasto do dia/mês, chamadas por demo, taxa de fallback.

## 8. Limites (baixos, por decisão dele)

- Sandbox: TTL 24h · máx 200 sandboxes ativos.
- Registros criados por visitante: máx 10 por demo por sandbox (candidatos criados, notas emitidas, alunos adicionados…). Seeds não contam.
- Texto livre: currículo máx 5.000 caracteres · extrato máx 2.000 · qualquer outro campo texto máx 200. Rejeição (não truncamento) acima do limite, com mensagem elegante.
- IA: 3 chamadas por sandbox · teto diário global (§7).
- Rate limit: 30 requisições/min por sandbox; excedeu → 429 com tela amigável.
- E-mail de captura: máx 2 envios por sandbox; só envia o PDF que o próprio visitante gerou.
- PDFs gerados: máx 5 por sandbox.

## 9. Segurança (seção vinculante — cada item vira teste)

1. **Zero upload de arquivo** em qualquer rota do Lab — nenhuma rota aceita multipart/file. Teste automatizado garante.
2. **Todo texto de visitante é texto morto:** autoescape Jinja2 em tudo; **PROIBIDO `|safe`** sobre qualquer dado de visitante — inclusive nas telas do ADMIN (leads, gastos) onde ataque armazenado pegaria o dono. Teste automatizado varre templates do Lab por `|safe`.
3. **Entrada dura:** limites da §8; rejeição de caracteres de controle e invisíveis (permitidos: \n, \t); campos estruturados só aceitam formato exato (nota 0-10, valores monetários, datas).
4. **Banco:** só consultas parametrizadas via SQLAlchemy — proibido SQL por string.
5. **IA blindada** conforme §7 (dado delimitado, saída validada e escapada).
6. **PDF:** texto sanitizado antes do fpdf2 (mesmo filtro da entrada) — só glifos, nada interpretável.
7. **Herdado do site sem exceções:** CSP restritiva, security headers, HTTPS. O Lab não adiciona `unsafe-*` nem origem externa nova.
8. **Cookies do Lab** não carregam dado pessoal — só o token opaco do sandbox.
9. **Sem dado real:** todo conteúdo semeado é fictício e visivelmente fictício (empresa "fictícia declarada", CPFs inválidos por design, e-mails @exemplo.com.br).

## 10. Conversão, leads e SEO

- Faixa "me contrate" em toda tela (copy final aprovada por ele) → aponta para o contato do site com `?origem=lab-<demo>`.
- Captura opcional nos momentos de valor: "quer receber esta NF / este boletim / este relatório por e-mail?" → grava `lab_lead` com a demo e o momento; envio pelo SMTP já configurado (respeitando §8). Leads aparecem no admin atual marcados com origem.
- SEO da vitrine: title/description cruzando cargo + domínio + técnica + Curitiba (termos da pesquisa), JSON-LD, entrada no sitemap. Páginas INTERNAS das demos: `noindex` (conteúdo de sandbox não é para o Google).
- GIFs de 10s: gerados na fase final, a partir das demos prontas.

## 11. Testes

Padrão do repo (pytest, banco em memória, TestClient): ciclo do sandbox (criação, seed, isolamento entre dois sandboxes, expiração), limites da §8 (cada um), regras de segurança da §9 (upload rejeitado, |safe ausente, controle rejeitado, validação de saída da IA com respostas simuladas), guardião (teto por sandbox, teto diário, fallback em falha de API), fluxos de cada demo (esteira, NF+PDF, grade+boletim), leads, e integração com o site (vitrine no sitemap, noindex interno, faixa presente em toda tela).

## 12b. Fase de identidades (ordem vinculante)

Antes de qualquer tela: (1) pesquisa de UI/UX moderna (§2.13: ícones, fontes que combinem, cores complementares, padrões atuais de SaaS bonito e ágil); (2) referências de cases de sucesso enviadas pelo Leandro (§2.16); (3) proposta das 3 marcas completas; (4) veredito dele no navegador. Só então as telas são construídas.

## 12. Fora de escopo (YAGNI declarado)

Levas futuras (PDV, shopping, posto de saúde); código-fonte público das demos; login/conta no Lab; versão EN; métricas além do GA já existente; qualquer serviço pago novo.

## 13b. Lei da tela cheia

**REGRA ABSOLUTA (dele, 20/08, verbatim: "Force a não ter absolutamente nenhuma barra de rolagem (horizontal e vertical) em nenhuma parte da vitrine e sistemas"):** vale para a VITRINE e para as TRÊS DEMOS, em TODOS os tamanhos de tela, inclusive celular. Zero barra de rolagem de página, zero barra interna, zero horizontal, zero vertical. Tudo cabe por composição. No mobile, quando o layout do desktop não couber, a saída é RECOMPOR (cards viram linhas compactas, uma etapa por vez, densidade menor), nunca rolar. (decisão do Leandro, 20/08, verbatim: "não pode ter barra de rolagem em nenhum sistema e em nenhum momento. Precisa tudo se encaixar na tela do usuário de forma harmonica e sistemica... ser responsivo e otimizado para qualquer tipo de tela e tamanhos")

- Dentro das demos, a PÁGINA nunca rola: o shell é travado no viewport (100dvh), com moldura fixa (barra a11y + cabeçalho Lab + rodapé CTA) e o miolo preenchendo exatamente o espaço restante em grids/colunas que se encaixam.
- REGRA ENDURECIDA POR ELE (20/08, verbatim: "Nos sistemas, elimine toda e qualquer barra de rolagem, dentro ou fora dos sistemas, sejam elas horizontais ou verticais"): NENHUMA barra de rolagem existe nas demos, nem de pagina nem interna, nem vertical nem horizontal. O conteudo CABE POR COMPOSICAO. Quando uma lista puder crescer (o visitante adiciona ate 10 registros), a saida e densidade e paginacao (mostrar N por vez com navegacao discreta, condensar linhas, resumir), NUNCA rolagem. A utilitaria .rola-interno fica proibida dentro das demos; se ja estiver aplicada em algum lugar, sai.
- Cada tela é projetada para caber por composição (densidade, colunas, tamanhos fluidos com clamp), não por encolhimento forçado; harmonia e completude visual em qualquer viewport, de celular a ultrawide.
- A VITRINE /lab tambem entra nesta lei (decisao dele, 20/08: grid de 3 colunas "para evitar rolagem"): no desktop, hero enxuto + os 3 cards lado a lado + CTA em 3 colunas cabem em uma tela; no mobile a vitrine pode rolar, porque 3 cards empilhados nao cabem sem virar miniatura ilegivel.
- Teste vinculante por tela: em 390×844, 768×1024, 1280×800 e 1920×1080, document.scrollHeight <= viewport (sem rolagem de página) e nenhum overflow horizontal.

## 14. Orçamento de performance (§2.14 — rapidez como requisito)

- Interações dentro da demo respondem em **< 200ms percebidos**: SSR leve + atualizações parciais (fetch + troca de fragmento, padrão já usado no Nodal) — sem recarregar página inteira em ação de fluxo (mover candidato, lançar nota, adicionar item da NF).
- **Feedback otimista** nas ações de clique (a UI responde na hora; reverte com aviso elegante se o servidor negar).
- **Zero framework JS pesado** — vanilla como no resto do site; CSS/JS do Lab entram na minificação do build e no cache de 1 ano com `?v=`.
- IA é a única operação lenta permitida: SEMPRE com estado de carregando bonito (skeleton/progresso) e nunca bloqueando o resto da tela.
- PDFs gerados em < 1s (fpdf2 é local e leve; já provado no CV).
- Meta de auditoria: cada demo com Desempenho ≥ 90 no Lighthouse mobile (sem as cortinas do site, que não existem no Lab).

## 15. Riscos aceitos e mitigação

- **1 vCPU:** chamadas de IA são raras (teto) e PDFs leves; rate limit protege o resto. Sem worker novo.
- **Cache immutable de 1 ano** (rodada PageSpeed): TODO asset novo do Lab nasce com `?v=` — regra herdada, teste cobre.
- **Conteúdo de sandbox ofensivo visto por captura de e-mail:** o e-mail só envia o PDF do próprio visitante para o e-mail que ele informou — ninguém vê sandbox alheio.
