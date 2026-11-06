from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
a = r'''        if re.search(r"DECK\s+LEGEND|DECK\s+SCHEDULE|DECK\s+TYPES?", lab.text.upper()):'''
b = r'''        if re.search(r"\bLEGEND\b|DECK\s+SCHEDULE|DECK\s+TYPES?", lab.text.upper()):'''
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('ok')
