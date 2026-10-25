"""Tests for the FreeCAD model's check against the parameter sheet."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from cncguitarwizard.backends.freecad import MEASURE_SCRIPT_NAME
from cncguitarwizard.backends.freecad.measure import MEASURED_PREFIX
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import (
    FreeCADExecutionError,
    build_prototype001,
    parameter_sheet,
)
from cncguitarwizard.workflows.model_check import (
    ModelCheck,
    measured_model,
    model_check,
)
from cncguitarwizard.workflows.parameter_sheet import READY_FOR_REVIEW, REVIEW_REQUIRED

PARAMETERS = Prototype001Parameters()
SHEET = parameter_sheet(PARAMETERS, PARAMETERS.build())

# As FreeCAD 1.1 measured the default build.
BODY_BOX = [-1.3074, -146.8388, -44.0, 459.2, 146.8388, 0.0]
NECK_BOX = [-150.635, -30.88, -36.536, 461.2, 30.88, 0.004]
BOARD_BOX = [0.0, -28.061, 0.0, 461.2, 28.061, 6.0]


def _shape(box: list[float], valid: bool = True, solids: int = 1) -> dict[str, Any]:
    return {"valid": valid, "solids": solids, "box": box}


def _found(**changes: Any) -> dict[str, Any]:
    """Return the default build's measurements, some of them changed."""
    found: dict[str, Any] = {
        "parts": {
            "NeckBack": _shape(NECK_BOX),
            "Fretboard": _shape(BOARD_BOX),
            "Body": _shape(BODY_BOX),
        },
        "step": _shape([-150.635, -146.8388, -44.0, 461.2, 146.8388, 6.0], solids=3),
        "sheet": True,
    }
    found.update(changes)
    return found


def _check(
    found: dict[str, Any], parameters: Prototype001Parameters = PARAMETERS
) -> ModelCheck:
    return model_check(measured_model(found), parameters, SHEET)


def _failed(check: ModelCheck) -> list[str]:
    return [item.name for item in check.checks if not item.passed]


def test_the_default_model_passes_every_check() -> None:
    check = _check(_found())

    assert check.status == READY_FOR_REVIEW
    assert [item.name for item in check.checks] == [
        "model_holds_its_parts",
        "model_parts_are_valid",
        "step_is_valid",
        "step_holds_the_model_solids",
        "model_holds_its_parameters",
        "step_lies_where_the_model_does",
        "body_length_in_model",
        "body_width_in_model",
        "body_back_at_thickness",
    ]
    assert json.loads(json.dumps(check.as_dict()))["status"] == READY_FOR_REVIEW


@pytest.mark.parametrize(
    ("changes", "fails"),
    [
        (
            {"parts": {"NeckBack": _shape(NECK_BOX), "Body": _shape(BODY_BOX)}},
            "model_holds_its_parts",
        ),
        (
            {
                "parts": {
                    "NeckBack": _shape(NECK_BOX),
                    "Fretboard": _shape(BOARD_BOX, valid=False),
                    "Body": _shape(BODY_BOX),
                }
            },
            "model_parts_are_valid",
        ),
        ({"sheet": False}, "model_holds_its_parameters"),
    ],
    ids=["no fretboard", "invalid part", "no spreadsheet"],
)
def test_a_missing_or_broken_part_asks_for_review(
    changes: dict[str, Any], fails: str
) -> None:
    check = _check(_found(**changes))

    assert fails in _failed(check)
    assert check.status == REVIEW_REQUIRED


def test_a_step_that_lost_a_solid_or_moved_asks_for_review() -> None:
    lost = _check(
        _found(
            step=_shape([-150.635, -146.8388, -44.0, 461.2, 146.8388, 6.0], solids=2)
        )
    )
    moved = _check(
        _found(
            step=_shape([-149.635, -146.8388, -44.0, 462.2, 146.8388, 6.0], solids=3)
        )
    )

    assert _failed(lost) == ["step_holds_the_model_solids"]
    assert _failed(moved) == ["step_lies_where_the_model_does"]


def test_a_body_unlike_the_sheet_asks_for_review() -> None:
    short = _found()
    short["parts"]["Body"] = _shape([BODY_BOX[0] + 1.0, *BODY_BOX[1:]])
    thin = _found()
    thin["parts"]["Body"] = _shape([*BODY_BOX[:2], -42.0, *BODY_BOX[3:]])
    thin["step"]["box"][2] = -42.0  # its STEP as thin as the model

    assert _failed(_check(short)) == ["body_length_in_model"]
    assert _failed(_check(thin)) == ["body_back_at_thickness"]


def test_a_body_with_a_separate_top_needs_the_top_too() -> None:
    capped = replace(PARAMETERS, body_cap_thickness=16.0)
    # The core alone is not the body: its top must be there, a part of its
    # own, the body's checks still made on the core (its back, its size).
    assert _failed(_check(_found(), capped)) == ["model_holds_its_parts"]
    core = [*BODY_BOX[:5], -16.0]
    top = [*BODY_BOX[:2], -16.0, *BODY_BOX[3:]]
    parts = {
        "NeckBack": _shape(NECK_BOX),
        "Fretboard": _shape(BOARD_BOX),
        "Body": _shape(core),
        "Top": _shape(top),
    }
    step = _shape([-150.635, -146.8388, -44.0, 461.2, 146.8388, 6.0], solids=4)
    assert _failed(_check(_found(parts=parts, step=step), capped)) == []


def test_a_neck_through_needs_no_body_part_and_gets_no_body_checks() -> None:
    parameters = replace(PARAMETERS, neck_joint="neck_through")
    found = _found()
    del found["parts"]["Body"]
    found["parts"]["Neck_block"] = _shape([-10.0, -50.0, -44.0, 400.0, 50.0, 0.0])
    found["step"] = _shape([-150.635, -50.0, -44.0, 461.2, 50.0, 6.0], solids=3)

    check = _check(found, parameters)

    assert check.status == READY_FOR_REVIEW
    assert not any(item.name.startswith("body_") for item in check.checks)


@pytest.mark.parametrize(
    "found",
    [
        {"step": _shape(NECK_BOX), "sheet": True},
        _found(step={"valid": True, "solids": 3, "box": [0.0, 0.0, 0.0]}),
        _found(parts=[1, 2]),
    ],
    ids=["no parts", "short box", "parts not by name"],
)
def test_measurements_that_do_not_read_are_refused(found: dict[str, Any]) -> None:
    with pytest.raises(FreeCADExecutionError, match="do not read"):
        measured_model(found)


def _fake_freecad(
    monkeypatch: pytest.MonkeyPatch, check: subprocess.CompletedProcess[str] | None
) -> None:
    """Make FreeCAD's runs fake: the build makes empty model files, the
    measuring script answers ``check`` (the default build's measurements
    when ``None``)."""

    def fake_run(
        arguments: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        script = Path(arguments[1])
        if script.name == MEASURE_SCRIPT_NAME:
            if check is not None:
                return check
            stdout = "FreeCAD 1.1\n" + MEASURED_PREFIX + json.dumps(_found())
            return subprocess.CompletedProcess(arguments, 0, stdout, "")
        (script.parent / "Prototype001.FCStd").touch()
        (script.parent / "Prototype001.step").touch()
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_a_freecad_build_checks_its_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_freecad(monkeypatch, None)
    command = tmp_path / "freecadcmd"
    command.touch()

    result = build_prototype001(tmp_path / "output", freecad_command=command)

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert result.model_check_status == READY_FOR_REVIEW
    assert report["status"] == "complete"
    assert report["model_check"]["status"] == READY_FOR_REVIEW
    assert report["model_check"]["script"] == MEASURE_SCRIPT_NAME
    assert report["model_check"]["parts"]["Body"]["solids"] == 1
    assert (result.output_directory / MEASURE_SCRIPT_NAME).is_file()
    assert (result.output_directory / "freecad_check.log").is_file()


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        (("FreeCAD 1.1\nExiting", ""), "printed no measurements"),
        (("", "Part.read failed"), "Part.read failed"),
    ],
    ids=["nothing printed", "FreeCAD failed"],
)
def test_a_check_that_cannot_be_made_leaves_the_model_for_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    answer: tuple[str, str],
    reason: str,
) -> None:
    stdout, stderr = answer
    code = 1 if stderr else 0
    _fake_freecad(monkeypatch, subprocess.CompletedProcess([], code, stdout, stderr))
    command = tmp_path / "freecadcmd"
    command.touch()

    result = build_prototype001(tmp_path / "output", freecad_command=command)

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert result.model_check_status == REVIEW_REQUIRED
    assert report["status"] == "complete"  # the model itself was made
    assert report["model_check"]["status"] == REVIEW_REQUIRED
    assert reason in report["model_check"]["error"]


def test_a_build_without_freecad_has_no_model_check(tmp_path: Path) -> None:
    result = build_prototype001(tmp_path / "output", run_freecad=False)

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert result.model_check_status is None
    assert "model_check" not in report
    assert not (result.output_directory / MEASURE_SCRIPT_NAME).exists()
