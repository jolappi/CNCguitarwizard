"""Top- and side-view reference geometry for a tapered headstock."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Literal

from ..exceptions import HeadstockGeometryError
from ..primitives import Line2D, Point2D, Point3D


@dataclass(frozen=True, slots=True)
class HeadstockPlan:
    """Represent a symmetric, modern tapered 3+3 headstock outline.

    The nut is at ``x = 0`` and the headstock extends in the negative x
    direction. A short shoulder transition widens the outline before it
    tapers toward the rounded-tip reference width.

    Args:
        length: Nut-to-tip plan length in millimetres.
        nut_width: Width at the nut in millimetres.
        shoulder_distance: Distance from nut to maximum width.
        shoulder_width: Maximum headstock width in millimetres.
        tip_width: Width at the headstock tip in millimetres.

    Raises:
        HeadstockGeometryError: If dimensions cannot form the tapered outline.
    """

    length: float
    nut_width: float
    shoulder_distance: float
    shoulder_width: float
    tip_width: float
    side_curve_segments: int = 8
    nut_line: Line2D = field(init=False)
    shoulder_line: Line2D = field(init=False)
    tip_line: Line2D = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and construct the symmetric outline."""
        self._validate()

        nut_left = Point2D(0.0, self.nut_width / 2.0)
        nut_right = Point2D(0.0, -self.nut_width / 2.0)
        shoulder_left = Point2D(
            -self.shoulder_distance,
            self.shoulder_width / 2.0,
        )
        shoulder_right = Point2D(
            -self.shoulder_distance,
            -self.shoulder_width / 2.0,
        )
        tip_left = Point2D(-self.length, self.tip_width / 2.0)
        tip_right = Point2D(-self.length, -self.tip_width / 2.0)
        distances = (
            *(
                self.shoulder_distance
                * index
                / self.side_curve_segments
                for index in range(self.side_curve_segments + 1)
            ),
            *(
                self.shoulder_distance
                + (self.length - self.shoulder_distance)
                * index
                / self.side_curve_segments
                for index in range(1, self.side_curve_segments + 1)
            ),
        )
        right_side = tuple(
            Point2D(-distance, -self.width_at_distance(distance) / 2.0)
            for distance in distances
        )
        left_side = tuple(
            Point2D(-distance, self.width_at_distance(distance) / 2.0)
            for distance in distances
        )

        object.__setattr__(self, "nut_line", Line2D(nut_left, nut_right))
        object.__setattr__(
            self,
            "shoulder_line",
            Line2D(shoulder_left, shoulder_right),
        )
        object.__setattr__(self, "tip_line", Line2D(tip_left, tip_right))
        object.__setattr__(
            self,
            "boundary",
            (
                nut_left,
                *right_side,
                *reversed(left_side[1:]),
            ),
        )

    def _validate(self) -> None:
        """Reject dimensions that cannot form the intended tapered shape."""
        dimensions = (
            self.length,
            self.nut_width,
            self.shoulder_distance,
            self.shoulder_width,
            self.tip_width,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise HeadstockGeometryError(
                "Headstock plan dimensions must be finite and positive."
            )
        if self.shoulder_distance >= self.length:
            raise HeadstockGeometryError(
                "Headstock shoulder must lie between the nut and tip."
            )
        if self.shoulder_width < self.nut_width:
            raise HeadstockGeometryError(
                "Headstock shoulder must not be narrower than the nut."
            )
        if self.tip_width >= self.shoulder_width:
            raise HeadstockGeometryError(
                "Headstock tip must be narrower than the shoulder."
            )
        if self.side_curve_segments < 2:
            raise HeadstockGeometryError(
                "Headstock side curves require at least two segments."
            )

    def width_at_distance(self, distance: float) -> float:
        """Return smooth side width at a nut-to-tip distance."""
        if distance <= self.shoulder_distance:
            fraction = distance / self.shoulder_distance
            blend = self._smoothstep(fraction)
            return self.nut_width + (
                self.shoulder_width - self.nut_width
            ) * blend
        fraction = (distance - self.shoulder_distance) / (
            self.length - self.shoulder_distance
        )
        return self.shoulder_width + (
            self.tip_width - self.shoulder_width
        ) * fraction

    @staticmethod
    def _smoothstep(fraction: float) -> float:
        """Return cubic interpolation with zero slope at both ends."""
        return fraction * fraction * (3.0 - 2.0 * fraction)


@dataclass(frozen=True, slots=True)
class HeadstockAngleReference:
    """Represent the angled headstock center plane in side view.

    Args:
        length: Nut-to-tip plan length in millimetres.
        angle_degrees: Downward headstock angle in degrees.

    Raises:
        HeadstockGeometryError: If length or angle is outside the supported
            physical range.
    """

    length: float
    angle_degrees: float
    tip_drop: float = field(init=False)
    reference_line: Line2D = field(init=False)

    def __post_init__(self) -> None:
        """Validate inputs and construct the angled reference line."""
        if not math.isfinite(self.length) or self.length <= 0.0:
            raise HeadstockGeometryError(
                "Headstock reference length must be finite and positive."
            )
        if (
            not math.isfinite(self.angle_degrees)
            or self.angle_degrees <= 0.0
            or self.angle_degrees >= 90.0
        ):
            raise HeadstockGeometryError(
                "Headstock angle must be between zero and 90 degrees."
            )

        tip_drop = self.length * math.tan(math.radians(self.angle_degrees))
        object.__setattr__(self, "tip_drop", tip_drop)
        object.__setattr__(
            self,
            "reference_line",
            Line2D(
                Point2D(0.0, 0.0),
                Point2D(-self.length, -tip_drop),
            ),
        )


@dataclass(frozen=True, slots=True)
class HeadstockSolid:
    """Represent an angled headstock blank with configurable thickness.

    Thickness is measured normal to the headstock face. Prototype001 uses
    16 mm, while the supported manufacturing range is 14–16 mm.

    Args:
        plan: Two-dimensional headstock boundary.
        angle: Angled center-plane reference matching the plan length.
        thickness: Finished headstock thickness in millimetres.

    Raises:
        HeadstockGeometryError: If references disagree or thickness is
            outside the supported range.
    """

    plan: HeadstockPlan
    angle: HeadstockAngleReference
    thickness: float = 16.0
    top_boundary: tuple[Point3D, ...] = field(init=False)
    bottom_boundary: tuple[Point3D, ...] = field(init=False)
    extrusion_vector: Point3D = field(init=False)

    def __post_init__(self) -> None:
        """Validate references and construct the angled solid boundaries."""
        if not math.isclose(self.plan.length, self.angle.length):
            raise HeadstockGeometryError(
                "Headstock plan and angle reference must share a length."
            )
        if not math.isfinite(self.thickness) or not 14.0 <= self.thickness <= 16.0:
            raise HeadstockGeometryError(
                "Headstock thickness must be between 14 and 16 mm."
            )

        radians = math.radians(self.angle.angle_degrees)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        tangent = math.tan(radians)
        top_boundary = tuple(
            Point3D(
                point.x,
                point.y,
                point.x * tangent,
            )
            for point in self.plan.boundary
        )
        extrusion_vector = Point3D(
            self.thickness * sine,
            0.0,
            -self.thickness * cosine,
        )
        bottom_boundary = tuple(
            Point3D(
                point.x + extrusion_vector.x,
                point.y + extrusion_vector.y,
                point.z + extrusion_vector.z,
            )
            for point in top_boundary
        )

        object.__setattr__(self, "top_boundary", top_boundary)
        object.__setattr__(self, "bottom_boundary", bottom_boundary)
        object.__setattr__(self, "extrusion_vector", extrusion_vector)


@dataclass(frozen=True, slots=True)
class TunerHole:
    """Represent one circular tuner-hole feature in plan view.

    Args:
        index: One-based position from nut toward tip on its side.
        side: Bass or treble side of the headstock.
        center: Hole-center point.
        diameter: Finished hole diameter in millimetres.
    """

    index: int
    side: Literal["bass", "treble"]
    center: Point2D
    diameter: float


@dataclass(frozen=True, slots=True)
class TunerLayout:
    """Place and validate six tuner holes on a symmetric 3+3 headstock.

    Station distances are measured from the nut toward the tip. Side offsets
    are positive distances from the centerline. Both sequences are ordered
    from nut to tip.

    Args:
        headstock: Headstock plan that contains the holes.
        hole_diameter: Finished tuner-hole diameter in millimetres.
        station_distances: Three nut-to-hole distances in millimetres.
        side_offsets: Three centerline offsets in millimetres.
        minimum_edge_clearance: Required material outside every hole.
        minimum_hole_clearance: Required gap between hole edges.

    Raises:
        HeadstockGeometryError: If holes overlap or violate clearances.
    """

    headstock: HeadstockPlan
    hole_diameter: float = 10.0
    station_distances: tuple[float, float, float] = (60.0, 95.0, 130.0)
    side_offsets: tuple[float, float, float] = (21.0, 18.0, 15.0)
    minimum_edge_clearance: float = 2.0
    minimum_hole_clearance: float = 10.0
    holes: tuple[TunerHole, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Construct holes and verify manufacturing clearances."""
        self._validate_parameters()

        bass_holes = tuple(
            TunerHole(
                index=index,
                side="bass",
                center=Point2D(-distance, offset),
                diameter=self.hole_diameter,
            )
            for index, (distance, offset) in enumerate(
                zip(self.station_distances, self.side_offsets, strict=True),
                start=1,
            )
        )
        treble_holes = tuple(
            TunerHole(
                index=index,
                side="treble",
                center=Point2D(-distance, -offset),
                diameter=self.hole_diameter,
            )
            for index, (distance, offset) in enumerate(
                zip(self.station_distances, self.side_offsets, strict=True),
                start=1,
            )
        )
        holes = bass_holes + treble_holes
        self._validate_edge_clearance(holes)
        self._validate_hole_clearance(holes)
        object.__setattr__(self, "holes", holes)

    def _validate_parameters(self) -> None:
        """Reject invalid layout parameters before constructing holes."""
        scalar_values = (
            self.hole_diameter,
            self.minimum_edge_clearance,
            self.minimum_hole_clearance,
            *self.station_distances,
            *self.side_offsets,
        )
        if not all(math.isfinite(value) for value in scalar_values):
            raise HeadstockGeometryError("Tuner layout values must be finite.")
        if self.hole_diameter <= 0.0:
            raise HeadstockGeometryError(
                "Tuner-hole diameter must be greater than zero."
            )
        if self.minimum_edge_clearance < 0.0:
            raise HeadstockGeometryError(
                "Tuner edge clearance must not be negative."
            )
        if self.minimum_hole_clearance < 0.0:
            raise HeadstockGeometryError(
                "Tuner-hole clearance must not be negative."
            )
        if any(distance <= 0.0 for distance in self.station_distances):
            raise HeadstockGeometryError(
                "Tuner stations must lie beyond the nut."
            )
        if tuple(sorted(self.station_distances)) != self.station_distances:
            raise HeadstockGeometryError(
                "Tuner stations must be ordered from nut to tip."
            )
        if any(offset <= 0.0 for offset in self.side_offsets):
            raise HeadstockGeometryError(
                "Tuner side offsets must be greater than zero."
            )

    def _validate_edge_clearance(self, holes: tuple[TunerHole, ...]) -> None:
        """Ensure each circular hole remains inside the headstock."""
        required_clearance = self.hole_diameter / 2.0 + self.minimum_edge_clearance
        for hole in holes:
            distance = -hole.center.x
            if (
                distance < required_clearance
                or distance > self.headstock.length - required_clearance
            ):
                raise HeadstockGeometryError(
                    f"Tuner {hole.side} {hole.index} violates nut or tip clearance."
                )

            half_width = self._half_width_at(distance)
            if abs(hole.center.y) + required_clearance > half_width:
                raise HeadstockGeometryError(
                    f"Tuner {hole.side} {hole.index} violates side-edge clearance."
                )

    def _half_width_at(self, distance: float) -> float:
        """Return the curved-plan half-width at a nut distance."""
        return self.headstock.width_at_distance(distance) / 2.0

    def _validate_hole_clearance(self, holes: tuple[TunerHole, ...]) -> None:
        """Ensure the circular holes do not overlap each other."""
        minimum_center_distance = self.hole_diameter + self.minimum_hole_clearance
        for first, second in combinations(holes, 2):
            center_distance = math.hypot(
                second.center.x - first.center.x,
                second.center.y - first.center.y,
            )
            if center_distance < minimum_center_distance:
                raise HeadstockGeometryError(
                    "Tuner holes violate the requested hole-to-hole clearance."
                )

    @property
    def minimum_side_edge_clearance(self) -> float:
        """Return the least wood between a hole and a headstock side edge."""
        return min(
            self._half_width_at(-hole.center.x)
            - abs(hole.center.y)
            - hole.diameter / 2.0
            for hole in self.holes
        )
