"""DXF plan outlines of the Prototype001 instrument and its cover plates.

``render_plan_dxf`` draws the whole instrument as the model lays it out
(millimetres, X from the nut toward the tail, Y across the neck): the
body, neck, headstock and fretboard outlines, the nut, the fret slots,
the inlays and tuner holes, every cavity, hole and wire hole of the body,
the top's carve, steps and contours, the engraving, the cover plates and
a bolt-on neck's plate on the back, each kind on a layer of its own (the
holes drilled sideways by hand, a tremolo claw's screws, on
``SIDE_HOLES``). ``render_covers_dxf`` lays the sheet
plates (cavity covers, control plates, the pickguard, the truss-rod cover)
out side by side for cutting, each with its holes and slots and a label.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ...geometry.body import CoverPlate
from ...geometry.primitives import Point2D
from ..svg.plan_view import _fretboard_polygon, _nut_polygon
from .document import DxfDocument

if TYPE_CHECKING:
    from ...presets import Prototype001Geometry

COVER_GAP = 10.0
"""Space left between the plates laid out for cutting, in mm."""

LABEL_HEIGHT = 4.0
"""The plates' labels' height, in mm."""


def render_plan_dxf(geometry: Prototype001Geometry) -> str:
    """Return the instrument's plan outlines as an R12 DXF, a layer a kind."""
    dxf = DxfDocument()
    body = geometry.body
    outline = dxf.layer("BODY_OUTLINE", 7)
    dxf.polyline(body.outline.points, outline)
    if geometry.neck_through is not None and not geometry.neck_through.one_piece:
        dxf.polyline(
            geometry.neck_through.block.outline, dxf.layer("NECK_THROUGH_BLOCK", 7)
        )
    dxf.polyline(geometry.neck_outline.boundary, dxf.layer("NECK_OUTLINE", 7))
    dxf.polyline(geometry.headstock.plan.boundary, dxf.layer("HEADSTOCK_OUTLINE", 7))
    dxf.polyline(_fretboard_polygon(geometry), dxf.layer("FRETBOARD_OUTLINE", 8))
    dxf.polyline(_nut_polygon(geometry), dxf.layer("NUT", 9))
    slots = dxf.layer("FRET_SLOTS", 2)
    zero = geometry.fret_layout.zero_fret_slot
    for slot in (*((zero,) if zero is not None else ()), *geometry.fret_layout.slots):
        dxf.line(slot.start, slot.end, slots)
    inlays = dxf.layer("INLAYS", 6)
    for marker in geometry.inlay_layout.markers:
        dxf.polyline(marker.outline, inlays)
    tuners = dxf.layer("TUNER_HOLES", 3)
    for tuner in geometry.tuner_layout.holes:
        dxf.circle(tuner.center, tuner.diameter / 2.0, tuners)
    truss = geometry.truss_rod_channel
    if truss.adjustment_side == "nut" and truss.adjuster_boundary:
        dxf.polyline(truss.adjuster_boundary, dxf.layer("TRUSS_ROD_ACCESS", 1))
    if geometry.carbon_rods is not None:
        rods = dxf.layer("CARBON_RODS", 8)
        for channel in geometry.carbon_rods.channels():
            dxf.polyline(channel, rods)

    if body.carved_top is not None:
        dxf.polyline(body.carved_top.plateau, dxf.layer("TOP_CARVE_PLATEAU", 8))
    if body.stepped_top is not None:
        steps = dxf.layer("TOP_STEPS", 6)
        for boundary in body.stepped_top.boundaries:
            dxf.polyline(boundary, steps)
    for contour in body.contours:
        dxf.polyline(
            contour.region(),
            dxf.layer("TOP_CONTOURS" if contour.face == "top" else "BACK_CONTOURS", 8),
        )
    top = dxf.layer("BODY_TOP_CAVITIES", 1)
    for cavity in body.top_cavities:
        dxf.polyline(cavity.outline, top)
    rear = dxf.layer("BODY_REAR_CAVITIES", 5)
    for rear_cavity in body.rear_cavities:
        dxf.polyline(rear_cavity.cover_recess.outline, rear)
        for pocket in rear_cavity.pockets:
            dxf.polyline(pocket.outline, rear)
    if body.neck_plate:
        dxf.polyline(body.neck_plate, dxf.layer("NECK_PLATE", 8))
    holes = dxf.layer("BODY_HOLES_TOP", 3)
    mounting = body.bridge_mounting
    for pivot in mounting.pivot_holes:
        dxf.circle(pivot, mounting.pivot_hole_diameter / 2.0, holes)
    for hole in (*body.holes, *body.control_top_marks):
        dxf.circle(hole.center, hole.diameter / 2.0, holes)
    back_holes = dxf.layer("BODY_HOLES_BACK", 4)
    for hole in (*body.rear_holes, *body.control_back_marks):
        dxf.circle(hole.center, hole.diameter / 2.0, back_holes)
    if body.jack_hole is not None:
        jack = body.jack_hole
        dxf.circle(
            Point2D(jack.start_x, jack.start_y),
            jack.diameter / 2.0,
            dxf.layer("JACK", 3),
        )
    if body.wire_holes:
        wiring = dxf.layer("WIRE_HOLES", 1)
        for wire in body.wire_holes:
            dxf.line(
                Point2D(wire.start.x, wire.start.y),
                Point2D(wire.end.x, wire.end.y),
                wiring,
            )
    if body.side_holes:
        sideways = dxf.layer("SIDE_HOLES", 6)
        for side in body.side_holes:
            dxf.line(
                Point2D(side.start.x, side.start.y),
                Point2D(side.end.x, side.end.y),
                sideways,
            )
    engraving = body.engraving
    if engraving is not None:
        layer = dxf.layer("ENGRAVING", 4)
        for line in engraving.lines:
            dxf.polyline(line, layer, closed=False)
        for shape in engraving.pockets:
            dxf.polyline(shape.outline, layer)
    covers = dxf.layer("COVERS", 30)
    cover_holes = dxf.layer("COVER_HOLES", 30)
    for plate in geometry.covers:
        _plate(dxf, plate, covers, cover_holes, Point2D(0.0, 0.0))
    xs = [p.x for p in (*body.outline.points, *geometry.headstock.plan.boundary)]
    dxf.line(
        Point2D(min(xs) - 5.0, 0.0),
        Point2D(max(xs) + 5.0, 0.0),
        dxf.layer("CENTERLINE", 8),
    )
    return dxf.render()


def render_covers_dxf(covers: Sequence[CoverPlate]) -> str | None:
    """Return the sheet plates laid out side by side for cutting, or ``None``.

    Each plate keeps its plan orientation (seen from above as it is
    fitted), its holes and slots, with its name below it.
    """
    if not covers:
        return None
    dxf = DxfDocument()
    outline = dxf.layer("COVER_OUTLINES", 7)
    holes = dxf.layer("COVER_HOLES", 1)
    labels = dxf.layer("COVER_LABELS", 3)
    cursor = 0.0
    for plate in covers:
        xs = [point.x for point in plate.outline]
        ys = [point.y for point in plate.outline]
        shift = Point2D(cursor - min(xs), -min(ys))
        _plate(dxf, plate, outline, holes, shift)
        dxf.text(
            Point2D(cursor, -2.0 * LABEL_HEIGHT),
            LABEL_HEIGHT,
            f"{plate.name} ({plate.thickness:g} mm)",
            labels,
        )
        cursor += max(xs) - min(xs) + COVER_GAP
    return dxf.render()


def _plate(
    dxf: DxfDocument, plate: CoverPlate, outline: str, holes: str, shift: Point2D
) -> None:
    """Draw one plate, its holes and slots, moved by ``shift``."""

    def moved(point: Point2D) -> Point2D:
        return Point2D(point.x + shift.x, point.y + shift.y)

    dxf.polyline([moved(point) for point in plate.outline], outline)
    for hole in plate.holes:
        dxf.circle(moved(hole.center), hole.diameter / 2.0, holes)
    for slot in plate.slots:
        dxf.polyline([moved(point) for point in slot.outline], holes)
