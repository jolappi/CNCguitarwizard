"""Tests for two-dimensional geometry utility functions."""

from cncguitarwizard.geometry.primitives import Line2D, Point2D
from cncguitarwizard.geometry.utils import distance, interpolate, midpoint


def test_distance_matches_the_length_of_an_equivalent_line() -> None:
    start = Point2D(0.0, 0.0)
    end = Point2D(3.0, 4.0)

    assert distance(start, end) == Line2D(start, end).length == 5.0


def test_midpoint_returns_a_new_point_halfway_between_endpoints() -> None:
    start = Point2D(2.0, 4.0)
    end = Point2D(6.0, 8.0)

    result = midpoint(start, end)

    assert result == Point2D(4.0, 6.0)
    assert result is not start
    assert result is not end


def test_interpolate_returns_the_start_point_at_zero_fraction() -> None:
    start = Point2D(2.0, 4.0)
    end = Point2D(6.0, 8.0)

    assert interpolate(start, end, 0.0) == start


def test_interpolate_returns_the_end_point_at_one_fraction() -> None:
    start = Point2D(2.0, 4.0)
    end = Point2D(6.0, 8.0)

    assert interpolate(start, end, 1.0) == end


def test_interpolate_returns_the_expected_interior_point() -> None:
    result = interpolate(Point2D(0.0, 0.0), Point2D(8.0, 4.0), 0.25)

    assert result == Point2D(2.0, 1.0)


def test_interpolate_extrapolates_for_a_fraction_outside_the_segment() -> None:
    result = interpolate(Point2D(0.0, 0.0), Point2D(4.0, 2.0), 1.5)

    assert result == Point2D(6.0, 3.0)
