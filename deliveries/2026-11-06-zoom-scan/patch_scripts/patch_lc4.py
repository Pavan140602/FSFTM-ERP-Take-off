from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
a = """                if any(_overlap(sh.bbox, w) for w in ds.words):
                    continue
                if best is None or d + pen < best[0]:"""
b = """                # Other text on the symbol rules it out; the callout's own
                # words do not (slanted text has a big square box).
                if any(
                    _overlap(sh.bbox, w)
                    for w in ds.words
                    if not (lab.rect[0] - 1 <= (w[0] + w[2]) / 2 <= lab.rect[2] + 1 and lab.rect[1] - 1 <= (w[1] + w[3]) / 2 <= lab.rect[3] + 1)
                ):
                    continue
                if best is None or d + pen < best[0]:"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('ok')
