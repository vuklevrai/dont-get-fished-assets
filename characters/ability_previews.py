"""Animated previews of the two abilities with their effects, matching what AbilityFx does in game:
  previews/timestop.gif  the prehistoric fish stops time: windup, sphere burst with the negative flash, the
                         world turns grey-violet, two red piranhas freeze into statues (and bubbles stop in
                         mid-air), clock, menacing "go" glyphs, anger mark, the raging fish hits a frozen piranha
                         (the impact waits), then time resumes and the hit goes off.
  previews/croc.gif      the crocodile opens its jaws (swirling slow zone, slowed piranha with a snail), bites
                         (CHOMP), death roll.
Characters come from the .blend files (appended), posed every frame from the same clip functions as the game.

    python3 ability_previews.py [timestop] [croc]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import crocodile  # noqa: E402
import hyneria  # noqa: E402
import piranha  # noqa: E402
import render  # noqa: E402
from blendlib import bl_quat, bl_vec  # noqa: E402
from voxlib import T, qmul, qnorm, ramp, srgb_to_linear, hexrgb  # noqa: E402

FX = os.path.join(os.path.dirname(HERE), "fx")
OUT = os.path.join(HERE, "previews")
W, H = 640, 360
FPS = 30
STEP = 2  # render every other frame: 15 fps GIFs
ONLY = [int(x) for x in os.environ.get("PREVIEW_FRAMES", "").split(",") if x]  # test a few frames


def tex(name):
    return Image.open(os.path.join(FX, name)).convert("RGBA")


def font(size):
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


# --------------------------------------------------------------------------------------------- scene

def new_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.resolution_x, scene.render.resolution_y = W, H
    world = bpy.data.worlds.new("World")
    scene.world = world
    render.set_background(scene, top=(0.5, 0.72, 0.88), bottom=(0.1, 0.3, 0.48))
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    for name, energy, loc, size in (("Key", 1100, (2, -6, 8), 5), ("Fill", 350, (-7, -4, 2), 7), ("Rim", 500, (-2, 7, 5), 4)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        render.aim(lo, (0, 0, 0))
    return scene, cam


class Instance:
    """One appended copy of a character, posed from Python."""

    def __init__(self, key, ch):
        self.key = key
        self.ch = ch
        path = os.path.join(HERE, key, key + ".blend")
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = list(src.objects)
        scene = bpy.context.scene
        new = [o for o in dst.objects if o is not None]
        for o in list(new):
            if o.type in ("CAMERA", "LIGHT"):
                bpy.data.objects.remove(o)
                new.remove(o)
        for o in new:
            scene.collection.objects.link(o)
            o.animation_data_clear()
        self.top = next(o for o in new if o.parent is None and o.name.split(".")[0] == key)
        self.objs = {}
        self.meshes = []
        for o in self.top.children_recursive:
            base = o.name.split(".")[0]
            if o.type == "EMPTY" and base in ch.nodes:
                self.objs[base] = o
            elif o.type == "MESH":
                self.meshes.append(o)
        self.top.rotation_mode = "XYZ"
        self.statue = False

    def place(self, pos, heading=0.0, roll=0.0, pitch=0.0):
        self.top.location = pos
        self.top.rotation_euler = (roll, pitch, heading)

    def pose(self, deltas):
        for n in self.ch.order:
            local = self.ch.rest_local(n)
            d = deltas.get(n)
            if d is not None:
                dp, dq = d
                local = T(local.p + np.asarray(dp, float), qmul(local.q, dq))
            o = self.objs[n]
            o.rotation_mode = "QUATERNION"
            o.location = bl_vec(local.p)
            o.rotation_quaternion = bl_quat(local.q)

    def world(self, node):
        bpy.context.view_layer.update()
        return self.objs[node].matrix_world.translation.copy()

    def set_statue(self, on):
        if on == self.statue:
            return
        self.statue = on
        for o in self.meshes:
            slot = o.material_slots[0]
            if on:
                slot.link = "OBJECT"
                slot.material = statue_material(o.data.materials[0])
            else:
                slot.link = "DATA"


_statues = {}


def statue_material(mat):
    """Grey-violet stone version of a colour (what the time-stop Highlight does in game)."""
    if mat.name in _statues:
        return _statues[mat.name]
    c = mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
    lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    g = 0.12 + 0.75 * lum ** 0.8
    tint = (0.78, 0.74, 0.92)
    s = bpy.data.materials.new(mat.name + "_statue")
    b = s.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (g * tint[0], g * tint[1], g * tint[2], 1)
    b.inputs["Roughness"].default_value = 0.85
    _statues[mat.name] = s
    return s


def blend(a, b, w):
    """Mix two delta dicts (node -> (dp, dq))."""
    out = {}
    ident = ((0, 0, 0), (0, 0, 0, 1))
    for n in set(a) | set(b):
        pa, qa = a.get(n, ident)
        pb, qb = b.get(n, ident)
        qa, qb = np.asarray(qa, float), np.asarray(qb, float)
        if np.dot(qa, qb) < 0:
            qb = -qb
        out[n] = (tuple(np.asarray(pa, float) * (1 - w) + np.asarray(pb, float) * w), qnorm(qa * (1 - w) + qb * w))
    return out


def project(scene, cam, co):
    v = world_to_camera_view(scene, cam, Vector(co))
    return v.x * W, (1 - v.y) * H, v.z


def px_per_unit(scene, cam, co):
    a = project(scene, cam, co)
    b = project(scene, cam, Vector(co) + cam.matrix_world.to_quaternion() @ Vector((1, 0, 0)))
    return math.hypot(b[0] - a[0], b[1] - a[1])


def render_frame(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return Image.open(path).convert("RGBA")


# --------------------------------------------------------------------------------------------- 2D helpers

def paste(img, sprite, cx, cy, size, rot=0.0, alpha=1.0):
    if size < 2 or alpha <= 0:
        return
    w = int(size)
    h = int(size * sprite.size[1] / sprite.size[0])
    s = sprite.resize((max(1, w), max(1, h)), Image.LANCZOS)
    if rot:
        s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = s.split()[3].point(lambda v: int(v * alpha))
        s.putalpha(a)
    img.alpha_composite(s, (int(cx - s.size[0] / 2), int(cy - s.size[1] / 2)))


def invert_inside(arr, cx, cy, r):
    yy, xx = np.mgrid[0:H, 0:W]
    m = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    arr[m, :3] = 255 - arr[m, :3]
    return m


def grade(arr, amount, mask=None):
    """Roblox-style grade of the stopped world: saturation -0.72, contrast +0.22, violet tint."""
    if amount <= 0:
        return arr
    rgb = arr[..., :3].astype(np.float32) / 255
    lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
    g = rgb + (lum - rgb) * 0.72
    g = (g - 0.5) * 1.22 + 0.5 - 0.03
    g = g * np.array([212, 196, 255], np.float32) / 255
    g = np.clip(g, 0, 1)
    out = rgb + (g - rgb) * amount
    res = (out * 255).astype(np.uint8)
    if mask is None:
        arr[..., :3] = res
    else:
        arr[mask, :3] = res[mask]
    return arr


def ring(img, cx, cy, r, colour, width, glow=True):
    d = ImageDraw.Draw(img)
    if glow:
        for k, a in ((width * 3, 60), (width * 2, 110)):
            d.ellipse([cx - r - k / 2, cy - r - k / 2, cx + r + k / 2, cy + r + k / 2], outline=colour[:3] + (a,), width=int(k))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=int(width))


def text(img, s, cx, cy, size, fill, stroke, rot=0.0, scale=1.0):
    if scale <= 0.05:
        return
    f = font(max(8, int(size * scale)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bbox = d.textbbox((0, 0), s, font=f, stroke_width=max(2, int(size * scale / 9)))
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - tw / 2, cy - th / 2), s, font=f, fill=fill, stroke_width=max(2, int(size * scale / 9)), stroke_fill=stroke)
    if rot:
        layer = layer.rotate(rot, center=(cx, cy), resample=Image.BICUBIC)
    img.alpha_composite(layer)


def popscale(t, t0, dur=0.18, peak=1.3):
    """0 -> peak -> 1 bounce like AbilityFx's pop()."""
    if t < t0:
        return 0.0
    k = (t - t0) / dur
    if k >= 1:
        return 1.0
    if k < 0.6:
        return peak * math.sin(k / 0.6 * math.pi / 2)
    return peak + (1 - peak) * (k - 0.6) / 0.4


def save_gif(frames, path, fps=15):
    ims = [f.convert("RGB").quantize(colors=220, method=Image.MEDIANCUT, dither=Image.NONE) for f in frames]
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=int(1000 / fps), loop=0, optimize=True)


# --------------------------------------------------------------------------------------------- time stop

def timestop():
    scene, cam = new_scene()
    hy_ch, pi_ch = hyneria.build(), piranha.build()
    hy = Instance("hyneria", hy_ch)
    pa = Instance("piranha", pi_ch)
    pb = Instance("piranha", pi_ch)
    cam.data.lens = 34
    cam.location = (0.6, -14.5, 2.4)
    render.aim(cam, (0.6, 0, 0.2))

    clock_tex, hand_tex = tex("timestop_clock.png"), tex("timestop_hand.png")
    go_tex, vein_tex, star_tex = tex("menacing_go.png"), tex("anger_vein.png"), tex("impact_star.png")

    T_WIND, T_BURST, DUR = 0.6, 1.1, 3.0
    T_RESUME = T_BURST + DUR
    END = 5.2
    rng = np.random.default_rng(7)
    bubbles = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(3, 9), rng.uniform(25, 60)) for _ in range(26)]
    motes = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.0, 0.5)) for _ in range(70)]
    hit = None
    frames = []
    tmp = os.path.join(OUT, "frames_timestop")
    os.makedirs(tmp, exist_ok=True)

    def frozen_time(t):
        """Time as the frozen things see it: it stops at the burst and goes on after the resume."""
        if t < T_BURST:
            return t
        if t < T_RESUME:
            return T_BURST
        return t - DUR

    for f in range(0, int(END * FPS) + 1, STEP):
        if ONLY and f not in ONLY and f > max(ONLY):
            break
        t = f / FPS
        # ---- prehistoric fish
        hx = -3.2
        if t < T_WIND:
            d = hy_ch.clips["repos"].fn(t)
        elif t < T_WIND + 1.6:
            d = hy_ch.clips["arret_du_temps"].fn(t - T_WIND)
        elif t < T_RESUME:
            d = hy_ch.clips["rage"].fn((t - T_WIND - 1.6) % 0.5)
            hx += 6.0 * ramp(t, T_WIND + 1.6, T_RESUME) ** 1.1
        else:
            d = hy_ch.clips["nage"].fn((t - T_RESUME) % 1.0)
            hx += 6.0 + 0.9 * (t - T_RESUME)
        hy.pose(d)
        hy.place((hx, 0.4, 0.0), heading=0.0)
        # ---- piranhas: swim, freeze, resume (b takes the delayed hit)
        ft = frozen_time(t)
        pa.pose(pi_ch.clips["nage"].fn(ft % 0.8))
        pa.place((4.6 - 0.9 * ft, 3.2, 1.1), heading=math.pi)
        pa.set_statue(T_BURST <= t < T_RESUME)
        kb = max(0.0, t - T_RESUME) if hit else 0.0
        knock = (1 - math.exp(-4 * kb)) if kb > 0 else 0.0
        pb.pose(pi_ch.clips["nage"].fn((ft * 1.1) % 0.8) if kb == 0 or kb > 0.9 else pi_ch.clips["dash"].fn(min(kb, 0.99)))
        pb.place((0.8 + 0.7 * ft + 3.0 * knock, -1.3 - 2.6 * knock, -0.3 + 0.9 * knock),
                 heading=0.35 + 6.0 * knock, roll=2.5 * knock)
        pb.set_statue(T_BURST <= t < T_RESUME)
        # the raging fish brushes past the frozen piranha: the hit is stored
        if hit is None and T_BURST < t < T_RESUME:
            a, b = hy.world("tete"), pb.world("corps_avant")
            if (a - b).length < 2.3:
                hit = (t, (a + b) / 2)

        if ONLY and f not in ONLY:
            continue
        img = render_frame(scene, os.path.join(tmp, "f%03d.png" % f))
        arr = np.array(img)
        ppu = px_per_unit(scene, cam, hy.world("corps_avant"))
        cx, cy, _ = project(scene, cam, hy.world("corps_avant"))

        # bubbles rising in the background stop in mid-air too
        bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dbl = ImageDraw.Draw(bl)
        for bx, by, br, bs in bubbles:
            y = (by - bs * ft) % (H + 40) - 20
            x = bx + 6 * math.sin(ft * 2 + bx)
            dbl.ellipse([x - br, y - br, x + br, y + br], outline=(235, 250, 255, 150), width=2)
            dbl.ellipse([x - br * 0.45, y - br * 0.6, x - br * 0.1, y - br * 0.25], fill=(255, 255, 255, 130))
        base = Image.fromarray(arr)
        base.alpha_composite(bl)
        arr = np.array(base)

        # ---- the sphere and the grade
        R_full = math.hypot(W, H)
        if T_BURST <= t < T_BURST + 0.35:
            k = (t - T_BURST) / 0.35
            r = R_full * (1 - (1 - k) ** 4)
            invert_inside(arr, cx, cy, r)
        elif T_BURST + 0.35 <= t < T_BURST + 0.5:
            arr[..., :3] = 255 - arr[..., :3]
        if T_BURST + 0.45 <= t < T_RESUME:
            arr = grade(arr, ramp(t, T_BURST + 0.45, T_BURST + 0.75))
        elif T_RESUME <= t < T_RESUME + 0.3:
            # the stopped zone shrinks back into the fish, colour returns from the edges
            k = (t - T_RESUME) / 0.3
            r = R_full * (1 - k) ** 2
            yy, xx = np.mgrid[0:H, 0:W]
            arr = grade(arr, 1.0, (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r)
        img = Image.fromarray(arr)

        if T_BURST <= t < T_BURST + 0.5:
            k = (t - T_BURST) / 0.35
            r = R_full * (1 - (1 - min(k, 1)) ** 4)
            ring(img, cx, cy, r, (255, 204, 51, 255), 6)
            ring(img, cx, cy, r * 0.82, (170, 90, 255, 220), 4)
        if T_RESUME <= t < T_RESUME + 0.3:
            k = (t - T_RESUME) / 0.3
            ring(img, cx, cy, R_full * (1 - k) ** 2, (200, 140, 255, 230), 5)
        if T_RESUME + 0.3 <= t < T_RESUME + 0.7:
            k = (t - T_RESUME - 0.3) / 0.4
            ring(img, cx, cy, 30 + 160 * k, (255, 255, 255, int(220 * (1 - k))), 4, glow=False)

        # ---- windup motes
        if T_WIND <= t < T_BURST:
            d2 = ImageDraw.Draw(img)
            for a, ph in motes:
                k = ((t - T_WIND) / 0.45 + ph) % 1.0
                rr = (1 - k) * 4.2 * ppu
                x, y = cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.8
                s = 2 + 3 * (1 - k)
                d2.ellipse([x - s, y - s, x + s, y + s], fill=(205, 150, 255, 230))

        # ---- the stopper's props
        if T_BURST <= t < T_RESUME + 0.25:
            fade = 1 - ramp(t, T_RESUME, T_RESUME + 0.25)
            head = hy.world("tete")
            hx2, hy2, _ = project(scene, cam, head + Vector((0, 0, 2.0)))
            sc = popscale(t, T_BURST, 0.25, 1.2)
            paste(img, clock_tex, hx2, hy2, 1.9 * ppu * sc, alpha=fade)
            ticks = int(t - T_BURST)
            paste(img, hand_tex, hx2, hy2, 1.9 * ppu * sc, rot=-30 * ticks, alpha=fade)
            body = hy.world("corps_avant")
            for n in range(5):
                if t < T_BURST + 0.12 * (n + 1):
                    continue
                a = n / 5 * 2 * math.pi + 0.6
                p = body + Vector((math.cos(a) * 2.6, 0, 0.6 + (n % 2) * 1.1 + 0.15 * math.sin(t * 2.4 + n * 1.7)))
                gx, gy, _ = project(scene, cam, p)
                s = popscale(t, T_BURST + 0.12 * (n + 1), 0.22, 1.35)
                paste(img, go_tex, gx, gy, 0.95 * ppu * s, rot=(10 if n % 2 else -12) + 2.5 * math.sin(t * 17 + n),
                      alpha=fade)
            vx, vy, _ = project(scene, cam, head + Vector((0.3, 0, 1.0)))
            pulse = 1 + 0.18 * max(0.0, math.sin(t * 9))
            paste(img, vein_tex, vx, vy, 0.75 * ppu * popscale(t, T_BURST + 0.1, 0.2, 1.4) * pulse, alpha=fade)
        if T_BURST + 0.05 <= t < T_BURST + 1.2:
            s = popscale(t, T_BURST + 0.05, 0.3, 1.3) * (1 - ramp(t, T_BURST + 0.9, T_BURST + 1.2))
            text(img, "ZA WARUDO!", W / 2, H * 0.17, 46, (255, 204, 51, 255), (70, 10, 110, 255), rot=4, scale=s)
        if hit and hit[0] <= t < T_RESUME + 0.3:
            hx3, hy3, _ = project(scene, cam, hit[1])
            if t < T_RESUME:
                paste(img, star_tex, hx3, hy3, 1.4 * ppu * popscale(t, hit[0], 0.16, 1.3), rot=12)
            else:
                k = (t - T_RESUME) / 0.3
                paste(img, star_tex, hx3, hy3, 1.4 * ppu * (1 + 1.2 * k), rot=12, alpha=1 - k)
        frames.append(img)
        print("timestop", f, flush=True)
        if ONLY:
            img.convert("RGB").save(os.path.join(tmp, "test_%03d.png" % f))
    if ONLY:
        return
    save_gif(frames, os.path.join(OUT, "timestop.gif"))
    frames[int(1.6 * FPS / STEP)].convert("RGB").save(os.path.join(OUT, "timestop_still.png"))
    frames[int((T_RESUME - 0.4) * FPS / STEP)].convert("RGB").save(os.path.join(OUT, "timestop_still2.png"))


# --------------------------------------------------------------------------------------------- crocodile

def croc():
    scene, cam = new_scene()
    cr_ch, pi_ch = crocodile.build(), piranha.build()
    cr = Instance("crocodile", cr_ch)
    pa = Instance("piranha", pi_ch)
    pb = Instance("piranha", pi_ch)
    cam.data.lens = 32
    cam.location = (0.2, -12.0, 3.4)
    render.aim(cam, (0.2, 0, 0.1))

    # the slow zone, in 3D: a flat swirl ring and a faint green shell (what AbilityFx builds)
    zone_r = 5.5  # 11 studs
    ring_mat = bpy.data.materials.new("SlowRing")
    nt = ring_mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    texn = nt.nodes.new("ShaderNodeTexImage")
    texn.image = bpy.data.images.load(os.path.join(FX, "slow_ring.png"))
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.6
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    fadev = nt.nodes.new("ShaderNodeMath")
    fadev.operation = "MULTIPLY"
    fadev.inputs[1].default_value = 0.0
    nt.links.new(texn.outputs["Color"], emit.inputs["Color"])
    nt.links.new(texn.outputs["Alpha"], fadev.inputs[0])
    nt.links.new(fadev.outputs[0], mix.inputs["Fac"])
    nt.links.new(transp.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=2 * zone_r)
    disc = bpy.context.active_object
    disc.data.materials.append(ring_mat)
    shell_mat = bpy.data.materials.new("SlowShell")
    nt2 = shell_mat.node_tree
    nt2.nodes.clear()
    o2 = nt2.nodes.new("ShaderNodeOutputMaterial")
    fres = nt2.nodes.new("ShaderNodeLayerWeight")
    fres.inputs["Blend"].default_value = 0.25
    em2 = nt2.nodes.new("ShaderNodeEmission")
    em2.inputs["Color"].default_value = (0.25, 0.85, 0.55, 1)
    em2.inputs["Strength"].default_value = 1.2
    tr2 = nt2.nodes.new("ShaderNodeBsdfTransparent")
    mx2 = nt2.nodes.new("ShaderNodeMixShader")
    mul2 = nt2.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 0.0
    nt2.links.new(fres.outputs["Facing"], mul2.inputs[0])
    nt2.links.new(mul2.outputs[0], mx2.inputs["Fac"])
    nt2.links.new(tr2.outputs[0], mx2.inputs[1])
    nt2.links.new(em2.outputs[0], mx2.inputs[2])
    nt2.links.new(mx2.outputs[0], o2.inputs["Surface"])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=zone_r, segments=48, ring_count=24)
    shell = bpy.context.active_object
    shell.data.materials.append(shell_mat)
    for p in shell.data.polygons:
        p.use_smooth = True

    snail, jaw_tex, star_tex = tex("slow_icon.png"), tex("bite_jaw.png"), tex("impact_star.png")
    T_ARM, T_BITE, END = 0.4, 1.55, 4.2
    frames = []
    tmp = os.path.join(OUT, "frames_croc")
    os.makedirs(tmp, exist_ok=True)
    bite_pos = None
    for f in range(0, int(END * FPS) + 1, STEP):
        if ONLY and f not in ONLY and f > max(ONLY):
            break
        t = f / FPS
        armed = T_ARM <= t < T_BITE
        cx = -3.4
        if t < T_ARM:
            d = cr_ch.clips["repos"].fn(t)
        elif t < T_BITE:
            k = ramp(t, T_ARM, T_ARM + 0.12)
            base = blend(cr_ch.clips["repos"].fn(t), cr_ch.clips["nage"].fn((t - T_ARM) % 1.2), k)
            ov = cr_ch.clips["gueule_ouverte"].fn((t - T_ARM) % 1.0)
            d = dict(base)
            for j in ("tete", "machoire"):
                d[j] = blend({j: base.get(j, ((0, 0, 0), (0, 0, 0, 1)))}, {j: ov[j]}, k)[j]
            cx += 2.2 * (t - T_ARM)
        else:
            kc = t - T_BITE
            d = cr_ch.clips["croc"].fn(min(kc, 1.5)) if kc < 1.5 else cr_ch.clips["repos"].fn(kc - 1.5)
            cx += 2.2 * (T_BITE - T_ARM) + 0.6 * min(kc, 0.4)
        cr.pose(d)
        cr.place((cx, 0.0, 0.0))
        # zone follows the croc while the jaws are open
        on = ramp(t, T_ARM, T_ARM + 0.25) * (1 - ramp(t, T_BITE, T_BITE + 0.3))
        mid = cr.world("corps_avant")
        disc.location = (mid.x, mid.y, mid.z - 0.05)
        disc.rotation_euler = (0, 0, 2.2 * t)
        shell.location = mid
        ring_mat.node_tree.nodes["Math"].inputs[1].default_value = 0.85 * on
        shell_mat.node_tree.nodes["Math"].inputs[1].default_value = 0.35 * on
        disc.hide_render = shell.hide_render = on <= 0.01
        # piranha a: swims at the croc, gets slowed in the zone, bitten, knocked away tumbling
        slow = 0.5 if (armed and t > T_ARM + 0.3) else 1.0
        if t < T_BITE:
            ax = 3.6 - 1.4 * t if t < T_ARM + 0.3 else 3.6 - 1.4 * (T_ARM + 0.3) - 0.7 * (t - T_ARM - 0.3)
            pa_pose = pi_ch.clips["nage"].fn((t * (1.0 if slow == 1 else 0.6)) % 0.8)
            pa.place((ax, 0.35, 0.25), heading=math.pi)
            ka = 0.0
        else:
            ka = t - T_BITE - 0.25
            ax0 = 3.6 - 1.4 * (T_ARM + 0.3) - 0.7 * (T_BITE - T_ARM - 0.3)
            if ka < 0:
                pa_pose = pi_ch.clips["nage"].fn((t * 0.6) % 0.8)
                pa.place((ax0, 0.35, 0.25), heading=math.pi)
            else:
                k = 1 - math.exp(-3 * ka)
                pa_pose = pi_ch.clips["repos"].fn(ka % 2.4)
                pa.place((ax0 + 3.4 * k, 0.35 + 1.0 * k, 0.25 + 1.4 * k), heading=math.pi + 5.5 * k, roll=4.0 * k)
        pa.pose(pa_pose)
        pb.pose(pi_ch.clips["nage"].fn((t * 0.9) % 0.8))
        pb.place((5.5 - 0.8 * t, 3.6, 1.4), heading=math.pi - 0.3)

        if ONLY and f not in ONLY:
            continue
        img = render_frame(scene, os.path.join(tmp, "f%03d.png" % f))
        ppu = px_per_unit(scene, cam, cr.world("tete"))
        # snail over the slowed piranha
        if armed and t > T_ARM + 0.3 or (T_BITE <= t < T_BITE + 0.25):
            sx, sy, _ = project(scene, cam, pa.world("corps_avant") + Vector((0, 0, 1.5)))
            paste(img, snail, sx, sy + 4 * math.sin(t * 5), 1.2 * ppu * popscale(t, T_ARM + 0.3, 0.2, 1.3),
                  rot=6 * math.sin(t * 3))
        # CHOMP at the snout when the jaws shut
        snap = T_BITE + 0.22
        if snap - 0.1 <= t < snap + 0.6:
            if bite_pos is None:
                bite_pos = cr.world("machoire") + Vector((0.9, 0, 0.1))
            bx, by, _ = project(scene, cam, bite_pos)
            size = 3.4 * ppu
            k = ramp(t, snap - 0.1, snap)
            fade = 1 - ramp(t, snap + 0.35, snap + 0.6)
            if t >= snap:
                paste(img, star_tex, bx, by, size * 0.9 * popscale(t, snap, 0.18, 1.35), alpha=fade)
            jaw = jaw_tex.resize((int(size), int(size * jaw_tex.size[1] / jaw_tex.size[0])), Image.LANCZOS)
            gap = (1 - k) * size * 0.45
            if fade > 0:
                up = jaw.copy()
                lo = jaw.rotate(180)
                if fade < 1:
                    for im_ in (up, lo):
                        im_.putalpha(im_.split()[3].point(lambda v: int(v * fade)))
                img.alpha_composite(up, (int(bx - up.size[0] / 2), int(by - up.size[1] - gap + size * 0.08)))
                img.alpha_composite(lo, (int(bx - lo.size[0] / 2), int(by + gap - size * 0.08)))
            if t >= snap:
                text(img, "CHOMP!", bx, by - size * 0.55, 34, (255, 255, 255, int(255 * fade)), (120, 20, 30, int(255 * fade)),
                     rot=8, scale=popscale(t, snap, 0.2, 1.4))
        # the bite shakes the camera
        if snap <= t < snap + 0.35:
            amp = 6 * (1 - (t - snap) / 0.35)
            img = Image.fromarray(np.roll(np.array(img), (int(amp * math.sin(t * 90)), int(amp * math.cos(t * 70))), axis=(0, 1)))
        frames.append(img)
        print("croc", f, flush=True)
        if ONLY:
            img.convert("RGB").save(os.path.join(tmp, "test_%03d.png" % f))
    if ONLY:
        return
    save_gif(frames, os.path.join(OUT, "croc.gif"))
    frames[int((T_ARM + 0.9) * FPS / STEP)].convert("RGB").save(os.path.join(OUT, "croc_still.png"))
    frames[int((T_BITE + 0.26) * FPS / STEP)].convert("RGB").save(os.path.join(OUT, "croc_still2.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = [a for a in sys.argv[1:] if a in ("timestop", "croc")] or ["timestop", "croc"]
    for w in which:
        {"timestop": timestop, "croc": croc}[w]()
