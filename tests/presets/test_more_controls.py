"""Tests for the superstrat, single-volume, active bass and Jazz Bass layouts."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.cam.body import plan_body_machining
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.controls import (
    BLADE_SWITCH_SCREW_SPACING,
    BLADE_SWITCH_TOP_WALL,
    JAZZ_PLATE_SCREW_SPACING,
)
from cncguitarwizard.render.svg import render_plan_view_svg
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

GUITAR = Prototype001Parameters()
BASS = Prototype001Parameters.for_instrument("bass_guitar")


def _apart(a, b) -> float:  # type: ignore[no-untyped-def]
    return math.hypot(a.x - b.x, a.y - b.y)


def _pots(body):  # type: ignore[no-untyped-def]
    return [hole for hole in body.holes if hole.name.startswith("Control pot")]


def test_the_superstrat_cavity_holds_the_blade_switch() -> None:
    geometry = replace(GUITAR, body_controls="superstrat").build()
    body = geometry.body
    rear = body.control_cavity
    assert rear is not None and body.switch_cavity is None
    assert len(_pots(body)) == 2
    # The switch in a deeper pocket, a thin top over it.
    (pocket,) = rear.steps
    assert pocket.name == "Control switch pocket"
    assert body.thickness - pocket.depth == pytest.approx(BLADE_SWITCH_TOP_WALL)
    # Its lever's slot through the top, 1 mm into the pocket.
    (slot,) = body.through_cavities
    assert slot.name == "Control switch slot"
    assert slot.depth + pocket.depth == pytest.approx(body.thickness + 1.0)
    assert all(point_in_polygon(p, pocket.outline) for p in slot.outline)
    # Its two screws through the top, 1-5/8 in apart, either side of it.
    screws = [h for h in body.holes if h.name.startswith("Control switch screw")]
    assert len(screws) == 2
    assert _apart(screws[0].center, screws[1].center) == pytest.approx(
        BLADE_SWITCH_SCREW_SPACING
    )
    assert all(rear.depth_at(screw.center) == pocket.depth for screw in screws)
    plan = plan_body_machining(body, MachiningParameters())
    paths = {
        setup.name: [path.name for path in setup.toolpaths] for setup in plan.setups
    }
    assert "Control switch slot" in paths["Body_top"]
    assert "Control switch pocket" in paths["Body_back_controls"]
    assert "Control switch screw 1" in paths["Body_top_small_holes"]
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "control switch slot through cut" in source
    assert "control cavity step cut" in source


def test_the_superstrat_slot_still_opens_under_a_carved_top() -> None:
    body = (
        replace(
            GUITAR,
            body_controls="superstrat",
            body_carved_top=True,
            body_thickness=50.8,
        )
        .build()
        .body
    )
    rear = body.control_cavity
    assert rear is not None
    (pocket,) = rear.steps
    (slot,) = body.through_cavities
    assert slot.depth + pocket.depth == pytest.approx(body.thickness + 1.0)


def test_one_volume_pot_takes_a_selector_only_with_two_pickups() -> None:
    two = replace(GUITAR, body_controls="volume_1").build().body
    assert len(_pots(two)) == 1 and two.switch_cavity is not None
    one = replace(GUITAR, body_controls="volume_1", body_pickups="H").build()
    assert len(_pots(one.body)) == 1 and one.body.switch_cavity is None
    assert [cover.name for cover in one.covers] == ["Control cavity cover"]
    assert len(one.covers[0].holes) == 3


def test_the_active_bass_cavity_has_four_pots_in_a_row() -> None:
    geometry = replace(BASS, body_controls="active_4").build()
    body = geometry.body
    pots = _pots(body)
    assert len(pots) == 4 and body.switch_cavity is None
    gaps = [_apart(a.center, b.center) for a, b in zip(pots, pots[1:])]
    assert gaps == pytest.approx([28.0, 28.0, 28.0])
    rear = body.control_cavity
    assert rear is not None
    assert all(rear.depth_at(pot.center) is not None for pot in pots)
    assert len(geometry.covers[0].holes) == 6


def test_the_jazz_bass_plate_can_carry_the_jack() -> None:
    plate_jack = replace(BASS, body_controls="jazz_bass", body_jack="plate")
    geometry = plate_jack.build()
    body = geometry.body
    assert body.jack_hole is None
    assert body.control_cavity is None and body.switch_cavity is None
    recess, cavity = body.control_top_cavities
    (plate,) = geometry.covers
    names = [hole.name for hole in plate.holes]
    assert names == [
        "Pot 1 shaft hole",
        "Pot 2 shaft hole",
        "Pot 3 shaft hole",
        "Jack hole",
        "Screw 1",
        "Screw 2",
    ]
    holes = {hole.name: hole for hole in plate.holes}
    # Every pot and the jack over the cavity, the screws on the ledge.
    for name in names[:4]:
        assert point_in_polygon(holes[name].center, cavity.outline)
    for name in names[4:]:
        assert not point_in_polygon(holes[name].center, cavity.outline)
    assert _apart(holes["Screw 1"].center, holes["Screw 2"].center) == (
        pytest.approx(JAZZ_PLATE_SCREW_SPACING)
    )
    assert "jack bore" not in FreeCADScriptExporter().render_prototype001(geometry)
    assert render_plan_view_svg(geometry).startswith("<svg")
    layout = body_editor_layout(
        {
            "prototype": {
                "instrument": "bass_guitar",
                "body_controls": "jazz_bass",
                "body_jack": "plate",
            }
        }
    )
    assert layout["jack"] is None and layout["control"] is not None
    # With a side jack the plate has no jack hole and the bore runs in.
    side = replace(BASS, body_controls="jazz_bass").build()
    assert side.body.jack_hole is not None
    assert "Jack hole" not in [hole.name for hole in side.covers[0].holes]


def test_only_the_jazz_bass_plate_takes_the_jack() -> None:
    with pytest.raises(BodyGeometryError, match="Only the Jazz Bass plate"):
        replace(GUITAR, body_controls="tele", body_jack="plate").build()


def test_the_web_form_offers_the_layouts() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert {"superstrat", "volume_1", "active_4", "jazz_bass"} <= set(
        fields["body_controls"]["options"]
    )
    assert fields["body_jack"]["options"] == ["side", "cup", "strat", "plate"]
    assert "Jazz Bass" in fields["body_jack"]["labels"]["plate"]


@pytest.mark.parametrize("template", sorted(YOUR_DESIGN_TEMPLATES))
def test_strat_controls_fit_under_a_guard_on_every_template(template: str) -> None:
    """Chosen from the menu, the guard-mounted controls just work."""
    _, shape = YOUR_DESIGN_TEMPLATES[template]
    instrument = "bass_guitar" if "bass" in template else "electric_guitar"
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument),
        body_shape=shape,
        body_controls="pickguard",
    )
    geometry = parameters.build()
    (guard,) = [cover for cover in geometry.covers if cover.name == "Pickguard"]
    (cavity,) = [
        c for c in geometry.body.control_top_cavities if c.name == "Control cavity"
    ]
    outline = geometry.body.outline.points
    assert all(point_in_polygon(p, guard.outline) for p in cavity.outline)
    assert all(point_in_polygon(p, outline) for p in cavity.outline)
    pots = [hole for hole in guard.holes if hole.name.startswith("Control pot")]
    assert len(pots) == 3
    assert any(slot.name == "Control switch slot" for slot in guard.slots)
