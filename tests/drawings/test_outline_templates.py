"""Tests for the outline templates: written out, read back, fitted."""

import dataclasses
import math

import pytest

from cncguitarwizard.drawings import (
    DrawingError,
    TemplateFrame,
    fit_closed_spline,
    fit_headstock,
    read_template_outline,
    read_template_pattern,
    template_svg,
)
from cncguitarwizard.drawings.outlines import headstock_spans
from cncguitarwizard.geometry.primitives import (
    Point2D,
    SmoothCurve,
    bezier_point,
    closed_catmull_rom,
    closed_catmull_rom_spans,
    smooth_curve_spans,
)
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import NECK_TEMPLATES
from cncguitarwizard.webapp import _coerce, _jsonable

BODY = TemplateFrame((Point2D(0, 0), Point2D(100, 0), Point2D(0, 100)))
HEADSTOCK = TemplateFrame((Point2D(0, 0), Point2D(-100, 0), Point2D(0, 50)))


def _body_svg(points: list[Point2D]) -> str:
    return template_svg("body", BODY, closed_catmull_rom_spans(points), [])


def _wrapped(svg: str, transform: str) -> str:
    """The whole drawing moved and scaled, as another program saves it."""
    return svg.replace(
        '  <g id="cgwReference"', f'  <g transform="{transform}"><g id="cgwReference"'
    ).replace("</svg>", "</g></svg>")


def test_the_curves_are_exact_bezier_spans() -> None:
    points = [Point2D(0, 0), Point2D(40, 5), Point2D(60, 40), Point2D(10, 50)]
    sampled = closed_catmull_rom(points, 4)
    spans = closed_catmull_rom_spans(points)
    for index, span in enumerate(spans):
        for step in range(4):
            expected = sampled[index * 4 + step]
            got = bezier_point(span, step / 4)
            assert (got.x, got.y) == pytest.approx((expected.x, expected.y))
    curve = SmoothCurve(((0, 21), (40, 30), (150, 24)))
    for span in smooth_curve_spans(curve):
        for t in (0.25, 0.5, 0.75):
            point = bezier_point(span, t)
            assert point.y == pytest.approx(curve.value_at(point.x))


@pytest.mark.parametrize("key", list(YOUR_DESIGN_TEMPLATES))
def test_a_body_template_read_back_unchanged_is_the_same_body(key: str) -> None:
    points = [Point2D(x, y) for x, y in YOUR_DESIGN_TEMPLATES[key][1].control_points]
    # Moved and scaled to 72 pixels to the inch, as Illustrator saves it.
    for svg in (
        _body_svg(points),
        _wrapped(_body_svg(points), "translate(30 40) scale(0.75)"),
    ):
        read = read_template_outline(svg, BODY)
        fit = fit_closed_spline(read.points, read.nodes)
        assert [(round(p.x, 6), round(p.y, 6)) for p in fit.points] == [
            (round(p.x, 6), round(p.y, 6)) for p in points
        ]
    assert read.scale == pytest.approx(0.75)


def test_a_body_drawn_with_few_nodes_or_as_a_polyline_is_fitted_close() -> None:
    points = [
        Point2D(x, y)
        for x, y in YOUR_DESIGN_TEMPLATES["stratocaster"][1].control_points
    ]
    # A smooth path with a third of the nodes: its nodes are the handles.
    few = fit_closed_spline(*_read(_body_svg(points[::3])))
    assert len(few.points) == len(points[::3]) and few.deviation <= 0.25
    # A polyline's nodes are no handles: as many as keep it within 0.25 mm.
    polyline = closed_catmull_rom(points, 8)
    spans = [(a, a, b, b) for a, b in zip(polyline, (*polyline[1:], polyline[0]))]
    read = read_template_outline(template_svg("body", BODY, spans, []), BODY)
    fit = fit_closed_spline(read.points, read.nodes)
    assert fit.deviation <= 0.3 and len(fit.points) < len(polyline) / 3


def _read(svg: str) -> tuple:  # type: ignore[type-arg]
    read = read_template_outline(svg, BODY)
    return read.points, read.nodes


def test_an_outline_drawn_anew_is_the_largest_closed_shape() -> None:
    points = [
        Point2D(x, y) for x, y in ((0, -50), (300, -150), (450, 0), (300, 150), (0, 50))
    ]
    svg = _body_svg(points).replace('id="cgwOutline" ', "")
    svg = svg.replace(
        "  </g>\n</svg>",
        '    <circle cx="200" cy="0" r="40"/><path d="M0 0 H5"/>\n  </g>\n</svg>',
    )
    read = read_template_outline(svg, BODY)
    # The circle and the line beside it are no outline (they are read
    # into the pattern).
    assert read.ignored == 2
    assert max(p.x for p in read.points) == pytest.approx(450, abs=0.1)
    beside = read_template_pattern(svg, BODY)
    assert beside is not None and beside.beside == 2 and len(beside.lines) == 2


def test_a_template_without_its_marks_or_an_outline_is_refused() -> None:
    svg = _body_svg([Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10)])
    with pytest.raises(DrawingError, match="registration mark cgwMarkB is missing"):
        read_template_outline(svg.replace('id="cgwMarkB"', 'id="other"'), BODY)
    start = svg.index('<path id="cgwOutline"')
    end = svg.index("/>", start) + 2
    # An open line is no outline (ends more than 3 mm apart).
    open_line = (
        svg[:start] + '<path id="cgwOutline" d="M0 0 L50 0 L50 50"/>' + svg[end:]
    )
    with pytest.raises(DrawingError, match="no closed outline"):
        read_template_outline(open_line, BODY)


def _headstocks() -> dict[str, Prototype001Parameters]:
    base = Prototype001Parameters()
    found = {}
    for key, (_, values) in NECK_TEMPLATES.items():
        parameters = dataclasses.replace(base, **_coerce(_jsonable(values)))
        if parameters.headstock_bass_edge:
            found[key] = parameters
    return found


@pytest.mark.parametrize("key", list(_headstocks()))
def test_a_headstock_read_back_unchanged_is_the_same_headstock(key: str) -> None:
    parameters = _headstocks()[key]
    plan = parameters.headstock_plan()
    svg = template_svg(key, HEADSTOCK, headstock_spans(plan), [])
    for drawing in (svg, _wrapped(svg, "translate(-20 15) scale(1.3333)")):
        read = read_template_outline(drawing, HEADSTOCK)
        fit = fit_headstock(
            read.points, parameters.nut_width / 2, plan.bass_sign, read.nodes
        )
        for got, expected in (
            (fit.bass_edge, plan.bass_edge),
            (fit.treble_edge, plan.treble_edge),
            (fit.tip_points, plan.tip_points),
        ):
            assert _flat(got) == pytest.approx(_flat(expected), abs=0.011)


def _flat(points: tuple) -> list[float]:  # type: ignore[type-arg]
    return [value for point in points or () for value in point]


def _headstock(bass: tuple, treble: tuple, tip: tuple = ()) -> Prototype001Parameters:  # type: ignore[type-arg]
    return dataclasses.replace(
        Prototype001Parameters(),
        headstock_outline="drawn",
        headstock_bass_edge=bass,
        headstock_treble_edge=treble,
        headstock_tip_points=tip,
    )


def test_a_headstock_edited_elsewhere_comes_back_as_drawn() -> None:
    parameters = _headstock(
        ((40.0, 30.0), (150.0, 24.0)), ((40.0, 30.0), (150.0, 24.0))
    )
    plan = parameters.headstock_plan()
    svg = template_svg("h", HEADSTOCK, headstock_spans(plan), [])
    longer = svg.replace(
        '<path id="cgwOutline"', '<path id="cgwOutline" transform="scale(1.1 1)"'
    )
    read = read_template_outline(longer, HEADSTOCK)
    fit = fit_headstock(
        read.points, parameters.nut_width / 2, plan.bass_sign, read.nodes
    )
    assert fit.bass_edge[-1] == pytest.approx((165.0, 24.0), abs=0.02)
    assert fit.deviation <= 0.25
    rebuilt = dataclasses.replace(
        parameters,
        headstock_bass_edge=fit.bass_edge,
        headstock_treble_edge=fit.treble_edge,
    ).headstock_plan()
    assert rebuilt.length == pytest.approx(165.0, abs=0.02)


def test_a_pointed_headstock_and_a_hooked_tip() -> None:
    # Edges meeting at the tip: a pointed headstock, no tip points.
    pointed = _headstock(
        ((40.0, 30.0), (120.0, 25.0), (180.0, 0.0)),
        ((40.0, 30.0), (120.0, 25.0), (180.0, 0.0)),
    )
    plan = pointed.headstock_plan()
    assert plan.pointed
    read = read_template_outline(
        template_svg("p", HEADSTOCK, headstock_spans(plan), []), HEADSTOCK
    )
    fit = fit_headstock(read.points, pointed.nut_width / 2, plan.bass_sign, read.nodes)
    assert fit.tip_points == () and fit.bass_edge[-1][0] == fit.treble_edge[-1][0]
    assert abs(fit.bass_edge[-1][1] + fit.treble_edge[-1][1]) < 1.0
    # An ear hooking back toward the nut past the tip: neither an edge
    # (it turns back) nor the tip (it turns back across) can draw it.
    hook = [
        Point2D(x, y)
        for x, y in (
            (0, -21),
            (-150, -25),
            (-185, -25),
            (-185, 30),
            (-160, 45),
            (-175, 40),
            (-150, 25),
            (0, 21),
        )
    ]
    with pytest.raises(DrawingError, match="hook"):
        fit_headstock(hook, 21.0, -1.0)
    with pytest.raises(DrawingError, match="does not reach past the nut"):
        fit_headstock([Point2D(0, -21), Point2D(-10, 0), Point2D(0, 21)], 21.0, -1.0)
    assert math.isfinite(fit.deviation)


def test_a_pattern_layer_is_written_and_read_back() -> None:
    points = [Point2D(x, y) for x, y in ((0, -50), (300, -150), (450, 0), (300, 150))]
    pattern = (
        (Point2D(50, 0), Point2D(150, 20), Point2D(250, 0)),
        (Point2D(100, -60), Point2D(140, -60), Point2D(140, -20), Point2D(100, -60)),
    )
    svg = template_svg("body", BODY, closed_catmull_rom_spans(points), [], (), pattern)
    assert 'inkscape:label="Pattern"' in svg
    # Moved and scaled as another program saves it: read back in place.
    for drawing in (svg, _wrapped(svg, "translate(10 -5) scale(0.75)")):
        read_back = read_template_pattern(drawing, BODY, tolerance=None)
        assert read_back is not None and len(read_back.lines) == 2
        for line, original in zip(read_back.lines, pattern, strict=True):
            assert [(round(p.x, 3), round(p.y, 3)) for p in line] == [
                (p.x, p.y) for p in original
            ]
    # The pattern's shapes are never taken for the outline, however big.
    big = svg.replace(
        '<g id="cgwPatternLayer" inkscape:groupmode="layer" inkscape:label="Pattern">',
        '<g id="cgwPatternLayer" inkscape:groupmode="layer" inkscape:label="Pattern">'
        '<rect x="-100" y="-300" width="700" height="600"/>',
    ).replace('id="cgwOutline" ', "")
    read = read_template_outline(big, BODY)
    assert max(p.x for p in read.points) == pytest.approx(450, abs=0.5)
    # Straight lines are thinned to their ends; no layer, no pattern.
    straight = (tuple(Point2D(x, 0.0) for x in range(0, 101, 10)),)
    thin = template_svg("b", BODY, closed_catmull_rom_spans(points), [], (), straight)
    thinned_back = read_template_pattern(thin, BODY)
    assert thinned_back is not None
    (line,) = thinned_back.lines
    assert len(line) == 2
    assert read_template_pattern(_body_svg(points), BODY) is None


def test_a_small_drawing_is_as_wide_as_its_notes() -> None:
    import re

    square = [Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10)]
    spans = tuple((a, a, b, b) for a, b in zip(square, square[1:] + square[:1]))
    frame = TemplateFrame((Point2D(0, 0), Point2D(10, 0), Point2D(0, 10)))
    note = "A note far longer than the small drawing above it is wide, every word."
    svg = template_svg("small", frame, spans, [], (note,))
    match = re.search(r'width="([\d.]+)mm"', svg)
    assert match is not None
    # 15 mm each side, then 3.5 mm letters about 0.55 of their size wide.
    assert float(match.group(1)) >= 30.0 + 0.55 * 3.5 * len(note) - 0.01
    # The drawing itself is read back unchanged.
    assert len(read_template_outline(svg, frame).points) >= 4
