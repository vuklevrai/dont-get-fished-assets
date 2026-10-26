# Small 2D drawing kit shared by the effect generators (runs inside Blender's Python: numpy + bpy).
# Images are float32 arrays (height, width, 4), straight alpha, sRGB values in 0..1, row 0 = top.
import math
import os

import numpy as np

try:
    import bpy
except ImportError:  # lets the drawing code be tested outside Blender
    bpy = None


def rgb(c, a=1.0):
    return np.array([c[0] / 255, c[1] / 255, c[2] / 255, a], dtype=np.float32)


def blank(w, h):
    return np.zeros((h, w, 4), dtype=np.float32)


def grid(w, h):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return xs + 0.5, ys + 0.5


def over(dst, src):
    """Composite src over dst (both straight alpha)."""
    sa = src[:, :, 3:4]
    da = dst[:, :, 3:4]
    out_a = sa + da * (1 - sa)
    safe = np.maximum(out_a, 1e-6)
    out = np.empty_like(dst)
    out[:, :, :3] = (src[:, :, :3] * sa + dst[:, :, :3] * da * (1 - sa)) / safe
    out[:, :, 3:4] = out_a
    return out


def fill(w, h, mask, color):
    """A layer of `color` with alpha = mask * color alpha."""
    img = blank(w, h)
    img[:, :, :3] = color[:3]
    img[:, :, 3] = np.clip(mask, 0, 1) * color[3]
    return img


def segment_distance(xs, ys, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 < 1e-9:
        return np.hypot(xs - ax, ys - ay)
    t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / length2, 0, 1)
    return np.hypot(xs - (ax + t * dx), ys - (ay + t * dy))


def polyline_mask(w, h, points, widths, xs=None, ys=None):
    """Anti-aliased mask of a polyline whose width can change along it (round joins and caps).
    `widths` is one value or one per point."""
    if xs is None:
        xs, ys = grid(w, h)
    if np.isscalar(widths):
        widths = [widths] * len(points)
    mask = np.zeros((h, w), dtype=np.float32)
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        half = 0.5 * (widths[i] + widths[i + 1]) / 2
        # only touch the bounding box of the segment
        x0 = int(max(0, math.floor(min(a[0], b[0]) - half - 2)))
        x1 = int(min(w, math.ceil(max(a[0], b[0]) + half + 2)))
        y0 = int(max(0, math.floor(min(a[1], b[1]) - half - 2)))
        y1 = int(min(h, math.ceil(max(a[1], b[1]) + half + 2)))
        if x0 >= x1 or y0 >= y1:
            continue
        d = segment_distance(xs[y0:y1, x0:x1], ys[y0:y1, x0:x1], a, b)
        m = np.clip(half + 0.5 - d, 0, 1)
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], m)
    return mask


def disc_mask(w, h, cx, cy, r, xs=None, ys=None):
    if xs is None:
        xs, ys = grid(w, h)
    return np.clip(r + 0.5 - np.hypot(xs - cx, ys - cy), 0, 1)


def blur(a, radius):
    """Separable box blur, 3 passes (close to a gaussian). Works on 2D or 3D arrays."""
    r = int(max(1, round(radius / 1.7)))
    out = a.astype(np.float32)
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0)] * out.ndim
            pad[axis] = (r, r)
            p = np.pad(out, pad, mode="constant")
            c = np.cumsum(p, axis=axis, dtype=np.float64)
            c = np.concatenate([np.zeros_like(np.take(c, [0], axis=axis)), c], axis=axis)
            n = out.shape[axis]
            hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
            lo = np.take(c, np.arange(0, n), axis=axis)
            out = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return out


def grow(mask, radius):
    """Dilate a mask by `radius` px (anti-aliased), like the splash script's outline."""
    h, w = mask.shape
    grown = np.zeros_like(mask)
    r = int(math.ceil(radius))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            dist = math.hypot(dx, dy)
            if dist > radius + 0.5:
                continue
            weight = min(1.0, radius + 0.5 - dist)
            shifted = np.zeros_like(mask)
            ys = slice(max(dy, 0), h + min(dy, 0))
            yd = slice(max(-dy, 0), h + min(-dy, 0))
            xs = slice(max(dx, 0), w + min(dx, 0))
            xd = slice(max(-dx, 0), w + min(-dx, 0))
            shifted[yd, xd] = mask[ys, xs]
            grown = np.maximum(grown, shifted * weight)
    return grown


def outline(img, radius, color):
    """Puts a coloured outline of `radius` px under the drawing."""
    h, w, _ = img.shape
    ring = grow(img[:, :, 3], radius)
    return over(fill(w, h, ring, rgb(color)), img)


def value_noise(w, h, cell, seed, octaves=3, xs=None, ys=None, wrap_x=False):
    """Smooth value noise in 0..1 (bicubic-ish), tileable horizontally if wrap_x."""
    rng = np.random.default_rng(seed)
    if xs is None:
        xs, ys = grid(w, h)
    total = np.zeros((h, w), dtype=np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = cell / (2 ** o)
        gw = int(math.ceil(w / c)) + 3
        gh = int(math.ceil(h / c)) + 3
        lattice = rng.random((gh, gw)).astype(np.float32)
        if wrap_x:
            period = max(1, int(round(w / c)))
            lattice[:, period:] = lattice[:, : gw - period]
        u = xs / c
        v = ys / c
        i0 = np.floor(u).astype(int)
        j0 = np.floor(v).astype(int)
        fu = u - i0
        fv = v - j0
        fu = fu * fu * (3 - 2 * fu)
        fv = fv * fv * (3 - 2 * fv)
        if wrap_x:
            period = max(1, int(round(w / c)))
            i0 %= period
            i1 = (i0 + 1) % period
        else:
            i1 = i0 + 1
        j1 = j0 + 1
        a = lattice[j0, i0] * (1 - fu) + lattice[j0, i1] * fu
        b = lattice[j1, i0] * (1 - fu) + lattice[j1, i1] * fu
        total += amp * (a * (1 - fv) + b * fv)
        norm += amp
        amp *= 0.5
    return total / norm


def atlas(frames, columns):
    h, w, _ = frames[0].shape
    rows = int(math.ceil(len(frames) / columns))
    sheet = np.zeros((rows * h, columns * w, 4), dtype=np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, columns)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = f
    return sheet


def on_background(img, color):
    h, w, _ = img.shape
    bg = blank(w, h)
    bg[:, :, :3] = np.array([v / 255 for v in color], dtype=np.float32)
    bg[:, :, 3] = 1
    return over(bg, img)


def save_png(path, img):
    img = np.clip(img, 0, 1).astype(np.float32)
    h, w, _ = img.shape
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if bpy is not None:
        im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
        im.colorspace_settings.name = "Non-Color"
        im.pixels.foreach_set(np.flipud(img).ravel())
        im.filepath_raw = os.path.abspath(path)
        im.file_format = "PNG"
        im.save()
        bpy.data.images.remove(im)
    else:
        from PIL import Image
        Image.fromarray((img * 255 + 0.5).astype(np.uint8), "RGBA").save(path)
    print("saved", path)


def load_png(path):
    if bpy is not None:
        im = bpy.data.images.load(os.path.abspath(path))
        im.colorspace_settings.name = "Non-Color"
        w, h = im.size
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        bpy.data.images.remove(im)
        return np.flipud(px)
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255
