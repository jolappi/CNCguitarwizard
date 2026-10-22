"""Tests for the pointed volute: in the model, the FreeCAD loft and the CAM."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad.script_exporter import FreeCADScriptExporter
from cncguitarwizard.cam import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.cam.neck import _BackSurface, _Frame
from cncguitarwizard.geometry.neck import Volute
from cncguitarwizard.geometry.primitives import Point3D
from cncguitarwizard.presets import Prototype001Geometry, Prototype001Parameters


def with_volute(**changes: float | str) -> Prototype001Parameters:
    return replace(Prototype001Parameters(), headstock_pointed_volute=True, **changes)


def with_arrow(**changes: float) -> Prototype001Parameters:
    return with_volute(headstock_volute_style="arrow", **changes)


def back(geometry: Prototype001Geometry) -> _BackSurface:
    """Return the neck's back as its programs cut it, in the model frame."""
    return _BackSurface(geometry, 0.0, 0.0, _Frame(0.0, 0.0, mirror_y=False))


def test_the_guitar_carries_it_behind_the_nut_the_neck_as_wide() -> None:
    assert Prototype001Parameters().build().volute is None

    assert with_arrow().build().volute == Volute(4.0, 30.0, 21.0)
    assert with_arrow(headstock_pointed_volute_length=40.0).build().volute == (
        Volute(4.0, 40.0, 21.0)
    )
    # Drawn, by default: its three lines.
    assert with_volute().build().volute.drawn


def test_a_headless_neck_has_none() -> None:
    headless = Prototype001Parameters.for_instrument("headless_guitar")

    assert replace(headless, headstock_pointed_volute=True).build().volute is None


def test_the_back_programs_cut_it_under_the_headstocks_back() -> None:
    plain = back(Prototype001Parameters().build())
    volute = back(with_arrow().build())

    # 4 mm more wood down the middle at its fullest, 9 mm behind the nut;
    # the neck past its point and the headstock past its end as they were.
    assert volute.model_z(-9.0, 0.0) == pytest.approx(plain.model_z(-9.0, 0.0) - 4.0)
    for x in (20.0, 10.5, -31.0, -60.0):
        assert volute.model_z(x, 0.0) == pytest.approx(plain.model_z(x, 0.0))


def test_its_sides_come_down_evenly_to_the_fretboard() -> None:
    # A regression: the drawn crest reaches the neck's edges, where its
    # whole height stood out from the rounded back as fins.
    plain = back(Prototype001Parameters().build())
    geometry = with_volute().build()
    volute = back(geometry)

    # On the neck's rounded back, 5 mm onto it, near the edge: the share
    # of its wood the back is as deep there as down the middle.
    share = plain.model_z(5.0, 20.0) / plain.model_z(5.0, 0.0)
    assert 0.0 < share < 0.5
    assert plain.model_z(5.0, 20.0) - volute.model_z(5.0, 20.0) == pytest.approx(
        geometry.volute.extra(5.0, 20.0) * share
    )


def test_the_blank_is_thick_enough_for_it_on_a_flat_headstock() -> None:
    plain = plan_neck_machining(
        replace(Prototype001Parameters(), headstock_angle=0.0).build(),
        NeckMachiningParameters(),
    )
    volute = plan_neck_machining(
        with_arrow(headstock_angle=0.0).build(), NeckMachiningParameters()
    )

    # The flat headstock's back is level with the neck's; the volute
    # reaches 4 mm below it.
    assert volute.stock_thickness > plain.stock_thickness


def test_freecad_lofts_it_under_the_back_never_the_face() -> None:
    row = (
        Point3D(-9.0, -21.0, -1.0),
        Point3D(-9.0, -10.0, -16.0),
        Point3D(-9.0, 0.0, -16.0),
        Point3D(-9.0, 10.0, -16.0),
        Point3D(-9.0, 21.0, -1.0),
    )

    lofted = FreeCADScriptExporter._with_volute(row, Volute(4.0, 30.0, 21.0))

    # The top edges stay; the back's points go down, most in the middle.
    assert lofted[0] == row[0] and lofted[-1] == row[-1]
    assert lofted[2].z == pytest.approx(-20.0)
    assert -20.0 < lofted[1].z < -16.0 and lofted[1].z == lofted[3].z

    # A rounded back's sides, shallower, get less of it: in proportion.
    rounded = (row[0], Point3D(-9.0, -18.0, -8.5), *row[2:])
    side = FreeCADScriptExporter._with_volute(rounded, Volute(4.0, 30.0, 21.0))[1]
    extra = Volute(4.0, 30.0, 21.0).extra(-9.0, -18.0)
    assert side.z == pytest.approx(-8.5 - extra * 7.5 / 15.0)
    exporter = FreeCADScriptExporter()
    assert exporter.render_prototype001(
        with_volute().build()
    ) != exporter.render_prototype001(Prototype001Parameters().build())


def test_a_drawn_volute_from_the_headstock_editor() -> None:
    from cncguitarwizard.webapp import headstock_editor_layout

    crest = [[-5.0, 0.0], [0.0, 21.0, "corner"]]
    arrow = with_arrow().build()
    drawn = replace(
        with_volute(),
        headstock_volute_style="drawn",
        headstock_volute_points=tuple(tuple(p) for p in crest),
    ).build()

    assert arrow.volute is not None and not arrow.volute.drawn
    assert drawn.volute is not None and drawn.volute.drawn
    # The arrow is shown, not drawn; a drawn one's three lines, each from
    # where drawing starts until drawn, into its own setting.
    shown = headstock_editor_layout(
        {
            "prototype": {
                "headstock_pointed_volute": True,
                "headstock_volute_style": "arrow",
            }
        }
    )
    assert shown["volute"]["style"] == "arrow" and shown["volute"]["outline"]
    drawing = {"headstock_pointed_volute": True, "headstock_volute_style": "drawn"}
    lines = headstock_editor_layout(
        {"prototype": {**drawing, "headstock_volute_points": crest}}
    )["volute"]["lines"]
    assert set(lines) == {"crest", "headstock", "neck"}
    assert lines["crest"]["drawn"] is True and lines["crest"]["points"] == crest
    assert lines["headstock"]["drawn"] is False
    assert lines["headstock"]["field"] == "headstock_volute_headstock_points"
    assert lines["neck"]["points"][0] == [-22.5, 0.0]
    assert headstock_editor_layout({"prototype": {}})["volute"] is None
