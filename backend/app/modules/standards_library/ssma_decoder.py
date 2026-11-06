# OE-DELIVERY: 2026-10-29-standards-library-v1
# SSMA designation decoder — Standards Library seed component.
# Decodes SSMA (Steel Stud Manufacturers Association) member designations such as
# 600S162-54 into geometry: web depth, style, flange width, and steel thickness.
# Format: <depth x100><style><flange x100>-<mil>
#   depth / flange are in 1/100 inch; mil is the minimum base steel thickness in
#   1/1000 inch (95 percent of the design thickness).

import re

# mil -> SSMA design thickness in inches (SSMA Technical Guide / ICC-ES ESR-3064).
MIL_DESIGN_THICKNESS_IN = {
    18: 0.0188,
    27: 0.0283,
    30: 0.0312,
    33: 0.0346,
    43: 0.0451,
    54: 0.0566,
    68: 0.0713,
    97: 0.1017,
    118: 0.1242,
}

# Approximate sheet-steel gauge for each mil value (estimating convenience only).
MIL_GAUGE_LABEL = {
    118: "12 ga",
    97: "12 ga",
    68: "14 ga",
    54: "16 ga",
    43: "18 ga",
    33: "20 ga (structural)",
    30: "20 ga (drywall)",
    27: "22 ga",
    18: "25 ga",
}

STYLE_NAMES = {
    "S": "Stud / joist (C-section)",
    "T": "Track",
    "U": "Channel",
    "F": "Furring channel",
    "SFS": "Supreme framing stud",
    "SFT": "Supreme framing track",
}

_DESIGNATION_RE = re.compile(
    r"^\s*(\d{3,4})\s*(SFS|SFT|S|T|U|F)\s*(\d{3})\s*-\s*(\d{2,3})\s*$",
    re.IGNORECASE,
)


def design_thickness_in(mil):
    """Design thickness (inches) for an SSMA mil value."""
    if mil in MIL_DESIGN_THICKNESS_IN:
        return MIL_DESIGN_THICKNESS_IN[mil]
    # Fallback: mil is 95 percent of the design thickness.
    return round(mil / 950.0, 4)


def decode_ssma(designation):
    """Decode an SSMA designation. Returns a dict, or None if it does not parse."""
    if not designation:
        return None
    m = _DESIGNATION_RE.match(str(designation))
    if not m:
        return None
    depth, style, flange, mil = int(m.group(1)), m.group(2).upper(), int(m.group(3)), int(m.group(4))
    t = design_thickness_in(mil)
    return {
        "designation": "%d%s%03d-%d" % (depth, style, flange, mil),
        "depth_in": depth / 100.0,
        "style": style,
        "style_name": STYLE_NAMES[style],
        "flange_in": flange / 100.0,
        "mil": mil,
        "design_thickness_in": t,
        "min_thickness_in": round(0.95 * t, 4),
        "gauge_label": MIL_GAUGE_LABEL.get(mil),
    }


if __name__ == "__main__":
    cases = {
        "600S162-54": (6.0, "S", 1.62, 0.0566, "16 ga"),
        "362S162-33": (3.62, "S", 1.62, 0.0346, "20 ga (structural)"),
        "1200T300-97": (12.0, "T", 3.0, 0.1017, "12 ga"),
        "800S200-68": (8.0, "S", 2.0, 0.0713, "14 ga"),
        "250U200-18": (2.5, "U", 2.0, 0.0188, "25 ga"),
    }
    for text, (dep, sty, fla, thi, gau) in cases.items():
        d = decode_ssma(text)
        assert d is not None, text
        assert d["depth_in"] == dep and d["style"] == sty and d["flange_in"] == fla, (text, d)
        assert d["design_thickness_in"] == thi and d["gauge_label"] == gau, (text, d)
        print("OK", text, "->", d["style_name"], d["depth_in"], "in deep,", d["flange_in"], "in flange,", d["design_thickness_in"], "in,", gau)
    assert decode_ssma("W10X26") is None
    assert decode_ssma("600S162") is None
    print("decoder self-test passed")
