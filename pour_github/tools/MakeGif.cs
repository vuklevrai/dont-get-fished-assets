using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Linq;

// Writes a looping animated GIF from a list of frames (GDI+ multi-frame save).
public static class MakeGif
{
    public static void Write(string[] frames, string outPath, int size, int delayCentiseconds, int tiles)
    {
        var gifCodec = ImageCodecInfo.GetImageEncoders().First(c => c.MimeType == "image/gif");
        var images = frames.Select(f => Render(f, size, tiles)).ToArray();

        // frame delays (0x5100) and infinite loop (0x5101) live on the first image
        var delay = (PropertyItem)System.Runtime.Serialization.FormatterServices.GetUninitializedObject(typeof(PropertyItem));
        delay.Id = 0x5100;
        delay.Type = 4;
        delay.Len = 4 * images.Length;
        delay.Value = new byte[4 * images.Length];
        for (int i = 0; i < images.Length; i++) BitConverter.GetBytes(delayCentiseconds).CopyTo(delay.Value, 4 * i);
        var loop = (PropertyItem)System.Runtime.Serialization.FormatterServices.GetUninitializedObject(typeof(PropertyItem));
        loop.Id = 0x5101;
        loop.Type = 3;
        loop.Len = 2;
        loop.Value = BitConverter.GetBytes((short)0);
        images[0].SetPropertyItem(delay);
        images[0].SetPropertyItem(loop);

        var first = new EncoderParameters(1);
        first.Param[0] = new EncoderParameter(Encoder.SaveFlag, (long)EncoderValue.MultiFrame);
        images[0].Save(outPath, gifCodec, first);
        var next = new EncoderParameters(1);
        next.Param[0] = new EncoderParameter(Encoder.SaveFlag, (long)EncoderValue.FrameDimensionTime);
        for (int i = 1; i < images.Length; i++) images[0].SaveAdd(images[i], next);
        var flush = new EncoderParameters(1);
        flush.Param[0] = new EncoderParameter(Encoder.SaveFlag, (long)EncoderValue.Flush);
        images[0].SaveAdd(flush);
        foreach (var img in images) img.Dispose();
    }

    // tiles x tiles copies of the frame, scaled into a size x size image
    static Bitmap Render(string path, int size, int tiles)
    {
        var bmp = new Bitmap(size, size);
        using (var src = new Bitmap(path))
        using (var g = Graphics.FromImage(bmp))
        {
            g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
            int cell = size / tiles;
            for (int y = 0; y < tiles; y++)
                for (int x = 0; x < tiles; x++)
                    g.DrawImage(src, new Rectangle(x * cell, y * cell, cell, cell), 0, 0, src.Width, src.Height, GraphicsUnit.Pixel, Wrap());
        }
        return bmp;
    }

    static ImageAttributes Wrap()
    {
        var a = new ImageAttributes();
        a.SetWrapMode(System.Drawing.Drawing2D.WrapMode.TileFlipXY);
        return a;
    }
}
