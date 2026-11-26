# DDC-CWICR-OE: DataDrivenConstruction - OpenConstructionERP
"""Unit tests for seeded similar-symbol search ("count by example").

Exercises :func:`app.modules.takeoff.recognize.find_similar_symbols` with
synthetic ``get_drawings()``-shaped input (plain tuples) - no PDF, PyMuPDF or
database needed. The user clicks one symbol on the page and we return every
near-identical symbol so they can confirm them as a single count measurement;
nothing is persisted here (CLAUDE.md rule 7).
"""

from __future__ import annotations

from app.modules.takeoff import recognize


def _rect_path(x0: float, y0: float, x1: float, y1: float) -> dict:
    """A get_drawings()-shaped path holding a single rectangle item."""
    return {"items": [("re", (x0, y0, x1, y1))]}


def test_click_finds_all_identical_symbols() -> None:
    # Four identical 20x20 symbols plus one smaller 12x12 symbol that, being a
    # different size, must NOT be returned when the user seeds from a 20x20 one.
    drawings = [
        _rect_path(0, 0, 20, 20),
        _rect_path(100, 0, 120, 20),
        _rect_path(0, 100, 20, 120),
        _rect_path(100, 100, 120, 120),
        _rect_path(200, 200, 212, 212),  # 12x12 - excluded by the size gate
    ]
    # Click the centre of the first symbol.
    result = recognize.find_similar_symbols(drawings, 10.0, 10.0)
    assert result["note"] is None
    assert result["seed_found"] is True
    assert len(result["hits"]) == 4  # the four 20x20, not the 12x12
    assert all(h["confidence"] >= 0.5 for h in result["hits"])
    # Exactly one hit is the seed the user clicked.
    assert sum(1 for h in result["hits"] if h["is_seed"]) == 1
    # Every hit carries a centroid + bbox in PDF points.
    for h in result["hits"]:
        assert {"x", "y", "bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1"} <= set(h)


def test_click_on_empty_space_finds_no_seed() -> None:
    drawings = [_rect_path(0, 0, 20, 20)]
    result = recognize.find_similar_symbols(drawings, 500.0, 500.0)
    assert result["seed_found"] is False
    assert result["hits"] == []
    assert result["note"] == "no_symbol_at_point"


def test_page_with_no_vector_layer() -> None:
    # No drawings at all -> the page has no vector layer (e.g. a scan).
    result = recognize.find_similar_symbols([], 10.0, 10.0)
    assert result["seed_found"] is False
    assert result["hits"] == []
    assert result["note"] == "no_vector_layer"


def test_hits_are_capped_by_max_hits() -> None:
    # A dense grid of identical symbols; the review panel cap is honoured.
    drawings = [_rect_path(x, y, x + 20, y + 20) for x in range(0, 400, 40) for y in range(0, 400, 40)]
    result = recognize.find_similar_symbols(drawings, 10.0, 10.0, max_hits=5)
    assert len(result["hits"]) == 5
    assert result["seed_found"] is True


def test_all_pages_matches_the_seed_on_every_page() -> None:
    # Seed clicked on page 1; page 2 has two of the same symbol, page 3 only a
    # different-sized one, page 4 is a scan with no vectors.
    pages = {
        1: [_rect_path(0, 0, 20, 20), _rect_path(100, 0, 120, 20)],
        2: [_rect_path(50, 50, 70, 70), _rect_path(300, 300, 320, 320)],
        3: [_rect_path(0, 0, 12, 12)],
        4: [],
    }
    result = recognize.find_similar_symbols_all_pages(pages, 1, 10.0, 10.0)
    assert result["seed_found"] is True
    assert result["note"] is None
    assert [p["page"] for p in result["pages"]] == [1, 2]
    assert result["total_hits"] == 4
    # Only the clicked page carries the seed flag.
    assert sum(h["is_seed"] for h in result["pages"][0]["hits"]) == 1
    assert not any(h["is_seed"] for h in result["pages"][1]["hits"])


def test_all_pages_reports_a_missed_click_and_a_scanned_seed_page() -> None:
    pages = {1: [_rect_path(0, 0, 20, 20)], 2: [_rect_path(0, 0, 20, 20)]}
    missed = recognize.find_similar_symbols_all_pages(pages, 1, 500.0, 500.0)
    assert missed == {"seed_found": False, "note": "no_symbol_at_point", "total_hits": 0, "pages": []}
    scanned = recognize.find_similar_symbols_all_pages({1: [], 2: pages[2]}, 1, 10.0, 10.0)
    assert scanned["note"] == "no_vector_layer"
