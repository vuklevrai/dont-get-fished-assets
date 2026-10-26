# Realistic red capture fog (the one realistic element of the game), rendered as a Cycles volume.
#
#   blender -b --factory-startup --python fog_flipbook.py -- <out_dir> [frames=64]
#
# fog_flipbook.png    : 4x4 flipbook (1024x1024, 256 px frames) of a looping, slowly boiling fog pool seen
#                       from three-quarters above, roughly round with a ragged edge.
# fog_flipbook_8x8.png: the same loop with 64 frames of 128 px (smoother motion, softer image).
# fog_puff.png        : one isolated puff (512 px), a particle texture to add thickness.
# Straight-alpha RGBA. The loop is seamless: the noise is sampled on a circle in (z, w) space, so the last
# frame flows into the first. Deterministic (fixed seeds, no simulation cache).
import math
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
FRAMES = int(argv[1]) if len(argv) > 1 else 64
os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(OUT, "_fog_frames")
os.makedirs(TMP, exist_ok=True)

RES = 256
SAMPLES = 64
SEED = 7.3                 # moves the whole noise field: another seed = another fog
BOIL = 0.42                # radius of the (z, w) loop circle: how much the fog churns over a loop
SWIRL = 0.22               # rad of back-and-forth twist at the centre over a loop
DENSITY = 6.5
EMIT = 1.1                 # self glow, so the fog stays readable over bright water
CORE = (170, 20, 20)       # sRGB, centre of the fog
EDGE = (255, 60, 40)       # sRGB, ragged rim
ELEVATION = 58             # degrees: camera looking down at three quarters


def lin(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (ch(c[0]), ch(c[1]), ch(c[2]), 1.0)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.seed = 1
scene.cycles.volume_step_rate = 1.0
scene.cycles.volume_max_steps = 256
scene.render.film_transparent = True
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.42, 0.55, 0.7, 1.0)     # soft sky fill from every side
bg.inputs["Strength"].default_value = 0.45

sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 7.5
sun_data.angle = math.radians(8)
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(38), math.radians(-24), math.radians(30))
scene.collection.objects.link(sun)

cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim_camera(elevation_deg, scale, target_z=0.05):
    e = math.radians(elevation_deg)
    dist = 12
    cam.location = (0.0, -dist * math.cos(e), target_z + dist * math.sin(e))
    cam.rotation_euler = (math.pi / 2 - e, 0.0, 0.0)
    cam_data.ortho_scale = scale


# ---------------------------------------------------------------- volume material
class Graph:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.nt.nodes.clear()

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def feed(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.nt.links.new(val, sock)
        else:
            sock.default_value = val

    def math(self, op, a, b=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.feed(n.inputs[0], a)
        if b is not None:
            self.feed(n.inputs[1], b)
        return n.outputs[0]

    def vmath(self, op, a, b=None):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self.feed(n.inputs[0], a)
        if b is not None:
            self.feed(n.inputs[1], b)
        return n.outputs[0] if op not in ("LENGTH", "DOT_PRODUCT") else n.outputs["Value"]

    def smooth(self, value, lo, hi):
        """0 at lo, 1 at hi, smoothstep in between and clamped (lo > hi is a falling edge)."""
        n = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self.feed(n.inputs["Value"], value)
        n.inputs["From Min"].default_value = min(lo, hi)
        n.inputs["From Max"].default_value = max(lo, hi)
        n.inputs["To Min"].default_value = 0.0 if lo < hi else 1.0
        n.inputs["To Max"].default_value = 1.0 if lo < hi else 0.0
        return n.outputs["Result"]

    def noise(self, vector, w, scale, detail, roughness, distortion=0.0):
        n = self.node("ShaderNodeTexNoise", noise_dimensions="4D")
        self.feed(n.inputs["Vector"], vector)
        self.feed(n.inputs["W"], w)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = roughness
        n.inputs["Distortion"].default_value = distortion
        return n.outputs["Fac"]


def fog_material(phase_value, puff=False):
    """phase_value: 0..1 position in the loop. puff=True makes a single round puff instead of the pool."""
    mat = bpy.data.materials.new("Fog")
    mat.use_nodes = True
    g = Graph(mat)
    theta = 2 * math.pi * phase_value
    coord = g.node("ShaderNodeTexCoord").outputs["Object"]

    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], coord)
    xy = g.node("ShaderNodeCombineXYZ")
    g.feed(xy.inputs[0], sep.outputs[0])
    g.feed(xy.inputs[1], sep.outputs[1])
    radius = g.vmath("LENGTH", xy.outputs[0])

    # a gentle back-and-forth twist, strongest in the middle
    twist = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, radius, clamp=True), SWIRL * math.sin(theta))
    rot = g.node("ShaderNodeVectorRotate", rotation_type="Z_AXIS")
    g.feed(rot.inputs["Vector"], coord)
    g.feed(rot.inputs["Angle"], twist)

    # loop: the sample point travels round a circle in (z, w)
    offset = g.node("ShaderNodeCombineXYZ")
    offset.inputs[2].default_value = BOIL * math.sin(theta)
    q = g.vmath("ADD", rot.outputs[0], offset.outputs[0])
    w = SEED + BOIL * math.cos(theta)

    # ragged outline: two octaves of slow noise push the rim in and out
    edge_noise = g.noise(q, w, 1.6, 4.0, 0.6, 0.4)
    # swirling wisps: domain-warped noise, thresholded into soft clumps and threads
    wisps = g.noise(q, w + 3.1, 1.3, 6.0, 0.62, 2.8)
    billow = g.noise(q, w + 7.7, 4.0, 5.0, 0.55)
    clumps = g.smooth(wisps, 0.42, 0.66)
    # thin threads: the ridges of a second warped noise, kept near the rim where smoke frays
    threads_noise = g.noise(q, w + 11.3, 2.0, 6.0, 0.58, 1.8)
    ridge = g.math("SUBTRACT", 1.0, g.math("ABSOLUTE", g.math("SUBTRACT", g.math("MULTIPLY", threads_noise, 2.0), 1.0)))
    threads = g.smooth(ridge, 0.82, 0.96)

    ragged = g.math("ADD", radius, g.math("MULTIPLY", g.math("SUBTRACT", edge_noise, 0.5), 0.85))
    if puff:
        # a lumpy ball with billows
        dist3 = g.vmath("LENGTH", coord)
        ragged3 = g.math("ADD", dist3, g.math("MULTIPLY", g.math("SUBTRACT", edge_noise, 0.5), 0.6))
        shape = g.smooth(ragged3, 0.98, 0.35)
        clumps = g.smooth(billow, 0.3, 0.7)
        tone = ragged3
    else:
        across = g.smooth(ragged, 1.2, 0.45)
        # a low dome sitting on the water: thick in the middle, thinner at the rim
        top = g.math("ADD", g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.math("POWER", g.math("MINIMUM", ragged, 1.2), 2.0)), 0.55), 0.1)
        z_noisy = g.math("ADD", sep.outputs[2], g.math("MULTIPLY", g.math("SUBTRACT", billow, 0.5), 0.5))
        under = g.smooth(sep.outputs[2], -0.5, -0.32)
        over = g.smooth(g.math("SUBTRACT", z_noisy, top), 0.05, -0.3)
        shape = g.math("MULTIPLY", across, g.math("MULTIPLY", under, over))
        tone = ragged

    # haze thick in the middle, clumps everywhere, threads fraying out at the rim
    rim = g.math("MULTIPLY", g.smooth(tone, 0.45, 0.8), g.smooth(tone, 1.25, 0.95))
    body = g.math("ADD", g.math("MULTIPLY", clumps, 1.0), g.math("MULTIPLY", g.smooth(tone, 0.85, 0.15), 0.28))
    body = g.math("ADD", body, g.math("MULTIPLY", threads, g.math("MULTIPLY", rim, 0.8)))
    density = g.math("MULTIPLY", g.math("MULTIPLY", shape, body), DENSITY)

    ramp = g.node("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.25, lin(CORE)
    els[1].position, els[1].color = 0.95, lin(EDGE)
    g.feed(ramp.inputs["Fac"], tone)

    vol = g.node("ShaderNodeVolumePrincipled")
    g.feed(vol.inputs["Color"], ramp.outputs["Color"])
    g.feed(vol.inputs["Density"], density)
    vol.inputs["Absorption Color"].default_value = lin((150, 30, 26))
    vol.inputs["Anisotropy"].default_value = 0.25
    g.feed(vol.inputs["Emission Color"], ramp.outputs["Color"])
    g.feed(vol.inputs["Emission Strength"], g.math("MULTIPLY", g.math("MULTIPLY", shape, body), EMIT))
    out = g.node("ShaderNodeOutputMaterial")
    g.feed(out.inputs["Volume"], vol.outputs[0])
    return mat


def make_domain(size, z_centre):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, z_centre))
    ob = bpy.context.active_object
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.location = (0.0, 0.0, 0.0)
    for v in ob.data.vertices:
        v.co.z += z_centre
    return ob


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return np.flipud(px)        # row 0 = top


def save_png(name, rgba):
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.flipud(np.clip(rgba, 0, 1)).astype(np.float32).ravel())
    img.filepath_raw = os.path.join(OUT, name)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("saved", os.path.join(OUT, name))


def unpremultiply(rgba):
    # Cycles writes straight alpha already for PNG; keep the colour of very thin smoke clean
    out = rgba.copy()
    out[:, :, :3] = np.clip(out[:, :, :3], 0, 1)
    return out


def atlas(frames, grid, res):
    sheet = np.zeros((grid * res, grid * res, 4), dtype=np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, grid)
        sheet[r * res:(r + 1) * res, c * res:(c + 1) * res] = f
    return sheet


def over(rgba, color):
    bgc = np.zeros_like(rgba)
    bgc[:, :, :3] = np.array([v / 255 for v in color])
    bgc[:, :, 3] = 1
    a = rgba[:, :, 3:4]
    bgc[:, :, :3] = rgba[:, :, :3] * a + bgc[:, :, :3] * (1 - a)
    return bgc


# ---------------------------------------------------------------- the looping pool
domain = make_domain((2.9, 2.9, 1.3), 0.05)
aim_camera(ELEVATION, 2.5)


def render_loop(count, res, tag):
    scene.render.resolution_x = scene.render.resolution_y = res
    out = []
    for f in range(count):
        domain.data.materials.clear()
        domain.data.materials.append(fog_material(f / count))
        path = os.path.join(TMP, f"{tag}_{f:02d}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(unpremultiply(load_rgba(path)))
        print(tag, "frame", f + 1, "/", count, flush=True)
    return out


# 16 frames at 256 px for the main sheet, and the same loop with 64 frames at 128 px for the 8x8 sheet
frames = render_loop(16, RES, "fog")
main = atlas(frames, 4, RES)
save_png("fog_flipbook.png", main)
save_png("fog_preview_water.png", over(main, (78, 214, 251)))
save_png("fog_preview_sky.png", over(main, (150, 205, 245)))
if FRAMES >= 64:
    small = render_loop(64, RES // 2, "fog8")
    save_png("fog_flipbook_8x8.png", atlas(small, 8, RES // 2))
scene.render.resolution_x = scene.render.resolution_y = RES

# coverage of the frame, to size the billboard against the hit circle
alpha = np.mean([fr[:, :, 3] for fr in frames], axis=0)
cols = np.where(alpha.max(axis=0) > 0.2)[0]
print("fog width (alpha > 0.2) as a share of the frame: %.3f" % ((cols[-1] - cols[0] + 1) / RES))

# ---------------------------------------------------------------- one isolated puff
bpy.data.objects.remove(domain, do_unlink=True)
puff = make_domain((2.2, 2.2, 2.2), 0.0)
puff.data.materials.append(fog_material(0.37, puff=True))
aim_camera(ELEVATION, 2.3, 0.0)
scene.render.resolution_x = scene.render.resolution_y = 512
path = os.path.join(TMP, "puff.png")
scene.render.filepath = path
bpy.ops.render.render(write_still=True)
puff_rgba = unpremultiply(load_rgba(path))
save_png("fog_puff.png", puff_rgba)
print("done")
