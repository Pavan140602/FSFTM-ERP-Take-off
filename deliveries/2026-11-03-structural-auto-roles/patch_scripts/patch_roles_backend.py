# OE-DELIVERY 2026-11-03-auto-takeoff-roles: role (LB / NLB wall, header, jamb, floor / roof
# truss, floor joist, beam, column ...) + profile per item, header/jamb tags + schedules,
# column marks with their text position.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    c = s.count(old)
    if c != count:
        print('ANCHOR FAIL (found %d want %d)\n%s' % (c, count, old[:200]))
        sys.exit(1)
    s = s.replace(old, new)


rep('''_DIM_RE = re.compile(r"^\\d+\\s*['’]\\s*-?\\s*\\d*")''',
    '''_DIM_RE = re.compile(r"^\\d+\\s*['’]\\s*-?\\s*\\d*")
# Headers / jambs (OE-DELIVERY 2026-11-03-auto-takeoff-roles).
_JAMB_RE = re.compile(r"\\bJAMBS?\\b|\\bJMB\\b", re.IGNORECASE)
_HDR_TAG_RE = re.compile(r"^(?:HDR|H)-?\\d{1,2}[A-Z]?$", re.IGNORECASE)
_JAMB_TAG_RE = re.compile(r"^(?:JB|JMB|JAMB)-?\\d{1,2}[A-Z]?$", re.IGNORECASE)''')

# classify: jambs + header role on SSMA members
rep('''        if D._ssma_valid(des):
            if _HEADER_RE.search(text):
                return {"category": "other", "designation": f"{des} HDR" if "HDR" not in des else des, "spacing_in": None, "series": False}''',
    '''        if D._ssma_valid(des):
            if _JAMB_RE.search(text):
                return {"category": "other", "designation": des, "spacing_in": None, "series": False, "role": "Jamb"}
            if _HEADER_RE.search(text):
                return {"category": "other", "designation": f"{des} HDR" if "HDR" not in des else des, "spacing_in": None, "series": False, "role": "Header"}''')
# header / jamb tags (before wall tags; W-tags never match these)
rep('''    if _WALL_TAG_RE.match(compact) and len(compact) <= 6:
        return {"category": "walls", "designation": compact, "spacing_in": None, "series": False, "tag": True}''',
    '''    if _HDR_TAG_RE.match(compact) and spacing is None:
        return {"category": "other", "designation": compact, "spacing_in": None, "series": False, "tag": True, "role": "Header"}
    if _JAMB_TAG_RE.match(compact) and spacing is None:
        return {"category": "other", "designation": compact, "spacing_in": None, "series": False, "tag": True, "role": "Jamb"}
    if _WALL_TAG_RE.match(compact) and len(compact) <= 6:
        return {"category": "walls", "designation": compact, "spacing_in": None, "series": False, "tag": True}''')
rep('''    if re.fullmatch(r"\\(?\\d\\)?\\s*HDR|HDR|HEADER", compact) or compact in ("HDR", "BOXHEADER", "BOXBEAM"):
        return {"category": "other", "designation": "HDR", "spacing_in": None, "series": False}''',
    '''    if re.fullmatch(r"\\(?\\d\\)?\\s*HDR|HDR|HEADER", compact) or compact in ("HDR", "BOXHEADER", "BOXBEAM"):
        return {"category": "other", "designation": "HDR", "spacing_in": None, "series": False, "role": "Header"}''')

# schedules: header / jamb schedules too
rep('''                if not _WALL_TAG_RE.match(first) and not _TRUSS_TAG_RE.match(first):
                    continue''',
    '''                if not (_WALL_TAG_RE.match(first) or _TRUSS_TAG_RE.match(first) or _HDR_TAG_RE.match(first) or _JAMB_TAG_RE.match(first)):
                    continue''')

# member loop: a header / jamb tag with no line under it still counts, at the tag
rep('''            seed = _member_seed(lab, model, strict=bool(info.get("tag")))
            if seed is None:
                continue''',
    '''            seed = _member_seed(lab, model, strict=bool(info.get("tag")))
            if seed is None:
                if info.get("tag") and info.get("role") in ("Header", "Jamb") and cat in wanted:
                    tag_marks.append((lab, info))
                continue''')
rep('''    # Members (beams, other, single joists/trusses, column labels on lines).
    member_entries: list[dict[str, Any]] = []''',
    '''    # Members (beams, other, single joists/trusses, column labels on lines).
    member_entries: list[dict[str, Any]] = []
    tag_marks: list[tuple[Label, dict[str, Any]]] = []''')
rep('''            "confidence": 0.85 if info.get("source") != "ai" else 0.7,
            "source": info.get("source") or "rules",
        })

    # Joist / truss series and their bays.''',
    '''            "confidence": 0.85 if info.get("source") != "ai" else 0.7,
            "source": info.get("source") or "rules",
            "role": info.get("role"),
        })
    # Header / jamb tags placed as counts at the tag; a lone tag with no
    # schedule row is skipped (could be a grid or detail mark).
    tag_seen: dict[str, int] = {}
    for lab, info in tag_marks:
        tag_seen[info["designation"]] = tag_seen.get(info["designation"], 0) + 1
    for lab, info in tag_marks:
        tag = info["designation"]
        spec = (specs or {}).get(tag)
        if not spec and tag_seen.get(tag, 0) < 2:
            continue
        items.append({
            "key": _key(p, "other", tag, lab.cx, lab.cy),
            "category": "other",
            "kind": "count",
            "designation": tag,
            "label": tag,
            "spec": spec,
            "points": [[_r(lab.cx), _r(lab.cy)]],
            "anchor": [_r(lab.cx), _r(lab.cy)],
            "label_rect": [_r(v) for v in lab.rect],
            "label_quad": label_quad(lab),
            "page": p,
            "series": None,
            "index": None,
            "generated": False,
            "confidence": 0.7 if spec else 0.5,
            "source": info.get("source") or "rules",
            "role": info.get("role"),
        })

    # Joist / truss series and their bays.''')

# columns: mark + where it is printed
rep('''                "spec": (f"Mark {c['mark']}" if c["mark"] else None),''',
    '''                "spec": (f"Mark {c['mark']}" if c["mark"] else None),
                "mark": c["mark"],
                "mark_quad": label_quad(c["mark_obj"]) if c.get("mark_obj") is not None else None,''')
rep('''            out.append({
                "label_obj": src[1] if src else None,''',
    '''            out.append({
                "mark_obj": mark_lab[1] if mark_lab else None,
                "label_obj": src[1] if src else None,''')

# roles for every item of the page
rep('''    items = _dedupe_items(items)
    counts: dict[str, int] = {}''',
    '''    items = _dedupe_items(items)
    assign_roles(items, model, specs)
    counts: dict[str, int] = {}''')

ROLES = '''

# ── roles: what each member is (OE-DELIVERY 2026-11-03-auto-takeoff-roles) ──
# The role names match the structural Tool Chest sets (SSMA / AISC), so an
# auto markup lands with the same Subject as the tool you would draw it with.

_ROOF_CTX_RE = re.compile(r"ROOF\\s+(?:FRAMING|PLAN|TRUSS)|TRUSS\\s+LAYOUT|RAFTER", re.IGNORECASE)
_FLOOR_CTX_RE = re.compile(r"FLOOR\\s+(?:FRAMING|PLAN|TRUSS|JOIST)|(?:LEVEL|LVL)\\s*\\d+\\s+FRAMING|(?:2ND|3RD|\\dTH|SECOND|THIRD)\\s+FLOOR", re.IGNORECASE)
_CEILING_CTX_RE = re.compile(r"CEILING\\s+(?:FRAMING|JOIST|PLAN)", re.IGNORECASE)
_NLB_RE = re.compile(r"NON[\\s-]*(?:LOAD|BEARING|STRUCTURAL)|\\bNLB\\b|\\bNLBW\\b|PARTITION|CURTAIN\\s*WALL|INTERIOR\\s+NON", re.IGNORECASE)
_LB_RE = re.compile(r"LOAD[\\s-]*BEARING|\\bLBW?\\b|\\bBEARING\\s+WALL|SHEAR\\s*WALL|\\bSW\\b|STRUCTURAL\\s+STUD", re.IGNORECASE)


def sheet_context(model: PageModel) -> str | None:
    """'roof', 'floor' or 'ceiling' from the sheet title and notes."""
    roof = floor = ceiling = 0
    for lab in model.labels:
        t = lab.text
        if len(t) > 80:
            continue
        roof += len(_ROOF_CTX_RE.findall(t))
        floor += len(_FLOOR_CTX_RE.findall(t))
        ceiling += len(_CEILING_CTX_RE.findall(t))
    if max(roof, floor, ceiling) == 0:
        return None
    if roof >= floor and roof >= ceiling:
        return "roof"
    return "floor" if floor >= ceiling else "ceiling"


def profile_of(text: str | None) -> str | None:
    """First SSMA / AISC designation inside a schedule row or callout."""
    if not text:
        return None
    m = D._SSMA_RE.search(text) or D._AISC_RE.search(text)
    return D.normalize_designation(m.group(0)) if m else None


def wall_role(tag: str, spec: str | None) -> str:
    text = spec or ""
    if _NLB_RE.search(text):
        return "Non-Load Bearing Wall"
    if _LB_RE.search(text):
        return "Load Bearing Wall"
    t = tag.upper()
    if t.startswith(("IW", "PW", "NW")):
        return "Non-Load Bearing Wall"
    if t.startswith(("EW", "LW", "BW", "SW")):
        return "Load Bearing Wall"
    prof = profile_of(text)
    if prof:
        m = re.match(r"(\\d{3,4})S\\d{3}-(\\d{2,3})", prof)
        if m:
            # Heavy studs (54 mil +) carry load; light ones are partitions.
            return "Load Bearing Wall" if int(m.group(2)) >= 54 else "Non-Load Bearing Wall"
    return "CFS Wall"


def assign_roles(items: list[dict[str, Any]], model: PageModel, specs: dict[str, str] | None) -> None:
    ctx = sheet_context(model)
    for it in items:
        cat = it["category"]
        des = str(it.get("designation") or "")
        spec = it.get("spec") or (specs or {}).get(des)
        text = f"{des} {spec or ''} {it.get('label') or ''}"
        role = it.get("role")
        if cat == "walls":
            role = wall_role(des, spec)
        elif cat == "trusses":
            if re.search(r"FLOOR", text, re.IGNORECASE):
                role = "Floor Truss"
            elif re.search(r"ROOF|RAFTER", text, re.IGNORECASE):
                role = "Roof Truss"
            else:
                role = "Floor Truss" if ctx == "floor" else "Roof Truss"
        elif cat == "joists":
            if re.search(r"CEIL", text, re.IGNORECASE) or ctx == "ceiling":
                role = "Ceiling Joist"
            elif re.search(r"ROOF", text, re.IGNORECASE) or ctx == "roof":
                role = "Roof Joist"
            else:
                role = "Floor Joist"
        elif cat == "beams":
            role = role or "Beam"
        elif cat == "columns":
            role = "Column"
        elif cat == "areas":
            role = "Framing Area"
        elif not role:
            if _JAMB_RE.search(text):
                role = "Jamb"
            elif _HEADER_RE.search(text):
                role = "Header"
            elif des.startswith("L"):
                role = "Angle"
            elif re.match(r"\\d{3,4}T\\d", des):
                role = "Track"
            elif re.match(r"\\d{3,4}S\\d", des):
                role = "Stud"
            else:
                role = "Other"
        it["role"] = role
        prof = profile_of(spec) if (spec and not profile_of(des)) else None
        if prof:
            it["profile"] = prof
'''
rep('''# ── driver ────────────────────────────────────────────────────────────''',
    ROLES.strip('\n') + '''


# ── driver ────────────────────────────────────────────────────────────''')
P.write_text(s, encoding='utf-8')
print('ok')
