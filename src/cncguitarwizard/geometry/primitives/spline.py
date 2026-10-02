"""Closed Catmull-Rom splines: smooth outlines through a few control points."""

from __future__ import annotations

from collections.abc import Sequence

from ..exceptions import GeometryException
from .point2d import Point2D


def closed_catmull_rom(
    control_points: Sequence[Point2D],
    samples_per_segment: int = 8,
) -> tuple[Point2D, ...]:
    """Return a closed, smooth outline passing through every control point.

    Each segment between two neighbouring control points is a uniform
    Catmull-Rom cubic, whose tangent at a point is parallel to the line
    joining its two neighbours, so the loop is tangent-continuous at every
    control point. The last point joins back to the first.

    Args:
        control_points: At least three points, in order around the loop.
        samples_per_segment: Points per segment, the control point first.

    Returns:
        ``len(control_points) * samples_per_segment`` outline points.

    Raises:
        GeometryException: For fewer than three control points or fewer than
            one sample per segment.
    """
    count = len(control_points)
    if count < 3:
        raise GeometryException("A closed spline needs at least three control points.")
    if samples_per_segment < 1:
        raise GeometryException("A spline segment needs at least one sample.")
    points: list[Point2D] = []
    for index in range(count):
        p0 = control_points[index - 1]
        p1 = control_points[index]
        p2 = control_points[(index + 1) % count]
        p3 = control_points[(index + 2) % count]
        for step in range(samples_per_segment):
            t = step / samples_per_segment
            t2 = t * t
            t3 = t2 * t
            points.append(
                Point2D(
                    _blend(p0.x, p1.x, p2.x, p3.x, t, t2, t3),
                    _blend(p0.y, p1.y, p2.y, p3.y, t, t2, t3),
                )
            )
    return tuple(points)


def open_catmull_rom(
    control_points: Sequence[Point2D],
    samples_per_segment: int = 8,
) -> tuple[Point2D, ...]:
    """Return a smooth open curve from the first control point to the last.

    As ``closed_catmull_rom``, but not joined back: each end point stands
    in for its own missing neighbour, so the curve leaves the first point
    toward the second and arrives at the last from the one before.

    Args:
        control_points: At least two points, in order along the curve.
        samples_per_segment: Points per segment, the control point first.

    Returns:
        ``(len(control_points) - 1) * samples_per_segment + 1`` points,
        both ends included.

    Raises:
        GeometryException: For fewer than two control points or fewer than
            one sample per segment.
    """
    count = len(control_points)
    if count < 2:
        raise GeometryException("An open spline needs at least two control points.")
    if samples_per_segment < 1:
        raise GeometryException("A spline segment needs at least one sample.")
    points: list[Point2D] = []
    for index in range(count - 1):
        p0 = control_points[max(index - 1, 0)]
        p1 = control_points[index]
        p2 = control_points[index + 1]
        p3 = control_points[min(index + 2, count - 1)]
        for step in range(samples_per_segment):
            t = step / samples_per_segment
            t2 = t * t
            t3 = t2 * t
            points.append(
                Point2D(
                    _blend(p0.x, p1.x, p2.x, p3.x, t, t2, t3),
                    _blend(p0.y, p1.y, p2.y, p3.y, t, t2, t3),
                )
            )
    points.append(control_points[-1])
    return tuple(points)


def _blend(
    a: float, b: float, c: float, d: float, t: float, t2: float, t3: float
) -> float:
    return 0.5 * (
        2.0 * b
        + (c - a) * t
        + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
        + (3.0 * b - a - 3.0 * c + d) * t3
    )
