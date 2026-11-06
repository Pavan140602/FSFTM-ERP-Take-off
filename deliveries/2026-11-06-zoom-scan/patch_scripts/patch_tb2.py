from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\framing_rules.py")
s = p.read_text(encoding="utf-8")
i = s.index("def title_block_small_title(page) -> str:")
j = s.index("def page_kind(page)", i)
new_fn = r'''def title_block_small_title(page) -> str:
    """The sheet title printed in small text in the title block strip (often
    under the sheet number, over one or two lines: "FIRST FLOOR WALL" /
    "PLAN"). Returns the first block of lines that reads as a plan title."""
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
            text = " ".join(sp.get("text", "").strip() for sp in spans).strip()
            if text:
                lines.append((y0, x0, max(sp.get("size", 0) for sp in spans), text))
    lines.sort()
    # Lines one under the other make one title.
    blocks: list[list[tuple[float, float, float, str]]] = []
    for ln in lines:
        if blocks and 0 <= ln[0] - blocks[-1][-1][0] <= 2.0 * ln[2]:
            blocks[-1].append(ln)
        else:
            blocks.append([ln])
    for blk in blocks:
        text = plan_title_text(" ".join(t for _y, _x, _s, t in blk))
        if _TB_PLAN_RE.fullmatch(text):
            return text
    return ""


def plan_title_text(text: str) -> str:
    """A plan title made comparable: upper case, single spaces, without a
    part / area suffix ("- PART B", "- OVERALL", "(AREA A)"); "FOUNDATION/1ST
    FLOOR PLAN" reads as a foundation plan."""
    u = " ".join((text or "").upper().split())
    u = re.sub(r"\s*[-\u2013(]\s*(PART|AREA|OVERALL|SECTOR|ZONE|BLDG|BUILDING)\b.*$", "", u)
    u = re.sub(r"^FOUNDATION\s*/.*$", "FOUNDATION PLAN", u)
    return u.strip()


# Big title-block text that is not a sheet title: project status or the
# sheet number (the real title is then printed small).
_TB_NOT_TITLE_RE = re.compile(
    r"^(?:NEW\s+)?CONSTRUCTION$|NOT\s+FOR\s+CONSTRUCTION|^\d+\s*PERCENT|\bCD\b|ISSUED|PERMIT|BID\s+SET|PRELIMINARY"
    r"|^[A-Z]{1,2}-?\d{1,2}(?:\.\d{1,3})?[A-Z]?$"
)


'''
s = s[:i] + new_fn + s[j:]
a = '''        small = " ".join(title_block_small_title(page).upper().split())
        m = _TB_PLAN_RE.fullmatch(small) if small else None
        if not m:
            return None, None, titles
        tb = small'''
b = '''        small = title_block_small_title(page) if _TB_NOT_TITLE_RE.search(tb) else ""
        m = _TB_PLAN_RE.fullmatch(small) if small else None
        if not m:
            return None, None, titles
        tb = small'''
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
