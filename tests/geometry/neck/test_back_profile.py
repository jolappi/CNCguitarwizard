"""Tests for Wizard-inspired D neck-back profile references."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import (
    NeckBackCrossSection,
    NeckOutline,
    NeckProfileStations,
)


def make_outline() -> NeckOutline:
    """Return the locked Prototype001 neck outline."""
    return NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)


def test_d_profile_preserves_width_and_center_depth() -> None:
    section = NeckBackCrossSection(51.3333333333, 19.0)
    center = section.back_curve[len(section.back_curve) // 2]

    assert section.underside_line.length == pytest.approx(51.3333333333)
    assert center.x == pytest.approx(0.0)
    assert center.y == pytest.approx(-19.0)


def test_d_profile_is_symmetric() -> None:
    section = NeckBackCrossSection(43.047, 17.0)

    for left, right in zip(
        section.back_curve,
        reversed(section.back_curve),
        strict=True,
    ):
        assert left.x == pytest.approx(-right.x)
        assert left.y == pytest.approx(right.y)


def test_profile_stations_derive_widths_from_neck_taper() -> None:
    stations = NeckProfileStations(make_outline(), 17.0, 19.0)

    assert stations.first_fret.fret_number == 1
    assert stations.twelfth_fret.fret_number == 12
    assert stations.first_fret.width == pytest.approx(43.047, abs=0.001)
    assert stations.twelfth_fret.width == pytest.approx(51.333, abs=0.001)
    assert stations.first_fret.cross_section.depth == 17.0
    assert stations.twelfth_fret.cross_section.depth == 19.0


def test_profile_geometry_is_immutable() -> None:
    section = NeckBackCrossSection(43.047, 17.0)

    with pytest.raises(FrozenInstanceError):
        section.exponent = 4.0


@pytest.mark.parametrize(
    "create_profile",
    [
        lambda: NeckBackCrossSection(0.0, 17.0),
        lambda: NeckBackCrossSection(43.0, 0.0),
        lambda: NeckBackCrossSection(43.0, 17.0, exponent=1.9),
        lambda: NeckBackCrossSection(43.0, 17.0, sample_count=2),
        lambda: NeckBackCrossSection(43.0, 17.0, sample_count=32),
        lambda: NeckProfileStations(make_outline(), 20.0, 19.0),
    ],
)
def test_profiles_reject_invalid_parameters(
    create_profile: Callable[[], NeckBackCrossSection | NeckProfileStations],
) -> None:
    with pytest.raises(NeckGeometryError):
        create_profile()
