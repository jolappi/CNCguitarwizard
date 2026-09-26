"""Parametric solid-body geometry."""

from .body_solid import BodySolid
from .bridges import (
    BRIDGE_KINDS,
    BRIDGE_LABELS,
    BridgeHardware,
    BridgeSpec,
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
    bridge_spec_from_dict,
)
from .covers import CoverPlate, cover_screw_points
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
    "BRIDGE_KINDS",
    "BRIDGE_LABELS",
    "BodyOutline",
    "BodySolid",
    "BridgeHardware",
    "BridgeMounting",
    "BridgeSpec",
    "Cavity",
    "CoverPlate",
    "CircularCavity",
    "DrilledHole",
    "FloydRoseSpec",
    "HardtailSpec",
    "JackHole",
    "KahlerBridgeSpec",
    "RearCavity",
    "RectangularCavity",
    "TracedCavity",
    "TracedOutline",
    "TuneOMaticSpec",
    "bridge_spec_from_dict",
    "cover_screw_points",
]
