"""
Arte do Baixador de Vídeos: ícone e imagens de fundo com tema de multimídia.
Tudo é desenhado por código (Pillow), então não precisa de arquivos de imagem.

Rodar `python arte.py` gera o arquivo icone.ico (usado ao criar o .exe).
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PURPLE = (124, 58, 237)
PINK = (236, 72, 153)
CYAN = (34, 211, 238)
ORANGE = (245, 158, 11)
BG = (15, 17, 21)
CARD = (24, 27, 34)


# ---------- utilidades ----------
def _font(size, bold=True):
    names = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
             if bold else
             ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, int(size))
        except OSError:
            continue
    try:
        return ImageFont.load_default(int(size))
    except TypeError:
        return ImageFont.load_default()


def _hgrad(w, h, stops):
    """Gradiente horizontal com várias cores."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    n = len(stops) - 1
    for x in range(w):
        t = x / max(1, w - 1) * n
        i = min(int(t), n - 1)
        f = t - i
        c = tuple(int(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * f) for k in range(3))
        d.line([(x, 0), (x, h)], fill=c)
    return img


def _dgrad(w, h, stops):
    """Gradiente diagonal (canto superior esquerdo -> inferior direito)."""
    strip = _hgrad(w + h, 1, stops)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        img.paste(strip.crop((y, 0, y + w, 1)), (0, y))
    return img


def _rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255
    )
    return m


def _glow(base, box, color, blur, alpha=150):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=tuple(color) + (alpha,))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def _play(d, cx, cy, r, fill):
    """Triângulo de 'play' dentro de um círculo imaginário de raio r."""
    d.polygon(
        [(cx - r * 0.42, cy - r * 0.58), (cx - r * 0.42, cy + r * 0.58),
         (cx + r * 0.66, cy)],
        fill=fill,
    )


def _note(d, x, y, s, fill):
    """Duas colcheias ligadas. (x, y) = base da primeira cabeça de nota."""
    hw, hh = s * 0.34, s * 0.25
    stem = max(2, s * 0.07)
    gap = s * 0.62
    top = y - hh / 2 - s * 0.95
    for dx in (0, gap):
        d.ellipse([x + dx, y - hh, x + dx + hw, y], fill=fill)
        d.rectangle([x + dx + hw - stem, top, x + dx + hw, y - hh / 2], fill=fill)
    d.polygon(
        [(x + hw - stem, top), (x + gap + hw, top - s * 0.10),
         (x + gap + hw, top + s * 0.12), (x + hw - stem, top + s * 0.22)],
        fill=fill,
    )


def _bars(layer, x, y_base, heights, bw, gap, colors, alpha):
    d = ImageDraw.Draw(layer)
    for i, h in enumerate(heights):
        c = tuple(colors[i % len(colors)]) + (alpha,)
        x0 = x + i * (bw + gap)
        d.rounded_rectangle([x0, y_base - h, x0 + bw, y_base], radius=bw / 2, fill=c)


def _holes(d, length, y_positions, hole_w, hole_h, pitch, fill, x_start=None):
    x = pitch / 2 if x_start is None else x_start
    while x < length:
        for yy in y_positions:
            d.rounded_rectangle([x, yy, x + hole_w, yy + hole_h],
                                radius=hole_h * 0.3, fill=fill)
        x += pitch


def _filmstrip(length, height, base=(12, 10, 22, 255), hole=(230, 230, 245, 210)):
    """Tira de filme horizontal (RGBA) com furos e quadros coloridos."""
    strip = Image.new("RGBA", (length, height), base)
    d = ImageDraw.Draw(strip)
    hole_w, hole_h, pitch = height * 0.10, height * 0.09, height * 0.20
    _holes(d, length, [height * 0.06, height - height * 0.06 - hole_h],
           hole_w, hole_h, pitch, hole)
    margin = height * 0.22
    fh = int(height - 2 * margin)
    fw = int(fh * 1.45)
    palettes = [(PURPLE, PINK), (CYAN, PURPLE), (PINK, ORANGE), (PURPLE, CYAN)]
    x, i = int(height * 0.08), 0
    while x < length:
        c1, c2 = palettes[i % len(palettes)]
        frame = _dgrad(fw, fh, [c1, c2]).convert("RGBA")
        fd = ImageDraw.Draw(frame)
        _play(fd, fw * 0.5, fh * 0.5, fh * 0.28, (255, 255, 255, 150))
        strip.paste(frame, (x, int(margin)),
                    _rounded_mask((fw, fh), int(fh * 0.12)))
        x += fw + int(height * 0.06)
        i += 1
    return strip


def _fade(img, factor):
    a = img.getchannel("A").point(lambda v: int(v * factor))
    img.putalpha(a)
    return img


def _rounded_out(base, radius, bg=None):
    """Aplica cantos arredondados. bg=None -> cantos transparentes (serve p/ qualquer tema)."""
    w, h = base.size
    mask = _rounded_mask((w, h), radius)
    if bg is None:
        out = base.convert("RGBA")
        out.putalpha(mask)
        return out
    out = Image.new("RGB", (w, h), bg)
    out.paste(base.convert("RGB"), (0, 0), mask)
    return out


# ---------- ícone do aplicativo ----------
def make_icon(size=256):
    s = 4
    n = size * s
    base = _dgrad(n, n, [PURPLE, (190, 52, 180), PINK]).convert("RGBA")
    _glow(base, [-n * 0.2, -n * 0.3, n * 0.7, n * 0.5], (255, 255, 255), n * 0.12, 70)

    shadow = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    _play(ImageDraw.Draw(shadow), n * 0.5 + n * 0.02, n * 0.47 + n * 0.02, n * 0.31,
          (20, 0, 40, 130))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(n * 0.02)))

    top = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(top)
    _play(d, n * 0.5 + n * 0.02, n * 0.47, n * 0.31, (255, 255, 255, 255))
    _note(d, n * 0.60, n * 0.87, n * 0.27, (255, 255, 255, 240))
    base.alpha_composite(top)

    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(base, (0, 0), _rounded_mask((n, n), int(n * 0.22)))
    return out.resize((size, size), Image.LANCZOS)


def save_ico(path):
    make_icon(256).save(
        path, format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


# ---------- banner do topo ----------
def make_banner(width, height, title, subtitle, bg=None, scale=2, light=False):
    W, H = width * scale, height * scale
    if light:
        stops = [(243, 240, 255), (226, 217, 255), (236, 214, 250), (252, 211, 233)]
        ga = 0.55
    else:
        stops = [(18, 14, 32), (36, 20, 74), (92, 34, 150), (196, 52, 142)]
        ga = 1.0
    base = _hgrad(W, H, stops).convert("RGBA")
    _glow(base, [W * 0.55, -H * 0.6, W * 1.0, H * 1.0], PURPLE, H * 0.45, int(130 * ga))
    _glow(base, [W * 0.80, H * 0.05, W * 1.20, H * 1.4], PINK, H * 0.40, int(120 * ga))
    _glow(base, [W * 0.35, H * 0.55, W * 0.62, H * 1.6], CYAN, H * 0.35, int(50 * ga))

    if light:
        strip = _filmstrip(int(W * 0.62), int(H * 0.60),
                           base=(88, 63, 160, 255), hole=(243, 240, 255, 235))
        fade = 0.70
    else:
        strip = _filmstrip(int(W * 0.62), int(H * 0.60))
        fade = 0.55
    strip = _fade(strip.rotate(-7, expand=True, resample=Image.BICUBIC), fade)
    base.paste(strip, (int(W * 0.56), int(H * 0.30)), strip)

    ink = (91, 33, 182) if light else (255, 255, 255)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # anéis de som em volta do botão play
    cx, cy, r = W * 0.885, H * 0.5, H * 0.30
    for k, a in ((1.55, 55 if light else 40), (1.95, 38 if light else 25),
                 (2.4, 22 if light else 14)):
        d.ellipse([cx - r * k, cy - r * k, cx + r * k, cy + r * k],
                  outline=ink + (a,), width=max(2, scale * 2))
    # equalizador
    _bars(ov, W * 0.585, H * 0.88,
          [H * v for v in (0.22, 0.42, 0.30, 0.55, 0.36, 0.26, 0.46)],
          int(H * 0.06), int(H * 0.05), [CYAN, PINK, PURPLE if light else (255, 255, 255)],
          190 if light else 150)
    # notas musicais
    _note(d, W * 0.715, H * 0.55, H * 0.34, ink + (190 if light else 170,))
    _note(d, W * 0.60, H * 0.30, H * 0.20, ink + (130 if light else 110,))
    # botão play
    _glow(ov, [cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5], PINK, r * 0.5, 170)
    if light:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(109, 40, 217, 255))
        _play(d, cx, cy, r, (255, 255, 255, 255))
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 240))
        _play(d, cx, cy, r, (124, 58, 237, 255))
    base.alpha_composite(ov)

    # título e subtítulo
    if title:
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(txt)
        f1, f2 = _font(34 * scale), _font(13 * scale, bold=False)
        x, y1, y2 = 26 * scale, H * 0.20, H * 0.62
        if light:
            td.text((x + 2, y1 + 2), title, font=f1, fill=(255, 255, 255, 170))
            td.text((x, y1), title, font=f1, fill=(46, 16, 101, 255))
            td.text((x, y2), subtitle, font=f2, fill=(91, 33, 182, 255))
        else:
            td.text((x + 2, y1 + 3), title, font=f1, fill=(0, 0, 0, 120))
            td.text((x, y1), title, font=f1, fill=(255, 255, 255, 255))
            td.text((x, y2), subtitle, font=f2, fill=(224, 210, 255, 255))
        base.alpha_composite(txt)

    return _rounded_out(base, 18 * scale, bg)


# ---------- rodapé (marca d'água fica por cima, como texto) ----------
def make_footer(width, height, bg=None, scale=2, light=False):
    W, H = width * scale, height * scale
    if light:
        stops = [(233, 228, 252), (246, 243, 255), (233, 228, 252)]
        hole, note = (124, 58, 237, 60), (91, 33, 182, 150)
    else:
        stops = [(30, 22, 56), (17, 15, 26), (30, 22, 56)]
        hole, note = (230, 230, 245, 45), (196, 170, 255, 120)
    base = _hgrad(W, H, stops).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    hole_h, hole_w = 3 * scale, 7 * scale
    _holes(d, W, [2 * scale, H - 2 * scale - hole_h], hole_w, hole_h, 15 * scale, hole)
    # ícones pequenos nas pontas
    r = H * 0.30
    for cx in (W * 0.05, W * 0.95):
        d.ellipse([cx - r, H / 2 - r, cx + r, H / 2 + r], fill=(124, 58, 237, 255))
        _play(d, cx, H / 2, r, (255, 255, 255, 255))
    _note(d, W * 0.10, H * 0.78, H * 0.42, note)
    _note(d, W * 0.89, H * 0.78, H * 0.42, note)
    base.alpha_composite(ov)
    return _rounded_out(base, 10 * scale, bg)


# ---------- miniatura padrão (quando ainda não há vídeo) ----------
def make_placeholder(w, h, light=False):
    if light:
        stops = [(233, 228, 252), (247, 244, 255), (233, 228, 252)]
        band_c, hole_c = (206, 198, 240, 255), (250, 248, 255, 230)
        circle, tri, note_a, glow_a = (124, 58, 237, 255), (255, 255, 255, 255), 55, 90
        note_c = (124, 58, 237)
    else:
        stops = [(26, 20, 48), (50, 26, 92), (26, 20, 48)]
        band_c, hole_c = (10, 8, 18, 255), (230, 230, 245, 60)
        circle, tri, note_a, glow_a = (255, 255, 255, 235), PURPLE + (255,), 45, 170
        note_c = (255, 255, 255)
    base = _dgrad(w, h, stops).convert("RGBA")
    band = h * 0.14
    bd = ImageDraw.Draw(base)
    bd.rectangle([0, 0, w, band], fill=band_c)
    bd.rectangle([0, h - band, w, h], fill=band_c)
    r = h * 0.20
    _glow(base, [w / 2 - r * 2, h / 2 - r * 2, w / 2 + r * 2, h / 2 + r * 2],
          PURPLE, r * 0.8, glow_a)
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    hh, hw, pitch = band * 0.42, band * 0.55, band * 1.15
    _holes(d, w, [band * 0.29, h - band * 0.29 - hh], hw, hh, pitch, hole_c)
    d.ellipse([w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r], fill=circle)
    _play(d, w / 2, h / 2, r, tri)
    _note(d, w * 0.08, h * 0.70, h * 0.24, note_c + (note_a,))
    _note(d, w * 0.84, h * 0.50, h * 0.18, note_c + (note_a - 5,))
    base.alpha_composite(ov)
    return base.convert("RGB")


# ---------- ilustração para estados vazios (fundo = cor do app) ----------
def make_empty_art(w, h, bg=None, light=False):
    """Ilustração para estados vazios. Fundo transparente; light=True usa tons escuros
    (para o tema claro)."""
    base = Image.new("RGBA", (w, h), (tuple(bg) + (255,)) if bg else (0, 0, 0, 0))
    ink = (76, 29, 149, 235) if light else (255, 255, 255, 240)
    note_col = (91, 33, 182, 150) if light else (255, 255, 255, 130)
    strip_fade = 0.22 if light else 0.35
    ga = 0.7 if light else 1.0
    cx, cy = w * 0.5, h * 0.48
    _glow(base, [cx - h * 0.9, cy - h * 0.8, cx + h * 0.9, cy + h * 0.8], PURPLE,
          h * 0.25, int(120 * ga))
    _glow(base, [w * 0.68, h * 0.1, w * 0.98, h * 1.1], PINK, h * 0.25, int(70 * ga))
    _glow(base, [w * 0.02, h * 0.1, w * 0.32, h * 1.1], CYAN, h * 0.25, int(55 * ga))

    for side, angle in ((0.02, 9), (0.60, -9)):
        strip = _fade(_filmstrip(int(w * 0.38), int(h * 0.42)).rotate(
            angle, expand=True, resample=Image.BICUBIC), strip_fade)
        base.paste(strip, (int(w * side), int(h * 0.30)), strip)

    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # lupa com play
    r = h * 0.27
    ring = max(4, int(h * 0.05))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=ring)
    a = r * 0.72
    d.line([(cx + a, cy + a), (cx + r * 1.55, cy + r * 1.55)], fill=ink, width=ring * 2)
    d.ellipse([cx + r * 1.55 - ring, cy + r * 1.55 - ring,
               cx + r * 1.55 + ring, cy + r * 1.55 + ring], fill=ink)
    _play(d, cx, cy, r * 0.62, PINK + (255,))
    # notas e equalizador
    _note(d, w * 0.26, h * 0.42, h * 0.22, note_col)
    _note(d, w * 0.70, h * 0.60, h * 0.26, note_col)
    _bars(ov, w * 0.11, h * 0.86, [h * v for v in (0.16, 0.30, 0.22, 0.38, 0.26)],
          int(h * 0.05), int(h * 0.04), [CYAN, PURPLE], 170)
    _bars(ov, w * 0.80, h * 0.86, [h * v for v in (0.26, 0.36, 0.20, 0.32, 0.16)],
          int(h * 0.05), int(h * 0.04), [PINK, ORANGE], 170)
    base.alpha_composite(ov)
    return base if bg is None else base.convert("RGB")


# ---------- imagens do assistente de instalação (Inno Setup) ----------
def make_wizard_large(w=164, h=314):
    """Imagem lateral da tela de boas-vindas do instalador."""
    sc = 3
    W, H = w * sc, h * sc
    base = _dgrad(W, H, [(20, 14, 44), (76, 29, 149), (196, 52, 142)]).convert("RGBA")
    _glow(base, [-W * 0.3, H * 0.05, W * 1.3, H * 0.55], PURPLE, W * 0.25, 150)
    _glow(base, [W * 0.1, H * 0.6, W * 1.2, H * 1.2], PINK, W * 0.3, 110)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # furos de filme nas bordas
    hh, hw, pitch = 7 * sc, 10 * sc, 22 * sc
    y = pitch / 2
    while y < H:
        for x in (5 * sc, W - 5 * sc - hw):
            d.rounded_rectangle([x, y, x + hw, y + hh], radius=2 * sc,
                                fill=(255, 255, 255, 60))
        y += pitch
    # equalizador e notas
    _bars(ov, W * 0.22, H * 0.90, [H * v for v in (0.05, 0.09, 0.06, 0.11, 0.07, 0.04, 0.08)],
          int(W * 0.07), int(W * 0.04), [CYAN, PINK, (255, 255, 255)], 170)
    _note(d, W * 0.22, H * 0.74, W * 0.22, (255, 255, 255, 150))
    _note(d, W * 0.58, H * 0.66, W * 0.16, (255, 255, 255, 110))
    base.alpha_composite(ov)
    icon = make_icon(int(W * 0.62))
    base.alpha_composite(icon, (int((W - icon.width) / 2), int(H * 0.17)))
    return base.resize((w, h), Image.LANCZOS).convert("RGB")


def make_wizard_small(size=55):
    """Ícone pequeno do canto das demais telas do instalador (fundo branco)."""
    icon = make_icon(size * 4).resize((size, size), Image.LANCZOS)
    out = Image.new("RGB", (size, size), (255, 255, 255))
    out.paste(icon, (0, 0), icon)
    return out
