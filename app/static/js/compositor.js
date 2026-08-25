/* ==========================================================================
   Compositor de blocos do case

   A página do case é uma lista de blocos. Esta lista vive inteira aqui em
   memória e viaja num campo escondido em JSON quando você salva. Nada é
   gravado no servidor enquanto você monta: arrastar, duplicar e excluir mexem
   só na tela, e o Salvar do formulário grava tudo de uma vez. Isso evita o
   estado que mais atrapalha um editor — metade dos blocos gravada e a outra
   metade não.

   Duas coisas falam com o servidor antes da hora, porque não cabem em JSON:
   subir arquivo e resolver o link de um embed.
   ========================================================================== */
(function () {
  var raiz = document.querySelector("[data-compositor]");
  if (!raiz) return;

  var lista = raiz.querySelector("[data-cp-lista]");
  var campo = raiz.querySelector("[data-cp-json]");
  var conta = raiz.querySelector("[data-cp-conta]");
  var solte = raiz.querySelector("[data-cp-solte]");
  var entrada = raiz.querySelector("[data-cp-arquivos]");
  var caseId = raiz.dataset.case;
  var csrf = raiz.dataset.csrf;

  var TIPOS = {
    texto:    { nome: "Texto", ico: "texto" },
    image:    { nome: "Foto", ico: "imagem" },
    galeria:  { nome: "Galeria", ico: "galeria" },
    video:    { nome: "Vídeo", ico: "video" },
    reels:    { nome: "Reels", ico: "reels" },
    audio:    { nome: "Áudio", ico: "audio" },
    embed:    { nome: "Link", ico: "elo" },
    hashtags: { nome: "Hashtags", ico: "hashtag" },
    ficha:    { nome: "Ficha técnica", ico: "ficha" },
    numeros:  { nome: "Números", ico: "barras" },
    citacao:  { nome: "Citação", ico: "aspas" },
    divisor:  { nome: "Divisor", ico: "divisor" }
  };
  var VISUAIS = ["image", "galeria", "video", "reels", "audio", "embed"];

  var blocos = [];
  try {
    var cru = raiz.querySelector("[data-cp-inicial]");
    blocos = JSON.parse((cru && cru.textContent) || "[]") || [];
  } catch (e) { blocos = []; }

  /* ---------- desenho ---------- */

  /* os desenhos vêm do HTML (paleta + banco escondido), nunca de string no JS:
     assim existe um único lugar onde cada ícone é definido */
  function ico(nome) {
    var modelo = raiz.querySelector('.ico[data-ico="' + nome + '"]');
    return modelo ? modelo.outerHTML : "";
  }

  function esc(t) {
    return String(t == null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* uma linha de texto que diz o que tem dentro sem precisar abrir o bloco */
  function resumo(b) {
    var m = b.meta || {};
    if (b.kind === "texto") return (m.titulo || m.corpo || "").slice(0, 70) || "vazio";
    if (b.kind === "galeria") return ((m.fotos || []).length) + " foto(s)";
    if (b.kind === "hashtags") return (m.tags || []).map(function (t) { return "#" + t; }).join(" ").slice(0, 70);
    if (b.kind === "ficha") return ((m.linhas || []).length) + " linha(s)";
    if (b.kind === "numeros") return (m.itens || []).map(function (n) { return n.valor; }).join(" ·︎ ");
    if (b.kind === "citacao") return (m.frase || "").slice(0, 70);
    if (b.kind === "divisor") return m.rotulo || "—";
    if (m.fonte === "link") return (m.provider ? m.provider + " ·︎ " : "") + (b.src || "");
    return b.caption || (b.src || "").split("/").pop() || "sem arquivo";
  }

  function campoTexto(rot, chave, valor, linhas) {
    return '<label class="cp-campo"><span>' + rot + "</span>" +
      (linhas
        ? '<textarea rows="' + linhas + '" data-k="' + chave + '">' + esc(valor) + "</textarea>"
        : '<input data-k="' + chave + '" value="' + esc(valor) + '">') +
      "</label>";
  }

  function corpo(b, i) {
    var m = b.meta || {};
    var h = "";

    if (b.kind === "texto") {
      h += campoTexto("Título (opcional)", "meta.titulo", m.titulo || "");
      h += campoTexto("Texto", "meta.corpo", m.corpo || "", 6);
      h += '<p class="cp-dica">Uma linha em branco separa parágrafos. **negrito** e *itálico* funcionam.</p>';
    }

    if (b.kind === "image") {
      h += '<div class="cp-previa">' + (b.thumb || b.src
        ? '<img src="/media/' + esc(b.thumb || b.src) + '" alt="">'
        : '<span class="cp-vazio">sem arquivo</span>') + "</div>";
      h += campoTexto("Legenda", "caption", b.caption || "");
      h += trocaArquivo(i, "image/*", "Trocar a foto");
    }

    if (b.kind === "galeria") {
      h += '<div class="cp-galeria">';
      (m.fotos || []).forEach(function (f, j) {
        h += '<figure class="cp-g-foto"><img src="/media/' + esc(f.thumb || f.src) + '" alt="">' +
          '<button type="button" class="cp-g-x" data-tirar="' + j + '" aria-label="Tirar foto">×︎</button>' +
          '<input class="cp-g-cap" data-gk="' + j + '" placeholder="legenda" value="' + esc(f.legenda || "") + '"></figure>';
      });
      h += "</div>";
      h += '<div class="cp-linha">' +
        '<label class="cp-campo cp-curto"><span>Colunas</span><select data-k="meta.colunas">' +
        [2, 3, 4].map(function (n) {
          return '<option value="' + n + '"' + ((m.colunas || 3) === n ? " selected" : "") + ">" + n + "</option>";
        }).join("") + "</select></label>" +
        botaoArquivo(i, "image/*", "Adicionar fotos", "galeria") + "</div>";
    }

    if (b.kind === "video" || b.kind === "reels" || b.kind === "audio") {
      var qual = b.kind === "audio" ? "áudio" : "vídeo";
      h += '<div class="cp-fonte" role="group">' +
        botaoFonte(b, "arquivo", "Arquivo") + botaoFonte(b, "link", "Link") + "</div>";
      if (m.fonte === "link") {
        h += '<div class="cp-linha">' + campoTexto("Endereço", "src", b.src || "") +
          '<button type="button" class="btn sm" data-resolver>Buscar prévia</button></div>';
        if (m.provider) h += '<p class="cp-dica">Reconhecido: <b>' + esc(m.provider) + "</b>.</p>";
        else h += '<p class="cp-dica">' + (b.kind === "audio"
          ? "Cole o link do Spotify, SoundCloud ou Deezer."
          : "Cole o link do YouTube, Vimeo ou Instagram.") + "</p>";
      } else {
        h += '<div class="cp-previa">' + (b.src
          ? '<span class="cp-arquivo">' + esc(b.src.split("/").pop()) + "</span>"
          : '<span class="cp-vazio">sem arquivo</span>') + "</div>";
        h += trocaArquivo(i, b.kind === "audio" ? "audio/*" : "video/*", "Enviar " + qual);
      }
      h += campoTexto("Legenda", "caption", b.caption || "");
    }

    if (b.kind === "embed") {
      h += '<div class="cp-linha">' + campoTexto("Endereço", "src", b.src || "") +
        '<button type="button" class="btn sm" data-resolver>Buscar prévia</button></div>';
      if (m.title) h += '<p class="cp-dica">' + esc(m.site || "") + " — <b>" + esc(m.title) + "</b></p>";
      h += campoTexto("Legenda", "caption", b.caption || "");
    }

    if (b.kind === "hashtags") {
      h += campoTexto("Tags (separadas por vírgula)", "meta.tags_str", (m.tags || []).join(", "));
      h += '<p class="cp-dica">O # entra sozinho na hora de mostrar.</p>';
    }

    if (b.kind === "ficha") {
      h += campoTexto("Título (opcional)", "meta.titulo", m.titulo || "");
      h += '<div class="cp-pares">';
      (m.linhas || []).forEach(function (l, j) {
        h += '<div class="cp-par">' +
          '<input data-pk="' + j + '.rotulo" placeholder="Função" value="' + esc(l.rotulo) + '">' +
          '<input data-pk="' + j + '.valor" placeholder="Nome" value="' + esc(l.valor) + '">' +
          '<button type="button" class="cp-x" data-tirar-par="' + j + '" aria-label="Remover">×︎</button></div>';
      });
      h += "</div>";
      h += '<button type="button" class="btn ghost sm" data-mais-par>+ Linha</button>';
    }

    if (b.kind === "numeros") {
      h += '<div class="cp-pares">';
      (m.itens || []).forEach(function (n, j) {
        h += '<div class="cp-par">' +
          '<input data-nk="' + j + '.valor" placeholder="+240%" value="' + esc(n.valor) + '">' +
          '<input data-nk="' + j + '.rotulo" placeholder="de alcance orgânico" value="' + esc(n.rotulo) + '">' +
          '<button type="button" class="cp-x" data-tirar-num="' + j + '" aria-label="Remover">×︎</button></div>';
      });
      h += "</div>";
      h += '<button type="button" class="btn ghost sm" data-mais-num>+ Número</button>';
    }

    if (b.kind === "citacao") {
      h += campoTexto("Frase", "meta.frase", m.frase || "", 3);
      h += campoTexto("Autor", "meta.autor", m.autor || "");
    }

    if (b.kind === "divisor") {
      h += campoTexto("Título do capítulo (opcional)", "meta.rotulo", m.rotulo || "");
    }

    return h;
  }

  function botaoFonte(b, valor, rotulo) {
    var on = (b.meta || {}).fonte === valor || (valor === "arquivo" && !(b.meta || {}).fonte);
    return '<button type="button" class="cp-f' + (on ? " on" : "") + '" data-fonte="' + valor + '">' + rotulo + "</button>";
  }

  function botaoArquivo(i, accept, rotulo, modo) {
    if (!caseId) return '<span class="cp-dica">Salve o case para enviar arquivos.</span>';
    return '<button type="button" class="btn ghost sm" data-subir="' + (modo || "trocar") +
      '" data-accept="' + accept + '">' + rotulo + "</button>";
  }

  function trocaArquivo(i, accept, rotulo) {
    return '<div class="cp-linha">' + botaoArquivo(i, accept, rotulo) + "</div>";
  }

  function desenhar() {
    lista.innerHTML = "";
    blocos.forEach(function (b, i) {
      var t = TIPOS[b.kind] || { nome: b.kind, ico: "texto" };
      var art = document.createElement("article");
      art.className = "cp-bloco";
      art.dataset.i = i;
      if (b._aberto) art.classList.add("aberto");
      art.innerHTML =
        '<header class="cp-b-topo">' +
          '<button type="button" class="cp-arrasta" draggable="true" aria-label="Arrastar para reordenar">' + ico("arrasta") + "</button>" +
          '<button type="button" class="cp-b-nome" data-abrir>' + ico(t.ico) +
            "<b>" + t.nome + "</b><span>" + esc(resumo(b)) + "</span></button>" +
          '<div class="cp-b-acoes">' +
            (VISUAIS.indexOf(b.kind) >= 0 && b.kind !== "galeria"
              ? '<select class="cp-larg" data-k="layout" title="Largura">' +
                ["full", "half", "tall"].map(function (l) {
                  var rot = { full: "Cheia", half: "Metade", tall: "Alta" }[l];
                  return '<option value="' + l + '"' + (b.layout === l ? " selected" : "") + ">" + rot + "</option>";
                }).join("") + "</select>"
              : "") +
            '<button type="button" data-mover="-1" aria-label="Subir">' + ico("sobe-um") + "</button>" +
            '<button type="button" data-mover="1" aria-label="Descer">' + ico("desce-um") + "</button>" +
            '<button type="button" data-duplicar aria-label="Duplicar">' + ico("copia") + "</button>" +
            '<button type="button" class="danger" data-excluir aria-label="Excluir">' + ico("lixeira") + "</button>" +
            '<button type="button" class="cp-seta" data-abrir aria-label="Abrir">' + ico("recolher") + "</button>" +
          "</div>" +
        "</header>" +
        '<div class="cp-b-corpo">' + corpo(b, i) + "</div>";
      lista.appendChild(art);
    });
    if (!blocos.length) {
      lista.innerHTML = '<p class="cp-nada">Nenhum bloco ainda. Escolha um tipo acima ou solte um arquivo aqui embaixo.</p>';
    }
    conta.textContent = blocos.length + (blocos.length === 1 ? " bloco" : " blocos");
    salvarCampo();
  }

  function salvarCampo() {
    campo.value = JSON.stringify(blocos.map(function (b) {
      var c = {}; for (var k in b) if (k !== "_aberto") c[k] = b[k];
      return c;
    }));
  }

  /* ---------- modelo ---------- */

  function novo(kind) {
    var b = { kind: kind, src: "", thumb: "", caption: "", layout: "full", meta: {}, _aberto: true };
    if (kind === "galeria") b.meta = { fotos: [], colunas: 3 };
    if (kind === "ficha") b.meta = { titulo: "", linhas: [{ rotulo: "", valor: "" }] };
    if (kind === "numeros") b.meta = { itens: [{ valor: "", rotulo: "" }] };
    if (kind === "hashtags") b.meta = { tags: [] };
    if (["video", "reels", "audio", "embed"].indexOf(kind) >= 0) b.meta = { fonte: kind === "embed" ? "link" : "arquivo" };
    return b;
  }

  function definir(b, chave, valor) {
    if (chave === "meta.tags_str") {
      b.meta.tags = valor.split(",").map(function (t) { return t.trim().replace(/^#/, ""); })
        .filter(Boolean);
      return;
    }
    if (chave.indexOf("meta.") === 0) b.meta[chave.slice(5)] = valor;
    else b[chave] = valor;
  }

  /* ---------- eventos ---------- */

  raiz.querySelectorAll("[data-add]").forEach(function (bt) {
    bt.addEventListener("click", function () {
      blocos.push(novo(bt.dataset.add));
      desenhar();
      var ultimo = lista.lastElementChild;
      if (ultimo) {
        ultimo.scrollIntoView({ block: "center", behavior: "smooth" });
        var foco = ultimo.querySelector("input, textarea, select");
        if (foco) foco.focus();
      }
    });
  });

  lista.addEventListener("click", function (e) {
    var art = e.target.closest(".cp-bloco");
    if (!art) return;
    var i = +art.dataset.i, b = blocos[i];

    if (e.target.closest("[data-abrir]")) { b._aberto = !b._aberto; art.classList.toggle("aberto"); return; }
    if (e.target.closest("[data-excluir]")) { blocos.splice(i, 1); desenhar(); return; }
    if (e.target.closest("[data-duplicar]")) {
      blocos.splice(i + 1, 0, JSON.parse(JSON.stringify(b))); desenhar(); return;
    }
    var mover = e.target.closest("[data-mover]");
    if (mover) {
      var j = i + (+mover.dataset.mover);
      if (j >= 0 && j < blocos.length) { blocos.splice(j, 0, blocos.splice(i, 1)[0]); desenhar(); }
      return;
    }
    var fonte = e.target.closest("[data-fonte]");
    if (fonte) { b.meta.fonte = fonte.dataset.fonte; b.src = ""; desenhar(); return; }

    var tirar = e.target.closest("[data-tirar]");
    if (tirar) { b.meta.fotos.splice(+tirar.dataset.tirar, 1); desenhar(); return; }
    if (e.target.closest("[data-mais-par]")) { b.meta.linhas.push({ rotulo: "", valor: "" }); desenhar(); return; }
    var tp = e.target.closest("[data-tirar-par]");
    if (tp) { b.meta.linhas.splice(+tp.dataset.tirarPar, 1); desenhar(); return; }
    if (e.target.closest("[data-mais-num]")) { b.meta.itens.push({ valor: "", rotulo: "" }); desenhar(); return; }
    var tn = e.target.closest("[data-tirar-num]");
    if (tn) { b.meta.itens.splice(+tn.dataset.tirarNum, 1); desenhar(); return; }

    var subir = e.target.closest("[data-subir]");
    if (subir) { pedirArquivo(subir.dataset.accept, i, subir.dataset.subir); return; }
    if (e.target.closest("[data-resolver]")) { resolver(art, b); return; }
  });

  /* Digitar não redesenha: perderia o cursor a cada tecla. Só o resumo do
     cabeçalho acompanha, e o campo escondido é reescrito. */
  lista.addEventListener("input", function (e) {
    var art = e.target.closest(".cp-bloco");
    if (!art) return;
    var b = blocos[+art.dataset.i];
    var alvo = e.target;

    if (alvo.dataset.k) {
      var v = alvo.value;
      if (alvo.dataset.k === "meta.colunas") v = +v;
      definir(b, alvo.dataset.k, v);
    } else if (alvo.dataset.gk != null) {
      b.meta.fotos[+alvo.dataset.gk].legenda = alvo.value;
    } else if (alvo.dataset.pk) {
      var p = alvo.dataset.pk.split(".");
      b.meta.linhas[+p[0]][p[1]] = alvo.value;
    } else if (alvo.dataset.nk) {
      var n = alvo.dataset.nk.split(".");
      b.meta.itens[+n[0]][n[1]] = alvo.value;
    }
    var eco = art.querySelector(".cp-b-nome span");
    if (eco) eco.textContent = resumo(b);
    salvarCampo();
  });

  /* ---------- arrastar para reordenar ---------- */

  var arrastando = null;
  lista.addEventListener("dragstart", function (e) {
    var alca = e.target.closest(".cp-arrasta");
    if (!alca) { e.preventDefault(); return; }
    arrastando = alca.closest(".cp-bloco");
    arrastando.classList.add("arrastando");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", arrastando.dataset.i);
  });
  lista.addEventListener("dragover", function (e) {
    if (!arrastando) return;
    e.preventDefault();
    var sobre = e.target.closest(".cp-bloco");
    if (!sobre || sobre === arrastando) return;
    var r = sobre.getBoundingClientRect();
    var depois = (e.clientY - r.top) > r.height / 2;
    lista.insertBefore(arrastando, depois ? sobre.nextSibling : sobre);
  });
  lista.addEventListener("dragend", function () {
    if (!arrastando) return;
    arrastando.classList.remove("arrastando");
    arrastando = null;
    var ordem = [].map.call(lista.querySelectorAll(".cp-bloco"), function (el) { return blocos[+el.dataset.i]; });
    blocos = ordem;
    desenhar();
  });

  /* ---------- arquivos ---------- */

  var alvoUpload = { i: -1, modo: "novo" };

  function pedirArquivo(accept, i, modo) {
    if (!caseId) { alert("Salve o case uma vez para poder enviar arquivos."); return; }
    alvoUpload = { i: i, modo: modo || "novo" };
    entrada.accept = accept || "image/*,video/*,audio/*";
    entrada.multiple = modo !== "trocar";
    entrada.value = "";
    entrada.click();
  }

  raiz.querySelector("[data-cp-escolher]").addEventListener("click", function () {
    pedirArquivo("image/*,video/*,audio/*", -1, "novo");
  });
  entrada.addEventListener("change", function () { enviar(entrada.files); });

  ["dragenter", "dragover"].forEach(function (ev) {
    raiz.addEventListener(ev, function (e) {
      if (!e.dataTransfer || arrastando) return;
      if ([].indexOf.call(e.dataTransfer.types || [], "Files") < 0) return;
      e.preventDefault(); solte.classList.add("sobre");
    });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    raiz.addEventListener(ev, function (e) {
      if (ev === "drop" && e.dataTransfer && e.dataTransfer.files.length) {
        e.preventDefault();
        alvoUpload = { i: -1, modo: "novo" };
        enviar(e.dataTransfer.files);
      }
      solte.classList.remove("sobre");
    });
  });

  async function enviar(arquivos) {
    if (!arquivos || !arquivos.length) return;
    if (!caseId) { alert("Salve o case uma vez para poder enviar arquivos."); return; }
    solte.classList.add("enviando");
    var fd = new FormData();
    fd.append("csrf", csrf);
    [].forEach.call(arquivos, function (f) { fd.append("files", f); });
    try {
      var r = await fetch("/admin/cases/" + caseId + "/arquivo", { method: "POST", body: fd });
      var d = await r.json();
      if (!r.ok || d.error) throw new Error(d.error || "falha no envio");
      aplicarArquivos(d.arquivos || []);
    } catch (e) {
      alert("Não consegui enviar: " + e.message);
    } finally {
      solte.classList.remove("enviando");
    }
  }

  function aplicarArquivos(arqs) {
    if (alvoUpload.modo === "galeria" && blocos[alvoUpload.i]) {
      arqs.forEach(function (a) {
        if (a.kind === "image") blocos[alvoUpload.i].meta.fotos.push({ src: a.src, thumb: a.thumb, legenda: "" });
      });
    } else if (alvoUpload.modo === "trocar" && blocos[alvoUpload.i]) {
      var a = arqs[0];
      if (a) { blocos[alvoUpload.i].src = a.src; blocos[alvoUpload.i].thumb = a.thumb; }
    } else {
      arqs.forEach(function (a) {
        var b = novo(a.kind === "image" ? "image" : a.kind);
        b.src = a.src; b.thumb = a.thumb; b.meta.fonte = "arquivo"; b._aberto = false;
        blocos.push(b);
      });
    }
    desenhar();
  }

  async function resolver(art, b) {
    var url = (art.querySelector('[data-k="src"]') || {}).value || b.src;
    if (!url) return;
    var fd = new FormData();
    fd.append("csrf", csrf); fd.append("url", url);
    try {
      var r = await fetch("/admin/embed/resolver", { method: "POST", body: fd });
      var d = await r.json();
      if (!r.ok || d.error) throw new Error(d.error || "endereço não reconhecido");
      b.src = d.url;
      b.meta = Object.assign({}, b.meta, d.meta, { fonte: "link" });
      desenhar();
    } catch (e) {
      alert("Não consegui ler esse endereço: " + e.message);
    }
  }

  desenhar();
})();
