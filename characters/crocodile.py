"""Crocodile (after the reference picture, in the voxel brainrot style): olive back with raised scute rows,
crested tail with dark bands, cream belly, long toothy snout whose upper fangs show with the mouth shut,
one gold tooth, eyes on top of the skull with slit pupils, four short clawed legs.

Ability "croc": while BiteArmedUntil is ahead the jaws hang wide open (overlay "gueule_ouverte"); BiteStart
plays "croc": jaws snap shut on the prey, the head shakes, then a full death roll."""
import math

from voxlib import Character, G, T, bump, ramp, rot
from parts import brow, h3, idx, pl, rounded, top_eye

COLORS = {
    "dos": "#3a4c22",
    "scute": "#28361a",
    "vert": "#5d7a31",
    "vert_c": "#86a047",
    "jaune": "#c4bf74",
    "ventre": "#e6dcaa",
    "bande": "#243018",
    "gueule": "#e17f84",
    "langue": "#c25866",
    "dent": "#f7f3e6",
    "dore": "#f5c518",
    "blanc": "#f2f0dc",
    "iris": "#d6c52a",
    "encre": "#141414",
    "griffe": "#2a261e",
}

TOP = [(-2.62, 0.06), (-2.1, 0.12), (-1.6, 0.19), (-1.1, 0.26), (-0.5, 0.34), (0.2, 0.38), (0.75, 0.34),
       (0.95, 0.27), (1.1, 0.27), (1.3, 0.21), (1.6, 0.16), (1.85, 0.16), (2.02, 0.08)]
BOT = [(-2.62, -0.06), (-2.1, -0.12), (-1.6, -0.18), (-1.1, -0.24), (-0.5, -0.36), (0.2, -0.4), (0.75, -0.35),
       (1.0, -0.3), (1.3, -0.28), (1.6, -0.26), (1.9, -0.23), (2.0, -0.17)]
HW = [(-2.62, 0.05), (-2.1, 0.09), (-1.6, 0.15), (-1.1, 0.23), (-0.5, 0.42), (0.2, 0.49), (0.75, 0.45),
      (0.95, 0.37), (1.2, 0.41), (1.5, 0.33), (1.75, 0.27), (1.92, 0.29), (2.02, 0.21)]

MOUTH = -0.1
HINGE = (1.0, MOUTH)
CHAIN = ["corps_avant", "corps_arriere", "queue_1", "queue_2", "queue_3", "queue_4"]
LEGS = {"patte_av": (0.62, -0.2, 0.42, "corps_avant"), "patte_ar": (-0.3, -0.2, 0.45, "corps_arriere")}


def build():
    ch = Character("crocodile", "Crocodile", COLORS)
    ch.root = {"pivot": (0.2, 0, 0), "size": (2.0, 1.5, 7.2)}

    ch.node("corps_avant", "centre", (0.9, 0, 0))
    ch.node("tete", "corps_avant", (0.9, 0, 0))
    ch.node("machoire", "tete", (HINGE[0], HINGE[1], 0))
    ch.node("corps_arriere", "corps_avant", (0.2, 0, 0))
    ch.node("queue_1", "corps_arriere", (-0.5, 0, 0))
    ch.node("queue_2", "queue_1", (-1.1, 0, 0))
    ch.node("queue_3", "queue_2", (-1.6, 0, 0))
    ch.node("queue_4", "queue_3", (-2.1, 0, 0))
    for leg, (lx, ly, lz, parent) in LEGS.items():
        for side, sfx in ((-1, "g"), (1, "d")):
            ch.node("%s_%s" % (leg, sfx), parent, (lx, ly, side * lz))

    def top(x):
        return pl(x, TOP)

    def bot(x):
        return pl(x, BOT)

    def hw(x):
        return pl(x, HW)

    def hw_low(x):
        # the lower jaw is a voxel narrower than the snout, so the upper fangs hang outside it
        return hw(x) - 0.1 if x > 1.08 else hw(x)

    def inside(x, y, z):
        if x < -2.62 or x > 2.02:
            return False
        if y < MOUTH and (x > 2.0 or abs(z) > hw_low(x)):
            return False
        if rounded(y, z, top(x), bot(x), hw(x), 5.0):
            return True
        return False

    def seg_of(x, y, z):
        if x >= HINGE[0] and y < MOUTH:
            return "machoire"
        for name, x0 in (("tete", 0.9), ("corps_avant", 0.2), ("corps_arriere", -0.5), ("queue_1", -1.1),
                         ("queue_2", -1.6), ("queue_3", -2.1)):
            if x >= x0:
                return name
        return "queue_4"

    def mat_of(x, y, z, seg, surf):
        i, j, k = idx(x), idx(y), idx(z)
        t, b, w = top(x), bot(x), hw(x)
        u = (y - b) / max(t - b, 1e-6)
        if x > 1.05 and MOUTH < y < MOUTH + G and abs(z) < w - 0.1 and x < 1.95:
            return "gueule"
        if x > 1.05 and MOUTH - G < y < MOUTH and abs(z) < hw_low(x) - 0.1 and x < 1.92:
            return "gueule"
        if u < 0.22:
            return "ventre"
        if u < 0.4:
            return "jaune"
        if seg.startswith("queue") and surf and u > 0.55 and i % 3 == 0:
            return "bande"
        if u > 0.78:
            return "dos"
        if u > 0.58:
            return "vert"
        return "vert_c"

    ch.body(seg_of, inside, mat_of, -2.7, 2.1, -0.4, 0.4, -0.45, 0.45)

    # scutes: staggered rows of raised bumps along the back, a double crest down the tail
    bumps = []
    for i in range(idx(-0.5), idx(0.86)):
        x = (i + 0.5) * G
        for k, stagger in ((-3, 0), (-2, 1), (1, 1), (2, 0)):
            if (i + stagger) % 2 == 0 and abs((k + 0.5) * G) < hw(x) - 0.04:
                bumps.append((i, k, "scute"))
    for i in range(idx(-2.5), idx(-0.5)):
        if i % 2 == 0:
            for k in (-1, 0):
                bumps.append((i, k, "scute"))
    # nostril bump at the tip of the snout
    for k in (-1, 0):
        bumps.append((idx(1.88), k, "dos"))
    nostril_y = None
    for i, k, m in bumps:
        jt = ch.top_j(i, k)
        if jt is None:
            continue
        x = (i + 0.5) * G
        ch.put(seg_of(x, 0, 0), i, jt + 1, k, m)
        if m == "dos":
            nostril_y = (jt + 2) * G

    # teeth: upper fangs over the jaw rim (one in gold), lower ones up inside the snout
    up, gold, low = [], [], []
    for n, x in enumerate((1.12, 1.23, 1.34, 1.45, 1.56, 1.67, 1.78, 1.88)):
        big = n in (4, 7)
        for side in (-1, 1):
            z = side * (hw(x) - 0.045)
            h = 0.13 if big else 0.1
            box = ((x - 0.025, MOUTH - h, z - 0.024), (x + 0.025, MOUTH + 0.01, z + 0.024))
            (gold if (n == 4 and side > 0) else up).append(box)
            xl = x + 0.055
            if xl < 1.92:
                zl = side * (hw_low(xl) - 0.04)
                low.append(((xl - 0.022, MOUTH - 0.01, zl - 0.022), (xl + 0.022, MOUTH + 0.09, zl + 0.022)))
    ch.boxes("dents_haut", "tete", T(), "dent", up)
    ch.boxes("dent_or", "tete", T(), "dore", gold)
    ch.boxes("dents_bas", "machoire", T(), "dent", low)
    ch.boxes("langue", "machoire", T(), "langue", [((1.1, MOUTH - 0.03, -0.09), (1.5, MOUTH + 0.01, 0.09))])
    ch.boxes("narines", "tete", T(), "encre", [((1.86, nostril_y, z - 0.025), (1.92, nostril_y + 0.006, z + 0.025))
                                                for z in (-0.05, 0.05)])

    # eyes on top of the skull, heavy lids as brows
    for side in (-1, 1):
        cy = top(1.15) + 0.07
        top_eye(ch, "tete", (1.15, cy, side * 0.19), side, "blanc", "iris", "encre", size=0.22)
        brow(ch, "tete", (1.14, cy + 0.13, side * 0.21), side, "dos", tilt=-0.3, length=0.3, thick=0.07, out=0.06)

    # legs: shoulder/thigh, forearm/shin, flat foot with claws
    for leg, (lx, ly, lz, parent) in LEGS.items():
        hind = leg == "patte_ar"
        for side, sfx in ((-1, "g"), (1, "d")):
            name = "%s_%s" % (leg, sfx)
            vol = ch.volume(name)

            def kk(m):
                return m if side > 0 else -1 - m

            cells = []
            for i in (-1, 0) + ((-2,) if hind else ()):
                for j in (-1, 0):
                    for m in (0, 1):
                        cells.append(((i, j, kk(m)), "vert"))
            for i in (-1, 0):
                for j in (-3, -2):
                    cells.append(((i, j, kk(2)), "vert_c"))
                    if hind:
                        cells.append(((i, j, kk(1)), "vert_c"))
            for i in (-1, 0, 1):
                for m in (1, 2, 3):
                    cells.append(((i, -4, kk(m)), "jaune"))
            for c, m in cells:
                vol.cells[c] = m
            claws = []
            for m in (1, 2, 3):
                zc = side * ((m + 0.5) * G)
                claws.append(((0.2, -0.4, zc - 0.02), (0.27, -0.35, zc + 0.02)))
            ch.boxes("%s_griffes" % name, name, T((lx, ly, side * lz)), "griffe", claws)

    add_clips(ch)
    ch.triggers = {"BiteStart": "croc"}
    ch.overlays = {"BiteArmedUntil": "gueule_ouverte"}
    ch.attack_alias = "croc"
    return ch


def add_clips(ch):
    two_pi = 2 * math.pi
    still = (0, 0, 0, 1)

    def legs_pose(d, fold, paddle_t=None, spread=0.0):
        """fold 0 = legs down, 1 = tucked back along the body for swimming."""
        for leg in ("patte_av", "patte_ar"):
            for side, sfx in ((-1, "g"), (1, "d")):
                name = "%s_%s" % (leg, sfx)
                pad = 0.0
                if paddle_t is not None:
                    ph = (0 if side < 0 else math.pi) + (math.pi if leg == "patte_ar" else 0)
                    pad = 0.25 * math.sin(two_pi * paddle_t / 1.5 + ph)
                yaw = -side * (1.25 * fold) + side * spread + pad * side
                roll = -side * 0.9 * fold
                d[name] = ((0, 0.04 * fold, 0), rot(roll=roll, yaw=yaw))

    def repos(t):
        w = two_pi / 3.0
        d = {"rig": ((0, 0.03 * math.sin(w * t), 0), rot(roll=0.015 * math.sin(w * t + 0.4)))}
        for n, (seg, amp) in enumerate(zip(CHAIN, (0.004, 0.008, 0.014, 0.022, 0.03, 0.042))):
            d[seg] = ((0, 0, 0), rot(yaw=amp * math.sin(w * t - 0.6 * n)))
        d["tete"] = ((0, 0, 0), rot(yaw=-0.01 * math.sin(w * t), pitch=0.03 * bump(t, 0.6, 1.3, 2.2)))
        # a slow, menacing gape
        d["machoire"] = ((0, 0, 0), rot(pitch=-0.16 * bump(t, 0.5, 1.3, 2.3)))
        legs_pose(d, 0.15, paddle_t=t)
        look = 0.02 * (bump(t, 0.2, 0.5, 1.0) - bump(t, 1.6, 1.9, 2.6))
        for sfx in ("g", "d"):
            d["pupille_%s" % sfx] = ((look, 0, 0), still)
        return d

    def nage(t):
        w = two_pi / 1.2
        d = {"rig": ((0, 0.02 * math.sin(2 * w * t), 0), rot(roll=0.025 * math.sin(w * t)))}
        for n, (seg, amp) in enumerate(zip(CHAIN, (0.03, 0.06, 0.1, 0.14, 0.19, 0.25))):
            d[seg] = ((0, 0, 0), rot(yaw=amp * math.sin(w * t - 0.7 * n)))
        d["tete"] = ((0, 0, 0), rot(yaw=-0.035 * math.sin(w * t)))
        legs_pose(d, 1.0)
        for sfx in ("g", "d"):
            d["pupille_%s" % sfx] = ((0.02, 0, 0), still)
        return d

    def gueule_ouverte(t):
        w = two_pi / 1.0
        return {
            "tete": ((0, 0, 0), rot(pitch=0.1 + 0.02 * math.sin(w * t))),
            "machoire": ((0, 0, 0), rot(pitch=-(0.62 + 0.06 * math.sin(w * t)))),
        }

    def croc(t):
        # 0-0.15 jaws gape and the head rears; 0.15-0.27 lunge and SNAP (shut at 0.25); 0.27-0.42 shake;
        # 0.42-1.2 death roll (a full turn); 1.2-1.5 settle
        d = {}
        rear = ramp(t, 0.0, 0.14) * (1 - ramp(t, 0.16, 0.25))
        jaw = 0.85 * ramp(t, 0.0, 0.12) * (1 - ramp(t, 0.2, 0.25))
        clench = -0.03 * bump(t, 0.25, 0.28, 0.4)
        d["machoire"] = ((0, 0, 0), rot(pitch=-(jaw + clench)))
        shake = bump(t, 0.25, 0.3, 0.45)
        d["tete"] = ((0, 0, 0), rot(pitch=0.32 * rear - 0.1 * bump(t, 0.18, 0.26, 0.45),
                                    yaw=0.18 * shake * math.sin(two_pi * t / 0.07)))
        lunge = -0.12 * rear + 0.5 * bump(t, 0.15, 0.26, 1.3)
        roll = two_pi * ramp(t, 0.42, 1.2)
        d["rig"] = ((lunge, 0.04 * bump(t, 0.15, 0.26, 0.6), 0), rot(roll=roll))
        coil = ramp(t, 0.0, 0.15) * (1 - ramp(t, 0.18, 0.3))
        for n, (seg, amp) in enumerate(zip(CHAIN, (0.06, 0.1, 0.16, 0.2, 0.24, 0.28))):
            whip = 0.0
            if t > 0.42:
                whip = math.sin(two_pi * (t - 0.42) / 0.4 - 0.6 * n) * bump(t, 0.42, 0.7, 1.3)
            d[seg] = ((0, 0, 0), rot(yaw=amp * (0.8 * coil + 0.9 * whip)))
        legs_pose(d, ramp(t, 0.2, 0.45) * (1 - ramp(t, 1.15, 1.5)), spread=0.5 * rear)
        for sfx in ("g", "d"):
            d["sourcil_%s" % sfx] = ((0, -0.03 * bump(t, 0.0, 0.15, 1.4), 0), rot(pitch=-0.25 * bump(t, 0.0, 0.15, 1.4)))
            d["pupille_%s" % sfx] = ((0.02 * bump(t, 0.0, 0.1, 0.5), 0, 0), still)
        return d

    ch.clip("repos", 3.0, True, repos)
    ch.clip("nage", 1.2, True, nage)
    ch.clip("gueule_ouverte", 1.0, True, gueule_ouverte, joints=["tete", "machoire"])
    ch.clip("croc", 1.5, False, croc)
