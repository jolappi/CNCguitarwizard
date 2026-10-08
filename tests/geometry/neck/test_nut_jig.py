"""Tests for the nut-slot filing jig: a comb standing against the nut."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck.nut_jig import (
    NUT_JIG_CORNER_RELIEF,
    NUT_JIG_EDGE_CLEARANCE,
    NUT_JIG_LEG_DEPTH,
    NUT_JIG_LEG_WIDTH,
    board_surface,
    default_gauges,
    resolved_gauges,
)
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import INSTRUMENT_OVERRIDES

GUITAR = Prototype001Parameters(nut_jig=True)


def _taper(parameters: Prototype001Parameters) -> float:
    """The board's widening per mm along the neck, each side."""
    last = parameters.centre_scale * (1.0 - 2.0 ** (-parameters.fret_count / 12.0))
    return (parameters.final_fret_width - parameters.nut_width) / 2.0 / last


def test_no_jig_unless_asked() -> None:
    assert Prototype001Parameters().nut_slot_jig() is None


def test_a_slot_for_each_string_as_wide_as_its_string() -> None:
    jig = GUITAR.nut_slot_jig()
    assert jig is not None
    # .010-.046, bass first, each 0.05 mm wider than its string, at the
    # strings' 7 mm spacing on the nut.
    assert [slot.gauge for slot in jig.slots] == [
        0.046,
        0.036,
        0.026,
        0.017,
        0.013,
        0.010,
    ]
    assert [slot.centre for slot in jig.slots] == pytest.approx(
        [17.5, 10.5, 3.5, -3.5, -10.5, -17.5]
    )
    for slot in jig.slots:
        assert slot.width == pytest.approx(slot.gauge * 25.4 + 0.05)
        # Down to the frets' height over the radius, up through the top.
        surface = board_surface(430.0, slot.centre)
        assert slot.floor == pytest.approx(surface + 1.2)
        assert slot.top >= 5.0 + surface


def test_it_sits_on_the_radius_between_legs_round_the_board() -> None:
    jig = GUITAR.nut_slot_jig()
    assert jig is not None
    treble, bass = jig.edges
    # The board 42 mm at the nut, widening toward its last fret over the
    # jig's 3 mm.
    assert bass == pytest.approx(21.0 + 3.0 * _taper(GUITAR))
    assert treble == pytest.approx(-bass)
    xs = [point.x for point in jig.body]
    assert max(xs) == pytest.approx(bass + NUT_JIG_EDGE_CLEARANCE + NUT_JIG_LEG_WIDTH)
    assert min(xs) == pytest.approx(-max(xs))
    # The legs reach 3 mm below the board's edges.
    assert min(point.y for point in jig.body) == pytest.approx(
        board_surface(430.0, bass) - NUT_JIG_LEG_DEPTH
    )
    # The underside follows the radius between the corners cut away for
    # the board's edges.
    under = [
        point
        for point in jig.body
        if abs(point.x) < bass - NUT_JIG_CORNER_RELIEF - 1e-9 and point.y < 2.0
    ]
    assert len(under) > 30
    for point in under:
        assert point.y == pytest.approx(board_surface(430.0, point.x))
    # The board's edges, and the crown, are clear of the jig's wood.
    for x in (treble, 0.0, bass):
        assert not point_in_polygon(
            type(jig.body[0])(x, board_surface(430.0, x) - 0.01), jig.body
        )


def test_the_outline_has_its_slots_cut_in() -> None:
    jig = GUITAR.nut_slot_jig()
    assert jig is not None
    outline = jig.outline
    for slot in jig.slots:
        half = slot.width / 2.0
        floor = [
            p
            for p in outline
            if p.y == pytest.approx(slot.floor) and abs(p.x - slot.centre) < 1.0
        ]
        assert sorted(p.x for p in floor) == pytest.approx(
            [slot.centre - half, slot.centre + half]
        )
        # Nothing of the top is left between the slot's walls.
        assert not any(
            abs(p.x - slot.centre) < half - 1e-9 and p.y > slot.floor for p in outline
        )
    assert len(outline) == len(jig.body) + 4 * len(jig.slots) - sum(
        1
        for p in jig.body
        if p.y > 3.0 and any(abs(p.x - s.centre) <= s.width / 2.0 for s in jig.slots)
    )


def test_gauges_in_any_order_inches_or_thousandths() -> None:
    assert resolved_gauges((10, 46, 13, 36, 17, 26), 6) == (
        0.046,
        0.036,
        0.026,
        0.017,
        0.013,
        0.010,
    )
    assert resolved_gauges((0.045, 0.105, 0.065, 0.085), 4)[0] == 0.105
    with pytest.raises(NeckGeometryError, match="one per string"):
        resolved_gauges((10, 13), 6)
    with pytest.raises(NeckGeometryError, match="too thick"):
        resolved_gauges((0.3,), 1)
    with pytest.raises(NeckGeometryError, match="positive"):
        resolved_gauges((0.0,), 1)
    jig = replace(GUITAR, nut_jig_gauges=(9, 11, 16, 24, 32, 42)).nut_slot_jig()
    assert jig is not None
    assert jig.slots[-1].width == pytest.approx(0.009 * 25.4 + 0.05)


def test_usual_sets_for_guitars_and_basses() -> None:
    assert default_gauges(7, 647.7) == (0.059, 0.046, 0.036, 0.026, 0.017, 0.013, 0.010)
    assert default_gauges(8, 685.8)[0] == 0.074
    assert default_gauges(4, 863.6) == (0.105, 0.085, 0.065, 0.045)
    assert default_gauges(5, 863.6) == (0.130, 0.105, 0.085, 0.065, 0.045)
    with pytest.raises(NeckGeometryError, match="nut_jig_gauges"):
        default_gauges(3, 647.7)
    bass = Prototype001Parameters(**INSTRUMENT_OVERRIDES["bass_guitar"], nut_jig=True)
    jig = bass.nut_slot_jig()
    assert jig is not None
    # 10 mm apart on a 38 mm nut, the E string's slot 2.72 mm wide.
    assert [slot.centre for slot in jig.slots] == pytest.approx([15, 5, -5, -15])
    assert jig.slots[0].width == pytest.approx(0.105 * 25.4 + 0.05)


def test_a_leaning_nut_spaces_the_slots_along_its_face() -> None:
    fanned = replace(
        GUITAR, scale_length=647.7, bass_scale_length=686.0, perpendicular_fret=7.0
    )
    jig = fanned.nut_slot_jig()
    assert jig is not None
    # The bass end of the nut sits further back (toward the headstock).
    lean = fanned.fret_skew.at(0.0) * fanned.bass_sign
    assert lean == pytest.approx(-(1.0 - 2.0 ** (-7 / 12)) * 38.3 / 35.0)
    k = math.hypot(1.0, lean)
    assert [slot.centre for slot in jig.slots] == pytest.approx(
        [17.5 * k, 10.5 * k, 3.5 * k, -3.5 * k, -10.5 * k, -17.5 * k]
    )
    # The legs clear the board's edges across the jig's thickness: on the
    # treble side the board reaches further out at the jig's back face.
    treble, bass = jig.edges
    assert bass == pytest.approx(21.0 * k)
    assert treble == pytest.approx(-(21.0 + 3.0 * _taper(fanned)) * k + 3.0 * lean)


def test_the_jig_needs_a_nut_on_the_nut_line_to_file() -> None:
    with pytest.raises(NeckGeometryError, match="locking nut"):
        replace(GUITAR, locking_nut="r2").nut_slot_jig()
    floyd = replace(GUITAR, body_bridge=FloydRoseSpec())
    with pytest.raises(NeckGeometryError, match="locking nut"):
        floyd.nut_slot_jig()
    with pytest.raises(NeckGeometryError, match="zero fret"):
        replace(GUITAR, nut_style="zero_fret").nut_slot_jig()
    # A slotted (Fender) nut stands on the nut line too.
    assert replace(GUITAR, nut_style="slot").nut_slot_jig() is not None


def test_sizes_the_jig_cannot_be_made_with() -> None:
    with pytest.raises(NeckGeometryError, match="nut_jig_height"):
        replace(GUITAR, nut_jig_height=2.0).nut_slot_jig()
    with pytest.raises(NeckGeometryError, match="nut_jig_thickness"):
        replace(GUITAR, nut_jig_thickness=0.0).nut_slot_jig()
    with pytest.raises(NeckGeometryError, match="nut_jig_slot_play"):
        replace(GUITAR, nut_jig_slot_play=-0.1).nut_slot_jig()
    with pytest.raises(NeckGeometryError, match="reaches the fretboard's edge"):
        replace(GUITAR, nut_string_spacing=8.2).nut_slot_jig()


def test_the_built_geometry_carries_the_jig() -> None:
    geometry = GUITAR.build()
    assert geometry.nut_jig is not None
    assert len(geometry.nut_jig.slots) == 6
    assert Prototype001Parameters().build().nut_jig is None


def test_it_stands_against_the_nut_in_the_freecad_model() -> None:
    from cncguitarwizard.backends.freecad import FreeCADScriptExporter

    geometry = GUITAR.build()
    jig = geometry.nut_jig
    assert jig is not None
    # On the nut's face (X 0), on the board's crown (6 mm up), the bass
    # side where the model has it; 3 mm thick toward the bridge.
    crown = jig.placed(type(jig.body[0])(17.5, 1.0))
    assert crown == pytest.approx((0.0, 17.5 * GUITAR.bass_sign, 7.0))
    assert jig.toward_bridge == pytest.approx((1.0, 0.0))
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert '"Part::Feature", "NutSlotJig"' in source
    assert "App.Vector(3.0, 0.0, 0.0)" in source
    # A leaning nut's jig turns with its face.
    fanned = replace(
        GUITAR, scale_length=647.7, bass_scale_length=686.0, perpendicular_fret=7.0
    ).nut_slot_jig()
    assert fanned is not None
    dx, dy = fanned.toward_bridge
    x, y, _ = fanned.placed(type(jig.body[0])(10.0, 0.0))
    assert dx * x + dy * y == pytest.approx(0.0)
    assert math.hypot(x, y) == pytest.approx(10.0)
