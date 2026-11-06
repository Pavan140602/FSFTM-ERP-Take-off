from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = base / "detail_scan.py"
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)


rep("""        sh = best[1]
        if any(math.hypot(sh.cx - x, sh.cy - y) <= max(4.0, sh.w * 0.75) for x, y in taken):
            continue
        out.append({"label": lab, "point": (sh.cx, sh.cy), "size": round(sh.w, 1)})""", """        sh = best[1]
        hit = next((k for k, (x, y) in enumerate(taken) if math.hypot(sh.cx - x, sh.cy - y) <= max(4.0, sh.w * 0.75)), None)
        if hit is not None:
            if hit < n_found:
                claims.append((lab, hit))  # the column is there: this label names it
            continue
        out.append({"label": lab, "point": (sh.cx, sh.cy), "size": round(sh.w, 1)})""")
rep("""    out: list[dict[str, Any]] = []
    unresolved: list[Any] = []
    checked = 0
    taken = list(found)""", """    out: list[dict[str, Any]] = []
    unresolved: list[Any] = []
    claims: list[tuple[Any, int]] = []
    checked = 0
    taken = list(found)
    n_found = len(found)""")
rep("""    label_columns.unresolved = unresolved  # type: ignore[attr-defined]""", """    label_columns.unresolved = unresolved  # type: ignore[attr-defined]
    label_columns.claims = claims  # type: ignore[attr-defined]""")
p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")
rep("""                col_unresolved = list(getattr(Z.label_columns, "unresolved", []))""", """                col_unresolved = list(getattr(Z.label_columns, "unresolved", []))
                # A label pointing at a column already found names it (and is
                # then not read again as a beam).
                for lab, k in getattr(Z.label_columns, "claims", []):
                    c = col_found[k]
                    if c.get("label_obj") is not None and c.get("designation") not in (None, "", "COLUMN"):
                        continue
                    info = classify(lab) or {}
                    des = info.get("designation") or re.sub(r"\\s+", "", lab.text.upper())
                    c.update({"label_obj": lab, "designation": des, "label": des, "label_rect": list(lab.rect)})""")
p.write_text(s, encoding="utf-8")
print("ok")
