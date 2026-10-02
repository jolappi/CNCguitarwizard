"""Tests for the closed and open Catmull-Rom splines."""

import pytest

from cncguitarwizard.geometry.exceptions import GeometryException
from cncguitarwizard.geometry.primitives import (
    Point2D,
    closed_catmull_rom,
    open_catmull_rom,
)


def test_spline_passes_through_every_control_point_in_order() -> None:
    square = (Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10))
    outline = closed_catmull_rom(square, samples_per_segment=4)

    assert len(outline) == 16
    assert outline[0::4] == square


def test_spline_is_smooth_and_bulges_past_a_square() -> None:
    square = (Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10))
    outline = closed_catmull_rom(square, samples_per_segment=8)

    # Between two corners the curve swings outside the straight edge.
    assert min(point.y for point in outline) < 0.0
    assert max(point.x for point in outline) > 10.0


def test_spline_rejects_too_few_points_or_samples() -> None:
    with pytest.raises(GeometryException, match="three"):
        closed_catmull_rom((Point2D(0, 0), Point2D(1, 0)))
    with pytest.raises(GeometryException, match="sample"):
        closed_catmull_rom(
            (Point2D(0, 0), Point2D(1, 0), Point2D(0, 1)), samples_per_segment=0
        )


def test_an_open_curve_runs_from_the_first_point_to_the_last() -> None:
    points = (Point2D(0, 0), Point2D(10, 5), Point2D(20, 0))
    curve = open_catmull_rom(points, 4)

    assert len(curve) == 2 * 4 + 1
    assert curve[0] == points[0] and curve[-1] == points[-1]
    assert curve[4] == points[1]
    with pytest.raises(GeometryException, match="two control points"):
        open_catmull_rom((Point2D(0, 0),))
