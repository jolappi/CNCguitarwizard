import math
from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.exceptions import ZeroLengthVectorError
from cncguitarwizard.geometry.primitives.vector2d import Vector2D


def test_vector_exposes_its_components():
    vector = Vector2D(x=10.0, y=20.0)

    assert vector.x == 10.0
    assert vector.y == 20.0


def test_vectors_with_matching_components_are_equal():
    assert Vector2D(1.0, 2.0) == Vector2D(1.0, 2.0)


def test_vectors_with_different_components_are_not_equal():
    assert Vector2D(1.0, 2.0) != Vector2D(2.0, 1.0)


def test_vector_components_cannot_be_reassigned():
    vector = Vector2D(1.0, 2.0)

    with pytest.raises(FrozenInstanceError):
        vector.x = 5.0


def test_vector_length_uses_the_euclidean_magnitude():
    assert Vector2D(3.0, 4.0).length == 5.0


def test_zero_length_vector_has_zero_length():
    assert Vector2D(0.0, 0.0).length == 0.0


def test_dot_product_multiplies_and_sums_matching_components():
    assert Vector2D(2.0, 3.0).dot(Vector2D(4.0, -5.0)) == -7.0


def test_cross_product_is_positive_for_a_counter_clockwise_turn():
    assert Vector2D(1.0, 0.0).cross(Vector2D(0.0, 1.0)) == 1.0


def test_cross_product_is_negative_for_a_clockwise_turn():
    assert Vector2D(0.0, 1.0).cross(Vector2D(1.0, 0.0)) == -1.0


def test_angle_to_returns_the_angle_in_radians():
    angle = Vector2D(1.0, 0.0).angle_to(Vector2D(0.0, 1.0))

    assert angle == pytest.approx(math.pi / 2.0)


def test_angle_to_returns_zero_for_parallel_vectors():
    assert Vector2D(2.0, 2.0).angle_to(Vector2D(4.0, 4.0)) == pytest.approx(0.0)


def test_angle_to_rejects_a_zero_length_vector():
    with pytest.raises(ZeroLengthVectorError):
        Vector2D(1.0, 0.0).angle_to(Vector2D(0.0, 0.0))


def test_perpendicular_returns_a_counter_clockwise_rotation():
    vector = Vector2D(2.0, 3.0)

    assert vector.perpendicular() == Vector2D(-3.0, 2.0)
    assert vector.perpendicular().dot(vector) == 0.0


def test_normalized_vector_has_unit_length_and_preserves_direction():
    normalized = Vector2D(3.0, 4.0).normalized()

    assert normalized == Vector2D(0.6, 0.8)
    assert normalized.length == pytest.approx(1.0)


def test_normalizing_a_zero_length_vector_raises_zero_length_vector_error():
    with pytest.raises(ZeroLengthVectorError):
        Vector2D(0.0, 0.0).normalized()
