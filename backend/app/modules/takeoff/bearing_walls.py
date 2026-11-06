"""Load bearing or not, read from the floor framing above the walls
(OE-DELIVERY 2026-11-11-div5-rules).

An estimator decides which walls carry load by looking at the framing plan
of the floor above: walls the joists / trusses land on (running across them)
are load bearing; walls the joists run alongside are non-load bearing. A
wall-type tag or schedule that says so still wins (shear walls stay shear
walls).

The two sheets are lined up the way a person lays one print over another:
same scale (feet), then shifted until the joist ends sit on the walls.
"""

from __future__ import annotations

import math
import re
from typing import Any

_ORD = {"GROUND": 1, "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7, "EIGHTH": 8}
_ORD_RE = re.compile(r"\b(\d{1,2})\s*(?:ST|ND|RD|TH)\b|\b(GROUND|FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH)\b")
FRAMING_PAGE_RE = re.compile(
    r"FRAM(?:E|ING)\s+(?:LAYOUT|PLAN)|JOIST\s+(?:LAYOUT|PLAN)|TRUSS\s+(?:LAYOUT|PLAN)|FLOOR\s+FRAMING|ROOF\s+FRAMING|DECK(?:ING)?\s+PLAN"
)
WALL_PAGE_RE = re.compile(r"\bWALLS?\b[^\n]{0,40}\b(?:LAYOUT|PLAN|SECTIONS?)\b|\bSHEAR\s*WALL\b")
_SAYS_RE = re.compile(r"NON[\s-]*(?:LOAD|BEARING|STRUCTURAL)|\bNLBW?\b|LOAD[\s-]*BEARING|\bLBW?\b|\bBEARING\s+WALL|PARTITION", re.IGNORECASE)
_KEEP_ROLES = {"Shear Wall", "Strap Braced Wall", "CMU Wall"}


def title_text(model) -> str:
    """The sheet's big-print titles, joined (the drawing title and its
    second line, e.g. 'LGS FLOOR FRAME LAYOUT PLAN' / 'FOR 2nd,FLOOR')."""
    lines = model.text_lines or []
    if not lines:
        return ""
    hs = sorted(bb[3] - bb[1] for _t, bb, _d, _p in lines if bb[3] > bb[1])
    if not hs:
        return ""
    med = hs[len(hs) // 2]
    big = [t for t, bb, _d, _p in lines if bb[3] - bb[1] >= 1.6 * med and len(t) <= 80]
    return " | ".join(" ".join(t.upper().split()) for t in big)


def levels(title: str) -> set[int]:
    out: set[int] = set()
    for part in title.split("|"):
        if not re.search(r"FLOOR|LEVEL|FRAM|WALL|JOIST|TRUSS", part) and not re.match(r"\s*FOR\b", part):
            continue
        for m in _ORD_RE.finditer(part):
            out.add(int(m.group(1)) if m.group(1) else _ORD[m.group(2)])
    return out


def _framing_lines(model) -> tuple[list[tuple[tuple[float, float], tuple[float, float]]], float]:
    """Joist / truss lines of a framing sheet, in feet, and their spacing."""
    from app.modules.takeoff import detail_scan as Z

    upf = model.units_per_foot or 0.0
    if not upf or model.detail is None:
        return [], 0.0
    out = []
    pitches = []
    for f in Z.plan_joist_fields(model):
        pitches.append(f["pitch"] / upf)
        for a, b in f["lines"]:
            out.append(((a[0] / upf, a[1] / upf), (b[0] / upf, b[1] / upf)))
    pitch = sorted(pitches)[len(pitches) // 2] if pitches else 0.0
    return out, pitch


def _walls_ft(res: dict[str, Any]) -> list[tuple[dict[str, Any], tuple[float, float], tuple[float, float]]]:
    upf = res.get("units_per_foot") or 0.0
    if not upf:
        return []
    out = []
    for it in res.get("items") or []:
        if it.get("category") != "walls" or it.get("kind") != "line" or len(it.get("points") or []) != 2:
            continue
        (ax, ay), (bx, by) = it["points"]
        out.append((it, (ax / upf, ay / upf), (bx / upf, by / upf)))
    return out


def _seg_dist(px, py, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / L2))
    return math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


def _register(walls, joists) -> tuple[float, float, float] | None:
    """Shift (dx, dy) taking framing feet onto wall-sheet feet, and the
    share of joist ends that then land on a wall. Candidates line up the
    plans' left/right and top/bottom edges; the best is kept."""
    if not walls or not joists:
        return None
    wx = [p[0] for _it, a, b in walls for p in (a, b)]
    wy = [p[1] for _it, a, b in walls for p in (a, b)]
    jx = [p[0] for a, b in joists for p in (a, b)]
    jy = [p[1] for a, b in joists for p in (a, b)]
    cand_x = {round(min(wx) - min(jx), 2), round(max(wx) - max(jx), 2), round((min(wx) + max(wx) - min(jx) - max(jx)) / 2.0, 2)}
    cand_y = {round(min(wy) - min(jy), 2), round(max(wy) - max(jy), 2), round((min(wy) + max(wy) - min(jy) - max(jy)) / 2.0, 2)}
    ends = [p for a, b in joists for p in (a, b)]
    if len(ends) > 400:
        ends = ends[:: max(1, len(ends) // 400)]
    segs = [(a, b) for _it, a, b in walls]

    def score(dx: float, dy: float, pts) -> float:
        hits = 0
        for x, y in pts:
            px, py = x + dx, y + dy
            if any(_seg_dist(px, py, a, b) <= 1.0 for a, b in segs):
                hits += 1
        return hits / max(1, len(pts))

    best = None
    for dx in cand_x:
        for dy in cand_y:
            sc = score(dx, dy, ends)
            if best is None or sc > best[2]:
                best = (dx, dy, sc)
    if best is None:
        return None
    # Slide the print about the best guess, half a foot at a time, until the
    # joist ends sit on the walls (the edges of the two plans rarely match
    # exactly: a canopy, a dimension line) (OE-DELIVERY 2026-11-11-div5-rules).
    few = ends[:: max(1, len(ends) // 150)]
    bx, by, _ = best
    fine = (bx, by, score(bx, by, few))
    for i in range(-6, 7):
        for j in range(-6, 7):
            sc = score(bx + 0.5 * i, by + 0.5 * j, few)
            if sc > fine[2] + 1e-9:
                fine = (bx + 0.5 * i, by + 0.5 * j, sc)
    return (fine[0], fine[1], score(fine[0], fine[1], ends))


def classify(walls, joists, pitch: float, shift: tuple[float, float]) -> list[tuple[dict[str, Any], str, int, int]]:
    """(wall item, verdict, joists bearing, joists alongside) per wall."""
    dx, dy = shift
    J = [((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy)) for a, b in joists]
    out = []
    for it, a, b in walls:
        L = math.dist(a, b)
        if L < 1.0:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        bear = along = 0
        spans: list[tuple[float, float]] = []
        for p, q in J:
            M = math.dist(p, q) or 1.0
            vx, vy = (q[0] - p[0]) / M, (q[1] - p[1]) / M
            cross = abs(ux * vy - uy * vx)
            if cross > 0.85:
                # Joist across the wall line: does it reach the wall?
                den = ux * vy - uy * vx
                wx_, wy_ = p[0] - a[0], p[1] - a[1]
                t = (wx_ * vy - wy_ * vx) / den  # along the wall
                u = (wx_ * uy - wy_ * ux) / den  # along the joist from p
                if -0.5 <= t <= L + 0.5 and -1.0 <= u <= M + 1.0:
                    bear += 1
            elif cross < 0.35:
                off = abs((p[0] - a[0]) * -uy + (p[1] - a[1]) * ux)
                if off <= max(2.0, 2.0 * pitch):
                    t1, t2 = (p[0] - a[0]) * ux + (p[1] - a[1]) * uy, (q[0] - a[0]) * ux + (q[1] - a[1]) * uy
                    lo, hi = max(0.0, min(t1, t2)), min(L, max(t1, t2))
                    if hi > lo:
                        along += 1
                        spans.append((lo, hi))
        need = max(2, int(0.3 * L / pitch)) if pitch > 0 else 2
        if bear >= need:
            out.append((it, "Load Bearing Wall", bear, along))
        # Joists alongside over much of its length (a long wall may be
        # passed by several joist runs end to end).
        cover = 0.0
        end = 0.0
        for lo, hi in sorted(spans):
            lo = max(lo, end)
            if hi > lo:
                cover += hi - lo
                end = hi
        if bear < need and bear < max(2, need // 3) and cover >= 0.4 * L:
            out.append((it, "Non-Load Bearing Wall", bear, along))
    return out


def apply(results: list[dict[str, Any]], models: list[Any], sources: list[Any]) -> dict[str, Any]:
    """Set load bearing / non-load bearing on wall markups from the framing
    of the floor above. Returns a short summary per wall sheet."""
    by_page = {m.page_no: m for m in list(models) + list(sources)}
    framing = []
    for m in by_page.values():
        title = title_text(m)
        if not FRAMING_PAGE_RE.search(title):
            continue
        J, pitch = _framing_lines(m)
        if len(J) >= 6:
            framing.append((m, levels(title), J, pitch, "ROOF" in title))
    summary: dict[str, Any] = {}
    if not framing:
        return summary
    for res in results:
        m = by_page.get(res.get("page"))
        if m is None or m.kind:  # house-rules sheets: the rules decide
            continue
        title = title_text(m)
        walls = _walls_ft(res)
        if len(walls) < 4:
            continue
        lv = levels(title)
        # The floor above the walls: framing for level L+1 (else the roof
        # over the top floor, else any framing sheet that lines up).
        cands = [f for f in framing if f[0].page_no != m.page_no]
        if lv:
            above = {L + 1 for L in lv}
            pref = [f for f in cands if f[1] & above]
            cands = pref or cands
        best = None
        for f in cands:
            reg = _register(walls, f[2])
            if reg and (best is None or reg[2] > best[1][2]):
                best = (f, reg)
        if best is None or best[1][2] < 0.25:
            continue
        (fm, _flv, J, pitch, _roof), (dx, dy, score) = best
        verdicts = classify(walls, J, pitch, (dx, dy))
        n_lb = n_nlb = 0
        for it, verdict, bear, along in verdicts:
            # What the drawings say outright wins over the framing read.
            if it.get("role") in _KEEP_ROLES:
                continue
            # The user's default types (exterior / demising / other) only
            # stand in until the framing says (OE-DELIVERY 2026-11-11-div5-rules).
            default_note = it.get("role_default")
            spec_now = str(it.get("spec") or "")
            if default_note:
                spec_now = spec_now.replace("; " + default_note, "").replace(default_note, "")
            if _SAYS_RE.search(spec_now):
                continue
            # Walls read by the house framing rules keep the rules' role.
            if any(k.startswith("rule_") and it.get(k) is not None for k in it):
                continue
            if default_note:
                it["spec"] = spec_now
                it.pop("role_default", None)
                prof = str(it.get("profile") or "")
                if verdict == "Load Bearing Wall" and prof.startswith("362S"):
                    it["profile"] = "600S162-54"
                elif verdict != "Load Bearing Wall" and prof == "600S162-54":
                    it["profile"] = "362S125-18"
            it["role"] = verdict
            it["bearing_from"] = fm.page_no
            note = (
                f"Load bearing: {bear} joists of the floor above (sheet {fm.page_no}) land on it"
                if verdict == "Load Bearing Wall"
                else f"Non-load bearing: the joists above (sheet {fm.page_no}) run alongside it"
            )
            it["spec"] = f"{it.get('spec') or ''}; {note}".lstrip("; ")
            if verdict == "Load Bearing Wall":
                n_lb += 1
            else:
                n_nlb += 1
        summary[str(res.get("page"))] = {"framing_sheet": fm.page_no, "fit": round(score, 2), "load_bearing": n_lb, "non_load_bearing": n_nlb}
        res.setdefault("bearing", summary[str(res.get("page"))])
    return summary


def framing_sources(pdf, models: list[Any], build, limit: int = 6) -> list[Any]:
    """Framing sheets of the set that are not being taken off but tell which
    walls bear: read when a wall sheet is in the run."""
    if not any(WALL_PAGE_RE.search(title_text(m)) for m in models):
        return []
    have = {m.page_no for m in models}
    out = []
    for page_no in range(1, min(len(pdf), 150) + 1):
        if page_no in have:
            continue
        try:
            text = " ".join(pdf[page_no - 1].get_text().upper().split())
        except Exception:
            continue
        if not FRAMING_PAGE_RE.search(text) or not re.search(r"\bJOISTS?\b|\bTRUSS(?:ES)?\b", text):
            continue
        try:
            m = build(pdf[page_no - 1], page_no)
        except Exception:
            continue
        if FRAMING_PAGE_RE.search(title_text(m)):
            m.framing_source = True
            out.append(m)
        if len(out) >= limit:
            break
    return out
