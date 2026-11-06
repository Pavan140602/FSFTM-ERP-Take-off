# OE-DELIVERY 2026-11-05-framing-rules: follow each arrow to its arrowhead tips (the walls).
from pathlib import Path
import sys

A = Path(sys.argv[1]) / "backend/app/modules/takeoff/auto_takeoff.py"
s = A.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if s.count(old) != 1:
        print("ANCHOR FAIL", s.count(old), old[:120])
        sys.exit(1)
    s = s.replace(old, new)


rep('''    fsched: dict[str, Any] = field(default_factory=dict)
''', '''    fsched: dict[str, Any] = field(default_factory=dict)
    # All drawn pieces down to arrowhead size (framing rules only).
    fine: list[Any] = field(default_factory=list)
    fine_index: "SegIndex | None" = None
''')

rep('''        m.fsched = doc["schedules"]
        if m.kind:''', '''        m.fsched = doc["schedules"]
        if m.kind:
            try:
                m.fine = page_segments(page, min_len=3.0)
                m.fine_index = SegIndex(m.fine)
            except Exception:
                m.fine, m.fine_index = [], None''')

# replace the face-cast block with arrow walking
start = s.index("    # The arrows stop at (or just short of) the walls: the distribution runs")
end = s.index("    s_hi += _face(p_hi[0], p_hi[1], jx, jy, dist_ang, True)") + len("    s_hi += _face(p_hi[0], p_hi[1], jx, jy, dist_ang, True)")
s = s[:start] + '''    # The arrow lines continue in arrowhead pieces up to the walls: follow
    # them to the tips. The distribution then spans wall to wall and the
    # members reach their bearing walls.
    reach = 3.0 * upf
    d_lo -= _walk_arrow(model, dist, -dx, -dy, reach)
    d_hi += _walk_arrow(model, dist, dx, dy, reach)
    s_lo -= _walk_arrow(model, span, -jx, -jy, reach)
    s_hi += _walk_arrow(model, span, jx, jy, reach)''' + s[end:]

rep('''

def _series_from_leader(''', '''

def _walk_arrow(model: PageModel, line: tuple[float, float, float, float], ux: float, uy: float, max_ext: float) -> float:
    """How far a drawn line continues past its end (direction ``ux, uy``)
    in short pieces - arrowheads, half arrows - before a gap."""
    if model.fine_index is None:
        return 0.0
    # Line end in the walking direction and the line's own axis.
    e0 = (line[0], line[1])
    e1 = (line[2], line[3])
    px, py = e1 if (e1[0] - e0[0]) * ux + (e1[1] - e0[1]) * uy >= 0 else e0
    ext = 0.0
    for _ in range(16):
        grown = ext
        ex, ey = px + ux * ext, py + uy * ext
        for i in model.fine_index.near(ex - 6, ey - 6, ex + 6, ey + 6):
            sg = model.fine[i]
            for ax, ay, bx, by in ((sg[0], sg[1], sg[2], sg[3]), (sg[2], sg[3], sg[0], sg[1])):
                ta = (ax - px) * ux + (ay - py) * uy
                tb = (bx - px) * ux + (by - py) * uy
                if tb <= ta or ta > ext + 2.5 or ta < ext - 12:
                    continue
                ln = math.hypot(bx - ax, by - ay)
                if ln < 1.0 or (tb - ta) / ln < 0.9:
                    continue
                if abs((ax - px) * -uy + (ay - py) * ux) > 4 or abs((bx - px) * -uy + (by - py) * ux) > 4:
                    continue
                grown = max(grown, tb)
        if grown <= ext + 0.5 or grown > max_ext:
            break
        ext = grown
    return ext


def _series_from_leader(''')
A.write_text(s, encoding="utf-8")
print("ok")
