from pathlib import Path
import os
os.chdir(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = Path('auto_takeoff.py'); s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep("                poly = Z.deck_bay(lab, lines)\n", "                poly = Z.deck_bay(lab, lines) or _deck_region(lab, model)\n")
rep("""            if cat == "areas" and info.get("role") != "Deck":
                continue
            if cat == "beams" and info.get("series"):""", """            if cat == "areas" and (
                info.get("role") != "Deck"
                or re.search(r"PLAN|SHEET|SCHEDULE|LEGEND|NOTES?\b", lab.text.upper())
                or lab.cx > 0.9 * model.width
            ):
                continue  # a title or note about deck, not a callout
            if cat == "beams" and info.get("series"):""")
p.write_text(s, encoding='utf-8')
p = Path('detail_scan.py'); s = p.read_text(encoding='utf-8')
rep('''        if not re.fullmatch(r"[A-Z]{1,3}\d{0,2}|[A-Z]?\d{1,2}", t) or len(t) > 3:''', '''        if not re.fullmatch(r"[A-Z]{1,3}\d{0,2}", t) or len(t) > 3:''')
p.write_text(s, encoding='utf-8')
print('ok')
