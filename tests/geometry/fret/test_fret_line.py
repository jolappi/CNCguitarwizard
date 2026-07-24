"""Tests for fret lines derived from a neck centerline."""

from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.fret import FretCalculator, FretLine
from cncguitarwizard.geometry.neck import Centerline
from cncguitarwizard.geometry.primitives import Point2D, Vector2D


def test_fret_line_location_is_derived_from_the_centerline() -> None:
    centerline = Centerline(609.6)
    position = FretCalculator.calculate(centerline.length, 1)[0]

    fret_line = FretLine(centerline, position)

    assert fret_line.location == Point2D(position.distance_from_nut, 0.0)


def test_fret_line_direction_is_perpendicular_to_the_centerline() -> None:
    centerline = Centerline(609.6)
    position = FretCalculator.calculate(centerline.length, 1)[0]
    centerline_direction = Vector2D(
        centerline.line.end.x - centerline.line.start.x,
        centerline.line.end.y - centerline.line.start.y,
    )

    fret_line = FretLine(centerline, position)

    assert fret_line.direction.length == pytest.approx(1.0)
    assert fret_line.direction.dot(centerline_direction) == pytest.approx(0.0)


def test_fret_line_is_immutable() -> None:
    centerline = Centerline(609.6)
    position = FretCalculator.calculate(centerline.length, 1)[0]
    fret_line = FretLine(centerline, position)

    with pytest.raises(FrozenInstanceError):
        fret_line.location = Point2D(0.0, 0.0)
