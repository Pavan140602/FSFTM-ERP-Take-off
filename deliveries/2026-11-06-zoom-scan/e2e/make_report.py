"""Final takeoff report: run Auto Takeoff (zoom parts on) on test sheets,
render each sheet with its parts grid and markups, and write the data."""
import sys, json, math, base64, io, collections
sys.path.insert(0, '.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A, detail_scan as Z

OUT = r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\732e120e-2b91-4dfc-bda2-2925a51afa1e\scratchpad\report"
import os
os.makedirs(OUT, exist_ok=True)

D = r"C:\Users\ishat\Downloads"
SHEETS = [
    ("AC Retreat by Marriott", D + r"\2026-11-02_AC RETREAT, BY MARIOTT_STR_V25.pdf", 18, False, "S2.01b", "2nd floor framing, part B (curved entry)"),
    ("AC Retreat by Marriott", D + r"\2026-11-02_AC RETREAT, BY MARIOTT_STR_V25.pdf", 23, False, "S4.01a", "4th floor framing, part A"),
    ("AC Retreat by Marriott", D + r"\2026-11-02_AC RETREAT, BY MARIOTT_STR_V25.pdf", 20, False, "S3.01a", "3rd floor framing, part A"),
    ("StudioRes by Marriott", D + r"\Pages from 01) StudioRes PCB - Building Drawings.pdf", 3, True, "S200", "Foundation plan (house rules)"),
    ("StudioRes by Marriott", D + r"\Pages from 01) StudioRes PCB - Building Drawings.pdf", 5, True, "S202", "3rd floor framing (house rules)"),
    ("Home2 Suites Mobile", D + r"\2026-10-14_25090 Mobile Home2Suites _STR_V25.pdf", 3, False, "S-1.00", "Foundation plan"),
    ("Home2 Suites Mobile", D + r"\2026-10-14_25090 Mobile Home2Suites _STR_V25.pdf", 16, False, "S-6.02", "Roof framing plan"),
]
COL = {"columns": (0.05, 0.62, 0.32), "beams": (0.80, 0.10, 0.55), "joists": (0.12, 0.42, 0.85), "trusses": (0.12, 0.42, 0.85),
       "areas": (0.95, 0.60, 0.05), "walls": (0.45, 0.30, 0.75), "other": (0.45, 0.45, 0.45)}


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def parea(pts):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


docs = {}
report = []
for proj, path, pno, rules, num, title in SHEETS:
    pdf = docs.setdefault(path, pymupdf.open(path))
    res = A.run_auto_takeoff(pdf, [pno], list(A.CATEGORIES), rules=rules)
    pg = res["pages"][0]
    off = A.run_auto_takeoff(pdf, [pno], list(A.CATEGORIES), rules=rules, detail_scan=False)["pages"][0]
    upf = pg.get("units_per_foot") or 9.0
    page = pdf[pno - 1]
    model = A.build_page_model(page, pno)
    parts = Z.plan_parts(model, 0)
    items = pg["items"]
    # Draw. Points are in display space; page rotation 0 on these sheets.
    sh = page.new_shape()
    for part in parts:
        z = part["core"]
        x0, y0, x1, y1 = max(z[0], 0), max(z[1], 0), min(z[2], page.rect.width), min(z[3], page.rect.height)
        sh.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
        sh.finish(color=(0.15, 0.35, 0.9), width=2.2, dashes="[14 8] 0", stroke_opacity=0.55, fill=None)
    sh.commit()
    for part in parts:
        z = part["zoom"]
        page.insert_text(pymupdf.Point(z[0] + 10, z[1] + 34), f"PART {part['id']}", fontsize=26, color=(0.15, 0.35, 0.9), fill_opacity=0.6)
    sh = page.new_shape()
    for it in items:
        c = COL.get(it["category"], (0.4, 0.4, 0.4))
        zoom = it.get("source") == "zoom"
        pts = [pymupdf.Point(p[0], p[1]) for p in it["points"]]
        if it["kind"] == "count":
            for q in pts:
                sh.draw_circle(q, 10 if zoom else 8)
                sh.finish(color=c, width=3.2 if zoom else 2.2, fill=None)
        elif it["kind"] == "area":
            sh.draw_polyline(pts + [pts[0]])
            sh.finish(color=c, width=2, fill=c, fill_opacity=0.18, stroke_opacity=0.8)
        else:
            sh.draw_polyline(pts)
            sh.finish(color=c, width=3.4 if zoom else 2.0, stroke_opacity=0.85, closePath=False, dashes="[10 5] 0" if (zoom and it["designation"] == "BEAM") else None)
    sh.commit()
    clip = pymupdf.Rect(0, 0, page.rect.width * 0.905, page.rect.height)
    zoomf = 1500 / clip.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoomf, zoomf), clip=clip)
    jpg = pix.tobytes("jpeg", jpg_quality=72)
    # Quantities.
    rows = collections.OrderedDict()
    for it in items:
        key = (it["category"], it.get("role") or "", it["designation"])
        r = rows.setdefault(key, {"category": it["category"], "role": it.get("role") or "", "designation": it["designation"], "count": 0, "lf": 0.0, "sf": 0.0, "zoom": 0})
        n = len(it["points"]) if it["kind"] == "count" else 1
        r["count"] += n
        if it["kind"] == "line":
            r["lf"] += plen(it["points"]) / upf
        if it["kind"] == "area":
            r["sf"] += parea(it["points"]) / (upf * upf)
        if it.get("source") == "zoom":
            r["zoom"] += n
    zs = pg.get("zoom_scan") or {}
    report.append({
        "project": proj, "sheet": num, "title": title, "page": pno, "rules": rules,
        "scale": pg.get("scale"), "grid": zs.get("grid"), "parts": zs.get("parts"),
        "img": base64.b64encode(jpg).decode(), "w": pix.width, "h": pix.height,
        "rows": sorted(rows.values(), key=lambda r: (["columns", "beams", "joists", "trusses", "areas", "walls", "other"].index(r["category"]) if r["category"] in COL else 9, r["designation"])),
        "counts": pg["counts"], "counts_before": off["counts"],
        "missed": [{"designation": m["designation"], "category": m["category"]} for m in pg.get("missed") or []],
        "log": zs.get("log") or [],
        "removed": zs.get("removed", 0),
    })
    print(num, pg["counts"], "before", off["counts"], "parts", zs.get("grid"), "missed", len(pg.get("missed") or []), len(jpg) // 1024, "KB")
json.dump(report, open(os.path.join(OUT, "report.json"), "w"))
