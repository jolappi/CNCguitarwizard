"""Decorative patterns engraved into the body's top, laid out at random.

``pattern_lines`` lays out one of ``ENGRAVING_PATTERNS`` from a seed (the
same seed always gives the same pattern), every line cut back to where
the top may be engraved (``EngravingArea``):

* ``scroll`` (``engraving_lines``), Design by Jone's scrolls, below;
* ``evh_stripes``, criss-crossing taped stripes as on Eddie Van Halen's
  "Frankenstrat": straight bands of random widths at random angles, each
  band's two edges engraved and every later band covering the earlier
  ones as tape would;
* ``flame``, wavy lines across the body as in flamed maple;
* ``ripples``, groups of concentric rings, each group covering the ones
  laid before it;
* ``crackle``, the cells of a random Voronoi pattern, as crazed lacquer;
* ``camo``, woodland camouflage as a relief: lobed shapes stretched one
  way, each cleared flat to one of ``CAMO_LEVELS`` depths, a smaller one
  sometimes inside a larger, deeper (``pattern_pockets``);
* ``pinstripe``, a stripe round the body ``PINSTRIPE_INSET`` inside the
  engraving's margin, following the edge as a painted pinstripe does
  (Jackson RR, ESP LTD Alexi Hexed), broken where something is in its way;
* ``drawn``, lines drawn in another program and read back from the body
  editor's SVG template (``drawn_lines``), cut back the same way.

The scroll pattern is Design by Jone's surface design (``pintakuviodesignbyjone``):
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
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import partial
from typing import Literal

from ..cam.planar import offset_polygon
from ..geometry.body.engraving import EngravedPocket
from ..geometry.primitives import Point2D

EngravingPattern = Literal[
    "scroll",
    "evh_stripes",
    "flame",
    "ripples",
    "crackle",
    "camo",
    "pinstripe",
    "drawn",
]

ENGRAVING_PATTERNS: tuple[str, ...] = (
    "scroll",
    "evh_stripes",
    "flame",
    "ripples",
    "crackle",
    "camo",
    "pinstripe",
    "drawn",
)
"""Every pattern, in the order the form offers them."""

STRIPE_WIDTHS = (6.0, 16.0)
"""Narrowest and widest EVH stripe, in mm: wide enough that a V-bit's two
grooves stay apart."""

STRIPE_ANGLES = (0.0, 30.0, 60.0, 90.0, 120.0, 150.0)
"""The directions the stripes lean round, in degrees from the neck."""

STRIPE_SPREAD = 12.0
"""How far a stripe turns off its direction at random, in degrees."""

FLAME_WAVELENGTH = (60.0, 110.0)
"""Shortest and longest wave of the flame lines, in mm."""

FLAME_AMPLITUDE = (1.5, 4.0)
"""Least and most a flame line swings either way, in mm."""

MIN_PATTERN_LINE = 8.0
"""Shortest piece of the other patterns' lines kept, in mm: shorter ones
are stray marks."""

RIPPLE_GAP = 8.0
"""Distance between a ripple group's rings, in mm."""

RIPPLE_RINGS = (2, 6)
"""Fewest and most rings in a ripple group."""

CAMO_SIZE = (0.3, 0.55)
"""Smallest and largest camo blob, its width as a share of the spacing
(half its width before it is stretched)."""

CAMO_STRETCH = (1.2, 2.3)
"""Least and most a camo blob is stretched along its length."""

CAMO_TURN = 25.0
"""How far a camo blob turns off the pattern's direction at random, in
degrees."""

CAMO_LOBES: tuple[tuple[int, float, float], ...] = (
    (2, 0.12, 0.28),
    (3, 0.08, 0.20),
    (4, 0.04, 0.13),
    (5, 0.03, 0.09),
    (6, 0.02, 0.05),
)
"""A camo blob's lobes: each harmonic of its outline (round it, ``k``
times) and the least and most it swells the radius, as a share of it."""

CAMO_COVER = 2.5
"""How many camo shapes are tried for, per the spacing squared of the
area's bounds (as many as fit are laid)."""

CAMO_ARMS = (1, 3)
"""Fewest and most arms a camo shape reaches out with."""

CAMO_ARM_LENGTH = (0.35, 0.8)
"""Shortest and longest arm, as a share of the shape's size."""

CAMO_ARM_WIDTH = (0.25, 0.5)
"""Narrowest and widest arm, in radians round the shape."""

CAMO_INNER = (0.4, 0.6)
"""How big a camo shape started inside another is, as a share of that
one's size."""

CAMO_NEST = 0.25
"""How often a camo shape is tried inside a big one, to lie in it a level
deeper."""

CAMO_PROBE = 4.0
"""Spacing of the points a camo shape is first tried at, in mm."""

CAMO_SHRINK = 0.75
"""How much smaller a camo shape that does not fit is tried again."""

CAMO_SMALLEST = 12.0
"""The narrowest camo shape, its half-width before it is stretched, in mm."""

CAMO_GAP = 3.0
"""Wood left between two camo shapes at one level, between two that do
not overlap, and between one and a shape it lies inside, in mm."""

CAMO_GIVE_UP = 600
"""How many tries in a row may lay no camo shape before the layout stops:
the area is as full as it gets."""

CAMO_KEEP = 0.5
"""How much of a camo shape's outline must show where shapes at other
levels overlap it (the deeper shows)."""

CAMO_LEVELS = 4
"""The levels a camo relief is cut to: ``depth / CAMO_LEVELS`` apart, the
deepest at the engraving's depth (0.5, 1, 1.5 and 2 mm at 2 mm)."""

RELIEF_PATTERNS: frozenset[str] = frozenset({"camo"})
"""The patterns cut as a relief of pockets (``pattern_pockets``), not as
lines."""

PINSTRIPE_INSET = 0.5
"""How far inside the engraving's margin the pinstripe runs, in mm: just
inside, so the whole stripe is in the area."""


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
        level: How far the face lies below the top's full height at a
            point (a stepped or carved top), or ``None`` for a flat top: a
            relief's pockets keep to where it is level.
    """

    outline: tuple[Point2D, ...]
    margin: float
    keep_out: tuple[tuple[Point2D, ...], ...]
    holes: tuple[tuple[Point2D, float], ...]
    clearance: float
    level: Callable[[Point2D], float] | None = None

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


def pattern_lines(
    pattern: str,
    area: EngravingArea,
    seed: int,
    spacing: float,
    drawn: Sequence[Sequence[Point2D]] = (),
) -> tuple[tuple[Point2D, ...], ...]:
    """Return ``pattern``'s lines over ``area``, laid out from ``seed``.

    ``spacing`` sets each pattern's scale: the scroll copies' spacing,
    one stripe per twice its square of the area's bounds, a fifth of
    it between flame lines, a ripple group per its square, a crackle cell
    about its size (the pinstripe takes neither it nor the seed). Pieces
    shorter than ``MIN_PATTERN_LINE`` are left out. A relief pattern
    (``RELIEF_PATTERNS``) has no lines: see ``pattern_pockets``. The
    ``drawn`` pattern is the ``drawn`` lines (``drawn_lines``).

    Raises:
        ValueError: For an unknown pattern.
    """
    if pattern == "scroll":
        return engraving_lines(area, seed, spacing)
    if pattern == "drawn":
        return drawn_lines(drawn, area)
    if pattern not in ENGRAVING_PATTERNS:
        raise ValueError(
            f"Unknown engraving pattern {pattern!r}; use one of "
            f"{', '.join(ENGRAVING_PATTERNS)}."
        )
    if pattern in RELIEF_PATTERNS:
        return ()
    allows = area.allows()
    xs = [p.x for p in area.outline]
    ys = [p.y for p in area.outline]
    bounds = (min(xs), max(xs), min(ys), max(ys))
    rng = random.Random(seed)
    if pattern == "evh_stripes":
        lines = _stripes(bounds, rng, spacing)
    elif pattern == "flame":
        lines = _flame(bounds, rng, spacing)
    elif pattern == "ripples":
        lines = _ripples(bounds, rng, spacing)
    elif pattern == "pinstripe":
        lines = _pinstripe(area)
    else:
        lines = _crackle(bounds, rng, spacing)
    return tuple(
        piece
        for line in lines
        for piece in _pieces(_opened(line, allows), allows)
        if _length(piece) >= MIN_PATTERN_LINE
    )


def drawn_lines(
    lines: Sequence[Sequence[Point2D]], area: EngravingArea
) -> tuple[tuple[Point2D, ...], ...]:
    """Return lines drawn elsewhere, cut back to where the top may be engraved.

    Each is first taken every ``ARC_STEP`` along it (a long straight
    stretch is cut where it crosses a cavity, not only at its ends); a
    line ending where it began is closed. Pieces shorter than ``MIN_LINE``
    are left out.
    """
    allows = area.allows()
    pieces: list[tuple[Point2D, ...]] = []
    for line in lines:
        if len(line) < 2:
            continue
        dense = [line[0]]
        for a, b in zip(line, line[1:]):
            steps = max(1, math.ceil(math.hypot(b.x - a.x, b.y - a.y) / ARC_STEP))
            dense += [
                Point2D(a.x + (b.x - a.x) * k / steps, a.y + (b.y - a.y) * k / steps)
                for k in range(1, steps + 1)
            ]
        pieces += _pieces(_opened(dense, allows), allows)
    return tuple(pieces)


def _opened(line: list[Point2D], allows: AreaTest) -> list[Point2D]:
    """Return a closed line turned to start where the area cuts it.

    So its pieces are not cut again at its seam.
    """
    if len(line) > 2 and line[0] == line[-1]:
        for index, point in enumerate(line[:-1]):
            if not allows(point):
                return [*line[index:-1], *line[: index + 1]]
    return line


Bounds = tuple[float, float, float, float]


def _straight(start: Point2D, end: Point2D) -> list[Point2D]:
    """Return a straight line sampled ``ARC_STEP`` apart."""
    count = max(1, math.ceil(math.hypot(end.x - start.x, end.y - start.y) / ARC_STEP))
    return [
        Point2D(
            start.x + (end.x - start.x) * k / count,
            start.y + (end.y - start.y) * k / count,
        )
        for k in range(count + 1)
    ]


def _runs(
    points: Sequence[Point2D], keep: Callable[[Point2D], bool]
) -> list[list[Point2D]]:
    """Return the runs of ``points`` that ``keep`` accepts."""
    runs: list[list[Point2D]] = []
    run: list[Point2D] = []
    for point in (*points, None):
        if point is not None and keep(point):
            run.append(point)
            continue
        if len(run) >= 2:
            runs.append(run)
        run = []
    return runs


def _stripes(bounds: Bounds, rng: random.Random, spacing: float) -> list[list[Point2D]]:
    """Taped stripes: each band's edges, cut where later bands cover them."""
    left, right, bottom, top = bounds
    reach = math.hypot(right - left, top - bottom)
    count = max(6, math.ceil((right - left) * (top - bottom) / (2.0 * spacing**2)))
    bands: list[tuple[Point2D, tuple[float, float], float]] = []
    for _ in range(count):
        angle = math.radians(
            rng.choice(STRIPE_ANGLES) + rng.uniform(-STRIPE_SPREAD, STRIPE_SPREAD)
        )
        centre = Point2D(rng.uniform(left, right), rng.uniform(bottom, top))
        width = rng.uniform(*STRIPE_WIDTHS)
        bands.append((centre, (math.cos(angle), math.sin(angle)), width))

    def across(
        point: Point2D, band: tuple[Point2D, tuple[float, float], float]
    ) -> float:
        centre, (ux, uy), _ = band
        return (point.x - centre.x) * -uy + (point.y - centre.y) * ux

    lines: list[list[Point2D]] = []
    for index, band in enumerate(bands):
        centre, (ux, uy), width = band
        later = bands[index + 1 :]
        for side in (-1.0, 1.0):
            offset = side * width / 2.0
            start = Point2D(
                centre.x - ux * reach - uy * offset, centre.y - uy * reach + ux * offset
            )
            end = Point2D(
                centre.x + ux * reach - uy * offset, centre.y + uy * reach + ux * offset
            )
            lines += _runs(
                _straight(start, end),
                lambda point: all(
                    abs(across(point, other)) >= other[2] / 2.0 for other in later
                ),
            )
    return lines


def _flame(bounds: Bounds, rng: random.Random, spacing: float) -> list[list[Point2D]]:
    """Wavy lines across the body, neighbours swinging nearly together."""
    left, right, bottom, top = bounds
    gap = max(6.0, spacing / 5.0)
    wavelength = rng.uniform(*FLAME_WAVELENGTH)
    phase = rng.uniform(0.0, 2.0 * math.pi)
    amplitude = rng.uniform(*FLAME_AMPLITUDE)
    lines: list[list[Point2D]] = []
    x = left - FLAME_AMPLITUDE[1]
    while x <= right + FLAME_AMPLITUDE[1]:
        # Each line drifts a little from the last, so they never cross.
        phase += rng.uniform(-0.25, 0.25)
        amplitude = min(
            FLAME_AMPLITUDE[1],
            max(FLAME_AMPLITUDE[0], amplitude + rng.uniform(-0.4, 0.4)),
        )
        steps = max(2, math.ceil((top - bottom) / ARC_STEP))
        lines.append(
            [
                Point2D(
                    x + amplitude * math.sin(2.0 * math.pi * y / wavelength + phase),
                    y,
                )
                for y in (bottom + (top - bottom) * k / steps for k in range(steps + 1))
            ]
        )
        x += gap * rng.uniform(0.8, 1.25)
    return lines


def _ripples(bounds: Bounds, rng: random.Random, spacing: float) -> list[list[Point2D]]:
    """Groups of rings, each covering the groups laid before it."""
    left, right, bottom, top = bounds
    count = max(3, math.ceil((right - left) * (top - bottom) / spacing**2 / 2.0))
    groups: list[tuple[Point2D, float]] = []
    for _ in range(count * PLACEMENT_TRIES):
        if len(groups) >= count:
            break
        centre = Point2D(rng.uniform(left, right), rng.uniform(bottom, top))
        if any(
            math.hypot(centre.x - c.x, centre.y - c.y) < NEAREST * spacing
            for c, _ in groups
        ):
            continue
        rings = rng.randint(*RIPPLE_RINGS)
        groups.append((centre, RIPPLE_GAP * rings))
    lines: list[list[Point2D]] = []
    for index, (centre, outer) in enumerate(groups):
        later = groups[index + 1 :]
        radius = RIPPLE_GAP
        while radius <= outer + 1e-9:
            steps = max(8, math.ceil(2.0 * math.pi * radius / ARC_STEP))
            ring = [
                Point2D(
                    centre.x + radius * math.cos(2.0 * math.pi * k / steps),
                    centre.y + radius * math.sin(2.0 * math.pi * k / steps),
                )
                for k in range(steps + 1)
            ]
            lines += _runs(
                ring,
                lambda point: all(
                    math.hypot(point.x - c.x, point.y - c.y) > r + RIPPLE_GAP / 2.0
                    for c, r in later
                ),
            )
            radius += RIPPLE_GAP
    return lines


@dataclass(frozen=True, slots=True)
class _Blob:
    """One camo shape: a lobed round with arms, stretched along ``angle``
    and turned."""

    centre: Point2D
    angle: float
    stretch: float
    radius: float
    lobes: tuple[tuple[int, float, float], ...]
    arms: tuple[tuple[float, float, float], ...] = ()
    extent: float = field(init=False)
    turn: tuple[float, float] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "turn", (math.cos(self.angle), math.sin(self.angle)))
        # How far it reaches from its centre at most.
        object.__setattr__(
            self,
            "extent",
            self.radius
            * self.stretch
            * (
                1.0
                + sum(swell for _, swell, _ in self.lobes)
                + sum(length for _, length, _ in self.arms)
            ),
        )

    def reach(self, theta: float) -> float:
        """Return the blob's radius at ``theta`` before it is stretched.

        Its lobes swell it all round; each arm ``(direction, length,
        width)`` reaches out round its direction, tapering off.
        """
        swells = sum(
            swell * math.sin(k * theta + phase) for k, swell, phase in self.lobes
        )
        reaches = 0.0
        for direction, length, width in self.arms:
            off = (theta - direction + math.pi) % (2.0 * math.pi) - math.pi
            reaches += length * math.exp(-((off / width) ** 2))
        return self.radius * (1.0 + swells + reaches)

    def outline(self, step: float) -> list[Point2D]:
        """Return its outline, closed, about ``step`` apart."""
        steps = max(
            24, math.ceil(2.0 * math.pi * self.radius * self.stretch * 1.4 / step)
        )
        cos_a, sin_a = math.cos(self.angle), math.sin(self.angle)
        points = []
        for k in range(steps + 1):
            theta = 2.0 * math.pi * k / steps
            reach = self.reach(theta)
            u, v = self.stretch * reach * math.cos(theta), reach * math.sin(theta)
            points.append(
                Point2D(
                    self.centre.x + u * cos_a - v * sin_a,
                    self.centre.y + u * sin_a + v * cos_a,
                )
            )
        return points

    def covers(self, point: Point2D, gap: float) -> bool:
        """Whether ``point`` lies inside it, or within about ``gap`` of it."""
        dx, dy = point.x - self.centre.x, point.y - self.centre.y
        if math.hypot(dx, dy) > self.extent + self.stretch * gap:
            return False
        cos_a, sin_a = self.turn
        u = (dx * cos_a + dy * sin_a) / self.stretch
        v = -dx * sin_a + dy * cos_a
        return math.hypot(u, v) < self.reach(math.atan2(v, u)) + gap


class _Swells:
    """A camo shape's lobes and arms sampled round it once, for its tries.

    ``reach`` is its longest half-length (size times stretch) at the
    first try: the samples are ``CAMO_PROBE`` apart round that, closer on
    the smaller tries.
    """

    def __init__(
        self,
        lobes: tuple[tuple[int, float, float], ...],
        arms: tuple[tuple[float, float, float], ...],
        reach: float,
    ) -> None:
        count = max(24, math.ceil(2.0 * math.pi * reach * 1.4 / CAMO_PROBE))
        thetas = [2.0 * math.pi * k / count for k in range(count)]
        self.cos = [math.cos(theta) for theta in thetas]
        self.sin = [math.sin(theta) for theta in thetas]
        self.lobes = [
            1.0 + sum(swell * math.sin(k * theta + phase) for k, swell, phase in lobes)
            for theta in thetas
        ]
        self.arms = [
            [
                length
                * math.exp(
                    -(
                        (
                            ((theta - direction + math.pi) % (2.0 * math.pi) - math.pi)
                            / width
                        )
                        ** 2
                    )
                )
                for theta in thetas
            ]
            for direction, length, width in arms
        ]

    def probe(
        self,
        centre: Point2D,
        angle: float,
        stretch: float,
        size: float,
        arms: int,
        every: int = 1,
    ) -> list[Point2D]:
        """Return the outline at this size with its first ``arms`` arms.

        Every ``every``-th sample of it.
        """
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        points = []
        for index in range(0, len(self.cos), every):
            cos_t, sin_t = self.cos[index], self.sin[index]
            rho = size * (
                self.lobes[index] + sum(arm[index] for arm in self.arms[:arms])
            )
            u, v = stretch * rho * cos_t, rho * sin_t
            x = centre.x + u * cos_a - v * sin_a
            points.append(Point2D(x, centre.y + u * sin_a + v * cos_a))
        return points


@dataclass(slots=True)
class _Laid:
    """A camo shape laid: its blob, outline (coarsely), level, face, the
    shallower shape it lies wholly inside, and which of its outline's
    points still show (not under a deeper shape)."""

    blob: _Blob
    probe: list[Point2D]
    level: int
    drop: float
    within: int | None
    showing: list[bool]


def pattern_pockets(
    pattern: str, area: EngravingArea, seed: int, spacing: float, depth: float
) -> tuple[EngravedPocket, ...]:
    """Return a relief pattern's pockets over ``area``, laid out from ``seed``.

    ``camo``: lobed shapes ``CAMO_SIZE`` of ``spacing`` wide (at least
    ``CAMO_SMALLEST``), stretched along the pattern's direction, each
    wholly in the area over a level face and ``CAMO_GAP`` clear of the
    others — or that far inside one, and then deeper than it. Each is
    cleared flat to one of ``CAMO_LEVELS`` depths down to ``depth``.
    Empty for a pattern of lines.
    """
    if pattern not in RELIEF_PATTERNS:
        return ()
    return _camo(area, random.Random(seed), spacing, depth)


def _camo(
    area: EngravingArea, rng: random.Random, spacing: float, depth: float
) -> tuple[EngravedPocket, ...]:
    """Woodland camo as a relief: lobed shapes, each to its own level."""
    allows = area.allows()
    level = area.level or (lambda point: 0.0)
    xs = [p.x for p in area.outline]
    ys = [p.y for p in area.outline]
    left, right, bottom, top = min(xs), max(xs), min(ys), max(ys)
    count = max(4, math.ceil((right - left) * (top - bottom) / spacing**2 * CAMO_COVER))
    direction = rng.uniform(0.0, math.pi)
    laid: list[_Laid] = []

    def lay(
        blob: _Blob, outline: Callable[[int], list[Point2D]], shape_level: int
    ) -> bool:
        """Lay the shape at its level if it fits.

        In the area over a level face; ``CAMO_GAP`` clear of the shapes at
        its own level; over or under the others (the deeper shows where
        they overlap) so each keeps ``CAMO_KEEP`` of its outline showing,
        or else ``CAMO_GAP`` clear of them too. ``outline(every)`` is
        every ``every``-th point of its outline, coarsely; every fifth
        first: most tries fail there, quickly.
        """
        reach = max(CAMO_STRETCH) * CAMO_GAP
        nearby = [
            index
            for index, entry in enumerate(laid)
            if math.hypot(
                blob.centre.x - entry.blob.centre.x, blob.centre.y - entry.blob.centre.y
            )
            <= blob.extent + entry.blob.extent + reach
        ]
        sparse = outline(5)
        if not all(allows(point) for point in sparse) or any(
            laid[index].level == shape_level
            and any(laid[index].blob.covers(point, CAMO_GAP) for point in sparse)
            for index in nearby
        ):
            return False
        probe = outline(1)
        if not all(allows(point) for point in probe):
            return False
        # Over a level face (one band of a stepped top, a carve's plateau).
        drop = level(blob.centre)
        if any(abs(level(point) - drop) > 1e-6 for point in probe):
            return False
        hidden = [False] * len(probe)
        updates: list[tuple[int, list[bool]]] = []
        for index in nearby:
            other = laid[index]

            def apart() -> bool:
                return not any(
                    other.blob.covers(point, CAMO_GAP) for point in probe
                ) and not any(blob.covers(point, CAMO_GAP) for point in other.probe)

            if other.level == shape_level:
                if not apart():
                    return False
                continue
            under_other = [other.blob.covers(point, 0.0) for point in probe]
            over_other = [blob.covers(point, 0.0) for point in other.probe]
            if not any(under_other) and not any(over_other):
                # Side by side: no thin wall between them.
                if not apart():
                    return False
                continue
            if other.level > shape_level:
                hidden = [a or b for a, b in zip(hidden, under_other, strict=True)]
            else:
                shows = [
                    a and not b for a, b in zip(other.showing, over_other, strict=True)
                ]
                if sum(shows) < CAMO_KEEP * len(shows):
                    return False
                updates.append((index, shows))
        if hidden.count(False) < CAMO_KEEP * len(probe) or not all(
            allows(point) for point in blob.outline(ARC_STEP)
        ):
            return False
        # Wholly inside a shallower one: cut on from its floor.
        within: int | None = None
        for index in nearby:
            other = laid[index]
            if (
                other.level < shape_level
                and (within is None or other.level > laid[within].level)
                and all(other.blob.covers(point, -CAMO_GAP) for point in probe)
            ):
                within = index
        for index, shows in updates:
            laid[index].showing = shows
        laid.append(
            _Laid(blob, probe, shape_level, drop, within, [not h for h in hidden])
        )
        return True

    misses = 0
    for _ in range(count * PLACEMENT_TRIES):
        # Full, or no room found in a long while.
        if len(laid) >= count or misses >= CAMO_GIVE_UP:
            break
        misses += 1
        laid_before = len(laid)
        centre = Point2D(rng.uniform(left, right), rng.uniform(bottom, top))
        # Now and then one starts inside a big shape not yet at the
        # deepest level, to lie in it a level deeper.
        hosts = [
            entry.blob
            for entry in laid
            if entry.level < CAMO_LEVELS - 1
            and entry.blob.radius >= CAMO_SMALLEST / CAMO_INNER[1] + CAMO_GAP
        ]
        if hosts and rng.random() < CAMO_NEST:
            host = rng.choice(hosts)
            centre = Point2D(
                host.centre.x + rng.uniform(-0.25, 0.25) * host.radius,
                host.centre.y + rng.uniform(-0.25, 0.25) * host.radius,
            )
        if not allows(centre):
            continue
        size = spacing * rng.uniform(*CAMO_SIZE)
        angle = direction + math.radians(rng.uniform(-CAMO_TURN, CAMO_TURN))
        stretch = rng.uniform(*CAMO_STRETCH)
        lobes = tuple(
            (k, rng.uniform(least, most), rng.uniform(0.0, 2.0 * math.pi))
            for k, least, most in CAMO_LOBES
        )
        arms = tuple(
            (
                rng.uniform(0.0, 2.0 * math.pi),
                rng.uniform(*CAMO_ARM_LENGTH),
                rng.uniform(*CAMO_ARM_WIDTH),
            )
            for _ in range(rng.randint(*CAMO_ARMS))
        )
        # Started on a shape, it lies over it, a level deeper at least;
        # wholly inside one, it is shaped after it: smaller, turned and
        # stretched about as it is.
        beneath = [entry for entry in laid if entry.blob.covers(centre, 0.0)]
        lowest = max((entry.level + 1 for entry in beneath), default=0)
        if lowest >= CAMO_LEVELS:
            continue
        shape_level = rng.randint(lowest, CAMO_LEVELS - 1)
        around = [
            entry.blob for entry in beneath if entry.blob.covers(centre, -CAMO_GAP)
        ]
        if around:
            inner = min(around, key=lambda other: other.radius)
            size = min(size, inner.radius * rng.uniform(*CAMO_INNER))
            angle = inner.angle + math.radians(rng.uniform(-10.0, 10.0))
            stretch = inner.stretch * rng.uniform(0.8, 1.0)
            arms = arms[:1]
        # Till it fits, as the gaps fill: with fewer arms (an arm is what
        # most often runs into something), then smaller and rounder. Its
        # lobes and arms round it once, every try then scaled from them.
        size = max(CAMO_SMALLEST, size)
        shape = _Swells(lobes, arms, size * stretch)
        while not any(
            lay(
                _Blob(centre, angle, stretch, size, lobes, arms[:count]),
                partial(shape.probe, centre, angle, stretch, size, count),
                shape_level,
            )
            for count in range(len(arms), -1, -1)
        ):
            if size <= CAMO_SMALLEST:
                break
            size = max(CAMO_SMALLEST, size * CAMO_SHRINK)
            stretch = max(CAMO_STRETCH[0], stretch * CAMO_SHRINK**0.5)
        if len(laid) > laid_before:
            misses = 0
    return tuple(
        EngravedPocket(
            tuple(entry.blob.outline(ARC_STEP)[:-1]),
            depth * (entry.level + 1) / CAMO_LEVELS,
            entry.drop,
            entry.within,
        )
        for entry in laid
    )


def _pinstripe(area: EngravingArea) -> list[list[Point2D]]:
    """Return the stripe round the body, just inside the margin, closed."""
    stripe = offset_polygon(
        area.outline, area.margin + PINSTRIPE_INSET, inward=True, sample_spacing=1.0
    )
    if len(stripe) < 3:
        return []
    return [[*stripe, stripe[0]]]


def _crackle(bounds: Bounds, rng: random.Random, spacing: float) -> list[list[Point2D]]:
    """The edges of a random Voronoi pattern's cells, each edge once."""
    left, right, bottom, top = bounds
    count = max(4, math.ceil((right - left) * (top - bottom) / spacing**2 * 1.5))
    seeds: list[Point2D] = []
    for _ in range(count * PLACEMENT_TRIES):
        if len(seeds) >= count:
            break
        point = Point2D(rng.uniform(left, right), rng.uniform(bottom, top))
        if all(
            math.hypot(point.x - s.x, point.y - s.y) >= 0.6 * spacing for s in seeds
        ):
            seeds.append(point)
    box = [
        Point2D(left, bottom),
        Point2D(right, bottom),
        Point2D(right, top),
        Point2D(left, top),
    ]
    edges: dict[tuple[tuple[float, float], tuple[float, float]], None] = {}
    for index, here in enumerate(seeds):
        cell = box
        for other in seeds:
            if other is here:
                continue
            cell = _half_plane(cell, here, other)
            if len(cell) < 3:
                break
        for a, b in zip(cell, (*cell[1:], cell[0]), strict=False):
            key_a = (round(a.x, 3), round(a.y, 3))
            key_b = (round(b.x, 3), round(b.y, 3))
            if key_a == key_b:
                continue
            edges[(min(key_a, key_b), max(key_a, key_b))] = None

    def on_box(point: tuple[float, float]) -> bool:
        x, y = point
        return (
            abs(x - left) < 1e-3
            or abs(x - right) < 1e-3
            or abs(y - bottom) < 1e-3
            or abs(y - top) < 1e-3
        )

    return [
        _straight(Point2D(*a), Point2D(*b))
        for a, b in edges
        if not (on_box(a) and on_box(b))
    ]


def _half_plane(
    polygon: Sequence[Point2D], keep: Point2D, other: Point2D
) -> list[Point2D]:
    """Return ``polygon`` cut to the side of the bisector nearer ``keep``."""
    mx, my = (keep.x + other.x) / 2.0, (keep.y + other.y) / 2.0
    nx, ny = other.x - keep.x, other.y - keep.y

    def side(point: Point2D) -> float:
        return (point.x - mx) * nx + (point.y - my) * ny

    clipped: list[Point2D] = []
    for index, current in enumerate(polygon):
        following = polygon[(index + 1) % len(polygon)]
        here, there = side(current), side(following)
        if here <= 0.0:
            clipped.append(current)
        if (here <= 0.0) != (there <= 0.0):
            t = here / (here - there)
            clipped.append(
                Point2D(
                    current.x + (following.x - current.x) * t,
                    current.y + (following.y - current.y) * t,
                )
            )
    return clipped
