"""Probe: rows of short evenly spaced ticks per colour = hatched wall runs."""
import collections
import math
import sys

import pymupdf

path, pno = sys.argv[1], int(sys.argv[2])
out = sys.argv[3] if len(sys.argv) > 3 else None
page = pymupdf.open(path)[pno - 1]
ticks = collections.defaultdict(list)
for dr in page.get_drawings():
    c = dr.get("color")
    if not c:
        continue
    k = tuple(round(x, 2) for x in c)
    for it in dr["items"]:
        if it[0] != "l":
            continue
        a, b = it[1], it[2]
        L = math.hypot(b.x - a.x, b.y - a.y)
        if 2.0 <= L <= 16.0 and (abs(a.x - b.x) < 0.05 or abs(a.y - b.y) < 0.05):
            ticks[k].append((a.x, a.y, b.x, b.y, L))
for k, ts in sorted(ticks.items(), key=lambda kv: -len(kv[1])):
    # group: vertical ticks (x const) in a row along x, keyed by (round(y_mid), length)
    rows = collections.defaultdict(list)
    for x0, y0, x1, y1, L in ts:
        if abs(x0 - x1) < 0.05:  # vertical tick -> horizontal wall
            rows[("H", round(min(y0, y1), 0), round(L, 0))].append(x0)
        else:
            rows[("V", round(min(x0, x1), 0), round(L, 0))].append(y0)
    runs = []
    for key, pos in rows.items():
        pos = sorted(set(round(p, 1) for p in pos))
        if len(pos) < 4:
            continue
        gaps = [b - a for a, b in zip(pos, pos[1:])]
        med = sorted(gaps)[len(gaps) // 2]
        # split at gaps > 2.5 * med
        start = pos[0]
        n = 1
        for a, b in zip(pos, pos[1:]):
            if b - a > 2.5 * med:
                if n >= 4:
                    runs.append((key, start, a, med, n))
                start, n = b, 1
            else:
                n += 1
        if n >= 4:
            runs.append((key, start, pos[-1], med, n))
    tot = sum(r[2] - r[1] for r in runs)
    print(k, "ticks", len(ts), "runs", len(runs), "len", round(tot), "spacing", collections.Counter(round(r[3], 1) for r in runs).most_common(3), "width", collections.Counter(r[0][2] for r in runs).most_common(3))

if out:
    sh = page.new_shape()
    for k, ts in ticks.items():
        pass
    page.get_pixmap(dpi=72).save(out)
