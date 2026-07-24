from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.primitives.line2d import (
    Line2D,
    Point2D,
)


def test_line_length_uses_the_euclidean_distance_between_endpoints():
    line = Line2D(
        start=Point2D(0.0, 0.0),
        end=Point2D(3.0, 4.0),
    )

    assert line.length == 5.0


def test_line_with_identical_endpoints_has_zero_length():
    point = Point2D(1.0, 2.0)

    line = Line2D(
        start=point,
        end=point,
    )

    assert line.length == 0.0


def test_horizontal_line_length_matches_its_x_axis_span():
    line = Line2D(
        Point2D(0.0, 0.0),
        Point2D(100.0, 0.0),
    )

    assert line.length == 100.0


def test_lines_with_matching_endpoints_are_equal():
    start = Point2D(0.0, 0.0)
    end = Point2D(3.0, 4.0)

    assert Line2D(start, end) == Line2D(start, end)


def test_lines_with_different_endpoints_are_not_equal():
    assert Line2D(Point2D(0.0, 0.0), Point2D(3.0, 4.0)) != Line2D(
        Point2D(0.0, 0.0),
        Point2D(4.0, 3.0),
    )


def test_line_endpoints_cannot_be_reassigned():
    line = Line2D(Point2D(0.0, 0.0), Point2D(3.0, 4.0))

    with pytest.raises(FrozenInstanceError):
        line.start = Point2D(1.0, 1.0)
