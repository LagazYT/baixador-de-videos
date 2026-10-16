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
  "retro-dark": "#1f1c19", "retro-light": "#f2ead8",
  "steampunk-dark": "#1c140e", "steampunk-light": "#efe2c4",
  "arcade-dark": "#0b0b1a", "arcade-light": "#f4f1e6",
  "rpg-dark": "#10151e", "rpg-light": "#f3e9d2",
};
const STYLES = ["classico", "cyberpunk", "retro", "steampunk", "arcade", "rpg"];
const STYLE_NAMES = { classico: "Clássico", cyberpunk: "Cyberpunk", retro: "Retrô", steampunk: "Steampunk",
  arcade: "Arcade 8-bit", rpg: "Fantasia / RPG" };
const DEFAULTS = { theme: "dark", style: "classico", notify: true, clipboard: true, autoUpdate: true,
  ignoredHosts: [], lastClip: "", autoCheckApp: true, lastAppCheck: 0, knownAppVersion: "", compat: false };
const ISSUES_URL = "https://github.com/LagazYT/baixador-de-videos/issues/new";
const APP_CHECK_EVERY = 12 * 3600 * 1000;

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
  playing: null,        // item do histórico tocando no player
  version: "",
  appUpdate: null,      // informações da versão nova do app
  pendingAuto: null,    // "Baixar de novo": opções a aplicar depois da análise
  jobInfo: null,        // vídeo do download atual (título e miniatura para o cartão)
  chooseAgain: false,   // "Baixar com outras opções" depois de concluir
  searchSrc: "youtube",
  lastError: "",        // último erro (vai no relatório de erro)
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
      const nosubs = /semleg/.test(url);
      emit("analyzed", { reqId: id, url, id: "abc123", title: "Vídeo de teste com um título bem comprido para ver a quebra de linha",
        uploader: "Canal Exemplo", duration: "12:34", durationSec: 754, thumbnail: "", thumbs: ["https://i.ytimg.com/vi/abc/maxresdefault.webp", "https://i.ytimg.com/vi/abc/hqdefault.jpg"],
        heights: [2160, 1080, 720, 480, 360], h264: [1080, 720, 480, 360], codecKnown: true,
        subs: nosubs ? [] : [{ label: "Português (Brasil)", code: "pt-BR", auto: false }, { label: "Inglês (automática)", code: "en-orig", auto: true }] }); },
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
        const note = window.__mockNote || "";
        Object.assign(mockJob, { status: "done", text: note ? "Concluído, " + note + "." : "Download concluído!", active: false });
        const e = { id: String(Date.now()), url: d.url, title: d.title, uploader: d.uploader, duration: d.duration,
          quality: d.quality, uri: "content://x/" + hist.length, mime: "video/mp4", name: d.title + ".mp4", size: 12345678,
          date: "15/10/2026 10:00", thumb: d.thumb, exists: true, path: "Download/BaixadorDeVideos/" + d.title + ".mp4",
          compat: d.compat !== "off" && d.compat !== undefined && !note, subs: d.section ? "" : (d.subLabel || ""), section: d.section || undefined };
        hist.unshift(e);
        App.onEvent("job", Object.assign({}, mockJob)); App.onEvent("done", { entry: e, note, fallback: !!note });
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
    mediaUrl: (u, m) => { log("mediaUrl", u); return window.__testVideo || ""; },
    keepScreenOn: (on) => log("keepScreenOn", on),
    checkAppUpdate: (manual) => { log("checkAppUpdate", manual);
      const v = window.__remoteVersion || "1.2.0";
      if (window.__offline) return emit("appUpdate", { state: "error", manual, msg: "Sem conexão." });
      emit("appUpdate", { state: v > "1.2.0" ? "available" : "latest", manual, info: { version: v, current: "1.2.0",
        page: "https://github.com/x/releases/tag/android-v" + v, notes: "📱 Novidades\n- Atualizações automáticas", url: "u", size: 1 } }); },
    downloadAppUpdate: () => { log("downloadAppUpdate"); [10, 55, 100].forEach((p, i) => emit("appUpdateProgress", { pct: p }, 100 + i * 100));
      emit("appUpdateReady", { version: window.__remoteVersion, sameKey: !window.__otherKey }, 500); },
    installAppUpdate: () => log("installAppUpdate"),
    setBars: (c, l) => log("setBars", [c, l]),
    toast: (m) => log("toast", m),
    saveThumb: (u, t, id) => { log("saveThumb", [JSON.parse(u), t, id]);
      if (window.__thumbFail) return emit("thumbError", { msg: "Não foi possível salvar a thumbnail.\nHTTP 404" });
      emit("thumbSaved", { name: t + " [" + id + "] - thumbnail.jpg", w: 1280, h: 720, uri: "content://t" }); },
    copyReport: (e) => { log("copyReport", e); return "Baixador de Vídeos 1.2.0 (Android)\nÚltimo erro:\n" + e + "\n[15/10/2026] https://youtu.be/erro\n"; },
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

/* rótulo do histórico: qualidade + H.264 + trecho + legenda */
function entryLabel(h) {
  const parts = [qualityLabel(h.quality, true)];
  if (h.compat) parts.push("H.264");
  if (h.section) parts.push("✂ " + sectionText(h.section));
  if (h.subs) parts.push("Legenda: " + h.subs);
  return parts.join("  •  ");
}

/* "2:15", "1:02:05", "135", "2:15.5" ou "2 15" -> segundos (null se inválido) */
function parseClock(text) {
  let t = String(text || "").trim().replace(",", ".").replace(/\s+/g, ":");
  if (!t) return null;
  const parts = t.split(":");
  if (parts.length > 3 || parts.some((p) => !/^\d+(\.\d+)?$/.test(p))) return null;
  const nums = parts.map(Number);
  if (nums.slice(1).some((n) => n >= 60)) return null;
  return nums.reduce((acc, n) => acc * 60 + n, 0);
}

function clockText(sec) {
  sec = Math.max(0, Number(sec) || 0);
  const whole = Math.floor(sec), frac = sec - whole;
  const h = Math.floor(whole / 3600), m = Math.floor((whole % 3600) / 60), s = whole % 60;
  let t = h ? h + ":" + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0") : m + ":" + String(s).padStart(2, "0");
  if (frac >= 0.05) t += "." + (Math.round(frac * 10) % 10);
  return t;
}

function sectionText(sec) { return clockText(sec.start) + " a " + clockText(sec.end); }

/* Como entregar em H.264: off | h264 (já existe) | recode (converte) | pref (site não informa codecs) */
function compatPlan(compat, quality, v) {
  if (!compat || quality === "audio") return { mode: "off", h: 0 };
  if (!v || !v.codecKnown) return { mode: "pref", h: 0 };
  const h264 = v.h264 || [], heights = v.heights || [];
  if (quality === "best" || !quality) {
    // "Melhor qualidade" = melhor versão que já existe em H.264 (sem conversão demorada)
    if (h264.length) return { mode: "h264", h: Math.max.apply(null, h264) };
    return { mode: "recode", h: heights.length ? Math.max.apply(null, heights) : 0 };
  }
  const h = parseInt(quality, 10);
  return h264.includes(h) ? { mode: "h264", h } : { mode: "recode", h };
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
function modal(title, text, buttons, opts) {
  $("#modal").classList.toggle("sheet", !!(opts && opts.sheet));
  $("#modal-title").textContent = title;
  $("#modal-text").textContent = text || "";
  $("#modal-text").classList.toggle("hidden", !text);
  const box = $("#modal-buttons");
  box.innerHTML = "";
  (buttons || [{ label: "OK", pri: true }]).forEach((b) => {
    const el = document.createElement("button");
    el.className = "btn" + (b.pri ? " pri" : "") + (b.danger ? " danger" : "") + (b.ghost ? " ghost" : "") + (b.cls ? " " + b.cls : "");
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
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });  // toque fora fecha
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
      [{ label: "Atualizar agora", pri: true, fn: () => { showTab("config"); N.updateYtdlp(); } },
       { label: "Copiar relatório de erro", keep: true, fn: copyReport }]);
    return;
  }
  modal("Erro", msg, [{ label: "Copiar relatório de erro", keep: true, fn: copyReport }]);
}

function copyReport() {
  let text = "";
  try { text = N.copyReport(S.lastError || "") || ""; } catch (e) { text = ""; }
  // o relatório tem links: não sugerir download deles ao voltar para o app
  const m = text.match(URL_RE);
  if (m) { S.settings.lastClip = m[0]; saveSettings(); }
  toast("Relatório copiado. Cole na mensagem para quem vai te ajudar.", 3500);
}

/* ---------- aparência ---------- */
function currentMode() {
  const t = S.settings.theme;
  if (t === "system") return S.systemDark ? "dark" : "light";
  return t === "light" ? "light" : "dark";
}

function applyLook() {
  const style = STYLES.includes(S.settings.style) ? S.settings.style : "classico";
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
  $("#style-summary").textContent = "Atual: " + (STYLE_NAMES[style] || style);
  try { N.setBars(BAR_COLORS[style + "-" + mode], mode === "light"); } catch (e) { /* ignora */ }
}

/* ---------- abas ---------- */
function showTab(name) {
  S.tab = name;
  $$(".tab").forEach((s) => s.classList.toggle("active", s.id === "tab-" + name));
  $$(".nav button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  window.scrollTo(0, 0);
  if (name === "historico") N.getHistory();
  if (name === "player") renderPlayerList();
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
  $("#subs").innerHTML = '<option value="">Sem legendas</option>';
  $("#opt-trim").checked = false;
  $("#trim-box").classList.add("hidden");
  $("#btn-thumb").disabled = true;
  $("#vdur").classList.add("hidden");
  refreshOptions();
  updateButtons();
  renderCard();
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
  S.chooseAgain = false;
  resetVideo();
  busyBtn($("#btn-analyze"), true, "Analisando");
  N.analyze(S.analyzeReq, url);
}

function onAnalyzed(d) {
  if (d.reqId === S.probeReq) { showSuggestion(d); return; }
  if (d.reqId !== S.analyzeReq) return;
  busyBtn($("#btn-analyze"), false);
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
  // legendas, trecho e thumbnail
  const sb = $("#subs");
  sb.innerHTML = '<option value="">Sem legendas</option>';
  (d.subs || []).forEach((x, i) => { const o = document.createElement("option"); o.value = String(i); o.textContent = x.label; sb.appendChild(o); });
  $("#opt-trim").checked = false;
  $("#opt-exact").checked = false;
  $("#trim-start").value = "0:00";
  $("#trim-end").value = d.durationSec ? clockText(d.durationSec) : "";
  $("#btn-thumb").disabled = !((d.thumbs && d.thumbs.length) || d.thumbnail);
  const pend = S.pendingAuto;
  S.pendingAuto = null;
  if (pend) {
    if (pend.quality) q.value = pickQuality(pend.quality, d.heights || []);
    if (pend.section) {
      $("#opt-trim").checked = true;
      $("#trim-start").value = clockText(pend.section.start);
      $("#trim-end").value = clockText(pend.section.end);
      $("#opt-exact").checked = !!pend.section.exact;
    }
    if (pend.compat) { $("#opt-compat").checked = true; }
    if (pend.subs) {
      const idx = (d.subs || []).findIndex((x) => x.label === pend.subs);
      if (idx >= 0) sb.value = String(idx);
    }
  }
  $("#trim-box").classList.toggle("hidden", !$("#opt-trim").checked);
  $("#vdur").textContent = d.duration || "";
  $("#vdur").classList.toggle("hidden", !d.duration);
  refreshOptions();
  updateButtons();
  renderCard();
  if (pend) downloadFromUi();
}

/* qualidade pedida, ou a maior abaixo dela */
function pickQuality(wanted, heights) {
  if (wanted === "best" || wanted === "audio") return wanted;
  const w = parseInt(wanted, 10);
  if (heights.includes(w)) return String(w);
  const below = heights.filter((h) => h <= w);
  return below.length ? String(Math.max.apply(null, below)) : "best";
}

/* ---------- opções do download (H.264, legendas, trecho) ---------- */
function refreshOptions() {
  const v = S.video, quality = $("#quality").value, audio = quality === "audio";
  const compat = $("#opt-compat").checked;
  let text;
  if (!v) text = "Salva em MP4 H.264 + AAC, o formato que abre no CapCut, Premiere, VN, InShot e em qualquer celular.";
  else if (audio) text = "Não se aplica ao MP3.";
  else if (!compat) text = "Desligado: o vídeo vem no formato original do site (no YouTube, às vezes VP9 ou AV1, que alguns editores não abrem).";
  else {
    const p = compatPlan(true, quality, v);
    if (p.mode === "h264" && quality === "best") text = "✔ Sai em MP4 H.264 na melhor versão que já existe nesse formato (" + p.h + "p), sem conversão. Para uma resolução maior, escolha-a na lista: o app converte depois do download.";
    else if (p.mode === "h264") text = "✔ Sai em MP4 H.264 nessa qualidade, sem conversão.";
    else if (p.mode === "recode") text = "Este vídeo não tem H.264 " + (p.h ? "em " + p.h + "p" : "nessa qualidade") + ": depois do download o app converte o vídeo. No celular isso pode demorar bastante (principalmente acima de 1080p).";
    else text = "O app escolhe a versão H.264 quando o site oferecer.";
  }
  $("#compat-hint").textContent = text;
  const trim = $("#opt-trim").checked;
  const subs = (v && v.subs) || [];
  const chosen = $("#subs").value !== "";
  let st = "";
  if (v) {
    if (trim) st = "Legendas não são baixadas junto com um trecho.";
    else if (!subs.length) st = "Este vídeo não tem legendas.";
    else if (chosen && audio) st = "Com MP3, a legenda é salva como arquivo .srt.";
    else if (chosen) st = "Vai embutida no vídeo e também como arquivo .srt.";
    else st = subs.length + (subs.length === 1 ? " disponível." : " disponíveis.");
  }
  $("#subs-hint").textContent = st;
  $("#subs").disabled = !v || !subs.length || trim;
  updateDrawer();
}

/* gaveta "Mais opções": fechada por padrão; o título mostra o que está ligado */
function updateDrawer() {
  const open = !$("#opts-body").classList.contains("hidden");
  const active = [];
  if ($("#opt-compat").checked && $("#quality").value !== "audio") active.push("MP4 H.264");
  if ($("#opt-trim").checked) active.push("só um trecho");
  else if ($("#subs").value !== "") active.push("legenda");
  const head = $("#opts-toggle");
  head.setAttribute("aria-expanded", open ? "true" : "false");
  head.classList.toggle("active", active.length > 0);
  $("#opts-summary").textContent = active.length ? "Ligado: " + active.join(", ")
    : (open ? "Toque para fechar" : "MP4 para editores, trecho, legendas e thumbnail");
}

/* trecho escolhido: { section } ou { error } */
function readSection() {
  if (!$("#opt-trim").checked) return { section: null };
  const start = parseClock($("#trim-start").value), end0 = parseClock($("#trim-end").value);
  if (start === null) return { error: "Início inválido. Use minutos:segundos, por exemplo 2:15." };
  if (end0 === null) return { error: "Fim inválido. Use minutos:segundos, por exemplo 3:40." };
  const dur = S.video && S.video.durationSec;
  let end = end0;
  if (dur && start >= dur) return { error: "O início passa do fim do vídeo (" + clockText(dur) + ")." };
  if (dur && end > dur) end = dur;
  if (end <= start) return { error: "O fim do trecho precisa ser depois do início." };
  if (end - start < 1) return { error: "O trecho precisa ter pelo menos 1 segundo." };
  return { section: { start, end, exact: $("#opt-exact").checked } };
}

function downloadFromUi() {
  if (!S.video) return;
  const quality = $("#quality").value;
  const r = readSection();
  if (r.error) { modal("Trecho do vídeo", r.error); return; }
  const p = compatPlan($("#opt-compat").checked, quality, S.video);
  const subIdx = $("#subs").value;
  const sub = !r.section && subIdx !== "" ? (S.video.subs || [])[Number(subIdx)] : null;
  startDownload(S.video, quality, { compat: p.mode, height: p.h, sub, section: r.section });
}

function onAnalyzeError(d) {
  if (d.reqId === S.probeReq) return; // sugestão silenciosa: ignora links que não são vídeo
  if (d.reqId !== S.analyzeReq) return;
  busyBtn($("#btn-analyze"), false);
  S.pendingAuto = null;
  S.lastError = d.msg || "";
  resetVideo();
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

function startDownload(info, quality, o) {
  if (S.job && ACTIVE.includes(S.job.status)) {
    modal("Aguarde", "Já existe um download em andamento. Espere terminar para iniciar outro.");
    return;
  }
  quality = quality || "best";
  // sem opções explícitas (pesquisa, sugestão): usa a preferência de H.264
  o = o || compatPlan(!!S.settings.compat, quality, info.codecKnown ? info : null);
  if (!o.compat && o.mode) o = { compat: o.mode, height: o.h };
  S.jobInfo = { url: info.url, title: info.title || "", uploader: info.uploader || "", duration: info.duration || "",
    thumb: info.thumbnail || info.thumb || "" };
  S.chooseAgain = false;
  const payload = {
    url: info.url, quality, title: info.title || "", uploader: info.uploader || "",
    duration: info.duration || "", thumb: info.thumbnail || info.thumb || "",
    compat: o.compat || "off", height: o.height || 0,
  };
  if (o.sub) { payload.subLang = o.sub.code; payload.subAuto = !!o.sub.auto; payload.subLabel = o.sub.label; }
  if (o.section) payload.section = o.section;
  N.download(JSON.stringify(payload));
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

/* Cartão do vídeo: o mesmo cartão mostra as opções, o andamento e o resultado do download. */
function renderCard() {
  const j = S.job;
  const shown = !!j && (ACTIVE.includes(j.status) || j.status === "done" || j.status === "error");
  const active = !!j && ACTIVE.includes(j.status);
  const same = !S.video || (shown && S.jobInfo && S.jobInfo.url === S.video.url);
  const info = S.video || (shown ? S.jobInfo : null);
  $("#video-card").classList.toggle("hidden", !info);
  $("#link-tip").classList.toggle("hidden", !!info);
  // com um vídeo na tela, a ação principal passa a ser "Baixar"
  $("#btn-analyze").classList.toggle("pri", !S.video);
  if (!info) return;
  if (!S.video) {  // download vindo da pesquisa, do histórico ou da sugestão
    const th = $("#thumb");
    th.onerror = () => { th.dataset.real = ""; placeholderImg(th); };
    if (info.thumb) { th.dataset.real = "1"; th.src = info.thumb; } else { th.dataset.real = ""; th.src = img("placeholder"); }
    $("#vtitle").textContent = info.title || "Download";
    $("#vmeta").textContent = info.uploader || "";
    $("#vdur").textContent = info.duration || "";
    $("#vdur").classList.toggle("hidden", !info.duration);
  }
  const choose = !!S.video && (!shown || !same || j.status === "error" || S.chooseAgain);
  $("#choose-box").classList.toggle("hidden", !choose);
  $("#progress-box").classList.toggle("hidden", !shown || (!same && !active));
  $("#btn-cancel").classList.toggle("hidden", !active);
  $("#done-actions").classList.toggle("hidden", !(shown && j.status === "done" && same));
  $("#btn-again").classList.toggle("hidden", !S.video || choose);
}

function onJob(j) {
  S.job = j;
  if (!S.jobInfo || S.jobInfo.url !== j.url) S.jobInfo = { url: j.url, title: j.title || "" };
  const active = ACTIVE.includes(j.status);
  const pct = Math.max(0, Math.min(100, j.pct || 0));
  $("#progress").style.width = (j.status === "done" ? 100 : pct) + "%";
  setIndeterminate(j.status === "starting" || j.status === "saving" || j.status === "processing");
  $("#topbar-fill").style.width = active ? Math.max(3, pct) + "%" : "0";
  // com outro vídeo na tela, diz qual vídeo está baixando
  const other = active && S.video && S.video.url !== j.url && j.title;
  setStatus((other ? "Baixando: " + j.title.slice(0, 60) + "\n" : "") + j.text,
    j.status === "done" ? "ok" : (j.status === "error" ? "err" : ""));
  updateButtons();
  renderCard();
}

function onDone(d) {
  const e = d.entry;
  S.lastDone = e;
  const note = d.note || (d.fallback ? "formato ajustado para compatibilidade" : "");
  setStatus("✔ " + (note ? "Concluído, " + note + "." : "Download concluído!") +
    "\nSalvo em Download/BaixadorDeVideos", "ok");
  renderCard();
  toast("Download concluído!");
  S.history = [e].concat(S.history.filter((h) => h.id !== e.id));
  if (S.tab === "historico") renderHistory();
  if (S.tab === "player") renderPlayerList();
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
$("#btn-download").addEventListener("click", downloadFromUi);
$("#quality").addEventListener("change", refreshOptions);
$("#opts-toggle").addEventListener("click", () => {
  $("#opts-body").classList.toggle("hidden");
  updateDrawer();
});
$("#subs").addEventListener("change", refreshOptions);
$("#opt-compat").addEventListener("change", (e) => { S.settings.compat = e.target.checked; saveSettings(); refreshOptions(); });
$("#opt-trim").addEventListener("change", (e) => {
  $("#trim-box").classList.toggle("hidden", !e.target.checked);
  refreshOptions();
});
["#trim-start", "#trim-end"].forEach((sel) => $(sel).addEventListener("blur", (e) => {
  const v = parseClock(e.target.value);
  if (v !== null) e.target.value = clockText(v);  // "1 30" -> "1:30"
}));
$("#btn-thumb").addEventListener("click", () => {
  const v = S.video;
  if (!v) return;
  const urls = (v.thumbs && v.thumbs.length) ? v.thumbs : [v.thumbnail];
  busyBtn($("#btn-thumb"), true, "Salvando");
  N.saveThumb(JSON.stringify(urls), v.title || "thumbnail", v.id || "");
});
$("#btn-cancel").addEventListener("click", () => N.cancel());
$("#btn-folder").addEventListener("click", () => N.openDownloads());
$("#btn-folder-hist").addEventListener("click", () => N.openDownloads());
$("#btn-again").addEventListener("click", () => { S.chooseAgain = true; renderCard(); });
$("#btn-open-last").addEventListener("click", () => { if (S.lastDone) playEntry(S.lastDone); });
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
  N.search(S.searchReq, q, S.searchSrc);
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
      '<button class="btn sm" data-a="pick">Qualidade</button></div></div>';
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
$$("#seg-src button").forEach((b) => b.addEventListener("click", () => {
  S.searchSrc = b.dataset.v;
  $$("#seg-src button").forEach((x) => x.classList.toggle("on", x === b));
  if ($("#q").value.trim()) search();
}));
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
  $("#hist-count").textContent = S.history.length ? "Histórico (" + S.history.length + ")" : "Histórico";
  const items = S.history.filter((h) => !f || ((h.title || "") + " " + (h.uploader || "")).toLowerCase().includes(f));
  if (!items.length) {
    box.innerHTML = f ? '<p class="muted small" style="text-align:center;padding:20px">Nenhum resultado para esse filtro.</p>'
      : emptyArt("Nenhum download no histórico ainda. Os vídeos que você baixar aparecerão aqui.");
    return;
  }
  box.innerHTML = "";
  items.slice(0, S.histLimit).forEach((h) => {
    const el = document.createElement("div");
    el.className = "res item";
    const who = [h.uploader, h.duration].filter(Boolean).join("  •  ");
    const meta = [h.date, entryLabel(h), fmtBytes(h.size)].filter(Boolean).join("  •  ");
    el.innerHTML = '<img class="sthumb" alt="">' +
      '<div class="info"><div class="t">' + esc(h.title) + "</div>" +
      (who ? '<div class="m">' + esc(who) + "</div>" : "") +
      '<div class="m">' + esc(meta) + "</div>" +
      (h.exists ? "" : '<div class="m missing">Arquivo não encontrado no celular</div>') + "</div>" +
      '<button class="icon-btn" data-a="menu" aria-label="Mais ações">⋯</button>';
    const im = el.querySelector("img");
    im.onerror = () => placeholderImg(im);
    im.src = h.thumb || img("placeholder");
    el.querySelector('[data-a="menu"]').addEventListener("click", (e) => { e.stopPropagation(); historyActions(h); });
    el.addEventListener("click", () => { if (h.exists) playEntry(h); else historyActions(h); });
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

/* menu de ações de um item do histórico */
function historyActions(h) {
  const acts = [];
  if (h.exists) acts.push({ label: "▶ Assistir", pri: true, fn: () => playEntry(h) });
  acts.push({ label: "↻ Baixar de novo", pri: !h.exists, fn: () => redownload(h) });
  acts.push({ label: "Escolher outra qualidade", fn: () => { S.pendingAuto = null; showTab("baixar"); analyze(h.url); } });
  if (h.exists) acts.push({ label: "Compartilhar", fn: () => N.shareFile(h.uri, h.mime || "") });
  acts.push({ label: "Remover do histórico", cls: "link-danger", fn: () => {
    N.removeHistory(h.id);
    S.history = S.history.filter((x) => x.id !== h.id);
    renderHistory();
    toast("Removido do histórico. O arquivo continua no celular.");
  } });
  acts.push({ label: "Fechar", ghost: true });
  modal(h.title || "Vídeo", h.exists ? "" : "O arquivo foi movido ou apagado do celular.", acts, { sheet: true });
}

/* "Baixar de novo": analisa o link e baixa com as mesmas opções (pergunta se era um trecho) */
function redownload(h) {
  if (S.job && ACTIVE.includes(S.job.status)) {
    modal("Aguarde", "Já existe um download em andamento. Espere terminar para iniciar outro.");
    return;
  }
  const go = (section) => {
    S.pendingAuto = { quality: h.quality, section, compat: !!h.compat, subs: h.subs || "" };
    showTab("baixar");
    analyze(h.url);
  };
  if (h.section) {
    modal("Baixar de novo", "Este download foi só um trecho (" + sectionText(h.section) + "). O que você quer baixar agora?", [
      { label: "Só o trecho (" + sectionText(h.section) + ")", pri: true, fn: () => go(h.section) },
      { label: "O vídeo inteiro", fn: () => go(null) },
    ]);
    return;
  }
  go(null);
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


/* ---------- ABA PLAYER ---------- */
const video = $("#video");

function fmtClock(t) {
  if (!isFinite(t) || t < 0) t = 0;
  t = Math.floor(t);
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
  const mm = String(m).padStart(2, "0"), ss = String(s).padStart(2, "0");
  return h ? h + ":" + mm + ":" + ss : mm + ":" + ss;
}

function playerItems() {
  const f = ($("#p-filter").value || "").trim().toLowerCase();
  return S.history.filter((h) => h.exists && h.uri &&
    (!f || ((h.title || "") + " " + (h.uploader || "")).toLowerCase().includes(f)));
}

function renderPlayerList() {
  const box = $("#p-list");
  if (!S.histLoaded) { box.innerHTML = '<p class="muted small" style="text-align:center;padding:20px">Carregando...</p>'; return; }
  const items = playerItems();
  if (!items.length) {
    box.innerHTML = emptyArt($("#p-filter").value.trim() ? "Nenhum vídeo para esse filtro."
      : "Nenhum vídeo baixado ainda. Os vídeos que você baixar aparecem aqui para assistir.");
    return;
  }
  box.innerHTML = "";
  items.slice(0, 80).forEach((h) => {
    const playing = S.playing && S.playing.id === h.id;
    const el = document.createElement("div");
    el.className = "res item" + (playing ? " playing" : "");
    el.innerHTML = '<img class="sthumb" alt="">' +
      '<div class="info"><div class="t">' + esc(h.title) + "</div>" +
      '<div class="m">' + esc([h.uploader, h.duration, entryLabel(h)].filter(Boolean).join("  •  ")) + "</div></div>" +
      '<button class="icon-btn' + (playing ? " pri" : "") + '" data-a="play" aria-label="' + (playing ? "Pausar ou continuar" : "Assistir") + '">' +
      (playing ? "⏸" : "▶") + "</button>";
    const im = el.querySelector("img");
    im.onerror = () => placeholderImg(im);
    im.src = h.thumb || img("placeholder");
    el.addEventListener("click", () => {
      if (playing) { togglePlay(); return; }
      playEntry(h);
    });
    box.appendChild(el);
  });
}

function playEntry(h) {
  if (!h) return;
  if (h.exists === false) {
    modal("Arquivo não encontrado", "Esse arquivo foi movido ou apagado. Use \"Baixar de novo\" para baixá-lo outra vez.");
    return;
  }
  const url = N.mediaUrl(h.uri, h.mime || "");
  showTab("player");
  $("#p-error").classList.add("hidden");
  S.playing = h;
  $("#p-title").textContent = h.title || h.name || "Vídeo";
  if (!url) { playerError(); return; }
  $("#player-empty").classList.add("hidden");
  video.poster = h.thumb || "";
  video.src = url;
  video.loop = $("#p-loop").classList.contains("on");
  video.playbackRate = parseFloat($("#p-speed").value) || 1;
  const pr = video.play();
  if (pr && pr.catch) pr.catch(() => {});
  renderPlayerList();
}

function playerError() {
  const box = $("#p-error");
  box.textContent = "Este arquivo não pode ser reproduzido no player do app (formato não suportado pelo celular).";
  const b = document.createElement("button");
  b.className = "btn pri";
  b.textContent = "Abrir em outro app";
  b.addEventListener("click", () => { if (S.playing) N.openFile(S.playing.uri, S.playing.mime || ""); });
  box.appendChild(document.createElement("br"));
  box.appendChild(b);
  box.classList.remove("hidden");
}

function togglePlay() {
  if (!video.src) { const it = playerItems(); if (it.length) playEntry(it[0]); return; }
  if (video.paused || video.ended) { const pr = video.play(); if (pr && pr.catch) pr.catch(() => {}); }
  else video.pause();
}

function stepPlayer(delta) {
  const items = playerItems();
  if (!items.length) return;
  const idx = S.playing ? items.findIndex((h) => h.id === S.playing.id) : -1;
  playEntry(idx < 0 ? items[0] : items[(idx + delta + items.length) % items.length]);
}

let seeking = false;
const seekEl = $("#p-seek");
seekEl.addEventListener("input", () => {
  seeking = true;
  if (isFinite(video.duration)) $("#p-cur").textContent = fmtClock(video.duration * seekEl.value / 1000);
});
seekEl.addEventListener("change", () => {
  if (isFinite(video.duration) && video.duration > 0) video.currentTime = video.duration * seekEl.value / 1000;
  seeking = false;
});
video.addEventListener("timeupdate", () => {
  if (seeking) return;
  $("#p-cur").textContent = fmtClock(video.currentTime);
  if (isFinite(video.duration) && video.duration > 0) seekEl.value = Math.round(1000 * video.currentTime / video.duration);
});
video.addEventListener("loadedmetadata", () => { $("#p-dur").textContent = fmtClock(video.duration); });
video.addEventListener("play", () => { $("#p-play").textContent = "⏸"; N.keepScreenOn(true); renderPlayerList(); });
video.addEventListener("pause", () => { $("#p-play").textContent = "▶"; N.keepScreenOn(false); });
video.addEventListener("ended", () => { $("#p-play").textContent = "▶"; N.keepScreenOn(false); });
video.addEventListener("error", () => { if (video.getAttribute("src")) playerError(); });
video.addEventListener("click", togglePlay);

$("#p-play").addEventListener("click", togglePlay);
$("#p-back").addEventListener("click", () => { video.currentTime = Math.max(0, video.currentTime - 10); });
$("#p-fwd").addEventListener("click", () => {
  if (isFinite(video.duration)) video.currentTime = Math.min(video.duration, video.currentTime + 10);
});
$("#p-prev").addEventListener("click", () => stepPlayer(-1));
$("#p-next").addEventListener("click", () => stepPlayer(1));
$("#p-mute").addEventListener("click", () => {
  video.muted = !video.muted;
  $("#p-mute").textContent = video.muted ? "🔇" : "🔊";
});
$("#p-speed").addEventListener("change", (e) => { video.playbackRate = parseFloat(e.target.value) || 1; });
$("#p-loop").addEventListener("click", () => {
  const on = !$("#p-loop").classList.contains("on");
  $("#p-loop").classList.toggle("on", on);
  video.loop = on;
});
$("#p-full").addEventListener("click", () => {
  if (!video.src) return;
  video.controls = true;
  const req = video.requestFullscreen || video.webkitRequestFullscreen;
  if (req) { const pr = req.call(video); if (pr && pr.catch) pr.catch(() => { video.controls = false; }); }
});
document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement) { video.controls = false; applyLook(); }
});
let pFilterTimer = null;
$("#p-filter").addEventListener("input", () => { clearTimeout(pFilterTimer); pFilterTimer = setTimeout(renderPlayerList, 200); });

/* ---------- ABA CONFIGURAÇÕES ---------- */
$$("#seg-theme button").forEach((b) => b.addEventListener("click", () => {
  S.settings.theme = b.dataset.v; saveSettings(); applyLook();
}));
$$("[data-drawer]").forEach((head) => head.addEventListener("click", () => {
  const body = document.getElementById(head.dataset.drawer);
  body.classList.toggle("hidden");
  head.setAttribute("aria-expanded", body.classList.contains("hidden") ? "false" : "true");
}));
$("#style-toggle").addEventListener("click", () => {
  const body = $("#style-body");
  body.classList.toggle("hidden");
  $("#style-toggle").setAttribute("aria-expanded", body.classList.contains("hidden") ? "false" : "true");
});
$$("#seg-style button").forEach((b) => b.addEventListener("click", () => {
  S.settings.style = b.dataset.v; saveSettings(); applyLook();
  if (S.tab === "historico") renderHistory();
}));
[["#opt-notify", "notify"], ["#opt-clipboard", "clipboard"], ["#opt-autoupdate", "autoUpdate"], ["#opt-autocheck", "autoCheckApp"]].forEach(([sel, key]) => {
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
$("#btn-report").addEventListener("click", copyReport);
$("#btn-issues").addEventListener("click", () => N.openUrl(ISSUES_URL));

function setCookies(loaded) {
  const c = $("#st-cookies");
  c.textContent = loaded ? "carregado" : "nenhum";
  c.className = loaded ? "ok" : "no";
}

function fillSettings(state) {
  $("#opt-compat").checked = !!S.settings.compat;
  $("#opt-notify").checked = !!S.settings.notify;
  $("#opt-clipboard").checked = !!S.settings.clipboard;
  $("#opt-autoupdate").checked = !!S.settings.autoUpdate;
  $("#opt-autocheck").checked = S.settings.autoCheckApp !== false;
  if (state) {
    $("#st-ytdlp").textContent = state.ytdlp || "preparando...";
    $("#st-folder").textContent = state.folder || "Download/BaixadorDeVideos";
    $("#about").textContent = "Produzido por Lagaz";
    if (state.version) {
      S.version = state.version;
      $("#upd-current").textContent = state.version;
      $("#version-foot").textContent = "Baixador de Vídeos  •  versão " + state.version;
    }
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


/* ---------- atualizações do aplicativo ---------- */
function checkAppUpdate(manual) {
  if (manual) {
    busyBtn($("#btn-check-update"), true, "Buscando");
    $("#upd-status").textContent = "Procurando uma versão nova...";
    $("#upd-status").className = "muted small";
  }
  N.checkAppUpdate(!!manual);
}

function onAppUpdate(d) {
  busyBtn($("#btn-check-update"), false);
  const st = $("#upd-status");
  if (d.state === "error") {
    st.textContent = "Não foi possível verificar agora (sem internet?).";
    st.className = "small warn-text";
    if (d.manual) toast("Não foi possível verificar atualizações agora.");
    return;
  }
  S.settings.lastAppCheck = Date.now();
  S.settings.knownAppVersion = d.info.version;
  saveSettings();
  if (d.state !== "available") {
    S.appUpdate = null;
    $("#upd-actions").classList.add("hidden");
    $("#upd-notes").classList.add("hidden");
    $("#app-update-banner").classList.add("hidden");
    st.textContent = "Você já está na versão mais recente. ✔";
    st.className = "small exists";
    if (d.manual) toast("Você já está na versão mais recente (" + (S.version || d.info.current) + ").");
    return;
  }
  S.appUpdate = d.info;
  st.textContent = "Nova versão disponível: " + d.info.version + " 🎉";
  st.className = "small";
  st.style.color = "var(--accent-text)";
  if (d.info.notes) { $("#upd-notes").textContent = d.info.notes; $("#upd-notes").classList.remove("hidden"); }
  const btn = $("#btn-install-update");
  btn.textContent = "⬇ Baixar e instalar";
  btn.disabled = !d.info.url;
  $("#upd-actions").classList.remove("hidden");
  $("#app-update-banner-text").textContent = "🎉 Nova versão " + d.info.version + " do app disponível.";
  $("#app-update-banner").classList.remove("hidden");
}

function onAppUpdateProgress(d) {
  $("#upd-bar").classList.remove("hidden");
  $("#upd-bar").classList.toggle("indet", d.pct < 0);
  if (d.pct >= 0) {
    $("#upd-progress").style.width = d.pct + "%";
    $("#btn-install-update").textContent = "Baixando... " + d.pct + "%";
  }
}

function onAppUpdateReady(d) {
  $("#upd-bar").classList.add("hidden");
  const btn = $("#btn-install-update");
  btn.disabled = false;
  btn.textContent = "Instalar a versão " + d.version;
  btn.dataset.ready = "1";
  if (!d.sameKey) {
    modal("Atenção antes de instalar",
      "Esta versão foi assinada com uma chave diferente da versão instalada, então o Android não deixa " +
      "atualizar por cima.\n\nPara instalar: desinstale o app atual e instale a versão nova pela página de " +
      "downloads. O histórico e as configurações deste aparelho serão apagados (os vídeos baixados continuam " +
      "na pasta Download).",
      [{ label: "Abrir a página de downloads", pri: true, fn: () => N.openUrl(S.appUpdate ? S.appUpdate.page : "") }]);
    return;
  }
  N.installAppUpdate();
}

function onAppUpdateError(d) {
  $("#upd-bar").classList.add("hidden");
  const btn = $("#btn-install-update");
  btn.disabled = false;
  btn.textContent = "⬇ Baixar e instalar";
  delete btn.dataset.ready;
  modal("Atualização", "Não foi possível atualizar agora.\n\n" + d.msg,
    [{ label: "Abrir a página de downloads", pri: true, fn: () => N.openUrl(S.appUpdate ? S.appUpdate.page : "") }]);
}

$("#btn-check-update").addEventListener("click", () => checkAppUpdate(true));
$("#btn-install-update").addEventListener("click", () => {
  const btn = $("#btn-install-update");
  if (btn.dataset.ready === "1") { N.installAppUpdate(); return; }
  if (!S.appUpdate) return;
  confirmBox("Atualizar o app",
    "Baixar e instalar a versão " + S.appUpdate.version + "?\n\nO Android vai mostrar a tela de instalação; " +
    "toque em Atualizar. Seu histórico e suas configurações são mantidos.",
    "Baixar e instalar", () => {
      btn.disabled = true;
      btn.textContent = "Baixando...";
      N.downloadAppUpdate();
    });
});
$("#btn-update-page").addEventListener("click", () => N.openUrl(S.appUpdate ? S.appUpdate.page : ""));
$("#btn-go-update").addEventListener("click", () => {
  showTab("config");
  setTimeout(() => $("#card-updates").scrollIntoView({ behavior: "smooth", block: "start" }), 50);
});

function autoCheckAppUpdate() {
  if (S.settings.autoCheckApp === false) return;
  if (Date.now() - (S.settings.lastAppCheck || 0) < APP_CHECK_EVERY) {
    // verificou há pouco: só volta a avisar se já sabia de uma versão nova
    if (S.settings.knownAppVersion && S.version && S.settings.knownAppVersion !== S.version) checkAppUpdate(false);
    return;
  }
  checkAppUpdate(false);
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
        else { S.lastError = "Falha no download.\n" + d.msg; errorHelp(S.lastError, d.code); }
        break;
      case "history": S.history = d.items || []; S.histLoaded = true; renderHistory(); renderPlayerList(); break;
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
      case "restoreBars": applyLook(); break;
      case "appUpdate": onAppUpdate(d); break;
      case "appUpdateProgress": onAppUpdateProgress(d); break;
      case "appUpdateReady": onAppUpdateReady(d); break;
      case "appUpdateError": onAppUpdateError(d); break;
      case "appInstallPermission":
        toast("Permita \"Instalar apps desconhecidos\" para o Baixador de Vídeos e volte ao app.", 5000);
        break;
      case "focus": checkClipboard(); break;
      case "thumbSaved":
        busyBtn($("#btn-thumb"), false);
        toast("🖼 Thumbnail salva em Download/BaixadorDeVideos (" + d.w + "×" + d.h + ")", 3500);
        break;
      case "thumbError":
        busyBtn($("#btn-thumb"), false);
        S.lastError = d.msg || "";
        errorHelp(d.msg || "Não foi possível salvar a thumbnail.", "generic");
        break;
      default: break;
    }
  },
  onBack() {
    if (!$("#modal").classList.contains("hidden")) { closeModal(); return true; }
    if (document.fullscreenElement) { document.exitFullscreen().catch(() => {}); return true; }
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
  setTimeout(autoCheckAppUpdate, 4000);
  if (st.shared) { showTab("baixar"); analyze(st.shared); } else { setTimeout(checkClipboard, 600); }
})();
