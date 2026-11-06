from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = base / "detail_scan.py"
s = p.read_text(encoding="utf-8")
if "def symbol_at" not in s:
    s += r'''

def symbol_at(ds: DetailSheet, x: float, y: float) -> list[float] | None:
    """Size and turn of the column symbol drawn at (x, y): [long side, short
    side, angle of the long side in degrees] in drawing units - so the
    viewer draws a wide flange or a rectangular tube the way it sits on the
    plan (OE-DELIVERY 2026-11-07-column-shapes)."""
    best = None
    for sh in ds.shapes:
        if not (3.0 <= sh.w <= 40.0) or sh.aspect > 4.0:
            continue
        d = math.hypot(sh.cx - x, sh.cy - y)
        if d > max(3.0, 0.5 * sh.w):
            continue
        # The drawn outline beats a white knock-out under it; the closest
        # centre wins, then the bigger outline (an I drawn round a web).
        mask = sh.filled and not sh.dark_fill and not sh.stroked
        score = (mask, round(d, 1), -sh.w)
        if best is None or score < best[0]:
            best = (score, sh)
    if best is None:
        return None
    sh = best[1]
    return [round(sh.w, 2), round(sh.h, 2), round(sh.angle, 1)]
'''
    p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")
a = '''                "confidence": 0.6 if c.get("zoom") else 0.7,
                "source": "zoom" if c.get("zoom") else "rules",
            })'''
b = '''                "confidence": 0.6 if c.get("zoom") else 0.7,
                "source": "zoom" if c.get("zoom") else "rules",
                # Symbol size and turn on the sheet (OE-DELIVERY 2026-11-07-column-shapes).
                "symbol": _column_symbol(model, x, y),
            })'''
assert s.count(a) == 1
s = s.replace(a, b)
a = '''def _detail_leader_ends(model: PageModel):'''
b = '''def _column_symbol(model: PageModel, x: float, y: float) -> list[float] | None:
    if model.detail is None:
        return None
    try:
        from app.modules.takeoff import detail_scan as Z

        return Z.symbol_at(model.detail, x, y)
    except Exception:
        return None


def _detail_leader_ends(model: PageModel):'''
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
