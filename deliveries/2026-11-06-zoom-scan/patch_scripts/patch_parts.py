from pathlib import Path
import os

os.chdir(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


p = Path('auto_takeoff.py')
s = p.read_text(encoding='utf-8')
rep('''    rules: bool = False,
    detail_scan: bool = True,
) -> dict[str, Any]:
    """Run every requested category on one page model."""''', '''    rules: bool = False,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:
    """Run every requested category on one page model."""''')
rep('''    zoom_stats: dict[str, Any] | None = None
    if detail_scan and model.detail is not None and ("columns" in wanted or "beams" in wanted):
        from app.modules.takeoff import detail_scan as Z

        try:
            added, removed, zoom_stats = Z.scan_columns(''', '''    zoom_stats: dict[str, Any] | None = None
    zparts: list[dict[str, Any]] = []
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
            added, removed, zoom_stats = Z.scan_columns(''')
rep('''                seeded_only=bool(rule_on and model.kind == "foundation"),
                col_mark_re=_COL_MARK_RE,
            )''', '''                seeded_only=bool(rule_on and model.kind == "foundation"),
                col_mark_re=_COL_MARK_RE,
                parts=zparts or None,
            )''')
rep('''            new_beams, beam_stats = Z.scan_beams(model, model.detail, beam_labs, items, col_pts, unlabeled=not rule_on)''',
    '''            new_beams, beam_stats = Z.scan_beams(model, model.detail, beam_labs, items, col_pts, unlabeled=not rule_on, parts=zparts or None)''')
rep('''            zoom_stats["beams"] = {"error": True}
    if rule_on:
        _nearest_tag_owns_shared(items)''', '''            zoom_stats["beams"] = {"error": True}
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
            new_series, j_stats = Z.scan_joists(model, model.detail, series_labs, items, zparts or None)
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
            for lab, info in labels_by_cat.get("areas", []):
                if info.get("role") != "Deck":
                    continue
                if any(
                    it.get("kind") == "area" and it.get("role") == "Deck"
                    and min(q[0] for q in it["points"]) <= lab.cx <= max(q[0] for q in it["points"])
                    and min(q[1] for q in it["points"]) <= lab.cy <= max(q[1] for q in it["points"])
                    for it in items
                ):
                    continue
                poly = Z.deck_bay(lab, lines)
                if not poly:
                    continue
                d_added += 1
                items.append({
                    "key": _key(p, "areas", info["designation"], lab.cx, lab.cy, "zoom"),
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
        _nearest_tag_owns_shared(items)''')
rep('''    counts: dict[str, int] = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + (len(it["points"]) if it["kind"] == "count" else 1)
    return {''', '''    counts: dict[str, int] = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + (len(it["points"]) if it["kind"] == "count" else 1)
    if rule_on:
        missed = missed_tags(model, items, rule_infos, wanted)
    elif detail_scan:
        missed = generic_missed(model, items, labels_by_cat, wanted, used_by_columns)
    else:
        missed = []
    if detail_scan and zparts:
        from app.modules.takeoff import detail_scan as Z

        zoom_stats = zoom_stats or {}
        zoom_stats["parts"] = len(zparts)
        zoom_stats["grid"] = zparts[0]["grid"]
        try:
            zoom_stats["log"] = Z.part_log(model, zparts, items, missed)
        except Exception:
            zoom_stats["log"] = []
    return {''')
rep('''        "missed": missed_tags(model, items, rule_infos, wanted) if rule_on else [],
        "zoom_scan": zoom_stats,''', '''        "missed": missed,
        "zoom_scan": zoom_stats,''')
rep('''def missed_tags(model: PageModel, items''', '''def generic_missed(
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
        by_des.setdefault(re.sub(r"[\\s\\-]", "", it.get("designation") or ""), []).append(it)

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
            if id(lab) in used_by_columns:
                continue
            if cat == "areas" and info.get("role") != "Deck":
                continue
            if cat == "beams" and info.get("series"):
                continue
            des = info["designation"]
            key = re.sub(r"[\\s\\-]", "", des)
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


def missed_tags(model: PageModel, items''')
rep('''    rules: bool = False,
    detail_scan: bool = True,
) -> dict[str, Any]:
    cats = [c for c in categories if c in CATEGORIES] or list(CATEGORIES)''', '''    rules: bool = False,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:
    cats = [c for c in categories if c in CATEGORIES] or list(CATEGORIES)''')
rep('''rules=rules_on, detail_scan=detail_scan)''', '''rules=rules_on, detail_scan=detail_scan, zoom_parts=zoom_parts)''')
rep('''    rules: bool = False,
    detail_scan: bool = True,
) -> dict[str, Any]:
    """Run Auto Takeoff over ``pages`` (1-based) of an open PyMuPDF doc."""''', '''    rules: bool = False,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:
    """Run Auto Takeoff over ``pages`` (1-based) of an open PyMuPDF doc."""''')
rep('''        rules=rules,
        detail_scan=detail_scan,
    )''', '''        rules=rules,
        detail_scan=detail_scan,
        zoom_parts=zoom_parts,
    )''')
p.write_text(s, encoding='utf-8')

p = Path('auto_takeoff_ai.py')
s = p.read_text(encoding='utf-8')
rep('''    framing_rules: bool = True,
    detail_scan: bool = True,
) -> dict[str, Any]:''', '''    framing_rules: bool = True,
    detail_scan: bool = True,
    zoom_parts: int = 0,
) -> dict[str, Any]:''')
rep('''        rules=framing_rules,
        detail_scan=detail_scan,
    )''', '''        rules=framing_rules,
        detail_scan=detail_scan,
        zoom_parts=zoom_parts,
    )''')
p.write_text(s, encoding='utf-8')

p = Path('router.py')
s = p.read_text(encoding='utf-8')
rep('''    detail_scan: bool = Field(default=True)
''', '''    detail_scan: bool = Field(default=True)
    # Parts the sheet is split into for the zoomed check: 0 = by how busy it is.
    zoom_parts: int = Field(default=0, ge=0, le=36)
''')
rep('''            detail_scan=body.detail_scan,
        )''', '''            detail_scan=body.detail_scan,
            zoom_parts=body.zoom_parts,
        )''')
p.write_text(s, encoding='utf-8')
print("patched")
