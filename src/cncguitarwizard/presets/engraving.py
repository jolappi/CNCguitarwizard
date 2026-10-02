"""A decorative scroll pattern engraved into the body's top, laid out at random.

The pattern is Design by Jone's surface design (``pintakuviodesignbyjone``):
one motif of five arcs — a broad swirl, a curl and a small tip rolling
out of it, a hook and a long sweep — scattered over the top, each copy
turned one of the drawing's two ways (``MOTIF_TURNS``). Here the
copies are placed at random from a seed (``engraving_lines``): the same
seed always gives the same pattern. Every arc is cut back to where the
top may be engraved (``EngravingArea``).
"""

from __future__ import annotations

import bisect
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from ..cam.planar import offset_polygon
from ..geometry.primitives import Point2D


@dataclass(frozen=True, slots=True)
class MotifArc:
    """One arc of the motif, relative to the motif's swirl centre.

    Args:
        dx: Arc centre's X offset from the swirl's centre, in mm.
        dy: Its Y offset, in mm.
        radius: Arc radius, in mm.
        start: Start angle, in degrees, anticlockwise from +X.
        end: End angle, in degrees (the arc runs anticlockwise to it).
    """

    dx: float
    dy: float
    radius: float
    start: float
    end: float


MOTIF: tuple[MotifArc, ...] = (
    MotifArc(0.0, 0.0, 61.87, 31.922, 134.358),
    MotifArc(24.725, 23.416, 29.121, 21.642, 192.982),
    MotifArc(64.97, 41.257, 16.296, 29.481, 189.827),
    MotifArc(91.747, 39.741, 31.853, 261.57, 336.332),
    MotifArc(113.608, 86.609, 81.469, 221.417, 274.133),
)
"""The motif's five arcs, measured off the drawing (its unturned copies)."""

MOTIF_TURNS = (90.0, 0.0)
"""The two ways the drawing turns its copies, in degrees, given a quarter
turn: the drawing stands upright, its long side along the neck."""

ROW_STEP = 0.25
"""Row spacing of the precomputed crossings the area is tested by, in mm."""

ARC_STEP = 1.0
"""Spacing of the points an arc is engraved through, in mm."""

MIN_LINE = 3.0
"""Shortest piece of an arc worth engraving once it is cut back, in mm."""

NEAREST = 0.5
"""How near two copies' swirl centres may come, as a fraction of the
spacing: the drawing's copies cross and overlap freely."""

PLACEMENT_TRIES = 30
"""Darts thrown per copy placed when scattering the copies."""


@dataclass(frozen=True, slots=True)
class EngravingArea:
    """Where the top may be engraved.

    Args:
        outline: The body's outline; the area is ``margin`` inside it.
        margin: How far in from the body's edge the engraving stays.
        keep_out: Polygons to stay ``clearance`` clear of (cavities, the
            pickguard, the bridge, contours).
        holes: Circles ``(centre, radius)`` to stay ``clearance`` clear of.
        clearance: The gap kept round everything in ``keep_out`` and
            ``holes``.
    """

    outline: tuple[Point2D, ...]
    margin: float
    keep_out: tuple[tuple[Point2D, ...], ...]
    holes: tuple[tuple[Point2D, float], ...]
    clearance: float

    def allows(self) -> AreaTest:
        """Return a test of whether a point may be engraved."""
        inside = _Rows.of(offset_polygon(self.outline, self.margin, inward=True))
        grown = tuple(
            _Rows.of(offset_polygon(polygon, self.clearance, inward=False))
            for polygon in self.keep_out
            if len(polygon) >= 3
        )
        return AreaTest(inside, grown, self.holes, self.clearance)


@dataclass(frozen=True, slots=True)
class _Rows:
    """A polygon as its edge crossings on rows ``ROW_STEP`` apart.

    A point is tested on the row nearest it (to within ``ROW_STEP / 2``),
    by counting the crossings left of it: quick however many points the
    polygon has.
    """

    bottom: float
    left: float
    right: float
    crossings: tuple[tuple[float, ...], ...]

    @classmethod
    def of(cls, polygon: Sequence[Point2D]) -> _Rows:
        ys = [p.y for p in polygon]
        bottom = min(ys)
        rows = math.ceil((max(ys) - bottom) / ROW_STEP) + 1
        crossings: list[list[float]] = [[] for _ in range(rows)]
        for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
            low, high = (a, b) if a.y <= b.y else (b, a)
            first = math.ceil((low.y - bottom) / ROW_STEP)
            last = math.floor((high.y - bottom) / ROW_STEP)
            for row in range(max(first, 0), min(last, rows - 1) + 1):
                y = bottom + row * ROW_STEP
                if low.y <= y < high.y:
                    t = (y - low.y) / (high.y - low.y)
                    crossings[row].append(low.x + (high.x - low.x) * t)
        xs = [p.x for p in polygon]
        return cls(
            bottom, min(xs), max(xs), tuple(tuple(sorted(row)) for row in crossings)
        )

    def holds(self, point: Point2D) -> bool:
        if not self.left <= point.x <= self.right:
            return False
        row = round((point.y - self.bottom) / ROW_STEP)
        if not 0 <= row < len(self.crossings):
            return False
        return bisect.bisect(self.crossings[row], point.x) % 2 == 1


@dataclass(frozen=True, slots=True)
class AreaTest:
    """Whether a point lies where the top may be engraved (see ``EngravingArea``)."""

    inside: _Rows
    keep_out: tuple[_Rows, ...]
    holes: tuple[tuple[Point2D, float], ...]
    clearance: float

    def __call__(self, point: Point2D) -> bool:
        if not self.inside.holds(point):
            return False
        if any(polygon.holds(point) for polygon in self.keep_out):
            return False
        return all(
            math.hypot(point.x - centre.x, point.y - centre.y) > radius + self.clearance
            for centre, radius in self.holes
        )


def engraving_lines(
    area: EngravingArea, seed: int, spacing: float
) -> tuple[tuple[Point2D, ...], ...]:
    """Return the pattern's lines over ``area``, laid out from ``seed``.

    Copies of the motif are scattered so each reaches the area, one per
    ``spacing`` squared of the area's bounds (the drawing's density at
    the default) and no two swirl centres nearer than ``NEAREST`` times
    ``spacing``, each turned one of the ``MOTIF_TURNS``. Each arc is
    sampled ``ARC_STEP`` apart and cut back to the pieces inside the area
    at least ``MIN_LINE`` long. A copy that would crowd more than
    ``MAX_CLUSTER`` lines together (see ``_Crowding``) is passed over for
    another; at the end every line standing alone, or in a stray group of
    a few short ones (see ``_Crowding.without_lone_lines``), is dropped.

    Args:
        area: Where the top may be engraved.
        seed: Chooses the layout; the same seed gives the same lines.
        spacing: About how far apart the copies are, in mm.

    Returns:
        The engraved lines, each an open polyline.
    """
    allows = area.allows()
    xs = [p.x for p in area.outline]
    ys = [p.y for p in area.outline]
    left, right, bottom, top = min(xs), max(xs), min(ys), max(ys)
    rng = random.Random(seed)
    count = math.ceil((right - left) * (top - bottom) / (spacing * spacing))
    centres: list[Point2D] = []
    crowding = _Crowding()
    for _ in range(count * PLACEMENT_TRIES):
        if len(centres) >= count:
            break
        turn = MOTIF_TURNS[int(rng.random() * len(MOTIF_TURNS))]
        # Where the swirl's centre may go so the copy reaches the area.
        low_x, high_x, low_y, high_y = _motif_bounds(turn)
        x0, x1 = left - high_x, right - low_x
        y0, y1 = bottom - high_y, top - low_y
        centre = Point2D(x0 + (x1 - x0) * rng.random(), y0 + (y1 - y0) * rng.random())
        if any(
            math.hypot(centre.x - c.x, centre.y - c.y) < NEAREST * spacing
            for c in centres
        ):
            continue
        pieces = [
            piece
            for arc in MOTIF
            for piece in _pieces(_turned_arc(arc, centre, turn), allows)
        ]
        if crowding.adds(pieces):
            centres.append(centre)
    return crowding.without_lone_lines()


MAX_CLUSTER = 10
"""Most lines that may pass through one ``CLUSTER_CELL``-wide square and
the eight round it."""

CLUSTER_CELL = 10.0
"""Side of the grid's squares lines are counted in, in mm."""

LONE_GAP = 10.0
"""How near two lines must come to belong together, in mm."""

MIN_GROUP = 40.0
"""Least length of lines, all told, a group of them must have to stay, in
mm: a smaller group is a stray mark."""


class _Crowding:
    """The lines laid so far, on a grid, to keep clusters thin.

    Each ``CLUSTER_CELL`` square knows which lines pass through it; a
    block of three by three squares may hold at most ``MAX_CLUSTER``
    lines.
    """

    def __init__(self) -> None:
        self.lines: list[tuple[Point2D, ...]] = []
        self.cells: dict[tuple[int, int], set[int]] = {}

    @staticmethod
    def _cell(point: Point2D) -> tuple[int, int]:
        return (math.floor(point.x / CLUSTER_CELL), math.floor(point.y / CLUSTER_CELL))

    def adds(self, pieces: Sequence[tuple[Point2D, ...]]) -> bool:
        """Add ``pieces`` (one copy's lines) unless they crowd; return whether."""
        first = len(self.lines)
        touched: dict[tuple[int, int], set[int]] = {}
        for offset, piece in enumerate(pieces):
            for point in piece:
                touched.setdefault(self._cell(point), set()).add(first + offset)
        around = {
            (i + di, j + dj)
            for i, j in touched
            for di in (-1, 0, 1)
            for dj in (-1, 0, 1)
        }
        for i, j in around:
            block: set[int] = set()
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    cell = (i + di, j + dj)
                    block |= self.cells.get(cell, set()) | touched.get(cell, set())
            if len(block) > MAX_CLUSTER:
                return False
        self.lines += pieces
        for cell, ids in touched.items():
            self.cells.setdefault(cell, set()).update(ids)
        return True

    def without_lone_lines(self) -> tuple[tuple[Point2D, ...], ...]:
        """Return the lines less those standing alone.

        Lines that come within ``LONE_GAP`` of each other belong together;
        a group of one line, or shorter than ``MIN_GROUP`` all told (a
        stray mark), is dropped.
        """
        points: dict[tuple[int, int], list[tuple[int, Point2D]]] = {}
        for index, line in enumerate(self.lines):
            for point in line:
                points.setdefault(self._cell(point), []).append((index, point))
        reach = math.ceil(LONE_GAP / CLUSTER_CELL)
        group = list(range(len(self.lines)))

        def root(index: int) -> int:
            while group[index] != index:
                group[index] = group[group[index]]
                index = group[index]
            return index

        for (i, j), here in points.items():
            for di in range(-reach, reach + 1):
                for dj in range(-reach, reach + 1):
                    for other, near in points.get((i + di, j + dj), ()):
                        for index, point in here:
                            if (
                                other != index
                                and root(other) != root(index)
                                and math.hypot(near.x - point.x, near.y - point.y)
                                <= LONE_GAP
                            ):
                                group[root(other)] = root(index)
        members: dict[int, list[int]] = {}
        for index in range(len(self.lines)):
            members.setdefault(root(index), []).append(index)
        kept = sorted(
            index
            for indices in members.values()
            if len(indices) > 1
            and sum(_length(self.lines[i]) for i in indices) >= MIN_GROUP
            for index in indices
        )
        return tuple(self.lines[index] for index in kept)


def _motif_bounds(turn: float) -> tuple[float, float, float, float]:
    """Return how far the motif turned ``turn`` reaches from its swirl's centre.

    As ``(least x, most x, least y, most y)``.
    """
    points = [p for arc in MOTIF for p in _turned_arc(arc, Point2D(0.0, 0.0), turn)]
    return (
        min(p.x for p in points),
        max(p.x for p in points),
        min(p.y for p in points),
        max(p.y for p in points),
    )


def _turned_arc(arc: MotifArc, centre: Point2D, turn: float) -> list[Point2D]:
    """Return ``arc``'s points, the motif turned ``turn`` degrees at ``centre``."""
    cosine, sine = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    cx = centre.x + arc.dx * cosine - arc.dy * sine
    cy = centre.y + arc.dx * sine + arc.dy * cosine
    sweep = (arc.end - arc.start) % 360.0
    count = max(2, math.ceil(math.radians(sweep) * arc.radius / ARC_STEP))
    points = []
    for index in range(count + 1):
        angle = math.radians(arc.start + turn + sweep * index / count)
        points.append(
            Point2D(
                cx + arc.radius * math.cos(angle), cy + arc.radius * math.sin(angle)
            )
        )
    return points


def _pieces(points: Sequence[Point2D], allows: AreaTest) -> list[tuple[Point2D, ...]]:
    """Return the runs of ``points`` inside the area, ``MIN_LINE`` or longer."""
    pieces: list[tuple[Point2D, ...]] = []
    run: list[Point2D] = []
    for point in (*points, None):
        if point is not None and allows(point):
            run.append(point)
            continue
        if len(run) >= 2 and _length(run) >= MIN_LINE:
            pieces.append(tuple(run))
        run = []
    return pieces


def _length(points: Sequence[Point2D]) -> float:
    return sum(
        math.hypot(b.x - a.x, b.y - a.y)
        for a, b in zip(points, points[1:], strict=False)
    )
