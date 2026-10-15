"""
Arte do estilo "Steampunk": latão, cobre e madeira escura (ou pergaminho no tema
claro), com engrenagens, rebites, canos e um manômetro com o botão de play.
O ícone e as imagens do instalador são os do estilo clássico.
"""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import arte_classico

BRASS = (181, 137, 58)
BRASS_LIGHT = (222, 184, 106)
BRASS_DARK = (122, 88, 34)
COPPER = (176, 100, 58)
COPPER_DARK = (120, 62, 34)
VERDIGRIS = (79, 138, 123)
WOOD = (28, 20, 14)
WOOD_2 = (42, 29, 20)
LEATHER = (59, 42, 30)
PARCHMENT = (239, 226, 196)
PARCHMENT_2 = (227, 210, 173)
INK = (42, 29, 20)


def _rgba(c, a=255):
    return tuple(c[:3]) + (int(a),)


def _font(size, bold=True):
    names = (["georgiab.ttf", "palab.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]
             if bold else
             ["georgia.ttf", "pala.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"])
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
        return dict(bg=PARCHMENT, bg2=PARCHMENT_2, ink=INK, soft=(109, 90, 67), shade=(200, 180, 140))
    return dict(bg=WOOD, bg2=WOOD_2, ink=PARCHMENT, soft=(179, 159, 128), shade=(14, 10, 7))


def _gear(size, teeth, color, hole_color, dark=None):
    """Engrenagem desenhada: anel dentado com furo e raios."""
    s = size * 2  # desenha maior e reduz (bordas suaves)
    hole = tuple(hole_color) if len(hole_color) == 4 else _rgba(hole_color)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = s / 2
    r_out, r_in = s * 0.48, s * 0.39
    pts = []
    steps = teeth * 4
    for i in range(steps):
        ang = 2 * math.pi * i / steps
        r = r_out if (i % 4) in (1, 2) else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    d.polygon(pts, fill=_rgba(color))
    dark = dark or tuple(max(0, c - 45) for c in color)
    d.ellipse([cx - r_in * 0.86, cy - r_in * 0.86, cx + r_in * 0.86, cy + r_in * 0.86], outline=_rgba(dark),
              width=max(2, s // 60))
    # janelas entre os raios
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        rx, ry = cx + r_in * 0.52 * math.cos(a), cy + r_in * 0.52 * math.sin(a)
        rr = r_in * 0.17
        d.ellipse([rx - rr, ry - rr, rx + rr, ry + rr], fill=hole)
    hub = r_in * 0.24
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=_rgba(dark))
    d.ellipse([cx - hub * 0.45, cy - hub * 0.45, cx + hub * 0.45, cy + hub * 0.45], fill=hole)
    return img.resize((size, size), Image.LANCZOS)


def _rivet(d, x, y, r, base=BRASS):
    d.ellipse([x - r, y - r, x + r, y + r], fill=_rgba(BRASS_DARK))
    d.ellipse([x - r * 0.8, y - r * 0.8, x + r * 0.6, y + r * 0.6], fill=_rgba(base))
    d.ellipse([x - r * 0.45, y - r * 0.5, x - r * 0.05, y - r * 0.1], fill=_rgba(BRASS_LIGHT))


def _gauge(size, face, ink):
    """Manômetro de latão com um botão de play no centro."""
    s = size * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    d.ellipse([0, 0, s - 1, s - 1], fill=_rgba(BRASS_DARK))
    d.ellipse([s * 0.04, s * 0.04, s * 0.96, s * 0.96], fill=_rgba(BRASS))
    d.ellipse([s * 0.10, s * 0.10, s * 0.90, s * 0.90], fill=_rgba(face))
    # marcas da escala
    for i in range(13):
        a = math.radians(135 + i * 22.5)
        r1, r2 = s * 0.37, s * (0.31 if i % 3 == 0 else 0.34)
        d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)), (c + r2 * math.cos(a), c + r2 * math.sin(a))],
               fill=_rgba(ink), width=max(2, s // (60 if i % 3 == 0 else 110)))
    # zona vermelha
    d.arc([s * 0.16, s * 0.16, s * 0.84, s * 0.84], 0, 45, fill=_rgba(COPPER), width=max(3, s // 40))
    # play
    r = s * 0.17
    d.polygon([(c - r * 0.55, c - r * 0.75), (c - r * 0.55, c + r * 0.75), (c + r * 0.85, c)], fill=_rgba(COPPER_DARK))
    for k in range(4):  # rebites do aro
        a = math.radians(45 + 90 * k)
        _rivet(d, c + s * 0.46 * math.cos(a), c + s * 0.46 * math.sin(a), s * 0.025)
    return img.resize((size, size), Image.LANCZOS)


def _pipe(d, x0, y, x1, h, color=COPPER):
    d.rectangle([x0, y - h / 2, x1, y + h / 2], fill=_rgba(color))
    d.rectangle([x0, y - h / 2, x1, y - h / 4], fill=_rgba(tuple(min(255, c + 40) for c in color)))
    for x in (x0, x1):
        d.rectangle([x - h * 0.35, y - h * 0.8, x + h * 0.35, y + h * 0.8], fill=_rgba(BRASS_DARK))


def _round(base, radius, bg=None):
    w, h = base.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    if bg is None:
        out = base.convert("RGBA")
        out.putalpha(mask)
        return out
    out = Image.new("RGB", (w, h), bg)
    out.paste(base.convert("RGB"), (0, 0), mask)
    return out


def _frame(base, scale, radius):
    """Moldura de latão com rebites nos cantos."""
    w, h = base.size
    d = ImageDraw.Draw(base)
    bw = 4 * scale
    d.rounded_rectangle([bw / 2, bw / 2, w - bw / 2, h - bw / 2], radius=radius, outline=_rgba(BRASS), width=bw)
    d.rounded_rectangle([bw * 1.6, bw * 1.6, w - bw * 1.6, h - bw * 1.6], radius=max(1, radius - bw),
                        outline=_rgba(BRASS_DARK), width=max(1, scale))
    m = bw * 3.2
    for x, y in ((m, m), (w - m, m), (m, h - m), (w - m, h - m)):
        _rivet(d, x, y, 3 * scale)


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
    base = Image.new("RGBA", (W, H), _rgba(p["bg"]))
    d = ImageDraw.Draw(base)
    # tábuas de madeira / faixas de pergaminho
    plank = H / 4
    for i in range(4):
        if i % 2:
            d.rectangle([0, i * plank, W, (i + 1) * plank], fill=_rgba(p["bg2"]))
    # brilho quente atrás das engrenagens
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W * 0.55, -H * 0.3, W * 1.05, H * 1.3], fill=_rgba(BRASS, 70 if not light else 45))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(H * 0.25)))
    # canos
    d = ImageDraw.Draw(base)
    _pipe(d, W * 0.50, H * 0.80, W * 0.97, H * 0.09)
    # engrenagens
    hole = p["bg"]
    g1 = _gear(int(H * 0.95), 14, BRASS, hole)
    g2 = _gear(int(H * 0.62), 10, COPPER, hole)
    g3 = _gear(int(H * 0.40), 8, BRASS_DARK, hole, dark=(80, 58, 22))
    base.alpha_composite(g1, (int(W * 0.66), int(-H * 0.18)))
    base.alpha_composite(g2, (int(W * 0.585), int(H * 0.42)))
    base.alpha_composite(g3, (int(W * 0.905), int(H * 0.60)))
    # manômetro com play
    gs = int(H * 0.66)
    gauge = _gauge(gs, PARCHMENT if not light else (250, 243, 226), INK)
    base.alpha_composite(gauge, (int(W * 0.775), int(H * 0.17)))
    d = ImageDraw.Draw(base)
    if title:
        f_tag = _font(9 * scale, bold=False)
        f_title = _font(28 * scale)
        f_sub = _font(12 * scale, bold=False)
        x = 24 * scale
        d.text((x, H * 0.12), "— OFICINA DE DOWNLOADS —", font=f_tag, fill=_rgba(BRASS if not light else BRASS_DARK))
        d.text((x + 2, H * 0.25 + 2), title, font=f_title, fill=_rgba(p["shade"]))
        d.text((x, H * 0.25), title, font=f_title, fill=_rgba(p["ink"]))
        d.text((x, H * 0.62), subtitle, font=f_sub, fill=_rgba(p["soft"]))
    _frame(base, scale, 12 * scale)
    return _round(base, 12 * scale, bg)


# ---------- rodapé: placa de latão ----------
def make_footer(width, height, bg=None, scale=2, light=False):
    p = _palette(light)
    W, H = width * scale, height * scale
    base = Image.new("RGBA", (W, H), _rgba(p["bg2"]))
    d = ImageDraw.Draw(base)
    d.line([(0, scale), (W, scale)], fill=_rgba(BRASS), width=2 * scale)
    for x in (W * 0.03, W * 0.97):
        _rivet(d, x, H / 2, 3.5 * scale)
    g = _gear(int(H * 0.8), 10, BRASS, p["bg2"])
    base.alpha_composite(g, (int(W * 0.07), int(H * 0.1)))
    base.alpha_composite(g.rotate(18), (int(W * 0.93 - H * 0.8), int(H * 0.1)))
    return _round(base, 8 * scale, bg)


# ---------- miniatura padrão ----------
def make_placeholder(w, h, light=False):
    p = _palette(light)
    base = Image.new("RGBA", (w, h), _rgba(p["bg2"]))
    gs = int(h * 0.62)
    g = _gear(int(h * 0.9), 16, BRASS if not light else BRASS_LIGHT, p["bg2"])
    g = Image.blend(Image.new("RGBA", g.size, (0, 0, 0, 0)), g, 0.35)
    base.alpha_composite(g, (int(w * 0.62), int(h * 0.30)))
    base.alpha_composite(g.resize((int(h * 0.6), int(h * 0.6))), (int(w * 0.02), int(-h * 0.12)))
    gauge = _gauge(gs, PARCHMENT if not light else (250, 243, 226), INK)
    base.alpha_composite(gauge, (int(w / 2 - gs / 2), int(h / 2 - gs / 2)))
    _frame(base, max(1, h // 180), max(4, h // 30))
    return base.convert("RGB")


# ---------- ilustração para estados vazios (fundo transparente) ----------
def make_empty_art(w, h, bg=None, light=False):
    p = _palette(light)
    base = Image.new("RGBA", (w, h), _rgba(bg) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    _pipe(d, w * 0.14, h * 0.78, w * 0.86, h * 0.07)
    hole = p["bg"] if bg else (0, 0, 0, 0)
    g1 = _gear(int(h * 0.62), 14, BRASS, hole)
    g2 = _gear(int(h * 0.44), 10, COPPER, hole)
    g3 = _gear(int(h * 0.34), 8, BRASS_DARK, hole, dark=(80, 58, 22))
    base.alpha_composite(g1, (int(w * 0.22), int(h * 0.10)))
    base.alpha_composite(g2, (int(w * 0.64), int(h * 0.30)))
    base.alpha_composite(g3, (int(w * 0.13), int(h * 0.52)))
    gs = int(h * 0.56)
    gauge = _gauge(gs, PARCHMENT if not light else (250, 243, 226), INK)
    base.alpha_composite(gauge, (int(w / 2 - gs / 2), int(h * 0.16)))
    return base if bg is None else base.convert("RGB")
