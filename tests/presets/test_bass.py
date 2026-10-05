"""Tests for the bass guitar defaults, pickup types and string count."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import HardtailSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.pickups import (
    pickup_half_length,
    pickup_route,
    pickup_screws,
)


@pytest.fixture(scope="module")
def bass():  # type: ignore[no-untyped-def]
    return Prototype001Parameters.for_instrument("bass_guitar").build()


def test_the_electric_guitar_is_the_plain_default() -> None:
    assert Prototype001Parameters.for_instrument("electric_guitar") == (
        Prototype001Parameters()
    )
    with pytest.raises(NeckGeometryError, match="Unknown instrument"):
        Prototype001Parameters.for_instrument("banjo")  # type: ignore[arg-type]


def test_the_bass_has_four_big_tuners_in_line(bass) -> None:  # type: ignore[no-untyped-def]
    holes = bass.tuner_layout.holes

    assert len(holes) == 4
    assert all(hole.diameter == 19.0 for hole in holes)
    assert [round(-hole.center.x, 1) for hole in holes] == [60.0, 98.0, 136.0, 174.0]
    assert bass.tuner_layout.minimum_side_edge_clearance >= 8.0


def test_the_bass_neck_is_long_and_wide(bass) -> None:  # type: ignore[no-untyped-def]
    outline = bass.neck_outline

    assert outline.scale_length == 863.6
    assert outline.nut_width == 38.0
    assert outline.heel_width == 62.0
    assert len(bass.fret_layout.slots) == 21


def test_the_bass_body_carries_p_and_j_pickups_and_a_four_string_bridge(
    bass,  # type: ignore[no-untyped-def]
) -> None:
    body = bass.body
    names = [hole.name for hole in body.holes]

    assert sum(name.startswith("String") for name in names) == 4
    assert "Neck pickup bass coil bass screw recess" in names
    assert "Bridge pickup bass front screw recess" in names
    # Warmoth's rout diagrams: the Precision Bass route two 28.5 mm coils
    # one behind the other along the neck (2.28 in), the Jazz Bass a
    # 20 mm bar whose side recesses reach 5 mm out of each side.
    neck = body.neck_pickup
    bridge = body.bridge_pickup
    assert neck is not None and bridge is not None
    assert neck.max_x - neck.min_x == pytest.approx(57.0)
    assert bridge.max_x - bridge.min_x == pytest.approx(30.0)
    for hole in body.holes:
        assert point_in_polygon(hole.center, body.outline.points), hole.name


def test_a_pickup_position_can_be_left_empty() -> None:
    body = (
        replace(
            Prototype001Parameters.for_instrument("bass_guitar"),
            body_pickups="custom",
            body_neck_pickup="none",
            body_bridge_pickup="bass_soapbar",
        )
        .build()
        .body
    )

    assert body.neck_pickup is None
    assert body.bridge_pickup is not None
    assert all("Neck pickup" not in hole.name for hole in body.holes)
    assert body.neck_pocket in body.top_cavities


def test_pickup_routes_and_screws_follow_the_bass_side() -> None:
    righty = pickup_route("precision_bass", "P", 100.0, 20.0, -1.0)
    lefty = pickup_route("precision_bass", "P", 100.0, 20.0, 1.0)
    assert righty is not None and lefty is not None
    # The bass coil (nut-ward half) lies on the bass side.
    nut_ward_y = [p.y for p in righty.outline if p.x < 100.0 - 1.0]
    # Its inner end's ear reaches 17.3 mm past the centreline.
    assert max(nut_ward_y) < 20.0 and min(nut_ward_y) < -40.0
    assert [p.y for p in lefty.outline] == pytest.approx([-p.y for p in righty.outline])
    for _, x, y in pickup_screws("precision_bass", 100.0, -1.0, 79.9):
        from cncguitarwizard.geometry.primitives import Point2D

        assert point_in_polygon(Point2D(x, y), righty.outline)
    assert pickup_route("none", "N", 0.0, 20.0, -1.0) is None
    assert pickup_screws("none", 0.0, -1.0, 79.9) == ()
    assert pickup_half_length("jazz_bass") == pytest.approx(15.0)


def test_the_hardtail_follows_its_string_count() -> None:
    hardware = HardtailSpec(string_count=4, string_spacing=19.0).hardware(863.6, 44.0)
    strings = [hole for hole in hardware.holes if hole.name.startswith("String")]

    assert [round(hole.center_y, 1) for hole in strings] == [-28.5, -9.5, 9.5, 28.5]


def test_the_bass_neck_bolts_spread_toward_the_body_edge(bass) -> None:  # type: ignore[no-untyped-def]
    parameters = Prototype001Parameters.for_instrument("bass_guitar")
    heel_end = parameters.body_layout().heel_end
    ferrules = [h for h in bass.body.rear_holes if h.name.startswith("Neck bolt")]
    xs = sorted({round(h.center_x - heel_end, 1) for h in ferrules})

    # 56 mm apart along the neck: the pair at the pocket's mouth sits
    # near the body's edge, further out than a guitar's 32 mm pattern, and
    # the rear pair's ferrules lie wholly over the pocket.
    assert xs == [-63.5, -7.5]
    pocket_end = max(p.x for p in bass.body.neck_pocket.outline)
    for ferrule in ferrules:
        assert point_in_polygon(ferrule.center, bass.body.outline.points)
        assert ferrule.center_x + ferrule.diameter / 2.0 <= pocket_end


def test_the_bass_routes_follow_warmoths_rout_diagrams() -> None:
    jazz = pickup_route("jazz_bass", "J", 0.0, 19.0, -1.0)
    precision = pickup_route("precision_bass", "P", 0.0, 19.0, -1.0)
    assert jazz is not None and precision is not None

    # Jazz: 96 x 20 mm (3.75 x 0.79 in) with two round recesses in each
    # long side, 19.6 mm either side of the middle.
    assert jazz.max_y - jazz.min_y == pytest.approx(96.0)
    side = [p for p in jazz.outline if abs(p.x) > 10.0 + 1e-6]
    assert {round(abs(p.y) // 10) for p in side} == {1, 2}
    # The pickup itself (an SJB-1b, 94.4 x 18.2 mm) fits the route, and its
    # four screws sit in the side recesses outside its sides, their 6 mm
    # spring recesses inside the route.
    pickup = [Point2D(x, y) for x in (-9.1, 9.1) for y in (-47.2, 47.2)]
    assert all(point_in_polygon(p, jazz.outline) for p in pickup)
    screws = pickup_screws("jazz_bass", 0.0, -1.0, 79.9)
    assert len(screws) == 4
    for _, x, y in screws:
        assert (abs(x), abs(y)) == pytest.approx((12.0, 19.6))
        assert abs(x) - 9.1 > 2.0  # clear of the pickup's side
        assert all(
            point_in_polygon(Point2D(x + 2.9 * dx, y + 2.9 * dy), jazz.outline)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )
    # Precision: 93 mm across the strings over both coils (3.678 in), the
    # ears beyond that, and 57 mm along the neck.
    coil_ends = [p.y for p in precision.outline if abs(abs(p.y) - 46.5) < 1e-6]
    assert coil_ends
    assert precision.max_y - precision.min_y > 93.0
    assert len(pickup_screws("precision_bass", 0.0, -1.0, 79.9)) == 4


def test_a_bass_can_take_rickenbacker_style_humbuckers() -> None:
    body = (
        replace(Prototype001Parameters.for_instrument("bass_guitar"), body_pickups="RR")
        .build()
        .body
    )
    neck, bridge = body.neck_pickup, body.bridge_pickup
    assert neck is not None and bridge is not None

    # A 90 x 36 mm block with 1 mm round it, screwed 82 mm apart.
    for route in (neck, bridge):
        assert route.max_y - route.min_y == pytest.approx(92.0)
        assert route.max_x - route.min_x == pytest.approx(38.0)
    screws = [h for h in body.holes if h.name.startswith("Bridge pickup")]
    assert len(screws) == 2
    assert abs(screws[0].center_y - screws[1].center_y) == pytest.approx(82.0)
    for screw in screws:
        assert point_in_polygon(screw.center, bridge.outline)


def test_a_five_string_bass_is_an_instrument_of_its_own() -> None:
    parameters = Prototype001Parameters.for_instrument("five_string_bass")
    geometry = parameters.build()
    body = geometry.body

    assert parameters.string_count == 5
    assert parameters.nut_width == 47.0
    # Five string-through holes and a 4+1 headstock, Fender Jazz V style.
    assert sum(hole.name.startswith("String") for hole in body.holes) == 5
    sides = [hole.side for hole in geometry.tuner_layout.holes]
    assert sides.count("bass") == 4 and sides.count("treble") == 1
    # The five-string Jazz Bass route is Warmoth's 4-1/8 in; its screws
    # spread with it, still in its side recesses.
    bridge = body.bridge_pickup
    assert bridge is not None
    assert bridge.max_y - bridge.min_y == pytest.approx(104.0)
    for hole in body.holes:
        if hole.name.startswith("Bridge pickup"):
            assert point_in_polygon(hole.center, bridge.outline)
            assert abs(hole.center_y) == pytest.approx(23.6)


@pytest.mark.parametrize(
    "style", ["4+1", "1+4", "3+2", "2+3", "5_inline", "5_inline_reverse"]
)
def test_every_five_string_headstock_keeps_its_tuners_off_the_edge(style: str) -> None:
    from cncguitarwizard.presets.prototype001 import distance_to_headstock_edge

    parameters = replace(
        Prototype001Parameters.for_instrument("five_string_bass"), headstock_style=style
    )
    plan, tuners = parameters.headstock_design()

    # A lone tuner (4+1) gets its edge too, and a row's end tuners are not
    # left nearer than the check allows.
    for hole in tuners.holes:
        gap = distance_to_headstock_edge(plan, hole.center)
        assert gap >= parameters.tuner_edge_offset - 0.01
