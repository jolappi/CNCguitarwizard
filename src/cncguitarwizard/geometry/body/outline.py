"""Original double-cutaway superstrat-style body outline."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, rounded_polygon_points


@dataclass(frozen=True, slots=True)
class TracedOutline:
    """A body silhouette digitised from an external reference drawing.

    Unlike ``BodyOutline``, this outline is not generated from named
    proportions — its points are supplied directly, already converted
    into the neck's own nut-origin coordinate frame (X = distance from
    the nut, Y = lateral distance from the centerline). It exposes the
    same ``points`` attribute so it can be used anywhere a
    ``BodyOutline`` is accepted.

    Args:
        points: Ordered vertices of one closed polygon loop.

    Raises:
        BodyGeometryError: If fewer than three points are given, or any
            coordinate is non-finite.
    """

    points: tuple[Point2D, ...]

    def __post_init__(self) -> None:
        """Reject a point set too small or malformed to be a silhouette."""
        if len(self.points) < 3:
            raise BodyGeometryError(
                "Traced outline needs at least three points."
            )
        if not all(
            math.isfinite(point.x) and math.isfinite(point.y)
            for point in self.points
        ):
            raise BodyGeometryError(
                "Traced outline points must all be finite."
            )


@dataclass(frozen=True, slots=True)
class BodyOutline:
    """Parametric double-cutaway body silhouette.

    Shares the neck's own coordinate frame: X is distance from the nut,
    Y is lateral distance from the centerline. This is an original
    outline in the general "superstrat" genre — deep, asymmetric
    cutaway horns and a single-point tail — built entirely from named
    proportions rather than traced from any specific instrument, so
    every dimension below is independently adjustable for future
    reshaping.

    Each side is walked as one continuous boundary from its horn tip:
    first the *outer* run away from the neck (tip through the shoulder,
    waist, lower bout, to the tail), then, after the tail point, back up
    the other side's outer run to its own horn tip, and finally the
    short *inner*, cutaway-facing run from each tip to the point where
    the body becomes solid and full-width (``neck_pocket_start``). The
    two sides' inner runs meet there, at the one edge that actually
    crosses the centerline before the tail — the horn tips themselves
    are never connected to each other, since the neck occupies that
    space out to the nut. The neck pocket recess itself (and its own
    end position) is a separate, shallower cavity cut into this solid
    outline, not a feature of the silhouette.

    Args:
        scale_length: Nut-to-bridge distance in millimetres, fixing the
            tail's reference position.
        neck_pocket_start: Longitudinal position where the body becomes
            solid and full-width, matching the front edge of the neck's
            own heel mounting area.
        neck_pocket_half_width: Half-width of the neck heel.
        neck_pocket_wall_clearance: Extra wood width, each side, between
            the heel and the outline at the pocket walls.
        treble_horn_tip_position, bass_horn_tip_position: Longitudinal
            position of each horn's point.
        treble_horn_tip_half_width, bass_horn_tip_half_width: Lateral
            offset of each horn's point from the centerline.
        treble_shoulder_position, bass_shoulder_position: Longitudinal
            position of the outer curve where each horn widens into the
            main bout.
        treble_shoulder_half_width, bass_shoulder_half_width: Lateral
            offset at that shoulder.
        treble_waist_position, bass_waist_position: Longitudinal
            position of the narrowest point between the shoulder and the
            lower bout.
        treble_waist_half_width, bass_waist_half_width: Lateral offset
            at the waist.
        treble_lower_bout_position, bass_lower_bout_position:
            Longitudinal position of each side's widest point.
        treble_lower_bout_half_width, bass_lower_bout_half_width:
            Lateral offset at the widest point. The treble side is
            wider and its horn longer, matching the classic superstrat
            asymmetry.
        tail_extension: Distance from the bridge reference (scale
            length) to the tail point.
        tail_point_extension: Additional reach of the tail's point
            beyond where the two edges converge.
        tail_half_width: Lateral offset where each edge turns in toward
            the tail point.
        horn_tip_radius, shoulder_radius, waist_radius,
        lower_bout_radius, tail_radius: Corner radii blending the
            corresponding vertices into smooth curves.
        samples_per_corner: Points used to approximate each rounded
            corner.

    Raises:
        BodyGeometryError: If a dimension is non-finite, non-positive
            where required, or the horns and tail collapse the outline
            out of longitudinal order.
    """

    scale_length: float
    neck_pocket_start: float
    neck_pocket_half_width: float
    neck_pocket_wall_clearance: float = 3.0

    # The treble side carries the long, sharply-swept cutaway horn and
    # the wider lower bout; the bass side carries the shorter, blunter
    # horn and the narrower bout. (Earlier defaults had these reversed,
    # which mirror-imaged the whole body into a left-handed layout.)
    treble_horn_tip_position: float = 260.0
    treble_horn_tip_half_width: float = 30.0
    treble_shoulder_position: float = 400.0
    treble_shoulder_half_width: float = 100.0
    treble_waist_position: float = 555.0
    treble_waist_half_width: float = 118.0
    treble_lower_bout_position: float = 615.0
    treble_lower_bout_half_width: float = 168.0

    bass_horn_tip_position: float = 350.0
    bass_horn_tip_half_width: float = 34.0
    bass_shoulder_position: float = 385.0
    bass_shoulder_half_width: float = 95.0
    bass_waist_position: float = 560.0
    bass_waist_half_width: float = 78.0
    bass_lower_bout_position: float = 650.0
    bass_lower_bout_half_width: float = 108.0

    tail_extension: float = 150.0
    tail_point_extension: float = 25.0
    tail_half_width: float = 14.0

    # A sharp, narrow radius at the horn tips reads as a proper pointed
    # superstrat spike rather than a rounded paddle.
    horn_tip_radius: float = 5.0
    shoulder_radius: float = 70.0
    waist_radius: float = 90.0
    lower_bout_radius: float = 130.0
    tail_radius: float = 18.0
    neck_pocket_corner_radius: float = 8.0

    samples_per_corner: int = 10
    points: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and build the rounded outline points."""
        self._validate()
        vertices, radii = self._build_vertices()
        object.__setattr__(
            self,
            "points",
            rounded_polygon_points(vertices, radii, self.samples_per_corner),
        )

    @property
    def tail_position(self) -> float:
        """Return the longitudinal position where the two edges meet."""
        return self.scale_length + self.tail_extension

    def _pocket_half_width(self) -> float:
        return self.neck_pocket_half_width + self.neck_pocket_wall_clearance

    def _build_vertices(self) -> tuple[list[Point2D], list[float]]:
        """Return the closed vertex loop and matching per-vertex radii."""
        pocket_half_width = self._pocket_half_width()
        tail_x = self.tail_position
        tail_tip_x = tail_x + self.tail_point_extension

        vertices = [
            Point2D(self.treble_horn_tip_position, self.treble_horn_tip_half_width),
            Point2D(self.treble_shoulder_position, self.treble_shoulder_half_width),
            Point2D(self.treble_waist_position, self.treble_waist_half_width),
            Point2D(
                self.treble_lower_bout_position,
                self.treble_lower_bout_half_width,
            ),
            Point2D(tail_x, self.tail_half_width),
            Point2D(tail_tip_x, 0.0),
            Point2D(tail_x, -self.tail_half_width),
            Point2D(
                self.bass_lower_bout_position,
                -self.bass_lower_bout_half_width,
            ),
            Point2D(self.bass_waist_position, -self.bass_waist_half_width),
            Point2D(self.bass_shoulder_position, -self.bass_shoulder_half_width),
            Point2D(self.bass_horn_tip_position, -self.bass_horn_tip_half_width),
            Point2D(self.neck_pocket_start, -pocket_half_width),
            Point2D(self.neck_pocket_start, pocket_half_width),
        ]
        # The outer run (tip through shoulder, waist, bout, to the tail)
        # is the body's real, continuous edge — it neither knows nor
        # cares about the pocket. Only the *inner*, cutaway-facing edge
        # of each horn ends at the pocket: it runs from that horn's tip
        # straight to its own neck_pocket_start point, and the two
        # neck_pocket_start points connect directly to each other,
        # closing the loop with the one edge that actually crosses the
        # centerline before the tail. Body wood is solid and full-width
        # from neck_pocket_start onward; the pocket recess itself (and
        # its own neck_pocket_end) is a separate, shallower cavity cut
        # into that solid material, not a notch in this silhouette.
        radii = [
            self.horn_tip_radius,
            self.shoulder_radius,
            self.waist_radius,
            self.lower_bout_radius,
            self.tail_radius,
            self.tail_radius,
            self.tail_radius,
            self.lower_bout_radius,
            self.waist_radius,
            self.shoulder_radius,
            self.horn_tip_radius,
            self.neck_pocket_corner_radius,
            self.neck_pocket_corner_radius,
        ]
        return vertices, radii

    def _validate(self) -> None:
        """Reject dimensions that cannot form a simple body outline."""
        scalar_fields = (
            self.scale_length,
            self.neck_pocket_half_width,
            self.neck_pocket_wall_clearance,
            self.treble_horn_tip_half_width,
            self.treble_shoulder_half_width,
            self.treble_waist_half_width,
            self.treble_lower_bout_half_width,
            self.bass_horn_tip_half_width,
            self.bass_shoulder_half_width,
            self.bass_waist_half_width,
            self.bass_lower_bout_half_width,
            self.tail_extension,
            self.tail_point_extension,
            self.tail_half_width,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in scalar_fields):
            raise BodyGeometryError(
                "Body outline lengths and half-widths must be finite and "
                "positive."
            )
        radii = (
            self.horn_tip_radius,
            self.shoulder_radius,
            self.waist_radius,
            self.lower_bout_radius,
            self.tail_radius,
            self.neck_pocket_corner_radius,
        )
        if not all(math.isfinite(radius) and radius >= 0.0 for radius in radii):
            raise BodyGeometryError(
                "Body outline corner radii must be finite and non-negative."
            )
        pocket_half_width = self._pocket_half_width()
        if self.treble_horn_tip_half_width < pocket_half_width * 0.5:
            raise BodyGeometryError(
                "Treble horn tip must clear the neck pocket wall."
            )
        if self.bass_horn_tip_half_width < pocket_half_width * 0.5:
            raise BodyGeometryError(
                "Bass horn tip must clear the neck pocket wall."
            )
        treble_stations = (
            self.treble_horn_tip_position,
            self.neck_pocket_start,
        )
        if treble_stations[0] >= treble_stations[1]:
            raise BodyGeometryError(
                "Treble horn tip must sit before the neck pocket."
            )
        bass_stations = (
            self.bass_horn_tip_position,
            self.neck_pocket_start,
        )
        if bass_stations[0] >= bass_stations[1]:
            raise BodyGeometryError(
                "Bass horn tip must sit before the neck pocket."
            )
        for label, positions in (
            (
                "Treble",
                (
                    self.treble_horn_tip_position,
                    self.treble_shoulder_position,
                    self.treble_waist_position,
                    self.treble_lower_bout_position,
                    self.tail_position,
                ),
            ),
            (
                "Bass",
                (
                    self.bass_horn_tip_position,
                    self.bass_shoulder_position,
                    self.bass_waist_position,
                    self.bass_lower_bout_position,
                    self.tail_position,
                ),
            ),
        ):
            if list(positions) != sorted(positions):
                raise BodyGeometryError(
                    f"{label} outline stations must run from the horn tip "
                    "to the tail in increasing order."
                )
