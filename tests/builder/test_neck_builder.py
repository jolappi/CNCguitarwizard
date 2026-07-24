"""Tests for the fluent neck builder."""

from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.builder import BuilderError, NeckBuilder


def test_neck_builder_creates_a_neck_with_requested_dimensions() -> None:
    neck = (
        NeckBuilder()
        .scale_length(609.6)
        .nut_width(42.0)
        .bridge_width(63.0)
        .build()
    )

    assert neck.scale_length == 609.6
    assert neck.nut_width == 42.0
    assert neck.bridge_width == 63.0
    assert neck.centerline.length == 609.6
    assert neck.fretboard.nut_line.length == 42.0
    assert neck.fretboard.bridge_line.length == 63.0


def test_neck_builder_returns_a_new_builder_for_each_configuration_step() -> None:
    builder = NeckBuilder()

    configured_builder = builder.scale_length(609.6)

    assert configured_builder is not builder


def test_neck_model_is_immutable() -> None:
    neck = NeckBuilder().scale_length(609.6).nut_width(42.0).bridge_width(63.0).build()

    with pytest.raises(FrozenInstanceError):
        neck.nut_width = 43.0


@pytest.mark.parametrize(
    "builder",
    [
        NeckBuilder(),
        NeckBuilder().scale_length(609.6),
        NeckBuilder().scale_length(609.6).nut_width(42.0),
    ],
)
def test_neck_builder_rejects_missing_required_dimensions(
    builder: NeckBuilder,
) -> None:
    with pytest.raises(BuilderError):
        builder.build()


@pytest.mark.parametrize(
    "builder",
    [
        NeckBuilder().scale_length(0.0).nut_width(42.0).bridge_width(63.0),
        NeckBuilder().scale_length(609.6).nut_width(0.0).bridge_width(63.0),
        NeckBuilder().scale_length(609.6).nut_width(42.0).bridge_width(0.0),
    ],
)
def test_neck_builder_rejects_non_positive_dimensions(builder: NeckBuilder) -> None:
    with pytest.raises(BuilderError):
        builder.build()
