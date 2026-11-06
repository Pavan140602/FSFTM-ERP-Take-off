

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
        f[2].append((lo, hi))
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
    # Openings: where neither face is drawn with the wall's own (heavy) pen.
    pen_w = min(fa[3], fb[3])
    spans: list[tuple[float, float]] = []
    for k, f in faces.items():
        if abs(f[0] - fa[0]) <= 0.7 or abs(f[0] - fb[0]) <= 0.7:
            if f[3] >= max(heavy_w * 0.8, pen_w * 0.6):
                spans.extend(f[2])
    spans.sort()
    merged: list[list[float]] = []
    for lo, hi in spans:
        if merged and lo <= merged[-1][1] + 0.6:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    gaps = []
    for (_lo, hi), (lo2, _hi2) in zip(merged, merged[1:]):
        g = lo2 - hi
        if 2.0 * upf <= g <= 20.0 * upf:
            gaps.append((hi, lo2))
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
    """Studs in a run at a spacing, one at each end: floor(L / s) + 1."""
    if spacing_units <= 0 or length_units <= 0:
        return 0
    return int(math.floor(length_units / spacing_units + 1e-6)) + 1
