"""Immutable three-dimensional point primitive."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point3D:
    """Represent a point in three-dimensional model space.

    Args:
        x: Longitudinal coordinate in millimetres.
        y: Lateral coordinate in millimetres.
        z: Vertical coordinate in millimetres.
    """

    x: float
    y: float
    z: float
