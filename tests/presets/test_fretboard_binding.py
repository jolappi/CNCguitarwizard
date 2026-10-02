"""Tests for the fretboard's binding along its long edges."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    plan_fretboard_machining,
)
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters


def _board_width(geometry, row: int) -> float:  # type: ignore[no-untyped-def]
    points = geometry.fretboard_surface.mesh.rows[row]
    return abs(points[-1].y - points[0].y)


def test_a_bound_board_is_cut_narrower_by_its_binding_each_side() -> None:
    plain = Prototype001Parameters().build()
    bound = replace(Prototype001Parameters(), fretboard_binding_width=1.5).build()

    assert _board_width(bound, 0) == pytest.approx(_board_width(plain, 0) - 3.0)
    assert _board_width(bound, -1) == pytest.approx(_board_width(plain, -1) - 3.0)
    # The slots run to the narrowed board's edges, at the same frets.
    for a, b in zip(plain.fret_layout.slots, bound.fret_layout.slots, strict=True):
        assert b.start.x == pytest.approx(a.start.x)
        assert abs(b.start.y - b.end.y) == pytest.approx(abs(a.start.y - a.end.y) - 3.0)
    # The neck under it keeps the nominal widths: board + binding = neck.
    assert bound.neck_outline.nut_width == plain.neck_outline.nut_width
    assert bound.fretboard_binding_width == 1.5


def test_the_programs_say_to_bind_the_board() -> None:
    bound = replace(Prototype001Parameters(), fretboard_binding_width=1.5).build()
    plan = plan_fretboard_machining(bound, FretboardMachiningParameters())
    notes = {setup.name: " ".join(setup.notes) for setup in plan.setups}

    assert "1.5 mm narrower each side" in notes["Fretboard_outline"]
    assert "nip each fret's tang" in notes["Fretboard_slots"]
    plain = plan_fretboard_machining(
        Prototype001Parameters().build(), FretboardMachiningParameters()
    )
    assert all("binding" not in " ".join(s.notes) for s in plain.setups)


def test_the_freecad_model_gets_the_binding_strips() -> None:
    bound = replace(Prototype001Parameters(), fretboard_binding_width=1.5).build()

    script = FreeCADScriptExporter().render_prototype001(bound)
    assert "fretboard_binding_feature" in script
    assert "FretboardBinding" in script
    plain = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build()
    )
    assert "fretboard_binding_feature" not in plain


def test_a_binding_out_of_range_is_refused() -> None:
    with pytest.raises(NeckGeometryError, match="fretboard_binding_width"):
        replace(Prototype001Parameters(), fretboard_binding_width=4.0).build()
    with pytest.raises(NeckGeometryError, match="fretboard_binding_width"):
        replace(Prototype001Parameters(), fretboard_binding_width=-1.0).build()
