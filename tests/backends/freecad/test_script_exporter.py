"""Tests for dependency-free FreeCAD script generation."""

import ast
from dataclasses import replace
from pathlib import Path
from typing import Callable

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.backends.freecad.exceptions import FreeCADBackendError
from cncguitarwizard.geometry.body import (
    BodyOutline,
    BodySolid,
    BridgeMounting,
    DrilledHole,
    JackHole,
    RearCavity,
    RectangularCavity,
)
from cncguitarwizard.geometry.fretboard import (
    Fretboard,
    FretboardSurface,
    FretLayout,
    InlayLayout,
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
from cncguitarwizard.presets import Prototype001Parameters


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


def make_body() -> BodySolid:
    """Return a low-effort Prototype001-sized body assembly for tests."""
    outline = BodyOutline(609.6, 407.2, 28.0)
    return BodySolid(
        outline=outline,
        thickness=44.0,
        neck_pocket=RectangularCavity(
            "Neck pocket", 434.2, 0.0, 54.0, 56.0, 20.0, corner_radius=2.0
        ),
        bridge_pickup=RectangularCavity(
            "Bridge pickup route", 570.0, 0.0, 38.1, 88.9, 22.0, corner_radius=6.0
        ),
        neck_pickup=RectangularCavity(
            "Neck pickup route", 500.0, 0.0, 38.1, 88.9, 22.0, corner_radius=6.0
        ),
        bridge_mounting=BridgeMounting(609.6),
        control_cavity=RearCavity(
            RectangularCavity(
                "Control cavity", 610.0, 90.0, 70.0, 55.0, 30.0, corner_radius=8.0
            ),
            RectangularCavity(
                "Control cavity cover recess",
                610.0,
                90.0,
                80.0,
                65.0,
                2.0,
                corner_radius=8.0,
            ),
        ),
        jack_hole=JackHole(700.0, 140.0, 160.0, diameter=12.5, depth=30.0),
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


def test_complete_prototype_can_be_rendered_with_one_export_call(
    tmp_path: Path,
) -> None:
    step_path = tmp_path / "Prototype001.step"
    source = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build(),
        step_path=step_path,
    )

    ast.parse(source)
    assert "neck_shape.cut(truss_rod_shape)" in source
    # The nut-end U trim reshapes a boundary that only exists as a genuine
    # edge of neck_shape's own material when there is no headstock-root
    # transition. Prototype001's default config joins the headstock via
    # that transition, so the trim is skipped rather than cutting through
    # the now-continuous loft; see test_headstock_can_be_omitted_for_neck_end_inspection
    # for the U trim's own coverage on a build where it still applies.
    assert "NUT_END_U_TRIM_RADIUS = " not in source
    assert '"nut-end U trim"' not in source
    assert "fretboard_shape.cut(slot_shape)" in source
    # The whole headstock — tip through the join — is now stations inside
    # neck_shape's own single loft (see render_neck_assembly and
    # _headstock_transition_sections), not a separate solid built and
    # fused here, so tuner holes cut straight into neck_shape and there is
    # no "headstock root trim" boolean step or fuse of two pieces.
    assert "neck_shape.cut(cutter)" in source
    assert '"headstock root trim"' not in source
    assert "HEADSTOCK_TIP_SECTION_POINTS = " not in source
    assert "headstock_tip_shape" not in source
    assert "HEADSTOCK_ROOT_SECTION_POINTS = " not in source
    assert (
        "headstock_root_shape = make_loft(HEADSTOCK_ROOT_SECTION_POINTS)"
        not in source
    )
    assert "def preserves_base_shape(candidate, shapes):" in source
    assert "expected_volume = max(shape.Volume for shape in shapes)" in source
    assert "def fuse_or_compound(shapes, operation):" in source
    assert "[neck_shape]" in source
    assert (
        "Part.export([neck_feature, fretboard_feature, body_feature], "
        f'"{step_path}")' in source
    )
    assert "joint_fillet_radius = 3.0" in source
    assert "HEADSTOCK_OUTER_D_PROFILE_GUIDES = " not in source
    assert '"HeadstockOuterDProfileGuides"' not in source
    assert "outer_d_profile_guide_feature.ViewObject" not in source
    assert "HEEL_BLOCK" not in source
    assert '"heel-block fusion"' not in source
    assert "heel_nose_face.extrude(" not in source
    assert '"heel-transition fillet"' in source
    assert "def safe_fillet(" in source
    assert "base transition retained" in source
    assert '"heel side-joint fillet"' not in source


def test_complete_prototype_uses_the_simple_curved_headstock_join() -> None:
    geometry = Prototype001Parameters().build()
    source = FreeCADScriptExporter().render_prototype001(geometry)

    assert geometry.neck_surface.headstock_root_start_position == -15.0
    assert "VOLUTE_SECTION_POINTS = " not in source
    assert geometry.neck_surface.nut_root_side_extension == 15.0
    assert '"headstock root trim"' not in source
    assert '"headstock-root edge fillet"' not in source
    assert "[neck_shape]" in source


def test_optional_outer_d_profile_guides_do_not_change_the_nut_or_step_export(
    tmp_path: Path,
) -> None:
    geometry = replace(
        Prototype001Parameters(),
        headstock_outer_d_profile_guide_extension=12.0,
    ).build()
    source = FreeCADScriptExporter().render_prototype001(
        geometry,
        step_path=tmp_path / "Prototype001.step",
    )

    assert geometry.neck_surface.nut_shelf_length == 5.0
    assert "[neck_shape]" in source
    assert "HEADSTOCK_OUTER_D_PROFILE_GUIDES = " in source
    assert "Part.makeCompound(\n    outer_d_profile_guide_edges\n)" in source
    assert "Part.export([neck_feature, fretboard_feature, body_feature]" in source


def test_headstock_can_be_omitted_for_neck_end_inspection() -> None:
    source = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build(),
        hide_headstock=True,
    )

    assert "headstock_feature = document.addObject" not in source
    assert "headstock_feature.ViewObject" not in source
    assert "HEADSTOCK_BOUNDARY = " not in source
    assert "HEADSTOCK_OUTER_D_PROFILE_GUIDES = " not in source
    assert "NUT_END_U_TRIM_RADIUS = " in source


def test_nut_end_u_trim_replaces_only_the_straight_neck_end_boundary() -> None:
    geometry = Prototype001Parameters().build()
    source = FreeCADScriptExporter().render_prototype001(
        geometry,
        hide_headstock=True,
    )

    assert geometry.neck_surface.nut_shelf_length == 5.0
    assert geometry.nut_end_u_trim_depth == 12.0
    assert geometry.nut_end_u_side_fillet_radius == 2.0
    assert "NUT_END_U_TRIM_DEPTH = 12.0" in source
    assert "NUT_END_U_TRIM_END_X = -15.0" in source
    assert "NUT_END_U_TRIM_CENTER_X = -27.375" in source
    assert "NUT_END_U_TRIM_RADIUS = 24.375" in source
    assert "nut_end_u_trim_shape = Part.makeCylinder(" in source
    assert "neck_shape.cut(nut_end_u_trim_shape).removeSplitter()" in source
    assert "NUT_END_U_SIDE_FILLET_RADIUS = 2.0" in source
    assert "nut_end_u_side_edges = nut_corner_edges(" in source
    assert "NUT_END_U_TRIM_END_X" in source
    assert '"nut-end U cylinder-side fillet"' in source
    assert "nut_u_side_rim_edges" not in source
    assert "neck_shape = make_loft(NECK_SECTION_POINTS)" in source
    assert (
        source.index("neck_shape = make_loft(NECK_SECTION_POINTS)")
        < source.index("NUT_END_U_TRIM_RADIUS = ")
        < source.index("neck_shape.cut(truss_rod_shape)")
    )


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
    first_section = assignment.value.elts[0]
    assert isinstance(first_section, ast.List)
    assert len(first_section.elts) == surface.profile_sample_count


def test_neck_sections_do_not_repeat_existing_top_edge_points() -> None:
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

    assert isinstance(assignment.value, ast.List)
    for section in assignment.value.elts:
        assert isinstance(section, ast.List)
        coordinates = [ast.literal_eval(point) for point in section.elts]
        assert all(
            first != second
            for first, second in zip(
                coordinates,
                coordinates[1:],
                strict=False,
            )
        )


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
    assert "heel_face = Part.Face(Part.makePolygon(heel_bottom))" not in source
    assert "heel_shape = heel_face.extrude(" not in source
    assert '"heel-block fusion"' not in source


def test_flat_heel_rows_keep_the_same_loft_profile_structure() -> None:
    surface = NeckBackSurface(
        NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 4.0),
        11.0,
        13.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        profile_sample_count=9,
        segments_per_region=2,
    )
    source = FreeCADScriptExporter().render_neck_back(surface)
    module = ast.parse(source)
    section_points = next(
        node.value
        for node in module.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "SECTION_POINTS"
    )

    assert isinstance(section_points, ast.List)
    assert all(
        isinstance(row, ast.List)
        and len(row.elts) == surface.profile_sample_count
        for row in section_points.elts
    )


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
    assert "neck_shape.cut(truss_rod_shape)" in source
    assert '"truss-rod cut"' in source
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
    assert "fret_slot_surface_overcut = 0.2" in source
    assert "fret_slot_side_overcut = 1.0" in source
    assert "for fret_index, surface_row in enumerate(" in source
    assert "for _, y, z in reversed(extended_row)" in source
    assert "slot_face = Part.Face(Part.makePolygon(profile))" in source
    assert "slot_shape = slot_face.extrude(" in source
    assert "fretboard_shape.cut(slot_shape)" in source
    assert 'f"fret-slot cut {fret_index}"' in source


def test_neck_assembly_omits_fret_slot_cuts_by_default() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
    )

    assert "FRET_SURFACE_ROWS" not in source
    assert "fretboard_shape.cut" not in source


def test_neck_assembly_can_cut_barbed_wire_inlay_markers() -> None:
    fretboard_surface = make_fretboard_surface()
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        fretboard_surface,
        inlay_layout=InlayLayout(fretboard_surface, depth=2.0),
    )

    assert "INLAY_MARKER_OUTLINES = " in source
    assert "inlay_depth = 2.0" in source
    assert "inlay_surface_z = 6.0" in source
    assert "for inlay_index, outline in enumerate(" in source
    assert "marker_face = Part.Face(Part.makePolygon(profile))" in source
    assert "marker_shape = marker_face.extrude(" in source
    assert "fretboard_shape.cut(marker_shape)" in source
    assert 'f"inlay-marker cut {inlay_index}"' in source
    assert source.index("marker_face") < source.index(
        "fretboard_feature.Shape = fretboard_shape"
    )


def test_neck_assembly_omits_inlay_cuts_by_default() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
    )

    assert "INLAY_MARKER_OUTLINES" not in source


def test_neck_assembly_rejects_an_inlay_layout_from_a_different_surface() -> (
    None
):
    with pytest.raises(FreeCADBackendError):
        FreeCADScriptExporter().render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            inlay_layout=InlayLayout(make_fretboard_surface(), depth=2.0),
        )


def test_neck_assembly_can_cut_a_solid_body_with_its_cavities() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=make_body(),
    )

    assert "BODY_OUTLINE_POINTS = " in source
    assert "body_thickness = 44.0" in source
    assert (
        "def cavity_cut(shape, outline_points, depth, label, from_back=False):"
        in source
    )
    assert "body_shape = cavity_cut(body_shape, " in source
    assert "'neck pocket cut'" in source
    assert "'control cavity cut', from_back=True)" in source
    assert "'control cavity cover recess cut', from_back=True)" in source
    assert "'switch cavity cut'" not in source
    assert "pivot_hole = Part.makeCylinder(" in source
    assert "jack_bore = Part.makeCylinder(" in source
    assert "body_shape.cut(jack_bore)" in source
    assert 'document.addObject(\n    "Part::Feature", "Body"\n)' in source
    assert "body_feature.Shape = body_shape" in source
    assert source.index("body_shape = Part.Face(") < source.index(
        "body_feature.Shape = body_shape"
    )


def test_neck_assembly_omits_the_control_cavity_cut_when_absent() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=replace(make_body(), control_cavity=None),
    )

    assert "'control cavity cut'" not in source
    assert "BODY_OUTLINE_POINTS = " in source


def test_neck_assembly_cuts_a_rear_switch_cavity_with_its_cover() -> None:
    switch = RearCavity(
        RectangularCavity("Switch cavity", 680.0, 20.0, 30.0, 40.0, 30.0),
        RectangularCavity(
            "Switch cavity cover recess", 680.0, 20.0, 40.0, 50.0, 2.0
        ),
    )
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=replace(make_body(), switch_cavity=switch),
    )

    assert "'switch cavity cut', from_back=True)" in source
    assert "'switch cavity cover recess cut', from_back=True)" in source
    assert "'battery cavity cut'" not in source


def test_neck_assembly_cuts_a_rear_battery_cavity_with_its_cover() -> None:
    battery = RearCavity(
        RectangularCavity("Battery cavity", 680.0, 20.0, 55.0, 30.0, 10.0),
        RectangularCavity(
            "Battery cavity cover recess", 680.0, 20.0, 65.0, 40.0, 2.0
        ),
    )
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=replace(make_body(), battery_cavity=battery),
    )

    assert "'battery cavity cut', from_back=True)" in source
    assert "'battery cavity cover recess cut', from_back=True)" in source


def test_neck_assembly_omits_pivot_holes_for_a_flat_mount_bridge() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=replace(
            make_body(),
            bridge_mounting=BridgeMounting(609.6, pivot_stud_spacing=None),
        ),
    )

    assert "pivot_hole = Part.makeCylinder(" not in source
    assert "'sustain-block cavity cut'" in source


def test_neck_assembly_drills_body_holes_from_the_top_face() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=replace(
            make_body(),
            holes=(DrilledHole("Pot 1 shaft hole", 610.0, 90.0, 10.0, 44.0),),
        ),
    )

    assert "drilled_hole = Part.makeCylinder(" in source
    assert "    5.0,\n    44.0 + 2.0 * body_overcut,\n" in source
    assert "App.Vector(610.0, 90.0, body_overcut)" in source
    assert "'pot 1 shaft hole cut'" in source


def test_neck_assembly_omits_the_sustain_block_cut_for_a_fixed_bridge() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=replace(
            make_body(),
            bridge_mounting=BridgeMounting(609.6, has_sustain_block=False),
        ),
    )

    assert "'sustain-block cavity cut'" not in source
    assert "'bridge pickup route cut'" in source


def test_neck_assembly_omits_body_by_default() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
    )

    assert "BODY_OUTLINE_POINTS" not in source
    assert "body_feature" not in source


def test_neck_assembly_rejects_a_body_object_name_collision() -> None:
    with pytest.raises(FreeCADBackendError):
        FreeCADScriptExporter().render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            body=make_body(),
            body_object_name="NeckBack",
        )


def test_neck_assembly_includes_body_feature_in_step_export(
    tmp_path: Path,
) -> None:
    step_path = tmp_path / "Prototype001.step"
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        body=make_body(),
        step_path=step_path,
    )

    assert (
        "Part.export([neck_feature, fretboard_feature, body_feature], "
        f'"{step_path}")' in source
    )


def test_neck_assembly_applies_r8_fillet_to_the_two_nut_corner_edges() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        nut_corner_radius=8.0,
    )

    assert "def nut_corner_edges(" in source
    assert "nut_corner_radius = 8.0" in source
    assert "fretboard_nut_edges = nut_corner_edges(" in source
    assert '"fretboard nut-corner fillet"' in source


def test_neck_assembly_rejects_a_nut_corner_radius_wider_than_the_nut() -> None:
    with pytest.raises(FreeCADBackendError):
        FreeCADScriptExporter().render_neck_assembly(
            make_neck_surface(),
            make_fretboard_surface(),
            nut_corner_radius=22.0,
        )


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
        joint_fillet_radius=3.0,
        join_headstock_to_neck=True,
        step_path=step_path,
    )

    assert "HEADSTOCK_ROOT_SECTION_POINTS = " not in source
    assert (
        "headstock_root_shape = make_loft(HEADSTOCK_ROOT_SECTION_POINTS)"
        not in source
    )
    assert "def preserves_base_shape(candidate, shapes):" in source
    assert "def fuse_or_compound(shapes, operation):" in source
    assert "[neck_shape, headstock_shape]" in source
    assert '"headstock-to-neck fusion"' in source
    assert "headstock_root_edges = nut_corner_edges(" in source
    assert '"headstock-root edge fillet"' in source
    assert source.count("neck_feature.Shape = neck_shape") == 2
    assert "headstock_feature = document.addObject" not in source
    assert (
        f'Part.export([neck_feature, fretboard_feature], "{step_path}")'
        in source
    )


def test_explicit_headstock_root_swell_adds_an_optional_root_loft() -> None:
    source = FreeCADScriptExporter().render_neck_assembly(
        make_neck_surface(),
        make_fretboard_surface(),
        headstock=make_headstock(),
        join_headstock_to_neck=True,
        headstock_root_swell=1.5,
    )

    assert "HEADSTOCK_ROOT_SECTION_POINTS = " in source
    assert "headstock_root_shape = make_loft(HEADSTOCK_ROOT_SECTION_POINTS)" in source
    assert "[neck_shape, headstock_shape, headstock_root_shape]" in source


def test_headstock_root_continues_as_a_tapered_d_neck_volute() -> None:
    """The volute must use longitudinal and lateral curves into the D neck."""
    neck_surface = make_neck_surface()

    sections = FreeCADScriptExporter._headstock_root_sections(
        neck_surface,
        root_swell=1.5,
    )

    first_neck_section = sections[0]
    final_neck_section = sections[-1]
    profile_count = neck_surface.profile_sample_count
    center_index = profile_count // 2
    first_section_width = (
        first_neck_section[profile_count - 1].y - first_neck_section[0].y
    )
    final_section_width = (
        final_neck_section[profile_count - 1].y - final_neck_section[0].y
    )

    assert first_section_width == pytest.approx(neck_surface._width_at(2.5))
    assert final_section_width == pytest.approx(neck_surface._width_at(20.0))
    assert first_neck_section[-(center_index + 1)].z < first_neck_section[-1].z
    assert final_neck_section[-(center_index + 1)].z < final_neck_section[-1].z
    assert first_neck_section[0].z > first_neck_section[center_index].z
    # The centre is deepest, while both full-width D-profile edges are
    # already seated on the neck. This produces the visible secondary curves.
    assert (
        first_neck_section[-(center_index + 1)].z
        < first_neck_section[-center_index].z
    )
    assert first_neck_section[-1].z == pytest.approx(
        first_neck_section[0].z - 0.02
    )
    assert first_neck_section[-profile_count].z == pytest.approx(
        first_neck_section[profile_count - 1].z - 0.02
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
    assert "headstock_shape.cut(cutter)" in source
    assert '"tuner-hole cut"' in source
    assert "tuner_chamfer_depth = 0.2" in source
    assert "chamfer = Part.makeCone(" in source
    assert "diameter / 2.0 + tuner_chamfer_depth" in source
    assert "headstock_shape.cut(chamfer)" in source
    assert '"tuner chamfer cut"' in source


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
