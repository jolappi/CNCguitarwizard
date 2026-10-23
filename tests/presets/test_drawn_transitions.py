"""Tests for the heel and the headstock's root drawn as two lines: in the
model, the FreeCAD loft, the CAM and the web app's editors."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad.script_exporter import FreeCADScriptExporter
from cncguitarwizard.cam.neck import _BackSurface, _Frame
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import NeckBackSurface
from cncguitarwizard.presets import Prototype001Geometry, Prototype001Parameters


def drawn_heel(**changes: object) -> Prototype001Parameters:
    return replace(Prototype001Parameters(), heel_root_style="drawn", **changes)


def drawn_root(**changes: object) -> Prototype001Parameters:
    """A flat headstock's drawn root (``headstock_angle`` 0) unless changed."""
    return replace(
        Prototype001Parameters(),
        **{"headstock_angle": 0.0, "headstock_root_style": "drawn", **changes},
    )


def back(geometry: Prototype001Geometry) -> _BackSurface:
    """Return the neck's back as its programs cut it, in the model frame."""
    return _BackSurface(geometry, 0.0, 0.0, _Frame(0.0, 0.0, mirror_y=False))


def row_at(surface: NeckBackSurface, x: float) -> tuple:
    return next(row for row in surface.mesh.rows if row[0].x == pytest.approx(x))


def test_both_are_smooth_unless_drawn() -> None:
    plain = Prototype001Parameters().build().neck_surface

    assert plain.heel_drawn is None and plain.root_drawn is None
    heel = drawn_heel().build().neck_surface.heel_drawn
    assert heel is not None and heel.depth == 20.0 and heel.toward_block == 1.0
    root = drawn_root().build().neck_surface.root_drawn
    # A flat headstock's back: level, its face's 4 mm drop and 16 mm below.
    assert root is not None and root.toward_block == -1.0
    assert root.depth_at(-30.0) == root.depth_at(10.0) == 20.0
    # An angled one's back falls away behind the nut with its face.
    angled = drawn_root(headstock_angle=8.0).build()
    tilt = angled.neck_surface.root_drawn
    assert tilt is not None and tilt.slope == pytest.approx(-math.tan(math.radians(8)))
    assert tilt.depth_at(-30.0) == pytest.approx(
        angled.headstock.thickness / math.cos(math.radians(8))
        - angled.headstock.face_z(-30.0)
    )
    # With the volute on its own lines shape the back there instead.
    with_volute = drawn_root(headstock_pointed_volute=True).build()
    assert with_volute.neck_surface.root_drawn is None
    with pytest.raises(NeckGeometryError, match="Unknown heel root"):
        replace(Prototype001Parameters(), heel_root_style="scooped").build()


def test_the_heel_falls_from_the_neck_line_to_its_block() -> None:
    surface = (
        drawn_heel(
            heel_root_flat_points=((12.0, 0.0), (0.0, 30.8)),
            heel_root_neck_points=((60.0, 0.0), (45.0, 30.8)),
        )
        .build()
        .neck_surface
    )
    block = surface.neck_outline.last_fret_position - surface.heel_flat_start_offset

    # At the block's start, its square section 20 mm deep; down the middle
    # the block's flat reaches 12 mm toward the nut, rounding the heel.
    assert {point.z for point in row_at(surface, block)[1:-1]} == {-20.0}
    middle = [
        min(point.z for point in row)
        for row in surface.mesh.rows
        if block - 70.0 <= row[0].x <= block
    ]
    assert middle == sorted(middle, reverse=True)
    ahead = surface.mesh.rows[
        max(
            index
            for index, row in enumerate(surface.mesh.rows)
            if row[0].x < block - 60.0
        )
    ]
    # Ahead of the neck line, the neck's own profile, as shallow as the
    # neck there.
    assert ahead == surface.plain_profile_row(ahead[0].x)
    assert ahead[len(ahead) // 2].z > -14.0


def test_the_heels_lines_stay_between_the_12th_fret_and_its_block() -> None:
    # A point past either, the setting it is in named.
    with pytest.raises(NeckGeometryError, match="heel_root_flat_points must lie"):
        drawn_heel(heel_root_flat_points=((-5.0, 0.0), (0.0, 30.0))).build()
    with pytest.raises(NeckGeometryError, match="heel_root_neck_points must lie"):
        drawn_heel(heel_root_neck_points=((150.0, 0.0), (45.0, 30.0))).build()
    # Points all ahead of the block, the curve through them swinging a
    # hair past it: kept along the block, which stays flat.
    swinging = drawn_heel(
        heel_root_flat_points=((0.0, 0.0), (12.0, 10.0), (0.0, 20.0), (0.0, 30.8))
    ).build()
    surface = swinging.neck_surface
    block = surface.neck_outline.last_fret_position - surface.heel_flat_start_offset
    assert surface.heel_drawn is not None
    assert max(point.x for point in surface.heel_drawn.flat) == pytest.approx(block)


def test_the_roots_lines_stay_between_the_first_fret_and_the_tip() -> None:
    with pytest.raises(NeckGeometryError, match="headstock_root_neck_points must"):
        drawn_root(headstock_root_neck_points=((-40.0, 0.0), (-14.0, 23.1))).build()
    with pytest.raises(NeckGeometryError, match="headstock_root_flat_points must"):
        drawn_root(headstock_root_flat_points=((145.0, 0.0), (20.0, 23.1))).build()


def test_a_flat_headstocks_back_runs_into_the_neck_between_its_lines() -> None:
    geometry = drawn_root(
        headstock_root_flat_points=((12.0, 0.0), (8.0, 12.0), (15.0, 23.1)),
        headstock_root_neck_points=((-12.0, 0.0), (-12.0, 23.1)),
    ).build()
    surface = geometry.neck_surface
    cut = back(geometry)

    # Past the flat line the headstock's flat back, 20 mm deep; past the
    # neck line (12 mm onto the neck) the neck's own profile.
    assert cut.model_z(-16.0, 0.0) == pytest.approx(-20.0)
    assert cut.model_z(-16.0, 18.0) == pytest.approx(-20.0, abs=0.01)
    neck = surface.plain_profile_row(14.0)
    assert cut.model_z(14.0, 0.0) == pytest.approx(neck[len(neck) // 2].z, abs=0.01)
    # Between, down evenly from the one to the other, never past either.
    centre = [cut.model_z(x, 0.0) for x in range(-12, 13, 2)]
    assert centre == sorted(centre)
    assert all(-20.0 <= z <= -11.0 for z in centre)
    smooth = back(replace(Prototype001Parameters(), headstock_angle=0.0).build())
    # The smooth root drops straight to the flat back behind the nut.
    assert smooth.model_z(-2.0, 18.0) == pytest.approx(-20.0)
    assert cut.model_z(-2.0, 18.0) > -19.0


def test_an_angled_headstocks_back_too_falling_away_behind_the_nut() -> None:
    geometry = drawn_root(headstock_angle=8.0).build()
    cut = back(geometry)
    headstock = geometry.headstock
    plane = headstock.thickness / math.cos(math.radians(8.0))

    # Past the flat line (20 mm behind the nut), the headstock's back plane.
    for x in (-24.0, -40.0):
        assert cut.model_z(x, 0.0) == pytest.approx(headstock.face_z(x) - plane)
    # From it the back rises evenly to the neck's, 14 mm onto the neck.
    centre = [cut.model_z(x, 0.0) for x in range(-20, 15, 2)]
    assert centre == sorted(centre)
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface, headstock, geometry.joint_fillet_radius
    )
    for row in (row for row in rows if -20.0 < row[0].x <= 16.0):
        assert all(a.y <= b.y for a, b in zip(row, row[1:], strict=False))
        # Never above the top edges, toward the fretboard or the face.
        assert max(p.z for p in row[1:-1]) <= min(row[0].z, row[-1].z)


def test_freecad_lofts_the_drawn_root_between_the_neck_and_headstock() -> None:
    geometry = drawn_root().build()
    smooth = replace(Prototype001Parameters(), headstock_angle=0.0).build()

    def rows(of: Prototype001Geometry) -> tuple:
        return FreeCADScriptExporter.neck_loft_rows(
            of.neck_surface, of.headstock, of.joint_fillet_radius
        )

    drawn_rows = [row for row in rows(geometry) if -21.0 < row[0].x <= 20.0]
    # Each row across the back in order (a square side straight down): no
    # fold for the loft to trip on.
    for row in drawn_rows:
        assert all(a.y <= b.y for a, b in zip(row, row[1:], strict=False))
    # Its top edges stay as the smooth root's: only the back is drawn.
    edges = {round(row[0].x, 3): (row[0], row[-1]) for row in rows(smooth)}
    for row in drawn_rows:
        if round(row[0].x, 3) in edges:
            for drawn, plain in zip((row[0], row[-1]), edges[round(row[0].x, 3)]):
                assert (drawn.y, drawn.z) == pytest.approx((plain.y, plain.z))
    # The blend reaches past the neck line before the neck's own rows.
    centre = len(drawn_rows[0]) // 2
    at_nut = min(drawn_rows, key=lambda row: abs(row[0].x))
    assert -20.0 < at_nut[centre].z < -11.0
    assert FreeCADScriptExporter().render_prototype001(geometry) != (
        FreeCADScriptExporter().render_prototype001(smooth)
    )


def test_the_editors_draw_them_and_say_where_they_lie() -> None:
    from cncguitarwizard.webapp import headstock_editor_layout, heel_editor_layout

    heel = heel_editor_layout({"prototype": {"heel_root_style": "drawn"}})
    assert heel["heel"]["lines"]["flat"]["field"] == "heel_root_flat_points"
    assert heel["heel"]["lines"]["flat"]["drawn"] is False
    assert heel["heel"]["origin"] == pytest.approx(heel["block"])
    assert heel["heel"]["style"] == "drawn" and heel["problem"] is None
    assert heel["twelfth"] < heel["block"] < heel["heel_end"]
    # Where the editor lets its points go, a millimetre inside the 12th
    # fret and the block, and the lines' order, neck to block, so the two
    # never cross.
    low, high = heel["heel"]["limits"]
    assert low == pytest.approx(heel["twelfth"] + 1.0, abs=0.01)
    assert high == pytest.approx(heel["block"], abs=0.01)
    assert heel["heel"]["order"] == ["neck", "flat"] and heel["heel"]["toward"] == 1
    # A line set past the block (a saved design) is drawn as it is even
    # so, the reason said, to be mended.
    past = {"heel_root_style": "drawn", "heel_root_flat_points": [[-5, 0], [0, 30]]}
    mended = heel_editor_layout({"prototype": past})
    assert "heel_root_flat_points must lie" in mended["problem"]
    assert mended["heel"]["lines"]["flat"]["points"][0] == [-5, 0]
    # Smooth, its lines are where drawing them starts, drawing one makes
    # it drawn (its style setting named for that).
    smooth = heel_editor_layout({"prototype": {}})["heel"]
    assert smooth["style"] == "smooth" and smooth["style_field"] == "heel_root_style"
    # The root's with the volute off, on any headstock, the volute's on.
    root = headstock_editor_layout({"prototype": {}})["root"]
    assert root["style"] == "smooth" and root["toward"] == -1
    assert root["limits"][0] < -100.0 < 30.0 < root["limits"][1]
    assert root["lines"]["neck"]["field"] == "headstock_root_neck_points"
    assert root["lines"]["flat"]["points"][0] == [20.0, 0.0]
    volute = headstock_editor_layout({"prototype": {"headstock_pointed_volute": True}})
    assert volute["root"] is None and volute["volute"] is not None
    broken = heel_editor_layout(
        {"prototype": {"heel_root_style": "drawn", "heel_root_flat_points": [[0, 0]]}}
    )
    assert "error" in broken
