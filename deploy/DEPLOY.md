# Deploy — leandrofurtado.com.br na Hostinger (VPS)

Guia completo, do zero ao site no ar com HTTPS e firewall. Tempo estimado: ~30 min.

## 0. O que você precisa

- VPS Hostinger **KVM 1** (1 vCPU, 4 GB RAM, 50 GB NVMe). Sobra folga para este site.
  Hospedagem compartilhada **não serve**: ela não roda Docker nem processo Python contínuo.
- Datacenter **Brasil (São Paulo)**, pelo tempo de resposta.
- Sistema: template **Ubuntu 24.04 com Docker**, que já vem com docker e docker compose.
- Domínio `leandrofurtado.com.br` apontado para o IP do VPS:
  no painel da Hostinger (ou onde o DNS estiver), crie os registros:
  - `A` → `leandrofurtado.com.br` → IP do VPS
  - `A` → `www` → IP do VPS

## 1. Acesse o VPS e prepare o sistema

```bash
ssh root@SEU_IP
```

O template já traz docker e docker compose, então aqui só falta o resto:

```bash
apt update && apt upgrade -y
apt install -y nginx certbot python3-certbot-nginx git ufw
```

Se você escolheu o Ubuntu 24.04 **sem** Docker, acrescente `docker.io docker-compose-v2`
nessa mesma linha.

## 2. Firewall (UFW)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

Só SSH, HTTP e HTTPS ficam abertos. A aplicação (porta 8000) fica acessível apenas
localmente (`127.0.0.1`), atrás do Nginx.

**Extra recomendado (anti brute-force no SSH):**

```bash
apt install -y fail2ban && systemctl enable --now fail2ban
```

## 3. Suba o código

No seu Mac, envie a pasta do projeto para o VPS:

```bash
rsync -avz --exclude '.venv' --exclude 'data' --exclude '.git' "/Users/leandrofurtado/LEANDRO FURTADO/leandrofurtado-site/" root@SEU_IP:/opt/leandrofurtado-site/
```

## 4. Rode a aplicação

O container roda como usuário `appuser` (uid 1000). A pasta `data` no host guarda o
banco e os uploads, então ela precisa pertencer a esse mesmo uid — se você pular isso,
o container sobe e morre sem conseguir gravar o SQLite.

```bash
cd /opt/leandrofurtado-site
mkdir -p data
chown -R 1000:1000 data
docker compose up -d --build
```

Verifique: `curl -I http://127.0.0.1:8000` deve responder `200 OK`.
Se algo falhar, `docker compose logs -f web` mostra o motivo.

**O que já vem pronto no primeiro boot:** currículo completo (experiências,
certificações, prêmio, skills), categorias dos cases, redes sociais, CNPJ, e-mails e os
logotipos SVG dos clientes. Nada disso precisa ser redigitado. O que **não** vem são os
cases (você cria no painel) e as credenciais de SMTP, Anthropic e Instagram.

**Senha do admin:** no primeiro boot uma senha forte é gerada em
`/opt/leandrofurtado-site/data/ADMIN_CREDENTIALS.txt`:

```bash
cat /opt/leandrofurtado-site/data/ADMIN_CREDENTIALS.txt
```

Guarde e depois **troque a senha** em Configurações no painel. Se preferir definir a sua,
descomente `ADMIN_PASSWORD` no `docker-compose.yml` **antes** do primeiro boot.

## 5. Nginx + HTTPS

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/leandrofurtado.com.br
ln -s /etc/nginx/sites-available/leandrofurtado.com.br /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
```

Antes do certificado existir, o Nginx não sobe com os blocos 443. Emita primeiro o certificado
usando só o bloco 80 (comente temporariamente os dois `server` de 443 se precisar) e rode:

```bash
certbot --nginx -d leandrofurtado.com.br -d www.leandrofurtado.com.br
nginx -t && systemctl reload nginx
```

O certbot renova sozinho (timer do systemd). Pronto: **https://leandrofurtado.com.br** no ar.

## 6. Primeiros passos no painel

Acesse `https://leandrofurtado.com.br/admin` e faça login. O Dashboard lista as
pendências em tempo real: siga a lista dele até zerar.

### 6.1 Trocar a senha
**Configurações → Senha.** Faça isso antes de qualquer outra coisa e apague o
`data/ADMIN_CREDENTIALS.txt` do servidor depois.

### 6.2 SMTP (obrigatório para leads e newsletter)
Sem isso o formulário de contato salva o lead no painel mas não te avisa por e-mail, e a
newsletter não sai. Com Gmail:

1. Ative a verificação em duas etapas na conta Google.
2. Gere uma **senha de app** em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   (16 caracteres, sem espaços).
3. Em **Configurações → SMTP**, preencha:
   - Host: `smtp.gmail.com` · Porta: `587`
   - Usuário: seu Gmail · Senha: a senha de app (não a senha da conta)
   - Remetente: o mesmo Gmail · E-mail dos leads: para onde o aviso vai
4. Teste: envie uma mensagem pelo `/contato` do site e confira se o e-mail chegou.

### 6.3 Chave da Anthropic (busca por imagem)
Em [console.anthropic.com](https://console.anthropic.com) crie uma API key e cole em
**Configurações → Anthropic**. Sem ela a busca por texto e voz continua funcionando; só
a busca por imagem fica desligada.

### 6.4 Conteúdo
1. **LinkedIn** → apague os 6 posts de demonstração e cadastre os reais (resumo, tag e
   link do post).
2. **Perfil & CV** → suba a foto de perfil e a de capa, e revise os textos.
3. **Cases** → crie os cases de verdade: capa, mídia, cliente, ano, tags e categoria.
   O cliente do case vira marca clicável automaticamente em todo o site.
4. **Marcas & Clientes** → suba o SVG dos clientes novos. Sem SVG a marca aparece como
   assinatura tipográfica, que funciona, mas o logo fica melhor.

### 6.5 Newsletter
**Newsletter → Nova campanha.** Escreva em Markdown, escolha o público, clique em
**Ver e-mail ↗** para conferir a peça, mande um **teste** para você e só então dispare.
Todo envio leva link de descadastro assinado, exigência da LGPD e do GDPR.

## 7. Instagram (publicação automática)

1. Converta seu Instagram para conta **profissional** e vincule a uma Página do Facebook.
2. Em [developers.facebook.com](https://developers.facebook.com), crie um app → produto
   **Instagram Graph API**.
3. Gere um token de usuário com permissões `instagram_basic`, `pages_show_list` e
   `instagram_content_publish`; troque por um **token de longa duração** (60 dias, renovável).
4. Descubra o **IG User ID** (via Graph Explorer: `me/accounts` → `?fields=instagram_business_account`).
5. Cole ID + token em **Admin → Configurações → Instagram** e marque a publicação automática.
6. Em cada case, marque "Publicar no Instagram ao publicar". A capa do case vira o post,
   com legenda gerada (título + subtítulo + link + hashtags das tags).

## 7b. Firewall de aplicação + CDN (Cloudflare — grátis e recomendado)

O UFW protege as portas do servidor; para proteção de camada 7 (WAF), anti-DDoS e cache
global, coloque o site atrás do **Cloudflare (plano Free)**:

1. Crie conta em cloudflare.com → **Add site** → `leandrofurtado.com.br`.
2. Aponte os nameservers do domínio (painel Hostinger → Domínio → Nameservers) para os
   dois NS que o Cloudflare indicar.
3. No Cloudflare, deixe os registros `A` (raiz e www) com a **nuvem laranja** (proxy ON).
4. **SSL/TLS → Full (strict)** (o certbot do servidor continua válido).
5. Ative: **WAF managed rules**, **Bot Fight Mode**, **Always Use HTTPS**, **Brotli**,
   e em **Caching** use o padrão (estáticos do site já saem com Cache-Control).
6. (Opcional) **Rate limiting** na rota `/admin/login`.

Resultado: WAF gerenciado + DDoS mitigation + CDN global na frente do VPS — e o IP de
origem fica oculto.

## 7c. Performance (PageSpeed 100)

O site foi estruturado para nota máxima: SSR sem bloqueio, fontes self-hosted com
`preload`, JS todo `defer`, Three.js carregado **depois** do load (fora do caminho
crítico), imagens WebP com lazy-load e aspect-ratio fixo (zero CLS), CSS único enxuto.
Com Nginx (gzip) + Cloudflare (brotli/CDN) o resultado esperado no
[PageSpeed Insights](https://pagespeed.web.dev) é 95–100 em todas as categorias.
Rode o teste após o deploy com o domínio final.

## 8. Backup (importante)

Tudo que muda está em `/opt/leandrofurtado-site/data` (banco SQLite + uploads).
Backup diário automático para a home:

```bash
crontab -e
```

```
0 4 * * * tar -czf /root/backup-site-$(date +\%u).tar.gz -C /opt/leandrofurtado-site data
```

(mantém 7 dias rotativos; baixe de tempos em tempos para o seu Mac.)

## 9. Atualizações futuras

```bash
cd /opt/leandrofurtado-site
git pull            # ou rsync de novo a partir do Mac
docker compose up -d --build
```

## Checklist Google (fazer 1x após o ar)

- [Search Console](https://search.google.com/search-console): adicionar a propriedade
  `leandrofurtado.com.br`, verificar via DNS e enviar `https://leandrofurtado.com.br/sitemap.xml`.
- Testar rich results: https://search.google.com/test/rich-results (deve reconhecer **Person** e **ProfilePage**).
- PageSpeed: https://pagespeed.web.dev — o site é estático-leve (SSR + assets locais), deve pontuar alto.
