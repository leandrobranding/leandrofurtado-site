# leandrofurtado.com.br

Portfólio, painel administrativo e sala de demonstrações, feitos do zero e
rodando em produção em [leandrofurtado.com.br](https://leandrofurtado.com.br).

Não é exercício nem template adaptado. É o site que está no ar, com o código
que está no ar.

```
574 testes em pytest   ·   66 templates   ·   Python 3.13
FastAPI + SQLAlchemy 2.0 + SQLite (WAL) + Jinja2
Docker e nginx num VPS Linux de 1 vCPU
```

---

## O que tem dentro

**Site público.** Portfólio com casos, clientes e categorias, busca, dois
idiomas com URLs próprias e `hreflang`, JSON-LD de `Person` e `WebSite`,
`sitemap.xml` gerado do banco, newsletter com confirmação por e-mail e página
de contato com anti-spam.

**Painel administrativo.** CRUD de casos, clientes, categorias, mídia e
configurações; upload com processamento de imagem; reordenação arrastando;
trilha de auditoria; login com Argon2 e segundo fator por código.

**Lab.** Sala de demonstrações onde sistemas SaaS rodam de verdade dentro do
site, abertos ao público sem cadastro. O primeiro é o **Admita**, de admissão
de pessoal: esteira em kanban com regras que travam o avanço, checklist
obrigatório, aprovações em ordem, agenda de entrevistas e trilha de auditoria.
Cada visitante recebe um sandbox isolado por cookie que expira em 24 horas
(`app/lab/sandbox.py`).

**Currículo em PDF.** Gerado na hora a partir do mesmo perfil que alimenta a
página Sobre, nos dois idiomas, com as fontes da casa embutidas
(`app/services/resume.py`). Não existe arquivo de currículo no servidor, então
não existe currículo desatualizado.

---

## Decisões que valem explicação

**SQLite, não Postgres.** Um vCPU, um processo de escrita, tráfego de
portfólio. SQLite em modo WAL resolve com menos peça móvel, e o backup é um
arquivo. Trocar por Postgres seria adicionar um serviço para resolver um
problema que não existe.

**Sem framework de front.** Jinja2 renderizando no servidor, CSS e JavaScript
escritos à mão. A página chega pronta, o robô de busca lê sem executar nada, e
não há bundle para carregar. As animações são CSS e GSAP; o 3D é Three.js, e só
onde ele é o conteúdo.

**SEO derivado, não digitado.** Título e descrição de cada página saem de uma
fórmula sobre o conteúdo (`app/services/seo.py`), medida contra o que o Google
desenha: 60 caracteres de título, 155 de descrição. Campo de SEO em formulário
fica vazio ou repete a linha de cima; fórmula não esquece.

**Anti-spam sem serviço externo** (`app/services/anti_spam.py`). Três camadas:
filtro de conteúdo, carimbo de tempo assinado e limite por IP. O bot recebe
sucesso falso e nada é gravado. Zero dependência paga.

**Migrações declarativas** (`app/services/migrations.py`). O esquema esperado é
declarado; o que falta é criado no boot. Sem ferramenta de migração para um
banco de um arquivo.

**Produto embutido é módulo opcional.** O site hospeda um produto próprio que
ainda não foi lançado e não está neste repositório. O acoplamento com ele foi
desfeito: `app/main.py` decide em tempo de import se o módulo existe, e todas
as costuras (routers, índice de busca, mapa do site) ficam atrás desse teste.
A suíte roda dos dois lados. Produto embutido que impede o hospedeiro de subir
não é produto embutido, é acoplamento.

**Custo zero como restrição de projeto.** Busca por imagem sem API paga,
backup sem plano contratado, e-mail pelo SMTP que já existia. A restrição é
real, não retórica: o VPS foi o limite do orçamento.

---

## Rodando localmente

Precisa de **Python 3.13**, a mesma versão da imagem de produção
(`FROM python:3.13-slim`). O Python que vem no macOS é 3.9 e não instala a
pilha travada em `requirements.txt`.

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

O banco e a pasta de mídia nascem sozinhos em `data/` no primeiro boot, junto
com um usuário administrador cuja senha é gerada e escrita em
`data/ADMIN_CREDENTIALS.txt`. Nenhum segredo é versionado.

Para dados de exemplo:

```bash
python3 scripts/seed_demo.py
```

## Testes

```bash
pytest
```

574 testes, banco em memória, sem rede. O deploy trava se a suíte parar.

Os testes deste projeto documentam o motivo, não só o comportamento: quase todo
arquivo abre com o problema real que o gerou, com data. `tests/test_seo_derivado_de_case.py`
guarda os orçamentos do resultado de busca; `tests/lab/test_regras_seguranca.py`
guarda o isolamento entre sandboxes; `tests/test_selos_rodape.py` quebra se o
site parar de entregar os cabeçalhos de segurança que o selo do rodapé afirma.

## Estrutura

```
app/
  main.py           middlewares, idioma, rotas raiz
  routers/          site público, admin, API
  services/         seo, imagens, anti-spam, migrações, currículo, e-mail
  lab/              sala de demonstrações e o Admita
  templates/        Jinja2
  static/           css, js e fontes
deploy/             nginx, scripts de subida, deploy e backup
docs/superpowers/   specs e planos de implementação
tests/              574 testes
```

## Deploy

`deploy/subir.sh` prepara um VPS Ubuntu do zero: Docker, nginx, certificado
e serviço. `deploy/atualizar.sh` atualiza, e **exige um backup verificado antes
de qualquer alteração**: baixa o banco pela API de backup do SQLite, confere a
integridade, e só então sobe. `data/` nunca é tocado pelo deploy.

Os scripts esperam `CHAVE_SSH` e o IP do servidor como argumento.

---

© Leandro Furtado. Código publicado para leitura; todos os direitos reservados.
