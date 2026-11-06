from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\framing_rules.py")
s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep('''    m = _TB_PLAN_RE.fullmatch(tb)
    if not m:
        return None, None, titles
    if m.group("found"):''', '''    m = _TB_PLAN_RE.fullmatch(tb)
    if not m:
        # The big text may be a project status ("NEW CONSTRUCTION") with the
        # sheet title printed small under the sheet number
        # (OE-DELIVERY 2026-11-06-zoom-scan).
        small = " ".join(title_block_small_title(page).upper().split())
        m = _TB_PLAN_RE.fullmatch(small) if small else None
        if not m:
            return None, None, titles
        tb = small
    if m.group("found"):''')
rep('''def page_kind(page) -> tuple[str | None, int | None, list[str]]:''', '''def title_block_small_title(page) -> str:
    """A plan title printed in small text in the title block strip (right or
    bottom edge): the line naming a plan (FOUNDATION / FRAMING / WALL PLAN),
    joined with the line right above it when that one carries the level
    ("SECOND FLOOR" / "FRAMING PLAN")."""
    try:
        d = page.get_text("dict")
    except Exception:
        return ""
    W, H = float(page.rect.width), float(page.rect.height)
    lines: list[tuple[float, float, float, str]] = []
    for b in d.get("blocks", []):
        for ln in b.get("lines", []):
            spans = ln.get("spans") or []
            if not spans:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            if x0 < 0.9 * W or y0 < 0.75 * H:
                continue
            text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if text:
                lines.append((y0, x0, max(s.get("size", 0) for s in spans), text))
    lines.sort()
    for i, (y0, x0, sz, text) in enumerate(lines):
        u = " ".join(text.upper().split())
        if not re.search(r"\b(FOUNDATION|FRAMING|WALL)\b", u) or "PLAN" not in u and "FRAMING" not in u:
            continue
        if i > 0:
            py, px, psz, ptext = lines[i - 1]
            pu = " ".join(ptext.upper().split())
            if 0 < y0 - py <= 2.0 * sz and re.search(r"FLOOR|LEVEL|ROOF|\d(ST|ND|RD|TH)\b|FIRST|SECOND|THIRD|FOURTH|FIFTH|GROUND", pu):
                return f"{pu} {u}"
        return u
    return ""


def page_kind(page) -> tuple[str | None, int | None, list[str]]:''')
p.write_text(s, encoding='utf-8')
print('ok')
