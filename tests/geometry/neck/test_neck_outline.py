"""Tests for top-view guitar neck outline geometry."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.neck import NeckOutline


def make_outline() -> NeckOutline:
    """Return the locked Prototype001 neck outline."""
    return NeckOutline(
        scale_length=609.6,
        fret_count=24,
        nut_width=42.0,
        last_fret_width=56.0,
        heel_width=56.0,
        heel_length=63.0,
    )


def test_outline_uses_the_calculated_final_fret_position() -> None:
    outline = make_outline()
    expected_position = FretCalculator.calculate(609.6, 24)[-1].distance_from_nut

    assert outline.last_fret_position == pytest.approx(expected_position)
    assert outline.last_fret_line.start.x == pytest.approx(expected_position)


def test_outline_preserves_requested_widths() -> None:
    outline = make_outline()

    assert outline.nut_line.length == pytest.approx(42.0)
    assert outline.last_fret_line.length == pytest.approx(56.0)
    assert outline.heel_end_line.length == pytest.approx(56.0)


def test_parallel_heel_has_the_requested_length() -> None:
    outline = make_outline()

    assert outline.left_heel.length == pytest.approx(63.0)
    assert outline.right_heel.length == pytest.approx(63.0)


def test_outline_is_symmetric_about_the_centerline() -> None:
    outline = make_outline()

    for left, right in (
        (outline.nut_line.start, outline.nut_line.end),
        (outline.last_fret_line.start, outline.last_fret_line.end),
        (outline.heel_end_line.start, outline.heel_end_line.end),
    ):
        assert left.x == pytest.approx(right.x)
        assert left.y == pytest.approx(-right.y)


def test_outline_is_immutable() -> None:
    outline = make_outline()

    with pytest.raises(FrozenInstanceError):
        outline.heel_length = 70.0


@pytest.mark.parametrize(
    "create_outline",
    [
        lambda: NeckOutline(0.0, 24, 42.0, 56.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 0, 42.0, 56.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 24, 0.0, 56.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 24, 42.0, 41.0, 56.0, 63.0),
        lambda: NeckOutline(609.6, 24, 42.0, 56.0, 55.0, 63.0),
        lambda: NeckOutline(609.6, 24, 42.0, 56.0, 56.0, float("nan")),
    ],
)
def test_outline_rejects_invalid_dimensions(
    create_outline: Callable[[], NeckOutline],
) -> None:
    with pytest.raises(NeckGeometryError):
        create_outline()
