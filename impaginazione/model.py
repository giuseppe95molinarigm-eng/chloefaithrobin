"""Rebuild Gold Man's body text (prologue -> acknowledgements) from the markup PDF,
apply Chloe's round-1 annotations, and emit a JSON document model."""
import sys, json, re, collections, unicodedata
import pypdf, pdfplumber

SRC = sys.argv[1]; OUT = sys.argv[2]
FIRST, LAST = 7, 387
r = pypdf.PdfReader(SRC); pl = pdfplumber.open(SRC)


def fam(c):
    f = c["fontname"].split("+")[-1]
    return f


def is_body(c):
    f = fam(c)
    return ("AGaramond" in f or "Times" in f or "Arial" in f or "Minion" in f) and 8.5 < c["size"] < 12


# ---------------------------------------------------------------- tokens
class Tok:
    __slots__ = ("t", "it", "dele", "ins", "post", "page", "line", "kind")

    def __init__(s, t, it, page, line, kind="c"):
        s.t = t; s.it = it; s.dele = False; s.ins = []; s.post = []; s.page = page; s.line = line; s.kind = kind


pages = {}          # pn -> dict(chars, tokmap, lines)
for pn in range(FIRST, LAST + 1):
    p = pl.pages[pn - 1]
    chars = p.chars
    # group by baseline
    lines = []
    for i, c in enumerate(chars):
        base = round(c["matrix"][5], 1)
        if lines and abs(lines[-1]["base"] - base) < 3 and c["x0"] >= lines[-1]["xlast"] - 30:
            lines[-1]["idx"].append(i); lines[-1]["xlast"] = c["x1"]
        else:
            lines.append(dict(base=base, idx=[i], xlast=c["x1"]))
    for L in lines:
        cs = [chars[i] for i in L["idx"]]
        fams = collections.Counter(fam(c) for c in cs if c["text"] != " ")
        f = fams.most_common(1)[0][0] if fams else ""
        size = max(c["size"] for c in cs)
        if "Montserrat-Regular" in f and size < 10: L["role"] = "folio"
        elif "AvantGarde" in f and size > 20: L["role"] = "chap"
        elif "AvantGarde" in f: L["role"] = "sub"
        elif "Montserrat-Thin" in f: L["role"] = "acktitle"
        elif all(is_body(c) or c["text"] == " " for c in cs): L["role"] = "body"
        else: L["role"] = "other"
        txt = [c for c in cs if c["text"] != " "]
        L["x0"] = min(c["x0"] for c in txt) if txt else 0
        L["x1"] = max(c["x1"] for c in txt) if txt else 0
        L["text"] = "".join(c["text"] for c in cs)
    body = [L for L in lines if L["role"] == "body"]
    # ornament (scene break) positions
    orn = []
    for cv in p.curves:
        if 12 < cv["x1"] - cv["x0"] < 17 and 12 < cv["bottom"] - cv["top"] < 17 and cv.get("stroke") and (cv.get("linewidth") or 0) > 1.2:
            orn.append(cv["top"])
    pages[pn] = dict(chars=chars, lines=lines, body=body, orn=orn, H=float(p.height))
    if body:
        xs = collections.Counter(round(L["x0"]) for L in body)
        left = min(x for x, n in xs.items() if n >= max(1, len(body) // 6)) if len(body) > 2 else min(xs)
        pages[pn]["left"] = left
        x1s = sorted(L["x1"] for L in body)
        pages[pn]["right"] = x1s[int(len(x1s) * 0.8)] if x1s else 300

# corpus of words for hyphenation decisions
corpus = collections.Counter()
for pn, P in pages.items():
    for L in P["body"]:
        for w in re.findall(r"[A-Za-z’'\-]+", L["text"].strip().rstrip("-")):
            corpus[w.lower()] += 1

# line-end hyphen decisions (checked by hand); True = real compound hyphen
HYPH = []
HYPH_FORCE = {}
# ---------------------------------------------------------------- build stream
stream = []          # list of Tok or marker dicts
charmap = {}         # (pn, char_index) -> Tok
para_open = False


def marker(kind, **kw):
    d = dict(kind=kind); d.update(kw); stream.append(d); return d


pending_scene = False
prev_line_end = None   # info about previous body line: ends_para(bool), hyphen(bool)
cur_para = None
for pn in range(FIRST, LAST + 1):
    P = pages[pn]; chars = P["chars"]
    if pn == 386: continue
    heads = [L for L in P["lines"] if L["role"] in ("chap", "sub", "acktitle")]
    if heads:
        chap = [L for L in heads if L["role"] in ("chap", "acktitle")]
        sub = [L for L in heads if L["role"] == "sub"]
        if chap:
            marker("chapter", title=chap[0]["text"].strip(), sub=" ".join(L["text"].strip() for L in sub),
                   ack=chap[0]["role"] == "acktitle", page=pn)
            prev_line_end = dict(end=True, hyph=False); cur_para = None
    orn = sorted(P["orn"])
    for li, L in enumerate(P["body"]):
        top = min(chars[i]["top"] for i in L["idx"])
        while orn and orn[0] < top:
            orn.pop(0); marker("scene"); prev_line_end = dict(end=True, hyph=False); cur_para = None
        indent = L["x0"] - P["left"] > 7
        new_para = prev_line_end is None or prev_line_end["end"] or indent
        if new_para:
            cur_para = marker("para", indent=indent, page=pn)
        elif prev_line_end.get("hyph"):
            # decide whether the line-end hyphen is a real one
            last = prev_line_end["tok"]
            a = prev_line_end["word"]; b = re.match(r"[A-Za-z’']*", "".join(chars[i]["text"] for i in L["idx"][:30])).group(0)
            joined_h = (a + "-" + b).lower(); joined = (a + b).lower()
            if corpus[joined_h] > 0 and corpus[joined] == 0: keep = True
            elif corpus[joined] > 0: keep = False
            elif b[:1].isupper(): keep = True
            elif corpus[a.lower()] > 0 and corpus[b.lower()] > 0 and len(a) > 2 and len(b) > 2: keep = True
            else: keep = False
            # the original setting had hyphenation switched off: every line-end hyphen is a real one
            keep = True
            if joined_h in HYPH_FORCE: keep = HYPH_FORCE[joined_h]
            HYPH.append(dict(page=pn, a=a, b=b, keep=keep))
            if not keep: last.kind = "softhyph"
        prev = None
        idxs = L["idx"]
        for n_i, i in enumerate(idxs):
            c = chars[i]; t = unicodedata.normalize("NFC", c["text"])
            if t == " " and prev is not None and len(prev["text"]) > 1 and c["x0"] < prev["x1"] - 0.3:
                nx = next((chars[j] for j in idxs[n_i + 1:] if chars[j]["text"] != " "), None)
                if nx is not None and nx["x0"] - prev["x1"] < 1.0:
                    continue   # ligature ghost space
            tok = Tok(t, "Italic" in fam(c), pn, li)
            stream.append(tok); charmap[(pn, i)] = tok; prev = c
        # line end analysis
        last_txt = L["text"].rstrip(" ")
        ends_space = L["text"].endswith(" ")
        full = L["x1"] >= P["right"] - 4
        if ends_space:
            end = False
        elif last_txt.endswith(("—", "-", "/")) and full:
            end = False
        else:
            end = True
        info = dict(end=end, hyph=False)
        if not end and last_txt.endswith("-") and not ends_space:
            m = re.search(r"([A-Za-z’']+)-$", last_txt)
            if m:
                info.update(hyph=True, word=m.group(1), tok=stream[-1])
        if not end and not ends_space and not last_txt.endswith(("—", "-", "/")):
            pass
        prev_line_end = info
    while orn:
        orn.pop(0); marker("scene"); prev_line_end = dict(end=True, hyph=False); cur_para = None

print("tokens", sum(1 for s in stream if isinstance(s, Tok)), "paras", sum(1 for s in stream if isinstance(s, dict) and s["kind"] == "para"),
      "scenes", sum(1 for s in stream if isinstance(s, dict) and s["kind"] == "scene"))

# ---------------------------------------------------------------- annotations
def quads(a):
    q = a.get("/QuadPoints")
    if not q:
        x0, y0, x1, y1 = [float(v) for v in a["/Rect"]]; return [(x0, y0, x1, y1)]
    q = [float(v) for v in q]; res = []
    for i in range(0, len(q), 8):
        xs = q[i:i + 8:2]; ys = q[i + 1:i + 8:2]; res.append((min(xs), min(ys), max(xs), max(ys)))
    return res


def inside(c, boxes, H):
    cx = (c["x0"] + c["x1"]) / 2; cy = H - (c["top"] + c["bottom"]) / 2
    return any(x0 - 0.6 <= cx <= x1 + 0.6 and y0 - 0.8 <= cy <= y1 + 0.8 for (x0, y0, x1, y1) in boxes)


def smart(new, prev_char):
    new = re.sub(r"\.\s\.\s\.", ".\u00a0.\u00a0.", new)
    out = []; p = prev_char
    for ch in new:
        if ch in "'\"":
            opening = p in ("", " ", "\r", " ", "—", "“", "(", "\t")
            ch = ("‘" if opening else "’") if ch == "'" else ("“" if opening else "”")
        out.append(ch); p = ch
    return "".join(out)


anns = []
for pn in range(FIRST, LAST + 1):
    pg = r.pages[pn - 1]; P = pages[pn]; H = P["H"]
    refs = pg.get("/Annots") or []
    used = set()
    for ref in refs:
        a = ref.get_object()
        if a.get("/Subtype") == "/StrikeOut" and a.get("/IRT") is not None:
            used.add(a.raw_get("/IRT").idnum)
    for ref in refs:
        a = ref.get_object(); st = a.get("/Subtype")
        if st == "/Popup" or ref.idnum in used: continue
        e = dict(id=ref.idnum, page=pn, st=st, note=(a.get("/Contents") or "").strip())
        rect = [float(v) for v in a["/Rect"]]
        if st in ("/StrikeOut", "/Highlight"):
            qs = quads(a)
            toks = [charmap[(pn, i)] for i, c in enumerate(P["chars"]) if (pn, i) in charmap and inside(c, qs, H)]
            e["toks"] = toks
            if st == "/StrikeOut":
                irt = a.get("/IRT")
                e["op"] = "rep" if irt is not None else "del"
                e["new"] = (irt.get_object().get("/Contents") or "").strip() if irt is not None else ""
            else:
                e["op"] = "hl"
        elif st == "/Caret":
            cx = (rect[0] + rect[2]) / 2; cy = H - (rect[1] + rect[3]) / 2
            best = None
            for i, c in enumerate(P["chars"]):
                if (pn, i) not in charmap: continue
                if c["top"] - 3 <= cy <= c["bottom"] + 4 or (c["top"] - 6 <= H - rect[3] <= c["bottom"]):
                    for edge, side in ((c["x0"], "before"), (c["x1"], "after")):
                        d = abs(edge - cx)
                        if best is None or d < best[0]: best = (d, i, side)
            if best is None: continue
            e["op"] = "ins"; e["new"] = (a.get("/Contents") or "").strip()
            e["at"] = charmap[(pn, best[1])]; e["side"] = best[2]
        elif st == "/Text":
            e["op"] = "note"; e["y"] = H - rect[3]
        anns.append(e)

# token index lookup
tindex = {}
for k, s in enumerate(stream):
    if isinstance(s, Tok): tindex[id(s)] = k

stats = collections.Counter(); skipped = []
touched = set()
ITAL = {"italics": True, "remove italics": False}


def ctx_prev_char(k):
    j = k - 1
    while j >= 0:
        s = stream[j]
        if isinstance(s, Tok):
            if not s.dele: return s.t[-1:]
        else: return "\r"
        j -= 1
    return ""


def next_tok_text(k):
    j = k
    while j < len(stream):
        s = stream[j]
        if isinstance(s, Tok):
            if not s.dele and s.kind != "softhyph": return s.t[:1]
        else: return "\r"
        j += 1
    return ""



DEDUP = []
def prev_word(k):
    s = ""
    j = k - 1
    while j >= 0 and isinstance(stream[j], Tok) and len(s) < 40:
        if not stream[j].dele: s = stream[j].t + s
        j -= 1
    m = re.search(r"([A-Za-z’']+)\s+$", s)
    return m.group(1) if m else ""
def next_text(k):
    s = ""
    j = k
    while j < len(stream) and isinstance(stream[j], Tok) and len(s) < 3:
        if not stream[j].dele: s += stream[j].t
        j += 1
    return s

# newest annotation wins on overlaps
for e in sorted(anns, key=lambda e: -e["id"]):
    op = e["op"]
    if op in ("rep", "del"):
        ks = sorted(tindex[id(t)] for t in e["toks"])
        if not ks: skipped.append((e["id"], e["page"], "no text")); continue
        rng = range(ks[0], ks[-1] + 1)
        if any(k in touched for k in rng):
            stats["dup_skipped"] += 1; skipped.append((e["id"], e["page"], "overlap")); continue
        toks = [stream[k] for k in rng if isinstance(stream[k], Tok)]
        allit = all(t.it for t in toks if t.t.strip())
        for k in rng:
            touched.add(k)
            if isinstance(stream[k], Tok): stream[k].dele = True
        if op == "del":
            otxt = "".join(t.t for t in toks)
            pc = ctx_prev_char(ks[0]); nc = next_text(ks[-1] + 1)[:1]
            if " " in otxt and (pc.isalnum() or pc in "’”.,?!") and nc.isalnum():
                stream[ks[0]].ins.append((" ", False))
        if op == "rep":
            first = ks[0]
            new = smart(e["new"], ctx_prev_char(first))
            otxt = "".join(t.t for t in toks)
            if otxt[:1] == " " and new[:1] not in (" ", ",", ".", ";", ":", "?", "!", "’", "”"): new = " " + new
            if otxt[-1:] == " " and new[-1:] != " " and new: new = new + " "
            pc0 = ctx_prev_char(first); nc0 = next_text(ks[-1] + 1)[:1]
            if new and pc0.isalnum() and new[0].isalnum() and not otxt[:1].isalnum(): new = " " + new
            if new and nc0.isalnum() and new[-1].isalnum() and not otxt[-1:].isalnum(): new = new + " "
            # de-duplicate words/punctuation that Chloe repeated outside the struck range
            pw = prev_word(first); nw = next_text(ks[-1] + 1)
            m1 = re.match(r"([A-Za-z’']+)\s+", new)
            if m1 and pw and m1.group(1).lower() == pw.lower():
                new = new[m1.end():]; DEDUP.append((e["page"], "lead:" + pw))
            if new and nw[:1] and new[-1] in ",.;:" and nw[:1] == new[-1]:
                new = new[:-1]; DEDUP.append((e["page"], "trail:" + nw[:1]))
            stream[first].ins.append((new, allit))
        stats[op] += 1
    elif op == "ins":
        tok = e["at"]; k = tindex[id(tok)]; new = e["new"]
        if e["side"] == "after":
            nxt = next((stream[j] for j in range(k + 1, len(stream)) if isinstance(stream[j], Tok)), None)
            if tok.dele and nxt is not None and nxt.dele and (k + 1) in touched:
                stats["ins_skipped"] += 1; skipped.append((e["id"], e["page"], "ins in deleted")); continue
        else:
            prv = next((stream[j] for j in range(k - 1, -1, -1) if isinstance(stream[j], Tok)), None)
            if tok.dele and prv is not None and prv.dele:
                stats["ins_skipped"] += 1; skipped.append((e["id"], e["page"], "ins in deleted")); continue
        if new == "¶":
            if e["side"] == "after": tok.post.append(("PARA", False))
            else: tok.ins.insert(0, ("PARA", False))
            stats["para"] += 1; continue
        if e["side"] == "after":
            pc = tok.t[-1:]; nxt = next((stream[j] for j in range(k + 1, len(stream)) if isinstance(stream[j], Tok)), None)
            nc = (nxt.ins[0][0][:1] if nxt and nxt.ins else (nxt.t[:1] if nxt else ""))
            it = tok.it and bool(nxt and nxt.it)
        else:
            pc = ctx_prev_char(k); nc = tok.ins[0][0][:1] if tok.ins else tok.t[:1]
            prv = next((stream[j] for j in range(k - 1, -1, -1) if isinstance(stream[j], Tok)), None)
            it = tok.it and bool(prv and prv.it)
        word = bool(re.match(r"^[A-Za-z0-9’'\"]", new)) and (len(new) >= 2 or new in ("I", "a", "A"))
        if word and not (pc.isalnum() and nc.isalnum()):
            if (pc.isalnum() or pc in (",", ".", "?", "!", ";", ":", "”", "’")) and not new.startswith(("'", '"')): new = " " + new
            if nc.isalnum() or nc in ("“",): new = new + " "
        new = smart(new, pc)
        if e["side"] == "after": tok.post.append((new, it))
        elif tok.dele: tok.ins.insert(0, (new, it))
        else: tok.ins.append((new, it))
        stats["ins"] += 1
    elif op == "hl":
        n = e["note"].strip().lower().rstrip(".")
        ks = sorted(tindex[id(t)] for t in e["toks"])
        if n in ITAL and ks:
            for k in range(ks[0], ks[-1] + 1):
                if isinstance(stream[k], Tok): stream[k].it = ITAL[n]
            # also the inserted replacement text inside the range
            for k in range(ks[0], ks[-1] + 1):
                if isinstance(stream[k], Tok): stream[k].ins = [(t, ITAL[n]) for t, _ in stream[k].ins]
            stats["ital"] += 1
        elif n.startswith("join this to next paragraph"):
            # remove the closing quote at the end of the highlighted paragraph, then join with next paragraph
            k = ks[-1]
            for j in range(k, ks[0], -1):
                if isinstance(stream[j], Tok) and stream[j].t == "”": stream[j].dele = True; break
            for j in range(k + 1, len(stream)):
                if isinstance(stream[j], dict):
                    if stream[j]["kind"] == "para": stream[j]["kind"] = "join"; break
                elif stream[j].t.strip(): break
            stats["join"] += 1
        elif n.startswith("join to previous paragraph"):
            for j in range(ks[0], -1, -1):
                if isinstance(stream[j], dict):
                    if stream[j]["kind"] == "para": stream[j]["kind"] = "join"
                    break
            stats["join"] += 1
        else:
            stats["hl_layout"] += 1
    elif op == "note":
        n = e["note"].lower()
        if "remove paragraph indent" in n:
            # paragraph whose first line is closest below/at the note y on this page
            best = None
            for k, s in enumerate(stream):
                if isinstance(s, dict) and s["kind"] == "para" and s.get("page") == e["page"]:
                    nt = next(stream[j] for j in range(k + 1, len(stream)) if isinstance(stream[j], Tok))
                    # position of that first char
                    for (pn, i), t in charmap.items():
                        if t is nt:
                            y = pages[pn]["chars"][i]["top"]; d = abs(y - e["y"])
                            if best is None or d < best[0]: best = (d, k)
                            break
            if best: stream[best[1]]["indent"] = False; stats["noindent"] += 1
        else:
            stats["note_layout"] += 1

print(stats); print("skipped", skipped); print("dedup", DEDUP)

# ---------------------------------------------------------------- serialize
doc = []          # blocks: {type: chapter/para/scene, ...}
cur = None


def flush_run(runs, text, it):
    if not text: return
    if runs and runs[-1][1] == it: runs[-1][0] += text
    else: runs.append([text, it])


for s in stream:
    if isinstance(s, dict):
        if s["kind"] == "chapter":
            doc.append(dict(type="chapter", title=s["title"], sub=s["sub"], ack=s["ack"])); cur = None
        elif s["kind"] == "scene":
            doc.append(dict(type="scene")); cur = None
        elif s["kind"] == "para":
            cur = dict(type="para", indent=s["indent"], runs=[]); doc.append(cur)
        elif s["kind"] == "join":
            if cur is None: cur = dict(type="para", indent=True, runs=[]); doc.append(cur)
        continue
    for t, it in s.ins:
        if t == "\x01PARA":
            if cur is not None and not "".join(x for x, _ in cur["runs"]).strip():
                cur["indent"] = True
            else:
                cur = dict(type="para", indent=True, runs=[]); doc.append(cur)
            continue
        flush_run(cur["runs"], t, it)
    if not s.dele and s.kind != "softhyph":
        flush_run(cur["runs"], s.t, s.it)
    for t, it in s.post:
        if t == "PARA":
            cur = dict(type="para", indent=True, runs=[]); doc.append(cur); continue
        flush_run(cur["runs"], t, it)

# tidy whitespace
for b in doc:
    if b["type"] != "para": continue
    txt_runs = []
    for t, it in b["runs"]:
        t = re.sub(r"[ ]{2,}", " ", t)
        txt_runs.append([t, it])
    # collapse spaces across run boundaries
    for i in range(1, len(txt_runs)):
        if txt_runs[i - 1][0].endswith(" ") and txt_runs[i][0].startswith(" "):
            txt_runs[i][0] = txt_runs[i][0][1:]
    if txt_runs:
        txt_runs[0][0] = txt_runs[0][0].lstrip(" ")
        txt_runs[-1][0] = txt_runs[-1][0].rstrip(" ")
    # space before punctuation created by deletions
    full = []
    for i, (t, it) in enumerate(txt_runs):
        t = re.sub(r" +([,.;:?!”’])(?=\s|$|[”’])", r"\1", t) if False else t
        full.append([t, it])
    b["runs"] = [x for x in full if x[0]]
FIXLOG = []
def tidy(runs):
    chars = [(c, it) for t, it in runs for c in t]
    s = "".join(c for c, _ in chars)
    s0 = s
    dele = set(); ins = {}
    for mm in re.finditer(r"(?<=[A-Za-z’”)])( +)(?=[,;:?!]|\.(?![\u00a0.\d]|\s\.))", s): dele.update(range(mm.start(1), mm.end(1)))
    for mm in re.finditer(r"([,;:])( ?)", s): dele.update(range(mm.start(2), mm.end()))
    for mm in re.finditer(r"(?<= ) +", s): dele.update(range(mm.start(), mm.end()))
    for mm in re.finditer(r"(?<=[a-z][.?!,;:])(?=[A-Z“])|(?<=[.?!,]”)(?=[A-Za-z“])", s): ins[mm.start()] = " "
    out = []
    for k, (c, it) in enumerate(chars):
        if k in ins: out.append((" ", it))
        if k in dele: continue
        out.append((c, it))
    while out and out[0][0] == " ": out.pop(0)
    while out and out[-1][0] == " ": out.pop()
    res = []
    for c, it in out:
        if res and res[-1][1] == it: res[-1][0] += c
        else: res.append([c, it])
    s1 = "".join(c for c, _ in out)
    if s1 != s0.strip(): FIXLOG.append((s0, s1))
    return res
for b in doc:
    if b["type"] == "chapter":
        if b["sub"].startswith("A YEAR AGO,"):
            b["sub"] = "EIGHTEEN MONTHS EARLIER," + b["sub"][len("A YEAR AGO,"):]
    if b["type"] == "para": b["runs"] = tidy(b["runs"])
print("spacing fixes", len(FIXLOG))
import difflib
fx = []
for a, b2 in FIXLOG:
    sm = difflib.SequenceMatcher(None, a, b2)
    for op in sm.get_opcodes():
        if op[0] != "equal": fx.append((op[0], a[max(0, op[1]-25):op[2]+25], b2[max(0, op[3]-25):op[4]+25]))
json.dump(fx, open(OUT + ".fix.json", "w"), ensure_ascii=False, indent=0)
doc = [b for b in doc if not (b["type"] == "para" and not "".join(t for t, _ in b["runs"]).strip())]
json.dump(HYPH, open(OUT + ".hyph.json", "w"), ensure_ascii=False, indent=0)
json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=0)
print("blocks", collections.Counter(b["type"] for b in doc))
