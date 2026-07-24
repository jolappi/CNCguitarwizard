"""Public geometry primitives and exceptions."""

from .exceptions import (
    FretboardGeometryError,
    GeometryException,
    NeckGeometryError,
    ZeroLengthVectorError,
)
from .primitives import Line2D, Point2D, Vector2D

__all__ = [
    "GeometryException",
    "FretboardGeometryError",
    "Line2D",
    "NeckGeometryError",
    "Point2D",
    "Vector2D",
    "ZeroLengthVectorError",
]
