// Service worker: recebe os avisos das páginas, decide se vale sugerir e
// manda para o programa Baixador de Vídeos (que roda no seu computador).
importScripts("rules.js");

const BASE = "http://127.0.0.1:47653";
const lastSent = new Map();

async function isEnabled() {
  const { enabled = true } = await chrome.storage.local.get("enabled");
  return enabled;
}

async function postJson(path, payload) {
  try {
    const r = await fetch(BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await r.json();
  } catch (e) {
    return null; // programa fechado
  }
}

function setBadge(ok) {
  chrome.action.setBadgeText({ text: ok ? "" : "off" });
  chrome.action.setBadgeBackgroundColor({ color: "#6b7280" });
}

async function ping() {
  try {
    const r = await fetch(BASE + "/ping");
    const j = await r.json();
    setBadge(true);
    return j;
  } catch (e) {
    setBadge(false);
    return null;
  }
}

async function handleVideo(msg, sender) {
  if (!(await isEnabled())) return;
  const tab = sender.tab;
  if (!tab || !tab.url) return;

  const embed = msg.isTop ? null : bdvEmbedToWatch(msg.frameUrl);
  const verdict = bdvEvaluate(msg, embed || tab.url);
  if (!verdict.ok) return;

  const now = Date.now();
  if (now - (lastSent.get(verdict.url) || 0) < 10 * 60 * 1000) return;
  lastSent.set(verdict.url, now);

  await postJson("/video", {
    url: verdict.url,
    title: msg.title || tab.title || "",
    duration: msg.duration,
    live: msg.live,
    poster: msg.poster || "",
    manual: false,
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg) return;
  if (msg.type === "video") {
    handleVideo(msg, sender);
    sendResponse({ ok: true });
  } else if (msg.type === "ping") {
    ping().then(sendResponse);
    return true;
  } else if (msg.type === "manual") {
    postJson("/video", { url: msg.url, title: msg.title || "", manual: true }).then(sendResponse);
    return true;
  }
});

chrome.alarms.create("ping", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(a => { if (a.name === "ping") ping(); });
chrome.runtime.onStartup.addListener(ping);
chrome.runtime.onInstalled.addListener(ping);
