"""Dependency-free 2.5D/3D CAM: toolpaths and GRBL G-code from the geometry."""

from .body import BodyMachiningPlan, plan_body_machining
from .combined import combined_setup, combined_setups, setup_runs
from .covers import (
    CoverMachiningPlan,
    cover_setup_name,
    cover_tool,
    plan_cover_machining,
)
from .exceptions import CAMError, ToolpathError
from .feature import plan_feature_machining
from .fixturing import StockBounds, automatic_index_pins, pin_fits
from .fretboard import (
    FretboardMachiningParameters,
    FretboardMachiningPlan,
    fretboard_outline_polygon,
    plan_fretboard_machining,
)
from .gcode import GCodeWriter, GRBLWriter, Setup, program_stem
from .inlays import InlayMachiningPlan, inlay_fit_outline, plan_inlay_machining
from .machine import MachineFit, fitted_to_machine, program_span
from .neck import (
    HeadstockBlock,
    NeckMachiningParameters,
    NeckMachiningPlan,
    neck_plan_polygon,
    plan_neck_machining,
)
from .nut_jig import NutJigMachiningPlan, nut_jig_tool, plan_nut_jig_machining
from .operations import depth_levels, drill, pocket, profile
from .parameters import POST_PROCESSOR_LABELS, MachiningParameters
from .planar import clear_intervals, disc_fits, offset_polygon
from .preview import render_setup_svg
from .surfacing import (
    OffsetGrid,
    SampledSurface,
    build_offset_grid,
    offset_sampled_surface,
    raster_finish,
    raster_rough,
    sample_surface,
)
from .toolpath import Move, PathBuilder, Toolpath

__all__ = [
    "BodyMachiningPlan",
    "CAMError",
    "CoverMachiningPlan",
    "FretboardMachiningParameters",
    "FretboardMachiningPlan",
    "GCodeWriter",
    "HeadstockBlock",
    "InlayMachiningPlan",
    "MachineFit",
    "GRBLWriter",
    "POST_PROCESSOR_LABELS",
    "MachiningParameters",
    "Move",
    "NeckMachiningParameters",
    "NeckMachiningPlan",
    "NutJigMachiningPlan",
    "OffsetGrid",
    "PathBuilder",
    "SampledSurface",
    "Setup",
    "StockBounds",
    "Toolpath",
    "ToolpathError",
    "automatic_index_pins",
    "build_offset_grid",
    "clear_intervals",
    "combined_setup",
    "combined_setups",
    "cover_setup_name",
    "cover_tool",
    "depth_levels",
    "disc_fits",
    "drill",
    "fitted_to_machine",
    "fretboard_outline_polygon",
    "inlay_fit_outline",
    "neck_plan_polygon",
    "nut_jig_tool",
    "offset_polygon",
    "offset_sampled_surface",
    "plan_cover_machining",
    "plan_feature_machining",
    "pin_fits",
    "plan_body_machining",
    "plan_fretboard_machining",
    "plan_inlay_machining",
    "plan_neck_machining",
    "plan_nut_jig_machining",
    "pocket",
    "profile",
    "program_span",
    "program_stem",
    "raster_finish",
    "raster_rough",
    "render_setup_svg",
    "sample_surface",
    "setup_runs",
]
