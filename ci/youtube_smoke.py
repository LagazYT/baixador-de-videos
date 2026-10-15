"""Teste real das opções de download (roda no GitHub Actions, no Windows).

Usa as mesmas funções do programa (build_download_opts, download_plans...) com o
YouTube de verdade: H.264 sem conversão, conversão de 4K para H.264, trecho, MP3,
legendas e thumbnail. Não falha o build: só registra o resultado.
Uso: python ci/youtube_smoke.py <pasta de saída>
"""
import os
import re
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402
import yt_dlp  # noqa: E402

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "smoke")
os.makedirs(OUT, exist_ok=True)
FF = app.ffmpeg_location()
JS, HAS_JS = app.js_runtime_opts()
BUNNY = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"   # Big Buck Bunny (tem 4K)
ZOO = "https://www.youtube.com/watch?v=jNQXAC9IVRw"     # Me at the zoo (tem legendas)
print("ffmpeg:", FF, "| deno:", HAS_JS, "| yt-dlp:", yt_dlp.version.__version__)


def streams(path):
    r = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    found = re.findall(r"Stream #\S+.*?: (Video|Audio|Subtitle): (\w+)", r.stderr)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    secs = (int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))) if dur else None
    return [f"{k[0].lower()}:{c}" for k, c in found], secs


def info_of(url):
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True,
                           "skip_download": True, **JS}) as ydl:
        return ydl.extract_info(url, download=False)


def case(name, url, info, choice, compat=False, sub=None, section=None):
    t0 = time.time()
    try:
        heights = sorted({f["height"] for f in info.get("formats", [])
                          if f.get("height") and f.get("vcodec") != "none"}, reverse=True)
        hs, known = app.h264_heights(info)
        mode, h = app.compat_plan(compat, choice, heights, hs, known)
        folder = os.path.join(OUT, name)
        opts = app.build_download_opts(choice, folder, FF, mode, h, sub, section)
        opts.update(JS)
        plans = app.download_plans(opts, choice, mode)
        used = None
        res = None
        for o, note in plans:
            try:
                with yt_dlp.YoutubeDL(o) as ydl:
                    res = ydl.extract_info(url, download=True)
                used = note or "receita principal"
                break
            except Exception as e:  # noqa: BLE001
                print(f"   [{name}] receita falhou: {str(e)[:200]}")
        path = res["requested_downloads"][0]["filepath"]
        st, dur = streams(path)
        files = sorted(os.listdir(folder))
        print(f"OK  {name}: modo={mode} h={h} formato={res.get('format_id')} -> {st} "
              f"duração={dur and round(dur, 1)} | {used} | arquivos={files} | {time.time() - t0:.0f}s")
    except Exception:  # noqa: BLE001
        print(f"ERRO {name}: {traceback.format_exc()[-600:]}")


try:
    bunny = info_of(BUNNY)
    hs, known = app.h264_heights(bunny)
    print("Big Buck Bunny: alturas H.264:", sorted(hs), "| codecs informados:", known,
          "| thumbnails:", app.best_thumbnail_url(bunny))
    case("h264_melhor_trecho", BUNNY, bunny, app.LABEL_BEST, compat=True,
         section={"start": 60, "end": 70, "exact": False})
    case("4k_convertido_trecho", BUNNY, bunny, "2160p", compat=True,
         section={"start": 30, "end": 33, "exact": False})
    case("mp3_trecho", BUNNY, bunny, app.LABEL_AUDIO, section={"start": 10, "end": 15})
    case("trecho_exato_720", BUNNY, bunny, "720p", section={"start": 12.5, "end": 17, "exact": True})
except Exception:  # noqa: BLE001
    print("ERRO Big Buck Bunny:", traceback.format_exc()[-600:])

try:
    zoo = info_of(ZOO)
    subs = app.subtitle_options(zoo)
    print("Me at the zoo: legendas:", subs[:6], "| total:", len(subs))
    if subs:
        label, code, auto = subs[0]
        case("legenda_embutida", ZOO, zoo, "240p" if 240 in {f.get("height") for f in zoo["formats"]} else app.LABEL_BEST,
             compat=True, sub=(code, auto))
        case("mp3_com_srt", ZOO, zoo, app.LABEL_AUDIO, sub=(code, auto))
    path, size = app.save_thumbnail_file(app.thumbnail_candidates(zoo), os.path.join(OUT, "thumb"),
                                         zoo.get("title"), zoo.get("id"))
    print("OK  thumbnail:", os.path.basename(path), size)
except Exception:  # noqa: BLE001
    print("ERRO Me at the zoo:", traceback.format_exc()[-600:])
