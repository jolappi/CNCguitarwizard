"""Tests for the two-sided body machining plan on Prototype001."""

import math
from dataclasses import replace

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


def test_work_origin_is_index_pin_one_on_the_centerline(plan, body) -> None:  # type: ignore[no-untyped-def]
    assert plan.origin_y == 0.0
    assert (plan.origin_x, plan.origin_y) == plan.index_pin_positions[0]
    first_pin = plan.index_pins.toolpaths[0].moves[0]
    assert (first_pin.x, first_pin.y) == (0.0, 0.0)


def test_automatic_index_pins_stay_in_the_waste(plan, body, parameters) -> None:  # type: ignore[no-untyped-def]
    """Both dowels sit on the centerline outside the finished body."""
    (x1, y1), (x2, y2) = plan.index_pin_positions
    clearance = (
        parameters.index_pin_diameter / 2.0
        + parameters.tool_diameter
        + parameters.index_pin_wall
    )
    outline_min_x = min(point.x for point in body.outline.points)
    outline_max_x = max(point.x for point in body.outline.points)

    assert y1 == 0.0 and y2 == 0.0
    for pin in (Point2D(x1, y1), Point2D(x2, y2)):
        assert not point_in_polygon(pin, body.outline.points)
        assert distance_to_boundary(pin, body.outline.points) >= clearance
        for cavity in (body.neck_pocket, body.neck_pickup, *body.extra_cavities):
            assert not point_in_polygon(pin, cavity.outline)
            assert distance_to_boundary(pin, cavity.outline) >= clearance
    # Pin 1 in the horn gap ahead of the pocket, pin 2 in the tail notch.
    assert outline_min_x < x1 < body.neck_pocket.min_x
    assert x2 > max(point.x for point in body.outline.points if abs(point.y) < 5.0)
    assert x2 < outline_max_x + parameters.stock_margin
    # Every program checks both dowels before the spindle starts.
    assert plan.top.reference_points == ((x2 - x1, 0.0),)
    assert plan.back.reference_points == plan.top.reference_points


def test_automatic_index_pins_follow_a_changed_neck() -> None:
    base = plan_body_machining(
        Prototype001Parameters().build().body, MachiningParameters()
    )
    other = plan_body_machining(
        replace(Prototype001Parameters(), scale_length=647.7).build().body,
        MachiningParameters(),
    )
    heel_shift = 647.7 * (1 - 2 ** (-2)) - 609.6 * (1 - 2 ** (-2))
    assert other.index_pin_positions[0][0] - base.index_pin_positions[0][0] == (
        pytest.approx(heel_shift, abs=0.6)
    )


def test_explicit_index_pins_are_honoured(body) -> None:
    explicit = plan_body_machining(
        body, MachiningParameters(index_pin_positions=((335.0, 0.0), (762.0, 0.0)))
    )

    assert explicit.index_pin_positions == ((335.0, 0.0), (762.0, 0.0))
    assert explicit.top.reference_points == ((427.0, 0.0),)


def test_plan_rejects_an_index_pin_inside_the_finished_body(body) -> None:
    with pytest.raises(ToolpathError, match="inside the finished part"):
        plan_body_machining(
            body, MachiningParameters(index_pin_positions=((335.0, 0.0), (540.0, 0.0)))
        )


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


def test_plan_rejects_an_index_pin_outside_the_blank(body) -> None:
    with pytest.raises(ToolpathError, match="outside the blank"):
        plan_body_machining(
            body,
            MachiningParameters(index_pin_positions=((335.0, 0.0), (100.0, 0.0))),
        )


def test_floyd_rose_plan_drills_the_pivot_studs_and_routes_through() -> None:
    from dataclasses import replace

    from cncguitarwizard.geometry.body import FloydRoseSpec

    geometry = replace(
        Prototype001Parameters(),
        body_bridge=FloydRoseSpec(),
        body_bridge_pickup_offset=35.0,
    ).build()
    plan = plan_body_machining(geometry.body, MachiningParameters())
    names = [path.name for path in plan.top.toolpaths]

    assert "Pivot stud bass" in names and "Pivot stud treble" in names
    block = next(
        path for path in plan.top.toolpaths if path.name == "Sustain-block route"
    )
    assert block.deepest_z() == pytest.approx(-(geometry.body.thickness + 0.5))
    assert plan.top_small_holes is None
    assert "Tremolo spring cavity" in [path.name for path in plan.back.toolpaths]


def test_hardtail_plan_puts_narrow_holes_in_a_small_drill_program() -> None:
    from dataclasses import replace

    from cncguitarwizard.geometry.body import HardtailSpec

    geometry = replace(Prototype001Parameters(), body_bridge=HardtailSpec()).build()
    plan = plan_body_machining(geometry.body, MachiningParameters())

    assert plan.top_small_holes is not None
    assert [setup.name for setup in plan.setups] == [
        "Body_index_pins",
        "Body_top",
        "Body_top_small_holes",
        "Body_back",
    ]
    assert len(plan.preview_outlines) == 4
    small_names = [path.name for path in plan.top_small_holes.toolpaths]
    assert len(small_names) == 11 and "String 1 through hole" in small_names
    assert plan.top_small_holes.tool is not None
    assert plan.top_small_holes.tool.tool_diameter == 3.0
    assert all("String" not in path.name for path in plan.top.toolpaths)


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
