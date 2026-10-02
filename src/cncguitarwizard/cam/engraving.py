"""Engraving cut with a V-bit: the body top's pattern, the headstock's lettering."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace

from ..geometry.body import Engraving
from ..geometry.primitives import Point2D
from .parameters import MachiningParameters
from .toolpath import PathBuilder, Toolpath


def engraving_tool(
    parameters: MachiningParameters, depth: float
) -> MachiningParameters:
    """Return the V-bit's settings: the groove's width at ``depth`` as its size.

    Its feeds are the engraving ones; its step-down is
    ``engraving_step_down``.
    """
    half_angle = math.radians(parameters.engraving_tool_angle / 2.0)
    return replace(
        parameters,
        tool_diameter=2.0 * depth * math.tan(half_angle),
        tool_tip="vee",
        feed_rate=parameters.engraving_feed_rate,
        plunge_rate=min(parameters.plunge_rate, parameters.engraving_feed_rate),
        step_down=parameters.engraving_step_down,
    )


def engraving_path(
    engraving: Engraving,
    to_machine: Callable[[Point2D], Point2D],
    tool: MachiningParameters,
    surface_z: Callable[[Point2D], float] = lambda point: 0.0,
    name: str = "Engraving",
) -> Toolpath:
    """Return one toolpath engraving every line, nearest line next.

    Each line is cut in ``tool.step_down`` passes to the engraving's depth
    below the face, back and forth along it, so the bit only lifts between
    lines. ``surface_z`` is the face's machine Z at a model point (a
    headstock's angled face); the flat stock top's is zero.
    """
    builder = PathBuilder(
        name,
        safe_height=tool.safe_height,
        feed_rate=tool.feed_rate,
        plunge_rate=tool.plunge_rate,
    )
    passes = max(1, math.ceil(engraving.depth / tool.step_down - 1e-9))
    depths = [engraving.depth * (k + 1) / passes for k in range(passes)]
    # Each point as (machine X, Y, the face's Z there).
    lines = [[(to_machine(p), surface_z(p)) for p in line] for line in engraving.lines]
    for line in _ordered(lines):
        start, top = line[0]
        builder.rapid_to(start.x, start.y)
        builder.rapid_down_to(top)
        for index, depth in enumerate(depths):
            run = line if index % 2 == 0 else list(reversed(line))
            builder.plunge_to(run[0][1] - depth)
            for point, face in run[1:]:
                builder.cut_to(point.x, point.y, face - depth)
        builder.retract()
    return builder.build()


_Line = list[tuple[Point2D, float]]


def _ordered(lines: Sequence[_Line]) -> list[_Line]:
    """Return the lines in a short order: each next the one nearest the last end.

    A line is reversed when its far end is the nearer.
    """
    left = list(lines)
    ordered: list[_Line] = []
    at = Point2D(0.0, 0.0)
    while left:
        best = min(
            range(len(left)),
            key=lambda i: min(_gap(at, left[i][0][0]), _gap(at, left[i][-1][0])),
        )
        line = left.pop(best)
        if _gap(at, line[-1][0]) < _gap(at, line[0][0]):
            line = list(reversed(line))
        ordered.append(line)
        at = line[-1][0]
    return ordered


def _gap(a: Point2D, b: Point2D) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)
