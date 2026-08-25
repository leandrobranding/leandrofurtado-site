# Design — leandrofurtado.com.br

**Data:** 2026-08-06 · **Aprovado pelo usuário:** direção visual dark ("me surpreenda"), VPS Hostinger, bilíngue PT-BR/EN.

## Objetivo

Portfólio + currículo vivo de Leandro Furtado (Diretor de Arte Sênior, Curitiba), nível "site do ano":
dark, tipografia display gigante, motion fluido — mix vividmotion.co × 2xa.studio. Admin completo para
cases (fotos, vídeos, áudios, embeds de Instagram/matérias) com publicação automática no Instagram.
SEO máximo para Google e plataformas de recrutamento (Gupy, Catho, InfoJobs, Indeed, LinkedIn).

## Decisões

- **Stack:** Python 3.13 · FastAPI · Jinja2 (SSR = SEO) · SQLAlchemy + SQLite · Pillow · httpx.
- **Frontend:** vanilla JS autocontido (sem CDN): smooth scroll (lerp), reveals via IntersectionObserver,
  parallax, cursor customizado, transições de página. CSS custom properties, tema #090909.
- **i18n:** prefixo `/en` via middleware; campos `_pt`/`_en` no banco; hreflang + sitemaps.
- **Admin:** sessão assinada (itsdangerous) + Argon2 + CSRF + rate-limit de login. CRUD de cases,
  upload com validação (Pillow verify, limites), reordenação, editor de CV estruturado, settings.
- **Instagram:** Meta Graph API (container → publish) ao publicar case, com token nas settings; status salvo.
- **SEO ético:** JSON-LD (Person, ProfilePage, WebSite, CreativeWork, Breadcrumb), OG/Twitter cards,
  sitemap.xml, robots.txt, canonical. **Sem** "injection prompts" ocultos (prática enganosa, penalizada
  pelo Google) — recusado e substituído por dados estruturados legítimos.
- **Deploy:** Docker (python:3.13-slim) + docker-compose + Nginx + certbot + UFW. Guia em deploy/DEPLOY.md.
- **CV:** página /cv imprimível (PDF via imprimir do navegador), dados do resumo fornecido, editável no admin.

## Modelos

User · Category · Tag · Case (bilíngue, cover, categoria, tags, featured, published, ordem, status IG)
· MediaItem (image/video/audio/embed, bilíngue, ordem) · Profile (JSON CV pt/en) · SiteSetting · ContactMessage.

## Fora de escopo (v1)

Newsletter, blog, analytics próprio (campo p/ script de terceiros nas settings), multiusuário no admin.
