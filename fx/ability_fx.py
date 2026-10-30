"""Textures for the new abilities (PIL, drawn 4x and downsampled):
  timestop_clock.png   clock face shown above the prehistoric fish while time is stopped
  timestop_hand.png    its hand, drawn from the image centre up (an ImageLabel rotates about its centre)
  menacing_go.png      the manga "menacing" katakana (go) floating around the time stopper
  anger_vein.png       manga anger mark above the raging fish
  bite_jaw.png         a row of fangs on a gum band (upper jaw; the lower one is the same image turned 180)
  impact_star.png      comic impact burst for the bite and the hits that land when time resumes
  slow_ring.png        swirl ring laid flat around the crocodile while its jaws are open (slow zone)
  slow_icon.png        snail shown over slowed fish

    python3 fx/ability_fx.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SS = 4  # supersampling

OUTLINE = (24, 14, 36, 255)
GOLD = (255, 204, 51, 255)
GOLD_DARK = (196, 128, 20, 255)


def canvas(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def finish(img, name):
    w, h = img.size
    img = img.resize((w // SS, h // SS), Image.LANCZOS)
    img.save(os.path.join(HERE, name))
    return img


def outlined(mask, fill, outline=OUTLINE, width=6, shadow=None):
    """Colour a white-on-black mask with an outline (and an optional offset shadow for a 3D look)."""
    w, h = mask.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grow = mask.filter(ImageFilter.MaxFilter(2 * width * SS + 1))
    if shadow:
        dx, dy, col = shadow
        sh = Image.new("RGBA", (w, h), col)
        moved = Image.new("L", (w, h), 0)
        moved.paste(grow, (dx * SS, dy * SS))
        out.paste(sh, (0, 0), moved)
    out.paste(Image.new("RGBA", (w, h), outline), (0, 0), grow)
    if isinstance(fill, Image.Image):
        out.paste(fill, (0, 0), mask)
    else:
        out.paste(Image.new("RGBA", (w, h), fill), (0, 0), mask)
    return out


def vgradient(w, h, top, bottom):
    g = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        a = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - a) + bottom[i] * a) for i in range(4)))
    return g


def clock():
    S = 512 * SS
    img = canvas(512, 512)
    d = ImageDraw.Draw(img)
    c = S / 2

    def circle(r, **kw):
        d.ellipse([c - r, c - r, c + r, c + r], **kw)

    circle(252 * SS, fill=OUTLINE)
    circle(244 * SS, fill=GOLD)
    circle(226 * SS, fill=OUTLINE)
    circle(220 * SS, fill=(42, 18, 80, 215))
    circle(150 * SS, outline=(255, 204, 51, 150), width=5 * SS)
    for n in range(12):
        a = n * math.pi / 6
        big = n % 3 == 0
        r0, r1 = (150 if big else 172) * SS, 212 * SS
        hw = (16 if big else 7) * SS
        ux, uy = math.sin(a), -math.cos(a)
        px, py = -uy, ux
        pts = [(c + ux * r0 + px * hw, c + uy * r0 + py * hw), (c + ux * r1 + px * hw, c + uy * r1 + py * hw),
               (c + ux * r1 - px * hw, c + uy * r1 - py * hw), (c + ux * r0 - px * hw, c + uy * r0 - py * hw)]
        d.polygon(pts, fill=GOLD, outline=OUTLINE, width=4 * SS)
    circle(22 * SS, fill=OUTLINE)
    circle(15 * SS, fill=GOLD)
    return finish(img, "timestop_clock.png")


def hand():
    S = 512 * SS
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    c = S / 2
    d.polygon([(c - 14 * SS, c + 40 * SS), (c - 9 * SS, c - 120 * SS), (c - 26 * SS, c - 128 * SS),
               (c, c - 196 * SS), (c + 26 * SS, c - 128 * SS), (c + 9 * SS, c - 120 * SS),
               (c + 14 * SS, c + 40 * SS)], fill=255)
    d.ellipse([c - 26 * SS, c - 26 * SS, c + 26 * SS, c + 26 * SS], fill=255)
    fill = vgradient(S, S, (255, 236, 140, 255), (214, 140, 24, 255))
    img = outlined(mask, fill, width=5)
    return finish(img, "timestop_hand.png")


def menacing():
    S = 256 * SS
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)

    def bar(x0, y0, x1, y1, t):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        px, py = -dy / n * t / 2, dx / n * t / 2
        d.polygon([(SS * (x0 + px), SS * (y0 + py)), (SS * (x1 + px), SS * (y1 + py)),
                   (SS * (x1 - px), SS * (y1 - py)), (SS * (x0 - px), SS * (y0 - py))], fill=255)

    # the katakana "ko" (a box open on the left) and the two dakuten ticks, chunky and slanted
    bar(37, 80, 161, 74, 32)
    bar(147, 74, 153, 202, 32)
    bar(31, 204, 167, 198, 34)
    bar(171, 30, 184, 62, 15)
    bar(193, 24, 206, 56, 15)
    mask = mask.transform(mask.size, Image.AFFINE, (1, 0.22, -0.22 * S * 0.55, 0, 1, 0), Image.BICUBIC)
    fill = vgradient(S, S, (236, 120, 255, 255), (128, 28, 186, 255))
    img = outlined(mask, fill, outline=(20, 6, 30, 255), width=6, shadow=(9, 9, (70, 10, 100, 255)))
    return finish(img, "menacing_go.png")


def anger():
    S = 256 * SS
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    c = S / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = c + sx * 96 * SS, c + sy * 96 * SS
            r = 74 * SS
            # the arc of each corner circle that faces the middle
            mid = math.degrees(math.atan2(-sy, -sx))
            d.arc([cx - r, cy - r, cx + r, cy + r], mid - 38, mid + 38, fill=255, width=28 * SS)
    img = outlined(mask, (232, 36, 44, 255), outline=(90, 6, 12, 255), width=6)
    return finish(img, "anger_vein.png")


def jaw():
    W, H = 512 * SS, 192 * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gum = Image.new("L", (W, H), 0)
    teeth = Image.new("L", (W, H), 0)
    dg = ImageDraw.Draw(gum)
    dt = ImageDraw.Draw(teeth)
    dg.rounded_rectangle([12 * SS, 10 * SS, 500 * SS, 62 * SS], radius=26 * SS, fill=255)
    n = 7
    for k in range(n):
        x0 = 30 + k * (452 / n)
        x1 = x0 + 452 / n - 6
        tip = 176 if k in (0, n - 1, 3) else 150
        dt.polygon([(x0 * SS, 50 * SS), (x1 * SS, 50 * SS), ((x0 + x1) / 2 * SS, tip * SS)], fill=255)
    gum_img = outlined(gum, (150, 28, 40, 255), outline=(40, 8, 12, 255), width=5)
    teeth_img = outlined(teeth, (255, 250, 236, 255), outline=(40, 30, 30, 255), width=5)
    img.alpha_composite(teeth_img)
    img.alpha_composite(gum_img)
    return finish(img, "bite_jaw.png")


def star():
    S = 256 * SS
    c = S / 2
    outer = Image.new("L", (S, S), 0)
    inner = Image.new("L", (S, S), 0)
    for m, (r0, r1) in ((outer, (118, 58)), (inner, (82, 40))):
        pts = []
        for k in range(24):
            a = k * math.pi / 12 + 0.13
            r = (r0 if k % 2 == 0 else r1) * SS * (1.0 if k % 4 else 0.86)
            pts.append((c + r * math.cos(a), c + r * math.sin(a)))
        ImageDraw.Draw(m).polygon(pts, fill=255)
    img = outlined(outer, (255, 255, 255, 255), outline=(36, 22, 14, 255), width=6)
    img.paste(Image.new("RGBA", (S, S), (255, 214, 64, 255)), (0, 0), inner)
    return finish(img, "impact_star.png")


def slow_ring():
    S = 512 * SS
    c = S / 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    band = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(band)
    d.ellipse([c - 250 * SS, c - 250 * SS, c + 250 * SS, c + 250 * SS], fill=110)
    d.ellipse([c - 196 * SS, c - 196 * SS, c + 196 * SS, c + 196 * SS], fill=0)
    img.paste(Image.new("RGBA", (S, S), (70, 200, 140, 255)), (0, 0), band.filter(ImageFilter.GaussianBlur(6 * SS)))
    arms = Image.new("L", (S, S), 0)
    da = ImageDraw.Draw(arms)
    for k in range(6):
        base = k * math.pi / 3
        pts = []
        for s in range(40):
            u = s / 39
            r = (246 - 120 * u) * SS
            a = base + 1.3 * u
            pts.append((c + r * math.cos(a), c + r * math.sin(a)))
        da.line(pts, fill=255, width=16 * SS, joint="curve")
        # arrow head pointing inward along the swirl
        ex, ey = pts[-1]
        a = base + 1.3
        tx, ty = -math.cos(a), -math.sin(a)
        nx, ny = -ty, tx
        da.polygon([(ex + tx * 34 * SS, ey + ty * 34 * SS), (ex + nx * 26 * SS, ey + ny * 26 * SS),
                    (ex - nx * 26 * SS, ey - ny * 26 * SS)], fill=255)
    img.alpha_composite(outlined(arms, (170, 255, 200, 230), outline=(16, 70, 50, 230), width=4))
    return finish(img, "slow_ring.png")


def snail():
    S = 256 * SS
    body = Image.new("L", (S, S), 0)
    shell = Image.new("L", (S, S), 0)
    db = ImageDraw.Draw(body)
    ds = ImageDraw.Draw(shell)
    db.rounded_rectangle([30 * SS, 150 * SS, 226 * SS, 204 * SS], radius=26 * SS, fill=255)
    db.line([(64 * SS, 156 * SS), (48 * SS, 92 * SS)], fill=255, width=12 * SS)
    db.line([(84 * SS, 156 * SS), (88 * SS, 86 * SS)], fill=255, width=12 * SS)
    for x, y in ((48, 88), (88, 82)):
        db.ellipse([(x - 13) * SS, (y - 13) * SS, (x + 13) * SS, (y + 13) * SS], fill=255)
    ds.ellipse([96 * SS, 54 * SS, 216 * SS, 174 * SS], fill=255)
    img = outlined(body, (200, 230, 120, 255), outline=(36, 40, 20, 255), width=6)
    img.alpha_composite(outlined(shell, (226, 140, 58, 255), outline=(36, 24, 12, 255), width=6))
    d = ImageDraw.Draw(img)
    pts = []
    for s in range(120):
        u = s / 119
        a = u * 4.2 * math.pi
        r = (50 - 44 * u) * SS
        pts.append((156 * SS + r * math.cos(a), 114 * SS + r * math.sin(a)))
    d.line(pts, fill=(110, 52, 14, 255), width=7 * SS, joint="curve")
    for x, y in ((48, 88), (88, 82)):
        d.ellipse([(x - 5) * SS, (y - 5) * SS, (x + 5) * SS, (y + 5) * SS], fill=(20, 20, 20, 255))
    return finish(img, "slow_icon.png")


def preview(images, path):
    """All textures side by side on the two backgrounds used for the other effects."""
    tiles = [im.resize((200, int(200 * im.size[1] / im.size[0])), Image.LANCZOS) for im in images]
    h = max(t.size[1] for t in tiles) + 20
    out = Image.new("RGBA", (len(tiles) * 210 + 10, 2 * h), (0, 0, 0, 255))
    for row, bg in enumerate(((134, 196, 236, 255), (24, 78, 110, 255))):
        out.paste(Image.new("RGBA", (out.size[0], h), bg), (0, row * h))
        for n, t in enumerate(tiles):
            out.alpha_composite(t, (10 + n * 210, row * h + 10))
    out.convert("RGB").save(path)


if __name__ == "__main__":
    ims = [clock(), hand(), menacing(), anger(), jaw(), star(), slow_ring(), snail()]
    preview(ims, os.path.join(HERE, "ability_fx_preview.png"))
    print("ok")
