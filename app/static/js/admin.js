/* Admin — uploads drag&drop, embeds, reordenação, linhas dinâmicas do CV */
(() => {
  "use strict";
  const CSRF = window.CSRF;

  const post = async (url, body) => {
    const res = await fetch(url, { method: "POST", body });
    if (!res.ok) {
      let msg = "Erro";
      try { msg = (await res.json()).error || msg; } catch {}
      throw new Error(msg);
    }
    return res.json();
  };

  /* ---------- upload drag & drop ---------- */
  const uploader = document.getElementById("uploader");
  const fileInput = document.getElementById("fileInput");
  if (uploader) {
    const caseId = uploader.dataset.case;
    const send = async files => {
      if (!files.length) return;
      uploader.classList.add("over");
      uploader.querySelector("p").textContent = `Enviando ${files.length} arquivo(s)…`;
      const fd = new FormData();
      fd.append("csrf", CSRF);
      [...files].forEach(f => fd.append("files", f));
      try {
        await post(`/admin/cases/${caseId}/media`, fd);
        location.reload();
      } catch (e) {
        alert(e.message);
        location.reload();
      }
    };
    ["dragenter", "dragover"].forEach(ev => uploader.addEventListener(ev, e => { e.preventDefault(); uploader.classList.add("over"); }));
    ["dragleave", "drop"].forEach(ev => uploader.addEventListener(ev, e => { e.preventDefault(); if (ev === "dragleave") uploader.classList.remove("over"); }));
    uploader.addEventListener("drop", e => send(e.dataTransfer.files));
    if (fileInput) fileInput.addEventListener("change", () => send(fileInput.files));
  }

  /* ---------- embeds ---------- */
  const embedBtn = document.getElementById("embedBtn");
  if (embedBtn) {
    embedBtn.addEventListener("click", async () => {
      const input = document.getElementById("embedUrl");
      const url = input.value.trim();
      if (!url) return;
      const caseId = uploader.dataset.case;
      const fd = new FormData();
      fd.append("csrf", CSRF);
      fd.append("url", url);
      embedBtn.disabled = true;
      try { await post(`/admin/cases/${caseId}/embed`, fd); location.reload(); }
      catch (e) { alert(e.message); embedBtn.disabled = false; }
    });
  }

  /* ---------- edição inline de mídia (legenda/layout) ---------- */
  document.querySelectorAll(".media-row").forEach(row => {
    const id = row.dataset.id;
    const save = async () => {
      const fd = new FormData();
      fd.append("csrf", CSRF);
      row.querySelectorAll(".m-caption").forEach(inp => fd.append(inp.dataset.field, inp.value));
      fd.append("layout", row.querySelector(".m-layout").value);
      try { await post(`/admin/media/${id}/update`, fd); } catch (e) { alert(e.message); }
    };
    row.querySelectorAll(".m-caption").forEach(inp => inp.addEventListener("change", save));
    row.querySelector(".m-layout").addEventListener("change", save);
    row.querySelector(".m-del").addEventListener("click", async () => {
      if (!confirm("Remover este item?")) return;
      const fd = new FormData();
      fd.append("csrf", CSRF);
      try { await post(`/admin/media/${id}/delete`, fd); row.remove(); } catch (e) { alert(e.message); }
    });
  });

  /* ---------- reordenação drag & drop ---------- */
  const sortable = (listEl, endpoint) => {
    if (!listEl) return;
    let dragging = null;
    listEl.querySelectorAll("[draggable]").forEach(item => {
      item.addEventListener("dragstart", () => { dragging = item; item.classList.add("dragging"); });
      item.addEventListener("dragend", async () => {
        item.classList.remove("dragging");
        dragging = null;
        const order = [...listEl.querySelectorAll("[data-id]")].map(el => el.dataset.id);
        try {
          await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ csrf: CSRF, order }),
          });
        } catch {}
      });
    });
    listEl.addEventListener("dragover", e => {
      e.preventDefault();
      if (!dragging) return;
      const after = [...listEl.querySelectorAll("[draggable]:not(.dragging)")].find(el => {
        const r = el.getBoundingClientRect();
        return e.clientY < r.top + r.height / 2;
      });
      if (after) listEl.insertBefore(dragging, after); else listEl.appendChild(dragging);
    });
  };
  sortable(document.getElementById("caseList"), "/admin/cases/reorder");
  sortable(document.getElementById("mediaList"), "/admin/media/reorder");

  /* ---------- linhas dinâmicas (perfil/CV) ---------- */
  document.querySelectorAll(".add-row").forEach(btn => {
    btn.addEventListener("click", () => {
      const tpl = document.getElementById(`tpl-${btn.dataset.tpl}`);
      const rows = document.getElementById(`${btn.dataset.tpl}-rows`);
      if (!tpl || !rows) return;
      const frag = tpl.content.cloneNode(true);
      if (btn.dataset.tpl === "award") {
        // A linha nova precisa de um id próprio, único, ANTES de existir no
        // DOM — é o que casa o campo de upload desta linha (award_images_<id>)
        // com o prêmio certo no save, sem depender de posição nenhuma (ver o
        // comentário de app/routers/admin.py em profile_save sobre por que
        // pareamento por posição vazaria foto entre linhas ao remover uma do
        // meio). Prefixo "novo-" evita colidir com um id de 8 hex já
        // persistido no banco (gerado em secrets.token_hex(4)).
        const id = `novo-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
        frag.querySelector('input[name="award_id"]').value = id;
        frag.querySelector('input[name^="award_images"]').name = `award_images_${id}`;
      }
      rows.appendChild(frag);
    });
  });
  document.addEventListener("click", e => {
    if (e.target.classList.contains("del-row")) e.target.closest(".row-card")?.remove();
  });
})();

/* inputs de arquivo com envio automático (upload de logo das marcas) */
document.querySelectorAll("[data-autosubmit]").forEach(input => {
  input.addEventListener("change", () => {
    if (input.files.length) input.closest("form").submit();
  });
});

/* Campos de texto que crescem com o conteúdo.

   Um textarea de altura fixa cria a própria barra de rolagem assim que o texto
   passa de três linhas, e aí a página rola por fora enquanto o campo rola por
   dentro — duas rolagens disputando o mesmo gesto. Aqui o campo simplesmente
   fica do tamanho do que tem escrito, e a página continua sendo a única coisa
   que rola no painel. */
(function () {
  function ajustar(ta) {
    ta.style.height = "auto";
    ta.style.height = (ta.scrollHeight + 2) + "px";
  }
  const campos = document.querySelectorAll(".panel textarea");
  campos.forEach(ta => {
    ta.style.overflowY = "hidden";
    ajustar(ta);
    ta.addEventListener("input", () => ajustar(ta));
  });
  /* fontes chegam depois do primeiro cálculo e mudam a altura da linha */
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => campos.forEach(ajustar));
  }
})();

/* Uso de IA no formulário do case: três opções, uma marcada.

   O <input type="radio"> já guarda a escolha; o que falta é a marca visual
   acompanhar o clique sem recarregar a tela. */
document.querySelectorAll(".cf-ia-op").forEach(grupo => {
  grupo.addEventListener("change", () => {
    grupo.querySelectorAll(".cf-ia-bt").forEach(bt => {
      bt.classList.toggle("on", bt.querySelector("input").checked);
    });
  });
});

/* Interruptor da ficha técnica: a marca e o texto seguem o estado real. */
document.querySelectorAll("[data-cf-ficha]").forEach(bt => {
  const campo = bt.querySelector("input");
  const txt = bt.querySelector("[data-cf-ficha-txt]");
  campo.addEventListener("change", () => {
    bt.classList.toggle("on", campo.checked);
    bt.classList.toggle("ia-sim", campo.checked);
    if (txt) txt.textContent = campo.checked ? "Exibir na página" : "Não exibir";
  });
});

/* Prévia da capa do case, na hora de escolher o arquivo.

   Sem isto a pessoa salvava às cegas: a imagem só aparecia depois do Salvar, e
   a única forma de descobrir que era a errada era ver o card do portfólio
   quebrado. O ajuste é do CSS (`object-fit: cover` no mesmo enquadramento do
   card), então o que se vê aqui é o que o portfólio vai mostrar.

   Progressivo de verdade: sem JavaScript, o campo de arquivo continua sendo um
   campo de arquivo e o Salvar continua funcionando. Nada aqui é requisito. */
document.querySelectorAll("[data-capa]").forEach(bloco => {
  const campo = bloco.querySelector("[data-capa-arquivo]");
  const img = bloco.querySelector("[data-capa-img]");
  const vazio = bloco.querySelector("[data-capa-vazio]");
  const info = bloco.querySelector("[data-capa-info]");
  const rotulo = bloco.querySelector("[data-capa-rotulo]");
  const limpar = bloco.querySelector("[data-capa-limpar]");
  const rotuloVideo = bloco.querySelector("[data-video-rotulo]");
  const campoVideo = bloco.querySelector("[data-video-arquivo]");
  if (!campo || !img) return;

  let urlAnterior = "";

  const tamanho = bytes => {
    const mb = bytes / 1048576;
    return mb >= 1 ? mb.toFixed(1) + " MB" : Math.round(bytes / 1024) + " kB";
  };

  campo.addEventListener("change", () => {
    const arquivo = campo.files && campo.files[0];
    if (!arquivo) return;

    // o objeto anterior é revogado antes de nascer outro: trocar de arquivo
    // cinco vezes seguidas deixaria cinco imagens presas na memória da aba
    if (urlAnterior) URL.revokeObjectURL(urlAnterior);
    urlAnterior = URL.createObjectURL(arquivo);

    img.src = urlAnterior;
    img.hidden = false;
    if (vazio) vazio.hidden = true;
    if (rotulo) rotulo.textContent = "Alterar capa";

    // escolher arquivo novo desmarca a exclusão: as duas coisas juntas são
    // contradição, e o servidor já resolve a favor do arquivo — a tela precisa
    // dizer a mesma coisa que o servidor vai fazer
    if (limpar && limpar.checked) limpar.checked = false;

    if (info) {
      // a dimensão só existe depois que a imagem carrega; o nome e o peso já
      // existem agora, e é melhor mostrar o que se sabe do que esperar
      info.hidden = false;
      info.textContent = `${arquivo.name} ·︎ ${tamanho(arquivo.size)}`;
      img.addEventListener("load", () => {
        const l = img.naturalWidth, a = img.naturalHeight;
        if (!l || !a) return;
        const pequena = l < 1600 || a < 1200;
        info.textContent = `${arquivo.name} ·︎ ${tamanho(arquivo.size)} ·︎ ${l} × ${a}`
          + (pequena ? " — menor que o ideal de 1600 × 1200" : "");
        info.classList.toggle("aviso", pequena);
      }, { once: true });
    }
  });

  if (campoVideo && rotuloVideo) {
    campoVideo.addEventListener("change", () => {
      const arquivo = campoVideo.files && campoVideo.files[0];
      if (arquivo) rotuloVideo.textContent = "Alterar vídeo";
    });
  }
});
