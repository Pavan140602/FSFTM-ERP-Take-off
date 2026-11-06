# OE-DELIVERY 2026-11-05-framing-rules: read only real schedule titles, skip repeated sheets.
from pathlib import Path
import sys

P = Path(sys.argv[1]) / "backend/app/modules/takeoff/framing_rules.py"
s = P.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if s.count(old) != 1:
        print("ANCHOR FAIL", s.count(old), old[:120])
        sys.exit(1)
    s = s.replace(old, new)


rep('''    hits = page.search_for("SCHEDULE")
    if not hits:
        return {}, []''', '''    hits = [r for _t, r in schedule_titles(page)]
    if not hits:
        return {}, []''')

rep('''

_SCHED_CACHE: dict''', '''

_SCHED_TITLE_RE = re.compile(r"SCHEDULE")
_SCHED_NOT_TITLE = re.compile(r"\\b(SEE|REF\\.?|PER|REFER|&|AND|SCHEDULED)\\b")


def schedule_titles(page) -> list[tuple[str, Any]]:
    """Title lines of schedule tables ('CFMF JOIST SCHEDULE',
    'W1 - WALL FRAMING SCHEDULE', 'SHEAR WALL SCHEDULE - SW1'), not notes
    that only point at one ('SEE SCHEDULE', 'REF. SCHEDULE')."""
    import pymupdf

    out: list[tuple[str, Any]] = []
    try:
        d = page.get_text("dict")
    except Exception:
        return out
    for b in d.get("blocks", []):
        for ln in b.get("lines", []):
            spans = ln.get("spans") or []
            if not spans:
                continue
            t = " ".join(" ".join(sp.get("text", "") for sp in spans).upper().split())
            if "SCHEDULE" not in t or len(t) > 48 or _SCHED_NOT_TITLE.search(t):
                continue
            if max(sp.get("size", 0) for sp in spans) < 11:
                continue
            out.append((t, pymupdf.Rect(ln["bbox"])))
    return out


_SCHED_CACHE: dict''')

rep('''    for i in range(pdf.page_count):
        page = pdf[i]
        try:
            if not page.search_for("SCHEDULE"):
                continue
            sc, rc = read_schedules_fast(page)
        except Exception:
            continue''', '''    done_titles: set[str] = set()
    for i in range(pdf.page_count):
        page = pdf[i]
        try:
            titles = {t for t, _r in schedule_titles(page)}
            # Plan sheets repeat the same schedules: read each set once.
            if not titles or titles <= done_titles:
                continue
            sc, rc = read_schedules_fast(page)
        except Exception:
            continue
        done_titles |= titles''')
P.write_text(s, encoding="utf-8")
print("ok")
