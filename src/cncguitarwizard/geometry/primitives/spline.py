"""Catmull-Rom splines: smooth outlines through a few control points.

A drawn control point may be a sharp corner (``CORNER``): the curve
leaves it toward its next point and comes in toward it from its previous
one, so between two corners it runs straight. Drawn points carry the mark
as a third item, ``(x, y, "corner")``; ``drawn_points`` reads them.

A drawn polygon is the other way round: straight between its points, but
a point marked ``ROUND``, ``(x, y, "round")``, is rounded through
(``drawn_polygon``).
"""

from __future__ import annotations

from collections.abc import Sequence

from ..exceptions import GeometryException
from .point2d import Point2D

CORNER = "corner"
"""The mark a drawn control point carries to be a sharp corner."""

ROUND = "round"
"""The mark a drawn polygon's point carries to be rounded through."""

DrawnPoint = tuple[float, float] | tuple[float, float, str]
"""A drawn point: ``(x, y)``, or with its mark, ``(x, y, "corner")`` for a
spline's sharp corner or ``(x, y, "round")`` for a polygon's round one."""


def moved(point: Sequence[float | str], x: float, y: float) -> DrawnPoint:
    """Return a drawn ``point`` put at (``x``, ``y``), its mark kept."""
    return (x, y, str(point[2])) if len(point) == 3 else (x, y)


def drawn_points(
    points: Sequence[Sequence[float | str]], mark: str = CORNER
) -> tuple[tuple[Point2D, ...], tuple[bool, ...]]:
    """Return drawn points and which of them carry ``mark``.

    ``CORNER`` for a spline's control points (which are sharp corners),
    ``ROUND`` for a polygon's (which are rounded through).

    Raises:
        GeometryException: For a point that is not two numbers, or two and
            ``mark``.
    """
    positions: list[Point2D] = []
    marked: list[bool] = []
    for point in points:
        if not (
            isinstance(point, (tuple, list))
            and len(point) in (2, 3)
            and all(isinstance(value, (int, float)) for value in point[:2])
            and (len(point) == 2 or point[2] == mark)
        ):
            raise GeometryException(
                f"A drawn point is two numbers, or two and {mark!r}: {point!r}."
            )
        positions.append(Point2D(float(point[0]), float(point[1])))
        marked.append(len(point) == 3)
    return tuple(positions), tuple(marked)


def drawn_polygon(
    points: Sequence[Point2D],
    rounds: Sequence[bool],
    samples_per_segment: int = 8,
) -> tuple[Point2D, ...]:
    """Return a drawn polygon: straight between its points, but rounded
    through those marked round (``rounds``, one a point).

    The closed Catmull-Rom loop through them with every other point a
    sharp corner (``closed_catmull_rom``), so a side between two corners
    is straight and kept as its two ends alone; with no point round, the
    points themselves.

    Raises:
        GeometryException: For fewer than three points, or marks that are
            not one a point.
    """
    count = len(points)
    if len(rounds) != count:
        raise GeometryException("A drawn polygon needs one mark a point.")
    if not any(rounds):
        return tuple(points)
    corners = [not rounded for rounded in rounds]
    loop = closed_catmull_rom(points, samples_per_segment, corners)
    kept: list[Point2D] = []
    for index in range(count):
        side = loop[index * samples_per_segment : (index + 1) * samples_per_segment]
        straight = not rounds[index] and not rounds[(index + 1) % count]
        kept += side[:1] if straight else side
    return tuple(kept)


def closed_catmull_rom(
    control_points: Sequence[Point2D],
    samples_per_segment: int = 8,
    corners: Sequence[bool] = (),
) -> tuple[Point2D, ...]:
    """Return a closed, smooth outline passing through every control point.

    Each segment between two neighbouring control points is a uniform
    Catmull-Rom cubic, whose tangent at a point is parallel to the line
    joining its two neighbours, so the loop is tangent-continuous at every
    control point — but at a corner (``corners``), where the tangent on
    each side points along its segment's chord (``_segment``). The last
    point joins back to the first.

    Args:
        control_points: At least three points, in order around the loop.
        samples_per_segment: Points per segment, the control point first.
        corners: Which control points are sharp corners; empty for none.

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
    sharp = _corners(corners, count)
    points: list[Point2D] = []
    for index in range(count):
        points += _segment(
            control_points[index - 1],
            control_points[index],
            control_points[(index + 1) % count],
            control_points[(index + 2) % count],
            sharp[index],
            sharp[(index + 1) % count],
            samples_per_segment,
        )
    return tuple(points)


def open_catmull_rom(
    control_points: Sequence[Point2D],
    samples_per_segment: int = 8,
    corners: Sequence[bool] = (),
) -> tuple[Point2D, ...]:
    """Return a smooth open curve from the first control point to the last.

    As ``closed_catmull_rom``, but not joined back: each end point stands
    in for its own missing neighbour, so the curve leaves the first point
    toward the second and arrives at the last from the one before (as it
    does at a corner).

    Args:
        control_points: At least two points, in order along the curve.
        samples_per_segment: Points per segment, the control point first.
        corners: Which control points are sharp corners; empty for none.

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
    sharp = _corners(corners, count)
    points: list[Point2D] = []
    for index in range(count - 1):
        points += _segment(
            control_points[max(index - 1, 0)],
            control_points[index],
            control_points[index + 1],
            control_points[min(index + 2, count - 1)],
            sharp[index],
            sharp[index + 1],
            samples_per_segment,
        )
    points.append(control_points[-1])
    return tuple(points)


def _corners(corners: Sequence[bool], count: int) -> tuple[bool, ...]:
    """Return a corner mark for each of ``count`` points (none if empty).

    Raises:
        GeometryException: For marks that are not one a point.
    """
    if not corners:
        return (False,) * count
    if len(corners) != count:
        raise GeometryException("A spline needs one corner mark a control point.")
    return tuple(corners)


def _segment(
    p0: Point2D,
    p1: Point2D,
    p2: Point2D,
    p3: Point2D,
    sharp_start: bool,
    sharp_end: bool,
    samples: int,
) -> list[Point2D]:
    """Return one segment's samples from ``p1`` toward ``p2`` (``p2`` left out).

    A Catmull-Rom cubic, its tangents half the chord between each end's
    neighbours; at a sharp end, half its own chord instead, so a segment
    between two corners is straight.
    """
    if not sharp_start and not sharp_end:
        # The plain Catmull-Rom blend, as before corners were drawn.
        points = []
        for step in range(samples):
            t = step / samples
            t2 = t * t
            t3 = t2 * t
            points.append(
                Point2D(
                    _blend(p0.x, p1.x, p2.x, p3.x, t, t2, t3),
                    _blend(p0.y, p1.y, p2.y, p3.y, t, t2, t3),
                )
            )
        return points
    start = (p2.x - p1.x, p2.y - p1.y) if sharp_start else (p2.x - p0.x, p2.y - p0.y)
    end = (p2.x - p1.x, p2.y - p1.y) if sharp_end else (p3.x - p1.x, p3.y - p1.y)
    points = []
    for step in range(samples):
        t = step / samples
        t2 = t * t
        t3 = t2 * t
        h00 = 2.0 * t3 - 3.0 * t2 + 1.0
        h10 = t3 - 2.0 * t2 + t
        h01 = -2.0 * t3 + 3.0 * t2
        h11 = t3 - t2
        points.append(
            Point2D(
                h00 * p1.x + h10 * start[0] / 2.0 + h01 * p2.x + h11 * end[0] / 2.0,
                h00 * p1.y + h10 * start[1] / 2.0 + h01 * p2.y + h11 * end[1] / 2.0,
            )
        )
    return points


def _blend(
    a: float, b: float, c: float, d: float, t: float, t2: float, t3: float
) -> float:
    return 0.5 * (
        2.0 * b
        + (c - a) * t
        + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
        + (3.0 * b - a - 3.0 * c + d) * t3
    )
