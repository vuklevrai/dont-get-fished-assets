"""Preview renders of the characters (Cycles, CPU): stills, silhouettes and animation frames for GIFs.

    python3 render.py <key> stills|anim <clip> [step]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))


def open_char(key):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, key, key + ".blend"))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    return scene


def set_background(scene, top=(0.62, 0.78, 0.92), bottom=(0.16, 0.36, 0.55), strength=1.0):
    """Soft vertical gradient seen by the camera only (lighting stays neutral)."""
    world = scene.world
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    mix = nt.nodes.new("ShaderNodeMixShader")
    light_path = nt.nodes.new("ShaderNodeLightPath")
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs["Color"].default_value = (0.8, 0.86, 0.92, 1)
    bg_light.inputs["Strength"].default_value = 0.55
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    geo = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*top, 1)
    mapr = nt.nodes.new("ShaderNodeMapRange")
    mapr.inputs["From Min"].default_value = -1
    mapr.inputs["From Max"].default_value = 1
    nt.links.new(geo.outputs["Window"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg_cam.inputs["Color"])
    bg_cam.inputs["Strength"].default_value = strength
    nt.links.new(light_path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_light.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


def aim(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(scene, az, el, dist, target=(0.1, 0, 0), lens=50, ortho=None):
    """az: 0 = looking at the fish's right side (+Z model = -Y Blender), 90 = from the front (+X)."""
    cam = scene.camera
    tx, ty, tz = target[0], -target[2], target[1]
    a, e = math.radians(az), math.radians(el)
    cam.location = (tx + dist * math.sin(a) * math.cos(e), ty - dist * math.cos(a) * math.cos(e), tz + dist * math.sin(e))
    aim(cam, (tx, ty, tz))
    cam.data.lens = lens
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
    # the key light follows the camera so every view is lit from the front-top
    key = bpy.data.objects.get("Key")
    if key:
        key.location = (cam.location.x * 0.6 + 2.5, cam.location.y * 0.9, cam.location.z + 4.5)
        aim(key, (tx, ty, tz))


def frame_of(scene, clip, f):
    m = scene.timeline_markers.get(clip)
    return (m.frame if m else 0) + f


def render(scene, path, w=880, h=560):
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def stills(key, outdir, views=None):
    scene = open_char(key)
    set_background(scene)
    scene.frame_set(frame_of(scene, "repos", 0))
    views = views or [("profil", 0, 4, 8.5, 50), ("trois_quarts", 38, 16, 8.0, 50), ("face", 82, 8, 7.0, 50),
                      ("dessus", 0, 80, 8.5, 50), ("gauche", 180, 10, 8.5, 50)]
    for name, az, el, dist, lens in views:
        camera(scene, az, el, dist, lens=lens)
        render(scene, os.path.join(outdir, "%s_%s.png" % (key, name)))


def silhouette(key, outdir):
    scene = open_char(key)
    scene.render.film_transparent = True
    scene.frame_set(frame_of(scene, "repos", 0))
    camera(scene, 0, 0, 9, ortho=4.6)
    render(scene, os.path.join(outdir, "%s_silhouette_raw.png" % key), 880, 480)


def anim(key, clip, outdir, step=2, views=(("trois_quarts", 32, 14, 8.0),), size=(640, 420), frames=None):
    scene = open_char(key)
    set_background(scene)
    scene.cycles.samples = 14
    m = scene.timeline_markers.get(clip)
    markers = sorted(scene.timeline_markers, key=lambda mk: mk.frame)
    nxt = [mk.frame for mk in markers if mk.frame > m.frame]
    end = (nxt[0] - 10) if nxt else scene.frame_end
    count = end - m.frame + 1
    for vname, az, el, dist in views:
        camera(scene, az, el, dist)
        for f in (frames or range(0, count, step)):
            scene.frame_set(m.frame + f)
            render(scene, os.path.join(outdir, "%s_%s_%s_%03d.png" % (key, clip, vname, f)), *size)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    key, mode = args[0], args[1]
    out = args[2] if len(args) > 2 else os.path.join(HERE, key, "previews")
    os.makedirs(out, exist_ok=True)
    if mode == "stills":
        stills(key, out)
    elif mode == "silhouette":
        silhouette(key, out)
    elif mode == "anim":
        anim(key, args[3], out, step=int(args[4]) if len(args) > 4 else 2)
