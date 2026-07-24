"""Immutable two-dimensional point primitive."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point2D:
    """Represent a point in two-dimensional space.

    The point is immutable, making it safe to share between
    geometry objects without accidental modification.

    Args:
        x: Horizontal coordinate in millimetres.
        y: Vertical coordinate in millimetres.
    """

    x: float
    y: float
