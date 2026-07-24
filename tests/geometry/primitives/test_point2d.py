from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.primitives.point2d import Point2D


def test_point_exposes_its_coordinates():
    point = Point2D(x=10.0, y=20.0)

    assert point.x == 10.0
    assert point.y == 20.0


def test_points_with_matching_coordinates_are_equal():
    assert Point2D(1.0, 2.0) == Point2D(1.0, 2.0)


def test_points_with_different_coordinates_are_not_equal():
    assert Point2D(1.0, 2.0) != Point2D(2.0, 1.0)


def test_point_coordinates_cannot_be_reassigned():
    point = Point2D(1.0, 2.0)

    with pytest.raises(FrozenInstanceError):
        point.x = 5.0
