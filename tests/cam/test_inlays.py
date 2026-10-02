"""Tests for the sheet program that cuts the marker inlay pieces."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    ToolpathError,
    inlay_fit_outline,
    offset_polygon,
    plan_inlay_machining,
)
from cncguitarwizard.cam.inlays import INLAY_FIT_CLEARANCE, _piece_outline
from cncguitarwizard.cam.planar import (
    distance_to_boundary,
    polygon_bounds,
    signed_area,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters


def layout(style: str):  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), inlay_style=style).build().inlay_layout


def square(side: float) -> tuple[Point2D, ...]:
    return (
        Point2D(0.0, 0.0),
        Point2D(side, 0.0),
        Point2D(side, side),
        Point2D(0.0, side),
    )


def test_round_dots_get_no_program() -> None:
    assert plan_inlay_machining(layout("dot"), FretboardMachiningParameters()) is None


@pytest.mark.parametrize("style", ["barbed_wire", "block"])
def test_every_marker_is_cut_through_the_sheet(style: str) -> None:
    markers = layout(style)
    parameters = FretboardMachiningParameters()
    plan = plan_inlay_machining(markers, parameters)
    assert plan is not None

    (setup,) = plan.setups
    assert setup.name == "Fretboard_inlay_pieces"
    assert setup.tool is parameters.inlay
    assert len(setup.toolpaths) == len(markers.markers)
    assert setup.toolpaths[0].name.startswith(
        f"Inlay fret {markers.markers[0].fret_number} at y="
    )
    assert plan.stock_thickness == markers.depth
    assert plan.index_pin_positions == ()
    through = markers.depth + parameters.inlay.through_overshoot
    for path in setup.toolpaths:
        assert path.deepest_z() == pytest.approx(-through)
    # The pieces lie apart on the sheet, all inside it.
    boxes = [
        polygon_bounds([Point2D(move.x, move.y) for move in path.moves])
        for path in setup.toolpaths
    ]
    for index, first in enumerate(boxes):
        assert abs(first[0]) < plan.stock_length / 2.0
        assert abs(first[2]) < plan.stock_length / 2.0
        assert abs(first[1]) < plan.stock_width / 2.0
        assert abs(first[3]) < plan.stock_width / 2.0
        for second in boxes[index + 1 :]:
            assert (
                first[2] <= second[0]
                or second[2] <= first[0]
                or first[3] <= second[1]
                or second[3] <= first[1]
            )


def test_a_piece_is_its_pocket_less_the_clearance() -> None:
    radius = FretboardMachiningParameters().inlay.tool_radius
    for marker in layout("barbed_wire").markers[:2]:
        pocket = inlay_fit_outline(marker.outline, radius)
        piece = _piece_outline(marker, radius)
        for point in piece:
            assert point_in_polygon(point, pocket)
            assert distance_to_boundary(point, pocket) > INLAY_FIT_CLEARANCE - 0.01
        # The pocket only reaches past the marker into its inner corners.
        for point in pocket:
            assert (
                point_in_polygon(point, marker.outline)
                or distance_to_boundary(point, marker.outline) < radius
            )


def test_the_fit_outline_rounds_corners_both_ways() -> None:
    # A square loses its corners to the tool radius ...
    fitted = inlay_fit_outline(square(10.0), 1.0)
    assert abs(signed_area(fitted)) == pytest.approx(100.0 - (4.0 - math.pi), abs=0.1)
    assert min(math.hypot(p.x, p.y) for p in fitted) == pytest.approx(
        math.sqrt(2.0) - 1.0, abs=0.02
    )
    # ... and an L's inner corner is filled where the tool cannot reach.
    ell = (
        Point2D(0.0, 0.0),
        Point2D(10.0, 0.0),
        Point2D(10.0, 4.0),
        Point2D(4.0, 4.0),
        Point2D(4.0, 10.0),
        Point2D(0.0, 10.0),
    )
    fitted = inlay_fit_outline(ell, 1.0)
    assert point_in_polygon(Point2D(4.1, 4.1), fitted)


def test_a_marker_narrower_than_the_tool_is_rejected() -> None:
    sliver = (Point2D(0.0, 0.0), Point2D(10.0, 0.0), Point2D(10.0, 0.5))
    with pytest.raises(ToolpathError):
        inlay_fit_outline(sliver, 0.5)


def test_an_inward_offset_keeps_a_sampled_round_corner() -> None:
    # A circle sampled with edges shorter than the sample spacing: every
    # offset vertex comes from where the shifted edges cross.
    circle = tuple(
        Point2D(
            3.0 * math.cos(2.0 * math.pi * k / 24),
            3.0 * math.sin(2.0 * math.pi * k / 24),
        )
        for k in range(24)
    )
    offset = offset_polygon(circle, 1.0, inward=True)
    assert len(offset) >= 24
    assert max(math.hypot(p.x, p.y) for p in offset) == pytest.approx(
        3.0 - 1.0 / math.cos(math.pi / 24), abs=1e-6
    )
