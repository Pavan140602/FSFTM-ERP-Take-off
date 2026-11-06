# OE-DELIVERY 2026-11-05-detail-scan: stacked tags on framing plans, legend boxes ignored,
# joists read from drawn lines across a leader's line, and a "not taken off" list per sheet.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])
A = ROOT / "backend/app/modules/takeoff/auto_takeoff.py"
FRP = ROOT / "backend/app/modules/takeoff/framing_rules.py"
s = A.read_text(encoding="utf-8")
fr = FRP.read_text(encoding="utf-8")


def rep(old, new, which="A"):
    global s, fr
    src = s if which == "A" else fr
    if src.count(old) != 1:
        print("ANCHOR FAIL", which, src.count(old), old[:120])
        sys.exit(1)
    if which == "A":
        s = src.replace(old, new)
    else:
        fr = src.replace(old, new)


# 1. stacked tags: try the second tag when the first is not for this sheet
rep('''        first = rule_classify(toks[0], rules)
        if isinstance(first, dict):''', '''        first = rule_classify(toks[0], rules)
        if not isinstance(first, dict):
            # 'W4 J-3' on a framing plan: the wall type is for the wall plan,
            # the joist tag is for this one.
            second = rule_classify(toks[1], rules)
            if isinstance(second, dict):
                return second
        if isinstance(first, dict):''', "F")

# 2. legend boxes: excluded like schedules
rep('''        if m.kind:
            try:
                m.fine = page_segments(page, min_len=3.0)
                m.fine_index = SegIndex(m.fine)
            except Exception:
                m.fine, m.fine_index = [], None''', '''        if m.kind:
            try:
                m.fine = page_segments(page, min_len=3.0)
                m.fine_index = SegIndex(m.fine)
            except Exception:
                m.fine, m.fine_index = [], None
            # Legend boxes show sample tags (T-1, HD ...): never take them off.
            try:
                m.schedule_rects.extend(legend_rects(page, m))
            except Exception:
                pass''')

rep('''

def run_models(
    models: list[PageModel],''', '''

def legend_rects(page, model: PageModel) -> list[tuple[float, float, float, float]]:
    """Boxes titled LEGEND (or KEY / SYMBOLS): the smallest drawn rectangle
    around each title, or the area below it when none is drawn."""
    out: list[tuple[float, float, float, float]] = []
    try:
        hits = [r for w in ("LEGEND", "SYMBOL LEGEND") for r in page.search_for(w)]
    except Exception:
        return out
    for h in hits:
        cx, cy = (h.x0 + h.x1) / 2.0, (h.y0 + h.y1) / 2.0
        best = None
        for b in model.boxes:
            if b[0] - 1 <= cx <= b[2] + 1 and b[1] - 1 <= cy <= b[3] + 1:
                area = (b[2] - b[0]) * (b[3] - b[1])
                if area > 60 * 60 and (best is None or area < best[0]):
                    best = (area, b)
        if best is None:
            # Box from four lines: nearest long lines around the title.
            xs0 = [sg for sg in model.segments if abs(sg[1] - sg[3]) < 0.5 and sg[4] > 120 and min(sg[0], sg[2]) - 2 <= cx <= max(sg[0], sg[2]) + 2]
            above = [sg[1] for sg in xs0 if sg[1] <= cy + 2]
            below = [sg[1] for sg in xs0 if sg[1] > cy + 2]
            if above and below:
                top, bot = max(above), max(below)
                spans = [sg for sg in xs0 if abs(sg[1] - top) < 1]
                if spans:
                    sg = max(spans, key=lambda q: q[4])
                    out.append((min(sg[0], sg[2]), top, max(sg[0], sg[2]), bot))
            continue
        out.append(tuple(best[1][:4]))
    return out


def _series_from_tip_line(
    label: Label, info: dict[str, Any], model: PageModel
) -> tuple[list[tuple[float, float, float, float]], bool, list[tuple[float, float]] | None] | None:
    """Members drawn one by one across the line a tag's leader ends on (a
    corridor or end bay): the drawn lines crossing that line, between the
    walls, at about the schedule spacing. Wall faces (double lines) are not
    members."""
    assert model.index is not None
    tip = leader_tip(label, model)
    if tip is None:
        return None
    best = None
    for i in model.index.near(tip[0] - 2, tip[1] - 2, tip[0] + 2, tip[1] + 2):
        sg = model.segments[i]
        if sg[4] >= 30 and _pt_seg_dist(tip[0], tip[1], sg) <= 1.5 and (best is None or sg[4] > best[4]):
            best = sg
    if best is None:
        return None
    dist = merge_run(best, model, max_gap=2.0)
    upf = model.units_per_foot or 9.0
    spacing_units = (info.get("spacing_in") or 24.0) / 12.0 * upf
    members = [mm for mm in _crossing_members(dist, model, spacing_units) if not _has_partner((*mm, math.hypot(mm[2] - mm[0], mm[3] - mm[1]), 0.0, None), model, 2.0, 6.0)]
    if len(members) < 2:
        return None
    # Keep the regular run around the tip (walls end it).
    d_len = math.hypot(dist[2] - dist[0], dist[3] - dist[1]) or 1.0
    ux, uy = (dist[2] - dist[0]) / d_len, (dist[3] - dist[1]) / d_len
    pos = sorted(((((mm[0] + mm[2]) / 2.0 - dist[0]) * ux + ((mm[1] + mm[3]) / 2.0 - dist[1]) * uy), mm) for mm in members)
    t_tip = (tip[0] - dist[0]) * ux + (tip[1] - dist[1]) * uy
    i0 = min(range(len(pos)), key=lambda k: abs(pos[k][0] - t_tip))
    lo = hi = i0
    lim = 1.6 * spacing_units
    while lo > 0 and pos[lo][0] - pos[lo - 1][0] <= lim:
        lo -= 1
    while hi < len(pos) - 1 and pos[hi + 1][0] - pos[hi][0] <= lim:
        hi += 1
    picked = [p[1] for p in pos[lo:hi + 1]]
    if len(picked) < 2:
        return None
    return picked, False, None


def missed_tags(model: PageModel, items: list[dict[str, Any]], rule_infos: dict[tuple[str, float, float], dict[str, Any]], wanted: set[str]) -> list[dict[str, Any]]:
    """Tags on the sheet that no markup answers (nothing of that type within
    4 ft of the tag, or at its leader's end): listed for the estimator so
    nothing is skipped silently."""
    upf = model.units_per_foot or 9.0
    near = 4.0 * upf
    by_des: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_des.setdefault(re.sub(r"[\\s\\-]", "", it.get("designation") or ""), []).append(it)

    def dist(x: float, y: float, it: dict[str, Any]) -> float:
        best = 1e9
        pts = it.get("points") or []
        if len(pts) == 1:
            best = math.hypot(pts[0][0] - x, pts[0][1] - y)
        elif len(pts) >= 2:
            best = _pt_seg_dist(x, y, (pts[0][0], pts[0][1], pts[1][0], pts[1][1], 1.0))
        lr = it.get("label_rect")
        if lr and len(lr) == 4:
            best = min(best, math.hypot((lr[0] + lr[2]) / 2.0 - x, (lr[1] + lr[3]) / 2.0 - y))
        return best

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for (des, x, y), info in rule_infos.items():
        if info.get("category") not in wanted:
            continue
        key = re.sub(r"[\\s\\-]", "", des)
        spot = (key, int(x // 8), int(y // 8))
        if spot in seen:
            continue
        seen.add(spot)
        cands = by_des.get(key, [])
        if any(dist(x, y, it) <= near for it in cands):
            continue
        out.append({
            "designation": des,
            "category": info.get("category"),
            "role": info.get("role"),
            "at": [_r(x), _r(y)],
            "page": model.page_no,
            "reason": "No line, wall or bay could be traced from this tag - check it on the sheet.",
        })
    return out


def run_models(
    models: list[PageModel],''')

# 3. series fallback order: leader crossing -> drawn lines across the tip line -> generic
rep('''            via_leader = _series_from_leader(lab, info, model) if (rule_on and "rule_profile" in info) else None
            lines, generated, bay = via_leader if via_leader else _series_lines(lab, info, model)''', '''            via_leader = _series_from_leader(lab, info, model) if (rule_on and "rule_profile" in info) else None
            if via_leader is None and rule_on and "rule_profile" in info:
                via_leader = _series_from_tip_line(lab, info, model)
            lines, generated, bay = via_leader if via_leader else _series_lines(lab, info, model)''')

# 4. missed list in the page result
rep('''        "sheet_kind": model.kind if rule_on else None,
        "level": model.level if rule_on else None,
    }''', '''        "sheet_kind": model.kind if rule_on else None,
        "level": model.level if rule_on else None,
        "missed": missed_tags(model, items, rule_infos, wanted) if rule_on else [],
    }''')

A.write_text(s, encoding="utf-8")
FRP.write_text(fr, encoding="utf-8")
print("ok")
