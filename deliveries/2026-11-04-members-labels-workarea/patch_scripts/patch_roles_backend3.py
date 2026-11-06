# OE-DELIVERY 2026-11-03-auto-takeoff-members: steel = columns, beams, SJI joists (K/LH/DLH),
# deck areas (type B / composite / form / N / cellular); CFS = load bearing / shear /
# non-load bearing walls, LB + NLB headers and jambs, trusses, CFS joists, hat channels.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new):
    global s
    if s.count(old) != 1:
        print('ANCHOR FAIL', s.count(old), old[:160])
        sys.exit(1)
    s = s.replace(old, new)


rep('''_HDR_TAG_RE = re.compile(r"^(?:HDR|H)-?\\d{1,2}[A-Z]?$", re.IGNORECASE)''',
    '''_HDR_TAG_RE = re.compile(r"^(?:HDR|H)-?\\d{1,2}[A-Z]?$", re.IGNORECASE)
# Hat / furring channels and metal deck (OE-DELIVERY 2026-11-03-auto-takeoff-members).
_HAT_RE = re.compile(r"\\bHAT\\s*(?:CHANNEL|CHNL|SECTION)?S?\\b|FURRING\\s+CHANNEL|RESILIENT\\s+CHANNEL|\\bRC-?1\\b", re.IGNORECASE)
_DECK_WORD_RE = re.compile(r"\\bDECK(?:ING)?\\b", re.IGNORECASE)
_DECK_DES_RE = re.compile(
    r"(\\d(?:\\.\\d+)?|\\d\\s+\\d/\\d)\\s*(?:\\"|IN\\.?)?\\s*(?:TYPE\\s+)?(VLI|VLR|VL|PLB|LOK|B|F|A|N|C)\\b[\\s,-]*(\\d{2})?\\s*(?:GA\\.?)?",
    re.IGNORECASE,
)''')

DECK_FN = '''

def deck_info(text: str) -> dict[str, Any] | None:
    """Metal deck callout -> designation + deck type (OE-DELIVERY 2026-11-03-auto-takeoff-members)."""
    upper = text.upper()
    m = _DECK_DES_RE.search(upper)
    if not _DECK_WORD_RE.search(upper) and not (m and m.group(0).strip() == upper.strip()):
        return None
    if re.search(r"COMPOSITE|\\bVLI?\\b|\\bVLR\\b|\\bLOK\\b|\\bPLB\\b|\\bCOMP\\b", upper):
        kind = "Composite Deck"
    elif re.search(r"\\bFORM\\b|CONFORM|\\bUFX?\\b", upper):
        kind = "Form Deck"
    elif re.search(r"CELLULAR", upper):
        kind = "Cellular Deck"
    elif m and m.group(2).upper() == "N":
        kind = "Type N Deck"
    elif m and m.group(2).upper() in ("B", "F", "A"):
        kind = f"Type {m.group(2).upper()} Roof Deck"
    elif re.search(r"ROOF", upper):
        kind = "Roof Deck"
    elif re.search(r"FLOOR", upper):
        kind = "Floor Deck"
    else:
        kind = "Metal Deck"
    if m:
        depth = m.group(1).replace(" ", "-")
        des = f'{depth}" {m.group(2).upper()}' + (f"-{m.group(3)} GA" if m.group(3) else "")
    else:
        des = kind.upper()
    return {"category": "areas", "designation": des, "spacing_in": None, "series": False, "role": "Deck", "deck_type": kind}


def _deck_region(label: Label, model: PageModel) -> list[tuple[float, float]] | None:
    """The bay a deck callout sits in: the nearest long framing line on each side."""
    def accept_dir(vertical: bool):
        def acc(seg) -> bool:
            if seg[4] < 90:
                return False
            ang = abs(_seg_angle(seg))
            return (abs(ang - 90) <= 8) if vertical else (ang <= 8 or ang >= 172)
        return acc

    r = _cast(model, label.cx, label.cy, 1.0, 0.0, 1600.0, accept_dir(True))
    left = _cast(model, label.cx, label.cy, -1.0, 0.0, 1600.0, accept_dir(True))
    d = _cast(model, label.cx, label.cy, 0.0, 1.0, 1600.0, accept_dir(False))
    u = _cast(model, label.cx, label.cy, 0.0, -1.0, 1600.0, accept_dir(False))
    if None in (r, left, d, u):
        return None
    x0, x1 = label.cx - left, label.cx + r
    y0, y1 = label.cy - u, label.cy + d
    if (x1 - x0) < 40 or (y1 - y0) < 40:
        return None
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
'''
rep('''def classify(label: Label, hints: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:''',
    DECK_FN.strip('\n') + '''


def classify(label: Label, hints: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:''')

# deck + hat checks before the length guard (deck callouts are long sentences)
rep('''    text = label.text
    upper = text.upper()
    # A designation inside a sentence (notes, schedule cells) is a
    # reference, not a member on the plan.
    if len(text) > 44:
        return None
    spacing = spacing_inches(text)''', '''    text = label.text
    upper = text.upper()
    if len(text) <= 90:
        deck = deck_info(text)
        if deck and not D._AISC_RE.search(text) and not D._SSMA_RE.search(text):
            return deck
    # A designation inside a sentence (notes, schedule cells) is a
    # reference, not a member on the plan.
    if len(text) > 44:
        return None
    spacing = spacing_inches(text)
    if _HAT_RE.search(text):
        hm = re.search(r"(\\d+/\\d+|\\d+(?:\\.\\d+)?)\\s*(?:\\"|IN\\.?)?\\s*(?:DEEP\\s+)?(?:HAT|FURRING)", upper)
        des = f'{hm.group(1)}" HAT CHANNEL' if hm else "HAT CHANNEL"
        return {"category": "joists" if spacing is not None else "other", "designation": des, "spacing_in": spacing, "series": spacing is not None, "role": "Hat Channel"}''')

# SJI joists carry their role
rep('''            series = spacing is not None
            cat = "trusses" if _TRUSS_WORD_RE.search(text) else "joists"
            return {"category": cat, "designation": des, "spacing_in": spacing, "series": series}''',
    '''            series = spacing is not None
            cat = "trusses" if _TRUSS_WORD_RE.search(text) else "joists"
            return {"category": cat, "designation": des, "spacing_in": spacing, "series": series, "role": "Steel Joist" if cat == "joists" else None}''')

# series items keep the role from classify
rep('''                        "confidence": 0.6 if generated else 0.8,
                        "source": info.get("source") or "rules",
                    })''', '''                        "confidence": 0.6 if generated else 0.8,
                        "source": info.get("source") or "rules",
                        "role": info.get("role"),
                    })''')

# decks: one area per callout, the bay it sits in
rep('''    # Walls by tag.
    if "walls" in wanted:''', '''    # Metal deck areas (OE-DELIVERY 2026-11-03-auto-takeoff-members).
    if "areas" in wanted:
        for lab, info in labels_by_cat.get("areas", []):
            if info.get("role") != "Deck":
                continue
            poly = _deck_region(lab, model)
            if not poly:
                continue
            items.append({
                "key": _key(p, "areas", info["designation"], lab.cx, lab.cy),
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
                "confidence": 0.6,
                "source": info.get("source") or "rules",
                "role": "Deck",
                "profile": info.get("deck_type"),
            })

    # Walls by tag.
    if "walls" in wanted:''')

# roles: shear walls, LB/NLB headers + jambs, CFS joists, steel joists, decks, hats
rep('''def wall_role(tag: str, spec: str | None) -> str:
    text = spec or ""
    if _NLB_RE.search(text):''', '''def wall_role(tag: str, spec: str | None) -> str:
    text = spec or ""
    if re.search(r"SHEAR", text, re.IGNORECASE) or re.match(r"^SW", tag.upper()):
        return "Shear Wall"
    if _NLB_RE.search(text):''')
rep('''    if t.startswith(("EW", "LW", "BW", "SW")):
        return "Load Bearing Wall"''', '''    if t.startswith(("EW", "LW", "BW")):
        return "Load Bearing Wall"''')
rep('''        elif cat == "joists":
            if re.search(r"CEIL", text, re.IGNORECASE) or ctx == "ceiling":''', '''        elif role in ("Steel Joist", "Hat Channel", "Deck"):
            pass
        elif cat == "joists" and D._JOIST_RE.search(des):
            role = "Steel Joist"
        elif cat == "joists" and D._SSMA_RE.search(des):
            role = "CFS Joist"
        elif cat == "joists":
            if re.search(r"CEIL", text, re.IGNORECASE) or ctx == "ceiling":''')
rep('''        it["role"] = role
        prof = profile_of(spec) if (spec and not profile_of(des)) else None
        if prof:
            it["profile"] = prof
''', '''        it["role"] = role
        prof = profile_of(spec) if (spec and not profile_of(des)) else None
        if prof and not it.get("profile"):
            it["profile"] = prof
    _bearing_of_openings(items)


def _seg_dist(px: float, py: float, a: list[float], b: list[float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / L2))
    return math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


def _bearing_of_openings(items: list[dict[str, Any]]) -> None:
    """Headers / jambs take the wall they sit in: load bearing (incl. shear)
    or non-load bearing. With no wall nearby, heavy members (54 mil +) are
    taken as load bearing."""
    walls = [w for w in items if w["category"] == "walls" and len(w.get("points") or []) >= 2]
    for it in items:
        if it.get("role") not in ("Header", "Jamb"):
            continue
        pts = it.get("points") or [it.get("anchor")]
        px = sum(q[0] for q in pts) / len(pts)
        py = sum(q[1] for q in pts) / len(pts)
        best = None
        for w in walls:
            d = _seg_dist(px, py, w["points"][0], w["points"][-1])
            if d <= 40 and (best is None or d < best[0]):
                best = (d, w.get("role"))
        if best:
            bearing = best[1] in ("Load Bearing Wall", "Shear Wall")
        else:
            prof = it.get("profile") or it.get("designation") or ""
            m = re.search(r"\\d{3,4}[SLT]\\d{3}-(\\d{2,3})", str(prof))
            bearing = (int(m.group(1)) >= 54) if m else True
        it["role"] = ("Load Bearing " if bearing else "Non-Load Bearing ") + it["role"]
''')
P.write_text(s, encoding='utf-8')
print('ok')
