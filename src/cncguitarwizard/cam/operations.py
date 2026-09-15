"""2.5D machining operations: pockets, holes, and outside profiles.

Every operation works in the machine frame of one setup — X/Y at the
work origin, Z = 0 on the stock top, depths positive downward — and
returns a ``Toolpath`` of tool-centre moves. Geometry is passed in as
polygons of ``Point2D``; the operations never see the CAD model.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..geometry.primitives import Point2D
from .exceptions import ToolpathError
from .parameters import MachiningParameters
from .planar import (
    clear_intervals,
    disc_fits,
    offset_polygon,
    oriented,
    polygon_bounds,
    segment_fits,
)
from .toolpath import PathBuilder, Toolpath


def depth_levels(start_depth: float, depth: float, step_down: float) -> list[float]:
    """Return the Z of every pass from ``start_depth`` down to ``depth``.

    Passes are equal and never exceed ``step_down``; the last one lands
    exactly on ``-depth``.
    """
    if depth <= start_depth:
        raise ToolpathError("Cut depth must exceed the start depth.")
    count = max(1, math.ceil((depth - start_depth) / step_down - 1e-9))
    return [
        -(start_depth + (depth - start_depth) * index / count)
        for index in range(1, count + 1)
    ]


def pocket(
    name: str,
    polygon: Sequence[Point2D],
    depth: float,
    parameters: MachiningParameters,
    *,
    start_depth: float = 0.0,
) -> Toolpath:
    """Clear a closed polygon to ``depth`` and finish its walls.

    Each depth pass rasters the region where the tool fits with the
    finishing allowance still on the walls, linking rows in the cut
    where the link stays clear and retracting otherwise, then runs one
    finishing contour at the exact tool-radius offset. Plunges are
    straight, at the plunge rate.

    Raises:
        ToolpathError: If the tool cannot fit anywhere in the polygon.
    """
    radius = parameters.tool_radius
    rough_radius = radius + parameters.finishing_allowance
    rows = _raster_rows(polygon, rough_radius, parameters.raster_spacing)
    contour = oriented(offset_polygon(polygon, radius, inward=True), clockwise=True)
    if not rows and not contour:
        raise ToolpathError(
            f"{name} is too narrow for a {parameters.tool_diameter} mm tool."
        )
    builder = _builder(name, parameters)
    for z in depth_levels(start_depth, depth, parameters.step_down):
        _cut_raster(builder, rows, z, polygon, rough_radius, parameters)
        if contour:
            _cut_contour(builder, contour, z, polygon, radius, parameters)
    return builder.build()


def drill(
    name: str,
    centre: Point2D,
    diameter: float,
    depth: float,
    parameters: MachiningParameters,
    *,
    start_depth: float = 0.0,
) -> Toolpath:
    """Make a round hole with an end mill.

    A hole the tool's own size is peck-plunged. A larger hole is first
    peck-plunged at its centre (so no pillar survives) and then bored
    with a helix whose pitch is the step-down, ending with one full
    circle on the floor.

    Raises:
        ToolpathError: If the hole is smaller than the tool.
    """
    if diameter < parameters.tool_diameter - 1e-6:
        raise ToolpathError(
            f"{name} ({diameter} mm) is smaller than the "
            f"{parameters.tool_diameter} mm tool."
        )
    builder = _builder(name, parameters)
    builder.rapid_to(centre.x, centre.y)
    _peck(builder, start_depth, depth, parameters)
    helix_radius = (diameter - parameters.tool_diameter) / 2.0
    if helix_radius > 1e-6:
        _helix(builder, centre, helix_radius, start_depth, depth, parameters)
    return builder.build()


def profile(
    name: str,
    polygon: Sequence[Point2D],
    depth: float,
    parameters: MachiningParameters,
    *,
    start_depth: float = 0.0,
    with_tabs: bool = False,
) -> Toolpath:
    """Cut around the outside of a closed polygon, climb milling.

    The tool centre follows the outward tool-radius offset
    counter-clockwise, so the part stays on the tool's left. With
    ``with_tabs`` the passes within ``tab_height`` of the floor lift
    over ``tab_count`` evenly spaced bridges of ``tab_length``.
    """
    contour = oriented(
        offset_polygon(polygon, parameters.tool_radius, inward=False),
        clockwise=False,
    )
    if not contour:
        raise ToolpathError(f"{name} outline could not be offset.")
    builder = _builder(name, parameters)
    tab_top = -(depth - parameters.tab_height)
    tabs = _tab_spans(contour, parameters) if with_tabs and parameters.tab_count else []
    builder.rapid_to(contour[0].x, contour[0].y)
    for z in depth_levels(start_depth, depth, parameters.step_down):
        builder.plunge_to(z)
        if tabs and z < tab_top:
            _cut_loop_with_tabs(builder, contour, z, tab_top, tabs)
        else:
            for point in contour[1:]:
                builder.cut_to(point.x, point.y)
            builder.cut_to(contour[0].x, contour[0].y)
    return builder.build()


def _builder(name: str, parameters: MachiningParameters) -> PathBuilder:
    return PathBuilder(
        name,
        safe_height=parameters.safe_height,
        feed_rate=parameters.feed_rate,
        plunge_rate=parameters.plunge_rate,
    )


def _raster_rows(
    polygon: Sequence[Point2D],
    radius: float,
    spacing: float,
) -> list[tuple[float, list[tuple[float, float]]]]:
    """Return ``(y, intervals)`` for every raster row with something to cut."""
    _, min_y, _, max_y = polygon_bounds(polygon)
    low = min_y + radius
    high = max_y - radius
    if high < low:
        return []
    count = max(1, math.ceil((high - low) / spacing))
    rows = []
    for index in range(count + 1):
        y = low + (high - low) * index / count
        intervals = clear_intervals(polygon, y, radius)
        if intervals:
            rows.append((y, intervals))
    return rows


def _cut_raster(
    builder: PathBuilder,
    rows: list[tuple[float, list[tuple[float, float]]]],
    z: float,
    polygon: Sequence[Point2D],
    radius: float,
    parameters: MachiningParameters,
) -> None:
    """Zigzag every raster row at one depth."""
    forward = True
    for y, intervals in rows:
        ordered = intervals if forward else [
            (high, low) for low, high in reversed(intervals)
        ]
        for start_x, end_x in ordered:
            _approach(builder, Point2D(start_x, y), z, polygon, radius, parameters)
            builder.cut_to(end_x, y)
        forward = not forward


def _cut_contour(
    builder: PathBuilder,
    contour: Sequence[Point2D],
    z: float,
    polygon: Sequence[Point2D],
    radius: float,
    parameters: MachiningParameters,
) -> None:
    """Run one closed pass along the finishing contour at one depth.

    The approach is checked with the bare tool radius: the contour's
    own points sit exactly one radius from the wall, and the only
    material the link can meet is the finishing allowance itself.
    """
    _approach(builder, contour[0], z, polygon, radius, parameters)
    for point in contour[1:]:
        builder.cut_to(point.x, point.y)
    builder.cut_to(contour[0].x, contour[0].y)


def _approach(
    builder: PathBuilder,
    target: Point2D,
    z: float,
    polygon: Sequence[Point2D],
    radius: float,
    parameters: MachiningParameters,
) -> None:
    """Get the tool to ``target`` at depth ``z``, staying in the cut if it can.

    If the straight link from the current position keeps the tool
    inside the already-cleared region, feed there at the current depth
    and plunge. Otherwise retract, rapid over, and plunge.
    """
    if builder.positioned and builder.z <= 0.0:
        here = Point2D(builder.x, builder.y)
        if segment_fits(
            here,
            target,
            polygon,
            radius,
            spacing=parameters.raster_link_spacing,
        ):
            builder.cut_to(target.x, target.y)
            builder.plunge_to(z)
            return
    builder.rapid_to(target.x, target.y)
    builder.rapid_down_to(0.0)
    builder.plunge_to(z)


def _peck(
    builder: PathBuilder,
    start_depth: float,
    depth: float,
    parameters: MachiningParameters,
) -> None:
    """Plunge in step-down increments, lifting to clear chips between them.

    Ends with the tool on the hole floor.
    """
    builder.rapid_down_to(-start_depth)
    levels = depth_levels(start_depth, depth, parameters.step_down)
    for index, z in enumerate(levels):
        builder.plunge_to(z)
        if index < len(levels) - 1:
            builder.lift_to(-start_depth)


def _helix(
    builder: PathBuilder,
    centre: Point2D,
    helix_radius: float,
    start_depth: float,
    depth: float,
    parameters: MachiningParameters,
) -> None:
    """Bore a larger hole by descending along a sampled helix.

    Starts from the hole floor after the centre peck: lifts back to the
    start depth, steps out to the helix radius in air, and spirals down.
    """
    points_per_turn = 36
    total = depth - start_depth
    turns = max(1, math.ceil(total / parameters.step_down))
    steps = turns * points_per_turn
    builder.lift_to(-start_depth)
    builder.cut_to(centre.x + helix_radius, centre.y)
    for step in range(1, steps + 1):
        angle = 2.0 * math.pi * step / points_per_turn
        z = -(start_depth + total * step / steps)
        builder.cut_to(
            centre.x + helix_radius * math.cos(angle),
            centre.y + helix_radius * math.sin(angle),
            z,
        )
    for step in range(1, points_per_turn + 1):
        angle = 2.0 * math.pi * step / points_per_turn
        builder.cut_to(
            centre.x + helix_radius * math.cos(angle),
            centre.y + helix_radius * math.sin(angle),
        )
    builder.cut_to(centre.x, centre.y)


def _tab_spans(
    contour: Sequence[Point2D],
    parameters: MachiningParameters,
) -> list[tuple[float, float]]:
    """Return ``(start, end)`` arc-length spans of each holding tab."""
    perimeter = _perimeter(contour)
    half = parameters.tab_length / 2.0
    spans = []
    for index in range(parameters.tab_count):
        centre = perimeter * (index + 0.5) / parameters.tab_count
        spans.append((centre - half, centre + half))
    return spans


def _perimeter(contour: Sequence[Point2D]) -> float:
    count = len(contour)
    return sum(
        math.dist(
            (contour[index].x, contour[index].y),
            (contour[(index + 1) % count].x, contour[(index + 1) % count].y),
        )
        for index in range(count)
    )


def _cut_loop_with_tabs(
    builder: PathBuilder,
    contour: Sequence[Point2D],
    z: float,
    tab_top: float,
    spans: list[tuple[float, float]],
) -> None:
    """Cut once around the contour, lifting to ``tab_top`` across each tab."""
    count = len(contour)
    travelled = 0.0
    for index in range(count):
        start = contour[index]
        end = contour[(index + 1) % count]
        length = math.dist((start.x, start.y), (end.x, end.y))
        if length == 0.0:
            continue
        breaks = sorted(
            {
                boundary
                for span in spans
                for boundary in span
                if travelled < boundary < travelled + length
            }
        )
        cursor = 0.0
        for boundary in breaks + [length + travelled]:
            fraction = min(1.0, (boundary - travelled) / length)
            point = Point2D(
                start.x + (end.x - start.x) * fraction,
                start.y + (end.y - start.y) * fraction,
            )
            midpoint_distance = travelled + (cursor + fraction * length) / 2.0
            in_tab = any(low <= midpoint_distance <= high for low, high in spans)
            target_z = tab_top if in_tab else z
            if target_z != builder.z:
                builder.cut_to(builder.x, builder.y, target_z)
            builder.cut_to(point.x, point.y)
            cursor = fraction * length
        travelled += length
    if builder.z != z:
        builder.cut_to(builder.x, builder.y, z)


def pocket_fits(
    polygon: Sequence[Point2D],
    point: Point2D,
    parameters: MachiningParameters,
) -> bool:
    """Return whether the tool fits inside ``polygon`` centred at ``point``."""
    return disc_fits(point, polygon, parameters.tool_radius)
