# OE-DELIVERY 2026-11-05-framing-rules: title block must BE a plan title.
from pathlib import Path
import sys

P = Path(sys.argv[1]) / "backend/app/modules/takeoff/framing_rules.py"
s = P.read_text(encoding="utf-8")
old = '''    titles = page_titles(page)
    tb = title_block_title(page).upper()
    if tb and "PLAN" not in tb:
        return None, None, titles
    kind, level = sheet_kind(titles)
    if tb and kind is None:
        kind, level = sheet_kind([tb])
    return kind, level, titles
'''
new = '''    titles = page_titles(page)
    tb = " ".join(title_block_title(page).upper().split())
    if not tb:
        kind, level = sheet_kind(titles)
        return kind, level, titles
    m = _TB_PLAN_RE.fullmatch(tb)
    if not m:
        return None, None, titles
    if m.group("found"):
        return "foundation", 0, titles
    kind, level = sheet_kind([tb + (" PLAN" if not tb.endswith("PLAN") else "")])
    if kind and level is None and kind != "roof":
        k2, l2 = sheet_kind(titles)
        if k2 == kind:
            level = l2
    return kind, level, titles


_TB_PLAN_RE = re.compile(
    r"(?:(?:\\d{1,2}(?:ST|ND|RD|TH)|GROUND|FIRST|SECOND|THIRD|FOURTH|FIFTH|ROOF)\\s+)?(?:FLOOR\\s+|LEVEL\\s+)?"
    r"(?:(?P<found>FOUNDATION(?:\\s+PLAN)?)|FRAMING(?:\\s+PLAN)?|SHEAR\\s*WALL(?:\\s+PLAN)?|WALL\\s+PLAN)"
)
'''
if s.count(old) != 1:
    print("ANCHOR FAIL")
    sys.exit(1)
s = s.replace(old, new)
P.write_text(s, encoding="utf-8")
print("ok")
