# OE-DELIVERY: 2026-11-02-auto-takeoff
"""Auto Takeoff for structural / CFS framing sheets.

Reads a sheet the way an estimator does — text first, then the lines
the text names — and returns ready-to-place markups:

* **Beams / other members** — every member designation printed on a
  plan (``W12X26``, ``HSS6X3X3/8``, ``L2X2X3/8``, ``HDR``, box beams)
  is tied to the member line it is printed along; a run shared by
  several labels is split between them at the supports.
* **Joist / truss series** — a callout with a spacing
  (``1200S200-54 @ 4'-0" o.c.``, ``18K4 @ 5'-0" O.C.``,
  ``T1 @ 24" O.C.``) becomes one line per joist in its bay, read from
  the drawn joists when they are drawn, or generated at the spacing
  between the bay's supports when only the callout is shown. The bay
  itself is returned as an **Area**.
* **CFS walls by wall tag** — each tag (``W1``, ``SW-4``…) is tied to
  the wall it sits on (double line → centre line), split between tags
  at wall junctions, and labelled with its wall-schedule description.
* **Columns** — the repeated small column symbols on a framing plan,
  named from a nearby column designation or the column schedule.

Everything is deterministic geometry over the PDF's own vector and
text layers. An optional AI pass (the user's own API key, see
``auto_takeoff_ai``) only *classifies* labels the rules do not know
(custom truss / wall tags) and reads scanned sheets; it never invents
coordinates on a vector sheet.

Every item carries a stable ``key`` (page, category, designation and
label position) so the viewer can re-run Auto Takeoff without placing
a markup twice — see ``data/auto-takeoff.ts`` on the frontend.

Coordinates are PDF points in DISPLAY space (page rotation applied),
the same space the viewer stores measurement points in.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.modules.takeoff import detect as D

CATEGORIES = ("beams", "columns", "joists", "trusses", "walls", "areas", "other")

# ── text patterns ─────────────────────────────────────────────────────
_SPACING_RE = re.compile(
    r"@\s*(?:(\d{1,2})\s*['’]\s*-?\s*(\d{1,2}(?:\s+\d+/\d+|\.\d+)?)?\s*(?:\"|”|″)?|(\d{1,3}(?:\.\d+)?)\s*(?:\"|”|″|IN\b))\s*(?:O\.?\s*C\.?|OC\b|C/C)?",
    re.IGNORECASE,
)
_WALL_TAG_RE = re.compile(r"^(?:SW|CW|IW|EW|BW|LW|NW|PW|FW|W|WT)\s?-?\s?\d{1,2}[A-Z]?$", re.IGNORECASE)
_TRUSS_TAG_RE = re.compile(r"^(?:G?T|TR|RT|GT)\s?-?\s?\d{1,3}[A-Z]?$", re.IGNORECASE)
# Truss-design software marks: zero-padded 3 digits (T001 common, J001 jack,
# G001 girder, M001 mono, V001 valley, H001 hip, E001 end jack).
_TRUSS_SOFT_RE = re.compile(r"^(?:T|J|G|M|V|H|E|CJ|EJ|GT)0\d{2}[A-Z]?$")
_HEADER_RE = re.compile(r"\b(?:HDR|HEADER|BOX\s+BEAM|BOX\s+HEADER|L-?HEADER)\b", re.IGNORECASE)
_TRUSS_WORD_RE = re.compile(r"\bTRUSS(?:ES)?\b|\bRAFTERS?\b", re.IGNORECASE)
_JOIST_WORD_RE = re.compile(r"\bJOISTS?\b|\bJST\b", re.IGNORECASE)
_DIM_RE = re.compile(r"^\d+\s*['’]\s*-?\s*\d*")
# Headers / jambs (OE-DELIVERY 2026-11-03-auto-takeoff-roles).
_JAMB_RE = re.compile(r"\bJAMBS?\b|\bJMB\b", re.IGNORECASE)
_HDR_TAG_RE = re.compile(r"^(?:HDR|H)-?\d{1,2}[A-Z]?$", re.IGNORECASE)
# Hat / furring channels and metal deck (OE-DELIVERY 2026-11-03-auto-takeoff-members).
_HAT_RE = re.compile(r"\bHAT\s*(?:CHANNEL|CHNL|SECTION)?S?\b|FURRING\s+CHANNEL|RESILIENT\s+CHANNEL|\bRC-?1\b", re.IGNORECASE)
_DECK_WORD_RE = re.compile(r"\bDECK(?:ING)?\b", re.IGNORECASE)
_DECK_DES_RE = re.compile(
    r"(\d(?:\.\d+)?|\d\s+\d/\d)\s*(?:\"|IN\.?)?\s*(?:TYPE\s+)?(VLI|VLR|VL|PLB|LOK|B|F|A|N|C)\b[\s,-]*(\d{2})?\s*(?:GA\.?)?",
    re.IGNORECASE,
)
_JAMB_TAG_RE = re.compile(r"^(?:JB|JMB|JAMB)-?\d{1,2}[A-Z]?$", re.IGNORECASE)

# Paper inches per foot above which a sheet is treated as a detail
# sheet (members on a 1 1/2" = 1'-0" connection detail are not takeoff).
_DETAIL_SCALE_IN_PER_FT = 0.5


# ── data ──────────────────────────────────────────────────────────────


@dataclass
class Label:
    text: str
    rect: tuple[float, float, float, float]
    angle: float  # folded to (-90, 90]
    size: float
    ux: float = 1.0
    uy: float = 0.0

    @property
    def cx(self) -> float:
        return (self.rect[0] + self.rect[2]) / 2.0

    @property
    def cy(self) -> float:
        return (self.rect[1] + self.rect[3]) / 2.0


Seg = tuple  # (x1, y1, x2, y2, length, width, pen)


@dataclass
class PageModel:
    page_no: int
    width: float
    height: float
    labels: list[Label]
    segments: list[Seg]
    boxes: list[tuple[float, float, float, float, bool]]  # x0, y0, x1, y1, filled
    lines: list[Any]  # detect._Line (y-bucketed, for schedules)
    units_per_foot: float | None
    scale_text: str | None
    schedule_rects: list[tuple[float, float, float, float]] = field(default_factory=list)
    index: "SegIndex | None" = None
    # A sheet that prints column sizes at the columns (column / foundation
    # plan); used to name columns on other sheets at the same grid spot.
    column_source: bool = False
    # Framing rules (OE-DELIVERY 2026-11-05-framing-rules): what the sheet is
    # ('framing' | 'roof' | 'walls' | 'foundation' | None), the floor level
    # and the drawing set's schedules.
    kind: str | None = None
    level: int | None = None
    fsched: dict[str, Any] = field(default_factory=dict)
    # All drawn pieces down to arrowhead size (framing rules only).
    fine: list[Any] = field(default_factory=list)
    fine_index: "SegIndex | None" = None
    # The sheet read at full detail: every closed small shape and every
    # stroke, curves included (OE-DELIVERY 2026-11-06-zoom-scan).
    detail: Any = None


# ── text layer ────────────────────────────────────────────────────────


def _fold(angle: float) -> float:
    return (angle + 90.0) % 180.0 - 90.0


def page_labels(page) -> list[Label]:
    """Text lines in display space, fragments merged along their direction.

    CAD exports split one callout into several text objects
    (``1200S200-54`` · ``@`` · ``4' - 0" o.c.``); they are merged when
    they share a direction and baseline and sit within ~1.6 character
    heights of each other.
    """
    matrix = page.rotation_matrix
    raw: list[Label] = []
    try:
        data = page.get_text("dict")
    except Exception:
        return raw
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            if not text.strip():
                continue
            dx, dy = line.get("dir", (1.0, 0.0))
            vx = dx * matrix.a + dy * matrix.c
            vy = dx * matrix.b + dy * matrix.d
            norm = math.hypot(vx, vy) or 1.0
            vx, vy = vx / norm, vy / norm
            angle = math.degrees(math.atan2(vy, vx))
            rect = D._transform_rect(tuple(line["bbox"]), matrix)
            sizes = [float(s.get("size", 0) or 0) for s in line.get("spans", [])]
            size = max(sizes) if sizes else 8.0
            raw.append(Label(text.strip(), rect, angle, max(size, 1.0), vx, vy))
    return _merge_fragments(raw)


def _merge_fragments(raw: list[Label]) -> list[Label]:
    buckets: dict[int, list[Label]] = {}
    for lab in raw:
        buckets.setdefault(int(round(lab.angle / 5.0)) % 72, []).append(lab)
    merged: list[Label] = []
    for items in buckets.values():
        ux, uy = items[0].ux, items[0].uy
        nx, ny = -uy, ux

        def perp(lab: Label) -> float:
            return nx * lab.cx + ny * lab.cy

        def along(lab: Label) -> tuple[float, float]:
            xs = (lab.rect[0], lab.rect[2])
            ys = (lab.rect[1], lab.rect[3])
            proj = [ux * x + uy * y for x in xs for y in ys]
            return min(proj), max(proj)

        items.sort(key=perp)
        rows: list[list[Label]] = []
        for lab in items:
            if rows and abs(perp(lab) - perp(rows[-1][0])) <= 0.45 * max(lab.size, rows[-1][0].size):
                rows[-1].append(lab)
            else:
                rows.append([lab])
        for row in rows:
            row.sort(key=lambda lab: along(lab)[0])
            cur: Label | None = None
            cur_hi = 0.0
            for lab in row:
                lo, hi = along(lab)
                if cur is not None and lo - cur_hi <= 1.6 * max(lab.size, cur.size) and abs(lab.size - cur.size) <= 0.35 * max(lab.size, cur.size):
                    cur = Label(
                        f"{cur.text} {lab.text}",
                        (
                            min(cur.rect[0], lab.rect[0]),
                            min(cur.rect[1], lab.rect[1]),
                            max(cur.rect[2], lab.rect[2]),
                            max(cur.rect[3], lab.rect[3]),
                        ),
                        cur.angle,
                        max(cur.size, lab.size),
                        cur.ux,
                        cur.uy,
                    )
                    cur_hi = max(cur_hi, hi)
                else:
                    if cur is not None:
                        merged.append(cur)
                    cur, cur_hi = lab, hi
            if cur is not None:
                merged.append(cur)
    for lab in merged:
        lab.angle = _fold(lab.angle)
        lab.text = " ".join(lab.text.split())
    return merged


# ── vector layer ──────────────────────────────────────────────────────


def page_boxes(page, drawings: list | None = None) -> list[tuple[float, float, float, float, bool]]:
    """Small closed rectangles (column symbols, tag boxes) in display space."""
    matrix = page.rotation_matrix if getattr(page, "rotation", 0) else None
    boxes: list[tuple[float, float, float, float, bool]] = []
    if drawings is None:
        try:
            drawings = page.get_drawings()
        except Exception:
            return boxes
    for drawing in drawings:
        filled = drawing.get("fill") is not None
        items = drawing.get("items") or []
        rect = None
        if len(items) == 1 and items[0][0] == "re":
            r = items[0][1]
            rect = (r.x0, r.y0, r.x1, r.y1)
        elif 3 <= len(items) <= 5 and all(it[0] == "l" for it in items):
            pts = [items[0][1]] + [it[2] for it in items]
            xs = [p.x for p in pts]
            ys = [p.y for p in pts]
            closed = math.hypot(pts[0].x - pts[-1].x, pts[0].y - pts[-1].y) < 1.0 or drawing.get("closePath")
            axis = all(abs(a.x - b.x) < 0.6 or abs(a.y - b.y) < 0.6 for a, b in zip(pts, pts[1:]))
            if closed and axis:
                rect = (min(xs), min(ys), max(xs), max(ys))
        elif drawing.get("rect") is not None and len(items) <= 2 and filled:
            r = drawing["rect"]
            rect = (r.x0, r.y0, r.x1, r.y1)
        if rect is None:
            continue
        rect = D._transform_rect(rect, matrix)
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if 3.0 <= w <= 40.0 and 3.0 <= h <= 40.0:
            boxes.append((rect[0], rect[1], rect[2], rect[3], filled))
    return boxes


def _pen(drawing) -> tuple[int, int, int]:
    col = drawing.get("color") or (0.0, 0.0, 0.0)
    if len(col) == 1:
        col = (col[0], col[0], col[0])
    elif len(col) == 4:  # CMYK -> rough RGB
        c, m, y, k = col
        col = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return tuple(int(round(float(v) * 20)) for v in col[:3])  # type: ignore[return-value]


def page_segments(page, min_len: float = 20.0, drawings: list | None = None) -> list[Seg]:
    """Straight vector segments in DISPLAY space with their pen.

    Each segment is ``(x1, y1, x2, y2, length, width, pen)``; ``pen`` is
    the stroke colour quantised to 1/20 so a black member line never
    merges with the light-grey dashes of the grid line it sits on.
    """
    matrix = page.rotation_matrix if getattr(page, "rotation", 0) else None
    out: list[Seg] = []
    if drawings is None:
        try:
            drawings = page.get_drawings()
        except Exception:
            return out
    for drawing in drawings:
        if drawing.get("color") is None and drawing.get("fill") is not None:
            continue  # filled shapes (hatch, solid symbols) are not lines
        width = float(drawing.get("width") or 0.0)
        pen = _pen(drawing)

        def add(p1x: float, p1y: float, p2x: float, p2y: float) -> None:
            x1, y1 = D._transform_rect((p1x, p1y, p1x, p1y), matrix)[:2]
            x2, y2 = D._transform_rect((p2x, p2y, p2x, p2y), matrix)[:2]
            length = math.hypot(x2 - x1, y2 - y1)
            if length >= min_len:
                out.append((x1, y1, x2, y2, length, width, pen))

        for item in drawing.get("items") or []:
            if item[0] == "l":
                add(item[1].x, item[1].y, item[2].x, item[2].y)
            elif item[0] == "re":
                r = item[1]
                add(r.x0, r.y0, r.x1, r.y0)
                add(r.x1, r.y0, r.x1, r.y1)
                add(r.x1, r.y1, r.x0, r.y1)
                add(r.x0, r.y1, r.x0, r.y0)
    return out


def same_pen(a: Seg, b: Seg) -> bool:
    if len(a) > 6 and len(b) > 6 and a[6] is not None and b[6] is not None:
        if max(abs(x - y) for x, y in zip(a[6], b[6])) > 2:
            return False
    wa, wb = float(a[5] or 0), float(b[5] or 0)
    if wa <= 0.5 and wb <= 0.5:
        return True
    lo, hi = min(wa, wb), max(wa, wb)
    return lo > 0 and hi / lo <= 1.8


def is_light(s: Seg) -> bool:
    """Light-grey linework: grid lines, background, existing-to-remain."""
    return len(s) > 6 and s[6] is not None and min(s[6]) >= 12


class SegIndex:
    """Grid index over segments for radius and corridor queries."""

    def __init__(self, segments: list[Seg], cell: float = 64.0) -> None:
        self.segments = segments
        self.cell = cell
        self.grid: dict[tuple[int, int], list[int]] = {}
        for i, s in enumerate(segments):
            x0, x1 = sorted((s[0], s[2]))
            y0, y1 = sorted((s[1], s[3]))
            for gx in range(int(x0 // cell), int(x1 // cell) + 1):
                for gy in range(int(y0 // cell), int(y1 // cell) + 1):
                    self.grid.setdefault((gx, gy), []).append(i)
        # Collinear lookup: (angle bucket, offset bucket) -> segment ids.
        self.lines: dict[tuple[int, int], list[int]] = {}
        for i, s in enumerate(segments):
            key = self._line_key(s)
            self.lines.setdefault(key, []).append(i)

    @staticmethod
    def _line_key(s: Seg) -> tuple[int, int]:
        ang = _fold(math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])))
        rad = math.radians(ang)
        ux, uy = math.cos(rad), math.sin(rad)
        off = -uy * s[0] + ux * s[1]
        return (int(round(ang)) % 180, int(round(off / 4.0)))

    def near(self, x0: float, y0: float, x1: float, y1: float) -> list[int]:
        out: set[int] = set()
        c = self.cell
        for gx in range(int(min(x0, x1) // c), int(max(x0, x1) // c) + 1):
            for gy in range(int(min(y0, y1) // c), int(max(y0, y1) // c) + 1):
                out.update(self.grid.get((gx, gy), ()))
        return list(out)

    def collinear(self, s: Seg) -> list[int]:
        ak, ok = self._line_key(s)
        out: list[int] = []
        for da in (-1, 0, 1):
            for do in (-1, 0, 1):
                out.extend(self.lines.get(((ak + da) % 180, ok + do), ()))
        return out


def _seg_angle(s: Seg) -> float:
    return _fold(math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])))


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return 180.0 - d if d > 90.0 else d


def _pt_seg_dist(px: float, py: float, s: Seg) -> float:
    return D._point_segment_distance(px, py, s)


def merge_run(seed: Seg, model: PageModel, max_gap: float = 12.0, width_tol: float | None = None) -> tuple[float, float, float, float]:
    """Grow a segment into its collinear run (indexed ``detect._merge_run``)."""
    assert model.index is not None
    x1, y1, x2, y2, length = seed[0], seed[1], seed[2], seed[3], seed[4]
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    nx, ny = -uy, ux
    base = nx * x1 + ny * y1
    lo = min(ux * x1 + uy * y1, ux * x2 + uy * y2)
    hi = max(ux * x1 + uy * y1, ux * x2 + uy * y2)
    cands = [model.segments[i] for i in model.index.collinear(seed)]
    changed = True
    while changed:
        changed = False
        for s in cands:
            if not same_pen(seed, s):
                continue
            if width_tol is not None and abs((s[5] or 0.0) - (seed[5] or 0.0)) > width_tol:
                continue
            su = ((s[2] - s[0]) / s[4], (s[3] - s[1]) / s[4])
            if abs(su[0] * ux + su[1] * uy) < 0.9993:
                continue
            if abs(nx * s[0] + ny * s[1] - base) > 3.0 or abs(nx * s[2] + ny * s[3] - base) > 3.0:
                continue
            a = ux * s[0] + uy * s[1]
            b = ux * s[2] + uy * s[3]
            s_lo, s_hi = min(a, b), max(a, b)
            if s_lo <= hi + max_gap and s_hi >= lo - max_gap and (s_lo < lo - 0.01 or s_hi > hi + 0.01):
                lo, hi = min(lo, s_lo), max(hi, s_hi)
                changed = True
    ox, oy = nx * base, ny * base
    return (ox + ux * lo, oy + uy * lo, ox + ux * hi, oy + uy * hi)


# ── page model ────────────────────────────────────────────────────────


def build_page_model(page, page_no: int) -> PageModel:
    lines = D._page_lines(page)
    plans = D._find_plans(lines, page.rect)
    scale_text = None
    for plan in plans:
        if plan.get("scale"):
            scale_text = plan["scale"]
            break
    upf = D._scale_units_per_foot(scale_text)
    # One read of the vector drawings serves every pass (OE-DELIVERY
    # 2026-11-06-zoom-scan).
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []
    try:
        segments = page_segments(page, drawings=drawings)
    except Exception:
        segments = []
    model = PageModel(
        page_no=page_no,
        width=float(page.rect.width),
        height=float(page.rect.height),
        labels=page_labels(page),
        segments=segments,
        boxes=page_boxes(page, drawings=drawings),
        lines=lines,
        units_per_foot=upf,
        scale_text=scale_text,
    )
    model.schedule_rects = [tuple(r["rect"]) for r in D._schedule_regions(lines)]
    model.index = SegIndex(segments)
    try:
        from app.modules.takeoff import detail_scan as Z

        model.detail = Z.read_sheet(page, drawings=drawings, index_cls=SegIndex)
    except Exception:
        model.detail = None
    return model


def _in_rects(x: float, y: float, rects: Iterable[tuple[float, float, float, float]], pad: float = 0.0) -> bool:
    return any(r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad for r in rects)


# ── label classification ──────────────────────────────────────────────


def spacing_inches(text: str) -> float | None:
    m = _SPACING_RE.search(text or "")
    if not m:
        return None
    if m.group(3):
        val = float(m.group(3))
        return val if 4 <= val <= 120 else None
    feet = float(m.group(1))
    inches = D._fraction_value(m.group(2) or "") or 0.0
    total = feet * 12 + inches
    return total if 4 <= total <= 144 else None


def deck_info(text: str) -> dict[str, Any] | None:
    """Metal deck callout -> designation + deck type (OE-DELIVERY 2026-11-03-auto-takeoff-members)."""
    upper = text.upper()
    m = _DECK_DES_RE.search(upper)
    if not _DECK_WORD_RE.search(upper) and not (m and m.group(0).strip() == upper.strip()):
        return None
    if re.search(r"COMPOSITE|\bVLI?\b|\bVLR\b|\bLOK\b|\bPLB\b|\bCOMP\b", upper):
        kind = "Composite Deck"
    elif re.search(r"\bFORM\b|CONFORM|\bUFX?\b", upper):
        kind = "Form Deck"
    elif re.search(r"CELLULAR", upper):
        kind = "Cellular Deck"
    elif m and m.group(2).upper() == "N":
        kind = "Type N Deck"
    elif m and m.group(2).upper() in ("B", "F", "A"):
        kind = f"Type {m.group(2).upper()} Roof Deck"
    elif re.search(r"ROOF", upper):
        kind = "Roof Deck"
    elif re.search(r"FLOOR", upper):
        kind = "Floor Deck"
    else:
        kind = "Metal Deck"
    if m:
        depth = m.group(1).replace(" ", "-")
        des = f'{depth}" {m.group(2).upper()}' + (f"-{m.group(3)} GA" if m.group(3) else "")
    else:
        des = kind.upper()
    return {"category": "areas", "designation": des, "spacing_in": None, "series": False, "role": "Deck", "deck_type": kind}


def _deck_region(label: Label, model: PageModel) -> list[tuple[float, float]] | None:
    """The bay a deck callout sits in: the nearest long framing line on each side."""
    def accept_dir(vertical: bool):
        def acc(seg) -> bool:
            if seg[4] < 90:
                return False
            ang = abs(_seg_angle(seg))
            return (abs(ang - 90) <= 8) if vertical else (ang <= 8 or ang >= 172)
        return acc

    r = _cast(model, label.cx, label.cy, 1.0, 0.0, 1600.0, accept_dir(True))
    left = _cast(model, label.cx, label.cy, -1.0, 0.0, 1600.0, accept_dir(True))
    d = _cast(model, label.cx, label.cy, 0.0, 1.0, 1600.0, accept_dir(False))
    u = _cast(model, label.cx, label.cy, 0.0, -1.0, 1600.0, accept_dir(False))
    if None in (r, left, d, u):
        return None
    x0, x1 = label.cx - left, label.cx + r
    y0, y1 = label.cy - u, label.cy + d
    if (x1 - x0) < 40 or (y1 - y0) < 40:
        return None
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def classify(label: Label, hints: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Category + designation for one label, or None when it names nothing.

    ``hints`` (from the AI pass) maps a normalized label text to
    ``{"category": ..., "spec": ...}`` for tags the rules do not know.
    """
    text = label.text
    upper = text.upper()
    if len(text) <= 90:
        deck = deck_info(text)
        if deck and not D._AISC_RE.search(text) and not D._SSMA_RE.search(text):
            return deck
    # A designation inside a sentence (notes, schedule cells) is a
    # reference, not a member on the plan.
    if len(text) > 44:
        return None
    spacing = spacing_inches(text)
    if _HAT_RE.search(text):
        hm = re.search(r"(\d+/\d+|\d+(?:\.\d+)?)\s*(?:\"|IN\.?)?\s*(?:DEEP\s+)?(?:HAT|FURRING)", upper)
        des = f'{hm.group(1)}" HAT CHANNEL' if hm else "HAT CHANNEL"
        return {"category": "joists" if spacing is not None else "other", "designation": des, "spacing_in": spacing, "series": spacing is not None, "role": "Hat Channel"}
    aisc = D._AISC_RE.search(text)
    ssma = D._SSMA_RE.search(text)
    sji = D._JOIST_RE.search(text)
    if sji:
        des = D.normalize_designation(sji.group(0))
        depth = int(re.match(r"\d+", des).group(0))
        if 8 <= depth <= 72:
            series = spacing is not None
            cat = "trusses" if _TRUSS_WORD_RE.search(text) else "joists"
            return {"category": cat, "designation": des, "spacing_in": spacing, "series": series, "role": "Steel Joist" if cat == "joists" else None}
    if ssma:
        des = D.normalize_designation(ssma.group(0))
        if D._ssma_valid(des):
            if _JAMB_RE.search(text):
                return {"category": "other", "designation": des, "spacing_in": None, "series": False, "role": "Jamb"}
            if _HEADER_RE.search(text):
                return {"category": "other", "designation": f"{des} HDR" if "HDR" not in des else des, "spacing_in": None, "series": False, "role": "Header"}
            if spacing is not None:
                cat = "trusses" if _TRUSS_WORD_RE.search(text) else "joists"
                return {"category": cat, "designation": des, "spacing_in": spacing, "series": True}
            return {"category": "other", "designation": des, "spacing_in": None, "series": False}
    if aisc:
        des = D.normalize_designation(aisc.group(0))
        if des.startswith("L") or des.startswith("PIPE"):
            cat = "other"
        elif re.search(r"\bCOL\.?\b|\bCOLUMN\b", upper):
            cat = "columns"
        else:
            cat = "beams"
        return {"category": cat, "designation": des, "spacing_in": spacing, "series": False}
    compact = re.sub(r"\s+", "", upper)
    if hints and compact in hints and hints[compact].get("category") == "ignore":
        return None
    if hints and compact in hints:
        hint = hints[compact]
        cat = hint.get("category")
        if cat in CATEGORIES:
            return {
                "category": cat,
                "designation": hint.get("designation") or compact,
                "spacing_in": spacing or hint.get("spacing_in"),
                "series": bool(spacing or hint.get("spacing_in")) and cat in ("joists", "trusses"),
                "spec": hint.get("spec"),
                "source": "ai",
            }
    if _TRUSS_WORD_RE.search(text) and spacing is not None and len(text) <= 40:
        tag = re.sub(r"@.*", "", text).strip() or "TRUSS"
        return {"category": "trusses", "designation": tag.upper(), "spacing_in": spacing, "series": True}
    if _JOIST_WORD_RE.search(text) and spacing is not None and len(text) <= 40:
        tag = re.sub(r"@.*", "", text).strip() or "JOIST"
        return {"category": "joists", "designation": tag.upper(), "spacing_in": spacing, "series": True}
    if _COL_MARK_RE.match(compact) and spacing is None:
        return {"category": "columns", "designation": compact, "spacing_in": None, "series": False, "tag": True, "mark": True}
    if (_TRUSS_TAG_RE.match(compact) or _TRUSS_SOFT_RE.match(compact)) and spacing is None and len(compact) <= 5:
        return {"category": "trusses", "designation": compact, "spacing_in": None, "series": False, "tag": True}
    if _HDR_TAG_RE.match(compact) and spacing is None:
        return {"category": "other", "designation": compact, "spacing_in": None, "series": False, "tag": True, "role": "Header"}
    if _JAMB_TAG_RE.match(compact) and spacing is None:
        return {"category": "other", "designation": compact, "spacing_in": None, "series": False, "tag": True, "role": "Jamb"}
    if _WALL_TAG_RE.match(compact) and len(compact) <= 6:
        return {"category": "walls", "designation": compact, "spacing_in": None, "series": False, "tag": True}
    if re.fullmatch(r"\(?\d\)?\s*HDR|HDR|HEADER", compact) or compact in ("HDR", "BOXHEADER", "BOXBEAM"):
        return {"category": "other", "designation": "HDR", "spacing_in": None, "series": False, "role": "Header"}
    return None


# ── schedules (wall types) ────────────────────────────────────────────


def schedule_rows(models: list[PageModel]) -> tuple[dict[str, str], set[tuple[int, int, int]]]:
    """Tag -> description rows from wall / shear-wall schedules and legends.

    Also returns where each row's tag word sits ``(page, x/4, y/4)`` so
    the tag inside the schedule table is never taken for a plan tag.
    """
    specs: dict[str, str] = {}
    spots: set[tuple[int, int, int]] = set()
    for model in models:
        for line in model.lines:
            words = sorted(line.words, key=lambda w: w[1][0])
            # Split the bucketed row into table cells clusters: a wide
            # gap means another table / the title block on the same y.
            clusters: list[list[Any]] = []
            for w in words:
                if clusters and w[1][0] - clusters[-1][-1][1][2] <= 90:
                    clusters[-1].append(w)
                else:
                    clusters.append([w])
            for cl in clusters:
                if len(cl) < 2:
                    continue
                first = re.sub(r"\s+", "", cl[0][0].upper())
                if not (_WALL_TAG_RE.match(first) or _TRUSS_TAG_RE.match(first) or _HDR_TAG_RE.match(first) or _JAMB_TAG_RE.match(first)):
                    continue
                rest_words = [w[0] for w in cl[1:]]
                tags = sum(1 for w in rest_words if _WALL_TAG_RE.match(re.sub(r"\s+", "", w.upper())))
                if tags * 2 >= len(rest_words):
                    continue
                rest = " ".join(rest_words).strip()
                if len(rest) < 4:
                    continue
                r = cl[0][1]
                spots.add((model.page_no, int(round((r[0] + r[2]) / 8.0)), int(round((r[1] + r[3]) / 8.0))))
                if first not in specs or len(rest) > len(specs[first]):
                    specs[first] = rest[:160]
    return specs, spots


def schedule_specs(models: list[PageModel]) -> dict[str, str]:
    return schedule_rows(models)[0]


# ── column marks (C1, C2 ...) and the column schedule ─────────────────
# OE-DELIVERY: 2026-11-02-auto-takeoff-columns

_COL_MARK_RE = re.compile(r"^(?:C|COL|SC|HC|PC|TC|CL)-?\d{1,3}[A-Z]?$", re.IGNORECASE)
_PROFILE_RES = (D._AISC_RE, D._SSMA_RE)


def _profile_in(text: str) -> str | None:
    for rx in _PROFILE_RES:
        m = rx.search(text or "")
        if m:
            return D.normalize_designation(m.group(0))
    return None


def column_schedule(models: list["PageModel"]) -> dict[str, str]:
    """Column mark -> profile from column schedules.

    Two table shapes are read:
    * row form   ``C1  HSS8X8X1/2  ...`` (mark first, profile on the row);
    * column form a row of marks ``C1 C2 C3`` with each profile printed
      below its mark in the same column.
    """
    out: dict[str, str] = {}
    for model in models:
        lines = sorted(
            [ln for ln in model.lines if ln.words],
            key=lambda ln: min(w[1][1] for w in ln.words),
        )
        for li, line in enumerate(lines):
            words = sorted(line.words, key=lambda w: w[1][0])
            marks = [w for w in words if _COL_MARK_RE.match(re.sub(r"\s+", "", w[0]))]
            if not marks:
                continue
            first = re.sub(r"\s+", "", words[0][0]).upper()
            if _COL_MARK_RE.match(first) and len(marks) == 1:
                # Row form: the profile on the same row, within table reach.
                rest = " ".join(w[0] for w in words[1:] if w[1][0] - words[0][1][2] < 500)
                prof = _profile_in(rest)
                if prof:
                    out.setdefault(first, prof)
                continue
            if len(marks) < 2:
                continue
            # Column form: look down each mark's column for a profile.
            y_top = max(w[1][3] for w in marks)
            for mk in marks:
                mark = re.sub(r"\s+", "", mk[0]).upper()
                if mark in out:
                    continue
                mx0, mx1 = mk[1][0], mk[1][2]
                cx = (mx0 + mx1) / 2.0
                reach = max(30.0, (mx1 - mx0) * 2)
                for below in lines[li + 1:]:
                    by = min(w[1][1] for w in below.words)
                    if by - y_top > 400:
                        break
                    cell = " ".join(
                        w[0] for w in sorted(below.words, key=lambda w: w[1][0])
                        if abs((w[1][0] + w[1][2]) / 2.0 - cx) <= reach
                    )
                    prof = _profile_in(cell)
                    if prof:
                        out[mark] = prof
                        break
    return out


# ── geometry: members ─────────────────────────────────────────────────


def _member_seed(label: Label, model: PageModel, radius: float = 60.0, min_len: float = 40.0, strict: bool = False) -> Seg | None:
    cx, cy = label.cx, label.cy
    assert model.index is not None
    near: list[tuple[Seg, float]] = []
    for i in model.index.near(cx - radius, cy - radius, cx + radius, cy + radius):
        s = model.segments[i]
        if s[4] < min_len or is_light(s):
            continue
        d = _pt_seg_dist(cx, cy, s)
        if d <= radius:
            near.append((s, d))
    if not near:
        return None
    aligned = [it for it in near if _angle_diff(_seg_angle(it[0]), label.angle) <= 12.0]
    if aligned:
        near = aligned
    elif strict or len(label.text) > 3:
        # A designation is printed along its member; with no aligned
        # line nearby the label is a callout/leader, not on a member.
        return None
    return min(near, key=lambda it: (round(it[1] / 8.0), -it[0][4], it[1]))[0]


def _run_key(run: tuple[float, float, float, float]) -> tuple[int, int, int]:
    ang = _fold(math.degrees(math.atan2(run[3] - run[1], run[2] - run[0])))
    rad = math.radians(ang)
    off = -math.sin(rad) * run[0] + math.cos(rad) * run[1]
    return (int(round(ang / 2.0)), int(round(off / 4.0)), 0)


def _project(run, x: float, y: float) -> float:
    ux, uy = run[2] - run[0], run[3] - run[1]
    length = math.hypot(ux, uy) or 1.0
    return ((x - run[0]) * ux + (y - run[1]) * uy) / length


def _point_on(run, t: float) -> tuple[float, float]:
    length = math.hypot(run[2] - run[0], run[3] - run[1]) or 1.0
    return (run[0] + (run[2] - run[0]) * t / length, run[1] + (run[3] - run[1]) * t / length)


def _cut_candidates(run, model: PageModel, boxes_only: bool = False) -> list[float]:
    """Positions along a run where a support/crossing member meets it."""
    assert model.index is not None
    length = math.hypot(run[2] - run[0], run[3] - run[1])
    out: list[float] = []
    ang = _fold(math.degrees(math.atan2(run[3] - run[1], run[2] - run[0])))
    for i in [] if boxes_only else model.index.near(min(run[0], run[2]) - 4, min(run[1], run[3]) - 4, max(run[0], run[2]) + 4, max(run[1], run[3]) + 4):
        s = model.segments[i]
        # Supports meet a member square-on; hips and braces crossing at
        # an angle are not where the member stops.
        if s[4] < 25 or is_light(s) or _angle_diff(_seg_angle(s), ang) < 70:
            continue
        # Intersection of the infinite run line with segment s.
        x1, y1, x2, y2 = run
        x3, y3, x4, y4 = s[0], s[1], s[2], s[3]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            continue
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
        if -0.01 <= u <= 1.01 and 0.0 < t < 1.0:
            out.append(t * length)
    for b in model.boxes:
        bx, by = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        t = _project(run, bx, by)
        px, py = _point_on(run, t)
        if 0 < t < length and math.hypot(px - bx, py - by) <= max(b[2] - b[0], b[3] - b[1]):
            out.append(t)
    if boxes_only and model.fine_index is not None:
        # Column squares drawn as four short lines: two short sides
        # crossing the run 3-9 units apart.
        ux, uy = (run[2] - run[0]) / (length or 1.0), (run[3] - run[1]) / (length or 1.0)
        sides: list[float] = []
        for i in model.fine_index.near(min(run[0], run[2]) - 6, min(run[1], run[3]) - 6, max(run[0], run[2]) + 6, max(run[1], run[3]) + 6):
            sg = model.fine[i]
            ln = math.hypot(sg[2] - sg[0], sg[3] - sg[1])
            if not (3.0 <= ln <= 9.5) or abs(((sg[2] - sg[0]) * ux + (sg[3] - sg[1]) * uy) / ln) > 0.2:
                continue
            n0 = (sg[0] - run[0]) * -uy + (sg[1] - run[1]) * ux
            n1 = (sg[2] - run[0]) * -uy + (sg[3] - run[1]) * ux
            if n0 * n1 > 0:
                continue
            sides.append(((sg[0] + sg[2]) / 2.0 - run[0]) * ux + ((sg[1] + sg[3]) / 2.0 - run[1]) * uy)
        sides.sort()
        for a, b in zip(sides, sides[1:]):
            if 3.0 <= b - a <= 9.5 and 0 < (a + b) / 2.0 < length:
                out.append((a + b) / 2.0)
    return sorted(out)


def _split_shared(entries: list[dict[str, Any]], model: PageModel, strict: bool = False) -> None:
    """Several labels on one run: give each its own piece of the run.
    ``strict`` (framing rules): only runs covering the same stretch are one
    run - two walls on one grid line either side of a corridor are not."""
    groups: dict[tuple[int, ...], list[dict[str, Any]]] = {}
    for e in entries:
        if e.get("run"):
            key: tuple[int, ...] = _run_key(e["run"])
            if strict:
                r = e["run"]
                a, b = sorted(((r[0], r[1]), (r[2], r[3])))
                key = key + (int(round(a[0] / 6)), int(round(a[1] / 6)), int(round(b[0] / 6)), int(round(b[1] / 6)))
            groups.setdefault(key, []).append(e)
    for group in groups.values():
        if len(group) < 2:
            continue
        run = max((g["run"] for g in group), key=lambda r: math.hypot(r[2] - r[0], r[3] - r[1]))
        length = math.hypot(run[2] - run[0], run[3] - run[1])
        for g in group:
            g["_t"] = _project(run, g["label"].cx, g["label"].cy)
        group.sort(key=lambda g: g["_t"])
        cuts = _cut_candidates(run, model)
        bounds = [0.0]
        for a, b in zip(group, group[1:]):
            mid = (a["_t"] + b["_t"]) / 2.0
            between = [c for c in cuts if a["_t"] + 4 < c < b["_t"] - 4]
            bounds.append(min(between, key=lambda c: abs(c - mid)) if between else mid)
        bounds.append(length)
        # The end pieces run on to the ends of the line, which may be a
        # wall or corridor line far past the last column: when an end piece
        # is far longer than the pieces between the labels (or > 70 ft),
        # end it at the nearest column / support past its label
        # (OE-DELIVERY 2026-11-05-framing-rules).
        inner = sorted(hi - lo for lo, hi in zip(bounds[1:-1], bounds[2:-1]))
        ref = inner[len(inner) // 2] if inner else None
        too_long = 70 * model.units_per_foot if model.units_per_foot else None
        box_cuts = _cut_candidates(run, model, boxes_only=True)

        def _long(piece: float) -> bool:
            return bool((ref and piece > 1.6 * ref) or (too_long and piece > too_long))

        if len(bounds) >= 3 and _long(bounds[1] - bounds[0]):
            t0 = group[0]["_t"]
            pick = [c for c in box_cuts if c < t0 - 4] or [c for c in cuts if c < t0 - 4]
            if pick:
                bounds[0] = max(pick)
        if len(bounds) >= 3 and _long(bounds[-1] - bounds[-2]):
            t1 = group[-1]["_t"]
            pick = [c for c in box_cuts if c > t1 + 4] or [c for c in cuts if c > t1 + 4]
            if pick:
                bounds[-1] = min(pick)
        for g, lo, hi in zip(group, bounds, bounds[1:]):
            if hi - lo < 12:
                g["run"] = None
                continue
            g["run"] = (*_point_on(run, lo), *_point_on(run, hi))


def _trim_to_supports(run, label: Label, model: PageModel) -> tuple[float, float, float, float]:
    """A single label on a very long run (continuous line through several
    bays) keeps only its own bay: the stretch between the nearest support
    crossings on either side of the label."""
    length = math.hypot(run[2] - run[0], run[3] - run[1])
    # Only an implausibly long single member (> 70 ft at the sheet scale)
    # is trimmed; without a known scale the run is kept whole.
    if not model.units_per_foot or length < 70 * model.units_per_foot:
        return run
    t = _project(run, label.cx, label.cy)
    cuts = _cut_candidates(run, model)
    lo = max([c for c in cuts if c < t - 4], default=0.0)
    hi = min([c for c in cuts if c > t + 4], default=length)
    return (*_point_on(run, lo), *_point_on(run, hi))


# ── geometry: joist / truss series ────────────────────────────────────


def _distribution_line(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """The span/distribution arrow a series callout is printed on.

    Framing plans draw a thin line with arrowheads across the joists of
    a bay and print the callout on it; its ends are the first and last
    joist of the series.
    """
    assert model.index is not None
    ux, uy = math.cos(math.radians(label.angle)), math.sin(math.radians(label.angle))
    nx, ny = -uy, ux
    proj = [ux * x + uy * y for x in (label.rect[0], label.rect[2]) for y in (label.rect[1], label.rect[3])]
    lab_lo, lab_hi = min(proj), max(proj)
    lab_len = max(lab_hi - lab_lo, 1.0)
    c_n = nx * label.cx + ny * label.cy
    reach = 2.2 * label.size
    best: tuple[float, Seg] | None = None
    for i in model.index.near(label.rect[0] - reach, label.rect[1] - reach, label.rect[2] + reach, label.rect[3] + reach):
        s = model.segments[i]
        if s[4] < 0.35 * lab_len or is_light(s) or _angle_diff(_seg_angle(s), label.angle) > 3.0:
            continue
        off = nx * (s[0] + s[2]) / 2.0 + ny * (s[1] + s[3]) / 2.0 - c_n
        if abs(off) > reach or abs(off) < 0.3 * label.size:
            continue
        a, b = ux * s[0] + uy * s[1], ux * s[2] + uy * s[3]
        overlap = min(lab_hi, max(a, b)) - max(lab_lo, min(a, b))
        if overlap < 0.4 * min(lab_len, s[4]):
            continue
        if best is None or abs(off) < best[0]:
            best = (abs(off), s)
    if best is None:
        return None
    return merge_run(best[1], model, max_gap=14.0)


def _crossing_members(dist: tuple[float, float, float, float], model: PageModel, spacing_units: float | None) -> list[tuple[float, float, float, float]]:
    """Member lines crossing a distribution line, one per member, in order."""
    assert model.index is not None
    length = math.hypot(dist[2] - dist[0], dist[3] - dist[1]) or 1.0
    ang = _fold(math.degrees(math.atan2(dist[3] - dist[1], dist[2] - dist[0])))
    margin = 4.0
    hits: list[tuple[float, tuple[float, float, float, float]]] = []
    for i in model.index.near(min(dist[0], dist[2]) - margin, min(dist[1], dist[3]) - margin, max(dist[0], dist[2]) + margin, max(dist[1], dist[3]) + margin):
        s = model.segments[i]
        if s[4] < 30 or is_light(s) or _angle_diff(_seg_angle(s), ang) < 75:
            continue
        x1, y1, x2, y2 = dist
        x3, y3, x4, y4 = s[0], s[1], s[2], s[3]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            continue
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
        tol_u = margin / s[4]
        if -margin / length <= t <= 1 + margin / length and -tol_u <= u <= 1 + tol_u:
            # Joists stop at their supports: never bridge a gap.
            run = merge_run(s, model, max_gap=2.0)
            hits.append((t * length, run))
    hits.sort(key=lambda h: h[0])
    out: list[tuple[float, tuple[float, float, float, float]]] = []
    min_gap = (spacing_units or 12.0) * 0.35
    for pos, run in hits:
        if out and pos - out[-1][0] < max(min_gap, 1.5):
            # Same member (double-drawn or doubled line): keep the longer.
            prev = out[-1][1]
            if math.hypot(run[2] - run[0], run[3] - run[1]) > math.hypot(prev[2] - prev[0], prev[3] - prev[1]):
                out[-1] = (pos, run)
            continue
        out.append((pos, run))
    return [r for _p, r in out]


def _series_from_distribution(label: Label, info: dict[str, Any], model: PageModel) -> tuple[list[tuple[float, float, float, float]], bool, list[tuple[float, float]] | None] | None:
    dist = _distribution_line(label, model)
    if dist is None:
        return None
    upf = model.units_per_foot
    spacing_units = (info["spacing_in"] / 12.0) * upf if (upf and info.get("spacing_in")) else None
    members = _crossing_members(dist, model, spacing_units)
    d_ang = math.atan2(dist[3] - dist[1], dist[2] - dist[0])
    dx, dy = math.cos(d_ang), math.sin(d_ang)  # along the distribution line
    jx, jy = -dy, dx  # along the members
    d_lo = dx * dist[0] + dy * dist[1]
    d_hi = dx * dist[2] + dy * dist[3]
    d_lo, d_hi = min(d_lo, d_hi), max(d_lo, d_hi)
    if len(members) >= 2:
        offs = [dx * (m[0] + m[2]) / 2.0 + dy * (m[1] + m[3]) / 2.0 for m in members]
        s_vals = [jx * x + jy * y for m in members for x, y in ((m[0], m[1]), (m[2], m[3]))]
        bay = _bay_poly(jx, jy, dx, dy, min(s_vals), max(s_vals), min(offs), max(offs))
        return members, False, bay
    # Only the arrow is drawn: generate members at the spacing between
    # the supports either side of the arrow.
    if not spacing_units:
        return None
    mx, my = (dist[0] + dist[2]) / 2.0, (dist[1] + dist[3]) / 2.0
    ang = math.degrees(d_ang)
    accept = lambda s: s[4] >= 30 and not is_light(s) and _angle_diff(_seg_angle(s), ang) <= 8  # noqa: E731
    a = _cast(model, mx, my, jx, jy, 1400.0, accept)
    b = _cast(model, mx, my, -jx, -jy, 1400.0, accept)
    if a is None or b is None:
        return None
    c_s = jx * mx + jy * my
    s_lo, s_hi = c_s - b, c_s + a
    width = d_hi - d_lo
    count = int(math.floor(width / spacing_units + 1e-6)) + 1
    start = d_lo + (width - (count - 1) * spacing_units) / 2.0
    lines = []
    for k in range(count):
        off = start + k * spacing_units
        lines.append((dx * off + jx * s_lo, dy * off + jy * s_lo, dx * off + jx * s_hi, dy * off + jy * s_hi))
    return lines, True, _bay_poly(jx, jy, dx, dy, s_lo, s_hi, d_lo, d_hi)


def _series_lines(label: Label, info: dict[str, Any], model: PageModel) -> tuple[list[tuple[float, float, float, float]], bool, list[tuple[float, float]] | None]:
    """Joist lines of the bay a series callout sits in.

    Returns (lines, generated, bay_polygon).
    """
    assert model.index is not None
    via_arrow = _series_from_distribution(label, info, model)
    if via_arrow is not None and via_arrow[0]:
        return via_arrow
    ux, uy = math.cos(math.radians(label.angle)), math.sin(math.radians(label.angle))
    nx, ny = -uy, ux
    cx, cy = label.cx, label.cy
    c_u = ux * cx + uy * cy
    c_n = nx * cx + ny * cy
    upf = model.units_per_foot
    spacing_units = (info["spacing_in"] / 12.0) * upf if (upf and info.get("spacing_in")) else None
    reach = 900.0
    cand: list[tuple[float, float, float, Seg]] = []  # (n offset, lo, hi, seg)
    seen_runs: set[tuple[int, int]] = set()
    for i in model.index.near(cx - reach, cy - reach, cx + reach, cy + reach):
        s = model.segments[i]
        if s[4] < 30 or _angle_diff(_seg_angle(s), label.angle) > 3.0:
            continue
        run = merge_run(s, model, max_gap=2.0)
        a = ux * run[0] + uy * run[1]
        b = ux * run[2] + uy * run[3]
        lo, hi = min(a, b), max(a, b)
        if not (lo - 6 <= c_u <= hi + 6):
            continue
        off = nx * (run[0] + run[2]) / 2.0 + ny * (run[1] + run[3]) / 2.0
        key = (int(round(off / 1.5)), int(round(lo / 6)))
        if key in seen_runs:
            continue
        seen_runs.add(key)
        cand.append((off, lo, hi, (run[0], run[1], run[2], run[3], hi - lo, None)))
    # Supports: perpendicular members the callout's bay spans between.
    span_lo, span_hi = _cast_supports(label, model, ux, uy)
    lines: list[tuple[float, float, float, float]] = []
    generated = False
    if cand and span_lo is not None and span_hi is not None:
        span = span_hi - span_lo
        inbay = [c for c in cand if c[1] >= span_lo - 0.15 * span and c[2] <= span_hi + 0.15 * span and (c[2] - c[1]) >= 0.6 * span]
        inbay.sort(key=lambda c: c[0])
        # Walk outward from the callout while the spacing stays regular.
        left = [c for c in inbay if c[0] < c_n]
        right = [c for c in inbay if c[0] >= c_n]
        left.sort(key=lambda c: -c[0])
        right.sort(key=lambda c: c[0])
        picked: list[tuple[float, float, float, Seg]] = []
        for side in (left, right):
            prev = c_n
            gaps: list[float] = []
            for c in side:
                gap = abs(c[0] - prev)
                if prev == c_n:
                    limit = (spacing_units or 60.0) * 1.3
                else:
                    ref = spacing_units or (sum(gaps) / len(gaps) if gaps else gap)
                    limit = ref * 1.45
                if gap < 1.0:
                    continue
                if gap > limit:
                    break
                if prev != c_n:
                    gaps.append(gap)
                picked.append(c)
                prev = c[0]
        if len(picked) >= 2:
            picked.sort(key=lambda c: c[0])
            # Drop doubled lines (a joist drawn as two close parallel lines).
            dedup: list[tuple[float, float, float, Seg]] = []
            for c in picked:
                if dedup and abs(c[0] - dedup[-1][0]) < (spacing_units or 12.0) * 0.35:
                    continue
                dedup.append(c)
            for c in dedup:
                s = c[3]
                lines.append((s[0], s[1], s[2], s[3]))
            n_lo, n_hi = dedup[0][0], dedup[-1][0]
            bay = _bay_poly(ux, uy, nx, ny, span_lo, span_hi, n_lo, n_hi)
            return lines, False, bay
    # Nothing drawn: generate at the spacing between the bay edges.
    if span_lo is None or span_hi is None or not spacing_units:
        return [], False, None
    edge_lo, edge_hi = _cast_edges(label, model, ux, uy, span_hi - span_lo)
    if edge_lo is None or edge_hi is None:
        return [], False, None
    width = edge_hi - edge_lo
    if width < spacing_units * 0.9:
        return [], False, None
    count = int(math.floor(width / spacing_units + 1e-6)) + 1
    start = edge_lo + (width - (count - 1) * spacing_units) / 2.0
    for k in range(count):
        off = start + k * spacing_units
        lines.append((
            ux * span_lo + nx * off,
            uy * span_lo + ny * off,
            ux * span_hi + nx * off,
            uy * span_hi + ny * off,
        ))
    generated = True
    return lines, generated, _bay_poly(ux, uy, nx, ny, span_lo, span_hi, edge_lo, edge_hi)


def leader_tip(label: Label, model: PageModel) -> tuple[float, float] | None:
    """Far end of the leader drawn from a label (None without one)."""
    c = leader_tips(label, model)
    return c[0][1] if c else None


def leader_tips(label: Label, model: PageModel) -> list[tuple[tuple[int, float], tuple[float, float]]]:
    """Possible far ends of the leader drawn from a label, best first: a
    line starting at the text box, followed through its bends; one ending
    on a small drawn symbol ranks first."""
    assert model.index is not None
    segs = model.fine if model.fine_index is not None else model.segments
    index = model.fine_index if model.fine_index is not None else model.index
    pad = max(5.0, 0.6 * label.size)
    x0, y0, x1, y1 = label.rect[0] - pad, label.rect[1] - pad, label.rect[2] + pad, label.rect[3] + pad

    def inside(x: float, y: float) -> bool:
        return x0 <= x <= x1 and y0 <= y <= y1

    found: list[tuple[tuple[int, float], tuple[float, float]]] = []
    for i in index.near(x0, y0, x1, y1):
        sg = segs[i]
        if not (6 <= sg[4] <= 260):
            continue
        a_in, b_in = inside(sg[0], sg[1]), inside(sg[2], sg[3])
        if a_in and b_in:
            continue
        if a_in != b_in:
            starts = [(sg[2], sg[3]) if a_in else (sg[0], sg[1])]
        else:
            # An underline running past both ends of the text.
            mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
            if not (inside(mx, my) or (min(sg[0], sg[2]) <= x0 and max(sg[0], sg[2]) >= x1 and y0 <= my <= y1)):
                continue
            if _angle_diff(_seg_angle(sg), label.angle) > 8:
                continue
            starts = [(sg[0], sg[1]), (sg[2], sg[3])]
        for start in starts:
            for cur, total in _follow_leader(segs, index, i, start, sg, inside):
                sym = _symbol_pieces(model, cur[0], cur[1])
                found.append(((0 if sym >= 12 else 1, total), cur))
    found.sort(key=lambda f: f[0])
    return found


def _follow_leader(segs, index, i: int, start: tuple[float, float], sg, inside) -> list[tuple[tuple[float, float], float]]:
    """Every bend / end along a leader, with the length walked to it."""
    cur = start
    out: list[tuple[tuple[float, float], float]] = []
    if True:
        if not inside(*cur) and sg[4] >= 8:
            out.append((cur, sg[4]))
        prev_ang = _seg_angle(sg)
        used = {i}
        total = sg[4]
        for _step in range(3):
            nxt = None
            for j in index.near(cur[0] - 1.5, cur[1] - 1.5, cur[0] + 1.5, cur[1] + 1.5):
                if j in used:
                    continue
                w = segs[j]
                if w[4] < 5 or _angle_diff(_seg_angle(w), prev_ang) < 10:
                    continue
                if math.hypot(w[0] - cur[0], w[1] - cur[1]) <= 1.5:
                    nxt = (j, (w[2], w[3]))
                elif math.hypot(w[2] - cur[0], w[3] - cur[1]) <= 1.5:
                    nxt = (j, (w[0], w[1]))
                if nxt:
                    break
            if not nxt:
                break
            used.add(nxt[0])
            w = segs[nxt[0]]
            prev_ang = _seg_angle(w)
            total += w[4]
            cur = nxt[1]
            if not inside(*cur):
                out.append((cur, total))
    return out


def _symbol_pieces(model: PageModel, x: float, y: float, reach: float = 9.0) -> int:
    if model.fine_index is None:
        return 0
    n = 0
    for i in model.fine_index.near(x - reach, y - reach, x + reach, y + reach):
        sg = model.fine[i]
        if sg[4] <= 2.2 * reach and max(abs(sg[0] - x), abs(sg[2] - x)) <= reach and max(abs(sg[1] - y), abs(sg[3] - y)) <= reach:
            n += 1
    return n


def _symbol_centre(model: PageModel, x: float, y: float, reach: float = 9.0) -> tuple[float, float]:
    """Centre of the small symbol (column square) drawn at a leader tip."""
    if model.fine_index is None:
        return x, y
    xs: list[float] = []
    ys: list[float] = []
    for i in model.fine_index.near(x - reach, y - reach, x + reach, y + reach):
        sg = model.fine[i]
        if sg[4] > 2.2 * reach:
            continue
        if max(abs(sg[0] - x), abs(sg[2] - x)) <= reach and max(abs(sg[1] - y), abs(sg[3] - y)) <= reach:
            xs += [sg[0], sg[2]]
            ys += [sg[1], sg[3]]
    if len(xs) < 6:
        return x, y
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _snap_symbol(model: PageModel, x: float, y: float) -> tuple[float, float] | None:
    """Centre of the column symbol at (or within ~3 ft of) a leader tip."""
    if _symbol_pieces(model, x, y) < 12:
        reach = 3.0 * (model.units_per_foot or 9.0)
        step = 3.0
        k = int(reach / step)
        best: tuple[float, float, tuple[float, float]] | None = None
        for gx in range(-k, k + 1):
            for gy in range(-k, k + 1):
                d = math.hypot(gx, gy) * step
                if d > reach:
                    continue
                q = (x + gx * step, y + gy * step)
                n = _symbol_pieces(model, q[0], q[1])
                if n >= 12 and (best is None or (-n, d) < (best[0], best[1])):
                    best = (-n, d, q)
        if best is None:
            return None
        x, y = best[2]
    for _ in range(3):
        x, y = _symbol_centre(model, x, y)
    return x, y


def _leader_columns(model: PageModel, labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]]) -> list[dict[str, Any]]:
    """Foundation plans: one column at the end of each column-size leader;
    each column symbol belongs to one label."""
    cands: list[tuple[tuple[int, float], int, Label, dict[str, Any], tuple[float, float]]] = []
    labs = labels_by_cat.get("columns", [])
    for li, (lab, info) in enumerate(labs):
        for score, tip in leader_tips(lab, model)[:6]:
            pt = _snap_symbol(model, tip[0], tip[1])
            if pt is not None:
                cands.append((score, li, lab, info, pt))
    cands.sort(key=lambda c: (c[0], c[1]))
    out: list[dict[str, Any]] = []
    done: set[int] = set()
    for _score, li, lab, info, pt in cands:
        if li in done or any(math.hypot(pt[0] - c["point"][0], pt[1] - c["point"][1]) < 4 for c in out):
            continue
        done.add(li)
        out.append({
            "mark_obj": None,
            "label_obj": lab,
            "point": pt,
            "designation": info["designation"],
            "label": info["designation"],
            "mark": None,
            "label_rect": list(lab.rect),
            "size": None,
        })
    return out


def _hatch_panel(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Centre line of the hatched wall panel nearest a shear / strap-braced
    wall tag: the hatch strokes are followed stroke to stroke, the panel's
    direction is its long side."""
    if model.fine_index is None:
        return None
    upf = model.units_per_foot or 9.0
    reach = 5.0 * upf

    def stroke(sg) -> float | None:
        ln = math.hypot(sg[2] - sg[0], sg[3] - sg[1])
        if not (2.0 <= ln <= 14.0):
            return None
        c = abs((sg[2] - sg[0]) / ln)
        if not (0.4 <= c <= 0.92):
            return None
        return _fold(math.degrees(math.atan2(sg[3] - sg[1], sg[2] - sg[0])))

    reach = 2.2 * upf
    r0, r1, r2, r3 = label.rect
    seeds: list[tuple[float, int]] = []
    for i in model.fine_index.near(r0 - reach, r1 - reach, r2 + reach, r3 + reach):
        sg = model.fine[i]
        if stroke(sg) is None:
            continue
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        d = math.hypot(max(r0 - mx, 0.0, mx - r2), max(r1 - my, 0.0, my - r3))
        if d <= reach:
            seeds.append((d, i))
    # Panel hatching is the heaviest stroke there (a thin general wall
    # pattern may run along the whole wall): heavier seeds first.
    seeds.sort(key=lambda sd: (-round(model.fine[sd[1]][5] or 0.0, 2), sd[0]))
    for _d, si in seeds[:12]:
        panel = _grow_hatch(model, si, stroke)
        if panel is not None:
            return panel
    return None


def _grow_hatch(model: PageModel, si: int, stroke) -> tuple[float, float, float, float] | None:
    """Hatched panel grown from one stroke (None unless it is a panel)."""
    assert model.fine_index is not None
    seed = (0.0, si)
    s_seed = model.fine[si]
    ang0 = stroke(s_seed)
    seen = {seed[1]}
    todo = [seed[1]]
    mids: list[tuple[float, float]] = []
    while todo and len(seen) < 4000:
        i = todo.pop()
        sg = model.fine[i]
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        mids.append((mx, my))
        for j in model.fine_index.near(mx - 8, my - 8, mx + 8, my + 8):
            if j in seen:
                continue
            o = model.fine[j]
            a = stroke(o)
            if a is None or _angle_diff(a, ang0 or 0.0) > 6:
                continue
            if abs((o[5] or 0.0) - (s_seed[5] or 0.0)) > 0.05 or o[6] != s_seed[6]:
                continue  # another pattern (same pen as the seed only)
            if math.hypot((o[0] + o[2]) / 2.0 - mx, (o[1] + o[3]) / 2.0 - my) <= 8:
                seen.add(j)
                todo.append(j)
    if len(mids) < 6:
        return None
    # Hatching can run on round a corner into the next panel: keep the
    # straight run through the seed stroke (vertical or horizontal, the
    # longer one), contiguous from the seed.
    s0 = model.fine[seed[1]]
    sx, sy = (s0[0] + s0[2]) / 2.0, (s0[1] + s0[3]) / 2.0

    def chain(vals: list[float], start: float) -> list[float]:
        vals = sorted(vals)
        if not vals:
            return []
        i = min(range(len(vals)), key=lambda k: abs(vals[k] - start))
        lo = hi = i
        while lo > 0 and vals[lo] - vals[lo - 1] <= 8.0:
            lo -= 1
        while hi < len(vals) - 1 and vals[hi + 1] - vals[hi] <= 8.0:
            hi += 1
        return vals[lo:hi + 1]

    vert = [m for m in mids if abs(m[0] - sx) <= 5.0]
    horz = [m for m in mids if abs(m[1] - sy) <= 5.0]
    v_run = chain([m[1] for m in vert], sy)
    h_run = chain([m[0] for m in horz], sx)
    if max(len(v_run), len(h_run)) >= 6:
        if len(v_run) >= len(h_run):
            x = sum(m[0] for m in vert) / len(vert)
            mids = [(x, y) for y in v_run]
        else:
            y = sum(m[1] for m in horz) / len(horz)
            mids = [(x, y) for x in h_run]
    xs = [p[0] for p in mids]
    ys = [p[1] for p in mids]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    # A panel is long and thin and densely hatched (not two dimension ticks).
    if max(w, h) < 12 or min(w, h) > 12 or len(mids) < max(w, h) / 8.0:
        return None
    if w >= h:
        y = sum(ys) / len(ys)
        return (min(xs) - 1.0, y, max(xs) + 1.0, y)
    x = sum(xs) / len(xs)
    return (x, min(ys) - 1.0, x, max(ys) + 1.0)


def _dimension_span(label: Label, model: PageModel, want: float | None = None) -> tuple[float, float, float, float] | None:
    """Dimension line drawn with the tag (the panel length, e.g. 7'-0"):
    a line parallel to the text just beside it, covering it, with a tick
    across each end."""
    if model.fine_index is None:
        return None
    cx, cy = label.cx, label.cy
    # One dimension often serves the tags on both sides of it (corridor
    # walls), so look a little past the nearest tag.
    near = 3.5 * label.size
    best: tuple[float, tuple[float, float, float, float]] | None = None
    min_len = 3.0 * (model.units_per_foot or 9.0)
    for i in model.fine_index.near(cx - 200, cy - near, cx + 200, cy + near) if abs(math.sin(math.radians(label.angle))) < 0.5 else model.fine_index.near(cx - near, cy - 200, cx + near, cy + 200):
        sg = model.fine[i]
        if sg[4] < min_len or _angle_diff(_seg_angle(sg), label.angle) > 3:
            continue
        # With a hatched panel to match, only a dimension about its length.
        if want is not None and not (0.85 * want <= sg[4] <= 1.15 * want):
            continue
        ux, uy = (sg[2] - sg[0]) / sg[4], (sg[3] - sg[1]) / sg[4]
        t = (cx - sg[0]) * ux + (cy - sg[1]) * uy
        if t < 0 or t > sg[4]:
            continue
        d = abs((cx - sg[0]) * -uy + (cy - sg[1]) * ux)
        if d > near:
            continue
        ticks = 0
        for ex, ey in ((sg[0], sg[1]), (sg[2], sg[3])):
            for j in model.fine_index.near(ex - 4, ey - 4, ex + 4, ey + 4):
                o = model.fine[j]
                if (
                    3 <= o[4] <= 16
                    and 25 <= _angle_diff(_seg_angle(o), _seg_angle(sg)) <= 65
                    and _pt_seg_dist(ex, ey, o) <= 1.5
                    and math.hypot((o[0] + o[2]) / 2.0 - ex, (o[1] + o[3]) / 2.0 - ey) <= 2.5
                ):
                    ticks += 1
                    break
        if ticks < 2:
            continue
        if best is None or d < best[0]:
            best = (d, (sg[0], sg[1], sg[2], sg[3]))
    return best[1] if best else None


def shear_panel(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Shear / strap-braced wall panel for a tag (framing rules): the
    hatched panel at the tag, as long as the dimension drawn with the tag
    when there is one; a panel drawn without hatching sits on the wall
    beyond the tag, between the dimension's ends."""
    hatch = _hatch_panel(label, model)
    dim = _dimension_span(label, model, want=math.hypot(hatch[2] - hatch[0], hatch[3] - hatch[1]) if hatch is not None else None)
    if hatch is not None and dim is not None and _angle_diff(_seg_angle((*hatch, 1.0)), _seg_angle((*dim, 1.0))) <= 3:
        lo = _project(hatch, dim[0], dim[1])
        hi = _project(hatch, dim[2], dim[3])
        lo, hi = min(lo, hi), max(lo, hi)
        h_len = math.hypot(hatch[2] - hatch[0], hatch[3] - hatch[1])
        d_len = hi - lo
        # Same panel: a real dimension (not a tag box) about as long as the
        # hatching and over it.
        if (
            d_len >= 3.0 * (model.units_per_foot or 9.0)
            and 0.85 * h_len <= d_len <= 1.15 * h_len
            and min(hi, h_len) - max(lo, 0.0) >= 0.6 * min(h_len, d_len)
        ):
            return (*_point_on(hatch, lo), *_point_on(hatch, hi))
        return hatch
    if hatch is not None:
        return hatch
    if dim is not None and math.hypot(dim[2] - dim[0], dim[3] - dim[1]) >= 3.0 * (model.units_per_foot or 9.0):
        return _panel_from_dimension(label, model, dim)
    return None


def _panel_from_dimension(label: Label, model: PageModel, dim: tuple[float, float, float, float] | None = None) -> tuple[float, float, float, float] | None:
    """Shear wall panel = the wall beside the tag, between the ends of the
    dimension drawn with the tag."""
    dim = dim or _dimension_span(label, model)
    if dim is None:
        return None
    wall = _wall_beside(label, model) or _line_beyond(label, dim, model)
    if wall is None:
        return None
    lo = _project(wall, dim[0], dim[1])
    hi = _project(wall, dim[2], dim[3])
    lo, hi = min(lo, hi), max(lo, hi)
    length = math.hypot(wall[2] - wall[0], wall[3] - wall[1])
    lo, hi = max(lo, 0.0), min(hi, length)
    if hi - lo < 12:
        return None
    return (*_point_on(wall, lo), *_point_on(wall, hi))


def _line_beyond(label: Label, dim: tuple[float, float, float, float], model: PageModel) -> tuple[float, float, float, float] | None:
    """Nearest line parallel to a dimension on the far side of the tag
    (the wall the dimensioned panel is on)."""
    if model.fine_index is None:
        return None
    dl = math.hypot(dim[2] - dim[0], dim[3] - dim[1]) or 1.0
    ux, uy = (dim[2] - dim[0]) / dl, (dim[3] - dim[1]) / dl
    side = (label.cx - dim[0]) * -uy + (label.cy - dim[1]) * ux
    sgn = 1.0 if side >= 0 else -1.0
    reach = 4.0 * label.size
    best: tuple[float, tuple[float, float, float, float]] | None = None
    x0, x1 = min(dim[0], dim[2]) - 4, max(dim[0], dim[2]) + 4
    y0, y1 = min(dim[1], dim[3]) - 4, max(dim[1], dim[3]) + 4
    for i in model.fine_index.near(x0 - reach, y0 - reach, x1 + reach, y1 + reach):
        sg = model.fine[i]
        if sg[4] < 0.8 * dl or _angle_diff(_seg_angle(sg), _seg_angle((*dim, dl))) > 2:
            continue
        off = (((sg[0] + sg[2]) / 2.0) - dim[0]) * -uy + (((sg[1] + sg[3]) / 2.0) - dim[1]) * ux
        if off * sgn <= abs(side) + 1.0 or abs(off) > abs(side) + reach:
            continue
        a = (sg[0] - dim[0]) * ux + (sg[1] - dim[1]) * uy
        b = (sg[2] - dim[0]) * ux + (sg[3] - dim[1]) * uy
        if min(a, b) > 4 or max(a, b) < dl - 4:
            continue
        if best is None or abs(off) < best[0]:
            best = (abs(off), (sg[0], sg[1], sg[2], sg[3]))
    return best[1] if best else None


def _wall_beside(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Double-line wall a wall-type tag sits beside (framing rules)."""
    seed = _wall_seed_beside(label, model)
    return _wall_from_seed(seed, model, True) if seed is not None else None


def opening_at(label: Label, model: PageModel) -> tuple[float, float, float, float] | None:
    """Opening (window / door gap in the wall) a header tag marks: the gap
    between drawn wall pieces nearest the tag, along the wall beside it,
    1.5-20 ft wide. Returned as a line across the opening on the wall's
    centre line."""
    assert model.index is not None
    seed = _wall_seed_beside(label, model)
    if seed is None:
        return None
    upf = model.units_per_foot or 9.0
    ux, uy = (seed[2] - seed[0]) / seed[4], (seed[3] - seed[1]) / seed[4]
    nx, ny = -uy, ux
    ox, oy = seed[0], seed[1]
    ang = _seg_angle(seed)
    t0 = (label.cx - ox) * ux + (label.cy - oy) * uy
    reach = 25.0 * upf
    pieces: list[tuple[float, float]] = []
    shift = None
    for j in model.index.near(min(ox + ux * (t0 - reach), ox + ux * (t0 + reach)) - 12, min(oy + uy * (t0 - reach), oy + uy * (t0 + reach)) - 12,
                              max(ox + ux * (t0 - reach), ox + ux * (t0 + reach)) + 12, max(oy + uy * (t0 - reach), oy + uy * (t0 + reach)) + 12):
        o = model.segments[j]
        if o[4] < 6 or is_light(o) or _angle_diff(_seg_angle(o), ang) > 1.5:
            continue
        na = (o[0] - ox) * nx + (o[1] - oy) * ny
        nb = (o[2] - ox) * nx + (o[3] - oy) * ny
        if abs(na) <= 1.5 and abs(nb) <= 1.5:
            a = (o[0] - ox) * ux + (o[1] - oy) * uy
            b = (o[2] - ox) * ux + (o[3] - oy) * uy
            pieces.append((min(a, b), max(a, b)))
        elif 2.0 <= abs(na) <= 10.0 and abs(na - nb) <= 1.0 and (shift is None or abs(na) < abs(shift)):
            shift = na
    if len(pieces) < 2:
        return None
    pieces.sort()
    merged: list[list[float]] = []
    for a, b in pieces:
        if merged and a <= merged[-1][1] + 1.0:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    best: tuple[float, float, float] | None = None
    for (a0, a1), (b0, b1) in zip(merged, merged[1:]):
        lo, hi = a1, b0
        w = hi - lo
        if not (1.5 * upf <= w <= 20.0 * upf):
            continue
        d = 0.0 if lo <= t0 <= hi else min(abs(t0 - lo), abs(t0 - hi))
        if d <= 3.0 * upf and (best is None or d < best[0]):
            best = (d, lo, hi)
    if best is None:
        return None
    c = (shift or 0.0) / 2.0
    sx, sy = ox + nx * c, oy + ny * c
    return (sx + ux * best[1], sy + uy * best[1], sx + ux * best[2], sy + uy * best[2])


def _is_dimension_line(sg: Seg, model: PageModel) -> bool:
    """A dimension line: a diagonal tick across each end."""
    if model.fine_index is None:
        return False
    ticks = 0
    for ex, ey in ((sg[0], sg[1]), (sg[2], sg[3])):
        for j in model.fine_index.near(ex - 4, ey - 4, ex + 4, ey + 4):
            o = model.fine[j]
            if (
                3 <= o[4] <= 16
                and 25 <= _angle_diff(_seg_angle(o), _seg_angle(sg)) <= 65
                and _pt_seg_dist(ex, ey, o) <= 1.5
                and math.hypot((o[0] + o[2]) / 2.0 - ex, (o[1] + o[3]) / 2.0 - ey) <= 2.5
            ):
                ticks += 1
                break
    return ticks >= 2


def _has_partner(sg: Seg, model: PageModel, lo: float = 2.0, hi: float = 10.0) -> bool:
    """A parallel face ``lo``..``hi`` units away (a double-line wall)."""
    assert model.index is not None
    ux, uy = (sg[2] - sg[0]) / sg[4], (sg[3] - sg[1]) / sg[4]
    for j in model.index.near(min(sg[0], sg[2]) - hi - 1, min(sg[1], sg[3]) - hi - 1, max(sg[0], sg[2]) + hi + 1, max(sg[1], sg[3]) + hi + 1):
        o = model.segments[j]
        if o is sg or o[4] < 20 or _angle_diff(_seg_angle(o), _seg_angle(sg)) > 2:
            continue
        off = abs(((o[0] + o[2]) / 2.0 - sg[0]) * -uy + ((o[1] + o[3]) / 2.0 - sg[1]) * ux)
        if lo <= off <= hi:
            a = (o[0] - sg[0]) * ux + (o[1] - sg[1]) * uy
            b = (o[2] - sg[0]) * ux + (o[3] - sg[1]) * uy
            if min(max(a, b), sg[4]) - max(min(a, b), 0.0) > 0.3 * min(o[4], sg[4]):
                return True
    return False


def _wall_seed_on_line(line: tuple[float, float, float, float], model: PageModel) -> Seg | None:
    """Wall face along a known line (a shear / strap panel): parallel, within
    6 units, overlapping it, with a second face."""
    assert model.index is not None
    ll = math.hypot(line[2] - line[0], line[3] - line[1]) or 1.0
    ux, uy = (line[2] - line[0]) / ll, (line[3] - line[1]) / ll
    ang = _fold(math.degrees(math.atan2(uy, ux)))
    best: tuple[float, Seg] | None = None
    for j in model.index.near(min(line[0], line[2]) - 8, min(line[1], line[3]) - 8, max(line[0], line[2]) + 8, max(line[1], line[3]) + 8):
        o = model.segments[j]
        if o[4] < 20 or is_light(o) or _angle_diff(_seg_angle(o), ang) > 2:
            continue
        off = abs(((o[0] + o[2]) / 2.0 - line[0]) * -uy + ((o[1] + o[3]) / 2.0 - line[1]) * ux)
        if off > 6.0:
            continue
        a = (o[0] - line[0]) * ux + (o[1] - line[1]) * uy
        b = (o[2] - line[0]) * ux + (o[3] - line[1]) * uy
        if min(max(a, b), ll) - max(min(a, b), 0.0) < 0.3 * min(ll, o[4]) or not _has_partner(o, model):
            continue
        if best is None or off < best[0]:
            best = (off, o)
    return best[1] if best else None


def wall_between_walls(
    label: Label, model: PageModel, on_line: tuple[float, float, float, float] | None = None
) -> tuple[float, float, float, float] | None:
    """Wall a wall-type tag names, the way an estimator measures it: along
    the wall beside the tag, from the centre of the intersecting wall on one
    side to the centre of the one on the other side. Window / door gaps in
    the wall are bridged; a gap with a wall across it (a corridor) is not."""
    assert model.index is not None
    seed = _wall_seed_on_line(on_line, model) if on_line is not None else _wall_seed_beside(label, model)
    if seed is None:
        return None
    upf = model.units_per_foot or 9.0
    ux, uy = (seed[2] - seed[0]) / seed[4], (seed[3] - seed[1]) / seed[4]
    nx, ny = -uy, ux
    ox, oy = seed[0], seed[1]
    ang = _seg_angle(seed)

    def along(x: float, y: float) -> float:
        return (x - ox) * ux + (y - oy) * uy

    def across(x: float, y: float) -> float:
        return (x - ox) * nx + (y - oy) * ny

    # Nearest face of the wall on the other side (for the centre line).
    centre_shift = 0.0
    best_off: float | None = None
    for j in model.index.near(min(seed[0], seed[2]) - 11, min(seed[1], seed[3]) - 11, max(seed[0], seed[2]) + 11, max(seed[1], seed[3]) + 11):
        o = model.segments[j]
        if o is seed or o[4] < 20 or _angle_diff(_seg_angle(o), ang) > 2:
            continue
        a_o, b_o = along(o[0], o[1]), along(o[2], o[3])
        if min(max(a_o, b_o), seed[4]) - max(min(a_o, b_o), 0.0) < 0.3 * min(o[4], seed[4]):
            continue
        off = across((o[0] + o[2]) / 2.0, (o[1] + o[3]) / 2.0)
        if 2.0 <= abs(off) <= 10.0 and (best_off is None or abs(off) < abs(best_off)):
            best_off = off
    if best_off is not None:
        centre_shift = best_off / 2.0
    t0 = along((on_line[0] + on_line[2]) / 2.0, (on_line[1] + on_line[3]) / 2.0) if on_line is not None else along(label.cx, label.cy)
    reach = 70.0 * upf
    band = 14.0
    # Wall face pieces along the line (both faces), and walls across it.
    cover: list[tuple[float, float]] = []
    stops: list[float] = []
    x0 = min(ox + ux * (t0 - reach), ox + ux * (t0 + reach)) - band
    x1 = max(ox + ux * (t0 - reach), ox + ux * (t0 + reach)) + band
    y0 = min(oy + uy * (t0 - reach), oy + uy * (t0 + reach)) - band
    y1 = max(oy + uy * (t0 - reach), oy + uy * (t0 + reach)) + band
    for j in model.index.near(x0, y0, x1, y1):
        o = model.segments[j]
        if o[4] < 6 or is_light(o):
            continue
        d_ang = _angle_diff(_seg_angle(o), ang)
        a, b = along(o[0], o[1]), along(o[2], o[3])
        na, nb = across(o[0], o[1]), across(o[2], o[3])
        if d_ang <= 1.5:
            if max(abs(na), abs(nb)) <= abs(centre_shift) * 2 + 1.5 and (abs(na - 0) <= 1.5 or abs(na - 2 * centre_shift) <= 1.5):
                cover.append((min(a, b), max(a, b)))
        elif d_ang >= 80 and o[4] >= 20:
            # Reaches the wall line (touches or crosses it) and is a wall.
            lo_n, hi_n = min(na, nb), max(na, nb)
            if lo_n <= centre_shift + band and hi_n >= centre_shift - band and _has_partner(o, model):
                stops.append((a + b) / 2.0)
    if not cover:
        return None
    # Pair the faces of each crossing wall into one centre.
    stops.sort()
    centres: list[float] = []
    group: list[float] = []
    for st in stops:
        if group and st - group[-1] > 11.0:
            centres.append(sum(group) / len(group))
            group = []
        group.append(st)
    if group:
        centres.append(sum(group) / len(group))
    left = [c for c in centres if c < t0 - 2.0]
    right = [c for c in centres if c > t0 + 2.0]
    cover.sort()
    # Stretch of wall around the tag: covered pieces joined across gaps
    # (openings) that no crossing wall interrupts.
    merged: list[list[float]] = []
    for a, b in cover:
        if merged and a <= merged[-1][1] + 1.0:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    lo_cov = min(m[0] for m in merged)
    hi_cov = max(m[1] for m in merged)
    # A tagged wall ends at walls on both sides; without them this is not
    # a wall run we can measure (the caller falls back).
    if not left or not right:
        return None
    lo, hi = max(left), min(right)
    lo = max(lo, lo_cov - 12.0)
    hi = min(hi, hi_cov + 12.0)
    # The wall must really run there: enough of [lo, hi] drawn as wall.
    drawn = sum(max(0.0, min(m[1], hi) - max(m[0], lo)) for m in merged)
    if hi - lo < 12.0 or drawn < 0.35 * (hi - lo):
        return None
    sx, sy = ox + nx * centre_shift, oy + ny * centre_shift
    return (sx + ux * lo, sy + uy * lo, sx + ux * hi, sy + uy * hi)


def _wall_seed_beside(label: Label, model: PageModel) -> Seg | None:
    """Wall face a wall-type tag sits beside: the nearest face the tag
    projects onto that has a parallel face 2-10 units away; heavier lines
    first (grid lines are thin)."""
    assert model.index is not None
    cx, cy = label.cx, label.cy
    radius = max(30.0, 3.5 * label.size)
    pad = 1.4 * label.size
    bx0, by0, bx1, by1 = label.rect[0] - pad, label.rect[1] - pad, label.rect[2] + pad, label.rect[3] + pad
    tag_len = max(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) + 2 * pad
    cands: list[tuple[float, Seg]] = []
    for i in model.index.near(cx - radius, cy - radius, cx + radius, cy + radius):
        sg = model.segments[i]
        if sg[4] < 30 or is_light(sg):
            continue
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        if bx0 <= mx <= bx1 and by0 <= my <= by1 and sg[4] <= tag_len * 1.6:
            continue
        ux, uy = (sg[2] - sg[0]) / sg[4], (sg[3] - sg[1]) / sg[4]
        t = (cx - sg[0]) * ux + (cy - sg[1]) * uy
        if t < -6 or t > sg[4] + 6:
            continue
        d = abs((cx - sg[0]) * -uy + (cy - sg[1]) * ux)
        if d > radius:
            continue
        partner = False
        for j in model.index.near(min(sg[0], sg[2]) - 11, min(sg[1], sg[3]) - 11, max(sg[0], sg[2]) + 11, max(sg[1], sg[3]) + 11):
            o = model.segments[j]
            if o is sg or o[4] < 20 or _angle_diff(_seg_angle(o), _seg_angle(sg)) > 2:
                continue
            off = abs(((o[0] + o[2]) / 2.0 - sg[0]) * -uy + ((o[1] + o[3]) / 2.0 - sg[1]) * ux)
            if 2.0 <= off <= 10.0:
                partner = True
                break
        if not partner or _is_dimension_line(sg, model):
            continue
        cands.append((d, sg))
    if not cands:
        return None
    # Walls are drawn heavier than dimension / leader lines: keep the
    # heavier candidates, then the nearest.
    maxw = max((c[1][5] or 0.0) for c in cands)
    heavy = [c for c in cands if (c[1][5] or 0.0) >= 0.6 * maxw] or cands
    return min(heavy, key=lambda c: (int(round(c[0] / 6.0)), -(c[1][5] or 0.0)))[1]


def _hatch_extent(run: tuple[float, float, float, float], t_tag: float, model: PageModel) -> tuple[float, float] | None:
    """Stretch of a wall run drawn hatched (shear / strap-braced panel)
    nearest ``t_tag`` (distance along the run)."""
    if model.fine_index is None:
        return None
    length = math.hypot(run[2] - run[0], run[3] - run[1])
    if length < 1:
        return None
    ux, uy = (run[2] - run[0]) / length, (run[3] - run[1]) / length
    hits: list[float] = []
    for i in model.fine_index.near(min(run[0], run[2]) - 8, min(run[1], run[3]) - 8, max(run[0], run[2]) + 8, max(run[1], run[3]) + 8):
        sg = model.fine[i]
        ln = math.hypot(sg[2] - sg[0], sg[3] - sg[1])
        if not (2.0 <= ln <= 14.0):
            continue
        cos = abs(((sg[2] - sg[0]) * ux + (sg[3] - sg[1]) * uy) / ln)
        if not (0.4 <= cos <= 0.92):
            continue  # hatch strokes run at an angle across the wall
        mx, my = (sg[0] + sg[2]) / 2.0, (sg[1] + sg[3]) / 2.0
        if abs((mx - run[0]) * -uy + (my - run[1]) * ux) > 5.0:
            continue
        hits.append((mx - run[0]) * ux + (my - run[1]) * uy)
    if len(hits) < 4:
        return None
    hits.sort()
    groups: list[list[float]] = [[hits[0]]]
    for h in hits[1:]:
        if h - groups[-1][-1] <= 8.0:
            groups[-1].append(h)
        else:
            groups.append([h])
    groups = [g for g in groups if len(g) >= 4]
    if not groups:
        return None
    reach = 4.0 * (model.units_per_foot or 9.0)

    def gap(g: list[float]) -> float:
        return 0.0 if g[0] <= t_tag <= g[-1] else min(abs(g[0] - t_tag), abs(g[-1] - t_tag))

    best = min(groups, key=gap)
    if gap(best) > reach:
        return None
    return max(0.0, best[0] - 1.0), min(length, best[-1] + 1.0)


def _clip_same_type_overlaps(entries: list[dict[str, Any]]) -> None:
    """Same wall type on the same line: no stretch counted twice. Shorter
    runs keep their stretch; a longer one keeps its largest uncovered piece
    (dropped when nothing useful is left)."""
    kept: list[tuple[str, tuple[float, float, float, float]]] = []

    def length(r) -> float:
        return math.hypot(r[2] - r[0], r[3] - r[1])

    for e in sorted((e for e in entries if e.get("run")), key=lambda e: length(e["run"])):
        run = e["run"]
        L = length(run)
        if L < 1:
            continue
        ux, uy = (run[2] - run[0]) / L, (run[3] - run[1]) / L
        des = e["info"].get("designation") or ""
        pieces = [(0.0, L)]
        for d2, r in kept:
            if d2 != des:
                continue
            if abs((r[0] - run[0]) * -uy + (r[1] - run[1]) * ux) > 4 or abs((r[2] - run[0]) * -uy + (r[3] - run[1]) * ux) > 4:
                continue
            a = (r[0] - run[0]) * ux + (r[1] - run[1]) * uy
            b = (r[2] - run[0]) * ux + (r[3] - run[1]) * uy
            lo, hi = min(a, b), max(a, b)
            nxt = []
            for p0, p1 in pieces:
                if hi <= p0 or lo >= p1:
                    nxt.append((p0, p1))
                    continue
                if lo > p0:
                    nxt.append((p0, lo))
                if hi < p1:
                    nxt.append((hi, p1))
            pieces = nxt
        pieces = [pc for pc in pieces if pc[1] - pc[0] >= 12.0]
        if not pieces:
            e["run"] = None
            continue
        p0, p1 = max(pieces, key=lambda pc: pc[1] - pc[0])
        e["run"] = (run[0] + ux * p0, run[1] + uy * p0, run[0] + ux * p1, run[1] + uy * p1)
        kept.append((des, e["run"]))


def _heavy_line_at(label: Label, model: PageModel) -> Seg | None:
    """Heaviest line parallel to a member tag, just beside it and running
    under it (a boxed CFS beam drawn as a thick line)."""
    assert model.index is not None
    reach = 2.0 * label.size
    ux, uy = math.cos(math.radians(label.angle)), math.sin(math.radians(label.angle))
    best: tuple[tuple[float, float], Seg] | None = None
    for i in model.index.near(label.rect[0] - reach, label.rect[1] - reach, label.rect[2] + reach, label.rect[3] + reach):
        sg = model.segments[i]
        if sg[4] < 24 or _angle_diff(_seg_angle(sg), label.angle) > 3:
            continue
        d = abs((label.cx - sg[0]) * -uy + (label.cy - sg[1]) * ux)
        if d > reach:
            continue
        t = (label.cx - sg[0]) * (sg[2] - sg[0]) / sg[4] + (label.cy - sg[1]) * (sg[3] - sg[1]) / sg[4]
        if t < -6 or t > sg[4] + 6:
            continue
        score = (-(sg[5] or 0.0), d)
        if best is None or score < best[0]:
            best = (score, sg)
    if best is None:
        return None
    # Only a line clearly heavier than the thin framing lines around it.
    return best[1] if (best[1][5] or 0.0) >= 0.8 else None


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
        # Never walk through a wall: stop at the first line across the path.
        stop = None
        for i in model.fine_index.near(min(ex, px + ux * grown) - 3, min(ey, py + uy * grown) - 3,
                                       max(ex, px + ux * grown) + 3, max(ey, py + uy * grown) + 3):
            sg = model.fine[i]
            ln = math.hypot(sg[2] - sg[0], sg[3] - sg[1])
            if ln < 3.0 or abs(((sg[2] - sg[0]) * ux + (sg[3] - sg[1]) * uy) / ln) > 0.2:
                continue
            n0 = (sg[0] - px) * -uy + (sg[1] - py) * ux
            n1 = (sg[2] - px) * -uy + (sg[3] - py) * ux
            if n0 * n1 > 0 and min(abs(n0), abs(n1)) > 0.5:
                continue
            t = ((sg[0] + sg[2]) / 2.0 - px) * ux + ((sg[1] + sg[3]) / 2.0 - py) * uy
            if ext + 0.5 < t < grown - 0.5 and (stop is None or t < stop):
                stop = t
        if stop is not None:
            return stop
        ext = grown
    return ext


def _series_from_leader(
    label: Label, info: dict[str, Any], model: PageModel
) -> tuple[list[tuple[float, float, float, float]], bool, list[tuple[float, float]] | None] | None:
    """Bay framed from a tag with a leader (framing rules).

    House framing plans print 'T-1' / 'RJ-1' beside the bay with a leader to
    the crossing of two lines: the distribution arrow (wall to wall, across
    the members) and the span line (along the members). Members are placed
    at the schedule spacing across the whole distribution, each as long as
    the span line. The span line is the one closer to the schedule length
    (the longer one when there is none).
    """
    assert model.index is not None
    upf = model.units_per_foot
    if not upf or not info.get("spacing_in"):
        return None
    spacing_units = info["spacing_in"] / 12.0 * upf
    cx, cy = label.cx, label.cy
    half = math.hypot(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) / 2.0
    near_r = half + 1.2 * label.size
    best: tuple[float, tuple[float, float, float, float], tuple[float, float, float, float]] | None = None
    for i in model.index.near(cx - near_r - 120, cy - near_r - 120, cx + near_r + 120, cy + near_r + 120):
        ld = model.segments[i]
        if not (6 <= ld[4] <= 140):
            continue
        d0 = math.hypot(ld[0] - cx, ld[1] - cy)
        d1 = math.hypot(ld[2] - cx, ld[3] - cy)
        if min(d0, d1) > near_r or max(d0, d1) < near_r * 0.8:
            continue
        fx, fy = (ld[2], ld[3]) if d1 > d0 else (ld[0], ld[1])
        lines_at: list[tuple[float, float, float, float]] = []
        for j in model.index.near(fx - 3, fy - 3, fx + 3, fy + 3):
            w = model.segments[j]
            if w is ld or w[4] < 20 or _angle_diff(_seg_angle(w), _seg_angle(ld)) < 15:
                continue
            if _pt_seg_dist(fx, fy, w) > 2.5:
                continue
            run = merge_run(w, model, max_gap=3.0)
            if math.hypot(run[2] - run[0], run[3] - run[1]) < 3 * spacing_units * 0.5:
                continue
            if any(_angle_diff(_fold(math.degrees(math.atan2(run[3] - run[1], run[2] - run[0]))),
                               _fold(math.degrees(math.atan2(o[3] - o[1], o[2] - o[0])))) < 5 for o in lines_at):
                continue
            lines_at.append(run)
        if len(lines_at) < 2:
            continue
        # Two lines at right angles through the leader tip.
        pair = None
        for a_i in range(len(lines_at)):
            for b_i in range(a_i + 1, len(lines_at)):
                a, b = lines_at[a_i], lines_at[b_i]
                ang_a = math.degrees(math.atan2(a[3] - a[1], a[2] - a[0]))
                ang_b = math.degrees(math.atan2(b[3] - b[1], b[2] - b[0]))
                if _angle_diff(_fold(ang_a), _fold(ang_b)) >= 80:
                    pair = (a, b)
                    break
            if pair:
                break
        if not pair:
            continue
        score = max(d0, d1)
        if best is None or score < best[0]:
            best = (score, pair[0], pair[1])
    if best is None:
        return None
    a, b = best[1], best[2]
    la = math.hypot(a[2] - a[0], a[3] - a[1])
    lb = math.hypot(b[2] - b[0], b[3] - b[1])
    want_ft = info.get("length_ft")
    if want_ft:
        span, dist = (a, b) if abs(la / upf - want_ft) <= abs(lb / upf - want_ft) else (b, a)
    else:
        span, dist = (a, b) if la >= lb else (b, a)
    d_len = math.hypot(dist[2] - dist[0], dist[3] - dist[1])
    if d_len < spacing_units * 0.9:
        return None
    dx, dy = (dist[2] - dist[0]) / d_len, (dist[3] - dist[1]) / d_len
    s_len = math.hypot(span[2] - span[0], span[3] - span[1])
    jx, jy = (span[2] - span[0]) / s_len, (span[3] - span[1]) / s_len
    d_lo = dx * dist[0] + dy * dist[1]
    d_hi = dx * dist[2] + dy * dist[3]
    s_lo = jx * span[0] + jy * span[1]
    s_hi = jx * span[2] + jy * span[3]
    # The arrow lines continue in arrowhead pieces up to the walls: follow
    # them to the tips. The distribution then spans wall to wall and the
    # members reach their bearing walls.
    reach = 3.0 * upf
    d_lo -= _walk_arrow(model, dist, -dx, -dy, reach)
    d_hi += _walk_arrow(model, dist, dx, dy, reach)
    s_lo -= _walk_arrow(model, span, -jx, -jy, reach)
    s_hi += _walk_arrow(model, span, jx, jy, reach)
    # Coordinates: point = dx*d + jx*s (the two axes are perpendicular).
    width = d_hi - d_lo
    count = int(math.floor(width / spacing_units + 1e-6)) + 1
    start = d_lo + (width - (count - 1) * spacing_units) / 2.0
    out: list[tuple[float, float, float, float]] = []
    for k in range(count):
        off = start + k * spacing_units
        out.append((dx * off + jx * s_lo, dy * off + jy * s_lo, dx * off + jx * s_hi, dy * off + jy * s_hi))
    return out, True, _bay_poly(jx, jy, dx, dy, s_lo, s_hi, d_lo, d_hi)


def _bay_poly(ux, uy, nx, ny, s_lo, s_hi, n_lo, n_hi) -> list[tuple[float, float]]:
    def pt(s: float, n: float) -> tuple[float, float]:
        return (ux * s + nx * n, uy * s + ny * n)

    return [pt(s_lo, n_lo), pt(s_hi, n_lo), pt(s_hi, n_hi), pt(s_lo, n_hi)]


def _cast(model: PageModel, ox: float, oy: float, dx: float, dy: float, reach: float, accept) -> float | None:
    """Distance along (dx, dy) from (ox, oy) to the first segment hit that ``accept`` likes."""
    assert model.index is not None
    ex, ey = ox + dx * reach, oy + dy * reach
    best: float | None = None
    for i in model.index.near(min(ox, ex), min(oy, ey), max(ox, ex), max(oy, ey)):
        s = model.segments[i]
        if not accept(s):
            continue
        x3, y3, x4, y4 = s[0], s[1], s[2], s[3]
        den = dx * (y3 - y4) - dy * (x3 - x4)
        if abs(den) < 1e-9:
            continue
        t = ((ox - x3) * (y3 - y4) - (oy - y3) * (x3 - x4)) / den
        u = -(dx * (oy - y3) - dy * (ox - x3)) / den
        if 2.0 < t <= reach and -0.02 <= u <= 1.02 and (best is None or t < best):
            best = t
    return best


def _cast_supports(label: Label, model: PageModel, ux: float, uy: float) -> tuple[float | None, float | None]:
    ang = label.angle
    c_u = ux * label.cx + uy * label.cy
    accept = lambda s: s[4] >= 30 and _angle_diff(_seg_angle(s), ang) >= 60  # noqa: E731
    reach = 1400.0
    a = _cast(model, label.cx, label.cy, ux, uy, reach, accept)
    b = _cast(model, label.cx, label.cy, -ux, -uy, reach, accept)
    if a is None or b is None:
        return None, None
    return c_u - b, c_u + a


def _cast_edges(label: Label, model: PageModel, ux: float, uy: float, span: float) -> tuple[float | None, float | None]:
    nx, ny = -uy, ux
    ang = label.angle
    c_n = nx * label.cx + ny * label.cy
    accept = lambda s: s[4] >= 0.5 * span and _angle_diff(_seg_angle(s), ang) <= 3  # noqa: E731
    a = _cast(model, label.cx, label.cy, nx, ny, 1400.0, accept)
    b = _cast(model, label.cx, label.cy, -nx, -ny, 1400.0, accept)
    if a is None or b is None:
        return None, None
    return c_n - b, c_n + a


# ── geometry: walls ───────────────────────────────────────────────────


def _leader_target(label: Label, model: PageModel) -> Seg | None:
    """Wall a tag points at through its leader line, if it has one.

    Architectural wall tags often sit beside the wall in an ellipse or
    hexagon with a short leader to the wall; the wall is the long line
    at the leader's far end.
    """
    assert model.index is not None
    cx, cy = label.cx, label.cy
    half = math.hypot(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) / 2.0
    near_r = half + 1.6 * label.size
    best: tuple[float, Seg] | None = None
    for i in model.index.near(cx - near_r - 140, cy - near_r - 140, cx + near_r + 140, cy + near_r + 140):
        ld = model.segments[i]
        if not (8 <= ld[4] <= 160):
            continue
        d0 = math.hypot(ld[0] - cx, ld[1] - cy)
        d1 = math.hypot(ld[2] - cx, ld[3] - cy)
        if min(d0, d1) > near_r or max(d0, d1) < near_r:
            continue
        fx, fy = (ld[2], ld[3]) if d1 > d0 else (ld[0], ld[1])
        for j in model.index.near(fx - 4, fy - 4, fx + 4, fy + 4):
            w = model.segments[j]
            if w is ld or w[4] < 30 or is_light(w) or _angle_diff(_seg_angle(w), _seg_angle(ld)) < 20:
                continue
            if _pt_seg_dist(fx, fy, w) <= 3.0:
                score = max(d0, d1)
                if best is None or score < best[0]:
                    best = (score, w)
    return best[1] if best else None


def _wall_run(label: Label, model: PageModel, strict: bool = False) -> tuple[float, float, float, float] | None:
    assert model.index is not None
    cx, cy = label.cx, label.cy
    via_leader = _leader_target(label, model)
    if via_leader is not None:
        return _wall_from_seed(via_leader, model, strict)
    radius = max(30.0, 3.5 * label.size)
    near: list[tuple[Seg, float]] = []
    for i in model.index.near(cx - radius, cy - radius, cx + radius, cy + radius):
        s = model.segments[i]
        if s[4] < 30 or is_light(s):
            continue
        d = _pt_seg_dist(cx, cy, s)
        if d <= radius:
            near.append((s, d))
    if not near:
        return None
    # The tag's own box (and its leader) are the nearest lines: skip any
    # segment whose midpoint sits on the tag box.
    pad = 1.4 * label.size
    bx0, by0, bx1, by1 = label.rect[0] - pad, label.rect[1] - pad, label.rect[2] + pad, label.rect[3] + pad
    tag_len = max(label.rect[2] - label.rect[0], label.rect[3] - label.rect[1]) + 2 * pad

    def on_tag(s: Seg) -> bool:
        mx, my = (s[0] + s[2]) / 2.0, (s[1] + s[3]) / 2.0
        return bx0 <= mx <= bx1 and by0 <= my <= by1 and s[4] <= tag_len * 1.6

    near = [it for it in near if not on_tag(it[0])]
    if not near:
        return None
    aligned = [it for it in near if _angle_diff(_seg_angle(it[0]), label.angle) <= 10.0]
    pool = aligned or near
    seed = min(pool, key=lambda it: (round(it[1] / 6.0), -it[0][4]))[0]
    return _wall_from_seed(seed, model, strict)


def _wall_from_seed(seed: Seg, model: PageModel, strict: bool = False) -> tuple[float, float, float, float]:
    """Wall run through ``seed``: merged, then centred between its faces.
    ``strict`` (framing rules): only the same line weight, no gaps - a wall
    stops where it stops, never bridging a corridor or opening."""
    assert model.index is not None
    run = merge_run(seed, model, max_gap=4.0, width_tol=0.05) if strict else merge_run(seed, model, max_gap=16.0)
    # Double-line wall: average with the parallel face within 2..16 units.
    ang = _seg_angle(seed)
    rad = math.radians(ang)
    ux, uy = math.cos(rad), math.sin(rad)
    nx, ny = -uy, ux
    base = nx * run[0] + ny * run[1]
    lo = ux * run[0] + uy * run[1]
    hi = ux * run[2] + uy * run[3]
    lo, hi = min(lo, hi), max(lo, hi)
    best: tuple[float, float, float] | None = None
    for i in model.index.near(min(run[0], run[2]) - 18, min(run[1], run[3]) - 18, max(run[0], run[2]) + 18, max(run[1], run[3]) + 18):
        s = model.segments[i]
        if s[4] < 0.3 * (hi - lo) or _angle_diff(_seg_angle(s), ang) > 2.0 or not same_pen(seed, s):
            continue
        off = nx * (s[0] + s[2]) / 2.0 + ny * (s[1] + s[3]) / 2.0 - base
        if 1.5 <= abs(off) <= 16.0:
            a = ux * s[0] + uy * s[1]
            b = ux * s[2] + uy * s[3]
            overlap = min(hi, max(a, b)) - max(lo, min(a, b))
            if overlap > 0.5 * (hi - lo) and (best is None or overlap > best[0]):
                best = (overlap, off, 0.0)
    shift = best[1] / 2.0 if best else 0.0
    return (run[0] + nx * shift, run[1] + ny * shift, run[2] + nx * shift, run[3] + ny * shift)


# ── geometry: columns ─────────────────────────────────────────────────


def _columns(
    model: PageModel,
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]],
    default_name: str | None,
    marks: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    assert model.index is not None
    words: list[tuple[float, float]] = [(lab.cx, lab.cy) for lab in model.labels]
    cand: list[tuple[float, float, float, float, bool]] = []
    for b in model.boxes:
        w, h = b[2] - b[0], b[3] - b[1]
        if max(w, h) / max(min(w, h), 0.1) > 1.8 or max(w, h) < 4.5 or max(w, h) > 30:
            continue
        cxb, cyb = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        if cxb > model.width * 0.92 or cyb > model.height * 0.95:
            continue  # title block / border strip
        if _in_rects(cxb, cyb, model.schedule_rects, 6):
            continue
        if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in words):
            continue  # a tag box with text inside, not a column
        reach = max(b[2] - b[0], b[3] - b[1], 10.0)
        if any(
            len(lab.text) <= 4
            and not _COL_MARK_RE.match(re.sub(r"\s+", "", lab.text))
            and math.hypot(lab.cx - cxb, lab.cy - cyb) <= reach
            for lab in model.labels
        ):
            continue  # part of a grid bubble / symbol with a short mark beside it
        cand.append(b)
    # Same-size symbols repeated on the sheet.
    sizes: dict[tuple[int, int], list[tuple[float, float, float, float, bool]]] = {}
    for b in cand:
        key = (int(round((b[2] - b[0]) / 1.5)), int(round((b[3] - b[1]) / 1.5)))
        sizes.setdefault(key, []).append(b)
    out: list[dict[str, Any]] = []
    col_labels = labels_by_cat.get("columns", [])
    for group in sizes.values():
        # De-duplicate concentric/double-drawn boxes.
        uniq: list[tuple[float, float, float, float, bool]] = []
        for b in group:
            c = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
            if any(abs(c[0] - (u[0] + u[2]) / 2.0) < 2 and abs(c[1] - (u[1] + u[3]) / 2.0) < 2 for u in uniq):
                continue
            uniq.append(b)
        if len(uniq) < 3:
            continue
        # Column symbols stand on a grid, far apart; boxes huddled together
        # are parts of one symbol (section / detail markers).
        def _c(b):
            return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

        # Checked against every candidate box, not just this size: legend
        # swatches stacked one under another are not columns.
        huddle = min(36.0, 3.0 * model.units_per_foot) if model.units_per_foot else 36.0
        spread = []
        for b in uniq:
            cb = _c(b)
            nearest = min(
                (d for o in cand if o is not b for d in [math.hypot(cb[0] - _c(o)[0], cb[1] - _c(o)[1])] if d > 2.0),
                default=1e9,
            )
            if nearest >= huddle:
                spread.append(b)
        uniq = spread
        if len(uniq) < 3:
            continue
        touched: list[tuple[float, float, float, float, bool]] = []
        for b in uniq:
            pad = 3.0
            hit = False
            for i in model.index.near(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad):
                s = model.segments[i]
                if s[4] < 60:
                    continue
                cxb, cyb = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
                if _pt_seg_dist(cxb, cyb, s) <= max(b[2] - b[0], b[3] - b[1]) / 2.0 + pad:
                    hit = True
                    break
            if hit or b[4]:
                touched.append(b)
        if len(touched) < 3 or len(touched) < 0.6 * len(uniq):
            continue
        for b in touched:
            cxb, cyb = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
            named = _column_named(cxb, cyb, labels_by_cat, default_name, marks)
            named["size"] = round(max(b[2] - b[0], b[3] - b[1]), 1)
            out.append(named)
    return out


def _column_symbol(model: PageModel, x: float, y: float) -> list[float] | None:
    if model.detail is None:
        return None
    try:
        from app.modules.takeoff import detail_scan as Z

        return Z.symbol_at(model.detail, x, y)
    except Exception:
        return None


def _detail_leader_ends(model: PageModel):
    """Leader ends of a callout, followed through the small pieces of the
    sheet read at full detail (also when the framing rules did not keep
    them)."""
    m2 = model
    if model.fine_index is None and model.detail is not None:
        import copy

        m2 = copy.copy(model)
        m2.fine = [s[:7] for s in model.detail.segs if s[4] >= 3.0]
        m2.fine_index = SegIndex(m2.fine)
    return lambda lab: [tip for _score, tip in leader_tips(lab, m2)]


def _column_named(
    cxb: float,
    cyb: float,
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]],
    default_name: str | None,
    marks: dict[str, str] | None,
    mark_reach: float = 70.0,
) -> dict[str, Any]:
    """Name a column symbol at (cxb, cyb): the size label or mark next to it,
    the mark read through the column schedule, or a square HSS size printed
    beside it."""
    col_labels = labels_by_cat.get("columns", [])
    size_lab = None
    mark_lab = None
    for lab, info in col_labels:
        d = math.hypot(lab.cx - cxb, lab.cy - cyb)
        if d > 70:
            continue
        if info.get("mark"):
            if d > mark_reach:
                continue  # a mark further off belongs to something else (deck cut marks C2, C17)
            if mark_lab is None or d < mark_lab[0]:
                mark_lab = (d, lab, info["designation"])
        elif size_lab is None or d < size_lab[0]:
            size_lab = (d, lab, info["designation"])
    if size_lab is None:
        # A square HSS / W size printed right beside the symbol.
        for lab, info in labels_by_cat.get("beams", []):
            # Distance to the text box, not its centre: a column
            # callout often starts at the column corner and runs
            # away from it (diagonal on many plans).
            rx = max(lab.rect[0] - cxb, 0.0, cxb - lab.rect[2])
            ry = max(lab.rect[1] - cyb, 0.0, cyb - lab.rect[3])
            d = math.hypot(rx, ry)
            des = info["designation"]
            square = re.match(r"HSS(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)X", des)
            if d <= 22 and square and square.group(1) == square.group(2):
                if size_lab is None or d < size_lab[0]:
                    size_lab = (d, lab, des)
    mark = mark_lab[2] if mark_lab else None
    size = size_lab[2] if size_lab else ((marks or {}).get(mark) if mark else None)
    if not size and not mark and marks and len(set(marks.values())) == 1:
        size = next(iter(marks.values()))
    name = size or mark or default_name or "COLUMN"
    label = f"{mark} {size}" if (mark and size) else name
    src = (size_lab or mark_lab)
    rect = list(src[1].rect) if src else None
    if mark_lab and not size_lab:
        rect = list(mark_lab[1].rect)
    return {
        "mark_obj": mark_lab[1] if mark_lab else None,
        "label_obj": src[1] if src else None,
        "point": (cxb, cyb),
        "designation": name,
        "label": label,
        "mark": mark,
        "label_rect": rect,
        "size": None,
    }


# ── roles: what each member is (OE-DELIVERY 2026-11-03-auto-takeoff-roles) ──
# The role names match the structural Tool Chest sets (SSMA / AISC), so an
# auto markup lands with the same Subject as the tool you would draw it with.

_ROOF_CTX_RE = re.compile(r"ROOF\s+(?:FRAMING|PLAN|TRUSS)|TRUSS\s+LAYOUT|RAFTER", re.IGNORECASE)
_FLOOR_CTX_RE = re.compile(r"FLOOR\s+(?:FRAMING|PLAN|TRUSS|JOIST)|(?:LEVEL|LVL)\s*\d+\s+FRAMING|(?:2ND|3RD|\dTH|SECOND|THIRD)\s+FLOOR", re.IGNORECASE)
_CEILING_CTX_RE = re.compile(r"CEILING\s+(?:FRAMING|JOIST|PLAN)", re.IGNORECASE)
_NLB_RE = re.compile(r"NON[\s-]*(?:LOAD|BEARING|STRUCTURAL)|\bNLB\b|\bNLBW\b|PARTITION|CURTAIN\s*WALL|INTERIOR\s+NON", re.IGNORECASE)
_LB_RE = re.compile(r"LOAD[\s-]*BEARING|\bLBW?\b|\bBEARING\s+WALL|SHEAR\s*WALL|\bSW\b|STRUCTURAL\s+STUD", re.IGNORECASE)


def sheet_context(model: PageModel) -> str | None:
    """'roof', 'floor' or 'ceiling' from the sheet title and notes."""
    roof = floor = ceiling = 0
    for lab in model.labels:
        t = lab.text
        if len(t) > 80:
            continue
        roof += len(_ROOF_CTX_RE.findall(t))
        floor += len(_FLOOR_CTX_RE.findall(t))
        ceiling += len(_CEILING_CTX_RE.findall(t))
    if max(roof, floor, ceiling) == 0:
        return None
    if roof >= floor and roof >= ceiling:
        return "roof"
    return "floor" if floor >= ceiling else "ceiling"


def profile_of(text: str | None) -> str | None:
    """First SSMA / AISC designation inside a schedule row or callout."""
    if not text:
        return None
    m = D._SSMA_RE.search(text) or D._AISC_RE.search(text)
    return D.normalize_designation(m.group(0)) if m else None


def wall_role(tag: str, spec: str | None) -> str:
    text = spec or ""
    if re.search(r"SHEAR", text, re.IGNORECASE) or re.match(r"^SW", tag.upper()):
        return "Shear Wall"
    if _NLB_RE.search(text):
        return "Non-Load Bearing Wall"
    if _LB_RE.search(text):
        return "Load Bearing Wall"
    # A wall type described only as a stud / partition wall (architectural
    # wall types) is a partition unless something says it carries load.
    if re.search(r"METAL\s+STUD\s+WALL|STUD\s+PARTITION|GYP|DRYWALL|FURRING", text, re.IGNORECASE):
        return "Non-Load Bearing Wall"
    t = tag.upper()
    if t.startswith(("IW", "PW", "NW")):
        return "Non-Load Bearing Wall"
    if t.startswith(("EW", "LW", "BW")):
        return "Load Bearing Wall"
    prof = profile_of(text)
    if prof:
        m = re.match(r"(\d{3,4})S\d{3}-(\d{2,3})", prof)
        if m:
            # Heavy studs (54 mil +) carry load; light ones are partitions.
            return "Load Bearing Wall" if int(m.group(2)) >= 54 else "Non-Load Bearing Wall"
    return "CFS Wall"


def assign_roles(items: list[dict[str, Any]], model: PageModel, specs: dict[str, str] | None) -> None:
    ctx = sheet_context(model)
    for it in items:
        cat = it["category"]
        des = str(it.get("designation") or "")
        spec = it.get("spec") or (specs or {}).get(des)
        text = f"{des} {spec or ''} {it.get('label') or ''}"
        role = it.get("role")
        if cat == "walls":
            role = wall_role(des, spec)
        elif cat == "trusses":
            if re.search(r"FLOOR", text, re.IGNORECASE):
                role = "Floor Truss"
            elif re.search(r"ROOF|RAFTER", text, re.IGNORECASE):
                role = "Roof Truss"
            else:
                role = "Floor Truss" if ctx == "floor" else "Roof Truss"
        elif role in ("Steel Joist", "Hat Channel", "Deck"):
            pass
        elif cat == "joists" and D._JOIST_RE.search(des):
            role = "Steel Joist"
        elif cat == "joists" and D._SSMA_RE.search(des):
            role = "CFS Joist"
        elif cat == "joists":
            if re.search(r"CEIL", text, re.IGNORECASE) or ctx == "ceiling":
                role = "Ceiling Joist"
            elif re.search(r"ROOF", text, re.IGNORECASE) or ctx == "roof":
                role = "Roof Joist"
            else:
                role = "Floor Joist"
        elif cat == "beams":
            role = role or "Beam"
        elif cat == "columns":
            role = "Column"
        elif cat == "areas":
            role = "Framing Area"
        elif not role:
            if _JAMB_RE.search(text):
                role = "Jamb"
            elif _HEADER_RE.search(text):
                role = "Header"
            elif des.startswith("L"):
                role = "Angle"
            elif re.match(r"\d{3,4}T\d", des):
                role = "Track"
            elif re.match(r"\d{3,4}S\d", des):
                role = "Stud"
            else:
                role = "Other"
        it["role"] = role
        prof = profile_of(spec) if (spec and not profile_of(des)) else None
        if prof and not it.get("profile"):
            it["profile"] = prof
    _bearing_of_openings(items)


def _seg_dist(px: float, py: float, a: list[float], b: list[float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / L2))
    return math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


def _bearing_of_openings(items: list[dict[str, Any]]) -> None:
    """Headers / jambs take the wall they sit in: load bearing (incl. shear)
    or non-load bearing. With no wall nearby, heavy members (54 mil +) are
    taken as load bearing."""
    walls = [w for w in items if w["category"] == "walls" and len(w.get("points") or []) >= 2]
    for it in items:
        if it.get("role") not in ("Header", "Jamb"):
            continue
        pts = it.get("points") or [it.get("anchor")]
        px = sum(q[0] for q in pts) / len(pts)
        py = sum(q[1] for q in pts) / len(pts)
        best = None
        for w in walls:
            d = _seg_dist(px, py, w["points"][0], w["points"][-1])
            if d <= 40 and (best is None or d < best[0]):
                best = (d, w.get("role"))
        if best:
            bearing = best[1] in ("Load Bearing Wall", "Shear Wall")
        else:
            prof = it.get("profile") or it.get("designation") or ""
            m = re.search(r"\d{3,4}[SLT]\d{3}-(\d{2,3})", str(prof))
            bearing = (int(m.group(1)) >= 54) if m else True
        it["role"] = ("Load Bearing " if bearing else "Non-Load Bearing ") + it["role"]


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


# ── driver ────────────────────────────────────────────────────────────


def _r(v: float) -> float:
    return round(float(v), 2)


def _key(page: int, cat: str, des: str, x: float, y: float, extra: str = "") -> str:
    return f"{page}|{cat}|{des}|{int(round(x / 8.0))},{int(round(y / 8.0))}{('|' + extra) if extra else ''}"


def labels_by_category(model: PageModel, hints=None, skip_spots=None) -> dict[str, list[tuple[Label, dict[str, Any]]]]:
    out: dict[str, list[tuple[Label, dict[str, Any]]]] = {}
    seen: set[tuple[str, int, int]] = set()
    for lab in model.labels:
        if _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
            continue
        if skip_spots and (model.page_no, int(round(lab.cx / 4.0)), int(round(lab.cy / 4.0))) in skip_spots:
            continue
        info = classify(lab, hints)
        if not info:
            continue
        k = (info["designation"], int(round(lab.cx / 4)), int(round(lab.cy / 4)))
        if k in seen:
            continue
        seen.add(k)
        out.setdefault(info["category"], []).append((lab, info))
    return out


_SQUARE_HSS_RE = re.compile(r"HSS\s?(\d+(?:\.\d+)?)\s?[Xx]\s?\1\s?[Xx]")


def name_columns_across_sheets(results: list[dict[str, Any]], sources: list[PageModel], col_marks: dict[str, str] | None) -> int:
    """Unnamed columns take the profile printed at the same grid spot on a
    column plan of the same sheet size (framing plans rarely repeat column
    sizes; the column / foundation plan does). Returns how many were named."""
    named: list[tuple[int, float, float, float, float, str]] = []
    for sm in sources:
        if sm.index is None:
            continue
        for c in _columns(sm, labels_by_category(sm), None, col_marks):
            if c["designation"] != "COLUMN":
                named.append((sm.page_no, sm.width, sm.height, c["point"][0], c["point"][1], c["designation"]))
    if not named:
        return 0
    count = 0
    for page in results:
        size = page.get("_size")
        for it in page["items"]:
            if it["category"] != "columns" or it["designation"] != "COLUMN":
                continue
            x, y = it["points"][0]
            best = None
            for src_page, w, h, sx, sy, des in named:
                if src_page == page["page"] or not size or abs(w - size[0]) > 2 or abs(h - size[1]) > 2:
                    continue
                d = math.hypot(sx - x, sy - y)
                if d <= 8 and (best is None or d < best[0]):
                    best = (d, des, src_page)
            if best:
                it["designation"] = best[1]
                it["label"] = best[1]
                it["spec"] = f"Profile from the column plan, page {best[2]}"
                it["key"] = _key(page["page"], "columns", best[1], x, y)
                count += 1
    return count


def label_quad(lab: "Label") -> list[list[float]]:
    """The text band of a label as 4 corners, following its reading
    direction, so the sheet highlight hugs rotated / diagonal text the way a
    Revu highlighter does (OE-DELIVERY 2026-11-02-revu-workspace)."""
    ux, uy = lab.ux, lab.uy
    norm = math.hypot(ux, uy) or 1.0
    ux, uy = ux / norm, uy / norm
    nx, ny = -uy, ux
    xs = (lab.rect[0], lab.rect[2])
    ys = (lab.rect[1], lab.rect[3])
    proj = [ux * x + uy * y for x in xs for y in ys]
    lo, hi = min(proj), max(proj)
    c_n = nx * lab.cx + ny * lab.cy
    half = max(lab.size * 0.62, 2.0)
    # A long rotated label's bbox overstates its length: cap it to the text.
    text_len = max(len(lab.text), 1) * lab.size * 0.62
    mid = (lo + hi) / 2.0
    if hi - lo > text_len * 1.15:
        lo, hi = mid - text_len / 2.0, mid + text_len / 2.0
    pts = []
    for a, b in ((lo, -half), (hi, -half), (hi, half), (lo, half)):
        pts.append([round(ux * a + nx * (c_n + b), 2), round(uy * a + ny * (c_n + b), 2)])
    return pts


def is_detail_sheet(model: PageModel) -> bool:
    if not model.units_per_foot:
        return False
    return model.units_per_foot / 72.0 > _DETAIL_SCALE_IN_PER_FT


def take_off_page(
    model: PageModel,
    categories: Iterable[str],
    *,
    hints: dict[str, dict[str, Any]] | None = None,
    specs: dict[str, str] | None = None,
    column_name: str | None = None,
    skip_spots: set[tuple[int, int, int]] | None = None,
    col_marks: dict[str, str] | None = None,
    rules: bool = False,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:
    """Run every requested category on one page model."""
    from app.modules.takeoff import framing_rules as FR

    wanted = set(categories) & set(CATEGORIES)
    rule_on = bool(rules and model.kind)
    if rule_on:
        wanted &= FR.ALLOWED.get(model.kind or "", set())
    rule_ctx = (model.kind or "", model.level, model.fsched)
    rule_infos: dict[tuple[str, float, float], dict[str, Any]] = {}
    rule_counts: list[tuple[Label, dict[str, Any]]] = []
    items: list[dict[str, Any]] = []
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]] = {}
    seen: set[tuple[str, int, int]] = set()
    for lab in model.labels:
        if _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
            continue
        if skip_spots and (model.page_no, int(round(lab.cx / 4.0)), int(round(lab.cy / 4.0))) in skip_spots:
            continue
        info = None
        if rule_on:
            ri = FR.rule_classify(lab.text, rule_ctx)
            if ri == "skip":
                continue
            if isinstance(ri, dict):
                info = ri
                rule_infos[(ri["designation"], _r(lab.cx), _r(lab.cy))] = ri
                if ri.get("count_role"):
                    if ri["category"] in wanted:
                        k = (ri["designation"], int(round(lab.cx / 4)), int(round(lab.cy / 4)))
                        if k not in seen:
                            seen.add(k)
                            rule_counts.append((lab, ri))
                    continue
        if info is None:
            info = classify(lab, hints)
        if not info:
            continue
        k = (info["designation"], int(round(lab.cx / 4)), int(round(lab.cy / 4)))
        if k in seen:
            continue  # bold double-draw of the same label
        seen.add(k)
        labels_by_cat.setdefault(info["category"], []).append((lab, info))

    p = model.page_no
    unit_note = None if model.units_per_foot else "No sheet scale found — calibrate this page so lengths read correctly."

    # Column symbols first: a size printed at a column names the column and
    # must not also become a beam (OE-DELIVERY 2026-11-02-auto-takeoff-columns).
    if rule_on and model.kind == "foundation":
        col_found = _leader_columns(model, labels_by_cat)
        # Base plate tags print under the column size: count them at the column.
        for lab_bp, _ri in rule_counts:
            near = min(col_found, key=lambda c: math.hypot(c["label_obj"].cx - lab_bp.cx, c["label_obj"].cy - lab_bp.cy), default=None)
            if near is not None and math.hypot(near["label_obj"].cx - lab_bp.cx, near["label_obj"].cy - lab_bp.cy) <= 4.5 * lab_bp.size:
                _ri["_at"] = near["point"]
    else:
        col_found = _columns(model, labels_by_cat, column_name, col_marks) if ("columns" in wanted or "beams" in wanted) else []
    # Detailed (zoomed) scan, tile by tile: columns drawn any way (rotated,
    # loose lines, odd sizes) and false ones (deck-span arrows) removed
    # (OE-DELIVERY 2026-11-06-zoom-scan).
    zoom_stats: dict[str, Any] | None = None
    zparts: list[dict[str, Any]] = []
    col_unresolved: list[Label] = []
    if detail_scan and model.detail is not None:
        from app.modules.takeoff import detail_scan as Z

        try:
            # The sheet split into parts zoomed into one by one (4, 6, 9 ...).
            zparts = Z.plan_parts(model, zoom_parts)
        except Exception:
            zparts = []
    if detail_scan and model.detail is not None and ("columns" in wanted or "beams" in wanted):
        from app.modules.takeoff import detail_scan as Z

        try:
            added, removed, zoom_stats = Z.scan_columns(
                model,
                model.detail,
                col_found,
                [],
                lambda x, y: _column_named(x, y, labels_by_cat, column_name, col_marks, mark_reach=30.0),
                seeded_only=bool(rule_on and model.kind == "foundation"),
                col_mark_re=_COL_MARK_RE,
                parts=zparts or None,
            )
            col_found = [c for i, c in enumerate(col_found) if i not in removed] + added
            # Every column size label must have its column: follow its
            # leader (or the line it is written on) to the symbol.
            if "columns" in wanted and not (rule_on and model.kind == "foundation"):
                # (On a foundation plan read by the house rules every column
                # already comes from its label's leader.)
                lab_cols, checked = Z.label_columns(
                    model,
                    model.detail,
                    [tuple(c["point"]) for c in col_found],
                    leader_ends=_detail_leader_ends(model),
                )
                for lc in lab_cols:
                    lab = lc["label"]
                    info = classify(lab) or {}
                    des = info.get("designation") or re.sub(r"\s+", "", lab.text.upper())
                    col_found.append({
                        "mark_obj": None,
                        "label_obj": lab,
                        "point": lc["point"],
                        "designation": des,
                        "label": des,
                        "mark": None,
                        "label_rect": list(lab.rect),
                        "size": lc["size"],
                        "zoom": True,
                    })
                zoom_stats["labels_checked"] = checked
                zoom_stats["added"] = zoom_stats.get("added", 0) + len(lab_cols)
                col_unresolved = list(getattr(Z.label_columns, "unresolved", []))
                # A label pointing at a column already found names it (and is
                # then not read again as a beam).
                for lab, k in getattr(Z.label_columns, "claims", []):
                    c = col_found[k]
                    if c.get("label_obj") is not None and c.get("designation") not in (None, "", "COLUMN"):
                        continue
                    info = classify(lab) or {}
                    des = info.get("designation") or re.sub(r"\s+", "", lab.text.upper())
                    c.update({"label_obj": lab, "designation": des, "label": des, "label_rect": list(lab.rect)})
        except Exception:
            zoom_stats = {"error": True}
    used_by_columns = {id(c["label_obj"]) for c in col_found if c.get("label_obj") is not None}

    # Members (beams, other, single joists/trusses, column labels on lines).
    member_entries: list[dict[str, Any]] = []
    tag_marks: list[tuple[Label, dict[str, Any]]] = []
    # Header / jamb tags: a lone tag with no schedule row is more likely a
    # detail or hold-down mark than a header.
    hj_count: dict[str, int] = {}
    for _lab, _info in labels_by_cat.get("other", []):
        if _info.get("tag") and _info.get("role") in ("Header", "Jamb"):
            hj_count[_info["designation"]] = hj_count.get(_info["designation"], 0) + 1
    for cat in ("beams", "other", "joists", "trusses"):
        if cat not in wanted:
            continue
        for lab, info in labels_by_cat.get(cat, []):
            if info.get("series") or id(lab) in used_by_columns:
                continue
            if (
                info.get("tag")
                and info.get("role") in ("Header", "Jamb")
                and not (specs or {}).get(info["designation"])
                and hj_count.get(info["designation"], 0) < 2
            ):
                continue
            # Scheduled beam tags (B-1 ...) name the heavy beam line drawn
            # under them (OE-DELIVERY 2026-11-05-framing-rules).
            seed = (_heavy_line_at(lab, model) if (rule_on and "rule_profile" in info) else None) or _member_seed(lab, model, strict=bool(info.get("tag")))
            if seed is None:
                if info.get("tag") and info.get("role") in ("Header", "Jamb") and cat in wanted:
                    tag_marks.append((lab, info))
                continue
            heavy = rule_on and "rule_profile" in info
            run = merge_run(seed, model, max_gap=4.0, width_tol=0.1) if heavy else merge_run(seed, model)
            if math.hypot(run[2] - run[0], run[3] - run[1]) < (24 if heavy else 40):
                continue
            member_entries.append({"label": lab, "info": info, "cat": cat, "run": run, "_heavy": heavy})
    _split_shared(member_entries, model)
    for e in member_entries:
        run = e["run"]
        if not run:
            continue
        lab, info = e["label"], e["info"]
        if not e.get("_heavy") and e["cat"] != "trusses" and not any(o is not e and o.get("run") and _run_key(o["run"]) == _run_key(run) for o in member_entries):
            run = _trim_to_supports(run, lab, model)
        items.append({
            "key": _key(p, e["cat"], info["designation"], lab.cx, lab.cy),
            "category": e["cat"],
            "kind": "line",
            "designation": info["designation"],
            "label": info["designation"],
            "spec": info.get("spec") or lab.text if lab.text != info["designation"] else info.get("spec"),
            "points": [[_r(run[0]), _r(run[1])], [_r(run[2]), _r(run[3])]],
            "anchor": [_r(lab.cx), _r(lab.cy)],
            "label_rect": [_r(v) for v in lab.rect],
            "label_quad": label_quad(lab),
            "page": p,
            "series": None,
            "index": None,
            "generated": False,
            "confidence": 0.85 if info.get("source") != "ai" else 0.7,
            "source": info.get("source") or "rules",
            "role": info.get("role"),
        })
    # Header / jamb tags placed as counts at the tag; a lone tag with no
    # schedule row is skipped (could be a grid or detail mark).
    tag_seen: dict[str, int] = {}
    for lab, info in tag_marks:
        tag_seen[info["designation"]] = tag_seen.get(info["designation"], 0) + 1
    for lab, info in tag_marks:
        tag = info["designation"]
        spec = (specs or {}).get(tag)
        if not spec and tag_seen.get(tag, 0) < 2:
            continue
        items.append({
            "key": _key(p, "other", tag, lab.cx, lab.cy),
            "category": "other",
            "kind": "count",
            "designation": tag,
            "label": tag,
            "spec": spec,
            "points": [[_r(lab.cx), _r(lab.cy)]],
            "anchor": [_r(lab.cx), _r(lab.cy)],
            "label_rect": [_r(v) for v in lab.rect],
            "label_quad": label_quad(lab),
            "page": p,
            "series": None,
            "index": None,
            "generated": False,
            "confidence": 0.7 if spec else 0.5,
            "source": info.get("source") or "rules",
            "role": info.get("role"),
        })

    # Joist / truss series and their bays.
    for cat in ("joists", "trusses"):
        if cat not in wanted and "areas" not in wanted:
            continue
        for lab, info in labels_by_cat.get(cat, []):
            if not info.get("series"):
                continue
            via_leader = _series_from_leader(lab, info, model) if (rule_on and "rule_profile" in info) else None
            lines, generated, bay = via_leader if via_leader else _series_lines(lab, info, model)
            if len(lines) < 2 and rule_on and "rule_profile" in info:
                # Last try: members drawn across the line the leader ends on.
                tl = _series_from_tip_line(lab, info, model)
                if tl is not None:
                    lines, generated, bay = tl
            series_key = _key(p, cat, info["designation"], lab.cx, lab.cy)
            spacing = info.get("spacing_in")
            spec = f"{info['designation']} @ {_fmt_in(spacing)} O.C." if spacing else info["designation"]
            if cat in wanted:
                for idx, ln in enumerate(lines):
                    items.append({
                        "key": f"{series_key}|{idx}",
                        "category": cat,
                        "kind": "line",
                        "designation": info["designation"],
                        "label": info["designation"],
                        "spec": spec,
                        "points": [[_r(ln[0]), _r(ln[1])], [_r(ln[2]), _r(ln[3])]],
                        "anchor": [_r(lab.cx), _r(lab.cy)],
                        "label_rect": [_r(v) for v in lab.rect],
                        "label_quad": label_quad(lab),
                        "page": p,
                        "series": series_key,
                        "index": idx,
                        "generated": generated,
                        "confidence": 0.6 if generated else 0.8,
                        "source": info.get("source") or "rules",
                        "role": info.get("role"),
                    })
            if bay and "areas" in wanted:
                items.append({
                    "key": f"{series_key}|bay",
                    "category": "areas",
                    "kind": "area",
                    "designation": f"{info['designation']} BAY",
                    "label": spec,
                    "spec": spec,
                    "points": [[_r(x), _r(y)] for x, y in bay],
                    "anchor": [_r(lab.cx), _r(lab.cy)],
                    "label_rect": [_r(v) for v in lab.rect],
                    "label_quad": label_quad(lab),
                    "page": p,
                    "series": series_key,
                    "index": None,
                    "generated": generated,
                    "confidence": 0.7,
                    "source": info.get("source") or "rules",
                })

    # Metal deck areas (OE-DELIVERY 2026-11-03-auto-takeoff-members).
    if "areas" in wanted:
        for lab, info in labels_by_cat.get("areas", []):
            if info.get("role") != "Deck":
                continue
            poly = _deck_region(lab, model)
            if not poly:
                continue
            items.append({
                "key": _key(p, "areas", info["designation"], lab.cx, lab.cy),
                "category": "areas",
                "kind": "area",
                "designation": info["designation"],
                "label": info["designation"],
                "spec": lab.text,
                "points": [[_r(x), _r(y)] for x, y in poly],
                "anchor": [_r(lab.cx), _r(lab.cy)],
                "label_rect": [_r(v) for v in lab.rect],
                "label_quad": label_quad(lab),
                "page": p,
                "series": None,
                "index": None,
                "generated": False,
                "confidence": 0.6,
                "source": info.get("source") or "rules",
                "role": "Deck",
                "profile": info.get("deck_type"),
            })

    # Walls by tag.
    if "walls" in wanted:
        wall_entries: list[dict[str, Any]] = []
        for lab, info in labels_by_cat.get("walls", []):
            if rule_on and info.get("role") in ("Shear Wall", "Strap Braced Wall"):
                run = shear_panel(lab, model) or _wall_beside(lab, model)
            elif rule_on:
                run = wall_between_walls(lab, model) or _wall_beside(lab, model)
            else:
                run = _wall_run(lab, model)
            if run is None or math.hypot(run[2] - run[0], run[3] - run[1]) < (12 if rule_on else 24):
                continue
            wall_entries.append({"label": lab, "info": info, "cat": "walls", "run": run})
            if rule_on and info.get("wall_type"):
                # 'BR-1 W1': the panel is also W1 stud framing - count it as
                # its own wall-type markup on the same line.
                twin = FR.rule_classify(info["wall_type"], rule_ctx)
                if isinstance(twin, dict):
                    rule_infos[(twin["designation"], _r(lab.cx), _r(lab.cy))] = twin
                    # The wall type runs wall to wall; the panel may be shorter.
                    twin_run = wall_between_walls(lab, model, on_line=run) or run
                    wall_entries.append({"label": lab, "info": twin, "cat": "walls", "run": twin_run, "_twin": True})
        if rule_on:
            # Shear / strap-braced panels: the hatched stretch at the tag.
            # Wall types (W1..) split their wall among themselves only, so a
            # 'BR-1' stacked over 'W1' does not cut the W1 wall in two.
            panels = [e for e in wall_entries if e["info"].get("role") in ("Shear Wall", "Strap Braced Wall") or e.get("_twin")]
            # Wall-type tags already end at the intersecting walls: only two
            # different tags on the very same stretch share it.
            plain = [e for e in wall_entries if e not in panels]
            for e in panels:
                # Two tags on one panel (both sides of a corridor wall pair
                # each have their own panel, so this is a true repeat).
                e["_share"] = False
            _split_shared(plain + [e for e in panels if e.get("_share")], model, strict=True)
            # Wall types: each foot of wall once - tags at a junction measure
            # overlapping stretches; later (longer) ones keep what is left.
            _clip_same_type_overlaps([e for e in wall_entries if e["info"].get("role") == "Load Bearing Wall"])
        else:
            _split_shared(wall_entries, model)
        tag_counts: dict[str, int] = {}
        for e in wall_entries:
            tag_counts[e["info"]["designation"]] = tag_counts.get(e["info"]["designation"], 0) + 1
        for e in wall_entries:
            run = e["run"]
            if not run:
                continue
            lab, info = e["label"], e["info"]
            tag = info["designation"]
            spec = (specs or {}).get(tag) or info.get("spec")
            # A lone short "W1" with no schedule row is more likely a
            # grid or detail mark than a wall tag.
            if not spec and tag_counts.get(tag, 0) < 2 and info.get("source") != "ai":
                continue
            items.append({
                "key": _key(p, "walls", tag, lab.cx, lab.cy),
                "category": "walls",
                "kind": "line",
                "designation": tag,
                "label": tag,
                "spec": spec,
                "points": [[_r(run[0]), _r(run[1])], [_r(run[2]), _r(run[3])]],
                "anchor": [_r(lab.cx), _r(lab.cy)],
                "label_rect": [_r(v) for v in lab.rect],
                "label_quad": label_quad(lab),
                "page": p,
                "series": None,
                "index": None,
                "generated": False,
                "confidence": 0.75 if spec else 0.55,
                "source": info.get("source") or "rules",
            })

    # Columns: one count markup per column, so a single wrong one can be
    # selected and deleted on its own (OE-DELIVERY 2026-11-02-auto-takeoff-list).
    if "columns" in wanted:
        for c in col_found:
            x, y = c["point"]
            items.append({
                "key": _key(p, "columns", c["designation"], x, y),
                "category": "columns",
                "kind": "count",
                "designation": c["designation"],
                "label": c["label"],
                "spec": (f"Mark {c['mark']}" if c["mark"] else None),
                "mark": c["mark"],
                "mark_quad": label_quad(c["mark_obj"]) if c.get("mark_obj") is not None else None,
                "label_rect": [_r(v) for v in c["label_rect"]] if c["label_rect"] else None,
                "label_quad": label_quad(c["label_obj"]) if c.get("label_obj") is not None else None,
                "points": [[_r(x), _r(y)]],
                "anchor": [_r(x), _r(y)],
                "page": p,
                "series": None,
                "index": None,
                "generated": False,
                "confidence": 0.6 if c.get("zoom") else 0.7,
                "source": "zoom" if c.get("zoom") else "rules",
                # Symbol size and turn on the sheet (OE-DELIVERY 2026-11-07-column-shapes).
                "symbol": _column_symbol(model, x, y),
            })

    # Rule counts: headers, holdowns, steel braces, base plates, one per tag.
    for lab, info in rule_counts:
        tag = info["designation"]
        at = info.pop("_at", None) or (lab.cx, lab.cy)
        # Headers stay counts: structural plans rarely draw the opening as a
        # gap, so its width cannot be read reliably (opening_at is kept for
        # plans that do).
        span = None
        items.append({
            "key": _key(p, info["category"], tag, lab.cx, lab.cy),
            "category": info["category"],
            "kind": "line" if span else "count",
            "designation": tag,
            "label": tag,
            "spec": info.get("spec"),
            "points": [[_r(span[0]), _r(span[1])], [_r(span[2]), _r(span[3])]] if span else [[_r(at[0]), _r(at[1])]],
            "anchor": [_r(lab.cx), _r(lab.cy)],
            "label_rect": [_r(v) for v in lab.rect],
            "label_quad": label_quad(lab),
            "page": p,
            "series": None,
            "index": None,
            "generated": False,
            "confidence": 0.75 if info.get("spec") else 0.6,
            "source": "rules",
            "role": info.get("role"),
            "rule_profile": info.get("rule_profile"),
            "rule_level": info.get("rule_level"),
        })

    # Detailed scan for beams: labelled beams with no line yet (curved ones
    # included) and heavy beam lines between columns that carry no size
    # (OE-DELIVERY 2026-11-06-zoom-scan).
    if detail_scan and model.detail is not None and "beams" in wanted:
        from app.modules.takeoff import detail_scan as Z

        try:
            sizes = {(round(c["point"][0], 1), round(c["point"][1], 1)): (c.get("size") or 12.0) for c in col_found}
            col_pts = [(float(x), float(y), float(sz)) for (x, y), sz in sizes.items()]
            beam_labs = [(lab, info) for lab, info in labels_by_cat.get("beams", []) if id(lab) not in used_by_columns and not info.get("series")]
            new_beams, beam_stats = Z.scan_beams(model, model.detail, beam_labs, items, col_pts, unlabeled=not rule_on, parts=zparts or None)
            for e in new_beams:
                lab, info = e["label"], e["info"] or {}
                pts = e["points"]
                anchor = (lab.cx, lab.cy) if lab is not None else pts[len(pts) // 2]
                items.append({
                    "key": _key(p, "beams", e["designation"], anchor[0], anchor[1], "zoom"),
                    "category": "beams",
                    "kind": "line",
                    "designation": e["designation"],
                    "label": e["designation"] if not e["unlabeled"] else "BEAM (no size on plan)",
                    "spec": info.get("spec"),
                    "points": [[_r(x), _r(y)] for x, y in pts],
                    "anchor": [_r(anchor[0]), _r(anchor[1])],
                    "label_rect": [_r(v) for v in lab.rect] if lab is not None else None,
                    "label_quad": label_quad(lab) if lab is not None else None,
                    "page": p,
                    "series": None,
                    "index": None,
                    "generated": False,
                    "confidence": 0.7 if not e["unlabeled"] else 0.45,
                    "source": "zoom",
                    "role": info.get("role"),
                })
            # First-pass "beams" that are really a column callout's leader.
            drop = Z.leader_beams(model, model.detail, items, [tuple(c["point"]) for c in col_found])
            if drop:
                items[:] = [it for k, it in enumerate(items) if k not in drop]
            beam_stats["leaders_removed"] = len(drop)
            if zoom_stats is None:
                zoom_stats = {}
            zoom_stats["beams"] = beam_stats
        except Exception:
            if zoom_stats is None:
                zoom_stats = {}
            zoom_stats["beams"] = {"error": True}
    # Joist / truss callouts that framed nothing: read zoomed in, line by
    # line at the callout's spacing (OE-DELIVERY 2026-11-06-zoom-scan).
    if detail_scan and model.detail is not None and ("joists" in wanted or "trusses" in wanted):
        from app.modules.takeoff import detail_scan as Z

        try:
            series_labs = [
                (lab, info)
                for cat in ("joists", "trusses")
                if cat in wanted
                for lab, info in labels_by_cat.get(cat, [])
                if info.get("series")
            ]
            new_series, j_stats = Z.scan_joists(
                model, model.detail, series_labs, items, zparts or None,
                leader_ends=lambda lab: [tip for _score, tip in leader_tips(lab, model)],
            )
            for e in new_series:
                lab, info = e["label"], e["info"]
                cat = info.get("category") or "joists"
                series_key = _key(p, cat, info["designation"], lab.cx, lab.cy, "zoom")
                spacing = info.get("spacing_in")
                spec = f"{info['designation']} @ {_fmt_in(spacing)} O.C." if spacing else info["designation"]
                for idx, ln in enumerate(e["lines"]):
                    items.append({
                        "key": f"{series_key}|{idx}",
                        "category": cat,
                        "kind": "line",
                        "designation": info["designation"],
                        "label": info["designation"],
                        "spec": spec,
                        "points": [[_r(ln[0]), _r(ln[1])], [_r(ln[2]), _r(ln[3])]],
                        "anchor": [_r(lab.cx), _r(lab.cy)],
                        "label_rect": [_r(v) for v in lab.rect],
                        "label_quad": label_quad(lab),
                        "page": p,
                        "series": series_key,
                        "index": idx,
                        "generated": False,
                        "confidence": 0.65,
                        "source": "zoom",
                        "role": info.get("role"),
                    })
            zoom_stats = zoom_stats or {}
            zoom_stats["joists"] = j_stats
        except Exception:
            zoom_stats = zoom_stats or {}
            zoom_stats["joists"] = {"error": True}
    # Deck callouts with no bay: bounded by the beams taken off around them.
    if detail_scan and model.detail is not None and "areas" in wanted:
        from app.modules.takeoff import detail_scan as Z

        try:
            lines = [
                [(float(q[0]), float(q[1])) for q in it["points"]]
                for it in items
                if it.get("kind") == "line" and it.get("category") in ("beams", "walls")
            ]
            d_added = 0
            # Deck tags keyed to a deck legend (AD / BD / CD ...): each tag
            # on the plan marks the bay that gets that deck.
            legend_tags, legend_boxes = Z.deck_legend(model, deck_info)
            deck_labs: list[tuple[Label, dict[str, Any]]] = []
            for lab, info in labels_by_cat.get("areas", []):
                if info.get("role") == "Deck" and not _in_rects(lab.cx, lab.cy, legend_boxes, 2):
                    deck_labs.append((lab, info))
            if legend_tags:
                for lab in model.labels:
                    t = "".join(lab.text.split()).upper()
                    if t in legend_tags and not _in_rects(lab.cx, lab.cy, legend_boxes, 2) and not _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
                        info = dict(legend_tags[t])
                        info["designation"] = f"{t} - {info['designation']}"
                        deck_labs.append((lab, info))
            zoom_stats = zoom_stats or {}
            zoom_stats["deck_legend"] = sorted(legend_tags)
            model.schedule_rects = list(model.schedule_rects) + [b for b in legend_boxes if b not in model.schedule_rects]
            for lab, info in deck_labs:
                if any(
                    it.get("kind") == "area" and it.get("role") == "Deck"
                    and min(q[0] for q in it["points"]) <= lab.cx <= max(q[0] for q in it["points"])
                    and min(q[1] for q in it["points"]) <= lab.cy <= max(q[1] for q in it["points"])
                    for it in items
                ):
                    continue
                poly = Z.deck_bay(lab, lines) or _deck_region(lab, model)
                if not poly:
                    continue
                d_added += 1
                items.append({
                    "key": _key(p, "areas", info["designation"], lab.cx, lab.cy, "zoom"),
                    "category": "areas",
                    "kind": "area",
                    "designation": info["designation"],
                    "label": info["designation"],
                    "spec": info.get("legend_text") or lab.text,
                    "points": [[_r(x), _r(y)] for x, y in poly],
                    "anchor": [_r(lab.cx), _r(lab.cy)],
                    "label_rect": [_r(v) for v in lab.rect],
                    "label_quad": label_quad(lab),
                    "page": p,
                    "series": None,
                    "index": None,
                    "generated": False,
                    "confidence": 0.55,
                    "source": "zoom",
                    "role": "Deck",
                    "profile": info.get("deck_type"),
                })
            zoom_stats = zoom_stats or {}
            zoom_stats["deck"] = {"added": d_added}
        except Exception:
            zoom_stats = zoom_stats or {}
            zoom_stats["deck"] = {"error": True}
    if rule_on:
        _nearest_tag_owns_shared(items)
    items = _dedupe_items(items)
    snap_member_ends(items)
    assign_roles(items, model, specs)
    if rule_on:
        for it in items:
            a = it.get("anchor") or [0, 0]
            ri = rule_infos.get((it.get("designation") or "", _r(a[0]), _r(a[1])))
            if ri:
                for k in ("rule_profile", "rule_height", "rule_level", "rule_spacing"):
                    if ri.get(k) and not it.get(k):
                        it[k] = ri[k]
                if ri.get("role"):
                    it["role"] = ri["role"]
                if ri.get("spec") and it.get("series") is None:
                    it["spec"] = ri["spec"]
                elif ri.get("spec") and it.get("series"):
                    it["spec"] = ri["spec"]
            if not it.get("rule_level") and model.level is not None and model.kind in ("framing", "walls"):
                it["level"] = FR.ORD_NAME.get(model.level, str(model.level)) + " FLOOR"
            elif model.kind == "roof" and not it.get("rule_level"):
                it["level"] = "ROOF"
        items = FR.post_process(items, model.kind or "", model.level, model.fsched)
    # Stud walls: full width, header areas apart, studs at their spacing
    # (OE-DELIVERY 2026-11-08-stud-walls).
    if "walls" in wanted:
        try:
            items = stud_walls(items, model)
        except Exception:
            pass
    counts: dict[str, int] = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + (len(it["points"]) if it["kind"] == "count" else 1)
    if rule_on:
        missed = missed_tags(model, items, rule_infos, wanted)
    elif detail_scan:
        missed = generic_missed(model, items, labels_by_cat, wanted, used_by_columns)
    else:
        missed = []
    if detail_scan and "columns" in wanted:
        for lab in col_unresolved:
            missed.append({
                "designation": re.sub(r"\s+", "", lab.text.upper()),
                "category": "columns",
                "role": "Column",
                "at": [_r(lab.cx), _r(lab.cy)],
                "page": model.page_no,
                "reason": "Column size with no column symbol where it points (drawn as part of a wall?) - check it on the sheet.",
            })
    if detail_scan and zparts:
        from app.modules.takeoff import detail_scan as Z

        zoom_stats = zoom_stats or {}
        zoom_stats["parts"] = len(zparts)
        zoom_stats["grid"] = zparts[0]["grid"]
        try:
            zoom_stats["log"] = Z.part_log(model, zparts, items, missed)
        except Exception:
            zoom_stats["log"] = []
    return {
        "page": p,
        "scale": model.scale_text,
        "units_per_foot": model.units_per_foot,
        "paper_in_per_ft": round(model.units_per_foot / 72.0, 5) if model.units_per_foot else None,
        "detail_sheet": is_detail_sheet(model),
        "counts": counts,
        "items": items,
        "note": unit_note,
        "sheet_kind": model.kind if rule_on else None,
        "level": model.level if rule_on else None,
        "missed": missed,
        "zoom_scan": zoom_stats,
    }


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One markup per member: two callouts covering the same bay (or a
    label double-drawn far enough apart to survive the label de-dupe)
    must not place the same line or bay twice."""
    out: list[dict[str, Any]] = []
    lines: list[tuple[str, tuple[float, float, float, float], Any]] = []
    areas: list[tuple[float, float, float, float]] = []
    for it in items:
        pts = it["points"]
        if it["kind"] == "line":
            a = (pts[0][0], pts[0][1], pts[1][0], pts[1][1])
            dup = False
            for cat, b, des in lines:
                if cat != it["category"] or (cat == "walls" and des != it.get("designation")):
                    continue
                same = math.hypot(a[0] - b[0], a[1] - b[1]) <= 4 and math.hypot(a[2] - b[2], a[3] - b[3]) <= 4
                flip = math.hypot(a[0] - b[2], a[1] - b[3]) <= 4 and math.hypot(a[2] - b[0], a[3] - b[1]) <= 4
                if same or flip:
                    dup = True
                    break
            if dup:
                continue
            lines.append((it["category"], a, it.get("designation")))
        elif it["kind"] == "area":
            xs = [q[0] for q in pts]
            ys = [q[1] for q in pts]
            box = (min(xs), min(ys), max(xs), max(ys))
            dup = False
            for b in areas:
                ix = max(0.0, min(box[2], b[2]) - max(box[0], b[0]))
                iy = max(0.0, min(box[3], b[3]) - max(box[1], b[1]))
                inter = ix * iy
                small = min((box[2] - box[0]) * (box[3] - box[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1.0
                if inter / small > 0.6:
                    dup = True
                    break
            if dup:
                continue
            areas.append(box)
        out.append(it)
    return out


def _fmt_in(inches: float | None) -> str:
    if not inches:
        return ""
    if inches >= 12 and abs(inches % 12) < 1e-6 or inches > 24:
        ft = int(inches // 12)
        rem = inches - ft * 12
        return f"{ft}'-{rem:g}\""
    return f"{inches:g}\""


def unknown_label_inventory(model: PageModel, limit: int = 120) -> list[dict[str, Any]]:
    """Short labels the rules could not classify (for the AI pass)."""
    counts: dict[str, int] = {}
    for lab in model.labels:
        compact = re.sub(r"\s+", "", lab.text.upper())
        if not (1 <= len(compact) <= 16) or not re.search(r"[A-Z]", compact) or not re.search(r"\d", compact):
            continue
        # Loads, areas, dates, phone numbers, sheet refs are never members.
        if re.search(r"[:/+,()#$%]|PSF|PSI|KSF|MPH|LBS|SF$|SQ|DATE|^\d+$", compact) or re.match(r"^[A-Z]\d?\.\d", compact):
            continue
        if _DIM_RE.match(lab.text) or _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
            continue
        known = classify(lab)
        if known is not None and not known.get("tag"):
            continue
        counts[compact] = counts.get(compact, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
    return [{"text": k, "count": v} for k, v in ranked]


def schedule_text(model: PageModel, limit_chars: int = 3500) -> str:
    """Schedule / legend text of a page, for the AI pass."""
    parts: list[str] = []
    for line in model.lines:
        rect = D._line_rect(line)
        if rect is None:
            continue
        upper = line.text.upper()
        if _in_rects((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0, model.schedule_rects, 4) or any(
            w in upper for w in ("SCHEDULE", "LEGEND", "WALL TYPE", "MARK", "TRUSS", "JOIST", "O.C.")
        ):
            parts.append(line.text)
    text = "\n".join(parts)
    return text[:limit_chars]


def build_models(
    pdf, pages: list[int], *, want_specs: bool = True, rules: bool = False
) -> tuple[list[PageModel], list[PageModel]]:
    """Page models for ``pages`` plus light models of schedule sheets."""
    models: list[PageModel] = []
    for page_no in pages:
        if 1 <= page_no <= len(pdf):
            models.append(build_page_model(pdf[page_no - 1], page_no))
    if rules:
        apply_framing_rules(pdf, models)
    spec_models = list(models)
    if want_specs:
        # Wall schedules usually sit on the wall plan itself but may be on
        # another sheet: also read other pages that carry a schedule.
        for page_no in range(1, min(len(pdf), 120) + 1):
            if page_no in pages:
                continue
            try:
                text = pdf[page_no - 1].get_text().upper()
            except Exception:
                continue
            if len(_SQUARE_HSS_RE.findall(text)) >= 3 and sum(1 for m in spec_models if m.column_source) < 4:
                full = build_page_model(pdf[page_no - 1], page_no)
                full.column_source = True
                spec_models.append(full)
            elif "SCHEDULE" in text or "WALL TYPE" in text or "LEGEND" in text or "COLUMN" in text:
                spec_models.append(PageModel(page_no, 0, 0, [], [], [], D._page_lines(pdf[page_no - 1]), None, None))
            if len(spec_models) > 60:
                break
    return models, spec_models


def apply_framing_rules(pdf, models: list[PageModel]) -> dict[str, Any]:
    """Sheet kind, level and schedules on each model (framing rules)."""
    from app.modules.takeoff import framing_rules as FR

    doc = FR.document_schedules(pdf, getattr(pdf, "name", None))
    for m in models:
        page = pdf[m.page_no - 1]
        try:
            m.kind, m.level, _titles = FR.page_kind(page)
        except Exception:
            m.kind, m.level = None, None
        m.fsched = doc["schedules"]
        if m.kind:
            try:
                m.fine = page_segments(page, min_len=3.0)
                m.fine_index = SegIndex(m.fine)
            except Exception:
                m.fine, m.fine_index = [], None
            # Legend boxes show sample tags (T-1, HD ...): never take them off.
            try:
                m.schedule_rects.extend(legend_rects(page, m))
            except Exception:
                pass
            try:
                m.schedule_rects.extend(FR.page_schedule_rects(page, doc["rects"], m.page_no - 1))
            except Exception:
                pass
    return doc


def legend_rects(page, model: PageModel) -> list[tuple[float, float, float, float]]:
    """Boxes titled LEGEND (or KEY / SYMBOLS): the smallest drawn rectangle
    around each title, or the area below it when none is drawn."""
    out: list[tuple[float, float, float, float]] = []
    try:
        hits = [r for w in ("LEGEND", "SYMBOL LEGEND") for r in page.search_for(w)]
    except Exception:
        return out
    for h in hits:
        cx, cy = (h.x0 + h.x1) / 2.0, (h.y0 + h.y1) / 2.0
        best = None
        for b in model.boxes:
            if b[0] - 1 <= cx <= b[2] + 1 and b[1] - 1 <= cy <= b[3] + 1:
                area = (b[2] - b[0]) * (b[3] - b[1])
                if area > 60 * 60 and (best is None or area < best[0]):
                    best = (area, b)
        if best is None:
            # Box from four lines: nearest long lines around the title.
            xs0 = [sg for sg in model.segments if abs(sg[1] - sg[3]) < 0.5 and sg[4] > 120 and min(sg[0], sg[2]) - 2 <= cx <= max(sg[0], sg[2]) + 2]
            above = [sg[1] for sg in xs0 if sg[1] <= cy + 2]
            below = [sg[1] for sg in xs0 if sg[1] > cy + 2]
            if above and below:
                top, bot = max(above), max(below)
                spans = [sg for sg in xs0 if abs(sg[1] - top) < 1]
                if spans:
                    sg = max(spans, key=lambda q: q[4])
                    out.append((min(sg[0], sg[2]), top, max(sg[0], sg[2]), bot))
            continue
        out.append(tuple(best[1][:4]))
    return out


def _series_from_tip_line(
    label: Label, info: dict[str, Any], model: PageModel
) -> tuple[list[tuple[float, float, float, float]], bool, list[tuple[float, float]] | None] | None:
    """Members drawn one by one across the line a tag's leader ends on (a
    corridor or end bay): the drawn lines crossing that line, between the
    walls, at about the schedule spacing. Wall faces (double lines) are not
    members."""
    assert model.index is not None
    tip = leader_tip(label, model)
    if tip is None:
        return None
    best = None
    for i in model.index.near(tip[0] - 2, tip[1] - 2, tip[0] + 2, tip[1] + 2):
        sg = model.segments[i]
        if sg[4] >= 30 and _pt_seg_dist(tip[0], tip[1], sg) <= 1.5 and (best is None or sg[4] > best[4]):
            best = sg
    if best is None:
        return None
    dist = merge_run(best, model, max_gap=2.0)
    upf = model.units_per_foot or 9.0
    spacing_units = (info.get("spacing_in") or 24.0) / 12.0 * upf
    members = [mm for mm in _crossing_members(dist, model, spacing_units) if not _has_partner((*mm, math.hypot(mm[2] - mm[0], mm[3] - mm[1]), 0.0, None), model, 2.0, 6.0)]
    if len(members) < 2:
        return None
    # Keep the regular run around the tip (walls end it).
    d_len = math.hypot(dist[2] - dist[0], dist[3] - dist[1]) or 1.0
    ux, uy = (dist[2] - dist[0]) / d_len, (dist[3] - dist[1]) / d_len
    pos = sorted(((((mm[0] + mm[2]) / 2.0 - dist[0]) * ux + ((mm[1] + mm[3]) / 2.0 - dist[1]) * uy), mm) for mm in members)
    t_tip = (tip[0] - dist[0]) * ux + (tip[1] - dist[1]) * uy
    i0 = min(range(len(pos)), key=lambda k: abs(pos[k][0] - t_tip))
    lo = hi = i0
    lim = 1.6 * spacing_units
    while lo > 0 and pos[lo][0] - pos[lo - 1][0] <= lim:
        lo -= 1
    while hi < len(pos) - 1 and pos[hi + 1][0] - pos[hi][0] <= lim:
        hi += 1
    picked = [p[1] for p in pos[lo:hi + 1]]
    if len(picked) < 2:
        return None
    return picked, False, None


def _nearest_tag_owns_shared(items: list[dict[str, Any]]) -> None:
    """Joist / truss lines claimed by tags of different types (an end bay
    tagged RJ-1 next to a corridor tagged J-1 framed at the same spacing):
    each line goes to the nearest tag; the others' copies are dropped."""
    groups: dict[tuple[int, int, int, int, str], list[int]] = {}
    for i, it in enumerate(items):
        if it.get("kind") != "line" or it.get("category") not in ("joists", "trusses") or not it.get("series"):
            continue
        (x0, y0), (x1, y1) = it["points"][0], it["points"][1]
        a, b = sorted(((round(x0 / 3), round(y0 / 3)), (round(x1 / 3), round(y1 / 3))))
        groups.setdefault((a[0], a[1], b[0], b[1], it["category"]), []).append(i)
    drop: set[int] = set()
    for idx in groups.values():
        if len({items[i]["designation"] for i in idx}) < 2:
            continue

        def d(i: int) -> float:
            it = items[i]
            (x0, y0), (x1, y1) = it["points"][0], it["points"][1]
            return _pt_seg_dist(it["anchor"][0], it["anchor"][1], (x0, y0, x1, y1, 1.0))

        keep = min(idx, key=d)
        drop.update(i for i in idx if i != keep)
    if drop:
        items[:] = [it for i, it in enumerate(items) if i not in drop]


DEFAULT_STUD_SPACING_IN = 24.0
# Stud spacings a framing plan uses; anything else written "@ x O.C." in a
# wall's notes is screw / nail spacing (#8 @ 4" O.C.), not studs.
_STUD_SPACINGS = (12.0, 16.0, 19.2, 24.0)
_OC_RE = re.compile(r"@\s*(\d+(?:\.\d+)?)\s*(\"|''|IN\b|INCH)?\s*O\.?\s*C", re.IGNORECASE)


def stud_spacing_in(text: str) -> float | None:
    """Stud spacing written on the plan / schedule ("600S200-68 @ 24\" O.C."),
    in inches; a screw spacing in the same note is skipped."""
    for m in _OC_RE.finditer(text or ""):
        v = float(m.group(1))
        if m.group(2) is None and v <= 4:
            v *= 12.0  # "@ 2 O.C." with no unit: feet
        for sp in _STUD_SPACINGS:
            if abs(v - sp) < 0.05:
                return sp
    return None


def stud_walls(items: list[dict[str, Any]], model: PageModel) -> list[dict[str, Any]]:
    """Each wall markup read at full width, the way an estimator takes off
    a stud wall:

    * width - the distance between the wall's two drawn faces (else the stud
      depth from its profile, 600S... = 6"); the markup moves onto the true
      centre line between the faces;
    * header areas - where the faces stop at an opening the run is cut, and
      the opening becomes its own piece (no studs; header size from the
      nearest header tag), never merged with the plain wall. Runs of the same
      wall tag in one line are read together, so an opening where two runs
      meet is found too;
    * studs - at the spacing on the plan (schedule / tag "@ 16\" O.C."), else
      24" on centre; one at each end.
    """
    upf = model.units_per_foot or 0.0
    from app.modules.takeoff import detail_scan as Z

    headers = [it for it in items if it.get("kind") == "count" and "Header" in (it.get("role") or "")]
    walls = [
        k for k, it in enumerate(items)
        if it.get("category") == "walls" and it.get("kind") == "line" and len(it.get("points") or []) == 2
    ]
    if not walls or not upf:
        for k in walls:
            it = items[k]
            it.setdefault("stud_spacing_in", stud_spacing_in(" ".join(str(it.get(x) or "") for x in ("spec", "label"))) or DEFAULT_STUD_SPACING_IN)
            it.setdefault("segment", "wall")
        return items

    # Chains: runs of one wall tag lying in one line and touching end to end.
    def axis(it):
        (ax, ay), (bx, by) = it["points"]
        ang = (math.degrees(math.atan2(by - ay, bx - ax)) + 90.0) % 180.0 - 90.0
        return ang, ax, ay, bx, by

    parent = {k: k for k in walls}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ii, a in enumerate(walls):
        ia = items[a]
        aa, ax, ay, bx, by = axis(ia)
        for b in walls[ii + 1:]:
            ib = items[b]
            if ib.get("designation") != ia.get("designation") or ib.get("role") != ia.get("role"):
                continue
            ab, cx, cy, dx, dy = axis(ib)
            if min(abs(aa - ab), 180 - abs(aa - ab)) > 2.0:
                continue
            if min(math.hypot(px - qx, py - qy) for px, py in ((ax, ay), (bx, by)) for qx, qy in ((cx, cy), (dx, dy))) > 2.0:
                continue
            L = math.hypot(bx - ax, by - ay) or 1.0
            nx, ny = -(by - ay) / L, (bx - ax) / L
            if abs((cx - ax) * nx + (cy - ay) * ny) > 1.5 or abs((dx - ax) * nx + (dy - ay) * ny) > 1.5:
                continue
            parent[find(a)] = find(b)
    chains: dict[int, list[int]] = {}
    for k in walls:
        chains.setdefault(find(k), []).append(k)

    replace: dict[int, list[dict[str, Any]]] = {}
    learned_widths: list[float] = []
    learned_pen_widths: set[float] = set()
    for members in chains.values():
        first = items[members[0]]
        (ax, ay), (bx, by) = first["points"]
        L0 = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / L0, (by - ay) / L0
        nx, ny = -uy, ux
        ts = []
        for k in members:
            for px, py in items[k]["points"]:
                ts.append((px - ax) * ux + (py - ay) * uy)
        t_lo, t_hi = min(ts), max(ts)
        A0 = (ax + ux * t_lo, ay + uy * t_lo)
        B0 = (ax + ux * t_hi, ay + uy * t_hi)
        profile = first.get("profile") or first.get("rule_profile") or ""
        depth = Z.stud_depth_in(profile)
        fallback_w = (depth or 6.0) / 12.0 * upf
        if model.detail is not None:
            geo = Z.wall_geometry(model, model.detail, A0, B0, fallback_w)
        else:
            geo = {"width": fallback_w, "offset": 0.0, "openings": [], "length": t_hi - t_lo}
        width = geo["width"] or fallback_w
        off = geo["offset"] if abs(geo["offset"]) <= width else 0.0
        openings = [(g0 + t_lo, g1 + t_lo) for g0, g1 in geo["openings"]]
        if geo.get("width"):
            learned_widths.append(geo["width"])
            learned_pen_widths.update(geo.get("face_widths") or [])

        def pt(t: float) -> tuple[float, float]:
            return (ax + ux * t + nx * off, ay + uy * t + ny * off)

        done_openings: set[int] = set()
        for k in members:
            it = items[k]
            text = " ".join(str(it.get(x) or "") for x in ("spec", "rule_spacing", "label"))
            sp_in = stud_spacing_in(text) or DEFAULT_STUD_SPACING_IN
            sp_units = sp_in / 12.0 * upf
            r0 = min(((px - ax) * ux + (py - ay) * uy) for px, py in it["points"])
            r1 = max(((px - ax) * ux + (py - ay) * uy) for px, py in it["points"])
            # Plain wall of this run: its extent less the openings.
            t = r0
            pieces: list[tuple[float, float, int | None]] = []
            for oi, (g0, g1) in enumerate(sorted(openings)):
                if g1 <= r0 or g0 >= r1:
                    continue
                if g0 > t:
                    pieces.append((t, g0, None))
                if oi not in done_openings:
                    done_openings.add(oi)
                    pieces.append((g0, g1, oi))
                t = max(t, g1)
            if t < r1:
                pieces.append((t, r1, None))
            out_pieces: list[dict[str, Any]] = []
            for pi_, (t0, t1, oi) in enumerate(pieces):
                is_hdr = oi is not None
                if t1 - t0 < (0.5 if is_hdr else 1.0) * upf:
                    continue
                p0, p1 = pt(t0), pt(t1)
                piece = dict(it)
                piece["points"] = [[_r(p0[0]), _r(p0[1])], [_r(p1[0]), _r(p1[1])]]
                piece["key"] = it["key"] if len(pieces) == 1 else f"{it['key']}|w{pi_}"
                # Pieces of one wall share its tag and label: their number keeps
                # them apart when the viewer merges a run (and on re-runs).
                if len(pieces) > 1:
                    piece["index"] = pi_
                piece["wall_width"] = _r(width)
                piece["wall_width_in"] = round(width / upf * 12.0, 2)
                piece["stud_spacing_in"] = sp_in
                piece["stud_spacing"] = _r(sp_units)
                if is_hdr:
                    mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
                    near = min(headers, key=lambda h: math.hypot(h["points"][0][0] - mx, h["points"][0][1] - my), default=None)
                    hdr = near if near is not None and math.hypot(near["points"][0][0] - mx, near["points"][0][1] - my) <= max(4.0 * upf, t1 - t0) else None
                    piece["segment"] = "header"
                    piece["stud_count"] = 0
                    piece["designation"] = f"{it['designation']} HEADER"
                    piece["label"] = piece["designation"]
                    piece["header"] = hdr["designation"] if hdr else None
                    piece["profile"] = (hdr.get("profile") if hdr else None) or profile
                    piece["spec"] = (
                        f"Header area of wall {it['designation']} ({_fmt_in(round((t1 - t0) / upf * 12.0 * 8) / 8)} opening)"
                        + (f": header {hdr['designation']} - {hdr.get('spec') or hdr.get('profile') or ''}" if hdr else "")
                    )
                else:
                    piece["segment"] = "wall"
                    piece["stud_count"] = Z.stud_count(t1 - t0, sp_units)
                out_pieces.append(piece)
            replace[k] = out_pieces
    out: list[dict[str, Any]] = []
    for k, it in enumerate(items):
        if k in replace:
            out.extend(replace[k])
        else:
            out.append(it)
    # Cover the whole drawn wall: stretches of double-line wall in the wall
    # pen, at a wall width, that no tag reached (beside an opening, past a
    # cross wall ...) are taken off too - as the tagged wall they continue,
    # else as an untagged wall to check (OE-DELIVERY 2026-11-09-colours-keys).
    if model.detail is not None and len(learned_widths) >= 3:
        try:
            out.extend(_fill_uncovered_walls(out, model, learned_widths, learned_pen_widths, headers))
        except Exception:
            pass
    # A shear / strap-braced panel drawn on a bearing wall is part of that
    # wall: the wall's studs already cover it, so the panel counts none of
    # its own (its chord studs are in its spec) - the two are shown together,
    # and either can be picked out with the role filter.
    plain = [w for w in out if w.get("category") == "walls" and w.get("kind") == "line" and w.get("segment") == "wall"]
    for w in plain:
        if w.get("role") not in ("Shear Wall", "Strap Braced Wall"):
            continue
        (ax, ay), (bx, by) = w["points"]
        L = math.hypot(bx - ax, by - ay)
        if L <= 0:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        for o in plain:
            if o is w or o.get("role") in ("Shear Wall", "Strap Braced Wall"):
                continue
            (cx, cy), (dx, dy) = o["points"]
            if abs((cx - ax) * -uy + (cy - ay) * ux) > 2.0 or abs((dx - ax) * -uy + (dy - ay) * ux) > 2.0:
                continue
            t1, t2 = (cx - ax) * ux + (cy - ay) * uy, (dx - ax) * ux + (dy - ay) * uy
            ov = min(L, max(t1, t2)) - max(0.0, min(t1, t2))
            if ov >= 0.6 * L:
                w["stud_count"] = 0
                w["stud_spacing"] = None  # the viewer counts / draws none for it
                w["studs_in"] = o.get("designation")
                w["spec"] = f"{w.get('spec') or ''}; field studs counted in wall {o.get('designation')}".lstrip("; ")
                break
    return out


def _fill_uncovered_walls(
    out: list[dict[str, Any]],
    model: PageModel,
    learned_widths: list[float],
    learned_pen_widths: set[float],
    headers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from app.modules.takeoff import detail_scan as Z

    upf = model.units_per_foot or 9.0
    ds = model.detail
    # Wall widths seen (clustered to 1/2"), and the face pens they were drawn with.
    widths: list[float] = []
    for w in sorted(learned_widths):
        if not widths or abs(w - widths[-1]) > 0.5 / 12.0 * upf:
            widths.append(w)
    pens = {
        (sg[6], round(float(sg[5] or 0.0), 2))
        for sg in ds.segs
        if round(float(sg[5] or 0.0), 2) in learned_pen_widths and sg[6] is not None and min(sg[6]) < 12
    }
    walls = [w for w in out if w.get("category") == "walls" and w.get("kind") == "line" and len(w.get("points") or []) == 2]
    covered = [((w["points"][0][0], w["points"][0][1]), (w["points"][1][0], w["points"][1][1]), float(w.get("wall_width") or 0.0)) for w in walls]
    found = Z.uncovered_walls(model, ds, pens, widths, covered)
    added: list[dict[str, Any]] = []
    for n, (a, b, w) in enumerate(found):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L <= 0:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        # The tagged wall it continues: same line, ends within 4 ft.
        src = None
        best = None
        for wl in walls:
            if wl.get("segment") != "wall":
                continue
            (cx, cy), (dx, dy) = wl["points"]
            cl = math.hypot(dx - cx, dy - cy)
            if cl <= 0 or abs(((dx - cx) * uy - (dy - cy) * ux) / cl) > 0.05:
                continue
            if abs((cx - a[0]) * -uy + (cy - a[1]) * ux) > 1.5:
                continue
            gap = min(math.hypot(px - qx, py - qy) for px, py in ((cx, cy), (dx, dy)) for qx, qy in (a, b))
            if gap <= 4.0 * upf and (best is None or gap < best):
                best, src = gap, wl
        sp_in = (src.get("stud_spacing_in") if src else None) or DEFAULT_STUD_SPACING_IN
        sp_units = sp_in / 12.0 * upf
        if src is not None:
            piece = dict(src)
            piece["key"] = f"{src['key']}|x{n}"
            piece["index"] = 1000 + n
            piece["spec"] = f"{src.get('spec') or ''}; continued along the drawn wall".lstrip("; ")
            piece["confidence"] = 0.6
        else:
            win = round(w / upf * 12.0 * 2) / 2
            piece = {
                "key": _key(model.page_no, "walls", "WALL", (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, f"x{n}"),
                "category": "walls",
                "kind": "line",
                "designation": "WALL",
                "label": "WALL",
                "role": "Wall",
                "profile": f'{_fmt_in(win)} wall (no tag on the plan)',
                "spec": f'Drawn {_fmt_in(win)} wall with no wall tag - check its type on the plan',
                "anchor": [_r((a[0] + b[0]) / 2), _r((a[1] + b[1]) / 2)],
                "page": model.page_no,
                "series": None,
                "index": None,
                "generated": False,
                "confidence": 0.4,
                "source": "zoom",
            }
        piece["points"] = [[_r(a[0]), _r(a[1])], [_r(b[0]), _r(b[1])]]
        piece["source"] = "zoom"
        piece["segment"] = "wall"
        piece["wall_width"] = _r(w)
        piece["wall_width_in"] = round(w / upf * 12.0, 2)
        piece["stud_spacing_in"] = sp_in
        piece["stud_spacing"] = _r(sp_units)
        piece["stud_count"] = Z.stud_count(L, sp_units)
        added.append(piece)
    return added


def generic_missed(
    model: PageModel,
    items: list[dict[str, Any]],
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]],
    wanted: set[str],
    used_by_columns: set[int],
) -> list[dict[str, Any]]:
    """Without house rules: member callouts (beam sizes, joist / truss
    series, deck) that no markup of that size answers within 4 ft - listed
    so nothing is skipped silently (OE-DELIVERY 2026-11-06-zoom-scan)."""
    upf = model.units_per_foot or 9.0
    near = 4.0 * upf
    by_des: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_des.setdefault(re.sub(r"[\s\-]", "", it.get("designation") or ""), []).append(it)

    def dist(x: float, y: float, it: dict[str, Any]) -> float:
        pts = it.get("points") or []
        best = 1e9
        if len(pts) == 1:
            best = math.hypot(pts[0][0] - x, pts[0][1] - y)
        elif it.get("kind") == "area" and len(pts) >= 3:
            xs = [q[0] for q in pts]
            ys = [q[1] for q in pts]
            if min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys):
                return 0.0
        if len(pts) >= 2:
            for a, b in zip(pts, pts[1:]):
                best = min(best, _pt_seg_dist(x, y, (a[0], a[1], b[0], b[1], 1.0)))
        lr = it.get("label_rect")
        if lr and len(lr) == 4:
            best = min(best, math.hypot((lr[0] + lr[2]) / 2.0 - x, (lr[1] + lr[3]) / 2.0 - y))
        return best

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for cat in ("beams", "joists", "trusses", "areas"):
        if cat not in wanted:
            continue
        for lab, info in labels_by_cat.get(cat, []):
            if id(lab) in used_by_columns or _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
                continue
            if cat == "areas" and (
                info.get("role") != "Deck"
                or re.search(r"PLAN|SHEET|SCHEDULE|LEGEND|NOTES?\b", lab.text.upper())
                or lab.cx > 0.9 * model.width
            ):
                continue  # a title or note about deck, not a callout
            if cat == "beams" and info.get("series"):
                continue
            if cat == "beams" and re.match(r"^(HSS(\d+(?:\.\d+)?)X\2X|W\d+X)", re.sub(r"\s+", "", lab.text.upper())) and any(
                it.get("category") == "columns" and any(math.hypot(q[0] - lab.cx, q[1] - lab.cy) <= near for q in it.get("points") or [])
                for it in items
            ):
                continue  # a column size whose column is right there
            des = info["designation"]
            key = re.sub(r"[\s\-]", "", des)
            spot = (key, int(lab.cx // 8), int(lab.cy // 8))
            if spot in seen:
                continue
            seen.add(spot)
            if any(dist(lab.cx, lab.cy, it) <= near for it in by_des.get(key, [])):
                continue
            out.append({
                "designation": des,
                "category": cat,
                "role": info.get("role"),
                "at": [_r(lab.cx), _r(lab.cy)],
                "page": model.page_no,
                "reason": "Checked zoomed in: no member of this size could be traced from this callout - check it on the sheet.",
            })
    return out


def missed_tags(model: PageModel, items: list[dict[str, Any]], rule_infos: dict[tuple[str, float, float], dict[str, Any]], wanted: set[str]) -> list[dict[str, Any]]:
    """Tags on the sheet that no markup answers (nothing of that type within
    4 ft of the tag, or at its leader's end): listed for the estimator so
    nothing is skipped silently."""
    upf = model.units_per_foot or 9.0
    near = 4.0 * upf
    by_des: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_des.setdefault(re.sub(r"[\s\-]", "", it.get("designation") or ""), []).append(it)

    def dist(x: float, y: float, it: dict[str, Any]) -> float:
        best = 1e9
        pts = it.get("points") or []
        if len(pts) == 1:
            best = math.hypot(pts[0][0] - x, pts[0][1] - y)
        elif len(pts) >= 2:
            best = _pt_seg_dist(x, y, (pts[0][0], pts[0][1], pts[1][0], pts[1][1], 1.0))
        lr = it.get("label_rect")
        if lr and len(lr) == 4:
            best = min(best, math.hypot((lr[0] + lr[2]) / 2.0 - x, (lr[1] + lr[3]) / 2.0 - y))
        return best

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for (des, x, y), info in rule_infos.items():
        if info.get("category") not in wanted:
            continue
        key = re.sub(r"[\s\-]", "", des)
        spot = (key, int(x // 8), int(y // 8))
        if spot in seen:
            continue
        seen.add(spot)
        cands = by_des.get(key, [])
        if any(dist(x, y, it) <= near for it in cands):
            continue
        out.append({
            "designation": des,
            "category": info.get("category"),
            "role": info.get("role"),
            "at": [_r(x), _r(y)],
            "page": model.page_no,
            "reason": "No line, wall or bay could be traced from this tag - check it on the sheet.",
        })
    return out


def run_models(
    models: list[PageModel],
    spec_models: list[PageModel],
    categories: Iterable[str],
    *,
    hints_by_page: dict[int, dict[str, dict[str, Any]]] | None = None,
    include_details: bool = False,
    extra_specs: dict[str, str] | None = None,
    rules: bool = False,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:
    cats = [c for c in categories if c in CATEGORIES] or list(CATEGORIES)
    # Framing rules apply once the set has recognised plan sheets.
    rules_on = bool(rules and any(m.kind for m in models))
    specs, spots = schedule_rows(spec_models)
    col_marks = column_schedule(spec_models)
    if extra_specs:
        for k, v in extra_specs.items():
            if k.startswith("@COL:"):
                col_marks.setdefault(k[5:], v)
            else:
                specs.setdefault(k, v)
    results: list[dict[str, Any]] = []
    for model in models:
        if rules_on and not model.kind:
            results.append({
                "page": model.page_no,
                "scale": model.scale_text,
                "units_per_foot": model.units_per_foot,
                "paper_in_per_ft": round(model.units_per_foot / 72.0, 5) if model.units_per_foot else None,
                "detail_sheet": is_detail_sheet(model),
                "counts": {},
                "items": [],
                "note": "Not a framing, shear wall or foundation plan - skipped by the framing rules.",
                "sheet_kind": None,
            })
            continue
        if is_detail_sheet(model) and not include_details:
            results.append({
                "page": model.page_no,
                "scale": model.scale_text,
                "units_per_foot": model.units_per_foot,
                "paper_in_per_ft": round(model.units_per_foot / 72.0, 5) if model.units_per_foot else None,
                "detail_sheet": True,
                "counts": {},
                "items": [],
                "note": "Detail sheet (large scale) - skipped. Tick 'Include detail sheets' to read it.",
            })
            continue
        hints = (hints_by_page or {}).get(model.page_no)
        res = take_off_page(model, cats, hints=hints, specs=specs, skip_spots=spots, col_marks=col_marks, rules=rules_on, detail_scan=detail_scan, zoom_parts=zoom_parts)
        res["_size"] = (model.width, model.height)
        results.append(res)
    if "columns" in cats:
        sources = [m for m in spec_models if m.column_source] + [m for m in models if m.index is not None]
        name_columns_across_sheets(results, sources, col_marks)
    for res in results:
        res.pop("_size", None)
    # What was read before drawing (OE-DELIVERY 2026-11-04-auto-takeoff-zoom):
    # schedules, column marks and the sheets the notes came from.
    read = {
        "schedule_rows": len(specs),
        "wall_types": sum(1 for k in specs if _WALL_TAG_RE.match(k)),
        "header_jamb_types": sum(1 for k in specs if _HDR_TAG_RE.match(k) or _JAMB_TAG_RE.match(k)),
        "column_marks": len(col_marks),
        "sheets_read": len(spec_models),
    }
    if rules_on:
        fs = next((m.fsched for m in models if m.fsched), {})
        read["framing_rules"] = True
        read["schedules"] = {k: sorted(v) for k, v in fs.items()}
        read["sheets"] = [
            {"page": m.page_no, "kind": m.kind, "level": m.level} for m in models if m.kind
        ]
    return {"pages": results, "specs": specs, "column_marks": col_marks, "read": read}


def run_auto_takeoff(
    pdf,
    pages: list[int],
    categories: Iterable[str],
    *,
    hints_by_page: dict[int, dict[str, dict[str, Any]]] | None = None,
    include_details: bool = False,
    extra_specs: dict[str, str] | None = None,
    rules: bool = False,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:
    """Run Auto Takeoff over ``pages`` (1-based) of an open PyMuPDF doc."""
    models, spec_models = build_models(pdf, pages, rules=rules)
    return run_models(
        models,
        spec_models,
        categories,
        hints_by_page=hints_by_page,
        include_details=include_details,
        extra_specs=extra_specs,
        rules=rules,
        detail_scan=detail_scan,
        zoom_parts=zoom_parts,
    )
