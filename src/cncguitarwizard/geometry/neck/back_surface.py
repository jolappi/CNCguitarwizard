"""Lofted three-dimensional surface for the neck back."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from ..exceptions import NeckGeometryError
from ..fret import FretCalculator
from ..primitives import Point3D, QuadFace, SurfaceMesh
from .outline import NeckOutline


@dataclass(frozen=True, slots=True)
class NeckBackSurface:
    """Generate a loft-ready mesh through the neck profile references.

    The longitudinal surface passes exactly through the nut, fret 1, fret 12,
    final fret, and heel-end reference stations. Each interval is divided
    into the same configurable number of segments.

    Args:
        neck_outline: Top-view outline controlling local neck width.
        first_fret_thickness: Wood depth at fret 1.
        twelfth_fret_thickness: Wood depth at fret 12.
        final_fret_thickness: Wood depth at the final fret.
        exponent: Superellipse exponent controlling the D profile.
        profile_sample_count: Odd number of points across each section.
        segments_per_region: Longitudinal segments between reference stations.

    Raises:
        NeckGeometryError: If dimensions or mesh resolution are invalid.
    """

    neck_outline: NeckOutline
    first_fret_thickness: float
    twelfth_fret_thickness: float
    final_fret_thickness: float
    exponent: float = 3.5
    profile_sample_count: int = 33
    segments_per_region: int = 8
    station_positions: tuple[float, ...] = field(init=False)
    mesh: SurfaceMesh = field(init=False)

    def __post_init__(self) -> None:
        """Validate parameters and construct all mesh rows and faces."""
        self._validate()

        fret_positions = FretCalculator.calculate(
            self.neck_outline.scale_length,
            self.neck_outline.fret_count,
        )
        first_position = fret_positions[0].distance_from_nut
        twelfth_position = fret_positions[11].distance_from_nut
        final_position = fret_positions[-1].distance_from_nut
        heel_end_position = final_position + self.neck_outline.heel_length
        station_positions = self._build_station_positions(
            (
                0.0,
                first_position,
                twelfth_position,
                final_position,
                heel_end_position,
            )
        )
        rows = tuple(
            self._build_profile_row(position)
            for position in station_positions
        )
        faces = tuple(
            QuadFace(
                first_pair[0],
                first_pair[1],
                second_pair[1],
                second_pair[0],
            )
            for first_row, second_row in pairwise(rows)
            for first_pair, second_pair in zip(
                pairwise(first_row),
                pairwise(second_row),
                strict=True,
            )
        )

        object.__setattr__(self, "station_positions", station_positions)
        object.__setattr__(self, "mesh", SurfaceMesh(rows, faces))

    def _validate(self) -> None:
        """Reject invalid geometry and mesh-resolution values."""
        dimensions = (
            self.first_fret_thickness,
            self.twelfth_fret_thickness,
            self.final_fret_thickness,
            self.exponent,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise NeckGeometryError(
                "Neck-back surface dimensions must be finite and positive."
            )
        if not (
            self.first_fret_thickness
            <= self.twelfth_fret_thickness
            <= self.final_fret_thickness
        ):
            raise NeckGeometryError(
                "Neck-back thickness must not decrease toward the heel."
            )
        if self.exponent < 2.0:
            raise NeckGeometryError(
                "Neck-back surface exponent must be at least two."
            )
        if (
            self.profile_sample_count < 3
            or self.profile_sample_count % 2 == 0
        ):
            raise NeckGeometryError(
                "Profile sample count must be an odd integer of at least three."
            )
        if self.segments_per_region < 1:
            raise NeckGeometryError(
                "At least one longitudinal segment per region is required."
            )
        if self.neck_outline.fret_count < 12:
            raise NeckGeometryError(
                "At least 12 frets are required for the neck-back surface."
            )

    def _build_station_positions(
        self,
        references: tuple[float, ...],
    ) -> tuple[float, ...]:
        """Return ordered stations including every thickness reference."""
        positions: list[float] = []
        for region_index, (start, end) in enumerate(pairwise(references)):
            for segment in range(self.segments_per_region + 1):
                if region_index > 0 and segment == 0:
                    continue
                fraction = segment / self.segments_per_region
                positions.append(start + (end - start) * fraction)
        return tuple(positions)

    def _build_profile_row(self, position: float) -> tuple[Point3D, ...]:
        """Return one D-profile row at a longitudinal station."""
        width = self._width_at(position)
        depth = self._depth_at(position)
        half_width = width / 2.0
        step = width / (self.profile_sample_count - 1)

        return tuple(
            self._surface_point(
                position,
                -half_width + index * step,
                half_width,
                depth,
            )
            for index in range(self.profile_sample_count)
        )

    def _surface_point(
        self,
        position: float,
        lateral: float,
        half_width: float,
        depth: float,
    ) -> Point3D:
        """Return one sampled point on a station superellipse."""
        normalized_lateral = abs(lateral) / half_width
        normalized_depth = (1.0 - normalized_lateral**self.exponent) ** (
            1.0 / self.exponent
        )
        return Point3D(position, lateral, -depth * normalized_depth)

    def _width_at(self, position: float) -> float:
        """Return linearly tapered width at a longitudinal position."""
        if position >= self.neck_outline.last_fret_position:
            return self.neck_outline.heel_width
        fraction = position / self.neck_outline.last_fret_position
        return (
            self.neck_outline.nut_width
            + (
                self.neck_outline.last_fret_width
                - self.neck_outline.nut_width
            )
            * fraction
        )

    def _depth_at(self, position: float) -> float:
        """Return piecewise-linear depth through the locked references."""
        first_position = self.station_positions_reference(1)
        twelfth_position = self.station_positions_reference(12)
        final_position = self.neck_outline.last_fret_position

        if position >= final_position:
            return self.final_fret_thickness
        if position <= first_position:
            return self.first_fret_thickness
        if position <= twelfth_position:
            return self._interpolate_value(
                position,
                first_position,
                twelfth_position,
                self.first_fret_thickness,
                self.twelfth_fret_thickness,
            )
        return self._interpolate_value(
            position,
            twelfth_position,
            final_position,
            self.twelfth_fret_thickness,
            self.final_fret_thickness,
        )

    def station_positions_reference(self, fret_number: int) -> float:
        """Return the calculated longitudinal position of one fret."""
        return FretCalculator.calculate(
            self.neck_outline.scale_length,
            fret_number,
        )[-1].distance_from_nut

    @staticmethod
    def _interpolate_value(
        position: float,
        start_position: float,
        end_position: float,
        start_value: float,
        end_value: float,
    ) -> float:
        """Linearly interpolate a value between longitudinal references."""
        fraction = (position - start_position) / (end_position - start_position)
        return start_value + (end_value - start_value) * fraction
