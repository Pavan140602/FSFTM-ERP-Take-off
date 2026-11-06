# OE-DELIVERY 2026-11-05-framing-rules: distribution runs wall face to wall face; members
# run onto the bearing walls (to the wall's far face).
from pathlib import Path
import sys

A = Path(sys.argv[1]) / "backend/app/modules/takeoff/auto_takeoff.py"
s = A.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if s.count(old) != 1:
        print("ANCHOR FAIL", s.count(old), old[:120])
        sys.exit(1)
    s = s.replace(old, new)


rep('''    d_len = math.hypot(dist[2] - dist[0], dist[3] - dist[1])
    if d_len < spacing_units * 0.9:
        return None
    dx, dy = (dist[2] - dist[0]) / d_len, (dist[3] - dist[1]) / d_len
    s_len = math.hypot(span[2] - span[0], span[3] - span[1])
    jx, jy = (span[2] - span[0]) / s_len, (span[3] - span[1]) / s_len
    d_lo = dx * dist[0] + dy * dist[1]
    d_hi = dx * dist[2] + dy * dist[3]
    s_lo = jx * span[0] + jy * span[1]
    s_hi = jx * span[2] + jy * span[3]''', '''    d_len = math.hypot(dist[2] - dist[0], dist[3] - dist[1])
    if d_len < spacing_units * 0.9:
        return None
    dx, dy = (dist[2] - dist[0]) / d_len, (dist[3] - dist[1]) / d_len
    s_len = math.hypot(span[2] - span[0], span[3] - span[1])
    jx, jy = (span[2] - span[0]) / s_len, (span[3] - span[1]) / s_len
    d_lo = dx * dist[0] + dy * dist[1]
    d_hi = dx * dist[2] + dy * dist[3]
    s_lo = jx * span[0] + jy * span[1]
    s_hi = jx * span[2] + jy * span[3]
    # The arrows stop at (or just short of) the walls: the distribution runs
    # to the wall faces either side; the members run onto their bearing
    # walls (to the far face).
    span_ang = _fold(math.degrees(math.atan2(jy, jx)))
    dist_ang = _fold(math.degrees(math.atan2(dy, dx)))
    near = 1.5 * upf
    wall_w = 1.0 * upf

    def _face(px: float, py: float, ux: float, uy: float, par_ang: float, far: bool) -> float:
        acc = lambda sg: sg[4] >= 6 and not is_light(sg) and _angle_diff(_seg_angle(sg), par_ang) <= 6  # noqa: E731
        bx, by = px - ux * 3.0, py - uy * 3.0
        t = _cast(model, bx, by, ux, uy, near + 3.0, acc)
        if t is None:
            return 0.0
        ext = t - 3.0
        if far:
            fx, fy = bx + ux * t, by + uy * t
            t2 = _cast(model, fx, fy, ux, uy, wall_w, acc)
            if t2 is not None:
                ext += t2
        return max(ext, -3.0)

    m_lo = (dist[0], dist[1]) if (dx * dist[0] + dy * dist[1]) <= (dx * dist[2] + dy * dist[3]) else (dist[2], dist[3])
    m_hi = (dist[2], dist[3]) if m_lo == (dist[0], dist[1]) else (dist[0], dist[1])
    d_lo -= _face(m_lo[0], m_lo[1], -dx, -dy, span_ang, False)
    d_hi += _face(m_hi[0], m_hi[1], dx, dy, span_ang, False)
    p_lo = (span[0], span[1]) if (jx * span[0] + jy * span[1]) <= (jx * span[2] + jy * span[3]) else (span[2], span[3])
    p_hi = (span[2], span[3]) if p_lo == (span[0], span[1]) else (span[0], span[1])
    s_lo -= _face(p_lo[0], p_lo[1], -jx, -jy, dist_ang, True)
    s_hi += _face(p_hi[0], p_hi[1], jx, jy, dist_ang, True)''')
A.write_text(s, encoding="utf-8")
print("ok")
