"""Building blocks shared by the characters: profiles, hashed patterns, eyes, brows, teeth and fin plates."""
import math

import numpy as np

from voxlib import G, T, rot


def pl(x, pts):
    """Piecewise linear profile through [(x, value), ...] (any order)."""
    pts = sorted(pts)
    return float(np.interp(x, [p[0] for p in pts], [p[1] for p in pts]))


def rounded(y, z, top, bot, hw, n=4.0):
    """Rounded-rectangle cross-section test (n = 2 ellipse, larger = boxier)."""
    if top <= bot or hw <= 0:
        return False
    yc = (top + bot) / 2
    hy = (top - bot) / 2
    return (abs(y - yc) / hy) ** n + (abs(z) / hw) ** n <= 1.0


def h3(i, j, k, seed=0):
    """Stable pseudo-random value in [0, 1) for a voxel."""
    v = math.sin(i * 127.1 + j * 311.7 + k * 74.7 + seed * 19.19) * 43758.5453
    return v - math.floor(v)


def idx(v):
    return int(math.floor(v / G + 1e-6))


def eye(ch, seg, centre, side, white, pupil, size=0.22, pupil_size=(0.07, 0.09), pupil_shift=0.03, name="oeil",
        pupil_seg=True, socket=None):
    """Cube eye on the side of the head (side = +1 for +Z = the fish's right) with a pupil that can move
    (its own joint) slightly ahead of the centre; socket = colour of a frame around it."""
    cx, cy, cz = centre
    sfx = "d" if side > 0 else "g"
    h = size / 2
    zin, zout = (-0.008, 0.032) if side > 0 else (-0.032, 0.008)
    ch.boxes("%s_%s_blanc" % (name, sfx), seg, T((cx, cy, cz)), white, [((-h, -h, zin), (h, h, zout))])
    if socket:
        f = h + 0.035
        si, so = (-0.008, 0.016) if side > 0 else (-0.016, 0.008)
        ch.boxes("%s_%s_orbite" % (name, sfx), seg, T((cx, cy, cz)), socket, [((-f, -f, si), (f, f, so))])
    pw, ph = pupil_size
    zi, zo = (0.022, 0.046) if side > 0 else (-0.046, -0.022)
    ppos = (cx + pupil_shift, cy, cz)
    if pupil_seg:
        pname = "pupille_%s" % sfx
        ch.node(pname, seg, ppos)
        pseg = pname
    else:
        pseg = seg
    boxes = [((-pw / 2, -ph / 2, zi), (pw / 2, ph / 2, zo))]
    ch.boxes("%s_%s_pupille" % (name, sfx), pseg, T(ppos), pupil, boxes)
    return pseg


def top_eye(ch, seg, centre, side, white, iris, pupil, size=0.2, name="oeil"):
    """Eye sitting on top of the head (crocodile): white cube, coloured iris face, vertical slit pupil joint."""
    cx, cy, cz = centre
    sfx = "d" if side > 0 else "g"
    h = size / 2
    ch.boxes("%s_%s_blanc" % (name, sfx), seg, T((cx, cy, cz)), white, [((-h, -h, -h), (h, h, h))])
    # iris on the outer and front faces
    ch.boxes("%s_%s_iris" % (name, sfx), seg, T((cx, cy, cz)), iris, [
        ((-h + 0.02, -h + 0.03, (h - 0.002) if side > 0 else (-h - 0.012)), (h - 0.02, h - 0.03, (h + 0.012) if side > 0 else (-h + 0.002))),
        ((h - 0.002, -h + 0.03, -h + 0.02), (h + 0.012, h - 0.03, h - 0.02)),
    ])
    pname = "pupille_%s" % sfx
    ch.node(pname, seg, (cx, cy, cz))
    ch.boxes("%s_%s_pupille" % (name, sfx), pname, T((cx, cy, cz)), pupil, [
        ((-0.02, -0.07, (h + 0.008) if side > 0 else (-h - 0.022)), (0.02, 0.07, (h + 0.022) if side > 0 else (-h - 0.008))),
        ((h + 0.008, -0.07, -0.02), (h + 0.022, 0.07, 0.02)),
    ])
    return pname


def brow(ch, seg, centre, side, mat, tilt=-0.4, length=0.3, thick=0.08, out=0.05, name="sourcil"):
    """Brow bar joint; tilt < 0 lowers its front end (angry)."""
    sfx = "d" if side > 0 else "g"
    pname = "%s_%s" % (name, sfx)
    q = rot(pitch=tilt)
    ch.node(pname, seg, centre, q)
    zi, zo = (-0.03, out) if side > 0 else (-out, 0.03)
    ch.boxes("%s_%s_mesh" % (name, sfx), pname, T(centre, q), mat,
             [((-length / 2, -thick / 2, zi), (length / 2, thick / 2, zo))])
    return pname


def tooth(boxes, x, y, z, up, w=0.07, h=0.12, d=0.05):
    """A fang made of a wide base and a narrow tip; up = +1 points up, -1 down. Appends to boxes (model space)."""
    base_h = h * 0.55
    if up > 0:
        boxes.append(((x - w / 2, y, z - d / 2), (x + w / 2, y + base_h, z + d / 2)))
        boxes.append(((x - w / 4, y + base_h, z - d / 3), (x + w / 4, y + h, z + d / 3)))
    else:
        boxes.append(((x - w / 2, y - base_h, z - d / 2), (x + w / 2, y, z + d / 2)))
        boxes.append(((x - w / 4, y - h, z - d / 3), (x + w / 4, y - base_h, z + d / 3)))


def plate(ch, seg, cells, name):
    """Thin fin plate: cells {(i, j): mat} on the segment's local grid in X/Y, one voxel thick centred on z = 0."""
    vol = ch.volume(seg, name, off=(0.0, 0.0, -G / 2))
    for (i, j), m in cells.items():
        vol.cells[(i, j, 0)] = m
    return vol


def side_plate(ch, seg, cells, name, side):
    """Plate lying in the local X/Z plane (one voxel thick in Y), e.g. a leg sole or a flipper seen from above."""
    vol = ch.volume(seg, name, off=(0.0, -G / 2, 0.0))
    for (i, k), m in cells.items():
        vol.cells[(i, 0, k)] = m
    return vol
