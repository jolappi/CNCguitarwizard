"""Toolpaths for the body's edge finishes: contours, roundovers, binding.

The arm contour, belly cut and roundovers are cut with a ball nose the
size of the main tool (the ball nose the neck back is finished with);
the binding channel is a plain profile with the main end mill. Every
function works in one setup's machine frame and takes a ``to_model``
map back to the model frame, where the geometry is described.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace

from ..geometry.body import Contour, EdgeProfile
from ..geometry.primitives import Point2D
from .operations import profile
from .parameters import MachiningParameters
from .planar import offset_polygon, oriented, polygon_bounds, segment_distance
from .surfacing import build_offset_grid, raster_rough
from .toolpath import PathBuilder, Toolpath

ToModel = Callable[[Point2D], Point2D]

CONTOUR_STEP_OVER = 1.0
"""Distance between the finishing passes over a contour, in mm."""

ROUNDOVER_ARC_STEP = 1.0
"""Distance between roundover passes, measured round the ball's path."""


def ball_tool(parameters: MachiningParameters) -> MachiningParameters:
    """Return the main tool's settings for a ball nose of the same size."""
    return replace(parameters, tool_tip="ball")


def contour_paths(
    contour: Contour,
    to_model: ToModel,
    tool: MachiningParameters,
    floor: float = math.inf,
) -> tuple[Toolpath, Toolpath]:
    """Return the roughing and finishing passes for one contour.

    The bevel's surface is sampled over its region (plus the tool's
    radius and the waste past the edge), offset for the ball, roughed in
    step-down layers and finished with passes ``CONTOUR_STEP_OVER``
    apart that only run where the surface is below the face. Nothing
    goes deeper than ``floor`` (the outline's holding tabs).
    """

    # Past the edge the ramp runs on through the outline's slot, which
    # is where the ball finishes the edge from; the waste beyond it is
    # left alone.
    slot = tool.tool_diameter + 0.5

    def height(x: float, y: float) -> float:
        return -min(contour.machining_depth(to_model(Point2D(x, y)), slot), floor)

    region = [_to_machine(point, to_model) for point in contour.region()]
    min_x, min_y, max_x, max_y = polygon_bounds(region)
    margin = tool.tool_radius + contour.depth
    x_range = (min_x - margin, max_x + margin)
    y_range = (min_y - margin, max_y + margin)
    grid = build_offset_grid(
        height, x_range, y_range, tool, spacing_x=1.0, spacing_y=1.0
    )
    rough = raster_rough(
        f"{contour.name} roughing",
        grid,
        tool,
        x_range=x_range,
        y_range=y_range,
        step_over=tool.tool_diameter * tool.step_over,
    )
    builder = _builder(f"{contour.name} finishing", tool)
    forward = True
    y = y_range[0]
    while y <= y_range[1] + 1e-9:
        xs = _steps(x_range[0], x_range[1], 1.0)
        if not forward:
            xs.reverse()
        tips = [grid.tip_at(x, y) for x in xs]
        for run in _below_face(xs, tips):
            builder.rapid_to(run[0][0], y)
            builder.rapid_down_to(run[0][1])
            builder.plunge_to(run[0][1])
            for x, z in run[1:]:
                builder.cut_to(x, y, z)
        forward = not forward
        y += CONTOUR_STEP_OVER
    return rough, builder.build()


def roundover_path(
    name: str,
    outline: Sequence[Point2D],
    radius: float,
    tool: MachiningParameters,
    face_depth: Callable[[Point2D], float],
    floor: float = math.inf,
) -> Toolpath:
    """Return passes that round the outline's edge over with a ball nose.

    The ball's centre sweeps a quarter circle ``radius + ball radius``
    about the fillet's own centre (``radius`` in from the edge and down
    from the face), one full loop of the outline per step, from the
    face down to the wall. ``face_depth`` lowers each point by any bevel
    already cut there, so the roundover follows an arm contour. No pass
    goes deeper than ``floor``.
    """
    ball = tool.tool_radius
    reach = radius + ball
    step = ROUNDOVER_ARC_STEP / reach
    count = max(2, math.ceil((math.pi / 2.0) / step))
    builder = _builder(name, tool)
    offsetter = _Offsetter(oriented(outline, clockwise=False))
    for index in range(1, count + 1):
        angle = (math.pi / 2.0) * index / count
        offset = -radius + reach * math.sin(angle)
        tip = reach * math.cos(angle) - radius - ball
        for run in offsetter.runs(offset):
            points = [(p, max(tip - face_depth(p), -floor)) for p in run]
            builder.rapid_to(points[0][0].x, points[0][0].y)
            builder.rapid_down_to(points[0][1])
            builder.plunge_to(points[0][1])
            for point, z in points[1:]:
                builder.cut_to(point.x, point.y, z)
    return builder.build()


def binding_path(
    name: str,
    outline: Sequence[Point2D],
    edge: EdgeProfile,
    parameters: MachiningParameters,
    face_drop: float = 0.0,
) -> Toolpath:
    """Return the profile that cuts a binding channel into the edge.

    ``face_drop``: how far the face at the edge lies below the stock top
    (a carved top's rim); the channel starts there.
    """
    inner = offset_polygon(outline, edge.binding_width, inward=True, sample_spacing=2.0)
    return profile(
        name, inner, face_drop + edge.binding_depth, parameters, start_depth=face_drop
    )


class _Offsetter:
    """Offset one closed outline by many distances, quickly.

    The outline is resampled every 1.5 mm and each sample pushed along
    its smoothed normal; samples that end up nearer the outline than the
    offset (at a tight concave or pointed spot) are dropped. A bucket
    grid of the outline's segments keeps each nearness check local.
    """

    CELL = 8.0

    def __init__(self, outline: Sequence[Point2D]) -> None:
        self.segments = list(zip(outline, (*outline[1:], outline[0]), strict=True))
        self.buckets: dict[tuple[int, int], list[int]] = {}
        for index, (a, b) in enumerate(self.segments):
            for cell in self._cells(
                min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)
            ):
                self.buckets.setdefault(cell, []).append(index)
        self.samples: list[tuple[Point2D, float, float]] = []
        for index, (a, b) in enumerate(self.segments):
            length = math.dist((a.x, a.y), (b.x, b.y))
            steps = max(1, math.ceil(length / 1.5))
            before = self.segments[index - 1][0]
            after = self.segments[(index + 1) % len(self.segments)][1]
            for step in range(steps):
                t = step / steps
                point = Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
                # Tangent blended toward the neighbouring segments near
                # the ends, so the normals turn smoothly at vertices.
                tx = (b.x - a.x) + (a.x - before.x) * (1.0 - t) + (after.x - b.x) * t
                ty = (b.y - a.y) + (a.y - before.y) * (1.0 - t) + (after.y - b.y) * t
                size = math.hypot(tx, ty) or 1.0
                # Counter-clockwise loop: the outward normal is on the right.
                self.samples.append((point, ty / size, -tx / size))

    def _cells(
        self, min_x: float, min_y: float, max_x: float, max_y: float
    ) -> list[tuple[int, int]]:
        size = self.CELL
        return [
            (cx, cy)
            for cx in range(math.floor(min_x / size), math.floor(max_x / size) + 1)
            for cy in range(math.floor(min_y / size), math.floor(max_y / size) + 1)
        ]

    def _nearer_than(self, point: Point2D, distance: float) -> bool:
        reach = distance - 0.05
        for cell in self._cells(
            point.x - reach, point.y - reach, point.x + reach, point.y + reach
        ):
            for index in self.buckets.get(cell, ()):
                a, b = self.segments[index]
                if segment_distance(point, a, b) < reach:
                    return True
        return False

    def runs(self, offset: float) -> list[list[Point2D]]:
        """Return the outline offset outward by ``offset`` (inward if negative).

        One closed loop (its first point repeated at the end) where every
        sample keeps its distance; otherwise the open runs between the
        spots where samples had to be dropped, so the tool lifts over
        those spots instead of cutting a chord across them.
        """
        moved = [
            Point2D(point.x + nx * offset, point.y + ny * offset)
            for point, nx, ny in self.samples
        ]
        if abs(offset) < 1e-6:
            return [[*moved, moved[0]]]
        kept = [not self._nearer_than(p, abs(offset)) for p in moved]
        if all(kept):
            return [[*moved, moved[0]]]
        if not any(kept):
            return []
        # Start just after a dropped sample so no run wraps round.
        start = kept.index(False)
        runs: list[list[Point2D]] = []
        current: list[Point2D] = []
        for step in range(1, len(moved) + 1):
            index = (start + step) % len(moved)
            if kept[index]:
                current.append(moved[index])
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)
        return [run for run in runs if len(run) >= 2]


def _to_machine(point: Point2D, to_model: ToModel) -> Point2D:
    """Invert ``to_model`` for a frame that is a shift and maybe a Y flip."""
    origin = to_model(Point2D(0.0, 0.0))
    unit_y = to_model(Point2D(0.0, 1.0))
    flip = unit_y.y - origin.y
    return Point2D(point.x - origin.x, (point.y - origin.y) * flip)


def _below_face(xs: list[float], tips: list[float]) -> list[list[tuple[float, float]]]:
    """Split a pass into runs where the tool cuts below the face."""
    runs: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for index, (x, tip) in enumerate(zip(xs, tips, strict=True)):
        cutting = (
            tip < -0.05
            or (index + 1 < len(tips) and tips[index + 1] < -0.05)
            or (index > 0 and tips[index - 1] < -0.05)
        )
        if cutting:
            current.append((x, min(tip, 0.0)))
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [run for run in runs if len(run) >= 2]


def _steps(start: float, end: float, spacing: float) -> list[float]:
    count = max(1, math.ceil((end - start) / spacing))
    return [start + (end - start) * index / count for index in range(count + 1)]


def _builder(name: str, tool: MachiningParameters) -> PathBuilder:
    return PathBuilder(
        name,
        safe_height=tool.safe_height,
        feed_rate=tool.feed_rate,
        plunge_rate=tool.plunge_rate,
    )
