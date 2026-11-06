from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep("""        k = int(round(off / 0.6))
        f = faces.setdefault(k, [off, 0.0, [], 0.0])
        f[2].append((lo, hi))
        f[1] += hi - lo
        f[3] = max(f[3], float(s[5] or 0.0))""", """        k = int(round(off / 0.6))
        f = faces.setdefault(k, [off, 0.0, [], 0.0])
        f[2].append((lo, hi, float(s[5] or 0.0)))
        f[1] += hi - lo
        f[3] = max(f[3], float(s[5] or 0.0))""")
rep("""    # Openings: where neither face is drawn with the wall's own (heavy) pen.
    pen_w = min(fa[3], fb[3])
    spans: list[tuple[float, float]] = []
    for k, f in faces.items():
        if abs(f[0] - fa[0]) <= 0.7 or abs(f[0] - fb[0]) <= 0.7:
            if f[3] >= max(heavy_w * 0.8, pen_w * 0.6):
                spans.extend(f[2])
    spans.sort()""", """    # Openings: where neither face is drawn with the wall's own pen - only
    # hairlines (window / door lines, background) run across an opening.
    face_segs = [
        seg
        for f in faces.values()
        if abs(f[0] - fa[0]) <= 0.7 or abs(f[0] - fb[0]) <= 0.7
        for seg in f[2]
    ]
    hair = min((w for _lo, _hi, w in face_segs), default=0.0)
    wall_pen = max(0.6 * heavy_w, 1.2 * hair + 1e-6)
    spans: list[tuple[float, float]] = sorted((lo, hi) for lo, hi, w in face_segs if w >= wall_pen)""")
p.write_text(s, encoding="utf-8")
print("ok")
