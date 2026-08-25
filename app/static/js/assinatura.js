/* Assinatura no botão direito, em todo o site.
 *
 * Fica em arquivo próprio porque nem toda página herda o base.html: a de construção
 * e a de descadastro são autônomas de propósito, para não vazarem o layout do site.
 * Qualquer página nova precisa carregar este arquivo.
 *
 * Vale dizer sem rodeio: isto não protege imagem nem texto. Quem quiser copiar usa o
 * menu do navegador, as ferramentas de desenvolvedor ou uma captura de tela. O que
 * isto faz é assinar o gesto, como uma marca d'água de comportamento.
 */
(function () {
  "use strict";

  // Espaço do aluno do Nodal (spec §17, adendo "sem aviso de proteção de
  // conteúdo no espaço do aluno", pedido do Leandro no fim da Tarefa 10):
  // o aluno pagou pelo conteúdo, o bloco de prompt já tem um botão
  // "Copiar" oficial (ver _blocos.html::bloco_prompt), e imprimir é
  // recurso da própria plataforma (folha de impressão da Tarefa 9) — o
  // aviso ali só constrangeria quem está usando o produto do jeito certo.
  // `data-aviso="off"` é o gancho, decidido no SERVIDOR (mesmo padrão de
  // `data-tips`/`data-preloader`, ver app/main.py::render() e
  // _base_nodal.html) — checado uma vez só aqui, e usado dentro de
  // `avisar()` mais abaixo, o ÚNICO funil por onde os quatro gatilhos do
  // aviso (PrintScreen, heurística de captura no Mac, copiar, afterprint)
  // passam. O chip de assinatura do clique direito (`.rc-chip`, abaixo)
  // NÃO É o "aviso de proteção" que a regra desliga — é outra coisa (uma
  // marca d'água de comportamento, não um recado de constrangimento) e o
  // pedido não citou ele; continua ativo em toda página, aluno incluso.
  var AVISO_DESLIGADO = document.body.dataset.aviso === "off";

  // onde o menu do navegador continua sendo útil e bloquear só atrapalharia
  var LIVRE = "input, textarea, select, [contenteditable], a[href]";
  var chip = null;
  var sumir = null;

  document.addEventListener("contextmenu", function (e) {
    if (e.target.closest && e.target.closest(LIVRE)) return;
    e.preventDefault();

    if (!chip) {
      chip = document.createElement("div");
      chip.className = "rc-chip";
      chip.setAttribute("aria-hidden", "true");
      chip.innerHTML = '<i>✳︎</i><span>// Leandro Furtado</span>';
      document.body.appendChild(chip);
    }

    var largura = 190, altura = 44;
    var x = Math.min(e.clientX, window.innerWidth - largura - 12);
    var y = Math.min(e.clientY, window.innerHeight - altura - 12);
    chip.style.left = Math.max(12, x) + "px";
    chip.style.top = Math.max(12, y) + "px";

    chip.classList.remove("on");
    void chip.offsetWidth;        // reinicia a animação em cliques seguidos
    chip.classList.add("on");

    clearTimeout(sumir);
    sumir = setTimeout(function () { chip.classList.remove("on"); }, 1600);
  });

  /* No celular o botão direito não existe: o gesto é o toque longo. O Android
     dispara contextmenu e cai na regra acima, mas o Safari do iPhone abre a folha
     de compartilhamento sem disparar evento nenhum. Sem isto, quem quisesse salvar
     uma imagem pelo iPhone passava direto por tudo que está aqui. */
  document.addEventListener("dragstart", function (e) {
    if (e.target.tagName === "IMG") e.preventDefault();
  });

  /* ------------------------------------------------------------------
     Recado de captura de tela.

     Não existe API que avise "esta pessoa tirou um print" — os navegadores
     escondem isso de propósito, e ainda bem: seria mais uma forma de vigiar
     quem visita. O que dá para ler é o atalho de teclado, e só ele:

       Mac      ⌘ + Shift + 3, 4 ou 5   → chega, testado
       Windows  PrintScreen             → costuma chegar no keyup
       Windows  ⊞ + Shift + S           → o sistema quase sempre engole antes

     Fica de fora, sem remédio possível: print de celular pelos botões
     físicos, ferramenta de recorte aberta pelo menu, extensão de navegador e
     foto da tela com outro aparelho. Ou seja, pega boa parte de quem está no
     computador e nada de quem está no celular.
     ------------------------------------------------------------------ */

  var PT = (document.documentElement.lang || "pt").toLowerCase().indexOf("en") !== 0;
  /* Três gestos levam conteúdo do site embora: capturar a tela, copiar um
     trecho e imprimir. Cada um tem o seu ícone e o seu texto, porque uma frase
     genérica que servisse aos três não soaria como ninguém falando. */
  var COMUM = PT
    ? { ola: "Ei jovem!", abraco: "Um abraço, Leandro Furtado.", botao: "Voltar para o site" }
    : { ola: "Hey there!", abraco: "A hug, Leandro Furtado.", botao: "Back to the site" };

  var CASOS = PT ? {
    print: {
      rotulo: "Captura de tela",
      corpo: "Para você tirar um print agora, você gostou mesmo do meu site hein? ;)",
      uso: "Se usar com respeito e bom senso essa captura de tela, vai ser lindo de viver."
    },
    copia: {
      rotulo: "Trecho copiado",
      corpo: "Você copiou um pedaço do meu site. Fico feliz que tenha servido pra alguma coisa! ;)",
      uso: "Se usar com respeito e bom senso esse conteúdo, vai ser lindo de viver."
    },
    imprimir: {
      rotulo: "Impressão",
      corpo: "Vai imprimir ou salvar em PDF? Então gostou mesmo do meu site hein? ;)",
      uso: "Se usar com respeito e bom senso essas páginas, vai ser lindo de viver."
    }
  } : {
    print: {
      rotulo: "Screenshot",
      corpo: "Taking a screenshot right now means you really liked my site, right? ;)",
      uso: "Use this screenshot with respect and good sense and it will be a beautiful thing."
    },
    copia: {
      rotulo: "Copied text",
      corpo: "You just copied a piece of my site. Glad it was useful! ;)",
      uso: "Use this content with respect and good sense and it will be a beautiful thing."
    },
    imprimir: {
      rotulo: "Printing",
      corpo: "Printing or saving as PDF? So you really liked my site, right? ;)",
      uso: "Use these pages with respect and good sense and it will be a beautiful thing."
    }
  };

  var ICONES = {
    print: '<path d="M3 8.6a2 2 0 0 1 2-2h2.2l1.3-2.1h6.9l1.3 2.1H19a2 2 0 0 1 2 2v8.8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8.6z"/>' +
           '<circle cx="12" cy="12.8" r="3.6"/>',
    copia: '<rect x="9" y="9" width="11.4" height="11.4" rx="2"/>' +
           '<path d="M5.4 15H4.6a2 2 0 0 1-2-2V5.6a2 2 0 0 1 2-2H12a2 2 0 0 1 2 2v.8"/>',
    imprimir: '<path d="M6.4 9.4V3.6h11.2v5.8"/>' +
              '<path d="M6.4 17.6H5a2 2 0 0 1-2-2v-4.2a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4.2a2 2 0 0 1-2 2h-1.4"/>' +
              '<rect x="6.4" y="14.2" width="11.2" height="6.2" rx="1"/>'
  };

  var modal = null;
  var focoAnterior = null;

  function montar() {
    modal = document.createElement("div");
    modal.className = "sc-veu";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.innerHTML =
      '<div class="sc-card">' +
        '<div class="sc-topo">' +
          '<svg viewBox="0 0 100 100" class="sc-mark" aria-hidden="true">' +
            '<polygon points="57.6 73.8 30.6 73.8 30.6 35.7 40 35.7 40 63.9 59.5 63.9 57.6 73.8"/>' +
            '<polygon points="64.9 54.5 49.4 54.5 49.4 45.1 66.6 45.1 64.9 54.5"/>' +
            '<polygon points="67.6 35.7 49.4 35.7 49.4 26.3 69.4 26.3 67.6 35.7"/>' +
          "</svg>" +
          '<span class="sc-risco" aria-hidden="true"></span>' +
          '<svg viewBox="0 0 24 24" class="sc-cam" aria-hidden="true" fill="none" ' +
               'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
          "</svg>" +
        "</div>" +
        '<span class="sc-rotulo"></span>' +
        "<h2>" + COMUM.ola + "</h2>" +
        '<span class="sc-linha" aria-hidden="true"></span>' +
        "<p class='sc-corpo'></p>" +
        '<p class="sc-uso"></p>' +
        '<p class="sc-abraco">' + COMUM.abraco + "</p>" +
        '<button type="button" class="sc-btn">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" ' +
               'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M19 12H5"/><path d="m11 6-6 6 6 6"/>' +
          "</svg>" +
          "<span>" + COMUM.botao + "</span>" +
        "</button>" +
      "</div>";
    document.body.appendChild(modal);

    modal.addEventListener("click", function (e) {
      if (e.target === modal || e.target.closest(".sc-btn")) fechar();
    });
  }

  function vestir(qual) {
    var caso = CASOS[qual] || CASOS.print;
    modal.setAttribute("aria-label", caso.rotulo);
    modal.querySelector(".sc-cam").innerHTML = ICONES[qual] || ICONES.print;
    modal.querySelector(".sc-rotulo").textContent = caso.rotulo;
    modal.querySelector(".sc-corpo").textContent = caso.corpo;
    modal.querySelector(".sc-uso").textContent = caso.uso;
  }

  function fechar() {
    if (!modal) return;
    modal.classList.remove("on");
    document.documentElement.style.overflow = "";
    if (focoAnterior && focoAnterior.focus) {
      try { focoAnterior.focus(); } catch (e) { /* saiu da página */ }
    }
  }

  function mostrar(qual) {
    // uma vez por visita: quem tira cinco prints não precisa de cinco recados
    try {
      if (sessionStorage.getItem("lf-print")) return;
      sessionStorage.setItem("lf-print", "1");
    } catch (e) { /* modo privado: mostra assim mesmo, uma vez por página */ }

    if (!modal) montar();
    vestir(qual);
    focoAnterior = document.activeElement;
    modal.classList.add("on");
    document.documentElement.style.overflow = "hidden";
    var botao = modal.querySelector(".sc-btn");
    if (botao) setTimeout(function () { botao.focus(); }, 420);
  }

  /* O recado espera a captura acontecer. Aparecer na hora colocaria o próprio
     modal dentro do print, e a pessoa levaria a mensagem em vez do conteúdo
     que queria guardar. */
  function avisar(qual) {
    if (AVISO_DESLIGADO) return;
    setTimeout(function () { mostrar(qual); }, 900);
  }

  /* Windows: o PrintScreen chega ao navegador de verdade, normalmente no
     soltar da tecla. É o único caso em que dá para ler a tecla direto. */
  document.addEventListener("keyup", function (e) {
    if (e.key === "PrintScreen" || e.code === "PrintScreen") avisar("print");
  }, true);

  /* Mac e Windows com ferramenta de recorte: a tecla nunca chega.
     ⌘⇧3, ⌘⇧4, ⌘⇧5 e ⊞⇧S são atalhos do sistema, e o sistema os consome antes
     de qualquer aplicativo. Ler e.key ali é esperar por um evento que não vem.

     O que ainda dá para observar é o efeito colateral: ⌘⇧4, ⌘⇧5 e ⊞⇧S abrem
     uma interface do próprio sistema, e nesse instante a janela do navegador
     perde o foco. Sozinho isso não diz nada (trocar de aplicativo faz o mesmo),
     mas perder o foco logo depois de Cmd+Shift ficarem pressionados é um
     desenho bem específico.

     ⌘⇧3 captura a tela inteira na hora, sem interface e sem trocar o foco.
     Esse não deixa rastro nenhum e não há como pegar. */
  var armado = 0;
  document.addEventListener("keydown", function (e) {
    if (e.metaKey && e.shiftKey) armado = Date.now();
  }, true);

  function talvezCaptura() {
    if (!armado || Date.now() - armado > 1800) return;
    armado = 0;
    avisar("print");
  }
  window.addEventListener("blur", talvezCaptura);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) talvezCaptura();
  });

  /* ------------------------------------------------------------------
     Os dois gestos que funcionam em todo sistema, Mac incluído.

     Como a captura de tela é invisível para a web no Mac, o recado ficaria
     só para quem usa Windows. Copiar e imprimir são as outras duas formas de
     levar conteúdo daqui, e essas o navegador conta sem esconder nada.
     ------------------------------------------------------------------ */

  var MINIMO_COPIA = 120;   // e-mail, telefone e um nome não acionam nada

  document.addEventListener("copy", function () {
    var sel = window.getSelection();
    if (!sel) return;
    var texto = String(sel).trim();
    if (texto.length < MINIMO_COPIA) return;
    // quem copia o que digitou num formulário está copiando o próprio texto
    var no = sel.anchorNode;
    var el = no && (no.nodeType === 1 ? no : no.parentElement);
    if (el && el.closest && el.closest("input, textarea, [contenteditable]")) return;
    avisar("copia");
  });

  /* O recado sai depois de imprimir, nunca antes: aberto durante a impressão
     ele entraria no papel, e a pessoa levaria a mensagem impressa junto. */
  window.addEventListener("afterprint", function () { avisar("imprimir"); });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal && modal.classList.contains("on")) fechar();
  });
})();
