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
part = (SP / "uncovered_part.py").read_text(encoding="utf-8").replace("""            for q in (ca, cb):
                pass
""", "")
if "def uncovered_walls" not in s:
    s += part
# wall_geometry reports the face pens it trusted
rep("""    spans: list[tuple[float, float]] = sorted((lo, hi) for lo, hi, w in face_segs if w >= wall_pen)""",
    """    spans: list[tuple[float, float]] = sorted((lo, hi) for lo, hi, w in face_segs if w >= wall_pen)
    out["face_widths"] = sorted({round(w, 2) for _lo, _hi, w in face_segs if w >= wall_pen})""")
p.write_text(s, encoding="utf-8")

p = base / "auto_takeoff.py"
s = p.read_text(encoding="utf-8")
# collect learned widths / pens while walls are read
rep("""    replace: dict[int, list[dict[str, Any]]] = {}
    for members in chains.values():""", """    replace: dict[int, list[dict[str, Any]]] = {}
    learned_widths: list[float] = []
    learned_pen_widths: set[float] = set()
    for members in chains.values():""")
rep("""        width = geo["width"] or fallback_w
        off = geo["offset"] if abs(geo["offset"]) <= width else 0.0
        openings = [(g0 + t_lo, g1 + t_lo) for g0, g1 in geo["openings"]]""", """        width = geo["width"] or fallback_w
        off = geo["offset"] if abs(geo["offset"]) <= width else 0.0
        openings = [(g0 + t_lo, g1 + t_lo) for g0, g1 in geo["openings"]]
        if geo.get("width"):
            learned_widths.append(geo["width"])
            learned_pen_widths.update(geo.get("face_widths") or [])""")
rep("""    # A shear / strap-braced panel drawn on a bearing wall is part of that
    # wall: the wall's studs already cover it, so the panel counts none of""", """    # Cover the whole drawn wall: stretches of double-line wall in the wall
    # pen, at a wall width, that no tag reached (beside an opening, past a
    # cross wall ...) are taken off too - as the tagged wall they continue,
    # else as an untagged wall to check (OE-DELIVERY 2026-11-09-colours-keys).
    if model.detail is not None and len(learned_widths) >= 3:
        try:
            out.extend(_fill_uncovered_walls(out, model, learned_widths, learned_pen_widths, headers))
        except Exception:
            pass
    # A shear / strap-braced panel drawn on a bearing wall is part of that
    # wall: the wall's studs already cover it, so the panel counts none of""")
rep('''def generic_missed(''', '''def _fill_uncovered_walls(
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


def generic_missed(''')
p.write_text(s, encoding="utf-8")
print("ok")
