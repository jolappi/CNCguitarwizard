"""Tests for top-view guitar neck outline geometry."""

import math
from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.neck import NeckOutline
from cncguitarwizard.geometry.neck.outline import heel_end_curve
from cncguitarwizard.geometry.primitives import Point2D


def make_outline() -> NeckOutline:
    """Return the locked Prototype001 neck outline."""
    return NeckOutline(
        scale_length=609.6,
        fret_count=24,
        nut_width=42.0,
        last_fret_width=56.0,
        heel_width=56.0,
        heel_length=63.0,
    )


def test_outline_uses_the_calculated_final_fret_position() -> None:
    outline = make_outline()
    expected_position = FretCalculator.calculate(609.6, 24)[-1].distance_from_nut

    assert outline.last_fret_position == pytest.approx(expected_position)
    assert outline.last_fret_line.start.x == pytest.approx(expected_position)


def test_outline_preserves_requested_widths() -> None:
    outline = make_outline()

    assert outline.nut_line.length == pytest.approx(42.0)
    assert outline.last_fret_line.length == pytest.approx(56.0)
    assert outline.heel_end_line.length == pytest.approx(56.0)


def test_parallel_heel_has_the_requested_length() -> None:
    outline = make_outline()

    assert outline.left_heel.length == pytest.approx(63.0)
    assert outline.right_heel.length == pytest.approx(63.0)


def test_outline_is_symmetric_about_the_centerline() -> None:
    outline = make_outline()

    for left, right in (
        (outline.nut_line.start, outline.nut_line.end),
        (outline.last_fret_line.start, outline.last_fret_line.end),
        (outline.heel_end_line.start, outline.heel_end_line.end),
    ):
        assert left.x == pytest.approx(right.x)
        assert left.y == pytest.approx(-right.y)


def test_outline_is_immutable() -> None:
    outline = make_outline()

    with pytest.raises(FrozenInstanceError):
        outline.heel_length = 70.0


@pytest.mark.parametrize(
    "create_outline",
    [
        lambda: NeckOutline(0.0, 24, 42.0, 56.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 0, 42.0, 56.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 24, 0.0, 56.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 24, 42.0, 41.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 24, 42.0, 56.0, 55.0, 63.0),
        lambda: NeckOutline(609.6, 24, 42.0, 56.0, 56.0, float("nan")),
    ],
)
def test_outline_rejects_invalid_dimensions(
    create_outline: Callable[[], NeckOutline],
) -> None:
    with pytest.raises(NeckGeometryError):
        create_outline()


def test_a_round_heel_end_is_an_arc_blended_into_its_sides() -> None:
    end = heel_end_curve(100.0, 28.0, 127.0, 6.35)

    # From the -Y side round to the +Y side, through the end on the centre.
    assert (end[0].y, end[-1].y) == (-28.0, 28.0)
    assert end[0].x == pytest.approx(end[-1].x)
    assert max(p.x for p in end) == pytest.approx(100.0)
    middle = end[len(end) // 2]
    assert (middle.x, middle.y) == pytest.approx((100.0, 0.0))
    # On the arc near the centre, its radius from (100 - 127, 0).
    for point in end[len(end) // 3 : 2 * len(end) // 3]:
        assert math.hypot(point.x - (100.0 - 127.0), point.y) == pytest.approx(127.0)
    # Square: just its corners.
    assert heel_end_curve(100.0, 28.0, 0.0, 0.0) == (
        Point2D(100.0, -28.0),
        Point2D(100.0, 28.0),
    )
    with pytest.raises(NeckGeometryError, match="more than half"):
        heel_end_curve(100.0, 28.0, 20.0, 6.35)
    with pytest.raises(NeckGeometryError, match="corner radius"):
        heel_end_curve(100.0, 28.0, 127.0, 30.0)


def test_a_round_heel_ends_short_of_its_end_beside_the_centre() -> None:
    outline = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 4.0, 127.0, 6.35)
    end = outline.last_fret_position + outline.heel_length

    assert outline.heel_end_inset(0.0) == pytest.approx(0.0)
    # On the arc: its sagitta there.
    assert outline.heel_end_inset(19.0) == pytest.approx(
        127.0 - math.sqrt(127.0**2 - 19.0**2), abs=0.01
    )
    assert outline.heel_end_inset(-19.0) == outline.heel_end_inset(19.0)
    # The outline is cut back to it: nothing past the end beside the centre.
    for point in outline.boundary:
        assert point.x <= end - outline.heel_end_inset(point.y) + 1e-6
    assert max(p.x for p in outline.boundary) == pytest.approx(end)
    # The square outline is as before.
    square = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 4.0)
    assert len(square.boundary) == 8
    assert square.heel_end_inset(20.0) == 0.0
    # A board reaching the end is rounded with it.
    board = (
        Point2D(0.0, -21.0),
        Point2D(end, -28.0),
        Point2D(end, 28.0),
        Point2D(0.0, 21.0),
    )
    trimmed = outline.trimmed(board)
    assert all(p.x <= end - outline.heel_end_inset(p.y) + 1e-6 for p in trimmed)
    assert square.trimmed(board) == board
