"""Voxel "brainrot" characters for Don't Get Fished: the shared builder.

Model space is the one of the reference bonite (bonite_brainrot.glb): Y up, head toward +X, voxel grid 0.1,
1 unit = Config.FISH_SCALE = 2 studs in game. A character is a chain of named nodes (rig > centre > segments);
every segment owns voxel volumes (merged into boxes for the game, into faces + studs for Blender) and loose
boxes (eyes, brows, teeth...). Animation clips are functions of time giving each node a local offset on top
of its rest pose; the same functions feed Blender (keyframes, NLA tracks, GLB) and the game (FishAnims:
Motor6D.Transform rows), so both always match.
"""
import json
import math

import numpy as np

G = 0.1  # voxel size, model units
FPS = 30  # FishAnimator samples clips at 30 fps
FISH_SCALE = 2.0  # Config.FISH_SCALE: studs per model unit


# ------------------------------------------------------------------------------------------------ maths

def qaxis(axis, angle):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    s = math.sin(angle / 2)
    return np.array([a[0] * s, a[1] * s, a[2] * s, math.cos(angle / 2)])


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ])


def qconj(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def qrot(q, v):
    return qmul(qmul(q, np.array([v[0], v[1], v[2], 0.0])), qconj(q))[:3]


def qnorm(q):
    q = np.asarray(q, float)
    return q / np.linalg.norm(q)


def rot(roll=0.0, yaw=0.0, pitch=0.0):
    """Body-friendly angles: yaw about Y (side to side), then pitch about Z (nose up), then roll about X."""
    return qmul(qmul(qaxis((0, 1, 0), yaw), qaxis((0, 0, 1), pitch)), qaxis((1, 0, 0), roll))


class T:
    """Rigid transform (position, quaternion x y z w)."""
    __slots__ = ("p", "q")

    def __init__(self, p=(0, 0, 0), q=(0, 0, 0, 1)):
        self.p = np.asarray(p, float)
        self.q = qnorm(q)

    def __mul__(self, o):
        return T(self.p + qrot(self.q, o.p), qmul(self.q, o.q))

    def inv(self):
        qi = qconj(self.q)
        return T(-qrot(qi, self.p), qi)

    def apply(self, v):
        return self.p + qrot(self.q, v)


# easing helpers for the clips
def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, t0, t1):
    """0 before t0, 1 after t1, smooth in between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return smooth((t - t0) / (t1 - t0))


def bump(t, t0, t1, t2):
    """0 -> 1 between t0 and t1, back to 0 at t2."""
    return ramp(t, t0, t1) - ramp(t, t1, t2) if t < t2 else 0.0


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# ------------------------------------------------------------------------------------------------ model

class Volume:
    """Voxels of one segment, on a grid local to the segment (voxel (i,j,k) spans [i*G + off, (i+1)*G + off])."""

    def __init__(self, seg, name, off=(0.0, 0.0, 0.0)):
        self.seg = seg
        self.name = name
        self.off = np.asarray(off, float)
        self.cells = {}


class BoxGroup:
    """Loose boxes (eyes, teeth...) in their own frame, welded to a segment."""

    def __init__(self, name, seg, frame, mat, boxes, studs=False):
        self.name = name
        self.seg = seg
        self.frame = frame  # T, absolute rest frame in model space
        self.mat = mat
        self.boxes = [(np.asarray(lo, float), np.asarray(hi, float)) for lo, hi in boxes]
        self.studs = studs


class Clip:
    def __init__(self, name, length, loop, fn, speed=1.0, joints=None):
        self.name = name
        self.length = length
        self.loop = loop
        self.fn = fn  # t -> {node: (dpos, dquat)}
        self.speed = speed
        self.joints = joints  # None = every segment; a list = overlay clip that only drives these

    @property
    def frames(self):
        return int(round(self.length * FPS)) + 1


class Character:
    def __init__(self, key, model, colors):
        self.key = key  # file names: piranha, hyneria, crocodile
        self.model = model  # FishData / FishAnims entry: Piranha, Hyneria, Crocodile
        self.colors = dict(colors)
        self.nodes = {}
        self.order = []
        self.volumes = {}
        self.groups = []
        self.clips = {}
        self.root = {"pivot": (0.2, 0, 0), "size": (1.2, 1.4, 4.6)}
        self.triggers = {}
        self.states = {}
        self.overlays = {}
        self.emissive = {}
        self.attack_alias = None
        self.node("rig", None, (0, 0, 0))
        self.node("centre", "rig", (0, 0, 0))

    # ---- structure
    def node(self, name, parent, pos, q=(0, 0, 0, 1)):
        assert name not in self.nodes, name
        self.nodes[name] = {"parent": parent, "rest": T(pos, q)}
        self.order.append(name)

    def segments(self):
        return [n for n in self.order if n not in ("rig", "centre")]

    def rest_world(self, name):
        return self.nodes[name]["rest"]

    def rest_local(self, name):
        nd = self.nodes[name]
        if nd["parent"] is None:
            return nd["rest"]
        return self.nodes[nd["parent"]]["rest"].inv() * nd["rest"]

    def volume(self, seg, name=None, off=(0, 0, 0)):
        key = (seg, name or seg)
        if key not in self.volumes:
            self.volumes[key] = Volume(seg, name or seg, off)
        return self.volumes[key]

    def body(self, seg_of, inside, mat_of, x0, x1, y0, y1, z0, z1):
        """Fill model-space voxels: seg_of(x,y,z) picks the segment (its rest frame must be axis aligned and on
        the grid), inside() keeps a voxel centre, mat_of() colours it (None = leave empty)."""
        for i in range(int(math.floor(x0 / G)), int(math.ceil(x1 / G))):
            x = (i + 0.5) * G
            for j in range(int(math.floor(y0 / G)), int(math.ceil(y1 / G))):
                y = (j + 0.5) * G
                for k in range(int(math.floor(z0 / G)), int(math.ceil(z1 / G))):
                    z = (k + 0.5) * G
                    if not inside(x, y, z):
                        continue
                    seg = seg_of(x, y, z)
                    if seg is None:
                        continue
                    # patterns only matter on the skin: hidden voxels keep plain band colours so they merge
                    surf = not all(inside(x + dx, y + dy, z + dz) for dx, dy, dz in
                                   ((G, 0, 0), (-G, 0, 0), (0, G, 0), (0, -G, 0), (0, 0, G), (0, 0, -G)))
                    m = mat_of(x, y, z, seg, surf)
                    if m is None:
                        continue
                    self.put(seg, i, j, k, m)

    def put(self, seg, i, j, k, m, name=None):
        """Model-space voxel index -> segment-local voxel."""
        rest = self.nodes[seg]["rest"]
        assert np.allclose(rest.q, (0, 0, 0, 1)), seg
        o = np.round(rest.p / G).astype(int)
        assert np.allclose(o * G, rest.p), (seg, rest.p)
        self.volume(seg, name).cells[(i - o[0], j - o[1], k - o[2])] = m

    def top_j(self, i, k):
        """Highest model-space voxel row in column (i, k) over the on-grid body volumes, or None."""
        best = None
        for (seg, vname), vol in self.volumes.items():
            rest = self.nodes[seg]["rest"]
            if not (np.allclose(rest.q, (0, 0, 0, 1)) and np.allclose(vol.off, 0)):
                continue
            o = np.round(rest.p / G).astype(int)
            for (a, b, c) in vol.cells:
                if a + o[0] == i and c + o[2] == k:
                    j = b + o[1]
                    best = j if best is None else max(best, j)
        return best

    def unput(self, seg, i, j, k, name=None):
        o = np.round(self.nodes[seg]["rest"].p / G).astype(int)
        self.volume(seg, name).cells.pop((i - o[0], j - o[1], k - o[2]), None)

    def boxes(self, name, seg, frame, mat, boxes, studs=False):
        if not isinstance(frame, T):
            frame = T(frame)
        self.groups.append(BoxGroup(name, seg, frame, mat, boxes, studs))

    def clip(self, name, length, loop, fn, speed=1.0, joints=None):
        self.clips[name] = Clip(name, length, loop, fn, speed, joints)

    # ---- posing
    def pose(self, clip, t):
        """World (model-space) transform of every node at time t of a clip."""
        deltas = clip.fn(t) if clip else {}
        world = {}
        for n in self.order:
            local = self.rest_local(n)
            d = deltas.get(n)
            if d is not None:
                dp, dq = d
                local = T(local.p + np.asarray(dp, float), qmul(local.q, dq))
            parent = self.nodes[n]["parent"]
            world[n] = world[parent] * local if parent else local
        return world

    def check_loops(self, tol=1e-4):
        bad = []
        for c in self.clips.values():
            if not c.loop:
                continue
            a, b = self.pose(c, 0), self.pose(c, c.length)
            for n in self.order:
                if np.abs(a[n].p - b[n].p).max() > tol or min(np.abs(a[n].q - b[n].q).max(), np.abs(a[n].q + b[n].q).max()) > tol:
                    bad.append((c.name, n))
        return bad


# ------------------------------------------------------------------------------------------------ boxes

def greedy_boxes(cells):
    """Merge same-material voxels into few boxes. cells: {(i,j,k): mat}. Returns {mat: [(i0,j0,k0,i1,j1,k1)]}
    with exclusive upper bounds. Tries the 6 axis orders and keeps the one with the fewest boxes."""
    best = None
    for order in ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        out = {}
        used = set()
        keys = sorted(cells, key=lambda c: (c[order[0]], c[order[1]], c[order[2]]))
        for c in keys:
            if c in used:
                continue
            m = cells[c]
            lo = list(c)
            hi = [c[0] + 1, c[1] + 1, c[2] + 1]

            def ok(lo_, hi_):
                for i in range(lo_[0], hi_[0]):
                    for j in range(lo_[1], hi_[1]):
                        for k in range(lo_[2], hi_[2]):
                            if (i, j, k) in used or cells.get((i, j, k)) != m:
                                return False
                return True

            for ax in reversed(order):  # grow along the last axis first
                while True:
                    lo2, hi2 = list(lo), list(hi)
                    lo2[ax] = hi[ax]
                    hi2[ax] = hi[ax] + 1
                    if ok(lo2, hi2):
                        hi[ax] += 1
                    else:
                        break
            for i in range(lo[0], hi[0]):
                for j in range(lo[1], hi[1]):
                    for k in range(lo[2], hi[2]):
                        used.add((i, j, k))
            out.setdefault(m, []).append((*lo, *hi))
        n = sum(len(v) for v in out.values())
        if best is None or n < best[0]:
            best = (n, out)
    return best[1]


LUAU_KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if", "in", "local", "nil",
                 "not", "or", "repeat", "return", "then", "true", "until", "while"}


def key(name):
    """A table key that is always valid Luau: name = ..., or ["name"] = ... for keywords and odd names."""
    if name.isidentifier() and name not in LUAU_KEYWORDS:
        return name
    return '["%s"]' % name


def fmt(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def v3(p):
    return "Vector3.new(%s, %s, %s)" % (fmt(p[0]), fmt(p[1]), fmt(p[2]))


def quat4(q):
    q = qnorm(q)
    if q[3] < 0:
        q = -q
    return "{ %s, %s, %s, %s }" % tuple(fmt(c) for c in q)


def fishdata_pieces(ch):
    """Pieces in the FishData format: name, seg, mat, frame (absolute rest), boxes in that frame."""
    pieces = []
    for (seg, vname), vol in ch.volumes.items():
        frame = ch.rest_world(seg)
        merged = greedy_boxes(vol.cells)
        for m in sorted(merged):
            boxes = []
            for b in merged[m]:
                lo = np.array(b[:3]) * G + vol.off
                hi = np.array(b[3:]) * G + vol.off
                boxes.append((lo, hi))
            pieces.append({"name": "%s_%s" % (vname, m), "seg": seg, "mat": m, "frame": frame, "boxes": boxes})
    for g in ch.groups:
        pieces.append({"name": g.name, "seg": g.seg, "mat": g.mat, "frame": g.frame, "boxes": g.boxes})
    return pieces


def write_fishdata(ch, path, note):
    pieces = fishdata_pieces(ch)
    lines = [
        "-- %s" % note,
        "-- Generated by characters/build_characters.py: boxes per rig segment, in model units (fish faces +X).",
        "return {",
        "\troot = { pivot = %s, size = %s }," % (v3(ch.root["pivot"]), v3(ch.root["size"])),
        "\tcolors = {",
    ]
    for m, h in ch.colors.items():
        r, g, b = hexrgb(h)
        lines.append("\t\t%s = Color3.fromRGB(%d, %d, %d)," % (key(m), r, g, b))
    lines += ["\t},", "\tsegments = {"]
    for s in ch.segments():
        nd = ch.nodes[s]
        rest = nd["rest"]
        lines.append('\t\t%s = { parent = "%s", pos = %s, rot = %s },' % (key(s), nd["parent"], v3(rest.p), quat4(rest.q)))
    lines += ["\t},", "\tpieces = {"]
    nbox = 0
    for p in pieces:
        lines.append('\t\t{ name = "%s", seg = "%s", mat = "%s", pos = %s, rot = %s, boxes = {' % (
            p["name"], p["seg"], p["mat"], v3(p["frame"].p), quat4(p["frame"].q)))
        for lo, hi in p["boxes"]:
            lines.append("\t\t\t{ %s }," % ", ".join(fmt(c) for c in (*lo, *hi)))
            nbox += 1
        lines.append("\t\t} },")
    lines += ["\t},", "}", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return nbox, len(pieces)


# ------------------------------------------------------------------------------------------------ game anims

R_TO = qaxis((0, 1, 0), math.pi / 2)  # FishBuilder TO_ROBLOX = CFrame.Angles(0, rad(90), 0)


def to_fish(ch, t):
    pivot = np.asarray(ch.root["pivot"], float)
    return T(FISH_SCALE * qrot(R_TO, t.p - pivot), qmul(R_TO, t.q))


def roblox_rows(ch, clip, joints=None):
    """Motor6D.Transform rows {joint: [[px,py,pz,qx,qy,qz,qw] per frame]} reproducing the model-space motion
    with FishBuilder's joints (HumanoidRootPart fixed at the origin, C0 = rest offset, C1 = identity)."""
    segs = ch.segments()
    rest = {n: ch.rest_world(n) for n in ch.order}
    J = {s: to_fish(ch, rest[s]) for s in segs}
    J["centre"] = T()
    parent = {s: ch.nodes[s]["parent"] for s in segs}
    C0 = {s: J[parent[s]].inv() * J[s] for s in segs}
    joints = joints or clip.joints or segs
    rows = {s: [] for s in joints}
    for f in range(clip.frames):
        w = ch.pose(clip, f / FPS)
        Jp = {s: to_fish(ch, w[s]) for s in segs}
        Jp["centre"] = T()
        for s in joints:
            tr = C0[s].inv() * Jp[parent[s]].inv() * Jp[s]
            q = tr.q if tr.q[3] >= 0 else -tr.q
            rows[s].append([round(float(c), 4) + 0.0 for c in (*tr.p, *q)])
    return rows


def write_fishanims(ch, path, note):
    anims = {}
    for c in ch.clips.values():
        entry = {"length": round(c.length, 4), "frames": c.frames, "joints": roblox_rows(ch, c)}
        if c.loop:
            entry["loop"] = True
        entry["speed"] = c.speed
        anims[c.name] = entry
    data = {"anims": anims, "joints": ch.segments(), "fps": FPS}
    if ch.triggers:
        data["triggers"] = ch.triggers
    if ch.states:
        data["states"] = ch.states
    if ch.overlays:
        data["overlays"] = ch.overlays
    body = json.dumps(data, separators=(",", ":"))
    with open(path, "w") as f:
        f.write("-- %s\n" % note)
        f.write("-- anims[name].joints[motorName][frame] = { px, py, pz, qx, qy, qz, qw } (Motor6D.Transform, studs at scale 1).\n")
        f.write("-- triggers: one-shot clip when that timestamp attribute changes; states: loop replacing the swim while\n")
        f.write("-- the attribute (server time) is ahead; overlays: loop on its own joints only, on top of the rest.\n")
        f.write('local data = game:GetService("HttpService"):JSONDecode([==[%s]==])\n' % body)
        if ch.attack_alias and "attaque" not in ch.clips:
            f.write("-- the stock FishAnimator plays \"attaque\" on DashStart\n")
            f.write("data.anims.attaque = data.anims.attaque or data.anims.%s\n" % ch.attack_alias)
        f.write("return data\n")


def roblox_fk_check(ch):
    """Replays FishAnims the way the game does (Part1 = Part0 * C0 * Transform) and compares every joint with
    the model-space pose. Returns the worst position error in studs."""
    segs = ch.segments()
    rest = {n: ch.rest_world(n) for n in ch.order}
    J = {s: to_fish(ch, rest[s]) for s in segs}
    J["centre"] = T()
    parent = {s: ch.nodes[s]["parent"] for s in segs}
    C0 = {s: J[parent[s]].inv() * J[s] for s in segs}
    worst = 0.0
    for c in ch.clips.values():
        rows = roblox_rows(ch, c, segs)
        for f in range(0, c.frames, 3):
            w = ch.pose(c, f / FPS)
            world = {"centre": T()}
            for s in segs:  # parents come first in ch.order
                r = rows[s][f]
                world[s] = world[parent[s]] * C0[s] * T(r[:3], (r[3], r[4], r[5], r[6]))
            for s in segs:
                want = to_fish(ch, w[s])
                for probe in ((0, 0, 0), (1, 0, 0), (0, 1, 0)):
                    e = np.abs(world[s].apply(probe) - want.apply(probe)).max()
                    worst = max(worst, e)
    return worst
