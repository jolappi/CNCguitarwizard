"""Tests for the sheet programs that cut the cavity covers."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    GRBLWriter,
    MachiningParameters,
    cover_setup_name,
    plan_cover_machining,
)
from cncguitarwizard.geometry.body import CoverPlate
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters


def covers(layout: str) -> tuple[CoverPlate, ...]:
    parameters = replace(Prototype001Parameters(), body_controls=layout)
    return parameters.build().covers


def test_no_covers_means_no_plan() -> None:
    assert plan_cover_machining((), MachiningParameters()) is None


def test_each_cover_gets_its_own_small_tool_program() -> None:
    plan = plan_cover_machining(covers("gibson_4"), MachiningParameters())
    assert plan is not None

    assert [setup.name for setup in plan.setups] == [
        "Cover_control_cavity",
        "Cover_switch_cavity",
    ]
    assert len(plan.preview_outlines) == 2
    assert plan.index_pin_positions == ()
    assert plan.stock_thickness == 2.0
    for setup in plan.setups:
        assert setup.tool is not None and setup.tool.tool_diameter == 3.0
        assert setup.work_zero is not None
        names = [path.name for path in setup.toolpaths]
        assert names[-1].endswith("outline")
        assert all("Screw" in name for name in names[:-1])
        # Everything cuts through the 2 mm sheet and no deeper than needed.
        lowest = min(move.z for path in setup.toolpaths for move in path.moves)
        assert lowest == pytest.approx(-2.5)


def test_back_covers_are_cut_as_seen_from_the_back() -> None:
    (control, _) = covers("gibson_4")
    plan = plan_cover_machining((control,), MachiningParameters())
    assert plan is not None
    setup = plan.setups[0]

    # The frame is centred on the cover and flipped in Y.
    ys = [hole.center_y for hole in control.holes]
    centre_y = (
        min(p.y for p in control.outline) + max(p.y for p in control.outline)
    ) / 2.0
    first = setup.toolpaths[0].moves[0]
    assert first.y == pytest.approx(-(ys[0] - centre_y))


def test_the_tele_plate_carries_pot_holes_and_a_switch_slot() -> None:
    (plate,) = covers("tele")
    plan = plan_cover_machining((plate,), MachiningParameters())
    assert plan is not None
    setup = plan.setups[0]
    names = [path.name for path in setup.toolpaths]

    assert setup.name == cover_setup_name(plate) == "Cover_control_plate"
    assert "Control plate - Blade switch slot" in names
    assert "Control plate - Pot 1 shaft hole" in names
    # The outline is cut inside the plate's own shape (a fit clearance).
    xs = [p.x for p in plate.outline]
    ys = [p.y for p in plate.outline]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    plate_frame = tuple(Point2D(p.x - cx, p.y - cy) for p in plate.outline)
    assert all(
        point_in_polygon(point, plate_frame) for point in plan.preview_outlines[0]
    )
    source = GRBLWriter().render(setup, MachiningParameters())
    assert "(Work zero: the centre of the cover, Z at the sheet top)" in source
    assert "index pin" not in source
