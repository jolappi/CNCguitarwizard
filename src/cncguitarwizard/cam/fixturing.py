"""Blank sizing and index-pin placement shared by every part."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..geometry.primitives import Point2D, point_in_polygon
from .exceptions import ToolpathError
from .parameters import MachiningParameters
from .planar import disc_fits, distance_to_boundary, polygon_bounds


@dataclass(frozen=True, slots=True)
class StockBounds:
    """The rectangular blank: a part outline's bounding box plus a margin."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @classmethod
    def around(cls, outline: Sequence[Point2D], margin: float) -> StockBounds:
        """Return the blank that leaves ``margin`` of waste around ``outline``."""
        min_x, min_y, max_x, max_y = polygon_bounds(outline)
        return cls(min_x - margin, min_y - margin, max_x + margin, max_y + margin)

    @property
    def length(self) -> float:
        return self.max_x - self.min_x

    @property
    def width(self) -> float:
        return self.max_y - self.min_y


def pin_fits(
    pin: Point2D,
    outline: Sequence[Point2D],
    avoid: Sequence[Sequence[Point2D]],
    parameters: MachiningParameters,
    stock: StockBounds,
) -> bool:
    """Whether a dowel here stays in the waste, clear of every cut and edge.

    The hole must lie outside the part outline with the tool diameter
    plus ``index_pin_wall`` of wood to the profile cut, equally clear of
    every polygon in ``avoid`` (cavities that reach into the waste, areas
    a surfacing pass sweeps), and ``stock_edge_margin`` inside the blank.
    """
    clearance = (
        parameters.index_pin_diameter / 2.0
        + parameters.tool_diameter
        + parameters.index_pin_wall
    )
    edge = parameters.index_pin_diameter / 2.0 + parameters.stock_edge_margin
    if not (
        stock.min_x + edge <= pin.x <= stock.max_x - edge
        and stock.min_y + edge <= pin.y <= stock.max_y - edge
    ):
        return False
    if not disc_fits(pin, outline, clearance, inside=False):
        return False
    for polygon in avoid:
        if point_in_polygon(pin, polygon):
            return False
        if distance_to_boundary(pin, polygon) < clearance:
            return False
    return True


def automatic_index_pins(
    outline: Sequence[Point2D],
    avoid: Sequence[Sequence[Point2D]],
    parameters: MachiningParameters,
    stock: StockBounds,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Place two dowels on the centerline in the blank's waste.

    The centerline ``Y = 0`` is scanned across the blank for runs where a
    dowel fits (see ``pin_fits``). Pin 1 is the middle of the first run
    from the nut end, pin 2 the middle of the last run toward the tail.
    Both lie on the centerline, so flipping the blank about it leaves
    them in place, and neither is inside the finished part.

    Raises:
        ToolpathError: If fewer than two separate runs exist.
    """
    step = 0.5
    runs: list[tuple[float, float]] = []
    x = stock.min_x
    current: float | None = None
    while x <= stock.max_x + 1e-9:
        fits = pin_fits(Point2D(x, 0.0), outline, avoid, parameters, stock)
        if fits and current is None:
            current = x
        elif not fits and current is not None:
            runs.append((current, x - step))
            current = None
        x += step
    if current is not None:
        runs.append((current, stock.max_x))
    runs = [run for run in runs if run[1] - run[0] >= parameters.index_pin_diameter]
    if len(runs) < 2:
        raise ToolpathError(
            "Could not find two waste areas on the centerline for the index "
            "pins; enlarge stock_margin or pass index_pin_positions explicitly."
        )
    first, last = runs[0], runs[-1]
    return (
        ((first[0] + first[1]) / 2.0, 0.0),
        ((last[0] + last[1]) / 2.0, 0.0),
    )


def resolve_index_pins(
    outline: Sequence[Point2D],
    avoid: Sequence[Sequence[Point2D]],
    parameters: MachiningParameters,
    stock: StockBounds,
) -> tuple[tuple[float, float], ...]:
    """Return the explicit pins after checking them, or automatic ones."""
    pins = parameters.index_pin_positions or automatic_index_pins(
        outline, avoid, parameters, stock
    )
    for x, y in pins:
        if not pin_fits(Point2D(x, y), outline, avoid, parameters, stock):
            raise ToolpathError(
                f"Index pin at ({x}, {y}) would end up inside the finished "
                "part, too close to a cut, or outside the blank."
            )
    return tuple((x, y) for x, y in pins)
