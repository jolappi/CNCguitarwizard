"""Tests for the instrument styles: a whole instrument in one choice."""

import pytest

from cncguitarwizard.presets.prototype001 import INSTRUMENT_OVERRIDES, NECK_TEMPLATES
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.webapp import (
    load_design,
    neck_through_changes,
    parameter_schema,
    style_design,
)

OFFERED = [
    (key, instrument)
    for key, style in STYLES.items()
    for instrument in style.instruments
]


@pytest.mark.parametrize(("key", "instrument"), OFFERED)
def test_every_style_builds_for_every_instrument_it_is_offered_for(
    key: str, instrument: str
) -> None:
    design = style_design(instrument, key, "My guitar")

    # Loaded as a saved design is, it builds as it is.
    loaded = load_design(design)
    assert loaded.name == "My guitar"
    assert loaded.skipped == ()
    loaded.parameters.build()


def test_a_style_sets_its_body_neck_and_the_rest() -> None:
    loaded = load_design(style_design("electric_guitar", "les_paul"))
    parameters = loaded.parameters

    assert parameters.neck_joint == "set"
    assert parameters.body_pickups == "HH"
    assert parameters.body_bridge.kind == "tune_o_matic"
    assert parameters.inlay_style == "trapezoid"
    # The Gibson neck's headstock, drawn.
    for name, value in NECK_TEMPLATES["gibson"][1].items():
        assert getattr(parameters, name) == value
    # A Floyd Rose is set for the instrument's strings.
    seven = load_design(style_design("seven_string_guitar", "jackson_rr")).parameters
    assert seven.body_bridge.kind == "floyd_rose"
    assert seven.body_bridge.string_count == 7  # type: ignore[union-attr]


def test_styles_are_offered_by_instrument_and_others_refused() -> None:
    styles = parameter_schema()["styles"]

    assert list(styles) == list(STYLES)
    assert styles["stratocaster"]["instruments"] == ["electric_guitar"]
    assert "bass_guitar" in styles["jazz_bass"]["instruments"]
    assert all(
        instrument in INSTRUMENT_OVERRIDES
        for style in styles.values()
        for instrument in style["instruments"]
    )
    assert "error" in style_design("bass_guitar", "stratocaster")
    assert "error" in style_design("electric_guitar", "no_such_style")


@pytest.mark.parametrize(("key", "instrument"), OFFERED)
def test_every_style_builds_neck_through_from_easy_mode(
    key: str, instrument: str
) -> None:
    # Easy mode's Neck-through tick: the joint and what such a neck
    # cannot keep, changed together.
    design = style_design(instrument, key)
    changes = neck_through_changes(design["prototype"])
    design["prototype"].update(changes)

    parameters = load_design(design).parameters
    assert parameters.neck_joint == "neck_through"
    parameters.build()


def test_neck_through_changes_only_what_it_must() -> None:
    strat = style_design("electric_guitar", "stratocaster")["prototype"]
    assert neck_through_changes(strat) == {
        "neck_joint": "neck_through",
        "neck_heel_end": "square",
        "body_neck_plate": "ferrules",
    }
    # A Telecaster's vintage rod, adjusted at the heel with no spoke wheel.
    tele = style_design("electric_guitar", "telecaster")["prototype"]
    assert neck_through_changes(tele)["truss_rod_adjustment"] == "headstock"
    # Already neck-through, or the defaults (a missing setting): no more.
    rhoads = style_design("electric_guitar", "jackson_rr")["prototype"]
    assert neck_through_changes(rhoads) == {}
    assert neck_through_changes({}) == {"neck_joint": "neck_through"}
