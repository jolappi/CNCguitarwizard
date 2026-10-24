"""Three-dimensional radiused playing surface for a tapered fretboard."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator
from ..neck.outline import HeelFlare
from ..primitives import Point3D, QuadFace, SurfaceMesh
from .skew import FretSkew


@dataclass(frozen=True, slots=True)
class FretboardSurface:
    """Generate a loft-ready constant-radius fretboard surface.

    A cross-section row is generated at the nut and at every fret. Width is
    interpolated from the nut to the final fret (and on past it), flaring
    out with a heel wider than that (``heel_flare``), while radius and
    center thickness remain constant.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets and longitudinal surface intervals.
        nut_width: Fretboard width at the nut in millimetres.
        last_fret_width: Fretboard width at the final fret in millimetres.
        radius: Constant playing-surface radius in millimetres.
        center_thickness: Centerline thickness above the flat underside.
        end_extension: Additional length after the final fret.
        profile_sample_count: Odd number of points across each radius section.
        skew: Slanted or fanned frets: every row leans with its fret, a
            point ``y`` off the centerline moving ``skew.at(x) * y`` along
            the neck (see ``FretSkew``); ``station_positions`` stay on the
            centerline.
        frets_per_octave: Equal steps in each octave (12; more for a
            microtonal board, see ``FretCalculator``).
        heel_flare: The neck's flare out to a heel wider than its taper
            (``NeckOutline.heel_flare``): the board flares with it, flush
            with the neck's sides; ``None`` for none.

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
    end_extension: float = 0.0
    skew: FretSkew = field(default_factory=FretSkew)
    frets_per_octave: int = 12
    heel_flare: HeelFlare | None = None
    station_positions: tuple[float, ...] = field(init=False)
    mesh: SurfaceMesh = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and construct surface rows and quad faces."""
        self._validate()

        fret_positions = FretCalculator.calculate(
            self.scale_length,
            self.fret_count,
            self.frets_per_octave,
        )
        station_positions = (
            0.0,
            *(position.distance_from_nut for position in fret_positions),
        )
        final_fret_position = station_positions[-1]
        if self.end_extension > 0.0:
            station_positions = (
                *station_positions,
                final_fret_position + self.end_extension,
            )
        rows = tuple(
            self._build_profile_row(position, final_fret_position)
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

        steepest = max(abs(self.skew.at(position)) for position in station_positions)
        if steepest > math.tan(math.radians(35.0)):
            raise FretboardGeometryError(
                f"A fret leans {math.degrees(math.atan(steepest)):.0f} degrees; "
                "keep every fret within 35 degrees."
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
        if not math.isfinite(self.end_extension) or self.end_extension < 0.0:
            raise FretboardGeometryError(
                "Fretboard end extension must be finite and non-negative."
            )
        if self.last_fret_width < self.nut_width:
            raise FretboardGeometryError(
                "Final-fret width must not be narrower than the nut."
            )
        widest = self.last_fret_width + (
            self.heel_flare.extra if self.heel_flare is not None else 0.0
        )
        if self.radius <= widest / 2.0:
            raise FretboardGeometryError(
                "Fretboard radius must exceed half of the widest section."
            )
        if self.profile_sample_count < 3 or self.profile_sample_count % 2 == 0:
            raise FretboardGeometryError(
                "Profile sample count must be an odd integer of at least three."
            )
        widest_sagitta = self.radius - math.sqrt(self.radius**2 - (widest / 2.0) ** 2)
        if self.center_thickness <= widest_sagitta:
            raise FretboardGeometryError(
                "Fretboard surface leaves no material at its widest edges."
            )

    def profile_row(self, position: float) -> tuple[Point3D, ...]:
        """Return the surface's cross-section at a station along the neck.

        Args:
            position: Distance from the nut along the centreline, in mm.

        Returns:
            ``profile_sample_count`` points across the board, as the mesh's
            own rows are built.
        """
        return self._build_profile_row(
            position, self.station_positions[self.fret_count]
        )

    def outline_rows(self) -> tuple[tuple[Point3D, ...], ...]:
        """Return the rows whose ends trace the board's edges in plan: its
        first and last, and every row along a heel's flare (its edges are
        straight between them otherwise)."""
        rows = self.mesh.rows
        if self.heel_flare is None:
            return (rows[0], rows[-1])
        flaring = (
            row
            for position, row in zip(self.station_positions, rows, strict=True)
            if self.heel_flare.start < position < self.station_positions[-1]
        )
        return (rows[0], *flaring, rows[-1])

    def half_width_at(self, position: float) -> float:
        """Return the board's half-width ``position`` from the nut, along
        its centreline: its taper, flaring out with a wider heel."""
        return self._width(position, self.station_positions[self.fret_count]) / 2.0

    def _width(self, position: float, final_position: float) -> float:
        """Return the board's width at a station, the final fret's given."""
        width = self.nut_width + (self.last_fret_width - self.nut_width) * (
            position / final_position
        )
        if self.heel_flare is not None:
            width += self.heel_flare.extra_at(position)
        return width

    def _build_profile_row(
        self,
        position: float,
        final_position: float,
    ) -> tuple[Point3D, ...]:
        """Return one circular-arc row at a longitudinal station."""
        width = self._width(position, final_position)
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
        surface_drop = self.radius - math.sqrt(self.radius**2 - lateral**2)
        return Point3D(
            position + self.skew.at(position) * lateral,
            lateral,
            self.center_thickness - surface_drop,
        )
