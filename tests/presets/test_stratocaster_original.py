"""Tests for a Stratocaster as on the original: its neck's back running
into the heel and the headstock as the user's reference Stratocaster neck
does, and its arm contour and belly cut where the user's drawing has them."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.planar import distance_to_boundary
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import NECK_TEMPLATE_RESETS
from cncguitarwizard.presets.styles import STYLES

STYLE = STYLES["stratocaster"]
STRAT = Prototype001Parameters(**STYLE.prototype_values(STYLE.instruments[0]))
GEOMETRY = STRAT.build()


def _back_at(x: float) -> float:
    """Return the neck's back down its middle at ``x``, below the glue face."""
    rows = GEOMETRY.neck_surface.mesh.rows
    row = min(rows, key=lambda r: abs(r[0].x - x))
    return min(row, key=lambda p: abs(p.y)).z


def test_the_back_runs_into_the_headstocks_lower_back_as_the_reference() -> None:
    # The reference neck keeps the blank's back on its headstock: 14.3 mm
    # thick, its face 4.3 mm down, so its back 3.9 mm below the neck's.
    assert (STRAT.headstock_thickness, STRAT.headstock_face_drop) == (14.3, 4.3)
    assert STRAT.headstock_root_style == "drawn"
    neck = 20.8 - STRAT.fretboard_thickness
    assert _back_at(14.0) == pytest.approx(-neck, abs=0.05)
    assert _back_at(-8.0) == pytest.approx(-18.6, abs=0.01)
    # Between, it turns down evenly, never below the headstock's back.
    depths = [_back_at(x) for x in (12.0, 8.0, 5.0, 2.0)]
    assert depths == sorted(depths, reverse=True)
    assert all(-18.6 - 1e-6 <= d <= -neck + 1e-6 for d in depths)


def test_the_root_is_lofted_smooth_across_the_headstocks_flare() -> None:
    # Regression: beside the drawn lines' ends, where the headstock flares
    # out on the bass side, the loft kinked 3 mm from one row to the next.
    rows = [
        row
        for row in FreeCADScriptExporter.neck_loft_rows(
            GEOMETRY.neck_surface,
            GEOMETRY.headstock,
            GEOMETRY.joint_fillet_radius,
            GEOMETRY.volute,
        )
        if -40.0 <= row[0].x <= 20.0
    ]
    for before, row, after in zip(rows, rows[1:], rows[2:], strict=False):
        for a, b, c in zip(before, row, after, strict=True):
            t = (b.x - a.x) / (c.x - a.x)
            assert abs(a.z + (c.z - a.z) * t - b.z) < 1.0, (round(b.x, 1), b.y)


def test_the_back_runs_into_the_heels_block_as_the_reference() -> None:
    assert STRAT.heel_thickness == 18.6
    assert STRAT.heel_root_style == "drawn"
    surface = GEOMETRY.neck_surface
    block = surface.neck_outline.last_fret_position - surface.heel_flat_start_offset
    # The block's flat from 44 mm ahead of it down the middle, the neck's
    # own profile from 64 mm.
    assert _back_at(block - 40.0) == pytest.approx(-18.6, abs=0.01)
    assert _back_at(block - 70.0) > -16.5


def test_a_headstock_thinner_than_the_neck_needs_its_root_drawn() -> None:
    # Regression: the back's model refused a headstock thinner than the
    # neck's wood at the first fret, though a drawn root runs the back into
    # its own (lower) back plane instead.
    with pytest.raises(NeckGeometryError, match="Nut-transition thickness"):
        replace(STRAT, headstock_root_style="smooth").build()


def test_another_neck_template_takes_none_of_the_stratocasters_own() -> None:
    for name in (
        "heel_root_style",
        "heel_root_flat_points",
        "heel_root_neck_points",
        "headstock_face_drop",
        "headstock_face_transition",
        "headstock_root_style",
        "headstock_root_flat_points",
        "headstock_root_neck_points",
    ):
        assert name in NECK_TEMPLATE_RESETS


def test_its_arm_contour_and_belly_cut_are_the_drawings() -> None:
    shape = STRAT.body_shape
    assert shape.arm_contour_points and shape.belly_cut_points
    contours = {c.name: c for c in GEOMETRY.body.contours}
    arm, belly = contours["Arm contour"], contours["Belly cut"]
    # As deep as a face can be cut, its roundover running on down from
    # their floor (together to the body's middle).
    assert (arm.depth, belly.depth) == (10.9, 10.9)
    assert arm.depth + GEOMETRY.body.top_edge.radius == pytest.approx(22.0)
    assert (arm.face, belly.face) == ("top", "back")
    # Where both cut the edge, it keeps wood enough.
    left = [
        STRAT.body_thickness - arm.depth_at(p) - belly.depth_at(p)
        for c in (arm, belly)
        for p in c.edge
    ]
    assert min(left) > 14.0


def test_its_edges_are_rounded_over_its_back_short_of_the_neck_plate() -> None:
    # 7/16 in, as a Stratocaster's edges usually are; its neck plate sits
    # nearer the back's edge than that, as on the original, so the back's
    # roundover stops short of it (the edge there blended by hand).
    body = GEOMETRY.body
    assert (body.top_edge.radius, body.back_edge.radius) == (11.1, 11.1)
    assert body.top_edge.square == () and len(body.back_edge.square) == 1
    plate = body.neck_plate
    assert min(distance_to_boundary(p, body.outline.points) for p in plate) < 3.0
    beside = [
        p
        for p in body.edge_points
        if min(distance_to_boundary(p, plate), 99.0) < body.back_edge.radius + 1.0
    ]
    assert beside and not any(body.back_edge.rounds_at(p) for p in beside)
    # Only there: the rest of the edge, most of it, rounded over.
    edge = body.edge_points
    lengths = [
        (math.dist((a.x, a.y), (b.x, b.y)), body.back_edge.rounds_at(a))
        for a, b in zip(edge, (*edge[1:], edge[0]), strict=True)
    ]
    rounded = sum(length for length, rounds in lengths if rounds)
    assert rounded > 0.85 * sum(length for length, _ in lengths)
    # The model's rings are cut round it too.
    script = FreeCADScriptExporter().render_prototype001(GEOMETRY)
    assert script.count("edge_ring(") > 10 and ", [[" in script
