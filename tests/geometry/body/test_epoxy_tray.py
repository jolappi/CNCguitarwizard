"""Tests for the epoxy tray routed over the top."""

import ast
import math
from dataclasses import replace
from pathlib import Path

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.cam.planar import (
    disc_fits,
    distance_to_boundary,
    segment_distance,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.dxf import render_plan_dxf
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg
from cncguitarwizard.webapp import body_editor_layout, design_problems
from cncguitarwizard.workflows import build_prototype001


def tray(**overrides: object) -> Prototype001Parameters:
    return replace(  # type: ignore[arg-type]
        Prototype001Parameters(), **{"body_epoxy_tray_depth": 3.0, **overrides}
    )


@pytest.mark.parametrize("rim", [4.0, 6.0])
def test_the_tray_leaves_as_much_wood_at_the_edge_as_round_the_openings(
    rim: float,
) -> None:
    body = tray(body_epoxy_tray_rim=rim).build().body
    assert body.epoxy_tray is not None
    outline = body.outline.points

    # The rim: its edge body_epoxy_tray_rim in from the body's.
    for point in body.epoxy_tray.outline[::25]:
        assert point_in_polygon(point, outline)
        assert distance_to_boundary(point, outline) == pytest.approx(rim, abs=0.1)
    # A wall as thick round every route and hole in the top.
    walls = body.epoxy_tray.walls
    for cavity in (body.neck_pocket, body.neck_pickup, body.bridge_pickup):
        assert cavity is not None
        wall = next(w for w in walls if point_in_polygon(cavity.outline[0], w))
        for point in wall[::5]:
            assert distance_to_boundary(point, cavity.outline) == pytest.approx(
                rim, abs=0.1
            )
    for hole in body.holes:
        assert any(
            point_in_polygon(hole.center, wall)
            and min(math.dist((p.x, p.y), (hole.center.x, hole.center.y)) for p in wall)
            == pytest.approx(hole.diameter / 2.0 + rim, abs=0.1)
            for wall in walls
        )


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"body_top_edge_radius": 5.0}, "wider than the top edge's roundover"),
        ({"body_epoxy_tray_rim": -1.0}, "finite and positive"),
        ({"body_arm_contour_depth": 10.0}, "needs the flat top"),
        ({"body_epoxy_tray_depth": 12.0}, "under 3 mm of wood over Control cavity"),
    ],
)
def test_a_tray_that_cannot_hold_epoxy_is_refused(
    overrides: dict[str, object], match: str
) -> None:
    with pytest.raises(BodyGeometryError, match=match):
        tray(**overrides).build()


@pytest.mark.parametrize(
    "overrides",
    [{"body_carved_top": True}, {"neck_joint": "neck_through"}],
)
def test_a_tray_on_a_top_that_is_not_its_own_flat_top_is_left_out(
    overrides: dict[str, object],
) -> None:
    # A carved top, or a neck-through body's centre: the tray does not
    # apply there (setting_conditions), so it is left out, not refused.
    assert tray(**overrides).build().body.epoxy_tray is None


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


def test_a_gap_in_the_tray_narrower_than_the_cutter_is_left_as_wood() -> None:
    # The walls round the neck pocket and the neck pickup route stand 2 mm
    # apart (10 mm between the routes, a 4 mm wall round each): the 6 mm
    # cutter never gets in between them.
    body = tray().build().body
    assert body.epoxy_tray is not None
    assert body.neck_pocket is not None and body.neck_pickup is not None
    between = Point2D((body.neck_pocket.max_x + body.neck_pickup.min_x) / 2.0, 0.0)
    from cncguitarwizard.cam.operations import pocket

    path = pocket(
        "Epoxy tray",
        body.epoxy_tray.outline,
        3.0,
        MachiningParameters(),
        islands=list(body.epoxy_tray.walls),
    )
    radius = MachiningParameters().tool_radius
    moves = path.moves
    for start, end in zip(moves, moves[1:], strict=False):
        if end.rapid or end.z >= 0.0:
            continue
        run = (Point2D(start.x, start.y), Point2D(end.x, end.y))
        assert segment_distance(between, *run) > radius


def test_the_model_cuts_the_tray_only_where_the_cutter_reaches(tmp_path: Path) -> None:
    # The build hands the body's cutter to the FreeCAD script, which cuts
    # the tray opened by it: the gap above stays wood in the model too.
    result = build_prototype001(
        tmp_path,
        tray(),
        run_freecad=False,
        machining=MachiningParameters(tool_diameter=8.0),
    )
    source = result.python_path.read_text(encoding="utf-8")
    assert "TRAY_TOOL_RADIUS = 4.0" in source
    assert "makeOffset2D(" in source
    # Rendered on its own, with no cutter, the whole tray is cut.
    alone = FreeCADScriptExporter().render_prototype001(tray().build())
    assert "TRAY_TOOL_RADIUS = 0.0" in alone
