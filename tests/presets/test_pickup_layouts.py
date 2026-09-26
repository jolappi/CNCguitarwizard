"""Tests for the named pickup layouts and the middle position."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.pickups import PICKUP_CONFIGURATIONS, pickup_route

GUITAR = ("HH", "HSH", "HSS", "H", "SSS", "SS")
BASS = ("PJ", "JJ", "P", "MM")


def routes(body) -> dict[str, object]:  # type: ignore[no-untyped-def]
    return {c.name: c for c in body.top_cavities if "pickup" in c.name}


@pytest.mark.parametrize("layout", GUITAR + BASS)
def test_every_layout_builds_with_its_routes(layout: str) -> None:
    instrument = "bass_guitar" if layout in BASS else "electric_guitar"
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument),  # type: ignore[arg-type]
        body_pickups=layout,
    )
    body = parameters.build().body
    neck, middle, bridge = PICKUP_CONFIGURATIONS[layout]

    names = set(routes(body))
    assert ("Neck pickup route" in names) == (neck != "none")
    assert ("Middle pickup route" in names) == (middle != "none")
    assert ("Bridge pickup route" in names) == (bridge != "none")
    for hole in body.holes:
        assert point_in_polygon(hole.center, body.outline.points), hole.name


def test_hsh_puts_a_single_coil_halfway_between_the_humbuckers() -> None:
    body = replace(Prototype001Parameters(), body_pickups="HSH").build().body
    found = routes(body)
    centre = {name: (c.min_x + c.max_x) / 2.0 for name, c in found.items()}  # type: ignore[attr-defined]

    assert centre["Middle pickup route"] == pytest.approx(
        (centre["Neck pickup route"] + centre["Bridge pickup route"]) / 2.0
    )
    middle = found["Middle pickup route"]
    assert middle.max_x - middle.min_x == pytest.approx(20.0)  # type: ignore[attr-defined]
    assert middle.max_y - middle.min_y == pytest.approx(88.0, abs=0.1)  # type: ignore[attr-defined]
    assert "Middle pickup bass screw recess" in [h.name for h in body.holes]


def test_the_middle_pickup_can_be_placed_by_hand() -> None:
    parameters = replace(
        Prototype001Parameters(), body_pickups="SSS", body_middle_pickup_offset=70.0
    )
    body = parameters.build().body
    middle = routes(body)["Middle pickup route"]
    heel_end = body.neck_pocket.max_x

    assert (middle.min_x + middle.max_x) / 2.0 == pytest.approx(heel_end + 70.0)  # type: ignore[attr-defined]


def test_custom_takes_each_position_from_its_own_parameter() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_pickups="custom",
        body_neck_pickup="single_coil",
        body_middle_pickup="none",
        body_bridge_pickup="humbucker",
    )

    assert parameters.pickup_types() == ("single_coil", "none", "humbucker")
    assert replace(parameters, body_pickups="SS").pickup_types() == (
        "single_coil",
        "none",
        "single_coil",
    )
    with pytest.raises(BodyGeometryError, match="Unknown pickup layout"):
        replace(parameters, body_pickups="XYZ").pickup_types()  # type: ignore[arg-type]


def test_the_single_coil_route_is_a_round_ended_bar() -> None:
    route = pickup_route("single_coil", "S", 0.0, 20.0, -1.0)

    assert route is not None
    assert route.max_x - route.min_x == pytest.approx(20.0)
    assert route.max_y - route.min_y == pytest.approx(88.0, abs=0.1)


@pytest.mark.parametrize("layout", ["HSH", "HSS", "SSS"])
def test_the_middle_pickup_sits_in_the_middle_of_the_gap(layout: str) -> None:
    found = routes(replace(Prototype001Parameters(), body_pickups=layout).build().body)
    neck, middle, bridge = (
        found["Neck pickup route"],
        found["Middle pickup route"],
        found["Bridge pickup route"],
    )

    assert middle.min_x - neck.max_x == pytest.approx(  # type: ignore[attr-defined]
        bridge.min_x - middle.max_x  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize("layout", ["SSS", "SS"])
def test_a_bridge_single_coil_slants_its_treble_end_toward_the_bridge(
    layout: str,
) -> None:
    body = replace(Prototype001Parameters(), body_pickups=layout).build().body
    bridge = routes(body)["Bridge pickup route"]
    points = bridge.outline  # type: ignore[attr-defined]
    # The left-handed body has the treble side at +Y.
    treble_end = max(points, key=lambda point: point.y)
    bass_end = min(points, key=lambda point: point.y)

    assert treble_end.x > bass_end.x
    screws = {h.name: h for h in body.holes if h.name.startswith("Bridge pickup")}
    assert (
        screws["Bridge pickup treble screw recess"].center_x
        - screws["Bridge pickup bass screw recess"].center_x
    ) == pytest.approx(76.0 * __import__("math").sin(__import__("math").radians(10.0)))


def test_the_slant_can_be_set_and_leaves_humbuckers_alone() -> None:
    straight = (
        replace(
            Prototype001Parameters(),
            body_pickups="SSS",
            body_bridge_single_coil_angle=0.0,
        )
        .build()
        .body
    )
    bridge = routes(straight)["Bridge pickup route"]
    assert bridge.max_x - bridge.min_x == pytest.approx(20.0)  # type: ignore[attr-defined]
    hsh = routes(replace(Prototype001Parameters(), body_pickups="HSH").build().body)
    assert hsh["Bridge pickup route"].max_x - hsh["Bridge pickup route"].min_x == (  # type: ignore[attr-defined]
        pytest.approx(41.0)
    )
