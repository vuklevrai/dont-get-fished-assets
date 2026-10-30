"""Final previews of every character: stills, silhouette, one GIF per clip and a sheet.
Frames go to characters/<key>/previews/frames (not committed).

    python3 render_all.py [piranha hyneria crocodile]
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import render  # noqa: E402

VIEWS = {
    "piranha": dict(dist=8.5, still=[("profil", 0, 4, 8.5), ("trois_quarts", 38, 16, 8.0), ("face", 70, 10, 7.0),
                                     ("dessus", 20, 70, 8.5)], anim=("trois_quarts", 32, 14, 8.0)),
    "hyneria": dict(dist=10, still=[("profil", 0, 4, 10.0), ("trois_quarts", 38, 18, 9.5), ("face", 70, 12, 8.0),
                                    ("dessus", 20, 70, 10.0)], anim=("trois_quarts", 32, 16, 9.5)),
    "crocodile": dict(dist=10.5, still=[("profil", 0, 6, 10.5), ("trois_quarts", 38, 22, 10.0), ("face", 70, 14, 8.5),
                                        ("dessus", 20, 70, 10.5)], anim=("trois_quarts", 32, 18, 9.5)),
}
LOOPS = {"repos", "nage", "rage", "gueule_ouverte"}
CLIPS = {
    "piranha": ["repos", "nage", "dash"],
    "hyneria": ["repos", "nage", "arret_du_temps", "rage"],
    "crocodile": ["repos", "nage", "gueule_ouverte", "croc"],
}


def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def gif(frames, path, fps=15, label=None):
    ims = []
    for f in frames:
        im = Image.open(f).convert("RGB")
        if label:
            d = ImageDraw.Draw(im)
            d.text((12, 10), label, fill=(255, 255, 255), font=font(18), stroke_width=3, stroke_fill=(20, 30, 50))
        ims.append(im.quantize(colors=200, method=Image.MEDIANCUT, dither=Image.NONE))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=int(1000 / fps), loop=0, optimize=True)


def silhouette(raw, path):
    im = Image.open(raw).convert("RGBA")
    a = im.split()[3].point(lambda v: 255 if v > 40 else 0)
    out = Image.new("RGB", im.size, (255, 255, 255))
    out.paste((0, 0, 0), (0, 0), a)
    out.save(path)
    os.remove(raw)


def sheet(key, out):
    names = [v[0] for v in VIEWS[key]["still"]]
    ims = [Image.open(os.path.join(out, "%s_%s.png" % (key, n))) for n in names]
    w, h = ims[0].size
    w2, h2 = w // 2, h // 2
    s = Image.new("RGB", (w2 * 2, h2 * 2))
    for n, im in enumerate(ims):
        s.paste(im.resize((w2, h2), Image.LANCZOS), ((n % 2) * w2, (n // 2) * h2))
    s.save(os.path.join(out, "%s_planche.png" % key))


def run(key):
    out = os.path.join(HERE, key, "previews")
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    v = VIEWS[key]
    render.stills(key, out, views=[(n, az, el, d, 50) for n, az, el, d in v["still"]])
    sheet(key, out)
    scene = render.open_char(key)
    scene.render.film_transparent = True
    scene.frame_set(render.frame_of(scene, "repos", 0))
    render.camera(scene, 0, 0, 9, ortho={"piranha": 4.9, "hyneria": 5.4, "crocodile": 5.6}[key])
    raw = os.path.join(out, "%s_silhouette_raw.png" % key)
    render.render(scene, raw, 880, 420)
    silhouette(raw, os.path.join(out, "%s_silhouette.png" % key))
    name, az, el, dist = v["anim"]
    for clip in CLIPS[key]:
        for old in glob.glob(os.path.join(frames_dir, "%s_%s_*.png" % (key, clip))):
            os.remove(old)
        render.anim(key, clip, frames_dir, step=2, views=((name, az, el, dist),), size=(480, 316))
        frames = sorted(glob.glob(os.path.join(frames_dir, "%s_%s_%s_*.png" % (key, clip, name))))
        if clip in LOOPS and len(frames) > 2:
            frames = frames[:-1]  # the last frame of a loop is the first one again
        gif(frames, os.path.join(out, "%s_%s.gif" % (key, clip)), label=clip)


if __name__ == "__main__":
    keys = [a for a in sys.argv[1:] if a in VIEWS] or list(VIEWS)
    for k in keys:
        run(k)
        print("done", k, flush=True)
