"""
Arte do estilo "Arcade 8-bit": pixel art de fliperama, com céu estrelado, montanhas,
moedas, corações e um botão de play feito de blocos. Tudo é desenhado em baixa
resolução e ampliado sem suavizar (pixels de verdade).
O ícone e as imagens do instalador são os do estilo clássico.
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

import arte_classico

NAVY = (11, 11, 26)
PANEL = (20, 20, 43)
GRID = (36, 36, 72)
PURPLE = (88, 52, 196)
PINK = (255, 61, 110)
PINK_DARK = (180, 30, 74)
CYAN = (45, 226, 230)
YELLOW = (255, 214, 10)
ORANGE = (255, 140, 26)
GREEN = (76, 230, 122)
WHITE = (240, 240, 255)
CREAM = (244, 241, 230)
CREAM_2 = (230, 224, 204)
INK = (26, 26, 46)


def _fonts_dir():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fontes")


def _font(size, pixel_title=True):
    name = "PressStart2P-Regular.ttf" if pixel_title else "VT323-Regular.ttf"
    try:
        return ImageFont.truetype(os.path.join(_fonts_dir(), name), int(size))
    except OSError:
        for alt in ("consolab.ttf", "DejaVuSansMono-Bold.ttf"):
            try:
                return ImageFont.truetype(alt, int(size))
            except OSError:
                continue
    try:
        return ImageFont.load_default(int(size))
    except TypeError:
        return ImageFont.load_default()


def _rgba(c, a=255):
    return tuple(c[:3]) + (int(a),)


def _palette(light):
    if light:
        return dict(bg=CREAM, bg2=CREAM_2, sky=[(255, 226, 196), (255, 204, 170), (250, 176, 160)],
                    ink=INK, soft=(90, 86, 110), mount=(124, 98, 196), mount2=(160, 136, 220),
                    ground=(222, 120, 160), star=(255, 255, 255))
    return dict(bg=NAVY, bg2=PANEL, sky=[(11, 11, 26), (24, 16, 56), (52, 22, 86)],
                ink=WHITE, soft=(170, 170, 210), mount=(40, 26, 92), mount2=(66, 40, 132),
                ground=(255, 61, 110), star=(240, 240, 255))


def _upscale(img, size):
    return img.resize(size, Image.NEAREST)


def _pixel_rect(d, x0, y0, x1, y1, fill, step=1):
    """Retângulo com cantos "em degrau" (sem arredondar)."""
    d.rectangle([x0 + step, y0, x1 - step, y1], fill=fill)
    d.rectangle([x0, y0 + step, x1, y1 - step], fill=fill)


def _play_block(d, cx, cy, s, body=PINK, shade=PINK_DARK, tri=WHITE):
    """Botão de play de fliperama em pixels (s = meia largura, em pixels)."""
    _pixel_rect(d, cx - s, cy - s + 1, cx + s, cy + s + 1, shade, step=2)
    _pixel_rect(d, cx - s, cy - s, cx + s, cy + s - 1, body, step=2)
    d.rectangle([cx - s + 2, cy - s + 1, cx + s - 3, cy - s + 1], fill=(255, 150, 180))
    h = max(2, int(s * 0.55))
    for i in range(h * 2 + 1):  # triângulo em degraus
        y = cy - h + i
        w = h - abs(h - i)
        d.line([(cx - h // 2, y), (cx - h // 2 + w, y)], fill=tri)


def _coin(d, x, y, r=2):
    d.rectangle([x - r + 1, y - r, x + r - 1, y + r], fill=YELLOW)
    d.rectangle([x - r, y - r + 1, x + r, y + r - 1], fill=YELLOW)
    d.line([(x, y - r + 1), (x, y + r - 1)], fill=ORANGE)


def _heart(d, x, y, color=PINK):
    rows = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c == "1":
                d.point((x + i, y + j), fill=color)


def _star(d, x, y, color):
    d.point((x, y), fill=color)
    d.point((x - 1, y), fill=_rgba(color, 120))
    d.point((x + 1, y), fill=_rgba(color, 120))
    d.point((x, y - 1), fill=_rgba(color, 120))
    d.point((x, y + 1), fill=_rgba(color, 120))


DIGITS = {"9": ["111", "101", "111", "001", "111"], "x": ["000", "101", "010", "101", "000"]}


def _digit(d, x, y, ch, color):
    for j, row in enumerate(DIGITS[ch]):
        for i, c in enumerate(row):
            if c == "1":
                d.point((x + i, y + j), fill=color)


def _cloud(d, x, y, color):
    d.rectangle([x + 2, y, x + 7, y + 1], fill=color)
    d.rectangle([x, y + 2, x + 11, y + 3], fill=color)
    d.rectangle([x + 5, y - 1, x + 8, y], fill=color)


def _mountains(d, lw, lh, base_y, color, seed, peak):
    rnd = random.Random(seed)
    x, y = 0, base_y - rnd.randint(1, peak)
    pts = [(0, lh)]
    while x <= lw:
        pts.append((x, y))
        x += rnd.randint(2, 4)
        y = max(base_y - peak, min(base_y, y + rnd.choice((-2, -1, 1, 2))))
    pts += [(lw, lh)]
    d.polygon(pts, fill=color)


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
    lh = 36
    px = max(1, H // lh)
    lw = W // px + 1
    low = Image.new("RGBA", (lw, lh), _rgba(p["sky"][0]))
    d = ImageDraw.Draw(low)
    # céu em faixas (sem degradê suave, como nos consoles antigos)
    for i, c in enumerate(p["sky"]):
        d.rectangle([0, int(lh * 0.42 + i * 3), lw, lh], fill=_rgba(c))
    rnd = random.Random(7)
    clear_x = int(lw * 0.52) if title else -1  # sem estrelas atrás do título
    if light:
        for cx, cy in ((0.58, 0.20), (0.76, 0.10), (0.92, 0.34), (0.35, 0.12), (0.10, 0.30)):
            if int(lw * cx) > clear_x:
                _cloud(d, int(lw * cx), int(lh * cy), _rgba((255, 255, 255), 230))
    else:
        for _ in range(int(lw * 0.30)):
            x = rnd.randint(0, lw)
            if x > clear_x:
                _star(d, x, rnd.randint(1, int(lh * 0.55)), p["star"])
    # lua de pixels
    mx, my = int(lw * 0.60), 7
    d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=_rgba((255, 236, 170) if not light else (255, 250, 230)))
    d.ellipse([mx - 1, my - 4, mx + 6, my + 3], fill=_rgba(p["sky"][0]))
    # montanhas e chão quadriculado
    _mountains(d, lw, lh, int(lh * 0.80), _rgba(p["mount2"]), 3, 9)
    _mountains(d, lw, lh, int(lh * 0.86), _rgba(p["mount"]), 11, 6)
    gy = int(lh * 0.86)
    d.rectangle([0, gy, lw, lh], fill=_rgba(p["bg"]))
    d.line([(0, gy), (lw, gy)], fill=_rgba(p["ground"]))
    for k in range(0, lw, 5):
        d.line([(k, gy + 1), (k - 4 + (k - lw // 2) // 6, lh)], fill=_rgba(p["ground"], 140))
    d.line([(0, gy + 3), (lw, gy + 3)], fill=_rgba(p["ground"], 140))
    # botão de play gigante, moedas e corações
    # sem título (celular): tudo mais à direita, longe do texto da tela
    k = 0.0 if title else 0.06
    _play_block(d, int(lw * (0.83 + k * 0.6)), int(lh * 0.42), 8)
    for i, (cx, cy) in enumerate(((0.68, 0.30), (0.73, 0.18), (0.95, 0.20))):
        _coin(d, int(lw * min(0.96, cx + k)), int(lh * cy), 2)
    for i in range(3):
        _heart(d, int(lw * (0.64 + k * 1.5)) + i * 8, int(lh * 0.66), PINK if i < 2 else (110, 110, 140))
    base = _upscale(low, (lw * px, lh * px)).crop((0, 0, W, H))
    if lh * px < H:  # completa a altura que sobrou
        full = Image.new("RGBA", (W, H), _rgba(p["bg"]))
        full.paste(base, (0, 0))
        base = full
    if title:  # faixa escura atrás do texto (o subtítulo não some no meio das montanhas)
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        stop = int(W * 0.62)
        for x in range(0, stop, max(1, px)):
            a = 235 if x < W * 0.40 else int(235 * (stop - x) / (stop - W * 0.40))
            sd.rectangle([x, 0, x + px, H], fill=_rgba(p["bg"], a))
        base.alpha_composite(shade)
    d = ImageDraw.Draw(base)
    if title:
        f_tag = _font(8 * scale)
        f_title = _font(16 * scale)
        f_sub = _font(20 * scale, pixel_title=False)
        x = 22 * scale
        d.text((x, H * 0.14), "★ APERTE START ★", font=f_tag, fill=_rgba(YELLOW if not light else PINK_DARK))
        d.text((x + 3 * scale // 2, H * 0.34 + 3 * scale // 2), title, font=f_title, fill=_rgba(PINK_DARK if not light else (200, 190, 220)))
        d.text((x, H * 0.34), title, font=f_title, fill=_rgba(p["ink"]))
        d.text((x, H * 0.62), subtitle, font=f_sub, fill=_rgba(CYAN if not light else (60, 60, 110)))
    # moldura de pixels
    b = 3 * scale
    d.rectangle([0, 0, W - 1, H - 1], outline=_rgba(p["ink"] if light else CYAN), width=b)
    for cx, cy in ((0, 0), (W - b * 2, 0), (0, H - b * 2), (W - b * 2, H - b * 2)):
        d.rectangle([cx, cy, cx + b * 2 - 1, cy + b * 2 - 1], fill=(0, 0, 0, 0) if bg is None else _rgba(bg))
    if bg is not None:
        out = Image.new("RGB", (W, H), bg)
        out.paste(base.convert("RGB"), (0, 0), base)
        return out
    return base


# ---------- rodapé: vidas e moedas ----------
def make_footer(width, height, bg=None, scale=2, light=False):
    p = _palette(light)
    W, H = width * scale, height * scale
    lh = 12
    px = max(1, H // lh)
    lw = W // px + 1
    low = Image.new("RGBA", (lw, lh), _rgba(p["bg2"]))
    d = ImageDraw.Draw(low)
    d.line([(0, 0), (lw, 0)], fill=_rgba(PINK))
    d.line([(0, 1), (lw, 1)], fill=_rgba(CYAN if not light else INK))
    left = max(3, int(lw * 0.06))  # longe da borda: a tela do celular corta as laterais
    for i in range(3):
        _heart(d, left + i * 8, 4, PINK)
    right = int(lw * 0.94)
    _coin(d, right - 16, 7, 2)
    _digit(d, right - 12, 5, "x", _rgba(p["soft"]))
    _digit(d, right - 8, 5, "9", _rgba(YELLOW))
    _digit(d, right - 4, 5, "9", _rgba(YELLOW))
    base = _upscale(low, (lw * px, lh * px)).crop((0, 0, W, H))
    if base.size != (W, H):
        full = Image.new("RGBA", (W, H), _rgba(p["bg2"]))
        full.paste(base, (0, 0))
        base = full
    if bg is not None:
        out = Image.new("RGB", (W, H), bg)
        out.paste(base.convert("RGB"), (0, 0), base)
        return out
    return base


# ---------- miniatura padrão ----------
def make_placeholder(w, h, light=False):
    p = _palette(light)
    lh = 45
    px = max(1, h // lh)
    lw = w // px + 1
    low = Image.new("RGBA", (lw, lh), _rgba(p["bg2"]))
    d = ImageDraw.Draw(low)
    for x in range(0, lw, 6):
        d.line([(x, 0), (x, lh)], fill=_rgba(GRID if not light else CREAM))
    for y in range(0, lh, 6):
        d.line([(0, y), (lw, y)], fill=_rgba(GRID if not light else CREAM))
    rnd = random.Random(5)
    for _ in range(18):
        _star(d, rnd.randint(0, lw), rnd.randint(0, lh), CYAN if not light else PURPLE)
    _play_block(d, lw // 2, lh // 2 - 1, 11)
    for i, (cx, cy) in enumerate(((0.2, 0.25), (0.8, 0.7), (0.15, 0.75))):
        _coin(d, int(lw * cx), int(lh * cy), 2)
    img = _upscale(low, (lw * px, lh * px)).crop((0, 0, w, h))
    if img.size != (w, h):
        full = Image.new("RGBA", (w, h), _rgba(p["bg2"]))
        full.paste(img, (0, 0))
        img = full
    return img.convert("RGB")


# ---------- ilustração para estados vazios: controle de pixels ----------
def make_empty_art(w, h, bg=None, light=False):
    lh = 50
    px = max(1, h // lh)
    lw = w // px + 1
    low = Image.new("RGBA", (lw, lh), _rgba(bg) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(low)
    cx, cy = lw // 2, lh // 2 + 2
    body = (70, 70, 120) if not light else (200, 196, 230)
    edge = (40, 40, 80) if not light else (120, 112, 170)
    # corpo do controle (genérico)
    _pixel_rect(d, cx - 22, cy - 9, cx + 22, cy + 10, _rgba(edge), step=3)
    _pixel_rect(d, cx - 21, cy - 10, cx + 21, cy + 8, _rgba(body), step=3)
    # direcional
    dx, dy = cx - 12, cy - 1
    d.rectangle([dx - 1, dy - 4, dx + 1, dy + 4], fill=_rgba(INK if light else NAVY))
    d.rectangle([dx - 4, dy - 1, dx + 4, dy + 1], fill=_rgba(INK if light else NAVY))
    # botões
    for bx, by, c in ((cx + 10, cy + 1, PINK), (cx + 15, cy - 3, CYAN)):
        d.rectangle([bx - 2, by - 1, bx + 2, by + 1], fill=_rgba(c))
        d.rectangle([bx - 1, by - 2, bx + 1, by + 2], fill=_rgba(c))
    d.rectangle([cx - 3, cy - 4, cx - 1, cy - 3], fill=_rgba(edge))
    d.rectangle([cx + 1, cy - 4, cx + 3, cy - 3], fill=_rgba(edge))
    # moedas, estrelas e corações flutuando
    for x, y in ((cx - 30, cy - 14), (cx + 30, cy - 12), (cx + 36, cy + 6)):
        _coin(d, x, y, 2)
    for x, y in ((cx - 36, cy + 4), (cx - 8, cy - 18), (cx + 18, cy - 19)):
        _star(d, x, y, YELLOW)
    _heart(d, cx - 4, cy - 22 + 1, PINK)
    img = _upscale(low, (lw * px, lh * px)).crop((0, 0, w, h))
    if img.size != (w, h):
        full = Image.new("RGBA", (w, h), (0, 0, 0, 0) if bg is None else _rgba(bg))
        full.paste(img, (0, 0))
        img = full
    return img if bg is None else img.convert("RGB")
