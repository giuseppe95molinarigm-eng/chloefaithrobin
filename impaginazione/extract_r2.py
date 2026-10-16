import sys, json, re, unicodedata, pypdf, pdfplumber
src, out = sys.argv[1], sys.argv[2]
r = pypdf.PdfReader(src); pl = pdfplumber.open(src)
BODY = lambda c: "AGP" in c["fontname"] and abs(c["size"]-11)<0.6

def quads(a):
    q=a.get("/QuadPoints")
    if not q:
        x0,y0,x1,y1=[float(v) for v in a["/Rect"]]; return [(x0,y0,x1,y1)]
    q=[float(v) for v in q]; res=[]
    for i in range(0,len(q),8):
        xs=q[i:i+8:2]; ys=q[i+1:i+8:2]; res.append((min(xs),min(ys),max(xs),max(ys)))
    return res

def build(page):
    """Return list of tokens: (text, char|None) in reading order, with body-only filter."""
    ch=page.chars; toks=[]; prev=None
    for c in ch:
        t=c["text"]
        if t==" " and prev is not None and len(prev["text"])>1 and c["x0"]<prev["x1"]-0.3: continue  # ligature ghost space
        if prev is not None and abs(c["top"]-prev["top"])>3:
            if prev["text"] not in (" ","-","­"): toks.append(("\r",None))
            elif prev["text"] in ("-","­"): toks.append(("\x00",None))  # possible hyphenation: hard boundary
        toks.append((unicodedata.normalize("NFC",t),c)); prev=c
    return toks

def fmt(s): return s

def ctx_from(toks, i, direction, nchars=60):
    """collect text from token index i going direction (-1 before, +1 after) until boundary"""
    out=[]; n=0; j=i
    while 0<=j<len(toks) and n<nchars:
        t,c=toks[j]
        if t=="\x00": break
        if c is not None and not BODY(c): break
        out.append(t); n+=len(t); j+=direction
    s="".join(reversed(out)) if direction<0 else "".join(out)
    return s

def inside(c,boxes,H):
    cx=(c["x0"]+c["x1"])/2; cy=H-(c["top"]+c["bottom"])/2
    return any(x0-0.6<=cx<=x1+0.6 and y0-0.8<=cy<=y1+0.8 for (x0,y0,x1,y1) in boxes)

def folio(page):
    t=page.extract_text() or ""; lines=[l.strip() for l in t.splitlines() if l.strip()]
    for l in lines[-1:]+lines[:1]:
        if re.fullmatch(r"\d{1,3}",l): return l
    return ""

rows=[]
for pi,p in enumerate(r.pages):
    refs=p.get("/Annots") or []
    if not refs: continue
    pp=pl.pages[pi]; H=float(pp.height); toks=build(pp); fol=folio(pp)
    used=set(); items=[]
    for ref in refs:
        a=ref.get_object(); st=a.get("/Subtype")
        if st=="/Popup": continue
        rect=[float(v) for v in a["/Rect"]]
        contents=(a.get("/Contents") or "").replace("\r","\n").strip()
        e=dict(id=ref.idnum,mpage=pi+1,folio=fol,y=rect[3],x=rect[0],original="",new="",note="",before="",after="")
        if st in ("/StrikeOut","/Highlight"):
            qs=quads(a); idx=[k for k,(t,c) in enumerate(toks) if c is not None and inside(c,qs,H)]
            if idx:
                s,eidx=idx[0],idx[-1]
                e["original"]="".join(t for t,c in toks[s:eidx+1] if t!="\x00")
                e["before"]=ctx_from(toks,s-1,-1); e["after"]=ctx_from(toks,eidx+1,1)
                e["body"]=all(BODY(toks[k][1]) for k in idx)
            else: e["body"]=False
            if st=="/StrikeOut":
                irt=a.get("/IRT")
                if irt is not None:
                    e.update(kind="Sostituzione",new=(irt.get_object().get("/Contents") or "").strip()); used.add(irt.idnum)
                else: e.update(kind="Eliminazione",note=contents)
            else: e.update(kind="Commento",note=contents)
            items.append(e)
        elif st=="/Caret":
            e.update(kind="_caret",new=contents); e["cx"]=(rect[0]+rect[2])/2; e["cy"]=(rect[1]+rect[3])/2; e["rect"]=rect
            items.append(e)
        elif st=="/Text":
            e.update(kind="Nota",note=contents,body=False); items.append(e)
    for e in items:
        if e["kind"]!="_caret": continue
        if e["id"] in used: e["drop"]=True; continue
        e["kind"]="Inserimento"
        # find insertion boundary: char on same line whose edge is closest to caret centre x
        py=H-e["cy"]; best=None
        for k,(t,c) in enumerate(toks):
            if c is None: continue
            if c["top"]-3<=py<=c["bottom"]+4 or (c["top"]-6<=H-e["rect"][3]<=c["bottom"]):
                for edge,pos in ((c["x0"],k),(c["x1"],k+1)):
                    d=abs(edge-e["cx"])
                    if best is None or d<best[0]: best=(d,pos)
        if best is None:
            e["body"]=False; continue
        pos=best[1]
        e["before"]=ctx_from(toks,pos-1,-1); e["after"]=ctx_from(toks,pos,1)
        e["body"]=True
    for e in items:
        if e.get("drop"): continue
        for k in ("cx","cy","rect"): e.pop(k,None)
        rows.append(e)
rows.sort(key=lambda e:(e["mpage"],-round(e["y"]/4),e["x"]))
for n,e in enumerate(rows,1): e["n"]=n
json.dump(rows,open(out,"w"),ensure_ascii=False,indent=1)
from collections import Counter
print(len(rows),Counter(e["kind"] for e in rows), "body:",sum(1 for e in rows if e.get("body")))
