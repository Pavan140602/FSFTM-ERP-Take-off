from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding="utf-8")
a = """        widths = [
            float(ds.segs[j][5] or 0.0)
            for j in ds.index.near(mx - 8, my - 8, mx + 8, my + 8)
            if _pt_seg(mx, my, ds.segs[j]) <= 7.0 and _adiff(_ang(ds.segs[j]), ang) <= 5.0
        ]
        if widths and max(widths) < heavy_w:
            drop.add(i)"""
b = """        widths = []
        for t in (0.2, 0.35, 0.5, 0.65, 0.8):  # dashed beams: look along it
            sx, sy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            widths.extend(
                float(ds.segs[j][5] or 0.0)
                for j in ds.index.near(sx - 8, sy - 8, sx + 8, sy + 8)
                if _pt_seg(sx, sy, ds.segs[j]) <= 7.0 and _adiff(_ang(ds.segs[j]), ang) <= 5.0
            )
        if widths and max(widths) < heavy_w:
            drop.add(i)"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
