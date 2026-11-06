"""Detail (zoom) scan for columns and beams (OE-DELIVERY 2026-11-06-zoom-scan).

Synthetic sheets drawn with PyMuPDF: each test draws the case found on a
real drawing set (AC Retreat S2.01b / S4.01a, Home2 Suites S-6.02)."""

from __future__ import annotations

import math

import pymupdf

from app.modules.takeoff import auto_takeoff as A
from app.modules.takeoff import detail_scan as Z


def _page(w: float = 1200, h: float = 800):
    doc = pymupdf.open()
    return doc, doc.new_page(width=w, height=h)


def _square(page, cx: float, cy: float, side: float, angle: float = 0.0, width: float = 0.72, fill=None) -> None:
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    pts = []
    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = dx * side / 2, dy * side / 2
        pts.append(pymupdf.Point(cx + x * c - y * s, cy + x * s + y * c))
    sh = page.new_shape()
    sh.draw_polyline(pts + [pts[0]])
    sh.finish(color=(0, 0, 0), width=width, fill=fill, closePath=True)
    sh.commit()


def _line(page, a, b, width: float = 1.68, color=(0, 0, 0)) -> None:
    page.draw_line(pymupdf.Point(*a), pymupdf.Point(*b), color=color, width=width)


def _model(page):
    return A.build_page_model(page, 1)


def _scan(model, found=()):
    return Z.scan_columns(
        model,
        model.detail,
        [{"point": p} for p in found],
        [],
        lambda x, y: {"designation": "COLUMN", "label": "COLUMN", "mark": None, "label_rect": None, "mark_obj": None, "label_obj": None},
        col_mark_re=A._COL_MARK_RE,
    )


def test_rotated_square_with_members_is_a_column() -> None:
    doc, page = _page()
    _square(page, 600, 400, 11, angle=33)
    # Two beams frame into it from different directions.
    _line(page, (600 + 12, 400), (760, 400))
    _line(page, (600, 400 + 12), (600, 560))
    added, removed, stats = _scan(_model(page))
    assert len(added) == 1 and not removed
    x, y = added[0]["point"]
    assert abs(x - 600) < 1.5 and abs(y - 400) < 1.5
    assert stats["tiles"] > 1


def test_square_drawn_as_loose_pieces_in_any_order() -> None:
    doc, page = _page()
    # Outline written piece by piece, out of order and reversed (CAD export).
    sh = page.new_shape()
    for a, b in (((300, 200), (311, 200)), ((300, 211), (300, 200)), ((311, 211), (300, 211)), ((311, 200), (311, 211))):
        sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
    sh.finish(color=(0, 0, 0), width=0.72)
    sh.commit()
    ds = Z.read_sheet(page, index_cls=A.SegIndex)
    assert any(abs(s.cx - 305.5) < 0.6 and abs(s.cy - 205.5) < 0.6 and s.kind == "square" for s in ds.shapes)


def test_deck_arrow_body_is_not_a_column_and_is_removed() -> None:
    doc, page = _page()
    for cy in (200, 300, 400):
        # Filled arrow: a black block with a black head touching it.
        page.draw_rect(pymupdf.Rect(500, cy - 9, 528, cy + 9), color=None, fill=(0, 0, 0))
        sh = page.new_shape()
        sh.draw_polyline([pymupdf.Point(500, cy - 16), pymupdf.Point(480, cy), pymupdf.Point(500, cy + 16)])
        sh.finish(color=None, fill=(0, 0, 0), closePath=True)
        sh.commit()
    model = _model(page)
    added, removed, _ = _scan(model, found=[(514, 200), (514, 300), (514, 400)])
    assert not added
    assert removed == {0, 1, 2}


def test_text_mask_is_not_a_column() -> None:
    doc, page = _page()
    for x in (300, 500, 700):
        page.draw_rect(pymupdf.Rect(x - 5, 395, x + 5, 405), color=None, fill=(1, 1, 1))
        page.insert_text(pymupdf.Point(x - 30, 403), "1200S200-54 @ 4'-0\" o.c.", fontsize=7)
        _line(page, (x, 300), (x, 500), width=1.0)
    added, _removed, _ = _scan(_model(page))
    assert not added


def test_curved_beam_is_traced_column_to_column() -> None:
    doc, page = _page()
    _square(page, 300, 500, 11)
    _square(page, 500, 300, 11)
    # Quarter arc from (306, 500) round to (500, 306), centre (500, 500).
    sh = page.new_shape()
    sh.draw_curve(pymupdf.Point(306, 500), pymupdf.Point(306, 306), pymupdf.Point(500, 306))
    sh.finish(color=(0, 0, 0), width=1.68, closePath=False)
    sh.commit()
    page.insert_text(pymupdf.Point(330, 380), "W33X130", fontsize=8)
    model = _model(page)
    labs = A.labels_by_category(model).get("beams", [])
    assert labs
    cols = [(300.0, 500.0, 11.0), (500.0, 300.0, 11.0)]
    out, stats = Z.scan_beams(model, model.detail, labs, [], cols)
    assert stats["labelled_added"] == 1
    pts = out[0]["points"]
    assert len(pts) > 2  # follows the curve
    ends = {(round(p[0]), round(p[1])) for p in (pts[0], pts[-1])}
    assert ends == {(300, 500), (500, 300)}
    # Arc length, not the chord.
    assert Z.poly_len(pts) > 1.05 * math.hypot(200, 200)


def test_line_break_is_bridged() -> None:
    doc, page = _page()
    _line(page, (300, 400), (390, 400))
    _line(page, (398, 400), (500, 400))  # a drafting gap
    model = _model(page)
    ds = model.detail
    seed = next(i for i, s in enumerate(ds.segs) if abs(s[0] - 300) < 0.5 and abs(s[1] - 400) < 0.5)
    pts = Z._trace(ds, seed, [], set(), gap=11.0)
    xs = sorted(p[0] for p in pts)
    assert xs[0] <= 300.5 and xs[-1] >= 499.5


def test_sheet_split_into_parts_covers_it_once() -> None:
    doc, page = _page(1200, 800)
    for k in range(40):
        _line(page, (60 + k * 25, 60), (60 + k * 25, 700), width=0.5)
    model = _model(page)
    model.units_per_foot = 9.0
    for n in (4, 6, 9):
        parts = Z.plan_parts(model, n)
        assert len(parts) == n
        # Every point of the sheet belongs to exactly one part's core.
        for x, y in ((5, 5), (600, 400), (1100, 790), (300, 650)):
            assert sum(1 for pt in parts if Z.in_core(pt, x, y)) == 1
        # Zoom areas overlap their neighbours (members on the cut are seen whole).
        if n > 1:
            a, b = parts[0]["zoom"], parts[1]["zoom"]
            assert a[2] > b[0] or a[3] > b[1]
    assert len(Z.plan_parts(model, 0)) >= 4


def test_joist_callout_framed_at_its_spacing() -> None:
    doc, page = _page()
    upf = 9.0  # 1/8" = 1'-0"
    # Joists at 16" (12 units) between two beams, then a wider gap.
    for k in range(8):
        _line(page, (300 + k * 12, 200), (300 + k * 12, 420), width=0.5)
    _line(page, (300 + 8 * 12 + 60, 200), (300 + 8 * 12 + 60, 420), width=0.5)  # next bay
    page.insert_text(pymupdf.Point(330, 300), "J-1", fontsize=8, rotate=90)
    model = _model(page)
    model.units_per_foot = upf
    lab = next(lb for lb in model.labels if lb.text.strip() == "J-1")
    info = {"category": "joists", "designation": "J-1", "spacing_in": 16.0, "series": True}
    out, stats = Z.scan_joists(model, model.detail, [(lab, info)], [], Z.plan_parts(model, 4))
    assert stats["callouts_framed"] == 1
    xs = sorted(round((ln[0] + ln[2]) / 2) for ln in out[0]["lines"])
    assert xs == [300 + k * 12 for k in range(8)]  # stops where the spacing breaks


def test_deck_legend_tags() -> None:
    doc, page = _page()
    page.insert_text(pymupdf.Point(900, 600), "DECK LEGEND", fontsize=9)
    page.insert_text(pymupdf.Point(900, 630), "AD", fontsize=8)
    page.insert_text(pymupdf.Point(940, 628), '3" DEEP, 18 GA. COMPOSITE STEEL DECK', fontsize=7)
    page.insert_text(pymupdf.Point(300, 300), "AD", fontsize=8)
    model = _model(page)
    tags, boxes = Z.deck_legend(model, A.deck_info)
    assert "AD" in tags and tags["AD"]["role"] == "Deck"
    plan_tag = next(lb for lb in model.labels if lb.text.strip() == "AD" and lb.cx < 500)
    assert not A._in_rects(plan_tag.cx, plan_tag.cy, boxes, 2)


def test_column_label_finds_symbol_at_end_of_its_text_line() -> None:
    doc, page = _page()
    # Home2 S-1.00: the size is written on a short leader line whose end
    # touches the column symbol; no other leader.
    _square(page, 304, 400, 8)
    _line(page, (310, 400), (370, 400), width=0.25)
    page.insert_text(pymupdf.Point(312, 398), "HSS10X10X5/8", fontsize=8)
    # A beam size printed along a long beam line is not a column label.
    _line(page, (300, 600), (700, 600), width=1.7)
    _square(page, 296, 600, 8)
    page.insert_text(pymupdf.Point(450, 597), "W24X84", fontsize=8)
    model = _model(page)
    model.units_per_foot = 9.0
    out, checked = Z.label_columns(model, model.detail, [])
    pts = [(round(o["point"][0]), round(o["point"][1])) for o in out]
    assert (304, 400) in pts
    assert all(abs(y - 600) > 5 for _x, y in pts)


def test_column_symbol_size_and_turn() -> None:
    doc, page = _page()
    # A rectangular tube drawn turned 30 degrees: 16 x 8 units.
    a = math.radians(30)
    c, s_ = math.cos(a), math.sin(a)
    pts = [pymupdf.Point(500 + x * c - y * s_, 300 + x * s_ + y * c) for x, y in ((-8, -4), (8, -4), (8, 4), (-8, 4))]
    sh = page.new_shape()
    sh.draw_polyline(pts + [pts[0]])
    sh.finish(color=(0, 0, 0), width=0.7, closePath=True)
    sh.commit()
    model = _model(page)
    sym = Z.symbol_at(model.detail, 500, 300)
    assert sym is not None
    assert abs(sym[0] - 16) < 0.6 and abs(sym[1] - 8) < 0.6
    assert abs(((sym[2] - 30) + 90) % 180 - 90) < 1.5


if __name__ == "__main__":  # pytest is not installed in the dev venv
    import sys

    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(exc))
    sys.exit(1 if fails else 0)
