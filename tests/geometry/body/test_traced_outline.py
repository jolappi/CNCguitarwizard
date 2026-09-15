"""Tests for outlines digitised from an external reference drawing."""

import pytest

from cncguitarwizard.geometry.body import TracedOutline
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D


def test_traced_outline_exposes_its_points() -> None:
    points = (Point2D(0.0, 0.0), Point2D(10.0, 0.0), Point2D(5.0, 10.0))

    outline = TracedOutline(points)

    assert outline.points == points


def test_traced_outline_rejects_fewer_than_three_points() -> None:
    with pytest.raises(BodyGeometryError):
        TracedOutline((Point2D(0.0, 0.0), Point2D(10.0, 0.0)))


def test_traced_outline_rejects_non_finite_points() -> None:
    with pytest.raises(BodyGeometryError):
        TracedOutline(
            (
                Point2D(0.0, 0.0),
                Point2D(float("nan"), 0.0),
                Point2D(5.0, 10.0),
            )
        )
