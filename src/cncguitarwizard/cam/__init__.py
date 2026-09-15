"""Dependency-free 2.5D CAM: toolpaths and GRBL G-code from the geometry."""

from .body import BodyMachiningPlan, plan_body_machining
from .exceptions import CAMError, ToolpathError
from .gcode import GRBLWriter, Setup
from .operations import depth_levels, drill, pocket, profile
from .parameters import MachiningParameters
from .planar import clear_intervals, disc_fits, offset_polygon
from .preview import render_setup_svg
from .toolpath import Move, PathBuilder, Toolpath

__all__ = [
    "BodyMachiningPlan",
    "CAMError",
    "GRBLWriter",
    "MachiningParameters",
    "Move",
    "PathBuilder",
    "Setup",
    "Toolpath",
    "ToolpathError",
    "clear_intervals",
    "depth_levels",
    "disc_fits",
    "drill",
    "offset_polygon",
    "plan_body_machining",
    "pocket",
    "profile",
    "render_setup_svg",
]
