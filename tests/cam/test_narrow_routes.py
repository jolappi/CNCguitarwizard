"""Tests for routes too narrow for a wide main tool: the body's wire
channels and truss-rod access under a 12 mm end mill, cut with the small
end mill in the face's small-drill program instead."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    MachiningParameters,
    plan_body_machining,
    plan_feature_machining,
)
from cncguitarwizard.cam.body import BodyMachiningPlan
from cncguitarwizard.cam.planar import disc_fits
from cncguitarwizard.cam.toolpath import Toolpath
from cncguitarwizard.geometry.body import BodySolid, TracedCavity
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.styles import STYLES

WIDE = MachiningParameters(tool_diameter=12.0)
"""A 12 mm end mill at 6 mm a pass: too wide for a wire channel."""


def _style(name: str) -> Prototype001Parameters:
    style = STYLES[name]
    return Prototype001Parameters(**style.prototype_values(style.instruments[0]))


def _path(paths: tuple[Toolpath, ...], name: str) -> Toolpath:
    return next(path for path in paths if path.name == name)


def _stays_inside(
    path: Toolpath,
    outline: tuple[Point2D, ...],
    plan: BodyMachiningPlan,
    radius: float,
    *,
    mirror: bool = False,
) -> bool:
    """Return whether every cut in the wood keeps the cutter inside
    ``outline`` (in the model frame)."""
    sign = -1.0 if mirror else 1.0
    return all(
        disc_fits(
            Point2D(move.x + plan.origin_x, plan.origin_y + sign * move.y),
            outline,
            radius - 1e-6,
        )
        for move in path.moves
        if not move.rapid and move.z < 0.0
    )


@pytest.fixture(scope="module")
def body() -> BodySolid:
    return Prototype001Parameters().build().body


def test_a_route_the_main_tool_fits_nowhere_in_goes_to_the_small_end_mill(
    body: BodySolid,
) -> None:
    plan = plan_body_machining(body, WIDE)

    assert "Truss rod access" not in [path.name for path in plan.top.toolpaths]
    small = plan.top_small_holes
    assert small is not None and small.tool is not None
    assert small.tool.tool_diameter == 3.0
    # The route first, then the holes, which may start at its floor.
    assert small.toolpaths[0].name == "Truss rod access"
    assert small.description == (
        "Body top face - narrow routes and holes for the 3 mm end mill"
    )
    assert "change to the small end mill" in small.notes[0]
    assert (
        "Too narrow for the 12 mm end mill, cut in Body_top_small_holes with "
        "the 3 mm one: Truss rod access." in plan.top.notes
    )
    access = next(c for c in body.top_cavities if c.name == "Truss rod access")
    route = small.toolpaths[0]
    assert route.deepest_z() == pytest.approx(-access.depth)
    assert _stays_inside(route, access.outline, plan, 1.5)
    assert len(plan.preview_outlines) == len(plan.setups)


def test_the_main_tool_keeps_every_route_it_fits_in(body: BodySolid) -> None:
    plan = plan_body_machining(body, MachiningParameters())

    assert "Truss rod access" in [path.name for path in plan.top.toolpaths]
    assert plan.top_small_holes is None
    assert not any(
        note.startswith("Too narrow") for setup in plan.setups for note in setup.notes
    )


def test_a_stratocaster_s_wire_channels_are_cut_with_the_small_end_mill() -> None:
    # Regression: a 12 mm main tool stopped the plan ("Bridge pickup wire
    # channel is too narrow for a 12.0 mm tool").
    body = _style("stratocaster").build().body
    plan = plan_body_machining(body, WIDE)

    channels = [
        "Bridge pickup wire channel",
        "Middle pickup wire channel",
        "Neck pickup wire channel",
    ]
    assert plan.top_small_holes is not None
    names = [path.name for path in plan.top_small_holes.toolpaths]
    assert names[:3] == channels
    assert not set(channels) & {path.name for path in plan.top.toolpaths}
    for name in channels:
        cavity = next(c for c in body.top_cavities if c.name == name)
        path = _path(plan.top_small_holes.toolpaths, name)
        assert path.deepest_z() == pytest.approx(-cavity.depth)
        assert _stays_inside(path, cavity.outline, plan, 1.5)


def test_a_narrow_rear_step_is_cut_from_the_back_with_the_small_end_mill(
    body: BodySolid,
) -> None:
    rear = body.control_cavity
    assert rear is not None
    xs = [point.x for point in rear.cavity.outline]
    ys = [point.y for point in rear.cavity.outline]
    x, y = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    slot = (
        Point2D(x - 15.0, y - 4.0),
        Point2D(x + 15.0, y - 4.0),
        Point2D(x + 15.0, y + 4.0),
        Point2D(x - 15.0, y + 4.0),
    )
    step = TracedCavity("Wire slot", slot, rear.cavity.depth + 3.0)
    narrowed = replace(body, control_cavity=replace(rear, steps=(step,)))
    plan = plan_body_machining(narrowed, WIDE)

    assert plan.back_controls is not None
    assert "Wire slot" not in [path.name for path in plan.back_controls.toolpaths]
    small = plan.back_small_holes
    assert small is not None
    assert small.toolpaths[0].name == "Wire slot"
    assert small.description.startswith("Body back face - narrow routes")
    assert any("Wire slot" in note for note in plan.back.notes)
    path = small.toolpaths[0]
    # From the cavity's floor, cut first by Body_back_controls.
    cuts = [move.z for move in path.moves if not move.rapid]
    assert max(cuts) <= -rear.cavity.depth + 1e-9
    assert path.deepest_z() == pytest.approx(-step.depth)
    assert _stays_inside(path, slot, plan, 1.5, mirror=True)


def test_a_les_paul_s_core_channels_get_a_small_end_mill_program() -> None:
    les_paul = _style("les_paul")
    body = les_paul.build().body
    plan = plan_body_machining(body, WIDE)

    # Its wire channels alone, every one too narrow: no Body_core_top.
    names = [setup.name for setup in plan.setups]
    assert names[:3] == [
        "Body_core_index_pins",
        "Body_core_small_routes",
        "Body_index_pins",
    ]
    assert plan.core_top is None
    small = plan.core_small_routes
    assert small is not None and small.tool is not None
    assert small.tool.tool_diameter == 3.0
    assert [path.name for path in small.toolpaths] == [
        cavity.name for cavity in body.core_cavities
    ]
    assert "Body_core_small_routes" in plan.setups[0].notes[-1]
    assert any("glue the 15.875 mm top on" in note for note in small.notes)
    assert len(plan.preview_outlines) == len(plan.setups)

    # Chambered: the chambers with the main tool, the top glued on after
    # the small end mill's channels.
    chambered = plan_body_machining(
        replace(les_paul, body_chambers=True).build().body, WIDE
    )
    assert chambered.core_top is not None
    assert chambered.core_small_routes is not None
    assert [setup.name for setup in chambered.setups][:3] == [
        "Body_core_index_pins",
        "Body_core_top",
        "Body_core_small_routes",
    ]
    assert all(path.name.startswith("Chamber") for path in chambered.core_top.toolpaths)
    assert any(
        note.startswith("Too narrow") and "Body_core_small_routes" in note
        for note in chambered.core_top.notes
    )
    assert not any("glue" in note for note in chambered.core_top.notes)
    assert any("glue" in note for note in chambered.core_small_routes.notes)


def test_a_feature_s_narrow_route_goes_to_its_small_program() -> None:
    geometry = _style("stratocaster").build()
    setups = plan_feature_machining(
        geometry.body,
        geometry.covers,
        lambda name: name.startswith("Bridge pickup"),
        "bridge pickup",
        WIDE,
    )

    by_name = {setup.name: setup for setup in setups}
    top = by_name["Feature_bridge_pickup_top"]
    small = by_name["Feature_bridge_pickup_top_small_holes"]
    assert "Bridge pickup route" in [path.name for path in top.toolpaths]
    assert "Bridge pickup wire channel" not in [path.name for path in top.toolpaths]
    assert small.toolpaths[0].name == "Bridge pickup wire channel"
    assert small.description.endswith("top face, narrow routes and small holes")
    assert "change to the small end mill" in small.notes[0]
