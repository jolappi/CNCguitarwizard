"""Cut the nut-slot filing jig out of sheet, in one program.

The jig (``geometry.neck.nut_jig``) is a plate that stands on edge on the
fretboard, so it is cut lying flat, seen as it stands: the sheet's
thickness is its length along the neck, machine X runs along the nut's
face (the bass end at +X) and machine Y up from the fretboard. One small
cutter does it all — the fret-slot cutter's kind, ``nut_jig_tool_diameter``
wide, at the fret-slot speed and step-down: each string's slot first,
while the sheet holds it, then the outline. The sheet is on double-sided
tape, so the jig needs no tabs.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, replace

from ..geometry.neck.nut_jig import NUT_JIG_CORNER_RELIEF, NutJigSlot, NutSlotJig
from ..geometry.primitives import Point2D
from .exceptions import ToolpathError
from .gcode import Setup
from .operations import depth_levels, profile
from .parameters import MachiningParameters
from .planar import polygon_bounds
from .toolpath import PathBuilder, Toolpath

NUT_JIG_SHEET_MARGIN = 5.0
"""Sheet left round the jig beyond the cutter, in mm."""

SLOT_RUN_OUT = 1.0
"""How far each slot runs on past the jig's top, beyond the cutter, mm."""

SLOT_STEP_OVER = 0.8
"""The most a wide slot's lines step across, as a share of the cutter."""


@dataclass(frozen=True, slots=True)
class NutJigMachiningPlan:
    """The program that cuts the jig from sheet.

    Args:
        jig: The sheet program.
        stock_length: Sheet length (X) the jig needs.
        stock_width: Sheet width (Y) the jig needs.
        stock_thickness: The sheet's thickness: the jig's own.
        origin_x: Always ``0`` — the program has its own work zero.
        origin_y: Always ``0``.
        index_pin_positions: Always empty — no dowels.
        preview_outlines: The jig's outline in the program's frame.
    """

    jig: Setup
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float = 0.0
    origin_y: float = 0.0
    index_pin_positions: tuple[tuple[float, float], ...] = ()
    preview_outlines: tuple[tuple[Point2D, ...], ...] = ()

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the jig's one program."""
        return (self.jig,)


def nut_jig_tool(
    slot_tool: MachiningParameters, diameter: float
) -> MachiningParameters:
    """Return the jig's cutter: the fret-slot cutter's speeds, ``diameter`` wide."""
    return replace(
        slot_tool, tool_diameter=diameter, finishing_allowance=0.0, tab_count=0
    )


def plan_nut_jig_machining(
    jig: NutSlotJig | None, tool: MachiningParameters
) -> NutJigMachiningPlan | None:
    """Plan the jig's sheet program, or return ``None`` without a jig.

    Raises:
        ToolpathError: If the cutter is too wide for the corners cut away
            where the legs meet the underside.
    """
    if jig is None:
        return None
    if tool.tool_diameter >= NUT_JIG_CORNER_RELIEF - 0.1:
        raise ToolpathError(
            f"The {tool.tool_diameter:g} mm nut-jig cutter is too wide for the "
            f"jig's {NUT_JIG_CORNER_RELIEF:g} mm corners at its legs: set "
            f"nut_jig_tool_diameter under {NUT_JIG_CORNER_RELIEF - 0.1:g} mm."
        )
    min_x, min_y, max_x, max_y = polygon_bounds(jig.body)
    centre = Point2D((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

    def frame(point: Point2D) -> Point2D:
        return Point2D(point.x - centre.x, point.y - centre.y)

    through = jig.thickness + tool.through_overshoot
    paths = [_slot(slot, frame, through, tool) for slot in jig.slots]
    body = tuple(frame(point) for point in jig.body)
    paths.append(profile("Nut-slot jig - outline", body, through, tool))
    margin = tool.tool_diameter + NUT_JIG_SHEET_MARGIN
    length = max_x - min_x + 2.0 * margin
    width = max_y - min_y + 2.0 * margin
    narrow = [slot for slot in jig.slots if slot.width < tool.tool_diameter - 1e-6]
    setup = Setup(
        "Jig_nut_slots",
        f"Nut-slot filing jig - {len(jig.slots)} slots, cut from "
        f"{jig.thickness:g} mm sheet",
        tuple(paths),
        (
            f"Sheet {jig.thickness:g} mm thick (hardwood, plywood or plastic), "
            f"at least {length:.0f} x {width:.0f} mm, on double-sided tape on a "
            "spoilboard: the jig has no tabs.",
            f"The {tool.tool_diameter:g} mm cutter (the fret-slot cutter's "
            "kind and speed): the slots first, then the outline. The jig lies "
            "as it stands on the neck seen from the bridge: X along the nut's "
            "face, the bass end at +X; Y up from the fretboard.",
            "Slots: "
            + "; ".join(
                f"string {slot.string} (.{slot.gauge * 1000:03.0f} in) "
                f"{max(slot.width, tool.tool_diameter):.2f} mm"
                for slot in jig.slots
            )
            + ".",
            *(
                (
                    f"The slots for strings "
                    f"{', '.join(str(slot.string) for slot in narrow)} come out "
                    f"{tool.tool_diameter:g} mm wide, the cutter's width, wider "
                    "than their strings: a cutter no wider than "
                    f"{min(slot.width for slot in narrow):.2f} mm cuts each its "
                    "own width.",
                )
                if narrow
                else ()
            ),
            "Stand the jig on the fretboard with its face flat against the "
            "nut's front and its legs over the board's edges, the widest slot "
            "on the bass side. Run each string's file through its slot to "
            "start the nut's slot; then take the jig off and finish each slot, "
            "sloping it down toward the headstock and turning it toward the "
            "string's tuner post.",
        ),
        tool=tool,
        work_zero="the centre of the jig, Z at the sheet top",
    )
    return NutJigMachiningPlan(
        setup,
        stock_length=length,
        stock_width=width,
        stock_thickness=jig.thickness,
        preview_outlines=(tuple(frame(point) for point in jig.outline),),
    )


def _slot(
    slot: NutJigSlot,
    frame: Callable[[Point2D], Point2D],
    depth: float,
    tool: MachiningParameters,
) -> Toolpath:
    """Return one slot's path: lines along it, up and down a pass at a time.

    A slot no wider than the cutter is one line; a wider one has a line
    on each wall and as many between as keep the steps across under
    ``SLOT_STEP_OVER`` of the cutter. Each line's round end sits on the
    floor; the top end runs out past the jig's top.
    """
    name = (
        f"Slot {slot.string} - .{slot.gauge * 1000:03.0f} in string, "
        f"{slot.width:.2f} mm"
    )
    radius = tool.tool_radius
    spread = max(0.0, slot.width - tool.tool_diameter)
    count = math.ceil(spread / (SLOT_STEP_OVER * tool.tool_diameter) - 1e-9) + 1
    xs = [
        slot.centre - spread / 2.0 + spread * index / max(1, count - 1)
        for index in range(count)
    ]
    bottom = slot.floor + radius
    end = slot.top + radius + SLOT_RUN_OUT
    builder = PathBuilder(
        name,
        safe_height=tool.safe_height,
        feed_rate=tool.feed_rate,
        plunge_rate=tool.plunge_rate,
    )
    x, y = xs[0], end
    start = frame(Point2D(x, y))
    builder.rapid_to(start.x, start.y)
    builder.rapid_down_to(0.0)

    def cut(to_x: float, to_y: float) -> None:
        point = frame(Point2D(to_x, to_y))
        builder.cut_to(point.x, point.y)

    for level, z in enumerate(depth_levels(0.0, depth, tool.step_down)):
        builder.plunge_to(z)
        # Down one line, across, up the next; back the other way on the
        # next pass.
        for line in xs if level % 2 == 0 else reversed(xs):
            if line != x:
                x = line
                cut(x, y)
            y = bottom if y == end else end
            cut(x, y)
    return builder.build()
