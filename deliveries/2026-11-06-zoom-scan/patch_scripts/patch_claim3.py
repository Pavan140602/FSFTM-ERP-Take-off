from pathlib import Path
base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = base / "detail_scan.py"
s = p.read_text(encoding="utf-8")
a = """                    for ex, ey, pn in ends
                    if pn == 0.0
                ),
                default=None,
            )"""
b = """                    for ex, ey, pn in ends
                ),
                default=None,
            )"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")
a = """            if cat == "beams" and info.get("series"):
                continue"""
b = """            if cat == "beams" and info.get("series"):
                continue
            if cat == "beams" and re.match(r"^(HSS(\d+(?:\.\d+)?)X\2X|W\d+X)", re.sub(r"\s+", "", lab.text.upper())) and any(
                it.get("category") == "columns" and any(math.hypot(q[0] - lab.cx, q[1] - lab.cy) <= near for q in it.get("points") or [])
                for it in items
            ):
                continue  # a column size whose column is right there"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
