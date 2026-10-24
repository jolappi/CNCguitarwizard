"""Scallops: the playing surface hollowed between the frets."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import FretboardGeometryError
from ..primitives import Point3D
from .surface import FretboardSurface

SCALLOP_FLOOR = 1.5
"""The least wood, in mm, a scallop leaves above the glue face under its
deepest point (at the board's edge, where the radius has taken most)."""

SCALLOP_EASE = 0.15
"""How much of a scallop, either end, eases it into the land (its slope
going to 0 there): a circular arc met the land at an angle, a ridge under
the fingers that the loft also overshot."""

SCALLOP_ROWS = 16
"""How many spans the hollowed surface's rows divide each scallop into
(between its lands): enough for its arc to loft smoothly, few enough that
a board scalloped from the nut stays quick to loft."""


@dataclass(frozen=True, slots=True)
class FretboardScallops:
    """The playing surface hollowed between frets, as on a scalloped board.

    Every fret space from ``from_fret`` on to the last fret (0: from the
    nut) is hollowed ``depth`` deep at its middle: a circular arc along the
    neck between the ``land`` left flat either side of each fret line (the
    fret's foot sits on it), eased into the land over ``SCALLOP_EASE`` of
    it at either end, as deep right across the board, so the hollow follows
    the radius. Slanted or fanned frets lean their spaces with
    them.

    Args:
        surface: The radiused playing surface that is hollowed.
        from_fret: The fret the first scalloped space starts at, 0 for the
            nut; the last ends at the last fret.
        depth: How deep each scallop is at its middle, in mm.
        land: How much is left flat either side of a fret line, in mm.

    Raises:
        FretboardGeometryError: For a start outside the frets, a depth not
            finite and positive, a land not finite and non-negative, a space
            too short for its scallop (no more than twice its depth long
            between its lands), or one leaving less than ``SCALLOP_FLOOR``
            under it.
    """

    surface: FretboardSurface
    from_fret: int
    depth: float
    land: float

    def __post_init__(self) -> None:
        """Validate the scallops against the frets and the board."""
        surface = self.surface
        if not 0 <= self.from_fret < surface.fret_count:
            raise FretboardGeometryError(
                f"Scallops start at a fret from 0 (the nut) to "
                f"{surface.fret_count - 1}; {self.from_fret} is not one."
            )
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise FretboardGeometryError("Scallop depth must be finite and positive.")
        if not math.isfinite(self.land) or self.land < 0.0:
            raise FretboardGeometryError(
                "Scallop land must be finite and non-negative."
            )
        for number in self.fret_numbers:
            for side in (-1.0, 1.0):
                start, end = self._space(number, side * self._half_width(number))
                if end - start <= 2.0 * self.depth:
                    raise FretboardGeometryError(
                        f"The space after fret {number} is too short for a "
                        f"{self.depth:g} mm scallop between "
                        f"{self.land:g} mm lands: make it shallower or the "
                        "lands narrower."
                    )
        half = self._half_width(surface.fret_count)
        edge_drop = surface.radius - math.sqrt(surface.radius**2 - half**2)
        floor = surface.center_thickness - edge_drop - self.depth
        if floor < SCALLOP_FLOOR:
            raise FretboardGeometryError(
                f"A {self.depth:g} mm scallop leaves {floor:.1f} mm of the "
                f"fretboard at its edge; keep at least {SCALLOP_FLOOR:g} mm "
                "(a shallower scallop or a thicker fretboard)."
            )

    @property
    def fret_numbers(self) -> range:
        """Return the frets whose following space is scalloped."""
        return range(self.from_fret, self.surface.fret_count)

    def depth_at(self, x: float, y: float) -> float:
        """Return how far below the radiused surface the scallop lies.

        Args:
            x: Distance from the nut along the neck, in mm.
            y: Lateral distance from the centreline, in mm.

        Returns:
            The depth in mm, 0 on the lands and outside the scalloped
            spaces.
        """
        for number in self.fret_numbers:
            start, end = self._space(number, y)
            if start < x < end:
                chord = end - start
                radius = (chord**2 / 4.0 + self.depth**2) / (2.0 * self.depth)
                offset = x - (start + end) / 2.0
                arc = math.sqrt(radius**2 - offset**2) - (radius - self.depth)
                # Eased into the land: no slope where it meets it.
                t = min(1.0, min(x - start, end - x) / (SCALLOP_EASE * chord))
                return arc * t**3 * (10.0 - 15.0 * t + 6.0 * t**2)
        return 0.0

    def rows(self) -> tuple[tuple[Point3D, ...], ...]:
        """Return the playing surface's rows with the scallops hollowed in.

        The surface's own rows (the nut, every fret and the board's end),
        and ``SCALLOP_ROWS`` spans of rows across every scalloped space
        between its lands, each point lowered by the scallop under it.
        """
        surface = self.surface
        positions = set(surface.station_positions)
        for number in self.fret_numbers:
            start, end = self._space(number, 0.0)
            positions.update(
                start + (end - start) * k / SCALLOP_ROWS
                for k in range(SCALLOP_ROWS + 1)
            )
        return tuple(
            tuple(
                Point3D(point.x, point.y, point.z - self.depth_at(point.x, point.y))
                for point in surface.profile_row(position)
            )
            for position in sorted(positions)
        )

    def _fret_line(self, number: int, y: float) -> float:
        """Return where fret ``number`` (0: the nut) crosses lateral ``y``."""
        position = self.surface.station_positions[number]
        return position + self.surface.skew.at(position) * y

    def _space(self, number: int, y: float) -> tuple[float, float]:
        """Return where the scallop after fret ``number`` runs at ``y``."""
        return (
            self._fret_line(number, y) + self.land,
            self._fret_line(number + 1, y) - self.land,
        )

    def _half_width(self, number: int) -> float:
        """Return the board's half-width at fret ``number``."""
        return self.surface.half_width_at(self.surface.station_positions[number])
