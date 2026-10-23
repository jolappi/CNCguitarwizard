"""Tests for a microtonal neck: more (or fewer) frets to the octave."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters

QUARTER_TONES = replace(Prototype001Parameters(), frets_per_octave=24, fret_count=48)


def test_a_quarter_tone_neck_has_its_octave_at_half_the_scale() -> None:
    geometry = QUARTER_TONES.build()
    slots = geometry.fret_layout.slots
    half = QUARTER_TONES.scale_length / 2.0

    assert len(slots) == 48
    # Its 24th fret is the octave: as far from the nut as from the saddles.
    assert slots[23].start.x == pytest.approx(slots[23].end.x)
    nut = geometry.fret_layout.fretboard.centerline.line.start.x
    assert slots[23].start.x - nut == pytest.approx(half)
    # Its 48th, two octaves up, where an ordinary neck's 24th is.
    ordinary = Prototype001Parameters().build().fret_layout.slots
    assert slots[47].start.x == pytest.approx(ordinary[23].start.x)


def test_its_markers_stay_at_the_usual_pitches() -> None:
    single, double = QUARTER_TONES.marker_frets()

    assert single == (6, 10, 14, 18, 30, 34, 38, 42)
    assert double == (24, 48)
    markers = QUARTER_TONES.inlay_design().markers
    assert sorted({marker.fret_number for marker in markers}) == sorted(
        (*single, *double)
    )
    # Twelve to the octave, the markers are on the frets listed.
    assert Prototype001Parameters().marker_frets() == (
        (3, 5, 7, 9, 15, 17, 19, 21),
        (12, 24),
    )


def test_the_neck_is_carved_at_the_same_places() -> None:
    # Its 1st and 12th fret stations stay a semitone and the octave up:
    # the hand meets the same neck, whatever the fretting.
    ordinary = Prototype001Parameters().build().neck_surface
    microtonal = QUARTER_TONES.build().neck_surface

    for fret in (1, 12):
        assert microtonal.station_positions_reference(fret) == pytest.approx(
            ordinary.station_positions_reference(fret)
        )
    assert microtonal.neck_outline.last_fret_position == pytest.approx(
        ordinary.neck_outline.last_fret_position
    )


def test_fanned_frets_turn_about_a_microtonal_fret() -> None:
    fanned = replace(QUARTER_TONES, bass_scale_length=660.4, perpendicular_fret=14.0)
    # The 14th quarter tone is the 7th semitone's place.
    assert fanned.fret_skew.perpendicular_fraction == pytest.approx(
        1.0 - 2.0 ** (-7.0 / 12.0)
    )


@pytest.mark.parametrize("steps", [4, 73])
def test_too_few_or_too_many_frets_to_the_octave_are_refused(steps: int) -> None:
    with pytest.raises(NeckGeometryError, match="frets_per_octave"):
        replace(Prototype001Parameters(), frets_per_octave=steps).build()
