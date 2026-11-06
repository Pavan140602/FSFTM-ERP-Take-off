# OE-DELIVERY 2026-11-05-framing-rules: foundation plans - a column at the end of each
# size label's leader; the base plate tag printed under it counts at that column.
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


rep('''    col_found = _columns(model, labels_by_cat, column_name, col_marks) if ("columns" in wanted or "beams" in wanted) else []''',
    '''    if rule_on and model.kind == "foundation":
        col_found = _leader_columns(model, labels_by_cat)
        # Base plate tags print under the column size: count them at the column.
        for lab_bp, _ri in rule_counts:
            near = min(col_found, key=lambda c: math.hypot(c["label_obj"].cx - lab_bp.cx, c["label_obj"].cy - lab_bp.cy), default=None)
            if near is not None and math.hypot(near["label_obj"].cx - lab_bp.cx, near["label_obj"].cy - lab_bp.cy) <= 4.5 * lab_bp.size:
                _ri["_at"] = near["point"]
    else:
        col_found = _columns(model, labels_by_cat, column_name, col_marks) if ("columns" in wanted or "beams" in wanted) else []''')

rep('''    for lab, info in rule_counts:
        tag = info["designation"]
        items.append({
            "key": _key(p, info["category"], tag, lab.cx, lab.cy),
            "category": info["category"],
            "kind": "count",
            "designation": tag,
            "label": tag,
            "spec": info.get("spec"),
            "points": [[_r(lab.cx), _r(lab.cy)]],''', '''    for lab, info in rule_counts:
        tag = info["designation"]
        at = info.pop("_at", None) or (lab.cx, lab.cy)
        items.append({
            "key": _key(p, info["category"], tag, lab.cx, lab.cy),
            "category": info["category"],
            "kind": "count",
            "designation": tag,
            "label": tag,
            "spec": info.get("spec"),
            "points": [[_r(at[0]), _r(at[1])]],''')

rep('''

def _walk_arrow(''', '''

def leader_tip(label: Label, model: PageModel) -> tuple[float, float] | None:
    """Far end of the leader line drawn from a label (None without one)."""
    assert model.index is not None
    cx, cy = label.cx, label.cy
    half = math.hypot(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) / 2.0
    near_r = half + 1.2 * label.size
    best: tuple[float, tuple[float, float]] | None = None
    segs = model.fine if model.fine_index is not None else model.segments
    index = model.fine_index if model.fine_index is not None else model.index
    for i in index.near(cx - near_r - 160, cy - near_r - 160, cx + near_r + 160, cy + near_r + 160):
        ld = segs[i]
        if not (10 <= ld[4] <= 200):
            continue
        # Leaders are drawn at an angle to the text.
        if _angle_diff(_seg_angle(ld), label.angle) < 12:
            continue
        d0 = math.hypot(ld[0] - cx, ld[1] - cy)
        d1 = math.hypot(ld[2] - cx, ld[3] - cy)
        if min(d0, d1) > near_r or max(d0, d1) < near_r:
            continue
        tip = (ld[2], ld[3]) if d1 > d0 else (ld[0], ld[1])
        score = min(d0, d1)
        if best is None or score < best[0]:
            best = (score, tip)
    return best[1] if best else None


def _symbol_centre(model: PageModel, x: float, y: float, reach: float = 9.0) -> tuple[float, float]:
    """Centre of the small symbol (column square) drawn at a leader tip."""
    if model.fine_index is None:
        return x, y
    xs: list[float] = []
    ys: list[float] = []
    for i in model.fine_index.near(x - reach, y - reach, x + reach, y + reach):
        sg = model.fine[i]
        if sg[4] > 2.2 * reach:
            continue
        if max(abs(sg[0] - x), abs(sg[2] - x)) <= reach and max(abs(sg[1] - y), abs(sg[3] - y)) <= reach:
            xs += [sg[0], sg[2]]
            ys += [sg[1], sg[3]]
    if len(xs) < 6:
        return x, y
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _leader_columns(model: PageModel, labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]]) -> list[dict[str, Any]]:
    """Foundation plans: one column at the end of each column-size leader."""
    out: list[dict[str, Any]] = []
    for lab, info in labels_by_cat.get("columns", []):
        tip = leader_tip(lab, model)
        if tip is None:
            continue
        pt = _symbol_centre(model, tip[0], tip[1])
        if any(math.hypot(pt[0] - c["point"][0], pt[1] - c["point"][1]) < 3 for c in out):
            continue
        out.append({
            "mark_obj": None,
            "label_obj": lab,
            "point": pt,
            "designation": info["designation"],
            "label": info["designation"],
            "mark": None,
            "label_rect": list(lab.rect),
            "size": None,
        })
    return out


def _walk_arrow(''')
A.write_text(s, encoding="utf-8")
print("ok")
