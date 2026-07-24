"""Guitar neck centerline geometry."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from ..exceptions import GeometryException
from ..primitives import Line2D, Point2D


@dataclass(frozen=True, slots=True)
class Centerline:
    """Represent the reference centerline of a guitar neck.

    Args:
        scale_length: Distance from the nut to the bridge in millimetres.

    Raises:
        GeometryException: If ``scale_length`` is not greater than zero.
    """

    scale_length: float
    line: Line2D = field(init=False)

    def __post_init__(self) -> None:
        """Validate the scale length and construct the centerline segment."""
        if not isfinite(self.scale_length) or self.scale_length <= 0.0:
            raise GeometryException(
                "Scale length must be a finite value greater than zero."
            )

        object.__setattr__(
            self,
            "line",
            Line2D(Point2D(0.0, 0.0), Point2D(self.scale_length, 0.0)),
        )

    @property
    def length(self) -> float:
        """Return the centerline length in millimetres."""
        return self.line.length
