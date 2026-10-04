"""Tests for the neck-through construction: a centre block and glued wings."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.body import TuneOMaticSpec, body_part, split_by_line
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import NECK_THROUGH_MARGIN
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

THROUGH = replace(Prototype001Parameters(), neck_joint="neck_through")


def area(points) -> float:  # type: ignore[no-untyped-def]
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


def test_a_line_splits_a_polygon_into_its_pieces() -> None:
    # A U: the line across its arms leaves two pieces, not one joined by a
    # zero-width bridge along the line.
    u = tuple(
        Point2D(x, y)
        for x, y in (
            (0, 0),
            (30, 0),
            (30, 30),
            (20, 30),
            (20, 10),
            (10, 10),
            (10, 30),
            (0, 30),
        )
    )
    above = split_by_line(u, 20.0, keep_above=True)
    below = split_by_line(u, 20.0, keep_above=False)
    assert len(above) == 2 and len(below) == 1
    assert sum(abs(area(p)) for p in (*above, *below)) == pytest.approx(abs(area(u)))
    assert all(min(p.y for p in piece) == pytest.approx(20.0) for piece in above)


@pytest.mark.parametrize(
    "parameters",
    [
        THROUGH,
        replace(
            THROUGH,
            body_shape=YOUR_DESIGN_TEMPLATES["les_paul"][1],
            body_bridge=TuneOMaticSpec(),
            truss_rod_adjustment="headstock",
        ),
    ],
)
def test_the_body_splits_into_a_block_and_wings(parameters) -> None:  # type: ignore[no-untyped-def]
    geometry = parameters.build()
    body, through = geometry.body, geometry.neck_through
    assert through is not None
    # No pocket and no bolts: the neck runs on through.
    assert body.neck_pocket is None and not body.rear_holes
    assert {wing.name for wing in through.wings} == {"Wing_bass", "Wing_treble"}
    pieces = (through.block, *through.wings)
    assert sum(abs(area(p.outline)) for p in pieces) == pytest.approx(
        abs(area(body.outline.points)), rel=1e-6
    )
    half = through.width / 2.0
    assert all(abs(p.y) <= half + 1e-6 for p in through.block.outline)
    # Wide enough for the pickups and the bridge, with the margin.
    for pickup in (body.neck_pickup, body.bridge_pickup):
        assert pickup is not None
        assert (
            max(abs(p.y) for p in pickup.outline) <= half - NECK_THROUGH_MARGIN + 1e-6
        )
    # The neck's back reaches the body's thickness where the body begins.
    deepest = {
        round(row[0].x, 3): min(p.z for p in row)
        for row in geometry.neck_surface.mesh.rows
    }
    at_body = [z for x, z in deepest.items() if x >= through.front_x - 1e-6]
    assert at_body and all(z == pytest.approx(-body.thickness) for z in at_body)
    ahead = [z for x, z in deepest.items() if 0.0 < x < through.front_x - 60.0]
    assert all(z > -30.0 for z in ahead)
    # The neck blank's plan runs from the headstock to the tail.
    plan_xs = [p.x for p in through.plan]
    assert min(plan_xs) < 0.0 < max(plan_xs)
    assert max(plan_xs) == pytest.approx(max(p.x for p in through.block.outline))


def test_a_neck_through_refuses_what_it_cannot_take() -> None:
    with pytest.raises(NeckGeometryError, match="neck_angle"):
        replace(THROUGH, neck_angle=2.0).build()
    # A Tune-o-matic's automatic angle is 0 here.
    assert replace(THROUGH, body_bridge=TuneOMaticSpec()).neck_angle_degrees == 0.0
    with pytest.raises(NeckGeometryError, match="buries a heel adjuster"):
        replace(THROUGH, truss_rod_spoke_wheel="no").build()


def test_the_neck_blank_carries_the_block() -> None:
    geometry = THROUGH.build()
    through = geometry.neck_through
    assert through is not None
    machining = MachiningParameters()
    plan = plan_neck_machining(geometry, NeckMachiningParameters(), machining)
    names = [setup.name for setup in plan.setups]
    assert names[:3] == ["Neck_index_pins", "Neck_top", "Neck_block_top"]
    assert names[-1] == "Neck_back_outline"
    assert len(plan.preview_outlines) == len(plan.setups)
    # As thick as the body; the dowels beyond the headstock and the tail.
    assert plan.stock_thickness == geometry.body.thickness
    (front, _), (back, _) = plan.index_pin_positions
    assert front < -geometry.headstock.plan.reach
    assert back > max(p.x for p in through.block.outline)
    # The block's pickup routes are cut on the neck's fixture.
    (top,) = [s for s in plan.setups if s.name == "Neck_block_top"]
    assert any("pickup" in path.name.lower() for path in top.toolpaths)
    assert not any("Outline" in path.name for path in top.toolpaths)
    # The outline is cut full depth round the block's waste.
    (outline,) = plan.back_outline.toolpaths
    cut_levels = sorted({round(m.z, 2) for m in outline.moves if not m.rapid})
    assert cut_levels[-1] < -0.1 and cut_levels[-1] > -4.0
    assert outline.deepest_z() == pytest.approx(
        -(geometry.body.thickness + machining.through_overshoot), abs=0.01
    )


def test_each_wing_has_its_own_blank_and_square_glue_faces() -> None:
    parameters = replace(THROUGH, body_top_binding_width=1.5)
    geometry = parameters.build()
    through = geometry.neck_through
    assert through is not None
    half = through.width / 2.0
    machining = MachiningParameters()
    for wing in through.wings:
        part = body_part(geometry.body, wing)
        ys = [p.y for p in wing.outline]
        axis = (min(ys) + max(ys)) / 2.0
        plan = plan_body_machining(part, machining, prefix=wing.name, pin_axis_y=axis)
        assert all(setup.name.startswith(wing.name) for setup in plan.setups)
        assert all(y == pytest.approx(axis) for _, y in plan.index_pin_positions)
        # The binding runs on past the glue line into the wing's waste, so
        # its channel reaches the glue face and the face stays square.
        (channel,) = [
            path for path in plan.top.toolpaths if path.name == "Top binding channel"
        ]
        origin_y = plan.origin_y
        model_ys = [m.y + origin_y for m in channel.moves if not m.rapid]
        assert min(abs(y) for y in model_ys) < half - 3.0
        # Only features reaching the wing are on it.
        for cavity in part.top_cavities:
            assert any(
                point_in_polygon(p, wing.outline) for p in cavity.outline
            ) or any(point_in_polygon(p, cavity.outline) for p in wing.outline)


def test_the_model_and_the_editor() -> None:
    geometry = THROUGH.build()
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "neck pocket cut" not in source
    assert '"Neck_block"' in source
    assert '"Wing_bass"' in source and '"Wing_treble"' in source
    assert "body_feature = document.addObject" not in source
    layout = body_editor_layout({"prototype": {"neck_joint": "neck_through"}})
    assert layout["neck_through"]["width"] == pytest.approx(
        geometry.neck_through.width,
        abs=0.01,  # type: ignore[union-attr]
    )
    assert not any(polygon["name"] == "Neck pocket" for polygon in layout["polygons"])
    assert body_editor_layout({"prototype": {}})["neck_through"] is None
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["neck_joint"]["options"] == ["bolt_on", "neck_through"]
    assert not fields["neck_joint"]["advanced"]
