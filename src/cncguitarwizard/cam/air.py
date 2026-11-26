"""Feed moves through air run at a feed of their own.

A program goes back through wood it has already cut away: a peck back
down its hole, a link across a pocket's cleared floor, a pass over a
stretch already finished. Those stretches cut nothing, so they can run
faster than the cutting and plunge feeds (``air_feed_rate``).

``air_fed`` follows the cutter down a program's moves over a grid of
heights, the wood under each cell lowered to the cutter wherever it
passes. The wood is unknown until the program cuts it: the stock top is
not assumed anywhere, so a move through wood this program never reached
(a blank thicker than planned, an earlier program's cut) is always wood.
"""

from __future__ import annotations

import math
from dataclasses import replace

from .gcode import Setup
from .parameters import MachiningParameters
from .toolpath import Move, Toolpath

AIR_CLEARANCE = 1.0
"""How far, in mm along the path, a stretch run at the air feed stays
from any wood the cutter meets: the same 1 mm the rapids stop over a
floor already cut (eco mode)."""

AIR_TOLERANCE = 0.05
"""Wood no thicker than this, in mm, counts as air."""

AIR_CELLS_PER_DIAMETER = 6
"""The grid's cells across the cutter's diameter (at most 1 mm each)."""


def air_fed(setup: Setup, parameters: MachiningParameters) -> Setup:
    """Return ``setup`` with its feed moves through air at the air feed.

    A stretch of a feed move runs at ``air_feed_rate`` where the cutter
    meets no wood along it, nor within ``AIR_CLEARANCE`` either side
    along the path: it slows to the cutting or plunge feed before it
    reaches wood. A stretch straight up or down runs no faster than
    ``z_lift_rate``, when that is set. The path itself is unchanged; a
    move only partly through air is split where its feed changes.

    Args:
        setup: The program, every toolpath cut with one tool.
        parameters: The machining form's parameters: their
            ``air_feed_rate`` (``0`` leaves ``setup`` as it is) and
            ``z_lift_rate``, and the tool of a setup that names none.

    Returns:
        The program with its air fed faster, and a header note saying
        so.
    """
    if parameters.air_feed_rate <= 0.0:
        return setup
    stock = _Stock(setup.tool or parameters)
    feeds = (parameters.air_feed_rate, parameters.z_lift_rate)
    return replace(
        setup,
        toolpaths=tuple(_air_fed(path, stock, *feeds) for path in setup.toolpaths),
        notes=(
            *setup.notes,
            f"Air feed F{parameters.air_feed_rate:.0f}: through wood this "
            "program has already cut away",
        ),
    )


class _Stock:
    """The wood under a grid of cells, lowered as the cutter passes.

    A cell holds the highest the wood can be at its centre; one the
    cutter has not yet passed over may hold wood at any height.
    """

    def __init__(self, tool: MachiningParameters) -> None:
        self.cell = min(1.0, tool.tool_diameter / AIR_CELLS_PER_DIAMETER)
        self._tool = tool
        self._radius = tool.tool_diameter / 2.0
        self._heights: dict[tuple[int, int], float] = {}

    def cut(self, x: float, y: float, z: float) -> bool:
        """Lower the wood to the cutter, its tip at ``(x, y, z)``.

        Every cell whose centre is under the cutter, measured from where
        the cutter is (not the nearest cell), is lowered to the cutter's
        surface there.

        Returns:
            Whether the cutter met wood there.
        """
        cell, radius = self.cell, self._radius
        met = False
        for i in range(
            math.ceil((x - radius) / cell), math.floor((x + radius) / cell) + 1
        ):
            across = i * cell - x
            reach = math.sqrt(max(radius * radius - across * across, 0.0))
            for j in range(
                math.ceil((y - reach) / cell), math.floor((y + reach) / cell) + 1
            ):
                surface = z + _lift(self._tool, math.hypot(across, j * cell - y))
                if self._heights.get((i, j), math.inf) > surface + AIR_TOLERANCE:
                    self._heights[(i, j)] = surface
                    met = True
        return met


def _lift(tool: MachiningParameters, distance: float) -> float:
    """Return how far above its tip the cutter's surface is ``distance``
    out from its axis."""
    if tool.tool_tip == "ball":
        radius = tool.tool_diameter / 2.0
        return radius - math.sqrt(max(radius * radius - distance * distance, 0.0))
    if tool.tool_tip == "vee":
        return distance / math.tan(math.radians(tool.engraving_tool_angle) / 2.0)
    return 0.0


def _air_fed(
    path: Toolpath, stock: _Stock, air_feed: float, lift_feed: float
) -> Toolpath:
    """Return ``path`` with its stretches through air at the air feed."""
    # Every feed move sampled at most a cell apart: the move it is on,
    # how far along that move, how far along the path (rapids too), and
    # whether the cutter met wood there.
    samples: list[tuple[int, float, float, bool]] = []
    travelled = 0.0
    previous: Move | None = None
    for index, move in enumerate(path.moves):
        if previous is not None:
            length = _distance(previous, move)
            steps = 0 if move.rapid else max(1, math.ceil(length / stock.cell))
            for step in range(1, steps + 1):
                share = step / steps
                at = _between(previous, move, share)
                met = stock.cut(at.x, at.y, at.z)
                samples.append((index, share, travelled + length * share, met))
            travelled += length
        previous = move
    clear = _clear_of_wood([s[2] for s in samples], [s[3] for s in samples])
    stretches: dict[int, list[tuple[float, bool]]] = {}
    for (index, share, _, _), air in zip(samples, clear, strict=True):
        stretches.setdefault(index, []).append((share, air))

    moves: list[Move] = []
    for index, move in enumerate(path.moves):
        flags = stretches.get(index)
        if flags is None or not any(air for _, air in flags):
            moves.append(move)
            continue
        start = path.moves[index - 1]
        # Each run of samples alike: one move to its last sample.
        for position, (share, air) in enumerate(flags):
            last = position == len(flags) - 1
            if not last and flags[position + 1][1] == air:
                continue
            end = move if last else _between(start, move, share)
            feed = move.feed
            if air:
                straight = (end.x, end.y) == (moves[-1].x, moves[-1].y)
                feed = min(air_feed, lift_feed) if straight and lift_feed else air_feed
            moves.append(Move(end.x, end.y, end.z, False, feed))
    return Toolpath(path.name, tuple(moves))


def _clear_of_wood(positions: list[float], met: list[bool]) -> list[bool]:
    """Return, for each sample, whether no wood is met within
    ``AIR_CLEARANCE`` of it either way along the path."""
    clear = [True] * len(positions)
    last = -math.inf
    for k, position in enumerate(positions):
        if met[k]:
            last = position
        if position - last <= AIR_CLEARANCE:
            clear[k] = False
    following = math.inf
    for k in reversed(range(len(positions))):
        if met[k]:
            following = positions[k]
        if following - positions[k] <= AIR_CLEARANCE:
            clear[k] = False
    return clear


def _distance(start: Move, end: Move) -> float:
    return math.dist((start.x, start.y, start.z), (end.x, end.y, end.z))


def _between(start: Move, end: Move, share: float) -> Move:
    """Return the point ``share`` of the way from ``start`` to ``end``."""
    return Move(
        start.x + (end.x - start.x) * share,
        start.y + (end.y - start.y) * share,
        start.z + (end.z - start.z) * share,
        False,
    )
