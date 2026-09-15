"""Point-in-polygon containment test."""

from __future__ import annotations

from collections.abc import Sequence

from .point2d import Point2D


def point_in_polygon(point: Point2D, polygon: Sequence[Point2D]) -> bool:
    """Return whether a point lies inside a closed polygon.

    Uses the standard ray-casting algorithm: a point is inside when a
    ray cast from it to infinity crosses the polygon boundary an odd
    number of times. Points exactly on the boundary may resolve either
    way; callers that need a safety margin should shrink the polygon
    (or the test point's offset from it) before calling this.

    Args:
        point: The point to test.
        polygon: Ordered vertices of one closed polygon loop.

    Returns:
        True if the point lies inside the polygon.
    """
    inside = False
    count = len(polygon)
    for index in range(count):
        first = polygon[index]
        second = polygon[(index + 1) % count]
        crosses = (first.y > point.y) != (second.y > point.y)
        if not crosses:
            continue
        intersect_x = (second.x - first.x) * (point.y - first.y) / (
            second.y - first.y
        ) + first.x
        if point.x < intersect_x:
            inside = not inside
    return inside
