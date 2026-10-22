"""Geometry models specific to guitar neck construction."""

from .back_surface import NeckBackSurface
from .centerline import Centerline
from .headstock import (
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
    Side,
    TunerHole,
    TunerLayout,
)
from .locking_nut import LOCKING_NUT_SPECS, LockingNut, LockingNutSpec
from .nut_jig import NutJigSlot, NutSlotJig
from .outline import NeckOutline
from .reinforcement import CarbonRods
from .side_profile import (
    NeckBackCrossSection,
    NeckProfileStation,
    NeckProfileStations,
    NeckSideProfile,
)
from .truss_rod import TrussRodChannel
from .vintage_rod import VintageTrussRod
from .volute import Volute, default_volute_lines, drawn_volute_line, side_share

__all__ = [
    "CarbonRods",
    "Centerline",
    "HeadstockAngleReference",
    "HeadstockPlan",
    "HeadstockSolid",
    "LOCKING_NUT_SPECS",
    "LockingNut",
    "LockingNutSpec",
    "NeckOutline",
    "NeckBackCrossSection",
    "NeckBackSurface",
    "NeckProfileStation",
    "NeckProfileStations",
    "NeckSideProfile",
    "NutJigSlot",
    "NutSlotJig",
    "Side",
    "TunerHole",
    "TunerLayout",
    "TrussRodChannel",
    "VintageTrussRod",
    "Volute",
    "default_volute_lines",
    "drawn_volute_line",
    "side_share",
]
