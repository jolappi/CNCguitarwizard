"""Immutable guitar neck model built from geometry inputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..geometry.fretboard import Fretboard
from ..geometry.neck import Centerline


@dataclass(frozen=True, slots=True)
class Neck:
    """Represent a guitar neck with its foundation geometry.

    Args:
        scale_length: Nut-to-bridge distance in millimetres.
        nut_width: Fretboard width at the nut in millimetres.
        bridge_width: Fretboard width at the bridge in millimetres.
    """

    scale_length: float
    nut_width: float
    bridge_width: float
    centerline: Centerline = field(init=False)
    fretboard: Fretboard = field(init=False)

    def __post_init__(self) -> None:
        """Create the centerline and fretboard geometry."""
        centerline = Centerline(self.scale_length)
        fretboard = Fretboard(
            self.scale_length,
            self.nut_width,
            self.bridge_width,
            centerline,
        )

        object.__setattr__(self, "centerline", centerline)
        object.__setattr__(self, "fretboard", fretboard)
