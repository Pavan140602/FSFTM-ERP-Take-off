from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\auto_takeoff.py")
s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep("""            if "columns" in wanted:
                lab_cols, checked = Z.label_columns(""", """            if "columns" in wanted and not (rule_on and model.kind == "foundation"):
                # (On a foundation plan read by the house rules every column
                # already comes from its label's leader.)
                lab_cols, checked = Z.label_columns(""")
rep("""                lambda x, y: _column_named(x, y, labels_by_cat, column_name, col_marks),""",
    """                lambda x, y: _column_named(x, y, labels_by_cat, column_name, col_marks, mark_reach=30.0),""")
rep("""    default_name: str | None,
    marks: dict[str, str] | None,
) -> dict[str, Any]:
    \"\"\"Name a column symbol at (cxb, cyb)""", """    default_name: str | None,
    marks: dict[str, str] | None,
    mark_reach: float = 70.0,
) -> dict[str, Any]:
    \"\"\"Name a column symbol at (cxb, cyb)""")
rep("""        d = math.hypot(lab.cx - cxb, lab.cy - cyb)
        if d > 70:
            continue
        if info.get("mark"):""", """        d = math.hypot(lab.cx - cxb, lab.cy - cyb)
        if d > 70:
            continue
        if info.get("mark"):
            if d > mark_reach:
                continue  # a mark further off belongs to something else (deck cut marks C2, C17)""")
p.write_text(s, encoding='utf-8')
print('ok')
