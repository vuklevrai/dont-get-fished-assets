using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

// Rebuilds the solid of a "blocky" glTF mesh as axis-aligned boxes.
// In-plane the model lives on a 0.1 grid; every exposed face of a cell is drawn either flat
// or as a square raised by RAISE. For each grid column along Z we pair entry (-Z) and exit (+Z)
// faces to get the solid's exact extent, which also covers thin plates (fins).
public static class Voxelize
{
    const double V = 0.1;
    const double RAISE = 0.022;
    const double INSET = 0.058; // side of a raised square

    public class Span { public int I, J; public double Z0, Z1; }

    public static List<Span> Columns(byte[] bin, int posOff, int vcount, int idxOff, int icount, int idxType, out int mismatched)
    {
        var px = new double[vcount]; var py = new double[vcount]; var pz = new double[vcount];
        for (int i = 0; i < vcount; i++)
        {
            px[i] = BitConverter.ToSingle(bin, posOff + i * 12);
            py[i] = BitConverter.ToSingle(bin, posOff + i * 12 + 4);
            pz[i] = BitConverter.ToSingle(bin, posOff + i * 12 + 8);
        }
        Func<int, int> idx = k => idxType == 5125 ? (int)BitConverter.ToUInt32(bin, idxOff + k * 4)
                                                  : BitConverter.ToUInt16(bin, idxOff + k * 2);
        // column (i,j) -> list of (plane, sign)
        var cols = new Dictionary<long, List<double[]>>();
        for (int t = 0; t + 2 < icount; t += 3)
        {
            int a = idx(t), b = idx(t + 1), c = idx(t + 2);
            double ux = px[b] - px[a], uy = py[b] - py[a];
            double vx = px[c] - px[a], vy = py[c] - py[a];
            double nz = ux * vy - uy * vx;
            double area2 = Math.Abs(nz);
            if (area2 < 1e-9) continue;
            // only faces whose normal is +-Z (z equal on all three vertices)
            if (Math.Abs(pz[a] - pz[b]) > 1e-4 || Math.Abs(pz[a] - pz[c]) > 1e-4) continue;
            double s = Math.Sign(nz);
            double x0 = Math.Min(px[a], Math.Min(px[b], px[c])), x1 = Math.Max(px[a], Math.Max(px[b], px[c]));
            double y0 = Math.Min(py[a], Math.Min(py[b], py[c])), y1 = Math.Max(py[a], Math.Max(py[b], py[c]));
            bool raised = Math.Abs((x1 - x0) - INSET) < 0.004 && Math.Abs((y1 - y0) - INSET) < 0.004;
            double plane = pz[a] - (raised ? s * RAISE : 0);
            // every grid cell whose (slightly offset) centre falls inside this triangle
            int i0 = (int)Math.Floor(x0 / V - 1e-6), i1 = (int)Math.Floor(x1 / V + 1e-6);
            int j0 = (int)Math.Floor(y0 / V - 1e-6), j1 = (int)Math.Floor(y1 / V + 1e-6);
            for (int i = i0; i <= i1; i++)
                for (int j = j0; j <= j1; j++)
                {
                    double cx = i * V + V / 2 + 0.0031, cy = j * V + V / 2 + 0.0017;
                    if (!Inside(cx, cy, px[a], py[a], px[b], py[b], px[c], py[c])) continue;
                    long key = K(i, j);
                    List<double[]> l;
                    if (!cols.TryGetValue(key, out l)) { l = new List<double[]>(); cols[key] = l; }
                    bool dup = false;
                    foreach (var e in l) if (Math.Abs(e[0] - plane) < 1e-4 && e[1] == s) { dup = true; break; }
                    if (!dup) l.Add(new double[] { plane, s });
                }
        }
        var spans = new List<Span>();
        mismatched = 0;
        foreach (var kv in cols)
        {
            int i = (int)(kv.Key / 100000) - 10000, j = (int)(kv.Key % 100000) - 10000;
            var l = kv.Value;
            l.Sort((p, q) => p[0].CompareTo(q[0]));
            // entry faces point -Z, exit faces +Z
            int k = 0;
            while (k < l.Count)
            {
                if (l[k][1] < 0 && k + 1 < l.Count && l[k + 1][1] > 0)
                {
                    spans.Add(new Span { I = i, J = j, Z0 = l[k][0], Z1 = l[k + 1][0] });
                    k += 2;
                }
                else { mismatched++; k++; }
            }
        }
        return spans;
    }

    static bool Inside(double x, double y, double ax, double ay, double bx, double by, double cx, double cy)
    {
        double d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by);
        double d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy);
        double d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay);
        bool neg = d1 < 0 || d2 < 0 || d3 < 0, pos = d1 > 0 || d2 > 0 || d3 > 0;
        return !(neg && pos);
    }

    // Greedy merge of spans with identical [Z0,Z1] into rectangles: returns "x0 y0 z0 x1 y1 z1" lines.
    public static List<double[]> Merge(List<Span> spans)
    {
        var groups = new Dictionary<string, HashSet<long>>();
        foreach (var s in spans)
        {
            string k = s.Z0.ToString("F4", CultureInfo.InvariantCulture) + "|" + s.Z1.ToString("F4", CultureInfo.InvariantCulture);
            HashSet<long> h;
            if (!groups.TryGetValue(k, out h)) { h = new HashSet<long>(); groups[k] = h; }
            h.Add(K(s.I, s.J));
        }
        var boxes = new List<double[]>();
        foreach (var kv in groups)
        {
            var parts = kv.Key.Split('|');
            double z0 = double.Parse(parts[0], CultureInfo.InvariantCulture), z1 = double.Parse(parts[1], CultureInfo.InvariantCulture);
            var cells = kv.Value;
            var list = new List<long>(cells); list.Sort();
            foreach (var key in list)
            {
                if (!cells.Contains(key)) continue;
                int i = (int)(key / 100000) - 10000, j = (int)(key % 100000) - 10000;
                // grow along j (y)
                int j2 = j;
                while (cells.Contains(K(i, j2 + 1))) j2++;
                // grow along i (x)
                int i2 = i;
                while (true)
                {
                    bool ok = true;
                    for (int jj = j; jj <= j2; jj++) if (!cells.Contains(K(i2 + 1, jj))) { ok = false; break; }
                    if (!ok) break;
                    i2++;
                }
                for (int ii = i; ii <= i2; ii++) for (int jj = j; jj <= j2; jj++) cells.Remove(K(ii, jj));
                boxes.Add(new double[] { i * V, j * V, z0, (i2 + 1) * V, (j2 + 1) * V, z1 });
            }
        }
        return boxes;
    }

    static long K(int i, int j) { return (long)(i + 10000) * 100000 + (j + 10000); }
}
