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


def _pin_clearance(parameters: MachiningParameters) -> float:
    """Return how far a dowel's centre stays from the part and every cut."""
    return (
        parameters.pin_diameter / 2.0
        + parameters.tool_diameter
        + parameters.index_pin_wall
    )


def _pin_edge(parameters: MachiningParameters) -> float:
    """Return how far a dowel's centre stays inside the blank's edge."""
    return parameters.pin_diameter / 2.0 + parameters.stock_edge_margin


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
    clearance = _pin_clearance(parameters)
    edge = _pin_edge(parameters)
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
    axis_y: float = 0.0,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Place two dowels on the centerline in the blank's waste.

    The centerline ``Y = 0`` (or the line ``Y = axis_y``, for a part off
    it such as a neck-through body's wing) is scanned across the blank for runs where a
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
        fits = pin_fits(Point2D(x, axis_y), outline, avoid, parameters, stock)
        if fits and current is None:
            current = x
        elif not fits and current is not None:
            runs.append((current, x - step))
            current = None
        x += step
    if current is not None:
        runs.append((current, stock.max_x))
    runs = [run for run in runs if run[1] - run[0] >= parameters.pin_diameter]
    if len(runs) < 2:
        raise ToolpathError(
            "Could not find two waste areas on the centerline for the index "
            "pins; enlarge stock_margin or pass index_pin_positions explicitly."
        )
    first, last = runs[0], runs[-1]
    return (
        ((first[0] + first[1]) / 2.0, axis_y),
        ((last[0] + last[1]) / 2.0, axis_y),
    )


def resolve_index_pins(
    outline: Sequence[Point2D],
    avoid: Sequence[Sequence[Point2D]],
    parameters: MachiningParameters,
    stock: StockBounds,
    axis_y: float = 0.0,
) -> tuple[tuple[tuple[float, float], ...], StockBounds]:
    """Return the pins and the blank they sit in (on ``Y = axis_y``).

    Explicit ``index_pin_positions`` are checked as given. Otherwise the
    pins are placed automatically; when the blank's ``stock_margin`` has
    no room for a dowel beyond an end of the part (a body without a tail
    notch on the centerline, or a neck pocket running out past the body's
    face), the blank is lengthened until a dowel fits past the furthest of
    the part and the cuts in ``avoid`` — at the front end alone, else the
    back end alone, else both — and the search is repeated, so the
    returned blank may be longer than ``StockBounds.around`` gave.

    Raises:
        ToolpathError: If the dowels are narrower than the tool that
            drills their holes, or no place for them is found.
    """
    if parameters.pin_diameter < parameters.tool_diameter - 1e-6:
        raise ToolpathError(
            f"The {parameters.pin_diameter:g} mm index pins are narrower than "
            f"the {parameters.tool_diameter:g} mm tool that drills their "
            "holes: set index_pin_diameter to dowels at least as wide, or "
            "leave it empty for dowels as wide as the tool."
        )
    if parameters.index_pin_positions:
        pins: tuple[tuple[float, float], ...] = tuple(
            (x, y) for x, y in parameters.index_pin_positions
        )
    else:
        try:
            pins = automatic_index_pins(outline, avoid, parameters, stock, axis_y)
        except ToolpathError:
            # Room for a whole dowel (and a step of the scan) between the
            # cuts' clearance and the blank's edge margin, at each end.
            reach = (
                _pin_clearance(parameters)
                + _pin_edge(parameters)
                + parameters.pin_diameter
                + 1.0
            )
            ends = [polygon_bounds(outline), *(polygon_bounds(a) for a in avoid)]
            front = min(stock.min_x, min(b[0] for b in ends) - reach)
            back = max(stock.max_x, max(b[2] for b in ends) + reach)
            # The least wood first: the front end alone, the back end
            # alone, then both.
            candidates = (
                StockBounds(front, stock.min_y, stock.max_x, stock.max_y),
                StockBounds(stock.min_x, stock.min_y, back, stock.max_y),
                StockBounds(front, stock.min_y, back, stock.max_y),
            )
            for grown in candidates:
                try:
                    pins = automatic_index_pins(
                        outline, avoid, parameters, grown, axis_y
                    )
                except ToolpathError:
                    if grown is candidates[-1]:
                        raise
                    continue
                stock = grown
                break
    for x, y in pins:
        if not pin_fits(Point2D(x, y), outline, avoid, parameters, stock):
            raise ToolpathError(
                f"Index pin at ({x}, {y}) would end up inside the finished "
                "part, too close to a cut, or outside the blank."
            )
    return pins, stock
