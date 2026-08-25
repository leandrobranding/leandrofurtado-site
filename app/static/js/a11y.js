/* Barra de acessibilidade.
 *
 * Tudo roda no navegador e nada é enviado para lugar nenhum, com uma única
 * exceção: a consulta de palavra, que passa pelo próprio servidor do site.
 * As preferências ficam no localStorage deste navegador.
 *
 * Carregado por base.html e, à mão, pela página de construção, que não herda
 * o base.html.
 */
(function () {
  "use strict";

  var raiz = document.documentElement;
  var caixa = document.querySelector(".a11y");
  if (!caixa) return;

  var lang = caixa.getAttribute("data-lang") === "en" ? "en" : "pt";
  var PT = lang === "pt";
  var prefixo = location.pathname.indexOf("/en/") === 0 || location.pathname === "/en" ? "/en" : "";

  var CHAVE = "lf-a11y";
  var PADRAO = {
    fonte: 0, linhas: 0, letras: 0,
    contraste: 0, satur: 100, dalton: "", daltmodo: "corrigir",
    links: false, teclado: false, lupa: false, dic: false, libras: false,
    estrutura: false
  };
  var est = carregar();

  function carregar() {
    var salvo = {};
    try { salvo = JSON.parse(localStorage.getItem(CHAVE) || "{}") || {}; } catch (e) { salvo = {}; }
    var saida = {};
    for (var k in PADRAO) saida[k] = (k in salvo) ? salvo[k] : PADRAO[k];
    return saida;
  }
  function salvar() {
    try { localStorage.setItem(CHAVE, JSON.stringify(est)); } catch (e) { /* modo privado */ }
  }

  function $(s, onde) { return (onde || caixa).querySelector(s); }
  function $$(s, onde) { return Array.prototype.slice.call((onde || caixa).querySelectorAll(s)); }
  function nosso(el) { return !!(el && el.closest && (el.closest(".a11y") || el.closest("div[vw]"))); }

  /* `!r.width && !r.height` (retângulo zerado) não pega o caso de
     `<details>` fechado: o navegador aplica `content-visibility: hidden` ao
     conteúdo, que esconde da tela mas MANTÉM a caixa de layout — um <li>
     dentro de um módulo fechado do acordeão do Nodal mede largura e altura
     normais e ainda assim não está visível. `checkVisibility()` é a API que
     pergunta a coisa certa ("isto está mesmo na tela?", considerando
     content-visibility, display:none herdado, visibility:hidden e opacity
     0.001), então ela vem primeiro; o teste de retângulo zerado fica como
     reserva só para o navegador que não tem `checkVisibility` (Firefox <
     125, Safari < 17.4) — nesses, o <details> fechado ainda vaza para a
     leitura, mas pelo menos os outros casos de invisibilidade (display:none
     etc.) continuam pegos como sempre pegaram. */
  function visivel(el, r) {
    if (typeof el.checkVisibility === "function") {
      return el.checkVisibility({
        contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true
      });
    }
    return !(!r.width && !r.height);
  }

  /* ====================================================================
     Tamanho da fonte

     O site usa clamp() com vw em quase todo texto, então mexer no font-size
     da raiz não muda nada. O jeito que funciona é medir o tamanho real de
     cada elemento com texto e multiplicar. A medida original fica guardada
     num WeakMap para o retorno ao normal ser exato.
     ==================================================================== */
  // Três níveis, não cinco: passo pequeno demais não se percebe, e o visitante
  // acabava clicando várias vezes sem entender se tinha mudado alguma coisa.
  var ESCALA = [1, 1.25, 1.55];
  var original = new WeakMap();
  var tocados = [];

  function temTextoDireto(el) {
    for (var n = el.firstChild; n; n = n.nextSibling) {
      if (n.nodeType === 3 && n.nodeValue.trim()) return true;
    }
    return false;
  }

  function aplicarFonte() {
    var k = ESCALA[est.fonte] || 1;

    if (k === 1) {
      tocados.forEach(function (el) { el.style.fontSize = ""; });
      tocados = [];
      return;
    }

    var novos = [];
    var todos = document.body.querySelectorAll("*");
    for (var i = 0; i < todos.length; i++) {
      var el = todos[i];
      if (nosso(el) || !temTextoDireto(el)) continue;
      var tag = el.tagName;
      if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") continue;

      var base = original.get(el);
      if (base === undefined) {
        base = parseFloat(getComputedStyle(el).fontSize) || 0;
        if (!base) continue;
        original.set(el, base);
      }
      el.style.fontSize = (base * k).toFixed(2) + "px";
      novos.push(el);
    }
    // o que saiu da página no meio do caminho já não precisa ser limpo
    tocados.forEach(function (el) { if (novos.indexOf(el) === -1) el.style.fontSize = ""; });
    tocados = novos;
  }

  // Conteúdo que entra depois (galeria, busca, feed) também precisa escalar.
  // O observador só fica ligado enquanto há escala: este site mexe no DOM o
  // tempo todo por causa do motion, e observar à toa custa caro.
  var pendente = null;
  var vigia = new MutationObserver(function () {
    clearTimeout(pendente);
    pendente = setTimeout(aplicarFonte, 350);
  });

  function vigiarDom(liga) {
    if (liga) vigia.observe(document.body, { childList: true, subtree: true });
    else { vigia.disconnect(); clearTimeout(pendente); }
  }

  /* ====================================================================
     Cores: contraste, intensidade e daltonismo

     O filtro vai no <html>. No <body> ele transformaria o body em bloco de
     contenção e todo position:fixed passaria a rolar junto com a página.
     ==================================================================== */
  // O tema que o visitante escolheu no site, para devolver ao sair do contraste.
  var temaDono = raiz.getAttribute("data-theme") || "dark";

  function aplicarCores() {
    // Inverter a página com filter deixava foto em negativo, logotipo branco
    // sumindo no branco e grafismo ilegível. O site já tem tema claro pronto,
    // com todos os acertos de logo e textura: o modo de fundo claro passa a
    // usar ele, e o alto contraste só reforça por cima. Nada de inversão.
    if (est.contraste === 2) raiz.setAttribute("data-theme", "light");
    else if (est.contraste === 1) raiz.setAttribute("data-theme", "dark");
    else raiz.setAttribute("data-theme", temaDono);

    var partes = [];
    if (est.satur !== 100) partes.push("saturate(" + (est.satur / 100) + ")");
    if (est.dalton) {
      partes.push("url(#a11y-" + (est.daltmodo === "simular" ? "sim" : "cor") + "-" + est.dalton + ")");
    }
    raiz.style.filter = partes.length ? partes.join(" ") : "";
    marca("contraste", est.contraste || null);
  }

  function marca(nome, valor) {
    if (valor === null || valor === false || valor === "" || valor === 0) {
      raiz.removeAttribute("data-a11y-" + nome);
    } else {
      raiz.setAttribute("data-a11y-" + nome, valor === true ? "1" : String(valor));
    }
  }

  /* ====================================================================
=======
     Lupa de conteúdo: o texto sob o cursor, grande, numa faixa no rodapé
     ==================================================================== */
  var lupa = $("[data-a11y-lupa]");
  var lupaAlvo = null;

  function sobLupa(e) {
    var el = e.target;
    if (!el || nosso(el)) return;
    var txt = "";
    var no = el;
    for (var passo = 0; no && passo < 4; passo++, no = no.parentElement) {
      if (nosso(no)) break;
      txt = (no.innerText || no.textContent || "").replace(/\s+/g, " ").trim();
      if (txt.length > 1) break;
    }
    if (!txt || txt === lupaAlvo) return;
    lupaAlvo = txt;
    lupa.querySelector("span").textContent = txt.slice(0, 320);
    lupa.classList.add("on");
  }

  function ligarLupa(liga) {
    lupa.hidden = !liga;
    if (liga) {
      document.addEventListener("pointerover", sobLupa, { passive: true });
    } else {
      document.removeEventListener("pointerover", sobLupa);
      lupa.classList.remove("on");
      lupaAlvo = null;
    }
  }

  /* ====================================================================
     Sinônimos e significados
     ==================================================================== */
  var verbete = $("[data-a11y-verbete]");

  function fecharVerbete() {
    verbete.classList.remove("on");
    setTimeout(function () { if (!verbete.classList.contains("on")) verbete.hidden = true; }, 250);
  }

  function posicionar(x, y) {
    verbete.hidden = false;
    var largura = verbete.offsetWidth || 340;
    var altura = verbete.offsetHeight || 200;
    var esq = Math.min(Math.max(12, x - largura / 2), innerWidth - largura - 12);
    var topo = y + 16;
    if (topo + altura > innerHeight - 12) topo = Math.max(12, y - altura - 16);
    verbete.style.left = esq + "px";
    verbete.style.top = topo + "px";
  }

  function pintarVerbete(dados) {
    var html = '<div class="a11y-v-topo"><strong>' + escapar(dados.termo) + "</strong>";
    if (dados.classes && dados.classes.length) html += "<i>" + escapar(dados.classes.join(" ·︎ ")) + "</i>";
    html += '<button type="button" data-fechar aria-label="' + (PT ? "Fechar" : "Close") + '">×︎</button></div>';

    if (dados.significados && dados.significados.length) {
      html += "<ol>";
      dados.significados.forEach(function (s) { html += "<li>" + escapar(s) + "</li>"; });
      html += "</ol>";
    } else {
      html += '<p class="a11y-v-vazio">' + (PT ? "Não achei essa palavra no dicionário."
                                               : "I could not find that word.") + "</p>";
    }
    if (dados.sinonimos && dados.sinonimos.length) {
      html += '<div class="a11y-v-sin"><b>' + (PT ? "Sinônimos" : "Synonyms") + "</b>";
      dados.sinonimos.forEach(function (s) { html += "<span>" + escapar(s) + "</span>"; });
      html += "</div>";
    }
    if (dados.fontes && dados.fontes.length) {
      html += '<p class="a11y-v-fonte">' + escapar(dados.fontes.join(" ·︎ ")) + "</p>";
    }
    verbete.innerHTML = html;
  }

  function escapar(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function consultar(palavra, x, y) {
    verbete.innerHTML = '<p class="a11y-v-vazio">' + (PT ? "Buscando…" : "Looking up…") + "</p>";
    posicionar(x, y);
    // reflow forçado em vez de requestAnimationFrame: o rAF não roda em aba
    // oculta, e aí o verbete ficaria montado porém invisível
    void verbete.offsetWidth;
    verbete.classList.add("on");

    fetch(prefixo + "/a11y/palavra?q=" + encodeURIComponent(palavra), { headers: { Accept: "application/json" } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.erro) d = { termo: palavra, significados: [], sinonimos: [], fontes: [] };
        pintarVerbete(d || { termo: palavra });
        posicionar(x, y);
      })
      .catch(function () {
        pintarVerbete({ termo: palavra, significados: [], sinonimos: [], fontes: [] });
      });
  }

  function aoDoisCliques(e) {
    if (nosso(e.target)) return;
    var texto = String(getSelection() || "").trim();
    if (!texto || texto.length > 40 || /\s/.test(texto)) return;
    consultar(texto, e.clientX, e.clientY);
  }

  verbete.addEventListener("click", function (e) {
    if (e.target.closest("[data-fechar]")) fecharVerbete();
  });

  /* ====================================================================
     Estrutura da página
     ==================================================================== */
  var abaAtual = "h";
  // Só marcos de navegação entram na lista. Papéis como listbox e button são
  // componentes, não regiões: enchiam o mapa sem ajudar ninguém a se localizar.
  var REGIOES = PT ? {
    header: "Cabeçalho", banner: "Cabeçalho", nav: "Menu", navigation: "Menu",
    main: "Conteúdo", aside: "Lateral", complementary: "Lateral",
    footer: "Rodapé", contentinfo: "Rodapé", form: "Formulário",
    search: "Busca", section: "Seção", region: "Seção", dialog: "Janela"
  } : {
    header: "Header", banner: "Header", nav: "Menu", navigation: "Menu",
    main: "Content", aside: "Aside", complementary: "Aside",
    footer: "Footer", contentinfo: "Footer", form: "Form",
    search: "Search", section: "Section", region: "Section", dialog: "Dialog"
  };

  function levantar(aba) {
    var itens = [];
    if (aba === "h") {
      $$("h1,h2,h3,h4,h5,h6", document).forEach(function (el) {
        if (nosso(el)) return;
        var txt = (el.innerText || "").replace(/\s+/g, " ").trim();
        if (txt) itens.push({ el: el, rotulo: el.tagName.toLowerCase(), texto: txt });
      });
    } else if (aba === "a") {
      $$("a[href]", document).forEach(function (el) {
        if (nosso(el)) return;
        var txt = (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim();
        var r = el.getBoundingClientRect();
        if (!txt || (!r.width && !r.height)) return;
        var fora = el.hostname && el.hostname !== location.hostname;
        itens.push({ el: el, rotulo: fora ? (PT ? "externo" : "external") : "link", texto: txt });
      });
    } else {
      $$("header,nav,main,aside,footer,form,section[aria-label],section[aria-labelledby],[role]", document)
        .forEach(function (el) {
          if (nosso(el)) return;
          var papel = (el.getAttribute("role") || el.tagName).toLowerCase();
          var nome = REGIOES[papel];
          if (!nome) return;                       // não é marco de navegação
          var r = el.getBoundingClientRect();
          if (!r.height) return;                   // fechado ou escondido agora
          var rotulo = el.getAttribute("aria-label") || "";
          itens.push({ el: el, rotulo: PT ? "região" : "region",
                       texto: rotulo ? nome + " ·︎ " + rotulo : nome });
        });
    }
    return itens;
  }

  function desenharMapa() {
    var ul = $("[data-a11y-mapa]");
    if (!ul) return;
    var itens = levantar(abaAtual);
    if (!itens.length) {
      ul.innerHTML = '<li class="vazio">' + (PT ? "Nada encontrado nesta página." : "Nothing found on this page.") + "</li>";
      return;
    }
    ul.innerHTML = "";
    itens.slice(0, 120).forEach(function (item) {
      var li = document.createElement("li");
      var b = document.createElement("button");
      b.type = "button";
      b.innerHTML = "<small>" + escapar(item.rotulo) + "</small><span>" + escapar(item.texto.slice(0, 90)) + "</span>";
      b.addEventListener("click", function () { irPara(item.el); });
      li.appendChild(b);
      ul.appendChild(li);
    });
  }

  function irPara(el) {
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    el.classList.add("a11y-apontado");
    setTimeout(function () { el.classList.remove("a11y-apontado"); }, 3800);
    // deixar o foco no destino é o que faz o Tab continuar dali
    if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
    try { el.focus({ preventScroll: true }); } catch (e) { /* nada */ }
  }

  /* ====================================================================
     Tradutor de Libras (VLibras, gov.br)

     Carrega só quando pedido: são cerca de 3 MB de player Unity. E precisa da
     política de segurança relaxada, que o servidor só entrega para quem tem o
     cookie — por isso a primeira ativação recarrega a página uma vez.
     ==================================================================== */
  var FONTE_VLIBRAS = "https://vlibras.gov.br/app";

  function cookieLibras(liga) {
    document.cookie = "lf_libras=" + (liga ? "1" : "0") +
      ";path=/;max-age=" + (liga ? 31536000 : 0) + ";samesite=lax" +
      (location.protocol === "https:" ? ";secure" : "");
  }
  function temCookieLibras() { return /(^|;\s*)lf_libras=1/.test(document.cookie); }

  function montarLibras() {
    var no = document.querySelector("[data-a11y-vw]");
    if (!no) return;
    no.hidden = false;
    if (window.__a11yLibras) return;
    window.__a11yLibras = true;

    var s = document.createElement("script");
    s.src = FONTE_VLIBRAS + "/vlibras-plugin.js";
    s.onload = function () {
      try {
        // "BL" = canto inferior esquerdo. No padrão ("R", meio da direita) o
        // avatar cai em cima do campo da newsletter na página de construção e
        // do trilho de redes no site. O visitante ainda pode arrastar.
        new window.VLibras.Widget({ rootPath: FONTE_VLIBRAS, position: "BL", opacity: 1 });
        // O widget monta tudo dentro de window.onload. Se o load nativo ainda
        // não passou, ele mesmo dispara. Se já passou (o visitante ligou o
        // Libras com a página aberta), só chamando à mão a montagem acontece.
        // Chamar nos dois casos registrava dois ouvintes de clique no botão,
        // e aí cada clique abria e fechava o painel na mesma hora.
        if (document.readyState === "complete" && typeof window.onload === "function") {
          window.onload();
        }
      } catch (e) { /* fora do ar: o resto da barra continua funcionando */ }
    };
    document.head.appendChild(s);
  }

  function alternarLibras(liga) {
    if (liga && !temCookieLibras()) { cookieLibras(true); location.reload(); return; }
    if (!liga && temCookieLibras()) { cookieLibras(false); location.reload(); return; }
    if (liga) montarLibras();
  }

  /* ====================================================================
     Pintar a interface a partir do estado
     ==================================================================== */
  function sincronizar() {
    $$("[data-a11y-alterna]").forEach(function (b) {
      b.setAttribute("aria-pressed", est[b.getAttribute("data-a11y-alterna")] ? "true" : "false");
    });
    $$("[data-a11y-quick]").forEach(function (b) {
      var nome = b.getAttribute("data-a11y-quick");
      var ligado = nome === "fonte" ? est.fonte > 0 : nome === "contraste" ? est.contraste > 0 : !!est[nome];
      b.setAttribute("aria-pressed", ligado ? "true" : "false");
    });
    $$("[data-a11y-passo]").forEach(function (bloco) {
      var nome = bloco.getAttribute("data-a11y-passo");
      var max = +bloco.getAttribute("data-max");
      var valor = est[nome] || 0;
      var pontos = bloco.querySelector(".a11y-pontos");
      pontos.innerHTML = "";
      for (var i = 0; i <= max; i++) {
        var p = document.createElement("i");
        if (i <= valor) p.className = "on";
        pontos.appendChild(p);
      }
      bloco.querySelector("[data-passo='-']").disabled = valor <= +bloco.getAttribute("data-min");
      bloco.querySelector("[data-passo='+']").disabled = valor >= max;
      var eco = bloco.querySelector("[data-valor]");
      if (eco) eco.textContent = valor ? (PT ? "nível " : "level ") + valor : "";
    });
    $$("[data-a11y-opcoes]").forEach(function (bloco) {
      var nome = bloco.getAttribute("data-a11y-opcoes");
      var atual = nome === "satur" ? String(est.satur) : String(est[nome === "daltmodo" ? "daltmodo" : nome]);
      $$("button", bloco).forEach(function (b) {
        b.setAttribute("aria-checked", b.value === atual ? "true" : "false");
      });
    });
    $$("[data-a11y-sub]").forEach(function (bloco) {
      bloco.hidden = !est[bloco.getAttribute("data-a11y-sub")];
    });
  }

  function aplicarTudo() {
    aplicarFonte();
    vigiarDom(est.fonte > 0);
    marca("linhas", est.linhas);
    marca("letras", est.letras);
    marca("links", est.links);
    marca("teclado", est.teclado);
    marca("dic", est.dic);
    aplicarCores();
    ligarLupa(est.lupa);
    if (est.dic) document.addEventListener("dblclick", aoDoisCliques);
    else { document.removeEventListener("dblclick", aoDoisCliques); fecharVerbete(); }
    if (est.estrutura) desenharMapa();
    if (est.libras && temCookieLibras()) montarLibras();
    sincronizar();
    salvar();
  }

  /* ====================================================================
     Ligações da interface
     ==================================================================== */
  /* No Mac não existe tecla escrita "Alt": é a Option, marcada ⌥. Mostrar
     "ALT + A" para quem está num MacBook manda a pessoa procurar uma tecla que
     não está no teclado dela. */
  var ehMac = (function () {
    // navigator.userAgentData é o caminho atual e o único que os navegadores
    // se comprometem a manter. navigator.platform está obsoleto e um dia vai
    // congelar num valor fixo; fica só como reserva, junto do user agent, para
    // Safari e Firefox, que ainda não implementam o primeiro.
    var moderno = navigator.userAgentData && navigator.userAgentData.platform;
    if (moderno) return /mac/i.test(moderno);
    return /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent || "");
  })();
  var MOD = ehMac ? "⌥︎ Option" : "Alt";
  $$("[data-tecla-mod]").forEach(function (k) { k.textContent = MOD; });
  // Teclado Apple não tem tecla escrita "Enter": num MacBook ela se chama
  // "return". Mandar procurar Enter ali é o mesmo erro do Alt.
  $$("[data-tecla-enter]").forEach(function (k) { k.textContent = ehMac ? "⏎︎ return" : "Enter"; });
  var dica = $("[data-tecla-dica]");
  if (dica) dica.textContent = ehMac
    ? (PT ? "No Mac, a tecla é a Option (⌥︎), do lado da barra de espaço."
          : "On a Mac this is the Option key (⌥︎), next to the space bar.")
    : (PT ? "A tecla Alt fica dos dois lados da barra de espaço."
          : "The Alt key sits on both sides of the space bar.");
  var lembrete = $(".a11y-kbd");
  if (lembrete) lembrete.textContent = (ehMac ? "⌥︎" : "ALT") + " + A";

  var painel = $(".a11y-painel");
  var gatilho = $(".a11y-trigger");
  var veu = document.createElement("div");
  veu.className = "a11y-veu";
  document.body.appendChild(veu);

  painel.removeAttribute("hidden");
  painel.inert = true;

  function abrirPainel(abre) {
    painel.classList.toggle("aberto", abre);
    veu.classList.toggle("aberto", abre);
    painel.inert = !abre;
    gatilho.setAttribute("aria-expanded", abre ? "true" : "false");
    if (abre) {
      if (est.estrutura) desenharMapa();
      setTimeout(function () { var x = $(".a11y-x"); if (x) x.focus(); }, 60);
    } else {
      gatilho.focus();
    }
  }

  gatilho.addEventListener("click", function () { abrirPainel(!painel.classList.contains("aberto")); });
  $(".a11y-x").addEventListener("click", function () { abrirPainel(false); });
  veu.addEventListener("click", function () { abrirPainel(false); });

  $$("[data-a11y-alterna]").forEach(function (b) {
    b.addEventListener("click", function () {
      var nome = b.getAttribute("data-a11y-alterna");
      est[nome] = !est[nome];
      if (nome === "libras") { salvar(); alternarLibras(est.libras); return; }
      if (nome === "estrutura" && est.estrutura) desenharMapa();
      aplicarTudo();
    });
  });

  $$("[data-a11y-passo]").forEach(function (bloco) {
    var nome = bloco.getAttribute("data-a11y-passo");
    var min = +bloco.getAttribute("data-min"), max = +bloco.getAttribute("data-max");
    $$("[data-passo]", bloco).forEach(function (b) {
      b.addEventListener("click", function () {
        var d = b.getAttribute("data-passo") === "+" ? 1 : -1;
        est[nome] = Math.min(max, Math.max(min, (est[nome] || 0) + d));
        aplicarTudo();
      });
    });
  });

  $$("[data-a11y-opcoes]").forEach(function (bloco) {
    var nome = bloco.getAttribute("data-a11y-opcoes");
    $$("button", bloco).forEach(function (b) {
      b.addEventListener("click", function () {
        est[nome] = nome === "satur" ? +b.value : b.value;
        if (nome === "contraste") est.contraste = +b.value;
        aplicarTudo();
      });
    });
  });

  $$("[data-aba]").forEach(function (b) {
    b.addEventListener("click", function () {
      abaAtual = b.getAttribute("data-aba");
      $$("[data-aba]").forEach(function (o) { o.setAttribute("aria-selected", o === b ? "true" : "false"); });
      desenharMapa();
    });
  });

  $$("[data-a11y-quick]").forEach(function (b) {
    b.addEventListener("click", function () {
      var nome = b.getAttribute("data-a11y-quick");
      if (nome === "fonte") est.fonte = (est.fonte + 1) % ESCALA.length;
      else if (nome === "contraste") est.contraste = (est.contraste + 1) % 3;
      else if (nome === "libras") { est.libras = !est.libras; salvar(); return alternarLibras(est.libras); }
      aplicarTudo();
    });
  });

  $(".a11y-reset").addEventListener("click", function () {
    var tinhaLibras = est.libras;
    for (var k in PADRAO) est[k] = PADRAO[k];
    aplicarTudo();
    if (tinhaLibras) alternarLibras(false);
  });

  document.addEventListener("keydown", function (e) {
    // e.code é a tecla física; e.key é o caractere que ela produz. No Mac,
    // Option+A não produz "a", produz "å" — era por isso que o atalho não
    // funcionava lá. Com o code, funciona em qualquer teclado e idioma.
    if (e.altKey && !e.ctrlKey && !e.metaKey) {
      if (e.code === "KeyA") {
        e.preventDefault();
        abrirPainel(!painel.classList.contains("aberto"));
        return;
      }
      if (e.code === "KeyC") {
        e.preventDefault();
        var conteudo = document.getElementById("main") || document.querySelector("main");
        if (conteudo) irPara(conteudo);
        return;
      }
    }
    if (e.key !== "Escape") return;
    if (verbete.classList.contains("on")) return fecharVerbete();
    if (painel.classList.contains("aberto")) abrirPainel(false);
  });

  // rolar fecha o verbete: ele fica ancorado num ponto da tela
  addEventListener("scroll", function () {
    if (verbete.classList.contains("on")) fecharVerbete();
  }, { passive: true });

  aplicarTudo();
})();
