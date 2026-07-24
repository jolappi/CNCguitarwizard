"""Top-view outline geometry for a guitar neck and heel."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import NeckGeometryError
from ..fret import FretCalculator
from ..primitives import Line2D, Point2D
from .centerline import Centerline


@dataclass(frozen=True, slots=True)
class NeckOutline:
    """Represent the top-view neck taper and parallel heel.

    The tapered section runs from the nut to the final fret. The heel begins
    at the final fret and continues at a constant width.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets.
        nut_width: Neck width at the nut in millimetres.
        last_fret_width: Neck width at the final fret in millimetres.
        heel_width: Constant heel width in millimetres.
        heel_length: Heel length after the final fret in millimetres.

    Raises:
        NeckGeometryError: If dimensions cannot form a valid neck outline.
    """

    scale_length: float
    fret_count: int
    nut_width: float
    last_fret_width: float
    heel_width: float
    heel_length: float
    centerline: Centerline = field(init=False)
    last_fret_position: float = field(init=False)
    nut_line: Line2D = field(init=False)
    last_fret_line: Line2D = field(init=False)
    heel_end_line: Line2D = field(init=False)
    left_taper: Line2D = field(init=False)
    right_taper: Line2D = field(init=False)
    left_heel: Line2D = field(init=False)
    right_heel: Line2D = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and construct the outline segments."""
        self._validate()

        centerline = Centerline(self.scale_length)
        last_fret_position = FretCalculator.calculate(
            self.scale_length,
            self.fret_count,
        )[-1].distance_from_nut
        heel_end = last_fret_position + self.heel_length

        nut_left = Point2D(0.0, self.nut_width / 2.0)
        nut_right = Point2D(0.0, -self.nut_width / 2.0)
        last_fret_left = Point2D(
            last_fret_position,
            self.last_fret_width / 2.0,
        )
        last_fret_right = Point2D(
            last_fret_position,
            -self.last_fret_width / 2.0,
        )
        heel_start_left = Point2D(last_fret_position, self.heel_width / 2.0)
        heel_start_right = Point2D(last_fret_position, -self.heel_width / 2.0)
        heel_end_left = Point2D(heel_end, self.heel_width / 2.0)
        heel_end_right = Point2D(heel_end, -self.heel_width / 2.0)

        object.__setattr__(self, "centerline", centerline)
        object.__setattr__(self, "last_fret_position", last_fret_position)
        object.__setattr__(self, "nut_line", Line2D(nut_left, nut_right))
        object.__setattr__(
            self,
            "last_fret_line",
            Line2D(last_fret_left, last_fret_right),
        )
        object.__setattr__(
            self,
            "heel_end_line",
            Line2D(heel_end_left, heel_end_right),
        )
        object.__setattr__(self, "left_taper", Line2D(nut_left, last_fret_left))
        object.__setattr__(self, "right_taper", Line2D(nut_right, last_fret_right))
        object.__setattr__(
            self,
            "left_heel",
            Line2D(heel_start_left, heel_end_left),
        )
        object.__setattr__(
            self,
            "right_heel",
            Line2D(heel_start_right, heel_end_right),
        )
        object.__setattr__(
            self,
            "boundary",
            (
                nut_left,
                nut_right,
                last_fret_right,
                heel_start_right,
                heel_end_right,
                heel_end_left,
                heel_start_left,
                last_fret_left,
            ),
        )

    def _validate(self) -> None:
        """Reject non-manufacturable outline dimensions."""
        dimensions = (
            self.scale_length,
            self.nut_width,
            self.last_fret_width,
            self.heel_width,
            self.heel_length,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise NeckGeometryError(
                "Neck outline dimensions must be finite and positive."
            )
        if self.fret_count <= 0:
            raise NeckGeometryError("Fret count must be greater than zero.")
        if self.last_fret_width < self.nut_width:
            raise NeckGeometryError(
                "Last-fret width must not be narrower than the nut."
            )
        if self.heel_width < self.last_fret_width:
            raise NeckGeometryError(
                "Heel width must not be narrower than the final fret."
            )
