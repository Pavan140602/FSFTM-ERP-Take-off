from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep("""    out: list[dict[str, Any]] = []
    checked = 0
    taken = list(found)
    for lab in model.labels:
        t = "".join(lab.text.split()).upper()
        m = _COL_SIZE_RE.match(t)""", """    out: list[dict[str, Any]] = []
    checked = 0
    taken = list(found)
    # W sizes name columns only on a column sheet (foundation / column plan,
    # where square tube sizes outnumber W sizes); on a framing plan a W size
    # is a beam.
    n_sq = n_w = 0
    for lab in model.labels:
        t = "".join(lab.text.split()).upper()
        mm = _COL_SIZE_RE.match(t)
        if not mm:
            continue
        if t.startswith("W"):
            n_w += 1
        elif mm.group(1) and mm.group(1) == mm.group(2):
            n_sq += 1
    w_columns = n_sq > 0 and n_sq >= n_w
    for lab in model.labels:
        t = "".join(lab.text.split()).upper()
        m = _COL_SIZE_RE.match(t)""")
rep("""        if t.startswith("W") and _on_member_line(lab, ds):
            continue  # a beam size printed along its beam""", """        if t.startswith("W") and (not w_columns or _on_member_line(lab, ds)):
            continue  # a beam size""")
rep("""                if not (3.0 <= sh.w <= 20.0) or sh.aspect > 5.0:
                    continue""", """                if not (3.0 <= sh.w <= 20.0) or sh.aspect > 5.0 or sh.kind is None:
                    continue  # triangles (moment-connection marks), arrows""")
p.write_text(s, encoding='utf-8')
print('ok')
