"""Tests for the complete Prototype001 build workflow."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import (
    BuildWorkflowError,
    FreeCADExecutionError,
    Prototype001Build,
    build_prototype001,
)


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


def test_build_writes_gcode_and_toolpath_previews_for_every_part(
    tmp_path: Path,
) -> None:
    result = build_prototype001(tmp_path / "output", run_freecad=False)

    names = [path.name for path in result.gcode_paths]
    assert names[:3] == ["Body_index_pins.nc", "Body_top.nc", "Body_back.nc"]
    assert "Neck_back_finish.nc" in names and "Fretboard_slots.nc" in names
    # Body 5 (with the electronics program), neck 5, fretboard 5, the
    # inlay pieces, and the control and switch cavity covers.
    assert len(names) == 18
    assert names[15] == "Fretboard_inlay_pieces.nc"
    assert "Body_back_small_holes.nc" in names
    assert names[-2:] == ["Cover_control_cavity.nc", "Cover_switch_cavity.nc"]
    assert [path.name for path in result.toolpath_preview_paths] == [
        name.replace(".nc", ".svg") for name in names
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
    assert report["gcode"]["Body_top"]["part"] == "Body"
    # Each part's programs are numbered in running order.
    steps = {
        part: sorted(
            (info["step"], name)
            for name, info in report["gcode"].items()
            if info["part"] == part
        )
        for part in ("Body", "Neck", "Fretboard")
    }
    assert steps["Body"][:2] == [(1, "Body_index_pins"), (2, "Body_top")]
    assert steps["Neck"] == [
        (1, "Neck_index_pins"),
        (2, "Neck_top"),
        (3, "Neck_back_rough"),
        (4, "Neck_back_finish"),
        (5, "Neck_back_outline"),
    ]
    assert [name for _, name in steps["Fretboard"]] == [
        "Fretboard_index_pins",
        "Fretboard_radius",
        "Fretboard_inlays",
        "Fretboard_slots",
        "Fretboard_outline",
    ]
    assert [step for step, _ in steps["Fretboard"]] == [1, 2, 3, 4, 5]
    assert report["gcode"]["Neck_back_finish"]["tool"] == "6 mm ball"
    assert report["gcode"]["Fretboard_slots"]["tool"] == "0.6 mm flat"
    assert set(report["stock"]) == {"Body", "Neck", "Fretboard", "Inlays", "Covers"}
    # The barbed-wire markers are cut from a 2 mm sheet in their own program.
    pieces = report["gcode"]["Fretboard_inlay_pieces"]
    assert (pieces["part"], pieces["step"]) == ("Inlays", 1)
    assert report["stock"]["Inlays"]["thickness_mm"] == 2.0
    assert report["gcode"]["Cover_control_cavity"]["tool"] == "3 mm flat"
    assert report["stock"]["Body"]["thickness_mm"] == 44.0
    # The default 24-fret neck takes a 440 mm stock rod (455 mm at most).
    assert report["truss_rod"]["rod_length_mm"] == 440.0
    assert report["truss_rod"]["recommended_stock_mm"] == 440.0
    assert report["truss_rod"]["longest_fitting_mm"] == pytest.approx(455.2)
    # The 8 degree headstock needs 36.6 mm; or a 20 mm plank with a block.
    neck = report["stock"]["Neck"]
    assert neck["thickness_mm"] == 36.6
    assert neck["laminated"]["plank_thickness_mm"] == 20.0
    assert neck["blank"] == "solid"
    assert neck["laminated"]["headstock_block_mm"]["thickness"] == 20.0
    assert len(report["stock"]["Fretboard"]["index_pins_model_xy"]) == 2


def test_stepwise_build_runs_one_stage_per_advance(tmp_path: Path) -> None:
    build = Prototype001Build(tmp_path / "output", run_freecad=False)

    assert build.labels == (
        "Building the geometry",
        "Planning the body toolpaths",
        "Planning the neck toolpaths",
        "Planning the fretboard toolpaths",
        "Planning the cover plates",
        "Writing G-code and toolpath previews",
        "Writing the DXF outlines",
        "Writing the FreeCAD script and report",
    )
    assert build.completed == 0 and not build.done
    with pytest.raises(BuildWorkflowError):
        build.result
    assert build.advance() is True
    assert build.completed == 1 and build.geometry is not None
    assert not (tmp_path / "output" / "Body_top.nc").exists()
    steps = 1
    while build.advance():
        steps += 1
    steps += 1
    assert steps == len(build.labels) and build.done
    assert build.advance() is False
    result = build.result
    assert result.report_path.is_file()
    assert len(result.gcode_paths) == 18
    assert Prototype001Build(tmp_path / "freecad").labels[-1] == "Running FreeCAD"


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
    assert "BREP failure" in (tmp_path / "failed" / "freecad.log").read_text(
        encoding="utf-8"
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )
    with pytest.raises(FreeCADExecutionError, match="without creating"):
        build_prototype001(tmp_path / "missing", freecad_command=command)


def test_build_writes_every_program_in_the_chosen_dialect(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
        machining=MachiningParameters(post_processor="fanuc", spindle_dwell=2.0),
    )
    for path in result.gcode_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "%" and lines[-1] == "%", path.name
        assert "G4 X2.000" in lines, path.name


def test_build_writes_kosy_programs_as_knc_files(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
        machining=MachiningParameters(post_processor="kosy"),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert result.gcode_paths
    assert all(path.suffix == ".knc" for path in result.gcode_paths)
    assert report["gcode"]["Body_top"]["file"] == "Body_top.knc"
    first = result.gcode_paths[0].read_text(encoding="utf-8").splitlines()
    assert first[:2] == ["_", "_"] and first[-1] == "G99"


def test_build_writes_the_laminated_neck_programs(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
        machining=MachiningParameters(neck_blank="laminated"),
    )
    names = [path.name for path in result.gcode_paths]
    report = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert names.index("Neck_back_finish.nc") < names.index("Headstock_top.nc")
    assert names.index("Headstock_back_finish.nc") < names.index("Neck_back_outline.nc")
    assert report["stock"]["Neck"]["blank"] == "laminated"
    assert report["stock"]["Neck"]["thickness_mm"] == 40.0
    assert report["gcode"]["Headstock_top"]["part"] == "Neck"


def test_build_reports_a_fretboard_blank_on_its_carrier(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
        machining=MachiningParameters(
            fretboard_blank_length=500.0,
            fretboard_blank_width=70.0,
            fretboard_carrier_thickness=12.0,
        ),
    )
    stock = json.loads(result.report_path.read_text(encoding="utf-8"))["stock"]
    fretboard = stock["Fretboard"]
    assert (fretboard["length_mm"], fretboard["width_mm"]) == (500.0, 70.0)
    assert fretboard["carrier"]["length_mm"] == 527.2
    assert fretboard["carrier"]["thickness_mm"] == 12.0
    assert "carrier" not in stock["Neck"]


def test_build_carves_the_neck_back_with_the_ball_nose_alone(tmp_path: Path) -> None:
    result = build_prototype001(
        tmp_path / "output",
        run_freecad=False,
        machining=MachiningParameters(neck_back_cut="ball"),
    )
    names = [path.name for path in result.gcode_paths]
    assert "Neck_back.nc" in names
    assert "Neck_back_rough.nc" not in names
    assert "Neck_back_finish.nc" not in names
