"""Tests for the single-sided fretboard machining plan on Prototype001."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    MachiningParameters,
    ToolpathError,
    fretboard_outline_polygon,
    plan_fretboard_machining,
)
from cncguitarwizard.cam.gcode import GCodeWriter
from cncguitarwizard.cam.inlays import plan_inlay_machining
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import parameter_schema


@pytest.fixture(scope="module")
def geometry():  # type: ignore[no-untyped-def]
    return Prototype001Parameters().build()


@pytest.fixture(scope="module")
def parameters() -> FretboardMachiningParameters:
    return FretboardMachiningParameters()


@pytest.fixture(scope="module")
def plan(geometry, parameters):  # type: ignore[no-untyped-def]
    return plan_fretboard_machining(geometry, parameters)


def test_outline_is_the_tapered_board_with_square_nut_corners(geometry) -> None:  # type: ignore[no-untyped-def]
    polygon = fretboard_outline_polygon(geometry)

    assert min(point.x for point in polygon) == pytest.approx(0.0)
    assert max(point.x for point in polygon) == pytest.approx(461.2)
    assert max(point.y for point in polygon) == pytest.approx(28.06, abs=0.01)
    # Square nut corners: the outline is exactly the four-corner trapezoid.
    assert len(polygon) == 4
    assert Point2D(0.0, 21.0) in polygon and Point2D(0.0, -21.0) in polygon
    assert point_in_polygon(Point2D(230.0, 0.0), polygon)


def test_outline_rounds_the_nut_corners_when_asked(geometry) -> None:  # type: ignore[no-untyped-def]
    from dataclasses import replace

    from cncguitarwizard.presets import Prototype001Parameters

    rounded = replace(Prototype001Parameters(), fretboard_nut_corner_radius=8.0).build()
    polygon = fretboard_outline_polygon(rounded)

    assert len(polygon) > 4
    assert all(math.hypot(point.x, abs(point.y) - 21.0) > 2.0 for point in polygon)


def test_plan_has_five_setups_in_tool_order(plan, parameters) -> None:  # type: ignore[no-untyped-def]
    assert [setup.name for setup in plan.setups] == [
        "Fretboard_index_pins",
        "Fretboard_radius",
        "Fretboard_inlays",
        "Fretboard_slots",
        "Fretboard_outline",
    ]
    assert plan.radius.tool is parameters.ball
    assert plan.inlays.tool is parameters.inlay
    assert plan.slots.tool is parameters.slot
    assert len(plan.inlays.toolpaths) == 12
    assert len(plan.slots.toolpaths) == 24


def test_radius_surface_sits_at_the_crown_and_drops_toward_the_edges(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    skim = parameters.blank_thickness - geometry.fretboard_surface.center_thickness
    origin_y = plan.origin_y
    moves = [move for move in plan.radius.toolpaths[0].moves if not move.rapid]

    def expected(model_y: float) -> float:
        return -(skim + 430.0 - math.sqrt(430.0**2 - model_y**2))

    crown = min(moves, key=lambda move: abs(move.y + origin_y))
    assert abs(crown.y + origin_y) < 0.6
    assert crown.z == pytest.approx(expected(crown.y + origin_y), abs=0.01)
    edge = [move for move in moves if abs(abs(move.y + origin_y) - 28.0) < 0.6]
    assert edge
    # Never below the surface; the pass itself sits on it (the link moves
    # between passes hover a little higher).
    for move in edge:
        assert move.z >= expected(move.y + origin_y) - 0.01
    assert min(move.z for move in edge) == pytest.approx(
        expected(edge[0].y + origin_y), abs=0.05
    )
    assert min(move.z for move in edge) < crown.z - 0.8


def test_fret_slots_follow_the_radius_across_the_board(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    skim = parameters.blank_thickness - geometry.fretboard_surface.center_thickness
    depth = geometry.fret_slot_depth
    first = plan.slots.toolpaths[0]
    origin_x, origin_y = plan.index_pin_positions[0]
    cut_moves = [move for move in first.moves if not move.rapid]

    assert first.name == "Fret 1 slot"
    slot_x = geometry.fret_layout.slots[0].start.x
    assert all(abs(move.x + origin_x - slot_x) < 1e-6 for move in cut_moves)
    centre = [move for move in cut_moves if abs(move.y + origin_y) < 0.51]
    assert min(move.z for move in centre) == pytest.approx(-(skim + depth), abs=0.01)
    half = abs(geometry.fret_layout.slots[0].start.y) + parameters.slot_overshoot
    assert max(abs(move.y + origin_y) for move in cut_moves) == pytest.approx(half)
    # Passes of at most 0.2 mm, so the 0.6 mm cutter does not snap, at
    # 30 000 rpm.
    depths = sorted({round(move.z, 3) for move in centre}, reverse=True)
    assert len(depths) == math.ceil(depth / 0.2 - 1e-9)
    assert all(a - b <= 0.2 + 1e-6 for a, b in zip(depths, depths[1:], strict=False))
    assert plan.slots.tool is not None
    assert plan.slots.tool.spindle_speed == 30000.0
    assert plan.slots.tool.step_down == 0.2


def test_inlay_pockets_are_cut_from_the_crown_to_their_depth(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    skim = parameters.blank_thickness - geometry.fretboard_surface.center_thickness
    for path in plan.inlays.toolpaths:
        assert path.deepest_z() == pytest.approx(-(skim + geometry.inlay_layout.depth))


def test_outline_and_pins(plan, geometry, parameters) -> None:  # type: ignore[no-untyped-def]
    polygon = fretboard_outline_polygon(geometry)
    (x1, y1), (x2, y2) = plan.index_pin_positions

    assert x1 < 0.0 and x2 > 461.2 and y1 == 0.0 and y2 == 0.0
    assert plan.outline.toolpaths[0].deepest_z() == pytest.approx(
        -(parameters.blank_thickness + parameters.flat.through_overshoot)
    )
    assert plan.stock_thickness == parameters.blank_thickness
    assert not point_in_polygon(Point2D(x1, y1), polygon)


def test_blank_thinner_than_the_board_is_rejected(geometry) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ToolpathError, match="thick"):
        plan_fretboard_machining(
            geometry, FretboardMachiningParameters(blank_thickness=5.0)
        )


def test_the_machining_form_sets_the_fret_slot_cutter(geometry) -> None:  # type: ignore[no-untyped-def]
    machining = MachiningParameters(
        fret_slot_spindle_speed=24000.0, fret_slot_step_down=0.3
    )
    plan = plan_fretboard_machining(
        geometry, FretboardMachiningParameters().with_form_settings(machining)
    )
    tool = plan.slots.tool
    assert tool is not None
    assert tool.spindle_speed == 24000.0 and tool.step_down == 0.3
    assert f"in {math.ceil(geometry.fret_slot_depth / 0.3 - 1e-9)} passes" in " ".join(
        plan.slots.notes
    )
    program = GCodeWriter.for_parameters(machining).render(plan.slots, machining)
    assert "M3 S24000" in program
    # The defaults: 30 000 rpm, 0.2 mm a pass.
    default = MachiningParameters()
    assert default.fret_slot_spindle_speed == 30000.0
    assert default.fret_slot_step_down == 0.2
    with pytest.raises(ToolpathError, match="fret_slot_step_down"):
        MachiningParameters(fret_slot_step_down=0.0)
    fields = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }
    for name in (
        "fret_slot_spindle_speed",
        "fret_slot_step_down",
        "inlay_spindle_speed",
        "inlay_step_down",
    ):
        assert not fields[name]["advanced"] and fields[name]["help"]


def test_the_inlay_cutter_is_fast_and_shallow_too(geometry) -> None:  # type: ignore[no-untyped-def]
    default = plan_fretboard_machining(geometry, FretboardMachiningParameters())
    tool = default.inlays.tool
    assert tool is not None
    assert tool.spindle_speed == 30000.0 and tool.step_down == 0.2
    # Every pocket in passes of at most 0.2 mm down to its floor.
    levels = sorted(
        {round(move.z, 3) for move in default.inlays.toolpaths[0].moves if move.z < 0},
        reverse=True,
    )
    assert all(a - b <= 0.2 + 1e-6 for a, b in zip(levels, levels[1:], strict=False))
    machining = MachiningParameters(inlay_spindle_speed=28000.0, inlay_step_down=0.4)
    tuned = FretboardMachiningParameters().with_form_settings(machining)
    plan = plan_fretboard_machining(geometry, tuned)
    assert plan.inlays.tool is not None
    assert plan.inlays.tool.spindle_speed == 28000.0
    assert plan.inlays.tool.step_down == 0.4
    pieces = plan_inlay_machining(geometry.inlay_layout, tuned)
    assert pieces is not None and pieces.pieces.tool is not None
    assert pieces.pieces.tool.spindle_speed == 28000.0
    assert "M3 S28000" in GCodeWriter.for_parameters(machining).render(
        pieces.pieces, machining
    )


@pytest.mark.parametrize("nut_style", ["shelf", "zero_fret"])
def test_every_slot_starts_one_step_into_the_radius(nut_style: str) -> None:
    """No slot starts deeper than a pass: its cutter comes down over the
    radius at the start and feeds in one step."""
    geometry = replace(Prototype001Parameters(), nut_style=nut_style).build()  # type: ignore[arg-type]
    parameters = FretboardMachiningParameters()
    plan = plan_fretboard_machining(geometry, parameters)
    surface = geometry.fretboard_surface
    skim = parameters.blank_thickness - surface.center_thickness
    origin_y = plan.index_pin_positions[0][1]

    def radius_z(machine_y: float) -> float:
        y = machine_y + origin_y
        return -(skim + surface.radius - math.sqrt(surface.radius**2 - y**2))

    step = parameters.slot.step_down
    for path in plan.slots.toolpaths:
        first = next(move for move in path.moves if not move.rapid)
        assert radius_z(first.y) - first.z <= step + 1e-6
        # Rapids stay over the radius, the last one 1 mm over it.
        rapids = [move for move in path.moves if move.rapid]
        assert all(move.z >= radius_z(move.y) + 1.0 - 1e-6 for move in rapids)
    assert any("not on the radiused surface" in note for note in plan.slots.notes)
