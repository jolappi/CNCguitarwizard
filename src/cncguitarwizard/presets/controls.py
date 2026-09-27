"""Electronics layouts: the cavities, shaft holes and cover plates of each.

A layout is chosen with ``Prototype001Parameters.body_controls``. Every
layout is placed from the body shape's own control area — the mean of its
``pot_offsets`` (the traced almond uses the drawing's own cavity) and its
round switch cavity — so it rides with the shape and the heel end. Rear
cavities close with a plate seated flush in a cover recess; a Telecaster
style control plate sits flush in a recess in the top instead, with the
pots and the blade switch mounted through the plate itself. Every plate
is a ``CoverPlate`` to cut from sheet, and the body gets a shallow spot
for each of its screws. An optional 9 V battery box (``battery_features``)
is one more rear cavity with its own cover, placed by the shape's
``battery_offset``, ``battery_y`` and ``battery_angle_degrees``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ..geometry.body import (
    Cavity,
    CircularCavity,
    CoverPlate,
    DrilledHole,
    RearCavity,
    RectangularCavity,
    TracedCavity,
    cover_screw_points,
)
from ..geometry.primitives import Point2D
from .body_shapes import BodyShapeSpec

ControlLayout = Literal["almond_2", "gibson_4", "rear_3", "tele", "none"]
"""An electronics layout (see ``CONTROL_LABELS``)."""

CONTROL_LABELS: dict[str, str] = {
    "almond_2": "Design by Jone almond, 2 pots + round switch cavity",
    "gibson_4": "Gibson style, 4 pots + round switch cavity",
    "rear_3": "Rear cavity, 3 pots in a row + round switch cavity",
    "tele": "Telecaster style control plate on the top (2 pots + blade switch)",
    "none": "No control cavities",
}

SCREW_SPOT_DIAMETER = 3.0
SCREW_SPOT_DEPTH = 1.0
SCREW_CLEARANCE = 3.2


@dataclass(frozen=True, slots=True)
class ControlFeatures:
    """Everything an electronics layout cuts into the body, plus its plates.

    Args:
        control_cavity: The rear control cavity, or ``None``.
        switch_cavity: The rear switch cavity, or ``None``.
        top_cavities: Top-routed electronics: a control plate's recess and
            the deeper cavity inside it.
        holes: Shaft holes drilled from the top into a rear cavity.
        back_marks: Cover-screw spots drilled from the back.
        top_marks: Cover-screw spots drilled from the top.
        covers: The plates to cut from sheet.
        battery_cavity: The rear 9 V battery box, or ``None``.
    """

    control_cavity: RearCavity | None = None
    switch_cavity: RearCavity | None = None
    top_cavities: tuple[Cavity, ...] = ()
    holes: tuple[DrilledHole, ...] = ()
    back_marks: tuple[DrilledHole, ...] = ()
    top_marks: tuple[DrilledHole, ...] = ()
    covers: tuple[CoverPlate, ...] = ()
    battery_cavity: RearCavity | None = None

    def with_covers(self, other: ControlFeatures) -> ControlFeatures:
        """Return these features with another's screw spots and covers added."""
        return ControlFeatures(
            self.control_cavity,
            self.switch_cavity,
            self.top_cavities,
            self.holes,
            (*self.back_marks, *other.back_marks),
            self.top_marks,
            (*self.covers, *other.covers),
            self.battery_cavity,
        )

    def with_battery(self, battery: ControlFeatures) -> ControlFeatures:
        """Return these features with a battery box's cavity, spots and cover."""
        return ControlFeatures(
            self.control_cavity,
            self.switch_cavity,
            self.top_cavities,
            self.holes,
            (*self.back_marks, *battery.back_marks),
            self.top_marks,
            (*self.covers, *battery.covers),
            battery.battery_cavity,
        )


def rear_cover(rear: RearCavity, count: int) -> ControlFeatures:
    """Return the sheet cover for a rear cavity and its screw spots.

    ``count`` screws are spread round the ledge between the cavity and
    its cover recess (``cover_screw_points``); each gets a clearance hole
    in the plate and a shallow spot 1 mm into the ledge's floor. The plate
    is the recess's outline, as thick as the recess is deep.
    """
    depth = rear.cover_recess.depth
    screws = cover_screw_points(
        rear.cavity.outline,
        rear.cover_recess.outline,
        count,
        SCREW_CLEARANCE + 2.0,
    )
    marks = tuple(
        DrilledHole(
            f"{rear.cavity.name} cover screw {index}",
            point.x,
            point.y,
            SCREW_SPOT_DIAMETER,
            depth + SCREW_SPOT_DEPTH,
        )
        for index, point in enumerate(screws, start=1)
    )
    plate = CoverPlate(
        f"{rear.cavity.name} cover",
        "back",
        rear.cover_recess.outline,
        depth,
        holes=tuple(
            DrilledHole(f"Screw {index}", point.x, point.y, SCREW_CLEARANCE, depth)
            for index, point in enumerate(screws, start=1)
        ),
    )
    return ControlFeatures(back_marks=marks, covers=(plate,))


BATTERY_CAVITY_CORNER_RADIUS = 5.0
"""Corner radius of the battery box, in mm (a 9 V battery still fits the
default 56 × 30 mm box with it)."""


def battery_features(
    shape: BodyShapeSpec,
    heel_end: float,
    *,
    length: float,
    width: float,
    depth: float,
    cover_margin: float,
    cover_depth: float,
) -> ControlFeatures:
    """Return a rear 9 V battery box: its cavity, cover, and screw spots.

    The box is ``length`` along its own axis by ``width`` and ``depth``
    deep from the back, centred ``shape.battery_offset`` behind the heel
    end at ``shape.battery_y`` and turned ``shape.battery_angle_degrees``
    from the neck's axis. Its cover recess is ``cover_margin`` wider all
    round; the plate is held by two screws in the ledge at the box's ends.
    """
    centre = Point2D(heel_end + shape.battery_offset, shape.battery_y)
    angle = math.radians(shape.battery_angle_degrees)
    cos, sin = math.cos(angle), math.sin(angle)

    def placed(
        name: str, along: float, across: float, radius: float, deep: float
    ) -> TracedCavity:
        box = RectangularCavity(name, 0.0, 0.0, along, across, deep, radius)
        return TracedCavity(
            name,
            tuple(
                Point2D(
                    centre.x + p.x * cos - p.y * sin, centre.y + p.x * sin + p.y * cos
                )
                for p in box.outline
            ),
            deep,
        )

    cavity = placed(
        "Battery cavity", length, width, BATTERY_CAVITY_CORNER_RADIUS, depth
    )
    recess = placed(
        "Battery cavity cover recess",
        length + 2.0 * cover_margin,
        width + 2.0 * cover_margin,
        BATTERY_CAVITY_CORNER_RADIUS + cover_margin,
        cover_depth,
    )
    reach = length / 2.0 + cover_margin / 2.0
    screws = [
        Point2D(centre.x + side * reach * cos, centre.y + side * reach * sin)
        for side in (-1.0, 1.0)
    ]
    marks = tuple(
        DrilledHole(
            f"Battery cavity cover screw {index}",
            point.x,
            point.y,
            SCREW_SPOT_DIAMETER,
            cover_depth + SCREW_SPOT_DEPTH,
        )
        for index, point in enumerate(screws, start=1)
    )
    cover = CoverPlate(
        "Battery cavity cover",
        "back",
        recess.outline,
        cover_depth,
        holes=tuple(
            DrilledHole(f"Screw {index}", p.x, p.y, SCREW_CLEARANCE, cover_depth)
            for index, p in enumerate(screws, start=1)
        ),
    )
    return ControlFeatures(
        back_marks=marks, covers=(cover,), battery_cavity=RearCavity(cavity, recess)
    )


def control_features(
    layout: ControlLayout,
    shape: BodyShapeSpec,
    heel_end: float,
    *,
    thickness: float,
    top_wall: float,
    cover_depth: float,
    pot_hole_diameter: float,
    switch_hole_diameter: float,
) -> ControlFeatures:
    """Return the cavities, holes and plates of one electronics layout."""
    if layout == "none":
        return ControlFeatures()
    depth = thickness - top_wall
    pots = [(heel_end + x, y) for x, y in shape.pot_offsets]
    anchor_x = sum(x for x, _ in pots) / len(pots)
    anchor_y = sum(y for _, y in pots) / len(pots)
    inward = -1.0 if anchor_y > 0.0 else 1.0

    if layout == "tele":
        # The long plate sits 10 mm in from the pots' line, toward the
        # centreline, so its ends stay clear of the body edge.
        return _tele(
            anchor_x, anchor_y + inward * 10.0, depth, cover_depth, pot_hole_diameter
        )

    if layout == "almond_2":
        cavity: Cavity = TracedCavity(
            "Control cavity", shape.control_cavity_points(heel_end), depth
        )
        cover: Cavity = TracedCavity(
            "Control cavity cover recess",
            shape.control_cover_points(heel_end),
            cover_depth,
        )
    elif layout == "gibson_4":
        centre_y = anchor_y + inward * 6.0
        pots = [
            (anchor_x + dx, centre_y + dy)
            for dx, dy in ((-21.0, -17.0), (21.0, -17.0), (-21.0, 17.0), (21.0, 17.0))
        ]
        cavity = RectangularCavity(
            "Control cavity", anchor_x, centre_y, 78.0, 70.0, depth, corner_radius=16.0
        )
        cover = RectangularCavity(
            "Control cavity cover recess",
            anchor_x,
            centre_y,
            90.0,
            82.0,
            cover_depth,
            corner_radius=22.0,
        )
    else:  # rear_3
        pots = [(anchor_x + dx, anchor_y) for dx in (-30.0, 0.0, 30.0)]
        cavity = RectangularCavity(
            "Control cavity", anchor_x, anchor_y, 94.0, 34.0, depth, corner_radius=16.9
        )
        cover = RectangularCavity(
            "Control cavity cover recess",
            anchor_x,
            anchor_y,
            106.0,
            46.0,
            cover_depth,
            corner_radius=22.9,
        )

    control = RearCavity(cavity, cover)
    switch_x = heel_end + shape.switch_cavity_offset
    switch = RearCavity(
        CircularCavity(
            "Switch cavity",
            switch_x,
            shape.switch_cavity_y,
            shape.switch_cavity_diameter,
            depth,
        ),
        CircularCavity(
            "Switch cavity cover recess",
            heel_end + shape.switch_cover_offset,
            shape.switch_cover_y,
            shape.switch_cover_diameter,
            cover_depth,
        ),
    )
    holes = [
        DrilledHole(
            "Switch shaft hole",
            switch_x,
            shape.switch_cavity_y,
            switch_hole_diameter,
            thickness,
        )
    ]
    # Generated layouts drag as one piece in the body editor, so their
    # pots are named after the cavity; the almond keeps its own pots.
    prefix = "Pot" if layout == "almond_2" else "Control pot"
    holes += [
        DrilledHole(f"{prefix} {index} shaft hole", x, y, pot_hole_diameter, thickness)
        for index, (x, y) in enumerate(pots, start=1)
    ]
    marks: list[DrilledHole] = []
    covers: list[CoverPlate] = []
    for rear, count in ((control, 4), (switch, 3)):
        plate = rear_cover(rear, count)
        marks += plate.back_marks
        covers += plate.covers
    return ControlFeatures(
        control_cavity=control,
        switch_cavity=switch,
        holes=tuple(holes),
        back_marks=tuple(marks),
        covers=tuple(covers),
    )


def _tele(
    anchor_x: float,
    anchor_y: float,
    depth: float,
    cover_depth: float,
    pot_hole_diameter: float,
) -> ControlFeatures:
    """A Telecaster-style plate: flush in the top, parallel to the neck.

    The 160 × 32 mm round-ended plate carries the blade switch's slot at
    its front and two pots behind it; the cavity under it is 140 × 22 mm;
    two screws hold it at its ends.
    """
    recess = RectangularCavity(
        "Control plate recess",
        anchor_x,
        anchor_y,
        160.0,
        32.0,
        cover_depth,
        corner_radius=15.99,
    )
    cavity = RectangularCavity(
        "Control cavity",
        anchor_x,
        anchor_y,
        140.0,
        22.0,
        depth,
        corner_radius=10.99,
    )
    screws = [Point2D(anchor_x - 75.0, anchor_y), Point2D(anchor_x + 75.0, anchor_y)]
    plate = CoverPlate(
        "Control plate",
        "top",
        recess.outline,
        cover_depth,
        holes=(
            DrilledHole(
                "Pot 1 shaft hole", anchor_x, anchor_y, pot_hole_diameter, cover_depth
            ),
            DrilledHole(
                "Pot 2 shaft hole",
                anchor_x + 45.0,
                anchor_y,
                pot_hole_diameter,
                cover_depth,
            ),
            *(
                DrilledHole(f"Screw {index}", p.x, p.y, SCREW_CLEARANCE, cover_depth)
                for index, p in enumerate(screws, start=1)
            ),
        ),
        slots=(
            RectangularCavity(
                "Blade switch slot",
                anchor_x - 45.0,
                anchor_y,
                20.0,
                7.0,
                cover_depth,
                corner_radius=3.49,
            ),
        ),
    )
    marks = tuple(
        DrilledHole(
            f"Control plate screw {index}",
            p.x,
            p.y,
            SCREW_SPOT_DIAMETER,
            cover_depth + SCREW_SPOT_DEPTH,
        )
        for index, p in enumerate(screws, start=1)
    )
    return ControlFeatures(
        top_cavities=(recess, cavity), top_marks=marks, covers=(plate,)
    )
