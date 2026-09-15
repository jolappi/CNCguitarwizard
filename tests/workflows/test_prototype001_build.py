"""Tests for the complete Prototype001 build workflow."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import FreeCADExecutionError, build_prototype001


def test_build_creates_scripts_and_traceable_report(tmp_path: Path) -> None:
    parameters = replace(
        Prototype001Parameters(),
        headstock_thickness=15.0,
    )

    result = build_prototype001(
        tmp_path / "output",
        parameters,
        run_freecad=False,
    )

    assert result.macro_path.is_file()
    assert result.python_path.is_file()
    assert result.report_path.is_file()
    assert not result.freecad_log_path.exists()
    assert not result.fcstd_path.exists()
    assert not result.step_path.exists()
    assert result.macro_path.read_text(encoding="utf-8") == (
        result.python_path.read_text(encoding="utf-8")
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["model"] == "Prototype001"
    assert report["status"] == "scripts_only"
    assert report["parameters"]["headstock_thickness"] == 15.0
    assert report["freecad_targets"]["document"] == "Prototype001.FCStd"
    assert len(report["script_sha256"]) == 64


def test_build_writes_body_gcode_and_toolpath_previews(tmp_path: Path) -> None:
    result = build_prototype001(tmp_path / "output", run_freecad=False)

    assert [path.name for path in result.gcode_paths] == [
        "Body_index_pins.nc",
        "Body_top.nc",
        "Body_back.nc",
    ]
    assert [path.name for path in result.toolpath_preview_paths] == [
        "Body_index_pins.svg",
        "Body_top.svg",
        "Body_back.svg",
    ]
    for path in (*result.gcode_paths, *result.toolpath_preview_paths):
        assert path.is_file()
    top = result.gcode_paths[1].read_text(encoding="utf-8")
    assert top.splitlines()[0].startswith("(CNCguitarwizard")
    assert "(-- Neck pocket --)" in top
    assert top.rstrip().endswith("M2")

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["machining"]["tool_diameter"] == 6.0
    assert report["gcode"]["Body_top"]["file"] == "Body_top.nc"
    assert report["gcode"]["Body_top"]["estimated_minutes"] > 0.0
    assert report["stock"]["thickness_mm"] == 44.0
    assert report["stock"]["work_origin_model_xy"] == [420.0, 0.0]


def test_generated_script_targets_absolute_build_paths(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "nested" / "build",
        run_freecad=False,
    )
    source = result.python_path.read_text(encoding="utf-8")

    assert f'document.saveAs("{result.fcstd_path}")' in source
    assert (
        "Part.export([neck_feature, fretboard_feature, body_feature], "
        f'"{result.step_path}")' in source
    )


def test_default_build_includes_the_headstock_instead_of_hiding_it(
    tmp_path: Path,
) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
    )
    source = result.python_path.read_text(encoding="utf-8")

    assert "headstock_feature = document.addObject" not in source
    assert "headstock_feature.ViewObject.Visibility = False" not in source
    assert "neck_shape = require_shape(" in source
    assert "neck_shape = fuse_or_compound(" in source


def test_complete_build_runs_freecad_and_verifies_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        arguments: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        output = Path(arguments[1]).parent
        (output / "Prototype001.FCStd").touch()
        (output / "Prototype001.step").touch()
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    command = tmp_path / "freecadcmd"
    command.touch()

    result = build_prototype001(
        tmp_path / "output",
        freecad_command=command,
    )

    assert result.fcstd_path.is_file()
    assert result.step_path.is_file()
    assert result.freecad_log_path.is_file()
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["status"] == "complete"


def test_complete_build_replaces_previous_model_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    old_fcstd = output / "Prototype001.FCStd"
    old_step = output / "Prototype001.step"
    old_fcstd.write_text("old", encoding="utf-8")
    old_step.write_text("old", encoding="utf-8")

    def fake_run(
        arguments: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        old_fcstd.write_text("new", encoding="utf-8")
        old_step.write_text("new", encoding="utf-8")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    command = tmp_path / "freecadcmd"
    command.touch()

    build_prototype001(output, freecad_command=command)

    assert old_fcstd.read_text(encoding="utf-8") == "new"
    assert old_step.read_text(encoding="utf-8") == "new"


def test_build_rejects_failed_or_incomplete_freecad_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = tmp_path / "freecadcmd"
    command.touch()

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args,
            1,
            "",
            "BREP failure",
        ),
    )
    with pytest.raises(FreeCADExecutionError, match="BREP failure"):
        build_prototype001(tmp_path / "failed", freecad_command=command)
    failed_report = json.loads(
        (tmp_path / "failed" / "build.json").read_text(encoding="utf-8")
    )
    assert failed_report["status"] == "failed"
    assert "BREP failure" in (
        tmp_path / "failed" / "freecad.log"
    ).read_text(encoding="utf-8")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )
    with pytest.raises(FreeCADExecutionError, match="without creating"):
        build_prototype001(tmp_path / "missing", freecad_command=command)
