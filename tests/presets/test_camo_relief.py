"""Tests for the camo relief: its shapes cut to their levels, modelled and
drawn."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.cam.body import plan_body_machining
from cncguitarwizard.geometry.body import body_part
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

CAMO = replace(
    Prototype001Parameters(), body_engraving=True, body_engraving_pattern="camo"
)


def test_the_relief_is_cleared_level_by_level() -> None:
    geometry = CAMO.build()
    engraving = geometry.body.engraving
    assert engraving is not None and engraving.lines == ()
    shapes = engraving.pockets
    assert len(shapes) > 12
    plan = plan_body_machining(geometry.body, MachiningParameters())
    names = [setup.name for setup in plan.setups]
    # No V-bit program, a flat end mill's after Body_top.
    assert "Body_top_engraving" not in names
    assert names.index("Body_top_relief") == names.index("Body_top") + 1
    relief = plan.top_relief
    assert relief is not None and relief.tool is not None
    assert relief.tool.tool_diameter == 3.0
    assert "0.5, 1, 1.5, 2 mm deep" in relief.description
    assert len(relief.toolpaths) == len(shapes)
    for path, shape in zip(relief.toolpaths, shapes, strict=True):
        cutting = [move.z for move in path.moves if not move.rapid]
        assert min(cutting) == pytest.approx(-(shape.face_drop + shape.depth))
        if shape.within is not None:
            # Cut on from its parent's floor.
            parent = shapes[shape.within]
            assert max(z for z in cutting if z < 0.0) <= -parent.depth + 1e-9
    # Another end mill: the program is made for it.
    smaller = plan_body_machining(
        geometry.body, MachiningParameters(relief_tool_diameter=2.0)
    )
    assert smaller.top_relief is not None
    assert "2 mm flat end mill" in smaller.top_relief.description


def test_the_relief_is_cut_in_the_model_and_drawn_in_the_editor() -> None:
    geometry = CAMO.build()
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "RELIEF_LEVELS = [(0.5, " in source
    assert 'f"relief {relief_depth:g} mm cut"' in source
    assert '_engraving"' not in source  # no drawn lines
    layout = body_editor_layout(
        {"prototype": {"body_engraving": True, "body_engraving_pattern": "camo"}}
    )
    assert layout["engraving"] == []
    assert len(layout["relief"]) == len(geometry.body.engraving.pockets)  # type: ignore[union-attr]
    assert {shape["depth"] for shape in layout["relief"]} == {0.5, 1.0, 1.5, 2.0}
    # Other patterns have no relief.
    lines = body_editor_layout({"prototype": {"body_engraving": True}})
    assert lines["relief"] == [] and lines["engraving"]


def test_a_neck_through_part_keeps_the_shapes_that_reach_it() -> None:
    geometry = replace(CAMO, neck_joint="neck_through").build()
    through = geometry.neck_through
    assert through is not None
    whole = geometry.body.engraving
    assert whole is not None
    counted = 0
    for part in through.parts:
        piece = body_part(geometry.body, part).engraving
        if piece is None:
            continue
        counted += len(piece.pockets)
        for shape in piece.pockets:
            assert shape in whole.pockets or any(
                shape.outline == other.outline for other in whole.pockets
            )
            if shape.within is not None:
                assert piece.pockets[shape.within].depth < shape.depth
    # Every shape is in a part; one across a glue line in both.
    assert counted >= len(whole.pockets)


def test_the_relief_tool_is_offered() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }
    assert fields["relief_tool_diameter"]["default"] == 3.0
    assert "camo" in fields["relief_tool_diameter"]["help"]
