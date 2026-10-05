"""Tests for the parts once left to notes, now modelled or machined where a
three-axis router can: the truss rod's sleeve slot, the locking nut's
screw pilots and a Floyd Rose's trem-claw screw holes."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.dxf import render_plan_dxf
from cncguitarwizard.render.svg import render_plan_view_svg

FLOYD = replace(Prototype001Parameters(), body_bridge=FloydRoseSpec())


def test_the_sleeve_slot_is_routed_and_modelled_under_the_fretboard() -> None:
    geometry = Prototype001Parameters().build()
    bore = geometry.truss_rod_channel.bore
    assert bore is not None and bore.routed
    # Its top would be 3 mm under the glue face, so routed from the top it
    # stays hidden under the board, which reaches the heel end.
    assert bore.axis_depth - bore.diameter / 2.0 > 0.0
    assert bore.floor_depth == pytest.approx(12.0)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "'truss-rod sleeve slot'" in source
    by_hand = replace(Prototype001Parameters(), truss_rod_sleeve_routed=False).build()
    assert '"truss-rod sleeve bore"' in FreeCADScriptExporter().render_prototype001(
        by_hand
    )


@pytest.mark.parametrize(("drill", "depth"), [(3.0, 2.0), (2.5, 8.0)])
def test_the_locking_nut_pilots_are_drilled_or_started(
    drill: float, depth: float
) -> None:
    geometry = FLOYD.build()
    nut = geometry.locking_nut
    assert nut is not None and nut.screw_diameter == 2.5
    flat = replace(NeckMachiningParameters().flat, small_hole_tool_diameter=drill)
    plan = plan_neck_machining(geometry, NeckMachiningParameters(flat=flat))
    assert plan.small_holes is not None
    assert plan.small_holes.name in [setup.name for setup in plan.setups]
    pilots = plan.small_holes.toolpaths
    assert [path.name for path in pilots] == [
        "Locking nut screw 1 pilot",
        "Locking nut screw 2 pilot",
    ]
    # Drilled to size where the drill fits the pilot, else started with
    # it as a guide.
    assert min(move.z for move in pilots[0].moves) == pytest.approx(-depth)
    started = "started" in " ".join(plan.small_holes.notes)
    assert started == (drill > nut.screw_diameter)


def test_a_neck_without_a_locking_nut_has_no_pilot_program() -> None:
    plan = plan_neck_machining(
        Prototype001Parameters().build(), NeckMachiningParameters()
    )
    assert plan.small_holes is None


def test_the_trem_claw_screws_are_modelled_in_the_spring_cavitys_wall() -> None:
    geometry = FLOYD.build()
    body = geometry.body
    holes = body.side_holes
    assert [hole.name for hole in holes] == [
        "Trem claw screw 1 hole",
        "Trem claw screw 2 hole",
    ]
    (spring,) = [r for r in body.rear_cavities if "spring" in r.cavity.name]
    wall = min(p.x for p in spring.cavity.outline)
    for hole, y in zip(holes, (-17.0, 17.0), strict=True):
        # From the nut-ward wall, 30 mm on toward the neck, halfway up the
        # cavity, along the neck.
        assert hole.start.x == pytest.approx(wall)
        assert hole.end.x == pytest.approx(wall - 30.0)
        assert hole.start.y == hole.end.y == pytest.approx(y)
        assert hole.start.z == pytest.approx(spring.cavity.depth / 2.0)
        assert hole.diameter == 3.5
    assert any("trem claw" in note for note in body.bridge_notes)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "'trem claw screw 1 hole cut'" in source
    assert render_plan_view_svg(geometry).count('stroke="#7d3c98"') == 2
    assert "SIDE_HOLES" in render_plan_dxf(geometry)
    # Left-handed, they are still in the wall.
    replace(FLOYD, handedness="left").build()


def test_the_trem_claw_screws_must_fit_and_stay_out_of_other_cavities() -> None:
    with pytest.raises(BodyGeometryError, match="claw_screw_spacing"):
        replace(
            Prototype001Parameters(),
            body_bridge=FloydRoseSpec(claw_screw_spacing=60.0),
        ).build()
    # Up near the top and long enough, they would run into the bridge
    # pickup's route.
    with pytest.raises(BodyGeometryError, match="Trem claw screw 1 hole would break"):
        replace(
            Prototype001Parameters(),
            body_bridge=FloydRoseSpec(claw_screw_height=40.0, claw_screw_depth=80.0),
        ).build()
