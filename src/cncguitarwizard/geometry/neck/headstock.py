"""Top- and side-view reference geometry for a tapered headstock."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

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
