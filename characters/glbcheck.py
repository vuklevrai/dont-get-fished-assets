"""Reads a GLB back (no Blender) and replays its animations, to check the export against the model."""
import json
import struct

import numpy as np

from voxlib import T


def load(path):
    b = open(path, "rb").read()
    _, _, length = struct.unpack_from("<III", b, 0)
    off = 12
    chunks = []
    while off < length:
        clen, ctype = struct.unpack_from("<II", b, off)
        chunks.append(b[off + 8:off + 8 + clen])
        off += 8 + clen
    js = json.loads(chunks[0])
    return js, (chunks[1] if len(chunks) > 1 else b"")


def accessor(js, binary, ai):
    a = js["accessors"][ai]
    v = js["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[a["componentType"]]
    size = struct.calcsize(fmt)
    stride = v.get("byteStride", n * size)
    base = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.array([struct.unpack_from("<" + fmt * n, binary, base + k * stride) for k in range(a["count"])])


def summary(js, binary):
    tris = 0
    for m in js.get("meshes", []):
        for pr in m["primitives"]:
            tris += js["accessors"][pr["indices"]]["count"] // 3
    return {
        "nodes": len(js["nodes"]),
        "meshes": len(js.get("meshes", [])),
        "materials": len(js.get("materials", [])),
        "tris": tris,
        "anims": [a["name"] for a in js.get("animations", [])],
    }


def replay(js, binary, anim_name, times):
    """World transforms {node name: [T per time]} of an animation sampled at the given times."""
    nodes = js["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    anim = next(a for a in js["animations"] if a["name"] == anim_name)
    chans = {}
    for ch in anim["channels"]:
        s = anim["samplers"][ch["sampler"]]
        tin = accessor(js, binary, s["input"])[:, 0]
        val = accessor(js, binary, s["output"])
        chans[(ch["target"]["node"], ch["target"]["path"])] = (tin, val)

    def sample(key, t, default):
        if key not in chans:
            return np.asarray(default, float)
        tin, val = chans[key]
        if t <= tin[0]:
            return val[0]
        if t >= tin[-1]:
            return val[-1]
        i = int(np.searchsorted(tin, t)) - 1
        a = (t - tin[i]) / (tin[i + 1] - tin[i])
        return val[i] * (1 - a) + val[i + 1] * a

    out = {n.get("name"): [] for n in nodes}
    for t in times:
        world = {}

        def w(i):
            if i in world:
                return world[i]
            n = nodes[i]
            p = sample((i, "translation"), t, n.get("translation", (0, 0, 0)))
            q = sample((i, "rotation"), t, n.get("rotation", (0, 0, 0, 1)))
            local = T(p, q)
            world[i] = w(parent[i]) * local if i in parent else local
            return world[i]

        for i, n in enumerate(nodes):
            out[n.get("name")].append(w(i))
    return out


def compare(ch, path, fps=30):
    """Worst node position error (model units) between the GLB animations and the model's clips."""
    js, binary = load(path)
    worst = 0.0
    for c in ch.clips.values():
        times = [f / fps for f in range(c.frames)]
        got = replay(js, binary, c.name, times)
        for f, t in enumerate(times):
            want = ch.pose(c, t)
            for n in ch.order:
                for probe in ((0, 0, 0), (0.3, 0, 0), (0, 0.3, 0)):
                    e = np.abs(got[n][f].apply(probe) - want[n].apply(probe)).max()
                    worst = max(worst, e)
    return worst, summary(js, binary)
