"""Plan the single-sided machining of the Prototype001 fretboard.

The fretboard blank is a flat board ``blank_thickness`` thick, glue
face down, held on two dowels in the waste beyond the nut and beyond
the end — or, a bought blank too short for them, glued on a longer
carrier board that takes them. Everything is cut from the top in one
fixturing, with tool changes between programs (re-touch Z on the blank
top after each):

1. ball nose — the radiused playing surface;
2. small end mill — the inlay pockets, measured from the crown;
3. fret-slot bit — 24 slots that follow the radius across the board;
4. flat end mill — a locking nut's shelf, when the board runs on under
   the nut, then the tapered outline with rounded nut corners and tabs.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from ..geometry.fretboard import shortened
from ..geometry.primitives import Line2D, Point2D, rounded_polygon_points
from .exceptions import ToolpathError
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .inlays import inlay_fit_outline
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .planar import polygon_bounds
from .surfacing import build_offset_grid, raster_finish, raster_rough
from .toolpath import PathBuilder, Toolpath

if TYPE_CHECKING:
    from ..presets import Prototype001Geometry


FRETBOARD_FIXTURE = "Fretboard blank on the index pins"
"""How the board's programs hold the blank (``Setup.fixture``)."""

INLAID_FIXTURE = "Fretboard blank on the index pins, the inlays glued in"
"""How the blank is held once the inlay pieces are glued in and levelled
(for the scallops, cut through them)."""

SLOPE_STEP = 0.5
"""Height of each terrace cut down a slotted nut's board slope, in mm."""

SCALLOP_GRID_SPACING = 0.5
"""How finely, in mm along the neck, the scallops' surface is sampled for
the ball nose: a space 11 mm long between its lands needs it."""


def _flat_tool() -> MachiningParameters:
    return MachiningParameters(stock_margin=35.0, tab_height=3.0)


def _ball_tool() -> MachiningParameters:
    return MachiningParameters(tool_tip="ball", stock_margin=35.0)


def _slot_tool() -> MachiningParameters:
    # Fast and shallow: a 0.6 mm cutter snaps otherwise (the machining
    # form's fret_slot_spindle_speed and fret_slot_step_down).
    return MachiningParameters(
        tool_diameter=0.6,
        spindle_speed=30000.0,
        feed_rate=300.0,
        plunge_rate=100.0,
        step_down=0.2,
        stock_margin=35.0,
    )


def _inlay_tool() -> MachiningParameters:
    # As the fret-slot cutter: fast and shallow (the machining form's
    # inlay_spindle_speed and inlay_step_down).
    return MachiningParameters(
        tool_diameter=1.0,
        spindle_speed=30000.0,
        feed_rate=300.0,
        plunge_rate=100.0,
        step_down=0.2,
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
        blank_length: The blank's length as bought, the board centred on
            it; ``None`` cuts it from stock ``flat.stock_margin`` longer
            at each end, lengthened where the index pins need it.
        blank_width: The blank's width, the board centred on it; ``None``
            leaves ``flat.stock_margin`` of waste each side.
        carrier_thickness: A carrier board the blank is glued on, which
            takes the index pins past a given blank's ends where it is too
            short for them; the pins are drilled through it. ``None``: no
            carrier, and the pins must fit in the blank.
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
    blank_length: float | None = None
    blank_width: float | None = None
    carrier_thickness: float | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("blank_thickness", self.blank_thickness),
            ("finishing_step_over", self.finishing_step_over),
            ("grid_spacing_x", self.grid_spacing_x),
            ("grid_spacing_y", self.grid_spacing_y),
            ("blank_length", self.blank_length),
            ("blank_width", self.blank_width),
            ("carrier_thickness", self.carrier_thickness),
        ):
            if value is None:
                continue
            if not math.isfinite(value) or value <= 0.0:
                raise ToolpathError(f"{name} must be finite and positive.")
        if not math.isfinite(self.slot_overshoot) or self.slot_overshoot < 0.0:
            raise ToolpathError("slot_overshoot must be finite and non-negative.")
        if self.ball.tool_tip != "ball":
            raise ToolpathError("The surfacing tool must be a ball nose.")

    def with_form_settings(
        self, machining: MachiningParameters
    ) -> FretboardMachiningParameters:
        """Return these with the form's small cutters and blank set.

        From the machining form: the fret-slot cutter's
        (``fret_slot_spindle_speed``, ``fret_slot_step_down``) and the
        inlay cutter's (``inlay_spindle_speed``, ``inlay_step_down``)
        speeds and step-downs, and the blank (``fretboard_blank_*``,
        ``fretboard_carrier_thickness``).
        """
        return replace(
            self,
            blank_thickness=machining.fretboard_blank_thickness,
            blank_length=machining.fretboard_blank_length,
            blank_width=machining.fretboard_blank_width,
            carrier_thickness=machining.fretboard_carrier_thickness,
            slot=replace(
                self.slot,
                spindle_speed=machining.fret_slot_spindle_speed,
                step_down=machining.fret_slot_step_down,
            ),
            inlay=replace(
                self.inlay,
                spindle_speed=machining.inlay_spindle_speed,
                step_down=machining.inlay_step_down,
            ),
        )


@dataclass(frozen=True, slots=True)
class FretboardCarrier:
    """The board a fretboard blank is glued on to take the index pins.

    Args:
        length: Its least length, in mm.
        width: Its least width (the blank's), in mm.
        thickness: Its thickness, in mm.
        nut_overhang: How far it reaches past the blank's nut end.
        end_overhang: How far it reaches past the blank's far end.
    """

    length: float
    width: float
    thickness: float
    nut_overhang: float
    end_overhang: float


@dataclass(frozen=True, slots=True)
class FretboardMachiningPlan:
    """The setups that machine one fretboard, in running order.

    ``carrier`` is the board the blank is glued on, or ``None``;
    ``scallops`` the program hollowing a scalloped board's fret spaces, or
    ``None``.
    """

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
    carrier: FretboardCarrier | None = None
    scallops: Setup | None = None

    @property
    def setups(self) -> tuple[Setup, ...]:
        # The scallops after the inlays are set and the slots cut, before
        # the board is parted from its blank.
        hollowed = (self.scallops,) if self.scallops is not None else ()
        return (
            self.index_pins,
            self.radius,
            self.inlays,
            self.slots,
            *hollowed,
            self.outline,
        )


def _given_blank(
    outline: tuple[Point2D, ...],
    automatic: StockBounds,
    parameters: FretboardMachiningParameters,
) -> StockBounds:
    """Return the blank as given (a bought one), the board centred on it.

    A length or width not given is the automatic blank's.

    Raises:
        ToolpathError: If the board does not fit on it.
    """
    min_x, min_y, max_x, max_y = polygon_bounds(outline)
    length = parameters.blank_length or automatic.length
    width = parameters.blank_width or automatic.width
    if length < max_x - min_x:
        raise ToolpathError(
            f"The fretboard is {max_x - min_x:.1f} mm long: a {length:g} mm "
            "blank (fretboard_blank_length) is too short for it."
        )
    if width < max_y - min_y:
        raise ToolpathError(
            f"The fretboard is {max_y - min_y:.1f} mm wide at its widest: a "
            f"{width:g} mm blank (fretboard_blank_width) is too narrow for it."
        )
    middle_x, middle_y = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
    return StockBounds(
        middle_x - length / 2.0,
        middle_y - width / 2.0,
        middle_x + length / 2.0,
        middle_y + width / 2.0,
    )


def fretboard_outline_polygon(geometry: Prototype001Geometry) -> tuple[Point2D, ...]:
    """Return the board's plan outline with its rounded nut corners.

    The corners are the surface's own end rows, so slanted frets give a
    slanted nut end and board end; its edges run through the rows along
    a heel's flare (``FretboardSurface.outline_rows``). A board that runs
    on under a locking nut ends the nut's seat behind the nut line
    instead; one reaching a round heel's end is rounded with it
    (``NeckOutline.trimmed``).
    """
    first, *rest = geometry.fretboard_surface.outline_rows()
    radius = geometry.fret_layout.fretboard.nut_corner_radius
    nut = geometry.locking_nut
    back = nut.seat_length if nut is not None and nut.on_fretboard else 0.0
    vertices = [
        Point2D(first[0].x - back, first[0].y),
        *(Point2D(row[0].x, row[0].y) for row in rest),
        *(Point2D(row[-1].x, row[-1].y) for row in reversed(rest)),
        Point2D(first[-1].x - back, first[-1].y),
    ]
    radii = [radius, *[0.0] * (len(vertices) - 2), radius]
    return geometry.neck_outline.trimmed(
        rounded_polygon_points(vertices, radii, samples_per_corner=8)
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
    given = parameters.blank_length is not None or parameters.blank_width is not None
    if given:
        stock = _given_blank(outline, stock, parameters)
    pins, pin_stock = resolve_index_pins(outline, [sweep], flat, stock)
    carrier: FretboardCarrier | None = None
    if parameters.blank_length is not None and pin_stock.length > stock.length:
        # A bought blank too short for the dowels: they go in a carrier.
        if parameters.carrier_thickness is None:
            raise ToolpathError(
                f"The index pins do not fit in the {stock.length:g} mm "
                f"fretboard blank: they need {pin_stock.length:.0f} mm. Glue "
                "it on a longer carrier board (fretboard_carrier_thickness) "
                "that takes them, or use a longer blank."
            )
    else:
        stock = pin_stock
    if parameters.carrier_thickness is not None:
        carrier = FretboardCarrier(
            length=pin_stock.length,
            width=stock.width,
            thickness=parameters.carrier_thickness,
            nut_overhang=stock.min_x - pin_stock.min_x,
            end_overhang=pin_stock.max_x - stock.max_x,
        )
    # A carrier is drilled through with the blank, into the spoilboard.
    pin_depth = (
        parameters.blank_thickness
        + (0.0 if carrier is None else carrier.thickness)
        + flat.through_overshoot
    )
    origin_x, origin_y = pins[0]
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])

    def machine(point: Point2D) -> Point2D:
        return Point2D(point.x - origin_x, point.y - origin_y)

    def machine_polygon(points: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
        return tuple(machine(point) for point in points)

    def surface_depth(model_y: float) -> float:
        """Depth of the radiused surface below the blank top at lateral y."""
        drop = surface.radius - math.sqrt(max(0.0, surface.radius**2 - model_y**2))
        return skim + drop

    nut = geometry.locking_nut
    slotted = nut is not None and not nut.is_locking
    # After the radius the blank's own top is left only round the board:
    # every later program's Z zero is there, as the radius program's was.
    touch_z = (
        "re-touch Z on the blank's untouched top beside the board (Z zero, as "
        "for Fretboard_radius) - not on the radiused surface, which lies "
        f"{skim:g} mm lower at the crown: touched there, every cut would go "
        "that much too deep."
    )

    min_x, min_y, max_x, max_y = polygon_bounds(outline)
    if given:
        blank_note = (
            f"Blank: {stock.length:g} x {stock.width:g} x "
            f"{parameters.blank_thickness:g} mm, the board centred on it: "
            f"{min_x - stock.min_x:.1f} mm of waste at each end, "
            f"{min_y - stock.min_y:.1f} mm each side."
        )
    else:
        blank_note = (
            f"Blank: at least {stock.length:.0f} x {stock.width:.0f} x "
            f"{parameters.blank_thickness:g} mm."
        )
    if carrier is None:
        fixing: tuple[str, ...] = (
            "Clamp the blank glue face down on a spoilboard.",
            blank_note,
        )
    else:
        fixing = (
            blank_note,
            f"Glue (or tape) the blank glue face down on a carrier board at "
            f"least {carrier.length:.0f} x {carrier.width:g} x "
            f"{carrier.thickness:g} mm, reaching {carrier.nut_overhang:.0f} mm "
            f"past the blank's nut end and {carrier.end_overhang:.0f} mm past "
            "its far end, and clamp the carrier on a spoilboard: the pins are "
            "drilled through it. The outline cuts "
            f"{flat.through_overshoot:g} mm into it, so the board stays on it "
            "until parted from it.",
        )
    index_pins = Setup(
        "Fretboard_index_pins",
        f"Fretboard index pins - drill both {flat.pin_diameter:g} mm dowel "
        "holes through the "
        + ("blank" if carrier is None else "blank and its carrier"),
        tuple(
            drill(
                f"Index pin {index}",
                machine(Point2D(x, y)),
                flat.pin_diameter,
                pin_depth,
                flat,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            *fixing,
            "Set X/Y zero at the index pin 1 position and Z zero on the blank top.",
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
    # A thick blank is roughed down in layers no deeper than the ball's
    # step-down before the finishing pass follows the radius.
    deepest = surface_depth(max(abs(min(ys)), abs(max(ys))))
    roughing = (
        (
            raster_rough(
                "Radius roughing",
                grid,
                parameters.ball,
                x_range=x_range,
                y_range=y_range,
                step_over=parameters.ball.raster_spacing,
            ),
        )
        if deepest > parameters.ball.step_down
        else ()
    )
    radius_setup = Setup(
        "Fretboard_radius",
        f"Fretboard playing surface - {surface.radius:g} mm radius, ball nose",
        (
            *roughing,
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
            *(
                (
                    f"Roughed first in layers of at most "
                    f"{parameters.ball.step_down:g} mm: the surface goes down "
                    f"to {deepest:.1f} mm.",
                )
                if roughing
                else ()
            ),
        ),
        reference_points,
        parameters.ball,
        fixture=FRETBOARD_FIXTURE,
    )

    inlay_paths: list[Toolpath] = []
    for marker in geometry.inlay_layout.markers:
        centre_y = sum(point.y for point in marker.outline) / len(marker.outline)
        inlay_paths.append(
            pocket(
                f"Inlay fret {marker.fret_number} at y={centre_y:.0f}",
                machine_polygon(
                    inlay_fit_outline(marker.outline, parameters.inlay.tool_radius)
                ),
                skim + geometry.inlay_layout.depth,
                parameters.inlay,
                start_depth=skim,
                # The wood left inside a marker (an ankh's loop), as its
                # piece's hole is cut.
                islands=[
                    machine_polygon(
                        inlay_fit_outline(hole, parameters.inlay.tool_radius)
                    )
                    for hole in marker.holes
                ],
            )
        )
    nut_slot_notes: tuple[str, ...] = ()
    if slotted and nut is not None:
        # The nut's slot, closed behind by the board's lip: the small
        # inlay end mill fits it.
        inlay_paths.append(
            pocket(
                "Nut slot",
                machine_polygon(
                    nut.slot_outline(reach=parameters.inlay.tool_radius + 1.0)
                ),
                parameters.blank_thickness - nut.shelf_height,
                parameters.inlay,
                start_depth=skim,
            )
        )
        where = (
            f"{nut.spec.set_back:g} mm behind the zero fret on the nut line"
            if nut.zero_fret
            else "behind the nut line"
        )
        nut_slot_notes = (
            f"The nut's slot: {nut.spec.depth:g} mm wide {where}, "
            f"{nut.spec.height:g} mm below the crown; the board runs on "
            f"{nut.spec.lip:g} mm at full height behind it, then slopes to the "
            f"glue face over {nut.spec.taper:g} mm (stepped in the outline "
            "program).",
        )
    inlays = Setup(
        "Fretboard_inlays",
        f"Fretboard inlay pockets - {geometry.inlay_layout.depth:g} mm below the crown"
        + (" - and the nut's slot" if slotted else ""),
        tuple(inlay_paths),
        (
            "Same fixture and X/Y zero; change to the inlay end mill and " + touch_z,
            "Each pocket follows its marker rounded to the tool, as its "
            "piece is cut (Fretboard_inlay_pieces); barbs narrower than the "
            "tool are left out of both.",
            *nut_slot_notes,
        ),
        reference_points,
        parameters.inlay,
        fixture=FRETBOARD_FIXTURE,
    )

    slot_paths: list[Toolpath] = []
    slot_tool = parameters.slot
    passes = max(1, math.ceil(geometry.fret_slot_depth / slot_tool.step_down - 1e-9))
    zero = geometry.fret_layout.zero_fret_slot
    named_slots = [
        *((("Zero fret slot", zero),) if zero is not None else ()),
        *(
            (f"Fret {number} slot", slot)
            for number, slot in enumerate(geometry.fret_layout.slots, start=1)
        ),
    ]
    inset = geometry.fret_layout.slot_end_inset
    for slot_name, slot in named_slots:
        if inset > 0.0:
            # A blind slot: the cutter's edge stops inset short of each of
            # the board's edges.
            cut = shortened(slot, inset + slot_tool.tool_radius)
            low, high = sorted((cut.start.y, cut.end.y))
        else:
            # Out past the board's edges (and its end, where a board cut at
            # the heel's end ends a leaning slot short).
            low = min(slot.start.y, slot.end.y) - parameters.slot_overshoot
            high = max(slot.start.y, slot.end.y) + parameters.slot_overshoot
        builder = PathBuilder(
            slot_name,
            safe_height=slot_tool.safe_height,
            feed_rate=slot_tool.feed_rate,
            plunge_rate=slot_tool.plunge_rate,
        )
        # A slanted slot runs along its own line: X follows Y (from its
        # own end: one cut short at a board's end is off the centre).
        slope = (
            (slot.end.x - slot.start.x) / (slot.end.y - slot.start.y)
            if abs(slot.end.y - slot.start.y) > 1e-9
            else 0.0
        )

        def x_at(y: float, slot: Line2D = slot, slope: float = slope) -> float:
            return slot.start.x + slope * (y - slot.start.y)

        sample_ys = _steps(low, high, 1.0)
        for index in range(1, passes + 1):
            depth = geometry.fret_slot_depth * index / passes
            ordered = sample_ys if index % 2 == 1 else list(reversed(sample_ys))
            start_y = ordered[0]
            start_z = -(surface_depth(start_y) + depth)
            if index == 1:
                builder.rapid_to(x_at(start_y) - origin_x, start_y - origin_y)
                builder.rapid_down_to(-surface_depth(start_y))
            builder.plunge_to(start_z)
            for y in ordered[1:]:
                builder.cut_to(
                    x_at(y) - origin_x,
                    y - origin_y,
                    -(surface_depth(y) + depth),
                )
        slot_paths.append(builder.build())
    binding = geometry.fretboard_binding_width

    def binding_notes(note: str) -> tuple[str, ...]:
        return (note,) if binding > 0.0 else ()

    slots = Setup(
        "Fretboard_slots",
        f"Fretboard fret slots - {geometry.fret_slot_width:g} mm wide, "
        f"{geometry.fret_slot_depth:g} mm below the radius",
        tuple(slot_paths),
        (
            "Same fixture and X/Y zero; change to the fret-slot cutter and " + touch_z,
            f"Each slot follows the radius across the board in {passes} passes "
            f"of {geometry.fret_slot_depth / passes:.2f} mm: "
            + (
                f"blind, it stops {inset:g} mm short of each of the board's "
                "edges, the cutter going down into the board at its ends."
                if inset > 0.0
                else f"it starts {parameters.slot_overshoot:g} mm past the "
                "board's edge, the cutter brought down to 1 mm over the radius "
                "there and fed in from it."
            ),
            *(
                (
                    "The first slot is the zero fret's, on the nut line: the "
                    "scale starts at it, and the nut behind it only guides the "
                    "strings (file its slots a little below the fret's top).",
                )
                if zero is not None
                else ()
            ),
            *(
                (
                    f"Nip each fret's tang back {inset:g} mm at both ends (a "
                    "little more does no harm), its crown running on to the "
                    "edge, before pressing it in.",
                )
                if inset > 0.0
                else binding_notes(
                    "The slots run out through the board's edges; nip each "
                    "fret's tang back over the binding before pressing it in."
                )
            ),
        ),
        reference_points,
        slot_tool,
        fixture=FRETBOARD_FIXTURE,
    )

    scallop_setup = _scallop_setup(
        geometry,
        parameters,
        surface_depth,
        (origin_x, origin_y),
        y_range,
        max(abs(y) for y in ys),
        reference_points,
    )

    shelf_paths: list[Toolpath] = []
    shelf_notes: tuple[str, ...] = ()
    if nut is not None and nut.is_locking and nut.on_fretboard:
        # Down to the shelf behind the nut line (behind a zero fret, from
        # the nut's front: the board stands full height under the zero
        # fret), the pocket reaching past the board's sides and end so
        # only that wall is left.
        reach = flat.tool_radius + 1.0
        half = nut.neck_width / 2.0 + reach
        pocket_outline = tuple(
            Point2D(nut.lean * y + dx, y)
            for dx, y in (
                (nut.front, -half),
                (nut.front, half),
                (-nut.seat_length - reach, half),
                (-nut.seat_length - reach, -half),
            )
        )
        shelf_paths.append(
            pocket(
                f"{nut.spec.name} locking nut shelf",
                machine_polygon(pocket_outline),
                parameters.blank_thickness - nut.shelf_height,
                flat,
            )
        )
        shelf_notes = (
            f"The board runs {nut.seat_length:g} mm on past the nut line under "
            f"the {nut.spec.name} locking nut, milled down to its "
            f"{nut.shelf_height:.2f} mm shelf first"
            + (
                f" from {nut.spec.set_back:g} mm behind it, the zero fret's "
                "slot in the full-height board before that."
                if nut.zero_fret
                else "."
            ),
        )
    if slotted and nut is not None and nut.spec.taper > 0.0:
        # The board's slope behind the lip, down to the glue face in
        # SLOPE_STEP terraces with the flat end mill; sand them smooth.
        lip_end = nut.spec.depth + nut.spec.lip
        # Past the board's sides, and a whole tool past its end (waste).
        half = nut.neck_width / 2.0 + flat.tool_radius + 1.0
        far = nut.seat_length + flat.tool_diameter + 1.0
        top = skim
        bottom = parameters.blank_thickness
        count = max(1, math.ceil((bottom - top) / SLOPE_STEP - 1e-9))
        previous = top
        for index in range(1, count + 1):
            depth = top + (bottom - top) * index / count
            # Where the slope comes down to this depth.
            back = lip_end + nut.spec.taper * (depth - top) / (bottom - top)
            terrace = tuple(
                Point2D(nut.lean * y - dx, y)
                for dx, y in ((back, -half), (back, half), (far, half), (far, -half))
            )
            shelf_paths.append(
                pocket(
                    f"Board slope behind the nut, step {index}",
                    machine_polygon(terrace),
                    depth,
                    flat,
                    start_depth=previous,
                )
            )
            previous = depth
        shelf_notes = (
            f"The board's slope behind the nut's lip is cut in {count} "
            f"terraces down to the glue face; sand them into one slope.",
        )
    # A bought blank only a little wider than the board leaves the outline
    # cutter little or no frame for the tabs to hold the board in.
    waste = min(
        min_x - stock.min_x,
        stock.max_x - max_x,
        min_y - stock.min_y,
        stock.max_y - max_y,
    )
    thin_frame = (
        (
            f"Only {waste:.1f} mm of blank beside the board, the outline "
            f"cutter {flat.tool_diameter:g} mm wide: the frame round it is "
            "thin or cut away, so fix the blank down (double-sided tape) for "
            "the tabs not to be all that holds the board.",
        )
        if carrier is None and waste < flat.tool_diameter + 2.0
        else ()
    )
    outline_setup = Setup(
        "Fretboard_outline",
        "Fretboard outline - tapered profile with tabs",
        (
            *shelf_paths,
            profile(
                "Fretboard outline with tabs",
                machine_polygon(outline),
                parameters.blank_thickness + flat.through_overshoot,
                flat,
                with_tabs=True,
            ),
        ),
        (
            "Same fixture and X/Y zero; back to the flat end mill and " + touch_z,
            f"Leaves {flat.tab_count} tabs {flat.tab_height:g} mm high; saw and "
            "sand them off.",
            *thin_frame,
            *shelf_notes,
            *binding_notes(
                f"The board is cut {binding:g} mm narrower each side for its "
                f"binding: glue {binding:g} mm strips along both long edges, "
                "flush with the top, then level them to the radius."
            ),
        ),
        reference_points,
        flat,
        fixture=FRETBOARD_FIXTURE if scallop_setup is None else INLAID_FIXTURE,
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
        preview_outlines=(preview,) * (5 if scallop_setup is None else 6),
        carrier=carrier,
        scallops=scallop_setup,
    )


RERADIUS_OVERRUN = 10.0
"""How far past a board already made, every way, its radius program's
passes run (``plan_fretboard_radius``), in mm."""


def plan_fretboard_radius(
    geometry: Prototype001Geometry,
    parameters: FretboardMachiningParameters,
) -> Setup:
    """Return a program cutting only the fretboard's radius, for a board
    already made: to give it another radius.

    Its work zero is the centre of the board's end at the body, on the
    board's top, X running from there toward the nut; the passes run
    along the board ``RERADIUS_OVERRUN`` past it every way (past its
    edges at the edges' depth), the first from the end along the centre
    line, then out to one side and the other. The crown ends
    ``blank_thickness`` less the design's board thickness under the top:
    the blank is the board as it is now. Roughed first in layers when it
    goes down deeper than the ball nose's step-down.

    Raises:
        ToolpathError: If the board is not as thick now as the design's.
    """
    surface = geometry.fretboard_surface
    skim = parameters.blank_thickness - surface.center_thickness
    if skim < 0.0:
        raise ToolpathError(
            "The board must be at least as thick now (fretboard_blank_thickness) "
            "as the fretboard's thickness it is cut to."
        )
    ball = parameters.ball
    outline = fretboard_outline_polygon(geometry)
    nut_x = min(point.x for point in outline)
    end_x = _centre_line_end(outline)

    def depth(x: float, y: float) -> float:
        """How far under the board's top the radius lies, held past its
        edges and ends at theirs."""
        along = min(max(x, nut_x), end_x)
        lateral = min(abs(y), surface.half_width_at(along))
        drop = surface.radius - math.sqrt(max(0.0, surface.radius**2 - lateral**2))
        return skim + drop

    # X from the end toward the nut (the radius is alike either side of
    # the centre line, so the cut is the same turned round).
    half = max(abs(point.y) for point in outline) + RERADIUS_OVERRUN
    x_range = (-RERADIUS_OVERRUN, end_x - nut_x + RERADIUS_OVERRUN)
    grid = build_offset_grid(
        lambda x, y: -depth(end_x - x, y),
        x_range,
        (-half, half),
        ball,
        spacing_x=parameters.grid_spacing_x,
        spacing_y=parameters.grid_spacing_y,
    )
    # Each pass type from the centre line out, one side and then the other.
    deepest = max(depth(x, half) for x in (nut_x, end_x))
    toolpaths: list[Toolpath] = []
    if deepest > ball.step_down:
        for name, y_range in (
            ("Radius roughing, +Y side", (0.0, half)),
            ("Radius roughing, -Y side", (-half, -ball.raster_spacing)),
        ):
            toolpaths.append(
                raster_rough(
                    name,
                    grid,
                    ball,
                    x_range=x_range,
                    y_range=y_range,
                    step_over=ball.raster_spacing,
                )
            )
    for name, y_range in (
        ("Radius surface, +Y side", (0.0, half)),
        ("Radius surface, -Y side", (-half, -parameters.finishing_step_over)),
    ):
        toolpaths.append(
            raster_finish(
                name,
                grid,
                ball,
                x_range=x_range,
                y_range=y_range,
                step_over=parameters.finishing_step_over,
            )
        )
    return Setup(
        "Fretboard_radius_only",
        f"Fretboard playing surface only - {surface.radius:g} mm radius on a "
        "board already made, ball nose",
        tuple(toolpaths),
        (
            "A board already made, frets out, along X: its end at the body at "
            "X 0, its nut end toward +X, its centre line on Y 0.",
            f"The passes run {RERADIUS_OVERRUN:g} mm past the board every way.",
            f"The crown ends {skim:g} mm under the board's top, the edges "
            f"{depth(end_x, half):.2f} mm at the end: the board's thickness now "
            "is fretboard_blank_thickness, the one it is cut to the "
            "fretboard's thickness.",
            *(
                (
                    f"Roughed first in layers of at most {ball.step_down:g} mm: "
                    f"the surface goes down to {deepest:.1f} mm.",
                )
                if deepest > ball.step_down
                else ()
            ),
        ),
        tool=ball,
        work_zero="the centre of the fretboard's end at the body, Z on its top there",
    )


def _centre_line_end(outline: tuple[Point2D, ...]) -> float:
    """Return the X where the board's centre line (Y 0) leaves it at its
    far end: the centre of the end, square, slanted or round."""
    crossings = [
        a.x + (b.x - a.x) * (0.0 - a.y) / (b.y - a.y)
        for a, b in zip(outline, (*outline[1:], outline[0]), strict=True)
        if (a.y <= 0.0 < b.y) or (b.y <= 0.0 < a.y)
    ]
    return max(crossings)


def _scallop_setup(
    geometry: Prototype001Geometry,
    parameters: FretboardMachiningParameters,
    surface_depth: Callable[[float], float],
    origin: tuple[float, float],
    y_range: tuple[float, float],
    half_width: float,
    reference_points: tuple[tuple[float, float], ...],
) -> Setup | None:
    """Return the program hollowing the scalloped fret spaces, or ``None``.

    The ball nose rasters along the neck over the scalloped spaces only,
    down to the radiused surface less the scallop under it (drop-cutter,
    so it never cuts below it), on a grid ``SCALLOP_GRID_SPACING`` along
    the neck; roughed first in layers if the scallops go deeper than the
    ball's step-down.
    """
    scallops = geometry.fretboard_scallops
    if scallops is None:
        return None
    ball = parameters.ball
    origin_x, origin_y = origin
    stations = scallops.surface.station_positions
    first, last = stations[scallops.from_fret], stations[scallops.surface.fret_count]
    # Leaning frets lean their spaces: as far again at the board's edges.
    lean = half_width * max(abs(scallops.surface.skew.at(x)) for x in (first, last))
    x_range = (
        first - lean - ball.tool_radius - origin_x,
        last + lean + ball.tool_radius - origin_x,
    )

    def depth(xm: float, ym: float) -> float:
        x, y = xm + origin_x, ym + origin_y
        return surface_depth(y) + scallops.depth_at(x, y)

    grid = build_offset_grid(
        lambda xm, ym: -depth(xm, ym),
        x_range,
        y_range,
        ball,
        spacing_x=SCALLOP_GRID_SPACING,
        spacing_y=parameters.grid_spacing_y,
    )
    roughing = (
        (
            raster_rough(
                "Scallop roughing",
                grid,
                ball,
                x_range=x_range,
                y_range=y_range,
                step_over=ball.raster_spacing,
            ),
        )
        if scallops.depth > ball.step_down
        else ()
    )
    # The tightest scallop: its arc's radius, against the ball's.
    tightest = min(
        _arc_radius(stations[n + 1] - stations[n] - 2.0 * scallops.land, scallops.depth)
        for n in scallops.fret_numbers
    )
    where = "the nut" if scallops.from_fret == 0 else f"fret {scallops.from_fret}"
    # What the scallops leave of the inlays they cut through.
    inlays = geometry.inlay_layout
    under = [
        max(scallops.depth_at(p.x, p.y) for p in marker.outline)
        for marker in inlays.markers
    ]
    under = [depth for depth in under if depth > 0.0]
    inlay_notes = (
        (
            f"The inlay pockets are {inlays.depth:g} mm deep, their pieces from "
            f"a sheet that thick: a scallop leaves at least "
            f"{inlays.depth - max(under):.1f} mm of each piece under it.",
        )
        if under
        else ()
    )
    return Setup(
        "Fretboard_scallops",
        f"Fretboard scallops - {scallops.depth:g} mm deep between the frets "
        f"from {where} on, ball nose",
        (
            *roughing,
            raster_finish(
                "Scallops",
                grid,
                ball,
                x_range=x_range,
                y_range=y_range,
                step_over=parameters.finishing_step_over,
            ),
        ),
        (
            "Glue the inlay pieces in and level them with the radius before "
            "this program: the scallops are cut through them.",
            "Same fixture and X/Y zero; the ball nose as for Fretboard_radius, "
            "Z zero again on the blank's untouched top beside the board.",
            f"Each fret space from {where} on is hollowed {scallops.depth:g} mm "
            f"at its middle, {scallops.land:g} mm left flat either side of each "
            "fret for its foot.",
            *inlay_notes,
            *(
                (
                    f"The tightest scallop is a {tightest:.1f} mm radius, under "
                    f"the ball's {ball.tool_radius:g} mm: it comes out shallower "
                    "there (a smaller ball reaches it).",
                )
                if tightest < ball.tool_radius
                else ()
            ),
        ),
        reference_points,
        ball,
        fixture=INLAID_FIXTURE,
    )


def _arc_radius(chord: float, depth: float) -> float:
    """Return the radius of a circular arc ``depth`` deep over ``chord``."""
    return (chord**2 / 4.0 + depth**2) / (2.0 * depth)


def _steps(start: float, end: float, spacing: float) -> list[float]:
    count = max(1, math.ceil((end - start) / spacing - 1e-9))
    return [start + (end - start) * index / count for index in range(count + 1)]
