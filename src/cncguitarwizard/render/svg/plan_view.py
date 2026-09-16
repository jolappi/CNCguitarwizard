"""A one-glance plan view of the whole Prototype001 instrument."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from ...geometry.primitives import Point2D

if TYPE_CHECKING:
    from ...presets import Prototype001Geometry


def render_plan_view_svg(geometry: Prototype001Geometry) -> str:
    """Return an SVG of the body, neck, headstock, and every routed feature.

    The drawing uses the model frame seen from the front: X runs from
    the nut toward the tail, +Y is up. Top-face cavities are filled,
    rear cavities are dashed, holes are circles, frets are lines, and
    the inlays are drawn as their own outlines.
    """
    body = geometry.body
    points: list[Point2D] = list(body.outline.points)
    points.extend(geometry.headstock.plan.boundary)
    min_x = min(point.x for point in points) - 15.0
    max_x = max(point.x for point in points) + 15.0
    min_y = min(point.y for point in points) - 15.0
    max_y = max(point.y for point in points) + 15.0
    width = max_x - min_x
    height = max_y - min_y

    def sx(x: float) -> str:
        return f"{x - min_x:.2f}"

    def sy(y: float) -> str:
        return f"{max_y - y:.2f}"

    def path(polygon: Iterable[Point2D], style: str) -> str:
        data = " ".join(
            f"{'M' if index == 0 else 'L'}{sx(point.x)},{sy(point.y)}"
            for index, point in enumerate(polygon)
        )
        return f'<path d="{data} Z" {style}/>'

    def circle(x: float, y: float, radius: float, style: str) -> str:
        return f'<circle cx="{sx(x)}" cy="{sy(y)}" r="{radius:.2f}" {style}/>'

    wood = 'fill="#f1e4c8" stroke="#6b4a1f" stroke-width="0.8"'
    fretboard = 'fill="#3b2a1a" stroke="#1f150c" stroke-width="0.5"'
    pocket = 'fill="#f2c4b3" fill-opacity="0.85" stroke="#7a3a1a" stroke-width="0.5"'
    rear = (
        'fill="#c9b7e6" fill-opacity="0.45" stroke="#5a3a8a" stroke-width="0.6" '
        'stroke-dasharray="3,2"'
    )
    hole = 'fill="#fff" stroke="#222" stroke-width="0.5"'
    fret = 'stroke="#d9c9a8" stroke-width="0.6"'
    inlay = 'fill="#e8e2d0" stroke="none"'

    parts = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width:.2f} {height:.2f}" '
            f'width="{width * 1.2:.0f}" height="{height * 1.2:.0f}">'
        ),
        path(body.outline.points, wood),
        path(geometry.headstock.plan.boundary, wood),
        path(geometry.neck_outline.boundary, wood),
    ]
    parts.append(path(_fretboard_polygon(geometry), fretboard))
    for slot in geometry.fret_layout.slots:
        parts.append(
            f'<line x1="{sx(slot.start.x)}" y1="{sy(slot.start.y)}" '
            f'x2="{sx(slot.end.x)}" y2="{sy(slot.end.y)}" {fret}/>'
        )
    for marker in geometry.inlay_layout.markers:
        parts.append(path(marker.outline, inlay))
    for tuner in geometry.tuner_layout.holes:
        parts.append(circle(tuner.center.x, tuner.center.y, tuner.diameter / 2.0, hole))

    for cavity in body.top_cavities:
        parts.append(path(cavity.outline, pocket))
    for rear_cavity in body.rear_cavities:
        parts.append(path(rear_cavity.cover_recess.outline, rear))
        parts.append(path(rear_cavity.cavity.outline, rear))
    pivot_radius = body.bridge_mounting.pivot_hole_diameter / 2.0
    for pivot in body.bridge_mounting.pivot_holes:
        parts.append(circle(pivot.x, pivot.y, pivot_radius, hole))
    for drilled in body.holes:
        parts.append(
            circle(drilled.center_x, drilled.center_y, drilled.diameter / 2.0, hole)
        )
    jack = body.jack_hole
    parts.append(circle(jack.start_x, jack.start_y, jack.diameter / 2.0, hole))
    parts.append(
        f'<line x1="{sx(min_x + 5.0)}" y1="{sy(0.0)}" '
        f'x2="{sx(max_x - 5.0)}" y2="{sy(0.0)}" '
        'stroke="#999" stroke-width="0.3" stroke-dasharray="4,3"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _fretboard_polygon(geometry: Prototype001Geometry) -> Sequence[Point2D]:
    """Return the fretboard's plan trapezoid from the nut to its end."""
    outline = geometry.neck_outline
    end_x = outline.last_fret_position + geometry.fretboard_surface.end_extension
    half_nut = outline.nut_width / 2.0
    half_end = outline.last_fret_width / 2.0
    return (
        Point2D(0.0, -half_nut),
        Point2D(end_x, -half_end),
        Point2D(end_x, half_end),
        Point2D(0.0, half_nut),
    )
