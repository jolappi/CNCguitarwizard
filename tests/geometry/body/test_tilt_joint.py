"""Tests for the heel bevel and a neck plate tilted on it (a Tilt Joint)."""

import ast
import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import HeelRelief
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import (
    HEEL_BEVEL_SIDE_RUN,
    NECK_BOLT_MARK_DEPTH,
)
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg

STRATOCASTER = YOUR_DESIGN_TEMPLATES["stratocaster"][1]


def tilt(**overrides: object) -> Prototype001Parameters:
    """A Fender style plate on a bevel, on the Stratocaster style body."""
    return replace(  # type: ignore[arg-type]
        Prototype001Parameters(),
        **{
            "body_shape": STRATOCASTER,
            "body_heel_relief": "bevel",
            "body_neck_plate": "plate",
            **overrides,
        },
    )


def bevel_of(parameters: Prototype001Parameters) -> HeelRelief:
    (relief,) = [c for c in parameters.build().body.contours if c.name == "Heel relief"]
    assert isinstance(relief, HeelRelief)
    return relief


def test_a_bevel_is_a_flat_slope_from_the_edge_up_to_its_line() -> None:
    parameters = replace(Prototype001Parameters(), body_heel_relief="bevel")
    relief = bevel_of(parameters)
    heel_end = parameters.body_layout().heel_end
    outline = parameters.build().body.outline.points

    deep, face = relief.plane
    assert face == pytest.approx(heel_end + 15.0, abs=0.1)
    # Its full depth where the centreline leaves the body ahead of the heel.
    assert point_in_polygon(Point2D(deep + 1.0, 0.0), outline)
    assert not point_in_polygon(Point2D(deep - 1.0, 0.0), outline)
    # Straight between: as deep again half as far from the face.
    slope = relief.depth / (face - deep)
    for x in (heel_end - 40.0, heel_end - 20.0, heel_end):
        assert relief.depth_at(Point2D(x, 0.0)) == pytest.approx(slope * (face - x))
    # The ferrules sink into it as into a contour.
    body = parameters.build().body
    for hole in body.rear_holes:
        if hole.name.endswith("ferrule"):
            under = relief.depth_at(hole.center)
            assert hole.depth == pytest.approx(under + 5.0)


@pytest.mark.parametrize("plate", ["plate", "asymmetric"])
def test_a_plate_on_a_bevel_has_its_bolts_drilled_by_hand(plate: str) -> None:
    parameters = tilt(body_neck_plate=plate)
    body = parameters.build().body
    relief = bevel_of(parameters)
    heel_end = parameters.body_layout().heel_end
    deep, face = relief.plane
    slope = relief.depth / (face - deep)

    # The CNC marks each bolt's centre on the bevel...
    marks = [hole for hole in body.rear_holes if hole.name.startswith("Neck bolt")]
    assert [hole.name for hole in marks] == [
        f"Neck bolt {n} centre mark" for n in range(1, 5)
    ]
    for mark in marks:
        assert mark.depth == pytest.approx(
            relief.depth_at(mark.center) + NECK_BOLT_MARK_DEPTH
        )
    # ...and each hole runs square to it into the neck pocket.
    holes = [hole for hole in body.side_holes if hole.name.startswith("Neck bolt")]
    assert len(holes) == 4
    floor = parameters.body_thickness - parameters.heel_thickness
    for mark, hole in zip(marks, holes, strict=True):
        assert hole.opens_into == "Neck pocket"
        assert (hole.start.x, hole.start.y) == pytest.approx(
            (mark.center_x, mark.center_y)
        )
        assert hole.start.z == pytest.approx(relief.depth_at(mark.center))
        assert hole.end.z == pytest.approx(floor)
        rise = hole.end.z - hole.start.z
        assert (hole.end.x - hole.start.x) / rise == pytest.approx(slope)
    # The tail pair come out the end wall (3 mm) and radius short of the
    # heel end.
    assert max(hole.end.x for hole in holes) == pytest.approx(heel_end - 5.5)
    plan = plan_body_machining(body, MachiningParameters())
    assert plan.back_small_holes is not None
    note = plan.back_small_holes.notes[-1]
    assert f"tilted {math.degrees(math.atan(slope)):.1f} degrees" in note


def test_the_plate_must_sit_wholly_on_the_bevels_slope() -> None:
    # A bevel whose line crosses the plate: its tail end is off it.
    line = ((-60.0, 40.0), (-40.0, 32.0), (-20.0, 0.0), (-40.0, -32.0), (-60.0, -40.0))
    parameters = tilt(body_shape=replace(STRATOCASTER, heel_relief_points=line))
    with pytest.raises(BodyGeometryError, match="wholly on the heel bevel's slope"):
        parameters.build()


def test_a_bevel_line_must_run_on_behind_the_edge() -> None:
    line = ((-76.0, 20.0), (-75.5, 0.0), (-76.0, -20.0))
    parameters = tilt(body_shape=replace(STRATOCASTER, heel_relief_points=line))
    with pytest.raises(BodyGeometryError, match="must run on behind"):
        parameters.build()


def test_a_hand_drilled_hole_opens_only_into_its_own_cavity() -> None:
    body = tilt().build().body
    bolt = next(hole for hole in body.side_holes if hole.name == "Neck bolt 1 hole")
    # Run on 1 mm into the pocket.
    deeper = replace(bolt, end=replace(bolt.end, z=bolt.end.z + 1.0))

    replace(body, side_holes=(deeper,))
    with pytest.raises(BodyGeometryError, match="would break into Neck pocket"):
        replace(body, side_holes=(replace(deeper, opens_into=""),))


def test_the_tilted_bolts_are_modelled_and_drawn() -> None:
    geometry = tilt(body_neck_plate="asymmetric").build()

    source = FreeCADScriptExporter().render_prototype001(geometry)
    ast.parse(source)
    assert source.count("BODY_CUTTERS.append(side_hole)  # neck bolt 1 hole\n") == 1
    assert "Neck bolt 1 hole" in render_plan_view_svg(geometry)


@pytest.mark.parametrize("handedness", ["right", "left"])
def test_a_plate_tilts_toward_the_treble_corner_on_a_corner_bevel(
    handedness: str,
) -> None:
    parameters = tilt(
        body_neck_plate="asymmetric",
        body_heel_relief_line="corner",
        handedness=handedness,
    )
    body = parameters.build().body
    relief = bevel_of(parameters)
    treble = -parameters.bass_sign
    heel_end = parameters.body_layout().heel_end

    # Sloping toward the treble corner (toward the nut and the treble side),
    # laid out round the heel so it takes the whole plate, on its slope.
    assert relief.plane_axis == pytest.approx(
        (-math.sqrt(0.5), treble * math.sqrt(0.5))
    )
    deep, face = relief.plane
    for point in body.neck_plate:
        assert point_in_polygon(point, relief.region())
        assert (relief.along_plane(point) - deep) * (face - deep) >= 0.0
    # Its bolts lean toward the heel end and the bass side as they go in;
    # the plate sits that far toward the treble side, so they come out in
    # the pocket either side of the centreline, the tail pair the end wall
    # and radius short of the heel end.
    holes = [hole for hole in body.side_holes if hole.name.startswith("Neck bolt")]
    assert len(holes) == 4
    for hole in holes:
        assert hole.end.x > hole.start.x
        assert (hole.end.y - hole.start.y) * treble < 0.0
    exits = sorted(hole.end.y * treble for hole in holes)
    assert exits[0] == pytest.approx(-exits[-1], abs=0.2)
    assert max(hole.end.x for hole in holes) == pytest.approx(heel_end - 5.5)
    plan = plan_body_machining(body, MachiningParameters())
    assert plan.back_small_holes is not None
    note = plan.back_small_holes.notes[-1]
    assert "toward the treble corner" in note
    assert "toward the heel end and the bass side" in note


def test_a_bevel_with_no_plate_slopes_at_its_sides_too() -> None:
    # Up to the face at its line from HEEL_BEVEL_SIDE_RUN in, a slanted
    # side, not a wall the slope's depth deep; with a plate on it, flat to
    # its line, for the plate to sit on.
    parameters = replace(Prototype001Parameters(), body_heel_relief="bevel")
    relief = bevel_of(parameters)
    assert relief.side_run == HEEL_BEVEL_SIDE_RUN
    assert bevel_of(tilt()).side_run == 0.0
    body = parameters.build().body
    pocket = body.neck_pocket
    assert pocket is not None
    bass = parameters.bass_sign
    bass_wall = max(p.y * bass for p in pocket.outline)
    heel_end = max(p.x for p in pocket.outline)
    deep, face = relief.plane
    x = heel_end - 20.0
    sloped = relief.depth * (face - x) / (face - deep)
    for inside in (1.0, 3.0, 6.0):
        point = Point2D(x, (bass_wall - inside) * bass)
        assert relief.depth_at(point) == pytest.approx(
            min(sloped, relief.depth * inside / HEEL_BEVEL_SIDE_RUN), abs=0.05
        )
    # Well in from its line, the slope itself.
    assert relief.depth_at(Point2D(x, 0.0)) == pytest.approx(sloped)
    # Its layers keep in from the line by as much.
    level = relief.depth / 3.0
    region = relief.level_region(level)
    assert not point_in_polygon(Point2D(x, (bass_wall - 1.0) * bass), region)


def test_a_bevel_side_run_must_not_be_negative() -> None:
    line = (Point2D(-100.0, 50.0), Point2D(-60.0, 0.0), Point2D(-100.0, -50.0))
    edge = (Point2D(-100.0, 50.0), Point2D(-100.0, 0.0), Point2D(-100.0, -50.0))
    with pytest.raises(BodyGeometryError, match="side run"):
        HeelRelief(
            "Heel relief", edge, line, 6.0, "plane", (-100.0, -60.0), side_run=-1.0
        )
