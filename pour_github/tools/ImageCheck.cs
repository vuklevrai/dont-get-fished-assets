using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

// Small helpers to sanity-check the rendered water frames.
public static class ImageCheck
{
    static byte[] Pixels(Bitmap bmp)
    {
        var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
        var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        var bytes = new byte[data.Stride * bmp.Height];
        Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);
        bmp.UnlockBits(data);
        return bytes;
    }

    // mean absolute difference per channel (0-255) between two same-size images
    public static double MeanDiff(string a, string b)
    {
        using (var ba = new Bitmap(a))
        using (var bb = new Bitmap(b))
        {
            var pa = Pixels(ba);
            var pb = Pixels(bb);
            long sum = 0;
            for (int i = 0; i < pa.Length; i++) sum += Math.Abs(pa[i] - pb[i]);
            return (double)sum / pa.Length;
        }
    }

    // mean difference across the wrap seams (last column vs first column, last row vs first row)
    // compared with the mean difference between neighbouring columns/rows inside the image
    public static string SeamReport(string path)
    {
        using (var bmp = new Bitmap(path))
        {
            int w = bmp.Width, h = bmp.Height;
            var rect = new Rectangle(0, 0, w, h);
            var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
            int stride = data.Stride;
            var px = new byte[stride * h];
            Marshal.Copy(data.Scan0, px, 0, px.Length);
            bmp.UnlockBits(data);
            Func<int, int, int, int> at = (x, y, c) => px[y * stride + x * 3 + c];
            double seamX = 0, innerX = 0, seamY = 0, innerY = 0;
            for (int y = 0; y < h; y++)
                for (int c = 0; c < 3; c++)
                {
                    seamX += Math.Abs(at(w - 1, y, c) - at(0, y, c));
                    innerX += Math.Abs(at(w / 2, y, c) - at(w / 2 + 1, y, c));
                }
            for (int x = 0; x < w; x++)
                for (int c = 0; c < 3; c++)
                {
                    seamY += Math.Abs(at(x, h - 1, c) - at(x, 0, c));
                    innerY += Math.Abs(at(x, h / 2, c) - at(x, h / 2 + 1, c));
                }
            int n = h * 3;
            return string.Format("seamX={0:F2} innerX={1:F2} seamY={2:F2} innerY={3:F2}", seamX / n, innerX / n, seamY / (w * 3), innerY / (w * 3));
        }
    }

    // tiles an image 2x2 (to eyeball seams) or lays several frames side by side
    public static void Compose(string[] paths, int cols, string outPath, int cellSize)
    {
        int rows = (paths.Length + cols - 1) / cols;
        using (var outBmp = new Bitmap(cols * cellSize, rows * cellSize))
        using (var g = Graphics.FromImage(outBmp))
        {
            g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
            for (int i = 0; i < paths.Length; i++)
                using (var img = new Bitmap(paths[i]))
                    g.DrawImage(img, (i % cols) * cellSize, (i / cols) * cellSize, cellSize, cellSize);
            outBmp.Save(outPath, ImageFormat.Png);
        }
    }
}
