

def uncovered_walls(
    model,
    ds: DetailSheet,
    pens: set,
    widths: list[float],
    covered: list[tuple[tuple[float, float], tuple[float, float], float]],
) -> list[tuple[tuple[float, float], tuple[float, float], float]]:
    """Stretches of double-line wall the takeoff has not covered yet: two
    parallel lines drawn with a wall-face pen (learned from the walls already
    found), a wall width apart. ``covered`` = (a, b, width) of the walls taken
    off. Returns (a, b, width) of each uncovered stretch of at least 2 ft
    (OE-DELIVERY 2026-11-09-colours-keys)."""
    upf = model.units_per_foot or 9.0
    if not pens or not widths or ds.index is None:
        return []
    tol_w = 0.6 / 12.0 * upf
    min_len = 1.0 * upf
    face = [
        j for j, s in enumerate(ds.segs)
        if s[4] >= min_len and (s[6], round(float(s[5] or 0.0), 2)) in pens
    ]
    face_set = set(face)
    wmax = max(widths) + tol_w
    runs: list[tuple[float, float, float, float, float]] = []  # ang, off, lo, hi, width (on the midline)
    for i in face:
        s = ds.segs[i]
        a_s = _ang(s)
        L = s[4]
        ux, uy = (s[2] - s[0]) / L, (s[3] - s[1]) / L
        nx, ny = -uy, ux
        for j in ds.index.near(min(s[0], s[2]) - wmax, min(s[1], s[3]) - wmax, max(s[0], s[2]) + wmax, max(s[1], s[3]) + wmax):
            if j <= i or j not in face_set:
                continue
            t = ds.segs[j]
            if _adiff(_ang(t), a_s) > 2.0:
                continue
            d = (t[0] - s[0]) * nx + (t[1] - s[1]) * ny
            d2 = (t[2] - s[0]) * nx + (t[3] - s[1]) * ny
            if abs(d - d2) > 0.6:
                continue
            w = abs((d + d2) / 2.0)
            if not any(abs(w - ww) <= tol_w for ww in widths):
                continue
            t1 = (t[0] - s[0]) * ux + (t[1] - s[1]) * uy
            t2 = (t[2] - s[0]) * ux + (t[3] - s[1]) * uy
            lo, hi = max(0.0, min(t1, t2)), min(L, max(t1, t2))
            if hi - lo < min_len:
                continue
            mid = (d + d2) / 4.0  # half the offset: the centre line
            # Express on a common axis for the angle: offset of the centre
            # line from the origin, and the run along the axis.
            ang = math.radians(a_s)
            ex, ey = math.cos(ang), math.sin(ang)
            px, py = s[0] + nx * mid, s[1] + ny * mid
            o = -px * ey + py * ex
            p0 = (s[0] + ux * lo) * ex + (s[1] + uy * lo) * ey
            p1 = (s[0] + ux * hi) * ex + (s[1] + uy * hi) * ey
            runs.append((a_s, o, min(p0, p1), max(p0, p1), w))
    if not runs:
        return []
    # Merge runs on the same centre line.
    runs.sort(key=lambda r: (round(r[0]), round(r[1] / 1.5), r[2]))
    merged: list[list[float]] = []
    for r in runs:
        if merged:
            m = merged[-1]
            if _adiff(m[0], r[0]) <= 2.0 and abs(m[1] - r[1]) <= 1.5 and r[2] <= m[3] + 0.5 * upf:
                m[3] = max(m[3], r[3])
                m[4] = max(m[4], r[4])
                continue
        merged.append(list(r))
    out = []
    for ang_d, o, lo, hi, w in merged:
        ang = math.radians(ang_d)
        ex, ey = math.cos(ang), math.sin(ang)
        # Back to points: centre line points at lo / hi.
        def pt(t: float) -> tuple[float, float]:
            return (ex * t - ey * o, ey * t + ex * o)

        # Take away what the walls already found cover.
        cuts: list[tuple[float, float]] = []
        for (ca, cb, cw) in covered:
            dx, dy = cb[0] - ca[0], cb[1] - ca[1]
            cl = math.hypot(dx, dy)
            if cl <= 0:
                continue
            if _adiff(math.degrees(math.atan2(dy, dx)), ang_d) > 3.0:
                continue
            for q in (ca, cb):
                pass
            off_a = -ca[0] * ey + ca[1] * ex
            off_b = -cb[0] * ey + cb[1] * ex
            if abs(off_a - o) > max(cw, w) / 2.0 + 1.0 or abs(off_b - o) > max(cw, w) / 2.0 + 1.0:
                continue
            ta = ca[0] * ex + ca[1] * ey
            tb = cb[0] * ex + cb[1] * ey
            cuts.append((min(ta, tb) - w, max(ta, tb) + w))
        cuts.sort()
        t = lo
        for c0, c1 in cuts:
            if c1 <= t or c0 >= hi:
                continue
            if c0 - t >= 2.0 * upf:
                out.append((pt(t), pt(c0), w))
            t = max(t, c1)
        if hi - t >= 2.0 * upf:
            out.append((pt(t), pt(hi), w))
    return out
