"""Lofted three-dimensional surface for the neck back."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from ..exceptions import NeckGeometryError
from ..fret.calculator import FretCalculator
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
        preserve_d_profile_at_heel: Keep the rounded playing profile through
            the heel instead of flattening it into the mounting block.

    Raises:
        NeckGeometryError: If dimensions or mesh resolution are invalid.
    """

    neck_outline: NeckOutline
    first_fret_thickness: float
    twelfth_fret_thickness: float
    final_fret_thickness: float
    nut_transition_thickness: float | None = None
    nut_shelf_length: float = 0.0
    nut_transition_length: float = 0.0
    nut_volute_depth: float = 0.0
    nut_volute_peak_fraction: float = 0.5
    nut_root_side_extension: float = 0.0
    heel_transition_length: float = 0.0
    heel_flat_start_offset: float = 0.0
    heel_scoop_depth: float = 0.0
    heel_root_center_extension: float = 0.0
    preserve_d_profile_at_heel: bool = False
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
        heel_flat_start = final_position - self.heel_flat_start_offset
        heel_transition_start = heel_flat_start - self.heel_transition_length
        station_positions = self._build_station_positions(
            tuple(
                dict.fromkeys(
                    (
                        self.headstock_root_start_position,
                        0.0,
                        self.nut_transition_length,
                        first_position,
                        twelfth_position,
                        heel_transition_start,
                        heel_flat_start,
                        final_position,
                        heel_end_position,
                    )
                )
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
        first_position = self.station_positions_reference(1)
        twelfth_position = self.station_positions_reference(12)
        final_position = self.neck_outline.last_fret_position
        transition_thickness = (
            self.first_fret_thickness
            if self.nut_transition_thickness is None
            else self.nut_transition_thickness
        )
        if (
            not math.isfinite(transition_thickness)
            or transition_thickness < self.first_fret_thickness
        ):
            raise NeckGeometryError(
                "Nut-transition thickness must be finite and at least the "
                "first-fret wood thickness."
            )
        if (
            not math.isfinite(self.nut_shelf_length)
            or self.nut_shelf_length < 0.0
        ):
            raise NeckGeometryError(
                "Nut shelf length must be finite and non-negative."
            )
        if (
            not math.isfinite(self.nut_transition_length)
            or not 0.0 <= self.nut_transition_length <= first_position
        ):
            raise NeckGeometryError(
                "Nut-transition length must run from zero to fret one."
            )
        if (
            not math.isfinite(self.nut_volute_depth)
            or self.nut_volute_depth < 0.0
            or self.nut_volute_depth > transition_thickness / 2.0
        ):
            raise NeckGeometryError(
                "Nut volute depth must be finite, non-negative, and no "
                "greater than half the nut-transition thickness."
            )
        if (
            not math.isfinite(self.nut_volute_peak_fraction)
            or not 0.05 <= self.nut_volute_peak_fraction <= 0.95
        ):
            raise NeckGeometryError(
                "Nut volute peak fraction must lie between 0.05 and 0.95."
            )
        if (
            not math.isfinite(self.nut_root_side_extension)
            or not 0.0
            <= self.nut_root_side_extension
            <= 30.0
        ):
            raise NeckGeometryError(
                "Nut root side extension must be between 0 and 30 mm."
            )
        if (
            not math.isfinite(self.heel_transition_length)
            or not 0.0
            <= self.heel_transition_length
            <= final_position
            - self.heel_flat_start_offset
            - twelfth_position
        ):
            raise NeckGeometryError(
                "Heel-transition length must fit between fret 12 and the "
                "final fret."
            )
        if (
            not math.isfinite(self.heel_flat_start_offset)
            or not 0.0
            <= self.heel_flat_start_offset
            < final_position - twelfth_position
        ):
            raise NeckGeometryError(
                "Heel flat-start offset must fit after fret 12."
            )
        if (
            not math.isfinite(self.heel_scoop_depth)
            or self.heel_scoop_depth < 0.0
            or self.heel_scoop_depth >= self.final_fret_thickness / 2.0
        ):
            raise NeckGeometryError(
                "Heel scoop depth must be finite, non-negative, and less "
                "than half the heel thickness."
            )
        heel_flat_start = final_position - self.heel_flat_start_offset
        transition_start = heel_flat_start - self.heel_transition_length
        if (
            not math.isfinite(self.heel_root_center_extension)
            or not 0.0
            <= self.heel_root_center_extension
            <= transition_start - twelfth_position
        ):
            raise NeckGeometryError(
                "Heel root center extension must fit between fret 12 and "
                "the heel runout."
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
                index,
                -half_width + index * step,
                half_width,
                depth,
            )
            for index in range(self.profile_sample_count)
        )

    def _surface_point(
        self,
        position: float,
        index: int,
        lateral: float,
        half_width: float,
        depth: float,
    ) -> Point3D:
        """Return one point on the playing profile or a continuous root."""
        normalized_lateral = abs(lateral) / half_width
        side_weight = self._smootherstep(normalized_lateral)
        nut_root_side_weight = self._smootherstep(
            math.sqrt(normalized_lateral)
        )
        center_weight = 1.0 - side_weight
        nut_blend = self._nut_transition_blend_at(
            position,
            nut_root_side_weight,
        )
        heel_blend = self._heel_transition_blend_at(position, center_weight)
        normalized_depth = (1.0 - normalized_lateral**self.exponent) ** (
            1.0 / self.exponent
        )
        curved_z = -depth * normalized_depth
        if heel_blend > 0.0:
            return self._heel_surface_point(
                position,
                index,
                lateral,
                half_width,
                depth,
                curved_z,
                heel_blend,
            )

        last_index = self.profile_sample_count - 1
        if index in (0, last_index):
            flat_lateral = lateral
            flat_z = 0.0
        else:
            flat_fraction = (index - 1) / (self.profile_sample_count - 3)
            flat_lateral = -half_width + 2.0 * half_width * flat_fraction
            flat_z = -depth
        base_point = Point3D(
            position,
            self._interpolate_value(
                nut_blend, 0.0, 1.0, lateral, flat_lateral
            ),
            self._interpolate_value(
                nut_blend, 0.0, 1.0, curved_z, flat_z
            ),
        )
        return base_point

    def _heel_surface_point(
        self,
        position: float,
        index: int,
        lateral: float,
        half_width: float,
        depth: float,
        curved_z: float,
        blend: float,
    ) -> Point3D:
        """Return a D section that progressively becomes the heel rectangle.

        Intermediate sections use a superellipse rather than a linear
        D-to-rectangle interpolation. This makes the center of the back settle
        into the heel plane while the shoulders open outward as continuous
        curves, avoiding the triangular ramp produced by moving every profile
        point along a straight line.
        """
        last_index = self.profile_sample_count - 1
        if index in (0, last_index):
            return Point3D(position, lateral, 0.0)

        heel_exponent = self._interpolate_value(
            blend,
            0.0,
            1.0,
            self.exponent,
            32.0,
        )
        normalized_lateral = abs(lateral) / half_width
        heel_z = -depth * (
            1.0 - normalized_lateral**heel_exponent
        ) ** (1.0 / heel_exponent)
        section_blend = self._smootherstep(blend)
        return Point3D(
            position,
            lateral,
            self._interpolate_value(
                section_blend,
                0.0,
                1.0,
                curved_z,
                heel_z,
            ),
        )

    def _width_at(self, position: float) -> float:
        """Return the fretboard-following taper through the heel."""
        if position <= 0.0:
            return self.neck_outline.nut_width
        final_position = self.neck_outline.last_fret_position
        if position >= final_position:
            return self.neck_outline.heel_width
        fraction = position / final_position
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
        heel_flat_start = final_position - self.heel_flat_start_offset

        if position <= 0.0:
            if self.nut_transition_thickness is None:
                return self.first_fret_thickness
            return self.nut_transition_thickness + self._nut_volute_depth_at(
                position
            )
        if (
            self.nut_transition_thickness is not None
            and self.nut_transition_length > 0.0
            and position < self.nut_transition_length
        ):
            fraction = self._smoothstep(position / self.nut_transition_length)
            base_depth = self._interpolate_value(
                fraction,
                0.0,
                1.0,
                self.nut_transition_thickness,
                self.first_fret_thickness,
            )
            return base_depth + self._nut_volute_depth_at(position)
        if position >= heel_flat_start:
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
        transition_start = heel_flat_start - self.heel_transition_length
        first_position = self.station_positions_reference(1)
        playing_slope = (
            self.twelfth_fret_thickness - self.first_fret_thickness
        ) / (twelfth_position - first_position)
        if self.heel_transition_length <= 0.0:
            return self.twelfth_fret_thickness + playing_slope * (
                position - twelfth_position
            )
        transition_start_depth = self.twelfth_fret_thickness + playing_slope * (
            transition_start - twelfth_position
        )
        if position <= transition_start:
            return self.twelfth_fret_thickness + playing_slope * (
                position - twelfth_position
            )
        fraction = (position - transition_start) / self.heel_transition_length
        tangent_depth = self._hermite_value(
            fraction,
            transition_start_depth,
            self.final_fret_thickness,
            playing_slope * self.heel_transition_length,
            0.0,
        )
        remaining_depth = self.final_fret_thickness - tangent_depth
        total_depth_change = (
            self.final_fret_thickness - transition_start_depth
        )
        scoop = (
            16.0
            * self.heel_scoop_depth
            * fraction**2
            * (1.0 - fraction) ** 2
            * remaining_depth
            / total_depth_change
        )
        return tangent_depth + scoop

    def _nut_transition_blend_at(
        self,
        position: float,
        side_weight: float = 0.0,
    ) -> float:
        """Return the laterally tapered headstock-root blend.

        The centre begins its transition at the nut. Near each fretboard edge,
        the same-length D-profile transition begins farther toward the
        headstock. This forms a rear-facing U-shaped root: the side profiles
        continue past the nut while the centre remains at the nut reference,
        without adding an outward material swell.
        """
        if self.nut_shelf_length > 0.0:
            # The fixed nut shelf stays exactly 5 mm long at the centerline.
            # Only the side rows lead into the D profile earlier, so the
            # shoulders can keep curving right up to the neck end without
            # moving the nut line or extending the shelf.
            shelf_length = self.nut_shelf_length
            shelf_entry_blend = 1.0 - self._smootherstep(side_weight)
            extra_extension = max(
                self.nut_root_side_extension - shelf_length,
                0.0,
            ) * side_weight
            transition_start = -(shelf_length + extra_extension)
            if position < transition_start:
                return 1.0
            if position < -shelf_length and extra_extension > 0.0:
                fraction = (position - transition_start) / extra_extension
                return self._interpolate_value(
                    self._smootherstep(fraction),
                    0.0,
                    1.0,
                    1.0,
                    shelf_entry_blend,
                )
            if position < 0.0:
                shelf_fraction = (position + shelf_length) / shelf_length
                effective_fraction = min(
                    max(shelf_fraction + side_weight, 0.0),
                    1.0,
                )
                return 1.0 - self._smootherstep(effective_fraction)
            return 0.0

        if self.nut_transition_length <= 0.0:
            return 0.0
        fraction = min(
            max(position / self.nut_transition_length, 0.0),
            1.0,
        )
        return 1.0 - self._smootherstep(fraction)

    def _nut_volute_depth_at(self, position: float) -> float:
        """Return the smooth, local extra depth of the headstock volute.

        The volute is a tangent-continuous material swell on the back of the
        neck.  It is zero at the nut and at the end of the volute length, so
        it cannot introduce a step at either adjoining surface.  The peak can
        be moved toward the nut to reproduce a compact Strat-style runout.
        The same shape mirrors onto the headstock side (negative positions),
        so the swell reaches the headstock rather than stopping dead at the
        nut with nothing on the headstock side to meet it.
        """
        if self.nut_transition_length <= 0.0 or self.nut_volute_depth == 0.0:
            return 0.0
        fraction = min(
            max(abs(position) / self.nut_transition_length, 0.0), 1.0
        )
        peak = self.nut_volute_peak_fraction
        if fraction <= peak:
            rise = self._smootherstep(fraction / peak)
        else:
            fall = self._smootherstep((1.0 - fraction) / (1.0 - peak))
            rise = fall
        return self.nut_volute_depth * rise

    @property
    def headstock_root_start_position(self) -> float:
        """Return the earliest station needed by the joined headstock root."""
        return -max(
            self.nut_shelf_length,
            self.nut_root_side_extension,
        )

    def _heel_transition_blend_at(
        self,
        position: float,
        center_weight: float = 0.0,
    ) -> float:
        """Return the laterally tapered D-to-flat bolt-on heel blend.

        The full, planar mounting block always begins at the configured heel
        flat-start station. The centre of its lead-in begins farther toward
        the neck than the two side edges, forming the broad, rounded
        Strat-style triangular root without reducing the flat mounting area.
        """
        final_position = self.neck_outline.last_fret_position
        heel_flat_start = final_position - self.heel_flat_start_offset
        if self.preserve_d_profile_at_heel:
            return 0.0
        if position >= heel_flat_start:
            return 1.0
        if self.heel_transition_length <= 0.0:
            return 0.0
        transition_start = (
            heel_flat_start
            - self.heel_transition_length
            - self.heel_root_center_extension * center_weight
        )
        if position <= transition_start:
            return 0.0
        fraction = (position - transition_start) / (
            heel_flat_start - transition_start
        )
        return self._smootherstep(fraction)

    @staticmethod
    def _smoothstep(fraction: float) -> float:
        """Return cubic interpolation with zero slope at both ends."""
        return fraction * fraction * (3.0 - 2.0 * fraction)

    @staticmethod
    def _smootherstep(fraction: float) -> float:
        """Return quintic interpolation with zero first and second slopes."""
        return fraction**3 * (
            fraction * (fraction * 6.0 - 15.0) + 10.0
        )

    @staticmethod
    def _hermite_value(
        fraction: float,
        start_value: float,
        end_value: float,
        start_tangent: float,
        end_tangent: float,
    ) -> float:
        """Return cubic Hermite interpolation with controlled end tangents."""
        squared = fraction * fraction
        cubed = squared * fraction
        return (
            (2.0 * cubed - 3.0 * squared + 1.0) * start_value
            + (cubed - 2.0 * squared + fraction) * start_tangent
            + (-2.0 * cubed + 3.0 * squared) * end_value
            + (cubed - squared) * end_tangent
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
