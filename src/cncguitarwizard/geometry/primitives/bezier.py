"""Cubic Bézier spans: the package's smooth curves as SVG draws them.

A uniform Catmull-Rom span and a cubic Hermite span are both cubics, so
each converts exactly to one cubic Bézier: an outline written to an SVG
file this way has a node at every control point, as the editors do.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..exceptions import GeometryException
from .monotone_curve import SmoothCurve
from .point2d import Point2D

BezierSpan = tuple[Point2D, Point2D, Point2D, Point2D]
"""One cubic Bézier: its start, its two control points and its end."""


def closed_catmull_rom_spans(
    control_points: Sequence[Point2D],
) -> tuple[BezierSpan, ...]:
    """Return ``closed_catmull_rom``'s loop as one Bézier span a point.

    Span ``i`` runs from control point ``i`` to the next, its tangents a
    third of the chords between the neighbours, as the uniform
    Catmull-Rom cubic has them.

    Raises:
        GeometryException: For fewer than three control points.
    """
    count = len(control_points)
    if count < 3:
        raise GeometryException("A closed spline needs at least three control points.")
    spans: list[BezierSpan] = []
    for index in range(count):
        p0 = control_points[index - 1]
        p1 = control_points[index]
        p2 = control_points[(index + 1) % count]
        p3 = control_points[(index + 2) % count]
        spans.append(
            (
                p1,
                Point2D(p1.x + (p2.x - p0.x) / 6.0, p1.y + (p2.y - p0.y) / 6.0),
                Point2D(p2.x - (p3.x - p1.x) / 6.0, p2.y - (p3.y - p1.y) / 6.0),
                p2,
            )
        )
    return tuple(spans)


def smooth_curve_spans(curve: SmoothCurve) -> tuple[BezierSpan, ...]:
    """Return a ``SmoothCurve`` ``y(x)`` as one Bézier span between points.

    Each span is the curve's own cubic Hermite piece: its control points
    a third of the way along in ``x``, on the tangents at its ends.
    """
    spans: list[BezierSpan] = []
    for index in range(len(curve.points) - 1):
        (x0, y0), (x1, y1) = curve.points[index], curve.points[index + 1]
        third = (x1 - x0) / 3.0
        spans.append(
            (
                Point2D(x0, y0),
                Point2D(x0 + third, y0 + curve.slopes[index] * third),
                Point2D(x1 - third, y1 - curve.slopes[index + 1] * third),
                Point2D(x1, y1),
            )
        )
    return tuple(spans)


def hermite_spans(
    points: Sequence[Point2D], tangents: Sequence[tuple[float, float]]
) -> tuple[BezierSpan, ...]:
    """Return the cubic Hermite curve through ``points`` as Bézier spans.

    ``tangents[i]`` is the curve's derivative at ``points[i]`` per unit
    of its span's parameter, as ``HeadstockPlan.tip_outline`` uses them.
    """
    spans: list[BezierSpan] = []
    for index in range(len(points) - 1):
        p0, p1 = points[index], points[index + 1]
        (m0x, m0y), (m1x, m1y) = tangents[index], tangents[index + 1]
        spans.append(
            (
                p0,
                Point2D(p0.x + m0x / 3.0, p0.y + m0y / 3.0),
                Point2D(p1.x - m1x / 3.0, p1.y - m1y / 3.0),
                p1,
            )
        )
    return tuple(spans)


def bezier_point(span: BezierSpan, t: float) -> Point2D:
    """Return the span's point at parameter ``t`` in ``[0, 1]``."""
    a, b, c, d = span
    u = 1.0 - t
    w0, w1, w2, w3 = u * u * u, 3.0 * u * u * t, 3.0 * u * t * t, t * t * t
    return Point2D(
        w0 * a.x + w1 * b.x + w2 * c.x + w3 * d.x,
        w0 * a.y + w1 * b.y + w2 * c.y + w3 * d.y,
    )


def flatten_span(span: BezierSpan, tolerance: float) -> tuple[Point2D, ...]:
    """Return points along the span, its start excluded, its end included.

    The span is halved until its control points lie within ``tolerance``
    of its chord, so the points never stray further than that from it.
    """
    out: list[Point2D] = []
    _flatten(span, tolerance, out, 0)
    return tuple(out)


def _flatten(
    span: BezierSpan, tolerance: float, out: list[Point2D], depth: int
) -> None:
    a, b, c, d = span
    if depth >= 16 or (
        _chord_distance(b, a, d) <= tolerance and _chord_distance(c, a, d) <= tolerance
    ):
        out.append(d)
        return
    ab, bc, cd = _mid(a, b), _mid(b, c), _mid(c, d)
    abc, bcd = _mid(ab, bc), _mid(bc, cd)
    middle = _mid(abc, bcd)
    _flatten((a, ab, abc, middle), tolerance, out, depth + 1)
    _flatten((middle, bcd, cd, d), tolerance, out, depth + 1)


def _mid(a: Point2D, b: Point2D) -> Point2D:
    return Point2D((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def _chord_distance(point: Point2D, a: Point2D, b: Point2D) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return math.hypot(point.x - a.x, point.y - a.y)
    return abs((point.x - a.x) * dy - (point.y - a.y) * dx) / length
