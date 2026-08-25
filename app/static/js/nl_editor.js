/* Editor visual da newsletter.
 *
 * O palco não é uma prévia ao lado do formulário: ele é o formulário. Cada bloco é
 * editável no lugar, com a mesma tipografia e as mesmas cores do e-mail que vai sair.
 * A lista de blocos é serializada em JSON num campo escondido na hora de salvar.
 */
(function () {
  "use strict";

  var palco = document.getElementById("edBlocos");
  if (!palco) return;

  var campoJSON = document.getElementById("blocosJSON");
  var form = document.getElementById("formNL");
  var blocos = [];

  try {
    blocos = JSON.parse(document.getElementById("blocosIniciais").textContent) || [];
  } catch (e) {
    blocos = [];
  }

  var VAZIOS = {
    titulo: { t: "titulo", v: "Um título de seção" },
    texto: { t: "texto", v: "Escreva aqui. Use **negrito** e [link](https://exemplo.com)." },
    destaque: { t: "destaque", v: "Uma frase que merece destaque\nOutra linha, se precisar" },
    lista: { t: "lista", v: ["Primeiro item;", "Segundo item;", "Último item."] },
    imagem: { t: "imagem", v: "", alt: "" },
    botao: { t: "botao", v: "Ver o site", url: "https://leandrofurtado.com.br" },
    divisor: { t: "divisor" },
    espaco: { t: "espaco" },
  };

  var NOMES = {
    titulo: "Título", texto: "Parágrafo", destaque: "Destaque", lista: "Lista em caixa",
    imagem: "Imagem", botao: "Botão", divisor: "Divisor", espaco: "Espaço",
  };

  /* data do cabeçalho, igual à do e-mail */
  var MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
               "jul", "ago", "set", "out", "nov", "dez"];
  var hoje = new Date();
  var elData = document.getElementById("edData");
  if (elData) {
    elData.textContent = String(hoje.getDate()).padStart(2, "0") + " " +
      MESES[hoje.getMonth()].toUpperCase() + " " + hoje.getFullYear();
  }

  function serializar() {
    campoJSON.value = JSON.stringify(blocos);
  }

  function mover(de, para) {
    if (para < 0 || para >= blocos.length) return;
    var item = blocos.splice(de, 1)[0];
    blocos.splice(para, 0, item);
    desenhar();
  }

  function remover(i) {
    blocos.splice(i, 1);
    desenhar();
  }

  function acrescentar(tipo, posicao) {
    var novo = JSON.parse(JSON.stringify(VAZIOS[tipo] || VAZIOS.texto));
    if (typeof posicao === "number") blocos.splice(posicao, 0, novo);
    else blocos.push(novo);
    desenhar();
    // foca o campo do bloco recém-criado, para já sair escrevendo
    var alvo = palco.querySelector('[data-i="' + (typeof posicao === "number" ? posicao : blocos.length - 1) + '"] [data-campo]');
    if (alvo) { alvo.focus(); if (alvo.select) alvo.select(); }
  }

  function autoAltura(el) {
    el.style.height = "auto";
    // 2px de folga: sem isso, arredondamento de subpixel faz aparecer barra de rolagem
    el.style.height = (el.scrollHeight + 2) + "px";
  }

  /* refaz as alturas quando a fonte termina de carregar, senão a medida sai errada */
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      palco.querySelectorAll("textarea").forEach(autoAltura);
    });
  }

  function miolo(b, i) {
    var t = b.t;
    if (t === "divisor") return '<hr class="edb-divisor">';
    if (t === "espaco") return '<div class="edb-espaco">espaço</div>';

    if (t === "imagem") {
      return '' +
        '<div class="edb-img">' +
          (b.v ? '<img src="/media/' + b.v + '" alt="">' : '<span class="edb-img-vazio">nenhuma imagem</span>') +
          '<label class="btn ghost edb-file">' +
            '<input type="file" accept="image/*" data-upload="' + i + '" hidden>' +
            (b.v ? "Trocar imagem" : "Escolher imagem") +
          '</label>' +
        '</div>';
    }

    if (t === "botao") {
      return '' +
        '<div class="edb-botao">' +
          '<span class="edb-pill"><input data-campo="v" value="' + esc(b.v || "") + '" placeholder="TEXTO DO BOTÃO"> →︎</span>' +
          '<input class="edb-url" data-campo="url" value="' + esc(b.url || "") + '" placeholder="https://...">' +
        '</div>';
    }

    if (t === "lista") {
      var itens = (b.v || []).join("\n");
      return '<textarea class="edb-lista" data-campo="v" rows="3" placeholder="Um item por linha">' +
        esc(itens) + "</textarea>";
    }

    var classe = t === "titulo" ? "edb-titulo" : (t === "destaque" ? "edb-destaque" : "edb-texto");
    return '<textarea class="' + classe + '" data-campo="v" rows="2">' + esc(b.v || "") + "</textarea>";
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function desenhar() {
    palco.innerHTML = "";
    if (!blocos.length) {
      palco.innerHTML = '<p class="ed-vazio">Nenhum bloco ainda. Escolha um na coluna da esquerda.</p>';
      serializar();
      return;
    }

    blocos.forEach(function (b, i) {
      var el = document.createElement("div");
      el.className = "edb";
      el.dataset.i = i;
      el.draggable = true;
      el.innerHTML =
        '<div class="edb-barra">' +
          '<span class="edb-nome">⠿︎ ' + (NOMES[b.t] || b.t) + "</span>" +
          '<span class="edb-acoes">' +
            '<button type="button" data-acao="cima" title="Subir">↑︎</button>' +
            '<button type="button" data-acao="baixo" title="Descer">↓︎</button>' +
            '<button type="button" data-acao="dup" title="Duplicar">⧉︎</button>' +
            '<button type="button" data-acao="del" title="Remover">✕︎</button>' +
          "</span>" +
        "</div>" +
        '<div class="edb-miolo">' + miolo(b, i) + "</div>";
      palco.appendChild(el);
    });

    palco.querySelectorAll("textarea").forEach(autoAltura);
    serializar();
  }

  /* edição no lugar */
  palco.addEventListener("input", function (e) {
    var campo = e.target.dataset.campo;
    if (!campo) return;
    var i = +e.target.closest(".edb").dataset.i;
    var b = blocos[i];
    if (b.t === "lista" && campo === "v") {
      b.v = e.target.value.split("\n").filter(function (l) { return l.trim(); });
    } else {
      b[campo] = e.target.value;
    }
    if (e.target.tagName === "TEXTAREA") autoAltura(e.target);
    serializar();
  });

  /* ações da barra do bloco */
  palco.addEventListener("click", function (e) {
    var botao = e.target.closest("[data-acao]");
    if (!botao) return;
    var i = +botao.closest(".edb").dataset.i;
    var acao = botao.dataset.acao;
    if (acao === "cima") mover(i, i - 1);
    else if (acao === "baixo") mover(i, i + 1);
    else if (acao === "dup") { blocos.splice(i + 1, 0, JSON.parse(JSON.stringify(blocos[i]))); desenhar(); }
    else if (acao === "del") remover(i);
  });

  /* upload de imagem sem sair da página */
  palco.addEventListener("change", function (e) {
    var idx = e.target.dataset.upload;
    if (idx === undefined || !e.target.files[0]) return;
    var i = +idx;
    var dados = new FormData();
    dados.append("csrf", window.CSRF);
    dados.append("file", e.target.files[0]);
    var rotulo = e.target.closest(".edb-file");
    if (rotulo) rotulo.textContent = "enviando...";
    fetch("/admin/newsletter/upload", { method: "POST", body: dados })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok) { blocos[i].v = j.src; desenhar(); }
        else { alert(j.erro || "Falhou o envio da imagem"); desenhar(); }
      })
      .catch(function () { alert("Falhou o envio da imagem"); desenhar(); });
  });

  /* paleta: clique acrescenta no fim */
  document.querySelectorAll("[data-add]").forEach(function (chip) {
    chip.addEventListener("click", function () { acrescentar(chip.dataset.add); });
    chip.addEventListener("dragstart", function (ev) {
      ev.dataTransfer.setData("text/novo", chip.dataset.add);
      ev.dataTransfer.effectAllowed = "copy";
    });
  });

  var addFim = document.getElementById("edAddFim");
  if (addFim) addFim.addEventListener("click", function () { acrescentar("texto"); });

  /* arrastar: reordenar os existentes e soltar os novos da paleta */
  var arrastando = null;

  palco.addEventListener("dragstart", function (e) {
    var el = e.target.closest(".edb");
    if (!el) return;
    arrastando = +el.dataset.i;
    e.dataTransfer.effectAllowed = "move";
    el.classList.add("arrastando");
  });

  palco.addEventListener("dragend", function () {
    palco.querySelectorAll(".edb").forEach(function (x) {
      x.classList.remove("arrastando", "alvo");
    });
    arrastando = null;
  });

  palco.addEventListener("dragover", function (e) {
    e.preventDefault();
    var el = e.target.closest(".edb");
    palco.querySelectorAll(".edb").forEach(function (x) { x.classList.remove("alvo"); });
    if (el) el.classList.add("alvo");
  });

  palco.addEventListener("drop", function (e) {
    e.preventDefault();
    var el = e.target.closest(".edb");
    var destino = el ? +el.dataset.i : blocos.length;
    var tipoNovo = e.dataTransfer.getData("text/novo");
    if (tipoNovo) {
      acrescentar(tipoNovo, destino);
    } else if (arrastando !== null && arrastando !== destino) {
      mover(arrastando, destino);
    }
  });

  if (form) form.addEventListener("submit", serializar);

  desenhar();
})();
