"""Tests for the carved (arched) top: a flat plateau, a fall and a flat rim."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import CarvedTop, TuneOMaticSpec
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.render.svg import render_plan_view_svg
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

CARVED = replace(Prototype001Parameters(), body_carved_top=True)
LES_PAUL = replace(
    CARVED,
    body_shape=YOUR_DESIGN_TEMPLATES["les_paul"][1],
    body_bridge=TuneOMaticSpec(),
    body_thickness=50.8,
)


def _square(half: float) -> tuple[Point2D, ...]:
    return (
        Point2D(-half, -half),
        Point2D(half, -half),
        Point2D(half, half),
        Point2D(-half, half),
    )


def test_the_top_falls_from_the_plateau_to_a_flat_rim() -> None:
    carve = CarvedTop(_square(100.0), _square(30.0), 9.5, 8.0)

    # Flat on the plateau, flat on the rim, falling in between.
    assert carve.drop_at(0.0, 0.0) == 0.0
    assert carve.drop_at(25.0, 0.0) == 0.0
    assert carve.drop_at(95.0, 0.0) == pytest.approx(9.5)
    assert carve.drop_at(93.0, 0.0) == pytest.approx(9.5, abs=0.05)
    drops = [carve.drop_at(x, 0.0) for x in range(30, 92, 4)]
    assert drops == sorted(drops)
    assert 0.0 < carve.drop_at(60.0, 0.0) < 9.5
    # The rim level carries on past the edge, then the blank is left.
    assert carve.drop_at(105.0, 0.0) == pytest.approx(9.5)
    assert carve.drop_at(130.0, 0.0) == 0.0


def test_the_pickups_bridge_and_pocket_sit_on_the_plateau() -> None:
    layout = LES_PAUL.body_layout()
    carve = layout.carved_top
    assert carve is not None
    flat = [
        layout.neck_pocket,
        *(p for p in (layout.neck_pickup, layout.bridge_pickup) if p is not None),
    ]
    from cncguitarwizard.geometry.body.carve import CELL, PLATEAU_EDGE_FALL

    outline = layout.outline.points

    def from_edge(point: Point2D) -> float:
        def segment(a: Point2D, b: Point2D) -> float:
            dx, dy = b.x - a.x, b.y - a.y
            t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)
            t = min(1.0, max(0.0, t))
            return math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy)

        return min(segment(a, b) for a, b in zip(outline, (*outline[1:], outline[0])))

    clear = carve.edge_rim + CELL + PLATEAU_EDGE_FALL
    for cavity in flat:
        for point in cavity.outline:
            # Inside the body the features are flat; only by the neck
            # pocket's mouth, where the plateau keeps clear of the edge so
            # the top has room to fall, does the top fall round it.
            if point_in_polygon(point, outline) and from_edge(point) > clear:
                assert carve.drop_at(point.x, point.y) == pytest.approx(0.0, abs=1e-6)
    for hole in layout.holes:
        if hole.name.startswith(("Bridge post", "Tailpiece stud")):
            assert carve.drop_at(hole.center_x, hole.center_y) == pytest.approx(0.0)


def test_the_back_cavities_keep_their_wall_under_the_arch() -> None:
    flat = LES_PAUL.build().body
    carved = replace(LES_PAUL, body_carved_top=False).build().body
    assert flat.carved_top is not None and carved.carved_top is None
    cavity = flat.control_cavity
    assert cavity is not None and carved.control_cavity is not None
    # Shallower by as much as the top falls over it.
    assert cavity.cavity.depth < carved.control_cavity.cavity.depth
    wall = min(
        LES_PAUL.body_thickness
        - flat.carved_top.drop_at(p.x, p.y)
        - cavity.cavity.depth
        for p in cavity.cavity.outline
    )
    assert wall == pytest.approx(LES_PAUL.body_rear_cavity_top_wall, abs=0.01)


def test_a_carved_top_refuses_an_arm_contour() -> None:
    with pytest.raises(BodyGeometryError, match="arm contour"):
        replace(CARVED, body_arm_contour_depth=12.0).build()


def test_the_carve_is_its_own_program_first() -> None:
    geometry = LES_PAUL.build()
    plan = plan_body_machining(geometry.body, MachiningParameters())
    names = [setup.name for setup in plan.setups]
    assert names[:3] == ["Body_index_pins", "Body_top_carve", "Body_top"]
    # Roughed to sand by hand by default, with a ball finish on request.
    (rough,) = plan.top_carve.toolpaths  # type: ignore[union-attr]
    assert rough.deepest_z() == pytest.approx(-9.5, abs=0.05)
    smooth = plan_body_machining(geometry.body, MachiningParameters(carve_finish=True))
    _, finish = smooth.top_carve.toolpaths  # type: ignore[union-attr]
    assert finish.deepest_z() == pytest.approx(-9.5, abs=0.05)
    assert len(plan.preview_outlines) == len(plan.setups)
    flat = plan_body_machining(
        replace(LES_PAUL, body_carved_top=False).build().body, MachiningParameters()
    )
    assert flat.top_carve is None


def test_a_top_binding_is_cut_from_the_rim() -> None:
    geometry = replace(LES_PAUL, body_top_binding_width=1.5).build()
    plan = plan_body_machining(geometry.body, MachiningParameters())
    (channel,) = [
        path for path in plan.top.toolpaths if path.name == "Top binding channel"
    ]
    assert channel.deepest_z() == pytest.approx(
        -(9.5 + geometry.body.top_edge.binding_depth)
    )


def test_the_model_editor_and_plan_view_show_the_carve() -> None:
    geometry = LES_PAUL.build()
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "carved top cut" in source and "CARVE_ROWS" in source
    # The heights as a cubic's control points, which cannot ripple past
    # them (a cubic fitted through them can).
    assert "buildFromPolesMultsKnots" in source and "interpolate(" not in source
    assert "carved top cut" not in FreeCADScriptExporter().render_prototype001(
        replace(LES_PAUL, body_carved_top=False).build()
    )
    editor = body_editor_layout({"prototype": {"body_carved_top": True}})
    assert any(polygon["role"] == "plateau" for polygon in editor["polygons"])
    assert 'stroke-dasharray="5,3"' in render_plan_view_svg(geometry)


def test_the_web_form_offers_the_carved_top() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["body_carved_top"]["type"] == "bool"
    assert not fields["body_carved_top"]["advanced"]
    assert fields["body_carve_depth"]["default"] == 9.5
    assert fields["body_carve_rim"]["default"] == 8.0
    machining = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }
    assert machining["carve_tool_diameter"]["default"] == 0.0
    assert machining["carve_finish"]["type"] == "bool"
    assert not machining["carve_finish"]["advanced"]


def test_the_plateau_has_round_ends_and_keeps_every_feature() -> None:
    layout = LES_PAUL.body_layout()
    carve = layout.carved_top
    assert carve is not None
    plateau = carve.plateau
    tail = max(p.x for p in plateau)
    # Round toward the tail: its tail point on the middle, and 10 mm short
    # of it far narrower than its full width (a half circle's chord).
    (end,) = [p for p in plateau if p.x == tail]
    assert abs(end.y) < 2.0
    near_end = [p.y for p in plateau if p.x > tail - 10.0]
    widest = max(p.y for p in plateau) - min(p.y for p in plateau)
    assert max(near_end) - min(near_end) < 0.6 * widest
    for hole in layout.holes:
        if hole.name.startswith(("Bridge post", "Tailpiece stud")):
            assert point_in_polygon(Point2D(hole.center_x, hole.center_y), plateau)
            assert carve.drop_at(hole.center_x, hole.center_y) == 0.0


def test_the_fall_is_smooth_without_bumps() -> None:
    from cncguitarwizard.cam.planar import offset_polygon

    stratocaster = replace(CARVED, body_shape=YOUR_DESIGN_TEMPLATES["stratocaster"][1])
    for parameters in (LES_PAUL, stratocaster):
        layout = parameters.body_layout()
        carve = layout.carved_top
        assert carve is not None
        outline = layout.outline.points
        # Right by the neck pocket's walls, at its mouth, the top falls
        # toward the mouth, across these lines.
        routed = [
            offset_polygon(layout.neck_pocket.outline, 3.0, inward=False),
            *(p.outline for p in (layout.neck_pickup, layout.bridge_pickup) if p),
        ]
        xs = [p.x for p in outline]
        # Out from the centre line the top only ever falls (no bumps), and
        # its second difference stays small (no creases or cliffs).
        for x in range(int(min(xs)) + 2, int(max(xs)), 6):
            for sign in (1.0, -1.0):
                values = []
                for k in range(400):
                    point = Point2D(float(x), sign * k * 0.5)
                    if not point_in_polygon(point, outline):
                        if values:
                            break
                        continue
                    if any(point_in_polygon(point, route) for route in routed):
                        values = []
                        continue
                    values.append(carve.drop_at(point.x, point.y))
                for a, b in zip(values, values[1:], strict=False):
                    assert b >= a - 0.02
                for a, b, c in zip(values, values[1:], values[2:], strict=False):
                    assert abs(a - 2.0 * b + c) < 1.0


def test_the_pickup_rings_rest_on_the_flat() -> None:
    from cncguitarwizard.cam.planar import offset_polygon
    from cncguitarwizard.presets.prototype001 import (
        PICKUP_RING_KEEP,
        PICKUP_RING_REACH,
    )

    layout = LES_PAUL.body_layout()
    carve = layout.carved_top
    assert carve is not None
    assert (PICKUP_RING_REACH, PICKUP_RING_KEEP) == (12.0, 7.0)
    # A humbucker's ring (about 92 x 45 mm) reaches up to about 5 mm past
    # its route: all of it on the flat, the neck pickup's by the cutaway
    # too, none of it over the fall.
    for pickup in (layout.neck_pickup, layout.bridge_pickup):
        assert pickup is not None
        for point in offset_polygon(pickup.outline, 5.0, inward=False):
            assert carve.drop_at(point.x, point.y) < 0.05
    # Away from the edge the plateau's wider margin keeps them flat further.
    bridge = layout.bridge_pickup
    assert bridge is not None
    for point in offset_polygon(bridge.outline, 10.0, inward=False):
        assert carve.drop_at(point.x, point.y) < 0.05


def test_a_top_binding_sits_on_the_rim_all_round() -> None:
    from cncguitarwizard.cam.planar import offset_polygon

    layout = replace(LES_PAUL, body_top_binding_width=1.5).body_layout()
    carve = layout.carved_top
    assert carve is not None
    pocket = offset_polygon(layout.neck_pocket.outline, 1.0, inward=False)
    # Across the binding's channel (and a little in), round the whole edge
    # and by the neck pocket's mouth too, the top is at the rim's level.
    for inset in (0.2, 0.7, 1.35, 1.9):
        for point in offset_polygon(layout.outline.points, inset, inward=True):
            if not point_in_polygon(point, pocket):
                assert carve.drop_at(point.x, point.y) == pytest.approx(9.5, abs=0.05)
    # The pickups' rings still rest on the flat.
    for pickup in (layout.neck_pickup, layout.bridge_pickup):
        assert pickup is not None
        for point in offset_polygon(pickup.outline, 5.0, inward=False):
            assert carve.drop_at(point.x, point.y) < 0.05


def test_the_carve_depth_is_set_by_its_own_field() -> None:
    shallow = replace(LES_PAUL, body_carve_depth=6.0)
    carve = shallow.body_layout().carved_top
    assert carve is not None and carve.height == 6.0
    plan = plan_body_machining(shallow.build().body, MachiningParameters())
    assert plan.top_carve is not None
    assert plan.top_carve.toolpaths[-1].deepest_z() == pytest.approx(-6.0, abs=0.05)
    with pytest.raises(BodyGeometryError, match="body_carve_depth"):
        replace(LES_PAUL, body_carve_depth=30.0).build()
    with pytest.raises(BodyGeometryError):
        replace(LES_PAUL, body_carve_depth=0.0).build()


def test_the_model_checks_the_carve_cut_took_off_its_wood() -> None:
    import re

    from cncguitarwizard.backends.freecad.script_exporter import _carve_removed

    geometry = LES_PAUL.build()
    carve = geometry.body.carved_top
    assert carve is not None
    source = FreeCADScriptExporter().render_prototype001(geometry)
    # A curved cut can fail quietly: each fuzz is tried and kept only when
    # it took off about the wood the carve should.
    assert "for carve_fuzz in (0.0, 0.001, 0.01):" in source
    match = re.search(r"CARVE_REMOVED = (\d+)", source)
    assert match is not None
    removed = float(match.group(1))
    assert removed == pytest.approx(_carve_removed(carve), abs=1.0)
    # Between nothing and the whole rim depth over the body's area.
    xs = [p.x for p in carve.outline]
    ys = [p.y for p in carve.outline]
    assert 0.0 < removed < carve.height * (max(xs) - min(xs)) * (max(ys) - min(ys))
    # Over the plateau the surface stands clear, so it crosses the flat
    # top at a slope instead of nearly tangent (where the cut failed).
    from cncguitarwizard.backends.freecad.script_exporter import CARVE_PLATEAU_LIFT

    heights = re.search(r"CARVE_HEIGHTS = (\[.*\])", source)
    assert heights is not None
    values = {float(v) for v in re.findall(r"-?[\d.]+", heights.group(1))}
    assert CARVE_PLATEAU_LIFT == 0.3 and CARVE_PLATEAU_LIFT in values
    assert not any(0.02 < value < CARVE_PLATEAU_LIFT for value in values)
    # The strip kept at rim level all round is cut to it on its own (the
    # held-up surface would leave wood over a binding by the neck pocket),
    # before the edges and the carve.
    rim = source.index("carved top rim strip")
    assert f"CARVE_EDGE_RIM = {carve.height!r}, {carve.edge_rim!r}" in source
    assert carve.edge_rim == (
        max(LES_PAUL.body_top_binding_width, LES_PAUL.body_top_edge_radius) + 1.0
    )
    assert rim < source.index("carved top cut")
    # And the carve is cut last, after the cavities (and edges).
    assert source.index("carved top cut") > source.index("neck pocket cut")


def test_the_carve_roughs_quickly_to_sand() -> None:
    body = LES_PAUL.build().body
    carve = body.carved_top
    assert carve is not None
    default = MachiningParameters()
    plan = plan_body_machining(body, default)
    setup = plan.top_carve
    assert setup is not None
    # Runs linked in the cut, no ball finish: about an hour and a half with
    # the 6 mm main tool, and a bigger roughing tool far quicker.
    minutes = setup.estimated_minutes(default)
    assert minutes < 100.0
    assert setup.rapid_length() < 10_000.0
    bigger = MachiningParameters(carve_tool_diameter=10.0)
    quick = plan_body_machining(body, bigger).top_carve
    assert quick is not None and quick.tool is not None
    assert quick.tool.tool_diameter == 10.0
    assert quick.estimated_minutes(bigger) < 0.65 * minutes
    assert any("10 mm flat end mill" in note for note in quick.notes)
    finished = MachiningParameters(carve_finish=True)
    slow = plan_body_machining(body, finished).top_carve
    assert slow is not None and slow.estimated_minutes(finished) > 2.0 * minutes
    # The tool never cuts into the arch, and the rim's level runs only as
    # far past the edge as the tool needs.
    (rough,) = setup.toolpaths
    reach = default.tool_radius + 3.0
    outline = body.outline.points
    xs = [p.x for p in outline]
    for move in rough.moves:
        if move.rapid:
            continue
        model = Point2D(move.x + plan.origin_x, move.y + plan.origin_y)
        assert move.z >= -carve.drop_at(model.x, model.y) - 0.05 or not (
            point_in_polygon(model, outline)
        )
    machine_xs = [move.x for move in rough.moves]
    assert max(machine_xs) - min(machine_xs) <= max(xs) - min(xs) + 2 * reach + 1e-6


def test_the_model_never_dips_under_the_carve() -> None:
    import math

    from cncguitarwizard.backends.freecad.script_exporter import (
        CARVE_SURFACE_SPACING,
        _carve_held_up,
        _carve_poles,
    )
    from cncguitarwizard.cam.planar import offset_polygon

    layout = LES_PAUL.body_layout()
    carve = layout.carved_top
    assert carve is not None
    poles = _carve_held_up(
        _carve_poles(carve.surface_rows(CARVE_SURFACE_SPACING)), carve
    )
    heights = [[z for _, _, z in row] for row in poles]
    x0, y0 = poles[0][0][0], poles[0][0][1]
    dx, dy = poles[0][1][0] - x0, poles[1][0][1] - y0

    def basis(t: float) -> tuple[float, float, float, float]:
        return (
            (1 - t) ** 3 / 6,
            (3 * t**3 - 6 * t * t + 4) / 6,
            (-3 * t**3 + 3 * t * t + 3 * t + 1) / 6,
            t**3 / 6,
        )

    def model(x: float, y: float) -> float:
        fx, fy = (x - x0) / dx, (y - y0) / dy
        i, j = math.floor(fx), math.floor(fy)
        bx, by = basis(fx - i), basis(fy - j)
        return sum(
            by[a] * bx[b] * heights[j - 1 + a][i - 1 + b]
            for a in range(4)
            for b in range(4)
        )

    # The neck pickup sits by the cutaway, where the top falls its whole
    # depth in a few mm: smoothing that, the model dipped under a corner
    # of the pickup's ring. Held up, it stays on the flat there (the lift
    # over the plateau covers the rest) and never cuts into the fall.
    for pickup in (layout.neck_pickup, layout.bridge_pickup):
        assert pickup is not None
        for point in offset_polygon(pickup.outline, 5.0, inward=False):
            assert model(point.x, point.y) > -0.3
    for k in range(0, len(heights[0]) - 4):
        for m in range(0, len(heights) - 4):
            x, y = x0 + (k + 2.25) * dx, y0 + (m + 2.75) * dy
            if point_in_polygon(Point2D(x, y), layout.outline.points):
                assert model(x, y) >= -carve.drop_at(x, y) - 0.3


def test_the_plateau_keeps_clear_of_the_edge() -> None:
    from cncguitarwizard.cam.planar import offset_polygon
    from cncguitarwizard.geometry.body.carve import CELL, PLATEAU_EDGE_FALL

    layout = replace(LES_PAUL, body_top_binding_width=1.5).body_layout()
    carve = layout.carved_top
    assert carve is not None
    # A ring (12 mm round its route) and the few mm the fall needs off it.
    rings = [
        offset_polygon(pickup.outline, 18.0, inward=False)
        for pickup in (layout.neck_pickup, layout.bridge_pickup)
        if pickup is not None
    ]
    pocket = layout.neck_pocket.outline
    # Halfway into the room the plateau leaves the fall by the edge (along
    # the cutaway, beside the neck pocket), the top is already falling:
    # no wall from the rim straight up to the plateau. Only a pickup's
    # ring stays flat nearer.
    inset = carve.edge_rim + CELL + PLATEAU_EDGE_FALL / 2.0
    checked = 0
    for point in offset_polygon(layout.outline.points, inset, inward=True):
        if point_in_polygon(point, pocket) or any(
            point_in_polygon(point, ring) for ring in rings
        ):
            continue
        assert carve.drop_at(point.x, point.y) > 1.0
        checked += 1
    assert checked > 100
