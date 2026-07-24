"""Fret-slot segments clipped to a tapered fretboard outline."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator, FretLine
from ..primitives import Line2D, Point2D
from .fretboard import Fretboard


@dataclass(frozen=True, slots=True)
class FretLayout:
    """Compose equal-temperament fret slots with a fretboard outline.

    Each slot is perpendicular to the fretboard centerline and terminates
    exactly at the tapered left and right edges.

    Args:
        fretboard: Fretboard whose outline bounds every slot.
        fret_count: Number of fret slots to generate.

    Raises:
        FretboardGeometryError: If the fret count or fretboard dimensions
            cannot produce valid manufacturing geometry.
    """

    fretboard: Fretboard
    fret_count: int
    slots: tuple[Line2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate inputs and construct all bounded fret-slot segments."""
        self._validate()

        positions = FretCalculator.calculate(
            self.fretboard.scale_length,
            self.fret_count,
        )
        slots = tuple(self._create_slot(FretLine(self.fretboard.centerline, position))
                      for position in positions)
        object.__setattr__(self, "slots", slots)

    def _validate(self) -> None:
        """Reject dimensions that cannot form a useful fret layout."""
        values = (
            self.fretboard.scale_length,
            self.fretboard.nut_width,
            self.fretboard.bridge_width,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise FretboardGeometryError(
                "Scale length and fretboard widths must be finite and positive."
            )
        if self.fret_count <= 0:
            raise FretboardGeometryError("Fret count must be greater than zero.")

    def _create_slot(self, fret_line: FretLine) -> Line2D:
        """Return one fret line clipped to the tapered fretboard."""
        fraction = (
            fret_line.position.distance_from_nut / self.fretboard.scale_length
        )
        width = (
            self.fretboard.nut_width
            + (self.fretboard.bridge_width - self.fretboard.nut_width) * fraction
        )
        half_width = width / 2.0
        direction = fret_line.direction
        location = fret_line.location

        left = Point2D(
            location.x + direction.x * half_width,
            location.y + direction.y * half_width,
        )
        right = Point2D(
            location.x - direction.x * half_width,
            location.y - direction.y * half_width,
        )
        return Line2D(left, right)
