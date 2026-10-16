import sys
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.psCharStrings import T2CharString
font_path, dejavu = sys.argv[1], sys.argv[2]
f = TTFont(font_path); gs = f.getGlyphSet(); cm = f.getBestCmap()
gname = cm[0x01CE]
a = cm[ord("a")]
dj = TTFont(dejavu); dgs = dj.getGlyphSet(); dcm = dj.getBestCmap()
car = dgs[dcm[0x02C7]]
bp = BoundsPen(dgs); car.draw(bp); cx0, cy0, cx1, cy1 = bp.bounds
bpa = BoundsPen(gs); gs[a].draw(bpa); ax0, ay0, ax1, ay1 = bpa.bounds
aw = f["hmtx"][a][0]
target_w = (ax1 - ax0) * 0.62
sc = target_w / (cx1 - cx0)
dx = (ax0 + ax1) / 2 - (cx0 + cx1) / 2 * sc
dy = ay1 + 70 - cy0 * sc
cff = f["CFF "].cff; top = cff[cff.fontNames[0]]; cs = top.CharStrings
pen = T2CharStringPen(aw, gs)
gs[a].draw(pen)
car.draw(TransformPen(pen, (sc, 0, 0, sc, dx, dy)))
newcs = pen.getCharString(private=cs[a].private, globalSubrs=top.GlobalSubrs)
cs[gname] = newcs
f["hmtx"][gname] = (aw, int(ax0))
f.save(font_path)
print("rebuilt", gname, "scale", round(sc, 3))
