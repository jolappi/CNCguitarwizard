"""Longitudinal and radial fretboard profile geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator
from ..primitives import Line2D, Point2D


@dataclass(frozen=True, slots=True)
class FretboardSideProfile:
    """Represent the centerline side profile of a separate fretboard.

    Args:
        scale_length: Nut-to-bridge scale length in millimetres.
        fret_count: Number of frets.
        center_thickness: Fretboard thickness at its centerline.

    Raises:
        FretboardGeometryError: If dimensions cannot form a valid profile.
    """

    scale_length: float
    fret_count: int
    center_thickness: float
    end_position: float = field(init=False)
    bottom_line: Line2D = field(init=False)
    top_line: Line2D = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate inputs and construct the rectangular center profile."""
        dimensions = (self.scale_length, self.center_thickness)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise FretboardGeometryError(
                "Fretboard side-profile dimensions must be finite and positive."
            )
        if self.fret_count <= 0:
            raise FretboardGeometryError("Fret count must be greater than zero.")

        end_position = FretCalculator.calculate(
            self.scale_length,
            self.fret_count,
        )[-1].distance_from_nut
        nut_bottom = Point2D(0.0, 0.0)
        end_bottom = Point2D(end_position, 0.0)
        end_top = Point2D(end_position, self.center_thickness)
        nut_top = Point2D(0.0, self.center_thickness)

        object.__setattr__(self, "end_position", end_position)
        object.__setattr__(self, "bottom_line", Line2D(nut_bottom, end_bottom))
        object.__setattr__(self, "top_line", Line2D(nut_top, end_top))
        object.__setattr__(
            self,
            "boundary",
            (nut_bottom, end_bottom, end_top, nut_top),
        )


@dataclass(frozen=True, slots=True)
class FretboardCrossSection:
    """Represent a flat-bottomed, constant-radius fretboard section.

    ``center_thickness`` is measured from the flat underside to the highest
    point of the radiused playing surface.

    Args:
        width: Fretboard chord width in millimetres.
        radius: Playing-surface radius in millimetres.
        center_thickness: Thickness at the centerline in millimetres.
        sample_count: Number of points used to describe the circular arc.

    Raises:
        FretboardGeometryError: If the requested section is geometrically
            impossible or leaves no material at the edges.
    """

    width: float
    radius: float
    center_thickness: float
    sample_count: int = 33
    sagitta: float = field(init=False)
    edge_thickness: float = field(init=False)
    top_arc: tuple[Point2D, ...] = field(init=False)
    bottom_line: Line2D = field(init=False)
    boundary: tuple[Point2D, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate dimensions and sample the circular playing surface."""
        self._validate()

        half_width = self.width / 2.0
        sagitta = self.radius - math.sqrt(self.radius**2 - half_width**2)
        edge_thickness = self.center_thickness - sagitta
        if edge_thickness <= 0.0:
            raise FretboardGeometryError(
                "Fretboard radius and thickness leave no material at the edges."
            )

        step = self.width / (self.sample_count - 1)
        top_arc = tuple(
            Point2D(
                x=-half_width + index * step,
                y=self.center_thickness
                - (
                    self.radius
                    - math.sqrt(
                        self.radius**2 - (-half_width + index * step) ** 2
                    )
                ),
            )
            for index in range(self.sample_count)
        )
        bottom_left = Point2D(-half_width, 0.0)
        bottom_right = Point2D(half_width, 0.0)

        object.__setattr__(self, "sagitta", sagitta)
        object.__setattr__(self, "edge_thickness", edge_thickness)
        object.__setattr__(self, "top_arc", top_arc)
        object.__setattr__(
            self,
            "bottom_line",
            Line2D(bottom_left, bottom_right),
        )
        object.__setattr__(
            self,
            "boundary",
            (bottom_left, bottom_right, *reversed(top_arc)),
        )

    def _validate(self) -> None:
        """Reject invalid circular-section parameters."""
        dimensions = (self.width, self.radius, self.center_thickness)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise FretboardGeometryError(
                "Fretboard cross-section dimensions must be finite and positive."
            )
        if self.radius <= self.width / 2.0:
            raise FretboardGeometryError(
                "Fretboard radius must exceed half of the section width."
            )
        if self.sample_count < 3 or self.sample_count % 2 == 0:
            raise FretboardGeometryError(
                "Arc sample count must be an odd integer of at least three."
            )
