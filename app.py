"""
Baixador de Vídeos - aplicativo desktop para Windows (interface moderna)
Cole o link, veja a miniatura, escolha a qualidade e baixe.
Usa o yt-dlp (suporta YouTube e milhares de outros sites).
"""
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import hashlib
import tempfile
import threading
import time
import urllib.request
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import customtkinter as ctk
import yt_dlp
from PIL import Image, ImageOps
from yt_dlp.utils import DownloadCancelled

import arte

try:  # ícone na bandeja do sistema (opcional)
    import pystray
except Exception:  # noqa: BLE001
    pystray = None

# ---------- Tema ----------
ctk.set_default_color_theme("blue")

# Estilos visuais (cores em pares: tema claro, tema escuro).
# "classico" é o visual principal; "cyberpunk" é opcional (aba ⚙).
STYLES = {
    "classico": dict(
        BG=("#f3f4f9", "#0f1115"),
        CARD=("#ffffff", "#181b22"),
        CARD_2=("#e9ebf3", "#232833"),
        CARD_2_HOVER=("#dcdfec", "#2d3340"),
        LINE=("#e9ebf3", "#232833"),
        ACCENT="#7c3aed",
        ACCENT_HOVER="#6d28d9",
        ON_ACCENT="#ffffff",
        DANGER="#dc2626",
        DANGER_HOVER="#b91c1c",
        MUTED=("#6b7280", "#9ca3af"),
        SUCCESS=("#15803d", "#22c55e"),
        TEXT=("#1f2937", "#e5e7eb"),
        TEXT_SOFT=("#374151", "#d1d5db"),
        WARN=("#b45309", "#f59e0b"),
        ERROR=("#dc2626", "#f87171"),
        BANNER_BG=("#fef3c7", "#3b2a0a"),
        BANNER_TEXT=("#92400e", "#fbbf24"),
        REMOVE_HOVER=("#fee2e2", "#3b1010"),
        SEG_UNSEL=("#7c819a", "#2d3340"),
        SEG_UNSEL_HOVER=("#666b85", "#3a4050"),
        SEG_TEXT=("#ffffff", "#e5e7eb"),
        ACCENT_TEXT=("#6d28d9", "#a78bfa"),
        FOOTER_TEXT=("#5b5f80", "#a5a8c0"),
        ENTRY_BORDER=0,
        CARD_BORDER=0,
        HUD=False,
        SHARP=False,
        SOFT=False,
        FONT=None,
    ),
    "cyberpunk": dict(
        BG=("#e7e8eb", "#101013"),
        CARD=("#f5f5f7", "#1a1b1f"),
        CARD_2=("#dcdde1", "#26272d"),
        CARD_2_HOVER=("#cdced4", "#32343b"),
        LINE=("#b9bbc2", "#34363d"),
        ACCENT="#f7d61e",
        ACCENT_HOVER="#e2c210",
        ON_ACCENT="#0c0c0e",
        DANGER="#e8263a",
        DANGER_HOVER="#c41d30",
        MUTED=("#5d6068", "#8d9099"),
        SUCCESS=("#0f8a5f", "#2fd38a"),
        TEXT=("#121215", "#ececef"),
        TEXT_SOFT=("#2c2e34", "#c9cbd1"),
        WARN=("#8a5f00", "#f7d61e"),
        ERROR=("#c41d30", "#ff4d5e"),
        BANNER_BG=("#f3e49a", "#2a2408"),
        BANNER_TEXT=("#4d3e00", "#f7d61e"),
        REMOVE_HOVER=("#f6c9ce", "#3a1218"),
        SEG_UNSEL=("#b9bbc2", "#7a7d86"),
        SEG_UNSEL_HOVER=("#a8aab2", "#8d9099"),
        SEG_TEXT=("#0c0c0e", "#0c0c0e"),
        ACCENT_TEXT=("#7a6200", "#f7d61e"),
        FOOTER_TEXT=("#2c2e34", "#c9cbd1"),
        ENTRY_BORDER=1,
        CARD_BORDER=1,
        HUD=True,
        SHARP=True,
        SOFT=False,
        FONT="Bahnschrift",  # fonte técnica que já vem no Windows 10/11
    ),
    "retro": dict(
        BG=("#f2ead8", "#1f1c19"),
        CARD=("#fbf6ea", "#2a2622"),
        CARD_2=("#e7dcc4", "#36312c"),
        CARD_2_HOVER=("#dccfb2", "#433d36"),
        LINE=("#2b2724", "#5a5148"),
        ACCENT="#d9622b",
        ACCENT_HOVER="#bf5223",
        ON_ACCENT="#fbf6ea",
        DANGER="#c0422b",
        DANGER_HOVER="#a5361f",
        MUTED=("#6e645a", "#aa9f91"),
        SUCCESS=("#2f6f6a", "#5fb3a8"),
        TEXT=("#2b2724", "#f2ead8"),
        TEXT_SOFT=("#4a433c", "#ddd3bf"),
        WARN=("#9a6a0c", "#e3a72f"),
        ERROR=("#b0361f", "#f08060"),
        BANNER_BG=("#f3e1b0", "#3a2f17"),
        BANNER_TEXT=("#5a3f00", "#e3a72f"),
        REMOVE_HOVER=("#f2d4c8", "#4a2a20"),
        SEG_UNSEL=("#d8ccb2", "#4a433c"),
        SEG_UNSEL_HOVER=("#cbbea2", "#57504a"),
        SEG_TEXT=("#2b2724", "#f2ead8"),
        ACCENT_TEXT=("#b04a1c", "#e3a72f"),
        FOOTER_TEXT=("#2b2724", "#f2ead8"),
        ENTRY_BORDER=2,
        CARD_BORDER=2,
        HUD=False,
        SHARP=False,
        SOFT=True,
        FONT="Consolas",  # fonte de "máquina de escrever" que já vem no Windows
    ),
    "steampunk": dict(
        BG=("#efe2c4", "#1c140e"),
        CARD=("#f7ecd2", "#2a1d14"),
        CARD_2=("#e3d2ad", "#3b2a1e"),
        CARD_2_HOVER=("#d8c398", "#4a3627"),
        LINE=("#b5893a", "#9a7230"),
        ACCENT="#b5893a",
        ACCENT_HOVER="#9a7230",
        ON_ACCENT="#1c140e",
        DANGER="#a8442a",
        DANGER_HOVER="#8c3620",
        MUTED=("#6d5a43", "#b39f80"),
        SUCCESS=("#3f7a6c", "#6fb3a2"),
        TEXT=("#2a1d14", "#efe2c4"),
        TEXT_SOFT=("#4a3826", "#dccbaa"),
        WARN=("#8a5a10", "#e0b04a"),
        ERROR=("#a8442a", "#e98a6a"),
        BANNER_BG=("#ecd9a8", "#3a2a12"),
        BANNER_TEXT=("#5a3a08", "#e0b04a"),
        REMOVE_HOVER=("#ecc9b8", "#4a2618"),
        SEG_UNSEL=("#d8c398", "#4a3627"),
        SEG_UNSEL_HOVER=("#ccb487", "#58412f"),
        SEG_TEXT=("#2a1d14", "#efe2c4"),
        ACCENT_TEXT=("#8a5a10", "#d8a64a"),
        FOOTER_TEXT=("#2a1d14", "#efe2c4"),
        ENTRY_BORDER=2,
        CARD_BORDER=2,
        HUD=False,
        SHARP=False,
        SOFT=False,
        FONT="Georgia",  # fonte serifada clássica que já vem no Windows
    ),
    "arcade": dict(
        BG=("#f4f1e6", "#0b0b1a"),
        CARD=("#ffffff", "#14142b"),
        CARD_2=("#e6e0cc", "#1f1f3d"),
        CARD_2_HOVER=("#d9d1b8", "#2a2a52"),
        LINE=("#1a1a2e", "#2de2e6"),
        ACCENT="#ff3d6e",
        ACCENT_HOVER="#e0245a",
        ON_ACCENT="#ffffff",
        DANGER="#ff8c1a",
        DANGER_HOVER="#e07410",
        MUTED=("#5a5670", "#9a9ac8"),
        SUCCESS=("#1f9e4f", "#4ce67a"),
        TEXT=("#1a1a2e", "#f0f0ff"),
        TEXT_SOFT=("#2e2e48", "#d0d0f0"),
        WARN=("#b07800", "#ffd60a"),
        ERROR=("#d02050", "#ff6e94"),
        BANNER_BG=("#fff1c2", "#2a1f00"),
        BANNER_TEXT=("#6a4a00", "#ffd60a"),
        REMOVE_HOVER=("#ffd6e0", "#3a1424"),
        SEG_UNSEL=("#e6e0cc", "#1f1f3d"),
        SEG_UNSEL_HOVER=("#d9d1b8", "#2a2a52"),
        SEG_TEXT=("#1a1a2e", "#f0f0ff"),
        ACCENT_TEXT=("#d02050", "#2de2e6"),
        FOOTER_TEXT=("#1a1a2e", "#f0f0ff"),
        ENTRY_BORDER=2,
        CARD_BORDER=2,
        HUD=False,
        SHARP=True,
        SOFT=False,
        FONT="VT323",  # fonte de pixels (vem junto com o programa, pasta "fontes")
        FONT_FILE="VT323-Regular.ttf",
        FONT_FALLBACK="Consolas",
        FONT_SCALE=1.35,  # a VT323 é pequena: aumenta todos os textos
    ),
    "rpg": dict(
        BG=("#f3e9d2", "#10151e"),
        CARD=("#fbf5e6", "#1a212b"),
        CARD_2=("#ece0c2", "#252e3a"),
        CARD_2_HOVER=("#e2d3ae", "#2f3a48"),
        LINE=("#b08d3e", "#8a6d3b"),
        ACCENT="#a32b2b",
        ACCENT_HOVER="#871f22",
        ON_ACCENT="#f6e2a8",
        DANGER="#5b6472",
        DANGER_HOVER="#4a525e",
        MUTED=("#6e5d44", "#a99f8c"),
        SUCCESS=("#2f7a4f", "#5fc48c"),
        TEXT=("#2b2117", "#efe6d2"),
        TEXT_SOFT=("#4a3c2a", "#d8cdb5"),
        WARN=("#8a5a10", "#e0b04a"),
        ERROR=("#a32b2b", "#ef8a7a"),
        BANNER_BG=("#efe0b8", "#2a2412"),
        BANNER_TEXT=("#5a3a08", "#e0c070"),
        REMOVE_HOVER=("#f0d0c8", "#3a1c1c"),
        SEG_UNSEL=("#e2d3ae", "#252e3a"),
        SEG_UNSEL_HOVER=("#d8c79c", "#2f3a48"),
        SEG_TEXT=("#2b2117", "#efe6d2"),
        ACCENT_TEXT=("#8a2020", "#e0c070"),
        FOOTER_TEXT=("#2b2117", "#e0c070"),
        ENTRY_BORDER=1,
        CARD_BORDER=2,
        HUD=False,
        SHARP=False,
        SOFT=True,
        FONT="Palatino Linotype",  # serifada elegante que já vem no Windows
    ),
}
STYLE_LABELS = {"Clássico": "classico", "Cyberpunk": "cyberpunk", "Retrô": "retro", "Steampunk": "steampunk",
                "Arcade 8-bit": "arcade", "Fantasia / RPG": "rpg"}
DEFAULT_STYLE = "classico"
UI_STYLE = DEFAULT_STYLE


STYLE_DEFAULTS = dict(FONT_FILE=None, FONT_FALLBACK=None, FONT_SCALE=1.0)


def fonts_dir():
    """Pasta das fontes que vêm com o programa (dentro do executável ou ao lado do app.py)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fontes")


def load_style_font():
    """Carrega a fonte própria do estilo (só para este programa). Devolve o nome a usar."""
    if not FONT_FILE:
        return FONT
    try:
        if ctk.FontManager.load_font(os.path.join(fonts_dir(), FONT_FILE)):
            return FONT
    except Exception:  # noqa: BLE001
        pass
    return FONT_FALLBACK or FONT


_BaseCTkFont = ctk.CTkFont
_THEME_FONT = {}


class ScaledFont(_BaseCTkFont):
    """CTkFont que aumenta o tamanho conforme o estilo (fontes de pixel são menores)."""

    def __init__(self, *args, size=None, **kwargs):
        if size is not None and FONT_SCALE != 1.0:
            size = int(round(size * FONT_SCALE))
        super().__init__(*args, size=size, **kwargs)


def apply_style(name):
    """Define as cores/formas globais do estilo escolhido. Chamar antes de criar a janela."""
    global UI_STYLE, FONT
    UI_STYLE = name if name in STYLES else DEFAULT_STYLE
    globals().update(STYLE_DEFAULTS)
    globals().update(STYLES[UI_STYLE])
    arte.set_style(UI_STYLE)
    FONT = load_style_font()
    ctk.CTkFont = ScaledFont if FONT_SCALE != 1.0 else _BaseCTkFont
    try:
        th = ctk.ThemeManager.theme
        base = _THEME_FONT.setdefault("base", dict(th["CTkFont"]))  # tamanho/fonte originais
        th["CTkFont"]["size"] = int(round(base.get("size", 13) * FONT_SCALE))
        th["CTkFont"]["family"] = FONT or base.get("family")
        th["CTkButton"]["text_color"] = [ON_ACCENT, ON_ACCENT]
        th["CTkButton"]["fg_color"] = [ACCENT, ACCENT]
        th["CTkButton"]["hover_color"] = [ACCENT_HOVER, ACCENT_HOVER]
        th["CTkCheckBox"]["fg_color"] = [ACCENT, ACCENT]
        th["CTkSwitch"]["progress_color"] = [ACCENT, ACCENT]
        th["CTkEntry"]["border_color"] = list(LINE)
    except Exception:  # noqa: BLE001
        pass


def R(n):
    """Raio dos cantos: o do clássico, quase reto no cyberpunk, suave no retrô."""
    if SHARP:
        return 2
    if SOFT:
        return min(n, 6)
    return n


apply_style(DEFAULT_STYLE)

APPEARANCE = {"light": "Light", "dark": "Dark", "system": "System"}
THEME_LABELS = {"Claro": "light", "Escuro": "dark", "Sistema": "system"}

APP_VERSION = "1.7.0"  # manter igual ao MyAppVersion do installer.iss
THUMB_W, THUMB_H = 320, 180

APP_DIR = os.path.dirname(
    sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
)

TOOLS_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "BaixadorDeVideos", "tools"
)
DENO_URL = (
    "https://github.com/denoland/deno/releases/latest/download/"
    "deno-x86_64-pc-windows-msvc.zip"
)
FFMPEG_URLS = [
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/latest/download/"
    "ffmpeg-master-latest-win64-gpl.zip",
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
]

SEARCH_SOURCES = {
    "YouTube": "ytsearch",
    "YouTube (recentes)": "ytsearchdate",
    "SoundCloud (áudio)": "scsearch",
}
SEARCH_LIMIT = 15

HISTORY_PATH = os.path.join(os.path.dirname(TOOLS_DIR), "historico.json")
THUMBS_DIR = os.path.join(os.path.dirname(TOOLS_DIR), "thumbs")
HISTORY_MAX = 500

# Integração com o navegador (extensão -> programa, só dentro do próprio computador)
BRIDGE_PORT = 47653
ALLOWED_ORIGIN_PREFIXES = ("chrome-extension://", "moz-extension://")
SUGGEST_MIN_GAP = 20        # segundos entre duas sugestões
SUGGEST_REPEAT = 3600       # não repete a sugestão do mesmo vídeo por 1 hora
TOAST_SECONDS = 15
LOG_PATH = os.path.join(os.path.dirname(TOOLS_DIR), "erros.log")
# Qualidade do botão "Baixar" do aviso do navegador (padrão: até 1080p, MP4 compatível)
QUICK_CHOICES = {"Até 1080p (recomendado)": "1080p", "Até 720p": "720p",
                 "Até 480p": "480p", "Melhor disponível": "best"}
HISTORY_PAGE = 30
SMALL_W, SMALL_H = 128, 72

COOKIE_AUTO = "Automático"
COOKIE_NONE = "Não usar"
COOKIE_FILE = "Arquivo cookies.txt..."
COOKIE_CHOICES = [COOKIE_AUTO, "Edge", "Chrome", "Firefox", "Brave", "Opera",
                  COOKIE_FILE, COOKIE_NONE]
BROWSER_ORDER = ["edge", "chrome", "firefox", "brave", "opera"]  # Edge primeiro
BROWSER_NAMES = {"edge": "Edge", "chrome": "Chrome", "firefox": "Firefox",
                 "brave": "Brave", "opera": "Opera"}
BROWSER_EXE = {"edge": "msedge.exe", "chrome": "chrome.exe", "firefox": "firefox.exe",
               "brave": "brave.exe", "opera": "opera.exe"}
SETTINGS_PATH = os.path.join(os.path.dirname(TOOLS_DIR), "config.json")
EXT_URL = "https://chrome.google.com/webstore/detail/cclelndahbckbenkjhflpdbgdldlbecc"
FIREFOX_URL = "https://www.mozilla.org/firefox/new/"
BROWSER_STATE = {
    "edge": ("LOCALAPPDATA", r"Microsoft\Edge\User Data\Local State"),
    "chrome": ("LOCALAPPDATA", r"Google\Chrome\User Data\Local State"),
    "brave": ("LOCALAPPDATA", r"BraveSoftware\Brave-Browser\User Data\Local State"),
    "opera": ("APPDATA", r"Opera Software\Opera Stable\Local State"),
}

PROTECTED_TEXT = (
    "O Edge e o Chrome protegem o login (cookies) com uma trava do próprio navegador, "
    "e nenhum programa externo consegue ler. Isso não é defeito do app.\n\n"
    "Solução rápida (1 minuto) com um arquivo cookies.txt:\n"
    "1. Instale a extensão \"Get cookies.txt LOCALLY\" no Edge (botão 1).\n"
    "2. Abra o youtube.com no Edge, logado na conta que pode ver o vídeo. Se puder, "
    "use uma janela InPrivate (permita a extensão nela): o login dura mais.\n"
    "3. Clique na extensão, depois em Export, e salve o arquivo.\n"
    "4. Clique no botão 2 e escolha o arquivo salvo.\n\n"
    "Alternativa: entrar no YouTube pelo Firefox, que o app consegue ler direto (botão 3)."
)
LOGIN_TEXT = (
    "O YouTube exige login para este vídeo (restrição de idade). Entre no YouTube, no "
    "navegador escolhido no campo Login do navegador, com uma conta que possa ver esse "
    "vídeo (maior de idade e com a idade confirmada).\n\n"
    "Se preferir, use um arquivo cookies.txt exportado do navegador (botões abaixo)."
)

COOKIE_FILE_HELP = (
    "Não foi possível ler o login do navegador (ele usa uma proteção nos cookies "
    "que o app não consegue abrir).\n\n"
    "Solução: exporte um arquivo cookies.txt do YouTube com uma extensão de "
    "navegador (por exemplo \"Get cookies.txt LOCALLY\") e escolha "
    "\"Arquivo cookies.txt...\" em Login do navegador."
)

ANSI_RE = re.compile(r"(?:\x1b)?\[[0-9;]*m")

LOGIN_HELP = (
    "Este vídeo tem restrição de idade (ou exige login) e o YouTube só libera "
    "para quem está logado.\n\n"
    "Como resolver:\n"
    "1) Entre no YouTube, com uma conta que possa ver o vídeo, no Firefox "
    "(é o mais confiável) e tente de novo.\n"
    "2) No Chrome/Edge, feche o navegador antes de tentar.\n"
    "3) Ou exporte um arquivo cookies.txt e escolha \"Arquivo cookies.txt...\" "
    "em Login do navegador."
)

LABEL_BEST = "Melhor qualidade disponível"
LABEL_AUDIO = "Somente áudio (MP3)"


def ffmpeg_works(exe):
    """Confere se o ffmpeg executa de verdade (arquivo corrompido/bloqueado falha aqui)."""
    try:
        r = subprocess.run(
            [exe, "-version"], capture_output=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def ffmpeg_location():
    """Procura um ffmpeg que funcione: ao lado do app, na pasta de componentes, no PATH
    ou o embutido (imageio-ffmpeg)."""
    candidates = []
    for base in (APP_DIR, TOOLS_DIR):
        exe = os.path.join(base, "ffmpeg.exe")
        if os.path.exists(exe):
            candidates.append(exe)
    found = shutil.which("ffmpeg")
    if found:
        candidates.append(found)
    for exe in candidates:
        if ffmpeg_works(exe):
            return os.path.dirname(exe)
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        os.makedirs(TOOLS_DIR, exist_ok=True)
        target = os.path.join(TOOLS_DIR, "ffmpeg.exe")
        if not os.path.exists(target) or not ffmpeg_works(target):
            shutil.copy2(exe, target)
        if ffmpeg_works(target):
            return TOOLS_DIR
    except Exception:  # noqa: BLE001
        pass
    return None


def ensure_ffmpeg_on_path(ffdir):
    """Coloca a pasta do FFmpeg no PATH do programa. Algumas partes do yt-dlp (como o
    download de só um trecho) só procuram o FFmpeg no PATH e ignoram o ffmpeg_location."""
    if not ffdir:
        return ffdir
    folder = ffdir if os.path.isdir(ffdir) else os.path.dirname(ffdir)
    parts = os.environ.get("PATH", "").split(os.pathsep)
    if not any(os.path.normcase(p) == os.path.normcase(folder) for p in parts if p):
        os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
    return ffdir


MPV_DLL_NAMES = ("libmpv-2.dll", "mpv-2.dll", "mpv-1.dll")
MPV_RELEASES_API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mp3", ".m4a", ".opus",
              ".ogg", ".wav", ".flac", ".aac")
_mpv_module = None


def mpv_dir():
    """Pasta onde está o libmpv (o motor do player), ou None."""
    for base in (APP_DIR, TOOLS_DIR):
        for name in MPV_DLL_NAMES:
            if os.path.exists(os.path.join(base, name)):
                return base
    return None


def load_mpv():
    """Carrega o python-mpv usando o libmpv encontrado. Retorna o módulo ou None."""
    global _mpv_module
    if _mpv_module is not None:
        return _mpv_module
    folder = mpv_dir()
    if folder is None:
        return None
    os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(folder)
    except Exception:  # noqa: BLE001
        pass
    try:
        import mpv  # python-mpv

        _mpv_module = mpv
    except Exception:  # noqa: BLE001
        return None
    return _mpv_module


def download_mpv(progress=None):
    """Baixa o libmpv (compilação oficial de shinchiro) para a pasta de componentes."""
    req = urllib.request.Request(MPV_RELEASES_API, headers={
        "User-Agent": "BaixadorDeVideos", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    url = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.startswith("mpv-dev-x86_64-") and "-v3-" not in name and name.endswith(".7z"):
            url = asset.get("browser_download_url")
            break
    if not url:
        raise RuntimeError("Componente do player não encontrado para download.")
    import py7zr

    tmp = tempfile.mkdtemp(prefix="bdv_mpv_")
    try:
        archive = os.path.join(tmp, "mpv.7z")
        download_file(url, archive, progress)
        out = os.path.join(tmp, "x")
        with py7zr.SevenZipFile(archive, "r") as z:
            z.extractall(path=out)
        found = None
        for root, _dirs, files in os.walk(out):
            for f in files:
                if f.lower() in MPV_DLL_NAMES:
                    found = os.path.join(root, f)
                    break
            if found:
                break
        if not found:
            raise RuntimeError("libmpv não encontrado no arquivo baixado.")
        os.makedirs(TOOLS_DIR, exist_ok=True)
        shutil.copy2(found, os.path.join(TOOLS_DIR, os.path.basename(found)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


GITHUB_REPO = "LagazYT/baixador-de-videos"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
UPDATE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SETUP_ASSET = "BaixadorDeVideos_Setup.exe"
UPDATE_CHECK_EVERY = 12 * 3600  # segundos


def version_tuple(v):
    nums = re.findall(r"\d+", str(v or ""))
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(remote, local):
    a, b = list(version_tuple(remote)), list(version_tuple(local))
    n = max(len(a), len(b))
    return a + [0] * (n - len(a)) > b + [0] * (n - len(b))


def fetch_latest_release():
    """Consulta a última versão publicada no GitHub. Retorna um dicionário."""
    req = urllib.request.Request(UPDATE_API, headers={
        "User-Agent": f"BaixadorDeVideos/{APP_VERSION}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    version = str(data.get("tag_name", "")).lstrip("vV")
    asset = None
    for a in data.get("assets", []):
        if a.get("name") == SETUP_ASSET:
            asset = a
            break
    notes = str(data.get("body") or "")
    marker = notes.find("## Novidades")
    if marker >= 0:
        notes = notes[marker:]
    return {
        "version": version,
        "page": data.get("html_url") or RELEASES_PAGE,
        "notes": notes.strip()[:900],
        "url": (asset or {}).get("browser_download_url", ""),
        "size": int((asset or {}).get("size") or 0),
        "digest": str((asset or {}).get("digest") or ""),
    }


def installed_with_setup():
    """O programa foi instalado pelo instalador (pode se atualizar sozinho)?"""
    return getattr(sys, "frozen", False) and os.path.exists(os.path.join(APP_DIR, "unins000.exe"))


def download_update(info, progress=None):
    """Baixa o instalador novo e confere tamanho e SHA-256. Retorna o caminho."""
    url = info.get("url", "")
    prefix = f"https://github.com/{GITHUB_REPO}/releases/download/"
    if not url.startswith(prefix):
        raise RuntimeError("Endereço de atualização inesperado.")
    folder = os.path.join(tempfile.gettempdir(), "BaixadorDeVideos-update")
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, f"BaixadorDeVideos_Setup_{info.get('version', 'novo')}.exe")
    download_file(url, dest, progress)
    size = os.path.getsize(dest)
    if info.get("size") and size != info["size"]:
        raise RuntimeError("O download da atualização veio incompleto. Tente de novo.")
    digest = info.get("digest", "")
    if digest.startswith("sha256:"):
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest().lower() != digest.split(":", 1)[1].lower():
            os.remove(dest)
            raise RuntimeError("O arquivo baixado não confere com o publicado. Tente de novo.")
    return dest


def fmt_clock(seconds):
    if seconds is None or seconds != seconds or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def find_deno():
    for base in (APP_DIR, TOOLS_DIR):
        path = os.path.join(base, "deno.exe")
        if os.path.exists(path):
            return path
    return shutil.which("deno")


def js_runtime_opts():
    """O YouTube exige um runtime JavaScript (Deno ou Node) para liberar os formatos."""
    opts = {}
    try:
        import yt_dlp_ejs  # noqa: F401
    except ImportError:
        opts["remote_components"] = ["ejs:github"]  # baixa os scripts sob demanda

    deno = find_deno()
    if deno:
        if not shutil.which("deno"):
            opts["js_runtimes"] = {"deno": {"path": deno}}
        return opts, True
    if shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
        return opts, True
    return opts, False


def download_file(url, dest, progress=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)


def extract_members(zip_path, names, dest_dir):
    """Extrai arquivos (por nome) de dentro de um .zip para dest_dir."""
    found = set()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            base = os.path.basename(info.filename).lower()
            if base in names and not info.is_dir():
                target = os.path.join(dest_dir, base)
                with zf.open(info) as src, open(target + ".part", "wb") as out:
                    shutil.copyfileobj(src, out)
                os.replace(target + ".part", target)
                found.add(base)
    if names[0] not in found:
        raise RuntimeError(f"{names[0]} não encontrado no arquivo baixado.")


class QuietLogger:
    """Evita escrever no console (que não existe no .exe sem janela)."""

    def __init__(self):
        self.last_error = ""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.last_error = clean_msg(msg)


def clean_msg(msg):
    """Remove os códigos de cor (ANSI) que o yt-dlp coloca nas mensagens."""
    return ANSI_RE.sub("", str(msg)).strip()


def needs_login(msg):
    m = str(msg).lower()
    return any(k in m for k in (
        "confirm your age", "sign in to confirm", "age-restricted",
        "age restricted", "cookies-from-browser", "login required",
    ))


def pick_quality(wanted, options):
    """Escolhe, entre as opções do vídeo, a qualidade pedida (ou a maior abaixo dela)."""
    if wanted in options:
        return wanted
    m = re.fullmatch(r"(\d+)p", wanted or "")
    if m:
        target = int(m.group(1))
        below = [int(o[:-1]) for o in options
                 if re.fullmatch(r"\d+p", o) and int(o[:-1]) <= target]
        if below:
            return f"{max(below)}p"
    return LABEL_BEST


def is_postprocess_error(msg):
    m = str(msg).lower()
    return any(k in m for k in ("postprocessing", "conversion failed", "ffmpeg", "ffprobe"))


def tail_text(lines, n=6, limit=500):
    """Últimas linhas úteis de uma lista de mensagens (para mostrar o motivo real do erro)."""
    flat = [l.strip() for l in "\n".join(map(str, lines)).splitlines() if l.strip()]
    return "\n".join(flat[-n:])[-limit:]


def log_error(url, msg, detail=""):
    """Guarda o erro em erros.log (ajuda a descobrir o motivo se acontecer de novo)."""
    try:
        path = LOG_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and os.path.getsize(path) > 200_000:
            os.remove(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] {url}\n{msg}\n{detail}\n{'-' * 40}\n")
    except Exception:  # noqa: BLE001
        pass


def is_cookie_locked(msg):
    m = str(msg).lower()
    return "could not copy" in m and "cookie database" in m


def is_decrypt_fail(msg):
    m = str(msg).lower()
    return any(k in m for k in (
        "failed to decrypt", "dpapi", "app-bound", "cannot decrypt", "unable to decrypt",
    ))


def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:  # noqa: BLE001
        pass


def browser_protected(browser):
    """True se o navegador usa a proteção 'app-bound' nos cookies (o yt-dlp não lê)."""
    if browser in load_settings().get("broken_browsers", []):
        return True
    spec = BROWSER_STATE.get(browser)
    base = os.environ.get(spec[0]) if spec else None
    if not base:
        return False
    try:
        with open(os.path.join(base, spec[1]), encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("os_crypt", {}).get("app_bound_encrypted_key"))
    except Exception:  # noqa: BLE001
        return False


def mark_broken(browser):
    cfg = load_settings()
    broken = set(cfg.get("broken_browsers", []))
    broken.add(browser)
    cfg["broken_browsers"] = sorted(broken)
    save_settings(cfg)


def firefox_available():
    appdata = os.environ.get("APPDATA")
    return bool(appdata) and os.path.isdir(
        os.path.join(appdata, "Mozilla", "Firefox", "Profiles")
    )


def load_history():
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def save_history(items):
    try:
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        tmp = HISTORY_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, HISTORY_PATH)
    except Exception:  # noqa: BLE001
        pass


def update_settings(**kwargs):
    cfg = load_settings()
    cfg.update(kwargs)
    save_settings(cfg)


def norm_url(url):
    """Forma simples de comparar endereços (ignora #, utm_*, www etc.)."""
    try:
        u = urlparse(url)
    except Exception:  # noqa: BLE001
        return url
    host = (u.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in ("youtube.com", "m.youtube.com", "music.youtube.com") and u.path == "/watch":
        return "youtube:" + dict(parse_qsl(u.query)).get("v", "")
    if host == "youtu.be":
        return "youtube:" + u.path.strip("/")
    drop = ("fbclid", "gclid", "si", "feature")
    q = [(k, v) for k, v in parse_qsl(u.query)
         if not k.lower().startswith("utm_") and k.lower() not in drop]
    return urlunparse((u.scheme, host, u.path.rstrip("/"), "", urlencode(q), ""))


def make_bridge_handler(app):
    """Servidor local que recebe os avisos da extensão do navegador."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "BaixadorBridge/1.0"

        def log_message(self, *args):
            pass

        def _trusted(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            origin = self.headers.get("Origin") or ""
            return host in ("127.0.0.1", "localhost") and origin.startswith(
                ALLOWED_ORIGIN_PREFIXES
            )

        def _send(self, code, obj=None):
            body = b"" if obj is None else json.dumps(obj).encode("utf-8")
            self.send_response(code)
            origin = self.headers.get("Origin")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_OPTIONS(self):
            if not self._trusted():
                self._send(403, {"ok": False})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin"))
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if not self._trusted():
                self._send(403, {"ok": False})
                return
            if self.path.split("?")[0] == "/ping":
                app.bridge_last_seen = time.time()
                self._send(200, {"ok": True, "app": "BaixadorDeVideos",
                                 "version": APP_VERSION, "enabled": app.suggest_enabled})
            else:
                self._send(404, {"ok": False})

        def do_POST(self):
            if not self._trusted():
                self._send(403, {"ok": False})
                return
            if self.path.split("?")[0] != "/video":
                self._send(404, {"ok": False})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length > 20000:
                    raise ValueError("grande demais")
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                url = str(data.get("url") or "")
                if not url.startswith(("http://", "https://")) or len(url) > 2000:
                    raise ValueError("endereço inválido")
            except Exception:  # noqa: BLE001
                self._send(400, {"ok": False})
                return
            app.bridge_last_seen = time.time()
            app.events.put(("browser_video", data))
            self._send(200, {"ok": True, "enabled": app.suggest_enabled})

    return Handler


class BridgeServer:
    def __init__(self, app, port=None):
        self.app = app
        self.port = port or BRIDGE_PORT
        self.httpd = None

    def start(self):
        self.httpd = ThreadingHTTPServer(
            ("127.0.0.1", self.port), make_bridge_handler(self.app)
        )
        self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:  # noqa: BLE001
                pass
            self.httpd = None


def quality_text(h):
    q = h.get("quality") or ""
    if q == LABEL_AUDIO:
        txt = "MP3"
    elif q == LABEL_BEST:
        txt = f"Melhor ({h['height']}p)" if h.get("height") else "Melhor qualidade"
    else:
        txt = q
    extras = []
    if h.get("compat"):
        extras.append("H.264")
    sec = h.get("section")
    if sec:
        extras.append("✂ " + section_text(sec))
    if h.get("subs"):
        extras.append("Legenda: " + h["subs"])
    return "  •  ".join([txt] + extras)


# ---------- Opções do download (H.264, legendas, trecho) ----------
H264_FILTER = "[vcodec~='^(avc|h264)']"
# conversão para H.264 + AAC em MP4 (abre no Premiere, Vegas, CapCut, celulares...)
RECODE_ARGS = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
SUBS_NONE = "Sem legendas"
NOTE_FALLBACK = "formato ajustado para compatibilidade"
NOTE_NO_RECODE = "sem converter para H.264: a conversão falhou"
NOTE_NO_SUBS = "sem legenda: não foi possível baixá-la"
LANG_NAMES = {
    "pt": "Português", "pt-BR": "Português (Brasil)", "pt-PT": "Português (Portugal)",
    "en": "Inglês", "en-US": "Inglês (EUA)", "en-GB": "Inglês (Reino Unido)",
    "es": "Espanhol", "es-419": "Espanhol (América Latina)", "es-ES": "Espanhol (Espanha)",
    "fr": "Francês", "de": "Alemão", "it": "Italiano", "ja": "Japonês", "ko": "Coreano",
    "zh": "Chinês", "zh-Hans": "Chinês (simplificado)", "zh-Hant": "Chinês (tradicional)",
    "ru": "Russo", "ar": "Árabe", "hi": "Hindi", "tr": "Turco", "pl": "Polonês",
    "nl": "Holandês", "id": "Indonésio", "vi": "Vietnamita", "th": "Tailandês",
}


def lang_name(code):
    code = code or ""
    return LANG_NAMES.get(code) or LANG_NAMES.get(code.split("-")[0]) or code


def subtitle_options(info):
    """Legendas do vídeo: [(rótulo, idioma, automática)]. Legendas feitas pelo canal vêm
    primeiro; das automáticas, só o idioma original, português e inglês (o YouTube oferece
    traduções automáticas para dezenas de idiomas)."""
    out, seen = [], set()

    def name_of(entries, code):
        if lang_name(code) != code:  # nome em português quando conhecemos o idioma
            return lang_name(code)
        for e in entries or []:
            if e.get("name"):
                return str(e["name"])
        return code

    manual = info.get("subtitles") or {}
    for code in sorted(manual, key=lambda c: (not c.startswith("pt"), c)):
        if code in ("live_chat", "rechat") or not manual[code]:
            continue
        out.append((name_of(manual[code], code), code, False))
        seen.add(code.split("-")[0])
    auto = info.get("automatic_captions") or {}
    picks = [c for c in auto if c.endswith("-orig")][:1]
    picks += [c for c in ("pt-BR", "pt", "en") if c in auto]
    for code in picks:
        base = code.replace("-orig", "").split("-")[0]
        if base in seen or not auto[code]:
            continue
        seen.add(base)
        label = name_of(auto[code], code.replace("-orig", "")).replace(" (Original)", "")
        out.append((f"{label} (automática)", code, True))
    labels = set()
    unique = []
    for label, code, is_auto in out:  # rótulos repetidos ganham o código do idioma
        if label in labels:
            label = f"{label} [{code}]"
        labels.add(label)
        unique.append((label, code, is_auto))
    return unique


def h264_heights(info):
    """Alturas com vídeo H.264 e se o site informa os codecs."""
    found, known = set(), False
    for f in info.get("formats") or []:
        v = f.get("vcodec")
        if v and v != "none":
            known = True
            if f.get("height") and re.match(r"(avc|h264)", v):
                found.add(f["height"])
    return found, known


def compat_plan(compat, choice, heights, h264set, known):
    """Como entregar o vídeo em H.264: ("off"|"h264"|"recode"|"pref", altura)."""
    if not compat or choice == LABEL_AUDIO:
        return "off", None
    if not known:
        return "pref", None
    if choice == LABEL_BEST:
        # "Melhor qualidade" = melhor versão que já existe em H.264 (sem conversão demorada)
        if h264set:
            return "h264", max(h264set)
        return "recode", max(heights) if heights else None
    m = re.match(r"(\d+)p", choice or "")
    h = int(m.group(1)) if m else None
    if h and h in h264set:
        return "h264", h
    return "recode", h


def parse_clock(text):
    """'2:15', '1:02:05', '135' ou '2:15.5' -> segundos (None se inválido)."""
    t = (text or "").strip().replace(",", ".")
    if not t:
        return None
    parts = t.split(":")
    if len(parts) > 3:
        return None
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums) or any(n >= 60 for n in nums[1:]):
        return None
    total = 0.0
    for n in nums:
        total = total * 60 + n
    return total


def clock_text(seconds):
    """Tempo legível para o trecho: 2:15, 1:02:05 ou 2:15.5."""
    seconds = max(0.0, float(seconds or 0))
    whole = int(seconds)
    frac = seconds - whole
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    txt = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    if frac >= 0.05:
        txt += f".{int(round(frac * 10)) % 10}"
    return txt


def section_text(sec):
    return f"{clock_text(sec.get('start'))} a {clock_text(sec.get('end'))}"


def section_tag(sec):
    """Pedaço do nome do arquivo: 'trecho 2m15s-3m40s'."""
    def one(v):
        v = int(v or 0)
        h, rem = divmod(v, 3600)
        m, s = divmod(rem, 60)
        return (f"{h}h" if h else "") + f"{m}m{s:02d}s"
    return f"trecho {one(sec.get('start'))}-{one(sec.get('end'))}"


def build_download_opts(choice, folder, ffmpeg, mode="off", height=None, sub=None,
                        section=None):
    """Monta as opções do yt-dlp para um download.
    sub = (idioma, automática) ou None; section = {"start", "end", "exact"} ou None."""
    has_ff = ffmpeg is not None
    name = "%(title).150B [%(id)s]"
    if section:
        name += f" ({section_tag(section)})"
    opts = {
        "outtmpl": os.path.join(folder, name + ".%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "no_color": True,
    }
    if has_ff:
        opts["ffmpeg_location"] = ffmpeg
    pps = []
    audio = choice == LABEL_AUDIO
    if audio:
        if has_ff:
            opts["format"] = "bestaudio/best"
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                        "preferredquality": "192"})
        else:
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        if choice == LABEL_BEST:
            fmt = "bv*+ba/b/best" if has_ff else "b/best"
            hc = ""
        else:
            h = int(choice.replace("p", "").split()[0])
            hc = f"[height<={h}]"
            fmt = (f"bv*{hc}+ba/b{hc}/bv*+ba/b/best" if has_ff else f"b{hc}/b/best")
        if has_ff:
            opts["merge_output_format"] = "mp4"
            # na mesma resolução, prefere MP4/AAC (toca em qualquer aparelho)
            opts["format_sort"] = ["res", "ext:mp4:m4a"]
            if mode == "h264":
                hh = f"[height<={height}]" if height else hc
                fmt = (f"bv*{H264_FILTER}{hh}+ba[acodec^=mp4a]/bv*{H264_FILTER}{hh}+ba/"
                       f"b{H264_FILTER}{hh}/" + fmt)
            elif mode == "pref":
                opts["format_sort"] = ["vcodec:h264", "res", "acodec:aac", "ext:mp4:m4a"]
            elif mode == "recode":
                # junta em MKV (aceita qualquer codec) e converte para MP4 H.264
                opts["merge_output_format"] = "mkv"
                pps.append({"key": "FFmpegVideoConvertor", "preferedformat": "mp4"})
                opts["postprocessor_args"] = {"videoconvertor": list(RECODE_ARGS)}
        opts["format"] = fmt
    if sub and has_ff:
        code, is_auto = sub
        opts["writesubtitles"] = not is_auto
        opts["writeautomaticsub"] = bool(is_auto)
        opts["subtitleslangs"] = [code]
        opts["subtitlesformat"] = "srt/vtt/best"
        pps.insert(0, {"key": "FFmpegSubtitlesConvertor", "format": "srt", "when": "before_dl"})
        if not audio:  # embute no vídeo e mantém o .srt ao lado
            pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": True})
    if section and has_ff:
        opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(float(section["start"]), float(section["end"]))])
        # áudio é convertido de qualquer jeito: corta no ponto exato (sem custo extra visível)
        opts["force_keyframes_at_cuts"] = bool(section.get("exact")) or audio
    if pps:
        opts["postprocessors"] = pps
    return opts


def strip_subs(opts):
    """Mesmas opções, sem legendas."""
    out = {k: v for k, v in opts.items() if k not in (
        "writesubtitles", "writeautomaticsub", "subtitleslangs", "subtitlesformat")}
    pps = [p for p in opts.get("postprocessors") or []
           if p["key"] not in ("FFmpegSubtitlesConvertor", "FFmpegEmbedSubtitle")]
    out.pop("postprocessors", None)
    if pps:
        out["postprocessors"] = pps
    return out


def download_plans(opts, quality, mode="off"):
    """Receitas de download [(opções, nota)]: a pedida e, se a conversão falhar,
    alternativas mais seguras. A nota aparece no fim ("Concluído, ...")."""
    plans = [(dict(opts), None)]
    base = opts
    if mode == "recode":
        base = {k: v for k, v in opts.items() if k != "postprocessor_args"}
        pps = [p for p in opts.get("postprocessors") or [] if p["key"] != "FFmpegVideoConvertor"]
        base.pop("postprocessors", None)
        if pps:
            base["postprocessors"] = pps
        base["merge_output_format"] = "mp4"
        plans.append((dict(base), NOTE_NO_RECODE))
    if "merge_output_format" in base:
        m = re.search(r"(\d+)p", quality or "")
        hc = f"[height<={m.group(1)}]" if m else ""
        # mesmos arquivos, mas juntando em MKV (aceita qualquer codec)
        plans.append(({**base, "merge_output_format": "mkv"}, NOTE_FALLBACK))
        # só H.264 + AAC (juntam em MP4 em qualquer ffmpeg)
        plans.append(({**base, "format": (
            f"bv*[vcodec^=avc1]{hc}+ba[acodec^=mp4a]/bv*[ext=mp4]{hc}+ba[ext=m4a]"
            f"/b[ext=mp4]{hc}/b{hc}")}, NOTE_FALLBACK))
        # arquivo único, sem precisar juntar nada
        single = {k: v for k, v in base.items()
                  if k not in ("merge_output_format", "format_sort")}
        single["format"] = f"b{hc}/b"
        plans.append((single, NOTE_FALLBACK))
    elif any(p["key"] == "FFmpegExtractAudio" for p in opts.get("postprocessors") or []):
        # MP3: se a conversão falhar, mantém o áudio original
        single = {k: v for k, v in opts.items() if k != "postprocessors"}
        pps = [p for p in opts["postprocessors"] if p["key"] != "FFmpegExtractAudio"]
        if pps:
            single["postprocessors"] = pps
        single["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        plans.append((single, NOTE_FALLBACK))
    return plans


def ffmpeg_exe(ffmpeg):
    """Caminho do executável a partir do que ffmpeg_location() devolve (pasta ou arquivo)."""
    if ffmpeg and os.path.isdir(ffmpeg):
        return os.path.join(ffmpeg, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return ffmpeg


def unique_path(path):
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path = f"{base} ({n}){ext}"
        n += 1
    return path


def cut_section_file(ffmpeg, src, dest_dir, section):
    """Corta o trecho de um arquivo já baixado (plano B do "baixar só um trecho")."""
    stem, ext = os.path.splitext(os.path.basename(src))
    start = float(section["start"])
    dur = float(section["end"]) - start
    common = ["-ss", f"{start:.3f}", "-i", src, "-t", f"{dur:.3f}"]
    if ext.lower() == ".mp3":
        args = common + ["-map", "0:a", "-c", "copy"]
    elif section.get("exact"):
        ext = ".mp4"  # o corte exato recodifica em H.264 + AAC
        args = common + ["-map", "0:v?", "-map", "0:a?"] + RECODE_ARGS
    else:
        args = common + ["-map", "0:v?", "-map", "0:a?", "-c", "copy"]
        if ext.lower() in (".mp4", ".m4a", ".mov"):
            args += ["-movflags", "+faststart"]
    dest = unique_path(os.path.join(dest_dir, f"{stem} ({section_tag(section)}){ext}"))
    r = subprocess.run(
        [ffmpeg_exe(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", *args, dest],
        capture_output=True, text=True, errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if r.returncode != 0 or not os.path.exists(dest) or os.path.getsize(dest) == 0:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise RuntimeError("Não foi possível cortar o trecho: " + (r.stderr or "").strip()[-300:])
    return dest


def first_real_error(attempts):
    """A primeira falha que explica o problema (as receitas de reserva costumam terminar
    em "formato indisponível", o que esconde a causa real)."""
    for m in attempts:
        if "format is not available" not in m and "Requested format" not in m:
            return m
    return attempts[-1] if attempts else ""


def is_subtitle_error(msg):
    m = str(msg).lower()
    return "subtitle" in m and ("unable to download" in m or "http error" in m or "429" in m)


def thumbnail_candidates(info):
    """Endereços das thumbnails, da melhor para a pior (a maior às vezes não existe)."""
    thumbs = [t for t in (info.get("thumbnails") or []) if t.get("url")]
    thumbs.sort(key=lambda t: (t.get("preference") or 0, (t.get("width") or 0) * (t.get("height") or 0)),
                reverse=True)
    urls = []
    for u in [info.get("thumbnail")] + [t["url"] for t in thumbs]:
        if u and u.startswith("http") and u not in urls:
            urls.append(u)
    return urls[:4]


def best_thumbnail_url(info):
    urls = thumbnail_candidates(info)
    return urls[0] if urls else None


def save_thumbnail_file(urls, folder, title, vid):
    """Baixa a thumbnail em alta resolução e salva como JPG. Devolve (caminho, tamanho)."""
    if isinstance(urls, str):
        urls = [urls]
    last = None
    img = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            break
        except Exception as e:  # noqa: BLE001  (tenta a próxima)
            last = e
    if img is None:
        raise last or RuntimeError("Este vídeo não tem thumbnail.")
    safe = yt_dlp.utils.sanitize_filename(title or "thumbnail", restricted=False)
    safe = re.sub(r'[<>:"/\\|?*]', "_", safe).strip(" .")[:120] or "thumbnail"
    base = f"{safe} [{vid}] - thumbnail" if vid else f"{safe} - thumbnail"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, base + ".jpg")
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{base} ({n}).jpg")
        n += 1
    img.save(path, "JPEG", quality=95)
    return path, img.size


ISSUES_URL = "https://github.com/LagazYT/baixador-de-videos/issues/new"
PP_TEXT = {
    "Merger": "Juntando áudio e vídeo...",
    "VideoConvertor": "Convertendo para MP4 H.264... isso pode levar alguns minutos.",
    "EmbedSubtitle": "Colocando a legenda no vídeo...",
    "ExtractAudio": "Convertendo para MP3...",
}


def build_report(ffmpeg, has_js, extra=""):
    """Texto com as informações que ajudam a descobrir a causa de um problema."""
    import platform
    try:
        ver = yt_dlp.version.__version__
    except Exception:  # noqa: BLE001
        ver = "?"
    lines = [
        f"Baixador de Vídeos {APP_VERSION} (Windows)",
        f"Sistema: {platform.platform()}",
        f"yt-dlp: {ver}",
        f"FFmpeg: {'sim' if ffmpeg else 'não encontrado'}",
        f"Deno (YouTube): {'sim' if has_js else 'não encontrado'}",
        f"Estilo: {UI_STYLE}",
        f"Data: {datetime.now():%d/%m/%Y %H:%M}",
    ]
    if extra:
        lines += ["", "Último erro:", extra.strip()[:1500]]
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            log = f.read()[-4000:]
        if log.strip():
            lines += ["", "Registro de erros (mais recentes):", log.strip()]
    except OSError:
        pass
    text = "\n".join(lines)
    home = os.path.expanduser("~")
    if home and len(home) > 3:  # não expõe o nome de usuário do Windows
        text = text.replace(home, "%USERPROFILE%")
    return text


def fmt_bytes(n):
    if not n:
        return "--"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_duration(seconds):
    if not seconds:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fetch_thumbnail(info):
    """Baixa a miniatura do vídeo e devolve uma imagem PIL (ou None)."""
    url = info.get("thumbnail")
    if not url:
        thumbs = [t for t in info.get("thumbnails", []) if t.get("url")]
        if thumbs:
            url = thumbs[-1]["url"]
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return ImageOps.fit(img, (THUMB_W * 2, THUMB_H * 2))
    except Exception:  # noqa: BLE001
        return None


def fetch_image(url, size):
    """Baixa uma imagem qualquer e recorta para o tamanho pedido."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return ImageOps.fit(img, size)
    except Exception:  # noqa: BLE001
        return None


def pick_thumb(entry, prefix):
    thumbs = [t for t in (entry.get("thumbnails") or []) if t.get("url")]
    if thumbs:
        thumbs.sort(key=lambda t: t.get("width") or 0)
        for t in thumbs:
            if (t.get("width") or 0) >= 200:
                return t["url"]
        return thumbs[-1]["url"]
    if entry.get("thumbnail"):
        return entry["thumbnail"]
    if prefix.startswith("yt") and entry.get("id"):
        return f"https://i.ytimg.com/vi/{entry['id']}/mqdefault.jpg"
    return None


def fmt_views(n):
    if not n:
        return ""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mi de visualizações"
    if n >= 1_000:
        return f"{n / 1_000:.0f} mil visualizações"
    return f"{int(n)} visualizações"


class HelpDialog(ctk.CTkToplevel):
    """Janela de ajuda com botões de ação. buttons = [(texto, função, primário, fecha)]"""

    def __init__(self, master, title, message, detail, buttons, icon_path=None):
        super().__init__(master)
        self.title(title)
        self.configure(fg_color=CARD)
        self.resizable(False, False)
        self.transient(master)
        ctk.CTkLabel(
            self, text=title, anchor="w", justify="left", wraplength=520,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(22, 8))
        ctk.CTkLabel(
            self, text=message, anchor="w", justify="left", wraplength=520,
            text_color=TEXT_SOFT,
        ).pack(anchor="w", padx=24)
        if detail:
            ctk.CTkLabel(
                self, text="Detalhe técnico: " + detail, anchor="w", justify="left",
                wraplength=520, text_color=MUTED, font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=24, pady=(10, 0))
        for text, cmd, primary, close in buttons:
            ctk.CTkButton(
                self, text=text, height=40, corner_radius=R(10),
                fg_color=ACCENT if primary else CARD_2,
                hover_color=ACCENT_HOVER if primary else CARD_2_HOVER,
                text_color=ON_ACCENT if primary else TEXT,
                command=lambda c=cmd, cl=close: self._run(c, cl),
            ).pack(fill="x", padx=24, pady=(8, 0))
        ctk.CTkButton(
            self, text="Fechar", height=36, corner_radius=R(10), fg_color="transparent",
            hover_color=CARD_2, text_color=MUTED, command=self.destroy,
        ).pack(pady=(10, 16))

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + max(0, (master.winfo_height() - h) // 3)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        if icon_path:
            self.after(250, lambda: self._set_icon(icon_path))
        self.after(150, self._grab)

    def _set_icon(self, path):
        try:
            self.iconbitmap(path)
        except Exception:  # noqa: BLE001
            pass

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def _run(self, cmd, close):
        if close:
            self.destroy()
        cmd()


class SuggestionToast(ctk.CTkToplevel):
    """Aviso no canto da tela: 'Vídeo detectado no navegador' com botão para baixar."""

    KEY = "#010203"  # cor transparente (deixa os cantos arredondados)

    def __init__(self, master, p, image, already, on_download, on_choose, on_ignore,
                 on_closed, icon_path=None):
        super().__init__(master)
        self._closed = False
        self._on_closed = on_closed
        self._left = TOAST_SECONDS
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=self.KEY)
        try:
            self.attributes("-transparentcolor", self.KEY)
        except Exception:  # noqa: BLE001
            pass

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=R(16), border_width=2,
                            border_color=ACCENT, bg_color=self.KEY)
        card.pack(fill="both", expand=True)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(
            head, text="🎬  Vídeo detectado no navegador", text_color=ACCENT_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            head, text="✕", width=26, height=26, corner_radius=R(8), fg_color="transparent",
            hover_color=CARD_2, text_color=MUTED, command=self.close,
        ).pack(side="right")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(6, 0))
        ctk.CTkLabel(body, text="", image=image, width=SMALL_W, height=SMALL_H).pack(
            side="left")
        info = ctk.CTkFrame(body, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(12, 0))
        title = p.get("title") or "Vídeo"
        if len(title) > 80:
            title = title[:77] + "..."
        ctk.CTkLabel(
            info, text=title, anchor="w", justify="left", wraplength=215,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", fill="x")
        meta = "  •  ".join(x for x in (p.get("uploader") or "", p.get("duration") or "") if x)
        if meta:
            ctk.CTkLabel(
                info, text=meta, anchor="w", justify="left", wraplength=215,
                text_color=MUTED, font=ctk.CTkFont(size=11),
            ).pack(anchor="w", fill="x", pady=(2, 0))
        note = None
        if already:
            note = f"Você já baixou este vídeo em {already}"
        elif p.get("login"):
            note = "Pode exigir login (restrição de idade)"
        if note:
            ctk.CTkLabel(
                info, text=note, anchor="w", justify="left", wraplength=215,
                text_color=WARN, font=ctk.CTkFont(size=11),
            ).pack(anchor="w", fill="x", pady=(2, 0))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(10, 12))
        ctk.CTkButton(
            btns, text="↻ Baixar de novo" if already else "⬇ Baixar", width=120,
            height=34, corner_radius=R(10), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"), command=lambda: self._act(on_download),
        ).pack(side="left")
        ctk.CTkButton(
            btns, text="Qualidade...", width=96, height=34, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
            command=lambda: self._act(on_choose),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btns, text="Ignorar site", width=84, height=34, corner_radius=R(10),
            fg_color="transparent", hover_color=CARD_2, text_color=MUTED,
            font=ctk.CTkFont(size=12), command=lambda: self._act(on_ignore),
        ).pack(side="right")

        self.update_idletasks()
        w, h = max(self.winfo_reqwidth(), 400), self.winfo_reqheight()
        x = self.winfo_screenwidth() - w - 20
        y = self.winfo_screenheight() - h - 70  # acima da barra de tarefas
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.after(1000, self._tick)

    def _act(self, fn):
        self.close()
        fn()

    def _tick(self):
        if self._closed:
            return
        try:
            px, py = self.winfo_pointerxy()
            inside = (self.winfo_rootx() <= px <= self.winfo_rootx() + self.winfo_width()
                      and self.winfo_rooty() <= py <= self.winfo_rooty() + self.winfo_height())
        except Exception:  # noqa: BLE001
            inside = False
        if not inside:  # com o mouse em cima, o aviso fica parado
            self._left -= 1
        if self._left <= 0:
            self.close()
            return
        self.after(1000, self._tick)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except Exception:  # noqa: BLE001
            pass
        self._on_closed()


class App(ctk.CTk):
    def __init__(self):
        cfg0 = load_settings()
        self.appearance = cfg0.get("appearance", "dark")
        if self.appearance not in APPEARANCE:
            self.appearance = "dark"
        ctk.set_appearance_mode(APPEARANCE[self.appearance])
        super().__init__()
        self.title("Baixador de Vídeos")
        self.minimize_to_tray = bool(cfg0.get("minimize_to_tray", False)) and pystray is not None
        self.tray = None
        self._tray_notified = False
        self.suggest_enabled = bool(cfg0.get("suggest_downloads", True))
        self.quick_quality = cfg0.get("quick_quality", "1080p")
        if self.quick_quality not in QUICK_CHOICES.values():
            self.quick_quality = "1080p"
        self.ignored_hosts = list(cfg0.get("ignored_hosts", []))
        self.bridge = None
        self.bridge_last_seen = 0.0
        self._toast = None
        self._last_toast_time = 0.0
        self._suggested = {}
        self._probing = False
        self.update_info = None
        self.updating_app = False
        self._mpv_failed = False
        self.player = None
        self.player_fs = None
        self.player_fs_player = None
        self.player_item = None
        self._player_seeking = False
        self._pending_seek = None
        self._player_list_widgets = []
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.ico_path = None
        try:  # ícone personalizado de multimídia
            ico_dir = os.path.dirname(TOOLS_DIR)
            os.makedirs(ico_dir, exist_ok=True)
            ico = os.path.join(ico_dir, "icone.ico")
            arte.save_ico(ico)
            self.iconbitmap(ico)
            self.ico_path = ico
        except Exception:  # noqa: BLE001
            pass
        h = min(860, self.winfo_screenheight() - 90)
        self.geometry(f"780x{h}")
        self.minsize(720, 560)
        self.configure(fg_color=BG)

        self.ffmpeg = ensure_ffmpeg_on_path(ffmpeg_location())
        self.js_opts, self.has_js = js_runtime_opts()
        self.events = queue.Queue()
        self.cancel_flag = threading.Event()
        self.busy = False
        self.video_info = None

        self.url_var = ctk.StringVar()
        self.quality_var = ctk.StringVar(value="—")
        self.folder_var = ctk.StringVar(
            value=os.path.join(os.path.expanduser("~"), "Videos")
        )
        # opções do download (1.6): H.264, legendas e trecho
        self.compat_var = ctk.BooleanVar(value=bool(cfg0.get("compat_editors", False)))
        self.sub_var = ctk.StringVar(value=SUBS_NONE)
        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_start_var = ctk.StringVar(value="0:00")
        self.trim_end_var = ctk.StringVar(value="")
        self.trim_exact_var = ctk.BooleanVar(value=False)
        self._sub_map = {}
        self.video_heights = []
        self.h264_set = set()
        self.codec_known = False
        self.pending_section = None
        self.pending_compat = None
        self.pending_sub = None
        self.last_error_text = ""

        self._placeholder = ctk.CTkImage(
            light_image=arte.make_placeholder(THUMB_W * 2, THUMB_H * 2, light=True),
            dark_image=arte.make_placeholder(THUMB_W * 2, THUMB_H * 2),
            size=(THUMB_W, THUMB_H),
        )

        self._small_placeholder = ctk.CTkImage(
            light_image=arte.make_placeholder(SMALL_W * 2, SMALL_H * 2, light=True),
            dark_image=arte.make_placeholder(SMALL_W * 2, SMALL_H * 2),
            size=(SMALL_W, SMALL_H),
        )
        _btitle = "Baixador de Vídeos"
        _bsub = "Cole um link ou pesquise, escolha a qualidade e baixe."
        self._banner_img = ctk.CTkImage(
            light_image=arte.make_banner(732, 104, _btitle, _bsub, light=True),
            dark_image=arte.make_banner(732, 104, _btitle, _bsub),
            size=(732, 104),
        )
        self._footer_img = ctk.CTkImage(
            light_image=arte.make_footer(732, 36, light=True),
            dark_image=arte.make_footer(732, 36),
            size=(732, 36),
        )
        self._empty_art = ctk.CTkImage(
            light_image=arte.make_empty_art(1120, 400, light=True),
            dark_image=arte.make_empty_art(1120, 400),
            size=(560, 200),
        )
        self.auto_download = False
        self.pending_quality = None
        self.video_url = ""
        self._analyzing_url = ""
        self.current_thumb = None
        self.history = load_history()
        self._hist_widgets = []
        self._hist_limit = HISTORY_PAGE
        self._hist_job = None
        self.active_cookie_opts = {}
        cfg = load_settings()
        self.cookie_file = cfg.get("cookie_file")
        choice = cfg.get("cookie_choice", COOKIE_AUTO)
        if choice not in COOKIE_CHOICES or (
            choice == COOKIE_FILE
            and not (self.cookie_file and os.path.exists(self.cookie_file))
        ):
            choice = COOKIE_AUTO
        self._initial_cookie_choice = choice
        self._lock_retried = set()
        self.setting_up = False
        self.searching = False
        self.search_id = 0
        self._result_widgets = []
        self._row_thumbs = {}

        self._build_ui()
        self.after(100, self._poll_events)
        self.after(500, self._maybe_setup)
        self.after(800, self._start_bridge)
        self.after(3000, self._refresh_ext_status)
        self.after(6000, self._auto_check_update)

    # ---------- Interface ----------
    def _card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=R(16), bg_color=BG,
                            border_width=CARD_BORDER, border_color=LINE)
        if HUD:  # marcadores amarelo/vermelho no canto (estilo cyberpunk)
            tick = ctk.CTkFrame(card, width=46, height=3, fg_color=ACCENT, corner_radius=0)
            tick.place(x=0, y=0)
            dot = ctk.CTkFrame(card, width=10, height=3, fg_color=DANGER, corner_radius=0)
            dot.place(x=50, y=0)
        return card

    def _build_ui(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=24, pady=20)

        # Cabeçalho (banner de multimídia)
        ctk.CTkLabel(root, text="", image=self._banner_img).pack(pady=(0, 12))

        # Rodapé com marca d'água (reservado antes das abas)
        ctk.CTkLabel(
            root, text="Produzido por Lagaz", image=self._footer_img,
            compound="center", text_color=FOOTER_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="bottom", pady=(8, 0))

        # Aviso de instalação de componentes (Deno / FFmpeg)
        self.setup_banner = ctk.CTkFrame(root, fg_color=BANNER_BG, corner_radius=R(12))
        self.setup_label = ctk.CTkLabel(
            self.setup_banner, text="", text_color=BANNER_TEXT, wraplength=560,
            justify="left", anchor="w",
        )
        self.setup_label.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self.setup_btn = ctk.CTkButton(
            self.setup_banner, text="Tentar novamente", width=140, height=32,
            corner_radius=R(8), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._maybe_setup,
        )

        # Abas
        self.tabs = ctk.CTkTabview(
            root, fg_color=BG, corner_radius=R(16),
            segmented_button_fg_color=CARD,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=SEG_UNSEL,
            segmented_button_unselected_hover_color=SEG_UNSEL_HOVER,
            text_color=SEG_TEXT,
        )
        self.tabs.pack(fill="both", expand=True)
        tab_dl = self.tabs.add("Baixar")
        tab_search = self.tabs.add("Pesquisar")
        tab_hist = self.tabs.add("Histórico")
        tab_player = self.tabs.add("▶ Player")
        tab_cfg = self.tabs.add("⚙")
        page = ctk.CTkScrollableFrame(tab_dl, fg_color="transparent")
        page.pack(fill="both", expand=True)
        self._build_search_tab(tab_search)
        self._build_history_tab(tab_hist)
        self._build_player_tab(tab_player)
        self._build_settings_tab(tab_cfg)
        try:  # engrenagem um pouco maior
            self.tabs._segmented_button._buttons_dict["⚙"].configure(
                font=ctk.CTkFont(size=20), width=56
            )
        except Exception:  # noqa: BLE001
            pass

        # Card do link
        url_card = self._card(page)
        url_card.pack(fill="x", pady=(0, 12))
        row = ctk.CTkFrame(url_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=16)
        self.url_entry = ctk.CTkEntry(
            row, textvariable=self.url_var, height=44, corner_radius=R(12),
            border_width=ENTRY_BORDER, border_color=LINE, fg_color=CARD_2,
            placeholder_text="Cole o link do vídeo aqui...",
        )
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.bind("<Return>", lambda e: self.analyze())
        ctk.CTkButton(
            row, text="Colar", width=80, height=44, corner_radius=R(12),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT, command=self.paste,
        ).pack(side="left", padx=(8, 0))
        self.btn_analyze = ctk.CTkButton(
            row, text="Analisar", width=110, height=44, corner_radius=R(12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"), command=self.analyze,
        )
        self.btn_analyze.pack(side="left", padx=(8, 0))

        # Card do vídeo (miniatura + informações + qualidade)
        info_card = self._card(page)
        info_card.pack(fill="x", pady=(0, 12))
        inner = ctk.CTkFrame(info_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        self.thumb_label = ctk.CTkLabel(
            inner, text="", image=self._placeholder,
            compound="center", text_color=MUTED, corner_radius=R(12),
            width=THUMB_W, height=THUMB_H,
        )
        self.thumb_label.pack(side="left")

        side = ctk.CTkFrame(inner, fg_color="transparent")
        side.pack(side="left", fill="both", expand=True, padx=(16, 0))

        self.title_label = ctk.CTkLabel(
            side, text="Nenhum vídeo carregado", anchor="w", justify="left",
            wraplength=340, font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.title_label.pack(anchor="w", fill="x")
        self.meta_label = ctk.CTkLabel(
            side, text="", anchor="w", text_color=MUTED, wraplength=340,
            justify="left",
        )
        self.meta_label.pack(anchor="w", fill="x", pady=(4, 12))

        ctk.CTkLabel(side, text="Qualidade", text_color=MUTED, anchor="w").pack(
            anchor="w"
        )
        self.quality_menu = ctk.CTkOptionMenu(
            side, variable=self.quality_var, values=["—"], height=40,
            corner_radius=R(10), fg_color=CARD_2, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_2, dropdown_text_color=TEXT, text_color=TEXT,
            state="disabled", command=lambda _v: self._refresh_options(),
        )
        self.quality_menu.pack(anchor="w", fill="x", pady=(4, 0))

        # Gaveta "Mais opções" (fechada: o download funciona como antes)
        opt_card = self._card(page)
        opt_card.pack(fill="x", pady=(0, 12))
        self._opts_open = False
        self.opts_toggle = ctk.CTkButton(
            opt_card, text="▸  Mais opções", anchor="w", height=42, corner_radius=R(12),
            fg_color="transparent", hover_color=CARD_2, text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold"), command=self._toggle_opts,
        )
        self.opts_toggle.pack(fill="x", padx=6, pady=6)
        self.opts_body = ctk.CTkFrame(opt_card, fg_color="transparent")
        trow0 = ctk.CTkFrame(self.opts_body, fg_color="transparent")
        trow0.pack(fill="x", padx=16, pady=(2, 12))
        self.btn_thumb = ctk.CTkButton(
            trow0, text="Salvar thumbnail", width=160, height=32, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
            command=self.save_thumbnail, state="disabled",
        )
        self.btn_thumb.pack(side="left")
        ctk.CTkLabel(
            trow0, text="Salva a capa do vídeo em JPG, em alta resolução, na pasta escolhida.",
            anchor="w", text_color=MUTED, font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(10, 0))
        self.compat_switch = ctk.CTkSwitch(
            self.opts_body, text="Compatível com editores (MP4 H.264)", variable=self.compat_var,
            command=self._on_compat_toggle, progress_color=ACCENT,
            button_color=("#ffffff", "#ececef"),
        )
        self.compat_switch.pack(anchor="w", padx=16)
        self.compat_hint = ctk.CTkLabel(
            self.opts_body, text="", anchor="w", justify="left", wraplength=640,
            text_color=MUTED, font=ctk.CTkFont(size=12),
        )
        self.compat_hint.pack(anchor="w", fill="x", padx=16, pady=(2, 10))

        srow = ctk.CTkFrame(self.opts_body, fg_color="transparent")
        srow.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(srow, text="Legendas", anchor="w").pack(side="left")
        self.sub_menu = ctk.CTkOptionMenu(
            srow, variable=self.sub_var, values=[SUBS_NONE], width=250, height=34,
            corner_radius=R(10), fg_color=CARD_2, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_2,
            dropdown_text_color=TEXT, text_color=TEXT, state="disabled",
            command=lambda _v: self._refresh_options(),
        )
        self.sub_menu.pack(side="left", padx=(10, 0))
        self.sub_hint = ctk.CTkLabel(
            srow, text="", anchor="w", justify="left", wraplength=330,
            text_color=MUTED, font=ctk.CTkFont(size=12),
        )
        self.sub_hint.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.trim_check = ctk.CTkCheckBox(
            self.opts_body, text="Baixar só um trecho", variable=self.trim_var,
            command=self._on_trim_toggle, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=MUTED, corner_radius=R(6),
        )
        self.trim_check.pack(anchor="w", padx=16, pady=(0, 14))
        self.trim_box = ctk.CTkFrame(self.opts_body, fg_color="transparent")
        trow = ctk.CTkFrame(self.trim_box, fg_color="transparent")
        trow.pack(fill="x")
        entry_kw = dict(width=96, height=34, corner_radius=R(10), border_width=ENTRY_BORDER,
                        border_color=LINE, fg_color=CARD_2, justify="center")
        ctk.CTkLabel(trow, text="Início", anchor="w").pack(side="left")
        ctk.CTkEntry(trow, textvariable=self.trim_start_var, **entry_kw).pack(
            side="left", padx=(8, 16))
        ctk.CTkLabel(trow, text="Fim", anchor="w").pack(side="left")
        ctk.CTkEntry(trow, textvariable=self.trim_end_var, **entry_kw).pack(
            side="left", padx=(8, 16))
        ctk.CTkCheckBox(
            trow, text="Corte exato (mais lento)", variable=self.trim_exact_var,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=MUTED,
            corner_radius=R(6),
        ).pack(side="left")
        ctk.CTkLabel(
            self.trim_box, anchor="w", justify="left", wraplength=640,
            text_color=MUTED, font=ctk.CTkFont(size=12),
            text=("Use minutos:segundos (ex.: 2:15) ou horas:minutos:segundos. Sem o corte "
                  "exato, o vídeo pode começar até alguns segundos antes do ponto escolhido "
                  "(o corte cai no quadro-chave mais próximo). O MP3 sempre sai no ponto exato."),
        ).pack(anchor="w", fill="x", pady=(6, 0))

        # Card da pasta
        folder_card = self._card(page)
        folder_card.pack(fill="x", pady=(0, 12))
        frow = ctk.CTkFrame(folder_card, fg_color="transparent")
        frow.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(frow, text="📁", font=ctk.CTkFont(size=18)).pack(side="left")
        ctk.CTkEntry(
            frow, textvariable=self.folder_var, height=38, corner_radius=R(10),
            border_width=ENTRY_BORDER, border_color=LINE, fg_color=CARD_2,
        ).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ctk.CTkButton(
            frow, text="Escolher pasta", width=120, height=38, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT, command=self.choose_folder,
        ).pack(side="left")

        # Login do navegador (vídeos com restrição de idade)
        login_card = self._card(page)
        login_card.pack(fill="x", pady=(0, 12))
        lrow = ctk.CTkFrame(login_card, fg_color="transparent")
        lrow.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(lrow, text="🔑", font=ctk.CTkFont(size=18)).pack(side="left")
        ctk.CTkLabel(
            lrow, text="Login do navegador", anchor="w",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=(8, 12))
        self.cookie_var = ctk.StringVar(value=self._initial_cookie_choice)
        ctk.CTkOptionMenu(
            lrow, variable=self.cookie_var, values=COOKIE_CHOICES, height=34,
            corner_radius=R(10), fg_color=CARD_2, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_2, dropdown_text_color=TEXT, text_color=TEXT,
            command=self._on_cookie_choice,
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            login_card, wraplength=620, justify="left", anchor="w",
            text_color=MUTED, font=ctk.CTkFont(size=12),
            text=("Vídeos com restrição de idade só baixam se você estiver logado no "
                  "YouTube em um navegador deste computador. No modo Automático, o app "
                  "usa o login do navegador apenas quando o YouTube pedir."),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Botões de ação
        actions = ctk.CTkFrame(page, fg_color="transparent", bg_color=BG)
        actions.pack(fill="x", pady=(0, 12))
        self.btn_download = ctk.CTkButton(
            actions, text="Baixar", height=48, corner_radius=R(12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.start_download, state="disabled",
        )
        self.btn_download.pack(side="left", fill="x", expand=True)
        self.btn_cancel = ctk.CTkButton(
            actions, text="Cancelar", width=110, height=48, corner_radius=R(12),
            fg_color=DANGER, hover_color=DANGER_HOVER, command=self.cancel,
            state="disabled",
        )
        self.btn_cancel.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions, text="Abrir pasta", width=120, height=48, corner_radius=R(12),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT, command=self.open_folder,
        ).pack(side="left", padx=(8, 0))

        # Progresso
        prog_card = self._card(page)
        prog_card.pack(fill="x")
        self.progress = ctk.CTkProgressBar(
            prog_card, height=12, corner_radius=R(6), progress_color=ACCENT,
            fg_color=CARD_2,
        )
        self.progress.pack(fill="x", padx=16, pady=(16, 8))
        self.progress.set(0)
        self.status_label = ctk.CTkLabel(
            prog_card, text="Cole o link do vídeo e clique em Analisar.",
            anchor="w", justify="left", wraplength=700, text_color=MUTED,
        )
        self.status_label.pack(anchor="w", fill="x", padx=16, pady=(0, 14))
        self._refresh_options()


    # ---------- Opções do download (H.264, legendas, trecho) ----------
    def _current_mode(self):
        return compat_plan(bool(self.compat_var.get()), self.quality_var.get(),
                           self.video_heights, self.h264_set, self.codec_known)

    def _refresh_options(self):
        """Atualiza as dicas e o estado das opções conforme o vídeo e a qualidade."""
        choice = self.quality_var.get()
        audio = choice == LABEL_AUDIO
        if not self.video_info:
            text = ("Salva em MP4 H.264 + AAC, o formato que abre no Premiere, Vegas, CapCut, "
                    "DaVinci e em qualquer celular. Analise um link para ver como o vídeo vai sair.")
        elif audio:
            text = "Não se aplica ao MP3."
        elif not self.compat_var.get():
            text = ("Desligado: o vídeo vem no formato original do site (no YouTube, às vezes "
                    "VP9 ou AV1, que alguns editores não abrem).")
        else:
            mode, h = self._current_mode()
            if mode == "h264" and choice == LABEL_BEST:
                text = (f"✔ Sai em MP4 H.264 na melhor versão que já existe nesse formato ({h}p), "
                        "sem conversão. Para uma resolução maior, escolha-a na lista: o app "
                        "converte depois do download.")
            elif mode == "h264":
                text = "✔ Sai em MP4 H.264 nessa qualidade, sem conversão."
            elif mode == "recode":
                q = f"em {h}p" if h else "nessa qualidade"
                text = (f"Este vídeo não tem H.264 {q}: depois do download o app converte o "
                        "vídeo. Pode levar alguns minutos (bem mais em 4K).")
            else:
                text = "O app escolhe a versão H.264 quando o site oferecer."
        self.compat_hint.configure(text=text)

        trim = bool(self.trim_var.get())
        chosen = self.sub_var.get() != SUBS_NONE
        if not self.video_info:
            sub_text = ""
        elif trim:
            sub_text = "Legendas não são baixadas junto com um trecho."
        elif not self._sub_map:
            sub_text = "Este vídeo não tem legendas."
        elif chosen and audio:
            sub_text = "Com MP3, a legenda é salva como arquivo .srt."
        elif chosen:
            sub_text = "Vai embutida no vídeo e também como arquivo .srt."
        else:
            sub_text = f"{len(self._sub_map)} disponível(is)."
        self.sub_hint.configure(text=sub_text)
        ok = bool(self.video_info) and bool(self._sub_map) and not trim
        self.sub_menu.configure(state="normal" if ok else "disabled")
        self._update_opts_header()

    def _toggle_opts(self):
        self._opts_open = not self._opts_open
        if self._opts_open:
            self.opts_body.pack(fill="x", pady=(0, 4), after=self.opts_toggle)
        else:
            self.opts_body.pack_forget()
        self._update_opts_header()

    def _update_opts_header(self):
        """Título da gaveta: mostra as opções ligadas mesmo com ela fechada."""
        active = []
        if self.compat_var.get() and self.quality_var.get() != LABEL_AUDIO:
            active.append("MP4 H.264")
        if self.trim_var.get():
            active.append("só um trecho")
        elif self.sub_var.get() != SUBS_NONE:
            active.append("legenda")
        arrow = "▾" if self._opts_open else "▸"
        text = f"{arrow}  Mais opções"
        if active:
            text += "   •   ligado: " + ", ".join(active)
        elif not self._opts_open:
            text += "   (MP4 para editores, trecho, legendas e thumbnail)"
        self.opts_toggle.configure(text=text, text_color=ACCENT_TEXT if active else TEXT)

    def _on_compat_toggle(self):
        update_settings(compat_editors=bool(self.compat_var.get()))
        self._refresh_options()

    def _show_trim(self, show):
        if show:
            self.trim_check.pack(pady=(0, 6))
            self.trim_box.pack(fill="x", padx=16, pady=(0, 14), after=self.trim_check)
        else:
            self.trim_box.pack_forget()
            self.trim_check.pack(pady=(0, 14))

    def _on_trim_toggle(self):
        self._show_trim(bool(self.trim_var.get()))
        self._refresh_options()

    def _read_section(self):
        """Lê o trecho escolhido: (trecho ou None, mensagem de erro ou None)."""
        if not self.trim_var.get():
            return None, None
        if self.ffmpeg is None:
            return None, ("Para baixar só um trecho, o programa precisa do FFmpeg. Espere a "
                          "instalação dos componentes terminar e tente de novo.")
        start = parse_clock(self.trim_start_var.get())
        end = parse_clock(self.trim_end_var.get())
        if start is None:
            return None, "Início inválido. Use minutos:segundos, por exemplo 2:15."
        if end is None:
            return None, "Fim inválido. Use minutos:segundos, por exemplo 3:40."
        dur = (self.video_info or {}).get("duration")
        if dur and start >= dur:
            return None, f"O início passa do fim do vídeo ({clock_text(dur)})."
        if dur and end > dur:
            end = float(dur)
        if end <= start:
            return None, "O fim do trecho precisa ser depois do início."
        if end - start < 1:
            return None, "O trecho precisa ter pelo menos 1 segundo."
        return {"start": start, "end": end, "exact": bool(self.trim_exact_var.get())}, None

    def save_thumbnail(self):
        info = self.video_info
        if not info:
            return
        url = thumbnail_candidates(info)
        if not url:
            messagebox.showinfo("Thumbnail", "Este vídeo não tem thumbnail.")
            return
        self.btn_thumb.configure(state="disabled", text="Salvando...")
        threading.Thread(
            target=self._thumb_worker,
            args=(url, self.folder_var.get().strip(), info.get("title"), info.get("id")),
            daemon=True,
        ).start()

    def _thumb_worker(self, url, folder, title, vid):
        try:
            path, size = save_thumbnail_file(url, folder, title, vid)
            self.events.put(("thumb_saved", path, size))
        except Exception as e:  # noqa: BLE001
            log_error(url[0] if url else "", f"Thumbnail: {e}")
            self.events.put(("thumb_error", str(e)))

    def copy_report(self):
        text = build_report(self.ffmpeg, self.has_js, self.last_error_text)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Erro", f"Não foi possível copiar: {e}")
            return
        messagebox.showinfo(
            "Relatório copiado",
            "O relatório de erro foi copiado. Cole (Ctrl+V) na mensagem para quem vai te "
            "ajudar ou num relato no GitHub.\n\nEle traz a versão do programa, do Windows e "
            "do yt-dlp e os últimos erros, sem o seu nome de usuário.",
        )

    def _show_error(self, msg):
        self.last_error_text = msg
        try:
            HelpDialog(self, "Erro", msg[:1100], None,
                       [("Copiar relatório de erro", self.copy_report, False, False)],
                       self.ico_path)
        except Exception:  # noqa: BLE001
            messagebox.showerror("Erro", msg[:1100])

    def _pp_hook(self, d):
        if self.cancel_flag.is_set():
            raise DownloadCancelled()
        if d.get("status") == "started":
            name = d.get("postprocessor")
            text = PP_TEXT.get(name)
            if text:
                self.events.put(("pp", text, name == "VideoConvertor"))

    # ---------- Componentes (Deno / FFmpeg) ----------
    def _missing_components(self):
        missing = []
        if not self.has_js:
            missing.append("Deno")
        if not self.ffmpeg:
            missing.append("FFmpeg")
        if mpv_dir() is None and not self._mpv_failed:
            missing.append("Player")
        return missing

    def _show_banner(self, text):
        if hasattr(self, "_update_banner_btn"):
            self._update_banner_btn.pack_forget()
        self.setup_label.configure(text=text)
        self.setup_banner.pack(fill="x", pady=(0, 10), before=self.tabs)

    def _hide_banner_if_ok(self):
        if not self._missing_components() and not self.setting_up:
            if self.update_info and not self.updating_app:
                self._show_update_banner(self.update_info["version"])
                return
            self.setup_banner.pack_forget()

    def _maybe_setup(self):
        if self.setting_up:
            return
        missing = self._missing_components()
        if not missing:
            self._hide_banner_if_ok()
            return
        self.setting_up = True
        self.setup_btn.pack_forget()
        self._show_banner(
            f"Preparando componentes necessários ({', '.join(missing)}). "
            "Isso é feito só na primeira vez..."
        )
        threading.Thread(
            target=self._setup_worker,
            args=(not self.has_js, not self.ffmpeg, mpv_dir() is None),
            daemon=True,
        ).start()

    def _setup_worker(self, need_deno, need_ffmpeg, need_mpv=False):
        def make_cb(name):
            state = {"p": -1}

            def cb(done, total):
                pct = int(done * 100 / total) if total else 0
                if total and pct == state["p"]:
                    return
                state["p"] = pct
                txt = (f"Baixando {name}... {pct}%" if total
                       else f"Baixando {name}... {fmt_bytes(done)}")
                self.events.put(("setup_progress", txt))

            return cb

        try:
            os.makedirs(TOOLS_DIR, exist_ok=True)
            tmp = tempfile.mkdtemp(prefix="bdv_")
            try:
                if need_deno:
                    z = os.path.join(tmp, "deno.zip")
                    download_file(DENO_URL, z, make_cb("Deno"))
                    extract_members(z, ["deno.exe"], TOOLS_DIR)
                if need_ffmpeg:
                    last_error = None
                    for url in FFMPEG_URLS:
                        try:
                            z = os.path.join(tmp, "ffmpeg.zip")
                            download_file(url, z, make_cb("FFmpeg"))
                            extract_members(z, ["ffmpeg.exe", "ffprobe.exe"], TOOLS_DIR)
                            last_error = None
                            break
                        except Exception as e:  # noqa: BLE001
                            last_error = e
                    if last_error is not None:
                        raise last_error
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            if need_mpv:
                # o player é opcional: se falhar, o resto continua funcionando
                try:
                    download_mpv(make_cb("Player"))
                except Exception:  # noqa: BLE001
                    self._mpv_failed = True
            self.events.put(("setup_done",))
        except Exception as e:  # noqa: BLE001
            self.events.put(("setup_error", str(e)))

    # ---------- Aba Pesquisar ----------
    def _build_search_tab(self, tab):
        top = self._card(tab)
        top.pack(fill="x", pady=(8, 10))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(16, 8))

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            row, textvariable=self.search_var, height=44, corner_radius=R(12),
            border_width=ENTRY_BORDER, border_color=LINE, fg_color=CARD_2, placeholder_text="Pesquisar vídeos...",
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda e: self.search())

        self.source_var = ctk.StringVar(value=list(SEARCH_SOURCES)[0])
        ctk.CTkOptionMenu(
            row, variable=self.source_var, values=list(SEARCH_SOURCES), width=160,
            height=44, corner_radius=R(12), fg_color=CARD_2, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_2, dropdown_text_color=TEXT, text_color=TEXT,
        ).pack(side="left", padx=(8, 0))
        self.btn_search = ctk.CTkButton(
            row, text="Buscar", width=100, height=44, corner_radius=R(12),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"), command=self.search,
        )
        self.btn_search.pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(top, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(
            row2, text_color=MUTED, anchor="w", justify="left", wraplength=470,
            text=("Outros sites: pesquise no navegador, copie o link e cole na "
                  "aba Baixar."),
        ).pack(side="left")
        ctk.CTkButton(
            row2, text="🌐 Pesquisar na web", width=160, height=34, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT, command=self.search_web,
        ).pack(side="right")

        self.results_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True)
        self._show_results_status("Digite algo e clique em Buscar.", art=True)

    def _clear_results(self):
        for w in self._result_widgets:
            try:
                w.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._result_widgets = []
        self._row_thumbs = {}

    def _show_results_status(self, text, art=False):
        self._clear_results()
        lbl = ctk.CTkLabel(
            self.results_frame, bg_color=BG, text=text, text_color=MUTED, wraplength=640,
            justify="center", image=self._empty_art if art else None,
            compound="top",
        )
        lbl.pack(pady=20 if art else 30)
        self._result_widgets.append(lbl)

    def search_web(self):
        q = self.search_var.get().strip()
        if q:
            webbrowser.open(f"https://www.google.com/search?tbm=vid&q={quote(q)}")
        else:
            webbrowser.open("https://www.google.com/videohp")

    def search(self):
        q = self.search_var.get().strip()
        if not q or self.searching:
            return
        self.searching = True
        self.search_id += 1
        sid = self.search_id
        self.btn_search.configure(state="disabled")
        self._show_results_status("Buscando...")
        prefix = SEARCH_SOURCES[self.source_var.get()]
        threading.Thread(
            target=self._search_worker, args=(sid, prefix, q), daemon=True
        ).start()

    def _search_worker(self, sid, prefix, query):
        logger = QuietLogger()
        opts = {"quiet": True, "no_warnings": True, "no_color": True,
                "skip_download": True, "extract_flat": "in_playlist",
                "logger": logger, **self.js_opts}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"{prefix}{SEARCH_LIMIT}:{query}", download=False)
            results = []
            for e in info.get("entries") or []:
                if not e:
                    continue
                url = e.get("webpage_url") or e.get("url") or ""
                if not url.startswith("http"):
                    if prefix.startswith("yt") and e.get("id"):
                        url = "https://www.youtube.com/watch?v=" + e["id"]
                    else:
                        continue
                meta = "  •  ".join(p for p in (
                    e.get("channel") or e.get("uploader") or "",
                    fmt_duration(e.get("duration")),
                    fmt_views(e.get("view_count")),
                ) if p)
                results.append({
                    "url": url,
                    "title": e.get("title") or "Sem título",
                    "meta": meta,
                    "thumb": pick_thumb(e, prefix),
                })
            self.events.put(("search_results", sid, results))

            def job(i, thumb_url):
                img = fetch_image(thumb_url, (SMALL_W * 2, SMALL_H * 2))
                if img is not None:
                    self.events.put(("search_thumb", sid, i, img))

            with ThreadPoolExecutor(max_workers=6) as pool:
                for i, r in enumerate(results):
                    if r["thumb"]:
                        pool.submit(job, i, r["thumb"])
        except Exception as e:  # noqa: BLE001
            msg = clean_msg(logger.last_error or str(e))
            self.events.put(("search_error", sid, msg))

    def _render_results(self, results):
        if not results:
            self._show_results_status("Nenhum resultado encontrado.", art=True)
            return
        self._clear_results()
        for i, r in enumerate(results):
            card = ctk.CTkFrame(self.results_frame, fg_color=CARD, corner_radius=R(14), bg_color=BG)
            card.pack(fill="x", pady=5, padx=2)
            self._result_widgets.append(card)

            thumb = ctk.CTkLabel(
                card, text="", image=self._small_placeholder,
                width=SMALL_W, height=SMALL_H,
            )
            thumb.pack(side="left", padx=12, pady=12)
            self._row_thumbs[i] = thumb

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(side="right", padx=12)
            ctk.CTkButton(
                btns, text="⬇ Baixar", width=110, height=34, corner_radius=R(10),
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                command=lambda u=r["url"]: self.use_result(u, True),
            ).pack(pady=(0, 6))
            ctk.CTkButton(
                btns, text="Qualidade...", width=110, height=34, corner_radius=R(10),
                fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
                command=lambda u=r["url"]: self.use_result(u, False),
            ).pack()

            mid = ctk.CTkFrame(card, fg_color="transparent")
            mid.pack(side="left", fill="both", expand=True)
            title = r["title"]
            if len(title) > 90:
                title = title[:87] + "..."
            ctk.CTkLabel(
                mid, text=title, anchor="w", justify="left", wraplength=290,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(anchor="w", fill="x", pady=(14, 2))
            ctk.CTkLabel(
                mid, text=r["meta"], anchor="w", justify="left", wraplength=290,
                text_color=MUTED, font=ctk.CTkFont(size=12),
            ).pack(anchor="w", fill="x")

    def _on_search_thumb(self, sid, idx, img):
        if sid != self.search_id:
            return
        lbl = self._row_thumbs.get(idx)
        if lbl is None:
            return
        try:
            lbl.configure(image=ctk.CTkImage(img, size=(SMALL_W, SMALL_H)))
        except Exception:  # noqa: BLE001
            pass

    def use_result(self, url, quick):
        """Manda o resultado para a aba Baixar (quick = já baixa na melhor qualidade)."""
        if self.busy:
            messagebox.showinfo(
                "Aguarde", "Espere a tarefa atual terminar para iniciar outra."
            )
            return
        self.url_var.set(url)
        self.pending_quality = None
        self.auto_download = quick
        self.tabs.set("Baixar")
        self.analyze()

    # ---------- Aba ⚙ (Configurações) ----------
    def _build_settings_tab(self, tab):
        page = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        page.pack(fill="both", expand=True)

        # Aparência
        card = self._card(page)
        card.pack(fill="x", pady=(8, 12))
        ctk.CTkLabel(
            card, text="Aparência", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(
            card, text_color=MUTED, anchor="w", justify="left", wraplength=620,
            font=ctk.CTkFont(size=12),
            text=("Escolha o tema do aplicativo. \"Sistema\" acompanha o tema do "
                  "Windows automaticamente."),
        ).pack(anchor="w", padx=16, pady=(0, 10))
        self.theme_seg = ctk.CTkSegmentedButton(
            card, values=list(THEME_LABELS), command=self._on_theme_change,
            height=38, corner_radius=R(10), fg_color=CARD_2, selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, unselected_color=SEG_UNSEL,
            unselected_hover_color=SEG_UNSEL_HOVER, text_color=SEG_TEXT,
        )
        label = next(k for k, v in THEME_LABELS.items() if v == self.appearance)
        self.theme_seg.set(label)
        self.theme_seg.pack(fill="x", padx=16, pady=(0, 16))

        # Estilo visual: gaveta com os estilos (fechada mostra o estilo atual)
        card_st = self._card(page)
        card_st.pack(fill="x", pady=(0, 12))
        self._style_open = False
        self.style_toggle = ctk.CTkButton(
            card_st, text="", anchor="w", height=44, corner_radius=R(12),
            fg_color="transparent", hover_color=CARD_2, text_color=TEXT,
            font=ctk.CTkFont(size=16, weight="bold"), command=self._toggle_style_drawer,
        )
        self.style_toggle.pack(fill="x", padx=6, pady=6)
        self.style_body = ctk.CTkFrame(card_st, fg_color="transparent")
        ctk.CTkLabel(
            self.style_body, text_color=MUTED, anchor="w", justify="left", wraplength=620,
            font=ctk.CTkFont(size=12),
            text=("Muda as cores, as formas e as imagens do aplicativo. Clássico é o visual "
                  "principal; Cyberpunk usa amarelo, vermelho e cinza com cantos retos; Retrô "
                  "é minimalista, em creme, laranja e verde-petróleo; Steampunk usa latão, "
                  "cobre e madeira; Arcade 8-bit é pixel art de fliperama; Fantasia / RPG tem "
                  "castelo, ouro e pergaminho. O programa reinicia para aplicar."),
        ).pack(anchor="w", padx=16, pady=(0, 10))
        grid = ctk.CTkFrame(self.style_body, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 14))
        self._style_btns = {}
        for i, (label, key) in enumerate(STYLE_LABELS.items()):
            btn = ctk.CTkButton(
                grid, text=label, height=40, corner_radius=R(10),
                command=lambda lb=label: self._on_style_change(lb),
            )
            btn.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="ew")
            self._style_btns[key] = btn
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1, uniform="estilos")
        self._paint_style_drawer()

        # Bandeja do sistema
        card2 = self._card(page)
        card2.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            card2, text="Bandeja do sistema", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 8))
        self.tray_var = ctk.BooleanVar(value=self.minimize_to_tray)
        self.tray_switch = ctk.CTkSwitch(
            card2, text="Ao fechar, minimizar para a bandeja do sistema",
            variable=self.tray_var, command=self._on_tray_toggle,
            progress_color=ACCENT, button_color=("#ffffff", "#ececef"),
        )
        self.tray_switch.pack(anchor="w", padx=16)
        ctk.CTkLabel(
            card2, text_color=MUTED, anchor="w", justify="left", wraplength=620,
            font=ctk.CTkFont(size=12),
            text=("O programa continua rodando em segundo plano e os downloads não são "
                  "interrompidos. Clique no ícone perto do relógio para abrir; para "
                  "fechar de vez, use \"Sair\" no menu do ícone."),
        ).pack(anchor="w", padx=16, pady=(8, 16 if pystray else 6))
        if pystray is None:
            self.tray_switch.configure(state="disabled")
            ctk.CTkLabel(
                card2, text_color=WARN, anchor="w", justify="left", wraplength=620,
                font=ctk.CTkFont(size=12),
                text=("Componente da bandeja (pystray) não encontrado. Abra o app pelo "
                      "executar.bat para instalar."),
            ).pack(anchor="w", padx=16, pady=(0, 16))

        # Sugestões de download no navegador
        card4 = self._card(page)
        card4.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            card4, text="Sugestões de download no navegador",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))
        self.suggest_var = ctk.BooleanVar(value=self.suggest_enabled)
        ctk.CTkSwitch(
            card4, text="Sugerir o download quando eu estiver assistindo um vídeo",
            variable=self.suggest_var, command=self._on_suggest_toggle,
            progress_color=ACCENT, button_color=("#ffffff", "#ececef"),
        ).pack(anchor="w", padx=16)
        ctk.CTkLabel(
            card4, text_color=MUTED, anchor="w", justify="left", wraplength=620,
            font=ctk.CTkFont(size=12),
            text=("Funciona com a extensão do navegador (Edge, Chrome, Brave...). O "
                  "programa só recebe o endereço e o título da página quando um vídeo "
                  "começa a tocar, e nada sai do seu computador."),
        ).pack(anchor="w", padx=16, pady=(8, 8))
        qrow = ctk.CTkFrame(card4, fg_color="transparent")
        qrow.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(qrow, text="Qualidade do botão Baixar do aviso:", anchor="w").pack(
            side="left")
        cur = next(k for k, v in QUICK_CHOICES.items() if v == self.quick_quality)
        self.quick_var = ctk.StringVar(value=cur)
        ctk.CTkOptionMenu(
            qrow, variable=self.quick_var, values=list(QUICK_CHOICES), width=190,
            height=34, corner_radius=R(10), fg_color=CARD_2, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_2,
            dropdown_text_color=TEXT, text_color=TEXT, command=self._on_quick_quality,
        ).pack(side="left", padx=(10, 0))
        self.ext_status = ctk.CTkLabel(
            card4, text="", anchor="w", justify="left", wraplength=620,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.ext_status.pack(anchor="w", padx=16)
        brow = ctk.CTkFrame(card4, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(10, 16))
        ctk.CTkButton(
            brow, text="Instalar a extensão", width=170, height=36, corner_radius=R(10),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.show_extension_help,
        ).pack(side="left")
        ctk.CTkButton(
            brow, text="Limpar sites ignorados", width=170, height=36, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
            command=self.clear_ignored,
        ).pack(side="left", padx=(8, 0))

        # Sobre
        card3 = self._card(page)
        card3.pack(fill="x", pady=(0, 12))
        try:
            ver = f"yt-dlp {yt_dlp.version.__version__}"
        except Exception:  # noqa: BLE001
            ver = "yt-dlp"
        ctk.CTkLabel(
            card3, text="Baixador de Vídeos", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(
            card3, text=f"Produzido por Lagaz  •  {ver}", text_color=MUTED,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Atualizações do aplicativo
        card_up = self._card(page)
        card_up.pack(fill="x", pady=(0, 12), before=card3)
        ctk.CTkLabel(
            card_up, text="Atualizações", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 2))
        self.update_status = ctk.CTkLabel(
            card_up, text=f"Versão instalada: {APP_VERSION}", anchor="w", justify="left",
            wraplength=620, text_color=MUTED, font=ctk.CTkFont(size=12),
        )
        self.update_status.pack(anchor="w", padx=16)
        self.update_notes = ctk.CTkLabel(
            card_up, text="", anchor="w", justify="left", wraplength=620,
            text_color=TEXT_SOFT, font=ctk.CTkFont(size=12),
        )
        self.update_progress = ctk.CTkProgressBar(
            card_up, height=8, corner_radius=R(4), progress_color=ACCENT, fg_color=CARD_2)
        self.update_progress.set(0)
        urow = ctk.CTkFrame(card_up, fg_color="transparent")
        urow.pack(fill="x", padx=16, pady=(10, 4))
        self.btn_check_update = ctk.CTkButton(
            urow, text="Buscar atualizações", width=170, height=36, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
            command=lambda: self.check_update(manual=True),
        )
        self.btn_check_update.pack(side="left")
        self.btn_install_update = ctk.CTkButton(
            urow, text="⬇ Baixar e instalar", width=170, height=36, corner_radius=R(10),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(weight="bold"),
            command=self.install_update,
        )
        self.btn_update_page = ctk.CTkButton(
            urow, text="Ver novidades", width=120, height=36, corner_radius=R(10),
            fg_color="transparent", hover_color=CARD_2, text_color=ACCENT_TEXT,
            command=lambda: webbrowser.open((self.update_info or {}).get("page") or RELEASES_PAGE),
        )
        self.auto_update_var = ctk.BooleanVar(value=bool(load_settings().get("auto_check_update", True)))
        ctk.CTkSwitch(
            card_up, text="Verificar atualizações automaticamente",
            variable=self.auto_update_var, progress_color=ACCENT, button_color=("#ffffff", "#ececef"),
            command=lambda: update_settings(auto_check_update=bool(self.auto_update_var.get())),
        ).pack(anchor="w", padx=16, pady=(6, 16))

        # Problemas? (relatório de erro)
        card_bug = self._card(page)
        card_bug.pack(fill="x", pady=(0, 12), before=card3)
        ctk.CTkLabel(
            card_bug, text="Problemas?", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(
            card_bug, text_color=MUTED, anchor="w", justify="left", wraplength=620,
            font=ctk.CTkFont(size=12),
            text=("Se um download falhar, copie o relatório de erro e mande para quem está "
                  "te ajudando, ou abra um relato no GitHub. Ele traz a versão do programa, "
                  "do Windows e do yt-dlp e os últimos erros, sem o seu nome de usuário."),
        ).pack(anchor="w", padx=16, pady=(0, 10))
        brow2 = ctk.CTkFrame(card_bug, fg_color="transparent")
        brow2.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            brow2, text="Copiar relatório de erro", width=190, height=36, corner_radius=R(10),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.copy_report,
        ).pack(side="left")
        ctk.CTkButton(
            brow2, text="Relatar no GitHub", width=150, height=36, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
            command=lambda: webbrowser.open(ISSUES_URL),
        ).pack(side="left", padx=(8, 0))

        # versão atual no rodapé das configurações
        ctk.CTkLabel(
            page, text=f"Baixador de Vídeos  •  versão {APP_VERSION}", bg_color=BG,
            text_color=MUTED, font=ctk.CTkFont(size=12),
        ).pack(pady=(4, 12))

    def _toggle_style_drawer(self):
        self._style_open = not self._style_open
        if self._style_open:
            self.style_body.pack(fill="x", after=self.style_toggle)
        else:
            self.style_body.pack_forget()
        self._paint_style_drawer()

    def _paint_style_drawer(self):
        """Título da gaveta com o estilo atual e destaque no botão do estilo em uso."""
        current = next(k for k, v in STYLE_LABELS.items() if v == UI_STYLE)
        arrow = "▾" if self._style_open else "▸"
        self.style_toggle.configure(text=f"{arrow}  Estilo visual   •   atual: {current}")
        for key, btn in self._style_btns.items():
            on = key == UI_STYLE
            label = next(k for k, v in STYLE_LABELS.items() if v == key)
            btn.configure(
                text=("✔ " + label) if on else label,
                fg_color=ACCENT if on else CARD_2, hover_color=ACCENT_HOVER if on else CARD_2_HOVER,
                text_color=ON_ACCENT if on else TEXT,
            )

    def _on_style_change(self, label):
        key = STYLE_LABELS.get(label, DEFAULT_STYLE)
        if key == UI_STYLE:
            return
        if self.busy:
            messagebox.showinfo(
                "Aguarde",
                "Espere o download atual terminar para trocar o estilo visual.",
            )
            return
        if not messagebox.askyesno(
            "Trocar estilo visual",
            f"Mudar para o estilo {label}?\n\nO programa vai reiniciar para aplicar "
            "(leva só alguns segundos).",
        ):
            return
        update_settings(ui_style=key)
        self._restart()

    def _restart(self):
        """Fecha e abre o programa de novo (para aplicar o estilo visual)."""
        if getattr(sys, "frozen", False):
            cmd = [sys.executable] + sys.argv[1:]
        else:
            cmd = [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:]
        self.cancel_flag.set()
        self._stop_tray()
        if self.bridge is not None:
            self.bridge.stop()
        self._player_close()
        try:
            subprocess.Popen(cmd, cwd=os.getcwd(), close_fds=True)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(
                "Reiniciar",
                f"Não consegui reiniciar sozinho. Feche e abra o programa.\n\n{e}",
            )
            return
        self.destroy()

    def _on_theme_change(self, label):
        key = THEME_LABELS.get(label, "dark")
        self.appearance = key
        ctk.set_appearance_mode(APPEARANCE[key])
        update_settings(appearance=key)

    def _on_tray_toggle(self):
        self.minimize_to_tray = bool(self.tray_var.get())
        update_settings(minimize_to_tray=self.minimize_to_tray)
        if not self.minimize_to_tray:
            self._stop_tray()

    # ---------- Integração com o navegador ----------
    def _start_bridge(self):
        if self.bridge is not None:
            return
        try:
            bridge = BridgeServer(self)
            bridge.start()
            self.bridge = bridge
        except Exception:  # noqa: BLE001  (porta ocupada, por exemplo)
            self.bridge = None

    def _on_suggest_toggle(self):
        self.suggest_enabled = bool(self.suggest_var.get())
        update_settings(suggest_downloads=self.suggest_enabled)
        self._update_ext_status()

    def _on_quick_quality(self, label):
        self.quick_quality = QUICK_CHOICES.get(label, "1080p")
        update_settings(quick_quality=self.quick_quality)

    def _update_ext_status(self):
        if not self.suggest_enabled:
            text, color = "Sugestões desativadas.", MUTED
        elif self.bridge is None:
            text = (f"Não foi possível iniciar o receptor (a porta {BRIDGE_PORT} pode "
                    "estar em uso por outro programa).")
            color = WARN
        elif self.bridge_last_seen and time.time() - self.bridge_last_seen < 100:
            text, color = "✔ Extensão conectada.", SUCCESS
        else:
            text = ("Extensão não detectada. Instale a extensão e deixe o navegador "
                    "aberto.")
            color = MUTED
        try:
            self.ext_status.configure(text=text, text_color=color)
        except Exception:  # noqa: BLE001
            pass

    def _refresh_ext_status(self):
        self._update_ext_status()
        self.after(3000, self._refresh_ext_status)

    def _notify(self, title, text):
        """Aviso do Windows (só quando a janela está escondida na bandeja)."""
        try:
            if self.tray is not None and self.state() in ("withdrawn", "iconic"):
                self.tray.notify(str(text)[:200], title)
        except Exception:  # noqa: BLE001
            pass

    def _on_browser_video(self, data):
        url = str(data.get("url") or "")[:2000]
        if not url.startswith(("http://", "https://")):
            return
        if data.get("manual"):  # botão "Baixar a página atual" da extensão
            if self.busy:
                self._show_window()
                messagebox.showinfo(
                    "Aguarde", "Espere a tarefa atual terminar para iniciar outra."
                )
                return
            self._show_window()
            self.url_var.set(url)
            self.pending_quality = None
            self.auto_download = False
            self.tabs.set("Baixar")
            self.analyze()
            return
        if not self.suggest_enabled:
            return
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if any(host == h or host.endswith("." + h) for h in self.ignored_hosts):
            return
        now = time.time()
        key = norm_url(url)
        if now - self._suggested.get(key, 0) < SUGGEST_REPEAT:
            return
        if now - self._last_toast_time < SUGGEST_MIN_GAP or self._probing:
            return
        self._probing = True
        threading.Thread(
            target=self._probe_worker, args=(url, key, data), daemon=True
        ).start()

    def _probe_worker(self, url, key, data):
        """Confere se o yt-dlp consegue baixar essa página antes de sugerir."""
        logger = QuietLogger()
        opts = {"quiet": True, "no_warnings": True, "no_color": True, "noplaylist": True,
                "logger": logger, "skip_download": True, "socket_timeout": 15,
                **self.js_opts}
        info, login = None, False
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:  # noqa: BLE001
            if needs_login(clean_msg(logger.last_error or str(e))):
                login = True
            else:
                self.events.put(("suggest_fail", key))  # site não suportado / sem vídeo
                return
        if info is not None and info.get("_type") == "playlist":
            self.events.put(("suggest_fail", key))
            return
        info = info or {}
        pil = fetch_thumbnail(info) if info else None
        if pil is None and data.get("poster"):
            pil = fetch_image(str(data["poster"]), (THUMB_W * 2, THUMB_H * 2))
        self.events.put(("suggest_ready", {
            "url": url, "key": key,
            "title": info.get("title") or str(data.get("title") or "")[:120] or "Vídeo",
            "uploader": info.get("uploader") or info.get("channel") or "",
            "duration": fmt_duration(info.get("duration") or
                                     (data.get("duration") if data.get("duration") not in (None, "Infinity") else 0)),
            "thumb": pil, "login": login,
        }))

    def _show_suggestion(self, p):
        self._probing = False
        if not self.suggest_enabled:
            return
        now = time.time()
        self._suggested[p["key"]] = now
        self._last_toast_time = now
        already = next((h.get("date") for h in self.history
                        if norm_url(h.get("url", "")) == p["key"]), None)
        pil = p.get("thumb")
        image = (ctk.CTkImage(ImageOps.fit(pil, (SMALL_W * 2, SMALL_H * 2)),
                              size=(SMALL_W, SMALL_H))
                 if pil is not None else self._small_placeholder)
        if self._toast is not None:
            self._toast.close()
        try:
            self._toast = SuggestionToast(
                self, p, image, already,
                on_download=lambda: self._suggest_download(p),
                on_choose=lambda: self._suggest_choose(p),
                on_ignore=lambda: self._suggest_ignore(p),
                on_closed=self._toast_closed, icon_path=self.ico_path,
            )
        except Exception:  # noqa: BLE001
            self._toast = None

    def _toast_closed(self):
        self._toast = None

    def _suggest_download(self, p):
        if self.busy:
            self._show_window()
            messagebox.showinfo(
                "Aguarde", "Espere a tarefa atual terminar para baixar este vídeo."
            )
            return
        self.url_var.set(p["url"])
        self.pending_quality = None if self.quick_quality == "best" else self.quick_quality
        self.auto_download = True
        self.tabs.set("Baixar")
        self.analyze()
        self._notify("Baixando vídeo", p.get("title") or p["url"])

    def _suggest_choose(self, p):
        if self.busy:
            self._show_window()
            messagebox.showinfo(
                "Aguarde", "Espere a tarefa atual terminar para iniciar outra."
            )
            return
        self._show_window()
        self.url_var.set(p["url"])
        self.pending_quality = None
        self.auto_download = False
        self.tabs.set("Baixar")
        self.analyze()

    def _suggest_ignore(self, p):
        host = (urlparse(p["url"]).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host and host not in self.ignored_hosts:
            self.ignored_hosts.append(host)
            update_settings(ignored_hosts=self.ignored_hosts)
        self._notify("Baixador de Vídeos", f"Não vou mais sugerir downloads em {host}.")

    def clear_ignored(self):
        if not self.ignored_hosts:
            messagebox.showinfo("Sites ignorados", "Nenhum site está sendo ignorado.")
            return
        lista = "\n".join(self.ignored_hosts[:15])
        if messagebox.askyesno(
            "Limpar sites ignorados",
            f"Voltar a sugerir downloads nestes sites?\n\n{lista}",
        ):
            self.ignored_hosts = []
            update_settings(ignored_hosts=[])

    def _extension_dir(self):
        for base in (APP_DIR, os.path.dirname(APP_DIR)):
            path = os.path.join(base, "extensao_navegador")
            if os.path.isdir(path):
                return path
        return None

    def show_extension_help(self):
        folder = self._extension_dir()
        message = (
            "Para o programa saber quando você está assistindo um vídeo, instale a "
            "extensão no navegador (leva 1 minuto):\n\n"
            "Edge, Chrome ou Brave:\n"
            "1. Abra a página de extensões do navegador (botão 1; no Chrome digite "
            "chrome://extensions).\n"
            "2. Ative o \"Modo de desenvolvedor\".\n"
            "3. Clique em \"Carregar sem pacote\" (no Chrome: \"Carregar sem "
            "compactação\") e escolha a pasta da extensão (botão 2 abre a pasta).\n"
            "4. Pronto! Fixe o ícone da extensão ao lado da barra de endereços para ver "
            "o status.\n\n"
            "Depois, quando um vídeo estiver tocando por alguns segundos, aparece um "
            "aviso no canto da tela com o botão Baixar."
        )
        if folder is None:
            message += ("\n\n⚠ A pasta \"extensao_navegador\" não foi encontrada ao lado "
                        "do programa.")
        buttons = [
            ("1. Abrir a página de extensões do Edge", self._open_edge_ext, False, False),
            ("2. Abrir a pasta da extensão", lambda: self._open_ext_folder(folder), True, False),
            ("3. Copiar o caminho da pasta", lambda: self._copy_ext_path(folder), False, False),
        ]
        HelpDialog(self, "Instalar a extensão do navegador", message, "", buttons,
                   self.ico_path)

    def _open_edge_ext(self):
        try:
            os.startfile("microsoft-edge:edge://extensions/")
        except Exception:  # noqa: BLE001
            webbrowser.open("edge://extensions/")

    def _open_ext_folder(self, folder):
        if folder:
            try:
                os.startfile(folder)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Erro", str(e))
        else:
            messagebox.showwarning("Pasta não encontrada",
                                   "A pasta da extensão não foi encontrada.")

    def _copy_ext_path(self, folder):
        if folder:
            self.clipboard_clear()
            self.clipboard_append(folder)
            messagebox.showinfo("Copiado", "Caminho copiado:\n" + folder)

    # ---------- Atualizações do aplicativo ----------
    def _auto_check_update(self):
        cfg = load_settings()
        if not cfg.get("auto_check_update", True):
            return
        if time.time() - float(cfg.get("last_update_check", 0)) < UPDATE_CHECK_EVERY:
            # já verificou há pouco: só mostra o aviso se já sabia de uma versão nova
            known = cfg.get("known_update")
            if known and is_newer(known, APP_VERSION):
                self.check_update(manual=False)
            return
        self.check_update(manual=False)

    def check_update(self, manual=False):
        if getattr(self, "_checking_update", False) or self.updating_app:
            return
        self._checking_update = True
        if manual:
            self.btn_check_update.configure(state="disabled", text="Buscando...")
            self.update_status.configure(text="Procurando uma versão nova...", text_color=MUTED)

        def work():
            try:
                info = fetch_latest_release()
                self.events.put(("update_checked", info, manual, None))
            except Exception as e:  # noqa: BLE001
                self.events.put(("update_checked", None, manual, str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_checked(self, info, manual, error):
        self._checking_update = False
        self.btn_check_update.configure(state="normal", text="Buscar atualizações")
        if error:
            self.update_status.configure(
                text=f"Versão instalada: {APP_VERSION}. Não foi possível verificar agora "
                     "(sem internet?).", text_color=WARN)
            if manual:
                messagebox.showwarning("Atualizações", "Não foi possível verificar atualizações agora.\n\n" + error[:200])
            return
        update_settings(last_update_check=time.time(), known_update=info["version"])
        if not is_newer(info["version"], APP_VERSION):
            self.update_info = None
            self.btn_install_update.pack_forget()
            self.btn_update_page.pack_forget()
            self.update_notes.pack_forget()
            self.update_status.configure(
                text=f"Versão instalada: {APP_VERSION}. Você já está na versão mais recente. ✔",
                text_color=SUCCESS)
            if manual:
                messagebox.showinfo("Atualizações", f"Você já está na versão mais recente ({APP_VERSION}).")
            return
        self.update_info = info
        self.update_status.configure(
            text=f"Versão instalada: {APP_VERSION}.  Nova versão disponível: {info['version']} 🎉",
            text_color=ACCENT_TEXT)
        if info.get("notes"):
            self.update_notes.configure(text=info["notes"].replace("## ", "").replace("**", ""))
            self.update_notes.pack(anchor="w", padx=16, pady=(6, 0), before=self.btn_check_update.master)
        self.btn_install_update.configure(
            text="⬇ Baixar e instalar" if installed_with_setup() else "⬇ Baixar a nova versão")
        self.btn_install_update.pack(side="left", padx=(8, 0))
        self.btn_update_page.pack(side="left", padx=(8, 0))
        self._show_update_banner(info["version"])
        self._notify("Nova versão disponível", f"Baixador de Vídeos {info['version']}")

    def _show_update_banner(self, version):
        if self.setting_up:
            return
        self.setup_label.configure(
            text=f"🎉 Nova versão {version} disponível. Veja em ⚙ › Atualizações.")
        if not hasattr(self, "_update_banner_btn"):
            self._update_banner_btn = ctk.CTkButton(
                self.setup_banner, text="Atualizar", width=110, height=32, corner_radius=R(8),
                fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._open_update_tab,
            )
        self.setup_btn.pack_forget()
        self._update_banner_btn.pack(side="right", padx=(0, 14))
        self.setup_banner.pack(fill="x", pady=(0, 10), before=self.tabs)

    def _open_update_tab(self):
        self._show_window()
        self.tabs.set("⚙")

    def install_update(self):
        info = self.update_info
        if not info:
            return
        if not installed_with_setup() or not info.get("url"):
            # rodando pelo código-fonte ou versão portátil: abre a página de download
            webbrowser.open(info.get("page") or RELEASES_PAGE)
            return
        if self.busy:
            if not messagebox.askyesno(
                "Atualizar", "Há um download em andamento. Ele será interrompido. Continuar?"):
                return
        if not messagebox.askyesno(
            "Atualizar",
            f"Baixar e instalar a versão {info['version']}?\n\nO programa vai fechar durante a "
            "instalação e abrir de novo sozinho. Seu histórico e suas configurações são mantidos.",
        ):
            return
        self.updating_app = True
        self.btn_install_update.configure(state="disabled", text="Baixando...")
        self.btn_check_update.configure(state="disabled")
        self.update_progress.set(0)
        self.update_progress.pack(fill="x", padx=16, pady=(8, 0), before=self.btn_check_update.master)

        def progress(done, total):
            self.events.put(("update_progress", done, total))

        def work():
            try:
                path = download_update(info, progress)
                self.events.put(("update_ready", path, None))
            except Exception as e:  # noqa: BLE001
                self.events.put(("update_ready", None, str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_progress(self, done, total):
        if total:
            self.update_progress.set(done / total)
            self.btn_install_update.configure(text=f"Baixando... {int(done * 100 / total)}%")

    def _on_update_ready(self, path, error):
        if error or not path:
            self.updating_app = False
            self.update_progress.pack_forget()
            self.btn_install_update.configure(state="normal", text="⬇ Baixar e instalar")
            self.btn_check_update.configure(state="normal")
            messagebox.showerror("Atualizar", "Não foi possível baixar a atualização.\n\n" + str(error)[:300])
            return
        self.btn_install_update.configure(text="Instalando...")
        try:
            # /SILENT: mostra só o progresso; o instalador fecha e reabre o programa sozinho
            subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"],
                             close_fds=True)
        except Exception as e:  # noqa: BLE001
            self.updating_app = False
            messagebox.showerror("Atualizar", f"Não foi possível iniciar o instalador.\n\n{e}")
            return
        self.busy = False
        self._quit()

    # ---------- Bandeja do sistema ----------
    def _on_close(self):
        if self.minimize_to_tray and pystray is not None:
            self._hide_to_tray()
        else:
            self._quit()

    def _start_tray(self):
        if pystray is None:
            return
        try:
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Abrir Baixador de Vídeos",
                    lambda icon, item: self.events.put(("tray", "show")),
                    default=True,
                ),
                pystray.MenuItem("Sair", lambda icon, item: self.events.put(("tray", "quit"))),
            )
            self.tray = pystray.Icon(
                "BaixadorDeVideos", arte.make_icon(64), "Baixador de Vídeos", menu
            )
            self.tray.run_detached()
        except Exception:  # noqa: BLE001
            self.tray = None

    def _stop_tray(self):
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:  # noqa: BLE001
                pass
            self.tray = None

    def _hide_to_tray(self):
        if self.tray is None:
            self._start_tray()
        if self.tray is None:  # não foi possível criar o ícone: fecha normalmente
            self._quit()
            return
        self.withdraw()
        if not self._tray_notified:
            self._tray_notified = True
            try:
                self.tray.notify(
                    "O programa continua rodando aqui. Clique no ícone para abrir.",
                    "Baixador de Vídeos",
                )
            except Exception:  # noqa: BLE001
                pass

    def _show_window(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _quit(self):
        if self.busy:
            self._show_window()
            if not messagebox.askyesno(
                "Sair", "Há uma tarefa em andamento. Deseja sair mesmo assim?"
            ):
                return
        self.cancel_flag.set()
        self._stop_tray()
        if self.bridge is not None:
            self.bridge.stop()
        self._player_close()
        self.destroy()

    # ---------- Aba Player ----------
    def _build_player_tab(self, tab):
        top = self._card(tab)
        top.pack(fill="both", expand=True, pady=(8, 10))

        head = ctk.CTkFrame(top, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 6))
        self.player_title = ctk.CTkLabel(
            head, text="Nenhum vídeo tocando", anchor="w", justify="left", wraplength=520,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.player_title.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            head, text="Abrir arquivo...", width=120, height=30, corner_radius=R(8),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
            command=self.player_open_file,
        ).pack(side="right")

        # área do vídeo (o libmpv desenha dentro deste quadro)
        holder = ctk.CTkFrame(top, fg_color="#000000", corner_radius=R(10))
        holder.pack(fill="both", expand=True, padx=16)
        self.video_frame = tk.Frame(holder, bg="#000000", height=300, highlightthickness=0, bd=0)
        self.video_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.video_msg = tk.Label(
            self.video_frame, bg="#000000", fg="#9ca3af", justify="center",
            text="Escolha um vídeo da lista abaixo para assistir.", font=("Segoe UI", 11),
        )
        self.video_msg.place(relx=0.5, rely=0.5, anchor="center")
        self.video_frame.bind("<Double-Button-1>", lambda e: self.player_fullscreen())

        # barra de tempo
        seek_row = ctk.CTkFrame(top, fg_color="transparent")
        seek_row.pack(fill="x", padx=16, pady=(10, 0))
        self.time_label = ctk.CTkLabel(seek_row, text="00:00 / 00:00", text_color=MUTED, width=110)
        self.time_label.pack(side="right", padx=(8, 0))
        self.seek_slider = ctk.CTkSlider(
            seek_row, from_=0, to=1000, number_of_steps=1000, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, progress_color=ACCENT, command=self._on_seek_drag,
        )
        self.seek_slider.set(0)
        self.seek_slider.pack(side="left", fill="x", expand=True)
        self.seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "_player_seeking", True))
        self.seek_slider.bind("<ButtonRelease-1>", self._on_seek_release)

        # botões
        ctrl = ctk.CTkFrame(top, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(8, 14))
        btn = dict(width=44, height=36, corner_radius=R(10), fg_color=CARD_2,
                   hover_color=CARD_2_HOVER, text_color=TEXT, font=ctk.CTkFont(size=15))
        ctk.CTkButton(ctrl, text="⏮", command=lambda: self.player_step(-1), **btn).pack(side="left")
        ctk.CTkButton(ctrl, text="↺10", command=lambda: self.player_seek_rel(-10),
                      **dict(btn, width=52, font=ctk.CTkFont(size=13))).pack(side="left", padx=(6, 0))
        self.play_btn = ctk.CTkButton(
            ctrl, text="▶", width=64, height=36, corner_radius=R(10), fg_color=ACCENT,
            hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=16, weight="bold"),
            command=self.player_toggle,
        )
        self.play_btn.pack(side="left", padx=(6, 0))
        ctk.CTkButton(ctrl, text="10↻", command=lambda: self.player_seek_rel(10),
                      **dict(btn, width=52, font=ctk.CTkFont(size=13))).pack(side="left", padx=(6, 0))
        ctk.CTkButton(ctrl, text="⏭", command=lambda: self.player_step(1), **btn).pack(side="left", padx=(6, 0))

        ctk.CTkButton(ctrl, text="⛶ Tela cheia", width=110, command=self.player_fullscreen,
                      **{k: v for k, v in btn.items() if k != "width"}).pack(side="right")
        self.speed_var = ctk.StringVar(value="1x")
        ctk.CTkOptionMenu(
            ctrl, variable=self.speed_var, values=["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x"],
            width=78, height=36, corner_radius=R(10), fg_color=CARD_2, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_2, dropdown_text_color=TEXT,
            text_color=TEXT, command=self._on_speed,
        ).pack(side="right", padx=(0, 8))
        self.volume_slider = ctk.CTkSlider(
            ctrl, from_=0, to=100, width=110, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            progress_color=ACCENT, command=self._on_volume,
        )
        self.volume_slider.set(int(load_settings().get("player_volume", 80)))
        self.volume_slider.pack(side="right", padx=(0, 8))
        self.mute_btn = ctk.CTkButton(ctrl, text="🔊", command=self.player_mute, **btn)
        self.mute_btn.pack(side="right", padx=(0, 4))
        self.loop_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ctrl, text="Repetir", variable=self.loop_var, command=self._on_loop,
                        text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        width=80).pack(side="right", padx=(0, 10))

        # biblioteca: vídeos baixados
        lib = self._card(tab)
        lib.pack(fill="x", pady=(0, 4))
        lrow = ctk.CTkFrame(lib, fg_color="transparent")
        lrow.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(lrow, text="Seus vídeos", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.player_filter = ctk.StringVar()
        ctk.CTkEntry(
            lrow, textvariable=self.player_filter, height=32, width=240, corner_radius=R(10),
            border_width=ENTRY_BORDER, border_color=LINE, fg_color=CARD_2,
            placeholder_text="Filtrar...",
        ).pack(side="right")
        self.player_filter.trace_add("write", lambda *a: self._render_player_list())
        self.player_list = ctk.CTkScrollableFrame(lib, fg_color="transparent", height=190)
        self.player_list.pack(fill="x", padx=8, pady=(0, 10))
        self._render_player_list()
        self.after(250, self._player_poll)

    def _player_items(self):
        query = self.player_filter.get().strip().lower() if hasattr(self, "player_filter") else ""
        items = []
        for h in self.history:
            path = h.get("path")
            if not path or not os.path.exists(path):
                continue
            if query and query not in f"{h.get('title', '')} {h.get('uploader', '')}".lower():
                continue
            items.append(h)
        return items

    def _render_player_list(self):
        if not hasattr(self, "player_list"):
            return
        for w in self._player_list_widgets:
            try:
                w.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._player_list_widgets = []
        items = self._player_items()
        if not items:
            lbl = ctk.CTkLabel(
                self.player_list, bg_color=CARD, text_color=MUTED,
                text=("Nenhum vídeo baixado encontrado. Os vídeos que você baixar "
                      "aparecem aqui para assistir."),
            )
            lbl.pack(pady=16)
            self._player_list_widgets.append(lbl)
            return
        current = (self.player_item or {}).get("path")
        for h in items[:60]:
            playing = h.get("path") == current
            row = ctk.CTkFrame(self.player_list, fg_color=CARD_2 if playing else "transparent",
                               corner_radius=R(10), bg_color=CARD)
            row.pack(fill="x", pady=2)
            self._player_list_widgets.append(row)
            title = h.get("title") or os.path.basename(h.get("path", ""))
            if len(title) > 70:
                title = title[:67] + "..."
            meta = "  •  ".join(x for x in (h.get("uploader") or "", h.get("duration") or "",
                                             quality_text(h)) if x)
            ctk.CTkButton(
                row, text="⏸" if playing else "▶", width=38, height=32, corner_radius=R(8),
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                command=lambda e=h: self.play_entry(e),
            ).pack(side="left", padx=(8, 10), pady=6)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(txt, text=title, anchor="w", text_color=ACCENT_TEXT if playing else TEXT,
                         font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", fill="x")
            ctk.CTkLabel(txt, text=meta, anchor="w", text_color=MUTED,
                         font=ctk.CTkFont(size=11)).pack(anchor="w", fill="x")

    # --- controle do libmpv ---
    def _ensure_player(self):
        if self.player is not None:
            return True
        m = load_mpv()
        if m is None:
            self._player_unavailable()
            return False
        try:
            self.video_frame.update_idletasks()
            self.player = self._new_mpv(m, self.video_frame, fullscreen=False)
        except Exception as e:  # noqa: BLE001
            self.player = None
            messagebox.showerror("Player", f"Não foi possível iniciar o player.\n\n{e}")
            return False
        self.video_msg.place_forget()
        return True

    def _new_mpv(self, m, frame, fullscreen):
        p = m.MPV(
            wid=str(int(frame.winfo_id())),
            osc=fullscreen,
            input_default_bindings=True,
            input_vo_keyboard=True,
            keep_open="yes",
            idle="yes",
            hwdec="auto-safe",
            ytdl=False,
        )
        p.volume = float(self.volume_slider.get())
        try:
            p.speed = float(self.speed_var.get().rstrip("x"))
        except Exception:  # noqa: BLE001
            pass
        if fullscreen:
            for key in ("ESC", "f", "MBTN_LEFT_DBL"):
                try:
                    p.on_key_press(key)(lambda: self.events.put(("player_exit_fs",)))
                except Exception:  # noqa: BLE001
                    pass
        return p

    def _player_unavailable(self):
        if self._mpv_failed or mpv_dir() is not None:
            text = ("O player do aplicativo não pôde ser carregado. O vídeo vai abrir "
                    "no player do Windows.")
        else:
            text = ("O player precisa de um componente (cerca de 30 MB), baixado "
                    "automaticamente. Aguarde a faixa de preparação no topo terminar.")
            self._maybe_setup()
        self.video_msg.configure(text=text)
        self.video_msg.place(relx=0.5, rely=0.5, anchor="center")

    def _active_player(self):
        return self.player_fs_player if self.player_fs is not None else self.player

    def play_entry(self, h):
        path = h.get("path")
        if not path or not os.path.exists(path):
            messagebox.showwarning(
                "Arquivo não encontrado",
                "Esse arquivo foi movido ou apagado. Use \"Baixar de novo\" para baixá-lo outra vez.",
            )
            return
        self.tabs.set("▶ Player")
        self.player_item = h
        self.player_title.configure(text=h.get("title") or os.path.basename(path))
        if not self._ensure_player():
            if self._mpv_failed or mpv_dir() is not None:
                self.hist_open(h)
            return
        try:
            self.player.loop_file = "inf" if self.loop_var.get() else "no"
            self.player.play(path)
            self.player.pause = False
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Player", f"Não foi possível tocar o arquivo.\n\n{e}")
        self._render_player_list()

    def player_open_file(self):
        exts = " ".join("*" + e for e in VIDEO_EXTS)
        path = filedialog.askopenfilename(
            title="Escolha um vídeo ou áudio",
            filetypes=[("Vídeos e áudios", exts), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.play_entry({"path": path, "title": os.path.basename(path)})

    def player_toggle(self):
        p = self._active_player()
        if p is None:
            items = self._player_items()
            if items:
                self.play_entry(items[0])
            return
        try:
            if p.idle_active and self.player_item:
                p.play(self.player_item["path"])
                p.pause = False
            else:
                p.pause = not p.pause
        except Exception:  # noqa: BLE001
            pass

    def player_seek_rel(self, seconds):
        p = self._active_player()
        if p is None:
            return
        try:
            p.seek(seconds, reference="relative")
        except Exception:  # noqa: BLE001
            pass

    def player_step(self, delta):
        items = self._player_items()
        if not items:
            return
        current = (self.player_item or {}).get("path")
        idx = next((i for i, h in enumerate(items) if h.get("path") == current), -1)
        nxt = items[(idx + delta) % len(items)] if idx >= 0 else items[0]
        self.play_entry(nxt)

    def player_mute(self):
        p = self._active_player()
        if p is None:
            return
        try:
            p.mute = not p.mute
            self.mute_btn.configure(text="🔇" if p.mute else "🔊")
        except Exception:  # noqa: BLE001
            pass

    def _on_volume(self, value):
        update_settings(player_volume=int(value))
        for p in (self.player, getattr(self, "player_fs_player", None)):
            if p is not None:
                try:
                    p.volume = float(value)
                except Exception:  # noqa: BLE001
                    pass

    def _on_speed(self, value):
        for p in (self.player, getattr(self, "player_fs_player", None)):
            if p is not None:
                try:
                    p.speed = float(value.rstrip("x"))
                except Exception:  # noqa: BLE001
                    pass

    def _on_loop(self):
        for p in (self.player, getattr(self, "player_fs_player", None)):
            if p is not None:
                try:
                    p.loop_file = "inf" if self.loop_var.get() else "no"
                except Exception:  # noqa: BLE001
                    pass

    def _on_seek_drag(self, value):
        p = self._active_player()
        if p is None:
            return
        try:
            dur = p.duration or 0
            self.time_label.configure(text=f"{fmt_clock(dur * value / 1000)} / {fmt_clock(dur)}")
        except Exception:  # noqa: BLE001
            pass

    def _on_seek_release(self, _event=None):
        self._player_seeking = False
        p = self._active_player()
        if p is None:
            return
        try:
            dur = p.duration or 0
            if dur > 0:
                p.seek(dur * self.seek_slider.get() / 1000, reference="absolute")
        except Exception:  # noqa: BLE001
            pass

    def _player_poll(self):
        p = self._active_player()
        if p is not None:
            try:
                pos = p.time_pos
                dur = p.duration
                if self._pending_seek is not None and dur:
                    p.seek(self._pending_seek, reference="absolute")
                    self._pending_seek = None
                if not self._player_seeking:
                    self.time_label.configure(text=f"{fmt_clock(pos)} / {fmt_clock(dur)}")
                    self.seek_slider.set(int(1000 * (pos or 0) / dur) if dur else 0)
                paused = bool(p.pause) or bool(p.idle_active)
                self.play_btn.configure(text="▶" if paused else "⏸")
            except Exception:  # noqa: BLE001
                pass
        self.after(250, self._player_poll)

    # --- tela cheia: recria o player numa janela própria e continua do mesmo ponto ---
    def player_fullscreen(self):
        if self.player_fs is not None:
            self._exit_fullscreen()
            return
        if self.player is None or not self.player_item:
            return
        m = load_mpv()
        if m is None:
            return
        try:
            pos = self.player.time_pos or 0
            paused = bool(self.player.pause)
            self.player.pause = True
        except Exception:  # noqa: BLE001
            pos, paused = 0, False
        win = tk.Toplevel(self)
        win.configure(bg="#000000")
        win.attributes("-fullscreen", True)
        frame = tk.Frame(win, bg="#000000")
        frame.pack(fill="both", expand=True)
        win.update_idletasks()
        win.bind("<Escape>", lambda e: self._exit_fullscreen())
        win.protocol("WM_DELETE_WINDOW", self._exit_fullscreen)
        try:
            fsp = self._new_mpv(m, frame, fullscreen=True)
            fsp.loop_file = "inf" if self.loop_var.get() else "no"
            fsp.play(self.player_item["path"])
            fsp.pause = paused
        except Exception as e:  # noqa: BLE001
            win.destroy()
            messagebox.showerror("Player", f"Não foi possível abrir a tela cheia.\n\n{e}")
            return
        self.player_fs = win
        self.player_fs_player = fsp
        self._pending_seek = pos

    def _exit_fullscreen(self):
        if self.player_fs is None:
            return
        fsp = self.player_fs_player
        try:
            pos = fsp.time_pos or 0
            paused = bool(fsp.pause)
        except Exception:  # noqa: BLE001
            pos, paused = 0, False
        try:
            fsp.terminate()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.player_fs.destroy()
        except Exception:  # noqa: BLE001
            pass
        self.player_fs = None
        self.player_fs_player = None
        if self.player is not None:
            try:
                self.player.seek(pos, reference="absolute")
                self.player.pause = paused
            except Exception:  # noqa: BLE001
                pass

    def _player_close(self):
        try:
            if self.player_fs is not None:
                self._exit_fullscreen()
        except Exception:  # noqa: BLE001
            pass
        if self.player is not None:
            try:
                self.player.terminate()
            except Exception:  # noqa: BLE001
                pass
            self.player = None

    # ---------- Aba Histórico ----------
    def _build_history_tab(self, tab):
        top = self._card(tab)
        top.pack(fill="x", pady=(8, 10))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(16, 8))
        self.hist_count = ctk.CTkLabel(
            row, text="Histórico", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.hist_count.pack(side="left")
        ctk.CTkButton(
            row, text="Limpar histórico", width=140, height=34, corner_radius=R(10),
            fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT, command=self.clear_history,
        ).pack(side="right")
        self.hist_filter_var = ctk.StringVar()
        ctk.CTkEntry(
            top, textvariable=self.hist_filter_var, height=40, corner_radius=R(12),
            border_width=ENTRY_BORDER, border_color=LINE, fg_color=CARD_2,
            placeholder_text="Filtrar por título ou canal...",
        ).pack(fill="x", padx=16, pady=(0, 16))
        self.hist_filter_var.trace_add("write", lambda *a: self._schedule_hist_render())
        self.hist_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.hist_frame.pack(fill="both", expand=True)
        self._render_history()

    def _schedule_hist_render(self):
        if self._hist_job is not None:
            self.after_cancel(self._hist_job)
        self._hist_job = self.after(250, self._filter_changed)

    def _filter_changed(self):
        self._hist_job = None
        self._hist_limit = HISTORY_PAGE
        self._render_history()

    def _hist_more(self):
        self._hist_limit += HISTORY_PAGE
        self._render_history()

    def _render_history(self):
        self._render_player_list()
        self._render_history_items()

    def _render_history_items(self):
        for w in self._hist_widgets:
            try:
                w.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._hist_widgets = []
        query = self.hist_filter_var.get().strip().lower()
        items = [
            h for h in self.history
            if not query or query in f"{h.get('title', '')} {h.get('uploader', '')}".lower()
        ]
        self.hist_count.configure(text=f"Histórico ({len(self.history)})")

        if not items:
            lbl = ctk.CTkLabel(
                self.hist_frame, bg_color=BG, text_color=MUTED, justify="center",
                compound="top",
                image=None if query else self._empty_art,
                text=("Nenhum resultado para esse filtro." if query else
                      "Nenhum download no histórico ainda.\n"
                      "Os vídeos que você baixar aparecerão aqui."),
            )
            lbl.pack(pady=20)
            self._hist_widgets.append(lbl)
            return

        for h in items[:self._hist_limit]:
            self._hist_row(h)
        if len(items) > self._hist_limit:
            btn = ctk.CTkButton(
                self.hist_frame, bg_color=BG, text=f"Mostrar mais ({len(items) - self._hist_limit})",
                height=38, corner_radius=R(10), fg_color=CARD_2, hover_color=CARD_2_HOVER, text_color=TEXT,
                command=self._hist_more,
            )
            btn.pack(pady=10)
            self._hist_widgets.append(btn)

    def _history_thumb(self, h):
        name = h.get("thumb")
        if name:
            try:
                img = Image.open(os.path.join(THUMBS_DIR, name)).convert("RGB")
                return ctk.CTkImage(img, size=(SMALL_W, SMALL_H))
            except Exception:  # noqa: BLE001
                pass
        return self._small_placeholder

    def _hist_row(self, h):
        card = ctk.CTkFrame(self.hist_frame, fg_color=CARD, corner_radius=R(14), bg_color=BG)
        card.pack(fill="x", pady=5, padx=2)
        self._hist_widgets.append(card)

        ctk.CTkLabel(
            card, text="", image=self._history_thumb(h), width=SMALL_W, height=SMALL_H
        ).pack(side="left", padx=12, pady=12)

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=12, pady=10)
        ctk.CTkButton(
            right, text="↻ Baixar de novo", width=150, height=32, corner_radius=R(10),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=lambda e=h: self.redownload(e),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 6))
        small = dict(width=72, height=28, corner_radius=R(8), fg_color=CARD_2,
                     hover_color=CARD_2_HOVER, text_color=TEXT, font=ctk.CTkFont(size=12))
        ctk.CTkButton(right, text="Qualidade", command=lambda e=h: self.hist_pick_quality(e),
                      **small).grid(row=1, column=0, padx=(0, 3), pady=(0, 4))
        ctk.CTkButton(right, text="▶ Assistir", command=lambda e=h: self.play_entry(e),
                      **small).grid(row=1, column=1, padx=(3, 0), pady=(0, 4))
        ctk.CTkButton(right, text="Pasta", command=lambda e=h: self.hist_folder(e),
                      **small).grid(row=2, column=0, padx=(0, 3))
        ctk.CTkButton(
            right, text="Remover", width=72, height=28, corner_radius=R(8),
            fg_color="transparent", hover_color=REMOVE_HOVER, text_color=ERROR,
            font=ctk.CTkFont(size=12), command=lambda e=h: self.hist_remove(e),
        ).grid(row=2, column=1, padx=(3, 0))

        mid = ctk.CTkFrame(card, fg_color="transparent")
        mid.pack(side="left", fill="both", expand=True)
        title = h.get("title") or "Sem título"
        if len(title) > 90:
            title = title[:87] + "..."
        ctk.CTkLabel(
            mid, text=title, anchor="w", justify="left", wraplength=280,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", fill="x", pady=(14, 2))
        who = "  •  ".join(p for p in (h.get("uploader") or "", h.get("duration") or "") if p)
        if who:
            ctk.CTkLabel(
                mid, text=who, anchor="w", justify="left", wraplength=280,
                text_color=MUTED, font=ctk.CTkFont(size=12),
            ).pack(anchor="w", fill="x")
        parts = [h.get("date") or "", quality_text(h)]
        if h.get("size"):
            parts.append(fmt_bytes(h["size"]))
        ctk.CTkLabel(
            mid, text="  •  ".join(p for p in parts if p), anchor="w", justify="left",
            wraplength=280, text_color=MUTED, font=ctk.CTkFont(size=12),
        ).pack(anchor="w", fill="x")
        exists = bool(h.get("path")) and os.path.exists(h["path"])
        ctk.CTkLabel(
            mid, anchor="w", font=ctk.CTkFont(size=11),
            text="✔ Arquivo no computador" if exists
            else "Arquivo não encontrado (movido ou apagado)",
            text_color=SUCCESS if exists else WARN,
        ).pack(anchor="w", fill="x", pady=(2, 0))

    def _on_download_done(self, ctx):
        """Registra o download concluído no histórico."""
        try:
            path = ctx.get("path")
            entry = {
                "id": str(int(time.time() * 1000)),
                "url": ctx["url"],
                "title": ctx.get("title") or "Sem título",
                "uploader": ctx.get("uploader") or "",
                "duration": fmt_duration(ctx.get("duration")),
                "quality": ctx.get("quality"),
                "height": ctx.get("height"),
                "compat": bool(ctx.get("compat")),
                "section": ctx.get("section"),
                "subs": ctx.get("subs") or "",
                "path": path,
                "size": os.path.getsize(path) if path and os.path.exists(path) else 0,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "thumb": None,
            }
            pil = ctx.get("thumb")
            if pil is not None:
                os.makedirs(THUMBS_DIR, exist_ok=True)
                name = entry["id"] + ".jpg"
                ImageOps.fit(pil, (SMALL_W * 2, SMALL_H * 2)).save(
                    os.path.join(THUMBS_DIR, name), quality=85
                )
                entry["thumb"] = name
            self.history.insert(0, entry)
            for old in self.history[HISTORY_MAX:]:
                self._delete_thumb(old)
            self.history = self.history[:HISTORY_MAX]
            save_history(self.history)
            self._render_history()
            self._notify("Download concluído", entry["title"])
        except Exception:  # noqa: BLE001
            pass

    def _delete_thumb(self, h):
        name = h.get("thumb")
        if name:
            try:
                os.remove(os.path.join(THUMBS_DIR, name))
            except OSError:
                pass

    def redownload(self, h):
        """Baixa de novo, já com a mesma qualidade (e opções) de antes."""
        if self.busy:
            messagebox.showinfo(
                "Aguarde", "Espere a tarefa atual terminar para iniciar outra."
            )
            return
        sec = h.get("section")
        if sec:
            HelpDialog(
                self, "Baixar de novo",
                f"Este download foi só um trecho ({section_text(sec)}). O que você quer "
                "baixar agora?", None,
                [(f"Só o trecho ({section_text(sec)})",
                  lambda: self._redownload(h, sec), True, True),
                 ("O vídeo inteiro", lambda: self._redownload(h, None), False, True)],
                self.ico_path,
            )
            return
        self._redownload(h, None)

    def _redownload(self, h, section):
        self.url_var.set(h["url"])
        self.pending_quality = h.get("quality")
        self.pending_section = section
        self.pending_compat = bool(h.get("compat"))
        self.pending_sub = h.get("subs") or None
        self.auto_download = True
        self.tabs.set("Baixar")
        self.analyze()

    def hist_pick_quality(self, h):
        """Abre o vídeo na aba Baixar para escolher a qualidade."""
        if self.busy:
            messagebox.showinfo(
                "Aguarde", "Espere a tarefa atual terminar para iniciar outra."
            )
            return
        self.url_var.set(h["url"])
        self.pending_quality = None
        self.pending_section = self.pending_compat = self.pending_sub = None
        self.auto_download = False
        self.tabs.set("Baixar")
        self.analyze()

    def hist_open(self, h):
        path = h.get("path")
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Erro", str(e))
        else:
            messagebox.showwarning(
                "Arquivo não encontrado",
                "Esse arquivo foi movido ou apagado. Use \"Baixar de novo\" para "
                "baixá-lo outra vez.",
            )

    def hist_folder(self, h):
        path = h.get("path")
        try:
            if path and os.path.exists(path):
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            elif path and os.path.isdir(os.path.dirname(path)):
                os.startfile(os.path.dirname(path))
            else:
                messagebox.showwarning(
                    "Pasta não encontrada", "A pasta deste download não existe mais."
                )
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Erro", str(e))

    def hist_remove(self, h):
        self.history = [x for x in self.history if x.get("id") != h.get("id")]
        self._delete_thumb(h)
        save_history(self.history)
        self._render_history()

    def clear_history(self):
        if not self.history:
            return
        if messagebox.askyesno(
            "Limpar histórico",
            "Apagar todo o histórico de downloads?\n\n"
            "Os arquivos baixados continuam no computador.",
        ):
            for h in self.history:
                self._delete_thumb(h)
            self.history = []
            save_history(self.history)
            self._render_history()

    # ---------- Ações ----------
    def paste(self):
        try:
            text = self.clipboard_get().strip()
        except Exception:  # noqa: BLE001
            return
        if text:
            self.url_var.set(text)
            self.analyze()  # já analisa ao colar

    def choose_folder(self):
        d = filedialog.askdirectory(initialdir=self.folder_var.get())
        if d:
            self.folder_var.set(d)

    def open_folder(self):
        folder = self.folder_var.get()
        os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    def set_busy(self, busy):
        self.busy = busy
        self.btn_analyze.configure(state="disabled" if busy else "normal")
        self.btn_cancel.configure(state="normal" if busy else "disabled")

    def _set_progress_mode(self, indeterminate):
        self.progress.stop()
        self._indet = bool(indeterminate)
        if indeterminate:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
        else:
            self.progress.configure(mode="determinate")
            self.progress.set(0)

    def _on_cookie_choice(self, choice):
        if choice == COOKIE_FILE:
            path = filedialog.askopenfilename(
                title="Escolha o arquivo cookies.txt",
                filetypes=[("cookies.txt", "*.txt"), ("Todos os arquivos", "*.*")],
            )
            if path:
                self.cookie_file = path
            else:
                choice = COOKIE_AUTO
                self.cookie_var.set(COOKIE_AUTO)
        self._persist_cookie_choice(choice)

    def _cookie_attempts(self):
        """Lista de tentativas (opções extras do yt-dlp) conforme a escolha do usuário."""
        mode = self.cookie_var.get()
        if mode == COOKIE_NONE:
            return [{}]
        if mode == COOKIE_FILE:
            return [{"cookiefile": self.cookie_file}] if self.cookie_file else [{}]
        if mode == COOKIE_AUTO:
            attempts = [{}]
            if self.cookie_file and os.path.exists(self.cookie_file):
                attempts.append({"cookiefile": self.cookie_file})
            attempts += [
                {"cookiesfrombrowser": (b,)}
                for b in BROWSER_ORDER if not browser_protected(b)
            ]
            return attempts
        return [{"cookiesfrombrowser": (mode.lower(),)}]

    def _persist_cookie_choice(self, choice):
        cfg = load_settings()
        cfg["cookie_choice"] = choice
        cfg["cookie_file"] = self.cookie_file
        save_settings(cfg)

    def _reset_after_failure(self):
        self._set_progress_mode(indeterminate=False)
        self.set_busy(False)
        self.auto_download = False
        self.btn_download.configure(state="disabled")
        self.title_label.configure(text="Nenhum vídeo carregado")
        self.meta_label.configure(text="")
        self.thumb_label.configure(image=self._placeholder, text="")

    def _on_login_help(self, kind, url, detail):
        self._reset_after_failure()
        self.status_label.configure(
            text="É preciso um login válido para baixar este vídeo.", text_color=WARN
        )
        if kind == "protected":
            title, message = "O login do navegador não pôde ser lido", PROTECTED_TEXT
            buttons = [
                ("1. Instalar a extensão que exporta o cookies.txt",
                 lambda: webbrowser.open(EXT_URL), False, False),
                ("2. Escolher o cookies.txt que eu exportei",
                 lambda: self._use_cookie_file(url), True, True),
                ("3. Usar o Firefox (entrar no YouTube por ele)",
                 lambda: self._use_firefox(), False, True),
            ]
        else:
            title, message = "Este vídeo exige login", LOGIN_TEXT
            buttons = [
                ("Escolher um arquivo cookies.txt",
                 lambda: self._use_cookie_file(url), True, True),
                ("Instalar a extensão que exporta o cookies.txt",
                 lambda: webbrowser.open(EXT_URL), False, False),
            ]
        HelpDialog(self, title, message, (detail or "")[:160], buttons, self.ico_path)

    def _use_cookie_file(self, url):
        path = filedialog.askopenfilename(
            title="Escolha o arquivo cookies.txt",
            filetypes=[("cookies.txt", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return
        self.cookie_file = path
        self.cookie_var.set(COOKIE_FILE)
        self._persist_cookie_choice(COOKIE_FILE)
        self.url_var.set(url)
        self.analyze()

    def _use_firefox(self):
        self.cookie_var.set("Firefox")
        self._persist_cookie_choice("Firefox")
        if firefox_available():
            messagebox.showinfo(
                "Firefox",
                "Certifique-se de estar logado no YouTube pelo Firefox, com uma conta "
                "que possa ver o vídeo, e clique em Analisar.",
            )
        else:
            webbrowser.open(FIREFOX_URL)
            messagebox.showinfo(
                "Firefox",
                "Instale o Firefox, entre no YouTube por ele (com uma conta que possa "
                "ver o vídeo) e depois clique em Analisar.",
            )

    def _on_cookie_locked(self, browser, url):
        name = BROWSER_NAMES.get(browser, browser)
        self._set_progress_mode(indeterminate=False)
        self.set_busy(False)
        self.btn_download.configure(state="disabled")
        self.title_label.configure(text="Nenhum vídeo carregado")
        self.meta_label.configure(text="")
        self.thumb_label.configure(image=self._placeholder, text="")

        if url in self._lock_retried:
            self.auto_download = False
            self.status_label.configure(
                text="Não foi possível ler o login do navegador.", text_color=ERROR
            )
            messagebox.showerror(
                "Erro",
                f"Mesmo com o {name} fechado não foi possível ler o login. O navegador "
                "pode estar usando uma proteção nova nos cookies.\n\n"
                'Use a opção "Arquivo cookies.txt..." em Login do navegador.',
            )
            return

        self.status_label.configure(
            text=f"O {name} precisa estar fechado para o app ler o login.",
            text_color=WARN,
        )
        ok = messagebox.askyesno(
            f"Fechar o {name}?",
            f"O Windows bloqueia o arquivo de login do {name} enquanto ele está aberto "
            f"(inclusive em segundo plano).\n\nDeseja que eu feche o {name} agora e "
            "tente de novo?\n\nSalve o que estiver fazendo nele antes. Suas abas "
            "podem ser reabertas depois com Ctrl+Shift+T.",
        )
        if not ok:
            self.auto_download = False
            self.status_label.configure(
                text=f"Feche o {name} e clique em Analisar novamente.", text_color=MUTED
            )
            return
        self._lock_retried.add(url)
        self._close_browser(browser)
        self.status_label.configure(
            text=f"Fechando o {name} e tentando de novo...", text_color=MUTED
        )
        self.after(2000, lambda: self._retry_analyze(url))

    def _close_browser(self, browser):
        exe = BROWSER_EXE.get(browser)
        if not exe:
            return
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", exe], capture_output=True,
                creationflags=0x08000000,  # sem abrir janela de console
            )
        except Exception:  # noqa: BLE001
            pass

    def _retry_analyze(self, url):
        self.url_var.set(url)
        self.analyze()

    def analyze(self):
        url = self.url_var.get().strip()
        if not url or self.busy:
            return
        self._analyzing_url = url
        self.set_busy(True)
        self.btn_cancel.configure(state="disabled")
        self.btn_download.configure(state="disabled")
        self.quality_menu.configure(state="disabled")
        self.video_info = None
        self._sub_map = {}
        self.sub_var.set(SUBS_NONE)
        self.btn_thumb.configure(state="disabled")
        self._refresh_options()
        self.title_label.configure(text="Carregando...")
        self.meta_label.configure(text="")
        self.thumb_label.configure(image=self._placeholder, text="")
        self.status_label.configure(text="Analisando o link...", text_color=MUTED)
        self._set_progress_mode(indeterminate=True)
        attempts = self._cookie_attempts()
        threading.Thread(
            target=self._analyze_worker, args=(url, attempts), daemon=True
        ).start()

    def _analyze_worker(self, url, attempts):
        login_needed = False
        cookies_read = False
        login_msg = ""
        last_msg = ""
        locked = None  # navegador cujo arquivo de login está bloqueado (aberto)
        decrypt_msg = ""
        for i, extra in enumerate(attempts):
            if i > 0 and not login_needed:
                break
            browser = (extra.get("cookiesfrombrowser") or (None,))[0]
            if i > 0:
                name = BROWSER_NAMES.get(browser, "arquivo cookies.txt")
                self.events.put(
                    ("status", f"Vídeo com restrição: tentando o login do {name}...")
                )
            logger = QuietLogger()
            opts = {"quiet": True, "no_warnings": True, "no_color": True,
                    "noplaylist": True, "logger": logger, "skip_download": True,
                    **self.js_opts, **extra}
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                heights = sorted(
                    {f["height"] for f in info.get("formats", [])
                     if f.get("height") and f.get("vcodec") != "none"},
                    reverse=True,
                )
                thumb = fetch_thumbnail(info)
                self.events.put(("analyzed", info, heights, thumb, extra))
                return
            except Exception as e:  # noqa: BLE001
                last_msg = clean_msg(logger.last_error or str(e))
                if browser and is_cookie_locked(last_msg):
                    locked = locked or browser
                elif extra and is_decrypt_fail(last_msg):
                    if browser:
                        mark_broken(browser)
                    decrypt_msg = decrypt_msg or last_msg
                elif needs_login(last_msg):
                    login_needed = True
                    login_msg = login_msg or last_msg
                    if extra:
                        cookies_read = True
        if locked and not browser_protected(locked):
            self.events.put(("cookie_locked", locked, url))
        elif locked or decrypt_msg:
            self.events.put(("login_help", "protected", url, decrypt_msg or last_msg))
        elif login_needed:
            kind = "login" if (cookies_read or len(attempts) == 1) else "protected"
            self.events.put(("login_help", kind, url, login_msg))
        else:
            log_error(url, last_msg)
            self.events.put(("error", f"Não foi possível analisar o link.\n{last_msg}"))

    def start_download(self):
        if self.busy or not self.video_info:
            return
        folder = self.folder_var.get().strip()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Pasta inválida", str(e))
            return

        choice = self.quality_var.get()
        section, err = self._read_section()
        if err:
            messagebox.showwarning("Trecho do vídeo", err)
            return
        mode, height = self._current_mode()
        sub_label = self.sub_var.get()
        sub = None
        if not section and sub_label in self._sub_map:
            sub = self._sub_map[sub_label]
        opts = build_download_opts(choice, folder, self.ffmpeg, mode, height, sub, section)
        opts["progress_hooks"] = [self._hook]
        opts["postprocessor_hooks"] = [self._pp_hook]
        opts.update(self.js_opts)
        opts.update(self.active_cookie_opts)

        vi = self.video_info or {}
        ctx = {
            "url": self.video_url or self.url_var.get().strip(),
            "title": vi.get("title") or "Sem título",
            "uploader": vi.get("uploader") or vi.get("channel") or "",
            "duration": vi.get("duration"),
            "quality": choice,
            "thumb": self.current_thumb,
            "mode": mode,
            "compat": mode != "off",
            "section": section,
            "subs": sub_label if sub else "",
        }

        self.cancel_flag.clear()
        self.set_busy(True)
        self.btn_download.configure(state="disabled")
        # trecho: o FFmpeg baixa sem informar o progresso, então a barra fica em movimento
        self._set_progress_mode(indeterminate=bool(section))
        self.status_label.configure(
            text=(f"Baixando o trecho de {section_text(section)}..." if section
                  else "Iniciando download..."), text_color=MUTED)
        threading.Thread(
            target=self._download_worker, args=(opts, ctx), daemon=True
        ).start()

    def _try_plans(self, plans, ctx, state, debug_lines):
        """Tenta as receitas em ordem. Devolve (info, caminho, nota) ou None se falharem."""
        class _YDL(yt_dlp.YoutubeDL):
            def write_debug(self, message, only_once=False):
                debug_lines.append(str(message))  # guarda a saída do FFmpeg

        retried_same = ctx.get("mode") == "recode"  # não repete uma conversão demorada
        i = 0
        while i < len(plans):
            plan, note = plans[i]
            logger = QuietLogger()
            try:
                with _YDL({**plan, "logger": logger}) as ydl:
                    info = ydl.extract_info(ctx["url"], download=True) or {}
                    path = None
                    finished = info.get("requested_downloads") or []
                    if finished:
                        path = finished[0].get("filepath")
                    if not path:
                        path = ydl.prepare_filename(info)
                return info, path, note
            except DownloadCancelled:
                raise
            except Exception as e:  # noqa: BLE001
                if self.cancel_flag.is_set():
                    raise DownloadCancelled()
                msg = clean_msg(logger.last_error or str(e))
                state["attempts"].append(msg)
                if not state["subs_dropped"] and ctx.get("subs") and is_subtitle_error(msg):
                    # a legenda falhou (o YouTube às vezes limita): baixa sem ela
                    state["subs_dropped"] = True
                    plans = [(strip_subs(o), n) for o, n in plans]
                    self.events.put(("status", "Não foi possível baixar a legenda. "
                                               "Baixando o vídeo sem ela..."))
                    continue
                if plan.get("download_ranges"):
                    return None  # trecho direto falhou: vai para o plano B (cortar aqui)
                if is_postprocess_error(msg):
                    if i == 0 and not retried_same:
                        # Falha momentânea (antivírus lendo os arquivos recém-baixados,
                        # por exemplo): espera um pouco e junta de novo. Os arquivos já
                        # baixados são reaproveitados, então é rápido.
                        retried_same = True
                        self.events.put(("status", "A junção dos arquivos falhou. "
                                                   "Tentando de novo em instantes..."))
                        time.sleep(3)
                        if self.cancel_flag.is_set():
                            raise DownloadCancelled()
                        continue
                    if i + 1 < len(plans):
                        self.events.put(("status", "A conversão falhou. Tentando outro formato..."))
                        i += 1
                        continue
                return None
        return None

    def _download_worker(self, opts, ctx):
        mode = ctx.get("mode", "off")
        section = ctx.get("section")
        debug_lines = []
        state = {"attempts": [], "subs_dropped": False}
        tmp_dir = None
        try:
            res = self._try_plans(download_plans(opts, ctx.get("quality"), mode),
                                  ctx, state, debug_lines)
            if res is None and section and self.ffmpeg:
                # Plano B do trecho: baixa o vídeo inteiro numa pasta temporária e corta
                # aqui com o FFmpeg (funciona sempre que o download normal funciona).
                folder = os.path.dirname(opts["outtmpl"])
                os.makedirs(folder, exist_ok=True)
                tmp_dir = tempfile.mkdtemp(prefix=".baixador-trecho-", dir=folder)
                full = {k: v for k, v in opts.items()
                        if k not in ("download_ranges", "force_keyframes_at_cuts")}
                full["outtmpl"] = os.path.join(tmp_dir, "%(title).150B [%(id)s].%(ext)s")
                self.events.put(("indet", False))
                self.events.put(("status", "Não deu para baixar só o trecho direto. Baixando o "
                                           "vídeo para cortar o trecho aqui..."))
                res = self._try_plans(download_plans(full, ctx.get("quality"), mode),
                                      ctx, state, debug_lines)
                if res is not None:
                    info, src, note = res
                    self.events.put(("pp", "Cortando o trecho...", True))
                    res = (info, cut_section_file(self.ffmpeg, src, folder, section), note)
            if res is not None:
                info, path, note = res
                sub_note = NOTE_NO_SUBS if state["subs_dropped"] else None
                notes = [n for n in (note, sub_note) if n]
                self.events.put(("done", {
                    **ctx, "path": path, "height": info.get("height"),
                    "note": "; ".join(notes),
                    "compat": bool(ctx.get("compat")) and note is None,
                    "subs": "" if sub_note else ctx.get("subs", ""),
                }))
                return
        except DownloadCancelled:
            self.events.put(("cancelled",))
            return
        except Exception as e:  # noqa: BLE001  (erro ao cortar o trecho, por exemplo)
            state["attempts"].append(clean_msg(str(e)))
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        attempts = state["attempts"]
        msg = first_real_error(attempts)
        detail = tail_text(debug_lines) if is_postprocess_error(msg) else ""
        log_error(ctx.get("url", ""), msg,
                  "\n".join(f"tentativa {n + 1}: {m[:300]}" for n, m in enumerate(attempts))
                  + ("\n" + detail if detail else ""))
        if needs_login(msg):
            msg = LOGIN_HELP + "\n\nDetalhe: " + msg[:220]
        elif "format is not available" in msg or "Requested format" in msg:
            if not self.has_js:
                msg += ("\n\nDica: o YouTube precisa do Deno instalado. "
                        "Abra o Terminal e rode:\nwinget install DenoLand.Deno\n"
                        "Depois feche e abra o programa de novo.")
            else:
                msg += "\n\nDica: tente outra qualidade na lista."
        elif is_postprocess_error(msg):
            msg += ("\n\nO programa tentou vários formatos e a conversão do vídeo falhou "
                    "em todos. Verifique se o antivírus não está bloqueando o FFmpeg e "
                    "tente outra qualidade na aba Baixar.")
            if detail:
                msg += "\n\nDetalhe do conversor:\n" + detail
        self.events.put(("error", f"Falha no download.\n{msg}"))

    def _hook(self, d):
        if self.cancel_flag.is_set():
            raise DownloadCancelled()
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            speed = d.get("speed")
            eta = d.get("eta")
            if total:
                txt = f"Baixando... {pct:.1f}%   ({fmt_bytes(done)} de {fmt_bytes(total)})"
            else:
                txt = f"Baixando... {fmt_bytes(done)}"
            if speed:
                txt += f"   •   {fmt_bytes(speed)}/s"
            if eta:
                txt += f"   •   faltam {int(eta)}s"
            self.events.put(("progress", pct, txt))
        elif d["status"] == "finished":
            self.events.put(
                ("progress", 100, "Processando arquivo (juntando áudio e vídeo)...")
            )

    def cancel(self):
        if self.busy:
            self.cancel_flag.set()
            self.status_label.configure(text="Cancelando...", text_color=MUTED)

    # ---------- Eventos vindos das threads ----------
    def _poll_events(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "analyzed":
                    self._on_analyzed(ev[1], ev[2], ev[3], ev[4])
                elif kind == "browser_video":
                    self._on_browser_video(ev[1])
                elif kind == "suggest_ready":
                    self._show_suggestion(ev[1])
                elif kind == "suggest_fail":
                    self._probing = False
                    self._suggested[ev[1]] = time.time()
                elif kind == "update_checked":
                    self._on_update_checked(ev[1], ev[2], ev[3])
                elif kind == "update_progress":
                    self._on_update_progress(ev[1], ev[2])
                elif kind == "update_ready":
                    self._on_update_ready(ev[1], ev[2])
                elif kind == "player_exit_fs":
                    self._exit_fullscreen()
                elif kind == "tray":
                    if ev[1] == "show":
                        self._show_window()
                    else:
                        self._quit()
                elif kind == "login_help":
                    self._on_login_help(ev[1], ev[2], ev[3])
                elif kind == "cookie_locked":
                    self._on_cookie_locked(ev[1], ev[2])
                elif kind == "status":
                    self.status_label.configure(text=ev[1], text_color=MUTED)
                elif kind == "indet":
                    self._set_progress_mode(indeterminate=ev[1])
                elif kind == "pp":
                    self.status_label.configure(text=ev[1], text_color=MUTED)
                    if ev[2] and not getattr(self, "_indet", False):
                        self._set_progress_mode(indeterminate=True)
                elif kind == "progress":
                    if not getattr(self, "_indet", False):
                        self.progress.set(ev[1] / 100)
                    self.status_label.configure(text=ev[2], text_color=MUTED)
                elif kind == "done":
                    self.set_busy(False)
                    self.btn_download.configure(state="normal")
                    self._set_progress_mode(indeterminate=False)
                    self.progress.set(1)
                    note = ev[1].get("note")
                    self.status_label.configure(
                        text=(f"✔ Concluído, {note}." if note else "✔ Download concluído!"),
                        text_color=SUCCESS,
                    )
                    self._on_download_done(ev[1])
                elif kind == "thumb_saved":
                    self.btn_thumb.configure(state="normal", text="Salvar thumbnail")
                    w, h = ev[2]
                    self.status_label.configure(
                        text=f"✔ Thumbnail salva ({w}×{h}): {os.path.basename(ev[1])}",
                        text_color=SUCCESS)
                elif kind == "thumb_error":
                    self.btn_thumb.configure(
                        state="normal" if self.video_info else "disabled",
                        text="Salvar thumbnail")
                    self._show_error("Não foi possível salvar a thumbnail.\n" + ev[1][:300])
                elif kind == "cancelled":
                    self.set_busy(False)
                    self.btn_download.configure(state="normal")
                    self.progress.set(0)
                    self._set_progress_mode(indeterminate=False)
                    self.status_label.configure(
                        text="Download cancelado.", text_color=MUTED
                    )
                elif kind == "setup_progress":
                    self._show_banner(ev[1])
                elif kind == "setup_done":
                    self.setting_up = False
                    self.ffmpeg = ensure_ffmpeg_on_path(ffmpeg_location())
                    self.js_opts, self.has_js = js_runtime_opts()
                    missing = self._missing_components()
                    if missing:
                        self._show_banner(
                            "Ainda faltam componentes: " + ", ".join(missing) + "."
                        )
                        self.setup_btn.pack(side="right", padx=(0, 14))
                    else:
                        self._show_banner("✔ Componentes prontos! Já pode baixar.")
                        self.after(3000, self._hide_banner_if_ok)
                elif kind == "setup_error":
                    self.setting_up = False
                    self._show_banner(
                        "Não foi possível baixar os componentes. Verifique sua "
                        "internet e tente de novo.\n" + str(ev[1])[:150]
                    )
                    self.setup_btn.pack(side="right", padx=(0, 14))
                elif kind == "search_results":
                    if ev[1] == self.search_id:
                        self.searching = False
                        self.btn_search.configure(state="normal")
                        self._render_results(ev[2])
                elif kind == "search_thumb":
                    self._on_search_thumb(ev[1], ev[2], ev[3])
                elif kind == "search_error":
                    if ev[1] == self.search_id:
                        self.searching = False
                        self.btn_search.configure(state="normal")
                        self._show_results_status(
                            "Não foi possível pesquisar agora.\n" + str(ev[2])[:300]
                        )
                elif kind == "error":
                    self.auto_download = False
                    self._set_progress_mode(indeterminate=False)
                    self.set_busy(False)
                    self.btn_download.configure(
                        state="normal" if self.video_info else "disabled"
                    )
                    if not self.video_info:
                        self.title_label.configure(text="Nenhum vídeo carregado")
                        self.thumb_label.configure(
                            image=self._placeholder, text=""
                        )
                    self.status_label.configure(
                        text="Ocorreu um erro.", text_color=ERROR
                    )
                    self._show_error(ev[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _on_analyzed(self, info, heights, thumb, cookie_opts):
        self.video_info = info
        self.video_url = self._analyzing_url
        self.current_thumb = thumb
        self.active_cookie_opts = cookie_opts
        self._set_progress_mode(indeterminate=False)
        self.set_busy(False)

        self.title_label.configure(text=info.get("title", "Sem título"))
        uploader = info.get("uploader") or info.get("channel") or ""
        dur = fmt_duration(info.get("duration"))
        self.meta_label.configure(
            text="  •  ".join(p for p in (uploader, dur) if p)
        )

        if thumb is not None:
            img = ctk.CTkImage(thumb, size=(THUMB_W, THUMB_H))
            self.thumb_label.configure(image=img, text="")
            self._thumb_ref = img  # evita o Python descartar a imagem
        else:
            self.thumb_label.configure(image=self._placeholder, text="")

        options = [LABEL_BEST] + [f"{h}p" for h in heights] + [LABEL_AUDIO]
        self.quality_menu.configure(values=options, state="normal")
        self.quality_var.set(LABEL_BEST)
        self.btn_download.configure(state="normal")
        self.btn_thumb.configure(
            state="normal" if best_thumbnail_url(info) else "disabled",
            text="Salvar thumbnail")

        # dados para as opções: versões H.264, legendas e duração (trecho)
        self.video_heights = list(heights)
        self.h264_set, self.codec_known = h264_heights(info)
        self._sub_map = {label: (code, auto) for label, code, auto in subtitle_options(info)}
        self.sub_menu.configure(values=[SUBS_NONE] + list(self._sub_map))
        self.sub_var.set(SUBS_NONE)
        dur = info.get("duration")
        self.trim_var.set(False)
        self.trim_exact_var.set(False)
        self.trim_start_var.set("0:00")
        self.trim_end_var.set(clock_text(dur) if dur else "")
        section = self.pending_section if self.auto_download else None
        if section:
            self.trim_var.set(True)
            self.trim_start_var.set(clock_text(section.get("start")))
            self.trim_end_var.set(clock_text(section.get("end")))
            self.trim_exact_var.set(bool(section.get("exact")))
        if self.auto_download and self.pending_compat:
            self.compat_var.set(True)
        if self.auto_download and self.pending_sub in self._sub_map:
            self.sub_var.set(self.pending_sub)
        self.pending_section = self.pending_compat = self.pending_sub = None
        self._show_trim(bool(self.trim_var.get()))

        self.status_label.configure(
            text="Pronto para baixar. Escolha a qualidade.", text_color=MUTED
        )
        if self.auto_download:
            self.auto_download = False
            wanted, self.pending_quality = self.pending_quality, None
            self.quality_var.set(pick_quality(wanted, options))
            self._refresh_options()
            self.start_download()
        else:
            self._refresh_options()


if __name__ == "__main__":
    apply_style(load_settings().get("ui_style", DEFAULT_STYLE))
    App().mainloop()
