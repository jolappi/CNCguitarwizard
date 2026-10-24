"""Tests for a round (Fender Stratocaster) heel end and the pocket, board
and bolts that follow it."""

import ast
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import fretboard_outline_polygon
from cncguitarwizard.cam.neck import neck_plan_polygon
from cncguitarwizard.geometry.neck.outline import heel_end_inset
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import (
    FENDER_HEEL_CORNER_RADIUS,
    FENDER_HEEL_END_RADIUS,
    NECK_TEMPLATE_RESETS,
    STRATOCASTER_NECK,
)
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg

ROUND = replace(Prototype001Parameters(), neck_heel_end="round")


def test_the_stratocaster_neck_has_a_round_heel_and_others_go_back_square() -> None:
    assert STRATOCASTER_NECK["neck_heel_end"] == "round"
    assert "neck_heel_end" in NECK_TEMPLATE_RESETS
    assert Prototype001Parameters().neck_heel_end == "square"


def test_the_pocket_follows_the_round_heel_with_its_clearance() -> None:
    layout = ROUND.body_layout()
    pocket = layout.neck_pocket.outline
    heel_end = layout.heel_end
    clearance = ROUND.body_neck_pocket_clearance
    half = ROUND.heel_width / 2.0 + clearance

    # Its end touches the heel's on the centre and rounds as it does, the
    # clearance out.
    assert max(p.x for p in pocket) == pytest.approx(heel_end)
    for point in pocket:
        assert (
            point.x
            <= heel_end
            - heel_end_inset(
                point.y,
                half,
                FENDER_HEEL_END_RADIUS + clearance,
                FENDER_HEEL_CORNER_RADIUS + clearance,
            )
            + 1e-6
        )
    # The heel sits inside it (on the centre, where they touch, within
    # what sampling the two arcs leaves).
    neck = ROUND.neck_outline()
    for point in neck.boundary:
        if point.x > heel_end - 20.0:
            assert point_in_polygon(point, pocket) or point.x >= heel_end - 0.02


def test_the_board_and_the_neck_are_cut_round_with_it() -> None:
    geometry = ROUND.build()
    outline = geometry.neck_outline
    end = outline.last_fret_position + outline.heel_length

    for polygon in (fretboard_outline_polygon(geometry), neck_plan_polygon(geometry)):
        assert all(p.x <= end - outline.heel_end_inset(p.y) + 1e-6 for p in polygon)
        # Short of the end at its corners, by its corners' rounding.
        assert max(p.x for p in polygon if abs(p.y) > 27.9) < end - 6.0
    assert "Fretboard" in render_plan_view_svg(geometry)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    ast.parse(source)
    assert "round heel end" in source and "round heel end on the board" in source


@pytest.mark.parametrize("template", ["design_by_jone", "stratocaster", "les_paul"])
def test_the_bolts_keep_their_end_wall_to_the_round_end(template: str) -> None:
    parameters = replace(
        ROUND,
        body_shape=YOUR_DESIGN_TEMPLATES[template][1],
        body_heel_relief="contour",
    )
    body = parameters.build().body
    outline = parameters.neck_outline()
    heel_end = parameters.body_layout().heel_end
    radius = parameters.body_neck_bolt_hole_diameter / 2.0
    holes = [h for h in body.rear_holes if h.name.endswith(" hole")]
    assert len(holes) == 4
    for hole in holes:
        wall = heel_end - outline.heel_end_inset(hole.center_y) - hole.center_x
        assert wall - radius >= parameters.body_neck_bolt_end_wall - 1e-6


def test_a_plate_sits_clear_of_the_round_end() -> None:
    parameters = replace(
        ROUND,
        body_shape=YOUR_DESIGN_TEMPLATES["stratocaster"][1],
        body_neck_plate="plate",
    )
    body = parameters.build().body
    outline = parameters.neck_outline()
    heel_end = parameters.body_layout().heel_end
    radius = parameters.body_neck_bolt_hole_diameter / 2.0
    tails = sorted(
        (h for h in body.rear_holes if h.name.startswith("Neck bolt")),
        key=lambda h: h.center_x,
    )[-2:]
    for hole in tails:
        wall = heel_end - outline.heel_end_inset(hole.center_y) - hole.center_x
        assert wall - radius == pytest.approx(parameters.body_neck_bolt_end_wall)


def test_a_neck_through_has_no_heel_end_to_round() -> None:
    # Left square, not refused: the setting does not apply there.
    outline = replace(ROUND, neck_joint="neck_through").neck_outline()

    assert outline.heel_end_radius == 0.0
