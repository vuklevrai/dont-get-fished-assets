"""Don't Get Fished - new maps (Aquarium, Ballon, Ocean) and their models, described as Roblox primitives.

Same conventions and table format as spawn/dgf_assets.py: Roblox studs, Y up. Each primitive is a dict
    asset, group, shape (Block | Wedge | Cylinder | Ball), size (x, y, z), pos (x, y, z),
    rot (3x3, rows; columns are the part's Right / Up / Back vectors, like a Roblox CFrame),
    color (r, g, b 0-255), mat (Stud | Smooth | Glass | Neon | Wood | Metal | ForceField), transparency, collide
export_table() turns a list of them into the compact table read by the Roblox importer (same as dgf_assets).

Assets, each exported on its own: FuturisticPod, Aquarium, BallonPlatforms, FishingBoat, Island.
Anchors (fisherman spots, seaweed spots, spawn volumes...) come from the *_spots() functions.
Deterministic: every random draw uses a fixed seed.
"""
import math
import random

import numpy as np

# --------------------------------------------------------------------------------- math helpers
IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def norm(a):
    n = length(a)
    return mul(a, 1.0 / n) if n > 1e-9 else (0.0, 0.0, 0.0)


def matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(r, v):
    return tuple(r[i][0] * v[0] + r[i][1] * v[1] + r[i][2] * v[2] for i in range(3))


def from_axes(right, up, back):
    return tuple((right[i], up[i], back[i]) for i in range(3))


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def look_rot(direction, up=(0.0, 1.0, 0.0)):
    """Rotation whose LookVector (-Z) points along `direction` (like CFrame.lookAt)."""
    back = norm(mul(direction, -1))
    if abs(dot(back, up)) > 0.999:
        up = (1.0, 0.0, 0.0)
    right = norm(cross(up, back))
    return from_axes(right, cross(back, right), back)


def axis_x_rot(direction):
    """Rotation whose local X axis points along `direction` (Roblox cylinders run along X)."""
    x = norm(direction)
    tmp = (0.0, 1.0, 0.0) if abs(x[1]) < 0.99 else (1.0, 0.0, 0.0)
    z = norm(cross(x, tmp))
    return from_axes(x, cross(z, x), z)


VERTICAL = axis_x_rot((0.0, 1.0, 0.0))   # upright cylinders


def lerp(a, b, t):
    return a + (b - a) * t


def shade(color, f):
    return tuple(max(0, min(255, int(round(c * f)))) for c in color)


def mix(c0, c1, t):
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c0, c1))


def yaw_toward(frm, to):
    """Yaw (around Y) that turns -Z towards `to` seen from `frm`."""
    d = sub(to, frm)
    return math.atan2(-d[0], -d[2])


def cframe(pos, rot):
    """12 numbers for CFrame.new(x, y, z, R00, R01, R02, R10, R11, R12, R20, R21, R22)."""
    return [round(v, 4) for v in (*pos, *rot[0], *rot[1], *rot[2])]


def quat_from_rot(r):
    m00, m01, m02 = r[0]
    m10, m11, m12 = r[1]
    m20, m21, m22 = r[2]
    tr = m00 + m11 + m22
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return ((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s)
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        return (0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        return ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2
    return ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)


def spot(pos, rot, **extra):
    q = quat_from_rot(rot)
    d = {"pos": [round(v, 3) for v in pos], "quat": [round(v, 5) for v in q], "cframe": cframe(pos, rot)}
    d.update(extra)
    return d


def clear_points(prims, sample, count, margin, seed, min_gap=20.0):
    """`count` random points from `sample(rng)` that are at least `margin` studs away from every collidable
    primitive (oriented boxes, a little conservative for cylinders and balls) and `min_gap` from each other."""
    boxes = []
    for p in prims:
        if not p["collide"]:
            continue
        r = np.array(p["rot"], float)
        boxes.append((np.array(p["pos"], float), r, np.array(p["size"], float) / 2 + margin))
    rng = random.Random(seed)
    out = []
    for _ in range(count * 200):
        if len(out) >= count:
            break
        q = np.array(sample(rng), float)
        if any(np.linalg.norm(q - np.array(o)) < min_gap for o in out):
            continue
        blocked = False
        for c, r, half in boxes:
            local = r.T @ (q - c)
            if np.all(np.abs(local) <= half):
                blocked = True
                break
        if not blocked:
            out.append([round(float(v), 2) for v in q])
    return out


# --------------------------------------------------------------------------------- primitives
class Asset:
    def __init__(self, name):
        self.name = name
        self.prims = []

    def prim(self, group, shape, size, pos, rot=IDENT, color=(255, 255, 255), mat="Stud", transparency=0.0,
             collide=True):
        p = dict(asset=self.name, group=group, shape=shape, size=tuple(float(v) for v in size),
                 pos=tuple(float(v) for v in pos), rot=rot, color=tuple(int(c) for c in color), mat=mat,
                 transparency=float(transparency), collide=bool(collide))
        self.prims.append(p)
        return p

    def box(self, group, lo, hi, color, mat="Stud", transparency=0.0, collide=True):
        """Axis-aligned block from corner `lo` to corner `hi`."""
        size = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
        if min(size) <= 1e-6:
            return None
        return self.prim(group, "Block", size, mul(add(lo, hi), 0.5), IDENT, color, mat, transparency, collide)

    def cylinder(self, group, a, b, diameter, color, mat="Smooth", collide=True, transparency=0.0):
        d = sub(b, a)
        return self.prim(group, "Cylinder", (length(d), diameter, diameter), mul(add(a, b), 0.5), axis_x_rot(d),
                         color, mat, transparency, collide)

    def beam(self, group, a, b, w, h, color, mat="Stud", collide=True, up=(0.0, 1.0, 0.0)):
        """Block of section w x h running from a to b."""
        d = sub(b, a)
        return self.prim(group, "Block", (w, h, length(d)), mul(add(a, b), 0.5), look_rot(d, up), color, mat,
                         collide=collide)

    def place(self, other, offset=(0, 0, 0), rot=IDENT):
        """Copy another asset's primitives into this one, rotated then moved."""
        for p in other.prims:
            q = dict(p)
            q["asset"] = self.name
            q["pos"] = add(offset, apply(rot, p["pos"]))
            q["rot"] = matmul(rot, p["rot"])
            self.prims.append(q)

    def count(self, groups=None):
        return sum(1 for p in self.prims if groups is None or p["group"] in groups)


def export_table(prims):
    """Compact JSON-able table: string lists + one number row per primitive (same as spawn/dgf_assets.py)."""
    assets, groups, shapes, mats = [], [], ["Block", "Wedge", "Cylinder", "Ball"], []

    def index(lst, v):
        if v not in lst:
            lst.append(v)
        return lst.index(v)

    rows = []
    for p in prims:
        q = quat_from_rot(p["rot"])
        rows.append([index(assets, p["asset"]), index(groups, p["group"]), shapes.index(p["shape"]),
                     index(mats, p["mat"]), 1 if p["collide"] else 0, round(p["transparency"], 2),
                     *p["color"], *[round(v, 3) for v in p["size"]], *[round(v, 3) for v in p["pos"]],
                     *[round(v, 5) for v in q]])
    return {"v": 1, "assets": assets, "groups": groups, "shapes": shapes, "mats": mats, "prims": rows}


# --------------------------------------------------------------------------------- voxels and noise
def value_noise3(points, cell, seed):
    """Smooth 3D value noise in 0..1 at an (n, 3) array of points."""
    rng = np.random.default_rng(seed)
    lattice = rng.random((64, 64, 64))
    p = np.asarray(points, float) / cell + 16.0
    i0 = np.floor(p).astype(int)
    f = p - i0
    f = f * f * (3 - 2 * f)
    out = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (np.where(dx, f[:, 0], 1 - f[:, 0]) * np.where(dy, f[:, 1], 1 - f[:, 1]) *
                     np.where(dz, f[:, 2], 1 - f[:, 2]))
                idx = (i0 + np.array([dx, dy, dz])) % 64
                out += w * lattice[idx[:, 0], idx[:, 1], idx[:, 2]]
    return out


def merge_boxes(labels):
    """Greedy merge of a 3D label grid (0 = empty) into boxes (x0, y0, z0, x1, y1, z1, label), cell units."""
    nx, ny, nz = labels.shape
    done = np.zeros(labels.shape, bool)
    boxes = []
    for y in range(ny):
        for z in range(nz):
            for x in range(nx):
                lab = labels[x, y, z]
                if lab == 0 or done[x, y, z]:
                    continue
                x1 = x + 1
                while x1 < nx and labels[x1, y, z] == lab and not done[x1, y, z]:
                    x1 += 1
                z1 = z + 1
                while z1 < nz and np.all(labels[x:x1, y, z1] == lab) and not np.any(done[x:x1, y, z1]):
                    z1 += 1
                y1 = y + 1
                while y1 < ny and np.all(labels[x:x1, y1, z:z1] == lab) and not np.any(done[x:x1, y1, z:z1]):
                    y1 += 1
                done[x:x1, y:y1, z:z1] = True
                boxes.append((x, y, z, x1, y1, z1, int(lab)))
    return boxes


def voxel_object(asset, group, origin, cell, solid, palette, seed, pit_share=0.15, shade_share=0.25,
                 noise_cell=7.0, collide=True):
    """Blocks for a boolean grid `solid` (indexed [x, y, z], cell `cell` studs, corner at `origin`).
    Visible cells get one of three colours from smooth noise (base / shade / pit); hidden cells take the
    base colour so they merge into big blocks."""
    nx, ny, nz = solid.shape
    labels = np.zeros(solid.shape, np.int32)
    pad = np.pad(solid, 1)
    exposed = solid & ~(pad[2:, 1:-1, 1:-1] & pad[:-2, 1:-1, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, :-2, 1:-1] &
                        pad[1:-1, 1:-1, 2:] & pad[1:-1, 1:-1, :-2])
    idx = np.argwhere(exposed)
    centres = origin + (idx + 0.5) * cell
    n = value_noise3(centres, noise_cell, seed)
    fine = value_noise3(centres, noise_cell * 0.45, seed + 1)
    lab = np.ones(len(idx), np.int32)
    lab[n > 1 - shade_share * 1.6] = 2
    lab[(fine > 1 - pit_share * 1.4) & (n < 0.7)] = 3
    labels[solid] = 1
    labels[tuple(idx.T)] = lab
    for x0, y0, z0, x1, y1, z1, k in merge_boxes(labels):
        lo = origin + np.array([x0, y0, z0]) * cell
        hi = origin + np.array([x1, y1, z1]) * cell
        asset.box(group, tuple(lo), tuple(hi), palette[k - 1], "Stud", collide=collide)


def ellipsoid_sdf(p, centre, radii):
    q = (p - np.asarray(centre)) / np.asarray(radii)
    return (np.linalg.norm(q, axis=-1) - 1.0) * min(radii)


def capsule_sdf(p, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=-1) - r


def wall_with_openings(asset, group, start, direction, length_, height, thickness, openings, color, inward,
                       mat="Stud", shades=None):
    """A straight wall on the ground from `start` along horizontal unit `direction`, with rectangular
    openings [(u0, u1, v0, v1), ...] in wall coordinates (u along the wall, v up). The wall's back face is on
    the `inward` side. Returns the blocks (merged per column band)."""
    cuts = sorted({0.0, length_, *[o[0] for o in openings], *[o[1] for o in openings]})
    bands = []
    for u0, u1 in zip(cuts[:-1], cuts[1:]):
        if u1 - u0 < 1e-6:
            continue
        um = (u0 + u1) / 2
        holes = sorted((o[2], o[3]) for o in openings if o[0] <= um <= o[1])
        solid = []
        v = 0.0
        for v0, v1 in holes:
            if v0 > v:
                solid.append((v, v0))
            v = max(v, v1)
        if v < height:
            solid.append((v, height))
        if bands and bands[-1][2] == solid:
            bands[-1] = (bands[-1][0], u1, solid)
        else:
            bands.append((u0, u1, solid))
    d = norm(direction)
    n = norm(inward)
    rot = from_axes(d, (0.0, 1.0, 0.0), cross(d, (0.0, 1.0, 0.0)))
    out = []
    for k, (u0, u1, solid) in enumerate(bands):
        for j, (v0, v1) in enumerate(solid):
            centre = add(add(start, mul(d, (u0 + u1) / 2)), (0.0, (v0 + v1) / 2, 0.0))
            centre = add(centre, mul(n, thickness / 2))
            c = color if shades is None else shades[(k + j) % len(shades)]
            out.append(asset.prim(group, "Block", (u1 - u0, v1 - v0, thickness), centre, rot, c, mat))
    return out


# =========================================================================================== POD
POD_RADIUS = 8.0
POD_RAMP = 6.0            # the ramp sticks out this far beyond the disc, towards the water
METAL = (206, 212, 222)
METAL_DARK = (92, 100, 118)
PANEL = (48, 56, 74)
CYAN = (0, 232, 255)
CYAN_SOFT = (120, 246, 255)


def build_pod():
    """FuturisticPod: a hovering metal disc with a cyan neon ring, a short ramp towards the water (-Z, the
    LookVector), glowing arch and posts at the back, hover thrusters underneath.
    Local origin = centre of the floor surface (where the fisherman stands), facing -Z."""
    pod = Asset("FuturisticPod")
    r = POD_RADIUS
    # disc and floor
    pod.cylinder("Floor", (0, -1.6, 0), (0, 0, 0), 2 * r, METAL, "Metal")
    pod.cylinder("Floor", (0, 0, 0), (0, 0.12, 0), 2 * r - 3.0, PANEL, "Smooth")
    pod.cylinder("Neon", (0, -1.75, 0), (0, -0.55, 0), 2 * r + 0.8, CYAN, "Neon", collide=False)
    pod.cylinder("Floor", (0, 0.12, 0), (0, 0.22, 0), 4.0, CYAN_SOFT, "Neon", collide=False)
    # floor lines (spokes)
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        d = (math.sin(a), 0.0, math.cos(a))
        pod.beam("Floor", add(mul(d, 2.4), (0, 0.17, 0)), add(mul(d, r - 1.8), (0, 0.17, 0)), 0.35, 0.12, CYAN,
                 "Neon", collide=False)
    # hover base: stepped cone + three thrusters
    for k, (d, y0, y1) in enumerate(((2 * r - 2.5, -3.0, -1.6), (2 * r - 6.0, -4.4, -3.0), (2 * r - 10.0, -5.6, -4.4))):
        pod.cylinder("Hull", (0, y0, 0), (0, y1, 0), d, METAL_DARK if k else METAL, "Metal")
    pod.cylinder("Neon", (0, -6.2, 0), (0, -5.6, 0), 3.4, CYAN, "Neon", collide=False)
    for k in range(3):
        a = k * 2 * math.pi / 3
        c = (math.sin(a) * (r - 3.2), 0.0, math.cos(a) * (r - 3.2))
        pod.cylinder("Hull", add(c, (0, -3.6, 0)), add(c, (0, -1.6, 0)), 2.4, METAL_DARK, "Metal")
        pod.cylinder("Neon", add(c, (0, -4.0, 0)), add(c, (0, -3.6, 0)), 1.8, CYAN, "Neon", collide=False)
    # ramp towards the water: a plate and a slightly sloped lip
    lip = r + POD_RAMP
    pod.box("Ramp", (-2.6, -0.8, -(r + 0.5)), (2.6, 0.0, -(r - 1.5)), METAL, "Metal")
    pod.prim("Ramp", "Block", (5.2, 0.6, POD_RAMP - 1.0), (0, -0.3, -(r + (POD_RAMP - 1.0) / 2 + 0.5)), IDENT, METAL,
             "Metal")
    pod.prim("Ramp", "Wedge", (5.2, 0.6, 1.5), (0, -0.3, -(lip + 0.25)), IDENT, METAL, "Metal")   # slopes down outwards
    for s in (-1, 1):
        pod.box("Ramp", (s * 2.6 - 0.15, -0.8, -lip), (s * 2.6 + 0.15, 0.25, -(r - 1.5)), CYAN, "Neon", collide=False)
        # little pylons at the ramp's root
        pod.cylinder("Post", (s * 3.6, 0, -(r - 1.2)), (s * 3.6, 2.4, -(r - 1.2)), 0.9, METAL, "Metal")
        pod.prim("Post", "Ball", (1.2, 1.2, 1.2), (s * 3.6, 2.7, -(r - 1.2)), IDENT, CYAN, "Neon", collide=False)
    # back half: posts with neon rails, and a glowing arch
    rail_y = 3.2
    n = 9
    pts = []
    for k in range(n):
        a = math.pi * (0.3 + 1.4 * k / (n - 1))       # from right-front round the back to left-front
        pts.append((math.sin(a) * (r - 0.7), math.cos(a) * (r - 0.7)))
    for k, (x, z) in enumerate(pts):
        pod.cylinder("Post", (x, 0, z), (x, rail_y, z), 0.6, METAL, "Metal")
        if k:
            px, pz = pts[k - 1]
            pod.beam("Rail", (px, rail_y, pz), (x, rail_y, z), 0.45, 0.3, CYAN, "Neon", collide=False)
            pod.beam("Rail", (px, rail_y - 1.4, pz), (x, rail_y - 1.4, z), 0.25, 0.25, METAL, "Metal", collide=False)
    # arch over the back, built from short straight pieces
    arch_r, arch_h = 5.6, 7.4
    prev = None
    for k in range(11):
        t = math.pi * k / 10
        p = (math.cos(t) * arch_r, rail_y - 0.4 + math.sin(t) * (arch_h - rail_y + 0.4), r - 1.2)
        if prev:
            pod.beam("Arch", prev, p, 0.9, 0.9, METAL, "Metal")
            pod.beam("Arch", add(prev, (0, 0, -0.5)), add(p, (0, 0, -0.5)), 0.35, 0.35, CYAN, "Neon", collide=False)
        prev = p
    for s in (-1, 1):
        pod.cylinder("Arch", (s * arch_r, 0, r - 1.2), (s * arch_r, rail_y - 0.4, r - 1.2), 1.2, METAL, "Metal")
    # console at the back
    pod.box("Console", (-1.4, 0.12, r - 3.4), (1.4, 1.8, r - 2.2), METAL_DARK, "Metal")
    pod.prim("Console", "Block", (2.4, 0.15, 1.2), (0, 1.9, r - 2.8), rot_x(math.radians(-25)), CYAN_SOFT, "Neon",
             collide=False)
    return pod


# =========================================================================================== AQUARIUM
WATER_LEVEL = -1.0
HALF_X, HALF_Z = 162.0, 126.0          # water: 324 x 252 studs
GLASS_T = 2.0
FLOOR_Y = -94.0                        # top of the glass floor (bottom of the sand)
SAND_Y = -86.0                         # average sand surface: ~85 studs of water above it
GLASS_TOP = 8.0
RIM_T, RIM_W = 3.0, 6.0
RIM_TOP = GLASS_TOP + RIM_T

SAND = (228, 202, 152)
SAND_LIGHT = (238, 216, 170)
SAND_DARK = (212, 184, 136)
GRAVEL = ((150, 132, 112), (118, 104, 92), (244, 240, 230), (186, 160, 128))
GLASS_COLOR = (205, 238, 244)
FRAME = (24, 150, 140)
FRAME_DARK = (18, 112, 106)
WOOD = (204, 162, 108)
WOOD_DARK = (176, 134, 86)
WOOD_LIGHT = (222, 186, 134)
ROCK = ((236, 232, 218), (216, 208, 188), (156, 148, 134))
CASTLE_STONE = ((178, 180, 190), (166, 168, 180), (188, 190, 198))
ROOF_RED = (200, 62, 60)
ROOF_BLUE = (62, 104, 198)

ROCK_CENTRE = (0.0, SAND_Y, 4.0)
ROCK_SCALE = 1.35
CASTLE_CENTRE = (-100.0, SAND_Y, 50.0)
ARCH_CENTRE = (104.0, SAND_Y, -54.0)
CHEST = (78.0, 66.0)


def sand_height(x, z):
    """Sand surface: gentle dunes, a bit higher at the back (+z) like a real tank."""
    n = (math.sin(x * 0.031 + 1.3) * math.cos(z * 0.027 - 0.4) + 0.6 * math.sin(x * 0.07 + z * 0.05 + 2.0))
    back = (z + HALF_Z) / (2 * HALF_Z)
    return SAND_Y - 2.0 + 1.6 * n + 4.0 * back


SAND_TILE = 18.0


def sand_top(x, z):
    """Top of the sand tile under (x, z): what objects actually stand on."""
    i = min(int((x + HALF_X) // SAND_TILE), int(2 * HALF_X / SAND_TILE) - 1)
    k = min(int((z + HALF_Z) // SAND_TILE), int(2 * HALF_Z / SAND_TILE) - 1)
    cx, cz = -HALF_X + (i + 0.5) * SAND_TILE, -HALF_Z + (k + 0.5) * SAND_TILE
    return float(round(sand_height(cx, cz)))


def build_sand(tank, rng):
    tile = SAND_TILE
    nx, nz = int(2 * HALF_X / tile), int(2 * HALF_Z / tile)
    for i in range(nx):
        for k in range(nz):
            x0, z0 = -HALF_X + i * tile, -HALF_Z + k * tile
            cx, cz = x0 + tile / 2, z0 + tile / 2
            h = round(sand_height(cx, cz))
            # soft gradient: lighter in the middle, a touch darker near the glass, plus patches
            edge = max(abs(cx) / HALF_X, abs(cz) / HALF_Z)
            t = 0.5 + 0.3 * math.sin(cx * 0.035 + cz * 0.05) + 0.15 * math.cos(cx * 0.09 - cz * 0.04) - 0.3 * edge
            color = SAND_DARK if t < 0.25 else (SAND if t < 0.62 else SAND_LIGHT)
            tank.box("Sand", (x0, FLOOR_Y, z0), (x0 + tile, h, z0 + tile), color, "Stud")
    # gravel and little pebbles scattered on top
    for _ in range(140):
        x = rng.uniform(-HALF_X + 4, HALF_X - 4)
        z = rng.uniform(-HALF_Z + 4, HALF_Z - 4)
        if math.hypot(x - ROCK_CENTRE[0], z - ROCK_CENTRE[2]) < 54 or math.hypot(x - CASTLE_CENTRE[0], z - CASTLE_CENTRE[2]) < 40:
            continue
        s = rng.uniform(1.2, 2.6)
        y = sand_top(x, z)
        tank.prim("Gravel", "Block", (s, s * 0.6, s * rng.uniform(0.8, 1.3)), (x, y + s * 0.3 - 0.1, z),
                  rot_y(rng.uniform(0, math.pi)), rng.choice(GRAVEL), "Smooth")


def build_glass(tank):
    x_out, z_out = HALF_X + GLASS_T, HALF_Z + GLASS_T
    bottom = FLOOR_Y - GLASS_T
    g = dict(mat="Glass", transparency=0.6)
    tank.box("Glass", (-x_out, bottom, -z_out), (x_out, FLOOR_Y, z_out), GLASS_COLOR, **g)
    for s in (-1, 1):
        tank.box("Glass", (s * HALF_X if s > 0 else -x_out, bottom, -z_out), (x_out if s > 0 else -HALF_X, GLASS_TOP, z_out),
                 GLASS_COLOR, **g)
        tank.box("Glass", (-HALF_X, bottom, s * HALF_Z if s > 0 else -z_out), (HALF_X, GLASS_TOP, z_out if s > 0 else -HALF_Z),
                 GLASS_COLOR, **g)
    # coloured plastic frame: corner posts, bottom trim, thick top rim with a neon light strip
    for sx in (-1, 1):
        for sz in (-1, 1):
            tank.box("Frame", (sx * x_out - 1.5, bottom - 1.0, sz * z_out - 1.5), (sx * x_out + 1.5, GLASS_TOP, sz * z_out + 1.5),
                     FRAME, "Smooth")
    tank.box("Frame", (-x_out - 1.5, bottom - 1.0, -z_out - 1.5), (x_out + 1.5, bottom + 2.0, -z_out + 0.5), FRAME, "Smooth")
    tank.box("Frame", (-x_out - 1.5, bottom - 1.0, z_out - 0.5), (x_out + 1.5, bottom + 2.0, z_out + 1.5), FRAME, "Smooth")
    tank.box("Frame", (-x_out - 1.5, bottom - 1.0, -z_out + 0.5), (-x_out + 0.5, bottom + 2.0, z_out - 0.5), FRAME, "Smooth")
    tank.box("Frame", (x_out - 0.5, bottom - 1.0, -z_out + 0.5), (x_out + 1.5, bottom + 2.0, z_out - 0.5), FRAME, "Smooth")
    half = RIM_W / 2
    edge_x, edge_z = HALF_X + GLASS_T / 2, HALF_Z + GLASS_T / 2
    for s in (-1, 1):
        tank.box("Rim", (-edge_x - half, GLASS_TOP, s * edge_z - half), (edge_x + half, RIM_TOP, s * edge_z + half), FRAME,
                 "Smooth")
        tank.box("Rim", (s * edge_x - half, GLASS_TOP, -edge_z + half), (s * edge_x + half, RIM_TOP, edge_z - half), FRAME,
                 "Smooth")
        # darker underside lip on the water side and a neon strip on top
        tank.box("Rim", (-edge_x + half, GLASS_TOP - 1.0, s * (edge_z - half) - 0.5), (edge_x - half, GLASS_TOP, s * (edge_z - half) + 0.5),
                 FRAME_DARK, "Smooth")
        tank.box("Rim", (s * (edge_x - half) - 0.5, GLASS_TOP - 1.0, -edge_z + half), (s * (edge_x - half) + 0.5, GLASS_TOP, edge_z - half),
                 FRAME_DARK, "Smooth")
        tank.box("Light", (-edge_x, RIM_TOP, s * edge_z - 0.4), (edge_x, RIM_TOP + 0.3, s * edge_z + 0.4), CYAN, "Neon", collide=False)
        tank.box("Light", (s * edge_x - 0.4, RIM_TOP, -edge_z), (s * edge_x + 0.4, RIM_TOP + 0.3, edge_z), CYAN, "Neon", collide=False)


def build_cabinet(tank, rng):
    """The wooden cabinet the tank stands on, and a light wood backdrop behind the back glass."""
    top = FLOOR_Y - GLASS_T - 1.0
    tank.box("Cabinet", (-HALF_X - 12, top - 4.0, -HALF_Z - 12), (HALF_X + 12, top, HALF_Z + 12), WOOD, "Wood")
    tank.box("Cabinet", (-HALF_X - 6, top - 56.0, -HALF_Z - 6), (HALF_X + 6, top - 4.0, HALF_Z + 6), WOOD_DARK, "Wood")
    # front and back doors with handles, plinth
    for s in (-1, 1):
        z = s * (HALF_Z + 6)
        for k in range(4):
            x0 = -HALF_X + 2 + k * (2 * HALF_X - 4) / 4
            x1 = x0 + (2 * HALF_X - 4) / 4 - 3
            tank.box("Cabinet", (x0, top - 52.0, z - 0.6 if s < 0 else z), (x1, top - 8.0, z if s < 0 else z + 0.6),
                     WOOD if k % 2 else WOOD_LIGHT, "Wood")
            hx = x1 - 4 if k % 2 == 0 else x0 + 4
            tank.box("Cabinet", (hx - 0.6, top - 34.0, z - 1.4 if s < 0 else z + 0.6), (hx + 0.6, top - 24.0, z - 0.6 if s < 0 else z + 1.4),
                     (200, 204, 212), "Metal")
    tank.box("Cabinet", (-HALF_X - 4, top - 62.0, -HALF_Z - 4), (HALF_X + 4, top - 56.0, HALF_Z + 4), (120, 88, 56), "Wood")
    # backdrop: vertical light planks just behind the back glass (like the reference photo)
    z0 = HALF_Z + GLASS_T + 0.6
    n = 14
    for k in range(n):
        x0 = -HALF_X + k * 2 * HALF_X / n
        c = WOOD_LIGHT if k % 3 == 0 else (shade(WOOD_LIGHT, 0.95) if k % 3 == 1 else shade(WOOD_LIGHT, 1.03))
        tank.box("Backdrop", (x0, FLOOR_Y - 2.0, z0), (x0 + 2 * HALF_X / n, GLASS_TOP - 4.0, z0 + 1.0), c, "Wood")


def build_rock(tank, cut_z=None):
    """The big porous rock in the middle: hollow, with tunnels a size-5 fish (9 x 3.5 studs) swims through.
    cut_z (previews only) keeps the part behind that plane, to show the inside in a section view."""
    k = ROCK_SCALE
    cell = 3.5
    cx, cy, cz = ROCK_CENTRE
    origin = np.array([cx - 40.0 * k, cy - 6.0, cz - 34.0 * k])
    nx, ny, nz = int(80 * k / cell) + 1, int((46 * k) / cell) + 1, int(68 * k / cell) + 1
    idx = np.indices((nx, ny, nz)).reshape(3, -1).T
    p = origin + (idx + 0.5) * cell

    def at(dx, dy, dz):
        return (cx + dx * k, cy + dy * k, cz + dz * k)

    def radii(rx, ry, rz):
        return (rx * k, ry * k, rz * k)

    d = ellipsoid_sdf(p, at(0, 2, 0), radii(32, 22, 27))
    for c, r in ((at(15, 7, 9), radii(18, 17, 15)), (at(-17, 5, -7), radii(17, 19, 16)),
                 (at(4, 18, -3), radii(16, 12, 14)), (at(-9, 3, 15), radii(14, 13, 11))):
        d = np.minimum(d, ellipsoid_sdf(p, c, r))
    d += 4.5 * (value_noise3(p, 11.0, 3) - 0.5)
    solid = d < 0
    # hollow chamber and tunnels (14-stud bores: about 11 clear after voxelising)
    chamber = ellipsoid_sdf(p, at(0, 8, 0), radii(14, 9, 12)) < 0
    tunnels = [
        (at(-45, 8, 2), at(45, 7, -2), 7.0),     # east-west, through the chamber
        (at(3, 9, -40), at(-3, 8, 40), 7.0),     # north-south, through the chamber
        (at(-34, 7, -32), at(0, 8, 0), 6.5),     # diagonal, into the chamber
        (at(2, 8, 0), at(3, 40, -2), 6.5),       # chimney out of the top
    ]
    for a, b, r in tunnels:
        chamber |= capsule_sdf(p, a, b, r) < 0
    solid &= ~chamber
    if cut_z is not None:
        solid &= p[:, 2] >= cut_z
    solid = solid.reshape(nx, ny, nz)
    voxel_object(tank, "Rock", origin, cell, solid, ROCK, seed=11, noise_cell=9.0)
    return tunnels


def build_rock_arch(tank):
    """A stone arch the fish can swim under, on the right of the tank."""
    cell = 3.0
    cx, cy, cz = ARCH_CENTRE
    origin = np.array([cx - 30.0, cy - 4.0, cz - 12.0])
    nx, ny, nz = 20, 15, 8
    idx = np.indices((nx, ny, nz)).reshape(3, -1).T
    p = origin + (idx + 0.5) * cell
    # half torus standing on the sand: centre line radius 21, tube radius 7, slightly squashed
    q = p - np.array([cx, cy, cz])
    ring = np.sqrt(q[:, 0] ** 2 + (q[:, 1] * 1.05) ** 2) - 21.0
    d = np.sqrt(ring ** 2 + (q[:, 2] * 1.25) ** 2) - 7.0
    d += 3.0 * (value_noise3(p, 6.0, 41) - 0.5)
    solid = (d < 0) & (p[:, 1] > cy - 4.0)
    voxel_object(tank, "Rock", origin, cell, solid.reshape(nx, ny, nz), ROCK, seed=43, noise_cell=6.0)


def build_amphora(tank):
    """A sunken amphora lying on its side, half buried."""
    x, z = -46.0, -78.0
    y = sand_top(x, z) + 3.2
    d = (math.cos(0.6), 0.08, math.sin(0.6))
    body = (196, 108, 64)
    tank.cylinder("Amphora", add((x, y, z), mul(d, -6)), add((x, y, z), mul(d, 6)), 8.0, body, "Smooth")
    tank.prim("Amphora", "Ball", (9.0, 9.0, 9.0), add((x, y, z), mul(d, -5.5)), IDENT, body, "Smooth")
    tank.cylinder("Amphora", add((x, y, z), mul(d, 6)), add((x, y, z), mul(d, 10)), 3.6, shade(body, 0.9), "Smooth")
    tank.cylinder("Amphora", add((x, y, z), mul(d, 10)), add((x, y, z), mul(d, 11)), 5.0, shade(body, 1.08), "Smooth")
    tank.cylinder("Amphora", add((x, y, z), mul(d, -2)), add((x, y, z), mul(d, 0.5)), 8.3, (230, 196, 120), "Smooth",
                  collide=False)


def build_small_rocks(tank, rng):
    spots = [(118.0, -40.0, 7.0), (-140.0, -96.0, 6.0), (36.0, 100.0, 5.0), (-40.0, -92.0, 5.5), (140.0, 92.0, 6.5)]
    for k, (x, z, r) in enumerate(spots):
        cell = 2.0
        n = int(2 * r / cell) + 3
        origin = np.array([x - n * cell / 2, sand_top(x, z) - 2.0, z - n * cell / 2])
        idx = np.indices((n, n, n)).reshape(3, -1).T
        p = origin + (idx + 0.5) * cell
        d = ellipsoid_sdf(p, (x, sand_top(x, z) + r * 0.25, z), (r * 1.1, r * 0.75, r))
        d += 2.0 * (value_noise3(p, 4.0, 20 + k) - 0.5)
        solid = (d < 0) & (p[:, 1] > origin[1])
        voxel_object(tank, "Rock", origin, cell, solid.reshape(n, n, n), ROCK, seed=30 + k, noise_cell=4.0)


def build_castle(tank):
    """Mini castle: hollow keep with doors on two sides and windows on the other two, corner towers."""
    cx, cy, cz = CASTLE_CENTRE
    # stand on the lowest sand tile under the footprint, so no wall floats
    cy = min(sand_top(cx + dx, cz + dz) for dx in (-26.0, 0.0, 26.0) for dz in (-26.0, 0.0, 26.0)) - 1.0
    side, height, thick = 46.0, 32.0, 3.0
    h = side / 2
    door = (h - 7.0, h + 7.0, 0.0, 17.0)
    windows = [(7.0, 17.0, 12.0, 22.0), (side - 17.0, side - 7.0, 12.0, 22.0)]
    walls = [
        ((cx - h, cy, cz - h), (1, 0, 0), (0, 0, 1), windows),
        ((cx + h, cy, cz + h), (-1, 0, 0), (0, 0, -1), windows),
        ((cx + h, cy, cz - h), (0, 0, 1), (-1, 0, 0), [door]),
        ((cx - h, cy, cz + h), (0, 0, -1), (1, 0, 0), [door]),
    ]
    for start, d, inward, openings in walls:
        wall_with_openings(tank, "Castle", start, d, side, height, thick, openings, CASTLE_STONE[0], inward,
                           shades=CASTLE_STONE)
        # battlements
        dd = norm(d)
        n = norm(inward)
        for k in range(int(side // 4)):
            u = 2.0 + k * 4.0
            if 1.0 < u < side - 1.0 and k % 2 == 0:
                c = add(add(start, mul(dd, u)), (0.0, height + 1.25, 0.0))
                c = add(c, mul(n, thick / 2))
                tank.prim("Castle", "Block", (2.2, 2.5, thick), c, from_axes(dd, (0, 1, 0), cross(dd, (0, 1, 0))),
                          CASTLE_STONE[k % 3])
        # rounded top corners in each door: a wedge whose right angle sits where the jamb meets the lintel
        for o in openings:
            if o[2] == 0.0:
                for s in (-1, 1):
                    jamb_u = o[1] if s > 0 else o[0]
                    c = add(add(start, mul(dd, jamb_u - s * 1.5)), (0.0, o[3] - 1.5, 0.0))
                    c = add(c, mul(n, thick / 2))
                    y_axis = (0.0, -1.0, 0.0)                  # the wedge's full bottom face against the lintel
                    z_axis = mul(dd, s)                        # its full back face against the jamb
                    rot = from_axes(cross(y_axis, z_axis), y_axis, z_axis)
                    tank.prim("Castle", "Wedge", (thick, 3.0, 3.0), c, rot, CASTLE_STONE[1])
    # corner towers with battlements and stepped conical roofs
    for k, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        tx, tz = cx + sx * h, cz + sz * h
        top = cy + height + 10.0
        tank.cylinder("Tower", (tx, cy, tz), (tx, top, tz), 14.0, CASTLE_STONE[1], "Stud")
        tank.cylinder("Tower", (tx, top, tz), (tx, top + 1.4, tz), 15.6, CASTLE_STONE[2], "Stud")
        for m in range(8):
            a = m * math.pi / 4
            tank.prim("Tower", "Block", (2.4, 2.8, 2.4), (tx + math.cos(a) * 6.8, top + 2.8, tz + math.sin(a) * 6.8),
                      rot_y(-a), CASTLE_STONE[m % 3])
        roof = ROOF_RED if k % 2 == 0 else ROOF_BLUE
        for j, (dia, hh) in enumerate(((12.6, 3.0), (9.4, 3.0), (6.2, 3.0), (3.0, 3.0))):
            y0 = top + 1.4 + j * hh
            tank.cylinder("Roof", (tx, y0, tz), (tx, y0 + hh, tz), dia, shade(roof, 1.0 + 0.05 * j), "Stud")
        tank.prim("Roof", "Ball", (1.8, 1.8, 1.8), (tx, top + 1.4 + 4 * 3.0 + 0.6, tz), IDENT, (255, 214, 60), "Smooth")
        tank.cylinder("Flag", (tx, top + 13.0, tz), (tx, top + 18.0, tz), 0.5, (90, 70, 50), "Wood", collide=False)
        tank.prim("Flag", "Block", (3.6, 2.2, 0.2), (tx + 1.9, top + 17.0, tz), IDENT, (255, 214, 60), "Smooth",
                  collide=False)


def build_driftwood(tank, rng):
    pieces = [((60.0, -70.0), 0.4), ((-128.0, -40.0), 1.0), ((128.0, 30.0), 1.4)]   # clear of the rock's tunnel mouths
    for k, ((x, z), yaw) in enumerate(pieces):
        r = random.Random(400 + k)
        base = (x, sand_top(x, z) + 1.0, z)
        d = (math.sin(yaw), 0.35, math.cos(yaw))
        main_end = add(base, mul(norm(d), 26))
        tank.beam("Wood", base, main_end, 3.2, 2.8, (118, 82, 52), "Wood")
        for j in range(4):
            t = 0.3 + 0.18 * j
            p = add(base, mul(sub(main_end, base), t))
            side = 1 if j % 2 else -1
            br = add(p, (side * r.uniform(5, 9) * math.cos(yaw), r.uniform(4, 9), -side * r.uniform(5, 9) * math.sin(yaw)))
            tank.beam("Wood", p, br, 1.6, 1.4, (132, 92, 58) if j % 2 else (104, 72, 46), "Wood")


def build_chest(tank):
    x, z = CHEST
    y = sand_top(x, z)
    rot = rot_y(0.5)

    def part(shape, size, local, color, mat="Wood", collide=True):
        tank.prim("Chest", shape, size, add((x, y, z), apply(rot, local)), rot, color, mat, collide=collide)

    part("Block", (10.0, 5.0, 6.0), (0, 2.5, 0), (132, 82, 44))
    for dx in (-4.2, 0.0, 4.2):
        part("Block", (1.0, 5.2, 6.2), (dx, 2.6, 0), (232, 184, 66), "Metal")
    part("Block", (10.4, 0.8, 6.4), (0, 5.2, 0), (232, 184, 66), "Metal")
    # open lid tilted back, coins heaped inside
    tank.prim("Chest", "Block", (10.0, 3.0, 1.2), add((x, y, z), apply(rot, (0, 7.4, 3.6))), matmul(rot, rot_x(math.radians(-20))),
              (120, 74, 40), "Wood")
    part("Block", (8.8, 1.2, 4.8), (0, 5.4, 0), (255, 214, 60), "Neon", collide=False)
    for k in range(6):
        a = k * 1.1
        part("Cylinder", (0.3, 1.4, 1.4), (math.cos(a) * 3.2, 6.1 + 0.2 * (k % 2), math.sin(a) * 1.6),
             (255, 220, 80), "Metal", collide=False)
    part("Ball", (1.6, 1.6, 1.6), (2.0, 6.4, -0.6), (230, 40, 80), "Smooth", collide=False)


def build_bubbler(tank):
    x, z = 150.0, 114.0
    y = sand_top(x, z)
    tank.prim("Bubbler", "Block", (4.0, 2.0, 4.0), (x, y + 1.0, z), IDENT, (110, 116, 128), "Stud")
    for k in range(12):
        s = 1.0 + 0.25 * (k % 3)
        tank.prim("Bubbles", "Ball", (s, s, s), (x + math.sin(k * 1.7) * 1.2, y + 4.0 + k * 7.0, z + math.cos(k * 2.3) * 1.2),
                  IDENT, (235, 250, 255), "Glass", transparency=0.35, collide=False)


def seaweed_spots(rng, tunnels):
    """About twenty clumps on the sand, away from the rock's doors, the castle and the chest."""
    out = []
    tries = 0
    while len(out) < 22 and tries < 2000:
        tries += 1
        x = rng.uniform(-HALF_X + 10, HALF_X - 10)
        z = rng.uniform(-HALF_Z + 10, HALF_Z - 10)
        if math.hypot(x - ROCK_CENTRE[0], z - ROCK_CENTRE[2]) < 62:
            continue
        if abs(x - CASTLE_CENTRE[0]) < 40 and abs(z - CASTLE_CENTRE[2]) < 40:
            continue
        if math.hypot(x - ARCH_CENTRE[0], z - ARCH_CENTRE[2]) < 34:
            continue
        if math.hypot(x - CHEST[0], z - CHEST[1]) < 14:
            continue
        if any(math.hypot(x - s["pos"][0], z - s["pos"][2]) < 26 for s in out):
            continue
        y = sand_top(x, z)
        out.append(spot((x, y, z), rot_y(rng.uniform(0, 2 * math.pi)), height=round(rng.uniform(24, 52), 1)))
    return out


def pod_ring_spots():
    """Ten pods outside the glass at rim height, each looking at the tank centre."""
    gap = POD_RADIUS + POD_RAMP + 2.0          # the ramp lip stops 2 studs short of the glass
    long_z = HALF_Z + GLASS_T + gap
    short_x = HALF_X + GLASS_T + gap
    places = [(x, long_z) for x in (-100.0, 0.0, 100.0)] + [(x, -long_z) for x in (-100.0, 0.0, 100.0)]
    places += [(short_x, z) for z in (-60.0, 60.0)] + [(-short_x, z) for z in (-60.0, 60.0)]
    # each pod looks at the centre of the tank (flat), its ramp pointing at the glass
    return [spot((x, RIM_TOP, z), look_rot((-x, 0.0, -z))) for x, z in places]


def build_aquarium(cut_z=None):
    rng = random.Random(2026)
    tank = Asset("Aquarium")
    build_glass(tank)
    build_cabinet(tank, rng)
    build_sand(tank, rng)
    tunnels = build_rock(tank, cut_z)
    build_small_rocks(tank, rng)
    build_castle(tank)
    build_rock_arch(tank)
    build_amphora(tank)
    build_driftwood(tank, rng)
    build_chest(tank)
    build_bubbler(tank)
    spots = {
        "v": 1,
        "map": "Aquarium",
        "water": {"shape": "Box", "min": [-HALF_X, sand_height(0, 0), -HALF_Z], "max": [HALF_X, WATER_LEVEL, HALF_Z],
                  "surfaceY": WATER_LEVEL, "glassInner": [-HALF_X, FLOOR_Y, -HALF_Z, HALF_X, GLASS_TOP, HALF_Z]},
        "FishermanSpots": pod_ring_spots(),
        "SeaweedSpots": seaweed_spots(random.Random(77), tunnels),
        "PlayerSpawnVolume": {"center": [0.0, -40.0, 0.0], "size": [300.0, 60.0, 228.0]},
        "PlayerSpawnPoints": clear_points(tank.prims, lambda r: (r.uniform(-150, 150), r.uniform(-70, -10), r.uniform(-114, 114)),
                                          24, 6.0, 91),
        "Tunnels": [{"from": [round(v, 2) for v in a], "to": [round(v, 2) for v in b], "radius": r} for a, b, r in tunnels],
        "Castle": {"center": list(CASTLE_CENTRE), "size": [46.0, 32.0, 46.0]},
        "Arch": {"center": list(ARCH_CENTRE), "span": 42.0},
    }
    return tank, spots


# =========================================================================================== BALLON
BALL_RADIUS = 110.0
BALL_CENTRE = (0.0, 0.0, 0.0)
POD_LOWEST = -6.2          # the pod's hover cone tip, below its floor


def build_hover_platform():
    """Small floating platform under a pod: hexagonal metal plate with glowing edges and thrusters.
    Local origin = the pod's floor centre (the platform's top sits just under the pod's hover cone)."""
    plat = Asset("HoverPlatform")
    top = POD_LOWEST - 0.2
    R = 11.0
    apothem = R * math.sqrt(3) / 2
    for k in range(3):
        rot = rot_y(k * math.pi / 3)
        plat.prim("Platform", "Block", (R, 2.0, 2 * apothem), (0, top - 1.0, 0), rot, METAL_DARK, "Metal")
    corners = [(math.cos(k * math.pi / 3) * R, math.sin(k * math.pi / 3) * R) for k in range(6)]
    for k in range(6):
        (x0, z0), (x1, z1) = corners[k], corners[(k + 1) % 6]
        plat.beam("Neon", (x0, top - 0.1, z0), (x1, top - 0.1, z1), 0.5, 0.3, CYAN, "Neon", collide=False)
    for k, (d, y0, y1) in enumerate(((16.0, top - 3.2, top - 2.0), (10.0, top - 4.6, top - 3.2), (5.0, top - 5.8, top - 4.6))):
        plat.cylinder("Platform", (0, y0, 0), (0, y1, 0), d, METAL if k == 1 else METAL_DARK, "Metal")
    plat.cylinder("Neon", (0, top - 6.4, 0), (0, top - 5.8, 0), 3.0, CYAN, "Neon", collide=False)
    for k in range(3):
        a = k * 2 * math.pi / 3 + math.pi / 6
        c = (math.cos(a) * 7.0, 0.0, math.sin(a) * 7.0)
        plat.cylinder("Platform", add(c, (0, top - 3.4, 0)), add(c, (0, top - 2.0, 0)), 2.6, METAL, "Metal")
        plat.cylinder("Neon", add(c, (0, top - 3.9, 0)), add(c, (0, top - 3.4, 0)), 2.0, CYAN, "Neon", collide=False)
    return plat


def ballon_pod_frames():
    """Ten pods around the ball, at different heights; each ramp lip ends ~8 studs from the water.
    Returns exact (position, rotation, latitude) triples."""
    lats = [8, 24, -4, 32, 14, 2, 28, 18, -2, 20]
    out = []
    reach = POD_RADIUS + POD_RAMP          # floor centre -> ramp lip
    for k, lat in enumerate(lats):
        lon = math.radians(k * 36 + 9 * (k % 2))
        y = BALL_RADIUS * math.sin(math.radians(lat)) + 2.0
        rho = reach + math.sqrt((BALL_RADIUS + 8.0) ** 2 - y * y)
        pos = (math.cos(lon) * rho, y, math.sin(lon) * rho)
        look = (-math.cos(lon), 0.0, -math.sin(lon))
        out.append((pos, look_rot(look), lat))
    return out


def ball_sample(rng):
    """A random point well inside the ball (uniform in volume, radius <= 88)."""
    while True:
        p = (rng.uniform(-88, 88), rng.uniform(-88, 88), rng.uniform(-88, 88))
        if length(p) <= 88.0:
            return add(BALL_CENTRE, p)


def build_ballon():
    frames = ballon_pod_frames()
    spots_list = [spot(pos, rot, lat=lat) for pos, rot, lat in frames]
    plat = build_hover_platform()
    layout = Asset("BallonPlatforms")
    for pos, rot, _ in frames:
        layout.place(plat, pos, rot)
    half = BALL_RADIUS / math.sqrt(3) - 8.0
    spots = {
        "v": 1,
        "map": "Ballon",
        "water": {"shape": "Sphere", "center": list(BALL_CENTRE), "radius": BALL_RADIUS},
        "FishermanSpots": spots_list,
        "SeaweedSpots": [],
        "PlayerSpawnVolume": {"center": list(BALL_CENTRE), "size": [round(2 * half, 2)] * 3},
        "PlayerSpawnSphere": {"center": list(BALL_CENTRE), "radius": 88.0},
        "PlayerSpawnPoints": clear_points([], ball_sample, 24, 0.0, 92),
        "ClientAttributes": {"MapWaterShape": "Sphere", "MapWaterCenter": list(BALL_CENTRE), "MapWaterRadius": BALL_RADIUS},
    }
    return layout, spots


# =========================================================================================== FISHING BOAT
HULL_WHITE = (242, 242, 236)
HULL_BLUE = (40, 96, 176)
HULL_RED = (188, 46, 42)
DECK_WOOD = ((178, 128, 80), (166, 118, 72), (186, 136, 88))
BOOM_YELLOW = (244, 192, 44)
NET_GREEN = (44, 142, 112)
BUOY = (255, 122, 32)
TIRE = (38, 38, 42)
BOAT_LENGTH, BOAT_BEAM = 26.0, 10.0
BOAT_DECK = 1.8


def boat_width(z):
    """Hull width at z (bow at -13, flat transom at +13)."""
    if z < -3.0:
        t = (-3.0 - z) / 10.0
        return max(1.4, BOAT_BEAM * (1 - t ** 1.7))
    return BOAT_BEAM - 1.0 * max(0.0, (z - 9.0) / 4.0)


def build_fishing_boat():
    """Small fishing boat, about 26 x 10 studs. Local origin on the waterline, centre of the hull; bow to -Z."""
    boat = Asset("FishingBoat")
    half_l = BOAT_LENGTH / 2
    # hull: sections along z, 1 stud at the bow, 2 studs elsewhere; red bottom, white sides, blue band
    zs = [-half_l + k for k in range(11)] + [-2.0 + 2 * k for k in range(8)]
    layers = [(-2.0, -1.0, HULL_RED, 0.62), (-1.0, 0.0, HULL_RED, 0.88), (0.0, 1.3, HULL_WHITE, 1.0),
              (1.3, BOAT_DECK + 0.2, HULL_BLUE, 1.0)]
    for z0, z1 in zip(zs[:-1], zs[1:]):
        w = boat_width((z0 + z1) / 2)
        for y0, y1, color, k in layers:
            boat.box("Hull", (-w * k / 2, y0, z0), (w * k / 2, y1, z1), color, "Smooth")
        # bulwarks along both sides, capped with blue
        if z0 >= -10.0:
            for s in (-1, 1):
                x = s * (w / 2 - 0.25)
                boat.box("Hull", (x - 0.25, BOAT_DECK + 0.2, z0), (x + 0.25, BOAT_DECK + 1.2, z1), HULL_WHITE, "Smooth")
                boat.box("Trim", (x - 0.35, BOAT_DECK + 1.2, z0), (x + 0.35, BOAT_DECK + 1.45, z1), HULL_BLUE, "Smooth")
    # transom and name board
    boat.box("Hull", (-4.6, -1.0, half_l - 0.4), (4.6, BOAT_DECK + 1.2, half_l), HULL_WHITE, "Smooth")
    boat.box("Trim", (-2.6, 0.2, half_l), (2.6, 1.1, half_l + 0.1), HULL_BLUE, "Smooth", collide=False)
    # deck planks
    for k, x0 in enumerate([-4.2 + 1.4 * i for i in range(6)]):
        boat.box("Deck", (x0, BOAT_DECK - 0.1, -8.0), (x0 + 1.4, BOAT_DECK + 0.2, half_l - 0.4), DECK_WOOD[k % 3], "Wood")
    boat.box("Deck", (-1.6, BOAT_DECK - 0.1, -11.0), (1.6, BOAT_DECK + 0.2, -8.0), DECK_WOOD[1], "Wood")

    # wheelhouse with windows all round and a door at the back
    cab_lo, cab_hi = (-3.4, BOAT_DECK + 0.2, -6.4), (3.4, BOAT_DECK + 5.0, 0.0)
    h = cab_hi[1] - cab_lo[1]
    win = [(1.0, 3.0, 2.0, 4.0), (3.8, 5.8, 2.0, 4.0)]
    wall_with_openings(boat, "Cabin", (cab_lo[0], cab_lo[1], cab_lo[2]), (1, 0, 0), 6.8, h, 0.4, win, HULL_WHITE, (0, 0, 1),
                       "Smooth")
    wall_with_openings(boat, "Cabin", (cab_hi[0], cab_lo[1], cab_hi[2]), (-1, 0, 0), 6.8, h, 0.4, [(2.4, 4.4, 0.0, 3.8)],
                       HULL_WHITE, (0, 0, -1), "Smooth")
    for s in (-1, 1):
        start = (s * 3.4, cab_lo[1], cab_lo[2] if s > 0 else cab_hi[2])
        d = (0, 0, 1) if s > 0 else (0, 0, -1)
        wall_with_openings(boat, "Cabin", start, d, 6.4, h, 0.4, [(1.4, 4.6, 2.0, 4.0)], HULL_WHITE, (-s, 0, 0), "Smooth")
    for (x0, x1) in ((-2.4, -0.4), (0.4, 2.4)):
        boat.box("Glass", (x0, cab_lo[1] + 2.0, cab_lo[2] + 0.1), (x1, cab_lo[1] + 4.0, cab_lo[2] + 0.3), (170, 220, 255),
                 "Glass", transparency=0.35)
    for s in (-1, 1):
        boat.box("Glass", (s * 3.4 - 0.1, cab_lo[1] + 2.0, -5.0), (s * 3.4 + 0.1, cab_lo[1] + 4.0, -1.8), (170, 220, 255),
                 "Glass", transparency=0.35)
    boat.box("Cabin", (-4.0, cab_hi[1], -6.9), (4.0, cab_hi[1] + 0.6, 0.6), HULL_BLUE, "Smooth")
    boat.box("Cabin", (-3.6, cab_lo[1] - 0.1, -6.6), (3.6, cab_lo[1] + 0.4, 0.2), HULL_BLUE, "Smooth")
    # roof gear: antenna, radar, searchlight, navigation lights (red to port, green to starboard)
    roof = cab_hi[1] + 0.6
    boat.cylinder("Gear", (0.8, roof, -2.0), (0.8, roof + 4.5, -2.0), 0.3, (220, 220, 225), "Metal", collide=False)
    boat.box("Gear", (-1.8, roof, -4.0), (-0.4, roof + 0.8, -2.6), (60, 64, 72), "Metal", collide=False)
    boat.prim("Gear", "Block", (3.0, 0.3, 0.6), (-1.1, roof + 1.2, -3.3), IDENT, (230, 230, 235), "Metal", collide=False)
    boat.prim("Gear", "Ball", (1.0, 1.0, 1.0), (2.4, roof + 0.6, -6.0), IDENT, (255, 248, 200), "Neon", collide=False)
    boat.prim("Gear", "Block", (0.5, 0.5, 0.5), (-4.0, roof - 0.3, -4.0), IDENT, (255, 40, 40), "Neon", collide=False)
    boat.prim("Gear", "Block", (0.5, 0.5, 0.5), (4.0, roof - 0.3, -4.0), IDENT, (40, 255, 90), "Neon", collide=False)
    # life ring on the starboard wall
    ring_c = (3.65, cab_lo[1] + 2.6, -0.9)
    boat.cylinder("Gear", sub(ring_c, (0.15, 0, 0)), add(ring_c, (0.15, 0, 0)), 2.2, (250, 250, 250), "Smooth", collide=False)
    boat.cylinder("Gear", sub(ring_c, (0.2, 0, 0)), add(ring_c, (0.2, 0, 0)), 1.0, (200, 60, 60), "Smooth", collide=False)

    # mast and fishing boom
    mast_base = (0.0, BOAT_DECK + 0.2, 1.4)
    boat.cylinder("Mast", mast_base, (0.0, 14.0, 1.4), 0.7, HULL_WHITE, "Metal")
    boat.cylinder("Mast", (-2.4, 11.0, 1.4), (2.4, 11.0, 1.4), 0.35, HULL_WHITE, "Metal")
    boom_root, boom_tip = (0.4, 8.0, 1.8), (5.8, 11.0, 7.0)
    boat.cylinder("Boom", boom_root, boom_tip, 0.55, BOOM_YELLOW, "Metal")
    boat.cylinder("Boom", add(boom_tip, (-0.3, 0, 0)), add(boom_tip, (0.3, 0, 0)), 1.0, (60, 60, 66), "Metal", collide=False)
    boat.beam("Rope", (0.0, 14.0, 1.4), boom_tip, 0.12, 0.12, (70, 56, 40), "Smooth", collide=False)
    boat.beam("Rope", boom_tip, (5.8, 6.2, 7.0), 0.12, 0.12, (70, 56, 40), "Smooth", collide=False)
    # net bag hanging from the boom
    for k, (w, y) in enumerate(((1.6, 5.6), (2.2, 4.8), (2.0, 4.0), (1.2, 3.4))):
        boat.box("Net", (5.8 - w / 2, y - 0.4, 7.0 - w / 2), (5.8 + w / 2, y + 0.4, 7.0 + w / 2), shade(NET_GREEN, 0.9 + 0.06 * k),
                 "Smooth", transparency=0.15, collide=False)
    # net pile, crates, fish boxes and a marker buoy on the deck
    for k, (x, z, w, d, hh) in enumerate(((-2.2, 4.2, 3.0, 2.6, 0.7), (-2.0, 4.6, 2.2, 1.8, 1.2), (-2.6, 3.8, 1.6, 1.4, 1.6))):
        boat.box("Net", (x - w / 2, BOAT_DECK + 0.2, z - d / 2), (x + w / 2, BOAT_DECK + 0.2 + hh, z + d / 2),
                 shade(NET_GREEN, 1.0 + 0.05 * k), "Smooth", collide=False)
    for k, (x, z, s) in enumerate(((2.6, 3.6, 1.6), (2.6, 5.4, 1.6), (2.7, 4.5, 1.2))):
        y0 = BOAT_DECK + 0.2 + (1.6 if k == 2 else 0.0)
        boat.box("Cargo", (x - s / 2, y0, z - s / 2), (x + s / 2, y0 + s, z + s / 2), DECK_WOOD[k % 3], "Wood")
        boat.box("Cargo", (x - s / 2 - 0.05, y0 + s * 0.45, z - s / 2 - 0.05), (x + s / 2 + 0.05, y0 + s * 0.55, z + s / 2 + 0.05),
                 (120, 84, 50), "Wood", collide=False)
    for k, z in enumerate((-7.0, -8.4)):
        boat.box("Cargo", (-1.4, BOAT_DECK + 0.2, z - 0.6), (1.4, BOAT_DECK + 1.0, z + 0.6), (52, 122, 210), "Smooth")
        boat.box("Cargo", (-1.2, BOAT_DECK + 0.9, z - 0.45), (1.2, BOAT_DECK + 1.05, z + 0.45), (200, 220, 235), "Smooth",
                 collide=False)
    boat.prim("Buoy", "Ball", (1.6, 1.6, 1.6), (-3.2, BOAT_DECK + 1.0, 7.4), IDENT, BUOY, "Smooth")
    boat.cylinder("Buoy", (-3.2, BOAT_DECK + 1.6, 7.4), (-3.2, BOAT_DECK + 4.2, 7.4), 0.2, (60, 60, 60), "Metal", collide=False)
    boat.box("Buoy", (-3.1, BOAT_DECK + 3.2, 7.35), (-1.9, BOAT_DECK + 4.0, 7.45), (240, 60, 60), "Smooth", collide=False)
    # buoys and tyres hanging over the sides
    for s in (-1, 1):
        for k, z in enumerate((-4.0, 1.0, 6.0)):
            w = boat_width(z) / 2
            c = (s * (w + 0.55), 0.9, z)
            boat.cylinder("Tyre", sub(c, (0.45, 0, 0)), add(c, (0.45, 0, 0)), 2.4, TIRE, "Smooth", collide=False)
            boat.cylinder("Tyre", sub(c, (0.5, 0, 0)), add(c, (0.5, 0, 0)), 1.0, (20, 20, 22), "Smooth", collide=False)
            boat.beam("Rope", (s * (w - 0.2), BOAT_DECK + 1.4, z), add(c, (0, 1.1, 0)), 0.1, 0.1, (70, 56, 40), "Smooth",
                      collide=False)
        boat.prim("Buoy", "Ball", (1.4, 1.4, 1.4), (s * (boat_width(-7.5) / 2 + 0.6), 1.4, -7.5), IDENT, BUOY, "Smooth",
                  collide=False)

    # raised fishing platform at the stern, with steps and a rail; the fisherman stands on it
    plat_y = BOAT_DECK + 2.8
    boat.box("Platform", (-3.4, BOAT_DECK + 0.2, 8.6), (3.4, plat_y, 12.4), DECK_WOOD[2], "Wood")
    for k in range(3):
        y1 = BOAT_DECK + 0.2 + (k + 1) * 0.9
        boat.box("Platform", (-1.4, BOAT_DECK + 0.2, 8.6 - (3 - k) * 0.9), (1.4, y1, 8.6 - (2 - k) * 0.9), DECK_WOOD[k % 3],
                 "Wood")
    for x, z in ((-3.2, 12.2), (3.2, 12.2), (-3.2, 8.8), (3.2, 8.8), (0.0, 12.2)):
        boat.cylinder("Rail", (x, plat_y, z), (x, plat_y + 2.2, z), 0.25, (220, 220, 225), "Metal", collide=False)
    boat.beam("Rail", (-3.2, plat_y + 2.2, 12.2), (3.2, plat_y + 2.2, 12.2), 0.25, 0.25, (220, 220, 225), "Metal", collide=False)
    for s in (-1, 1):
        boat.beam("Rail", (s * 3.2, plat_y + 2.2, 8.8), (s * 3.2, plat_y + 2.2, 12.2), 0.25, 0.25, (220, 220, 225), "Metal",
                  collide=False)
    boat.cylinder("Gear", (2.6, plat_y, 11.6), (2.6, plat_y + 1.2, 11.6), 0.9, (60, 60, 70), "Metal", collide=False)
    return boat


def boat_fisherman_stand():
    """Where the fisherman stands on the boat (local): top of the stern platform, facing the bow (-Z)."""
    return (0.0, BOAT_DECK + 2.8, 10.6), IDENT


def boat_local_spots(boat):
    pos, rot = boat_fisherman_stand()
    return {"v": 1, "model": "FishingBoat", "origin": "waterline, centre of the hull; bow towards -Z",
            "length": BOAT_LENGTH, "beam": BOAT_BEAM, "primitives": len(boat.prims),
            "FishermanStand": spot(pos, rot)}


# =========================================================================================== ISLAND
def build_island():
    """Small unreachable sand islet (~30 studs) with a tropical palm. Local origin on the waterline."""
    isl = Asset("Island")
    cell = 2.0
    n = 18
    origin = np.array([-n * cell / 2, -8.0, -n * cell / 2])
    ny = 7
    idx = np.indices((n, ny, n)).reshape(3, -1).T
    p = origin + (idx + 0.5) * cell
    r = np.hypot(p[:, 0], p[:, 2])
    wobble = 2.0 * (value_noise3(np.column_stack([p[:, 0], np.zeros(len(p)), p[:, 2]]), 6.0, 5) - 0.5)
    top = 4.2 * (1 - np.clip((r + wobble) / 15.5, 0, 1.4) ** 2) - 0.6
    solid = (p[:, 1] < top).reshape(n, ny, n)
    labels = np.zeros(solid.shape, np.int32)
    ys = (origin[1] + (np.arange(ny) + 0.5) * cell)
    for j, y in enumerate(ys):
        k = 1 if y < -0.5 else (2 if y < 1.0 else 3)          # wet sand, damp sand, dry sand
        labels[:, j, :][solid[:, j, :]] = k
    palette = [(196, 168, 118), (214, 188, 136), (238, 214, 160)]
    for x0, y0, z0, x1, y1, z1, k in merge_boxes(labels):
        lo = origin + np.array([x0, y0, z0]) * cell
        hi = origin + np.array([x1, y1, z1]) * cell
        isl.box("Sand", tuple(lo), tuple(hi), palette[k - 1], "Stud")
    rng = random.Random(8)
    for _ in range(5):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(9, 13)
        s = rng.uniform(1.6, 2.8)
        isl.prim("Rock", "Block", (s, s * 0.8, s), (math.cos(a) * rr, 0.6, math.sin(a) * rr), rot_y(a), (150, 146, 140), "Stud")
    for _ in range(6):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(2, 6)
        isl.prim("Grass", "Block", (1.2, rng.uniform(1.0, 2.0), 1.2), (math.cos(a) * rr + 1.0, 3.6, math.sin(a) * rr),
                 rot_y(a), (88, 176, 64), "Smooth", collide=False)
    # palm: a curved, ringed trunk leaning out, coconuts and drooping fronds
    base = (1.0, 2.6, 0.5)
    pts = []
    for k in range(10):
        t = k / 9
        pts.append((base[0] + 5.5 * t * t, base[1] + 17.0 * t, base[2] - 1.5 * t * t))
    for k in range(9):
        w = 1.9 - 0.06 * k
        isl.beam("Trunk", pts[k], pts[k + 1], w, w, (150, 110, 70) if k % 2 == 0 else (128, 92, 58), "Wood")
    crown = pts[-1]
    for k in range(3):
        a = k * 2.1
        isl.prim("Coconut", "Ball", (1.3, 1.3, 1.3), add(crown, (math.cos(a) * 0.9, -0.9, math.sin(a) * 0.9)), IDENT,
                 (110, 74, 40), "Smooth")
    greens = [(52, 150, 58), (70, 172, 64), (94, 192, 72)]
    for f in range(8):
        a = f * math.pi / 4 + 0.2
        d = (math.cos(a), 0.0, math.sin(a))
        prev = add(crown, (0, 0.4, 0))
        for j in range(5):
            out = 2.4 * (j + 1)
            droop = 0.9 * j * j * 0.45 - 0.6 * j + 0.2
            nxt = add(crown, (d[0] * out, 0.6 - droop, d[2] * out))
            width = 2.6 - 0.35 * j
            side = cross(d, (0, 1, 0))
            isl.beam("Frond", prev, nxt, width, 0.3, greens[(f + j) % 3], "Smooth", collide=False,
                     up=add((0, 1, 0), mul(side, 0.0)))
            prev = nxt
    return isl


# =========================================================================================== OCEAN
OCEAN_HALF = 600.0
ARENA_HALF = (150.0, 120.0)        # playable rectangle: 300 x 240
ZONE_BOTTOM, ZONE_TOP = -60.0, 40.0
OCEAN_BED = -46.0
ISLAND_AT = (200.0, WATER_LEVEL, -470.0)


def ocean_boat_frames():
    """Ten boats just outside the arena: bow 3 studs outside the zone wall, heading for the centre.
    Returns exact (position, rotation) pairs (the boat's waterline origin)."""
    gap = BOAT_LENGTH / 2 + 3.0
    hx, hz = ARENA_HALF
    places = [(x, hz + gap) for x in (-95.0, 0.0, 95.0)] + [(x, -hz - gap) for x in (-95.0, 0.0, 95.0)]
    places += [(hx + gap, z) for z in (-55.0, 55.0)] + [(-hx - gap, z) for z in (-55.0, 55.0)]
    # heading for the centre of the arena
    return [((x, WATER_LEVEL, z), look_rot((-x, 0.0, -z))) for x, z in places]


def build_ocean_layout():
    """Ocean map anchors, plus the zone wall as four translucent panels (the local session puts the texture on)."""
    layout = Asset("OceanZone")
    hx, hz = ARENA_HALF
    t = 1.0
    h = ZONE_TOP - ZONE_BOTTOM
    yc = (ZONE_TOP + ZONE_BOTTOM) / 2
    wall = dict(mat="ForceField", transparency=0.35)
    layout.prim("ZoneWall", "Block", (2 * hx + 2 * t, h, t), (0, yc, -hz - t / 2), IDENT, (120, 90, 255), **wall)
    layout.prim("ZoneWall", "Block", (2 * hx + 2 * t, h, t), (0, yc, hz + t / 2), IDENT, (120, 90, 255), **wall)
    layout.prim("ZoneWall", "Block", (t, h, 2 * hz), (-hx - t / 2, yc, 0), IDENT, (120, 90, 255), **wall)
    layout.prim("ZoneWall", "Block", (t, h, 2 * hz), (hx + t / 2, yc, 0), IDENT, (120, 90, 255), **wall)
    frames = ocean_boat_frames()
    boats = [spot(pos, rot) for pos, rot in frames]
    stand_pos, stand_rot = boat_fisherman_stand()
    fishermen = [spot(add(pos, apply(rot, stand_pos)), matmul(rot, stand_rot)) for pos, rot in frames]
    spots = {
        "v": 1,
        "map": "Ocean",
        "water": {"shape": "Box", "min": [-OCEAN_HALF, OCEAN_BED, -OCEAN_HALF], "max": [OCEAN_HALF, WATER_LEVEL, OCEAN_HALF],
                  "surfaceY": WATER_LEVEL},
        "Arena": {"center": [0.0, WATER_LEVEL, 0.0], "size": [2 * hx, 2 * hz]},
        "ZoneWall": {"bottom": ZONE_BOTTOM, "top": ZONE_TOP, "thickness": t,
                     "note": "texture fx/zone_wall_*.png, opaque at the bottom, fading towards the top"},
        "BoatSpots": boats,
        "FishermanSpots": fishermen,
        "IslandSpot": spot(ISLAND_AT, rot_y(0.6)),
        "SeaweedSpots": [],
        "PlayerSpawnVolume": {"center": [0.0, (OCEAN_BED + WATER_LEVEL) / 2, 0.0],
                              "size": [2 * hx - 20.0, -OCEAN_BED - 12.0, 2 * hz - 20.0]},
        "PlayerSpawnPoints": clear_points(layout.prims, lambda r: (r.uniform(-hx + 12, hx - 12), r.uniform(OCEAN_BED + 8, -6),
                                                                   r.uniform(-hz + 12, hz - 12)), 24, 6.0, 93),
    }
    return layout, spots
