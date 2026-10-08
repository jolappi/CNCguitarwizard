"""Humbucker frames: decorative plates round each humbucker, cut from sheet.

A plain ``ring``, a rounded rectangle round the route like a pickup
mounting ring; and two styles traced from the builder's drawing
(``humbframes.dxf``): ``horns``, a frame whose ends sweep into a horn
either side toward the neck, its bridge side round; and ``hook``, its
bass end cut in to a hook and its treble end sweeping into one long horn
toward the neck. The drawing's lines were pen strokes (their outer edge
is traced) and its size arbitrary: it is scaled so its opening is the
humbucker's, 70.5 mm across the strings, and the opening itself is cut
to the pickup's own (``pickups.pickup_openings``, the pickguard's), not
as drawn.

A frame's outline is a closed Catmull-Rom loop through its points, given
in the frame's own frame: ``a`` along the neck toward the bridge, ``c``
across it, the bass side negative, in millimetres, the opening centred
on the origin, the horns toward the neck (negative ``a``). Every
humbucker gets one, turned with the pickup, opened across the strings
with its route for seven and eight strings, mirrored for a left-handed
build and, where it does not fit with its horns toward the neck (or
when asked), turned round; a style's frame that does not fit either way
is cut back where it must be (``fitted_frame``). It must reach a little
past the pickup's opening all round. Four screws hold it, two past each
of the pickup's ears; it has holes over the pickup's height screws, to
reach them through it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from ..geometry.body import CoverPlate, DrilledHole, TracedCavity
from ..geometry.primitives import Point2D, closed_catmull_rom, point_in_polygon
from ._omarunko_outline import OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS
from .body_shapes import narrow_y, widen_y
from .controls import SCREW_CLEARANCE, SCREW_SPOT_DEPTH, SCREW_SPOT_DIAMETER

PickupFrameStyle = Literal["none", "ring", "horns", "hook"]
"""A humbucker frame's style: none, a plain ring or a traced frame."""

PICKUP_FRAME_STYLES: tuple[str, ...] = ("none", "ring", "horns", "hook")

FrameDirection = Literal["auto", "neck", "bridge"]
"""Which way a frame's horns point: ``auto`` toward the neck, turned round
where they do not fit that way."""

FRAME_SAMPLES_PER_SEGMENT = 8
"""Outline points per span of a frame's loop."""

FRAME_SCREW_ROOM = 4.0
"""How far a frame screw keeps from the pickup's ear and the frame's edge
(mm): its head's radius and a little."""

HEIGHT_SCREW_ACCESS = 6.5
"""The hole over each pickup height screw, to reach it through the frame
(mm): the screw's head passes through it."""

EAR_REACH = max(abs(y) for _, y in OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS)
"""How far the humbucker's route, its ears, reaches either side (mm)."""

# fmt: off
RING_POINTS: tuple[tuple[float, float], ...] = (
    (24.5, 47.0), (22.74, 51.24), (18.5, 53.0), (16.5, 53.0),
    (10.5, 53.0), (-10.5, 53.0), (-16.5, 53.0), (-18.5, 53.0),
    (-22.74, 51.24), (-24.5, 47.0), (-24.5, 45.0), (-24.5, 39.0),
    (-24.5, -39.0), (-24.5, -45.0), (-24.5, -47.0), (-22.74, -51.24),
    (-18.5, -53.0), (-16.5, -53.0), (-10.5, -53.0), (10.5, -53.0),
    (16.5, -53.0), (18.5, -53.0), (22.74, -51.24), (24.5, -47.0),
    (24.5, -45.0), (24.5, -39.0), (24.5, 39.0), (24.5, 45.0),
)
"""The plain ring's handles: a rounded rectangle 49 x 106 mm (corners
6 mm), round the route and its ears with room past them for the screws."""

HORNS_POINTS: tuple[tuple[float, float], ...] = (
    (-27.9, -79.54), (-24.93, -79.39), (-21.21, -78.96), (-14.55, -77.86),
    (-7.98, -76.38), (-1.52, -74.43), (10.13, -69.32), (15.8, -65.67),
    (20.82, -61.17), (24.88, -55.8), (26.29, -53.16), (27.7, -49.69),
    (28.95, -43.09), (29.06, -36.35), (29.1, -22.85), (29.1, -9.36),
    (29.09, 16.87), (29.04, 30.37), (28.7, 43.84), (27.18, 50.41),
    (24.56, 56.62), (20.89, 62.27), (16.29, 67.18), (10.98, 71.34),
    (5.12, 74.68), (-7.47, 79.46), (-13.3, 80.9), (-19.94, 82.06),
    (-22.91, 82.48), (-26.63, 82.96), (-27.74, 82.55), (-26.45, 81.78),
    (-23.23, 79.87), (-17.72, 75.99), (-12.81, 71.37), (-8.99, 65.85),
    (-7.7, 59.31), (-9.94, 53.03), (-14.59, 48.17), (-20.13, 44.34),
    (-22.76, 42.9), (-26.12, 41.24), (-27.48, 40.61), (-28.0, 39.45),
    (-28.0, 36.45), (-27.99, 29.7), (-27.97, 16.21), (-27.93, -10.77),
    (-27.91, -24.27), (-27.9, -31.01), (-27.9, -34.01), (-27.9, -37.76),
    (-27.89, -39.26), (-26.9, -40.17), (-24.27, -41.6), (-21.73, -43.19),
    (-18.86, -45.6), (-16.78, -47.76), (-14.77, -50.9), (-13.86, -53.75),
    (-13.56, -57.47), (-15.22, -63.97), (-18.67, -69.76), (-20.55, -72.09),
    (-23.1, -74.84), (-25.21, -76.97), (-26.25, -78.05),
)
"""The horns frame's handles (see the module docstring)."""

HOOK_POINTS: tuple[tuple[float, float], ...] = (
    (-15.25, -49.46), (-16.09, -48.22), (-17.02, -47.05), (-19.13, -44.92),
    (-24.0, -41.44), (-26.64, -40.01), (-27.78, -39.21), (-27.78, -37.71),
    (-27.78, -34.71), (-27.78, -31.71), (-27.78, -25.71), (-27.78, -19.72),
    (-27.78, -7.72), (-27.78, 16.27), (-27.78, 28.26), (-27.78, 34.26),
    (-27.78, 37.26), (-27.66, 40.18), (-25.64, 41.18), (-22.97, 42.53),
    (-17.8, 45.56), (-12.96, 49.1), (-9.2, 53.74), (-7.44, 59.41),
    (-7.7, 62.39), (-8.57, 65.25), (-11.57, 70.42), (-15.77, 74.69),
    (-20.49, 78.38), (-22.99, 80.05), (-25.54, 81.62), (-26.81, 82.41),
    (-25.59, 82.47), (-22.61, 82.16), (-16.67, 81.3), (-5.03, 78.46),
    (6.02, 73.84), (11.2, 70.83), (15.95, 67.17), (23.57, 57.97),
    (27.89, 46.83), (28.81, 34.9), (28.85, 22.91), (28.85, 10.92),
    (28.82, -12.32), (28.8, -24.32), (28.78, -36.31), (28.77, -42.31),
    (28.72, -45.3), (27.94, -48.2), (25.75, -53.77), (22.53, -58.82),
    (20.62, -61.12), (18.61, -63.35), (17.43, -60.85), (15.99, -58.23),
    (12.19, -53.61), (9.89, -51.69), (7.37, -50.06), (1.83, -47.8),
    (-4.09, -46.96), (-10.04, -47.6), (-12.91, -48.46), (-14.3, -49.02),
)
"""The hook frame's handles."""
# fmt: on

FRAME_POINTS: dict[str, tuple[tuple[float, float], ...]] = {
    "ring": RING_POINTS,
    "horns": HORNS_POINTS,
    "hook": HOOK_POINTS,
}
"""Each style's handles."""


@dataclass(frozen=True, slots=True)
class FramePlacing:
    """Where a frame's own frame lies in the model.

    Attributes:
        origin: The opening's centre.
        along: The model direction of the frame's ``a`` (a unit vector).
        across: The model direction of its ``c``.
        stretch: How much it is opened across (a seven- or eight-string
            humbucker's): ``c`` beyond the middle moves out by half.
    """

    origin: Point2D
    along: tuple[float, float]
    across: tuple[float, float]
    stretch: float

    def to_model(self, a: float, c: float) -> Point2D:
        """Return the model point of a frame point."""
        c = widen_y(c, self.stretch)
        return Point2D(
            self.origin.x + a * self.along[0] + c * self.across[0],
            self.origin.y + a * self.along[1] + c * self.across[1],
        )

    def to_frame(self, point: Point2D) -> tuple[float, float]:
        """Return a model point in the frame's own frame."""
        a, c = self.to_axes(point)
        return a, narrow_y(c, self.stretch)

    def to_axes(self, point: Point2D) -> tuple[float, float]:
        """Return a model point along and across the frame, as placed
        (opened across: no stretch taken off)."""
        dx, dy = point.x - self.origin.x, point.y - self.origin.y
        return (
            dx * self.along[0] + dy * self.along[1],
            dx * self.across[0] + dy * self.across[1],
        )

    def from_axes(self, a: float, c: float) -> Point2D:
        """Return the model point along and across the frame, as placed."""
        return Point2D(
            self.origin.x + a * self.along[0] + c * self.across[0],
            self.origin.y + a * self.along[1] + c * self.across[1],
        )


def frame_placing(
    centre_x: float,
    bass_sign: float,
    angle_degrees: float,
    stretch: float,
    turned: bool,
) -> FramePlacing:
    """Return how a frame on a pickup centred at ``centre_x`` lies.

    It turns with the pickup by ``angle_degrees`` as ``pickups`` turns a
    route (the treble end toward the tail); its bass side is toward
    ``bass_sign``; ``turned`` turns it round, its horns toward the bridge.
    """
    angle = math.radians(angle_degrees) * bass_sign
    cosine, sine = math.cos(angle), math.sin(angle)
    flip = -1.0 if turned else 1.0
    # Pickup-local X along the neck, Y across (the bass side at bass_sign).
    along = (flip * cosine, flip * sine)
    across_y = -bass_sign * flip
    across = (-across_y * sine, across_y * cosine)
    return FramePlacing(Point2D(centre_x, 0.0), along, across, stretch)


def frame_outline(
    points: Sequence[tuple[float, float]],
    placing: FramePlacing,
    samples: int = FRAME_SAMPLES_PER_SEGMENT,
) -> tuple[Point2D, ...]:
    """Return a frame's outline in the model through its points."""
    return tuple(
        closed_catmull_rom([placing.to_model(a, c) for a, c in points], samples)
    )


@dataclass(frozen=True, slots=True)
class PickupFrame:
    """One humbucker's frame.

    Attributes:
        position: ``"neck"``, ``"middle"`` or ``"bridge"``.
        points: Its handles in its own frame (as ``body_<position>_frame_points``
            holds them).
        placing: Where its own frame lies.
        turned: Whether it is turned round, its horns toward the bridge.
        plate: The frame as a sheet plate on the top: its opening, its two
            screws' holes and the holes over the pickup's height screws.
        screw_spots: The pilots for its screws, drilled into the top.
        problem: Why it does not fit, or ``None``.
        adjusted: Whether the style's shape was cut back to fit (see
            ``fitted_frame``).
    """

    position: str
    points: tuple[tuple[float, float], ...]
    placing: FramePlacing
    turned: bool
    plate: CoverPlate
    screw_spots: tuple[DrilledHole, ...]
    problem: str | None = None
    adjusted: bool = False


def pickup_frame(
    position: str,
    points: Sequence[tuple[float, float]],
    placing: FramePlacing,
    turned: bool,
    *,
    thickness: float,
    opening: tuple[Point2D, ...],
    height_screws: Sequence[tuple[str, float, float]],
) -> PickupFrame:
    """Return the frame through ``points`` on its pickup, not yet checked.

    Its four screws sit two past each of the pickup's ears, as far apart
    along the neck as the frame lets them with ``FRAME_SCREW_ROOM`` of it
    all round (see ``_screw_pair``); with no room, ``problem`` says so.
    """
    label = position.capitalize()
    outline = frame_outline(points, placing)
    local = [placing.to_axes(point) for point in outline]
    problem = None
    screws: list[Point2D] = []
    ear = EAR_REACH + placing.stretch / 2.0
    region = KeptRegion(
        [Point2D(a, c) for a, c in local], FRAME_SCREW_ROOM, inside=True
    )
    for side, sign in (("bass", -1.0), ("treble", 1.0)):
        pair = _screw_pair(local, region, sign, ear)
        if pair is None:
            problem = problem or (
                f"The {position} pickup's frame leaves no room for its two screws "
                f"past the pickup's {side} ear: they need "
                f"{SCREW_PAIR_SPACING:g} mm between them along the neck and "
                f"{FRAME_SCREW_ROOM:g} mm of frame all round; widen it there."
            )
            continue
        screws += [placing.from_axes(*spot) for spot in pair]
    plate = CoverPlate(
        f"{label} pickup frame",
        "top",
        outline,
        thickness,
        holes=(
            *(
                DrilledHole(
                    f"{side.capitalize()} height screw access",
                    x,
                    y,
                    HEIGHT_SCREW_ACCESS,
                    thickness,
                )
                for side, x, y in height_screws
            ),
            *(
                DrilledHole(f"Screw {index}", p.x, p.y, SCREW_CLEARANCE, thickness)
                for index, p in enumerate(screws, start=1)
            ),
        ),
        slots=(TracedCavity(f"{label} pickup opening", opening, thickness),),
        recessed=False,
    )
    spots = tuple(
        DrilledHole(
            f"{label} pickup frame screw {index}",
            p.x,
            p.y,
            SCREW_SPOT_DIAMETER,
            thickness + SCREW_SPOT_DEPTH,
        )
        for index, p in enumerate(screws, start=1)
    )
    return PickupFrame(position, tuple(points), placing, turned, plate, spots, problem)


SCREW_PAIR_SPACING = 8.0
"""The least (mm) a frame's two screws past one ear lie apart."""


def _screw_pair(
    local: Sequence[tuple[float, float]],
    region: KeptRegion,
    sign: float,
    ear: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Return where a frame's two screws past one ear go, or ``None``.

    Past the pickup's ear (``ear`` across, toward ``sign``), each with
    ``FRAME_SCREW_ROOM`` of frame all round (``region``, the frame in its
    own axes): looked for in millimetre steps across the frame, at the
    distance from the ear where the frame leaves the longest stretch
    along the neck (the middle one of those within a millimetre of it),
    at that stretch's two ends, as far apart as it lets them, at least
    ``SCREW_PAIR_SPACING``.
    """
    reach = max(sign * c for _, c in local)
    low = math.floor(min(a for a, _ in local))
    high = math.ceil(max(a for a, _ in local))
    rows: list[tuple[float, float, float, float]] = []
    c = ear + FRAME_SCREW_ROOM
    while c < reach:
        best: tuple[float, float, float] | None = None
        start: float | None = None
        for step in range(int(high - low) + 2):
            a = low + step
            usable = a <= high and not region.breaks(Point2D(a, sign * c))
            if usable and start is None:
                start = a
            elif not usable and start is not None:
                run = (a - 1.0 - start, start, a - 1.0)
                if best is None or run[0] > best[0]:
                    best = run
                start = None
        if best is not None and best[0] >= SCREW_PAIR_SPACING:
            rows.append((best[0], c, best[1], best[2]))
        c += 1.0
    if not rows:
        return None
    widest = max(row[0] for row in rows)
    near = [row for row in rows if row[0] >= widest - 1.0]
    _, c, first, last = near[len(near) // 2]
    return (first, sign * c), (last, sign * c)


def frame_problem(
    frame: PickupFrame,
    body: KeptRegion,
    obstacles: Sequence[tuple[str, Sequence[Point2D]]],
    cover: Sequence[Point2D] = (),
) -> str | None:
    """Return why a frame does not fit, or ``None``.

    It must lie on the body's flat top (``body``: inside its outline, its
    margin in from the edge), reach ``FRAME_MIN_BORDER`` past the
    pickup's opening all round (``cover``: the opening grown by it), keep
    clear of every one of ``obstacles`` (named outlines: the neck, the
    bridge, other pickups' routes and frames, the controls on the top) and
    have room for its screws.
    """
    if frame.problem:
        return frame.problem
    return outline_problem(frame.position, frame.plate.outline, body, obstacles, cover)


def outline_problem(
    position: str,
    outline: Sequence[Point2D],
    body: KeptRegion,
    obstacles: Sequence[tuple[str, Sequence[Point2D]]],
    cover: Sequence[Point2D] = (),
) -> str | None:
    """Return why a frame's ``outline`` does not fit, or ``None`` (see
    ``frame_problem``; its screws are not looked at)."""
    if any(body.breaks(point) for point in outline):
        return (
            f"The {position} pickup's frame runs off the body's flat top (it "
            f"keeps {body.margin:g} mm in from the edge)."
        )
    if cover:
        frame = PolygonBands(outline)
        if not all(frame.contains(point) for point in cover):
            return (
                f"The {position} pickup's frame does not reach "
                f"{FRAME_MIN_BORDER:g} mm past its opening all round."
            )
    for name, polygon in obstacles:
        if polygons_overlap(outline, polygon):
            return f"The {position} pickup's frame runs into {name}."
    return None


FRAME_EDGE_MARGIN = 2.0
"""How far (mm) a frame keeps in from the body's edge, at least (past a
roundover, it keeps to the flat top)."""

FRAME_CLEARANCE = 1.0
"""How far (mm) a fitted frame keeps from what it must not cover."""

FRAME_MIN_BORDER = 1.0
"""How far (mm) a frame reaches past the pickup's opening, at least."""

FIT_SPACING = 6.0
"""The most (mm) a fitted frame's points lie apart before it is fitted."""

FIT_BACK_OFF = 0.5
"""How far (mm) past a margin a fitted frame's moved point stops (its loop
bows a little past its points)."""


class KeptRegion:
    """A polygon a frame keeps inside, or out of, by a margin.

    The body's flat top (``inside``: in its outline, the margin in from
    the edge) or an obstacle and the clearance round it. Edges are looked
    up by band, so a point is tested against those near it only.
    """

    __slots__ = (
        "_box",
        "_count",
        "_edge_bands",
        "_height",
        "_min_y",
        "bands",
        "edges",
        "inside",
        "margin",
        "polygon",
    )

    def __init__(
        self, polygon: Sequence[Point2D], margin: float, *, inside: bool
    ) -> None:
        self.polygon = tuple(polygon)
        self.margin = margin
        self.inside = inside
        self.bands = PolygonBands(self.polygon)
        self.edges = tuple(zip(self.polygon, (*self.polygon[1:], self.polygon[0])))
        xs = [p.x for p in self.polygon]
        ys = [p.y for p in self.polygon]
        # Its bounding box grown by the margin: past it, nothing is near.
        self._box = (
            min(xs) - margin,
            max(xs) + margin,
            min(ys) - margin,
            max(ys) + margin,
        )
        self._min_y = min(ys) - margin
        self._count = 64
        self._height = (max(ys) + margin - self._min_y) / self._count or 1.0
        self._edge_bands: list[list[tuple[float, float, float, float]]] = [
            [] for _ in range(self._count)
        ]
        for a, b in self.edges:
            low = self._band(min(a.y, b.y) - margin)
            high = self._band(max(a.y, b.y) + margin)
            for index in range(low, high + 1):
                self._edge_bands[index].append((a.x, a.y, b.x, b.y))

    def _band(self, y: float) -> int:
        return min(self._count - 1, max(0, int((y - self._min_y) / self._height)))

    def breaks(self, point: Point2D) -> bool:
        """Return whether a frame may not be at ``point``: on the wrong side
        of the edge, or within the margin of it."""
        x, y = point.x, point.y
        min_x, max_x, min_y, max_y = self._box
        if not (min_x <= x <= max_x and min_y <= y <= max_y):
            return self.inside
        if self.bands.contains(point) != self.inside:
            return True
        reach = self.margin * self.margin
        for ax, ay, bx, by in self._edge_bands[self._band(y)]:
            dx, dy = bx - ax, by - ay
            squared = dx * dx + dy * dy
            t = 0.0
            if squared > 0.0:
                t = ((x - ax) * dx + (y - ay) * dy) / squared
                t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
            ex, ey = ax + t * dx - x, ay + t * dy - y
            if ex * ex + ey * ey < reach:
                return True
        return False

    def way_out(self, point: Point2D) -> Point2D:
        """Return the nearest place a frame may be: past the nearest edge
        on the kept side, its margin and ``FIT_BACK_OFF`` from it."""
        best, nearest = math.inf, point
        for a, b in self.edges:
            candidate = _nearest_on(point, a, b)
            distance = math.hypot(candidate.x - point.x, candidate.y - point.y)
            if distance < best:
                best, nearest = distance, candidate
        if best < 1e-9:
            return point
        # From the edge toward the point, or on through the edge from it.
        sign = 1.0 if self.bands.contains(point) == self.inside else -1.0
        reach = self.margin + FIT_BACK_OFF
        return Point2D(
            nearest.x + sign * (point.x - nearest.x) / best * reach,
            nearest.y + sign * (point.y - nearest.y) / best * reach,
        )


def frame_zones(
    obstacles: Sequence[tuple[str, Sequence[Point2D]]],
) -> list[KeptRegion]:
    """Return what a fitted frame keeps ``FRAME_CLEARANCE`` out of: each of
    ``obstacles`` (a point or a line, round it)."""
    zones = []
    for _, polygon in obstacles:
        if len(polygon) >= 3:
            zones.append(KeptRegion(polygon, FRAME_CLEARANCE, inside=False))
        else:
            zones += [
                KeptRegion(_circle(point, 0.5), FRAME_CLEARANCE, inside=False)
                for point in polygon
            ]
    return zones


def fitted_frame(
    points: Sequence[tuple[float, float]],
    placing: FramePlacing,
    body: KeptRegion,
    zones: Sequence[KeptRegion],
) -> tuple[tuple[float, float], ...]:
    """Return a frame's points moved where needed to fit.

    Its points are first spread along its own loop no more than
    ``FIT_SPACING`` apart (so a point moved does not swing a long span
    past its neighbours). Every point off the ``body``'s flat top or in
    one of the ``zones`` is moved the nearest way out — or, where that
    leaves it in something else, pulled in toward the pickup's opening
    until it is clear — ``FIT_BACK_OFF`` past the margin; where the loop
    between two points still strays, a point is added there (the middle
    of the stretch) and moved too, a few rounds over, and points doubling
    back are dropped. Elsewhere the frame keeps its shape, and it always
    stays round its opening.
    """
    origin = placing.origin

    def allowed(point: Point2D) -> bool:
        return not body.breaks(point) and not any(zone.breaks(point) for zone in zones)

    def pulled(point: Point2D) -> Point2D:
        if allowed(point):
            return point
        moved = point
        for _ in range(3):
            if body.breaks(moved):
                moved = body.way_out(moved)
            for zone in zones:
                if zone.breaks(moved):
                    moved = zone.way_out(moved)
        if allowed(moved):
            return moved
        # Else in toward the opening, which is always clear.
        dx, dy = point.x - origin.x, point.y - origin.y
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return point

        def at(t: float) -> Point2D:
            return Point2D(origin.x + dx * t, origin.y + dy * t)

        steps = max(1, math.ceil(length / 0.5))
        low, high = 0.0, 1.0
        for step in range(1, steps + 1):
            if not allowed(at(step / steps)):
                high = step / steps
                break
            low = step / steps
        for _ in range(6):
            middle = (low + high) / 2.0
            if allowed(at(middle)):
                low = middle
            else:
                high = middle
        return at(max(0.0, low - FIT_BACK_OFF / length))

    drawn = [placing.to_model(a, c) for a, c in points]
    loop = closed_catmull_rom(drawn, FRAME_SAMPLES_PER_SEGMENT)
    even: list[Point2D] = []
    for index, point in enumerate(drawn):
        even.append(point)
        after = drawn[(index + 1) % len(drawn)]
        extra = min(
            FRAME_SAMPLES_PER_SEGMENT - 1,
            math.ceil(math.hypot(after.x - point.x, after.y - point.y) / FIT_SPACING)
            - 1,
        )
        for step in range(1, extra + 1):
            offset = round(step * FRAME_SAMPLES_PER_SEGMENT / (extra + 1))
            even.append(loop[index * FRAME_SAMPLES_PER_SEGMENT + offset])
    model = [pulled(point) for point in even]
    # Checked twice as finely as the outline is drawn, so no stretch of it
    # between two of its points cuts a corner.
    check = 2 * FRAME_SAMPLES_PER_SEGMENT
    for _ in range(12):
        loop = closed_catmull_rom(model, check)
        stray: dict[int, list[Point2D]] = {}
        for index, sample in enumerate(loop):
            if index % check and not allowed(sample):
                stray.setdefault(index // check, []).append(sample)
        added = False
        # The middle of each span's stray stretch, the deepest into it.
        for span in sorted(stray, reverse=True):
            samples = stray[span]
            point = pulled(samples[len(samples) // 2])
            neighbours = (model[span], model[(span + 1) % len(model)])
            if all(math.hypot(point.x - n.x, point.y - n.y) > 0.3 for n in neighbours):
                model.insert(span + 1, point)
                added = True
        if not added:
            break
        model = _tidied(model)
    return tuple(
        (round(a, 2), round(c, 2))
        for a, c in (placing.to_frame(point) for point in model)
    )


def _tidied(model: list[Point2D]) -> list[Point2D]:
    """Return a loop's points without those doubling back on their way
    (turning by more than 135°) or within 0.5 mm of the one before."""
    model = list(model)
    changed = True
    while changed and len(model) > 4:
        changed = False
        for index, point in enumerate(model):
            before, after = model[index - 1], model[(index + 1) % len(model)]
            ax, ay = point.x - before.x, point.y - before.y
            bx, by = after.x - point.x, after.y - point.y
            first, second = math.hypot(ax, ay), math.hypot(bx, by)
            if first < 0.5 or (
                second > 1e-9 and ax * bx + ay * by < -0.7 * first * second
            ):
                del model[index]
                changed = True
                break
    return model


def _nearest_on(point: Point2D, a: Point2D, b: Point2D) -> Point2D:
    dx, dy = b.x - a.x, b.y - a.y
    squared = dx * dx + dy * dy
    t = 0.0
    if squared > 0.0:
        t = max(0.0, min(1.0, ((point.x - a.x) * dx + (point.y - a.y) * dy) / squared))
    return Point2D(a.x + t * dx, a.y + t * dy)


def _circle(centre: Point2D, radius: float) -> tuple[Point2D, ...]:
    return tuple(
        Point2D(
            centre.x + radius * math.cos(math.pi * k / 8.0),
            centre.y + radius * math.sin(math.pi * k / 8.0),
        )
        for k in range(16)
    )


def outline_area(outline: Sequence[Point2D]) -> float:
    """Return the area a closed outline holds."""
    return abs(
        sum(a.x * b.y - b.x * a.y for a, b in zip(outline, (*outline[1:], outline[0])))
        / 2.0
    )


class PolygonBands:
    """A polygon split into horizontal bands, to tell fast what is inside.

    Each band keeps the edges that reach into it, so a point is tested
    against those alone (the even-odd rule, as ``point_in_polygon``).
    """

    __slots__ = ("bands", "count", "height", "max_y", "min_y")

    def __init__(self, polygon: Sequence[Point2D], count: int = 64) -> None:
        ys = [p.y for p in polygon]
        self.min_y, self.max_y = min(ys), max(ys)
        self.count = count
        self.height = (self.max_y - self.min_y) / count or 1.0
        self.bands: list[list[tuple[Point2D, Point2D]]] = [[] for _ in range(count)]
        for a, b in zip(polygon, (*polygon[1:], polygon[0])):
            low = self._band(min(a.y, b.y))
            high = self._band(max(a.y, b.y))
            for index in range(low, high + 1):
                self.bands[index].append((a, b))

    def _band(self, y: float) -> int:
        return min(self.count - 1, max(0, int((y - self.min_y) / self.height)))

    def contains(self, point: Point2D) -> bool:
        """Return whether ``point`` lies inside the polygon."""
        if not self.min_y <= point.y <= self.max_y:
            return False
        inside = False
        for a, b in self.bands[self._band(point.y)]:
            if (a.y > point.y) != (b.y > point.y):
                x = a.x + (point.y - a.y) * (b.x - a.x) / (b.y - a.y)
                if point.x < x:
                    inside = not inside
        return inside


def polygons_overlap(a: Sequence[Point2D], b: Sequence[Point2D]) -> bool:
    """Return whether two polygons (or a polygon and a point) overlap."""
    if not a or not b:
        return False
    ax = [p.x for p in a]
    ay = [p.y for p in a]
    bx = [p.x for p in b]
    by = [p.y for p in b]
    if max(ax) < min(bx) or max(bx) < min(ax) or max(ay) < min(by) or max(by) < min(ay):
        return False
    if len(b) < 3:
        return any(point_in_polygon(p, a) for p in b)
    if any(point_in_polygon(p, b) for p in a) or any(point_in_polygon(p, a) for p in b):
        return True
    edges_b = list(zip(b, (*b[1:], b[0])))
    for p, q in zip(a, (*a[1:], a[0])):
        for r, s in edges_b:
            if _cross(p, q, r, s):
                return True
    return False


def _cross(p: Point2D, q: Point2D, r: Point2D, s: Point2D) -> bool:
    def side(u: Point2D, v: Point2D, w: Point2D) -> float:
        return (v.x - u.x) * (w.y - u.y) - (v.y - u.y) * (w.x - u.x)

    d1, d2 = side(r, s, p), side(r, s, q)
    d3, d4 = side(p, q, r), side(p, q, s)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)
