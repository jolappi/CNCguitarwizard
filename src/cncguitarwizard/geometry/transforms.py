"""Transform immutable two-dimensional geometry points."""

from __future__ import annotations

import math

from .primitives import Point2D, Vector2D


def translate(point: Point2D, vector: Vector2D) -> Point2D:
    """Return a point displaced by a vector.

    The translation formula is ``(x + dx, y + dy)``.

    Args:
        point: Point to translate.
        vector: Displacement to apply.

    Returns:
        A new translated point.
    """
    return Point2D(point.x + vector.x, point.y + vector.y)


def rotate(point: Point2D, angle: float) -> Point2D:
    """Return a point rotated about the origin by an angle in radians.

    The rotation formula is ``(x cos(a) - y sin(a), x sin(a) + y cos(a))``.

    Args:
        point: Point to rotate about the origin.
        angle: Counter-clockwise rotation angle in radians.

    Returns:
        A new rotated point.
    """
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return Point2D(
        point.x * cosine - point.y * sine,
        point.x * sine + point.y * cosine,
    )


def mirror_x(point: Point2D) -> Point2D:
    """Return a point mirrored across the x-axis.

    The reflection formula is ``(x, -y)``.

    Args:
        point: Point to mirror.

    Returns:
        A new mirrored point.
    """
    return Point2D(point.x, -point.y)


def mirror_y(point: Point2D) -> Point2D:
    """Return a point mirrored across the y-axis.

    The reflection formula is ``(-x, y)``.

    Args:
        point: Point to mirror.

    Returns:
        A new mirrored point.
    """
    return Point2D(-point.x, point.y)
