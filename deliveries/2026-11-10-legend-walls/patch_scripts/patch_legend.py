from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
SP = Path(r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\732e120e-2b91-4dfc-bda2-2925a51afa1e\scratchpad")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)


p = base / "detail_scan.py"
s = p.read_text(encoding="utf-8")
if "def legend_walls" not in s:
    s += (SP / "legend_part.py").read_text(encoding="utf-8")
p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")
rep('''    # All drawn pieces down to arrowhead size (framing rules only).
    fine: list[Any] = field(default_factory=list)''', '''    # All drawn pieces down to arrowhead size (framing rules only).
    fine: list[Any] = field(default_factory=list)
    # Every text line: (text, bbox, direction, pen) - legend colours; and the
    # plan's extent from its dimensions (OE-DELIVERY 2026-11-10-legend-walls).
    text_lines: list[Any] = field(default_factory=list)
    plan_region: tuple[float, float, float, float] | None = None''')
rep('''    model.schedule_rects = [tuple(r["rect"]) for r in D._schedule_regions(lines)]
    model.index = SegIndex(segments)''', '''    model.schedule_rects = [tuple(r["rect"]) for r in D._schedule_regions(lines)]
    model.index = SegIndex(segments)
    # No scale printed: read it from the dimensions, as an estimator would
    # check one (OE-DELIVERY 2026-11-10-legend-walls).
    try:
        from app.modules.takeoff import detail_scan as Z

        model.text_lines = _text_lines(page)
        d_upf, d_text, region = Z.dimension_scale(model.text_lines, segments, upf)
        model.plan_region = region
        if not upf and d_upf:
            model.units_per_foot = d_upf
            model.scale_text = d_text
    except Exception:
        pass''')
rep('''def _in_rects(x: float, y: float, rects''', '''def _text_lines(page) -> list[tuple[str, tuple[float, float, float, float], tuple[float, float], Any]]:
    """Every text line with its box (display space), writing direction and
    colour pen."""
    import pymupdf

    from app.modules.takeoff import detail_scan as Z

    rot = getattr(page, "rotation", 0)
    mat = page.rotation_matrix if rot else None
    out = []
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        return out
    for b in blocks:
        for ln in b.get("lines", []):
            spans = ln.get("spans") or []
            text = "".join(sp.get("text", "") for sp in spans).strip()
            if not text:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            dx, dy = ln.get("dir", (1.0, 0.0))
            if mat is not None:
                pts = [pymupdf.Point(x, y) * mat for x, y in ((x0, y0), (x1, y1))]
                x0, x1 = sorted((pts[0].x, pts[1].x))
                y0, y1 = sorted((pts[0].y, pts[1].y))
                v = pymupdf.Point(dx, dy) * pymupdf.Matrix(mat.a, mat.b, mat.c, mat.d, 0, 0)
                dx, dy = v.x, v.y
            c = spans[0].get("color", 0) or 0
            rgb = (((c >> 16) & 255) / 255.0, ((c >> 8) & 255) / 255.0, (c & 255) / 255.0)
            out.append((text, (x0, y0, x1, y1), (dx, dy), Z._pen(rgb)))
    return out


def _in_rects(x: float, y: float, rects''')
rep('''    if "walls" in wanted:
        try:
            items = stud_walls(items, model)
        except Exception:
            pass''', '''    if "walls" in wanted:
        try:
            items = stud_walls(items, model)
        except Exception:
            pass
        # Walls with no tags: drawn like a wall sample in the legend
        # (OE-DELIVERY 2026-11-10-legend-walls).
        try:
            items.extend(legend_wall_items(items, model))
        except Exception:
            pass''')
rep('''def _fill_uncovered_walls(''', '''_LEGEND_PROFILE_RE = re.compile(r"\\b(\\d{3,4}[STU]\\d{3}-\\d{2,3}(?:\\s*\\(\\d{2}\\))?)", re.IGNORECASE)


def _legend_role(text: str) -> str:
    t = text.upper()
    if "CMU" in t or "MASONRY" in t or "CONCRETE WALL" in t:
        return "CMU Wall"
    if re.search(r"NON[\\s-]*(?:LOAD[\\s-]*)?BEARING", t):
        return "Non-Load Bearing Wall"
    if "SHEAR" in t or "STRAP" in t or "BRACING" in t:
        return "Shear Wall"
    if "BEARING" in t:
        return "Load Bearing Wall"
    return "Wall"


def legend_wall_items(items: list[dict[str, Any]], model: PageModel) -> list[dict[str, Any]]:
    """Wall markups for walls drawn like a legend sample, where no wall
    markup is yet: full width, header areas apart, studs at the legend's
    spacing (else 24" o.c.)."""
    from app.modules.takeoff import detail_scan as Z

    upf = model.units_per_foot or 0.0
    if not upf or model.detail is None:
        return []
    found = Z.legend_walls(model, model.detail, model.text_lines, model.plan_region)
    if not found:
        return []
    have = [
        w for w in items
        if w.get("category") == "walls" and w.get("kind") == "line" and len(w.get("points") or []) == 2
    ]

    def covered(a, b) -> float:
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        spans = []
        for w in have:
            (cx, cy), (dx, dy) = w["points"]
            tol = max(float(w.get("wall_width") or 0.0), 2.0)
            if abs((cx - a[0]) * -uy + (cy - a[1]) * ux) > tol or abs((dx - a[0]) * -uy + (dy - a[1]) * ux) > tol:
                continue
            t1, t2 = (cx - a[0]) * ux + (cy - a[1]) * uy, (dx - a[0]) * ux + (dy - a[1]) * uy
            lo, hi = max(0.0, min(t1, t2)), min(L, max(t1, t2))
            if hi > lo:
                spans.append((lo, hi))
        spans.sort()
        tot, end = 0.0, 0.0
        for lo, hi in spans:
            lo = max(lo, end)
            if hi > lo:
                tot += hi - lo
                end = hi
        return tot / L

    out: list[dict[str, Any]] = []
    for n, f in enumerate(found):
        ty = f["type"]
        text = re.sub(r"\\s+", " ", ty["text"]).strip()
        m = _LEGEND_PROFILE_RE.search(text)
        profile = m.group(1).upper() if m else None
        colour = Z.pen_name(ty["pen"])
        role = _legend_role(text)
        designation = f"{colour} WALL"
        sp_in = stud_spacing_in(text) or DEFAULT_STUD_SPACING_IN
        sp_units = sp_in / 12.0 * upf
        a, b = f["a"], f["b"]
        L = f["length"]
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        width = f["width"]
        for pi_, (t0, t1, is_hdr) in enumerate(Z.split_wall_at_openings(L, f["openings"])):
            if t1 - t0 < (0.5 if is_hdr else 1.0) * upf:
                continue
            p0 = (a[0] + ux * t0, a[1] + uy * t0)
            p1 = (a[0] + ux * t1, a[1] + uy * t1)
            if not is_hdr and covered(p0, p1) >= 0.6:
                continue
            mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
            des = f"{designation} HEADER" if is_hdr else designation
            piece = {
                "key": _key(model.page_no, "walls", designation, mx, my, f"lg{n}.{pi_}"),
                "category": "walls",
                "kind": "line",
                "designation": des,
                "label": des,
                "role": role,
                "profile": profile or f"{colour.lower()} wall in the legend",
                "spec": (f"Header area of the {colour.lower()} wall ({_fmt_in(round((t1 - t0) / upf * 12.0 * 8) / 8)} opening). " if is_hdr else "")
                + f"Legend: {text[:300]}",
                "points": [[_r(p0[0]), _r(p0[1])], [_r(p1[0]), _r(p1[1])]],
                "anchor": [_r(mx), _r(my)],
                "page": model.page_no,
                "series": None,
                "index": pi_,
                "generated": False,
                "confidence": 0.7,
                "source": "legend",
                "segment": "header" if is_hdr else "wall",
                "wall_width": _r(width),
                "wall_width_in": round(width / upf * 12.0, 2),
                "stud_spacing_in": sp_in,
                "stud_spacing": _r(sp_units),
                "stud_count": 0 if is_hdr else Z.stud_count(t1 - t0, sp_units),
            }
            out.append(piece)
    return out


def _fill_uncovered_walls(''')
p.write_text(s, encoding="utf-8")
print("ok")
