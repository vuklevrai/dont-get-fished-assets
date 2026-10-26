# Dash speed lines and the near-death vignette (flat 2D textures).
#
#   blender -b --factory-startup --python screen_fx.py -- <out_dir>
#
# speed_line.png            256x32  thin white streak with soft, tapered ends (stretched particles or a Beam)
# speed_lines_screen.png    1024²   anime-style radial lines towards the centre, centre clear (full-screen overlay)
# speed_lines_screen_b.png  1024²   another draw of the same, to alternate with the first so the lines flicker
# low_hp_vignette.png       1024²   red edges, clear centre, soft gradient (pulse its transparency at <= 10 % HP)
# *_preview_*.png                    the same over the pond and the sky colours
# Straight-alpha RGBA, deterministic.
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fxlib as fx  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
os.makedirs(OUT, exist_ok=True)
WATER, SKY = (78, 214, 251), (150, 205, 245)


def speed_line():
    w, h = 256, 32
    xs, ys = fx.grid(w, h)
    u = xs / w
    # brighter towards the head (right), both ends fade out
    along = np.clip(np.sin(np.pi * u), 0, 1) ** 0.8 * (0.55 + 0.45 * u)
    half = 1.2 + 2.6 * np.sin(np.pi * u) ** 0.6           # px: thin at the tips, ~4 px wide in the middle
    across = np.clip(half + 0.8 - np.abs(ys - h / 2), 0, 1)
    glow = np.exp(-((ys - h / 2) / (half * 2.2)) ** 2) * 0.35
    alpha = np.clip(along * np.maximum(across, glow), 0, 1)
    img = fx.blank(w, h)
    img[:, :, :3] = 1.0
    img[:, :, 3] = alpha
    return img


def speed_lines_screen(seed):
    n = 1024
    xs, ys = fx.grid(n, n)
    cx = cy = n / 2
    dx, dy = xs - cx, ys - cy
    ang = np.arctan2(dy, dx)
    dist = np.hypot(dx, dy) / (n / 2)                     # 0 centre, 1 at the edge middles, 1.41 at corners
    rng = np.random.default_rng(seed)
    alpha = np.zeros((n, n), np.float32)
    count = 110
    for k in range(count):
        a0 = (k + rng.uniform(-0.35, 0.35)) / count * 2 * math.pi - math.pi
        width = math.radians(rng.uniform(0.25, 1.1))       # angular half-width at the outer end
        start = rng.uniform(0.42, 0.78)                     # where the line begins (towards the centre)
        strength = rng.uniform(0.35, 0.85)
        d_ang = np.angle(np.exp(1j * (ang - a0)))
        # wedge that narrows to a point at `start`
        taper = np.clip((dist - start) / (1.45 - start), 0, 1)
        half = width * taper
        edge = np.clip((half - np.abs(d_ang)) * (dist * n / 2) + 0.5, 0, 1)
        fade = np.clip((dist - start) / 0.25, 0, 1)
        alpha = np.maximum(alpha, edge * fade * strength)
    # keep the middle clear, with a soft border
    clear = np.clip((dist - 0.38) / 0.22, 0, 1)
    alpha *= clear * clear * (3 - 2 * clear)
    img = fx.blank(n, n)
    img[:, :, :3] = 1.0
    img[:, :, 3] = alpha
    return img


def low_hp_vignette():
    n = 1024
    xs, ys = fx.grid(n, n)
    u = (xs / n) * 2 - 1
    v = (ys / n) * 2 - 1
    # superellipse distance: hugs the screen edges more than a circle
    p = 3.0
    d = (np.abs(u) ** p + np.abs(v) ** p) ** (1 / p)
    t = np.clip((d - 0.68) / 0.5, 0, 1)
    alpha = t * t * (3 - 2 * t)
    # a slightly uneven, organic edge (soft, low-frequency)
    wobble = fx.value_noise(n, n, 160, 31, 3, xs, ys) - 0.5
    alpha = np.clip(alpha + wobble * 0.18 * alpha, 0, 1) * 0.92
    img = fx.blank(n, n)
    deep = np.array([150 / 255, 0, 8 / 255])
    bright = np.array([255 / 255, 30 / 255, 30 / 255])
    mix = np.clip((d - 0.75) / 0.5, 0, 1)[:, :, None]
    img[:, :, :3] = bright * (1 - mix) + deep * mix
    img[:, :, 3] = alpha
    return img


line = speed_line()
fx.save_png(os.path.join(OUT, "speed_line.png"), line)
big = np.repeat(np.repeat(line, 3, axis=0), 3, axis=1)
fx.save_png(os.path.join(OUT, "speed_line_preview.png"), np.concatenate(
    [fx.on_background(big, WATER), fx.on_background(big, SKY)], axis=0))

for name, seed in (("speed_lines_screen.png", 5), ("speed_lines_screen_b.png", 6)):
    img = speed_lines_screen(seed)
    fx.save_png(os.path.join(OUT, name), img)
fx.save_png(os.path.join(OUT, "speed_lines_screen_preview_water.png"), fx.on_background(img, WATER))
fx.save_png(os.path.join(OUT, "speed_lines_screen_preview_sky.png"), fx.on_background(img, SKY))

vig = low_hp_vignette()
fx.save_png(os.path.join(OUT, "low_hp_vignette.png"), vig)
fx.save_png(os.path.join(OUT, "low_hp_vignette_preview_water.png"), fx.on_background(vig, WATER))
fx.save_png(os.path.join(OUT, "low_hp_vignette_preview_sky.png"), fx.on_background(vig, SKY))
print("done")
