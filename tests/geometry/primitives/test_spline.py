"""Tests for the closed and open Catmull-Rom splines."""

import math

import pytest

from cncguitarwizard.geometry.exceptions import GeometryException
from cncguitarwizard.geometry.primitives import (
    CORNER,
    ROUND,
    Point2D,
    closed_catmull_rom,
    drawn_points,
    drawn_polygon,
    moved,
    open_catmull_rom,
)


def _crosses_itself(points: tuple[Point2D, ...]) -> bool:
    def turn(p: Point2D, q: Point2D, r: Point2D) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    edges = list(zip(points, (*points[1:], points[0]), strict=True))
    for i, (a, b) in enumerate(edges):
        for j in range(i + 2, len(edges)):
            if i == 0 and j == len(edges) - 1:
                continue
            c, d = edges[j]
            if (turn(c, d, a) > 0) != (turn(c, d, b) > 0) and (turn(a, b, c) > 0) != (
                turn(a, b, d) > 0
            ):
                return True
    return False


def test_two_points_drawn_almost_on_each_other_at_a_turn_make_no_loop() -> None:
    # Regression: a body's cutaway deepened at the upper frets, its inner
    # corner drawn as two points 0.09 mm apart between points 5 mm away. Its
    # Catmull-Rom tangents (half its neighbours' 5 mm span) curled that
    # short segment back on itself, a loop FreeCAD made no face of: the
    # body was lost. It is drawn with them no longer than its chord.
    corner = (
        Point2D(-9.57, 49.51),
        Point2D(-8.27, 54.24),
        Point2D(-7.02, 59.0),
        Point2D(-6.94, 59.04),
        Point2D(-3.17, 60.56),
        Point2D(1.35, 62.38),
        Point2D(10.43, 65.95),
        Point2D(10.43, 20.0),
        Point2D(-9.57, 20.0),
    )
    outline = closed_catmull_rom(corner, 8)
    assert not _crosses_itself(outline)
    # Still through every point, and the short segment between the two.
    for index, point in enumerate(corner):
        assert outline[index * 8] == point
    short = outline[2 * 8 : 3 * 8]
    assert all(-7.03 < p.x < -6.93 and 58.99 < p.y < 59.05 for p in short)
    # A loop of evenly spread points is the plain Catmull-Rom curve as ever:
    # at a quarter of its first segment, half of 2 P1 + (P2 - P0) t
    # + (2 P0 - 5 P1 + 4 P2 - P3) t^2 + (3 P1 - P0 - 3 P2 + P3) t^3.
    square = (Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10))
    quarter = closed_catmull_rom(square, 4)[1]
    assert (quarter.x, quarter.y) == pytest.approx((2.03125, -0.9375))


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


SQUARE = (
    Point2D(0.0, 0.0),
    Point2D(10.0, 0.0),
    Point2D(10.0, 10.0),
    Point2D(0.0, 10.0),
)


def test_corners_make_a_span_between_them_straight() -> None:
    plain = closed_catmull_rom(SQUARE, 8)
    # Unmarked, the curve is as it always was.
    assert closed_catmull_rom(SQUARE, 8, (False,) * 4) == plain
    # The bottom two corners: the bottom side straight, the rest round.
    marked = closed_catmull_rom(SQUARE, 8, (True, True, False, False))
    assert all(point.y == pytest.approx(0.0, abs=1e-12) for point in marked[:9])
    assert any(point.x > 10.0 + 1e-6 for point in marked[9:])
    # All four: a square.
    square = closed_catmull_rom(SQUARE, 8, (True,) * 4)
    assert all(
        min(abs(p.x), abs(p.x - 10.0), abs(p.y), abs(p.y - 10.0)) < 1e-9 for p in square
    )


def test_an_open_curve_is_sharp_at_its_corner() -> None:
    peak = (Point2D(0.0, 0.0), Point2D(5.0, 3.0), Point2D(10.0, 0.0))
    sharp = open_catmull_rom(peak, 4, (False, True, False))

    # Each side runs straight at the corner: in toward it, out from it.
    assert sharp[3].y / sharp[3].x == pytest.approx(0.6)
    assert (sharp[5].y - 3.0) / (sharp[5].x - 5.0) == pytest.approx(-0.6)
    with pytest.raises(GeometryException, match="one corner mark"):
        open_catmull_rom(peak, 4, (True,))


def test_drawn_points_carry_their_corners() -> None:
    points, corners = drawn_points(((1.0, 2.0), (3.0, 4.0, CORNER)))

    assert points == (Point2D(1.0, 2.0), Point2D(3.0, 4.0))
    assert corners == (False, True)
    assert moved((3.0, 4.0, CORNER), 5.0, 6.0) == (5.0, 6.0, CORNER)
    assert moved((3.0, 4.0), 5.0, 6.0) == (5.0, 6.0)
    with pytest.raises(GeometryException, match="two numbers"):
        drawn_points(((1.0, 2.0, "round"),))


def test_a_drawn_polygon_is_rounded_only_through_its_round_points() -> None:
    points, rounds = drawn_points(
        ((0.0, 0.0), (10.0, 0.0, ROUND), (10.0, 10.0), (0.0, 10.0)), ROUND
    )
    assert rounds == (False, True, False, False)
    assert moved((10.0, 0.0, ROUND), 1.0, 2.0) == (1.0, 2.0, ROUND)

    # None round: the points themselves.
    assert drawn_polygon(points, (False,) * 4, 8) == points
    polygon = drawn_polygon(points, rounds, 8)
    # The two sides at the round point sampled, the straight ones kept as
    # their ends alone.
    assert len(polygon) == 2 * 8 + 2
    assert (polygon[0], polygon[8]) == (points[0], points[1])
    assert polygon[16:] == points[2:]
    # Through the round point the outline turns smoothly, not by 90°:
    # finely sampled, hardly at all from one sample to the next.
    fine = drawn_polygon(points, rounds, 64)
    (ax, ay), (bx, by) = (
        (fine[64].x - fine[63].x, fine[64].y - fine[63].y),
        (fine[65].x - fine[64].x, fine[65].y - fine[64].y),
    )
    turn = math.degrees(abs(math.atan2(ax * by - ay * bx, ax * bx + ay * by)))
    assert turn < 5.0
    with pytest.raises(GeometryException, match="one mark a point"):
        drawn_polygon(points, (True,), 8)
