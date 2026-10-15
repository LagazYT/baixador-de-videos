"use strict";
/* Baixador de Vídeos (Android) - interface. Conversa com o app pela ponte window.Native. */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (t) => String(t == null ? "" : t).replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const EXT_URL = "https://chrome.google.com/webstore/detail/cclelndahbckbenkjhflpdbgdldlbecc";
const URL_RE = /https?:\/\/[^\s"'<>]+/i;
const ACTIVE = ["starting", "downloading", "processing", "saving"];
const BAR_COLORS = {
  "classico-dark": "#0f1115", "classico-light": "#f3f4f9",
  "cyberpunk-dark": "#101013", "cyberpunk-light": "#e7e8eb",
};
const DEFAULTS = { theme: "dark", style: "classico", notify: true, clipboard: true, autoUpdate: true,
  ignoredHosts: [], lastClip: "" };

const S = {
  settings: Object.assign({}, DEFAULTS),
  systemDark: true,
  tab: "baixar",
  video: null,          // vídeo analisado na aba Baixar
  job: null,            // download atual
  lastDone: null,       // último arquivo baixado (para Abrir/Compartilhar)
  history: [],
  histLoaded: false,
  histLimit: 30,
  seq: 0,
  analyzeReq: "",
  searchReq: "",
  probeReq: "",
  suggestion: null,
};

/* ---------- ponte nativa (com simulação para testar no navegador) ---------- */
const N = window.Native || makeMock();

function makeMock() {
  const later = (fn, ms) => setTimeout(fn, ms || 400);
  const emit = (t, d, ms) => later(() => App.onEvent(t, d), ms);
  let hist = [], settings = "{}", cookies = false, mockJob = null, timer = null;
  window.__mockLog = [];
  const log = (m, a) => window.__mockLog.push([m, a]);
  return {
    getState: () => JSON.stringify({ settings: JSON.parse(settings), systemDark: true, version: "1.2.0",
      ytdlp: "2026.10.01", setup: { state: "done", text: "" }, cookies, folder: "Download/BaixadorDeVideos" }),
    analyze: (id, url) => { log("analyze", url);
      if (/idade/.test(url)) return emit("analyzeError", { reqId: id, code: "login",
        msg: "ERROR: [youtube] abc: Sign in to confirm your age. Use --cookies-from-browser or --cookies" });
      if (/erro/.test(url)) return emit("analyzeError", { reqId: id, code: "generic", msg: "ERROR: Unsupported URL: " + url });
      emit("analyzed", { reqId: id, url, title: "Vídeo de teste com um título bem comprido para ver a quebra de linha",
        uploader: "Canal Exemplo", duration: "12:34", thumbnail: "", heights: [2160, 1080, 720, 480, 360] }); },
    search: (id, q, src) => { log("search", [q, src]);
      emit("searchResults", { reqId: id, results: [1, 2, 3, 4].map((i) => ({ url: "https://youtu.be/v" + i,
        title: "Resultado " + i + " para " + q, uploader: "Canal " + i, duration: "3:2" + i,
        meta: "Canal " + i + "  •  3:2" + i + "  •  1.2 mi de visualizações", thumb: "" })) }); },
    download: (json) => { const d = JSON.parse(json); log("download", d);
      if (mockJob && ACTIVE.includes(mockJob.status)) return emit("error", { code: "busy", msg: "Já existe um download em andamento." });
      mockJob = { id: "dl1", url: d.url, quality: d.quality, title: d.title, status: "starting", pct: 0, text: "Iniciando...", active: true };
      emit("job", Object.assign({}, mockJob));
      let p = 0;
      timer = setInterval(() => { p += 25;
        if (p <= 100) { Object.assign(mockJob, { status: "downloading", pct: p, text: p + "% de 12.3MiB a 1.2MiB/s faltam 00:0" + (4 - p / 25) });
          App.onEvent("job", Object.assign({}, mockJob)); return; }
        clearInterval(timer);
        if (/falha/.test(d.url)) { Object.assign(mockJob, { status: "error", text: "Falha no download.", active: false });
          App.onEvent("job", Object.assign({}, mockJob)); App.onEvent("error", { code: "generic", msg: "ERROR: Postprocessing: Conversion failed!" }); return; }
        Object.assign(mockJob, { status: "done", text: "Download concluído!", active: false });
        const e = { id: String(Date.now()), url: d.url, title: d.title, uploader: d.uploader, duration: d.duration,
          quality: d.quality, uri: "content://x/" + hist.length, mime: "video/mp4", name: d.title + ".mp4", size: 12345678,
          date: "15/10/2026 10:00", thumb: d.thumb, exists: true, path: "Download/BaixadorDeVideos/" + d.title + ".mp4" };
        hist.unshift(e);
        App.onEvent("job", Object.assign({}, mockJob)); App.onEvent("done", { entry: e, fallback: false });
      }, 150); },
    cancel: () => { log("cancel"); if (timer) clearInterval(timer);
      if (mockJob) { Object.assign(mockJob, { status: "cancelled", text: "Download cancelado.", active: false });
        emit("job", Object.assign({}, mockJob)); emit("cancelled", {}); } },
    saveSettings: (j) => { settings = j; log("saveSettings", JSON.parse(j)); },
    getHistory: () => emit("history", { items: hist.slice() }, 50),
    removeHistory: (id) => { hist = hist.filter((h) => h.id !== id); log("removeHistory", id); },
    clearHistory: () => { hist = []; log("clearHistory"); },
    openFile: (u, m) => log("openFile", u), shareFile: (u, m) => log("shareFile", u),
    openDownloads: () => log("openDownloads"), openUrl: (u) => log("openUrl", u),
    pickCookies: () => { log("pickCookies"); cookies = true; emit("cookies", { ok: true, loaded: true, msg: "cookies.txt carregado (12 cookies)." }); },
    clearCookies: () => { cookies = false; log("clearCookies"); },
    updateYtdlp: () => { log("updateYtdlp"); emit("update", { state: "running", text: "Atualizando o yt-dlp..." }, 10);
      emit("update", { state: "done", text: "O yt-dlp já está na versão mais recente.", version: "2026.10.01" }, 600); },
    readClipboard: () => window.__clip || "",
    setBars: (c, l) => log("setBars", [c, l]),
    toast: (m) => log("toast", m),
    __setHistory: (h) => { hist = h; },
  };
}

/* ---------- utilidades ---------- */
let toastTimer = null;
function toast(msg, ms) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), ms || 2600);
}

function nextId(prefix) { S.seq += 1; return prefix + S.seq; }

function busyBtn(btn, on, label) {
  if (on) {
    if (!btn.dataset.old) btn.dataset.old = btn.innerHTML;
    btn.innerHTML = '<span class="spin"></span> ' + esc(label);
    btn.disabled = true;
  } else {
    if (btn.dataset.old) btn.innerHTML = btn.dataset.old;
    delete btn.dataset.old;
    btn.disabled = false;
  }
}

function fmtBytes(n) {
  if (!n) return "";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return n.toFixed(1).replace(".", ",") + " " + u[i];
}

function qualityLabel(q, short) {
  if (q === "audio") return short ? "MP3" : "Somente áudio (MP3)";
  if (q === "best" || !q) return short ? "Melhor qualidade" : "Melhor qualidade disponível";
  return q + "p";
}

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, "").toLowerCase(); } catch (e) { return ""; }
}

function img(name) {
  return "img/" + document.body.dataset.style + "-" + document.body.dataset.mode + "-" + name + ".png";
}

function placeholderImg(el) {
  el.onerror = null;
  el.src = img("placeholder");
}

function saveSettings() {
  try { N.saveSettings(JSON.stringify(S.settings)); } catch (e) { /* ignora */ }
}

/* ---------- janela de diálogo ---------- */
function modal(title, text, buttons) {
  $("#modal-title").textContent = title;
  $("#modal-text").textContent = text;
  const box = $("#modal-buttons");
  box.innerHTML = "";
  (buttons || [{ label: "OK", pri: true }]).forEach((b) => {
    const el = document.createElement("button");
    el.className = "btn" + (b.pri ? " pri" : "") + (b.danger ? " danger" : "") + (b.ghost ? " ghost" : "");
    el.textContent = b.label;
    el.addEventListener("click", () => { if (!b.keep) closeModal(); if (b.fn) b.fn(); });
    box.appendChild(el);
  });
  if (!buttons || !buttons.some((b) => b.ghost)) {
    const close = document.createElement("button");
    close.className = "btn ghost";
    close.textContent = "Fechar";
    close.addEventListener("click", closeModal);
    box.appendChild(close);
  }
  $("#modal").classList.remove("hidden");
}
function closeModal() { $("#modal").classList.add("hidden"); }
function confirmBox(title, text, okLabel, fn) {
  modal(title, text, [{ label: okLabel, pri: true, fn }, { label: "Cancelar", ghost: true }]);
}

function loginHelp(detail) {
  modal("Este vídeo exige login",
    "O YouTube só libera vídeos com restrição de idade (ou exclusivos) para quem está logado.\n\n" +
    "Como resolver:\n" +
    "1. No computador, instale a extensão \"Get cookies.txt LOCALLY\" no navegador.\n" +
    "2. Abra o youtube.com logado numa conta que possa ver o vídeo e exporte o cookies.txt pela extensão.\n" +
    "3. Envie o arquivo para o celular (WhatsApp, e-mail, Drive...).\n" +
    "4. Toque em \"Escolher cookies.txt\" e selecione o arquivo.\n\n" +
    (detail ? "Detalhe técnico: " + detail.slice(0, 200) : ""),
    [
      { label: "Escolher cookies.txt", pri: true, fn: () => N.pickCookies() },
      { label: "Ver a extensão", fn: () => N.openUrl(EXT_URL) },
    ]);
}

function errorHelp(msg, code) {
  if (code === "login") { loginHelp(msg); return; }
  if (code === "format") {
    modal("Formato indisponível", msg + "\n\nO YouTube muda com frequência. Atualize o motor de download e tente de novo.",
      [{ label: "Atualizar agora", pri: true, fn: () => { showTab("config"); N.updateYtdlp(); } }]);
    return;
  }
  modal("Erro", msg);
}

/* ---------- aparência ---------- */
function currentMode() {
  const t = S.settings.theme;
  if (t === "system") return S.systemDark ? "dark" : "light";
  return t === "light" ? "light" : "dark";
}

function applyLook() {
  const style = S.settings.style === "cyberpunk" ? "cyberpunk" : "classico";
  const mode = currentMode();
  document.body.dataset.style = style;
  document.body.dataset.mode = mode;
  $$("img[data-img]").forEach((el) => {
    const name = el.dataset.img;
    if (name === "placeholder" && el.dataset.real === "1") return;
    el.src = img(name);
  });
  $$("img.empty-art").forEach((el) => { el.src = img("empty"); });
  $$("#seg-theme button").forEach((b) => b.classList.toggle("on", b.dataset.v === S.settings.theme));
  $$("#seg-style button").forEach((b) => b.classList.toggle("on", b.dataset.v === style));
  try { N.setBars(BAR_COLORS[style + "-" + mode], mode === "light"); } catch (e) { /* ignora */ }
}

/* ---------- abas ---------- */
function showTab(name) {
  S.tab = name;
  $$(".tab").forEach((s) => s.classList.toggle("active", s.id === "tab-" + name));
  $$(".nav button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  window.scrollTo(0, 0);
  if (name === "historico") N.getHistory();
}
$$(".nav button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

/* ---------- ABA BAIXAR ---------- */
function resetVideo(title) {
  S.video = null;
  const th = $("#thumb");
  th.dataset.real = "";
  th.src = img("placeholder");
  $("#vtitle").textContent = title || "Nenhum vídeo carregado";
  $("#vmeta").textContent = "";
  $("#quality").innerHTML = "<option>—</option>";
  $("#quality").disabled = true;
  updateButtons();
}

function analyze(url) {
  url = (url || $("#url").value).trim();
  if (!url) { toast("Cole um link primeiro."); return; }
  const m = url.match(URL_RE);
  if (!m) { toast("Isso não parece um link. Cole um endereço começando com https://"); return; }
  url = m[0];
  $("#url").value = url;
  $("#errbox").classList.add("hidden");
  S.analyzeReq = nextId("a");
  resetVideo("Carregando...");
  busyBtn($("#btn-analyze"), true, "Analisando");
  setStatus("Analisando o link...", "");
  setIndeterminate(true);
  N.analyze(S.analyzeReq, url);
}

function onAnalyzed(d) {
  if (d.reqId === S.probeReq) { showSuggestion(d); return; }
  if (d.reqId !== S.analyzeReq) return;
  busyBtn($("#btn-analyze"), false);
  setIndeterminate(false);
  S.video = d;
  const th = $("#thumb");
  th.onerror = () => { th.dataset.real = ""; placeholderImg(th); };
  if (d.thumbnail) { th.dataset.real = "1"; th.src = d.thumbnail; } else { th.dataset.real = ""; th.src = img("placeholder"); }
  $("#vtitle").textContent = d.title || "Sem título";
  $("#vmeta").textContent = [d.uploader, d.duration].filter(Boolean).join("  •  ");
  const q = $("#quality");
  q.innerHTML = "";
  [["best", qualityLabel("best")]].concat((d.heights || []).map((h) => [String(h), h + "p"]))
    .concat([["audio", qualityLabel("audio")]])
    .forEach(([v, l]) => { const o = document.createElement("option"); o.value = v; o.textContent = l; q.appendChild(o); });
  q.disabled = false;
  if (d.pendingQuality) q.value = d.pendingQuality;
  updateButtons();
  setStatus("Pronto para baixar. Escolha a qualidade.", "");
}

function onAnalyzeError(d) {
  if (d.reqId === S.probeReq) return; // sugestão silenciosa: ignora links que não são vídeo
  if (d.reqId !== S.analyzeReq) return;
  busyBtn($("#btn-analyze"), false);
  setIndeterminate(false);
  resetVideo();
  setStatus("Não foi possível analisar o link.", "err");
  const box = $("#errbox");
  box.textContent = d.msg;
  box.classList.remove("hidden");
  if (d.code === "login" || d.code === "format") {
    const b = document.createElement("button");
    b.className = "btn pri";
    b.textContent = d.code === "login" ? "Como resolver" : "Atualizar o motor";
    b.addEventListener("click", () => errorHelp(d.msg, d.code));
    box.appendChild(document.createElement("br"));
    box.appendChild(b);
    if (d.code === "login") loginHelp(d.msg);
  }
}

function startDownload(info, quality) {
  if (S.job && ACTIVE.includes(S.job.status)) {
    modal("Aguarde", "Já existe um download em andamento. Espere terminar para iniciar outro.");
    return;
  }
  $("#done-actions").classList.add("hidden");
  N.download(JSON.stringify({
    url: info.url, quality: quality || "best", title: info.title || "", uploader: info.uploader || "",
    duration: info.duration || "", thumb: info.thumbnail || info.thumb || "",
  }));
}

function setStatus(text, cls) {
  const s = $("#status");
  s.textContent = text;
  s.className = "muted small" + (cls ? " " + cls : "");
}

function setIndeterminate(on) {
  $("#progress").parentElement.classList.toggle("indet", !!on);
}

function updateButtons() {
  const active = S.job && ACTIVE.includes(S.job.status);
  $("#btn-download").disabled = !S.video || !!active;
  $("#btn-cancel").disabled = !active;
}

function onJob(j) {
  S.job = j;
  const active = ACTIVE.includes(j.status);
  const pct = Math.max(0, Math.min(100, j.pct || 0));
  $("#progress").style.width = (j.status === "done" ? 100 : pct) + "%";
  setIndeterminate(j.status === "starting" || j.status === "saving" || j.status === "processing");
  $("#topbar-fill").style.width = active ? Math.max(3, pct) + "%" : "0";
  const prefix = active && j.title ? j.title.slice(0, 60) + "\n" : "";
  setStatus(prefix + j.text, j.status === "done" ? "ok" : (j.status === "error" ? "err" : ""));
  updateButtons();
}

function onDone(d) {
  const e = d.entry;
  S.lastDone = e;
  setStatus("✔ " + (d.fallback ? "Concluído (formato ajustado para compatibilidade)" : "Download concluído!") +
    "\nSalvo em Download/BaixadorDeVideos/" + (e.name || ""), "ok");
  $("#done-actions").classList.remove("hidden");
  toast("Download concluído!");
  S.history = [e].concat(S.history.filter((h) => h.id !== e.id));
  if (S.tab === "historico") renderHistory();
}

$("#btn-analyze").addEventListener("click", () => analyze());
$("#url").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); analyze(); } });
$("#btn-paste").addEventListener("click", () => {
  const t = (N.readClipboard() || "").trim();
  if (!t) { toast("A área de transferência está vazia."); return; }
  const m = t.match(URL_RE);
  $("#url").value = m ? m[0] : t;
  if (m) { S.settings.lastClip = m[0]; saveSettings(); analyze(m[0]); }
});
$("#btn-download").addEventListener("click", () => {
  if (!S.video) return;
  startDownload(S.video, $("#quality").value);
});
$("#btn-cancel").addEventListener("click", () => N.cancel());
$("#btn-folder").addEventListener("click", () => N.openDownloads());
$("#btn-open-last").addEventListener("click", () => { if (S.lastDone) N.openFile(S.lastDone.uri, S.lastDone.mime || ""); });
$("#btn-share-last").addEventListener("click", () => { if (S.lastDone) N.shareFile(S.lastDone.uri, S.lastDone.mime || ""); });

/* ---------- sugestão (link copiado) ---------- */
function checkClipboard() {
  if (!S.settings.clipboard) return;
  let t = "";
  try { t = (N.readClipboard() || "").trim(); } catch (e) { return; }
  const m = t.match(URL_RE);
  if (!m) return;
  const url = m[0];
  if (url === S.settings.lastClip) return;
  if (url === $("#url").value.trim()) return;
  if (S.job && ACTIVE.includes(S.job.status) && S.job.url === url) return;
  const host = hostOf(url);
  if ((S.settings.ignoredHosts || []).some((h) => host === h || host.endsWith("." + h))) return;
  S.settings.lastClip = url;
  saveSettings();
  S.probeReq = nextId("p");
  N.analyze(S.probeReq, url);
}

function showSuggestion(d) {
  S.suggestion = d;
  const th = $("#sg-thumb");
  th.onerror = () => placeholderImg(th);
  th.src = d.thumbnail || img("placeholder");
  $("#sg-label").textContent = "🎬 Link de vídeo copiado";
  $("#sg-title").textContent = d.title || "Vídeo";
  $("#sg-meta").textContent = [d.uploader, d.duration].filter(Boolean).join("  •  ");
  const done = S.history.find((h) => h.url === d.url);
  $("#sg-note").textContent = done ? "Você já baixou este vídeo em " + done.date : "";
  $("#sg-dl").textContent = done ? "↻ Baixar de novo" : "⬇ Baixar";
  $("#suggest").classList.remove("hidden");
}
function hideSuggestion() { $("#suggest").classList.add("hidden"); S.suggestion = null; }

$("#sg-close").addEventListener("click", hideSuggestion);
$("#sg-dl").addEventListener("click", () => {
  const d = S.suggestion; hideSuggestion();
  if (d) { startDownload(d, "best"); showTab("baixar"); }
});
$("#sg-pick").addEventListener("click", () => {
  const d = S.suggestion; hideSuggestion();
  if (d) { showTab("baixar"); $("#url").value = d.url; onAnalyzedFromSuggestion(d); }
});
$("#sg-ignore").addEventListener("click", () => {
  const d = S.suggestion; hideSuggestion();
  if (!d) return;
  const host = hostOf(d.url);
  if (host && !S.settings.ignoredHosts.includes(host)) { S.settings.ignoredHosts.push(host); saveSettings(); }
  toast("Não vou mais sugerir downloads de " + host + ".");
});
function onAnalyzedFromSuggestion(d) {
  S.analyzeReq = nextId("a");
  onAnalyzed(Object.assign({}, d, { reqId: S.analyzeReq }));
}

/* ---------- ABA PESQUISAR ---------- */
function emptyArt(text) {
  return '<div class="card empty"><img class="empty-art" src="' + img("empty") + '" alt=""><p>' + esc(text) + "</p></div>";
}

function search() {
  const q = $("#q").value.trim();
  if (!q) { toast("Digite algo para pesquisar."); return; }
  S.searchReq = nextId("s");
  busyBtn($("#btn-search"), true, "Buscando");
  $("#results").innerHTML = '<p class="muted small" style="text-align:center;padding:24px 0">Buscando...</p>';
  N.search(S.searchReq, q, $("#src").value);
}

function onSearchResults(d) {
  if (d.reqId !== S.searchReq) return;
  busyBtn($("#btn-search"), false);
  const box = $("#results");
  if (!d.results.length) { box.innerHTML = emptyArt("Nenhum resultado encontrado."); return; }
  box.innerHTML = "";
  d.results.forEach((r) => {
    const el = document.createElement("div");
    el.className = "res";
    el.innerHTML = '<img class="sthumb" alt="">' +
      '<div class="info"><div class="t">' + esc(r.title) + '</div><div class="m">' + esc(r.meta) + "</div>" +
      '<div class="b"><button class="btn pri sm" data-a="quick">⬇ Baixar</button>' +
      '<button class="btn sm" data-a="pick">Qualidade...</button></div></div>';
    const im = el.querySelector("img");
    im.onerror = () => placeholderImg(im);
    im.src = r.thumb || img("placeholder");
    el.querySelector('[data-a="quick"]').addEventListener("click", () => {
      startDownload({ url: r.url, title: r.title, uploader: r.uploader, duration: r.duration, thumb: r.thumb }, "best");
      showTab("baixar");
    });
    el.querySelector('[data-a="pick"]').addEventListener("click", () => { showTab("baixar"); analyze(r.url); });
    box.appendChild(el);
  });
}

function onSearchError(d) {
  if (d.reqId !== S.searchReq) return;
  busyBtn($("#btn-search"), false);
  $("#results").innerHTML = '<div class="banner err">' + esc(d.msg) + "</div>";
}

$("#btn-search").addEventListener("click", search);
$("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); search(); } });
$("#web-search").addEventListener("click", (e) => {
  e.preventDefault();
  const q = $("#q").value.trim();
  N.openUrl(q ? "https://www.google.com/search?tbm=vid&q=" + encodeURIComponent(q) : "https://www.google.com/videohp");
});

/* ---------- ABA HISTÓRICO ---------- */
function renderHistory() {
  const box = $("#hist-list");
  const f = $("#hist-filter").value.trim().toLowerCase();
  if (!S.histLoaded) {
    $("#hist-count").textContent = "Histórico";
    box.innerHTML = '<p class="muted small" style="text-align:center;padding:20px">Carregando...</p>';
    return;
  }
  $("#hist-count").textContent = "Histórico (" + S.history.length + ")";
  const items = S.history.filter((h) => !f || ((h.title || "") + " " + (h.uploader || "")).toLowerCase().includes(f));
  if (!items.length) {
    box.innerHTML = f ? '<p class="muted small" style="text-align:center;padding:20px">Nenhum resultado para esse filtro.</p>'
      : emptyArt("Nenhum download no histórico ainda. Os vídeos que você baixar aparecerão aqui.");
    return;
  }
  box.innerHTML = "";
  items.slice(0, S.histLimit).forEach((h) => {
    const el = document.createElement("div");
    el.className = "res";
    const who = [h.uploader, h.duration].filter(Boolean).join("  •  ");
    const meta = [h.date, qualityLabel(h.quality, true), fmtBytes(h.size)].filter(Boolean).join("  •  ");
    el.innerHTML = '<img class="sthumb" alt="">' +
      '<div class="info"><div class="t">' + esc(h.title) + "</div>" +
      (who ? '<div class="m">' + esc(who) + "</div>" : "") +
      '<div class="m">' + esc(meta) + "</div>" +
      '<div class="m ' + (h.exists ? "exists" : "missing") + '">' +
      (h.exists ? "✔ Arquivo no celular" : "Arquivo não encontrado (movido ou apagado)") + "</div></div>" +
      '<div class="b full"><button class="btn pri sm grow" data-a="again">↻ Baixar de novo</button>' +
      '<button class="btn sm" data-a="pick">Qualidade</button>' +
      '<button class="btn sm" data-a="open">Abrir</button>' +
      '<button class="btn sm link-danger" data-a="del">Remover</button></div>';
    const im = el.querySelector("img");
    im.onerror = () => placeholderImg(im);
    im.src = h.thumb || img("placeholder");
    el.querySelector('[data-a="again"]').addEventListener("click", () => {
      startDownload({ url: h.url, title: h.title, uploader: h.uploader, duration: h.duration, thumb: h.thumb }, h.quality);
      showTab("baixar");
    });
    el.querySelector('[data-a="pick"]').addEventListener("click", () => { showTab("baixar"); analyze(h.url); });
    el.querySelector('[data-a="open"]').addEventListener("click", () => {
      if (!h.exists) {
        modal("Arquivo não encontrado", "Esse arquivo foi movido ou apagado. Use \"Baixar de novo\" para baixá-lo outra vez.");
        return;
      }
      N.openFile(h.uri, h.mime || "");
    });
    el.querySelector('[data-a="del"]').addEventListener("click", () => {
      N.removeHistory(h.id);
      S.history = S.history.filter((x) => x.id !== h.id);
      renderHistory();
    });
    box.appendChild(el);
  });
  if (items.length > S.histLimit) {
    const more = document.createElement("button");
    more.className = "btn more";
    more.textContent = "Mostrar mais (" + (items.length - S.histLimit) + ")";
    more.addEventListener("click", () => { S.histLimit += 30; renderHistory(); });
    box.appendChild(more);
  }
}

let filterTimer = null;
$("#hist-filter").addEventListener("input", () => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => { S.histLimit = 30; renderHistory(); }, 200);
});
$("#btn-hist-clear").addEventListener("click", () => {
  if (!S.history.length) { toast("O histórico já está vazio."); return; }
  confirmBox("Limpar histórico", "Apagar todo o histórico de downloads?\n\nOs arquivos baixados continuam no celular.",
    "Limpar", () => { N.clearHistory(); S.history = []; renderHistory(); });
});

/* ---------- ABA CONFIGURAÇÕES ---------- */
$$("#seg-theme button").forEach((b) => b.addEventListener("click", () => {
  S.settings.theme = b.dataset.v; saveSettings(); applyLook();
}));
$$("#seg-style button").forEach((b) => b.addEventListener("click", () => {
  S.settings.style = b.dataset.v; saveSettings(); applyLook();
  if (S.tab === "historico") renderHistory();
}));
[["#opt-notify", "notify"], ["#opt-clipboard", "clipboard"], ["#opt-autoupdate", "autoUpdate"]].forEach(([sel, key]) => {
  $(sel).addEventListener("change", (e) => { S.settings[key] = e.target.checked; saveSettings(); });
});
$("#btn-ignored").addEventListener("click", () => {
  const list = S.settings.ignoredHosts || [];
  if (!list.length) { modal("Sites ignorados", "Nenhum site está sendo ignorado."); return; }
  confirmBox("Limpar sites ignorados", "Voltar a sugerir downloads nestes sites?\n\n" + list.slice(0, 15).join("\n"),
    "Limpar", () => { S.settings.ignoredHosts = []; saveSettings(); toast("Lista de sites ignorados limpa."); });
});
$("#btn-cookie").addEventListener("click", () => N.pickCookies());
$("#btn-cookie-clear").addEventListener("click", () => {
  N.clearCookies(); setCookies(false); toast("cookies.txt removido.");
});
$("#btn-update").addEventListener("click", () => N.updateYtdlp());

function setCookies(loaded) {
  const c = $("#st-cookies");
  c.textContent = loaded ? "carregado" : "nenhum";
  c.className = loaded ? "ok" : "no";
}

function fillSettings(state) {
  $("#opt-notify").checked = !!S.settings.notify;
  $("#opt-clipboard").checked = !!S.settings.clipboard;
  $("#opt-autoupdate").checked = !!S.settings.autoUpdate;
  if (state) {
    $("#st-ytdlp").textContent = state.ytdlp || "preparando...";
    $("#st-folder").textContent = state.folder || "Download/BaixadorDeVideos";
    $("#about").textContent = "Produzido por Lagaz  •  v" + (state.version || "") +
      (state.ytdlp ? "  •  yt-dlp " + state.ytdlp : "");
    setCookies(!!state.cookies);
  }
}

function onSetup(d) {
  const box = $("#setup");
  if (d.state === "done") {
    box.classList.add("hidden");
    try { const st = JSON.parse(N.getState()); fillSettings(st); } catch (e) { /* ignora */ }
    return;
  }
  $("#setup-text").textContent = d.text;
  box.classList.remove("hidden");
  box.querySelector(".spin").classList.toggle("hidden", d.state !== "running");
}

/* ---------- eventos vindos do app ---------- */
const App = {
  onEvent(type, d) {
    switch (type) {
      case "setup": onSetup(d); break;
      case "analyzed": onAnalyzed(d); break;
      case "analyzeError": onAnalyzeError(d); break;
      case "searchResults": onSearchResults(d); break;
      case "searchError": onSearchError(d); break;
      case "job": onJob(d); break;
      case "done": onDone(d); break;
      case "cancelled": toast("Download cancelado."); break;
      case "error":
        updateButtons();
        if (d.code === "busy") modal("Aguarde", d.msg);
        else errorHelp("Falha no download.\n" + d.msg, d.code);
        break;
      case "history": S.history = d.items || []; S.histLoaded = true; renderHistory(); break;
      case "cookies":
        setCookies(!!d.loaded);
        if (d.ok) toast(d.msg, 3500); else modal("cookies.txt", d.msg);
        break;
      case "update":
        $("#update-msg").textContent = d.text;
        if (d.state === "running") busyBtn($("#btn-update"), true, "Atualizando");
        else {
          busyBtn($("#btn-update"), false);
          if (d.version) { $("#st-ytdlp").textContent = d.version; }
        }
        break;
      case "shared":
        hideSuggestion();
        showTab("baixar");
        analyze(d.url);
        break;
      case "systemDark": S.systemDark = !!d.dark; applyLook(); break;
      case "focus": checkClipboard(); break;
      default: break;
    }
  },
  onBack() {
    if (!$("#modal").classList.contains("hidden")) { closeModal(); return true; }
    if (!$("#suggest").classList.contains("hidden")) { hideSuggestion(); return true; }
    if (S.tab !== "baixar") { showTab("baixar"); return true; }
    return false;
  },
};
window.App = App;

/* ---------- início ---------- */
(function init() {
  let st = {};
  try { st = JSON.parse(N.getState()); } catch (e) { st = {}; }
  S.settings = Object.assign({}, DEFAULTS, st.settings || {});
  if (!Array.isArray(S.settings.ignoredHosts)) S.settings.ignoredHosts = [];
  S.systemDark = st.systemDark !== false;
  applyLook();
  fillSettings(st);
  resetVideo();
  if (st.setup) onSetup(st.setup);
  if (st.job) {
    onJob(st.job);
    if (st.job.status === "done") setStatus("✔ " + st.job.text, "ok");
  }
  N.getHistory();
  if (st.shared) { showTab("baixar"); analyze(st.shared); } else { setTimeout(checkClipboard, 600); }
})();
