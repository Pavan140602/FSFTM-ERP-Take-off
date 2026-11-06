from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
a = """        ends: list[tuple[float, float]] = []
        if leader_ends is not None:
            try:
                ends.extend(list(leader_ends(lab))[:4])
            except Exception:
                pass
        ends.extend(_underline_ends(lab, ds))
        # Already has its column (at a leader end, or touching the text).
        def near_label(x: float, y: float) -> float:
            dx = max(lab.rect[0] - x, 0.0, x - lab.rect[2])
            dy = max(lab.rect[1] - y, 0.0, y - lab.rect[3])
            return math.hypot(dx, dy)
        if any(near_label(x, y) <= 14 or any(math.hypot(x - ex, y - ey) <= 14 for ex, ey in ends) for x, y in taken):
            continue
        checked += 1
        best = None
        for ex, ey in ends:"""
b = """        # Where the callout points: the line it is written on first, then
        # its leader(s).
        ends: list[tuple[float, float, float]] = [(x, y, 0.0) for x, y in _underline_ends(lab, ds)]
        if leader_ends is not None:
            try:
                ends.extend((x, y, 2.0) for x, y in list(leader_ends(lab))[:4])
            except Exception:
                pass
        checked += 1
        best = None
        for ex, ey, pen in ends:"""
assert s.count(a) == 1
s = s.replace(a, b)
a = """                d = math.hypot(sh.cx - ex, sh.cy - ey) - sh.w / 2.0
                if d > reach_tip:
                    continue
                if any(_overlap(sh.bbox, w) for w in ds.words):
                    continue
                if best is None or d < best[0]:
                    best = (d, sh)"""
b = """                d = math.hypot(sh.cx - ex, sh.cy - ey) - sh.w / 2.0
                if d > reach_tip:
                    continue
                if any(_overlap(sh.bbox, w) for w in ds.words):
                    continue
                if best is None or d + pen < best[0]:
                    best = (d + pen, sh)"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('ok')
