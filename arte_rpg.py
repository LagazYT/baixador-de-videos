"""
Arte do estilo "Fantasia / RPG": castelo sob a lua, selo dourado com o botão de play,
molduras douradas com gemas, escudo e baú do tesouro.
O ícone e as imagens do instalador são os do estilo clássico.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import arte_classico

NIGHT = (16, 21, 30)
NIGHT_2 = (30, 38, 58)
STONE = (26, 33, 41)
STONE_2 = (37, 46, 56)
GOLD = (210, 172, 80)
GOLD_LIGHT = (240, 210, 130)
GOLD_DARK = (138, 106, 48)
CRIMSON = (163, 43, 43)
CRIMSON_DARK = (110, 26, 30)
EMERALD = (47, 143, 91)
PARCH = (243, 233, 210)
PARCH_2 = (232, 218, 186)
INK = (43, 33, 23)
MOON = (244, 236, 205)
WOOD = (110, 70, 38)
WOOD_DARK = (72, 44, 24)


def _rgba(c, a=255):
    return tuple(c[:3]) + (int(a),)


def _fonts_dir():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fontes")


def _title_font(size, weight=700):
    try:
        f = ImageFont.truetype(os.path.join(_fonts_dir(), "Cinzel.ttf"), int(size))
        try:
            f.set_variation_by_axes([weight])
        except Exception:  # noqa: BLE001
            pass
        return f
    except OSError:
        return _font(size)


def _font(size, bold=False):
    names = (["palab.ttf", "georgiab.ttf", "DejaVuSerif-Bold.ttf"] if bold
             else ["pala.ttf", "georgia.ttf", "DejaVuSerif.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, int(size))
        except OSError:
            continue
    try:
        return ImageFont.load_default(int(size))
    except TypeError:
        return ImageFont.load_default()


def _palette(light):
    if light:
        return dict(bg=PARCH, bg2=PARCH_2, sky_top=(250, 226, 196), sky_bot=(244, 236, 214),
                    far=(170, 150, 170), near=(120, 98, 120), castle=(88, 70, 92), ink=INK,
                    soft=(110, 90, 66), window=(255, 214, 120), frame=GOLD_DARK)
    return dict(bg=NIGHT, bg2=STONE, sky_top=(12, 16, 32), sky_bot=(44, 52, 86),
                far=(34, 42, 66), near=(22, 28, 44), castle=(12, 15, 24), ink=PARCH,
                soft=(196, 184, 156), window=(255, 196, 90), frame=GOLD)


def _vgrad(w, h, top, bottom):
    g = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), _rgba(tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))))
    return g.resize((w, h))


def _ridge(d, W, H, base, amp, color, seed, step):
    rnd = random.Random(seed)
    pts = [(0, H)]
    x, y = 0, base
    while x <= W + step:
        pts.append((x, y))
        x += step
        y = max(base - amp, min(base + amp * 0.3, y + rnd.uniform(-amp * 0.5, amp * 0.5)))
    pts.append((W, H))
    d.polygon(pts, fill=_rgba(color))


def _castle(d, x, base, s, color, window):
    """Castelo genérico: muralha com ameias, duas torres e um torreão central."""
    def tower(cx, w, h, roof=True):
        d.rectangle([cx - w / 2, base - h, cx + w / 2, base], fill=_rgba(color))
        for k in range(3):  # ameias
            bx = cx - w / 2 + k * w / 2.5
            d.rectangle([bx, base - h - s * 0.6, bx + w / 5, base - h], fill=_rgba(color))
        if roof:
            d.polygon([(cx - w * 0.62, base - h - s * 0.4), (cx + w * 0.62, base - h - s * 0.4),
                       (cx, base - h - w * 1.3)], fill=_rgba(color))
            d.line([(cx, base - h - w * 1.3), (cx, base - h - w * 1.8)], fill=_rgba(color), width=max(1, int(s * 0.25)))
            d.polygon([(cx, base - h - w * 1.8), (cx + w * 0.5, base - h - w * 1.65), (cx, base - h - w * 1.5)],
                      fill=_rgba(CRIMSON))
        for wy in (0.35, 0.6):
            d.rectangle([cx - s * 0.35, base - h * (1 - wy), cx + s * 0.35, base - h * (1 - wy) + s * 0.9],
                        fill=_rgba(window))
    d.rectangle([x - s * 9, base - s * 6, x + s * 9, base], fill=_rgba(color))  # muralha
    for k in range(10):
        bx = x - s * 9 + k * s * 1.85
        d.rectangle([bx, base - s * 7, bx + s * 0.9, base - s * 6], fill=_rgba(color))
    d.pieslice([x - s * 1.6, base - s * 3.6, x + s * 1.6, base - s * 0.4], 180, 360, fill=_rgba(window, 120))
    tower(x - s * 8, s * 3.2, s * 13)
    tower(x + s * 8, s * 3.2, s * 13)
    tower(x, s * 4.2, s * 17)


def _seal(size, light):
    """Selo dourado com o botão de play (o "emblema" do app)."""
    s = size * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([s * 0.08, s * 0.08, s * 0.92, s * 0.92], fill=_rgba(GOLD_LIGHT, 150))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.08)))
    d = ImageDraw.Draw(img)
    c = s / 2
    d.ellipse([s * 0.14, s * 0.14, s * 0.86, s * 0.86], fill=_rgba(GOLD_DARK))
    d.ellipse([s * 0.17, s * 0.17, s * 0.83, s * 0.83], fill=_rgba(GOLD))
    d.ellipse([s * 0.23, s * 0.23, s * 0.77, s * 0.77], fill=_rgba(CRIMSON if not light else CRIMSON))
    d.ellipse([s * 0.25, s * 0.25, s * 0.75, s * 0.75], outline=_rgba(GOLD_LIGHT), width=max(2, s // 90))
    for k in range(8):  # pontas de estrela no aro
        a = math.radians(k * 45)
        r1, r2 = s * 0.30, s * 0.36
        d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)), (c + r2 * math.cos(a), c + r2 * math.sin(a))],
               fill=_rgba(GOLD_LIGHT), width=max(2, s // 80))
    r = s * 0.14
    d.polygon([(c - r * 0.6, c - r * 0.85), (c - r * 0.6, c + r * 0.85), (c + r * 0.95, c)], fill=_rgba(PARCH))
    return img.resize((size, size), Image.LANCZOS)


def _gem(d, x, y, r, color):
    d.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=_rgba(GOLD_DARK))
    d.polygon([(x, y - r * 0.7), (x + r * 0.7, y), (x, y + r * 0.7), (x - r * 0.7, y)], fill=_rgba(color))
    d.polygon([(x - r * 0.15, y - r * 0.5), (x + r * 0.2, y - r * 0.15), (x - r * 0.3, y - r * 0.05)],
              fill=(255, 255, 255, 140))


def _frame(base, scale, color):
    """Moldura dourada dupla com gemas nos cantos."""
    w, h = base.size
    d = ImageDraw.Draw(base)
    b = 3 * scale
    d.rectangle([b / 2, b / 2, w - b / 2, h - b / 2], outline=_rgba(color), width=b)
    d.rectangle([b * 2.2, b * 2.2, w - b * 2.2, h - b * 2.2], outline=_rgba(color, 170), width=max(1, scale))
    for x, y in ((b * 2.2, b * 2.2), (w - b * 2.2, b * 2.2), (b * 2.2, h - b * 2.2), (w - b * 2.2, h - b * 2.2)):
        _gem(d, x, y, 4.5 * scale, CRIMSON)


def _finish(base, bg):
    if bg is None:
        return base
    out = Image.new("RGB", base.size, bg)
    out.paste(base.convert("RGB"), (0, 0), base)
    return out


# ---------- ícone e instalador: iguais ao clássico ----------
def make_icon(size=256):
    return arte_classico.make_icon(size)


def save_ico(path):
    return arte_classico.save_ico(path)


def make_wizard_large(w=164, h=314):
    return arte_classico.make_wizard_large(w, h)


def make_wizard_small(size=55):
    return arte_classico.make_wizard_small(size)


# ---------- banner do topo ----------
def make_banner(width, height, title, subtitle, bg=None, scale=2, light=False):
    p = _palette(light)
    W, H = width * scale, height * scale
    base = _vgrad(W, H, p["sky_top"], p["sky_bot"])
    d = ImageDraw.Draw(base)
    rnd = random.Random(3)
    clear_x = W * 0.5 if title else -1
    if not light:
        for _ in range(int(W / (14 * scale))):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H * 0.6)
            if x > clear_x:
                r = rnd.choice((1, 1, 1.5, 2)) * scale * 0.7
                d.ellipse([x - r, y - r, x + r, y + r], fill=_rgba(MOON, rnd.randint(120, 230)))
    # lua com brilho
    cx = 0.645 if title else 0.70  # sem título (celular): castelo mais à direita, longe do texto
    mx, my, mr = W * cx, H * 0.28, H * 0.17
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([mx - mr * 2, my - mr * 2, mx + mr * 2, my + mr * 2],
                                 fill=_rgba(MOON if not light else (255, 240, 200), 70))
    base.alpha_composite(halo.filter(ImageFilter.GaussianBlur(mr * 0.8)))
    d = ImageDraw.Draw(base)
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=_rgba(MOON if not light else (255, 246, 220)))
    # montanhas e castelo
    _ridge(d, W, H, H * 0.70, H * 0.16, p["far"], 5, W / 24)
    _castle(d, W * cx, H * 0.86, H * 0.028, p["castle"], p["window"])
    _ridge(d, W, H, H * 0.88, H * 0.06, p["near"], 9, W / 40)
    # selo dourado com play
    ss = int(min(H * (0.80 if title else 0.70), W * 0.26))
    sx = 0.875 if title else 0.895
    base.alpha_composite(_seal(ss, light), (int(W * sx - ss / 2), int(H * 0.47 - ss / 2)))
    d = ImageDraw.Draw(base)
    if title:
        x = 24 * scale
        d.text((x, H * 0.13), "— GUILDA DOS DOWNLOADS —", font=_title_font(8.5 * scale, 600),
               fill=_rgba(GOLD if not light else GOLD_DARK))
        f_title = _title_font(26 * scale, 800)
        d.text((x + scale * 1.5, H * 0.26 + scale * 1.5), title, font=f_title,
               fill=_rgba((0, 0, 0) if not light else (210, 190, 150), 170))
        d.text((x, H * 0.26), title, font=f_title, fill=_rgba(GOLD_LIGHT if not light else INK))
        d.text((x, H * 0.64), subtitle, font=_font(12 * scale), fill=_rgba(p["soft"]))
    _frame(base, scale, p["frame"])
    return _finish(base, bg)


# ---------- rodapé: faixa de pedra com gemas ----------
def make_footer(width, height, bg=None, scale=2, light=False):
    p = _palette(light)
    W, H = width * scale, height * scale
    base = Image.new("RGBA", (W, H), _rgba(p["bg2"]))
    d = ImageDraw.Draw(base)
    d.line([(0, scale), (W, scale)], fill=_rgba(p["frame"]), width=2 * scale)
    d.line([(0, 4 * scale), (W, 4 * scale)], fill=_rgba(p["frame"], 110), width=scale)
    for x, color in ((W * 0.07, CRIMSON), (W * 0.10, EMERALD), (W * 0.90, EMERALD), (W * 0.93, CRIMSON)):
        _gem(d, x, H * 0.58, H * 0.2, color)
    return _finish(base, bg)


# ---------- miniatura padrão: escudo com o play ----------
def make_placeholder(w, h, light=False):
    p = _palette(light)
    base = _vgrad(w, h, p["bg2"], p["bg"] if not light else PARCH_2)
    d = ImageDraw.Draw(base)
    cx, cy, s = w / 2, h * 0.5, h * 0.36
    shield = [(cx - s, cy - s * 0.95), (cx + s, cy - s * 0.95), (cx + s, cy - s * 0.1),
              (cx, cy + s * 1.05), (cx - s, cy - s * 0.1)]
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - s * 1.6, cy - s * 1.5, cx + s * 1.6, cy + s * 1.5], fill=_rgba(GOLD, 70))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.4)))
    d = ImageDraw.Draw(base)
    d.polygon([(x, y + s * 0.06) for x, y in shield], fill=_rgba((0, 0, 0), 120))
    d.polygon(shield, fill=_rgba(GOLD_DARK))
    inner = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.86 - s * 0.02) for x, y in shield]
    d.polygon(inner, fill=_rgba(CRIMSON))
    d.line([(cx, cy - s * 0.8), (cx, cy + s * 0.85)], fill=_rgba(CRIMSON_DARK), width=max(2, int(s * 0.04)))
    r = s * 0.42
    d.polygon([(cx - r * 0.55, cy - r * 0.75), (cx - r * 0.55, cy + r * 0.75), (cx + r * 0.85, cy)], fill=_rgba(PARCH))
    _frame(base, max(1, h // 180), p["frame"])
    return base.convert("RGB")


# ---------- ilustração para estados vazios: baú do tesouro ----------
def make_empty_art(w, h, bg=None, light=False):
    base = Image.new("RGBA", (w, h), _rgba(bg) if bg else (0, 0, 0, 0))
    cx, by = w / 2, h * 0.86
    cw, ch = h * 0.62, h * 0.34
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - cw * 0.55, by - ch * 2.2, cx + cw * 0.55, by - ch * 0.6],
                                 fill=_rgba(GOLD_LIGHT, 170))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(h * 0.06)))
    d = ImageDraw.Draw(base)
    x0, x1 = cx - cw / 2, cx + cw / 2
    # corpo
    d.rectangle([x0, by - ch, x1, by], fill=_rgba(WOOD))
    for k in range(1, 4):
        d.line([(x0, by - ch * k / 4), (x1, by - ch * k / 4)], fill=_rgba(WOOD_DARK), width=max(1, int(h * 0.006)))
    # tampa aberta (inclinada para trás)
    lid = [(x0 + cw * 0.04, by - ch), (x1 - cw * 0.04, by - ch), (x1 - cw * 0.12, by - ch * 1.85),
           (x0 + cw * 0.12, by - ch * 1.85)]
    d.polygon(lid, fill=_rgba(WOOD_DARK))
    d.polygon([(x0 + cw * 0.08, by - ch * 1.05), (x1 - cw * 0.08, by - ch * 1.05),
               (x1 - cw * 0.14, by - ch * 1.75), (x0 + cw * 0.14, by - ch * 1.75)], fill=_rgba((60, 34, 18)))
    # moedas transbordando
    rnd = random.Random(4)
    for _ in range(26):
        mx = rnd.uniform(x0 + cw * 0.08, x1 - cw * 0.08)
        my = by - ch * rnd.uniform(0.95, 1.25)
        r = h * rnd.uniform(0.022, 0.032)
        d.ellipse([mx - r, my - r * 0.8, mx + r, my + r * 0.8], fill=_rgba(GOLD_DARK))
        d.ellipse([mx - r * 0.8, my - r * 0.7, mx + r * 0.8, my + r * 0.6], fill=_rgba(GOLD))
    # cintas e fechadura douradas
    bw = cw * 0.07
    for bx in (x0 + cw * 0.14, x1 - cw * 0.14 - bw):
        d.rectangle([bx, by - ch, bx + bw, by], fill=_rgba(GOLD))
        d.rectangle([bx, by - ch, bx + bw * 0.35, by], fill=_rgba(GOLD_LIGHT))
    d.rectangle([x0, by - h * 0.012, x1, by], fill=_rgba(GOLD_DARK))
    lw_, lh_ = cw * 0.12, ch * 0.32
    d.rectangle([cx - lw_ / 2, by - ch * 0.9, cx + lw_ / 2, by - ch * 0.9 + lh_], fill=_rgba(GOLD))
    d.ellipse([cx - lw_ * 0.15, by - ch * 0.8, cx + lw_ * 0.15, by - ch * 0.8 + lw_ * 0.3], fill=_rgba(INK))
    # brilhos
    for sx, sy, sr in ((cx - cw * 0.75, by - ch * 1.9, 0.05), (cx + cw * 0.7, by - ch * 1.6, 0.04),
                       (cx + cw * 0.15, by - ch * 2.4, 0.035), (cx - cw * 0.35, by - ch * 2.2, 0.03)):
        r = h * sr
        d.polygon([(sx, sy - r), (sx + r * 0.25, sy - r * 0.25), (sx + r, sy), (sx + r * 0.25, sy + r * 0.25),
                   (sx, sy + r), (sx - r * 0.25, sy + r * 0.25), (sx - r, sy), (sx - r * 0.25, sy - r * 0.25)],
                  fill=_rgba(GOLD_LIGHT if not light else GOLD))
    return base if bg is None else base.convert("RGB")
