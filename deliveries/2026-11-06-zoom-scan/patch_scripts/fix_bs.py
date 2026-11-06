from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
for name in ("framing_rules.py", "auto_takeoff.py", "detail_scan.py"):
    p = base / name
    s = p.read_text(encoding="utf-8")
    n = s.count("\x08")
    if n:
        s = s.replace("\x08", "\\b")
        p.write_text(s, encoding="utf-8")
    print(name, n, "after:", p.read_text(encoding="utf-8").count("\x08"))
