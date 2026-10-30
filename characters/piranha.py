"""Enemy fish (bots): a classic fish in blood reds, built like a piranha to look menacing: underbite full of
fangs, small-pupil yellow eyes under a heavy frown, saw-toothed dorsal fin and a scar across the right eye."""
import math

from voxlib import Character, G, T, bump, ramp, rot
from parts import brow, eye, h3, idx, pl, plate, rounded, tooth

COLORS = {
    "dos": "#4a0a10",  # back
    "sombre": "#86101a",
    "rouge": "#cf1a22",  # main flank
    "vif": "#ff4b2b",
    "ventre": "#ffa064",  # belly
    "tache": "#3a0509",  # spots
    "nageoire": "#5a0910",
    "pointe": "#1c0306",  # fin tips, brows, pupils
    "gueule": "#2a0306",  # inside of the mouth
    "dent": "#fff4e0",
    "oeil": "#ffd21f",
    "cicatrice": "#f5b9a6",
}

# side profile: (x, top), (x, bottom), (x, half width)
TOP = [(-1.12, 0.16), (-0.9, 0.22), (-0.6, 0.33), (-0.3, 0.47), (0.0, 0.56), (0.35, 0.62), (0.7, 0.62),
       (0.95, 0.56), (1.15, 0.44), (1.32, 0.28), (1.47, 0.08)]
BOT = [(-1.12, -0.16), (-0.9, -0.22), (-0.6, -0.34), (-0.3, -0.48), (0.0, -0.58), (0.35, -0.62), (0.7, -0.6),
       (0.95, -0.54), (1.15, -0.46), (1.35, -0.34), (1.56, -0.12)]
HW = [(-1.12, 0.12), (-0.8, 0.2), (-0.5, 0.28), (-0.3, 0.3), (1.2, 0.3), (1.5, 0.22), (1.56, 0.2)]

MOUTH = -0.1  # mouth line: the jaw is everything under it ahead of the hinge
HINGE_X = 0.9


def build():
    ch = Character("piranha", "Piranha", COLORS)
    ch.root = {"pivot": (0.2, 0, 0), "size": (1.2, 1.9, 4.8)}

    # rig: chain from the front body to the tail, head and jaw ahead
    ch.node("corps_avant", "centre", (0.8, 0, 0))
    ch.node("tete", "corps_avant", (0.8, 0, 0))
    ch.node("machoire", "tete", (HINGE_X, MOUTH, 0))
    ch.node("corps_arriere", "corps_avant", (0.2, 0, 0))
    ch.node("queue_1", "corps_arriere", (-0.4, 0, 0))
    ch.node("queue_2", "queue_1", (-0.8, 0, 0))
    ch.node("nageoire_caudale", "queue_2", (-1.1, 0, 0))
    ch.node("nageoire_dorsale", "corps_arriere", (-0.1, 0.5, 0))
    ch.node("nageoire_anale", "corps_arriere", (-0.1, -0.5, 0))
    for side, sfx in ((-1, "g"), (1, "d")):
        ch.node("pectorale_%s" % sfx, "corps_avant", (0.7, -0.25, side * 0.3),
                rot(yaw=side * 0.75, pitch=0.55))

    def top(x):
        return pl(x, TOP)

    def bot(x):
        return pl(x, BOT)

    def hw(x):
        return pl(x, HW)

    def inside(x, y, z):
        if x < -1.12 or x > 1.58:
            return False
        if y < MOUTH:
            # lower jaw: protrudes ahead of the snout and is wider than it
            if x > 1.56:
                return False
        elif x > 1.47:
            return False
        # the snout above the mouth is narrower than the jaw, so the lower fangs show on its sides
        if x > 1.02 and MOUTH < y < 0.1 and abs(z) > 0.2:
            return False
        return rounded(y, z, top(x), bot(x), hw(x), 4.0)

    def seg_of(x, y, z):
        if x >= HINGE_X and y < MOUTH:
            return "machoire"
        if x >= 0.8:
            return "tete"
        if x >= 0.2:
            return "corps_avant"
        if x >= -0.4:
            return "corps_arriere"
        if x >= -0.8:
            return "queue_1"
        return "queue_2"

    def mat_of(x, y, z, seg, surf):
        i, j, k = idx(x), idx(y), idx(z)
        t, b = top(x), bot(x)
        u = (y - b) / max(t - b, 1e-6)
        # the upper lip row is dark all along the mouth so the white fangs stand out; the jaw has a dark rim
        if x > 1.0 and MOUTH < y < MOUTH + G:
            return "gueule"
        if x > 1.0 and MOUTH - G < y < MOUTH:
            return "gueule" if abs(z) < 0.2 else "sombre"
        # gill line behind the head
        if 0.82 < x < 0.92 and -0.35 < y < 0.35:
            return "sombre"
        if u > 0.86:
            m = "dos"
        elif u > 0.7:
            m = "sombre"
        elif u > 0.44:
            m = "rouge"
        elif u > 0.24:
            m = "vif"
        else:
            m = "ventre"
        if surf and abs(z) > 0.2 and m == "sombre" and -0.6 < x < 0.8 and h3(i, j, k, 3) < 0.22:
            m = "tache"
        return m

    ch.body(seg_of, inside, mat_of, -1.2, 1.6, -0.7, 0.7, -0.31, 0.31)

    # fangs: lower ones on the jaw rim (visible with the mouth shut), upper ones hidden in the jaw until it opens
    low, up = [], []
    for x in (1.1, 1.22, 1.34, 1.46):
        for side in (-1, 1):
            tooth(low, x, MOUTH, side * 0.245, 1, w=0.08, h=0.16 if x < 1.4 else 0.13, d=0.05)
    for z in (-0.15, -0.05, 0.05, 0.15):
        tooth(low, 1.53, MOUTH, z, 1, w=0.07, h=0.14 if abs(z) > 0.1 else 0.1, d=0.05)
    for x in (1.13, 1.25, 1.37):
        for side in (-1, 1):
            tooth(up, x, MOUTH, side * 0.15, -1, w=0.07, h=0.1, d=0.05)
    ch.boxes("dents_bas", "machoire", T(), "dent", low)
    ch.boxes("dents_haut", "tete", T(), "dent", up)

    # eyes (dark socket, small pupils), heavy frown, and a stitched scar across the right eye
    for side in (-1, 1):
        eye(ch, "tete", (1.15, 0.26, side * 0.3), side, "oeil", "pointe", size=0.26, pupil_size=(0.06, 0.08),
            pupil_shift=0.04, socket="pointe")
        brow(ch, "tete", (1.12, 0.45, side * 0.31), side, "pointe", tilt=-0.45, length=0.38, thick=0.1)
    scar = T((1.15, 0.26, 0.3), rot(pitch=-0.8))
    ch.boxes("cicatrice", "tete", scar, "cicatrice", [((-0.22, -0.025, 0.028), (0.22, 0.025, 0.05))])
    ch.boxes("cicatrice_points", "tete", scar, "pointe",
             [((dx - 0.012, -0.05, 0.045), (dx + 0.012, 0.05, 0.06)) for dx in (-0.12, 0.0, 0.12)])

    # swept-back dorsal fin, shark style, black edge
    cells = {}
    heights = {2: 0.2, 1: 0.32, 0: 0.44, -1: 0.52, -2: 0.32, -3: 0.14}
    for i, hgt in heights.items():
        x = -0.1 + (i + 0.5) * G
        base = idx(top(x) - 0.5) - 1
        tip = idx(top(x) - 0.5 + hgt)
        for j in range(base, tip + 1):
            edge = j == tip or (i == -1 and j == tip - 1) or (i in (-2, -3) and j >= tip - 1)
            cells[(i, j)] = "pointe" if edge else "nageoire"
    plate(ch, "nageoire_dorsale", cells, "nageoire_dorsale")

    # anal fin, smaller and pointing back
    cells = {}
    for i, hgt in {1: 0.12, 0: 0.2, -1: 0.28, -2: 0.2, -3: 0.1}.items():
        x = -0.1 + (i + 0.5) * G
        b = bot(x) + 0.5
        low_j = idx(b - hgt)
        for j in range(low_j, idx(b) + 2):
            cells[(i, j)] = "pointe" if j == low_j else "nageoire"
    plate(ch, "nageoire_anale", cells, "nageoire_anale")

    # forked tail
    cells = {}
    for i in range(-7, 1):
        u = -(i + 0.5) * G
        h = 0.14 + 0.85 * u
        for j in range(-8, 8):
            y = (j + 0.5) * G
            if abs(y) > h:
                continue
            if u > 0.28 and abs(y) < 1.25 * (u - 0.28):
                continue
            edge = abs(y) > h - 0.12 or u > 0.55
            cells[(i, j)] = "pointe" if edge else "nageoire"
    plate(ch, "nageoire_caudale", cells, "nageoire_caudale")

    # pectoral fins: fans behind the gills, pointing down and back
    for sfx in ("g", "d"):
        cells = {}
        for i, (j0, j1) in {-1: (-2, 0), -2: (-2, 0), -3: (-2, 0), -4: (-2, -1), -5: (-1, -1)}.items():
            for j in range(j0, j1 + 1):
                cells[(i, j)] = "pointe" if i <= -4 else "nageoire"
        plate(ch, "pectorale_%s" % sfx, cells, "pectorale_%s" % sfx)

    add_clips(ch)
    ch.triggers = {"DashStart": "dash"}
    return ch


CHAIN = ["corps_avant", "corps_arriere", "queue_1", "queue_2", "nageoire_caudale"]


def add_clips(ch):
    two_pi = 2 * math.pi

    def repos(t):
        w = two_pi * 2 / 2.4
        d = {"rig": ((0, 0.035 * math.sin(two_pi * t / 2.4), 0), rot(pitch=0.025 * math.sin(two_pi * t / 2.4 + 0.6)))}
        for n, (seg, amp) in enumerate(zip(CHAIN, (0.012, 0.022, 0.035, 0.05, 0.075))):
            d[seg] = ((0, 0, 0), rot(yaw=amp * math.sin(w * t - 0.55 * n)))
        d["tete"] = ((0, 0, 0), rot(yaw=-0.012 * math.sin(w * t)))
        # slow menacing chomp
        d["machoire"] = ((0, 0, 0), rot(pitch=-(0.05 + 0.05 * (0.5 - 0.5 * math.cos(two_pi * t / 1.2)))))
        for side, sfx in ((-1, "g"), (1, "d")):
            d["pectorale_%s" % sfx] = ((0, 0, 0), rot(yaw=side * 0.22 * math.sin(two_pi * t / 0.8 + (0 if side < 0 else math.pi))))
        # the eyes scan around: forward, back, forward
        look = 0.03 * (bump(t, 0.2, 0.45, 0.95) - bump(t, 1.1, 1.35, 1.85) + 0.6 * bump(t, 1.95, 2.1, 2.35))
        for sfx in ("g", "d"):
            d["pupille_%s" % sfx] = ((look, 0.012 * bump(t, 1.1, 1.35, 1.85), 0), (0, 0, 0, 1))
        d["nageoire_dorsale"] = ((0, 0, 0), rot(yaw=0.04 * math.sin(w * t - 1.0)))
        return d

    def nage(t):
        w = two_pi / 0.8
        d = {"rig": ((0, 0.025 * math.sin(2 * w * t), 0), rot(roll=0.03 * math.sin(w * t)))}
        for n, (seg, amp) in enumerate(zip(CHAIN, (0.04, 0.07, 0.1, 0.13, 0.17))):
            d[seg] = ((0, 0, 0), rot(yaw=amp * math.sin(w * t - 0.65 * n)))
        d["tete"] = ((0, 0, 0), rot(yaw=-0.03 * math.sin(w * t)))
        d["machoire"] = ((0, 0, 0), rot(pitch=-(0.07 + 0.03 * math.sin(2 * w * t))))
        for side, sfx in ((-1, "g"), (1, "d")):
            d["pectorale_%s" % sfx] = ((0, 0, 0), rot(yaw=-side * (0.35 + 0.1 * math.sin(2 * w * t))))
            d["pupille_%s" % sfx] = ((0.03, 0, 0), (0, 0, 0, 1))
        d["nageoire_dorsale"] = ((0, 0, 0), rot(yaw=-0.06 * math.sin(w * t - 1.2)))
        d["nageoire_anale"] = ((0, 0, 0), rot(yaw=-0.06 * math.sin(w * t - 1.2)))
        return d

    def dash(t):
        # 0-0.22 coil into a C with the jaw wide open, 0.22-0.42 whip straight and lunge, jaw snaps shut at 0.35,
        # then the tail rings down and the teeth chatter twice
        coil = ramp(t, 0.0, 0.2) * (1 - ramp(t, 0.22, 0.3))
        whip = 0.0
        if t > 0.22:
            k = t - 0.22
            whip = -0.75 * math.exp(-4.0 * k) * math.sin(two_pi * k / 0.36) if k < 0.78 else 0.0
            whip *= 1 - ramp(t, 0.8, 1.0)
        d = {}
        bends = (0.1, 0.2, 0.26, 0.26, 0.22)
        for n, (seg, b) in enumerate(zip(CHAIN, bends)):
            lag = 0.025 * n
            k = t - 0.22 - lag
            wv = 0.0
            if k > 0:
                wv = -0.8 * math.exp(-4.2 * k) * math.sin(two_pi * k / 0.34) * (1 - ramp(t, 0.85, 1.0))
            d[seg] = ((0, 0, 0), rot(yaw=b * (coil + wv)))
        lunge = -0.14 * ramp(t, 0.0, 0.2) * (1 - ramp(t, 0.2, 0.3)) + 0.26 * bump(t, 0.24, 0.36, 0.85)
        roll = 0.25 * bump(t, 0.24, 0.36, 0.7)
        d["rig"] = ((lunge, 0.03 * bump(t, 0.2, 0.35, 0.8), 0), rot(roll=roll))
        d["tete"] = ((0, 0, 0), rot(yaw=0.14 * coil + 0.05 * whip, pitch=0.08 * coil))
        jaw = 0.62 * ramp(t, 0.02, 0.18) * (1 - ramp(t, 0.31, 0.36))
        jaw += 0.22 * bump(t, 0.5, 0.56, 0.62) + 0.18 * bump(t, 0.66, 0.72, 0.78)
        d["machoire"] = ((0, 0, 0), rot(pitch=-jaw))
        frown = ramp(t, 0.0, 0.15) * (1 - ramp(t, 0.75, 1.0))
        for side, sfx in ((-1, "g"), (1, "d")):
            d["sourcil_%s" % sfx] = ((0.01 * frown, -0.035 * frown, 0), rot(pitch=-0.2 * frown))
            d["pupille_%s" % sfx] = ((0.035 * frown, -0.01 * frown, 0), (0, 0, 0, 1))
            d["pectorale_%s" % sfx] = ((0, 0, 0), rot(yaw=side * (0.5 * ramp(t, 0.18, 0.3) * (1 - ramp(t, 0.6, 1.0)))))
        d["nageoire_dorsale"] = ((0, 0, 0), rot(yaw=0.1 * coil))
        return d

    ch.clip("repos", 2.4, True, repos)
    ch.clip("nage", 0.8, True, nage)
    ch.clip("dash", 1.0, False, dash, speed=1.0)
