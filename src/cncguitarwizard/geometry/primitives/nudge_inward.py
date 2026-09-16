"""Nudge a closed outline's points a hair toward its own interior."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .point2d import Point2D


def nudge_inward(points: Sequence[Point2D], distance: float) -> list[Point2D]:
    """Return ``points`` each moved ``distance`` into the polygon they bound.

    Every vertex moves along the bisector of its two edges' inward
    normals, so the result lies inside the outline at convex *and*
    concave corners alike — unlike moving toward the outline's centre,
    which at a concave fillet can land outside. Used to test whether one
    outline encloses another when the two share walls, where a point
    exactly on the shared edge would make ray casting a coin toss.
    """
    count = len(points)
    if count < 3:
        return list(points)
    area = 0.0
    for index in range(count):
        first, second = points[index], points[(index + 1) % count]
        area += first.x * second.y - second.x * first.y
    # Interior lies to the left of each edge of a counter-clockwise loop.
    sign = 1.0 if area >= 0.0 else -1.0
    nudged: list[Point2D] = []
    for index in range(count):
        previous = points[index - 1]
        current = points[index]
        following = points[(index + 1) % count]
        nx = ny = 0.0
        for start, end in ((previous, current), (current, following)):
            dx, dy = end.x - start.x, end.y - start.y
            length = math.hypot(dx, dy)
            if length == 0.0:
                continue
            nx += sign * -dy / length
            ny += sign * dx / length
        length = math.hypot(nx, ny)
        if length == 0.0:
            nudged.append(current)
            continue
        nx, ny = nx / length * distance, ny / length * distance
        nudged.append(Point2D(current.x + nx, current.y + ny))
    return nudged
