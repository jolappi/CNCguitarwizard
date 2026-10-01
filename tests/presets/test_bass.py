"""Tests for the bass guitar defaults, pickup types and string count."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import HardtailSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
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
    assert "Bridge pickup bass screw recess" in names
    # The Precision Bass route is two offset coils, wider than a Jazz bar.
    neck = body.neck_pickup
    bridge = body.bridge_pickup
    assert neck is not None and bridge is not None
    assert neck.max_x - neck.min_x == pytest.approx(42.0)
    assert bridge.max_x - bridge.min_x == pytest.approx(21.0)
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
    lefty = pickup_route("precision_bass", "P", 100.0, 20.0, -1.0)
    righty = pickup_route("precision_bass", "P", 100.0, 20.0, 1.0)
    assert lefty is not None and righty is not None
    # The bass coil (nut-ward half) lies on the bass side.
    nut_ward_y = [p.y for p in lefty.outline if p.x < 100.0 - 1.0]
    assert max(nut_ward_y) < 15.0 and min(nut_ward_y) < -40.0
    assert [p.y for p in righty.outline] == pytest.approx([-p.y for p in lefty.outline])
    for _, x, y in pickup_screws("precision_bass", 100.0, -1.0, 79.9):
        from cncguitarwizard.geometry.primitives import Point2D

        assert point_in_polygon(Point2D(x, y), lefty.outline)
    assert pickup_route("none", "N", 0.0, 20.0, -1.0) is None
    assert pickup_screws("none", 0.0, -1.0, 79.9) == ()
    assert pickup_half_length("jazz_bass") == pytest.approx(10.5)


def test_the_hardtail_follows_its_string_count() -> None:
    hardware = HardtailSpec(string_count=4, string_spacing=19.0).hardware(863.6, 44.0)
    strings = [hole for hole in hardware.holes if hole.name.startswith("String")]

    assert [round(hole.center_y, 1) for hole in strings] == [-28.5, -9.5, 9.5, 28.5]


def test_the_bass_neck_bolts_spread_toward_the_body_edge(bass) -> None:  # type: ignore[no-untyped-def]
    parameters = Prototype001Parameters.for_instrument("bass_guitar")
    heel_end = parameters.body_layout().heel_end
    ferrules = [h for h in bass.body.rear_holes if h.name.endswith("ferrule")]
    xs = sorted({round(h.center_x - heel_end, 1) for h in ferrules})

    # 56 mm apart along the neck: the pair at the pocket's mouth sits
    # near the body's edge, further out than a guitar's 32 mm pattern, and
    # the rear pair's ferrules lie wholly over the pocket.
    assert xs == [-63.5, -7.5]
    pocket_end = max(p.x for p in bass.body.neck_pocket.outline)
    for ferrule in ferrules:
        assert point_in_polygon(ferrule.center, bass.body.outline.points)
        assert ferrule.center_x + ferrule.diameter / 2.0 <= pocket_end
