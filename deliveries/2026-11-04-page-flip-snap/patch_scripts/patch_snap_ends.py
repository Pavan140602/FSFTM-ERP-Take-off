# OE-DELIVERY 2026-11-04-snap-ends: member ends land exactly on the column centre or the
# framing line they stop at (moved only along the member, so it stays straight).
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new):
    global s
    if s.count(old) != 1:
        print('ANCHOR FAIL', s.count(old), old[:140])
        sys.exit(1)
    s = s.replace(old, new)


FN = '''

# ── precise member ends (OE-DELIVERY 2026-11-04-snap-ends) ─────────────


def snap_member_ends(items: list[dict[str, Any]], col_reach: float = 16.0, col_perp: float = 4.5, line_reach: float = 10.0) -> int:
    """Pull each end of a beam / joist / truss line onto the column centre or
    the crossing framing line it stops at, so lengths read centre-to-centre.

    An end only moves along its own member (the line stays straight), only
    to a column whose centre sits on the member's line (within ``col_perp``)
    and within ``col_reach`` of the end, else to the crossing of a framing
    line within ``line_reach``. Returns how many ends moved.
    """
    cols = [(float(p[0]), float(p[1])) for it in items if it.get("category") == "columns" for p in (it.get("points") or [])]
    members = [
        it for it in items
        if it.get("kind") == "line" and it.get("category") in ("beams", "joists", "trusses", "other")
        and not it.get("generated") and len(it.get("points") or []) == 2
    ]
    framing = [it for it in items if it.get("kind") == "line" and it.get("category") in ("beams", "walls") and len(it.get("points") or []) == 2]
    moved = 0
    for it in members:
        (x1, y1), (x2, y2) = it["points"]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        if L < 20:
            continue
        ux, uy = dx / L, dy / L
        ends = [[x1, y1], [x2, y2]]
        for k, (px, py) in enumerate(((x1, y1), (x2, y2))):
            best: tuple[float, float] | None = None  # (|shift|, signed shift along the member)
            for cx, cy in cols:
                along = (cx - px) * ux + (cy - py) * uy
                perp = abs(-(cx - px) * uy + (cy - py) * ux)
                if perp <= col_perp and abs(along) <= col_reach and (best is None or abs(along) < best[0]):
                    best = (abs(along), along)
            if best is None:
                for f in framing:
                    if f is it:
                        continue
                    (ax, ay), (bx, by) = f["points"]
                    fx, fy = bx - ax, by - ay
                    fl = math.hypot(fx, fy)
                    if fl < 20:
                        continue
                    cos = abs(ux * fx / fl + uy * fy / fl)
                    if cos > 0.7:
                        continue  # nearly parallel: not a support
                    den = ux * fy - uy * fx
                    if abs(den) < 1e-9:
                        continue
                    t = ((ax - px) * fy - (ay - py) * fx) / den  # along the member from this end
                    u = ((ax - px) * uy - (ay - py) * ux) / den  # along the framing line
                    if abs(t) <= line_reach and -0.02 * fl <= u <= fl * 1.02 and (best is None or abs(t) < best[0]):
                        best = (abs(t), t)
            if best is not None and best[0] > 0.25:
                # never flip or collapse the member
                new_len = L + (best[1] if k == 1 else -best[1])
                if new_len < 0.5 * L:
                    continue
                ends[k] = [px + best[1] * ux, py + best[1] * uy]
                moved += 1
        it["points"] = [[_r(ends[0][0]), _r(ends[0][1])], [_r(ends[1][0]), _r(ends[1][1])]]
    return moved
'''

rep('''# ── driver ────────────────────────────────────────────────────────────''',
    FN.strip('\n') + '''


# ── driver ────────────────────────────────────────────────────────────''')
rep('''    items = _dedupe_items(items)
    assign_roles(items, model, specs)''', '''    items = _dedupe_items(items)
    snap_member_ends(items)
    assign_roles(items, model, specs)''')
P.write_text(s, encoding='utf-8')
print('ok')
