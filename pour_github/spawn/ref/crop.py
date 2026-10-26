import bpy, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
src, out_dir = argv[0], argv[1]
crops = [tuple(map(int, c.split(","))) for c in argv[2:]]
img = bpy.data.images.load(src)
w, h = img.size
px = list(img.pixels)  # RGBA floats, rows bottom-to-top
for i, (x0, y0, cw, ch, scale) in enumerate(crops):
    out = bpy.data.images.new(f"crop{i}", cw * scale, ch * scale, alpha=False)
    data = [0.0] * (cw * scale * ch * scale * 4)
    for oy in range(ch * scale):
        sy = h - 1 - (y0 + oy // scale)          # image y is top-down in the request
        for ox in range(cw * scale):
            sx = x0 + ox // scale
            si = (sy * w + sx) * 4
            di = ((ch * scale - 1 - oy) * cw * scale + ox) * 4
            data[di:di + 4] = px[si:si + 4]
    out.pixels = data
    out.filepath_raw = os.path.join(out_dir, os.path.splitext(os.path.basename(src))[0] + f"_crop{i}.png")
    out.file_format = "PNG"
    out.save()
    print("saved", out.filepath_raw)
