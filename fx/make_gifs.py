# Animated GIF previews of the flipbooks, over the pond colour and the sky colour (plain Python + Pillow).
#
#   python make_gifs.py <fx_dir>
import os
import sys

from PIL import Image

FX = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
SHEETS = [
    # file, columns, frames per second, loops (True) or plays once then holds (False)
    ("fog_flipbook.png", 4, 12, True),
    ("fog_flipbook_8x8.png", 8, 30, True),
    ("titan_lightning_flipbook.png", 4, 27, False),
    ("zone_wall_flipbook.png", 4, 12, True),
    ("aim_beam_flipbook.png", 4, 10, True),
    ("explosion_flipbook.png", 4, 21, False),
]
BACKGROUNDS = {"water": (78, 214, 251), "sky": (150, 205, 245)}

for name, cols, fps, loop in SHEETS:
    path = os.path.join(FX, name)
    if not os.path.exists(path):
        print("missing", name)
        continue
    sheet = Image.open(path).convert("RGBA")
    size = sheet.width // cols
    frames = [sheet.crop((c * size, r * size, (c + 1) * size, (r + 1) * size))
              for r in range(sheet.height // size) for c in range(cols)]
    show = 256 if size < 256 else size
    for tag, color in BACKGROUNDS.items():
        out = []
        for f in frames:
            bg = Image.new("RGBA", f.size, color + (255,))
            bg.alpha_composite(f)
            out.append(bg.convert("RGB").resize((show, show), Image.LANCZOS))
        durations = [int(1000 / fps)] * len(out)
        if not loop:
            durations[-1] = 600            # hold the end, then replay
        gif = os.path.join(FX, name.replace(".png", f"_{tag}.gif"))
        out[0].save(gif, save_all=True, append_images=out[1:], duration=durations, loop=0, optimize=True)
        print("saved", gif)
