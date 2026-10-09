import sys, numpy as np, potrace
from PIL import Image, ImageFilter
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("L")
S = 4
im = im.resize((im.width * S, im.height * S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.0)).point(lambda v: 0 if v < 140 else 255).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(1.5))
a = np.array(im)
bm = potrace.Bitmap(a < 140)
path = bm.trace(turdsize=120, alphamax=1.0, opticurve=True, opttolerance=0.2)
# bounding box of ink
ys, xs = np.where(a < 140)
x0, y0, x1, y1 = xs.min() - 4, ys.min() - 4, xs.max() + 4, ys.max() + 4
parts = []
P=lambda p:(p.x,p.y) if hasattr(p,'x') else tuple(p)
for curve in path:
    pts=[P(curve.start_point)]+[P(sg.end_point) for sg in curve]
    xs_=[p[0] for p in pts]; ys_=[p[1] for p in pts]
    if max(xs_)-min(xs_) > 0.9*(x1-x0) and max(ys_)-min(ys_) > 0.9*(y1-y0): continue
    P=lambda p:(p.x,p.y) if hasattr(p,"x") else tuple(p)
    d = ["M%.2f,%.2f" % P(curve.start_point)]
    for seg in curve:
        if seg.is_corner:
            d.append("L%.2f,%.2f L%.2f,%.2f" % (P(seg.c) + P(seg.end_point)))
        else:
            d.append("C%.2f,%.2f %.2f,%.2f %.2f,%.2f" % (P(seg.c1) + P(seg.c2) + P(seg.end_point)))
    d.append("Z"); parts.append(" ".join(d))
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%d %d %d %d" width="%d" height="%d">'
       '<path fill="device-cmyk(0 0 0 1)" fill-rule="evenodd" d="%s"/></svg>') % (x0, y0, x1 - x0, y1 - y0, x1 - x0, y1 - y0, " ".join(parts))
open(dst, "w").write(svg)
print("bbox", x0, y0, x1, y1, "curves", len(path), "ratio", (x1 - x0) / (y1 - y0))
