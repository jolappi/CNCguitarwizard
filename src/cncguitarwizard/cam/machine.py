"""A part's programs turned a quarter to fit the machine's travel.

Every part is planned lying along the machine's X (sideways), its length
across the operator. A machine whose X travel is shorter than a part is
long (a 750 x 1000 mm one and an 870 mm neck blank, say) cuts it along Y
instead: ``fitted_to_machine`` turns all of that part's programs a
quarter about the work zero, so the stock is turned the same way on the
table and nothing else changes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..geometry.primitives import Point2D
from .gcode import Setup
from .parameters import MachiningParameters
from .toolpath import Move, Toolpath


@dataclass(frozen=True, slots=True)
class MachineFit:
    """How a part's programs lie on the machine.

    Args:
        setups: The programs, turned when they had to be.
        outlines: Each program's preview outline, turned with it.
        turned: Whether they run along the machine's Y.
        span: How far the tool travels in X and Y, as they now lie.
        fits: Whether that is within the machine's travel; ``None`` when
            the travel is not known.
    """

    setups: tuple[Setup, ...]
    outlines: tuple[tuple[Point2D, ...], ...]
    turned: bool
    span: tuple[float, float]
    fits: bool | None


def program_span(setups: Sequence[Setup]) -> tuple[float, float]:
    """Return how far the tool travels in X and in Y over ``setups``.

    Every position the programs visit counts, the work zero and the
    dowels checked at the start included.

    Args:
        setups: One part's programs.

    Returns:
        The X and Y extent, in mm.
    """
    xs = [0.0]
    ys = [0.0]
    for setup in setups:
        for x, y in setup.reference_points:
            xs.append(x)
            ys.append(y)
        for path in setup.toolpaths:
            for move in path.moves:
                xs.append(move.x)
                ys.append(move.y)
    return max(xs) - min(xs), max(ys) - min(ys)


def fitted_to_machine(
    setups: Sequence[Setup],
    outlines: Sequence[tuple[Point2D, ...]],
    parameters: MachiningParameters,
) -> MachineFit:
    """Return a part's programs lying the way they fit the machine.

    Sideways, along X, as planned, whenever they fit
    (``machine_x_travel`` and ``machine_y_travel``; an empty one limits
    nothing); turned a quarter, along Y, when only that way fits. When
    neither does they stay sideways, and each program's notes say so.

    Args:
        setups: One part's programs, in running order.
        outlines: Each program's preview outline.
        parameters: The machine's travel.

    Returns:
        The programs and outlines as they lie, and how.
    """
    span_x, span_y = program_span(setups)
    if _within(span_x, span_y, parameters):
        fits = (
            None
            if parameters.machine_x_travel is None
            and parameters.machine_y_travel is None
            else True
        )
        return MachineFit(tuple(setups), tuple(outlines), False, (span_x, span_y), fits)
    if _within(span_y, span_x, parameters):
        note = (
            f"Turned a quarter to fit the machine's {_travel(parameters)} "
            f"travel: the part runs along Y ({span_x:.0f} mm), the stock turned "
            "with it on the table (its X along the machine's Y, its Y along "
            "the machine's -X); the work zero stays where it was."
        )
        return MachineFit(
            tuple(_turned(setup, note) for setup in setups),
            tuple(
                tuple(Point2D(_negated(point.y), point.x) for point in outline)
                for outline in outlines
            ),
            True,
            (span_y, span_x),
            True,
        )
    note = (
        f"Too big for the machine's {_travel(parameters)} travel either way: "
        f"it needs {span_x:.0f} x {span_y:.0f} mm."
    )
    return MachineFit(
        tuple(replace(setup, notes=(note, *setup.notes)) for setup in setups),
        tuple(outlines),
        False,
        (span_x, span_y),
        False,
    )


def _within(span_x: float, span_y: float, parameters: MachiningParameters) -> bool:
    """Return whether spans of X and Y fit the machine's travel."""
    x_travel = parameters.machine_x_travel
    y_travel = parameters.machine_y_travel
    return (x_travel is None or span_x <= x_travel) and (
        y_travel is None or span_y <= y_travel
    )


def _travel(parameters: MachiningParameters) -> str:
    """Return the machine's travel as words, e.g. ``"750 x 1000 mm"``."""

    def axis(value: float | None) -> str:
        return "?" if value is None else f"{value:g}"

    return (
        f"{axis(parameters.machine_x_travel)} x {axis(parameters.machine_y_travel)} mm"
    )


def _turned(setup: Setup, note: str) -> Setup:
    """Return ``setup`` turned a quarter counter-clockwise about its zero.

    The part's X runs along the machine's Y and its Y along the
    machine's -X, the dowels with it; ``note`` heads its notes.
    """
    return replace(
        setup,
        toolpaths=tuple(
            Toolpath(
                path.name,
                tuple(
                    Move(_negated(move.y), move.x, move.z, move.rapid, move.feed)
                    for move in path.moves
                ),
            )
            for path in setup.toolpaths
        ),
        notes=(note, *setup.notes),
        reference_points=tuple((_negated(y), x) for x, y in setup.reference_points),
    )


def _negated(value: float) -> float:
    """Return ``-value``, but never -0.0 (written as ``-0.000``)."""
    return 0.0 - value
