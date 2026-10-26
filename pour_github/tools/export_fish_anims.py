# Converts the glTF animations of a blocky fish into Motor6D.Transform keyframes for the Roblox rig
# built by FishBuilder (one joint per segment, head hanging off corps_avant).
#
#   blender -b --factory-startup --python export_fish_anims.py -- <fish.glb> <out_dir> [scale]
#
# Writes anims.json and anims_data.png (4-byte length + JSON packed into RGB pixels).
import json
import os
import struct
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = argv[0], os.path.abspath(argv[1])
SCALE = float(argv[2]) if len(argv) > 2 else 2.0
FPS = 30
os.makedirs(OUT, exist_ok=True)

# Roblox joint -> parent joint in the Roblox rig ("centre" is the HumanoidRootPart)
JOINTS = {
    "corps_avant": "centre", "tete": "corps_avant", "corps_arriere": "corps_avant", "queue_1": "corps_arriere",
    "queue_2": "queue_1", "nageoire_caudale": "queue_2", "nageoire_dorsale": "corps_avant",
    "nageoire_pectorale_g": "corps_avant", "nageoire_pectorale_d": "corps_avant",
}

data = open(GLB, "rb").read()
json_len = struct.unpack_from("<I", data, 12)[0]
gltf = json.loads(data[20:20 + json_len])
bin_start = 20 + json_len + 8
binary = data[bin_start:]

COMP = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4)}
WIDTH = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}


def accessor(i):
    acc = gltf["accessors"][i]
    view = gltf["bufferViews"][acc["bufferView"]]
    fmt, size = COMP[acc["componentType"]]
    n = WIDTH[acc["type"]]
    off = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride", size * n)
    out = np.empty((acc["count"], n))
    for k in range(acc["count"]):
        out[k] = struct.unpack_from("<" + fmt * n, binary, off + k * stride)
    return out


nodes = gltf["nodes"]
by_name = {n.get("name"): i for i, n in enumerate(nodes)}
parent = {}
for i, n in enumerate(nodes):
    for c in n.get("children", []):
        parent[c] = i


def quat_mat(q):
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_quat(m):
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    return np.array(q)


def matrix(t, q):
    m = np.eye(4)
    m[:3, :3] = quat_mat(np.asarray(q, float))
    m[:3, 3] = t
    return m


def rest(i):
    n = nodes[i]
    return matrix(n.get("translation", [0, 0, 0]), n.get("rotation", [0, 0, 0, 1]))


def sample(track, t):
    times, values, is_rot = track
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    k = np.searchsorted(times, t) - 1
    f = (t - times[k]) / (times[k + 1] - times[k])
    a, b = values[k], values[k + 1]
    if is_rot:
        if np.dot(a, b) < 0:
            b = -b
        v = a * (1 - f) + b * f
        return v / np.linalg.norm(v)
    return a * (1 - f) + b * f


result = {"fps": FPS, "joints": list(JOINTS), "anims": {}}
for anim in gltf.get("animations", []):
    tracks = {}
    length = 0.0
    for ch in anim["channels"]:
        path = ch["target"]["path"]
        if path == "scale":
            continue
        s = anim["samplers"][ch["sampler"]]
        times = accessor(s["input"])[:, 0]
        values = accessor(s["output"])
        tracks[(ch["target"]["node"], path)] = (times, values, path == "rotation")
        length = max(length, times[-1])

    def local(i, t):
        n = nodes[i]
        tr = tracks.get((i, "translation"))
        ro = tracks.get((i, "rotation"))
        return matrix(sample(tr, t) if tr else n.get("translation", [0, 0, 0]),
                      sample(ro, t) if ro else n.get("rotation", [0, 0, 0, 1]))

    def world(i, t, use_rest=False):
        """Transform of node i relative to the 'centre' node's parent space."""
        m = rest(i) if use_rest else local(i, t)
        p = parent.get(i)
        while p is not None and nodes[p].get("name") not in ("bonite",):
            m = (rest(p) if use_rest else local(p, t)) @ m
            p = parent.get(p)
        return m

    frames = int(round(length * FPS)) + 1
    out = {}
    for joint, parent_joint in JOINTS.items():
        ji = by_name[joint]
        rows = []
        for f in range(frames):
            t = min(length, f / FPS)
            if parent_joint == "centre":
                # HumanoidRootPart stays put: measure against the rest pose of rig/centre
                anim_rel = np.linalg.inv(world(by_name["centre"], t, use_rest=True)) @ world(ji, t)
                rest_rel = np.linalg.inv(world(by_name["centre"], t, use_rest=True)) @ world(ji, t, use_rest=True)
            else:
                pi = by_name[parent_joint]
                anim_rel = np.linalg.inv(world(pi, t)) @ world(ji, t)
                rest_rel = np.linalg.inv(world(pi, t, use_rest=True)) @ world(ji, t, use_rest=True)
            x = np.linalg.inv(rest_rel) @ anim_rel           # Motor6D.Transform, in model units
            q = mat_quat(x[:3, :3])
            p = x[:3, 3] * SCALE
            rows.append([round(float(v), 4) for v in (*p, *q)])
        out[joint] = rows
    result["anims"][anim["name"]] = {"length": round(float(length), 4), "frames": frames, "joints": out}
    print("anim", anim["name"], "length", round(float(length), 3), "frames", frames)

raw = json.dumps(result, separators=(",", ":")).encode("utf-8")
open(os.path.join(OUT, "anims.json"), "wb").write(raw)
payload = len(raw).to_bytes(4, "big") + raw
payload += b"\0" * ((-len(payload)) % 3)
width = 512
height = (len(payload) // 3 + width - 1) // width
payload += b"\0" * (width * height * 3 - len(payload))
rgb = np.frombuffer(payload, np.uint8).reshape(height, width, 3).astype(np.float32) / 255.0
img = bpy.data.images.new("anims_data", width, height, alpha=False)
img.colorspace_settings.name = "Non-Color"
img.pixels.foreach_set(np.flipud(np.dstack([rgb, np.ones((height, width), np.float32)])).ravel())
img.filepath_raw = os.path.join(OUT, "anims_data.png")
img.file_format = "PNG"
img.save()
print("bytes", len(raw), "image", width, height)
