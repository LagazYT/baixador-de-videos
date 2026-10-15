"""Diagnóstico: o FFmpeg que o programa usa no Windows consegue baixar um trecho?"""
import os
import subprocess
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import app  # noqa: E402
import yt_dlp  # noqa: E402

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "diag")
os.makedirs(OUT, exist_ok=True)
FFDIR = app.ffmpeg_location()
EXE = os.path.join(FFDIR, "ffmpeg.exe") if FFDIR else None
print("ffmpeg escolhido:", FFDIR, "| yt-dlp:", yt_dlp.version.__version__)
try:
    import imageio_ffmpeg
    print("imageio-ffmpeg:", imageio_ffmpeg.__version__, imageio_ffmpeg.get_ffmpeg_exe())
except Exception as e:  # noqa: BLE001
    print("imageio-ffmpeg:", e)
for args in (["-version"], ["-hide_banner", "-protocols"]):
    r = subprocess.run([EXE] + args, capture_output=True, text=True, errors="replace")
    txt = (r.stdout + r.stderr)
    print("$ ffmpeg", " ".join(args), "->", r.returncode)
    print(txt[:300] if args == ["-version"] else " ".join(txt.split()))
    if args == ["-version"]:
        print("   tls:", [w for w in txt.split() if any(k in w for k in ("tls", "ssl", "schannel"))])

B = "https://raw.githubusercontent.com/LagazYT/baixador-de-videos/main/ci/diag/"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
       "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-us,en;q=0.5",
       "Sec-Fetch-Mode": "navigate"}


def fmt(fid, f, ext, v, a, h):
    return {"format_id": fid, "url": B + f, "ext": ext, "vcodec": v, "acodec": a, "height": h,
            "width": h * 16 // 9 if h else None, "protocol": "https", "http_headers": HDR}


INFO = {"id": "diag", "title": "Diagnóstico", "ext": "mp4", "duration": 20,
        "webpage_url": "https://example.com/diag", "extractor": "generic", "extractor_key": "Generic",
        "formats": [fmt("a", "aud.m4a", "m4a", "none", "mp4a.40.2", None),
                    fmt("v720", "avc.mp4", "mp4", "avc1.4d401f", "none", 720),
                    fmt("v2160", "vp9.webm", "webm", "vp09.00.51.08", "none", 2160)]}

for name, choice, section in (("inteiro", app.LABEL_BEST, None),
                              ("trecho", "720p", {"start": 5, "end": 12, "exact": False}),
                              ("trecho_exato", "720p", {"start": 5, "end": 12, "exact": True}),
                              ("trecho_mp3", app.LABEL_AUDIO, {"start": 3, "end": 8})):
    lines = []

    class L:
        def debug(self, m): lines.append(m)
        def info(self, m): lines.append(m)
        def warning(self, m): lines.append("WARN " + m)
        def error(self, m): lines.append("ERR " + m)

    try:
        o = app.build_download_opts(choice, os.path.join(OUT, name), FFDIR, "off", None, None, section)
        o.update(verbose=True, quiet=False, logger=L())
        with yt_dlp.YoutubeDL(o) as ydl:
            res = ydl.process_ie_result(dict(INFO), download=True)
        print(f"OK {name}:", res["requested_downloads"][0]["filepath"])
        for l in lines:
            if "ffmpeg command line" in l:
                print("   ", l[:700])
    except Exception as e:  # noqa: BLE001
        print(f"FALHOU {name}: {e}")
        print("\n".join(l for l in lines if "ffmpeg" in l.lower() or "ERR" in l or "WARN" in l)[-3000:])
