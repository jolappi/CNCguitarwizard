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
    headstock = geometry.headstock

    assert paths["Truss-rod channel"].deepest_z() == pytest.approx(-truss.depth)
    # A flat tool can go no deeper than the highest surface point under
    # it, so the face pass bottoms out at the headstock tip's own height.
    face = paths["Headstock face finishing"]
    assert face.deepest_z() == pytest.approx(
        headstock.face_z(-headstock.plan.length), abs=0.1
    )
    mark = paths["Tuner bass 1 centre mark"]
    hole = geometry.tuner_layout.holes[0]
    assert mark.deepest_z() == pytest.approx(
        headstock.face_z(hole.center.x) - 0.5, abs=1e-6
    )


def test_ball_finish_never_cuts_below_the_neck_back(plan, geometry, parameters) -> None:  # type: ignore[no-untyped-def]
    """Every finishing move keeps the ball above every sampled back-surface point."""
    thickness = plan.stock_thickness
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
    skin_level = -(plan.stock_thickness - parameters.skin)

    assert rough.deepest_z() >= skin_level - 1e-6
    assert finish.deepest_z() >= skin_level - 1e-6
    # The heel back (20 mm thick) is the shallowest neck-wood cut: 20 mm
    # above the glue plane, whatever the blank's thickness.
    assert finish.deepest_z() <= -(plan.stock_thickness - 20.0)


def test_outline_cuts_the_skin_with_tabs(plan, parameters) -> None:  # type: ignore[no-untyped-def]
    outline = plan.back_outline.toolpaths[0]
    thickness = plan.stock_thickness
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


def test_blank_too_thin_for_the_headstock_is_thickened(geometry) -> None:  # type: ignore[no-untyped-def]
    plan = plan_neck_machining(geometry, NeckMachiningParameters(blank_thickness=30.0))

    # The face falls from the nut's 5 mm seat: the last 145 mm at 8 deg drop
    # 20.38 mm, plus 16 mm / cos 8 deg.
    assert plan.stock_thickness == pytest.approx(36.6, abs=0.05)
    assert "more than the 30 mm blank_thickness" in " ".join(plan.setups[0].notes)


def test_a_six_in_line_headstock_thickens_the_blank() -> None:
    from dataclasses import replace

    from cncguitarwizard.presets import Prototype001Parameters

    geometry = replace(Prototype001Parameters(), headstock_style="6_inline").build()
    plan = plan_neck_machining(geometry, NeckMachiningParameters())

    assert plan.stock_thickness == pytest.approx(42.9, abs=0.05)


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


def _cut_span(path) -> float:  # type: ignore[no-untyped-def]
    """Return how far along X the tool centre travels while cutting."""
    xs = [move.x for move in path.moves if not move.rapid and move.z < 0.0]
    return max(xs) - min(xs)


@pytest.mark.parametrize("adjustment", ["heel", "headstock"])
def test_truss_rod_steps_run_over_their_neighbours(adjustment: str) -> None:
    # A round cutter leaves its radius in every corner: each pocket runs a
    # tool radius on over the next part (and toward the adjuster), so the
    # rod's square blocks meet no corner; the channel's anchor end stays.
    geometry = replace(
        Prototype001Parameters(), truss_rod_adjustment=adjustment
    ).build()
    parameters = NeckMachiningParameters()
    radius = MachiningParameters(stock_margin=35.0).tool_radius
    paths = {p.name: p for p in plan_neck_machining(geometry, parameters).top.toolpaths}
    truss = geometry.truss_rod_channel

    # Tool-centre travel = part length + 2 overruns - the tool's diameter.
    assert _cut_span(paths["Truss-rod step"]) == pytest.approx(
        truss.step_length, abs=0.05
    )
    assert _cut_span(paths["Truss-rod pocket"]) == pytest.approx(
        truss.pocket_length, abs=0.05
    )
    assert _cut_span(paths["Truss-rod channel"]) == pytest.approx(
        truss.channel_length - radius, abs=0.05
    )
    notes = " ".join(plan_neck_machining(geometry, parameters).top.notes)
    assert "each run 3 mm on over their neighbours" in notes


def test_a_flat_headstock_face_is_milled_4_mm_down() -> None:
    # At 0 degrees the face is set 4 mm below the glue face behind the nut
    # shelf, so the strings break over the nut toward the tuners.
    geometry = replace(Prototype001Parameters(), headstock_angle=0.0).build()
    top = plan_neck_machining(geometry, NeckMachiningParameters()).top
    paths = {path.name: path for path in top.toolpaths}

    assert paths["Headstock face finishing"].deepest_z() == pytest.approx(-4.0)
    assert any("milled 4 mm below the glue face" in note for note in top.notes)
    assert any("straight through" in note for note in top.notes)


def test_a_flat_headstock_not_set_down_leaves_its_face_unmilled() -> None:
    geometry = replace(
        Prototype001Parameters(), headstock_angle=0.0, headstock_face_drop=0.0
    ).build()
    top = plan_neck_machining(geometry, NeckMachiningParameters()).top
    names = [path.name for path in top.toolpaths]

    assert "Headstock face roughing" not in names
    assert "Headstock face finishing" not in names
    assert any("level with the glue face" in note for note in top.notes)


def test_a_flat_headstock_neck_comes_from_a_20_mm_plank() -> None:
    # The neck and the set-down flat headstock both end 20 mm below the
    # glue face: the plank alone is enough, with no block to glue on.
    geometry = replace(Prototype001Parameters(), headstock_angle=0.0).build()
    plan = plan_neck_machining(geometry, NeckMachiningParameters())

    assert plan.stock_thickness == 20.0
    assert plan.plank_thickness == 20.0
    assert plan.headstock_block is None
    assert not any("laminate" in note for note in plan.index_pins.notes)


def test_an_angled_headstock_block_is_as_thick_as_the_neck_plank(geometry) -> None:  # type: ignore[no-untyped-def]
    plan = plan_neck_machining(geometry, NeckMachiningParameters())
    block = plan.headstock_block
    headstock = geometry.headstock

    assert block is not None
    # The block is usually cut from the same 20 mm plank as the neck.
    assert plan.plank_thickness == 20.0 and block.thickness == 20.0
    # It starts where the headstock's back first falls below the plank.
    back = headstock.face_z(block.start_x) - headstock.thickness / math.cos(
        math.radians(headstock.angle.angle_degrees)
    )
    assert -21.0 < back <= -20.0 + 1e-6
    # It runs just past the tip, short of the tip's index pin, and is wide
    # enough for the outline cut.
    tip_pin_x = min(x for x, _ in plan.index_pin_positions)
    assert block.end_x < -headstock.plan.length
    assert tip_pin_x + 0.5 * NeckMachiningParameters().flat.index_pin_diameter < (
        block.end_x
    )
    assert block.width >= 2.0 * max(abs(p.y) for p in headstock.plan.boundary) + 12
    # A solid blank's notes offer the laminated way.
    assert any("blank='laminated'" in note for note in plan.index_pins.notes)


def test_a_laminated_blank_cuts_the_neck_first_and_the_headstock_after(  # type: ignore[no-untyped-def]
    geometry,
) -> None:
    plan = plan_neck_machining(geometry, NeckMachiningParameters(blank="laminated"))
    block = plan.headstock_block
    assert block is not None
    origin_x = plan.index_pin_positions[0][0]

    assert [setup.name for setup in plan.setups] == [
        "Neck_index_pins",
        "Neck_top",
        "Neck_back_rough",
        "Neck_back_finish",
        "Headstock_top",
        "Headstock_back_rough",
        "Headstock_back_finish",
        "Neck_back_outline",
    ]
    assert len(plan.preview_outlines) == len(plan.setups)
    assert plan.stock_thickness == plan.plank_thickness + block.thickness == 40.0

    def cuts(setup):  # type: ignore[no-untyped-def]
        return [m for p in setup.toolpaths for m in p.moves if not m.rapid]

    # Before the block: everything within the 20 mm plank, the neck's back
    # only from where the headstock needs the block on to the heel.
    assert min(m.z for m in cuts(plan.index_pins)) == pytest.approx(-20.5)
    for setup in (plan.top, plan.back_rough, plan.back_finish):
        assert min(m.z for m in cuts(setup)) >= -20.0
    for setup in (plan.back_rough, plan.back_finish):
        assert min(m.x for m in cuts(setup)) + origin_x >= block.start_x - 1e-6
    assert not any(
        "Headstock face" in path.name or "Tuner" in path.name
        for path in plan.top.toolpaths
    )
    # After it: the face and tuner marks, then the headstock's back through
    # the full 40 mm, only back to its root.
    headstock_top, headstock_rough, headstock_finish = plan.headstock_setups
    assert any("Tuner" in path.name for path in headstock_top.toolpaths)
    assert min(m.z for m in cuts(headstock_top)) < -20.0
    for setup in (headstock_rough, headstock_finish):
        assert max(m.x for m in cuts(setup)) + origin_x <= block.start_x + 6.0 + 1e-6
        assert min(m.z for m in cuts(setup)) == pytest.approx(-38.0)
    assert any("Glue the" in note for note in headstock_top.notes)
    # The outline last, through the whole 40 mm.
    assert min(m.z for m in cuts(plan.back_outline)) == pytest.approx(-40.5)


def test_a_flat_headstock_needs_no_laminating(  # type: ignore[no-untyped-def]
) -> None:
    geometry = replace(Prototype001Parameters(), headstock_angle=0.0).build()
    plan = plan_neck_machining(geometry, NeckMachiningParameters(blank="laminated"))

    assert plan.headstock_setups == () and plan.headstock_block is None
    assert plan.stock_thickness == 20.0


def test_a_given_blank_thickness_is_raised_when_too_thin_and_kept_when_thicker() -> (
    None
):
    geometry = Prototype001Parameters().build()
    thick = plan_neck_machining(geometry, NeckMachiningParameters(blank_thickness=45.0))

    assert thick.stock_thickness == 45.0


def test_the_ball_nose_alone_can_carve_the_back(geometry, plan) -> None:  # type: ignore[no-untyped-def]
    ball = plan_neck_machining(geometry, NeckMachiningParameters(back_cut="ball"))
    assert [setup.name for setup in ball.setups] == [
        "Neck_index_pins",
        "Neck_top",
        "Neck_back",
        "Neck_back_outline",
    ]
    back = ball.back_rough
    assert ball.back_finish is None
    assert back.tool.tool_tip == "ball"
    rough, finish = back.toolpaths
    assert (rough.name, finish.name) == ("Neck back roughing", "Neck back finishing")
    # Its finish is the two-program plan's own, and so is the depth.
    assert plan.back_finish is not None
    two = plan.back_finish.toolpaths[0]
    assert finish.deepest_z() == pytest.approx(two.deepest_z())
    assert len(finish.moves) == len(two.moves)
    # Layers no deeper than the ball's step-down, from the top.
    levels = sorted({round(m.z, 3) for m in rough.moves if m.z < 0.0}, reverse=True)
    assert levels[0] >= -back.tool.step_down
    assert "no tool change" in " ".join(back.notes)
    assert len(ball.preview_outlines) == len(ball.setups)


def test_a_laminated_neck_cuts_its_headstock_with_the_ball_nose_too(geometry) -> None:  # type: ignore[no-untyped-def]
    plan = plan_neck_machining(
        geometry, NeckMachiningParameters(back_cut="ball", blank="laminated")
    )
    names = [setup.name for setup in plan.setups]
    assert names == [
        "Neck_index_pins",
        "Neck_top",
        "Neck_back",
        "Headstock_top",
        "Headstock_back",
        "Neck_back_outline",
    ]
    assert "After Neck_back, glue" in " ".join(plan.index_pins.notes)
    assert len(plan.preview_outlines) == len(plan.setups)
    with pytest.raises(ToolpathError, match="back_cut"):
        NeckMachiningParameters(back_cut="flat")  # type: ignore[arg-type]
