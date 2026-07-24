"""Tests for equal-temperament fret calculations."""

import math
from dataclasses import FrozenInstanceError

import pytest

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
