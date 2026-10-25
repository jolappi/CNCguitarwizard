"""A quick 3D model of the guitar: triangle meshes to turn and look at.

Not the build's model (FreeCAD's, exact, minutes to make, if it makes it
at all): the surfaces the design already holds, sampled, in a second or
two — to try a change and see it at once.

* The neck, headstock included, is the loft's own rows (the back as
  FreeCAD lofts it, round into the heel and the headstock), closed across
  their top edges and at both ends.
* The fretboard is its radiused surface's rows, closed down to its flat
  underside.
* The body is its top and its back sampled on a grid (``spacing`` apart)
  as heights: the top lowered by a carve, the contours, the roundover and
  the routes from the top, the back raised by its contours, roundover
  and rear routes; the grid's points just outside the outline are moved
  onto it, so the edge is the outline's, and walls join top and back
  round the edge and round every route cut through.

The neck and the fretboard are tilted back onto the body as the build
tilts them (``Prototype001Geometry.neck_tilt``).

Holes, the truss-rod channel and the wiring are left out. The hardware is
in detail sets of its own (``DETAILS``, ``detail_parts``), each drawn or
not: frets, markers and the nut; tuners; pickguard, pickups and knobs;
bridge and strings — each in typical sizes, to look right, not to build
from.
"""

from __future__ import annotations

import math
import sys
from array import array
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..exceptions import ValidationError
from ..geometry.primitives import Point2D, Point3D, point_in_polygon

if TYPE_CHECKING:
    from ..geometry.body import BodySolid
    from ..geometry.fretboard import FretboardSurface
    from ..geometry.neck import HeadstockSolid
    from ..geometry.primitives import Line2D
    from ..presets.prototype001 import Prototype001Geometry, Prototype001Parameters

PREVIEW_SPACING = 2.0
"""The body's sampling grid, in mm."""

_THROUGH = 0.05
"""How thin, in mm, the body (or a separate top) may be at a point and
still be drawn there."""

PREVIEW_COLOURS = {
    "Body": "#c9a26b",
    "Top": "#ead9ae",
    "Neck": "#e7cc93",
    "Fretboard": "#4a2c1d",
    "Frets": "#cfd0cb",
    "Markers": "#f4f0e6",
    "Nut": "#efe6cf",
    "Tuners": "#b9bdc1",
    "Pickguard": "#f3f0e9",
    "Pickups": "#2c2a27",
    "Knobs": "#e2d8c0",
    "Bridge": "#b4b8bc",
    "Strings": "#9a9a96",
}
"""Each part's colour in the viewer."""

DETAILS = {
    "neck": "Frets, position markers and the nut",
    "headstock": "Tuners",
    "body": "Pickguard, pickups and knobs",
    "bridge": "Bridge and strings",
}
"""The detail sets ``detail_parts`` makes, each drawn or not: each takes a
little longer to make."""

# The hardware's sizes, typical ones (the design does not hold them).
_FRET_CROWN = 2.6
"""A fret's crown width."""
_MARKER_SPACING = 0.75
"""The markers' sampling grid (the board's radius followed across)."""
_NUT_OVER_FRETS = 0.5
"""How far the strings sit over the frets at the nut."""
_ACTION_AT_SADDLES = 3.0
"""How far the strings sit over the frets' plane at the saddles (twice
the action at the twelfth fret, less what they sit over them at the nut)."""
_POST_HEIGHT = 17.0
"""A tuner post's height over the headstock face."""
_WIND_HEIGHT = 5.0
"""How high on its post a string is wound."""
_PICKUP_RISE = 6.0
"""A pickup's top over the pickguard (or the top, without one)."""
_KNOB = (12.5, 11.0, 17.0)
"""A knob's radius at its foot and at its top, and its height."""


@dataclass(frozen=True, slots=True)
class PreviewPart:
    """One part of the quick model, a closed triangle mesh.

    Args:
        name: E.g. ``"Body"``.
        colour: Its colour, ``"#rrggbb"``.
        positions: Its vertices, ``x, y, z`` each, in mm in the model frame.
        triangles: Three vertex indices a triangle, anticlockwise seen from
            outside.
    """

    name: str
    colour: str
    positions: tuple[float, ...]
    triangles: tuple[int, ...]

    def float32(self) -> bytes:
        """Return the positions as little-endian 32-bit floats."""
        return _little_endian(array("f", self.positions))

    def uint32(self) -> bytes:
        """Return the triangles as little-endian 32-bit indices."""
        return _little_endian(array("I", self.triangles))


def preview_parts(
    geometry: Prototype001Geometry,
    neck_rows: Sequence[Sequence[Point3D]],
    spacing: float = PREVIEW_SPACING,
) -> tuple[PreviewPart, ...]:
    """Return the quick model's parts: body, neck and fretboard, and a
    separate top (``Top``, the body then its core).

    Args:
        geometry: The built design.
        neck_rows: The neck's loft rows, headstock to heel end, each across
            the back from one top edge to the other
            (``FreeCADScriptExporter.neck_loft_rows``).
        spacing: The body's sampling grid, in mm.

    Returns:
        The parts, each a closed mesh.
    """
    tilt = _Tilt(*geometry.neck_tilt)
    board = geometry.fretboard_surface.mesh.rows
    body = _body_pieces(geometry.body, spacing)
    parts = [
        _part("Body", body[:1]),
        _part("Neck", [tilt.piece(_rows_piece(neck_rows))]),
        _part(
            "Fretboard",
            [tilt.piece(_rows_piece([_down_to_glue(row) for row in board]))],
        ),
    ]
    if len(body) > 1:
        parts.append(_part("Top", body[1:]))
    return tuple(parts)


def detail_parts(
    geometry: Prototype001Geometry,
    parameters: Prototype001Parameters,
    detail: str,
) -> tuple[PreviewPart, ...]:
    """Return one detail set's parts: those of it the design has.

    Args:
        geometry: The built design.
        parameters: Its parameters (the strings' spacing, the frets' height,
            the nut's thickness).
        detail: A key of ``DETAILS``.

    Returns:
        The parts, each a closed mesh; none for what the design has not
        (a pickguard, markers).

    Raises:
        ValidationError: For a detail not in ``DETAILS``.
    """
    makers = {
        "neck": _neck_details,
        "headstock": _headstock_details,
        "body": _body_details,
        "bridge": _bridge_details,
    }
    if detail not in makers:
        raise ValidationError(
            f"No quick model detail {detail!r}: one of {', '.join(DETAILS)}."
        )
    pieces = makers[detail](geometry, parameters)
    return tuple(_part(name, found) for name, found in pieces.items() if found)


def stl_bytes(parts: Sequence[PreviewPart]) -> bytes:
    """Return the parts as one binary STL, in mm."""
    out = bytearray(b"cncguitarwizard quick model".ljust(80, b" "))
    triangles = []
    for part in parts:
        p = part.positions
        for index in range(0, len(part.triangles), 3):
            corners = [
                (p[3 * v], p[3 * v + 1], p[3 * v + 2])
                for v in part.triangles[index : index + 3]
            ]
            triangles.append(corners)
    out += array("I", [len(triangles)]).tobytes()
    for a, b, c in triangles:
        normal = _unit(_cross(_minus(b, a), _minus(c, a)))
        out += _little_endian(array("f", [*normal, *a, *b, *c]))
        out += b"\0\0"
    return bytes(out)


Vector = tuple[float, ...]

_Piece = tuple[list[float], list[int]]
"""A closed mesh's positions and triangles, one solid of a part."""


@dataclass(frozen=True, slots=True)
class _Tilt:
    """The neck tilted back onto the body, as the build tilts it: turned
    ``angle`` degrees about the line across at ``pivot_x``, ``pivot_z``,
    its nut end going down (``Prototype001Geometry.neck_tilt``)."""

    angle: float
    pivot_x: float
    pivot_z: float

    def __call__(self, x: float, y: float, z: float) -> Vector:
        if self.angle == 0.0:
            return (x, y, z)
        turn = math.radians(self.angle)
        dx, dz = x - self.pivot_x, z - self.pivot_z
        return (
            self.pivot_x + dx * math.cos(turn) - dz * math.sin(turn),
            y,
            self.pivot_z + dx * math.sin(turn) + dz * math.cos(turn),
        )

    def piece(self, piece: _Piece) -> _Piece:
        """Return ``piece`` tilted."""
        positions, triangles = piece
        if self.angle == 0.0:
            return piece
        tilted: list[float] = []
        for index in range(0, len(positions), 3):
            tilted += self(*positions[index : index + 3])
        return tilted, triangles


# ---- the neck and the fretboard: closed rows ---------------------------------


def _down_to_glue(row: Sequence[Point3D]) -> list[Point3D]:
    """Return a fretboard row with its sides run down to the glue face."""
    first, last = row[0], row[-1]
    return [Point3D(first.x, first.y, 0.0), *row, Point3D(last.x, last.y, 0.0)]


def _rows_piece(rows: Sequence[Sequence[Point3D]]) -> _Piece:
    """Return a solid through ``rows`` (each across it, as many points
    each), closed between each row's two ends and at both end rows."""
    count = len(rows[0])
    positions = [
        c for row in rows for point in row for c in (point.x, point.y, point.z)
    ]
    triangles: list[int] = []

    def at(i: int, k: int) -> int:
        return i * count + k

    for i in range(len(rows) - 1):
        for k in range(count - 1):
            a, b, c, d = at(i, k), at(i, k + 1), at(i + 1, k + 1), at(i + 1, k)
            triangles += (a, b, c, a, c, d)
        # Across between the row's ends.
        left, right = at(i, 0), at(i, count - 1)
        next_left, next_right = at(i + 1, 0), at(i + 1, count - 1)
        triangles += (left, next_left, next_right, left, next_right, right)
    for i, flip in ((0, True), (len(rows) - 1, False)):
        loop = [at(i, k) for k in range(count)]
        if flip:
            loop.reverse()
        triangles += _cap(positions, loop)
    return positions, triangles


def _cap(positions: list[float], loop: list[int]) -> list[int]:
    """Return a fan of triangles over ``loop`` (a row closed by its ends),
    from its middle."""
    xs = [positions[3 * v] for v in loop]
    ys = [positions[3 * v + 1] for v in loop]
    zs = [positions[3 * v + 2] for v in loop]
    centre = len(positions) // 3
    positions += (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))
    triangles: list[int] = []
    for a, b in zip(loop, (*loop[1:], loop[0]), strict=True):
        triangles += (centre, a, b)
    return triangles


# ---- the body: heights on a grid ----------------------------------------------


def _body_pieces(body: BodySolid, spacing: float) -> list[_Piece]:
    """Return the body, or with a separate top the core and the cap."""
    outline = body.outline.points
    edge = _SegmentIndex(body.edge_points)
    x0, y0, columns, rows = _grid(outline, spacing)

    def point(i: int, j: int) -> Point2D:
        return Point2D(x0 + i * spacing, y0 + j * spacing)

    inside = _fill(outline, x0, y0, spacing, columns, rows)
    through = _filled(
        [cavity.outline for cavity in body.through_cavities],
        x0,
        y0,
        spacing,
        columns,
        rows,
    )
    # Routes from the top and from the back: the depth each cuts to.
    top_routes = _route_depths(
        [
            (cavity.outline, cavity.depth)
            for cavity in body.top_cavities
            if cavity not in body.through_cavities
        ],
        x0,
        y0,
        spacing,
        columns,
        rows,
    )
    rear = [
        (pocket.outline, pocket.depth)
        for cavity in body.rear_cavities
        for pocket in (*cavity.pockets, cavity.cover_recess)
    ]
    back_routes = _route_depths(rear, x0, y0, spacing, columns, rows)
    # Each contour asked only within its own region's box (asking is a
    # search along its edge).
    boxed = []
    for contour in body.contours:
        region = contour.region(outline)
        xs_, ys_ = [p.x for p in region], [p.y for p in region]
        box = (min(xs_) - spacing, min(ys_) - spacing, max(xs_) + spacing)
        boxed.append((contour, (*box, max(ys_) + spacing)))
    top_edge, back_edge = body.top_edge, body.back_edge
    reach = max(top_edge.radius, back_edge.radius)

    def contour_depth(face: str, at: Point2D) -> float:
        deepest = 0.0
        for contour, (low_x, low_y, high_x, high_y) in boxed:
            if (
                contour.face == face
                and low_x <= at.x <= high_x
                and low_y <= at.y <= high_y
            ):
                deepest = max(deepest, contour.depth_at(at))
        return deepest

    def heights(at: Point2D, edge_distance: float) -> tuple[float, float]:
        """The top's depth below Z 0 and the back's height above its face."""
        top = body.top_drop_at(at.x, at.y) + contour_depth("top", at)
        if edge_distance < top_edge.radius and top_edge.rounds_at(at):
            top += _round_drop(top_edge.radius, edge_distance)
        back = contour_depth("back", at)
        if edge_distance < back_edge.radius and back_edge.rounds_at(at):
            back += _round_drop(back_edge.radius, edge_distance)
        return top, back

    core_routes = _route_depths(
        [(cavity.outline, cavity.depth) for cavity in body.core_cavities],
        x0,
        y0,
        spacing,
        columns,
        rows,
    )
    # Each grid point's place: inside, or just outside and moved onto the
    # edge; its top and back heights.
    faces: dict[tuple[int, int], tuple[Point2D, float, float]] = {}
    for j in range(rows):
        for i in range(columns):
            if through[j][i]:
                continue
            if inside[j][i]:
                at = point(i, j)
                top, back = heights(at, edge.distance(at, reach))
                route = top_routes[j][i]
                rear_route = back_routes[j][i]
                faces[(i, j)] = (
                    at,
                    -max(top, route),
                    -body.thickness + max(back, rear_route),
                )
            elif _next_to(inside, i, j):
                at = edge.nearest(point(i, j))
                top, back = heights(at, 0.0)
                faces[(i, j)] = (at, -top, -body.thickness + back)
    if body.cap_thickness == 0.0:
        return [_grid_piece(faces, columns, rows)]
    # A separate top: the core up to the cap's underside (lower where a
    # route reaches into it, and its own routes down from there), the cap
    # over it; either left out where a route goes clean through it.
    split = -body.cap_thickness
    core: dict[tuple[int, int], tuple[Point2D, float, float]] = {}
    cap: dict[tuple[int, int], tuple[Point2D, float, float]] = {}
    for (i, j), (at, top, back) in faces.items():
        floor = min(split, top, split - core_routes[j][i])
        if floor - back > _THROUGH:
            core[(i, j)] = (at, floor, back)
        if top - max(split, back) > _THROUGH:
            cap[(i, j)] = (at, top, max(split, back))
    return [_grid_piece(core, columns, rows), _grid_piece(cap, columns, rows)]


def _plate_piece(
    outline: Sequence[Point2D],
    spacing: float,
    bottom: Callable[[Point2D], float],
    top: Callable[[Point2D], float],
) -> _Piece:
    """Return a solid over ``outline`` from ``bottom`` up to ``top`` (each a
    height at a point), sampled ``spacing`` apart, its edge the outline's."""
    edge = _SegmentIndex(outline)
    x0, y0, columns, rows = _grid(outline, spacing)
    inside = _fill(outline, x0, y0, spacing, columns, rows)
    places: dict[tuple[int, int], tuple[Point2D, float, float]] = {}
    for j in range(rows):
        for i in range(columns):
            at = Point2D(x0 + i * spacing, y0 + j * spacing)
            if not inside[j][i]:
                if not _next_to(inside, i, j):
                    continue
                at = edge.nearest(at)
            places[(i, j)] = (at, top(at), bottom(at))
    return _grid_piece(places, columns, rows)


def _grid(outline: Sequence[Point2D], spacing: float) -> tuple[float, float, int, int]:
    """Return a grid over ``outline`` with a point to spare all round: its
    first point's ``x`` and ``y``, and its columns and rows."""
    xs = [p.x for p in outline]
    ys = [p.y for p in outline]
    x0, y0 = min(xs) - spacing, min(ys) - spacing
    columns = math.ceil((max(xs) - x0) / spacing) + 2
    rows = math.ceil((max(ys) - y0) / spacing) + 2
    return x0, y0, columns, rows


def _grid_piece(
    places: dict[tuple[int, int], tuple[Point2D, float, float]],
    columns: int,
    rows: int,
) -> _Piece:
    """Return the solid over a grid's points: each ``(at, top, bottom)``,
    a cell's top and bottom where all four corners have one, and walls
    round the cells' edge."""
    positions: list[float] = []
    top_index: dict[tuple[int, int], int] = {}
    back_index: dict[tuple[int, int], int] = {}
    for key, (at, top, back) in places.items():
        top_index[key] = len(positions) // 3
        positions += (at.x, at.y, top)
        back_index[key] = len(positions) // 3
        positions += (at.x, at.y, back)
    triangles: list[int] = []
    edges: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}
    for j in range(rows - 1):
        for i in range(columns - 1):
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if not all(corner in places for corner in corners):
                continue
            a, b, c, d = (top_index[corner] for corner in corners)
            triangles += (a, b, c, a, c, d)
            a, b, c, d = (back_index[corner] for corner in corners)
            triangles += (a, c, b, a, d, c)
            for first, second in zip(corners, (*corners[1:], corners[0]), strict=True):
                edges[(first, second)] = edges.get((first, second), 0) + 1
    # Walls up the edge (and round a route cut through): each top edge used
    # by one cell only, down to the back beneath it.
    for first, second in edges:
        if (second, first) in edges:
            continue
        a, b = top_index[first], top_index[second]
        c, d = back_index[second], back_index[first]
        triangles += (a, d, c, a, c, b)
    return positions, triangles


def _round_drop(radius: float, distance: float) -> float:
    """Return how far a roundover lowers the face ``distance`` in from the edge."""
    if radius <= 0.0 or distance >= radius:
        return 0.0
    inset = radius - distance
    return radius - math.sqrt(max(0.0, radius * radius - inset * inset))


def _next_to(inside: list[list[bool]], i: int, j: int) -> bool:
    """Return whether a grid point outside has an inside one beside it."""
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            jj, ii = j + dj, i + di
            if 0 <= jj < len(inside) and 0 <= ii < len(inside[0]) and inside[jj][ii]:
                return True
    return False


def _fill(
    polygon: Sequence[Point2D],
    x0: float,
    y0: float,
    spacing: float,
    columns: int,
    rows: int,
) -> list[list[bool]]:
    """Return which grid points lie inside ``polygon`` (by scanlines)."""
    cells = [[False] * columns for _ in range(rows)]
    edges = list(zip(polygon, (*polygon[1:], polygon[0]), strict=True))
    for j in range(rows):
        y = y0 + j * spacing
        crossings = sorted(
            a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y)
            for a, b in edges
            if (a.y <= y < b.y) or (b.y <= y < a.y)
        )
        for start, end in zip(crossings[0::2], crossings[1::2], strict=False):
            first = max(0, math.ceil((start - x0) / spacing))
            last = min(columns - 1, math.floor((end - x0) / spacing))
            for i in range(first, last + 1):
                cells[j][i] = True
    return cells


def _filled(
    polygons: Sequence[Sequence[Point2D]],
    x0: float,
    y0: float,
    spacing: float,
    columns: int,
    rows: int,
) -> list[list[bool]]:
    """Return which grid points lie inside any of ``polygons``."""
    cells = [[False] * columns for _ in range(rows)]
    for polygon in polygons:
        if len(polygon) < 3:
            continue
        for j, row in enumerate(_fill(polygon, x0, y0, spacing, columns, rows)):
            for i, inside in enumerate(row):
                if inside:
                    cells[j][i] = True
    return cells


def _route_depths(
    routes: Sequence[tuple[Sequence[Point2D], float]],
    x0: float,
    y0: float,
    spacing: float,
    columns: int,
    rows: int,
) -> list[list[float]]:
    """Return the deepest route at each grid point (0 for none)."""
    depths = [[0.0] * columns for _ in range(rows)]
    for outline, depth in routes:
        if len(outline) < 3:
            continue
        for j, row in enumerate(_fill(outline, x0, y0, spacing, columns, rows)):
            for i, inside in enumerate(row):
                if inside and depth > depths[j][i]:
                    depths[j][i] = depth
    return depths


class _SegmentIndex:
    """Nearest points on a closed outline, found through a bucket grid."""

    CELL = 8.0

    def __init__(self, outline: Sequence[Point2D]) -> None:
        self.segments = list(zip(outline, (*outline[1:], outline[0]), strict=True))
        self.buckets: dict[tuple[int, int], list[int]] = {}
        for index, (a, b) in enumerate(self.segments):
            for cell in self._cells(
                min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)
            ):
                self.buckets.setdefault(cell, []).append(index)

    def _cells(
        self, low_x: float, low_y: float, high_x: float, high_y: float
    ) -> list[tuple[int, int]]:
        size = self.CELL
        return [
            (cx, cy)
            for cx in range(math.floor(low_x / size), math.floor(high_x / size) + 1)
            for cy in range(math.floor(low_y / size), math.floor(high_y / size) + 1)
        ]

    def distance(self, point: Point2D, reach: float) -> float:
        """Return the distance to the outline, or ``math.inf`` past ``reach``."""
        best = math.inf
        for _, distance in self._near(point, reach):
            best = min(best, distance)
        return best if best <= reach else math.inf

    def nearest(self, point: Point2D) -> Point2D:
        """Return the outline's point nearest ``point``."""
        reach = self.CELL
        while True:
            found = min(
                self._near(point, reach), key=lambda pair: pair[1], default=None
            )
            if found is not None:
                return found[0]
            reach *= 2.0

    def _near(self, point: Point2D, reach: float) -> list[tuple[Point2D, float]]:
        seen: set[int] = set()
        found: list[tuple[Point2D, float]] = []
        for cell in self._cells(
            point.x - reach, point.y - reach, point.x + reach, point.y + reach
        ):
            for index in self.buckets.get(cell, ()):
                if index in seen:
                    continue
                seen.add(index)
                a, b = self.segments[index]
                foot = _foot(point, a, b)
                found.append((foot, math.hypot(foot.x - point.x, foot.y - point.y)))
        return found


def _foot(point: Point2D, a: Point2D, b: Point2D) -> Point2D:
    """Return the point of segment ``a``-``b`` nearest ``point``."""
    ex, ey = b.x - a.x, b.y - a.y
    length = ex * ex + ey * ey
    t = 0.0 if length == 0.0 else ((point.x - a.x) * ex + (point.y - a.y) * ey) / length
    t = max(0.0, min(1.0, t))
    return Point2D(a.x + ex * t, a.y + ey * t)


# ---- the details: frets, markers and the nut ------------------------------------


def _neck_details(
    geometry: Prototype001Geometry, parameters: Prototype001Parameters
) -> dict[str, list[_Piece]]:
    surface = geometry.fretboard_surface
    tilt = _Tilt(*geometry.neck_tilt)
    layout = geometry.fret_layout
    slots = [*layout.slots]
    if layout.zero_fret_slot is not None:
        slots.append(layout.zero_fret_slot)

    # The markers flush with the board, a hair proud so they show.
    def under(at: Point2D) -> float:
        return _board_top(surface, at.y) - 0.6

    def face(at: Point2D) -> float:
        return _board_top(surface, at.y) + 0.1

    return {
        "Frets": [
            tilt.piece(_fret_piece(surface, slot, parameters.fret_height))
            for slot in slots
        ],
        "Markers": [
            tilt.piece(_plate_piece(marker.outline, _MARKER_SPACING, under, face))
            for marker in geometry.inlay_layout.markers
            if len(marker.outline) >= 3
        ],
        "Nut": [tilt.piece(_nut_piece(surface, parameters))],
    }


def _board_top(surface: FretboardSurface, y: float) -> float:
    """Return the board's playing surface's height ``y`` off the centreline."""
    radius = surface.radius
    return surface.center_thickness - radius + math.sqrt(max(0.0, radius**2 - y**2))


def _fret_piece(surface: FretboardSurface, slot: Line2D, height: float) -> _Piece:
    """Return a fret: its crown along ``slot``, edge to edge of the board
    and on its radius."""
    start, end = slot.start, slot.end
    lean = 0.0 if end.y == start.y else (end.x - start.x) / (end.y - start.y)
    centre = start.x - lean * start.y
    reach = surface.half_width_at(centre) - 0.3
    half = _FRET_CROWN / 2.0
    rows = []
    for k in range(11):
        y = -reach + 2.0 * reach * k / 10
        x = centre + lean * y
        z = _board_top(surface, y)
        crown = [
            Point3D(
                x - half * math.cos(math.pi * s / 6),
                y,
                z + height * math.sin(math.pi * s / 6),
            )
            for s in range(7)
        ]
        rows.append(
            [Point3D(x - half, y, z - 0.3), *crown, Point3D(x + half, y, z - 0.3)]
        )
    return _rows_piece(rows)


def _nut_piece(surface: FretboardSurface, parameters: Prototype001Parameters) -> _Piece:
    """Return the nut across the board's end, as high as the strings sit."""
    reach = surface.half_width_at(0.0)
    lean = surface.skew.at(0.0)
    thickness = parameters.nut_thickness
    rows = []
    for k in range(9):
        y = -reach + 2.0 * reach * k / 8
        x = lean * y
        top = _board_top(surface, y) + parameters.fret_height + _NUT_OVER_FRETS
        rows.append(
            [
                Point3D(x - thickness, y, 0.0),
                Point3D(x - thickness, y, top),
                Point3D(x, y, top),
                Point3D(x, y, 0.0),
            ]
        )
    return _rows_piece(rows)


# ---- the details: tuners -------------------------------------------------------


def _headstock_details(
    geometry: Prototype001Geometry, parameters: Prototype001Parameters
) -> dict[str, list[_Piece]]:
    headstock = geometry.headstock
    tilt = _Tilt(*geometry.neck_tilt)
    post = parameters.tuner_post_diameter / 2.0
    pieces = []
    for hole in geometry.tuner_layout.holes:
        base, normal = _tuner_seat(headstock, hole.center)
        bushing = hole.diameter / 2.0 + 1.5
        back = _along(base, normal, -headstock.thickness)
        # Its gear under the back, its button out past the headstock's side.
        housing = _along(back, normal, -5.0)
        side = parameters.bass_sign if hole.side == "bass" else -parameters.bass_sign
        away = (0.0, side, 0.0)
        button = _along(_along(housing, away, 26.0), normal, -2.0)
        pieces += [
            _cylinder_piece(_along(base, normal, -0.5), normal, bushing, bushing, 3.0),
            _cylinder_piece(base, normal, post, post, _POST_HEIGHT),
            _cylinder_piece(back, _scaled(normal, -1.0), 9.0, 9.0, 10.0),
            _cylinder_piece(housing, away, 1.6, 1.6, 21.0, sides=8),
            _cylinder_piece(button, normal, 6.5, 6.5, 4.0),
        ]
    return {"Tuners": [tilt.piece(piece) for piece in pieces]}


def _tuner_seat(headstock: HeadstockSolid, centre: Point2D) -> tuple[Vector, Vector]:
    """Return where a tuner sits on the headstock face, and the face's
    normal there (its posts stand along it)."""
    rise = headstock.face_z(centre.x + 0.5) - headstock.face_z(centre.x - 0.5)
    return (centre.x, centre.y, headstock.face_z(centre.x)), _unit((-rise, 0.0, 1.0))


# ---- the details: pickguard, pickups and knobs -----------------------------------


def _body_details(
    geometry: Prototype001Geometry, parameters: Prototype001Parameters
) -> dict[str, list[_Piece]]:
    body = geometry.body

    def surface(at: Point2D) -> float:
        return -body.top_drop_at(at.x, at.y)

    plates = [cover for cover in geometry.covers if cover.face == "top"]
    guards: list[_Piece] = []
    seats: list[tuple[Sequence[Point2D], float]] = []
    for cover in plates:
        foot = max(surface(p) for p in cover.outline)
        guards.append(
            _plate_piece(
                cover.outline,
                PREVIEW_SPACING,
                _level(foot),
                _level(foot + cover.thickness),
            )
        )
        seats.append((cover.outline, foot + cover.thickness))

    def seat(at: Point2D) -> float:
        """The height a part stands on: a top plate's, else the top's."""
        for outline, height in seats:
            if point_in_polygon(at, outline):
                return height
        return surface(at)

    # The pickups as the pickguard's openings show them, else as routed.
    openings = [
        slot.outline
        for cover in plates
        for slot in cover.slots
        if "pickup" in slot.name.lower()
    ]
    routes = [
        cavity.outline
        for cavity in (body.neck_pickup, body.bridge_pickup, *body.extra_cavities)
        if cavity is not None and "pickup" in cavity.name.lower()
    ]
    pickups = []
    for outline in openings or routes:
        foot = max(seat(p) for p in (*outline, _middle(outline)))
        pickups.append(
            _plate_piece(outline, 1.0, _level(foot - 3.0), _level(foot + _PICKUP_RISE))
        )
    up = (0.0, 0.0, 1.0)
    knobs = []
    holes = [
        *(hole for cover in plates for hole in cover.holes),
        *body.holes,
    ]
    for hole in holes:
        name = hole.name.lower()
        at = Point2D(hole.center_x, hole.center_y)
        if "pot" in name and "shaft" in name:
            foot, top, height = _KNOB
            knobs.append(
                _cylinder_piece((at.x, at.y, seat(at)), up, foot, top, height, 24)
            )
        elif "switch" in name and "shaft" in name:
            # A toggle's lever and its tip.
            base = (at.x, at.y, seat(at))
            knobs += [
                _cylinder_piece(base, up, 1.6, 1.4, 18.0, sides=10),
                _cylinder_piece(_along(base, up, 14.0), up, 4.0, 3.5, 10.0, sides=16),
            ]
    for cover in plates:
        for slot in cover.slots:
            if "switch" in slot.name.lower():
                # A blade switch's tip, up through its slot.
                middle = _middle(slot.outline)
                base = (middle.x, middle.y, seat(middle))
                knobs.append(_cylinder_piece(base, up, 3.5, 3.0, 11.0, sides=16))
    return {"Pickguard": guards, "Pickups": pickups, "Knobs": knobs}


def _level(height: float) -> Callable[[Point2D], float]:
    """Return a height the same at every point."""

    def at(_: Point2D) -> float:
        return height

    return at


def _middle(outline: Sequence[Point2D]) -> Point2D:
    """Return the middle of ``outline``'s points."""
    return Point2D(
        sum(p.x for p in outline) / len(outline),
        sum(p.y for p in outline) / len(outline),
    )


# ---- the details: bridge and strings ---------------------------------------------


def _bridge_details(
    geometry: Prototype001Geometry, parameters: Prototype001Parameters
) -> dict[str, list[_Piece]]:
    """The strings from their tuners over the nut to the saddles, the action
    set over the frets on the neck (and tilted with it); a bridge plate on
    the top beneath the saddles."""
    surface = geometry.fretboard_surface
    body = geometry.body
    tilt = _Tilt(*geometry.neck_tilt)
    count = parameters.string_count
    scale = surface.scale_length
    nut_lean, bridge_lean = surface.skew.at(0.0), surface.skew.at(scale)
    frets = parameters.fret_height
    posts = _posts_of_strings(geometry, count)
    strings: list[_Piece] = []
    saddles: list[tuple[Vector, float]] = []
    for string in range(1, count + 1):
        side = parameters.bass_sign * ((count + 1) / 2.0 - string)
        nut_y = side * parameters.nut_string_spacing
        bridge_y = side * parameters.bridge_string_spacing
        # Thick to thin, bass to treble.
        radius = 0.6 - 0.3 * (string - 1) / max(1, count - 1)
        nut_z = _board_top(surface, nut_y) + frets + _NUT_OVER_FRETS + radius
        front = (nut_lean * nut_y, nut_y, nut_z)
        back = (front[0] - parameters.nut_thickness, nut_y, nut_z)
        post = posts[string - 1] if string <= len(posts) else None
        wound = post if post is not None else (back[0] - 15.0, nut_y, nut_z)
        saddle = (
            scale + bridge_lean * bridge_y,
            bridge_y,
            _board_top(surface, bridge_y) + frets + _ACTION_AT_SADDLES + radius,
        )
        path = [tilt(*point) for point in (wound, back, front, saddle)]
        strings += [
            _cylinder_piece(a, _unit(_minus(b, a)), radius, radius, _length(a, b), 6)
            for a, b in zip(path, path[1:], strict=False)
        ]
        saddles.append((path[-1], radius))
    # The plate across beneath the saddles, on the top.
    middle_x = sum(end[0] for end, _ in saddles) / len(saddles)
    spread = (count - 1) / 2.0 * parameters.bridge_string_spacing + 9.0
    corners = [
        Point2D(middle_x + dx + bridge_lean * dy, dy)
        for dx in (-14.0, 22.0)
        for dy in (-spread, spread)
    ]
    heights = [-body.top_drop_at(p.x, p.y) for p in (*corners, Point2D(middle_x, 0.0))]
    floor, plate = min(heights) - 1.0, max(heights) + 2.5
    bridge = [
        _box_piece(
            middle_x - 14.0, middle_x + 22.0, -spread, spread, floor, plate, bridge_lean
        )
    ]
    half = min(4.5, parameters.bridge_string_spacing / 2.0 - 0.6)
    for (x, y, z), radius in saddles:
        top = max(plate + 1.0, z - radius)
        bridge.append(
            _box_piece(x - 1.5, x + 8.5, y - half, y + half, plate - 0.5, top)
        )
    return {"Bridge": bridge, "Strings": strings}


def _posts_of_strings(geometry: Prototype001Geometry, count: int) -> list[Vector]:
    """Return where each string, bass first, is wound on its tuner's post:
    the bass side's from the nut out to the bass strings from the outside
    in, the treble side's to the treble strings from the outside in (as a
    Gibson's or a Fender's)."""
    headstock = geometry.headstock
    holes = geometry.tuner_layout.holes
    bass = sorted((h for h in holes if h.side == "bass"), key=lambda h: h.index)
    treble = sorted((h for h in holes if h.side == "treble"), key=lambda h: h.index)
    posts = []
    for hole in [*bass, *reversed(treble)][:count]:
        base, normal = _tuner_seat(headstock, hole.center)
        posts.append(_along(base, normal, _WIND_HEIGHT))
    return posts


# ---- the details: solids -------------------------------------------------------


def _cylinder_piece(
    base: Vector,
    axis: Vector,
    foot: float,
    top: float,
    height: float,
    sides: int = 20,
) -> _Piece:
    """Return a cylinder (a cone's frustum if ``foot`` and ``top``, its
    radii, differ) standing ``height`` on ``base`` along the unit ``axis``."""
    across = (1.0, 0.0, 0.0) if abs(axis[1]) > 0.9 else (0.0, 1.0, 0.0)
    u = _unit(_cross(axis, across))
    v = _cross(axis, u)
    positions: list[float] = []
    for radius, lift in ((foot, 0.0), (top, height)):
        for k in range(sides):
            turn = 2.0 * math.pi * k / sides
            c, s = math.cos(turn) * radius, math.sin(turn) * radius
            positions += (
                base[n] + axis[n] * lift + u[n] * c + v[n] * s for n in range(3)
            )
    triangles: list[int] = []
    for k in range(sides):
        a, b = k, (k + 1) % sides
        triangles += (a, b, sides + b, a, sides + b, sides + a)
    triangles += _cap(positions, list(reversed(range(sides))))
    triangles += _cap(positions, list(range(sides, 2 * sides)))
    return positions, triangles


def _box_piece(
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    lean: float = 0.0,
) -> _Piece:
    """Return a box, its ends along X leaning ``lean`` (X across Y, as a
    fanned bridge's line)."""
    return _rows_piece(
        [
            [
                Point3D(x0 + lean * y, y, z0),
                Point3D(x0 + lean * y, y, z1),
                Point3D(x1 + lean * y, y, z1),
                Point3D(x1 + lean * y, y, z0),
            ]
            for y in (y0, y1)
        ]
    )


# ---- meshes --------------------------------------------------------------------


def _part(name: str, pieces: Sequence[_Piece]) -> PreviewPart:
    """Return the part of ``pieces``, each turned outward (a positive volume)."""
    positions: list[float] = []
    triangles: list[int] = []
    for piece_positions, piece_triangles in pieces:
        offset = len(positions) // 3
        positions += piece_positions
        triangles += (offset + v for v in _outward(piece_positions, piece_triangles))
    return PreviewPart(name, PREVIEW_COLOURS[name], tuple(positions), tuple(triangles))


def _outward(positions: list[float], triangles: list[int]) -> list[int]:
    """Return a closed mesh's triangles turned outward (a positive volume)."""
    volume = 0.0
    for index in range(0, len(triangles), 3):
        a, b, c = (
            tuple(positions[3 * v : 3 * v + 3]) for v in triangles[index : index + 3]
        )
        volume += _dot(a, _cross(b, c))
    if volume >= 0.0:
        return triangles
    return [
        vertex
        for index in range(0, len(triangles), 3)
        for vertex in (triangles[index], triangles[index + 2], triangles[index + 1])
    ]


def _minus(a: Vector, b: Vector) -> Vector:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vector, b: Vector) -> Vector:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Vector, b: Vector) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a: Vector) -> Vector:
    size = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / size, a[1] / size, a[2] / size)


def _scaled(a: Vector, factor: float) -> Vector:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def _along(point: Vector, direction: Vector, distance: float) -> Vector:
    """Return ``point`` moved ``distance`` along the unit ``direction``."""
    return (
        point[0] + direction[0] * distance,
        point[1] + direction[1] * distance,
        point[2] + direction[2] * distance,
    )


def _length(a: Vector, b: Vector) -> float:
    return math.sqrt(_dot(_minus(b, a), _minus(b, a)))


def _little_endian(values: array) -> bytes:  # type: ignore[type-arg]
    """Return ``values``' bytes, little-endian whatever the machine."""
    if sys.byteorder == "big":
        values.byteswap()
    return values.tobytes()


__all__ = [
    "DETAILS",
    "PREVIEW_COLOURS",
    "PREVIEW_SPACING",
    "PreviewPart",
    "detail_parts",
    "preview_parts",
    "stl_bytes",
]
