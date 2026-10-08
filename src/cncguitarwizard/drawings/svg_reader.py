"""Read the shapes of an SVG drawing as polylines in millimetres.

Enough of SVG for an outline drawn in Inkscape, Illustrator, Affinity
Designer or a CAD program: paths (every command, arcs included), rects,
circles, ellipses, lines, polylines and polygons, inside groups and
layers with any ``transform``, in a document sized in any unit. Text,
images and anything under ``defs`` are left out. Curves are flattened to
within a tolerance, in the document's own millimetres.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterator
from dataclasses import dataclass

from ..geometry.primitives import BezierSpan, Point2D, flatten_span
from .exceptions import DrawingError

Matrix = tuple[float, float, float, float, float, float]
"""An SVG affine transform ``(a, b, c, d, e, f)``: x' = a x + c y + e."""

IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

MM_PER_UNIT = {
    "": 25.4 / 96.0,
    "px": 25.4 / 96.0,
    "pt": 25.4 / 72.0,
    "pc": 25.4 / 6.0,
    "in": 25.4,
    "cm": 10.0,
    "mm": 1.0,
    "q": 0.25,
}
"""Millimetres per length unit (CSS: 96 px to the inch)."""

SKIPPED = {
    "defs",
    "clipPath",
    "mask",
    "symbol",
    "marker",
    "pattern",
    "metadata",
    "title",
    "desc",
    "text",
    "image",
    "style",
    "script",
    "use",
    "linearGradient",
    "radialGradient",
    "filter",
    "namedview",
}
"""Elements whose content is not drawn geometry."""

_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_LENGTH = re.compile(
    r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([a-zA-Z%]*)\s*$"
)
_TRANSFORM = re.compile(r"([a-zA-Z]+)\s*\(([^)]*)\)")


@dataclass(frozen=True, slots=True)
class SvgShape:
    """One drawn element, flattened.

    Attributes:
        element_id: Its ``id`` ("" for none).
        label: Its name in the drawing program: ``inkscape:label`` or
            Illustrator's ``data-name`` ("" for none).
        groups: The ids and labels of the groups (layers) it sits in,
            outermost first.
        hidden: Whether it, or a group it sits in, is not displayed.
        subpaths: Its pieces, each a polyline in the document's
            millimetres (Y down, as SVG has it).
        closed: Whether each piece was closed.
        nodes: For each piece, the indices of its points that are the
            drawing's own nodes (where one curve or line of the path meets
            the next), its start first.
    """

    element_id: str
    label: str
    groups: tuple[str, ...]
    hidden: bool
    subpaths: tuple[tuple[Point2D, ...], ...]
    closed: tuple[bool, ...]
    nodes: tuple[tuple[int, ...], ...] = ()

    def names(self) -> tuple[str, ...]:
        """Return its own id and label."""
        return tuple(name for name in (self.element_id, self.label) if name)


@dataclass(frozen=True, slots=True)
class SvgImage:
    """A picture placed in the drawing (``<image>``).

    Attributes:
        element_id: Its ``id`` ("" for none).
        groups: The ids and labels of the groups (layers) it sits in.
        hidden: Whether it, or a group it sits in, is not displayed.
        matrix: Its user units to the document's millimetres.
        box: Its ``x``, ``y``, ``width`` and ``height``, in user units.
        stretched: Whether it fills its box (``preserveAspectRatio``
            "none"); else it is fitted in, centred.
        href: Its ``href``: a ``data:`` URI, or a file's name.
    """

    element_id: str
    groups: tuple[str, ...]
    hidden: bool
    matrix: Matrix
    box: tuple[float, float, float, float]
    stretched: bool
    href: str


def read_svg_shapes(text: str, tolerance: float = 0.05) -> tuple[SvgShape, ...]:
    """Return every drawn shape in an SVG document, in millimetres.

    Args:
        text: The SVG file's text.
        tolerance: How far a flattened curve may stray from the curve, in
            millimetres.

    Raises:
        DrawingError: If the text is not an SVG document.
    """
    return read_svg_drawing(text, tolerance)[0]


def read_svg_drawing(
    text: str, tolerance: float = 0.05
) -> tuple[tuple[SvgShape, ...], tuple[SvgImage, ...]]:
    """Return an SVG document's shapes (``read_svg_shapes``) and pictures.

    Raises:
        DrawingError: If the text is not an SVG document.
    """
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise DrawingError(f"This is not an SVG file ({error}).") from error
    if _local(root.tag) != "svg":
        raise DrawingError("This is not an SVG file (its root is not <svg>).")
    shapes: list[SvgShape] = []
    images: list[SvgImage] = []
    _walk(root, _document_matrix(root), (), False, tolerance, shapes, images, top=True)
    return tuple(shapes), tuple(images)


def _document_matrix(root: ElementTree.Element) -> Matrix:
    """Map the root's user units to millimetres, from its size and viewBox."""
    width = _length_mm(root.get("width"))
    height = _length_mm(root.get("height"))
    box = _numbers(root.get("viewBox", ""))
    if len(box) != 4 or box[2] <= 0.0 or box[3] <= 0.0:
        # No viewBox: user units are pixels.
        scale = MM_PER_UNIT["px"]
        return (scale, 0.0, 0.0, scale, 0.0, 0.0)
    min_x, min_y, box_width, box_height = box
    if width is None and height is None:
        scale_x = scale_y = MM_PER_UNIT["px"]
    elif width is None:
        assert height is not None
        scale_x = scale_y = height / box_height
    elif height is None:
        scale_x = scale_y = width / box_width
    else:
        scale_x, scale_y = width / box_width, height / box_height
    if root.get("preserveAspectRatio", "").strip() != "none":
        # xMidYMid meet: one scale, the box centred in the viewport.
        scale = min(scale_x, scale_y)
        shift_x = (box_width * (scale_x - scale)) / 2.0
        shift_y = (box_height * (scale_y - scale)) / 2.0
        return (
            scale,
            0.0,
            0.0,
            scale,
            shift_x - min_x * scale,
            shift_y - min_y * scale,
        )
    return (scale_x, 0.0, 0.0, scale_y, -min_x * scale_x, -min_y * scale_y)


def _length_mm(value: str | None) -> float | None:
    if not value:
        return None
    match = _LENGTH.match(value)
    if match is None or match.group(2) == "%":
        return None
    unit = match.group(2).lower()
    if unit not in MM_PER_UNIT:
        return None
    return float(match.group(1)) * MM_PER_UNIT[unit]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _hidden(element: ElementTree.Element) -> bool:
    style = element.get("style", "")
    declarations = {
        key.strip(): value.strip()
        for key, _, value in (part.partition(":") for part in style.split(";"))
    }
    return (
        element.get("display", declarations.get("display", "")) == "none"
        or element.get("visibility", declarations.get("visibility", "")) == "hidden"
    )


def _walk(
    element: ElementTree.Element,
    matrix: Matrix,
    groups: tuple[str, ...],
    hidden: bool,
    tolerance: float,
    shapes: list[SvgShape],
    images: list[SvgImage],
    top: bool = False,
) -> None:
    tag = _local(element.tag)
    if tag in SKIPPED and tag != "image":
        return
    hidden = hidden or _hidden(element)
    if not top:
        matrix = _multiply(matrix, _parse_transform(element.get("transform", "")))
    element_id = element.get("id", "")
    label = element.get(INKSCAPE_LABEL) or element.get("data-name") or ""
    if tag == "image":
        images.append(
            SvgImage(
                element_id,
                groups,
                hidden,
                matrix,
                (
                    _attribute_number(element, "x"),
                    _attribute_number(element, "y"),
                    _attribute_number(element, "width"),
                    _attribute_number(element, "height"),
                ),
                element.get("preserveAspectRatio", "").strip().startswith("none"),
                (element.get(XLINK_HREF) or element.get("href") or "").strip(),
            )
        )
        return
    if tag in ("svg", "g", "a", "switch") or top:
        names = tuple(name for name in (element_id, label) if name)
        for child in element:
            _walk(
                child,
                matrix,
                groups + names if not top else groups,
                hidden,
                tolerance,
                shapes,
                images,
            )
        return
    pieces = _element_pieces(tag, element)
    if not pieces:
        return
    subpaths: list[tuple[Point2D, ...]] = []
    closed: list[bool] = []
    nodes: list[tuple[int, ...]] = []
    for start, spans, is_closed in pieces:
        points = [_apply(matrix, start)]
        ends = [0]
        for span in spans:
            points.extend(
                flatten_span(
                    (
                        _apply(matrix, span[0]),
                        _apply(matrix, span[1]),
                        _apply(matrix, span[2]),
                        _apply(matrix, span[3]),
                    ),
                    tolerance,
                )
            )
            ends.append(len(points) - 1)
        subpaths.append(tuple(points))
        closed.append(is_closed)
        nodes.append(tuple(ends))
    shapes.append(
        SvgShape(
            element_id,
            label,
            groups,
            hidden,
            tuple(subpaths),
            tuple(closed),
            tuple(nodes),
        )
    )


Piece = tuple[Point2D, list[BezierSpan], bool]
"""A subpath: its start, its spans (lines as straight spans), closed."""


def _element_pieces(tag: str, element: ElementTree.Element) -> list[Piece]:
    number = _attribute_number
    if tag == "path":
        return parse_path(element.get("d", ""))
    if tag in ("polyline", "polygon"):
        values = _numbers(element.get("points", ""))
        points = [
            Point2D(x, y) for x, y in zip(values[::2], values[1::2], strict=False)
        ]
        if len(points) < 2:
            return []
        spans = [_line(a, b) for a, b in zip(points, points[1:], strict=False)]
        if tag == "polygon":
            spans.append(_line(points[-1], points[0]))
        return [(points[0], spans, tag == "polygon")]
    if tag == "line":
        a = Point2D(number(element, "x1"), number(element, "y1"))
        b = Point2D(number(element, "x2"), number(element, "y2"))
        return [(a, [_line(a, b)], False)]
    if tag == "rect":
        x, y = number(element, "x"), number(element, "y")
        width, height = number(element, "width"), number(element, "height")
        if width <= 0.0 or height <= 0.0:
            return []
        rx = element.get("rx")
        ry = element.get("ry")
        radius_x = number(element, "rx") if rx is not None else number(element, "ry")
        radius_y = number(element, "ry") if ry is not None else radius_x
        radius_x, radius_y = min(radius_x, width / 2.0), min(radius_y, height / 2.0)
        if radius_x <= 0.0 or radius_y <= 0.0:
            corners = [
                Point2D(x, y),
                Point2D(x + width, y),
                Point2D(x + width, y + height),
                Point2D(x, y + height),
            ]
            spans = [
                _line(a, b)
                for a, b in zip(corners, corners[1:] + corners[:1], strict=True)
            ]
            return [(corners[0], spans, True)]
        d = (
            f"M{x + radius_x},{y} H{x + width - radius_x} "
            f"A{radius_x},{radius_y} 0 0 1 {x + width},{y + radius_y} "
            f"V{y + height - radius_y} "
            f"A{radius_x},{radius_y} 0 0 1 {x + width - radius_x},{y + height} "
            f"H{x + radius_x} "
            f"A{radius_x},{radius_y} 0 0 1 {x},{y + height - radius_y} "
            f"V{y + radius_y} A{radius_x},{radius_y} 0 0 1 {x + radius_x},{y} Z"
        )
        return parse_path(d)
    if tag in ("circle", "ellipse"):
        cx, cy = number(element, "cx"), number(element, "cy")
        if tag == "circle":
            radius_x = radius_y = number(element, "r")
        else:
            radius_x, radius_y = number(element, "rx"), number(element, "ry")
        if radius_x <= 0.0 or radius_y <= 0.0:
            return []
        return parse_path(
            f"M{cx + radius_x},{cy} A{radius_x},{radius_y} 0 0 1 {cx},{cy + radius_y} "
            f"A{radius_x},{radius_y} 0 0 1 {cx - radius_x},{cy} "
            f"A{radius_x},{radius_y} 0 0 1 {cx},{cy - radius_y} "
            f"A{radius_x},{radius_y} 0 0 1 {cx + radius_x},{cy} Z"
        )
    return []


def _attribute_number(element: ElementTree.Element, name: str) -> float:
    """Return a coordinate attribute's number, in user units."""
    match = _LENGTH.match(element.get(name, ""))
    return float(match.group(1)) if match else 0.0


def _numbers(text: str) -> list[float]:
    return [float(value) for value in _NUMBER.findall(text)]


def _line(a: Point2D, b: Point2D) -> BezierSpan:
    return (a, a, b, b)


def parse_path(data: str) -> list[Piece]:
    """Return a path's ``d`` as subpaths of cubic spans, in its own units.

    Every command is read, absolute and relative: lines become straight
    spans, quadratics are raised to cubics and arcs are split into
    quarter-turn cubics.

    Raises:
        DrawingError: If the path data cannot be read.
    """
    tokens = _PathTokens(data)
    pieces: list[Piece] = []
    current = Point2D(0.0, 0.0)
    start = current
    spans: list[BezierSpan] = []
    closed = False
    last_control: Point2D | None = None
    last_command = ""

    def finish() -> None:
        nonlocal spans, closed
        if spans:
            pieces.append((spans[0][0], spans, closed))
        spans = []
        closed = False

    command = ""
    while True:
        token = tokens.command()
        if token is None:
            if tokens.at_end():
                break
            if not command or command in "Zz":
                raise DrawingError(f"Cannot read the path data near {tokens.rest()!r}.")
            # Implicit repetition (after a moveto, of lineto).
            token = {"M": "L", "m": "l"}.get(command, command)
        command = token
        relative = command.islower()
        upper = command.upper()
        origin = current if relative else Point2D(0.0, 0.0)

        def point() -> Point2D:
            x, y = tokens.number(), tokens.number()
            return Point2D(origin.x + x, origin.y + y)

        if upper == "M":
            finish()
            current = start = point()
            last_control = None
        elif upper == "Z":
            if current != start or not spans:
                spans.append(_line(current, start))
            closed = True
            current = start
            finish()
            last_control = None
        elif upper == "L":
            end = point()
            spans.append(_line(current, end))
            current = end
            last_control = None
        elif upper in "HV":
            value = tokens.number()
            if upper == "H":
                end = Point2D(value + (current.x if relative else 0.0), current.y)
            else:
                end = Point2D(current.x, value + (current.y if relative else 0.0))
            spans.append(_line(current, end))
            current = end
            last_control = None
        elif upper == "C":
            c1, c2, end = point(), point(), point()
            spans.append((current, c1, c2, end))
            current, last_control = end, c2
        elif upper == "S":
            c1 = (
                Point2D(2 * current.x - last_control.x, 2 * current.y - last_control.y)
                if last_control is not None and last_command.upper() in "CS"
                else current
            )
            c2, end = point(), point()
            spans.append((current, c1, c2, end))
            current, last_control = end, c2
        elif upper in "QT":
            if upper == "Q":
                control = point()
            else:
                control = (
                    Point2D(
                        2 * current.x - last_control.x, 2 * current.y - last_control.y
                    )
                    if last_control is not None and last_command.upper() in "QT"
                    else current
                )
            end = point()
            spans.append(
                (
                    current,
                    Point2D(
                        current.x + 2.0 / 3.0 * (control.x - current.x),
                        current.y + 2.0 / 3.0 * (control.y - current.y),
                    ),
                    Point2D(
                        end.x + 2.0 / 3.0 * (control.x - end.x),
                        end.y + 2.0 / 3.0 * (control.y - end.y),
                    ),
                    end,
                )
            )
            current, last_control = end, control
        elif upper == "A":
            radius_x, radius_y = abs(tokens.number()), abs(tokens.number())
            rotation = tokens.number()
            large, sweep = tokens.flag(), tokens.flag()
            end = point()
            spans.extend(_arc(current, end, radius_x, radius_y, rotation, large, sweep))
            current = end
            last_control = None
        else:
            raise DrawingError(f"Unknown path command {command!r}.")
        last_command = command
    finish()
    return pieces


class _PathTokens:
    """Commands, numbers and arc flags read off path data in turn."""

    def __init__(self, data: str) -> None:
        self.data = data
        self.index = 0

    def _skip(self) -> None:
        while self.index < len(self.data) and self.data[self.index] in " \t\r\n,":
            self.index += 1

    def at_end(self) -> bool:
        self._skip()
        return self.index >= len(self.data)

    def rest(self) -> str:
        return self.data[self.index : self.index + 20]

    def command(self) -> str | None:
        self._skip()
        if (
            self.index < len(self.data)
            and self.data[self.index] in "MmZzLlHhVvCcSsQqTtAa"
        ):
            self.index += 1
            return self.data[self.index - 1]
        return None

    def number(self) -> float:
        self._skip()
        match = _NUMBER.match(self.data, self.index)
        if match is None:
            raise DrawingError(f"Cannot read the path data near {self.rest()!r}.")
        self.index = match.end()
        return float(match.group())

    def flag(self) -> bool:
        self._skip()
        if self.index < len(self.data) and self.data[self.index] in "01":
            self.index += 1
            return self.data[self.index - 1] == "1"
        raise DrawingError(f"Cannot read an arc flag near {self.rest()!r}.")


def _arc(
    start: Point2D,
    end: Point2D,
    radius_x: float,
    radius_y: float,
    rotation_degrees: float,
    large: bool,
    sweep: bool,
) -> list[BezierSpan]:
    """Return an SVG elliptical arc as cubic spans of at most a quarter turn."""
    if start == end:
        return []
    if radius_x == 0.0 or radius_y == 0.0:
        return [_line(start, end)]
    phi = math.radians(rotation_degrees % 360.0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx, dy = (start.x - end.x) / 2.0, (start.y - end.y) / 2.0
    x1 = cos_phi * dx + sin_phi * dy
    y1 = -sin_phi * dx + cos_phi * dy
    # Radii too small to reach are scaled up (SVG's own rule).
    scale = (x1 * x1) / (radius_x * radius_x) + (y1 * y1) / (radius_y * radius_y)
    if scale > 1.0:
        radius_x *= math.sqrt(scale)
        radius_y *= math.sqrt(scale)
    numerator = radius_x**2 * radius_y**2 - radius_x**2 * y1**2 - radius_y**2 * x1**2
    denominator = radius_x**2 * y1**2 + radius_y**2 * x1**2
    factor = math.sqrt(max(0.0, numerator / denominator)) if denominator else 0.0
    if large == sweep:
        factor = -factor
    cx1 = factor * radius_x * y1 / radius_y
    cy1 = -factor * radius_y * x1 / radius_x
    cx = cos_phi * cx1 - sin_phi * cy1 + (start.x + end.x) / 2.0
    cy = sin_phi * cx1 + cos_phi * cy1 + (start.y + end.y) / 2.0

    def angle(ux: float, uy: float, vx: float, vy: float) -> float:
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    theta = angle(1.0, 0.0, (x1 - cx1) / radius_x, (y1 - cy1) / radius_y)
    delta = angle(
        (x1 - cx1) / radius_x,
        (y1 - cy1) / radius_y,
        (-x1 - cx1) / radius_x,
        (-y1 - cy1) / radius_y,
    )
    if not sweep and delta > 0.0:
        delta -= 2.0 * math.pi
    elif sweep and delta < 0.0:
        delta += 2.0 * math.pi
    count = max(1, math.ceil(abs(delta) / (math.pi / 2.0) - 1e-9))
    step = delta / count
    handle = 4.0 / 3.0 * math.tan(step / 4.0)

    def on_ellipse(t: float) -> tuple[Point2D, tuple[float, float]]:
        cos_t, sin_t = math.cos(t), math.sin(t)
        point = Point2D(
            cx + radius_x * cos_phi * cos_t - radius_y * sin_phi * sin_t,
            cy + radius_x * sin_phi * cos_t + radius_y * cos_phi * sin_t,
        )
        derivative = (
            -radius_x * cos_phi * sin_t - radius_y * sin_phi * cos_t,
            -radius_x * sin_phi * sin_t + radius_y * cos_phi * cos_t,
        )
        return point, derivative

    spans: list[BezierSpan] = []
    for index in range(count):
        t0 = theta + index * step
        p0, d0 = on_ellipse(t0)
        p1, d1 = on_ellipse(t0 + step)
        if index == 0:
            p0 = start
        if index == count - 1:
            p1 = end
        spans.append(
            (
                p0,
                Point2D(p0.x + handle * d0[0], p0.y + handle * d0[1]),
                Point2D(p1.x - handle * d1[0], p1.y - handle * d1[1]),
                p1,
            )
        )
    return spans


def _parse_transform(text: str) -> Matrix:
    matrix = IDENTITY
    for name, arguments in _TRANSFORM.findall(text):
        values = _numbers(arguments)
        step: Matrix
        if name == "matrix" and len(values) == 6:
            step = (values[0], values[1], values[2], values[3], values[4], values[5])
        elif name == "translate" and values:
            step = (
                1.0,
                0.0,
                0.0,
                1.0,
                values[0],
                values[1] if len(values) > 1 else 0.0,
            )
        elif name == "scale" and values:
            step = (
                values[0],
                0.0,
                0.0,
                values[1] if len(values) > 1 else values[0],
                0.0,
                0.0,
            )
        elif name == "rotate" and values:
            a = math.radians(values[0])
            cos_a, sin_a = math.cos(a), math.sin(a)
            step = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
            if len(values) == 3:
                cx, cy = values[1], values[2]
                step = _multiply(
                    _multiply((1.0, 0.0, 0.0, 1.0, cx, cy), step),
                    (1.0, 0.0, 0.0, 1.0, -cx, -cy),
                )
        elif name == "skewX" and values:
            step = (1.0, 0.0, math.tan(math.radians(values[0])), 1.0, 0.0, 0.0)
        elif name == "skewY" and values:
            step = (1.0, math.tan(math.radians(values[0])), 0.0, 1.0, 0.0, 0.0)
        else:
            continue
        matrix = _multiply(matrix, step)
    return matrix


def _multiply(m: Matrix, n: Matrix) -> Matrix:
    """Return ``m`` after ``n``: a point is mapped by ``n`` first."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    )


def apply_matrix(matrix: Matrix, point: Point2D) -> Point2D:
    """Return a point mapped by an SVG matrix."""
    return _apply(matrix, point)


def _apply(matrix: Matrix, point: Point2D) -> Point2D:
    a, b, c, d, e, f = matrix
    return Point2D(a * point.x + c * point.y + e, b * point.x + d * point.y + f)


def shape_points(shape: SvgShape) -> Iterator[Point2D]:
    """Yield every point of every piece of a shape."""
    for subpath in shape.subpaths:
        yield from subpath
