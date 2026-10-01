"""Tests for the monotone and the rounded cubic curves."""

import pytest

from cncguitarwizard.geometry.exceptions import GeometryException
from cncguitarwizard.geometry.primitives import MonotoneCurve, SmoothCurve


def test_curve_passes_through_its_points_and_starts_flat() -> None:
    curve = MonotoneCurve(((0.0, 21.0), (45.0, 33.0), (150.0, 20.0)))

    assert curve.value_at(0.0) == 21.0
    assert curve.value_at(45.0) == pytest.approx(33.0)
    assert curve.value_at(150.0) == pytest.approx(20.0)
    assert curve.slopes[0] == 0.0
    # A peak gets a flat slope, so the curve never overshoots it.
    assert curve.slopes[1] == 0.0
    assert max(curve.value_at(x / 10.0) for x in range(1501)) == pytest.approx(33.0)


def test_curve_stays_between_neighbouring_points() -> None:
    curve = MonotoneCurve(((0.0, 0.0), (10.0, 1.0), (20.0, 9.0), (30.0, 10.0)))

    for x in range(10, 21):
        assert 1.0 - 1e-9 <= curve.value_at(float(x)) <= 9.0 + 1e-9


def test_curve_holds_its_ends_outside_the_range() -> None:
    curve = MonotoneCurve(((0.0, 5.0), (10.0, 8.0)))

    assert curve.value_at(-3.0) == 5.0
    assert curve.value_at(99.0) == 8.0


@pytest.mark.parametrize(
    "points",
    [
        ((0.0, 1.0),),
        ((0.0, 1.0), (0.0, 2.0)),
        ((0.0, 1.0), (5.0, 2.0), (4.0, 3.0)),
        ((0.0, 1.0), (5.0, float("nan"))),
    ],
)
def test_curve_rejects_bad_points(points: tuple[tuple[float, float], ...]) -> None:
    with pytest.raises(GeometryException):
        MonotoneCurve(points)


def test_a_smooth_curve_rounds_through_a_peak() -> None:
    points = ((0.0, 20.0), (40.0, 30.0), (80.0, 20.0), (120.0, 28.0))
    curve = SmoothCurve(points)

    for x, y in points:
        assert curve.value_at(x) == pytest.approx(y)
    # Each handle's slope is its neighbours' chord: through the low handle
    # at 80 mm it keeps moving, swinging below it into a round hollow
    # (MonotoneCurve would stop flat at it and never dip past it).
    assert curve.slopes[2] == pytest.approx((28.0 - 30.0) / 80.0)
    assert min(curve.value_at(x / 2.0) for x in range(160, 241)) < 20.0
    # Outside the points the ends are held flat.
    assert curve.value_at(200.0) == 28.0


def test_a_smooth_curve_needs_increasing_x() -> None:
    with pytest.raises(GeometryException):
        SmoothCurve(((0.0, 1.0), (0.0, 2.0)))
