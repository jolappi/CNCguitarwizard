"""Toolpaths for the cavity covers and control plates, cut from sheet.

Each cover gets its own program so it can be cut from whatever sheet
suits it — plexiglass, pickguard plastic, or thin plywood. The sheet is
held down on a spoilboard; the work zero is the centre of the cover's
bounding box on the sheet top, so one sheet can carry several covers
side by side by moving the zero between programs.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..geometry.body import CoverPlate
from ..geometry.primitives import Point2D
from .exceptions import ToolpathError
from .gcode import Setup
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .planar import offset_polygon, polygon_bounds
from .toolpath import Toolpath

COVER_FIT_CLEARANCE = 0.2
"""How much smaller than its recess a cover is cut, per side, in mm."""

COVER_SHEET_MARGIN = 10.0
"""Sheet left around the largest cover on every side, in mm."""


@dataclass(frozen=True, slots=True)
class CoverMachiningPlan:
    """One program per cover plate, all cut with the small tool.

    Args:
        covers: One setup per cover, in the order the body lists them.
        stock_length: Sheet length (X) needed for the largest cover.
        stock_width: Sheet width (Y) needed for the largest cover.
        stock_thickness: Thickest cover's sheet thickness.
        origin_x: Always ``0`` — each program has its own work zero.
        origin_y: Always ``0``.
        index_pin_positions: Always empty — covers need no dowels.
        preview_outlines: Each cover's outline in its program's frame.
    """

    covers: tuple[Setup, ...]
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float = 0.0
    origin_y: float = 0.0
    index_pin_positions: tuple[tuple[float, float], ...] = ()
    preview_outlines: tuple[tuple[Point2D, ...], ...] = ()

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the cover programs in order."""
        return self.covers


def cover_tool(parameters: MachiningParameters) -> MachiningParameters:
    """Return the small-tool settings used for sheet covers.

    The small drill doubles as the cutter (``small_cutter``): slower
    feeds, shallow steps (at most 1 mm) and short, low tabs suit plastic
    sheet.
    """
    small = parameters.small_cutter
    return replace(
        small,
        feed_rate=min(small.feed_rate, 600.0),
        step_down=min(small.step_down, 1.0),
        tab_count=4,
        tab_length=4.0,
    )


def cover_setup_name(cover: CoverPlate) -> str:
    """Return the program name for one cover, e.g. ``Cover_control_cavity``."""
    stem = re.sub(r"[^a-z0-9]+", "_", cover.name.lower()).strip("_")
    stem = stem.removesuffix("_cover")
    return f"Cover_{stem}"


def plan_cover_machining(
    covers: Sequence[CoverPlate], parameters: MachiningParameters
) -> CoverMachiningPlan | None:
    """Plan one sheet program per cover, or return ``None`` when there are none.

    A back cover is cut as seen from the back (Y mirrored), so the face
    up on the machine is the face that shows on the finished guitar.

    Raises:
        ToolpathError: If a cover is too small for the tool.
    """
    if not covers:
        return None
    setups: list[Setup] = []
    previews: list[tuple[Point2D, ...]] = []
    length = width = thickness = 0.0
    for cover in covers:
        setup, outline = _cover_setup(cover, parameters)
        setups.append(setup)
        previews.append(outline)
        min_x, min_y, max_x, max_y = polygon_bounds(outline)
        length = max(length, max_x - min_x)
        width = max(width, max_y - min_y)
        thickness = max(thickness, cover.thickness)
    return CoverMachiningPlan(
        tuple(setups),
        stock_length=length + 2.0 * COVER_SHEET_MARGIN,
        stock_width=width + 2.0 * COVER_SHEET_MARGIN,
        stock_thickness=thickness,
        preview_outlines=tuple(previews),
    )


def _cover_setup(
    cover: CoverPlate, parameters: MachiningParameters
) -> tuple[Setup, tuple[Point2D, ...]]:
    tool = cover_tool(parameters)
    tool = replace(tool, tab_height=min(tool.tab_height, cover.thickness / 2.0))
    min_x, min_y, max_x, max_y = polygon_bounds(cover.outline)
    centre_x = (min_x + max_x) / 2.0
    centre_y = (min_y + max_y) / 2.0
    mirror = cover.face == "back"

    def frame(point: Point2D) -> Point2D:
        dy = point.y - centre_y
        return Point2D(point.x - centre_x, -dy if mirror else dy)

    outline = tuple(frame(point) for point in cover.outline)
    # A recessed cover is cut a little smaller to fit its recess; one on
    # the face (a truss-rod cover) to its own outline.
    fitted = (
        offset_polygon(outline, COVER_FIT_CLEARANCE, inward=True)
        if cover.recessed
        else outline
    )
    if not fitted:
        raise ToolpathError(f"{cover.name} is too small to cut.")
    through = cover.thickness + parameters.through_overshoot
    paths: list[Toolpath] = [
        drill(
            f"{cover.name} - {hole.name}",
            frame(hole.center),
            hole.diameter,
            through,
            tool,
        )
        for hole in cover.holes
    ]
    paths += [
        pocket(
            f"{cover.name} - {slot.name}",
            tuple(frame(point) for point in slot.outline),
            through,
            tool,
        )
        for slot in cover.slots
    ]
    paths.append(
        profile(f"{cover.name} - outline", fitted, through, tool, with_tabs=True)
    )
    face = "back" if mirror else "top"
    setup = Setup(
        cover_setup_name(cover),
        f"{cover.name} - cut from {cover.thickness:g} mm sheet",
        tuple(paths),
        (
            f"Sheet {cover.thickness:g} mm (plexiglass, pickguard plastic or "
            "plywood) screwed or taped to a spoilboard.",
            *(
                (
                    f"Visible face up: this cover sits on the body's {face}.",
                    f"Cut {COVER_FIT_CLEARANCE:g} mm smaller than its recess per "
                    "side; break the tabs and sand the edge.",
                )
                if cover.recessed
                else (
                    _face_note(cover),
                    "Break the tabs and sand the edge.",
                )
            ),
            "Holes and slots first, then the outline.",
        ),
        tool=tool,
        work_zero="the centre of the cover, Z at the sheet top",
    )
    return setup, tuple(fitted)


def _face_note(cover: CoverPlate) -> str:
    """Return where a part screwed onto a face (not in a recess) goes."""
    if cover.name.endswith("pickup frame"):
        return (
            "Visible face up: it is screwed onto the top round its pickup (no "
            "recess), into the pilots Body_top_small_holes drills; the "
            "pickup's height screws are reached through its two larger holes."
        )
    if cover.name == "Strap guide plate":
        return (
            "Visible face up: it is screwed onto the back over its two spacers "
            "(no recess), into the pilots Body_back_small_holes drills; the "
            "strap runs under its bar, between the spacers."
        )
    if cover.name == "Jack plate":
        return (
            "Visible face up: it is screwed onto the body's side over the jack's "
            "bore (no recess), bent to the side's curve, the jack through its "
            "middle hole; hold it centred on the bore and drill its four screws' "
            "pilots by hand through its holes."
        )
    if cover.name.startswith("Strap guide spacer"):
        return (
            "Either face up: it sits under one of the strap guide plate's "
            "flames, between the plate and the back, its screw through it."
        )
    return (
        "Visible face up: it is screwed onto the headstock face over the "
        "truss-rod trough (no recess), into the pilots Neck_top_small_holes "
        "drills (on a laminated neck, drill them by hand through its holes)."
    )
