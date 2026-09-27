"""Parametric solid-body geometry."""

from .body_solid import BodySolid, outlines_overlap
from .bridges import (
    BRIDGE_KINDS,
    BRIDGE_LABELS,
    BRIDGE_MAX_STRINGS,
    BridgeHardware,
    BridgeSpec,
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
    bridge_spec_from_dict,
    turned_hardware,
)
from .covers import CoverPlate, cover_screw_points
from .edges import ContourCut, EdgeProfile
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
    "BRIDGE_MAX_STRINGS",
    "BodyOutline",
    "BodySolid",
    "outlines_overlap",
    "BridgeHardware",
    "BridgeMounting",
    "BridgeSpec",
    "Cavity",
    "ContourCut",
    "CoverPlate",
    "CircularCavity",
    "DrilledHole",
    "EdgeProfile",
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
    "turned_hardware",
]
