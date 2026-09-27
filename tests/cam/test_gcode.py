"""Tests for the G-code writer and its dialects."""

import re
from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    POST_PROCESSOR_LABELS,
    GCodeWriter,
    GRBLWriter,
    MachiningParameters,
    Setup,
    Toolpath,
)
from cncguitarwizard.cam.exceptions import ToolpathError
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


def test_preview_draws_each_cut_as_a_tool_wide_band() -> None:
    from cncguitarwizard.cam import MachiningParameters, render_setup_svg
    from cncguitarwizard.cam.operations import pocket
    from cncguitarwizard.geometry.primitives import Point2D

    parameters = MachiningParameters()
    square = [
        Point2D(0.0, 0.0),
        Point2D(40.0, 0.0),
        Point2D(40.0, 40.0),
        Point2D(0.0, 40.0),
    ]
    setup = Setup("Test", "test", (pocket("Pocket", square, 5.0, parameters),))

    svg = render_setup_svg(setup, square, parameters.tool_diameter)

    assert 'stroke-width="6.00" stroke-opacity="0.25"' in svg
    assert "Shaded bands show the 6 mm tool width" in svg
    assert 'stroke-width="6.00"' not in render_setup_svg(setup, square)


def test_writer_names_a_setups_own_work_zero() -> None:
    setup = make_setup()
    own_zero = Setup(
        setup.name,
        setup.description,
        setup.toolpaths,
        work_zero="the centre of the cover, Z at the sheet top",
    )
    lines = GRBLWriter().render(own_zero, MachiningParameters()).splitlines()

    assert "(Work zero: the centre of the cover, Z at the sheet top)" in lines
    assert "(Start over the work zero - check it here)" in lines
    assert lines[-3] == "(Return over the work zero)"
    assert not any("index pin" in line for line in lines)


def moves(source: str) -> list[str]:
    """Return the program's G0/G1 lines, which every dialect shares."""
    return [line for line in source.splitlines() if re.match(r"G[01] ", line)]


def test_every_dialect_writes_the_same_moves() -> None:
    setup, parameters = make_setup(), MachiningParameters()
    grbl = GCodeWriter().render(setup, parameters)
    # KOSY writes two decimals and nccad's own feed units (see below).
    for dialect in (d for d in POST_PROCESSOR_LABELS if d != "kosy"):
        source = GCodeWriter(dialect).render(setup, parameters)
        assert moves(source) == moves(grbl), dialect


def test_the_default_writer_is_grbl() -> None:
    setup, parameters = make_setup(), MachiningParameters()

    assert GRBLWriter is GCodeWriter
    assert GCodeWriter().render(setup, parameters) == GCodeWriter("grbl").render(
        setup, parameters
    )
    assert "G4" not in GCodeWriter().render(setup, parameters)


def test_marlin_uses_semicolon_comments_and_no_end_code() -> None:
    lines = (
        GCodeWriter("marlin").render(make_setup(), MachiningParameters()).splitlines()
    )

    # A ; comment runs to the end of the line: brackets need no escaping.
    assert "; Setup: Test setup (square)" in lines
    assert not any(line.startswith("(") for line in lines)
    assert "G17" not in lines and "G94" not in lines
    assert lines[-1] == "G0 X0.000 Y0.000"


def test_fanuc_wraps_the_program_and_changes_the_tool() -> None:
    lines = (
        GCodeWriter("fanuc").render(make_setup(), MachiningParameters()).splitlines()
    )

    assert lines[0] == "%" and lines[-1] == "%"
    assert lines[1] == "O1000 (CNCGUITARWIZARD TEST)"
    assert "(SETUP: TEST SETUP [SQUARE])" in lines
    assert lines.index("T1 M6") < lines.index("S10000 M3")
    assert lines[-2] == "M30"


def test_the_spindle_dwell_is_written_in_each_dialects_units() -> None:
    parameters = MachiningParameters(spindle_dwell=2.5)
    expected = {
        "grbl": "G4 P2.500",
        "linuxcnc": "G4 P2.500",
        "mach3": "G4 P2500",
        "marlin": "G4 P2500",
        "fanuc": "G4 X2.500",
    }
    for dialect, dwell in expected.items():
        writer = GCodeWriter.for_parameters(replace(parameters, post_processor=dialect))
        lines = writer.render(make_setup(), parameters).splitlines()
        spindle = next(i for i, line in enumerate(lines) if "M3" in line)
        assert lines[spindle + 1] == dwell, dialect


def test_an_unknown_post_processor_is_rejected() -> None:
    with pytest.raises(ToolpathError, match="post_processor"):
        MachiningParameters(post_processor="haas")  # type: ignore[arg-type]


def test_kosy_writes_a_knc_program_in_nccads_units() -> None:
    writer = GCodeWriter("kosy")
    lines = writer.render(make_setup(), MachiningParameters()).splitlines()

    assert writer.extension == ".knc" and GCodeWriter().extension == ".nc"
    assert lines[:2] == ["_", "_"]
    assert "; Setup: Test setup (square)" in lines
    assert "G90" in lines and "G21" not in lines
    # Relay 6 switches the spindle; nccad takes no spindle speed.
    assert lines.index("M10 O6.1") < lines.index("M10 O6.0")
    assert not any(line.startswith("M3") for line in lines)
    body = [line for line in lines if re.match(r"G[01] ", line)]
    # Two decimals, and feeds in nccad's units: mm/min / 6.
    assert "G1 Z-2.00 F50.0" in body
    assert "G1 X10.00 F166.7" in body
    assert lines[-1] == "G99"


def test_kosy_caps_feeds_at_ncads_fastest_and_says_so() -> None:
    parameters = MachiningParameters(
        feed_rate=1800.0, spindle_dwell=2.0, post_processor="kosy"
    )
    builder = PathBuilder("Fast", safe_height=5.0, feed_rate=1800.0, plunge_rate=300.0)
    builder.rapid_to(0.0, 0.0)
    builder.plunge_to(-1.0)
    builder.cut_to(20.0, 0.0)
    setup = Setup("Fast", "Fast cut", (builder.build(),))
    writer = GCodeWriter.for_parameters(parameters)
    lines = writer.render(setup, parameters).splitlines()

    assert "; Feeds over 1200 mm/min are cut at nccad's F200" in lines
    assert any(line.endswith("F200.0") for line in lines)
    # The dwell counts 1/18 s.
    assert lines[lines.index("M10 O6.1") + 1] == "M30 P36"
