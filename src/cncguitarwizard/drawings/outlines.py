"""The editors' outlines as Bézier spans, a node at every handle."""

from __future__ import annotations

from ..geometry.neck.headstock import HeadstockPlan
from ..geometry.primitives import (
    BezierSpan,
    Point2D,
    SmoothCurve,
    hermite_spans,
    smooth_curve_spans,
)


def headstock_spans(plan: HeadstockPlan) -> tuple[BezierSpan, ...]:
    """Return a drawn headstock's outline, closed along the nut line.

    The bass edge from the nut to the tip, the tip (its own curve, a
    straight cut, or nothing for a pointed tip), the treble edge back to
    the nut, and the nut line back to the start; in the model frame.
    """
    assert plan.bass_edge is not None and plan.treble_edge is not None

    def edge(curve: SmoothCurve, y_sign: float) -> list[BezierSpan]:
        spans = smooth_curve_spans(curve)
        return [
            (
                Point2D(-a.x, y_sign * a.y),
                Point2D(-b.x, y_sign * b.y),
                Point2D(-c.x, y_sign * c.y),
                Point2D(-d.x, y_sign * d.y),
            )
            for a, b, c, d in spans
        ]

    bass = edge(plan.edge_curve("bass"), plan.bass_sign)
    treble = edge(plan.edge_curve("treble"), -plan.bass_sign)
    if plan.pointed:
        tip: list[BezierSpan] = []
    else:
        points, leaving, arriving = plan.tip_curve()
        tip = (
            list(hermite_spans(points, leaving, arriving))
            if leaving
            else [(points[0], points[0], points[1], points[1])]
        )
        # The tip runs -Y to +Y; the outline goes bass corner first.
        if plan.bass_sign > 0:
            tip = [(d, c, b, a) for a, b, c, d in reversed(tip)]
    back = [(d, c, b, a) for a, b, c, d in reversed(treble)]
    end, start = back[-1][3], bass[0][0]
    return (*bass, *tip, *back, (end, end, start, start))
