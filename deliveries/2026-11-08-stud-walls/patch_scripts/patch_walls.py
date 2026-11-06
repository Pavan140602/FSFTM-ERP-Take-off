from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
SP = Path(r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\732e120e-2b91-4dfc-bda2-2925a51afa1e\scratchpad")

p = base / "detail_scan.py"
s = p.read_text(encoding="utf-8")
if "def wall_geometry" not in s:
    s += (SP / "walls_part.py").read_text(encoding="utf-8")
    p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('''    counts: dict[str, int] = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + (len(it["points"]) if it["kind"] == "count" else 1)
    if rule_on:
        missed = missed_tags(model, items, rule_infos, wanted)''', '''    # Stud walls: full width, header areas apart, studs at their spacing
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
        missed = missed_tags(model, items, rule_infos, wanted)''')

rep('''def generic_missed(''', '''DEFAULT_STUD_SPACING_IN = 24.0


def stud_walls(items: list[dict[str, Any]], model: PageModel) -> list[dict[str, Any]]:
    """Each wall markup read at full width, the way an estimator takes off
    a stud wall:

    * width - the distance between the wall's two drawn faces (else the stud
      depth from its profile, 600S... = 6"); the markup moves onto the true
      centre line between the faces;
    * header areas - where the faces stop at an opening the run is cut, and
      the opening becomes its own piece (no studs; header size from the
      nearest header tag), never merged with the plain wall;
    * studs - at the spacing on the plan (schedule / tag "@ 16\\" O.C."), else
      24" on centre; one at each end.
    """
    upf = model.units_per_foot or 0.0
    from app.modules.takeoff import detail_scan as Z

    headers = [
        it for it in items
        if it.get("kind") == "count" and "Header" in (it.get("role") or "")
    ]
    out: list[dict[str, Any]] = []
    for it in items:
        if it.get("category") != "walls" or it.get("kind") != "line" or len(it.get("points") or []) != 2:
            out.append(it)
            continue
        text = " ".join(str(it.get(k) or "") for k in ("spec", "rule_spacing", "label"))
        sp_in = spacing_inches(text) or DEFAULT_STUD_SPACING_IN
        profile = it.get("profile") or it.get("rule_profile") or ""
        depth = Z.stud_depth_in(profile)
        (ax, ay), (bx, by) = it["points"]
        if not upf:
            it.update({"stud_spacing_in": sp_in, "segment": "wall"})
            out.append(it)
            continue
        fallback_w = (depth or 6.0) / 12.0 * upf
        geo = Z.wall_geometry(model, model.detail, (ax, ay), (bx, by), fallback_w) if model.detail is not None else {
            "width": fallback_w, "offset": 0.0, "openings": [], "length": math.hypot(bx - ax, by - ay)
        }
        L = geo["length"]
        if L <= 0:
            out.append(it)
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        width = geo["width"] or fallback_w
        off = geo["offset"] if abs(geo["offset"]) <= width else 0.0
        sp_units = sp_in / 12.0 * upf
        pieces = Z.split_wall_at_openings(L, geo["openings"])
        for i, (t0, t1, is_hdr) in enumerate(pieces):
            if t1 - t0 < (0.5 if is_hdr else 1.0) * upf:
                continue
            p0 = (ax + ux * t0 + nx * off, ay + uy * t0 + ny * off)
            p1 = (ax + ux * t1 + nx * off, ay + uy * t1 + ny * off)
            piece = dict(it)
            piece["points"] = [[_r(p0[0]), _r(p0[1])], [_r(p1[0]), _r(p1[1])]]
            piece["key"] = it["key"] if len(pieces) == 1 else f"{it['key']}|w{i}"
            piece["wall_width"] = _r(width)
            piece["wall_width_in"] = round(width / upf * 12.0, 2)
            piece["stud_spacing_in"] = sp_in
            piece["stud_spacing"] = _r(sp_units)
            if is_hdr:
                # The opening: header over it, jacks / kings at its sides.
                mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
                near = min(
                    headers,
                    key=lambda h: math.hypot(h["points"][0][0] - mx, h["points"][0][1] - my),
                    default=None,
                )
                hdr = near if near is not None and math.hypot(near["points"][0][0] - mx, near["points"][0][1] - my) <= max(4.0 * upf, (t1 - t0)) else None
                piece["segment"] = "header"
                piece["stud_count"] = 0
                piece["designation"] = f"{it['designation']} HEADER"
                piece["label"] = piece["designation"]
                piece["header"] = hdr["designation"] if hdr else None
                piece["profile"] = (hdr.get("profile") if hdr else None) or profile
                piece["spec"] = (
                    f"Header area of wall {it['designation']} ({_fmt_in((t1 - t0) / upf * 12.0)} opening)"
                    + (f": header {hdr['designation']} - {hdr.get('spec') or hdr.get('profile') or ''}" if hdr else "")
                )
            else:
                piece["segment"] = "wall"
                piece["stud_count"] = Z.stud_count(t1 - t0, sp_units)
            out.append(piece)
    return out


def generic_missed(''')
p.write_text(s, encoding="utf-8")
print("ok")
