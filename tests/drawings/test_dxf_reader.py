"""Tests for reading CAD drawings: DXF entities as polylines in millimetres."""

import math

import pytest

from cncguitarwizard.drawings import DrawingError, is_dxf, read_dxf_drawing
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.render.dxf import DxfDocument


def _dxf(*entities: list[tuple[int, object]], units: int = 4, layers: str = "") -> str:
    """A DXF file: a header with its units, a layer table, the entities."""

    def pairs(items: list[tuple[int, object]]) -> str:
        return "".join(f"{code}\n{value}\n" for code, value in items)

    header = pairs(
        [(0, "SECTION"), (2, "HEADER"), (9, "$INSUNITS"), (70, units), (0, "ENDSEC")]
    )
    tables = pairs([(0, "SECTION"), (2, "TABLES"), (0, "TABLE"), (2, "LAYER")])
    tables += layers + pairs([(0, "ENDTAB"), (0, "ENDSEC")])
    body = pairs([(0, "SECTION"), (2, "ENTITIES")])
    body += "".join(pairs(entity) for entity in entities)
    return header + tables + body + pairs([(0, "ENDSEC"), (0, "EOF")])


def _line(a: tuple[float, float], b: tuple[float, float], layer: str = "0") -> list:  # type: ignore[type-arg]
    return [(0, "LINE"), (8, layer), (10, a[0]), (20, a[1]), (11, b[0]), (21, b[1])]


def _arc(
    centre: tuple[float, float], radius: float, start: float, end: float, **extra: float
) -> list:  # type: ignore[type-arg]
    entity = [(0, "ARC"), (8, "0"), (10, centre[0]), (20, centre[1]), (40, radius)]
    entity += [(50, start), (51, end)]
    if "extrusion" in extra:
        entity += [(210, 0.0), (220, 0.0), (230, extra["extrusion"])]
    return entity


def _distance(point: Point2D, centre: tuple[float, float]) -> float:
    return math.hypot(point.x - centre[0], point.y - centre[1])


def test_lines_and_arcs_meeting_end_to_end_are_one_closed_outline() -> None:
    # A 20 mm square with one corner rounded 5 mm, its pieces drawn in no
    # order and either way round, as a CAD program saves them.
    text = _dxf(
        _line((0, 0), (20, 0)),
        _line((0, 20), (0, 0)),
        _arc((15, 15), 5, 0, 90),
        _line((15, 20), (0, 20)),
        _line((20, 15), (20, 0)),
    )
    assert is_dxf(text)
    shapes, points = read_dxf_drawing(text)
    (shape,) = shapes
    assert shape.closed == (True,) and shape.label == "0" and points == ()
    (line,) = shape.subpaths
    xs = [p.x for p in line]
    ys = [p.y for p in line]
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((0, 20, 0, 20))
    # The corners and the arc's ends are its nodes; the arc's own points
    # all lie on it.
    corners = {(round(line[n].x, 6), round(line[n].y, 6)) for n in shape.nodes[0]}
    assert corners == {(0, 0), (20, 0), (20, 15), (15, 20), (0, 20)}
    arc = [p for p in line if p.x > 15 and p.y > 15]
    assert arc and all(_distance(p, (15, 15)) == pytest.approx(5) for p in arc)


def test_polyline_bulges_are_arcs() -> None:
    # A closed LWPOLYLINE: a straight side, then a half circle (bulge 1,
    # counter-clockwise) back to the start.
    polyline = [(0, "LWPOLYLINE"), (8, "pocket"), (90, 2), (70, 1)]
    polyline += [(10, 0.0), (20, 0.0), (42, 0.0), (10, 10.0), (20, 0.0), (42, 1.0)]
    (shape,) = read_dxf_drawing(_dxf(polyline))[0]
    (line,) = shape.subpaths
    assert shape.closed == (True,)
    arc = line[1:]
    assert all(_distance(p, (5, 0)) == pytest.approx(5, abs=1e-9) for p in arc)
    # From (10, 0) counter-clockwise round (5, 0) to (0, 0): over the top.
    assert max(p.y for p in arc) == pytest.approx(5, abs=0.05)


def test_the_r12_writers_own_polylines_circles_and_points() -> None:
    dxf = DxfDocument()
    layer = dxf.layer("cgwOutline", 7)
    square = [Point2D(0, 0), Point2D(30, 0), Point2D(30, 10), Point2D(0, 10)]
    dxf.polyline(square, layer)
    dxf.polyline([Point2D(0, 20), Point2D(30, 20)], "lines", closed=False)
    dxf.circle(Point2D(50, 0), 4.0, "holes")
    dxf.point(Point2D(1.5, 2.5), "cgwHandles")
    shapes, points = read_dxf_drawing(dxf.render())
    by_layer = {shape.label: shape for shape in shapes}
    assert by_layer["cgwOutline"].subpaths[0] == tuple(square)
    assert by_layer["cgwOutline"].nodes == ((0, 1, 2, 3),)
    assert by_layer["lines"].closed == (False,)
    circle = by_layer["holes"]
    assert circle.closed == (True,)
    assert all(_distance(p, (50, 0)) == pytest.approx(4) for p in circle.subpaths[0])
    assert points == (("cgwHandles", Point2D(1.5, 2.5)),)


def test_splines_by_their_control_points_or_through_their_fit_points() -> None:
    # A quadratic Bezier as a degree-2 NURBS: halfway, a quarter of each
    # end and half the middle point.
    bezier = [(0, "SPLINE"), (8, "0"), (70, 8), (71, 2), (72, 6), (73, 3), (74, 0)]
    bezier += [(40, 0.0)] * 3 + [(40, 1.0)] * 3
    bezier += [(10, 0.0), (20, 0.0), (10, 10.0), (20, 20.0), (10, 20.0), (20, 0.0)]
    # A quarter circle, rational: its middle weight the cosine of 45°.
    quarter = [(0, "SPLINE"), (8, "1"), (70, 12), (71, 2), (72, 6), (73, 3)]
    quarter += [(40, 0.0)] * 3 + [(40, 1.0)] * 3
    quarter += [(10, 10.0), (20, 0.0), (41, 1.0), (10, 10.0), (20, 10.0)]
    quarter += [(41, math.sqrt(0.5)), (10, 0.0), (20, 10.0), (41, 1.0)]
    # Fit points only: the curve runs through them.
    fitted = [(0, "SPLINE"), (8, "2"), (70, 8), (71, 3), (72, 0), (73, 0), (74, 4)]
    fits = [(0.0, 0.0), (10.0, 5.0), (20.0, -3.0), (30.0, 8.0)]
    for x, y in fits:
        fitted += [(11, x), (21, y)]
    shapes, _ = read_dxf_drawing(_dxf(bezier, quarter, fitted))
    by_layer = {shape.label: shape.subpaths[0] for shape in shapes}
    assert min(_distance(p, (10, 10)) for p in by_layer["0"]) < 0.05
    assert by_layer["0"][0] == Point2D(0, 0) and by_layer["0"][-1] == Point2D(20, 0)
    assert all(_distance(p, (0, 0)) == pytest.approx(10) for p in by_layer["1"])
    for x, y in fits:
        assert min(_distance(p, (x, y)) for p in by_layer["2"]) < 1e-9
    # Smooth between them, not straight from point to point.
    assert len(by_layer["2"]) > 12


def test_ellipses_mirrored_arcs_and_arcs_with_no_sweep() -> None:
    ellipse = [(0, "ELLIPSE"), (8, "e"), (10, 0.0), (20, 0.0), (11, 10.0), (21, 0.0)]
    ellipse += [(40, 0.5), (41, 0.0), (42, 2 * math.pi)]
    mirrored = _arc((5, 0), 2, 0, 90, extrusion=-1.0)
    mirrored[1] = (8, "m")
    nothing = _arc((0, 0), 3, 45, 45)
    nothing[1] = (8, "n")
    shapes, _ = read_dxf_drawing(_dxf(ellipse, mirrored, nothing))
    by_layer = {shape.label: shape for shape in shapes}
    (line,) = by_layer["e"].subpaths
    assert by_layer["e"].closed == (True,)
    assert max(p.x for p in line) == pytest.approx(10)
    assert max(p.y for p in line) == pytest.approx(5, abs=0.01)
    # Drawn seen from below, the arc is mirrored: about (-5, 0), to the
    # left of it.
    arc = by_layer["m"].subpaths[0]
    assert all(_distance(p, (-5, 0)) == pytest.approx(2) for p in arc)
    assert all(p.x <= -5 + 1e-9 for p in arc)
    assert "n" not in by_layer


def test_units_layers_and_files_that_are_not_dxf() -> None:
    # Inches: 1 in is 25.4 mm.
    (shape,) = read_dxf_drawing(_dxf(_line((0, 0), (1, 0)), units=1))[0]
    assert shape.subpaths[0][-1] == Point2D(25.4, 0)
    # A layer turned off (a negative colour), or an entity made invisible.
    off = "0\nLAYER\n2\nhidden\n70\n0\n62\n-7\n"
    invisible = _line((0, 0), (1, 1)) + [(60, 1)]
    shapes, _ = read_dxf_drawing(
        _dxf(
            _line((0, 5), (1, 5), "hidden"),
            invisible,
            _line((0, 9), (1, 9)),
            layers=off,
        )
    )
    assert [shape.hidden for shape in shapes] == [True, True, False]
    with pytest.raises(DrawingError, match="binary DXF"):
        read_dxf_drawing("AutoCAD Binary DXF\r\n\x1a\x00")
    with pytest.raises(DrawingError, match="not a DXF"):
        read_dxf_drawing("hello\nworld\n")
    assert not is_dxf("<svg></svg>")
    assert is_dxf("999\nmade by hand\n0\nSECTION\n2\nHEADER\n")
