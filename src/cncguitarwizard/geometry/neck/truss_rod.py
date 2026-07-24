"""Top- and side-view geometry for a centered truss-rod channel."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from ..exceptions import TrussRodGeometryError
from ..primitives import Line2D, Point2D
from .outline import NeckOutline


@dataclass(frozen=True, slots=True)
class TrussRodChannel:
    """Represent a rectangular double-action truss-rod channel.

    The channel is centered on the neck centerline. ``start_position`` is
    measured from the nut toward the heel.

    Args:
        neck_outline: Neck boundary used for fit and clearance checks.
        start_position: Channel start distance from the nut in millimetres.
        length: Channel length in millimetres.
        width: Channel width in millimetres.
        depth: Channel depth in millimetres.
        adjustment_side: End from which the rod is adjusted.
        minimum_side_clearance: Required wood on each side of the channel.

    Raises:
        TrussRodGeometryError: If the channel does not fit safely in the neck.
    """

    neck_outline: NeckOutline
    start_position: float
    length: float
    width: float
    depth: float
    adjustment_side: Literal["nut", "heel"] = "heel"
    minimum_side_clearance: float = 3.0
    end_position: float = field(init=False)
    centerline: Line2D = field(init=False)
    top_boundary: tuple[Point2D, ...] = field(init=False)
    side_boundary: tuple[Point2D, ...] = field(init=False)
    adjustment_point: Point2D = field(init=False)

    def __post_init__(self) -> None:
        """Validate the channel and construct its reference geometry."""
        self._validate_parameters()
        end_position = self.start_position + self.length
        self._validate_fit(end_position)

        half_width = self.width / 2.0
        top_boundary = (
            Point2D(self.start_position, half_width),
            Point2D(self.start_position, -half_width),
            Point2D(end_position, -half_width),
            Point2D(end_position, half_width),
        )
        side_boundary = (
            Point2D(self.start_position, 0.0),
            Point2D(self.start_position, -self.depth),
            Point2D(end_position, -self.depth),
            Point2D(end_position, 0.0),
        )
        adjustment_x = (
            self.start_position if self.adjustment_side == "nut" else end_position
        )

        object.__setattr__(self, "end_position", end_position)
        object.__setattr__(
            self,
            "centerline",
            Line2D(
                Point2D(self.start_position, 0.0),
                Point2D(end_position, 0.0),
            ),
        )
        object.__setattr__(self, "top_boundary", top_boundary)
        object.__setattr__(self, "side_boundary", side_boundary)
        object.__setattr__(
            self,
            "adjustment_point",
            Point2D(adjustment_x, 0.0),
        )

    def _validate_parameters(self) -> None:
        """Reject invalid channel dimensions and configuration."""
        dimensions = (
            self.start_position,
            self.length,
            self.width,
            self.depth,
            self.minimum_side_clearance,
        )
        if not all(math.isfinite(value) for value in dimensions):
            raise TrussRodGeometryError("Truss-rod dimensions must be finite.")
        if self.start_position < 0.0:
            raise TrussRodGeometryError(
                "Truss-rod start position must not precede the nut."
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
        """Ensure channel length and width remain inside the neck."""
        heel_end = (
            self.neck_outline.last_fret_position + self.neck_outline.heel_length
        )
        if end_position > heel_end:
            raise TrussRodGeometryError(
                "Truss-rod channel extends beyond the heel."
            )

        width_at_start = self._neck_width_at(self.start_position)
        width_at_end = self._neck_width_at(end_position)
        required_width = self.width + 2.0 * self.minimum_side_clearance
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
            + (
                self.neck_outline.last_fret_width
                - self.neck_outline.nut_width
            )
            * fraction
        )
