"""Tests for the routes under a separate top: the wire channels routed into
the core, and the chambers lightening it."""

import math

import pytest

from cncguitarwizard.geometry.body.chambers import (
    CHAMBER_EDGE_WALL,
    CHAMBER_FLOOR,
    CHAMBER_WALL,
    plan_chambers,
)
from cncguitarwizard.geometry.body.wiring import (
    WIRE_CORE_CHANNEL_DEPTH,
    WIRE_OPENING,
    WireSpace,
    plan_wiring,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon

THICKNESS = 44.0
CAP = 16.0
SPLIT = THICKNESS - CAP


def _box(x0: float, y0: float, x1: float, y1: float) -> tuple[Point2D, ...]:
    return (Point2D(x0, y0), Point2D(x1, y0), Point2D(x1, y1), Point2D(x0, y1))


def _distance_to(point: Point2D, polygon: tuple[Point2D, ...]) -> float:
    best = math.inf
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        dx, dy = b.x - a.x, b.y - a.y
        length = dx * dx + dy * dy
        t = 0.0 if length == 0 else ((point.x - a.x) * dx + (point.y - a.y) * dy)
        t = max(0.0, min(1.0, t / length if length else 0.0))
        best = min(best, math.hypot(a.x + t * dx - point.x, a.y + t * dy - point.y))
    return best


BODY = _box(0, -150, 400, 150)
PICKUP = WireSpace("Neck pickup route", _box(60, -40, 100, 40), 22.0, 44.0, "top")
CONTROLS = WireSpace("Control cavity", _box(220, 60, 300, 110), 0.0, 27.0, "back")


def test_a_channel_under_the_top_joins_what_no_hole_reaches() -> None:
    # Without a separate top the way from the route to the controls is a
    # hole drilled by hand; with one, a channel routed into the core.
    plain = plan_wiring(THICKNESS, BODY, CONTROLS, [PICKUP], [], [])
    assert plain.holes and not plain.core_channels
    capped = plan_wiring(THICKNESS, BODY, CONTROLS, [PICKUP], [], [], cap=CAP)
    assert not capped.holes and not capped.by_hand
    (channel,) = capped.core_channels
    assert channel.name == "Neck pickup wire channel"
    # Its floor deep enough to open into the control cavity, whose ceiling
    # is a mm under the top: WIRE_OPENING below it.
    assert channel.depth == pytest.approx(
        max(WIRE_CORE_CHANNEL_DEPTH, SPLIT - (CONTROLS.top - WIRE_OPENING))
    )
    assert any(point_in_polygon(p, PICKUP.outline) for p in channel.outline)
    assert any(point_in_polygon(p, CONTROLS.outline) for p in channel.outline)


def test_a_channel_under_the_top_keeps_clear_and_needs_both_ends_in_the_core() -> None:
    # A route that stays in the top cannot be joined under it.
    shallow = WireSpace("Neck pickup route", PICKUP.outline, 36.0, 44.0, "top")
    wiring = plan_wiring(THICKNESS, BODY, CONTROLS, [shallow], [], [], cap=CAP)
    assert not wiring.core_channels
    # A cavity in the way, or the top carved down to its underside over it,
    # leaves the hole.
    wall = WireSpace("Wall", _box(150, -140, 160, 140), 10.0, 44.0)
    blocked = plan_wiring(THICKNESS, BODY, CONTROLS, [PICKUP], [], [wall], cap=CAP)
    assert not blocked.core_channels
    carved = plan_wiring(
        THICKNESS,
        BODY,
        CONTROLS,
        [PICKUP],
        [],
        [],
        cap=CAP,
        top_at=lambda point: SPLIT + 1.0,
    )
    assert not carved.core_channels


def test_chambers_take_the_room_left_clear_of_everything() -> None:
    block = 50.0
    chambers = plan_chambers(BODY, THICKNESS, CAP, [CONTROLS, PICKUP], block)
    assert chambers
    assert [c.name for c in chambers] == [
        f"Chamber {k + 1}" for k in range(len(chambers))
    ]
    for chamber in chambers:
        assert chamber.depth == pytest.approx(SPLIT - CHAMBER_FLOOR)
        for point in chamber.outline:
            assert _distance_to(point, BODY) >= CHAMBER_EDGE_WALL - 1.0
            assert _distance_to(point, CONTROLS.outline) >= CHAMBER_WALL - 1.0
            # Out of the centre block, its wall from it.
            assert abs(point.y) >= block + CHAMBER_WALL - 1.0
    # The control cavity stands in the treble wing's room: a rib joins its
    # wood to the wall, so no chamber goes round it (an island).
    middle = Point2D(260, 85)
    assert not any(point_in_polygon(middle, c.outline) for c in chambers)


def test_a_chamber_leaves_its_floor_over_a_raised_back_and_none_is_too_small() -> None:
    (chamber, *_) = plan_chambers(
        BODY, THICKNESS, CAP, [], 50.0, back_at=lambda point: 5.0
    )
    assert chamber.depth == pytest.approx(SPLIT - 5.0 - CHAMBER_FLOOR)
    small = _box(0, -30, 40, 30)
    assert plan_chambers(small, THICKNESS, CAP, [], 0.0) == ()
    # A top carved down near its underside keeps its wood over it.
    assert (
        plan_chambers(BODY, THICKNESS, CAP, [], 50.0, top_at=lambda p: SPLIT + 2.0)
        == ()
    )
