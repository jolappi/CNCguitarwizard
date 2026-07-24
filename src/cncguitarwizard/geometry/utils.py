"""Small utility functions for immutable two-dimensional geometry."""

from __future__ import annotations

from .primitives import Line2D, Point2D


def distance(start: Point2D, end: Point2D) -> float:
    """Return the distance between two points.

    Args:
        start: First point to measure.
        end: Second point to measure.

    Returns:
        Euclidean distance between ``start`` and ``end`` in millimetres.
    """
    return Line2D(start, end).length


def midpoint(start: Point2D, end: Point2D) -> Point2D:
    """Return the point halfway between two points.

    Args:
        start: First point.
        end: Second point.

    Returns:
        A new point at the midpoint of ``start`` and ``end``.
    """
    return interpolate(start, end, 0.5)


def interpolate(start: Point2D, end: Point2D, fraction: float) -> Point2D:
    """Return a point at a fractional position between two points.

    A fraction of ``0.0`` returns ``start`` and a fraction of ``1.0`` returns
    ``end``. Values outside that range extrapolate along the same line.

    Args:
        start: First point.
        end: Second point.
        fraction: Position between the points.

    Returns:
        A new interpolated point.
    """
    return Point2D(
        start.x + (end.x - start.x) * fraction,
        start.y + (end.y - start.y) * fraction,
    )
