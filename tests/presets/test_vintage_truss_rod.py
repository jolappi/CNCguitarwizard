"""Tests for the vintage Fender truss rod: laid in from the neck's back
under a walnut strip and a teardrop plug (``truss_rod_install`` "back")."""

import ast
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Geometry, Prototype001Parameters
from cncguitarwizard.presets.prototype001 import (
    VINTAGE_ROD_WALL,
    VINTAGE_STRIP_MIN,
    _back_z,
)
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.render.dxf import render_plan_dxf
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg

TELECASTER = replace(
    Prototype001Parameters.for_instrument("electric_guitar"),
    **STYLES["telecaster"].prototype_values("electric_guitar"),
)
VINTAGE = replace(TELECASTER, truss_rod_install="back")


@cache
def vintage() -> Prototype001Geometry:
    """Return the Telecaster style's neck with a vintage rod, built."""
    return VINTAGE.build()


def test_a_rod_from_the_top_is_the_default_and_has_no_vintage_rod() -> None:
    assert Prototype001Parameters().truss_rod_install == "top"
    assert TELECASTER.vintage_truss_rod(TELECASTER.neck_outline()) is None


def test_the_vintage_rod_runs_from_the_headstock_to_the_heel_end() -> None:
    geometry = vintage()
    rod = geometry.vintage_truss_rod
    outline = geometry.neck_outline

    assert rod is not None
    # Anchored where the top starts down onto the headstock's face,
    # adjusted at the heel's end face.
    assert rod.start == pytest.approx(-VINTAGE.nut_seat_length())
    assert rod.end == pytest.approx(outline.last_fret_position + outline.heel_length)
    assert rod.width == VINTAGE.truss_rod_width
    # The channel's plan, for what must keep clear of it: nothing is cut
    # from the top, and no stock rod's length is asked for.
    channel = geometry.truss_rod_channel
    assert channel.routed_from == "back"
    assert channel.start_position == pytest.approx(rod.start)
    assert channel.end_position == pytest.approx(rod.end)
    fit = VINTAGE.truss_rod_fit(outline)
    assert fit.recommended is None
    assert fit.rod_length == pytest.approx(rod.end - rod.start)
    assert geometry.body.truss_rod_access is None


def test_the_rod_keeps_wood_over_its_anchor_and_walnut_under_the_back() -> None:
    geometry = vintage()
    rod = geometry.vintage_truss_rod
    assert rod is not None

    assert -geometry.headstock.top_z(rod.start, 0.0) + VINTAGE_ROD_WALL <= (
        rod.ceiling_depth(rod.start)
    )
    rows = geometry.neck_surface.mesh.rows
    for step in range(101):
        x = rod.start + (rod.end - rod.start) * step / 100
        walnut = -_back_z(rows, x, rod.width / 2.0) - rod.strip_depth(x)
        assert walnut >= VINTAGE_STRIP_MIN - 1e-9


def test_a_neck_too_thin_for_the_walnut_is_refused() -> None:
    thin = replace(VINTAGE, first_fret_thickness=14.0, twelfth_fret_thickness=16.0)
    with pytest.raises(NeckGeometryError, match="walnut over"):
        thin.build()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"truss_rod_adjustment": "headstock"}, "truss_rod_adjustment to heel"),
        ({"truss_rod_spoke_wheel": "yes"}, "truss_rod_spoke_wheel"),
        ({"truss_rod_profile": "low_profile"}, "truss_rod_profile"),
        ({"headstock_angle": 8.0}, "headstock_angle to 0"),
        ({"neck_joint": "neck_through"}, "run through the body"),
        ({"truss_rod_install": "side"}, '"top" or "back"'),
    ],
)
def test_a_vintage_rod_it_cannot_be_is_refused(
    changes: dict[str, object], message: str
) -> None:
    parameters = replace(VINTAGE, **changes)
    with pytest.raises(NeckGeometryError, match=message):
        parameters.vintage_truss_rod(parameters.neck_outline())


def test_the_back_routes_the_channel_before_the_back_is_carved() -> None:
    geometry = vintage()
    rod = geometry.vintage_truss_rod
    assert rod is not None
    plan = plan_neck_machining(geometry, NeckMachiningParameters())

    names = [setup.name for setup in plan.setups]
    assert names.index("Neck_back_truss_rod") == names.index("Neck_back_rough") - 1
    assert len(plan.preview_outlines) == len(plan.setups)
    # Nothing of the rod is cut from the top.
    assert not any("Truss" in path.name for path in plan.top.toolpaths)
    assert "truss-rod channel" not in plan.top.description
    setup = plan.back_truss_rod
    assert setup is not None
    teardrop, channel = setup.toolpaths
    thickness = plan.stock_thickness
    # The teardrop down to the plug's floor; the channel down to the rod's
    # side nearest the fretboard, deepest at its ends.
    assert teardrop.deepest_z() == pytest.approx(-(thickness - rod.plug_depth))
    assert channel.deepest_z() == pytest.approx(
        -(thickness - rod.ceiling_depth(rod.end)), abs=0.01
    )
    middle = (rod.start + rod.end) / 2.0 - plan.origin_x
    floor_middle = min(move.z for move in channel.moves if abs(move.x - middle) <= 1.0)
    assert floor_middle == pytest.approx(
        -(thickness - rod.ceiling_depth(middle + plan.origin_x)), abs=0.01
    )
    # It runs out through the heel's end; the walnut is glued in before
    # the back's programs carve it.
    assert max(move.x for move in channel.moves) > rod.end - plan.origin_x
    assert any("walnut strip" in note for note in setup.notes)
    assert any("walnut" in note for note in plan.back_rough.notes)


def test_freecad_cuts_the_channel_and_adds_the_walnut(tmp_path: Path) -> None:
    source = FreeCADScriptExporter().render_prototype001(
        vintage(), step_path=tmp_path / "neck.step"
    )

    ast.parse(source)
    assert '"TrussRodStrip"' in source and '"TrussRodPlug"' in source
    # In the STEP model with the rest.
    assert "truss_rod_strip_feature, truss_rod_plug_feature" in source
    # Cut with a little fuzz where a plain boolean fails quietly, and
    # refused unless the walnut is there and the neck lost more than it.
    assert "for vintage_fuzz in (0.0, 0.001, 0.01):" in source
    assert "removed > strip.Volume + plug.Volume" in source
    # No channel boxed out of the top.
    assert "truss_rod_shape = Part.makeBox(" not in source
    default = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build()
    )
    assert "truss_rod_shape = Part.makeBox(" in default
    assert "TrussRodStrip" not in default


def test_the_plan_and_its_dxf_show_the_walnut() -> None:
    geometry = vintage()

    assert "Walnut strip (back)" in render_plan_view_svg(geometry)
    assert "TRUSS_ROD_WALNUT" in render_plan_dxf(geometry)
    assert "TRUSS_ROD_WALNUT" not in render_plan_dxf(Prototype001Parameters().build())
