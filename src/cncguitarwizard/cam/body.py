"""Plan the two-sided machining of a ``BodySolid``.

The body is a flat slab, so everything on it is 2.5D work with one end
mill and two setups: the top face up, then the blank flipped about the
neck centerline onto two index pins. Both setups share the same work
origin — index pin 1 — because flipping about the centerline maps the
model point ``(x, y)`` to the machine point ``(x, -y)`` and leaves the
pins where they were.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..geometry.body import BodySolid, Cavity, DrilledHole
from ..geometry.primitives import Point2D, point_in_polygon
from .exceptions import ToolpathError
from .gcode import Setup
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .planar import polygon_bounds
from .toolpath import Toolpath


@dataclass(frozen=True, slots=True)
class BodyMachiningPlan:
    """The setups that machine one body, plus the blank they need.

    Args:
        index_pins: Program that drills the two index pins from the top.
        top: Top-face setup: pockets, holes, and the upper half of the
            outline.
        back: Back-face setup after the flip: rear cavities, cover
            recesses, and the lower half of the outline with tabs.
        stock_length: Minimum blank length along X.
        stock_width: Minimum blank width along Y.
        stock_thickness: Blank thickness (the body thickness).
        origin_x: Model X of the work origin (index pin 1).
        origin_y: Model Y of the work origin.
    """

    index_pins: Setup
    top: Setup
    back: Setup
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float
    origin_y: float

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the setups in running order."""
        return (self.index_pins, self.top, self.back)


def plan_body_machining(
    body: BodySolid,
    parameters: MachiningParameters,
) -> BodyMachiningPlan:
    """Return toolpaths for every machinable feature of the body.

    Raises:
        ToolpathError: If an index pin lies outside the body, or a
            feature cannot be cut with the tool.
    """
    origin_x, origin_y = parameters.index_pin_positions[0]
    for x, y in parameters.index_pin_positions:
        if not point_in_polygon(Point2D(x, y), body.outline.points):
            raise ToolpathError(f"Index pin at ({x}, {y}) is outside the body.")

    top_frame = _Frame(origin_x, origin_y, mirror_y=False)
    back_frame = _Frame(origin_x, origin_y, mirror_y=True)
    half_depth = body.thickness / 2.0 + parameters.profile_overlap

    pins = Setup(
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
            for index, (x, y) in enumerate(parameters.index_pin_positions, start=1)
        ),
        (
            "Clamp the blank top face up on a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the stock top.",
            "Insert both dowels after this program before running Body_top.",
        ),
    )

    top_paths: list[Toolpath] = []
    for cavity in _top_cavities(body):
        top_paths.append(
            pocket(
                cavity.name,
                top_frame.polygon(cavity.outline),
                cavity.depth,
                parameters,
            )
        )
    for hole in body.holes:
        top_paths.append(_drill_hole(hole, body, top_frame, parameters))
    top_paths.append(
        profile(
            "Outline, upper half",
            top_frame.polygon(body.outline.points),
            half_depth,
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
    )

    back_paths: list[Toolpath] = []
    for rear in body.rear_cavities:
        back_paths.append(
            pocket(
                rear.cover_recess.name,
                back_frame.polygon(rear.cover_recess.outline),
                rear.cover_recess.depth,
                parameters,
            )
        )
        back_paths.append(
            pocket(
                rear.cavity.name,
                back_frame.polygon(rear.cavity.outline),
                rear.cavity.depth,
                parameters,
                start_depth=rear.cover_recess.depth,
            )
        )
    back_paths.append(
        profile(
            "Outline, lower half with tabs",
            back_frame.polygon(body.outline.points),
            half_depth,
            parameters,
            with_tabs=True,
        )
    )
    back = Setup(
        "Body_back",
        "Body back face - rear cavities, cover recesses, lower half of the outline",
        tuple(back_paths),
        (
            "Flip the blank about the neck centerline onto the same two index pins.",
            "Keep X/Y zero at index pin 1; set Z zero on the (new) stock top.",
            f"The outline finishes with {parameters.tab_count} holding tabs "
            f"{parameters.tab_height:.1f} mm high; saw and sand them off.",
        ),
    )

    min_x, min_y, max_x, max_y = polygon_bounds(body.outline.points)
    margin = 2.0 * parameters.tool_diameter
    return BodyMachiningPlan(
        pins,
        top,
        back,
        stock_length=max_x - min_x + 2.0 * margin,
        stock_width=max_y - min_y + 2.0 * margin,
        stock_thickness=body.thickness,
        origin_x=origin_x,
        origin_y=origin_y,
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


def _top_cavities(body: BodySolid) -> tuple[Cavity, ...]:
    """Return the top-face cavities in cutting order."""
    cavities: list[Cavity] = [body.neck_pocket, body.neck_pickup, body.bridge_pickup]
    if body.bridge_mounting.sustain_block_cavity is not None:
        cavities.append(body.bridge_mounting.sustain_block_cavity)
    cavities.extend(body.extra_cavities)
    return tuple(cavities)


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
        if point_in_polygon(hole.center, rear.cavity.outline):
            depth = min(
                depth, body.thickness - rear.depth + parameters.through_overshoot
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
