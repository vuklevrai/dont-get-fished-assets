"""Builds the voxel characters: Blender scene (.blend), GLB with animations, and the game data
(luau/FishData/<Model>.luau, luau/FishAnims/<Model>.luau), with consistency checks.

    python3 build_characters.py [piranha] [hyneria] [crocodile]     (bpy 5.2 as a Python module)
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import blendlib  # noqa: E402
import glbcheck  # noqa: E402
import voxlib  # noqa: E402

ROOT = os.path.dirname(HERE)
LUAU = os.path.join(ROOT, "luau")
ALL = ["piranha", "hyneria", "crocodile"]


def build_one(key):
    mod = importlib.import_module(key)
    ch = mod.build()
    out = os.path.join(HERE, key)
    os.makedirs(out, exist_ok=True)
    report = {"key": key, "model": ch.model}

    report["loop_errors"] = ch.check_loops()
    os.makedirs(os.path.join(LUAU, "FishData"), exist_ok=True)
    os.makedirs(os.path.join(LUAU, "FishAnims"), exist_ok=True)
    note = "%s (Don't Get Fished), voxel model built in Blender by characters/%s.py." % (ch.model, key)
    nbox, npieces = voxlib.write_fishdata(ch, os.path.join(LUAU, "FishData", ch.model + ".luau"), note)
    voxlib.write_fishanims(ch, os.path.join(LUAU, "FishAnims", ch.model + ".luau"), note)
    report["game_parts"] = nbox
    report["game_pieces"] = npieces
    report["game_joints"] = len(ch.segments())
    report["roblox_fk_error_studs"] = round(voxlib.roblox_fk_check(ch), 6)

    top, objs, stats = blendlib.build(ch)
    report["blender_tris"] = stats["tris"]
    report["blender_meshes"] = stats["meshes"]
    glb = os.path.join(out, key + ".glb")
    blendlib.export_glb(glb)

    # Blender's own evaluation of the NLA tracks against the model
    worst = 0.0
    for c in ch.clips.values():
        for f in range(0, c.frames, 2):
            got = blendlib.evaluated_world(objs, ch, c.name, f)
            want = ch.pose(c, f / voxlib.FPS)
            for n in ch.order:
                worst = max(worst, float(abs(got[n].p - want[n].p).max()))
    report["blender_eval_error"] = round(worst, 6)
    for n in ch.order:
        for tr in objs[n].animation_data.nla_tracks:
            tr.mute = False

    gerr, gsum = glbcheck.compare(ch, glb)
    report["glb_error"] = round(gerr, 6)
    report["glb"] = gsum

    blendlib.lay_out_timeline(ch, stats["strips"])
    blendlib.add_viewing_rig(target=(0.1, 0.0, 0.0), dist=7.5)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, key + ".blend"))
    with open(os.path.join(out, "build_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    names = [a for a in sys.argv[1:] if a in ALL] or ALL
    for k in names:
        build_one(k)
