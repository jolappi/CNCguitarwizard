"""Tests for the heel relief: the back cut away where the neck joins."""

import ast
import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import HeelRelief
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import (
    NECK_BOLT_MIN_WOOD,
    NECK_PLATE_RELIEF_GAP,
)
from cncguitarwizard.webapp import body_editor_layout


def square(size: float = 200.0) -> tuple[Point2D, ...]:
    """A counter-clockwise square, densely sampled."""
    points = []
    for index in range(40):
        points.append(Point2D(-size / 2 + size * index / 40, -size / 2))
    for index in range(40):
        points.append(Point2D(size / 2, -size / 2 + size * index / 40))
    for index in range(40):
        points.append(Point2D(size / 2 - size * index / 40, size / 2))
    for index in range(40):
        points.append(Point2D(-size / 2, size / 2 - size * index / 40))
    return tuple(points)


# A line across the square's left end, 40 mm in: the relief runs from the
# left edge (x = -100) in to x = -60.
LINE = (
    Point2D(-100.0, 50.0),
    Point2D(-60.0, 50.0),
    Point2D(-60.0, -50.0),
    Point2D(-100.0, -50.0),
)


def test_a_contour_ramps_from_the_edge_in_to_its_line() -> None:
    relief = HeelRelief.between("Heel relief", square(), LINE, 8.0)

    assert relief.face == "back" and relief.profile == "ramp"
    assert relief.depth_at(Point2D(-99.5, 0.0)) == pytest.approx(8.0, abs=0.2)
    assert relief.depth_at(Point2D(-80.0, 0.0)) == pytest.approx(4.0, abs=0.3)
    assert relief.depth_at(Point2D(-61.0, 0.0)) == pytest.approx(0.2, abs=0.2)
    assert relief.depth_at(Point2D(-40.0, 0.0)) == 0.0
    # Everywhere between edge and line it rises toward the line.
    depths = [relief.depth_at(Point2D(x, 10.0)) for x in range(-99, -60, 3)]
    assert depths == sorted(depths, reverse=True)


def test_a_notch_is_flat_to_a_wall_at_its_line() -> None:
    relief = HeelRelief.between("Heel relief", square(), LINE, 6.0, "flat")

    for x in (-99.0, -80.0, -61.0):
        assert relief.depth_at(Point2D(x, 0.0)) == 6.0
    assert relief.depth_at(Point2D(-59.0, 0.0)) == 0.0


def test_a_cutter_finishes_the_edge_from_the_slot_past_it() -> None:
    relief = HeelRelief.between("Heel relief", square(), LINE, 8.0)

    # 4 mm past the edge, in a 6.5 mm slot: the edge's depth runs on.
    assert relief.machining_depth(Point2D(-104.0, 0.0), 6.5) == pytest.approx(8.0)
    assert relief.machining_depth(Point2D(-110.0, 0.0), 6.5) == 0.0
    # Inside the body past the line, nothing.
    assert relief.machining_depth(Point2D(-50.0, 0.0), 6.5) == 0.0


def test_its_layers_narrow_toward_the_edge_and_reach_into_the_waste() -> None:
    relief = HeelRelief.between("Heel relief", square(), LINE, 8.0)

    half = relief.level_region(4.0)
    assert point_in_polygon(Point2D(-90.0, 0.0), half)
    assert point_in_polygon(Point2D(-105.0, 0.0), half)  # the waste past the edge
    assert not point_in_polygon(Point2D(-70.0, 0.0), half)
    # A notch's every layer reaches the wall.
    notch = HeelRelief.between("Heel relief", square(), LINE, 8.0, "flat")
    assert point_in_polygon(Point2D(-62.0, 0.0), notch.level_region(7.0))


def test_a_line_with_its_ends_together_is_refused() -> None:
    with pytest.raises(BodyGeometryError, match="too close together"):
        HeelRelief.between(
            "Heel relief", square(), (Point2D(-100.0, 0.0), Point2D(-100.0, 1.0)), 8.0
        )


@pytest.mark.parametrize("kind", ["contour", "notch"])
def test_the_preset_relieves_the_heel_and_sinks_the_ferrules_into_it(kind: str) -> None:
    parameters = replace(Prototype001Parameters(), body_heel_relief=kind)
    plain = Prototype001Parameters().build().body
    body = parameters.build().body

    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    assert isinstance(relief, HeelRelief)
    assert relief.profile == ("flat" if kind == "notch" else "ramp")
    bolts = {
        hole.name: hole for hole in body.rear_holes if hole.name.startswith("Neck bolt")
    }
    assert set(relief.carries) == set(bolts)
    before = {hole.name: hole for hole in plain.rear_holes}
    for name, hole in bolts.items():
        under = relief.depth_at(Point2D(hole.center_x, hole.center_y))
        if name.endswith("ferrule"):
            # As deep into the relief's surface as into the flat back.
            assert hole.depth == pytest.approx(before[name].depth + under)
        else:
            assert hole.depth == before[name].depth
    assert any(
        relief.depth_at(Point2D(hole.center_x, hole.center_y)) > 0.0
        for hole in bolts.values()
    )


@pytest.mark.parametrize("line", ["around", "pocket"])
def test_a_relief_round_the_heel_takes_in_the_whole_heel(line: str) -> None:
    # The neck pocket's place on the back, to its bass wall, and no more
    # on the bass side: out past the heel on the treble side only.
    parameters = replace(
        Prototype001Parameters(),
        body_heel_relief="contour",
        body_heel_relief_line=line,
    )
    body = parameters.build().body
    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    pocket = body.neck_pocket
    assert pocket is not None
    bass = parameters.bass_sign
    bass_wall = max(point.y * bass for point in pocket.outline)
    heel_end = max(p.x for p in pocket.outline)
    assert max(point.y * bass for point in relief.line) == pytest.approx(bass_wall)
    outline = body.outline.points
    for x in (heel_end - 30.0, heel_end - 15.0, heel_end - 5.0):
        for y in (-0.8, -0.4, 0.0, 0.4, 0.8):
            point = Point2D(x, y * bass_wall)
            if point_in_polygon(point, outline):
                assert relief.depth_at(point) > 0.0
        assert relief.depth_at(Point2D(x, (bass_wall + 3.0) * bass)) == 0.0


def test_the_preset_takes_a_drawn_heel_relief_line() -> None:
    drawn = Prototype001Parameters().built_body_shape
    line = ((-20.0, 40.0), (10.0, 30.0), (20.0, 0.0), (10.0, -30.0), (-20.0, -40.0))
    parameters = replace(
        Prototype001Parameters(),
        body_heel_relief="contour",
        body_shape=replace(drawn, heel_relief_points=line),
    )
    body = parameters.build().body
    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    heel_end = max(
        p.x for c in body.top_cavities if c.name == "Neck pocket" for p in c.outline
    )
    assert max(p.x for p in relief.line) == pytest.approx(heel_end + 20.0, abs=1.0)


def test_a_relief_too_deep_for_the_bolts_is_refused() -> None:
    parameters = replace(
        Prototype001Parameters(), body_heel_relief="notch", body_heel_relief_depth=16.0
    )
    with pytest.raises(
        BodyGeometryError, match=f"keep at least {NECK_BOLT_MIN_WOOD:g} mm"
    ):
        parameters.build()


def test_a_neck_through_body_has_no_heel_to_relieve() -> None:
    parameters = replace(
        Prototype001Parameters(), neck_joint="neck_through", body_heel_relief="contour"
    )
    with pytest.raises(BodyGeometryError, match="no heel to relieve"):
        parameters.build()


def test_it_is_machined_from_the_back_and_modelled_in_freecad() -> None:
    geometry = replace(Prototype001Parameters(), body_heel_relief="contour").build()
    plan = plan_body_machining(geometry.body, MachiningParameters())

    assert plan.back_edges is not None
    assert [path.name for path in plan.back_edges.toolpaths] == [
        "Heel relief roughing",
        "Heel relief finishing",
    ]
    source = FreeCADScriptExporter().render_prototype001(geometry)
    ast.parse(source)
    assert source.count("terrace(") >= 2


def test_the_body_editor_draws_its_line() -> None:
    layout = body_editor_layout({"prototype": {"body_heel_relief": "notch"}})

    line = layout["heel_relief"]
    assert line["automatic"] is True and len(line["points"]) == 7
    assert body_editor_layout({"prototype": {}})["heel_relief"] is None


@pytest.mark.parametrize("line", ["around", "pocket"])
def test_the_body_editor_draws_the_line_as_it_is_cut(line: str) -> None:
    # The automatic line itself, not a curve through its handles (which
    # would round off the pocket's corners); the handles spread evenly
    # along it, its ends on its ends.
    prototype = {"body_heel_relief": "contour", "body_heel_relief_line": line}
    drawn = body_editor_layout({"prototype": prototype})["heel_relief"]
    parameters = Prototype001Parameters(
        body_heel_relief="contour", body_heel_relief_line=line
    )
    body = parameters.build().body
    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    heel_end = parameters.neck_outline().last_fret_position + parameters.heel_length
    assert drawn["line"] == [
        [round(p.x - heel_end, 2), round(p.y, 2)] for p in relief.line
    ]
    handles = drawn["points"]
    assert handles[0] == drawn["line"][0] and handles[-1] == drawn["line"][-1]
    steps = [math.dist(a, b) for a, b in zip(handles, handles[1:], strict=False)]
    assert max(steps) < 2.0 * min(steps)


def test_a_bevel_across_a_corner_slopes_along_its_own_axis() -> None:
    # The square's corner at (-100, 100) cut off by a 45 degree line.
    out = (-math.sqrt(0.5), math.sqrt(0.5))
    line = (Point2D(-100.0, 40.0), Point2D(-70.0, 70.0), Point2D(-40.0, 100.0))
    face = -100.0 * out[0] + 40.0 * out[1]
    deep = -100.0 * out[0] + 100.0 * out[1]
    relief = HeelRelief.between(
        "Heel relief", square(), line, 6.0, "plane", (deep, face), out
    )

    def at(along: float) -> Point2D:
        # A point that far along the axis, on the corner's diagonal.
        return Point2D(along * out[0], along * out[1])

    assert relief.depth_at(at(face + 0.5)) == pytest.approx(6.0 * 0.5 / (deep - face))
    assert relief.depth_at(at((face + deep) / 2.0)) == pytest.approx(3.0)
    assert relief.depth_at(at(face - 5.0)) == 0.0
    # Its layers narrow toward the corner.
    half = relief.level_region(3.0)
    assert point_in_polygon(at(deep - 3.0), half)
    assert not point_in_polygon(at(face + 5.0), half)
    with pytest.raises(BodyGeometryError, match="unit direction"):
        HeelRelief.between(
            "Heel relief", square(), line, 6.0, "plane", (deep, face), (1.0, 1.0)
        )


def distance_to(point: Point2D, polygon: tuple[Point2D, ...]) -> float:
    """The distance from ``point`` to a closed polygon's edges."""
    best = math.inf
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        ex, ey = b.x - a.x, b.y - a.y
        t = ((point.x - a.x) * ex + (point.y - a.y) * ey) / (ex * ex + ey * ey)
        t = min(1.0, max(0.0, t))
        best = min(best, math.hypot(a.x + ex * t - point.x, a.y + ey * t - point.y))
    return best


@pytest.mark.parametrize("kind", ["contour", "notch", "bevel"])
def test_a_line_by_the_pocket_keeps_the_reach_from_it_on_the_treble_side(
    kind: str,
) -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_heel_relief=kind,
        body_heel_relief_line="pocket",
    )
    body = parameters.build().body
    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    assert isinstance(relief, HeelRelief)
    pocket = body.neck_pocket
    assert pocket is not None
    treble = -parameters.bass_sign

    heel_end = max(p.x for p in pocket.outline)
    bass_wall = max(-point.y * treble for point in pocket.outline)
    for point in relief.line:
        if point.y * treble > -bass_wall + 1e-6:
            assert distance_to(point, pocket.outline) == pytest.approx(15.0, abs=0.3)
        else:
            # The rest along the pocket's bass wall to the body's edge.
            assert -point.y * treble == pytest.approx(bass_wall, abs=1e-9)
    # Round its tail end, out to the body's edge on the treble side.
    assert max(p.x for p in relief.line) == pytest.approx(heel_end + 15.0, abs=0.1)
    assert -relief.line[0].y * treble == pytest.approx(bass_wall)
    assert relief.line[-1].y * treble > 0.0
    if kind == "bevel":
        # Sloping along the neck, as round the heel.
        assert relief.plane_axis == (1.0, 0.0)


def test_a_plate_tilts_on_a_bevel_by_the_pocket() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_shape=YOUR_DESIGN_TEMPLATES["stratocaster"][1],
        body_neck_plate="plate",
        body_heel_relief="bevel",
        body_heel_relief_line="pocket",
    )
    holes = parameters.build().body.side_holes
    assert len([hole for hole in holes if hole.name.startswith("Neck bolt")]) == 4


@pytest.mark.parametrize("handedness", ["right", "left"])
@pytest.mark.parametrize("line", ["around", "pocket", "corner"])
@pytest.mark.parametrize("kind", ["contour", "notch", "bevel"])
@pytest.mark.parametrize("template", ["stratocaster", "jackson_rr"])
def test_the_relief_is_always_on_the_treble_side(
    template: str, kind: str, line: str, handedness: str
) -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_shape=YOUR_DESIGN_TEMPLATES[template][1],
        handedness=handedness,
        body_heel_relief=kind,
        body_heel_relief_line=line,
    )
    body = parameters.build().body
    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    assert isinstance(relief, HeelRelief)
    treble = -parameters.bass_sign
    pocket = body.neck_pocket
    assert pocket is not None

    # Edge and line alike: on the bass side nothing past the pocket's bass
    # wall round the heel (it takes in the whole heel), nor past the
    # centreline across the treble corner.
    bound = 0.0 if line == "corner" else max(-p.y * treble for p in pocket.outline)
    assert min(p.y * treble for p in (*relief.edge, *relief.line)) >= -bound - 1e-9
    beyond = Point2D(relief.line[-1].x, -treble * (bound + 5.0))
    assert relief.depth_at(beyond) == 0.0


def test_a_tilted_plate_takes_the_bevel_across_the_neck_and_no_further() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_shape=YOUR_DESIGN_TEMPLATES["stratocaster"][1],
        body_neck_plate="plate",
        body_heel_relief="bevel",
    )
    body = parameters.build().body
    (relief,) = [c for c in body.contours if c.name == "Heel relief"]
    assert isinstance(relief, HeelRelief)
    treble = -parameters.bass_sign

    # Under the plate on the bass side, the gap past its edge, and no more.
    reach = parameters.body_neck_plate_width / 2.0 + NECK_PLATE_RELIEF_GAP
    assert -min(p.y * treble for p in (*relief.edge, *relief.line)) == pytest.approx(
        reach
    )
    assert all(point_in_polygon(p, relief.region()) for p in body.neck_plate)


def test_a_line_wholly_on_the_bass_side_is_refused() -> None:
    parameters = replace(Prototype001Parameters(), body_heel_relief="contour")
    bass = parameters.bass_sign
    shape = replace(
        parameters.body_shape,
        heel_relief_points=((-30.0, bass * 60.0), (10.0, bass * 35.0)),
    )
    # Past the pocket's bass wall all the way.
    with pytest.raises(BodyGeometryError, match="wholly on the bass side"):
        replace(parameters, body_shape=shape).build()
