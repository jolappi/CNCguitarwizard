"""Tests for equal-temperament fret calculations."""

import math
from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fret import FretCalculator, FretPosition


def test_fret_calculator_returns_the_expected_first_fret_position() -> None:
    scale_length = 609.6
    position = FretCalculator.calculate(scale_length, 24)[0]
    expected_remaining_scale = scale_length / math.pow(2.0, 1.0 / 12.0)

    assert position.number == 1
    assert position.distance_from_nut == pytest.approx(
        scale_length - expected_remaining_scale
    )
    assert position.remaining_scale == pytest.approx(expected_remaining_scale)


def test_fret_calculator_places_the_twelfth_fret_at_half_the_scale_length() -> None:
    position = FretCalculator.calculate(609.6, 24)[11]

    assert position.number == 12
    assert position.distance_from_nut == pytest.approx(304.8)
    assert position.remaining_scale == pytest.approx(304.8)


def test_fret_calculator_returns_the_requested_number_of_positions() -> None:
    assert len(FretCalculator.calculate(609.6, 24)) == 24


def test_fret_position_is_immutable() -> None:
    position = FretPosition(1, 34.214, 575.386)

    with pytest.raises(FrozenInstanceError):
        position.number = 2


def test_a_microtonal_octave_is_divided_into_its_own_equal_steps() -> None:
    semitones = FretCalculator.calculate(609.6, 24)
    quarter_tones = FretCalculator.calculate(609.6, 48, frets_per_octave=24)

    # Every other quarter tone is a semitone; the octave is still at half.
    assert [p.distance_from_nut for p in quarter_tones[1::2]] == pytest.approx(
        [p.distance_from_nut for p in semitones]
    )
    assert quarter_tones[23].distance_from_nut == pytest.approx(304.8)
    nineteen = FretCalculator.calculate(609.6, 19, frets_per_octave=19)
    assert nineteen[-1].distance_from_nut == pytest.approx(304.8)
    with pytest.raises(FretboardGeometryError, match="at least one fret"):
        FretCalculator.calculate(609.6, 24, frets_per_octave=0)


def test_the_nearest_fret_to_a_pitch() -> None:
    assert FretCalculator.nearest_fret(7) == 7
    # A quarter-tone neck: two frets a semitone.
    assert FretCalculator.nearest_fret(3, 24) == 6
    assert FretCalculator.nearest_fret(12, 24) == 24
    # 19 per octave: semitone 3 is 4.75 steps, 7 is 11.08; 22: 5.5 rounds up.
    assert FretCalculator.nearest_fret(3, 19) == 5
    assert FretCalculator.nearest_fret(7, 19) == 11
    assert FretCalculator.nearest_fret(3, 22) == 6
