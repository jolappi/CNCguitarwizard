"""Tests for the single-sided fretboard machining plan on Prototype001."""

import math

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    ToolpathError,
    fretboard_outline_polygon,
    plan_fretboard_machining,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters


@pytest.fixture(scope="module")
def geometry():  # type: ignore[no-untyped-def]
    return Prototype001Parameters().build()


@pytest.fixture(scope="module")
def parameters() -> FretboardMachiningParameters:
    return FretboardMachiningParameters()


@pytest.fixture(scope="module")
def plan(geometry, parameters):  # type: ignore[no-untyped-def]
    return plan_fretboard_machining(geometry, parameters)


def test_outline_is_the_tapered_board_with_rounded_nut_corners(geometry) -> None:  # type: ignore[no-untyped-def]
    polygon = fretboard_outline_polygon(geometry)

    assert min(point.x for point in polygon) == pytest.approx(0.0)
    assert max(point.x for point in polygon) == pytest.approx(461.2)
    assert max(point.y for point in polygon) == pytest.approx(28.06, abs=0.01)
    # The nut corners are rounded: nothing reaches (0, 21).
    assert all(math.hypot(point.x, abs(point.y) - 21.0) > 2.0 for point in polygon)
    assert point_in_polygon(Point2D(230.0, 0.0), polygon)


def test_plan_has_five_setups_in_tool_order(plan, parameters) -> None:  # type: ignore[no-untyped-def]
    assert [setup.name for setup in plan.setups] == [
        "Fretboard_index_pins",
        "Fretboard_radius",
        "Fretboard_inlays",
        "Fretboard_slots",
        "Fretboard_outline",
    ]
    assert plan.radius.tool is parameters.ball
    assert plan.inlays.tool is parameters.inlay
    assert plan.slots.tool is parameters.slot
    assert len(plan.inlays.toolpaths) == 12
    assert len(plan.slots.toolpaths) == 24


def test_radius_surface_sits_at_the_crown_and_drops_toward_the_edges(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    skim = parameters.blank_thickness - geometry.fretboard_surface.center_thickness
    origin_y = plan.origin_y
    moves = [move for move in plan.radius.toolpaths[0].moves if not move.rapid]

    def expected(model_y: float) -> float:
        return -(skim + 430.0 - math.sqrt(430.0**2 - model_y**2))

    crown = min(moves, key=lambda move: abs(move.y + origin_y))
    assert abs(crown.y + origin_y) < 0.6
    assert crown.z == pytest.approx(expected(crown.y + origin_y), abs=0.01)
    edge = [move for move in moves if abs(abs(move.y + origin_y) - 28.0) < 0.6]
    assert edge
    # Never below the surface; the pass itself sits on it (the link moves
    # between passes hover a little higher).
    for move in edge:
        assert move.z >= expected(move.y + origin_y) - 0.01
    assert min(move.z for move in edge) == pytest.approx(
        expected(edge[0].y + origin_y), abs=0.05
    )
    assert min(move.z for move in edge) < crown.z - 0.8


def test_fret_slots_follow_the_radius_across_the_board(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    skim = parameters.blank_thickness - geometry.fretboard_surface.center_thickness
    depth = geometry.fret_slot_depth
    first = plan.slots.toolpaths[0]
    origin_x, origin_y = plan.index_pin_positions[0]
    cut_moves = [move for move in first.moves if not move.rapid]

    assert first.name == "Fret 1 slot"
    slot_x = geometry.fret_layout.slots[0].start.x
    assert all(abs(move.x + origin_x - slot_x) < 1e-6 for move in cut_moves)
    centre = [move for move in cut_moves if abs(move.y + origin_y) < 0.51]
    assert min(move.z for move in centre) == pytest.approx(-(skim + depth), abs=0.01)
    half = abs(geometry.fret_layout.slots[0].start.y) + parameters.slot_overshoot
    assert max(abs(move.y + origin_y) for move in cut_moves) == pytest.approx(half)
    # Three passes of at most 0.9 mm.
    depths = sorted({round(move.z, 2) for move in centre}, reverse=True)
    assert len(depths) == 3


def test_inlay_pockets_are_cut_from_the_crown_to_their_depth(  # type: ignore[no-untyped-def]
    plan, geometry, parameters
) -> None:
    skim = parameters.blank_thickness - geometry.fretboard_surface.center_thickness
    for path in plan.inlays.toolpaths:
        assert path.deepest_z() == pytest.approx(-(skim + geometry.inlay_layout.depth))


def test_outline_and_pins(plan, geometry, parameters) -> None:  # type: ignore[no-untyped-def]
    polygon = fretboard_outline_polygon(geometry)
    (x1, y1), (x2, y2) = plan.index_pin_positions

    assert x1 < 0.0 and x2 > 461.2 and y1 == 0.0 and y2 == 0.0
    assert plan.outline.toolpaths[0].deepest_z() == pytest.approx(
        -(parameters.blank_thickness + parameters.flat.through_overshoot)
    )
    assert plan.stock_thickness == parameters.blank_thickness
    assert not point_in_polygon(Point2D(x1, y1), polygon)


def test_blank_thinner_than_the_board_is_rejected(geometry) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ToolpathError, match="thick"):
        plan_fretboard_machining(
            geometry, FretboardMachiningParameters(blank_thickness=5.0)
        )
