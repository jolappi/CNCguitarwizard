"""Tests for immutable two-dimensional point transformations."""

import math

import pytest

from cncguitarwizard.geometry.primitives import Point2D, Vector2D
from cncguitarwizard.geometry.transforms import mirror_x, mirror_y, rotate, translate


def test_translate_returns_a_new_point_displaced_by_the_vector() -> None:
    point = Point2D(2.0, 3.0)

    result = translate(point, Vector2D(-1.0, 4.0))

    assert result == Point2D(1.0, 7.0)
    assert result is not point


def test_rotate_by_zero_preserves_the_point_coordinates() -> None:
    point = Point2D(2.0, 3.0)

    result = rotate(point, 0.0)

    assert result == point
    assert result is not point


def test_rotate_by_ninety_degrees_is_counter_clockwise_about_the_origin() -> None:
    result = rotate(Point2D(2.0, 3.0), math.pi / 2.0)

    assert result.x == pytest.approx(-3.0)
    assert result.y == pytest.approx(2.0)


def test_mirror_x_negates_only_the_y_coordinate() -> None:
    assert mirror_x(Point2D(2.0, 3.0)) == Point2D(2.0, -3.0)


def test_mirror_y_negates_only_the_x_coordinate() -> None:
    assert mirror_y(Point2D(2.0, 3.0)) == Point2D(-2.0, 3.0)
