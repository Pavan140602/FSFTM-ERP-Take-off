from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
a = """    # First-pass columns that sit on an arrow part are removed.
    removed: set[int] = set()
    for i, c in enumerate(found):
        x, y = c["point"]
        if any(a.bbox[0] - 1 <= x <= a.bbox[2] + 1 and a.bbox[1] - 1 <= y <= a.bbox[3] + 1 for a in arrows):
            removed.add(i)"""
b = """    # First-pass columns checked again zoomed in: one on an arrow part, or
    # with a grid letter / tag text at its centre (a grid bubble), is removed.
    removed: set[int] = set()
    for i, c in enumerate(found):
        x, y = c["point"]
        if any(a.bbox[0] - 1 <= x <= a.bbox[2] + 1 and a.bbox[1] - 1 <= y <= a.bbox[3] + 1 for a in arrows):
            removed.add(i)
            continue
        for w in ds.words:
            if w[2] - w[0] > 30:
                continue  # a long word / sentence near a column is a callout
            if w[0] - 1 <= x <= w[2] + 1 and w[1] - 1 <= y <= w[3] + 1:
                removed.add(i)
                break"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('ok')
