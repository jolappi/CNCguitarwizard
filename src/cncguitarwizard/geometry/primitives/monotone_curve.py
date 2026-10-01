"""Smooth curves y(x) through points.

``MonotoneCurve`` never overshoots between its points; ``SmoothCurve``
rounds through them, swinging past them as a drawn outline does.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, field

from ..exceptions import GeometryException


@dataclass(frozen=True, slots=True)
class MonotoneCurve:
    """Piecewise cubic Hermite curve through ``(x, y)`` points (Fritsch–Carlson).

    Between two neighbouring points the curve stays within their two
    ``y`` values, so a drawn edge never bulges past the handles that
    shape it. The first point's slope is zero — a headstock edge leaves
    the nut parallel to the neck — interior slopes are the weighted
    harmonic mean of the neighbouring secants (zero at a local peak or
    dip), and the last point takes its secant.

    Args:
        points: At least two points with strictly increasing ``x``.

    Raises:
        GeometryException: For fewer than two points, non-finite values or
            ``x`` values that do not strictly increase.
    """

    points: tuple[tuple[float, float], ...]
    slopes: tuple[float, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate the points and compute the slope at each one."""
        if len(self.points) < 2:
            raise GeometryException("A curve needs at least two points.")
        if not all(math.isfinite(x) and math.isfinite(y) for x, y in self.points):
            raise GeometryException("Curve points must be finite.")
        xs = [x for x, _ in self.points]
        if any(b <= a for a, b in zip(xs, xs[1:], strict=False)):
            raise GeometryException("Curve points must have increasing x.")
        widths = [b - a for a, b in zip(xs, xs[1:], strict=False)]
        secants = [
            (self.points[i + 1][1] - self.points[i][1]) / widths[i]
            for i in range(len(widths))
        ]
        slopes = [0.0]
        for i in range(1, len(self.points) - 1):
            before, after = secants[i - 1], secants[i]
            if before * after <= 0.0:
                slopes.append(0.0)
                continue
            w1 = 2.0 * widths[i] + widths[i - 1]
            w2 = widths[i] + 2.0 * widths[i - 1]
            slopes.append((w1 + w2) / (w1 / before + w2 / after))
        slopes.append(secants[-1])
        object.__setattr__(self, "slopes", tuple(slopes))

    def value_at(self, x: float) -> float:
        """Return ``y`` at ``x``; outside the points the ends are held flat."""
        xs = [px for px, _ in self.points]
        if x <= xs[0]:
            return self.points[0][1]
        if x >= xs[-1]:
            return self.points[-1][1]
        index = bisect_right(xs, x) - 1
        (x0, y0), (x1, y1) = self.points[index], self.points[index + 1]
        width = x1 - x0
        t = (x - x0) / width
        t2, t3 = t * t, t * t * t
        return (
            (2 * t3 - 3 * t2 + 1) * y0
            + (t3 - 2 * t2 + t) * width * self.slopes[index]
            + (-2 * t3 + 3 * t2) * y1
            + (t3 - t2) * width * self.slopes[index + 1]
        )


@dataclass(frozen=True, slots=True)
class SmoothCurve:
    """Rounded curve y(x) through points (Catmull–Rom tangents).

    Unlike ``MonotoneCurve`` it may swing past its points to round a
    bulge or a hollow through them, as a hand-drawn outline does: every
    interior point's slope is that of the chord between its neighbours.
    The first point's slope is zero (a headstock edge leaves the nut
    parallel to the neck) and the last point takes its secant.

    Args:
        points: At least two points with strictly increasing ``x``.

    Raises:
        GeometryException: For fewer than two points, non-finite values or
            ``x`` values that do not strictly increase.
    """

    points: tuple[tuple[float, float], ...]
    slopes: tuple[float, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate the points and compute the slope at each one."""
        if len(self.points) < 2:
            raise GeometryException("A curve needs at least two points.")
        if not all(math.isfinite(x) and math.isfinite(y) for x, y in self.points):
            raise GeometryException("Curve points must be finite.")
        xs = [x for x, _ in self.points]
        if any(b <= a for a, b in zip(xs, xs[1:], strict=False)):
            raise GeometryException("Curve points must have increasing x.")
        slopes = [0.0]
        for i in range(1, len(self.points) - 1):
            (x0, y0), (x1, y1) = self.points[i - 1], self.points[i + 1]
            slopes.append((y1 - y0) / (x1 - x0))
        (xa, ya), (xb, yb) = self.points[-2], self.points[-1]
        slopes.append((yb - ya) / (xb - xa))
        object.__setattr__(self, "slopes", tuple(slopes))

    def value_at(self, x: float) -> float:
        """Return ``y`` at ``x``; outside the points the ends are held flat."""
        xs = [px for px, _ in self.points]
        if x <= xs[0]:
            return self.points[0][1]
        if x >= xs[-1]:
            return self.points[-1][1]
        index = bisect_right(xs, x) - 1
        (x0, y0), (x1, y1) = self.points[index], self.points[index + 1]
        width = x1 - x0
        t = (x - x0) / width
        t2, t3 = t * t, t * t * t
        return (
            (2 * t3 - 3 * t2 + 1) * y0
            + (t3 - 2 * t2 + t) * width * self.slopes[index]
            + (-2 * t3 + 3 * t2) * y1
            + (t3 - t2) * width * self.slopes[index + 1]
        )
