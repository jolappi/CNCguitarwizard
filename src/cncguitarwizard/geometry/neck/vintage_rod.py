"""A vintage Fender truss rod, laid in from the neck's back.

Fender's first necks had their rod put in from behind: a channel routed
along the back of the neck, its floor (toward the fretboard) curved, so
the rod lies deeper in the middle than at its ends and, tightened, pulls
straight against the wood toward the fretboard; a walnut strip glued in
over it (the "skunk stripe"), carved with the back; and at the headstock
end, where the rod is anchored, a walnut teardrop plug. It is adjusted at
the heel, its nut at the heel's end face. From 1971 the rod was turned
round, the "bullet" rod: anchored at the heel's end, adjusted at the
headstock, its bullet-shaped nut behind the nut in a trough in the
headstock's face, no plug, the strip the channel's whole length.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ..exceptions import TrussRodGeometryError
from ..primitives import Point2D

TEARDROP_SAMPLES = 32
"""Points round a teardrop plug's round end."""


@dataclass(frozen=True, slots=True)
class VintageTrussRod:
    """A truss rod laid into a channel routed from the neck's back.

    Depths are below the neck's top (the fretboard's glue face), as the
    top-routed channel's are; the channel is open toward the back.

    Args:
        start: Where the rod's anchor end lies, from the nut toward the
            heel (negative: in the headstock).
        end: Where its adjusting end lies: the heel end.
        width: The channel's width, and the walnut strip's.
        rod_diameter: The rod's diameter.
        end_depth: The rod's axis below the top at both ends.
        bow: How much deeper the axis lies in the middle (a parabola
            between the ends).
        plug_width: The teardrop plug's width: its round end, at ``start``.
        plug_length: Its length, from its round end to where it has
            narrowed to the channel.
        adjusted_at: ``"heel"``, the vintage rod: anchored at ``start``
            under the plug, its nut at the heel's end face; or
            ``"headstock"``, a 1970s bullet rod: anchored at the heel's
            end, its bullet nut ahead of ``start`` in the headstock's face
            (the channel's trough, ``TrussRodChannel.adjuster_boundary``),
            and no plug: the strip runs from ``start``.

    Raises:
        TrussRodGeometryError: For sizes that are not finite and positive
            (the bow may be nil), an end not past the start, a rod not
            narrower than its channel, a plug not wider than the channel,
            not longer than it is wide or not shorter than the rod, or a rod
            breaking out of the top.
    """

    start: float
    end: float
    width: float
    rod_diameter: float
    end_depth: float
    bow: float
    plug_width: float
    plug_length: float
    adjusted_at: Literal["heel", "headstock"] = "heel"

    def __post_init__(self) -> None:
        """Reject a rod that cannot be laid in."""
        sizes = (
            self.width,
            self.rod_diameter,
            self.end_depth,
            self.plug_width,
            self.plug_length,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in sizes):
            raise TrussRodGeometryError(
                "A vintage truss rod's sizes must be finite and positive."
            )
        if not (math.isfinite(self.bow) and self.bow >= 0.0):
            raise TrussRodGeometryError(
                "A vintage truss rod's bow must not be negative."
            )
        if not self.end > self.start:
            raise TrussRodGeometryError("A vintage truss rod must end past its start.")
        if self.rod_diameter >= self.width:
            raise TrussRodGeometryError(
                "A vintage truss rod must be narrower than its channel."
            )
        if self.adjusted_at not in ("heel", "headstock"):
            raise TrussRodGeometryError(
                'A vintage truss rod is adjusted at the "heel" or the "headstock".'
            )
        if self.has_plug and not self.width < self.plug_width < self.plug_length:
            raise TrussRodGeometryError(
                "A vintage truss rod's plug must be wider than its channel and "
                "longer than it is wide."
            )
        if self.strip_start >= self.end:
            raise TrussRodGeometryError(
                "A vintage truss rod's plug must be shorter than the rod."
            )
        if self.end_depth <= self.rod_diameter / 2.0:
            raise TrussRodGeometryError(
                "A vintage truss rod must lie below the neck's top."
            )

    def axis_depth(self, x: float) -> float:
        """Return the rod's axis below the top at ``x`` (its ends' depth
        beyond them)."""
        u = min(1.0, max(0.0, (x - self.start) / (self.end - self.start)))
        return self.end_depth + self.bow * 4.0 * u * (1.0 - u)

    def ceiling_depth(self, x: float) -> float:
        """Return how far below the top the channel reaches at ``x``: the
        rod's side nearest the fretboard."""
        return self.axis_depth(x) - self.rod_diameter / 2.0

    def strip_depth(self, x: float) -> float:
        """Return where the walnut over the rod starts at ``x``, below the
        top: the rod's side nearest the back."""
        return self.axis_depth(x) + self.rod_diameter / 2.0

    @property
    def has_plug(self) -> bool:
        """Return whether a teardrop plug covers its anchor at the
        headstock: a rod adjusted at the heel's."""
        return self.adjusted_at == "heel"

    @property
    def strip_start(self) -> float:
        """Return where the walnut strip starts: the plug's narrow end, or
        the channel's start without a plug."""
        return self.start + (self.plug_length if self.has_plug else 0.0)

    @property
    def strip_outline(self) -> tuple[Point2D, ...]:
        """Return the walnut strip in plan, from the plug to the end."""
        half = self.width / 2.0
        return (
            Point2D(self.strip_start, -half),
            Point2D(self.end, -half),
            Point2D(self.end, half),
            Point2D(self.strip_start, half),
        )

    @property
    def plug_depth(self) -> float:
        """Return the teardrop plug's floor below the top: the rod's side
        nearest the back where it lies deepest under the plug (its narrow
        end, or the middle of a rod hardly longer than the plug)."""
        return self.strip_depth(min(self.strip_start, (self.start + self.end) / 2.0))

    @property
    def plug_outline(self) -> tuple[Point2D, ...]:
        """Return the teardrop plug in plan, counter-clockwise.

        Its round end at ``start``, ``plug_width`` across, narrowing to
        the channel's width ``plug_length`` along: the convex hull of the
        round end and the channel's width there. Empty without a plug.
        """
        if not self.has_plug:
            return ()
        radius = self.plug_width / 2.0
        centre = self.start + radius
        points = [
            Point2D(
                centre + radius * math.cos(2.0 * math.pi * k / TEARDROP_SAMPLES),
                radius * math.sin(2.0 * math.pi * k / TEARDROP_SAMPLES),
            )
            for k in range(TEARDROP_SAMPLES)
        ]
        half = self.width / 2.0
        points += [Point2D(self.strip_start, -half), Point2D(self.strip_start, half)]
        return _convex_hull(points)


def _convex_hull(points: list[Point2D]) -> tuple[Point2D, ...]:
    """Return the points' convex hull, counter-clockwise (monotone chain)."""
    ordered = sorted(set(points), key=lambda p: (p.x, p.y))

    def cross(o: Point2D, a: Point2D, b: Point2D) -> float:
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    lower: list[Point2D] = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper: list[Point2D] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    return tuple(lower[:-1] + upper[:-1])
