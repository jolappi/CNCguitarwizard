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
    HeadlessBridgeSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
    bridge_spec_from_dict,
    mirrored_hardware,
    turned_hardware,
)
from .carve import CarvedTop, plateau_round
from .covers import CoverPlate, cover_screw_points
from .edges import ContourCut, EdgeProfile
from .engraving import Engraving
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
from .neck_through import (
    BodyPart,
    NeckThrough,
    body_part,
    neck_through,
    split_by_line,
)
from .outline import BodyOutline, TracedOutline

__all__ = [
    "CarvedTop",
    "plateau_round",
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
    "Engraving",
    "FloydRoseSpec",
    "HardtailSpec",
    "HeadlessBridgeSpec",
    "JackHole",
    "KahlerBridgeSpec",
    "RearCavity",
    "RectangularCavity",
    "TracedCavity",
    "TracedOutline",
    "TuneOMaticSpec",
    "bridge_spec_from_dict",
    "cover_screw_points",
    "mirrored_hardware",
    "turned_hardware",
    "BodyPart",
    "body_part",
    "NeckThrough",
    "neck_through",
    "split_by_line",
]
