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
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

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
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .toolpath import Toolpath


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

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the setups in running order.

        Each face runs its main program, then its electronics program,
        then its small-drill program.
        """
        candidates = (
            self.index_pins,
            self.top,
            self.top_controls,
            self.top_small_holes,
            self.top_edges,
            self.top_engraving,
            self.back,
            self.back_controls,
            self.back_small_holes,
            self.back_edges,
        )
        return tuple(setup for setup in candidates if setup is not None)


def plan_body_machining(
    body: BodySolid,
    parameters: MachiningParameters,
) -> BodyMachiningPlan:
    """Return toolpaths for every machinable feature of the body.

    Raises:
        ToolpathError: If an index pin would end up in the finished body,
            too close to a cut or the blank's edge, or a feature cannot
            be cut with the tool.
    """
    stock = StockBounds.around(body.outline.points, parameters.stock_margin)
    pins, stock = resolve_index_pins(
        body.outline.points,
        [cavity.outline for cavity in _top_cavities(body)],
        parameters,
        stock,
    )
    origin_x, origin_y = pins[0]
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])

    top_frame = _Frame(origin_x, origin_y, mirror_y=False)
    back_frame = _Frame(origin_x, origin_y, mirror_y=True)
    half_depth = body.thickness / 2.0 + parameters.profile_overlap

    pin_setup = Setup(
        "Body_index_pins",
        "Body index pins - drill both dowel holes through the blank",
        tuple(
            drill(
                f"Index pin {index}",
                top_frame.point(Point2D(x, y)),
                parameters.index_pin_diameter,
                body.thickness + parameters.through_overshoot,
                parameters,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            "Clamp the blank top face up on a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the stock top.",
            "Both dowels sit in the waste on the centerline - pin 1 in the horn "
            "gap ahead of the neck pocket, pin 2 in the tail notch - so they "
            "never end up in the finished body.",
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
                top_frame.polygon(body.outline.points),
                body.top_edge,
                parameters,
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
                    if body.battery_cavity is not None
                    else ()
                ),
            ),
            reference_points,
        )
    for hole in body.rear_holes:
        if hole not in back_small:
            back_paths.append(_drill_rear_hole(hole, body, back_frame, parameters))
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
                back_frame.polygon(body.outline.points),
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

    top_outline = top_frame.polygon(body.outline.points)
    back_outline = back_frame.polygon(body.outline.points)
    previews = [top_outline, top_outline]
    for optional in (top_controls, top_small_holes, top_edges, top_engraving):
        if optional is not None:
            previews.append(top_outline)
    previews.append(back_outline)
    for optional in (back_controls, back_small_holes, back_edges):
        if optional is not None:
            previews.append(back_outline)
    return BodyMachiningPlan(
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
    return Setup(
        "Body_top_engraving",
        f"Body top face - decorative engraving {depth:g} mm deep with a V-bit",
        (engraving_path(body.engraving, frame.point, tool),),
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
                frame.polygon(body.outline.points),
                edge.radius,
                ball,
                lambda point: max(
                    (contour.depth_at(frame.model(point)) for contour in contours),
                    default=0.0,
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
