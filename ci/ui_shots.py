"""Capturas de tela da interface (rodam no GitHub Actions, no Windows).

Abre o programa a partir do código, simula um vídeo analisado (sem internet) e salva
imagens da aba Baixar com as opções do download e da aba de configurações.
Uso: python ci/ui_shots.py <pasta de saída>
"""
import os
import sys

from PIL import Image, ImageGrab

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "shots"
os.makedirs(OUT, exist_ok=True)

INFO = {
    "id": "demo123", "title": "Vídeo de demonstração com um título bem comprido",
    "uploader": "Canal Exemplo", "duration": 754, "webpage_url": "https://example.com/v",
    "thumbnail": "",
    "formats": [
        {"format_id": "a", "vcodec": "none", "acodec": "mp4a.40.2"},
        {"format_id": "1", "height": 2160, "vcodec": "vp09.00.51.08", "acodec": "none"},
        {"format_id": "2", "height": 1080, "vcodec": "avc1.640028", "acodec": "none"},
        {"format_id": "3", "height": 720, "vcodec": "avc1.4d401f", "acodec": "none"},
    ],
    "subtitles": {"pt-BR": [{"name": "Portuguese (Brazil)", "url": "x"}]},
    "automatic_captions": {"en-orig": [{"name": "English (Original)", "url": "x"}]},
}


def grab(win, name):
    win.update()
    x, y = win.winfo_rootx(), win.winfo_rooty()
    w, h = win.winfo_width(), win.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(os.path.join(OUT, name))
    print("salvo:", name, w, h)


def scroll(widget, frac):
    w = widget
    while w is not None and not hasattr(w, "_parent_canvas"):
        w = w.master
    if w is not None:
        w._parent_canvas.yview_moveto(frac)


def run():
    style = os.environ.get("SHOT_STYLE", "classico")
    app.apply_style(style)
    # sem baixar componentes nem procurar atualizações durante as capturas
    app.App._maybe_setup = lambda self: None
    app.App._auto_check_update = lambda self: None
    a = app.App()
    a.geometry("780x740+0+0")

    def step1():
        a._analyzing_url = INFO["webpage_url"]
        a.url_var.set(INFO["webpage_url"])
        thumb = app.arte.make_placeholder(app.THUMB_W * 2, app.THUMB_H * 2)
        a._on_analyzed(INFO, [2160, 1080, 720], thumb, {})
        scroll(a.compat_switch, 0.0)
        a.after(600, lambda: (grab(a, f"{style}_0_fechada.png"), a.after(200, step1b)))

    def step1b():
        a._toggle_opts()  # abre a gaveta "Mais opções"
        a.compat_var.set(True)
        a.quality_var.set("2160p")
        a.sub_var.set("Português (Brasil)")
        a._refresh_options()
        a.after(600, step2)

    def step2():
        scroll(a.compat_switch, 0.18)
        a.after(500, lambda: (grab(a, f"{style}_1_opcoes.png"), a.after(200, step3)))

    def step3():
        a.trim_var.set(True)
        a._on_trim_toggle()
        a.trim_start_var.set("2:15")
        a.trim_end_var.set("3:40")
        scroll(a.compat_switch, 0.3)
        a.after(500, lambda: (grab(a, f"{style}_2_trecho.png"), a.after(200, step4)))

    def step4():
        a.tabs.set("⚙")
        a.after(400, lambda: (scroll(a.update_status, 1.0), a.after(500, step5)))

    def step5():
        grab(a, f"{style}_3_config.png")
        a.after(200, a.destroy)

    a.after(1500, step1)
    a.mainloop()


if __name__ == "__main__":
    run()
    for f in sorted(os.listdir(OUT)):
        print(f, Image.open(os.path.join(OUT, f)).size)
