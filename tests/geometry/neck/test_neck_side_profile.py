"""Tests for longitudinal neck thickness geometry."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import NeckSideProfile


def make_profile() -> NeckSideProfile:
    """Return the locked Prototype001 neck wood profile."""
    return NeckSideProfile(
        scale_length=609.6,
        fret_count=24,
        first_fret_thickness=17.0,
        twelfth_fret_thickness=19.0,
        heel_thickness=20.0,
        heel_length=63.0,
    )


def test_profile_places_thicknesses_at_their_reference_frets() -> None:
    profile = make_profile()

    first_fret_point = profile.bottom_segments[0].end
    twelfth_fret_point = profile.bottom_segments[1].end
    heel_start_point = profile.bottom_segments[2].end

    assert first_fret_point.x == pytest.approx(profile.first_fret_position)
    assert first_fret_point.y == pytest.approx(-17.0)
    assert twelfth_fret_point.x == pytest.approx(profile.twelfth_fret_position)
    assert twelfth_fret_point.y == pytest.approx(-19.0)
    assert heel_start_point.x == pytest.approx(profile.last_fret_position)
    assert heel_start_point.y == pytest.approx(-20.0)


def test_profile_keeps_the_heel_parallel_and_constant_thickness() -> None:
    profile = make_profile()
    heel_segment = profile.bottom_segments[-1]

    assert heel_segment.length == pytest.approx(63.0)
    assert heel_segment.start.y == heel_segment.end.y == -20.0
    assert profile.top_line.end.x == pytest.approx(profile.heel_end_position)


def test_profile_is_immutable() -> None:
    profile = make_profile()

    with pytest.raises(FrozenInstanceError):
        profile.heel_thickness = 21.0


@pytest.mark.parametrize(
    "create_profile",
    [
        lambda: NeckSideProfile(0.0, 24, 17.0, 19.0, 20.0, 63.0),
        lambda: NeckSideProfile(609.6, 11, 17.0, 19.0, 20.0, 63.0),
        lambda: NeckSideProfile(609.6, 24, 0.0, 19.0, 20.0, 63.0),
        lambda: NeckSideProfile(609.6, 24, 20.0, 19.0, 20.0, 63.0),
        lambda: NeckSideProfile(609.6, 24, 17.0, 21.0, 20.0, 63.0),
        lambda: NeckSideProfile(609.6, 24, 17.0, 19.0, 20.0, float("nan")),
    ],
)
def test_profile_rejects_invalid_dimensions(
    create_profile: Callable[[], NeckSideProfile],
) -> None:
    with pytest.raises(NeckGeometryError):
        create_profile()
