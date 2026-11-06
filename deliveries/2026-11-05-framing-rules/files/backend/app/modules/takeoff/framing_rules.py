# OE-DELIVERY: 2026-11-04-framing-rules
"""Framing-set takeoff rules (CFS + hot-rolled steel building sets).

Written from the StudioRes PCB structural set (STRL Engineering) and kept as
the house rules for every similar project:

* **Sheet kinds** - read from the sheet title:
    - ``N FLOOR FRAMING PLAN`` / ``ROOF FRAMING PLAN``  -> *framing*: floor
      framing only - trusses and joists framed one by one at their schedule
      spacing, steel W beams, CFS beams (B-x) and the deck (diaphragm) areas.
      Walls and headers are NOT taken here (they repeat the wall plan).
    - ``N FLOOR SHEAR WALL PLAN`` -> *walls*: wall types (W1..), headers
      (H1..), shear walls (SW-x), strap braced walls (BR-x), holdowns (HD) and
      steel braces (BRACE-X). Level-based schedules use the row
      ``Nth TO (N+1)th`` (the 1st floor plan uses "1ST TO 2ND"; the top floor
      uses "4TH TO ROOF" / "4TH TO 5TH").
    - ``FOUNDATION PLAN`` -> columns (HSS / W at the column symbols) and base
      plates (BP-x). Footings are NOT taken.
    - anything else (details, sections, schedules, notes) is not taken off.
* **Schedules** - read as tables (PyMuPDF ``find_tables``): wall framing
  (per level: framing, spacing, height), header (per level: framing, jack and
  king studs), CFMF truss / joist / beam (framing, spacing, length), shear
  wall and X-brace wall (per level: chord studs, holdowns, bracing), base
  plate and diaphragm schedules.

Pure helpers + one entry point (:func:`apply_framing_rules`) used by
``auto_takeoff.run_models``.
"""
from __future__ import annotations

import re
from typing import Any

ORDINALS = {"1ST": 1, "2ND": 2, "3RD": 3, "4TH": 4, "5TH": 5, "6TH": 6, "7TH": 7, "8TH": 8, "9TH": 9, "10TH": 10}
ORD_NAME = {1: "1ST", 2: "2ND", 3: "3RD", 4: "4TH", 5: "5TH", 6: "6TH", 7: "7TH", 8: "8TH", 9: "9TH", 10: "10TH"}

_TITLE_RE = re.compile(
    r"\b(?P<lvl>\d{1,2}(?:ST|ND|RD|TH)|GROUND|FIRST|SECOND|THIRD|FOURTH|FIFTH|ROOF)?\s*(?:FLOOR\s+|LEVEL\s+)?"
    r"(?P<kind>SHEAR\s*WALL\s+PLAN|FRAMING\s+PLAN|FOUNDATION\s+PLAN|WALL\s+PLAN)\b",
    re.IGNORECASE,
)
_WORD_LEVEL = {"GROUND": 1, "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5}


def norm_tag(tag: str) -> str:
    """'H-1' / 'H1' / 'h 1' -> 'H1' (schedules and plans write tags differently)."""
    return re.sub(r"[\s\-_.]+", "", (tag or "").upper())


def level_of(text: str) -> int | None:
    """Lower level of a schedule row: '1ST TO 2ND' -> 1, '4TH TO ROOF (2)' -> 4."""
    m = re.search(r"(\d{1,2})\s*(?:ST|ND|RD|TH)\b", (text or "").upper())
    return int(m.group(1)) if m else None


def sheet_kind(titles: list[str]) -> tuple[str | None, int | None]:
    """('framing' | 'roof' | 'walls' | 'foundation' | None, level) from the
    large title texts of a sheet. A framing plan's level is the floor it
    frames (2ND FLOOR FRAMING PLAN -> 2); a wall plan's level is the floor
    the walls stand on (1ST FLOOR SHEAR WALL PLAN -> 1)."""
    best: tuple[str | None, int | None] = (None, None)
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
            continue
        kind_txt = m.group("kind")
        lvl_txt = (m.group("lvl") or "").upper()
        lvl: int | None = None
        if lvl_txt in _WORD_LEVEL:
            lvl = _WORD_LEVEL[lvl_txt]
        elif lvl_txt and lvl_txt != "ROOF":
            lvl = level_of(lvl_txt)
        if "FOUNDATION" in kind_txt:
            return ("foundation", 0)
        if "WALL" in kind_txt:
            if lvl is None:
                wall_nolevel = True
                continue
            return ("walls", lvl)
        if "FRAMING" in kind_txt:
            if lvl_txt == "ROOF":
                best = ("roof", None)
            else:
                best = ("framing", lvl)
    if best[0] is None and wall_nolevel:
        return ("walls", 1)
    return best


def title_block_title(page) -> str:
    """The sheet title written in the title block (the strip along the right
    or bottom edge, next to the sheet number) - e.g. 'FRAMING PLAN',
    'WALL PLAN', 'DETAILS'. Empty when the sheet has no such strip."""
    try:
        d = page.get_text("dict")
    except Exception:
        return ""
    W, H = float(page.rect.width), float(page.rect.height)
    parts: list[tuple[float, float, str]] = []
    for b in d.get("blocks", []):
        for ln in b.get("lines", []):
            spans = ln.get("spans") or []
            if not spans:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            sz = max(s.get("size", 0) for s in spans)
            if sz < 14 or x0 < 0.9 * W or y0 < 0.75 * H:
                continue
            text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if re.fullmatch(r"[A-Z]{1,2}-?\d{3}(\.\d+)?", text):
                continue
            parts.append((y0, x0, text))
    parts.sort()
    return " ".join(p[2] for p in parts)


def page_kind(page) -> tuple[str | None, int | None, list[str]]:
    """(kind, level, titles) of one sheet. The title block decides whether it
    is a plan at all (so a detail sheet with a small 'FOUNDATION PLAN' detail
    is not one); the drawing title gives the level."""
    titles = page_titles(page)
    tb = " ".join(title_block_title(page).upper().split())
    if not tb:
        kind, level = sheet_kind(titles)
        return kind, level, titles
    m = _TB_PLAN_RE.fullmatch(tb)
    if not m:
        return None, None, titles
    if m.group("found"):
        return "foundation", 0, titles
    kind, level = sheet_kind([tb + (" PLAN" if not tb.endswith("PLAN") else "")])
    if kind and level is None and kind != "roof":
        k2, l2 = sheet_kind(titles)
        if k2 == kind:
            level = l2
    return kind, level, titles


_TB_PLAN_RE = re.compile(
    r"(?:(?:\d{1,2}(?:ST|ND|RD|TH)|GROUND|FIRST|SECOND|THIRD|FOURTH|FIFTH|ROOF)\s+)?(?:FLOOR\s+|LEVEL\s+)?"
    r"(?:(?P<found>FOUNDATION(?:\s+PLAN)?)|FRAMING(?:\s+PLAN)?|SHEAR\s*WALL(?:\s+PLAN)?|WALL\s+PLAN)"
)


_SCHED_TITLE_RE = re.compile(r"SCHEDULE")
_SCHED_NOT_TITLE = re.compile(r"\b(SEE|REF\.?|PER|REFER|&|AND|SCHEDULED)\b")


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


_SCHED_CACHE: dict[tuple[str, int, int], dict[str, Any]] = {}


def document_schedules(pdf: Any, path: str | None) -> dict[str, Any]:
    """All schedules of a drawing set, read once per file (about 2 s for a
    sheet with schedules) and kept for later runs. A sheet that only repeats
    schedules already read is skipped; its table outlines are in ``rects``
    only when it matches the read sheet's layout (otherwise see
    :func:`page_schedule_rects`).

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
    done_titles: set[str] = set()
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
                if twin is not None and twin in rects:
                    rects[i] = list(rects[twin])
                continue
            sc, rc = read_schedules_fast(page)
        except Exception:
            continue
        read_pages.append((spots, i))
        done_titles |= titles
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


# ── schedules ─────────────────────────────────────────────────────────


def _clean(c: Any) -> str:
    return " ".join(str(c or "").split())


def _col(header: list[str], *names: str) -> int | None:
    for i, h in enumerate(header):
        hu = h.upper()
        if any(n in hu for n in names):
            return i
    return None


def parse_schedule_table(title: str, rows: list[list[str]]) -> dict[str, Any] | None:
    """One schedule table -> {'kind', 'tag' or rows by tag}.

    Returns ``{"kind": k, "entries": {TAG: {...} or {level: {...}}}}``.
    """
    t = " ".join(title.upper().split())
    rows = [[_clean(c) for c in r] for r in rows if any(_clean(c) for c in r)]
    if not rows:
        return None
    # header row = first row naming DESIGNATION / LEVEL / LOCATION / MARK
    hi = next((i for i, r in enumerate(rows) if any(re.search(r"DESIGNATION|^LEVEL$|LOCATION|^MARK$", c.upper()) for c in r)), None)
    if hi is None:
        return None
    header = rows[hi]
    body = rows[hi + 1:]
    out: dict[str, Any] = {}

    m_wall = re.search(r"\b(W\s*-?\s*\d+[A-Z]?)\s*-\s*WALL\s+FRAMING\s+SCHEDULE", t)
    m_sw = re.search(r"SHEAR\s+WALL\s+SCHEDULE\s*-\s*([A-Z]+-?\d+)", t)
    m_br = re.search(r"BRACE\s+WALL\s+SCHEDULE\s*-\s*([A-Z]+-?\d+)", t)
    if m_wall or m_sw or m_br:
        tag = norm_tag((m_wall or m_sw or m_br).group(1))
        kind = "wall" if m_wall else ("shear_wall" if m_sw else "brace_wall")
        c_lvl = _col(header, "LEVEL", "LOCATION")
        c_fr = _col(header, "FRAMING")
        c_sp = _col(header, "SPACING")
        c_ht = _col(header, "HEIGHT")
        c_chord = _col(header, "CHORD")
        c_hd = _col(header, "HOLDOWN")
        c_br = _col(header, "BRACING", "SHEATHING")
        levels: dict[int, dict[str, str]] = {}
        for r in body:
            lv = level_of(r[c_lvl]) if c_lvl is not None and c_lvl < len(r) else None
            if lv is None:
                continue
            g = lambda c: r[c] if c is not None and c < len(r) else ""  # noqa: E731
            levels[lv] = {
                "framing": g(c_fr), "spacing": g(c_sp), "height": g(c_ht),
                "chord": g(c_chord), "holdown": g(c_hd), "bracing": g(c_br), "level": g(c_lvl),
            }
        if levels:
            out = {"kind": kind, "entries": {tag: {"levels": levels}}}
        return out or None

    if "HEADER SCHEDULE" in t:
        c_d = _col(header, "DESIGNATION")
        c_fr = _col(header, "FRAMING")
        c_lv = _col(header, "LEVEL")
        c_j = _col(header, "JACK")
        c_k = _col(header, "KING")
        entries: dict[str, Any] = {}
        cur = None
        cur_fr = ""
        for r in body:
            g = lambda c: r[c] if c is not None and c < len(r) else ""  # noqa: E731
            if g(c_d):
                cur = norm_tag(g(c_d))
                cur_fr = ""
            if not cur:
                continue
            if g(c_fr):
                cur_fr = g(c_fr)
            lv = level_of(g(c_lv))
            if lv is None:
                continue
            entries.setdefault(cur, {"levels": {}})["levels"][lv] = {
                "framing": cur_fr, "jack": g(c_j), "king": g(c_k), "level": g(c_lv),
            }
        return {"kind": "header", "entries": entries} if entries else None

    kind = None
    if "TRUSS SCHEDULE" in t:
        kind = "truss"
    elif "JOIST SCHEDULE" in t:
        kind = "joist"
    elif "BEAM SCHEDULE" in t:
        kind = "cfs_beam"
    elif "BASE PLATE SCHEDULE" in t:
        kind = "base_plate"
    elif "DIAPHRAGM SCHEDULE" in t:
        kind = "diaphragm"
    if kind is None:
        return None
    c_d = _col(header, "DESIGNATION", "MARK")
    if c_d is None:
        return None
    entries = {}
    for r in body:
        if c_d >= len(r) or not r[c_d]:
            continue
        rec = {header[i].upper(): r[i] for i in range(min(len(header), len(r))) if header[i]}
        tag = norm_tag(r[c_d])
        if kind == "diaphragm":
            tag = norm_tag(re.sub(r"[^A-Z0-9-].*$", "", r[c_d].upper().split()[-1] if r[c_d] else "")) or "D1"
        entries[tag] = {
            "framing": next((v for k, v in rec.items() if "FRAMING" in k or "COLUMN" in k or "SHEATHING" in k), ""),
            "spacing": next((v for k, v in rec.items() if "SPACING" in k and "CONN" not in k), ""),
            "length": next((v for k, v in rec.items() if "LENGTH" in k), ""),
            "height": next((v for k, v in rec.items() if "HEIGHT" in k), ""),
            "raw": rec,
        }
    return {"kind": kind, "entries": entries} if entries else None


def read_schedules(page) -> tuple[dict[str, dict[str, Any]], list[tuple[float, float, float, float]]]:
    """All schedule tables on one PyMuPDF page -> ({kind: {TAG: entry}}, table rects)."""
    out: dict[str, dict[str, Any]] = {}
    rects: list[tuple[float, float, float, float]] = []
    try:
        tabs = page.find_tables()
    except Exception:
        return out, rects
    W, H = float(page.rect.width), float(page.rect.height)
    for tb in tabs.tables:
        x0, y0, x1, y1 = tb.bbox
        if (x1 - x0) > 0.6 * W and (y1 - y0) > 0.6 * H:
            continue  # the sheet border / title block frame
        try:
            rows = tb.extract()
        except Exception:
            continue
        if not rows:
            continue
        title = " ".join(_clean(c) for c in rows[0] if _clean(c))
        if "SCHEDULE" not in title.upper():
            # title printed just above the table frame
            import pymupdf

            above = page.get_text("text", clip=pymupdf.Rect(x0, max(0.0, y0 - 28), x1, y0 + 1))
            title = " ".join(above.split()) + " " + title
        parsed = parse_schedule_table(title, rows)
        if not parsed:
            continue
        rects.append((x0, y0, x1, y1))
        bucket = out.setdefault(parsed["kind"], {})
        for tag, entry in parsed["entries"].items():
            if tag in bucket and "levels" in entry and "levels" in bucket[tag]:
                bucket[tag]["levels"].update(entry["levels"])
            else:
                bucket.setdefault(tag, entry)
    return out, rects


def merge_schedules(parts: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in parts:
        for kind, entries in p.items():
            b = out.setdefault(kind, {})
            for tag, e in entries.items():
                if tag in b and "levels" in e and "levels" in b[tag]:
                    for lv, row in e["levels"].items():
                        b[tag]["levels"].setdefault(lv, row)
                else:
                    b.setdefault(tag, e)
    return out


def level_row(entry: dict[str, Any] | None, level: int | None) -> dict[str, str] | None:
    """The schedule row for a wall plan level (rows are keyed by their lower level)."""
    if not entry or "levels" not in entry or level is None:
        return None
    levels = entry["levels"]
    if level in levels:
        return levels[level]
    # top floor written as "4TH TO ROOF" when the plan says ROOF etc.
    lower = [lv for lv in levels if lv <= level]
    return levels[max(lower)] if lower else None


def feet_inches(text: str) -> float | None:
    """"9'-7 1/4\"" -> feet."""
    t = (text or "").replace("''", '"').replace("’", "'")
    m = re.search(r"(\d+)\s*'\s*-?\s*(\d+)?(?:\s+(\d+)/(\d+))?", t)
    if not m:
        return None
    ft = float(m.group(1))
    inch = float(m.group(2) or 0)
    if m.group(3):
        inch += float(m.group(3)) / float(m.group(4))
    return ft + inch / 12.0


def spacing_in(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", text or "")
    v = float(m.group(1)) if m else None
    return v if v and 4 <= v <= 96 else None


# ── page titles + fast schedule reading ───────────────────────────────


def page_titles(page, min_size: float = 12.0) -> list[str]:
    """Whole lines of large text (sheet / drawing titles), spans joined."""
    out: list[str] = []
    try:
        d = page.get_text("dict")
    except Exception:
        return out
    for b in d.get("blocks", []):
        for ln in b.get("lines", []):
            spans = ln.get("spans") or []
            if not spans or max(s.get("size", 0) for s in spans) < min_size:
                continue
            text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if 4 <= len(text) <= 80 and "NOTES" not in text.upper():
                out.append(text)
    return out


def read_schedules_fast(page) -> tuple[dict[str, dict[str, Any]], list[tuple[float, float, float, float]]]:
    """:func:`read_schedules` limited to the areas around each 'SCHEDULE'
    title, so a dense plan sheet does not cost seconds."""
    import pymupdf

    hits = [r for _t, r in schedule_titles(page)]
    if not hits:
        return {}, []
    W, H = float(page.rect.width), float(page.rect.height)
    clips: list[Any] = []
    for h in hits:
        c = pymupdf.Rect(max(0, h.x0 - 520), max(0, h.y0 - 40), min(W, h.x1 + 900), min(H, h.y0 + 760))
        merged = False
        for i, o in enumerate(clips):
            if o.intersects(c):
                clips[i] = o | c
                merged = True
                break
        if not merged:
            clips.append(c)
    out: dict[str, dict[str, Any]] = {}
    rects: list[tuple[float, float, float, float]] = []
    seen: set[tuple[int, int]] = set()
    for c in clips:
        try:
            tabs = page.find_tables(clip=c)
        except Exception:
            continue
        for tb in tabs.tables:
            x0, y0, x1, y1 = tb.bbox
            key = (int(x0 // 4), int(y0 // 4))
            if key in seen:
                continue
            seen.add(key)
            try:
                rows = tb.extract()
            except Exception:
                continue
            if not rows:
                continue
            title = " ".join(_clean(x) for x in rows[0] if _clean(x))
            if "SCHEDULE" not in title.upper():
                above = page.get_text("text", clip=pymupdf.Rect(x0, max(0.0, y0 - 28), x1, y0 + 1))
                title = " ".join(above.split()) + " " + title
            parsed = parse_schedule_table(title, rows)
            if not parsed:
                continue
            rects.append((x0, y0, x1, y1))
            for tag, entry in parsed["entries"].items():
                bucket = out.setdefault(parsed["kind"], {})
                if tag in bucket and "levels" in entry and "levels" in bucket[tag]:
                    bucket[tag]["levels"].update(entry["levels"])
                else:
                    bucket.setdefault(tag, entry)
    return out, rects


# ── rules per sheet kind ──────────────────────────────────────────────

ALLOWED = {
    "framing": {"beams", "joists", "trusses", "areas", "other"},
    "roof": {"beams", "joists", "trusses", "areas", "other"},
    "walls": {"walls", "other"},
    "foundation": {"columns", "other"},
}

_SSMA_ONLY = re.compile(r"^\(?\d\)?-?\d{3,4}[STUF]\d{3}-\d{2,3}|^\d{3,4}[STUF]\d{3}-\d{2,3}")
_AISC_ONLY = re.compile(r"^(W\d+X[\d.]+|HSS[\dX./]+|WT\d+X[\d.]+|C\d+X[\d.]+|L\d[\dX/-]+)$")


def _sched_entry(fs: dict[str, Any], kind: str, tag: str) -> dict[str, Any] | None:
    return (fs.get(kind) or {}).get(norm_tag(tag))


def rule_classify(text: str, rules: tuple[str, int | None, dict[str, Any]]) -> dict[str, Any] | str | None:
    """Rule classification of one plan label, or 'skip', or None (use the
    normal classifier)."""
    kind, level, fs = rules
    toks = (text or "").upper().split()
    if len(toks) == 2:
        # Stacked tags read as one label: 'SW-1 W3' = shear wall SW-1 built
        # as wall type W3; 'RJ-1 W1' = joist tag beside a wall tag.
        first = rule_classify(toks[0], rules)
        if isinstance(first, dict):
            second = toks[1]
            if kind == "walls" and first.get("category") == "walls" and re.fullmatch(r"W\d{1,2}[A-Z]?", second):
                row = level_row(_sched_entry(fs, "wall", second), level)
                first["wall_type"] = second
                if row:
                    extra = f"wall {second}: {row['framing']} @ {row['spacing']}\" O.C., {row['height']} high"
                    first["spec"] = f"{first['spec']}; {extra}" if first.get("spec") else extra
                    first["rule_height"] = row.get("height")
            return first
    t = re.sub(r"\s+", "", (text or "").upper())
    if not t:
        return None
    if kind in ("framing", "roof"):
        m = re.fullmatch(r"(RT|T)-?(\d{1,2})", t)
        if m:
            tag = f"{m.group(1)}-{m.group(2)}"
            e = _sched_entry(fs, "truss", tag)
            sp = spacing_in(e.get("spacing", "")) if e else None
            return {"category": "trusses", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "length_ft": feet_inches((e or {}).get("length") or ""),
                    "role": "Roof Truss" if m.group(1) == "RT" else "Floor Truss", "rule_profile": (e or {}).get("framing"),
                    "spec": (f"{e['framing']} @ {e['spacing']}\" O.C., {e.get('length') or ''}".strip(", ") if e else None)}
        m = re.fullmatch(r"(RJ|J)-?(\d{1,2})", t)
        if m:
            tag = f"{m.group(1)}-{m.group(2)}"
            e = _sched_entry(fs, "joist", tag)
            sp = spacing_in(e.get("spacing", "")) if e else None
            return {"category": "joists", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "length_ft": feet_inches((e or {}).get("length") or ""),
                    "role": "Roof Joist" if m.group(1) == "RJ" else "CFS Joist", "rule_profile": (e or {}).get("framing"),
                    "spec": (f"{e['framing']} @ {e['spacing']}\" O.C., {e.get('length') or ''}".strip(", ") if e else None)}
        m = re.fullmatch(r"B-?(\d{1,2})", t)
        if m and _sched_entry(fs, "cfs_beam", t):
            e = _sched_entry(fs, "cfs_beam", t)
            return {"category": "beams", "designation": f"B-{m.group(1)}", "spacing_in": None, "series": False, "tag": True,
                    "role": "CFS Beam", "rule_profile": (e or {}).get("framing"), "spec": (e or {}).get("framing")}
        if re.fullmatch(r"W\d{1,2}[A-Z]?|H-?\d{1,2}|HD|SW-?\d+|BR-?\d+|BRACE-?X?\d*", t) or _SSMA_ONLY.match(t):
            return "skip"
        return None
    if kind == "walls":
        if re.fullmatch(r"W\d{1,2}[A-Z]?", t):
            row = level_row(_sched_entry(fs, "wall", t), level)
            spec = f"{row['framing']} @ {row['spacing']}\" O.C., {row['height']} high ({row['level']})" if row else None
            return {"category": "walls", "designation": t, "spacing_in": None, "series": False, "tag": True,
                    "spec": spec, "role": "Load Bearing Wall", "rule_profile": (row or {}).get("framing"),
                    "rule_height": (row or {}).get("height"), "rule_level": (row or {}).get("level"),
                    "rule_spacing": (row or {}).get("spacing")}
        m = re.fullmatch(r"(SW|BR)-?(\d{1,2})", t)
        if m:
            tag = f"{m.group(1)}-{m.group(2)}"
            row = level_row(_sched_entry(fs, "shear_wall" if m.group(1) == "SW" else "brace_wall", tag), level)
            spec = (f"Chord studs {row['chord']}; {row['holdown']}; {row['bracing']} ({row['level']})" if row else None)
            return {"category": "walls", "designation": tag, "spacing_in": None, "series": False, "tag": True, "spec": spec,
                    "role": "Shear Wall" if m.group(1) == "SW" else "Strap Braced Wall",
                    "rule_profile": (row or {}).get("chord"), "rule_level": (row or {}).get("level")}
        m = re.fullmatch(r"H-?(\d{1,2})", t)
        if m:
            tag = f"H{m.group(1)}"
            row = level_row(_sched_entry(fs, "header", tag), level)
            spec = (f"{row['framing']}; jack {row['jack']}; king {row['king']} ({row['level']})" if row else None)
            return {"category": "other", "designation": tag, "spacing_in": None, "series": False, "tag": True, "spec": spec,
                    "role": "Load Bearing Header", "count_role": "Load Bearing Header",
                    "rule_profile": (row or {}).get("framing"), "rule_level": (row or {}).get("level")}
        if t == "HD":
            return {"category": "other", "designation": "HD", "count_role": "Holdown", "role": "Holdown", "tag": True}
        m = re.fullmatch(r"BRACE-?(X?\d{1,2})", t)
        if m:
            return {"category": "other", "designation": f"BRACE-{m.group(1)}", "count_role": "Steel Brace", "role": "Steel Brace", "tag": True}
        if re.fullmatch(r"(RT|T|RJ|J|B)-?\d{1,2}", t) or _AISC_ONLY.match(t) or _SSMA_ONLY.match(t):
            return "skip"
        return None
    if kind == "foundation":
        m = re.fullmatch(r"BP-?(\d{1,2})", t)
        if m:
            e = _sched_entry(fs, "base_plate", t)
            raw = (e or {}).get("raw", {})
            spec = ", ".join(f"{k.title()}: {v}" for k, v in raw.items() if v and k != "MARK") or None
            return {"category": "other", "designation": f"BP-{m.group(1)}", "count_role": "Base Plate", "role": "Base Plate",
                    "tag": True, "spec": spec, "rule_profile": (e or {}).get("framing")}
        if _AISC_ONLY.match(t):
            return {"category": "columns", "designation": t, "spacing_in": None, "series": False}
        if re.fullmatch(r"W?F\d+(\.\d+)?(X\d+)?|SOG-?\d+|SL-?\d+", t):
            return "skip"
        return None
    return None


def post_process(items: list[dict[str, Any]], kind: str, level: int | None, fs: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep what the sheet kind takes off and stamp the schedule data."""
    allowed = ALLOWED.get(kind, set())
    diaphragm = next(iter((fs.get("diaphragm") or {}).items()), None)
    out: list[dict[str, Any]] = []
    for it in items:
        cat = it.get("category")
        if cat not in allowed:
            continue
        role = it.get("role") or ""
        if kind in ("framing", "roof"):
            if cat == "other" and role != "CFS Beam":
                continue
            if cat == "areas":
                sheathing = (diaphragm[1].get("framing") if diaphragm else None) or ""
                it["role"] = "Deck"
                it["designation"] = (diaphragm[0] if diaphragm else "DECK")
                it["profile"] = re.split(r"\s+FASTENED|,|;", sheathing, maxsplit=1)[0].strip() or "Deck"
                it["spec"] = sheathing or it.get("spec")
                it["label"] = it["designation"]
        elif kind == "walls":
            if cat == "other" and role not in ("Load Bearing Header", "Holdown", "Steel Brace"):
                continue
        elif kind == "foundation":
            if cat == "other" and role != "Base Plate":
                continue
            if cat == "columns":
                it["role"] = "Column"
        if it.get("rule_height"):
            ft = feet_inches(it["rule_height"])
            if ft:
                it["height_ft"] = round(ft, 4)
        if it.get("rule_profile"):
            it["profile"] = it["rule_profile"]
        if it.get("rule_level"):
            # '1ST TO 2ND (2)' -> '1ST TO 2ND' (footnote markers)
            it["level"] = re.sub(r"\s*\(.*$", "", str(it["rule_level"])).strip() or it["rule_level"]
        for k in ("rule_profile", "rule_height", "rule_level", "rule_spacing"):
            it.pop(k, None)
        out.append(it)
    return out


def page_schedule_rects(page, known: dict[int, list[tuple[float, float, float, float]]], index: int) -> list[tuple[float, float, float, float]]:
    """Schedule table outlines of one sheet (from the document read, or read
    now for a sheet that was skipped as a repeat)."""
    if index in known:
        return known[index]
    if not schedule_titles(page):
        return []
    try:
        _sc, rc = read_schedules_fast(page)
    except Exception:
        return []
    known[index] = rc
    return rc


_WARMING: set[str] = set()


def warm_schedules(path: str) -> None:
    """Read a drawing set's schedules on a worker thread (cache warm-up)."""
    import os
    import threading

    try:
        st = os.stat(path)
    except OSError:
        return
    if (str(path), int(st.st_size), int(st.st_mtime)) in _SCHED_CACHE or path in _WARMING:
        return
    _WARMING.add(path)

    def _run() -> None:
        try:
            import pymupdf

            pdf = pymupdf.open(path)
            try:
                document_schedules(pdf, path)
            finally:
                pdf.close()
        except Exception:
            pass
        finally:
            _WARMING.discard(path)

    threading.Thread(target=_run, daemon=True, name="schedule-warmup").start()
