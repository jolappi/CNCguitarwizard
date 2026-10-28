"""Tests for a one-piece neck: no fretboard of its own, the board cut into
the neck's top and its truss rod laid in from the back
(``fretboard_one_piece``)."""

import ast
import json
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    fretboard_outline_polygon,
    plan_fretboard_machining,
)
from cncguitarwizard.cam.neck import (
    NeckMachiningParameters,
    NeckMachiningPlan,
    neck_plan_polygon,
    plan_neck_machining,
)
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Geometry, Prototype001Parameters
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.render.preview3d import preview_parts
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg
from cncguitarwizard.setting_conditions import APPLIES_WHEN
from cncguitarwizard.webapp import parameter_schema
from cncguitarwizard.workflows import build_prototype001
from cncguitarwizard.workflows.model_check import NECK_PARTS

TELECASTER = replace(
    Prototype001Parameters.for_instrument("electric_guitar"),
    **STYLES["telecaster"].prototype_values("electric_guitar"),
)
ONE_PIECE = replace(TELECASTER, fretboard_one_piece=True)
BOARD = FretboardMachiningParameters()


@cache
def one_piece() -> Prototype001Geometry:
    """Return the Telecaster style's neck in one piece, built."""
    return ONE_PIECE.build()


@cache
def neck_plan() -> NeckMachiningPlan:
    return plan_neck_machining(one_piece(), NeckMachiningParameters(), None, BOARD)


def test_its_truss_rod_always_goes_in_from_the_back() -> None:
    # Set to go in from the top, it goes in from the back all the same.
    assert ONE_PIECE.truss_rod_install == "top"
    assert ONE_PIECE.truss_rod_from_back
    assert not TELECASTER.truss_rod_from_back
    geometry = one_piece()
    assert geometry.fretboard_one_piece
    assert geometry.vintage_truss_rod is not None
    assert geometry.truss_rod_channel.routed_from == "back"


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"truss_rod_spoke_wheel": "yes"}, "one-piece neck's truss rod"),
        ({"headstock_angle": 8.0}, "flat headstock"),
        ({"fretboard_binding_width": 1.5}, "no fretboard of its own to bind"),
        ({"neck_carbon_rods": True}, "a one-piece neck has none"),
    ],
)
def test_what_a_one_piece_neck_cannot_have_is_refused(
    changes: dict[str, object], match: str
) -> None:
    with pytest.raises(NeckGeometryError, match=match):
        replace(ONE_PIECE, **changes).build()  # type: ignore[arg-type]


def test_the_board_is_cut_into_the_neck_blank_first() -> None:
    plan = neck_plan()
    names = [setup.name for setup in plan.setups]
    assert names[:5] == [
        "Neck_index_pins",
        "Neck_fretboard_radius",
        "Neck_fretboard_inlays",
        "Neck_fretboard_slots",
        "Neck_top",
    ]
    assert names.index("Neck_back_truss_rod") < names.index("Neck_back_rough")
    assert len(plan.preview_outlines) == len(plan.setups)
    # The blank reaches up past the glue face by the board's blank, and
    # every through cut goes through that too.
    glued = plan_neck_machining(
        replace(TELECASTER, truss_rod_install="back").build(),
        NeckMachiningParameters(),
    )
    assert plan.stock_thickness == glued.stock_thickness + BOARD.blank_thickness
    for setup_name in ("Neck_index_pins", "Neck_back_outline"):
        (setup,) = [s for s in plan.setups if s.name == setup_name]
        deepest = min(move.z for path in setup.toolpaths for move in path.moves)
        assert deepest == pytest.approx(
            -(plan.stock_thickness + MachiningParameters().through_overshoot)
        )


def test_the_boards_programs_are_the_fretboards_on_the_necks_dowels() -> None:
    plan = neck_plan()
    board = plan_fretboard_machining(
        one_piece(),
        BOARD,
        origin=(plan.origin_x, plan.origin_y),
        reference_points=plan.index_pins.reference_points,
    )
    by_name = {setup.name: setup for setup in plan.setups}
    for setup in (board.radius, board.inlays, board.slots):
        on_neck = by_name[f"Neck_{setup.name[0].lower()}{setup.name[1:]}"]
        assert on_neck.toolpaths == setup.toolpaths
        assert on_neck.fixture == "Neck glue face up on the index pins"
        assert on_neck.description.startswith("One-piece neck: fretboard")


def test_the_top_comes_down_to_the_glue_face_round_the_board() -> None:
    plan = neck_plan()
    geometry = one_piece()
    (around,) = [
        path
        for path in plan.top.toolpaths
        if path.name == "Round the fretboard, down to the glue face"
    ]
    cuts = [
        Point2D(move.x + plan.origin_x, move.y + plan.origin_y)
        for move in around.moves
        if not move.rapid
    ]
    deepest = min(move.z for move in around.moves)
    assert deepest == pytest.approx(-BOARD.blank_thickness)
    # Round the board's nut end (the nut's seat, the headstock, its root
    # where it widens past the board), never beside it: the waste there
    # is left whole.
    board = fretboard_outline_polygon(geometry)
    front = min(point.x for point in board)
    assert not any(point_in_polygon(point, board) for point in cuts)
    assert all(point.x < front + 10.0 for point in cuts)
    assert min(p.x for p in cuts) < min(p.x for p in neck_plan_polygon(geometry))
    assert any("untouched top beside the board" in note for note in plan.top.notes)
    assert (
        plan.top.notes[0] == "Blank on the two index pins, its top up, same work zero."
    )


def test_the_model_fuses_the_board_into_the_neck() -> None:
    source = FreeCADScriptExporter().render_prototype001(
        one_piece(), step_path=Path("Prototype001.step")
    )
    ast.parse(source)
    assert "neck_feature.Shape.fuse(fretboard_feature.Shape)" in source
    assert "document.removeObject(fretboard_feature.Name)" in source
    # Only the neck is exported, the board in it; the model check then
    # asks for no fretboard of its own.
    (export,) = [line for line in source.splitlines() if "Part.export(" in line]
    assert "neck_feature" in export and "fretboard_feature" not in export
    assert NECK_PARTS == ("NeckBack", "Fretboard")


def test_the_previews_draw_the_board_in_the_necks_wood() -> None:
    geometry = one_piece()
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    names = [part.name for part in preview_parts(geometry, rows)]
    assert "Fretboard" not in names and "Neck" in names
    svg = render_plan_view_svg(geometry)
    board = svg.split("<title>Fretboard</title>")[0].rsplit("<path", 1)[1]
    assert 'fill="#f1e4c8"' in board


def test_the_form_offers_it_and_hides_what_it_rules_out() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    field = fields["fretboard_one_piece"]
    assert field["type"] == "bool" and not field["advanced"]
    assert "from the back" in field["help"]
    for name in ("truss_rod_install", "fretboard_binding_width", "neck_carbon_rods"):
        assert APPLIES_WHEN[name] == ({"fretboard_one_piece": (False,)},)


def test_the_build_makes_no_fretboard_programs(tmp_path: Path) -> None:
    result = build_prototype001(tmp_path / "output", ONE_PIECE, run_freecad=False)
    names = [path.name for path in result.gcode_paths]
    assert not any(name.startswith("Fretboard_") for name in names)
    assert "Neck_fretboard_radius_6mm_ballnose.nc" in names
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert "Fretboard" not in report["stock"]
    assert report["gcode"]["Neck_fretboard_slots"]["part"] == "Neck"
