"""Immutable two-dimensional vector primitive."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Self

from ..exceptions import ZeroLengthVectorError


@dataclass(frozen=True, slots=True)
class Vector2D:
    """Represent a displacement in two-dimensional space.

    Args:
        x: Horizontal component in millimetres.
        y: Vertical component in millimetres.
    """

    x: float
    y: float

    @property
    def length(self) -> float:
        """Return the vector magnitude in millimetres."""
        return math.hypot(self.x, self.y)

    def dot(self, other: Self) -> float:
        """Return the scalar dot product with another vector.

        Args:
            other: Vector to multiply component-wise.

        Returns:
            The scalar dot product.
        """
        return self.x * other.x + self.y * other.y

    def cross(self, other: Self) -> float:
        """Return the scalar two-dimensional cross product.

        Args:
            other: Vector used to form the cross product.

        Returns:
            The signed scalar cross product.
        """
        return self.x * other.y - self.y * other.x

    def angle_to(self, other: Self) -> float:
        """Return the unsigned angle to another vector in radians.

        Args:
            other: Vector to compare with this vector.

        Raises:
            ZeroLengthVectorError: If either vector has zero length.

        Returns:
            The angle between the vectors in the range from zero to pi.
        """
        length_product = self.length * other.length
        if length_product == 0.0:
            raise ZeroLengthVectorError(
                "Cannot calculate an angle with a zero-length vector."
            )

        return math.atan2(abs(self.cross(other)), self.dot(other))

    def perpendicular(self) -> Self:
        """Return a vector rotated 90 degrees counter-clockwise.

        Returns:
            A new perpendicular vector.
        """
        return self.__class__(-self.y, self.x)

    def normalized(self) -> Self:
        """Return a unit vector in the same direction.

        Raises:
            ZeroLengthVectorError: If this vector has no direction.

        Returns:
            A vector with a length of one.
        """
        length = self.length
        if length == 0.0:
            raise ZeroLengthVectorError("Cannot normalize a zero-length vector.")
        return self.__class__(self.x / length, self.y / length)
