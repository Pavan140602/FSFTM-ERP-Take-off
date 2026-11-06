"""Division 05 / CFS reading rules (OE-DELIVERY 2026-11-11-div5-rules).

Synthetic sheets drawn with PyMuPDF, each one a case read off a real set
(CFS 'Structural Approval Drawings REV-014': floor frame layout p12, wall
sections layout p24)."""

from __future__ import annotations

import pymupdf

from app.modules.takeoff import auto_takeoff as A
from app.modules.takeoff import bearing_walls as BW
from app.modules.takeoff import detail_scan as Z
from app.modules.takeoff import detect as D

UPF = 9.0  # 1/8" = 1'-0"


def _page(w: float = 1200, h: float = 800):
    doc = pymupdf.open()
    return doc, doc.new_page(width=w, height=h)


def _line(page, a, b, width: float = 0.5, color=(0, 0, 0)) -> None:
    page.draw_line(pymupdf.Point(*a), pymupdf.Point(*b), color=color, width=width)


def _model(page):
    m = A.build_page_model(page, 1)
    m.units_per_foot = UPF
    return m


def test_vocabulary_joist_girders_round_hss_pipe_kcs() -> None:
    lab = A.Label("44G8N9.5K", (0, 0, 60, 10), 0.0, 10.0, 1.0, 0.0)
    info = A.classify(lab)
    assert info and info["category"] == "beams" and info["role"] == "Joist Girder"
    assert D._AISC_RE.search("HSS6.625X0.280")
    assert D._AISC_RE.search("PIPE 4 STD")
    assert D._JOIST_RE.search("18KCS3") and D._JOIST_RE.search("24SLH10")


def test_bare_wall_code_is_not_deck() -> None:
    assert A.deck_info("1B") is None and A.deck_info("3A") is None
    assert A.deck_info('1.5" B 20GA') is not None
    assert A.deck_info("1 1/2\" TYPE B ROOF DECK") is not None


def test_joist_field_named_from_zone_mark_and_legend() -> None:
    doc, page = _page()
    pink = (1, 0.5, 0.5)
    # Twelve joists 30 ft long at 16" o.c. (12 pt), a truss across at 15 ft.
    for k in range(12):
        y = 150 + 12 * k
        _line(page, (100, y), (100 + 30 * UPF, y), width=0.24, color=pink)
    _line(page, (100 + 15 * UPF, 140), (100 + 15 * UPF, 300), width=0.72, color=(1, 0, 0))
    page.insert_text((150, 196), "JOIST 1", fontsize=9)
    page.insert_text((600, 650), '1x800S162-54 LGS FLOOR JOIST 1 @16" O.C', fontsize=7)
    page.insert_text((100, 760), "LGS FLOOR FRAME LAYOUT PLAN", fontsize=16)
    model = _model(page)
    fields = Z.joist_fields(model.detail, UPF)
    assert len(fields) == 1 and abs(fields[0]["pitch"] / UPF * 12 - 16.0) < 0.5
    items = A.field_joist_items([], model)
    assert items, "no joists taken off"
    assert {it["designation"] for it in items} == {"800S162-54"}
    assert all(it["spacing_in"] == 16.0 and it["label"] == "JOIST 1" for it in items)
    # Cut at the truss: two pieces per joist.
    assert len(items) == 24


def test_unnamed_parallel_lines_off_a_framing_sheet_are_not_joists() -> None:
    doc, page = _page()
    for k in range(10):
        y = 150 + 12 * k
        _line(page, (100, y), (100 + 30 * UPF, y), width=0.3)
    page.insert_text((100, 760), "FIRST FLOOR WALL ELEVATIONS", fontsize=16)
    model = _model(page)
    assert A.field_joist_items([], model) == []


def test_stair_flight_counts_treads() -> None:
    doc, page = _page()
    for k in range(9):  # 9 treads, 11" going, 4 ft wide
        y = 200 + 11 / 12 * UPF * k
        _line(page, (300, y), (300 + 4 * UPF, y), width=0.35)
    page.insert_text((310, 190), "UP", fontsize=7)
    model = _model(page)
    fl = Z.stair_flights(model)
    assert len(fl) == 1 and fl[0]["treads"] == 9 and abs(fl[0]["width_ft"] - 4.0) < 0.3
    st = A.stair_items(model)
    assert st and st[0]["role"] == "Stair" and st[0]["risers"] == 10


def _diamond(page, cx, cy, r=12, color=(1, 0, 1)) -> None:
    pts = [pymupdf.Point(cx, cy - r), pymupdf.Point(cx + r, cy), pymupdf.Point(cx, cy + r), pymupdf.Point(cx - r, cy)]
    sh = page.new_shape()
    sh.draw_polyline(pts + [pts[0]])
    sh.finish(color=color, width=0.24, closePath=True)
    sh.commit()


def test_wall_type_codes_in_diamonds_tag_walls() -> None:
    doc, page = _page()
    green = (0, 0.7, 0.3)
    # Two hairline double-line walls, 6" thick, 40 ft long.
    for y in (300, 500):
        _line(page, (100, y), (100 + 40 * UPF, y), width=0.24, color=green)
        _line(page, (100, y + 4.5), (100 + 40 * UPF, y + 4.5), width=0.24, color=green)
    # "2A" in a diamond above each, leader down to the wall face.
    for x, y in ((200, 300), (300, 500), (380, 500)):
        _diamond(page, x, y - 40)
        page.insert_text((x - 7, y - 36), "2A", fontsize=10)
        _line(page, (x, y - 28), (x, y), width=0.24, color=(1, 0, 1))
    page.insert_text((100, 700), "FIRST FLOOR WALL SECTIONS LAYOUT", fontsize=16)
    page.insert_text((100, 730), "SINGLE STUD 600S162-54", fontsize=12)
    page.insert_text((600, 700), "2A (1 HOUR FIRE RATED WALL)", fontsize=9)
    model = _model(page)
    tags = A.symbol_wall_tags(model)
    assert len(tags) == 3
    assert all(info["designation"] == "2A" and "600S162-54" in info["spec"] and "FIRE RATED" in info["spec"] for _l, info in tags)


def test_one_off_numbers_in_symbols_are_not_wall_types() -> None:
    doc, page = _page()
    for n, x in enumerate((200, 300, 400, 500), start=1):
        _diamond(page, x, 200)
        page.insert_text((x - 3, 204), str(n), fontsize=10)
        _line(page, (x, 212), (x, 260), width=0.24)
    page.insert_text((100, 700), "WALL LAYOUT PLAN", fontsize=16)
    model = _model(page)
    assert A.symbol_wall_tags(model) == []


def test_bearing_from_joists_above() -> None:
    # Joists run east-west at 16" o.c. over two walls: the north-south wall
    # carries them, the east-west wall runs alongside.
    joists = [((0.0, y * 16 / 12.0), (30.0, y * 16 / 12.0)) for y in range(15)]
    lb = {"category": "walls", "kind": "line"}
    nlb = {"category": "walls", "kind": "line"}
    walls = [(lb, (15.0, 0.0), (15.0, 18.0)), (nlb, (2.0, 8.5), (28.0, 8.5))]
    got = {id(it): v for it, v, _b, _a in BW.classify(walls, joists, 16 / 12.0, (0.0, 0.0))}
    assert got[id(lb)] == "Load Bearing Wall"
    assert got[id(nlb)] == "Non-Load Bearing Wall"


def _wall(x0, y0, x1, y1, role="Wall"):
    return {"category": "walls", "kind": "line", "segment": "wall", "role": role, "designation": "WALL",
            "points": [[x0, y0], [x1, y1]], "wall_width": 4.5, "spec": "Drawn wall with no wall tag"}


def test_default_roles_exterior_demising_partition() -> None:
    # A row of hotel rooms: outside wall along y=0 (and the ends), corridor
    # side not drawn, demising walls every 13 ft running 25 ft in, a short
    # closet partition inside one room.
    u = UPF
    items = [_wall(0, 0, 80 * u, 0), _wall(0, 0, 0, 25 * u), _wall(80 * u, 0, 80 * u, 25 * u)]
    for k in range(1, 6):
        items.append(_wall(13 * k * u, 0, 13 * k * u, 25 * u))
    closet = _wall(3 * u, 10 * u, 8 * u, 10 * u)
    items.append(closet)
    model = A.PageModel(1, 1200, 800, [], [], [], [], UPF, None)
    A.default_wall_roles(items, model)
    assert items[0]["role"] == "Load Bearing Wall" and items[0]["profile"] == "600S162-54"
    assert all(w["role"] == "Load Bearing Wall" for w in items[3:8]), [w["role"] for w in items[3:8]]
    assert closet["role"] == "Non-Load Bearing Wall" and closet["profile"] == "362S125-18"
    assert "exterior" in items[0]["spec"] and "demising" in items[3]["spec"]


def test_framing_sheet_levels() -> None:
    assert BW.levels("LGS FLOOR FRAME LAYOUT PLAN | FOR 2ND,FLOOR") == {2}
    assert BW.levels("PLAN FOR 2ND, 3RD, 4TH & 5TH FLOOR") == {2, 3, 4, 5}
    assert BW.levels("FIRST FLOOR WALL SECTIONS LAYOUT") == {1}


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
                import traceback

                traceback.print_exc()
                print("FAIL", name, repr(exc))
    sys.exit(1 if fails else 0)
