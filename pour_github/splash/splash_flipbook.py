# Cartoon water splash for the fish leaps, modelled and rendered in Blender.
#
#   blender -b --factory-startup --python splash_flipbook.py -- <out_dir>
#
# splash_crown.png : 4x4 flipbook (1024x1024, 16 frames, left to right then top to bottom) of a crown
#   splash seen from the side: the wall rises with pointed tips, the tips break into drops, a jet
#   shoots up in the middle and everything falls back. The water line sits at BASE_ROW of each frame.
# splash_ring.png  : top view of the foam ring left on the surface.
# Toon shading in the pond's colours (light cyan cells, white lines), with a soft blue outline.
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(OUT, "_frames")
os.makedirs(TMP, exist_ok=True)

FRAMES = 16
RES = 256
ORTHO = 6.0          # world units across one frame
BASE_ROW = 0.22      # water line, as a fraction of the frame height from the bottom
SPIKES = 9
rng = np.random.default_rng(11)

# pond palette (sRGB) - matches the water texture: cells (78, 214, 251), lines (135, 241, 255)
SHADES = [(70, 186, 246), (128, 222, 255), (196, 242, 255), (250, 255, 255)]
FOAM = [(150, 226, 255), (214, 246, 255), (245, 253, 255), (255, 255, 255)]
OUTLINE = (40, 146, 226)


def lin(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (ch(c[0]), ch(c[1]), ch(c[2]), 1.0)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.use_denoising = False
scene.render.film_transparent = True
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
world = bpy.data.worlds.new("World")
scene.world = world


def toon_material(name, shades):
    """Flat emission picked by a constant ramp on N.L (both faces lit: the walls are open sheets)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    flip = nt.nodes.new("ShaderNodeMath")
    flip.operation = "MULTIPLY_ADD"          # 1 - 2 * backfacing
    flip.inputs[1].default_value = -2.0
    flip.inputs[2].default_value = 1.0
    nt.links.new(geo.outputs["Backfacing"], flip.inputs[0])
    normal = nt.nodes.new("ShaderNodeVectorMath")
    normal.operation = "SCALE"
    nt.links.new(geo.outputs["Normal"], normal.inputs[0])
    nt.links.new(flip.outputs[0], normal.inputs["Scale"])
    light = nt.nodes.new("ShaderNodeCombineXYZ")
    d = np.array([-0.45, -0.75, 0.6])
    d /= np.linalg.norm(d)
    for k, v in enumerate(d):
        light.inputs[k].default_value = float(v)
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(normal.outputs[0], dot.inputs[0])
    nt.links.new(light.outputs[0], dot.inputs[1])
    remap = nt.nodes.new("ShaderNodeMapRange")
    remap.inputs["From Min"].default_value = -1.0
    remap.inputs["From Max"].default_value = 1.0
    nt.links.new(dot.outputs["Value"], remap.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    stops = [0.0, 0.42, 0.66, 0.86]
    els[0].position, els[0].color = stops[0], lin(shades[0])
    els[1].position, els[1].color = stops[1], lin(shades[1])
    for s, c in zip(stops[2:], shades[2:]):
        e = els.new(s)
        e.color = lin(c)
    nt.links.new(remap.outputs["Result"], ramp.inputs["Fac"])
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    return mat


WATER_MAT = toon_material("SplashWater", SHADES)
FOAM_MAT = toon_material("SplashFoam", FOAM)

cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = ORTHO
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def side_camera():
    # slightly from above, like a player watching the leap; the water line lands on BASE_ROW
    elev = math.radians(14)
    dist = 20
    lift = (0.5 - BASE_ROW) * ORTHO          # along the screen's up axis
    target = np.array([0.0, lift * math.sin(elev), lift * math.cos(elev)])
    pos = target + dist * np.array([0.0, -math.cos(elev), math.sin(elev)])
    cam.location = pos.tolist()
    cam.rotation_euler = (math.pi / 2 - elev, 0.0, 0.0)


def top_camera():
    cam.location = (0.0, 0.0, 20.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)


def clear_meshes():
    for o in list(scene.collection.objects):
        if o.type == "MESH":
            bpy.data.objects.remove(o, do_unlink=True)


def add_mesh(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x * x


def crown(t):
    """The wall: an open sheet, flaring outward, its rim pulled up into SPIKES tips."""
    rise = ease_out(t / 0.42)
    fall = ease_in((t - 0.42) / 0.58)
    height = 1.9 * rise * (1 - fall)
    if height < 0.03:
        return None, []
    r0 = 0.55 + 1.0 * t
    flare = 0.35 + 0.75 * t
    tip_amp = 0.45 * rise * (1 - 0.7 * fall)
    bm = bmesh.new()
    nu, nv = 72, 10
    rows = []
    tips = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(nu):
            u = i / nu * 2 * math.pi
            spike = max(0.0, math.cos(SPIKES * u + 0.4)) ** 4
            wobble = 0.06 * math.sin(3 * u + 1.7) + 0.04 * math.sin(7 * u)
            top = height * (1 + tip_amp * spike + wobble)
            z = top * v
            r = r0 + flare * v * v + 0.12 * spike * v ** 3
            row.append(bm.verts.new((r * math.cos(u), r * math.sin(u), z)))
            if j == nv and spike > 0.999:
                tips.append(np.array([r * math.cos(u), r * math.sin(u), z]))
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            a, b = rows[j][i], rows[j][(i + 1) % nu]
            c, d = rows[j + 1][(i + 1) % nu], rows[j + 1][i]
            bm.faces.new((a, b, c, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, tips


def blob(bm, centre, radius, stretch=1.0):
    res = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=radius)
    for v in res["verts"]:
        v.co.z *= stretch
        v.co += Vector(centre)


def foam_ring(bm, radius, minor, z=0.0, bumps=7, phase=0.0):
    """A lumpy tube swept around a circle."""
    ring = []
    nu, nv = 64, 8
    for i in range(nu):
        u = i / nu * 2 * math.pi
        rr = radius * (1 + 0.05 * math.sin(bumps * u + phase))
        mm = minor * (1 + 0.35 * max(0.0, math.sin(bumps * u + phase * 1.7)))
        col = []
        for k in range(nv):
            w = k / nv * 2 * math.pi
            x = (rr + mm * math.cos(w)) * math.cos(u)
            y = (rr + mm * math.cos(w)) * math.sin(u)
            col.append(bm.verts.new((x, y, z + mm * 0.6 * math.sin(w))))
        ring.append(col)
    for i in range(nu):
        for k in range(nv):
            a, b = ring[i][k], ring[(i + 1) % nu][k]
            c, d = ring[(i + 1) % nu][(k + 1) % nv], ring[i][(k + 1) % nv]
            bm.faces.new((a, b, c, d))


# drops thrown from the tips: launched when the wall peaks, then ballistic
DROPS = []
for k in range(SPIKES):
    u = (k * 2 * math.pi - 0.4) / SPIKES
    out = np.array([math.cos(u), math.sin(u), 0.0])
    DROPS.append({"u": u, "dir": out, "speed": rng.uniform(1.8, 2.8), "up": rng.uniform(3.0, 4.4), "r": rng.uniform(0.15, 0.22)})
EXTRA = [{"u": rng.uniform(0, 2 * math.pi), "speed": rng.uniform(1.5, 3.2), "up": rng.uniform(4.0, 6.0), "r": rng.uniform(0.08, 0.13),
          "t0": rng.uniform(0.18, 0.4)} for _ in range(10)]
G = 11.0
DURATION = 0.55


def frame_geometry(t):
    clear_meshes()
    bm, _ = crown(t)
    if bm:
        add_mesh("Crown", bm, WATER_MAT)
    drops = bmesh.new()
    any_drop = False
    t_launch = 0.4
    for d in DROPS:
        r0 = 0.55 + 1.0 * t_launch + 0.35 + 0.75 * t_launch
        start = np.array([r0 * math.cos(d["u"]), r0 * math.sin(d["u"]), 2.6])   # the tips at the crown's peak
        if t < t_launch:
            continue
        s = (t - t_launch) * DURATION
        p = start + np.array([math.cos(d["u"]), math.sin(d["u"]), 0.0]) * d["speed"] * s
        p[2] += d["up"] * s - 0.5 * G * s * s
        if p[2] > -0.1:
            size = d["r"] * (1 - 0.5 * (t - t_launch) / (1 - t_launch))
            blob(drops, p.tolist(), size, 1.25)
            any_drop = True
    for d in EXTRA:
        if t < d["t0"]:
            continue
        s = (t - d["t0"]) * DURATION
        p = np.array([math.cos(d["u"]) * (0.4 + d["speed"] * s), math.sin(d["u"]) * (0.4 + d["speed"] * s), d["up"] * s - 0.5 * G * s * s])
        if p[2] > -0.1:
            blob(drops, p.tolist(), d["r"], 1.2)
            any_drop = True
    # the jet: a column that pops up in the middle once the crown falls, with a bead on top
    jt = (t - 0.3) / 0.7
    if 0 < jt < 1:
        h = 2.3 * math.sin(math.pi * min(jt, 1.0) ** 0.8)
        if h > 0.15:
            col = bmesh.ops.create_cone(drops, cap_ends=True, segments=16, radius1=0.32, radius2=0.12, depth=h)
            for v in col["verts"]:
                v.co.z += h / 2
            bead_z = h + 0.12 + (0.5 * max(0.0, jt - 0.6) * 3)
            blob(drops, (0.0, 0.0, bead_z), 0.22 * (1 - 0.5 * max(0.0, jt - 0.6)), 1.3)
            any_drop = True
    if any_drop:
        add_mesh("Drops", drops, WATER_MAT)
    else:
        drops.free()
    # foam collar where the splash meets the water
    collar = 1 - ease_in((t - 0.6) / 0.4)
    if collar > 0.05:
        bm = bmesh.new()
        foam_ring(bm, 0.6 + 1.05 * t, 0.2 * collar + 0.05, 0.0, 7, t * 3)
        add_mesh("Collar", bm, FOAM_MAT)


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return np.flipud(px)        # row 0 = top


def outline(rgba, radius=2.5, color=OUTLINE):
    a = rgba[:, :, 3]
    h, w = a.shape
    grown = np.zeros_like(a)
    r = int(math.ceil(radius))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            dist = math.hypot(dx, dy)
            if dist > radius + 0.5:
                continue
            weight = min(1.0, radius + 0.5 - dist)
            shifted = np.zeros_like(a)
            ys = slice(max(dy, 0), h + min(dy, 0))
            yd = slice(max(-dy, 0), h + min(-dy, 0))
            xs = slice(max(dx, 0), w + min(dx, 0))
            xd = slice(max(-dx, 0), w + min(-dx, 0))
            shifted[yd, xd] = a[ys, xs]
            grown = np.maximum(grown, shifted * weight)
    c = np.array([v / 255 for v in color], dtype=np.float32)
    out = np.empty_like(rgba)
    # renders are straight alpha: put the drawing over the outline layer
    out_a = a + grown * (1 - a)
    safe = np.maximum(out_a, 1e-6)[:, :, None]
    out[:, :, :3] = (rgba[:, :, :3] * a[:, :, None] + c * (grown * (1 - a))[:, :, None]) / safe
    out[:, :, 3] = out_a
    return out


def save_png(name, rgba):
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.flipud(np.clip(rgba, 0, 1)).astype(np.float32).ravel())
    img.filepath_raw = os.path.join(OUT, name)
    img.file_format = "PNG"
    img.save()
    print("saved", img.filepath_raw)


# ---------------------------------------------------------------- crown flipbook
side_camera()
atlas = np.zeros((RES * 4, RES * 4, 4), dtype=np.float32)
for f in range(FRAMES):
    t = (f + 0.5) / FRAMES
    frame_geometry(t)
    path = os.path.join(TMP, f"crown_{f:02d}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    rgba = outline(load_rgba(path))
    # fade the very last frames so the particle ends softly
    rgba[:, :, 3] *= min(1.0, (FRAMES - f) / 3.0)
    row, colm = divmod(f, 4)
    atlas[row * RES:(row + 1) * RES, colm * RES:(colm + 1) * RES] = rgba
    print("frame", f)
save_png("splash_crown.png", atlas)

# ---------------------------------------------------------------- foam ring (top view)
clear_meshes()
top_camera()
cam_data.ortho_scale = 2.4
scene.render.resolution_x = 512
scene.render.resolution_y = 512
bm = bmesh.new()
foam_ring(bm, 0.92, 0.1, 0.0, 9, 0.6)
add_mesh("Ring", bm, FOAM_MAT)
bm = bmesh.new()
for k in range(14):
    u = k / 14 * 2 * math.pi + rng.uniform(-0.1, 0.1)
    rr = 0.92 + rng.uniform(-0.12, 0.14)
    blob(bm, (rr * math.cos(u), rr * math.sin(u), 0.0), rng.uniform(0.03, 0.07), 0.5)
add_mesh("Bits", bm, FOAM_MAT)
path = os.path.join(TMP, "ring.png")
scene.render.filepath = path
bpy.ops.render.render(write_still=True)
save_png("splash_ring.png", outline(load_rgba(path), 3.0, (96, 200, 250)))

# contact sheet on a sky-blue background, to check the look
bg = np.zeros_like(atlas)
bg[:, :, :3] = np.array([0.45, 0.78, 0.95])
bg[:, :, 3] = 1
a = atlas[:, :, 3:4]
sheet = bg.copy()
sheet[:, :, :3] = atlas[:, :, :3] * a + bg[:, :, :3] * (1 - a)
save_png("splash_preview.png", sheet)
