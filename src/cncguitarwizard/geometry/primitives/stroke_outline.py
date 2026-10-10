"""The outline of lines drawn with a round pen of some width."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .point2d import Point2D
from .point_in_polygon import point_in_polygon


def stroke_outlines(
    strokes: Sequence[Sequence[Point2D]],
    half_width: float,
    cell: float,
    tolerance: float,
) -> tuple[tuple[Point2D, ...], ...]:
    """Return the outlines of ``strokes`` drawn ``2 * half_width`` wide.

    Each stroke is an open polyline drawn with a round pen: its ends and
    corners are rounded, and strokes that touch or cross merge into one
    shape. The shape is found where the distance to the nearest stroke is
    ``half_width``, on a grid ``cell`` apart (marching squares, each
    crossing placed along its cell's edge by the distances either end), and
    each outline is then thinned to its corners within ``tolerance``.

    An area the strokes close in (a loop's middle) is filled, so every
    outline is one simple polygon with no hole; strokes that do not touch
    give one outline each.

    Args:
        strokes: The polylines, each two points or more.
        half_width: Half the pen's width.
        cell: The grid's spacing; a tenth of the width or less keeps the
            ends round.
        tolerance: How far a thinned outline may stray from the traced one.

    Returns:
        The outlines, counter-clockwise, largest first.

    Raises:
        ValueError: For no stroke, a stroke of fewer than two points, or a
            width, cell or tolerance that is not positive.
    """
    if not strokes or any(len(stroke) < 2 for stroke in strokes):
        raise ValueError("Every stroke needs at least two points.")
    if not all(value > 0.0 for value in (half_width, cell, tolerance)):
        raise ValueError("The width, cell and tolerance must be positive.")
    segments = [
        (a, b) for stroke in strokes for a, b in zip(stroke, stroke[1:], strict=False)
    ]
    xs = [p.x for stroke in strokes for p in stroke]
    ys = [p.y for stroke in strokes for p in stroke]
    margin = half_width + 2.0 * cell
    left, bottom = min(xs) - margin, min(ys) - margin
    columns = math.ceil((max(xs) + margin - left) / cell) + 1
    rows = math.ceil((max(ys) + margin - bottom) / cell) + 1

    def at(i: int, j: int) -> Point2D:
        return Point2D(left + i * cell, bottom + j * cell)

    # How far inside the shape each grid point is (negative inside).
    level = [
        [
            min(_segment_distance(at(i, j), a, b) for a, b in segments) - half_width
            for j in range(rows)
        ]
        for i in range(columns)
    ]

    def crossing(key: tuple[str, int, int]) -> Point2D:
        kind, i, j = key
        a = level[i][j]
        b = level[i + 1][j] if kind == "h" else level[i][j + 1]
        t = a / (a - b)
        start = at(i, j)
        if kind == "h":
            return Point2D(start.x + t * cell, start.y)
        return Point2D(start.x, start.y + t * cell)

    # Each cell joins the edges its outline crosses, two by two.
    links: dict[tuple[str, int, int], list[tuple[str, int, int]]] = {}

    def join(first: tuple[str, int, int], second: tuple[str, int, int]) -> None:
        links.setdefault(first, []).append(second)
        links.setdefault(second, []).append(first)

    for i in range(columns - 1):
        for j in range(rows - 1):
            corners = (
                level[i][j],
                level[i + 1][j],
                level[i + 1][j + 1],
                level[i][j + 1],
            )
            inside = [value < 0.0 for value in corners]
            if all(inside) or not any(inside):
                continue
            # Edges counter-clockwise from the bottom, each between two
            # corners in that order.
            edges = (("h", i, j), ("v", i + 1, j), ("h", i, j + 1), ("v", i, j))
            crossed = [edges[k] for k in range(4) if inside[k] != inside[(k + 1) % 4]]
            if len(crossed) == 2:
                join(crossed[0], crossed[1])
                continue
            # A saddle: the middle decides which corners are joined.
            middle_inside = sum(corners) / 4.0 < 0.0
            if middle_inside == inside[0]:
                join(edges[0], edges[1])
                join(edges[2], edges[3])
            else:
                join(edges[3], edges[0])
                join(edges[1], edges[2])

    loops: list[tuple[Point2D, ...]] = []
    unvisited = set(links)
    while unvisited:
        start = unvisited.pop()
        loop = [start]
        previous, current = start, links[start][0]
        while current != start:
            unvisited.discard(current)
            loop.append(current)
            following = links[current]
            nxt = following[0] if following[0] != previous else following[1]
            previous, current = current, nxt
        loops.append(_thinned([crossing(key) for key in loop], tolerance))
    # Holes (a loop inside another) are filled: only the outer ones stay.
    outer = [
        loop
        for loop in loops
        if not any(
            other is not loop and point_in_polygon(loop[0], other) for other in loops
        )
    ]
    return tuple(
        loop if _area(loop) > 0.0 else tuple(reversed(loop))
        for loop in sorted(outer, key=lambda loop: -abs(_area(loop)))
    )


def _segment_distance(point: Point2D, a: Point2D, b: Point2D) -> float:
    """Return the distance from ``point`` to the segment ``a``-``b``."""
    ex, ey = b.x - a.x, b.y - a.y
    length_squared = ex * ex + ey * ey
    t = 0.0
    if length_squared > 0.0:
        t = ((point.x - a.x) * ex + (point.y - a.y) * ey) / length_squared
        t = min(1.0, max(0.0, t))
    return math.hypot(a.x + ex * t - point.x, a.y + ey * t - point.y)


def _area(points: Sequence[Point2D]) -> float:
    """Return a closed polygon's signed area (positive counter-clockwise)."""
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


def _thinned(points: list[Point2D], tolerance: float) -> tuple[Point2D, ...]:
    """Return a closed loop with the points it can do without left out.

    Douglas-Peucker on the loop split at its two points furthest apart.
    """
    if len(points) < 4:
        return tuple(points)
    first = 0
    far = max(
        range(len(points)),
        key=lambda index: math.dist(
            (points[0].x, points[0].y), (points[index].x, points[index].y)
        ),
    )
    halves = (points[first : far + 1], [*points[far:], points[first]])
    kept: list[Point2D] = []
    for half in halves:
        kept.extend(_simplified(half, tolerance)[:-1])
    return tuple(kept)


def _simplified(points: Sequence[Point2D], tolerance: float) -> list[Point2D]:
    """Return an open polyline's Douglas-Peucker simplification."""
    if len(points) < 3:
        return list(points)
    start, end = points[0], points[-1]
    worst, index = -1.0, 0
    for position in range(1, len(points) - 1):
        distance = _segment_distance(points[position], start, end)
        if distance > worst:
            worst, index = distance, position
    if worst <= tolerance:
        return [start, end]
    return [
        *_simplified(points[: index + 1], tolerance)[:-1],
        *_simplified(points[index:], tolerance),
    ]
