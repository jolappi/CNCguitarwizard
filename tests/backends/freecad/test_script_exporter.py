"""Tests for dependency-free FreeCAD script generation."""

import ast
from pathlib import Path
from typing import Callable

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.backends.freecad.exceptions import FreeCADBackendError
from cncguitarwizard.geometry.fretboard import FretboardSurface
from cncguitarwizard.geometry.neck import NeckBackSurface, NeckOutline


def make_neck_surface() -> NeckBackSurface:
    """Return a low-resolution neck surface for backend tests."""
    return NeckBackSurface(
        NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0),
        17.0,
        19.0,
        20.0,
        profile_sample_count=5,
        segments_per_region=1,
    )


def make_fretboard_surface() -> FretboardSurface:
    """Return a low-resolution fretboard surface for backend tests."""
    return FretboardSurface(609.6, 24, 42.0, 56.0, 430.0, 6.0, 5)


@pytest.mark.parametrize(
    "render_source",
    [
        lambda: FreeCADScriptExporter().render_neck_back(make_neck_surface()),
        lambda: FreeCADScriptExporter().render_fretboard(
            make_fretboard_surface()
        ),
    ],
)
def test_generated_freecad_source_is_valid_python(
    render_source: Callable[[], str],
) -> None:
    source = render_source()

    ast.parse(source)
    assert "Part.makeLoft(sections, True, False, False)" in source
    assert "document.recompute()" in source


def test_neck_script_contains_one_section_for_each_surface_row() -> None:
    surface = make_neck_surface()
    source = FreeCADScriptExporter().render_neck_back(surface)
    module = ast.parse(source)
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "SECTION_POINTS"
    )

    assert isinstance(assignment, ast.Assign)
    assert isinstance(assignment.value, ast.List)
    assert len(assignment.value.elts) == len(surface.mesh.rows)


def test_fretboard_sections_close_at_the_flat_underside() -> None:
    source = FreeCADScriptExporter().render_fretboard(
        make_fretboard_surface()
    )

    assert ",0.0],[0.0,-21.0,0.0]" in source


def test_exporter_writes_python_and_macro_files(tmp_path: Path) -> None:
    exporter = FreeCADScriptExporter()
    source = exporter.render_neck_back(make_neck_surface())
    destination = tmp_path / "Prototype001_Neck.FCMacro"

    exporter.write_script(destination, source)

    assert destination.read_text(encoding="utf-8") == source


def test_script_can_save_fcstd_and_export_step(tmp_path: Path) -> None:
    fcstd_path = tmp_path / "Prototype001_Neck.FCStd"
    step_path = tmp_path / "Prototype001_Neck.step"

    source = FreeCADScriptExporter().render_neck_back(
        make_neck_surface(),
        fcstd_path=fcstd_path,
        step_path=step_path,
    )

    assert f'document.saveAs("{fcstd_path}")' in source
    assert f'Part.export([feature], "{step_path}")' in source
    assert source.index("document.recompute()") < source.index(
        "document.saveAs"
    )
    assert source.index("document.saveAs") < source.index("Part.export")


def test_script_omits_output_commands_when_paths_are_not_given() -> None:
    source = FreeCADScriptExporter().render_neck_back(make_neck_surface())

    assert "document.saveAs" not in source
    assert "Part.export" not in source


def test_exporter_rejects_unsafe_names_and_file_suffixes(
    tmp_path: Path,
) -> None:
    exporter = FreeCADScriptExporter()

    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_back(
            make_neck_surface(),
            document_name="invalid-name",
        )
    with pytest.raises(FreeCADBackendError):
        exporter.write_script(tmp_path / "neck.txt", "source")
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_back(
            make_neck_surface(),
            fcstd_path=tmp_path / "neck.step",
        )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_back(
            make_neck_surface(),
            step_path=tmp_path / "neck.stl",
        )
