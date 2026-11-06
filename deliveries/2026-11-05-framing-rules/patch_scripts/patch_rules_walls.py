# OE-DELIVERY 2026-11-05-framing-rules: shear wall plans - walls never bridge a gap, stacked
# tags (BR-1 over W1) share their wall, shear / strap-braced walls take the hatched length.
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


rep('''def merge_run(seed: Seg, model: PageModel, max_gap: float = 12.0) -> tuple[float, float, float, float]:''',
    '''def merge_run(seed: Seg, model: PageModel, max_gap: float = 12.0, width_tol: float | None = None) -> tuple[float, float, float, float]:''')
rep('''        for s in cands:
            if not same_pen(seed, s):
                continue
            su = ((s[2] - s[0]) / s[4], (s[3] - s[1]) / s[4])''', '''        for s in cands:
            if not same_pen(seed, s):
                continue
            if width_tol is not None and abs((s[5] or 0.0) - (seed[5] or 0.0)) > width_tol:
                continue
            su = ((s[2] - s[0]) / s[4], (s[3] - s[1]) / s[4])''')

rep('''def _wall_run(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    assert model.index is not None
    cx, cy = label.cx, label.cy
    via_leader = _leader_target(label, model)
    if via_leader is not None:
        return _wall_from_seed(via_leader, model)''', '''def _wall_run(label: Label, model: PageModel, strict: bool = False) -> tuple[float, float, float, float] | None:
    assert model.index is not None
    cx, cy = label.cx, label.cy
    via_leader = _leader_target(label, model)
    if via_leader is not None:
        return _wall_from_seed(via_leader, model, strict)''')
rep('''    seed = min(pool, key=lambda it: (round(it[1] / 6.0), -it[0][4]))[0]
    return _wall_from_seed(seed, model)


def _wall_from_seed(seed: Seg, model: PageModel) -> tuple[float, float, float, float]:
    """Wall run through ``seed``: merged, then centred between its faces."""
    assert model.index is not None
    run = merge_run(seed, model, max_gap=16.0)''', '''    seed = min(pool, key=lambda it: (round(it[1] / 6.0), -it[0][4]))[0]
    return _wall_from_seed(seed, model, strict)


def _wall_from_seed(seed: Seg, model: PageModel, strict: bool = False) -> tuple[float, float, float, float]:
    """Wall run through ``seed``: merged, then centred between its faces.
    ``strict`` (framing rules): only the same line weight, no gaps - a wall
    stops where it stops, never bridging a corridor or opening."""
    assert model.index is not None
    run = merge_run(seed, model, max_gap=4.0, width_tol=0.05) if strict else merge_run(seed, model, max_gap=16.0)''')

# hatch extent helper
rep('''

def _walk_arrow(''', '''

def _hatch_extent(run: tuple[float, float, float, float], t_tag: float, model: PageModel) -> tuple[float, float] | None:
    """Stretch of a wall run drawn hatched (shear / strap-braced panel)
    nearest ``t_tag`` (distance along the run)."""
    if model.fine_index is None:
        return None
    length = math.hypot(run[2] - run[0], run[3] - run[1])
    if length < 1:
        return None
    ux, uy = (run[2] - run[0]) / length, (run[3] - run[1]) / length
    hits: list[float] = []
    for i in model.fine_index.near(min(run[0], run[2]) - 8, min(run[1], run[3]) - 8, max(run[0], run[2]) + 8, max(run[1], run[3]) + 8):
        sg = model.fine[i]
        ln = math.hypot(sg[2] - sg[0], sg[3] - sg[1])
        if not (2.0 <= ln <= 14.0):
            continue
        cos = abs(((sg[2] - sg[0]) * ux + (sg[3] - sg[1]) * uy) / ln)
        if not (0.4 <= cos <= 0.92):
            continue  # hatch strokes run at an angle across the wall
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        if abs((mx - run[0]) * -uy + (my - run[1]) * ux) > 5.0:
            continue
        hits.append((mx - run[0]) * ux + (my - run[1]) * uy)
    if len(hits) < 4:
        return None
    hits.sort()
    groups: list[list[float]] = [[hits[0]]]
    for h in hits[1:]:
        if h - groups[-1][-1] <= 8.0:
            groups[-1].append(h)
        else:
            groups.append([h])
    groups = [g for g in groups if len(g) >= 4]
    if not groups:
        return None
    reach = 4.0 * (model.units_per_foot or 9.0)

    def gap(g: list[float]) -> float:
        return 0.0 if g[0] <= t_tag <= g[-1] else min(abs(g[0] - t_tag), abs(g[-1] - t_tag))

    best = min(groups, key=gap)
    if gap(best) > reach:
        return None
    return max(0.0, best[0] - 1.0), min(length, best[-1] + 1.0)


def _walk_arrow(''')

# walls section in take_off_page
rep('''        for lab, info in labels_by_cat.get("walls", []):
            run = _wall_run(lab, model)
            if run is None or math.hypot(run[2] - run[0], run[3] - run[1]) < 24:
                continue
            wall_entries.append({"label": lab, "info": info, "cat": "walls", "run": run})
        _split_shared(wall_entries, model)''', '''        for lab, info in labels_by_cat.get("walls", []):
            run = _wall_run(lab, model, strict=rule_on)
            if run is None or math.hypot(run[2] - run[0], run[3] - run[1]) < 24:
                continue
            wall_entries.append({"label": lab, "info": info, "cat": "walls", "run": run})
        if rule_on:
            # Shear / strap-braced panels: the hatched stretch at the tag.
            # Wall types (W1..) split their wall among themselves only, so a
            # 'BR-1' stacked over 'W1' does not cut the W1 wall in two.
            panels = [e for e in wall_entries if e["info"].get("role") in ("Shear Wall", "Strap Braced Wall")]
            plain = [e for e in wall_entries if e not in panels]
            for e in panels:
                run = e["run"]
                t = _project(run, e["label"].cx, e["label"].cy)
                ext = _hatch_extent(run, t, model)
                if ext is not None and ext[1] - ext[0] >= 12:
                    e["run"] = (*_point_on(run, ext[0]), *_point_on(run, ext[1]))
                else:
                    e["_share"] = True
            _split_shared(plain + [e for e in panels if e.get("_share")], model)
        else:
            _split_shared(wall_entries, model)''')
A.write_text(s, encoding="utf-8")
print("ok")
