"""Side-view thickness profile for a guitar neck blank."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from ..exceptions import NeckGeometryError
from ..fret import FretCalculator
from ..primitives import Line2D, Point2D


@dataclass(frozen=True, slots=True)
class NeckSideProfile:
    """Represent the longitudinal side profile of the neck wood.

    Thickness values describe the neck wood below the fretboard. The
    fretboard remains a separate geometry layer.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets.
        first_fret_thickness: Wood thickness at fret 1 in millimetres.
        twelfth_fret_thickness: Wood thickness at fret 12 in millimetres.
        heel_thickness: Constant heel wood thickness in millimetres.
        heel_length: Heel length after the final fret in millimetres.

    Raises:
        NeckGeometryError: If the dimensions cannot form a valid profile.
    """

    scale_length: float
    fret_count: int
    first_fret_thickness: float
    twelfth_fret_thickness: float
    heel_thickness: float
    heel_length: float
    first_fret_position: float = field(init=False)
    twelfth_fret_position: float = field(init=False)
    last_fret_position: float = field(init=False)
    heel_end_position: float = field(init=False)
    top_line: Line2D = field(init=False)
    bottom_segments: tuple[Line2D, ...] = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and construct the side-profile boundary."""
        self._validate()

        fret_positions = FretCalculator.calculate(
            self.scale_length,
            self.fret_count,
        )
        first_fret_position = fret_positions[0].distance_from_nut
        twelfth_fret_position = fret_positions[11].distance_from_nut
        last_fret_position = fret_positions[-1].distance_from_nut
        heel_end_position = last_fret_position + self.heel_length

        nut_top = Point2D(0.0, 0.0)
        heel_end_top = Point2D(heel_end_position, 0.0)
        nut_bottom = Point2D(0.0, -self.first_fret_thickness)
        first_fret_bottom = Point2D(
            first_fret_position,
            -self.first_fret_thickness,
        )
        twelfth_fret_bottom = Point2D(
            twelfth_fret_position,
            -self.twelfth_fret_thickness,
        )
        heel_start_bottom = Point2D(
            last_fret_position,
            -self.heel_thickness,
        )
        heel_end_bottom = Point2D(
            heel_end_position,
            -self.heel_thickness,
        )
        bottom_points = (
            nut_bottom,
            first_fret_bottom,
            twelfth_fret_bottom,
            heel_start_bottom,
            heel_end_bottom,
        )

        object.__setattr__(self, "first_fret_position", first_fret_position)
        object.__setattr__(self, "twelfth_fret_position", twelfth_fret_position)
        object.__setattr__(self, "last_fret_position", last_fret_position)
        object.__setattr__(self, "heel_end_position", heel_end_position)
        object.__setattr__(self, "top_line", Line2D(nut_top, heel_end_top))
        object.__setattr__(
            self,
            "bottom_segments",
            tuple(
                Line2D(start, end)
                for start, end in pairwise(bottom_points)
            ),
        )
        object.__setattr__(
            self,
            "boundary",
            (nut_top, nut_bottom, *bottom_points[1:], heel_end_top),
        )

    def _validate(self) -> None:
        """Reject invalid or structurally reversed thickness values."""
        dimensions = (
            self.scale_length,
            self.first_fret_thickness,
            self.twelfth_fret_thickness,
            self.heel_thickness,
            self.heel_length,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise NeckGeometryError(
                "Neck side-profile dimensions must be finite and positive."
            )
        if self.fret_count < 12:
            raise NeckGeometryError(
                "At least 12 frets are required for the thickness profile."
            )
        if self.first_fret_thickness > self.twelfth_fret_thickness:
            raise NeckGeometryError(
                "First-fret thickness must not exceed twelfth-fret thickness."
            )
        if self.twelfth_fret_thickness > self.heel_thickness:
            raise NeckGeometryError(
                "Twelfth-fret thickness must not exceed heel thickness."
            )
