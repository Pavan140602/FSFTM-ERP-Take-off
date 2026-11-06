"""Detail (zoom) scan for columns and beams.

OE-DELIVERY 2026-11-06-zoom-scan

What an estimator does on a busy sheet: zoom in and walk the plan area by
area, checking every small symbol and every heavy line, not only the ones
that were easy to see zoomed out.  The first pass only accepts straight,
upright rectangles that repeat at least three times; this pass reads the
sheet at full detail:

* every closed small shape, drawn any way (one rectangle, four loose lines,
  a rotated square along a curved wall, rounded corners, a circle);
* every stroke, curves included (flattened into short chords);
* the plan is walked in tiles (about 3 in of paper each) and every shape in
  the tile is judged on its own evidence: a column is a small closed shape
  that framing members run into, or that has the same look as a column
  already confirmed on the sheet.

Deck-span arrows and other filled symbol parts are recognised and never
counted as columns.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

TILE = 216.0  # 3 in of paper
_EPS = 0.6
# Sheet references printed in section / detail markers: S6.11, S501, A-301.
_REF_RE = re.compile(r"^(?:[A-Z]{1,2}-?\d{1,2}\.\d{1,3}[A-Z]?|[A-Z]{1,2}-?\d{3,4}[A-Z]?)$")


@dataclass
class Shape:
    cx: float
    cy: float
    w: float  # long side of the smallest enclosing rectangle
    h: float  # short side
    angle: float  # long side, degrees folded to (-90, 90]
    bbox: tuple[float, float, float, float]
    filled: bool
    dark_fill: bool
    stroked: bool
    width: float  # pen width of the outline
    ratio: float  # polygon area / enclosing rectangle area
    did: int  # drawing index (-1 when assembled from loose lines)
    pen: tuple[int, int, int] | None = None

    @property
    def size(self) -> float:
        return self.w

    @property
    def aspect(self) -> float:
        return self.w / max(self.h, 0.1)

    @property
    def kind(self) -> str | None:
        if self.ratio >= 0.86 and self.aspect <= 1.8:
            return "square"
        if 0.7 <= self.ratio < 0.86 and self.aspect <= 1.15:
            return "round"
        return None


@dataclass
class DetailSheet:
    shapes: list[Shape] = field(default_factory=list)
    segs: list[tuple] = field(default_factory=list)  # (x1, y1, x2, y2, len, width, pen, did)
    filled: list[tuple[tuple[float, float, float, float], int, bool]] = field(default_factory=list)
    words: list[tuple[float, float, float, float]] = field(default_factory=list)  # every word's box on the sheet
    index: Any = None
    tiles: int = 0


# ── geometry helpers ──────────────────────────────────────────────────


def _xf(matrix, x: float, y: float) -> tuple[float, float]:
    if matrix is None:
        return float(x), float(y)
    a, b, c, d, e, f = (float(v) for v in matrix)
    return a * x + c * y + e, b * x + d * y + f


def _bezier(p0, p1, p2, p3, n: int = 8) -> list[tuple[float, float]]:
    out = []
    for k in range(1, n + 1):
        t = k / n
        u = 1 - t
        out.append((
            u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
        ))
    return out


def _hull(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _poly_area(pts: list[tuple[float, float]]) -> float:
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _min_rect(pts: list[tuple[float, float]]) -> tuple[float, float, float] | None:
    """(long side, short side, angle of long side) of the smallest
    enclosing rectangle."""
    hull = _hull(pts)
    if len(hull) < 3:
        return None
    best = None
    for (x1, y1), (x2, y2) in zip(hull, hull[1:] + hull[:1]):
        ang = math.atan2(y2 - y1, x2 - x1)
        c, s = math.cos(ang), math.sin(ang)
        us = [x * c + y * s for x, y in hull]
        vs = [-x * s + y * c for x, y in hull]
        a, b = max(us) - min(us), max(vs) - min(vs)
        if best is None or a * b < best[0]:
            best = (a * b, a, b, ang)
    _, a, b, ang = best
    if b > a:
        a, b, ang = b, a, ang + math.pi / 2
    deg = (math.degrees(ang) + 90.0) % 180.0 - 90.0
    return a, b, deg


def _dark(fill) -> bool:
    if not fill:
        return False
    if len(fill) == 4:
        c, m, y, k = fill
        fill = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return max(float(v) for v in fill[:3]) < 0.35


def _pen(color) -> tuple[int, int, int] | None:
    if color is None:
        return None
    if len(color) == 1:
        color = (color[0],) * 3
    elif len(color) == 4:
        c, m, y, k = color
        color = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return tuple(int(round(float(v) * 20)) for v in color[:3])  # type: ignore[return-value]


def _shape_from(points: list[tuple[float, float]], drawing, did: int, ordered: bool = True) -> Shape | None:
    if len(points) < 4:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    if max(bbox[2] - bbox[0], bbox[3] - bbox[1]) > 44 or max(bbox[2] - bbox[0], bbox[3] - bbox[1]) < 3:
        return None
    mr = _min_rect(points)
    if mr is None:
        return None
    a, b, ang = mr
    if b < 1.5:
        return None
    area = _poly_area(points) if ordered else _poly_area(_hull(points))
    ratio = area / max(a * b, 1e-6)
    fill = drawing.get("fill") if drawing is not None else None
    color = drawing.get("color") if drawing is not None else (0, 0, 0)
    return Shape(
        cx=(bbox[0] + bbox[2]) / 2.0,
        cy=(bbox[1] + bbox[3]) / 2.0,
        w=a,
        h=b,
        angle=ang,
        bbox=bbox,
        filled=fill is not None,
        dark_fill=_dark(fill),
        stroked=color is not None,
        width=float((drawing or {}).get("width") or 0.0),
        ratio=min(ratio, 1.0),
        did=did,
        pen=_pen(color),
    )


# ── reading the sheet at full detail ──────────────────────────────────


def read_sheet(page, drawings: list | None = None, index_cls=None) -> DetailSheet:
    """Every closed small shape and every stroke (curves flattened) in
    display space."""
    matrix = page.rotation_matrix if getattr(page, "rotation", 0) else None
    if drawings is None:
        try:
            drawings = page.get_drawings()
        except Exception:
            drawings = []
    ds = DetailSheet()
    for did, drawing in enumerate(drawings):
        items = drawing.get("items") or []
        width = float(drawing.get("width") or 0.0)
        pen = _pen(drawing.get("color"))
        stroked = drawing.get("color") is not None
        chains: list[list[tuple[float, float]]] = []
        cur: list[tuple[float, float]] = []

        def push(pts: list[tuple[float, float]]) -> None:
            nonlocal cur
            if cur and math.hypot(cur[-1][0] - pts[0][0], cur[-1][1] - pts[0][1]) <= 0.05:
                cur.extend(pts[1:])
            else:
                if len(cur) >= 2:
                    chains.append(cur)
                cur = list(pts)
            # A loop that closes on itself ends there: symbols are often
            # drawn as two outlines in one path (double-drawn square).
            if (
                len(cur) >= 4
                and math.hypot(cur[-1][0] - cur[0][0], cur[-1][1] - cur[0][1]) <= _EPS
                and max(abs(q[0] - cur[0][0]) + abs(q[1] - cur[0][1]) for q in cur) >= 3.0
            ):
                chains.append(cur)
                cur = []

        for it in items:
            op = it[0]
            if op == "l":
                push([_xf(matrix, it[1].x, it[1].y), _xf(matrix, it[2].x, it[2].y)])
            elif op == "c":
                p0 = _xf(matrix, it[1].x, it[1].y)
                p1 = _xf(matrix, it[2].x, it[2].y)
                p2 = _xf(matrix, it[3].x, it[3].y)
                p3 = _xf(matrix, it[4].x, it[4].y)
                push([p0] + _bezier(p0, p1, p2, p3))
            elif op == "re":
                r = it[1]
                pts = [_xf(matrix, r.x0, r.y0), _xf(matrix, r.x1, r.y0), _xf(matrix, r.x1, r.y1), _xf(matrix, r.x0, r.y1)]
                if len(cur) >= 2:
                    chains.append(cur)
                cur = []
                chains.append(pts + [pts[0]])
            elif op == "qu":
                q = it[1]
                pts = [_xf(matrix, q.ul.x, q.ul.y), _xf(matrix, q.ur.x, q.ur.y), _xf(matrix, q.lr.x, q.lr.y), _xf(matrix, q.ll.x, q.ll.y)]
                if len(cur) >= 2:
                    chains.append(cur)
                cur = []
                chains.append(pts + [pts[0]])
        if len(cur) >= 2:
            chains.append(cur)

        filled = drawing.get("fill") is not None
        if filled:
            xs = [p[0] for ch in chains for p in ch]
            ys = [p[1] for ch in chains for p in ch]
            if xs:
                ds.filled.append(((min(xs), min(ys), max(xs), max(ys)), did, _dark(drawing.get("fill"))))
        open_pieces: list[tuple[tuple[float, float], tuple[float, float]]] = []
        for ch in chains:
            if stroked:
                for (x1, y1), (x2, y2) in zip(ch, ch[1:]):
                    ln = math.hypot(x2 - x1, y2 - y1)
                    if ln >= 0.5:
                        ds.segs.append((x1, y1, x2, y2, ln, width, pen, did))
            span = max(max(q[0] for q in ch) - min(q[0] for q in ch), max(q[1] for q in ch) - min(q[1] for q in ch))
            closed = len(ch) >= 4 and span >= 3.0 and (
                math.hypot(ch[0][0] - ch[-1][0], ch[0][1] - ch[-1][1]) <= 1.0
                or ((drawing.get("closePath") or filled) and len(chains) == 1)
            )
            if closed:
                pts = ch[:-1] if math.hypot(ch[0][0] - ch[-1][0], ch[0][1] - ch[-1][1]) <= 1.0 else ch
                sh = _shape_from(pts, drawing, did)
                if sh is not None:
                    ds.shapes.append(sh)
            elif len(open_pieces) < 4000:
                xs = [p[0] for p in ch]
                ys = [p[1] for p in ch]
                if max(xs) - min(xs) <= 44 and max(ys) - min(ys) <= 44:
                    open_pieces.extend(zip(ch, ch[1:]))
        # Outlines written as loose pieces in any order (CAD exports):
        # join them where their ends meet.
        if len(open_pieces) >= 4:
            for loop in _loops(open_pieces):
                sh = _shape_from(loop, drawing, did, ordered=False)
                if sh is not None:
                    ds.shapes.append(sh)
    ds.shapes.extend(_loose_rectangles(ds.segs))
    ds.shapes = _dedupe_shapes(ds.shapes)
    try:
        for w in page.get_text("words"):
            ax, ay = _xf(matrix, w[0], w[1])
            bx, by = _xf(matrix, w[2], w[3])
            ds.words.append((min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)))
    except Exception:
        pass
    if index_cls is not None:
        ds.index = index_cls([s[:7] for s in ds.segs], cell=32.0)
    return ds


def _loops(pieces: list[tuple[tuple[float, float], tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Closed loops made of loose pieces: connected groups where every
    joint joins exactly two pieces."""
    nodes: list[tuple[float, float]] = []
    grid: dict[tuple[int, int], list[int]] = {}

    def node(p: tuple[float, float]) -> int:
        kx, ky = int(math.floor(p[0] / 1.0)), int(math.floor(p[1] / 1.0))
        for gx in (kx - 1, kx, kx + 1):
            for gy in (ky - 1, ky, ky + 1):
                for n in grid.get((gx, gy), []):
                    if math.hypot(nodes[n][0] - p[0], nodes[n][1] - p[1]) <= 0.15:
                        return n
        nodes.append(p)
        grid.setdefault((kx, ky), []).append(len(nodes) - 1)
        return len(nodes) - 1

    edges: list[tuple[int, int]] = []
    seen_e: set[tuple[int, int]] = set()
    for a, b in pieces:
        na, nb = node(a), node(b)
        k = (min(na, nb), max(na, nb))
        if na != nb and k not in seen_e:  # a side written twice counts once
            seen_e.add(k)
            edges.append((na, nb))
    parent = list(range(len(nodes)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    deg = [0] * len(nodes)
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comps: dict[int, list[int]] = {}
    for n in range(len(nodes)):
        if deg[n]:
            comps.setdefault(find(n), []).append(n)
    out = []
    for members in comps.values():
        if len(members) >= 4 and all(deg[n] == 2 for n in members):
            out.append([nodes[n] for n in members])
    return out


def _loose_rectangles(segs: list[tuple]) -> list[Shape]:
    """Squares drawn as four separate lines (any rotation)."""
    short = [s for s in segs if 3.0 <= s[4] <= 40.0]
    if len(short) > 60000:
        return []
    grid: dict[tuple[int, int], list[int]] = {}

    def key(x: float, y: float) -> tuple[int, int]:
        return int(math.floor(x / 2.0)), int(math.floor(y / 2.0))

    for i, s in enumerate(short):
        for x, y in ((s[0], s[1]), (s[2], s[3])):
            grid.setdefault(key(x, y), []).append(i)

    def at(x: float, y: float, skip: int) -> list[tuple[int, tuple[float, float]]]:
        kx, ky = key(x, y)
        out = []
        for gx in (kx - 1, kx, kx + 1):
            for gy in (ky - 1, ky, ky + 1):
                for j in grid.get((gx, gy), []):
                    if j == skip:
                        continue
                    t = short[j]
                    if math.hypot(t[0] - x, t[1] - y) <= _EPS:
                        out.append((j, (t[2], t[3])))
                    elif math.hypot(t[2] - x, t[3] - y) <= _EPS:
                        out.append((j, (t[0], t[1])))
        return out

    def perp(a, b) -> bool:
        ax, ay = a[2] - a[0], a[3] - a[1]
        bx, by = b[2] - b[0], b[3] - b[1]
        return abs(ax * bx + ay * by) <= 0.08 * a[4] * b[4]

    found: list[Shape] = []
    seen: set[tuple[int, ...]] = set()
    for i, s in enumerate(short):
        if s[7] is not None and False:
            continue
        start, b = (s[0], s[1]), (s[2], s[3])
        for j, c in at(b[0], b[1], i):
            if not perp(s, short[j]):
                continue
            for k, d in at(c[0], c[1], j):
                if k == i or not perp(short[j], short[k]):
                    continue
                for m, e in at(d[0], d[1], k):
                    if m in (i, j) or not perp(short[k], short[m]):
                        continue
                    if math.hypot(e[0] - start[0], e[1] - start[1]) > _EPS:
                        continue
                    ids = tuple(sorted((i, j, k, m)))
                    if ids in seen:
                        continue
                    seen.add(ids)
                    if len({short[q][7] for q in ids}) == 1:
                        continue  # one drawing: already read as a closed path
                    sh = _shape_from([start, b, c, d], {"color": (0, 0, 0), "width": s[5]}, -1)
                    if sh is not None:
                        found.append(sh)
    return found


def _dedupe_shapes(shapes: list[Shape]) -> list[Shape]:
    shapes = sorted(shapes, key=lambda s: -s.w)
    out: list[Shape] = []
    grid: dict[tuple[int, int], list[int]] = {}
    for s in shapes:
        k = (int(s.cx // 8), int(s.cy // 8))
        dup = False
        for gx in (k[0] - 1, k[0], k[0] + 1):
            for gy in (k[1] - 1, k[1], k[1] + 1):
                for j in grid.get((gx, gy), []):
                    o = out[j]
                    if abs(o.cx - s.cx) < 1.2 and abs(o.cy - s.cy) < 1.2 and abs(o.w - s.w) < 1.5:
                        dup = True
                        # A filled copy under an outline: keep the fill flag.
                        if s.filled and not o.filled:
                            o.filled, o.dark_fill = True, s.dark_fill
                        if s.stroked and not o.stroked:
                            o.stroked, o.width = True, s.width
                        break
                if dup:
                    break
            if dup:
                break
        if not dup:
            grid.setdefault(k, []).append(len(out))
            out.append(s)
    return out


# ── zoom parts: the sheet split into areas checked one by one ─────────


def plan_area(model) -> tuple[float, float, float, float]:
    """The drawing area of the sheet: everything drawn, less the title
    block strip on the right and bottom and the border."""
    W, H = model.width, model.height
    x0, y0, x1, y1 = W * 0.01, H * 0.01, W * 0.90, H * 0.95
    xs: list[float] = []
    ys: list[float] = []
    for sg in model.segments:
        for x, y in ((sg[0], sg[1]), (sg[2], sg[3])):
            if x0 <= x <= x1 and y0 <= y <= y1:
                xs.append(x)
                ys.append(y)
    for lab in model.labels:
        if x0 <= lab.cx <= x1 and y0 <= lab.cy <= y1:
            xs.append(lab.cx)
            ys.append(lab.cy)
    if len(xs) < 4:
        return (x0, y0, x1, y1)
    xs.sort()
    ys.sort()
    # Trim stray marks at the very edges (border ticks, notes far away).
    k = max(0, int(0.002 * len(xs)))
    return (max(x0, xs[k] - 6), max(y0, ys[k] - 6), min(x1, xs[-1 - k] + 6), min(y1, ys[-1 - k] + 6))


def plan_parts(model, parts: int = 0) -> list[dict[str, Any]]:
    """Split the drawing area into parts to zoom into one by one (like an
    estimator zooming in Revu): 4, 6, 9, 12 or 16 parts, more for a crowded
    sheet. Each part has its ``core`` (what it owns, so nothing is counted
    twice) and its ``zoom`` area (core plus an overlap of about 2 ft, so a
    member crossing the line between two parts is still seen whole)."""
    ax0, ay0, ax1, ay1 = plan_area(model)
    aw, ah = max(ax1 - ax0, 1.0), max(ay1 - ay0, 1.0)
    if parts <= 0:
        busy = len(model.segments) + 6 * len(model.labels)
        if model.detail is not None:
            busy += len(model.detail.shapes) * 4
        parts = 4 if busy < 6000 else 6 if busy < 14000 else 9 if busy < 26000 else 12 if busy < 45000 else 16
    # Rows x columns closest to square parts.
    best = None
    for rows in range(1, parts + 1):
        if parts % rows:
            continue
        cols = parts // rows
        cw, ch = aw / cols, ah / rows
        score = max(cw / ch, ch / cw)
        if best is None or score < best[0]:
            best = (score, rows, cols)
    _, rows, cols = best
    upf = model.units_per_foot or 9.0
    ov = max(2.0 * upf, 12.0)
    out = []
    for r in range(rows):
        for c in range(cols):
            core = (ax0 + aw * c / cols, ay0 + ah * r / rows, ax0 + aw * (c + 1) / cols, ay0 + ah * (r + 1) / rows)
            # The outer parts own everything up to the sheet edge.
            core = (
                0.0 if c == 0 else core[0],
                0.0 if r == 0 else core[1],
                model.width + 1 if c == cols - 1 else core[2],
                model.height + 1 if r == rows - 1 else core[3],
            )
            zoom = (
                max(ax0, ax0 + aw * c / cols - ov),
                max(ay0, ay0 + ah * r / rows - ov),
                min(ax1, ax0 + aw * (c + 1) / cols + ov),
                min(ay1, ay0 + ah * (r + 1) / rows + ov),
            )
            out.append({"id": len(out) + 1, "row": r + 1, "col": c + 1, "core": core, "zoom": zoom, "grid": [rows, cols]})
    return out


def in_core(part: dict[str, Any], x: float, y: float) -> bool:
    c = part["core"]
    return c[0] <= x < c[2] and c[1] <= y < c[3]



# ── columns ───────────────────────────────────────────────────────────


def _pt_seg(px: float, py: float, s) -> float:
    dx, dy = s[2] - s[0], s[3] - s[1]
    L2 = dx * dx + dy * dy
    if L2 <= 1e-9:
        return math.hypot(px - s[0], py - s[1])
    t = max(0.0, min(1.0, ((px - s[0]) * dx + (py - s[1]) * dy) / L2))
    return math.hypot(px - (s[0] + t * dx), py - (s[1] + t * dy))


def _is_light(pen) -> bool:
    return pen is not None and min(pen) >= 12


def _member_dirs(sh: Shape, ds: DetailSheet, members: list[tuple[float, float, float, float]], heavy_w: float) -> set[int]:
    """Sides (45 degree bins, 0-7) from which heavy lines and taken-off
    members run into the shape. A beam running through counts on both
    sides; two beams meeting at a corner count twice too."""
    dirs: set[int] = set()

    def side(s) -> int:
        # Direction from the symbol centre to the far end of the line.
        fx, fy = max(((s[0], s[1]), (s[2], s[3])), key=lambda q: math.hypot(q[0] - sh.cx, q[1] - sh.cy))
        return int(round(math.degrees(math.atan2(fy - sh.cy, fx - sh.cx)) / 45.0)) % 8

    def sides(s) -> set[int]:
        out = {side(s)}
        # Passing straight through: both ends far out on opposite sides.
        d1 = math.hypot(s[0] - sh.cx, s[1] - sh.cy)
        d2 = math.hypot(s[2] - sh.cx, s[3] - sh.cy)
        if min(d1, d2) > sh.w:
            out.add(int(round(math.degrees(math.atan2(s[1] - sh.cy, s[0] - sh.cx)) / 45.0)) % 8)
            out.add(int(round(math.degrees(math.atan2(s[3] - sh.cy, s[2] - sh.cx)) / 45.0)) % 8)
        return out

    half = sh.w / 2.0
    # Members usually stop a little short of the column face (a clearance
    # gap drawn at plan scale): about one symbol width.
    reach = half + max(5.0, 0.8 * sh.w)
    pad = reach + 2.0
    if ds.index is not None:
        cand = ds.index.near(sh.cx - pad, sh.cy - pad, sh.cx + pad, sh.cy + pad)
    else:
        cand = range(len(ds.segs))
    for i in cand:
        s = ds.segs[i]
        if s[7] == sh.did or float(s[5] or 0.0) < heavy_w or _is_light(s[6]):
            continue
        if _pt_seg(sh.cx, sh.cy, s) > reach:
            continue
        # It must reach out of the symbol: the outline itself does not count.
        far = max(math.hypot(s[0] - sh.cx, s[1] - sh.cy), math.hypot(s[2] - sh.cx, s[3] - sh.cy))
        if far < half + max(2.0, 0.5 * sh.w):
            continue
        dirs |= sides(s)
    for m in members:
        if _pt_seg(sh.cx, sh.cy, (m[0], m[1], m[2], m[3])) <= reach:
            dirs |= sides(m)
    return dirs


def _overlap(a: tuple[float, float, float, float], w: tuple[float, float, float, float]) -> bool:
    """A word sits in the shape: its centre inside, or a third of it
    overlapping (a callout touching a column corner does not count)."""
    cx, cy = (w[0] + w[2]) / 2.0, (w[1] + w[3]) / 2.0
    if a[0] <= cx <= a[2] and a[1] <= cy <= a[3]:
        return True
    ix = max(0.0, min(a[2], w[2]) - max(a[0], w[0]))
    iy = max(0.0, min(a[3], w[3]) - max(a[1], w[1]))
    area = max((w[2] - w[0]) * (w[3] - w[1]), 1e-6)
    return ix * iy / area >= 0.33


def _edge_continues(sh: Shape, ds: DetailSheet) -> bool:
    """One of the shape's sides runs on past its corner as a line of the
    same weight: the box is a piece of a double-line wall (a wall end or a
    T junction), not a symbol standing on its own."""
    if ds.index is None:
        return False
    a = math.radians(sh.angle)
    ux, uy = math.cos(a), math.sin(a)  # long side
    vx, vy = -uy, ux
    edges = []
    for (dx, dy, hl, ex, ey) in ((vx, vy, sh.w / 2.0, ux, uy), (ux, uy, sh.h / 2.0, vx, vy)):
        for sign in (-1.0, 1.0):
            off = (sh.h / 2.0) if (dx, dy) == (vx, vy) else (sh.w / 2.0)
            mx, my = sh.cx + sign * dx * off, sh.cy + sign * dy * off
            edges.append((mx, my, ex, ey, hl))
    min_w = 0.5 * max(sh.width, 0.3)
    reach = sh.w + 4.0
    for i in ds.index.near(sh.cx - reach, sh.cy - reach, sh.cx + reach, sh.cy + reach):
        s = ds.segs[i]
        if s[7] == sh.did or float(s[5] or 0.0) < min_w or s[4] < 0.5 * sh.h:
            continue
        sx, sy = (s[2] - s[0]) / s[4], (s[3] - s[1]) / s[4]
        for mx, my, ex, ey, hl in edges:
            if abs(sx * ex + sy * ey) < 0.998:
                continue  # not parallel to this side
            perp = abs(-(s[0] - mx) * ey + (s[1] - my) * ex)
            if perp > 0.6:
                continue
            t1 = (s[0] - mx) * ex + (s[1] - my) * ey
            t2 = (s[2] - mx) * ex + (s[3] - my) * ey
            lo, hi = min(t1, t2), max(t1, t2)
            if lo > hl + 1.0 or hi < -hl - 1.0:
                continue  # elsewhere on the same line
            beyond = max(hi - hl, -hl - lo)
            if beyond >= max(2.0, 0.4 * sh.w):
                return True
    return False


def _crossed(sh: Shape, ds: DetailSheet) -> bool:
    """Both diagonals drawn across the box."""
    if ds.index is None:
        return False
    diag = math.hypot(sh.w, sh.h)
    angs = []
    for i in ds.index.near(*sh.bbox):
        s = ds.segs[i]
        if s[4] >= 0.6 * diag and _pt_seg(sh.cx, sh.cy, s) <= 1.5:
            a = _ang(s)
            if 15.0 <= abs(a) <= 75.0:
                angs.append(a)
    return any(a > 0 for a in angs) and any(a < 0 for a in angs)


def _grid_cross(sh: Shape, ds: DetailSheet) -> bool:
    """Two lines crossing near the middle of the shape (a column on a grid
    intersection)."""
    if ds.index is None:
        return False
    angs: list[float] = []
    # Grid lines are dashed: a dash may stop short of the centre, so test
    # the line it lies on (perpendicular distance) and that the dash
    # reaches into the symbol.
    r = max(1.5, 0.45 * sh.w)
    for i in ds.index.near(sh.cx - sh.w, sh.cy - sh.w, sh.cx + sh.w, sh.cy + sh.w):
        s = ds.segs[i]
        if s[7] == sh.did or s[4] < 0.3 * sh.w:
            continue
        dx, dy = s[2] - s[0], s[3] - s[1]
        perp = abs((sh.cx - s[0]) * dy - (sh.cy - s[1]) * dx) / max(s[4], 1e-6)
        if perp <= 1.0 and _pt_seg(sh.cx, sh.cy, s) <= sh.w * 0.75 + r:
            a = (math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) + 90.0) % 180.0 - 90.0
            if any(min(abs(a - b) % 180, 180 - abs(a - b) % 180) >= 60 for b in angs):
                return True
            angs.append(a)
    return False


def _arrow_part(sh: Shape, ds: DetailSheet) -> bool:
    """A filled block that is part of a larger filled symbol (deck-span or
    north arrow, section marker) - never a column."""
    if not sh.dark_fill:
        return False
    if sh.aspect > 1.2 and not sh.stroked:
        return True
    x0, y0, x1, y1 = sh.bbox
    for (r, did, dark) in ds.filled:
        if did == sh.did or not dark:
            continue
        if r[0] <= x1 + 1.0 and r[2] >= x0 - 1.0 and r[1] <= y1 + 1.0 and r[3] >= y0 - 1.0:
            # Touching another filled piece that is not just a copy of it.
            if abs((r[0] + r[2]) / 2 - sh.cx) > 1.0 or abs((r[1] + r[3]) / 2 - sh.cy) > 1.0:
                return True
    return False


def _heavy_width(ds: DetailSheet) -> float:
    ws = sorted(float(s[5] or 0.0) for s in ds.segs if s[4] >= 20 and not _is_light(s[6]) and (s[5] or 0) > 0)
    if not ws:
        return 0.5
    # Member lines are the heaviest common pen on a framing plan.
    hi = ws[int(0.75 * (len(ws) - 1))]
    return max(0.45, min(1.0, 0.6 * hi))


def scan_columns(
    model,
    ds: DetailSheet,
    found: list[dict[str, Any]],
    members: list[tuple[float, float, float, float]],
    name_at,
    *,
    seeded_only: bool = False,
    col_mark_re=None,
    parts: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], set[int], dict[str, Any]]:
    """Columns the first pass missed, and first-pass columns that are not
    columns (arrow parts). ``name_at(x, y)`` names a column at a point.

    ``seeded_only``: only shapes that look like a column already found on
    the sheet are accepted (foundation plans, where footings are drawn as
    squares too)."""
    W, H = model.width, model.height
    upf = model.units_per_foot or 0.0
    words = [(lab.cx, lab.cy, lab) for lab in model.labels]
    heavy_w = _heavy_width(ds)
    stats: dict[str, Any] = {"tiles": 0, "shapes_checked": 0, "added": 0, "removed": 0}

    def in_rects(x: float, y: float, pad: float = 0.0) -> bool:
        return any(r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad for r in model.schedule_rects)

    # Candidates: closed small shapes that could be a column symbol.
    cands: list[Shape] = []
    arrows: list[Shape] = []
    for sh in ds.shapes:
        if sh.kind is None or not (4.5 <= sh.w <= 30.0):
            continue
        if sh.cx > W * 0.92 or sh.cy > H * 0.95 or sh.cx < W * 0.01 or sh.cy < H * 0.01:
            continue
        if in_rects(sh.cx, sh.cy, 6):
            continue
        if _arrow_part(sh, ds):
            arrows.append(sh)
            continue
        if sh.stroked and not sh.filled and _is_light(sh.pen) and sh.w < 8.0:
            continue  # faint little box: background / existing linework
        if sh.filled and not sh.dark_fill and not sh.stroked:
            continue  # white knock-out behind text or under a symbol
        x0, y0, x1, y1 = sh.bbox
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y, _l in words) or any(
            _overlap((x0, y0, x1, y1), w) for w in ds.words
        ):
            continue  # text inside or across it: a tag box, bubble or text mask
        if sh.aspect > 1.3 and _crossed(sh, ds):
            continue  # box with an X: shaft / opening
        reach = max(sh.w, 10.0)
        if any(
            _REF_RE.match("".join(lab.text.split()))
            and not (col_mark_re and col_mark_re.match("".join(lab.text.split())))
            and math.hypot(lab.cx - sh.cx, lab.cy - sh.cy) <= 2.5 * reach
            for _x, _y, lab in words
        ):
            continue  # section / detail marker head next to its sheet number
        if any(
            len(lab.text) <= 4
            and not (col_mark_re and col_mark_re.match("".join(lab.text.split())))
            and math.hypot(lab.cx - sh.cx, lab.cy - sh.cy) <= reach
            for _x, _y, lab in words
        ):
            continue  # grid bubble / marker with a short mark beside it
        cands.append(sh)

    # Concentric outlines (double-drawn symbol): keep the outer one.
    cands.sort(key=lambda s: -s.w)
    uniq: list[Shape] = []
    for sh in cands:
        if any(abs(sh.cx - u.cx) < 2.0 and abs(sh.cy - u.cy) < 2.0 for u in uniq):
            continue
        uniq.append(sh)
    cands = uniq

    # First-pass columns checked again zoomed in: one on an arrow part, or
    # with a grid letter / tag text at its centre (a grid bubble), is removed.
    removed: set[int] = set()
    for i, c in enumerate(found):
        x, y = c["point"]
        if any(a.bbox[0] - 1 <= x <= a.bbox[2] + 1 and a.bbox[1] - 1 <= y <= a.bbox[3] + 1 for a in arrows):
            removed.add(i)
            continue
        for w in ds.words:
            if w[2] - w[0] > 30:
                continue  # a long word / sentence near a column is a callout
            if w[0] - 1 <= x <= w[2] + 1 and w[1] - 1 <= y <= w[3] + 1:
                removed.add(i)
                break
    kept = [c for i, c in enumerate(found) if i not in removed]

    # Seeds: the look of columns already confirmed on the sheet.
    seeds: list[Shape] = []
    for c in kept:
        x, y = c["point"]
        best = min(
            (s for s in cands if abs(s.cx - x) <= max(3.0, s.w / 2) and abs(s.cy - y) <= max(3.0, s.w / 2)),
            key=lambda s: math.hypot(s.cx - x, s.cy - y),
            default=None,
        )
        if best is not None:
            seeds.append(best)

    def like_seed(sh: Shape) -> bool:
        return any(
            abs(sh.w - s.w) <= 0.15 * s.w + 0.6
            and abs(sh.h - s.h) <= 0.15 * s.h + 0.6
            and sh.kind == s.kind
            and sh.dark_fill == s.dark_fill
            for s in seeds
        )

    huddle = min(36.0, 3.0 * upf) if upf else 36.0
    size_groups: dict[tuple[int, str], int] = {}
    for sh in cands:
        k = (int(round(sh.w / 1.5)), sh.kind or "")
        size_groups[k] = size_groups.get(k, 0) + 1

    taken = [tuple(c["point"]) for c in kept]
    added: list[dict[str, Any]] = []
    for part in (parts if parts is not None else plan_parts(model)):
        stats["tiles"] += 1
        c0, c1, c2, c3 = part["core"]
        tile = [s for s in cands if c0 <= s.cx < c2 and c1 <= s.cy < c3]
        for sh in tile:
            stats["shapes_checked"] += 1
            if any(math.hypot(sh.cx - x, sh.cy - y) <= max(4.0, sh.w * 0.75) for x, y in taken):
                continue
            # Boxes of about the same size huddled together are one
            # detail symbol or a legend; a smaller mark beside a column
            # (beam-end arrow, splice) does not make it one.
            near_other = min(
                (
                    math.hypot(sh.cx - o.cx, sh.cy - o.cy)
                    for o in cands
                    if o is not sh
                    and math.hypot(sh.cx - o.cx, sh.cy - o.cy) > 2.0
                    and 0.6 <= o.w / max(sh.w, 0.1) <= 1.67
                ),
                default=1e9,
            )
            if near_other < huddle and not like_seed(sh):
                continue  # several small boxes huddled: one detail symbol
            dirs = _member_dirs(sh, ds, members, heavy_w)
            group = size_groups.get((int(round(sh.w / 1.5)), sh.kind or ""), 0)
            seeded = like_seed(sh)
            if sh.did == -1 and group < 3 and not seeded:
                # A one-off rectangle made only by separate lines crossing
                # (walls, framing): no symbol was drawn there.
                ok = False
            elif seeded_only:
                ok = seeded and (len(dirs) >= 1 or sh.filled or sh.kind == "square")
            elif seeded:
                ok = len(dirs) >= 1
            elif sh.kind == "round":
                ok = False  # piles, bubbles, bolts: round only when a confirmed column looks the same
            elif group >= 3:
                ok = len(dirs) >= 1
            else:
                # Alone (or a pair): members from two directions, or a
                # beam running through it on a grid crossing.
                axes = {d % 4 for d in dirs}
                ok = len(axes) >= 2 or (len(dirs) >= 2 and _grid_cross(sh, ds))
            if not ok:
                continue
            if _edge_continues(sh, ds):
                continue  # a piece of a double-line wall
            named = name_at(sh.cx, sh.cy)
            named.update({
                "point": (sh.cx, sh.cy),
                "size": round(sh.w, 1),
                "zoom": True,
            })
            added.append(named)
            taken.append((sh.cx, sh.cy))
            stats["added"] += 1
    ds.tiles = stats["tiles"]
    stats["removed"] = len(removed)
    return added, removed, stats


# ── beams ─────────────────────────────────────────────────────────────


def _ang(s) -> float:
    return (math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) + 90.0) % 180.0 - 90.0


def _adiff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _same_pen(a, b) -> bool:
    if a[6] is not None and b[6] is not None and max(abs(x - y) for x, y in zip(a[6], b[6])) > 2:
        return False
    wa, wb = float(a[5] or 0), float(b[5] or 0)
    lo, hi = min(wa, wb), max(wa, wb)
    return hi <= 0.5 or (lo > 0 and hi / lo <= 1.5)


def trace_member(
    ds: DetailSheet,
    seed: int,
    stops: list[tuple[float, float, float]],
    *,
    max_turn: float = 25.0,
    max_len: float = 4000.0,
) -> list[tuple[float, float]]:
    """Follow a heavy line from segment ``seed`` both ways through joints
    (gently bending: curved beams), stopping at a column / support
    (``stops`` = (x, y, radius)). Returns the polyline."""
    segs = ds.segs
    s0 = segs[seed]
    used = {seed}

    def walk(px: float, py: float, prev_ang: float, prev) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        total = 0.0
        cur = prev
        while total < max_len:
            if any(math.hypot(px - x, py - y) <= r for x, y, r in stops):
                break
            best = None
            for j in ds.index.near(px - 1.2, py - 1.2, px + 1.2, py + 1.2):
                if j in used:
                    continue
                t = segs[j]
                if not _same_pen(cur, t):
                    continue
                if math.hypot(t[0] - px, t[1] - py) <= 1.0:
                    nxt = (t[2], t[3])
                elif math.hypot(t[2] - px, t[3] - py) <= 1.0:
                    nxt = (t[0], t[1])
                else:
                    continue
                turn = _adiff(_ang(t), prev_ang)
                if turn > max_turn:
                    continue
                if best is None or turn < best[0]:
                    best = (turn, j, nxt)
            if best is None:
                break
            _turn, j, nxt = best
            used.add(j)
            cur = segs[j]
            prev_ang = _ang(cur)
            total += cur[4]
            px, py = nxt
            out.append((px, py))
        return out

    a = (s0[0], s0[1])
    b = (s0[2], s0[3])
    fwd = walk(b[0], b[1], _ang(s0), s0)
    back = walk(a[0], a[1], _ang(s0), s0)
    return list(reversed(back)) + [a, b] + fwd


def simplify(pts: list[tuple[float, float]], tol: float = 0.8) -> list[tuple[float, float]]:
    """Douglas-Peucker: straight beams come back as two points, curved ones
    keep enough points to follow the curve."""
    if len(pts) <= 2:
        return pts

    def rec(lo: int, hi: int, keep: set[int]) -> None:
        if hi <= lo + 1:
            return
        a, b = pts[lo], pts[hi]
        far, idx = -1.0, -1
        for k in range(lo + 1, hi):
            d = _pt_seg(pts[k][0], pts[k][1], (a[0], a[1], b[0], b[1]))
            if d > far:
                far, idx = d, k
        if far > tol:
            keep.add(idx)
            rec(lo, idx, keep)
            rec(idx, hi, keep)

    keep = {0, len(pts) - 1}
    rec(0, len(pts) - 1, keep)
    return [pts[k] for k in sorted(keep)]


def poly_len(pts: Iterable[tuple[float, float]]) -> float:
    pts = list(pts)
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _dist_poly(px: float, py: float, pts: list[tuple[float, float]]) -> float:
    if len(pts) == 1:
        return math.hypot(px - pts[0][0], py - pts[0][1])
    return min(_pt_seg(px, py, (a[0], a[1], b[0], b[1])) for a, b in zip(pts, pts[1:]))


def _samples(pts: list[tuple[float, float]], step: float = 4.0) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        for k in range(n):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out.append(pts[-1])
    return out


def _covered(pts: list[tuple[float, float]], lines: list[list[tuple[float, float]]], tol: float = 6.0) -> float:
    """Share of a polyline already drawn by another line markup."""
    sm = _samples(pts)
    if not sm or not lines:
        return 0.0
    boxes = []
    for ln in lines:
        xs = [p[0] for p in ln]
        ys = [p[1] for p in ln]
        boxes.append((min(xs) - tol, min(ys) - tol, max(xs) + tol, max(ys) + tol, ln))
    hit = 0
    for x, y in sm:
        for b in boxes:
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and _dist_poly(x, y, b[4]) <= tol:
                hit += 1
                break
    return hit / len(sm)


def _trace(
    ds: DetailSheet,
    seed: int,
    stops: list[tuple[float, float, float]],
    used: set[int],
    *,
    max_turn: float = 25.0,
    gap: float = 5.0,
) -> list[tuple[float, float]]:
    """Follow a heavy member line both ways from segment ``seed``: through
    joints that bend gently (curved beams), across small breaks in the line,
    and stopping at a column (``stops`` = (x, y, radius))."""
    segs = ds.segs
    s0 = segs[seed]
    used.add(seed)

    def at_stop(x: float, y: float) -> bool:
        return any(math.hypot(x - sx, y - sy) <= r for sx, sy, r in stops)

    def walk(px: float, py: float, prev, back: bool) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        # Heading of travel.
        hx, hy = (prev[0] - prev[2], prev[1] - prev[3]) if back else (prev[2] - prev[0], prev[3] - prev[1])
        hl = math.hypot(hx, hy) or 1.0
        hx, hy = hx / hl, hy / hl
        steps = 0
        while steps < 5000:
            steps += 1
            if at_stop(px, py):
                break
            best = None
            for j in ds.index.near(px - gap, py - gap, px + gap, py + gap):
                if j in used:
                    continue
                t = segs[j]
                if not _same_pen(prev, t):
                    continue
                for (ax, ay), (bx, by) in (((t[0], t[1]), (t[2], t[3])), ((t[2], t[3]), (t[0], t[1]))):
                    d = math.hypot(ax - px, ay - py)
                    if d > gap:
                        continue
                    vx, vy = bx - ax, by - ay
                    vl = math.hypot(vx, vy) or 1.0
                    cos = (vx * hx + vy * hy) / vl
                    turn = math.degrees(math.acos(max(-1.0, min(1.0, cos))))
                    if d > 1.0:
                        # A jump across a break must stay on the line.
                        jx, jy = (ax - px) / d, (ay - py) / d
                        if turn > 8.0 or (jx * hx + jy * hy) < 0.97:
                            continue
                    elif turn > max_turn:
                        continue
                    score = (d > 1.0, turn, d)
                    if best is None or score < best[0]:
                        best = (score, j, (ax, ay), (bx, by))
            if best is None:
                break
            _sc, j, a, b = best
            used.add(j)
            prev = segs[j]
            if math.hypot(a[0] - px, a[1] - py) > 1.0:
                out.append(a)
            out.append(b)
            vx, vy = b[0] - a[0], b[1] - a[1]
            vl = math.hypot(vx, vy) or 1.0
            hx, hy = vx / vl, vy / vl
            px, py = b
        return out

    a = (s0[0], s0[1])
    b = (s0[2], s0[3])
    fwd = walk(b[0], b[1], s0, False)
    back = walk(a[0], a[1], s0, True)
    return list(reversed(back)) + [a, b] + fwd


def _snap_ends(pts: list[tuple[float, float]], cols: list[tuple[float, float, float]]) -> list[tuple[float, float]]:
    """Carry each end onto the centre of the column it stops at."""
    if len(pts) < 2:
        return pts
    pts = list(pts)
    for end, nxt in ((0, 1), (len(pts) - 1, len(pts) - 2)):
        ex, ey = pts[end]
        dx, dy = ex - pts[nxt][0], ey - pts[nxt][1]
        dl = math.hypot(dx, dy) or 1.0
        dx, dy = dx / dl, dy / dl
        best = None
        for cx, cy, size in cols:
            along = (cx - ex) * dx + (cy - ey) * dy
            perp = abs(-(cx - ex) * dy + (cy - ey) * dx)
            if -size <= along <= size / 2.0 + 12.0 and perp <= max(4.5, 0.75 * size):
                d = math.hypot(cx - ex, cy - ey)
                if best is None or d < best[0]:
                    best = (d, (cx, cy))
        if best is not None:
            pts[end] = best[1]
    return pts


def scan_beams(
    model,
    ds: DetailSheet,
    labels: list[tuple[Any, dict[str, Any]]],
    items: list[dict[str, Any]],
    cols: list[tuple[float, float, float]],
    *,
    unlabeled: bool = True,
    parts: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Beam lines the first pass missed.

    1. Every beam size label with no beam of that size beside it: the heavy
       line printed under / beside it is followed (curves included) from
       support to support.
    2. Heavy lines drawn with the same pen as the sheet's beams that run
       between columns but carry no size label: added as beams to name.

    Returns (new line entries, stats). Each entry: points, designation,
    label (Label or None), info, unlabeled flag."""
    upf = model.units_per_foot or 9.0
    heavy_w = _heavy_width(ds)
    stats = {"labels_checked": 0, "labelled_added": 0, "unlabelled_added": 0}
    if ds.index is None:
        return [], stats
    beam_lines = [
        [(float(p[0]), float(p[1])) for p in it["points"]]
        for it in items
        if it.get("kind") == "line" and it.get("category") in ("beams", "other", "joists", "trusses", "walls")
    ]
    stops = [(x, y, max(3.0, size / 2.0 + 1.0)) for x, y, size in cols]
    used: set[int] = set()
    out: list[dict[str, Any]] = []

    def heavy(s) -> bool:
        return float(s[5] or 0.0) >= heavy_w and not _is_light(s[6])

    # Pens of the beams already taken off: unlabelled lines must match.
    pens: dict[tuple, int] = {}
    for it in items:
        if it.get("category") != "beams" or it.get("kind") != "line":
            continue
        p0, p1 = it["points"][0], it["points"][-1]
        mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
        for j in ds.index.near(mx - 2, my - 2, mx + 2, my + 2):
            s = ds.segs[j]
            if s[4] >= 6 and heavy(s) and _pt_seg(mx, my, s) <= 2.0:
                k = (s[6], round(float(s[5] or 0.0), 2))
                pens[k] = pens.get(k, 0) + 1
    beam_pens = {k for k, n in pens.items() if n >= 2}

    min_len = max(18.0, 2.0 * upf)
    # Part by part, as zoomed in.
    labels = sorted(labels, key=lambda li: part_index(parts, li[0].cx, li[0].cy))
    cols = sorted(cols, key=lambda c: part_index(parts, c[0], c[1]))
    # Breaks in a drawn member line (text knock-outs, drafting gaps): about 1'-3".
    gap = max(5.0, 1.25 * upf)
    # A member drawn as two lines (flange edges) is one member: lines within
    # about 1 ft of an existing markup are the same one.
    cover_tol = max(6.0, 0.9 * upf)

    # 1. Labels without their beam.
    for lab, info in labels:
        des = info["designation"]
        if any(
            it.get("category") == "beams" and it.get("designation") == des
            and _dist_poly(lab.cx, lab.cy, [(float(p[0]), float(p[1])) for p in it["points"]]) <= 3.0 * lab.size
            for it in items
        ):
            continue
        stats["labels_checked"] += 1
        R = max(3.0 * lab.size, 14.0)
        cands = []
        for j in ds.index.near(lab.cx - R, lab.cy - R, lab.cx + R, lab.cy + R):
            s = ds.segs[j]
            if j in used or not heavy(s):
                continue
            d = _pt_seg(lab.cx, lab.cy, s)
            if d > R:
                continue
            # Printed along the member; a curved beam's label sits along
            # the chord, so a steeper piece of curve is a weaker match.
            off = _adiff(_ang(s), lab.angle)
            cands.append((off > 35.0, d, j))
        cands.sort()
        for _far, _d, j in cands[:8]:
            trial_used = set(used)
            pts = _trace(ds, j, stops, trial_used, gap=gap)
            pts = simplify(_snap_ends(pts, cols))
            if poly_len(pts) < min_len:
                continue
            if _dist_poly(lab.cx, lab.cy, pts) > R:
                continue
            if _covered(pts, beam_lines, cover_tol) > 0.5:
                continue
            used |= trial_used
            beam_lines.append(pts)
            out.append({"points": pts, "designation": des, "label": lab, "info": info, "unlabeled": False})
            stats["labelled_added"] += 1
            break

    # 2. Unlabelled heavy lines between columns, same pen as the beams.
    if unlabeled and beam_pens and cols:

        def supported(px: float, py: float) -> bool:
            if any(math.hypot(px - cx, py - cy) <= 1.0 for cx, cy, _s in cols):
                return True
            return any(_dist_poly(px, py, ln) <= 9.0 for ln in beam_lines)

        for x, y, size in cols:
            r = size / 2.0 + max(4.0, 0.6 * size) + 2.0
            for j in list(ds.index.near(x - r, y - r, x + r, y + r)):
                s = ds.segs[j]
                if j in used or not heavy(s) or (s[6], round(float(s[5] or 0.0), 2)) not in beam_pens:
                    continue
                if _pt_seg(x, y, s) > r:
                    continue
                far = max(math.hypot(s[0] - x, s[1] - y), math.hypot(s[2] - x, s[3] - y))
                if far < size:
                    continue  # part of the symbol
                trial_used = set(used)
                pts = _trace(ds, j, [st for st in stops if math.hypot(st[0] - x, st[1] - y) > 1.0], trial_used, gap=gap)
                pts = simplify(_snap_ends(pts, cols))
                if poly_len(pts) < max(min_len, 3.0 * upf):
                    continue
                # Both ends on a support: a column, or a beam already taken off.
                if not (supported(*pts[0]) and supported(*pts[-1])):
                    continue
                if _covered(pts, beam_lines, cover_tol) > 0.5:
                    continue
                used |= trial_used
                beam_lines.append(pts)
                # A size printed along it after all (its label was spent on
                # a neighbouring bay): use it.
                named = None
                for lab, info in labels:
                    R = max(3.0 * lab.size, 14.0)
                    if _dist_poly(lab.cx, lab.cy, pts) <= R:
                        k = min(range(len(pts) - 1), key=lambda q: _pt_seg(lab.cx, lab.cy, (pts[q][0], pts[q][1], pts[q + 1][0], pts[q + 1][1])))
                        seg = (pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1])
                        if _adiff(_ang(seg), lab.angle) <= 20.0:
                            d = _pt_seg(lab.cx, lab.cy, seg)
                            if named is None or d < named[0]:
                                named = (d, lab, info)
                if named is not None:
                    out.append({"points": pts, "designation": named[2]["designation"], "label": named[1], "info": named[2], "unlabeled": False})
                    stats["labelled_added"] += 1
                else:
                    out.append({"points": pts, "designation": "BEAM", "label": None, "info": None, "unlabeled": True})
                    stats["unlabelled_added"] += 1
    return out, stats


# ── joists / trusses ──────────────────────────────────────────────────


def part_index(parts: list[dict[str, Any]] | None, x: float, y: float) -> int:
    for k, part in enumerate(parts or []):
        if in_core(part, x, y):
            return k
    return 0


def _frame_at(
    ds: DetailSheet,
    px: float,
    py: float,
    angle: float,
    s_units: float,
    upf: float,
) -> list[tuple[float, float, float, float]]:
    """Members drawn parallel to ``angle`` that cross the probe through
    (px, py), read one by one at spacing ``s_units`` from the nearest one
    outwards until the spacing breaks (a support or the end of the bay)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    c_u = ux * px + uy * py
    c_n = nx * px + ny * py
    R = 40.0 * upf
    tol_u = 0.75 * upf
    buckets: dict[int, list[Any]] = {}
    for j in ds.index.near(px - R, py - R, px + R, py + R):
        s = ds.segs[j]
        if s[4] < 1.0 * upf or _adiff(_ang(s), angle) > 4.0:
            continue
        a1 = ux * s[0] + uy * s[1]
        a2 = ux * s[2] + uy * s[3]
        off = nx * (s[0] + s[2]) / 2.0 + ny * (s[1] + s[3]) / 2.0
        if abs(off - c_n) > R:
            continue
        b = buckets.setdefault(int(round(off / 0.75)), [off, []])
        b[1].append((min(a1, a2), max(a1, a2)))
    lines: list[tuple[float, float, float]] = []
    for off, spans in buckets.values():
        spans.sort()
        merged: list[list[float]] = []
        for lo, hi in spans:
            if merged and lo <= merged[-1][1] + 1.5 * upf:  # small breaks (text knock-outs)
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            if lo - tol_u <= c_u <= hi + tol_u and hi - lo >= 3.0 * upf:
                lines.append((off, lo, hi))
    if len(lines) < 3:
        return []
    lines.sort()
    k0 = min(range(len(lines)), key=lambda q: abs(lines[q][0] - c_n))
    if abs(lines[k0][0] - c_n) > 1.5 * s_units:
        return []  # nothing framed right here
    picked = [lines[k0]]
    for step in (1, -1):
        last = lines[k0][0]
        q = k0 + step
        while 0 <= q < len(lines):
            gap = abs(lines[q][0] - last)
            if gap < 0.75 * s_units:
                q += step  # an edge / double line: not the next member
                continue
            if gap > 1.3 * s_units:
                break  # spacing breaks: support or end of the bay
            picked.append(lines[q])
            last = lines[q][0]
            q += step
    if len(picked) < 3:
        return []
    picked.sort()
    return [(ux * lo + nx * off, uy * lo + ny * off, ux * hi + nx * off, uy * hi + ny * off) for off, lo, hi in picked]


def _line_dir_at(ds: DetailSheet, x: float, y: float, upf: float) -> float | None:
    """Direction of the member line a leader ends on."""
    best = None
    r = max(4.0, 0.6 * upf)
    for j in ds.index.near(x - r, y - r, x + r, y + r):
        s = ds.segs[j]
        if s[4] < 3.0 * upf:
            continue
        d = _pt_seg(x, y, s)
        if d <= r and (best is None or d < best[0]):
            best = (d, _ang(s))
    return best[1] if best else None


def scan_joists(
    model,
    ds: DetailSheet,
    labels: list[tuple[Any, dict[str, Any]]],
    items: list[dict[str, Any]],
    parts: list[dict[str, Any]] | None = None,
    leader_ends=None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Joist / truss callouts ("J-1", "1200S200-54 @ 4'-0" o.c.") that
    produced no members: zoomed in on the callout's part, the member lines
    are read one by one at the callout's spacing - across the callout
    itself, then at the end of its leader (``leader_ends(label)`` gives the
    leader tips, best first).

    Returns (entries, stats); each entry: label, info, lines (x0, y0, x1, y1)."""
    upf = model.units_per_foot or 0.0
    stats = {"callouts_checked": 0, "callouts_framed": 0, "members_added": 0}
    if not upf or ds.index is None:
        return [], stats
    labels = sorted(labels, key=lambda li: part_index(parts, li[0].cx, li[0].cy))
    out: list[dict[str, Any]] = []
    taken: list[list[tuple[float, float]]] = [
        [(float(p[0]), float(p[1])) for p in it["points"]]
        for it in items
        if it.get("category") in ("joists", "trusses") and len(it.get("points") or []) >= 2
    ]
    for lab, info in labels:
        sp_in = info.get("spacing_in")
        if not sp_in:
            continue
        s_units = sp_in / 12.0 * upf
        if s_units < 3.0:
            continue
        des = info["designation"]
        near = max(3.0 * upf, 2.0 * s_units)
        if any(
            it.get("category") in ("joists", "trusses") and it.get("designation") == des
            and len(it.get("points") or []) >= 2
            and _dist_poly(lab.cx, lab.cy, [(float(p[0]), float(p[1])) for p in it["points"]]) <= near
            for it in items
        ):
            continue
        stats["callouts_checked"] += 1
        probes: list[tuple[float, float, float]] = [(lab.cx, lab.cy, lab.angle)]
        if leader_ends is not None:
            try:
                for tip in list(leader_ends(lab))[:3]:
                    ang = _line_dir_at(ds, tip[0], tip[1], upf)
                    if ang is not None:
                        # The leader ends ON a member: the members run along it.
                        probes.append((tip[0], tip[1], ang))
            except Exception:
                pass
        segs: list[tuple[float, float, float, float]] = []
        for px, py, ang in probes:
            segs = _frame_at(ds, px, py, ang, s_units, upf)
            if segs:
                break
        if not segs:
            continue
        # Never a second copy of members already taken off.
        segs = [
            sg for sg in segs
            if not any(_dist_poly((sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0, t) <= 3.0 for t in taken)
        ]
        if len(segs) < 3:
            continue
        taken.extend([[(sg[0], sg[1]), (sg[2], sg[3])] for sg in segs])
        out.append({"label": lab, "info": info, "lines": segs})
        stats["callouts_framed"] += 1
        stats["members_added"] += len(segs)
    return out, stats


# ── deck ──────────────────────────────────────────────────────────────


def deck_bay(lab, lines: list[list[tuple[float, float]]], reach: float = 1600.0) -> list[tuple[float, float]] | None:
    """The bay a deck callout sits in, bounded by the beams taken off around
    it (curved and zoom-found ones included): the nearest member crossing a
    ray to the right, left, down and up."""

    def cast(dx: float, dy: float) -> float | None:
        best = None
        for ln in lines:
            for p, q in zip(ln, ln[1:]):
                ex, ey = q[0] - p[0], q[1] - p[1]
                L = math.hypot(ex, ey)
                if L < 1e-6:
                    continue
                if abs((ex * dx + ey * dy) / L) > 0.5:
                    continue  # running along the ray, not across it
                den = dx * ey - dy * ex
                if abs(den) < 1e-9:
                    continue
                t = ((p[0] - lab.cx) * ey - (p[1] - lab.cy) * ex) / den
                u = ((p[0] - lab.cx) * dy - (p[1] - lab.cy) * dx) / den
                if 2.0 < t <= reach and -0.01 <= u <= 1.01 and (best is None or t < best):
                    best = t
        return best

    r, l, d, u = cast(1, 0), cast(-1, 0), cast(0, 1), cast(0, -1)
    if None in (r, l, d, u):
        return None
    x0, x1, y0, y1 = lab.cx - l, lab.cx + r, lab.cy - u, lab.cy + d
    if (x1 - x0) < 40 or (y1 - y0) < 40:
        return None
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ── what is still not taken off, part by part ────────────────────────


def part_log(
    model,
    parts: list[dict[str, Any]],
    items: list[dict[str, Any]],
    missed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per zoomed part: what was taken off in it and what is still missing."""
    log = []
    for part in parts:
        counts: dict[str, int] = {}
        for it in items:
            pts = it.get("points") or []
            if not pts:
                continue
            if it.get("kind") == "count":
                n = sum(1 for p in pts if in_core(part, p[0], p[1]))
                if n:
                    counts[it["category"]] = counts.get(it["category"], 0) + n
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if it.get("kind") == "area":
                cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            else:
                mid = pts[len(pts) // 2] if len(pts) > 2 else ((xs[0] + xs[-1]) / 2.0, (ys[0] + ys[-1]) / 2.0)
                cx, cy = mid[0], mid[1]
            if in_core(part, cx, cy):
                counts[it["category"]] = counts.get(it["category"], 0) + 1
        miss = [m for m in missed if in_core(part, m["at"][0], m["at"][1])]
        z = part["zoom"]
        log.append({
            "part": part["id"],
            "row": part["row"],
            "col": part["col"],
            "rect": [round(v, 1) for v in z],
            "counts": counts,
            "missed": len(miss),
        })
    return log


def deck_legend(model, deck_info) -> tuple[dict[str, dict[str, Any]], list[tuple[float, float, float, float]]]:
    """Deck tags defined in a deck legend: a short mark (AD, BD, D1) with its
    deck description printed to its right. Returns ({tag: deck info},
    legend boxes). ``deck_info(text)`` classifies a deck description."""
    labels = model.labels
    tags: dict[str, dict[str, Any]] = {}
    boxes: list[tuple[float, float, float, float]] = []
    for lab in labels:
        t = "".join(lab.text.split()).upper()
        if not re.fullmatch(r"[A-Z]{1,3}\d{0,2}", t) or len(t) > 3:
            continue
        h = max(lab.size, 6.0)
        row = [
            o for o in labels
            if o is not lab and 0 < o.rect[0] - lab.rect[2] <= 30 * h and abs(o.cy - lab.cy) <= 2.5 * h
        ]
        if not row:
            continue
        text = " ".join(o.text for o in sorted(row, key=lambda o: (round(o.cy / h), o.rect[0])))
        info = deck_info(text)
        if not info:
            continue
        info = dict(info)
        info["legend_text"] = text
        tags.setdefault(t, info)
        xs = [lab.rect[0]] + [o.rect[2] for o in row]
        ys = [lab.rect[1]] + [o.rect[1] for o in row] + [lab.rect[3]] + [o.rect[3] for o in row]
        boxes.append((min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h))
    # The legend title belongs to the legend too.
    for lab in labels:
        if re.search(r"\bLEGEND\b|DECK\s+SCHEDULE|DECK\s+TYPES?", lab.text.upper()):
            boxes.append((lab.rect[0] - 160, lab.rect[1] - 10, lab.rect[2] + 300, lab.rect[3] + 260))
    return tags, boxes


# ── every column label must have its column ──────────────────────────

_COL_SIZE_RE = re.compile(r"^(?:HSS\s*(\d+(?:\.\d+)?)\s*X\s*(\d+(?:\.\d+)?)\s*X|W\s*\d+\s*X\s*\d+|PIPE\s*\d)", re.IGNORECASE)


def _underline_ends(lab, ds: DetailSheet) -> list[tuple[float, float]]:
    """Ends of the line a callout is written on (a diagonal leader with the
    text sitting on it) that run past the text: the far end is where it
    points."""
    if ds.index is None:
        return []
    a = math.radians(lab.angle)
    ux, uy = math.cos(a), math.sin(a)
    c_u = ux * lab.cx + uy * lab.cy
    half = max(abs((lab.rect[2] - lab.rect[0]) * ux) + abs((lab.rect[3] - lab.rect[1]) * uy), 1.0) / 2.0
    # Text width along its own direction (rotated text has a square-ish box).
    tw = 0.55 * len(lab.text) * lab.size
    half = max(half * 0.5, tw / 2.0)
    r = half + 6.0 * lab.size
    out = []
    heavy_w = _heavy_width(ds)
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 0.8 * half or _adiff(_ang(s), lab.angle) > 5.0:
            continue
        perp = abs(-(lab.cx - s[0]) * uy + (lab.cy - s[1]) * ux)
        if perp > 1.3 * lab.size:
            continue
        if float(s[5] or 0.0) >= heavy_w or s[4] > 6.0 * max(half, 10.0):
            continue  # a member line (a beam the size is printed on), not a leader
        # The text often fills the whole leader: its ends are where it points.
        out.extend([(s[0], s[1]), (s[2], s[3])])
    return out


def _on_member_line(lab, ds: DetailSheet) -> bool:
    """The text is printed along a long line (a beam): a member size, not
    a column callout."""
    if ds.index is None:
        return False
    a = math.radians(lab.angle)
    ux, uy = math.cos(a), math.sin(a)
    tw = 0.55 * len(lab.text) * lab.size
    r = 2.0 * lab.size
    heavy_w = _heavy_width(ds)
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 2.6 * tw / 2.0 or _adiff(_ang(s), lab.angle) > 5.0:
            continue
        if float(s[5] or 0.0) < heavy_w:
            continue  # a thin leader the size is written on, not a member
        perp = abs(-(lab.cx - s[0]) * uy + (lab.cy - s[1]) * ux)
        if perp <= 1.6 * lab.size and _pt_seg(lab.cx, lab.cy, s) <= 2.0 * lab.size:
            return True
    return False


def label_columns(
    model,
    ds: DetailSheet,
    found: list[tuple[float, float]],
    leader_ends=None,
) -> tuple[list[dict[str, Any]], int]:
    """Column size labels (HSS a x a, W, pipe) with no column at them: the
    leader - or the line the text is written on - is followed to its end and
    the small symbol drawn there is taken as the column. A beam label ends
    on a long member line, not on a small symbol, so it is never taken.
    Returns (columns: label, point, size; labels checked)."""
    W, H = model.width, model.height
    upf = model.units_per_foot or 9.0
    # A small symbol may sit a little way past the end of the leader.
    reach_tip = max(6.0, 1.5 * upf)
    out: list[dict[str, Any]] = []
    unresolved: list[Any] = []
    claims: list[tuple[Any, int]] = []
    checked = 0
    taken = list(found)
    n_found = len(found)
    # W sizes name columns only on a column sheet (foundation / column plan,
    # where square tube sizes outnumber W sizes); on a framing plan a W size
    # is a beam.
    n_sq = n_w = 0
    for lab in model.labels:
        t = "".join(lab.text.split()).upper()
        mm = _COL_SIZE_RE.match(t)
        if not mm:
            continue
        if t.startswith("W"):
            n_w += 1
        elif mm.group(1) and mm.group(1) == mm.group(2):
            n_sq += 1
    w_columns = n_sq > 0 and n_sq >= n_w
    for lab in model.labels:
        t = "".join(lab.text.split()).upper()
        m = _COL_SIZE_RE.match(t)
        if not m:
            continue
        if m.group(1) and m.group(2) and m.group(1) != m.group(2):
            continue  # rectangular HSS: a beam / brace size
        if t.startswith("W") and (not w_columns or _on_member_line(lab, ds)):
            continue  # a beam size
        if lab.cx > 0.9 * W or lab.cy > 0.95 * H:
            continue
        if any(r[0] - 4 <= lab.cx <= r[2] + 4 and r[1] - 4 <= lab.cy <= r[3] + 4 for r in model.schedule_rects):
            continue
        # Where the callout points: the line it is written on first, then
        # its leader(s).
        ends: list[tuple[float, float, float]] = [(x, y, 0.0) for x, y in _underline_ends(lab, ds)]
        if leader_ends is not None:
            try:
                ends.extend((x, y, 1000.0) for x, y in list(leader_ends(lab))[:4])  # leaders only when the text line points nowhere
            except Exception:
                pass
        checked += 1
        best = None
        for ex, ey, pen in ends:
            for sh in ds.shapes:
                if not (3.0 <= sh.w <= 20.0) or sh.aspect > 5.0 or sh.kind is None:
                    continue  # triangles (moment-connection marks), arrows
                if sh.filled and not sh.dark_fill and not sh.stroked:
                    continue  # text mask
                d = math.hypot(sh.cx - ex, sh.cy - ey) - sh.w / 2.0
                if d > reach_tip:
                    continue
                # Other text on the symbol rules it out; the callout's own
                # words do not (slanted text has a big square box).
                if any(
                    _overlap(sh.bbox, w)
                    for w in ds.words
                    if not (lab.rect[0] - 1 <= (w[0] + w[2]) / 2 <= lab.rect[2] + 1 and lab.rect[1] - 1 <= (w[1] + w[3]) / 2 <= lab.rect[3] + 1)
                ):
                    continue
                if best is None or d + pen < best[0]:
                    best = (d + pen, sh)
        if best is None:
            # A column found already at the end of the line the text is
            # written on (an I-shaped W column has no closed box): this
            # label names it.
            near_k = min(
                (
                    (math.hypot(x - ex, y - ey), k)
                    for k, (x, y) in enumerate(taken[:n_found])
                    for ex, ey, pn in ends
                ),
                default=None,
            )
            if near_k is not None and near_k[0] <= 14.0:
                claims.append((lab, near_k[1]))
                continue
            # No symbol where it points: unless a column already stands at
            # one of its ends, list it for the estimator.
            if not any(math.hypot(x - ex, y - ey) <= 20 for x, y in taken for ex, ey, _p in ends) and not any(
                max(lab.rect[0] - x, 0.0, x - lab.rect[2]) + max(lab.rect[1] - y, 0.0, y - lab.rect[3]) <= 14 for x, y in taken
            ):
                unresolved.append(lab)
            continue
        sh = best[1]
        hit = next((k for k, (x, y) in enumerate(taken) if math.hypot(sh.cx - x, sh.cy - y) <= max(4.0, sh.w * 0.75)), None)
        if hit is not None:
            if hit < n_found:
                claims.append((lab, hit))  # the column is there: this label names it
            continue
        out.append({"label": lab, "point": (sh.cx, sh.cy), "size": round(sh.w, 1)})
        taken.append((sh.cx, sh.cy))
    label_columns.unresolved = unresolved  # type: ignore[attr-defined]
    label_columns.claims = claims  # type: ignore[attr-defined]
    return out, checked


def leader_beams(model, ds: DetailSheet, items: list[dict[str, Any]], cols: list[tuple[float, float]]) -> set[int]:
    """Beam markups that are really a callout's leader: drawn on a thin line
    (not the beam pen), short, and ending at a column. Returns their indexes
    in ``items``."""
    if ds.index is None:
        return set()
    upf = model.units_per_foot or 9.0
    heavy_w = _heavy_width(ds)
    drop: set[int] = set()
    for i, it in enumerate(items):
        if it.get("category") != "beams" or it.get("kind") != "line" or it.get("source") == "zoom":
            continue
        pts = it.get("points") or []
        if len(pts) != 2:
            continue
        (x1, y1), (x2, y2) = pts
        L = math.hypot(x2 - x1, y2 - y1)
        if L > 6.0 * upf or L < 1.0:
            continue
        if not any(min(math.hypot(x1 - cx, y1 - cy), math.hypot(x2 - cx, y2 - cy)) <= 14.0 for cx, cy in cols):
            continue
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        ang = (math.degrees(math.atan2(y2 - y1, x2 - x1)) + 90.0) % 180.0 - 90.0
        # Any line of the beam pen alongside (a beam drawn heavy, the markup
        # sitting on its thin edge line) means it is a real beam.
        widths = []
        for t in (0.2, 0.35, 0.5, 0.65, 0.8):  # dashed beams: look along it
            sx, sy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            widths.extend(
                float(ds.segs[j][5] or 0.0)
                for j in ds.index.near(sx - 15, sy - 15, sx + 15, sy + 15)
                if _pt_seg(sx, sy, ds.segs[j]) <= 14.0 and _adiff(_ang(ds.segs[j]), ang) <= 5.0
            )
        if widths and max(widths) < heavy_w:
            drop.add(i)
    return drop


def symbol_at(ds: DetailSheet, x: float, y: float) -> list[float] | None:
    """Size and turn of the column symbol drawn at (x, y): [long side, short
    side, angle of the long side in degrees] in drawing units - so the
    viewer draws a wide flange or a rectangular tube the way it sits on the
    plan (OE-DELIVERY 2026-11-07-column-shapes)."""
    best = None
    for sh in ds.shapes:
        if not (3.0 <= sh.w <= 40.0) or sh.aspect > 4.0:
            continue
        d = math.hypot(sh.cx - x, sh.cy - y)
        if d > max(3.0, 0.5 * sh.w):
            continue
        # The drawn outline beats a white knock-out under it; the closest
        # centre wins, then the bigger outline (an I drawn round a web).
        mask = sh.filled and not sh.dark_fill and not sh.stroked
        score = (mask, round(d, 1), -sh.w)
        if best is None or score < best[0]:
            best = (score, sh)
    if best is None:
        return None
    sh = best[1]
    return [round(sh.w, 2), round(sh.h, 2), round(sh.angle, 1)]


# ── stud walls: full width, header areas, studs (OE-DELIVERY 2026-11-08-stud-walls) ──

_STUD_DEPTH_RE = re.compile(r"(?:^|[^\d])(\d{3,4})[STU]\d{3}", re.IGNORECASE)


def stud_depth_in(profile: str | None) -> float | None:
    """Stud depth in inches from an SSMA name: 600S200-68 -> 6.0, 362S162-33 -> 3.625."""
    m = _STUD_DEPTH_RE.search(profile or "")
    if not m:
        return None
    return int(m.group(1)) / 100.0


def wall_geometry(
    model,
    ds: DetailSheet,
    a: tuple[float, float],
    b: tuple[float, float],
    fallback_width: float | None,
) -> dict[str, Any]:
    """Read a wall run off the sheet, zoomed in: the two heavy face lines
    each side of it give its full width (and its true centre line), and the
    places where those faces stop - an opening, with only thin window / door
    lines across it - are the header areas.

    Returns {"width": units or None, "offset": shift of the centre line,
    "openings": [(t0, t1), ...] along a->b in units, "length": units}."""
    upf = model.units_per_foot or 9.0
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    out: dict[str, Any] = {"width": None, "offset": 0.0, "openings": [], "length": L}
    if L < 1e-6 or ds.index is None:
        return out
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -uy, ux
    ang = (math.degrees(math.atan2(uy, ux)) + 90.0) % 180.0 - 90.0
    reach = max(1.4 * upf, 10.0)
    x0, x1 = min(a[0], b[0]) - reach, max(a[0], b[0]) + reach
    y0, y1 = min(a[1], b[1]) - reach, max(a[1], b[1]) + reach
    heavy_w = _heavy_width(ds)
    faces: dict[int, list] = {}
    for j in ds.index.near(x0, y0, x1, y1):
        s = ds.segs[j]
        if s[4] < 1.0 or _adiff(_ang(s), ang) > 3.0 or _is_light(s[6]):
            continue
        off = ((s[0] + s[2]) / 2.0 - a[0]) * nx + ((s[1] + s[3]) / 2.0 - a[1]) * ny
        if abs(off) > reach:
            continue
        t1 = (s[0] - a[0]) * ux + (s[1] - a[1]) * uy
        t2 = (s[2] - a[0]) * ux + (s[3] - a[1]) * uy
        lo, hi = max(0.0, min(t1, t2)), min(L, max(t1, t2))
        if hi - lo <= 0.2:
            continue
        k = int(round(off / 0.6))
        f = faces.setdefault(k, [off, 0.0, [], 0.0])
        f[2].append((lo, hi, float(s[5] or 0.0)))
        f[1] += hi - lo
        f[3] = max(f[3], float(s[5] or 0.0))
    if not faces:
        return out
    # Faces: the two best-covered heavy-enough lines on opposite sides (or
    # the line the run sits on plus its partner) at a stud-wall spacing.
    cands = sorted(faces.values(), key=lambda f: -f[1])
    best = None
    lo_w, hi_w = 2.5 / 12.0 * upf, 16.0 / 12.0 * upf
    for i, fa in enumerate(cands[:8]):
        for fb in cands[i + 1:8]:
            w = abs(fa[0] - fb[0])
            if not (lo_w <= w <= hi_w):
                continue
            score = min(fa[1], fb[1])
            if score < 0.35 * L:
                continue
            if best is None or score > best[0]:
                best = (score, fa, fb)
    if best is None:
        out["width"] = fallback_width
        return out
    _, fa, fb = best
    out["width"] = abs(fa[0] - fb[0])
    out["offset"] = (fa[0] + fb[0]) / 2.0
    # Openings: where neither face is drawn with the wall's own pen - only
    # hairlines (window / door lines, background) run across an opening.
    face_segs = [
        seg
        for f in faces.values()
        if abs(f[0] - fa[0]) <= 0.7 or abs(f[0] - fb[0]) <= 0.7
        for seg in f[2]
    ]
    hair = min((w for _lo, _hi, w in face_segs), default=0.0)
    wall_pen = max(0.6 * heavy_w, 1.2 * hair + 1e-6)
    spans: list[tuple[float, float]] = sorted((lo, hi) for lo, hi, w in face_segs if w >= wall_pen)
    merged: list[list[float]] = []
    for lo, hi in spans:
        if merged and lo <= merged[-1][1] + 0.6:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    gaps = []
    if merged:
        # Runs go wall to wall, so a missing face at either end is an
        # opening too (a door or window right beside a cross wall).
        edges = [(0.0, merged[0][0])] + [(hi, lo2) for (_lo, hi), (lo2, _hi2) in zip(merged, merged[1:])] + [(merged[-1][1], L)]
        for g0, g1 in edges:
            if 2.0 * upf <= g1 - g0 <= 20.0 * upf:
                gaps.append((g0, g1))
    out["openings"] = gaps
    return out


def split_wall_at_openings(L: float, openings: list[tuple[float, float]]) -> list[tuple[float, float, bool]]:
    """Pieces of a wall run: (t0, t1, is_header_area) in order."""
    pieces: list[tuple[float, float, bool]] = []
    t = 0.0
    for g0, g1 in sorted(openings):
        if g0 > t + 1e-6:
            pieces.append((t, g0, False))
        pieces.append((max(t, g0), g1, True))
        t = g1
    if t < L - 1e-6:
        pieces.append((t, L, False))
    return pieces


def stud_count(length_units: float, spacing_units: float) -> int:
    """Studs in a run: one at the start, one at every spacing, one at the
    end - ceil(L / s) + 1 (as the viewer draws them)."""
    if spacing_units <= 0 or length_units <= 0:
        return 0
    return int(math.ceil(length_units / spacing_units - 1e-6)) + 1
