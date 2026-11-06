from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)


rep("""        if s[4] > 2.6 * max(half, 1.0):
            continue  # a member line (a beam the size is printed on), not a leader""", """        if float(s[5] or 0.0) >= heavy_w or s[4] > 6.0 * max(half, 10.0):
            continue  # a member line (a beam the size is printed on), not a leader""")
rep("""    out = []
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 0.8 * half or _adiff(_ang(s), lab.angle) > 5.0:""", """    out = []
    heavy_w = _heavy_width(ds)
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 0.8 * half or _adiff(_ang(s), lab.angle) > 5.0:""")
rep("""    tw = 0.55 * len(lab.text) * lab.size
    r = 2.0 * lab.size
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 2.6 * tw / 2.0 or _adiff(_ang(s), lab.angle) > 5.0:
            continue""", """    tw = 0.55 * len(lab.text) * lab.size
    r = 2.0 * lab.size
    heavy_w = _heavy_width(ds)
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 2.6 * tw / 2.0 or _adiff(_ang(s), lab.angle) > 5.0:
            continue
        if float(s[5] or 0.0) < heavy_w:
            continue  # a thin leader the size is written on, not a member""")
p.write_text(s, encoding="utf-8")
print("ok")
