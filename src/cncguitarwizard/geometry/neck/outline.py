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

HEEL_FLARE_SAMPLES = 16
"""Points along each side of a flaring heel (``HeelFlare``)."""

SAME_POINT = 1e-6
"""Clipped points nearer each other than this, in mm, are one point."""


@dataclass(frozen=True, slots=True)
class HeelFlare:
    """A heel wider than the neck's taper: the neck and the fretboard on it
    flare out together to its width at the heel end.

    Args:
        heel_end: Where the heel ends, from the nut, in mm.
        length: How far ahead of ``heel_end`` the flare begins, in mm.
        extra: How much wider than the taper the heel end is, in mm.
    """

    heel_end: float
    length: float
    extra: float

    @property
    def start(self) -> float:
        """Return where the flare begins, from the nut."""
        return self.heel_end - self.length

    def extra_at(self, x: float) -> float:
        """Return how much wider than the taper the neck is ``x`` from the
        nut: nothing ahead of the flare, then growing as the square of the
        way along it (so there is no kink where it begins), all of
        ``extra`` from the heel end on."""
        along = (x - self.start) / self.length
        if along <= 0.0:
            return 0.0
        return self.extra * min(1.0, along) ** 2


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
    square_too: bool = False,
) -> tuple[Point2D, ...]:
    """Return a plan polygon cut back to a round heel end.

    Whatever lies past the end (``heel_end_curve``) is cut away; the
    polygon must lie within ``half_width`` of the centre. It is the
    polygon itself for a square end, or, ``square_too``, cut square at
    ``end_x``. A point is never given twice: a corner on a clipping line
    comes out of the clip once more where its edge crosses the line, a
    hair away, and the edge between the two would have no direction to
    offset along (an offset of it, a toolpath, would spike).
    """
    far = min(p.x for p in polygon) - 1.0
    if end_radius == 0.0:
        if not square_too:
            return tuple(polygon)
        reach = half_width + max(abs(p.y) for p in polygon)
        end: Sequence[Point2D] = (Point2D(end_x, -reach), Point2D(end_x, reach))
        region = (Point2D(far, -reach), *end, Point2D(far, reach))
    else:
        end = heel_end_curve(end_x, half_width, end_radius, corner_radius)
        # Convex: back along each side from the end, counter-clockwise.
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
    kept: list[Point2D] = []
    for point in points:
        if (
            not kept
            or math.dist((point.x, point.y), (kept[-1].x, kept[-1].y)) >= SAME_POINT
        ):
            kept.append(point)
    if len(kept) > 1 and (
        math.dist((kept[0].x, kept[0].y), (kept[-1].x, kept[-1].y)) < SAME_POINT
    ):
        kept.pop()
    return tuple(kept)


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
    at the final fret and continues at a constant width; or, where
    ``heel_width`` is wider than the taper reaches at the heel end and
    ``heel_flare_length`` is set, the neck flares out to it over that
    length ahead of the heel end (``heel_flare``), the fretboard on it
    with it.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets.
        nut_width: Neck width at the nut in millimetres.
        last_fret_width: Neck width at the final fret in millimetres.
        heel_width: The heel's width (at its end, where it flares) in
            millimetres.
        heel_length: Heel length after the final fret in millimetres.
        heel_end_radius: The heel end's arc across it, or 0 for a square
            end (see ``heel_end_curve``).
        heel_corner_radius: A round heel end's corners, blending its arc
            into the sides.
        fretboard_to_heel_end: The fretboard runs on past the heel's end
            and is cut back to it (``trimmed``), square or round, so it
            covers the heel and goes no further (``fretboard_end``
            "heel"); else a square end leaves it as it is.
        frets_per_octave: Equal steps in each octave (12; more for a
            microtonal neck): where the final fret, and so the heel, lies.
        heel_flare_length: How far ahead of the heel end a heel wider
            than the taper flares out to it, in millimetres (0: it steps
            out at the final fret).

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
    frets_per_octave: int = 12
    fretboard_to_heel_end: bool = False
    heel_flare_length: float = 0.0
    heel_flare: HeelFlare | None = field(init=False)
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
            self.frets_per_octave,
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
        # A heel wider than the taper reaches at its end flares out to it.
        taper_at_heel_end = (
            self.nut_width
            + (self.last_fret_width - self.nut_width) * heel_end / last_fret_position
        )
        flare = None
        if self.heel_flare_length > 0.0 and self.heel_width > taper_at_heel_end:
            flare = HeelFlare(
                heel_end,
                min(self.heel_flare_length, heel_end),
                self.heel_width - taper_at_heel_end,
            )
        object.__setattr__(self, "heel_flare", flare)
        square: tuple[Point2D, ...] = (
            nut_left,
            nut_right,
            last_fret_right,
            heel_start_right,
            heel_end_right,
            heel_end_left,
            heel_start_left,
            last_fret_left,
        )
        if flare is not None:
            # Each side straight to where the flare begins, then along it.
            stations = (
                0.0,
                *(
                    flare.start + flare.length * k / HEEL_FLARE_SAMPLES
                    for k in range(HEEL_FLARE_SAMPLES + 1)
                ),
            )
            right = [Point2D(x, -self.half_width_at(x)) for x in stations]
            left = [Point2D(x, self.half_width_at(x)) for x in reversed(stations)]
            square = (*left[-1:], *right, *left[:-1])
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

    def half_width_at(self, x: float) -> float:
        """Return the neck's half-width ``x`` from the nut: its taper, then
        the heel's width; or the taper flaring out to a wider heel."""
        taper = (
            self.nut_width
            + (self.last_fret_width - self.nut_width)
            * (max(0.0, x) / self.last_fret_position)
        ) / 2.0
        if self.heel_flare is not None:
            return taper + self.heel_flare.extra_at(x) / 2.0
        return taper if x < self.last_fret_position else self.heel_width / 2.0

    def heel_end_inset(self, y: float) -> float:
        """Return how far short of the heel end, on the centre, it ends at
        ``y`` (nothing for a square end)."""
        return heel_end_inset(
            y, self.heel_width / 2.0, self.heel_end_radius, self.heel_corner_radius
        )

    def trimmed(self, polygon: Sequence[Point2D]) -> tuple[Point2D, ...]:
        """Return a plan polygon (the fretboard's) cut back to a round heel
        end; itself for a square end, or cut square at it when the board
        runs on to it (``fretboard_to_heel_end``)."""
        return clip_to_heel_end(
            polygon,
            self.heel_end_position,
            self.heel_width / 2.0,
            self.heel_end_radius,
            self.heel_corner_radius,
            square_too=self.fretboard_to_heel_end,
        )

    @property
    def heel_end_position(self) -> float:
        """Return where the heel ends along the neck, from the nut."""
        return self.last_fret_position + self.heel_length

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
        if not math.isfinite(self.heel_flare_length) or self.heel_flare_length < 0.0:
            raise NeckGeometryError("The heel's flare must not be negative.")
