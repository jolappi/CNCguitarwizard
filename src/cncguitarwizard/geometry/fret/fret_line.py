"""Geometric fret lines derived from a neck centerline."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..neck.centerline import Centerline
from ..primitives import Point2D, Vector2D
from ..utils import interpolate
from .fret_position import FretPosition


@dataclass(frozen=True, slots=True)
class FretLine:
    """Represent an infinite fret line perpendicular to a centerline.

    A fretboard width is not part of this foundation, so a fret is represented
    by a location and a unit direction instead of an arbitrary line segment.

    Args:
        centerline: Neck reference line that determines the fret location.
        position: Calculated location of the fret along the scale.
    """

    centerline: Centerline
    position: FretPosition
    location: Point2D = field(init=False)
    direction: Vector2D = field(init=False)

    def __post_init__(self) -> None:
        """Derive the fret location and perpendicular direction."""
        fraction = self.position.distance_from_nut / self.centerline.length
        location = interpolate(
            self.centerline.line.start,
            self.centerline.line.end,
            fraction,
        )
        centerline_direction = Vector2D(
            self.centerline.line.end.x - self.centerline.line.start.x,
            self.centerline.line.end.y - self.centerline.line.start.y,
        )

        object.__setattr__(self, "location", location)
        object.__setattr__(
            self,
            "direction",
            centerline_direction.perpendicular().normalized(),
        )
