"""Basic immutable 2D line."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .point2d import Point2D


@dataclass(frozen=True, slots=True)
class Line2D:
    """Represent an immutable line segment between two points.

    Args:
        start: First endpoint of the segment.
        end: Second endpoint of the segment.
    """

    start: Point2D
    end: Point2D

    @property
    def length(self) -> float:
        """Return the line segment length in millimetres."""
        return hypot(self.end.x - self.start.x, self.end.y - self.start.y)
