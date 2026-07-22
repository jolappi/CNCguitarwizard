"""
Fret position calculations.
"""

from dataclasses import dataclass
from math import pow


TWELFTH_ROOT_OF_TWO = pow(2.0, 1.0 / 12.0)


@dataclass(slots=True, frozen=True)
class FretPosition:
    """Represents a single fret."""

    number: int
    distance_from_nut: float
    remaining_scale: float


class FretCalculator:
    """Calculates fret positions using the equal temperament formula."""

    @staticmethod
    def calculate(scale_length: float, fret_count: int) -> list[FretPosition]:

        positions: list[FretPosition] = []

        for fret in range(1, fret_count + 1):

            remaining = scale_length / pow(
                TWELFTH_ROOT_OF_TWO,
                fret,
            )

            distance = scale_length - remaining

            positions.append(
                FretPosition(
                    number=fret,
                    distance_from_nut=distance,
                    remaining_scale=remaining,
                )
            )

        return positions
