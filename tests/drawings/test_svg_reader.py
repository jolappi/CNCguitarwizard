"""Tests for reading SVG drawings as polylines in millimetres."""

import math

import pytest

from cncguitarwizard.drawings import DrawingError, read_svg_shapes
from cncguitarwizard.drawings.svg_reader import parse_path


def _svg(
    body: str, size: str = 'width="100mm" height="100mm" viewBox="0 0 100 100"'
) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" {size}>{body}</svg>'


def _points(text: str) -> list[tuple[float, float]]:
    (shape,) = read_svg_shapes(text)
    return [(round(p.x, 6), round(p.y, 6)) for sub in shape.subpaths for p in sub]


def test_every_path_command_absolute_and_relative() -> None:
    # Implicit lineto after a moveto, numbers run together, H/V.
    assert _points(_svg('<path d="M0,0 10,0l0,10H5v-5.5.5Z"/>')) == [
        (0, 0),
        (10, 0),
        (10, 10),
        (5, 10),
        (5, 4.5),
        (5, 5),
        (0, 0),
    ]
    # A cubic, its smooth continuation and a quadratic pass their ends.
    for d in ("M0 0C0 10 10 10 10 0S20-10 20 0", "M0 0Q5 10 10 0T20 0"):
        points = _points(_svg(f'<path d="{d}"/>'))
        assert points[0] == (0, 0) and points[-1] == (20, 0)
        assert any(y > 4 for _, y in points) and any(y < -4 for _, y in points)


def test_arcs_round_to_their_radius_with_flags_run_together() -> None:
    # Two half arcs make a circle of radius 5 about (10, 10).
    points = _points(_svg('<path d="M5 10a5 5 0 1 1 10 0a5 5 0 11-10 0z"/>'))
    for x, y in points:
        assert math.hypot(x - 10, y - 10) == pytest.approx(5.0, abs=0.06)
    assert min(y for _, y in points) == pytest.approx(5.0, abs=0.06)
    # Too small a radius is scaled up to reach: a half circle.
    half = _points(_svg('<path d="M0 0A1 1 0 0 1 10 0"/>'))
    assert max(abs(y) for _, y in half) == pytest.approx(5.0, abs=0.06)


def test_groups_transforms_and_document_units() -> None:
    shape = (
        '<g transform="translate(10 20)">'
        '<g transform="rotate(90) scale(2)"><path d="M0 0H5"/></g></g>'
    )
    assert _points(_svg(shape)) == [(10, 20), (10, 30)]
    matrix = '<path transform="matrix(1 0 0 -1 0 50)" d="M0 0L0 10"/>'
    assert _points(_svg(matrix)) == [(0, 50), (0, 40)]
    # 96 px to the inch, 72 pt, and a viewBox scaled to the page.
    assert _points(_svg('<path d="M0 0H96"/>', 'width="96" height="96"'))[-1] == (
        25.4,
        0,
    )
    pt = 'width="72pt" height="72pt" viewBox="0 0 72 72"'
    assert _points(_svg('<path d="M0 0H72"/>', pt))[-1] == (25.4, 0)
    offset = 'width="200mm" height="100mm" viewBox="-10 -10 100 50"'
    assert _points(_svg('<path d="M-10 -10H90"/>', offset)) == [(0, 0), (200, 0)]
    # A box of another shape is fitted in, centred (xMidYMid meet).
    meet = 'width="200mm" height="200mm" viewBox="0 0 100 50"'
    assert _points(_svg('<path d="M0 0H100"/>', meet)) == [(0, 50), (200, 50)]


def test_basic_shapes_close() -> None:
    shapes = read_svg_shapes(
        _svg(
            '<rect x="1" y="2" width="10" height="5"/>'
            '<rect x="0" y="0" width="10" height="10" rx="2"/>'
            '<circle cx="50" cy="50" r="10"/><ellipse cx="0" cy="0" rx="4" ry="2"/>'
            '<polygon points="0,0 10,0 10,10"/><polyline points="0,0 5,5"/>'
            '<line x1="0" y1="0" x2="3" y2="4"/>'
        )
    )
    assert [shape.closed for shape in shapes] == [
        (True,),
        (True,),
        (True,),
        (True,),
        (True,),
        (False,),
        (False,),
    ]
    xs = [p.x for p in shapes[0].subpaths[0]]
    assert (min(xs), max(xs)) == (1, 11)
    circle = shapes[2].subpaths[0]
    assert all(
        math.hypot(p.x - 50, p.y - 50) == pytest.approx(10, abs=0.06) for p in circle
    )


def test_names_layers_hidden_and_definitions() -> None:
    shapes = read_svg_shapes(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        'viewBox="0 0 10 10">'
        '<defs><path id="hiddenDef" d="M0 0H1"/></defs>'
        '<g id="layer1" inkscape:label="Outline"><path id="p1" d="M0 0H1"/></g>'
        '<g style="display:none"><path data-name="cgwMarkA" d="M0 0H1"/></g>'
        "<text>not geometry</text></svg>"
    )
    assert [shape.names() for shape in shapes] == [("p1",), ("cgwMarkA",)]
    assert shapes[0].groups == ("layer1", "Outline") and not shapes[0].hidden
    assert shapes[1].hidden
    # The path's nodes are where one span meets the next.
    (shape,) = read_svg_shapes(_svg('<path d="M0 0C0 5 5 5 5 0L9 0"/>'))
    assert shape.nodes[0][0] == 0 and shape.nodes[0][-1] == len(shape.subpaths[0]) - 1
    assert len(shape.nodes[0]) == 3


def test_what_is_not_svg_is_refused() -> None:
    with pytest.raises(DrawingError, match="not an SVG file"):
        read_svg_shapes("{}")
    with pytest.raises(DrawingError, match="not an SVG file"):
        read_svg_shapes("<html/>")
    with pytest.raises(DrawingError, match="Cannot read the path data"):
        parse_path("M0 0 L")
