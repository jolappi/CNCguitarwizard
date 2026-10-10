"""Tests for the epoxy tray routed over the top."""

import ast
import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.cam.planar import disc_fits, distance_to_boundary
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.dxf import render_plan_dxf
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg
from cncguitarwizard.webapp import body_editor_layout, design_problems


def tray(**overrides: object) -> Prototype001Parameters:
    return replace(  # type: ignore[arg-type]
        Prototype001Parameters(), **{"body_epoxy_tray_depth": 3.0, **overrides}
    )


def test_the_tray_leaves_a_rim_at_the_edge_and_walls_round_the_openings() -> None:
    body = tray().build().body
    assert body.epoxy_tray is not None
    outline = body.outline.points

    # The rim: its edge 4 mm in from the body's.
    for point in body.epoxy_tray.outline[::25]:
        assert point_in_polygon(point, outline)
        assert distance_to_boundary(point, outline) == pytest.approx(4.0, abs=0.1)
    # A wall 2 mm thick round every route and hole in the top.
    walls = body.epoxy_tray.walls
    for cavity in (body.neck_pocket, body.neck_pickup, body.bridge_pickup):
        assert cavity is not None
        wall = next(w for w in walls if point_in_polygon(cavity.outline[0], w))
        for point in wall[::5]:
            assert distance_to_boundary(point, cavity.outline) == pytest.approx(
                2.0, abs=0.1
            )
    for hole in body.holes:
        assert any(
            point_in_polygon(hole.center, wall)
            and min(math.dist((p.x, p.y), (hole.center.x, hole.center.y)) for p in wall)
            == pytest.approx(hole.diameter / 2.0 + 2.0, abs=0.1)
            for wall in walls
        )


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"body_top_edge_radius": 5.0}, "wider than the top edge's roundover"),
        ({"body_epoxy_tray_rim": -1.0}, "finite and positive"),
        ({"body_arm_contour_depth": 10.0}, "needs the flat top"),
        ({"body_carved_top": True}, "needs the flat top"),
        ({"neck_joint": "neck_through"}, "centre is the neck"),
        ({"body_epoxy_tray_depth": 12.0}, "under 3 mm of wood over Control cavity"),
    ],
)
def test_a_tray_that_cannot_hold_epoxy_is_refused(
    overrides: dict[str, object], match: str
) -> None:
    with pytest.raises(BodyGeometryError, match=match):
        tray(**overrides).build()


def test_the_tray_is_routed_first_in_the_top_program() -> None:
    body = tray().build().body
    plan = plan_body_machining(body, MachiningParameters())

    first, second = plan.top.toolpaths[:2]
    assert first.name == "Epoxy tray"
    assert first.deepest_z() == pytest.approx(-3.0)
    # The routes are cut inside its walls afterwards.
    assert second.name == "Neck pocket"


def test_the_tray_is_modelled_drawn_and_shown() -> None:
    geometry = tray().build()

    source = FreeCADScriptExporter().render_prototype001(geometry)
    ast.parse(source)
    assert "epoxy tray cut" in source
    assert "Epoxy tray" in render_plan_view_svg(geometry)
    assert "EPOXY_TRAY" in render_plan_dxf(geometry)
    layout = body_editor_layout({"prototype": {"body_epoxy_tray_depth": 3.0}})
    roles = [polygon["role"] for polygon in layout["polygons"]]
    assert roles[1] == "tray" and roles.count("tray_wall") >= 5
    # Its walls reach past the outline at the neck pocket's mouth, and are
    # not counted as outside it.
    assert design_problems({"prototype": {"body_epoxy_tray_depth": 3.0}}) == []


def test_the_tray_routes_keep_off_its_walls() -> None:
    body = tray().build().body
    assert body.epoxy_tray is not None
    from cncguitarwizard.cam.operations import pocket

    path = pocket(
        "Epoxy tray",
        body.epoxy_tray.outline,
        3.0,
        MachiningParameters(),
        islands=list(body.epoxy_tray.walls),
    )
    radius = MachiningParameters().tool_radius
    for move in path.moves:
        if move.rapid or move.z >= 0.0:
            continue
        point = Point2D(move.x, move.y)
        assert all(
            disc_fits(point, wall, radius - 1e-6, inside=False)
            for wall in body.epoxy_tray.walls
        )
