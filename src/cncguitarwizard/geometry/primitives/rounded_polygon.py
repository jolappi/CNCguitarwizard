"""Corner-rounding for closed two-dimensional polygons."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .point2d import Point2D
from .vector2d import Vector2D


def rounded_polygon_points(
    vertices: Sequence[Point2D],
    radii: Sequence[float],
    samples_per_corner: int = 8,
) -> tuple[Point2D, ...]:
    """Return a closed outline that rounds each vertex by its own radius.

    Each vertex is replaced by a tangent circular arc cut into that
    corner, exactly as a CAD fillet rounds a polygon corner. A radius of
    zero keeps that vertex sharp. The straight run between one corner's
    arc and the next is left implicit: connecting the returned points in
    order with straight lines reproduces it.

    Args:
        vertices: Ordered corner points of the polygon to round.
        radii: Fillet radius for each vertex, matched by index to
            ``vertices``. A radius that would overrun either adjacent
            edge is silently reduced to the largest one that fits.
        samples_per_corner: Number of points used to approximate each
            rounded corner's arc.

    Returns:
        Outline points forming one closed polygon loop.
    """
    count = len(vertices)
    points: list[Point2D] = []
    for index in range(count):
        previous = vertices[index - 1]
        current = vertices[index]
        following = vertices[(index + 1) % count]
        radius = radii[index]
        if radius <= 0.0:
            points.append(current)
            continue
        points.extend(
            _round_corner(
                previous,
                current,
                following,
                radius,
                samples_per_corner,
            )
        )
    return tuple(points)


def _round_corner(
    previous: Point2D,
    current: Point2D,
    following: Point2D,
    radius: float,
    samples: int,
) -> tuple[Point2D, ...]:
    """Return the arc points that round one polygon vertex."""
    to_previous = Vector2D(previous.x - current.x, previous.y - current.y)
    to_following = Vector2D(following.x - current.x, following.y - current.y)
    if to_previous.length == 0.0 or to_following.length == 0.0:
        return (current,)

    direction_previous = to_previous.normalized()
    direction_following = to_following.normalized()
    half_angle = direction_previous.angle_to(direction_following) / 2.0
    if half_angle < 1e-6:
        return (current,)

    tangent_length = min(
        radius / math.tan(half_angle),
        to_previous.length * 0.5,
        to_following.length * 0.5,
    )
    if tangent_length <= 0.0:
        return (current,)
    effective_radius = tangent_length * math.tan(half_angle)

    start = Point2D(
        current.x + direction_previous.x * tangent_length,
        current.y + direction_previous.y * tangent_length,
    )
    end = Point2D(
        current.x + direction_following.x * tangent_length,
        current.y + direction_following.y * tangent_length,
    )
    bisector_vector = Vector2D(
        direction_previous.x + direction_following.x,
        direction_previous.y + direction_following.y,
    )
    if bisector_vector.length == 0.0:
        return (start, end)
    bisector = bisector_vector.normalized()
    distance_to_center = effective_radius / math.sin(half_angle)
    center = Point2D(
        current.x + bisector.x * distance_to_center,
        current.y + bisector.y * distance_to_center,
    )

    start_angle = math.atan2(start.y - center.y, start.x - center.x)
    end_angle = math.atan2(end.y - center.y, end.x - center.x)
    sweep = (end_angle - start_angle + math.pi) % (2.0 * math.pi) - math.pi

    return tuple(
        Point2D(
            center.x
            + effective_radius * math.cos(start_angle + sweep * step / samples),
            center.y
            + effective_radius * math.sin(start_angle + sweep * step / samples),
        )
        for step in range(samples + 1)
    )
