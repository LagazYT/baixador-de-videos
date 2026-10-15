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

URL = "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4"
for name, section in (("inteiro", None), ("trecho", {"start": 30, "end": 40, "exact": False}),
                      ("trecho_exato", {"start": 30, "end": 40, "exact": True})):
    lines = []

    class L:
        def debug(self, m): lines.append(m)
        def info(self, m): lines.append(m)
        def warning(self, m): lines.append("WARN " + m)
        def error(self, m): lines.append("ERR " + m)

    try:
        o = app.build_download_opts(app.LABEL_BEST, os.path.join(OUT, name), FFDIR, "off", None, None, section)
        o.update(verbose=True, quiet=False, logger=L())
        with yt_dlp.YoutubeDL(o) as ydl:
            res = ydl.extract_info(URL, download=True)
        print(f"OK {name}:", res["requested_downloads"][0]["filepath"])
    except Exception as e:  # noqa: BLE001
        print(f"FALHOU {name}: {e}")
        print("\n".join(l for l in lines if "ffmpeg" in l.lower() or "ERR" in l or "WARN" in l)[-3000:])
