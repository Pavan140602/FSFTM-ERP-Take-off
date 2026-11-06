# OE-DELIVERY 2026-11-05-framing-rules: wall-plan tags - the hatched panel at a SW / BR tag,
# the double-line wall beside a W tag.
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


rep('''

def _hatch_extent(''', '''

def _hatch_panel(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Centre line of the hatched wall panel nearest a shear / strap-braced
    wall tag: the hatch strokes are followed stroke to stroke, the panel's
    direction is its long side."""
    if model.fine_index is None:
        return None
    upf = model.units_per_foot or 9.0
    reach = 5.0 * upf

    def stroke(sg) -> float | None:
        ln = math.hypot(sg[2] - sg[0], sg[3] - sg[1])
        if not (2.0 <= ln <= 14.0):
            return None
        c = abs((sg[2] - sg[0]) / ln)
        if not (0.4 <= c <= 0.92):
            return None
        return _fold(math.degrees(math.atan2(sg[3] - sg[1], sg[2] - sg[0])))

    cx, cy = label.cx, label.cy
    seed = None
    for i in model.fine_index.near(cx - reach, cy - reach, cx + reach, cy + reach):
        sg = model.fine[i]
        if stroke(sg) is None:
            continue
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        d = math.hypot(mx - cx, my - cy)
        if d <= reach and (seed is None or d < seed[0]):
            seed = (d, i)
    if seed is None:
        return None
    ang0 = stroke(model.fine[seed[1]])
    seen = {seed[1]}
    todo = [seed[1]]
    mids: list[tuple[float, float]] = []
    while todo and len(seen) < 4000:
        i = todo.pop()
        sg = model.fine[i]
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        mids.append((mx, my))
        for j in model.fine_index.near(mx - 8, my - 8, mx + 8, my + 8):
            if j in seen:
                continue
            o = model.fine[j]
            a = stroke(o)
            if a is None or _angle_diff(a, ang0 or 0.0) > 6:
                continue
            if math.hypot((o[0] + o[2]) / 2.0 - mx, (o[1] + o[3]) / 2.0 - my) <= 8:
                seen.add(j)
                todo.append(j)
    if len(mids) < 6:
        return None
    xs = [p[0] for p in mids]
    ys = [p[1] for p in mids]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if max(w, h) < 12:
        return None
    if w >= h:
        y = sum(ys) / len(ys)
        return (min(xs) - 1.0, y, max(xs) + 1.0, y)
    x = sum(xs) / len(xs)
    return (x, min(ys) - 1.0, x, max(ys) + 1.0)


def _wall_beside(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Double-line wall a wall-type tag sits beside (framing rules): the
    nearest wall face the tag projects onto that has a parallel face 2-10
    units away; heavier lines first (grid lines are thin)."""
    assert model.index is not None
    cx, cy = label.cx, label.cy
    radius = max(30.0, 3.5 * label.size)
    pad = 1.4 * label.size
    bx0, by0, bx1, by1 = label.rect[0] - pad, label.rect[1] - pad, label.rect[2] + pad, label.rect[3] + pad
    tag_len = max(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) + 2 * pad
    best: tuple[tuple[int, float], Seg] | None = None
    for i in model.index.near(cx - radius, cy - radius, cx + radius, cy + radius):
        sg = model.segments[i]
        if sg[4] < 30 or is_light(sg):
            continue
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        if bx0 <= mx <= bx1 and by0 <= my <= by1 and sg[4] <= tag_len * 1.6:
            continue
        ux, uy = (sg[2] - sg[0]) / sg[4], (sg[3] - sg[1]) / sg[4]
        t = (cx - sg[0]) * ux + (cy - sg[1]) * uy
        if t < -6 or t > sg[4] + 6:
            continue
        d = abs((cx - sg[0]) * -uy + (cy - sg[1]) * ux)
        if d > radius:
            continue
        partner = False
        for j in model.index.near(min(sg[0], sg[2]) - 11, min(sg[1], sg[3]) - 11, max(sg[0], sg[2]) + 11, max(sg[1], sg[3]) + 11):
            o = model.segments[j]
            if o is sg or o[4] < 20 or _angle_diff(_seg_angle(o), _seg_angle(sg)) > 2:
                continue
            off = abs(((o[0] + o[2]) / 2.0 - sg[0]) * -uy + ((o[1] + o[3]) / 2.0 - sg[1]) * ux)
            if 2.0 <= off <= 10.0:
                partner = True
                break
        if not partner:
            continue
        score = (int(round(d / 6.0)), -(sg[5] or 0.0))
        if best is None or score < best[0]:
            best = (score, sg)
    if best is None:
        return None
    return _wall_from_seed(best[1], model, True)


def _hatch_extent(''')

rep('''        for lab, info in labels_by_cat.get("walls", []):
            run = _wall_run(lab, model, strict=rule_on)
            if run is None or math.hypot(run[2] - run[0], run[3] - run[1]) < 24:
                continue
            wall_entries.append({"label": lab, "info": info, "cat": "walls", "run": run})
        if rule_on:''', '''        for lab, info in labels_by_cat.get("walls", []):
            if rule_on and info.get("role") in ("Shear Wall", "Strap Braced Wall"):
                run = _hatch_panel(lab, model) or _wall_beside(lab, model)
            elif rule_on:
                run = _wall_beside(lab, model)
            else:
                run = _wall_run(lab, model)
            if run is None or math.hypot(run[2] - run[0], run[3] - run[1]) < (12 if rule_on else 24):
                continue
            wall_entries.append({"label": lab, "info": info, "cat": "walls", "run": run})
        if rule_on:''')
rep('''            for e in panels:
                run = e["run"]
                t = _project(run, e["label"].cx, e["label"].cy)
                ext = _hatch_extent(run, t, model)
                if ext is not None and ext[1] - ext[0] >= 12:
                    e["run"] = (*_point_on(run, ext[0]), *_point_on(run, ext[1]))
                else:
                    e["_share"] = True''', '''            for e in panels:
                # Two tags on one panel (both sides of a corridor wall pair
                # each have their own panel, so this is a true repeat).
                e["_share"] = False''')
A.write_text(s, encoding="utf-8")
print("ok")
