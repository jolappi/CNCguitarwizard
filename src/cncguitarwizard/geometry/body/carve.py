"""A carved (arched) top, Les Paul style: a flat plateau, a fall, a flat rim.

The top stays at its full height (Z = 0) over a plateau round the
pickups, the bridge and the neck pocket, and falls from the plateau's
edge to a flat rim ``rim`` wide along the body's edge, ``height`` below
the plateau: a smoothstep, so the fall leaves the plateau and meets the
rim level with them (the recurve). How far a point lies down the fall
starts as its distance from the plateau against its distance from the
rim's inner edge (exact Euclidean distance transforms on a ``CELL``
grid), then is relaxed toward a harmonic field (``RELAX_PASSES``
over-relaxed passes with the plateau and the rim held), which smooths
away the creases the ratio leaves where the nearest edge changes.

The drop is read back by bilinear interpolation, so asking for it
anywhere is quick. Past the body's edge the rim carries on for ``band``
(the cutter's room to finish it); beyond that the drop is 0, the blank
left whole.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import BodyGeometryError
from ..primitives import Point2D

CELL = 2.0
"""The distance grid's spacing, in mm."""

_FAR = 1e20

EDGE_FALL = 3.0
"""The shortest fall left between a kept flat area and an ``edge_rim``, in
mm."""

PLATEAU_EDGE_FALL = 12.0
"""The shortest fall left between the plateau and an ``edge_rim``, in mm:
where the plateau runs along the edge (a Les Paul's cutaway, beside the
neck pocket) the top would otherwise drop its whole height in a few mm,
a wall; only the ``keep`` areas (a pickup's ring) stay flat nearer."""

RELAX_PASSES = 40
"""Over-relaxed smoothing passes over the fall."""

RELAX_FACTOR = 1.7
"""The over-relaxation factor."""


@dataclass(frozen=True, slots=True)
class CarvedTop:
    """The carved top's shape over the body.

    Args:
        outline: The body's outline.
        plateau: The flat area at full height (it may reach past the
            outline, as round a neck pocket opening onto the horns).
        height: How far the rim lies below the plateau, in mm.
        rim: The flat rim's width along the body's edge, in mm.
        band: How far past the edge the rim level carries on, in mm.
        keep: Areas kept flat however near the edge (but ``EDGE_FALL``
            clear of its ``edge_rim``): a pickup's ring, the bridge. The
            plateau itself stays ``PLATEAU_EDGE_FALL`` clear of it.
        fall: The fall's width aimed for: where the plateau (or a kept
            area) comes nearer the edge than ``rim`` and this, the rim
            narrows, to ``edge_rim`` at worst, so the fall is never
            squeezed into the rim.
        edge_rim: The rim kept all round however close the plateau or a
            kept area comes (a binding's channel or a roundover sits on
            it); nothing is held flat within ``EDGE_FALL`` of it.

    Raises:
        BodyGeometryError: For a height or rim that is not positive, or
            a plateau or outline of fewer than three points.
    """

    outline: tuple[Point2D, ...]
    plateau: tuple[Point2D, ...]
    height: float
    rim: float
    band: float = 12.0
    keep: tuple[tuple[Point2D, ...], ...] = ()
    fall: float = 25.0
    edge_rim: float = 0.0
    x0: float = field(init=False)
    y0: float = field(init=False)
    drops: tuple[tuple[float, ...], ...] = field(init=False, repr=False)
    outside: tuple[tuple[float, ...], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.outline) < 3 or len(self.plateau) < 3:
            raise BodyGeometryError("A carved top needs an outline and a plateau.")
        for name, value in (("height", self.height), ("rim", self.rim)):
            if not math.isfinite(value) or value <= 0.0:
                raise BodyGeometryError(f"The carved top's {name} must be positive.")
        xs = [p.x for p in self.outline]
        ys = [p.y for p in self.outline]
        x0 = min(xs) - self.band - 2.0 * CELL
        y0 = min(ys) - self.band - 2.0 * CELL
        columns = math.ceil((max(xs) + self.band + 2.0 * CELL - x0) / CELL) + 1
        rows = math.ceil((max(ys) + self.band + 2.0 * CELL - y0) / CELL) + 1
        inside = _fill(self.outline, x0, y0, columns, rows)
        plateau = _fill(self.plateau, x0, y0, columns, rows)
        held = [[False] * columns for _ in range(rows)]
        for area in self.keep:
            if len(area) >= 3:
                extra = _fill(area, x0, y0, columns, rows)
                held = [
                    [a or b for a, b in zip(row, more, strict=True)]
                    for row, more in zip(held, extra, strict=True)
                ]
        to_outside = _distances([[not cell for cell in row] for row in inside])
        to_inside = _distances(inside)
        # The edge's own strip (a binding's), a grid cell wider so it reads
        # at rim level all across, stays at rim level: nothing is held flat
        # within it and EDGE_FALL of it, and the plateau keeps
        # PLATEAU_EDGE_FALL clear of it so the fall has room.
        edge_rim = self.edge_rim + CELL if self.edge_rim > 0.0 else 0.0
        flat = [
            [
                (
                    plateau[j][i]
                    and not (
                        inside[j][i] and to_outside[j][i] < edge_rim + PLATEAU_EDGE_FALL
                    )
                )
                or (
                    held[j][i]
                    and not (
                        inside[j][i]
                        and edge_rim > 0.0
                        and to_outside[j][i] < edge_rim + EDGE_FALL
                    )
                )
                for i in range(columns)
            ]
            for j in range(rows)
        ]
        to_plateau = _distances(flat)
        # How far down the fall each cell lies (0 plateau, 1 rim); the
        # falling cells are relaxed, the rest held.
        share = [[0.0] * columns for _ in range(rows)]
        falling: list[tuple[int, int]] = []
        for j in range(rows):
            for i in range(columns):
                if not inside[j][i]:
                    share[j][i] = 1.0
                    continue
                if flat[j][i]:
                    continue
                fall = to_plateau[j][i]
                # Where the plateau comes nearer the edge than the rim
                # and a whole fall, the rim narrows (to nothing at
                # worst) so the fall keeps what room there is.
                room = fall + to_outside[j][i]
                rim = min(max(self.rim, edge_rim), max(edge_rim, room - self.fall))
                left = to_outside[j][i] - rim
                if left <= 0.0:
                    share[j][i] = 1.0
                    continue
                share[j][i] = fall / (fall + left)
                if 0 < i < columns - 1 and 0 < j < rows - 1:
                    falling.append((j, i))
        for _ in range(RELAX_PASSES):
            for j, i in falling:
                average = (
                    share[j][i - 1]
                    + share[j][i + 1]
                    + share[j - 1][i]
                    + share[j + 1][i]
                ) / 4.0
                value = share[j][i] + RELAX_FACTOR * (average - share[j][i])
                share[j][i] = min(1.0, max(0.0, value))
        drops: list[tuple[float, ...]] = []
        for j in range(rows):
            row: list[float] = []
            for i in range(columns):
                if inside[j][i]:
                    t = share[j][i]
                    row.append(self.height * t * t * (3.0 - 2.0 * t))
                elif to_inside[j][i] <= self.band:
                    # The rim's level past the edge (the plateau's reach
                    # past it, round a neck pocket's mouth, too: it is all
                    # waste), so the edge reads at rim level.
                    row.append(self.height)
                else:
                    row.append(0.0)
            drops.append(tuple(row))
        object.__setattr__(self, "x0", x0)
        object.__setattr__(self, "y0", y0)
        object.__setattr__(self, "drops", tuple(drops))
        object.__setattr__(self, "outside", tuple(tuple(row) for row in to_inside))

    def drop_at(self, x: float, y: float) -> float:
        """Return how far the top lies below the plateau at ``(x, y)``."""
        return _bilinear(self.drops, (x - self.x0) / CELL, (y - self.y0) / CELL, 0.0)

    def outside_at(self, x: float, y: float) -> float:
        """Return about how far ``(x, y)`` lies outside the outline (0 inside)."""
        return _bilinear(
            self.outside, (x - self.x0) / CELL, (y - self.y0) / CELL, math.inf
        )

    def surface_rows(self, spacing: float) -> list[list[tuple[float, float, float]]]:
        """Return the top as rows of ``(x, y, z)`` points ``spacing`` apart.

        Over the body's bounds and a margin, for a surface fitted through
        them (the FreeCAD model's).
        """
        xs = [p.x for p in self.outline]
        ys = [p.y for p in self.outline]
        left, right = min(xs) - 5.0, max(xs) + 5.0
        bottom, top = min(ys) - 5.0, max(ys) + 5.0
        columns = math.ceil((right - left) / spacing) + 1
        rows = math.ceil((top - bottom) / spacing) + 1
        return [
            [
                (
                    left + (right - left) * i / (columns - 1),
                    bottom + (top - bottom) * j / (rows - 1),
                    -self.drop_at(
                        left + (right - left) * i / (columns - 1),
                        bottom + (top - bottom) * j / (rows - 1),
                    ),
                )
                for i in range(columns)
            ]
            for j in range(rows)
        ]


def _bilinear(
    grid: tuple[tuple[float, ...], ...], fx: float, fy: float, beyond: float
) -> float:
    """Return ``grid`` read at fractional cell ``(fx, fy)``, ``beyond`` off it."""
    columns, rows = len(grid[0]), len(grid)
    if not (0.0 <= fx <= columns - 1 and 0.0 <= fy <= rows - 1):
        return beyond
    i, j = min(int(fx), columns - 2), min(int(fy), rows - 2)
    tx, ty = fx - i, fy - j
    low = grid[j][i] + (grid[j][i + 1] - grid[j][i]) * tx
    high = grid[j + 1][i] + (grid[j + 1][i + 1] - grid[j + 1][i]) * tx
    return low + (high - low) * ty


def _fill(
    polygon: tuple[Point2D, ...], x0: float, y0: float, columns: int, rows: int
) -> list[list[bool]]:
    """Return which grid cells' centres lie inside ``polygon`` (by scanlines)."""
    cells = [[False] * columns for _ in range(rows)]
    edges = list(zip(polygon, (*polygon[1:], polygon[0]), strict=True))
    for j in range(rows):
        y = y0 + j * CELL
        crossings = sorted(
            a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y)
            for a, b in edges
            if (a.y <= y < b.y) or (b.y <= y < a.y)
        )
        for start, end in zip(crossings[0::2], crossings[1::2], strict=False):
            first = max(0, math.ceil((start - x0) / CELL))
            last = min(columns - 1, math.floor((end - x0) / CELL))
            for i in range(first, last + 1):
                cells[j][i] = True
    return cells


def _distances(sources: list[list[bool]]) -> list[list[float]]:
    """Return each cell's exact distance to the nearest source cell, in mm.

    Felzenszwalb and Huttenlocher's separable squared-distance transform:
    down the columns, then along the rows.
    """
    rows, columns = len(sources), len(sources[0])
    squared = [[0.0 if cell else _FAR for cell in row] for row in sources]
    for i in range(columns):
        column = _transform([squared[j][i] for j in range(rows)])
        for j in range(rows):
            squared[j][i] = column[j]
    return [[math.sqrt(value) * CELL for value in _transform(row)] for row in squared]


def _transform(values: list[float]) -> list[float]:
    """Return the 1D squared-distance transform of ``values``."""
    count = len(values)
    hull = [0] * count
    bounds = [0.0] * (count + 1)
    top = 0
    bounds[0], bounds[1] = -math.inf, math.inf
    for q in range(1, count):
        while True:
            p = hull[top]
            crossing = ((values[q] + q * q) - (values[p] + p * p)) / (2.0 * (q - p))
            if crossing > bounds[top] or top == 0:
                break
            top -= 1
        top += 1
        hull[top] = q
        bounds[top] = crossing
        bounds[top + 1] = math.inf
    result = [0.0] * count
    k = 0
    for q in range(count):
        while bounds[k + 1] < q:
            k += 1
        p = hull[k]
        result[q] = (q - p) * (q - p) + values[p]
    return result


def plateau_round(
    features: list[tuple[tuple[Point2D, ...], float]], samples: int = 32
) -> tuple[Point2D, ...]:
    """Return the plateau round ``features``, drawn in straight lines and arcs.

    Each feature comes with its own margin; the plateau is the convex
    hull of every feature point's margin circle (straight sides, arcs at
    the corners), its tail end (+X) a half circle as wide as the plateau,
    reaching on past the features, so the fall starts from a clean line
    with no bumps.
    """
    points = [
        Point2D(
            p.x + margin * math.cos(2.0 * math.pi * k / samples),
            p.y + margin * math.sin(2.0 * math.pi * k / samples),
        )
        for feature, margin in features
        for p in feature
        for k in range(samples)
    ]
    if len(points) < 3:
        raise BodyGeometryError("A carved top needs features to keep flat.")
    hull = _convex_hull(points)
    # The tail end: a half circle as wide as the plateau, placed so it
    # holds the hull's own tail corners.
    low = min(p.y for p in hull)
    high = max(p.y for p in hull)
    middle, cap = (low + high) / 2.0, (high - low) / 2.0
    centre_x = max(
        p.x - math.sqrt(max(0.0, cap * cap - (p.y - middle) ** 2)) for p in hull
    )
    return _convex_hull(
        [
            *hull,
            *(
                Point2D(
                    centre_x + cap * math.cos(math.pi * (k / samples - 0.5)),
                    middle + cap * math.sin(math.pi * (k / samples - 0.5)),
                )
                for k in range(samples + 1)
            ),
        ]
    )


def _convex_hull(points: list[Point2D]) -> tuple[Point2D, ...]:
    """Return the convex hull, counter-clockwise (Andrew's monotone chain)."""
    ordered = sorted(set((p.x, p.y) for p in points))

    def cross(
        o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
    ) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0.0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0.0:
            upper.pop()
        upper.append(p)
    return tuple(Point2D(x, y) for x, y in lower[:-1] + upper[:-1])
