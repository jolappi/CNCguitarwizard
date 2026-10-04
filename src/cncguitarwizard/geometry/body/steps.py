"""A stepped top: the top lowered in bands that follow the body's edge.

Each step has a boundary, a closed line on the top: inside the innermost
the top keeps its full height, and every band nearer the edge lies one
``step`` lower than the band inside it — the ESP LTD Alexi Hexed's
graphic (its pinstripes nested along the edge) made into levels. The
boundaries are the outline taken in by ``body_top_step_insets``, or drawn
(``YourDesignShape.step_points``): straight lines between points, so a
step can run straight across where the edge curves (the Hexed's tail).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, point_in_polygon


@dataclass(frozen=True, slots=True)
class SteppedTop:
    """The top in levels, each band nearer the edge a step lower.

    Args:
        boundaries: Each step's boundary, the outermost first, each
            inside the one before it.
        step: How much lower each band lies than the one inside it.

    Raises:
        BodyGeometryError: For no boundary, one of under three points, a
            boundary not inside the one before it, or a step that is not
            positive.
    """

    boundaries: tuple[tuple[Point2D, ...], ...]
    step: float

    def __post_init__(self) -> None:
        if not self.boundaries:
            raise BodyGeometryError("A stepped top needs at least one step.")
        if not math.isfinite(self.step) or self.step <= 0.0:
            raise BodyGeometryError("body_top_step_height must be positive.")
        for index, boundary in enumerate(self.boundaries, start=1):
            if len(boundary) < 3:
                raise BodyGeometryError(
                    f"The stepped top's step {index} leaves nothing of the body "
                    "inside it: make body_top_step_insets smaller, or draw it "
                    "with three points or more."
                )

    def check_nested(self, ignore: Callable[[Point2D], bool] | None = None) -> None:
        """Refuse a step not wholly inside the one nearer the edge.

        Each step's points must lie inside the one before, none of that
        one's inside it, and no two of their lines cross — quick for drawn
        steps (a few points); the steps taken in from the edge are nested
        by how they are made. A point (or crossing) ``ignore`` accepts does
        not count: off the body, in the neck pocket or right by the edge,
        where the lines may meet (the Alexi Hexed's converge on the edge
        beside the neck).

        Raises:
            BodyGeometryError: For steps that cross or are not nested.
        """

        def counts(point: Point2D) -> bool:
            return ignore is None or not ignore(point)

        for index, (outer, inner) in enumerate(
            zip(self.boundaries, self.boundaries[1:], strict=False), start=2
        ):
            if (
                any(
                    counts(point) and not point_in_polygon(point, outer)
                    for point in inner
                )
                or any(
                    counts(point) and point_in_polygon(point, inner) for point in outer
                )
                or any(counts(point) for point in _crossings(outer, inner))
            ):
                raise BodyGeometryError(
                    f"The stepped top's step {index} must lie inside step "
                    f"{index - 1}, the one nearer the edge, without crossing it."
                )

    @property
    def depth(self) -> float:
        """Return how far the band at the edge lies below the full height."""
        return self.step * len(self.boundaries)

    def drop_at(self, x: float, y: float) -> float:
        """Return how far the top lies below its full height at ``(x, y)``.

        The deepest band whose boundary the point is outside: a step down
        for each boundary it is outside, where they nest (off the body,
        where drawn lines meet, as deep as any cut there).
        """
        point = Point2D(x, y)
        return max(
            (
                depth
                for boundary, depth in self.bands()
                if not point_in_polygon(point, boundary)
            ),
            default=0.0,
        )

    def bands(self) -> tuple[tuple[tuple[Point2D, ...], float], ...]:
        """Return each step's boundary with the depth outside it.

        Everything outside a boundary (and inside the outline) is cut at
        least that deep: the innermost boundary one step, the outermost
        all of them.
        """
        count = len(self.boundaries)
        return tuple(
            (boundary, self.step * (count - index))
            for index, boundary in enumerate(self.boundaries)
        )


def _crossings(
    first: tuple[Point2D, ...], second: tuple[Point2D, ...]
) -> list[Point2D]:
    """Return where the sides of one closed polygon cross the other's."""

    def turn(a: Point2D, b: Point2D, c: Point2D) -> float:
        return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)

    found: list[Point2D] = []
    for a, b in zip(first, (*first[1:], first[0]), strict=True):
        for c, d in zip(second, (*second[1:], second[0]), strict=True):
            ta, tb = turn(c, d, a), turn(c, d, b)
            if (turn(a, b, c) > 0.0) != (turn(a, b, d) > 0.0) and (ta > 0.0) != (
                tb > 0.0
            ):
                t = ta / (ta - tb)
                found.append(Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
    return found
