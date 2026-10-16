"""Apply a markup round (annotations on our own PDF) to doc.json.
usage: round2.py doc_in.json rows.json doc_out.json report.json"""
import sys, json, re, collections

DOC_IN, ROWS, DOC_OUT, REPORT = sys.argv[1:5]
doc = json.load(open(DOC_IN))
rows = json.load(open(ROWS))

# ------------------------------------------------------------------ flat token list
G = []   # [char, italic, blockinfo-or-None]
for b in doc:
    G.append(["\n", False, {k: v for k, v in b.items() if k != "runs"}])
    if b["type"] == "para":
        for t, it in b["runs"]:
            for c in t:
                G.append([c, it, None])
F = "".join(g[0] for g in G)


def rx(s):
    out = []
    for c in s:
        if c == "\r": out.append(r"[ \n]?")
        elif c in (" ", " "): out.append(r"[  ]")
        else: out.append(re.escape(c))
    return "".join(out)


def locate(e):
    b, o, a = e["before"], e["original"], e["after"]
    tries = [(40, 40), (25, 25), (15, 15), (40, 0), (0, 40), (25, 0), (0, 25), (8, 8), (60, 60), (100, 100)]
    for nb, na in tries:
        bb = b[-nb:] if nb else ""; aa = a[:na] if na else ""
        if len(bb) + len(aa) + len(o) < 6: continue
        pat = rx(bb) + "(" + rx(o) + ")" + rx(aa)
        ms = list(re.finditer(pat, F))
        if len(ms) == 1:
            return ms[0].start(1), ms[0].end(1)
    return None


def smart(new, prev_char):
    new = re.sub(r"\.\s\.\s\.", ". . .", new)
    out = []; p = prev_char
    for ch in new:
        if ch in "'\"":
            opening = p in ("", " ", "\n", " ", "—", "“", "(", "\t")
            ch = ("‘" if opening else "’") if ch == "'" else ("“" if opening else "”")
        out.append(ch); p = ch
    return "".join(out)


ITAL = {"italics": True, "add italics": True, "remove italics": False}
located, report = [], []
for e in rows:
    k = e["kind"]; note = e["note"].strip(); new = e["new"]
    rec = dict(n=e["n"], page=e["mpage"], kind=k, original=e["original"].replace("\r", " "), new=new, note=note)
    if not e.get("body") and k != "Commento":
        rec["status"] = "front matter (gen.py)"; report.append(rec); continue
    if k == "Commento" and note.lower().rstrip(".") not in ITAL:
        rec["status"] = "layout note (manual)"; report.append(rec); continue
    span = locate(e)
    if span is None:
        rec["status"] = "NOT FOUND"; report.append(rec); continue
    e["span"] = span; located.append(e); rec["status"] = "located"; report.append(rec)

# newest annotation wins on overlapping ranges
touched = []
ok = []
for e in sorted(located, key=lambda e: -e["id"]):
    s, t = e["span"]
    if e["kind"] != "Commento" and any(s < t2 and s2 < t and t > s for s2, t2 in touched):
        next(r for r in report if r["n"] == e["n"])["status"] = "overlap (newer edit wins)"; continue
    if e["kind"] != "Commento": touched.append((s, t))
    ok.append(e)


def prev_char(i):
    j = i - 1
    while j >= 0:
        if G[j][2] is not None: return "\n"
        return G[j][0]
    return ""


# italics first (no position change), then text edits from the end backwards
for e in [e for e in ok if e["kind"] == "Commento"]:
    s, t = e["span"]; val = ITAL[e["note"].strip().lower().rstrip(".")]
    for i in range(s, t):
        if G[i][2] is None: G[i][1] = val
edits = sorted([e for e in ok if e["kind"] != "Commento"], key=lambda e: (-e["span"][0], -(e["span"][1] - e["span"][0])))
for e in edits:
    s, t = e["span"]; k = e["kind"]; new = e["new"]
    orig = F[s:t]
    if new.strip().lower() == "insert space": new = " "
    m = re.match(r"insert a paragraph break and then these (?:two )?paragraphs?:\s*(.*)", new, re.S | re.I)
    if m: new = "¶" + re.sub(r"\s*\n\s*\n\s*", "¶", m.group(1).strip())
    if k == "Eliminazione": new = ""
    pc = prev_char(s)
    nc = G[t][0] if t < len(G) and G[t][2] is None else "\n"
    allit = bool(orig.strip()) and all(G[i][1] for i in range(s, t) if G[i][2] is None and G[i][0].strip())
    if k == "Inserimento":
        allit = s > 0 and t < len(G) and G[s - 1][1] and G[t][1]
    if new and new != " " and not new.startswith("¶"):
        if new[0].isalnum() and pc.isalnum() and not orig[:1].isalnum(): new = " " + new
        elif orig[:1] == " " and (new[0].isalnum() or new[0] in "'\"“‘"): new = " " + new
        if new[-1].isalnum() and nc.isalnum() and not orig[-1:].isalnum(): new = new + " "
        elif new[-1] in ".?!,;:" and nc.isalnum(): new = new + " "
        elif orig[-1:] == " " and (new[-1].isalnum() or new[-1] in ".,;:?!”’"): new = new + " "
        # drop punctuation Chloe repeated from just outside the range
        if new[-1:] in ",.;:" and nc == new[-1:]: new = new[:-1]
    new = smart(new, pc)
    toks = []
    for c in new:
        if c == "¶": toks.append(["\n", False, {"type": "para", "indent": True}])
        else: toks.append([c, allit, None])
    if k == "Eliminazione" and pc.isalnum() and nc.isalnum() and " " in orig:
        toks = [[" ", False, None]]
    G[s:t] = toks

# ------------------------------------------------------------------ rebuild blocks
out = []; cur = None
for c, it, info in G:
    if info is not None:
        b = dict(info)
        if b["type"] == "para": b["runs"] = []
        out.append(b); cur = b if b["type"] == "para" else None
        continue
    if cur is None:
        cur = {"type": "para", "indent": True, "runs": []}; out.append(cur)
    if cur["runs"] and cur["runs"][-1][1] == it: cur["runs"][-1][0] += c
    else: cur["runs"].append([c, it])


def tidy(runs):
    chars = [(c, it) for t, it in runs for c in t]
    s = "".join(c for c, _ in chars)
    dele = set(); ins = {}
    for mm in re.finditer(r"(?<=[A-Za-z’”)])( +)(?=[,;:?!]|\.(?![ .\d]|\s\.))", s): dele.update(range(mm.start(1), mm.end(1)))
    for mm in re.finditer(r"([,;:])( ?)\1", s): dele.update(range(mm.start(2), mm.end()))
    for mm in re.finditer(r"(?<= ) +", s): dele.update(range(mm.start(), mm.end()))
    for mm in re.finditer(r"(?<=[a-z][.?!,;:])(?=[A-Z“])|(?<=[.?!,]”)(?=[A-Za-z“])", s): ins[mm.start()] = " "
    o = []
    for k, (c, it) in enumerate(chars):
        if k in ins: o.append((" ", it))
        if k in dele: continue
        o.append((c, it))
    while o and o[0][0] == " ": o.pop(0)
    while o and o[-1][0] == " ": o.pop()
    res = []
    for c, it in o:
        if res and res[-1][1] == it: res[-1][0] += c
        else: res.append([c, it])
    return res


for b in out:
    if b["type"] == "para": b["runs"] = tidy(b["runs"])
out = [b for b in out if not (b["type"] == "para" and not "".join(t for t, _ in b["runs"]).strip())]
json.dump(out, open(DOC_OUT, "w"), ensure_ascii=False, indent=0)
json.dump(report, open(REPORT, "w"), ensure_ascii=False, indent=1)
print(collections.Counter(r["status"] for r in report))
for r in report:
    if r["status"] not in ("located",): print(r["n"], r["page"], r["status"], "|", r["original"][:50], "=>", r["new"][:50], "|", r["note"][:40])
