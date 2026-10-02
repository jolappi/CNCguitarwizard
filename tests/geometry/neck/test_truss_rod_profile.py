"""Tests for the standard and low-profile truss rods and the neck they need."""

from dataclasses import replace

import pytest

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import TELECASTER_NECK, TRUSS_ROD_MIN_FLOOR
from cncguitarwizard.webapp import parameter_schema

HEADSTOCK = replace(Prototype001Parameters(), truss_rod_adjustment="headstock")
LOW = replace(HEADSTOCK, truss_rod_profile="low_profile")


def test_a_headstock_adjusted_standard_rod_thickens_the_neck() -> None:
    # The 11 mm pocket lies in the neck by the nut: 1 mm of wood under it
    # at its edges, where the D profile has curved up (12.3 mm at the
    # centre of the 42 mm neck), so 18.3 mm with the 6 mm board.
    assert TRUSS_ROD_MIN_FLOOR == 1.0
    assert HEADSTOCK.first_fret_thickness_needed() == pytest.approx(18.3)
    assert HEADSTOCK.first_fret_thickness == 17.0
    # At the heel, or with a low-profile rod, the neck stays as set.
    assert Prototype001Parameters().first_fret_thickness_needed() == 17.0
    assert LOW.first_fret_thickness_needed() == 17.0
    # A neck already thick enough is left alone.
    thick = replace(HEADSTOCK, first_fret_thickness=21.0)
    assert thick.first_fret_thickness_needed() == 21.0


def test_the_adjusting_end_stays_on_the_neck_side() -> None:
    channel = HEADSTOCK.build().truss_rod_channel
    assert channel.start_position == pytest.approx(-5.0)
    assert min(min(p.x for p in part.boundary) for part in channel.pockets) == (
        pytest.approx(-5.0)
    )


def test_a_low_profile_rod_is_one_straight_shallow_channel() -> None:
    channel = LOW.build().truss_rod_channel
    assert channel.pockets == ()
    assert (channel.width, channel.depth) == (6.35, 9.5)
    assert channel.axis_depth == pytest.approx(4.75)
    # Reached with its hex key through a notch, covered behind a shelf nut.
    trough = channel.adjuster_boundary
    assert 2.0 * max(p.y for p in trough) == pytest.approx(8.0)
    assert channel.adjuster_depth == pytest.approx(4.75 + 4.0)


def test_a_low_profile_rod_takes_no_spoke_wheel_by_default() -> None:
    heel = replace(Prototype001Parameters(), truss_rod_profile="low_profile")
    assert not heel.truss_rod_spoke_wheel_fitted
    geometry = heel.build()
    outline = geometry.truss_rod_channel.neck_outline
    # Without a wheel its adjuster sits at the heel's end face.
    assert geometry.truss_rod_channel.end_position == pytest.approx(
        outline.last_fret_position + outline.heel_length
    )


@pytest.mark.parametrize("profile", ["standard", "low_profile"])
def test_the_telecaster_neck_takes_either_rod_at_the_headstock(profile: str) -> None:
    parameters = replace(
        Prototype001Parameters(),
        **{
            **TELECASTER_NECK,
            "truss_rod_adjustment": "headstock",
            "truss_rod_profile": profile,
        },
    )
    channel = parameters.build().truss_rod_channel
    assert channel.start_position == pytest.approx(-9.5)


def test_the_web_form_offers_the_rod_profile() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    profile = fields["truss_rod_profile"]
    assert profile["type"] == "choice" and not profile["advanced"]
    assert profile["options"] == ["standard", "low_profile"]
