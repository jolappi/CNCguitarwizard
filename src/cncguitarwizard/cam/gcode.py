"""GRBL-flavoured G-code output for one machining setup."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import PROJECT_NAME, __version__
from .parameters import MachiningParameters
from .toolpath import Move, Toolpath


@dataclass(frozen=True, slots=True)
class Setup:
    """Every toolpath cut with one tool while the stock is fixtured one way.

    Args:
        name: Short identifier, also used for the output file stem.
        description: One line shown in the G-code header.
        toolpaths: Operations in cutting order.
        notes: Operator instructions written as header comments.
    """

    name: str
    description: str
    toolpaths: tuple[Toolpath, ...]
    notes: tuple[str, ...] = ()

    def cutting_length(self) -> float:
        """Return the total feed-move length in millimetres."""
        return sum(path.cutting_length() for path in self.toolpaths)

    def rapid_length(self) -> float:
        """Return the total rapid-move length in millimetres."""
        return sum(path.rapid_length() for path in self.toolpaths)

    def estimated_minutes(self, parameters: MachiningParameters) -> float:
        """Return a rough run time from path lengths and nominal feeds."""
        cutting = 0.0
        for path in self.toolpaths:
            previous: Move | None = None
            for move in path.moves:
                if previous is not None and not move.rapid and move.feed:
                    distance = (
                        (move.x - previous.x) ** 2
                        + (move.y - previous.y) ** 2
                        + (move.z - previous.z) ** 2
                    ) ** 0.5
                    cutting += distance / move.feed
                previous = move
        return cutting + self.rapid_length() / parameters.rapid_rate


class GRBLWriter:
    """Render a ``Setup`` as absolute, millimetre G-code for GRBL.

    Only ``G0`` and ``G1`` are emitted — arcs and helices are already
    sampled into short lines — so the output runs on any GRBL build
    without arc support and reads back into a simulator trivially.
    Coordinates are written to three decimals and words are omitted
    when unchanged.
    """

    def render(self, setup: Setup, parameters: MachiningParameters) -> str:
        """Return the complete program for one setup."""
        lines = [
            f"({PROJECT_NAME} {__version__})",
            f"(Setup: {_comment(setup.description)})",
            (
                f"(Tool: {parameters.tool_diameter:.3f} mm end mill, "
                f"S{parameters.spindle_speed:.0f}, F{parameters.feed_rate:.0f}, "
                f"plunge F{parameters.plunge_rate:.0f}, "
                f"step-down {parameters.step_down:.3f} mm)"
            ),
            "(Work zero: X/Y at index pin 1, Z at stock top)",
        ]
        lines.extend(f"({_comment(note)})" for note in setup.notes)
        lines.extend(
            [
                "G21",
                "G90",
                "G17",
                "G94",
                f"G0 Z{parameters.safe_height:.3f}",
                "(Start over index pin 1 - check the work zero here)",
                "G0 X0.000 Y0.000",
                f"M3 S{parameters.spindle_speed:.0f}",
            ]
        )
        state = _WordState(initial_z=parameters.safe_height)
        for path in setup.toolpaths:
            lines.append(f"(-- {_comment(path.name)} --)")
            for move in path.moves:
                rendered = state.render(move)
                if rendered is not None:
                    lines.append(rendered)
        lines.extend(
            [
                "M5",
                f"G0 Z{parameters.safe_height:.3f}",
                "(Return over index pin 1)",
                "G0 X0.000 Y0.000",
                "M2",
                "",
            ]
        )
        return "\n".join(lines)


class _WordState:
    """Track the last written words so unchanged ones can be omitted."""

    def __init__(self, *, initial_z: float) -> None:
        # The program starts parked over the work origin at the safe height.
        self._x: str | None = "0.000"
        self._y: str | None = "0.000"
        self._z: str | None = f"{initial_z:.3f}"
        self._feed: str | None = None

    def render(self, move: Move) -> str | None:
        """Return the move's line, or ``None`` if it changes nothing."""
        words = ["G0" if move.rapid else "G1"]
        x, y, z = (f"{value:.3f}" for value in (move.x, move.y, move.z))
        if x != self._x:
            words.append(f"X{x}")
            self._x = x
        if y != self._y:
            words.append(f"Y{y}")
            self._y = y
        if z != self._z:
            words.append(f"Z{z}")
            self._z = z
        if not move.rapid and move.feed is not None:
            feed = f"{move.feed:.0f}"
            if feed != self._feed:
                words.append(f"F{feed}")
                self._feed = feed
        if len(words) == 1:
            return None
        return " ".join(words)


def _comment(text: str) -> str:
    """Strip characters that would terminate a G-code comment early."""
    return text.replace("(", "[").replace(")", "]")
