# "Titan" transformation strike, cartoon style (outlines, flat bands of colour), for the Titan power-up.
#
#   blender -b --factory-startup --python titan_lightning.py -- <out_dir>
#
# titan_lightning_flipbook.png : 4x4 flipbook (1024x1024, 256 px frames, ~0.6 s at 27 fps). A thin leader
#   flickers down, a thick yellow-orange bolt slams into the impact point, the frame flashes, branches crackle
#   out and black smoke puffs up around the impact (the yellow / black contrast of the reference), then it fades.
#   Impact point: (0.5, 0.86) of each frame; the bolt enters from the top edge.
# titan_flash_ring.png : 512x512 shockwave ring seen from above (expand it over ~0.3 s on the water).
# titan_preview_water.png / titan_preview_sky.png : the flipbook over the pond and the sky colours.
# Deterministic: every random draw comes from a fixed seed per frame.
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fxlib as fx  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")

RES = 256
FRAMES = 16
IMPACT = (0.5 * RES, 0.86 * RES)

# palette (sRGB)
OUTLINE = (70, 28, 4)
ORANGE = (255, 138, 18)
YELLOW = (255, 214, 40)
PALE = (255, 246, 170)
WHITE = (255, 255, 248)
SMOKE = (26, 20, 24)
SMOKE_LIGHT = (62, 50, 52)
GLOW = (255, 190, 60)


def bolt_points(rng, start, end, roughness, depth=6):
    """Jagged path from start to end by midpoint displacement."""
    pts = [np.array(start, float), np.array(end, float)]
    amp = roughness
    for _ in range(depth):
        new = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            mid = (a + b) / 2
            d = b - a
            n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
            mid = mid + n * rng.uniform(-amp, amp)
            new += [mid, b]
        pts = new
        amp *= 0.55
    return [tuple(p) for p in pts]


def branch_set(rng, main, count, spread, length):
    """Branches leaving the main bolt, heading down and outwards."""
    out = []
    for _ in range(count):
        k = int(rng.uniform(0.25, 0.85) * (len(main) - 1))
        sx, sy = main[k]
        side = rng.choice([-1, 1])
        ang = math.radians(rng.uniform(20, 70)) * side
        ln = rng.uniform(0.5, 1.0) * length
        end = (sx + math.sin(ang) * ln * spread, sy + math.cos(ang) * ln)
        out.append(bolt_points(rng, (sx, sy), end, ln * 0.18, 4))
    return out


def impact_branches(rng, count, length):
    """Short crackles spraying out of the impact point."""
    out = []
    for _ in range(count):
        ang = math.radians(rng.uniform(-170, -10))
        ln = rng.uniform(0.45, 1.0) * length
        end = (IMPACT[0] + math.cos(ang) * ln, IMPACT[1] + math.sin(ang) * ln * 0.55)
        out.append(bolt_points(rng, IMPACT, end, ln * 0.2, 4))
    return out


def tapered(points, width, tail=0.35):
    """Widths along a path: full at the start, thinner towards the end."""
    n = len(points)
    return [width * (1 - tail * i / max(1, n - 1)) for i in range(n)]


def draw_bolt(canvas, xs, ys, points, width, glow=0.0):
    """Cartoon bolt: dark outline, orange rim, yellow body, white core (+ optional soft glow)."""
    h, w, _ = canvas.shape
    widths = tapered(points, width)
    body = fx.polyline_mask(w, h, points, widths, xs, ys)
    if glow > 0:
        halo = fx.blur(body, width * 1.6) * glow
        canvas = fx.over(canvas, fx.fill(w, h, halo, fx.rgb(GLOW, 0.85)))
    layers = [
        (1.0, 6.0, OUTLINE),
        (1.0, 3.0, ORANGE),
        (1.0, 0.0, YELLOW),
        (0.45, 0.0, PALE),
        (0.18, 0.0, WHITE),
    ]
    for scale, extra, color in layers:
        m = fx.polyline_mask(w, h, points, [v * scale + extra for v in widths], xs, ys)
        canvas = fx.over(canvas, fx.fill(w, h, m, fx.rgb(color)))
    return canvas


def smoke_puffs(rng, t, xs, ys):
    """Black cartoon smoke rising around the impact: lumpy blobs with a lighter top and an outline."""
    w = h = RES
    layer = fx.blank(w, h)
    if t <= 0:
        return layer
    grow = min(1.0, t / 0.35)
    fade = 1.0 - max(0.0, (t - 0.55) / 0.55)
    if fade <= 0:
        return layer
    puffs = [(-62, -6, 30), (-34, -26, 36), (0, -36, 40), (36, -24, 34), (64, -4, 28), (-12, -2, 30), (22, 0, 28)]
    body = np.zeros((h, w), np.float32)
    shade = np.zeros((h, w), np.float32)
    for k, (dx, dy, r) in enumerate(puffs):
        jitter = rng.uniform(-4, 4, 2)
        cx = IMPACT[0] + dx * (0.6 + 0.6 * grow) + jitter[0]
        cy = IMPACT[1] + dy * (0.4 + 0.9 * grow) - 18 * t + jitter[1]
        rr = r * (0.35 + 0.65 * grow) * (0.9 + 0.2 * math.sin(k * 1.7 + t * 9))
        body = np.maximum(body, fx.disc_mask(w, h, cx, cy, rr, xs, ys))
        # lighter cap on each puff
        shade = np.maximum(shade, fx.disc_mask(w, h, cx - rr * 0.25, cy - rr * 0.3, rr * 0.55, xs, ys))
    layer = fx.over(layer, fx.fill(w, h, fx.grow(body, 3.0), fx.rgb(OUTLINE, fade)))
    layer = fx.over(layer, fx.fill(w, h, body, fx.rgb(SMOKE, fade)))
    layer = fx.over(layer, fx.fill(w, h, shade * body, fx.rgb(SMOKE_LIGHT, fade)))
    return layer


def frame(f):
    rng = np.random.default_rng(1000 + (f // 2) * 17)    # the crackle re-draws every 2 frames
    xs, ys = fx.grid(RES, RES)
    t = f / (FRAMES - 1)                                    # 0..1 over ~0.6 s
    canvas = fx.blank(RES, RES)
    top = (IMPACT[0] + rng.uniform(-30, 30), -12.0)

    # 0) leader: a thin flicker growing down (frames 0-1)
    if f <= 1:
        reach = 0.45 + 0.4 * f
        end = (IMPACT[0] + (top[0] - IMPACT[0]) * (1 - reach) * 0.3, top[1] + (IMPACT[1] - top[1]) * reach)
        canvas = draw_bolt(canvas, xs, ys, bolt_points(rng, top, end, 26), 5, glow=0.5)
        return canvas

    # 1) flash: a burst of light around the impact, strongest on the strike frames
    flash = max(0.0, 1.0 - (f - 2) / 4.0)
    if flash > 0:
        d = np.hypot(xs - IMPACT[0], (ys - IMPACT[1]) * 1.25)
        radial = np.clip(1.0 - d / (RES * (0.55 + 0.25 * flash)), 0, 1) ** 1.6
        canvas = fx.over(canvas, fx.fill(RES, RES, radial * flash, fx.rgb(PALE, 0.95)))
        if f in (2, 3):
            canvas = fx.over(canvas, fx.fill(RES, RES, np.ones((RES, RES), np.float32), fx.rgb(WHITE, 0.35 if f == 2 else 0.18)))

    # 2) smoke behind the bolts once it has struck
    canvas = fx.over(canvas, smoke_puffs(np.random.default_rng(77 + f), (f - 4) / (FRAMES - 5), xs, ys))

    # 3) the main bolt: thick on impact, thinning while it fades
    life = 1.0 - max(0.0, (f - 9) / 7.0)
    if life > 0:
        width = 18 * (1.15 if f in (2, 3) else 1.0) * (0.35 + 0.65 * life)
        main = bolt_points(rng, top, IMPACT, 38)
        branches = branch_set(rng, main, 2 + min(4, f - 2), 1.0, 70 * min(1.0, (f - 1) / 4))
        for b in branches:
            canvas = draw_bolt(canvas, xs, ys, b, max(3.0, width * 0.38), glow=0.6 * life)
        canvas = draw_bolt(canvas, xs, ys, main, width, glow=1.0 * life)
        # crackles spraying out of the impact
        if f >= 3:
            for b in impact_branches(rng, 3 + (f % 3), 46 + 30 * min(1.0, (f - 3) / 4)):
                canvas = draw_bolt(canvas, xs, ys, b, max(2.5, width * 0.28), glow=0.4 * life)
        # bright impact core
        core = fx.disc_mask(RES, RES, IMPACT[0], IMPACT[1], 16 * life + 4, xs, ys)
        canvas = fx.over(canvas, fx.fill(RES, RES, fx.blur(core, 6), fx.rgb(WHITE, 0.9 * life)))

    # 4) a few sparks drifting up at the end
    if f >= 8:
        srng = np.random.default_rng(4242)
        for k in range(10):
            ang = srng.uniform(-math.pi * 0.95, -math.pi * 0.05)
            spd = srng.uniform(50, 110)
            tt = (f - 8) / 7
            sx = IMPACT[0] + math.cos(ang) * spd * tt
            sy = IMPACT[1] + math.sin(ang) * spd * tt + 40 * tt * tt
            s = fx.disc_mask(RES, RES, sx, sy, 2.6 * (1 - tt) + 0.8, xs, ys)
            canvas = fx.over(canvas, fx.fill(RES, RES, s, fx.rgb(YELLOW, 1 - tt * 0.8)))

    # fade the very last frames so the particle ends softly
    canvas[:, :, 3] *= min(1.0, (FRAMES + 0.5 - f) / 3.0)
    return canvas


def flash_ring():
    """Shockwave ring from above: a jagged, bright band with an outline and a crackle inside."""
    n = 512
    xs, ys = fx.grid(n, n)
    c = n / 2
    d = np.hypot(xs - c, ys - c)
    ang = np.arctan2(ys - c, xs - c)
    wobble = 7 * np.sin(ang * 9 + 0.7) + 4 * np.sin(ang * 23 + 2.1)
    outer = np.clip(205 + wobble + 0.5 - d, 0, 1)
    inner = np.clip(d - (150 - wobble * 1.4) + 0.5, 0, 1)
    band = outer * inner
    img = fx.blank(n, n)
    soft = fx.blur(band, 18)
    img = fx.over(img, fx.fill(n, n, soft, fx.rgb(GLOW, 0.7)))
    img = fx.over(img, fx.fill(n, n, fx.grow(band, 5.0), fx.rgb(OUTLINE)))
    img = fx.over(img, fx.fill(n, n, band, fx.rgb(ORANGE)))
    core_outer = np.clip(196 + wobble + 0.5 - d, 0, 1)
    core_inner = np.clip(d - (164 - wobble) + 0.5, 0, 1)
    img = fx.over(img, fx.fill(n, n, core_outer * core_inner, fx.rgb(YELLOW)))
    shine = np.clip(186 + wobble + 0.5 - d, 0, 1) * np.clip(d - (176 - wobble * 0.5) + 0.5, 0, 1)
    img = fx.over(img, fx.fill(n, n, shine, fx.rgb(WHITE)))
    # crackles running round the inside of the ring
    rng = np.random.default_rng(9)
    for k in range(6):
        a0 = rng.uniform(0, 2 * math.pi)
        arc = [(c + math.cos(a0 + s) * (140 - 10 * math.sin(s * 5)), c + math.sin(a0 + s) * (140 - 10 * math.sin(s * 5)))
               for s in np.linspace(0, rng.uniform(0.5, 0.9), 6)]
        pts = []
        for p, q in zip(arc[:-1], arc[1:]):
            pts += bolt_points(rng, p, q, 5, 2)[:-1]
        pts.append(arc[-1])
        img = draw_bolt(img, xs, ys, pts, 4, glow=0.4)
    return img


os.makedirs(OUT, exist_ok=True)
frames = []
for f in range(FRAMES):
    frames.append(frame(f))
    print("titan frame", f + 1, "/", FRAMES)
sheet = fx.atlas(frames, 4)
fx.save_png(os.path.join(OUT, "titan_lightning_flipbook.png"), sheet)
fx.save_png(os.path.join(OUT, "titan_preview_water.png"), fx.on_background(sheet, (78, 214, 251)))
fx.save_png(os.path.join(OUT, "titan_preview_sky.png"), fx.on_background(sheet, (150, 205, 245)))
ring = flash_ring()
fx.save_png(os.path.join(OUT, "titan_flash_ring.png"), ring)
fx.save_png(os.path.join(OUT, "titan_flash_ring_preview.png"), fx.on_background(ring, (78, 214, 251)))
print("done")
