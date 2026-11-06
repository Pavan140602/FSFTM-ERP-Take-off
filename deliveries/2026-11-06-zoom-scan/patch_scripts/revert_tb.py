from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\framing_rules.py")
s = p.read_text(encoding="utf-8")
a = '''    m = _TB_PLAN_RE.fullmatch(tb)
    if not m:
        # The big text may be a project status ("NEW CONSTRUCTION") with the
        # sheet title printed small under the sheet number
        # (OE-DELIVERY 2026-11-06-zoom-scan).
        small = title_block_small_title(page) if _TB_NOT_TITLE_RE.search(tb) else ""
        m = _TB_PLAN_RE.fullmatch(small) if small else None
        if not m:
            return None, None, titles
        tb = small
    if m.group("found"):'''
b = '''    m = _TB_PLAN_RE.fullmatch(tb)
    if not m:
        # Sets that print the sheet title small under a project status
        # ("NEW CONSTRUCTION") are read by title_block_small_title(), but are
        # not switched to the house rules yet: their members are written
        # differently (callouts with spacing on the plan, overall plans) and
        # the rules would skip them (OE-DELIVERY 2026-11-06-zoom-scan).
        return None, None, titles
    if m.group("found"):'''
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("reverted")
