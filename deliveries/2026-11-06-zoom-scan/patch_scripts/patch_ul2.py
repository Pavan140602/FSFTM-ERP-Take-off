from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep("""        if s[4] > 8.0 * max(half, 1.0):
            continue  # a long member line, not a callout's leader""", """        if s[4] > 2.6 * max(half, 1.0):
            continue  # a member line (a beam the size is printed on), not a leader""")
rep("""    W, H = model.width, model.height
    out: list[dict[str, Any]] = []
    checked = 0
    taken = list(found)""", """    W, H = model.width, model.height
    upf = model.units_per_foot or 9.0
    # A small symbol may sit a little way past the end of the leader.
    reach_tip = max(6.0, 1.5 * upf)
    out: list[dict[str, Any]] = []
    checked = 0
    taken = list(found)""")
rep("""                d = math.hypot(sh.cx - ex, sh.cy - ey) - sh.w / 2.0
                if d > 6.0:
                    continue""", """                d = math.hypot(sh.cx - ex, sh.cy - ey) - sh.w / 2.0
                if d > reach_tip:
                    continue""")
p.write_text(s, encoding='utf-8')
print('ok')
