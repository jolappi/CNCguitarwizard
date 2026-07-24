"""Tests for fret slots bounded by a tapered fretboard."""

from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.fretboard import Fretboard, FretLayout
from cncguitarwizard.geometry.neck import Centerline


def make_fretboard() -> Fretboard:
    """Return the Prototype001 fretboard foundation."""
    scale_length = 609.6
    return Fretboard(
        scale_length=scale_length,
        nut_width=42.0,
        bridge_width=63.0,
        centerline=Centerline(scale_length),
    )


def test_layout_generates_the_requested_number_of_slots() -> None:
    layout = FretLayout(make_fretboard(), fret_count=24)

    assert len(layout.slots) == 24


def test_slot_centers_match_equal_temperament_positions() -> None:
    fretboard = make_fretboard()
    positions = FretCalculator.calculate(fretboard.scale_length, 24)
    layout = FretLayout(fretboard, fret_count=24)

    for slot, position in zip(layout.slots, positions, strict=True):
        slot_center_x = (slot.start.x + slot.end.x) / 2.0
        slot_center_y = (slot.start.y + slot.end.y) / 2.0

        assert slot_center_x == pytest.approx(position.distance_from_nut)
        assert slot_center_y == pytest.approx(0.0)


def test_slot_lengths_follow_the_linear_fretboard_taper() -> None:
    fretboard = make_fretboard()
    positions = FretCalculator.calculate(fretboard.scale_length, 24)
    layout = FretLayout(fretboard, fret_count=24)

    for slot, position in zip(layout.slots, positions, strict=True):
        fraction = position.distance_from_nut / fretboard.scale_length
        expected_width = (
            fretboard.nut_width
            + (fretboard.bridge_width - fretboard.nut_width) * fraction
        )

        assert slot.length == pytest.approx(expected_width)


def test_twelfth_fret_slot_is_halfway_through_the_taper() -> None:
    fretboard = make_fretboard()
    layout = FretLayout(fretboard, fret_count=24)

    assert layout.slots[11].length == pytest.approx(
        (fretboard.nut_width + fretboard.bridge_width) / 2.0
    )


def test_layout_is_immutable() -> None:
    layout = FretLayout(make_fretboard(), fret_count=24)

    with pytest.raises(FrozenInstanceError):
        layout.fret_count = 22


@pytest.mark.parametrize("fret_count", [0, -1])
def test_layout_rejects_non_positive_fret_counts(fret_count: int) -> None:
    with pytest.raises(FretboardGeometryError):
        FretLayout(make_fretboard(), fret_count=fret_count)
