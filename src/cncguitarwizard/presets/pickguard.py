"""A pickguard (scratchplate) cut from sheet, shaped to the body and pickups.

The guard is a closed Catmull-Rom outline through control points, like a
drawn body. Left to itself (``automatic_points``) it lies ``margin``
inside the body's outline from the neck, where it leaves a notch, to the
bridge, where it runs on a little either side of it: round the shorter
horn, but on the longer horn's side straight past the pickups. When the
controls sit in the guard (the ``pickguard`` control layout) it runs on
past the bridge on the controls' side. Its points can then be moved by
hand (``YourDesignShape.pickguard_points``).

The guard gets a rectangular opening over every pickup (the pickup's own
size, ``pickups.pickup_openings``), a hole for every pot and the
pickup selector's bushing under it, a pickguard layout's blade-switch
slot, and screws round its edge (``SCREW_INSET`` in, about
``SCREW_PITCH`` apart, clear of the openings) with a shallow spot in the
body under each.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from ..cam.planar import offset_polygon
from ..geometry.body import Cavity, CoverPlate, DrilledHole, TracedCavity
from ..geometry.exceptions import BodyGeometryError
from ..geometry.primitives import Point2D, closed_catmull_rom, point_in_polygon

PICKUP_MARGIN = 3.0
"""Least guard left past the last pickup's route, in mm."""

PICKUP_HUG = 8.0
"""How far past the pickups' ends the guard's bass-side edge runs, in mm."""

HUG_BLEND = 40.0
"""Over how much of the neck the bass-side edge curves in to the pickups, in mm."""

SCREW_INSET = 4.5
"""How far in from the guard's edge its screws sit, in mm."""

SCREW_PITCH = 60.0
"""About how far apart the guard's screws are, along its edge, in mm."""

BRIDGE_CLEARANCE = 1.0
"""Gap between the guard and the bridge's routes and holes, in mm: the guard's
edge sits in the few millimetres between the bridge pickup and the bridge."""

SADDLE_REACH = 15.0
"""How far a bridge's plate and saddles reach ahead of the scale line, in mm:
the guard stops this far short of it on a bridge with no routes (a
hardtail, a Tune-o-matic)."""

CONTROLS_MARGIN = 12.0
"""How far the guard runs past a pickguard control cavity, in mm."""

POINT_SPACING = 22.0
"""About how far apart an automatic guard's control points are, in mm."""

NECK_WRAP = 0.65
"""How much of the neck pocket's length the guard reaches forward beside it."""

NECK_CLEARANCE = 0.5
"""Gap between the guard's notch and the neck pocket's sides, in mm."""

NECK_PASS = 20.0
"""How far past the neck pocket's side the guard reaches on the longer
horn's side when there are no pickups to run past, in mm."""

BRIDGE_WRAP = 12.0
"""How far past the bridge's front the guard runs on either side of it, in mm."""

DRAWN_BRIDGE_STEP = 8.0
"""About how far apart the points stepping a drawn guard round the bridge
are, in mm, so its spline keeps to the box's edges."""

TRUSS_ROD_CLEARANCE = 3.5
"""Gap the guard is stepped back round the truss rod's access notch, in mm
(its spline rounds the corners in by a millimetre or two)."""

DRAWN_BRIDGE_CLEARANCE = 3.0
"""Gap a drawn guard is stepped back to round the bridge, in mm: more than
``BRIDGE_CLEARANCE``, as its corners round in toward the bridge."""

WING_REACH = 100.0
"""How far past the bridge's front the guard runs out along a V's shorter
wing, in mm."""

TAIL_ROUND = 30.0
"""Over how much of its length a style's tail past the bridge rounds off
at its end, in mm."""

HORN_DIFFERENCE = 5.0
"""How much further one horn must reach than the other to count as the
longer, in mm."""

SAMPLES_PER_SEGMENT = 8
"""Outline samples per span between two control points."""


@dataclass(frozen=True, slots=True)
class PickguardStyle:
    """How an automatic guard is drawn on the longer horn's side and past
    the bridge.

    Args:
        long_side_wrap: How far forward beside the neck the guard reaches
            on the longer horn's side, in mm.
        waist: How far that side curves in between the first and last
            pickups, in mm.
        flare: How far that side flares out toward the bridge, in mm.
        early_flare: Whether the flare runs from the first pickup's end to
            the last pickup's centre (a Stratocaster's) rather than from
            the last pickup's centre to the guard's end.
        tail: How far past the bridge's front the shorter horn's side runs,
            in mm (a Stratocaster's controls section).
    """

    long_side_wrap: float
    waist: float
    flare: float
    early_flare: bool
    tail: float


PickguardStyleName = Literal["stratocaster", "superstrat"]
"""An automatic guard's style (see ``PICKGUARD_STYLES``)."""

PICKGUARD_STYLES: dict[str, PickguardStyle] = {
    # Measured off a Stratocaster's HH guard: a tongue beside the neck,
    # the edge widening steadily to the bridge pickup, a long tail past
    # the bridge on the treble side.
    "stratocaster": PickguardStyle(
        long_side_wrap=34.0, waist=0.0, flare=25.0, early_flare=True, tail=55.0
    ),
    # Drawn in the body editor: close round the pickups with a waist
    # between them, flaring out only toward the bridge.
    "superstrat": PickguardStyle(
        long_side_wrap=10.0, waist=5.0, flare=9.0, early_flare=False, tail=12.0
    ),
}
"""The automatic guard's styles, by name."""


@dataclass(frozen=True, slots=True)
class Pickguard:
    """A pickguard: its plate, its screws' spots in the body, its points.

    Args:
        plate: The guard as a sheet cover on the top face.
        screw_spots: The body's shallow spots under its screws.
        control_points: The points its outline runs through, model frame.
        automatic: Whether the points were laid out automatically.
    """

    plate: CoverPlate
    screw_spots: tuple[DrilledHole, ...]
    control_points: tuple[Point2D, ...]
    automatic: bool


def automatic_points(
    outline: Sequence[Point2D],
    heel_end: float,
    margin: float,
    bridge_areas: Sequence[Sequence[Point2D]],
    controls_region: Sequence[Point2D] | None,
    pickups: Sequence[Sequence[Point2D]] = (),
    neck_pocket: Sequence[Point2D] = (),
    bass_sign: float = 0.0,
    style: PickguardStyle = PICKGUARD_STYLES["stratocaster"],
) -> tuple[Point2D, ...]:
    """Return an automatic guard's control points, in ``style``.

    The body's outline is taken ``margin`` in, and the guard laid out in
    stations across the neck from the neck pocket's end to the bridge:

    - Beside the neck there is a notch the neck sits in,
      ``NECK_CLEARANCE`` round the ``neck_pocket``.
    - On the longer horn's side (the one reaching further toward the
      nut) the guard does not follow the horn: its edge runs
      ``PICKUP_HUG`` past the ``pickups`` (``NECK_PASS`` past the pocket
      with none), curving in by the style's ``waist`` between the first
      and last pickups and flaring out by its ``flare`` toward the bridge,
      and its ``long_side_wrap`` forward beside the neck.
    - On the shorter horn's side it follows the body's edge: round the
      horn, when a cutaway parts it from the body beside the neck, and
      back down the cutaway to the notch; with no cutaway it reaches
      forward beside the neck, ``NECK_WRAP`` of the pocket's length.
    - On the bass side (``bass_sign``), if that is the shorter horn's,
      the edge curves in to ``PICKUP_HUG`` past the pickups over
      ``HUG_BLEND``.
    - It stops ``BRIDGE_CLEARANCE`` short of the bridge (``bridge_areas``:
      its routes and holes) — or, with less room than ``PICKUP_MARGIN``
      past the last pickup too, halfway between the two — and reaches
      ``BRIDGE_WRAP`` on past its front either side of it, the shorter
      horn's side the style's ``tail``. With
      ``controls_region`` (a pickguard control cavity) the controls' side
      runs on to ``CONTROLS_MARGIN`` past it, and along it reaches out
      that far past it too (as far as the body lets it).

    Raises:
        BodyGeometryError: When nothing of the body is left for a guard.
    """
    inset = offset_polygon(outline, margin, inward=True)
    if len(inset) < 3:
        raise BodyGeometryError("The body is too small for a pickguard.")
    bridge_points = [p for area in bridge_areas for p in area]
    bridge_front = (
        min(p.x for p in bridge_points) - BRIDGE_CLEARANCE
        if bridge_points
        else max(p.x for p in inset)
    )
    pickup_points = [p for route in pickups for p in route]
    if pickup_points and bridge_points:
        last_pickup = max(p.x for p in pickup_points)
        if bridge_front < last_pickup + PICKUP_MARGIN:
            # Too little room for both gaps: halfway between the bridge
            # pickup and the bridge (into the pickup, if they overlap).
            bridge_front = max(
                bridge_front, (last_pickup + min(p.x for p in bridge_points)) / 2.0
            )
    elif pickup_points:
        bridge_front = max(
            bridge_front, max(p.x for p in pickup_points) + PICKUP_MARGIN
        )
    sides = (-1.0, 1.0)
    # Beside the bridge, either side of it, the guard runs on a little:
    # twice the clearance off it, as the spline rounds the inner corner
    # in toward the bridge by about as much.
    beside_bridge = {
        side: max((side * p.y for p in bridge_points), default=0.0)
        + 2.0 * BRIDGE_CLEARANCE
        for side in sides
    }
    wide_bridge = any(abs(p.y) > BRIDGE_WRAP for p in bridge_points)
    side_end = {
        side: bridge_front + (BRIDGE_WRAP if wide_bridge else 0.0) for side in sides
    }
    long_side, wings = _longer_horn_side(outline) if neck_pocket else (0.0, False)
    if long_side and wings:
        # Horns that are wings past the bridge (a V's): the guard runs out
        # along the shorter one, WING_REACH past the bridge.
        side_end[-long_side] = bridge_front + WING_REACH
    elif long_side and wide_bridge:
        side_end[-long_side] = bridge_front + max(BRIDGE_WRAP, style.tail)
    keep_side = 0.0
    keep_from = keep_to = keep_out = 0.0
    if controls_region:
        ys = [p.y for p in controls_region]
        keep_side = 1.0 if sum(ys) / len(ys) >= 0.0 else -1.0
        side_end[keep_side] = max(
            side_end[keep_side], max(p.x for p in controls_region) + CONTROLS_MARGIN
        )
        # Along the controls the guard reaches out past them, as far as
        # the body lets it.
        keep_from = min(p.x for p in controls_region) - CONTROLS_MARGIN
        keep_to = max(p.x for p in controls_region) + CONTROLS_MARGIN
        keep_out = max(keep_side * y for y in ys) + CONTROLS_MARGIN
    notch = {
        side: max((side * p.y for p in neck_pocket), default=0.0) + NECK_CLEARANCE
        for side in sides
    }
    reach = {
        side: max(side * p.y for p in pickup_points) + PICKUP_HUG
        if pickup_points
        else notch[side] + NECK_PASS
        for side in sides
    }
    step = 2.0
    stations = _stations(inset, heel_end + 0.5, bridge_front, step)
    # A shorter horn parted from the body by a cutaway is followed round.
    walk_from: dict[float, float] = {}
    for side in sides:
        if side != long_side and neck_pocket and stations and stations[0][2][side]:
            walk_from[side] = next(
                (x for x, _, outer in stations if not outer[side]), stations[-1][0]
            )
    hug_side = 0.0
    if pickup_points and bass_sign and math.copysign(1.0, bass_sign) != long_side:
        hug_side = math.copysign(1.0, bass_sign)
    hug_from = min((p.x for p in pickup_points), default=math.inf) - PICKUP_HUG
    hug_start = max(hug_from - HUG_BLEND, walk_from.get(hug_side, -math.inf))

    # The longer horn's side curves in between the pickups and flares out
    # toward the bridge, as the style has it.
    centres = sorted(
        (min(p.x for p in route) + max(p.x for p in route)) / 2.0
        for route in pickups
        if route
    )
    waist_at = (centres[0] + centres[-1]) / 2.0 if centres else 0.0
    waist = style.waist if len(centres) > 1 else 0.0
    flare_end = side_end[long_side] if long_side else bridge_front
    first_end = min(
        (max(p.x for p in route) for route in pickups if route), default=0.0
    )

    def shape(x: float) -> float:
        if not centres:
            return 0.0
        if style.early_flare:
            flare = style.flare * _eased(x, first_end, centres[-1])
        else:
            flare = style.flare * _eased(x, centres[-1], flare_end)
        if x <= waist_at:
            return flare - waist * _eased(x, heel_end, waist_at)
        if x <= centres[-1]:
            return flare - waist * (1.0 - _eased(x, waist_at, centres[-1]))
        return flare

    def bound(side: float, x: float, edge: float) -> float:
        # How far out (side * y) the guard reaches at x on one side, where
        # the inset body reaches ``edge``.
        out = edge
        if side == long_side and not (side == keep_side and x > bridge_front):
            out = min(edge, reach[side] + shape(x))
        elif side == hug_side:
            ease = _eased(x, hug_start, max(hug_from, hug_start + HUG_BLEND / 2))
            out = min(edge, edge + (reach[side] - edge) * ease)
        if side == keep_side and keep_from <= x <= keep_to:
            out = max(out, min(edge, keep_out))
        return out

    lows: list[Point2D] = []
    highs: list[Point2D] = []
    for x, (lo, hi), _ in stations:
        lo, hi = -bound(-1.0, x, -lo), bound(1.0, x, hi)
        if hi - lo > 1.0:
            if x >= walk_from.get(-1.0, -math.inf):
                lows.append(Point2D(x, lo))
            if x >= walk_from.get(1.0, -math.inf):
                highs.append(Point2D(x, hi))
    if len(lows) < 3 or len(highs) < 3:
        raise BodyGeometryError("The body has no room for a pickguard.")
    # Past the bridge's front, either side of it: at each station how far
    # out (side * y) the guard's inner and outer edges are — the inner one
    # beside the bridge, or a wing's inner edge where that lies further out.
    strips: dict[float, list[tuple[float, float, float]]] = {}
    for side in sides:
        strips[side] = []
        x = bridge_front + step
        while x <= side_end[side]:
            spans = [
                (min(side * lo, side * hi), max(side * lo, side * hi))
                for lo, hi in _spans(inset, x)
            ]
            if not spans:
                break
            near, far = max(spans, key=lambda span: span[1])
            inner = max(beside_bridge[side], near)
            outer = bound(side, x, far)
            if outer - inner < 1.0:
                break
            strips[side].append((x, inner, outer))
            x += step
        tail = side_end[side] > bridge_front + BRIDGE_WRAP
        if side != keep_side and tail:
            strips[side] = _rounded_tail(strips[side])
    fronts = {
        side: _front(
            inset,
            side,
            lows if side < 0 else highs,
            heel_end,
            notch[side],
            walk_from.get(side),
            style.long_side_wrap
            if side == long_side
            else NECK_WRAP * _length(neck_pocket),
            bound,
            step,
        )
        if neck_pocket
        else []
        for side in sides
    }
    return _resampled_paths(
        _loop(
            fronts,
            lows,
            highs,
            strips,
            bridge_front,
            heel_end,
            notch,
        ),
        POINT_SPACING,
    )


def _rounded_tail(
    strip: Sequence[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """Return a tail's stations with its outer edge rounded in at its end.

    Each station is its ``x`` and how far out its inner and outer edges
    are. Over its last ``TAIL_ROUND`` (at most half its length) the outer
    edge comes in toward the inner along a quarter ellipse, as a
    Stratocaster guard's tail does.
    """
    if len(strip) < 3:
        return list(strip)
    start, end = strip[0][0], strip[-1][0]
    radius = min(TAIL_ROUND, (end - start) / 2.0)
    rounded = []
    for x, inner, outer in strip:
        t = (x - (end - radius)) / radius
        if t > 0.0:
            keep = max(math.sqrt(max(0.0, 1.0 - t * t)), 0.1)
            outer = inner + (outer - inner) * keep
        rounded.append((x, inner, outer))
    return rounded


def _stations(
    inset: Sequence[Point2D], start: float, stop: float, step: float
) -> list[tuple[float, tuple[float, float], dict[float, bool]]]:
    """Return the guard's stations across the neck from ``start`` to ``stop``.

    Each is its ``x``, the stretch of body across it there (the one over
    the centreline, else the longest) and, for each side, whether more
    body lies further out on that side (a horn parted by a cutaway).
    """
    stations = []
    x = start
    while x <= stop:
        spans = _spans(inset, x)
        if spans:
            middle = [span for span in spans if span[0] < 0.0 < span[1]]
            lo, hi = middle[0] if middle else max(spans, key=lambda s: s[1] - s[0])
            outer = {
                -1.0: any(span[1] < lo for span in spans),
                1.0: any(span[0] > hi for span in spans),
            }
            stations.append((x, (lo, hi), outer))
        x += step
    return stations


def _front(
    inset: Sequence[Point2D],
    side: float,
    columns: Sequence[Point2D],
    heel_end: float,
    notch: float,
    walk_from: float | None,
    wrap: float,
    bound: Callable[[float, float, float], float],
    step: float,
) -> list[Point2D]:
    """Return one side's edge forward of its stations, from the neck's notch.

    With ``walk_from`` it follows the body round the horn and back down
    the cutaway to the notch; otherwise it reaches ``wrap`` forward
    beside the neck while there is room past the notch.
    """
    if walk_from is not None:
        walked = _walk(inset, columns[0], side, notch)
        if walked is not None:
            return list(reversed(walked[1:]))
    beside: list[Point2D] = []
    x = heel_end - step / 2.0
    while x > heel_end - wrap:
        spans = [s for s in _spans(inset, x) if s[0] < 0.0 < s[1]]
        if not spans:
            break
        outer = bound(side, x, max(side * spans[0][0], side * spans[0][1]))
        if outer < notch + 2.0:
            break
        beside.append(Point2D(x, side * outer))
        x -= step
    front = beside[-1].x if beside else heel_end
    return [Point2D(front, side * notch), *reversed(beside)]


def _walk(
    inset: Sequence[Point2D], start: Point2D, side: float, notch: float
) -> list[Point2D] | None:
    """Return the body's edge from ``start`` toward the nut to the notch line.

    It runs round the horn and back down the cutaway until it comes to
    the notch's side (``side * y == notch``); ``None`` if it never does.
    """
    count = len(inset)
    nearest = min(
        (
            index
            for index in range(count)
            if (inset[index].x - start.x) * (inset[(index + 1) % count].x - start.x)
            <= 0.0
        ),
        key=lambda index: abs(
            _y_at(inset[index], inset[(index + 1) % count], start.x) - start.y
        ),
        default=None,
    )
    if nearest is None:
        return None
    a, b = inset[nearest], inset[(nearest + 1) % count]
    index, direction = (nearest, -1) if a.x < b.x else (nearest + 1, 1)
    walked = [start]
    for _ in range(count):
        point = inset[index % count]
        previous = walked[-1]
        if side * point.y <= notch:
            t = (side * previous.y - notch) / (side * previous.y - side * point.y)
            walked.append(
                Point2D(previous.x + (point.x - previous.x) * t, side * notch)
            )
            return walked
        walked.append(point)
        index += direction
    return None


def _y_at(a: Point2D, b: Point2D, x: float) -> float:
    """Return the y where the segment ``a``-``b`` crosses ``x``."""
    if b.x == a.x:
        return a.y
    return a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x)


def _length(points: Sequence[Point2D]) -> float:
    """Return how far ``points`` stretch along the neck."""
    return max(p.x for p in points) - min(p.x for p in points)


def _loop(
    fronts: dict[float, list[Point2D]],
    lows: Sequence[Point2D],
    highs: Sequence[Point2D],
    strips: dict[float, list[tuple[float, float, float]]],
    bridge_front: float,
    heel_end: float,
    notch: dict[float, float],
) -> list[list[Point2D]]:
    """Return the guard's edge as paths, each ending where the next starts.

    Past the bridge's front each side's ``strips`` (stations: ``x`` and
    how far out the inner and outer edges are) run out along their outer
    edge and back along their inner one. Its corners — round the neck's
    notch and the bridge's — end paths, so they stay control points.
    """

    def outer(side: float) -> list[Point2D]:
        return [Point2D(x, side * far) for x, _, far in strips[side]]

    def inner(side: float) -> list[Point2D]:
        # From the bridge's front out to the strip's end.
        stations = strips[side]
        if not stations:
            return []
        return [
            Point2D(bridge_front, side * stations[0][1]),
            *(Point2D(x, side * near) for x, near, _ in stations),
        ]

    lo_curve = [*fronts[-1.0][1:], *lows, *outer(-1.0)]
    hi_curve = [*fronts[1.0][1:], *highs, *outer(1.0)]
    lo_inner, hi_inner = inner(-1.0), inner(1.0)
    paths: list[list[Point2D]] = [lo_curve]
    if lo_inner:
        paths += [[lo_curve[-1], lo_inner[-1]], list(reversed(lo_inner))]
    across_from = lo_inner[0] if lo_inner else lo_curve[-1]
    across_to = hi_inner[0] if hi_inner else hi_curve[-1]
    paths.append([across_from, across_to])
    if hi_inner:
        paths += [hi_inner, [hi_inner[-1], hi_curve[-1]]]
    paths.append(list(reversed(hi_curve)))
    if fronts[1.0] and fronts[-1.0]:
        paths.append(
            [
                hi_curve[0],
                fronts[1.0][0],
                Point2D(heel_end, notch[1.0]),
                Point2D(heel_end, -notch[-1.0]),
                fronts[-1.0][0],
                lo_curve[0],
            ]
        )
    else:
        paths.append([hi_curve[0], lo_curve[0]])
    return _cornered(paths)


def _cornered(paths: Sequence[Sequence[Point2D]]) -> list[list[Point2D]]:
    """Return ``paths`` with every straight corner path split at its points.

    Two-point paths and the notch's run stay corner to corner; zero-length
    pieces are dropped.
    """
    result: list[list[Point2D]] = []
    for path in paths:
        pieces = (
            [list(path)]
            if len(path) > 6
            else [[a, b] for a, b in zip(path, path[1:], strict=False)]
        )
        for piece in pieces:
            length = sum(
                math.hypot(b.x - a.x, b.y - a.y)
                for a, b in zip(piece, piece[1:], strict=False)
            )
            if length > 0.5:
                result.append(piece)
    return result


def _longer_horn_side(outline: Sequence[Point2D]) -> tuple[float, bool]:
    """Return the side (+1 or -1) of the longer horn, and whether horns are wings.

    The longer horn reaches further toward the nut. When neither does by
    ``HORN_DIFFERENCE``, the horns may be wings reaching away from the neck
    past the bridge, as a V's are: then the longer one reaches further that
    way (and the second value is true). Returns 0 for the side when neither
    is longer either way.
    """
    sides = (-1.0, 1.0)
    toward = {
        side: min((p.x for p in outline if side * p.y > 0.0), default=math.inf)
        for side in sides
    }
    if abs(toward[-1.0] - toward[1.0]) >= HORN_DIFFERENCE:
        return (-1.0 if toward[-1.0] < toward[1.0] else 1.0), False
    away = {
        side: max((p.x for p in outline if side * p.y > 0.0), default=-math.inf)
        for side in sides
    }
    if abs(away[-1.0] - away[1.0]) >= HORN_DIFFERENCE:
        return (-1.0 if away[-1.0] > away[1.0] else 1.0), True
    return 0.0, False


def _eased(x: float, start: float, stop: float) -> float:
    """Return 0 before ``start``, 1 after ``stop``, a smooth step between."""
    if stop <= start:
        return 1.0 if x >= stop else 0.0
    t = min(1.0, max(0.0, (x - start) / (stop - start)))
    return t * t * (3.0 - 2.0 * t)


def guard_outline(control_points: Sequence[Point2D]) -> tuple[Point2D, ...]:
    """Return the guard's outline through its control points (a closed spline)."""
    return tuple(closed_catmull_rom(control_points, SAMPLES_PER_SEGMENT))


def pickguard(
    control_points: Sequence[Point2D],
    *,
    automatic: bool,
    thickness: float,
    pickup_openings: Sequence[tuple[str, tuple[Point2D, ...]]],
    holes: Sequence[DrilledHole],
    slots: Sequence[Cavity],
    screw_clearance: float,
    screw_spot_diameter: float,
    screw_spot_depth: float,
) -> Pickguard:
    """Return the guard through ``control_points`` with its openings.

    ``holes`` and ``slots`` under the guard go through it (pots, the
    selector's bushing, a blade switch's slot); so do the
    ``pickup_openings`` under it (``pickups.pickup_openings``, named).

    It is not checked against the body here (the body editor draws a
    guard still being moved): see ``check_on_body``.
    """
    outline = guard_outline(control_points)
    openings: list[Cavity] = [
        TracedCavity(name, opening, thickness)
        for name, opening in pickup_openings
        if any(point_in_polygon(p, outline) for p in opening)
    ]
    openings += [
        slot for slot in slots if point_in_polygon(_centre(slot.outline), outline)
    ]
    through = [
        DrilledHole(hole.name, hole.center_x, hole.center_y, hole.diameter, thickness)
        for hole in holes
        if point_in_polygon(hole.center, outline)
    ]
    screws = _screws(outline, openings, through)
    plate = CoverPlate(
        "Pickguard",
        "top",
        outline,
        thickness,
        holes=(
            *through,
            *(
                DrilledHole(f"Screw {index}", p.x, p.y, screw_clearance, thickness)
                for index, p in enumerate(screws, start=1)
            ),
        ),
        slots=tuple(openings),
    )
    spots = tuple(
        DrilledHole(
            f"Pickguard screw {index}",
            p.x,
            p.y,
            screw_spot_diameter,
            screw_spot_depth,
        )
        for index, p in enumerate(screws, start=1)
    )
    return Pickguard(plate, spots, tuple(control_points), automatic)


def clear_of_bridge(
    control_points: Sequence[Point2D],
    bridge_areas: Sequence[Sequence[Point2D]],
    pickups: Sequence[Sequence[Point2D]] = (),
) -> tuple[Point2D, ...]:
    """Return a drawn guard's points stepped round the bridge.

    A drawn guard (a template's, say) is drawn for one bridge; another
    reaches elsewhere. Wherever the guard runs into the box round the
    bridge (``bridge_areas``: its routes and holes,
    ``DRAWN_BRIDGE_CLEARANCE`` all round; where that leaves under
    ``PICKUP_MARGIN`` past the last of ``pickups``, starting halfway
    between the two), it is cut back
    along the box's edges instead — the way round that leaves the box
    outside the guard — on to wherever the guard comes out of the box
    next.

    Raises:
        BodyGeometryError: When the whole guard lies over the bridge.
    """
    points = [p for area in bridge_areas for p in area]
    if not points:
        return tuple(control_points)
    bridge_front = min(p.x for p in points)
    front = bridge_front - DRAWN_BRIDGE_CLEARANCE
    last_pickup = max((p.x for route in pickups for p in route), default=-math.inf)
    if front < last_pickup + PICKUP_MARGIN:
        # Too little room for both gaps: the edge goes halfway between the
        # bridge pickup and the bridge (into the pickup, if they overlap).
        front = max(front, (last_pickup + bridge_front) / 2.0)
    box = _Box(
        front,
        max(p.x for p in points) + DRAWN_BRIDGE_CLEARANCE,
        max(abs(p.y) for p in points) + DRAWN_BRIDGE_CLEARANCE,
    )
    return _clear_of_box(control_points, box, "the bridge")


def clear_of_truss_rod(
    control_points: Sequence[Point2D], access: Sequence[Point2D]
) -> tuple[Point2D, ...]:
    """Return a guard's points stepped round the truss rod's access notch.

    A heel-adjusted truss rod's spoke wheel sits in a notch past the neck
    pocket's end (``access``); the guard is cut back round it,
    ``TRUSS_ROD_CLEARANCE`` clear, so the wheel can be turned with the
    guard on.
    """
    if not access:
        return tuple(control_points)
    box = _Box(
        min(p.x for p in access),
        max(p.x for p in access) + TRUSS_ROD_CLEARANCE,
        max(abs(p.y) for p in access) + TRUSS_ROD_CLEARANCE,
    )
    return _clear_of_box(control_points, box, "the truss rod's access")


def _clear_of_box(
    control_points: Sequence[Point2D], box: _Box, what: str
) -> tuple[Point2D, ...]:
    """Return the guard's points cut back round ``box`` (see ``clear_of_bridge``).

    Raises:
        BodyGeometryError: When the whole guard lies over the box.
    """
    start = next((i for i, p in enumerate(control_points) if not box.holds(p)), None)
    if start is None:
        raise BodyGeometryError(f"The pickguard lies wholly over {what}.")
    loop = [*control_points[start:], *control_points[:start]]
    count = len(loop)
    # Round the box against the guard's own turn, so the box stays out.
    turn = sum(
        a.x * b.y - b.x * a.y for a, b in zip(loop, [*loop[1:], loop[0]], strict=True)
    )
    clockwise = turn > 0.0
    step = -1.0 if clockwise else 1.0
    # Where the guard's edge goes into the box and out of it: the position
    # along the edge (edge index plus fraction) and the point.
    entries: list[tuple[float, Point2D]] = []
    exits: list[tuple[float, Point2D]] = []
    for index in range(count):
        a, b = loop[index], loop[(index + 1) % count]
        crossing = box.clip(a, b)
        if crossing is None:
            continue
        t0, t1 = crossing
        if not box.holds(a) and t0 > 0.0:
            entries.append((index + t0, _between(a, b, t0)))
        if not box.holds(b) and t1 < 1.0:
            exits.append((index + t1, _between(a, b, t1)))
    if not entries or not exits:
        return tuple(control_points)
    # Along the guard's edge; at each way into the box, round the box's
    # edge to the next way out of it (wherever along the guard that is),
    # and on along the guard from there.
    result = [loop[0]]
    position = 0.0
    while position < count:
        index = int(position)
        entry = next(
            ((at, p) for at, p in entries if index <= at < index + 1 and at > position),
            None,
        )
        if entry is None:
            position = index + 1.0
            if index + 1 < count:
                result.append(loop[index + 1])
            continue
        start_place = box.place(entry[1])

        def ahead(crossing: tuple[float, Point2D]) -> float:
            along = ((box.place(crossing[1]) - start_place) * step) % box.perimeter
            return along if along > 1e-9 else box.perimeter

        exit_at, exit_point = min(exits, key=ahead)
        result += box.round(entry[1], exit_point, clockwise)
        if exit_at <= position:
            break  # round past the start: the loop is closed
        position = exit_at
    kept: list[Point2D] = []
    for point in result:
        if not kept or math.hypot(point.x - kept[-1].x, point.y - kept[-1].y) > 0.5:
            kept.append(point)
    return tuple(kept)


@dataclass(frozen=True, slots=True)
class _Box:
    """A box across the centreline: ``x0`` to ``x1`` along, ``half`` out."""

    x0: float
    x1: float
    half: float

    def holds(self, p: Point2D) -> bool:
        return self.x0 < p.x < self.x1 and -self.half < p.y < self.half

    def clip(self, a: Point2D, b: Point2D) -> tuple[float, float] | None:
        """Return where (0 to 1) the segment ``a``-``b`` is inside, if it is."""
        t0, t1 = 0.0, 1.0
        dx, dy = b.x - a.x, b.y - a.y
        for p, q in (
            (-dx, a.x - self.x0),
            (dx, self.x1 - a.x),
            (-dy, a.y + self.half),
            (dy, self.half - a.y),
        ):
            if p == 0.0:
                if q <= 0.0:
                    return None
                continue
            t = q / p
            if p < 0.0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
        return (t0, t1) if t0 < t1 else None

    @property
    def perimeter(self) -> float:
        return 2.0 * (self.x1 - self.x0) + 4.0 * self.half

    def place(self, p: Point2D) -> float:
        """Return how far round the box (anticlockwise from its corner at
        ``x0``, ``-half``) a point on its edge is."""
        if abs(p.y + self.half) < 1e-6:
            return p.x - self.x0
        if abs(p.x - self.x1) < 1e-6:
            return (self.x1 - self.x0) + p.y + self.half
        if abs(p.y - self.half) < 1e-6:
            return (self.x1 - self.x0) + 2.0 * self.half + (self.x1 - p.x)
        return self.perimeter - (p.y + self.half)

    def round(self, entry: Point2D, exit: Point2D, clockwise: bool) -> list[Point2D]:
        """Return the box's edge from ``entry`` to ``exit``, one way round.

        Clockwise (as seen with Y up) leaves the box on the right of the
        path; a guard drawn anticlockwise keeps it outside so.
        """
        corners = [
            Point2D(self.x0, -self.half),
            Point2D(self.x1, -self.half),
            Point2D(self.x1, self.half),
            Point2D(self.x0, self.half),
        ]
        perimeter = self.perimeter
        corner_places = [self.place(c) for c in corners]
        start, stop = self.place(entry), self.place(exit)
        # The corners above run anticlockwise.
        step = -1.0 if clockwise else 1.0
        span = ((stop - start) * step) % perimeter
        passed = sorted(
            (
                ((c - start) * step) % perimeter,
                corner,
            )
            for c, corner in zip(corner_places, corners, strict=True)
        )
        path = [
            entry,
            *(corner for along, corner in passed if 0.0 < along < span),
            exit,
        ]
        # Points along each edge, so a spline through them keeps to it.
        stepped = [path[0]]
        for a, b in zip(path, path[1:], strict=False):
            count = max(
                1, math.ceil(math.hypot(b.x - a.x, b.y - a.y) / DRAWN_BRIDGE_STEP)
            )
            stepped += [_between(a, b, k / count) for k in range(1, count + 1)]
        return stepped


def _between(a: Point2D, b: Point2D, t: float) -> Point2D:
    """Return the point ``t`` (0 to 1) of the way from ``a`` to ``b``."""
    return Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)


def check_on_body(guard: Pickguard, body_outline: Sequence[Point2D]) -> None:
    """Refuse a guard that runs off the body.

    Raises:
        BodyGeometryError: When a point of its outline is off the body.
    """
    if not all(point_in_polygon(p, body_outline) for p in guard.plate.outline):
        raise BodyGeometryError("The pickguard runs off the body: move its points in.")


def _spans(polygon: Sequence[Point2D], x: float) -> list[tuple[float, float]]:
    """Return the stretches across the neck where ``x`` lies inside ``polygon``."""
    ys: list[float] = []
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        if (a.x <= x < b.x) or (b.x <= x < a.x):
            ys.append(a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x))
    ys.sort()
    return [(ys[i], ys[i + 1]) for i in range(0, len(ys) - 1, 2)]


def _resampled_paths(
    paths: Sequence[Sequence[Point2D]], spacing: float
) -> tuple[Point2D, ...]:
    """Return points about ``spacing`` apart along a loop made of ``paths``.

    Each path ends where the next starts; every path's ends are kept (a
    notch's corners), the stretch between them spread evenly.
    """
    points: list[Point2D] = []
    for path in paths:
        length = sum(
            math.hypot(b.x - a.x, b.y - a.y)
            for a, b in zip(path, path[1:], strict=False)
        )
        count = max(1, round(length / spacing))
        points += _along(path, count)
    return tuple(points)


def _along(path: Sequence[Point2D], count: int) -> list[Point2D]:
    """Return ``count`` points evenly along an open ``path``, its start first."""
    lengths = [0.0]
    for a, b in zip(path, path[1:], strict=False):
        lengths.append(lengths[-1] + math.hypot(b.x - a.x, b.y - a.y))
    total = lengths[-1]
    points: list[Point2D] = []
    index = 0
    for step in range(count):
        target = total * step / count
        while index + 2 < len(lengths) and lengths[index + 1] < target:
            index += 1
        a, b = path[index], path[min(index + 1, len(path) - 1)]
        span = lengths[min(index + 1, len(lengths) - 1)] - lengths[index]
        t = 0.0 if span <= 0.0 else (target - lengths[index]) / span
        points.append(Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
    return points


def _resampled(loop: Sequence[Point2D], count: int) -> tuple[Point2D, ...]:
    """Return ``count`` points evenly spaced round a closed ``loop``."""
    closed = [*loop, loop[0]]
    lengths = [0.0]
    for a, b in zip(closed, closed[1:], strict=False):
        lengths.append(lengths[-1] + math.hypot(b.x - a.x, b.y - a.y))
    total = lengths[-1]
    points: list[Point2D] = []
    index = 0
    for step in range(count):
        target = total * step / count
        while lengths[index + 1] < target:
            index += 1
        a, b = closed[index], closed[index + 1]
        span = lengths[index + 1] - lengths[index]
        t = 0.0 if span == 0.0 else (target - lengths[index]) / span
        points.append(Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
    return tuple(points)


def _centre(points: Sequence[Point2D]) -> Point2D:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return Point2D((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def _screws(
    outline: Sequence[Point2D],
    openings: Sequence[Cavity],
    holes: Sequence[DrilledHole],
) -> tuple[Point2D, ...]:
    """Return the guard's screws, ``SCREW_INSET`` in, clear of its openings."""
    path = offset_polygon(outline, SCREW_INSET, inward=True)
    if len(path) < 3:
        return ()
    perimeter = sum(
        math.hypot(b.x - a.x, b.y - a.y)
        for a, b in zip(path, (*path[1:], path[0]), strict=True)
    )
    count = max(6, round(perimeter / SCREW_PITCH))
    clear = 4.0
    grown = [offset_polygon(o.outline, clear, inward=False) for o in openings]
    screws: list[Point2D] = []
    for point in _resampled(path, count):
        near_opening = any(point_in_polygon(point, area) for area in grown)
        near_hole = any(
            math.hypot(point.x - h.center_x, point.y - h.center_y)
            < h.diameter / 2.0 + clear
            for h in holes
        )
        if not near_opening and not near_hole:
            screws.append(point)
    return tuple(screws)
