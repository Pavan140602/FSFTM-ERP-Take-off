"""Column marks + schedule profiles, label rects (all-or-nothing).
OE-DELIVERY: 2026-11-02-auto-takeoff-columns"""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')

SCHED = r'''

# ── column marks (C1, C2 ...) and the column schedule ─────────────────
# OE-DELIVERY: 2026-11-02-auto-takeoff-columns

_COL_MARK_RE = re.compile(r"^(?:C|COL|SC|HC|PC|TC|CL)-?\d{1,3}[A-Z]?$", re.IGNORECASE)
_PROFILE_RES = (D._AISC_RE, D._SSMA_RE)


def _profile_in(text: str) -> str | None:
    for rx in _PROFILE_RES:
        m = rx.search(text or "")
        if m:
            return D.normalize_designation(m.group(0))
    return None


def column_schedule(models: list["PageModel"]) -> dict[str, str]:
    """Column mark -> profile from column schedules.

    Two table shapes are read:
    * row form   ``C1  HSS8X8X1/2  ...`` (mark first, profile on the row);
    * column form a row of marks ``C1 C2 C3`` with each profile printed
      below its mark in the same column.
    """
    out: dict[str, str] = {}
    for model in models:
        lines = sorted(
            [ln for ln in model.lines if ln.words],
            key=lambda ln: min(w[1][1] for w in ln.words),
        )
        for li, line in enumerate(lines):
            words = sorted(line.words, key=lambda w: w[1][0])
            marks = [w for w in words if _COL_MARK_RE.match(re.sub(r"\s+", "", w[0]))]
            if not marks:
                continue
            first = re.sub(r"\s+", "", words[0][0]).upper()
            if _COL_MARK_RE.match(first) and len(marks) == 1:
                # Row form: the profile on the same row, within table reach.
                rest = " ".join(w[0] for w in words[1:] if w[1][0] - words[0][1][2] < 500)
                prof = _profile_in(rest)
                if prof:
                    out.setdefault(first, prof)
                continue
            if len(marks) < 2:
                continue
            # Column form: look down each mark's column for a profile.
            y_top = max(w[1][3] for w in marks)
            for mk in marks:
                mark = re.sub(r"\s+", "", mk[0]).upper()
                if mark in out:
                    continue
                mx0, mx1 = mk[1][0], mk[1][2]
                cx = (mx0 + mx1) / 2.0
                reach = max(30.0, (mx1 - mx0) * 2)
                for below in lines[li + 1:]:
                    by = min(w[1][1] for w in below.words)
                    if by - y_top > 400:
                        break
                    cell = " ".join(
                        w[0] for w in sorted(below.words, key=lambda w: w[1][0])
                        if abs((w[1][0] + w[1][2]) / 2.0 - cx) <= reach
                    )
                    prof = _profile_in(cell)
                    if prof:
                        out[mark] = prof
                        break
    return out
'''

pairs = [
# 1. schedule helpers after schedule_specs
("""def schedule_specs(models: list[PageModel]) -> dict[str, str]:
    return schedule_rows(models)[0]
""", """def schedule_specs(models: list[PageModel]) -> dict[str, str]:
    return schedule_rows(models)[0]
""" + SCHED),
# 2. classify column marks
("""    if (_TRUSS_TAG_RE.match(compact) or _TRUSS_SOFT_RE.match(compact)) and spacing is None and len(compact) <= 5:""",
 """    if _COL_MARK_RE.match(compact) and spacing is None:
        return {"category": "columns", "designation": compact, "spacing_in": None, "series": False, "tag": True, "mark": True}
    if (_TRUSS_TAG_RE.match(compact) or _TRUSS_SOFT_RE.match(compact)) and spacing is None and len(compact) <= 5:"""),
# 3. _columns signature
("""def _columns(model: PageModel, labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]], default_name: str | None) -> list[dict[str, Any]]:""",
 """def _columns(
    model: PageModel,
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]],
    default_name: str | None,
    marks: dict[str, str] | None = None,
) -> list[dict[str, Any]]:"""),
# 4. grid-bubble filter must not drop a column with its mark beside it
("""        if any(len(lab.text) <= 4 and math.hypot(lab.cx - cxb, lab.cy - cyb) <= reach for lab in model.labels):""",
 """        if any(
            len(lab.text) <= 4
            and not _COL_MARK_RE.match(re.sub(r"\\s+", "", lab.text))
            and math.hypot(lab.cx - cxb, lab.cy - cyb) <= reach
            for lab in model.labels
        ):"""),
# 5. naming: size label > mark (+ schedule) > nearby square HSS / W > default
("""            name = default_name or "COLUMN"
            best = None
            for lab, info in col_labels:
                d = math.hypot(lab.cx - cxb, lab.cy - cyb)
                if d <= 70 and (best is None or d < best[0]):
                    best = (d, info["designation"])
            if best:
                name = best[1]
            out.append({"point": (cxb, cyb), "designation": name, "size": round(max(b[2] - b[0], b[3] - b[1]), 1)})""",
 """            size_lab = None
            mark_lab = None
            for lab, info in col_labels:
                d = math.hypot(lab.cx - cxb, lab.cy - cyb)
                if d > 70:
                    continue
                if info.get("mark"):
                    if mark_lab is None or d < mark_lab[0]:
                        mark_lab = (d, lab, info["designation"])
                elif size_lab is None or d < size_lab[0]:
                    size_lab = (d, lab, info["designation"])
            if size_lab is None:
                # A square HSS / W size printed right beside the symbol.
                for lab, info in labels_by_cat.get("beams", []):
                    d = math.hypot(lab.cx - cxb, lab.cy - cyb)
                    des = info["designation"]
                    square = re.match(r"HSS(\\d+(?:\\.\\d+)?)X(\\d+(?:\\.\\d+)?)X", des)
                    if d <= 45 and (des.startswith("W") or (square and square.group(1) == square.group(2))):
                        if size_lab is None or d < size_lab[0]:
                            size_lab = (d, lab, des)
            mark = mark_lab[2] if mark_lab else None
            size = size_lab[2] if size_lab else ((marks or {}).get(mark) if mark else None)
            if not size and not mark and marks and len(set(marks.values())) == 1:
                size = next(iter(marks.values()))
            name = size or mark or default_name or "COLUMN"
            label = f"{mark} {size}" if (mark and size) else name
            src = (size_lab or mark_lab)
            rect = list(src[1].rect) if src else None
            if mark_lab and not size_lab:
                rect = list(mark_lab[1].rect)
            out.append({
                "point": (cxb, cyb),
                "designation": name,
                "label": label,
                "mark": mark,
                "label_rect": rect,
                "size": round(max(b[2] - b[0], b[3] - b[1]), 1),
            })"""),
# 6. column items carry label + rect
("""        for c in _columns(model, labels_by_cat, column_name):
            x, y = c["point"]""", """        for c in _columns(model, labels_by_cat, column_name, col_marks):
            x, y = c["point"]"""),
("""                "category": "columns",
                "kind": "count",
                "designation": c["designation"],
                "label": c["designation"],
                "spec": None,""", """                "category": "columns",
                "kind": "count",
                "designation": c["designation"],
                "label": c["label"],
                "spec": (f"Mark {c['mark']}" if c["mark"] else None),
                "label_rect": [_r(v) for v in c["label_rect"]] if c["label_rect"] else None,"""),
# 7. take_off_page gets the marks
("""    column_name: str | None = None,
    skip_spots: set[tuple[int, int, int]] | None = None,
) -> dict[str, Any]:""", """    column_name: str | None = None,
    skip_spots: set[tuple[int, int, int]] | None = None,
    col_marks: dict[str, str] | None = None,
) -> dict[str, Any]:"""),
("""        results.append(take_off_page(model, cats, hints=hints, specs=specs, skip_spots=spots))""",
 """        results.append(take_off_page(model, cats, hints=hints, specs=specs, skip_spots=spots, col_marks=col_marks))"""),
("""    specs, spots = schedule_rows(spec_models)
    if extra_specs:""", """    specs, spots = schedule_rows(spec_models)
    col_marks = column_schedule(spec_models)
    if extra_specs:"""),
("""    return {"pages": results, "specs": specs}""", """    return {"pages": results, "specs": specs, "column_marks": col_marks}"""),
]
bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
# 8. every label-based item records the label rect (profile highlight)
n_rect = s.count('            "anchor": [_r(lab.cx), _r(lab.cy)],\n') + s.count('                        "anchor": [_r(lab.cx), _r(lab.cy)],\n') + s.count('                    "anchor": [_r(lab.cx), _r(lab.cy)],\n') + s.count('                "anchor": [_r(lab.cx), _r(lab.cy)],\n')
import re as _re
s, k = _re.subn(r'(\n(\s+)"anchor": \[_r\(lab\.cx\), _r\(lab\.cy\)\],\n)', lambda m: m.group(1) + m.group(2) + '"label_rect": [_r(v) for v in lab.rect],\n', s)
print('label_rect added to', k, 'item kinds')
# Spec schedules: also read column schedule sheets
s = s.replace('if "SCHEDULE" in text or "WALL TYPE" in text or "LEGEND" in text:', 'if "SCHEDULE" in text or "WALL TYPE" in text or "LEGEND" in text or "COLUMN" in text:')
p.write_text(s, encoding='utf-8')
print('ok')
