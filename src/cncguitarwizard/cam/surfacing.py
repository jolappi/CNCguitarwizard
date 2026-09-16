"""3D surfacing: drop-cutter offset grids and raster toolpaths.

A part surface is given as a height function ``z(x, y)`` in the machine
frame (zero on the blank top, cuts negative) that is defined everywhere
the raster will sweep. ``build_offset_grid`` turns it into the *tool-tip
surface* — how low the tip may go at each grid node without any part of
the tool cutting below the part — for a flat or ball-nosed tool. Raster
passes then simply sample that grid.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass

from .exceptions import ToolpathError
from .operations import depth_levels
from .parameters import MachiningParameters
from .toolpath import PathBuilder, Toolpath

HeightFunction = Callable[[float, float], float]


@dataclass(frozen=True, slots=True)
class OffsetGrid:
    """Tool-tip heights on a regular grid.

    Args:
        x0: X of the first column.
        y0: Y of the first row.
        spacing_x: Column spacing.
        spacing_y: Row spacing.
        tips: ``tips[row][column]`` — lowest safe tip Z at that node.
    """

    x0: float
    y0: float
    spacing_x: float
    spacing_y: float
    tips: tuple[tuple[float, ...], ...]

    @property
    def x_max(self) -> float:
        return self.x0 + (len(self.tips[0]) - 1) * self.spacing_x

    @property
    def y_max(self) -> float:
        return self.y0 + (len(self.tips) - 1) * self.spacing_y

    def floor(self) -> float:
        """Return the lowest tip height anywhere on the grid."""
        return min(min(row) for row in self.tips)

    def tip_at(self, x: float, y: float) -> float:
        """Return the bilinearly interpolated tip height, clamped to the grid."""
        fx = min(max((x - self.x0) / self.spacing_x, 0.0), len(self.tips[0]) - 1.0)
        fy = min(max((y - self.y0) / self.spacing_y, 0.0), len(self.tips) - 1.0)
        ix = min(int(fx), len(self.tips[0]) - 2) if len(self.tips[0]) > 1 else 0
        iy = min(int(fy), len(self.tips) - 2) if len(self.tips) > 1 else 0
        tx = fx - ix
        ty = fy - iy
        row0 = self.tips[iy]
        row1 = self.tips[min(iy + 1, len(self.tips) - 1)]
        ix1 = min(ix + 1, len(row0) - 1)
        top = row0[ix] + (row0[ix1] - row0[ix]) * tx
        bottom = row1[ix] + (row1[ix1] - row1[ix]) * tx
        return top + (bottom - top) * ty


@dataclass(frozen=True, slots=True)
class SampledSurface:
    """Surface heights on a regular grid, each the maximum over its cell."""

    x0: float
    y0: float
    spacing_x: float
    spacing_y: float
    heights: tuple[tuple[float, ...], ...]


def sample_surface(
    surface: HeightFunction,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    spacing_x: float = 1.0,
    spacing_y: float = 0.5,
    edge_samples_x: int = 3,
    edge_samples_y: int = 1,
) -> SampledSurface:
    """Sample a height function on a grid, conservatively.

    Every node carries the *highest* height within its own cell, found
    from ``edge_samples_x`` × ``edge_samples_y`` sub-samples, so a wall
    or ridge between nodes is never missed. One sampling can be offset
    for several tools with ``offset_sampled_surface``.
    """
    x_count = max(2, math.ceil((x_range[1] - x_range[0]) / spacing_x) + 1)
    y_count = max(2, math.ceil((y_range[1] - y_range[0]) / spacing_y) + 1)
    xs = [x_range[0] + index * spacing_x for index in range(x_count)]
    ys = [y_range[0] + index * spacing_y for index in range(y_count)]
    sub_x = _cell_offsets(spacing_x, max(1, edge_samples_x))
    sub_y = _cell_offsets(spacing_y, max(1, edge_samples_y))
    heights = tuple(
        tuple(
            max(surface(x + ox, y + oy) for ox in sub_x for oy in sub_y)
            for x in xs
        )
        for y in ys
    )
    return SampledSurface(x_range[0], y_range[0], spacing_x, spacing_y, heights)


def build_offset_grid(
    surface: HeightFunction,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    tool: MachiningParameters,
    *,
    spacing_x: float = 1.0,
    spacing_y: float = 0.5,
    edge_samples_x: int = 3,
    edge_samples_y: int = 1,
) -> OffsetGrid:
    """Sample the surface and offset it for the tool (drop-cutter)."""
    return offset_sampled_surface(
        sample_surface(
            surface,
            x_range,
            y_range,
            spacing_x=spacing_x,
            spacing_y=spacing_y,
            edge_samples_x=edge_samples_x,
            edge_samples_y=edge_samples_y,
        ),
        tool,
    )


def offset_sampled_surface(
    sampled: SampledSurface,
    tool: MachiningParameters,
) -> OffsetGrid:
    """Offset a sampled surface for the tool (drop-cutter).

    For a flat end mill the tip may go no lower than the highest surface
    point under its disc. For a ball nose the sphere must clear every
    surface point: tip = max over the footprint of
    ``z + sqrt(r² - d²) - r``. A node counts as being at the *closest*
    point of its cell to the tool centre, so together with the
    conservative sampling the tool can only hover a little, never gouge.
    """
    radius = tool.tool_radius
    spacing_x, spacing_y = sampled.spacing_x, sampled.spacing_y
    heights = [list(row) for row in sampled.heights]
    y_count = len(heights)
    x_count = len(heights[0])

    ball = tool.tool_tip == "ball"
    span_x = math.ceil((radius + spacing_x / 2.0) / spacing_x)
    span_y = math.ceil((radius + spacing_y / 2.0) / spacing_y)
    offsets: list[tuple[int, int, float]] = []
    for dix in range(-span_x, span_x + 1):
        for diy in range(-span_y, span_y + 1):
            nearest_x = max(0.0, abs(dix) * spacing_x - spacing_x / 2.0)
            nearest_y = max(0.0, abs(diy) * spacing_y - spacing_y / 2.0)
            distance = math.hypot(nearest_x, nearest_y)
            if distance > radius + 1e-9:
                continue
            lift = math.sqrt(max(0.0, radius * radius - distance * distance)) - radius
            offsets.append((dix, diy, lift if ball else 0.0))

    very_low = -1e9
    tips = [[very_low] * x_count for _ in range(y_count)]
    for dix, diy, lift in offsets:
        for iy in range(y_count):
            jy = iy + diy
            if jy < 0 or jy >= y_count:
                continue
            source = heights[jy]
            target = tips[iy]
            if dix >= 0:
                shifted = source[dix:] + [very_low] * dix
            else:
                shifted = [very_low] * (-dix) + source[:dix]
            tips[iy] = [
                max(current, candidate + lift)
                for current, candidate in zip(target, shifted, strict=True)
            ]
    return OffsetGrid(
        sampled.x0,
        sampled.y0,
        spacing_x,
        spacing_y,
        tuple(tuple(row) for row in tips),
    )


def _cell_offsets(spacing: float, samples: int) -> list[float]:
    """Return sample offsets spanning one grid cell, centred on the node."""
    if samples <= 1:
        return [0.0]
    return [
        -spacing / 2.0 + spacing * index / (samples - 1) for index in range(samples)
    ]


def raster_finish(
    name: str,
    grid: OffsetGrid,
    tool: MachiningParameters,
    *,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    step_over: float,
    sample_spacing: float = 1.0,
    tolerance: float = 0.002,
) -> Toolpath:
    """Follow the offset surface with parallel passes along X.

    Passes alternate direction. The link between neighbouring passes is
    a feed move at the higher of the two end heights, since the surface
    in between has already been cut to within a scallop.
    """
    ys = _steps(y_range[0], y_range[1], step_over)
    builder = _builder(name, tool)
    forward = True
    for y in ys:
        xs = _steps(x_range[0], x_range[1], sample_spacing)
        if not forward:
            xs.reverse()
        points = _simplify([(x, grid.tip_at(x, y)) for x in xs], tolerance)
        start_x, start_z = points[0]
        if not builder.positioned:
            builder.rapid_to(start_x, y)
            builder.rapid_down_to(start_z)
            builder.plunge_to(start_z)
        else:
            builder.cut_to(start_x, y, max(builder.z, start_z))
            builder.cut_to(start_x, y, start_z)
        for x, z in points[1:]:
            builder.cut_to(x, y, z)
        forward = not forward
    return builder.build()


def raster_rough(
    name: str,
    grid: OffsetGrid,
    tool: MachiningParameters,
    *,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    step_over: float,
    sample_spacing: float = 1.0,
    tolerance: float = 0.01,
) -> Toolpath:
    """Remove the stock above the offset surface in Z-limited layers.

    Every layer rasters the whole area, cutting where material remains
    between the previous layer and this one and following the surface
    where it is shallower than the layer, so no pass exceeds the tool's
    step-down. The final layer leaves the surface as the flat tool can
    reach it.
    """
    floor = grid.floor()
    if floor >= 0.0:
        raise ToolpathError(f"{name}: the surface is not below the blank top.")
    levels = depth_levels(0.0, -floor, tool.step_down)
    ys = _steps(y_range[0], y_range[1], step_over)
    xs_forward = _steps(x_range[0], x_range[1], sample_spacing)
    builder = _builder(name, tool)
    previous_level = 0.0
    for level in levels:
        forward = True
        for y in ys:
            xs = xs_forward if forward else list(reversed(xs_forward))
            tips = [grid.tip_at(x, y) for x in xs]
            for segment in _segments(xs, tips, previous_level):
                points = _simplify(
                    [(x, max(tip, level)) for x, tip in segment], tolerance
                )
                start_x, start_z = points[0]
                builder.rapid_to(start_x, y)
                builder.rapid_down_to(previous_level)
                builder.plunge_to(start_z)
                for x, z in points[1:]:
                    builder.cut_to(x, y, z)
            forward = not forward
        previous_level = level
    return builder.build()


def _segments(
    xs: list[float],
    tips: list[float],
    previous_level: float,
) -> list[list[tuple[float, float]]]:
    """Split a pass into runs where material remains below ``previous_level``."""
    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for x, tip in zip(xs, tips, strict=True):
        if tip < previous_level - 1e-6:
            current.append((x, tip))
        elif current:
            segments.append(current)
            current = []
    if current:
        segments.append(current)
    return [segment for segment in segments if len(segment) >= 2]


def _steps(start: float, end: float, spacing: float) -> list[float]:
    """Return evenly spaced values from ``start`` to ``end`` inclusive."""
    count = max(1, math.ceil((end - start) / spacing - 1e-9))
    return [start + (end - start) * index / count for index in range(count + 1)]


def _simplify(
    points: list[tuple[float, float]],
    tolerance: float,
) -> list[tuple[float, float]]:
    """Drop points that lie within ``tolerance`` of the chord (Douglas-Peucker)."""
    if len(points) <= 2:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        x1, z1 = points[first]
        x2, z2 = points[last]
        worst = -1.0
        worst_index = -1
        for index in range(first + 1, last):
            x, z = points[index]
            fraction = 0.0 if x2 == x1 else (x - x1) / (x2 - x1)
            deviation = abs(z - (z1 + (z2 - z1) * fraction))
            if deviation > worst:
                worst = deviation
                worst_index = index
        if worst > tolerance:
            keep[worst_index] = True
            stack.append((first, worst_index))
            stack.append((worst_index, last))
    return [point for point, kept in zip(points, keep, strict=True) if kept]


def _builder(name: str, tool: MachiningParameters) -> PathBuilder:
    return PathBuilder(
        name,
        safe_height=tool.safe_height,
        feed_rate=tool.feed_rate,
        plunge_rate=tool.plunge_rate,
    )


def interpolate_rows(
    stations: list[float],
    rows: list[tuple[list[float], list[float]]],
    x: float,
    y: float,
) -> float | None:
    """Interpolate a lofted surface given as rows of ``(ys, zs)`` per station.

    Returns ``None`` when ``x`` is outside the station range or ``y``
    outside both bracketing rows.
    """
    if x < stations[0] - 1e-9 or x > stations[-1] + 1e-9:
        return None
    index = bisect_left(stations, x)
    if index == 0:
        return _row_z(rows[0], y)
    if index >= len(stations):
        return _row_z(rows[-1], y)
    x0, x1 = stations[index - 1], stations[index]
    z0 = _row_z(rows[index - 1], y)
    z1 = _row_z(rows[index], y)
    if z0 is None and z1 is None:
        return None
    if z0 is None:
        return z1
    if z1 is None:
        return z0
    fraction = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
    return z0 + (z1 - z0) * fraction


def _row_z(row: tuple[list[float], list[float]], y: float) -> float | None:
    ys, zs = row
    if y < ys[0] - 1e-9 or y > ys[-1] + 1e-9:
        return None
    index = bisect_left(ys, y)
    if index == 0:
        return zs[0]
    if index >= len(ys):
        return zs[-1]
    y0, y1 = ys[index - 1], ys[index]
    fraction = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
    return zs[index - 1] + (zs[index] - zs[index - 1]) * fraction
