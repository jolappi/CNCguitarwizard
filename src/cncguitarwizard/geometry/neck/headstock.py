"""Top- and side-view reference geometry for a tapered headstock."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Literal

from ..exceptions import HeadstockGeometryError
from ..primitives import Line2D, Point2D


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
                nut_right,
                shoulder_right,
                tip_right,
                tip_left,
                shoulder_left,
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
        """Return the linearly interpolated half-width at a nut distance."""
        if distance <= self.headstock.shoulder_distance:
            fraction = distance / self.headstock.shoulder_distance
            width = (
                self.headstock.nut_width
                + (self.headstock.shoulder_width - self.headstock.nut_width)
                * fraction
            )
            return width / 2.0

        taper_length = self.headstock.length - self.headstock.shoulder_distance
        fraction = (distance - self.headstock.shoulder_distance) / taper_length
        width = (
            self.headstock.shoulder_width
            + (self.headstock.tip_width - self.headstock.shoulder_width) * fraction
        )
        return width / 2.0

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
