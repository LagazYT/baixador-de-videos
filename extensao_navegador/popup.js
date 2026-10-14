const $ = s => document.querySelector(s);

async function refresh() {
  const j = await chrome.runtime.sendMessage({ type: "ping" });
  const ok = !!j;
  $("#dot").className = "dot " + (ok ? "ok" : "off");
  $("#status").textContent = ok ? "Conectado ao Baixador de Vídeos" : "O Baixador de Vídeos não está aberto";
  $("#send").disabled = !ok;
  $("#hint").textContent = ok && j.enabled === false
    ? "As sugestões estão desativadas no programa (aba ⚙)."
    : (ok ? "" : "Abra o programa no computador para receber as sugestões.");
}

(async () => {
  const { enabled = true } = await chrome.storage.local.get("enabled");
  $("#auto").checked = enabled;
  refresh();
})();

$("#auto").addEventListener("change", e => chrome.storage.local.set({ enabled: e.target.checked }));

$("#send").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !/^https?:/.test(tab.url || "")) { $("#hint").textContent = "Abra uma página de vídeo primeiro."; return; }
  await chrome.runtime.sendMessage({ type: "manual", url: tab.url, title: tab.title || "" });
  window.close();
});
