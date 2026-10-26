# Cartoon pond water: a seamless, looping animated texture built from shader nodes.
#
# Run headless:
#   blender -b --factory-startup --python water_texture.py -- <out_dir> preview|anim
#
# The pattern lives on a 1x1 tile. Seamless tiling comes from mapping (u, v) onto a flat torus
# in 4D (cos u, sin u, cos v, sin v) before sampling the 4D Voronoi/Noise textures; the loop in
# time comes from moving those samples around a small circle over the animation.
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_DIR = os.path.abspath(argv[0]) if argv else os.path.abspath("frames")
MODE = argv[1] if len(argv) > 1 else "preview"

FRAMES = 24
RES = 512
TAU = 2 * math.pi

OSL_PATH = os.path.join(os.path.dirname(OUT_DIR), "cartoon_cells.osl")

# look (tuned against the reference screenshot)
CELLS = 7               # cells across the tile (integer so it wraps)
JITTER = 0.85           # how irregular the cells are (JITTER / 2 + ORBIT must stay below 0.5)
ORBIT = 0.07            # how far each cell's site travels over the loop (the ripple)
CELL_SHADE = 0.6        # per-cell darkening variation
LINE_WIDTH = 0.03       # distance-to-edge (cell units) below which we draw the bright line
LINE_SOFT = 0.03
GLOW_WIDTH = 0.22       # lighter band inside each cell, next to its edge
GLOW_AMOUNT = 0.6
WOBBLE_RADIUS = 0.9     # torus radius of the edge-wobble noise
WOBBLE_AMOUNT = 0.022   # in tile units
WOBBLE_DRIFT = 0.45
WIGGLE_RADIUS = 2.4     # finer noise that makes the lines a bit wavy
WIGGLE_AMOUNT = 0.006

# pre-compensated for the pond's lighting in Roblox (which pushes green up), so that in game the
# cells read ~(78, 214, 251) and the lines ~(135, 241, 255) like the reference
COLORS = {
    "cell": (80, 183, 246),
    "cell_dark": (63, 176, 242),
    "glow": (99, 192, 247),
    "line": (139, 218, 255),
}


def linear(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (ch(rgb[0]), ch(rgb[1]), ch(rgb[2]), 1.0)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------------------------------------------------------- render settings
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.shading_system = True  # Open Shading Language, for the cell script
scene.cycles.samples = 16
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 0
scene.cycles.filter_width = 1.2
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.frame_start = 0
scene.frame_end = FRAMES - 1
scene.render.fps = 12

# ---------------------------------------------------------------- camera + plane
cam_data = bpy.data.cameras.new("TileCamera")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 1.0
cam = bpy.data.objects.new("TileCamera", cam_data)
cam.location = (0, 0, 5)
scene.collection.objects.link(cam)
scene.camera = cam

# the plane is larger than the 1x1 frame so border pixels still see the (periodic) pattern
mesh = bpy.data.meshes.new("WaterTile")
s = 1.5
mesh.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("WaterTile", mesh)
scene.collection.objects.link(plane)

# ---------------------------------------------------------------- material
mat = bpy.data.materials.new("CartoonWater")
mat.use_nodes = True
plane.data.materials.append(mat)
nt = mat.node_tree
nodes, links = nt.nodes, nt.links
nodes.clear()

_col = [0]


def node(kind, label=None, **props):
    n = nodes.new(kind)
    n.location = (_col[0] * 220, -len([x for x in nodes if abs(x.location.x - _col[0] * 220) < 1]) * 160)
    if label:
        n.label = label
    for k, v in props.items():
        setattr(n, k, v)
    return n


def feed(sock, val):
    if isinstance(val, bpy.types.NodeSocket):
        links.new(val, sock)
    else:
        sock.default_value = val


def op(operation, a, b=None):
    n = node("ShaderNodeMath", operation=operation)
    feed(n.inputs[0], a)
    if b is not None:
        feed(n.inputs[1], b)
    return n.outputs[0]


def mix(fac, a, b):
    n = node("ShaderNodeMix", data_type="RGBA")
    colors = [s for s in n.inputs if s.type == "RGBA"]
    feed(n.inputs[0], fac)
    feed(colors[0], a)
    feed(colors[1], b)
    out = [s for s in n.outputs if s.type == "RGBA"]
    return out[0]


def rgb(name):
    n = node("ShaderNodeRGB", label=name)
    n.outputs[0].default_value = linear(COLORS[name])
    return n.outputs[0]


def torus(u, v, radius, offset=None):
    """(u, v) on the flat 4D torus -> (vector socket, w socket). offset = (dx, dy, dz, dw) sockets."""
    au, av = op("MULTIPLY", u, TAU), op("MULTIPLY", v, TAU)
    comps = [
        op("MULTIPLY", op("COSINE", au), radius),
        op("MULTIPLY", op("SINE", au), radius),
        op("MULTIPLY", op("COSINE", av), radius),
        op("MULTIPLY", op("SINE", av), radius),
    ]
    if offset:
        comps = [c if o is None else op("ADD", c, o) for c, o in zip(comps, offset)]
    comb = node("ShaderNodeCombineXYZ")
    for i in range(3):
        feed(comb.inputs[i], comps[i])
    return comb.outputs[0], comps[3]


# column 0: coordinates and time
_col[0] = 0
coord = node("ShaderNodeTexCoord")
sep = node("ShaderNodeSeparateXYZ")
links.new(coord.outputs["Object"], sep.inputs[0])
u = op("ADD", sep.outputs[0], 0.5)
v = op("ADD", sep.outputs[1], 0.5)
time = node("ShaderNodeValue", label="Time (loops 0 -> 1)")
fcurve = time.outputs[0].driver_add("default_value")
fcurve.driver.type = "SCRIPTED"
fcurve.driver.expression = f"frame / {FRAMES}"
t_angle = op("MULTIPLY", time.outputs[0], TAU)
t_cos, t_sin = op("COSINE", t_angle), op("SINE", t_angle)

# column 1-2: edge wobble (animated) + fine wiggle (static)
_col[0] = 1
wob_vec, wob_w = torus(u, v, WOBBLE_RADIUS,
                       (op("MULTIPLY", t_cos, WOBBLE_DRIFT), op("MULTIPLY", t_sin, WOBBLE_DRIFT), None, None))
_col[0] = 2
wobble = node("ShaderNodeTexNoise", label="Wobble", noise_dimensions="4D")
wobble.inputs["Scale"].default_value = 1.2
wobble.inputs["Detail"].default_value = 1.0
wobble.inputs["Roughness"].default_value = 0.5
links.new(wob_vec, wobble.inputs["Vector"])
links.new(wob_w, wobble.inputs["W"])
_col[0] = 1
wig_vec, wig_w = torus(u, v, WIGGLE_RADIUS)
_col[0] = 2
wiggle = node("ShaderNodeTexNoise", label="Wiggle", noise_dimensions="4D")
wiggle.inputs["Scale"].default_value = 1.5
wiggle.inputs["Detail"].default_value = 0.0
links.new(wig_vec, wiggle.inputs["Vector"])
links.new(wig_w, wiggle.inputs["W"])

_col[0] = 3
wob_rgb = node("ShaderNodeSeparateColor")
links.new(wobble.outputs["Color"], wob_rgb.inputs[0])
wig_rgb = node("ShaderNodeSeparateColor")
links.new(wiggle.outputs["Color"], wig_rgb.inputs[0])
du = op("ADD", op("MULTIPLY", op("SUBTRACT", wob_rgb.outputs[0], 0.5), WOBBLE_AMOUNT * 2),
        op("MULTIPLY", op("SUBTRACT", wig_rgb.outputs[0], 0.5), WIGGLE_AMOUNT * 2))
dv = op("ADD", op("MULTIPLY", op("SUBTRACT", wob_rgb.outputs[1], 0.5), WOBBLE_AMOUNT * 2),
        op("MULTIPLY", op("SUBTRACT", wig_rgb.outputs[1], 0.5), WIGGLE_AMOUNT * 2))
u2, v2 = op("ADD", u, du), op("ADD", v, dv)

# column 4-5: periodic Voronoi cells (OSL script node), sites orbiting over the loop
_col[0] = 4
cell_coord = node("ShaderNodeCombineXYZ")
feed(cell_coord.inputs[0], u2)
feed(cell_coord.inputs[1], v2)
_col[0] = 5
osl_text = bpy.data.texts.new("cartoon_cells.osl")
with open(OSL_PATH, encoding="utf-8") as f:
    osl_text.write(f.read())
cells = node("ShaderNodeScript", label="Cartoon cells (OSL)")
cells.mode = "INTERNAL"
cells.script = osl_text
# headless there is no node editor for the "Script Node Update" operator: call Cycles' compiler directly
import cycles.osl  # noqa: E402
cycles.osl.update_script_node(cells, lambda kind, msg: print("OSL", kind, msg))
assert "EdgeDist" in cells.outputs, "OSL script did not compile"
links.new(cell_coord.outputs[0], cells.inputs["Coord"])
cells.inputs["Cells"].default_value = CELLS
cells.inputs["Jitter"].default_value = JITTER
cells.inputs["Orbit"].default_value = ORBIT
links.new(time.outputs[0], cells.inputs["Time"])

# column 6-7: shading
_col[0] = 6
line = node("ShaderNodeMapRange", label="Line mask", interpolation_type="SMOOTHSTEP")
links.new(cells.outputs["EdgeDist"], line.inputs["Value"])
line.inputs["From Min"].default_value = LINE_WIDTH
line.inputs["From Max"].default_value = LINE_WIDTH + LINE_SOFT
line.inputs["To Min"].default_value = 1.0
line.inputs["To Max"].default_value = 0.0
glow = node("ShaderNodeMapRange", label="Glow mask", interpolation_type="SMOOTHSTEP")
links.new(cells.outputs["EdgeDist"], glow.inputs["Value"])
glow.inputs["From Min"].default_value = 0.0
glow.inputs["From Max"].default_value = GLOW_WIDTH
glow.inputs["To Min"].default_value = GLOW_AMOUNT
glow.inputs["To Max"].default_value = 0.0
shade = op("MULTIPLY", cells.outputs["CellRand"], CELL_SHADE)

_col[0] = 7
col = mix(shade, rgb("cell"), rgb("cell_dark"))
col = mix(glow.outputs[0], col, rgb("glow"))
col = mix(line.outputs[0], col, rgb("line"))

_col[0] = 8
emit = node("ShaderNodeEmission")
links.new(col, emit.inputs["Color"])
emit.inputs["Strength"].default_value = 1.0
out = node("ShaderNodeOutputMaterial")
links.new(emit.outputs[0], out.inputs["Surface"])

# ---------------------------------------------------------------- render
os.makedirs(OUT_DIR, exist_ok=True)
if MODE == "preview":
    scene.frame_set(0)
    scene.render.filepath = os.path.join(OUT_DIR, "preview.png")
    bpy.ops.render.render(write_still=True)
else:
    for f in range(FRAMES):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(OUT_DIR, f"water_{f:02d}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered frame", f)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(OUT_DIR), "cartoon_water.blend"))
print("done", MODE)
