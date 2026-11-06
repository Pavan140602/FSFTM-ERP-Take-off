# OE-DELIVERY 2026-11-05-framing-rules: sheet titles split over two lines; schedule cache per file.
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


rep('''    best: tuple[str | None, int | None] = (None, None)
    for t in titles:
        u = " ".join((t or "").upper().split())
        m = _TITLE_RE.search(u)
        if not m:
            continue''', '''    best: tuple[str | None, int | None] = (None, None)
    # Title blocks often break a title over two lines ("1ST FLOOR SHEAR" /
    # "WALL PLAN"): try each line joined with the next one first.
    cands = [f"{a} {b}" for a, b in zip(titles, titles[1:])] + list(titles)
    wall_nolevel = False
    for t in cands:
        u = " ".join((t or "").upper().split())
        if len(u) > 60 or u.startswith(("SEE ", "REFER")) or "SIM" in u.split():
            continue
        m = _TITLE_RE.search(u)
        if not m:
            continue''')
rep('''        if "WALL" in kind_txt:
            return ("walls", lvl or 1)''', '''        if "WALL" in kind_txt:
            if lvl is None:
                wall_nolevel = True
                continue
            return ("walls", lvl)''')
rep('''                best = ("framing", lvl)
    return best
''', '''                best = ("framing", lvl)
    if best[0] is None and wall_nolevel:
        return ("walls", 1)
    return best


_SCHED_CACHE: dict[tuple[str, int, int], dict[str, Any]] = {}


def document_schedules(pdf: Any, path: str | None) -> dict[str, Any]:
    """All schedules of a drawing set, read once per file (about 2 s for a
    sheet with schedules) and kept for later runs.

    Returns ``{"schedules": merged, "rects": {page_index: [rect, ...]}}``."""
    import os

    key = None
    if path:
        try:
            st = os.stat(path)
            key = (str(path), int(st.st_size), int(st.st_mtime))
        except OSError:
            key = None
    if key and key in _SCHED_CACHE:
        return _SCHED_CACHE[key]
    parts: list[dict[str, dict[str, Any]]] = []
    rects: dict[int, list[tuple[float, float, float, float]]] = {}
    for i in range(pdf.page_count):
        page = pdf[i]
        try:
            if not page.search_for("SCHEDULE"):
                continue
            sc, rc = read_schedules_fast(page)
        except Exception:
            continue
        if sc:
            parts.append(sc)
        if rc:
            rects[i] = rc
    res = {"schedules": merge_schedules(parts), "rects": rects}
    if key:
        if len(_SCHED_CACHE) > 16:
            _SCHED_CACHE.pop(next(iter(_SCHED_CACHE)))
        _SCHED_CACHE[key] = res
    return res
''')
P.write_text(s, encoding="utf-8")
print("ok")
