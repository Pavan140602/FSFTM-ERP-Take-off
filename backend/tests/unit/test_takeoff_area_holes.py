"""Cut-out holes are subtracted from an area's server-side value."""

from app.modules.takeoff.service import recompute_measurement_value, recompute_volume_value

SQUARE = [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}]
HOLE = [{"x": 25, "y": 25}, {"x": 75, "y": 25}, {"x": 75, "y": 75}, {"x": 25, "y": 75}]


def _area(holes: object) -> float | None:
    return recompute_measurement_value(
        measurement_type="area",
        points=SQUARE,
        scale_pixels_per_unit=10.0,
        count_value=None,
        client_value=None,
        holes=holes,
    )


def test_area_without_holes_is_gross() -> None:
    assert _area(None) == 100.0


def test_hole_is_subtracted() -> None:
    assert _area([HOLE]) == 75.0


def test_malformed_holes_never_add_area() -> None:
    assert _area("nope") == 100.0
    assert _area([[{"x": 1, "y": 1}], 5, [{"x": "a"}]]) == 100.0


def test_volume_uses_net_area() -> None:
    vol = recompute_volume_value(
        measurement_type="volume",
        points=SQUARE,
        scale_pixels_per_unit=10.0,
        depth=2.0,
        client_volume=None,
        holes=[HOLE],
    )
    assert vol == 150.0
