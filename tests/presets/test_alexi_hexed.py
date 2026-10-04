"""Tests for the ESP LTD Alexi Hexed style template, the stepped top and
the pinstripe."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.cam.body import plan_body_machining
from cncguitarwizard.cam.planar import distance_to_boundary, offset_polygon
from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.engraving import PINSTRIPE_INSET
from cncguitarwizard.presets.prototype001 import BODY_TEMPLATE_VALUES
from cncguitarwizard.render.svg import render_plan_view_svg
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

LABEL, HEXED = YOUR_DESIGN_TEMPLATES["alexi_hexed"]
ALEXI = replace(
    Prototype001Parameters(), body_shape=HEXED, **BODY_TEMPLATE_VALUES["alexi_hexed"]
)


def test_the_template_is_the_rr_outline_with_the_hexed_look() -> None:
    assert LABEL == "ESP LTD Alexi Hexed style (mockup, not the original)"
    rr = YOUR_DESIGN_TEMPLATES["jackson_rr"][1]
    assert HEXED.control_points == rr.control_points
    assert HEXED.pickguard_points == ()
    values = BODY_TEMPLATE_VALUES["alexi_hexed"]
    assert values["body_pickups"] == "H"
    assert values["body_controls"] == "volume_1"
    assert isinstance(values["body_bridge"], FloydRoseSpec)
    assert values["body_stepped_top"] is True
    assert values["body_top_step_insets"] == (12.0, 40.0)
    assert values["body_top_step_height"] == 1.5
    # Only the alexi_hexed template sets anything besides its shape.
    assert set(BODY_TEMPLATE_VALUES) == {"alexi_hexed"}


def test_the_hexed_has_one_humbucker_one_knob_and_a_floyd_rose() -> None:
    geometry = ALEXI.build()
    body = geometry.body
    assert body.bridge_pickup is not None and body.neck_pickup is None
    pots = [hole for hole in body.holes if hole.name.startswith("Control pot")]
    assert len(pots) == 1 and body.switch_cavity is None
    assert body.bridge_mounting.pivot_stud_spacing == pytest.approx(73.91)
    assert geometry.locking_nut is not None  # the Floyd Rose's R2


def test_the_template_draws_its_steps_with_straight_tails() -> None:
    body = ALEXI.build().body
    steps = body.stepped_top
    assert steps is not None and steps.depth == 3.0
    heel_end = ALEXI.body_layout().heel_end
    # The drawn lines, straight between their points.
    assert [
        [(round(p.x - heel_end, 1), round(p.y, 1)) for p in boundary]
        for boundary in steps.boundaries
    ] == [list(line) for line in HEXED.step_points]
    outer, inner = HEXED.step_points
    # Two nested arrows, each tail a sharp V at the notch, the inner
    # one's point 4 mm inside the outer's.
    points = [
        next(p for p in line if p[0] > 100.0 and abs(p[1]) < 100.0)
        for line in (outer, inner)
    ]
    assert points == [(219.2, 14.8), (215.4, 13.1)]
    # Beside the neck they converge on the edge, the treble horn's the
    # bass horn's mirror image.
    for line in (outer, inner):
        bass = next(p for p in line if p[0] < 0.0 and p[1] < -30.0)
        assert (bass[0], -bass[1]) in line
    assert distance_to_boundary(
        steps.boundaries[1][3], steps.boundaries[0]
    ) == pytest.approx(4.16, abs=0.05)
    # Full height round the pickup and the bridge, a step down in the
    # middle band, two at the edge.
    pickup = body.bridge_pickup
    assert pickup is not None
    assert all(body.top_drop_at(p.x, p.y) == 0.0 for p in pickup.outline)
    near_edge = next(
        p
        for p in offset_polygon(body.outline.points, 5.0, inward=True)
        if p.x > heel_end + 250.0 and p.y < -100.0
    )
    assert body.top_drop_at(near_edge.x, near_edge.y) == 3.0
    assert body.top_drop_at(heel_end + 217.3, 14.0) == 1.5
    assert body.top_edge_drop == 3.0
    # The volume pot's cavity keeps its top wall under the lowered band.
    rear = body.control_cavity
    assert rear is not None
    drop = max(body.top_drop_at(p.x, p.y) for p in rear.cavity.outline)
    assert drop > 0.0
    assert body.thickness - drop - rear.cavity.depth == pytest.approx(
        ALEXI.body_rear_cavity_top_wall
    )


def test_undrawn_steps_follow_the_edge() -> None:
    automatic = replace(ALEXI, body_shape=replace(HEXED, step_points=()))
    body = automatic.build().body
    steps = body.stepped_top
    assert steps is not None
    outline = body.outline.points
    for inset, boundary in zip((12.0, 40.0), steps.boundaries, strict=True):
        for point in boundary[:: len(boundary) // 30]:
            assert distance_to_boundary(point, outline) == pytest.approx(inset, abs=0.3)
    with pytest.raises(BodyGeometryError, match="further in than the last"):
        replace(automatic, body_top_step_insets=(40.0, 12.0)).build()
    with pytest.raises(BodyGeometryError, match="reaches the pickups or the bridge"):
        replace(automatic, body_top_step_insets=(12.0, 70.0)).build()


def test_the_steps_are_cut_true_and_modelled() -> None:
    geometry = ALEXI.build()
    body = geometry.body
    steps = body.stepped_top
    assert steps is not None
    parameters = MachiningParameters()
    plan = plan_body_machining(body, parameters)
    names = [setup.name for setup in plan.setups]
    assert names[:3] == ["Body_index_pins", "Body_top_steps", "Body_top"]
    setup = plan.top_steps
    assert setup is not None
    inner, outer = setup.toolpaths
    assert inner.deepest_z() == pytest.approx(-1.5)
    assert outer.deepest_z() == pytest.approx(-3.0)
    outline = body.outline.points
    radius = parameters.tool_radius
    for path, boundary in ((inner, steps.boundaries[1]), (outer, steps.boundaries[0])):
        cuts = [
            Point2D(move.x + plan.origin_x, move.y + plan.origin_y)
            for move in path.moves
            if not move.rapid and move.z < 0.0
        ][::20]
        assert cuts
        for point in cuts:
            # In the body, the tool never over the step's higher side.
            assert point_in_polygon(point, outline)
            assert distance_to_boundary(point, outline) >= radius - 0.4
            assert not point_in_polygon(point, boundary)
            assert distance_to_boundary(point, boundary) >= radius - 0.4
        # The wall: the last pass runs round the step a radius out.
        assert any(
            distance_to_boundary(point, boundary) == pytest.approx(radius, abs=0.2)
            for point in cuts
        )
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert source.count("stepped top step") == 2
    assert render_plan_view_svg(geometry).count('stroke="#6a4a8a"') == 2


def test_a_stepped_top_refuses_what_does_not_go_with_it() -> None:
    with pytest.raises(BodyGeometryError, match="either carved or stepped"):
        replace(ALEXI, body_carved_top=True).build()
    with pytest.raises(BodyGeometryError, match="pickguard does not lie flat"):
        replace(ALEXI, body_pickguard=True).build()
    # Drawn steps must nest without crossing (inside the body, away from
    # its edge and the neck pocket).
    outer = list(HEXED.step_points[0])
    outer[3] = (213.7, 16.4)
    crossing = replace(HEXED, step_points=(tuple(outer), HEXED.step_points[1]))
    with pytest.raises(BodyGeometryError, match="without crossing it"):
        replace(ALEXI, body_shape=crossing).body_layout()
    # A point that is not two numbers (a hole left in the list) says so.
    broken = replace(
        HEXED, step_points=((*HEXED.step_points[0][:3], None), HEXED.step_points[1])
    )
    with pytest.raises(BodyGeometryError, match="not two numbers"):
        replace(ALEXI, body_shape=broken).body_layout()
    with pytest.raises(BodyGeometryError, match="quarter of the body"):
        replace(ALEXI, body_top_step_height=6.0).build()
    narrow = replace(
        ALEXI,
        body_shape=replace(HEXED, step_points=()),
        body_top_step_insets=(2.0, 40.0),
    ).build()
    with pytest.raises(Exception, match="leaves no band the"):
        plan_body_machining(narrow.body, MachiningParameters())
    # Any body takes it, its steps clear of the pickups and the bridge.
    strat = YOUR_DESIGN_TEMPLATES["stratocaster"][1]
    plain = replace(
        Prototype001Parameters(),
        body_shape=strat,
        body_stepped_top=True,
        body_top_step_insets=(8.0, 18.0),
    ).build()
    assert plain.body.stepped_top is not None
    # The editor draws the steps wherever they fall.
    assert (
        replace(Prototype001Parameters(), body_shape=strat, body_stepped_top=True)
        .body_layout()
        .stepped_top
        is not None
    )


def test_the_pinstripe_runs_round_the_edge_just_inside_the_margin() -> None:
    pinstripe = replace(
        ALEXI,
        body_stepped_top=False,
        body_engraving=True,
        body_engraving_pattern="pinstripe",
        body_engraving_depth=1.0,
    )
    body = pinstripe.build().body
    engraving = body.engraving
    assert engraving is not None
    outline = body.outline.points
    margin = pinstripe.body_engraving_margin
    length = 0.0
    for line in engraving.lines:
        for point in line[:: max(1, len(line) // 40)]:
            assert point_in_polygon(point, outline)
            assert distance_to_boundary(point, outline) == pytest.approx(
                margin + PINSTRIPE_INSET, abs=0.6
            )
        length += sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(line, line[1:]))
    # Most of the way round: broken only where something is in its way.
    perimeter = sum(
        math.hypot(b.x - a.x, b.y - a.y)
        for a, b in zip(outline, (*outline[1:], outline[0]))
    )
    assert 0.6 * perimeter < length < perimeter
    pocket = body.neck_pocket
    assert pocket is not None
    assert not any(
        point_in_polygon(point, pocket.outline)
        for line in engraving.lines
        for point in line
    )


def test_the_editor_draws_the_steps_with_handles() -> None:
    def layout(shape):  # type: ignore[no-untyped-def]
        return body_editor_layout(
            {
                "prototype": {
                    "body_shape": {
                        "kind": "your_design",
                        "control_points": [list(p) for p in shape.control_points],
                        "step_points": [
                            [list(p) for p in line] for line in shape.step_points
                        ],
                    },
                    "body_stepped_top": True,
                    "body_pickups": "H",
                    "body_controls": "volume_1",
                    "body_bridge": {"kind": "floyd_rose"},
                }
            }
        )

    drawn = layout(HEXED)
    assert drawn["steps"]["automatic"] is False
    assert drawn["steps"]["points"] == [
        [list(p) for p in line] for line in HEXED.step_points
    ]
    automatic = layout(replace(HEXED, step_points=()))
    assert automatic["steps"]["automatic"] is True
    # Simplified to a handful of handles each.
    assert [len(line) for line in automatic["steps"]["points"]] < [60, 60]
    assert all(polygon["role"] != "step" for polygon in drawn["polygons"])
    hexed = drawn["templates"]["alexi_hexed"]
    assert hexed["values"]["body_stepped_top"] is True
    assert hexed["shape"]["step_points"][0][3] == [219.2, 14.8]
    assert drawn["templates"]["jackson_rr"]["values"] == {}
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert "Alexi Hexed" in fields["body_engraving_pattern"]["labels"]["pinstripe"]
    assert not fields["body_stepped_top"]["advanced"]
    assert "Alexi Hexed" in fields["body_stepped_top"]["help"]
