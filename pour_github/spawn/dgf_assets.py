"""Don't Get Fished - block assets (pirate ship spawn, trees) described as Roblox primitives.

Everything is in Roblox studs (Y up). The ship's bow points to -Z and its starboard side (+X) is the
side that faces the map (that is where the walk-the-plank boards are).

Each primitive is a dict:
    asset, group, shape (Block | Wedge | Cylinder | Ball), size (x, y, z), pos (x, y, z),
    rot (3x3, rows; columns are the part's Right / Up / Back vectors, like a Roblox CFrame),
    color (r, g, b 0-255), mat (Stud | Smooth | Glass | Neon), transparency, collide
Groups the Roblox importer treats specially: Barrier (invisible wall), SpawnPoint (invisible
marker), Lantern (neon light), Flag (gets the Jolly Roger decal).
"""
import math
import random

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


def norm(a):
    length = math.sqrt(dot(a, a))
    return mul(a, 1.0 / length) if length > 1e-9 else (0.0, 0.0, 0.0)


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


VERTICAL = axis_x_rot((0.0, 1.0, 0.0))   # for upright cylinders (masts, barrels)


def lerp(a, b, t):
    return a + (b - a) * t


def shade(color, f):
    return tuple(max(0, min(255, int(round(c * f)))) for c in color)


# --------------------------------------------------------------------------------- primitives
PRIMS = []


def prim(asset, group, shape, size, pos, rot=IDENT, color=(255, 255, 255), mat="Stud", transparency=0.0,
         collide=True):
    p = dict(asset=asset, group=group, shape=shape, size=tuple(size), pos=tuple(pos), rot=rot, color=tuple(color),
             mat=mat, transparency=transparency, collide=collide)
    PRIMS.append(p)
    return p


def mirrored(p):
    """Copy of a primitive mirrored across the ship's centre plane (x -> -x)."""
    r = p["rot"]
    sign = (-1, 1, 1)
    rot = tuple(tuple(r[i][j] * sign[i] * sign[j] for j in range(3)) for i in range(3))
    q = dict(p)
    q["pos"] = (-p["pos"][0], p["pos"][1], p["pos"][2])
    q["rot"] = rot
    PRIMS.append(q)
    return q


def both(p):
    mirrored(p)
    return p


def segment_box(asset, group, a, b, thickness, height, color, mat="Stud", collide=True, inward=None):
    """Vertical board between two points a, b of the (x, z) plane, offset `thickness` towards `inward`."""
    (x0, y0, z0), (x1, _, z1) = a, b
    t = norm((x1 - x0, 0.0, z1 - z0))
    n = (t[2], 0.0, -t[0])                      # normal on the starboard (+x) side of the direction
    if inward is not None and dot(n, inward) > 0:
        n = mul(n, -1)
    length = math.hypot(x1 - x0, z1 - z0) + 0.35
    mid = ((x0 + x1) / 2, y0 + height / 2, (z0 + z1) / 2)
    centre = sub(mid, mul(n, thickness / 2))    # board sits on the inner side of the line
    rot = from_axes(n, (0.0, 1.0, 0.0), cross(n, (0.0, 1.0, 0.0)))
    return prim(asset, group, "Block", (thickness, height, length), centre, rot, color, mat, collide=collide)


def rope(asset, a, b, thickness=0.25, color=(58, 44, 34)):
    d = sub(b, a)
    return prim(asset, "Rope", "Block", (thickness, thickness, math.sqrt(dot(d, d))), mul(add(a, b), 0.5),
                look_rot(d), color, "Smooth", collide=False)


def cylinder(asset, group, a, b, diameter, color, mat="Smooth", collide=True):
    d = sub(b, a)
    return prim(asset, group, "Cylinder", (math.sqrt(dot(d, d)), diameter, diameter), mul(add(a, b), 0.5),
                axis_x_rot(d), color, mat, collide=collide)


# =========================================================================================== SHIP
SHIP = "Ship"
B = 17.0                       # half beam at deck level (outer surface)
BOW, STERN = -54.0, 50.0
T = 1.4                        # hull plank thickness
FORE_Z, STERN_DECK_Z = -36.0, 30.0   # forecastle / quarterdeck boundaries
PLANKS_Z = (-13.5, 0.0, 13.5)  # walk-the-plank boards on the starboard (+x) side
CANNONS_Z = (-20.0, -7.0, 7.0, 20.0)
HATCH = (-3.0, 3.0, 12.0, 29.0)  # x0, x1, z0, z1 of the stairwell to the hold
HOLD_FLOOR = -12.0
HOLD_Z = (-32.0, 36.0)
GLASS = (-9.0, 9.0, -28.0, 8.0)

HULL = (98, 57, 32)
HULL_DARK = (78, 45, 26)
WALE = (142, 42, 34)
BULWARK = (122, 74, 41)
GOLD = (232, 184, 66)
DECK = ((174, 110, 61), (162, 100, 55), (186, 121, 67), (168, 106, 58))
MAST = (122, 78, 42)
SAIL = ((247, 239, 218), (239, 230, 207), (244, 235, 212), (236, 226, 201))
IRON = (44, 44, 50)
GLASS_TINT = (190, 232, 255)
LANTERN = (255, 198, 96)

rng = random.Random(1717)


def W(z):
    """Outer half-width of the hull at deck level."""
    if z < -20.0:
        t = min(1.0, (-20.0 - z) / 34.0)
        return B * max(0.0, math.cos(t * math.pi / 2)) ** 0.8
    if z > 26.0:
        t = (z - 26.0) / 24.0
        return B * (1.0 - 0.3 * t * t)
    return B


def g(y):
    """Tumblehome: the hull gets narrower towards its bottom."""
    if y >= 0:
        return 1.0 - 0.02 * y / 4.0
    s = min(1.0, -y / 14.0)
    return 1.0 - 0.24 * s ** 1.6


def hull_x(z, y):
    return W(z) * g(y)


def bottom_y(z):
    if z < -32.0:
        t = (-32.0 - z) / 22.0
        return -14.0 + 12.0 * t * t
    if z > 38.0:
        t = (z - 38.0) / 12.0
        return -14.0 + 5.0 * t * t
    return -14.0


def sheer_top(z):
    if z < FORE_Z:
        return 8.0
    if z > STERN_DECK_Z:
        return 12.0
    return 4.0


BOW_Z = [-54.0, -51.0, -48.0, -45.0, -42.0, -39.0, -36.0, -32.0, -28.0, -24.0, -20.0]
STERN_ZS = [26.0, 30.0, 34.0, 38.0, 42.0, 46.0, 50.0]


def z_segments(gaps=()):
    """Consecutive (z0, z1) pieces along the hull, leaving out the given z gaps."""
    pieces = []
    zs = BOW_Z + STERN_ZS
    for z0, z1 in zip(zs[:-1], zs[1:]):
        if z0 == -20.0 and z1 == 26.0:
            continue
        pieces.append((z0, z1))
    mid = [(-20.0, 26.0)]
    for g0, g1 in sorted(gaps):
        nxt = []
        for a, b in mid:
            if g1 <= a or g0 >= b:
                nxt.append((a, b))
                continue
            if g0 > a:
                nxt.append((a, g0))
            if g1 < b:
                nxt.append((g1, b))
        mid = nxt
    return sorted(pieces + mid)


def strake_color(k, z):
    if k == 0:
        base = HULL_DARK
    elif k == 6:
        base = WALE
    elif k >= 7:
        base = BULWARK
    else:
        base = HULL if k % 2 else shade(HULL, 1.08)
    return shade(base, 1.0 + rng.uniform(-0.04, 0.04))


def build_hull():
    plank_gaps = [(z - 2.0, z + 2.0) for z in PLANKS_Z]
    for side in (1, -1):
        for k in range(13):                     # strakes 2 studs tall from y=-14 up to y=12
            ya, yb = -14.0 + 2 * k, -12.0 + 2 * k
            gaps = plank_gaps if (side == 1 and ya >= 0.0 and yb <= 4.0) else ()
            for z0, z1 in z_segments(gaps):
                zm = (z0 + z1) / 2
                if yb > sheer_top(zm) + 1e-6 or yb <= bottom_y(zm) + 0.6:
                    continue
                ym = (ya + yb) / 2
                w0, w1 = hull_x(z0, ym), hull_x(z1, ym)
                if max(w0, w1) < 0.6:
                    continue
                color = strake_color(k, zm)
                p = segment_box(SHIP, "Hull", (side * w0, ya, z0), (side * w1, ya, z1), T, 2.0, color,
                                inward=(-side, 0, 0))
                p["collide"] = True
        # gold cap rail on top of the bulwarks
        for z0, z1 in z_segments(plank_gaps if side == 1 else ()):
            zm = (z0 + z1) / 2
            top = sheer_top(zm)
            w0, w1 = hull_x(z0, top), hull_x(z1, top)
            if max(w0, w1) < 0.6:
                continue
            p = segment_box(SHIP, "Trim", (side * (w0 + 0.25), top, z0), (side * (w1 + 0.25), top, z1), 1.9, 0.6,
                            shade(GOLD, 1.0 + rng.uniform(-0.03, 0.03)), inward=(-side, 0, 0))

    # stem post at the bow and the flat transom at the stern
    prim(SHIP, "Hull", "Block", (1.8, 11.0, 1.8), (0.0, 2.6, BOW + 0.4), color=HULL_DARK)
    prim(SHIP, "Trim", "Block", (2.0, 0.6, 2.0), (0.0, 8.4, BOW + 0.4), color=GOLD)
    for k in range(13):
        ya, yb = -14.0 + 2 * k, -12.0 + 2 * k
        if yb <= bottom_y(STERN) + 0.6 or yb > 12.0 + 1e-6:
            continue
        w = hull_x(STERN, (ya + yb) / 2)
        prim(SHIP, "Hull", "Block", (2 * w, 2.0, T), (0.0, (ya + yb) / 2, STERN - T / 2), color=strake_color(k, STERN))
    prim(SHIP, "Trim", "Block", (2 * hull_x(STERN, 12) + 0.6, 0.6, 1.9), (0.0, 12.3, STERN - 0.7), color=GOLD)
    # captain's windows on the transom
    for x in (-7.5, -2.5, 2.5, 7.5):
        prim(SHIP, "Window", "Block", (3.4, 4.0, 0.3), (x, 4.0, STERN + 0.05), color=LANTERN, mat="Neon",
             collide=False, transparency=0.15)
        prim(SHIP, "Trim", "Block", (4.0, 0.5, 0.5), (x, 6.2, STERN + 0.15), color=GOLD, collide=False)
        prim(SHIP, "Trim", "Block", (4.0, 0.5, 0.5), (x, 1.8, STERN + 0.15), color=GOLD, collide=False)

    # bottom boards where the hull is closed (bow and stern, outside the hold)
    for z0, z1 in z_segments():
        zm = (z0 + z1) / 2
        if HOLD_Z[0] <= zm <= HOLD_Z[1]:
            continue
        by = bottom_y(zm)
        w = min(hull_x(z0, by + 0.5), hull_x(z1, by + 0.5))
        if w < 0.8:
            continue
        prim(SHIP, "Hull", "Block", (2 * w, 1.0, abs(z1 - z0) + 0.3), (0.0, by + 0.5, zm), color=HULL_DARK)

    # portholes into the hold and painted gunports, on both sides
    for z in (-26.0, -16.0, -6.0, 4.0, 14.0, 24.0, 32.0):
        x = hull_x(z, -7.0) + 0.1
        both(cylinder(SHIP, "Trim", (x - 0.3, -7.0, z), (x + 0.2, -7.0, z), 2.3, GOLD, collide=False))
        both(cylinder(SHIP, "Glass", (x - 0.35, -7.0, z), (x + 0.25, -7.0, z), 1.6, GLASS_TINT, mat="Glass",
                      collide=False))
    for z in (-21.0, -11.0, -1.0, 9.0, 19.0, 29.0):
        x = hull_x(z, -4.0) + 0.12
        both(prim(SHIP, "Trim", "Block", (0.3, 2.2, 2.2), (x, -4.0, z), color=(30, 24, 22), collide=False))
        lid = rot_z(math.radians(35))           # lid propped open, swinging outwards
        hinge = (x + 0.05, -2.9, z)
        both(prim(SHIP, "Trim", "Block", (0.3, 2.3, 2.5), add(hinge, apply(lid, (0.0, -1.15, 0.0))), lid,
                  color=WALE, collide=False))


def deck_rows(y_mid, z_min, z_max, x_range=16, holes=()):
    """Plank rows (x centre, z0, z1) covering the hull's inner outline at height y_mid."""
    rows = []
    steps = int((z_max - z_min) / 0.25)
    zs = [z_min + 0.25 * k for k in range(steps + 1)] + [z_max]
    for xc in range(-x_range, x_range + 1, 2):
        start = None
        last_inside = None
        for z in zs:
            # rows may run into the hull planks so no gap is left along the walls
            inside = hull_x(z, y_mid) - T + 1.2 >= abs(xc) + 1.0
            for hx0, hx1, hz0, hz1 in holes:
                if hx0 - 1e-6 <= xc - 1.0 and xc + 1.0 <= hx1 + 1e-6 and hz0 < z < hz1:
                    inside = False
            if inside:
                if start is None:
                    start = z
                last_inside = z
            elif start is not None:
                if z - start > 0.5:
                    rows.append((xc, start, z))
                start = None
        if start is not None and last_inside - start > 0.5:
            rows.append((xc, start, last_inside))
    return rows


def lay_planks(group, y_top, rows, palette):
    for xc, z0, z1 in rows:
        z = z0
        while z < z1 - 0.1:
            length = min(z1 - z, rng.uniform(6.0, 13.0))
            if z1 - (z + length) < 2.0:
                length = z1 - z
            color = shade(rng.choice(palette), 1.0 + rng.uniform(-0.03, 0.03))
            prim(SHIP, group, "Block", (2.0, 1.0, length + 0.02), (xc, y_top - 0.5, z + length / 2), color=color)
            z += length


def railing(a, b, y0, height, post_every=3.0, gaps=()):
    """Posts + top rail from point a to b (x, z) at floor height y0, skipping gaps (start, end) along it."""
    ax, az = a
    bx, bz = b
    length = math.hypot(bx - ax, bz - az)
    d = ((bx - ax) / length, (bz - az) / length)
    n_posts = max(1, int(round(length / post_every)))
    pieces = [(0.0, length)]
    for g0, g1 in gaps:
        nxt = []
        for s0, s1 in pieces:
            if g1 <= s0 or g0 >= s1:
                nxt.append((s0, s1))
                continue
            if g0 > s0:
                nxt.append((s0, g0))
            if g1 < s1:
                nxt.append((g1, s1))
        pieces = nxt
    for s0, s1 in pieces:
        p0 = (ax + d[0] * s0, y0, az + d[1] * s0)
        p1 = (ax + d[0] * s1, y0, az + d[1] * s1)
        count = max(1, int(round((s1 - s0) / post_every)))
        for i in range(count + 1):
            t = i / count
            p = (lerp(p0[0], p1[0], t), y0 + height / 2, lerp(p0[2], p1[2], t))
            prim(SHIP, "Rail", "Block", (0.6, height, 0.6), p, color=BULWARK)
        mid = ((p0[0] + p1[0]) / 2, y0 + height - 0.2, (p0[2] + p1[2]) / 2)
        prim(SHIP, "Rail", "Block", (0.5, 0.5, (s1 - s0) + 0.6), mid, look_rot((p1[0] - p0[0], 0.0, p1[2] - p0[2])),
             color=GOLD)


def stairs(x0, x1, z_low, z_high, y_bottom, steps, rise=1.0, palette=DECK):
    """Solid steps climbing from z_low (first step) towards z_high (last step)."""
    run = (z_high - z_low) / steps
    for k in range(1, steps + 1):
        za = z_low + (k - 1) * run
        top = y_bottom + k * rise
        prim(SHIP, "Stairs", "Block", (x1 - x0, top - y_bottom, abs(run) + 0.02),
             ((x0 + x1) / 2, (top + y_bottom) / 2, za + run / 2), color=shade(rng.choice(palette), 0.95))


def build_decks():
    # main deck (open part between the castles), with the stairwell hole
    lay_planks("Deck", 0.0, deck_rows(-0.5, FORE_Z, STERN_DECK_Z, holes=[HATCH]), DECK)
    # forecastle and quarterdeck decks
    lay_planks("Deck", 5.0, deck_rows(4.5, BOW + 1.0, FORE_Z + 0.8), DECK)
    lay_planks("Deck", 8.0, deck_rows(7.5, STERN_DECK_Z - 0.8, STERN - 0.5), DECK)

    # walls under the castles (cabins are closed: doors and windows are decorative)
    for y0, y1 in ((0.0, 2.0), (2.0, 4.0)):
        w = hull_x(FORE_Z, (y0 + y1) / 2) - T + 0.3
        prim(SHIP, "Hull", "Block", (2 * w, y1 - y0, 0.8), (0.0, (y0 + y1) / 2, FORE_Z - 0.4), color=BULWARK)
    for y0, y1 in ((0.0, 2.0), (2.0, 4.0), (4.0, 6.0), (6.0, 7.0)):
        w = hull_x(STERN_DECK_Z, (y0 + y1) / 2) - T + 0.3
        prim(SHIP, "Hull", "Block", (2 * w, y1 - y0, 0.8), (0.0, (y0 + y1) / 2, STERN_DECK_Z + 0.4), color=BULWARK)
    # cabin doors and windows
    prim(SHIP, "Door", "Block", (3.2, 4.4, 0.3), (0.0, 2.2, FORE_Z + 0.05), color=(70, 40, 24))
    prim(SHIP, "Door", "Block", (3.4, 5.6, 0.3), (0.0, 2.8, STERN_DECK_Z - 0.05), color=(70, 40, 24))
    prim(SHIP, "Trim", "Ball", (0.5, 0.5, 0.5), (1.1, 2.8, STERN_DECK_Z - 0.3), color=GOLD, collide=False)
    for x in (-7.0, 7.0):
        prim(SHIP, "Window", "Block", (3.0, 3.0, 0.3), (x, 4.2, STERN_DECK_Z - 0.05), color=LANTERN, mat="Neon",
             transparency=0.15, collide=False)
        prim(SHIP, "Trim", "Block", (3.6, 0.45, 0.4), (x, 5.9, STERN_DECK_Z - 0.15), color=GOLD, collide=False)

    # stairs: main deck -> forecastle (two) and main deck -> quarterdeck (two), plus the stairwell to the hold
    for side in (1, -1):
        xa, xb = sorted((side * 5.0, side * 9.0))
        stairs(xa, xb, FORE_Z + 6.0, FORE_Z, 0.0, 5)
        xa, xb = sorted((side * 9.4, side * 13.4))
        stairs(xa, xb, STERN_DECK_Z - 8.0, STERN_DECK_Z, 0.0, 8)
    # stairwell down to the hold: solid steps standing on the hold floor, going down towards +z
    run = (HATCH[3] - HATCH[2]) / 12
    for k in range(1, 13):
        top = -k * 1.0
        za = HATCH[2] + (k - 1) * run
        prim(SHIP, "Stairs", "Block", (HATCH[1] - HATCH[0], top - (HOLD_FLOOR - 1.0), run + 0.02),
             (0.0, (top + HOLD_FLOOR - 1.0) / 2, za + run / 2), color=shade(rng.choice(DECK), 0.95))

    # railings: around the stairwell, along the castle edges
    railing((HATCH[0] - 0.4, HATCH[2]), (HATCH[0] - 0.4, HATCH[3] + 0.4), 0.0, 3.2)
    railing((HATCH[1] + 0.4, HATCH[2]), (HATCH[1] + 0.4, HATCH[3] + 0.4), 0.0, 3.2)
    railing((HATCH[0] - 0.4, HATCH[3] + 0.4), (HATCH[1] + 0.4, HATCH[3] + 0.4), 0.0, 3.2)
    wf = hull_x(FORE_Z, 5) - T
    railing((-wf, FORE_Z - 0.3), (wf, FORE_Z - 0.3), 5.0, 3.2, gaps=[(wf - 9.2, wf - 4.8), (wf + 4.8, wf + 9.2)])
    ws = hull_x(STERN_DECK_Z, 8) - T
    railing((-ws, STERN_DECK_Z + 0.3), (ws, STERN_DECK_Z + 0.3), 8.0, 3.2,
            gaps=[(ws - 13.6, ws - 9.2), (ws + 9.2, ws + 13.6)])


def build_hold():
    y = HOLD_FLOOR
    gx0, gx1, gz0, gz1 = GLASS
    # wooden floor around the glass
    for xc, z0, z1 in deck_rows(y - 0.5, HOLD_Z[0], HOLD_Z[1], x_range=14):
        segments = [(z0, z1)]
        if gx0 - 0.6 < xc < gx1 + 0.6:
            segments = [(a, b) for a, b in ((z0, gz0 - 0.5), (gz1 + 0.5, z1)) if b - a > 0.3]
        for a, b in segments:
            prim(SHIP, "Floor", "Block", (2.0, 1.0, b - a), (xc, y - 0.5, (a + b) / 2),
                 color=shade(rng.choice(DECK), 0.9))
    # glass panes in a wooden frame
    xs = (gx0, 0.0, gx1)
    zs = (gz0, -16.0, -4.0, gz1)
    for i in range(2):
        for j in range(3):
            x0, x1 = xs[i] + 0.5, xs[i + 1] - 0.5
            z0, z1 = zs[j] + 0.5, zs[j + 1] - 0.5
            prim(SHIP, "Glass", "Block", (x1 - x0, 1.0, z1 - z0), ((x0 + x1) / 2, y - 0.5, (z0 + z1) / 2),
                 color=GLASS_TINT, mat="Glass", transparency=0.55)
    for x in xs:
        prim(SHIP, "Floor", "Block", (1.0, 1.0, gz1 - gz0 + 1.0), (x, y - 0.5, (gz0 + gz1) / 2), color=MAST)
    for z in zs:
        prim(SHIP, "Floor", "Block", (gx1 - gx0 + 1.0, 1.0, 1.0), (0.0, y - 0.5, z), color=MAST)

    # bulkheads closing the hold at both ends
    for zb, off in ((HOLD_Z[0], -0.4), (HOLD_Z[1], 0.4)):
        for k in range(6):
            ya, yb = -13.0 + 2 * k, min(-1.0, -11.0 + 2 * k)
            w = hull_x(zb, (ya + yb) / 2) - T + 0.3
            prim(SHIP, "Hull", "Block", (2 * w, yb - ya, 0.8), (0.0, (ya + yb) / 2, zb + off), color=BULWARK)

    # ceiling beams under the deck (kept clear of the stairwell)
    for z in (-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0):
        w = hull_x(z, -1.5) - T + 0.3
        if HATCH[2] - 0.5 <= z <= HATCH[3] + 0.5:
            for a, b in ((-w, HATCH[0] - 0.5), (HATCH[1] + 0.5, w)):
                prim(SHIP, "Beam", "Block", (b - a, 1.0, 1.0), ((a + b) / 2, -1.5, z), color=MAST)
        else:
            prim(SHIP, "Beam", "Block", (2 * w, 1.0, 1.0), (0.0, -1.5, z), color=MAST)
    # pillars on the glass frame, hanging lanterns
    for x in (gx0, gx1):
        for z in (-16.0, -4.0):
            prim(SHIP, "Beam", "Block", (1.2, 10.0, 1.2), (x, -7.0, z), color=MAST)
    # lanterns on brackets along the hull walls (kept out of the middle, where the camera goes)
    for side in (1, -1):
        for z in (-22.0, -6.0, 10.0, 26.0):
            wall = hull_x(z, -5.0) - T
            prim(SHIP, "Trim", "Block", (1.6, 0.4, 0.4), (side * (wall - 0.7), -3.6, z), color=IRON, mat="Smooth",
                 collide=False)
            lantern(side * (wall - 1.3), -4.9, z, hanging=True)
    # cargo
    for x, z in ((-10.0, 33.0), (10.0, 33.0), (-10.5, -29.5), (10.5, -29.5), (9.5, 30.0)):
        barrel(x, y, z)
    for x, z in ((-10.0, 29.5), (10.5, 25.5), (-10.5, -26.0)):
        crate(x, y, z, 3.0)


def lantern(x, y, z, hanging=False):
    # indoor lanterns use a softer glow than the ones outside in the sun
    glow = (232, 168, 78) if hanging else LANTERN
    prim(SHIP, "Trim", "Block", (1.5, 0.35, 1.5), (x, y + 0.95, z), color=GOLD, collide=False)
    prim(SHIP, "Lantern", "Block", (1.0, 1.5, 1.0), (x, y, z), color=glow, mat="Neon", collide=False)
    prim(SHIP, "Trim", "Block", (1.5, 0.35, 1.5), (x, y - 0.95, z), color=GOLD, collide=False)


def barrel(x, y, z):
    prim(SHIP, "Cargo", "Cylinder", (3.2, 2.6, 2.6), (x, y + 1.6, z), VERTICAL, color=(150, 94, 50))
    for dy in (0.6, 2.6):
        prim(SHIP, "Cargo", "Cylinder", (0.3, 2.75, 2.75), (x, y + dy, z), VERTICAL, color=IRON, collide=False)


def crate(x, y, z, s):
    prim(SHIP, "Cargo", "Block", (s, s, s), (x, y + s / 2, z), rot_y(rng.uniform(-0.2, 0.2)), color=(190, 132, 72))


def cannon(side, z):
    x = side * 12.4
    car = (x, 0.7, z)
    prim(SHIP, "Cannon", "Block", (3.6, 1.4, 2.6), car, color=(120, 74, 40))
    for dx in (-1.2, 1.2):
        for dz in (-1.4, 1.4):
            prim(SHIP, "Cannon", "Cylinder", (0.5, 1.2, 1.2), (x + dx, 0.55, z + dz),
                 axis_x_rot((0.0, 0.0, 1.0)), color=(70, 44, 26), collide=False)
    a = (x - side * 1.0, 2.0, z)
    b = (x + side * 4.8, 2.0, z)               # pokes out through the bulwark
    cylinder(SHIP, "Cannon", a, b, 1.4, IRON, collide=True)
    cylinder(SHIP, "Cannon", (x + side * 4.6, 2.0, z), (x + side * 5.1, 2.0, z), 1.8, IRON, collide=False)
    prim(SHIP, "Cannon", "Ball", (0.9, 0.9, 0.9), (x - side * 1.3, 2.0, z), color=IRON, collide=False)
    # painted port around the barrel on the outside of the bulwark
    xo = side * (hull_x(z, 2.0) + 0.1)
    prim(SHIP, "Trim", "Block", (0.3, 2.6, 2.6), (xo, 2.0, z), color=(30, 24, 22), collide=False)


def mast(z, y_base, y_top, diameter, yards, sails):
    cylinder(SHIP, "Mast", (0.0, y_base, z), (0.0, y_top, z), diameter, MAST, collide=True)
    prim(SHIP, "Mast", "Block", (diameter + 0.6, 0.8, diameter + 0.6), (0.0, y_top + 0.4, z), color=GOLD,
         collide=False)
    for y, span in yards:                       # yards sit just in front of the mast, where the sails hang
        cylinder(SHIP, "Yard", (-span / 2, y, z - 1.0), (span / 2, y, z - 1.0), 1.0, MAST, collide=False)
        for s in (-1, 1):
            prim(SHIP, "Yard", "Block", (0.6, 0.6, 0.6), (s * span / 2, y, z - 1.0), color=GOLD, collide=False)
    for n_sail, (y0, y1, w_top, w_bottom, bulge) in enumerate(sails):
        # the cloth bellies forward (-z): strips follow the curve and are tilted along it so they join up
        strips = 6
        h = (y1 - y0) / strips

        def belly(t):
            return -bulge * math.sin(math.pi * t) - 1.0

        for i in range(strips):
            ta, tb = i / strips, (i + 1) / strips   # 0 at the yard, 1 at the foot of the sail
            za, zb = belly(ta), belly(tb)
            y = y1 - (i + 0.5) * h
            tilt = math.atan2(za - zb, h)           # local up axis runs from the lower edge to the upper one
            width = lerp(w_top, w_bottom, (ta + tb) / 2)
            length = math.hypot(h, zb - za) + 0.12
            color = SAIL[(n_sail + i // 2) % len(SAIL)]
            prim(SHIP, "Sail", "Block", (width, length, 0.35), (0.0, y, z + (za + zb) / 2), rot_x(tilt),
                 color=color, mat="Smooth", collide=False)


def pennant(pos, length, height, color):
    """Small triangular flag streaming towards -z from a pole at pos (two wedges)."""
    x, y, z = pos
    # upper half: wedge's right angle sits on the pole at the middle height
    prim(SHIP, "Pennant", "Wedge", (0.2, height / 2, length), (x, y + height / 4, z - length / 2),
         color=color, mat="Smooth", collide=False)
    flip = rot_z(math.pi)
    prim(SHIP, "Pennant", "Wedge", (0.2, height / 2, length), (x, y - height / 4, z - length / 2), flip,
         color=color, mat="Smooth", collide=False)


def build_rigging():
    # foremast, mainmast, mizzen
    mast(-24.0, HOLD_FLOOR, 50.0, 2.2, [(17.0, 26.0), (32.0, 21.0), (45.0, 14.0)],
         [(9.0, 16.6, 25.0, 27.0, 1.4), (17.6, 31.6, 20.0, 24.0, 1.3), (32.6, 44.6, 13.0, 18.0, 1.0)])
    mast(-2.0, HOLD_FLOOR, 64.0, 2.8, [(21.0, 32.0), (38.0, 27.0), (53.0, 19.0)],
         [(9.5, 20.6, 31.0, 33.0, 1.7), (21.6, 37.6, 26.0, 30.0, 1.6), (38.6, 52.6, 18.0, 24.0, 1.2)])
    # mizzen sails start 8 studs above the quarterdeck so avatars walk under them
    mast(42.0, 8.0, 48.0, 1.8, [(25.0, 18.0), (37.0, 14.0)],
         [(16.5, 24.6, 17.0, 19.0, 1.0), (25.6, 36.6, 13.0, 16.0, 0.9)])
    # crow's nest on the mainmast, above the highest yard
    prim(SHIP, "Mast", "Cylinder", (0.8, 7.0, 7.0), (0.0, 56.5, -2.0), VERTICAL, color=MAST, collide=False)
    for i in range(12):
        a = i / 12 * math.tau
        prim(SHIP, "Mast", "Block", (0.4, 1.6, 1.9), (3.2 * math.cos(a), 57.7, -2.0 + 3.2 * math.sin(a)),
             rot_y(-a), color=BULWARK, collide=False)
    # Jolly Roger on top of the mainmast + pennants
    cylinder(SHIP, "Mast", (0.0, 64.0, -2.0), (0.0, 69.0, -2.0), 0.45, MAST, collide=False)
    prim(SHIP, "Flag", "Block", (0.25, 6.6, 10.0), (0.0, 65.6, -2.0 - 0.25 - 5.0), color=(22, 22, 26), mat="Smooth",
         collide=False)
    pennant((0.0, 49.0, -24.0 - 0.6), 5.0, 2.0, (205, 50, 42))
    pennant((0.0, 47.0, 42.0 - 0.5), 4.0, 1.8, (205, 50, 42))
    # bowsprit
    cylinder(SHIP, "Mast", (0.0, 5.0, BOW + 3.0), (0.0, 13.0, BOW - 20.0), 1.6, MAST, collide=False)
    # shrouds and stays
    for z_m, y_top in ((-24.0, 44.0), (-2.0, 52.0), (42.0, 36.0)):
        for side in (1, -1):
            for dz in (-3.0, 0.0, 3.0):
                z = z_m + dz
                top = sheer_top(z)
                rope(SHIP, (side * 0.8, y_top, z_m), (side * (hull_x(z, top) - 0.4), top + 0.6, z))
    rope(SHIP, (0.0, 63.0, -2.0), (0.0, 49.0, -24.0))
    rope(SHIP, (0.0, 49.0, -24.0), (0.0, 13.0, BOW - 20.0))
    rope(SHIP, (0.0, 47.0, 42.0), (0.0, 55.0, -2.0))
    rope(SHIP, (0.0, 47.0, 42.0), (0.0, 12.6, STERN - 1.0))


def build_deck_props():
    for side in (1, -1):
        for z in CANNONS_Z:
            cannon(side, z)
    # steering wheel on the quarterdeck
    prim(SHIP, "Wheel", "Block", (1.2, 3.0, 1.2), (0.0, 9.5, 36.0), color=MAST)
    wc = (0.0, 11.4, 35.3)
    for i in range(12):
        a = i / 12 * math.tau
        prim(SHIP, "Wheel", "Block", (1.1, 0.35, 0.35), (wc[0] + 2.0 * math.cos(a), wc[1] + 2.0 * math.sin(a), wc[2]),
             rot_z(a + math.pi / 2), color=(150, 92, 48), collide=False)
    for i in range(8):
        a = i / 8 * math.tau
        p = (wc[0] + 1.3 * math.cos(a), wc[1] + 1.3 * math.sin(a), wc[2])
        prim(SHIP, "Wheel", "Block", (2.9, 0.25, 0.25), p, rot_z(a), color=(150, 92, 48), collide=False)
    prim(SHIP, "Wheel", "Cylinder", (0.6, 1.0, 1.0), wc, axis_x_rot((0.0, 0.0, 1.0)), color=GOLD, collide=False)
    # stern lanterns, barrels, crates, a treasure chest
    for side in (1, -1):
        x = side * (hull_x(48.5, 12) - 0.9)
        prim(SHIP, "Trim", "Block", (0.5, 2.0, 0.5), (x, 13.6, 48.5), color=IRON, collide=False)
        lantern(x, 15.4, 48.5)
    for x, z in ((-10.5, -33.0), (10.5, -33.0), (-6.0, 27.0)):
        barrel(x, 0.0, z)
    for x, z in ((10.0, -29.0), (-10.0, -29.5)):
        crate(x, 0.0, z, 2.6)
    prim(SHIP, "Cargo", "Block", (4.0, 2.2, 2.6), (6.0, 9.1, 46.5), color=(118, 70, 36))
    prim(SHIP, "Cargo", "Block", (4.2, 0.9, 2.8), (6.0, 10.6, 46.5), color=(104, 60, 30))
    prim(SHIP, "Trim", "Block", (4.3, 0.4, 0.4), (6.0, 10.0, 45.2), color=GOLD, collide=False)
    # walk-the-plank boards
    for z in PLANKS_Z:
        prim(SHIP, "Plank", "Block", (18.5, 0.8, 3.0), (12.3 + 9.25, 0.4, z), color=(176, 116, 64))
        for dz in (-1.0, 1.0):
            prim(SHIP, "Plank", "Wedge", (0.6, 3.0, 3.0), (hull_x(z, -1.5) + 1.3, -1.6, z + dz),
                 rot_y(-math.pi / 2), color=BULWARK, collide=False)


def build_barriers():
    """Invisible walls hugging the hull (and the planks) so nobody falls off the floating ship."""
    plank_gaps = [(z - 2.0, z + 2.0) for z in PLANKS_Z]
    y0, h = -0.5, 36.0
    for side in (1, -1):
        for z0, z1 in z_segments(plank_gaps if side == 1 else ()):
            w0, w1 = W(z0) + 1.2, W(z1) + 1.2
            p = segment_box(SHIP, "Barrier", (side * w0, y0, z0), (side * w1, y0, z1), 1.0, h, (255, 80, 80),
                            mat="Smooth", inward=(side, 0, 0))
            p["transparency"] = 1.0
    prim(SHIP, "Barrier", "Block", (2 * W(STERN) + 4.0, h, 1.0), (0.0, y0 + h / 2, STERN + 1.5), color=(255, 80, 80),
         mat="Smooth", transparency=1.0)
    prim(SHIP, "Barrier", "Block", (4.0, h, 1.0), (0.0, y0 + h / 2, BOW - 1.5), color=(255, 80, 80),
         mat="Smooth", transparency=1.0)
    for z in PLANKS_Z:
        x_in = W(z) + 0.7
        x_out = 12.3 + 18.5 + 0.6
        for s in (-1, 1):
            prim(SHIP, "Barrier", "Block", (x_out - x_in, 14.0, 0.6), ((x_in + x_out) / 2, 7.4, z + s * 2.2),
                 color=(255, 80, 80), mat="Smooth", transparency=1.0)
        prim(SHIP, "Barrier", "Block", (0.6, 14.0, 5.0), (x_out + 0.3, 7.4, z), color=(255, 80, 80), mat="Smooth",
             transparency=1.0)


def build_spawn_points():
    spots = [
        (-8.0, 0.0, -27.0), (8.0, 0.0, -27.0), (-8.0, 0.0, -13.0), (8.0, 0.0, -13.0),
        (-8.0, 0.0, 2.0), (8.0, 0.0, 2.0), (-6.5, 0.0, 17.0), (6.5, 0.0, 17.0),
        (-6.0, 8.0, 41.0), (6.0, 8.0, 40.5), (-4.0, 5.0, -42.0), (4.0, 5.0, -42.0),
        (-5.0, HOLD_FLOOR, -22.0), (5.0, HOLD_FLOOR, -10.0), (-6.0, HOLD_FLOOR, 18.0), (5.5, HOLD_FLOOR, 33.0),
    ]
    for x, y, z in spots:
        prim(SHIP, "SpawnPoint", "Block", (2.0, 1.0, 2.0), (x, y + 0.5, z), color=(80, 255, 120), mat="Smooth",
             transparency=1.0, collide=False)


def build_ship():
    build_hull()
    build_decks()
    build_hold()
    build_rigging()
    build_deck_props()
    build_barriers()
    build_spawn_points()


# ========================================================================================== TREES
# foliage gradient, from the shaded underside to the sunlit top
LEAVES = ((40, 104, 33), (54, 132, 39), (72, 158, 46), (96, 182, 54), (124, 204, 64))
BARK = ((112, 72, 42), (100, 64, 36), (124, 80, 46))


def leaf_color(t, r):
    t = min(1.0, max(0.0, t))
    idx = min(len(LEAVES) - 1, int(t * (len(LEAVES) - 1) + r.uniform(0.0, 0.6)))
    return shade(LEAVES[idx], 1.0 + r.uniform(-0.03, 0.03))


def canopy_blob(name, r, centre, radius, height, t_low, t_high):
    """A rounded cushion of foliage: 2-stud layers, each a rounded square (two crossing slabs)."""
    layers = max(2, int(round(height / 2.0)))
    lh = height / layers
    cx, cy, cz = centre
    for i in range(layers):
        yc = cy - height / 2 + (i + 0.5) * lh
        f = (yc - cy) / (height / 2)
        rad = max(radius * 0.38, radius * math.sqrt(max(0.0, 1.0 - f * f * 0.85)))
        ox, oz = cx + r.uniform(-0.5, 0.5), cz + r.uniform(-0.5, 0.5)
        color = leaf_color(lerp(t_low, t_high, i / (layers - 1)), r)
        prim(name, "Leaves", "Block", (2 * rad, lh + 0.02, 2 * rad * 0.64), (ox, yc, oz), color=color)
        prim(name, "Leaves", "Block", (2 * rad * 0.64, lh + 0.02, 2 * rad), (ox, yc, oz), color=color)
        if rad > 4.5:                            # third slab rounds off the bigger layers
            prim(name, "Leaves", "Block", (2 * rad * 0.86, lh + 0.02, 2 * rad * 0.86), (ox, yc, oz),
                 color=shade(color, 0.97))
    return cx, cy, cz


def tree(name, seed, trunk_h, trunk_w, blobs):
    """blobs: list of (dx, dy_from_trunk_top, dz, radius, height, t_low, t_high)."""
    r = random.Random(seed)
    # trunk: three slightly offset, tapering segments
    x = z = 0.0
    y = 0.0
    seg_h = trunk_h / 3
    tops = []
    for i in range(3):
        w = lerp(trunk_w, trunk_w * 0.7, i / 2)
        prim(name, "Trunk", "Block", (w, seg_h + 0.6, w), (x, y + seg_h / 2, z), color=r.choice(BARK))
        y += seg_h
        tops.append((x, y, z))
        x += r.uniform(-0.4, 0.4)
        z += r.uniform(-0.4, 0.4)
    # root flares
    for i in range(4):
        a = i * math.pi / 2 + r.uniform(-0.25, 0.25)
        d = (math.sin(a), 0.0, math.cos(a))
        prim(name, "Trunk", "Wedge", (2.2, 2.6, 3.4), (d[0] * (trunk_w / 2 + 1.3), 1.3, d[2] * (trunk_w / 2 + 1.3)),
             rot_y(a + math.pi), color=r.choice(BARK))
    tx, ty, tz = tops[-1]
    centres = []
    for dx, dy, dz, radius, height, t_low, t_high in blobs:
        centres.append(canopy_blob(name, r, (tx + dx, ty + dy, tz + dz), radius, height, t_low, t_high))
    # branches from the upper trunk towards the outer cushions
    for c in centres[1:4]:
        base = tops[1]
        d = sub(c, base)
        length = math.sqrt(dot(d, d)) * 0.85
        prim(name, "Trunk", "Block", (1.8, 1.8, length), add(base, mul(norm(d), length / 2)), look_rot(d),
             color=r.choice(BARK))
    # little lumps on the rims and a few leaves hanging underneath break up the outline
    main = blobs[0]
    for _ in range(9):
        a = r.uniform(0, math.tau)
        rad = main[3] * r.uniform(0.75, 0.95)
        s = r.uniform(3.0, 4.4)
        y = ty + main[1] + r.uniform(-0.2, 0.45) * main[4]
        prim(name, "Leaves", "Block", (s, 2.0, s), (tx + math.cos(a) * rad, y, tz + math.sin(a) * rad),
             color=leaf_color(0.55 + (y - ty - main[1]) / main[4], r))
    for _ in range(4):
        a = r.uniform(0, math.tau)
        rad = main[3] * r.uniform(0.5, 0.8)
        prim(name, "Leaves", "Block", (2.0, r.uniform(2.0, 3.6), 2.0),
             (tx + math.cos(a) * rad, ty + main[1] - main[4] / 2 - 1.0, tz + math.sin(a) * rad),
             color=LEAVES[0])


def build_trees():
    # big round oak: wide main cushion with four satellites
    tree("TreeA", 11, 14.0, 4.8, [
        (0.0, 4.0, 0.0, 11.5, 10.0, 0.15, 1.0),
        (8.5, 1.5, 3.0, 6.5, 6.0, 0.05, 0.75),
        (-7.5, 2.5, -4.5, 6.5, 6.0, 0.05, 0.8),
        (-2.5, 1.0, 8.5, 6.0, 6.0, 0.0, 0.7),
        (2.0, 9.5, -2.0, 6.5, 4.0, 0.6, 1.0),
    ])
    # tall tree with two stacked tiers
    tree("TreeB", 23, 20.0, 4.2, [
        (0.0, 7.0, 0.0, 8.0, 8.0, 0.35, 1.0),
        (1.0, 0.0, -1.0, 10.0, 6.0, 0.0, 0.6),
        (-6.0, 1.5, 4.0, 5.0, 4.0, 0.05, 0.6),
        (0.5, 12.5, 0.5, 5.0, 4.0, 0.7, 1.0),
    ])
    # wide, low umbrella tree
    tree("TreeC", 37, 10.0, 5.4, [
        (0.0, 3.0, 0.0, 13.5, 8.0, 0.15, 1.0),
        (10.0, 0.5, -3.0, 7.0, 5.0, 0.0, 0.7),
        (-9.5, 1.0, 4.0, 7.0, 5.0, 0.0, 0.7),
        (3.0, 0.0, 10.0, 6.5, 5.0, 0.0, 0.65),
        (-3.0, 7.0, -3.0, 7.0, 4.0, 0.6, 1.0),
    ])
    # bush: a single small cushion
    r = random.Random(5)
    canopy_blob("Bush", r, (0.0, 2.2, 0.0), 4.6, 4.4, 0.15, 1.0)
    for a in (0.6, 2.4, 4.4):
        prim("Bush", "Leaves", "Block", (3.0, 2.0, 3.0), (math.cos(a) * 3.6, 3.4, math.sin(a) * 3.6),
             color=LEAVES[3])


def build_all():
    PRIMS.clear()
    build_ship()
    build_trees()
    return PRIMS


# --------------------------------------------------------------------------------- export
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


def export_table(prims):
    """Compact JSON-able table: string lists + one number row per primitive."""
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
