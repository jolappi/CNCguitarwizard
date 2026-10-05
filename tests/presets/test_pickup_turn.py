"""Tests for turning each pickup about its centre (the body editor's
Shift-drag)."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body.body_solid import outlines_overlap
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

HSS = replace(Prototype001Parameters(), body_pickups="HSS")


def _screws(parameters: Prototype001Parameters, label: str) -> dict[str, tuple]:
    layout = parameters.body_layout()
    return {
        hole.name.split()[2]: (hole.center_x, hole.center_y)
        for hole in layout.holes
        if hole.name.startswith(f"{label} pickup") and "screw recess" in hole.name
    }


def _bearing(screws: dict[str, tuple]) -> float:
    """The bass-to-treble screw line's angle in the plan, in degrees."""
    (bx, by), (tx, ty) = screws["bass"], screws["treble"]
    return math.degrees(math.atan2(ty - by, tx - bx))


@pytest.mark.parametrize("position", ["neck", "middle", "bridge"])
def test_a_pickup_turns_about_its_own_centre(position: str) -> None:
    label = position.capitalize()
    turned = replace(HSS, **{f"body_{position}_pickup_angle": 12.0})
    before, after = _screws(HSS, label), _screws(turned, label)

    # The screws turn 12 degrees about the same centre...
    centre = [
        tuple(sum(c) / 2.0 for c in zip(*s.values(), strict=True))
        for s in (before, after)
    ]
    if position == "bridge":
        # Turned, the humbucker reaches nearer the bridge's routes, so it
        # moves toward the neck just enough to keep its clearance.
        assert centre[1][0] < centre[0][0]
        assert centre[1][1] == pytest.approx(centre[0][1])
    else:
        assert centre[1] == pytest.approx(centre[0], abs=1e-6)
        layout = turned.body_layout()
        assert dict(layout.pickup_centres)[position] == pytest.approx(
            dict(HSS.body_layout().pickup_centres)[position]
        )
    assert abs(_bearing(after) - _bearing(before)) == pytest.approx(12.0)
    # ...the treble end swinging toward the tail.
    shift = centre[1][0] - centre[0][0]
    assert after["treble"][0] - shift > before["treble"][0]
    assert after["bass"][0] - shift < before["bass"][0]


def test_the_turn_adds_to_a_bridge_single_coils_slant_and_mirrors() -> None:
    sss = replace(Prototype001Parameters(), body_pickups="SSS")
    slanted = _bearing(_screws(sss, "Bridge"))
    turned = _bearing(_screws(replace(sss, body_bridge_pickup_angle=-10.0), "Bridge"))
    # -10 degrees undoes the 10 degree slant: the pickup lies square.
    assert abs(slanted) == pytest.approx(80.0)
    assert turned == pytest.approx(90.0)
    # Left-handed, the treble end still swings toward the tail.
    left = replace(HSS, handedness="left", body_neck_pickup_angle=12.0)
    screws = _screws(left, "Neck")
    straight = _screws(replace(HSS, handedness="left"), "Neck")
    assert screws["treble"][0] > straight["treble"][0]


def test_a_turned_bridge_pickup_keeps_clear_of_the_bridge() -> None:
    from cncguitarwizard.geometry.body import FloydRoseSpec

    parameters = replace(
        Prototype001Parameters(),
        body_bridge=FloydRoseSpec(),
        body_bridge_pickup_angle=20.0,
    )
    layout = parameters.body_layout()
    assert layout.bridge_pickup is not None
    routes = [c for c in layout.extra_cavities if "pickup" not in c.name]
    assert routes
    assert not any(
        outlines_overlap(layout.bridge_pickup.outline, route.outline)
        for route in routes
    )
    parameters.build()


def test_a_guard_opening_turns_with_its_pickup() -> None:
    def opening(parameters: Prototype001Parameters) -> tuple:
        guard = parameters.body_layout().pickguard
        assert guard is not None
        (slot,) = [s for s in guard.plate.slots if s.name == "Neck pickup opening"]
        (a, b) = slot.outline[0], slot.outline[1]
        return math.degrees(math.atan2(b.y - a.y, b.x - a.x))

    guarded = replace(HSS, body_pickguard=True)
    turned = replace(guarded, body_neck_pickup_angle=15.0)
    assert abs(opening(turned) - opening(guarded)) == pytest.approx(15.0)


def test_a_pickup_turns_only_so_far() -> None:
    with pytest.raises(BodyGeometryError, match="within 45 degrees"):
        replace(HSS, body_middle_pickup_angle=46.0).build()


def test_the_editor_gets_each_pickups_centre_and_angle_field() -> None:
    layout = body_editor_layout({"prototype": {"body_pickups": "HSS"}})
    assert layout["bass_sign"] == -1.0
    assert set(layout["pickups"]) == {"pickup:neck", "pickup:middle", "pickup:bridge"}
    neck = layout["pickups"]["pickup:neck"]
    assert neck["field"] == "body_neck_pickup_angle"
    assert neck["centre"] == [30.5, 0.0]
    # Only the fitted pickups turn.
    single = body_editor_layout({"prototype": {"body_pickups": "H"}})
    assert set(single["pickups"]) == {"pickup:bridge"}
    fields = {
        field["name"]
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert {
        "body_neck_pickup_angle",
        "body_middle_pickup_angle",
        "body_bridge_pickup_angle",
    } <= fields
