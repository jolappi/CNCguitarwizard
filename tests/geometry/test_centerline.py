import math

import pytest

from cncguitarwizard.geometry import GeometryException, Line2D
from cncguitarwizard.geometry.centerline import Centerline
from cncguitarwizard.geometry.primitives import Point2D


def test_centerline_starts_at_the_nut_and_ends_at_the_bridge():
    centerline = Centerline.create(609.6)

    assert centerline == Line2D(Point2D(0.0, 0.0), Point2D(609.6, 0.0))


@pytest.mark.parametrize("scale_length", [0.0, -1.0, math.inf, math.nan])
def test_centerline_rejects_invalid_scale_lengths(scale_length: float) -> None:
    with pytest.raises(GeometryException):
        Centerline.create(scale_length)
