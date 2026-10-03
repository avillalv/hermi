from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from pathlib import Path
import os, tempfile

HERE = Path(__file__).resolve().parent
OUT = str(HERE) + "/"
# Colors (BRAND.md "Geometry" and "Colors"; keep in sync with 05-ui-ux-spec.md section 2).
SKY = "#2AA5FF"; PINK = "#FF5E7E"; YELLOW = "#FFCB2E"; CREAM = "#FFF8EC"
INK = "#17324A"; INK_DARK = "#E6F2FF"; PAPER = "#FBF5EA"; NIGHT = "#0B1A2A"
PLANE = "M50 2C54 2 57 10 57 18L57 36L96 63L96 70L57 58L56 78L75 89L75 95L54 90L52 98L48 98L46 90L25 95L25 89L44 78L43 58L4 70L4 63L43 36L43 18C43 10 46 2 50 2Z"

def wordmark(text, font_path, size, tracking=0.0):
    f=TTFont(font_path); gs=f.getGlyphSet(); cmap=f.getBestCmap(); upm=f['head'].unitsPerEm
    s=size/upm; x=0; paths=[]
    hmtx=f['hmtx']
    for ch in text:
        g=cmap[ord(ch)]
        pen=SVGPathPen(gs)
        tp=TransformPen(pen,(s,0,0,-s,x,0))
        gs[g].draw(tp); paths.append(pen.getCommands())
        x+=hmtx[g][0]*s+tracking*size
    cap=f['OS/2'].sCapHeight*s
    return " ".join(paths), x-tracking*size, cap

def mark(rounded=False):
    # 1024 grid. Two dotted routes (pink left, yellow right) are the posts of an H;
    # a cream plane flies the crossbar between them.
    rx=' rx="228"' if rounded else ''
    dots=[]
    for x, c in ((236, PINK), (788, YELLOW)):
        for y in range(192, 693, 100):
            dots.append(f'<circle cx="{x}" cy="{y}" r="46" fill="{c}"/>')
        dots.append(f'<circle cx="{x}" cy="809" r="70" fill="{c}"/>')
    links=''.join(f'<circle cx="{x}" cy="500" r="22" fill="{CREAM}"/>' for x in (328, 696))
    plane=(f'<path transform="translate(512 500) rotate(90) scale(3) translate(-50 -50)" d="{PLANE}" '
           f'fill="{CREAM}" stroke="{CREAM}" stroke-width="3" stroke-linejoin="round"/>')
    return f'<rect width="1024" height="1024"{rx} fill="{SKY}"/>' + ''.join(dots) + links + plane

def write(name, w, h, body, title):
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
         f'role="img" aria-label="{title}">\n  <title>{title}</title>\n  {body}\n</svg>\n')
    (HERE/name).write_bytes(svg.encode())  # bytes: write_text would write CRLF on Windows

write("hermi-app-icon.svg",1024,1024,mark(),"Hermi app icon")
write("hermi-mark.svg",1024,1024,mark(rounded=True),"Hermi")

fp=os.environ.get("FREDOKA_600", "package/files/fredoka-latin-600-normal.woff")  # from: npm pack @fontsource/fredoka
TRACK=0.0
d,wid,cap=wordmark("Hermi",fp,300,TRACK)
MS=0.42     # mark scale in the lockup (mark is 430 px)
PAD=90      # outer padding
GAP=64      # mark to wordmark
def lockup(dark):
    ink = INK_DARK if dark else INK
    bgc = NIGHT if dark else PAPER
    msize=1024*MS
    H=int(msize+2*PAD)
    base=PAD+msize/2+cap/2   # cap height centered on the mark's horizontal axis
    W=int(PAD+msize+GAP+wid+PAD)
    body=(f'<rect width="{W}" height="{H}" fill="{bgc}"/>\n  '
          f'<g transform="translate({PAD} {PAD}) scale({MS})">{mark(rounded=True)}</g>\n  '
          f'<path transform="translate({PAD+msize+GAP:.1f} {base:.1f})" fill="{ink}" d="{d}"/>')
    return W,H,body
W,H,b=lockup(False); write("hermi-logo.svg",W,H,b,"Hermi")
W,H,b=lockup(True); write("hermi-logo-dark.svg",W,H,b,"Hermi")
d2,wid2,cap2=wordmark("Hermi",fp,200,TRACK)
write("hermi-wordmark.svg",int(wid2+8),int(cap2*1.5),f'<path transform="translate(4 {cap2*1.25:.1f})" fill="{INK}" d="{d2}"/>',"Hermi")

# Review page for the preview PNG. Written outside the repo (PREVIEW_HTML, default: system temp).
def uri(n): return (HERE/n).as_uri()
WM_W=300; WM_DROP=cap2*0.25*WM_W/(wid2+8)  # drop the wordmark so its baseline sits on the row's bottom edge
html=f'''<!doctype html><meta charset="utf-8"><style>
body{{margin:0;padding:24px;width:760px;background:#fff;font:14px sans-serif}}
img{{display:block}} .row{{display:flex;align-items:flex-end;gap:24px;margin-top:12px}}
.light,.dark{{margin-top:12px}} .light img,.dark img{{width:760px}}
</style>
<div class="light"><img src="{uri('hermi-logo.svg')}"></div>
<div class="dark"><img src="{uri('hermi-logo-dark.svg')}"></div>
<div class="row">
  <img src="{uri('hermi-mark.svg')}" width="240" height="240">
  <img src="{uri('hermi-mark.svg')}" width="60" height="60">
  <img src="{uri('hermi-mark.svg')}" width="29" height="29">
  <img src="{uri('hermi-wordmark.svg')}" width="{WM_W}" style="margin:0 0 -{WM_DROP:.0f}px 16px">
</div>'''
page=Path(os.environ.get("PREVIEW_HTML", Path(tempfile.gettempdir())/"hermi-logo-preview.html"))
page.write_bytes(html.encode())
print("ok", round(wid), round(cap), "preview page:", page)
