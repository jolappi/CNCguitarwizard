"""G-code output for one machining setup, in the controller's dialect."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import PROJECT_NAME, __version__
from .parameters import MachiningParameters, PostProcessor
from .toolpath import Move, Toolpath

REVIEW_REQUIRED_NOTE = (
    "REVIEW REQUIRED: simulate and air-cut this program, checking the "
    "work zero, tool, clamps and machine travel, before cutting stock"
)
"""Every program's second header line: generated G-code is never ready to
cut on its own word; the operator checks it and starts the machine."""


@dataclass(frozen=True, slots=True)
class Setup:
    """Every toolpath cut with one tool while the stock is fixtured one way.

    Args:
        name: Short identifier; the program's file name begins with it
            (``program_stem``).
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
        fixture: How the stock is held, e.g. ``"Body top face up on the
            index pins"``: setups one after another with the same fixture,
            tool and work zero can run as one program
            (``combined_setups``). Anything done by hand between two
            programs (dowels put in, inlays glued) gives the later one
            another fixture; ``None`` for a setup never run with another.
    """

    name: str
    description: str
    toolpaths: tuple[Toolpath, ...]
    notes: tuple[str, ...] = ()
    reference_points: tuple[tuple[float, float], ...] = ()
    tool: MachiningParameters | None = None
    work_zero: str | None = None
    fixture: str | None = None

    def cutting_length(self) -> float:
        """Return the total feed-move length in millimetres."""
        return sum(path.cutting_length() for path in self.toolpaths)

    def rapid_length(self) -> float:
        """Return the total rapid-move length in millimetres."""
        return sum(path.rapid_length() for path in self.toolpaths)

    def estimated_minutes(self, parameters: MachiningParameters) -> float:
        """Return a rough run time from path lengths and nominal feeds.

        With a Z lift speed, the rapids straight up and down are timed at
        it, as the writer feeds them: the form's (``parameters``), which the
        writer takes for every program, a part's own tool or not.
        """
        lift_rate = parameters.z_lift_rate
        parameters = self.tool or parameters
        cutting = 0.0
        lifting = 0.0
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
                elif (
                    previous is not None
                    and move.rapid
                    and lift_rate > 0.0
                    and (move.x, move.y) == (previous.x, previous.y)
                ):
                    lifting += abs(move.z - previous.z)
                previous = move
        rapids = (self.rapid_length() - lifting) / parameters.rapid_rate
        if lifting > 0.0:
            rapids += lifting / lift_rate
        return cutting + rapids


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
        z_lift_rate: The feed every Z move outside the cut is written at
            (a lift, a move back down to just above the work), as ``G1``;
            ``0`` for rapids (``G0``).
    """

    post_processor: PostProcessor = "grbl"
    spindle_dwell: float = 0.0
    z_lift_rate: float = 0.0

    @property
    def extension(self) -> str:
        """Return the program file's extension, dot included."""
        return ".knc" if self.post_processor == "kosy" else ".nc"

    @classmethod
    def for_parameters(cls, parameters: MachiningParameters) -> GCodeWriter:
        """Return the writer the machining parameters ask for."""
        return cls(
            parameters.post_processor,
            parameters.spindle_dwell,
            parameters.z_lift_rate,
        )

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
            note(REVIEW_REQUIRED_NOTE),
            note(f"Setup: {setup.description}"),
            note(
                f"Tool: {_tool_name(parameters)}, "
                f"S{parameters.spindle_speed:.0f}, F{parameters.feed_rate:.0f}, "
                f"plunge F{parameters.plunge_rate:.0f}, "
                f"step-down {parameters.step_down:.3f} mm"
                + (
                    f", Z lifts F{self.z_lift_rate:.0f}"
                    if self.z_lift_rate > 0.0
                    else ""
                )
            ),
            note(
                f"Work zero: {setup.work_zero}"
                if setup.work_zero
                else "Work zero: X/Y at index pin 1, Z at stock top"
            ),
        ]
        lines.extend(note(text) for text in setup.notes)
        kosy = dialect == "kosy"
        feeds = (parameters.feed_rate, parameters.plunge_rate, self.z_lift_rate)
        if kosy and max(feeds) > KOSY_MAX_FEED:
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

        origin = f"G0 X{number(0.0)} Y{number(0.0)}"
        state = _WordState(
            initial_z=parameters.safe_height,
            decimals=decimals,
            feed_scale=1.0 / 6.0 if kosy else 1.0,
            max_feed=KOSY_MAX_FEED / 6.0 if kosy else None,
            z_lift_feed=self.z_lift_rate or None,
        )
        lines += [
            state.lift(parameters.safe_height),
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
        for path in setup.toolpaths:
            lines.append(note(f"-- {path.name} --"))
            for move in path.moves:
                rendered = state.render(move)
                if rendered is not None:
                    lines.append(rendered)
        lines += [
            "M10 O6.0" if kosy else "M5",
            state.lift(parameters.safe_height),
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


def program_stem(setup: Setup, parameters: MachiningParameters) -> str:
    """Return a program's file name without its extension.

    The setup's name and the tool it is cut with, so the file says which
    cutter to fit: ``Body_top_6mm_flathead``, ``Neck_back_finish_6mm_ballnose``,
    ``Fretboard_inlays_60deg_vbit``.

    Args:
        setup: The program's setup.
        parameters: The machining parameters, whose tool the setup is cut
            with unless it has one of its own (``setup.tool``).

    Returns:
        The file name's stem.
    """
    return f"{setup.name}_{_tool_tag(setup.tool or parameters)}"


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
        z_lift_feed: float | None = None,
    ) -> None:
        self._decimals = decimals
        self._feed_scale = feed_scale
        self._max_feed = max_feed
        self._z_lift_feed = z_lift_feed
        # The program starts parked over the work origin at the safe height.
        self._x: str | None = self._number(0.0)
        self._y: str | None = self._number(0.0)
        self._z: str | None = self._number(initial_z)
        self._feed: str | None = None

    def _number(self, value: float) -> str:
        return f"{value:.{self._decimals}f}"

    def lift(self, z: float) -> str:
        """Return a move straight to height ``z`` outside the cut: a rapid,
        or with a lift feed a feed move at it."""
        self._z = self._number(z)
        if self._z_lift_feed is None:
            return f"G0 Z{self._z}"
        return f"G1 Z{self._z} {self._feed_word(self._z_lift_feed)}".rstrip()

    def render(self, move: Move) -> str | None:
        """Return the move's line, or ``None`` if it changes nothing."""
        x, y, z = (self._number(value) for value in (move.x, move.y, move.z))
        # A rapid straight up or down, outside the cut: at the lift feed.
        straight = (x, y) == (self._x, self._y)
        if move.rapid and straight and self._z_lift_feed is not None:
            return None if z == self._z else self.lift(move.z)
        words = ["G0" if move.rapid else "G1"]
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
            feed = self._feed_word(move.feed)
            if feed:
                words.append(feed)
        if len(words) == 1:
            return None
        return " ".join(words)

    def _feed_word(self, feed: float) -> str:
        """Return the ``F`` word for ``feed``, or nothing when it is the
        feed already in force."""
        value = feed * self._feed_scale
        if self._max_feed is not None:
            value = min(value, self._max_feed)
        text = f"{value:.0f}" if self._feed_scale == 1.0 else f"{value:.1f}"
        if text == self._feed:
            return ""
        self._feed = text
        return f"F{text}"


def _comment(text: str) -> str:
    """Strip characters that would terminate a G-code comment early."""
    return text.replace("(", "[").replace(")", "]")


def _tool_name(parameters: MachiningParameters) -> str:
    """Return the tool as the header names it."""
    if parameters.tool_tip == "vee":
        return (
            f"{parameters.engraving_tool_angle:g} degree V-bit "
            f"({parameters.tool_diameter:.3f} mm wide at full depth)"
        )
    kind = "ball nose" if parameters.tool_tip == "ball" else "end mill"
    return f"{parameters.tool_diameter:.3f} mm {kind}"


def _tool_tag(parameters: MachiningParameters) -> str:
    """Return the tool as a file name says it: ``6mm_flathead``,
    ``3.175mm_ballnose`` or, for a V-bit, its angle: ``60deg_vbit``."""
    if parameters.tool_tip == "vee":
        return f"{parameters.engraving_tool_angle:g}deg_vbit"
    kind = "ballnose" if parameters.tool_tip == "ball" else "flathead"
    return f"{parameters.tool_diameter:g}mm_{kind}"
