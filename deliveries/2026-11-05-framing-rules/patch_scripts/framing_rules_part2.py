

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

    hits = page.search_for("SCHEDULE")
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
                    "role": "Roof Truss" if m.group(1) == "RT" else "Floor Truss", "rule_profile": (e or {}).get("framing"),
                    "spec": (f"{e['framing']} @ {e['spacing']}\" O.C., {e.get('length') or ''}".strip(", ") if e else None)}
        m = re.fullmatch(r"(RJ|J)-?(\d{1,2})", t)
        if m:
            tag = f"{m.group(1)}-{m.group(2)}"
            e = _sched_entry(fs, "joist", tag)
            sp = spacing_in(e.get("spacing", "")) if e else None
            return {"category": "joists", "designation": tag, "spacing_in": sp or 24.0, "series": True, "tag": True,
                    "role": "CFS Joist", "rule_profile": (e or {}).get("framing"),
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
                it["role"] = "Deck"
                it["designation"] = diaphragm[0] if diaphragm else "DECK"
                it["profile"] = (diaphragm[1].get("framing") if diaphragm else None) or "Deck"
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
            it["level"] = it["rule_level"]
        for k in ("rule_profile", "rule_height", "rule_level", "rule_spacing"):
            it.pop(k, None)
        out.append(it)
    return out
