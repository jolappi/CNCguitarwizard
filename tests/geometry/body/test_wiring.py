"""Tests for the wire channels and holes between the electronics cavities."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.cam.body import plan_body_machining
from cncguitarwizard.geometry.body import (
    BodySolid,
    BridgeSpec,
    FloydRoseSpec,
    HardtailSpec,
    TuneOMaticSpec,
)
from cncguitarwizard.geometry.body.wiring import (
    GROUND_HOLE_DIAMETER,
    WIRE_CHANNEL_WIDTH,
    WIRE_HOLE_DIAMETER,
    WIRE_SKIN,
    WireHole,
    WireSpace,
    plan_wiring,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, Point3D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_plan_view_svg

GUITAR = Prototype001Parameters()
THICKNESS = 44.0
BODY = (Point2D(0, -100), Point2D(300, -100), Point2D(300, 100), Point2D(0, 100))


def _box(x0: float, y0: float, x1: float, y1: float) -> tuple[Point2D, ...]:
    return (Point2D(x0, y0), Point2D(x1, y0), Point2D(x1, y1), Point2D(x0, y1))


def _route(name: str, x0: float, x1: float, depth: float = 22.0) -> WireSpace:
    """A pickup route across the body, from the top."""
    return WireSpace(name, _box(x0, -40, x1, 40), THICKNESS - depth, THICKNESS, "top")


CONTROLS = WireSpace("Control cavity", _box(150, 50, 230, 90), 0.0, 36.0, "back")


def _distance_to(point: Point2D, polygon: tuple[Point2D, ...]) -> float:
    best = math.inf
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        dx, dy = b.x - a.x, b.y - a.y
        t = max(
            0.0,
            min(
                1.0, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)
            ),
        )
        best = min(best, math.hypot(a.x + t * dx - point.x, a.y + t * dy - point.y))
    return best


def _axis(hole: WireHole, count: int = 40) -> list[Point3D]:
    return [
        Point3D(
            hole.start.x + (hole.end.x - hole.start.x) * k / count,
            hole.start.y + (hole.end.y - hole.start.y) * k / count,
            hole.start.z + (hole.end.z - hole.start.z) * k / count,
        )
        for k in range(count + 1)
    ]


def _check_hole(
    hole: WireHole,
    spaces: dict[str, WireSpace],
    thickness: float,
    outline: tuple[Point2D, ...],
) -> None:
    """A hole runs wall to wall through the wood, and can be drilled."""
    radius = hole.diameter / 2.0
    entry, other = spaces[hole.drilled_from], spaces[hole.into]
    start = Point2D(hole.start.x, hole.start.y)
    end = Point2D(hole.end.x, hole.end.y)
    # Wall to wall, opening into both cavities.
    assert _distance_to(start, entry.outline) < 1e-6
    assert _distance_to(end, other.outline) < 1e-6
    assert entry.bottom + radius - 1e-6 <= hole.start.z <= entry.top - radius + 1e-6
    assert other.bottom + radius - 1e-6 <= hole.end.z <= other.top - radius + 1e-6
    # Under the top and over the back all the way.
    for point in _axis(hole):
        assert point.z + radius + WIRE_SKIN <= thickness + 1e-6
        assert point.z - radius - WIRE_SKIN >= -1e-6
        assert point_in_polygon(Point2D(point.x, point.y), outline)
    # The bit gets in through the cavity's open face, past its far rim.
    run = math.hypot(end.x - start.x, end.y - start.y)
    ux, uy = (end.x - start.x) / run, (end.y - start.y) / run
    slope = abs(hole.end.z - hole.start.z) / run
    span = 0.0
    while point_in_polygon(
        Point2D(start.x - ux * (span + 0.1), start.y - uy * (span + 0.1)),
        entry.outline,
    ):
        span += 0.1
    if hole.face == "top":
        assert hole.end.z < hole.start.z
        assert hole.start.z + slope * span >= thickness + radius - 0.2
    else:
        assert hole.end.z > hole.start.z
        assert hole.start.z - slope * span <= -radius + 0.2


def test_a_pickup_route_is_drilled_through_to_a_rear_cavity() -> None:
    bridge = _route("Bridge pickup route", 160, 200)
    wiring = plan_wiring(THICKNESS, BODY, CONTROLS, [bridge], [], [])
    (hole,) = wiring.holes
    assert hole.name == "Bridge pickup wire hole"
    assert hole.diameter == WIRE_HOLE_DIAMETER
    assert not wiring.channels and not wiring.by_hand
    spaces = {space.name: space for space in (CONTROLS, bridge)}
    _check_hole(hole, spaces, THICKNESS, BODY)
    # It leaves the route as low as it can, where the leads lie.
    if hole.drilled_from == bridge.name:
        assert hole.start.z == pytest.approx(bridge.bottom + 3.0, abs=0.5)
    assert hole.note().startswith("Bridge pickup wire hole: 6 mm, from the ")


def test_pickups_in_a_row_chain_to_the_controls() -> None:
    neck = _route("Neck pickup route", 60, 100)
    bridge = _route("Bridge pickup route", 140, 180)
    wiring = plan_wiring(THICKNESS, BODY, CONTROLS, [neck, bridge], [], [])
    holes = {hole.name: hole for hole in wiring.holes}
    assert set(holes) == {"Neck pickup wire hole", "Bridge pickup wire hole"}
    # The neck pickup's lead goes by the bridge pickup's route.
    joined = {holes["Neck pickup wire hole"].drilled_from}
    joined.add(holes["Neck pickup wire hole"].into)
    assert joined == {neck.name, bridge.name}
    spaces = {space.name: space for space in (CONTROLS, neck, bridge)}
    for hole in wiring.holes:
        _check_hole(hole, spaces, THICKNESS, BODY)


def test_a_hole_keeps_clear_of_the_cavities_between() -> None:
    bridge = _route("Bridge pickup route", 160, 200)
    # A deep route right across the way, from the top down to 6 mm off
    # the back: nothing passes under it.
    wall = WireSpace("Tremolo route", _box(205, 30, 215, 95), 6.0, THICKNESS)
    spaces = {space.name: space for space in (CONTROLS, bridge)}
    clear = plan_wiring(THICKNESS, BODY, CONTROLS, [bridge], [], [wall])
    for hole in clear.holes:
        _check_hole(hole, spaces, THICKNESS, BODY)
        for point in _axis(hole, 200):
            near = _distance_to(Point2D(point.x, point.y), wall.outline)
            inside = point_in_polygon(Point2D(point.x, point.y), wall.outline)
            assert not inside and near >= hole.diameter / 2.0 + 2.0 - 0.6
    # A wall through the body between them: no straight hole, left to the
    # builder.
    through = WireSpace("Wall", _box(120, 42, 240, 48), 0.0, THICKNESS)
    stuck = plan_wiring(THICKNESS, BODY, CONTROLS, [bridge], [], [through])
    assert not stuck.holes
    assert stuck.by_hand == (
        "No straight hole joins the bridge pickup route to the wiring: make "
        "its lead's way by hand.",
    )


def test_cavities_that_meet_need_no_hole() -> None:
    touching = WireSpace(
        "Bridge pickup route", _box(160, 40, 200, 60), 22.0, 44.0, "top"
    )
    wiring = plan_wiring(THICKNESS, BODY, CONTROLS, [touching], [], [])
    assert wiring.holes == () and wiring.by_hand == ()


def test_under_a_pickguard_the_channel_is_routed() -> None:
    neck = _route("Neck pickup route", 60, 100)
    controls = WireSpace("Control cavity", _box(120, 45, 200, 90), 14.0, 44.0, "top")
    guard = _box(40, -60, 220, 95)
    wiring = plan_wiring(THICKNESS, BODY, controls, [neck], [], [], covers=(guard,))
    (channel,) = wiring.channels
    assert not wiring.holes
    assert channel.name == "Neck pickup wire channel"
    assert channel.depth == pytest.approx(16.0)
    width = max(p.y for p in channel.outline) - min(p.y for p in channel.outline)
    assert width >= WIRE_CHANNEL_WIDTH - 1e-6
    # An opening in the guard over the way: drilled instead.
    opening = _box(105, 30, 115, 60)
    drilled = plan_wiring(
        THICKNESS,
        BODY,
        controls,
        [neck],
        [],
        [],
        covers=(guard,),
        openings=(opening,),
    )
    assert drilled.channels == () and len(drilled.holes) == 1


def test_wire_holes_are_checked() -> None:
    with pytest.raises(BodyGeometryError, match="positive diameter"):
        WireHole("Hole", Point3D(0, 0, 1), Point3D(1, 0, 1), 0.0, "A", "B", "top")
    with pytest.raises(BodyGeometryError, match="some length"):
        WireHole("Hole", Point3D(0, 0, 1), Point3D(0, 0, 1), 6.0, "A", "B", "top")
    with pytest.raises(BodyGeometryError, match="floor below its ceiling"):
        WireSpace("Route", _box(0, 0, 1, 1), 5.0, 5.0)
    body = GUITAR.build().body
    stray = WireHole(
        "Stray wire hole", Point3D(0, 0, 20), Point3D(5, 0, 20), 6.0, "A", "B", "top"
    )
    with pytest.raises(BodyGeometryError, match="Stray wire hole must lie in the body"):
        BodySolid(
            body.outline,
            body.thickness,
            body.neck_pocket,
            body.bridge_pickup,
            body.neck_pickup,
            body.bridge_mounting,
            body.jack_hole,
            wire_holes=(stray,),
        )


def _spaces(body: BodySolid) -> dict[str, WireSpace]:
    """The body's cavities as the wiring sees them."""
    spaces: dict[str, WireSpace] = {}
    for cavity in body.top_cavities:
        spaces[cavity.name] = WireSpace(
            cavity.name,
            cavity.outline,
            max(0.0, body.thickness - cavity.depth),
            body.thickness,
            "top",
        )
    for rear in body.rear_cavities:
        spaces[rear.name] = WireSpace(
            rear.name, rear.cavity.outline, 0.0, rear.cavity.depth, "back"
        )
    return spaces


def test_the_default_guitar_is_wired_by_drilled_holes() -> None:
    geometry = GUITAR.build()
    body = geometry.body
    names = {hole.name: hole for hole in body.wire_holes}
    assert set(names) == {
        "Neck pickup wire hole",
        "Bridge pickup wire hole",
        "Bridge ground hole",
    }
    assert body.wire_channels == () and body.wire_notes == ()
    assert names["Bridge ground hole"].diameter == GROUND_HOLE_DIAMETER
    # The bridge pickup to the controls, the neck pickup by it.
    bridge = names["Bridge pickup wire hole"]
    assert {bridge.drilled_from, bridge.into} == {
        "Bridge pickup route",
        "Control cavity",
    }
    neck = names["Neck pickup wire hole"]
    assert {neck.drilled_from, neck.into} == {
        "Neck pickup route",
        "Bridge pickup route",
    }
    spaces = _spaces(body)
    for hole in (bridge, neck):
        _check_hole(hole, spaces, body.thickness, body.outline.points)
    # Given in Body_top's notes, cut in the model, drawn in the plan.
    plan = plan_body_machining(body, MachiningParameters())
    (top,) = [setup for setup in plan.setups if setup.name == "Body_top"]
    assert (
        "Drill the wire holes by hand once every cavity is cut, with a long bit:"
        in (top.notes)
    )
    assert all(hole.note() in top.notes for hole in body.wire_holes)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert source.count("wire_hole = Part.makeCylinder(") == 3
    assert "'neck pickup wire hole cut'" in source
    assert 'stroke="#c0392b"' in render_plan_view_svg(geometry)


def test_strat_pickups_are_routed_under_the_guard() -> None:
    geometry = replace(GUITAR, body_controls="pickguard", body_pickups="SSS").build()
    body = geometry.body
    assert sorted(channel.name for channel in body.wire_channels) == [
        "Bridge pickup wire channel",
        "Middle pickup wire channel",
        "Neck pickup wire channel",
    ]
    # Only the ground is drilled.
    assert [hole.name for hole in body.wire_holes] == ["Bridge ground hole"]
    (guard,) = [cover for cover in geometry.covers if cover.name == "Pickguard"]
    for channel in body.wire_channels:
        assert all(point_in_polygon(p, guard.outline) for p in channel.outline)
        assert channel in body.top_cavities
    plan = plan_body_machining(body, MachiningParameters())
    (top,) = [setup for setup in plan.setups if setup.name == "Body_top"]
    names = [path.name for path in top.toolpaths]
    assert any("Neck pickup wire channel" in name for name in names)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "'neck pickup wire channel cut'" in source


@pytest.mark.parametrize(
    ("bridge", "target"),
    [
        (FloydRoseSpec(), "Floyd Rose spring cavity"),
        (TuneOMaticSpec(), "stud"),
        (HardtailSpec(), "through hole"),
    ],
)
def test_the_ground_wire_reaches_the_bridge(bridge: BridgeSpec, target: str) -> None:
    body = replace(GUITAR, body_bridge=bridge).build().body
    (ground,) = [hole for hole in body.wire_holes if hole.name == "Bridge ground hole"]
    assert target in ground.drilled_from + ground.into
    assert "Control cavity" in (ground.drilled_from, ground.into)


def test_no_controls_or_switched_off_no_wiring() -> None:
    for parameters in (
        replace(GUITAR, body_controls="none"),
        replace(GUITAR, body_wire_channels=False),
    ):
        body = parameters.build().body
        assert body.wire_holes == () and body.wire_channels == ()


def test_the_body_editor_lays_no_wiring_out() -> None:
    assert GUITAR.body_layout().wiring.holes == ()
