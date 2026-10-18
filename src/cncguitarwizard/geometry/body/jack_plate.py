"""A Les Paul style jack plate: a square plastic plate on the body's side.

The output jack's bore runs in from the edge into the control cavity;
the jack itself is held by this plate, screwed onto the side over the
bore, its thread through the plate's middle. Gibson's is 1-11/32 in
square, its corners rounded, its four screws on a 1 in square and the
jack's hole 3/8 in; it is cut from sheet as the covers are and, flat,
bent onto the side's curve as it is screwed on.
"""

from __future__ import annotations

import math

from ..exceptions import BodyGeometryError
from ..primitives import Point2D
from .covers import CoverPlate
from .hardware import DrilledHole

JACK_PLATE_SIZE = 34.13
"""The plate's side, in mm (1-11/32 in)."""

JACK_PLATE_SCREW_SPACING = 25.4
"""The four screws' square, centre to centre, in mm (1 in)."""

JACK_PLATE_SCREW_CLEARANCE = 3.2
"""The screws' clearance holes through the plate, in mm."""

JACK_PLATE_JACK_HOLE = 9.52
"""The hole for the jack's thread, in mm (3/8 in)."""

JACK_PLATE_CORNER_RADIUS = 3.0
"""The plate's rounded corners' radius, in mm."""

JACK_PLATE_CORNER_SAMPLES = 8
"""Points round each rounded corner."""


def les_paul_jack_plate(thickness: float, edge_height: float) -> CoverPlate:
    """Return the jack plate to cut from sheet.

    Its outline is in its own flat frame, as seen from outside the body:
    the jack's centre at the origin, ``x`` along the edge and ``y`` up
    the side, the plate square to the bore.

    Args:
        thickness: The sheet's thickness.
        edge_height: The body's side where the plate goes (the body's
            thickness), which it must fit.

    Returns:
        The plate, its face ``"side"``.

    Raises:
        BodyGeometryError: For a side lower than the plate.
    """
    if edge_height <= JACK_PLATE_SIZE:
        raise BodyGeometryError(
            f"The Les Paul style jack plate ({JACK_PLATE_SIZE:g} mm square) does "
            f"not fit the {edge_height:g} mm body's side: turn body_jack_plate off "
            "or make the body thicker."
        )
    half = JACK_PLATE_SIZE / 2.0
    inset = half - JACK_PLATE_CORNER_RADIUS
    outline: list[Point2D] = []
    # Each rounded corner, counter-clockwise from the right-hand side.
    for corner, (sign_x, sign_y) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for step in range(JACK_PLATE_CORNER_SAMPLES + 1):
            angle = math.pi / 2.0 * (corner + step / JACK_PLATE_CORNER_SAMPLES)
            outline.append(
                Point2D(
                    sign_x * inset + JACK_PLATE_CORNER_RADIUS * math.cos(angle),
                    sign_y * inset + JACK_PLATE_CORNER_RADIUS * math.sin(angle),
                )
            )
    screw = JACK_PLATE_SCREW_SPACING / 2.0
    holes = (
        DrilledHole("Jack plate jack hole", 0.0, 0.0, JACK_PLATE_JACK_HOLE, thickness),
        *(
            DrilledHole(
                f"Jack plate screw {index}",
                sign_x * screw,
                sign_y * screw,
                JACK_PLATE_SCREW_CLEARANCE,
                thickness,
            )
            for index, (sign_x, sign_y) in enumerate(
                ((1, 1), (-1, 1), (-1, -1), (1, -1)), start=1
            )
        ),
    )
    return CoverPlate(
        "Jack plate", "side", tuple(outline), thickness, holes=holes, recessed=False
    )
