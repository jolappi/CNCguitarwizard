"""Turn an outline drawn elsewhere into the editors' own handles.

A body's outline becomes the control points of the closed Catmull-Rom
loop ``YourDesignShape`` draws; a headstock's, the two drawn edges and the
tip points ``HeadstockPlan`` takes. Every handle lies on the drawn line,
and handles are added where the editor's curve strays from it, until it
keeps within a tolerance everywhere: the drawing, as the editor can then
move it.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..geometry.exceptions import GeometryException
from ..geometry.neck.headstock import TIP_POINT_WIDTH, tip_direction, tip_tangents
from ..geometry.primitives import (
    Point2D,
    SmoothCurve,
    closed_catmull_rom,
    flatten_span,
    hermite_spans,
)
from .exceptions import DrawingError

FIT_TOLERANCE = 0.25
"""How far (mm) the editor's curve may stray from the drawn outline."""

MAX_BODY_POINTS = 240
"""The most control points a body outline is given."""

MIN_NODE_SPACING = 8.0
"""Nodes closer than this on average (mm) are a polyline's, not handles."""

MAX_EDGE_POINTS = 40
"""The most points a headstock edge is given."""

MAX_TIP_POINTS = 16
"""The most points a headstock tip is given."""

NUT_REACH = 1.0
"""Within this far of the nut (mm) a headstock outline is at the nut."""


def resample_closed(points: Sequence[Point2D], spacing: float) -> list[Point2D]:
    """Return a closed polyline's points every ``spacing`` along it."""
    loop = [*points, points[0]]
    lengths = [math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(loop, loop[1:])]
    total = sum(lengths)
    count = max(8, round(total / spacing))
    out: list[Point2D] = []
    index, start = 0, 0.0
    for step in range(count):
        target = total * step / count
        while index < len(lengths) - 1 and start + lengths[index] < target:
            start += lengths[index]
            index += 1
        a, b = loop[index], loop[index + 1]
        t = (target - start) / lengths[index] if lengths[index] else 0.0
        out.append(Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
    return out


def _resample_through(
    loop: Sequence[Point2D], anchors: Sequence[int], spacing: float
) -> tuple[list[Point2D], list[int]]:
    """Resample a closed polyline about every ``spacing``, through anchors.

    Each stretch between two anchors (indices into ``loop``, ascending) is
    resampled on its own, so every anchor is itself a sample; returns the
    samples and the anchors' indices among them.
    """
    dense: list[Point2D] = []
    indices: list[int] = []
    count = len(loop)
    for position, start in enumerate(anchors):
        end = anchors[(position + 1) % len(anchors)]
        stretch = [loop[(start + i) % count] for i in range((end - start) % count + 1)]
        lengths = [
            math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(stretch, stretch[1:])
        ]
        total = sum(lengths)
        indices.append(len(dense))
        dense.append(stretch[0])
        steps = max(1, round(total / spacing))
        index, walked = 0, 0.0
        for step in range(1, steps):
            target = total * step / steps
            while index < len(lengths) - 1 and walked + lengths[index] < target:
                walked += lengths[index]
                index += 1
            a, b = stretch[index], stretch[index + 1]
            t = (target - walked) / lengths[index] if lengths[index] else 0.0
            dense.append(Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
    return dense, indices


def _distance_to_polyline(point: Point2D, line: Sequence[Point2D]) -> float:
    best = math.inf
    for a, b in zip(line, line[1:]):
        dx, dy = b.x - a.x, b.y - a.y
        squared = dx * dx + dy * dy
        t = (
            0.0
            if squared == 0.0
            else max(
                0.0, min(1.0, ((point.x - a.x) * dx + (point.y - a.y) * dy) / squared)
            )
        )
        best = min(best, math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy))
    return best


def _deviation(
    drawn: Sequence[Point2D], curve: Sequence[Point2D], local: bool = False
) -> float:
    """Return how far two polylines stray from each other, both ways.

    ``local``: both run the same way between the same ends, so each point
    is looked for only on the other's stretch level with it (an overstated
    distance there only adds a handle).
    """
    if len(drawn) < 2 or len(curve) < 2:
        return 0.0
    return max(_one_way(drawn, curve, local), _one_way(curve, drawn, local))


def _one_way(points: Sequence[Point2D], line: Sequence[Point2D], local: bool) -> float:
    if not local:
        return max(_distance_to_polyline(point, line) for point in points)
    window = 6 + len(line) // 10
    worst = 0.0
    for index, point in enumerate(points):
        level = round(index * (len(line) - 1) / max(1, len(points) - 1))
        stretch = line[max(0, level - window) : level + window + 1]
        worst = max(worst, _distance_to_polyline(point, stretch))
    return worst


@dataclass(frozen=True, slots=True)
class BodyFit:
    """A body outline as control points.

    Attributes:
        points: The closed loop's control points, in the drawing's order.
        deviation: How far the loop strays from the drawing at most (mm).
    """

    points: tuple[Point2D, ...]
    deviation: float


def fit_closed_spline(
    outline: Sequence[Point2D],
    nodes: Sequence[int] = (),
    tolerance: float = FIT_TOLERANCE,
    max_points: int = MAX_BODY_POINTS,
) -> BodyFit:
    """Return control points whose closed Catmull-Rom loop is the outline.

    The points start at the drawing's own ``nodes`` (indices into
    ``outline``; an outline from the template has one at every handle it
    was drawn with), or evenly spread along it with fewer than eight.
    Every span that strays more than ``tolerance`` from the outline is
    halved, as are the spans beside a halved one left more than two and a
    half times as long (a uniform Catmull-Rom loop wants its points evenly
    spaced), until none strays or there are ``max_points``.
    """
    loop = list(outline)
    node_set = set(nodes)
    perimeter = sum(
        math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(loop, (*loop[1:], loop[0]))
    )
    spacing = max(0.75, perimeter / 2000.0)
    # A polyline's (a traced or converted drawing's) nodes are no handles.
    if 8 <= len(node_set) <= perimeter / MIN_NODE_SPACING:
        dense, indices = _resample_through(loop, sorted(node_set), spacing)
    else:
        dense = resample_closed(loop, spacing)
        indices = [round(step * len(dense) / 16) for step in range(16)]
    count = len(dense)
    cache: dict[tuple[int, ...], float] = {}

    def gap(k: int) -> int:
        return (indices[(k + 1) % len(indices)] - indices[k]) % count or count

    def deviation(k: int) -> float:
        n = len(indices)
        key = tuple(indices[(k + offset) % n] for offset in (-1, 0, 1, 2))
        if key not in cache:
            start = indices[k]
            drawn = [dense[(start + i) % count] for i in range(gap(k) + 1)]
            control = [dense[index] for index in key]
            samples = max(8, len(drawn) // 2)
            curve = [
                *closed_catmull_rom(control, samples)[samples : 2 * samples],
                control[2],
            ]
            cache[key] = _deviation(drawn, curve, local=True)
        return cache[key]

    deviations: list[float] = []
    for _ in range(40):
        deviations = [deviation(k) for k in range(len(indices))]
        split = {
            k for k, value in enumerate(deviations) if value > tolerance and gap(k) > 3
        }
        if not split or len(indices) + len(split) > max_points:
            break
        # Spans beside a halved one stay at most 2.5 times its halves.
        changed = True
        while changed:
            changed = False
            n = len(indices)
            for k in range(n):
                if k in split or gap(k) <= 3:
                    continue
                for neighbour in ((k - 1) % n, (k + 1) % n):
                    after = gap(neighbour) / 2 if neighbour in split else gap(neighbour)
                    if gap(k) > 2.5 * after:
                        split.add(k)
                        changed = True
                        break
        inserted: list[int] = []
        for k, start in enumerate(indices):
            inserted.append(start)
            if k in split:
                inserted.append((start + gap(k) // 2) % count)
        indices = sorted(set(inserted))
    return BodyFit(tuple(dense[i] for i in indices), max(deviations, default=0.0))


@dataclass(frozen=True, slots=True)
class HeadstockFit:
    """A headstock outline as the drawn edges and tip points.

    Attributes:
        bass_edge: ``headstock_bass_edge``: (distance from the nut,
            half-width) points, the last at the tip.
        treble_edge: ``headstock_treble_edge`` likewise.
        tip_points: ``headstock_tip_points``: (how far past the tip line,
            y) across the tip from -Y to +Y.
        deviation: How far the fitted outline strays from the drawing at
            most (mm), the nut's own end left out.
    """

    bass_edge: tuple[tuple[float, float], ...]
    treble_edge: tuple[tuple[float, float], ...]
    tip_points: tuple[tuple[float, float], ...]
    deviation: float


def fit_headstock(
    outline: Sequence[Point2D],
    nut_half_width: float,
    bass_sign: float,
    nodes: Sequence[int] = (),
    tolerance: float = FIT_TOLERANCE,
) -> HeadstockFit:
    """Return the drawn edges and tip that make a headstock's outline.

    ``outline`` is the headstock in the model frame (X negative past the
    nut), closed — along the nut line, or anywhere else near the nut. It
    is read from the point furthest from the nut back along both sides to
    the nut. Both edges end at one distance from the nut, the tip line,
    and the tip runs across from the -Y side's end to the +Y side's; the
    tip line is the first of these that draws the outline within
    ``tolerance``, else the one drawing it closest: where the drawing has
    a node on both sides at one distance (the template's tip corners,
    furthest first); where each side turns to run more across the
    headstock than along it; and back from the far end a millimetre at a
    time. Corners closer together than ``TIP_POINT_WIDTH`` make a pointed
    tip. The drawing's own ``nodes`` (indices into ``outline``) on an edge
    or the tip are its first points there (from the template, every handle
    the editor had), and points are added where it strays.

    Raises:
        DrawingError: If the outline does not reach back to the nut on
            both sides, or no tip line leaves edges that run away from the
            nut and a tip that runs across the headstock (a hook the tip
            points cannot draw).
    """
    loop = list(outline)
    perimeter = sum(
        math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(loop, (*loop[1:], loop[0]))
    )
    anchors = sorted(set(nodes))
    if 3 <= len(anchors) <= perimeter / MIN_NODE_SPACING:
        loop, _ = _resample_through(loop, anchors, 0.5)
    else:
        loop = resample_closed(loop, 0.5)
    count = len(loop)
    apex = max(range(count), key=lambda i: -loop[i].x)
    if -loop[apex].x < 20.0:
        raise DrawingError("The outline does not reach past the nut.")
    chains = []
    for step in (1, -1):
        chain = [loop[apex]]
        index = apex
        for _ in range(count):
            index = (index + step) % count
            chain.append(loop[index])
            if -loop[index].x <= NUT_REACH:
                break
        else:
            raise DrawingError(
                "The outline does not come back to the nut on both sides: "
                "draw the headstock from the nut on one side round to the "
                "nut on the other."
            )
        # From the nut to the apex, as (distance, y).
        chains.append([(-p.x, p.y) for p in reversed(chain)])
    # The side leaving the nut at -Y first (it may cross over by the tip).
    low, high = sorted(chains, key=lambda chain: chain[0][1])
    node_points = [(-outline[i].x, outline[i].y) for i in anchors]
    reach = min(_reach(low), _reach(high))

    on_low = [node for node in node_points if _on(low, node)]
    on_high = [node for node in node_points if _on(high, node)]
    pairs = sorted(
        {
            d
            for d, y in on_low
            for e, z in on_high
            if abs(d - e) < 0.01 and abs(y - z) >= TIP_POINT_WIDTH
        },
        reverse=True,
    )
    corners = [chain[_corner(chain)] for chain in (low, high)]
    # Corners meeting: a pointed tip, its edges running on to the point.
    meeting = abs(corners[1][1] - corners[0][1]) < TIP_POINT_WIDTH
    best: tuple[float, HeadstockFit] | None = None
    tried: set[float] = set()
    # The node pairs, furthest first (a symmetric tip's own nodes pair up
    # too, so one is kept only well within the tolerance, else the
    # closest); then the corners and the sweep, the first close enough.
    distances = [corner[0] for corner in corners]
    for stage in (
        [reach] if meeting else [],
        pairs,
        [min(distances), max(distances), *(reach - step for step in range(80))],
    ):
        for length in stage:
            length = min(length, reach)
            if length <= NUT_REACH + 5.0 or round(length, 2) in tried:
                continue
            tried.add(round(length, 2))
            fit = _fit_at(
                low, high, length, node_points, nut_half_width, bass_sign, tolerance
            )
            if fit is None:
                continue
            if best is None or fit.deviation < best[0]:
                best = (fit.deviation, fit)
            # A template's own corners: much closer than any other pair.
            if fit.deviation <= (tolerance / 2 if stage is pairs else tolerance):
                return fit
        if best is not None and best[0] <= tolerance:
            return best[1]
    if best is None:
        raise DrawingError(
            "The tip turns back across the headstock (a hook) or an edge turns "
            "back toward the nut: each edge must run away from the nut to the "
            "tip, and the tip across from one edge's end to the other's."
        )
    return best[1]


def _reach(chain: Sequence[tuple[float, float]]) -> float:
    """Return how far a side, nut to apex, runs away from the nut unbroken."""
    for index in range(1, len(chain)):
        if chain[index][0] <= chain[index - 1][0]:
            return chain[index - 1][0]
    return chain[-1][0]


def _on(chain: Sequence[tuple[float, float]], node: tuple[float, float]) -> bool:
    return (
        _distance_to_polyline(
            Point2D(-node[0], node[1]), [Point2D(-d, y) for d, y in chain]
        )
        < 0.05
    )


def _fit_at(
    low: Sequence[tuple[float, float]],
    high: Sequence[tuple[float, float]],
    length: float,
    nodes: Sequence[tuple[float, float]],
    nut_half_width: float,
    bass_sign: float,
    tolerance: float,
) -> HeadstockFit | None:
    """Return the fit with the tip line at ``length``, or ``None``.

    ``None`` where the tip, from the -Y side's end at ``length`` round to
    the +Y side's, does not run across the headstock.
    """
    low_edge, low_rest = _cut(low, length)
    high_edge, high_rest = _cut(high, length)
    tip = [*low_rest, *reversed(high_rest[:-1])]
    if any(b[1] < a[1] - 0.05 for a, b in zip(tip, tip[1:])):
        return None
    pointed = abs(high_edge[-1][1] - low_edge[-1][1]) < TIP_POINT_WIDTH
    if pointed and len(tip) > 2:
        # Ends this close only where the edges meet at the apex.
        return None
    seeds = _seeds(nodes, (low_edge, high_edge, tip))
    edges = {}
    deviation = 0.0
    try:
        for y_sign, edge, seed in (
            (-1.0, low_edge, seeds[0]),
            (1.0, high_edge, seeds[1]),
        ):
            points, error = _fit_edge(edge, nut_half_width, y_sign, tolerance, seed)
            edges["bass" if y_sign * bass_sign > 0 else "treble"] = points
            deviation = max(deviation, error)
        tip_points: tuple[tuple[float, float], ...] = ()
        if not pointed and len(tip) > 2:
            tip_points, error = _fit_tip(
                tip, length, edges, bass_sign, nut_half_width, tolerance, seeds[2]
            )
            deviation = max(deviation, error)
    except DrawingError:
        return None
    return HeadstockFit(edges["bass"], edges["treble"], tip_points, deviation)


def _seeds(
    nodes: Sequence[tuple[float, float]],
    parts: Sequence[Sequence[tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    """Return the nodes lying on each part (an edge or the tip), in turn."""
    found: list[list[tuple[float, float]]] = [[] for _ in parts]
    for node in nodes:
        point = Point2D(-node[0], node[1])
        distances = [
            _distance_to_polyline(point, [Point2D(-d, y) for d, y in part])
            if len(part) > 1
            else math.inf
            for part in parts
        ]
        nearest = min(range(len(parts)), key=lambda index: distances[index])
        if distances[nearest] < 0.05:
            found[nearest].append(node)
    return found


def _corner(chain: Sequence[tuple[float, float]]) -> int:
    """Return where a side, nut to apex, stops running along the headstock.

    Back from the apex, the last point reached while every step runs more
    across the headstock than along it (or back toward the nut).
    """
    index = len(chain) - 1
    while index > 0:
        (d0, y0), (d1, y1) = chain[index - 1], chain[index]
        if d1 - d0 > abs(y1 - y0):
            break
        index -= 1
    return index


def _cut(
    side: Sequence[tuple[float, float]], length: float
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Split a side, nut to apex, at ``length``: the edge and the rest.

    The edge ends at ``length`` and the rest starts there; ``length`` is
    no further than the side runs away from the nut unbroken.
    """
    for index in range(1, len(side)):
        (d0, y0), (d1, y1) = side[index - 1], side[index]
        if d1 >= length - 1e-9:
            t = (length - d0) / (d1 - d0) if d1 > d0 else 1.0
            end = (length, y0 + (y1 - y0) * t)
            rest = [end, *side[index:]] if d1 > length + 1e-9 else list(side[index:])
            return [*side[:index], end], rest
    return list(side), [side[-1]]


def _fit_edge(
    edge: Sequence[tuple[float, float]],
    nut_half_width: float,
    y_sign: float,
    tolerance: float,
    seeds: Sequence[tuple[float, float]] = (),
) -> tuple[tuple[tuple[float, float], ...], float]:
    """Return a ``SmoothCurve`` edge's points, and how far it strays.

    ``edge`` runs from the nut to the tip as (distance, y); the curve
    starts at the nut's half-width, runs through the ``seeds`` (nodes on
    the edge) and ends at the edge's own end.
    """
    samples = [(d, y_sign * y) for d, y in edge if d > NUT_REACH]
    for (d0, _), (d1, _) in zip(samples, samples[1:]):
        if d1 <= d0:
            side = "+Y" if y_sign > 0 else "-Y"
            raise DrawingError(
                f"The {side} edge turns back toward the nut {d0:.0f} mm from it: "
                "an edge must run away from the nut all the way to the tip."
            )
    if not samples:
        raise DrawingError("The headstock outline has no edge past the nut.")
    end = samples[-1]
    chosen = [end]
    for d, y in sorted(seeds):
        if NUT_REACH < d < end[0] - 0.05 and all(abs(d - c) >= 0.05 for c, _ in chosen):
            chosen.append((d, y_sign * y))
    chosen.sort()
    error = 0.0
    for _ in range(MAX_EDGE_POINTS):
        try:
            curve = SmoothCurve(((0.0, nut_half_width), *chosen))
        except GeometryException as failure:
            raise DrawingError(f"The edge cannot be drawn ({failure}).") from failure
        worst, error = None, 0.0
        for d, half in samples:
            miss = abs(curve.value_at(d) - half)
            if miss > error and all(abs(d - c) >= 1.0 for c, _ in chosen):
                worst, error = (d, half), miss
        if worst is None or error <= tolerance:
            break
        chosen = sorted([*chosen, worst])
    return tuple((round(d, 2), round(h, 2)) for d, h in chosen), error


def _fit_tip(
    tip: Sequence[tuple[float, float]],
    length: float,
    edges: dict[str, tuple[tuple[float, float], ...]],
    bass_sign: float,
    nut_half_width: float,
    tolerance: float,
    seeds: Sequence[tuple[float, float]] = (),
) -> tuple[tuple[tuple[float, float], ...], float]:
    """Return the tip points shaping the tip, and how far it strays.

    The ``seeds`` (nodes on the tip) are its first points.
    """
    drawn = [Point2D(-d, y) for d, y in tip]
    for a, b in zip(drawn, drawn[1:]):
        if b.y < a.y - 0.05:
            raise DrawingError(
                "The tip turns back across the headstock (a hook): the tip runs "
                "across from corner to corner. Draw the hook into an edge "
                "instead, or straighten it."
            )

    def edge_y(y_sign: float) -> Callable[[float], float]:
        side = "bass" if y_sign * bass_sign > 0 else "treble"
        curve = SmoothCurve(((0.0, nut_half_width), *edges[side]))
        return lambda d: y_sign * curve.value_at(d)

    low = Point2D(-length, edge_y(-1.0)(length))
    high = Point2D(-length, edge_y(1.0)(length))
    directions = (
        tip_direction(edge_y(-1.0), length),
        tip_direction(edge_y(1.0), length),
    )
    inner = drawn[1:-1]
    chosen: list[Point2D] = []
    for d, y in sorted(seeds, key=lambda seed: seed[1]):
        if low.y + 0.5 < y < high.y - 0.5 and all(abs(y - c.y) >= 0.5 for c in chosen):
            chosen.append(Point2D(-d, y))
    error = 0.0
    for _ in range(MAX_TIP_POINTS + 1):
        nodes = (low, *chosen, high)
        curve = [nodes[0]]
        if chosen:
            for span in hermite_spans(nodes, tip_tangents(nodes, *directions)):
                curve.extend(flatten_span(span, 0.02))
        else:
            curve.append(high)
        error = _deviation(drawn, curve)
        if error <= tolerance or len(chosen) == MAX_TIP_POINTS:
            break
        candidates = [
            p
            for p in inner
            if p.y > low.y
            and p.y < high.y
            and all(abs(p.y - c.y) >= 0.5 for c in chosen)
        ]
        if not candidates:
            break
        worst = max(candidates, key=lambda p: _distance_to_polyline(p, curve))
        chosen = sorted([*chosen, worst], key=lambda p: p.y)
    return (
        tuple((round(-p.x - length, 2), round(p.y, 2)) for p in chosen),
        error,
    )
