"""Tests for the heel relief: the back cut away where the neck joins."""

import ast
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import HeelRelief
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import NECK_BOLT_MIN_WOOD
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
