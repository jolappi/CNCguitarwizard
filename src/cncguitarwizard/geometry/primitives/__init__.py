"""Immutable two-dimensional geometry primitives."""

from .bezier import (
    BezierSpan,
    bezier_point,
    closed_catmull_rom_spans,
    flatten_span,
    hermite_spans,
    smooth_curve_spans,
)
from .line2d import Line2D
from .monotone_curve import MonotoneCurve, SmoothCurve
from .nudge_inward import nudge_inward
from .point2d import Point2D
from .point3d import Point3D
from .point_in_polygon import point_in_polygon
from .rounded_polygon import rounded_polygon_points
from .spline import closed_catmull_rom, open_catmull_rom
from .surface_mesh import QuadFace, SurfaceMesh
from .vector2d import Vector2D

__all__ = [
    "BezierSpan",
    "Line2D",
    "MonotoneCurve",
    "SmoothCurve",
    "Point2D",
    "Point3D",
    "QuadFace",
    "SurfaceMesh",
    "Vector2D",
    "bezier_point",
    "closed_catmull_rom_spans",
    "flatten_span",
    "hermite_spans",
    "smooth_curve_spans",
    "closed_catmull_rom",
    "nudge_inward",
    "open_catmull_rom",
    "point_in_polygon",
    "rounded_polygon_points",
]
