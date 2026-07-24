"""Equal-temperament fret position values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FretPosition:
    """Represent a calculated position for one fret.

    Args:
        number: One-based fret number.
        distance_from_nut: Distance from the nut along the scale in millimetres.
        remaining_scale: Distance from the fret to the bridge in millimetres.
    """

    number: int
    distance_from_nut: float
    remaining_scale: float
