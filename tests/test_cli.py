"""Tests for CNCguitarwizard command-line workflows."""

from pathlib import Path

from cncguitarwizard.__main__ import main


def test_build_prototype001_command_creates_package(
    tmp_path: Path,
    capsys: object,
) -> None:
    output = tmp_path / "build"

    main(["build-prototype001", "--output", str(output)])

    assert (output / "Prototype001.FCMacro").is_file()
    assert (output / "Prototype001_freecad.py").is_file()
    assert (output / "build.json").is_file()
