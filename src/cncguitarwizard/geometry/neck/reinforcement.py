"""Carbon fibre bars set into the neck's top beside the truss rod.

Two bars, one each side of the truss rod's route, stiffen the neck
against bending and twist. Each lies in a channel routed into the neck's
top (the fretboard's glue face) ``offset`` from the centerline, from
``start`` to ``end`` along the neck, as wide as the bar and
``CLEARANCE`` more for the epoxy, as deep as the bar is tall; the bars
are glued in flush before the fretboard goes on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import NeckGeometryError
from ..primitives import Point2D

CLEARANCE = 0.1
"""How much wider a channel is than its bar, for the epoxy, in mm."""


@dataclass(frozen=True, slots=True)
class CarbonRods:
    """Two carbon fibre bars in channels beside the truss rod.

    Args:
        start: Where the bars start along the neck, from the nut.
        end: Where they end, toward the heel.
        offset: Each bar's centre from the centerline.
        width: The bar's width across the neck.
        depth: The bar's height, its channel's depth below the glue face.

    Raises:
        NeckGeometryError: For a size that is not positive, an end before
            the start, or bars that would overlap on the centerline.
    """

    start: float
    end: float
    offset: float
    width: float
    depth: float

    def __post_init__(self) -> None:
        for name, value in (
            ("neck_carbon_rod_width", self.width),
            ("neck_carbon_rod_depth", self.depth),
            ("neck_carbon_rod_offset", self.offset),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise NeckGeometryError(f"{name} must be finite and positive.")
        if not math.isfinite(self.start) or not math.isfinite(self.end) or (
            self.end <= self.start
        ):
            raise NeckGeometryError("The carbon rods must end after they start.")
        if self.offset <= self.channel_width / 2.0:
            raise NeckGeometryError(
                "neck_carbon_rod_offset must keep the two carbon rods apart."
            )

    @property
    def length(self) -> float:
        """Return each bar's length, in mm."""
        return self.end - self.start

    @property
    def channel_width(self) -> float:
        """Return a channel's width: the bar's and the epoxy's clearance."""
        return self.width + CLEARANCE

    def channels(self) -> tuple[tuple[Point2D, ...], tuple[Point2D, ...]]:
        """Return both channels in plan, the +Y one first."""
        half = self.channel_width / 2.0

        def channel(centre: float) -> tuple[Point2D, ...]:
            return (
                Point2D(self.start, centre - half),
                Point2D(self.end, centre - half),
                Point2D(self.end, centre + half),
                Point2D(self.start, centre + half),
            )

        return channel(self.offset), channel(-self.offset)
