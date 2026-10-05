"""A neck-through body: a centre block of the neck blank and two glued wings.

The neck blank runs on through the body as a centre block ``width`` wide
(the body's outline between the two glue lines ``Y = +-width / 2``); the
wings are the outline beyond them, cut from their own blanks and glued
to the block's sides. Each part is cut from a blank a little larger than
it, so whatever reaches past a glue line (a cavity, a carve, a
roundover) is cut there into the part's waste and the profile then
trims it off: the glue faces stay square.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, point_in_polygon
from .body_solid import BodySolid, outlines_overlap
from .hardware import BridgeMounting, Cavity, DrilledHole, RearCavity
from .outline import TracedOutline

_EPSILON = 1e-9


def split_by_line(
    polygon: Sequence[Point2D], level: float, keep_above: bool
) -> list[tuple[Point2D, ...]]:
    """Return the pieces of ``polygon`` on one side of the line ``Y = level``.

    ``keep_above`` keeps ``Y >= level``, else ``Y <= level``. Unlike a
    single clipping pass, a polygon crossing the line more than twice
    (a deep cutaway) comes back as separate pieces, not one joined by
    zero-width bridges along the line. The pieces keep the polygon's
    winding; their edges on the line are the cut.
    """
    sign = 1.0 if keep_above else -1.0
    points = list(polygon)
    if len(points) >= 2 and points[0] == points[-1]:
        points.pop()
    count = len(points)

    def side(point: Point2D) -> float:
        value = sign * (point.y - level)
        # On the line counts as inside, so a crossing is never doubled.
        return value if abs(value) > _EPSILON else _EPSILON

    # The boundary with every crossing inserted: (point, kind) where kind
    # is "in" (inside vertex), "enter" or "exit" (a crossing).
    walk: list[tuple[Point2D, str]] = []
    for index in range(count):
        a, b = points[index], points[(index + 1) % count]
        sa, sb = side(a), side(b)
        if sa > 0.0:
            walk.append((a, "in"))
        if (sa > 0.0) != (sb > 0.0):
            t = (level - a.y) / (b.y - a.y)
            crossing = Point2D(a.x + (b.x - a.x) * t, level)
            walk.append((crossing, "exit" if sa > 0.0 else "enter"))
    crossings = [index for index, (_, kind) in enumerate(walk) if kind != "in"]
    if not crossings:
        return [tuple(points)] if side(points[0]) > 0.0 else []
    # Rotate so the walk starts at a crossing into the kept side.
    start = next(index for index in crossings if walk[index][1] == "enter")
    walk = walk[start:] + walk[:start]
    chains: list[list[Point2D]] = []
    for point, kind in walk:
        if kind == "enter":
            chains.append([point])
        else:
            chains[-1].append(point)
    # Along the line the polygon's inside runs between alternate
    # crossings: each chain's exit pairs with the other end of its run,
    # where another chain enters.
    ends = sorted(
        (chain[point_index].x, chain_index, point_index == 0)
        for chain_index, chain in enumerate(chains)
        for point_index in (0, -1)
    )
    partner: dict[int, int] = {}
    for first, second in zip(ends[0::2], ends[1::2], strict=True):
        (_, chain_a, enters_a), (_, chain_b, enters_b) = first, second
        if enters_a == enters_b:
            raise BodyGeometryError(
                "The outline crosses a glue line in a way it cannot be split along."
            )
        exiting, entering = (chain_b, chain_a) if enters_a else (chain_a, chain_b)
        partner[exiting] = entering
    pieces: list[tuple[Point2D, ...]] = []
    used: set[int] = set()
    for first_chain in range(len(chains)):
        if first_chain in used:
            continue
        piece: list[Point2D] = []
        current = first_chain
        while current not in used:
            used.add(current)
            piece.extend(chains[current])
            current = partner[current]
        pieces.append(_tidy(piece))
    return [piece for piece in pieces if len(piece) >= 3 and abs(_area(piece)) > 1.0]


def _tidy(points: list[Point2D]) -> tuple[Point2D, ...]:
    """Return ``points`` without repeats."""
    tidy: list[Point2D] = []
    for point in points:
        if not tidy or math.hypot(point.x - tidy[-1].x, point.y - tidy[-1].y) > 1e-7:
            tidy.append(point)
    if (
        len(tidy) > 1
        and math.hypot(tidy[0].x - tidy[-1].x, tidy[0].y - tidy[-1].y) <= 1e-7
    ):
        tidy.pop()
    return tuple(tidy)


def _area(points: Sequence[Point2D]) -> float:
    """Return the signed area (positive counter-clockwise)."""
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


def _inside_point(polygon: Sequence[Point2D]) -> Point2D:
    """Return a point inside ``polygon`` (the middle of a horizontal run)."""
    ys = sorted(p.y for p in polygon)
    for fraction in (0.5, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9):
        y = ys[0] + (ys[-1] - ys[0]) * fraction
        xs = sorted(
            a.x + (b.x - a.x) * (y - a.y) / (b.y - a.y)
            for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True)
            if (a.y <= y < b.y) or (b.y <= y < a.y)
        )
        if len(xs) >= 2:
            return Point2D((xs[0] + xs[1]) / 2.0, y)
    return polygon[0]


def strip(
    polygon: Sequence[Point2D], low: float, high: float
) -> list[tuple[Point2D, ...]]:
    """Return the pieces of ``polygon`` between ``Y = low`` and ``Y = high``."""
    return [
        piece
        for part in split_by_line(polygon, high, keep_above=False)
        for piece in split_by_line(part, low, keep_above=True)
    ]


@dataclass(frozen=True, slots=True)
class BodyPart:
    """One piece of a neck-through body.

    Args:
        name: ``"Block"``, or the wing's name (``"Wing_bass"``,
            ``"Wing_treble"``, a second piece ``..._2``).
        outline: The part's outline (its glue edges on a glue line).
        edge_outline: The outline its edge finishes follow: the body's
            outline carried on ``reach`` past each glue line into the
            part's waste, so a roundover or binding runs right across the
            glue line and the glue face stays square.
    """

    name: str
    outline: tuple[Point2D, ...]
    edge_outline: tuple[Point2D, ...]


@dataclass(frozen=True, slots=True)
class NeckThrough:
    """A neck-through body split along its two glue lines.

    Args:
        width: The centre block's width (the glue lines at ``+-width / 2``),
            or ``None`` for a one-piece instrument: the block is the whole
            body and there are no wings.
        block: The centre block: the body's outline between the glue lines.
        wings: The wings beyond them, each a ``BodyPart``.
        front_x: Where the body first meets the neck's sides, along X:
            the neck's back has reached the body's thickness there.
        plan: The neck blank's whole plan: the neck and headstock joined
            to the block.
    """

    width: float | None
    block: BodyPart
    wings: tuple[BodyPart, ...]
    front_x: float
    plan: tuple[Point2D, ...]

    @property
    def one_piece(self) -> bool:
        """Whether the neck and the whole body are one piece (no wings)."""
        return self.width is None

    @property
    def parts(self) -> tuple[BodyPart, ...]:
        """Return the block and the wings."""
        return (self.block, *self.wings)


def neck_through(
    outline: Sequence[Point2D],
    width: float | None,
    head: Sequence[Point2D],
    sides: tuple[Sequence[Point2D], Sequence[Point2D]],
    bass_sign: float,
    reach: float,
) -> NeckThrough:
    """Split a body ``outline`` into a centre block ``width`` wide and wings.

    ``head`` is the neck's plan from the nut's +Y corner round the
    headstock to its -Y corner; ``sides`` the neck's two sides, (+Y, -Y),
    each a line from the nut to a point well inside the body. ``reach`` is how
    far an edge finish is carried past a glue line (see
    ``BodyPart.edge_outline``). A ``width`` of ``None`` makes the whole
    body the block: a one-piece instrument, cut with its neck from one
    blank.

    Raises:
        BodyGeometryError: For a block no wider than the neck where it
            enters the body, a body the glue lines leave no block or no
            wings, or a block in pieces.
    """
    points = tuple(outline)
    if _area(points) < 0.0:
        points = tuple(reversed(points))
    if width is None:
        half = math.inf
        blocks = [points]
    else:
        half = width / 2.0
        blocks = (
            strip(points, -half, half) if math.isfinite(half) and half > 0.0 else []
        )
    if len(blocks) != 1:
        raise BodyGeometryError(
            "The neck-through block must be one piece of the body: "
            f"the glue lines at +-{half:.1f} mm cut it into {len(blocks)}."
        )
    (block,) = blocks
    high = _meet(block, sides[0])
    low = _meet(block, sides[1])
    neck_half = max(abs(high[1].y), abs(low[1].y))
    if half <= neck_half + 1.0:
        raise BodyGeometryError(
            f"The neck-through block ({2.0 * half:.1f} mm) must be wider than the "
            f"neck where it enters the body ({2.0 * neck_half:.1f} mm)."
        )
    if width is None:
        (block_edge,) = blocks
    else:
        (block_edge,) = [
            piece
            for piece in strip(points, -half - reach, half + reach)
            if point_in_polygon(_inside_point(block), piece)
        ]
    wings: list[BodyPart] = []
    for sign in (1.0, -1.0) if width is not None else ():
        name = "Wing_bass" if sign == bass_sign else "Wing_treble"
        pieces = split_by_line(points, sign * half, keep_above=sign > 0.0)
        edges = split_by_line(points, sign * (half - reach), keep_above=sign > 0.0)
        for number, piece in enumerate(pieces, start=1):
            inside = _inside_point(piece)
            (edge,) = [e for e in edges if point_in_polygon(inside, e)]
            wings.append(
                BodyPart(f"{name}_{number}" if number > 1 else name, piece, edge)
            )
    if width is not None and not wings:
        raise BodyGeometryError("The neck-through block leaves the body no wings.")
    # Round the back from where the -Y side meets the block (counter-
    # clockwise) to where the +Y side does, then the neck's +Y side to the
    # nut, round the headstock and back down its -Y side.
    count = len(block)
    around = [low[1]]
    index = (low[0] + 1) % count
    while True:
        around.append(block[index])
        if index == high[0]:
            break
        index = (index + 1) % count
    around.append(high[1])
    return NeckThrough(
        width,
        BodyPart("Block", block, block_edge),
        tuple(wings),
        _front_x(block, neck_half),
        _tidy([*around, *head]),
    )


def _meet(block: Sequence[Point2D], side: Sequence[Point2D]) -> tuple[int, Point2D]:
    """Return where a neck side, from the nut on, first meets the block.

    ``(index, point)``: the block edge it crosses (from ``block[index]``)
    and the crossing.
    """
    count = len(block)
    for a, b in zip(side, side[1:], strict=False):
        best: tuple[float, int, Point2D] | None = None
        for index in range(count):
            c, d = block[index], block[(index + 1) % count]
            denominator = (b.x - a.x) * (d.y - c.y) - (b.y - a.y) * (d.x - c.x)
            if abs(denominator) < 1e-12:
                continue
            t = ((c.x - a.x) * (d.y - c.y) - (c.y - a.y) * (d.x - c.x)) / denominator
            u = ((c.x - a.x) * (b.y - a.y) - (c.y - a.y) * (b.x - a.x)) / denominator
            if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 and (best is None or t < best[0]):
                best = (t, index, Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
        if best is not None:
            return best[1], best[2]
    raise BodyGeometryError("The neck does not reach the neck-through block.")


def _front_x(block: Sequence[Point2D], neck_half_width: float) -> float:
    """Return the least X where the block's outline lies within the neck's width."""
    xs = []
    for a, b in zip(block, (*block[1:], block[0]), strict=True):
        for t in (i / 20.0 for i in range(21)):
            x, y = a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t
            if abs(y) <= neck_half_width:
                xs.append(x)
    return min(xs)


def _circle(x: float, y: float, radius: float) -> tuple[Point2D, ...]:
    return tuple(
        Point2D(
            x + radius * math.cos(2.0 * math.pi * k / 16),
            y + radius * math.sin(2.0 * math.pi * k / 16),
        )
        for k in range(16)
    )


def body_part(body: BodySolid, part: BodyPart) -> BodySolid:
    """Return the part of a neck-through ``body`` cut from ``part``'s blank.

    It carries every feature that reaches into the part (one reaching
    past a glue line is cut whole, its far side in the part's waste), a
    carve and contours whole (their surfaces are the body's), the
    engraving's lines within the part's ``edge_outline``, and edge
    finishes along that outline; it is not checked again (``checked``).
    """
    outline = part.outline

    def reaches(points: Sequence[Point2D]) -> bool:
        return len(points) >= 3 and outlines_overlap(tuple(points), outline)

    def hole_reaches(hole: DrilledHole) -> bool:
        return reaches(_circle(hole.center_x, hole.center_y, hole.diameter / 2.0))

    def cavity(item: Cavity | None) -> Cavity | None:
        return item if item is not None and reaches(item.outline) else None

    def rear(item: RearCavity | None) -> RearCavity | None:
        return item if item is not None and reaches(item.cover_recess.outline) else None

    mounting = body.bridge_mounting
    if (
        not any(
            hole_reaches(
                DrilledHole(
                    "Pivot",
                    pivot.x,
                    pivot.y,
                    mounting.pivot_hole_diameter,
                    mounting.pivot_hole_depth,
                )
            )
            for pivot in mounting.pivot_holes
        )
        and cavity(mounting.sustain_block_cavity) is None
    ):
        mounting = BridgeMounting(
            mounting.reference_x, pivot_stud_spacing=None, has_sustain_block=False
        )
    engraving = body.engraving
    if engraving is not None:
        edge = part.edge_outline
        runs: list[tuple[Point2D, ...]] = []
        for line in engraving.lines:
            run: list[Point2D] = []
            for point in line:
                if point_in_polygon(point, edge):
                    run.append(point)
                    continue
                if len(run) >= 2:
                    runs.append(tuple(run))
                run = []
            if len(run) >= 2:
                runs.append(tuple(run))
        # A relief's shapes that reach the part, whole (one inside another
        # reaches it too), renumbered.
        kept = [
            index
            for index, shape in enumerate(engraving.pockets)
            if reaches(shape.outline)
        ]
        renumbered: dict[int | None, int | None] = {
            old: new for new, old in enumerate(kept)
        }
        pockets = tuple(
            replace(shape, within=renumbered.get(shape.within))
            for shape in (engraving.pockets[index] for index in kept)
        )
        engraving = (
            replace(engraving, lines=tuple(runs), pockets=pockets)
            if runs or pockets
            else None
        )
    return replace(
        body,
        outline=TracedOutline(outline),
        neck_pocket=cavity(body.neck_pocket),
        bridge_pickup=cavity(body.bridge_pickup),
        neck_pickup=cavity(body.neck_pickup),
        bridge_mounting=mounting,
        control_cavity=rear(body.control_cavity),
        switch_cavity=rear(body.switch_cavity),
        battery_cavity=rear(body.battery_cavity),
        extra_cavities=tuple(c for c in body.extra_cavities if reaches(c.outline)),
        holes=tuple(h for h in body.holes if hole_reaches(h)),
        through_cavities=tuple(c for c in body.through_cavities if reaches(c.outline)),
        extra_rear_cavities=tuple(
            r for r in body.extra_rear_cavities if reaches(r.cover_recess.outline)
        ),
        rear_holes=tuple(h for h in body.rear_holes if hole_reaches(h)),
        control_top_cavities=tuple(
            c for c in body.control_top_cavities if reaches(c.outline)
        ),
        control_back_marks=tuple(h for h in body.control_back_marks if hole_reaches(h)),
        control_top_marks=tuple(h for h in body.control_top_marks if hole_reaches(h)),
        contours=tuple(c for c in body.contours if reaches(c.region())),
        truss_rod_access=cavity(body.truss_rod_access),
        wire_channels=tuple(c for c in body.wire_channels if reaches(c.outline)),
        # Drilled by hand through the glued body, not in a part's blank.
        wire_holes=(),
        side_holes=(),
        wire_notes=(),
        engraving=engraving,
        edge_outline=part.edge_outline,
        checked=False,
    )
