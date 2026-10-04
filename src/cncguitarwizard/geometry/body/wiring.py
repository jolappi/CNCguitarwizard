"""Wire channels between the electronics cavities.

Every pickup route is wired to the controls, nearest first: a route joins
whichever cavity already wired is nearest (the controls, or a pickup
route wired before it), so pickups in a row chain to the controls as on a
Stratocaster or a Les Paul. The bridge's ground wire runs from the
controls to a tremolo's spring cavity (its claw), or else to the nearest
bridge cavity or hole.

A machine cutting from the top or the back leaves any channel open on
that face, so a channel is routed only where a pickguard hides it: a slot
``WIRE_CHANNEL_WIDTH`` wide from the top, between two top routes. Every
other way is a straight hole drilled by hand from one cavity into the
other (``WireHole``): the bit goes in through the cavity's open face, past
its far rim, and on through the wood. The hole's height and angle are
found so it leaves ``WIRE_SKIN`` of wood under the top and over the back,
``WIRE_WALL`` round every other cavity and hole, and opens into both
cavities; the shallowest that does is taken. Heights here are above the
back face (``0`` the back, the body's thickness the top).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, Point3D, point_in_polygon
from .hardware import TracedCavity

WIRE_HOLE_DIAMETER = 6.0
"""A pickup lead's hole, drilled by hand (a 1/4 in bit), in mm."""

GROUND_HOLE_DIAMETER = 3.0
"""The bridge ground wire's hole, in mm."""

WIRE_CHANNEL_WIDTH = 10.0
"""A channel routed from the top under a pickguard, in mm."""

WIRE_CHANNEL_DEPTH = 16.0
"""How deep such a channel is routed, at most, in mm (never deeper than
the routes it joins)."""

WIRE_SKIN = 3.0
"""Least wood a drilled hole leaves under the top and over the back, in mm."""

WIRE_WALL = 2.0
"""Least wood between a hole or channel and any cavity or hole it does not
join, in mm."""

WIRE_DRILL_REACH = 300.0
"""The longest hole a long (aircraft) bit drills, from the rim it passes
to where it breaks through, in mm."""

WIRE_STEEPEST = 60.0
"""The steepest hole drilled, degrees from level."""

_SAMPLE = 1.0
"""Spacing of the checks along a hole or a channel, in mm."""

_OPENING_SLACK = 1.0
"""How far a cover's opening may reach past the route under it, in mm."""

_SLOPE_STEP = 0.02
"""The slopes a hole is tried at (rise over run)."""


@dataclass(frozen=True, slots=True)
class WireSpace:
    """A cavity the wiring joins, or one it keeps clear of.

    Args:
        name: As the cavity is named (``"Neck pickup route"``).
        outline: Its plan outline.
        bottom: Height of its floor above the back face (``0`` for a
            cavity routed from the back).
        top: Height of its ceiling (the body's thickness for a cavity
            routed from the top).
        face: The face it opens onto, through which a hole can be drilled
            into the wood beyond it, or ``None`` for one that cannot be
            drilled from (a hole, the jack's bore).
        parts: Further outlines that belong to it: a rear cavity's cover
            recess and deeper steps, never in the way of its own wiring.
    """

    name: str
    outline: tuple[Point2D, ...]
    bottom: float
    top: float
    face: Literal["top", "back"] | None = None
    parts: tuple[tuple[Point2D, ...], ...] = ()

    def __post_init__(self) -> None:
        if len(self.outline) < 3:
            raise BodyGeometryError(f"{self.name} needs an outline.")
        if not (
            math.isfinite(self.bottom)
            and math.isfinite(self.top)
            and self.bottom < self.top
        ):
            raise BodyGeometryError(f"{self.name} needs a floor below its ceiling.")

    @property
    def label(self) -> str:
        """Return the name without ``route`` or ``cavity`` (``"Neck pickup"``)."""
        return self.name.removesuffix(" route").removesuffix(" cavity")


@dataclass(frozen=True, slots=True)
class WireHole:
    """A straight hole drilled by hand from one cavity into another.

    The bit goes in through ``face``, the open face of the cavity it is
    drilled from, and meets the wood at ``start`` on that cavity's wall; it
    breaks into the other cavity at ``end``. Heights are above the back
    face.

    Args:
        name: ``"Neck pickup wire hole"``, ``"Bridge ground hole"``.
        start: Where the bit meets the wood.
        end: Where it breaks into the other cavity.
        diameter: The bit's diameter.
        drilled_from: The cavity it is drilled from.
        into: The cavity it breaks into.
        face: The face the bit comes in through.

    Raises:
        BodyGeometryError: For a non-positive diameter or a hole of no
            length.
    """

    name: str
    start: Point3D
    end: Point3D
    diameter: float
    drilled_from: str
    into: str
    face: Literal["top", "back"]

    def __post_init__(self) -> None:
        values = (*_xyz(self.start), *_xyz(self.end), self.diameter)
        if not all(math.isfinite(value) for value in values) or self.diameter <= 0.0:
            raise BodyGeometryError(f"{self.name} must have a positive diameter.")
        if self.length <= 0.0:
            raise BodyGeometryError(f"{self.name} must have some length.")

    @property
    def length(self) -> float:
        """Return the hole's length through the wood."""
        return math.dist(_xyz(self.start), _xyz(self.end))

    @property
    def angle(self) -> float:
        """Return how steeply it runs, degrees from level."""
        run = math.hypot(self.end.x - self.start.x, self.end.y - self.start.y)
        return math.degrees(math.atan2(abs(self.end.z - self.start.z), run))

    def note(self) -> str:
        """Return how to drill it, for the program's notes."""
        way = "down" if self.face == "top" else "up"
        return (
            f"{self.name}: {self.diameter:g} mm, from the "
            f"{self.drilled_from.lower()} into the {self.into.lower()}, the bit "
            f"in through the {self.face} at {self.angle:.0f} degrees from level "
            f"and {way}ward, from X {self.start.x:.0f} Y {self.start.y:.0f} "
            f"(its axis {self.start.z:.0f} mm above the back) toward "
            f"X {self.end.x:.0f} Y {self.end.y:.0f}; {self.length:.0f} mm "
            "through the wood."
        )


@dataclass(frozen=True, slots=True)
class Wiring:
    """The wire channels and holes, and the ways left to the builder.

    Args:
        channels: Channels routed from the top, under the pickguard.
        holes: Holes drilled by hand.
        by_hand: The connections no straight hole fits, to be made by
            hand (a note each).
    """

    channels: tuple[TracedCavity, ...] = ()
    holes: tuple[WireHole, ...] = ()
    by_hand: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Link:
    """One way found between two cavities, and what it costs."""

    cost: float
    channel: TracedCavity | None = None
    hole: WireHole | None = None


def plan_wiring(
    thickness: float,
    outline: Sequence[Point2D],
    controls: WireSpace,
    pickups: Sequence[WireSpace],
    bridge: Sequence[WireSpace],
    obstacles: Sequence[WireSpace],
    *,
    covers: Sequence[tuple[Point2D, ...]] = (),
    openings: Sequence[tuple[Point2D, ...]] = (),
    top_at: Callable[[Point2D], float] | None = None,
    back_at: Callable[[Point2D], float] | None = None,
) -> Wiring:
    """Return the channels and holes wiring the pickups and the bridge.

    Args:
        thickness: The body's thickness.
        outline: The body's outline.
        controls: The cavity the pots are in.
        pickups: The pickup routes.
        bridge: The bridge's cavities and holes its ground wire can reach.
        obstacles: Every other cavity and hole; a space in ``pickups``,
            ``bridge`` or ``controls`` may be listed too, and is kept clear
            of except by its own wiring.
        covers: What hides a channel routed from the top (the pickguard).
        openings: The holes through those covers.
        top_at: The top's height at a point (lower over a carved top or an
            arm contour), the thickness if not given.
        back_at: The back's height at a point (above ``0`` in a belly
            cut), ``0`` if not given.
    """
    planner = _Planner(
        thickness,
        tuple(outline),
        (controls, *pickups, *bridge, *obstacles),
        tuple(covers),
        tuple(openings),
        top_at or (lambda point: thickness),
        back_at or (lambda point: 0.0),
    )
    channels: list[TracedCavity] = []
    holes: list[WireHole] = []
    by_hand: list[str] = []
    wired = [controls]
    waiting = list(pickups)
    while waiting:
        best: tuple[_Link, WireSpace] | None = None
        for pickup in waiting:
            for target in wired:
                link = planner.link(pickup, target, f"{pickup.label} wire")
                if link is not None and (best is None or link.cost < best[0].cost):
                    best = (link, pickup)
        if best is None:
            by_hand.extend(
                f"No straight hole joins the {pickup.name.lower()} to the "
                "wiring: make its lead's way by hand."
                for pickup in waiting
            )
            break
        link, pickup = best
        if link.channel is not None:
            channels.append(link.channel)
        if link.hole is not None:
            holes.append(link.hole)
        wired.append(pickup)
        waiting.remove(pickup)
    if bridge:
        grounds = [
            (target.face == "back", hole)
            for target in bridge
            if (hole := planner.hole(controls, target, "Bridge ground hole", True))
            is not None
        ]
        # A tremolo's spring cavity first (its claw takes the wire), else
        # the nearest.
        claws = [hole for claw, hole in grounds if claw]
        if grounds:
            holes.append(
                min(claws or [hole for _, hole in grounds], key=lambda h: h.length)
            )
        else:
            by_hand.append(
                "No straight hole joins the controls to the bridge: run the "
                "ground wire by hand."
            )
    return Wiring(tuple(channels), tuple(holes), tuple(by_hand))


class _Planner:
    """Finds the channel or hole between two cavities."""

    def __init__(
        self,
        thickness: float,
        outline: tuple[Point2D, ...],
        spaces: tuple[WireSpace, ...],
        covers: tuple[tuple[Point2D, ...], ...],
        openings: tuple[tuple[Point2D, ...], ...],
        top_at: Callable[[Point2D], float],
        back_at: Callable[[Point2D], float],
    ) -> None:
        self.thickness = thickness
        self.outline = outline
        self.spaces = spaces
        self.covers = covers
        self.openings = openings
        self.top_at = top_at
        self.back_at = back_at
        self._links: dict[tuple[int, int], _Link | None] = {}
        self._outline_edges = _edges(outline)
        self._bounds = {
            id(polygon): _bounds(polygon)
            for space in spaces
            for polygon in (space.outline, *space.parts)
        }

    def link(self, source: WireSpace, target: WireSpace, name: str) -> _Link | None:
        """Return a channel under the guard, else a hole, from source to target.

        Cavities that already meet need neither (cost ``0``).
        """
        key = (id(source), id(target))
        if key not in self._links:
            self._links[key] = self._link(source, target, name)
        return self._links[key]

    def _link(self, source: WireSpace, target: WireSpace, name: str) -> _Link | None:
        lines = _plan_lines(source, target)
        if not lines:
            return _Link(0.0)
        if source.face == "top" and target.face == "top" and self.covers:
            for start, end in lines:
                channel = self.channel(source, target, start, end, f"{name} channel")
                if channel is not None:
                    return _Link(math.dist(_xy(start), _xy(end)), channel=channel)
        hole = self.hole(source, target, f"{name} hole", False)
        return None if hole is None else _Link(hole.length, hole=hole)

    def channel(
        self,
        a: WireSpace,
        b: WireSpace,
        start: Point2D,
        end: Point2D,
        name: str,
    ) -> TracedCavity | None:
        """Return a channel routed from the top from ``a`` to ``b``, if hidden."""
        depth = min(
            WIRE_CHANNEL_DEPTH, self.thickness - a.bottom, self.thickness - b.bottom
        )
        if depth <= 0.0:
            return None
        ux, uy = _unit(start, end)
        reach = WIRE_CHANNEL_WIDTH / 2.0 + 1.0
        outline = _stadium(
            Point2D(start.x - ux * reach, start.y - uy * reach),
            Point2D(end.x + ux * reach, end.y + uy * reach),
            WIRE_CHANNEL_WIDTH / 2.0,
        )
        own = (a.outline, *a.parts, b.outline, *b.parts)
        for point in _dense(outline):
            # In (or by) the routes it joins: a cover's opening over a
            # pickup may reach a hair past the route.
            if any(
                point_in_polygon(point, polygon)
                or _distance_to_polygon(point, polygon) < _OPENING_SLACK
                for polygon in own
            ):
                continue
            if not point_in_polygon(point, self.outline):
                return None
            if not any(point_in_polygon(point, cover) for cover in self.covers) or any(
                point_in_polygon(point, opening) for opening in self.openings
            ):
                return None
        floor = self.thickness - depth
        x0, y0, x1, y1 = _bounds(outline)
        for space in self.spaces:
            if space is a or space is b or _inside_own(space, (a, b)):
                continue
            if space.top <= floor - WIRE_WALL:
                continue
            for polygon in (space.outline, *space.parts):
                px0, py0, px1, py1 = self._bounds[id(polygon)]
                if (
                    px1 < x0 - WIRE_WALL
                    or px0 > x1 + WIRE_WALL
                    or py1 < y0 - WIRE_WALL
                    or py0 > y1 + WIRE_WALL
                ):
                    continue
                if _polygons_near(outline, polygon, WIRE_WALL):
                    return None
        return TracedCavity(name, outline, depth)

    def hole(
        self, a: WireSpace, b: WireSpace, name: str, ground: bool
    ) -> WireHole | None:
        """Return the shortest drilled hole between ``a`` and ``b``, if any."""
        diameter = GROUND_HOLE_DIAMETER if ground else WIRE_HOLE_DIAMETER
        found: list[WireHole] = []
        for start, end in _plan_lines(a, b):
            for entry, other, p0, p1 in ((a, b, start, end), (b, a, end, start)):
                if entry.face is None:
                    continue
                hole = self._drilled(entry, other, p0, p1, diameter / 2.0, name)
                if hole is not None:
                    found.append(hole)
        return min(found, key=lambda hole: hole.length) if found else None

    def _drilled(
        self,
        entry: WireSpace,
        other: WireSpace,
        p0: Point2D,
        p1: Point2D,
        radius: float,
        name: str,
    ) -> WireHole | None:
        """Return the hole drilled from ``entry`` into ``other``, if one fits.

        ``p0`` lies on ``entry``'s wall, ``p1`` on ``other``'s, the hole
        between them in plan; its height at ``p0`` and its slope are found
        here. Of the holes that fit, the one nearest the floor of the top
        route it joins (where the leads lie), then the shallowest.
        """
        gap = math.dist(_xy(p0), _xy(p1))
        if gap <= 0.0:
            return None
        ux, uy = _unit(p0, p1)
        span = _span_behind(p0, ux, uy, entry.outline)
        if span is None:
            return None
        steps = max(2, math.ceil(gap / _SAMPLE))
        along = [gap * k / steps for k in range(steps + 1)]
        points = [Point2D(p0.x + ux * s, p0.y + uy * s) for s in along]
        if not point_in_polygon(p0, self.outline) or any(
            _segment_distance(p0, p1, c, d) < radius + WIRE_WALL
            for c, d in self._outline_edges
        ):
            return None
        # The faces over and under the way (a carve, a contour), every
        # other sample: the room under the top and over the back.
        under = [
            (s, self.top_at(point) - radius - WIRE_SKIN)
            for s, point in zip(along[::2], points[::2], strict=True)
        ]
        over = [
            (s, self.back_at(point) + radius + WIRE_SKIN)
            for s, point in zip(along[::2], points[::2], strict=True)
        ]
        rim = self.top_at(Point2D(p0.x - ux * span, p0.y - uy * span))
        # Where along the hole each other cavity or hole is in the way.
        blocks = self._blocks(p0, ux, uy, gap, radius, (entry, other))
        down = entry.face == "top"
        sign = -1.0 if down else 1.0
        steepest = math.tan(math.radians(WIRE_STEEPEST))
        best: tuple[tuple[float, float], float, float] | None = None
        for step in range(1, math.floor(steepest / _SLOPE_STEP) + 1):
            slope = step * _SLOPE_STEP
            if (span + gap) * math.hypot(1.0, slope) > WIRE_DRILL_REACH:
                break
            if down:
                # In past the far rim, out of the route above its floor.
                low = max(rim + radius - slope * span, entry.bottom + radius)
                high = math.inf
            else:
                low = entry.bottom + radius
                high = min(slope * span - radius, entry.top - radius)
            high = min(high, *(room - sign * slope * s for s, room in under))
            low = max(low, *(room - sign * slope * s for s, room in over))
            # Into the other cavity through its wall.
            low = max(low, other.bottom + radius - sign * slope * gap)
            high = min(high, other.top - radius - sign * slope * gap)
            z0 = _lowest_clear(low, high, blocks, slope, down, radius)
            if z0 is None:
                continue
            arrival = z0 + sign * slope * gap
            if down:
                key = (z0 - entry.bottom, slope)
            elif other.face == "top":
                key = (arrival - other.bottom, slope)
            else:
                key = (slope, z0)
            if best is None or key < best[0]:
                best = (key, z0, arrival)
        if best is None:
            return None
        _, z0, arrival = best
        return WireHole(
            name,
            Point3D(p0.x, p0.y, z0),
            Point3D(p1.x, p1.y, arrival),
            2.0 * radius,
            entry.name,
            other.name,
            "top" if down else "back",
        )

    def _blocks(
        self,
        p0: Point2D,
        ux: float,
        uy: float,
        gap: float,
        radius: float,
        own: tuple[WireSpace, WireSpace],
    ) -> list[tuple[float, float, WireSpace]]:
        """Return the stretches ``(from, to)`` of the way another space is near."""
        reach = radius + WIRE_WALL
        steps = max(2, math.ceil(gap / _SAMPLE))
        found: list[tuple[float, float, WireSpace]] = []
        lo_x, hi_x = min(p0.x, p0.x + ux * gap), max(p0.x, p0.x + ux * gap)
        lo_y, hi_y = min(p0.y, p0.y + uy * gap), max(p0.y, p0.y + uy * gap)
        for space in self.spaces:
            if any(space is joined for joined in own) or _inside_own(space, own):
                continue
            for polygon in (space.outline, *space.parts):
                x0, y0, x1, y1 = self._bounds[id(polygon)]
                if (
                    x1 < lo_x - reach
                    or x0 > hi_x + reach
                    or y1 < lo_y - reach
                    or y0 > hi_y + reach
                ):
                    continue
                near = []
                for k in range(steps + 1):
                    point = Point2D(
                        p0.x + ux * gap * k / steps, p0.y + uy * gap * k / steps
                    )
                    if (
                        x0 - reach <= point.x <= x1 + reach
                        and y0 - reach <= point.y <= y1 + reach
                        and _near(point, polygon, reach)
                    ):
                        near.append(gap * k / steps)
                if near:
                    found.append(
                        (near[0] - _SAMPLE, near[-1] + _SAMPLE, space),
                    )
        return found


def _lowest_clear(
    low: float,
    high: float,
    blocks: list[tuple[float, float, WireSpace]],
    slope: float,
    down: bool,
    radius: float,
) -> float | None:
    """Return the lowest start height in ``[low, high]`` clear of ``blocks``."""
    if low > high:
        return None
    # The start heights at which the hole meets each space in the way.
    banned: list[tuple[float, float]] = []
    for s1, s2, space in blocks:
        below = space.bottom - radius - WIRE_WALL
        above = space.top + radius + WIRE_WALL
        if down:
            banned.append((below + slope * s1, above + slope * s2))
        else:
            banned.append((below - slope * s2, above - slope * s1))
    candidate = low
    moved = True
    while moved and candidate <= high:
        moved = False
        for start, end in banned:
            if start < candidate < end:
                candidate, moved = end, True
    return candidate if candidate <= high else None


def _plan_lines(a: WireSpace, b: WireSpace) -> list[tuple[Point2D, Point2D]]:
    """Return ways in plan from ``a``'s wall to ``b``'s: centre to centre, and
    the shortest. Empty if the two already meet."""
    lines: list[tuple[Point2D, Point2D]] = []
    centre_a, centre_b = _centroid(a.outline), _centroid(b.outline)
    if point_in_polygon(centre_a, a.outline) and point_in_polygon(centre_b, b.outline):
        out = _last_exit(centre_a, centre_b, a.outline)
        into = _first_entry(centre_a, centre_b, b.outline)
        if out is not None and into is not None:
            if math.dist(_xy(centre_a), _xy(into)) <= math.dist(
                _xy(centre_a), _xy(out)
            ):
                return []
            lines.append((out, into))
    closest = _closest_points(a.outline, b.outline)
    if closest is None:
        return []
    if not lines or math.dist(_xy(closest[0]), _xy(closest[1])) < math.dist(
        _xy(lines[0][0]), _xy(lines[0][1])
    ):
        lines.append(closest)
    return lines


def _closest_points(
    a: Sequence[Point2D], b: Sequence[Point2D]
) -> tuple[Point2D, Point2D] | None:
    """Return the nearest pair of points on two outlines (``None`` if they meet)."""
    if _crosses(a, b) or point_in_polygon(a[0], b) or point_in_polygon(b[0], a):
        return None
    best: tuple[float, Point2D, Point2D] | None = None
    for first, second, swap in ((a, b, False), (b, a, True)):
        for point in first:
            for c, d in _edges(second):
                foot = _foot(point, c, d)
                distance = math.dist(_xy(point), _xy(foot))
                if best is None or distance < best[0]:
                    best = (distance, foot, point) if swap else (distance, point, foot)
    if best is None or best[0] < 1e-6:
        return None
    return best[1], best[2]


def _last_exit(
    origin: Point2D, toward: Point2D, polygon: Sequence[Point2D]
) -> Point2D | None:
    """Return where the way from ``origin`` to ``toward`` last leaves ``polygon``."""
    hits = _crossings(origin, toward, polygon)
    return hits[-1] if hits else None


def _first_entry(
    origin: Point2D, toward: Point2D, polygon: Sequence[Point2D]
) -> Point2D | None:
    """Return where the way from ``origin`` to ``toward`` first enters ``polygon``."""
    hits = _crossings(origin, toward, polygon)
    return hits[0] if hits else None


def _crossings(
    origin: Point2D, toward: Point2D, polygon: Sequence[Point2D]
) -> list[Point2D]:
    """Return where the segment crosses the polygon's sides, in order."""
    found: list[tuple[float, Point2D]] = []
    dx, dy = toward.x - origin.x, toward.y - origin.y
    for c, d in _edges(polygon):
        ex, ey = d.x - c.x, d.y - c.y
        denominator = dx * ey - dy * ex
        if abs(denominator) < 1e-12:
            continue
        t = ((c.x - origin.x) * ey - (c.y - origin.y) * ex) / denominator
        u = ((c.x - origin.x) * dy - (c.y - origin.y) * dx) / denominator
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            found.append((t, Point2D(origin.x + dx * t, origin.y + dy * t)))
    return [point for _, point in sorted(found, key=lambda item: item[0])]


def _span_behind(
    point: Point2D, ux: float, uy: float, polygon: Sequence[Point2D]
) -> float | None:
    """Return how far the cavity reaches back from ``point`` on its wall."""
    far = Point2D(point.x - ux * 10000.0, point.y - uy * 10000.0)
    distances = [
        math.dist(_xy(point), _xy(hit))
        for hit in _crossings(point, far, polygon)
        if math.dist(_xy(point), _xy(hit)) > 1e-6
    ]
    if not distances:
        return None
    span = min(distances)
    # Back from the wall must be the cavity's inside.
    middle = Point2D(point.x - ux * span / 2.0, point.y - uy * span / 2.0)
    return span if point_in_polygon(middle, polygon) else None


def _inside_own(space: WireSpace, own: Sequence[WireSpace]) -> bool:
    """Whether a space lies within one of the joined cavities (a pot's hole)."""
    centre = _centroid(space.outline)
    return any(
        point_in_polygon(centre, polygon)
        for joined in own
        for polygon in (joined.outline, *joined.parts)
    )


def _near(point: Point2D, polygon: Sequence[Point2D], reach: float) -> bool:
    return point_in_polygon(point, polygon) or (
        _distance_to_polygon(point, polygon) < reach
    )


def _polygons_near(
    first: Sequence[Point2D], second: Sequence[Point2D], reach: float
) -> bool:
    """Whether two outlines overlap or come within ``reach`` of each other."""
    if _crosses(first, second):
        return True
    if point_in_polygon(first[0], second) or point_in_polygon(second[0], first):
        return True
    return any(_distance_to_polygon(p, second) < reach for p in first) or any(
        _distance_to_polygon(p, first) < reach for p in second
    )


def _crosses(first: Sequence[Point2D], second: Sequence[Point2D]) -> bool:
    for a, b in _edges(first):
        for c, d in _edges(second):
            if _segments_cross(a, b, c, d):
                return True
    return False


def _segments_cross(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> bool:
    def turn(p: Point2D, q: Point2D, r: Point2D) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    return (turn(a, b, c) > 0.0) != (turn(a, b, d) > 0.0) and (turn(c, d, a) > 0.0) != (
        turn(c, d, b) > 0.0
    )


def _segment_distance(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> float:
    """Return how close two segments come (``0`` where they cross)."""
    if _segments_cross(a, b, c, d):
        return 0.0
    return min(
        math.dist(_xy(a), _xy(_foot(a, c, d))),
        math.dist(_xy(b), _xy(_foot(b, c, d))),
        math.dist(_xy(c), _xy(_foot(c, a, b))),
        math.dist(_xy(d), _xy(_foot(d, a, b))),
    )


def _distance_to_polygon(point: Point2D, polygon: Sequence[Point2D]) -> float:
    return min(
        math.dist(_xy(point), _xy(_foot(point, c, d))) for c, d in _edges(polygon)
    )


def _foot(point: Point2D, a: Point2D, b: Point2D) -> Point2D:
    """Return the nearest point to ``point`` on the segment ``a``–``b``."""
    dx, dy = b.x - a.x, b.y - a.y
    length = dx * dx + dy * dy
    t = 0.0 if length == 0.0 else ((point.x - a.x) * dx + (point.y - a.y) * dy) / length
    t = max(0.0, min(1.0, t))
    return Point2D(a.x + dx * t, a.y + dy * t)


def _bounds(polygon: Sequence[Point2D]) -> tuple[float, float, float, float]:
    xs = [point.x for point in polygon]
    ys = [point.y for point in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _edges(polygon: Sequence[Point2D]) -> list[tuple[Point2D, Point2D]]:
    return list(zip(polygon, (*polygon[1:], polygon[0]), strict=True))


def _centroid(polygon: Sequence[Point2D]) -> Point2D:
    """Return the area centroid (the vertices' mean for a degenerate one)."""
    area = cx = cy = 0.0
    for a, b in _edges(polygon):
        cross = a.x * b.y - b.x * a.y
        area += cross
        cx += (a.x + b.x) * cross
        cy += (a.y + b.y) * cross
    if abs(area) < 1e-9:
        return Point2D(
            sum(p.x for p in polygon) / len(polygon),
            sum(p.y for p in polygon) / len(polygon),
        )
    return Point2D(cx / (3.0 * area), cy / (3.0 * area))


def _stadium(start: Point2D, end: Point2D, radius: float) -> tuple[Point2D, ...]:
    """Return a slot's outline: two half circles joined, counter-clockwise."""
    ux, uy = _unit(start, end)
    heading = math.atan2(uy, ux)
    points: list[Point2D] = []
    for centre, offset in ((end, -math.pi / 2.0), (start, math.pi / 2.0)):
        for k in range(9):
            angle = heading + offset + math.pi * k / 8.0
            points.append(
                Point2D(
                    centre.x + radius * math.cos(angle),
                    centre.y + radius * math.sin(angle),
                )
            )
    return tuple(points)


def _dense(polygon: Sequence[Point2D]) -> list[Point2D]:
    """Return the outline's points with more along its long sides."""
    points: list[Point2D] = []
    for a, b in _edges(polygon):
        steps = max(1, math.ceil(math.dist(_xy(a), _xy(b)) / _SAMPLE))
        points.extend(
            Point2D(a.x + (b.x - a.x) * k / steps, a.y + (b.y - a.y) * k / steps)
            for k in range(steps)
        )
    return points


def _unit(start: Point2D, end: Point2D) -> tuple[float, float]:
    length = math.dist(_xy(start), _xy(end))
    return (end.x - start.x) / length, (end.y - start.y) / length


def _xy(point: Point2D) -> tuple[float, float]:
    return point.x, point.y


def _xyz(point: Point3D) -> tuple[float, float, float]:
    return point.x, point.y, point.z
