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
    CarvedTop,
    Cavity,
    DrilledHole,
    RearCavity,
    ScoopedGrooves,
    TracedCavity,
)
from ..geometry.primitives import Point2D, point_in_polygon
from .body_edges import (
    ball_tool,
    binding_path,
    contour_paths,
    roundover_path,
    scoop_paths,
)
from .engraving import engraving_path, engraving_tool
from .exceptions import ToolpathError
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .operations import depth_levels, drill, pocket, profile
from .parameters import MachiningParameters
from .planar import PolygonIndex, offset_polygon, simplified
from .surfacing import (
    OffsetGrid,
    SampledSurface,
    offset_sampled_surface,
    raster_finish,
    raster_rough,
    sample_surface,
)
from .toolpath import PathBuilder, Toolpath

TOP_FIXTURE = "Body top face up on the index pins"
"""How the top face's programs hold the blank (``Setup.fixture``)."""

BACK_FIXTURE = "Body back face up on the index pins"
"""How the back face's programs hold the blank, once it is flipped."""

CORE_FIXTURE = "Body core top face up on the index pins"
"""How the core's own program holds the core, before its top is glued on."""


@dataclass(frozen=True, slots=True)
class BodyMachiningPlan:
    """The setups that machine one body, plus the blank they need.

    Args:
        index_pins: Program that drills the two index pins from the top.
        top: Top-face setup: pockets, holes, and the upper half of the
            outline.
        top_small_holes: Top-face program with the small drill for holes
            narrower than the main tool, and with the small end mill for
            routes the main tool fits nowhere in (a wire channel under a
            12 mm end mill), or ``None`` when there are none.
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
        top_carve_flats: Top-face program taking a carved top's flat
            parts with a big flat end mill, run before ``top_carve``, or
            ``None``.
        top_steps: Top-face program lowering a stepped top's bands, run
            first, or ``None``.
        back: Back-face setup after the flip: rear cavities, cover
            recesses and rear holes.
        back_release: The lower half of the outline with its tabs, cut
            once every other back program has run (``Body_back_outline``):
            the body freed last; ``None`` without the outline.
        core_index_pins: Under a separate top, the program that drills the
            index pins through the core before the top is glued on, or
            ``None`` without routes under it.
        core_top: The core's own routes (wire channels, chambers), cut
            into its top before the top is glued on, or ``None``.
        core_small_routes: The core's routes too narrow for the main tool,
            cut with the small end mill after ``core_top``, or ``None``.
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
    top_carve_flats: Setup | None = None
    back_release: Setup | None = None
    core_index_pins: Setup | None = None
    core_top: Setup | None = None
    core_small_routes: Setup | None = None

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the setups in running order.

        Under a separate top the core's own programs come first, before the
        top is glued on. Each face runs its main program, then its
        electronics program, then its small-drill program.
        """
        candidates = (
            self.core_index_pins,
            self.core_top,
            self.core_small_routes,
            self.index_pins,
            self.top_carve_flats,
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
            self.back_release,
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
            *_cap_notes(body),
            "Insert both dowels after this program before running Body_top.",
        ),
        reference_points,
    )
    core_pins, core_top, core_small = _core_setups(
        body, pins, stock, top_frame, parameters
    )

    # A route the main tool fits nowhere in (a wire channel, the truss
    # rod's access, under a wide end mill) is cut with the small end mill
    # instead, in the face's small-drill program after the main ones.
    small_tool = parameters.small_cutter
    top_narrow: list[Toolpath] = []

    def top_pocket(cavity: Cavity, tool: MachiningParameters = parameters) -> Toolpath:
        return _top_pocket(cavity, body, top_frame, tool)

    top_paths: list[Toolpath] = []
    # An epoxy tray first, over the whole top, its walls left standing:
    # the routes are cut down inside them afterwards.
    if body.epoxy_tray is not None:
        tray = body.epoxy_tray
        top_paths.append(
            pocket(
                "Epoxy tray",
                top_frame.polygon(simplified(tray.outline, 0.05)),
                tray.depth,
                parameters,
                islands=[top_frame.polygon(wall) for wall in tray.walls],
            )
        )
    for cavity in _top_cavities(body):
        if cavity in body.control_top_cavities:
            continue
        if _tool_fits(_pocket_outline(cavity), parameters):
            top_paths.append(top_pocket(cavity))
            # A tilted floor (an angled neck pocket) steps down after it.
            top_paths += _floor_terraces(cavity, top_frame, parameters)
        else:
            top_narrow.append(top_pocket(cavity, small_tool))
            top_narrow += _floor_terraces(cavity, top_frame, small_tool)
    small_holes = [
        hole for hole in body.holes if hole.diameter < parameters.tool_diameter - 1e-6
    ] + [
        hole
        for hole in body.control_top_marks
        if hole.diameter < parameters.tool_diameter - 1e-6
    ]
    controls = [
        cavity
        for cavity in body.control_top_cavities
        if _tool_fits(_pocket_outline(cavity), parameters)
    ]
    top_narrow += [
        top_pocket(cavity, small_tool)
        for cavity in body.control_top_cavities
        if cavity not in controls
    ]
    top_controls: Setup | None = None
    if controls:
        top_controls = Setup(
            "Body_top_controls",
            "Body top face - control plate recess and cavity",
            tuple(top_pocket(cavity) for cavity in controls),
            (
                "Same fixture, tool and X/Y zero as Body_top.",
                "The plate's screw spots are in Body_top_small_holes.",
            ),
            reference_points,
            fixture=TOP_FIXTURE,
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
            *_narrow_notes(top_narrow, parameters, "Body_top_small_holes"),
        ),
        reference_points,
        fixture=TOP_FIXTURE,
    )

    top_small_holes: Setup | None = None
    if small_holes or top_narrow:
        cutter = "end mill" if top_narrow else "drill"
        top_small_holes = Setup(
            "Body_top_small_holes",
            _small_description("Body top face", top_narrow, small_holes, small_tool),
            (
                *top_narrow,
                *(
                    _drill_hole(hole, body, top_frame, small_tool)
                    for hole in small_holes
                ),
            ),
            (
                f"Same fixture and X/Y zero as Body_top; change to the small {cutter} "
                "and re-touch Z on the stock top.",
            ),
            reference_points,
            small_tool,
            fixture=TOP_FIXTURE,
        )

    electronics = [
        rear
        for rear in (body.control_cavity, body.switch_cavity, body.battery_cavity)
        if rear is not None
    ]
    back_paths: list[Toolpath] = []
    control_paths: list[Toolpath] = []
    back_narrow: list[Toolpath] = []
    for rear in body.extra_rear_cavities:
        wide, narrow = _rear_pockets(rear, back_frame, parameters)
        back_paths += wide
        back_narrow += narrow
    for rear in electronics:
        wide, narrow = _rear_pockets(rear, back_frame, parameters)
        control_paths += wide
        back_narrow += narrow
    back_small = [
        hole
        for hole in (*body.rear_holes, *body.control_back_marks)
        if hole.diameter < parameters.tool_diameter - 1e-6
    ]
    back_controls: Setup | None = None
    if control_paths:
        back_controls = Setup(
            "Body_back_controls",
            "Body back face - electronics cavities and their cover recesses",
            tuple(control_paths),
            (
                "Same fixture, tool and X/Y zero as Body_back (the outline "
                "is cut last, in Body_back_outline).",
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
            fixture=BACK_FIXTURE,
        )
    for hole in body.rear_holes:
        if hole not in back_small:
            back_paths.append(_drill_rear_hole(hole, body, back_frame, parameters))
    # The outline's lower half, with its tabs, is a program of its own run
    # last of all (Body_back_outline): the cut that frees the body comes
    # at the very end, after every other back program.
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
        "Body back face - bridge cavities, rear holes",
        tuple(back_paths),
        (
            "Flip the blank about the neck centerline onto the same two index pins.",
            "Keep X/Y zero at index pin 1; set Z zero on the (new) stock top.",
            *(
                (
                    "The outline's lower half is cut last, in Body_back_outline, "
                    "after every other back program.",
                )
                if cut_outline
                else ()
            ),
            *_narrow_notes(back_narrow, parameters, "Body_back_small_holes"),
        ),
        reference_points,
        fixture=BACK_FIXTURE,
    )
    back_release: Setup | None = None
    if cut_outline:
        back_release = Setup(
            "Body_back_outline",
            "Body back face - lower half of the outline with its tabs, the body "
            "freed last",
            (
                profile(
                    "Outline, lower half with tabs",
                    back_frame.polygon(body.outline.points),
                    half_depth,
                    parameters,
                    with_tabs=True,
                ),
            ),
            (
                "Same fixture, tool and X/Y zero as Body_back: run it last, "
                "after every other back program.",
                f"The outline finishes with {parameters.tab_count} holding tabs "
                f"{parameters.tab_height:.1f} mm high; saw and sand them off."
                if parameters.tab_count
                else "The outline is cut through: the body comes free.",
                "The dowels stay in the waste frame, which the tabs keep attached "
                "to the body until the end.",
            ),
            reference_points,
            fixture=BACK_FIXTURE,
        )

    back_small_holes: Setup | None = None
    if back_small or back_narrow:
        cutter = "end mill" if back_narrow else "drill"
        back_small_holes = Setup(
            "Body_back_small_holes",
            _small_description("Body back face", back_narrow, back_small, small_tool),
            (
                *back_narrow,
                *(
                    _drill_rear_hole(hole, body, back_frame, small_tool)
                    for hole in back_small
                ),
            ),
            (
                f"Same fixture and X/Y zero as Body_back; change to the small {cutter} "
                "and re-touch Z on the stock top (the back face).",
                *body.joint_notes,
            ),
            reference_points,
            small_tool,
            fixture=BACK_FIXTURE,
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
    top_carve_flats, top_carve = _carve_setups(
        body, top_frame, parameters, reference_points
    )
    top_steps = _steps_setup(body, top_frame, parameters, reference_points)

    top_outline = top_frame.polygon(body.outline.points)
    back_outline = back_frame.polygon(body.outline.points)
    previews = [top_outline, top_outline]
    for optional in (core_pins, core_top, core_small):
        if optional is not None:
            previews.append(top_outline)
    for optional in (top_carve_flats, top_carve, top_steps):
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
    for optional in (back_controls, back_small_holes, back_edges, back_release):
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
        top_carve_flats=top_carve_flats,
        back_release=back_release,
        core_index_pins=core_pins,
        core_top=core_top,
        core_small_routes=core_small,
    )
    return plan if prefix == "Body" else _renamed(plan, prefix)


def _cap_notes(body: BodySolid) -> tuple[str, ...]:
    """Return what Body_index_pins says of a separate top, if any."""
    if body.cap_thickness == 0.0:
        return ()
    if body.core_cavities:
        return (
            f"The blank is the core with its {body.cap_thickness:g} mm top glued "
            "on (Body_core_top first): the drill runs on through the top into "
            "the core's own dowel holes.",
        )
    return (
        f"The blank is the core ({body.core_thickness:g} mm) with its "
        f"{body.cap_thickness:g} mm top glued on first.",
    )


def _core_setups(
    body: BodySolid,
    pins: Sequence[tuple[float, float]],
    stock: StockBounds,
    frame: _Frame,
    parameters: MachiningParameters,
) -> tuple[Setup | None, Setup | None, Setup | None]:
    """Return the core's own programs under a separate top, run before the
    top is glued on: its dowel holes, then its routes (the wire channels
    and chambers hidden under the top), then the routes too narrow for the
    main tool, with the small end mill; ``None`` for each one not needed.
    """
    if not body.core_cavities:
        return None, None, None
    wide = [
        cavity
        for cavity in body.core_cavities
        if _tool_fits(cavity.outline, parameters)
    ]
    narrow = [cavity for cavity in body.core_cavities if cavity not in wide]
    origin_x, origin_y = pins[0]
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])
    core = body.core_thickness
    pins_setup = Setup(
        "Body_core_index_pins",
        f"Body core index pins - drill both {parameters.pin_diameter:g} mm dowel "
        "holes through the core, before its top is glued on",
        tuple(
            drill(
                f"Index pin {index}",
                frame.point(Point2D(x, y)),
                parameters.pin_diameter,
                core + parameters.through_overshoot,
                parameters,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            "The core first, its top not yet glued on: clamp it top face up on "
            "a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the core's top.",
            f"Core blank: at least {stock.length:.0f} x {stock.width:.0f} x "
            f"{core:g} mm; the top's blank as large and "
            f"{body.cap_thickness:g} mm thick.",
            "Insert both dowels after this program before running "
            f"{'Body_core_top' if wide else 'Body_core_small_routes'}.",
        ),
        reference_points,
    )

    def routes(
        cavities: list[Cavity], tool: MachiningParameters
    ) -> tuple[Toolpath, ...]:
        return tuple(
            pocket(cavity.name, frame.polygon(cavity.outline), cavity.depth, tool)
            for cavity in cavities
        )

    small = parameters.small_cutter
    narrow_paths = routes(narrow, small)
    # The top goes on after the last of the core's programs.
    glue_note = (
        f"Then glue the {body.cap_thickness:g} mm top on, the core still on "
        "its dowels and the glue kept out of the routes and the dowel holes; "
        "once it has set, Body_index_pins drills on through the top into the "
        "core's dowel holes, and every other program follows as for a body "
        "of one piece."
    )
    routes_setup: Setup | None = None
    if wide:
        routes_setup = Setup(
            "Body_core_top",
            "Body core top - wire channels and chambers, hidden under the top",
            routes(wide, parameters),
            (
                "Core on the two index pins, top face up, same work zero as "
                "Body_core_index_pins.",
                *_narrow_notes(narrow_paths, parameters, "Body_core_small_routes"),
                *(() if narrow else (glue_note,)),
            ),
            reference_points,
            fixture=CORE_FIXTURE,
        )
    small_setup: Setup | None = None
    if narrow:
        small_setup = Setup(
            "Body_core_small_routes",
            "Body core top - the routes too narrow for the main tool, for the "
            f"{small.tool_diameter:g} mm end mill",
            narrow_paths,
            (
                "Core on the two index pins, top face up, same work zero as "
                "Body_core_index_pins; change to the small end mill and re-touch "
                "Z on the core's top.",
                glue_note,
            ),
            reference_points,
            small,
            fixture=CORE_FIXTURE,
        )
    return pins_setup, routes_setup, small_setup


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
            fixture=None if setup.fixture is None else text(setup.fixture),
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
            "top_carve_flats",
            "back_release",
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
        # In eco mode the tool comes down fast to over the floor the band's
        # last pass left (the stock top for its first).
        cleared = 0.0
        for z in depth_levels(start, depth, parameters.step_down):
            for run in runs:
                _cut_step_pass(
                    builder, frame.polygon(run), z, spacing * STEP_LINK, cleared
                )
            if parameters.eco_mode:
                cleared = z
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
        fixture=TOP_FIXTURE,
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
    builder: PathBuilder,
    run: Sequence[Point2D],
    z: float,
    link: float,
    cleared: float = 0.0,
) -> None:
    """Run one pass at ``z``, from its end nearest the tool.

    A closed pass (its ends together) starts from its point nearest the
    tool. A pass no further than ``link`` from where the last one ended is
    fed straight across at depth; otherwise the tool lifts, comes down fast
    to 1 mm over ``cleared`` (the Z the wood there is cut down to already:
    the stock top, by default) and plunges.
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
        builder.rapid_down_to(cleared)
    if builder.z > z:
        builder.plunge_to(z)
    for point in points[1:]:
        builder.cut_to(point.x, point.y)


CARVE_EDGE_REACH = 3.0
"""How far past its tool's radius a carve's rim level is cut beyond the
body's edge (room for the cutter to finish the rim right to the edge;
the waste further out is left), in mm."""


def _carve_setups(
    body: BodySolid,
    frame: _Frame,
    parameters: MachiningParameters,
    reference_points: tuple[tuple[float, float], ...],
) -> tuple[Setup | None, Setup | None]:
    """Return the programs that arch a carved top: the big flat end mill's
    over its flat parts first (``carve_flat_tool_diameter``) or ``None``,
    and the carve's own; ``(None, None)`` for a flat top.

    A flat end mill (``carve_tool_diameter``, else the main tool) roughs
    the arch in step-down layers, its runs taken nearest first and linked
    in the cut, the last layer following the arch: the steps it leaves
    are sanded smooth by hand. With ``carve_finish`` a ball nose as wide
    finishes it in passes ``CARVE_FINISH_STEP`` apart. The rim's level is
    cut on past the edge only as far as the tool needs to finish it.

    The big flat end mill roughs it all the same way first, quickly: the
    rim cut flat to its level, the fall left standing where the cutter's
    width rides over it. The roughing then cuts only the wood it left, and
    the ball nose only where it takes off more than the roughing tool
    left, the fall: never the flat plateau and rim.
    """
    carve = body.carved_top
    if carve is None:
        return None, None
    tool = parameters.carve_cutter
    flats: Setup | None = None
    stock: OffsetGrid | None = None
    flat = parameters.carve_flat_cutter
    if flat is not None:
        flat_sampled, flat_x_range, flat_y_range = _carve_surface(
            carve, body, frame, flat
        )
        stock = offset_sampled_surface(flat_sampled, flat)
        flats = Setup(
            "Body_top_carve_flats",
            "Body top face - carved top's flats with a "
            f"{flat.tool_diameter:g} mm flat end mill, before Body_top_carve",
            (
                raster_rough(
                    "Carved top flats",
                    stock,
                    flat,
                    x_range=flat_x_range,
                    y_range=flat_y_range,
                    step_over=flat.raster_spacing,
                    sample_spacing=2.0,
                    link_distance=4.0 * flat.raster_spacing,
                ),
            ),
            (
                "Same fixture and X/Y zero as Body_index_pins, dowels in; run it "
                "first, then Body_top_carve.",
                f"A {flat.tool_diameter:g} mm flat end mill (touch Z on the stock "
                "top): the rim along the edge cut flat to its level, the bulk of "
                "the wood taken off the fall, never below the arch. "
                "Body_top_carve's tools cut only what it leaves.",
                "The rim's level is cut a little past the body's edge, into the "
                "waste the outline takes later.",
            ),
            reference_points,
            flat,
            fixture=TOP_FIXTURE,
        )
    sampled, x_range, y_range = _carve_surface(carve, body, frame, tool)
    tips = offset_sampled_surface(sampled, tool)
    rough = raster_rough(
        "Carved top roughing",
        tips,
        tool,
        x_range=x_range,
        y_range=y_range,
        step_over=tool.raster_spacing,
        sample_spacing=2.0,
        link_distance=4.0 * tool.raster_spacing,
        stock=stock,
    )
    notes = [
        "Same fixture and X/Y zero as Body_index_pins, dowels in; run it "
        + ("after Body_top_carve_flats, " if flats is not None else "")
        + "before Body_top.",
        f"Rough with a {tool.tool_diameter:g} mm flat end mill"
        + (
            ""
            if parameters.carve_tool_diameter <= 0.0
            else " (not the main tool: touch Z on the stock top after the change)"
        )
        + (": only the wood Body_top_carve_flats left." if flats is not None else "."),
        "The rim's level is cut a little past the body's edge, into the "
        "waste the outline takes later.",
    ]
    if not parameters.carve_finish:
        notes.append(
            "The last layer follows the arch in rows "
            f"{tool.raster_spacing:g} mm apart: sand their steps smooth by hand."
        )
        return flats, Setup(
            "Body_top_carve",
            f"Body top face - carved top, {carve.height:g} mm arch to a "
            f"{carve.rim:g} mm rim, roughed to sand",
            (rough,),
            tuple(notes),
            reference_points,
            tool,
            fixture=TOP_FIXTURE,
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
        # In eco mode only where the end mill left wood, with flats or not.
        rest=tips if flats is not None or ball.eco_mode else None,
        link_distance=ball.eco_link_distance,
    )
    notes.append(
        f"Change to a {ball.tool_diameter:g} mm ball nose for the finishing "
        "passes and re-touch Z on the stock top (the plateau); sand the "
        "passes' scallops smooth."
        + (
            " It runs only over the fall: the plateau and the rim are flat as "
            "the end mills left them."
            if flats is not None or ball.eco_mode
            else ""
        )
    )
    return flats, Setup(
        "Body_top_carve",
        f"Body top face - carved top, {carve.height:g} mm arch to a "
        f"{carve.rim:g} mm rim",
        (rough, finish),
        tuple(notes),
        reference_points,
        ball,
        fixture=TOP_FIXTURE,
    )


def _carve_surface(
    carve: CarvedTop, body: BodySolid, frame: _Frame, tool: MachiningParameters
) -> tuple[SampledSurface, tuple[float, float], tuple[float, float]]:
    """Return a carved top's surface sampled for ``tool``, and the X and Y
    ranges it runs over: the rim's level cut on past the edge only as far
    as the tool needs (``CARVE_EDGE_REACH`` past its radius, within the
    carve's ``band``), the blank's top beyond."""
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
    return sampled, x_range, y_range


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
        fixture=TOP_FIXTURE,
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
    tool = parameters.relief_cutter
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
        fixture=TOP_FIXTURE,
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
    scoops = [
        cavity
        for cavity in body.top_cavities
        if face == "top" and isinstance(cavity, ScoopedGrooves)
    ]
    if not contours and not scoops and edge.radius <= 0.0:
        return None
    ball = parameters.ball_cutter
    paths: list[Toolpath] = []
    for contour in contours:
        paths += contour_paths(contour, frame.model, ball, floor)
    for grooves in scoops:
        paths += scoop_paths(grooves, frame.model, ball)
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
                (lambda point: edge.rounds_at(frame.model(point)))
                if edge.square
                else None,
            )
        )
    other = "Body_top" if face == "top" else "Body_back"
    what = " and ".join(
        [contour.name.lower() for contour in contours]
        + [f"{grooves.name}'s scoops" for grooves in scoops]
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
        fixture=TOP_FIXTURE if face == "top" else BACK_FIXTURE,
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
    """Pocket one top cavity; a through route runs on past the back.

    Of scooped grooves, the part at full depth: where they lift out of
    the wood the ball nose follows (``Body_top_edges``).
    """
    if isinstance(cavity, ScoopedGrooves):
        cavity = TracedCavity(cavity.name, cavity.flat_outline, cavity.depth)
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


def _pocket_outline(cavity: Cavity) -> tuple[Point2D, ...]:
    """Return the outline ``_top_pocket`` pockets a top cavity to: of
    scooped grooves, the part at full depth."""
    if isinstance(cavity, ScoopedGrooves):
        return cavity.flat_outline
    return cavity.outline


def _tool_fits(outline: Sequence[Point2D], parameters: MachiningParameters) -> bool:
    """Return whether the tool fits anywhere in a route's ``outline``: if
    not, ``pocket`` cannot cut the route with it."""
    return bool(offset_polygon(outline, parameters.tool_radius, inward=True))


def _narrow_notes(
    routes: Sequence[Toolpath], parameters: MachiningParameters, program: str
) -> tuple[str, ...]:
    """Return a note naming the routes too narrow for the main tool, cut
    in ``program`` with the small end mill; none without such routes."""
    if not routes:
        return ()
    names = ", ".join(route.name for route in routes)
    return (
        f"Too narrow for the {parameters.tool_diameter:g} mm end mill, cut in "
        f"{program} with the {parameters.small_hole_tool_diameter:g} mm one: "
        f"{names}.",
    )


def _small_description(
    face: str,
    routes: Sequence[Toolpath],
    holes: Sequence[DrilledHole],
    small: MachiningParameters,
) -> str:
    """Return a small-drill program's description: ``face``'s holes for
    the small drill, or its narrow routes (and holes) for the small end
    mill."""
    if not routes:
        return f"{face} - holes for the {small.tool_diameter:g} mm drill"
    what = "narrow routes and holes" if holes else "narrow routes"
    return f"{face} - {what} for the {small.tool_diameter:g} mm end mill"


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
) -> tuple[list[Toolpath], list[Toolpath]]:
    """Pocket one rear cavity: its cover recess (none for a cover screwed
    onto the back), the cavity, its steps.

    Returns:
        The pockets cut with the main tool, and those it fits nowhere in,
        cut with the small end mill (``small_cutter``) instead.
    """
    recessed = not rear.cover_on_back
    parts = [
        *(((rear.cover_recess, 0.0),) if recessed else ()),
        (rear.cavity, rear.cover_recess.depth if recessed else 0.0),
        *((step, rear.cavity.depth) for step in rear.steps),
    ]
    wide: list[Toolpath] = []
    narrow: list[Toolpath] = []
    for part, start_depth in parts:
        fits = _tool_fits(part.outline, parameters)
        (wide if fits else narrow).append(
            pocket(
                part.name,
                frame.polygon(part.outline),
                part.depth,
                parameters if fits else parameters.small_cutter,
                start_depth=start_depth,
            )
        )
    return wide, narrow


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
        for floor in rear.routes:
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
