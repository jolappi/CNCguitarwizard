"""
Neck parameter definitions.

All dimensions are stored internally in millimetres.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class NeckParameters:
    """Parametric guitar neck definition."""

    scale_length: float = 609.6          # 24"
    fret_count: int = 24

    nut_width: float = 42.0
    heel_width: float = 63.0

    first_fret_thickness: float = 17.0
    twelfth_fret_thickness: float = 19.0

    heel_thickness: float = 20.0

    fretboard_thickness: float = 7.0

    headstock_angle: float = 10.0

    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
