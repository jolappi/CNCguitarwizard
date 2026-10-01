"""A top-mounted Floyd Rose locking nut and the shelf it stands on.

The nut's front face stands on the nut line (where the scale is measured
from, the strings breaking over its front edge) and it reaches ``depth``
back toward the headstock. Floyd Rose sets the nut's top a little above
the frets' tops, so the shelf under it sits ``height`` minus that much
below them. With a 6 mm fretboard and 1.2 mm frets, the shallow R2 nut's
shelf is about 1.7 mm above the fretboard's glue face: the fretboard runs
on under the nut and is milled down to it there. The deep R3 nut's shelf
comes out below ``MIN_BOARD_SHELF``, too thin to leave of the fretboard,
so the board ends at the nut line as usual and the nut stands on the
neck's own seat on a shim (Floyd Rose packs shims with its nuts).

Either way the flat seat on the neck runs ``seat_length`` behind the nut
line before the headstock face starts, and two screws hold the nut down
from the top, ``screw_spacing`` apart across the neck, half the nut's
depth behind the nut line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import NeckGeometryError
from ..primitives import Point2D

NUT_ABOVE_FRETS = 0.38
"""How far the nut's top stands above the frets' tops, in mm (Floyd
Rose's 0.215 in shelf under its 0.230 in R2 nut)."""

MIN_BOARD_SHELF = 1.0
"""The thinnest fretboard left under the nut, in mm; a lower shelf puts
the nut on the neck's seat with a shim instead."""

SEAT_MARGIN = 1.0
"""Flat seat left behind the nut's back face, in mm."""


@dataclass(frozen=True, slots=True)
class LockingNutSpec:
    """One locking nut's size.

    Args:
        name: Its label.
        width: Across the neck, in mm.
        height: From its base to its top, in mm.
        depth: Along the neck, front face to back face, in mm.
        screw_spacing: Between its two mounting screws, across the neck.
    """

    name: str
    width: float
    height: float
    depth: float
    screw_spacing: float


LOCKING_NUT_SPECS: dict[str, LockingNutSpec] = {
    "r2": LockingNutSpec("Floyd Rose R2", 41.3, 5.85, 15.0, 13.59),
    "r3": LockingNutSpec("Floyd Rose R3", 42.85, 7.10, 15.0, 13.59),
}
"""The Floyd Rose Original nuts: R2 (1-5/8 in, the default) and R3
(1-11/16 in)."""


@dataclass(frozen=True, slots=True)
class LockingNut:
    """A locking nut placed on the neck.

    Args:
        spec: The nut's size.
        lean: The nut line's slope, dx/dy (0 for a square nut).
        neck_width: The neck's width at the nut, in mm.
        shelf_height: The shelf under the nut above the fretboard's glue
            face, in mm.
        screw_diameter: The mounting screws' pilot holes, in mm.
        screw_depth: How deep the pilot holes reach below the glue face.

    Raises:
        NeckGeometryError: For a nut wider than the neck, a shelf below
            the glue face, or screw sizes that are not positive.
    """

    spec: LockingNutSpec
    lean: float
    neck_width: float
    shelf_height: float
    screw_diameter: float
    screw_depth: float

    def __post_init__(self) -> None:
        if self.spec.width > self.neck_width + 1e-9:
            raise NeckGeometryError(
                f"The {self.spec.name} locking nut is {self.spec.width:g} mm "
                f"wide; nut_width must be at least that ({self.neck_width:g} mm)."
            )
        if not math.isfinite(self.shelf_height) or self.shelf_height < 0.0:
            raise NeckGeometryError(
                f"The {self.spec.name} locking nut would need its shelf "
                f"{-self.shelf_height:.2f} mm below the fretboard's glue face; "
                "use a thicker fretboard, taller frets or a shallower nut."
            )
        for name, value in (
            ("screw_diameter", self.screw_diameter),
            ("screw_depth", self.screw_depth),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise NeckGeometryError(
                    f"Locking nut {name} must be finite and positive."
                )

    @classmethod
    def placed(
        cls,
        spec: LockingNutSpec,
        *,
        lean: float,
        neck_width: float,
        fretboard_thickness: float,
        fret_height: float,
        screw_diameter: float,
        screw_depth: float,
    ) -> LockingNut:
        """Return the nut with its shelf set from the board and the frets."""
        shelf = fretboard_thickness + fret_height - (spec.height - NUT_ABOVE_FRETS)
        return cls(spec, lean, neck_width, shelf, screw_diameter, screw_depth)

    @property
    def on_fretboard(self) -> bool:
        """Whether the fretboard runs on under the nut as its shelf."""
        return self.shelf_height >= MIN_BOARD_SHELF

    @property
    def shim(self) -> float:
        """The shim under a nut on the neck's seat, in mm (0 on the board)."""
        return 0.0 if self.on_fretboard else self.shelf_height

    @property
    def seat_length(self) -> float:
        """How far the flat seat runs behind the nut line, in mm."""
        return self.spec.depth + SEAT_MARGIN

    def seat_outline(self) -> tuple[Point2D, ...]:
        """Return the seat in plan: the neck's width, along the nut line."""
        half = self.neck_width / 2.0
        return tuple(
            Point2D(self.lean * y + dx, y)
            for dx, y in (
                (0.0, -half),
                (0.0, half),
                (-self.seat_length, half),
                (-self.seat_length, -half),
            )
        )

    def screw_centres(self) -> tuple[Point2D, Point2D]:
        """Return the two mounting screws' centres."""
        half = self.spec.screw_spacing / 2.0
        back = self.spec.depth / 2.0
        return (
            Point2D(-self.lean * half - back, -half),
            Point2D(self.lean * half - back, half),
        )
