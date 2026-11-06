from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\auto_takeoff.py")
s = p.read_text(encoding="utf-8")
i = s.index("def stud_walls(items: list[dict[str, Any]], model: PageModel) -> list[dict[str, Any]]:")
j = s.index("def generic_missed(", i)
new = r'''def stud_walls(items: list[dict[str, Any]], model: PageModel) -> list[dict[str, Any]]:
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
    return out


'''
s = s[:i] + new + s[j:]
p.write_text(s, encoding="utf-8")
print("ok")
