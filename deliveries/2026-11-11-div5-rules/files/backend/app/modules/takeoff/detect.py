# OE-DELIVERY: 2026-10-30-detect-v6 (was 2026-10-30-detect-v5)
"""Auto-detect pilot for the PDF Measurements Detect tab.

Implements the estimator's flow on top of the uploaded drawing file:

* ``build_summary`` reads the set first — general-notes rules (grades,
  stud and camber rules, defaults), the schedules present, a per-page
  map (readable or not, scale strings, plan titles) and a census of
  every member designation in the set, so the panel can show what the
  system understood before anything is detected.
* ``run_detect`` finds one category (beams in this pilot, plus the
  cheap pattern categories) on the plans: designation labels with
  their on-sheet position, nearby stud / camber / length text, the
  Standards Library weight for the designation, and a schedule
  cross-check — a member found on a plan AND in its schedule is
  confirmed, anything else is flagged for the estimator to verify.

Scales are handled per page, and per plan when a page carries more
than one plan: each plan title is paired with its nearest scale
string and matches are assigned to the nearest plan, so lengths are
never computed with another plan's scale.

Everything degrades gracefully: a document whose file is not on the
server (a local file the browser opened directly) reports
``available: False`` with guidance instead of raising, mirroring the
AI Assistant panel's behaviour.
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CATEGORIES = ("beams", "columns", "joists", "studs", "walls", "trusses", "area", "other")

# ── designation patterns (matched against one text line at a time) ──
_FRAC = r"\d+\s?/\s?\d+"
_AISC_RE = re.compile(
    r"(?:HSS\s?\d+(?:\.\d+)?\s?[Xx]\s?\d+(?:\.\d+)?\s?[Xx]\s?(?:" + _FRAC + r"|\d*\.\d+|\d+))"
    r"|(?:(?:W|WT|M|MT|S|ST|HP|C|MC)\s?\d+(?:\.\d+)?\s?[Xx]\s?\d+(?:\.\d+)?)"
    r"|(?:L\s?\d+(?:\.\d+)?\s?[Xx]\s?\d+(?:\.\d+)?\s?[Xx]\s?(?:" + _FRAC + r"|\d*\.\d+|\d+))"
    # Round HSS (diameter x wall) and pipe (OE-DELIVERY 2026-11-11-div5-rules).
    r"|(?:HSS\s?\d+(?:\.\d+)?\s?[Xx]\s?(?:" + _FRAC + r"|\d*\.\d+))"
    r"|(?:PIPE\s?\d+(?:\.\d+)?(?:\s?(?:STD|XXS|XS|X-STRONG|SCH\.?\s?\d+))?)"
)
_SSMA_RE = re.compile(r"\d{3,4}\s?(?:SFS|SFT|S|T|U|F)\s?\d{3}\s?-\s?\d{2,3}")
# SJI joists: K, KCS, LH, SLH, DLH (OE-DELIVERY 2026-11-11-div5-rules adds KCS / SLH).
_JOIST_RE = re.compile(r"\d{2,3}\s?(?:DLH|SLH|LH|KCS|K)\s?\d{1,2}\b")
# SJI joist girders: 44G8N9.5K, 48BG10N12K, 36VG6N8.4K.
_GIRDER_RE = re.compile(r"\b\d{2,3}\s?(?:BG|VG|G)\s?\d{1,2}\s?N\s?\d+(?:\.\d+)?\s?K\b")
_SSMA_MILS = {18, 27, 30, 33, 43, 54, 68, 97, 118}

_SCALE_RE = re.compile(
    r"(\d+\s+\d+\s?/\s?\d+|\d+\s?/\s?\d+|\d+(?:\.\d+)?)\s*[\"″]\s*=\s*1\s*'\s*-\s*0\s*[\"″]?|\bNTS\b|NOT TO SCALE",
    re.IGNORECASE,
)
_PLAN_TITLE_RE = re.compile(
    r"\b([A-Z][A-Z0-9&.'()/-]*(?:\s+[A-Z0-9&.'()/-]+){0,5}?\s+PLAN)\b"
)
_PLAN_HINTS = ("FRAMING", "LEVEL", "FLOOR", "ROOF", "FOUNDATION", "MEZZANINE", "CEILING", "ENLARGED", "PARTIAL")

_STUDS_COUNT_RE = re.compile(r"(\d{1,3})\s*(?:-|\s)?\s*(?:3/4|7/8|1/2)?\s*(?:\"|″|IN\.?)?\s*(?:DIA\.?\s*)?STUDS?\b", re.IGNORECASE)
_STUD_ROWS_RE = re.compile(r"(\d)\s*ROWS?\s+(?:OF\s+)?STUDS?\b", re.IGNORECASE)
_CAMBER_RE = re.compile(r"CAMBER\s*(?:OF|=|:)?\s*(\d+(?:\.\d+)?|\d+\s?/\s?\d+)\s*(?:\"|″|IN\.?)?", re.IGNORECASE)
_LENGTH_RE = re.compile(r"(\d{1,2})\s*'\s*-?\s*(\d{1,2}(?:\s+\d+\s*/\s*\d+|/\d+)?)?\s*(?:\"|″)?")
_PAREN_LEN_RE = re.compile(r"\(\+?\s*(\d{1,2}\s*'\s*-?\s*(?:\d{1,2}(?:\s+\d+\s*/\s*\d+|/\d+)?)?\s*(?:\"|″)?)\)")
_GRADE_RE = re.compile(r"\b(?:ASTM\s*)?(?:A992|A500(?:\s*GR\.?\s*[BC])?|A36|A572(?:\s*GR\.?\s*\d+)?|A108|A325|A490)\b", re.IGNORECASE)


def normalize_designation(raw: str) -> str:
    """Upper-case, single X separators, no spaces (HSS 6x2 x 1/8 → HSS6X2X1/8)."""
    text = re.sub(r"\s+", "", (raw or "").upper())
    return text.replace("×", "X")


def _fraction_value(text: str) -> float | None:
    text = (text or "").strip()
    if not text:
        return None
    total = 0.0
    for part in text.split():
        if "/" in part:
            num, _, den = part.partition("/")
            try:
                total += float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                return None
        else:
            try:
                total += float(part)
            except ValueError:
                return None
    return total


def _length_feet(text: str) -> float | None:
    match = _LENGTH_RE.search(text or "")
    if not match:
        return None
    feet = float(match.group(1))
    inches = _fraction_value(match.group(2) or "") or 0.0
    return round(feet + inches / 12.0, 3)


def _ssma_valid(normalized: str) -> bool:
    match = re.fullmatch(r"(\d{3,4})(SFS|SFT|S|T|U|F)(\d{3})-(\d{2,3})", normalized)
    return bool(match) and int(match.group(4)) in _SSMA_MILS


def _category_for(normalized: str, kind: str, line_text: str) -> str:
    if _SSMA_RE.fullmatch(normalized):
        return "studs"
    if _JOIST_RE.fullmatch(normalized):
        return "joists"
    if normalized.startswith("L") or normalized.startswith("PIPE"):
        return "other"
    if kind == "column_schedule" or re.search(r"\bCOL\.?\b|\bCOLUMN\b", line_text, re.IGNORECASE):
        return "columns"
    return "beams"


def _page_kind(text: str) -> str:
    upper = (text or "").upper()
    if "COLUMN SCHEDULE" in upper:
        return "column_schedule"
    if "BEAM SCHEDULE" in upper:
        return "beam_schedule"
    if "JOIST SCHEDULE" in upper:
        return "joist_schedule"
    if "GENERAL NOTES" in upper:
        return "notes"
    if "SCHEDULE" in upper:
        return "schedule"
    return "sheet"


class _Line:
    """One visual text line: joined words plus where each word sits."""

    __slots__ = ("text", "words")

    def __init__(self) -> None:
        self.text = ""
        self.words: list[tuple[str, tuple[float, float, float, float], int, int]] = []

    def add(self, word: str, rect: tuple[float, float, float, float]) -> None:
        start = len(self.text) + (1 if self.text else 0)
        self.text = f"{self.text} {word}" if self.text else word
        self.words.append((word, rect, start, start + len(word)))

    def rect_for(self, start: int, end: int) -> tuple[float, float, float, float] | None:
        boxes = [rect for _, rect, w_start, w_end in self.words if w_start < end and w_end > start]
        if not boxes:
            return None
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )


def _transform_rect(rect, matrix) -> tuple[float, float, float, float]:
    """Map a rect through a fitz rotation matrix (user space → display space)."""
    if matrix is None:
        return rect
    a, b, c, d, e, f = (float(v) for v in matrix)
    xs: list[float] = []
    ys: list[float] = []
    for x, y in ((rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3])):
        xs.append(a * x + c * y + e)
        ys.append(b * x + d * y + f)
    return (min(xs), min(ys), max(xs), max(ys))


def _page_lines(page) -> list[_Line]:
    # fitz reports word boxes in UNROTATED page space even on rotated
    # sheets (the Gold Rush set is rotation=90), while the viewer works
    # in display space — transform every box first, or titles, scales
    # and marks all land in the wrong geometry.
    matrix = page.rotation_matrix if getattr(page, "rotation", 0) else None
    raw: list[tuple[str, tuple[float, float, float, float]]] = []
    for x0, y0, x1, y1, word, *_rest in page.get_text("words"):
        rect = _transform_rect((float(x0), float(y0), float(x1), float(y1)), matrix)
        raw.append((word, rect))
    heights = sorted(r[3] - r[1] for _w, r in raw if r[3] > r[1])
    median_h = heights[len(heights) // 2] if heights else 10.0
    bucket = max(5.0, median_h * 0.6)
    lines: dict[int, _Line] = {}
    for word, rect in raw:
        key = int(round(((rect[1] + rect[3]) / 2.0) / bucket))
        line = lines.setdefault(key, _Line())
        line.add(word, rect)
    result: list[_Line] = []
    for line in lines.values():
        line.words.sort(key=lambda item: item[1][0])
        rebuilt = _Line()
        for word, rect, _s, _e in line.words:
            rebuilt.add(word, rect)
        result.append(rebuilt)
    return result


def _context_around(lines: list[_Line], rect, page_no: int) -> str:
    x0, y0, x1, y1 = rect
    parts: list[str] = []
    for line in lines:
        for _word, w_rect, _s, _e in line.words:
            cx = (w_rect[0] + w_rect[2]) / 2.0
            cy = (w_rect[1] + w_rect[3]) / 2.0
            if x0 - 190 <= cx <= x1 + 190 and y0 - 52 <= cy <= y1 + 52:
                parts.append(_word)
                break
        else:
            continue
        parts.append(line.text)
    return " ".join(parts)


def _extract_details(context: str, *, in_schedule: bool) -> dict[str, Any]:
    details: dict[str, Any] = {"studs": None, "stud_rows": None, "camber": None, "length_ft": None}
    match = _STUDS_COUNT_RE.search(context)
    if match:
        details["studs"] = int(match.group(1))
    match = _STUD_ROWS_RE.search(context)
    if match:
        details["stud_rows"] = int(match.group(1))
    match = _CAMBER_RE.search(context)
    if match:
        value = _fraction_value(match.group(1))
        if value is not None:
            details["camber"] = round(value, 3)
    if in_schedule:
        details["length_ft"] = _length_feet(context)
    return details


def _find_plans(lines: list[_Line], page_rect) -> list[dict[str, Any]]:
    heights = sorted(
        r[3] - r[1] for line in lines for _w, r, _s, _e in line.words if r[3] > r[1]
    )
    median_h = heights[len(heights) // 2] if heights else 10.0
    titles: list[tuple[str, tuple[float, float], float]] = []
    scales: list[tuple[str, tuple[float, float]]] = []
    for line in lines:
        for match in _PLAN_TITLE_RE.finditer(line.text.upper()):
            name = " ".join(match.group(1).split())
            if not any(hint in name for hint in _PLAN_HINTS) or len(name) > 52:
                continue
            rect = line.rect_for(match.start(1), match.end(1))
            # Real plan titles are set in large type; the same words in
            # notes and callouts ("SEE PLAN FOR SIZE...") are body size.
            if rect and (rect[3] - rect[1]) >= 1.45 * median_h:
                titles.append((name.title(), ((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0), rect[3] - rect[1]))
        for match in _SCALE_RE.finditer(line.text):
            rect = line.rect_for(match.start(), match.end())
            if rect:
                scales.append((" ".join(match.group(0).split()), ((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0)))
    titles.sort(key=lambda item: -item[2])
    plans: list[dict[str, Any]] = []
    for name, anchor, _h in titles:
        if len(plans) >= 4:
            break
        if any(
            p["name"] == name and abs(p["anchor"][0] - anchor[0]) < 90 and abs(p["anchor"][1] - anchor[1]) < 90
            for p in plans
        ):
            continue
        nearest = None
        nearest_dist = None
        for scale_text, s_anchor in scales:
            dist = (anchor[0] - s_anchor[0]) ** 2 + (anchor[1] - s_anchor[1]) ** 2
            if nearest_dist is None or dist < nearest_dist:
                nearest, nearest_dist = scale_text, dist
        plans.append({"name": name, "scale": nearest, "anchor": [round(anchor[0], 1), round(anchor[1], 1)]})
    if not plans and scales:
        plans.append({"name": "Sheet", "scale": scales[0][0], "anchor": [page_rect.width / 2.0, page_rect.height / 2.0]})
    # Regions: with 2+ plans, split the page at anchor midpoints.
    if len(plans) >= 2:
        ordered = sorted(plans, key=lambda p: p["anchor"][0])
        vertical = (ordered[-1]["anchor"][0] - ordered[0]["anchor"][0]) >= (
            max(p["anchor"][1] for p in plans) - min(p["anchor"][1] for p in plans)
        )
        cuts = []
        seq = ordered if vertical else sorted(plans, key=lambda p: p["anchor"][1])
        for first, second in zip(seq, seq[1:]):
            axis = 0 if vertical else 1
            cuts.append((first["name"], second["name"], (first["anchor"][axis] + second["anchor"][axis]) / 2.0))
        for plan in plans:
            x0, y0, x1, y1 = 0.0, 0.0, float(page_rect.width), float(page_rect.height)
            for name_a, name_b, cut in cuts:
                axis_is_x = vertical
                if plan["name"] == name_a:
                    if axis_is_x:
                        x1 = min(x1, cut)
                    else:
                        y1 = min(y1, cut)
                elif plan["name"] == name_b:
                    if axis_is_x:
                        x0 = max(x0, cut)
                    else:
                        y0 = max(y0, cut)
            plan["region"] = [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]
    return plans


def _assign_plan(plans: list[dict[str, Any]], rect) -> str | None:
    if not plans:
        return None
    cx = (rect[0] + rect[2]) / 2.0
    cy = (rect[1] + rect[3]) / 2.0
    for plan in plans:
        region = plan.get("region")
        if region and region[0] <= cx <= region[2] and region[1] <= cy <= region[3]:
            return plan["name"]
    best = min(plans, key=lambda p: (p["anchor"][0] - cx) ** 2 + (p["anchor"][1] - cy) ** 2)
    return best["name"]


def _scale_units_per_foot(scale_text: str | None) -> float | None:
    """'1/2" = 1'-0"' → PDF units per real foot (72 units per inch)."""
    if not scale_text:
        return None
    match = re.search(r"(\d+\s+\d+\s?/\s?\d+|\d+\s?/\s?\d+|\d+(?:\.\d+)?)\s*[\"″]\s*=", scale_text)
    if not match:
        return None
    inches = _fraction_value(match.group(1))
    if not inches:
        return None
    return inches * 72.0


def _page_segments(page) -> list[tuple[float, float, float, float, float, float | None]]:
    """Straight vector segments of a page in DISPLAY space.

    Returns (x1, y1, x2, y2, length, stroke_width). CAD sheets draw a
    member as chained collinear segments split at grid crossings, so
    callers merge runs instead of using single segments directly.
    """
    matrix = page.rotation_matrix if getattr(page, "rotation", 0) else None
    segments: list[tuple[float, float, float, float, float, float | None]] = []

    import fitz

    def add(p1, p2, width) -> None:
        x1, y1 = _transform_rect((p1.x, p1.y, p1.x, p1.y), matrix)[:2]
        x2, y2 = _transform_rect((p2.x, p2.y, p2.x, p2.y), matrix)[:2]
        length = math.hypot(x2 - x1, y2 - y1)
        if length >= 20:
            segments.append((x1, y1, x2, y2, length, width))

    for drawing in page.get_drawings():
        width = drawing.get("width")
        for item in drawing["items"]:
            if item[0] == "l":
                add(item[1], item[2], width)
            elif item[0] == "re":
                rect = item[1]
                corners = [
                    fitz.Point(rect.x0, rect.y0),
                    fitz.Point(rect.x1, rect.y0),
                    fitz.Point(rect.x1, rect.y1),
                    fitz.Point(rect.x0, rect.y1),
                ]
                for a, b in zip(corners, corners[1:] + corners[:1]):
                    add(a, b, width)
    return segments


def _point_segment_distance(px: float, py: float, seg) -> float:
    x1, y1, x2, y2 = seg[0], seg[1], seg[2], seg[3]
    dx, dy = x2 - x1, y2 - y1
    denom = dx * dx + dy * dy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / denom))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _merge_run(seed, segments) -> tuple[float, float, float, float]:
    """Grow a seed segment into the full collinear run it belongs to.

    CAD splits a beam line at every crossing grid line; segments on
    the same line (angle within ~2 degrees, offset within 3 units)
    whose projections touch or nearly touch (gap up to 30 units) are
    one member run.
    """
    x1, y1, x2, y2 = seed[0], seed[1], seed[2], seed[3]
    length = seed[4]
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    # Normal direction for the offset test.
    nx, ny = -uy, ux
    base_offset = nx * x1 + ny * y1

    def projection(px: float, py: float) -> float:
        return ux * px + uy * py

    lo = min(projection(x1, y1), projection(x2, y2))
    hi = max(projection(x1, y1), projection(x2, y2))
    changed = True
    while changed:
        changed = False
        for seg in segments:
            sx1, sy1, sx2, sy2, s_len = seg[0], seg[1], seg[2], seg[3], seg[4]
            if s_len < 20:
                continue
            s_ux, s_uy = (sx2 - sx1) / s_len, (sy2 - sy1) / s_len
            if abs(s_ux * ux + s_uy * uy) < 0.9993:  # not parallel
                continue
            if abs(nx * sx1 + ny * sy1 - base_offset) > 3.0:
                continue
            s_lo = min(projection(sx1, sy1), projection(sx2, sy2))
            s_hi = max(projection(sx1, sy1), projection(sx2, sy2))
            if s_lo <= hi + 30 and s_hi >= lo - 30 and (s_lo < lo or s_hi > hi):
                lo = min(lo, s_lo)
                hi = max(hi, s_hi)
                changed = True
    cx, cy = x1 - ux * projection(x1, y1), y1 - uy * projection(x1, y1)
    return (cx + ux * lo, cy + uy * lo, cx + ux * hi, cy + uy * hi)


def _page_text_runs(page) -> list[tuple[list[float], float]]:
    """(rect, angle) for every printed text line, in display space.

    CAD member labels are printed ALONG their member — horizontal
    text on horizontal members, rotated text on vertical and sloped
    members. The label's own print direction therefore states the
    member's orientation on ANY drawing, with no per-file tuning.
    Angles are folded to (-90, 90] like segment angles.
    """
    matrix = page.rotation_matrix
    runs: list[tuple[list[float], float]] = []
    try:
        data = page.get_text("rawdict")
    except Exception:
        return runs
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            dx, dy = line.get("dir", (1.0, 0.0))
            vx = dx * matrix.a + dy * matrix.c
            vy = dx * matrix.b + dy * matrix.d
            angle = math.degrees(math.atan2(vy, vx))
            angle = (angle + 90.0) % 180.0 - 90.0
            runs.append((_transform_rect(tuple(line["bbox"]), matrix), angle))
    return runs


def _label_angle_for(runs: list[tuple[list[float], float]], rect) -> float | None:
    """Print direction of the text run a designation belongs to."""
    cx = (rect[0] + rect[2]) / 2.0
    cy = (rect[1] + rect[3]) / 2.0
    best: tuple[float, float] | None = None
    for run_rect, angle in runs:
        if run_rect[0] - 6 <= cx <= run_rect[2] + 6 and run_rect[1] - 6 <= cy <= run_rect[3] + 6:
            return angle
        rcx = (run_rect[0] + run_rect[2]) / 2.0
        rcy = (run_rect[1] + run_rect[3]) / 2.0
        dist = math.hypot(rcx - cx, rcy - cy)
        if dist <= 24 and (best is None or dist < best[0]):
            best = (dist, angle)
    return best[1] if best else None


def _associate_line(entry: dict[str, Any], segments) -> None:
    """Attach the member's own line (and its angle) to a plan match."""
    rect = entry["rect"]
    cx = (rect[0] + rect[2]) / 2.0
    cy = (rect[1] + rect[3]) / 2.0
    near = []
    for seg in segments:
        if seg[4] < 55:
            continue
        dist = _point_segment_distance(cx, cy, seg)
        if dist <= 60:
            near.append((seg, dist))
    if not near:
        return
    # Orientation first: the label is printed along its own member,
    # so prefer segments running the same way as the label text.
    # A brace or edge beam crossing at a different angle is then
    # rejected even when it passes closer or runs longer. Falls
    # back to all nearby segments when none match the direction.
    label_angle = entry.get("label_angle")
    if label_angle is not None:
        def _aligned(item) -> bool:
            seg = item[0]
            seg_angle = math.degrees(math.atan2(seg[3] - seg[1], seg[2] - seg[0]))
            seg_angle = (seg_angle + 90.0) % 180.0 - 90.0
            diff = abs(seg_angle - label_angle) % 180.0
            if diff > 90.0:
                diff = 180.0 - diff
            return diff <= 12.0

        aligned = [item for item in near if _aligned(item)]
        if aligned:
            near = aligned
    # Rank by distance bucket first, then by run length. Labels sit
    # ON their own member, so the member is (nearly) always the
    # closest line; a long diagonal brace crossing the field a
    # little farther away must not steal the label just for being
    # the longest/heaviest segment nearby (the v2/v3 failure on
    # X-braced joist fields).
    def _rank(item):
        seg, dist = item
        return (round(dist / 8.0), -seg[4], dist)

    seed = min(near, key=_rank)[0]
    x1, y1, x2, y2 = _merge_run(seed, segments)
    run_length = math.hypot(x2 - x1, y2 - y1)
    if run_length < 40:
        return
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    angle = (angle + 90.0) % 180.0 - 90.0  # fold so a label never reads upside down
    entry["line"] = [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]
    entry["angle"] = round(angle, 1)
    entry["line_length_units"] = round(run_length, 1)


def _line_rect(line: _Line) -> tuple[float, float, float, float] | None:
    if not line.words:
        return None
    return (
        min(w[1][0] for w in line.words),
        min(w[1][1] for w in line.words),
        max(w[1][2] for w in line.words),
        max(w[1][3] for w in line.words),
    )


_SCHEDULE_KIND_WORDS = (("COLUMN", "column_schedule"), ("JOIST", "joist_schedule"), ("BEAM", "beam_schedule"))
_SCHEDULE_ROW_WORDS = ("MARK", "SIZE", "LENGTH", "QTY", "TYPE", "REMARK", "MEMBER")


def _schedule_regions(lines: list[_Line]) -> list[dict[str, Any]]:
    """Table regions under SCHEDULE headings on a page.

    A sheet often carries plans AND schedules together. Classifying
    the whole page as a schedule (the v1/v2 behaviour) marked every
    plan label on such a page as schedule-sourced — and line
    association only runs for plan-sourced labels, so mixed pages
    got no lines at all. Regions keep the two apart: only text
    inside a schedule table's region counts as schedule-sourced.
    A region starts at a short SCHEDULE heading line and grows
    downward over row-like lines (designations, numbers, table
    header words) in the heading's column band, stopping at a
    plan title or a wide vertical gap.
    """
    rects: list[tuple[_Line, tuple[float, float, float, float]]] = []
    for line in lines:
        rect = _line_rect(line)
        if rect:
            rects.append((line, rect))
    ordered = sorted(rects, key=lambda item: (item[1][1] + item[1][3]) / 2.0)
    regions: list[dict[str, Any]] = []
    for line, rect in rects:
        upper = line.text.upper()
        if "SCHEDULE" not in upper or len(line.words) > 8:
            continue
        if any(regex.search(line.text) for regex in (_AISC_RE, _SSMA_RE, _JOIST_RE)):
            continue
        kind = "schedule"
        for word, word_kind in _SCHEDULE_KIND_WORDS:
            if word in upper:
                kind = word_kind
                break
        xlo, xhi = rect[0] - 30, rect[2] + 520
        bottom = rect[3]
        prev = rect[3]
        for other, other_rect in ordered:
            cy = (other_rect[1] + other_rect[3]) / 2.0
            if cy <= rect[3] or cy - prev > 55:
                continue
            if other_rect[0] > xhi or other_rect[2] < xlo:
                continue
            other_upper = other.text.upper()
            if " PLAN" in other_upper and any(hint in other_upper for hint in _PLAN_HINTS):
                break
            if (
                any(regex.search(other.text) for regex in (_AISC_RE, _SSMA_RE, _JOIST_RE))
                or re.search(r"\d", other.text)
                or any(word in other_upper for word in _SCHEDULE_ROW_WORDS)
            ):
                bottom = max(bottom, other_rect[3])
                prev = cy
        regions.append({"kind": kind, "rect": (xlo, rect[1] - 5, xhi, bottom + 12)})
    return regions


def _region_for(regions: list[dict[str, Any]], rect) -> dict[str, Any] | None:
    cx = (rect[0] + rect[2]) / 2.0
    cy = (rect[1] + rect[3]) / 2.0
    for region in regions:
        rr = region["rect"]
        if rr[0] - 10 <= cx <= rr[2] + 10 and rr[1] <= cy <= rr[3]:
            return region
    return None


def scan_document(pdf, weights: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """One pass over the file: pages, plans, schedules and every match."""
    pages: list[dict[str, Any]] = []
    all_matches: list[dict[str, Any]] = []
    schedules: dict[str, set[str]] = {"beams": set(), "columns": set(), "joists": set()}
    notes_pages: list[int] = []

    for page_no, page in enumerate(pdf, start=1):
        text = page.get_text()
        kind = _page_kind(text)
        upper_text = text.upper()
        if kind == "notes" or "FRAMING NOTES" in upper_text or "STRUCTURAL NOTES" in upper_text:
            notes_pages.append(page_no)
        lines = _page_lines(page)
        plans = _find_plans(lines, page.rect)
        page_scales = sorted({p["scale"] for p in plans if p.get("scale")})
        pages.append(
            {
                "page": page_no,
                "kind": kind,
                "readable": len(text.strip()) >= 40,
                "chars": len(text),
                "width": round(float(page.rect.width), 1),
                "height": round(float(page.rect.height), 1),
                "scales": page_scales,
                "plans": plans,
            }
        )
        regions = _schedule_regions(lines)
        text_runs = _page_text_runs(page)
        for line in lines:
            found: list[tuple[str, int, int, str]] = []
            for regex, flavor in ((_AISC_RE, "aisc"), (_SSMA_RE, "ssma"), (_JOIST_RE, "joist")):
                for match in regex.finditer(line.text):
                    found.append((match.group(0), match.start(), match.end(), flavor))
            for raw, start, end, flavor in found:
                normalized = normalize_designation(raw)
                if flavor == "ssma" and not _ssma_valid(normalized):
                    continue
                if flavor == "joist":
                    depth = int(re.match(r"\d+", normalized).group(0))
                    if depth < 8 or depth > 48:
                        continue
                rect = line.rect_for(start, end)
                if rect is None:
                    continue
                region = _region_for(regions, rect)
                in_schedule = region is not None
                eff_kind = region["kind"] if region else kind
                context = line.text if in_schedule else _context_around(lines, rect, page_no)
                category = _category_for(normalized, eff_kind, line.text)
                details = _extract_details(context, in_schedule=in_schedule)
                existing = "(E)" in line.text[:start].upper()
                if not in_schedule and details["length_ft"] is None:
                    paren = _PAREN_LEN_RE.search(line.text[end:])
                    if paren:
                        details["length_ft"] = _length_feet(paren.group(1))
                weight_row = weights.get(normalized) or {}
                entry = {
                    "designation": weight_row.get("designation") or normalized,
                    "normalized": normalized,
                    "category": category,
                    "page": page_no,
                    "plan": _assign_plan(plans, rect),
                    "rect": [round(v, 1) for v in rect],
                    "label_angle": _label_angle_for(text_runs, rect),
                    "page_size": [round(float(page.rect.width), 1), round(float(page.rect.height), 1)],
                    "source": "schedule" if in_schedule else "plan",
                    "existing": existing,
                    "studs": details["studs"],
                    "stud_rows": details["stud_rows"],
                    "camber_in": details["camber"],
                    "length_ft": details["length_ft"],
                    "weight_lb_ft": weight_row.get("weight_lb_ft"),
                    "line": None,
                    "angle": None,
                    "length_source": ("schedule" if in_schedule else "annotation") if details["length_ft"] else None,
                }
                entry["line_weight_lb"] = (
                    round(entry["length_ft"] * entry["weight_lb_ft"], 1)
                    if entry["length_ft"] and entry["weight_lb_ft"]
                    else None
                )
                all_matches.append(entry)
                if in_schedule and category in schedules:
                    schedules[category].add(normalized)

    # CAD exports often draw the same label twice (a bold double-draw);
    # collapse exact duplicates so the panel never shows a row twice.
    deduped: list[dict[str, Any]] = []
    seen_keys: set[tuple] = set()
    for entry in all_matches:
        key = (
            entry["page"],
            entry["normalized"],
            round(entry["rect"][0] / 5),
            round(entry["rect"][1] / 5),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(entry)
    all_matches = deduped

    # Attach each plan label to the member line it names: the line is
    # drawn on the sheet, the label is rotated to the line's angle,
    # and — when the plan's scale is known — the run gives a geometric
    # length for members the schedule/annotation did not size.
    page_info = {p["page"]: p for p in pages}
    by_page: dict[int, list[dict[str, Any]]] = {}
    for entry in all_matches:
        if entry["source"] == "plan":
            by_page.setdefault(entry["page"], []).append(entry)
    for page_no, entries in by_page.items():
        try:
            segments = _page_segments(pdf[page_no - 1])
        except Exception:
            continue
        if not segments:
            continue
        info = page_info.get(page_no) or {}
        plan_scales = {pl["name"]: pl.get("scale") for pl in info.get("plans", [])}
        for entry in entries:
            _associate_line(entry, segments)
            if entry.get("line") and entry["length_ft"] is None:
                scale_text = plan_scales.get(entry.get("plan") or "")
                if not scale_text:
                    # No plan match: fall back to the DOMINANT plan's
                    # scale (plans are ordered by title size, biggest
                    # first), not an alphabetical page-scale list —
                    # the first alphabetical scale on a multi-scale
                    # sheet is often a detail's enlarged scale.
                    page_plans = info.get("plans") or []
                    scale_text = (page_plans[0].get("scale") if page_plans else None) or (info.get("scales") or [None])[0]
                units_per_foot = _scale_units_per_foot(scale_text)
                if units_per_foot:
                    entry["length_ft"] = round(entry["line_length_units"] / units_per_foot, 2)
                    entry["length_source"] = "geometry"
                    if entry["weight_lb_ft"]:
                        entry["line_weight_lb"] = round(entry["length_ft"] * entry["weight_lb_ft"], 1)

    # Cross-check: plan finds that also sit in their schedule are confirmed.
    for entry in all_matches:
        confirmed = entry["source"] == "schedule" or entry["normalized"] in schedules.get(entry["category"], set())
        entry["verified"] = bool(confirmed and entry["source"] == "plan" and not entry.get("existing"))
        entry["in_schedule"] = entry["normalized"] in schedules.get(entry["category"], set())
        if entry.get("existing"):
            entry["note"] = "Existing member (E) — confirm it is in this scope."
        elif entry["source"] == "plan" and not entry["in_schedule"]:
            entry["note"] = "Found on the plan — not in the schedule. Verify."
        elif entry["source"] == "schedule":
            entry["note"] = "From the schedule — location on a plan not confirmed."
        else:
            entry["note"] = ""
        if entry.get("length_source") == "geometry":
            entry["note"] = (entry["note"] + " " if entry["note"] else "") + "Length read from the plan line at the sheet scale — verify."

    return {"pages": pages, "matches": all_matches, "schedules": schedules, "notes_pages": notes_pages}


def extract_notes_rules(pdf, notes_pages: list[int]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(kind: str, sentence: str, page_no: int) -> None:
        clean = " ".join(sentence.split())[:230]
        key = clean.lower()
        if len(clean) < 12 or key in seen:
            return
        seen.add(key)
        rules.append({"kind": kind, "text": clean, "page": page_no})

    for page_no in notes_pages[:6]:
        text = pdf[page_no - 1].get_text()
        for sentence in re.split(r"(?<=[.;])\s+", text.replace("\n", " ")):
            upper = sentence.upper()
            if "CAMBER" in upper:
                add("camber", sentence, page_no)
            elif "STUD" in upper:
                add("studs", sentence, page_no)
            elif _GRADE_RE.search(sentence):
                add("grade", sentence, page_no)
            elif "UNO" in upper or upper.strip().startswith(("ALL BEAMS", "ALL COLUMNS", "ALL JOISTS", "ALL STEEL")):
                add("default", sentence, page_no)
            elif "GALV" in upper:
                add("coating", sentence, page_no)
            if len(rules) >= 14:
                return rules
    return rules


def summarize(scan: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
    census: dict[str, dict[str, Any]] = {}
    for category in CATEGORIES:
        entries = [m for m in scan["matches"] if m["category"] == category]
        unique: dict[str, int] = {}
        for entry in entries:
            unique[entry["designation"]] = unique.get(entry["designation"], 0) + 1
        census[category] = {
            "total": len(entries),
            "unique": [
                {"designation": name, "count": count}
                for name, count in sorted(unique.items(), key=lambda item: -item[1])
            ],
            "pages": sorted({m["page"] for m in entries}),
        }
    schedules = [
        {"kind": kind, "designations": sorted(values)}
        for kind, values in scan["schedules"].items()
        if values
    ]
    return {
        "available": True,
        "page_count": len(scan["pages"]),
        "readable_pages": sum(1 for p in scan["pages"] if p["readable"]),
        "pages": scan["pages"],
        "notes_rules": rules,
        "schedules": schedules,
        "census": census,
    }


# ── document / file plumbing ──────────────────────────────────────


def _resolve_file(doc) -> Path | None:
    raw = getattr(doc, "file_path", None)
    if not raw:
        return None
    path = Path(str(raw))
    if path.exists():
        return path
    if not path.is_absolute():
        try:
            from app.core.storage import resolve_data_dir

            candidate = resolve_data_dir() / str(raw)
            if candidate.exists():
                return candidate
        except Exception:
            pass
    return None


async def _weights_for(session, designations: set[str]) -> dict[str, dict[str, Any]]:
    weights: dict[str, dict[str, Any]] = {}
    if session is None or not designations:
        return weights
    try:
        from app.modules.standards_library.service import lookup_section
    except Exception:
        return weights
    for designation in sorted(designations):
        try:
            result = await lookup_section(session, designation)
        except Exception:
            continue
        match = (result or {}).get("match")
        if match is not None:
            weights[designation] = {
                "designation": match.designation,
                "weight_lb_ft": match.weight_lb_ft,
            }
    return weights


_SCAN_CACHE: dict[str, dict[str, Any]] = {}


async def _scan_document(session, doc):
    path = _resolve_file(doc)
    if path is None:
        return None
    import fitz

    try:
        stat = path.stat()
        cache_key = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    except OSError:
        cache_key = None
    pdf = fitz.open(path)
    try:
        designations: set[str] = set()
        for page in pdf:
            for line in _page_lines(page):
                for regex in (_AISC_RE, _SSMA_RE, _JOIST_RE):
                    for match in regex.finditer(line.text):
                        designations.add(normalize_designation(match.group(0)))
        weights = await _weights_for(session, designations)
        fingerprint = "|".join(f"{k}={weights.get(k, {}).get('weight_lb_ft')}" for k in sorted(weights))
        full_key = f"{cache_key}|{fingerprint}" if cache_key else None
        if full_key and full_key in _SCAN_CACHE:
            return _SCAN_CACHE[full_key]
        scan = scan_document(pdf, weights)
        if full_key:
            # One open document is the norm; keep the cache bounded.
            _SCAN_CACHE.clear()
            _SCAN_CACHE[full_key] = scan
        return scan
    finally:
        pdf.close()


_UNAVAILABLE = {
    "available": False,
    "message": (
        "This drawing is open as a local file, so the server cannot read it yet. "
        "Upload it to the project once — then Detect can read the notes, plans and schedules."
    ),
}


async def build_summary(session, doc) -> dict[str, Any]:
    scan = await _scan_document(session, doc)
    if scan is None:
        return dict(_UNAVAILABLE)
    path = _resolve_file(doc)
    import fitz

    pdf = fitz.open(path)
    try:
        rules = extract_notes_rules(pdf, scan["notes_pages"])
    finally:
        pdf.close()
    summary = summarize(scan, rules)
    summary["document_id"] = str(getattr(doc, "id", ""))
    return summary


async def run_detect(session, doc, category: str, page: int | None = None) -> dict[str, Any]:
    if category not in CATEGORIES:
        category = "beams"
    scan = await _scan_document(session, doc)
    if scan is None:
        return dict(_UNAVAILABLE)
    matches = [dict(m) for m in scan["matches"] if m["category"] == category]
    if page is not None:
        matches = [m for m in matches if m["page"] == page]
    for index, entry in enumerate(matches, start=1):
        entry["id"] = f"{category}-{index}"
    page_info = next((p for p in scan["pages"] if p["page"] == page), None) if page else None
    return {
        "available": True,
        "category": category,
        "page": page,
        "plans": page_info["plans"] if page_info else [],
        "scales": page_info["scales"] if page_info else [],
        "found": len(matches),
        "to_verify": sum(1 for m in matches if not m["verified"]),
        "matches": matches,
    }
