

# ── scale from dimensions, legend walls (OE-DELIVERY 2026-11-10-legend-walls) ──
#
# Drawings come in every style. When a sheet prints no scale, the scale is
# read the way an estimator checks one: a dimension string ("11'-3 1/2"")
# against the length of the dimension line it sits on - the ratio most of
# the dimensions agree on is the scale. When walls carry no tags, the
# legend says what each wall looks like (a coloured or hatched sample next
# to its spec): every stretch of the plan drawn the same way is that wall.

_FT_IN_RE = re.compile(
    r"^(\d{1,3})\s*['’]\s*-?\s*(\d{1,2})?(?:\s+(\d{1,2})/(\d{1,2}))?\s*(?:(\d{1,2})/(\d{1,2}))?\s*[\"”″]?$"
)
_VULGAR = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875}


def parse_ft_in(text: str) -> float | None:
    """Feet of a dimension string: 11'-3 1/2", 96'-3½", 12' - 8 1/2"."""
    t = (text or "").strip()
    extra = 0.0
    for k, v in _VULGAR.items():
        if k in t:
            extra += v
            t = t.replace(k, "")
    m = _FT_IN_RE.match(t.strip())
    if not m:
        return None
    ft = int(m.group(1))
    inch = float(m.group(2) or 0)
    if m.group(3):
        inch += int(m.group(3)) / max(1, int(m.group(4)))
    elif m.group(5):
        inch += int(m.group(5)) / max(1, int(m.group(6)))
    v = ft + (inch + extra) / 12.0
    return v if v >= 1.0 else None


# Standard architectural scales, units (pt) per foot.
_STD_SCALES = [
    ('3" = 1\'-0"', 216.0), ('1 1/2" = 1\'-0"', 108.0), ('1" = 1\'-0"', 72.0), ('3/4" = 1\'-0"', 54.0),
    ('1/2" = 1\'-0"', 36.0), ('3/8" = 1\'-0"', 27.0), ('1/4" = 1\'-0"', 18.0), ('3/16" = 1\'-0"', 13.5),
    ('1/8" = 1\'-0"', 9.0), ('3/32" = 1\'-0"', 6.75), ('1/16" = 1\'-0"', 4.5),
]


def dimension_scale(
    text_lines: list[tuple[str, tuple[float, float, float, float], tuple[float, float], Any]],
    segs: list[tuple],
    known_upf: float | None = None,
) -> tuple[float | None, str | None, tuple[float, float, float, float] | None]:
    """(units per foot, scale text, plan region) from the dimension strings.

    Each feet-inch string is paired with the line it is written along (text
    centre near the line's middle); length / feet is that dimension's vote.
    The scale is the value most votes agree on (within 3%); the region is the
    extent of the agreeing dimensions - the plan they measure (dimensions of a
    legend elevation drawn at another scale do not agree and stay out)."""
    votes: list[tuple[float, tuple[float, float, float, float]]] = []
    longs = [s for s in segs if s[4] >= 12.0]
    for text, bb, d, _pen_ in text_lines:
        v = parse_ft_in(text)
        if v is None or v > 600:
            continue
        dx, dy = d
        x0, y0, x1, y1 = bb
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        h = max(4.0, min(x1 - x0, y1 - y0))
        best = None
        for s in longs:
            if not (min(s[0], s[2]) - 4 * h <= cx <= max(s[0], s[2]) + 4 * h and min(s[1], s[3]) - 4 * h <= cy <= max(s[1], s[3]) + 4 * h):
                continue
            ux, uy = (s[2] - s[0]) / s[4], (s[3] - s[1]) / s[4]
            if abs(ux * dx + uy * dy) < 0.995:
                continue
            px, py = cx - s[0], cy - s[1]
            t = px * ux + py * uy
            dist = abs(-px * uy + py * ux)
            if dist > 2.5 * h or abs(t - s[4] / 2.0) > 0.35 * s[4] + 4.0:
                continue
            if best is None or dist < best[0]:
                best = (dist, s[4], (min(s[0], s[2]), min(s[1], s[3]), max(s[0], s[2]), max(s[1], s[3])))
        if best is not None:
            votes.append((best[1] / v, best[2]))
    if not votes:
        return None, None, None
    if known_upf:
        upf = known_upf
    else:
        best_n, upf = 0, None
        for r, _bb in votes:
            n = sum(1 for q, _ in votes if abs(q - r) <= 0.03 * r)
            if n > best_n:
                best_n, upf = n, r
        if upf is None or best_n < 5 or best_n < 0.3 * len(votes):
            return None, None, None
        agree = [q for q, _ in votes if abs(q - upf) <= 0.03 * upf]
        agree.sort()
        upf = agree[len(agree) // 2]
    agree_bb = [bb for q, bb in votes if abs(q - upf) <= 0.03 * upf]
    region = None
    if len(agree_bb) >= 4:
        region = (
            min(b[0] for b in agree_bb) - 2.0 * upf,
            min(b[1] for b in agree_bb) - 2.0 * upf,
            max(b[2] for b in agree_bb) + 2.0 * upf,
            max(b[3] for b in agree_bb) + 2.0 * upf,
        )
    if known_upf:
        return known_upf, None, region
    name = None
    for nm, val in _STD_SCALES:
        if abs(val - upf) <= 0.02 * val:
            name = nm
            break
    text = name or f"{upf / 72.0 * 12.0:.3g}\" = 1'-0\" (as printed)"
    return upf, f"{text} - read from the dimensions", region


def tick_runs(ds: DetailSheet, upf: float, region: tuple[float, float, float, float] | None = None) -> list[dict[str, Any]]:
    """Rows of short, evenly spaced strokes of one pen - the stud / hatch
    pattern a wall is drawn with. Ticks across the wall or slanted (hatch)
    both count; the row's centre line is the wall's, the ticks' reach across
    it the wall's width."""
    lo_w, hi_w = 2.0 / 12.0 * upf, 18.0 / 12.0 * upf
    ticks = [
        s for s in ds.segs
        if s[6] is not None and lo_w <= s[4] <= hi_w
        and (region is None or (region[0] <= (s[0] + s[2]) / 2 <= region[2] and region[1] <= (s[1] + s[3]) / 2 <= region[3]))
    ]
    used: set[int] = set()
    runs: list[dict[str, Any]] = []
    # Candidate wall directions: horizontal, vertical, and across the tick.
    groups: dict[tuple, list[int]] = {}
    for i, s in enumerate(ticks):
        mx, my = (s[0] + s[2]) / 2.0, (s[1] + s[3]) / 2.0
        ta = math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) % 180.0
        for wa in {0.0, 90.0, round((ta + 90.0) % 180.0)}:
            if _adiff(wa, ta) < 25.0:
                continue  # a stroke along the wall is a face, not a tick
            r = math.radians(wa)
            ex, ey = math.cos(r), math.sin(r)
            off = -mx * ey + my * ex
            across = abs(math.sin(math.radians(ta - wa))) * s[4]
            groups.setdefault((s[6], wa, round(off / 1.0), round(across / 1.0), round(ta)), []).append(i)
    order = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    for (pen, wa, _o, _w, _ta), idx in order:
        idx = [i for i in idx if i not in used]
        if len(idx) < 5:
            continue
        r = math.radians(wa)
        ex, ey = math.cos(r), math.sin(r)
        pts = []
        for i in idx:
            s = ticks[i]
            mx, my = (s[0] + s[2]) / 2.0, (s[1] + s[3]) / 2.0
            pts.append((mx * ex + my * ey, -mx * ey + my * ex, i))
        pts.sort()
        # Split at gaps far above the row's own spacing.
        gaps = [b[0] - a[0] for a, b in zip(pts, pts[1:]) if b[0] - a[0] > 0.3]
        if not gaps:
            continue
        sp = sorted(gaps)[len(gaps) // 2]
        if sp > 1.5 * upf or sp < 0.8:
            continue
        cur = [pts[0]]
        chunks = []
        for a, b in zip(pts, pts[1:]):
            if b[0] - a[0] > 3.0 * sp:
                chunks.append(cur)
                cur = []
            cur.append(b)
        chunks.append(cur)
        for ch in chunks:
            if len(ch) < 5 or ch[-1][0] - ch[0][0] < 1.5 * upf:
                continue
            for q in ch:
                used.add(q[2])
            off = sum(q[1] for q in ch) / len(ch)
            t0, t1 = ch[0][0] - sp / 2.0, ch[-1][0] + sp / 2.0
            s0 = ticks[ch[0][2]]
            ta = math.degrees(math.atan2(s0[3] - s0[1], s0[2] - s0[0]))
            width = abs(math.sin(math.radians(ta - wa))) * s0[4]
            a = (ex * t0 - ey * off, ey * t0 + ex * off)
            b = (ex * t1 - ey * off, ey * t1 + ex * off)
            runs.append({
                "pen": pen, "ang": wa, "off": off, "t0": t0, "t1": t1, "width": width,
                "spacing": sp, "n": len(ch), "a": a, "b": b,
                "bbox": (min(a[0], b[0]) - width, min(a[1], b[1]) - width, max(a[0], b[0]) + width, max(a[1], b[1]) + width),
            })
    return runs


_WALL_TXT_RE = re.compile(r"\bWALLS?\b|\b\d{3,4}[STU]\d{3}\b", re.IGNORECASE)
_PEN_NAMES = [
    ((0, 0, 20), "BLUE"), ((0, 20, 0), "GREEN"), ((20, 0, 20), "MAGENTA"), ((20, 10, 0), "ORANGE"),
    ((0, 20, 20), "CYAN"), ((20, 0, 0), "RED"), ((20, 20, 0), "YELLOW"), ((0, 0, 0), "BLACK"),
    ((10, 10, 10), "GREY"), ((10, 0, 10), "PURPLE"), ((0, 10, 0), "DARK GREEN"), ((0, 0, 10), "NAVY"),
    ((16, 8, 3), "BROWN"), ((20, 15, 10), "TAN"), ((10, 15, 20), "LIGHT BLUE"), ((10, 20, 10), "LIGHT GREEN"),
]


def pen_name(pen) -> str:
    if pen is None:
        return "BLACK"
    return min(_PEN_NAMES, key=lambda pn: sum((a - b) ** 2 for a, b in zip(pn[0], pen)))[1]


def _bb_gap(a, b) -> float:
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def legend_wall_types(
    text_lines: list[tuple[str, tuple[float, float, float, float], tuple[float, float], Any]],
    runs: list[dict[str, Any]],
    upf: float,
) -> list[dict[str, Any]]:
    """Wall types the legend defines: a block of text naming a wall (WALL /
    a stud size) with a sample pattern beside it, or the text itself in the
    wall's colour. Returns {pen, text, bbox, sample} per type."""
    # Blocks: consecutive lines of one colour, one under the other.
    rows = sorted(
        [(t, bb, pen) for t, bb, d, pen in text_lines if abs(d[0]) > 0.9 and t.strip()],
        key=lambda r: (r[1][1], r[1][0]),
    )
    blocks: list[dict[str, Any]] = []
    for t, bb, pen in rows:
        h = bb[3] - bb[1]
        for blk in blocks:
            last = blk["last"]
            if blk["pen"] == pen and 0 <= bb[1] - last[3] <= 1.2 * h and abs(bb[0] - blk["bbox"][0]) <= 3.0 * h:
                blk["lines"].append(t)
                blk["last"] = bb
                x0, y0, x1, y1 = blk["bbox"]
                blk["bbox"] = (min(x0, bb[0]), min(y0, bb[1]), max(x1, bb[2]), max(y1, bb[3]))
                break
        else:
            blocks.append({"pen": pen, "lines": [t], "bbox": bb, "last": bb})
    types: list[dict[str, Any]] = []
    for blk in blocks:
        text = " ".join(blk["lines"])
        if not _WALL_TXT_RE.search(text) or len(text) > 600:
            continue
        bb = blk["bbox"]
        h = blk["last"][3] - blk["last"][1]
        # A sample: a short tick row right beside the text.
        near = [r for r in runs if _bb_gap(r["bbox"], bb) <= max(4.0 * h, 1.0 * upf) and (r["t1"] - r["t0"]) <= max(bb[2] - bb[0], 30 * h) * 1.3]
        coloured = blk["pen"] is not None and max(blk["pen"]) - min(blk["pen"]) >= 8
        pen = None
        sample = None
        if near:
            sample = min(near, key=lambda r: _bb_gap(r["bbox"], bb))
            pen = sample["pen"]
        elif coloured:
            pen = blk["pen"]
        if pen is None or any(t["pen"] == pen for t in types):
            continue
        types.append({"pen": pen, "text": text, "bbox": bb, "sample": sample})
    return types


def legend_walls(
    model,
    ds: DetailSheet,
    text_lines: list[tuple[str, tuple[float, float, float, float], tuple[float, float], Any]],
    region: tuple[float, float, float, float] | None,
) -> list[dict[str, Any]]:
    """Walls drawn like a legend sample: per type, every tick row of its pen
    on the plan, joined along one line (an opening between two stretches of
    the same wall is a header area). Returns {type, a, b, width, openings}."""
    upf = model.units_per_foot or 0.0
    if not upf or not text_lines:
        return []
    runs = tick_runs(ds, upf)
    types = legend_wall_types(text_lines, runs, upf)
    if not types:
        return []
    legend_boxes = [t["bbox"] for t in types] + [t["sample"]["bbox"] for t in types if t.get("sample")]
    out: list[dict[str, Any]] = []
    for ty in types:
        mine = []
        for r in runs:
            if r["pen"] != ty["pen"] or r is ty.get("sample"):
                continue
            cx, cy = (r["a"][0] + r["b"][0]) / 2.0, (r["a"][1] + r["b"][1]) / 2.0
            if region is not None and not (region[0] <= cx <= region[2] and region[1] <= cy <= region[3]):
                continue
            if any(_bb_gap(r["bbox"], lb) <= 1.0 * upf for lb in legend_boxes):
                continue
            if r["width"] < 2.0 / 12.0 * upf:
                continue
            mine.append(r)
        # Join stretches of one line: gaps up to 2 ft close, up to 16 ft are openings.
        mine.sort(key=lambda r: (round(r["ang"]), round(r["off"] / 2.0), r["t0"]))
        lines: list[list[dict[str, Any]]] = []
        for r in mine:
            if lines:
                L = lines[-1]
                q = L[-1]
                if round(q["ang"]) == round(r["ang"]) and abs(q["off"] - r["off"]) <= 2.0 and r["t0"] - q["t1"] <= 16.0 * upf:
                    L.append(r)
                    continue
            lines.append([r])
        for L in lines:
            t0 = min(r["t0"] for r in L)
            t1 = max(r["t1"] for r in L)
            if t1 - t0 < 2.0 * upf:
                continue
            ang = math.radians(L[0]["ang"])
            ex, ey = math.cos(ang), math.sin(ang)
            off = sum(r["off"] * (r["t1"] - r["t0"]) for r in L) / sum(r["t1"] - r["t0"] for r in L)
            widths = sorted(r["width"] for r in L)
            width = widths[len(widths) // 2]
            openings = []
            for p, q in zip(L, L[1:]):
                g0, g1 = p["t1"], q["t0"]
                if g1 - g0 >= 2.0 * upf:
                    openings.append((g0 - t0, g1 - t0))
            a = (ex * t0 - ey * off, ey * t0 + ex * off)
            b = (ex * t1 - ey * off, ey * t1 + ex * off)
            out.append({"type": ty, "a": a, "b": b, "width": width, "openings": openings, "length": t1 - t0})
    return out
