"""Plan the two-sided machining of the Prototype001 neck.

The neck blank is planed to ``blank_thickness`` with its top face the
fretboard glue plane (model ``Z = 0``). Two dowels in the waste beyond
the headstock tip and beyond the heel, on the centerline, locate it in
both setups:

* **top** — truss-rod channel, the 8-degree headstock face as a Z-limited
  raster with the flat end mill, and shallow centre marks for the tuner
  holes (which must be drilled perpendicular to the angled face, so they
  are left to a drill press with an 8-degree wedge);
* **back** (flipped about the centerline) — Z-limited roughing of the
  neck back and headstock back with the flat end mill, ball-nose
  finishing, and finally the plan outline cut through the remaining
  skin with holding tabs.

Every surface is a height function in the machine frame; the drop-cutter
offset grids in ``surfacing`` keep the tool from gouging.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Literal

from ..geometry.body import body_part
from ..geometry.primitives import Point2D, point_in_polygon
from .body import plan_body_machining
from .engraving import engraving_path, engraving_tool
from .exceptions import ToolpathError
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .planar import polygon_bounds
from .surfacing import (
    build_offset_grid,
    interpolate_rows,
    offset_sampled_surface,
    raster_finish,
    raster_rough,
    sample_surface,
)
from .toolpath import Toolpath

if TYPE_CHECKING:
    from ..geometry.neck import HeadstockSolid, TrussRodChannel
    from ..presets import Prototype001Geometry


def _flat_tool() -> MachiningParameters:
    return MachiningParameters(stock_margin=35.0)


def _ball_tool() -> MachiningParameters:
    return MachiningParameters(tool_tip="ball", stock_margin=35.0)


@dataclass(frozen=True, slots=True)
class NeckMachiningParameters:
    """Tools, blank and surfacing settings for the neck.

    Args:
        flat: The 6 mm flat end mill used for the truss-rod channel,
            headstock face, tuner marks, roughing, and the outline.
        ball: The ball nose of the same diameter used to finish the back.
        blank_thickness: Planed thickness of the neck blank; ``None`` (the
            default) for the thinnest that holds the neck and headstock.
            Raised automatically when the headstock needs more.
        blank: ``"solid"`` for one plank as thick as the headstock needs;
            ``"laminated"`` to machine the neck from its own plank first
            and glue a block under the headstock end afterwards, the
            headstock then cut in programs of its own (see
            ``plan_neck_machining``).
        skin: Wood left under the part (at the glue-plane side) outside
            the outline and along the back's edges, so the neck stays in
            its waste frame until the tabbed outline cut.
        roughing_step_over: Raster step for roughing, as a fraction of
            the tool diameter.
        finishing_step_over: Raster step for the ball finish, in
            millimetres (scallop height is step² / 8r).
        face_finish_step_over: Raster step for the flat-tool pass that
            finishes the headstock face plane, in millimetres.
        grid_spacing_x: Drop-cutter grid spacing along the neck; the
            finishing raster samples the surface at this spacing too.
        grid_spacing_y: Drop-cutter grid spacing across the neck. Keep
            ``finishing_step_over`` a whole multiple of it so every pass
            runs exactly on grid rows and no interpolation is involved.
        tuner_mark_depth: Depth of the centre marks left for the tuner
            holes on the headstock face.
    """

    flat: MachiningParameters = field(default_factory=_flat_tool)
    ball: MachiningParameters = field(default_factory=_ball_tool)
    blank_thickness: float | None = None
    blank: Literal["solid", "laminated"] = "solid"
    skin: float = 2.0
    roughing_step_over: float = 0.6
    finishing_step_over: float = 0.75
    face_finish_step_over: float = 2.0
    grid_spacing_x: float = 1.0
    grid_spacing_y: float = 0.25
    tuner_mark_depth: float = 0.5

    def __post_init__(self) -> None:
        if self.blank_thickness is not None and (
            not math.isfinite(self.blank_thickness) or self.blank_thickness <= 0.0
        ):
            raise ToolpathError("blank_thickness must be finite and positive.")
        for name, value in (
            ("skin", self.skin),
            ("finishing_step_over", self.finishing_step_over),
            ("face_finish_step_over", self.face_finish_step_over),
            ("grid_spacing_x", self.grid_spacing_x),
            ("grid_spacing_y", self.grid_spacing_y),
            ("tuner_mark_depth", self.tuner_mark_depth),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ToolpathError(f"{name} must be finite and positive.")
        if self.blank not in ("solid", "laminated"):
            raise ToolpathError('blank must be "solid" or "laminated".')
        if not 0.0 < self.roughing_step_over <= 1.0:
            raise ToolpathError("roughing_step_over must lie in (0, 1].")
        if self.ball.tool_tip != "ball":
            raise ToolpathError("The finishing tool must be a ball nose.")


@dataclass(frozen=True, slots=True)
class HeadstockBlock:
    """The block glued under a plank's headstock end to make a laminated blank.

    Model frame: X from the nut (the headstock is at negative X), Y across.

    Args:
        start_x: Where the block starts, nut side: where the headstock's
            back first reaches below the plank.
        end_x: Where it ends, just past the headstock's tip (short of the
            tip's index pin, which stays in the plank alone).
        width: Its width, centred on the neck.
        thickness: Its thickness below the plank: as thick as the plank,
            or more when the headstock needs it.
    """

    start_x: float
    end_x: float
    width: float
    thickness: float

    @property
    def length(self) -> float:
        """Return the block's length along the neck."""
        return self.start_x - self.end_x


@dataclass(frozen=True, slots=True)
class NeckMachiningPlan:
    """The setups that machine one neck, in running order.

    ``stock_thickness`` is the whole blank's. A laminated blank is a
    ``plank_thickness`` plank with ``headstock_block`` glued under its
    headstock end (``None`` when the plank alone is thick enough): the
    neck is cut from the plank first, and the ``headstock_*`` setups cut
    the headstock after the block is glued on, before the outline.
    """

    index_pins: Setup
    top: Setup
    back_rough: Setup
    back_finish: Setup
    back_outline: Setup
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float
    origin_y: float
    index_pin_positions: tuple[tuple[float, float], ...]
    preview_outlines: tuple[tuple[Point2D, ...], ...]
    plank_thickness: float = 0.0
    headstock_block: HeadstockBlock | None = None
    headstock_setups: tuple[Setup, ...] = ()
    top_engraving: Setup | None = None
    block_top_setups: tuple[Setup, ...] = ()
    block_back_setups: tuple[Setup, ...] = ()

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the setups in running order.

        A laminated blank's headstock programs come after the neck's own,
        once the block is glued on, and the outline last of all. A
        neck-through blank's body block (its pickup and bridge routes, its
        share of a carve) is cut with the neck's top face, and its back
        after the neck's back.
        """
        return (
            self.index_pins,
            self.top,
            *self.block_top_setups,
            *((self.top_engraving,) if self.top_engraving is not None else ()),
            self.back_rough,
            self.back_finish,
            *self.headstock_setups,
            *self.block_back_setups,
            self.back_outline,
        )


def _lettering_setup(
    geometry: Prototype001Geometry,
    frame: _Frame,
    flat: MachiningParameters,
    face_depth: Callable[[float, float], float],
    after: str,
    reference_points: tuple[tuple[float, float], ...],
) -> Setup | None:
    """Return the V-bit program for the headstock's lettering, or ``None``.

    It follows the finished face (``face_depth``: its Z at a model point),
    so it runs right after ``after`` mills it, before the blank is turned.
    """
    lettering = geometry.headstock_engraving
    if lettering is None:
        return None
    tool = engraving_tool(flat, lettering.depth)
    return Setup(
        "Headstock_engraving",
        f"Headstock face - lettering {lettering.depth:g} mm deep with a V-bit",
        (
            engraving_path(
                lettering,
                frame.point,
                tool,
                lambda point: face_depth(point.x, point.y),
                "Headstock lettering",
            ),
        ),
        (
            f"Same fixture, X/Y and Z zero as {after}, right after it, before "
            f"the blank is turned over; change to a {flat.engraving_tool_angle:g} "
            "degree V-bit and re-touch Z on the glue face.",
            "The bit follows the finished headstock face; its grooves come out "
            f"{tool.tool_diameter:.2f} mm wide.",
        ),
        reference_points,
        tool,
    )


def _round_up(depth: float) -> float:
    """Return ``depth`` rounded up to the next 0.1 mm."""
    return math.ceil(round(depth * 10.0, 6)) / 10.0


def _headstock_block(
    headstock: HeadstockSolid,
    plank: float,
    needed: float,
    tool_diameter: float,
) -> HeadstockBlock | None:
    """Return the block a ``plank``-thick blank needs under its headstock.

    It starts where the headstock's back first falls below the plank and
    runs just past the tip (room for the outline cut, short of the tip's
    index pin); it is as wide as the headstock plus that room either side
    and as thick as the plank — a block is usually cut from the same wood
    — or thicker when the headstock needs more. ``None`` when the plank
    alone holds the headstock.
    """
    if needed - plank <= 1e-9:
        return None
    radians = math.radians(headstock.angle.angle_degrees)
    back_offset = headstock.thickness / math.cos(radians)
    tangent = math.tan(radians)
    # The back plane: face_z(x) - back_offset, falling toward the tip.
    if tangent > 0.0:
        start = headstock.face_pivot_x + (
            -plank + headstock.face_drop + back_offset
        ) / tangent
    else:
        start = 0.0
    start = min(0.0, math.floor(start))
    room = tool_diameter + 2.0
    end = math.floor(-headstock.plan.reach - room)
    half = max(abs(point.y) for point in headstock.plan.boundary)
    width = math.ceil(2.0 * (half + room))
    return HeadstockBlock(start, end, width, max(plank, _round_up(needed - plank)))


def _face_depth_at(
    face_depth: Callable[[float, float], float], point: Point2D
) -> float:
    """Return ``face_depth`` at a model-frame point."""
    return face_depth(point.x, point.y)


def _nut_filler_note(truss: TrussRodChannel, shelf: float) -> tuple[str, ...]:
    """Return the note to fill the route under the nut, if it runs there.

    A headstock-adjusted rod's route starts under the nut seat, so the
    nut would rest only on the wood either side of it; a filler glued
    over the rod, flush with the seat, gives it its whole width back.
    """
    under_nut = [
        boundary
        for boundary in (truss.top_boundary, *(part.boundary for part in truss.pockets))
        if min(p.x for p in boundary) < 0.0 and max(p.x for p in boundary) > -shelf
    ]
    if not under_nut:
        return ()
    width = max(2.0 * max(abs(p.y) for p in boundary) for boundary in under_nut)
    return (
        f"The truss rod's route runs under the nut seat: after fitting the rod, "
        f"glue a wooden filler {width:g} mm wide and {round(shelf, 1):g} mm long (the "
        "nut's seat, behind the fretboard) into it over the rod, flush with "
        "the seat, before gluing the nut, so the nut sits on wood over its "
        "whole width.",
    )


def _adjuster_notes(geometry: Prototype001Geometry) -> tuple[str, ...]:
    """Return how the truss rod's adjuster without a spoke wheel is reached."""
    truss = geometry.truss_rod_channel
    heel_end = truss.neck_outline.last_fret_position + truss.neck_outline.heel_length
    if truss.adjustment_side == "heel" and math.isclose(truss.end_position, heel_end):
        return (
            "The route runs out through the heel's end: the rod's adjuster nut "
            "sits at the heel's end face, turned with the neck off.",
        )
    if truss.adjustment_side == "nut" and truss.access_diameter > 0.0:
        return (
            f"The truss rod's key reaches the adjuster through a "
            f"{truss.access_diameter:g} mm notch behind the nut, the open start "
            "of its hole: a key that needs it longer is drilled on by hand "
            "along the rod's axis.",
        )
    return ()


def _locking_nut_notes(geometry: Prototype001Geometry) -> tuple[str, ...]:
    """Return how to fit a locking nut or a slotted nut, if the neck has one."""
    nut = geometry.locking_nut
    if nut is None:
        return ()
    if not nut.is_locking:
        return (
            f"Fender style nut, {nut.spec.depth:g} mm thick: glue it into the "
            f"slot near the fretboard's end ({nut.spec.height:g} mm deep at the "
            "crown, cut in the fretboard's inlay program), front face on the "
            f"nut line; behind it the board runs on {nut.spec.lip:g} mm, then "
            f"slopes to the neck over {nut.spec.taper:g} mm.",
        )
    seat = (
        f"it stands on the fretboard, which runs on under it {nut.shelf_height:.1f} "
        "mm thick (cut in the fretboard's outline program)"
        if nut.on_fretboard
        else f"it stands on the neck's seat on a {nut.shim:.2f} mm shim"
    )
    return (
        f"{nut.spec.name} locking nut, front face on the nut line: {seat}. "
        f"Drill its two screws' {nut.screw_diameter:g} mm pilot holes by hand "
        f"through the nut, {nut.screw_depth:g} mm into the neck, "
        f"{nut.spec.screw_spacing:g} mm apart and {nut.spec.depth / 2.0:g} mm "
        "behind the nut line.",
    )


def _overrun_truss_route(
    truss: TrussRodChannel, overrun: float
) -> list[tuple[str, tuple[Point2D, ...], float]]:
    """Return the channel, step and pocket, each run on over its neighbours.

    A round cutter leaves its radius in every corner, so where a pocket
    meets the next, narrower part of the route, its end corners would
    stand into the rod's square step and block. Each part therefore runs
    ``overrun`` (the tool's radius) on over its neighbour, deeper than
    that neighbour for that short stretch, and the pocket at the
    adjusting end runs on as far toward the adjuster (its sleeve's bore,
    or the headstock trough); only the channel's anchor end stays as
    drawn. The channel is returned first.
    """
    parts = [
        ("Truss-rod channel", truss.top_boundary, truss.depth),
        *((part.name, part.boundary, part.depth) for part in truss.pockets),
    ]
    spans = [
        (min(p.x for p in boundary), max(p.x for p in boundary))
        for _, boundary, _ in parts
    ]
    first = min(start for start, _ in spans)
    last = max(end for _, end in spans)
    heel = truss.adjustment_side == "heel"
    route = []
    for index, ((name, boundary, depth), (start, end)) in enumerate(
        zip(parts, spans, strict=True)
    ):
        # Every end that meets another part, plus the adjusting end; the
        # channel (first) keeps its anchor end.
        pocket_part = index > 0
        meets_before = start > first + 1e-9 or (not heel and pocket_part)
        meets_after = end < last - 1e-9 or (heel and pocket_part)
        before = overrun if meets_before else 0.0
        after = overrun if meets_after else 0.0
        moved = tuple(
            Point2D(
                p.x - before if abs(p.x - start) < 1e-9 else p.x + after,
                p.y,
            )
            for p in boundary
        )
        route.append((name, moved, depth))
    return route


def neck_plan_polygon(geometry: Prototype001Geometry) -> tuple[Point2D, ...]:
    """Return the whole neck's plan outline: headstock, neck, and heel."""
    neck = geometry.neck_outline.boundary
    headstock = geometry.headstock.plan.boundary
    raw = [neck[1], *headstock[2:], neck[0], *reversed(neck[2:])]
    points: list[Point2D] = []
    for point in raw:
        if points and math.hypot(point.x - points[-1].x, point.y - points[-1].y) < 1e-6:
            continue
        points.append(point)
    if math.hypot(points[0].x - points[-1].x, points[0].y - points[-1].y) < 1e-6:
        points.pop()
    return tuple(points)


def plan_neck_machining(
    geometry: Prototype001Geometry,
    parameters: NeckMachiningParameters,
    body_parameters: MachiningParameters | None = None,
) -> NeckMachiningPlan:
    """Return toolpaths for every machinable feature of the neck.

    The blank is as thick as the neck and headstock need — their deepest
    point below the glue face — or ``blank_thickness`` when that is more.
    A flat headstock needs no more than the neck (20 mm); an angled one
    needs a thicker blank, either one solid plank or the neck's own plank
    with a block glued under the headstock (``headstock_block``). The
    same programs cut both: they are planned for the full thickness, with
    Z zero on the blank's back — the block's underside on a laminated
    blank — so over the neck the first passes cut air.

    A neck-through blank runs on through the body as its centre block, as
    thick as the body: its outline is the neck and the block together, its
    back is milled only up to where the body begins (the block's back is
    the blank's), and the block's own features are cut by the body's
    programs (``body_parameters``, else the flat tool's) on the neck's
    fixture, named ``Neck_block_...``; the outline is then cut full depth.

    Raises:
        ToolpathError: If an index pin cannot be placed, or a neck-through
            headstock needs a blank thicker than the body (glue a block
            under it: ``blank="laminated"``).
    """
    flat = parameters.flat
    ball = parameters.ball
    headstock = geometry.headstock
    angle = math.radians(headstock.angle.angle_degrees)
    tangent = math.tan(angle)
    back_plane_offset = headstock.thickness / math.cos(angle)
    tip_x = -headstock.plan.reach
    headstock_lowest = headstock.face_z(tip_x) - back_plane_offset
    neck_lowest = min(
        point.z for row in geometry.neck_surface.mesh.rows for point in row
    )
    through = geometry.neck_through
    plank = _round_up(-neck_lowest)
    needed = _round_up(-min(headstock_lowest, neck_lowest))
    thickness = max(parameters.blank_thickness or 0.0, needed)
    if through is not None:
        # The block is the body's own centre: exactly as thick as it.
        plank = geometry.body.thickness
        needed = max(needed, plank)
        thickness = max(parameters.blank_thickness or 0.0, needed)

    outline = through.plan if through is not None else neck_plan_polygon(geometry)
    min_x, min_y, max_x, max_y = polygon_bounds(outline)
    radius = max(flat.tool_radius, ball.tool_radius)
    sweep = (
        Point2D(min_x - radius, min_y - radius),
        Point2D(max_x + radius, min_y - radius),
        Point2D(max_x + radius, max_y + radius),
        Point2D(min_x - radius, max_y + radius),
    )
    stock = StockBounds.around(outline, flat.stock_margin)
    block = _headstock_block(headstock, plank, needed, flat.tool_diameter)
    laminated = parameters.blank == "laminated" and block is not None
    if laminated:
        assert block is not None
        thickness = plank + block.thickness
    elif through is not None and thickness > plank + 1e-6:
        raise ToolpathError(
            f"The neck-through blank must be the body's {plank:g} mm thick, but "
            f"the headstock needs {thickness:g} mm: glue a block under it "
            "(neck_blank 'laminated') or set the headstock flatter."
        )
    pins, stock = resolve_index_pins(outline, [sweep], flat, stock)
    origin_x, origin_y = pins[0]
    top_frame = _Frame(origin_x, origin_y, mirror_y=False)
    back_frame = _Frame(origin_x, origin_y, mirror_y=True)
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])
    size = f"{stock.length:.0f} x {stock.width:.0f}"

    if laminated:
        assert block is not None
        blank_notes: tuple[str, ...] = (
            f"Laminated blank: a {size} x {plank:g} mm plank now. After "
            "Neck_back_finish, glue a "
            f"{block.length:.0f} x {block.width:.0f} x {block.thickness:g} mm "
            f"block under its headstock end, from {-block.start_x:.0f} mm "
            "behind the nut to just past the tip (the tip's dowel stays in "
            "the plank alone); then run the Headstock_ programs and "
            "Neck_back_outline.",
        )
    else:
        blank_notes = (
            f"Blank: at least {size} x {thickness:g} mm"
            + (
                f" (more than the {parameters.blank_thickness:g} mm "
                "blank_thickness: the headstock needs it)."
                if parameters.blank_thickness is not None
                and thickness > parameters.blank_thickness
                else "."
            ),
            *(
                (
                    f"Or use a {plank:g} mm plank (blank='laminated'): the "
                    "neck is cut from it first, then a "
                    f"{block.length:.0f} x {block.width:.0f} x "
                    f"{block.thickness:g} mm block is glued under the "
                    "headstock and the headstock cut in programs of its own.",
                )
                if block is not None
                else ()
            ),
        )
    index_pins = Setup(
        "Neck_index_pins",
        "Neck index pins - drill both dowel holes through the blank",
        tuple(
            drill(
                f"Index pin {index}",
                top_frame.point(Point2D(x, y)),
                flat.index_pin_diameter,
                (plank if laminated else thickness) + flat.through_overshoot,
                flat,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            "Clamp the planed blank glue-face up on a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the blank top.",
            "Both dowels sit in the waste on the centerline, beyond the "
            "headstock tip and beyond the heel.",
            *blank_notes,
        ),
        reference_points,
        flat,
    )

    # ---- top face: truss rod, headstock face, tuner marks -----------------
    shelf = headstock.nut_seat_length + headstock.nut_reach

    # The nut's flat seat runs nut_seat_length behind the nut line (a
    # locking nut's is longer), level with the glue face; the face starts
    # right behind it.
    def face_depth(model_x: float, model_y: float = 0.0) -> float:
        return headstock.top_z(model_x, model_y)

    lettering = _lettering_setup(
        geometry,
        top_frame,
        flat,
        face_depth,
        "Headstock_top" if laminated else "Neck_top",
        reference_points,
    )

    truss = geometry.truss_rod_channel
    route = _overrun_truss_route(truss, flat.tool_radius)
    truss_paths = [
        pocket(name, top_frame.polygon(boundary), depth, flat)
        for name, boundary, depth in route
    ]
    if truss.adjuster_boundary:
        truss_paths.append(
            pocket(
                "Truss-rod access trough",
                top_frame.polygon(truss.adjuster_boundary),
                truss.adjuster_depth,
                flat,
            )
        )
    face_paths: list[Toolpath] = []
    # A flat headstock not set down has the blank's own top for its face:
    # nothing to mill there.
    if not headstock.is_flat:
        face_x = (tip_x - radius, headstock.nut_reach - headstock.nut_seat_length)
        face_y = (min_y - radius, max_y + radius)
        face_grid = build_offset_grid(
            lambda xm, ym: _face_depth_at(
                face_depth, top_frame.model_point(Point2D(xm, ym))
            ),
            top_frame.x_range(face_x),
            top_frame.y_range(face_y),
            flat,
            spacing_x=parameters.grid_spacing_x,
            spacing_y=parameters.grid_spacing_y,
        )
        face_paths.append(
            raster_rough(
                "Headstock face roughing",
                face_grid,
                flat,
                x_range=top_frame.x_range(face_x),
                y_range=top_frame.y_range(face_y),
                step_over=flat.tool_diameter * parameters.roughing_step_over,
            )
        )
        face_paths.append(
            raster_finish(
                "Headstock face finishing",
                face_grid,
                flat,
                x_range=top_frame.x_range(face_x),
                y_range=top_frame.y_range(face_y),
                step_over=parameters.face_finish_step_over,
            )
        )
    for hole in geometry.tuner_layout.holes:
        surface_depth = -face_depth(hole.center.x, hole.center.y)
        face_paths.append(
            drill(
                f"Tuner {hole.side} {hole.index} centre mark",
                top_frame.point(hole.center),
                flat.tool_diameter,
                surface_depth + parameters.tuner_mark_depth,
                flat,
                start_depth=surface_depth,
            )
        )
    face_notes = (
        (
            f"The headstock face is milled to {headstock.angle.angle_degrees:g} "
            f"degrees right behind the nut's {shelf:g} mm flat seat, which "
            "stays level with the glue face; the nut is glued to the seat "
            "and to the fretboard's end."
            if tangent > 0.0
            else f"The headstock is flat (0 degrees), its face milled "
            f"{headstock.face_drop:g} mm below the glue face right behind "
            f"the nut's {shelf:g} mm flat seat, so the strings break over "
            "the nut; the nut is glued to the seat and to the fretboard."
            if headstock.face_drop > 0.0
            else "The headstock is flat (0 degrees): its face is the blank's "
            "top, level with the glue face, and is not milled."
        ),
        (
            "Tuner holes get 0.5 mm centre marks only: drill them perpendicular "
            "to the angled face on a drill press with a wedge."
            if tangent > 0.0
            else "Tuner holes get 0.5 mm centre marks only: drill them "
            "straight through on a drill press."
        ),
    )
    truss_notes = (
        f"The truss-rod step and pocket each run {flat.tool_radius:g} mm on "
        "over their neighbours, so the cutter's round corners stay out of "
        "the rod's square blocks.",
        *(
            (
                f"Drill the truss-rod adjuster's sleeve bore by hand: "
                f"{truss.bore.diameter:g} mm, "
                f"{truss.bore.end - truss.bore.start:g} mm in from the heel "
                "end along the rod's axis, "
                f"{truss.bore.axis_depth:g} mm below the glue face.",
            )
            if truss.bore is not None
            else ()
        ),
        *_adjuster_notes(geometry),
        # A board running on under the nut covers the route there itself.
        *(
            ()
            if geometry.locking_nut is not None and geometry.locking_nut.on_fretboard
            else _nut_filler_note(truss, shelf)
        ),
        *_locking_nut_notes(geometry),
    )
    if laminated:
        top = Setup(
            "Neck_top",
            "Neck glue face - truss-rod channel",
            tuple(truss_paths),
            (
                "Blank on the two index pins, glue face up, same work zero.",
                "The headstock face and the tuner marks wait for "
                "Headstock_top, after the block is glued on.",
                *truss_notes,
            ),
            reference_points,
            flat,
        )
    else:
        top = Setup(
            "Neck_top",
            "Neck glue face - truss-rod channel, headstock face, tuner centre marks",
            (*truss_paths[:1], *face_paths, *truss_paths[1:]),
            (
                "Blank on the two index pins, glue face up, same work zero.",
                *face_notes,
                *truss_notes,
            ),
            reference_points,
            flat,
        )

    # ---- back: roughing, ball finishing, outline ---------------------------
    def back_setups(
        prefix: str,
        what: str,
        blank: float,
        x_from: float,
        x_to: float,
        notes: tuple[str, ...],
    ) -> tuple[Setup, Setup]:
        """Rough and finish the back between x_from and x_to (model X).

        The surface is sampled a little past both ends so the tool never
        overlooks a neighbouring rise.
        """
        surface = _BackSurface(geometry, blank, parameters.skin, back_frame)
        margin = 3.0 * max(flat.tool_diameter, ball.tool_diameter)
        cut_x = back_frame.x_range((x_from, x_to))
        sample_x = back_frame.x_range((x_from - margin, x_to + margin))
        carve_y = back_frame.y_range((carve_low - radius, carve_high + radius))
        sampled = sample_surface(
            surface.machine_z,
            sample_x,
            carve_y,
            spacing_x=parameters.grid_spacing_x,
            spacing_y=parameters.grid_spacing_y,
        )
        rough = Setup(
            f"{prefix}_back_rough",
            f"{what} back - Z-limited roughing with the flat end mill",
            (
                raster_rough(
                    f"{what} back roughing",
                    offset_sampled_surface(sampled, flat),
                    flat,
                    x_range=cut_x,
                    y_range=carve_y,
                    step_over=flat.tool_diameter * parameters.roughing_step_over,
                ),
            ),
            (
                *notes,
                f"Roughing stops {parameters.skin:g} mm short of the glue plane "
                "everywhere, so the neck stays attached to its waste frame.",
            ),
            reference_points,
            flat,
        )
        finish = Setup(
            f"{prefix}_back_finish",
            f"{what} back - ball-nose finishing",
            (
                raster_finish(
                    f"{what} back finishing",
                    offset_sampled_surface(sampled, ball),
                    ball,
                    x_range=cut_x,
                    y_range=carve_y,
                    step_over=parameters.finishing_step_over,
                ),
            ),
            (
                f"Same fixture and X/Y zero as {prefix}_back_rough; change to "
                "the ball nose and re-touch Z on the same surface.",
                f"Scallop height about "
                f"{parameters.finishing_step_over**2 / (8.0 * ball.tool_radius):.3f}"
                " mm.",
            ),
            reference_points,
            ball,
        )
        return rough, finish

    flip = "Flip the blank about the neck centerline onto the same two index pins."
    # The back is carved across the neck and headstock: a neck-through
    # block's waste beside the neck goes with its full-depth outline cut.
    _, carve_low, _, carve_high = (
        polygon_bounds(neck_plan_polygon(geometry))
        if through is not None
        else (min_x, min_y, max_x, max_y)
    )
    # A neck-through block's back is the blank's own: the back is milled
    # only until the body begins.
    back_end = (
        through.front_x + 2.0 * radius if through is not None else max_x
    ) + radius
    headstock_setups: tuple[Setup, ...] = ()
    if laminated:
        assert block is not None
        split = block.start_x
        back_rough, back_finish = back_setups(
            "Neck",
            "Neck",
            plank,
            split,
            back_end,
            (
                flip,
                "Keep X/Y zero at index pin 1; set Z zero on the plank's back.",
                f"Only the neck back from {-split:.0f} mm behind the nut to the "
                "heel: the headstock's back needs the block, so the headstock "
                "end stays square for now.",
            ),
        )
        headstock_top = Setup(
            "Headstock_top",
            "Headstock face and tuner centre marks, with the block glued on",
            tuple(face_paths),
            (
                f"Glue the {block.length:.0f} x {block.width:.0f} x "
                f"{block.thickness:g} mm block under the headstock end, from "
                f"{-split:.0f} mm behind the nut to just past the tip, and let "
                "it cure.",
                "Glue face up again on the two index pins, the block down: "
                f"rest the neck end on a {block.thickness:g} mm spacer (an "
                "offcut of the same plank) and use dowels long enough to "
                "reach the plank.",
                "Same X/Y zero; Z zero on the glue face, as before.",
                *face_notes,
            ),
            reference_points,
            flat,
        )
        headstock_rough, headstock_finish = back_setups(
            "Headstock",
            "Headstock",
            thickness,
            min_x - radius,
            split + flat.tool_diameter,
            (
                flip + " The glue face lies flat; the block is on top.",
                "Keep X/Y zero at index pin 1; set Z zero on the block's "
                "underside, now the highest point.",
                "Only the headstock and its root: the neck's back is already "
                "cut, below the block.",
            ),
        )
        headstock_setups = (
            headstock_top,
            *((lettering,) if lettering is not None else ()),
            headstock_rough,
            headstock_finish,
        )
    else:
        back_rough, back_finish = back_setups(
            "Neck",
            "Neck",
            thickness,
            min_x - radius,
            back_end,
            (
                flip,
                "Keep X/Y zero at index pin 1; set Z zero on the (new) blank top.",
            ),
        )
    back_outline = Setup(
        "Neck_back_outline",
        (
            "Neck-through back - plan outline of the neck and body block, full "
            "depth, with tabs"
            if through is not None
            else "Neck back - plan outline through the skin, with tabs"
        ),
        (
            profile(
                "Neck outline with tabs",
                back_frame.polygon(outline),
                thickness + flat.through_overshoot,
                flat,
                # Round a neck-through block the waste is still whole.
                start_depth=(
                    0.0 if through is not None else thickness - parameters.skin - 0.5
                ),
                with_tabs=True,
            ),
        ),
        (
            "Same fixture and X/Y zero; back to the flat end mill, re-touch Z"
            + (" on the block's underside." if laminated else "."),
            (
                "Cuts the whole outline of the neck and its body block, the "
                f"waste beside the block from the top, leaving {flat.tab_count} "
                "tabs; saw and sand them off, then fair the back edges into "
                "the sides by hand. The block's glue faces stay square: glue "
                "the wings to them."
                if through is not None
                else f"Cuts the {parameters.skin:g} mm skin around the outline, "
                f"leaving {flat.tab_count} tabs; saw and sand them off, then "
                "fair the back edges into the sides by hand."
            ),
        ),
        reference_points,
        flat,
    )
    block_top: tuple[Setup, ...] = ()
    block_back: tuple[Setup, ...] = ()
    block_top_previews: tuple[tuple[Point2D, ...], ...] = ()
    block_back_previews: tuple[tuple[Point2D, ...], ...] = ()
    if through is not None:
        block_plan = plan_body_machining(
            body_part(geometry.body, through.block),
            body_parameters or flat,
            prefix="Neck_block",
            fixture=(pins, stock),
            cut_outline=False,
        )
        top_names = {
            setup.name
            for setup in (
                block_plan.top_carve,
                block_plan.top,
                block_plan.top_controls,
                block_plan.top_small_holes,
                block_plan.top_edges,
                block_plan.top_engraving,
            )
            if setup is not None
        }
        for setup, preview in zip(
            block_plan.setups, block_plan.preview_outlines, strict=True
        ):
            if setup is block_plan.index_pins or not setup.toolpaths:
                continue
            on_top = setup.name in top_names
            setup = replace(
                setup,
                notes=(
                    (
                        "The neck blank on its two index pins, glue face up, "
                        "same work zero as Neck_top."
                        if on_top
                        else "The neck blank flipped onto its two index pins, "
                        "as for Neck_back_rough."
                    ),
                    *(
                        note
                        for note in setup.notes
                        if "index pin" not in note and "Flip the blank" not in note
                    ),
                ),
            )
            if on_top:
                block_top += (setup,)
                block_top_previews += (preview,)
            else:
                block_back += (setup,)
                block_back_previews += (preview,)

    top_outline = top_frame.polygon(outline)
    back_outline_polygon = back_frame.polygon(outline)
    headstock_previews = (
        (
            top_outline,
            *((top_outline,) if lettering is not None else ()),
            back_outline_polygon,
            back_outline_polygon,
        )
        if headstock_setups
        else ()
    )
    top_engraving = None if laminated else lettering
    return NeckMachiningPlan(
        index_pins,
        top,
        back_rough,
        back_finish,
        back_outline,
        stock_length=stock.length,
        stock_width=stock.width,
        stock_thickness=thickness,
        origin_x=origin_x,
        origin_y=origin_y,
        index_pin_positions=pins,
        plank_thickness=plank,
        headstock_block=block,
        headstock_setups=headstock_setups,
        top_engraving=top_engraving,
        block_top_setups=block_top,
        block_back_setups=block_back,
        preview_outlines=(
            top_outline,
            top_outline,
            *block_top_previews,
            *((top_outline,) if top_engraving is not None else ()),
            back_outline_polygon,
            back_outline_polygon,
            *headstock_previews,
            *block_back_previews,
            back_outline_polygon,
        ),
    )


@dataclass(frozen=True, slots=True)
class _Frame:
    """Map model coordinates into one setup's machine frame and back."""

    origin_x: float
    origin_y: float
    mirror_y: bool

    def point(self, point: Point2D) -> Point2D:
        if self.mirror_y:
            return Point2D(point.x - self.origin_x, -point.y + self.origin_y)
        return Point2D(point.x - self.origin_x, point.y - self.origin_y)

    def model_point(self, point: Point2D) -> Point2D:
        if self.mirror_y:
            return Point2D(point.x + self.origin_x, self.origin_y - point.y)
        return Point2D(point.x + self.origin_x, point.y + self.origin_y)

    def polygon(self, points: Sequence[Point2D]) -> tuple[Point2D, ...]:
        return tuple(self.point(point) for point in points)

    def x_range(self, model_range: tuple[float, float]) -> tuple[float, float]:
        return (model_range[0] - self.origin_x, model_range[1] - self.origin_x)

    def y_range(self, model_range: tuple[float, float]) -> tuple[float, float]:
        low = self.point(Point2D(0.0, model_range[0])).y
        high = self.point(Point2D(0.0, model_range[1])).y
        return (min(low, high), max(low, high))


class _BackSurface:
    """The neck's back as a machine-frame height function for the flipped setup.

    Inside the neck it is the lofted back-surface mesh; over the
    headstock it is the angled back plane; wherever both exist the
    deeper wins. Outside the plan outline, and anywhere the true surface
    comes closer than ``skin`` to the glue plane, the height is clamped
    so a skin of wood remains.
    """

    def __init__(
        self,
        geometry: Prototype001Geometry,
        thickness: float,
        skin: float,
        frame: _Frame,
    ) -> None:
        self._thickness = thickness
        self._skin = skin
        self._frame = frame
        rows = geometry.neck_surface.mesh.rows
        self._stations = [row[0].x for row in rows]
        self._rows = [
            ([point.y for point in row], [point.z for point in row]) for row in rows
        ]
        headstock = geometry.headstock
        angle = math.radians(headstock.angle.angle_degrees)
        self._plane_offset = headstock.thickness / math.cos(angle)
        self._headstock = headstock
        self._headstock_back = tuple(
            Point2D(point.x, point.y) for point in headstock.bottom_boundary
        )

    def model_z(self, x: float, y: float) -> float:
        """Return the part's back height in the model frame (glue plane = 0)."""
        candidates = []
        mesh_z = interpolate_rows(self._stations, self._rows, x, y)
        if mesh_z is not None:
            candidates.append(mesh_z)
        if point_in_polygon(Point2D(x, y), self._headstock_back):
            candidates.append(self._headstock.face_z(x) - self._plane_offset)
        if not candidates:
            return -self._skin
        return min(min(candidates), -self._skin)

    def machine_z(self, xm: float, ym: float) -> float:
        """Return the back height in the flipped machine frame."""
        model = self._frame.model_point(Point2D(xm, ym))
        return -(self._thickness + self.model_z(model.x, model.y))
