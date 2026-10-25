"""Tests for the cutters every NC program is cut with: each one's size and
how deep it cuts a pass, half its diameter unless set."""

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    MachiningParameters,
    plan_body_machining,
    plan_neck_machining,
)
from cncguitarwizard.cam.neck import NeckMachiningParameters
from cncguitarwizard.presets import Prototype001Parameters


def test_a_depth_per_pass_of_0_is_half_the_cutter() -> None:
    plain = MachiningParameters()
    assert plain.step_down == 3.0
    assert MachiningParameters(tool_diameter=8.0).step_down == 4.0
    assert MachiningParameters(tool_diameter=8.0, step_down=2.5).step_down == 2.5

    # Each cutter its own size, half of it a pass unless set.
    assert (plain.small_cutter.tool_diameter, plain.small_cutter.step_down) == (3, 1.5)
    small = MachiningParameters(small_hole_step_down=1.0).small_cutter
    assert small.step_down == 1.0
    assert (plain.ball_cutter.tool_tip, plain.ball_cutter.tool_diameter) == ("ball", 6)
    assert plain.ball_cutter.step_down == 3.0
    ball = MachiningParameters(ball_tool_diameter=4.0).ball_cutter
    assert (ball.tool_diameter, ball.step_down) == (4.0, 2.0)
    assert plain.relief_cutter.step_down == 1.5
    # The carve: the main tool unless its own, a big flat end mill only set.
    assert plain.carve_cutter is plain
    assert MachiningParameters(carve_step_down=2.0).carve_cutter.step_down == 2.0
    carve = MachiningParameters(carve_tool_diameter=10.0).carve_cutter
    assert (carve.tool_diameter, carve.step_down) == (10.0, 5.0)
    assert plain.carve_flat_cutter is None
    big = MachiningParameters(carve_flat_tool_diameter=25.4).carve_flat_cutter
    assert big is not None and big.step_down == pytest.approx(12.7)
    # The tiny cutters stay shallow: they snap.
    assert (plain.fret_slot_step_down, plain.inlay_step_down) == (0.2, 0.2)
    assert (plain.fret_slot_tool_diameter, plain.inlay_tool_diameter) == (0.6, 1.0)


def test_small_holes_are_cut_half_the_small_cutter_a_pass() -> None:
    body = Prototype001Parameters().build().body
    plan = plan_body_machining(body, MachiningParameters())

    assert plan.back_small_holes is not None
    tool = plan.back_small_holes.tool
    assert tool is not None and (tool.tool_diameter, tool.step_down) == (3.0, 1.5)


def test_the_neck_and_fretboard_cut_with_the_forms_cutters() -> None:
    # Regression: the neck's and fretboard's programs kept their own 6 mm
    # tools at 10 000 rpm whatever the machining form said.
    form = MachiningParameters(
        tool_diameter=8.0,
        spindle_speed=16000.0,
        ball_tool_diameter=4.0,
        fret_slot_tool_diameter=0.5,
        inlay_tool_diameter=0.8,
    )
    neck = NeckMachiningParameters().with_form_settings(form)
    board = FretboardMachiningParameters().with_form_settings(form)

    for flat in (neck.flat, board.flat):
        assert (flat.tool_diameter, flat.step_down, flat.spindle_speed) == (8, 4, 16000)
        assert flat.stock_margin == 35.0  # the part's own blank kept
    for ball in (neck.ball, board.ball):
        assert (ball.tool_tip, ball.tool_diameter, ball.step_down) == ("ball", 4, 2)
        assert ball.spindle_speed == 16000.0
    assert board.slot.tool_diameter == 0.5 and board.slot.step_down == 0.2
    assert board.inlay.tool_diameter == 0.8 and board.inlay.step_down == 0.2


def test_a_flat_end_mill_too_wide_for_the_truss_rod_leaves_it_to_the_small() -> None:
    # Regression: an 8 mm flat end mill, the neck's now, could not cut the
    # 6 mm truss-rod channel and the build stopped.
    geometry = Prototype001Parameters().build()
    form = MachiningParameters(tool_diameter=8.0)
    neck = NeckMachiningParameters().with_form_settings(form)
    plan = plan_neck_machining(geometry, neck, form)

    assert not any(path.name.startswith("Truss-rod") for path in plan.top.toolpaths)
    small = plan.small_holes
    assert small is not None and small.tool is not None
    assert (small.tool.tool_diameter, small.tool.step_down) == (3.0, 1.5)
    assert small.toolpaths[0].name == "Truss-rod channel"
    assert "truss-rod route" in small.description
    assert any("narrower than the 8 mm flat end mill" in note for note in small.notes)
    # A 6 mm one cuts it on the glue face, as before.
    plain = plan_neck_machining(
        geometry, NeckMachiningParameters(), MachiningParameters()
    )
    assert plain.top.toolpaths[0].name == "Truss-rod channel"
