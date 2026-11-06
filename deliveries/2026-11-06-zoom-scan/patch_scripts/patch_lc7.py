from pathlib import Path
base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = base / "detail_scan.py"
s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep("""        if best is None:
            continue
        sh = best[1]
        if any(math.hypot(sh.cx - x, sh.cy - y) <= max(4.0, sh.w * 0.75) for x, y in taken):
            continue
        out.append({"label": lab, "point": (sh.cx, sh.cy), "size": round(sh.w, 1)})
        taken.append((sh.cx, sh.cy))
    return out, checked""", """        if best is None:
            # No symbol where it points: unless a column already stands at
            # one of its ends, list it for the estimator.
            if not any(math.hypot(x - ex, y - ey) <= 20 for x, y in taken for ex, ey, _p in ends) and not any(
                max(lab.rect[0] - x, 0.0, x - lab.rect[2]) + max(lab.rect[1] - y, 0.0, y - lab.rect[3]) <= 14 for x, y in taken
            ):
                unresolved.append(lab)
            continue
        sh = best[1]
        if any(math.hypot(sh.cx - x, sh.cy - y) <= max(4.0, sh.w * 0.75) for x, y in taken):
            continue
        out.append({"label": lab, "point": (sh.cx, sh.cy), "size": round(sh.w, 1)})
        taken.append((sh.cx, sh.cy))
    label_columns.unresolved = unresolved  # type: ignore[attr-defined]
    return out, checked""")
rep("""    out: list[dict[str, Any]] = []
    checked = 0
    taken = list(found)
    # W sizes name columns""", """    out: list[dict[str, Any]] = []
    unresolved: list[Any] = []
    checked = 0
    taken = list(found)
    # W sizes name columns""")
p.write_text(s, encoding='utf-8')

p = base / "auto_takeoff.py"
s = p.read_text(encoding='utf-8')
rep("""                zoom_stats["labels_checked"] = checked
                zoom_stats["added"] = zoom_stats.get("added", 0) + len(lab_cols)""", """                zoom_stats["labels_checked"] = checked
                zoom_stats["added"] = zoom_stats.get("added", 0) + len(lab_cols)
                col_unresolved = list(getattr(Z.label_columns, "unresolved", []))""")
rep("""    zoom_stats: dict[str, Any] | None = None
    zparts: list[dict[str, Any]] = []""", """    zoom_stats: dict[str, Any] | None = None
    zparts: list[dict[str, Any]] = []
    col_unresolved: list[Label] = []""")
rep("""    elif detail_scan:
        missed = generic_missed(model, items, labels_by_cat, wanted, used_by_columns)
    else:
        missed = []""", """    elif detail_scan:
        missed = generic_missed(model, items, labels_by_cat, wanted, used_by_columns)
    else:
        missed = []
    if detail_scan and "columns" in wanted:
        for lab in col_unresolved:
            missed.append({
                "designation": re.sub(r"\s+", "", lab.text.upper()),
                "category": "columns",
                "role": "Column",
                "at": [_r(lab.cx), _r(lab.cy)],
                "page": model.page_no,
                "reason": "Column size with no column symbol where it points (drawn as part of a wall?) - check it on the sheet.",
            })""")
p.write_text(s, encoding='utf-8')
print('ok')
