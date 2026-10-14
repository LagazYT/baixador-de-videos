// Roda dentro das páginas. Quando um vídeo está TOCANDO (por alguns segundos),
// avisa o background.js. Não lê nada além do endereço, título e tamanho do vídeo.
(() => {
  if (window.__bdvLoaded) return;
  window.__bdvLoaded = true;

  const WAIT_MS = 4000; // só considera depois de 4 s tocando (evita prévias e cliques sem querer)
  let timer = null;
  let lastSig = "";

  function check(v) {
    try {
      if (!v.isConnected || v.paused || v.ended || v.readyState < 2) return;
      const sig = location.href + "|" + (v.currentSrc || "");
      if (sig === lastSig) return;
      lastSig = sig;
      const r = v.getBoundingClientRect();
      const og = document.querySelector('meta[property="og:image"]');
      chrome.runtime.sendMessage({
        type: "video",
        title: document.title || "",
        frameUrl: location.href,
        isTop: window.top === window,
        duration: v.duration,
        live: !isFinite(v.duration),
        muted: v.muted || v.volume === 0,
        loop: v.loop,
        w: Math.round(r.width),
        h: Math.round(r.height),
        poster: v.poster || (og && og.content) || "",
      }).catch(() => {});
    } catch (e) { /* extensão recarregada: ignora */ }
  }

  document.addEventListener("playing", e => {
    if (!(e.target instanceof HTMLVideoElement)) return;
    clearTimeout(timer);
    const v = e.target;
    timer = setTimeout(() => check(v), WAIT_MS);
  }, true);

  document.addEventListener("pause", () => clearTimeout(timer), true);
})();
