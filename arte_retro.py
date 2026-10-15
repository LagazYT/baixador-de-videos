"""
Arte do estilo "Retrô minimalista": papel creme, tinta escura e faixas de pôr do
sol em laranja, mostarda e verde-petróleo. Formas chapadas, sem degradês.
O ícone e as imagens do instalador são os do estilo clássico.
"""
from PIL import Image, ImageDraw, ImageFont

import arte_classico

CREAM = (242, 234, 216)
CREAM_2 = (231, 220, 196)
INK = (43, 39, 36)
INK_SOFT = (110, 100, 90)
ORANGE = (217, 98, 43)
MUSTARD = (227, 167, 47)
TEAL = (47, 111, 106)
BROWN = (31, 28, 25)
BROWN_2 = (44, 40, 36)
LINE_DARK = (88, 80, 72)

STRIPES = (MUSTARD, ORANGE, (192, 66, 43), TEAL)


def _rgba(c, a=255):
    return tuple(c[:3]) + (int(a),)


def _font(size, bold=True):
    names = (["consolab.ttf", "courbd.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf"]
             if bold else
             ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"])
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
        return dict(paper=CREAM, paper2=CREAM_2, ink=INK, soft=INK_SOFT)
    return dict(paper=BROWN, paper2=BROWN_2, ink=CREAM, soft=(170, 160, 145))


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


def _sun(size, ink, paper, bands=4):
    """Sol de pôr do sol: semicírculo em faixas, com cortes horizontais."""
    w = h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, w - 1, h - 1], fill=_rgba(MUSTARD))
    # faixas coloridas de baixo para cima
    band_h = h / 2 / bands
    for i, c in enumerate(STRIPES[:bands]):
        y0 = h / 2 + i * band_h
        d.rectangle([0, y0, w, y0 + band_h], fill=_rgba(c))
    # cortes (linhas de papel) que vão engrossando para baixo
    for i in range(bands):
        y = h / 2 + (i + 1) * band_h - band_h * (0.10 + i * 0.06)
        d.rectangle([0, y, w, y + band_h * (0.10 + i * 0.06)], fill=_rgba(paper))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, w - 1, h - 1], fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    ImageDraw.Draw(out).ellipse([0, 0, w - 1, h - 1], outline=_rgba(ink), width=max(2, size // 40))
    return out


def _play(d, cx, cy, r, fill):
    d.polygon([(cx - r * 0.45, cy - r * 0.62), (cx - r * 0.45, cy + r * 0.62),
               (cx + r * 0.68, cy)], fill=fill)


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
    base = Image.new("RGBA", (W, H), _rgba(p["paper"]))
    d = ImageDraw.Draw(base)
    # faixas horizontais na base (o "chão" do pôr do sol)
    stripe_h = max(3, H // 22)
    for i, c in enumerate(STRIPES):
        y = H - (len(STRIPES) - i) * stripe_h
        d.rectangle([0, y, W, y + stripe_h], fill=_rgba(c))
    # sol à direita
    s = int(H * 0.86)
    sun = _sun(s, p["ink"], p["paper"])
    base.alpha_composite(sun, (int(W - s - H * 0.22), int(H * 0.04)))
    d = ImageDraw.Draw(base)
    # pequeno botão de play sobre o sol
    cx, cy, r = W - s / 2 - H * 0.22, H * 0.04 + s * 0.30, s * 0.16
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_rgba(p["paper"]), outline=_rgba(p["ink"]),
              width=max(2, scale * 2))
    _play(d, cx + r * 0.05, cy, r * 0.62, _rgba(p["ink"]))
    if title:
        f_title = _font(28 * scale)
        f_sub = _font(11 * scale, bold=False)
        f_tag = _font(9 * scale)
        x = 24 * scale
        d.text((x, H * 0.14), "EST. 2026 · DOWNLOADS", font=f_tag, fill=_rgba(p["soft"]))
        d.text((x, H * 0.26), title.upper(), font=f_title, fill=_rgba(p["ink"]))
        max_w = W - s - H * 0.22 - x - 16 * scale
        words, lines, cur = subtitle.split(), [], ""
        for wd in words:
            test = (cur + " " + wd).strip()
            if d.textlength(test, font=f_sub) <= max_w or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        for i, line in enumerate(lines[:2]):
            d.text((x, H * 0.57 + i * 14 * scale), line, font=f_sub, fill=_rgba(p["soft"]))
    return _round(base, 10 * scale, bg)


# ---------- rodapé ----------
def make_footer(width, height, bg=None, scale=2, light=False):
    p = _palette(light)
    W, H = width * scale, height * scale
    base = Image.new("RGBA", (W, H), _rgba(p["paper"]))
    d = ImageDraw.Draw(base)
    d.line([(0, 1 * scale), (W, 1 * scale)], fill=_rgba(p["ink"]), width=2 * scale)
    # quatro faixinhas coloridas em cada ponta
    sw, gap = 6 * scale, 3 * scale
    for side in (0, 1):
        for i, c in enumerate(STRIPES):
            x = 14 * scale + i * (sw + gap) if side == 0 else W - 14 * scale - (i + 1) * (sw + gap) + gap
            d.rectangle([x, H * 0.30, x + sw, H * 0.78], fill=_rgba(c))
    return _round(base, 6 * scale, bg)


# ---------- miniatura padrão ----------
def make_placeholder(w, h, light=False):
    p = _palette(light)
    base = Image.new("RGBA", (w, h), _rgba(p["paper2"]))
    d = ImageDraw.Draw(base)
    # "tela de TV" arredondada
    m = h * 0.12
    d.rounded_rectangle([m, m, w - m, h - m], radius=int(h * 0.10), fill=_rgba(p["paper"]),
                        outline=_rgba(p["ink"]), width=max(2, h // 70))
    # faixas embaixo da tela
    sh = (h - 2 * m) * 0.06
    for i, c in enumerate(STRIPES):
        y = h - m - (len(STRIPES) - i + 1) * sh
        d.rectangle([m + h * 0.06, y, w - m - h * 0.06, y + sh * 0.7], fill=_rgba(c))
    cx, cy, r = w / 2, h * 0.42, h * 0.15
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_rgba(ORANGE), outline=_rgba(p["ink"]), width=max(2, h // 90))
    _play(d, cx + r * 0.05, cy, r * 0.62, _rgba(p["paper"]))
    return base.convert("RGB")


# ---------- ilustração para estados vazios (fundo transparente) ----------
def make_empty_art(w, h, bg=None, light=False):
    p = _palette(light)
    base = Image.new("RGBA", (w, h), _rgba(bg) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    # sol grande ao centro, apoiado numa linha de horizonte
    s = int(h * 0.78)
    sun = _sun(s, p["ink"], p["paper"])
    base.alpha_composite(sun, (int(w / 2 - s / 2), int(h * 0.06)))
    d = ImageDraw.Draw(base)
    y = h * 0.06 + s * 0.98
    d.line([(w * 0.18, y), (w * 0.82, y)], fill=_rgba(p["ink"]), width=max(3, h // 70))
    # fita cassete simples à esquerda e nota à direita (formas geométricas)
    cw, ch = w * 0.12, h * 0.26
    x0, y0 = w * 0.10, h * 0.40
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=int(h * 0.03), outline=_rgba(p["ink"]), width=max(3, h // 90))
    for k in (0.3, 0.7):
        r = ch * 0.16
        d.ellipse([x0 + cw * k - r, y0 + ch * 0.42 - r, x0 + cw * k + r, y0 + ch * 0.42 + r],
                  outline=_rgba(p["ink"]), width=max(3, h // 110))
    d.rectangle([x0 + cw * 0.15, y0 + ch * 0.72, x0 + cw * 0.85, y0 + ch * 0.80], fill=_rgba(TEAL))
    x1 = w * 0.80
    d.ellipse([x1, h * 0.58, x1 + h * 0.10, h * 0.66], fill=_rgba(ORANGE))
    d.rectangle([x1 + h * 0.085, h * 0.36, x1 + h * 0.10, h * 0.62], fill=_rgba(ORANGE))
    d.rectangle([x1 + h * 0.085, h * 0.36, x1 + h * 0.17, h * 0.395], fill=_rgba(ORANGE))
    return base if bg is None else base.convert("RGB")
