from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = base / "detail_scan.py"
s = p.read_text(encoding="utf-8")
if "def leader_beams" not in s:
    s += '''

def leader_beams(model, ds: DetailSheet, items: list[dict[str, Any]], cols: list[tuple[float, float]]) -> set[int]:
    """Beam markups that are really a callout's leader: drawn on a thin line
    (not the beam pen), short, and ending at a column. Returns their indexes
    in ``items``."""
    if ds.index is None:
        return set()
    upf = model.units_per_foot or 9.0
    heavy_w = _heavy_width(ds)
    drop: set[int] = set()
    for i, it in enumerate(items):
        if it.get("category") != "beams" or it.get("kind") != "line" or it.get("source") == "zoom":
            continue
        pts = it.get("points") or []
        if len(pts) != 2:
            continue
        (x1, y1), (x2, y2) = pts
        L = math.hypot(x2 - x1, y2 - y1)
        if L > 6.0 * upf or L < 1.0:
            continue
        if not any(min(math.hypot(x1 - cx, y1 - cy), math.hypot(x2 - cx, y2 - cy)) <= 14.0 for cx, cy in cols):
            continue
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        ang = (math.degrees(math.atan2(y2 - y1, x2 - x1)) + 90.0) % 180.0 - 90.0
        widths = [
            float(ds.segs[j][5] or 0.0)
            for j in ds.index.near(mx - 2, my - 2, mx + 2, my + 2)
            if _pt_seg(mx, my, ds.segs[j]) <= 1.5 and _adiff(_ang(ds.segs[j]), ang) <= 5.0
        ]
        if widths and max(widths) < heavy_w:
            drop.add(i)
    return drop
'''
    p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")
a = """            if zoom_stats is None:
                zoom_stats = {}
            zoom_stats["beams"] = beam_stats"""
b = """            # First-pass "beams" that are really a column callout's leader.
            drop = Z.leader_beams(model, model.detail, items, [tuple(c["point"]) for c in col_found])
            if drop:
                items[:] = [it for k, it in enumerate(items) if k not in drop]
            beam_stats["leaders_removed"] = len(drop)
            if zoom_stats is None:
                zoom_stats = {}
            zoom_stats["beams"] = beam_stats"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
