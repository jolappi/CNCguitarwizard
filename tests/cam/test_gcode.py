"""Tests for the GRBL G-code writer."""

import re

from cncguitarwizard.cam import GRBLWriter, MachiningParameters, Setup, Toolpath
from cncguitarwizard.cam.toolpath import Move, PathBuilder


def make_setup() -> Setup:
    builder = PathBuilder(
        "Square", safe_height=5.0, feed_rate=1000.0, plunge_rate=300.0
    )
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-2.0)
    builder.cut_to(10.0, 0.0)
    builder.cut_to(10.0, 10.0)
    builder.cut_to(0.0, 10.0)
    builder.cut_to(0.0, 0.0)
    return Setup("Test", "Test setup (square)", (builder.build(),), ("Note one",))


def test_writer_emits_a_grbl_program_with_header_and_footer() -> None:
    source = GRBLWriter().render(make_setup(), MachiningParameters())
    lines = source.splitlines()

    assert lines[1] == "(Setup: Test setup [square])"
    assert "(Note one)" in lines
    assert "G21" in lines and "G90" in lines and "G17" in lines
    assert "M3 S10000" in lines
    # Every program starts and ends parked over index pin 1.
    assert lines.index("G0 X0.000 Y0.000") < lines.index("M3 S10000")
    assert lines[-5:] == [
        "M5",
        "G0 Z5.000",
        "(Return over index pin 1)",
        "G0 X0.000 Y0.000",
        "M2",
    ]
    assert "(-- Square --)" in lines


def test_writer_omits_unchanged_words_and_repeats_feed_only_on_change() -> None:
    source = GRBLWriter().render(make_setup(), MachiningParameters())
    body = source.split("(-- Square --)")[1].split("\nM5")[0].splitlines()[1:]

    # The rapid to (0, 0) at the safe height is where the program already
    # is, so nothing is written for it.
    assert body[0] == "G1 Z-2.000 F300"
    assert body[1] == "G1 X10.000 F1000"
    assert body[2] == "G1 Y10.000"
    assert body[-1] == "G0 Z5.000"
    assert all(re.fullmatch(r"G[01]( [XYZF]-?\d+(\.\d{3})?)+", line) for line in body)


def test_writer_visits_reference_points_before_starting_the_spindle() -> None:
    setup = make_setup()
    with_reference = Setup(
        setup.name, setup.description, setup.toolpaths, setup.notes, ((426.0, 0.0),)
    )
    lines = GRBLWriter().render(with_reference, MachiningParameters()).splitlines()
    start = lines.index("G0 X0.000 Y0.000")

    assert lines[start + 1 : start + 5] == [
        "(Check dowel 2)",
        "G0 X426.000 Y0.000",
        "(Back over index pin 1)",
        "G0 X0.000 Y0.000",
    ]
    assert lines[start + 5] == "M3 S10000"


def test_setup_lengths_and_time_estimate() -> None:
    setup = make_setup()
    parameters = MachiningParameters(rapid_rate=3000.0)

    # The plunge starts at the 5 mm safe height: 7 mm down, 40 mm around,
    # and a 7 mm rapid back up.
    assert setup.cutting_length() == 47.0
    assert setup.rapid_length() == 7.0
    minutes = setup.estimated_minutes(parameters)
    assert minutes == (7.0 / 300.0) + (40.0 / 1000.0) + (7.0 / 3000.0)


def test_path_builder_never_rapids_below_the_safe_height() -> None:
    builder = PathBuilder("P", safe_height=5.0, feed_rate=1000.0, plunge_rate=300.0)
    builder.rapid_to(1.0, 1.0)
    builder.plunge_to(-4.0)
    builder.rapid_to(20.0, 20.0)
    path = builder.build()

    rapids = [move for move in path.moves if move.rapid]
    assert all(move.z >= 5.0 for move in rapids)
    assert path.moves[2] == Move(1.0, 1.0, 5.0, True)


def test_empty_toolpath_lengths_are_zero() -> None:
    path = Toolpath("Empty", ())

    assert path.cutting_length() == 0.0
    assert path.rapid_length() == 0.0
    assert path.deepest_z() == 0.0
