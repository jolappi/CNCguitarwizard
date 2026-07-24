"""Tests for guitar neck centerline geometry."""

import pytest

from cncguitarwizard.geometry.exceptions import GeometryException
from cncguitarwizard.geometry.neck import Centerline
from cncguitarwizard.geometry.primitives import Line2D, Point2D


def test_centerline_constructs_a_line_from_nut_to_scale_length() -> None:
    centerline = Centerline(609.6)

    assert centerline.scale_length == 609.6
    assert centerline.line == Line2D(Point2D(0.0, 0.0), Point2D(609.6, 0.0))


def test_centerline_length_delegates_to_its_line() -> None:
    centerline = Centerline(609.6)

    assert centerline.length == centerline.line.length == 609.6


@pytest.mark.parametrize(
    "scale_length",
    [0.0, -1.0, float("inf"), float("-inf"), float("nan")],
)
def test_centerline_rejects_a_scale_length_that_is_not_positive(
    scale_length: float,
) -> None:
    with pytest.raises(GeometryException):
        Centerline(scale_length)
