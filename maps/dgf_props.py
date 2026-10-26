"""Don't Get Fished - second batch of props (brief 2): Ocean decor (megalodon fossil, corals, decor spots) and the
weapons of the new fishermen (harpoon gun, harpoon, bazooka, missile).

Same conventions and table format as dgf_maps.py (Roblox studs, Y up, primitives as dicts, export_table).
Deterministic: every random draw uses a fixed seed.
"""
import math
import random

import numpy as np

from dgf_maps import (IDENT, Asset, add, apply, axis_x_rot, cross, dot, from_axes, length, lerp, look_rot, matmul,
                      mix, mul, norm, rot_x, rot_y, shade, spot, sub)

UP = (0.0, 1.0, 0.0)


# --------------------------------------------------------------------------------- small builders
def tooth(asset, group, base, up, along, height, width, thick, color, collide=False):
    """Isosceles triangle tooth from two mirrored wedges: base centre `base`, pointing along `up`, its base edge
    running along `along` (the jaw line). Roblox wedges keep their tall leg on their back (+Z) face."""
    up, along = norm(up), norm(along)
    out = []
    for side in (1, -1):
        back = mul(along, side)                       # the tall leg faces the tooth's centre line
        rot = from_axes(norm(cross(up, back)), up, back)
        centre = add(add(base, mul(along, -side * width / 4)), mul(up, height / 2))
        out.append(asset.prim(group, "Wedge", (thick, height, width / 2), centre, rot, color, "Smooth", collide=collide))
    return out


def chain(asset, group, points, diameters, color, mat="Smooth", collide=False, overlap=0.0):
    """Tapered tube along a polyline, one cylinder per segment (ends extended by `overlap` to hide the joints)."""
    out = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        d = norm(sub(b, a))
        a2, b2 = sub(a, mul(d, overlap)), add(b, mul(d, overlap))
        dia = (diameters[i] + diameters[i + 1]) / 2
        out.append(asset.cylinder(group, a2, b2, dia, color, mat, collide=collide))
    return out


def cap(asset, group, x, z, radius, height, color, y0=0.0):
    """Spherical cap mound standing `height` above y0 (a ball sunk into the floor)."""
    return asset.prim(group, "Ball", (2 * radius,) * 3, (x, y0 + height - radius, z), IDENT, color, "Smooth",
                      collide=False)


def smooth_curve(keys, s):
    """Monotone cubic (Catmull-Rom style) interpolation through [(s, v), ...] sorted by s."""
    ss = [k[0] for k in keys]
    vs = [k[1] for k in keys]
    if s <= ss[0]:
        return vs[0]
    if s >= ss[-1]:
        return vs[-1]
    i = max(j for j in range(len(ss) - 1) if ss[j] <= s)
    t = (s - ss[i]) / (ss[i + 1] - ss[i])
    p0 = vs[i - 1] if i > 0 else vs[i]
    p3 = vs[i + 2] if i + 2 < len(vs) else vs[i + 1]
    p1, p2 = vs[i], vs[i + 1]
    t2, t3 = t * t, t * t * t
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


# --------------------------------------------------------------------------------- distance checks
def prim_sdf(points, p):
    """Signed distance from an (n, 3) array of points to one primitive (wedges use their bounding box)."""
    r = np.array(p["rot"], float)
    q = (np.asarray(points, float) - np.array(p["pos"], float)) @ r      # local coordinates
    half = np.array(p["size"], float) / 2
    if p["shape"] == "Ball":
        return np.linalg.norm(q, axis=1) - half.min()
    if p["shape"] == "Cylinder":
        radial = np.hypot(q[:, 1], q[:, 2]) - min(half[1], half[2])
        axial = np.abs(q[:, 0]) - half[0]
        outside = np.hypot(np.maximum(axial, 0), np.maximum(radial, 0))
        return outside + np.minimum(np.maximum(axial, radial), 0)
    d = np.abs(q) - half
    outside = np.linalg.norm(np.maximum(d, 0), axis=1)
    return outside + np.minimum(d.max(axis=1), 0)


def clearance(points, prims):
    """Smallest distance from any of the points to any primitive (negative = inside one)."""
    pts = np.asarray(points, float)
    best = np.full(len(pts), np.inf)
    for p in prims:
        best = np.minimum(best, prim_sdf(pts, p))
    return float(best.min()), pts[int(best.argmin())]


def bounds(prims):
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for p in prims:
        r = np.array(p["rot"], float)
        half = np.array(p["size"], float) / 2
        if p["shape"] == "Ball":
            reach = np.full(3, half.min())
        else:
            reach = np.abs(r) @ half
        c = np.array(p["pos"], float)
        lo = np.minimum(lo, c - reach)
        hi = np.maximum(hi, c + reach)
    return lo, hi


def shifted(asset, offset):
    out = Asset(asset.name)
    out.place(asset, offset)
    return out


# =========================================================================================== MEGALODON FOSSIL
BONE = (231, 220, 190)
BONE_MID = (214, 200, 166)
BONE_DARK = (196, 180, 146)
JAW = (184, 166, 128)
TOOTH = (250, 246, 234)
SOCKET = (54, 44, 38)
CRACK = (124, 108, 84)
MOSS = (106, 150, 76)
MOSS_DARK = (78, 120, 62)
SAND = ((222, 200, 156), (208, 186, 140))

GAPE = math.radians(30)                  # how far the mouth is open
HINGE = (0.0, 9.2, -22.0)                # jaw hinge, the upper skull turns about it
JAW_A, JAW_B = 10.0, 17.5                # half width and depth of the U-shaped jaws
LOWER_Y = 2.1                            # centre height of the lower jaw bar (it rests on the sand)
RIB_Z = (-15.5, -1.0, 13.5, 28.0)        # where the four rib pairs leave the spine (14.5 studs apart)
RIB_W = (14.0, 16.0, 16.0, 14.0)         # half width of the cage at each rib
RIB_SWEEP = 7.0                          # rib tips sit this far behind their root
RIB_REF_Y = 18.0                         # the sweep depends on the height alone: ribs stay parallel where fish swim
PROBE_Y = 8.0                            # height of the swim-through checks (a fish's centre)
SPINE_Z0, SPINE_Z1 = -19.5, 37.0


def spine_point(s):
    z = lerp(SPINE_Z0, SPINE_Z1, s)
    y = smooth_curve([(0.0, 12.8), (0.12, 16.6), (0.3, 18.2), (0.55, 18.0), (0.8, 16.4), (0.92, 13.2), (1.0, 13.4)], s)
    x = 7.0 * max(0.0, (s - 0.7) / 0.3) ** 2           # the tail curls to one side: a gentle arc
    return (x, y, z)


def spine_frame(s, ds=1e-3):
    p0, p1 = spine_point(max(0.0, s - ds)), spine_point(min(1.0, s + ds))
    t = norm(sub(p1, p0))
    side = norm(cross(UP, mul(t, -1)))                  # +x when the spine runs along +z
    up = norm(cross(mul(t, -1), side))
    return spine_point(s), t, side, up


def s_at_z(z):
    return (z - SPINE_Z0) / (SPINE_Z1 - SPINE_Z0)


def build_skull(fossil, rng):
    R = rot_x(GAPE)

    def up_pt(p):                                       # upper skull frame -> model
        return add(HINGE, apply(R, p))

    def up_dir(d):
        return apply(R, d)

    def up_box(group, lo, hi, color, collide=True, mat="Smooth"):
        size = sub(hi, lo)
        centre = mul(add(lo, hi), 0.5)
        return fossil.prim(group, "Block", size, up_pt(centre), R, color, mat, collide=collide)

    def u_curve(theta, scale=1.0):
        return (JAW_A * scale * math.cos(theta), 0.0, -JAW_B * scale * math.sin(theta))

    def u_tangent(theta):
        return norm((-JAW_A * math.sin(theta), 0.0, -JAW_B * math.cos(theta)))

    # --- jaws: two U-shaped bars made of short blocks
    n = 14
    thetas = [math.pi * i / n for i in range(n + 1)]
    for i in range(n):
        a, b = u_curve(thetas[i]), u_curve(thetas[i + 1])
        d = norm(sub(b, a))
        a2, b2 = sub(a, mul(d, 0.7)), add(b, mul(d, 0.7))
        mid = 0.5 * (thetas[i] + thetas[i + 1])
        thick = 3.4 - 0.9 * math.sin(mid)               # chunkier at the hinge, slimmer at the front
        # upper jaw (turned with the skull)
        fossil.beam("Jaw", up_pt(a2), up_pt(b2), 3.0, thick, JAW, "Smooth", True, up_dir(UP))
        # lower jaw on the sand
        la = add((0.0, LOWER_Y, HINGE[2]), a2)
        lb = add((0.0, LOWER_Y, HINGE[2]), b2)
        fossil.beam("Jaw", la, lb, 3.2, thick + 0.3, JAW, "Smooth", True)
    # hinge: the two jaws meet in a knob on each side
    for sx in (-1, 1):
        lo_end = (sx * JAW_A, LOWER_Y + 1.6, HINGE[2] + 0.4)
        hi_end = up_pt((sx * JAW_A, -1.4, 0.4))
        fossil.beam("Jaw", lo_end, hi_end, 2.8, 2.8, JAW, "Smooth", True, (0.0, 0.0, 1.0))
        fossil.prim("Jaw", "Ball", (3.6, 3.6, 3.6), up_pt((sx * JAW_A, -0.6, 0.8)), IDENT, BONE_MID, "Smooth")
        fossil.prim("Jaw", "Ball", (3.4, 3.4, 3.4), (sx * JAW_A, LOWER_Y + 0.8, HINGE[2] + 0.8), IDENT, BONE_MID, "Smooth")

    # --- teeth: an outer row of big triangles and a smaller, staggered inner row on each jaw
    for row, (offset, k, stagger) in enumerate(((0.55, 1.0, 0.0), (-0.75, 0.62, 0.5))):
        count = 15 if row == 0 else 12
        for j in range(count):
            th = math.radians(16) + (math.pi - math.radians(32)) * (j + 0.5 + stagger * 0.5) / (count + stagger * 0.5)
            front = math.sin(th)                         # 1 at the front of the jaw, smaller towards the hinge
            h = (1.9 + 1.7 * front ** 1.5) * k
            w = (1.7 + 0.9 * front) * k
            normal = norm((math.cos(th) / JAW_A, 0.0, -math.sin(th) / JAW_B))   # outward normal of the U
            along = u_tangent(th)
            base = add(u_curve(th), mul(normal, offset))
            # upper jaw: hanging from the bar's underside, leaning a little into the mouth
            tip_dir = norm(add((0.0, -1.0, 0.0), mul(normal, -0.18)))
            tooth(fossil, "Teeth", up_pt(add(base, (0.0, -1.2, 0.0))), up_dir(tip_dir), up_dir(along), h, w, 0.7, TOOTH)
            # lower jaw: standing on the bar, leaning slightly outwards
            lb = add((0.0, LOWER_Y + 1.5, HINGE[2]), base)
            tooth(fossil, "Teeth", lb, norm(add(UP, mul(normal, 0.15))), along, h * 0.95, w, 0.7, TOOTH)

    # --- cranium: low and wide, with a ridge and bevelled top edges (a house-shaped section), a long pointed
    #     rostrum overhanging the jaws in front, the occiput behind
    up_box("Skull", (-7.5, 1.4, -15.5), (7.5, 6.6, -1.0), BONE)
    for sx in (-1, 1):
        back = (-sx * 1.0, 0.0, 0.0)                     # the wedge's tall side faces the middle
        bevel = from_axes(norm(cross(UP, back)), UP, back)
        fossil.prim("Skull", "Wedge", (14.5, 2.4, 5.25), up_pt((sx * 4.875, 7.8, -8.25)), matmul(R, bevel), BONE, "Smooth")
    up_box("Skull", (-2.25, 6.6, -15.5), (2.25, 9.0, -1.0), BONE)
    up_box("Skull", (-5.0, 2.0, -21.0), (5.0, 5.6, -15.5), BONE_MID)
    fossil.prim("Skull", "Wedge", (10.0, 3.4, 5.5), up_pt((0.0, 5.6 + 1.7, -18.25)), R, BONE_MID, "Smooth")
    up_box("Skull", (-3.4, 2.2, -24.6), (3.4, 5.0, -21.0), BONE)
    fossil.prim("Skull", "Wedge", (6.8, 1.6, 3.6), up_pt((0.0, 5.0 + 0.8, -22.8)), R, BONE, "Smooth")
    fossil.prim("Skull", "Wedge", (6.8, 2.8, 2.0), up_pt((0.0, 3.6, -25.6)), matmul(R, rot_x(math.pi / 2)), BONE, "Smooth")
    up_box("Skull", (-5.8, 2.8, -1.4), (5.8, 8.6, 3.0), BONE_MID)                      # occiput, meets the spine
    up_box("Skull", (-3.2, 8.4, -4.0), (3.2, 10.2, 1.6), BONE)                         # crest
    # eye sockets: a dark hollow framed by a heavy brow and a cheek bar, all standing proud of the side face
    def side_box(sx, out, inner, y0, y1, z0, z1, color):
        x0, x1 = (7.5 - inner, 7.5 + out) if sx > 0 else (-7.5 - out, -7.5 + inner)
        return up_box("Skull", (x0, y0, z0), (x1, y1, z1), color, collide=False)

    for sx in (-1, 1):
        side_box(sx, 0.25, 0.25, 2.6, 5.6, -13.6, -9.4, SOCKET)
        side_box(sx, 1.0, 0.4, 5.4, 6.9, -14.6, -8.4, BONE)           # brow
        side_box(sx, 0.8, 0.3, 1.6, 2.8, -14.0, -8.8, BONE_MID)       # cheek
        side_box(sx, 0.7, 0.3, 2.4, 5.8, -15.0, -13.6, BONE_MID)      # front of the socket
        # nostril pits under the rostrum
        up_box("Skull", (sx * 1.6 - 0.7, 2.05, -23.8), (sx * 1.6 + 0.7, 2.25, -22.4), SOCKET, collide=False)

    # cracks: thin dark zigzags on the flat faces of the cranium and the rostrum
    def crack_on_face(points, axis_val, face):
        for a, b in zip(points[:-1], points[1:]):
            if face == "side":                          # points are (y, z) on the plane x = axis_val
                pa, pb = (axis_val, a[0], a[1]), (axis_val, b[0], b[1])
                d = norm(sub(pb, pa))
                rot = from_axes((1.0, 0.0, 0.0), (0.0, d[2], -d[1]), d)
                size = (0.16, 0.34, length(sub(pb, pa)) + 0.2)
            else:                                       # points are (x, z) on the plane y = axis_val
                pa, pb = (a[0], axis_val, a[1]), (b[0], axis_val, b[1])
                d = norm(sub(pb, pa))
                rot = from_axes(norm(cross(UP, d)), UP, d)
                size = (0.34, 0.16, length(sub(pb, pa)) + 0.2)
            fossil.prim("Detail", "Block", size, up_pt(mul(add(pa, pb), 0.5)), matmul(R, rot), CRACK, "Smooth",
                        collide=False)

    for sx in (-1, 1):
        crack_on_face([(6.4, -7.0), (5.0, -5.8), (4.4, -3.8), (2.8, -3.0), (1.8, -1.6)], sx * 7.58, "side")
    crack_on_face([(-1.4, -14.6), (-0.4, -12.6), (-1.2, -10.4), (0.0, -8.2)], 9.06, "top")
    crack_on_face([(2.6, -20.4), (1.4, -19.0), (2.2, -17.6)], 5.66, "top")
    # moss on the ridge, the bevels and the crest
    for k in range(9):
        x = rng.uniform(-5.5, 5.5)
        z = rng.uniform(-14.5, -2.5)
        y = 9.05 if abs(x) < 2.2 else 6.65 + 2.4 * (1 - (abs(x) - 2.25) / 5.25)
        fossil.prim("Detail", "Block", (rng.uniform(1.4, 2.6), 0.45, rng.uniform(1.6, 3.0)), up_pt((x, y, z)),
                    matmul(R, rot_y(rng.uniform(-0.5, 0.5))), MOSS if k % 3 else MOSS_DARK, "Smooth", collide=False)
    for k in range(3):
        fossil.prim("Detail", "Block", (rng.uniform(1.2, 2.2), 0.45, rng.uniform(1.2, 2.0)),
                    up_pt((rng.uniform(-2.5, 2.5), 10.3, rng.uniform(-3.4, 1.0))), R, MOSS, "Smooth", collide=False)
    # moss and cracks on the lower jaw
    for th in (0.5, 1.3, 2.4):
        c = add((0.0, LOWER_Y + 1.85, HINGE[2]), u_curve(th))
        fossil.prim("Detail", "Block", (1.8, 0.4, 1.6), c, rot_y(th), MOSS_DARK, "Smooth", collide=False)
    for th in (0.9, 2.1):
        c = add((0.0, LOWER_Y, HINGE[2]), u_curve(th))
        fossil.prim("Detail", "Block", (3.5, 3.6, 0.3), c, look_rot(u_tangent(th)), CRACK, "Smooth", collide=False)


def build_spine(fossil, rng):
    """Separate vertebrae (discs) along the spine curve, with neural spines on top and haemal spines under the tail."""
    s, k = 0.0, 0
    while s <= 1.0:
        p, t, side, up = spine_frame(s)
        dia = lerp(5.2, 2.6, s ** 1.1)
        color = (BONE, BONE_MID)[k % 2] if k % 7 != 3 else BONE_DARK
        fossil.cylinder("Spine", sub(p, mul(t, 0.75)), add(p, mul(t, 0.75)), dia, color, "Smooth", collide=True)
        if k % 5 == 2:                                   # a crack ring on some vertebrae
            fossil.cylinder("Detail", sub(p, mul(t, 0.12)), add(p, mul(t, 0.12)), dia + 0.12, CRACK, "Smooth", collide=False)
        # neural spine, leaning back
        d = norm(add(mul(up, math.cos(math.radians(32))), mul(t, math.sin(math.radians(32)))))
        ln = lerp(4.2, 2.0, s)
        a = add(p, mul(up, dia * 0.35))
        fossil.beam("SpineDetail", a, add(a, mul(d, ln)), 0.55, 0.9, BONE_MID, "Smooth", False, t)
        # transverse processes in the trunk
        if s < 0.8 and k % 2 == 0:
            for sx in (-1, 1):
                b = add(p, mul(side, sx * dia * 0.42))
                fossil.cylinder("SpineDetail", b, add(b, add(mul(side, sx * 1.6), mul(up, -0.4))), 0.8, BONE_MID, "Smooth", collide=False)
        # haemal spines under the tail
        if s > 0.87:
            dd = norm(add(mul(up, -math.cos(math.radians(38))), mul(t, math.sin(math.radians(38)))))
            b = add(p, mul(up, -dia * 0.35))
            fossil.beam("SpineDetail", b, add(b, mul(dd, lerp(3.4, 1.8, s))), 0.5, 0.8, BONE_MID, "Smooth", False, t)
        if k % 6 == 1 and s < 0.9:                       # a moss tuft on top now and then
            fossil.prim("Detail", "Block", (1.3, 0.45, 1.3), add(p, mul(up, dia / 2 + 0.1)), from_axes(side, up, t),
                        MOSS, "Smooth", collide=False)
        # step to the next vertebra: about 2.45 studs along the curve
        step = 0.0
        while step < 2.45 and s <= 1.0:
            s2 = s + 0.002
            step += length(sub(spine_point(min(s2, 1.0)), spine_point(s)))
            s = s2
        k += 1
    return k


def rib_points(i, sx, steps=10):
    """Centre line of rib pair i, side sx: an arc from the vertebra out and down to the sand, swept back by an
    amount that depends on the height alone, so neighbouring ribs stay parallel where the fish swim between them."""
    p = spine_point(s_at_z(RIB_Z[i]))
    along, across = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)  # every rib in a plane square to the trunk: all parallel
    w = RIB_W[i]
    phi1 = math.radians(122)                             # past the widest point the tips curl back in: a barrel
    h = (p[1] - 0.7) / (1 - math.cos(phi1))
    pts = []
    for j in range(steps + 1):
        phi = math.radians(10) + (phi1 - math.radians(10)) * j / steps
        y = p[1] - h * (1 - math.cos(phi))
        q = add((p[0], y, p[2]), mul(across, sx * w * math.sin(phi)))
        q = add(q, mul(along, RIB_SWEEP * max(0.0, (RIB_REF_Y - y) / RIB_REF_Y) ** 1.1))
        pts.append(q)
    pts[0] = add(p, mul(across, sx * 1.6))               # start inside the vertebra
    return pts


def build_ribs(fossil, rng):
    for i in range(len(RIB_Z)):
        for sx in (-1, 1):
            pts = rib_points(i, sx)
            dias = [lerp(2.4, 1.3, j / (len(pts) - 1)) for j in range(len(pts))]
            chain(fossil, "Ribs", pts, dias, BONE if (i + (sx > 0)) % 2 else BONE_MID, overlap=0.35)
            fossil.prim("Ribs", "Ball", (1.9, 1.9, 1.9), pts[-1], IDENT, BONE_MID, "Smooth", collide=False)
            j = 3 + (i + (sx > 0)) % 4                   # a crack ring somewhere along the rib
            a, b = pts[j], pts[j + 1]
            m = mul(add(a, b), 0.5)
            d = norm(sub(b, a))
            fossil.cylinder("Detail", sub(m, mul(d, 0.14)), add(m, mul(d, 0.14)), dias[j] + 0.18, CRACK, "Smooth", collide=False)
            # half buried tip: a sand mound and a moss tuft where the rib meets the sand
            tip = pts[-1]
            cap(fossil, "Sand", tip[0] + sx * 0.6, tip[2], rng.uniform(3.4, 4.4), rng.uniform(1.1, 1.6), SAND[(i + 1) % 2])
            fossil.prim("Detail", "Block", (1.2, 0.8, 1.2), add(tip, (sx * -1.2, 0.2, 0.6)), rot_y(rng.uniform(0, 1.5)),
                        MOSS_DARK, "Smooth", collide=False)


def build_fins(fossil, rng):
    # pectoral fins: fans of rays lying on the sand behind the jaw, outside the cage
    for sx in (-1, 1):
        root = (sx * 9.6, 1.5, -13.4)
        fossil.beam("Fins", (sx * 6.6, 2.4, -14.2), root, 1.4, 1.2, BONE_MID, "Smooth", False)
        for j in range(6):
            ang = math.radians(18 + j * 12)
            ln = 14.0 - j * 1.2
            d = norm((sx * math.cos(ang), -0.05, math.sin(ang)))
            mid = add(root, add(mul(d, ln * 0.55), (0.0, 0.25, 0.0)))
            end = add(root, mul(d, ln))
            end = (end[0], 0.6, end[2])
            chain(fossil, "Fins", [root, mid, end], [1.0, 0.8, 0.55], BONE if j % 2 else BONE_MID, overlap=0.2)
        cap(fossil, "Sand", sx * 19.0, -6.0, 4.6, 1.2, SAND[0])
    # dorsal fin: rays rising from the vertebrae above the cage, the leading one longest
    rays = 7
    for j in range(rays):
        s = s_at_z(-3.0 + j * 2.3)
        p, t, side, up = spine_frame(s)
        base = add(p, mul(up, 2.6))
        ln = 13.0 - j * 1.4
        d = norm(add(mul(up, math.cos(math.radians(30 + j * 3))), mul(t, math.sin(math.radians(30 + j * 3)))))
        mid = add(base, add(mul(d, ln * 0.5), mul(t, 0.6)))
        chain(fossil, "Fins", [base, mid, add(base, add(mul(d, ln), mul(t, 1.4)))], [0.9, 0.7, 0.45],
              BONE if j % 2 else BONE_MID, overlap=0.2)
    # caudal fin: the spine runs on into the big upper lobe, a shorter lower lobe below
    p, t, side, up = spine_frame(1.0)
    for j in range(7):
        ang = math.radians(30 + j * 6.5)
        ln = 13.0 - j * 0.9
        d = norm(add(mul(t, math.cos(ang)), mul(up, math.sin(ang))))
        mid = add(p, mul(d, ln * 0.5))
        chain(fossil, "Fins", [p, mid, add(p, mul(d, ln))], [1.0, 0.75, 0.45], BONE if j % 2 else BONE_MID, overlap=0.2)
    for j in range(5):
        ang = math.radians(-22 - j * 7)
        ln = 8.0 - j * 0.6
        d = norm(add(mul(t, math.cos(ang)), mul(up, math.sin(ang))))
        chain(fossil, "Fins", [p, add(p, mul(d, ln * 0.5)), add(p, mul(d, ln))], [0.9, 0.7, 0.45],
              BONE_MID if j % 2 else BONE, overlap=0.2)
    # the last vertebrae climb into the upper lobe
    d = norm(add(mul(t, math.cos(math.radians(36))), mul(up, math.sin(math.radians(36)))))
    for j in range(4):
        c = add(p, mul(d, 2.4 + j * 2.6))
        fossil.cylinder("Spine", sub(c, mul(d, 0.6)), add(c, mul(d, 0.6)), 2.4 - j * 0.35, BONE_MID, "Smooth", collide=True)


def build_megalodon():
    """~94 studs long, upright on its belly with the tail curled into a gentle arc, mouth wide open.
    Origin: centre of the underside, on y = 0; the head looks along -Z. Only the skull, jaws and vertebrae collide."""
    rng = random.Random(2061)
    fossil = Asset("MegalodonFossil")
    build_skull(fossil, rng)
    build_spine(fossil, rng)
    build_ribs(fossil, rng)
    build_fins(fossil, rng)
    # sand piled against the chin and the jaw hinges
    cap(fossil, "Sand", 0.0, -39.0, 6.0, 1.6, SAND[0])
    cap(fossil, "Sand", -9.0, -28.5, 4.4, 1.2, SAND[1])
    cap(fossil, "Sand", 10.0, -25.0, 4.0, 1.1, SAND[0])
    cap(fossil, "Sand", 6.0, 36.0, 4.4, 1.2, SAND[1])
    # centre the footprint on the origin (the sand caps may dip under y = 0: they sink into the floor)
    lo, hi = bounds([p for p in fossil.prims if p["group"] != "Sand"])
    offset = (-(lo[0] + hi[0]) / 2, 0.0, -(lo[2] + hi[2]) / 2)
    centred = shifted(fossil, offset)
    centred.offset = offset                              # where the build frame moved to (for the checks)
    return centred


def fossil_checks(fossil):
    """Swim-through checks (like the aquarium tunnels), against every part of the fossil:
    - each gap between two consecutive rib pairs: a straight line across the body at fish height, entering
      between the ribs on one side, crossing the cage and leaving between the ribs on the other side;
    - a lengthwise run inside the cage.
    clear_diameter = 2 x the distance from the line to the nearest part (a size-5 fish is 9 x 3.5 studs)."""
    prims = fossil.prims
    ox, _, oz = fossil.offset
    lo, hi = bounds([p for p in prims if p["group"] != "Sand"])
    report = {"size": [round(float(v), 1) for v in hi - lo], "passages": []}

    def z_at_height(i, y):
        pts = rib_points(i, 1)
        return float(np.interp(y, [q[1] for q in pts][::-1], [q[2] for q in pts][::-1]))

    for i in range(len(RIB_Z) - 1):
        zm = (z_at_height(i, PROBE_Y) + z_at_height(i + 1, PROBE_Y)) / 2 + oz
        line = [(x + ox, PROBE_Y, zm) for x in np.arange(-32.0, 32.01, 0.25)]
        d, at = clearance(line, prims)
        report["passages"].append({"between_rib_pairs": [i + 1, i + 2], "z": round(zm, 2),
                                   "clear_diameter": round(2 * d, 2), "tightest_at": [round(float(v), 2) for v in at]})
    # inside the cage, from where the first rib pair crosses fish height to where the last one does
    z0 = z_at_height(0, PROBE_Y) + oz
    z1 = z_at_height(len(RIB_Z) - 1, PROBE_Y) + oz
    zs = np.arange(z0, z1, 0.25)
    pts = np.array([(ox, PROBE_Y, z) for z in zs])
    best = np.full(len(pts), np.inf)
    for p in prims:
        best = np.minimum(best, prim_sdf(pts, p))
    ok = zs[2 * best >= 11.0]
    report["cage_lengthwise"] = {"clear_11_from_z": round(float(ok.min()), 1), "clear_11_to_z": round(float(ok.max()), 1),
                                 "widest": round(float(2 * best.max()), 1), "narrowest_inside": round(float(2 * best.min()), 1)}
    return report


# =========================================================================================== CORALS
def coral_branching(rng):
    """Staghorn coral, hot pink: a trunk that forks into upturned branches with round tips."""
    c = Asset("CoralBranching")
    base, mid, tip = (210, 52, 134), (255, 92, 170), (255, 182, 220)

    def grow(p, d, ln, dia, depth):
        q = add(p, mul(d, ln))
        col = mix(base, mid, min(1.0, (4 - depth) / 2.5))
        c.cylinder("Coral", sub(p, mul(d, 0.2)), q, dia, col, "Smooth", collide=False)
        if depth == 0 or ln < 1.1:
            c.prim("Coral", "Ball", (dia * 1.35,) * 3, q, IDENT, tip, "Smooth", collide=False)
            return
        kids = 2 if depth > 1 else rng.choice((1, 2, 2))
        for k in range(kids):
            yaw = rng.uniform(0, 2 * math.pi)
            tilt = math.radians(rng.uniform(18, 42))
            nd = norm(add(mul(d, math.cos(tilt)), mul((math.cos(yaw), 0.0, math.sin(yaw)), math.sin(tilt))))
            nd = norm(add(nd, (0.0, 0.35, 0.0)))        # branches keep reaching up
            grow(q, nd, ln * rng.uniform(0.68, 0.84), dia * 0.74, depth - 1)

    c.prim("Coral", "Ball", (3.4, 3.4, 3.4), (0.0, 0.2, 0.0), IDENT, base, "Smooth", collide=False)
    for k in range(3):
        yaw = k * 2.1 + 0.4
        d = norm((math.cos(yaw) * 0.35, 1.0, math.sin(yaw) * 0.35))
        grow((0.0, 0.6, 0.0), d, 3.6, 1.55, 3)
    return c


def coral_fan(rng):
    """Sea fan (gorgonian), purple: a flat lacework of thin branches in one vertical plane."""
    c = Asset("CoralFan")
    stem, mid, tip = (120, 44, 178), (168, 76, 230), (222, 160, 255)
    c.prim("Coral", "Ball", (2.6, 2.6, 2.6), (0.0, 0.1, 0.0), IDENT, stem, "Smooth", collide=False)

    def grow(p, ang, ln, dia, depth):
        d = (math.sin(ang), math.cos(ang), 0.0)
        q = add(p, mul(d, ln))
        c.cylinder("Coral", sub(p, mul(d, 0.1)), q, dia, mix(stem, mid, min(1.0, (5 - depth) / 3)), "Smooth", collide=False)
        if depth == 0:
            c.prim("Coral", "Ball", (dia * 1.8,) * 3, q, IDENT, tip, "Smooth", collide=False)
            return
        spread = math.radians(rng.uniform(16, 30))
        for sgn in (-1, 1):
            na = ang + sgn * spread + rng.uniform(-0.08, 0.08)
            na = max(-math.radians(72), min(math.radians(72), na))
            grow(q, na, ln * rng.uniform(0.72, 0.86), max(0.32, dia * 0.8), depth - 1)

    grow((0.0, 0.4, 0.0), 0.0, 3.0, 1.2, 5)
    # a few cross links make it read as lace
    pts = [p["pos"] for p in c.prims if p["shape"] == "Ball"][1:]
    pts.sort(key=lambda v: math.atan2(v[0], v[1]))
    for a, b in zip(pts[:-1:3], pts[1::3]):
        if length(sub(a, b)) < 3.2:
            c.cylinder("Coral", a, b, 0.3, mid, "Smooth", collide=False)
    return c


def coral_brain(rng):
    """Brain coral, sunny yellow: overlapping domes ringed with dark meandering grooves."""
    c = Asset("CoralBrain")
    body, light, groove = (255, 204, 48), (255, 228, 120), (206, 128, 22)
    domes = [((0.0, 0.0, 0.0), 4.6), ((3.6, 0.0, 2.2), 3.0), ((-3.2, 0.0, 2.6), 2.6)]
    for (x, _, z), r in domes:
        c.prim("Coral", "Ball", (2 * r,) * 3, (x, r * 0.45, z), IDENT, body, "Smooth", collide=False)
    for (x, _, z), r in domes:
        centre = (x, r * 0.45, z)
        # wavy rings at a few heights: the grooves of a brain coral run round the dome and meander
        rings = (14, 38, 60) if r > 4 else (22, 52)
        for k, lat0 in enumerate(rings):
            steps = 16 if r > 4 else 11
            waves = 6 + k
            pts = []
            for j in range(steps + 1):
                lon = 2 * math.pi * j / steps
                lat = math.radians(lat0 + 7.0 * math.sin(waves * lon + k * 1.3))
                v = (math.cos(lat) * math.cos(lon), math.sin(lat), math.cos(lat) * math.sin(lon))
                pts.append(add(centre, mul(v, r + 0.02)))
            chain(c, "Coral", pts, [0.4] * len(pts), groove, overlap=0.08)
        c.prim("Coral", "Ball", (r * 0.7,) * 3, add(centre, (-r * 0.35, r * 0.62, -r * 0.3)), IDENT, light, "Smooth", collide=False)
    return c


def coral_tubes(rng):
    """Organ-pipe coral, orange: a bundle of upright tubes with light rims and dark mouths."""
    c = Asset("CoralTubes")
    body, rim, hole = (255, 124, 34), (255, 198, 96), (112, 36, 16)
    c.prim("Coral", "Ball", (6.0, 6.0, 6.0), (0.0, -1.4, 0.0), IDENT, (226, 98, 30), "Smooth", collide=False)
    placed = []
    for _ in range(400):
        if len(placed) >= 19:
            break
        a = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(rng.random()) * 4.0
        x, z = math.cos(a) * rr, math.sin(a) * rr
        r = rng.uniform(0.6, 1.05)
        if any(math.hypot(x - px, z - pz) < r + pr + 0.15 for px, pz, pr in placed):
            continue
        placed.append((x, z, r))
    for x, z, r in placed:
        h = 9.0 - math.hypot(x, z) * 1.3 + rng.uniform(-1.2, 1.2)
        c.cylinder("Coral", (x, 0.0, z), (x, h, z), 2 * r, body, "Smooth", collide=False)
        c.cylinder("Coral", (x, h - 0.5, z), (x, h + 0.05, z), 2 * r + 0.3, rim, "Smooth", collide=False)
        c.cylinder("Coral", (x, h, z), (x, h + 0.1, z), 2 * r - 0.5, hole, "Smooth", collide=False)
    return c


def coral_table(rng):
    """Table coral, turquoise: a stem carrying flat wavy-edged plates in two tiers."""
    c = Asset("CoralTable")
    stem, plate, rim, knob = (22, 150, 146), (36, 214, 200), (156, 255, 236), (120, 240, 226)
    c.cylinder("Coral", (0.0, 0.0, 0.0), (0.0, 4.6, 0.0), 2.4, stem, "Smooth", collide=False)
    c.prim("Coral", "Ball", (3.6, 3.6, 3.6), (0.0, 0.3, 0.0), IDENT, stem, "Smooth", collide=False)
    c.cylinder("Coral", (0.6, 4.4, 0.3), (0.9, 6.8, 0.5), 1.6, stem, "Smooth", collide=False)
    for (cx, y, cz), r in (((0.0, 4.6, 0.0), 6.2), ((0.9, 6.8, 0.5), 4.0)):
        c.cylinder("Coral", (cx, y, cz), (cx, y + 0.7, cz), 2 * r, plate, "Smooth", collide=False)
        lobes = 16 if r > 5 else 11
        for k in range(lobes):
            a = k / lobes * 2 * math.pi + rng.uniform(-0.08, 0.08)
            px, pz = cx + math.cos(a) * r, cz + math.sin(a) * r
            lr = rng.uniform(1.0, 1.5)
            c.cylinder("Coral", (px, y + 0.05, pz), (px, y + 0.65, pz), 2 * lr, rim, "Smooth", collide=False)
        for k in range(6 if r > 5 else 4):
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0, r * 0.75)
            c.prim("Coral", "Ball", (0.9, 0.9, 0.9), (cx + math.cos(a) * rr, y + 0.75, cz + math.sin(a) * rr), IDENT,
                   knob, "Smooth", collide=False)
    return c


def coral_anemone(rng):
    """Sea anemone: a violet column crowned with curling pink tentacles tipped in orange."""
    c = Asset("CoralAnemone")
    column, disc, tent, tip = (140, 58, 196), (196, 110, 236), (255, 108, 150), (255, 196, 96)
    c.cylinder("Coral", (0.0, 0.0, 0.0), (0.0, 2.6, 0.0), 4.6, column, "Smooth", collide=False)
    c.cylinder("Coral", (0.0, 2.5, 0.0), (0.0, 3.0, 0.0), 5.2, disc, "Smooth", collide=False)
    c.prim("Coral", "Ball", (2.0, 2.0, 2.0), (0.0, 3.0, 0.0), IDENT, (255, 150, 190), "Smooth", collide=False)
    n = 22
    for k in range(n):
        ring = 0 if k < 13 else 1
        a = k / (13 if ring == 0 else 9) * 2 * math.pi + (0.25 if ring else 0.0)
        r0 = 2.2 if ring == 0 else 1.2
        base = (math.cos(a) * r0, 3.0, math.sin(a) * r0)
        out = (math.cos(a), 0.0, math.sin(a))
        ln = rng.uniform(4.2, 5.6) if ring == 0 else rng.uniform(3.4, 4.4)
        lean = 0.75 if ring == 0 else 0.35
        pts = [base]
        for j in range(1, 4):
            f = j / 3
            # rises, leans out, then the tip curls back over
            pts.append(add(base, add(mul(out, ln * lean * f * (1.0 + 0.25 * f)), (0.0, ln * (f - 0.28 * f * f), 0.0))))
        chain(c, "Coral", pts, [0.95, 0.8, 0.62, 0.48], tent, overlap=0.2)
        c.prim("Coral", "Ball", (0.95, 0.95, 0.95), pts[-1], IDENT, tip, "Smooth", collide=False)
    return c


CORAL_BUILDERS = [coral_branching, coral_fan, coral_brain, coral_tubes, coral_table, coral_anemone]
CORAL_NAMES = ["CoralBranching", "CoralFan", "CoralBrain", "CoralTubes", "CoralTable", "CoralAnemone"]


def build_corals():
    out = []
    for k, f in enumerate(CORAL_BUILDERS):
        a = f(random.Random(700 + k))
        lo, hi = bounds(a.prims)
        # origin at the centre of the base, the base on y = 0 (domes and the brain coral sink a little into the floor)
        out.append(shifted(a, (-(lo[0] + hi[0]) / 2, 0.0, -(lo[2] + hi[2]) / 2)))
    return out


# =========================================================================================== OCEAN DECOR SPOTS
OCEAN_BED = -46.0
ARENA_HALF = (150.0, 120.0)
FOSSIL_AT = (60.0, OCEAN_BED, -40.0)
FOSSIL_YAW = math.radians(-118)          # head towards the arena centre's side, body along the long axis
SPAWN_GAP = 25.0                         # corals and seaweed never come closer than this to a player spawn point
ISLAND_AT = (200.0, -470.0)


def point_segment_distance(p, a, b):
    p, a, b = np.asarray(p, float), np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
    return float(np.linalg.norm(p - (a + t * ab)))


def ocean_decor_spots(fossil, corals, spawn_points):
    """FossilSpot, CoralSpots (variant 1-6, scale 0.8-1.6) and SeaweedSpots (height 18-40), in the Ocean's frame,
    standing on the bed (y = -46). Two thirds inside the arena in groves, one third outside up to +-500."""
    rng = random.Random(4646)
    rot = rot_y(FOSSIL_YAW)
    fossil_world = Asset("FossilWorld")
    fossil_world.place(fossil, FOSSIL_AT, rot)
    f_lo, f_hi = bounds([p for p in fossil_world.prims if p["group"] != "Sand"])
    coral_height = [bounds(c.prims)[1][1] for c in corals]
    coral_radius = [max(abs(v) for v in (bounds(c.prims)[0][0], bounds(c.prims)[1][0], bounds(c.prims)[0][2], bounds(c.prims)[1][2])) for c in corals]
    hx, hz = ARENA_HALF
    taken = []                                           # (x, z, radius) of everything placed on the bed

    def fossil_clear(x, z, r):
        # keep off the fossil's footprint (its bounding box, grown by the object's radius and a margin)
        return not (f_lo[0] - r - 3 < x < f_hi[0] + r + 3 and f_lo[2] - r - 3 < z < f_hi[2] + r + 3)

    def spawn_clear(x, z, top):
        a, b = (x, OCEAN_BED, z), (x, OCEAN_BED + top, z)
        return all(point_segment_distance(sp, a, b) >= SPAWN_GAP for sp in spawn_points)

    def free(x, z, r):
        return all(math.hypot(x - tx, z - tz) >= r + tr + 1.0 for tx, tz, tr in taken)

    coral_spots, weed_spots = [], []

    def add_coral(x, z, variant, scale, yaw):
        coral_spots.append(spot((x, OCEAN_BED, z), rot_y(yaw), variant=variant, scale=round(scale, 2)))
        taken.append((x, z, coral_radius[variant - 1] * scale))

    def add_weed(x, z, h, yaw):
        weed_spots.append(spot((x, OCEAN_BED, z), rot_y(yaw), height=round(h, 1)))
        taken.append((x, z, 2.0))

    # --- inside the arena: groves around a few centres
    centres = []
    for _ in range(4000):
        if len(centres) >= 11:
            break
        x, z = rng.uniform(-hx + 14, hx - 14), rng.uniform(-hz + 14, hz - 14)
        if not fossil_clear(x, z, 10) or any(math.hypot(x - cx, z - cz) < 46 for cx, cz in centres):
            continue
        if not spawn_clear(x, z, 8.0):
            continue
        centres.append((x, z))
    inside_corals, inside_weeds = 40, 27
    tries = 0
    while (len(coral_spots) < inside_corals or len(weed_spots) < inside_weeds) and tries < 200000:
        tries += 1
        cx, cz = centres[tries % len(centres)]
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0, 17)
        x, z = cx + math.cos(a) * rr, cz + math.sin(a) * rr
        if abs(x) > hx - 6 or abs(z) > hz - 6:
            continue
        if len(coral_spots) < inside_corals and (len(weed_spots) >= inside_weeds or rng.random() < 0.62):
            variant = 1 + len(coral_spots) % 6           # every variant in turn: an even mix
            scale = rng.uniform(0.8, 1.6) if tries % 40 else 0.8
            r = coral_radius[variant - 1] * scale
            top = coral_height[variant - 1] * scale
            if fossil_clear(x, z, r) and spawn_clear(x, z, top) and free(x, z, r):
                add_coral(x, z, variant, scale, rng.uniform(0, 2 * math.pi))
        else:
            h = rng.uniform(18, 40)
            if fossil_clear(x, z, 3) and spawn_clear(x, z, h) and free(x, z, 2.0):
                add_weed(x, z, h, rng.uniform(0, 2 * math.pi))
    # a few seaweed around the fossil, it looks long sunk
    for k in range(3):
        for _ in range(500):
            a = rng.uniform(0, 2 * math.pi)
            x = FOSSIL_AT[0] + math.cos(a) * rng.uniform(32, 44)
            z = FOSSIL_AT[2] + math.sin(a) * rng.uniform(32, 44)
            h = rng.uniform(18, 30)
            if abs(x) < hx - 6 and abs(z) < hz - 6 and fossil_clear(x, z, 3) and spawn_clear(x, z, h) and free(x, z, 2.0):
                add_weed(x, z, h, rng.uniform(0, 2 * math.pi))
                break
    # --- outside the arena, out to +-500: fewer and fewer further out, for the endless-ocean look
    out_corals, out_weeds = 20, 13
    n_c, n_w = len(coral_spots), len(weed_spots)
    tries = 0
    while (len(coral_spots) - n_c < out_corals or len(weed_spots) - n_w < out_weeds) and tries < 200000:
        tries += 1
        # a clump centre, then 1-3 items around it
        r = 175 + (325 * rng.random() ** 1.6)
        a = rng.uniform(0, 2 * math.pi)
        x, z = max(-500, min(500, math.cos(a) * r * 1.1)), max(-500, min(500, math.sin(a) * r))
        if abs(x) < hx + 18 and abs(z) < hz + 18:
            continue
        if math.hypot(x - ISLAND_AT[0], z - ISLAND_AT[1]) < 55:
            continue
        for _ in range(rng.choice((1, 2, 3))):
            px = max(-500.0, min(500.0, x + rng.uniform(-9, 9)))
            pz = max(-500.0, min(500.0, z + rng.uniform(-9, 9)))
            if len(coral_spots) - n_c < out_corals and (len(weed_spots) - n_w >= out_weeds or rng.random() < 0.6):
                variant = 1 + (len(coral_spots) - n_c + 3) % 6
                scale = rng.uniform(0.9, 1.6)
                if free(px, pz, coral_radius[variant - 1] * scale):
                    add_coral(px, pz, variant, scale, rng.uniform(0, 2 * math.pi))
            elif len(weed_spots) - n_w < out_weeds:
                if free(px, pz, 2.0):
                    add_weed(px, pz, rng.uniform(22, 40), rng.uniform(0, 2 * math.pi))
    fossil_spot = spot(FOSSIL_AT, rot)
    stats = {
        "corals_inside": sum(1 for s in coral_spots if abs(s["pos"][0]) <= hx and abs(s["pos"][2]) <= hz),
        "corals_outside": sum(1 for s in coral_spots if not (abs(s["pos"][0]) <= hx and abs(s["pos"][2]) <= hz)),
        "seaweed_inside": sum(1 for s in weed_spots if abs(s["pos"][0]) <= hx and abs(s["pos"][2]) <= hz),
        "seaweed_outside": sum(1 for s in weed_spots if not (abs(s["pos"][0]) <= hx and abs(s["pos"][2]) <= hz)),
        "variants": [sum(1 for s in coral_spots if s["variant"] == v) for v in range(1, 7)],
    }
    return fossil_spot, coral_spots, weed_spots, stats, fossil_world


# =========================================================================================== WEAPONS
# Every weapon: origin at the grip (where the right hand closes), barrel along -Z (the LookVector), no collision.
# Projectiles: origin at the point (harpoon tip, missile nose), flying along -Z.
STEEL = (196, 202, 212)
STEEL_LIGHT = (232, 236, 242)
STEEL_DARK = (120, 126, 138)
GUN_WOOD = (178, 112, 60)
GUN_WOOD_DARK = (122, 74, 40)
RUBBER = (40, 40, 46)
BAND = (255, 122, 24)
BRASS = (230, 184, 70)
OLIVE = (94, 116, 58)
OLIVE_DARK = (70, 88, 44)
HAZARD = ((252, 204, 36), (30, 30, 34))
MISSILE_WHITE = (242, 242, 236)
MISSILE_RED = (226, 44, 40)
BLACK = (34, 34, 38)


def ring(asset, group, centre, axis, radius, tube, color, mat="Metal", segments=8):
    """A small torus from short cylinders: `axis` is the ring's normal."""
    axis = norm(axis)
    u = norm(cross(axis, (0.0, 1.0, 0.0) if abs(axis[1]) < 0.9 else (1.0, 0.0, 0.0)))
    v = cross(axis, u)
    pts = [add(centre, add(mul(u, radius * math.cos(a)), mul(v, radius * math.sin(a))))
           for a in [2 * math.pi * k / segments for k in range(segments + 1)]]
    chain(asset, group, pts, [tube] * len(pts), color, mat, overlap=tube * 0.5)


def build_harpoon():
    """Harpoon (projectile alone): ~7.6 studs, steel shaft, a crossed spear point with four barbs, a ring at the back
    for the rope. Origin at the tip, flying along -Z."""
    h = Asset("Harpoon")
    g = "Harpoon"
    # spear point: two flat triangles crossed, tip on the origin
    for along in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        tooth(h, g, (0.0, 0.0, 1.0), (0.0, 0.0, -1.0), along, 1.0, 0.46, 0.12, STEEL_LIGHT)
    h.cylinder(g, (0.0, 0.0, 0.95), (0.0, 0.0, 1.3), 0.34, STEEL_DARK, "Metal", collide=False)
    # barbs: four slim hooks folded back from just behind the point
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        out = (math.cos(a), math.sin(a), 0.0)
        d = norm(add(mul(out, 0.42), (0.0, 0.0, 1.0)))
        base = add((0.0, 0.0, 1.25), mul(out, 0.12))
        tooth(h, g, base, d, norm(cross(out, (0.0, 0.0, 1.0))), 0.95, 0.24, 0.07, STEEL_LIGHT)
    h.cylinder(g, (0.0, 0.0, 1.2), (0.0, 0.0, 7.0), 0.22, STEEL, "Metal", collide=False)
    # notches for the bands' wishbones, a strip of orange tape, the stop collar and the rope ring
    for z in (5.3, 6.0):
        h.box(g, (-0.07, 0.08, z), (0.07, 0.19, z + 0.22), STEEL_DARK, "Metal", collide=False)
    h.cylinder(g, (0.0, 0.0, 4.2), (0.0, 0.0, 4.55), 0.26, BAND, "Smooth", collide=False)
    h.cylinder(g, (0.0, 0.0, 6.9), (0.0, 0.0, 7.08), 0.32, STEEL_DARK, "Metal", collide=False)
    ring(h, g, (0.0, 0.0, 7.38), (1.0, 0.0, 0.0), 0.3, 0.1, BRASS)
    return h


HARPOON_RING = (0.0, 0.0, 7.38)


def build_harpoon_gun(harpoon):
    """Band speargun, 6 studs from butt to muzzle (the loaded harpoon pokes 1.6 further): wooden stock, metal rail
    and muzzle, two orange bands stretched back to the shaft. Group "Harpoon" is the loaded harpoon."""
    gun = Asset("HarpoonGun")
    shaft_y = 1.42
    # pistol grip and trigger
    gun.prim("Stock", "Block", (0.44, 1.35, 0.62), (0.0, -0.02, 0.06), rot_x(math.radians(-14)), GUN_WOOD_DARK, "Wood", collide=False)
    gun.prim("Stock", "Block", (0.5, 0.18, 0.72), (0.0, -0.7, 0.24), rot_x(math.radians(-14)), RUBBER, "Smooth", collide=False)
    for k in range(3):
        gun.cylinder("Stock", (-0.23, 0.32 - k * 0.32, -0.3 + k * 0.08), (0.23, 0.32 - k * 0.32, -0.3 + k * 0.08), 0.18,
                     GUN_WOOD, "Wood", collide=False)
    gun.prim("Metal", "Block", (0.1, 0.42, 0.12), (0.0, 0.43, -0.46), rot_x(math.radians(18)), STEEL_DARK, "Metal", collide=False)
    gun.box("Metal", (-0.06, 0.12, -0.92), (0.06, 0.22, -0.2), STEEL, "Metal", collide=False)
    gun.box("Metal", (-0.06, 0.12, -0.92), (0.06, 0.62, -0.82), STEEL, "Metal", collide=False)
    # stock: the long wooden body, a slimmer keel under its front, the rubber butt
    gun.box("Stock", (-0.28, 0.6, -4.3), (0.28, 1.24, 1.35), GUN_WOOD, "Wood", collide=False)
    gun.box("Stock", (-0.2, 0.42, -4.1), (0.2, 0.62, -0.95), GUN_WOOD_DARK, "Wood", collide=False)
    gun.prim("Stock", "Wedge", (0.4, 0.18, 0.6), (0.0, 0.51, -0.65), rot_y(math.pi), GUN_WOOD_DARK, "Wood", collide=False)
    gun.box("Stock", (-0.31, 0.56, 1.35), (0.31, 1.28, 1.62), RUBBER, "Smooth", collide=False)
    for z in (-3.4, -2.2, 0.6):
        for sx in (-1, 1):
            gun.cylinder("Metal", (sx * 0.27, 0.92, z), (sx * 0.31, 0.92, z), 0.16, BRASS, "Metal", collide=False)
    # rail on top, muzzle head with the band holes and the shaft guide
    gun.box("Metal", (-0.11, 1.24, -4.3), (0.11, 1.32, 0.9), STEEL, "Metal", collide=False)
    gun.box("Metal", (-0.42, 0.56, -4.82), (0.42, 1.36, -4.3), STEEL, "Metal", collide=False)
    for sx in (-1, 1):
        gun.cylinder("Metal", (sx * 0.38, 0.86, -4.56), (sx * 0.46, 0.86, -4.56), 0.3, RUBBER, "Smooth", collide=False)
    gun.cylinder("Metal", (0.0, shaft_y, -4.86), (0.0, shaft_y, -4.3), 0.44, STEEL_DARK, "Metal", collide=False)
    # two bands: from the muzzle sides back to wishbones hooked on the shaft's notches
    for z_hook, y_side in ((-1.15, 0.92), (-1.85, 0.8)):
        for sx in (-1, 1):
            gun.cylinder("Bands", (sx * 0.44, y_side, -4.5), (sx * 0.12, shaft_y + 0.1, z_hook), 0.2, BAND, "Smooth", collide=False)
        gun.cylinder("Bands", (-0.15, shaft_y + 0.12, z_hook), (0.15, shaft_y + 0.12, z_hook), 0.1, STEEL, "Metal", collide=False)
    # line reel under the stock
    gun.box("Metal", (-0.05, 0.3, -1.95), (0.05, 0.6, -1.75), STEEL_DARK, "Metal", collide=False)
    gun.cylinder("Metal", (-0.2, 0.2, -1.85), (0.2, 0.2, -1.85), 0.62, STEEL, "Metal", collide=False)
    gun.cylinder("Metal", (-0.21, 0.2, -1.85), (0.21, 0.2, -1.85), 0.48, (246, 214, 52), "Smooth", collide=False)
    # the loaded harpoon lies in the rail, its point 1.6 studs past the muzzle
    tip = (0.0, shaft_y, -6.45)
    start = len(gun.prims)
    gun.place(harpoon, tip)
    for p in gun.prims[start:]:
        p["group"] = "Harpoon"
    spots = {"Muzzle": spot((0.0, shaft_y, -4.86), IDENT), "HarpoonTip": spot(tip, IDENT),
             "RopeAttach": spot(add(tip, HARPOON_RING), IDENT)}
    return gun, spots


def build_missile():
    """Missile (projectile alone): 4 studs, red ogive nose, white body with a red band, four red tail fins and a dark
    nozzle with a hot glow. Origin at the nose, flying along -Z."""
    m = Asset("Missile")
    g = "Missile"
    m.prim(g, "Ball", (0.3, 0.3, 0.3), (0.0, 0.0, 0.15), IDENT, MISSILE_RED, "Smooth", collide=False)
    for z0, z1, d in ((0.08, 0.32, 0.36), (0.3, 0.56, 0.54), (0.54, 0.86, 0.68)):
        m.cylinder(g, (0.0, 0.0, z0), (0.0, 0.0, z1), d, MISSILE_RED, "Smooth", collide=False)
    m.cylinder(g, (0.0, 0.0, 0.84), (0.0, 0.0, 3.4), 0.74, MISSILE_WHITE, "Smooth", collide=False)
    m.cylinder(g, (0.0, 0.0, 1.5), (0.0, 0.0, 1.78), 0.76, MISSILE_RED, "Smooth", collide=False)
    m.cylinder(g, (0.0, 0.0, 2.3), (0.0, 0.0, 2.38), 0.76, (40, 40, 44), "Smooth", collide=False)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        out = (math.cos(a), math.sin(a), 0.0)
        back = (0.0, 0.0, 1.0)
        rot = from_axes(norm(cross(out, back)), out, back)
        m.prim(g, "Wedge", (0.08, 0.26, 0.95), add(mul(out, 0.37 + 0.13), (0.0, 0.0, 2.95)), rot, MISSILE_RED, "Smooth", collide=False)
    m.cylinder(g, (0.0, 0.0, 3.38), (0.0, 0.0, 3.78), 0.52, STEEL_DARK, "Metal", collide=False)
    m.cylinder(g, (0.0, 0.0, 3.78), (0.0, 0.0, 3.82), 0.36, (255, 150, 40), "Neon", collide=False)
    return m


MISSILE_EXHAUST = (0.0, 0.0, 3.82)


def build_bazooka(missile):
    """Cartoon shoulder rocket launcher, 6.6 studs from muzzle to exhaust: olive tube with yellow and black hazard bands, flared muzzle and
    exhaust, pistol and front grips, shoulder pad, side sight. Group "Missile" is the loaded missile."""
    b = Asset("Bazooka")
    y = 0.95
    b.cylinder("Tube", (0.0, y, -2.9), (0.0, y, 2.75), 1.3, OLIVE, "Smooth", collide=False)
    for k in range(5):                                   # hazard bands behind the muzzle
        z0 = -2.78 + k * 0.22
        b.cylinder("Tube", (0.0, y, z0), (0.0, y, z0 + 0.22), 1.36, HAZARD[k % 2], "Smooth", collide=False)
    b.cylinder("Tube", (0.0, y, 1.8), (0.0, y, 2.1), 1.36, HAZARD[0], "Smooth", collide=False)
    b.cylinder("Tube", (0.0, y, -3.36), (0.0, y, -2.85), 1.62, OLIVE_DARK, "Smooth", collide=False)
    b.cylinder("Tube", (0.0, y, -3.38), (0.0, y, -3.34), 1.14, (24, 24, 26), "Smooth", collide=False)
    b.cylinder("Tube", (0.0, y, 2.7), (0.0, y, 3.22), 1.78, (72, 72, 78), "Metal", collide=False)
    b.cylinder("Tube", (0.0, y, 3.22), (0.0, y, 3.26), 1.3, (24, 24, 26), "Smooth", collide=False)
    # grips, trigger, shoulder pad
    b.prim("Grip", "Block", (0.42, 1.1, 0.56), (0.0, 0.0, 0.05), rot_x(math.radians(-12)), BLACK, "Smooth", collide=False)
    b.prim("Grip", "Block", (0.1, 0.36, 0.12), (0.0, 0.42, -0.4), rot_x(math.radians(18)), MISSILE_RED, "Smooth", collide=False)
    b.box("Grip", (-0.06, 0.1, -0.82), (0.06, 0.2, -0.2), (60, 60, 66), "Metal", collide=False)
    b.box("Grip", (-0.06, 0.1, -0.82), (0.06, 0.4, -0.72), (60, 60, 66), "Metal", collide=False)
    b.box("Grip", (-0.18, 0.28, -0.25), (0.18, 0.34, 0.35), (60, 60, 66), "Metal", collide=False)
    b.prim("Grip", "Block", (0.36, 0.95, 0.42), (0.0, 0.0, -1.7), rot_x(math.radians(-6)), BLACK, "Smooth", collide=False)
    b.box("Grip", (-0.18, 0.26, -1.95), (0.18, 0.32, -1.45), (60, 60, 66), "Metal", collide=False)
    b.box("Grip", (-0.34, 0.12, 0.85), (0.34, 0.42, 1.95), BLACK, "Smooth", collide=False)
    # carrying handle on top and the side sight
    b.box("Tube", (-0.08, y + 0.6, 0.55), (0.08, y + 0.95, 0.7), (60, 60, 66), "Metal", collide=False)
    b.box("Tube", (-0.08, y + 0.6, 1.45), (0.08, y + 0.95, 1.6), (60, 60, 66), "Metal", collide=False)
    b.box("Tube", (-0.1, y + 0.9, 0.55), (0.1, y + 1.04, 1.6), BLACK, "Smooth", collide=False)
    b.box("Sight", (-0.66, y + 0.1, -1.0), (-0.5, y + 0.55, -0.6), (60, 60, 66), "Metal", collide=False)
    b.cylinder("Sight", (-0.72, y + 0.62, -1.55), (-0.72, y + 0.62, -0.1), 0.36, (54, 54, 60), "Metal", collide=False)
    b.cylinder("Sight", (-0.72, y + 0.62, -1.6), (-0.72, y + 0.62, -1.54), 0.3, (110, 220, 255), "Glass", collide=False)
    b.cylinder("Sight", (-0.72, y + 0.62, -0.11), (-0.72, y + 0.62, -0.05), 0.3, (255, 70, 60), "Neon", collide=False)
    b.box("Sight", (-0.05, y + 0.62, -2.5), (0.05, y + 0.9, -2.4), (60, 60, 66), "Metal", collide=False)
    # the loaded missile, its nose just out of the muzzle
    nose = (0.0, y, -3.5)
    start = len(b.prims)
    b.place(missile, nose)
    for p in b.prims[start:]:
        p["group"] = "Missile"
    spots = {"Muzzle": spot((0.0, y, -3.38), IDENT), "MissileNose": spot(nose, IDENT),
             "Backblast": spot((0.0, y, 3.26), rot_y(math.pi))}
    return b, spots


def build_weapons():
    harpoon = build_harpoon()
    missile = build_missile()
    gun, gun_spots = build_harpoon_gun(harpoon)
    bazooka, bazooka_spots = build_bazooka(missile)
    spots = {
        "v": 1,
        "note": "local coordinates of each model; origin = grip (guns) or point (projectiles); barrels and flights along -Z",
        "HarpoonGun": gun_spots,
        "Harpoon": {"Tip": spot((0.0, 0.0, 0.0), IDENT), "RopeAttach": spot(HARPOON_RING, IDENT)},
        "Bazooka": bazooka_spots,
        "Missile": {"Nose": spot((0.0, 0.0, 0.0), IDENT), "Exhaust": spot(MISSILE_EXHAUST, rot_y(math.pi))},
    }
    return {"HarpoonGun": gun, "Harpoon": harpoon, "Bazooka": bazooka, "Missile": missile}, spots
