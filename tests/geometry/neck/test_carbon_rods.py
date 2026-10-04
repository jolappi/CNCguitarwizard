"""Tests for the carbon fibre reinforcement beside the truss rod."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import CarbonRods
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import (
    CARBON_ROD_FLOOR,
    CARBON_ROD_GAP,
    CARBON_ROD_WALL,
    _back_z,
)
from cncguitarwizard.render.svg import render_plan_view_svg

RODS = replace(Prototype001Parameters(), neck_carbon_rods=True)


def test_two_bars_lie_beside_the_truss_rod() -> None:
    geometry = RODS.build()
    rods = geometry.carbon_rods
    assert rods is not None
    assert (rods.width, rods.depth, rods.start) == (3.2, 6.35, 20.0)
    # To where the heel flattens, clear of the neck screws.
    surface = geometry.neck_surface
    outline = geometry.neck_outline
    assert rods.end == pytest.approx(
        outline.last_fret_position - surface.heel_flat_start_offset
    )
    # Beside the truss rod's widest part along them, CARBON_ROD_GAP apart.
    widest = max(
        half
        for front, back, half in geometry.truss_rod_channel.keep_clear()
        if front < rods.end and back > rods.start
    )
    assert rods.offset - rods.channel_width / 2.0 == pytest.approx(
        widest + CARBON_ROD_GAP
    )
    plus, minus = rods.channels()
    assert min(p.y for p in plus) == pytest.approx(-max(p.y for p in minus))
    # Enough wood under them all along.
    outer = rods.offset + rods.channel_width / 2.0
    for x in range(int(rods.start), int(rods.end), 10):
        floor = -_back_z(surface.mesh.rows, float(x), outer) - rods.depth
        assert floor >= CARBON_ROD_FLOOR
    assert Prototype001Parameters().build().carbon_rods is None


def test_bars_that_do_not_fit_are_refused() -> None:
    with pytest.raises(NeckGeometryError, match="wood under them"):
        replace(RODS, neck_carbon_rod_size="3.2x9.5").build()
    with pytest.raises(NeckGeometryError, match="wood under them"):
        replace(RODS, neck_carbon_rod_size="custom", neck_carbon_rod_depth=9.0).build()
    with pytest.raises(NeckGeometryError, match="truss rod's route"):
        replace(RODS, neck_carbon_rod_offset=5.0).build()
    with pytest.raises(NeckGeometryError, match="neck's side"):
        replace(RODS, neck_carbon_rod_offset=19.0).build()
    with pytest.raises(NeckGeometryError, match="apart"):
        CarbonRods(20.0, 400.0, 1.0, 3.2, 6.35)
    assert CARBON_ROD_WALL == 2.0


def test_the_channels_are_cut_and_drawn() -> None:
    geometry = RODS.build()
    rods = geometry.carbon_rods
    assert rods is not None
    plan = plan_neck_machining(geometry, NeckMachiningParameters())
    names = [setup.name for setup in plan.setups]
    assert names[:3] == ["Neck_index_pins", "Neck_top", "Neck_carbon_rods"]
    assert len(plan.preview_outlines) == len(plan.setups)
    setup = plan.carbon_rods
    assert setup is not None and setup.tool is not None
    assert setup.tool.tool_diameter == 3.0
    assert len(setup.toolpaths) == 2
    assert all(
        path.deepest_z() == pytest.approx(-rods.depth) for path in setup.toolpaths
    )
    assert any("glue them in with epoxy" in note for note in setup.notes)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "carbon rod channels" in source and '"CarbonRods"' in source
    assert "carbon_rods_feature" in source
    svg = render_plan_view_svg(geometry)
    assert svg.count('stroke-dasharray="3,2"') >= 2


def test_the_bars_come_in_stock_sizes() -> None:
    from cncguitarwizard.webapp import parameter_schema

    for size, (width, depth) in {
        "3.2x6.35": (3.2, 6.35),
        "4x4": (4.0, 4.0),
    }.items():
        rods = replace(RODS, neck_carbon_rod_size=size).build().carbon_rods
        assert rods is not None and (rods.width, rods.depth) == (width, depth)
    custom = replace(
        RODS,
        neck_carbon_rod_size="custom",
        neck_carbon_rod_width=5.0,
        neck_carbon_rod_depth=5.0,
    ).build()
    assert custom.carbon_rods is not None
    assert (custom.carbon_rods.width, custom.carbon_rods.depth) == (5.0, 5.0)
    # A 4 x 4 bar is cut in a 4.1 mm channel with the 3 mm end mill.
    four = replace(RODS, neck_carbon_rod_size="4x4").build()
    plan = plan_neck_machining(four, NeckMachiningParameters())
    assert plan.carbon_rods is not None
    assert any("4 x 4 mm carbon fibre bars" in note for note in plan.carbon_rods.notes)
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["neck_carbon_rod_size"]["options"] == [
        "3.2x6.35",
        "4x4",
        "3.2x9.5",
        "custom",
    ]
    assert not fields["neck_carbon_rod_size"]["advanced"]
