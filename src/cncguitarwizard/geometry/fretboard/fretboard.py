"""Fretboard outline construction from a centerline and widths."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..neck import Centerline
from ..primitives import Line2D, Point2D, Vector2D


@dataclass(frozen=True, slots=True)
class Fretboard:
    """Represent the tapered outline of a fretboard.

    Args:
        scale_length: Nut-to-bridge distance in millimetres.
        nut_width: Width of the fretboard at the nut in millimetres.
        bridge_width: Width of the fretboard at the bridge in millimetres.
        centerline: Reference axis that determines the fretboard orientation.
    """

    scale_length: float
    nut_width: float
    bridge_width: float
    centerline: Centerline
    left_edge: Line2D = field(init=False)
    right_edge: Line2D = field(init=False)
    nut_line: Line2D = field(init=False)
    bridge_line: Line2D = field(init=False)
    outline: tuple[Line2D, Line2D, Line2D, Line2D] = field(init=False)

    def __post_init__(self) -> None:
        """Construct the four boundary lines from the centerline."""
        center_start = self.centerline.line.start
        center_end = self.centerline.line.end
        center_direction = Vector2D(
            center_end.x - center_start.x,
            center_end.y - center_start.y,
        ).normalized()
        left_direction = center_direction.perpendicular()
        bridge_center = Point2D(
            center_start.x + center_direction.x * self.scale_length,
            center_start.y + center_direction.y * self.scale_length,
        )

        nut_left = Point2D(
            center_start.x + left_direction.x * self.nut_width / 2.0,
            center_start.y + left_direction.y * self.nut_width / 2.0,
        )
        nut_right = Point2D(
            center_start.x - left_direction.x * self.nut_width / 2.0,
            center_start.y - left_direction.y * self.nut_width / 2.0,
        )
        bridge_left = Point2D(
            bridge_center.x + left_direction.x * self.bridge_width / 2.0,
            bridge_center.y + left_direction.y * self.bridge_width / 2.0,
        )
        bridge_right = Point2D(
            bridge_center.x - left_direction.x * self.bridge_width / 2.0,
            bridge_center.y - left_direction.y * self.bridge_width / 2.0,
        )

        nut_line = Line2D(nut_left, nut_right)
        bridge_line = Line2D(bridge_left, bridge_right)
        left_edge = Line2D(nut_left, bridge_left)
        right_edge = Line2D(nut_right, bridge_right)

        object.__setattr__(self, "left_edge", left_edge)
        object.__setattr__(self, "right_edge", right_edge)
        object.__setattr__(self, "nut_line", nut_line)
        object.__setattr__(self, "bridge_line", bridge_line)
        object.__setattr__(
            self,
            "outline",
            (nut_line, right_edge, bridge_line, left_edge),
        )
