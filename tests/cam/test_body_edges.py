"""Tests for the body's edge-finish programs."""

import ast
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.cam.body_edges import roundover_path
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES

STRAT = YOUR_DESIGN_TEMPLATES["stratocaster"][1]


@pytest.fixture(scope="module")
def edged():  # type: ignore[no-untyped-def]
    parameters = replace(
        Prototype001Parameters(),
        body_shape=STRAT,
        body_top_edge_radius=6.0,
        body_back_edge_radius=6.0,
        body_arm_contour_depth=12.0,
        body_belly_cut_depth=12.0,
    )
    geometry = parameters.build()
    return geometry, plan_body_machining(geometry.body, MachiningParameters())


def test_each_face_gets_a_ball_nose_program(edged) -> None:  # type: ignore[no-untyped-def]
    _, plan = edged
    names = [setup.name for setup in plan.setups]

    assert names == [
        "Body_index_pins",
        "Body_top",
        "Body_top_edges",
        "Body_back",
        "Body_back_controls",
        "Body_back_small_holes",
        "Body_back_edges",
    ]
    assert len(plan.preview_outlines) == len(names)
    for setup in (plan.top_edges, plan.back_edges):
        assert setup is not None and setup.tool is not None
        assert setup.tool.tool_tip == "ball"
    assert [path.name for path in plan.top_edges.toolpaths] == [
        "Arm contour roughing",
        "Arm contour finishing",
        "Top edge roundover",
    ]
    assert [path.name for path in plan.back_edges.toolpaths] == [
        "Belly cut roughing",
        "Belly cut finishing",
        "Back edge roundover",
    ]


def test_edge_programs_stay_in_the_outline_slot_and_above_the_tabs(edged) -> None:  # type: ignore[no-untyped-def]
    geometry, plan = edged
    parameters = MachiningParameters()
    half = geometry.body.thickness / 2.0 + parameters.profile_overlap

    top_low = min(m.z for p in plan.top_edges.toolpaths for m in p.moves)
    back_low = min(m.z for p in plan.back_edges.toolpaths for m in p.moves)
    assert -half - 1e-9 <= top_low < -12.0
    assert back_low >= -(half - parameters.tab_height - 0.5) - 1e-9


def test_a_roundover_sweeps_from_the_face_down_to_the_wall() -> None:
    square = (
        Point2D(0.0, 0.0),
        Point2D(100.0, 0.0),
        Point2D(100.0, 100.0),
        Point2D(0.0, 100.0),
    )
    ball = replace(MachiningParameters(), tool_tip="ball")
    path = roundover_path("Round", square, 6.0, ball, lambda point: 0.0)
    cuts = [move for move in path.moves if not move.rapid]

    # The deepest pass runs outside the edge by the ball's radius, its
    # tip a ball radius below the fillet's end.
    assert min(move.z for move in cuts) == pytest.approx(-9.0)
    deepest = [move for move in cuts if move.z == pytest.approx(-9.0)]
    assert min(move.x for move in deepest) == pytest.approx(-3.0, abs=0.01)
    # The first pass barely touches the face, 6 mm in from the edge.
    assert max(move.z for move in cuts) > -0.2


def test_a_binding_channel_is_cut_with_the_main_tool() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_shape=STRAT,
        body_top_binding_width=1.5,
        body_top_binding_depth=6.0,
    )
    plan = plan_body_machining(parameters.build().body, MachiningParameters())
    top_names = [path.name for path in plan.top.toolpaths]

    assert top_names[-1] == "Top binding channel"
    channel = plan.top.toolpaths[-1]
    assert min(move.z for move in channel.moves) == pytest.approx(-6.0)
    assert plan.top_edges is None


def test_the_freecad_script_models_the_finishes(edged) -> None:  # type: ignore[no-untyped-def]
    geometry, _ = edged
    source = FreeCADScriptExporter().render_prototype001(geometry)

    ast.parse(source)
    assert source.count("edge_ring(") >= 2 * 6
    assert "terrace(" in source
    assert "body_shape.cut(edge_cutters)" in source
    plain = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build()
    )
    assert "edge_cutters" not in plain
