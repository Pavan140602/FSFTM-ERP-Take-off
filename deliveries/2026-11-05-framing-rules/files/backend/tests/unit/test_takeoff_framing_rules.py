# OE-DELIVERY: 2026-11-05-framing-rules
"""Unit tests for the house framing rules (sheet kinds, schedules, tag rules,
trusses framed from a leader, holdown / base plate counts)."""

from __future__ import annotations

import math

from app.modules.takeoff import auto_takeoff as A
from app.modules.takeoff import framing_rules as R

BLACK = (0, 0, 0)


def seg(x1, y1, x2, y2, width=0.24, pen=BLACK):
    return (x1, y1, x2, y2, math.hypot(x2 - x1, y2 - y1), width, pen)


def lab(text, x0, y0, x1, y1, angle=0.0, size=8.0):
    rad = math.radians(angle)
    return A.Label(text, (x0, y0, x1, y1), angle, size, math.cos(rad), math.sin(rad))


WALL_ROWS = [
    ["W1 - WALL FRAMING SCHEDULE", "", "", ""],
    ["LEVEL", "FRAMING", "SPACING (IN)", "HEIGHT (FT-IN)"],
    ["4TH TO ROOF", "600S162-33 (50)", "24", "9'-7 1/4''"],
    ["3RD TO 4TH", "600S162-43 (50)", "24", "9'-7 1/4''"],
    ["2ND TO 3RD", "600S200-54 (50)", "24", "9'-7 1/4''"],
    ["1ST TO 2ND", "600S200-68 (50)", "24", "12'-7 1/4\""],
]
TRUSS_ROWS = [
    ["CFMF TRUSS SCHEDULE", "", "", "", ""],
    ["DESIGNATION", "FRAMING", "SPACING (IN)", "HEIGHT (IN)", "LENGTH (FT-IN)"],
    ["T-1", "362S162-33 (50)", "24", "16", "13'-0\""],
    ["RT-1", "362S162-54 (50)", "24", "16", "29'-0\""],
]


def schedules():
    parts = []
    for title, rows in (("W1 - WALL FRAMING SCHEDULE", WALL_ROWS), ("CFMF TRUSS SCHEDULE", TRUSS_ROWS)):
        parsed = R.parse_schedule_table(title, rows)
        assert parsed is not None
        parts.append({parsed["kind"]: parsed["entries"]})
    return R.merge_schedules(parts)


def test_sheet_kind_and_level_from_titles():
    assert R.sheet_kind(["2ND FLOOR FRAMING PLAN"]) == ("framing", 2)
    assert R.sheet_kind(["ROOF FRAMING PLAN"])[0] == "roof"
    assert R.sheet_kind(["FOUNDATION PLAN"]) == ("foundation", 0)
    # title broken over two lines in the title block
    assert R.sheet_kind(["S207", "3RD FLOOR SHEAR", "WALL PLAN"]) == ("walls", 3)
    assert R.sheet_kind(["TRUSS DETAILS"]) == (None, None)


def test_wall_schedule_rows_by_level():
    fs = schedules()
    w1 = fs["wall"]["W1"]
    row = R.level_row(w1, 1)
    assert row["level"] == "1ST TO 2ND" and row["framing"] == "600S200-68 (50)"
    assert R.level_row(w1, 3)["level"] == "3RD TO 4TH"
    assert abs(R.feet_inches(row["height"]) - (12 + 7.25 / 12)) < 1e-6
    assert fs["truss"]["T1"]["length"] == "13'-0\""


def test_rules_per_sheet_kind():
    fs = schedules()
    walls1 = ("walls", 1, fs)
    w = R.rule_classify("W1", walls1)
    assert w["category"] == "walls" and w["rule_profile"] == "600S200-68 (50)" and w["rule_level"] == "1ST TO 2ND"
    # the 3rd floor plan takes the 3RD TO 4TH row
    assert R.rule_classify("W1", ("walls", 3, fs))["rule_profile"] == "600S162-43 (50)"
    assert R.rule_classify("HD", walls1)["count_role"] == "Holdown"
    assert R.rule_classify("BRACE-X1", walls1)["count_role"] == "Steel Brace"
    assert R.rule_classify("T-1", walls1) == "skip"  # trusses belong to the framing plan
    stacked = R.rule_classify("SW-1 W1", walls1)
    assert stacked["role"] == "Shear Wall" and stacked["wall_type"] == "W1"

    framing2 = ("framing", 2, fs)
    t = R.rule_classify("T-1", framing2)
    assert t["category"] == "trusses" and t["series"] and t["spacing_in"] == 24 and t["rule_profile"] == "362S162-33 (50)"
    assert abs(t["length_ft"] - 13.0) < 1e-6
    assert R.rule_classify("W1", framing2) == "skip"  # walls belong to the wall plan
    assert R.rule_classify("HD", framing2) == "skip"

    found = ("foundation", 0, fs)
    assert R.rule_classify("BP-1", found)["count_role"] == "Base Plate"
    assert R.rule_classify("HSS6X6X1/4", found)["category"] == "columns"
    assert R.rule_classify("WF3.5", found) == "skip"  # no footings


def test_post_process_keeps_only_the_sheet_kind():
    items = [
        {"category": "walls", "role": "Load Bearing Wall", "rule_height": "12'-7 1/4\"", "rule_level": "1ST TO 2ND (2)", "rule_profile": "600S200-68 (50)"},
        {"category": "beams", "role": "Beam"},
        {"category": "other", "role": "Holdown"},
        {"category": "other", "role": "Angle"},
    ]
    out = R.post_process(items, "walls", 1, {})
    assert [i["role"] for i in out] == ["Load Bearing Wall", "Holdown"]
    assert out[0]["level"] == "1ST TO 2ND" and out[0]["profile"] == "600S200-68 (50)"
    assert abs(out[0]["height_ft"] - 12.6042) < 1e-3


def test_trusses_framed_from_tag_leader_at_schedule_spacing():
    # Bay 13 ft wide (x 0..117 at 9 units/ft), 29 ft deep (y 0..261).
    # Distribution arrow across the bay, span line along it, tag with a
    # leader to where they cross.
    segments = [
        seg(10, 100, 107, 100),  # distribution (arrow body)
        seg(107, 100, 117, 97), seg(107, 100, 117, 103),  # arrowhead to the wall
        seg(10, 100, 0, 97), seg(10, 100, 0, 103),
        seg(50, 5, 50, 256),  # span line
        seg(50, 256, 50, 261), seg(50, 5, 50, 0),  # half arrows to the walls
        seg(50, 100, 66, 116),  # leader
    ]
    m = A.PageModel(1, 400, 400, [], segments, [], [], 9.0, '1/8" = 1\'-0"')
    m.index = A.SegIndex(segments)
    m.fine = segments
    m.fine_index = A.SegIndex(segments)
    tag = lab("RT-1", 66, 114, 90, 124)
    info = {"spacing_in": 24.0, "length_ft": 29.0, "rule_profile": "x"}
    lines, generated, bay = A._series_from_leader(tag, info, m)
    assert generated and len(lines) == 7  # 13 ft bay at 24" o.c.
    for ln in lines:
        assert abs(ln[0] - ln[2]) < 1e-6  # members run along the span line
        assert abs(abs(ln[3] - ln[1]) - 261) < 1.0  # wall to wall


def test_document_schedule_titles_skip_note_references():
    class FakePage:
        def get_text(self, kind):
            def line(text, size, y):
                return {"bbox": (0, y, 100, y + 10), "spans": [{"text": text, "size": size}]}

            return {"blocks": [{"lines": [
                line("CFMF TRUSS SCHEDULE", 15.8, 0),
                line("SEE SCHEDULE FOR STIRRUPS", 9.6, 20),
                line("REF. SCHEDULE", 16.0, 40),
                line("W1 - WALL FRAMING SCHEDULE", 15.8, 60),
            ]}]}

    titles = [t for t, _r in R.schedule_titles(FakePage())]
    assert titles == ["CFMF TRUSS SCHEDULE", "W1 - WALL FRAMING SCHEDULE"]
