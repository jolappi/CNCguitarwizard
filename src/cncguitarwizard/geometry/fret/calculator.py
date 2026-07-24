"""Equal-temperament fret position calculations."""

from __future__ import annotations

import math

from .fret_position import FretPosition


class FretCalculator:
    """Calculate fret positions using the equal-temperament formula."""

    @staticmethod
    def calculate(scale_length: float, fret_count: int) -> list[FretPosition]:
        """Calculate fret positions for a scale length.

        Args:
            scale_length: Nut-to-bridge length in millimetres.
            fret_count: Number of frets to calculate.

        Returns:
            Calculated fret positions in ascending fret-number order.
        """
        positions: list[FretPosition] = []

        for number in range(1, fret_count + 1):
            remaining_scale = scale_length / math.pow(2.0, number / 12.0)
            distance_from_nut = scale_length - remaining_scale
            positions.append(
                FretPosition(number, distance_from_nut, remaining_scale)
            )

        return positions
