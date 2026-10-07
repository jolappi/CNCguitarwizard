"""Plan the two-sided machining of a ``BodySolid``.

The body is a flat slab, so everything on it is 2.5D work with one end
mill and two setups: the top face up, then the blank flipped about the
neck centerline onto two index pins. Both setups share the same work
origin — index pin 1 — because flipping about the centerline maps the
model point ``(x, y)`` to the machine point ``(x, -y)`` and leaves the
pins where they were.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

from ..geometry.body import (
    BodySolid,
    Cavity,
    DrilledHole,
    RearCavity,
    TracedCavity,
)
from ..geometry.primitives import Point2D, point_in_polygon
from .body_edges import ball_tool, binding_path, contour_paths, roundover_path
from .engraving import engraving_path, engraving_tool
from .exceptions import ToolpathError
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .operations import depth_levels, drill, pocket, profile
from .parameters import MachiningParameters
from .planar import PolygonIndex, offset_polygon, simplified
from .surfacing import (
    offset_sampled_surface,
    raster_finish,
    raster_rough,
    sample_surface,
)
from .toolpath import PathBuilder, Toolpath


@dataclass(frozen=True, slots=True)
class BodyMachiningPlan:
    """The setups that machine one body, plus the blank they need.

    Args:
        index_pins: Program that drills the two index pins from the top.
        top: Top-face setup: pockets, holes, and the upper half of the
            outline.
        top_small_holes: Top-face program with the small drill for holes
            narrower than the main tool, or ``None`` when there are none.
        top_controls: Top-face program for top-routed electronics (a
            control plate's recess and cavity), or ``None``.
        back_controls: Back-face program for the electronics cavities
            and their cover recesses, or ``None``.
        top_edges: Top-face ball-nose program for an arm contour and a
            top roundover, or ``None``.
        back_edges: Back-face ball-nose program for a belly cut and a
            back roundover, or ``None``.
        top_engraving: Top-face V-bit program for the decorative
            engraving, or ``None``.
        top_relief: Top-face flat end mill program clearing a relief
            engraving's shapes (camo) to their levels, or ``None``.
        top_carve: Top-face program arching a carved top (roughed with
            the main tool, finished with a ball nose), run first, or
            ``None``.
        top_steps: Top-face program lowering a stepped top's bands, run
            first, or ``None``.
        back: Back-face setup after the flip: rear cavities, cover
            recesses, rear holes, and the lower half of the outline with
            tabs.
        stock_length: Minimum blank length along X.
        stock_width: Minimum blank width along Y.
        stock_thickness: Blank thickness (the body thickness).
        origin_x: Model X of the work origin (index pin 1).
        origin_y: Model Y of the work origin.
        index_pin_positions: Both dowel centres in the model frame.
    """

    index_pins: Setup
    top: Setup
    back: Setup
    top_small_holes: Setup | None
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float
    origin_y: float
    index_pin_positions: tuple[tuple[float, float], ...]
    preview_outlines: tuple[tuple[Point2D, ...], ...] = ()
    back_small_holes: Setup | None = None
    top_controls: Setup | None = None
    back_controls: Setup | None = None
    top_edges: Setup | None = None
    back_edges: Setup | None = None
    top_engraving: Setup | None = None
    top_relief: Setup | None = None
    top_carve: Setup | None = None
    top_steps: Setup | None = None

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the setups in running order.

        Each face runs its main program, then its electronics program,
        then its small-drill program.
        """
        candidates = (
            self.index_pins,
            self.top_carve,
            self.top_steps,
            self.top,
            self.top_controls,
            self.top_small_holes,
            self.top_edges,
            self.top_engraving,
            self.top_relief,
            self.back,
            self.back_controls,
            self.back_small_holes,
            self.back_edges,
        )
        return tuple(setup for setup in candidates if setup is not None)


def plan_body_machining(
    body: BodySolid,
    parameters: MachiningParameters,
    *,
    prefix: str = "Body",
    fixture: tuple[tuple[tuple[float, float], ...], StockBounds] | None = None,
    cut_outline: bool = True,
    pin_axis_y: float = 0.0,
) -> BodyMachiningPlan:
    """Return toolpaths for every machinable feature of the body.

    For one part of a neck-through body (``body_part``): ``prefix`` names
    its programs (``Wing_bass_top`` ...); ``fixture`` gives the pins and
    blank it shares with other programs (the neck blank's, for its centre
    block), whose own outline cut then stays out (``cut_outline``); a
    wing's own dowels go on ``Y = pin_axis_y``, its blank's middle.

    Raises:
        ToolpathError: If an index pin would end up in the finished body,
            too close to a cut or the blank's edge, or a feature cannot
            be cut with the tool.
    """
    if fixture is not None:
        pins, stock = fixture
    else:
        stock = StockBounds.around(body.outline.points, parameters.stock_margin)
        pins, stock = resolve_index_pins(
            body.outline.points,
            [cavity.outline for cavity in _top_cavities(body)]
            + (
                # A carved top's rim is cut on past the edge: the dowels keep
                # clear of that band too.
                [
                    offset_polygon(
                        body.outline.points, body.carved_top.band, inward=False
                    )
                ]
                if body.carved_top is not None
                else []
            ),
            parameters,
            stock,
            pin_axis_y,
        )
    origin_x, origin_y = pins[0]
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])

    top_frame = _Frame(origin_x, origin_y, mirror_y=False)
    back_frame = _Frame(origin_x, origin_y, mirror_y=True)
    half_depth = body.thickness / 2.0 + parameters.profile_overlap

    pin_setup = Setup(
        "Body_index_pins",
        f"Body index pins - drill both {parameters.pin_diameter:g} mm dowel holes "
        "through the blank",
        tuple(
            drill(
                f"Index pin {index}",
                top_frame.point(Point2D(x, y)),
                parameters.pin_diameter,
                body.thickness + parameters.through_overshoot,
                parameters,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            "Clamp the blank top face up on a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the stock top.",
            (
                "Both dowels sit in the waste on the centerline - pin 1 in the "
                "horn gap ahead of the neck pocket, pin 2 in the tail notch - "
                "so they never end up in the finished body."
                if pin_axis_y == 0.0
                else "Both dowels sit in the waste ahead of and behind the part, "
                "on a line along its middle, so they never end up in it."
            ),
            f"Blank: at least {stock.length:.0f} x {stock.width:.0f} x "
            f"{body.thickness:g} mm; pin 1 is "
            f"{pins[0][0] - stock.min_x:.1f} mm from the nut-end edge "
            "on the centerline.",
            "Insert both dowels after this program before running Body_top.",
        ),
        reference_points,
    )

    def top_pocket(cavity: Cavity) -> Toolpath:
        return _top_pocket(cavity, body, top_frame, parameters)

    top_paths: list[Toolpath] = []
    for cavity in _top_cavities(body):
        if cavity in body.control_top_cavities:
            continue
        top_paths.append(top_pocket(cavity))
        # A tilted floor (an angled neck pocket) steps down after it.
        top_paths += _floor_terraces(cavity, top_frame, parameters)
    small_holes = [
        hole for hole in body.holes if hole.diameter < parameters.tool_diameter - 1e-6
    ] + [
        hole
        for hole in body.control_top_marks
        if hole.diameter < parameters.tool_diameter - 1e-6
    ]
    top_controls: Setup | None = None
    if body.control_top_cavities:
        top_controls = Setup(
            "Body_top_controls",
            "Body top face - control plate recess and cavity",
            tuple(top_pocket(cavity) for cavity in body.control_top_cavities),
            (
                "Same fixture, tool and X/Y zero as Body_top.",
                "The plate's screw spots are in Body_top_small_holes.",
            ),
            reference_points,
        )
    for hole in body.holes:
        if hole in small_holes:
            continue
        top_paths.append(_drill_hole(hole, body, top_frame, parameters))
    mounting = body.bridge_mounting
    for side, pivot in zip(("bass", "treble"), mounting.pivot_holes, strict=False):
        top_paths.append(
            drill(
                f"Pivot stud {side}",
                top_frame.point(pivot),
                mounting.pivot_hole_diameter,
                mounting.pivot_hole_depth,
                parameters,
            )
        )
    if cut_outline:
        top_paths.append(
            profile(
                "Outline, upper half",
                top_frame.polygon(body.outline.points),
                half_depth,
                parameters,
            )
        )
    if body.top_edge.has_binding:
        top_paths.append(
            binding_path(
                "Top binding channel",
                top_frame.polygon(body.edge_points),
                body.top_edge,
                parameters,
                # On a carved top's rim, the carve's height down.
                face_drop=body.top_edge_drop,
            )
        )
    top = Setup(
        "Body_top",
        "Body top face - pockets, holes, upper half of the outline",
        tuple(top_paths),
        (
            "Blank on the two index pins, top face up, same work zero as "
            "Body_index_pins.",
            "The outline is cut to half depth plus overlap; the blank stays in "
            "one piece.",
            "The jack bore enters from the edge and is not part of this program.",
            *(f"Bridge: {note}" for note in body.bridge_notes),
            *(
                (
                    "Drill the wire holes by hand once every cavity is cut, "
                    "with a long bit:",
                    *(hole.note() for hole in body.wire_holes),
                )
                if body.wire_holes
                else ()
            ),
            *body.wire_notes,
        ),
        reference_points,
    )

    top_small_holes: Setup | None = None
    if small_holes:
        small_tool = replace(
            parameters,
            tool_diameter=parameters.small_hole_tool_diameter,
            plunge_rate=min(parameters.plunge_rate, 150.0),
        )
        top_small_holes = Setup(
            "Body_top_small_holes",
            f"Body top face - holes for the {small_tool.tool_diameter:g} mm drill",
            tuple(
                _drill_hole(hole, body, top_frame, small_tool) for hole in small_holes
            ),
            (
                "Same fixture and X/Y zero as Body_top; change to the small drill "
                "and re-touch Z on the stock top.",
            ),
            reference_points,
            small_tool,
        )

    def rear_pockets(rear: RearCavity) -> list[Toolpath]:
        return _rear_pockets(rear, back_frame, parameters)

    electronics = [
        rear
        for rear in (body.control_cavity, body.switch_cavity, body.battery_cavity)
        if rear is not None
    ]
    back_paths: list[Toolpath] = []
    for rear in body.extra_rear_cavities:
        back_paths += rear_pockets(rear)
    back_small = [
        hole
        for hole in (*body.rear_holes, *body.control_back_marks)
        if hole.diameter < parameters.tool_diameter - 1e-6
    ]
    back_controls: Setup | None = None
    if electronics:
        back_controls = Setup(
            "Body_back_controls",
            "Body back face - electronics cavities and their cover recesses",
            tuple(path for rear in electronics for path in rear_pockets(rear)),
            (
                "Same fixture, tool and X/Y zero as Body_back (still held by the "
                "outline's tabs).",
                "The cover-screw spots are in Body_back_small_holes; drill the "
                "screw pilots by hand to suit the screws.",
                *(
                    (
                        "Drill the battery lead's channel from the battery box "
                        "to the control cavity by hand.",
                    )
                    # Unless the wiring planned it (Body_top's notes).
                    if body.battery_cavity is not None
                    and not any(
                        "battery" in hole.name.lower() for hole in body.wire_holes
                    )
                    and not any("battery" in note for note in body.wire_notes)
                    else ()
                ),
            ),
            reference_points,
        )
    for hole in body.rear_holes:
        if hole not in back_small:
            back_paths.append(_drill_rear_hole(hole, body, back_frame, parameters))
    if cut_outline:
        back_paths.append(
            profile(
                "Outline, lower half with tabs",
                back_frame.polygon(body.outline.points),
                half_depth,
                parameters,
                with_tabs=True,
            )
        )
    if body.back_edge.has_binding:
        back_paths.append(
            binding_path(
                "Back binding channel",
                back_frame.polygon(body.edge_points),
                body.back_edge,
                parameters,
            )
        )
    back = Setup(
        "Body_back",
        "Body back face - bridge cavities, rear holes, lower half of the outline",
        tuple(back_paths),
        (
            "Flip the blank about the neck centerline onto the same two index pins.",
            "Keep X/Y zero at index pin 1; set Z zero on the (new) stock top.",
            f"The outline finishes with {parameters.tab_count} holding tabs "
            f"{parameters.tab_height:.1f} mm high; saw and sand them off.",
            "The dowels stay in the waste frame, which the tabs keep attached "
            "to the body until the end.",
        ),
        reference_points,
    )

    back_small_holes: Setup | None = None
    if back_small:
        small_tool = replace(
            parameters,
            tool_diameter=parameters.small_hole_tool_diameter,
            plunge_rate=min(parameters.plunge_rate, 150.0),
        )
        back_small_holes = Setup(
            "Body_back_small_holes",
            f"Body back face - holes for the {small_tool.tool_diameter:g} mm drill",
            tuple(
                _drill_rear_hole(hole, body, back_frame, small_tool)
                for hole in back_small
            ),
            (
                "Same fixture and X/Y zero as Body_back; change to the small drill "
                "and re-touch Z on the stock top (the back face).",
            ),
            reference_points,
            small_tool,
        )

    # The top's edge work stays within the upper outline's slot; the
    # back's stays above the holding tabs.
    top_edges = _edge_setup(
        body, "top", top_frame, parameters, reference_points, half_depth
    )
    back_edges = _edge_setup(
        body,
        "back",
        back_frame,
        parameters,
        reference_points,
        half_depth - parameters.tab_height - 0.5,
    )

    top_engraving = _engraving_setup(body, top_frame, parameters, reference_points)
    top_relief = _relief_setup(body, top_frame, parameters, reference_points)
    top_carve = _carve_setup(body, top_frame, parameters, reference_points)
    top_steps = _steps_setup(body, top_frame, parameters, reference_points)

    top_outline = top_frame.polygon(body.outline.points)
    back_outline = back_frame.polygon(body.outline.points)
    previews = [top_outline, top_outline]
    for optional in (top_carve, top_steps):
        if optional is not None:
            previews.append(top_outline)
    for optional in (
        top_controls,
        top_small_holes,
        top_edges,
        top_engraving,
        top_relief,
    ):
        if optional is not None:
            previews.append(top_outline)
    previews.append(back_outline)
    for optional in (back_controls, back_small_holes, back_edges):
        if optional is not None:
            previews.append(back_outline)
    plan = BodyMachiningPlan(
        pin_setup,
        top,
        back,
        top_small_holes,
        stock_length=stock.length,
        stock_width=stock.width,
        stock_thickness=body.thickness,
        origin_x=origin_x,
        origin_y=origin_y,
        index_pin_positions=tuple((x, y) for x, y in pins),
        preview_outlines=tuple(previews),
        back_small_holes=back_small_holes,
        top_controls=top_controls,
        back_controls=back_controls,
        top_edges=top_edges,
        back_edges=back_edges,
        top_engraving=top_engraving,
        top_relief=top_relief,
        top_carve=top_carve,
        top_steps=top_steps,
    )
    return plan if prefix == "Body" else _renamed(plan, prefix)


def _renamed(plan: BodyMachiningPlan, prefix: str) -> BodyMachiningPlan:
    """Return ``plan`` with its programs named for one part (``prefix``).

    ``Body_top`` becomes ``Wing_bass_top``, its description and notes
    follow, and a flip turns about the dowels' own line.
    """
    label = prefix.replace("_", " ")

    def text(value: str) -> str:
        return (
            value.replace("Body_", f"{prefix}_")
            .replace("Body ", f"{label} ")
            .replace(
                "Flip the blank about the neck centerline",
                "Flip the blank about the line through the dowels",
            )
        )

    def renamed(setup: Setup | None) -> Setup | None:
        if setup is None:
            return None
        return replace(
            setup,
            name=text(setup.name),
            description=text(setup.description),
            notes=tuple(text(note) for note in setup.notes),
        )

    changes: dict[str, Any] = {
        name: renamed(getattr(plan, name))
        for name in (
            "index_pins",
            "top",
            "back",
            "top_small_holes",
            "back_small_holes",
            "top_controls",
            "back_controls",
            "top_edges",
            "back_edges",
            "top_engraving",
            "top_relief",
            "top_carve",
            "top_steps",
        )
    }
    return replace(plan, **changes)


CARVE_FINISH_STEP = 1.0
"""Step-over of the ball nose's finishing passes over a carved top, in mm."""

STEP_WALL_TOLERANCE = 0.02
"""How far a stepped top's wall pass may stray from the step's boundary
(simplified that much first, which makes it far quicker), in mm."""

STEP_REACH = 300.0
"""How far in from the edge a stepped top's clearing passes may go, in mm."""

STEP_CLEARING_TOLERANCE = 0.25
"""How far a stepped top's clearing passes (all but each wall's) may stray
from the outline's own offset, in mm: they leave the wall to the last."""

STEP_LINK = 1.5
"""How many step-overs a stepped top's pass may feed across to the next
pass at depth; further, the tool lifts and comes down again."""


def _steps_setup(
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
    reference_points: tuple[tuple[float, float], ...],
) -> Setup | None:
    """Return the program lowering a stepped top's bands, or ``None``.

    The innermost step's band (everything outside its boundary) goes one
    step down first, then each next band a step deeper, in step-down
    layers. A band is cleared in passes along the body's edge — the
    outline taken in by the tool's radius, then a step-over further in
    each pass, each kept only where the tool stays outside the step's
    boundary — until a pass lies wholly inside it; then the boundary taken
    out by the radius runs round as the step's wall, cut true. Each pass
    starts nearest where the last ended and is fed across when that is
    near.

    Raises:
        ToolpathError: For a band too narrow for the tool anywhere.
    """
    steps = body.stepped_top
    if steps is None:
        return None
    radius = parameters.tool_radius
    spacing = parameters.raster_spacing
    # The clearing passes come from a coarser outline, sampled coarser;
    # the walls from the boundaries themselves.
    rough = simplified(body.outline.points, STEP_CLEARING_TOLERANCE)
    inside_body = PolygonIndex.of(
        offset_polygon(rough, radius, inward=True, sample_spacing=3.0, arc_spacing=2.0)
    )
    paths: list[Toolpath] = []
    start = 0.0
    for index, (boundary, depth) in reversed(list(enumerate(steps.bands()))):
        wall = offset_polygon(
            simplified(boundary, STEP_WALL_TOLERANCE), radius, inward=False
        )
        keep_out = PolygonIndex.of(wall)
        runs: list[list[Point2D]] = []
        distance = radius
        while distance < STEP_REACH:
            loop = offset_polygon(
                rough, distance, inward=True, sample_spacing=3.0, arc_spacing=2.0
            )
            outside = _runs_where(loop, lambda point: not keep_out.holds(point))
            if not outside:
                break
            runs += outside
            distance += spacing
        # The wall, where it lies in the body.
        runs += _runs_where(wall, inside_body.holds)
        if not runs:
            raise ToolpathError(
                f"The stepped top's step {index + 1} leaves no band the "
                f"{parameters.tool_diameter:g} mm tool can cut."
            )
        builder = _steps_builder(f"Stepped top, {depth:g} mm band", parameters)
        for z in depth_levels(start, depth, parameters.step_down):
            for run in runs:
                _cut_step_pass(builder, frame.polygon(run), z, spacing * STEP_LINK)
        paths.append(builder.build())
        start = depth
    return Setup(
        "Body_top_steps",
        f"Body top face - stepped top, {len(steps.boundaries)} steps of "
        f"{steps.step:g} mm",
        tuple(paths),
        (
            "Same fixture, tool and X/Y zero as Body_index_pins, dowels in; run "
            "it before Body_top.",
            "Each band is cut along the edge, its last pass following the "
            "step's wall; the next step's band goes deeper after it.",
        ),
        reference_points,
    )


def _runs_where(
    loop: Sequence[Point2D], keep: Callable[[Point2D], bool]
) -> list[list[Point2D]]:
    """Return the runs of a closed ``loop`` that ``keep`` accepts.

    A loop kept all round comes back closed; a run that wraps past the
    loop's first point is joined up.
    """
    if not loop:
        return []
    kept = [keep(point) for point in loop]
    if all(kept):
        return [[*loop, loop[0]]]
    # Start just after a point left out, so no run wraps.
    first = kept.index(False)
    order = [*range(first + 1, len(loop)), *range(first + 1)]
    runs: list[list[Point2D]] = []
    run: list[Point2D] = []
    for index in order:
        if kept[index]:
            run.append(loop[index])
            continue
        if len(run) >= 2:
            runs.append(run)
        run = []
    if len(run) >= 2:
        runs.append(run)
    return runs


def _steps_builder(name: str, parameters: MachiningParameters) -> PathBuilder:
    return PathBuilder(
        name,
        safe_height=parameters.safe_height,
        feed_rate=parameters.feed_rate,
        plunge_rate=parameters.plunge_rate,
    )


def _cut_step_pass(
    builder: PathBuilder, run: Sequence[Point2D], z: float, link: float
) -> None:
    """Run one pass at ``z``, from its end nearest the tool.

    A closed pass (its ends together) starts from its point nearest the
    tool. A pass no further than ``link`` from where the last one ended is
    fed straight across at depth; otherwise the tool lifts and plunges.
    """
    points = list(run)
    if builder.positioned:

        def away(point: Point2D) -> float:
            return math.hypot(point.x - builder.x, point.y - builder.y)

        if math.hypot(points[0].x - points[-1].x, points[0].y - points[-1].y) < 1e-6:
            first = min(range(len(points) - 1), key=lambda i: away(points[i]))
            ring = points[:-1]
            points = [*ring[first:], *ring[:first], ring[first]]
        elif away(points[-1]) < away(points[0]):
            points.reverse()
    near = (
        builder.positioned
        and builder.z <= z + 1e-9
        and math.hypot(points[0].x - builder.x, points[0].y - builder.y) <= link
    )
    if near:
        builder.cut_to(points[0].x, points[0].y)
    else:
        builder.rapid_to(points[0].x, points[0].y)
        builder.rapid_down_to(0.0)
    if builder.z > z:
        builder.plunge_to(z)
    for point in points[1:]:
        builder.cut_to(point.x, point.y)


CARVE_EDGE_REACH = 3.0
"""How far past its tool's radius a carve's rim level is cut beyond the
body's edge (room for the cutter to finish the rim right to the edge;
the waste further out is left), in mm."""


def _carve_setup(
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
    reference_points: tuple[tuple[float, float], ...],
) -> Setup | None:
    """Return the program that arches a carved top, or ``None``.

    A flat end mill (``carve_tool_diameter``, else the main tool) roughs
    the arch in step-down layers, its runs taken nearest first and linked
    in the cut, the last layer following the arch: the steps it leaves
    are sanded smooth by hand. With ``carve_finish`` a ball nose as wide
    finishes it in passes ``CARVE_FINISH_STEP`` apart. The rim's level is
    cut on past the edge only as far as the tool needs to finish it.
    """
    carve = body.carved_top
    if carve is None:
        return None
    tool = (
        replace(parameters, tool_diameter=parameters.carve_tool_diameter)
        if parameters.carve_tool_diameter > 0.0
        else parameters
    )
    reach = min(carve.band, tool.tool_radius + CARVE_EDGE_REACH)
    points = body.outline.points
    low = frame.point(
        Point2D(min(p.x for p in points) - reach, min(p.y for p in points) - reach)
    )
    high = frame.point(
        Point2D(max(p.x for p in points) + reach, max(p.y for p in points) + reach)
    )
    x_range = (min(low.x, high.x), max(low.x, high.x))
    y_range = (min(low.y, high.y), max(low.y, high.y))

    def surface(x: float, y: float) -> float:
        model = frame.model(Point2D(x, y))
        if carve.outside_at(model.x, model.y) > reach:
            return 0.0
        return -carve.drop_at(model.x, model.y)

    sampled = sample_surface(
        surface,
        x_range,
        y_range,
        spacing_x=2.0,
        spacing_y=1.0,
        edge_samples_x=1,
        edge_samples_y=1,
    )
    rough = raster_rough(
        "Carved top roughing",
        offset_sampled_surface(sampled, tool),
        tool,
        x_range=x_range,
        y_range=y_range,
        step_over=tool.raster_spacing,
        sample_spacing=2.0,
        link_distance=4.0 * tool.raster_spacing,
    )
    notes = [
        "Same fixture and X/Y zero as Body_index_pins, dowels in; run it "
        "before Body_top.",
        f"Rough with a {tool.tool_diameter:g} mm flat end mill"
        + (
            ""
            if tool is parameters
            else " (not the main tool: touch Z on the stock top after the change)"
        )
        + ".",
        "The rim's level is cut a little past the body's edge, into the "
        "waste the outline takes later.",
    ]
    if not parameters.carve_finish:
        notes.append(
            "The last layer follows the arch in rows "
            f"{tool.raster_spacing:g} mm apart: sand their steps smooth by hand."
        )
        return Setup(
            "Body_top_carve",
            f"Body top face - carved top, {carve.height:g} mm arch to a "
            f"{carve.rim:g} mm rim, roughed to sand",
            (rough,),
            tuple(notes),
            reference_points,
            tool,
        )
    ball = ball_tool(tool)
    finish = raster_finish(
        "Carved top finishing",
        offset_sampled_surface(sampled, ball),
        ball,
        x_range=x_range,
        y_range=y_range,
        step_over=CARVE_FINISH_STEP,
        sample_spacing=1.0,
    )
    notes.append(
        f"Change to a {ball.tool_diameter:g} mm ball nose for the finishing "
        "passes and re-touch Z on the stock top (the plateau); sand the "
        "passes' scallops smooth."
    )
    return Setup(
        "Body_top_carve",
        f"Body top face - carved top, {carve.height:g} mm arch to a "
        f"{carve.rim:g} mm rim",
        (rough, finish),
        tuple(notes),
        reference_points,
        ball,
    )


def _engraving_setup(
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
    reference_points: tuple[tuple[float, float], ...],
) -> Setup | None:
    """Return the V-bit program for the top's engraving, or ``None``."""
    if body.engraving is None or not body.engraving.lines:
        return None
    depth = body.engraving.depth
    tool = engraving_tool(parameters, depth)
    lowered = body.carved_top is not None or body.stepped_top is not None
    return Setup(
        "Body_top_engraving",
        f"Body top face - decorative engraving {depth:g} mm deep with a V-bit",
        (
            engraving_path(
                body.engraving,
                frame.point,
                tool,
                # Following a carved top's arch or a stepped top's levels.
                (lambda point: -body.top_drop_at(point.x, point.y))
                if lowered
                else (lambda point: 0.0),
            ),
        ),
        (
            "Same fixture and X/Y zero as Body_top; change to a "
            f"{parameters.engraving_tool_angle:g} degree V-bit and re-touch Z "
            "on the stock top.",
            f"The grooves come out {tool.tool_diameter:.2f} mm wide at the face.",
            "Run it before any roundover, while the top is still flat.",
        ),
        reference_points,
        tool,
    )


def _relief_setup(
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
    reference_points: tuple[tuple[float, float], ...],
) -> Setup | None:
    """Return the flat end mill's program for a relief engraving, or ``None``.

    Each shape is cleared flat to its level below the face over it (a
    stepped top's band lowers both); one inside another is cut on from
    that one's floor.
    """
    if body.engraving is None or not body.engraving.pockets:
        return None
    tool = replace(
        parameters,
        tool_diameter=parameters.relief_tool_diameter,
        step_down=min(parameters.step_down, parameters.engraving_step_down),
        plunge_rate=min(parameters.plunge_rate, 150.0),
    )
    shapes = body.engraving.pockets
    paths = tuple(
        pocket(
            f"Relief shape {index} ({shape.depth:g} mm)",
            frame.polygon(shape.outline),
            shape.face_drop + shape.depth,
            tool,
            start_depth=shape.face_drop
            + (shapes[shape.within].depth if shape.within is not None else 0.0),
        )
        for index, shape in enumerate(shapes, start=1)
    )
    levels = ", ".join(f"{depth:g}" for depth in sorted({s.depth for s in shapes}))
    return Setup(
        "Body_top_relief",
        f"Body top face - relief, {len(shapes)} shapes cleared {levels} mm deep "
        f"with a {tool.tool_diameter:g} mm flat end mill",
        paths,
        (
            "Same fixture and X/Y zero as Body_top; change to a "
            f"{tool.tool_diameter:g} mm flat end mill and re-touch Z on the stock "
            "top.",
            "Each shape is cleared flat to its own level below the face; a "
            "shape inside another is cut on from that one's floor.",
            "Run it before any roundover, while the top is still flat.",
        ),
        reference_points,
        tool,
    )


def _edge_setup(
    body: BodySolid,
    face: Literal["top", "back"],
    frame: _Frame,
    parameters: MachiningParameters,
    reference_points: tuple[tuple[float, float], ...],
    floor: float,
) -> Setup | None:
    """Return the ball-nose program for one face's contour and roundover.

    Nothing goes deeper than ``floor``.
    """
    contours = [contour for contour in body.contours if contour.face == face]
    edge = body.top_edge if face == "top" else body.back_edge
    if not contours and edge.radius <= 0.0:
        return None
    ball = ball_tool(parameters)
    paths: list[Toolpath] = []
    for contour in contours:
        paths += contour_paths(contour, frame.model, ball, floor)
    if edge.radius > 0.0:
        paths.append(
            roundover_path(
                f"{face.capitalize()} edge roundover",
                frame.polygon(body.edge_points),
                edge.radius,
                ball,
                lambda point: (
                    max(
                        (contour.depth_at(frame.model(point)) for contour in contours),
                        default=0.0,
                    )
                    # A carved top's edge is its rim, the carve's height
                    # down; a stepped top's its outermost band.
                    + (
                        body.top_drop_at(frame.model(point).x, frame.model(point).y)
                        if face == "top"
                        else 0.0
                    )
                ),
                floor,
            )
        )
    other = "Body_top" if face == "top" else "Body_back"
    what = " and ".join(
        [contour.name.lower() for contour in contours]
        + ([f"{edge.radius:g} mm roundover"] if edge.radius > 0.0 else [])
    )
    return Setup(
        f"Body_{face}_edges",
        f"Body {face} face - {what} with a ball nose",
        tuple(paths),
        (
            f"Same fixture and X/Y zero as {other}; change to a "
            f"{ball.tool_diameter:g} mm ball nose and re-touch Z on the stock top.",
            "Run it after the outline so the roundover has the outline's slot "
            "to work in.",
        ),
        reference_points,
        ball,
    )


@dataclass(frozen=True, slots=True)
class _Frame:
    """Map model coordinates into one setup's machine frame."""

    origin_x: float
    origin_y: float
    mirror_y: bool

    def point(self, point: Point2D) -> Point2D:
        """Return the machine position of a model point.

        The flip is about the model centerline (Y = 0), so a flipped
        setup sees every Y negated — the work origin's own Y included.
        """
        if self.mirror_y:
            return Point2D(point.x - self.origin_x, -point.y + self.origin_y)
        return Point2D(point.x - self.origin_x, point.y - self.origin_y)

    def polygon(self, points: Sequence[Point2D]) -> tuple[Point2D, ...]:
        return tuple(self.point(point) for point in points)

    def model(self, point: Point2D) -> Point2D:
        """Return the model position of a machine point (``point``'s inverse)."""
        if self.mirror_y:
            return Point2D(point.x + self.origin_x, self.origin_y - point.y)
        return Point2D(point.x + self.origin_x, point.y + self.origin_y)


def _top_pocket(
    cavity: Cavity,
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
) -> Toolpath:
    """Pocket one top cavity; a through route runs on past the back."""
    depth = cavity.depth
    if cavity in body.through_cavities and depth >= body.thickness:
        depth = body.thickness + parameters.through_overshoot
    # A stepped floor (or a through route inside a recess) starts where
    # the enclosing pocket, cut earlier, already ended.
    return pocket(
        cavity.name,
        frame.polygon(cavity.outline),
        depth,
        parameters,
        start_depth=body.step_start_depth(cavity),
    )


FLOOR_TERRACE_STEP = 0.1
"""Height of each terrace a tilted pocket floor is cut in, in mm."""


def _floor_terraces(
    cavity: Cavity, frame: _Frame, parameters: MachiningParameters
) -> list[Toolpath]:
    """Step a tilted floor down toward its deep end in thin terraces.

    Each terrace reaches as far as the floor is at least that deep, so
    the steps stand at most ``FLOOR_TERRACE_STEP`` proud of the slope and
    the neck rests on their edges. A terrace too short for the tool (at
    the very mouth) is left out.
    """
    if not isinstance(cavity, TracedCavity) or cavity.floor_slope <= 0.0:
        return []
    slope = cavity.floor_slope
    top, bottom = cavity.depth, cavity.deepest
    count = math.floor((bottom - top) / FLOOR_TERRACE_STEP + 1e-9)
    paths: list[Toolpath] = []
    previous = top
    for index in range(1, count + 1):
        depth = top + index * FLOOR_TERRACE_STEP
        reach = cavity.max_x - (depth - top) / slope
        region = _clip_behind(cavity.outline, reach)
        if not region or reach - cavity.min_x < parameters.tool_diameter:
            break
        paths.append(
            pocket(
                f"{cavity.name} floor, step {index}",
                frame.polygon(region),
                depth,
                parameters,
                start_depth=previous,
            )
        )
        previous = depth
    return paths


def _clip_behind(polygon: tuple[Point2D, ...], limit: float) -> tuple[Point2D, ...]:
    """Return the part of ``polygon`` with x at most ``limit``."""
    clipped: list[Point2D] = []
    count = len(polygon)
    for index in range(count):
        current, following = polygon[index], polygon[(index + 1) % count]
        inside = current.x <= limit
        if inside:
            clipped.append(current)
        if inside != (following.x <= limit):
            fraction = (limit - current.x) / (following.x - current.x)
            clipped.append(
                Point2D(limit, current.y + (following.y - current.y) * fraction)
            )
    return tuple(clipped) if len(clipped) >= 3 else ()


def _rear_pockets(
    rear: RearCavity,
    frame: _Frame,
    parameters: MachiningParameters,
) -> list[Toolpath]:
    """Pocket one rear cavity: its cover recess, the cavity, its steps."""
    paths = [
        pocket(
            rear.cover_recess.name,
            frame.polygon(rear.cover_recess.outline),
            rear.cover_recess.depth,
            parameters,
        ),
        pocket(
            rear.cavity.name,
            frame.polygon(rear.cavity.outline),
            rear.cavity.depth,
            parameters,
            start_depth=rear.cover_recess.depth,
        ),
    ]
    paths += [
        pocket(
            step.name,
            frame.polygon(step.outline),
            step.depth,
            parameters,
            start_depth=rear.cavity.depth,
        )
        for step in rear.steps
    ]
    return paths


def _top_cavities(body: BodySolid) -> tuple[Cavity, ...]:
    """Return the top-face cavities in cutting order (through routes last)."""
    return body.top_cavities


def _drill_rear_hole(
    hole: DrilledHole,
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
) -> Toolpath:
    """Drill one hole from the back, starting below any wider rear hole.

    A hole inside a wider, shallower rear hole at the same spot (a bolt
    hole under its ferrule counterbore) starts at that hole's floor; a
    hole that reaches a top cavity (the neck pocket) runs on by the
    through overshoot so it breaks cleanly into it.
    """
    start_depth = 0.0
    # Inside a rear cavity or its cover recess the wood starts at that
    # floor (a cover screw's spot sits on the recess floor).
    for rear in body.rear_cavities:
        for floor in (rear.cover_recess, *rear.pockets):
            if floor.depth < hole.depth and point_in_polygon(
                hole.center, floor.outline
            ):
                start_depth = max(start_depth, floor.depth)
    for other in body.rear_holes:
        if (
            other is not hole
            and other.diameter > hole.diameter
            and other.depth < hole.depth
            and math.hypot(
                other.center_x - hole.center_x, other.center_y - hole.center_y
            )
            <= (other.diameter - hole.diameter) / 2.0
        ):
            start_depth = max(start_depth, other.depth)
    depth = hole.depth
    for cavity in _top_cavities(body):
        if (
            point_in_polygon(hole.center, cavity.outline)
            and depth + cavity.depth >= body.thickness - 1e-6
        ):
            depth = body.thickness - cavity.depth + parameters.through_overshoot
    return drill(
        hole.name,
        frame.point(hole.center),
        hole.diameter,
        depth,
        parameters,
        start_depth=start_depth,
    )


def _drill_hole(
    hole: DrilledHole,
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
) -> Toolpath:
    """Drill one hole from the top, skipping air and stopping at rear cavities.

    A hole whose centre lies in a top cavity starts at that cavity's
    floor. A hole whose centre lies over a rear cavity only needs to
    break through the top wall into it, however deep the model's
    through hole is.
    """
    start_depth = 0.0
    for cavity in _top_cavities(body):
        if point_in_polygon(hole.center, cavity.outline) and cavity.depth < hole.depth:
            start_depth = max(start_depth, cavity.depth)
    depth = hole.depth
    for rear in body.rear_cavities:
        rear_depth = rear.depth_at(hole.center)
        if rear_depth is not None:
            depth = min(
                depth, body.thickness - rear_depth + parameters.through_overshoot
            )
    if depth >= body.thickness:
        depth = body.thickness + parameters.through_overshoot
    return drill(
        hole.name,
        frame.point(hole.center),
        hole.diameter,
        depth,
        parameters,
        start_depth=start_depth,
    )
