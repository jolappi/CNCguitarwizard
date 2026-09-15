"""Tests for the two-sided body machining plan on Prototype001."""

import math

import pytest

from cncguitarwizard.cam import (
    GRBLWriter,
    MachiningParameters,
    ToolpathError,
    plan_body_machining,
)
from cncguitarwizard.cam.planar import disc_fits, distance_to_boundary
from cncguitarwizard.geometry.body import BodySolid
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters


@pytest.fixture(scope="module")
def body() -> BodySolid:
    return Prototype001Parameters().build().body


@pytest.fixture(scope="module")
def parameters() -> MachiningParameters:
    return MachiningParameters()


@pytest.fixture(scope="module")
def plan(body: BodySolid, parameters: MachiningParameters):  # type: ignore[no-untyped-def]
    return plan_body_machining(body, parameters)


def to_model(point: Point2D, plan, mirror: bool) -> Point2D:  # type: ignore[no-untyped-def]
    if mirror:
        return Point2D(point.x + plan.origin_x, plan.origin_y - point.y)
    return Point2D(point.x + plan.origin_x, point.y + plan.origin_y)


def test_plan_has_three_setups_in_running_order(plan) -> None:  # type: ignore[no-untyped-def]
    assert [setup.name for setup in plan.setups] == [
        "Body_index_pins",
        "Body_top",
        "Body_back",
    ]
    assert [path.name for path in plan.index_pins.toolpaths] == [
        "Index pin 1",
        "Index pin 2",
    ]
    names = [path.name for path in plan.top.toolpaths]
    assert names[:3] == ["Neck pocket", "Neck pickup route", "Bridge pickup route"]
    assert "Bridge baseplate cutout" in names
    assert names[-1] == "Outline, upper half"
    back_names = [path.name for path in plan.back.toolpaths]
    assert back_names == [
        "Control cavity cover recess",
        "Control cavity",
        "Switch cavity cover recess",
        "Switch cavity",
        "Outline, lower half with tabs",
    ]


def test_work_origin_is_index_pin_one_on_the_centerline(plan) -> None:  # type: ignore[no-untyped-def]
    assert (plan.origin_x, plan.origin_y) == (420.0, 0.0)
    first_pin = plan.index_pins.toolpaths[0].moves[0]
    assert (first_pin.x, first_pin.y) == (0.0, 0.0)


def test_every_top_cut_stays_inside_its_own_feature(body, plan, parameters) -> None:  # type: ignore[no-untyped-def]
    """No cutting move on the top face leaves the cavity or hole it belongs to."""
    radius = parameters.tool_radius
    cavities = {cavity.name: cavity for cavity in (
        body.neck_pocket, body.neck_pickup, body.bridge_pickup, *body.extra_cavities
    )}
    holes = {hole.name: hole for hole in body.holes}
    for path in plan.top.toolpaths:
        for move in path.moves:
            if move.rapid or move.z >= 0.0:
                continue
            point = to_model(Point2D(move.x, move.y), plan, mirror=False)
            if path.name in cavities:
                assert disc_fits(point, cavities[path.name].outline, radius), path.name
            elif path.name in holes:
                hole = holes[path.name]
                assert math.hypot(point.x - hole.center_x, point.y - hole.center_y) <= (
                    hole.diameter / 2.0 - radius + 1e-6
                ), path.name
            else:
                assert path.name == "Outline, upper half"
                assert not point_in_polygon(point, body.outline.points)
                assert distance_to_boundary(point, body.outline.points) >= radius - 1e-6


def test_every_back_cut_stays_inside_its_own_feature(body, plan, parameters) -> None:  # type: ignore[no-untyped-def]
    radius = parameters.tool_radius
    regions = {}
    for rear in body.rear_cavities:
        regions[rear.cavity.name] = rear.cavity.outline
        regions[rear.cover_recess.name] = rear.cover_recess.outline
    for path in plan.back.toolpaths:
        for move in path.moves:
            if move.rapid or move.z >= 0.0:
                continue
            point = to_model(Point2D(move.x, move.y), plan, mirror=True)
            if path.name in regions:
                assert disc_fits(point, regions[path.name], radius), path.name
            else:
                assert path.name == "Outline, lower half with tabs"
                assert not point_in_polygon(point, body.outline.points)


def test_shaft_holes_only_break_through_the_top_wall(body, plan, parameters) -> None:  # type: ignore[no-untyped-def]
    paths = {path.name: path for path in plan.top.toolpaths}
    top_wall = body.thickness - body.control_cavity.depth

    for name in ("Switch shaft hole", "Pot 1 shaft hole", "Pot 2 shaft hole"):
        assert paths[name].deepest_z() == pytest.approx(
            -(top_wall + parameters.through_overshoot)
        )


def test_screw_recesses_start_at_the_route_floor(body, plan) -> None:  # type: ignore[no-untyped-def]
    paths = {path.name: path for path in plan.top.toolpaths}
    recess = paths["Neck pickup bass screw recess"]
    cutting = [move for move in recess.moves if not move.rapid]

    # Three equal pecks from the 22 mm route floor to 30 mm.
    assert cutting[0].z == pytest.approx(-(body.neck_pickup.depth + 8.0 / 3.0))
    assert recess.deepest_z() == pytest.approx(-30.0)
    assert all(move.z <= -body.neck_pickup.depth + 1.0 for move in cutting)


def test_index_pins_go_through_the_blank(plan, body, parameters) -> None:  # type: ignore[no-untyped-def]
    for path in plan.index_pins.toolpaths:
        assert path.deepest_z() == pytest.approx(
            -(body.thickness + parameters.through_overshoot)
        )


def test_both_outline_halves_overlap_at_the_mid_plane(plan, body, parameters) -> None:  # type: ignore[no-untyped-def]
    top = plan.top.toolpaths[-1]
    back = plan.back.toolpaths[-1]
    expected = -(body.thickness / 2.0 + parameters.profile_overlap)

    assert top.deepest_z() == pytest.approx(expected)
    assert back.deepest_z() == pytest.approx(expected)
    tab_top = expected + parameters.tab_height
    assert any(
        not move.rapid and abs(move.z - tab_top) < 1e-6 for move in back.moves
    )


def test_plan_reports_a_blank_larger_than_the_outline(plan, body) -> None:  # type: ignore[no-untyped-def]
    xs = [point.x for point in body.outline.points]
    ys = [point.y for point in body.outline.points]

    assert plan.stock_length > max(xs) - min(xs)
    assert plan.stock_width > max(ys) - min(ys)
    assert plan.stock_thickness == body.thickness


def test_plan_rejects_an_index_pin_outside_the_body(body) -> None:
    with pytest.raises(ToolpathError, match="outside"):
        plan_body_machining(
            body,
            MachiningParameters(index_pin_positions=((420.0, 0.0), (100.0, 0.0))),
        )


def test_setups_render_to_gcode(plan, parameters) -> None:  # type: ignore[no-untyped-def]
    for setup in plan.setups:
        source = GRBLWriter().render(setup, parameters)
        lines = source.splitlines()
        assert source.startswith("(CNCguitarwizard")
        assert source.rstrip().endswith("M2")
        assert "nan" not in source and "inf" not in source
        # Starts and ends over index pin 1 before the first cut / after the last.
        first_motion = next(line for line in lines if line.startswith("G0 X"))
        assert first_motion == "G0 X0.000 Y0.000"
        assert lines[-2] == "G0 X0.000 Y0.000"
