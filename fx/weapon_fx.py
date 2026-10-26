# Cartoon textures for the harpoon and bazooka fishermen (same toon style as the splash and the Titan strike:
# flat bands of colour, dark outlines).
#
#   blender -b --factory-startup --python weapon_fx.py -- <out_dir>
#
# explosion_flipbook.png : 1024x1024, 4x4 frames of 256 px, plays once (~0.7 s at 22 fps): white star flash,
#                          orange fireball in nested bands, grey smoke that takes over, rises and dissolves.
#                          The blast centre is at (0.5, 0.53) of each frame.
# smoke_puff.png         : 256x256, one grey cartoon puff (missile trail).
# bubble.png             : 128x128, a water bubble that reads on the blue water.
# shard_spark.png        : 128x128, a small white four-point sparkle (disintegration).
# aim_ring.png           : 512x512, crisp red danger circle with a soft inner glow (missile zone, harpoon column caps).
# missile_reticle.png    : 512x512, red crosshair (the bazooka's sight, blinks faster and faster).
# shockwave_ring.png     : 512x512, white-cyan pressure ring (explosion shockwave, expanded to the blast radius).
# missile_flame.png      : 256x64, nozzle flame for a Beam (texture X runs along the beam: the nozzle is on the left).
# weapon_fx_preview_*.png: every texture over the pond and the sky colours.
# Deterministic: fixed seeds.
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fxlib as fx  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")

WATER = (78, 214, 251)
SKY = (150, 205, 245)

# fire palette (sRGB), same family as titan_lightning
FIRE_OUTLINE = (66, 24, 6)
WHITE = (255, 255, 240)
PALE = (255, 244, 166)
YELLOW = (255, 208, 40)
ORANGE = (255, 132, 22)
RED = (228, 66, 18)
DARK_RED = (150, 34, 14)
# smoke palette
SMOKE_OUTLINE = (40, 36, 42)
SMOKE_DARK = (84, 80, 88)
SMOKE = (118, 114, 120)
SMOKE_LIGHT = (164, 160, 164)


def angular_wobble(theta, seed, amp, lobes=(3, 5, 7)):
    rng = np.random.default_rng(seed)
    w = np.zeros_like(theta)
    for k in lobes:
        w += rng.uniform(0.4, 1.0) * np.sin(k * theta + rng.uniform(0, 2 * math.pi))
    return 1 + amp * w / len(lobes)


def lumpy_disc(xs, ys, cx, cy, r, seed, amp=0.12):
    d = np.hypot(xs - cx, ys - cy)
    theta = np.arctan2(ys - cy, xs - cx)
    return np.clip(r * angular_wobble(theta, seed, amp) + 0.5 - d, 0, 1)


def union(xs, ys, blobs, scale=1.0, shift=(0.0, 0.0), amp=0.12):
    """blobs: (cx, cy, r, seed). scale shrinks every blob around its own centre; shift moves them."""
    m = np.zeros(xs.shape, np.float32)
    for cx, cy, r, seed in blobs:
        if r * scale > 0.5:
            m = np.maximum(m, lumpy_disc(xs, ys, cx + shift[0], cy + shift[1], r * scale, seed, amp))
    return m


def toon_layers(w, h, xs, ys, blobs, colours, outline_px, outline_colour, alpha=1.0, erode=None):
    """Cel-shaded cluster: outline, base, then nested inner bands (smaller copies shifted up-left).
    colours: [(scale, (dx, dy), colour), ...] from the outside in; the first one is the base shape."""
    base = union(xs, ys, blobs)
    if erode is not None:
        base = base * erode
    layer = fx.blank(w, h)
    if base.max() <= 0:
        return layer
    if outline_px > 0:
        layer = fx.over(layer, fx.fill(w, h, fx.grow(base, outline_px), fx.rgb(outline_colour, alpha)))
    for k, (scale, shift, colour) in enumerate(colours):
        m = base if k == 0 else union(xs, ys, blobs, scale, shift) * base
        layer = fx.over(layer, fx.fill(w, h, m, fx.rgb(colour, alpha)))
    return layer


def star_mask(xs, ys, cx, cy, r_in, r_out, spikes, seed, sharp=6.0):
    rng = np.random.default_rng(seed)
    theta = np.arctan2(ys - cy, xs - cx)
    d = np.hypot(xs - cx, ys - cy)
    lengths = rng.uniform(0.65, 1.0, spikes)
    k = np.floor((theta + math.pi) / (2 * math.pi) * spikes).astype(int) % spikes
    local = ((theta + math.pi) / (2 * math.pi) * spikes) % 1.0          # 0..1 inside each spike sector
    peak = (1 - np.abs(local - 0.5) * 2) ** sharp                       # 1 at the spike's middle
    r = r_in + (r_out * lengths[k] - r_in) * peak
    return np.clip(r + 0.5 - d, 0, 1)


def ring_mask(xs, ys, cx, cy, r_out, r_in):
    d = np.hypot(xs - cx, ys - cy)
    return np.clip(r_out + 0.5 - d, 0, 1) * np.clip(d - r_in + 0.5, 0, 1)


# ---------------------------------------------------------------- explosion flipbook
RES = 256
CENTRE = (128.0, 136.0)
FRAMES = 16

# fireball: a centre blob and a ring of blobs (unit offsets, unit radii), scaled by R(t)
_rng = np.random.default_rng(31)
FIRE_BLOBS = [(0.0, 0.0, 0.62, 100)]
for i in range(8):
    a = i / 8 * 2 * math.pi + _rng.uniform(-0.25, 0.25)
    FIRE_BLOBS.append((math.cos(a) * 0.52, math.sin(a) * 0.46, _rng.uniform(0.40, 0.52), 101 + i))
# smoke: more, bigger puffs that drift apart and up
SMOKE_BLOBS = [(0.0, -0.1, 0.55, 200)]
for i in range(10):
    a = i / 10 * 2 * math.pi + _rng.uniform(-0.3, 0.3)
    SMOKE_BLOBS.append((math.cos(a) * 0.62, math.sin(a) * 0.5 - 0.08, _rng.uniform(0.34, 0.48), 201 + i))

FIRE_R = [44, 64, 78, 85, 87, 85, 80, 72, 61, 48, 34, 19, 0, 0, 0, 0]
SMOKE_R = [0, 0, 0, 48, 62, 72, 78, 82, 84, 85, 85, 85, 84, 83, 82, 80]


def fire_colours(f):
    """Bands from the outside in: (scale, shift, colour). Early: white-hot; later: orange then red."""
    if f <= 2:
        return [(1, (0, 0), ORANGE), (0.80, (-3, -4), YELLOW), (0.58, (-5, -7), PALE), (0.36, (-6, -8), WHITE)]
    if f <= 5:
        return [(1, (0, 0), RED), (0.84, (-3, -4), ORANGE), (0.62, (-6, -8), YELLOW), (0.34, (-8, -10), PALE)]
    if f <= 8:
        return [(1, (0, 0), DARK_RED), (0.82, (-3, -4), RED), (0.58, (-6, -8), ORANGE), (0.28, (-8, -10), YELLOW)]
    return [(1, (0, 0), DARK_RED), (0.74, (-3, -4), RED), (0.40, (-5, -7), ORANGE)]


def explosion_frame(f):
    xs, ys = fx.grid(RES, RES)
    canvas = fx.blank(RES, RES)
    cx, cy = CENTRE
    t = f / (FRAMES - 1)

    # 1) smoke, behind everything: grows, rises, puffs drift apart, then dissolves through growing holes
    sr = SMOKE_R[f]
    if sr > 0:
        spread = 0.9 + 0.38 * t
        rise = 16 * t * t + 6 * t
        prng = np.random.default_rng(12)
        blobs = []
        for ox, oy, r, s in SMOKE_BLOBS:
            # from frame 10 the cloud breaks up: every puff shrinks away at its own pace
            shrink = 1.0 if f < 10 else max(0.0, 1 - (f - 9) / 6.0 * prng.uniform(0.75, 1.35))
            blobs.append((cx + ox * sr * spread, cy + oy * sr * spread - rise, r * sr * shrink, s))
        fade = min(1.0, (FRAMES + 1 - f) / 3.0)
        canvas = fx.over(canvas, toon_layers(
            RES, RES, xs, ys, blobs,
            [(1, (0, 0), SMOKE_DARK), (0.86, (-4, -5), SMOKE), (0.52, (-9, -11), SMOKE_LIGHT)],
            4.0, SMOKE_OUTLINE, alpha=fade))
        # warm glow of the fire on the underside of the smoke while it burns
        if 3 <= f <= 9:
            glow_m = union(xs, ys, blobs, 0.95, (0, 6)) * np.clip((ys - (cy - 10)) / 60, 0, 1)
            canvas = fx.over(canvas, fx.fill(RES, RES, glow_m, fx.rgb(ORANGE, 0.28 * (1 - (f - 3) / 7))))

    # 2) the fireball
    fr = FIRE_R[f]
    if fr > 0:
        sink = 6 * max(0, f - 6)                                         # the fire sinks into the smoke
        blobs = [(cx + ox * fr, cy + oy * fr + sink, r * fr, s) for ox, oy, r, s in FIRE_BLOBS]
        bands = fire_colours(f)
        canvas = fx.over(canvas, toon_layers(RES, RES, xs, ys, blobs, bands[:-1], 4.5, FIRE_OUTLINE))
        scale, shift, colour = bands[-1]
        core = lumpy_disc(xs, ys, cx + shift[0] * 1.6, cy + shift[1] * 1.6 + sink, fr * scale * 1.25, 400 + f, 0.18)
        canvas = fx.over(canvas, fx.fill(RES, RES, core * union(xs, ys, blobs), fx.rgb(colour)))

    # 3) the flash: a spiky white-yellow star and a thin light ring, first frames only
    if f <= 3:
        k = [1.0, 1.0, 0.7, 0.35][f]
        r_out = [70, 106, 112, 110][f]
        star = star_mask(xs, ys, cx, cy, r_out * 0.42, r_out, 12, seed=7 + f)
        if f >= 1:
            star = star * (1 - union(xs, ys, [(cx, cy, fr * 0.7, 1)], amp=0.0) * 0.0)
        layer = fx.blank(RES, RES)
        layer = fx.over(layer, fx.fill(RES, RES, fx.grow(star, 3.5), fx.rgb(FIRE_OUTLINE, k)))
        layer = fx.over(layer, fx.fill(RES, RES, star, fx.rgb(YELLOW, k)))
        inner = star_mask(xs, ys, cx, cy, r_out * 0.30, r_out * 0.72, 12, seed=7 + f)
        layer = fx.over(layer, fx.fill(RES, RES, inner, fx.rgb(PALE, k)))
        core = fx.disc_mask(RES, RES, cx, cy, r_out * 0.28, xs, ys)
        layer = fx.over(layer, fx.fill(RES, RES, core, fx.rgb(WHITE, k)))
        if f == 0:
            canvas = fx.over(canvas, layer)
        else:
            # behind the fireball from frame 1: the spikes stick out around it
            canvas = fx.over(layer, canvas)
    if 1 <= f <= 4:
        rr = [0, 92, 106, 113, 117][f]
        ring = ring_mask(xs, ys, cx, cy, rr, rr - [0, 9, 6, 4, 2][f])
        canvas = fx.over(canvas, fx.fill(RES, RES, ring, fx.rgb(WHITE, [0, 0.95, 0.75, 0.5, 0.25][f])))

    # 4) debris chunks and sparks flying out (in front)
    rng = np.random.default_rng(77)
    for k in range(12):
        ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05) if k < 8 else rng.uniform(0, 2 * math.pi)
        spd = rng.uniform(70, 125)
        size = rng.uniform(3.0, 5.5)
        tt = (f - 1) / 9
        if not (0 <= tt <= 1):
            continue
        start = 0.75 * max(FIRE_R[min(f, 4)], 1)
        px = cx + math.cos(ang) * (start + spd * 0.8 * tt)
        py = cy + math.sin(ang) * (start + spd * 0.8 * tt) + 50 * tt * tt
        if max(abs(px - RES / 2), abs(py - RES / 2)) > RES / 2 - 8:
            continue
        m = fx.disc_mask(RES, RES, px, py, size * (1 - 0.5 * tt), xs, ys)
        if k % 3 == 0:
            canvas = fx.over(canvas, fx.fill(RES, RES, fx.grow(m, 2.0), fx.rgb(FIRE_OUTLINE, 1 - tt * 0.6)))
            canvas = fx.over(canvas, fx.fill(RES, RES, m, fx.rgb(SMOKE_DARK, 1 - tt * 0.6)))
        elif tt <= 0.65:
            canvas = fx.over(canvas, fx.fill(RES, RES, fx.grow(m, 1.5), fx.rgb(ORANGE, 1 - tt)))
            canvas = fx.over(canvas, fx.fill(RES, RES, m, fx.rgb(PALE, 1 - tt)))
    return canvas


def explosion():
    frames = []
    for f in range(FRAMES):
        frames.append(explosion_frame(f))
        print("explosion frame", f + 1, "/", FRAMES, flush=True)
    for i, fr in enumerate(frames):
        a = fr[:, :, 3]
        edge = max(a[:3].max(), a[-3:].max(), a[:, :3].max(), a[:, -3:].max())
        if edge > 0.01:
            print("WARNING explosion frame %d touches the frame border (alpha %.2f)" % (i, edge))
    sheet = fx.atlas(frames, 4)
    fx.save_png(os.path.join(OUT, "explosion_flipbook.png"), sheet)
    fx.save_png(os.path.join(OUT, "explosion_preview_water.png"), fx.on_background(sheet, WATER))
    fx.save_png(os.path.join(OUT, "explosion_preview_sky.png"), fx.on_background(sheet, SKY))
    # how much of a frame the fireball covers at its biggest (to size the billboard against the blast radius)
    biggest = frames[int(np.argmax(FIRE_R))][:, :, 3]
    cols = np.where(biggest.max(axis=0) > 0.5)[0]
    print("explosion: widest drawing (frame %d) covers %.3f of the frame width" % (int(np.argmax(FIRE_R)), (cols[-1] - cols[0] + 1) / RES))
    widest = max(((np.where(fr[:, :, 3].max(axis=0) > 0.5)[0]) for fr in frames), key=lambda c: c[-1] - c[0] if len(c) else 0)
    print("explosion: widest over the whole sheet covers %.3f of the frame width" % ((widest[-1] - widest[0] + 1) / RES))
    return frames


# ---------------------------------------------------------------- single textures
def smoke_puff():
    n = 256
    xs, ys = fx.grid(n, n)
    c = n / 2
    blobs = [(c, c + 6, 62, 300), (c - 46, c + 18, 42, 301), (c + 48, c + 16, 44, 302),
             (c - 22, c - 30, 46, 303), (c + 26, c - 26, 44, 304), (c + 4, c + 40, 40, 305)]
    img = toon_layers(n, n, xs, ys, blobs,
                      [(1, (0, 0), SMOKE_DARK), (0.86, (-5, -6), SMOKE), (0.5, (-12, -14), SMOKE_LIGHT)],
                      6.0, SMOKE_OUTLINE)
    return img


def bubble():
    n = 128
    xs, ys = fx.grid(n, n)
    c = n / 2
    r = 56.0
    d = np.hypot(xs - c, ys - c)
    inside = np.clip(r + 0.5 - d, 0, 1)
    img = fx.blank(n, n)
    # body: almost clear in the middle, denser towards the rim (like a real bubble's fresnel)
    fres = np.clip(d / r, 0, 1) ** 2.2
    img = fx.over(img, fx.fill(n, n, inside * (0.10 + 0.30 * fres), fx.rgb((200, 244, 255))))
    # rim: a light cyan line with a darker cyan edge outside, so it reads on bright and dark water
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r + 2.5, r - 0.5), fx.rgb((40, 150, 200), 0.75)))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r, r - 4.0), fx.rgb((232, 252, 255), 0.95)))
    # big white highlight top-left, a small dot under it, a soft crescent bottom-right
    ex, ey = c - 22, c - 24
    u = (xs - ex) * math.cos(math.radians(40)) + (ys - ey) * math.sin(math.radians(40))
    v = -(xs - ex) * math.sin(math.radians(40)) + (ys - ey) * math.cos(math.radians(40))
    hl = np.clip((1 - np.sqrt((u / 16) ** 2 + (v / 9) ** 2)) * 12, 0, 1)
    img = fx.over(img, fx.fill(n, n, hl, fx.rgb((255, 255, 255), 0.98)))
    img = fx.over(img, fx.fill(n, n, fx.disc_mask(n, n, c - 36, c - 6, 4.5, xs, ys), fx.rgb((255, 255, 255), 0.9)))
    cres = ring_mask(xs, ys, c, c, r - 7, r - 14) * np.clip(((xs - c) + (ys - c)) / 50 - 0.6, 0, 1)
    img = fx.over(img, fx.fill(n, n, cres, fx.rgb((255, 255, 255), 0.55)))
    return img


def shard_spark():
    n = 128
    xs, ys = fx.grid(n, n)
    c = n / 2
    dx, dy = np.abs(xs - c), np.abs(ys - c)
    # a four-point star: |x|^p + |y|^p style concave diamond, long vertical and horizontal points
    star = np.clip(1 - (np.sqrt(dx / 54) + np.sqrt(dy / 54)), 0, 1)
    star = np.clip(star * 6, 0, 1)
    diag = np.clip(1 - (np.sqrt(np.abs(dx + dy) / 70 * 0.7 + np.abs(dx - dy) / 70 * 0.7)), 0, 1) * 0
    glow = fx.blur(star, 10) * 0.9 + np.clip(1 - np.hypot(dx, dy) / 40, 0, 1) ** 2 * 0.6
    img = fx.blank(n, n)
    img = fx.over(img, fx.fill(n, n, np.clip(glow, 0, 1), fx.rgb((200, 240, 255), 0.7)))
    img = fx.over(img, fx.fill(n, n, np.maximum(star, diag), fx.rgb((255, 255, 255))))
    img = fx.over(img, fx.fill(n, n, fx.disc_mask(n, n, c, c, 6, xs, ys), fx.rgb((255, 255, 255))))
    return img


AIM_RED = (255, 46, 36)
AIM_DARK = (104, 6, 6)
AIM_PALE = (255, 190, 176)


def aim_ring():
    n = 512
    xs, ys = fx.grid(n, n)
    c = n / 2
    d = np.hypot(xs - c, ys - c)
    r = 236.0
    img = fx.blank(n, n)
    # soft red glow on the inside of the circle, so the whole zone reads as danger
    inner_glow = np.clip((d - 120) / (r - 120), 0, 1) ** 2.4 * (d < r)
    img = fx.over(img, fx.fill(n, n, inner_glow, fx.rgb(AIM_RED, 0.45)))
    outer_glow = np.clip(1 - (d - r) / 14, 0, 1) * (d >= r)
    img = fx.over(img, fx.fill(n, n, outer_glow, fx.rgb(AIM_RED, 0.35)))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r + 4, r - 22), fx.rgb(AIM_DARK)))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r, r - 18), fx.rgb(AIM_RED)))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r - 5, r - 9), fx.rgb(AIM_PALE)))
    return img


def missile_reticle():
    n = 512
    xs, ys = fx.grid(n, n)
    c = n / 2
    shape = ring_mask(xs, ys, c, c, 150, 134)
    # four ticks crossing the circle, a gap in the middle
    for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a = (c + ax * 96, c + ay * 96)
        b = (c + ax * 196, c + ay * 196)
        shape = np.maximum(shape, fx.polyline_mask(n, n, [a, b], 16, xs, ys))
    # corner brackets
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        corner = (c + sx * 214, c + sy * 214)
        shape = np.maximum(shape, fx.polyline_mask(n, n, [(corner[0], corner[1] - sy * 60), corner, (corner[0] - sx * 60, corner[1])], 14, xs, ys))
    dot = fx.disc_mask(n, n, c, c, 14, xs, ys)
    shape = np.maximum(shape, dot)
    img = fx.blank(n, n)
    img = fx.over(img, fx.fill(n, n, fx.blur(shape, 10), fx.rgb(AIM_RED, 0.55)))
    img = fx.over(img, fx.fill(n, n, fx.grow(shape, 4.0), fx.rgb(AIM_DARK)))
    img = fx.over(img, fx.fill(n, n, shape, fx.rgb(AIM_RED)))
    # a thin pale line inside each stroke for the cartoon shine
    shine = ring_mask(xs, ys, c, c, 145, 140)
    for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        shine = np.maximum(shine, fx.polyline_mask(n, n, [(c + ax * 100 - ay * 2, c + ay * 100 - ax * 2), (c + ax * 190 - ay * 2, c + ay * 190 - ax * 2)], 4, xs, ys))
    img = fx.over(img, fx.fill(n, n, shine * shape, fx.rgb(AIM_PALE)))
    return img


def shockwave_ring():
    n = 512
    xs, ys = fx.grid(n, n)
    c = n / 2
    d = np.hypot(xs - c, ys - c)
    r = 238.0
    img = fx.blank(n, n)
    # a pressure wave: bright at its outer edge, fading towards the centre
    trail = np.clip((d - (r - 70)) / 70, 0, 1) ** 2 * (d <= r)
    img = fx.over(img, fx.fill(n, n, trail, fx.rgb((200, 245, 255), 0.6)))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r + 3, r - 16), fx.rgb((60, 170, 220), 0.9)))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r, r - 13), fx.rgb((240, 252, 255))))
    img = fx.over(img, fx.fill(n, n, ring_mask(xs, ys, c, c, r - 4, r - 8), fx.rgb((255, 255, 255))))
    return img


def missile_flame():
    w, h = 256, 64
    xs, ys = fx.grid(w, h)
    cy = h / 2

    def teardrop(length, width, x0=10.0):
        # round at the nozzle (left), tapering to a point at x0 + length
        u = np.clip((xs - x0) / length, 0, 1)
        half = width / 2 * np.sqrt(np.clip(1 - u, 0, 1)) * np.clip((xs - x0 + width / 2) / (width / 2), 0, 1) ** 0.5
        m = np.clip(half + 0.5 - np.abs(ys - cy), 0, 1) * (xs >= x0 - width / 2) * (xs <= x0 + length)
        return m

    img = fx.blank(w, h)
    outer = teardrop(214, 52, 30.0)
    img = fx.over(img, fx.fill(w, h, fx.grow(outer, 2.5), fx.rgb((120, 30, 10))))
    img = fx.over(img, fx.fill(w, h, outer, fx.rgb(ORANGE)))
    img = fx.over(img, fx.fill(w, h, teardrop(154, 38, 30.0), fx.rgb(YELLOW)))
    img = fx.over(img, fx.fill(w, h, teardrop(86, 22, 32.0), fx.rgb(WHITE)))
    # the tail end fades so the beam never ends on a hard edge
    img[:, :, 3] *= np.clip((246 - xs) / 60, 0, 1)
    return img


os.makedirs(OUT, exist_ok=True)
explosion()
singles = {
    "smoke_puff.png": smoke_puff(),
    "bubble.png": bubble(),
    "shard_spark.png": shard_spark(),
    "aim_ring.png": aim_ring(),
    "missile_reticle.png": missile_reticle(),
    "shockwave_ring.png": shockwave_ring(),
    "missile_flame.png": missile_flame(),
}
for name, img in singles.items():
    fx.save_png(os.path.join(OUT, name), img)

# contact sheet of the single textures over the pond and the sky (each shown in a 256 px cell)
cell = 256
for tag, colour in (("water", WATER), ("sky", SKY)):
    sheet = fx.blank(cell * len(singles), cell)
    for i, img in enumerate(singles.values()):
        h, w, _ = img.shape
        k = min(cell / w, cell / h) if max(w, h) > cell else 1.0
        if k != 1.0:
            step = int(round(1 / k))
            img = img[::step, ::step]
            h, w, _ = img.shape
        y0, x0 = (cell - h) // 2, i * cell + (cell - w) // 2
        sheet[y0:y0 + h, x0:x0 + w] = img
    fx.save_png(os.path.join(OUT, "weapon_fx_preview_%s.png" % tag), fx.on_background(sheet, colour))
print("done")
