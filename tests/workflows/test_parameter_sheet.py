"""Tests for the parameter sheet: key dimensions, their sources and checks."""

import csv
import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import advance_build, finish_build, start_build
from cncguitarwizard.workflows import (
    ParameterSheet,
    build_prototype001,
    parameter_sheet,
)
from cncguitarwizard.workflows.parameter_sheet import (
    CSV_COLUMNS,
    DEFAULT,
    DERIVED,
    DESIGN,
    INSTRUMENT,
    READY_FOR_REVIEW,
    REVIEW_REQUIRED,
    SHEET_FIELDS,
    TO_CONFIRM,
    SheetCheck,
    SheetRow,
)


def _sheet(parameters: Prototype001Parameters) -> ParameterSheet:
    return parameter_sheet(parameters, parameters.build())


def _row(sheet: ParameterSheet, name: str) -> SheetRow:
    return next(row for row in sheet.rows if row.name == name)


def _check(sheet: ParameterSheet, name: str) -> SheetCheck:
    return next(check for check in sheet.checks if check.name == name)


def test_the_default_design_passes_every_check() -> None:
    sheet = _sheet(Prototype001Parameters())

    octave = _check(sheet, "octave_fret_at_half_scale")
    temperament = _check(sheet, "frets_follow_equal_temperament")

    assert sheet.status == READY_FOR_REVIEW
    assert octave.expected == pytest.approx(304.8)
    assert octave.actual == pytest.approx(304.8, abs=1e-9)
    assert octave.unit == "mm"
    assert temperament.expected == 0.0
    assert temperament.actual < 1e-9


def test_every_listed_setting_is_on_the_sheet_with_its_unit() -> None:
    sheet = _sheet(Prototype001Parameters())

    settings = [row for row in sheet.rows if row.source != DERIVED]

    assert [(row.group, row.name, row.unit) for row in settings] == list(SHEET_FIELDS)
    assert _row(sheet, "scale_length").value == 609.6
    assert _row(sheet, "bass_scale_length").value is None
    assert _row(sheet, "body_bridge").value == "kahler_7300"
    assert _row(sheet, "body_shape").value == "your_design"


def test_the_derived_values_come_from_the_built_geometry() -> None:
    parameters = Prototype001Parameters()
    geometry = parameters.build()
    sheet = parameter_sheet(parameters, geometry)

    assert _row(sheet, "centre_scale").value == 609.6
    assert _row(sheet, "last_fret_position").value == pytest.approx(457.2)
    assert _row(sheet, "fretboard_end_position").value == pytest.approx(
        geometry.fretboard_surface.station_positions[-1], abs=1e-4
    )
    assert _row(sheet, "saddle_line_position").value == pytest.approx(609.6)
    assert _row(sheet, "neck_angle_degrees").value == 0.0
    assert _row(sheet, "body_length").value == pytest.approx(460.5, abs=0.1)
    assert _row(sheet, "body_width").value == pytest.approx(293.7, abs=0.1)
    assert all(row.source == DERIVED for row in sheet.rows if row.group == "Derived")


def test_each_setting_says_where_its_value_came_from() -> None:
    parameters = replace(
        Prototype001Parameters.for_instrument("bass_guitar"), nut_width=40.0
    )

    sheet = _sheet(parameters)

    assert _row(sheet, "nut_width").source == DESIGN
    assert _row(sheet, "scale_length").source == INSTRUMENT
    assert _row(sheet, "instrument").source == INSTRUMENT
    assert _row(sheet, "body_thickness").source == DEFAULT


@pytest.mark.parametrize(
    "changes",
    [
        {"bass_scale_length": 647.7},
        {"fret_slant_angle": 5.0},
        {"handedness": "left"},
        {"frets_per_octave": 24, "fret_count": 48},
    ],
    ids=["multiscale", "slanted", "left-handed", "microtonal"],
)
def test_the_checks_hold_on_fanned_slanted_mirrored_and_microtonal_necks(
    changes: dict[str, Any],
) -> None:
    parameters = replace(Prototype001Parameters(), **changes)

    sheet = _sheet(parameters)

    octave = _check(sheet, "octave_fret_at_half_scale")
    assert sheet.status == READY_FOR_REVIEW
    assert octave.expected == pytest.approx(parameters.centre_scale / 2.0)
    assert str(parameters.frets_per_octave) in octave.description


def test_a_failed_check_asks_for_review() -> None:
    off = SheetCheck(
        name="octave_fret_at_half_scale",
        description="Fret 12 at half the scale.",
        expected=304.8,
        actual=304.9,
        tolerance=0.01,
        unit="mm",
    )
    sheet = ParameterSheet(rows=(), checks=(off,))

    rows = list(csv.DictReader(io.StringIO(sheet.as_csv())))

    assert not off.passed
    assert sheet.status == REVIEW_REQUIRED
    assert sheet.as_dict()["status"] == REVIEW_REQUIRED
    assert rows[0]["value"] == REVIEW_REQUIRED
    assert rows[1]["result"] == "failed"


def test_the_csv_has_one_row_a_value() -> None:
    sheet = _sheet(Prototype001Parameters())

    reader = csv.DictReader(io.StringIO(sheet.as_csv()))
    rows = list(reader)

    assert tuple(reader.fieldnames or ()) == CSV_COLUMNS
    assert len(rows) == 1 + len(sheet.rows) + len(sheet.checks) + len(TO_CONFIRM)
    assert rows[0]["name"] == "status"
    assert rows[0]["value"] == READY_FOR_REVIEW
    scale = next(row for row in rows if row["name"] == "scale_length")
    assert (scale["value"], scale["unit"], scale["source"]) == (
        "609.6",
        "mm",
        DEFAULT,
    )
    fan = next(row for row in rows if row["name"] == "bass_scale_length")
    assert fan["value"] == ""
    octave = next(row for row in rows if row["name"] == "octave_fret_at_half_scale")
    assert octave["source"] == "check"
    assert (octave["value"], octave["expected"]) == ("304.8", "304.8")
    assert octave["tolerance"] == "0.01"
    assert octave["result"] == "passed"
    assert [row["value"] for row in rows if row["group"] == "To confirm"] == list(
        TO_CONFIRM
    )


def test_the_build_writes_the_sheet_and_reports_it(tmp_path: Path) -> None:
    result = build_prototype001(tmp_path / "build", run_freecad=False)

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    parameters = Prototype001Parameters()
    expected = parameter_sheet(parameters, parameters.build())

    assert result.parameter_sheet_path.name == "Prototype001_parameters.csv"
    assert result.parameter_sheet_path.read_text(encoding="utf-8") == (
        expected.as_csv()
    )
    assert report["generated_files"]["parameter_sheet"] == (
        "Prototype001_parameters.csv"
    )
    assert report["parameter_sheet"] == expected.as_dict()
    assert report["parameter_sheet"]["status"] == READY_FOR_REVIEW


def test_the_web_build_offers_the_sheet(tmp_path: Path) -> None:
    started = start_build({"prototype": {}, "machining": {}}, str(tmp_path))
    assert "error" not in started
    step = advance_build()
    while not step.get("done"):
        assert "error" not in step
        step = advance_build()

    result = finish_build()

    assert result["files"]["Prototype001_parameters.csv"].startswith(
        ",".join(CSV_COLUMNS)
    )
    assert result["report"]["parameter_sheet"]["status"] == READY_FOR_REVIEW
