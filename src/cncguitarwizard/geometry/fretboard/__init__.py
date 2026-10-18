"""Fretboard outline geometry."""

from .fret_layout import FretLayout, shortened
from .fretboard import Fretboard
from .inlay_layout import InlayLayout, InlayMarker, InlayStyle
from .profiles import FretboardCrossSection, FretboardSideProfile
from .scallops import FretboardScallops
from .skew import FretSkew
from .surface import FretboardSurface

__all__ = [
    "Fretboard",
    "FretboardCrossSection",
    "FretboardScallops",
    "FretboardSideProfile",
    "FretboardSurface",
    "FretLayout",
    "FretSkew",
    "InlayLayout",
    "InlayMarker",
    "InlayStyle",
    "shortened",
]
