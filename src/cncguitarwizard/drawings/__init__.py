"""Outlines drawn in another program: SVG and DXF templates out, drawings back in."""

from .dxf_reader import is_dxf, read_dxf_drawing
from .exceptions import DrawingError
from .fitting import BodyFit, HeadstockFit, fit_closed_spline, fit_headstock
from .svg_reader import SvgShape, read_svg_shapes
from .template import (
    ReadOutline,
    ReferenceShape,
    TemplateFrame,
    read_template_outline,
    read_template_pattern,
    template_dxf,
    template_svg,
)

__all__ = [
    "BodyFit",
    "DrawingError",
    "HeadstockFit",
    "ReadOutline",
    "ReferenceShape",
    "SvgShape",
    "TemplateFrame",
    "fit_closed_spline",
    "fit_headstock",
    "is_dxf",
    "read_dxf_drawing",
    "read_svg_shapes",
    "read_template_outline",
    "read_template_pattern",
    "template_dxf",
    "template_svg",
]
