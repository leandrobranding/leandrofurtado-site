/* ============================================================
   Rotação da segunda metade do título da vitrine.

   A frase de contorno troca sozinha, em ordem aleatória, com uma passagem
   curta de desfoque e deslocamento. É o único movimento contínuo da
   página, então ele precisa ser lento o bastante para não competir com a
   leitura e curto o bastante para não parecer travamento.

   Três cuidados:
   · só começa DEPOIS da animação de entrada do título (GSAP/SplitText),
     senão as duas brigam pelo mesmo elemento;
   · nunca repete a frase que já está na tela;
   · quem pede menos movimento não vê troca nenhuma, e fica com a frase
     original. O leitor de tela também não é incomodado: sem `aria-live`,
     a mudança de texto não é anunciada.
   ============================================================ */
(function () {
  "use strict";

  var alvo = document.querySelector(".lab-vt-title .ol");
  if (!alvo) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var FRASES = [
    "Vou te deixar clicar.",
    "Vou te deixar navegar.",
    "Vou te deixar acessar.",
    "Vou te deixar testar.",
    "Vou te deixar entrar.",
    "Vou te deixar curtir.",
    "Vou te deixar explorar.",
    "Vou te deixar usar.",
    "Vou te deixar decidir.",
    "Vou te deixar sonhar.",
  ];

  var ESPERA_INICIAL = 2600;   // deixa a entrada do título terminar
  var INTERVALO = 3600;        // tempo que cada frase fica na tela
  var PASSAGEM = 420;          // duração da saída e da entrada

  var atual = alvo.textContent.trim();

  function sorteia() {
    var candidatas = FRASES.filter(function (f) { return f !== atual; });
    return candidatas[Math.floor(Math.random() * candidatas.length)];
  }

  function troca() {
    var proxima = sorteia();
    if (!proxima) return;
    alvo.classList.add("trocando");
    window.setTimeout(function () {
      alvo.textContent = proxima;
      atual = proxima;
      alvo.classList.remove("trocando");
    }, PASSAGEM);
  }

  window.setTimeout(function () {
    troca();
    window.setInterval(troca, INTERVALO);
  }, ESPERA_INICIAL);
})();

/* Cortina antes/depois: o input já guarda o valor e já responde a teclado
   e a arrasto. Isto só copia o valor dele para a variável de CSS.

   Sem JavaScript a cortina fica parada em 50%, que é um estado honesto:
   metade de cada site aparece, e a comparação continua legível. */
document.querySelectorAll(".lab-vt-cortina").forEach(function (caixa) {
  var controle = caixa.querySelector(".lab-vt-cortina-controle");
  if (!controle) return;
  function aplicar() { caixa.style.setProperty("--corte", controle.value + "%"); }
  controle.addEventListener("input", aplicar);
  // O cartão inteiro é um link: arrastar a cortina não pode navegar.
  controle.addEventListener("click", function (e) { e.preventDefault(); });
  aplicar();
});
