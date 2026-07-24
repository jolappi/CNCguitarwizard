"""Tests for fretboard side and cross-section profiles."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fretboard import (
    FretboardCrossSection,
    FretboardSideProfile,
)


def test_side_profile_uses_six_millimetre_center_thickness() -> None:
    profile = FretboardSideProfile(609.6, 24, 6.0)

    assert profile.top_line.start.y == profile.top_line.end.y == 6.0
    assert profile.end_position == pytest.approx(457.2)


def test_cross_section_has_requested_center_and_edge_thicknesses() -> None:
    section = FretboardCrossSection(56.0, 430.0, 6.0)

    assert section.top_arc[len(section.top_arc) // 2].y == pytest.approx(6.0)
    assert section.top_arc[0].y == pytest.approx(section.edge_thickness)
    assert section.top_arc[-1].y == pytest.approx(section.edge_thickness)
    assert section.edge_thickness == pytest.approx(5.087, abs=0.001)


def test_cross_section_is_symmetric_about_its_centerline() -> None:
    section = FretboardCrossSection(42.0, 430.0, 6.0)

    for left, right in zip(section.top_arc, reversed(section.top_arc), strict=True):
        assert left.x == pytest.approx(-right.x)
        assert left.y == pytest.approx(right.y)


def test_profile_geometry_is_immutable() -> None:
    section = FretboardCrossSection(56.0, 430.0, 6.0)

    with pytest.raises(FrozenInstanceError):
        section.radius = 400.0


@pytest.mark.parametrize(
    "create_profile",
    [
        lambda: FretboardSideProfile(0.0, 24, 6.0),
        lambda: FretboardSideProfile(609.6, 0, 6.0),
        lambda: FretboardCrossSection(0.0, 430.0, 6.0),
        lambda: FretboardCrossSection(56.0, 28.0, 6.0),
        lambda: FretboardCrossSection(56.0, 430.0, 0.1),
        lambda: FretboardCrossSection(56.0, 430.0, 6.0, sample_count=2),
        lambda: FretboardCrossSection(56.0, 430.0, 6.0, sample_count=32),
    ],
)
def test_profiles_reject_invalid_dimensions(
    create_profile: Callable[[], FretboardSideProfile | FretboardCrossSection],
) -> None:
    with pytest.raises(FretboardGeometryError):
        create_profile()
