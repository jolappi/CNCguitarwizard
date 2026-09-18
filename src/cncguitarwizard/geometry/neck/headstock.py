"""Top- and side-view reference geometry for a tapered headstock."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Literal

from ..exceptions import HeadstockGeometryError
from ..primitives import Line2D, Point2D, Point3D

Side = Literal["bass", "treble"]
"""Which physical side of the centerline a feature is on.

The bass side is +Y on a right-handed neck (``bass_sign = 1.0``) and -Y
on a left-handed one (``bass_sign = -1.0``).
"""


@dataclass(frozen=True, slots=True)
class HeadstockPlan:
    """Represent a modern tapered headstock outline, symmetric by default.

    The nut is at ``x = 0`` and the headstock extends in the negative x
    direction. A short shoulder transition widens the outline before it
    runs straight to the tip reference width, which may be narrower (a
    tapered tip) or wider (a Strat-style lobe). The outline can be
    shifted sideways at the shoulder and at the tip (``shoulder_shift``,
    ``tip_shift``, positive toward the bass side) for an in-line or 4+2
    tuner layout, whose tuners sit along one edge; the nut stays centred
    on the neck. A shift may carry one edge past the centerline, so each
    side's "half-width" is a signed edge distance and only the total
    width has to stay positive. ``bass_sign`` says which way the bass side lies:
    +Y on a right-handed neck, -Y on a left-handed one.

    Args:
        length: Nut-to-tip plan length in millimetres.
        nut_width: Width at the nut in millimetres.
        shoulder_distance: Distance from nut to maximum width.
        shoulder_width: Maximum headstock width in millimetres.
        tip_width: Width at the headstock tip in millimetres.
        side_curve_segments: Sample count per side curve.
        shoulder_shift: Lateral offset of the outline's centre at the
            shoulder, toward the bass side.
        tip_shift: Lateral offset of the outline's centre at the tip,
            toward the bass side.
        bass_sign: +1.0 when the bass side is +Y (right-handed), -1.0
            when it is -Y (left-handed).

    Raises:
        HeadstockGeometryError: If dimensions cannot form the tapered outline.
    """

    length: float
    nut_width: float
    shoulder_distance: float
    shoulder_width: float
    tip_width: float
    side_curve_segments: int = 8
    shoulder_shift: float = 0.0
    tip_shift: float = 0.0
    bass_sign: float = 1.0
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
            self.half_width_at_y(self.shoulder_distance, 1.0),
        )
        shoulder_right = Point2D(
            -self.shoulder_distance,
            -self.half_width_at_y(self.shoulder_distance, -1.0),
        )
        tip_left = Point2D(-self.length, self.half_width_at_y(self.length, 1.0))
        tip_right = Point2D(-self.length, -self.half_width_at_y(self.length, -1.0))
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
            Point2D(-distance, -self.half_width_at_y(distance, -1.0))
            for distance in distances
        )
        left_side = tuple(
            Point2D(-distance, self.half_width_at_y(distance, 1.0))
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
        if self.side_curve_segments < 2:
            raise HeadstockGeometryError(
                "Headstock side curves require at least two segments."
            )
        if not all(
            math.isfinite(value) for value in (self.shoulder_shift, self.tip_shift)
        ):
            raise HeadstockGeometryError("Headstock shifts must be finite.")
        if self.bass_sign not in (1.0, -1.0):
            raise HeadstockGeometryError("Headstock bass_sign must be +1 or -1.")
        for side in ("bass", "treble"):
            if self._shoulder_half(side) < self.nut_width / 2.0:
                raise HeadstockGeometryError(
                    f"Headstock shoulder on the {side} side must not be "
                    "narrower than the nut."
                )

    def _shoulder_half(self, side: Side) -> float:
        sign = 1.0 if side == "bass" else -1.0
        return self.shoulder_width / 2.0 + sign * self.shoulder_shift

    def _tip_half(self, side: Side) -> float:
        sign = 1.0 if side == "bass" else -1.0
        return self.tip_width / 2.0 + sign * self.tip_shift

    def half_width_at(self, distance: float, side: Side) -> float:
        """Return one side's centerline-to-edge distance at a nut distance.

        Negative when that edge has crossed the centerline.
        """
        if distance <= self.shoulder_distance:
            fraction = distance / self.shoulder_distance
            blend = self._smoothstep(fraction)
            return self.nut_width / 2.0 + (
                self._shoulder_half(side) - self.nut_width / 2.0
            ) * blend
        fraction = (distance - self.shoulder_distance) / (
            self.length - self.shoulder_distance
        )
        return self._shoulder_half(side) + (
            self._tip_half(side) - self._shoulder_half(side)
        ) * fraction

    def side_of_y(self, y_sign: float) -> Side:
        """Return the physical side lying toward +Y (``1.0``) or -Y (``-1.0``)."""
        return "bass" if y_sign * self.bass_sign > 0.0 else "treble"

    def half_width_at_y(self, distance: float, y_sign: float) -> float:
        """Return the edge distance toward +Y or -Y at a nut distance."""
        return self.half_width_at(distance, self.side_of_y(y_sign))

    def edge_y(self, distance: float, y_sign: float) -> float:
        """Return the Y coordinate of the +Y (``1.0``) or -Y edge."""
        return y_sign * self.half_width_at_y(distance, y_sign)

    def width_at_distance(self, distance: float) -> float:
        """Return the full edge-to-edge width at a nut-to-tip distance."""
        return self.half_width_at(distance, "bass") + self.half_width_at(
            distance, "treble"
        )

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
    side: Side
    center: Point2D
    diameter: float


@dataclass(frozen=True, slots=True)
class TunerLayout:
    """Place and validate the tuner holes on a headstock.

    Station distances are measured from the nut toward the tip. Side offsets
    are distances from the centerline toward the hole's side. Without
    ``sides`` every station is mirrored onto both sides — the symmetric
    3+3 layout — and offsets must be positive. With ``sides`` each station
    is one hole on the named physical side, which describes 6-in-line and
    4+2 layouts (and their reverses) as well; an offset may then be
    negative for a hole of that side's row that has crossed the
    centerline. The headstock plan's ``bass_sign`` says which way the
    bass side lies.

    Args:
        headstock: Headstock plan that contains the holes.
        hole_diameter: Finished tuner-hole diameter in millimetres.
        station_distances: Nut-to-hole distances in millimetres.
        side_offsets: Centerline offsets in millimetres, one per station.
        minimum_edge_clearance: Required material outside every hole.
        minimum_hole_clearance: Required gap between hole edges.
        sides: The side of each station, or ``None`` to mirror every
            station onto both sides.

    Raises:
        HeadstockGeometryError: If holes overlap or violate clearances.
    """

    headstock: HeadstockPlan
    hole_diameter: float = 10.0
    station_distances: tuple[float, ...] = (60.0, 95.0, 130.0)
    side_offsets: tuple[float, ...] = (21.0, 18.0, 15.0)
    minimum_edge_clearance: float = 2.0
    minimum_hole_clearance: float = 10.0
    sides: tuple[Side, ...] | None = None
    holes: tuple[TunerHole, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Construct holes and verify manufacturing clearances."""
        self._validate_parameters()

        holes: list[TunerHole] = []
        for side in ("bass", "treble"):
            sign = self.headstock.bass_sign * (1.0 if side == "bass" else -1.0)
            stations = [
                (distance, offset)
                for index, (distance, offset) in enumerate(
                    zip(self.station_distances, self.side_offsets, strict=True)
                )
                if self.sides is None or self.sides[index] == side
            ]
            holes.extend(
                TunerHole(
                    index=index,
                    side=side,
                    center=Point2D(-distance, sign * offset),
                    diameter=self.hole_diameter,
                )
                for index, (distance, offset) in enumerate(stations, start=1)
            )
        self._validate_edge_clearance(tuple(holes))
        self._validate_hole_clearance(tuple(holes))
        object.__setattr__(self, "holes", tuple(holes))

    def holes_on(self, side: Side) -> tuple[TunerHole, ...]:
        """Return the holes on one side, nut to tip."""
        return tuple(hole for hole in self.holes if hole.side == side)

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
        if len(self.station_distances) != len(self.side_offsets) or not (
            self.station_distances
        ):
            raise HeadstockGeometryError(
                "Tuner stations need one side offset each."
            )
        if self.sides is not None:
            if len(self.sides) != len(self.station_distances):
                raise HeadstockGeometryError("Tuner stations need one side each.")
            if any(side not in ("bass", "treble") for side in self.sides):
                raise HeadstockGeometryError('Tuner sides must be "bass" or "treble".')
        for side in ("bass", "treble"):
            distances = tuple(
                distance
                for index, distance in enumerate(self.station_distances)
                if self.sides is None or self.sides[index] == side
            )
            if tuple(sorted(distances)) != distances:
                raise HeadstockGeometryError(
                    "Tuner stations must be ordered from nut to tip."
                )
        if self.sides is None and any(offset <= 0.0 for offset in self.side_offsets):
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

            upper = self.headstock.edge_y(distance, 1.0)
            lower = self.headstock.edge_y(distance, -1.0)
            if (
                hole.center.y + required_clearance > upper
                or hole.center.y - required_clearance < lower
            ):
                raise HeadstockGeometryError(
                    f"Tuner {hole.side} {hole.index} violates side-edge clearance."
                )

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
            min(
                self.headstock.edge_y(-hole.center.x, 1.0) - hole.center.y,
                hole.center.y - self.headstock.edge_y(-hole.center.x, -1.0),
            )
            - hole.diameter / 2.0
            for hole in self.holes
        )
