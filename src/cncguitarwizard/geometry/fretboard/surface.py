"""Three-dimensional radiused playing surface for a tapered fretboard."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator
from ..primitives import Point3D, QuadFace, SurfaceMesh


@dataclass(frozen=True, slots=True)
class FretboardSurface:
    """Generate a loft-ready constant-radius fretboard surface.

    A cross-section row is generated at the nut and at every fret. Width is
    interpolated from the nut to the final fret while radius and center
    thickness remain constant.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets and longitudinal surface intervals.
        nut_width: Fretboard width at the nut in millimetres.
        last_fret_width: Fretboard width at the final fret in millimetres.
        radius: Constant playing-surface radius in millimetres.
        center_thickness: Centerline thickness above the flat underside.
        profile_sample_count: Odd number of points across each radius section.

    Raises:
        FretboardGeometryError: If dimensions cannot form a valid surface.
    """

    scale_length: float
    fret_count: int
    nut_width: float
    last_fret_width: float
    radius: float
    center_thickness: float
    profile_sample_count: int = 33
    station_positions: tuple[float, ...] = field(init=False)
    mesh: SurfaceMesh = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and construct surface rows and quad faces."""
        self._validate()

        fret_positions = FretCalculator.calculate(
            self.scale_length,
            self.fret_count,
        )
        station_positions = (
            0.0,
            *(position.distance_from_nut for position in fret_positions),
        )
        final_position = station_positions[-1]
        rows = tuple(
            self._build_profile_row(position, final_position)
            for position in station_positions
        )
        faces = tuple(
            QuadFace(
                first_pair[0],
                first_pair[1],
                second_pair[1],
                second_pair[0],
            )
            for first_row, second_row in pairwise(rows)
            for first_pair, second_pair in zip(
                pairwise(first_row),
                pairwise(second_row),
                strict=True,
            )
        )

        object.__setattr__(self, "station_positions", station_positions)
        object.__setattr__(self, "mesh", SurfaceMesh(rows, faces))

    def _validate(self) -> None:
        """Reject invalid surface dimensions and resolution."""
        dimensions = (
            self.scale_length,
            self.nut_width,
            self.last_fret_width,
            self.radius,
            self.center_thickness,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise FretboardGeometryError(
                "Fretboard surface dimensions must be finite and positive."
            )
        if self.fret_count <= 0:
            raise FretboardGeometryError("Fret count must be greater than zero.")
        if self.last_fret_width < self.nut_width:
            raise FretboardGeometryError(
                "Final-fret width must not be narrower than the nut."
            )
        if self.radius <= self.last_fret_width / 2.0:
            raise FretboardGeometryError(
                "Fretboard radius must exceed half of the widest section."
            )
        if (
            self.profile_sample_count < 3
            or self.profile_sample_count % 2 == 0
        ):
            raise FretboardGeometryError(
                "Profile sample count must be an odd integer of at least three."
            )
        widest_sagitta = self.radius - math.sqrt(
            self.radius**2 - (self.last_fret_width / 2.0) ** 2
        )
        if self.center_thickness <= widest_sagitta:
            raise FretboardGeometryError(
                "Fretboard surface leaves no material at its widest edges."
            )

    def _build_profile_row(
        self,
        position: float,
        final_position: float,
    ) -> tuple[Point3D, ...]:
        """Return one circular-arc row at a longitudinal station."""
        fraction = position / final_position
        width = (
            self.nut_width
            + (self.last_fret_width - self.nut_width) * fraction
        )
        half_width = width / 2.0
        step = width / (self.profile_sample_count - 1)

        return tuple(
            self._surface_point(
                position,
                -half_width + index * step,
            )
            for index in range(self.profile_sample_count)
        )

    def _surface_point(self, position: float, lateral: float) -> Point3D:
        """Return one point on the constant-radius playing surface."""
        surface_drop = self.radius - math.sqrt(
            self.radius**2 - lateral**2
        )
        return Point3D(
            position,
            lateral,
            self.center_thickness - surface_drop,
        )
