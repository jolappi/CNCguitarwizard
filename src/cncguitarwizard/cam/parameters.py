"""Tool, feed, and fixturing parameters for the 2.5D toolpath planner."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .exceptions import ToolpathError


@dataclass(frozen=True, slots=True)
class MachiningParameters:
    """One end mill and the feeds, depths, and fixturing it is run with.

    Every distance is in millimetres, every feed in millimetres per
    minute. The defaults describe the TwoTrees H40 / GRBL setup from the
    Prototype001 manufacturing specification: a single 6 mm end mill,
    at most 3 mm axial step-down, a 0.30 mm wall finishing allowance,
    and two 6 mm index pins on the centerline for two-sided machining.

    Args:
        tool_diameter: Cutting diameter of the end mill.
        tool_tip: ``"flat"`` for a square end mill, ``"ball"`` for a ball
            nose of the same diameter (only surfacing cares).
        spindle_speed: Spindle speed in rpm, emitted with ``M3``.
        feed_rate: Cutting feed for XY moves.
        plunge_rate: Feed for straight plunges and helical descents.
        rapid_rate: Nominal rapid speed, used only for time estimates.
        step_down: Maximum axial depth of cut per pass.
        step_over: Radial engagement between raster rows, as a fraction
            of the tool diameter.
        finishing_allowance: Wall stock left by roughing and removed by
            the finishing contour.
        safe_height: Z height for rapid traverses above the stock top.
        through_overshoot: Extra depth below a through feature so the
            cutter clears the far face.
        tab_count: Holding tabs left on the final profile passes.
        tab_length: Length of each tab along the profile.
        tab_height: Height of each tab above the profile floor.
        index_pin_diameter: Diameter of the two-sided-machining dowels.
        index_pin_positions: Dowel centres in the model frame, or ``None``
            to place them automatically on the centerline in the blank's
            waste — in the horn gap ahead of the neck pocket and in the
            tail notch behind the body — so the holes never end up in
            the finished part. The first one is the G-code work origin
            (X = 0, Y = 0).
        index_pin_wall: Wood left between a dowel hole and the nearest
            cut (outline profile or cavity), beyond the tool diameter.
        stock_margin: Waste around the body outline on every side; the
            blank is the outline's bounding box grown by this much.
        stock_edge_margin: Minimum distance from a dowel hole to the
            blank's edge.
        profile_overlap: How far each side's outline profile cuts past
            the mid-plane so the two half-depth cuts meet.
        raster_link_spacing: Sample spacing when checking whether a link
            between raster rows can stay in the cut.

    Raises:
        ToolpathError: If any value is non-finite or out of its range.
    """

    tool_diameter: float = 6.0
    tool_tip: str = "flat"
    spindle_speed: float = 10000.0
    feed_rate: float = 1000.0
    plunge_rate: float = 300.0
    rapid_rate: float = 3000.0
    step_down: float = 3.0
    step_over: float = 0.4
    finishing_allowance: float = 0.3
    safe_height: float = 5.0
    through_overshoot: float = 0.5
    tab_count: int = 6
    tab_length: float = 8.0
    tab_height: float = 4.0
    index_pin_diameter: float = 6.0
    index_pin_positions: tuple[tuple[float, float], ...] | None = None
    index_pin_wall: float = 3.0
    stock_margin: float = 15.0
    stock_edge_margin: float = 8.0
    profile_overlap: float = 0.5
    raster_link_spacing: float = 1.0

    def __post_init__(self) -> None:
        """Reject parameters the planner cannot cut safely with."""
        positive = {
            "tool_diameter": self.tool_diameter,
            "spindle_speed": self.spindle_speed,
            "feed_rate": self.feed_rate,
            "plunge_rate": self.plunge_rate,
            "rapid_rate": self.rapid_rate,
            "step_down": self.step_down,
            "safe_height": self.safe_height,
            "tab_length": self.tab_length,
            "tab_height": self.tab_height,
            "index_pin_diameter": self.index_pin_diameter,
            "stock_margin": self.stock_margin,
            "stock_edge_margin": self.stock_edge_margin,
            "raster_link_spacing": self.raster_link_spacing,
        }
        for name, value in positive.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ToolpathError(f"{name} must be finite and positive.")
        non_negative = {
            "finishing_allowance": self.finishing_allowance,
            "through_overshoot": self.through_overshoot,
            "profile_overlap": self.profile_overlap,
            "index_pin_wall": self.index_pin_wall,
        }
        for name, value in non_negative.items():
            if not math.isfinite(value) or value < 0.0:
                raise ToolpathError(f"{name} must be finite and non-negative.")
        if self.tool_tip not in ("flat", "ball"):
            raise ToolpathError('tool_tip must be "flat" or "ball".')
        if not 0.0 < self.step_over <= 1.0:
            raise ToolpathError("step_over must lie in (0, 1].")
        if self.tab_count < 0:
            raise ToolpathError("tab_count must not be negative.")
        if self.index_pin_positions is not None:
            if len(self.index_pin_positions) != 2:
                raise ToolpathError("Exactly two index pins are required.")
            for x, y in self.index_pin_positions:
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ToolpathError("Index pin positions must be finite.")

    @property
    def tool_radius(self) -> float:
        """Return half the tool diameter."""
        return self.tool_diameter / 2.0

    @property
    def raster_spacing(self) -> float:
        """Return the distance between neighbouring raster rows."""
        return self.tool_diameter * self.step_over
