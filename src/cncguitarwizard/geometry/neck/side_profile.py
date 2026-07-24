"""Side-view thickness profile for a guitar neck blank."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from ..exceptions import NeckGeometryError
from ..fret import FretCalculator
from ..primitives import Line2D, Point2D
from .outline import NeckOutline


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


@dataclass(frozen=True, slots=True)
class NeckBackCrossSection:
    """Represent a symmetric, spline-like D neck-back section.

    A superellipse is used as a deterministic approximation of a thin D
    profile. An exponent of 2 produces a half ellipse; larger values flatten
    the center and retain fuller shoulders.

    Args:
        width: Neck width at the section in millimetres.
        depth: Neck-wood depth below the fretboard in millimetres.
        exponent: Superellipse exponent controlling the D shape.
        sample_count: Odd number of points used to sample the back curve.

    Raises:
        NeckGeometryError: If dimensions or sampling parameters are invalid.
    """

    width: float
    depth: float
    exponent: float = 3.5
    sample_count: int = 33
    back_curve: tuple[Point2D, ...] = field(init=False)
    underside_line: Line2D = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate parameters and sample the superellipse back curve."""
        dimensions = (self.width, self.depth, self.exponent)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise NeckGeometryError(
                "Neck cross-section dimensions must be finite and positive."
            )
        if self.exponent < 2.0:
            raise NeckGeometryError(
                "Neck profile exponent must be at least two."
            )
        if self.sample_count < 3 or self.sample_count % 2 == 0:
            raise NeckGeometryError(
                "Profile sample count must be an odd integer of at least three."
            )

        half_width = self.width / 2.0
        step = self.width / (self.sample_count - 1)
        back_curve = tuple(
            self._curve_point(-half_width + index * step, half_width)
            for index in range(self.sample_count)
        )
        left_top = Point2D(-half_width, 0.0)
        right_top = Point2D(half_width, 0.0)

        object.__setattr__(self, "back_curve", back_curve)
        object.__setattr__(
            self,
            "underside_line",
            Line2D(left_top, right_top),
        )
        object.__setattr__(
            self,
            "boundary",
            (left_top, right_top, *reversed(back_curve)),
        )

    def _curve_point(self, x_coordinate: float, half_width: float) -> Point2D:
        """Return one point on the lower half of the superellipse."""
        normalized_x = abs(x_coordinate) / half_width
        normalized_depth = (1.0 - normalized_x**self.exponent) ** (
            1.0 / self.exponent
        )
        return Point2D(x_coordinate, -self.depth * normalized_depth)


@dataclass(frozen=True, slots=True)
class NeckProfileStation:
    """Associate one neck cross-section with a fret position and width."""

    fret_number: int
    position: float
    width: float
    cross_section: NeckBackCrossSection


@dataclass(frozen=True, slots=True)
class NeckProfileStations:
    """Generate the first- and twelfth-fret D-profile references.

    Args:
        neck_outline: Top-view outline used to derive local widths.
        first_fret_thickness: Wood depth at fret 1.
        twelfth_fret_thickness: Wood depth at fret 12.
        exponent: Shared superellipse exponent.
        sample_count: Shared curve sample count.
    """

    neck_outline: NeckOutline
    first_fret_thickness: float
    twelfth_fret_thickness: float
    exponent: float = 3.5
    sample_count: int = 33
    first_fret: NeckProfileStation = field(init=False)
    twelfth_fret: NeckProfileStation = field(init=False)

    def __post_init__(self) -> None:
        """Construct both reference stations from the neck taper."""
        if self.neck_outline.fret_count < 12:
            raise NeckGeometryError(
                "At least 12 frets are required for profile stations."
            )
        thicknesses = (
            self.first_fret_thickness,
            self.twelfth_fret_thickness,
        )
        if not all(
            math.isfinite(value) and value > 0.0 for value in thicknesses
        ):
            raise NeckGeometryError(
                "Profile-station thicknesses must be finite and positive."
            )
        if self.first_fret_thickness > self.twelfth_fret_thickness:
            raise NeckGeometryError(
                "First-fret thickness must not exceed twelfth-fret thickness."
            )

        fret_positions = FretCalculator.calculate(
            self.neck_outline.scale_length,
            self.neck_outline.fret_count,
        )
        first_position = fret_positions[0].distance_from_nut
        twelfth_position = fret_positions[11].distance_from_nut
        first_width = self._width_at(first_position)
        twelfth_width = self._width_at(twelfth_position)

        object.__setattr__(
            self,
            "first_fret",
            NeckProfileStation(
                1,
                first_position,
                first_width,
                NeckBackCrossSection(
                    first_width,
                    self.first_fret_thickness,
                    self.exponent,
                    self.sample_count,
                ),
            ),
        )
        object.__setattr__(
            self,
            "twelfth_fret",
            NeckProfileStation(
                12,
                twelfth_position,
                twelfth_width,
                NeckBackCrossSection(
                    twelfth_width,
                    self.twelfth_fret_thickness,
                    self.exponent,
                    self.sample_count,
                ),
            ),
        )

    def _width_at(self, position: float) -> float:
        """Return the linearly tapered neck width at a position."""
        fraction = position / self.neck_outline.last_fret_position
        return (
            self.neck_outline.nut_width
            + (
                self.neck_outline.last_fret_width
                - self.neck_outline.nut_width
            )
            * fraction
        )
