"""Tests for the flame strap guide's plate, spacers and screws."""

import math

import pytest

from cncguitarwizard.geometry.body import FlameStrapGuide
from cncguitarwizard.geometry.body.strap_guide import (
    STRAP_GUIDE_SCREW_CLEARANCE,
    STRAP_GUIDE_SCREW_INSET,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon

CENTRE = Point2D(300.0, -50.0)


def spans(points: tuple[Point2D, ...]) -> tuple[float, float]:
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    return max(xs) - min(xs), max(ys) - min(ys)


def test_the_plate_is_a_bar_with_a_flame_at_either_end() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0)

    # The channel 27 mm either side of the middle, each flame 43.4 mm past
    # it; the tongues sweep 29 mm to one side, the bar's edge 13 mm to the
    # other.
    length, width = spans(guide.outline)
    assert length == pytest.approx(2.0 * (guide.channel_half + 43.4), abs=0.5)
    assert width == pytest.approx(58.0, abs=1.0)
    assert guide.channel_half == pytest.approx(27.0)


def test_the_second_flame_is_the_first_turned_half_round() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0)
    outline = guide.outline

    for point in outline:
        turned = (2.0 * CENTRE.x - point.x, 2.0 * CENTRE.y - point.y)
        assert min(math.dist(turned, (q.x, q.y)) for q in outline) < 1e-6


def test_the_spacers_stand_either_side_of_the_straps_channel() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0)
    first, second = guide.spacers

    assert all(point.x - CENTRE.x >= guide.channel_half - 1e-6 for point in first)
    assert all(CENTRE.x - point.x >= guide.channel_half - 1e-6 for point in second)


def test_a_screw_goes_through_each_spacer_on_the_bars_middle_line() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0)
    reach = guide.channel_half + STRAP_GUIDE_SCREW_INSET

    assert guide.screws == (
        Point2D(CENTRE.x + reach, CENTRE.y),
        Point2D(CENTRE.x - reach, CENTRE.y),
    )
    for screw, spacer in zip(guide.screws, guide.spacers, strict=True):
        assert point_in_polygon(screw, spacer)
        assert point_in_polygon(screw, guide.outline)


def test_the_guide_turns_with_its_angle() -> None:
    straight = FlameStrapGuide(CENTRE, 0.0)
    turned = FlameStrapGuide(CENTRE, 90.0)

    length, width = spans(straight.outline)
    assert spans(turned.outline) == pytest.approx((width, length), abs=1e-6)
    assert turned.screws[0].x == pytest.approx(CENTRE.x)
    assert turned.screws[0].y == pytest.approx(
        CENTRE.y + straight.channel_half + STRAP_GUIDE_SCREW_INSET
    )


def test_the_plate_and_spacers_are_cut_from_sheet_for_the_back() -> None:
    guide = FlameStrapGuide(CENTRE, 20.0, gap=6.0, thickness=4.0)

    plate, first, second = guide.covers()

    assert [part.name for part in (plate, first, second)] == [
        "Strap guide plate",
        "Strap guide spacer 1",
        "Strap guide spacer 2",
    ]
    assert all(part.face == "back" and not part.recessed for part in (plate, first))
    assert (plate.thickness, first.thickness, second.thickness) == (4.0, 6.0, 6.0)
    assert plate.outline == guide.outline
    assert (first.outline, second.outline) == guide.spacers
    assert [(h.center, h.diameter) for h in plate.holes] == [
        (screw, STRAP_GUIDE_SCREW_CLEARANCE) for screw in guide.screws
    ]
    assert [h.center for h in (*first.holes, *second.holes)] == list(guide.screws)


def test_the_screws_pilots_are_drilled_into_the_back() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0, screw_diameter=2.5, screw_depth=15.0)

    pilots = guide.pilot_holes()

    assert [hole.name for hole in pilots] == [
        "Strap guide screw 1 pilot",
        "Strap guide screw 2 pilot",
    ]
    assert all((h.diameter, h.depth) == (2.5, 15.0) for h in pilots)
    assert [hole.center for hole in pilots] == list(guide.screws)


@pytest.mark.parametrize(
    "field", ["strap_width", "gap", "thickness", "screw_diameter", "screw_depth"]
)
def test_a_size_that_is_not_positive_is_rejected(field: str) -> None:
    with pytest.raises(BodyGeometryError, match=field):
        FlameStrapGuide(CENTRE, 0.0, **{field: 0.0})


def test_pilots_as_wide_as_the_holes_through_the_parts_are_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="narrower"):
        FlameStrapGuide(CENTRE, 0.0, screw_diameter=STRAP_GUIDE_SCREW_CLEARANCE)
