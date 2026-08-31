/* ==========================================================================
   Grupo OM: o movimento das CINCO páginas.

   A PILHA é a das cinco referências que o Leandro escolheu (tema Rayo), e a
   descoberta que a decidiu é que aquele tema não usa React nem three.js: o
   que ele chama de "nível Awwwards" é GSAP mais Lenis. Os quatro arquivos já
   estavam vendorizados aqui, e nenhum host externo é tocado.

   AS QUATRO REGRAS QUE ESTE ARQUIVO NÃO QUEBRA:

   1. O movimento entra DEPOIS do conteúdo, nunca antes. Todo estado inicial
      de revelação vem da classe `om-js`, posta no `<head>` antes da primeira
      pintura (o mesmo `_cabeca.html` nas cinco páginas), e essa classe cai
      sozinha em 2,5 s se este arquivo não chegar.
      Aqui, a primeira coisa que se faz é cancelar aquele relógio; a última
      é uma varredura de segurança que devolve qualquer elemento que ainda
      esteja invisível. Uma proposta comercial não pode ficar em branco
      porque um JS de 72 KB não carregou.

   2. `prefers-reduced-motion` desliga o MOVIMENTO, e não o site. O script do
      `<head>` sequer põe `om-js` nesse caso, e a SEGUNDA METADE deste arquivo
      devolve ali mesmo: o Lenis nunca é criado, nenhuma revelação é armada,
      nenhuma fita corre. Rolagem suave é justamente o que mais incomoda quem
      pediu menos movimento, e desligar isso por `transition-duration: 0` não
      funcionaria.

      A PRIMEIRA METADE, essa, roda sempre. Menu de tela cheia, botões de
      compartilhar, estado do cabeçalho e trava de rolagem são FUNÇÃO, e até
      26/08 o arquivo inteiro devolvia na primeira linha: quem pedia menos
      movimento perdia o índice do site de treze páginas junto com a
      animação. Eram duas coisas sem relação nenhuma, e agora são dois blocos.

   3. Nada de `type: "chars"` no SplitText. Cortar caractere reescreve a
      quebra da manchete, e a manchete destas páginas quebra por causa de um
      `clamp` medido: em 110 px, um caractere a mais por linha muda o desenho
      da dobra inteira. `type: "lines"` respeita o que o navegador decidiu, e
      `autoSplit` refaz o corte quando a janela muda.

   4. Nenhuma animação de propriedade de layout. Só `transform` e `opacity`.
   ========================================================================== */
(function () {
  "use strict";

  var raiz = document.documentElement;
  var lenis = null;

  /* IR PARA UM PONTO, com ou sem Lenis.

     O Lenis toma conta da rolagem: ele mantém a posição num valor próprio e a
     escreve a cada quadro. Um `href="#topo"` do navegador move a página, o
     Lenis não fica sabendo, e no quadro seguinte ele escreve a posição antiga
     de volta. Era exatamente isso que fazia o botão "ao topo" não fazer nada:
     ele funcionava por um quadro.

     Com Lenis no ar, quem move é o Lenis. Sem ele, o navegador. */
  var irPara = function (destino) {
    /* QUARTA VERSÃO deste helper, e desta vez a rolagem é NOSSA.

       A história inteira, porque ela explica por que não se delega mais:
       1. `window.scrollTo({behavior:"smooth"})` não move com o Lenis no ar —
          o laço dele reescreve a posição a cada quadro e ganha a disputa.
       2. `lenis.scrollTo` falha calado quando o estado interno dele
          dessincroniza da posição real (medido: anda 24 px e estanca).
       3. A rede de segurança que cobria o caso 2 dava um SALTO SECO, e salto
          seco não é "voltar suavemente ao topo" (Leandro, 27/08).

       Então: o Lenis PARA, esta função anima a posição com o easing da
       própria peça, e no fim devolve a posição ao Lenis já sincronizada.
       Nenhuma disputa, nenhum estado alheio, nenhum salto. */
    var raiz = document.documentElement;
    var posicao = function () {
      return window.pageYOffset || raiz.scrollTop || 0;
    };
    var alvoY = typeof destino === "number"
      ? destino
      : (destino ? destino.getBoundingClientRect().top + posicao() : 0);
    var inicio = posicao();
    if (Math.abs(alvoY - inicio) < 2) { return; }
    if (lenis && typeof lenis.stop === "function") { lenis.stop(); }
    /* Quem prefere movimento reduzido vai direto: a suavidade é justamente o
       movimento que essa pessoa pediu para não ver. */
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      window.scrollTo({ top: alvoY, behavior: "instant" });
      if (lenis && typeof lenis.scrollTo === "function") {
        lenis.scrollTo(alvoY, { immediate: true });
      }
      if (lenis && typeof lenis.start === "function") { lenis.start(); }
      return;
    }
    /* Duração proporcional à distância, com piso e teto: 4000 px em 1,1 s e
       400 px em 0,45 s são a mesma sensação de velocidade. */
    var dur = Math.min(1100, Math.max(450, Math.abs(alvoY - inicio) * .28));
    var t0 = null;
    var terminou = false;
    var passo = function (agora) {
      if (terminou) { return; }
      if (t0 === null) { t0 = agora; }
      var p = Math.min(1, (agora - t0) / dur);
      var suave = 1 - Math.pow(1 - p, 3);   /* easeOutCubic, a curva da peça */
      window.scrollTo(0, inicio + (alvoY - inicio) * suave);
      if (p < 1) {
        window.requestAnimationFrame(passo);
      } else {
        terminou = true;
        /* Devolve a posição ao Lenis JÁ SINCRONIZADA, senão o primeiro
           quadro dele traria a página de volta para onde ela estava. */
        if (lenis && typeof lenis.scrollTo === "function") {
          lenis.scrollTo(alvoY, { immediate: true });
        }
        if (lenis && typeof lenis.start === "function") { lenis.start(); }
      }
    };
    window.requestAnimationFrame(passo);
    /* A REDE, versão final: se o `requestAnimationFrame` não correu (aba de
       fundo, navegador economizando quadros), a página estaria parada COM o
       Lenis parado — travada. O prazo é a duração mais meio segundo; se a
       animação terminou, isto aqui não faz nada. */
    window.setTimeout(function () {
      if (terminou) { return; }
      terminou = true;
      window.scrollTo({ top: alvoY, behavior: "instant" });
      if (lenis && typeof lenis.scrollTo === "function") {
        lenis.scrollTo(alvoY, { immediate: true });
      }
      if (lenis && typeof lenis.start === "function") { lenis.start(); }
    }, dur + 500);
  };

  /* ====================================================================
     PRIMEIRA METADE: FUNÇÃO. Roda SEMPRE.

     Esta separação foi feita em 26/08, e o motivo é o item 5. O menu de tela
     cheia é o único lugar onde o site de treze páginas se vê inteiro, e até
     esta rodada o arquivo devolvia na primeira linha quando `om-js` não
     existia. `om-js` não existe quando a pessoa pediu MENOS MOVIMENTO, e
     recusar o índice do site a quem pediu menos movimento é confundir duas
     coisas que não têm relação nenhuma.

     A regra que fica: movimento é opcional, função não é. Menu, botões de
     compartilhar, estado do cabeçalho e trava de rolagem vivem aqui em cima e
     não dependem de GSAP nenhum. A revelação por rolagem, as fitas, o corte
     dos títulos e a rolagem suave vivem na segunda metade, atrás da guarda.
     ==================================================================== */

  var querMovimento = raiz.className.indexOf("om-js") >= 0;

  /* ------------------------------------------------- menu de tela cheia --
     ITEM 5. Esc fecha, clique fora fecha, o foco fica preso enquanto está
     aberto, e ao fechar ele volta para o botão que abriu, que é a parte que
     quase todo menu de agência esquece: sem isso, quem navega por teclado é
     devolvido ao começo do documento e precisa tabular a página inteira de
     novo.

     O menu nasce `hidden` e `inert` no HTML. Só aqui ele deixa de estar, e é
     por isso que o botão também nasce `hidden`: enquanto este trecho não
     roda, não existe menu para abrir e não existe botão que o prometa. */
  /* ------------------------------------------- a altura do cabeçalho --
     `--alt-cab` decide onde o herói termina: ele sobe por trás do cabeçalho
     por margem negativa dessa medida e mede `100svh`. Se o número mentir para
     mais, sobra uma faixa da seção seguinte no pé da primeira dobra; para
     menos, o herói passa da tela.

     O CSS traz três valores medidos à mão (113, 91 e 106 px), e eles JÁ
     DERIVARAM: em 27/08 a barra do arco-íris caiu de 8 px para 4, o botão
     perdeu o rótulo, e o cabeçalho passou a medir 101,56 contra os 106
     declarados. O resultado foi uma tira branca de 4,44 px no pé da tela, que
     o Leandro viu antes de qualquer teste.

     Aqui a medida deixa de ser estimativa. Os valores do CSS continuam
     existindo como piso para quem não tem script, onde eles são o melhor
     palpite possível; com script, o número vem do navegador. */
  var cabecalhoParaMedir = document.querySelector("[data-cabecalho]");
  /* O DONO DA VARIÁVEL é quem a declara no CSS, e ela é declarada em
     `.rd-grupo-om`, que é o `<body>`. Escrever no `<html>` não adianta: o
     valor herdado perde para a regra do filho, e a medida certa fica sem
     efeito. Medido em 27/08: o script escrevia 101,56 px no `<html>` e a
     margem do herói continuava calculando com os 106 px do CSS, deixando a
     mesma tira branca de 4,44 px no pé da tela. */
  var donoDaAltura = document.querySelector(".rd-grupo-om") || raiz;
  if (cabecalhoParaMedir) {
    var medirCabecalho = function () {
      var alt = cabecalhoParaMedir.getBoundingClientRect().height;
      if (alt > 0) { donoDaAltura.style.setProperty("--alt-cab", alt.toFixed(2) + "px"); }
    };
    medirCabecalho();
    window.addEventListener("resize", medirCabecalho, { passive: true });
    /* As fontes chegam depois do primeiro cálculo e mudam a altura do menu em
       linha. Sem esta segunda medida, o número certo seria o de antes delas. */
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(medirCabecalho);
    }
  }

  var menu = document.querySelector("[data-menu]");
  var abre = document.querySelector("[data-menu-alterna]");
  if (menu && abre) {
    raiz.classList.add("om-menu-pronto");
    abre.hidden = false;
    var aberto = false;

    var focaveis = function () {
      return menu.querySelectorAll('a[href], button:not([disabled])');
    };

    /* A CASCATA das colunas: o atraso de cada uma é a posição dela, escrita
       uma vez só. Fazer isso aqui, e não no template, mantém a regra ao lado
       da animação que a usa. */
    var colunas = menu.querySelectorAll(".om-menu-caixa, .om-menu-arte, .om-menu-pe");
    for (var ci = 0; ci < colunas.length; ci++) {
      colunas[ci].style.setProperty("--ordem", String(ci));
    }
    /* E a ordem de cada LINHA do índice, que é a cascata da fresta. */
    var linhas = menu.querySelectorAll(".om-menu-paginas li");
    for (var li = 0; li < linhas.length; li++) {
      linhas[li].style.setProperty("--linha", String(li));
    }

    /* --------------------------------------------------- a arte sorteada --
       A coluna de imagem troca a cada abertura, sorteando entre os cases que
       a peça já carrega. Nenhum arquivo novo, nenhuma foto de banco: o menu
       mostra TRABALHO enquanto a pessoa decide para onde ir.

       A primeira imagem vem do servidor, para a coluna nunca aparecer vazia;
       daqui para frente quem escolhe é isto. Evita repetir a que está na
       tela, porque sortear a mesma duas vezes seguidas parece defeito. */
    var arte = menu.querySelector("[data-menu-arte]");
    var sortearArte = function () {
      if (!arte) { return; }
      var lista = (arte.getAttribute("data-menu-arte") || "").split(",").filter(Boolean);
      if (lista.length < 2) { return; }
      var img = arte.querySelector("img");
      if (!img) { return; }
      var nova = img.getAttribute("src");
      var voltas = 0;
      while (nova === img.getAttribute("src") && voltas < 12) {
        nova = lista[Math.floor(Math.random() * lista.length)];
        voltas++;
      }
      img.setAttribute("src", nova);
    };

    var relogioDoFecho = null;

    var fechar = function (devolverFoco) {
      if (!aberto) { return; }
      aberto = false;
      abre.setAttribute("aria-expanded", "false");
      /* `inert` JÁ, e `hidden` só no fim: enquanto a saída acontece o painel
         precisa continuar visível, mas não pode mais receber foco nem clique.
         Um menu que ainda aceita Tab enquanto some é um menu invisível com
         foco dentro. */
      menu.setAttribute("inert", "");
      menu.classList.remove("om-menu-abrindo");
      menu.classList.add("om-menu-fechando");
      raiz.classList.remove("om-travado");
      if (lenis) { lenis.start(); }
      if (devolverFoco) { abre.focus(); }

      window.clearTimeout(relogioDoFecho);
      /* O relógio, e não `transitionend`: `transitionend` não dispara quando
         a duração é zero, que é exatamente o caso de quem pediu menos
         movimento. O menu ficaria visível para sempre justamente para quem
         menos deveria vê-lo se mexendo. */
      /* .5 s de subida mais .175 s de cascata da última faixa. */
      var espera = querMovimento ? 700 : 0;
      relogioDoFecho = window.setTimeout(function () {
        if (aberto) { return; }
        menu.hidden = true;
        menu.classList.remove("om-menu-fechando");
      }, espera);
    };

    var abrir = function () {
      if (aberto) { return; }
      aberto = true;
      window.clearTimeout(relogioDoFecho);
      menu.classList.remove("om-menu-fechando");
      menu.hidden = false;
      menu.removeAttribute("inert");
      abre.setAttribute("aria-expanded", "true");
      /* Mede a barra ANTES de travar: depois de `overflow: hidden` ela já
         sumiu e a conta daria zero. */
      var barra = window.innerWidth - raiz.clientWidth;
      raiz.style.setProperty("--barra-rolagem", (barra > 0 ? barra : 0) + "px");
      raiz.classList.add("om-travado");
      if (lenis) { lenis.stop(); }
      /* REFLUXO FORÇADO, e não `requestAnimationFrame`.

         O navegador precisa ter CALCULADO o estado fechado antes de receber o
         estado aberto, senão ele vê os dois no mesmo quadro, não encontra
         diferença para interpolar, e o menu aparece pronto. A forma canônica
         de pedir esse cálculo é ler uma medida que obrigue o layout a
         acontecer: `offsetHeight` faz isso, aqui, agora, de forma síncrona.

         Eu tinha escrito dois `requestAnimationFrame` aninhados, que é a
         receita mais citada para isto. Medido no Chrome do Leandro em 27/08:
         a classe NUNCA era aplicada, nem depois de um segundo e meio. O menu
         abria sem nenhuma animação. Uma leitura de layout não depende de
         quadro nenhum ser agendado. */
      sortearArte();
      void menu.offsetHeight;
      menu.classList.add("om-menu-abrindo");
      var alvos = focaveis();
      if (alvos.length) { alvos[0].focus(); }
    };

    /* UM BOTÃO SÓ, e ele alterna: é o que garante que o X esteja na mesma
       posição do hambúrguer, porque é o mesmo elemento. */
    abre.addEventListener("click", function () {
      if (aberto) { fechar(true); } else { abrir(); }
    });

    var fechadores = menu.querySelectorAll("[data-menu-fecha]");
    for (var x = 0; x < fechadores.length; x++) {
      fechadores[x].addEventListener("click", function () { fechar(true); });
    }

    /* Um link clicado fecha o menu. Ele é um índice, e um índice que continua
       por cima da página que ele acabou de abrir é uma cortina. */
    var elos = menu.querySelectorAll("a[href]");
    for (var e = 0; e < elos.length; e++) {
      elos[e].addEventListener("click", function () { fechar(false); });
    }

    document.addEventListener("keydown", function (ev) {
      if (!aberto) { return; }
      if (ev.key === "Escape") { fechar(true); return; }
      if (ev.key !== "Tab") { return; }
      /* A ARMADILHA DE FOCO, e ela é feita à mão de propósito: `inert` no
         resto da página seria mais limpo, mas exigiria marcar cada irmão do
         menu, e um irmão novo esquecido abriria um buraco silencioso. Aqui a
         volta é fechada nos dois sentidos com quatro linhas. */
      var alvos = focaveis();
      if (!alvos.length) { return; }
      var primeiro = alvos[0];
      var ultimo = alvos[alvos.length - 1];
      if (ev.shiftKey && document.activeElement === primeiro) {
        ev.preventDefault();
        ultimo.focus();
      } else if (!ev.shiftKey && document.activeElement === ultimo) {
        ev.preventDefault();
        primeiro.focus();
      }
    });
  }

  /* ---------------------------------------------------- compartilhar --
     Os botões da página de case (item 8), e eles são ligados AQUI porque só
     aqui se sabe o que este navegador consegue fazer.

     A REGRA: um botão só aparece depois que o navegador confirma que sabe
     cumprir o que ele promete. `navigator.share` existe no celular e em parte
     dos desktops; a área de transferência exige contexto seguro. Sem nenhum
     dos dois, o bloco inteiro continua `hidden`, e é a decisão certa: botão
     que não faz nada é pior do que botão que não existe, e numa proposta
     comercial ele é pior ainda, porque o dono da agência clica.

     Nada disto fala com host nenhum de fora, que é o ponto: a folha nativa do
     sistema abre o WhatsApp e o e-mail que a pessoa já usa, sem um script de
     rede social carregado na página do cliente.

     E este trecho vive na PRIMEIRA METADE do arquivo, a que roda sempre.
     Compartilhar é função, não movimento: quem pediu menos animação não pediu
     menos site, e num arquivo em que a primeira linha devolvia sem `om-js`
     esses botões teriam sumido justamente para essa pessoa. */
  var caixasDePartilha = document.querySelectorAll("[data-partilha]");
  for (var q = 0; q < caixasDePartilha.length; q++) {
    (function (caixa) {
      var podeEnviar = !!(navigator.share);
      var podeCopiar = !!(navigator.clipboard && navigator.clipboard.writeText);
      if (!podeEnviar && !podeCopiar) { return; }
      caixa.hidden = false;

      var enviar = caixa.querySelector("[data-partilha-nativo]");
      if (enviar && podeEnviar) {
        enviar.hidden = false;
        enviar.addEventListener("click", function () {
          navigator.share({
            title: document.title,
            url: location.href
          }).catch(function () { /* a pessoa fechou a folha: não é erro */ });
        });
      }

      var copiar = caixa.querySelector("[data-partilha-copiar]");
      var rotulo = caixa.querySelector("[data-partilha-rotulo]");
      if (copiar && podeCopiar) {
        copiar.hidden = false;
        copiar.addEventListener("click", function () {
          navigator.clipboard.writeText(location.href).then(function () {
            if (!rotulo) { return; }
            var antes = rotulo.textContent;
            rotulo.textContent = "Endereço copiado";
            setTimeout(function () { rotulo.textContent = antes; }, 2200);
          }).catch(function () { /* permissão negada: o botão só não confirma */ });
        });
      }
    })(caixasDePartilha[q]);
  }

  /* -------------------------------------- cabeçalho e barra de leitura --
     ITENS 1 e 5, e os dois são o mesmo ouvinte de rolagem, de propósito: dois
     ouvintes escrevendo no mesmo quadro é como uma barra de progresso começa
     a tremer junto com um cabeçalho que encolhe.

     A BARRA acesa cresce de 0 a 100% conforme a leitura avança, e ela é
     `transform: scaleX`, nunca `width`: largura é propriedade de layout, e
     animá-la a cada quadro obriga o navegador a recalcular a página inteira
     enquanto a pessoa rola.

     A barra só é MOVIDA quando há movimento a dar. Sem `om-js` o CSS a deixa
     cheia e este trecho não a toca: quem pediu menos movimento recebe o
     arco-íris inteiro, parado, que é como a peça sempre foi.

     O CABEÇALHO, esse, muda em qualquer modo. Não é animação, é estado: sem a
     sombra, uma manchete de 110 px passa por baixo de um cabeçalho preso e as
     duas viram uma coisa só. */
  // ==========================================================================
  // A BUSCA POR TEXTO DA GRADE DE CASES (item 27)
  //
  // O filtro por EMPRESA e por ASSUNTO não está aqui: ele é link com
  // parâmetro, resolvido no servidor, e funciona com o JavaScript desligado.
  // O que mora aqui é só a busca por texto livre, e ela mora aqui por uma
  // razão só: sem `<form>` (Global Constraint 4) e sem script, uma caixa de
  // busca é um campo que não faz nada.
  //
  // Por isso o campo nasce `hidden` no HTML e quem o revela é esta função. A
  // grade já veio COMPLETA e legível do servidor; a busca só esconde linhas
  // dela, e limpar o campo devolve tudo.
  // ==========================================================================
  // ==========================================================================
  // ITEM 26, primeira metade: O MENU DE TELEFONES FECHA AO CLICAR FORA
  //
  // Ele é um `<details>` nativo: abre, fecha, navega por teclado e responde ao
  // Escape sozinho, e é por isso que o telefone continua alcançável com o
  // script fora do ar. O que o elemento NÃO faz sozinho é fechar quando a
  // pessoa clica em qualquer outro lugar da página, e é só isso que o código
  // abaixo acrescenta. Sem ele, o menu fica aberto por cima do conteúdo até
  // alguém voltar e clicar no mesmo botão.
  // ==========================================================================
  var menuDeTelefones = document.querySelector("[data-tel-menu]");
  if (menuDeTelefones) {
    document.addEventListener("click", function (ev) {
      if (menuDeTelefones.open && !menuDeTelefones.contains(ev.target)) {
        menuDeTelefones.open = false;
      }
    });
    // O `<details>` responde ao Escape quando o foco está DENTRO dele; este
    // fecha também quando a pessoa já saiu com o Tab e desistiu.
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && menuDeTelefones.open) { menuDeTelefones.open = false; }
    });
  }

  /* UM MENU DE FILTRO POR VEZ. Dois `<details>` irmãos abrem juntos por
     natureza, e abertos ao mesmo tempo as listas se encavalam. */
  var menusDeFiltro = document.querySelectorAll("[data-menu-filtro]");
  for (var mf = 0; mf < menusDeFiltro.length; mf++) {
    (function (meu) {
      meu.addEventListener("toggle", function () {
        if (!meu.open) { return; }
        for (var o = 0; o < menusDeFiltro.length; o++) {
          if (menusDeFiltro[o] !== meu) { menusDeFiltro[o].open = false; }
        }
      });
    })(menusDeFiltro[mf]);
  }
  if (menusDeFiltro.length) {
    document.addEventListener("click", function (ev) {
      for (var f = 0; f < menusDeFiltro.length; f++) {
        if (menusDeFiltro[f].open && !menusDeFiltro[f].contains(ev.target)) {
          menusDeFiltro[f].open = false;
        }
      }
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") { return; }
      for (var g = 0; g < menusDeFiltro.length; g++) { menusDeFiltro[g].open = false; }
    });
  }

  /* ====================================================== A AURORA =====
     O gradiente em movimento atrás do herói. WebGL cru, sem biblioteca.

     POR QUE NÃO three.js, que foi o que o Leandro sugeriu: ela pesa uns
     150 KB comprimidos, e a pilha de movimento desta peça já custa 145. O
     argumento que vende a proposta é "o seu site entrega de 154 a 266 KB por
     página"; dobrar o peso para desenhar um gradiente destrói a frase. O que
     está aqui embaixo faz o mesmo trabalho em umas quarenta linhas e roda
     inteiro na GPU.

     O DESENHO: quatro manchas de cor da identidade, muito fracas, deslizando
     devagar sobre o grafite. O mouse empurra a mancha mais próxima, com
     atraso, então o movimento parece inércia e não perseguição. Por cima,
     uma vinheta que escurece as bordas, para o texto branco não perder
     contraste em cima de uma mancha clara.

     A COR NUNCA ENCOSTA NA MARCA: isto é fundo de seção, e o cabeçalho fica
     por cima, opaco. É a mesma regra que vale para o arco-íris desde o
     primeiro ciclo. */
  var telaAurora = document.querySelector("[data-aurora]");
  if (telaAurora) {
    var gl = null;
    try {
      gl = telaAurora.getContext("webgl", { alpha: true, antialias: false,
                                            premultipliedAlpha: false })
        || telaAurora.getContext("experimental-webgl");
    } catch (e) { gl = null; }

    if (gl) {
      var VERT = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
      /* `mediump` e não `highp`: um gradiente não precisa de precisão alta, e
         `highp` não existe no fragment shader de parte dos celulares. */
      var FRAG = [
        "precision mediump float;",
        "uniform vec2 res;uniform float t;uniform vec2 mouse;",
        /* Uma mancha é uma distância suavizada. `pow` no fim é o que deixa a
           borda macia em vez de virar um círculo de contorno visível. */
        "float mancha(vec2 uv,vec2 c,float r){",
        "  float d=length((uv-c)*vec2(res.x/res.y,1.0));",
        "  return pow(max(0.0,1.0-d/r),3.0);",
        "}",
        "void main(){",
        "  vec2 uv=gl_FragCoord.xy/res;",
        /* Cada mancha anda numa elipse própria, com períodos que não são
           múltiplos um do outro: assim o conjunto nunca repete um ciclo
           reconhecível. */
        "  vec2 m1=vec2(0.24+0.10*sin(t*0.11),0.72+0.07*cos(t*0.09));",
        "  vec2 m2=vec2(0.72+0.09*cos(t*0.07),0.30+0.08*sin(t*0.13));",
        "  vec2 m3=vec2(0.50+0.13*sin(t*0.05),0.52+0.10*cos(t*0.06));",
        "  vec2 m4=vec2(0.88+0.07*sin(t*0.10),0.80+0.06*cos(t*0.08));",
        /* O MOUSE entra como deslocamento das duas manchas centrais, e não
           como uma quinta mancha presa ao cursor: uma luz colada no ponteiro
           lê como brinquedo; o campo inteiro respondendo lê como material. */
        "  vec2 d=(mouse-vec2(0.5))*0.16;",
        "  m1+=d; m3+=d*1.6;",
        "  vec3 cor=vec3(0.0);",
        /* As cores do arco-íris da identidade, em intensidade baixa: elas
           somam para um cinza levemente colorido, nunca para uma cor chapada. */
        "  cor+=vec3(0.90,0.16,0.09)*mancha(uv,m1,0.62)*0.34;",
        "  cor+=vec3(0.05,0.60,0.58)*mancha(uv,m2,0.58)*0.32;",
        "  cor+=vec3(0.95,0.64,0.00)*mancha(uv,m3,0.70)*0.24;",
        "  cor+=vec3(0.42,0.18,0.56)*mancha(uv,m4,0.52)*0.28;",
        /* VINHETA: escurece as bordas e o pé, que é onde o texto vive. O
           herói tem o kicker no alto e a declaração embaixo, e é ali que o
           contraste precisa sobrar. */
        /* Vinheta MAIS SUAVE do que a primeira versão: com `screen` o que
           sobra nas bordas é o grafite da seção, e não um buraco preto. */
        "  float v=1.0-0.55*pow(length((uv-vec2(0.5))*vec2(1.05,1.15)),1.7);",
        "  cor*=max(0.0,v);",
        /* Grão fino, para o degradê não formar as faixas horizontais que
           gradiente de 8 bits sempre forma numa tela grande. */
        "  float g=fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453);",
        "  cor+=(g-0.5)*0.012;",
        /* Alfa 1 e a intensidade toda na cor: com `screen`, o preto é
           transparente por definição, e mexer no alfa só apagaria a luz. */
        "  gl_FragColor=vec4(cor,1.0);",
        "}"
      ].join("\n");

      var compilar = function (tipo, fonte) {
        var s = gl.createShader(tipo);
        gl.shaderSource(s, fonte);
        gl.compileShader(s);
        return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
      };
      var vs = compilar(gl.VERTEX_SHADER, VERT);
      var fs = compilar(gl.FRAGMENT_SHADER, FRAG);

      if (vs && fs) {
        var prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        gl.useProgram(prog);

        var buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER,
          new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        var loc = gl.getAttribLocation(prog, "p");
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

        var uRes = gl.getUniformLocation(prog, "res");
        var uT = gl.getUniformLocation(prog, "t");
        var uMouse = gl.getUniformLocation(prog, "mouse");

        /* Meia resolução, teto de 1.5. Um gradiente sem uma única borda dura
           não ganha nada com a densidade real de uma tela retina, e pagar
           quatro vezes mais píxeis por quadro num notebook é a diferença
           entre 60 quadros e 30. */
        var dpr = Math.min(window.devicePixelRatio || 1, 1.5) * 0.5;
        var medirTela = function () {
          var w = Math.max(1, Math.round(telaAurora.clientWidth * dpr));
          var h = Math.max(1, Math.round(telaAurora.clientHeight * dpr));
          if (telaAurora.width !== w || telaAurora.height !== h) {
            telaAurora.width = w;
            telaAurora.height = h;
          }
          gl.viewport(0, 0, telaAurora.width, telaAurora.height);
          gl.uniform2f(uRes, telaAurora.width, telaAurora.height);
        };

        var mx = 0.5, my = 0.5, alvoX = 0.5, alvoY = 0.5;
        var pintar = function (tempo) {
          /* O ATRASO é o que dá peso ao movimento: a mancha persegue o alvo a
             6% por quadro, então ela chega depois do ponteiro e para devagar,
             como algo que tem massa. */
          mx += (alvoX - mx) * 0.06;
          my += (alvoY - my) * 0.06;
          gl.uniform2f(uMouse, mx, my);
          gl.uniform1f(uT, tempo);
          gl.drawArrays(gl.TRIANGLES, 0, 3);
        };

        medirTela();
        pintar(0);
        telaAurora.setAttribute("data-pronta", "");

        /* SEM MOVIMENTO: um quadro só, e o laço nunca começa. A imagem
           existe, o movimento não, que é o que `prefers-reduced-motion` pede
           e não "sumir com o fundo". */
        if (querMovimento) {
          var t0 = 0;
          var laco = function (agora) {
            if (!t0) { t0 = agora; }
            pintar((agora - t0) / 1000);
            window.requestAnimationFrame(laco);
          };
          window.requestAnimationFrame(laco);

          window.addEventListener("pointermove", function (ev) {
            var caixa = telaAurora.getBoundingClientRect();
            /* Fora da seção o alvo volta ao centro, senão a aurora fica
               congelada num canto enquanto a pessoa lê o resto da página. */
            if (ev.clientY < caixa.top || ev.clientY > caixa.bottom) {
              alvoX = 0.5; alvoY = 0.5; return;
            }
            alvoX = (ev.clientX - caixa.left) / Math.max(1, caixa.width);
            alvoY = 1 - (ev.clientY - caixa.top) / Math.max(1, caixa.height);
          }, { passive: true });

          window.addEventListener("resize", medirTela, { passive: true });
        }
      }
    }
  }

  var caixaDeBusca = document.querySelector("[data-busca]");
  var campoDeBusca = document.querySelector("[data-busca-campo]");
  if (caixaDeBusca && campoDeBusca) {
    caixaDeBusca.hidden = false;
    var cartoes = document.querySelectorAll(".om-grade-cases > .om-cartao");
    var vazio = document.querySelector("[data-vazio]");
    var conta = document.querySelector("[data-conta-cases]");
    /* O molde sai do `<p>` ANTES da troca abaixo: é nele que o atributo mora. */
    var molde = conta ? (conta.getAttribute("data-molde") || "") : "";
    /* Quem recebe escrita é o `<span>`, e não o `<p>`: desde 27/08 o contador
       carrega um ícone de case antes do texto, e escrever no `textContent`
       do pai apagaria o desenho junto. */
    if (conta) { conta = conta.querySelector("span") || conta; }
    var contaOriginal = conta ? conta.textContent : "";

    // Sem acento e em minúscula dos dois lados: quem digita "campanha
    // integrada" precisa achar "Comunicação Integrada", e ninguém digita
    // cedilha numa caixa de busca.
    var achatar = function (texto) {
      texto = texto.toLowerCase();
      if (texto.normalize) {
        texto = texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      }
      return texto;
    };

    var textoDe = [];
    for (var b = 0; b < cartoes.length; b++) {
      textoDe.push(achatar(cartoes[b].textContent || ""));
    }

    /* ------------------------------------------------------ a paginação --
       SEIS por página (pedido do Leandro, 26/08). Sem requisição: os dezoito
       cartões já vieram do servidor, então trocar de página é mostrar e
       esconder. Um pedido AJAX aqui iria ao servidor buscar o que já está na
       memória do navegador.

       A paginação e a busca são a MESMA função. Filtrar é escolher quais
       cartões entram na lista; paginar é escolher quais dessa lista aparecem
       agora. Escritas separadas, elas se contradizem no primeiro caso de
       borda: buscar estando na página 3 mostraria um recorte vazio de um
       resultado que tem dois itens. */
    var POR_PAGINA = 6;
    var paginacao = document.querySelector("[data-paginacao]");
    var pagina = 1;

    var rotulo = function (chave, padrao) {
      return (paginacao && paginacao.getAttribute("data-" + chave)) || padrao;
    };

    var botao = function (texto, aria, alvo, ligado, morto) {
      var li = document.createElement("li");
      var b = document.createElement("button");
      b.type = "button";
      b.className = "om-pag" + (ligado ? " om-pag-on" : "");
      b.textContent = texto;
      if (aria) { b.setAttribute("aria-label", aria); }
      if (ligado) { b.setAttribute("aria-current", "true"); }
      if (morto) { b.disabled = true; }
      else {
        b.addEventListener("click", function () {
          pagina = alvo;
          aplicar();
          /* Volta para o topo da GRADE, e não da página: quem clicou em "3"
             quer ver a página 3, e não o cabeçalho de novo. */
          var grade = document.querySelector(".om-grade-cases");
          if (grade) { irPara(grade); }
        });
      }
      li.appendChild(b);
      return li;
    };

    var pulo = function () {
      var li = document.createElement("li");
      var s = document.createElement("span");
      s.className = "om-pag-pulo";
      s.setAttribute("aria-hidden", "true");
      s.textContent = "...";
      li.appendChild(s);
      return li;
    };

    var desenharPaginacao = function (paginas) {
      if (!paginacao) { return; }
      paginacao.textContent = "";
      /* Uma página só não é paginação: é uma fileira de um botão que não leva
         a lugar nenhum. */
      paginacao.hidden = paginas < 2;
      if (paginas < 2) { return; }
      paginacao.appendChild(botao(
        "\u2039", rotulo("anterior", "Página anterior"), pagina - 1, false, pagina === 1));
      /* Sempre a primeira, a última, a atual e uma vizinha de cada lado. Com
         dezoito cases e seis por página são três páginas e tudo cabe; a regra
         existe para o dia em que a agência tiver sessenta. */
      var mostra = [];
      for (var n = 1; n <= paginas; n++) {
        if (n === 1 || n === paginas || Math.abs(n - pagina) <= 1) { mostra.push(n); }
      }
      var anterior = 0;
      for (var k = 0; k < mostra.length; k++) {
        if (mostra[k] - anterior > 1) { paginacao.appendChild(pulo()); }
        paginacao.appendChild(botao(
          String(mostra[k]), rotulo("pagina", "Página") + " " + mostra[k],
          mostra[k], mostra[k] === pagina, false));
        anterior = mostra[k];
      }
      paginacao.appendChild(botao(
        "\u203a", rotulo("proxima", "Próxima página"), pagina + 1, false, pagina === paginas));
    };

    var aplicar = function () {
      var termo = achatar(campoDeBusca.value).trim();
      var passaram = [];
      for (var i = 0; i < cartoes.length; i++) {
        if (!termo || textoDe[i].indexOf(termo) >= 0) { passaram.push(cartoes[i]); }
      }
      var paginas = Math.max(1, Math.ceil(passaram.length / POR_PAGINA));
      if (pagina > paginas) { pagina = paginas; }
      if (pagina < 1) { pagina = 1; }
      var inicio = (pagina - 1) * POR_PAGINA;
      for (var j = 0; j < cartoes.length; j++) { cartoes[j].hidden = true; }
      for (var k2 = inicio; k2 < inicio + POR_PAGINA && k2 < passaram.length; k2++) {
        passaram[k2].hidden = false;
      }
      if (vazio) { vazio.hidden = passaram.length > 0; }
      if (conta) {
        conta.textContent = termo && molde
          ? molde.replace("{n}", String(passaram.length)).replace("{total}", String(cartoes.length))
          : contaOriginal;
      }
      desenharPaginacao(paginas);
    };

    var filtrar = function () {
      /* Toda busca recomeça na primeira página. Sem isto, digitar estando na
         terceira mostraria um recorte vazio de um resultado que tem dois. */
      pagina = 1;
      aplicar();
    };
    aplicar();
    campoDeBusca.addEventListener("input", filtrar);
    // `search` cobre o "x" que o próprio navegador desenha no `type="search"`:
    // sem ele, limpar pelo x deixaria a grade recortada e o campo vazio.
    campoDeBusca.addEventListener("search", filtrar);
  }

  var cabecalho = document.querySelector("[data-cabecalho]");
  var progresso = document.querySelector("[data-progresso]");
  /* O BANNER "EM ALTA" (27/08): randômico e rotativo, como um slot de mídia
     programática. O sorteio é a cada carga; a troca é um crossfade a cada
     sete segundos. Com `prefers-reduced-motion`, fica a peça sorteada,
     parada: rotação é movimento, e movimento pedido para não acontecer. */
  var alta = document.querySelector("[data-alta]");
  if (alta) {
    var pecas = alta.querySelectorAll("img");
    if (pecas.length > 1) {
      var viva = Math.floor(Math.random() * pecas.length);
      var mostrar = function () {
        for (var i = 0; i < pecas.length; i++) {
          pecas[i].classList.toggle("om-alta-viva", i === viva);
        }
      };
      mostrar();
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        window.setInterval(function () {
          viva = (viva + 1) % pecas.length;
          mostrar();
        }, 7000);
      }
    }
  }

  var aoTopo = document.querySelector("[data-ao-topo]");
  if (aoTopo) {
    aoTopo.addEventListener("click", function (ev) {
      ev.preventDefault();
      irPara(0);
      /* O foco volta para o topo do documento junto com a página. Sem isto,
         quem navega por teclado continua no rodapé depois de "subir". */
      var marco = document.getElementById("om-topo") || document.body;
      marco.setAttribute("tabindex", "-1");
      marco.focus({ preventScroll: true });
    });
  }
  var faixaDoPe = document.querySelector(".footer-bottom");
  if (cabecalho || aoTopo || (progresso && querMovimento)) {
    var pedido = false;
    var medir = function () {
      pedido = false;
      var y = window.pageYOffset || raiz.scrollTop || 0;
      if (cabecalho) {
        /* 24 px, e não 1: o iOS devolve valores pequenos e negativos no
           repique da rolagem elástica, e a 1 px o cabeçalho piscava entre os
           dois estados no alto da página. */
        if (y > 24) { cabecalho.classList.add("om-preso"); }
        else { cabecalho.classList.remove("om-preso"); }
      }
      /* ITEM 26, segunda metade: VOLTAR AO TOPO, depois da primeira dobra.
         O limiar é a altura da JANELA, e não um número redondo: "depois da
         primeira dobra" quer dizer "depois do que coube na tela desta
         pessoa", e isso muda entre um celular e um monitor. */
      if (aoTopo) {
        aoTopo.hidden = y < window.innerHeight * 0.9;
        /* O LIMITE de até onde ele desce. A faixa de copyright é a última
           coisa da página e tem o botão de contato dentro dela: sem isto, os
           dois ocupam o mesmo canto e um cobre o outro.

           Mede o quanto da faixa já entrou na tela e devolve isso como recuo.
           Enquanto ela não aparece, o recuo é zero e nada muda. */
        if (faixaDoPe) {
          var caixa = faixaDoPe.getBoundingClientRect();
          var invadido = window.innerHeight - caixa.top;
          raiz.style.setProperty(
            "--om-recuo-pe", (invadido > 0 ? Math.round(invadido) : 0) + "px");
        }
      }
      if (progresso && querMovimento) {
        var total = raiz.scrollHeight - window.innerHeight;
        var quanto = total > 0 ? y / total : 0;
        quanto = quanto < 0 ? 0 : (quanto > 1 ? 1 : quanto);
        progresso.style.transform = "scaleX(" + quanto.toFixed(4) + ")";
      }
    };
    var aoRolar = function () {
      if (pedido) { return; }
      pedido = true;
      requestAnimationFrame(medir);
    };
    window.addEventListener("scroll", aoRolar, { passive: true });
    window.addEventListener("resize", aoRolar, { passive: true });
    medir();
  }

  /* ====================================================================
     SEGUNDA METADE: MOVIMENTO. Só com `om-js`, e só com GSAP.
     ==================================================================== */

  /* Sair aqui é o caminho normal, não a exceção: sem `om-js` (o leitor pediu
     menos movimento, ou o relógio já disparou), a página fica exatamente
     como o CSS a desenhou, inteira e visível, com menu e cabeçalho já
     funcionando. */
  if (!querMovimento) { return; }

  /* Se o GSAP não chegou, a classe precisa cair AGORA, e não em 2,5 s. */
  if (!window.gsap || !window.ScrollTrigger) {
    raiz.classList.remove("om-js");
    return;
  }

  clearTimeout(window.__omRelogio);
  gsap.registerPlugin(ScrollTrigger);

  /* ---------------------------------------------------------- rolagem --
     Lenis, com o `raf` pendurado no relógio do GSAP em vez de num
     `requestAnimationFrame` próprio. Dois laços de animação no mesmo quadro
     é a causa clássica de a rolagem suave "tremer" junto com um scrub: o
     ScrollTrigger lê a posição que o outro laço ainda não escreveu. Com um
     relógio só, a ordem é sempre a mesma.

     `lagSmoothing(0)` porque o padrão do GSAP é congelar o tempo quando um
     quadro demora demais, e num celular médio, com 56 imagens de logo
     entrando em cena, isso faz a fita dar um pulo. */
  if (window.Lenis) {
    lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1, touchMultiplier: 1.6 });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
    gsap.ticker.lagSmoothing(0);

    /* As âncoras do cabeçalho precisam passar pelo Lenis: o
       `scroll-behavior` nativo brigaria com ele e a página saltaria. O foco
       continua indo para o destino, que é o que faz a âncora servir para
       quem navega por teclado. */
    var ancoras = document.querySelectorAll('a[href^="#"]');
    for (var a = 0; a < ancoras.length; a++) {
      ancoras[a].addEventListener("click", function (ev) {
        var alvo = document.getElementById(this.getAttribute("href").slice(1));
        if (!alvo) { return; }
        ev.preventDefault();
        lenis.scrollTo(alvo, { offset: -24, duration: 1.1 });
        alvo.setAttribute("tabindex", "-1");
        alvo.focus({ preventScroll: true });
      });
    }
  }

  /* -------------------------------------------------------- revelação --
     `ScrollTrigger.batch` e não um trigger por elemento: com 40 alvos, um
     trigger cada é uma lista de 40 posições recalculada a cada `refresh`, e
     o `batch` ainda dá de graça o escalonamento das linhas do índice de
     serviços, que é o único lugar da página onde a cascata se percebe.

     `once: true` porque nada aqui volta a sumir quando o visitante rola para
     cima. Revelação que se desfaz é efeito, não desenho. */
  ScrollTrigger.batch(".om-rv", {
    start: "top 90%",
    once: true,
    onEnter: function (lote) {
      gsap.to(lote, {
        opacity: 1, y: 0, duration: 0.9, ease: "power3.out",
        stagger: 0.06, overwrite: true
      });
    }
  });

  /* --------------------------------------- o fio do índice (item 14) --
     A metade "motion na rolagem" do item 14: o fio de cada linha de serviço
     se desenha da esquerda para a direita conforme ela entra na tela.

     É UM `batch` PRÓPRIO, e não um trecho dentro do da revelação, porque as
     duas coisas têm tempos diferentes de propósito: a linha sobe em 0,9 s e o
     fio leva 1,05 s a partir dali. Um fio que terminasse junto com o texto
     seria só mais um pedaço da mesma revelação; terminando depois, ele lê
     como uma segunda ação, que é o "sumário sendo escrito".

     QUEM ANIMA É O CSS, e o script só põe uma classe. O fio é um
     pseudo-elemento (`::after`), e GSAP não alcança pseudo-elemento; e vale
     mais do que o contorno: com o desenho no CSS, o estado de repouso e o
     estado final moram no mesmo arquivo que o resto do desenho, em vez de um
     deles virar um número solto aqui dentro.

     O `stagger` é feito à mão, com `setTimeout` de 70 ms por linha do lote.
     São sete elementos, uma vez na vida da página. */
  var linhasDoIndice = document.querySelectorAll("[data-indice] > li");
  if (linhasDoIndice.length) {
    ScrollTrigger.batch("[data-indice] > li", {
      start: "top 90%",
      once: true,
      onEnter: function (lote) {
        for (var l = 0; l < lote.length; l++) {
          (function (linha, atraso) {
            setTimeout(function () { linha.classList.add("om-tracado"); }, atraso);
          })(lote[l], l * 70);
        }
      }
    });
  }

  /* ---------------------------------------------------------- manchete --
     Máscara de linha: cada linha sobe por trás de uma janela própria. É o
     gesto do tema de referência, e o `mask: "lines"` do GSAP 3.13 cria essa
     janela sozinho, o que evita a marcação extra no HTML.

     `document.fonts.ready` é obrigatório e não é preciosismo: cortar em
     linhas ANTES de a Montserrat chegar corta a manchete pela métrica da
     fonte do sistema, e quando a fonte troca as linhas ficam no lugar errado.
     Numa manchete de 110 px isso não é sutil: é uma linha inteira fora do
     lugar. */
  var cortes = [];
  function cortarTitulos() {
    if (!window.SplitText) { return; }
    gsap.registerPlugin(SplitText);
    var titulos = document.querySelectorAll(".om-split");
    for (var i = 0; i < titulos.length; i++) {
      (function (alvo) {
        try {
          SplitText.create(alvo, {
            type: "lines",
            mask: "lines",
            autoSplit: true,          /* refaz o corte quando a janela muda */
            /* O CONSERTO DO CORTE DE TEXTO (item 6). A janela que o `mask`
               cria tem a altura da caixa de linha, e as caixas desta peça são
               apertadas de propósito (manchete em .92, título em .98). Com
               entrelinha abaixo de 1, o "g" de "ligação" desce para fora da
               caixa e a janela o corta pela metade: era exatamente a captura
               que o Leandro mandou.

               Nomear a linha permite ao CSS dar a folga (`.om-linha`, em
               grupo-om.css) sem depender de um seletor de estrutura como
               `.om-split div`, que quebraria calado no dia em que o GSAP
               mudasse o número de camadas do embrulho. */
            linesClass: "om-linha",
            onSplit: function (self) {
              var tw = gsap.from(self.lines, {
                yPercent: 108, duration: 1, ease: "power4.out", stagger: 0.09,
                scrollTrigger: { trigger: alvo, start: "top 88%", once: true }
              });
              cortes.push({ tw: tw, el: alvo });
              return tw;
            }
          });
        } catch (e) {
          /* Um título que não corta é um título que aparece parado, e isso
             está certo: `gsap.from` nunca chegou a rodar, então não há
             estado inicial preso em lugar nenhum. */
        }
      })(titulos[i]);
    }

    /* O TÍTULO É O ÚNICO ELEMENTO SEM REDE. Um `.om-rv` que não revela ainda
       é um bloco cinza; um `.om-split` que não revela é um TÍTULO AUSENTE,
       porque a linha está deslocada 108% dentro de uma janela que corta. O
       `gsap.from` já pintou o estado inicial no instante em que foi criado, e
       se o gatilho não disparar (aba aberta em segundo plano, imagem `lazy`
       que mudou a altura da página depois do cálculo) ele fica assim.

       Então: 3,5 s depois, todo corte que ainda está no começo e cujo título
       já está dentro da janela vai para o fim na marra. */
    setTimeout(function () {
      for (var c = 0; c < cortes.length; c++) {
        var caixa = cortes[c].el.getBoundingClientRect();
        if (cortes[c].tw.progress() === 0 &&
            caixa.top < window.innerHeight && caixa.bottom > 0) {
          cortes[c].tw.progress(1);
        }
      }
    }, 3500);
  }
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(cortarTitulos);
  } else {
    cortarTitulos();
  }

  /* --------------------------------------------------------- contadores --
     O número final JÁ ESTÁ no HTML: o contador só o substitui pelo zero no
     instante em que começa a subir. Assim, quem não tem script vê os números
     prontos, e quem tem vê os três subirem.

     `snap` inteiro, e `tabular-nums` no CSS: sem os dois, "47" passa por
     larguras diferentes a cada quadro e a linha inteira treme. */
  var numeros = document.querySelectorAll("[data-conta]");
  for (var n = 0; n < numeros.length; n++) {
    (function (el) {
      var alvo = parseInt(el.getAttribute("data-conta"), 10);
      if (!alvo) { return; }
      var caixa = { v: 0 };
      gsap.to(caixa, {
        v: alvo, duration: 1.6, ease: "power2.out", snap: { v: 1 },
        scrollTrigger: { trigger: el, start: "top 92%", once: true },
        onStart: function () { el.textContent = "0"; },
        onUpdate: function () { el.textContent = String(Math.round(caixa.v)); },
        onComplete: function () { el.textContent = String(alvo); }
      });
    })(numeros[n]);
  }

  /* -------------------------------------------------------------- fitas --
     Duas fitas de logo, catorze marcas cada, sentidos opostos. Cada trilho
     tem a lista real e uma cópia idêntica, e o laço é `xPercent: 50 * direção`: exatamente metade do
     trilho, que é exatamente uma lista. Por isso o CSS tirou o `gap` da
     lista e pôs o intervalo no `li`: com `gap`, a emenda entre as cópias
     seria meia goteira mais curta e a fita saltaria a cada volta.

     A VELOCIDADE RESPONDE À ROLAGEM. É o detalhe que separa "tem um marquee"
     de "alguém desenhou este marquee": ao rolar, as fitas aceleram, e
     desaceleram sozinhas ao parar. O fator é limitado em 3,2x, porque acima
     disso os logos borram e a prova vira enfeite. */
  var fitas = [];
  var trilhos = document.querySelectorAll(".om-fita-trilho");
  for (var f = 0; f < trilhos.length; f++) {
    (function (trilho) {
      var direcao = parseInt(trilho.getAttribute("data-fita"), 10) < 0 ? -1 : 1;
      var de = direcao < 0 ? 0 : -50;
      var para = direcao < 0 ? -50 : 0;
      fitas.push(gsap.fromTo(trilho,
        { xPercent: de },
        { xPercent: para, duration: 52, ease: "none", repeat: -1 }));
    })(trilhos[f]);
  }

  if (fitas.length) {
    ScrollTrigger.create({
      onUpdate: function (self) {
        var fator = 1 + Math.min(Math.abs(self.getVelocity()) / 1600, 2.2);
        for (var i = 0; i < fitas.length; i++) {
          gsap.to(fitas[i], { timeScale: fator, duration: 0.4, overwrite: true });
        }
      }
    });
  }

  /* --------------------------------------------------------- as peças --
     Deslocamento por rolagem nas duas peças do cliente, e ele é PEQUENO de
     propósito: 7% de altura no total. Paralaxe grande num banner com texto
     chapado dentro faz a arte deslizar por trás da própria moldura, e o texto
     do cliente sai do enquadramento que ele mesmo aprovou.

     A `scale: 1.08` não é efeito: é a folga. Sem ela, deslocar a imagem 3,5%
     para cima abre uma tira vazia de 3,5% na base da moldura, e o que o dono
     vê é um banner descolado do próprio quadro. Com 8% de sobra, os 3,5% de
     cada lado nunca chegam na borda. */
  var pecas = document.querySelectorAll(".om-peca img");
  for (var p = 0; p < pecas.length; p++) {
    gsap.fromTo(pecas[p], { yPercent: -3.5, scale: 1.08 }, {
      yPercent: 3.5, scale: 1.08, ease: "none",
      scrollTrigger: { trigger: pecas[p], start: "top bottom", end: "bottom top", scrub: 0.6 }
    });
  }

  /* --------------------------------------------------- rede de segurança --
     O último cinto. Se um `batch` não disparar (imagem que muda de altura
     depois do `refresh`, aba aberta em segundo plano, `refresh` que chegou
     antes de a fonte trocar), qualquer `.om-rv` que ainda esteja invisível
     dentro da janela volta na força. É feio e é barato, e o alternativo é o
     dono da agência abrir a proposta e ver um bloco em branco. */
  ScrollTrigger.addEventListener("refresh", function () {
    setTimeout(function () {
      var alvos = document.querySelectorAll(".om-rv");
      for (var i = 0; i < alvos.length; i++) {
        var caixa = alvos[i].getBoundingClientRect();
        if (caixa.top < window.innerHeight && caixa.bottom > 0 &&
            getComputedStyle(alvos[i]).opacity === "0") {
          gsap.set(alvos[i], { opacity: 1, y: 0 });
        }
      }
      /* O MESMO CINTO PARA O FIO DO ÍNDICE (item 14). Se o `batch` dele não
         disparar, as sete linhas ficam com o fio zerado, e a seção de
         serviços aparece sem as réguas que a separam. A borda do `<li>`
         continua lá embaixo, então não é um buraco; ainda assim é desenho
         faltando, e o conserto custa quatro linhas. */
      var fios = document.querySelectorAll("[data-indice] > li");
      for (var f = 0; f < fios.length; f++) {
        var cx = fios[f].getBoundingClientRect();
        if (cx.top < window.innerHeight && cx.bottom > 0) {
          fios[f].classList.add("om-tracado");
        }
      }
    }, 1200);
  });

  /* As imagens são `lazy` e chegam depois: sem isto, as posições dos
     gatilhos ficam calculadas sobre uma página mais curta do que a real. */
  window.addEventListener("load", function () { ScrollTrigger.refresh(); });
})();
