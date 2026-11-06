# OE-DELIVERY 2026-11-05-framing-rules: wall-type tags measure their wall from the
# intersecting wall on one side to the one on the other (centrelines), bridging openings.
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


# 1. _wall_beside -> seed finder + wrapper
rep('''def _wall_beside(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Double-line wall a wall-type tag sits beside (framing rules): the
    nearest wall face the tag projects onto that has a parallel face 2-10
    units away; heavier lines first (grid lines are thin)."""
    assert model.index is not None''', '''def _wall_beside(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Double-line wall a wall-type tag sits beside (framing rules)."""
    seed = _wall_seed_beside(label, model)
    return _wall_from_seed(seed, model, True) if seed is not None else None


def _has_partner(sg: Seg, model: PageModel, lo: float = 2.0, hi: float = 10.0) -> bool:
    """A parallel face ``lo``..``hi`` units away (a double-line wall)."""
    assert model.index is not None
    ux, uy = (sg[2] - sg[0]) / sg[4], (sg[3] - sg[1]) / sg[4]
    for j in model.index.near(min(sg[0], sg[2]) - hi - 1, min(sg[1], sg[3]) - hi - 1, max(sg[0], sg[2]) + hi + 1, max(sg[1], sg[3]) + hi + 1):
        o = model.segments[j]
        if o is sg or o[4] < 20 or _angle_diff(_seg_angle(o), _seg_angle(sg)) > 2:
            continue
        off = abs(((o[0] + o[2]) / 2.0 - sg[0]) * -uy + ((o[1] + o[3]) / 2.0 - sg[1]) * ux)
        if lo <= off <= hi:
            a = (o[0] - sg[0]) * ux + (o[1] - sg[1]) * uy
            b = (o[2] - sg[0]) * ux + (o[3] - sg[1]) * uy
            if min(max(a, b), sg[4]) - max(min(a, b), 0.0) > 0.3 * min(o[4], sg[4]):
                return True
    return False


def wall_between_walls(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Wall a wall-type tag names, the way an estimator measures it: along
    the wall beside the tag, from the centre of the intersecting wall on one
    side to the centre of the one on the other side. Window / door gaps in
    the wall are bridged; a gap with a wall across it (a corridor) is not."""
    assert model.index is not None
    seed = _wall_seed_beside(label, model)
    if seed is None:
        return None
    upf = model.units_per_foot or 9.0
    ux, uy = (seed[2] - seed[0]) / seed[4], (seed[3] - seed[1]) / seed[4]
    nx, ny = -uy, ux
    ox, oy = seed[0], seed[1]
    ang = _seg_angle(seed)

    def along(x: float, y: float) -> float:
        return (x - ox) * ux + (y - oy) * uy

    def across(x: float, y: float) -> float:
        return (x - ox) * nx + (y - oy) * ny

    # Face of the wall on the other side (for the centre line).
    centre_shift = 0.0
    for j in model.index.near(min(seed[0], seed[2]) - 11, min(seed[1], seed[3]) - 11, max(seed[0], seed[2]) + 11, max(seed[1], seed[3]) + 11):
        o = model.segments[j]
        if o is seed or o[4] < 20 or _angle_diff(_seg_angle(o), ang) > 2:
            continue
        off = across((o[0] + o[2]) / 2.0, (o[1] + o[3]) / 2.0)
        if 2.0 <= abs(off) <= 10.0:
            centre_shift = off / 2.0
            break
    t0 = along(label.cx, label.cy)
    reach = 70.0 * upf
    band = 14.0
    # Wall face pieces along the line (both faces), and walls across it.
    cover: list[tuple[float, float]] = []
    stops: list[float] = []
    x0 = min(ox + ux * (t0 - reach), ox + ux * (t0 + reach)) - band
    x1 = max(ox + ux * (t0 - reach), ox + ux * (t0 + reach)) + band
    y0 = min(oy + uy * (t0 - reach), oy + uy * (t0 + reach)) - band
    y1 = max(oy + uy * (t0 - reach), oy + uy * (t0 + reach)) + band
    for j in model.index.near(x0, y0, x1, y1):
        o = model.segments[j]
        if o[4] < 6 or is_light(o):
            continue
        d_ang = _angle_diff(_seg_angle(o), ang)
        a, b = along(o[0], o[1]), along(o[2], o[3])
        na, nb = across(o[0], o[1]), across(o[2], o[3])
        if d_ang <= 1.5:
            if max(abs(na), abs(nb)) <= abs(centre_shift) * 2 + 1.5 and (abs(na - 0) <= 1.5 or abs(na - 2 * centre_shift) <= 1.5):
                cover.append((min(a, b), max(a, b)))
        elif d_ang >= 80 and o[4] >= 20:
            # Reaches the wall line (touches or crosses it) and is a wall.
            lo_n, hi_n = min(na, nb), max(na, nb)
            if lo_n <= centre_shift + band and hi_n >= centre_shift - band and _has_partner(o, model):
                stops.append((a + b) / 2.0)
    if not cover:
        return None
    # Pair the faces of each crossing wall into one centre.
    stops.sort()
    centres: list[float] = []
    group: list[float] = []
    for st in stops:
        if group and st - group[-1] > 11.0:
            centres.append(sum(group) / len(group))
            group = []
        group.append(st)
    if group:
        centres.append(sum(group) / len(group))
    left = [c for c in centres if c < t0 - 2.0]
    right = [c for c in centres if c > t0 + 2.0]
    cover.sort()
    # Stretch of wall around the tag: covered pieces joined across gaps
    # (openings) that no crossing wall interrupts.
    merged: list[list[float]] = []
    for a, b in cover:
        if merged and a <= merged[-1][1] + 1.0:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    lo_cov = min(m[0] for m in merged)
    hi_cov = max(m[1] for m in merged)
    lo = max(left) if left else lo_cov
    hi = min(right) if right else hi_cov
    lo = max(lo, lo_cov - 12.0)
    hi = min(hi, hi_cov + 12.0)
    # The wall must really run there: enough of [lo, hi] drawn as wall.
    drawn = sum(max(0.0, min(m[1], hi) - max(m[0], lo)) for m in merged)
    if hi - lo < 12.0 or drawn < 0.35 * (hi - lo):
        return None
    sx, sy = ox + nx * centre_shift, oy + ny * centre_shift
    return (sx + ux * lo, sy + uy * lo, sx + ux * hi, sy + uy * hi)


def _wall_seed_beside(label: Label, model: PageModel) -> Seg | None:
    """Wall face a wall-type tag sits beside: the nearest face the tag
    projects onto that has a parallel face 2-10 units away; heavier lines
    first (grid lines are thin)."""
    assert model.index is not None''')
rep('''        if best is None or score < best[0]:
            best = (score, sg)
    if best is None:
        return None
    return _wall_from_seed(best[1], model, True)''', '''        if best is None or score < best[0]:
            best = (score, sg)
    return best[1] if best is not None else None''')

# 2. take_off_page: W tags use wall_between_walls; twins too
rep('''            elif rule_on:
                run = _wall_beside(lab, model)''', '''            elif rule_on:
                run = wall_between_walls(lab, model) or _wall_beside(lab, model)''')
rep('''                twin = FR.rule_classify(info["wall_type"], rule_ctx)
                if isinstance(twin, dict):
                    rule_infos[(twin["designation"], _r(lab.cx), _r(lab.cy))] = twin
                    wall_entries.append({"label": lab, "info": twin, "cat": "walls", "run": run, "_twin": True})''', '''                twin = FR.rule_classify(info["wall_type"], rule_ctx)
                if isinstance(twin, dict):
                    rule_infos[(twin["designation"], _r(lab.cx), _r(lab.cy))] = twin
                    # The wall type runs wall to wall; the panel may be shorter.
                    twin_run = wall_between_walls(lab, model) or run
                    wall_entries.append({"label": lab, "info": twin, "cat": "walls", "run": twin_run, "_twin": True})''')
# W tags measured wall-to-wall are not split between neighbouring tags
rep('''            panels = [e for e in wall_entries if e["info"].get("role") in ("Shear Wall", "Strap Braced Wall") or e.get("_twin")]
            plain = [e for e in wall_entries if e not in panels]''', '''            panels = [e for e in wall_entries if e["info"].get("role") in ("Shear Wall", "Strap Braced Wall") or e.get("_twin")]
            # Wall-type tags already end at the intersecting walls: only two
            # different tags on the very same stretch share it.
            plain = [e for e in wall_entries if e not in panels]''')
A.write_text(s, encoding="utf-8")
print("ok")
