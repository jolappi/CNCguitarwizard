"""Planar helpers shared by the 2.5D toolpath generators.

Everything here works on closed polygons given as ordered ``Point2D``
loops. The key primitive is the *clearance* question — where can the
centre of a disc of a given radius go while the disc stays entirely
inside (or entirely outside) a polygon? It is answered exactly for
horizontal scanlines (``clear_intervals``) and approximately, but
conservatively, for whole contours (``offset_polygon``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..geometry.primitives import Point2D, point_in_polygon

Interval = tuple[float, float]

_EPSILON = 1e-9


def signed_area(polygon: Sequence[Point2D]) -> float:
    """Return the polygon's signed area (positive when counter-clockwise)."""
    total = 0.0
    count = len(polygon)
    for index in range(count):
        first = polygon[index]
        second = polygon[(index + 1) % count]
        total += first.x * second.y - second.x * first.y
    return total / 2.0


def oriented(polygon: Sequence[Point2D], *, clockwise: bool) -> tuple[Point2D, ...]:
    """Return the polygon wound in the requested direction."""
    points = tuple(polygon)
    is_clockwise = signed_area(points) < 0.0
    return points if is_clockwise == clockwise else tuple(reversed(points))


def polygon_bounds(polygon: Sequence[Point2D]) -> tuple[float, float, float, float]:
    """Return ``(min_x, min_y, max_x, max_y)`` of the polygon."""
    xs = [point.x for point in polygon]
    ys = [point.y for point in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def segment_distance(point: Point2D, start: Point2D, end: Point2D) -> float:
    """Return the distance from a point to a line segment."""
    dx, dy = end.x - start.x, end.y - start.y
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(point.x - start.x, point.y - start.y)
    t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy))


def distance_to_boundary(point: Point2D, polygon: Sequence[Point2D]) -> float:
    """Return the distance from a point to the nearest polygon edge."""
    count = len(polygon)
    return min(
        segment_distance(point, polygon[index], polygon[(index + 1) % count])
        for index in range(count)
    )


def disc_fits(
    point: Point2D,
    polygon: Sequence[Point2D],
    radius: float,
    *,
    inside: bool = True,
) -> bool:
    """Return whether a disc centred at ``point`` lies wholly inside/outside.

    ``inside=True`` asks whether the disc fits inside the polygon;
    ``inside=False`` whether it lies entirely outside it. A disc that
    merely touches the boundary counts as fitting.
    """
    if point_in_polygon(point, polygon) != inside:
        return False
    return distance_to_boundary(point, polygon) >= radius - _EPSILON


def segment_fits(
    start: Point2D,
    end: Point2D,
    polygon: Sequence[Point2D],
    radius: float,
    *,
    inside: bool = True,
    spacing: float = 1.0,
) -> bool:
    """Return whether the disc fits at every sample along a segment."""
    length = math.hypot(end.x - start.x, end.y - start.y)
    steps = max(1, math.ceil(length / spacing))
    for step in range(steps + 1):
        fraction = step / steps
        sample = Point2D(
            start.x + (end.x - start.x) * fraction,
            start.y + (end.y - start.y) * fraction,
        )
        if not disc_fits(sample, polygon, radius, inside=inside):
            return False
    return True


def clear_intervals(
    polygon: Sequence[Point2D],
    y: float,
    radius: float,
) -> list[Interval]:
    """Return the x-intervals on a horizontal line where a disc fits inside.

    The line ``Y = y`` crosses the polygon in a set of inside intervals
    (ray casting). A disc of ``radius`` centred on the line is blocked
    wherever the line passes within ``radius`` of an edge — the
    intersection of the line with that edge's stadium (segment ⊕ disc),
    which is a single interval because a stadium is convex. The result
    is the inside intervals minus the union of every blocked interval.
    """
    crossings: list[float] = []
    blocked: list[Interval] = []
    count = len(polygon)
    for index in range(count):
        first = polygon[index]
        second = polygon[(index + 1) % count]
        if (first.y > y) != (second.y > y):
            crossings.append(
                first.x + (y - first.y) * (second.x - first.x) / (second.y - first.y)
            )
        stadium = _stadium_interval(first, second, y, radius)
        if stadium is not None:
            blocked.append(stadium)
    crossings.sort()
    inside = [
        (crossings[index], crossings[index + 1])
        for index in range(0, len(crossings) - 1, 2)
    ]
    return _subtract_intervals(inside, _merge_intervals(blocked))


def offset_polygon(
    polygon: Sequence[Point2D],
    distance: float,
    *,
    inward: bool,
    arc_spacing: float = 0.5,
    sample_spacing: float = 1.0,
) -> tuple[Point2D, ...]:
    """Return the polygon offset by ``distance`` toward the inside or outside.

    Each edge is shifted along its normal; at vertices where the shifted
    edges pull apart a sampled arc about the vertex fills the gap. The
    raw result self-intersects where the shifted edges cross, so every
    candidate point is then checked against the original polygon and
    dropped unless a disc of ``distance`` centred there fits on the
    requested side. What remains is the true offset contour, in order,
    with any region too narrow for the disc left out. An empty tuple
    means the whole polygon is too narrow.
    """
    points = oriented(polygon, clockwise=False)
    count = len(points)
    sign = 1.0 if inward else -1.0
    raw: list[Point2D] = []
    for index in range(count):
        first = points[index]
        second = points[(index + 1) % count]
        third = points[(index + 2) % count]
        ux, uy = _unit(first, second)
        nx, ny = -uy * sign, ux * sign
        start = Point2D(first.x + nx * distance, first.y + ny * distance)
        end = Point2D(second.x + nx * distance, second.y + ny * distance)
        raw.extend(_densify(start, end, sample_spacing))
        vx, vy = _unit(second, third)
        mx, my = -vy * sign, vx * sign
        cross = ux * vy - uy * vx
        needs_arc = cross < 0.0 if inward else cross > 0.0
        if not needs_arc:
            continue
        start_angle = math.atan2(ny, nx)
        sweep = _signed_sweep(start_angle, math.atan2(my, mx))
        steps = max(1, math.ceil(abs(sweep) * distance / arc_spacing))
        # Place the arc samples on the circumscribed polygon — at the
        # half-step angles, slightly outside the true arc — so every
        # chord between them, and the chords joining the straight
        # offsets at either end, lie on tangents of the arc. A tool
        # following the chords then never comes closer than ``distance``
        # to the vertex.
        step_angle = sweep / steps
        chord_radius = distance / math.cos(abs(step_angle) / 2.0)
        for step in range(steps):
            angle = start_angle + step_angle * (step + 0.5)
            raw.append(
                Point2D(
                    second.x + math.cos(angle) * chord_radius,
                    second.y + math.sin(angle) * chord_radius,
                )
            )
    kept: list[Point2D] = []
    for candidate in raw:
        if not disc_fits(candidate, points, distance, inside=inward):
            continue
        if kept and math.hypot(
            candidate.x - kept[-1].x, candidate.y - kept[-1].y
        ) < 1e-6:
            continue
        kept.append(candidate)
    if len(kept) > 1 and math.hypot(
        kept[0].x - kept[-1].x, kept[0].y - kept[-1].y
    ) < 1e-6:
        kept.pop()
    return tuple(kept) if len(kept) >= 3 else ()


def _unit(start: Point2D, end: Point2D) -> tuple[float, float]:
    """Return the unit direction from ``start`` to ``end``."""
    dx, dy = end.x - start.x, end.y - start.y
    length = math.hypot(dx, dy)
    if length == 0.0:
        return 1.0, 0.0
    return dx / length, dy / length


def _densify(start: Point2D, end: Point2D, spacing: float) -> list[Point2D]:
    """Return ``start``, evenly spaced interior samples, and ``end``."""
    length = math.hypot(end.x - start.x, end.y - start.y)
    steps = max(1, math.ceil(length / spacing))
    return [
        Point2D(
            start.x + (end.x - start.x) * step / steps,
            start.y + (end.y - start.y) * step / steps,
        )
        for step in range(steps + 1)
    ]


def _signed_sweep(start_angle: float, end_angle: float) -> float:
    """Return the shortest signed rotation from one angle to another."""
    return (end_angle - start_angle + math.pi) % (2.0 * math.pi) - math.pi


def _stadium_interval(
    start: Point2D,
    end: Point2D,
    y: float,
    radius: float,
) -> Interval | None:
    """Return where the line ``Y = y`` passes *strictly* within ``radius``.

    A disc that only touches the segment is not blocked, so the line
    exactly one radius away from an edge yields nothing — consistent
    with ``disc_fits``.
    """
    parts: list[Interval] = []
    for centre in (start, end):
        offset = y - centre.y
        if abs(offset) < radius:
            half = math.sqrt(max(0.0, radius * radius - offset * offset))
            parts.append((centre.x - half, centre.x + half))
    dx, dy = end.x - start.x, end.y - start.y
    length = math.hypot(dx, dy)
    if length > 0.0:
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        along = _linear_interval(start.x, (y - start.y) * uy, ux, 0.0, length)
        across = _linear_interval(
            start.x, (y - start.y) * ny, nx, -radius, radius
        )
        if along is not None and across is not None:
            low = max(along[0], across[0])
            high = min(along[1], across[1])
            if low <= high:
                parts.append((low, high))
    if not parts:
        return None
    return min(part[0] for part in parts), max(part[1] for part in parts)


def _linear_interval(
    origin_x: float,
    constant: float,
    coefficient: float,
    low: float,
    high: float,
) -> Interval | None:
    """Solve ``low <= constant + coefficient * (x - origin_x) <= high`` for x.

    Returns ``None`` when no x satisfies it and an unbounded interval
    when every x does (the coefficient vanishes and the constant lies
    strictly inside the bounds — sitting exactly on a bound is a touch,
    not a block).
    """
    if abs(coefficient) < 1e-12:
        if low < constant < high:
            return (-math.inf, math.inf)
        return None
    first = origin_x + (low - constant) / coefficient
    second = origin_x + (high - constant) / coefficient
    return (min(first, second), max(first, second))


def _merge_intervals(intervals: list[Interval]) -> list[Interval]:
    """Return the union of intervals as sorted, disjoint intervals."""
    merged: list[Interval] = []
    for low, high in sorted(intervals):
        if merged and low <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def _subtract_intervals(
    keep: list[Interval],
    remove: list[Interval],
) -> list[Interval]:
    """Return the parts of ``keep`` not covered by the disjoint ``remove``."""
    result: list[Interval] = []
    for low, high in keep:
        cursor = low
        for cut_low, cut_high in remove:
            if cut_high <= cursor or cut_low >= high:
                continue
            if cut_low > cursor:
                result.append((cursor, cut_low))
            cursor = max(cursor, cut_high)
            if cursor >= high:
                break
        if cursor < high - _EPSILON:
            result.append((cursor, high))
    return [(low, high) for low, high in result if high - low > _EPSILON]
