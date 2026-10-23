"""Equal-temperament fret position calculations."""

from __future__ import annotations

import math

from ..exceptions import FretboardGeometryError
from .fret_position import FretPosition


class FretCalculator:
    """Calculate fret positions using the equal-temperament formula."""

    @staticmethod
    def calculate(
        scale_length: float, fret_count: int, frets_per_octave: int = 12
    ) -> list[FretPosition]:
        """Calculate fret positions for a scale length.

        Each fret shortens the string by the same ratio, the octave
        divided into ``frets_per_octave`` equal steps: 12 semitones, or a
        microtonal tuning's steps (24 quarter tones, 19, 22, 31...), the
        octave always at half the scale.

        Args:
            scale_length: Nut-to-bridge length in millimetres.
            fret_count: Number of frets to calculate.
            frets_per_octave: Equal steps in each octave.

        Returns:
            Calculated fret positions in ascending fret-number order.

        Raises:
            FretboardGeometryError: For fewer than one fret per octave.
        """
        if frets_per_octave < 1:
            raise FretboardGeometryError("An octave needs at least one fret.")
        positions: list[FretPosition] = []

        for number in range(1, fret_count + 1):
            remaining_scale = scale_length / math.pow(2.0, number / frets_per_octave)
            distance_from_nut = scale_length - remaining_scale
            positions.append(FretPosition(number, distance_from_nut, remaining_scale))

        return positions

    @staticmethod
    def nearest_fret(semitones: int, frets_per_octave: int = 12) -> int:
        """Return the fret nearest ``semitones`` up the string.

        On a 12-per-octave neck the fret itself; with more (or fewer)
        frets per octave the one nearest that pitch, a half step rounding
        up: on a quarter-tone neck semitone 3 is fret 6, the octave fret 24.

        Args:
            semitones: How many semitones up from the open string.
            frets_per_octave: Equal steps in each octave.

        Returns:
            The fret number (0 for the open string).
        """
        return math.floor(semitones * frets_per_octave / 12.0 + 0.5)
