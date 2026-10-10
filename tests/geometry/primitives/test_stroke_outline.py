"""Tests for the outline of lines drawn with a round pen."""

import math

import pytest

from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.geometry.primitives import stroke_outlines as outlines


def area(points: tuple[Point2D, ...]) -> float:
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


def test_one_stroke_is_a_capsule() -> None:
    (capsule,) = outlines([[Point2D(0.0, 0.0), Point2D(10.0, 0.0)]], 1.0, 0.1, 0.005)

    # A 10 x 2 rectangle and two half circles, counter-clockwise.
    assert area(capsule) == pytest.approx(20.0 + math.pi, rel=0.01)
    for point in capsule:
        nearest = math.hypot(max(0.0, point.x - 10.0, -point.x), point.y)
        assert nearest == pytest.approx(1.0, abs=0.02)


def test_strokes_that_cross_merge_and_apart_stay_apart() -> None:
    cross = outlines(
        [
            [Point2D(0.0, 0.0), Point2D(6.0, 10.0)],
            [Point2D(0.0, 10.0), Point2D(6.0, 0.0)],
        ],
        0.6,
        0.05,
        0.005,
    )
    apart = outlines(
        [
            [Point2D(0.0, 0.0), Point2D(0.0, 5.0)],
            [Point2D(3.0, 0.0), Point2D(3.0, 5.0)],
        ],
        0.5,
        0.05,
        0.005,
    )

    assert len(cross) == 1
    assert len(apart) == 2
    assert all(area(outline) > 0.0 for outline in (*cross, *apart))


def test_an_area_closed_in_is_filled() -> None:
    (triangle,) = outlines(
        [[Point2D(0.0, 0.0), Point2D(10.0, 0.0), Point2D(5.0, 8.0), Point2D(0.0, 0.0)]],
        0.5,
        0.05,
        0.005,
    )

    assert point_in_polygon(Point2D(5.0, 3.0), triangle)
    assert area(triangle) > 40.0  # the triangle's own 40, and the stroke round it


@pytest.mark.parametrize(
    ("strokes", "half_width"),
    [([], 1.0), ([[Point2D(0.0, 0.0)]], 1.0), ([[Point2D(0.0, 0.0)] * 2], 0.0)],
)
def test_nothing_to_draw_is_refused(
    strokes: list[list[Point2D]], half_width: float
) -> None:
    with pytest.raises(ValueError):
        outlines(strokes, half_width, 0.1, 0.01)
