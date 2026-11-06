import sys, collections
sys.path.insert(0, ".")
import pymupdf
from app.modules.takeoff import auto_takeoff as A

SP = r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\54925a2d-b9ef-4c09-b804-543c7d5f479b\scratchpad"
path = r"C:\Users\ishat\Downloads\Pages from 01) StudioRes PCB - Building Drawings.pdf"
pg = int(sys.argv[1])
clip = [float(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
pdf = pymupdf.open(path)
res = A.run_auto_takeoff(pdf, [pg], ["beams", "columns", "joists", "trusses", "walls", "areas", "other"], rules=True)
items = res["pages"][0]["items"]
upf = res["pages"][0]["units_per_foot"]
lens = collections.defaultdict(list)
out = pymupdf.open()
out.insert_pdf(pdf, from_page=pg - 1, to_page=pg - 1)
page = out[0]
COL = {"trusses": (1, 0, 0), "joists": (0, 0.6, 0), "beams": (0, 0, 1), "walls": (0.9, 0.4, 0), "other": (0.7, 0, 0.7), "columns": (0, 0.6, 0.8), "areas": (0.5, 0.5, 0)}
for it in items:
    c = COL.get(it["category"], (0, 0, 0))
    pts = it["points"]
    if it["kind"] == "line":
        page.draw_line(pts[0], pts[1], color=c, width=1.6)
        if upf:
            lens[(it["designation"])].append(round(((pts[1][0]-pts[0][0])**2 + (pts[1][1]-pts[0][1])**2) ** 0.5 / upf, 1))
    elif it["kind"] == "count":
        page.draw_circle(pts[0], 5, color=c, width=1.5)
    elif it["kind"] == "area":
        page.draw_polyline(pts + [pts[0]], color=c, width=0.8, dashes="[4] 0")
for k, v in lens.items():
    print(k, len(v), "lengths ft:", sorted(collections.Counter(v).items(), key=lambda kv: -kv[1])[:6])
r = pymupdf.Rect(*clip) if clip else page.rect
page.get_pixmap(clip=r, dpi=110 if clip else 40).save(SP + rf"\ov_{pg}.png")
