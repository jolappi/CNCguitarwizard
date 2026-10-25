"""Chambers routed into a body's core under a separate top.

A body glued up from a core and a separate top (a cap, see
``BodySolid.cap_thickness``) can be lightened as a chambered Les Paul is:
pockets routed into the core's top before the cap is glued on, hidden
under it. They take the room that is left:

* ``CHAMBER_EDGE_WALL`` in from the body's edge;
* ``CHAMBER_WALL`` clear of every cavity and hole reaching into the core
  (a route from the top through the cap, a rear cavity, the studs, the
  neck pocket, a wire channel), and of where the top falls within
  ``CHAMBER_CAP_WALL`` of the cap's underside (a carve's rim, a contour);
* out of a centre block along the body's middle (``block`` either side of
  the centreline) that holds the pickups, the bridge and the tailpiece, as
  a chambered body keeps its middle solid;
* their corners rounded ``CHAMBER_RADIUS`` round (none narrower than twice
  that), and none smaller than ``CHAMBER_LEAST_AREA``;
* each down from the cap's underside to ``CHAMBER_FLOOR`` over the back
  (over a belly cut where it reaches under them).

The room is found on a grid ``CHAMBER_GRID`` apart: the distances to what
it must keep clear of, the corners rounded by shrinking it by the radius
and growing it back, and the chambers traced round it (marching squares),
the grid's steps smoothed out (only ever inward).
Wood left standing inside a chamber (a stud's, a cavity's) is joined to its
wall by a rib ``2 * CHAMBER_WALL`` wide, so every chamber is one pocket with
no island. Heights are above the back face, as the wiring's are.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from ..primitives import Point2D, level_loops, point_in_polygon, thinned_loop
from .hardware import TracedCavity
from .wiring import WireSpace

CHAMBER_EDGE_WALL = 12.0
"""Least wood between a chamber and the body's edge, in mm."""

CHAMBER_WALL = 8.0
"""Least wood between a chamber and any cavity or hole, in mm."""

CHAMBER_FLOOR = 6.0
"""Wood a chamber leaves over the back, in mm."""

CHAMBER_CAP_WALL = 4.0
"""Least wood of the top over a chamber, in mm."""

CHAMBER_RADIUS = 12.0
"""A chamber's corners' radius, in mm."""

CHAMBER_LEAST_AREA = 2000.0
"""The smallest chamber routed, in mm²."""

CHAMBER_GRID = 2.0
"""The spacing of the grid the room is found on, in mm."""

CHAMBER_TOLERANCE = 0.2
"""How far a chamber's thinned outline may stray from its smoothed one, in
mm."""

_SMOOTHING = 8
"""How many times a traced outline is smoothed (each point drawn to its
neighbours): the grid's steps taken out, moving it well within the cell of
slack its walls are found with."""

_RIBS = 6
"""How many times ribs are added before the chambers are taken as found."""


def plan_chambers(
    outline: Sequence[Point2D],
    thickness: float,
    cap: float,
    keep_clear: Sequence[WireSpace],
    block: float,
    top_at: Callable[[Point2D], float] | None = None,
    back_at: Callable[[Point2D], float] | None = None,
) -> tuple[TracedCavity, ...]:
    """Return the chambers routed into the core under a separate top.

    Args:
        outline: The body's outline.
        thickness: The body's thickness.
        cap: The separate top's thickness: the chambers are routed down
            from ``thickness - cap``.
        keep_clear: Every cavity and hole; those reaching within
            ``CHAMBER_CAP_WALL`` of the cap's underside are kept clear of.
        block: The centre block's half-width: none of it within that of
            the centreline (``0`` for none).
        top_at: The top's height at a point, ``thickness`` if not given.
        back_at: The back's height at a point, ``0`` if not given.

    Returns:
        The chambers, ``"Chamber 1"`` nearest the neck, each its depth
        down from the cap's underside.
    """
    split = thickness - cap
    top = top_at or (lambda point: thickness)
    back = back_at or (lambda point: 0.0)
    cell = CHAMBER_GRID
    margin = CHAMBER_EDGE_WALL + 3.0 * cell
    xs = [p.x for p in outline]
    ys = [p.y for p in outline]
    left, bottom = min(xs) - margin, min(ys) - margin
    columns = math.ceil((max(xs) + margin - left) / cell) + 1
    rows = math.ceil((max(ys) + margin - bottom) / cell) + 1

    def at(i: int, j: int) -> Point2D:
        return Point2D(left + i * cell, bottom + j * cell)

    inside = _filled([tuple(outline)], left, bottom, cell, columns, rows)
    near = [
        polygon
        for space in keep_clear
        if space.bottom < split + CHAMBER_CAP_WALL
        for polygon in (space.outline, *space.parts)
        if len(polygon) >= 3
    ]
    blocked = _filled(near, left, bottom, cell, columns, rows)
    for i in range(columns):
        for j in range(rows):
            if not inside[i][j]:
                continue
            point = at(i, j)
            if abs(point.y) <= block or top(point) - split < CHAMBER_CAP_WALL:
                blocked[i][j] = True
    outside = [[not value for value in column] for column in inside]
    to_edge = _distances(outside, cell)
    # A cell's worth of slack: the grid finds a distance to its points.
    edge_wall = CHAMBER_EDGE_WALL + cell
    wall = CHAMBER_WALL + cell
    chambers: list[tuple[Point2D, ...]] = []
    for _ in range(_RIBS):
        to_wood = _distances(blocked, cell)
        room = [
            [
                inside[i][j] and to_edge[i][j] >= edge_wall and to_wood[i][j] >= wall
                for j in range(rows)
            ]
            for i in range(columns)
        ]
        # Shrunk by the radius and grown back: corners rounded, slivers gone.
        # Grown back a cell less, as the grid finds distances to its points:
        # so it never reaches past the room.
        to_wall = _distances([[not value for value in column] for column in room], cell)
        kept = [[value >= CHAMBER_RADIUS for value in column] for column in to_wall]
        to_kept = _distances(kept, cell)
        grown = CHAMBER_RADIUS - cell
        level = [[value - grown for value in column] for column in to_kept]
        loops = [
            thinned_loop(_smoothed(loop), CHAMBER_TOLERANCE)
            for loop in level_loops(level, left, bottom, cell, 0.01)
        ]
        islands = [
            loop
            for loop in loops
            if any(
                other is not loop and point_in_polygon(loop[0], other)
                for other in loops
            )
        ]
        chambers = [loop for loop in loops if not any(loop is i for i in islands)]
        if not islands:
            break
        # Each island's wood joined to the chamber's wall by a rib.
        for island in islands:
            around = next(
                loop for loop in chambers if point_in_polygon(island[0], loop)
            )
            start = min(
                island,
                key=lambda p: min(math.dist(_xy(p), _xy(q)) for q in around),
            )
            end = min(around, key=lambda q: math.dist(_xy(start), _xy(q)))
            _rib(blocked, start, end, left, bottom, cell)
    found: list[TracedCavity] = []
    for loop in sorted(chambers, key=lambda loop: min(p.x for p in loop)):
        if abs(_area(loop)) < CHAMBER_LEAST_AREA:
            continue
        highest = max(back(point) for point in _samples(loop, cell))
        depth = split - highest - CHAMBER_FLOOR
        if depth <= cell:
            continue
        ordered = loop if _area(loop) > 0.0 else tuple(reversed(loop))
        found.append(TracedCavity(f"Chamber {len(found) + 1}", ordered, depth))
    return tuple(found)


def _filled(
    polygons: Sequence[Sequence[Point2D]],
    left: float,
    bottom: float,
    cell: float,
    columns: int,
    rows: int,
) -> list[list[bool]]:
    """Return which grid points lie inside any of ``polygons`` (scanlines)."""
    cells = [[False] * rows for _ in range(columns)]
    for polygon in polygons:
        edges = list(zip(polygon, (*polygon[1:], polygon[0]), strict=True))
        for j in range(rows):
            y = bottom + j * cell
            crossings = sorted(
                a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y)
                for a, b in edges
                if (a.y <= y < b.y) or (b.y <= y < a.y)
            )
            for start, end in zip(crossings[0::2], crossings[1::2], strict=False):
                first = max(0, math.ceil((start - left) / cell))
                last = min(columns - 1, math.floor((end - left) / cell))
                for i in range(first, last + 1):
                    cells[i][j] = True
    return cells


def _distances(features: list[list[bool]], cell: float) -> list[list[float]]:
    """Return each grid point's distance to the nearest feature point.

    The exact Euclidean distance transform, a line at a time each way
    (Felzenszwalb and Huttenlocher); infinite with no feature at all.
    """
    columns, rows = len(features), len(features[0])
    far = float(columns * columns + rows * rows) * 4.0
    # Down each column, then along each row, in squared grid steps.
    squared = [
        _line_transform([0.0 if value else far for value in column])
        for column in features
    ]
    across = [
        _line_transform([squared[i][j] for i in range(columns)]) for j in range(rows)
    ]
    return [
        [
            math.sqrt(across[j][i]) * cell if across[j][i] < far else math.inf
            for j in range(rows)
        ]
        for i in range(columns)
    ]


def _line_transform(values: list[float]) -> list[float]:
    """Return the squared distance transform of one line of the grid."""
    count = len(values)
    hull = [0] * count
    bounds = [0.0] * (count + 1)
    k = 0
    bounds[0], bounds[1] = -math.inf, math.inf
    for q in range(1, count):
        while True:
            p = hull[k]
            s = ((values[q] + q * q) - (values[p] + p * p)) / (2.0 * (q - p))
            if s <= bounds[k]:
                k -= 1
                continue
            break
        k += 1
        hull[k] = q
        bounds[k] = s
        bounds[k + 1] = math.inf
    out = [0.0] * count
    k = 0
    for q in range(count):
        while bounds[k + 1] < q:
            k += 1
        p = hull[k]
        out[q] = (q - p) * (q - p) + values[p]
    return out


def _rib(
    blocked: list[list[bool]],
    start: Point2D,
    end: Point2D,
    left: float,
    bottom: float,
    cell: float,
) -> None:
    """Mark the grid points along ``start``-``end`` as wood to keep."""
    length = max(math.dist(_xy(start), _xy(end)), cell)
    steps = math.ceil(length / (cell / 2.0)) + 1
    for k in range(steps + 1):
        t = k / steps
        x = start.x + (end.x - start.x) * t
        y = start.y + (end.y - start.y) * t
        i, j = round((x - left) / cell), round((y - bottom) / cell)
        if 0 <= i < len(blocked) and 0 <= j < len(blocked[0]):
            blocked[i][j] = True


def _smoothed(loop: Sequence[Point2D]) -> list[Point2D]:
    """Return a closed loop smoothed ``_SMOOTHING`` times, each point
    moved halfway to the middle of its neighbours, but only ever inward:
    one that would leave the traced loop (across a sharp inside corner,
    where a rib meets the wood it holds) stays where it was traced."""
    points = list(loop)
    for _ in range(_SMOOTHING):
        points = [
            Point2D((a.x + 2.0 * b.x + c.x) / 4.0, (a.y + 2.0 * b.y + c.y) / 4.0)
            for a, b, c in zip(
                (points[-1], *points[:-1]),
                points,
                (*points[1:], points[0]),
                strict=True,
            )
        ]
    return [
        point if point_in_polygon(point, loop) else traced
        for point, traced in zip(points, loop, strict=True)
    ]


def _samples(loop: Sequence[Point2D], cell: float) -> list[Point2D]:
    """Return points over a loop's area: its corners and a grid inside it."""
    xs = [p.x for p in loop]
    ys = [p.y for p in loop]
    found = list(loop)
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            point = Point2D(x, y)
            if point_in_polygon(point, loop):
                found.append(point)
            x += 2.0 * cell
        y += 2.0 * cell
    return found


def _area(points: Sequence[Point2D]) -> float:
    """Return a closed polygon's signed area (positive counter-clockwise)."""
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


def _xy(point: Point2D) -> tuple[float, float]:
    return (point.x, point.y)


__all__ = [
    "CHAMBER_CAP_WALL",
    "CHAMBER_EDGE_WALL",
    "CHAMBER_FLOOR",
    "CHAMBER_GRID",
    "CHAMBER_LEAST_AREA",
    "CHAMBER_RADIUS",
    "CHAMBER_TOLERANCE",
    "CHAMBER_WALL",
    "plan_chambers",
]
