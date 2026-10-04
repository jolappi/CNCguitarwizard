"""Tests for the zero fret: a fret on the nut line, the nut a guide behind it."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    plan_fretboard_machining,
)
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_plan_view_svg
from cncguitarwizard.webapp import headstock_editor_layout, parameter_schema

ZERO = replace(Prototype001Parameters(), nut_style="zero_fret")


def test_the_nut_stands_behind_a_fret_on_the_nut_line() -> None:
    geometry = ZERO.build()
    nut = geometry.locking_nut
    assert nut is not None and nut.zero_fret and not nut.is_locking
    gap = ZERO.zero_fret_gap
    assert nut.front == pytest.approx(-gap)
    # The slot behind the gap, the board running on past it.
    xs = [p.x for p in nut.slot_outline()]
    assert max(xs) == pytest.approx(-gap)
    assert min(xs) == pytest.approx(-gap - ZERO.nut_thickness)
    assert nut.seat_length == pytest.approx(
        gap + ZERO.nut_thickness + ZERO.nut_slot_lip + ZERO.nut_slot_taper
    )
    # A slot on the nut line, besides fret 1 on.
    zero = geometry.fret_layout.zero_fret_slot
    assert zero is not None
    assert zero.start.x == pytest.approx(0.0) and zero.end.x == pytest.approx(0.0)
    assert len(geometry.fret_layout.slots) == ZERO.fret_count
    # Without it, no zero fret.
    assert Prototype001Parameters().build().fret_layout.zero_fret_slot is None
    slotted = replace(ZERO, nut_style="slot").build().locking_nut
    assert slotted is not None and not slotted.zero_fret and slotted.front == 0.0


def test_the_zero_fret_is_cut_drawn_and_noted() -> None:
    geometry = ZERO.build()
    plan = plan_fretboard_machining(geometry, FretboardMachiningParameters())
    names = [path.name for path in plan.slots.toolpaths]
    assert names[0] == "Zero fret slot" and names[1] == "Fret 1 slot"
    assert len(names) == ZERO.fret_count + 1
    assert any("zero fret" in note for note in plan.slots.notes)
    assert any("behind the zero fret" in note for note in plan.inlays.notes)
    neck = plan_neck_machining(geometry, NeckMachiningParameters())
    assert any("Zero fret on the nut line" in note for note in neck.top.notes)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    rows = source.split("FRET_SURFACE_ROWS = ")[1].split("\n")[0]
    plain = FreeCADScriptExporter().render_prototype001(
        replace(ZERO, nut_style="slot").build()
    )
    plain_rows = plain.split("FRET_SURFACE_ROWS = ")[1].split("\n")[0]
    assert rows.count("[[") == plain_rows.count("[[") + 1
    svg = render_plan_view_svg(geometry)
    assert svg.count('stroke="#d9c9a8"') == ZERO.fret_count + 1


def test_the_headstock_editor_shows_the_nut() -> None:
    for style in ("shelf", "slot", "zero_fret"):
        nut = headstock_editor_layout({"prototype": {"nut_style": style}})["nut"]
        xs = [x for x, _ in nut["nut"]]
        if style == "shelf":
            assert nut["board"] is None and max(xs) == 0.0
        elif style == "slot":
            assert nut["board"] is not None and max(xs) == 0.0
            assert nut["zero_fret"] is None
        else:
            assert max(xs) == pytest.approx(-ZERO.zero_fret_gap)
            assert nut["zero_fret"] == [[0.0, -21.0], [0.0, 21.0]]
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["nut_style"]["options"] == ["shelf", "slot", "zero_fret"]
    assert fields["zero_fret_gap"]["default"] == 3.0
