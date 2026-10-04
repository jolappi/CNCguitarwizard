"""Decorative engraving: lines cut a set depth into the body's top, or
closed shapes cleared flat to their levels (a relief)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import BodyGeometryError
from ..primitives import Point2D


@dataclass(frozen=True, slots=True)
class EngravedPocket:
    """A closed shape cleared flat below the face: one level of a relief.

    Args:
        outline: Its closed outline, model frame.
        depth: How deep its floor lies below the face over it.
        face_drop: How far that face lies below the top's full height (a
            stepped top's band; ``0`` on a flat top). The face is level
            over the whole shape.
        within: The index of the earlier, shallower pocket it lies inside
            (cut from that one's floor), or ``None``.
    """

    outline: tuple[Point2D, ...]
    depth: float
    face_drop: float = 0.0
    within: int | None = None


@dataclass(frozen=True, slots=True)
class Engraving:
    """Lines engraved into the top face with a V-bit, or a relief.

    Args:
        lines: Open polylines along the bit's centre, model frame.
        depth: How deep every line is cut below the face, and the deepest
            pocket.
        pockets: Closed shapes cleared flat to their own depths (a relief,
            ``EngravedPocket``), cut with a flat end mill.

    Raises:
        BodyGeometryError: For a non-positive depth, a line of fewer than
            two points, or a pocket deeper than ``depth``, of fewer than
            three points, or inside one that is not earlier and shallower.
    """

    lines: tuple[tuple[Point2D, ...], ...]
    depth: float
    pockets: tuple[EngravedPocket, ...] = ()

    def __post_init__(self) -> None:
        """Reject an engraving that cannot be cut."""
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise BodyGeometryError("Engraving depth must be positive.")
        if any(len(line) < 2 for line in self.lines):
            raise BodyGeometryError("Every engraved line needs two points or more.")
        for index, pocket in enumerate(self.pockets):
            if len(pocket.outline) < 3:
                raise BodyGeometryError("Every engraved pocket needs three points.")
            if not 0.0 < pocket.depth <= self.depth + 1e-9:
                raise BodyGeometryError(
                    "An engraved pocket must be no deeper than the engraving."
                )
            if pocket.within is not None and not (
                0 <= pocket.within < index
                and self.pockets[pocket.within].depth < pocket.depth
            ):
                raise BodyGeometryError(
                    "An engraved pocket inside another must come after it, deeper."
                )

    def length(self) -> float:
        """Return the total length of the engraved lines, in mm."""
        return sum(
            math.dist((a.x, a.y), (b.x, b.y))
            for line in self.lines
            for a, b in zip(line, line[1:], strict=False)
        )
