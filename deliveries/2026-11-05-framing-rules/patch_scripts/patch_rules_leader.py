# OE-DELIVERY 2026-11-05-framing-rules: frame trusses / joists from a tag whose leader
# points at the crossing of the bay's distribution arrow and span line.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])
A = ROOT / "backend/app/modules/takeoff/auto_takeoff.py"
FRP = ROOT / "backend/app/modules/takeoff/framing_rules.py"
s = A.read_text(encoding="utf-8")
fr = FRP.read_text(encoding="utf-8")


def rep(old, new, where="A"):
    global s, fr
    src = s if where == "A" else fr
    if src.count(old) != 1:
        print("ANCHOR FAIL", where, src.count(old), old[:120])
        sys.exit(1)
    if where == "A":
        s = src.replace(old, new)
    else:
        fr = src.replace(old, new)


FUNC = '''

def _series_from_leader(
    label: Label, info: dict[str, Any], model: PageModel
) -> tuple[list[tuple[float, float, float, float]], bool, list[tuple[float, float]] | None] | None:
    """Bay framed from a tag with a leader (framing rules).

    House framing plans print 'T-1' / 'RJ-1' beside the bay with a leader to
    the crossing of two lines: the distribution arrow (wall to wall, across
    the members) and the span line (along the members). Members are placed
    at the schedule spacing across the whole distribution, each as long as
    the span line. The span line is the one closer to the schedule length
    (the longer one when there is none).
    """
    assert model.index is not None
    upf = model.units_per_foot
    if not upf or not info.get("spacing_in"):
        return None
    spacing_units = info["spacing_in"] / 12.0 * upf
    cx, cy = label.cx, label.cy
    half = math.hypot(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) / 2.0
    near_r = half + 1.2 * label.size
    best: tuple[float, tuple[float, float, float, float], tuple[float, float, float, float]] | None = None
    for i in model.index.near(cx - near_r - 120, cy - near_r - 120, cx + near_r + 120, cy + near_r + 120):
        ld = model.segments[i]
        if not (6 <= ld[4] <= 140):
            continue
        d0 = math.hypot(ld[0] - cx, ld[1] - cy)
        d1 = math.hypot(ld[2] - cx, ld[3] - cy)
        if min(d0, d1) > near_r or max(d0, d1) < near_r * 0.8:
            continue
        fx, fy = (ld[2], ld[3]) if d1 > d0 else (ld[0], ld[1])
        lines_at: list[tuple[float, float, float, float]] = []
        for j in model.index.near(fx - 3, fy - 3, fx + 3, fy + 3):
            w = model.segments[j]
            if w is ld or w[4] < 20 or _angle_diff(_seg_angle(w), _seg_angle(ld)) < 15:
                continue
            if _pt_seg_dist(fx, fy, w) > 2.5:
                continue
            run = merge_run(w, model, max_gap=3.0)
            if math.hypot(run[2] - run[0], run[3] - run[1]) < 3 * spacing_units * 0.5:
                continue
            if any(_angle_diff(_fold(math.degrees(math.atan2(run[3] - run[1], run[2] - run[0]))),
                               _fold(math.degrees(math.atan2(o[3] - o[1], o[2] - o[0])))) < 5 for o in lines_at):
                continue
            lines_at.append(run)
        if len(lines_at) < 2:
            continue
        # Two lines at right angles through the leader tip.
        pair = None
        for a_i in range(len(lines_at)):
            for b_i in range(a_i + 1, len(lines_at)):
                a, b = lines_at[a_i], lines_at[b_i]
                ang_a = math.degrees(math.atan2(a[3] - a[1], a[2] - a[0]))
                ang_b = math.degrees(math.atan2(b[3] - b[1], b[2] - b[0]))
                if _angle_diff(_fold(ang_a), _fold(ang_b)) >= 80:
                    pair = (a, b)
                    break
            if pair:
                break
        if not pair:
            continue
        score = max(d0, d1)
        if best is None or score < best[0]:
            best = (score, pair[0], pair[1])
    if best is None:
        return None
    a, b = best[1], best[2]
    la = math.hypot(a[2] - a[0], a[3] - a[1])
    lb = math.hypot(b[2] - b[0], b[3] - b[1])
    want_ft = info.get("length_ft")
    if want_ft:
        span, dist = (a, b) if abs(la / upf - want_ft) <= abs(lb / upf - want_ft) else (b, a)
    else:
        span, dist = (a, b) if la >= lb else (b, a)
    d_len = math.hypot(dist[2] - dist[0], dist[3] - dist[1])
    if d_len < spacing_units * 0.9:
        return None
    dx, dy = (dist[2] - dist[0]) / d_len, (dist[3] - dist[1]) / d_len
    s_len = math.hypot(span[2] - span[0], span[3] - span[1])
    jx, jy = (span[2] - span[0]) / s_len, (span[3] - span[1]) / s_len
    d_lo = dx * dist[0] + dy * dist[1]
    d_hi = dx * dist[2] + dy * dist[3]
    s_lo = jx * span[0] + jy * span[1]
    s_hi = jx * span[2] + jy * span[3]
    # Coordinates: point = dx*d + jx*s (the two axes are perpendicular).
    width = d_hi - d_lo
    count = int(math.floor(width / spacing_units + 1e-6)) + 1
    start = d_lo + (width - (count - 1) * spacing_units) / 2.0
    out: list[tuple[float, float, float, float]] = []
    for k in range(count):
        off = start + k * spacing_units
        out.append((dx * off + jx * s_lo, dy * off + jy * s_lo, dx * off + jx * s_hi, dy * off + jy * s_hi))
    return out, True, _bay_poly(jx, jy, dx, dy, s_lo, s_hi, d_lo, d_hi)


def _bay_poly(ux, uy, nx, ny, s_lo, s_hi, n_lo, n_hi) -> list[tuple[float, float]]:'''

rep('''

def _bay_poly(ux, uy, nx, ny, s_lo, s_hi, n_lo, n_hi) -> list[tuple[float, float]]:''', FUNC)

rep('''            if not info.get("series"):
                continue
            lines, generated, bay = _series_lines(lab, info, model)''', '''            if not info.get("series"):
                continue
            via_leader = _series_from_leader(lab, info, model) if (rule_on and "rule_profile" in info) else None
            lines, generated, bay = via_leader if via_leader else _series_lines(lab, info, model)''')

# rule infos carry the schedule length (picks the span line)
rep('''            return {"category": "trusses", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "role": "Roof Truss" if m.group(1) == "RT" else "Floor Truss", "rule_profile": (e or {}).get("framing"),''',
    '''            return {"category": "trusses", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "length_ft": feet_inches((e or {}).get("length") or ""),
                    "role": "Roof Truss" if m.group(1) == "RT" else "Floor Truss", "rule_profile": (e or {}).get("framing"),''', "F")
rep('''            return {"category": "joists", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "role": "CFS Joist", "rule_profile": (e or {}).get("framing"),''',
    '''            return {"category": "joists", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "length_ft": feet_inches((e or {}).get("length") or ""),
                    "role": "Roof Joist" if m.group(1) == "RJ" else "CFS Joist", "rule_profile": (e or {}).get("framing"),''', "F")

A.write_text(s, encoding="utf-8")
FRP.write_text(fr, encoding="utf-8")
print("ok")
