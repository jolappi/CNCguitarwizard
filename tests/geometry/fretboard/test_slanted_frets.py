"""Tests for slanted frets."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import FretboardMachiningParameters, plan_fretboard_machining
from cncguitarwizard.cam.fretboard import fretboard_outline_polygon
from cncguitarwizard.geometry.exceptions import (
    FretboardGeometryError,
    NeckGeometryError,
)
from cncguitarwizard.geometry.fretboard import FretboardSurface, FretSkew
from cncguitarwizard.presets import Prototype001Parameters


@pytest.fixture(scope="module")
def slanted():  # type: ignore[no-untyped-def]
    parameters = replace(
        Prototype001Parameters(), fret_slant_angle=5.0, inlay_style="block"
    )
    return parameters, parameters.build()


def test_every_fret_and_both_board_ends_share_the_slant(slanted) -> None:  # type: ignore[no-untyped-def]
    parameters, geometry = slanted
    slope = math.tan(math.radians(5.0))

    for slot in geometry.fret_layout.slots:
        dx, dy = slot.end.x - slot.start.x, slot.end.y - slot.start.y
        assert abs(dx / dy) == pytest.approx(slope)
    rows = geometry.fretboard_surface.mesh.rows
    for row in (rows[0], rows[-1]):
        assert (row[-1].x - row[0].x) / (row[-1].y - row[0].y) == pytest.approx(slope)
    # The treble side (+Y on the right-handed default) moves toward the bridge.
    first = geometry.fret_layout.slots[0]
    treble, bass = sorted((first.start, first.end), key=lambda p: -p.y)
    assert treble.x > bass.x
    assert parameters.fret_slant == pytest.approx(slope)
    lefty = replace(parameters, headstock_bass_side="+y")
    assert lefty.fret_slant == pytest.approx(-slope)


def test_fret_spacing_stays_exact_on_the_centreline(slanted) -> None:  # type: ignore[no-untyped-def]
    _, geometry = slanted
    plain = Prototype001Parameters().build()

    for slot, straight in zip(
        geometry.fret_layout.slots, plain.fret_layout.slots, strict=True
    ):
        assert (slot.start.x + slot.end.x) / 2.0 == pytest.approx(straight.start.x)
    assert geometry.fretboard_surface.station_positions == (
        plain.fretboard_surface.station_positions
    )
    # The bridge, pickups and neck are untouched.
    assert geometry.body == plain.body
    assert geometry.neck_outline == plain.neck_outline


def test_block_inlays_follow_the_frets_and_dots_keep_their_shape(slanted) -> None:  # type: ignore[no-untyped-def]
    _, geometry = slanted
    slope = math.tan(math.radians(5.0))
    block = geometry.inlay_layout.markers[0].outline
    left = min(block, key=lambda p: (p.y, p.x))
    right = min(block, key=lambda p: (-p.y, p.x))
    assert right.x - left.x == pytest.approx(slope * (right.y - left.y), abs=0.5)

    dots = replace(
        Prototype001Parameters(), fret_slant_angle=5.0, inlay_style="dot"
    ).build()
    straight = replace(Prototype001Parameters(), inlay_style="dot").build()
    for moved, plain in zip(
        dots.inlay_layout.markers, straight.inlay_layout.markers, strict=True
    ):
        width = max(p.x for p in moved.outline) - min(p.x for p in moved.outline)
        plain_width = max(p.x for p in plain.outline) - min(p.x for p in plain.outline)
        assert width == pytest.approx(plain_width)


def test_the_fretboard_program_cuts_slanted_slots_and_ends(slanted) -> None:  # type: ignore[no-untyped-def]
    _, geometry = slanted
    plan = plan_fretboard_machining(geometry, FretboardMachiningParameters())
    slope = math.tan(math.radians(5.0))

    cuts = [move for move in plan.slots.toolpaths[11].moves if not move.rapid]
    xs = [move.x for move in cuts]
    ys = [move.y for move in cuts]
    assert (max(xs) - min(xs)) / (max(ys) - min(ys)) == pytest.approx(slope, rel=1e-3)
    outline = fretboard_outline_polygon(geometry)
    assert min(p.x for p in outline) == pytest.approx(-slope * 21.0)


def test_a_slanted_nut_gets_a_longer_nut_shelf() -> None:
    parameters = replace(Prototype001Parameters(), fret_slant_angle=8.0)
    geometry = parameters.build()
    reach = math.tan(math.radians(8.0)) * 21.0

    assert parameters.nut_shelf_reach() == pytest.approx(reach)
    assert geometry.neck_surface.nut_shelf_length == pytest.approx(5.0 + reach)
    with pytest.raises(NeckGeometryError, match="within 10 degrees"):
        replace(Prototype001Parameters(), fret_slant_angle=12.0).build()
    with pytest.raises(FretboardGeometryError, match="within 35 degrees"):
        FretboardSurface(600.0, 20, 42.0, 56.0, 300.0, 6.0, skew=FretSkew(1.0))
