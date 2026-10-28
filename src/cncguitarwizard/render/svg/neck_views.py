"""Drawings of the neck and the fretboard, for the web app's own pages.

Each is one SVG of a few views stacked: the part from above, from the
side, and in section, drawn with the colours of the wood, so the shape a
setting gives shows at a glance. The neck from the headstock's tip to
the heel; the fretboard with its frets as cut, its markers and, when
scalloped, its scallops shaded from above and hollowed in the side view.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from ...geometry.fret import FretCalculator
from ...geometry.primitives import Point2D, Point3D
from ...presets import Prototype001Geometry
from .plan_view import _fretboard_polygon, _nut_polygon

WIDTH = 1000.0
"""Every drawing's width, in its own units (the page scales it)."""

MARGIN = 16.0
"""Room round each view, in drawing units."""

WOOD = 'fill="#e9d3a8" stroke="#8a6a3a" stroke-width="0.8"'
IN_BODY = 'fill="#e9d3a8" fill-opacity="0.35" stroke="#8a6a3a" stroke-width="0.5"'
BODY_FRONT = 'stroke="#8a6a3a" stroke-width="0.8" stroke-dasharray="4 3"'
BOARD = 'fill="#3b2a1a" stroke="#1f150c" stroke-width="0.6"'
FRET = 'stroke="#d8d8d8" stroke-width="1.2"'
SLOT = 'stroke="#d8d8d8" stroke-width="0.9"'
INLAY = 'fill="#f4efe2" stroke="#b8b0a0" stroke-width="0.4"'
NUT = 'fill="#f7f3e8" stroke="#8a8070" stroke-width="0.6"'
SCALLOP = 'fill="#6b4e33" fill-opacity="0.9" stroke="none"'
BINDING = 'fill="#efe6d2" stroke="#8a8070" stroke-width="0.4"'
HOLE = 'fill="#fff" stroke="#333" stroke-width="0.6"'
TEXT = 'font-family="sans-serif" font-size="13" fill="#3b332b"'

SIDE_EXAGGERATION = 3.0
"""How much higher than long the side views are drawn: a neck's or a
board's height is small beside its length, and a scallop would not
show."""

SCALLOP_SAMPLES = 6.0
"""Side-view samples per millimetre along a scalloped board."""


class _View:
    """One view: model points onto its band of the drawing.

    Args:
        top: Where its band starts down the drawing.
        x_range: The model's ``(low, high)`` across the drawing.
        v_range: The model's ``(low, high)`` up the drawing.
        v_scale: How much the vertical is stretched against the horizontal.
        width: The band's width.
    """

    def __init__(
        self,
        top: float,
        x_range: tuple[float, float],
        v_range: tuple[float, float],
        v_scale: float = 1.0,
        width: float = WIDTH,
        left: float = 0.0,
    ) -> None:
        self.scale = (width - 2.0 * MARGIN) / (x_range[1] - x_range[0])
        self.v_scale = v_scale
        self.left = left
        self.x_low = x_range[0]
        self.v_high = v_range[1]
        self.top = top
        self.height = (v_range[1] - v_range[0]) * self.scale * v_scale + 2.0 * MARGIN

    def point(self, x: float, v: float) -> str:
        sx = self.left + MARGIN + (x - self.x_low) * self.scale
        sy = self.top + MARGIN + (self.v_high - v) * self.scale * self.v_scale
        return f"{sx:.1f},{sy:.1f}"

    def polygon(
        self, points: Iterable[tuple[float, float]], style: str, title: str
    ) -> str:
        data = " ".join(self.point(x, v) for x, v in points)
        return f'<polygon points="{data}" {style}><title>{title}</title></polygon>'

    def line(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        style: str,
        title: str = "",
    ) -> str:
        (x1, y1), (x2, y2) = (
            map(float, self.point(*a).split(",")),
            map(float, self.point(*b).split(",")),
        )
        start = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {style}'
        return f"{start}><title>{title}</title></line>" if title else f"{start}/>"


def _caption(top: float, text: str, left: float = 0.0) -> str:
    x, y = left + MARGIN, top + 13.0
    return f'<text x="{x:.1f}" y="{y:.1f}" {TEXT}>{_escape(text)}</text>'


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _document(parts: Sequence[str], height: float, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} '
        f'{height:.0f}" role="img" aria-label="{_escape(title)}">'
        + "".join(parts)
        + "</svg>"
    )


def _plan(points: Iterable[Point2D]) -> list[tuple[float, float]]:
    """Points from above: X along the neck, Y up the drawing (the bass
    side down, as the body editor has it)."""
    return [(point.x, point.y) for point in points]


def _nearest_row(rows: Sequence[Sequence[Point3D]], x: float) -> Sequence[Point3D]:
    return min(rows, key=lambda row: abs(row[len(row) // 2].x - x))


def _board_top(geometry: Prototype001Geometry, x: float, y: float = 0.0) -> float:
    """The playing surface's height at ``(x, y)``, a scallop's hollow taken."""
    surface = geometry.fretboard_surface
    row = _nearest_row(surface.mesh.rows, x)
    middle = min(row, key=lambda point: abs(point.y - y))
    scallops = geometry.fretboard_scallops
    return middle.z - (scallops.depth_at(x, y) if scallops is not None else 0.0)


def _board_style(geometry: Prototype001Geometry) -> str:
    """Return how the board is drawn: dark, or in the neck's own wood on a
    one-piece neck."""
    return WOOD if geometry.fretboard_one_piece else BOARD


def _section(
    view: _View,
    row: Sequence[Point3D],
    board: Sequence[Point3D] | None,
    title: str,
    style: str = BOARD,
) -> list[str]:
    """A section across the neck: its back (``row``, below the glue face)
    and the board on it, drawn in ``style`` (a one-piece neck's in its
    wood's)."""
    parts = [
        view.polygon(
            [(p.y, p.z) for p in row] + [(row[-1].y, 0.0), (row[0].y, 0.0)],
            WOOD,
            f"{title}: the neck",
        )
    ]
    if board:
        parts.append(
            view.polygon(
                [(p.y, p.z) for p in board] + [(board[-1].y, 0.0), (board[0].y, 0.0)],
                style,
                f"{title}: the fretboard",
            )
        )
    return parts


def _neck_side(
    geometry: Prototype001Geometry,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Return the neck from the side, nut to heel: its back's depth down
    the middle and the board's top on it, each as (along, height)."""
    rows = [
        row for row in geometry.neck_surface.mesh.rows if row[len(row) // 2].x >= 0.0
    ]
    depths = [(row[len(row) // 2].x, row[len(row) // 2].z) for row in rows]
    heel_end = depths[-1][0]
    stations = [x for x, _ in depths]
    samples = sorted({*stations, *(heel_end * k / 400.0 for k in range(401))})
    tops = [(x, _board_top(geometry, x)) for x in samples if x <= _board_end(geometry)]
    return depths, tops


def _depth_at(depths: Sequence[tuple[float, float]], x: float) -> float:
    """Return the neck's back's height at ``x``, between its stations."""
    for (x1, z1), (x2, z2) in zip(depths, depths[1:], strict=False):
        if x1 <= x <= x2:
            return z1 if x2 == x1 else z1 + (z2 - z1) * (x - x1) / (x2 - x1)
    return depths[-1][1]


def _board_end(geometry: Prototype001Geometry) -> float:
    """Return where the board ends down its middle: its last row's, or the
    heel's end where it is cut back to it."""
    end = geometry.fretboard_surface.station_positions[-1]
    outline = geometry.neck_outline
    return min(end, outline.heel_end_position) if outline.fretboard_to_heel_end else end


def _board_side(
    geometry: Prototype001Geometry,
) -> tuple[float, list[tuple[float, float]]]:
    """Return where the board ends and its top along its middle, as
    (along, height)."""
    end = _board_end(geometry)
    count = int(end * SCALLOP_SAMPLES)
    return end, [
        (end * k / count, _board_top(geometry, end * k / count))
        for k in range(count + 1)
    ]


def _twelfth_row(geometry: Prototype001Geometry) -> Sequence[Point3D]:
    """Return the board's section at the twelfth fret (or its last)."""
    surface = geometry.fretboard_surface
    return surface.profile_row(surface.station_positions[min(12, surface.fret_count)])


def render_neck_svg(
    geometry: Prototype001Geometry, frame_of: Prototype001Geometry | None = None
) -> str:
    """Return the neck from above, from the side and in section.

    From above: the headstock with its tuner holes, the neck to the
    heel, the fretboard, its frets and markers and the nut. From the side
    (its height stretched ``SIDE_EXAGGERATION`` times): the neck's depth
    under the board, the board on it. In section, true to scale: at the
    first fret and the twelfth, the neck's back profile and the board.
    ``frame_of`` sizes every view to another design instead (see
    ``render_plan_view_svg``), so the two lie one over the other.
    """
    frame = frame_of or geometry
    outline = geometry.neck_outline.boundary
    headstock = geometry.headstock.plan.boundary
    every = [*frame.neck_outline.boundary, *frame.headstock.plan.boundary]
    x_range = (min(p.x for p in every), max(p.x for p in every))
    y_reach = max(abs(p.y) for p in every)
    parts: list[str] = []

    top = 0.0
    parts.append(_caption(top, "From above"))
    plan = _View(top + 10.0, x_range, (-y_reach, y_reach))
    parts.append(plan.polygon(_plan(headstock), WOOD, "The headstock"))
    parts.append(plan.polygon(_plan(outline), WOOD, "The neck"))
    parts.append(
        plan.polygon(
            _plan(_fretboard_polygon(geometry)), _board_style(geometry), "The fretboard"
        )
    )
    for slot in geometry.fret_layout.slots:
        parts.append(
            plan.line((slot.start.x, slot.start.y), (slot.end.x, slot.end.y), FRET)
        )
    for marker in geometry.inlay_layout.markers:
        parts.append(
            plan.polygon(
                _plan(marker.outline), INLAY, f"Marker, fret {marker.fret_number}"
            )
        )
    parts.append(plan.polygon(_plan(_nut_polygon(geometry)), NUT, "The nut"))
    for hole in geometry.tuner_layout.holes:
        cx, cy = map(float, plan.point(hole.center.x, hole.center.y).split(","))
        radius = hole.diameter / 2.0 * plan.scale
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" {HOLE}>'
            "<title>Tuner hole</title></circle>"
        )
    top += 10.0 + plan.height

    # From the side: the neck from the nut to the heel.
    depths, tops = _neck_side(geometry)
    heel_end = depths[-1][0]
    frame_depths, frame_tops = _neck_side(frame) if frame_of else (depths, tops)
    v_low = min(z for _, z in frame_depths)
    v_high = max(z for _, z in frame_tops)
    # A neck-through (or one-piece) neck runs on through the body, as deep
    # as the body: the part inside it is drawn paler, so the heel seen is
    # only the ramp down to it ahead of the body.
    through = geometry.neck_through
    body_x = through.front_x if through is not None else None
    if body_x is not None and not 0.0 < body_x < heel_end:
        body_x = None
    caption = f"From the side (height x{SIDE_EXAGGERATION:g})"
    if body_x is not None:
        caption += ", paler inside the body"
    parts.append(_caption(top, caption))
    side = _View(
        top + 10.0, (x_range[0], x_range[1]), (v_low, v_high), SIDE_EXAGGERATION
    )
    if body_x is None:
        parts.append(
            side.polygon(
                depths + [(heel_end, 0.0), (0.0, 0.0)], WOOD, "The neck from the side"
            )
        )
    else:
        cut = (body_x, _depth_at(depths, body_x))
        ahead = [p for p in depths if p[0] < body_x] + [cut]
        inside = [cut] + [p for p in depths if p[0] > body_x]
        parts.append(
            side.polygon(
                ahead + [(body_x, 0.0), (0.0, 0.0)], WOOD, "The neck from the side"
            )
        )
        parts.append(
            side.polygon(
                inside + [(heel_end, 0.0), (body_x, 0.0)],
                IN_BODY,
                "Inside the body: the neck runs on through it, as deep as it",
            )
        )
        parts.append(
            side.line(
                (body_x, v_low), (body_x, v_high), BODY_FRONT, "Where the body begins"
            )
        )
    parts.append(
        side.polygon(
            tops + [(tops[-1][0], 0.0), (tops[0][0], 0.0)],
            _board_style(geometry),
            "The fretboard from the side",
        )
    )
    top += 10.0 + side.height

    # In section at the first and twelfth frets, side by side, true scale.
    positions = geometry.fretboard_surface.station_positions
    half = (WIDTH - MARGIN) / 2.0
    section_parts: list[str] = []
    heights = []
    for index, fret in enumerate((1, 12)):
        x = positions[fret]
        row = _nearest_row(geometry.neck_surface.mesh.rows, x)
        board = geometry.fretboard_surface.profile_row(x)
        frame_row, frame_board = (row, board)
        if frame_of is not None:
            frame_x = frame.fretboard_surface.station_positions[fret]
            frame_row = _nearest_row(frame.neck_surface.mesh.rows, frame_x)
            frame_board = frame.fretboard_surface.profile_row(frame_x)
        reach = max(abs(p.y) for p in (*frame_row, *frame_board)) + 4.0
        low = min(p.z for p in frame_row) - 2.0
        high = max(p.z for p in frame_board) + 2.0
        view = _View(
            top + 10.0,
            (-reach * 2.2, reach * 2.2),
            (low, high),
            width=half,
            left=index * half,
        )
        depth = max(p.z for p in board) - min(p.z for p in row)
        width = max(p.y for p in row) - min(p.y for p in row)
        section_parts.append(
            _caption(
                top, f"At fret {fret}: {width:.1f} wide, {depth:.1f} deep", index * half
            )
        )
        section_parts += _section(
            view, row, board, f"Fret {fret}", _board_style(geometry)
        )
        heights.append(view.height)
    parts += section_parts
    top += 10.0 + max(heights)
    return _document(parts, top, "The neck")


def render_fretboard_svg(
    geometry: Prototype001Geometry, frame_of: Prototype001Geometry | None = None
) -> str:
    """Return the fretboard from above, from the side and in section.

    From above: the board (its binding along its edges), its slots as
    cut (blind ones short of the edges), its markers, the nut, and its
    scallops shaded between their lands. From the side, along its middle
    (its height stretched ``SIDE_EXAGGERATION`` times): its crown, the
    scallops hollowed in it and the slots down into it. In section at the
    twelfth fret, true to scale: its radius. ``frame_of`` sizes every view
    to another design instead (see ``render_plan_view_svg``).
    """
    frame = frame_of or geometry
    surface = geometry.fretboard_surface
    board = _fretboard_polygon(geometry)
    framed = _fretboard_polygon(frame)
    x_range = (min(p.x for p in framed) - 10.0, max(p.x for p in framed) + 4.0)
    y_reach = max(abs(p.y) for p in framed) + 2.0
    layout = geometry.fret_layout
    scallops = geometry.fretboard_scallops
    positions = surface.station_positions
    parts: list[str] = []

    top = 0.0
    title = "From above" + (
        f", scalloped from fret {scallops.from_fret}" if scallops is not None else ""
    )
    parts.append(_caption(top, title))
    plan = _View(top + 10.0, x_range, (-y_reach, y_reach))
    binding = geometry.fretboard_binding_width
    if binding > 0.0:
        parts.append(
            plan.polygon(
                [(p.x, p.y + math.copysign(binding, p.y)) for p in board],
                BINDING,
                "The binding",
            )
        )
    parts.append(plan.polygon(_plan(board), _board_style(geometry), "The fretboard"))
    if scallops is not None:
        half_width = surface.half_width_at

        for number in scallops.fret_numbers:
            start, end = positions[number], positions[number + 1]
            corners = []
            for y_sign, x0 in ((-1.0, start), (1.0, start)):
                half = half_width(x0)
                corners.append(
                    (
                        x0 + surface.skew.at(x0) * y_sign * half + scallops.land,
                        y_sign * half,
                    )
                )
            for y_sign, x1 in ((1.0, end), (-1.0, end)):
                half = half_width(x1)
                corners.append(
                    (
                        x1 + surface.skew.at(x1) * y_sign * half - scallops.land,
                        y_sign * half,
                    )
                )
            parts.append(plan.polygon(corners, SCALLOP, f"Scallop after fret {number}"))
    zero = layout.zero_fret_slot
    named_slots = [
        *(((zero, "Zero fret slot"),) if zero is not None else ()),
        *((slot, f"Fret slot {number}") for number, slot in enumerate(layout.slots, 1)),
    ]
    for slot, name in named_slots:
        cut = layout.cut_slot(slot)
        parts.append(
            plan.line((cut.start.x, cut.start.y), (cut.end.x, cut.end.y), SLOT, name)
        )
    for marker in geometry.inlay_layout.markers:
        parts.append(
            plan.polygon(
                _plan(marker.outline), INLAY, f"Marker, fret {marker.fret_number}"
            )
        )
    parts.append(plan.polygon(_plan(_nut_polygon(geometry)), NUT, "The nut"))
    # The usual marker frets' numbers: on a microtonal board the frets
    # nearest those pitches.
    for semitones in (3, 5, 7, 9, 12, 15, 17, 19, 21, 24):
        fret = FretCalculator.nearest_fret(semitones, surface.frets_per_octave)
        if 1 <= fret <= surface.fret_count:
            middle = (positions[fret - 1] + positions[fret]) / 2.0
            sx, sy = map(float, plan.point(middle, -y_reach).split(","))
            parts.append(
                f'<text x="{sx:.1f}" y="{sy + 13:.1f}" text-anchor="middle" {TEXT}>'
                f"{fret}</text>"
            )
    top += 10.0 + plan.height + 14.0

    # From the side, along the middle: the crown, scallops and slots.
    end, tops = _board_side(geometry)
    v_high = max(z for _, z in (_board_side(frame)[1] if frame_of else tops))
    parts.append(
        _caption(
            top, f"From the side, along its middle (height x{SIDE_EXAGGERATION:g})"
        )
    )
    side = _View(top + 10.0, x_range, (0.0, v_high), SIDE_EXAGGERATION)
    parts.append(
        side.polygon(
            tops + [(end, 0.0), (0.0, 0.0)],
            _board_style(geometry),
            "The fretboard from the side",
        )
    )
    depth = geometry.fret_slot_depth
    for number, slot in enumerate(layout.slots, 1):
        x = (slot.start.x + slot.end.x) / 2.0
        z = _board_top(geometry, x)
        parts.append(
            side.line(
                (x, z), (x, z - depth), SLOT, f"Fret slot {number}, from the side"
            )
        )
    top += 10.0 + side.height

    # In section at the twelfth fret: the radius.
    row = _twelfth_row(geometry)
    frame_row = _twelfth_row(frame) if frame_of else row
    reach = max(abs(p.y) for p in frame_row) + 4.0
    view = _View(
        top + 10.0,
        (-reach * 2.4, reach * 2.4),
        (-1.0, max(p.z for p in frame_row) + 2.0),
        width=WIDTH / 2.0,
    )
    parts.append(_caption(top, f"At fret 12: {surface.radius:g} mm radius"))
    parts.append(
        view.polygon(
            [(p.y, p.z) for p in row] + [(row[-1].y, 0.0), (row[0].y, 0.0)],
            _board_style(geometry),
            "The fretboard at fret 12",
        )
    )
    top += 10.0 + view.height
    return _document(parts, top, "The fretboard")
