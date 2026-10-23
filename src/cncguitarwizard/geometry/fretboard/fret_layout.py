"""Fret-slot segments clipped to a tapered fretboard outline."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator, FretLine, FretPosition
from ..primitives import Line2D, Point2D
from .fretboard import Fretboard
from .skew import FretSkew


@dataclass(frozen=True, slots=True)
class FretLayout:
    """Compose equal-temperament fret slots with a fretboard outline.

    Each slot is perpendicular to the fretboard centerline and terminates
    exactly at the tapered left and right edges — or, with a ``skew``,
    leans along the neck by ``skew.at(x) * y`` as the fretboard's own
    outline does (slanted or fanned frets).

    Args:
        fretboard: Fretboard whose outline bounds every slot.
        fret_count: Number of fret slots to generate.
        skew: How each fret leans (see ``FretSkew``).
        zero_fret: Also a slot on the nut line, for a zero fret
            (``zero_fret_slot``; the board must run on past the nut line
            to hold it). It is not one of ``slots``, which stay fret 1 on.
        slot_end_inset: Blind slots: how far short of the board's edges
            each slot is cut, along it (``cut_slot``); 0 cuts them out
            through the edges. ``slots`` stay the fret lines, edge to
            edge.
        frets_per_octave: Equal steps in each octave (12; more for a
            microtonal board, see ``FretCalculator``).

    Raises:
        FretboardGeometryError: If the fret count or fretboard dimensions
            cannot produce valid manufacturing geometry, or blind slots
            would leave nothing of a slot.
    """

    fretboard: Fretboard
    fret_count: int
    skew: FretSkew = field(default_factory=FretSkew)
    zero_fret: bool = False
    slot_end_inset: float = 0.0
    frets_per_octave: int = 12
    slots: tuple[Line2D, ...] = field(init=False)
    zero_fret_slot: Line2D | None = field(init=False)

    def __post_init__(self) -> None:
        """Validate inputs and construct all bounded fret-slot segments."""
        self._validate()

        positions = FretCalculator.calculate(
            self.fretboard.scale_length,
            self.fret_count,
            self.frets_per_octave,
        )
        slots = tuple(
            self._create_slot(FretLine(self.fretboard.centerline, position))
            for position in positions
        )
        object.__setattr__(self, "slots", slots)
        zero = (
            self._create_slot(
                FretLine(
                    self.fretboard.centerline,
                    FretPosition(0, 0.0, self.fretboard.scale_length),
                )
            )
            if self.zero_fret
            else None
        )
        object.__setattr__(self, "zero_fret_slot", zero)
        shortest = min(slot.length for slot in (*slots, *((zero,) if zero else ())))
        if 2.0 * self.slot_end_inset >= shortest:
            raise FretboardGeometryError(
                f"Blind fret slots {self.slot_end_inset:g} mm short of each "
                f"edge leave nothing of a {shortest:.1f} mm slot."
            )

    def cut_slot(self, slot: Line2D) -> Line2D:
        """Return a slot as it is cut: ``slot_end_inset`` short of each edge.

        Args:
            slot: One of ``slots`` or the ``zero_fret_slot``.

        Returns:
            The slot itself when it is cut through the edges.
        """
        return shortened(slot, self.slot_end_inset)

    def _validate(self) -> None:
        """Reject dimensions that cannot form a useful fret layout."""
        values = (
            self.fretboard.scale_length,
            self.fretboard.nut_width,
            self.fretboard.bridge_width,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise FretboardGeometryError(
                "Scale length and fretboard widths must be finite and positive."
            )
        if self.fret_count <= 0:
            raise FretboardGeometryError("Fret count must be greater than zero.")
        if not math.isfinite(self.slot_end_inset) or self.slot_end_inset < 0.0:
            raise FretboardGeometryError(
                "The fret slots' end inset must be finite and non-negative."
            )

    def _create_slot(self, fret_line: FretLine) -> Line2D:
        """Return one fret line clipped to the tapered fretboard."""
        fraction = fret_line.position.distance_from_nut / self.fretboard.scale_length
        width = (
            self.fretboard.nut_width
            + (self.fretboard.bridge_width - self.fretboard.nut_width) * fraction
        )
        half_width = width / 2.0
        direction = fret_line.direction
        location = fret_line.location

        left = Point2D(
            location.x + direction.x * half_width,
            location.y + direction.y * half_width,
        )
        right = Point2D(
            location.x - direction.x * half_width,
            location.y - direction.y * half_width,
        )
        lean = self.skew.at(location.x)
        if lean:
            left = Point2D(left.x + lean * left.y, left.y)
            right = Point2D(right.x + lean * right.y, right.y)
        return Line2D(left, right)


def shortened(line: Line2D, amount: float) -> Line2D:
    """Return ``line`` with ``amount`` taken off each end, along it.

    Args:
        line: The segment to shorten.
        amount: How much comes off each end; 0 leaves it as it is.

    Returns:
        The middle of ``line``.

    Raises:
        FretboardGeometryError: If that leaves nothing of it.
    """
    if amount == 0.0:
        return line
    length = line.length
    if 2.0 * amount >= length:
        raise FretboardGeometryError(
            f"Taking {amount:g} mm off each end leaves nothing of a "
            f"{length:.1f} mm line."
        )
    dx = (line.end.x - line.start.x) / length * amount
    dy = (line.end.y - line.start.y) / length * amount
    return Line2D(
        Point2D(line.start.x + dx, line.start.y + dy),
        Point2D(line.end.x - dx, line.end.y - dy),
    )
