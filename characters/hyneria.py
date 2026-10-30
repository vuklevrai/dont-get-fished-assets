"""Prehistoric fish: a Devonian lobe-finned predator (after the reference painting, a Hyneria-like fish):
broad flat armoured head with pale plate seams and speckles, wide toothy mouth with a pale lip, teal scales,
lobed paired fins and fins edged in red and orange, two rear dorsals and a long spear-shaped tail.

Ability "time stop": arret_du_temps (one-shot, the fish flexes, roars and releases the stop at 0.5 s), then
"rage" (fast angry swim loop) while the RageUntil attribute is ahead."""
import math

from voxlib import Character, G, T, bump, ramp, rot
from parts import brow, eye, h3, idx, pl, plate, rounded

COLORS = {
    "dos": "#21363a",
    "ecaille": "#3d6d63",
    "ecaille_c": "#5b8f7d",
    "flanc_bas": "#93ab97",
    "ventre": "#d3d9c3",
    "tete": "#6c8c83",
    "suture": "#a6bdb0",
    "tache": "#283141",
    "nageoire": "#2e3a47",
    "rouge": "#c8402a",
    "orange": "#e8892f",
    "levre": "#eadbd0",
    "gueule": "#4a1a20",
    "dent": "#f6f1e2",
    "blanc": "#f6f6f1",
    "encre": "#12161f",
}

TOP = [(-1.92, 0.1), (-1.5, 0.15), (-1.0, 0.24), (-0.4, 0.36), (0.3, 0.44), (0.8, 0.44), (1.0, 0.37),
       (1.3, 0.31), (1.6, 0.25), (1.85, 0.17), (2.0, 0.07)]
BOT = [(-1.92, -0.1), (-1.5, -0.15), (-1.0, -0.25), (-0.4, -0.38), (0.3, -0.46), (0.8, -0.45), (1.0, -0.4),
       (1.3, -0.34), (1.6, -0.29), (1.85, -0.22), (1.97, -0.12)]
HW = [(-1.92, 0.08), (-1.5, 0.14), (-1.0, 0.24), (-0.4, 0.34), (0.3, 0.4), (0.9, 0.44), (1.2, 0.52),
      (1.5, 0.5), (1.8, 0.42), (2.0, 0.24)]

MOUTH = -0.1
HINGE_X = 1.1
CHAIN = ["corps_avant", "corps_arriere", "queue_1", "queue_2", "queue_3", "nageoire_caudale"]


def build():
    ch = Character("hyneria", "Hyneria", COLORS)
    ch.root = {"pivot": (0.3, 0, 0), "size": (1.6, 1.6, 6.6)}

    ch.node("corps_avant", "centre", (1.0, 0, 0))
    ch.node("tete", "corps_avant", (1.0, 0, 0))
    ch.node("machoire", "tete", (HINGE_X, MOUTH, 0))
    ch.node("corps_arriere", "corps_avant", (0.3, 0, 0))
    ch.node("queue_1", "corps_arriere", (-0.4, 0, 0))
    ch.node("queue_2", "queue_1", (-1.0, 0, 0))
    ch.node("queue_3", "queue_2", (-1.5, 0, 0))
    ch.node("nageoire_caudale", "queue_3", (-1.9, 0, 0))
    ch.node("dorsale_1", "corps_arriere", (-0.1, 0.4, 0))
    ch.node("dorsale_2", "queue_1", (-0.7, 0.3, 0))
    ch.node("anale", "queue_1", (-0.7, -0.3, 0))
    for side, sfx in ((-1, "g"), (1, "d")):
        ch.node("pectorale_%s" % sfx, "corps_avant", (0.8, -0.3, side * 0.4), rot(yaw=side * 0.7, pitch=0.6))
        ch.node("pelvienne_%s" % sfx, "corps_arriere", (-0.2, -0.36, side * 0.3), rot(yaw=side * 0.6, pitch=0.7))

    def top(x):
        return pl(x, TOP)

    def bot(x):
        return pl(x, BOT)

    def hw(x):
        return pl(x, HW)

    def inside(x, y, z):
        if x < -1.92:
            return False
        if y >= MOUTH and x > 2.0:
            return False
        if y < MOUTH and x > 1.97:
            return False
        return rounded(y, z, top(x), bot(x), hw(x), 3.5)

    def seg_of(x, y, z):
        if x >= HINGE_X and y < MOUTH:
            return "machoire"
        for name, x0 in (("tete", 1.0), ("corps_avant", 0.3), ("corps_arriere", -0.4), ("queue_1", -1.0),
                         ("queue_2", -1.5), ("queue_3", -1.9)):
            if x >= x0:
                return name
        return "nageoire_caudale"

    def mat_of(x, y, z, seg, surf):
        i, j, k = idx(x), idx(y), idx(z)
        t, b, w = top(x), bot(x), hw(x)
        u = (y - b) / max(t - b, 1e-6)
        # mouth: dark inside, pale lower lip all around the jaw
        if x > 1.15 and MOUTH < y < MOUTH + G:
            return "gueule" if abs(z) < w - 0.12 and x < 1.92 else "tete"
        if x > 1.15 and MOUTH - G < y < MOUTH:
            return "gueule" if abs(z) < w - 0.12 and x < 1.88 else "levre"
        if seg in ("tete", "machoire"):
            if u < 0.3:
                return "flanc_bas" if u > 0.12 else "ventre"
            if surf:
                # bony plates: pale seams down the middle, across the skull and along the cheek, dark speckles
                if u > 0.75 and abs(z) < 0.05:
                    return "suture"
                if u > 0.6 and (1.35 < x < 1.45 or 1.0 < x < 1.1):
                    return "suture"
                if abs(z) > w - 0.12 and 1.0 < x < 1.1 and u > 0.45:
                    return "suture"
                if h3(i, j, k, 7) < 0.11:
                    return "tache"
            return "tete"
        if u > 0.82:
            return "dos"
        if u > 0.45:
            if not surf:
                return "ecaille"
            # staggered scale rows: cells 3 voxels long, 2 high, shifted every row
            r = j // 2
            c = (i + (r % 2) * 2) // 3
            return "ecaille" if (c + r) % 2 else "ecaille_c"
        if u > 0.24:
            return "flanc_bas"
        return "ventre"

    ch.body(seg_of, inside, mat_of, -2.0, 2.1, -0.6, 0.6, -0.46, 0.46)

    # small sharp teeth on both jaws, seen through the slightly open mouth
    up, low = [], []
    xs = (1.28, 1.4, 1.52, 1.64, 1.76, 1.86)
    for n, x in enumerate(xs):
        for side in (-1, 1):
            z = side * (hw(x) - 0.05)
            up.append(((x - 0.024, MOUTH - 0.1, z - 0.022), (x + 0.024, MOUTH + 0.005, z + 0.022)))
            xl = x + 0.06
            if xl < 1.9:
                low.append(((xl - 0.022, MOUTH - 0.005, z - 0.022), (xl + 0.022, MOUTH + 0.07, z + 0.022)))
    for z in (-0.12, -0.04, 0.04, 0.12):
        up.append(((1.92, MOUTH - 0.08, z - 0.022), (1.96, MOUTH + 0.005, z + 0.022)))
    ch.boxes("dents_haut", "tete", T(), "dent", up)
    ch.boxes("dents_bas", "machoire", T(), "dent", low)

    for side in (-1, 1):
        eye(ch, "tete", (1.52, 0.14, side * 0.5), side, "blanc", "encre", size=0.21, pupil_size=(0.08, 0.09),
            pupil_shift=0.025, socket="dos")
        brow(ch, "tete", (1.5, 0.3, side * 0.49), side, "encre", tilt=-0.35, length=0.34, thick=0.08)

    def fin_cells(heights, base_of, up_dir=1):
        cells = {}
        for i, hgt in heights.items():
            b = base_of(i)
            if up_dir > 0:
                j0, j1 = b - 1, b + int(round(hgt / G))
                rng = range(j0, j1 + 1)
                edge = j1
            else:
                j0, j1 = b - int(round(hgt / G)), b + 1
                rng = range(j0, j1 + 1)
                edge = j0
            for j in rng:
                if j == edge:
                    cells[(i, j)] = "rouge"
                elif abs(j - edge) == 1 and hgt > 0.2:
                    cells[(i, j)] = "orange"
                else:
                    cells[(i, j)] = "nageoire"
        return cells

    # dorsal fins
    plate(ch, "dorsale_1", fin_cells({1: 0.16, 0: 0.3, -1: 0.36, -2: 0.32, -3: 0.18},
                                     lambda i: idx(top(-0.1 + (i + 0.5) * G) - 0.4)), "dorsale_1")
    plate(ch, "dorsale_2", fin_cells({1: 0.12, 0: 0.24, -1: 0.28, -2: 0.14},
                                     lambda i: idx(top(-0.7 + (i + 0.5) * G) - 0.3)), "dorsale_2")
    plate(ch, "anale", fin_cells({1: 0.12, 0: 0.24, -1: 0.28, -2: 0.14},
                                 lambda i: idx(bot(-0.7 + (i + 0.5) * G) + 0.3), up_dir=-1), "anale")

    # spear-shaped tail: rays above and below the tail tip
    def tail_cells(x_pivot, i_range):
        cells = {}
        for i in i_range:
            x = x_pivot + (i + 0.5) * G
            h = pl(x, [(-1.5, 0.14), (-1.9, 0.3), (-2.05, 0.36), (-2.5, 0.06)])
            for j in range(-5, 5):
                y = (j + 0.5) * G
                if abs(y) > h:
                    continue
                if abs(y) < 0.06 and x > -2.2:
                    cells[(i, j)] = "ecaille"
                elif abs(y) > h - 0.1 or x < -2.32:
                    cells[(i, j)] = "rouge" if (abs(y) > h - 0.1 and x < -2.0) or x < -2.4 else "orange"
                else:
                    cells[(i, j)] = "nageoire"
        return cells

    plate(ch, "queue_3", tail_cells(-1.5, range(-4, 0)), "queue_3_nageoire")
    plate(ch, "nageoire_caudale", tail_cells(-1.9, range(-6, 0)), "nageoire_caudale")

    # lobed paired fins: a scaly fleshy lobe, then the dark fan edged in red
    for sfx in ("g", "d"):
        cells = {}
        for i in (-1, -2):
            for j in (-1, 0):
                cells[(i, j)] = "ecaille"
        for i, (j0, j1) in {-3: (-2, 0), -4: (-2, 0), -5: (-2, -1)}.items():
            for j in range(j0, j1 + 1):
                cells[(i, j)] = "rouge" if i == -5 or j == -2 else ("orange" if i == -4 else "nageoire")
        plate(ch, "pectorale_%s" % sfx, cells, "pectorale_%s" % sfx)
        cells = {(-1, 0): "ecaille", (-1, -1): "ecaille", (-2, 0): "nageoire", (-2, -1): "orange",
                 (-3, -1): "rouge", (-3, 0): "rouge"}
        plate(ch, "pelvienne_%s" % sfx, cells, "pelvienne_%s" % sfx)

    add_clips(ch)
    ch.triggers = {"AbilityStart": "arret_du_temps"}
    ch.states = {"RageUntil": "rage"}
    ch.attack_alias = "arret_du_temps"
    return ch


def add_clips(ch):
    two_pi = 2 * math.pi
    still = (0, 0, 0, 1)

    def repos(t):
        w = two_pi / 3.0
        d = {"rig": ((0, 0.03 * math.sin(w * t), 0), rot(pitch=0.02 * math.sin(w * t + 0.5)))}
        for n, (seg, amp) in enumerate(zip(CHAIN, (0.006, 0.01, 0.016, 0.022, 0.03, 0.042))):
            d[seg] = ((0, 0, 0), rot(yaw=amp * math.sin(w * t - 0.6 * n)))
        d["tete"] = ((0, 0, 0), rot(yaw=-0.008 * math.sin(w * t)))
        d["machoire"] = ((0, 0, 0), rot(pitch=-(0.05 + 0.05 * (0.5 - 0.5 * math.cos(two_pi * t / 1.5)))))
        # lobe fins paddle in a walking gait: front left with back right
        for side, sfx in ((-1, "g"), (1, "d")):
            ph = 0 if side < 0 else math.pi
            d["pectorale_%s" % sfx] = ((0, 0, 0), rot(yaw=side * 0.22 * math.sin(two_pi * t / 1.5 + ph),
                                                       pitch=0.1 * math.sin(two_pi * t / 1.5 + ph + 1.2)))
            d["pelvienne_%s" % sfx] = ((0, 0, 0), rot(yaw=side * 0.2 * math.sin(two_pi * t / 1.5 + ph + math.pi)))
        look = 0.025 * (bump(t, 0.3, 0.6, 1.2) - bump(t, 1.5, 1.8, 2.4) + 0.5 * bump(t, 2.5, 2.7, 2.95))
        for sfx in ("g", "d"):
            d["pupille_%s" % sfx] = ((look, 0.012 * bump(t, 1.5, 1.8, 2.4), 0), still)
        d["dorsale_1"] = ((0, 0, 0), rot(yaw=0.03 * math.sin(w * t - 1.2)))
        d["dorsale_2"] = ((0, 0, 0), rot(yaw=0.04 * math.sin(w * t - 1.8)))
        d["anale"] = ((0, 0, 0), rot(yaw=0.04 * math.sin(w * t - 1.8)))
        return d

    def swim(t, period, amps, lag, jaw, jaw_amp, tuck, frown=0.0):
        w = two_pi / period
        d = {"rig": ((0, 0.02 * math.sin(2 * w * t), 0), rot(roll=0.03 * math.sin(w * t)))}
        for n, (seg, amp) in enumerate(zip(CHAIN, amps)):
            d[seg] = ((0, 0, 0), rot(yaw=amp * math.sin(w * t - lag * n)))
        d["tete"] = ((0, 0, 0), rot(yaw=-amps[0] * 1.1 * math.sin(w * t)))
        d["machoire"] = ((0, 0, 0), rot(pitch=-(jaw + jaw_amp * math.sin(2 * w * t))))
        for side, sfx in ((-1, "g"), (1, "d")):
            d["pectorale_%s" % sfx] = ((0, 0, 0), rot(yaw=-side * (tuck + 0.08 * math.sin(2 * w * t))))
            d["pelvienne_%s" % sfx] = ((0, 0, 0), rot(yaw=-side * (tuck * 0.8 + 0.06 * math.sin(2 * w * t + 1))))
            d["pupille_%s" % sfx] = ((0.025, 0, 0), still)
            if frown:
                d["sourcil_%s" % sfx] = ((0.01 * frown, -0.03 * frown, 0), rot(pitch=-0.25 * frown))
        for fin, ph in (("dorsale_1", 1.4), ("dorsale_2", 2.2), ("anale", 2.2)):
            d[fin] = ((0, 0, 0), rot(yaw=-0.07 * math.sin(w * t - ph)))
        return d

    def nage(t):
        return swim(t, 1.0, (0.03, 0.06, 0.1, 0.14, 0.18, 0.24), 0.7, 0.06, 0.02, 0.4)

    def rage(t):
        d = swim(t, 0.5, (0.05, 0.09, 0.14, 0.18, 0.22, 0.28), 0.75, 0.2, 0.08, 0.55, frown=1.0)
        d["rig"] = ((0, 0.02 * math.sin(4 * two_pi * t), 0), rot(roll=0.05 * math.sin(two_pi * t / 0.5)))
        return d

    def arret_du_temps(t):
        # 0-0.45 flex and tremble, roar; 0.5 the stop goes off (the client effect starts the sphere here);
        # snap forward, menacing grin, then everything settles to rest for the rage loop
        a = ramp(t, 0.0, 0.38) * (1 - ramp(t, 0.5, 0.62))
        shake = bump(t, 0.18, 0.3, 0.52)
        snap = 0.0
        if t > 0.5:
            k = t - 0.5
            snap = -0.22 * math.exp(-5.5 * k) * math.sin(two_pi * k / 0.32) * (1 - ramp(t, 1.3, 1.6))
        d = {}
        bow = (0.12, -0.08, -0.14, -0.18, -0.2, -0.26)
        for seg, b in zip(CHAIN, bow):
            d[seg] = ((0, 0, 0), rot(pitch=b * a + abs(b) * snap))
        jx = 0.012 * shake * math.sin(two_pi * 19 * t)
        jy = 0.012 * shake * math.sin(two_pi * 23 * t + 1)
        thrust = 0.16 * bump(t, 0.48, 0.58, 1.0)
        d["rig"] = ((jx + thrust, jy + 0.05 * a, 0), rot(roll=0.04 * shake * math.sin(two_pi * 15 * t)))
        d["tete"] = ((0, 0, 0), rot(pitch=0.32 * a - 0.06 * bump(t, 0.5, 0.6, 0.9)))
        jaw = 0.55 * ramp(t, 0.22, 0.48) * (1 - ramp(t, 0.72, 0.9)) + 0.1 * ramp(t, 0.8, 0.9) * (1 - ramp(t, 1.35, 1.6))
        d["machoire"] = ((0, 0, 0), rot(pitch=-jaw))
        frown = ramp(t, 0.1, 0.3) * (1 - ramp(t, 1.4, 1.6))
        flare = ramp(t, 0.1, 0.4) * (1 - ramp(t, 0.9, 1.3))
        for side, sfx in ((-1, "g"), (1, "d")):
            d["sourcil_%s" % sfx] = ((0.01 * frown, -0.035 * frown, 0), rot(pitch=-0.3 * frown))
            d["pectorale_%s" % sfx] = ((0, 0, 0), rot(yaw=side * 0.7 * flare, pitch=-0.3 * flare))
            d["pelvienne_%s" % sfx] = ((0, 0, 0), rot(yaw=side * 0.6 * flare))
            d["pupille_%s" % sfx] = ((0.02 * frown, 0, 0), still)
        for fin in ("dorsale_1", "dorsale_2", "anale"):
            d[fin] = ((0, 0, 0), rot(pitch=0.15 * flare))
        return d

    ch.clip("repos", 3.0, True, repos)
    ch.clip("nage", 1.0, True, nage)
    ch.clip("arret_du_temps", 1.6, False, arret_du_temps)
    ch.clip("rage", 0.5, True, rage)
