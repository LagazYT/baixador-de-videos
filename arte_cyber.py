"""
Arte do Baixador de Vídeos: ícone e imagens da interface em estilo cyberpunk
(amarelo, vermelho e cinza). Tudo é desenhado por código (Pillow), então não
precisa de arquivos de imagem.

Rodar `python arte.py` gera o icone.ico, as imagens do instalador e os ícones
da extensão do navegador.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------- paleta ----------
YELLOW = (247, 214, 30)
YELLOW_DIM = (176, 150, 18)
RED = (232, 38, 58)
RED_DIM = (150, 24, 38)
INK = (12, 12, 14)
BG = (16, 16, 19)
CARD = (26, 27, 31)
GRAY = (46, 48, 54)
GRAY_MID = (96, 98, 106)
GRAY_LIGHT = (168, 170, 177)
PAPER = (231, 232, 235)
PAPER_2 = (214, 216, 221)
WHITE = (245, 245, 247)


# ---------- utilidades ----------
def _font(size, bold=True):
    """Fonte técnica: Bahnschrift (Windows 10/11), com alternativas."""
    names = (["bahnschrift.ttf", "DejaVuSansCondensed-Bold.ttf", "arialbd.ttf",
              "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
             if bold else
             ["bahnschrift.ttf", "DejaVuSansCondensed.ttf", "arial.ttf",
              "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    for name in names:
        try:
            f = ImageFont.truetype(name, int(size))
            if name == "bahnschrift.ttf":  # fonte variável: escolhe o peso
                try:
                    f.set_variation_by_name("Bold" if bold else "SemiLight")
                except Exception:  # noqa: BLE001
                    pass
            return f
        except OSError:
            continue
    try:
        return ImageFont.load_default(int(size))
    except TypeError:
        return ImageFont.load_default()


def _rgba(c, a=255):
    return tuple(c[:3]) + (int(a),)


def _chamfer_poly(w, h, cut, corners=("tl", "br")):
    """Retângulo com cantos cortados em diagonal (visual 'HUD')."""
    tl = cut if "tl" in corners else 0
    tr = cut if "tr" in corners else 0
    br = cut if "br" in corners else 0
    bl = cut if "bl" in corners else 0
    return [(tl, 0), (w - 1 - tr, 0), (w - 1, tr), (w - 1, h - 1 - br),
            (w - 1 - br, h - 1), (bl, h - 1), (0, h - 1 - bl), (0, tl)]


def _chamfer_mask(size, cut, corners=("tl", "br")):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(_chamfer_poly(size[0], size[1], cut, corners), fill=255)
    return m


def _finish(base, cut, bg=None, corners=("tl", "br")):
    """Aplica os cantos chanfrados. bg=None -> cantos transparentes."""
    mask = _chamfer_mask(base.size, cut, corners)
    if bg is None:
        out = base.convert("RGBA")
        out.putalpha(mask)
        return out
    out = Image.new("RGB", base.size, bg)
    out.paste(base.convert("RGB"), (0, 0), mask)
    return out


def _glow(base, box, color, blur, alpha=120):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=_rgba(color, alpha))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def _scanlines(base, step, alpha, color=(0, 0, 0)):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(0, base.size[1], step):
        d.line([(0, y), (base.size[0], y)], fill=_rgba(color, alpha))
    base.alpha_composite(layer)


def _grid(d, w, h, step, color, x0=0):
    x = x0
    while x < w:
        d.line([(x, 0), (x, h)], fill=color)
        x += step
    y = 0
    while y < h:
        d.line([(x0, y), (w, y)], fill=color)
        y += step


def _hazard(size, c1, c2, stripe, angle_right=True):
    """Faixa de 'perigo' com listras diagonais."""
    w, h = size
    img = Image.new("RGBA", size, _rgba(c1))
    d = ImageDraw.Draw(img)
    x = -h * 2
    while x < w + h * 2:
        if angle_right:
            d.polygon([(x, h), (x + stripe, h), (x + stripe + h, 0), (x + h, 0)], fill=_rgba(c2))
        else:
            d.polygon([(x, 0), (x + stripe, 0), (x + stripe + h, h), (x + h, h)], fill=_rgba(c2))
        x += stripe * 2
    return img


def _play(d, cx, cy, r, fill):
    d.polygon([(cx - r * 0.45, cy - r * 0.62), (cx - r * 0.45, cy + r * 0.62),
               (cx + r * 0.68, cy)], fill=fill)


def _arrow_down(d, cx, top, bottom, width, fill):
    head = width * 1.9
    d.rectangle([cx - width / 2, top, cx + width / 2, bottom - head * 0.7], fill=fill)
    d.polygon([(cx - head, bottom - head), (cx + head, bottom - head), (cx, bottom)], fill=fill)


def _brackets(d, box, length, width, fill):
    """Cantoneiras de mira nos 4 cantos de uma caixa."""
    x0, y0, x1, y1 = box
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(x, y), (x + sx * length, y)], fill=fill, width=width)
        d.line([(x, y), (x, y + sy * length)], fill=fill, width=width)


def _bars(d, x, y_base, heights, bw, gap, colors):
    for i, h in enumerate(heights):
        x0 = x + i * (bw + gap)
        d.rectangle([x0, y_base - h, x0 + bw, y_base], fill=colors[i % len(colors)])


def _glitch_text(base, xy, text, font, main, offset_color, off):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    d.text((x - off, y + off * 0.4), text, font=font, fill=_rgba(offset_color, 210))
    d.text((x, y), text, font=font, fill=_rgba(main))
    base.alpha_composite(layer)
    return d.textbbox((x, y), text, font=font)


# ---------- ícone do aplicativo ----------
def make_icon(size=256):
    s = 4
    n = size * s
    base = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    tile = Image.new("RGBA", (n, n), _rgba(BG))
    td = ImageDraw.Draw(tile)
    _grid(td, n, n, n // 8, _rgba(GRAY, 255))
    _scanlines(tile, max(4, n // 64), 70)
    base.paste(tile, (0, 0), _chamfer_mask((n, n), int(n * 0.2)))

    d = ImageDraw.Draw(base)
    # moldura amarela chanfrada
    border = int(n * 0.045)
    poly = _chamfer_poly(n, n, int(n * 0.2))
    d.line(poly + [poly[0]], fill=_rgba(YELLOW), width=border, joint="curve")
    # play em vermelho (deslocado) + amarelo
    cx, cy, r = n * 0.47, n * 0.44, n * 0.30
    _play(d, cx - n * 0.035, cy + n * 0.012, r, _rgba(RED))
    _play(d, cx, cy, r, _rgba(YELLOW))
    # barra de download
    d.rectangle([n * 0.22, n * 0.78, n * 0.78, n * 0.83], fill=_rgba(RED))
    d.rectangle([n * 0.22, n * 0.78, n * 0.50, n * 0.83], fill=_rgba(YELLOW))
    return base.resize((size, size), Image.LANCZOS)


def save_ico(path):
    make_icon(256).save(
        path, format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


# ---------- banner do topo ----------
def make_banner(width, height, title, subtitle, bg=None, scale=2, light=False):
    W, H = width * scale, height * scale
    sc = scale
    if light:
        back, grid, sub_col, title_col, tag_col = PAPER, _rgba(PAPER_2), (70, 72, 80), INK, (90, 92, 100)
    else:
        back, grid, sub_col, title_col, tag_col = BG, _rgba(GRAY, 200), GRAY_LIGHT, WHITE, GRAY_MID
    base = Image.new("RGBA", (W, H), _rgba(back))
    d = ImageDraw.Draw(base)
    _grid(d, W, H, 22 * sc, grid, x0=int(W * 0.45))
    if not light:
        _glow(base, [W * 0.55, -H * 0.8, W * 1.1, H * 1.4], RED, H * 0.55, 60)
        _glow(base, [W * 0.70, -H * 0.2, W * 1.05, H * 1.2], YELLOW, H * 0.45, 35)

    # faixa de perigo na direita
    hz_w = int(W * 0.13)
    hz = _hazard((hz_w, H), YELLOW, INK, 11 * sc)
    base.paste(hz, (W - hz_w, 0), hz)
    d = ImageDraw.Draw(base)
    d.rectangle([W - hz_w - 5 * sc, 0, W - hz_w - 3 * sc, H], fill=_rgba(RED))

    # play com glitch
    cx, cy, r = W * 0.745, H * 0.5, H * 0.36
    _brackets(d, (cx - r * 1.2, cy - r * 1.05, cx + r * 1.2, cy + r * 1.05), int(r * 0.35),
              max(2, sc * 2), _rgba(YELLOW))
    _play(d, cx - 5 * sc, cy + 2 * sc, r, _rgba(RED, 230))
    _play(d, cx, cy, r, _rgba(YELLOW))
    for i, frac in enumerate((0.30, 0.62)):  # fatias deslocadas (efeito glitch)
        y = cy - r * 0.62 + r * 1.24 * frac
        x_end = cx - r * 0.45 + (r * 1.13) * (1 - abs(frac - 0.5) * 2) - 2 * sc
        d.rectangle([cx - r * 0.45 + 6 * sc, y, x_end + 6 * sc, y + 2 * sc],
                    fill=_rgba(BG if not light else PAPER))
    # barras de dados
    _bars(d, W * 0.565, H * 0.84, [H * v for v in (0.18, 0.32, 0.24, 0.42, 0.28, 0.16)],
          int(5 * sc), int(4 * sc), [_rgba(GRAY_MID), _rgba(YELLOW), _rgba(GRAY_MID), _rgba(RED)])

    # barra lateral amarela + título
    d.rectangle([0, 0, 6 * sc, H], fill=_rgba(YELLOW))
    d.rectangle([0, H * 0.62, 6 * sc, H], fill=_rgba(RED))
    if title:
        f_tag = _font(9 * sc)
        f_title = _font(33 * sc)
        f_sub = _font(12 * sc, bold=False)
        x = 26 * sc
        d.text((x, H * 0.10), "// SISTEMA DE DOWNLOAD  ·  v1", font=f_tag, fill=_rgba(tag_col))
        bbox = _glitch_text(base, (x, H * 0.20), title.upper(), f_title, title_col, RED, 3 * sc)
        d = ImageDraw.Draw(base)
        y_line = bbox[3] + 12 * sc
        d.rectangle([x, y_line, x + 40 * sc, y_line + 3 * sc], fill=_rgba(YELLOW))
        d.text((x + 50 * sc, y_line - 7 * sc), subtitle, font=f_sub, fill=_rgba(sub_col))

    _scanlines(base, 3 * sc, 40 if not light else 14)
    return _finish(base, 16 * sc, bg)


# ---------- rodapé (o texto da marca d'água fica por cima) ----------
def make_footer(width, height, bg=None, scale=2, light=False):
    W, H = width * scale, height * scale
    back = PAPER_2 if light else (20, 20, 23)
    tick = _rgba(GRAY_MID if light else GRAY, 255)
    base = Image.new("RGBA", (W, H), _rgba(back))
    d = ImageDraw.Draw(base)
    # réguas finas
    for x in range(0, W, 8 * scale):
        hgt = 5 * scale if (x // (8 * scale)) % 5 == 0 else 2 * scale
        d.line([(x, H - hgt), (x, H)], fill=tick)
    d.line([(0, 0), (W, 0)], fill=_rgba(YELLOW), width=2 * scale)
    # faixas de perigo nas pontas
    hz_w = int(W * 0.09)
    for x, right in ((0, True), (W - hz_w, False)):
        hz = _hazard((hz_w, H), YELLOW, INK, 7 * scale, right)
        base.paste(hz, (x, 0), hz)
    d = ImageDraw.Draw(base)
    d.rectangle([hz_w, 0, hz_w + 3 * scale, H], fill=_rgba(RED))
    d.rectangle([W - hz_w - 3 * scale, 0, W - hz_w, H], fill=_rgba(RED))
    f = _font(8 * scale, bold=False)
    col = _rgba((80, 82, 90) if light else GRAY_MID)
    d.text((hz_w + 12 * scale, H * 0.30), "SYS.ONLINE", font=f, fill=col)
    txt = "DL//0x4C47"
    tw = d.textlength(txt, font=f)
    d.text((W - hz_w - 12 * scale - tw, H * 0.30), txt, font=f, fill=col)
    return _finish(base, 8 * scale, bg)


# ---------- miniatura padrão (quando ainda não há vídeo) ----------
def make_placeholder(w, h, light=False):
    if light:
        back, grid, txt = PAPER_2, _rgba((200, 202, 208)), (60, 62, 70)
    else:
        back, grid, txt = (22, 22, 26), _rgba((38, 39, 44)), GRAY_LIGHT
    base = Image.new("RGBA", (w, h), _rgba(back))
    d = ImageDraw.Draw(base)
    _grid(d, w, h, max(8, h // 9), grid)
    m = h * 0.09
    _brackets(d, (m, m, w - m, h - m), int(h * 0.12), max(2, h // 90), _rgba(YELLOW))
    cx, cy, r = w / 2, h * 0.44, h * 0.17
    _play(d, cx - h * 0.018, cy + h * 0.006, r, _rgba(RED))
    _play(d, cx, cy, r, _rgba(YELLOW))
    f = _font(max(9, h * 0.075))
    label = "AGUARDANDO SINAL"
    tw = d.textlength(label, font=f)
    d.text((cx - tw / 2, h * 0.70), label, font=f, fill=_rgba(txt))
    d.rectangle([cx - tw / 2, h * 0.70 + h * 0.105, cx - tw / 2 + tw * 0.25, h * 0.70 + h * 0.12],
                fill=_rgba(RED))
    _scanlines(base, max(2, h // 60), 50 if not light else 18)
    return base.convert("RGB")


# ---------- ilustração para estados vazios (fundo transparente) ----------
def make_empty_art(w, h, bg=None, light=False):
    base = Image.new("RGBA", (w, h), _rgba(bg) if bg else (0, 0, 0, 0))
    line = _rgba((60, 62, 70) if light else GRAY_MID, 255)
    faint = _rgba((150, 152, 160) if light else GRAY, 255)
    d = ImageDraw.Draw(base)
    cx, cy = w * 0.5, h * 0.5
    # retícula de mira
    for k, a in ((0.42, 255), (0.30, 255)):
        r = h * k
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=faint if a else line, width=max(2, h // 120))
    r = h * 0.42
    for start in (300, 120):
        d.arc([cx - r, cy - r, cx + r, cy + r], start, start + 70, fill=_rgba(YELLOW), width=max(4, h // 60))
    d.line([(cx - r * 1.35, cy), (cx - r * 0.75, cy)], fill=line, width=max(2, h // 150))
    d.line([(cx + r * 0.75, cy), (cx + r * 1.35, cy)], fill=line, width=max(2, h // 150))
    _play(d, cx - h * 0.02, cy + h * 0.008, h * 0.17, _rgba(RED))
    _play(d, cx, cy, h * 0.17, _rgba(YELLOW))
    # linhas de dados dos lados
    for side in (-1, 1):
        x0 = cx + side * w * 0.22
        for i in range(5):
            y = h * (0.26 + i * 0.12)
            ln = w * (0.06 + (i * 37 % 5) * 0.02)
            xa, xb = (x0, x0 + ln) if side > 0 else (x0 - ln, x0)
            d.rectangle([xa, y, xb, y + max(3, h // 70)],
                        fill=_rgba(YELLOW) if i == 2 else (_rgba(RED) if i == 4 else faint))
    # faixas de perigo pequenas
    hz = _hazard((int(w * 0.10), int(h * 0.05)), YELLOW, INK, max(6, h // 40))
    base.paste(hz, (int(w * 0.08), int(h * 0.86)), hz)
    base.paste(hz, (int(w * 0.82), int(h * 0.09)), hz)
    return base if bg is None else base.convert("RGB")


# ---------- imagens do assistente de instalação (Inno Setup) ----------
def make_wizard_large(w=164, h=314):
    sc = 3
    W, H = w * sc, h * sc
    base = Image.new("RGBA", (W, H), _rgba(BG))
    d = ImageDraw.Draw(base)
    _grid(d, W, H, 20 * sc, _rgba(GRAY, 180))
    _glow(base, [-W * 0.4, H * 0.05, W * 1.4, H * 0.6], RED, W * 0.3, 70)
    hz = _hazard((W, 14 * sc), YELLOW, INK, 9 * sc)
    base.paste(hz, (0, H - 14 * sc), hz)
    d = ImageDraw.Draw(base)
    d.rectangle([0, 0, 5 * sc, H], fill=_rgba(YELLOW))
    icon = make_icon(int(W * 0.66))
    base.alpha_composite(icon, (int((W - icon.width) / 2), int(H * 0.16)))
    f = _font(15 * sc)
    for i, t in enumerate(("BAIXADOR", "DE VÍDEOS")):
        tw = d.textlength(t, font=f)
        _glitch_text(base, ((W - tw) / 2, H * 0.60 + i * 19 * sc), t, f, WHITE, RED, 2 * sc)
    d = ImageDraw.Draw(base)
    f2 = _font(8 * sc, bold=False)
    t = "PRODUZIDO POR LAGAZ"
    d.text(((W - d.textlength(t, font=f2)) / 2, H * 0.78), t, font=f2, fill=_rgba(GRAY_LIGHT))
    _scanlines(base, 3 * sc, 45)
    return base.resize((w, h), Image.LANCZOS).convert("RGB")


def make_wizard_small(size=55):
    icon = make_icon(size * 4).resize((size, size), Image.LANCZOS)
    out = Image.new("RGB", (size, size), (255, 255, 255))
    out.paste(icon, (0, 0), icon)
    return out
