"""Humbucker frames: decorative plates round each humbucker, cut from sheet.

Two styles traced from the builder's drawing (``humbframes.dxf``):
``horns``, a frame whose ends sweep into a horn either side toward the
neck, its bridge side round; and ``hook``, its bass end cut in to a hook
and its treble end sweeping into one long horn toward the neck. The
drawing's lines were pen strokes (their outer edge is traced) and its
size arbitrary: it is scaled so its opening is the humbucker's, 70.5 mm
across the strings, and the opening itself is cut to the pickup's own
(``pickups.pickup_openings``, the pickguard's), not as drawn.

A frame's outline is a closed Catmull-Rom loop through its points, given
in the frame's own frame: ``a`` along the neck toward the bridge, ``c``
across it, the bass side negative, in millimetres, the opening centred
on the origin, the horns toward the neck (negative ``a``). Every
humbucker gets one, turned with the pickup, opened across the strings
with its route for seven and eight strings, mirrored for a left-handed
build and, where it does not fit with its horns toward the neck (or
when asked), turned round. Two screws hold it, on the pickup's long
axis past the ears; it has holes over the pickup's height screws, to
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

PickupFrameStyle = Literal["none", "horns", "hook"]
"""A humbucker frame's style: none, or one of the traced frames."""

PICKUP_FRAME_STYLES: tuple[str, ...] = ("none", "horns", "hook")

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
    points: Sequence[tuple[float, float]], placing: FramePlacing
) -> tuple[Point2D, ...]:
    """Return a frame's outline in the model through its points."""
    return tuple(
        closed_catmull_rom(
            [placing.to_model(a, c) for a, c in points], FRAME_SAMPLES_PER_SEGMENT
        )
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
    """

    position: str
    points: tuple[tuple[float, float], ...]
    placing: FramePlacing
    turned: bool
    plate: CoverPlate
    screw_spots: tuple[DrilledHole, ...]
    problem: str | None = None


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

    Its two screws sit past the pickup's ears, on its long axis where the
    frame has ``FRAME_SCREW_ROOM`` all round them there, else as near it
    as it has (see ``_screw_spot``); with no room, ``problem`` says so.
    """
    label = position.capitalize()
    outline = frame_outline(points, placing)
    local = [placing.to_axes(point) for point in outline]
    problem = None
    screws: list[Point2D] = []
    ear = EAR_REACH + placing.stretch / 2.0
    for side, sign in (("bass", -1.0), ("treble", 1.0)):
        spot = _screw_spot(local, sign, ear)
        if spot is None:
            problem = problem or (
                f"The {position} pickup's frame leaves no room for its screw past "
                f"the pickup's {side} ear: it needs {FRAME_SCREW_ROOM:g} mm of frame "
                "all round it there; widen it."
            )
            continue
        screws.append(placing.from_axes(*spot))
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


SCREW_SEARCH = 20
"""How far (mm) either side of the pickup's long axis a frame screw is
looked for, when there is no room on it."""


def _screw_spot(
    local: Sequence[tuple[float, float]], sign: float, ear: float
) -> tuple[float, float] | None:
    """Return where a frame screw goes on one side, or ``None``.

    Past the pickup's ear (``ear`` across, toward ``sign``) with
    ``FRAME_SCREW_ROOM`` of frame all round, as near the pickup's long
    axis as there is room — on it where the frame allows — in the middle
    of the stretch of the line out from the ear that has it.
    """
    polygon = [Point2D(a, c) for a, c in local]
    reach = max(sign * c for _, c in local)
    for step in range(SCREW_SEARCH + 1):
        best: tuple[float, tuple[float, float]] | None = None
        for a in (0.0,) if step == 0 else (float(step), -float(step)):
            # The stretch of the line out from the ear with room all round.
            room: list[float] = []
            c = ear + FRAME_SCREW_ROOM
            while c < reach:
                point = Point2D(a, sign * c)
                if (
                    point_in_polygon(point, polygon)
                    and _distance_to_outline(point, polygon) >= FRAME_SCREW_ROOM
                ):
                    room.append(c)
                elif room:
                    break
                c += 0.5
            if room and (best is None or room[-1] - room[0] > best[0]):
                best = (room[-1] - room[0], (a, sign * (room[0] + room[-1]) / 2.0))
        if best is not None:
            return best[1]
    return None


def _distance_to_outline(point: Point2D, polygon: Sequence[Point2D]) -> float:
    best = math.inf
    for a, b in zip(polygon, (*polygon[1:], polygon[0])):
        dx, dy = b.x - a.x, b.y - a.y
        squared = dx * dx + dy * dy
        t = 0.0
        if squared > 0.0:
            t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / squared
            t = max(0.0, min(1.0, t))
        best = min(best, math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy))
    return best


def frame_problem(
    frame: PickupFrame,
    body_outline: Sequence[Point2D],
    obstacles: Sequence[tuple[str, Sequence[Point2D]]],
) -> str | None:
    """Return why a frame does not fit, or ``None``.

    It must lie on the body, clear of every one of ``obstacles`` (named
    outlines: the neck, the bridge, other pickups' routes and frames, the
    controls on the top), with room for its screws.
    """
    if frame.problem:
        return frame.problem
    outline = frame.plate.outline
    if not all(point_in_polygon(point, body_outline) for point in outline):
        return f"The {frame.position} pickup's frame runs off the body."
    for name, polygon in obstacles:
        if polygons_overlap(outline, polygon):
            return f"The {frame.position} pickup's frame runs into {name}."
    return None


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
