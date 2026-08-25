/* ============================================================
   Admita — esteira de admissão (Task 4 do Plano 2).

   Padrão de interação (nunca recarrega a página, §3/§13b):
   - Toda mutação (mover, aprovar, checklist, nova candidatura) faz um
     `fetch` POST e recebe de volta o MESMO fragmento HTML
     (`lab/admita/_shell.html`, renderizado por `app/lab/rotas.py`), que
     substitui `#admita-app` inteiro — sidebar/quadro/auditoria sempre
     saem consistentes um com o outro, sem round-trip parcial.
   - Feedback otimista: o gatilho (botão/seta) ganha uma marca "pendente"
     na hora, ANTES da resposta chegar; se o servidor recusa a ação
     (regra de negócio do §6.1, ex.: documento pendente), a marca some e
     um toast elegante explica o motivo — nada muda de verdade até o
     servidor confirmar.
   - Estado de UI que não é do servidor (qual checklist está aberto, se a
     auditoria está aberta, a página de paginação de cada coluna, a etapa
     ativa no modo mobile) vive só aqui em `estado` e é REAPLICADO depois
     de cada swap — o servidor nunca precisa saber disso.
   ============================================================ */
(function () {
  "use strict";

  var app = document.getElementById("admita-app");
  if (!app) return;

  // Quantos cards cabem por coluna NÃO é constante: depende da altura da
  // tela e da altura real de cada card (nome que quebra em duas linhas,
  // botão de aprovar, chip de prazo). Medimos a cada aplicação, em vez de
  // chutar um número que estoura no celular. Mínimo de 1 card sempre.
  var MINIMO_VISIVEL = 1;

  var estado = {
    checklistAberto: null,
    auditoriaAberta: false,
    etapaMobileAtiva: null,
    paginas: {},
    // agenda: sobrevive à troca de fragmento, senão marcar uma entrevista
    // fecharia o painel na cara de quem está marcando a próxima.
    agendaAberta: false,
    agendaCandidato: null,
    agendaMes: null, // {ano, mes} do mês desenhado; null = mês de hoje
    agendaPagina: 0, // primeiro candidato mostrado na lista da agenda
    configAberta: false,
  };

  var MESES_LONGOS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
  ];

  // -------------------------------------------------------------- toast --
  function mostrarToast(mensagem) {
    var toast = document.getElementById("admita-toast");
    if (!toast) return;
    toast.textContent = mensagem;
    toast.hidden = false;
    requestAnimationFrame(function () { toast.classList.add("visivel"); });
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(function () {
      toast.classList.remove("visivel");
      window.setTimeout(function () { toast.hidden = true; }, 220);
    }, 4200);
  }

  // -------------------------------------------------------- paginação ----
  // Nunca rolagem (§13b): no máximo PAGINA_TAMANHO cards visíveis por
  // coluna; "mostrar mais" TROCA de página (mostra o próximo lote), nunca
  // acumula — a altura da coluna nunca cresce.
  function modoApp() {
    return window.matchMedia("(max-width: 860px)").matches;
  }

  function aplicarPaginacao() {
    var colunas = app.querySelectorAll(".admita-coluna");
    if (modoApp()) {
      // no aplicativo a lista rola no dedo: paginar seria a única coisa
      // aqui que não pareceria app. Mostra tudo e sai.
      colunas.forEach(function (coluna) {
        coluna.querySelectorAll(".admita-card").forEach(function (card) {
          card.style.display = "";
        });
      });
      return;
    }
    colunas.forEach(function (coluna) {
      var etapa = coluna.getAttribute("data-etapa");
      var corpo = coluna.querySelector(".admita-coluna-corpo");
      if (!corpo) return;
      var cards = Array.prototype.slice.call(corpo.querySelectorAll(".admita-card"));
      if (!cards.length) return;

      var inicio = estado.paginas[etapa] || 0;
      if (inicio >= cards.length) inicio = 0;
      estado.paginas[etapa] = inicio;

      // 1. mostra tudo a partir do início da página atual
      cards.forEach(function (card, indice) {
        card.style.display = indice >= inicio ? "" : "none";
      });

      // 2. mede e corta o que passa do fundo do corpo da coluna. O primeiro
      //    card que estoura leva junto todos os seguintes, porque estão
      //    abaixo dele. Assim nenhum card aparece pela metade (§13b).
      var fundo = corpo.getBoundingClientRect().bottom;
      var visiveis = 0;
      for (var i = inicio; i < cards.length; i++) {
        var card = cards[i];
        if (visiveis >= MINIMO_VISIVEL && card.getBoundingClientRect().bottom > fundo + 0.5) {
          for (var j = i; j < cards.length; j++) cards[j].style.display = "none";
          break;
        }
        visiveis++;
      }

      var botao = coluna.querySelector("[data-mostrar-mais]");
      if (botao) {
        var texto = botao.querySelector("[data-mostrar-mais-texto]");
        var restantes = cards.length - (inicio + visiveis);
        if (restantes > 0) {
          texto.textContent = "mais " + restantes + " nesta etapa";
        } else {
          texto.textContent = "voltar ao início";
        }
        botao.setAttribute("data-visiveis", String(visiveis));
      }
    });
  }

  function ordemDasEtapas() {
    return Array.prototype.map.call(
      app.querySelectorAll(".admita-coluna"),
      function (c) { return c.getAttribute("data-etapa"); }
    );
  }

  // --------------------------------------------------- reaplicar estado --
  // ---------------------------------------------------------- agenda ----
  // O calendário é desenhado a partir dos `data-` da própria lista de
  // candidatos: uma fonte só de verdade, e trocar de mês não pede nada ao
  // servidor. Marcar/desmarcar continua sendo uma rota, porque isso é dado.

  function agendaDados() {
    var lista = document.getElementById("admita-agenda-lista");
    if (!lista) return { hoje: null, pessoas: [] };
    var pessoas = Array.prototype.slice
      .call(lista.querySelectorAll("[data-agenda-candidato]"))
      .map(function (botao) {
        return {
          id: botao.getAttribute("data-agenda-candidato"),
          data: botao.getAttribute("data-agenda-data") || "",
          elemento: botao,
        };
      });
    return { hoje: lista.getAttribute("data-hoje") || "", pessoas: pessoas };
  }

  function isoDoDia(ano, mes, dia) {
    return (
      String(ano) + "-" +
      String(mes + 1).padStart(2, "0") + "-" +
      String(dia).padStart(2, "0")
    );
  }

  function desenharCalendario() {
    var grade = document.getElementById("admita-agenda-grade");
    var titulo = document.getElementById("admita-agenda-mes-nome");
    var dica = document.getElementById("admita-agenda-dica");
    if (!grade || !titulo) return;

    var dados = agendaDados();
    var hoje = dados.hoje;
    var base = estado.agendaMes;
    if (!base) {
      var partes = (hoje || "").split("-");
      base = { ano: parseInt(partes[0], 10), mes: parseInt(partes[1], 10) - 1 };
      if (isNaN(base.ano)) return;
      estado.agendaMes = base;
    }

    var nomeMes = MESES_LONGOS[base.mes];
    titulo.textContent = nomeMes.charAt(0).toUpperCase() + nomeMes.slice(1) + " de " + base.ano;

    // dias com entrevista, e de quem
    var porDia = {};
    dados.pessoas.forEach(function (pessoa) {
      if (!pessoa.data) return;
      (porDia[pessoa.data] = porDia[pessoa.data] || []).push(pessoa);
    });

    var primeiro = new Date(base.ano, base.mes, 1);
    var diasNoMes = new Date(base.ano, base.mes + 1, 0).getDate();
    var vazios = primeiro.getDay();

    var html = "";
    for (var v = 0; v < vazios; v++) html += '<span class="admita-dia vazio"></span>';
    for (var dia = 1; dia <= diasNoMes; dia++) {
      var iso = isoDoDia(base.ano, base.mes, dia);
      var marcados = porDia[iso] || [];
      var classes = ["admita-dia"];
      if (iso === hoje) classes.push("hoje");
      if (marcados.length) classes.push("tem");
      if (hoje && iso < hoje) classes.push("passado");
      if (estado.agendaCandidato) {
        var meu = marcados.some(function (p) { return p.id === estado.agendaCandidato; });
        if (meu) classes.push("meu");
      }
      var rotulo = marcados.length
        ? dia + ", " + marcados.length + (marcados.length === 1 ? " entrevista" : " entrevistas")
        : String(dia);
      html +=
        '<button type="button" class="' + classes.join(" ") + '" data-agenda-dia="' + iso +
        '" aria-label="' + rotulo + '">' + dia +
        (marcados.length ? '<i class="admita-dia-ponto" aria-hidden="true"></i>' : "") +
        "</button>";
    }
    grade.innerHTML = html;

    if (dica) {
      if (!estado.agendaCandidato) {
        dica.textContent = "Selecione um candidato para liberar o calendário.";
      } else {
        var escolhido = dados.pessoas.filter(function (p) {
          return p.id === estado.agendaCandidato;
        })[0];
        dica.textContent = escolhido && escolhido.data
          ? "Clique em outro dia para remarcar, ou no mesmo dia para desmarcar."
          : "Clique num dia para marcar a entrevista.";
      }
    }

    grade.classList.toggle("sem-candidato", !estado.agendaCandidato);

    dados.pessoas.forEach(function (pessoa) {
      pessoa.elemento.classList.toggle(
        "selecionado", pessoa.id === estado.agendaCandidato
      );
    });
  }

  // A lista de candidatos da agenda não rola (regra do dono: nenhuma barra
  // de rolagem em lugar nenhum). Mostra o bloco que cabe de verdade e o
  // resto troca de página, igual às colunas do quadro.
  function paginarAgenda() {
    var lista = document.getElementById("admita-agenda-lista");
    if (!lista) return;
    var pessoas = Array.prototype.slice.call(lista.querySelectorAll(".admita-agenda-pessoa"));
    var botao = lista.querySelector("[data-agenda-mais]");
    if (!pessoas.length) return;

    var inicio = estado.agendaPagina || 0;
    if (inicio >= pessoas.length) inicio = 0;
    estado.agendaPagina = inicio;

    pessoas.forEach(function (p, i) { p.style.display = i >= inicio ? "" : "none"; });

    var fundo = lista.getBoundingClientRect().bottom;
    if (botao) fundo -= botao.getBoundingClientRect().height + 6;
    var visiveis = 0;
    for (var i = inicio; i < pessoas.length; i++) {
      if (visiveis >= 1 && pessoas[i].getBoundingClientRect().bottom > fundo + 0.5) {
        for (var j = i; j < pessoas.length; j++) pessoas[j].style.display = "none";
        break;
      }
      visiveis++;
    }

    var restantes = pessoas.length - (inicio + visiveis);
    if (botao) {
      var sobra = restantes > 0 || inicio > 0;
      botao.hidden = !sobra;
      botao.setAttribute("data-visiveis", String(visiveis));
      var texto = botao.querySelector("[data-agenda-mais-texto]");
      if (texto) {
        texto.textContent = restantes > 0
          ? "mais " + restantes + " na lista"
          : "voltar ao início";
      }
    }
  }

  function aplicarAgenda() {
    var painel = document.getElementById("admita-modal-agenda");
    if (painel) {
      painel.hidden = !estado.agendaAberta;
      if (estado.agendaAberta) {
        paginarAgenda();
        desenharCalendario();
      }
    }
    var config = document.getElementById("admita-modal-config");
    if (config) {
      config.hidden = !estado.configAberta;
      if (estado.configAberta) ajustarPainelDeConfig();
    }
  }

  async function marcarEntrevista(iso) {
    if (!estado.agendaCandidato) return;
    var dados = agendaDados();
    var escolhido = dados.pessoas.filter(function (p) {
      return p.id === estado.agendaCandidato;
    })[0];
    // clicar no dia que já é o dele desmarca: um clique só, sem outro botão
    var alvo = escolhido && escolhido.data === iso ? "" : iso;
    try {
      var html = await enviar(
        "/lab/admita/candidatos/" + estado.agendaCandidato + "/entrevista",
        { data: alvo }
      );
      trocarShell(html);
    } catch (erro) {
      mostrarToast(erro.message);
    }
  }

  // O menu tem que caber na caixa branca em QUALQUER altura de tela: com
  // clamp em vh a conta erra em janelas curtas e o último botão fica de
  // fora (foi o que o dono viu). Aqui a altura da linha é medida, não
  // estimada: começa no confortável e desce até o conteúdo caber.
  var LINHA_MAX = 52;
  var LINHA_MIN = 40;
  var VAO_MAX = 14;
  var VAO_MIN = 8;

  // A coluna de ícones precisa de duas coisas ao mesmo tempo: caber ABERTA
  // (com os rótulos de duas linhas) e ficar centrada no campo branco com a
  // mesma folga em cima e embaixo, senão a sobra de um lado só lê como
  // corte, que foi a reclamação do dono.
  function ajustarAlturaDoMenu() {
    var aside = document.getElementById("admita-sidebar");
    var nav = aside && aside.querySelector(".admita-sidebar-nav");
    var shell = document.getElementById("admita-shell");
    if (!nav || !aside || !shell) return;

    // a régua é a ALTURA REAL da coluna, não a do shell: são iguais no papel
    // e divergem por arredondamento, e a diferença virava botão para fora.
    var limite = Math.min(aside.clientHeight, shell.clientHeight);
    if (!limite || modoApp()) return;

    // 1. respiro primeiro: o vão só cede depois que a linha chega no piso,
    //    porque é o vão que dá harmonia (pedido do dono).
    var linha = LINHA_MAX;
    var vao = VAO_MAX;
    nav.style.setProperty("--admita-vao", vao + "px");
    nav.style.setProperty("--admita-linha", linha + "px");
    while (nav.scrollHeight > limite && linha > LINHA_MIN) {
      linha -= 2;
      nav.style.setProperty("--admita-linha", linha + "px");
    }
    while (nav.scrollHeight > limite && vao > VAO_MIN) {
      vao -= 1;
      nav.style.setProperty("--admita-vao", vao + "px");
    }

    // 2. centra no campo branco, com a MESMA folga em cima e embaixo. Já
    //    tentamos centrar pelo eixo do quadro; com a coluna quase da altura
    //    do campo, a conta rendia sobra só de um lado e lia como corte.
    var altura = nav.offsetHeight;
    var folga = Math.max(0, aside.clientHeight - altura);
    nav.style.top = Math.round(folga / 2) + "px";
  }

  // Saudação pelo relógio de quem abre. O servidor roda em UTC, então
  // cumprimentar a partir dele erraria o turno de quase todo visitante.
  // Relógio do sistema: hora do visitante, atualizada de meio em meio
  // minuto. Um sistema de verdade mostra a hora dele, não a do servidor.
  function aplicarRelogio() {
    var alvos = app.querySelectorAll("[data-relogio]");
    if (!alvos.length) return;
    var agora = new Date();
    var texto = String(agora.getHours()).padStart(2, "0") + ":" +
                String(agora.getMinutes()).padStart(2, "0") + ":" +
                String(agora.getSeconds()).padStart(2, "0");
    alvos.forEach(function (alvo) { alvo.textContent = texto; });
  }
  window.setInterval(aplicarRelogio, 1000);

  function aplicarSaudacao() {
    var alvo = app.querySelector("[data-saudacao]");
    if (!alvo) return;
    var hora = new Date().getHours();
    var texto = "Boa noite";
    if (hora >= 5 && hora < 12) texto = "Bom dia";
    else if (hora >= 12 && hora < 18) texto = "Boa tarde";
    alvo.textContent = texto;
  }

  function aplicarEstadoUI() {
    aplicarSaudacao();
    aplicarRelogio();
    ajustarAlturaDoMenu();
    aplicarPaginacao();
    aplicarAgenda();

    var checklists = app.querySelectorAll(".admita-checklist-painel");
    checklists.forEach(function (painel) {
      var aberto = estado.checklistAberto && painel.id === "admita-checklist-" + estado.checklistAberto;
      painel.hidden = !aberto;
      painel.classList.toggle("aberto", !!aberto);
    });
    if (estado.checklistAberto && !document.getElementById("admita-checklist-" + estado.checklistAberto)) {
      estado.checklistAberto = null;
    }

    var auditoria = document.getElementById("admita-auditoria");
    if (auditoria) {
      auditoria.hidden = !estado.auditoriaAberta;
      auditoria.classList.toggle("aberto", estado.auditoriaAberta);
      if (estado.auditoriaAberta) ajustarTrilha();
    }

    var board = document.getElementById("admita-board");
    var ordem = ordemDasEtapas();
    if (!estado.etapaMobileAtiva || ordem.indexOf(estado.etapaMobileAtiva) === -1) {
      estado.etapaMobileAtiva = ordem[0];
    }
    if (board) board.setAttribute("data-etapa-ativa", estado.etapaMobileAtiva);
    app.querySelectorAll(".admita-coluna").forEach(function (coluna) {
      var ativa = coluna.getAttribute("data-etapa") === estado.etapaMobileAtiva;
      coluna.classList.toggle("admita-coluna-ativa-mobile", ativa);
    });
    app.querySelectorAll(".admita-ficha-etapa").forEach(function (ficha) {
      var ativa = ficha.getAttribute("data-etapa-mobile-alvo") === estado.etapaMobileAtiva;
      ficha.classList.toggle("ativa", ativa);
      if (ativa && modoApp()) {
        ficha.scrollIntoView({ block: "nearest", inline: "center" });
      }
    });
    var abas = { agenda: estado.agendaAberta, ajustes: estado.configAberta, trilha: estado.auditoriaAberta };
    app.querySelectorAll(".admita-tab").forEach(function (tab) {
      var nome = tab.getAttribute("data-tab");
      var ativa = nome === "esteira"
        ? !(estado.agendaAberta || estado.configAberta || estado.auditoriaAberta)
        : !!abas[nome];
      tab.classList.toggle("ativa", ativa);
    });
    var nomeSpan = document.getElementById("admita-etapa-mobile-nome");
    var h2Ativo = board && board.querySelector(
      '.admita-coluna[data-etapa="' + estado.etapaMobileAtiva + '"] h2'
    );
    if (nomeSpan && h2Ativo) nomeSpan.textContent = h2Ativo.textContent;

    var setaAnterior = app.querySelector('[data-etapa-mobile="anterior"]');
    var setaProxima = app.querySelector('[data-etapa-mobile="proxima"]');
    var idxAtual = ordem.indexOf(estado.etapaMobileAtiva);
    if (setaAnterior) setaAnterior.disabled = idxAtual <= 0;
    if (setaProxima) setaProxima.disabled = idxAtual >= ordem.length - 1;
  }

  // -------------------------------------------------------------- fetch --
  async function enviar(url, dados) {
    var corpo = new URLSearchParams(dados || {});
    var resposta = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: corpo.toString(),
    });
    if (!resposta.ok) {
      var mensagem = "Não foi possível concluir a ação agora. Tente de novo.";
      try {
        var dadosErro = await resposta.json();
        if (dadosErro && dadosErro.detail) mensagem = dadosErro.detail;
      } catch (erroLeitura) { /* resposta sem corpo JSON: mantém mensagem padrão */ }
      throw new Error(mensagem);
    }
    return resposta.text();
  }

  function trocarShell(html) {
    app.innerHTML = html;
    aplicarEstadoUI();
    reaplicarDispensados();
    sincronizarCargos();
  }

  function marcarPendente(elemento, pendente) {
    if (!elemento) return;
    elemento.classList.toggle("admita-otimista", pendente);
    elemento.disabled = pendente;
  }

  async function acaoComOtimismo(gatilho, url, dados) {
    var cartao = gatilho.closest(".admita-card");
    marcarPendente(gatilho, true);
    if (cartao) cartao.classList.add("admita-card-pendente");
    try {
      var html = await enviar(url, dados);
      trocarShell(html);
    } catch (erro) {
      marcarPendente(gatilho, false);
      if (cartao) cartao.classList.remove("admita-card-pendente");
      mostrarToast(erro.message);
    }
  }

  // --------------------------------------------------------- delegação --
  app.addEventListener("click", function (evento) {
    var alvo;

    alvo = evento.target.closest("[data-mover]");
    if (alvo) {
      if (alvo.disabled) return;
      var idMover = alvo.getAttribute("data-candidato-id");
      var direcao = alvo.getAttribute("data-mover");
      acaoComOtimismo(alvo, "/lab/admita/candidatos/" + idMover + "/mover", { direcao: direcao });
      return;
    }

    alvo = evento.target.closest("[data-aprovar]");
    if (alvo) {
      var idAprovar = alvo.getAttribute("data-candidato-id");
      var etapaAprovar = alvo.getAttribute("data-aprovar");
      acaoComOtimismo(alvo, "/lab/admita/candidatos/" + idAprovar + "/aprovar-" + etapaAprovar, {});
      return;
    }

    alvo = evento.target.closest("[data-alternar-doc]");
    if (alvo) {
      var candId = alvo.getAttribute("data-candidato-id");
      var docId = alvo.getAttribute("data-doc-id");
      estado.checklistAberto = candId;
      acaoComOtimismo(
        alvo, "/lab/admita/candidatos/" + candId + "/documentos/" + docId + "/alternar", {}
      );
      return;
    }

    alvo = evento.target.closest("[data-abrir-checklist]");
    if (alvo) {
      estado.checklistAberto = alvo.getAttribute("data-abrir-checklist");
      aplicarEstadoUI();
      var painelAberto = document.getElementById("admita-checklist-" + estado.checklistAberto);
      var focoInicial = painelAberto && painelAberto.querySelector("[data-fechar-checklist]");
      if (focoInicial) focoInicial.focus();
      return;
    }
    alvo = evento.target.closest("[data-fechar-checklist]");
    if (alvo) {
      estado.checklistAberto = null;
      aplicarEstadoUI();
      return;
    }

    alvo = evento.target.closest("[data-abrir-auditoria]");
    if (alvo) {
      estado.auditoriaAberta = true;
      aplicarEstadoUI();
      var fechar = document.querySelector("#admita-auditoria [data-fechar-auditoria]");
      if (fechar) fechar.focus();
      return;
    }
    alvo = evento.target.closest("[data-fechar-auditoria]");
    if (alvo) {
      estado.auditoriaAberta = false;
      aplicarEstadoUI();
      return;
    }

    var tab = evento.target.closest("[data-tab]");
    if (tab) {
      var alvoTab = tab.getAttribute("data-tab");
      estado.agendaAberta = alvoTab === "agenda";
      estado.configAberta = alvoTab === "ajustes";
      estado.auditoriaAberta = alvoTab === "trilha";
      aplicarEstadoUI();
      return;
    }

    if (evento.target.closest("[data-abrir-agenda]")) {
      estado.agendaAberta = true;
      estado.configAberta = false;
      aplicarAgenda();
      return;
    }
    if (evento.target.closest("[data-fechar-agenda]")) {
      estado.agendaAberta = false;
      aplicarAgenda();
      return;
    }
    if (evento.target.closest("[data-abrir-config]")) {
      estado.configAberta = true;
      estado.agendaAberta = false;
      aplicarAgenda();
      return;
    }
    if (evento.target.closest("[data-fechar-config]")) {
      estado.configAberta = false;
      aplicarAgenda();
      return;
    }

    alvo = evento.target.closest("[data-agenda-candidato]");
    if (alvo) {
      var idPessoa = alvo.getAttribute("data-agenda-candidato");
      // clicar de novo no mesmo candidato o desmarca da seleção
      estado.agendaCandidato = estado.agendaCandidato === idPessoa ? null : idPessoa;
      desenharCalendario();
      return;
    }

    alvo = evento.target.closest("[data-agenda-mais]");
    if (alvo) {
      var visiveisLista = parseInt(alvo.getAttribute("data-visiveis"), 10) || 1;
      var atualLista = estado.agendaPagina || 0;
      var totalLista = document.querySelectorAll(".admita-agenda-pessoa").length;
      var proximo = atualLista + visiveisLista;
      estado.agendaPagina = proximo >= totalLista ? 0 : proximo;
      paginarAgenda();
      desenharCalendario();
      return;
    }

    alvo = evento.target.closest("[data-agenda-mes]");
    if (alvo) {
      var passo = parseInt(alvo.getAttribute("data-agenda-mes"), 10) || 0;
      var base = estado.agendaMes;
      if (base) {
        var novoMes = base.mes + passo;
        var ano = base.ano + Math.floor(novoMes / 12);
        novoMes = ((novoMes % 12) + 12) % 12;
        estado.agendaMes = { ano: ano, mes: novoMes };
        desenharCalendario();
      }
      return;
    }

    alvo = evento.target.closest("[data-agenda-dia]");
    if (alvo) {
      if (!estado.agendaCandidato) {
        mostrarToast("Escolha primeiro um candidato na lista da esquerda.");
        return;
      }
      marcarEntrevista(alvo.getAttribute("data-agenda-dia"));
      return;
    }

    // clique no fundo escuro fecha o painel aberto
    if (evento.target.id === "admita-modal-agenda") {
      estado.agendaAberta = false;
      aplicarAgenda();
      return;
    }
    if (evento.target.id === "admita-modal-config") {
      estado.configAberta = false;
      aplicarAgenda();
      return;
    }

    alvo = evento.target.closest(".admita-chave");
    if (alvo) {
      // painel fictício de configurações: a chave vira para a tela parecer
      // viva, e nada é gravado (o próprio painel avisa isso embaixo)
      var ligada = alvo.getAttribute("data-chave") === "on";
      alvo.setAttribute("data-chave", ligada ? "off" : "on");
      alvo.setAttribute("aria-checked", ligada ? "false" : "true");
      return;
    }

    alvo = evento.target.closest("[data-mostrar-mais]");
    if (alvo) {
      var colunaMais = alvo.closest(".admita-coluna");
      var etapaMais = colunaMais.getAttribute("data-etapa");
      var visiveisAgora = parseInt(alvo.getAttribute("data-visiveis"), 10) || 1;
      var atual = estado.paginas[etapaMais] || 0;
      estado.paginas[etapaMais] = atual + visiveisAgora;
      aplicarPaginacao();
      return;
    }

    alvo = evento.target.closest("[data-etapa-mobile-alvo]");
    if (alvo) {
      estado.etapaMobileAtiva = alvo.getAttribute("data-etapa-mobile-alvo");
      aplicarEstadoUI();
      return;
    }
    alvo = evento.target.closest("[data-etapa-mobile]");
    if (alvo) {
      if (alvo.disabled) return;
      var ordem = ordemDasEtapas();
      var idx = ordem.indexOf(estado.etapaMobileAtiva || ordem[0]);
      if (alvo.getAttribute("data-etapa-mobile") === "proxima") idx = Math.min(ordem.length - 1, idx + 1);
      else idx = Math.max(0, idx - 1);
      estado.etapaMobileAtiva = ordem[idx];
      aplicarEstadoUI();
      return;
    }

    alvo = evento.target.closest("[data-abrir-modal-novo], [data-novo-candidato]");
    if (alvo && !alvo.disabled) { abrirModal(); return; }
  });

  // O painel de configurações fica fora de `#admita-app` (é estático, não
  // entra na troca de fragmento), então o listener do app não o alcança:
  // sem isto o X não fechava e as chaves não viravam, só o ESC funcionava.
  // ------------------------------------------------- abas e acessos ----
  // Tudo aqui é da tela FICTÍCIA de configurações: troca de aba, chaves e
  // a lista de acessos. Nada vai ao servidor, e o texto que a pessoa digita
  // entra por `textContent`, nunca por innerHTML: texto de visitante é
  // texto morto, mesmo numa tela que não grava nada.
  // O painel não rola, então o conteúdo da aba tem que CABER. Aperta a folga
  // vertical das linhas até caber; se nem no mínimo couber, a aba avisa em
  // vez de deixar um item cortado pela borda (o dono viu isso acontecer).
  var CONF_PAD_MAX = 11;
  var CONF_PAD_MIN = 3;

  function ajustarPainelDeConfig() {
    var corpo = document.querySelector("#admita-modal-config .admita-config-corpo");
    if (!corpo) return;
    var pad = CONF_PAD_MAX;
    corpo.style.setProperty("--admita-conf-pad", pad + "px");
    while (corpo.scrollHeight > corpo.clientHeight && pad > CONF_PAD_MIN) {
      pad -= 1;
      corpo.style.setProperty("--admita-conf-pad", pad + "px");
    }
  }

  function trocarAba(nome) {
    var painel = document.getElementById("admita-modal-config");
    if (!painel) return;
    painel.querySelectorAll("[data-aba]").forEach(function (aba) {
      var ativa = aba.getAttribute("data-aba") === nome;
      aba.classList.toggle("ativa", ativa);
      aba.setAttribute("aria-selected", ativa ? "true" : "false");
    });
    painel.querySelectorAll("[data-painel]").forEach(function (bloco) {
      var ativo = bloco.getAttribute("data-painel") === nome;
      bloco.hidden = !ativo;
      bloco.classList.toggle("ativo", ativo);
    });
    painel.classList.toggle("em-acessos", nome === "acessos");
    ajustarPainelDeConfig();
  }

  function iniciaisDoNome(nome) {
    var partes = nome.trim().split(/\s+/);
    var primeira = partes[0] ? partes[0].charAt(0) : "?";
    var ultima = partes.length > 1 ? partes[partes.length - 1].charAt(0) : "";
    return (primeira + ultima).toUpperCase();
  }

  var PERFIS = ["Recrutador", "Coordenador de RH", "Gestor da vaga", "Somente leitura"];

  function criarLinhaDeAcesso(nome, email, perfil, indice) {
    var linha = document.createElement("div");
    linha.className = "admita-acesso-item";

    var avatar = document.createElement("span");
    avatar.className = "admita-acesso-avatar " + (indice % 2 === 0 ? "avatar-1" : "avatar-2");
    avatar.innerHTML = '<svg class="icone" aria-hidden="true"><use href="/static/lab/icones/admita.svg#i-usuario"/></svg>';

    var txt = document.createElement("span");
    txt.className = "admita-acesso-txt";
    var forte = document.createElement("strong");
    forte.textContent = nome;
    var em = document.createElement("em");
    em.textContent = email;
    txt.appendChild(forte);
    txt.appendChild(em);

    var ficha = document.createElement("span");
    ficha.className = "admita-ficha admita-ficha-perfil";
    ficha.textContent = perfil;

    var acoes = document.createElement("span");
    acoes.className = "admita-acesso-acoes";
    [["Alterar", "i-assinatura", "data-acesso-editar", ""],
     ["Excluir", "i-recusa", "data-acesso-excluir", " admita-botao-mini-perigo"]]
      .forEach(function (cfg) {
        var botao = document.createElement("button");
        botao.type = "button";
        botao.className = "admita-botao-mini" + cfg[3];
        botao.setAttribute(cfg[2], "");
        botao.setAttribute("aria-label", cfg[0] + " o acesso de " + nome);
        botao.innerHTML = '<svg class="icone" aria-hidden="true"><use href="/static/lab/icones/admita.svg#' + cfg[1] + '"/></svg>';
        botao.appendChild(document.createTextNode(cfg[0]));
        acoes.appendChild(botao);
      });

    linha.appendChild(avatar);
    linha.appendChild(txt);
    linha.appendChild(ficha);
    linha.appendChild(acoes);
    return linha;
  }

  var formAcesso = document.getElementById("admita-acesso-form");
  if (formAcesso) {
    formAcesso.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var erro = document.getElementById("admita-acesso-erro");
      var lista = document.getElementById("admita-acesso-lista");
      var dados = new FormData(formAcesso);
      var nome = (dados.get("nome") || "").toString().trim();
      var email = (dados.get("email") || "").toString().trim();
      var perfil = (dados.get("perfil") || PERFIS[0]).toString();

      function reclamar(mensagem) {
        erro.textContent = mensagem;
        erro.hidden = false;
      }
      if (nome.length < 2) return reclamar("Escreva o nome de quem vai receber o acesso.");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return reclamar("Esse e-mail não parece completo.");
      var repetido = Array.prototype.some.call(
        lista.querySelectorAll(".admita-acesso-txt em"),
        function (e) { return e.textContent.toLowerCase() === email.toLowerCase(); }
      );
      if (repetido) return reclamar("Esse e-mail já tem acesso ao Admita.");

      // a lista não rola: se a linha nova não couber no painel, o cadastro
      // é recusado com todas as letras, em vez de nascer uma barra
      erro.hidden = true;
      var nova = criarLinhaDeAcesso(nome, email, perfil, lista.children.length);
      lista.appendChild(nova);
      var painelAcessos = lista.closest(".admita-config-corpo");
      if (painelAcessos && painelAcessos.scrollHeight > painelAcessos.clientHeight) {
        lista.removeChild(nova);
        return reclamar("A lista encheu nesta demonstração. Remova um acesso para cadastrar outro.");
      }
      formAcesso.reset();
      mostrarToast("Acesso de " + nome + " cadastrado nesta demonstração.");
    });
  }

  document.addEventListener("click", function (evento) {
    var aba = evento.target.closest("[data-aba]");
    if (aba) {
      trocarAba(aba.getAttribute("data-aba"));
      return;
    }

    var editar = evento.target.closest("[data-acesso-editar]");
    if (editar) {
      var item = editar.closest(".admita-acesso-item");
      var fichaPerfil = item.querySelector(".admita-ficha-perfil");
      var atual = PERFIS.indexOf(fichaPerfil.textContent.trim());
      // alterar aqui é girar o perfil pela lista: sem formulário no meio do
      // caminho, e a mudança aparece na hora
      fichaPerfil.textContent = PERFIS[(atual + 1) % PERFIS.length];
      item.classList.add("alterado");
      window.setTimeout(function () { item.classList.remove("alterado"); }, 900);
      return;
    }

    var excluir = evento.target.closest("[data-acesso-excluir]");
    if (excluir) {
      var alvo = excluir.closest(".admita-acesso-item");
      var quem = alvo.querySelector("strong").textContent;
      alvo.remove();
      mostrarToast("Acesso de " + quem + " removido nesta demonstração.");
      return;
    }

    if (evento.target.closest("[data-fechar-config]")) {
      estado.configAberta = false;
      aplicarAgenda();
      return;
    }
    if (evento.target.id === "admita-modal-config") {
      estado.configAberta = false;
      aplicarAgenda();
      return;
    }
    var chave = evento.target.closest(".admita-chave");
    if (chave) {
      evento.preventDefault();
      var ligada = chave.getAttribute("data-chave") === "on";
      chave.setAttribute("data-chave", ligada ? "off" : "on");
      chave.setAttribute("aria-checked", ligada ? "false" : "true");
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    if (estado.agendaAberta) { estado.agendaAberta = false; aplicarAgenda(); return; }
    if (estado.configAberta) { estado.configAberta = false; aplicarAgenda(); return; }
    if (estado.checklistAberto) { estado.checklistAberto = null; aplicarEstadoUI(); return; }
    if (estado.auditoriaAberta) { estado.auditoriaAberta = false; aplicarEstadoUI(); }
  });

  aplicarEstadoUI();

  // ------------------------------------------------- modal "nova candidatura"
  var modal = document.getElementById("admita-modal-novo");
  var form = document.getElementById("admita-form-novo");
  var campoNome = document.getElementById("admita-campo-nome");
  var erroModal = document.getElementById("admita-modal-erro");
  var focoAntesDoModal = null;

  function elementosFocaveis() {
    return modal.querySelectorAll(
      'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
  }

  function abrirModal() {
    focoAntesDoModal = document.activeElement;
    modal.hidden = false;
    erroModal.hidden = true;
    form.reset();
    campoNome.focus();
    document.addEventListener("keydown", aoTeclarNoModal);
  }

  function fecharModal() {
    modal.hidden = true;
    document.removeEventListener("keydown", aoTeclarNoModal);
    if (focoAntesDoModal && typeof focoAntesDoModal.focus === "function") focoAntesDoModal.focus();
  }

  function aoTeclarNoModal(evento) {
    if (evento.key === "Escape") { fecharModal(); return; }
    if (evento.key !== "Tab") return;
    var itens = Array.prototype.slice.call(elementosFocaveis());
    if (!itens.length) return;
    var primeiro = itens[0];
    var ultimo = itens[itens.length - 1];
    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primeiro.focus();
    }
  }

  document.addEventListener("click", function (evento) {
    if (evento.target.closest("[data-fechar-modal-novo]")) { fecharModal(); return; }
    if (evento.target === modal) fecharModal(); // clique no fundo (fora do card)
  });

  form.addEventListener("submit", async function (evento) {
    evento.preventDefault();
    erroModal.hidden = true;
    var dados = new FormData(form);
    var botaoSalvar = document.getElementById("admita-form-novo-salvar");
    if (botaoSalvar) botaoSalvar.disabled = true;
    try {
      var html = await enviar("/lab/admita/candidatos", {
        nome: dados.get("nome") || "",
        cargo: dados.get("cargo") || "",
      });
      trocarShell(html);
      fecharModal();
    } catch (erro) {
      erroModal.textContent = erro.message;
      erroModal.hidden = false;
    } finally {
      if (botaoSalvar) botaoSalvar.disabled = false;
    }
  });
  // ============================================================ beta ====
  // O selo "v. beta" abre a única tela da demo que fala de negócio. Fica no
  // documento porque o selo existe em dois lugares: no topo do menu (dentro
  // do fragmento) e na assinatura central.
  document.addEventListener("click", function (evento) {
    var painelBeta = document.getElementById("admita-modal-beta");
    if (!painelBeta) return;
    if (evento.target.closest(".admita-selo-beta")) {
      painelBeta.hidden = false;
      return;
    }
    if (evento.target.closest("[data-fechar-beta]") || evento.target === painelBeta) {
      painelBeta.hidden = true;
    }
  });
  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    var painelBeta = document.getElementById("admita-modal-beta");
    if (painelBeta && !painelBeta.hidden) painelBeta.hidden = true;
  });

  // ========================================================= cargos ====
  // A lista de cargos é dado do servidor. O fragmento traz a fonte única
  // (`.admita-cargos-fonte`) e daqui saem as DUAS telas que a mostram: o
  // dropdown do modal de nova candidatura e a lista das configurações.
  // Nada de manter uma cópia paralela em memória: um lugar só é verdade.

  function cargosAtuais() {
    var fonte = app.querySelector(".admita-cargos-fonte");
    if (!fonte) return [];
    return Array.prototype.slice.call(fonte.children).map(function (item) {
      return {
        id: item.getAttribute("data-cargo-id"),
        nome: item.textContent.trim(),
        origem: item.getAttribute("data-cargo-origem") || "",
      };
    });
  }

  function sincronizarDropdownDeCargos(cargos) {
    var select = document.getElementById("admita-campo-cargo");
    if (!select) return;
    var escolhido = select.value;
    select.textContent = "";
    var vazio = document.createElement("option");
    vazio.value = "";
    vazio.disabled = true;
    vazio.selected = true;
    vazio.textContent = "Selecione um cargo";
    select.appendChild(vazio);
    cargos.forEach(function (cargo) {
      var opcao = document.createElement("option");
      opcao.value = cargo.nome;
      opcao.textContent = cargo.nome;   // texto de visitante entra por texto
      if (cargo.nome === escolhido) opcao.selected = true;
      select.appendChild(opcao);
    });
  }

  function sincronizarListaDeCargos(cargos) {
    var lista = document.getElementById("admita-cargo-lista");
    if (!lista) return;
    lista.textContent = "";
    cargos.forEach(function (cargo) {
      var linha = document.createElement("div");
      linha.className = "admita-cargo-item";
      linha.setAttribute("data-cargo", cargo.id);

      var ic = document.createElement("span");
      ic.className = "admita-cargo-ic";
      ic.innerHTML = '<svg class="icone" aria-hidden="true"><use href="/static/lab/icones/admita.svg#i-vaga"/></svg>';

      var nome = document.createElement("span");
      nome.className = "admita-cargo-nome";
      nome.textContent = cargo.nome;

      var acoes = document.createElement("span");
      acoes.className = "admita-acesso-acoes";
      var editar = document.createElement("button");
      editar.type = "button";
      editar.className = "admita-botao-mini";
      editar.setAttribute("data-cargo-renomear", "");
      editar.setAttribute("aria-label", "Renomear o cargo " + cargo.nome);
      editar.innerHTML = '<svg class="icone" aria-hidden="true"><use href="/static/lab/icones/admita.svg#i-assinatura"/></svg>';
      editar.appendChild(document.createTextNode("Renomear"));
      var excluir = document.createElement("button");
      excluir.type = "button";
      excluir.className = "admita-botao-mini admita-botao-mini-perigo";
      excluir.setAttribute("data-cargo-excluir", "");
      excluir.setAttribute("aria-label", "Excluir o cargo " + cargo.nome);
      excluir.innerHTML = '<svg class="icone" aria-hidden="true"><use href="/static/lab/icones/admita.svg#i-recusa"/></svg>';
      excluir.appendChild(document.createTextNode("Excluir"));
      acoes.appendChild(editar);
      acoes.appendChild(excluir);

      linha.appendChild(ic);
      linha.appendChild(nome);
      linha.appendChild(acoes);
      lista.appendChild(linha);
    });
    ajustarPainelDeConfig();
  }

  function sincronizarCargos() {
    var cargos = cargosAtuais();
    sincronizarDropdownDeCargos(cargos);
    sincronizarListaDeCargos(cargos);
  }

  function erroDeCargo(mensagem) {
    var erro = document.getElementById("admita-cargo-erro");
    if (!erro) return;
    erro.textContent = mensagem;
    erro.hidden = !mensagem;
  }

  async function mandarCargo(url, dados) {
    try {
      erroDeCargo("");
      var html = await enviar(url, dados);
      trocarShell(html);
      sincronizarCargos();
      return true;
    } catch (erro) {
      erroDeCargo(erro.message);
      return false;
    }
  }

  var formCargo = document.getElementById("admita-cargo-form");
  if (formCargo) {
    formCargo.addEventListener("submit", async function (evento) {
      evento.preventDefault();
      var campo = formCargo.querySelector("[name=nome]");
      var nome = (campo.value || "").trim();
      if (nome.length < 2) return erroDeCargo("Escreva o nome do cargo.");
      var deu = await mandarCargo("/lab/admita/cargos", { nome: nome });
      if (deu) campo.value = "";
    });
  }

  document.addEventListener("click", function (evento) {
    var renomear = evento.target.closest("[data-cargo-renomear]");
    if (renomear) {
      var linha = renomear.closest(".admita-cargo-item");
      var atual = linha.querySelector(".admita-cargo-nome").textContent;
      var novo = window.prompt("Novo nome para o cargo:", atual);
      if (novo === null) return;
      mandarCargo("/lab/admita/cargos/" + linha.getAttribute("data-cargo"), { nome: novo });
      return;
    }
    var excluirCargo = evento.target.closest("[data-cargo-excluir]");
    if (excluirCargo) {
      var alvoCargo = excluirCargo.closest(".admita-cargo-item");
      mandarCargo(
        "/lab/admita/cargos/" + alvoCargo.getAttribute("data-cargo") + "/excluir", {}
      );
    }
  });

  // ================================================ trilha de auditoria ====
  // A trilha lê como central de notificações: cada evento é um cartão que
  // sai da vista com o gesto do iOS, arrastando para o lado. Limpar aqui é
  // SÓ visual, e o próprio painel avisa: trilha de auditoria que apaga
  // sozinha não é trilha de auditoria, e as configurações prometem o
  // contrário. O que sai fica guardado em memória para não voltar a cada
  // troca de fragmento dentro da mesma visita.
  var eventosDispensados = [];

  function chaveDoEvento(item) {
    var acao = item.querySelector(".admita-evento-acao");
    var meta = item.querySelector(".admita-evento-meta");
    return (acao ? acao.textContent : "") + "|" + (meta ? meta.textContent : "");
  }

  // A caixa não rola, então o que não couber tem que SAIR, nunca aparecer
  // pela metade. Mede quantos eventos cabem inteiros e soma o resto na
  // linha do rodapé, com a contagem certa.
  function ajustarTrilha() {
    var painel = app.querySelector(".admita-auditoria");
    var lista = app.querySelector(".admita-auditoria-lista");
    if (!painel || !lista || painel.hidden) return;

    var marca = painel.querySelector(".admita-auditoria-marca");
    var rodape = painel.querySelector("[data-auditoria-mais]");
    var eventos = Array.prototype.slice.call(lista.querySelectorAll(".admita-evento"));
    eventos.forEach(function (item) { item.hidden = false; });

    var fundo = painel.getBoundingClientRect().bottom
      - painel.clientHeight * 0 - 0;
    // o pé do painel é a borda de cima da marca, menos a linha do rodapé
    if (marca) fundo = marca.getBoundingClientRect().top - 8;
    if (rodape && !rodape.hidden) fundo -= rodape.getBoundingClientRect().height + 6;

    var escondidos = 0;
    var cabendo = 0;
    for (var i = 0; i < eventos.length; i++) {
      if (cabendo >= 1 && eventos[i].getBoundingClientRect().bottom > fundo) {
        for (var j = i; j < eventos.length; j++) {
          eventos[j].hidden = true;
          escondidos++;
        }
        break;
      }
      cabendo++;
    }

    if (rodape) {
      var totalRestante = (parseInt(rodape.getAttribute("data-anteriores"), 10) || 0) + escondidos;
      if (totalRestante > 0) {
        rodape.hidden = false;
        rodape.textContent = "e mais " + totalRestante + " evento" +
          (totalRestante === 1 ? "" : "s") + " " +
          (totalRestante === 1 ? "anterior" : "anteriores") + ".";
      } else {
        rodape.hidden = true;
      }
    }
  }

  function atualizarVazioDaTrilha() {
    var lista = app.querySelector(".admita-auditoria-lista");
    if (!lista) return;
    var restantes = lista.querySelectorAll(".admita-evento:not(.saindo)").length;
    var aviso = app.querySelector("[data-auditoria-vazio]");
    if (aviso) aviso.hidden = restantes > 0;
    ajustarTrilha();
    var mais = app.querySelector("[data-auditoria-mais]");
    if (mais && restantes === 0) mais.hidden = true;
  }

  function dispensarEvento(item, guardar) {
    if (!item || item.classList.contains("saindo")) return;
    if (guardar !== false) eventosDispensados.push(chaveDoEvento(item));
    var corpo = item.querySelector(".admita-evento-corpo");
    item.style.height = item.offsetHeight + "px";
    item.classList.add("saindo");
    if (corpo) {
      corpo.classList.remove("arrastando");
      corpo.style.transition = "transform .28s cubic-bezier(.4,0,.2,1)";
      corpo.style.transform = "translateX(-110%)";
    }
    window.setTimeout(function () {
      item.style.height = "0px";
      item.style.marginTop = "0px";
    }, 30);
    window.setTimeout(function () {
      item.remove();
      atualizarVazioDaTrilha();
    }, 330);
  }

  function reaplicarDispensados() {
    if (!eventosDispensados.length) return;
    app.querySelectorAll(".admita-evento").forEach(function (item) {
      if (eventosDispensados.indexOf(chaveDoEvento(item)) !== -1) item.remove();
    });
    atualizarVazioDaTrilha();
  }

  // arrastar para o lado, como na central de notificações do iOS
  var LIMITE_DISPENSA = 92;
  (function ligarArrasto() {
    var alvo = null, inicioX = 0, deslocado = 0;

    app.addEventListener("pointerdown", function (evento) {
      var corpo = evento.target.closest(".admita-evento-corpo");
      if (!corpo) return;
      alvo = corpo;
      inicioX = evento.clientX;
      deslocado = 0;
      corpo.classList.add("arrastando");
      corpo.setPointerCapture(evento.pointerId);
    });

    app.addEventListener("pointermove", function (evento) {
      if (!alvo) return;
      deslocado = Math.min(0, evento.clientX - inicioX);   // só para a esquerda
      alvo.style.transform = "translateX(" + deslocado + "px)";
      var item = alvo.closest(".admita-evento");
      if (item) item.classList.toggle("deslizando", deslocado < -8);
    });

    function soltar() {
      if (!alvo) return;
      var corpo = alvo;
      var item = corpo.closest(".admita-evento");
      corpo.classList.remove("arrastando");
      if (deslocado <= -LIMITE_DISPENSA) {
        dispensarEvento(item, true);
      } else {
        corpo.classList.add("voltando");
        corpo.style.transform = "translateX(0)";
        if (item) item.classList.remove("deslizando");
        window.setTimeout(function () { corpo.classList.remove("voltando"); }, 300);
      }
      alvo = null;
      deslocado = 0;
    }
    app.addEventListener("pointerup", soltar);
    app.addEventListener("pointercancel", soltar);
  })();

  app.addEventListener("click", function (evento) {
    if (evento.target.closest("[data-auditoria-limpar]")) {
      // limpa os eventos que estão na tela, um atrás do outro
      var visiveis = Array.prototype.slice.call(
        app.querySelectorAll(".admita-evento:not(.saindo)")
      );
      visiveis.forEach(function (item, i) {
        window.setTimeout(function () { dispensarEvento(item, true); }, i * 70);
      });
      return;
    }
    if (evento.target.closest("[data-auditoria-limpar-tudo]")) {
      var todos = Array.prototype.slice.call(
        app.querySelectorAll(".admita-evento:not(.saindo)")
      );
      todos.forEach(function (item, i) {
        window.setTimeout(function () { dispensarEvento(item, true); }, i * 45);
      });
      var mais = app.querySelector("[data-auditoria-mais]");
      if (mais) mais.hidden = true;
      var contagem = app.querySelector("[data-auditoria-contagem]");
      if (contagem) contagem.textContent = "nenhum evento na tela";
      return;
    }
  });

  // ======================================================== entrada ====
  // Splash da marca, tela de acesso e o usuário fictício entrando. É o que
  // conta, em três segundos, que isto é um sistema com sessão e com gente
  // dentro, e não uma tela parada. Regras: qualquer clique ou tecla pula,
  // quem pediu menos movimento não vê nada disso (o CSS esconde a camada),
  // e NENHUMA senha existe de verdade: os pontinhos são desenhados.
  var entrada = document.getElementById("admita-entrada");
  var EMAIL_DEMO = (document.getElementById("admita-app") || {}).dataset
    ? (document.getElementById("admita-app").dataset.email || "teste@leandrofurtado.com.br")
    : "teste@leandrofurtado.com.br";

  function menosMovimento() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function encerrarEntrada() {
    if (!entrada || entrada.hidden) return;
    entrada.style.animation = "none";  // desarma a rede de segurança do CSS
    entrada.classList.add("saindo");
    window.setTimeout(function () {
      entrada.hidden = true;
      app.classList.add("revelando");
      aplicarEstadoUI();
      window.setTimeout(function () { app.classList.remove("revelando"); }, 1100);
    }, 500);
  }

  var relogiosDaEntrada = [];
  function pularEntrada() {
    relogiosDaEntrada.forEach(window.clearTimeout);
    relogiosDaEntrada = [];
    encerrarEntrada();
  }
  function passo(ms, fn) { relogiosDaEntrada.push(window.setTimeout(fn, ms)); }

  function tocarEntrada() {
    if (!entrada) return;
    // quem pede menos movimento não vê nada: a camada some no mesmo quadro
    if (menosMovimento()) {
      entrada.hidden = true;
      return;
    }

    var campoEmail = entrada.querySelector("[data-entrada-email]");
    var campoSenha = entrada.querySelector("[data-entrada-senha]");
    var botao = entrada.querySelector("[data-entrada-botao]");
    var cursor = campoEmail && campoEmail.querySelector(".admita-entrada-cursor");

    passo(950, function () { entrada.classList.add("passo-login"); });

    // digita o e-mail letra a letra, com o campo em foco
    passo(1450, function () {
      if (campoEmail) campoEmail.classList.add("ativo");
      var i = 0;
      var teclar = window.setInterval(function () {
        if (i >= EMAIL_DEMO.length) {
          window.clearInterval(teclar);
          return;
        }
        var letra = document.createTextNode(EMAIL_DEMO.charAt(i++));
        if (cursor) campoEmail.insertBefore(letra, cursor);
        else campoEmail.appendChild(letra);
      }, 38);
      relogiosDaEntrada.push(teclar);
    });

    // a senha aparece como pontinhos: nada é digitado nem guardado
    passo(2350, function () {
      if (campoEmail) campoEmail.classList.remove("ativo");
      if (cursor) cursor.remove();
      if (campoSenha) campoSenha.classList.add("ativo");
      var pontos = 0;
      var pingar = window.setInterval(function () {
        if (pontos >= 9) {
          window.clearInterval(pingar);
          return;
        }
        pontos++;
        if (campoSenha) campoSenha.textContent = "•".repeat(pontos);
      }, 55);
      relogiosDaEntrada.push(pingar);
    });

    passo(3050, function () {
      if (campoSenha) campoSenha.classList.remove("ativo");
      if (botao) botao.classList.add("pressionado");
    });
    passo(3200, function () {
      if (botao) {
        botao.classList.remove("pressionado");
        botao.classList.add("carregando");
      }
    });
    passo(3850, function () {
      if (botao) {
        botao.classList.remove("carregando");
        botao.classList.add("ok");
        var txt = botao.querySelector(".admita-entrada-botao-txt");
        if (txt) txt.textContent = "Acesso liberado";
      }
    });
    passo(4300, function () {
      entrada.classList.add("passo-dentro");
      passo(420, encerrarEntrada);
    });

    entrada.addEventListener("click", pularEntrada);
    document.addEventListener("keydown", function pulaNaTecla(evento) {
      if (entrada.hidden) {
        document.removeEventListener("keydown", pulaNaTecla);
        return;
      }
      if (evento.key === "Escape" || evento.key === " " || evento.key === "Enter") {
        pularEntrada();
      }
    });
  }

  // Sair do sistema: mesma camada, sem o cartão de acesso. Só a marca, a
  // linha e o aviso, e então a vitrine. Um sistema de verdade não some da
  // tela sem dizer que encerrou a sessão.
  function sairDoSistema(destino) {
    if (!entrada || menosMovimento()) {
      window.location.href = destino;
      return;
    }
    entrada.classList.remove("passo-login", "passo-dentro", "saindo");
    entrada.classList.add("saindo-do-sistema");
    entrada.style.animation = "none";
    entrada.hidden = false;
    var status = entrada.querySelector("[data-entrada-status]");
    if (status) status.textContent = "encerrando a sessão";
    window.setTimeout(function () {
      if (status) status.textContent = "até a próxima, " + (app.dataset.usuario || "");
    }, 780);
    window.setTimeout(function () { window.location.href = destino; }, 1350);
  }

  document.addEventListener("click", function (evento) {
    var saida = evento.target.closest(
      ".lab-nav-voltar, .admita-sair, .admita-usuario-sair"
    );
    if (!saida) return;
    evento.preventDefault();
    sairDoSistema(saida.getAttribute("href") || "/lab");
  });

  sincronizarCargos();
  tocarEntrada();

  aplicarEstadoUI();

  // A primeira medição acontece antes das fontes carregarem, e fonte nova
  // muda a altura dos cartões: sem refazer a conta, um cartão ficava
  // cortado no primeiro paint e só se ajeitava se alguém mexesse na janela.
  window.requestAnimationFrame(aplicarEstadoUI);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(aplicarEstadoUI);
  }
  window.addEventListener("load", aplicarEstadoUI);

  // Girar o telefone ou redimensionar a janela muda quantos cards cabem.
  // Sem isto, a conta feita na carga vira mentira e o card volta a ser
  // cortado (§13b). Debounce curto para não medir a cada pixel.
  var relayout;
  window.addEventListener("resize", function () {
    window.clearTimeout(relayout);
    relayout = window.setTimeout(function () {
      ajustarAlturaDoMenu();
      aplicarPaginacao();
    }, 120);
  });

})();
