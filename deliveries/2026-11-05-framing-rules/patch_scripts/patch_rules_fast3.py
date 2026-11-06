# OE-DELIVERY 2026-11-05-framing-rules: repeated schedule sheets borrow the table outlines.
from pathlib import Path
import sys

P = Path(sys.argv[1]) / "backend/app/modules/takeoff/framing_rules.py"
s = P.read_text(encoding="utf-8")
old = '''    done_titles: set[str] = set()
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
        done_titles |= titles'''
new = '''    done_titles: set[str] = set()
    read_pages: list[tuple[set[tuple[str, int, int]], int]] = []
    for i in range(pdf.page_count):
        page = pdf[i]
        try:
            found = schedule_titles(page)
            titles = {t for t, _r in found}
            if not titles:
                continue
            spots = {(t, int(r.x0 // 8), int(r.y0 // 8)) for t, r in found}
            # Plan sheets repeat the same schedules in the same places: read
            # each set once and give the repeat the same table outlines.
            if titles <= done_titles:
                twin = next((j for sp, j in read_pages if spots <= sp), None)
                if twin is not None:
                    if twin in rects:
                        rects[i] = list(rects[twin])
                    continue
            sc, rc = read_schedules_fast(page)
        except Exception:
            continue
        read_pages.append((spots, i))
        done_titles |= titles'''
if s.count(old) != 1:
    print("ANCHOR FAIL")
    sys.exit(1)
s = s.replace(old, new)
P.write_text(s, encoding="utf-8")
print("ok")
