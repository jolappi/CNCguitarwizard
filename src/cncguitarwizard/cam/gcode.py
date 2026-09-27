"""G-code output for one machining setup, in the controller's dialect."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import PROJECT_NAME, __version__
from .parameters import MachiningParameters, PostProcessor
from .toolpath import Move, Toolpath


@dataclass(frozen=True, slots=True)
class Setup:
    """Every toolpath cut with one tool while the stock is fixtured one way.

    Args:
        name: Short identifier, also used for the output file stem.
        description: One line shown in the G-code header.
        toolpaths: Operations in cutting order.
        notes: Operator instructions written as header comments.
        reference_points: Further machine-frame points (the other
            dowels) the program visits at the safe height before the
            spindle starts, so the operator can check the fixture.
        tool: The tool this setup is cut with, when it differs from the
            parameters handed to the writer (multi-tool parts).
        work_zero: Where the X/Y/Z zero is, when it is not index pin 1
            on the stock top (a sheet cover's own centre).
    """

    name: str
    description: str
    toolpaths: tuple[Toolpath, ...]
    notes: tuple[str, ...] = ()
    reference_points: tuple[tuple[float, float], ...] = ()
    tool: MachiningParameters | None = None
    work_zero: str | None = None

    def cutting_length(self) -> float:
        """Return the total feed-move length in millimetres."""
        return sum(path.cutting_length() for path in self.toolpaths)

    def rapid_length(self) -> float:
        """Return the total rapid-move length in millimetres."""
        return sum(path.rapid_length() for path in self.toolpaths)

    def estimated_minutes(self, parameters: MachiningParameters) -> float:
        """Return a rough run time from path lengths and nominal feeds."""
        parameters = self.tool or parameters
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


@dataclass(frozen=True, slots=True)
class GCodeWriter:
    """Render a ``Setup`` as absolute, millimetre G-code for one controller.

    Only ``G0`` and ``G1`` moves are emitted — arcs and helices are
    already sampled into short lines — so every dialect runs it without
    arc support and it reads back into a simulator trivially. Coordinates
    are written to three decimals and words are omitted when unchanged.
    The dialects differ only around the moves:

    * ``grbl`` and ``linuxcnc``: ``( )`` comments, ``G21 G90 G17 G94``,
      ``M3 S…``, a dwell of ``G4 P`` seconds, ``M2`` at the end.
    * ``mach3`` (Mach3/4, UCCNC): the same, but the dwell in milliseconds
      (Mach's default) and ``M30`` at the end.
    * ``marlin``: ``;`` comments (Marlin ignores ``( )`` unless built for
      them), only ``G21 G90``, a ``G4 P`` dwell in milliseconds, and no
      end code.
    * ``fanuc``: ``%`` around the program, an ``O1000`` program number,
      upper-case comments, ``G54`` and ``T1 M6`` before ``S… M3``, a
      ``G4 X`` dwell in seconds and ``M30`` at the end.
    * ``kosy`` (KOSY / nccad, ``.KNC``): two ``_`` lines and ``G90`` to
      start, ``;`` comments, every move with its G word and all of X, Y
      and Z to two decimals, feeds in nccad's units (mm/min ÷ 6, at most
      ``KOSY_MAX_FEED``), the spindle switched on relay 6 (``M10 O6.1`` /
      ``M10 O6.0``, no speed), a ``M30 P`` dwell in 1/18 s and ``G99`` at
      the end.

    Args:
        post_processor: The dialect (see ``MachiningParameters``).
        spindle_dwell: Seconds to wait after the spindle starts; ``0``
            for no dwell.
    """

    post_processor: PostProcessor = "grbl"
    spindle_dwell: float = 0.0

    @property
    def extension(self) -> str:
        """Return the program file's extension, dot included."""
        return ".knc" if self.post_processor == "kosy" else ".nc"

    @classmethod
    def for_parameters(cls, parameters: MachiningParameters) -> GCodeWriter:
        """Return the writer the machining parameters ask for."""
        return cls(parameters.post_processor, parameters.spindle_dwell)

    def render(self, setup: Setup, parameters: MachiningParameters) -> str:
        """Return the complete program for one setup.

        ``setup.tool`` takes precedence over ``parameters`` for the tool
        line, spindle speed, feeds, and safe height.
        """
        dialect = self.post_processor
        note = self._comment
        parameters = setup.tool or parameters
        zero = setup.work_zero or "index pin 1"
        lines: list[str] = []
        if dialect == "kosy":
            lines += ["_", "_"]
        if dialect == "fanuc":
            lines += ["%", f"O1000 {note(PROJECT_NAME + ' ' + setup.name)}"]
        lines += [
            note(f"{PROJECT_NAME} {__version__}"),
            note(f"Setup: {setup.description}"),
            note(
                f"Tool: {parameters.tool_diameter:.3f} mm "
                f"{'ball nose' if parameters.tool_tip == 'ball' else 'end mill'}, "
                f"S{parameters.spindle_speed:.0f}, F{parameters.feed_rate:.0f}, "
                f"plunge F{parameters.plunge_rate:.0f}, "
                f"step-down {parameters.step_down:.3f} mm"
            ),
            note(
                f"Work zero: {setup.work_zero}"
                if setup.work_zero
                else "Work zero: X/Y at index pin 1, Z at stock top"
            ),
        ]
        lines.extend(note(text) for text in setup.notes)
        kosy = dialect == "kosy"
        if kosy and max(parameters.feed_rate, parameters.plunge_rate) > KOSY_MAX_FEED:
            lines.append(
                note(f"Feeds over {KOSY_MAX_FEED:g} mm/min are cut at nccad's F200")
            )
        if kosy:
            lines += ["G90"]
        elif dialect == "marlin":
            lines += ["G21", "G90"]
        else:
            lines += ["G21", "G90", "G17", "G94"]
        if dialect == "fanuc":
            lines += ["G54", "T1 M6"]
        decimals = 2 if kosy else 3

        def number(value: float) -> str:
            return f"{value:.{decimals}f}"

        safe = number(parameters.safe_height)
        origin = f"G0 X{number(0.0)} Y{number(0.0)}"
        lines += [
            f"G0 Z{safe}",
            note(f"Start over {zero} - check the work zero here")
            if setup.work_zero is None
            else note("Start over the work zero - check it here"),
            origin,
        ]
        for index, (x, y) in enumerate(setup.reference_points, start=2):
            lines.append(note(f"Check dowel {index}"))
            lines.append(f"G0 X{number(x)} Y{number(y)}")
        if setup.reference_points:
            lines.append(note("Back over index pin 1"))
            lines.append(origin)
        speed = f"{parameters.spindle_speed:.0f}"
        if kosy:
            lines.append("M10 O6.1")
        elif dialect == "fanuc":
            lines.append(f"S{speed} M3")
        else:
            lines.append(f"M3 S{speed}")
        if self.spindle_dwell > 0.0:
            lines.append(self._dwell())
        state = _WordState(
            initial_z=parameters.safe_height,
            decimals=decimals,
            feed_scale=1.0 / 6.0 if kosy else 1.0,
            max_feed=KOSY_MAX_FEED / 6.0 if kosy else None,
        )
        for path in setup.toolpaths:
            lines.append(note(f"-- {path.name} --"))
            for move in path.moves:
                rendered = state.render(move)
                if rendered is not None:
                    lines.append(rendered)
        lines += [
            "M10 O6.0" if kosy else "M5",
            f"G0 Z{safe}",
            note("Return over index pin 1")
            if setup.work_zero is None
            else note("Return over the work zero"),
            origin,
        ]
        if kosy:
            lines.append("G99")
        elif dialect in ("grbl", "linuxcnc"):
            lines.append("M2")
        elif dialect in ("mach3", "fanuc"):
            lines.append("M30")
        if dialect == "fanuc":
            lines.append("%")
        lines.append("")
        return "\n".join(lines)

    def _comment(self, text: str) -> str:
        """Return ``text`` as a comment line in this dialect."""
        if self.post_processor in ("marlin", "kosy"):
            return f"; {text}"
        cleaned = _comment(text)
        return f"({cleaned.upper() if self.post_processor == 'fanuc' else cleaned})"

    def _dwell(self) -> str:
        """Return the spindle spin-up dwell in this dialect's units."""
        seconds = self.spindle_dwell
        if self.post_processor == "kosy":
            return f"M30 P{seconds * 18.0:.0f}"
        if self.post_processor in ("mach3", "marlin"):
            return f"G4 P{seconds * 1000.0:.0f}"
        if self.post_processor == "fanuc":
            return f"G4 X{seconds:.3f}"
        return f"G4 P{seconds:.3f}"


KOSY_MAX_FEED = 1200.0
"""The fastest feed nccad takes, in mm/min (its F200)."""


GRBLWriter = GCodeWriter
"""The default writer: ``GCodeWriter()`` writes GRBL."""


class _WordState:
    """Track the last written words so unchanged ones can be omitted.

    Coordinates are written to ``decimals`` places; feeds are scaled by
    ``feed_scale`` (a controller's own feed units) and capped at
    ``max_feed`` in those units.
    """

    def __init__(
        self,
        *,
        initial_z: float,
        decimals: int = 3,
        feed_scale: float = 1.0,
        max_feed: float | None = None,
    ) -> None:
        self._decimals = decimals
        self._feed_scale = feed_scale
        self._max_feed = max_feed
        # The program starts parked over the work origin at the safe height.
        self._x: str | None = self._number(0.0)
        self._y: str | None = self._number(0.0)
        self._z: str | None = self._number(initial_z)
        self._feed: str | None = None

    def _number(self, value: float) -> str:
        return f"{value:.{self._decimals}f}"

    def render(self, move: Move) -> str | None:
        """Return the move's line, or ``None`` if it changes nothing."""
        words = ["G0" if move.rapid else "G1"]
        x, y, z = (self._number(value) for value in (move.x, move.y, move.z))
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
            value = move.feed * self._feed_scale
            if self._max_feed is not None:
                value = min(value, self._max_feed)
            feed = f"{value:.0f}" if self._feed_scale == 1.0 else f"{value:.1f}"
            if feed != self._feed:
                words.append(f"F{feed}")
                self._feed = feed
        if len(words) == 1:
            return None
        return " ".join(words)


def _comment(text: str) -> str:
    """Strip characters that would terminate a G-code comment early."""
    return text.replace("(", "[").replace(")", "]")
