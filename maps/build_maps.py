# Builds the new Don't Get Fished maps and models in Blender: exports each primitive table (JSON + lossless
# data image for the Roblox importer), the anchor points (spots.json) and renders preview shots.
#
#   blender -b --factory-startup --python build_maps.py -- <repo_dir> [aquarium,ballon,ocean,models] [export|render|all]
#
# Geometry comes from dgf_maps.py (Roblox coordinates, Y up); Blender is Z up, so a Roblox point (x, y, z) sits
# at (x, -z, y). Data images: 4-byte big-endian length + UTF-8 JSON packed in RGB pixels, 512 px wide; a table that
# would need more than 1024 rows is split into _part1, _part2... (each part is a complete table).
# Previews use the stud texture from spawn/tex when it is there (pour_github/spawn/tex or ../spawn/tex).
import json
import math
import os
import sys

import bpy  # first: the stand-alone bpy module only provides bmesh once bpy is loaded
import bmesh  # noqa: E402
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
REPO = os.path.abspath(argv[0]) if argv else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WHAT = argv[1].split(",") if len(argv) > 1 else ["models", "aquarium", "ballon", "ocean"]
MODE = argv[2] if len(argv) > 2 else "all"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dgf_maps as M  # noqa: E402

TEX_CANDIDATES = [os.path.join(REPO, "pour_github", "spawn", "tex"), os.path.join(REPO, "spawn", "tex")]
TEX_DIR = next((d for d in TEX_CANDIDATES if os.path.exists(os.path.join(d, "stud_color.png"))), None)
HIDDEN_GROUPS = {"Barrier", "SpawnPoint", "Marker"}
WATER_RGB = (78, 214, 251)


def to_blender(v):
    return (v[0], -v[2], v[1])


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# ------------------------------------------------------------------------------------------ export
def write_table(prims, folder, name):
    """name.json + name_data.png (or name_part1.json / name_part1_data.png ... when too big for 512x1024)."""
    os.makedirs(folder, exist_ok=True)
    width, max_rows = 512, 1024
    capacity = width * max_rows * 3 - 4
    chunks = [prims]
    while True:
        raws = [json.dumps(M.export_table(c), separators=(",", ":")).encode("utf-8") for c in chunks]
        if all(len(r) <= capacity for r in raws):
            break
        parts = len(chunks) + 1
        step = math.ceil(len(prims) / parts)
        chunks = [prims[i:i + step] for i in range(0, len(prims), step)]
    files = []
    for k, raw in enumerate(raws):
        base = name if len(raws) == 1 else f"{name}_part{k + 1}"
        with open(os.path.join(folder, base + ".json"), "wb") as f:
            f.write(raw)
        payload = len(raw).to_bytes(4, "big") + raw
        payload += b"\0" * ((-len(payload)) % 3)
        height = (len(payload) // 3 + width - 1) // width
        payload += b"\0" * (width * height * 3 - len(payload))
        rgb = np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 3).astype(np.float32) / 255.0
        rgba = np.dstack([rgb, np.ones((height, width), np.float32)])
        img = bpy.data.images.new(base + "_data", width, height, alpha=False)
        img.colorspace_settings.name = "Non-Color"
        img.pixels.foreach_set(np.flipud(rgba).ravel())
        path = os.path.join(folder, base + "_data.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)
        # read it back: the bytes must survive the round trip
        check = bpy.data.images.load(path)
        check.colorspace_settings.name = "Non-Color"
        back = np.empty(width * height * 4, np.float32)
        check.pixels.foreach_get(back)
        bpy.data.images.remove(check)
        data = np.round(np.flipud(back.reshape(height, width, 4))[:, :, :3] * 255).astype(np.uint8).tobytes()
        n = int.from_bytes(data[:4], "big")
        assert data[4:4 + n] == raw, "data image round trip failed for " + path
        files.append((base, len(raw), width, height))
        print(f"exported {base}: {len(raw)} bytes -> {width}x{height} data image")
    return files


def write_spots(spots, folder):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "spots.json"), "w", encoding="utf-8") as f:
        json.dump(spots, f, indent=1)
    print("wrote", os.path.join(folder, "spots.json"))


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
        n = 24
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
        rings, segs = 10, 16
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
    elif kind == "Water":
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (srgb_to_linear(78), srgb_to_linear(214), srgb_to_linear(251), 1)
        bsdf.inputs["Roughness"].default_value = 0.1
        bsdf.inputs["Alpha"].default_value = 0.3
        links.new(bsdf.outputs[0], out.inputs["Surface"])
    else:
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        rough = {"Stud": 0.62, "Wood": 0.7, "Metal": 0.28, "Glass": 0.05, "ForceField": 0.2}.get(kind, 0.42)
        bsdf.inputs["Roughness"].default_value = rough
        if kind == "Metal":
            bsdf.inputs["Metallic"].default_value = 0.6
        color = attr.outputs["Color"]
        if kind == "Stud" and TEX_DIR:
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
        if kind in ("Glass", "ForceField"):
            bsdf.inputs["Alpha"].default_value = 0.28 if kind == "Glass" else 0.45
        if kind == "Hidden":
            bsdf.inputs["Alpha"].default_value = 0.2
        links.new(bsdf.outputs[0], out.inputs["Surface"])
    _MATS[kind] = m
    return m


def build_meshes(prims, name, offset=(0, 0, 0), rot=M.IDENT, skip_groups=(), only_groups=None):
    """One mesh per material; colours in a face-corner attribute. Primitives can be moved/rotated as a whole."""
    buckets = {}
    for p in prims:
        if p["group"] in skip_groups or (only_groups and p["group"] not in only_groups):
            continue
        key = "Hidden" if p["group"] in HIDDEN_GROUPS else p["mat"]
        buckets.setdefault(key, []).append(p)
    objects = []
    for mat, items in buckets.items():
        bm = bmesh.new()
        col = bm.loops.layers.float_color.new("Col")
        for p in items:
            verts, faces = shape_geometry(p["shape"], p["size"])
            r = M.matmul(rot, p["rot"])
            pos = M.add(offset, M.apply(rot, p["pos"]))
            bverts = [bm.verts.new(to_blender(M.add(pos, M.apply(r, v)))) for v in verts]
            lin = [srgb_to_linear(c) for c in p["color"]] + [1.0]
            for f in faces:
                try:
                    face = bm.faces.new([bverts[i] for i in f])
                except ValueError:
                    continue
                for loop in face.loops:
                    loop[col] = lin
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{name}_{mat}")
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(f"{name}_{mat}", me)
        bpy.context.scene.collection.objects.link(obj)
        obj.data.materials.append(material(mat))
        if mat == "Hidden":
            obj.hide_render = True
        objects.append(obj)
    return objects


def water_box(lo, hi, name="Water"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts, faces = shape_geometry("Block", M.sub(hi, lo))
    c = M.mul(M.add(lo, hi), 0.5)
    bv = [bm.verts.new(to_blender(M.add(c, v))) for v in verts]
    for f in faces:
        bm.faces.new([bv[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material("Water"))
    return obj


def water_ball(centre, radius, name="WaterBall"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=radius, location=to_blender(centre))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(material("Water"))
    return obj


def underwater_fog(lo, hi, density=0.004):
    me = bpy.data.meshes.new("Fog")
    bm = bmesh.new()
    verts, faces = shape_geometry("Block", M.sub(hi, lo))
    c = M.mul(M.add(lo, hi), 0.5)
    bv = [bm.verts.new(to_blender(M.add(c, v))) for v in verts]
    for f in faces:
        bm.faces.new([bv[i] for i in f])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Fog", me)
    bpy.context.scene.collection.objects.link(obj)
    m = bpy.data.materials.new("FogMat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (srgb_to_linear(60), srgb_to_linear(190), srgb_to_linear(240), 1)
    vol.inputs["Density"].default_value = density
    vol.inputs["Absorption Color"].default_value = (srgb_to_linear(70), srgb_to_linear(200), srgb_to_linear(250), 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    return obj


# ------------------------------------------------------------------------------------------ scene
PREVIEW_SCALE = float(os.environ.get("PREVIEW_SCALE", "1"))   # < 1 for quick, rough test renders


def setup_scene(sky=(0.42, 0.66, 0.95), res=(1400, 800), samples=40):
    res = (int(res[0] * PREVIEW_SCALE), int(res[1] * PREVIEW_SCALE))
    samples = max(8, int(samples * PREVIEW_SCALE))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.cycles.transparent_max_bounces = 16
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*sky, 1.0)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 4.2
    sun.angle = math.radians(8)
    sun_obj = bpy.data.objects.new("Sun", sun)
    sun_obj.rotation_euler = (math.radians(42), math.radians(12), math.radians(35))
    scene.collection.objects.link(sun_obj)
    return scene


def camera(name, eye, target, lens=30, ortho=None, clip_start=0.5, clip_end=5000):
    cam_data = bpy.data.cameras.new(name)
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.lens = lens
    cam_data.clip_start = clip_start
    cam_data.clip_end = clip_end
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    e, t = to_blender(eye), to_blender(target)
    cam.location = e
    d = (t[0] - e[0], t[1] - e[1], t[2] - e[2])
    yaw = math.atan2(d[1], d[0]) - math.pi / 2
    pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
    cam.rotation_euler = (math.pi / 2 + pitch, 0.0, yaw)
    return cam


ONLY_VIEWS = set(filter(None, os.environ.get("ONLY_VIEWS", "").split(",")))   # e.g. aquarium_top_preview


def render(path, cam):
    if ONLY_VIEWS and os.path.splitext(os.path.basename(path))[0] not in ONLY_VIEWS:
        return
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def behind(prims, cut_z):
    """Primitives that reach past z = cut_z (for section views)."""
    out = []
    for p in prims:
        r = p["rot"]
        reach = sum(abs(r[2][j]) * p["size"][j] / 2 for j in range(3))
        if p["pos"][2] + reach >= cut_z:
            out.append(p)
    return out


def place_model(model, spots_list, name):
    for k, s in enumerate(spots_list):
        c = s["cframe"]
        rot = ((c[3], c[4], c[5]), (c[6], c[7], c[8]), (c[9], c[10], c[11]))
        build_meshes(model.prims, f"{name}{k}", offset=tuple(c[:3]), rot=rot)


def seaweed_placeholders(spots_list):
    """Preview only: simple green fronds where the local session will grow the animated seaweed."""
    ph = M.Asset("SeaweedPreview")
    for k, s in enumerate(spots_list):
        x, y, z = s["pos"]
        h = s.get("height", 20)
        for j in range(5):
            a = j * 1.3 + k
            ox, oz = math.cos(a) * 1.6, math.sin(a) * 1.6
            hh = h * (0.6 + 0.1 * j)
            ph.box("Seaweed", (x + ox - 0.6, y, z + oz - 0.6), (x + ox + 0.6, y + hh, z + oz + 0.6),
                   (46 + 12 * j, 150 + 10 * j, 70), "Smooth")
    return ph


# ------------------------------------------------------------------------------------------ maps
def do_models(out_dir):
    pod = M.build_pod()
    boat = M.build_fishing_boat()
    island = M.build_island()
    results = {}
    if MODE in ("export", "all"):
        results["FuturisticPod"] = write_table(pod.prims, os.path.join(out_dir, "models"), "futuristic_pod")
        results["FishingBoat"] = write_table(boat.prims, os.path.join(out_dir, "models"), "fishing_boat")
        results["Island"] = write_table(island.prims, os.path.join(out_dir, "models"), "island")
        with open(os.path.join(out_dir, "models", "fishing_boat_spots.json"), "w", encoding="utf-8") as f:
            json.dump(M.boat_local_spots(boat), f, indent=1)
    if MODE in ("render", "all"):
        prev = os.path.join(out_dir, "models", "previews")
        os.makedirs(prev, exist_ok=True)
        setup_scene(res=(1000, 800), samples=48)
        build_meshes(pod.prims, "Pod")
        render(os.path.join(prev, "futuristic_pod_preview.png"), camera("c", (17, 12, -20), (0, -1, 0), 35))
        render(os.path.join(prev, "futuristic_pod_preview_back.png"), camera("c2", (-15, 9, 19), (0, 1, 0), 35))
        setup_scene(res=(1200, 800), samples=48)
        build_meshes(boat.prims, "Boat")
        water_box((-40, -6, -40), (40, 0, 40))
        render(os.path.join(prev, "fishing_boat_preview.png"), camera("c", (24, 14, -26), (0, 3, 0), 32))
        render(os.path.join(prev, "fishing_boat_preview_stern.png"), camera("c2", (-18, 12, 30), (0, 3, 2), 32))
        setup_scene(res=(1200, 800), samples=48)
        build_meshes(island.prims, "Island")
        water_box((-60, -8, -60), (60, 0, 60))
        render(os.path.join(prev, "island_preview.png"), camera("c", (40, 22, -48), (0, 8, 0), 32))
    return results


def do_aquarium(out_dir):
    tank, spots = M.build_aquarium()
    folder = os.path.join(out_dir, "maps", "aquarium")
    if MODE in ("export", "all"):
        write_table(tank.prims, folder, "aquarium")
        write_spots(spots, folder)
    if MODE in ("render", "all"):
        prev = os.path.join(folder, "previews")
        os.makedirs(prev, exist_ok=True)
        pod = M.build_pod()
        weed = seaweed_placeholders(spots["SeaweedSpots"])
        # 1) top view and overview, with water
        setup_scene(samples=32)
        build_meshes(tank.prims, "Tank")
        build_meshes(weed.prims, "Weed")
        place_model(pod, spots["FishermanSpots"], "Pod")
        water_box((-M.HALF_X, M.FLOOR_Y, -M.HALF_Z), (M.HALF_X, M.WATER_LEVEL, M.HALF_Z))
        render(os.path.join(prev, "aquarium_top_preview.png"), camera("top", (0, 600, 0.01), (0, 0, 0), ortho=560))
        render(os.path.join(prev, "aquarium_overview_preview.png"), camera("ov", (330, 210, -380), (0, -45, 0), 30))
        # 2) side view cut through the middle: everything entirely in front of the rock's centre is left out
        cz = M.ROCK_CENTRE[2]
        setup_scene(samples=32)
        build_meshes(behind(M.build_aquarium(cut_z=cz)[0].prims, cz), "Tank")
        build_meshes(behind(weed.prims, cz), "Weed")
        place_model(pod, [s for s in spots["FishermanSpots"] if s["pos"][2] > cz], "Pod")
        render(os.path.join(prev, "aquarium_cut_side_preview.png"), camera("cut", (0, -45, cz - 600), (0, -45, cz), ortho=390))
        # 3) under water, looking at the rock
        setup_scene(sky=(0.2, 0.55, 0.8), samples=32)
        build_meshes(tank.prims, "Tank", skip_groups=("Glass",))
        build_meshes(weed.prims, "Weed")
        underwater_fog((-M.HALF_X, M.FLOOR_Y, -M.HALF_Z), (M.HALF_X, M.WATER_LEVEL, M.HALF_Z), 0.0035)
        render(os.path.join(prev, "aquarium_underwater_rock_preview.png"), camera("uw", (-62, -66, -78), (0, -74, 4), 22))
        render(os.path.join(prev, "aquarium_underwater_castle_preview.png"),
               camera("uw2", (-150, -56, -30), (M.CASTLE_CENTRE[0], -70, M.CASTLE_CENTRE[2]), 24))
    return spots


def do_ballon(out_dir):
    plat, spots = M.build_ballon()
    folder = os.path.join(out_dir, "maps", "ballon")
    if MODE in ("export", "all"):
        write_table(plat.prims, folder, "ballon_platforms")
        write_spots(spots, folder)
    if MODE in ("render", "all"):
        prev = os.path.join(folder, "previews")
        os.makedirs(prev, exist_ok=True)
        setup_scene(sky=(0.36, 0.42, 0.62), samples=32)
        build_meshes(plat.prims, "Plat")
        place_model(M.build_pod(), spots["FishermanSpots"], "Pod")
        water_ball((0, 0, 0), M.BALL_RADIUS)
        render(os.path.join(prev, "ballon_overview_preview.png"), camera("ov", (300, 170, -330), (0, 0, 0), 30))
        render(os.path.join(prev, "ballon_side_preview.png"), camera("side", (0, 10, -520), (0, 0, 0), 30))
    return spots


def do_ocean(out_dir):
    layout, spots = M.build_ocean_layout()
    folder = os.path.join(out_dir, "maps", "ocean")
    if MODE in ("export", "all"):
        write_table(layout.prims, folder, "ocean_markers")
        write_spots(spots, folder)
    if MODE in ("render", "all"):
        prev = os.path.join(folder, "previews")
        os.makedirs(prev, exist_ok=True)
        setup_scene(samples=32)
        boat = M.build_fishing_boat()
        island = M.build_island()
        place_model(boat, spots["BoatSpots"], "Boat")
        c = spots["IslandSpot"]["cframe"]
        build_meshes(island.prims, "Island", offset=tuple(c[:3]))
        build_meshes(layout.prims, "Layout")
        water_box((-M.OCEAN_HALF, -40, -M.OCEAN_HALF), (M.OCEAN_HALF, M.WATER_LEVEL, M.OCEAN_HALF))
        scene = bpy.context.scene
        size = scene.render.resolution_x, scene.render.resolution_y
        scene.render.resolution_x = scene.render.resolution_y = int(1000 * PREVIEW_SCALE)
        render(os.path.join(prev, "ocean_top_preview.png"), camera("top", (0, 900, 0.01), (0, 0, 0), ortho=1220))
        scene.render.resolution_x, scene.render.resolution_y = size
        render(os.path.join(prev, "ocean_overview_preview.png"), camera("ov", (330, 160, -360), (0, -10, 20), 30))
        render(os.path.join(prev, "ocean_boats_close_preview.png"), camera("cl", (130, 30, -190), (60, 0, -131), 32))
    return spots


def main():
    out = REPO
    if "models" in WHAT:
        do_models(out)
    if "aquarium" in WHAT:
        do_aquarium(out)
    if "ballon" in WHAT:
        do_ballon(out)
    if "ocean" in WHAT:
        do_ocean(out)


main()
