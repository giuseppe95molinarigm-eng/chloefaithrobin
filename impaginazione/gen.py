"""Generate the Gold Man interior HTML (WeasyPrint) from doc.json."""
import json, sys, html, re

DOC, OUT = sys.argv[1], sys.argv[2]
CREDIT = sys.argv[3] if len(sys.argv) > 3 else "Elena Pensiero"
doc = json.load(open(DOC))

GOLD_RULE = "device-cmyk(0.225 0.383 0.917 0.019)"
GOLD_TITLE = "device-cmyk(0.324 0.442 0.892 0.092)"
GOLD_SUB = "device-cmyk(0.399 0.583 0.845 0.286)"
BLACK = "device-cmyk(0 0 0 1)"

# grid: 11/16, first baseline 70pt from top, 28 lines
LEAD = 16.0
BASE_OFF = 10.75          # baseline offset inside a 16pt line box (asc 750 / desc 250 @ 11pt)
MT = 70.0 - BASE_OFF      # 59.25
MB = 576.0 - MT - 28 * LEAD

css = f"""
@font-face {{ font-family: AGP; src: url(otf/AGaramondPro-Regular.otf); font-style: normal; font-weight: 400; }}
@font-face {{ font-family: AGP; src: url(otf/AGaramondPro-Italic.otf); font-style: italic; font-weight: 400; }}
@font-face {{ font-family: AGP; src: url(otf/AGaramondPro-Bold.otf); font-style: normal; font-weight: 700; }}
@font-face {{ font-family: EBG; src: url(npm/package/files/eb-garamond-latin-400-normal.woff); font-style: normal; font-weight: 400; }}
@font-face {{ font-family: EBG; src: url(npm/package/files/eb-garamond-latin-400-italic.woff); font-style: italic; font-weight: 400; }}
@font-face {{ font-family: EBG; src: url(npm/package/files/eb-garamond-latin-500-normal.woff); font-style: normal; font-weight: 700; }}
@font-face {{ font-family: AvantGarde; src: url(fonts/AvantGardeLT-Book_7.ttf); }}
@font-face {{ font-family: MontThin; src: url(fonts/Montserrat-Thin_6.ttf); }}
@font-face {{ font-family: MontSC; src: url(otf/MontSC.otf); }}

@page {{
  size: 360pt 576pt;
  margin: {MT}pt 0 {MB}pt 0;
}}
@page :right {{
  margin-left: 54pt; margin-right: 44pt;
  background: url(rule_recto.svg) no-repeat -54pt -59.25pt / 360pt 576pt;
  @bottom-right {{ content: counter(page); font: 9pt/9pt MontSC; color: {BLACK};
                   vertical-align: bottom; padding-bottom: 17.85pt; text-align: right; }}
}}
@page :left {{
  margin-left: 47pt; margin-right: 51pt;
  background: url(rule_verso.svg) no-repeat -47pt -59.25pt / 360pt 576pt;
  @bottom-left {{ content: counter(page); font: 9pt/9pt MontSC; color: {BLACK};
                  vertical-align: bottom; padding-bottom: 17.85pt; text-align: left; }}
}}
@page :blank {{
  background: none;
  @bottom-left {{ content: none; }} @bottom-right {{ content: none; }}
}}
@page front {{
  counter-reset: page 0;
  background: none;
  @bottom-left {{ content: none; }} @bottom-right {{ content: none; }}
}}
@page map {{
  counter-reset: page 0;
  margin: 0; background: none;
  @bottom-left {{ content: none; }} @bottom-right {{ content: none; }}
}}

html {{ font-family: AGP, EBG, "DejaVu Sans"; font-size: 11pt; line-height: {LEAD}pt; color: {BLACK};
        font-variant-ligatures: common-ligatures discretionary-ligatures; font-kerning: normal; }}
body {{ margin: 0; }}
p {{ margin: 0; letter-spacing: -0.15pt; text-align: justify; hyphens: manual; text-indent: 14.2pt;
     orphans: 2; widows: 2; hyphenate-limit-chars: 5 2 2; hyphenate-character: "-"; }}
p.ni {{ text-indent: 0; }}
i {{ font-style: italic; }}

.front {{ page: front; break-before: page; }}
.front.recto {{ break-before: right; }}
.mappage {{ page: map; break-before: left; height: 576pt; display: flex; align-items: center; justify-content: center; }}
.mappage img {{ height: 548pt; }}

.title {{ height: {28*LEAD}pt; position: relative; text-align: center; margin-left: -5pt; margin-right: 5pt; }}
.title .art {{ position: absolute; left: 0; right: 0; top: {222 - MT}pt; text-align: center; }}
.title .art img {{ width: 250pt; height: 134pt; }}
.title .logo {{ position: absolute; left: 0; right: 0; top: {455 - MT}pt; text-align: center; }}
.title .logo img {{ width: 62pt; }}

.copyright {{ height: {28*LEAD}pt; display: flex; flex-direction: column; justify-content: flex-end; }}
.copyright div {{ font-size: 9pt; line-height: 12pt; text-align: center; margin-left: 2pt; margin-right: -2pt; }}
.copyright p {{ text-indent: 0; text-align: center; hyphens: none; }}
.copyright .gap {{ height: 12pt; }}

.dedication {{ padding-top: {185 - MT - 2}pt; text-align: center; font-style: italic; font-size: 10pt; line-height: 14pt; margin-left: -5pt; margin-right: 5pt; }}
.dedication p {{ text-align: center; text-indent: 0; hyphens: none; }}

.notehead {{ font: 11pt/16pt MontThin; color: {GOLD_TITLE}; letter-spacing: 1.35pt; text-align: center; height: {LEAD}pt; position: relative; top: -1.2pt; }}
.ul {{ text-decoration: underline; text-decoration-thickness: 0.5pt; text-underline-offset: 2pt; }}

.chapter {{ break-before: right; }}
.opener {{ height: {18*LEAD}pt; position: relative; }}
.opener img {{ position: absolute; top: {34 - MT}pt; left: -8.8pt; right: 0; margin: 0 auto; width: 88.38pt; height: 207.22pt; }}
.opener h2 {{ position: absolute; left: -25pt; right: -25pt; top: {275.7 - MT - 18.1 - 2.7}pt; margin: 0; text-align: center;
             font: 400 24pt/24pt AvantGarde; color: {GOLD_TITLE}; letter-spacing: 1.6pt; }}
.opener .sub {{ position: absolute; left: -45pt; right: -45pt; top: {302 - MT - 7.6 - 1.1}pt; margin: 0; text-align: center;
             font: 400 10pt/10pt AvantGarde; color: {GOLD_SUB}; letter-spacing: 1.1pt; }}
.ackhead {{ break-before: right; }}


.scene {{ height: {9*LEAD}pt; position: relative; break-inside: avoid; }}
.scene img {{ position: absolute; left: 0; right: 0; margin: 0 auto; top: {4*LEAD - 7}pt; width: 16.3pt; height: 30pt; }}
"""


def runs_html(runs):
    out = []
    for t, it in runs:
        s = html.escape(t)
        out.append(f"<i>{s}</i>" if it else s)
    return "".join(out)


parts = []
# ---------------- front matter
parts.append(f"""
<section class="front recto"><div class="title">
  <div class="art"><img src="title_art.svg" alt="Gold Man — A Novel — Lori Hodgkinson"></div>
  <div class="logo"><img src="logo.png"></div>
</div></section>

<section class="front"><div class="copyright"><div>
<p>Copyright © Lori Hodgkinson, 2026</p>
<p>ISBN 978-1-998206-52-0 (<i>paperback</i>)</p>
<p>ISBN 978-1-998206-52-0 (<i>e-book</i>)</p>
<p>First Edition</p>
<div class="gap"></div>
<p>Published by RE:BOOKS Publishing</p>
<p><i>www.rebooks.ca</i></p>
<div class="gap"></div>
<p>All rights reserved. No part of this book may be reproduced in any form or by an electronic or mechanical means, including information storage and retrieval systems, without permission in writing from the publisher, except by a reviewer who may quote brief passages in a review.</p>
<div class="gap"></div>
<p>BOOK TEAM:</p>
<p><b>Publisher:</b> Rebecca Eckler • <b>Managing Editor:</b> Chloe Faith Robinson • <b>Print Production Coordinator:</b> Johannah Manio • <b>Copy Editors:</b> Victoria D’Anna, John Wilson</p>
<div class="gap"></div>
<p><i>Cover design by Chloe Faith Robinson</i></p>
<p><i>Interior design and typesetting by {html.escape(CREDIT)}</i></p>
</div></div></section>

<section class="front recto"><div class="dedication">
<p>For Mom and Dad. Your love and confidence<br>encouraged me to take risks.<br>And to Bob—your vibrant spirit, love, and<br>support will always be my inspiration.</p>
</div></section>

<section class="front recto">
<div class="notehead">AUTHOR’S NOTE</div>
<div style="height:40pt"></div>
<p>The character Pookmis (Wild Man of the Sea) draws from the powerful masks of Kwakw<span class="ul">a</span>k<span class="ul">a</span>’wakw Hereditary Chief and master carver Beau Dick (1955–2017), and from the rich mythology of supernatural beings in British Columbia Indigenous oral traditions.</p>
<p>With the greatest respect, I have taken poetic license in reimagining this figure for the novel. Pookmis in this story is not presented as a traditional teaching or an exact retelling of any specific folklore or dance.</p>
<p>All details, behaviours, and narrative roles are my own inventions.</p>
<p>I thank Indigenous Peoples for sharing their vibrant, inspirational customs and cultures.</p>
</section>

<section class="mappage"><img src="map.jpg"></section>
""")

# ---------------- body
first_after_head = False
for b in doc:
    if b["type"] == "chapter":
        if b.get("ack"):
            parts.append(f'<section class="ackhead"><div class="notehead">{html.escape(b["title"])}</div>'
                         f'<div style="height:40pt"></div></section>')
            # paragraphs follow inside flow; mark first as no-indent
        else:
            sub = f'<div class="sub">{html.escape(b["sub"])}</div>' if b["sub"] else ""
            parts.append(f'<section class="chapter"><div class="opener"><img src="sun.svg"><h2>{html.escape(b["title"])}</h2>{sub}</div></section>')
        first_after_head = True
        continue
    if b["type"] == "scene":
        parts.append('<div class="scene"><img src="orn.svg"></div>')
        first_after_head = True
        continue
    cls = "" if (b["indent"] and not first_after_head) else ' class="ni"'
    letters = [c for t, _ in b["runs"] for c in t if c.isalpha()]
    caps = ' style="hyphens: manual"' if letters and sum(c.isupper() for c in letters) > 0.7 * len(letters) else ""
    parts.append(f"<p{cls}{caps}>{runs_html(b['runs'])}</p>")
    first_after_head = False

page = f"""<!doctype html><html lang="en-US"><head><meta charset="utf-8"><title>Gold Man</title><meta name="author" content="Lori Hodgkinson">
<style>{css}</style></head><body>
{''.join(parts)}
</body></html>"""
open(OUT, "w").write(page)
print("written", OUT, len(page))
