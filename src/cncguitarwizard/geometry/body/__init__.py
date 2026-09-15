"""Parametric solid-body geometry."""

from .body_solid import BodySolid
from .hardware import (
    BridgeMounting,
    Cavity,
    CircularCavity,
    DrilledHole,
    JackHole,
    RearCavity,
    RectangularCavity,
    TracedCavity,
)
from .outline import BodyOutline, TracedOutline

__all__ = [
    "BodyOutline",
    "BodySolid",
    "BridgeMounting",
    "Cavity",
    "CircularCavity",
    "DrilledHole",
    "JackHole",
    "RearCavity",
    "RectangularCavity",
    "TracedCavity",
    "TracedOutline",
]
