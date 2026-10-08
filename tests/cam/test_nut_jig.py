"""Tests for the sheet program that cuts the nut-slot filing jig."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    MachiningParameters,
    ToolpathError,
    nut_jig_tool,
    plan_nut_jig_machining,
)
from cncguitarwizard.geometry.neck.nut_jig import NutSlotJig
from cncguitarwizard.presets import Prototype001Parameters

SLOT_TOOL = FretboardMachiningParameters().slot


def _jig() -> NutSlotJig:
    jig = Prototype001Parameters(nut_jig=True).nut_slot_jig()
    assert jig is not None
    return jig


def test_no_jig_means_no_program() -> None:
    assert plan_nut_jig_machining(None, nut_jig_tool(SLOT_TOOL, 0.6)) is None


def test_the_slots_first_then_the_outline_through_the_sheet() -> None:
    jig = _jig()
    plan = plan_nut_jig_machining(jig, nut_jig_tool(SLOT_TOOL, 0.6))
    assert plan is not None
    (setup,) = plan.setups
    assert setup.name == "Jig_nut_slots"
    assert setup.tool is not None and setup.tool.tool_diameter == 0.6
    # The fret-slot cutter's speed and step-down.
    assert setup.tool.spindle_speed == 30000.0
    assert setup.tool.step_down == 0.2
    names = [path.name for path in setup.toolpaths]
    assert names[0] == "Slot 1 - .046 in string, 1.22 mm"
    assert names[-1] == "Nut-slot jig - outline"
    assert len(names) == 7
    # Through the 3 mm sheet, 0.5 mm into the spoilboard, no tabs.
    for path in setup.toolpaths:
        assert min(move.z for move in path.moves) == pytest.approx(-3.5)
    assert plan.stock_thickness == 3.0
    (preview,) = plan.preview_outlines
    assert [(p.x, p.y) for p in preview] == pytest.approx(
        [(p.x, p.y) for p in _framed(jig, jig.outline)]
    )


def _framed(jig: NutSlotJig, points):  # type: ignore[no-untyped-def]
    xs = [p.x for p in jig.body]
    ys = [p.y for p in jig.body]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    return [type(p)(p.x - cx, p.y - cy) for p in points]


def test_each_slot_is_cut_its_own_width_from_its_floor_up() -> None:
    jig = _jig()
    tool = nut_jig_tool(SLOT_TOOL, 0.3)
    plan = plan_nut_jig_machining(jig, tool)
    assert plan is not None
    (setup,) = plan.setups
    (origin,) = _framed(jig, [jig.body[0]])
    shift_x, shift_y = origin.x - jig.body[0].x, origin.y - jig.body[0].y
    for slot, path in zip(jig.slots, setup.toolpaths, strict=False):
        cuts = [move for move in path.moves if not move.rapid and move.z < 0.0]
        xs = [move.x - shift_x for move in cuts]
        ys = [move.y - shift_y for move in cuts]
        # The cutter's sides on the slot's walls, its round end on the
        # floor; it runs out past the jig's top.
        assert min(xs) - 0.15 == pytest.approx(slot.centre - slot.width / 2.0)
        assert max(xs) + 0.15 == pytest.approx(
            slot.centre + slot.width / 2.0 if slot.width > 0.3 else slot.centre + 0.15
        )
        assert min(ys) - 0.15 == pytest.approx(slot.floor)
        assert max(ys) > slot.top + 0.15
        # Never more than 0.8 of the cutter between neighbouring lines.
        lines = sorted(set(round(x, 6) for x in xs))
        assert all(b - a <= 0.24 + 1e-9 for a, b in zip(lines, lines[1:]))
    # With a cutter no wider than the thinnest slot nothing is too wide.
    assert not any("come out" in note for note in setup.notes)


def test_slots_narrower_than_the_cutter_are_named() -> None:
    plan = plan_nut_jig_machining(_jig(), nut_jig_tool(SLOT_TOOL, 0.6))
    assert plan is not None
    (setup,) = plan.setups
    (note,) = [note for note in setup.notes if "come out" in note]
    assert "strings 4, 5, 6 come out 0.6 mm wide" in note
    assert "no wider than 0.30 mm" in note
    # The narrow slots are one line each.
    narrow = setup.toolpaths[5]
    assert len({round(move.x, 6) for move in narrow.moves if move.z < 0.0}) == 1


def test_a_cutter_too_wide_for_the_leg_corners_is_refused() -> None:
    with pytest.raises(ToolpathError, match="nut_jig_tool_diameter"):
        plan_nut_jig_machining(_jig(), nut_jig_tool(SLOT_TOOL, 1.5))
    with pytest.raises(ToolpathError):
        MachiningParameters(nut_jig_tool_diameter=0.0)


def test_the_build_writes_the_jig_program() -> None:
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from cncguitarwizard.workflows.prototype001 import Prototype001Build

    with TemporaryDirectory() as folder:
        build = Prototype001Build(
            Path(folder),
            Prototype001Parameters(nut_jig=True),
            run_freecad=False,
            machining=replace(MachiningParameters(), nut_jig_tool_diameter=0.4),
        )
        while build.advance():
            pass
        gcode = (Path(folder) / "Jig_nut_slots.nc").read_text()
        assert (Path(folder) / "Jig_nut_slots.svg").exists()
    assert "(Tool: 0.400 mm end mill" in gcode
    assert "Nut-slot filing jig" in gcode
