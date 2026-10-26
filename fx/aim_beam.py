# Harpoon aim column: a vertical band of realistic red fog (same look as fog_flipbook), rendered as a Cycles volume.
#
#   blender -b --factory-startup --python aim_beam.py -- <out_dir> [samples=64]
#
# aim_beam_flipbook.png : 4x4 flipbook (1024x1024, 256 px frames), a looping slice of a thick fog column seen from
#                         the side. Every frame tiles VERTICALLY (top row flows into the bottom row) and fades out
#                         softly on its left and right edges; the dense body covers the middle ~80 % of the width.
# aim_beam_preview_*.png, aim_beam_tiling_check.png : contact sheets over the pond / sky colours, and one frame
#                         stacked three times to check the vertical seam.
# How it stays seamless: the noise is periodic along the column (the height is mapped onto a circle in 4D noise
# space), the volume is three tiles tall so the middle tile is lit exactly like its neighbours, and the render is
# taller than one tile and cropped, so the denoiser never sees the seam rows as image borders.
# The loop: the fog flows down one tile per loop while it morphs between two noise fields
# (cos/sin weighting keeps the contrast constant), so frame 15 flows into frame 0.
import math
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath(".")
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
COUNT = int(argv[2]) if len(argv) > 2 else 16      # fewer frames = quick look test (no sheet)
os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(OUT, "_aim_frames")
os.makedirs(TMP, exist_ok=True)

RES = 256                  # one frame
PAD = 32                   # extra rows rendered above and below, cropped away
FRAMES = 16
SEED = 3.7
FREQ = 3.2                 # noise cells across one unit (the frame is 1 unit wide and 1 unit tall)
MORPH = 1.0                # how far the two noise fields are blended over a loop (1 = full cos/sin turn)
DENSITY = 5.0
EMIT = 0.8
HAZE = 0.18                # even fog inside the column, under the clumps
CORE = (160, 18, 18)       # sRGB, same palette as fog_flipbook (a touch deeper: the column is seen edge-on)
EDGE = (255, 60, 40)
R_SOLID = 0.33             # radius (frame = 1 unit wide) where the fog starts to thin out
R_EDGE = 0.485             # radius where it is gone


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
scene.render.resolution_y = RES + 2 * PAD
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.42, 0.55, 0.7, 1.0)
bg.inputs["Strength"].default_value = 0.45

# key light from behind the camera and a little above: the front of the column is lit, both sides darken the same
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 7.0
sun_data.angle = math.radians(8)
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(90 - 28), 0.0, 0.0)   # pointing along +Y and down 28 deg
scene.collection.objects.link(sun)

cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = (RES + 2 * PAD) / RES               # the taller side spans 1 + padding units
cam = bpy.data.objects.new("Cam", cam_data)
cam.location = (0.0, -6.0, 0.0)
cam.rotation_euler = (math.pi / 2, 0.0, 0.0)               # looking along +Y, image up = +Z
scene.collection.objects.link(cam)
scene.camera = cam


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

    def smooth(self, value, lo, hi):
        """0 at lo, 1 at hi, smoothstep in between and clamped (lo > hi is a falling edge)."""
        n = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self.feed(n.inputs["Value"], value)
        n.inputs["From Min"].default_value = min(lo, hi)
        n.inputs["From Max"].default_value = max(lo, hi)
        n.inputs["To Min"].default_value = 0.0 if lo < hi else 1.0
        n.inputs["To Max"].default_value = 1.0 if lo < hi else 0.0
        return n.outputs["Result"]

    def combine(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        self.feed(n.inputs[0], x)
        self.feed(n.inputs[1], y)
        self.feed(n.inputs[2], z)
        return n.outputs[0]

    def noise(self, vector, w, detail, roughness, distortion=0.0):
        n = self.node("ShaderNodeTexNoise", noise_dimensions="4D")
        self.feed(n.inputs["Vector"], vector)
        self.feed(n.inputs["W"], w)
        n.inputs["Scale"].default_value = 1.0
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = roughness
        n.inputs["Distortion"].default_value = distortion
        return n.outputs["Fac"]


def column_material(t):
    """t: 0..1 position in the loop."""
    mat = bpy.data.materials.new("AimFog")
    mat.use_nodes = True
    g = Graph(mat)
    sep = g.node("ShaderNodeSeparateXYZ")
    g.feed(sep.inputs[0], g.node("ShaderNodeTexCoord").outputs["Object"])
    x, y, z = sep.outputs[0], sep.outputs[1], sep.outputs[2]

    # height -> angle: one turn per unit of height, shifted by t so the fog flows down one tile per loop
    phi = g.math("MULTIPLY", g.math("ADD", z, t), 2 * math.pi)
    ring = FREQ / (2 * math.pi)                              # circle radius that keeps the noise cells round
    cz = g.math("MULTIPLY", g.math("COSINE", phi), ring)
    sz = g.math("MULTIPLY", g.math("SINE", phi), ring)
    # a gentle twist around the axis that varies with height and breathes over the loop
    twist = g.math("MULTIPLY", g.math("SINE", g.math("ADD", phi, 1.3)), 0.35 * math.sin(2 * math.pi * t) + 0.25)
    ct, st = g.math("COSINE", twist), g.math("SINE", twist)
    xr = g.math("SUBTRACT", g.math("MULTIPLY", x, ct), g.math("MULTIPLY", y, st))
    yr = g.math("ADD", g.math("MULTIPLY", x, st), g.math("MULTIPLY", y, ct))

    def field(offset, detail, rough, dist, k=1.0):
        # k scales the cell size; the circle radius scales with it so the column stays periodic and the cells round
        p = g.combine(g.math("MULTIPLY", xr, FREQ * k), g.math("MULTIPLY", yr, FREQ * k), g.math("MULTIPLY", cz, k))
        return g.noise(p, g.math("ADD", g.math("MULTIPLY", sz, k), SEED + offset), detail, rough, dist)

    # two independent fields blended by (cos, sin) of the loop angle: the contrast stays the same all along
    a = math.cos(2 * math.pi * t * MORPH)
    b = math.sin(2 * math.pi * t * MORPH)

    def morph(off1, off2, detail, rough, dist, k=1.0):
        f1 = g.math("SUBTRACT", field(off1, detail, rough, dist, k), 0.5)
        f2 = g.math("SUBTRACT", field(off2, detail, rough, dist, k), 0.5)
        return g.math("ADD", g.math("ADD", g.math("MULTIPLY", f1, a), g.math("MULTIPLY", f2, b)), 0.5)

    edge_noise = morph(0.0, 20.0, 3.0, 0.55, 0.3)
    wisps = morph(3.1, 23.1, 6.0, 0.62, 2.6, 0.75)
    billow = morph(7.7, 27.7, 4.0, 0.55, 0.0, 1.6)
    threads_noise = morph(11.3, 31.3, 6.0, 0.58, 1.8)

    radius = g.math("SQRT", g.math("ADD", g.math("MULTIPLY", x, x), g.math("MULTIPLY", y, y)))
    ragged = g.math("ADD", radius, g.math("MULTIPLY", g.math("SUBTRACT", edge_noise, 0.5), 0.16))
    shape = g.smooth(ragged, R_EDGE, R_SOLID)
    clumps = g.math("MULTIPLY", g.smooth(wisps, 0.38, 0.70), g.math("ADD", 0.55, g.math("MULTIPLY", billow, 0.9)))
    ridge = g.math("SUBTRACT", 1.0, g.math("ABSOLUTE", g.math("SUBTRACT", g.math("MULTIPLY", threads_noise, 2.0), 1.0)))
    threads = g.smooth(ridge, 0.80, 0.96)
    rim = g.math("MULTIPLY", g.smooth(ragged, R_SOLID - 0.08, R_SOLID + 0.06), g.smooth(ragged, R_EDGE + 0.02, R_EDGE - 0.05))
    # haze everywhere inside (keeps the column readable as one solid zone), clumps on top, threads fraying the rim
    body = g.math("ADD", g.math("MULTIPLY", clumps, 1.0), HAZE)
    body = g.math("ADD", body, g.math("MULTIPLY", threads, g.math("MULTIPLY", rim, 0.9)))
    dens = g.math("MULTIPLY", shape, body)

    ramp = g.node("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.12, lin(CORE)
    els[1].position, els[1].color = 0.47, lin(EDGE)
    g.feed(ramp.inputs["Fac"], ragged)

    vol = g.node("ShaderNodeVolumePrincipled")
    g.feed(vol.inputs["Color"], ramp.outputs["Color"])
    g.feed(vol.inputs["Density"], g.math("MULTIPLY", dens, DENSITY))
    vol.inputs["Absorption Color"].default_value = lin((150, 30, 26))
    vol.inputs["Anisotropy"].default_value = 0.25
    g.feed(vol.inputs["Emission Color"], ramp.outputs["Color"])
    g.feed(vol.inputs["Emission Strength"], g.math("MULTIPLY", dens, EMIT))
    out = g.node("ShaderNodeOutputMaterial")
    g.feed(out.inputs["Volume"], vol.outputs[0])
    return mat


# three tiles tall: the middle one is what the camera keeps, the others give it identical light and shadow
bpy.ops.mesh.primitive_cube_add(size=1.0)
domain = bpy.context.active_object
domain.scale = (1.1, 1.1, 3.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


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
    print("saved", os.path.join(OUT, name), flush=True)


def over(rgba, color):
    out = np.zeros_like(rgba)
    out[:, :, :3] = np.array([v / 255 for v in color])
    out[:, :, 3] = 1
    a = rgba[:, :, 3:4]
    out[:, :, :3] = rgba[:, :, :3] * a + out[:, :, :3] * (1 - a)
    return out


frames = []
for f in range(0, FRAMES, max(1, FRAMES // COUNT)):
    domain.data.materials.clear()
    domain.data.materials.append(column_material(f / FRAMES))
    path = os.path.join(TMP, f"aim_{f:02d}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    full = load_rgba(path)
    full[:, :, :3] = np.clip(full[:, :, :3], 0, 1)
    frames.append(full[PAD:PAD + RES])
    print("aim frame", f + 1, "/", FRAMES, flush=True)

if len(frames) < FRAMES:
    strip = np.concatenate([np.concatenate([fr] * 2, 0) for fr in frames], 1)
    save_png("aim_beam_quicklook.png", over(strip, (78, 214, 251)))
    prof = np.mean([fr[:, :, 3] for fr in frames], axis=0).mean(axis=0)
    print("alpha at the centre %.2f, quartiles of the centre column %s" % (prof[RES // 2], np.percentile(frames[0][:, RES // 2, 3], [10, 50, 90])))
    sys.exit(0)

# the sheet, its previews and a seam check
sheet = np.zeros((4 * RES, 4 * RES, 4), np.float32)
for i, fr in enumerate(frames):
    r, c = divmod(i, 4)
    sheet[r * RES:(r + 1) * RES, c * RES:(c + 1) * RES] = fr
save_png("aim_beam_flipbook.png", sheet)
save_png("aim_beam_preview_water.png", over(sheet, (78, 214, 251)))
save_png("aim_beam_preview_sky.png", over(sheet, (150, 205, 245)))
save_png("aim_beam_tiling_check.png", over(np.concatenate([np.concatenate([frames[0]] * 3, 0), np.concatenate([frames[8]] * 3, 0)], 1), (78, 214, 251)))

# numbers for the README: how wide the fog is, and how big the seam step is next to an ordinary row step
alpha = np.mean([fr[:, :, 3] for fr in frames], axis=0)
prof = alpha.mean(axis=0)
cols = np.where(prof > 0.5 * prof.max())[0]
print("alpha at the centre %.2f, at the edges %.3f / %.3f" % (prof[RES // 2], prof[0], prof[-1]))
print("half-max width as a share of the frame: %.3f" % ((cols[-1] - cols[0] + 1) / RES))
seam = np.mean([np.abs(fr[0] - fr[-1]).mean() for fr in frames])
inner = np.mean([np.abs(fr[1:] - fr[:-1]).mean() for fr in frames])
print("vertical seam step %.4f vs ordinary row step %.4f" % (seam, inner))
loop = np.abs(frames[0] - frames[-1]).mean()
step = np.mean([np.abs(frames[i + 1] - frames[i]).mean() for i in range(FRAMES - 1)])
print("loop step (15 -> 0) %.4f vs ordinary frame step %.4f" % (loop, step))
print("done")
