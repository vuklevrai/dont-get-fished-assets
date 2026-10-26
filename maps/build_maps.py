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


def place_scaled(model, spots_list, name, scale_key="scale"):
    """Like place_model, but each spot may carry a uniform scale (corals)."""
    for k, s in enumerate(spots_list):
        c = s["cframe"]
        rot = ((c[3], c[4], c[5]), (c[6], c[7], c[8]), (c[9], c[10], c[11]))
        f = s.get(scale_key, 1.0)
        prims = []
        for p in model.prims:
            q = dict(p)
            q["pos"] = M.mul(p["pos"], f)
            q["size"] = M.mul(p["size"], f)
            prims.append(q)
        build_meshes(prims, f"{name}{k}", offset=tuple(c[:3]), rot=rot)


def seaweed_fronds(spots_list):
    """Preview only: three slim, leaning fronds per seaweed spot (the local session grows the real, animated ones)."""
    ph = M.Asset("SeaweedPreview")
    for k, s in enumerate(spots_list):
        x, y, z = s["pos"]
        h = s.get("height", 20)
        for j in range(3):
            a = j * 2.1 + k
            base = (x + math.cos(a) * 1.2, y, z + math.sin(a) * 1.2)
            lean = (math.cos(a + 0.6) * 0.12, 1.0, math.sin(a + 0.6) * 0.12)
            hh = h * (0.7 + 0.15 * j)
            pts = [M.add(base, M.mul(lean, hh * f)) for f in (0.0, 0.34, 0.67, 1.0)]
            for i in range(3):
                pts[i + 1] = M.add(pts[i + 1], (math.sin(i * 1.7 + k) * 0.8, 0.0, math.cos(i * 1.3 + k) * 0.8))
                ph.beam("Seaweed", pts[i], pts[i + 1], 0.9 - 0.2 * i, 0.35, (46 + 14 * j, 150 + 12 * j, 72), "Smooth")
    return ph


def do_ocean_decor(out_dir):
    import dgf_props as P
    fossil = P.build_megalodon()
    corals = P.build_corals()
    ocean_spots = json.load(open(os.path.join(out_dir, "maps", "ocean", "spots.json"), encoding="utf-8"))
    fossil_spot, coral_spots, weed_spots, stats, fossil_world = P.ocean_decor_spots(fossil, corals, ocean_spots["PlayerSpawnPoints"])
    checks = P.fossil_checks(fossil)
    folder = os.path.join(out_dir, "maps", "ocean_decor")
    table = M.Asset("Corals")
    for k, c in enumerate(corals):
        for p in c.prims:
            q = dict(p)
            q["asset"] = f"Coral{k + 1}"
            table.prims.append(q)
    if MODE in ("export", "all"):
        write_table(fossil.prims, folder, "megalodon_fossil")
        write_table(table.prims, folder, "corals")
        spots = {
            "v": 1,
            "map": "Ocean",
            "frame": "the Ocean map's own frame, as maps/ocean/spots.json; the bed is the top of the floor slab, y = -46",
            "FossilSpot": fossil_spot,
            "CoralVariants": {str(k + 1): f"Coral{k + 1}: {P.CORAL_BUILDERS[k].__doc__.split(':')[0].strip()}" for k in range(6)},
            "CoralSpots": coral_spots,
            "SeaweedSpots": weed_spots,
            "stats": stats,
            "fossil_checks": checks,
            "primitives": {"MegalodonFossil": len(fossil.prims), **{f"Coral{k + 1}": len(c.prims) for k, c in enumerate(corals)}},
        }
        write_spots(spots, folder)
    if MODE in ("render", "all"):
        prev = os.path.join(folder, "previews")
        os.makedirs(prev, exist_ok=True)
        # 1) the fossil alone, two views
        setup_scene(sky=(0.36, 0.6, 0.85), res=(1400, 800), samples=48)
        build_meshes(fossil.prims, "Fossil")
        floor = M.Asset("Floor")
        floor.box("Floor", (-70, -2, -70), (70, 0, 70), (214, 196, 150), "Stud")
        build_meshes(floor.prims, "Floor")
        render(os.path.join(prev, "megalodon_fossil_preview.png"), camera("f1", (62, 40, -66), (0, 9, -4), 30))
        render(os.path.join(prev, "megalodon_fossil_preview_side.png"), camera("f2", (-96, 22, 18), (0, 10, 2), 30))
        # 2) the six corals in a row, numbered left to right as their variant
        setup_scene(sky=(0.36, 0.6, 0.85), res=(1600, 600), samples=48)
        for k, c in enumerate(corals):
            # variant 1 on the left of the picture (the camera looks along +Z, so screen left is +X)
            build_meshes(c.prims, f"Coral{k}", offset=(50 - k * 20, 0, 0))
        floor = M.Asset("Floor")
        floor.box("Floor", (-75, -2, -20), (75, 0, 20), (214, 196, 150), "Stud")
        build_meshes(floor.prims, "Floor")
        render(os.path.join(prev, "corals_preview.png"), camera("c", (0, 30, -96), (0, 3, 0), 30))
        # 3) the arena under water with all the decor, boats above
        weed = seaweed_fronds(weed_spots)
        fx, fz = fossil_spot["pos"][0], fossil_spot["pos"][2]
        for tag, eye, target, lens in (("ocean_decor_underwater_preview", (fx - 52, -27, fz + 70), (fx + 2, -36, fz), 24),
                                       ("ocean_decor_underwater_wide_preview", (-140, -14, 100), (40, -40, -30), 18)):
            setup_scene(sky=(0.2, 0.55, 0.8), samples=40)
            build_meshes(fossil_world.prims, "Fossil")
            place_scaled_list = [(corals[s["variant"] - 1], s) for s in coral_spots]
            for k, (c, s) in enumerate(place_scaled_list):
                place_scaled(c, [s], f"C{k}_")
            build_meshes(weed.prims, "Weed")
            place_model(M.build_fishing_boat(), ocean_spots["BoatSpots"], "Boat")
            bed = M.Asset("Bed")
            bed.box("Bed", (-520, -48, -520), (520, P.OCEAN_BED, 520), (214, 196, 150), "Stud")
            build_meshes(bed.prims, "Bed")
            underwater_fog((-520, P.OCEAN_BED, -520), (520, M.WATER_LEVEL, 520), 0.0042)
            render(os.path.join(prev, tag + ".png"), camera("uw", eye, target, lens))
        # 4) top view of the layout: arena, fossil, corals, seaweed (no water)
        setup_scene(res=(1000, 1000), samples=24)
        build_meshes(fossil_world.prims, "Fossil")
        for k, s in enumerate(coral_spots):
            place_scaled(corals[s["variant"] - 1], [s], f"C{k}_")
        build_meshes(weed.prims, "Weed")
        bed = M.Asset("Bed")
        bed.box("Bed", (-520, -48, -520), (520, P.OCEAN_BED, 520), (214, 196, 150), "Stud")
        hx, hz = P.ARENA_HALF
        for a, b in (((-hx, -hz), (hx, -hz)), ((hx, -hz), (hx, hz)), ((hx, hz), (-hx, hz)), ((-hx, hz), (-hx, -hz))):
            bed.prim("Guide", "Block", (max(abs(b[0] - a[0]), 2), 0.4, max(abs(b[1] - a[1]), 2)),
                     ((a[0] + b[0]) / 2, P.OCEAN_BED + 0.2, (a[1] + b[1]) / 2), M.IDENT, (60, 120, 255), "Neon")
        for sp in ocean_spots["PlayerSpawnPoints"]:
            bed.prim("Guide", "Cylinder", (0.4, 6, 6), (sp[0], P.OCEAN_BED + 0.3, sp[2]), M.VERTICAL, (255, 60, 60), "Neon", 0.0, False)
        build_meshes(bed.prims, "Bed")
        render(os.path.join(prev, "ocean_decor_top_preview.png"), camera("top", (0, 900, 0.01), (0, 0, 0), ortho=1080))
    print("ocean decor:", json.dumps(stats), json.dumps(checks))
    return stats


WEAPON_FILES = {"HarpoonGun": "harpoon_gun", "Harpoon": "harpoon", "Bazooka": "bazooka", "Missile": "missile"}
LUAU_SHAPES = ["Block", "Wedge", "Cylinder", "Ball"]
LUAU_MATERIALS = {"Smooth": "SmoothPlastic", "Metal": "Metal", "Wood": "Wood", "Neon": "Neon", "Glass": "Glass",
                  "Stud": "Plastic", "ForceField": "ForceField"}


def weapon_models_luau(models, spots, path):
    """luau/WeaponModels.luau: the four weapon tables embedded in a ModuleScript that builds them in Roblox
    (same parts as the JSON tables, so the weapons need no import step)."""
    mats = list(LUAU_MATERIALS)
    lines = [
        "-- Weapon models of the harpoon and bazooka fishermen, built from primitives (no mesh, no import step).",
        "-- GENERATED by maps/build_maps.py (weapons) from maps/dgf_props.py: do not edit by hand, re-run the script.",
        "--",
        "-- WeaponModels.build(name, anchored?) -> Model  (name: HarpoonGun | Harpoon | Bazooka | Missile)",
        "--   * PrimaryPart \"Root\" (invisible) sits on the model's origin: the grip for the guns (where the right hand",
        "--     closes), the point for the projectiles (harpoon tip, missile nose). Barrels and flights look along -Z,",
        "--     so model:PivotTo(CFrame.lookAt(from, to)) aims it.",
        "--   * each table group is a child Model: HarpoonGun.Harpoon is the loaded harpoon, Bazooka.Missile the loaded",
        "--     missile (hide or destroy them when firing).",
        "--   * anchors from models/weapons_spots.json are Attachments on Root: HarpoonGun.Root.Muzzle / RopeAttach,",
        "--     Harpoon.Root.RopeAttach, Bazooka.Root.Muzzle / Backblast, Missile.Root.Exhaust (looks out of the nozzle).",
        "--   * anchored ~= false (default): every part anchored (client effects moved with PivotTo). anchored == false:",
        "--     parts welded to Root, massless, ready to be welded to a hand.",
        "--   No part collides, touches or is hit by raycasts.",
        "local WeaponModels = {}",
        "",
        "local SHAPES = { " + ", ".join(f'"{s}"' for s in LUAU_SHAPES) + " }",
        "local MATERIALS = { " + ", ".join(f"Enum.Material.{LUAU_MATERIALS[m]}" for m in mats) + " }",
        "",
        "-- per part: group, shape, material, r, g, b, size x y z, position x y z, quaternion x y z w, transparency",
        "local MODELS = {",
    ]

    def num(v, digits):
        s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s

    for name, model in models.items():
        groups = []
        for p in model.prims:
            if p["group"] not in groups:
                groups.append(p["group"])
        lines.append(f"\t{name} = {{")
        lines.append("\t\tgroups = { " + ", ".join(f'"{g}"' for g in groups) + " },")
        anchors = []
        for key, sp in spots[name].items():
            c = sp["cframe"]
            anchors.append(f"{key} = CFrame.new(" + ", ".join(num(v, 4) for v in c) + ")")
        lines.append("\t\tanchors = { " + ", ".join(anchors) + " },")
        lines.append("\t\tparts = {")
        for p in model.prims:
            q = M.quat_from_rot(p["rot"])
            row = [groups.index(p["group"]) + 1, LUAU_SHAPES.index(p["shape"]) + 1, mats.index(p["mat"]) + 1,
                   *p["color"]]
            vals = [str(v) for v in row] + [num(v, 3) for v in p["size"]] + [num(v, 3) for v in p["pos"]]
            vals += [num(v, 5) for v in q] + [num(p["transparency"], 2)]
            lines.append("\t\t\t{ " + ", ".join(vals) + " },")
        lines.append("\t\t},")
        lines.append("\t},")
    lines += [
        "}",
        "",
        "function WeaponModels.build(name: string, anchored: boolean?): Model",
        "\tlocal def = MODELS[name]",
        "\tassert(def, \"unknown weapon model \" .. tostring(name))",
        "\tlocal fixed = anchored ~= false",
        "\tlocal model = Instance.new(\"Model\")",
        "\tmodel.Name = name",
        "\tlocal root = Instance.new(\"Part\")",
        "\troot.Name = \"Root\"",
        "\troot.Size = Vector3.new(0.2, 0.2, 0.2)",
        "\troot.Transparency = 1",
        "\troot.CanCollide = false",
        "\troot.CanQuery = false",
        "\troot.CanTouch = false",
        "\troot.Massless = true",
        "\troot.Anchored = fixed",
        "\troot.CFrame = CFrame.identity",
        "\troot.Parent = model",
        "\tmodel.PrimaryPart = root",
        "\tfor key, cf in def.anchors do",
        "\t\tlocal att = Instance.new(\"Attachment\")",
        "\t\tatt.Name = key",
        "\t\tatt.CFrame = cf",
        "\t\tatt.Parent = root",
        "\tend",
        "\tlocal holders = {}",
        "\tfor i, group in def.groups do",
        "\t\tlocal holder = Instance.new(\"Model\")",
        "\t\tholder.Name = group",
        "\t\tholder.Parent = model",
        "\t\tholders[i] = holder",
        "\tend",
        "\tfor _, row in def.parts do",
        "\t\tlocal shape = SHAPES[row[2]]",
        "\t\tlocal part = if shape == \"Wedge\" then Instance.new(\"WedgePart\") else Instance.new(\"Part\")",
        "\t\tif shape == \"Cylinder\" then",
        "\t\t\tpart.Shape = Enum.PartType.Cylinder",
        "\t\telseif shape == \"Ball\" then",
        "\t\t\tpart.Shape = Enum.PartType.Ball",
        "\t\tend",
        "\t\tpart.Material = MATERIALS[row[3]]",
        "\t\tpart.Color = Color3.fromRGB(row[4], row[5], row[6])",
        "\t\tpart.Size = Vector3.new(row[7], row[8], row[9])",
        "\t\tpart.CFrame = CFrame.new(row[10], row[11], row[12], row[13], row[14], row[15], row[16])",
        "\t\tpart.Transparency = row[17]",
        "\t\tpart.TopSurface = Enum.SurfaceType.Smooth",
        "\t\tpart.BottomSurface = Enum.SurfaceType.Smooth",
        "\t\tpart.CanCollide = false",
        "\t\tpart.CanQuery = false",
        "\t\tpart.CanTouch = false",
        "\t\tpart.Massless = true",
        "\t\tpart.Anchored = fixed",
        "\t\tpart.Parent = holders[row[1]]",
        "\t\tif not fixed then",
        "\t\t\tlocal weld = Instance.new(\"WeldConstraint\")",
        "\t\t\tweld.Part0 = root",
        "\t\t\tweld.Part1 = part",
        "\t\t\tweld.Parent = part",
        "\t\tend",
        "\tend",
        "\treturn model",
        "end",
        "",
        "-- anchor CFrames in the model's own frame, e.g. WeaponModels.anchor(\"Missile\", \"Exhaust\")",
        "function WeaponModels.anchor(name: string, key: string): CFrame",
        "\tlocal def = MODELS[name]",
        "\treturn def and def.anchors[key] or CFrame.identity",
        "end",
        "",
        "return WeaponModels",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote", path)


def scale_dummy():
    """A plain blocky R15-sized figure (5.2 studs) for scale in the weapon previews."""
    d = M.Asset("Dummy")
    grey, dark = (168, 172, 180), (120, 124, 134)
    d.box("Dummy", (-0.95, 0.0, -0.45), (-0.05, 2.0, 0.45), dark, "Smooth")
    d.box("Dummy", (0.05, 0.0, -0.45), (0.95, 2.0, 0.45), dark, "Smooth")
    d.box("Dummy", (-1.0, 2.0, -0.5), (1.0, 4.0, 0.5), grey, "Smooth")
    d.box("Dummy", (-2.0, 2.1, -0.45), (-1.05, 3.95, 0.45), grey, "Smooth")
    d.box("Dummy", (1.05, 2.1, -0.45), (2.0, 3.95, 0.45), grey, "Smooth")
    d.prim("Dummy", "Ball", (1.25, 1.25, 1.25), (0.0, 4.65, 0.0), M.IDENT, grey, "Smooth")
    return d


def do_weapons(out_dir):
    import dgf_props as P
    models, spots = P.build_weapons()
    folder = os.path.join(out_dir, "models")
    if MODE in ("export", "all"):
        for name, model in models.items():
            write_table(model.prims, folder, WEAPON_FILES[name])
        spots["primitives"] = {k: len(m.prims) for k, m in models.items()}
        with open(os.path.join(folder, "weapons_spots.json"), "w", encoding="utf-8") as f:
            json.dump(spots, f, indent=1)
        print("wrote", os.path.join(folder, "weapons_spots.json"))
        weapon_models_luau(models, spots, os.path.join(out_dir, "luau", "WeaponModels.luau"))
    if MODE in ("render", "all"):
        prev = os.path.join(folder, "previews")
        os.makedirs(prev, exist_ok=True)
        views = {"HarpoonGun": ((6.5, 3.2, -6.0), (0.0, 0.6, -2.3), 30), "Harpoon": ((4.6, 2.6, -1.0), (0.0, 0.0, 3.6), 30),
                 "Bazooka": ((6.2, 3.2, -5.4), (0.0, 0.8, -0.2), 30), "Missile": ((3.0, 1.6, -1.6), (0.0, 0.0, 1.9), 34)}
        for name, model in models.items():
            setup_scene(sky=(0.62, 0.74, 0.9), res=(1000, 700), samples=48)
            build_meshes(model.prims, name)
            eye, target, lens = views[name]
            render(os.path.join(prev, WEAPON_FILES[name] + "_preview.png"), camera("c", eye, target, lens))
        # the four side by side with a 5.2-stud figure for scale
        setup_scene(sky=(0.62, 0.74, 0.9), res=(1400, 700), samples=48)
        build_meshes(scale_dummy().prims, "Dummy", offset=(-4.6, 0.0, 0.0))
        # stacked, every barrel turned towards screen left (+X), origins on x = 1
        place = {"HarpoonGun": (1.0, 5.4), "Bazooka": (1.0, 2.9), "Harpoon": (1.6, 1.3), "Missile": (1.6, 0.45)}
        for name, (x, y) in place.items():
            build_meshes(models[name].prims, name + "L", offset=(x, y, 0.0), rot=M.rot_y(-math.pi / 2))
        floor = M.Asset("Floor")
        floor.box("Floor", (-14, -0.4, -6), (14, 0, 6), (210, 214, 222), "Smooth")
        build_meshes(floor.prims, "Floor")
        render(os.path.join(prev, "weapons_lineup_preview.png"), camera("c", (0.6, 3.6, -15.5), (0.6, 3.1, 0.0), 32))
    return models


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
    if "ocean_decor" in WHAT:
        do_ocean_decor(out)
    if "weapons" in WHAT:
        do_weapons(out)


main()
