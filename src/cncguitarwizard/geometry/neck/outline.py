"""Top-view outline geometry for a guitar neck and heel.

A heel ends square across the neck, or round as Fender's Stratocaster
heel does: a long, shallow arc across its end blended into each side by
a small corner radius (``heel_end_curve``), its pocket and fretboard end
following it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..exceptions import NeckGeometryError
from ..fret import FretCalculator
from ..primitives import Line2D, Point2D
from .centerline import Centerline

HEEL_END_SAMPLES = 12
"""Points along each corner of a round heel end, and twice as many along
its end arc."""


def heel_end_curve(
    end_x: float, half_width: float, end_radius: float, corner_radius: float
) -> tuple[Point2D, ...]:
    """Return a heel's end in plan, from its -Y side round to its +Y side.

    Square (``end_radius`` 0): its two corners at ``end_x``. Round: an arc
    of ``end_radius`` across the end through (``end_x``, 0), blended into
    each side by a fillet of ``corner_radius``; the first and last points
    are where the fillets meet the sides, ``half_width`` off the centre.

    Raises:
        NeckGeometryError: For an end radius not more than the half-width,
            or a corner radius not positive and under the half-width.
    """
    if end_radius == 0.0:
        return (Point2D(end_x, -half_width), Point2D(end_x, half_width))
    if not (math.isfinite(end_radius) and end_radius > half_width):
        raise NeckGeometryError(
            "A round heel end's radius must be more than half the heel's width."
        )
    if not (math.isfinite(corner_radius) and 0.0 < corner_radius < half_width):
        raise NeckGeometryError(
            "A round heel end's corner radius must be positive and under half "
            "the heel's width."
        )
    centre_x = end_x - end_radius
    # Each fillet's centre: its radius in from the side, and that much
    # inside the end arc; the two meet on the line through both centres.
    fillet_x = centre_x + math.sqrt(
        (end_radius - corner_radius) ** 2 - (half_width - corner_radius) ** 2
    )
    fillet_y = half_width - corner_radius
    meet = math.atan2(fillet_y, fillet_x - centre_x)
    count = HEEL_END_SAMPLES
    corner = [
        -math.pi / 2.0 + (math.pi / 2.0 - meet) * k / count for k in range(count + 1)
    ]
    low = [
        Point2D(
            fillet_x + corner_radius * math.cos(a),
            -fillet_y + corner_radius * math.sin(a),
        )
        for a in corner
    ]
    arc = [
        Point2D(centre_x + end_radius * math.cos(a), end_radius * math.sin(a))
        for a in (-meet + meet * k / count for k in range(1, 2 * count))
    ]
    high = [Point2D(p.x, -p.y) for p in reversed(low)]
    return (*low, *arc, *high)


def clip_to_heel_end(
    polygon: Sequence[Point2D],
    end_x: float,
    half_width: float,
    end_radius: float,
    corner_radius: float,
) -> tuple[Point2D, ...]:
    """Return a plan polygon cut back to a round heel end.

    Whatever lies past the end (``heel_end_curve``) is cut away; the
    polygon must lie within ``half_width`` of the centre. It is the
    polygon itself for a square end.
    """
    if end_radius == 0.0:
        return tuple(polygon)
    end = heel_end_curve(end_x, half_width, end_radius, corner_radius)
    # Convex: back along each side from the end, counter-clockwise.
    far = min(p.x for p in polygon) - 1.0
    region = (Point2D(far, -half_width), *end, Point2D(far, half_width))
    points = list(polygon)
    for a, b in zip(region, (*region[1:], region[0]), strict=True):

        def inside(p: Point2D, a: Point2D = a, b: Point2D = b) -> bool:
            return (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x) >= -1e-9

        clipped: list[Point2D] = []
        for here, after in zip(points, (*points[1:], points[0]), strict=True):
            if inside(here):
                clipped.append(here)
            if inside(here) != inside(after):
                ex, ey = after.x - here.x, after.y - here.y
                denominator = (b.x - a.x) * ey - (b.y - a.y) * ex
                t = (
                    (b.y - a.y) * (here.x - a.x) - (b.x - a.x) * (here.y - a.y)
                ) / denominator
                clipped.append(Point2D(here.x + ex * t, here.y + ey * t))
        points = clipped
    return tuple(points)


def heel_end_inset(
    y: float, half_width: float, end_radius: float, corner_radius: float
) -> float:
    """Return how far short of its end, on the centre, a heel ends at ``y``.

    Nothing for a square end; past the sides, as at them.
    """
    if end_radius == 0.0:
        return 0.0
    end = heel_end_curve(0.0, half_width, end_radius, corner_radius)
    y = min(abs(y), half_width)
    # From just below the centre up the +Y half.
    half = end[len(end) // 2 - 1 :]
    for a, b in zip(half, half[1:], strict=False):
        if a.y <= y <= b.y:
            t = 0.0 if b.y == a.y else (y - a.y) / (b.y - a.y)
            return -(a.x + (b.x - a.x) * t)
    return -end[-1].x


@dataclass(frozen=True, slots=True)
class NeckOutline:
    """Represent the top-view neck taper and parallel heel.

    The tapered section runs from the nut to the final fret. The heel begins
    at the final fret and continues at a constant width.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets.
        nut_width: Neck width at the nut in millimetres.
        last_fret_width: Neck width at the final fret in millimetres.
        heel_width: Constant heel width in millimetres.
        heel_length: Heel length after the final fret in millimetres.
        heel_end_radius: The heel end's arc across it, or 0 for a square
            end (see ``heel_end_curve``).
        heel_corner_radius: A round heel end's corners, blending its arc
            into the sides.

    Raises:
        NeckGeometryError: If dimensions cannot form a valid neck outline.
    """

    scale_length: float
    fret_count: int
    nut_width: float
    last_fret_width: float
    heel_width: float
    heel_length: float
    heel_end_radius: float = 0.0
    heel_corner_radius: float = 0.0
    centerline: Centerline = field(init=False)
    last_fret_position: float = field(init=False)
    nut_line: Line2D = field(init=False)
    last_fret_line: Line2D = field(init=False)
    heel_end_line: Line2D = field(init=False)
    left_taper: Line2D = field(init=False)
    right_taper: Line2D = field(init=False)
    left_heel: Line2D = field(init=False)
    right_heel: Line2D = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and construct the outline segments."""
        self._validate()

        centerline = Centerline(self.scale_length)
        last_fret_position = FretCalculator.calculate(
            self.scale_length,
            self.fret_count,
        )[-1].distance_from_nut
        heel_end = last_fret_position + self.heel_length

        nut_left = Point2D(0.0, self.nut_width / 2.0)
        nut_right = Point2D(0.0, -self.nut_width / 2.0)
        last_fret_left = Point2D(
            last_fret_position,
            self.last_fret_width / 2.0,
        )
        last_fret_right = Point2D(
            last_fret_position,
            -self.last_fret_width / 2.0,
        )
        heel_start_left = Point2D(last_fret_position, self.heel_width / 2.0)
        heel_start_right = Point2D(last_fret_position, -self.heel_width / 2.0)
        heel_end_left = Point2D(heel_end, self.heel_width / 2.0)
        heel_end_right = Point2D(heel_end, -self.heel_width / 2.0)

        object.__setattr__(self, "centerline", centerline)
        object.__setattr__(self, "last_fret_position", last_fret_position)
        object.__setattr__(self, "nut_line", Line2D(nut_left, nut_right))
        object.__setattr__(
            self,
            "last_fret_line",
            Line2D(last_fret_left, last_fret_right),
        )
        object.__setattr__(
            self,
            "heel_end_line",
            Line2D(heel_end_left, heel_end_right),
        )
        object.__setattr__(self, "left_taper", Line2D(nut_left, last_fret_left))
        object.__setattr__(self, "right_taper", Line2D(nut_right, last_fret_right))
        object.__setattr__(
            self,
            "left_heel",
            Line2D(heel_start_left, heel_end_left),
        )
        object.__setattr__(
            self,
            "right_heel",
            Line2D(heel_start_right, heel_end_right),
        )
        square = (
            nut_left,
            nut_right,
            last_fret_right,
            heel_start_right,
            heel_end_right,
            heel_end_left,
            heel_start_left,
            last_fret_left,
        )
        object.__setattr__(
            self,
            "boundary",
            clip_to_heel_end(
                square,
                heel_end,
                self.heel_width / 2.0,
                self.heel_end_radius,
                self.heel_corner_radius,
            ),
        )

    def heel_end_inset(self, y: float) -> float:
        """Return how far short of the heel end, on the centre, it ends at
        ``y`` (nothing for a square end)."""
        return heel_end_inset(
            y, self.heel_width / 2.0, self.heel_end_radius, self.heel_corner_radius
        )

    def trimmed(self, polygon: Sequence[Point2D]) -> tuple[Point2D, ...]:
        """Return a plan polygon (the fretboard's) cut back to a round heel
        end; itself for a square end."""
        return clip_to_heel_end(
            polygon,
            self.last_fret_position + self.heel_length,
            self.heel_width / 2.0,
            self.heel_end_radius,
            self.heel_corner_radius,
        )

    def _validate(self) -> None:
        """Reject non-manufacturable outline dimensions."""
        dimensions = (
            self.scale_length,
            self.nut_width,
            self.last_fret_width,
            self.heel_width,
            self.heel_length,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise NeckGeometryError(
                "Neck outline dimensions must be finite and positive."
            )
        if self.fret_count <= 0:
            raise NeckGeometryError("Fret count must be greater than zero.")
        if self.last_fret_width < self.nut_width:
            raise NeckGeometryError(
                "Last-fret width must not be narrower than the nut."
            )
        if self.heel_width < self.last_fret_width:
            raise NeckGeometryError(
                "Heel width must not be narrower than the final fret."
            )
