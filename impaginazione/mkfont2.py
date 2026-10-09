import sys, io
from fontTools.cffLib import CFFFontSet
from fontTools.fontBuilder import FontBuilder
from fontTools.agl import toUnicode
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.psCharStrings import T2WidthExtractor

src, dst, family, style = sys.argv[1:5]
extra = dict(a.split("=",1) for a in sys.argv[5:] if "=" in a and not a.startswith("add:"))   # char=glyph overrides
adds = [a[4:] for a in sys.argv[5:] if a.startswith("add:")]   # add:<fontfile>:<chars>
cff = CFFFontSet(); cff.decompile(io.BytesIO(open(src, "rb").read()), None)
top = cff[cff.fontNames[0]]; order = top.getGlyphOrder(); cs = top.CharStrings
upm = int(round(1 / top.FontMatrix[0])) if hasattr(top, "FontMatrix") else 1000
charstrings = {}; metrics = {}
for g in order:
    c = cs[g]; c.decompile()
    ext = T2WidthExtractor(getattr(c, "subrs", []) or [], top.GlobalSubrs, c.private.nominalWidthX, c.private.defaultWidthX)
    ext.execute(c); w = int(round(ext.width))
    pen = T2CharStringPen(w, None); cs[g].draw(pen); charstrings[g] = pen.getCharString()
    bp = BoundsPen(None); cs[g].draw(bp); b = bp.bounds or (0, 0, 0, 0)
    metrics[g] = (w, int(b[0]))
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
for spec in adds:
    fpath, chars = spec.split("::", 1)
    sf = TTFont(fpath); scm = sf.getBestCmap(); sgs = sf.getGlyphSet(); sc = 1000.0 / sf["head"].unitsPerEm
    for ch in chars:
        if ord(ch) not in scm: print("  missing in source", fpath, repr(ch)); continue
        gname = "x_uni%04X" % ord(ch)
        if gname in charstrings: continue
        sg = sgs[scm[ord(ch)]]; w = int(round(sg.width * sc))
        pen = T2CharStringPen(w, sgs); sg.draw(TransformPen(pen, (sc, 0, 0, sc, 0, 0))); charstrings[gname] = pen.getCharString()
        bp = BoundsPen(sgs); sg.draw(TransformPen(bp, (sc, 0, 0, sc, 0, 0))); b = bp.bounds or (0, 0, 0, 0)
        metrics[gname] = (w, int(b[0])); order.append(gname); extra[ch] = gname
cmap = {}
for g in order:
    u = toUnicode(g)
    if g != ".notdef" and not g.startswith("x_uni") and u and len(u) == 1: cmap.setdefault(ord(u), g)
if 0x20 in cmap: cmap.setdefault(0xA0, cmap[0x20])
for ch, g in extra.items(): cmap[ord(ch)] = g
if "hyphen" in order:
    for u in (0x2010, 0x2011, 0xAD): cmap[u] = "hyphen"
psname = (family + "-" + style).replace(" ", "")
fb = FontBuilder(upm, isTTF=False)
fb.setupGlyphOrder(order)
fb.setupCharacterMap(cmap)
fb.setupCFF(psname, {"FullName": family + " " + style, "FamilyName": family, "Weight": style}, charstrings, {})
fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=750, descent=-250)
fb.setupNameTable({"familyName": family, "styleName": style, "psName": psname})
fb.setupOS2(sTypoAscender=750, sTypoDescender=-250, sTypoLineGap=0, usWinAscent=900, usWinDescent=300,
            fsSelection=(0x01 if style == "Italic" else 0x40), usWeightClass=700 if style == "Bold" else 400)
fb.setupPost()
if style == "Italic": fb.font["head"].macStyle = 2
ligs = [g for g in order if "_" in g]
rules = ["    sub %s by %s;" % (" ".join(g.split("_")), g) for g in sorted(ligs, key=lambda x: -x.count("_")) if g != "T_h" and all(p in order for p in g.split("_"))]
fea = "languagesystem DFLT dflt;\nlanguagesystem latn dflt;\n"
if rules: fea += "feature liga {\n%s\n} liga;\n" % "\n".join(rules)
if "T_h" in order: fea += "feature dlig {\n    sub T h by T_h;\n} dlig;\n"
addOpenTypeFeaturesFromString(fb.font, fea)
fb.save(dst); print(dst, len(order))
