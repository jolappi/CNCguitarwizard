"""Tests for the Fender (Telecaster) style nut in a slot and the Telecaster neck."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    fretboard_outline_polygon,
    plan_fretboard_machining,
)
from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import NECK_TEMPLATES, TELECASTER_NECK
from cncguitarwizard.webapp import parameter_schema


@pytest.fixture(scope="module")
def slotted():  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), nut_style="slot").build()


def test_the_board_runs_on_under_a_slotted_nut(slotted) -> None:  # type: ignore[no-untyped-def]
    nut = slotted.locking_nut
    assert nut is not None and not nut.is_locking and nut.on_fretboard
    # 3 mm below the 6 mm board's crown, 3.5 mm thick, no screws; the
    # board runs on 3 mm at full height behind it and 3 mm sloping down.
    assert nut.shelf_height == pytest.approx(3.0)
    assert nut.board_height == pytest.approx(6.0)
    assert nut.seat_length == pytest.approx(3.5 + 3.0 + 3.0)
    assert nut.screw_centres() == ()
    assert min(p.x for p in nut.slot_outline()) == pytest.approx(-3.5)
    assert min(p.x for p in fretboard_outline_polygon(slotted)) == pytest.approx(-9.5)


def test_a_slotted_nuts_board_may_end_at_its_back_face() -> None:
    nut = replace(
        Prototype001Parameters(), nut_style="slot", nut_slot_lip=0.0, nut_slot_taper=0.0
    ).locking_nut_placed()
    assert nut is not None and nut.seat_length == pytest.approx(3.5)
    with pytest.raises(NeckGeometryError, match="nut_slot_lip"):
        replace(
            Prototype001Parameters(), nut_style="slot", nut_slot_lip=-1.0
        ).locking_nut_placed()


def test_a_slot_must_leave_board_under_the_nut() -> None:
    parameters = replace(Prototype001Parameters(), nut_style="slot", nut_slot_depth=5.5)
    with pytest.raises(NeckGeometryError, match="nut_slot_depth"):
        parameters.build()


def test_a_locking_nut_takes_the_slotted_nuts_place() -> None:
    parameters = replace(
        Prototype001Parameters(), nut_style="slot", body_bridge=FloydRoseSpec()
    )
    nut = parameters.locking_nut_placed()
    assert nut is not None and nut.is_locking


def test_the_fretboard_cam_mills_the_slot_and_the_neck_cam_says_how_to_fit_it(  # type: ignore[no-untyped-def]
    slotted,
) -> None:
    parameters = FretboardMachiningParameters()
    plan = plan_fretboard_machining(slotted, parameters)
    # The slot, closed behind by the lip, with the small inlay end mill.
    slot = plan.inlays.toolpaths[-1]
    assert slot.name == "Nut slot"
    assert slot.deepest_z() == pytest.approx(-(parameters.blank_thickness - 3.0))
    tool = parameters.inlay.tool_radius
    xs = [move.x + plan.origin_x for move in slot.moves]
    assert max(xs) == pytest.approx(-tool, abs=1e-6)
    assert min(xs) == pytest.approx(-3.5 + tool, abs=1e-6)
    # The slope behind the lip: terraces down to the glue face, first.
    *terraces, outline = plan.outline.toolpaths
    assert len(terraces) == 12 and outline.name.startswith("Fretboard outline")
    assert terraces[-1].deepest_z() == pytest.approx(-parameters.blank_thickness)
    assert any("12 terraces" in note for note in plan.outline.notes)

    notes = " ".join(plan_neck_machining(slotted, NeckMachiningParameters()).top.notes)
    assert "Fender style nut, 3.5 mm thick" in notes
    assert "board runs on 3 mm, then slopes to the neck over 3 mm" in notes
    assert "filler" not in notes


def test_the_freecad_script_runs_the_board_on_without_screws(slotted) -> None:  # type: ignore[no-untyped-def]
    source = FreeCADScriptExporter().render_prototype001(slotted)

    assert "board_run_on = Part.Face(" in source
    assert "board_slope = Part.Face(" in source
    assert "locking_nut_screw" not in source


def test_a_headstock_adjusted_rod_is_reached_fender_style() -> None:
    fender = replace(
        Prototype001Parameters(),
        **{
            **TELECASTER_NECK,
            "truss_rod_adjustment": "headstock",
            "truss_rod_spoke_wheel": "yes",
        },
    ).build()
    trough = fender.truss_rod_channel.adjuster_boundary
    # A spoke wheel in a short open trough behind the board, no cover.
    assert max(p.x for p in trough) == pytest.approx(-9.5)
    assert min(p.x for p in trough) == pytest.approx(-19.5)
    assert all(cover.name != "Truss rod cover" for cover in fender.covers)

    gibson = replace(Prototype001Parameters(), truss_rod_adjustment="headstock")
    assert any(cover.name == "Truss rod cover" for cover in gibson.build().covers)


@pytest.mark.parametrize("adjustment", ["heel", "headstock"])
def test_the_telecaster_neck_builds(adjustment: str) -> None:
    parameters = replace(
        Prototype001Parameters(),
        **{**TELECASTER_NECK, "truss_rod_adjustment": adjustment},
    )
    plan, tuners = parameters.headstock_design()
    assert plan.is_drawn and plan.length == pytest.approx(204.0)
    assert len(tuners.holes) == 6
    geometry = parameters.build()
    assert geometry.locking_nut is not None and not geometry.locking_nut.is_locking
    assert geometry.truss_rod_channel.adjustment_side == (
        "heel" if adjustment == "heel" else "nut"
    )


def test_the_web_form_offers_the_nut_style_and_the_telecaster_neck() -> None:
    schema = parameter_schema()
    fields = {
        field["name"]: field
        for group in schema["prototype"]
        for field in group["fields"]
    }

    style = fields["nut_style"]
    assert style["type"] == "choice" and not style["advanced"]
    assert style["options"] == ["shelf", "slot", "zero_fret"]
    assert style["default"] == "shelf"
    template = schema["neck_templates"]["telecaster"]
    assert template["label"] == NECK_TEMPLATES["telecaster"][0]
    assert template["values"]["nut_style"] == "slot"
    assert template["values"]["headstock_bass_edge"][0] == [12.0, 26.0]
    # Every value the template sets is a field of the form.
    assert set(template["values"]) <= set(fields)
