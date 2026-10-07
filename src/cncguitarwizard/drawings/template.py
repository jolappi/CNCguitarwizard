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
from .exceptions import DrawingError
from .svg_reader import SvgShape, read_svg_shapes

REFERENCE_LAYER = "cgwReference"
"""The reference layer's id: nothing in it is read back but the marks."""

OUTLINE_LAYER = "cgwOutlineLayer"
OUTLINE_ID = "cgwOutline"
"""The outline path's id: read back first when it is still there."""

MARK_IDS = ("cgwMarkA", "cgwMarkB", "cgwMarkC")
"""The registration marks' ids, in the order of ``TemplateFrame.marks``."""

MARK_SIZE = 4.0
"""A registration mark's half-width, in mm."""

CLOSE_GAP = 3.0
"""How far apart (mm) an outline's ends may be and still close."""


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
) -> str:
    """Return the template: the reference layer and the outline to edit.

    Args:
        title: The document's title.
        frame: Where the model goes on the page, and its marks.
        outline: The outline as Bézier spans end to end, closed.
        references: What the outline is drawn round.
        notes: Lines of text written under the drawing, in the reference
            layer (what to edit, and what to keep).
    """

    def xy(point: Point2D) -> str:
        x, y = frame.to_svg(point)
        return f"{x:.3f},{y:.3f}"

    corners: list[tuple[float, float]] = [frame.to_svg(p) for s in outline for p in s]
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
    width = max(x for x, _ in corners) + margin - min_x
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
            f'style="font-family:sans-serif;font-size:3.5px;fill:#555">'
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
    else the largest closed shape outside the reference layer (an outline
    drawn anew); its ends may be up to ``CLOSE_GAP`` apart.

    Raises:
        DrawingError: If it is not an SVG file, a registration mark is
            missing, or there is no closed outline.
    """
    shapes = read_svg_shapes(text)
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
    matrix = _affine(found, frame.marks)
    a, b, c, d, _, _ = matrix
    scale = 1.0 / math.sqrt(abs(a * d - b * c))
    outside = [
        shape
        for shape in shapes
        if not shape.hidden
        and not any(_named_group(group) for group in shape.groups)
        and not any(_named(shape, mark_id) for mark_id in MARK_IDS)
    ]
    named = [shape for shape in outside if _named(shape, OUTLINE_ID)]
    candidates = []
    for shape in named or outside:
        for points, closed, nodes in zip(
            shape.subpaths,
            shape.closed,
            shape.nodes or ((),) * len(shape.subpaths),
            strict=True,
        ):
            mapped = [_apply(matrix, point) for point in points]
            if len(mapped) > 1 and _gap(mapped) < 1e-6:
                mapped.pop()
            if len(mapped) < 3 or (not closed and _gap(mapped) > CLOSE_GAP):
                continue
            kept = tuple(sorted({index % len(mapped) for index in nodes}))
            candidates.append((abs(_area(mapped)), tuple(mapped), kept))
    if not candidates:
        raise DrawingError(
            "There is no closed outline in the drawing: draw it as one closed "
            "path in the Outline layer."
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    largest, points, nodes = candidates[0]
    ignored = sum(1 for area, _, _ in candidates[1:] if area > 0.01 * largest)
    return ReadOutline(points, scale, ignored, nodes)


def _gap(points: Sequence[Point2D]) -> float:
    return math.hypot(points[0].x - points[-1].x, points[0].y - points[-1].y)


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
