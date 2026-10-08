"""Read the shapes of a DXF drawing as polylines in millimetres.

Enough of DXF for an outline drawn in a CAD program (AutoCAD, Fusion,
FreeCAD, LibreCAD, QCAD, Rhino): ASCII DXF of any version, its entities'
``LINE``, ``ARC``, ``CIRCLE``, ``ELLIPSE``, ``LWPOLYLINE`` and ``POLYLINE``
(their bulges as arcs) and ``SPLINE`` (NURBS, or through its fit points),
on layers, in the drawing's units (``$INSUNITS``). Pieces that meet end
to end on one layer are joined into one line, closed where it comes back
to its start, as a CAD outline is often drawn line by line and arc by
arc. ``POINT``\\ s are read on their own. Text, hatches, dimensions and
blocks (``INSERT``) are left out.

Every shape comes as an ``SvgShape`` (its layer its group and its label),
so a template read back from DXF goes through the same steps as one read
back from SVG. Coordinates are the drawing's own: Y up, as DXF has it.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from ..geometry.primitives import Point2D, flatten_span
from .exceptions import DrawingError
from .svg_reader import SvgShape

MM_PER_DXF_UNIT = {
    0: 1.0,
    1: 25.4,
    2: 304.8,
    4: 1.0,
    5: 10.0,
    6: 1000.0,
    8: 25.4e-6,
    9: 0.0254,
    10: 914.4,
    13: 1e-3,
    14: 0.1,
}
"""Millimetres per ``$INSUNITS`` unit (unitless: millimetres)."""

JOIN_GAP = 0.05
"""How near (mm) two pieces' ends must be to be joined."""

CIRCLE_TURN = 2.0 * math.pi


@dataclass(frozen=True, slots=True)
class _Piece:
    layer: str
    hidden: bool
    points: tuple[Point2D, ...]
    closed: bool
    nodes: tuple[int, ...]


def is_dxf(text: str) -> bool:
    """Return whether ``text`` is an ASCII DXF file (it starts a section)."""
    lines = [line.strip() for line in text.lstrip("﻿").splitlines()[:40]]
    for index in range(0, len(lines) - 1, 2):
        if lines[index] == "999":
            continue
        return lines[index] == "0" and lines[index + 1] == "SECTION"
    return False


def read_dxf_drawing(
    text: str, tolerance: float = 0.05
) -> tuple[tuple[SvgShape, ...], tuple[tuple[str, Point2D], ...]]:
    """Return a DXF drawing's shapes and its points (each with its layer).

    Args:
        text: The DXF file's text.
        tolerance: How far an arc or a curve flattened into a polyline
            may stray from it, in millimetres.

    Raises:
        DrawingError: If it is a binary DXF or not a DXF file at all.
    """
    if text.startswith("AutoCAD Binary DXF"):
        raise DrawingError(
            "This is a binary DXF file: save it as an ASCII DXF (R12 or later)."
        )
    pairs = _pairs(text)
    scale = MM_PER_DXF_UNIT.get(int(_header(pairs, "$INSUNITS") or 0), 1.0)
    hidden_layers = _hidden_layers(pairs)
    pieces: list[_Piece] = []
    points: list[tuple[str, Point2D]] = []
    for kind, codes, vertices in _entities(pairs):
        layer = _text(codes, 8, "0")
        hidden = layer in hidden_layers or _number(codes, 60) == 1.0
        if kind == "POINT":
            points.append(
                (layer, Point2D(_number(codes, 10) * scale, _number(codes, 20) * scale))
            )
            continue
        made = _piece(kind, codes, vertices, tolerance / scale)
        if made is None:
            continue
        outline, closed, nodes = made
        if len(outline) < 2:
            continue
        pieces.append(
            _Piece(
                layer,
                hidden,
                tuple(Point2D(p.x * scale, p.y * scale) for p in outline),
                closed,
                nodes,
            )
        )
    shapes = [
        SvgShape(
            "",
            piece.layer,
            (piece.layer,),
            piece.hidden,
            (piece.points,),
            (piece.closed,),
            (piece.nodes,),
        )
        for piece in _joined(pieces)
    ]
    return tuple(shapes), tuple(points)


# -- the file -----------------------------------------------------------------


def _pairs(text: str) -> list[tuple[int, str]]:
    """Return the file's group codes and values."""
    lines = text.lstrip("﻿").splitlines()
    pairs = []
    try:
        for index in range(0, len(lines) - 1, 2):
            pairs.append((int(lines[index].strip()), lines[index + 1].strip()))
    except ValueError as error:
        raise DrawingError("This is not a DXF file (or it is cut short).") from error
    if not pairs or pairs[0] != (0, "SECTION") and pairs[0][0] != 999:
        raise DrawingError("This is not a DXF file.")
    return pairs


def _sections(pairs: Sequence[tuple[int, str]], name: str) -> Iterator[int]:
    """Yield the index after each ``SECTION`` named ``name``."""
    for index in range(len(pairs) - 1):
        if pairs[index] == (0, "SECTION") and pairs[index + 1] == (2, name):
            yield index + 2


def _header(pairs: Sequence[tuple[int, str]], variable: str) -> str | None:
    for start in _sections(pairs, "HEADER"):
        index = start
        while index < len(pairs) and pairs[index] != (0, "ENDSEC"):
            if pairs[index] == (9, variable) and index + 1 < len(pairs):
                return pairs[index + 1][1]
            index += 1
    return None


def _hidden_layers(pairs: Sequence[tuple[int, str]]) -> set[str]:
    """Return the layers turned off (a negative colour) or frozen."""
    hidden: set[str] = set()
    for start in _sections(pairs, "TABLES"):
        index = start
        while index < len(pairs) and pairs[index] != (0, "ENDSEC"):
            if pairs[index] == (0, "LAYER"):
                codes: dict[int, str] = {}
                index += 1
                while index < len(pairs) and pairs[index][0] != 0:
                    codes.setdefault(pairs[index][0], pairs[index][1])
                    index += 1
                colour = _number(codes, 62, 7.0)
                if colour < 0 or int(_number(codes, 70)) & 1:
                    hidden.add(codes.get(2, ""))
                continue
            index += 1
    return hidden


def _entities(
    pairs: Sequence[tuple[int, str]],
) -> Iterator[tuple[str, dict[int, str], list[dict[int, str]]]]:
    """Yield each entity in the ENTITIES section: its kind, its codes (the
    first of each) and, for a ``POLYLINE``, its ``VERTEX``\\ es' codes; an
    ``LWPOLYLINE``'s and a ``SPLINE``'s repeated codes come as the
    vertices' (one dict per point)."""
    for start in _sections(pairs, "ENTITIES"):
        index = start
        polyline: tuple[dict[int, str], list[dict[int, str]]] | None = None
        while index < len(pairs) and pairs[index] != (0, "ENDSEC"):
            kind = pairs[index][1]
            index += 1
            body: list[tuple[int, str]] = []
            while index < len(pairs) and pairs[index][0] != 0:
                body.append(pairs[index])
                index += 1
            codes: dict[int, str] = {}
            for code, value in body:
                codes.setdefault(code, value)
            if kind == "POLYLINE":
                polyline = (codes, [])
            elif kind == "VERTEX" and polyline is not None:
                polyline[1].append(codes)
            elif kind == "SEQEND" and polyline is not None:
                yield "POLYLINE", polyline[0], polyline[1]
                polyline = None
            elif kind in ("LWPOLYLINE", "SPLINE"):
                yield kind, codes, _repeated(kind, body)
            else:
                yield kind, codes, []


def _repeated(kind: str, body: Sequence[tuple[int, str]]) -> list[dict[int, str]]:
    """Return an LWPOLYLINE's vertices (10, 20, 42) or a SPLINE's lists
    (one dict per knot, control point, weight and fit point, by code)."""
    if kind == "LWPOLYLINE":
        vertices: list[dict[int, str]] = []
        for code, value in body:
            if code == 10:
                vertices.append({10: value})
            elif vertices and code in (20, 42):
                vertices[-1][code] = value
        return vertices
    lists: list[dict[int, str]] = []
    for code, value in body:
        if code in (10, 11, 40, 41):
            lists.append({code: value})
        elif code in (20, 21) and lists and (code - 10) in lists[-1]:
            lists[-1][code] = value
    return lists


def _number(codes: dict[int, str], code: int, default: float = 0.0) -> float:
    try:
        return float(codes[code])
    except (KeyError, ValueError):
        return default


def _text(codes: dict[int, str], code: int, default: str) -> str:
    return codes.get(code, default) or default


# -- entities into polylines -------------------------------------------------


def _piece(
    kind: str,
    codes: dict[int, str],
    vertices: list[dict[int, str]],
    tolerance: float,
) -> tuple[list[Point2D], bool, tuple[int, ...]] | None:
    """Return an entity flattened: its points, whether it is closed, and
    the indices of its nodes (where one line or arc of it meets the next),
    or ``None`` for an entity that draws no line."""
    mirrored = _number(codes, 230, 1.0) < 0.0
    made: tuple[list[Point2D], bool, tuple[int, ...]] | None
    if kind == "LINE":
        made = (
            [
                Point2D(_number(codes, 10), _number(codes, 20)),
                Point2D(_number(codes, 11), _number(codes, 21)),
            ],
            False,
            (0, 1),
        )
        mirrored = False
    elif kind == "ARC":
        centre = Point2D(_number(codes, 10), _number(codes, 20))
        start = math.radians(_number(codes, 50))
        end = math.radians(_number(codes, 51))
        sweep = (end - start) % CIRCLE_TURN
        if min(sweep, CIRCLE_TURN - sweep) < 1e-9:
            return None  # its ends at one angle: no arc (as CAD programs read it)
        arc = _arc(centre, _number(codes, 40), start, sweep, tolerance)
        made = (arc, False, (0, len(arc) - 1))
    elif kind == "CIRCLE":
        centre = Point2D(_number(codes, 10), _number(codes, 20))
        circle = _arc(centre, _number(codes, 40), 0.0, CIRCLE_TURN, tolerance)
        made = (circle[:-1], True, (0,))
    elif kind == "ELLIPSE":
        made = _ellipse(codes, tolerance)
        mirrored = False  # its centre and axis are the drawing's own
    elif kind == "LWPOLYLINE":
        closed = int(_number(codes, 70)) & 1 == 1
        made = _bulged(
            [
                (_number(vertex, 10), _number(vertex, 20), _number(vertex, 42))
                for vertex in vertices
            ],
            closed,
            tolerance,
        )
    elif kind == "POLYLINE":
        flags = int(_number(codes, 70))
        if flags & (16 | 64):
            return None  # a mesh, not a line
        closed = flags & 1 == 1
        made = _bulged(
            [
                (_number(vertex, 10), _number(vertex, 20), _number(vertex, 42))
                for vertex in vertices
                # A spline-fit polyline's frame points are not on it.
                if not int(_number(vertex, 70)) & 16
            ],
            closed,
            tolerance,
        )
    elif kind == "SPLINE":
        made = _spline(codes, vertices, tolerance)
        mirrored = False
    else:
        return None
    if made is None:
        return None
    points, closed, nodes = made
    if mirrored:
        # Drawn in a plane seen from below (its extrusion -Z): X mirrored.
        points = [Point2D(-p.x, p.y) for p in points]
    return points, closed, nodes


def _arc(
    centre: Point2D, radius: float, start: float, sweep: float, tolerance: float
) -> list[Point2D]:
    """Return an arc from ``start`` turning ``sweep`` (radians, negative
    clockwise), its ends included, within ``tolerance`` of it."""
    radius = abs(radius)
    if radius <= 0.0:
        return [centre]
    step = 2.0 * math.acos(max(-1.0, min(1.0, 1.0 - tolerance / radius)))
    count = max(2, math.ceil(abs(sweep) / max(step, 1e-3)))
    return [
        Point2D(
            centre.x + radius * math.cos(start + sweep * index / count),
            centre.y + radius * math.sin(start + sweep * index / count),
        )
        for index in range(count + 1)
    ]


def _bulged(
    vertices: Sequence[tuple[float, float, float]], closed: bool, tolerance: float
) -> tuple[list[Point2D], bool, tuple[int, ...]] | None:
    """Return a polyline through ``(x, y, bulge)`` vertices: a straight
    segment from each to the next, or an arc where its bulge (the tangent
    of a quarter of the arc's angle, positive counter-clockwise) is set."""
    if not vertices:
        return None
    count = len(vertices)
    points = [Point2D(vertices[0][0], vertices[0][1])]
    nodes = [0]
    for index in range(count if closed else count - 1):
        x, y, bulge = vertices[index]
        nx, ny, _ = vertices[(index + 1) % count]
        a, b = Point2D(x, y), Point2D(nx, ny)
        if abs(bulge) > 1e-9 and (a.x, a.y) != (b.x, b.y):
            angle = 4.0 * math.atan(bulge)
            chord = math.hypot(b.x - a.x, b.y - a.y)
            offset = (chord / 2.0) / math.tan(angle / 2.0)
            centre = Point2D(
                (a.x + b.x) / 2.0 - (b.y - a.y) / chord * offset,
                (a.y + b.y) / 2.0 + (b.x - a.x) / chord * offset,
            )
            radius = math.hypot(a.x - centre.x, a.y - centre.y)
            start = math.atan2(a.y - centre.y, a.x - centre.x)
            points += _arc(centre, radius, start, angle, tolerance)[1:]
        else:
            points.append(b)
        nodes.append(len(points) - 1)
    if closed and len(points) > 1:
        points.pop()
        nodes.pop()
    return points, closed, tuple(nodes)


def _ellipse(
    codes: dict[int, str], tolerance: float
) -> tuple[list[Point2D], bool, tuple[int, ...]]:
    """Return an ``ELLIPSE`` (or its arc) flattened."""
    centre = Point2D(_number(codes, 10), _number(codes, 20))
    major = Point2D(_number(codes, 11), _number(codes, 21))
    ratio = _number(codes, 40, 1.0)
    start = _number(codes, 41)
    end = _number(codes, 42, CIRCLE_TURN)
    sweep = (end - start) % CIRCLE_TURN or CIRCLE_TURN
    length = math.hypot(major.x, major.y)
    step = 2.0 * math.acos(max(-1.0, min(1.0, 1.0 - tolerance / max(length, 1e-9))))
    count = max(8, math.ceil(sweep / max(step, 1e-3)))
    points = [
        Point2D(
            centre.x + major.x * math.cos(t) - ratio * major.y * math.sin(t),
            centre.y + major.y * math.cos(t) + ratio * major.x * math.sin(t),
        )
        for t in (start + sweep * index / count for index in range(count + 1))
    ]
    full = abs(sweep - CIRCLE_TURN) < 1e-9
    if full:
        return points[:-1], True, (0,)
    return points, False, (0, len(points) - 1)


def _spline(
    codes: dict[int, str], lists: list[dict[int, str]], tolerance: float
) -> tuple[list[Point2D], bool, tuple[int, ...]] | None:
    """Return a ``SPLINE`` flattened: its NURBS curve (degree, knots,
    control points and weights), or the line through its fit points
    where it has no control points."""
    degree = int(_number(codes, 71, 3.0))
    knots = [_number(entry, 40) for entry in lists if 40 in entry]
    control = [Point2D(_number(e, 10), _number(e, 20)) for e in lists if 10 in e]
    weights = [_number(entry, 41, 1.0) for entry in lists if 41 in entry]
    fits = [Point2D(_number(e, 11), _number(e, 21)) for e in lists if 11 in e]
    closed = int(_number(codes, 70)) & 1 == 1
    if len(control) < degree + 1 or len(knots) != len(control) + degree + 1:
        if len(fits) < 2:
            return None
        through = _through(fits, tolerance)
        return through, closed, (0, len(through) - 1)
    if len(weights) != len(control):
        weights = [1.0] * len(control)
    low, high = knots[degree], knots[len(control)]
    if high <= low:
        return None
    # Samples enough for the control polygon's length at the tolerance.
    polygon = sum(
        math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(control, control[1:])
    )
    count = max(
        8 * (len(control) - degree), math.ceil(polygon / max(4.0 * tolerance, 0.2))
    )
    count = min(count, 4000)
    points = [
        _de_boor(degree, knots, control, weights, low + (high - low) * index / count)
        for index in range(count + 1)
    ]
    if (
        closed
        and math.hypot(points[0].x - points[-1].x, points[0].y - points[-1].y) < 1e-6
    ):
        return points[:-1], True, (0,)
    return points, closed, (0, len(points) - 1)


def _through(fits: Sequence[Point2D], tolerance: float) -> list[Point2D]:
    """Return the curve through a spline's fit points (one with no control
    points) as CAD programs draw it: the natural cubic spline (no bending
    at its ends) with its parameter running along the chords."""
    if len(fits) < 3:
        return list(fits)
    steps = [
        max(math.hypot(b.x - a.x, b.y - a.y), 1e-9) for a, b in zip(fits, fits[1:])
    ]
    xs = _natural_slopes([p.x for p in fits], steps)
    ys = _natural_slopes([p.y for p in fits], steps)
    points = [fits[0]]
    for index, step in enumerate(steps):
        a, b = fits[index], fits[index + 1]
        (ax, bx), (ay, by) = xs[index], ys[index]
        points += flatten_span(
            (
                a,
                Point2D(a.x + ax * step / 3.0, a.y + ay * step / 3.0),
                Point2D(b.x - bx * step / 3.0, b.y - by * step / 3.0),
                b,
            ),
            tolerance,
        )
    return points


def _natural_slopes(
    values: Sequence[float], steps: Sequence[float]
) -> list[tuple[float, float]]:
    """Return a natural cubic spline's slopes at each interval's two ends,
    through ``values`` at parameters ``steps`` apart."""
    count = len(values)
    # Second derivatives (zero at the ends): a tridiagonal solve.
    lower = [0.0] * count
    diagonal = [1.0] * count
    upper = [0.0] * count
    right = [0.0] * count
    for i in range(1, count - 1):
        lower[i], upper[i] = steps[i - 1], steps[i]
        diagonal[i] = 2.0 * (steps[i - 1] + steps[i])
        right[i] = 6.0 * (
            (values[i + 1] - values[i]) / steps[i]
            - (values[i] - values[i - 1]) / steps[i - 1]
        )
    for i in range(1, count):
        factor = lower[i] / diagonal[i - 1]
        diagonal[i] -= factor * upper[i - 1]
        right[i] -= factor * right[i - 1]
    second = [0.0] * count
    second[-1] = right[-1] / diagonal[-1]
    for i in range(count - 2, -1, -1):
        second[i] = (right[i] - upper[i] * second[i + 1]) / diagonal[i]
    slopes = []
    for i, step in enumerate(steps):
        rise = (values[i + 1] - values[i]) / step
        slopes.append(
            (
                rise - step * (2.0 * second[i] + second[i + 1]) / 6.0,
                rise + step * (second[i] + 2.0 * second[i + 1]) / 6.0,
            )
        )
    return slopes


def _de_boor(
    degree: int,
    knots: Sequence[float],
    control: Sequence[Point2D],
    weights: Sequence[float],
    t: float,
) -> Point2D:
    """Return the NURBS curve's point at parameter ``t`` (de Boor)."""
    span = degree
    while span < len(control) - 1 and t >= knots[span + 1]:
        span += 1
    points = [
        (
            control[j].x * weights[j],
            control[j].y * weights[j],
            weights[j],
        )
        for j in range(span - degree, span + 1)
    ]
    for r in range(1, degree + 1):
        for j in range(degree, r - 1, -1):
            i = span - degree + j
            denominator = knots[i + degree - r + 1] - knots[i]
            alpha = 0.0 if denominator == 0.0 else (t - knots[i]) / denominator
            (ax, ay, aw), (bx, by, bw) = points[j - 1], points[j]
            points[j] = (
                (1.0 - alpha) * ax + alpha * bx,
                (1.0 - alpha) * ay + alpha * by,
                (1.0 - alpha) * aw + alpha * bw,
            )
    x, y, w = points[degree]
    return Point2D(x / w, y / w)


# -- joining pieces ------------------------------------------------------------


def _joined(pieces: Sequence[_Piece]) -> list[_Piece]:
    """Return the pieces with those that meet end to end on one layer
    joined into one, closed where it comes back to its start."""
    out = [piece for piece in pieces if piece.closed]
    open_pieces = [piece for piece in pieces if not piece.closed]
    cells: dict[tuple[str, int, int], list[int]] = {}

    def cell(layer: str, point: Point2D) -> tuple[str, int, int]:
        return (layer, round(point.x / JOIN_GAP), round(point.y / JOIN_GAP))

    for index, piece in enumerate(open_pieces):
        for end in (piece.points[0], piece.points[-1]):
            cells.setdefault(cell(piece.layer, end), []).append(index)
    used = [False] * len(open_pieces)

    def near(a: Point2D, b: Point2D) -> bool:
        return math.hypot(a.x - b.x, a.y - b.y) <= JOIN_GAP

    def take(layer: str, point: Point2D) -> tuple[_Piece, bool] | None:
        """Return an unused piece with an end at ``point`` (reversed so it
        starts there), or ``None``."""
        key = cell(layer, point)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for index in cells.get((layer, key[1] + dx, key[2] + dy), ()):
                    if used[index]:
                        continue
                    piece = open_pieces[index]
                    if near(piece.points[0], point):
                        used[index] = True
                        return piece, False
                    if near(piece.points[-1], point):
                        used[index] = True
                        return piece, True
        return None

    for index, first in enumerate(open_pieces):
        if used[index]:
            continue
        used[index] = True
        points = list(first.points)
        nodes = list(first.nodes)
        hidden = first.hidden
        # On from its end, then back from its start.
        for forward in (True, False):
            while True:
                end = points[-1] if forward else points[0]
                found = take(first.layer, end)
                if found is None:
                    break
                piece, reverse = found
                hidden = hidden and piece.hidden
                # The piece as it runs on from the chain's end (or away
                # from its start).
                last = len(piece.points) - 1
                more = list(reversed(piece.points)) if reverse else list(piece.points)
                more_nodes = (
                    sorted(last - n for n in piece.nodes)
                    if reverse
                    else list(piece.nodes)
                )
                if forward:
                    offset = len(points) - 1
                    points += more[1:]
                    nodes += [offset + n for n in more_nodes if n > 0]
                else:
                    # Put in front of the chain, run toward its start.
                    back = list(reversed(more))
                    back_nodes = sorted(last - n for n in more_nodes)
                    points = back[:-1] + points
                    nodes = [n for n in back_nodes if n < last] + [
                        last + n for n in nodes
                    ]
        closed = len(points) > 2 and near(points[0], points[-1])
        if closed:
            points.pop()
            nodes = sorted({n % len(points) for n in nodes} | {0})
        out.append(
            _Piece(
                first.layer, hidden, tuple(points), closed, tuple(sorted(set(nodes)))
            )
        )
    return out
