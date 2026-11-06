from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\auto_takeoff.py")
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('''        text = " ".join(str(it.get(k) or "") for k in ("spec", "rule_spacing", "label"))
        sp_in = spacing_inches(text) or DEFAULT_STUD_SPACING_IN''', '''        text = " ".join(str(it.get(k) or "") for k in ("spec", "rule_spacing", "label"))
        sp_in = stud_spacing_in(text) or DEFAULT_STUD_SPACING_IN''')
rep('''                    f"Header area of wall {it['designation']} ({_fmt_in((t1 - t0) / upf * 12.0)} opening)"''',
    '''                    f"Header area of wall {it['designation']} ({_fmt_in(round((t1 - t0) / upf * 12.0 * 8) / 8)} opening)"''')
rep('''DEFAULT_STUD_SPACING_IN = 24.0
''', r'''DEFAULT_STUD_SPACING_IN = 24.0
# Stud spacings a framing plan uses; anything else written "@ x O.C." in a
# wall's notes is screw / nail spacing (#8 @ 4" O.C.), not studs.
_STUD_SPACINGS = (12.0, 16.0, 19.2, 24.0)
_OC_RE = re.compile(r"@\s*(\d+(?:\.\d+)?)\s*(\"|''|IN\b|INCH)?\s*O\.?\s*C", re.IGNORECASE)


def stud_spacing_in(text: str) -> float | None:
    """Stud spacing written on the plan / schedule ("600S200-68 @ 24\" O.C."),
    in inches; a screw spacing in the same note is skipped."""
    for m in _OC_RE.finditer(text or ""):
        v = float(m.group(1))
        if m.group(2) is None and v <= 4:
            v *= 12.0  # "@ 2 O.C." with no unit: feet
        for sp in _STUD_SPACINGS:
            if abs(v - sp) < 0.05:
                return sp
    return None
''')
p.write_text(s, encoding="utf-8")
print("ok")
