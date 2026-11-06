# OE-DELIVERY 2026-11-05-framing-rules: house framing rules wired into Auto Takeoff.
#   framing / roof plans -> floor framing only (trusses + joists framed one by one
#   at schedule spacing, beams, deck); shear wall plans -> walls of the level row
#   ("1ST TO 2ND" on the 1st floor plan), headers, shear / strap-braced walls,
#   holdowns, steel braces; foundation -> columns + base plates (no footings);
#   any other sheet is skipped.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])
A = ROOT / "backend/app/modules/takeoff/auto_takeoff.py"
AI = ROOT / "backend/app/modules/takeoff/auto_takeoff_ai.py"
RT = ROOT / "backend/app/modules/takeoff/router.py"

files = {p: p.read_text(encoding="utf-8") for p in (A, AI, RT)}


def rep(p, old, new):
    s = files[p]
    if s.count(old) != 1:
        print("ANCHOR FAIL", p.name, s.count(old), old[:140])
        sys.exit(1)
    files[p] = s.replace(old, new)


# ── PageModel ──
rep(A, '''    column_source: bool = False


''', '''    column_source: bool = False
    # Framing rules (OE-DELIVERY 2026-11-05-framing-rules): what the sheet is
    # ('framing' | 'roof' | 'walls' | 'foundation' | None), the floor level
    # and the drawing set's schedules.
    kind: str | None = None
    level: int | None = None
    fsched: dict[str, Any] = field(default_factory=dict)


''')

# ── take_off_page: rule classification ──
rep(A, '''    col_marks: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run every requested category on one page model."""
    wanted = set(categories) & set(CATEGORIES)
    items: list[dict[str, Any]] = []
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]] = {}
    seen: set[tuple[str, int, int]] = set()
    for lab in model.labels:
        if _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
            continue
        if skip_spots and (model.page_no, int(round(lab.cx / 4.0)), int(round(lab.cy / 4.0))) in skip_spots:
            continue
        info = classify(lab, hints)
        if not info:
            continue''', '''    col_marks: dict[str, str] | None = None,
    rules: bool = False,
) -> dict[str, Any]:
    """Run every requested category on one page model."""
    from app.modules.takeoff import framing_rules as FR

    wanted = set(categories) & set(CATEGORIES)
    rule_on = bool(rules and model.kind)
    if rule_on:
        wanted &= FR.ALLOWED.get(model.kind or "", set())
    rule_ctx = (model.kind or "", model.level, model.fsched)
    rule_infos: dict[tuple[str, int, int], dict[str, Any]] = {}
    rule_counts: list[tuple[Label, dict[str, Any]]] = []
    items: list[dict[str, Any]] = []
    labels_by_cat: dict[str, list[tuple[Label, dict[str, Any]]]] = {}
    seen: set[tuple[str, int, int]] = set()
    for lab in model.labels:
        if _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
            continue
        if skip_spots and (model.page_no, int(round(lab.cx / 4.0)), int(round(lab.cy / 4.0))) in skip_spots:
            continue
        info = None
        if rule_on:
            ri = FR.rule_classify(lab.text, rule_ctx)
            if ri == "skip":
                continue
            if isinstance(ri, dict):
                info = ri
                rule_infos[(ri["designation"], int(round(lab.cx)), int(round(lab.cy)))] = ri
                if ri.get("count_role"):
                    if ri["category"] in wanted:
                        k = (ri["designation"], int(round(lab.cx / 4)), int(round(lab.cy / 4)))
                        if k not in seen:
                            seen.add(k)
                            rule_counts.append((lab, ri))
                    continue
        if info is None:
            info = classify(lab, hints)
        if not info:
            continue''')

# ── emit rule counts, stamp rule data, filter by sheet kind ──
rep(A, '''    items = _dedupe_items(items)
    snap_member_ends(items)
    assign_roles(items, model, specs)
    counts: dict[str, int] = {}''', '''    # Rule counts: headers, holdowns, steel braces, base plates, one per tag.
    for lab, info in rule_counts:
        tag = info["designation"]
        items.append({
            "key": _key(p, info["category"], tag, lab.cx, lab.cy),
            "category": info["category"],
            "kind": "count",
            "designation": tag,
            "label": tag,
            "spec": info.get("spec"),
            "points": [[_r(lab.cx), _r(lab.cy)]],
            "anchor": [_r(lab.cx), _r(lab.cy)],
            "label_rect": [_r(v) for v in lab.rect],
            "label_quad": label_quad(lab),
            "page": p,
            "series": None,
            "index": None,
            "generated": False,
            "confidence": 0.75 if info.get("spec") else 0.6,
            "source": "rules",
            "role": info.get("role"),
            "rule_profile": info.get("rule_profile"),
            "rule_level": info.get("rule_level"),
        })

    items = _dedupe_items(items)
    snap_member_ends(items)
    assign_roles(items, model, specs)
    if rule_on:
        for it in items:
            a = it.get("anchor") or [0, 0]
            ri = rule_infos.get((it.get("designation") or "", int(round(a[0])), int(round(a[1]))))
            if ri:
                for k in ("rule_profile", "rule_height", "rule_level", "rule_spacing"):
                    if ri.get(k) and not it.get(k):
                        it[k] = ri[k]
                if ri.get("role"):
                    it["role"] = ri["role"]
                if ri.get("spec") and it.get("series") is None:
                    it["spec"] = ri["spec"]
                elif ri.get("spec") and it.get("series"):
                    it["spec"] = ri["spec"]
            if not it.get("rule_level") and model.level is not None and model.kind in ("framing", "walls"):
                it["level"] = FR.ORD_NAME.get(model.level, str(model.level)) + " FLOOR"
            elif model.kind == "roof" and not it.get("rule_level"):
                it["level"] = "ROOF"
        items = FR.post_process(items, model.kind or "", model.level, model.fsched)
    counts: dict[str, int] = {}''')

rep(A, '''        "counts": counts,
        "items": items,
        "note": unit_note,
    }


def _dedupe_items(''', '''        "counts": counts,
        "items": items,
        "note": unit_note,
        "sheet_kind": model.kind if rule_on else None,
        "level": model.level if rule_on else None,
    }


def _dedupe_items(''')

# ── build_models: sheet kinds + schedules ──
rep(A, '''def build_models(pdf, pages: list[int], *, want_specs: bool = True) -> tuple[list[PageModel], list[PageModel]]:
    """Page models for ``pages`` plus light models of schedule sheets."""
    models: list[PageModel] = []
    for page_no in pages:
        if 1 <= page_no <= len(pdf):
            models.append(build_page_model(pdf[page_no - 1], page_no))
    spec_models = list(models)''', '''def build_models(
    pdf, pages: list[int], *, want_specs: bool = True, rules: bool = False
) -> tuple[list[PageModel], list[PageModel]]:
    """Page models for ``pages`` plus light models of schedule sheets."""
    models: list[PageModel] = []
    for page_no in pages:
        if 1 <= page_no <= len(pdf):
            models.append(build_page_model(pdf[page_no - 1], page_no))
    if rules:
        apply_framing_rules(pdf, models)
    spec_models = list(models)''')

rep(A, '''def run_models(
    models: list[PageModel],''', '''def apply_framing_rules(pdf, models: list[PageModel]) -> dict[str, Any]:
    """Sheet kind, level and schedules on each model (framing rules)."""
    from app.modules.takeoff import framing_rules as FR

    doc = FR.document_schedules(pdf, getattr(pdf, "name", None))
    for m in models:
        page = pdf[m.page_no - 1]
        try:
            m.kind, m.level, _titles = FR.page_kind(page)
        except Exception:
            m.kind, m.level = None, None
        m.fsched = doc["schedules"]
        if m.kind:
            try:
                m.schedule_rects.extend(FR.page_schedule_rects(page, doc["rects"], m.page_no - 1))
            except Exception:
                pass
    return doc


def run_models(
    models: list[PageModel],''')

rep(A, '''    include_details: bool = False,
    extra_specs: dict[str, str] | None = None,
) -> dict[str, Any]:
    cats = [c for c in categories if c in CATEGORIES] or list(CATEGORIES)''', '''    include_details: bool = False,
    extra_specs: dict[str, str] | None = None,
    rules: bool = False,
) -> dict[str, Any]:
    cats = [c for c in categories if c in CATEGORIES] or list(CATEGORIES)
    # Framing rules apply once the set has recognised plan sheets.
    rules_on = bool(rules and any(m.kind for m in models))''')

rep(A, '''    for model in models:
        if is_detail_sheet(model) and not include_details:''', '''    for model in models:
        if rules_on and not model.kind:
            results.append({
                "page": model.page_no,
                "scale": model.scale_text,
                "units_per_foot": model.units_per_foot,
                "paper_in_per_ft": round(model.units_per_foot / 72.0, 5) if model.units_per_foot else None,
                "detail_sheet": is_detail_sheet(model),
                "counts": {},
                "items": [],
                "note": "Not a framing, shear wall or foundation plan - skipped by the framing rules.",
                "sheet_kind": None,
            })
            continue
        if is_detail_sheet(model) and not include_details:''')

rep(A, '''        res = take_off_page(model, cats, hints=hints, specs=specs, skip_spots=spots, col_marks=col_marks)''',
    '''        res = take_off_page(model, cats, hints=hints, specs=specs, skip_spots=spots, col_marks=col_marks, rules=rules_on)''')

rep(A, '''        "sheets_read": len(spec_models),
    }
    return {"pages": results, "specs": specs, "column_marks": col_marks, "read": read}''', '''        "sheets_read": len(spec_models),
    }
    if rules_on:
        fs = next((m.fsched for m in models if m.fsched), {})
        read["framing_rules"] = True
        read["schedules"] = {k: sorted(v) for k, v in fs.items()}
        read["sheets"] = [
            {"page": m.page_no, "kind": m.kind, "level": m.level} for m in models if m.kind
        ]
    return {"pages": results, "specs": specs, "column_marks": col_marks, "read": read}''')

rep(A, '''    extra_specs: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run Auto Takeoff over ``pages`` (1-based) of an open PyMuPDF doc."""
    models, spec_models = build_models(pdf, pages)
    return run_models(
        models,
        spec_models,
        categories,
        hints_by_page=hints_by_page,
        include_details=include_details,
        extra_specs=extra_specs,
    )''', '''    extra_specs: dict[str, str] | None = None,
    rules: bool = False,
) -> dict[str, Any]:
    """Run Auto Takeoff over ``pages`` (1-based) of an open PyMuPDF doc."""
    models, spec_models = build_models(pdf, pages, rules=rules)
    return run_models(
        models,
        spec_models,
        categories,
        hints_by_page=hints_by_page,
        include_details=include_details,
        extra_specs=extra_specs,
        rules=rules,
    )''')

# ── AI entry point ──
rep(AI, '''    use_ai: bool,
    include_details: bool,
) -> dict[str, Any]:
    path = D._resolve_file(doc)''', '''    use_ai: bool,
    include_details: bool,
    framing_rules: bool = True,
) -> dict[str, Any]:
    path = D._resolve_file(doc)''')
rep(AI, '''            models, spec_models = A.build_models(pdf, wanted, want_specs=True)''',
    '''            models, spec_models = A.build_models(pdf, wanted, want_specs=True, rules=framing_rules)''')
rep(AI, '''        include_details=include_details,
        extra_specs=extra_specs,
    )
    result["available"] = True''', '''        include_details=include_details,
        extra_specs=extra_specs,
        rules=framing_rules,
    )
    result["available"] = True''')

# ── router ──
rep(RT, '''    use_ai: bool = Field(default=False)
    include_details: bool = Field(default=False)


@router.get(
    "/documents/{doc_id}/auto-takeoff/status/",''', '''    use_ai: bool = Field(default=False)
    include_details: bool = Field(default=False)
    # House framing rules (OE-DELIVERY 2026-11-05-framing-rules).
    framing_rules: bool = Field(default=True)


@router.get(
    "/documents/{doc_id}/auto-takeoff/status/",''')
rep(RT, '''            use_ai=body.use_ai,
            include_details=body.include_details,
        )''', '''            use_ai=body.use_ai,
            include_details=body.include_details,
            framing_rules=body.framing_rules,
        )''')
# warm the schedule cache when the panel asks for the status
rep(RT, '''    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    ai = await auto_takeoff_ai.ai_status(session, str(user_id) if user_id else "")
    return {"available": detect_svc._resolve_file(doc) is not None, "ai": ai}''', '''    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    ai = await auto_takeoff_ai.ai_status(session, str(user_id) if user_id else "")
    path = detect_svc._resolve_file(doc)
    if path is not None:
        # Read the set's schedules in the background so the first run is fast.
        from app.modules.takeoff import framing_rules as _fr

        _fr.warm_schedules(str(path))
    return {"available": path is not None, "ai": ai}''')

FR_ADD = '''


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
'''
FRP = ROOT / "backend/app/modules/takeoff/framing_rules.py"
frs = FRP.read_text(encoding="utf-8").rstrip("\n") + FR_ADD

for p, s in files.items():
    p.write_text(s, encoding="utf-8")
FRP.write_text(frs, encoding="utf-8")
print("ok")
