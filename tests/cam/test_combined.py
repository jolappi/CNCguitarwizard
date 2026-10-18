"""Tests for joining programs cut one after another with the same tool."""

import json
from dataclasses import replace
from pathlib import Path

from cncguitarwizard.cam import (
    GCodeWriter,
    MachiningParameters,
    Setup,
    combined_setup,
    combined_setups,
    plan_body_machining,
    setup_runs,
)
from cncguitarwizard.cam.toolpath import PathBuilder, Toolpath
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import build_prototype001

FIXTURE = "Test top face up"
PARAMETERS = MachiningParameters()


def square(name: str) -> Toolpath:
    builder = PathBuilder(name, safe_height=5.0, feed_rate=1000.0, plunge_rate=300.0)
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-2.0)
    builder.cut_to(10.0, 0.0)
    return builder.build()


def setup(name: str, **changes: object) -> Setup:
    plain = Setup(
        name,
        f"{name} description",
        (square(f"{name} square"),),
        (f"{name} note",),
        fixture=FIXTURE,
    )
    return replace(plain, **changes)


def test_setups_with_the_same_fixture_tool_and_zero_run_together() -> None:
    setups = [setup("Part_top"), setup("Part_top_controls"), setup("Part_top_more")]

    assert setup_runs(setups, PARAMETERS) == ((0, 1, 2),)


def test_a_setup_without_a_fixture_never_runs_with_another() -> None:
    setups = [setup("Part_pins", fixture=None), setup("Part_top")]

    assert setup_runs(setups, PARAMETERS) == ((0,), (1,))


def test_another_fixture_tool_or_zero_starts_another_program() -> None:
    small = replace(PARAMETERS, tool_diameter=3.0)
    setups = [
        setup("Part_top"),
        setup("Part_top_small_holes", tool=small),
        setup("Part_top_edges"),
        setup("Part_back", fixture="Test back face up"),
        setup("Part_back_zeroed", fixture="Test back face up", work_zero="centre"),
    ]

    assert setup_runs(setups, PARAMETERS) == ((0,), (1,), (2,), (3,), (4,))


def test_the_parameters_stand_in_for_a_setup_without_its_own_tool() -> None:
    setups = [setup("Part_top"), setup("Part_top_controls", tool=PARAMETERS)]

    assert setup_runs(setups, PARAMETERS) == ((0, 1),)


def test_a_combined_program_cuts_every_setup_in_turn() -> None:
    first, second = setup("Body_back"), setup("Body_back_controls")

    joined = combined_setup([first, second])

    assert joined.name == "Body_back_and_controls"
    assert joined.description == (
        "Body_back description; then Body_back_controls description"
    )
    assert joined.toolpaths == (*first.toolpaths, *second.toolpaths)
    assert joined.notes == (
        "Body_back note",
        "Then Body_back_controls: Body_back_controls description.",
        "Body_back_controls: Body_back_controls note",
    )
    assert joined.fixture == FIXTURE
    assert joined.cutting_length() == first.cutting_length() + second.cutting_length()


def test_a_combined_name_keeps_at_least_each_later_setups_last_word() -> None:
    joined = combined_setup(
        [setup("Body_top_steps"), setup("Body_top"), setup("Body_top_controls")]
    )

    assert joined.name == "Body_top_steps_and_top_and_controls"


def test_a_single_setup_is_its_own_program() -> None:
    alone = setup("Part_top")

    assert combined_setup([alone]) is alone


def test_the_body_backs_programs_with_the_main_tool_run_as_one() -> None:
    body = Prototype001Parameters().build().body
    parameters = replace(PARAMETERS, combine_programs=True)
    plan = plan_body_machining(body, parameters)

    names = [program.name for program in combined_setups(plan.setups, parameters)]

    # The dowels go in after Body_index_pins and the blank is flipped
    # after Body_top: neither runs on into the next.
    assert names == [
        "Body_index_pins",
        "Body_top",
        "Body_back_and_controls",
        "Body_back_small_holes",
    ]
    program = GCodeWriter().render(
        combined_setups(plan.setups, parameters)[2], parameters
    )
    lines = program.splitlines()
    assert lines.count("M3 S10000") == 1
    assert "(-- Outline, lower half with tabs --)" in lines
    assert "(-- Control cavity --)" in lines


def test_the_build_writes_combined_programs_when_asked(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
        machining=MachiningParameters(combine_programs=True),
    )

    names = [path.name for path in result.gcode_paths]
    assert "Body_back_and_controls_6mm_flathead.nc" in names
    assert (
        "Body_back_6mm_flathead.nc" not in names
        and "Body_back_controls_6mm_flathead.nc" not in names
    )
    assert "Body_back_and_controls_6mm_flathead.svg" in [
        path.name for path in result.toolpath_preview_paths
    ]
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    entry = report["gcode"]["Body_back_and_controls"]
    assert entry["step"] == 3
    assert report["gcode"]["Body_back_small_holes"]["step"] == 4
    assert "Control cavity" in entry["operations"]
