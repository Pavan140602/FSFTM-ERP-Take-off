from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
a = """                ends.extend((x, y, 2.0) for x, y in list(leader_ends(lab))[:4])"""
b = """                ends.extend((x, y, 1000.0) for x, y in list(leader_ends(lab))[:4])  # leaders only when the text line points nowhere"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('ok')
