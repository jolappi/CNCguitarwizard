"""Tests for turning a part's programs a quarter to fit the machine."""

import json
from dataclasses import replace
from pathlib import Path

from cncguitarwizard.cam import (
    GCodeWriter,
    MachiningParameters,
    Setup,
    fitted_to_machine,
    program_span,
)
from cncguitarwizard.cam.toolpath import PathBuilder, Toolpath
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import build_prototype001

OUTLINE = (Point2D(0.0, -20.0), Point2D(800.0, -20.0), Point2D(800.0, 20.0))


def long_path(length: float) -> Toolpath:
    builder = PathBuilder("Long", safe_height=5.0, feed_rate=1000.0, plunge_rate=300.0)
    builder.rapid_to(10.0, -20.0)
    builder.plunge_to(-2.0)
    builder.cut_to(length, 20.0)
    return builder.build()


def part(length: float) -> Setup:
    return Setup(
        "Part_top",
        "A long part",
        (long_path(length),),
        ("Its own note.",),
        reference_points=((length - 5.0, 0.0),),
    )


def machine(x: float | None, y: float | None) -> MachiningParameters:
    return replace(MachiningParameters(), machine_x_travel=x, machine_y_travel=y)


def test_the_span_counts_the_work_zero_and_the_dowels() -> None:
    assert program_span([part(800.0)]) == (800.0, 40.0)


def test_without_the_machines_travel_every_part_runs_sideways() -> None:
    setup = part(800.0)

    fit = fitted_to_machine([setup], [OUTLINE], MachiningParameters())

    assert fit.setups == (setup,) and fit.outlines == (OUTLINE,)
    assert not fit.turned and fit.fits is None


def test_a_part_that_fits_along_x_stays_sideways() -> None:
    setup = part(700.0)

    fit = fitted_to_machine([setup], [OUTLINE], machine(750.0, 1000.0))

    assert fit.setups == (setup,)
    assert not fit.turned and fit.fits is True


def test_a_part_longer_than_x_but_not_y_runs_along_y() -> None:
    setup = part(800.0)

    fit = fitted_to_machine([setup], [OUTLINE], machine(750.0, 1000.0))

    (turned,) = fit.setups
    assert fit.turned and fit.fits is True
    assert fit.span == (40.0, 800.0)
    before = setup.toolpaths[0].moves
    after = turned.toolpaths[0].moves
    assert [(m.x, m.y, m.z) for m in after] == [(-m.y + 0.0, m.x, m.z) for m in before]
    assert turned.reference_points == ((0.0, 795.0),)
    assert fit.outlines[0][1] == Point2D(20.0, 800.0)
    assert turned.notes[0].startswith(
        "Turned a quarter to fit the machine's 750 x 1000"
    )
    assert turned.notes[1:] == setup.notes
    # The cutting is the same, only turned.
    assert turned.cutting_length() == setup.cutting_length()
    assert "-0.000" not in GCodeWriter().render(turned, MachiningParameters())


def test_one_travel_limits_only_its_own_axis() -> None:
    assert fitted_to_machine([part(800.0)], [OUTLINE], machine(750.0, None)).turned
    assert not fitted_to_machine([part(800.0)], [OUTLINE], machine(None, 30.0)).turned


def test_a_part_too_big_either_way_stays_sideways_and_says_so() -> None:
    setup = part(800.0)

    fit = fitted_to_machine([setup], [OUTLINE], machine(500.0, 600.0))

    assert not fit.turned and fit.fits is False
    assert fit.setups[0].toolpaths == setup.toolpaths
    assert fit.setups[0].notes[0] == (
        "Too big for the machine's 500 x 600 mm travel either way: it needs "
        "800 x 40 mm."
    )


def test_a_bass_neck_runs_along_y_on_a_750_by_1000_machine(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        Prototype001Parameters.for_instrument("bass_guitar"),
        run_freecad=False,
        machining=machine(750.0, 1000.0),
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    neck, body = report["stock"]["Neck"], report["stock"]["Body"]
    assert neck["machine_turned"] is True and neck["fits_machine"] is True
    assert neck["machine_span_mm"][0] < 750.0 < neck["machine_span_mm"][1]
    # The far dowel lies along the machine's Y now.
    (_, far) = neck["index_pins_machine_xy"]
    assert abs(far[0]) < 1.0 and far[1] > 750.0
    assert body["machine_turned"] is False and body["fits_machine"] is True
    top = (tmp_path / "output" / "Neck_top.nc").read_text(encoding="utf-8")
    assert "(Turned a quarter to fit the machine's 750 x 1000 mm travel" in top
