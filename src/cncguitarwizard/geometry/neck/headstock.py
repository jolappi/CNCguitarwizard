"""Top- and side-view reference geometry for a tapered headstock."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Literal

from ..exceptions import GeometryException, HeadstockGeometryError
from ..primitives import Line2D, Point2D, Point3D, SmoothCurve

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
        bass_edge: A drawn bass-side edge: ``(distance from the nut,
            half-width)`` points ending at the tip (``distance ==
            length``), or ``None`` for the tapered shape above. The edge
            is a ``SmoothCurve`` from the nut's half-width through them,
            rounding through its points (it may swing past them).
        treble_edge: The same for the treble side; give both or neither.
        tip_points: Points shaping a drawn headstock's tip between the two
            edges' tip corners: ``(how far past the tip line, y)``, with
            ``y`` strictly between the corners' and increasing. The tip is
            then a rounded curve (Catmull–Rom) from corner to corner
            through them, leaving each corner along its edge, so a round
            Stratocaster-like end meets its sides without a corner; empty,
            it is the straight cut ``tip_line``. A negative distance
            notches the tip.

    Raises:
        HeadstockGeometryError: If dimensions cannot form the tapered
            outline, a drawn edge does not end at the tip, does not run
            away from the nut, or crosses the other edge, or a tip point
            lies outside the tip or reaches back to the nut.
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
    bass_edge: tuple[tuple[float, float], ...] | None = None
    treble_edge: tuple[tuple[float, float], ...] | None = None
    tip_points: tuple[tuple[float, float], ...] = ()
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
        distances: tuple[float, ...] = (
            *(
                self.shoulder_distance * index / self.side_curve_segments
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
        if self.is_drawn:
            distances = self._drawn_distances()
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
        tip = self.tip_outline()[1:-1]
        object.__setattr__(
            self,
            "boundary",
            (
                nut_left,
                *right_side,
                *tip,
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
        self._validate_drawn()
        self._validate_tip()
        for side in ("bass", "treble"):
            if self._shoulder_half(side) < self.nut_width / 2.0:
                raise HeadstockGeometryError(
                    f"Headstock shoulder on the {side} side must not be "
                    "narrower than the nut."
                )

    @property
    def is_drawn(self) -> bool:
        """Return whether the edges were drawn rather than tapered."""
        return self.bass_edge is not None

    def _edge_curve(self, side: Side) -> SmoothCurve:
        edge = self.bass_edge if side == "bass" else self.treble_edge
        assert edge is not None
        return SmoothCurve(((0.0, self.nut_width / 2.0), *edge))

    def _drawn_distances(self) -> tuple[float, ...]:
        """Sample the drawn edges every 2.5 mm and at every control point."""
        assert self.bass_edge is not None and self.treble_edge is not None
        steps = max(2, math.ceil(self.length / 2.5))
        samples = {self.length * index / steps for index in range(steps + 1)}
        samples.update(d for d, _ in (*self.bass_edge, *self.treble_edge))
        return tuple(sorted(samples))

    def _validate_drawn(self) -> None:
        if (self.bass_edge is None) != (self.treble_edge is None):
            raise HeadstockGeometryError("Draw both headstock edges, or neither.")
        if self.bass_edge is None or self.treble_edge is None:
            return
        for side, edge in (("bass", self.bass_edge), ("treble", self.treble_edge)):
            if not edge:
                raise HeadstockGeometryError(f"The {side} edge needs a tip point.")
            if not math.isclose(edge[-1][0], self.length, abs_tol=1e-6):
                raise HeadstockGeometryError(
                    f"The drawn {side} edge must end at the tip, "
                    f"{self.length:g} mm from the nut."
                )
            try:
                SmoothCurve(((0.0, self.nut_width / 2.0), *edge))
            except GeometryException as error:
                raise HeadstockGeometryError(
                    f"The drawn {side} edge must run from the nut to the tip "
                    f"without doubling back ({error})"
                ) from error
        for distance in self._drawn_distances():
            if self.width_at_distance(distance) < 1.0:
                raise HeadstockGeometryError(
                    f"The drawn edges meet or cross {distance:.0f} mm from the nut."
                )

    def _validate_tip(self) -> None:
        if not self.tip_points:
            return
        if not self.is_drawn:
            raise HeadstockGeometryError("Only a drawn headstock's tip takes points.")
        low = -self.half_width_at_y(self.length, -1.0)
        high = self.half_width_at_y(self.length, 1.0)
        previous = low
        for past, y in self.tip_points:
            if not (math.isfinite(past) and math.isfinite(y)):
                raise HeadstockGeometryError("Headstock tip points must be finite.")
            if not previous < y < high:
                raise HeadstockGeometryError(
                    "Headstock tip points must run across the tip, between its "
                    f"corners ({low:.1f} to {high:.1f} mm), in order."
                )
            if self.length + past <= self.shoulder_distance:
                raise HeadstockGeometryError(
                    "A headstock tip point must stay past the shoulder."
                )
            previous = y

    TIP_SAMPLES_PER_SEGMENT = 16
    """Points sampled per span of a shaped tip."""

    def tip_outline(self) -> tuple[Point2D, ...]:
        """Return the tip from its -Y corner to its +Y corner.

        A straight cut without tip points; otherwise a Catmull–Rom curve
        through them, leaving and reaching each corner along that side's
        edge (its tangent as long as the span's chord).
        """
        low = Point2D(-self.length, self.edge_y(self.length, -1.0))
        high = Point2D(-self.length, self.edge_y(self.length, 1.0))
        if not self.tip_points:
            return (low, high)
        points = [
            low,
            *(Point2D(-(self.length + past), y) for past, y in self.tip_points),
            high,
        ]

        def edge_direction(y_sign: float) -> tuple[float, float]:
            # Along the edge away from the nut, per mm of distance.
            step = min(0.5, self.length / 10.0)
            slope = (
                self.edge_y(self.length, y_sign)
                - self.edge_y(self.length - step, y_sign)
            ) / step
            norm = math.hypot(1.0, slope)
            return (-1.0 / norm, slope / norm)

        tangents: list[tuple[float, float]] = []
        for index, point in enumerate(points):
            if index == 0:
                chord = math.hypot(points[1].x - point.x, points[1].y - point.y)
                dx, dy = edge_direction(-1.0)
                tangents.append((dx * chord, dy * chord))
            elif index == len(points) - 1:
                chord = math.hypot(points[-2].x - point.x, points[-2].y - point.y)
                dx, dy = edge_direction(1.0)
                # Arriving: the edge's own direction, back toward the nut.
                tangents.append((-dx * chord, -dy * chord))
            else:
                before, after = points[index - 1], points[index + 1]
                tangents.append(
                    ((after.x - before.x) / 2.0, (after.y - before.y) / 2.0)
                )
        samples = [points[0]]
        count = self.TIP_SAMPLES_PER_SEGMENT
        for index in range(len(points) - 1):
            p0, p1 = points[index], points[index + 1]
            (m0x, m0y), (m1x, m1y) = tangents[index], tangents[index + 1]
            for step in range(1, count + 1):
                t = step / count
                t2, t3 = t * t, t * t * t
                h00, h10 = 2 * t3 - 3 * t2 + 1, t3 - 2 * t2 + t
                h01, h11 = -2 * t3 + 3 * t2, t3 - t2
                samples.append(
                    Point2D(
                        h00 * p0.x + h10 * m0x + h01 * p1.x + h11 * m1x,
                        h00 * p0.y + h10 * m0y + h01 * p1.y + h11 * m1y,
                    )
                )
        return tuple(samples)

    @property
    def reach(self) -> float:
        """Return how far the headstock reaches from the nut, tip included."""
        return max(self.length, *(-point.x for point in self.tip_outline()))

    def tip_clearance(self, point: Point2D) -> float:
        """Return how far ``point`` lies from the tip, along its outline."""
        outline = self.tip_outline()
        return min(
            _segment_distance(point, a, b)
            for a, b in zip(outline, outline[1:], strict=False)
        )

    def envelope_y(self, distance: float, y_sign: float) -> float:
        """Return the +Y (``1.0``) or -Y edge's Y, the shaped tip included.

        Up to the tip line it is ``edge_y``; past it, the outer of the
        tip corner's and the tip's own furthest reach on that side, so a
        solid built to this envelope covers a tip that bulges out.
        """
        edge = self.edge_y(distance, y_sign)
        if distance <= self.length or not self.tip_points:
            return edge
        reach = max(y_sign * point.y for point in self.tip_outline())
        return y_sign * max(y_sign * edge, reach)

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
        if self.is_drawn:
            return self._edge_curve(side).value_at(distance)
        if distance <= self.shoulder_distance:
            fraction = distance / self.shoulder_distance
            blend = self._smoothstep(fraction)
            return (
                self.nut_width / 2.0
                + (self._shoulder_half(side) - self.nut_width / 2.0) * blend
            )
        fraction = (distance - self.shoulder_distance) / (
            self.length - self.shoulder_distance
        )
        return (
            self._shoulder_half(side)
            + (self._tip_half(side) - self._shoulder_half(side)) * fraction
        )

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


def _segment_distance(point: Point2D, a: Point2D, b: Point2D) -> float:
    """Return the distance from ``point`` to the segment ``a``–``b``."""
    dx, dy = b.x - a.x, b.y - a.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0.0:
        return math.hypot(point.x - a.x, point.y - a.y)
    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / length_squared
    t = max(0.0, min(1.0, t))
    return math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy))


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
            or self.angle_degrees < 0.0
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
    16 mm, while the supported manufacturing range is 14–16 mm. The face
    passes ``face_drop`` below the glue plane at the nut and falls at the
    angle from there: a flat (0 degree) headstock is set down this way so
    the strings still break over the nut toward the tuners.

    Args:
        plan: Two-dimensional headstock boundary.
        angle: Angled center-plane reference matching the plan length.
        thickness: Finished headstock thickness in millimetres.
        face_drop: How far the face lies below the glue plane at the nut,
            in millimetres (0 for a face through the nut line).
        nut_lean: The nut line's lean, X gained per millimetre of Y (a
            slanted or fanned nut; 0 for a square one).
        nut_seat_length: The nut's flat seat behind the nut line, level
            with the glue face: the nut is glued to it and to the
            fretboard's end. The face starts right behind it, following
            the nut line.
        face_transition_length: How far behind the seat the top eases
            from the seat down onto the face (see ``top_z``: a smooth S for
            an angled face, a Stratocaster style cove for one set down); 0
            for a sharp break. The face
            itself stays square to the neck: it falls from the seat's
            front-most end, so a leaning seat only turns the transition.

    Raises:
        HeadstockGeometryError: If references disagree or thickness is
            outside the supported range.
    """

    plan: HeadstockPlan
    angle: HeadstockAngleReference
    thickness: float = 16.0
    face_drop: float = 0.0
    nut_lean: float = 0.0
    nut_seat_length: float = 0.0
    face_transition_length: float = 0.0
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
        if not math.isfinite(self.nut_lean):
            raise HeadstockGeometryError("Headstock nut lean must be finite.")
        if not math.isfinite(self.nut_seat_length) or self.nut_seat_length < 0.0:
            raise HeadstockGeometryError("The nut seat length must be zero or more.")
        if (
            not math.isfinite(self.face_transition_length)
            or self.face_transition_length < 0.0
        ):
            raise HeadstockGeometryError(
                "The headstock face transition must be zero or longer."
            )
        if not math.isfinite(self.face_drop) or self.face_drop < 0.0:
            raise HeadstockGeometryError(
                "Headstock face drop must be zero or more."
            )

        radians = math.radians(self.angle.angle_degrees)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        top_boundary = tuple(
            Point3D(point.x, point.y, self.face_z(point.x))
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

    @property
    def face_pivot_x(self) -> float:
        """Return where the face plane leaves the glue plane (before any drop).

        The seat's front-most end: the face falls square to the neck from
        there, so it starts right behind a square seat and never rises
        above the glue plane behind a leaning one.
        """
        return self.nut_reach - self.nut_seat_length

    def face_z(self, x: float) -> float:
        """Return the face plane's height at ``x`` (behind the seat)."""
        tangent = math.tan(math.radians(self.angle.angle_degrees))
        return (x - self.face_pivot_x) * tangent - self.face_drop

    def top_z(self, x: float, y: float) -> float:
        """Return the neck's top height at (x, y) near and past the nut.

        Level with the glue face over the seat (and toward the neck), the
        face past the transition, and between them a curve that meets the
        face at its own slope. An angled face that starts at the glue
        plane is eased in with a ``smoothstep`` (level at the seat too); a
        face set down (``face_drop``) is reached through a Stratocaster
        style cove, a concave cup that leaves the seat's edge falling
        (at about 34 degrees for 4 mm over 12 mm) and flattens onto the
        face.
        """
        seat_end = self.face_start_x(y)
        if x >= seat_end:
            return 0.0
        # Never above the glue plane: out past the nut's width a leaning
        # seat's line runs ahead of the face's pivot.
        face = min(self.face_z(x), 0.0)
        length = self.face_transition_length
        if length <= 0.0 or x <= seat_end - length:
            return face
        t = (seat_end - x) / length
        if self.face_drop > 0.0:
            return (1.0 - (1.0 - t) ** 2) * face
        return (3.0 * t * t - 2.0 * t * t * t) * face

    def face_start_x(self, y: float) -> float:
        """Return where the face starts at ``y``: right behind the nut seat."""
        return self.nut_lean * y - self.nut_seat_length

    @property
    def nut_reach(self) -> float:
        """Return how far a leaning nut line reaches back past x = 0."""
        return abs(self.nut_lean) * self.plan.nut_width / 2.0

    @property
    def is_flat(self) -> bool:
        """Return whether the face neither falls nor is set down."""
        return self.angle.angle_degrees == 0.0 and self.face_drop == 0.0


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
        station_distances: Nut-to-hole distances in millimetres; none for a
            headless neck's headpiece.
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
            raise HeadstockGeometryError("Tuner edge clearance must not be negative.")
        if self.minimum_hole_clearance < 0.0:
            raise HeadstockGeometryError("Tuner-hole clearance must not be negative.")
        if any(distance <= 0.0 for distance in self.station_distances):
            raise HeadstockGeometryError("Tuner stations must lie beyond the nut.")
        # No stations at all is a headless neck's headpiece: no tuners.
        if len(self.station_distances) != len(self.side_offsets):
            raise HeadstockGeometryError("Tuner stations need one side offset each.")
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
                or self.headstock.tip_clearance(hole.center) < required_clearance
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
