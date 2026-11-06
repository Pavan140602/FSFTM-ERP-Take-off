from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\auto_takeoff.py")
s = p.read_text(encoding="utf-8")
bad = 'if cat == "beams" and re.match(r"^(HSS(\\d+(?:\\.\\d+)?)X\x02X|W\\d+X)"'
good = 'if cat == "beams" and re.match(r"^(HSS(\\d+(?:\\.\\d+)?)X\\2X|W\\d+X)"'
print(s.count(bad))
s = s.replace(bad, good)
print("ctrl chars left:", sum(s.count(c) for c in "\x01\x02\x03\x08"))
p.write_text(s, encoding="utf-8")
