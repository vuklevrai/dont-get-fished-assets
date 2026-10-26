# Generates the block textures used across the game (run inside Blender: numpy + image saving).
#
#   blender -b --factory-startup --python textures.py -- <out_dir>
#
# stud_color.png / stud_normal.png : 8x8 tiles (one tile = one 2-stud cell in Roblox, so the
#   MaterialVariant uses StudsPerTile = 16). No border lines between tiles: each tile has its own
#   slightly different shade (the soft "gradient" of the reference) and a raised rounded square.
# jolly_roger.png : pixel-art skull and crossbones, white on transparent, for the flag decal.
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def save_png(name, rgba):
    """rgba: (h, w, 4) float array, row 0 = top of the image."""
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"   # write the values as-is
    img.pixels.foreach_set(np.flipud(rgba).astype(np.float32).ravel())
    img.filepath_raw = os.path.join(OUT, name)
    img.file_format = "PNG"
    img.save()
    print("saved", img.filepath_raw)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def stud_textures(tiles=8, tile_px=128):
    n = tiles * tile_px
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    # position inside the tile, centred: -0.5 .. 0.5 (y grows downwards in the image)
    u = (xx % tile_px + 0.5) / tile_px - 0.5
    v = (yy % tile_px + 0.5) / tile_px - 0.5
    ti = (xx // tile_px).astype(int)
    tj = (yy // tile_px).astype(int)

    # per-tile shade: a smooth wave across the texture + a little random jitter per tile
    wave = 0.5 + 0.25 * np.sin(2 * np.pi * (np.arange(tiles)[:, None] / tiles) + 1.3) \
               + 0.25 * np.cos(2 * np.pi * (np.arange(tiles)[None, :] * 2 / tiles) + 0.4)
    jitter = rng.uniform(-0.5, 0.5, (tiles, tiles))
    shade = 0.935 + 0.035 * (wave - 0.5) * 2 + 0.018 * jitter       # ~0.88 .. 0.99
    base = shade[tj, ti]

    # rounded square "stud": signed distance to a rounded box of half size s, corner radius r
    s, r = 0.20, 0.07
    qx, qy = np.abs(u) - (s - r), np.abs(v) - (s - r)
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    inside = np.minimum(np.maximum(qx, qy), 0)
    d = outside + inside - r                       # < 0 inside the stud
    bevel = 0.035                                  # width of the sloped rim (tile units)

    inner = smoothstep(0.004, -0.004, d)           # 1 inside the stud
    rim = smoothstep(-bevel - 0.004, -bevel + 0.004, d) * inner   # 1 on the sloped rim
    # rim orientation: direction from the stud centre (light from the top-left)
    gx = np.where(np.abs(u) >= np.abs(v), np.sign(u), 0.0)
    gy = np.where(np.abs(v) > np.abs(u), np.sign(v), 0.0)
    light = (-gx - gy)                             # +1 facing top/left, -1 facing bottom/right
    col = base + inner * 0.03 + rim * light * 0.07
    # soft contact shadow just outside the bottom-right of the stud
    sh_d = np.hypot(np.maximum(np.abs(u - 0.015) - (s - r), 0), np.maximum(np.abs(v - 0.02) - (s - r), 0)) - r
    col -= (1 - inner) * smoothstep(0.03, 0.0, sh_d) * 0.06
    col = np.clip(col, 0, 1)
    rgba = np.dstack([col, col, col, np.ones_like(col)])
    save_png("stud_color.png", rgba)

    # normal map (OpenGL convention: +X right, +Y up in the image)
    tilt = 0.55
    nx = rim * gx * tilt
    ny = rim * (-gy) * tilt                        # image y grows downwards
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.dstack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5, np.ones_like(nx)])
    save_png("stud_normal.png", nrm)


SKULL = [
    "........................",
    "........XXXXXXXX........",
    "......XXXXXXXXXXXX......",
    ".....XXXXXXXXXXXXXX.....",
    "....XXXXXXXXXXXXXXXX....",
    "....XXXXXXXXXXXXXXXX....",
    "....XX....XXXX....XX....",
    "....X......XX......X....",
    "....X......XX......X....",
    "....XX....X..X....XX....",
    ".....XXXXXX..XXXXXX.....",
    "......XXXXXXXXXXXX......",
    ".......XX.XXXX.XX.......",
    ".......XXXXXXXXXX.......",
    "........X.X..X.X........",
    "........................",
    ".XX..................XX.",
    "XXXX................XXXX",
    ".XXXXX............XXXXX.",
    ".....XXXX......XXXX.....",
    "........XXXXXXXX........",
    ".....XXXX......XXXX.....",
    ".XXXXX............XXXXX.",
    "XXXX................XXXX",
    ".XX..................XX.",
]


def jolly_roger(scale=16):
    h, w = len(SKULL), len(SKULL[0])
    a = np.array([[1.0 if c == "X" else 0.0 for c in row] for row in SKULL])
    a = np.kron(a, np.ones((scale, scale)))
    pad = scale * 2
    a = np.pad(a, pad)
    bone = np.array([0.96, 0.94, 0.88])
    rgba = np.dstack([a * bone[0], a * bone[1], a * bone[2], a])
    save_png("jolly_roger.png", rgba)


stud_textures()
jolly_roger()
