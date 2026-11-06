# OE-DELIVERY 2026-11-05-framing-rules: sheet kind from the title-block title.
from pathlib import Path
import sys

P = Path(sys.argv[1]) / "backend/app/modules/takeoff/framing_rules.py"
s = P.read_text(encoding="utf-8")
ADD = '''

def title_block_title(page) -> str:
    """The sheet title written in the title block (the strip along the right
    or bottom edge, next to the sheet number) - e.g. 'FRAMING PLAN',
    'WALL PLAN', 'DETAILS'. Empty when the sheet has no such strip."""
    try:
        d = page.get_text("dict")
    except Exception:
        return ""
    W, H = float(page.rect.width), float(page.rect.height)
    parts: list[tuple[float, float, str]] = []
    for b in d.get("blocks", []):
        for ln in b.get("lines", []):
            spans = ln.get("spans") or []
            if not spans:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            sz = max(s.get("size", 0) for s in spans)
            if sz < 14 or x0 < 0.9 * W or y0 < 0.75 * H:
                continue
            text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if re.fullmatch(r"[A-Z]{1,2}-?\\d{3}(\\.\\d+)?", text):
                continue
            parts.append((y0, x0, text))
    parts.sort()
    return " ".join(p[2] for p in parts)


def page_kind(page) -> tuple[str | None, int | None, list[str]]:
    """(kind, level, titles) of one sheet. The title block decides whether it
    is a plan at all (so a detail sheet with a small 'FOUNDATION PLAN' detail
    is not one); the drawing title gives the level."""
    titles = page_titles(page)
    tb = title_block_title(page).upper()
    if tb and "PLAN" not in tb:
        return None, None, titles
    kind, level = sheet_kind(titles)
    if tb and kind is None:
        kind, level = sheet_kind([tb])
    return kind, level, titles
'''
anchor = "\n\n_SCHED_CACHE: dict"
if s.count(anchor) != 1:
    print("ANCHOR FAIL")
    sys.exit(1)
s = s.replace(anchor, ADD + anchor)
P.write_text(s, encoding="utf-8")
print("ok")
