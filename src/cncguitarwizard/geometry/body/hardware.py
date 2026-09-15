"""Routed cavities and hardware mounting points for the solid body."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, point_in_polygon, rounded_polygon_points


@dataclass(frozen=True, slots=True)
class TracedCavity:
    """A pocket whose outline was digitised from a reference drawing.

    Shares its read interface (``name``, ``depth``, ``outline``,
    ``min_x``/``max_x``/``min_y``/``max_y``) with ``RectangularCavity``
    and ``CircularCavity`` so all three can be cut and bounds-checked
    identically. Unlike those two, the outline is not generated from a
    size and a corner radius — its points are supplied directly,
    already converted into the neck's own nut-origin coordinate frame.

    Args:
        name: Short label used in error messages and generated comments.
        outline: Ordered vertices of one closed polygon loop.
        depth: Pocket depth in millimetres, cut down from the top face.

    Raises:
        BodyGeometryError: If fewer than three points are given, any
            coordinate is non-finite, or the depth is non-finite or
            non-positive.
    """

    name: str
    outline: tuple[Point2D, ...]
    depth: float

    def __post_init__(self) -> None:
        """Reject a traced cavity too small or malformed to be cut."""
        if len(self.outline) < 3:
            raise BodyGeometryError(f"{self.name} needs at least three points.")
        if not all(
            math.isfinite(point.x) and math.isfinite(point.y)
            for point in self.outline
        ):
            raise BodyGeometryError(f"{self.name} points must all be finite.")
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise BodyGeometryError(
                f"{self.name} depth must be finite and positive."
            )

    @property
    def min_x(self) -> float:
        """Return the pocket's smallest longitudinal extent."""
        return min(point.x for point in self.outline)

    @property
    def max_x(self) -> float:
        """Return the pocket's largest longitudinal extent."""
        return max(point.x for point in self.outline)

    @property
    def min_y(self) -> float:
        """Return the pocket's smallest lateral extent."""
        return min(point.y for point in self.outline)

    @property
    def max_y(self) -> float:
        """Return the pocket's largest lateral extent."""
        return max(point.y for point in self.outline)


@dataclass(frozen=True, slots=True)
class RectangularCavity:
    """A rounded-corner rectangular pocket routed into the body.

    Reused for the neck pocket, both pickup routes, and the control
    cavity — every one of those is, geometrically, just a rectangle of
    some size and depth centred at some point on the body.

    Args:
        name: Short label used in error messages and generated comments.
        center_x: Longitudinal centre in millimetres, in the neck's own
            nut-origin coordinate frame.
        center_y: Lateral centre in millimetres from the centerline.
        length_x: Full longitudinal size of the pocket.
        length_y: Full lateral size of the pocket.
        depth: Pocket depth in millimetres, cut down from the top face.
        corner_radius: Fillet radius applied to all four corners.

    Raises:
        BodyGeometryError: If any size is non-finite or non-positive, or
            the corner radius cannot fit inside the pocket.
    """

    name: str
    center_x: float
    center_y: float
    length_x: float
    length_y: float
    depth: float
    corner_radius: float = 3.0
    outline: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and build the rounded pocket outline."""
        self._validate()
        half_x = self.length_x / 2.0
        half_y = self.length_y / 2.0
        vertices = [
            Point2D(self.center_x - half_x, self.center_y - half_y),
            Point2D(self.center_x + half_x, self.center_y - half_y),
            Point2D(self.center_x + half_x, self.center_y + half_y),
            Point2D(self.center_x - half_x, self.center_y + half_y),
        ]
        radii = [self.corner_radius] * 4
        object.__setattr__(
            self,
            "outline",
            rounded_polygon_points(vertices, radii, samples_per_corner=8),
        )

    @property
    def min_x(self) -> float:
        """Return the pocket's smallest longitudinal extent."""
        return self.center_x - self.length_x / 2.0

    @property
    def max_x(self) -> float:
        """Return the pocket's largest longitudinal extent."""
        return self.center_x + self.length_x / 2.0

    @property
    def min_y(self) -> float:
        """Return the pocket's smallest lateral extent."""
        return self.center_y - self.length_y / 2.0

    @property
    def max_y(self) -> float:
        """Return the pocket's largest lateral extent."""
        return self.center_y + self.length_y / 2.0

    def _validate(self) -> None:
        """Reject a pocket that cannot be safely routed."""
        dimensions = (self.length_x, self.length_y, self.depth)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise BodyGeometryError(
                f"{self.name} size and depth must be finite and positive."
            )
        if not math.isfinite(self.center_x) or not math.isfinite(self.center_y):
            raise BodyGeometryError(
                f"{self.name} centre must be finite."
            )
        if not math.isfinite(self.corner_radius) or self.corner_radius < 0.0:
            raise BodyGeometryError(
                f"{self.name} corner radius must be finite and non-negative."
            )
        if self.corner_radius > min(self.length_x, self.length_y) / 2.0:
            raise BodyGeometryError(
                f"{self.name} corner radius must not exceed half its "
                "shortest side."
            )


@dataclass(frozen=True, slots=True)
class CircularCavity:
    """A round pocket routed into the body.

    Shares its read interface (``name``, ``depth``, ``outline``,
    ``min_x``/``max_x``/``min_y``/``max_y``) with ``RectangularCavity``
    so both can be cut and bounds-checked identically.

    Args:
        name: Short label used in error messages and generated comments.
        center_x: Longitudinal centre in millimetres.
        center_y: Lateral centre in millimetres from the centerline.
        diameter: Full diameter of the pocket in millimetres.
        depth: Pocket depth in millimetres, cut down from the top face.
        samples: Number of points used to approximate the circle.

    Raises:
        BodyGeometryError: If the diameter or depth is non-finite or
            non-positive.
    """

    name: str
    center_x: float
    center_y: float
    diameter: float
    depth: float
    samples: int = 32
    outline: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and build the sampled circle outline."""
        self._validate()
        radius = self.diameter / 2.0
        object.__setattr__(
            self,
            "outline",
            tuple(
                Point2D(
                    self.center_x + radius * math.cos(2.0 * math.pi * i / self.samples),
                    self.center_y + radius * math.sin(2.0 * math.pi * i / self.samples),
                )
                for i in range(self.samples)
            ),
        )

    @property
    def min_x(self) -> float:
        """Return the pocket's smallest longitudinal extent."""
        return self.center_x - self.diameter / 2.0

    @property
    def max_x(self) -> float:
        """Return the pocket's largest longitudinal extent."""
        return self.center_x + self.diameter / 2.0

    @property
    def min_y(self) -> float:
        """Return the pocket's smallest lateral extent."""
        return self.center_y - self.diameter / 2.0

    @property
    def max_y(self) -> float:
        """Return the pocket's largest lateral extent."""
        return self.center_y + self.diameter / 2.0

    def _validate(self) -> None:
        """Reject a pocket that cannot be safely routed."""
        if not math.isfinite(self.diameter) or self.diameter <= 0.0:
            raise BodyGeometryError(
                f"{self.name} diameter must be finite and positive."
            )
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise BodyGeometryError(f"{self.name} depth must be finite and positive.")
        if not math.isfinite(self.center_x) or not math.isfinite(self.center_y):
            raise BodyGeometryError(f"{self.name} centre must be finite.")


Cavity = RectangularCavity | CircularCavity | TracedCavity
"""Any pocket type that can be cut and bounds-checked on the body."""


@dataclass(frozen=True, slots=True)
class RearCavity:
    """A pocket routed in from the body's back face, with a cover recess.

    Control and switch cavities on a solid body are cut from the back,
    then closed with a plate that sits flush in a shallow, slightly
    larger recess around the cavity mouth. Both the deep cavity and the
    shallow recess are ordinary cavities in plan; only their cutting
    direction (up from the back face, not down from the top) differs,
    and that is the exporter's concern.

    Args:
        cavity: The deep route itself. Its ``depth`` is measured up from
            the back face.
        cover_recess: The shallow ledge the cover plate sits in. Its
            ``depth`` is the cover-plate thickness, also measured from
            the back face. Its outline must enclose the cavity outline.

    Raises:
        BodyGeometryError: If the cover recess is at least as deep as
            the cavity, or does not enclose the cavity outline.
    """

    cavity: Cavity
    cover_recess: Cavity

    def __post_init__(self) -> None:
        """Reject a recess that would not actually seat a cover plate."""
        if self.cover_recess.depth >= self.cavity.depth:
            raise BodyGeometryError(
                f"{self.cavity.name} cover recess must be shallower than "
                "the cavity itself."
            )
        if not all(
            point_in_polygon(point, self.cover_recess.outline)
            for point in self.cavity.outline
        ):
            raise BodyGeometryError(
                f"{self.cavity.name} cover recess must enclose the cavity."
            )

    @property
    def name(self) -> str:
        """Return the deep cavity's own label."""
        return self.cavity.name

    @property
    def depth(self) -> float:
        """Return the deep cavity's depth measured from the back face."""
        return self.cavity.depth


@dataclass(frozen=True, slots=True)
class BridgeMounting:
    """An approximate Kahler 7300-style top-mount tremolo cavity.

    No manufacturer template was available when this was built, so every
    dimension here is a labelled, clearly-adjustable placeholder rather
    than a verified fit. Re-measure the real hardware (sustain-block
    footprint and depth, mounting-screw positions) before cutting a
    real body from this model.

    Args:
        reference_x: Longitudinal position of the bridge's nominal
            intonation/pivot line — conventionally the scale length.
        pivot_stud_spacing: Lateral distance between the two pivot studs
            a stud-mounted bridge rocks on, or ``None`` for a bridge
            that is screwed flat to the body (a Kahler 7300) and needs
            no stud holes at all.
        pivot_hole_diameter: Diameter of each pivot stud's mounting hole.
        pivot_hole_depth: Depth of each pivot stud's mounting hole.
        sustain_block_length: Longitudinal size of the rear cavity that
            houses the sustain block and return springs.
        sustain_block_width: Lateral size of that rear cavity.
        sustain_block_depth: Depth of that rear cavity.
        sustain_block_offset: Distance the rear cavity's centre sits
            behind (heelward of) ``reference_x``. Ignored when
            ``sustain_block_cavity_override`` is given.
        sustain_block_cavity_override: A pocket to use in place of the
            auto-generated rounded rectangle — for example, a
            ``TracedCavity`` digitised from a real reference drawing.
            When given, ``sustain_block_length``/``_width``/``_depth``/
            ``_offset`` are not used to build the cavity.
        has_sustain_block: ``False`` for a fixed, flat-mount bridge (a
            Kahler 7300) that has no block or springs behind it — no
            rear cavity is built at all and ``sustain_block_cavity`` is
            ``None``.

    Raises:
        BodyGeometryError: If any dimension is non-finite or
            non-positive.
    """

    reference_x: float
    pivot_stud_spacing: float | None = 74.0
    pivot_hole_diameter: float = 8.0
    pivot_hole_depth: float = 12.0
    sustain_block_length: float = 45.0
    sustain_block_width: float = 70.0
    sustain_block_depth: float = 32.0
    sustain_block_offset: float = 30.0
    sustain_block_cavity_override: RectangularCavity | TracedCavity | None = None
    has_sustain_block: bool = True
    sustain_block_cavity: RectangularCavity | TracedCavity | None = field(
        init=False
    )

    def __post_init__(self) -> None:
        """Validate dimensions and build the sustain-block cavity, if any."""
        self._validate()
        if not self.has_sustain_block:
            object.__setattr__(self, "sustain_block_cavity", None)
            return
        object.__setattr__(
            self,
            "sustain_block_cavity",
            self.sustain_block_cavity_override
            or RectangularCavity(
                "Kahler sustain-block cavity",
                self.reference_x + self.sustain_block_offset,
                0.0,
                self.sustain_block_length,
                self.sustain_block_width,
                self.sustain_block_depth,
                corner_radius=6.0,
            ),
        )

    @property
    def pivot_holes(self) -> tuple[Point2D, ...]:
        """Return the pivot-stud hole centres — none for a flat-mount bridge."""
        if self.pivot_stud_spacing is None:
            return ()
        half_spacing = self.pivot_stud_spacing / 2.0
        return (
            Point2D(self.reference_x, -half_spacing),
            Point2D(self.reference_x, half_spacing),
        )

    def _validate(self) -> None:
        """Reject bridge dimensions that cannot form a safe cavity."""
        if self.pivot_stud_spacing is not None and not (
            math.isfinite(self.pivot_stud_spacing) and self.pivot_stud_spacing > 0.0
        ):
            raise BodyGeometryError(
                "Bridge pivot stud spacing must be finite and positive, or None."
            )
        dimensions = (
            self.pivot_hole_diameter,
            self.pivot_hole_depth,
            self.sustain_block_length,
            self.sustain_block_width,
            self.sustain_block_depth,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise BodyGeometryError(
                "Bridge mounting dimensions must be finite and positive."
            )
        if not math.isfinite(self.reference_x):
            raise BodyGeometryError(
                "Bridge reference position must be finite."
            )
        if not math.isfinite(self.sustain_block_offset):
            raise BodyGeometryError(
                "Bridge sustain-block offset must be finite."
            )


@dataclass(frozen=True, slots=True)
class DrilledHole:
    """A vertical round hole drilled down from the body's top face.

    Used for pot and switch shaft holes (drilled clean through the top
    wall into a rear cavity) and for the small clearance recesses under
    pickup height-adjustment screws (drilled on down from a route
    floor). The hole always starts at the top face, Z = 0; where it
    passes through a cavity it simply removes nothing extra.

    Args:
        name: Short label used in error messages and generated comments.
        center_x: Longitudinal centre in millimetres.
        center_y: Lateral centre in millimetres from the centerline.
        diameter: Hole diameter in millimetres.
        depth: Hole depth in millimetres from the top face. Equal to the
            body thickness for a through hole.

    Raises:
        BodyGeometryError: If the diameter or depth is non-finite or
            non-positive, or the centre is non-finite.
    """

    name: str
    center_x: float
    center_y: float
    diameter: float
    depth: float

    def __post_init__(self) -> None:
        """Reject a hole that cannot be safely drilled."""
        dimensions = (self.diameter, self.depth)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise BodyGeometryError(
                f"{self.name} diameter and depth must be finite and positive."
            )
        if not math.isfinite(self.center_x) or not math.isfinite(self.center_y):
            raise BodyGeometryError(f"{self.name} centre must be finite.")

    @property
    def center(self) -> Point2D:
        """Return the hole centre as a point."""
        return Point2D(self.center_x, self.center_y)


@dataclass(frozen=True, slots=True)
class JackHole:
    """A straight cylindrical bore for an edge-mounted output jack.

    The bore starts at a point on (or very near) the body outline and
    runs inward, connecting to the control cavity. Positioning it
    exactly on the outline is the caller's responsibility — this
    dataclass only validates the bore itself.

    Args:
        start_x: Longitudinal position where the bore meets the edge.
        start_y: Lateral position where the bore meets the edge.
        direction_degrees: Bore axis direction in the XY plane, degrees
            measured counter-clockwise from the positive X axis.
        diameter: Bore diameter in millimetres.
        depth: Bore length in millimetres, from the edge inward.

    Raises:
        BodyGeometryError: If the diameter or depth is non-finite or
            non-positive.
    """

    start_x: float
    start_y: float
    direction_degrees: float
    diameter: float = 12.5
    depth: float = 30.0

    def __post_init__(self) -> None:
        """Reject a bore that cannot be safely drilled."""
        dimensions = (self.diameter, self.depth)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise BodyGeometryError(
                "Jack bore diameter and depth must be finite and positive."
            )
        if not math.isfinite(self.start_x) or not math.isfinite(self.start_y):
            raise BodyGeometryError("Jack bore start position must be finite.")
        if not math.isfinite(self.direction_degrees):
            raise BodyGeometryError("Jack bore direction must be finite.")
