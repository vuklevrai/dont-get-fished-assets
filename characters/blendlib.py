"""Blender side of the voxel characters: meshes (merged faces + studs), the node rig, one NLA track per clip,
GLB export and a .blend whose timeline plays every clip in a row (markers name them)."""
import math

import bpy
import numpy as np

from voxlib import FPS, G, T, srgb_to_linear, hexrgb

STUD_HALF = 0.028  # stud footprint 0.056, like the reference bonite
STUD_HEIGHT = 0.022


def bl_vec(v):
    """Model space (Y up) -> Blender (Z up), the glTF exporter's inverse conversion."""
    return (float(v[0]), float(-v[2]), float(v[1]))


def bl_quat(q):
    """(x, y, z, w) in model space -> Blender (w, x, y, z)."""
    return (float(q[3]), float(q[0]), float(-q[2]), float(q[1]))


class MeshBuf:
    def __init__(self):
        self.verts = []
        self.faces = []

    def quad(self, pts, normal):
        p = [np.asarray(x, float) for x in pts]
        n = np.cross(p[1] - p[0], p[3] - p[0])
        if np.dot(n, normal) < 0:
            p = p[::-1]
        base = len(self.verts)
        self.verts += [tuple(x) for x in p]
        self.faces.append((base, base + 1, base + 2, base + 3))

    def box(self, lo, hi, skip=None):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        for a in range(3):
            b, c = [x for x in range(3) if x != a]
            for s in (-1, 1):
                if skip is not None and skip == (a, s):
                    continue
                pa = hi[a] if s > 0 else lo[a]
                pts = []
                for ub, uc in ((lo[b], lo[c]), (hi[b], lo[c]), (hi[b], hi[c]), (lo[b], hi[c])):
                    v = [0.0, 0.0, 0.0]
                    v[a], v[b], v[c] = pa, ub, uc
                    pts.append(v)
                nrm = [0.0, 0.0, 0.0]
                nrm[a] = s
                self.quad(pts, nrm)

    @property
    def tris(self):
        return 2 * len(self.faces)


def stud(buf, centre, a, s):
    """A small box on a voxel face (axis a, side s), like a building brick stud."""
    b, c = [x for x in range(3) if x != a]
    lo = np.array(centre, float)
    hi = np.array(centre, float)
    lo[b] -= STUD_HALF
    hi[b] += STUD_HALF
    lo[c] -= STUD_HALF
    hi[c] += STUD_HALF
    if s > 0:
        hi[a] += STUD_HEIGHT
    else:
        lo[a] -= STUD_HEIGHT
    buf.box(lo, hi, skip=(a, -s))


def greedy_rects(cells):
    """2D greedy merge of a set of (u, v) cells into rectangles (u0, v0, u1, v1) inclusive."""
    left = set(cells)
    out = []
    for c in sorted(cells):
        if c not in left:
            continue
        u0, v0 = c
        u1 = u0
        while (u1 + 1, v0) in left:
            u1 += 1
        v1 = v0
        while all((u, v1 + 1) in left for u in range(u0, u1 + 1)):
            v1 += 1
        for u in range(u0, u1 + 1):
            for v in range(v0, v1 + 1):
                left.discard((u, v))
        out.append((u0, v0, u1, v1))
    return out


def volume_meshes(ch, vol, occupied, studs=True):
    """Per material: merged exposed faces of a volume, plus studs in a checkerboard (like the reference bonite)
    on the exposed top and side voxel faces that are not pressed against another segment."""
    rest = ch.rest_world(vol.seg)
    on_grid = np.allclose(rest.q, (0, 0, 0, 1)) and np.allclose(vol.off, 0)
    o = np.round(rest.p / G).astype(int) if on_grid else None
    bufs = {}
    faces = {}
    for c, m in vol.cells.items():
        for a in range(3):
            for s in (-1, 1):
                n = list(c)
                n[a] += s
                n = tuple(n)
                if n in vol.cells:
                    continue
                b, cc = [x for x in range(3) if x != a]
                faces.setdefault((a, s, c[a], m), set()).add((c[b], c[cc]))
                # studs on the top and the flanks only (the skill's rule): none under the belly or on the
                # small front/back steps of the profile
                if not studs or a == 0 or (a == 1 and s < 0):
                    continue
                if on_grid and (n[0] + o[0], n[1] + o[1], n[2] + o[2]) in occupied:
                    continue
                # checkerboard, like the reference bonite: a stud on every other voxel face, all six sides
                g = (c[0] + o[0], c[1] + o[1], c[2] + o[2]) if on_grid else c
                if (g[b] + g[cc]) % 2:
                    continue
                centre = (np.array(c, float) + 0.5) * G + vol.off
                centre[a] += s * 0.5 * G
                stud(bufs.setdefault(m, MeshBuf()), centre, a, s)
    for (a, s, layer, m), cells in faces.items():
        buf = bufs.setdefault(m, MeshBuf())
        b, cc = [x for x in range(3) if x != a]
        pa = (layer + (1 if s > 0 else 0)) * G + vol.off[a]
        nrm = [0.0, 0.0, 0.0]
        nrm[a] = s
        for u0, v0, u1, v1 in greedy_rects(cells):
            pts = []
            for ub, uc in ((u0, v0), (u1 + 1, v0), (u1 + 1, v1 + 1), (u0, v1 + 1)):
                v = [0.0, 0.0, 0.0]
                v[a] = pa
                v[b] = ub * G + vol.off[b]
                v[cc] = uc * G + vol.off[cc]
                pts.append(v)
            buf.quad(pts, nrm)
    return bufs


def global_occupancy(ch):
    occ = set()
    for vol in ch.volumes.values():
        rest = ch.rest_world(vol.seg)
        if not (np.allclose(rest.q, (0, 0, 0, 1)) and np.allclose(vol.off, 0)):
            continue
        o = np.round(rest.p / G).astype(int)
        for c in vol.cells:
            occ.add((c[0] + o[0], c[1] + o[1], c[2] + o[2]))
    return occ


def make_material(name, hexcol, emission=0.0):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    rgb = [srgb_to_linear(c) for c in hexrgb(hexcol)]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.72
    bsdf.inputs["Metallic"].default_value = 0.0
    if emission > 0:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    mat.diffuse_color = (*rgb, 1.0)
    return mat


def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def mesh_object(name, buf, mat, parent, local=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([bl_vec(v) for v in buf.verts], [], buf.faces)
    me.validate()
    me.materials.append(mat)
    try:
        me.shade_flat()
    except AttributeError:
        for p in me.polygons:
            p.use_smooth = False
    me.update()
    ob = bpy.data.objects.new(name, me)
    link(ob, parent)
    if local is not None:
        ob.rotation_mode = "QUATERNION"
        ob.location = bl_vec(local.p)
        ob.rotation_quaternion = bl_quat(local.q)
    return ob


def action_for(obj, clip_name, locs, quats):
    act = bpy.data.actions.new("%s|%s" % (clip_name, obj.name))
    slot = act.slots.new(id_type="OBJECT", name=obj.name)
    layer = act.layers.new("Layer")
    strip = layer.strips.new(type="KEYFRAME")
    cb = strip.channelbag(slot, ensure=True)
    n = len(locs)
    for path, vals, size in (("location", locs, 3), ("rotation_quaternion", quats, 4)):
        for idx in range(size):
            fc = cb.fcurves.new(data_path=path, index=idx)
            fc.keyframe_points.add(n)
            co = np.empty(2 * n)
            co[0::2] = np.arange(n)
            co[1::2] = [v[idx] for v in vals]
            fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value] * n)
            fc.update()
    if obj.animation_data is None:
        obj.animation_data_create()
    track = obj.animation_data.nla_tracks.new()
    track.name = clip_name
    st = track.strips.new(clip_name, 0, act)
    st.action_slot = slot
    return st


def build(ch, studs=True):
    """Fresh scene with the character. Returns (top object, {node: object}, stats)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    mats = {m: make_material(m, h, ch.emissive.get(m, 0.0) if hasattr(ch, "emissive") else 0.0)
            for m, h in ch.colors.items()}

    top = link(bpy.data.objects.new(ch.key, None))
    top.empty_display_size = 0.3
    objs = {}
    for n in ch.order:
        e = bpy.data.objects.new(n, None)
        e.empty_display_size = 0.06
        e.empty_display_type = "SPHERE" if n not in ("rig", "centre") else "PLAIN_AXES"
        parent = ch.nodes[n]["parent"]
        link(e, objs[parent] if parent else top)
        e.rotation_mode = "QUATERNION"
        loc = ch.rest_local(n)
        e.location = bl_vec(loc.p)
        e.rotation_quaternion = bl_quat(loc.q)
        objs[n] = e

    occ = global_occupancy(ch)
    tris = 0
    meshes = 0
    for (seg, vname), vol in ch.volumes.items():
        for m, buf in volume_meshes(ch, vol, occ, studs).items():
            mesh_object("%s_%s" % (vname, m), buf, mats[m], objs[seg])
            tris += buf.tris
            meshes += 1
    for g in ch.groups:
        buf = MeshBuf()
        for lo, hi in g.boxes:
            buf.box(lo, hi)
        local = ch.rest_world(g.seg).inv() * g.frame
        mesh_object(g.name, buf, mats[g.mat], objs[g.seg], local)
        tris += buf.tris
        meshes += 1

    # one NLA track per clip on every node, all starting at frame 0 (what the glTF exporter wants)
    strips = {}
    for c in ch.clips.values():
        frames = [ch_local_pose(ch, c, f / FPS) for f in range(c.frames)]
        for n in ch.order:
            locs = [bl_vec(fr[n].p) for fr in frames]
            quats = [bl_quat(fr[n].q) for fr in frames]
            # keep quaternion signs continuous so linear keys do not flip through the long way
            for i in range(1, len(quats)):
                if np.dot(quats[i], quats[i - 1]) < 0:
                    quats[i] = tuple(-x for x in quats[i])
            strips.setdefault(c.name, []).append(action_for(objs[n], c.name, locs, quats))
    return top, objs, {"tris": tris, "meshes": meshes, "strips": strips}


def ch_local_pose(ch, clip, t):
    deltas = clip.fn(t)
    out = {}
    for n in ch.order:
        local = ch.rest_local(n)
        d = deltas.get(n)
        if d is not None:
            dp, dq = d
            from voxlib import qmul
            local = T(local.p + np.asarray(dp, float), qmul(local.q, dq))
        out[n] = local
    return out


def export_glb(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_animation_mode="NLA_TRACKS",
                              export_yup=True, export_cameras=False, export_lights=False,
                              export_force_sampling=True, export_optimize_animation_size=False,
                              export_optimize_animation_keep_anim_object=True)


def lay_out_timeline(ch, strips, gap=10):
    """For the saved .blend: strips one after the other (with markers) so pressing play shows every clip."""
    scene = bpy.context.scene
    start = 0
    for name, sts in strips.items():
        c = ch.clips[name]
        for st in sts:
            length = st.frame_end - st.frame_start
            # move the end first when shifting right so the strip never gets a negative length
            st.frame_end_ui = start + length
            st.frame_start_ui = start
            st.extrapolation = "NOTHING"
        scene.timeline_markers.new(name, frame=start)
        start += c.frames - 1 + gap
    scene.frame_start = 0
    scene.frame_end = start - gap


def add_viewing_rig(target=(0, 0, 0), dist=7.0):
    """Camera, key/fill lights and a pale world, so the .blend renders as is (F12)."""
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam = link(bpy.data.objects.new("Camera", cam_data))
    tx, ty, tz = bl_vec(target)
    cam.location = (tx + dist * 0.55, ty - dist * 0.8, tz + dist * 0.32)
    direction = np.array([tx, ty, tz]) - np.array(cam.location)
    from mathutils import Vector
    cam.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    for name, energy, loc, size in (("Key", 900, (3, -4, 6), 4), ("Fill", 300, (-5, -2, 2), 6), ("Rim", 500, (-2, 5, 4), 3)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo = link(bpy.data.objects.new(name, ld))
        lo.location = loc
        d = np.array([tx, ty, tz]) - np.array(loc)
        lo.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("World")
    scene.world = world
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.78, 0.84, 0.9, 1.0)
    bg.inputs["Strength"].default_value = 0.6
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 640
    return cam


def evaluated_world(objs, ch, clip_name, frame):
    """Model-space world transforms of the nodes at a frame of one clip (other tracks muted)."""
    for n in ch.order:
        ad = objs[n].animation_data
        for tr in ad.nla_tracks:
            tr.mute = tr.name != clip_name
    scene = bpy.context.scene
    scene.frame_set(frame)
    out = {}
    from mathutils import Matrix
    c_inv = Matrix.Rotation(-math.pi / 2, 4, "X")
    for n in ch.order:
        m = c_inv @ objs[n].matrix_world
        loc, q, _ = m.decompose()
        out[n] = T((loc.x, loc.y, loc.z), (q.x, q.y, q.z, q.w))
    return out
