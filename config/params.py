from dataclasses import dataclass

@dataclass
class NeckParameters:
    scale: float = 609.6
    frets: int = 24

    nut_width: float = 42.0
    width_24: float = 56.0

    fingerboard_radius: float = 430.0
    fingerboard_thickness: float = 6.0

    neck_thickness_1: float = 17.0
    neck_thickness_12: float = 19.0

    heel_width: float = 63.0
    heel_length: float = 150.0

    headstock_angle: float = 8.0

    tuner_hole: float = 10.0

    trussrod_length: float = 440.0
    trussrod_width: float = 6.0
    trussrod_depth: float = 9.0

    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
