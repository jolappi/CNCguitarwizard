"""Tests for dependency-free FreeCAD script generation."""

import ast
from pathlib import Path
from typing import Callable

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.backends.freecad.exceptions import FreeCADBackendError
from cncguitarwizard.geometry.fretboard import (
    Fretboard,
    FretboardSurface,
    FretLayout,
)
from cncguitarwizard.geometry.neck import (
    Centerline,
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
    NeckBackSurface,
    NeckOutline,
    TrussRodChannel,
    TunerLayout,
)


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


def make_truss_rod_channel(
    outline: NeckOutline | None = None,
    depth: float = 9.0,
) -> TrussRodChannel:
    """Return the locked rectangular double-action truss-rod channel."""
    return TrussRodChannel(
        outline or make_neck_surface().neck_outline,
        12.0,
        440.0,
        6.0,
        depth,
        adjustment_side="heel",
    )


def make_fret_layout(
    scale_length: float = 609.6,
    fret_count: int = 24,
) -> FretLayout:
    """Return a fret layout aligned with the Prototype001 surface."""
    final_fret_fraction = 1.0 - 2.0 ** (-fret_count / 12.0)
    bridge_width = 42.0 + (56.0 - 42.0) / final_fret_fraction
    fretboard = Fretboard(
        scale_length,
        42.0,
        bridge_width,
        Centerline(scale_length),
    )
    return FretLayout(fretboard, fret_count)


def make_headstock(thickness: float = 16.0) -> HeadstockSolid:
    """Return the angled Prototype001 headstock solid."""
    return HeadstockSolid(
        HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0),
        HeadstockAngleReference(150.0, 8.0),
        thickness,
    )


def make_tuner_layout(
    plan: HeadstockPlan | None = None,
) -> TunerLayout:
    """Return the locked six-hole Prototype001 tuner layout."""
    return TunerLayout(
        plan or make_headstock().plan,
        hole_diameter=10.0,
    )


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


def test_neck_assembly_creates_two_separate_features(tmp_path: Path) -> None:
    step_path = tmp_path / "Prototype001_Assembly.step"

    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        step_path=step_path,
    )

    ast.parse(source)
    assert 'document.addObject("Part::Feature", "NeckBack")' in source
    assert 'document.addObject("Part::Feature", "Fretboard")' in source
    assert "neck_shape = make_loft(NECK_SECTION_POINTS)" in source
    assert "neck_feature.Shape = neck_shape" in source
    assert "fretboard_shape = make_loft(FRETBOARD_SECTION_POINTS)" in source
    assert "fretboard_feature.Shape = fretboard_shape" in source
    assert (
        f'Part.export([neck_feature, fretboard_feature], "{step_path}")'
        in source
    )


def test_neck_assembly_serializes_both_surface_row_sets() -> None:
    neck_surface = make_neck_surface()
    fretboard_surface = make_fretboard_surface()
    source = FreeCADScriptExporter().render_neck_assembly(
        neck_surface,
        fretboard_surface,
    )
    module = ast.parse(source)
    assignments = {
        node.targets[0].id: node.value
        for node in module.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
    }

    neck_rows = assignments["NECK_SECTION_POINTS"]
    fretboard_rows = assignments["FRETBOARD_SECTION_POINTS"]
    assert isinstance(neck_rows, ast.List)
    assert isinstance(fretboard_rows, ast.List)
    assert len(neck_rows.elts) == len(neck_surface.mesh.rows)
    assert len(fretboard_rows.elts) == len(fretboard_surface.mesh.rows)


def test_neck_assembly_can_cut_the_truss_rod_channel() -> None:
    surface = make_neck_surface()
    channel = make_truss_rod_channel(surface.neck_outline)

    source = FreeCADScriptExporter().render_neck_assembly(
        surface,
        make_fretboard_surface(),
        truss_rod_channel=channel,
    )

    assert (
        "truss_rod_shape = Part.makeBox("
        "440.0, 6.0, 9.0, App.Vector(12.0, -3.0, -9.0))"
        in source
    )
    assert "neck_shape = neck_shape.cut(truss_rod_shape)" in source
    assert source.index("neck_shape.cut") < source.index(
        "neck_feature.Shape = neck_shape"
    )


def test_neck_assembly_omits_truss_rod_cut_by_default() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
    )

    assert "truss_rod_shape" not in source
    assert "neck_shape.cut" not in source


def test_neck_assembly_can_cut_radius_following_fret_slots() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        fret_layout=make_fret_layout(),
        fret_slot_width=0.6,
        fret_slot_depth=2.7,
    )

    assert "FRET_SURFACE_ROWS = " in source
    assert "fret_slot_width = 0.6" in source
    assert "fret_slot_depth = 2.7" in source
    assert "for surface_row in FRET_SURFACE_ROWS:" in source
    assert "face.extrude(App.Vector(fret_slot_width, 0.0, 0.0))" in source
    assert "fretboard_shape = fretboard_shape.cut(slot_shape)" in source


def test_neck_assembly_omits_fret_slot_cuts_by_default() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
    )

    assert "FRET_SURFACE_ROWS" not in source
    assert "fretboard_shape.cut" not in source


def test_neck_assembly_can_include_an_angled_headstock() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=make_headstock(),
    )

    assert "HEADSTOCK_BOUNDARY = " in source
    assert "headstock_face.extrude(" in source
    assert 'document.addObject("Part::Feature", "Headstock")' in source
    assert "headstock_feature.Shape = headstock_shape" in source


def test_headstock_is_included_in_step_export(tmp_path: Path) -> None:
    step_path = tmp_path / "Prototype001.step"
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=make_headstock(14.0),
        step_path=step_path,
    )

    assert (
        "Part.export([neck_feature, fretboard_feature, headstock_feature], "
        f'"{step_path}")' in source
    )


def test_headstock_can_be_joined_to_the_neck_for_manufacturing(
    tmp_path: Path,
) -> None:
    step_path = tmp_path / "Prototype001_Wood.step"
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=make_headstock(),
        tuner_layout=make_tuner_layout(),
        join_headstock_to_neck=True,
        step_path=step_path,
    )

    assert "neck_shape = neck_shape.fuse(headstock_shape)" in source
    assert source.count("neck_feature.Shape = neck_shape") == 2
    assert "headstock_feature = document.addObject" not in source
    assert (
        f'Part.export([neck_feature, fretboard_feature], "{step_path}")'
        in source
    )


def test_headstock_can_receive_six_normal_tuner_holes() -> None:
    headstock = make_headstock()
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=headstock,
        tuner_layout=make_tuner_layout(headstock.plan),
    )

    module = ast.parse(source)
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "TUNER_HOLES"
    )
    assert isinstance(assignment.value, ast.List)
    assert len(assignment.value.elts) == 6
    assert "cutter = Part.makeCylinder(" in source
    assert "diameter / 2.0" in source
    assert "headstock_shape = headstock_shape.cut(cutter)" in source
    assert "tuner_chamfer_depth = 0.2" in source
    assert "chamfer = Part.makeCone(" in source
    assert "diameter / 2.0 + tuner_chamfer_depth" in source
    assert "headstock_shape = headstock_shape.cut(chamfer)" in source


def test_tuner_chamfer_can_be_disabled() -> None:
    headstock = make_headstock()
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=headstock,
        tuner_layout=make_tuner_layout(headstock.plan),
        tuner_chamfer_depth=0.0,
    )

    assert "tuner_chamfer_depth = 0.0" in source


def test_headstock_omits_tuner_holes_by_default() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=make_headstock(),
    )

    assert "TUNER_HOLES" not in source
    assert "Part.makeCylinder" not in source


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
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            neck_object_name="Neck",
            fretboard_object_name="Neck",
        )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            headstock=make_headstock(),
            headstock_object_name="NeckBack",
        )


def test_neck_assembly_rejects_an_incompatible_truss_rod_channel() -> None:
    surface = make_neck_surface()
    different_outline = NeckOutline(609.6, 24, 43.0, 56.0, 56.0, 63.0)

    with pytest.raises(FreeCADBackendError):
        FreeCADScriptExporter().render_neck_assembly(
            surface,
            make_fretboard_surface(),
            truss_rod_channel=make_truss_rod_channel(different_outline),
        )
    with pytest.raises(FreeCADBackendError):
        FreeCADScriptExporter().render_neck_assembly(
            surface,
            make_fretboard_surface(),
            truss_rod_channel=make_truss_rod_channel(
                surface.neck_outline,
                depth=17.0,
            ),
        )


def test_neck_assembly_rejects_incompatible_fret_slots() -> None:
    exporter = FreeCADScriptExporter()

    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            fret_layout=make_fret_layout(scale_length=610.0),
        )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            fret_layout=make_fret_layout(fret_count=22),
        )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            fret_layout=make_fret_layout(),
            fret_slot_depth=6.0,
        )


def test_neck_assembly_rejects_incompatible_tuner_holes() -> None:
    exporter = FreeCADScriptExporter()

    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            tuner_layout=make_tuner_layout(),
        )

    different_plan = HeadstockPlan(150.0, 43.0, 30.0, 65.0, 40.0)
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            headstock=make_headstock(),
            tuner_layout=make_tuner_layout(different_plan),
        )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            headstock=make_headstock(),
            tuner_layout=make_tuner_layout(),
            tuner_chamfer_depth=-0.1,
        )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            headstock=make_headstock(14.0),
            tuner_layout=make_tuner_layout(),
            tuner_chamfer_depth=14.0,
        )


def test_neck_assembly_rejects_an_invalid_headstock_join() -> None:
    exporter = FreeCADScriptExporter()

    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            join_headstock_to_neck=True,
        )

    incompatible_headstock = HeadstockSolid(
        HeadstockPlan(150.0, 43.0, 30.0, 65.0, 40.0),
        HeadstockAngleReference(150.0, 8.0),
    )
    with pytest.raises(FreeCADBackendError):
        exporter.render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            headstock=incompatible_headstock,
            join_headstock_to_neck=True,
        )
