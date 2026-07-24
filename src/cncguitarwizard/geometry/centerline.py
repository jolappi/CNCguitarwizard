"""Centerline construction for guitar geometry."""

from __future__ import annotations

from math import isfinite

from .exceptions import GeometryException
from .primitives import Line2D, Point2D


class Centerline:
    """Create the longitudinal reference axis for an instrument.

    The nut is placed at the origin and positive x extends towards the bridge.
    All dimensions are expressed in millimetres.
    """

    @staticmethod
    def create(scale_length: float) -> Line2D:
        """Create a horizontal centerline from the nut to the bridge.

        Args:
            scale_length: Nut-to-bridge distance in millimetres.

        Raises:
            GeometryException: If ``scale_length`` is not finite and greater
                than zero.

        Returns:
            A line segment beginning at the origin and ending at the scale
            length on the x-axis.
        """
        if not isfinite(scale_length) or scale_length <= 0.0:
            raise GeometryException(
                "Scale length must be a finite positive value."
            )

        return Line2D(
            Point2D(0.0, 0.0),
            Point2D(scale_length, 0.0),
        )
