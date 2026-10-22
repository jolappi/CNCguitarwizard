"""A volute: wood left on the back of the headstock, behind the nut.

An angled headstock's short grain is weakest right behind the nut, where
it leaves the neck; a volute leaves wood there, carved into the back of
the headstock. Seen from behind its rounded nose reaches a little onto
the neck's back, and it widens behind the nut to the neck's whole width,
fading into the headstock's back; or it is drawn as three lines across
the back: its crest, and where it ends in the headstock's back and in the
neck's, falling away from the crest to each.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..exceptions import NeckGeometryError
from ..primitives import DrawnPoint, Point2D, drawn_points, open_catmull_rom

VOLUTE_LEAD = 1.0 / 3.0
"""How far onto the neck, ahead of the nut, a volute's nose reaches, as a
share of its length."""

VOLUTE_PEAK = 0.3
"""How far behind the nut a volute is fullest, as a share of its length."""

VOLUTE_NOSE = 1.5
"""How a volute's nose rounds, seen from behind: 2 a half ellipse, nearer
1 an arrow's rounded tip (its sides curving in to it), 1.5 between."""

VOLUTE_LOG_STEEPNESS = 9.0
"""How sharply a drawn volute falls from its crest: its fall is
``1 - log(1 + k t) / log(1 + k)`` of the way ``t`` to where it ends, ``k``
this (9: a base-ten logarithm)."""

DEFAULT_VOLUTE_LINES: dict[str, tuple[tuple[float, float], ...]] = {
    "crest": ((-7.0, 0.0), (-5.0, 0.57), (0.0, 1.0)),
    "headstock": ((30.0, 0.0), (31.0, 0.71), (34.0, 1.38)),
    "neck": ((-22.5, 0.0), (-19.0, 0.57), (-13.0, 1.0)),
}
"""Where drawing a volute starts: half of each line seen from behind,
``(behind the nut, across as a share of the neck's half-width)`` from the
centre line out. The crest bulges onto the neck down the middle and meets
the neck's edges at the nut; it ends in the headstock's back about 30 mm
behind the nut, across the headstock's shoulders, and in the neck's
22 mm past it down the middle, 13 mm at the edges."""


@dataclass(frozen=True, slots=True)
class Volute:
    """A volute carved on the back of the headstock, its nose rounded.

    The model's ``x`` runs from the nut toward the body, so the headstock
    is at negative ``x``. The volute's rounded nose reaches the neck's
    back ``VOLUTE_LEAD`` of its length ahead of the nut: seen from behind
    a rounded arrow (``VOLUTE_NOSE``) widening to the neck's whole width
    ``VOLUTE_PEAK`` of its length behind the nut, where it is fullest,
    ``depth`` more wood than the plain back down the middle; from there it
    fades smoothly into the headstock's back, the whole width still,
    ``length`` behind the nut. Across, two faces fall away from a rounded
    crest down the middle and each eases into the back at its outline, as
    a builder carves one.

    A drawn volute is three lines across the back instead: its ``crest``,
    ``depth`` proud of the plain back along it, and where it ends in the
    headstock's back (``headstock_end``) and in the neck's (``neck_end``).
    It is sharp along its crest, falling away from it on a logarithmic
    curve to each end, steep from the crest and flattening out, and meets
    the back there with no edge (``_fall``).

    Args:
        depth: The wood it adds at its fullest, below the plain back: a
            drawn one's height along its crest.
        length: How far behind the nut the rounded arrow reaches.
        half_width: Half the neck's width at the nut.
        crest: A drawn volute's crest seen from behind, across the back
            from one side to the other, in the model frame; empty for the
            rounded arrow.
        headstock_end: Where a drawn volute ends in the headstock's back.
        neck_end: Where a drawn volute ends in the neck's back.

    Raises:
        NeckGeometryError: For a size that is not finite and positive, or
            a drawn volute missing a line (two points each at least).
    """

    depth: float
    length: float
    half_width: float
    crest: tuple[Point2D, ...] = ()
    headstock_end: tuple[Point2D, ...] = ()
    neck_end: tuple[Point2D, ...] = ()
    headstock_sides: tuple[float, float, float] = field(
        init=False, repr=False, compare=False
    )
    """Which side of each drawn line (crest, headstock end, neck end) the
    headstock is: the sign of ``_nearest``'s side there."""

    def __post_init__(self) -> None:
        """Reject a volute that cannot be carved; find which side of each
        drawn line the headstock is."""
        for name in ("depth", "length", "half_width"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise NeckGeometryError(
                    f"The volute's {name} must be finite and positive."
                )
        lines = (self.crest, self.headstock_end, self.neck_end)
        if any(lines) and not all(len(line) >= 2 for line in lines):
            raise NeckGeometryError(
                "A drawn volute needs its crest and both its ends, two points each."
            )
        object.__setattr__(
            self,
            "headstock_sides",
            tuple(_headstock_side(line) for line in lines),
        )

    @property
    def drawn(self) -> bool:
        """Return whether it is drawn (its three lines), not the arrow."""
        return bool(self.crest)

    @property
    def point(self) -> float:
        """Return where its nose ends on the neck, ahead of the nut."""
        return self.length * VOLUTE_LEAD

    @property
    def fullest(self) -> float:
        """Return where it is fullest, behind the nut (a negative ``x``)."""
        return -self.length * VOLUTE_PEAK

    def extra(self, x: float, y: float) -> float:
        """Return the wood it adds below the plain back at ``(x, y)``."""
        if self.drawn:
            return self._drawn_extra(Point2D(x, y))
        if not -self.length < x < self.point:
            return 0.0
        if x >= self.fullest:
            # Its rounded nose: an arrow's, its sides curving from the
            # neck's whole width at its fullest in to a round tip, the wood
            # falling away smoothly to it all round.
            ahead = (x - self.fullest) / (self.point - self.fullest)
            radius = ahead**VOLUTE_NOSE + (y / self.half_width) ** 2
            return self.depth * (1.0 - radius) ** 2 if radius < 1.0 else 0.0
        # Behind its fullest it fades into the headstock's back, the whole
        # width still; across, two faces fall away from a rounded crest
        # down the middle, each easing into the back at the outline (a
        # sharp crest leaves the lofted solid too hard for FreeCAD's
        # booleans).
        fade = (self.fullest - x) / (self.fullest + self.length)
        across = abs(y) / self.half_width
        if across >= 1.0:
            return 0.0
        return self.depth * (1.0 - _smootherstep(fade)) * (1.0 - across**2) ** 2

    def _drawn_extra(self, point: Point2D) -> float:
        """Return a drawn volute's wood at ``point``: ``depth`` on its
        crest, falling away to nothing at the end on that side of it."""
        crest_side, headstock_end_side, neck_end_side = self.headstock_sides
        to_crest, side = _nearest(point, self.crest)
        toward_headstock = side * crest_side >= 0.0
        end, end_side = (
            (self.headstock_end, headstock_end_side)
            if toward_headstock
            else (self.neck_end, neck_end_side)
        )
        to_end, side = _nearest(point, end)
        past_end = (side * end_side >= 0.0) == toward_headstock
        if past_end or to_crest + to_end == 0.0:
            return 0.0
        return self.depth * _fall(to_crest / (to_crest + to_end))


def side_share(depth: float, middle_depth: float) -> float:
    """Return the share of a volute's wood a point of the back gets.

    All of it down the middle of the back, less up its sides, as the back
    there is less deep below the face (``depth`` against the middle's
    ``middle_depth``), none at its edges, level with the face: so the
    volute's sides come down evenly to the face (the fretboard's glue
    plane) instead of standing out from them. On the neck's rounded back
    the volute so makes its profile deeper, the same shape.

    Args:
        depth: How far below the face the plain back is at the point.
        middle_depth: How far below it the plain back is down its middle.

    Returns:
        The share, 0 to 1.
    """
    if middle_depth <= 0.0:
        return 0.0
    return max(0.0, min(1.0, depth / middle_depth))


def default_volute_lines(half_width: float) -> dict[str, tuple[DrawnPoint, ...]]:
    """Return a drawn volute's three lines where drawing one starts.

    Each half of it seen from behind, ``(behind the nut, across)`` from the
    centre line out to one side, as ``drawn_volute_line`` takes them
    (``DEFAULT_VOLUTE_LINES``, across scaled by the neck's half-width).

    Returns:
        ``{"crest", "headstock", "neck"}``.
    """
    return {
        name: tuple((behind, round(share * half_width, 1)) for behind, share in line)
        for name, line in DEFAULT_VOLUTE_LINES.items()
    }


def drawn_volute_line(points: Sequence[DrawnPoint]) -> tuple[Point2D, ...]:
    """Return one of a drawn volute's lines across the back, model frame.

    Args:
        points: Half of it seen from behind, ``(behind the nut, across)``
            from the centre line out to one side (a point marked
            ``"corner"`` a sharp bend); the other half mirrors it.

    Returns:
        A smooth line through them and their mirror, from one side to the
        other; empty for none.

    Raises:
        NeckGeometryError: For fewer than two points, mirrored.
    """
    if not points:
        return ()
    half, corners = drawn_points(points)
    model = [Point2D(-point.x, point.y) for point in half]
    mirror = [
        (Point2D(point.x, -point.y), corner)
        for point, corner in zip(reversed(model), reversed(corners), strict=True)
        if abs(point.y) > 1e-9
    ]
    whole = (*(point for point, _ in mirror), *model)
    if len(whole) < 2:
        raise NeckGeometryError("A drawn volute's line needs two points.")
    return open_catmull_rom(whole, 8, (*(corner for _, corner in mirror), *corners))


def _fall(fraction: float) -> float:
    """Return the share of a drawn volute's height ``fraction`` of the way
    from its crest to where it ends.

    A logarithmic fall, ``1 - log(1 + k t) / log(1 + k)``, steep from the
    crest (so the two sides meet there in an edge) and flattening out,
    less ``m t (1 - t)``, ``m`` its slope at the end: the same at the crest
    and the end, but meeting the back there level, with no edge.
    """
    if fraction >= 1.0:
        return 0.0
    k = VOLUTE_LOG_STEEPNESS
    end_slope = -k / ((1.0 + k) * math.log(1.0 + k))
    return (
        1.0
        - math.log(1.0 + k * fraction) / math.log(1.0 + k)
        + end_slope * fraction * (1.0 - fraction)
    )


def _headstock_side(line: tuple[Point2D, ...]) -> float:
    """Return which side of ``line`` the headstock is, as ``_nearest``'s
    side sign: tried a millimetre toward it from the line's middle."""
    if not line:
        return 1.0
    middle = line[len(line) // 2]
    _, side = _nearest(Point2D(middle.x - 1.0, middle.y), line)
    return 1.0 if side >= 0.0 else -1.0


def _nearest(point: Point2D, line: tuple[Point2D, ...]) -> tuple[float, float]:
    """Return how far ``point`` is from the open ``line``, and which side
    of it it is on (the sign of the turn from the line's way to it)."""
    best, side = math.inf, 0.0
    for start, end in zip(line, line[1:], strict=False):
        dx, dy = end.x - start.x, end.y - start.y
        length_squared = dx * dx + dy * dy
        along = (
            0.0
            if length_squared == 0.0
            else max(
                0.0,
                min(
                    1.0,
                    ((point.x - start.x) * dx + (point.y - start.y) * dy)
                    / length_squared,
                ),
            )
        )
        off_x = point.x - start.x - along * dx
        off_y = point.y - start.y - along * dy
        distance = math.hypot(off_x, off_y)
        if distance < best:
            best, side = distance, dx * off_y - dy * off_x
    return best, side


def _smootherstep(fraction: float) -> float:
    """Return the quintic ease from 0 to 1, flat at both ends."""
    return fraction**3 * (fraction * (fraction * 6.0 - 15.0) + 10.0)
