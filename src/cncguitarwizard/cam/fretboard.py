"""Plan the single-sided machining of the Prototype001 fretboard.

The fretboard blank is a flat board ``blank_thickness`` thick, glue
face down, held on two dowels in the waste beyond the nut and beyond
the end. Everything is cut from the top in one fixturing, with tool
changes between programs (re-touch Z on the blank top after each):

1. ball nose — the radiused playing surface;
2. small end mill — the inlay pockets, measured from the crown;
3. fret-slot bit — 24 slots that follow the radius across the board;
4. flat end mill — the tapered outline with rounded nut corners and tabs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..geometry.primitives import Point2D, rounded_polygon_points
from .exceptions import ToolpathError
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .surfacing import build_offset_grid, raster_finish
from .toolpath import PathBuilder, Toolpath

if TYPE_CHECKING:
    from ..presets import Prototype001Geometry


def _flat_tool() -> MachiningParameters:
    return MachiningParameters(stock_margin=35.0, tab_height=3.0)


def _ball_tool() -> MachiningParameters:
    return MachiningParameters(tool_tip="ball", stock_margin=35.0)


def _slot_tool() -> MachiningParameters:
    return MachiningParameters(
        tool_diameter=0.6,
        spindle_speed=12000.0,
        feed_rate=300.0,
        plunge_rate=100.0,
        step_down=0.9,
        stock_margin=35.0,
    )


def _inlay_tool() -> MachiningParameters:
    return MachiningParameters(
        tool_diameter=1.0,
        spindle_speed=12000.0,
        feed_rate=300.0,
        plunge_rate=100.0,
        step_down=1.0,
        finishing_allowance=0.0,
        stock_margin=35.0,
    )


@dataclass(frozen=True, slots=True)
class FretboardMachiningParameters:
    """Tools and blank settings for the fretboard.

    Args:
        flat: Flat end mill for the index pins and the outline.
        ball: Ball nose for the radiused surface.
        slot: The fret-slot cutter; its ``step_down`` is the depth per
            pass through the slot.
        inlay: The small end mill for the inlay pockets.
        blank_thickness: Board thickness before the radius is cut; the
            crown ends ``blank_thickness - center_thickness`` below the
            blank top.
        finishing_step_over: Raster step for the radius, in millimetres.
        slot_overshoot: How far each slot runs past the board edges.
        grid_spacing_x: Drop-cutter grid spacing along the board.
        grid_spacing_y: Drop-cutter grid spacing across the board.
    """

    flat: MachiningParameters = field(default_factory=_flat_tool)
    ball: MachiningParameters = field(default_factory=_ball_tool)
    slot: MachiningParameters = field(default_factory=_slot_tool)
    inlay: MachiningParameters = field(default_factory=_inlay_tool)
    blank_thickness: float = 7.0
    finishing_step_over: float = 1.0
    slot_overshoot: float = 1.0
    grid_spacing_x: float = 2.0
    grid_spacing_y: float = 0.5

    def __post_init__(self) -> None:
        for name, value in (
            ("blank_thickness", self.blank_thickness),
            ("finishing_step_over", self.finishing_step_over),
            ("grid_spacing_x", self.grid_spacing_x),
            ("grid_spacing_y", self.grid_spacing_y),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ToolpathError(f"{name} must be finite and positive.")
        if not math.isfinite(self.slot_overshoot) or self.slot_overshoot < 0.0:
            raise ToolpathError("slot_overshoot must be finite and non-negative.")
        if self.ball.tool_tip != "ball":
            raise ToolpathError("The surfacing tool must be a ball nose.")


@dataclass(frozen=True, slots=True)
class FretboardMachiningPlan:
    """The setups that machine one fretboard, in running order."""

    index_pins: Setup
    radius: Setup
    inlays: Setup
    slots: Setup
    outline: Setup
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float
    origin_y: float
    index_pin_positions: tuple[tuple[float, float], ...]
    preview_outlines: tuple[tuple[Point2D, ...], ...]

    @property
    def setups(self) -> tuple[Setup, ...]:
        return (self.index_pins, self.radius, self.inlays, self.slots, self.outline)


def fretboard_outline_polygon(geometry: Prototype001Geometry) -> tuple[Point2D, ...]:
    """Return the board's plan outline with its rounded nut corners."""
    surface = geometry.fretboard_surface
    first = surface.mesh.rows[0]
    last = surface.mesh.rows[-1]
    nut_half = abs(first[0].y)
    end_half = abs(last[0].y)
    end_x = last[0].x
    radius = geometry.fret_layout.fretboard.nut_corner_radius
    vertices = [
        Point2D(0.0, -nut_half),
        Point2D(end_x, -end_half),
        Point2D(end_x, end_half),
        Point2D(0.0, nut_half),
    ]
    return rounded_polygon_points(
        vertices, [radius, 0.0, 0.0, radius], samples_per_corner=8
    )


def plan_fretboard_machining(
    geometry: Prototype001Geometry,
    parameters: FretboardMachiningParameters,
) -> FretboardMachiningPlan:
    """Return toolpaths for every feature of the fretboard.

    Raises:
        ToolpathError: If the blank is thinner than the finished board,
            or an index pin cannot be placed.
    """
    surface = geometry.fretboard_surface
    skim = parameters.blank_thickness - surface.center_thickness
    if skim < 0.0:
        raise ToolpathError(
            "Fretboard blank must be at least as thick as the finished board."
        )
    flat = parameters.flat
    outline = fretboard_outline_polygon(geometry)
    xs = [point.x for point in outline]
    ys = [point.y for point in outline]
    radius = max(flat.tool_radius, parameters.ball.tool_radius)
    sweep = (
        Point2D(min(xs) - radius, min(ys) - radius),
        Point2D(max(xs) + radius, min(ys) - radius),
        Point2D(max(xs) + radius, max(ys) + radius),
        Point2D(min(xs) - radius, max(ys) + radius),
    )
    stock = StockBounds.around(outline, flat.stock_margin)
    pins = resolve_index_pins(outline, [sweep], flat, stock)
    origin_x, origin_y = pins[0]
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])

    def machine(point: Point2D) -> Point2D:
        return Point2D(point.x - origin_x, point.y - origin_y)

    def machine_polygon(points: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
        return tuple(machine(point) for point in points)

    def surface_depth(model_y: float) -> float:
        """Depth of the radiused surface below the blank top at lateral y."""
        drop = surface.radius - math.sqrt(
            max(0.0, surface.radius**2 - model_y**2)
        )
        return skim + drop

    index_pins = Setup(
        "Fretboard_index_pins",
        "Fretboard index pins - drill both dowel holes through the blank",
        tuple(
            drill(
                f"Index pin {index}",
                machine(Point2D(x, y)),
                flat.index_pin_diameter,
                parameters.blank_thickness + flat.through_overshoot,
                flat,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            "Clamp the blank glue face down on a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the blank top.",
            f"Blank: at least {stock.length:.0f} x {stock.width:.0f} x "
            f"{parameters.blank_thickness:g} mm.",
        ),
        reference_points,
        flat,
    )

    x_range = (min(xs) - radius - origin_x, max(xs) + radius - origin_x)
    y_range = (min(ys) - radius - origin_y, max(ys) + radius - origin_y)
    grid = build_offset_grid(
        lambda xm, ym: -surface_depth(ym + origin_y),
        x_range,
        y_range,
        parameters.ball,
        spacing_x=parameters.grid_spacing_x,
        spacing_y=parameters.grid_spacing_y,
    )
    radius_setup = Setup(
        "Fretboard_radius",
        f"Fretboard playing surface - {surface.radius:g} mm radius, ball nose",
        (
            raster_finish(
                "Radius surface",
                grid,
                parameters.ball,
                x_range=x_range,
                y_range=y_range,
                step_over=parameters.finishing_step_over,
            ),
        ),
        (
            "Blank on the two index pins, same work zero.",
            f"The crown ends {skim:g} mm below the blank top; the edges "
            f"{surface_depth(max(ys)):.2f} mm.",
        ),
        reference_points,
        parameters.ball,
    )

    inlay_paths: list[Toolpath] = []
    for marker in geometry.inlay_layout.markers:
        centre_y = sum(point.y for point in marker.outline) / len(marker.outline)
        inlay_paths.append(
            pocket(
                f"Inlay fret {marker.fret_number} at y={centre_y:.0f}",
                machine_polygon(marker.outline),
                skim + geometry.inlay_layout.depth,
                parameters.inlay,
                start_depth=skim,
            )
        )
    inlays = Setup(
        "Fretboard_inlays",
        f"Fretboard inlay pockets - {geometry.inlay_layout.depth:g} mm below the crown",
        tuple(inlay_paths),
        (
            "Same fixture and X/Y zero; change to the inlay end mill and "
            "re-touch Z on the blank top.",
            "Barbs narrower than the tool are left uncut.",
        ),
        reference_points,
        parameters.inlay,
    )

    slot_paths: list[Toolpath] = []
    slot_tool = parameters.slot
    passes = max(1, math.ceil(geometry.fret_slot_depth / slot_tool.step_down - 1e-9))
    for number, slot in enumerate(geometry.fret_layout.slots, start=1):
        half = max(abs(slot.start.y), abs(slot.end.y)) + parameters.slot_overshoot
        builder = PathBuilder(
            f"Fret {number} slot",
            safe_height=slot_tool.safe_height,
            feed_rate=slot_tool.feed_rate,
            plunge_rate=slot_tool.plunge_rate,
        )
        model_x = slot.start.x
        sample_ys = _steps(-half, half, 1.0)
        for index in range(1, passes + 1):
            depth = geometry.fret_slot_depth * index / passes
            ordered = sample_ys if index % 2 == 1 else list(reversed(sample_ys))
            start_y = ordered[0]
            start_z = -(surface_depth(start_y) + depth)
            if index == 1:
                builder.rapid_to(model_x - origin_x, start_y - origin_y)
                builder.rapid_down_to(-surface_depth(start_y))
            builder.plunge_to(start_z)
            for y in ordered[1:]:
                builder.cut_to(
                    model_x - origin_x, y - origin_y, -(surface_depth(y) + depth)
                )
        slot_paths.append(builder.build())
    slots = Setup(
        "Fretboard_slots",
        f"Fretboard fret slots - {geometry.fret_slot_width:g} mm wide, "
        f"{geometry.fret_slot_depth:g} mm below the radius",
        tuple(slot_paths),
        (
            "Same fixture and X/Y zero; change to the fret-slot cutter and "
            "re-touch Z on the blank top.",
            f"Each slot follows the radius across the board in {passes} passes.",
        ),
        reference_points,
        slot_tool,
    )

    outline_setup = Setup(
        "Fretboard_outline",
        "Fretboard outline - tapered profile with tabs",
        (
            profile(
                "Fretboard outline with tabs",
                machine_polygon(outline),
                parameters.blank_thickness + flat.through_overshoot,
                flat,
                with_tabs=True,
            ),
        ),
        (
            "Same fixture and X/Y zero; back to the flat end mill, re-touch Z.",
            f"Leaves {flat.tab_count} tabs {flat.tab_height:g} mm high; saw and "
            "sand them off.",
        ),
        reference_points,
        flat,
    )
    preview = machine_polygon(outline)
    return FretboardMachiningPlan(
        index_pins,
        radius_setup,
        inlays,
        slots,
        outline_setup,
        stock_length=stock.length,
        stock_width=stock.width,
        stock_thickness=parameters.blank_thickness,
        origin_x=origin_x,
        origin_y=origin_y,
        index_pin_positions=pins,
        preview_outlines=(preview,) * 5,
    )


def _steps(start: float, end: float, spacing: float) -> list[float]:
    count = max(1, math.ceil((end - start) / spacing - 1e-9))
    return [start + (end - start) * index / count for index in range(count + 1)]
