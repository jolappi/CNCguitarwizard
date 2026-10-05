"""Top- and side-view geometry for a centered truss-rod channel."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from ..exceptions import TrussRodGeometryError
from ..primitives import Line2D, Point2D
from .outline import NeckOutline


@dataclass(frozen=True, slots=True)
class TrussRodPocket:
    """One routed step of the channel: a plan rectangle and its depth.

    Args:
        name: E.g. ``"Truss-rod step"``.
        boundary: Plan rectangle in the model frame.
        depth: Depth below the neck's top (the fretboard's glue face).
    """

    name: str
    boundary: tuple[Point2D, ...]
    depth: float


@dataclass(frozen=True, slots=True)
class TrussRodBore:
    """A horizontal bore along the rod's axis for the adjuster's sleeve.

    A router cannot drill it along the neck, but it can cut it from the
    neck's top as a slot the bore's width down to the bore's floor, which
    the fretboard closes over (``routed``); otherwise it is drilled by
    hand.

    Args:
        start: Bore start along the neck.
        end: Bore end along the neck.
        axis_depth: Depth of the rod's axis below the neck's top.
        diameter: Bore diameter.
        routed: Whether it is routed from the top as a slot.
    """

    start: float
    end: float
    axis_depth: float
    diameter: float
    routed: bool = False

    @property
    def floor_depth(self) -> float:
        """The bore's lowest point below the neck's top: a slot's floor."""
        return self.axis_depth + self.diameter / 2.0


@dataclass(frozen=True, slots=True)
class TrussRodChannel:
    """Represent a double-action truss-rod route and its adjusting end.

    The route is centered on the neck centerline and runs from
    ``start_position`` (measured from the nut toward the heel) for
    ``length``. Toward the adjusting end the plain channel (``width`` ×
    ``depth``) steps down twice for the rod's anchor block and adjuster
    sleeve: a ``step_*`` pocket, then a wider, deeper ``pocket_*``. The
    rod's axis lies ``rod_axis_depth`` below the neck's top (left at 0:
    half the pocket's width above its floor).

    * ``"heel"`` — the route ends ``sleeve_length`` before the heel end;
      the adjuster's sleeve runs on through a bore of ``sleeve_diameter``
      (``bore``: drilled by hand, or with ``sleeve_routed`` cut from the
      top as a slot down to the bore's floor, under the fretboard) and its round
      head, ``nut_diameter`` × ``nut_length``, sits past the heel end on
      the body side, in the body's ``access_boundary`` notch
      (``access_length`` long, 1 mm clear of the head all round).
    * ``"nut"`` — the route starts at least ``shelf_length`` behind the
      nut, with the pockets there; the adjuster sits in a trough
      (``adjuster_boundary``) ``access_length`` long in the headstock face
      behind the route's start, under a truss-rod cover; with
      ``access_diameter`` the trough is only that wide, a notch for the
      adjusting key rather than room for the head.

    With all the step, pocket, sleeve and nut sizes at 0 the route is a
    plain rectangular channel.

    Args:
        neck_outline: Neck boundary used for fit and clearance checks.
        start_position: Route start distance from the nut in millimetres.
        length: Route length (channel, step and pocket) in millimetres.
        width: Plain channel width in millimetres.
        depth: Plain channel depth in millimetres.
        adjustment_side: End from which the rod is adjusted.
        minimum_side_clearance: Required wood on each side of the channel.
        step_length: Length of the first, narrower step at the adjusting end.
        step_width: Its width.
        step_depth: Its depth.
        pocket_length: Length of the wider pocket at the very end.
        pocket_width: Its width.
        pocket_depth: Its depth.
        sleeve_length: At the heel, the adjuster sleeve's bore length.
        sleeve_diameter: The bore's diameter.
        sleeve_routed: Cut the bore from the top as a slot (see
            ``TrussRodBore``) rather than leave it to be drilled by hand.
        nut_diameter: The adjuster's round head (spoke wheel) diameter.
        nut_length: The head's length along the rod.
        access_length: At the heel, how far the body's notch runs past the
            heel end; at the nut, the headstock trough's length (``0`` for
            no trough).
        access_diameter: At the nut, a key notch's width instead of room
            for the head (``0``: room for the head).
        shelf_length: The nut shelf in front of the headstock face.
        rod_axis_depth: The rod's (and adjuster's) axis below the neck's
            top; 0 puts it half the pocket's width above the pocket floor.

    Raises:
        TrussRodGeometryError: If the route does not fit safely in the neck.
    """

    neck_outline: NeckOutline
    start_position: float
    length: float
    width: float
    depth: float
    adjustment_side: Literal["nut", "heel"] = "heel"
    minimum_side_clearance: float = 3.0
    step_length: float = 0.0
    step_width: float = 0.0
    step_depth: float = 0.0
    pocket_length: float = 0.0
    pocket_width: float = 0.0
    pocket_depth: float = 0.0
    sleeve_length: float = 0.0
    sleeve_diameter: float = 0.0
    sleeve_routed: bool = False
    nut_diameter: float = 0.0
    nut_length: float = 0.0
    access_length: float = 0.0
    access_diameter: float = 0.0
    shelf_length: float = 0.0
    rod_axis_depth: float = 0.0
    end_position: float = field(init=False)
    centerline: Line2D = field(init=False)
    top_boundary: tuple[Point2D, ...] = field(init=False)
    side_boundary: tuple[Point2D, ...] = field(init=False)
    adjustment_point: Point2D = field(init=False)
    pockets: tuple[TrussRodPocket, ...] = field(init=False)
    axis_depth: float = field(init=False)
    bore: TrussRodBore | None = field(init=False)
    adjuster_boundary: tuple[Point2D, ...] = field(init=False)
    adjuster_depth: float = field(init=False)
    access_boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate the route and construct its reference geometry."""
        self._validate_parameters()
        end_position = self.start_position + self.length
        self._validate_fit(end_position)
        heel_end = self.neck_outline.last_fret_position + self.neck_outline.heel_length
        heel = self.adjustment_side == "heel"

        # Plain channel, then the step and pocket at the adjusting end.
        steps = self.step_length + self.pocket_length
        if steps > self.length - 1e-9 and steps > 0.0:
            raise TrussRodGeometryError(
                "The truss rod's step and pocket are longer than its route."
            )
        if heel:
            channel = (self.start_position, end_position - steps)
            step = (channel[1], channel[1] + self.step_length)
            pocket = (step[1], end_position)
        else:
            pocket = (self.start_position, self.start_position + self.pocket_length)
            step = (pocket[1], pocket[1] + self.step_length)
            channel = (step[1], end_position)
        pockets: list[TrussRodPocket] = []
        if self.step_length > 0.0:
            pockets.append(
                TrussRodPocket(
                    "Truss-rod step",
                    _rectangle(*step, self.step_width / 2.0),
                    self.step_depth,
                )
            )
        if self.pocket_length > 0.0:
            pockets.append(
                TrussRodPocket(
                    "Truss-rod pocket",
                    _rectangle(*pocket, self.pocket_width / 2.0),
                    self.pocket_depth,
                )
            )
        if self.rod_axis_depth > 0.0:
            axis_depth = self.rod_axis_depth
        elif self.pocket_length > 0.0:
            axis_depth = self.pocket_depth - self.pocket_width / 2.0
        else:
            axis_depth = self.depth - self.width / 2.0
        if self.sleeve_diameter > 0.0 and self.sleeve_length > 0.0:
            if axis_depth - self.sleeve_diameter / 2.0 < 0.0:
                raise TrussRodGeometryError(
                    "The adjuster's sleeve bore would break out of the neck's top."
                )

        half_width = self.width / 2.0
        top_boundary = (
            Point2D(channel[0], half_width),
            Point2D(channel[0], -half_width),
            Point2D(channel[1], -half_width),
            Point2D(channel[1], half_width),
        )
        side_boundary = (
            Point2D(channel[0], 0.0),
            Point2D(channel[0], -self.depth),
            Point2D(channel[1], -self.depth),
            Point2D(channel[1], 0.0),
        )
        adjustment_x = self.start_position if not heel else end_position

        bore = None
        adjuster: tuple[Point2D, ...] = ()
        access: tuple[Point2D, ...] = ()
        adjuster_depth = 0.0
        if self.nut_diameter > 0.0:
            half = self.nut_diameter / 2.0 + 1.0
            # The head is centred on the rod's axis, 0.5 mm clear below it.
            adjuster_depth = axis_depth + self.nut_diameter / 2.0 + 0.5
            if heel:
                front = heel_end - self.sleeve_length
                if end_position < front - 1e-6:
                    raise TrussRodGeometryError(
                        f"The truss rod ends {front - end_position:.1f} mm short of "
                        "its adjuster at the heel; make it longer."
                    )
                if self.sleeve_length > 0.0 and self.sleeve_diameter > 0.0:
                    bore = TrussRodBore(
                        end_position,
                        heel_end,
                        axis_depth,
                        self.sleeve_diameter,
                        self.sleeve_routed,
                    )
                if self.access_length > 0.0:
                    access = _rectangle(heel_end, heel_end + self.access_length, half)
            elif self.access_length > 0.0:
                if self.access_diameter > 0.0:
                    # Only a notch for the key, down to the rod's axis
                    # and the key's half below it.
                    half = self.access_diameter / 2.0
                    adjuster_depth = axis_depth + half
                behind = self.start_position
                adjuster = _rectangle(behind - self.access_length, behind, half)

        object.__setattr__(self, "end_position", end_position)
        object.__setattr__(
            self,
            "centerline",
            Line2D(Point2D(self.start_position, 0.0), Point2D(end_position, 0.0)),
        )
        object.__setattr__(self, "top_boundary", top_boundary)
        object.__setattr__(self, "side_boundary", side_boundary)
        object.__setattr__(self, "adjustment_point", Point2D(adjustment_x, 0.0))
        object.__setattr__(self, "pockets", tuple(pockets))
        object.__setattr__(self, "axis_depth", axis_depth)
        object.__setattr__(self, "bore", bore)
        object.__setattr__(self, "adjuster_boundary", adjuster)
        object.__setattr__(self, "adjuster_depth", adjuster_depth)
        object.__setattr__(self, "access_boundary", access)

    @property
    def channel_start(self) -> float:
        """Return where the plain channel starts along the neck."""
        return min(point.x for point in self.top_boundary)

    @property
    def channel_length(self) -> float:
        """Return the plain channel's length (without the step and pocket)."""
        xs = [point.x for point in self.top_boundary]
        return max(xs) - min(xs)

    def keep_clear(self) -> tuple[tuple[float, float, float], ...]:
        """Return ``(front, back, half width)`` of every part of the route.

        Other features (the neck bolts) keep their wood to these.
        """
        parts = [self.top_boundary, *(p.boundary for p in self.pockets)]
        if self.adjuster_boundary:
            parts.append(self.adjuster_boundary)
        spans = [
            (
                min(p.x for p in part),
                max(p.x for p in part),
                max(p.y for p in part),
            )
            for part in parts
        ]
        if self.bore is not None:
            spans.append((self.bore.start, self.bore.end, self.bore.diameter / 2.0))
        return tuple(spans)

    def _validate_parameters(self) -> None:
        """Reject invalid route dimensions and configuration."""
        dimensions = (
            self.start_position,
            self.length,
            self.width,
            self.depth,
            self.minimum_side_clearance,
        )
        if not all(math.isfinite(value) for value in dimensions):
            raise TrussRodGeometryError("Truss-rod dimensions must be finite.")
        if self.adjustment_side == "heel" and (
            self.start_position < -self.shelf_length - 1e-9
        ):
            raise TrussRodGeometryError(
                "Truss-rod start position must not precede the nut shelf."
            )
        extras = (
            self.step_length,
            self.step_width,
            self.step_depth,
            self.pocket_length,
            self.pocket_width,
            self.pocket_depth,
            self.sleeve_length,
            self.sleeve_diameter,
            self.nut_diameter,
            self.nut_length,
            self.access_length,
            self.access_diameter,
            self.rod_axis_depth,
        )
        if not all(math.isfinite(v) and v >= 0.0 for v in extras):
            raise TrussRodGeometryError(
                "Truss-rod step, pocket, sleeve and nut sizes must be zero or more."
            )
        for name in ("step", "pocket"):
            if getattr(self, f"{name}_length") > 0.0 and (
                getattr(self, f"{name}_width") <= 0.0
                or getattr(self, f"{name}_depth") <= 0.0
            ):
                raise TrussRodGeometryError(
                    f"The truss rod's {name} needs a width and a depth."
                )
        if (
            self.adjustment_side == "nut"
            and self.nut_diameter > 0.0
            and 0.0 < self.access_length < self.nut_length
        ):
            raise TrussRodGeometryError(
                "A headstock-adjusted rod's trough must be at least as long as "
                "its adjuster's head."
            )
        if self.length <= 0.0 or self.width <= 0.0 or self.depth <= 0.0:
            raise TrussRodGeometryError(
                "Truss-rod length, width, and depth must be positive."
            )
        if self.minimum_side_clearance < 0.0:
            raise TrussRodGeometryError(
                "Truss-rod side clearance must not be negative."
            )
        if self.adjustment_side not in ("nut", "heel"):
            raise TrussRodGeometryError(
                "Truss-rod adjustment side must be 'nut' or 'heel'."
            )

    def _validate_fit(self, end_position: float) -> None:
        """Ensure the route's length and width remain inside the neck."""
        heel_end = self.neck_outline.last_fret_position + self.neck_outline.heel_length
        if end_position > heel_end:
            raise TrussRodGeometryError("Truss-rod channel extends beyond the heel.")

        widest = max(self.width, self.step_width, self.pocket_width)
        width_at_start = self._neck_width_at(max(self.start_position, 0.0))
        width_at_end = self._neck_width_at(end_position)
        required_width = widest + 2.0 * self.minimum_side_clearance
        if min(width_at_start, width_at_end) < required_width:
            raise TrussRodGeometryError(
                "Truss-rod channel violates the requested side clearance."
            )

    def _neck_width_at(self, position: float) -> float:
        """Return the neck width at a centerline position."""
        if position >= self.neck_outline.last_fret_position:
            return self.neck_outline.heel_width

        fraction = position / self.neck_outline.last_fret_position
        return (
            self.neck_outline.nut_width
            + (self.neck_outline.last_fret_width - self.neck_outline.nut_width)
            * fraction
        )


def _rectangle(front: float, back: float, half: float) -> tuple[Point2D, ...]:
    """Return a plan rectangle from ``front`` to ``back``, ``half`` either side."""
    return (
        Point2D(front, -half),
        Point2D(back, -half),
        Point2D(back, half),
        Point2D(front, half),
    )
