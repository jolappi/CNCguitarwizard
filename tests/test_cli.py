"""Tests for CNCguitarwizard command-line workflows."""

import json
from pathlib import Path

import pytest

from cncguitarwizard.__main__ import main


def test_build_prototype001_command_creates_package(
    tmp_path: Path,
    capsys: object,
) -> None:
    output = tmp_path / "build"

    main(
        [
            "build-prototype001",
            "--output",
            str(output),
            "--scripts-only",
        ]
    )

    assert (output / "Prototype001.FCMacro").is_file()
    assert (output / "Prototype001_freecad.py").is_file()
    assert (output / "build.json").is_file()


def _design(prototype: dict[str, object], instrument: str = "bass_guitar") -> str:
    return json.dumps(
        {
            "format": "cncguitarwizard-design",
            "version": 1,
            "name": "Bolt bass",
            "instrument": instrument,
            "prototype": prototype,
            "machining": {"feed_rate": 900.0},
        }
    )


def test_build_prototype001_builds_a_saved_design(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    design = tmp_path / "bass.json"
    design.write_text(
        _design({"body_thickness": 42.0, "old_setting": 1}), encoding="utf-8"
    )
    output = tmp_path / "build"

    main(
        [
            "build-prototype001",
            "--design",
            str(design),
            "--output",
            str(output),
            "--scripts-only",
        ]
    )

    report = json.loads((output / "build.json").read_text(encoding="utf-8"))
    # The design's values on the bass's own defaults.
    assert report["parameters"]["body_thickness"] == 42.0
    assert report["parameters"]["string_count"] == 4
    assert report["machining"]["feed_rate"] == 900.0
    printed = capsys.readouterr().out
    assert "Design: bass.json (Bolt bass)" in printed
    assert "does not know: old_setting" in printed


def test_build_prototype001_refuses_a_file_that_is_not_a_design(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = tmp_path / "other.json"
    other.write_text('{"format": "something else"}', encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["build-prototype001", "--design", str(other), "--scripts-only"])

    assert "not a CNCguitarwizard design file" in capsys.readouterr().err
