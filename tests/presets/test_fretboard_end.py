"""Tests for where the fretboard ends toward the body (fretboard_end)."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import plan_fretboard_machining
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    fretboard_outline_polygon,
)
from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.presets import Prototype001Parameters

FANNED = replace(Prototype001Parameters(), bass_scale_length=660.4)


def _end(parameters: Prototype001Parameters) -> tuple[float, float]:
    """The board's end on its two sides: its outline's furthest x each."""
    outline = fretboard_outline_polygon(parameters.build())
    return (
        max(p.x for p in outline if p.y < 0.0),
        max(p.x for p in outline if p.y > 0.0),
    )


def test_a_fanned_board_covers_the_heel_and_stops_at_the_pocket() -> None:
    geometry = FANNED.build()
    heel_end = geometry.neck_outline.heel_end_position

    # Square at the heel's end on both sides: none of the heel bare in
    # front, none of the board past the neck pocket.
    assert _end(FANNED) == pytest.approx((heel_end, heel_end))
    pocket = next(c for c in geometry.body.top_cavities if c.name == "Neck pocket")
    assert max(p.x for p in pocket.outline) == pytest.approx(heel_end)
    # A fret leaning past it is cut short there (the bass side's last).
    last = geometry.fret_layout.slots[-1]
    assert max(last.start.x, last.end.x) == pytest.approx(heel_end)
    assert min(abs(last.start.y), abs(last.end.y)) < 20.0
    assert all(
        max(s.start.x, s.end.x) <= heel_end + 1e-9 for s in geometry.fret_layout.slots
    )
    # The FreeCAD board is cut back to it too.
    script = FreeCADScriptExporter().render_prototype001(geometry)
    assert "# The board run on to the heel's end: what lies past it cut off." in script
    assert "fretboard_shape.cut(heel_end_trim), 'round heel end on the board'" in script


def test_a_leaning_end_is_kept_as_chosen_and_straight_frets_are_as_before() -> None:
    leaning = replace(FANNED, fretboard_end="fret")
    bass, treble = _end(leaning)
    heel_end = leaning.neck_outline().heel_end_position

    # The old end: past the pocket on the bass side, short of it on the
    # treble.
    assert bass > heel_end + 10.0 and treble < heel_end - 10.0
    straight = Prototype001Parameters()
    assert not straight.board_to_heel_end
    assert replace(straight, fretboard_end="heel").build().fret_layout.slots == (
        straight.build().fret_layout.slots
    )
    assert replace(straight, fret_slant_angle=5.0).board_to_heel_end
    with pytest.raises(FretboardGeometryError, match="Unknown fretboard end"):
        replace(straight, fretboard_end="body").build()


def test_its_slots_are_machined_to_the_boards_end() -> None:
    def last_slot_span(parameters: Prototype001Parameters) -> float:
        geometry = parameters.build()
        plan = plan_fretboard_machining(geometry, FretboardMachiningParameters())
        path = plan.slots.toolpaths[-1]
        ys = [move.y for move in path.moves if not move.rapid]
        return max(ys) - min(ys)

    # Cut short at the board's end (and the overshoot past it), not run on
    # across the whole width past it.
    assert (
        last_slot_span(FANNED)
        < last_slot_span(replace(FANNED, fretboard_end="fret")) - 15.0
    )


def test_a_slot_cut_short_is_machined_along_its_own_line() -> None:
    geometry = FANNED.build()
    plan = plan_fretboard_machining(geometry, FretboardMachiningParameters())
    last = geometry.fret_layout.slots[-1]
    slope = (last.end.x - last.start.x) / (last.end.y - last.start.y)

    # Off the centre once cut short at the board's end: the cutter still
    # runs down the fret's own line.
    path = plan.slots.toolpaths[-1]
    for move in path.moves:
        if move.rapid:
            continue
        x, y = move.x + plan.origin_x, move.y + plan.origin_y
        assert x == pytest.approx(last.start.x + slope * (y - last.start.y), abs=1e-6)
