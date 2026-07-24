"""Tests for the complete Prototype001 build workflow."""

import json
from dataclasses import replace
from pathlib import Path

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import build_prototype001


def test_build_creates_scripts_and_traceable_report(tmp_path: Path) -> None:
    parameters = replace(
        Prototype001Parameters(),
        headstock_thickness=15.0,
    )

    result = build_prototype001(tmp_path / "output", parameters)

    assert result.macro_path.is_file()
    assert result.python_path.is_file()
    assert result.report_path.is_file()
    assert not result.fcstd_path.exists()
    assert not result.step_path.exists()
    assert result.macro_path.read_text(encoding="utf-8") == (
        result.python_path.read_text(encoding="utf-8")
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["model"] == "Prototype001"
    assert report["parameters"]["headstock_thickness"] == 15.0
    assert report["freecad_targets"]["document"] == "Prototype001.FCStd"
    assert len(report["script_sha256"]) == 64


def test_generated_script_targets_absolute_build_paths(tmp_path: Path) -> None:
    result = build_prototype001(tmp_path / "nested" / "build")
    source = result.python_path.read_text(encoding="utf-8")

    assert f'document.saveAs("{result.fcstd_path}")' in source
    assert (
        f'Part.export([neck_feature, fretboard_feature], "{result.step_path}")'
        in source
    )
