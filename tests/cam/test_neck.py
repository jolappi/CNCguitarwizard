"""Tests for the two-sided neck machining plan on Prototype001."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    GRBLWriter,
    MachiningParameters,
    NeckMachiningParameters,
    ToolpathError,
    neck_plan_polygon,
    plan_neck_machining,
)
from cncguitarwizard.cam.planar import distance_to_boundary
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters


@pytest.fixture(scope="module")
def geometry():  # type: ignore[no-untyped-def]
    return Prototype001Parameters().build()


@pytest.fixture(scope="module")
def parameters() -> NeckMachiningParameters:
    return NeckMachiningParameters()


@pytest.fixture(scope="module")
def plan(geometry, parameters):  # type: ignore[no-untyped-def]
    return plan_neck_machining(geometry, parameters)


def test_plan_polygon_joins_headstock_neck_and_heel(geometry) -> None:  # type: ignore[no-untyped-def]
    polygon = neck_plan_polygon(geometry)
    xs = [point.x for point in polygon]

    assert min(xs) == pytest.approx(-150.0)
    assert max(xs) == pytest.approx(461.2)
    assert point_in_polygon(Point2D(-100.0, 0.0), polygon)
    assert point_in_polygon(Point2D(300.0, 0.0), polygon)
    assert point_in_polygon(Point2D(459.0, 27.0), polygon)
    assert not point_in_polygon(Point2D(300.0, 40.0), polygon)


def test_plan_has_five_setups_with_their_tools(plan, parameters) -> None:  # type: ignore[no-untyped-def]
    assert [setup.name for setup in plan.setups] == [
        "Neck_index_pins",
        "Neck_top",
        "Neck_back_rough",
        "Neck_back_finish",
        "Neck_back_outline",
    ]
    assert plan.back_finish.tool is parameters.ball
    assert plan.back_rough.tool is parameters.flat
    top_names = [path.name for path in plan.top.toolpaths]
    assert top_names[0] == "Truss-rod channel"
    assert "Headstock face roughing" in top_names
    assert sum(name.endswith("centre mark") for name in top_names) == 6


def test_index_pins_sit_in_the_waste_beyond_tip_and_heel(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    polygon = neck_plan_polygon(geometry)
    (x1, y1), (x2, y2) = plan.index_pin_positions
    clearance = (
        parameters.flat.index_pin_diameter / 2.0
        + parameters.flat.tool_diameter
        + parameters.flat.index_pin_wall
    )

    assert y1 == 0.0 and y2 == 0.0
    assert x1 < -150.0 and x2 > 461.2
    for pin in (Point2D(x1, y1), Point2D(x2, y2)):
        assert not point_in_polygon(pin, polygon)
        assert distance_to_boundary(pin, polygon) >= clearance
    assert plan.top.reference_points == ((x2 - x1, 0.0),)
    assert plan.back_finish.reference_points == plan.top.reference_points


def test_truss_rod_and_headstock_face_depths(plan, geometry) -> None:  # type: ignore[no-untyped-def]
    paths = {path.name: path for path in plan.top.toolpaths}
    truss = geometry.truss_rod_channel
    tangent = math.tan(math.radians(geometry.headstock.angle.angle_degrees))

    assert paths["Truss-rod channel"].deepest_z() == pytest.approx(-truss.depth)
    # A flat tool can go no deeper than the highest surface point under
    # it, so the face pass bottoms out at the headstock tip's own height.
    face = paths["Headstock face finishing"]
    assert face.deepest_z() == pytest.approx(
        -geometry.headstock.plan.length * tangent, abs=0.1
    )
    mark = paths["Tuner bass 1 centre mark"]
    hole = geometry.tuner_layout.holes[0]
    assert mark.deepest_z() == pytest.approx(hole.center.x * tangent - 0.5, abs=1e-6)


def test_ball_finish_never_cuts_below_the_neck_back(plan, geometry, parameters) -> None:  # type: ignore[no-untyped-def]
    """Every finishing move keeps the ball above every sampled back-surface point."""
    thickness = parameters.blank_thickness
    r = parameters.ball.tool_radius
    origin_x, origin_y = plan.index_pin_positions[0]
    rows = geometry.neck_surface.mesh.rows[::6]
    vertices = [
        (point.x - origin_x, -(point.y - origin_y), -(thickness + point.z))
        for row in rows
        for point in row[::2]
    ]
    finish_moves = [
        move for move in plan.back_finish.toolpaths[0].moves if not move.rapid
    ]
    checked = 0
    for vx, vy, vz in vertices:
        for move in finish_moves:
            d = math.hypot(move.x - vx, move.y - vy)
            if d > r:
                continue
            checked += 1
            centre_z = move.z + r
            # 0.1 mm covers the grid sampling of the steep edge zone.
            assert centre_z >= vz + math.sqrt(r * r - d * d) - 0.1, (vx, vy, vz)
    assert checked > 1000


def test_roughing_stays_above_the_finished_surface_and_within_the_blank(  # type: ignore[no-untyped-def]
    plan, parameters
) -> None:
    rough = plan.back_rough.toolpaths[0]
    finish = plan.back_finish.toolpaths[0]
    skin_level = -(parameters.blank_thickness - parameters.skin)

    assert rough.deepest_z() >= skin_level - 1e-6
    assert finish.deepest_z() >= skin_level - 1e-6
    # The heel back (20 mm thick) is the shallowest neck-wood cut: 20 mm
    # into a 40 mm blank.
    assert finish.deepest_z() <= -20.0


def test_outline_cuts_the_skin_with_tabs(plan, parameters) -> None:  # type: ignore[no-untyped-def]
    outline = plan.back_outline.toolpaths[0]
    thickness = parameters.blank_thickness
    cut_moves = [move for move in outline.moves if not move.rapid]

    assert outline.deepest_z() == pytest.approx(
        -(thickness + parameters.flat.through_overshoot)
    )
    tab_top = (
        -(thickness + parameters.flat.through_overshoot) + parameters.flat.tab_height
    )
    assert any(abs(move.z - tab_top) < 1e-6 for move in cut_moves)
    # Nothing but the tab lifts rises above the skin: the pass starts
    # 0.5 mm above it and the tabs stay within the carved trench.
    assert all(move.z <= tab_top + 1e-6 for move in cut_moves if move.z < 0.0)


def test_blank_too_thin_for_the_headstock_is_rejected(geometry) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ToolpathError, match="thick"):
        plan_neck_machining(geometry, NeckMachiningParameters(blank_thickness=30.0))


def test_setups_render_with_their_own_tool_lines(plan) -> None:  # type: ignore[no-untyped-def]
    writer = GRBLWriter()
    finish = writer.render(plan.back_finish, MachiningParameters())
    rough = writer.render(plan.back_rough, MachiningParameters())

    assert "ball nose" in finish.splitlines()[2]
    assert "end mill" in rough.splitlines()[2]
    assert finish.rstrip().endswith("M2")


def test_plan_follows_a_longer_scale(geometry) -> None:  # type: ignore[no-untyped-def]
    longer = replace(Prototype001Parameters(), scale_length=647.7).build()
    plan = plan_neck_machining(longer, NeckMachiningParameters())

    assert plan.index_pin_positions[1][0] > 489.8
    assert plan.stock_length > 681.0
