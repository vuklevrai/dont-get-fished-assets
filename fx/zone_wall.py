# Storm-zone wall texture in the style of Fortnite's storm, for the Ocean map's rectangular zone.
#
#   blender -b --factory-startup --python zone_wall.py -- <out_dir>
#
# zone_wall_flipbook.png : 4x4 flipbook (1024x1024, 256 px frames), loops over 16 frames. Every frame tiles
#   horizontally (put it on the wall with a Texture repeating along the wall's length). Bottom = the water line.
# zone_wall_static.png   : 512x512 still version (also tiles horizontally), for the performance mode.
# zone_wall_preview_*.png : the flipbook over the pond and the sky colours.
# Look: translucent blue-violet (120, 70, 255) -> (80, 170, 255), undulating bright bands, rising streaks,
# crackles of lightning, a glowing rim at the bottom; opaque at the bottom, fading out towards the top.
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fxlib as fx  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
os.makedirs(OUT, exist_ok=True)

FRAMES = 16
VIOLET = np.array([120, 70, 255]) / 255
BLUE = np.array([80, 170, 255]) / 255
RIM = np.array([200, 240, 255]) / 255
TAU = 2 * math.pi


def periodic(xs, ys, w, h, t, kx, ky, m, phase):
    """A travelling wave that tiles in x (integer kx) and loops in time (integer m)."""
    return np.sin(TAU * (kx * xs / w + ky * ys / h + m * t) + phase)


def wall(w, h, t, seed, crackles=True):
    xs, ys = fx.grid(w, h)
    v = ys / h                                      # 0 at the top, 1 at the bottom (water line)
    # gentle swirl: warp the coordinates with slow waves
    wx = xs + 6.0 * w / 256 * periodic(xs, ys, w, h, t, 2, 1.0, 1, 0.3)
    wy = ys + 5.0 * h / 256 * periodic(xs, ys, w, h, t, 3, 0.5, -1, 1.7)
    # colour: violet low and blue high, with drifting patches
    patch = 0.5 + 0.25 * periodic(wx, wy, w, h, t, 1, 0.8, 1, 0.0) + 0.25 * periodic(wx, wy, w, h, t, 2, -1.3, -1, 2.0)
    mixk = np.clip(0.6 * (1 - v) + 0.35 * (patch - 0.5) + 0.05, 0, 1)[:, :, None]
    color = VIOLET * (1 - mixk) + BLUE * mixk
    # undulating bright bands
    bands = np.zeros((h, w), np.float32)
    for k, (y0, amp, kx, m, width, strength) in enumerate(((0.30, 0.05, 2, 1, 0.04, 0.4), (0.52, 0.06, 3, -1, 0.045, 0.4),
                                                           (0.72, 0.04, 1, 2, 0.035, 0.5), (0.86, 0.03, 2, -1, 0.03, 0.6))):
        centre = y0 + amp * np.sin(TAU * (kx * wx / w + m * t) + k)
        bands = np.maximum(bands, strength * np.exp(-((v - centre) / width) ** 2))
    # rising streaks (vertical, tiling in x, looping upward)
    streak = 0.5 + 0.5 * np.sin(TAU * (5 * wx / w) + 2.0 * np.sin(TAU * (wy / h * 1.0 + t)))
    streak = np.clip((streak - 0.8) / 0.2, 0, 1) * (0.25 + 0.75 * v) * 0.2
    # opacity: thick at the bottom, fading out at the top
    alpha = 0.3 + 0.58 * np.clip(v, 0, 1) ** 1.4
    alpha = np.clip(alpha + bands * 0.35 + streak * 0.3, 0, 0.95)
    color = color + (RIM - color) * np.clip(bands * 0.8 + streak, 0, 1)[:, :, None]
    # glowing rim at the water line
    rim = np.exp(-((1 - v) / 0.035) ** 2) + 0.4 * np.exp(-((1 - v) / 0.1) ** 2)
    color = color + (RIM - color) * np.clip(rim, 0, 1)[:, :, None]
    alpha = np.clip(alpha + rim * 0.5, 0, 0.97)
    img = fx.blank(w, h)
    img[:, :, :3] = np.clip(color, 0, 1)
    img[:, :, 3] = alpha
    if crackles:
        img = lightning(img, w, h, seed)
    return img


def lightning(img, w, h, seed):
    """A couple of thin crackles; drawn three times (shifted by the width) so they tile."""
    rng = np.random.default_rng(seed)
    xs, ys = fx.grid(w, h)
    mask = np.zeros((h, w), np.float32)
    for _ in range(rng.integers(1, 3)):
        x = rng.uniform(0, w)
        y = rng.uniform(0.25, 0.55) * h
        pts = [(x, y)]
        for _ in range(9):
            x += rng.uniform(-0.06, 0.06) * w
            y += rng.uniform(0.03, 0.07) * h
            pts.append((x, y))
        for shift in (-w, 0, w):
            shifted = [(px + shift, py) for px, py in pts]
            mask = np.maximum(mask, fx.polyline_mask(w, h, shifted, 1.6 * w / 256, xs, ys))
    glow = np.clip(fx.blur(mask, 3.0 * w / 256) * 2.2, 0, 1)
    layer = fx.fill(w, h, glow, fx.rgb((150, 210, 255), 0.6))
    img = fx.over(img, layer)
    return fx.over(img, fx.fill(w, h, mask, fx.rgb((240, 250, 255), 0.95)))


frames = []
for f in range(FRAMES):
    frames.append(wall(256, 256, f / FRAMES, 500 + f, crackles=(f % 4 in (0, 1))))
    print("zone frame", f + 1, "/", FRAMES)
sheet = fx.atlas(frames, 4)
fx.save_png(os.path.join(OUT, "zone_wall_flipbook.png"), sheet)
fx.save_png(os.path.join(OUT, "zone_wall_static.png"), wall(512, 512, 0.0, 900, crackles=True))
fx.save_png(os.path.join(OUT, "zone_wall_preview_water.png"), fx.on_background(sheet, (78, 214, 251)))
fx.save_png(os.path.join(OUT, "zone_wall_preview_sky.png"), fx.on_background(sheet, (150, 205, 245)))
# three copies side by side to check the horizontal tiling
tile = np.concatenate([frames[0]] * 3, axis=1)
fx.save_png(os.path.join(OUT, "zone_wall_tiling_check.png"), fx.on_background(tile, (78, 214, 251)))
print("done")
