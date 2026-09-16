"""Plan the two-sided machining of the Prototype001 neck.

The neck blank is planed to ``blank_thickness`` with its top face the
fretboard glue plane (model ``Z = 0``). Two dowels in the waste beyond
the headstock tip and beyond the heel, on the centerline, locate it in
both setups:

* **top** — truss-rod channel, the 8-degree headstock face as a Z-limited
  raster with the flat end mill, and shallow centre marks for the tuner
  holes (which must be drilled perpendicular to the angled face, so they
  are left to a drill press with an 8-degree wedge);
* **back** (flipped about the centerline) — Z-limited roughing of the
  neck back and headstock back with the flat end mill, ball-nose
  finishing, and finally the plan outline cut through the remaining
  skin with holding tabs.

Every surface is a height function in the machine frame; the drop-cutter
offset grids in ``surfacing`` keep the tool from gouging.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..geometry.primitives import Point2D, point_in_polygon
from .exceptions import ToolpathError
from .fixturing import StockBounds, resolve_index_pins
from .gcode import Setup
from .operations import drill, pocket, profile
from .parameters import MachiningParameters
from .planar import polygon_bounds
from .surfacing import (
    build_offset_grid,
    interpolate_rows,
    offset_sampled_surface,
    raster_finish,
    raster_rough,
    sample_surface,
)

if TYPE_CHECKING:
    from ..presets import Prototype001Geometry


def _flat_tool() -> MachiningParameters:
    return MachiningParameters(stock_margin=35.0)


def _ball_tool() -> MachiningParameters:
    return MachiningParameters(tool_tip="ball", stock_margin=35.0)


@dataclass(frozen=True, slots=True)
class NeckMachiningParameters:
    """Tools, blank and surfacing settings for the neck.

    Args:
        flat: The 6 mm flat end mill used for the truss-rod channel,
            headstock face, tuner marks, roughing, and the outline.
        ball: The ball nose of the same diameter used to finish the back.
        blank_thickness: Planed thickness of the neck blank; must exceed
            the headstock's lowest point below the glue plane.
        skin: Wood left under the part (at the glue-plane side) outside
            the outline and along the back's edges, so the neck stays in
            its waste frame until the tabbed outline cut.
        roughing_step_over: Raster step for roughing, as a fraction of
            the tool diameter.
        finishing_step_over: Raster step for the ball finish, in
            millimetres (scallop height is step² / 8r).
        face_finish_step_over: Raster step for the flat-tool pass that
            finishes the headstock face plane, in millimetres.
        grid_spacing_x: Drop-cutter grid spacing along the neck; the
            finishing raster samples the surface at this spacing too.
        grid_spacing_y: Drop-cutter grid spacing across the neck. Keep
            ``finishing_step_over`` a whole multiple of it so every pass
            runs exactly on grid rows and no interpolation is involved.
        tuner_mark_depth: Depth of the centre marks left for the tuner
            holes on the headstock face.
    """

    flat: MachiningParameters = field(default_factory=_flat_tool)
    ball: MachiningParameters = field(default_factory=_ball_tool)
    blank_thickness: float = 40.0
    skin: float = 2.0
    roughing_step_over: float = 0.6
    finishing_step_over: float = 0.75
    face_finish_step_over: float = 2.0
    grid_spacing_x: float = 1.0
    grid_spacing_y: float = 0.25
    tuner_mark_depth: float = 0.5

    def __post_init__(self) -> None:
        for name, value in (
            ("blank_thickness", self.blank_thickness),
            ("skin", self.skin),
            ("finishing_step_over", self.finishing_step_over),
            ("face_finish_step_over", self.face_finish_step_over),
            ("grid_spacing_x", self.grid_spacing_x),
            ("grid_spacing_y", self.grid_spacing_y),
            ("tuner_mark_depth", self.tuner_mark_depth),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ToolpathError(f"{name} must be finite and positive.")
        if not 0.0 < self.roughing_step_over <= 1.0:
            raise ToolpathError("roughing_step_over must lie in (0, 1].")
        if self.ball.tool_tip != "ball":
            raise ToolpathError("The finishing tool must be a ball nose.")


@dataclass(frozen=True, slots=True)
class NeckMachiningPlan:
    """The setups that machine one neck, in running order."""

    index_pins: Setup
    top: Setup
    back_rough: Setup
    back_finish: Setup
    back_outline: Setup
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float
    origin_y: float
    index_pin_positions: tuple[tuple[float, float], ...]
    preview_outlines: tuple[tuple[Point2D, ...], ...]

    @property
    def setups(self) -> tuple[Setup, ...]:
        return (
            self.index_pins,
            self.top,
            self.back_rough,
            self.back_finish,
            self.back_outline,
        )


def neck_plan_polygon(geometry: Prototype001Geometry) -> tuple[Point2D, ...]:
    """Return the whole neck's plan outline: headstock, neck, and heel."""
    neck = geometry.neck_outline.boundary
    headstock = geometry.headstock.plan.boundary
    raw = [neck[1], *headstock[2:], neck[0], *reversed(neck[2:])]
    points: list[Point2D] = []
    for point in raw:
        if points and math.hypot(point.x - points[-1].x, point.y - points[-1].y) < 1e-6:
            continue
        points.append(point)
    if math.hypot(points[0].x - points[-1].x, points[0].y - points[-1].y) < 1e-6:
        points.pop()
    return tuple(points)


def plan_neck_machining(
    geometry: Prototype001Geometry,
    parameters: NeckMachiningParameters,
) -> NeckMachiningPlan:
    """Return toolpaths for every machinable feature of the neck.

    Raises:
        ToolpathError: If the blank is too thin for the headstock, or an
            index pin cannot be placed.
    """
    flat = parameters.flat
    ball = parameters.ball
    thickness = parameters.blank_thickness
    headstock = geometry.headstock
    angle = math.radians(headstock.angle.angle_degrees)
    tangent = math.tan(angle)
    back_plane_offset = headstock.thickness / math.cos(angle)
    tip_x = -headstock.plan.length
    lowest = tip_x * tangent - back_plane_offset
    if thickness < -lowest + parameters.skin:
        raise ToolpathError(
            f"Neck blank must be at least {-lowest + parameters.skin:.1f} mm "
            f"thick for this headstock; {thickness} mm given."
        )

    outline = neck_plan_polygon(geometry)
    min_x, min_y, max_x, max_y = polygon_bounds(outline)
    radius = max(flat.tool_radius, ball.tool_radius)
    sweep = (
        Point2D(min_x - radius, min_y - radius),
        Point2D(max_x + radius, min_y - radius),
        Point2D(max_x + radius, max_y + radius),
        Point2D(min_x - radius, max_y + radius),
    )
    stock = StockBounds.around(outline, flat.stock_margin)
    pins = resolve_index_pins(outline, [sweep], flat, stock)
    origin_x, origin_y = pins[0]
    top_frame = _Frame(origin_x, origin_y, mirror_y=False)
    back_frame = _Frame(origin_x, origin_y, mirror_y=True)
    reference_points = tuple((x - origin_x, y - origin_y) for x, y in pins[1:])

    index_pins = Setup(
        "Neck_index_pins",
        "Neck index pins - drill both dowel holes through the blank",
        tuple(
            drill(
                f"Index pin {index}",
                top_frame.point(Point2D(x, y)),
                flat.index_pin_diameter,
                thickness + flat.through_overshoot,
                flat,
            )
            for index, (x, y) in enumerate(pins, start=1)
        ),
        (
            "Clamp the planed blank glue-face up on a spoilboard.",
            "Set X/Y zero at the index pin 1 position and Z zero on the blank top.",
            "Both dowels sit in the waste on the centerline, beyond the "
            "headstock tip and beyond the heel.",
            f"Blank: at least {stock.length:.0f} x {stock.width:.0f} x "
            f"{thickness:g} mm.",
        ),
        reference_points,
        flat,
    )

    # ---- top face: truss rod, headstock face, tuner marks -----------------
    shelf = geometry.neck_surface.nut_shelf_length

    def face_depth(model_x: float) -> float:
        return 0.0 if model_x >= -shelf else model_x * tangent

    truss = geometry.truss_rod_channel
    top_paths = [
        pocket(
            "Truss-rod channel",
            top_frame.polygon(truss.top_boundary),
            truss.depth,
            flat,
        )
    ]
    face_x = (tip_x - radius, -shelf)
    face_y = (min_y - radius, max_y + radius)
    face_grid = build_offset_grid(
        lambda xm, ym: face_depth(top_frame.model_point(Point2D(xm, ym)).x),
        top_frame.x_range(face_x),
        top_frame.y_range(face_y),
        flat,
        spacing_x=parameters.grid_spacing_x,
        spacing_y=parameters.grid_spacing_y,
    )
    top_paths.append(
        raster_rough(
            "Headstock face roughing",
            face_grid,
            flat,
            x_range=top_frame.x_range(face_x),
            y_range=top_frame.y_range(face_y),
            step_over=flat.tool_diameter * parameters.roughing_step_over,
        )
    )
    top_paths.append(
        raster_finish(
            "Headstock face finishing",
            face_grid,
            flat,
            x_range=top_frame.x_range(face_x),
            y_range=top_frame.y_range(face_y),
            step_over=parameters.face_finish_step_over,
        )
    )
    for hole in geometry.tuner_layout.holes:
        surface_depth = -face_depth(hole.center.x)
        top_paths.append(
            drill(
                f"Tuner {hole.side} {hole.index} centre mark",
                top_frame.point(hole.center),
                flat.tool_diameter,
                surface_depth + parameters.tuner_mark_depth,
                flat,
                start_depth=surface_depth,
            )
        )
    top = Setup(
        "Neck_top",
        "Neck glue face - truss-rod channel, headstock face, tuner centre marks",
        tuple(top_paths),
        (
            "Blank on the two index pins, glue face up, same work zero.",
            f"The headstock face is milled to {headstock.angle.angle_degrees:g} "
            f"degrees; the flat nut shelf keeps {shelf:g} mm before the nut.",
            "Tuner holes get 0.5 mm centre marks only: drill them perpendicular "
            "to the angled face on a drill press with a wedge.",
        ),
        reference_points,
        flat,
    )

    # ---- back: roughing, ball finishing, outline ---------------------------
    back_surface = _BackSurface(geometry, thickness, parameters.skin, back_frame)
    carve_x = back_frame.x_range((min_x - radius, max_x + radius))
    carve_y = back_frame.y_range((min_y - radius, max_y + radius))
    sampled_back = sample_surface(
        back_surface.machine_z,
        carve_x,
        carve_y,
        spacing_x=parameters.grid_spacing_x,
        spacing_y=parameters.grid_spacing_y,
    )
    rough_grid = offset_sampled_surface(sampled_back, flat)
    back_rough = Setup(
        "Neck_back_rough",
        "Neck back - Z-limited roughing with the flat end mill",
        (
            raster_rough(
                "Neck back roughing",
                rough_grid,
                flat,
                x_range=carve_x,
                y_range=carve_y,
                step_over=flat.tool_diameter * parameters.roughing_step_over,
            ),
        ),
        (
            "Flip the blank about the neck centerline onto the same two index pins.",
            "Keep X/Y zero at index pin 1; set Z zero on the (new) blank top.",
            f"Roughing stops {parameters.skin:g} mm short of the glue plane "
            "everywhere, so the neck stays attached to its waste frame.",
        ),
        reference_points,
        flat,
    )
    finish_grid = offset_sampled_surface(sampled_back, ball)
    back_finish = Setup(
        "Neck_back_finish",
        "Neck back - ball-nose finishing",
        (
            raster_finish(
                "Neck back finishing",
                finish_grid,
                ball,
                x_range=carve_x,
                y_range=carve_y,
                step_over=parameters.finishing_step_over,
            ),
        ),
        (
            "Same fixture and X/Y zero as Neck_back_rough; change to the ball "
            "nose and re-touch Z on the blank top.",
            f"Scallop height about "
            f"{parameters.finishing_step_over ** 2 / (8.0 * ball.tool_radius):.3f} mm.",
        ),
        reference_points,
        ball,
    )
    back_outline = Setup(
        "Neck_back_outline",
        "Neck back - plan outline through the skin, with tabs",
        (
            profile(
                "Neck outline with tabs",
                back_frame.polygon(outline),
                thickness + flat.through_overshoot,
                flat,
                start_depth=thickness - parameters.skin - 0.5,
                with_tabs=True,
            ),
        ),
        (
            "Same fixture and X/Y zero; back to the flat end mill, re-touch Z.",
            f"Cuts the {parameters.skin:g} mm skin around the outline, leaving "
            f"{flat.tab_count} tabs; saw and sand them off, then fair the "
            "back edges into the sides by hand.",
        ),
        reference_points,
        flat,
    )

    top_outline = top_frame.polygon(outline)
    back_outline_polygon = back_frame.polygon(outline)
    return NeckMachiningPlan(
        index_pins,
        top,
        back_rough,
        back_finish,
        back_outline,
        stock_length=stock.length,
        stock_width=stock.width,
        stock_thickness=thickness,
        origin_x=origin_x,
        origin_y=origin_y,
        index_pin_positions=pins,
        preview_outlines=(
            top_outline,
            top_outline,
            back_outline_polygon,
            back_outline_polygon,
            back_outline_polygon,
        ),
    )


@dataclass(frozen=True, slots=True)
class _Frame:
    """Map model coordinates into one setup's machine frame and back."""

    origin_x: float
    origin_y: float
    mirror_y: bool

    def point(self, point: Point2D) -> Point2D:
        if self.mirror_y:
            return Point2D(point.x - self.origin_x, -point.y + self.origin_y)
        return Point2D(point.x - self.origin_x, point.y - self.origin_y)

    def model_point(self, point: Point2D) -> Point2D:
        if self.mirror_y:
            return Point2D(point.x + self.origin_x, self.origin_y - point.y)
        return Point2D(point.x + self.origin_x, point.y + self.origin_y)

    def polygon(self, points: Sequence[Point2D]) -> tuple[Point2D, ...]:
        return tuple(self.point(point) for point in points)

    def x_range(self, model_range: tuple[float, float]) -> tuple[float, float]:
        return (model_range[0] - self.origin_x, model_range[1] - self.origin_x)

    def y_range(self, model_range: tuple[float, float]) -> tuple[float, float]:
        low = self.point(Point2D(0.0, model_range[0])).y
        high = self.point(Point2D(0.0, model_range[1])).y
        return (min(low, high), max(low, high))


class _BackSurface:
    """The neck's back as a machine-frame height function for the flipped setup.

    Inside the neck it is the lofted back-surface mesh; over the
    headstock it is the angled back plane; wherever both exist the
    deeper wins. Outside the plan outline, and anywhere the true surface
    comes closer than ``skin`` to the glue plane, the height is clamped
    so a skin of wood remains.
    """

    def __init__(
        self,
        geometry: Prototype001Geometry,
        thickness: float,
        skin: float,
        frame: _Frame,
    ) -> None:
        self._thickness = thickness
        self._skin = skin
        self._frame = frame
        rows = geometry.neck_surface.mesh.rows
        self._stations = [row[0].x for row in rows]
        self._rows = [
            ([point.y for point in row], [point.z for point in row]) for row in rows
        ]
        headstock = geometry.headstock
        angle = math.radians(headstock.angle.angle_degrees)
        self._tangent = math.tan(angle)
        self._plane_offset = headstock.thickness / math.cos(angle)
        self._headstock_back = tuple(
            Point2D(point.x, point.y) for point in headstock.bottom_boundary
        )

    def model_z(self, x: float, y: float) -> float:
        """Return the part's back height in the model frame (glue plane = 0)."""
        candidates = []
        mesh_z = interpolate_rows(self._stations, self._rows, x, y)
        if mesh_z is not None:
            candidates.append(mesh_z)
        if point_in_polygon(Point2D(x, y), self._headstock_back):
            candidates.append(x * self._tangent - self._plane_offset)
        if not candidates:
            return -self._skin
        return min(min(candidates), -self._skin)

    def machine_z(self, xm: float, ym: float) -> float:
        """Return the back height in the flipped machine frame."""
        model = self._frame.model_point(Point2D(xm, ym))
        return -(self._thickness + self.model_z(model.x, model.y))
