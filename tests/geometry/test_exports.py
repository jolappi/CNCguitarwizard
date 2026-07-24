"""Tests for the public geometry package API."""

from cncguitarwizard.geometry import (
    GeometryException,
    Line2D,
    Point2D,
    Vector2D,
    ZeroLengthVectorError,
)


def test_geometry_package_exports_public_api() -> None:
    assert GeometryException.__name__ == "GeometryException"
    assert Line2D.__name__ == "Line2D"
    assert Point2D.__name__ == "Point2D"
    assert Vector2D.__name__ == "Vector2D"
    assert ZeroLengthVectorError.__name__ == "ZeroLengthVectorError"
