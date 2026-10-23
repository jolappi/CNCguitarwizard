"""Tests for the finished model exported to other 3D formats."""

import pytest

from cncguitarwizard.backends.freecad import (
    EXPORT_FORMATS,
    export_script_name,
    render_format_export,
)
from cncguitarwizard.backends.freecad.exceptions import FreeCADBackendError


def test_an_export_script_writes_each_part_and_the_whole_in_each_format() -> None:
    source = render_format_export(["stl", "glb"])

    # Plain Python for FreeCAD to run, reading the model the build made.
    compile(source, "Prototype001_export.py", "exec")
    assert 'FORMATS = ["stl", "glb"]' in source
    assert 'DOCUMENT = "Prototype001.FCStd"' in source
    # A mesh within 0.05 mm of the surface; each part a file, then the whole.
    assert "LINEAR_DEFLECTION = 0.05" in source
    assert 'name = f"{stem}_{part.Label}.{extension}"' in source
    assert 'export(parts, os.path.join(folder, f"{stem}.{extension}"), extension)' in (
        source
    )
    assert 'print(f"WROTE {os.path.basename(path)}")' in source
    assert export_script_name(["stl"]) == "Prototype001_export_stl.py"
    assert export_script_name(["stl", "glb"]) == "Prototype001_export.py"
    assert set(EXPORT_FORMATS) == {"stl", "3mf", "obj", "glb", "iges", "brep"}


@pytest.mark.parametrize(
    ("formats", "message"),
    [
        ([], "at least one"),
        (["dwg"], "Unknown 3D format dwg"),
        (["stl", "stl"], "once"),
    ],
)
def test_no_format_an_unknown_one_or_one_twice_is_refused(
    formats: list[str], message: str
) -> None:
    with pytest.raises(FreeCADBackendError, match=message):
        render_format_export(formats)
