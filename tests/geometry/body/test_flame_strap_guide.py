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


def test_the_guide_is_a_slim_plate_over_two_flames() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0)

    # A 25 mm strap: the channel 14.5 mm either side of the middle, each
    # flame's long tongue 39.4 mm past it, the flames 20.6 mm across.
    length, width = spans(guide.outline)
    assert guide.channel_half == pytest.approx(14.5)
    assert length == pytest.approx(2.0 * (guide.channel_half + 39.4), abs=0.1)
    assert width == pytest.approx(20.6, abs=0.3)
    # The plate: a 10 mm bar, its tongues 20.6 mm past the channel, over
    # the flames' long tongues.
    plate_length, plate_width = spans(guide.plate)
    assert plate_length == pytest.approx(2.0 * (guide.channel_half + 20.6), abs=0.1)
    assert plate_width == pytest.approx(10.0, abs=0.3)
    assert all(point_in_polygon(point, guide.outline) for point in guide.plate)


def test_the_guide_is_the_same_either_side_of_the_strap_mirrored() -> None:
    guide = FlameStrapGuide(CENTRE, 0.0)

    for outline in (guide.outline, guide.plate):
        for point in outline:
            mirrored = (2.0 * CENTRE.x - point.x, point.y)
            assert min(math.dist(mirrored, (q.x, q.y)) for q in outline) < 1e-6


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
    assert plate.outline == guide.plate
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
