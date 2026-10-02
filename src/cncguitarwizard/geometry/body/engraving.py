"""Decorative engraving: lines cut a set depth into the body's top."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import BodyGeometryError
from ..primitives import Point2D


@dataclass(frozen=True, slots=True)
class Engraving:
    """Lines engraved into the top face with a V-bit.

    Args:
        lines: Open polylines along the bit's centre, model frame.
        depth: How deep every line is cut below the face.

    Raises:
        BodyGeometryError: For a non-positive depth or a line of fewer
            than two points.
    """

    lines: tuple[tuple[Point2D, ...], ...]
    depth: float

    def __post_init__(self) -> None:
        """Reject an engraving that cannot be cut."""
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise BodyGeometryError("Engraving depth must be positive.")
        if any(len(line) < 2 for line in self.lines):
            raise BodyGeometryError("Every engraved line needs two points or more.")

    def length(self) -> float:
        """Return the total length of the engraved lines, in mm."""
        return sum(
            math.dist((a.x, a.y), (b.x, b.y))
            for line in self.lines
            for a, b in zip(line, line[1:], strict=False)
        )
