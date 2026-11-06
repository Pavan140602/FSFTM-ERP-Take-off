# OE-DELIVERY: 2026-11-02-auto-takeoff
"""Unit tests for the Auto Takeoff engine (pure geometry, no PDF needed)."""

from __future__ import annotations

from app.modules.takeoff import auto_takeoff as A
from app.modules.takeoff import auto_takeoff_ai as X

BLACK = (0, 0, 0)
GREY = (17, 17, 17)


def seg(x1, y1, x2, y2, width=1.0, pen=BLACK):
    import math

    return (x1, y1, x2, y2, math.hypot(x2 - x1, y2 - y1), width, pen)


def model(labels, segments, boxes=(), upf=9.0):
    m = A.PageModel(1, 2000, 1400, list(labels), list(segments), list(boxes), [], upf, '1/8" = 1\'-0"')
    m.index = A.SegIndex(m.segments)
    return m


def lab(text, x0, y0, x1, y1, angle=0.0, size=8.0):
    import math

    rad = math.radians(angle)
    return A.Label(text, (x0, y0, x1, y1), angle, size, math.cos(rad), math.sin(rad))


def test_spacing_inches_reads_feet_inches_and_inches():
    assert A.spacing_inches("1200S200-54 @ 4' - 0\" o.c.") == 48
    assert A.spacing_inches('T1 @ 24" O.C.') == 24
    assert A.spacing_inches("W12X26") is None


def test_classify_categories():
    assert A.classify(lab("W12X26", 0, 0, 40, 8))["category"] == "beams"
    assert A.classify(lab("L2X2X3/8", 0, 0, 40, 8))["category"] == "other"
    j = A.classify(lab("18K4 @ 5'-0\" O.C.", 0, 0, 60, 8))
    assert j["category"] == "joists" and j["series"] and j["spacing_in"] == 60
    c = A.classify(lab("1200S200-54 @ 4' - 0\" o.c.", 0, 0, 90, 8))
    assert c["category"] == "joists" and c["series"]
    assert A.classify(lab("SW-4", 0, 0, 20, 8))["category"] == "walls"
    assert A.classify(lab("T001", 0, 0, 20, 8))["category"] == "trusses"
    # Sheet numbers and long note sentences are not members.
    assert A.classify(lab("S-1", 0, 0, 20, 8)) is None
    long_note = "PROVIDE W12X26 AT ALL TYPICAL LOCATIONS SHOWN ON THE PLANS AND SECTIONS"
    assert A.classify(lab(long_note, 0, 0, 300, 8)) is None


def test_ai_hint_can_veto_and_classify():
    hints = {"A3": {"category": "walls", "designation": "A3", "spacing_in": None, "spec": "6in stud"}, "SW-1": {"category": "ignore"}}
    assert A.classify(lab("A3", 0, 0, 10, 8), hints)["category"] == "walls"
    assert A.classify(lab("SW-1", 0, 0, 20, 8), hints) is None


def test_fragments_merge_along_baseline():
    parts = [lab("1200S200-54", 100, 100, 157, 109), lab("@", 160, 100, 169, 109), lab("4' - 0\" o.c.", 172, 100, 214, 109)]
    merged = A._merge_fragments(parts)
    assert len(merged) == 1 and merged[0].text.startswith("1200S200-54 @ 4'")


def test_beam_label_ties_to_its_line_not_the_grey_grid():
    beam = seg(100, 200, 500, 200, width=1.7)
    grid = [seg(x, 201, x + 36, 201, width=0.24, pen=GREY) for x in range(0, 900, 63)]
    m = model([lab("W12X26", 280, 190, 320, 197)], [beam, *grid])
    out = A.take_off_page(m, ["beams"])
    lines = [i for i in out["items"] if i["category"] == "beams"]
    assert len(lines) == 1
    (x1, _y1), (x2, _y2) = lines[0]["points"]
    assert min(x1, x2) == 100 and max(x1, x2) == 500  # did not run along the grid


def test_shared_run_is_split_between_labels():
    run = seg(0, 300, 900, 300, width=1.5)
    support = seg(450, 250, 450, 350, width=1.5)
    labels = [lab("W12X26", 200, 290, 240, 297), lab("W16X31", 650, 290, 690, 297)]
    out = A.take_off_page(model(labels, [run, support]), ["beams"])
    items = sorted(out["items"], key=lambda i: i["anchor"][0])
    assert [i["designation"] for i in items] == ["W12X26", "W16X31"]
    assert max(p[0] for p in items[0]["points"]) == 450
    assert min(p[0] for p in items[1]["points"]) == 450


def test_joist_series_from_distribution_arrow():
    # Bay 0..400 wide, joists vertical every 36 units (4 ft at 1/8"), a
    # horizontal arrow line under the callout spans the series.
    joists = [seg(x, 100, x, 500) for x in range(40, 400, 36)]
    arrow = seg(40, 300, 364, 300, width=0.3)
    callout = lab("1200S200-54 @ 4' - 0\" o.c.", 120, 286, 280, 295)
    out = A.take_off_page(model([callout], [*joists, arrow]), ["joists", "areas"])
    joist_items = [i for i in out["items"] if i["category"] == "joists"]
    assert len(joist_items) == len(joists)
    assert all(not i["generated"] for i in joist_items)
    assert any(i["category"] == "areas" for i in out["items"])


def test_keys_are_stable_between_runs():
    beam = seg(100, 200, 500, 200, width=1.7)
    m1 = model([lab("W12X26", 280, 190, 320, 197)], [beam])
    m2 = model([lab("W12X26", 280, 190, 320, 197)], [beam])
    k1 = [i["key"] for i in A.take_off_page(m1, ["beams"])["items"]]
    k2 = [i["key"] for i in A.take_off_page(m2, ["beams"])["items"]]
    assert k1 == k2 and k1


def test_dedupe_drops_identical_lines():
    item = {"category": "joists", "kind": "line", "points": [[0, 0], [100, 0]]}
    flipped = {"category": "joists", "kind": "line", "points": [[100, 1], [0, 1]]}
    assert len(A._dedupe_items([item, flipped])) == 1


def test_parse_hints_and_vision_labels():
    hints, specs = X.parse_hints({
        "labels": [{"text": "T 10", "category": "trusses", "designation": "T10", "spacing_in": 24}, {"text": "x", "category": "bogus"}],
        "wall_types": {"W1": "6in metal stud"},
    })
    assert hints["T10"]["category"] == "trusses" and "X" not in hints
    assert specs == {"W1": "6in metal stud"}
    labels = X.labels_from_vision({"labels": [{"text": "W12X26", "box": [0.1, 0.2, 0.12, 0.3], "angle": 90}]}, 1000, 1000)
    assert labels[0].angle == -90 and abs(labels[0].rect[0] - 100) < 1e-6


# ── column marks + schedule (OE-DELIVERY 2026-11-02-auto-takeoff-columns) ──


def _line(*words):
    from app.modules.takeoff import detect as D

    ln = D._Line()
    for text, x0, y0 in words:
        ln.add(text, (x0, y0, x0 + 8 * len(text), y0 + 9))
    return ln


def _sched_model(lines):
    m = A.PageModel(9, 0, 0, [], [], [], lines, None, None)
    return m


def test_column_schedule_row_form():
    lines = [_line(("MARK", 100, 100), ("SIZE", 200, 100)), _line(("C1", 100, 120), ("HSS8X8X1/2", 200, 120)), _line(("C2", 100, 140), ("W10X33", 200, 140))]
    assert A.column_schedule([_sched_model(lines)]) == {"C1": "HSS8X8X1/2", "C2": "W10X33"}


def test_column_schedule_column_form():
    lines = [
        _line(("C1", 100, 100), ("C2", 200, 100), ("C3", 300, 100)),
        _line(("HSS6X6X1/4", 85, 130), ("HSS8X8X3/8", 185, 130), ("W12X40", 290, 130)),
    ]
    assert A.column_schedule([_sched_model(lines)]) == {"C1": "HSS6X6X1/4", "C2": "HSS8X8X3/8", "C3": "W12X40"}


def test_column_named_from_mark_and_schedule():
    # Three column symbols on beam lines, each with a mark beside it.
    beam = seg(0, 200, 900, 200, width=1.7)
    boxes = [(x - 6, 194, x + 6, 206, False) for x in (100, 400, 700)]
    marks = [lab("C1", 110, 210, 122, 218), lab("C2", 410, 210, 422, 218), lab("C1", 710, 210, 722, 218)]
    out = A.take_off_page(model(marks, [beam], boxes), ["columns"], col_marks={"C1": "HSS8X8X1/2", "C2": "HSS6X6X1/4"})
    cols = sorted((i for i in out["items"] if i["category"] == "columns"), key=lambda i: i["anchor"][0])
    assert [c["designation"] for c in cols] == ["HSS8X8X1/2", "HSS6X6X1/4", "HSS8X8X1/2"]
    assert cols[0]["label"] == "C1 HSS8X8X1/2" and cols[0]["label_rect"]


# OE-DELIVERY 2026-11-03-auto-takeoff-roles
def test_wall_roles_from_schedule_text():
    from app.modules.takeoff.auto_takeoff import wall_role

    assert wall_role("SW-1", "600S162-97 SHEAR WALL") == "Load Bearing Wall"
    assert wall_role("W2", "362S125-33 NON-LOAD BEARING") == "Non-Load Bearing Wall"
    assert wall_role("W1", '6" METAL STUD WALL') == "Non-Load Bearing Wall"
    assert wall_role("EW1", None) == "Load Bearing Wall"
    assert wall_role("W9", "600S162-54") == "Load Bearing Wall"
    assert wall_role("W8", "362S125-30") == "Non-Load Bearing Wall"


def test_header_and_jamb_classification():
    from app.modules.takeoff.auto_takeoff import Label, classify

    def lab(t):
        return Label(text=t, rect=(0, 0, 40, 8), angle=0.0, size=6.0)

    assert classify(lab("(2) 600S162-54 JAMB"))["role"] == "Jamb"
    assert classify(lab("800S162-54 BOX HEADER"))["role"] == "Header"
    assert classify(lab("H2"))["role"] == "Header"
