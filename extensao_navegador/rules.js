// Regras para decidir se a página atual é uma página de vídeo "baixável".
// (Arquivo compartilhado: usado pelo background.js e testado fora do navegador.)

// Serviços com proteção anti-cópia (DRM): não adianta sugerir.
const BDV_IGNORED_HOSTS = [
  "netflix.com", "primevideo.com", "disneyplus.com", "max.com", "hbomax.com",
  "hulu.com", "paramountplus.com", "peacocktv.com", "tv.apple.com", "spotify.com",
];

// Sites conhecidos: só vale quando a página é de UM vídeo (e não a home, o feed etc.).
const BDV_SITE_RULES = [
  { host: /(^|\.)youtube\.com$/, ok: u => (u.pathname === "/watch" && u.searchParams.has("v")) || u.pathname.startsWith("/shorts/") || u.pathname.startsWith("/live/") },
  { host: /^youtu\.be$/, ok: u => u.pathname.length > 1 },
  { host: /(^|\.)vimeo\.com$/, ok: u => /^\/(\d+|channels\/[^/]+\/\d+|groups\/[^/]+\/videos\/\d+)/.test(u.pathname) },
  { host: /(^|\.)dailymotion\.com$/, ok: u => u.pathname.startsWith("/video/") },
  { host: /(^|\.)twitch\.tv$/, ok: u => u.pathname.startsWith("/videos/") || /\/clip\//.test(u.pathname) || u.hostname === "clips.twitch.tv" },
  { host: /(^|\.)tiktok\.com$/, ok: u => /\/video\/\d+/.test(u.pathname) },
  { host: /(^|\.)instagram\.com$/, ok: u => /^\/(reel|reels|p|tv)\//.test(u.pathname) },
  { host: /(^|\.)facebook\.com$/, ok: u => /^\/(watch|reel)/.test(u.pathname) || /\/videos\//.test(u.pathname) },
  { host: /^(www\.)?(x|twitter)\.com$/, ok: u => /\/status\/\d+/.test(u.pathname) },
  { host: /(^|\.)reddit\.com$/, ok: u => /\/comments\//.test(u.pathname) },
  { host: /(^|\.)bilibili\.com$/, ok: u => u.pathname.startsWith("/video/") },
  { host: /(^|\.)streamable\.com$/, ok: u => u.pathname.length > 1 },
  { host: /(^|\.)soundcloud\.com$/, ok: u => u.pathname.split("/").filter(Boolean).length >= 2 },
];

// info = { duration, live, muted, loop, w, h }  (dados do <video> que está tocando)
function bdvEvaluate(info, pageUrl) {
  let url;
  try { url = new URL(pageUrl); } catch (e) { return { ok: false, reason: "url" }; }
  if (!/^https?:$/.test(url.protocol)) return { ok: false, reason: "protocol" };
  const host = url.hostname.replace(/^www\./, "");
  if (BDV_IGNORED_HOSTS.some(h => host === h || host.endsWith("." + h))) return { ok: false, reason: "ignored" };
  if (info.w < 200 || info.h < 110) return { ok: false, reason: "small" };

  const rule = BDV_SITE_RULES.find(r => r.host.test(url.hostname));
  if (rule) return rule.ok(url) ? { ok: true, url: url.href } : { ok: false, reason: "not-watch-page" };

  // Site desconhecido: regras mais rígidas para não sugerir propaganda/vídeo de fundo.
  if (info.muted || info.loop) return { ok: false, reason: "muted-or-loop" };
  if (!info.live && !(info.duration >= 45)) return { ok: false, reason: "short" };
  return { ok: true, url: url.href };
}

// Player embutido (iframe) -> endereço da página do vídeo
function bdvEmbedToWatch(frameUrl) {
  try {
    const u = new URL(frameUrl);
    let m;
    if (/(^|\.)youtube(-nocookie)?\.com$/.test(u.hostname) && (m = u.pathname.match(/^\/embed\/([\w-]{6,})/))) {
      return "https://www.youtube.com/watch?v=" + m[1];
    }
    if (u.hostname === "player.vimeo.com" && (m = u.pathname.match(/^\/video\/(\d+)/))) {
      return "https://vimeo.com/" + m[1];
    }
  } catch (e) { /* ignora */ }
  return null;
}

if (typeof module !== "undefined") module.exports = { bdvEvaluate, bdvEmbedToWatch };
