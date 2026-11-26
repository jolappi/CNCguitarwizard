"""Tests for feeding the cutter faster through air it has already cut."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import GCodeWriter, MachiningParameters, Setup, air_fed
from cncguitarwizard.cam.air import AIR_CLEARANCE
from cncguitarwizard.cam.exceptions import ToolpathError
from cncguitarwizard.cam.toolpath import Move, PathBuilder

AIR = replace(MachiningParameters(), air_feed_rate=3000.0)


def _builder() -> PathBuilder:
    return PathBuilder("Test", safe_height=5.0, feed_rate=1000.0, plunge_rate=300.0)


def _setup(builder: PathBuilder) -> Setup:
    return Setup("Test", "Test setup", (builder.build(),))


def _peck_setup() -> Setup:
    # A hole pecked twice: back up to the top between them.
    builder = _builder()
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-3.0)
    builder.lift_to(0.0)
    builder.plunge_to(-6.0)
    return _setup(builder)


def test_without_an_air_feed_the_program_is_left_as_it_is() -> None:
    setup = _peck_setup()

    assert air_fed(setup, MachiningParameters()) is setup


def test_a_peck_goes_back_down_its_hole_at_the_air_feed() -> None:
    moves = air_fed(_peck_setup(), AIR).toolpaths[0].moves

    # The first peck plunges into wood; the second goes back down the
    # hole fast and slows to the plunge feed 1 mm over its floor.
    assert moves[1] == Move(0.0, 0.0, -3.0, False, 300.0)
    assert moves[3] == Move(0.0, 0.0, -2.0, False, 3000.0)
    assert moves[4] == Move(0.0, 0.0, -6.0, False, 300.0)


def test_straight_down_through_air_is_no_faster_than_the_z_lift_speed() -> None:
    parameters = replace(AIR, z_lift_rate=600.0)
    moves = air_fed(_peck_setup(), parameters).toolpaths[0].moves

    assert moves[3] == Move(0.0, 0.0, -2.0, False, 600.0)


def test_the_cutter_slows_before_it_meets_wood_again() -> None:
    # A slot cut along X, then back along it and on past its start into
    # wood the program has not cut.
    builder = _builder()
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-2.0)
    builder.cut_to(20.0, 0.0)
    builder.cut_to(-10.0, 0.0)
    moves = air_fed(_setup(builder), AIR).toolpaths[0].moves
    back = moves[3:-1]

    # The way back is split, the path itself the same: along the slot at
    # the air feed, off its start at the cutting feed again.
    assert [(m.y, m.z) for m in back] == [(0.0, -2.0)] * len(back)
    assert back[-1] == Move(-10.0, 0.0, -2.0, False, 1000.0)
    fast = [(start, end) for start, end in zip(moves, moves[1:]) if end.feed == 3000.0]
    assert len(fast) == 1
    start, end = fast[0]
    # Clear of the wood it just cut at the slot's end, and of the wood
    # past its start (the cutter's edge reaches it 3 mm short of it).
    assert 20.0 - AIR_CLEARANCE >= start.x > 15.0
    assert AIR_CLEARANCE <= end.x < 5.0


@pytest.mark.parametrize("tip", ["flat", "ball", "vee"])
def test_a_pass_over_a_stretch_already_cut_is_air(tip: str) -> None:
    builder = _builder()
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-1.0)
    builder.cut_to(30.0, 0.0)
    builder.cut_to(0.0, 0.0)
    parameters = replace(AIR, tool_tip=tip)
    moves = air_fed(_setup(builder), parameters).toolpaths[0].moves

    assert any(move.feed == 3000.0 for move in moves[3:])


def test_a_ball_pass_half_a_cell_beside_one_already_cut_is_wood() -> None:
    # Half a 1 mm grid cell over, the ball cuts the wood beside the first
    # pass deeper: measured from where the cutter is, not from the
    # nearest cell, that is wood all along it.
    builder = _builder()
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-1.0)
    builder.cut_to(30.0, 0.0)
    builder.cut_to(30.0, 0.5)
    builder.cut_to(0.0, 0.5)
    setup = _setup(builder)
    parameters = replace(AIR, tool_tip="ball")

    assert air_fed(setup, parameters).toolpaths == setup.toolpaths


def test_wood_the_program_never_cut_is_never_air() -> None:
    # One pass through stock: however high the stock top is, it is wood.
    builder = _builder()
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(2.0)
    builder.cut_to(50.0, 0.0)
    setup = _setup(builder)

    assert air_fed(setup, AIR).toolpaths == setup.toolpaths


def test_the_program_says_its_air_feed() -> None:
    setup = air_fed(_peck_setup(), AIR)
    text = GCodeWriter.for_parameters(AIR).render(setup, AIR)

    assert "(Air feed F3000: through wood this program has already cut away)" in text
    assert "G1 Z-2.000 F3000" in text


def test_kosy_says_when_the_air_feed_is_over_its_fastest() -> None:
    parameters = replace(AIR, post_processor="kosy")
    setup = air_fed(_peck_setup(), parameters)
    text = GCodeWriter.for_parameters(parameters).render(setup, parameters)

    assert "; Feeds over 1200 mm/min are cut at nccad's F200" in text


def test_a_negative_air_feed_is_rejected() -> None:
    with pytest.raises(ToolpathError, match="air_feed_rate"):
        MachiningParameters(air_feed_rate=-1.0)
