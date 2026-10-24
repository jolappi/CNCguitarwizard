"""Tests for a heel wider than the neck's taper: the neck and its fretboard
flaring out to it together."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam.fretboard import fretboard_outline_polygon
from cncguitarwizard.presets import Prototype001Parameters


def test_a_wider_heel_flares_the_neck_and_its_board_together() -> None:
    # Regression: heel_width 58 on a 56 mm final fret widened only the
    # short stub past the last fret, a step out at the last fret.
    geometry = replace(Prototype001Parameters(), heel_width=58.0).build()
    outline = geometry.neck_outline
    surface = geometry.fretboard_surface
    flare = outline.heel_flare
    assert flare is not None
    heel_end = outline.heel_end_position

    # Along the heel's mounting block, out to the heel's width at its end.
    assert flare.length == Prototype001Parameters().heel_mounting_length
    assert 2.0 * outline.half_width_at(heel_end) == pytest.approx(58.0)
    # The board flush with the neck all the way.
    for k in range(11):
        x = flare.start - 20.0 + (heel_end - flare.start + 20.0) * k / 10
        assert surface.half_width_at(x) == pytest.approx(outline.half_width_at(x))
    # Every slot reaches the board's edges.
    for slot in geometry.fret_layout.slots:
        middle = (slot.start.x + slot.end.x) / 2.0
        length = math.dist((slot.start.x, slot.start.y), (slot.end.x, slot.end.y))
        assert length == pytest.approx(2.0 * surface.half_width_at(middle))
    # The board is cut along it, and its pocket keeps its clearance round it.
    board = fretboard_outline_polygon(geometry)
    assert max(abs(p.y) for p in board) == pytest.approx(29.0, abs=0.01)
    pocket = geometry.body.neck_pocket
    assert pocket is not None
    clearance = Prototype001Parameters().body_neck_pocket_clearance
    for point in pocket.outline:
        if flare.start <= point.x < heel_end - 1.0:
            assert abs(point.y) - outline.half_width_at(point.x) == pytest.approx(
                clearance
            )


def test_a_heel_as_wide_as_the_final_fret_does_not_flare() -> None:
    geometry = Prototype001Parameters().build()

    assert geometry.neck_outline.heel_flare is None
    assert geometry.fretboard_surface.heel_flare is None
    assert len(geometry.fretboard_surface.outline_rows()) == 2
