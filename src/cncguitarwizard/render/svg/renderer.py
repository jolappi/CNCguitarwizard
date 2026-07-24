"""Dependency-free SVG rendering for geometry foundation objects."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeAlias

from ...geometry.fretboard import (
    Fretboard,
    FretboardCrossSection,
    FretboardSideProfile,
    FretLayout,
)
from ...geometry.neck import Centerline, NeckOutline, NeckSideProfile
from ...geometry.primitives import Line2D, Point2D

RenderableGeometry: TypeAlias = (
    Point2D
    | Line2D
    | Centerline
    | Fretboard
    | FretLayout
    | FretboardCrossSection
    | FretboardSideProfile
    | NeckOutline
    | NeckSideProfile
)


@dataclass(frozen=True, slots=True)
class SVGRenderer:
    """Render supported geometry objects as standalone SVG documents.

    Args:
        width: SVG viewport width in pixels.
        height: SVG viewport height in pixels.
        padding: Empty model-space margin around rendered geometry.
    """

    width: float = 800.0
    height: float = 600.0
    padding: float = 10.0

    def __post_init__(self) -> None:
        """Validate viewport and padding dimensions."""
        dimensions = (self.width, self.height)
        if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
            raise ValueError("SVG viewport dimensions must be finite and positive.")
        if not math.isfinite(self.padding) or self.padding < 0.0:
            raise ValueError("SVG padding must be finite and non-negative.")

    def render(self, geometry: RenderableGeometry) -> str:
        """Return a standalone SVG document for one geometry object.

        Args:
            geometry: Geometry object to render.

        Returns:
            A valid SVG document as a string.
        """
        if isinstance(geometry, Point2D):
            element = self._render_point(geometry)
        elif isinstance(geometry, Line2D):
            element = self._render_line(geometry)
        elif isinstance(geometry, Centerline):
            element = self._render_line(geometry.line)
        elif isinstance(geometry, Fretboard):
            element = self._render_fretboard(geometry)
        elif isinstance(geometry, FretLayout):
            element = self._render_fret_layout(geometry)
        elif isinstance(geometry, FretboardSideProfile):
            element = self._render_polygon(
                geometry.boundary,
                "fretboard-side-profile",
            )
        elif isinstance(geometry, FretboardCrossSection):
            element = self._render_polygon(
                geometry.boundary,
                "fretboard-cross-section",
            )
        elif isinstance(geometry, NeckOutline):
            element = self._render_neck_outline(geometry)
        elif isinstance(geometry, NeckSideProfile):
            element = self._render_neck_side_profile(geometry)
        else:
            raise TypeError(f"Unsupported geometry type: {type(geometry).__name__}")

        view_box = self._view_box(geometry)
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self._format_number(self.width)}" '
            f'height="{self._format_number(self.height)}" '
            f'viewBox="{view_box}">\n'
            f"{element}\n"
            "</svg>\n"
        )

    def _view_box(self, geometry: RenderableGeometry) -> str:
        """Return an automatically fitted SVG view box."""
        points = self._geometry_points(geometry)
        minimum_x = min(point.x for point in points) - self.padding
        maximum_x = max(point.x for point in points) + self.padding
        minimum_y = min(point.y for point in points) - self.padding
        maximum_y = max(point.y for point in points) + self.padding

        width = max(maximum_x - minimum_x, 1.0)
        height = max(maximum_y - minimum_y, 1.0)
        return " ".join(
            self._format_number(value)
            for value in (minimum_x, minimum_y, width, height)
        )

    @staticmethod
    def _geometry_points(geometry: RenderableGeometry) -> tuple[Point2D, ...]:
        """Return the points that define the rendered geometry bounds."""
        if isinstance(geometry, Point2D):
            return (geometry,)
        if isinstance(geometry, Line2D):
            return (geometry.start, geometry.end)
        if isinstance(geometry, Centerline):
            return (geometry.line.start, geometry.line.end)
        if isinstance(geometry, Fretboard):
            return tuple(
                point
                for line in geometry.outline
                for point in (line.start, line.end)
            )
        if isinstance(geometry, FretLayout):
            return tuple(
                point
                for line in (*geometry.fretboard.outline, *geometry.slots)
                for point in (line.start, line.end)
            )
        if isinstance(geometry, (FretboardSideProfile, FretboardCrossSection)):
            return geometry.boundary
        if isinstance(geometry, NeckOutline):
            return geometry.boundary
        if isinstance(geometry, NeckSideProfile):
            return geometry.boundary
        raise TypeError(f"Unsupported geometry type: {type(geometry).__name__}")

    @staticmethod
    def _render_point(point: Point2D) -> str:
        """Return the SVG element for a point."""
        return (
            f'<circle cx="{SVGRenderer._format_number(point.x)}" '
            f'cy="{SVGRenderer._format_number(point.y)}" r="1"/>'
        )

    @staticmethod
    def _render_line(line: Line2D) -> str:
        """Return the SVG element for a line segment."""
        return (
            f'<line x1="{SVGRenderer._format_number(line.start.x)}" '
            f'y1="{SVGRenderer._format_number(line.start.y)}" '
            f'x2="{SVGRenderer._format_number(line.end.x)}" '
            f'y2="{SVGRenderer._format_number(line.end.y)}"/>'
        )

    @staticmethod
    def _render_fretboard(fretboard: Fretboard) -> str:
        """Return the SVG polygon element for a fretboard outline."""
        points = (
            fretboard.nut_line.start,
            fretboard.nut_line.end,
            fretboard.bridge_line.end,
            fretboard.bridge_line.start,
        )
        coordinates = " ".join(
            f"{SVGRenderer._format_number(point.x)},"
            f"{SVGRenderer._format_number(point.y)}"
            for point in points
        )
        return f'<polygon points="{coordinates}"/>'

    @staticmethod
    def _render_fret_layout(layout: FretLayout) -> str:
        """Return a grouped fretboard outline and its fret-slot segments."""
        outline = SVGRenderer._render_fretboard(layout.fretboard).replace(
            "<polygon ",
            '<polygon class="fretboard-outline" ',
            1,
        )
        slots = "\n".join(
            SVGRenderer._render_line(slot).replace(
                "<line ",
                '<line class="fret-slot" ',
                1,
            )
            for slot in layout.slots
        )
        return f'<g class="fret-layout">\n{outline}\n{slots}\n</g>'

    @staticmethod
    def _render_neck_outline(outline: NeckOutline) -> str:
        """Return a polygon element for a top-view neck outline."""
        return SVGRenderer._render_polygon(outline.boundary, "neck-outline")

    @staticmethod
    def _render_neck_side_profile(profile: NeckSideProfile) -> str:
        """Return a polygon element for a longitudinal neck profile."""
        return SVGRenderer._render_polygon(
            profile.boundary,
            "neck-side-profile",
        )

    @staticmethod
    def _render_polygon(points: tuple[Point2D, ...], class_name: str) -> str:
        """Return a classed SVG polygon for a sequence of boundary points."""
        coordinates = " ".join(
            f"{SVGRenderer._format_number(point.x)},"
            f"{SVGRenderer._format_number(point.y)}"
            for point in points
        )
        return f'<polygon class="{class_name}" points="{coordinates}"/>'

    @staticmethod
    def _format_number(value: float) -> str:
        """Return a compact, deterministic SVG number."""
        return format(value, ".15g")
