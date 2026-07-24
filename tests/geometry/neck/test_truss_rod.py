"""Tests for double-action truss-rod channel geometry."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import TrussRodGeometryError
from cncguitarwizard.geometry.neck import NeckOutline, TrussRodChannel
from cncguitarwizard.geometry.primitives import Point2D


def make_neck_outline() -> NeckOutline:
    """Return the locked Prototype001 neck outline."""
    return NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)


def make_channel() -> TrussRodChannel:
    """Return the locked Prototype001 truss-rod channel."""
    return TrussRodChannel(
        neck_outline=make_neck_outline(),
        start_position=12.0,
        length=440.0,
        width=6.0,
        depth=9.0,
        adjustment_side="heel",
    )


def test_channel_uses_locked_rod_dimensions() -> None:
    channel = make_channel()

    assert channel.centerline.length == pytest.approx(440.0)
    assert channel.top_boundary[0].y - channel.top_boundary[1].y == 6.0
    assert channel.side_boundary[0].y - channel.side_boundary[1].y == 9.0


def test_channel_is_centered_on_the_neck() -> None:
    channel = make_channel()

    assert channel.centerline.start == Point2D(12.0, 0.0)
    assert channel.centerline.end == Point2D(452.0, 0.0)
    assert channel.top_boundary[0].y == pytest.approx(
        -channel.top_boundary[1].y
    )


def test_heel_adjustment_reference_is_at_channel_end() -> None:
    channel = make_channel()

    assert channel.adjustment_point == Point2D(channel.end_position, 0.0)


def test_channel_is_immutable() -> None:
    channel = make_channel()

    with pytest.raises(FrozenInstanceError):
        channel.depth = 10.0


@pytest.mark.parametrize(
    "create_channel",
    [
        lambda: TrussRodChannel(make_neck_outline(), -1.0, 440.0, 6.0, 9.0),
        lambda: TrussRodChannel(make_neck_outline(), 12.0, 0.0, 6.0, 9.0),
        lambda: TrussRodChannel(make_neck_outline(), 12.0, 600.0, 6.0, 9.0),
        lambda: TrussRodChannel(make_neck_outline(), 12.0, 440.0, 50.0, 9.0),
        lambda: TrussRodChannel(
            make_neck_outline(),
            12.0,
            440.0,
            6.0,
            9.0,
            minimum_side_clearance=-1.0,
        ),
    ],
)
def test_channel_rejects_invalid_or_non_fitting_geometry(
    create_channel: Callable[[], TrussRodChannel],
) -> None:
    with pytest.raises(TrussRodGeometryError):
        create_channel()
