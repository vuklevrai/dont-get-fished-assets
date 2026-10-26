# Builds the Don't Get Fished block assets (pirate ship spawn + trees) in Blender, renders preview shots
# and exports the primitive table as a lossless data image for the Roblox importer.
#
#   blender -b --factory-startup --python build_blender.py -- <spawn_dir> [render|export|all] [view,...]
#
# The geometry comes from dgf_assets.py (Roblox coordinates, Y up). Blender is Z up, so a Roblox point
# (x, y, z) is placed at (x, -z, y).
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SPAWN_DIR = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
MODE = argv[1] if len(argv) > 1 else "all"
VIEWS = argv[2].split(",") if len(argv) > 2 else None
sys.path.insert(0, SPAWN_DIR)
import dgf_assets as A  # noqa: E402

TEX_DIR = os.path.join(SPAWN_DIR, "tex")
RENDER_DIR = os.path.join(SPAWN_DIR, "renders")
os.makedirs(RENDER_DIR, exist_ok=True)

# where each asset sits in the Blender scene (Roblox coordinates), so they can be shot side by side
ASSET_OFFSET = {"Ship": (0, 0, 0), "TreeA": (150, 0, 40), "TreeB": (190, 0, 40), "TreeC": (235, 0, 40),
                "Bush": (268, 0, 40)}
HIDDEN_GROUPS = {"Barrier", "SpawnPoint"}


def to_blender(v):
    return (v[0], -v[2], v[1])


# ------------------------------------------------------------------------------------------ geometry
def shape_geometry(shape, size):
    sx, sy, sz = (s / 2 for s in size)
    if shape == "Block":
        v = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        return v, f
    if shape == "Wedge":
        # Roblox wedge: full bottom and back (+z) faces, slope rising from the front-bottom edge
        v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, -sy, sz), (-sx, -sy, sz), (-sx, sy, sz), (sx, sy, sz)]
        f = [(0, 1, 2, 3), (3, 2, 5, 4), (0, 4, 5, 1), (0, 3, 4), (1, 5, 2)]
        return v, f
    if shape == "Cylinder":
        n = 18
        r = min(sy, sz)
        v = []
        for x in (-sx, sx):
            for i in range(n):
                a = i / n * math.tau
                v.append((x, r * math.cos(a), r * math.sin(a)))
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        return v, f
    if shape == "Ball":
        r = min(sx, sy, sz)
        rings, segs = 8, 14
        v = [(0, r, 0)]
        for j in range(1, rings):
            phi = j / rings * math.pi
            for i in range(segs):
                th = i / segs * math.tau
                v.append((r * math.sin(phi) * math.cos(th), r * math.cos(phi), r * math.sin(phi) * math.sin(th)))
        v.append((0, -r, 0))
        f = [(0, 1 + (i + 1) % segs, 1 + i) for i in range(segs)]
        for j in range(rings - 2):
            a, b = 1 + j * segs, 1 + (j + 1) * segs
            f += [(a + i, a + (i + 1) % segs, b + (i + 1) % segs, b + i) for i in range(segs)]
        last = len(v) - 1
        base = 1 + (rings - 2) * segs
        f += [(last, base + i, base + (i + 1) % segs) for i in range(segs)]
        return v, f
    raise ValueError(shape)


def build_meshes(prims):
    """One mesh object per (asset, material); colours live in a face-corner colour attribute."""
    buckets = {}
    for p in prims:
        key = (p["asset"], "Hidden" if p["group"] in HIDDEN_GROUPS else p["mat"])
        buckets.setdefault(key, []).append(p)
    objects = {}
    for (asset, mat), items in buckets.items():
        bm = bmesh.new()
        col_layer = bm.loops.layers.float_color.new("Col")
        off = ASSET_OFFSET.get(asset, (0, 0, 0))
        for p in items:
            verts, faces = shape_geometry(p["shape"], p["size"])
            r = p["rot"]
            pos = A.add(p["pos"], off)
            bverts = [bm.verts.new(to_blender(A.add(pos, A.apply(r, v)))) for v in verts]
            color = [c / 255.0 for c in p["color"]]
            lin = [(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in color] + [1.0]
            for f in faces:
                try:
                    face = bm.faces.new([bverts[i] for i in f])
                except ValueError:
                    continue
                for loop in face.loops:
                    loop[col_layer] = lin
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{asset}_{mat}")
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(f"{asset}_{mat}", me)
        coll = bpy.data.collections.get(asset) or bpy.data.collections.new(asset)
        if coll.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(coll)
        coll.objects.link(obj)
        obj.data.materials.append(material(mat))
        if mat == "Hidden":
            obj.hide_render = True
            obj.display_type = "WIRE"
        objects[(asset, mat)] = obj
    return objects


# ------------------------------------------------------------------------------------------ materials
_MATS = {}


def material(kind):
    if kind in _MATS:
        return _MATS[kind]
    m = bpy.data.materials.new(kind)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    attr = nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    if kind == "Neon":
        em = nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 4.0
        links.new(attr.outputs["Color"], em.inputs["Color"])
        links.new(em.outputs[0], out.inputs["Surface"])
    else:
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Roughness"].default_value = 0.62 if kind == "Stud" else 0.4
        color = attr.outputs["Color"]
        if kind == "Stud":
            coord = nodes.new("ShaderNodeTexCoord")
            mapping = nodes.new("ShaderNodeMapping")
            mapping.inputs["Scale"].default_value = (1 / 16, 1 / 16, 1 / 16)
            img = nodes.new("ShaderNodeTexImage")
            img.image = bpy.data.images.load(os.path.join(TEX_DIR, "stud_color.png"), check_existing=True)
            img.image.colorspace_settings.name = "Non-Color"
            img.projection = "BOX"
            img.projection_blend = 0.15
            mult = nodes.new("ShaderNodeMix")
            mult.data_type = "RGBA"
            mult.blend_type = "MULTIPLY"
            mult.inputs[0].default_value = 1.0
            rgba = [s for s in mult.inputs if s.type == "RGBA"]
            links.new(coord.outputs["Object"], mapping.inputs["Vector"])
            links.new(mapping.outputs["Vector"], img.inputs["Vector"])
            links.new(attr.outputs["Color"], rgba[0])
            links.new(img.outputs["Color"], rgba[1])
            color = [s for s in mult.outputs if s.type == "RGBA"][0]
        links.new(color, bsdf.inputs["Base Color"])
        if kind == "Glass":
            bsdf.inputs["Alpha"].default_value = 0.42
            bsdf.inputs["Roughness"].default_value = 0.05
            try:
                m.surface_render_method = "BLENDED"
            except Exception:
                pass
        if kind == "Hidden":
            bsdf.inputs["Alpha"].default_value = 0.2
        links.new(bsdf.outputs[0], out.inputs["Surface"])
    _MATS[kind] = m
    return m


# ------------------------------------------------------------------------------------------ scene
def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 48
        scene.cycles.use_denoising = True
    else:
        try:
            scene.eevee.taa_render_samples = 48
        except AttributeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.66, 0.95, 1.0)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 4.2
    sun.angle = math.radians(8)
    sun_obj = bpy.data.objects.new("Sun", sun)
    sun_obj.rotation_euler = (math.radians(48), math.radians(12), math.radians(35))
    scene.collection.objects.link(sun_obj)
    return scene


def add_ground():
    """Grass slab under the trees and lights inside the hold, only for the previews."""
    me = bpy.data.meshes.new("PreviewGround")
    s = 70
    me.from_pydata([(150 - s, -40 - s, 0), (300 + s, -40 - s, 0), (300 + s, -40 + s, 0), (150 - s, -40 + s, 0)], [],
                   [(0, 1, 2, 3)])
    obj = bpy.data.objects.new("PreviewGround", me)
    m = bpy.data.materials.new("PreviewGrass")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.25, 0.62, 0.03, 1)
    me.materials.append(m)
    bpy.context.scene.collection.objects.link(obj)
    for p in A.PRIMS:
        if p["group"] == "Lantern":
            light = bpy.data.lights.new("LanternLight", "POINT")
            light.energy = 900 if p["pos"][1] < 0 else 300
            light.color = (1.0, 0.8, 0.45)
            lo = bpy.data.objects.new("LanternLight", light)
            lo.location = to_blender(A.add(p["pos"], (0, -1.2, 0)))
            bpy.context.scene.collection.objects.link(lo)


CAMERAS = {
    # name: (roblox eye, roblox target, focal length mm)
    "ship_3q": ((80.0, 42.0, -82.0), (0.0, 12.0, -6.0), 32),
    "ship_side": ((120.0, 22.0, -4.0), (0.0, 16.0, -6.0), 30),
    "ship_stern": ((-58.0, 30.0, 96.0), (0.0, 12.0, 6.0), 32),
    "ship_deck": ((-14.5, 17.0, 47.0), (4.0, 2.0, -22.0), 20),
    "ship_full": ((150.0, 70.0, -150.0), (0.0, 22.0, -6.0), 30),
    "ship_flag": ((30.0, 66.0, -26.0), (0.0, 60.0, -4.0), 35),
    "ship_hold": ((7.5, -6.0, 33.0), (-1.0, -11.0, -24.0), 18),
    "ship_below": ((46.0, -70.0, 18.0), (0.0, -12.0, -4.0), 28),
    "trees": ((205.0, 30.0, 175.0), (205.0, 14.0, 40.0), 32),
}


def render(name):
    eye, target, lens = CAMERAS[name]
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_end = 2000
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    e, t = to_blender(eye), to_blender(target)
    cam.location = e
    d = (t[0] - e[0], t[1] - e[1], t[2] - e[2])
    yaw = math.atan2(d[1], d[0]) - math.pi / 2
    pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
    cam.rotation_euler = (math.pi / 2 + pitch, 0.0, yaw)
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.filepath = os.path.join(RENDER_DIR, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


# ------------------------------------------------------------------------------------------ export
def export_data(prims):
    table = A.export_table(prims)
    raw = json.dumps(table, separators=(",", ":")).encode("utf-8")
    with open(os.path.join(SPAWN_DIR, "assets.json"), "wb") as f:
        f.write(raw)
    payload = len(raw).to_bytes(4, "big") + raw
    payload += b"\0" * ((-len(payload)) % 3)
    pixels = len(payload) // 3
    width = 512
    height = (pixels + width - 1) // width
    payload += b"\0" * (width * height * 3 - len(payload))
    rgb = np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 3).astype(np.float32) / 255.0
    rgba = np.dstack([rgb, np.ones((height, width), np.float32)])
    img = bpy.data.images.new("assets_data", width, height, alpha=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.flipud(rgba).ravel())
    path = os.path.join(SPAWN_DIR, "assets_data.png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    # read it back to make sure the bytes survive the round trip
    check = bpy.data.images.load(path)
    check.colorspace_settings.name = "Non-Color"
    back = np.empty(width * height * 4, np.float32)
    check.pixels.foreach_get(back)
    back = np.flipud(back.reshape(height, width, 4))[:, :, :3]
    data = np.round(back * 255).astype(np.uint8).tobytes()
    n = int.from_bytes(data[:4], "big")
    assert data[4:4 + n] == raw, "data image round trip failed"
    print(f"exported {len(prims)} primitives, {len(raw)} bytes -> {width}x{height} data image")
    counts = {}
    for p in prims:
        counts[p["asset"]] = counts.get(p["asset"], 0) + 1
    print("per asset:", counts)


def main():
    prims = A.build_all()
    if MODE in ("export", "all"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        export_data(prims)
    if MODE in ("render", "all"):
        setup_scene()
        build_meshes(prims)
        add_ground()
        for name in (VIEWS or CAMERAS.keys()):
            render(name)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SPAWN_DIR, "dgf_spawn_assets.blend"))


main()
