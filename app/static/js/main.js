/* ============================================================
   leandrofurtado.com.br, motion engine v3 (monocromático)
   Lenis · GSAP + ScrollTrigger + SplitText · WebGL GLSL próprio
   Performance: shader meia-resolução, grain estático, reveals
   só com transform/opacity (compositor-friendly).
   ============================================================ */
(() => {
  "use strict";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches ||
    new URLSearchParams(location.search).has("nomotion");
  const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const hasGSAP = typeof gsap !== "undefined";

  /* ---------- intro de marca (só no primeiríssimo acesso, nunca repete) ---------- */
  const brandIntro = document.querySelector(".brand-intro");
  const introActive = document.documentElement.classList.contains("intro");
  const INTRO_MS = 2650;  // cortina da intro começa a subir em 2.55s (CSS)
  if (brandIntro) {
    if (introActive) {
      try { localStorage.setItem("lf-intro", "1"); } catch (e) { /* modo privado */ }
      setTimeout(() => {
        brandIntro.remove();
        document.documentElement.classList.remove("intro");
      }, 3400);
    } else {
      brandIntro.remove();
    }
  }

  /* ---------- preloader ---------- */
  const preloader = document.querySelector(".preloader");
  let preloaderDone = Promise.resolve();
  // Espaço do aluno do Nodal (spec §17, adendo "nada de tela de
  // carregamento no espaço do aluno", fim da Tarefa 10): `base.html` já
  // nem renderiza `.preloader` nessas páginas, então `preloader` chega
  // `null` aqui na prática — este `if` é a SEGUNDA camada, mesmo padrão
  // de `data-tips` (linha ~215 abaixo): se algum dia alguém reintroduzir
  // o HTML do preloader sem lembrar da regra, o atributo ainda impede o
  // preloader de armar.
  if (document.body.dataset.preloader === "off") {
    if (preloader) preloader.remove();
  } else if (preloader && !reduced) {
    const count = preloader.querySelector(".pre-count");
    preloaderDone = new Promise(resolve => {
      const DUR = 850, START_DELAY = introActive ? INTRO_MS : 0;
      let finished = false, t0 = 0;
      const finish = () => {
        if (finished) return;
        finished = true;
        preloader.classList.add("done");
        setTimeout(() => { preloader.remove(); resolve(); }, 400);
      };
      const tick = now => {
        if (finished) return;
        const p = Math.min((now - t0) / DUR, 1);
        if (count) count.textContent = Math.round(p * 100);
        p < 1 ? requestAnimationFrame(tick) : finish();
      };
      setTimeout(() => {
        t0 = performance.now();
        requestAnimationFrame(tick);
      }, START_DELAY);
      // aba em segundo plano: rAF estrangulado não pode travar o site
      setTimeout(finish, START_DELAY + 2500);
    });
  } else if (preloader) {
    preloader.remove();
  }

  /* ---------- Lenis ---------- */
  let lenis = null;
  if (typeof Lenis !== "undefined" && !reduced) {
    lenis = new Lenis({ duration: 1.05, easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)) });
    const raf = time => { lenis.raf(time); requestAnimationFrame(raf); };
    requestAnimationFrame(raf);
  }

  if (hasGSAP) {
    gsap.registerPlugin(ScrollTrigger, SplitText);
    if (lenis) lenis.on("scroll", ScrollTrigger.update);
  }

  /* ---------- header + botão voltar-ao-topo ----------
     `.site-header` existe em toda página, Nodal incluso: o cabeçalho do
     produto (Tarefa 11) reaproveita a MESMA classe (regra do Leandro de
     18/08), então a animação de esconder/mostrar ao rolar já valia lá
     também, de graça — sem guard nenhum precisando ser mantido aqui.

     Rodada de refinamento 1 (item 1, veredito de 19/08): "header sempre
     fixo na rolagem — SÓ no Nodal (o portfólio não muda)". O portfólio
     continua escondendo o cabeçalho ao rolar para baixo (o `.hidden` logo
     abaixo); o Nodal passa a NUNCA escondê-lo — decidido no SERVIDOR, não
     aqui: `data-header-fixo="1"` no `<body>` (`_base_nodal.html`,
     `body_attrs`, todo o produto — catálogo público e área do aluno) é o
     gancho, mesmo padrão de `data-tips`/`data-preloader` alguns
     comentários acima. `.scrolled` (o fundo desfocado ao rolar) continua
     ligado nos dois — só o "some ao descer" é exclusivo do portfólio. */
  const header = document.querySelector(".site-header");
  const headerSempreFixo = document.body.dataset.headerFixo === "1";
  const topFab = document.querySelector(".top-fab");
  let lastY = 0;
  const onScroll = y => {
    header.classList.toggle("scrolled", y > 40);
    if (!headerSempreFixo) header.classList.toggle("hidden", y > 320 && y > lastY);
    if (topFab) topFab.classList.toggle("show", y > 500);
    lastY = y;
  };
  if (lenis) lenis.on("scroll", e => onScroll(e.scroll));
  else addEventListener("scroll", () => onScroll(scrollY), { passive: true });

  /* ---------- tema light/dark ---------- */
  const applyTheme = theme => {
    if (theme === "light") document.documentElement.dataset.theme = "light";
    else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("lf-theme", theme); } catch {}
    // o monograma 3D reage: material e luzes trocam para contrastar com o fundo
    dispatchEvent(new CustomEvent("lf:theme", { detail: theme }));
  };
  document.querySelectorAll(".theme-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      applyTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
    });
  });

  /* ---------- âncoras internas + voltar ao topo ----------
     Lenis mantém o scroll próprio: saltos nativos de âncora são
     sobrescritos no frame seguinte. Rolamos via lenis.scrollTo. */
  const smoothTo = target => {
    if (lenis) lenis.scrollTo(target, { duration: 1.1 });
    else if (typeof target === "number") window.scrollTo({ top: target, behavior: "smooth" });
    else target.scrollIntoView({ behavior: "smooth" });
  };
  document.querySelectorAll(".to-top").forEach(btn =>
    btn.addEventListener("click", () => smoothTo(0)));
  document.addEventListener("click", e => {
    const a = e.target.closest('a[href*="#"]');
    if (!a) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || !url.hash) return;
    const el = document.querySelector(url.hash);
    if (!el) return;
    e.preventDefault();
    history.pushState(null, "", url.hash);
    smoothTo(el);
  });

  /* ---------- lightbox do prêmio (Sobre): carrossel ----------
     Item novo (19/08): cada prêmio agora pode ter a própria galeria de
     fotos, então pode existir mais de um .award-gallery na página ao mesmo
     tempo. O carrossel (seta anterior/próxima) precisa ficar DENTRO da
     galeria em que o clique aconteceu — sem isso, "próxima" no último
     prêmio vazaria para a primeira foto de um prêmio diferente. */
  const lightbox = document.getElementById("lightbox");
  if (lightbox) {
    const img = lightbox.querySelector("img");
    const count = lightbox.querySelector(".lb-count");
    let gallery = [];
    let idx = 0;
    const goTo = i => {
      if (!gallery.length) return;
      idx = (i + gallery.length) % gallery.length;
      img.src = gallery[idx];
      if (count) count.textContent = `${idx + 1} / ${gallery.length}`;
    };
    document.querySelectorAll(".award-gallery").forEach(galEl => {
      const thumbs = [...galEl.querySelectorAll(".award-thumb")];
      const imgs = thumbs.map(t => t.dataset.img);
      thumbs.forEach((thumb, i) => thumb.addEventListener("click", () => {
        gallery = imgs;
        goTo(i);
        lightbox.showModal();
      }));
    });
    lightbox.querySelector(".lb-prev").addEventListener("click", () => goTo(idx - 1));
    lightbox.querySelector(".lb-next").addEventListener("click", () => goTo(idx + 1));
    lightbox.addEventListener("keydown", e => {
      if (e.key === "ArrowLeft") goTo(idx - 1);
      if (e.key === "ArrowRight") goTo(idx + 1);
    });
    lightbox.querySelector(".lightbox-close").addEventListener("click", () => lightbox.close());
    lightbox.addEventListener("click", e => { if (e.target === lightbox) lightbox.close(); });
  }

  /* ---------- modal de certificações (Sobre) ---------- */
  const certModal = document.getElementById("certModal");
  if (certModal) {
    const slot = name => certModal.querySelector(`[data-slot="${name}"]`);
    document.querySelectorAll(".cert-card").forEach(card => {
      card.addEventListener("click", () => {
        slot("title").textContent = card.dataset.title;
        slot("org").textContent = card.dataset.org + (card.dataset.year ? " ·︎ " + card.dataset.year : "");
        const codeWrap = certModal.querySelector('[data-slot-wrap="code"]');
        codeWrap.style.display = card.dataset.code ? "" : "none";
        slot("code").textContent = card.dataset.code;
        const link = slot("link"), nolink = slot("nolink");
        if (card.dataset.url) {
          link.href = card.dataset.url;
          link.hidden = false; nolink.hidden = true;
        } else {
          link.hidden = true; nolink.hidden = false;
        }
        certModal.showModal();
      });
    });
    certModal.querySelector(".cert-modal-close").addEventListener("click", () => certModal.close());
    certModal.addEventListener("click", e => { if (e.target === certModal) certModal.close(); });
  }

  /* ---------- edição inline do admin (Sobre) ---------- */
  const editModal = document.getElementById("editModal");
  if (editModal) {
    const fieldsEl = document.getElementById("profile-fields");
    const fields = fieldsEl ? JSON.parse(fieldsEl.textContent) : {};
    const textarea = document.getElementById("editField");
    let currentField = null;
    document.querySelectorAll(".edit-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        currentField = btn.dataset.edit;
        textarea.value = fields[currentField] || "";
        editModal.showModal();
      });
    });
    document.getElementById("editSave").addEventListener("click", async () => {
      if (!currentField) return;
      try {
        const res = await fetch("/admin/profile/inline", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ csrf: window.LF_CSRF, field: currentField, value: textarea.value }),
        });
        if ((await res.json()).ok) location.reload();
        else alert("Não foi possível salvar.");
      } catch { alert("Erro de conexão."); }
    });
    editModal.addEventListener("click", e => { if (e.target === editModal) editModal.close(); });
  }

  /* ---------- push de dicas de IA (retenção) ---------- */
  (() => {
    // gancho decidido no SERVIDOR (regra do Leandro, 18/08): o toast é
    // retenção do PORTFÓLIO, nunca aparece no Nodal — `data-tips="off"` só
    // existe no <body> quando app/templates/nodal/_base_nodal.html o
    // escreve (ver body_attrs em base.html). Não é pathname hardcoded aqui
    // de propósito: se um dia outro produto herdar o mesmo layout, o
    // servidor decide por ele também, sem tocar em main.js de novo.
    if (document.body.dataset.tips === "off") return;
    if (reduced) return;
    /* A vitrine /lab herda este main.js pelo base.html, mas o push de
       dicas de IA é feature da experiência do site (retenção do
       visitante comum), não do Lab de Demos: a home continua com ele
       (pedido do dono), a vitrine e as três demos saem cedo aqui, no
       mesmo estilo do guard de `reduced` acima. As demos (lab/_base_demo)
       nem carregam main.js, então body.dataset.page nunca chega a "lab"
       por lá; este guard cobre só a vitrine, que herda base.html. */
    if (document.body?.dataset.page === "lab") return;
    let off = false;
    try { off = sessionStorage.getItem("lf-tips-off") === "1"; } catch {}
    if (off) return;

    const isEN = document.documentElement.lang === "en";
    const TIPS = isEN ? [
      "<strong>Prompt like an art director:</strong> describe light, lens and composition, '85mm, hard side light, negative space' beats 'beautiful photo'.",
      "<strong>Midjourney:</strong> use <strong>--sref</strong> with a reference image to keep one visual style across a whole campaign.",
      "<strong>Claude</strong> can unfold one creative concept into 10 copy variations in seconds, great for headline exploration.",
      "<strong>Recraft.ai</strong> generates vector SVGs and icon sets with AI, perfect for identity systems.",
      "<strong>Photoshop Generative Fill</strong> extends key visuals to impossible formats (empena, DOOH, stories) in minutes.",
      "<strong>Runway / Kling</strong> turn static key visuals into motion for social, 5s loops sell an idea fast.",
      "Brand consistency with AI: fix a <strong>3-color palette</strong> and repeat it in every prompt.",
      "<strong>Magnific or Topaz</strong> upscale AI art for print without losing texture.",
      "<strong>ComfyUI</strong> makes image pipelines reproducible, treat prompts like versioned code.",
      "Cheap A/B: generate <strong>20 AI thumbnails</strong> of a concept before opening Photoshop.",
      "AI doesn't replace repertoire: feed prompts with <strong>real references</strong>, photographers, art movements, films.",
      "<strong>Figma AI</strong> speeds up wireframes; always refine hierarchy by hand afterwards.",
      "<strong>Agency workflow:</strong> use AI at the start (research, moodboards, territories) and at the end (adaptations, formats), keep the core idea human.",
      "<strong>Pitches:</strong> generate 3 visual routes with AI overnight and walk into the client meeting with living moodboards, not static references.",
      "<strong>Live marketing:</strong> AI mockups placed in real venue photos help clients approve brand activations before any physical build.",
      "<strong>Campaigns:</strong> train a consistent style (--sref / LoRA) and unfold one KV into OOH, social, DOOH and stage in hours, not weeks.",
      "<strong>Brand activation:</strong> real-time AI photo booths (face swap, style transfer) turn visitors into shareable branded content.",
      "<strong>Social listening + AI:</strong> summarize thousands of comments with Claude to find insights before the next campaign.",
      "<strong>Copy + art together:</strong> ask AI for 20 headline+visual pairs, then curate as a creative director, curation is the new craft.",
      "<strong>Media plans:</strong> AI drafts audience hypotheses and A/B matrices; test more angles with the same budget.",
      "<strong>Client presentations:</strong> AI-generated storyboards make film scripts tangible before production quotes.",
      "<strong>Post-campaign:</strong> feed results into AI to draft the learnings report, and start the next brief smarter.",
    ] : [
      "<strong>Faça prompt como diretor de arte:</strong> descreva luz, lente e composição, '85mm, luz lateral dura, espaço negativo' rende mais que 'foto bonita'.",
      "<strong>Midjourney:</strong> use <strong>--sref</strong> com imagem de referência para manter o mesmo estilo visual na campanha inteira.",
      "<strong>Claude</strong> desdobra um conceito criativo em 10 variações de copy em segundos, ótimo para explorar headlines.",
      "<strong>Recraft.ai</strong> gera SVGs e ícones vetoriais com IA, perfeito para sistemas de identidade.",
      "<strong>Generative Fill do Photoshop</strong> estende key visuals para formatos impossíveis (empena, DOOH, stories) em minutos.",
      "<strong>Runway / Kling</strong> transformam KV estático em motion para social, loops de 5s vendem a ideia rápido.",
      "Consistência de marca com IA: fixe uma <strong>paleta de 3 cores</strong> e repita em todos os prompts.",
      "<strong>Magnific ou Topaz</strong> fazem upscale de arte de IA para impressão sem perder textura.",
      "<strong>ComfyUI</strong> torna pipelines de imagem reproduzíveis, trate prompts como código versionado.",
      "Teste A/B barato: gere <strong>20 thumbnails com IA</strong> de um conceito antes de abrir o Photoshop.",
      "IA não substitui repertório: alimente os prompts com <strong>referências reais</strong>, fotógrafos, movimentos, filmes.",
      "<strong>Figma AI</strong> acelera wireframes; refine a hierarquia manualmente depois.",
      "<strong>Fluxo de agência:</strong> use IA no começo (pesquisa, moodboards, territórios) e no fim (adaptações, formatos), o miolo da ideia continua humano.",
      "<strong>Concorrências:</strong> gere 3 caminhos visuais com IA de um dia para o outro e chegue na reunião com moodboards vivos, não referências estáticas.",
      "<strong>Live marketing:</strong> mockups de IA aplicados em fotos reais do local fazem o cliente aprovar a ativação antes de qualquer construção física.",
      "<strong>Campanhas:</strong> treine um estilo consistente (--sref / LoRA) e desdobre um KV em OOH, social, DOOH e palco em horas, não semanas.",
      "<strong>Ativação de marca:</strong> cabines fotográficas com IA em tempo real (face swap, style transfer) transformam visitantes em conteúdo compartilhável.",
      "<strong>Social listening + IA:</strong> resuma milhares de comentários com o Claude e encontre insights antes da próxima campanha.",
      "<strong>Copy + arte juntos:</strong> peça à IA 20 pares de headline+visual e curadorie como diretor de criação, curadoria é o novo craft.",
      "<strong>Mídia:</strong> IA rascunha hipóteses de público e matrizes de A/B; teste mais ângulos com a mesma verba.",
      "<strong>Apresentações:</strong> storyboards gerados por IA tornam roteiros de filme tangíveis antes do orçamento de produção.",
      "<strong>Pós-campanha:</strong> jogue os resultados na IA para rascunhar o relatório de aprendizados, e comece o próximo briefing mais esperto.",
    ];

    const THUMB_UP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h3zm0 0 4-7a2 2 0 0 1 2 2v4h6a2 2 0 0 1 2 2.3l-1.3 7A2 2 0 0 1 17.7 20H7"/></svg>';
    const THUMB_DOWN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 14V3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-3zm0 0-4 7a2 2 0 0 1-2-2v-4H5a2 2 0 0 1-2-2.3l1.3-7A2 2 0 0 1 6.3 4H17"/></svg>';

    const toast = document.createElement("div");
    toast.className = "tip-toast";
    toast.setAttribute("role", "status");
    toast.innerHTML = `
      <div class="tip-toast-head">
        <span class="mono-label"><i>✳︎</i> <strong>${isEN ? "Leandro's AI tip" : "Dica de IA do Leandro"}</strong></span>
        <button class="tip-close" type="button" aria-label="fechar">✕︎</button>
      </div>
      <p></p>
      <div class="tip-votes">
        <button class="tip-vote" data-vote="up" type="button" aria-label="like">${THUMB_UP}<span>0</span></button>
        <button class="tip-vote" data-vote="down" type="button" aria-label="dislike">${THUMB_DOWN}<span>0</span></button>
      </div>`;
    document.body.appendChild(toast);
    const text = toast.querySelector("p");
    const voteBtns = toast.querySelectorAll(".tip-vote");

    // contagem de likes/dislikes por dica (persistida no backend)
    let allVotes = {};
    fetch("/tips/votes").then(r => r.json()).then(v => { allVotes = v || {}; }).catch(() => {});

    let order = TIPS.map((_, idx) => idx).sort(() => Math.random() - .5);
    let pos = 0, current = -1, hideTimer = null;

    const paintVotes = () => {
      const entry = allVotes[String(current)] || { up: 0, down: 0 };
      let hasVoted = false;
      try { hasVoted = !!localStorage.getItem("lf-tip-vote-" + current); } catch {}
      voteBtns.forEach(btn => {
        btn.querySelector("span").textContent = entry[btn.dataset.vote] || 0;
        btn.classList.toggle("voted", hasVoted);
      });
    };

    const show = () => {
      if (document.hidden) return;
      if (pos >= order.length) {  // reembaralha e continua, dicas nunca acabam
        order = TIPS.map((_, idx) => idx).sort(() => Math.random() - .5);
        pos = 0;
      }
      current = order[pos++];
      text.innerHTML = TIPS[current];
      paintVotes();
      toast.classList.add("show");
      hideTimer = setTimeout(() => toast.classList.remove("show"), 10_000);
    };
    // primeira dica rápida; depois cadência viva com intervalo randômico (12–22s)
    let loop = null;
    const schedule = () => {
      loop = setTimeout(() => {
        if (!toast.classList.contains("show")) show();
        schedule();
      }, 12_000 + Math.random() * 10_000);
    };
    setTimeout(() => { show(); schedule(); }, 4_500);

    voteBtns.forEach(btn => btn.addEventListener("click", async () => {
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => toast.classList.remove("show"), 5_000);
      try {
        const res = await fetch("/tips/vote", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tip: current, vote: btn.dataset.vote }),
        });
        const data = await res.json();
        if (data.ok) {
          allVotes[String(current)] = data.votes;
          try { localStorage.setItem("lf-tip-vote-" + current, btn.dataset.vote); } catch {}
          paintVotes();
        }
      } catch {}
    }));

    toast.querySelector(".tip-close").addEventListener("click", () => {
      toast.classList.remove("show");
      clearTimeout(hideTimer);
      clearTimeout(loop);
      try { sessionStorage.setItem("lf-tips-off", "1"); } catch {}
    });
  })();

  /* A visibilidade do aviso de consentimento é decidida no SERVIDOR
     (`mostrar_consentimento` em app/main.py: render()) — o bloco só existe no
     HTML quando ainda não há escolha registrada, e some sozinho na próxima
     página depois do POST. Nada de JavaScript aqui: as duas ações são botões
     de formulário comuns (ver base.html), e a entrada suave é CSS puro
     (@starting-style, em main.css). */

  /* ---------- relógio local com segundos e fuso (rodapé) ---------- */
  const clock = document.querySelector("[data-clock]");
  if (clock) {
    const tickClock = () => {
      /* Sem timeZone: o relógio passa a ser o de quem está lendo, no fuso do
         aparelho dela. Antes era fixo em São Paulo, o que fazia sentido quando
         o rodapé falava da minha cidade e deixou de fazer quando passou a
         falar da cidade do visitante. */
      clock.textContent = new Date().toLocaleTimeString(
        document.documentElement.lang || "pt-BR",
        { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "shortOffset" }
      );
    };
    tickClock();
    setInterval(tickClock, 1000);
  }

  /* Clicar em PT ou EN registra a vontade da pessoa. A partir daí ela vale
     mais que o país do IP, e o redirecionamento automático não acontece mais. */
  document.querySelectorAll(".lang-toggle, .mm-lang, .wip-lang a").forEach(el => {
    el.addEventListener("click", () => {
      const paraIngles = (el.getAttribute("href") || "").indexOf("/en") === 0;
      document.cookie = "lf_lang=" + (paraIngles ? "en" : "pt") +
        ";path=/;max-age=31536000;samesite=lax" +
        (location.protocol === "https:" ? ";secure" : "");
    });
  });

  /* ---------- vida: texto que rola no hover ---------- */
  /* `.wc-title` e não `.work-card-row span:first-child`: o seletor solto pegava
     qualquer span que fosse o primeiro filho de qualquer coisa dentro da linha,
     e passou a duplicar o endereço dentro da etiqueta SITE. Aqui o alvo é o
     título, que é o que sempre foi a intenção. */
  document.querySelectorAll(
    ".nav-link, .btn-underline, .footer-grid a, .mm-lang, .wc-title"
  ).forEach(el => {
    if (el.children.length || !el.textContent.trim()) return;
    const text = el.textContent.trim();
    el.innerHTML = `<span class="roll"><span>${text}</span><span aria-hidden="true">${text}</span></span>`;
  });

  /* ---------- vida: botões magnéticos ---------- */
  if (fine && !reduced) {
    document.querySelectorAll(".cta-pill, .theme-fab, .top-fab").forEach(el => {
      el.addEventListener("pointermove", e => {
        const r = el.getBoundingClientRect();
        const dx = (e.clientX - r.left - r.width / 2) / r.width;
        const dy = (e.clientY - r.top - r.height / 2) / r.height;
        el.style.translate = `${dx * 8}px ${dy * 6}px`;
      });
      el.addEventListener("pointerleave", () => { el.style.translate = ""; });
    });
  }

  /* ---------- menu mobile ---------- */
  const menuBtn = document.querySelector(".menu-btn");
  const mobileMenu = document.querySelector(".mobile-menu");
  if (menuBtn && mobileMenu) {
    let closeTimer = null;
    const setMenu = open => {
      clearTimeout(closeTimer);
      if (open) {
        mobileMenu.classList.remove("closing");
        mobileMenu.classList.add("open");
      } else if (mobileMenu.classList.contains("open")) {
        // fechamento espelhado: itens saem em cascata reversa antes da cortina
        mobileMenu.classList.add("closing");
        mobileMenu.classList.remove("open");
        closeTimer = setTimeout(() => mobileMenu.classList.remove("closing"), 950);
      }
      menuBtn.setAttribute("aria-expanded", String(open));
      mobileMenu.setAttribute("aria-hidden", String(!open));
      if (lenis) open ? lenis.stop() : lenis.start();
      document.body.style.overflow = open ? "hidden" : "";
    };
    menuBtn.addEventListener("click", () => setMenu(true));
    mobileMenu.querySelector(".mm-close")?.addEventListener("click", () => setMenu(false));
    // lupa dentro do menu: fecha o menu (a busca abre por cima via módulo de busca)
    mobileMenu.querySelector(".mm-search")?.addEventListener("click", () => setMenu(false));
    mobileMenu.querySelectorAll(".mm-nav a, .mm-head .brand, .mm-cta").forEach(a =>
      a.addEventListener("click", () => setMenu(false)));
    addEventListener("keydown", e => { if (e.key === "Escape") setMenu(false); });
  }

  /* ---------- contato: animação de envio no próprio box ---------- */
  const ctForm = document.querySelector("[data-ct-form]");
  const ctSending = document.querySelector("[data-ct-sending]");
  if (ctForm && ctSending) {
    const stepEl = ctSending.querySelector("[data-cts-step]");
    const thanksEl = ctSending.querySelector("[data-cts-thanks]");
    const barEl = ctSending.querySelector(".cts-bar span");
    let steps = [];
    try { steps = JSON.parse(ctForm.dataset.steps || "[]"); } catch (e) { steps = []; }
    const doneText = ctForm.dataset.done || "";
    let sending = false;

    ctForm.addEventListener("submit", async e => {
      if (sending) { e.preventDefault(); return; }
      if (!ctForm.reportValidity()) return;   // deixa o browser apontar o campo faltante
      e.preventDefault();
      sending = true;

      ctForm.hidden = true;
      ctSending.hidden = false;
      ctSending.classList.add("on");
      barEl.style.width = "0%";

      // 3 segundos reais: a mensagem sai de fato enquanto a animação roda
      const started = performance.now();
      const TOTAL = 3000;
      let stepIdx = 0;
      const stepTimer = setInterval(() => {
        stepIdx = Math.min(stepIdx + 1, steps.length - 1);
        if (steps[stepIdx]) stepEl.textContent = steps[stepIdx];
      }, TOTAL / Math.max(steps.length, 1));
      const barTimer = setInterval(() => {
        const p = Math.min((performance.now() - started) / TOTAL, 1) * 100;
        barEl.style.width = p.toFixed(1) + "%";
      }, 60);

      let ok = true;
      try {
        const res = await fetch(ctForm.action, {
          method: "POST",
          body: new FormData(ctForm),
          headers: { "X-Requested-With": "fetch" },
          redirect: "follow",
        });
        ok = res.ok && !res.url.includes("consent=1") && !res.url.includes("erro=1");
      } catch (err) {
        ok = false;
      }

      // espera o tempo cheio mesmo se o servidor responder antes
      const rest = Math.max(0, TOTAL - (performance.now() - started));
      setTimeout(() => {
        clearInterval(stepTimer);
        clearInterval(barTimer);
        barEl.style.width = "100%";
        ctSending.classList.add("done");
        stepEl.textContent = ok ? doneText : (steps[0] || "");
        thanksEl.hidden = !ok;
        setTimeout(() => {
          const url = new URL(ctForm.action, location.href);
          location.href = url.pathname.replace("/contact", "/contato") + (ok ? "?sent=1" : "?erro=1");
        }, 5000);   // tempo de ler a confirmação antes de a página recarregar
      }, rest);
    });
  }

  /* ---------- download do currículo com modal da marca ---------- */
  const dlModal = document.getElementById("dlModal");
  if (dlModal) {
    const bar = dlModal.querySelector(".dlm-bar span");
    const pct = dlModal.querySelector("[data-dlm-pct]");
    const fmtEl = dlModal.querySelector("[data-dlm-fmt]");
    let busy = false;

    document.querySelectorAll("[data-dl]").forEach(link => {
      link.addEventListener("click", async e => {
        if (busy) return;
        e.preventDefault();
        busy = true;
        fmtEl.textContent = link.dataset.dl;
        bar.style.width = "0%";
        pct.textContent = "0";
        dlModal.classList.remove("done");
        dlModal.showModal();

        // progresso real quando o servidor informa o tamanho; senão, ritmo próprio
        let shown = 0;
        const paint = v => {
          shown = Math.max(shown, Math.min(v, 100));
          bar.style.width = shown + "%";
          pct.textContent = Math.round(shown);
        };
        const tick = setInterval(() => paint(shown + (shown < 80 ? 6 : 1.5)), 120);

        try {
          const res = await fetch(link.href);
          if (!res.ok) throw new Error("download");
          const blob = await res.blob();
          clearInterval(tick);
          paint(100);
          dlModal.classList.add("done");

          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = (res.headers.get("Content-Disposition") || "")
            .match(/filename="?([^"]+)"?/)?.[1] || `curriculo.${link.dataset.dl.toLowerCase()}`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 4000);
          setTimeout(() => { dlModal.close(); busy = false; }, 900);
        } catch (err) {
          clearInterval(tick);
          dlModal.close();
          busy = false;
          location.href = link.href;  // sem fetch disponível, baixa direto
        }
      });
    });
    dlModal.addEventListener("click", e => { if (e.target === dlModal && !busy) dlModal.close(); });
  }

  /* ---------- dropdowns de filtro do portfólio (categoria, ano, cliente) ----
     São três, e cada um precisa abrir. Antes isso era um querySelector no
     singular: só o primeiro da página respondia ao clique, e os outros dois
     eram botões que não faziam nada. Abrir um fecha os demais — dois menus
     sobrepostos disputando a mesma área é ruído, não escolha. */
  const initPfSelect = () => {
  const grupo = [...document.querySelectorAll("[data-pf-select]")];
  if (!grupo.length) return;

  /* Cada menu é levado para o final do body na entrada. Não é capricho: o
     .pf-filters carrega um transform deixado pela animação de entrada, e um
     ancestral com transform faz `position: fixed` passar a se posicionar por
     ele em vez de pela janela. O menu ia parar 400px abaixo da tela, calculado
     certo e desenhado no lugar errado. Fora da subárvore, nenhum transform
     futuro em ancestral volta a quebrá-lo. */
  const MARGEM = 12;
  grupo.forEach((sel, i) => {
    const menu = sel.querySelector(".pf-select-menu");
    const btn = sel.querySelector(".pf-select-btn");
    if (!menu || !btn) return;
    menu.id = menu.id || `pf-menu-${i}`;
    btn.setAttribute("aria-controls", menu.id);
    document.body.appendChild(menu);
    sel.menuFora = menu;
  });

  /* Ancorado no botão; se não sobra altura embaixo, abre para cima. Nunca passa
     das bordas laterais da janela. */
  const posicionar = sel => {
    const btn = sel.querySelector(".pf-select-btn");
    const menu = sel.menuFora;
    if (!btn || !menu) return;
    const r = btn.getBoundingClientRect();
    /* mede o conteúdo antes de decidir a largura: o botão de cliente tem 210px
       e "Associação Comercial do Paraná" quebrava em três linhas dentro dele.
       Os 20px extras são a barra de rolagem, que com muitos clientes come da
       largura útil exatamente o suficiente para o nome mais longo quebrar. */
    menu.style.width = "max-content";
    const natural = menu.getBoundingClientRect().width + 20;
    const largura = Math.min(Math.max(r.width, natural), 400, innerWidth - MARGEM * 2);
    const abaixo = innerHeight - r.bottom - MARGEM;
    const acima = r.top - MARGEM;
    const paraCima = abaixo < 180 && acima > abaixo;
    menu.style.width = largura + "px";
    /* ancora pela borda mais próxima: um seletor na direita da tela abre para a
       esquerda, senão o menu mais largo que o botão empurraria para fora */
    const bruto = r.left + r.width / 2 > innerWidth / 2 ? r.right - largura : r.left;
    menu.style.left = Math.round(
      Math.min(Math.max(bruto, MARGEM), innerWidth - largura - MARGEM)) + "px";
    menu.style.maxHeight = Math.round(Math.max(120, paraCima ? acima : abaixo)) + "px";
    if (paraCima) {
      menu.style.top = "auto";
      menu.style.bottom = Math.round(innerHeight - r.top + 8) + "px";
    } else {
      menu.style.bottom = "auto";
      menu.style.top = Math.round(r.bottom + 8) + "px";
    }
  };

  const fechar = exceto => grupo.forEach(s => {
    if (s === exceto) return;
    s.classList.remove("open");
    s.menuFora?.classList.remove("aberto");
    s.querySelector(".pf-select-btn")?.setAttribute("aria-expanded", "false");
  });
  const aberto = () => grupo.find(s => s.classList.contains("open"));

  grupo.forEach(sel => {
    const btn = sel.querySelector(".pf-select-btn");
    if (!btn) return;
    const setOpen = abre => {
      if (abre) { fechar(sel); posicionar(sel); }
      sel.classList.toggle("open", abre);
      sel.menuFora?.classList.toggle("aberto", abre);
      btn.setAttribute("aria-expanded", String(abre));
    };
    btn.addEventListener("click", e => {
      e.stopPropagation();
      setOpen(!sel.classList.contains("open"));
    });
  });

  /* o menu não é mais descendente do seletor: o clique de fora precisa
     perguntar pelos dois */
  document.addEventListener("click", e => {
    if (!grupo.some(s => s.contains(e.target) || s.menuFora?.contains(e.target)))
      fechar(null);
  });
  addEventListener("keydown", e => { if (e.key === "Escape") fechar(null); });
  /* menu fixo não acompanha a rolagem da página: em vez de deixá-lo flutuando
     longe do botão, fecha. É o comportamento de qualquer seletor nativo. */
  addEventListener("scroll", () => { if (aberto()) fechar(null); }, { passive: true });
  addEventListener("resize", () => { const a = aberto(); if (a) posicionar(a); });
  };
  initPfSelect();

  /* ---------- carrosséis arrastáveis (marcas na hero mobile) ----------
     No toque o scroll nativo já resolve; aqui só somamos o arrasto com o mouse
     e evitamos que o arrasto vire clique no link. */
  /* ---------- marcas & clientes: uma linha só, sempre ----------

     Quantas marcas cabem numa linha depende da largura da tela, não de um
     número fixo: em 1920 cabem mais que em 1280. Então em vez de decidir por
     contagem, medimos — se a fila é mais larga que a janela, ela vira carrossel
     contínuo; se cabe, fica parada e distribuída. Nos dois casos, uma linha.

     O laço precisa da fila duplicada: a animação anda metade da largura e
     recomeça, e a segunda metade cobre o vão. As cópias são marcadas como
     decorativas para leitor de tela não ler a lista duas vezes. */
  const vitrine = document.querySelector("[data-marcas]");
  if (vitrine) {
    const fila = vitrine.querySelector("[data-marcas-fila]");
    const originais = [...fila.children];
    const VELOCIDADE = 55;   /* px por segundo: rápido demais vira ruído */

    const medir = () => {
      fila.classList.remove("rolando");
      fila.style.removeProperty("--dur");
      fila.style.removeProperty("--meia-folga");
      [...fila.children].forEach(el => { if (el.dataset.copia) el.remove(); });

      /* a comparação tem que acontecer com a fila no estado solto */
      if (fila.scrollWidth <= vitrine.clientWidth + 1) return;

      const largura = fila.scrollWidth;
      const folga = parseFloat(getComputedStyle(fila).columnGap) || 0;
      originais.forEach(el => {
        const c = el.cloneNode(true);
        c.dataset.copia = "1";
        c.setAttribute("aria-hidden", "true");
        c.setAttribute("tabindex", "-1");
        fila.appendChild(c);
      });
      /* meia folga a menos no fim do ciclo: sem isso aparece um buraco de um
         gap entre a última cópia e o reinício */
      fila.style.setProperty("--meia-folga", (folga / 2) + "px");
      fila.style.setProperty("--dur", (largura / VELOCIDADE).toFixed(1) + "s");
      fila.classList.add("rolando");
    };

    medir();
    addEventListener("resize", () => { clearTimeout(vitrine._t); vitrine._t = setTimeout(medir, 180); });
    /* imagem e fonte chegam depois do primeiro cálculo e mudam a largura */
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(medir);
    vitrine.querySelectorAll("img").forEach(i => {
      if (!i.complete) i.addEventListener("load", () => { clearTimeout(vitrine._t); vitrine._t = setTimeout(medir, 60); });
    });
  }

  /* Linha única, sempre.

     A regra é "esta frase nunca quebra". Só com CSS isso não fecha: o nome do
     cliente varia de "WAP" a "Hospital Marcelino Champagnat", e um clamp que
     serve para um corta o outro com reticências. Então medimos e encolhemos a
     fonte até caber, com piso de 9px — abaixo disso não é mais leitura. */
  document.querySelectorAll("[data-uma-linha]").forEach(el => {
    const caber = () => {
      /* zera antes de medir: o tamanho de partida é o do CSS na largura atual,
         não o que ficou guardado da largura anterior */
      el.style.fontSize = "";
      let tam = parseFloat(getComputedStyle(el).fontSize);
      while (el.scrollWidth > el.clientWidth + 1 && tam > 9) {
        tam -= 0.5;
        el.style.fontSize = tam + "px";
      }
    };
    caber();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(caber);
    let t;
    addEventListener("resize", () => { clearTimeout(t); t = setTimeout(caber, 140); });
  });

  /* Player do aparelho.

     O <video> nativo com `controls` traz a barra do navegador, que muda de
     desenho em cada um e cobre a tela inteira num vídeo vertical de 282px.
     Aqui os controles são do site: play/pause, posição e som, na mesma
     tipografia e no mesmo cinza do resto.

     Começa mudo e em laço porque é a única forma de tocar sem gesto do
     visitante. O botão de som é o gesto: ao ligar, o volume sobe do zero. */
  document.querySelectorAll("[data-fone]").forEach(caixa => {
    const v = caixa.querySelector("[data-fone-video]");
    if (!v) return;
    const trilha = caixa.querySelector("[data-fone-seek]");
    const feito = caixa.querySelector("[data-fone-progresso]");
    const relogio = caixa.querySelector("[data-fone-relogio]");
    const btMute = caixa.querySelector("[data-fone-mute]");
    const vol = caixa.querySelector("[data-fone-vol]");

    const mmss = s => {
      if (!isFinite(s)) return "0:00";
      const m = Math.floor(s / 60), r = Math.floor(s % 60);
      return m + ":" + String(r).padStart(2, "0");
    };
    const pintarEstado = () => {
      caixa.classList.toggle("pausado", v.paused);
      caixa.querySelectorAll("[data-fone-toggle]").forEach(b => {
        b.setAttribute("aria-label", v.paused ? "Reproduzir" : "Pausar");
      });
    };
    const pintarSom = () => {
      const ligado = !v.muted && v.volume > 0;
      caixa.classList.toggle("com-som", ligado);
      if (btMute) {
        btMute.setAttribute("aria-pressed", String(!ligado));
        btMute.setAttribute("aria-label", ligado ? "Desligar o som" : "Ligar o som");
      }
    };

    /* `escolha` guarda o que o visitante mandou fazer. Sem isto, o observador
       de visibilidade e o clique brigavam: dar play num vídeo que o observador
       tinha pausado não pegava, e um vídeo pausado de propósito voltava a tocar
       sozinho ao rolar. Quem decide é sempre o visitante. */
    let escolha = null;
    caixa.querySelectorAll("[data-fone-toggle]").forEach(b => {
      b.addEventListener("click", e => {
        e.preventDefault();
        if (v.paused) { escolha = "tocar"; v.play().catch(() => {}); }
        else { escolha = "pausar"; v.pause(); }
      });
    });
    v.addEventListener("play", pintarEstado);
    v.addEventListener("pause", pintarEstado);

    v.addEventListener("timeupdate", () => {
      const p = v.duration ? (v.currentTime / v.duration) * 100 : 0;
      if (feito) feito.style.width = p + "%";
      if (trilha) trilha.setAttribute("aria-valuenow", Math.round(p));
      if (relogio) relogio.textContent = mmss(v.currentTime);
    });

    /* buscar arrastando: pointer events cobrem mouse, toque e caneta de uma vez */
    if (trilha) {
      const irPara = clientX => {
        const b = trilha.getBoundingClientRect();
        const f = Math.min(1, Math.max(0, (clientX - b.left) / b.width));
        if (v.duration) v.currentTime = f * v.duration;
      };
      let arrastando = false;
      trilha.addEventListener("pointerdown", e => {
        arrastando = true; trilha.setPointerCapture(e.pointerId); irPara(e.clientX);
      });
      trilha.addEventListener("pointermove", e => { if (arrastando) irPara(e.clientX); });
      const solta = () => { arrastando = false; };
      trilha.addEventListener("pointerup", solta);
      trilha.addEventListener("pointercancel", solta);
      trilha.addEventListener("keydown", e => {
        const passo = e.shiftKey ? 10 : 5;
        if (e.key === "ArrowRight") { v.currentTime = Math.min(v.duration, v.currentTime + passo); e.preventDefault(); }
        if (e.key === "ArrowLeft") { v.currentTime = Math.max(0, v.currentTime - passo); e.preventDefault(); }
      });
    }

    if (btMute) {
      btMute.addEventListener("click", () => {
        if (v.muted || v.volume === 0) {
          v.muted = false;
          if (v.volume === 0) v.volume = .7;
        } else {
          v.muted = true;
        }
        if (vol) vol.value = v.muted ? 0 : v.volume;
        pintarSom();
      });
    }
    if (vol) {
      vol.addEventListener("input", () => {
        v.volume = +vol.value;
        v.muted = +vol.value === 0;
        pintarSom();
      });
    }

    /* fora de vista, para de tocar: vídeo rodando escondido gasta bateria e
       banda de quem está lendo outra parte da página */
    if ("IntersectionObserver" in window) {
      let pausadoPorEstar = false;
      new IntersectionObserver(entradas => {
        entradas.forEach(en => {
          if (en.isIntersecting) {
            if (pausadoPorEstar && escolha !== "pausar") { v.play().catch(() => {}); }
            pausadoPorEstar = false;
          } else if (!v.paused) {
            v.pause();
            pausadoPorEstar = true;
          }
        });
      }, { threshold: .25 }).observe(caixa);
    }

    pintarEstado();
    pintarSom();
  });

  document.querySelectorAll("[data-drag-scroll]").forEach(strip => {
    let down = false, startX = 0, startLeft = 0, moved = 0;
    strip.addEventListener("pointerdown", e => {
      if (e.pointerType === "touch") return;
      down = true; moved = 0;
      startX = e.clientX;
      startLeft = strip.scrollLeft;
    });
    strip.addEventListener("pointermove", e => {
      if (!down) return;
      const dx = e.clientX - startX;
      moved = Math.abs(dx);
      if (moved > 4) strip.classList.add("dragging");
      strip.scrollLeft = startLeft - dx;
    });
    const release = () => {
      down = false;
      setTimeout(() => strip.classList.remove("dragging"), 0);
    };
    strip.addEventListener("pointerup", release);
    strip.addEventListener("pointerleave", release);
    strip.addEventListener("click", e => { if (moved > 4) e.preventDefault(); }, true);
  });

  /* ---------- trilho de logos: arrastar para pausar (item 6, 19/08) ----------
     O trilho (.trilho-anda, ex.: marcas na home e em Sobre) já pausava no
     hover via CSS puro (:hover/:focus-within seguravam a animação). O pedido
     do Leandro foi ir além: dá para AGARRAR e arrastar a esteira com o
     mouse, e ela solta suave de onde ficou, sem voltar num pulo.

     Isso não dá pra fazer só com a animação CSS (@keyframes anda de um ponto
     fixo ao outro; pausar e retomar não guarda "onde parei" se o usuário
     mexeu a posição). Por isso, com JS ativo, a posição passa a ser
     calculada aqui — mesma velocidade de antes (a mesma duração --dur que o
     servidor já calculava por número de marcas), só que quadro a quadro, o
     que também é o que permite o arrasto: a posição é só uma variável.

     Sem JS, ou com prefers-reduced-motion, nada disto roda — o CSS sozinho
     já cobre os dois casos (a animação toca normal, ou nem existe e o
     trilho vira scroll nativo, ver @media reduce em main.css). */
  if (!reduced) {
    document.querySelectorAll(".trilho-anda").forEach(rail => {
      const fila = rail.querySelector(".trilho-fila");
      if (!fila) return;
      const dur = parseFloat(getComputedStyle(rail).getPropertyValue("--dur")) || 40;
      fila.style.animation = "none";
      rail.style.touchAction = "pan-y";

      let metade = fila.scrollWidth / 2;
      const medir = () => { metade = fila.scrollWidth / 2; };
      addEventListener("resize", medir);

      let x = 0;
      const vel = () => metade / dur; // px/s, no mesmo ritmo que a animação CSS tinha
      let parado = false;             // hover/foco pausa, igual a versão CSS já fazia
      let arrastando = false, moveu = 0, startX = 0, startPosX = 0, ponteiro = null, lastT = null;

      const aplicar = () => {
        if (metade > 0) x = ((x % metade) + metade) % metade;
        fila.style.transform = `translateX(${-x}px)`;
      };

      rail.addEventListener("pointerenter", () => { parado = true; });
      rail.addEventListener("pointerleave", () => { parado = false; });
      rail.addEventListener("focusin", () => { parado = true; });
      rail.addEventListener("focusout", () => { parado = false; });

      rail.addEventListener("pointerdown", e => {
        if (e.pointerType === "mouse" && e.button !== 0) return;
        arrastando = true; moveu = 0;
        startX = e.clientX; startPosX = x; ponteiro = e.pointerId;
        // a captura do ponteiro NÃO acontece aqui: com ela ativa desde o
        // pressionar, o navegador re-endereça o click para o trilho e o
        // link do logo nunca o recebe (o bug do clique morto). Ela entra
        // só quando o arrasto de fato começa, no pointermove.
      });
      rail.addEventListener("pointermove", e => {
        if (!arrastando) return;
        const dx = e.clientX - startX;
        moveu = Math.max(moveu, Math.abs(dx));
        if (moveu > 4 && !rail.classList.contains("trilho-arrastando")) {
          // agora é um arrasto de verdade: captura o ponteiro (o clique já
          // não vai acontecer — e será suprimido pelo guard de moveu > 4)
          try { rail.setPointerCapture(ponteiro); } catch (err) { /* ignora */ }
          rail.classList.add("trilho-arrastando");
        }
        x = startPosX - dx;
        aplicar();
      });
      const soltar = () => {
        if (!arrastando) return;
        arrastando = false;
        rail.classList.remove("trilho-arrastando");
        if (ponteiro != null) { try { rail.releasePointerCapture(ponteiro); } catch (err) { /* ignora */ } }
      };
      rail.addEventListener("pointerup", soltar);
      rail.addEventListener("pointercancel", soltar);
      // um arrasto não deveria abrir o link do logo por baixo
      rail.addEventListener("click", e => { if (moveu > 4) e.preventDefault(); }, true);

      const passo = t => {
        if (lastT == null) lastT = t;
        const dt = (t - lastT) / 1000;
        lastT = t;
        if (!arrastando && !parado) { x += vel() * dt; aplicar(); }
        requestAnimationFrame(passo);
      };
      requestAnimationFrame(passo);
    });
  }

  /* ---------- busca full screen (texto + voz + imagem) ---------- */
  const searchOverlay = document.querySelector(".search-overlay");
  const searchBtn = document.querySelector(".search-btn");
  /* Busca PRÓPRIA (Tarefa 11, rodada 1 — hoje só o Nodal): mesmo botão e
     mesmo overlay do site, mas o `<form method="get">` já semeado pelo
     servidor aponta para a busca do PRÓPRIO produto (/nodal/situacoes) —
     nunca para `/api/search`, que só indexa o portfólio (cases, páginas,
     perfil, LinkedIn) e devolveria conteúdo errado dentro do produto pago.
     Este ramo só abre/fecha o overlay; nada de fetch, voz ou imagem. */
  if (searchOverlay && searchBtn && searchOverlay.dataset.buscaPropria) {
    let closeTimer = null;
    const soInput = searchOverlay.querySelector(".so-input");
    const setSearch = open => {
      clearTimeout(closeTimer);
      if (open) {
        searchOverlay.classList.remove("closing");
        searchOverlay.classList.add("open");
        if (soInput) setTimeout(() => soInput.focus(), 380);
      } else if (searchOverlay.classList.contains("open")) {
        searchOverlay.classList.add("closing");
        searchOverlay.classList.remove("open");
        closeTimer = setTimeout(() => searchOverlay.classList.remove("closing"), 900);
      } else {
        return;
      }
      searchBtn.setAttribute("aria-expanded", String(open));
      searchOverlay.setAttribute("aria-hidden", String(!open));
      if (lenis) open ? lenis.stop() : lenis.start();
      document.body.style.overflow = open ? "hidden" : "";
    };
    searchBtn.addEventListener("click", () => setSearch(true));
    document.querySelector(".mm-search")?.addEventListener("click", () => setSearch(true));
    searchOverlay.querySelector(".so-close")?.addEventListener("click", () => setSearch(false));
    searchOverlay.querySelector(".so-head .brand")?.addEventListener("click", () => setSearch(false));
    addEventListener("keydown", e => { if (e.key === "Escape") setSearch(false); });
  } else if (searchOverlay && searchBtn) {
    const d = searchOverlay.dataset;
    const soInput = searchOverlay.querySelector(".so-input");
    const soResults = searchOverlay.querySelector(".so-results");
    const soStatus = searchOverlay.querySelector(".so-status span");
    const soMic = searchOverlay.querySelector(".so-mic");
    const soImg = searchOverlay.querySelector(".so-img");
    const soFile = searchOverlay.querySelector(".so-file");
    const soForm = searchOverlay.querySelector(".so-bar");
    const soCount = searchOverlay.querySelector("[data-so-count]");
    let soTimer = null, soAbort = null, soSeq = 0, soCloseTimer = null;

    const setStatus = msg => { soStatus.textContent = msg || d.tHint; };
    const esc = s => String(s).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const highlight = (text, terms) => {
      let out = esc(text);
      terms.forEach(t => {
        if (t.length < 2) return;
        const safe = t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        out = out.replace(new RegExp(`(${safe})(?![^<]*>)`, "ig"), "<mark>$1</mark>");
      });
      return out;
    };
    const setCount = n => {
      if (!soCount) return;
      soCount.hidden = n === null;
      if (n !== null) {
        soCount.innerHTML = `${n} <em>${n === 1 ? d.tResult : d.tResults}</em>`;
      }
    };
    const renderGroups = (groups, q) => {
      const total = groups.reduce((sum, g) => sum + g.items.length, 0);
      setCount(total);
      if (!groups.length) {
        soResults.innerHTML = `<p class="so-empty">${d.tNoresults} “${esc(q)}”.</p>`;
        return;
      }
      const terms = q.split(/[\s,]+/).filter(Boolean);
      soResults.innerHTML = groups.map(g => `
        <section class="so-group">
          <header class="so-group-label mono-label"><span>✳︎ ${esc(g.label)}</span><span>${g.items.length}</span></header>
          ${g.items.map(it => `
            <a class="so-item" href="${esc(it.url)}"${it.external ? ' target="_blank" rel="noopener"' : ""}>
              ${it.thumb ? `<img class="so-thumb" src="${esc(it.thumb)}" alt="" loading="lazy">` : ""}
              <span class="so-item-txt">
                <span class="so-item-t">${highlight(it.title, terms)}</span>
                ${it.sub ? `<span class="so-item-s">${esc(it.sub)}</span>` : ""}
              </span>
              <span class="so-item-arrow">${it.external ? "↗︎" : "→︎"}</span>
            </a>`).join("")}
        </section>`).join("");
    };
    const doSearch = async q => {
      q = q.trim();
      if (q.length < 2) { soResults.innerHTML = ""; setStatus(); setCount(null); return; }
      if (soAbort) soAbort.abort();
      soAbort = new AbortController();
      const seq = ++soSeq;
      try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&lang=${d.lang}`, { signal: soAbort.signal });
        const data = await r.json();
        if (seq !== soSeq) return;
        renderGroups(data.groups || [], q);
      } catch (e) { /* requisição abortada ou offline */ }
    };
    soInput.addEventListener("input", () => {
      clearTimeout(soTimer);
      soTimer = setTimeout(() => doSearch(soInput.value), 220);
    });
    soForm.addEventListener("submit", e => {
      e.preventDefault();
      clearTimeout(soTimer);
      doSearch(soInput.value);
    });

    /* ---------- voz: modal de captação, onda real e transcrição ao vivo ----------

       Duas coisas rodam juntas e são independentes: o reconhecimento de fala
       (Web Speech API), que devolve texto, e um analisador de áudio ligado ao
       microfone, que só mede volume para desenhar a onda. A onda existe porque
       o reconhecimento demora a devolver a primeira palavra — sem ela, os
       primeiros segundos parecem uma tela travada.

       O fluxo do microfone é sempre encerrado ao fechar. Deixar a captura viva
       depois que a pessoa saiu manteria o ponto vermelho do navegador aceso, e
       isso é quebra de confiança, não bug de layout. */
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voz = document.querySelector("[data-voz]");
    const vozTitulo = voz && voz.querySelector("[data-voz-titulo]");
    const vozSub = voz && voz.querySelector("[data-voz-sub]");
    const vozFinal = voz && voz.querySelector(".voz-final");
    const vozParcial = voz && voz.querySelector(".voz-parcial");
    const vozUsar = voz && voz.querySelector("[data-voz-usar]");
    const vozDeNovo = voz && voz.querySelector("[data-voz-de-novo]");
    const barras = voz ? [...voz.querySelectorAll("[data-voz-onda] i")] : [];

    let rec = null, ouvindo = false, texto = "", fluxo = null, ctx = null, raf = 0;

    const pararOnda = () => {
      cancelAnimationFrame(raf); raf = 0;
      if (fluxo) { fluxo.getTracks().forEach(t => t.stop()); fluxo = null; }
      if (ctx) { ctx.close().catch(() => {}); ctx = null; }
      barras.forEach(b => b.style.transform = "");
    };

    const stopVoice = () => {
      if (rec && ouvindo) { try { rec.stop(); } catch (e) { /* já parou */ } }
      pararOnda();
    };

    const fecharVoz = () => {
      stopVoice();
      if (voz) { voz.hidden = true; voz.classList.remove("on"); }
      soMic.classList.remove("listening");
      soMic.setAttribute("aria-pressed", "false");
    };

    /* barras que respondem ao volume real: cada uma lê uma faixa do espectro */
    async function ligarOnda() {
      try {
        fluxo = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        return false;   // negado ou sem microfone: o texto ainda pode funcionar
      }
      try {
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        const fonte = ctx.createMediaStreamSource(fluxo);
        const an = ctx.createAnalyser();
        an.fftSize = 128; an.smoothingTimeConstant = .75;
        fonte.connect(an);
        const dados = new Uint8Array(an.frequencyBinCount);
        const passo = Math.max(1, Math.floor(dados.length / (barras.length || 1)));
        (function desenhar() {
          an.getByteFrequencyData(dados);
          barras.forEach((b, i) => {
            const v = dados[i * passo] / 255;
            b.style.transform = "scaleY(" + (0.12 + v * 1.9).toFixed(3) + ")";
          });
          raf = requestAnimationFrame(desenhar);
        })();
      } catch (e) { /* sem AudioContext a onda fica parada, o resto funciona */ }
      return true;
    }

    function pintar() {
      if (vozFinal) vozFinal.textContent = texto;
      if (vozUsar) vozUsar.disabled = !texto.trim();
    }

    async function abrirVoz() {
      if (!SR) { setStatus(d.tVoiceoff); return; }
      texto = "";
      voz.hidden = false;
      /* reflow forçado, não requestAnimationFrame: rAF não dispara em aba
         despriorizada, e o modal ficaria montado com opacidade zero — visível
         para o teclado e invisível para os olhos. */
      void voz.offsetWidth;
      voz.classList.add("on");
      vozTitulo.textContent = d.tVwait;
      vozSub.textContent = d.tVsub;
      vozFinal.textContent = ""; vozParcial.textContent = "";
      vozUsar.disabled = true; vozDeNovo.hidden = true;
      voz.classList.remove("erro");

      const temAudio = await ligarOnda();
      if (!temAudio) {
        vozTitulo.textContent = d.tVdenied;
        voz.classList.add("erro");
        vozDeNovo.hidden = false;
        return;
      }
      iniciarFala();
    }

    function iniciarFala() {
      rec = new SR();
      rec.lang = d.lang === "en" ? "en-US" : "pt-BR";
      rec.interimResults = true;
      rec.continuous = true;

      rec.onstart = () => {
        ouvindo = true;
        soMic.classList.add("listening");
        soMic.setAttribute("aria-pressed", "true");
        voz.classList.add("ouvindo");
        vozTitulo.textContent = d.tVtitle;
        setStatus(d.tListening);
      };
      rec.onresult = e => {
        let firme = "", solto = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) firme += t; else solto += t;
        }
        if (firme) texto = (texto + " " + firme).replace(/\s+/g, " ").trim();
        vozParcial.textContent = solto ? (texto ? " " : "") + solto : "";
        pintar();
      };
      rec.onerror = ev => {
        voz.classList.add("erro");
        vozTitulo.textContent = ev.error === "not-allowed" ? d.tVdenied : d.tVoiceoff;
        vozDeNovo.hidden = false;
      };
      rec.onend = () => {
        ouvindo = false;
        voz.classList.remove("ouvindo");
        soMic.classList.remove("listening");
        soMic.setAttribute("aria-pressed", "false");
        vozParcial.textContent = "";
        pararOnda();
        if (!voz.classList.contains("erro")) {
          vozTitulo.textContent = texto.trim() ? d.tVdone : d.tVnothing;
        }
        vozDeNovo.hidden = false;
        pintar();
      };
      try { rec.start(); } catch (e) { /* já ativo */ }
    }

    if (voz) {
      soMic.addEventListener("click", () => {
        if (!voz.hidden) { fecharVoz(); return; }
        abrirVoz();
      });
      voz.querySelector("[data-voz-fechar]").addEventListener("click", fecharVoz);
      voz.addEventListener("click", e => { if (e.target === voz) fecharVoz(); });
      vozDeNovo.addEventListener("click", () => abrirVoz());
      vozUsar.addEventListener("click", () => {
        const t = texto.trim();
        fecharVoz();
        if (!t) return;
        soInput.value = t;
        soInput.focus();
        doSearch(t);
      });
    } else if (soMic) {
      soMic.addEventListener("click", () => setStatus(d.tVoiceoff));
    }

    /* imagem: o servidor compara a foto com as imagens dos cases e devolve os
       parecidos. Roda local, sem IA e sem chave: a imagem não sai do servidor. */
    /* ---------- imagem: mesma caixa da voz, com arquivo ou endereço ----------

       Duas entradas para a mesma pergunta: quem tem o arquivo arrasta, quem viu
       a imagem em outro site cola o link. O que o servidor faz é igual nos dois
       casos — reduz a imagem a um hash e compara com as dos cases. */
    const jan = document.querySelector("[data-img]");
    const janSolte = jan && jan.querySelector("[data-img-solte]");
    const janArquivo = jan && jan.querySelector("[data-img-arquivo]");
    const janLink = jan && jan.querySelector("[data-img-link]");
    const janForm = jan && jan.querySelector("[data-img-form]");
    const janErro = jan && jan.querySelector("[data-img-erro]");
    const janPrevia = jan && jan.querySelector("[data-img-previa]");

    const erroImg = chave => {
      if (!janErro) return;
      janErro.textContent = d["tIerr" + chave.charAt(0).toUpperCase() + chave.slice(1)] || d.tAioff;
      janErro.hidden = false;
      jan.classList.remove("lendo");
    };

    const fecharImg = () => {
      if (!jan) return;
      jan.hidden = true;
      jan.classList.remove("on", "lendo", "sobre");
      soImg.classList.remove("analyzing");
    };

    const abrirImg = () => {
      if (!jan) return;
      jan.hidden = false;
      void jan.offsetWidth;          /* mesmo motivo da voz: rAF não é confiável */
      jan.classList.add("on");
      janErro.hidden = true;
      janPrevia.hidden = true;
      janLink.value = "";
      setTimeout(() => janLink.focus(), 260);
    };

    /* o resultado é o mesmo dos dois caminhos: mostra na busca e fecha a janela */
    async function mandarImagem(corpo, previa) {
      janErro.hidden = true;
      jan.classList.add("lendo");
      soImg.classList.add("analyzing");
      if (previa) {
        janPrevia.querySelector("img").src = previa;
        janPrevia.hidden = false;
      }
      try {
        const r = await fetch(corpo.url, { method: "POST", body: corpo.dados });
        const data = await r.json();
        if (!data.ok) { erroImg(data.error || "resposta"); return; }
        const achou = (data.groups || []).some(g => g.items && g.items.length);
        fecharImg();
        setSearch(true);
        if (achou) { renderGroups(data.groups, ""); soStatus.textContent = d.tImgkw; }
        else { setStatus(d.tAioff); }
      } catch (e) {
        erroImg("resposta");
      } finally {
        jan.classList.remove("lendo");
        soImg.classList.remove("analyzing");
      }
    }

    function mandarArquivo(file) {
      if (!file) return;
      if (file.size > 8 * 1024 * 1024) { erroImg("tamanho"); return; }
      const fd = new FormData();
      fd.append("file", file);
      fd.append("lang", d.lang);
      mandarImagem({ url: "/api/search/image", dados: fd }, URL.createObjectURL(file));
    }

    if (jan) {
      soImg.addEventListener("click", () => { jan.hidden ? abrirImg() : fecharImg(); });
      jan.querySelector("[data-img-fechar]").addEventListener("click", fecharImg);
      jan.addEventListener("click", e => { if (e.target === jan) fecharImg(); });
      jan.querySelector("[data-img-escolher]").addEventListener("click", () => janArquivo.click());
      janArquivo.addEventListener("change", () => {
        const f = janArquivo.files[0];
        janArquivo.value = "";
        mandarArquivo(f);
      });

      ["dragenter", "dragover"].forEach(ev => janSolte.addEventListener(ev, e => {
        e.preventDefault(); janSolte.classList.add("sobre");
      }));
      ["dragleave", "drop"].forEach(ev => janSolte.addEventListener(ev, e => {
        e.preventDefault();
        janSolte.classList.remove("sobre");
        if (ev === "drop" && e.dataTransfer && e.dataTransfer.files[0]) mandarArquivo(e.dataTransfer.files[0]);
      }));

      janForm.addEventListener("submit", e => {
        e.preventDefault();
        const u = janLink.value.trim();
        if (!u) return;
        const fd = new FormData();
        fd.append("url", u);
        fd.append("lang", d.lang);
        mandarImagem({ url: "/api/search/image-url", dados: fd }, "");
      });
    } else {
      soImg.addEventListener("click", () => soFile.click());
      soFile.addEventListener("change", () => mandarArquivo(soFile.files[0]));
    }

    const setSearch = open => {
      clearTimeout(soCloseTimer);
      if (open) {
        searchOverlay.classList.remove("closing");
        searchOverlay.classList.add("open");
        setTimeout(() => soInput.focus(), 380);
      } else if (searchOverlay.classList.contains("open")) {
        fecharVoz();
        fecharImg();
        searchOverlay.classList.add("closing");
        searchOverlay.classList.remove("open");
        soCloseTimer = setTimeout(() => searchOverlay.classList.remove("closing"), 900);
      } else {
        return;
      }
      searchBtn.setAttribute("aria-expanded", String(open));
      searchOverlay.setAttribute("aria-hidden", String(!open));
      if (lenis) open ? lenis.stop() : lenis.start();
      document.body.style.overflow = open ? "hidden" : "";
    };
    searchBtn.addEventListener("click", () => setSearch(true));
    document.querySelector(".mm-search")?.addEventListener("click", () => setSearch(true));
    searchOverlay.querySelector(".so-close").addEventListener("click", () => setSearch(false));
    searchOverlay.querySelector(".so-head .brand")?.addEventListener("click", () => setSearch(false));
    soResults.addEventListener("click", e => { if (e.target.closest("a")) setSearch(false); });
    addEventListener("keydown", e => {
      /* Esc fecha uma camada por vez: primeiro o microfone, depois a busca.
         Fechar as duas de uma vez faria a pessoa perder a tela por engano. */
      if (e.key === "Escape") {
        if (voz && !voz.hidden) { fecharVoz(); return; }
        if (jan && !jan.hidden) { fecharImg(); return; }
        setSearch(false);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearch(true); }
    });
  }

  /* ---------- aviso de "copiado", compartilhado por todo botão de copiar ---------- */
  /* Copiar link: o botão mudava de cor por 1,6s e era todo o retorno. Num
     ícone de 20px isso passa despercebido, e a pessoa clica de novo sem saber
     se funcionou. Agora abre este aviso, no mesmo desenho dos outros modais —
     e é o mesmo aviso que qualquer botão de copiar no site usa, do share de
     case ao "Copiar" do bloco de prompt do Nodal (ver mais abaixo): a regra é
     uma só, então o mecanismo também é.
     Fica fora do `if (shareButtons.length)` de propósito, porque o Nodal usa
     `mostrarAviso` mesmo em página sem nenhum botão de share. */
  const avisoCopia = document.getElementById("avisoCopia");
  let fecharAviso = null;
  const msgPadrao = avisoCopia?.querySelector(".am-msg")?.textContent || "";
  const msgErro = avisoCopia?.dataset.amErro || "";
  const mostrarAviso = (url, rotulo) => {
    if (!avisoCopia) return;   // página sem o diálogo: o clique ainda copia
    const alvo = avisoCopia.querySelector("[data-am-url]");
    if (alvo) alvo.textContent = url.replace(/^https?:\/\//, "");
    const msg = avisoCopia.querySelector(".am-msg");
    if (msg) msg.textContent = rotulo || msgPadrao;
    if (!avisoCopia.open) avisoCopia.showModal();
    clearTimeout(fecharAviso);
    fecharAviso = setTimeout(() => avisoCopia.open && avisoCopia.close(), 2600);
  };
  avisoCopia?.addEventListener("click", () => avisoCopia.close());

  /* Copia `texto` e só então avisa sucesso — nunca ao contrário. Sem
     `navigator.clipboard` (contexto sem TLS, navegador antigo) ou com a
     promessa rejeitada, nada foi copiado, e um botão que vira verde e um
     aviso que diz "copiado" mentindo é pior que o botão inerte que existia
     antes: um botão que não faz nada a pessoa percebe; um que confirma
     sucesso faz ela sair confiando numa área de transferência vazia.
     `aoCopiar` só roda dentro do sucesso (é onde o botão vira verde) —
     nunca no `.catch`. */
  const copiarEavisar = (texto, exibir, rotuloOk, aoCopiar) => {
    if (!navigator.clipboard) {
      mostrarAviso("", msgErro);
      return;
    }
    navigator.clipboard.writeText(texto).then(() => {
      aoCopiar && aoCopiar();
      mostrarAviso(exibir, rotuloOk);
    }).catch(() => {
      mostrarAviso("", msgErro);
    });
  };

  /* ---------- compartilhamento genérico (case + página do cliente) ---------- */
  const shareButtons = document.querySelectorAll("[data-share]");
  if (shareButtons.length) {
    const openShare = btn => {
      const ctx = btn.closest("[data-share-ctx]");
      const fallbackTitle = document.querySelector(".project")?.dataset.shareTitle || document.title;
      const url = ctx?.dataset.shareUrl
        ? new URL(ctx.dataset.shareUrl, location.origin).href
        : location.href;
      const title = ctx?.dataset.shareTitle || fallbackTitle;
      const img = ctx?.dataset.shareImg || document.querySelector("[data-gallery] img")?.src || "";
      const enc = encodeURIComponent;
      const links = {
        x: `https://twitter.com/intent/tweet?url=${enc(url)}&text=${enc(title)}`,
        threads: `https://threads.net/intent/post?text=${enc(title + " " + url)}`,
        linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${enc(url)}`,
        pinterest: `https://pinterest.com/pin/create/button/?url=${enc(url)}&media=${enc(img)}&description=${enc(title)}`,
        whatsapp: `https://wa.me/?text=${enc(title + " " + url)}`,
      };
      const net = btn.dataset.share;
      if (net === "copy") {
        /* o endereço copiado é o que aparece no aviso: quem avisa precisa
           saber o que foi copiado. Num card de case o botão copia o
           endereço daquele case, não o da página onde o card está. */
        copiarEavisar(url, url, btn.closest("[data-share-aviso]")?.dataset.shareAviso, () => {
          btn.classList.add("ok");
          setTimeout(() => btn.classList.remove("ok"), 1600);
        });
        return;
      }
      if (net === "email") {
        location.href = `mailto:?subject=${enc(title)}&body=${enc(url)}`;
        return;
      }
      if (links[net]) open(links[net], "_blank", "noopener,width=680,height=560");
    };

    shareButtons.forEach(btn => {
      btn.addEventListener("click", () => openShare(btn));
    });
  }

  /* ---------- Nodal: "Copiar" do bloco de prompt ---------- */
  /* O botão nasce escondido (main.css: `.no-js [data-nb-copiar]`) e só
     aparece com o script no ar — sem isto, um clique que não copia nada é
     justamente o defeito que esta linha conserta. Mesmo aviso de sempre:
     copiar aqui não é diferente de copiar um link, é o mesmo gesto com outro
     conteúdo. */
  const promptCopyButtons = document.querySelectorAll("[data-nb-copiar]");
  promptCopyButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const texto = btn.closest(".nb-prompt")?.querySelector("pre")?.textContent || "";
      if (!texto) return;
      // o aviso mostra uma prévia curta, não o prompt inteiro — a caixa é
      // pensada para um endereço, não para um parágrafo
      const previa = texto.length > 60 ? texto.slice(0, 60).trim() + "…" : texto;
      copiarEavisar(texto, previa, "Prompt copiado", () => {
        btn.classList.add("ok");
        setTimeout(() => btn.classList.remove("ok"), 1600);
      });
    });
  });

  /* ---------- listagens de cases: 4 visualizações + preview em lista ---------- */
  const initCasesView = () => {
  const clientCases = document.querySelector("[data-cases-view]");
  if (clientCases) {
    const cseg = document.querySelector(".cases-vs .vs-seg");
    const cInd = cseg?.querySelector(".vs-ind");
    const cBtns = [...(cseg ? cseg.querySelectorAll("[data-view2]") : [])];
    const CVIEWS = ["editorial", "grid", "lista", "masonry"];
    const DEFAULT_VIEW = clientCases.dataset.defaultView || "editorial";
    const VIEW_KEY = "lf-view-" + (clientCases.dataset.viewKey || "cases");
    const moveCInd = () => {
      const on = cseg?.querySelector("button.on");
      if (!on || !cInd) return;
      cInd.style.left = on.offsetLeft + "px";
      cInd.style.width = on.offsetWidth + "px";
    };
    const setCView = v => {
      if (!CVIEWS.includes(v)) v = DEFAULT_VIEW;
      CVIEWS.forEach(x => clientCases.classList.remove("cv-" + x));
      clientCases.classList.add("cv-" + v);
      cBtns.forEach(b => b.classList.toggle("on", b.dataset.view2 === v));
      moveCInd();
      try { localStorage.setItem(VIEW_KEY, v); } catch (e) { /* modo privado */ }
      if (hasGSAP) requestAnimationFrame(() => ScrollTrigger.refresh());
    };
    let savedCView = null;
    try { savedCView = localStorage.getItem(VIEW_KEY); } catch (e) { /* modo privado */ }
    if (savedCView && savedCView !== DEFAULT_VIEW) setCView(savedCView);
    else moveCInd();
    cBtns.forEach(b => b.addEventListener("click", () => setCView(b.dataset.view2)));
    addEventListener("resize", moveCInd, { passive: true });

    /* modo lista: preview da capa seguindo o mouse */
    const peek = document.querySelector("[data-cases-peek]");
    if (peek && fine) {
      let peekOn = false;
      clientCases.querySelectorAll(".work-card").forEach(card => {
        card.addEventListener("pointerenter", () => {
          if (!clientCases.classList.contains("cv-lista") || !card.dataset.peek) return;
          peek.src = card.dataset.peek;
          peek.classList.add("show");
          peekOn = true;
        });
        card.addEventListener("pointerleave", () => {
          peek.classList.remove("show");
          peekOn = false;
        });
      });
      addEventListener("pointermove", e => {
        if (!peekOn) return;
        peek.style.left = Math.min(e.clientX + 26, innerWidth - peek.offsetWidth - 20) + "px";
        peek.style.top = Math.min(e.clientY + 22, innerHeight - peek.offsetHeight - 20) + "px";
      }, { passive: true });
    }
  }

  };
  initCasesView();

  /* ---------- case v4: visualizações, share, votos, barra e lightbox ---------- */
  const projectEl = document.querySelector(".project");
  if (projectEl) {
    const caseId = projectEl.dataset.caseId;

    /* alternador de visualização (persistido) */
    const gallery = document.querySelector("[data-gallery]");
    const viewBtns = [...document.querySelectorAll(".view-switch [data-view]")];
    const vsInd = document.querySelector(".vs-ind");
    /* Sem "behance": valor antigo guardado no navegador de quem ja visitou nao
       esta mais nesta lista, e `setView` devolve o editorial. Ninguem fica
       preso numa visualizacao que deixou de existir. */
    const VIEWS = ["editorial", "grid", "masonry"];
    const moveInd = () => {
      const on = document.querySelector(".vs-seg button.on");
      if (!on || !vsInd) return;
      vsInd.style.left = on.offsetLeft + "px";
      vsInd.style.width = on.offsetWidth + "px";
    };
    const setView = v => {
      if (!VIEWS.includes(v)) v = "editorial";
      VIEWS.forEach(x => gallery.classList.remove("view-" + x));
      gallery.classList.add("view-" + v);
      viewBtns.forEach(b => b.classList.toggle("on", b.dataset.view === v));
      moveInd();
      try { localStorage.setItem("lf-case-view", v); } catch (e) { /* modo privado */ }
      if (hasGSAP) requestAnimationFrame(() => ScrollTrigger.refresh());
    };
    if (gallery && viewBtns.length) {
      let savedView = null;
      try { savedView = localStorage.getItem("lf-case-view"); } catch (e) { /* modo privado */ }
      if (savedView && savedView !== "editorial") setView(savedView);
      else moveInd();
      viewBtns.forEach(b => b.addEventListener("click", () => setView(b.dataset.view)));
      addEventListener("resize", moveInd, { passive: true });
    }

    /* curtiu o case? — mesmo sistema de votos das dicas de IA */
    const voteBox = document.querySelector("[data-case-vote]");
    if (voteBox && caseId) {
      const vbtns = [...voteBox.querySelectorAll("[data-cvote]")];
      const voteKey = "lf-case-vote-" + caseId;
      const renderVotes = votes => {
        voteBox.querySelector('[data-cvote-count="up"]').textContent = votes.up || 0;
        voteBox.querySelector('[data-cvote-count="down"]').textContent = votes.down || 0;
      };
      fetch(`/cases/${caseId}/votes`).then(r => r.json()).then(renderVotes).catch(() => {});
      const lockVotes = v => vbtns.forEach(b => {
        b.disabled = true;
        b.classList.toggle("voted", b.dataset.cvote === v);
      });
      let prevVote = null;
      try { prevVote = localStorage.getItem(voteKey); } catch (e) { /* modo privado */ }
      if (prevVote) lockVotes(prevVote);
      vbtns.forEach(b => b.addEventListener("click", async () => {
        if (b.disabled) return;
        lockVotes(b.dataset.cvote);
        try { localStorage.setItem(voteKey, b.dataset.cvote); } catch (e) { /* modo privado */ }
        try {
          const r = await fetch("/cases/vote", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: Number(caseId), vote: b.dataset.cvote }),
          });
          const data = await r.json();
          if (data.ok) renderVotes(data.votes);
        } catch (e) { /* offline */ }
      }));
    }

    /* ver case em tela cheia: navegador inteiro em fullscreen */
    const toggleBrowserFs = () => {
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      else if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    };
    const caseFsBtn = document.querySelector("[data-case-fs]");
    if (caseFsBtn) {
      caseFsBtn.addEventListener("click", toggleBrowserFs);
      document.addEventListener("fullscreenchange", () => {
        const on = !!document.fullscreenElement;
        caseFsBtn.classList.toggle("on", on);
        caseFsBtn.setAttribute("aria-pressed", String(on));
      });
    }

    /* barra fixa: aparece só quando o usuário rola para cima */
    const caseBar = document.querySelector("[data-case-bar]");
    if (caseBar) {
      let lastBarY = 0;
      const onBar = y => {
        const show = y < lastBarY - 2 && y > 600;
        if (show !== caseBar.classList.contains("show")) {
          caseBar.classList.toggle("show", show);
          caseBar.setAttribute("aria-hidden", String(!show));
        }
        lastBarY = y;
      };
      if (lenis) lenis.on("scroll", ({ scroll }) => onBar(scroll));
      else addEventListener("scroll", () => onBar(scrollY), { passive: true });
    }

    /* lightbox carrossel: zoom, tela cheia, share e bloqueio de download */
    const clb = document.getElementById("caseLightbox");
    const galleryImgs = [...document.querySelectorAll("[data-gallery] img[data-full]")];
    if (clb && galleryImgs.length) {
      const stage = clb.querySelector(".clb-stage");
      const stageImg = stage.querySelector("img");
      const clbCount = clb.querySelector(".lb-count");
      const zoomBtn = clb.querySelector(".clb-zoom");
      const fsBtn = clb.querySelector(".clb-fs");
      const shareToolBtn = clb.querySelector(".clb-share");
      const sharePanel = clb.querySelector(".clb-share-panel");
      const sources = galleryImgs.map(i => i.dataset.full);
      let ci = 0;
      const setZoom = on => {
        clb.classList.toggle("zoomed", on);
        zoomBtn.classList.toggle("on", on);
        zoomBtn.setAttribute("aria-pressed", String(on));
        if (!on) stageImg.style.transformOrigin = "";
      };
      const goTo = i => {
        ci = (i + sources.length) % sources.length;
        stageImg.src = sources[ci];
        clbCount.textContent = `${ci + 1} / ${sources.length}`;
        setZoom(false);
      };
      galleryImgs.forEach((im, i) => im.closest("figure").addEventListener("click", () => {
        goTo(i);
        clb.showModal();
      }));
      clb.querySelector(".lb-prev").addEventListener("click", () => goTo(ci - 1));
      clb.querySelector(".lb-next").addEventListener("click", () => goTo(ci + 1));
      clb.addEventListener("keydown", e => {
        if (e.key === "ArrowLeft") goTo(ci - 1);
        if (e.key === "ArrowRight") goTo(ci + 1);
      });
      clb.querySelector(".lightbox-close").addEventListener("click", () => clb.close());
      clb.addEventListener("click", e => { if (e.target === clb) clb.close(); });
      clb.addEventListener("close", () => { setZoom(false); sharePanel.hidden = true; });
      /* zoom com origem seguindo o mouse */
      zoomBtn.addEventListener("click", () => setZoom(!clb.classList.contains("zoomed")));
      stage.addEventListener("click", () => { if (clb.classList.contains("zoomed")) setZoom(false); });
      stage.addEventListener("pointermove", e => {
        if (!clb.classList.contains("zoomed")) return;
        const r = stage.getBoundingClientRect();
        stageImg.style.transformOrigin =
          `${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`;
      });
      /* Tela cheia da imagem, não da página.

         Antes este botão chamava a mesma função do botão do topo e punha o
         navegador inteiro em fullscreen: a página ia junto, e a foto continuava
         do mesmo tamanho dentro do modal. Aqui quem vai para a tela cheia é a
         figura do palco, então a imagem ocupa a tela de verdade.

         Sair volta exatamente ao estado anterior, porque o modal nunca foi
         fechado: ele continua aberto atrás, com a mesma foto selecionada. */
      const naTelaCheia = () => document.fullscreenElement === stage;
      const alternarTelaCheia = () => {
        if (naTelaCheia()) { document.exitFullscreen().catch(() => {}); return; }
        if (stage.requestFullscreen) {
          setZoom(false);                      // zoom e tela cheia brigam pelo mesmo gesto
          stage.requestFullscreen().catch(() => {});
        }
      };
      fsBtn.addEventListener("click", alternarTelaCheia);
      stage.querySelector("[data-clb-sair]")?.addEventListener("click", e => {
        e.stopPropagation();                   // o clique no palco também tira o zoom
        document.exitFullscreen().catch(() => {});
      });
      document.addEventListener("fullscreenchange", () => {
        const on = naTelaCheia();
        clb.classList.toggle("clb-cheia", on);
        fsBtn.classList.toggle("on", on);
        fsBtn.setAttribute("aria-pressed", String(on));
      });
      /* achou interessante? compartilhe */
      shareToolBtn.addEventListener("click", () => {
        const opening = sharePanel.hidden;
        sharePanel.hidden = !opening;
        shareToolBtn.setAttribute("aria-expanded", String(opening));
        shareToolBtn.classList.toggle("on", opening);
      });
      /* bloqueio de download: sem menu de contexto e sem arrastar */
      clb.addEventListener("contextmenu", e => e.preventDefault());
      document.querySelectorAll("[data-gallery] img").forEach(im =>
        im.addEventListener("contextmenu", e => e.preventDefault()));
    }
  }

  /* ---------- tipografia + reveals (após fontes e preloader) ---------- */
  let typographyBooted = false;
  const initTypography = () => {
    /* idempotente: elementos já animados são marcados e ignorados nas
       reinicializações (troca de categoria/página sem recarregar) */
    const fresh = sel => [...document.querySelectorAll(sel)].filter(el => {
      if (el.dataset.anim === "1") return false;
      el.dataset.anim = "1";
      return true;
    });

    fresh("[data-hero-title]").forEach(el => {
      const split = new SplitText(el, { type: "lines,words", linesClass: "st-line" });
      gsap.set(split.lines, { overflow: "hidden" });
      gsap.from(split.words, {
        yPercent: 110, duration: 1.05, ease: "power4.out", stagger: .055,
        scrollTrigger: { trigger: el, start: "top bottom" },
      });
    });

    /* PageSpeed (auditoria de acessibilidade) reprova `aria-label` num `<p>`
       (papel genérico — atributo proibido nele). O SplitText, no padrão
       `aria: "auto"`, põe exatamente isso no elemento partido. Solução
       recomendada pelo próprio GSAP: `aria: "none"` desliga esse
       aria-label automático (e o aria-hidden que ele poria em cada
       palavra); a cópia íntegra do texto vai antes, num <span class="sr-only">
       fora do fluxo visual, e o `<p>` partido em si ganha aria-hidden="true"
       para o leitor de tela não anunciar cada fragmento de palavra. */
    fresh("[data-split]").forEach(el => {
      const srOnly = document.createElement("span");
      srOnly.className = "sr-only";
      srOnly.textContent = el.textContent;
      el.before(srOnly);
      el.setAttribute("aria-hidden", "true");

      const split = new SplitText(el, { type: "words", aria: "none" });
      gsap.fromTo(split.words, { opacity: .14 }, {
        opacity: 1, stagger: .06, ease: "none",
        scrollTrigger: { trigger: el, start: "top 78%", end: "bottom 45%", scrub: true },
      });
    });

    /* `gsap.from` esconde o elemento na hora e só devolve quando o gatilho
       dispara. Isso torna a posição do gatilho crítica: se ela for medida antes
       das imagens carregarem, a página cresce depois, o gatilho fica apontando
       para o lugar errado, e o que já passou nunca dispara. O elemento fica
       invisível para sempre.

       Numa página de case com catorze imagens, cada uma mudando a altura ao
       carregar, isso aparecia como um bloco em branco no meio do conteúdo.

       Duas defesas: recalcular as posições quando as imagens terminam, e uma
       rede embaixo que devolve à mão o que sobrar escondido. Conteúdo invisível
       para sempre é pior que animação perdida. */
    fresh("[data-reveal]").forEach(el => {
      gsap.from(el, {
        y: 30, opacity: 0, duration: .9, ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 96%" },
      });
    });

    const recalcular = () => ScrollTrigger.refresh();
    const imagens = [...document.images].filter(i => !i.complete);
    if (imagens.length) {
      let faltam = imagens.length;
      const conta = () => { if (--faltam <= 0) recalcular(); };
      imagens.forEach(i => { i.addEventListener("load", conta, { once: true });
                             i.addEventListener("error", conta, { once: true }); });
    }
    addEventListener("load", recalcular, { once: true });

    const redeDeSeguranca = () => {
      document.querySelectorAll("[data-reveal]").forEach(el => {
        if (+getComputedStyle(el).opacity > .01) return;
        const r = el.getBoundingClientRect();
        // só o que já devia estar visível: acima ou dentro da janela
        if (r.top < innerHeight * 1.1) gsap.set(el, { opacity: 1, y: 0, clearProps: "transform" });
      });
    };
    setTimeout(redeDeSeguranca, 2500);
    addEventListener("load", () => setTimeout(redeDeSeguranca, 1200), { once: true });

    fresh("[data-parallax]").forEach(img => {
      gsap.fromTo(img, { yPercent: -6, scale: 1.1 }, {
        yPercent: 6, scale: 1.1, ease: "none",
        scrollTrigger: { trigger: img.closest("figure") || img, start: "top bottom", end: "bottom top", scrub: true },
      });
    });

    fresh("[data-count]").forEach(el => {
      const target = parseInt(el.dataset.count, 10);
      const obj = { v: 0 };
      gsap.to(obj, {
        v: target, duration: 1.3, ease: "power3.out",
        onUpdate: () => { el.textContent = Math.round(obj.v); },
        scrollTrigger: { trigger: el, start: "top 85%" },
      });
    });

    // vida: marquee acelera com a velocidade do scroll
    const track = typographyBooted ? null : document.querySelector(".marquee-track");
    if (track) {
      track.style.animation = "none";
      const tween = gsap.to(track, { xPercent: -50, duration: 26, ease: "none", repeat: -1 });
      if (lenis) {
        lenis.on("scroll", e => {
          tween.timeScale(gsap.utils.clamp(1, 4, 1 + Math.abs(e.velocity) * .06));
        });
        gsap.ticker.add(() => tween.timeScale(gsap.utils.interpolate(tween.timeScale(), 1, .03)));
      }
    }

    // vida: títulos grandes derivam horizontalmente no scroll
    fresh(".fwork-intro, .footer-cta-title").forEach((el, i) => {
      gsap.fromTo(el, { xPercent: i % 2 ? 3 : -3 }, {
        xPercent: i % 2 ? -3 : 3, ease: "none",
        scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: 1.4 },
      });
    });

    // feed IG: título e @ derivam em direções opostas
    fresh("[data-drift]").forEach(el => {
      const dir = el.dataset.drift === "right" ? 1 : -1;
      gsap.fromTo(el, { x: dir * -50 }, {
        x: dir * 50, ease: "none",
        scrollTrigger: { trigger: el.closest("section") || el, start: "top bottom", end: "bottom top", scrub: 1.2 },
      });
    });

    // vida: imagens do feed, destaque e história entram com escala
    fresh(".ig-tile, .fwork-card figure, .story-img").forEach(el => {
      gsap.from(el, {
        scale: .94, opacity: 0, duration: .9, ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 94%" },
      });
    });

    /* vida: cards derivam sutilmente em velocidades diferentes ao rolar.

       Vale para card solto, não para linha de lista. Quem neutraliza isso na
       visualização em lista é o CSS (`.cv-lista .work-card { transform: none }`),
       e não estado guardado aqui: desligar e religar o ScrollTrigger a cada
       troca de vista devolvia a lista certa mas não devolvia a deriva na grade,
       e efeito que só funciona até a primeira troca é pior que efeito nenhum. */
    /* Só os cards editoriais da home. Nas listagens de case a deriva movia um
       card sim e outro não em até 80px de percurso: numa grade de quatro
       colunas isso é meia coluna subindo e a vizinha descendo, com as legendas
       paradas em alturas diferentes. A profundidade continua existindo lá, mas
       dentro da moldura — é a imagem que desliza (data-parallax), não o card,
       e imagem que desliza dentro de um figure com overflow escondido nunca
       tira a grade do lugar. */
    fresh(".fwork-card").forEach((card, i) => {
      gsap.fromTo(card, { y: i % 2 ? 40 : 0 }, {
        y: i % 2 ? -40 : 0, ease: "none",
        scrollTrigger: { trigger: card, start: "top bottom", end: "bottom top", scrub: 1.2 },
      });
    });

    // vida: skew das imagens conforme a velocidade do scroll
    if (lenis && !typographyBooted) {
      const skewables = gsap.utils.toArray(".fwork-card figure, .work-card figure, .g-item");
      if (skewables.length) {
        const setSkew = gsap.quickTo(skewables, "skewY", { duration: .35, ease: "power2.out" });
        lenis.on("scroll", e => setSkew(gsap.utils.clamp(-3.5, 3.5, e.velocity * .12)));
      }
    }

    // timeline horizontal (Sobre): seção pina e os cards avançam com o scroll
    const tlh = typographyBooted ? null : document.querySelector(".tlh");
    if (tlh && innerWidth > 900 && !("ontouchstart" in window)) {
      const track = tlh.querySelector(".tlh-track");
      const dist = () => Math.max(0, track.scrollWidth - tlh.clientWidth);
      if (dist() > 40) {
        tlh.classList.add("pinned");
        const st = {
          trigger: ".xp-h", start: "top 12%", end: () => "+=" + dist(),
          pin: true, scrub: 1, invalidateOnRefresh: true,
        };
        gsap.to(track, { x: () => -dist(), ease: "none", scrollTrigger: st });
        gsap.fromTo(".tlh-line i", { scaleX: 0 }, { scaleX: 1, ease: "none", scrollTrigger: { ...st, pin: false } });
        gsap.utils.toArray(".tlh-card").forEach((card, i) => {
          gsap.from(card, {
            y: 40, opacity: 0, duration: .6, ease: "power3.out", delay: Math.min(i * .06, .5),
            scrollTrigger: { trigger: ".xp-h", start: "top 60%" },
          });
        });
      }
    }

    // featured work: card visível ↔ título/meta ativos no rail
    const cards = typographyBooted ? [] : gsap.utils.toArray("[data-fw-card]");
    if (cards.length) {
      const activate = i => {
        document.querySelectorAll("[data-fw-title]").forEach(t => t.classList.toggle("is-active", +t.dataset.fwTitle === i));
        document.querySelectorAll("[data-fw-meta]").forEach(m => m.classList.toggle("is-active", +m.dataset.fwMeta === i));
      };
      cards.forEach((card, i) => {
        ScrollTrigger.create({
          trigger: card, start: "top 55%", end: "bottom 55%",
          onEnter: () => activate(i), onEnterBack: () => activate(i),
        });
      });
    }
    typographyBooted = true;
    ScrollTrigger.refresh();
  };

  if (hasGSAP && !reduced) {
    const start = () => requestAnimationFrame(() => {
      const probe = document.querySelector("[data-hero-title]");
      if (probe && probe.offsetWidth === 0) return requestAnimationFrame(start);
      initTypography();
    });
    Promise.all([document.fonts?.ready || Promise.resolve(), preloaderDone]).then(start, start);
  }

  /* ---------- cursor chip ---------- */
  const chip = document.querySelector(".cursor-chip");
  if (chip && fine && !reduced) {
    let x = 0, y = 0, rx = 0, ry = 0, active = false;
    addEventListener("pointermove", e => { x = e.clientX; y = e.clientY; }, { passive: true });
    (function loop() {
      if (active) {
        rx += (x - rx) * .18; ry += (y - ry) * .18;
        chip.style.transform = `translate(${rx}px, ${ry}px) translate(-50%, -50%) scale(1)`;
      } else { rx = x; ry = y; }
      requestAnimationFrame(loop);
    })();
    /* O texto do chip vem do próprio card. Antes era fixo em "Ver case", e um
       card de site prometia uma página que não existe — o clique abre o site
       do cliente. Sem valor no atributo, vale o padrão que veio no HTML. */
    const rotulo = chip.querySelector("span");
    const padrao = rotulo ? rotulo.textContent : "";
    document.addEventListener("mouseover", e => {
      const alvo = e.target.closest("[data-cursor-chip], .fwork-card");
      active = !!alvo;
      if (alvo && rotulo) rotulo.textContent = alvo.getAttribute("data-cursor-chip") || padrao;
      chip.classList.toggle("on", active);
    });
  }

  /* ---------- vídeo hover ---------- */
  document.querySelectorAll(".fwork-card, .work-card").forEach(card => {
    const video = card.querySelector("video");
    if (!video) return;
    card.addEventListener("mouseenter", () => video.play().catch(() => {}));
    card.addEventListener("mouseleave", () => video.pause());
  });

  /* ---------- transição de página ---------- */
  const curtain = document.querySelector(".curtain");

  /* ---------- navegação instantânea (filtros, paginação e afins) ----------
     Links que só trocam o conteúdo da MESMA página (mudar categoria, virar
     página) não recarregam o site nem passam pela cortina: buscamos o HTML,
     trocamos só o bloco [data-swap] e atualizamos a URL. Sem JS, os links
     continuam funcionando normalmente (são <a href> de verdade). */
  const swapRoot = () => document.querySelector("[data-swap]");
  const prefetched = new Map();

  const prefetch = href => {
    if (prefetched.has(href)) return prefetched.get(href);
    const req = fetch(href, { headers: { "X-Requested-With": "swap" } })
      .then(r => (r.ok ? r.text() : null))
      .catch(() => null);
    prefetched.set(href, req);
    if (prefetched.size > 24) prefetched.delete(prefetched.keys().next().value);
    return req;
  };

  const isSwappable = url => {
    const root = swapRoot();
    if (!root || url.origin !== location.origin) return false;
    // mesma rota base (ex.: /portfolio ou /en/portfolio), mudando só a query
    return url.pathname === location.pathname;
  };

  const applySwap = (html, href, push = true) => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const fresh = doc.querySelector("[data-swap]");
    const root = swapRoot();
    if (!fresh || !root) { location.href = href; return; }
    root.replaceWith(fresh);
    document.title = doc.title;
    if (push) history.pushState({ swap: 1 }, "", href);
    // remonta os módulos que dependem do conteúdo trocado
    initPfSelect();
    initCasesView();
    initTypography();
    if (lenis) lenis.scrollTo(0, { immediate: true });
    else scrollTo({ top: 0 });
    if (hasGSAP) requestAnimationFrame(() => ScrollTrigger.refresh());
  };

  const swapTo = async (href, push = true) => {
    const html = await prefetch(href);
    if (html) applySwap(html, href, push);
    else location.href = href;
  };

  // prefetch assim que o usuário demonstra intenção (hover/toque)
  document.addEventListener("pointerenter", e => {
    const a = e.target?.closest?.("a[href]");
    if (!a || a.target === "_blank") return;
    const url = new URL(a.href, location.href);
    if (url.origin === location.origin && !url.hash) prefetch(a.href);
  }, true);

  document.addEventListener("click", e => {
    // A cortina só age quando NENHUM outro script já tratou o clique: ela é a
    // ÚLTIMA linha (navegação de página inteira), não a primeira. O Nodal
    // troca de aula com `fetch` + `preventDefault` (nodal-estudo.js) e o
    // download do currículo faz o mesmo (acima, `[data-dl]`) — sem este
    // retorno cedo, a cortina não checava a flag e agendava um
    // `location.href` (setTimeout de 440ms) por cima de qualquer um desses,
    // recarregando a página inteira ~440ms depois de um fetch que já tinha
    // resolvido certo. Achado ao vivo (log de rede) numa troca de aula do
    // Nodal.
    if (e.defaultPrevented) return;
    const a = e.target.closest("a[href]");
    if (!a) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || a.target === "_blank" ||
        e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    if (url.pathname === location.pathname && url.hash) return;  // âncora interna

    if (isSwappable(url)) {           // filtro/paginação: troca instantânea
      e.preventDefault();
      swapTo(a.href);
      return;
    }
    if (curtain && !reduced) {        // outra página: mantém a cortina
      e.preventDefault();
      curtain.classList.add("leave");
      setTimeout(() => { location.href = a.href; }, 440);
    }
  });

  addEventListener("popstate", e => {
    if (e.state && e.state.swap && swapRoot()) swapTo(location.href, false);
  });
  addEventListener("pageshow", e => { if (e.persisted && curtain) curtain.classList.remove("leave"); });

  /* ============================================================
     Fundo do hero, fumaça prata mouse-reativa (GLSL próprio)
     Meia-resolução, monocromática, pausa fora da tela.
     ============================================================ */
  const bgCanvas = document.getElementById("glbg");
  if (bgCanvas && !reduced) {
    const gl = bgCanvas.getContext("webgl", { antialias: false, alpha: false, powerPreference: "low-power" });
    if (gl) {
      const VERT = `attribute vec2 p; void main(){ gl_Position = vec4(p, 0., 1.); }`;
      const FRAG = `
precision mediump float;
uniform vec2 uRes; uniform float uTime; uniform vec2 uMouse;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), u.x),
             mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0., a = .5;
  for(int i = 0; i < 4; i++){ v += a * noise(p); p *= 2.02; a *= .5; }
  return v;
}
void main(){
  vec2 uv = gl_FragCoord.xy / uRes;
  vec2 p = uv * vec2(uRes.x / uRes.y, 1.);
  vec2 m = uMouse * vec2(uRes.x / uRes.y, 1.);
  float d = length(p - m);
  vec2 warp = (p - m) / max(d, .0001) * exp(-d * 2.4) * .22;
  float n = fbm(p * 1.5 + warp + vec2(uTime * .035, -uTime * .02));
  vec3 col = vec3(.051) + vec3(1.) * smoothstep(.42, 1., n) * .085;
  col += (hash(gl_FragCoord.xy) - .5) * .012;
  gl_FragColor = vec4(col, 1.);
}`;
      const sh = (type, src) => {
        const s = gl.createShader(type);
        gl.shaderSource(s, src); gl.compileShader(s);
        return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
      };
      const vs = sh(gl.VERTEX_SHADER, VERT), fs = sh(gl.FRAGMENT_SHADER, FRAG);
      if (vs && fs) {
        const prog = gl.createProgram();
        gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
        gl.useProgram(prog);
        const buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        const loc = gl.getAttribLocation(prog, "p");
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
        const uRes = gl.getUniformLocation(prog, "uRes");
        const uTime = gl.getUniformLocation(prog, "uTime");
        const uMouse = gl.getUniformLocation(prog, "uMouse");
        const SCALE = .5;
        const resize = () => {
          bgCanvas.width = Math.max(2, bgCanvas.clientWidth * SCALE);
          bgCanvas.height = Math.max(2, bgCanvas.clientHeight * SCALE);
          gl.viewport(0, 0, bgCanvas.width, bgCanvas.height);
        };
        resize();
        addEventListener("resize", resize, { passive: true });
        let mx = .5, my = .45, smx = mx, smy = my, visible = true;
        addEventListener("pointermove", e => {
          const r = bgCanvas.getBoundingClientRect();
          mx = (e.clientX - r.left) / r.width;
          my = 1 - (e.clientY - r.top) / r.height;
        }, { passive: true });
        new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(bgCanvas);
        const t0 = performance.now();
        (function frame() {
          if (visible) {
            smx += (mx - smx) * .05; smy += (my - smy) * .05;
            gl.uniform2f(uRes, bgCanvas.width, bgCanvas.height);
            gl.uniform1f(uTime, (performance.now() - t0) / 1000);
            gl.uniform2f(uMouse, smx, smy);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
          }
          requestAnimationFrame(frame);
        })();
      }
    }
  }

  /* ============================================================
     Hero 3D, monograma LF em Three.js (prata escovada)
     Carregado de forma preguiçosa depois do load, só em desktop:
     zero custo no caminho crítico (Core Web Vitals intactos).
     ============================================================ */
  const canvas = document.getElementById("glhero");
  if (canvas && !reduced) {
    let booted = false;
    const boot = () => {
      if (booted) return;
      if (innerWidth === 0) return setTimeout(boot, 800);  // aba pré-renderizada/oculta
      booted = true;
      const s = document.createElement("script");
      s.src = "/static/vendor/three.min.js";
      s.onload = initThree;
      document.head.appendChild(s);
    };
    if (document.readyState === "complete") setTimeout(boot, 300);
    else addEventListener("load", () => setTimeout(boot, 300), { once: true });
  }

  function initThree() {
    if (typeof THREE === "undefined") return;
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "low-power" });
    // mobile: pixel ratio menor economiza GPU/bateria sem perder o brilho do metal
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, innerWidth <= 960 ? 1.3 : 1.6));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, .1, 500);
    camera.position.set(0, 0, 165);

    // Polígonos do monograma LF (do SVG oficial, viewBox 0–100, y invertido)
    const POLYS = [
      [[57.6, 73.8], [30.6, 73.8], [30.6, 35.7], [40, 35.7], [40, 63.9], [59.5, 63.9]],
      [[64.9, 54.5], [49.4, 54.5], [49.4, 45.1], [66.6, 45.1]],
      [[67.6, 35.7], [49.4, 35.7], [49.4, 26.3], [69.4, 26.3]],
    ];
    const material = new THREE.MeshStandardMaterial({
      color: 0xd9d7d2, metalness: .9, roughness: .28,
    });
    // no tema claro o metal escurece (grafite) para não sumir no fundo bege
    const isLight = () => document.documentElement.dataset.theme === "light";
    const paintForTheme = () => {
      const light = isLight();
      material.color.setHex(light ? 0x3a3936 : 0xd9d7d2);
      material.roughness = light ? .34 : .28;
      material.metalness = light ? .82 : .9;
    };
    const group = new THREE.Group();
    for (const pts of POLYS) {
      const shape = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x - 50, 50 - y)));
      const geo = new THREE.ExtrudeGeometry(shape, {
        depth: 9, bevelEnabled: true, bevelThickness: 1, bevelSize: .8, bevelSegments: 2,
      });
      group.add(new THREE.Mesh(geo, material));
    }
    group.scale.setScalar(.62);
    scene.add(group);

    const ambient = new THREE.AmbientLight(0xffffff, .25);
    scene.add(ambient);
    const key = new THREE.DirectionalLight(0xffffff, 1.1);
    key.position.set(60, 80, 90);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x8d8b86, .5);
    fill.position.set(-80, -40, 60);
    scene.add(fill);
    const lightForTheme = () => {
      const light = isLight();
      ambient.intensity = light ? .55 : .25;
      key.intensity = light ? 1.5 : 1.1;
      fill.intensity = light ? .8 : .5;
    };
    const syncTheme = () => { paintForTheme(); lightForTheme(); };
    syncTheme();
    addEventListener("lf:theme", syncTheme);

    const resize = () => {
      const w = canvas.clientWidth, h = canvas.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      if (w <= 960) {
        // mobile: monograma centralizado no terço superior da hero (o texto ancora embaixo)
        group.scale.setScalar(w < 480 ? .34 : .42);
        group.position.x = 0;
        group.position.y = 22;
      } else {
        // desktop: vive no lado direito do hero, atrás do título
        group.scale.setScalar(.62);
        group.position.x = w > 1200 ? 42 : 30;
        group.position.y = 12;
      }
    };
    resize();
    addEventListener("resize", resize, { passive: true });

    let mx = 0, my = 0, visible = true;
    addEventListener("pointermove", e => {
      mx = (e.clientX / innerWidth - .5) * 2;
      my = (e.clientY / innerHeight - .5) * 2;
    }, { passive: true });
    // mobile: inclinação do aparelho vira o mouse (quando o navegador permite sem prompt);
    // sem giroscópio o movimento idle de sin/cos segue dando vida
    addEventListener("deviceorientation", e => {
      if (e.gamma == null || e.beta == null) return;
      mx = Math.max(-1, Math.min(1, e.gamma / 28));
      my = Math.max(-1, Math.min(1, (e.beta - 45) / 35));
    }, { passive: true });
    new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(canvas);

    const t0 = performance.now();
    (function frame() {
      if (visible) {
        const t = (performance.now() - t0) / 1000;
        group.rotation.y += ((mx * .5 + Math.sin(t * .3) * .25) - group.rotation.y) * .04;
        group.rotation.x += ((-my * .3 + Math.cos(t * .22) * .12) - group.rotation.x) * .04;
        renderer.render(scene, camera);
      }
      requestAnimationFrame(frame);
    })();
  }
})();
