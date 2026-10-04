"""A one-glance plan view of the whole Prototype001 instrument."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from ...geometry.primitives import Point2D

if TYPE_CHECKING:
    from ...presets import Prototype001Geometry


def render_plan_view_svg(geometry: Prototype001Geometry) -> str:
    """Return an SVG of the body, neck, headstock, and every routed feature.

    The drawing is the model seen from the front, standing up: the
    headstock at the top, the model's X (nut toward tail) running down
    the page and +Y to the right — the side view turned a quarter turn
    clockwise, not mirrored. Top-face cavities are filled,
    rear cavities are dashed, holes are circles, frets are lines, and
    the inlays are drawn as their own outlines. The nut is drawn on its
    seat: bone white, or dark for a locking nut; a fretboard that runs on
    under the nut (a slotted nut's, an R2 locking nut's) reaches under it
    and on behind it, a line marking where a slotted nut's board starts
    sloping down to its end.
    """
    body = geometry.body
    points: list[Point2D] = list(body.outline.points)
    points.extend(geometry.headstock.plan.boundary)
    min_x = min(point.x for point in points) - 15.0
    max_x = max(point.x for point in points) + 15.0
    min_y = min(point.y for point in points) - 15.0
    max_y = max(point.y for point in points) + 15.0
    # Portrait: the page is as wide as the instrument and as tall as it
    # is long.
    width = max_y - min_y
    height = max_x - min_x

    def screen(x: float, y: float) -> tuple[str, str]:
        # A quarter turn clockwise of "X right, +Y up": the headstock (at
        # negative X) goes to the top and +Y to the right.
        return f"{y - min_y:.2f}", f"{x - min_x:.2f}"

    def path(polygon: Iterable[Point2D], style: str) -> str:
        data = " ".join(
            f"{'M' if index == 0 else 'L'}{','.join(screen(point.x, point.y))}"
            for index, point in enumerate(polygon)
        )
        return f'<path d="{data} Z" {style}/>'

    def circle(x: float, y: float, radius: float, style: str) -> str:
        cx, cy = screen(x, y)
        return f'<circle cx="{cx}" cy="{cy}" r="{radius:.2f}" {style}/>'

    def line(x1: float, y1: float, x2: float, y2: float, style: str) -> str:
        (ax, ay), (bx, by) = screen(x1, y1), screen(x2, y2)
        return f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" {style}/>'

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
        # A neck-through's block runs on from the neck, a shade darker; its
        # long sides are the glue lines to the wings.
        *(
            (
                path(
                    geometry.neck_through.block.outline,
                    'fill="#e2cc9f" stroke="#6b4a1f" stroke-width="0.6"',
                ),
            )
            if geometry.neck_through is not None
            else ()
        ),
        path(geometry.headstock.plan.boundary, wood),
        path(geometry.neck_outline.boundary, wood),
    ]
    parts.append(path(_fretboard_polygon(geometry), fretboard))
    nut = geometry.locking_nut
    nut_look = (
        'fill="#3c3c3c" stroke="#111" stroke-width="0.5"'
        if nut is not None and nut.is_locking
        else 'fill="#efe8d6" stroke="#8a7a5a" stroke-width="0.5"'
    )
    parts.append(path(_nut_polygon(geometry), nut_look))
    if nut is not None and not nut.is_locking and nut.spec.taper > 0.0:
        # Where the board behind a slotted nut starts sloping down.
        back = nut.spec.set_back + nut.spec.depth + nut.spec.lip
        half = nut.neck_width / 2.0
        parts.append(
            line(
                -nut.lean * half - back,
                -half,
                nut.lean * half - back,
                half,
                'stroke="#7a6040" stroke-width="0.4"',
            )
        )
    zero = geometry.fret_layout.zero_fret_slot
    for slot in (*((zero,) if zero is not None else ()), *geometry.fret_layout.slots):
        parts.append(line(slot.start.x, slot.start.y, slot.end.x, slot.end.y, fret))
    for marker in geometry.inlay_layout.markers:
        parts.append(path(marker.outline, inlay))
    for tuner in geometry.tuner_layout.holes:
        parts.append(circle(tuner.center.x, tuner.center.y, tuner.diameter / 2.0, hole))
    # A headstock-adjusted truss rod's trough shows in the headstock face.
    truss = geometry.truss_rod_channel
    if truss.adjustment_side == "nut" and truss.adjuster_boundary:
        parts.append(path(truss.adjuster_boundary, pocket))

    # A carved top's plateau, dashed: the top falls outside it.
    if body.carved_top is not None:
        parts.append(
            path(
                body.carved_top.plateau,
                'fill="none" stroke="#8a6a3a" stroke-width="0.6" '
                'stroke-dasharray="5,3"',
            )
        )
    # Arm contour (top) and belly cut (back), under the cavities.
    for contour in body.contours:
        look = (
            'fill="#9cc79a" fill-opacity="0.45" stroke="#3d6b3a" stroke-width="0.4"'
            if contour.face == "top"
            else 'fill="#9aa9d6" fill-opacity="0.35" stroke="#34457a" '
            'stroke-width="0.4" stroke-dasharray="3,2"'
        )
        parts.append(path(contour.region(), look))
    for cavity in body.top_cavities:
        parts.append(path(cavity.outline, pocket))
    for rear_cavity in body.rear_cavities:
        parts.append(path(rear_cavity.cover_recess.outline, rear))
        for rear_pocket in rear_cavity.pockets:
            parts.append(path(rear_pocket.outline, rear))
    pivot_radius = body.bridge_mounting.pivot_hole_diameter / 2.0
    for pivot in body.bridge_mounting.pivot_holes:
        parts.append(circle(pivot.x, pivot.y, pivot_radius, hole))
    for drilled in (*body.holes, *body.control_top_marks):
        parts.append(
            circle(drilled.center_x, drilled.center_y, drilled.diameter / 2.0, hole)
        )
    rear_hole = (
        'fill="#fff" fill-opacity="0.6" stroke="#5a3a8a" stroke-width="0.5" '
        'stroke-dasharray="2,1.5"'
    )
    for drilled in (*body.rear_holes, *body.control_back_marks):
        parts.append(
            circle(
                drilled.center_x, drilled.center_y, drilled.diameter / 2.0, rear_hole
            )
        )
    jack = body.jack_hole
    parts.append(circle(jack.start_x, jack.start_y, jack.diameter / 2.0, hole))
    parts.append(
        line(
            min_x + 5.0,
            0.0,
            max_x - 5.0,
            0.0,
            'stroke="#999" stroke-width="0.3" stroke-dasharray="4,3"',
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _fretboard_polygon(geometry: Prototype001Geometry) -> Sequence[Point2D]:
    """Return the fretboard's plan outline from the nut to its end.

    Taken from the surface's end rows, so slanted frets slant both ends.
    A board that runs on under the nut reaches the nut's seat further back.
    """
    rows = geometry.fretboard_surface.mesh.rows
    first, last = rows[0], rows[-1]
    nut = geometry.locking_nut
    back = nut.seat_length if nut is not None and nut.on_fretboard else 0.0
    return (
        Point2D(first[0].x - back, first[0].y),
        Point2D(last[0].x, last[0].y),
        Point2D(last[-1].x, last[-1].y),
        Point2D(first[-1].x - back, first[-1].y),
    )


def _nut_polygon(geometry: Prototype001Geometry) -> Sequence[Point2D]:
    """Return the nut in plan, its front face on the (leaning) nut line.

    A locking or slotted nut is as deep as it is; a plain nut fills its
    shelf. A locking nut is its own width, any other the neck's.
    """
    headstock = geometry.headstock
    nut = geometry.locking_nut
    half = (
        nut.spec.width
        if nut is not None and nut.is_locking
        else headstock.plan.nut_width
    ) / 2.0
    depth = nut.spec.depth if nut is not None else headstock.nut_seat_length
    # Behind a zero fret the nut stands back from the nut line.
    front = nut.front if nut is not None else 0.0
    lean = headstock.nut_lean
    return tuple(
        Point2D(lean * y + dx, y)
        for dx, y in (
            (front, -half),
            (front, half),
            (front - depth, half),
            (front - depth, -half),
        )
    )
