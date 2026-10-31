"""2.5D machining operations: pockets, holes, and outside profiles.

Every operation works in the machine frame of one setup — X/Y at the
work origin, Z = 0 on the stock top, depths positive downward — and
returns a ``Toolpath`` of tool-centre moves. Geometry is passed in as
polygons of ``Point2D``; the operations never see the CAD model.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from ..geometry.primitives import Point2D
from .exceptions import ToolpathError
from .parameters import MachiningParameters
from .planar import (
    EdgeGrid,
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
    islands: Sequence[Sequence[Point2D]] = (),
) -> Toolpath:
    """Clear a closed polygon to ``depth`` and finish its walls.

    Each depth pass rasters the region where the tool fits with the
    finishing allowance still on the walls, linking rows in the cut
    where the link stays clear and retracting otherwise, then runs one
    finishing contour at the exact tool-radius offset. Plunges are
    straight, at the plunge rate. ``islands`` are left standing (an
    epoxy tray's walls round the openings in it): the raster keeps off
    them, and each gets its own finishing contour round it; where two
    walls are too close for the tool, a finishing contour is left off
    between them (``_contour_runs``).

    In eco mode (``parameters.eco_mode``) the tool comes down fast to
    just over the floor its last pass left before it plunges (the stock
    top for the first: that pass alone vouches for the wood it cut), every
    other pass's raster runs the other way round, from where the last
    pass ended, and a closed finishing contour starts at its point nearest
    the tool: no long feed across the pocket already cut.

    Raises:
        ToolpathError: If the tool cannot fit anywhere in the polygon.
    """
    radius = parameters.tool_radius
    rough_radius = radius + parameters.finishing_allowance
    rows = _raster_rows(polygon, rough_radius, parameters.raster_spacing, islands)
    contours = [
        oriented(offset_polygon(polygon, radius, inward=True), clockwise=True),
        *(
            oriented(offset_polygon(island, radius, inward=False), clockwise=False)
            for island in islands
        ),
    ]
    runs = (
        [
            run
            for contour in contours
            for run in _contour_runs(contour, polygon, islands, radius)
        ]
        if islands
        else [(*contour, contour[0]) for contour in contours if contour]
    )
    if not rows and not runs:
        raise ToolpathError(
            f"{name} is too narrow for a {parameters.tool_diameter} mm tool."
        )
    builder = _builder(name, parameters)
    eco = parameters.eco_mode
    cleared = 0.0
    for level, z in enumerate(depth_levels(start_depth, depth, parameters.step_down)):
        _cut_raster(
            builder,
            rows,
            z,
            polygon,
            rough_radius,
            parameters,
            islands,
            backward=eco and level % 2 == 1,
            cleared=cleared,
        )
        for run in runs:
            _cut_contour(
                builder,
                _from_nearest(run, builder) if eco else run,
                z,
                polygon,
                radius,
                parameters,
                islands,
                cleared=cleared,
            )
        if eco:
            cleared = z
    return builder.build()


def _from_nearest(
    run: tuple[Point2D, ...], builder: PathBuilder
) -> tuple[Point2D, ...]:
    """Return a closed run (its first point again at its end) started at
    its point nearest the tool, the same way round; an open run as it is."""
    if not builder.positioned or len(run) < 3 or run[0] != run[-1]:
        return run
    ring = run[:-1]
    first = min(
        range(len(ring)),
        key=lambda index: math.hypot(
            ring[index].x - builder.x, ring[index].y - builder.y
        ),
    )
    return (*ring[first:], *ring[:first], ring[first])


def _contour_runs(
    contour: Sequence[Point2D],
    polygon: Sequence[Point2D],
    islands: Sequence[Sequence[Point2D]],
    radius: float,
) -> list[tuple[Point2D, ...]]:
    """Return the stretches of a closed finishing contour the tool fits along.

    Its points where the tool stays inside ``polygon`` and off every
    island, in runs of neighbours: a contour that passes between two
    walls too close for the tool is broken there, not cut through them.
    """
    if not contour:
        return []
    fits = [
        disc_fits(point, polygon, radius)
        and all(
            disc_fits(point, island, radius, inside=False)
            for island in _near(islands, point, point, radius)
        )
        for point in contour
    ]
    if all(fits):
        return [(*contour, contour[0])]
    if not any(fits):
        return []
    # Start where a gap ends, so no run wraps round the end.
    start = next(
        index for index in range(len(contour)) if not fits[index - 1] and fits[index]
    )
    runs: list[tuple[Point2D, ...]] = []
    current: list[Point2D] = []
    for step in range(len(contour)):
        index = (start + step) % len(contour)
        if fits[index]:
            current.append(contour[index])
        elif current:
            runs.append(tuple(current))
            current = []
    if current:
        runs.append(tuple(current))
    return [run for run in runs if len(run) >= 2]


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
    circle on the floor. In eco mode each peck after the first comes back
    down fast to just over the last one's floor.

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


CORNER_TOLERANCE = 0.05
"""Wood the main tool may leave on a wall, in mm, before the small end
mill is sent there (``clean_corners``)."""


def clean_corners(
    name: str,
    polygon: Sequence[Point2D],
    depth: float,
    parameters: MachiningParameters,
    small: MachiningParameters,
    *,
    start_depth: float = 0.0,
    floor: Callable[[Point2D], float] | None = None,
) -> Toolpath | None:
    """Cut the wood a pocket of ``polygon`` left in its corners, with the
    ``small`` end mill.

    The pocket's tool (``parameters``) leaves its own radius in every
    inside corner. The small end mill follows its own finishing contour,
    but only along the stretches where it reaches wood the pocket's tool
    could not, each from a point where the wall is already clean to the
    next. It goes back and forth along a stretch, one pass deeper each
    way, so it never lifts in a corner, and comes down at the stretch's
    clean end, in the pocket already cut.

    Args:
        name: The toolpath's name.
        polygon: The pocket's outline, in the machine frame.
        depth: The pocket's depth.
        parameters: The tool the pocket was cut with.
        small: The end mill cutting the corners.
        start_depth: Where the pocket starts (a step's enclosing floor).
        floor: For a floor that is not level (an angled neck pocket's
            terraces), how deep the small end mill may go centred at a
            point; each stretch is cut as deep as it may go all along it.
            ``depth`` everywhere if not given.

    Returns:
        The toolpath, or ``None`` when the pocket's tool left no corner.
    """
    if small.tool_radius >= parameters.tool_radius:
        return None
    main = offset_polygon(polygon, parameters.tool_radius, inward=True)
    contour = oriented(
        offset_polygon(polygon, small.tool_radius, inward=True), clockwise=True
    )
    if not main or not contour:
        return None
    runs = _corner_runs(contour, main, parameters.tool_radius - small.tool_radius)
    if not runs:
        return None
    builder = _builder(name, small)
    for run in runs:
        bottom = depth if floor is None else min(floor(point) for point in run)
        builder.rapid_to(run[0].x, run[0].y)
        builder.rapid_down_to(0.0)
        path = run
        for z in depth_levels(start_depth, bottom, small.step_down):
            builder.plunge_to(z)
            for point in path[1:]:
                builder.cut_to(point.x, point.y)
            # Back the other way on the next pass.
            path = path[::-1]
    return builder.build()


def _corner_runs(
    contour: Sequence[Point2D], main: Sequence[Point2D], reach: float
) -> list[tuple[Point2D, ...]]:
    """Return the stretches of the small end mill's ``contour`` where it
    cuts wood the main tool's (``main``) left, a clean point at each end.

    Along a wall the two contours run ``reach`` apart (the difference of
    the tools' radii); in a corner the main tool's turns short of it, and
    a point of the small one's further than that from it has wood beside
    it. A contour with wood all round is one closed stretch.
    """
    near = reach + CORNER_TOLERANCE
    edges = EdgeGrid(main, max(near, 1.0))
    left = [not edges.within(point, near) for point in contour]
    if all(left):
        return [(*contour, contour[0])]
    count = len(contour)
    runs: list[tuple[Point2D, ...]] = []
    current: list[Point2D] = []
    # Start just past a clean point, so no stretch wraps round the end.
    start = next(index for index in range(count) if not left[index - 1])
    for step in range(count):
        index = (start + step) % count
        if left[index]:
            if not current:
                # From the clean point before it.
                current.append(contour[index - 1])
            current.append(contour[index])
        elif current:
            current.append(contour[index])
            runs.append(tuple(current))
            current = []
    return runs


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
    islands: Sequence[Sequence[Point2D]] = (),
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
        intervals = clear_intervals(polygon, y, radius, islands)
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
    islands: Sequence[Sequence[Point2D]] = (),
    *,
    backward: bool = False,
    cleared: float = 0.0,
) -> None:
    """Zigzag every raster row at one depth.

    ``backward`` runs the same zigzag the other way round, from its last
    row's end, so a pass can start where the one before it ended. A
    plunge comes down fast to just over ``cleared`` (``_approach``).
    """
    cuts: list[tuple[Point2D, Point2D]] = []
    forward = True
    for y, intervals in rows:
        ordered = (
            intervals if forward else [(high, low) for low, high in reversed(intervals)]
        )
        cuts += [(Point2D(start_x, y), Point2D(end_x, y)) for start_x, end_x in ordered]
        forward = not forward
    if backward:
        cuts = [(end, start) for start, end in reversed(cuts)]
    for start, end in cuts:
        _approach(builder, start, z, polygon, radius, parameters, islands, cleared)
        builder.cut_to(end.x, end.y)


def _cut_contour(
    builder: PathBuilder,
    contour: Sequence[Point2D],
    z: float,
    polygon: Sequence[Point2D],
    radius: float,
    parameters: MachiningParameters,
    islands: Sequence[Sequence[Point2D]] = (),
    *,
    cleared: float = 0.0,
) -> None:
    """Run one pass along a finishing contour at one depth, as given.

    A closed contour comes with its first point again at its end. The
    approach is checked with the bare tool radius: the contour's own
    points sit exactly one radius from the wall, and the only material
    the link can meet is the finishing allowance itself. A plunge comes
    down fast to just over ``cleared`` (``_approach``).
    """
    _approach(builder, contour[0], z, polygon, radius, parameters, islands, cleared)
    for point in contour[1:]:
        builder.cut_to(point.x, point.y)


def _approach(
    builder: PathBuilder,
    target: Point2D,
    z: float,
    polygon: Sequence[Point2D],
    radius: float,
    parameters: MachiningParameters,
    islands: Sequence[Sequence[Point2D]] = (),
    cleared: float = 0.0,
) -> None:
    """Get the tool to ``target`` at depth ``z``, staying in the cut if it can.

    If the straight link from the current position keeps the tool
    inside the already-cleared region (and off the islands), feed there
    at the current depth and plunge. Otherwise retract, rapid over, come
    down fast to 1 mm over ``cleared`` (the Z the wood there is already
    cut down to: the stock top, by default), and plunge.
    """
    if builder.positioned and builder.z <= 0.0:
        here = Point2D(builder.x, builder.y)
        spacing = parameters.raster_link_spacing
        if segment_fits(here, target, polygon, radius, spacing=spacing) and all(
            segment_fits(here, target, island, radius, inside=False, spacing=spacing)
            for island in _near(islands, here, target, radius)
        ):
            builder.cut_to(target.x, target.y)
            builder.plunge_to(z)
            return
    builder.rapid_to(target.x, target.y)
    builder.rapid_down_to(cleared)
    builder.plunge_to(z)


def _near(
    islands: Sequence[Sequence[Point2D]],
    start: Point2D,
    end: Point2D,
    radius: float,
) -> list[Sequence[Point2D]]:
    """Return the islands a disc moving from ``start`` to ``end`` may touch.

    Those whose bounds, ``radius`` out, meet the move's: the others it
    cannot reach, so need not be checked edge by edge.
    """
    low_x, high_x = min(start.x, end.x) - radius, max(start.x, end.x) + radius
    low_y, high_y = min(start.y, end.y) - radius, max(start.y, end.y) + radius
    near = []
    for island in islands:
        min_x, min_y, max_x, max_y = polygon_bounds(island)
        if min_x <= high_x and low_x <= max_x and min_y <= high_y and low_y <= max_y:
            near.append(island)
    return near


def _peck(
    builder: PathBuilder,
    start_depth: float,
    depth: float,
    parameters: MachiningParameters,
) -> None:
    """Plunge in step-down increments, lifting to clear chips between them.

    In eco mode each peck after the first comes back down fast to just
    over the last one's floor, as a pecking cycle (``G83``) does. Ends
    with the tool on the hole floor.
    """
    builder.rapid_down_to(-start_depth)
    levels = depth_levels(start_depth, depth, parameters.step_down)
    for index, z in enumerate(levels):
        if parameters.eco_mode and index > 0:
            builder.rapid_down_to(levels[index - 1])
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
