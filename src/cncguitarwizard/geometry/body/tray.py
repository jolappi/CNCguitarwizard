"""A shallow tray routed over the top for an epoxy pour."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import BodyGeometryError
from ..primitives import Point2D


@dataclass(frozen=True, slots=True)
class EpoxyTray:
    """A shallow pocket over the top, walled in, for epoxy to be poured in.

    It is routed ``depth`` down from the top face inside ``outline`` (the
    body's outline, a rim of wood in from its edge), round ``walls`` left
    standing: one round every opening in the top (the neck pocket, the
    pickup routes, the other routes and the holes), so the epoxy stays out
    of them. The epoxy is poured in up to the face and sanded flush.

    Args:
        outline: Its outer edge, in the model frame.
        walls: The walls left standing in it, each an outline.
        depth: How deep it is routed, from the top face.

    Raises:
        BodyGeometryError: For a depth that is not finite and positive, or
            an outline of fewer than three points.
    """

    outline: tuple[Point2D, ...]
    walls: tuple[tuple[Point2D, ...], ...]
    depth: float

    def __post_init__(self) -> None:
        """Reject a tray that cannot be routed."""
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise BodyGeometryError("The epoxy tray's depth must be positive.")
        if len(self.outline) < 3:
            raise BodyGeometryError("The epoxy tray needs an outline.")
