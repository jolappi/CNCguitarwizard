"""Tests for the planar clearance helpers behind the toolpath planner."""

import math

import pytest

from cncguitarwizard.cam.planar import (
    clear_intervals,
    disc_fits,
    distance_to_boundary,
    offset_polygon,
    oriented,
    segment_fits,
    signed_area,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon


def rectangle(width: float, height: float) -> tuple[Point2D, ...]:
    return (
        Point2D(0.0, 0.0),
        Point2D(width, 0.0),
        Point2D(width, height),
        Point2D(0.0, height),
    )


def l_shape() -> tuple[Point2D, ...]:
    """A 40 x 40 square with its top-right 20 x 20 quadrant missing."""
    return (
        Point2D(0.0, 0.0),
        Point2D(40.0, 0.0),
        Point2D(40.0, 20.0),
        Point2D(20.0, 20.0),
        Point2D(20.0, 40.0),
        Point2D(0.0, 40.0),
    )


def test_signed_area_and_orientation() -> None:
    square = rectangle(10.0, 10.0)

    assert signed_area(square) == pytest.approx(100.0)
    assert signed_area(oriented(square, clockwise=True)) == pytest.approx(-100.0)
    assert oriented(square, clockwise=False) == square


def test_distance_to_boundary_measures_the_nearest_edge() -> None:
    square = rectangle(10.0, 10.0)

    assert distance_to_boundary(Point2D(5.0, 2.0), square) == pytest.approx(2.0)
    assert distance_to_boundary(Point2D(12.0, 5.0), square) == pytest.approx(2.0)


def test_disc_fits_requires_full_clearance_on_the_requested_side() -> None:
    square = rectangle(10.0, 10.0)

    assert disc_fits(Point2D(5.0, 5.0), square, 3.0)
    assert disc_fits(Point2D(5.0, 3.0), square, 3.0)
    assert not disc_fits(Point2D(5.0, 2.9), square, 3.0)
    assert not disc_fits(Point2D(-5.0, 5.0), square, 3.0)
    assert disc_fits(Point2D(-5.0, 5.0), square, 3.0, inside=False)
    assert not disc_fits(Point2D(-2.0, 5.0), square, 3.0, inside=False)


def test_clear_intervals_shrinks_a_rectangle_by_the_radius() -> None:
    intervals = clear_intervals(rectangle(20.0, 10.0), 5.0, 2.0)

    assert intervals == [pytest.approx((2.0, 18.0))]


def test_clear_intervals_is_empty_where_the_disc_cannot_reach() -> None:
    assert clear_intervals(rectangle(20.0, 10.0), 1.0, 2.0) == []
    assert clear_intervals(rectangle(20.0, 10.0), 5.0, 6.0) == []


def test_clear_intervals_splits_around_a_concave_corner() -> None:
    # Through the L at y = 30 only the left column is inside; at y = 10
    # the whole width is inside but the inner corner at (20, 20) pushes
    # the disc away.
    upper = clear_intervals(l_shape(), 30.0, 2.0)
    lower = clear_intervals(l_shape(), 19.0, 2.0)

    assert upper == [pytest.approx((2.0, 18.0))]
    assert len(lower) == 1
    assert lower[0][0] == pytest.approx(2.0)
    # One below the inner corner the disc can slide past x = 18 until it
    # touches the corner itself: 20 - sqrt(2^2 - 1^2).
    assert lower[0][1] == pytest.approx(20.0 - math.sqrt(3.0))


def test_clear_intervals_is_exact_against_the_disc_test() -> None:
    polygon = l_shape()
    radius = 2.5
    for y in (5.0, 17.5, 19.0, 21.0, 30.0):
        intervals = clear_intervals(polygon, y, radius)
        for x in [step * 0.25 for step in range(-8, 200)]:
            expected = disc_fits(Point2D(x, y), polygon, radius)
            covered = any(low - 1e-6 <= x <= high + 1e-6 for low, high in intervals)
            strictly_inside = any(
                low + 1e-6 < x < high - 1e-6 for low, high in intervals
            )
            if strictly_inside:
                assert expected, (x, y)
            elif not covered:
                assert not expected, (x, y)


def test_offset_polygon_inward_shrinks_a_rectangle() -> None:
    contour = offset_polygon(rectangle(20.0, 10.0), 2.0, inward=True)

    xs = [point.x for point in contour]
    ys = [point.y for point in contour]
    assert min(xs) == pytest.approx(2.0)
    assert max(xs) == pytest.approx(18.0)
    assert min(ys) == pytest.approx(2.0)
    assert max(ys) == pytest.approx(8.0)
    assert all(disc_fits(point, rectangle(20.0, 10.0), 2.0) for point in contour)


def test_offset_polygon_outward_grows_a_rectangle_with_rounded_corners() -> None:
    square = rectangle(10.0, 10.0)
    contour = offset_polygon(square, 3.0, inward=False)

    assert all(disc_fits(point, square, 3.0, inside=False) for point in contour)
    assert max(point.x for point in contour) == pytest.approx(13.0)
    # The corner is an arc, not a sharp point: nothing reaches (13, 13).
    assert all(math.hypot(point.x - 13.0, point.y - 13.0) > 1.0 for point in contour)
    assert signed_area(contour) > signed_area(square)


def test_offset_polygon_keeps_every_contour_segment_clear_on_an_l_shape() -> None:
    polygon = l_shape()
    contour = offset_polygon(polygon, 2.5, inward=True)

    assert len(contour) >= 3
    count = len(contour)
    for index in range(count):
        # Chord-safe arcs: even between samples the tool never gouges.
        assert segment_fits(
            contour[index], contour[(index + 1) % count], polygon, 2.5, spacing=0.1
        )


def test_offset_polygon_returns_empty_when_nothing_fits() -> None:
    assert offset_polygon(rectangle(20.0, 10.0), 6.0, inward=True) == ()


def test_offset_polygon_drops_a_region_too_narrow_for_the_disc() -> None:
    # A 40 x 10 bar with a 4 mm wide, 10 mm long slot sticking up from it.
    polygon = (
        Point2D(0.0, 0.0),
        Point2D(40.0, 0.0),
        Point2D(40.0, 10.0),
        Point2D(22.0, 10.0),
        Point2D(22.0, 20.0),
        Point2D(18.0, 20.0),
        Point2D(18.0, 10.0),
        Point2D(0.0, 10.0),
    )
    contour = offset_polygon(polygon, 3.0, inward=True)

    assert contour
    # The disc cannot enter the 4 mm slot; at most it bulges into its
    # mouth until it touches both mouth corners: y = 10 - sqrt(3^2 - 2^2).
    assert all(point.y <= 10.0 - math.sqrt(5.0) + 1e-6 for point in contour)
    assert all(point_in_polygon(point, polygon) for point in contour)
    assert all(disc_fits(point, polygon, 3.0) for point in contour)
