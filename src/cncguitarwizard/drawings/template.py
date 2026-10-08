"""An editor's outline as an SVG template, and the outline read back.

The template is drawn 1:1 in millimetres in two layers: *Reference*,
locked, with what the outline is drawn round (the neck, routes and
cavities, or the nut and tuner holes) and three registration marks; and
*Outline*, the one path to edit, a node at every handle the editor has.
Read back, the marks place the drawing: whatever the other program did
to its units, its page or its position (pixels at 72 or 96 to the inch,
a page grown round the drawing, the whole drawing moved), the outline
comes back in the model's own millimetres.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from xml.sax.saxutils import escape, quoteattr

from ..geometry.primitives import BezierSpan, Point2D
from .bitmap import MAX_CELLS, picture_bytes, png_ink, traced_outlines
from .exceptions import DrawingError
from .svg_reader import (
    SvgImage,
    SvgShape,
    apply_matrix,
    read_svg_drawing,
    read_svg_shapes,
)

REFERENCE_LAYER = "cgwReference"
"""The reference layer's id: nothing in it is read back but the marks."""

PATTERN_LAYER = "cgwPatternLayer"
"""The pattern layer's id: lines engraved into the top (a body's)."""

OUTLINE_LAYER = "cgwOutlineLayer"
OUTLINE_ID = "cgwOutline"
"""The outline path's id: read back first when it is still there."""

MARK_IDS = ("cgwMarkA", "cgwMarkB", "cgwMarkC")
"""The registration marks' ids, in the order of ``TemplateFrame.marks``."""

MARK_SIZE = 4.0
"""A registration mark's half-width, in mm."""

CLOSE_GAP = 3.0
"""How far apart (mm) an outline's ends may be and still close."""

NOTE_SIZE = 3.5
"""The notes' letter size under the drawing, in mm."""


@dataclass(frozen=True, slots=True)
class TemplateFrame:
    """Where a template's model coordinates go in its SVG.

    Attributes:
        marks: The three registration marks' model positions, not in a line.
        mirrored: Whether +Y is drawn downward (a left-handed design,
            shown mirrored as the editor shows it); else +Y is up.
    """

    marks: tuple[Point2D, Point2D, Point2D]
    mirrored: bool = False

    def to_svg(self, point: Point2D) -> tuple[float, float]:
        """Return a model point's SVG coordinates (millimetres, Y down)."""
        return (point.x, point.y if self.mirrored else -point.y)


@dataclass(frozen=True, slots=True)
class ReferenceShape:
    """Something drawn on the reference layer, for the outline to go round.

    Attributes:
        name: What it is, shown as its title (the neck pocket, say).
        points: A polygon or polyline in the model frame; for a circle its
            centre alone.
        closed: Whether ``points`` close into a polygon.
        radius: A circle's radius; 0 for a polygon or polyline.
        colour: Its stroke colour.
        dashed: Whether it is drawn dashed (a clearance, say).
    """

    name: str
    points: tuple[Point2D, ...]
    closed: bool = True
    radius: float = 0.0
    colour: str = "#4a7ab5"
    dashed: bool = False


def template_svg(
    title: str,
    frame: TemplateFrame,
    outline: Sequence[BezierSpan],
    references: Sequence[ReferenceShape],
    notes: Sequence[str] = (),
    pattern: Sequence[Sequence[Point2D]] | None = None,
) -> str:
    """Return the template: the reference layer and the outline to edit.

    Args:
        title: The document's title.
        frame: Where the model goes on the page, and its marks.
        outline: The outline as Bézier spans end to end, closed.
        references: What the outline is drawn round.
        notes: Lines of text written under the drawing, in the reference
            layer (what to edit, and what to keep).
        pattern: Lines engraved into the top, written in their own layer
            *Pattern* to be drawn on (empty for none yet); ``None`` for no
            such layer.
    """

    def xy(point: Point2D) -> str:
        x, y = frame.to_svg(point)
        return f"{x:.3f},{y:.3f}"

    corners: list[tuple[float, float]] = [frame.to_svg(p) for s in outline for p in s]
    corners += [frame.to_svg(p) for line in pattern or () for p in line]
    for shape in references:
        for point in shape.points:
            x, y = frame.to_svg(point)
            corners += [
                (x - shape.radius, y - shape.radius),
                (x + shape.radius, y + shape.radius),
            ]
    for mark in frame.marks:
        x, y = frame.to_svg(mark)
        corners += [(x - MARK_SIZE, y - MARK_SIZE), (x + MARK_SIZE, y + MARK_SIZE)]
    margin = 15.0
    line_height = 5.0
    min_x = min(x for x, _ in corners) - margin
    min_y = min(y for _, y in corners) - margin
    # Wide enough for the notes under a small drawing too (a sans-serif
    # letter is about 0.55 of its size wide).
    width = max(
        max(x for x, _ in corners) + margin - min_x,
        2.0 * margin + 0.55 * NOTE_SIZE * max((len(note) for note in notes), default=0),
    )
    height = max(y for _, y in corners) + margin - min_y + line_height * len(notes)

    reference = []
    for index, (mark_id, mark) in enumerate(zip(MARK_IDS, frame.marks, strict=True)):
        x, y = frame.to_svg(mark)
        s, r = MARK_SIZE, MARK_SIZE * 0.6
        reference.append(
            f'    <path id="{mark_id}" style="fill:none;stroke:#d33;stroke-width:0.3" '
            f'd="M{x - s:.3f},{y:.3f} H{x + s:.3f} M{x:.3f},{y - s:.3f} V{y + s:.3f} '
            f"M{x + r:.3f},{y:.3f} A{r},{r} 0 1 1 {x - r:.3f},{y:.3f} "
            f'A{r},{r} 0 1 1 {x + r:.3f},{y:.3f}">'
            f"<title>Registration mark {'ABC'[index]}: keep it</title></path>"
        )
    for shape in references:
        style = f"fill:none;stroke:{shape.colour};stroke-width:0.3" + (
            ";stroke-dasharray:1.5,1" if shape.dashed else ""
        )
        title_tag = f"<title>{escape(shape.name)}</title>"
        if shape.radius > 0.0:
            x, y = frame.to_svg(shape.points[0])
            reference.append(
                f'    <circle cx="{x:.3f}" cy="{y:.3f}" r="{shape.radius:.3f}" '
                f'style="{style}">{title_tag}</circle>'
            )
        else:
            d = "M" + " L".join(xy(point) for point in shape.points)
            reference.append(
                f'    <path d="{d}{" Z" if shape.closed else ""}" '
                f'style="{style}">{title_tag}</path>'
            )
    for index, note in enumerate(notes):
        baseline = min_y + height - margin / 2 - line_height * (len(notes) - 1 - index)
        reference.append(
            f'    <text x="{min_x + margin:.3f}" y="{baseline:.3f}" '
            f'style="font-family:sans-serif;font-size:{NOTE_SIZE:g}px;fill:#555">'
            f"{escape(note)}</text>"
        )
    d = (
        "M"
        + xy(outline[0][0])
        + " "
        + " ".join(f"C{xy(b)} {xy(c)} {xy(e)}" for _, b, c, e in outline)
        + " Z"
    )
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg"',
            '     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"',
            '     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"',
            f'     width="{width:.3f}mm" height="{height:.3f}mm"',
            f'     viewBox="{min_x:.3f} {min_y:.3f} {width:.3f} {height:.3f}">',
            f"  <title>{escape(title)}</title>",
            f'  <g id="{REFERENCE_LAYER}" inkscape:groupmode="layer" '
            'inkscape:label="Reference" sodipodi:insensitive="true">',
            *reference,
            "  </g>",
            *(
                (
                    f'  <g id="{PATTERN_LAYER}" inkscape:groupmode="layer" '
                    'inkscape:label="Pattern">',
                    *(
                        '    <path style="fill:none;stroke:#1a5fb4;'
                        'stroke-width:0.4" d="M'
                        + " L".join(xy(point) for point in line)
                        + '"/>'
                        for line in pattern
                        if len(line) >= 2
                    ),
                    "  </g>",
                )
                if pattern is not None
                else ()
            ),
            f'  <g id="{OUTLINE_LAYER}" inkscape:groupmode="layer" '
            'inkscape:label="Outline">',
            f'    <path id="{OUTLINE_ID}" style="fill:none;stroke:#000;'
            f'stroke-width:0.5" d={quoteattr(d)}/>',
            "  </g>",
            "</svg>",
            "",
        ]
    )


@dataclass(frozen=True, slots=True)
class ReadOutline:
    """An outline read back from a template.

    Attributes:
        points: The outline in the model frame, closed (its last point
            not repeating its first).
        scale: How much the other program had scaled the drawing, read
            off the marks (1 for none: a 72-dpi program's pixels give
            0.75 or 1.33).
        ignored: How many other closed shapes outside the reference layer
            were left out (the largest outline is the one read).
        nodes: The indices of ``points`` that are the drawing's own nodes.
    """

    points: tuple[Point2D, ...]
    scale: float
    ignored: int
    nodes: tuple[int, ...] = ()


def read_template_outline(text: str, frame: TemplateFrame) -> ReadOutline:
    """Return the outline drawn in a template, in the model frame.

    The outline is the path still named ``cgwOutline`` when there is one,
    else the largest closed shape outside the reference and pattern layers
    (an outline drawn anew); its ends may be up to ``CLOSE_GAP`` apart.
    ``ignored`` counts the other shapes beside it (``read_template_pattern``
    reads them into the pattern).

    Raises:
        DrawingError: If it is not an SVG file, a registration mark is
            missing, or there is no closed outline.
    """
    shapes = read_svg_shapes(text)
    matrix = _affine(_mark_centres(shapes), frame.marks)
    a, b, c, d, _, _ = matrix
    scale = 1.0 / math.sqrt(abs(a * d - b * c))
    choice = _outline_choice(shapes, matrix)
    if choice is None:
        raise DrawingError(
            "There is no closed outline in the drawing: draw it as one closed "
            "path in the Outline layer."
        )
    _, _, points, nodes = choice
    beside = len(_beside(shapes, matrix, choice))
    return ReadOutline(points, scale, beside, nodes)


Choice = tuple[int, int, tuple[Point2D, ...], tuple[int, ...]]
"""The outline's shape and piece (indices), its points and its nodes."""


def _drawn(shapes: Sequence[SvgShape]) -> list[int]:
    """Return the shapes outside the reference and pattern layers (indices)."""
    return [
        index
        for index, shape in enumerate(shapes)
        if not shape.hidden
        and not any(_named_group(group) or _in_pattern(group) for group in shape.groups)
        and not any(_named(shape, mark_id) for mark_id in MARK_IDS)
    ]


def _outline_choice(shapes: Sequence[SvgShape], matrix: Affine) -> Choice | None:
    """Return the outline among the drawn shapes (see
    ``read_template_outline``), or ``None``."""
    drawn = _drawn(shapes)
    named = [index for index in drawn if _named(shapes[index], OUTLINE_ID)]
    best: tuple[float, Choice] | None = None
    for index in named or drawn:
        shape = shapes[index]
        for piece, (points, closed, nodes) in enumerate(
            zip(
                shape.subpaths,
                shape.closed,
                shape.nodes or ((),) * len(shape.subpaths),
                strict=True,
            )
        ):
            mapped = [_apply(matrix, point) for point in points]
            if len(mapped) > 1 and _gap(mapped) < 1e-6:
                mapped.pop()
            if len(mapped) < 3 or (not closed and _gap(mapped) > CLOSE_GAP):
                continue
            kept = tuple(sorted({node % len(mapped) for node in nodes}))
            area = abs(_area(mapped))
            if best is None or area > best[0]:
                best = (area, (index, piece, tuple(mapped), kept))
    return best[1] if best is not None else None


def _beside(
    shapes: Sequence[SvgShape], matrix: Affine, choice: Choice | None
) -> list[tuple[Point2D, ...]]:
    """Return every drawn piece but the outline, as lines in the model
    (a closed one ending where it began)."""
    lines = []
    for index in _drawn(shapes):
        shape = shapes[index]
        for piece, (points, closed) in enumerate(
            zip(shape.subpaths, shape.closed, strict=True)
        ):
            if choice is not None and (index, piece) == choice[:2]:
                continue
            mapped = [_apply(matrix, point) for point in points]
            if closed and mapped and _gap(mapped) > 1e-6:
                mapped.append(mapped[0])
            if len(mapped) >= 2:
                lines.append(tuple(mapped))
    return lines


def _gap(points: Sequence[Point2D]) -> float:
    return math.hypot(points[0].x - points[-1].x, points[0].y - points[-1].y)


@dataclass(frozen=True, slots=True)
class ReadPattern:
    """A body's pattern read back from its template.

    Attributes:
        lines: The lines to engrave, in the model frame.
        beside: How many of them were shapes drawn beside the outline,
            outside the *Pattern* layer.
        pictures: How many pictures were traced into them.
        untraced: Why each picture that could not be traced was not.
    """

    lines: tuple[tuple[Point2D, ...], ...]
    beside: int = 0
    pictures: int = 0
    untraced: tuple[str, ...] = ()


def read_template_pattern(
    text: str, frame: TemplateFrame, tolerance: float | None = 0.05
) -> ReadPattern | None:
    """Return the pattern drawn in a template, or ``None``.

    Every visible shape in the *Pattern* layer, every shape drawn beside
    the outline outside it (in the Outline layer, say), and every picture
    outside the reference layer, its dark shapes traced
    (``bitmap.traced_outlines``): each piece a line in the model frame (a
    closed one ending where it began), placed by the registration marks
    and thinned to within ``tolerance`` of itself (``None``: every point
    kept; a traced picture's, to within three quarters of its traced
    cells, smoothing their steps). ``None`` where there is none of these
    and no *Pattern* layer (taken out: the pattern is left as it was).

    Raises:
        DrawingError: If it is not an SVG file or a registration mark is
            missing.
    """
    shapes, images = read_svg_drawing(text)
    matrix = _affine(_mark_centres(shapes), frame.marks)
    layered = [s for s in shapes if any(_in_pattern(group) for group in s.groups)]
    lines: list[tuple[Point2D, ...]] = []
    for shape in layered:
        if shape.hidden:
            continue
        for points, closed in zip(shape.subpaths, shape.closed, strict=True):
            mapped = [_apply(matrix, point) for point in points]
            if closed and mapped and _gap(mapped) > 1e-6:
                mapped.append(mapped[0])
            if len(mapped) >= 2:
                lines.append(tuple(mapped))
    beside = _beside(shapes, matrix, _outline_choice(shapes, matrix))
    lines += beside
    pictures = 0
    untraced: list[str] = []
    for image in images:
        if image.hidden or any(_named_group(group) for group in image.groups):
            continue
        try:
            traced = _traced(image, matrix)
        except DrawingError as error:
            untraced.append(str(error))
            continue
        pictures += 1
        lines += traced
    if not lines and not untraced and not _has_pattern_layer(text):
        return None
    if tolerance is not None:
        lines = [line if len(line) <= 3 else thinned(line, tolerance) for line in lines]
    return ReadPattern(tuple(lines), len(beside), pictures, tuple(untraced))


def _traced(image: SvgImage, matrix: Affine) -> list[tuple[Point2D, ...]]:
    """Return a picture's dark shapes traced, as lines in the model."""
    width, height, ink = png_ink(picture_bytes(image.href))
    x, y, box_width, box_height = image.box
    if image.stretched:
        scale_x, scale_y = box_width / width, box_height / height
        left, top = x, y
    else:
        scale_x = scale_y = min(box_width / width, box_height / height)
        left = x + (box_width - width * scale_x) / 2.0
        top = y + (box_height - height * scale_y) / 2.0

    def placed(u: float, v: float) -> Point2D:
        document = apply_matrix(
            image.matrix, Point2D(left + u * scale_x, top + v * scale_y)
        )
        return _apply(matrix, document)

    loops = traced_outlines(width, height, ink)
    if not loops:
        return []
    # A traced cell's size in the model, to smooth the steps by.
    block = max(1, -(-max(width, height) // MAX_CELLS))
    corner, along = placed(0.0, 0.0), placed(float(block), 0.0)
    cell = math.hypot(along.x - corner.x, along.y - corner.y)
    return [thinned([placed(u, v) for u, v in loop], 0.75 * cell) for loop in loops]


def thinned(points: Sequence[Point2D], tolerance: float) -> tuple[Point2D, ...]:
    """Return a line without the points it can do without (Douglas-Peucker):
    the rest keeps within ``tolerance`` of it."""
    if len(points) < 3:
        return tuple(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        a, b = points[first], points[last]
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy)
        worst, index = 0.0, -1
        for i in range(first + 1, last):
            p = points[i]
            if length < 1e-12:
                distance = math.hypot(p.x - a.x, p.y - a.y)
            else:
                distance = abs((p.x - a.x) * dy - (p.y - a.y) * dx) / length
            if distance > worst:
                worst, index = distance, i
        if index >= 0 and worst > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return tuple(p for p, kept in zip(points, keep, strict=True) if kept)


def _in_pattern(group: str) -> bool:
    return group.startswith(PATTERN_LAYER) or group.strip().lower() == "pattern"


def _has_pattern_layer(text: str) -> bool:
    return PATTERN_LAYER in text or 'label="Pattern"' in text


def _mark_centres(shapes: Sequence[SvgShape]) -> list[Point2D]:
    """Return the three registration marks' centres, in order."""
    found = []
    for mark_id in MARK_IDS:
        mark = next((s for s in shapes if _named(s, mark_id)), None)
        if mark is None:
            raise DrawingError(
                f"The registration mark {mark_id} is missing: keep the template's "
                "Reference layer, with its three red marks, in the file (they "
                "place the drawing to the millimetre)."
            )
        xs = [p.x for sub in mark.subpaths for p in sub]
        ys = [p.y for sub in mark.subpaths for p in sub]
        found.append(Point2D((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0))
    return found


def _named(shape: SvgShape, name: str) -> bool:
    return any(own.startswith(name) for own in shape.names())


def _named_group(group: str) -> bool:
    return group.startswith(REFERENCE_LAYER) or group.strip().lower() == "reference"


Affine = tuple[float, float, float, float, float, float]


def _affine(source: Sequence[Point2D], target: Sequence[Point2D]) -> Affine:
    """Return the affine map taking three source points onto three targets."""
    (x1, y1), (x2, y2), (x3, y3) = ((p.x, p.y) for p in source)
    determinant = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if abs(determinant) < 1e-6:
        raise DrawingError(
            "The registration marks lie in a line or on top of each other: "
            "keep them where the template put them, or move them only with the "
            "whole drawing."
        )

    def solve(u1: float, u2: float, u3: float) -> tuple[float, float, float]:
        # u = p x + q y + r through the three points.
        p = ((u2 - u1) * (y3 - y1) - (u3 - u1) * (y2 - y1)) / determinant
        q = ((x2 - x1) * (u3 - u1) - (x3 - x1) * (u2 - u1)) / determinant
        return p, q, u1 - p * x1 - q * y1

    a, c, e = solve(*(p.x for p in target))
    b, d, f = solve(*(p.y for p in target))
    return (a, b, c, d, e, f)


def _apply(matrix: Affine, point: Point2D) -> Point2D:
    a, b, c, d, e, f = matrix
    return Point2D(a * point.x + c * point.y + e, b * point.x + d * point.y + f)


def _area(points: Sequence[Point2D]) -> float:
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )
