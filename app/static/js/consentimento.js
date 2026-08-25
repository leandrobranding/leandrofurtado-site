/* Carrega o Google Tag Manager via DOM, fora de qualquer <script> inline.
 *
 * Por quê arquivo próprio, e não o snippet padrão do GTM direto no <head>: a
 * CSP do site (SecurityHeadersMiddleware, em app/main.py) não usa nonce —
 * os scripts inline existentes passam por 'unsafe-inline' em script-src. Um
 * snippet novo ali funcionaria, mas passar batido por um mecanismo que existe
 * só por causa de terceiros de peso maior (VLibras) não é motivo pra crescer
 * o inline por conta própria. Um arquivo estático de verdade, com endereço
 * fixo, é a opção que não pede nada novo à CSP além do próprio domínio do
 * GTM em script-src — e é o que o brief pediu.
 *
 * A marca <meta name="gtm-id"> só carrega conteúdo quando o servidor já
 * decidiu que pode: cookie lf_consent=sim, gtm_id configurado no painel, e a
 * tela não é a área logada do aluno do Nodal (ver `_gtm_ativo` em
 * app/main.py). Sem conteúdo na marca, este arquivo não faz nada — por isso
 * ele pode ser incluído em toda página sem custo para quem não deu consentimento.
 */
(function () {
  "use strict";
  var meta = document.querySelector('meta[name="gtm-id"]');
  var id = meta && meta.content && meta.content.trim();
  if (!id) return;

  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({ "gtm.start": new Date().getTime(), event: "gtm.js" });

  var script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtm.js?id=" + encodeURIComponent(id);
  document.head.appendChild(script);
})();
