"""Tests for the interchangeable bridge specifications."""

import pytest

from cncguitarwizard.geometry.body import (
    BRIDGE_KINDS,
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
    bridge_spec_from_dict,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError


def test_kahler_routes_only_the_baseplate_cutout() -> None:
    hardware = KahlerBridgeSpec().hardware(609.6, 44.0)

    assert hardware.mounting.pivot_holes == ()
    assert hardware.mounting.sustain_block_cavity is None
    assert [cavity.name for cavity in hardware.top_cavities] == [
        "Bridge baseplate cutout"
    ]
    cutout = hardware.top_cavities[0]
    assert cutout.min_x == pytest.approx(626.12, abs=0.01)
    assert cutout.max_x == pytest.approx(681.57, abs=0.01)
    assert cutout.max_y == pytest.approx(32.52)
    assert cutout.depth == 25.0
    assert hardware.through_cavities == () and hardware.rear_cavities == ()


def test_floyd_rose_follows_the_official_routing_diagram() -> None:
    """Dimensions from Floyd Rose's Original Series Routing Diagrams (mm)."""
    hardware = FloydRoseSpec().hardware(609.6, 44.0)

    studs = hardware.mounting.pivot_holes
    # 25.03 in from the nut on a 25.5 in scale; 73.91 mm apart, Ø 10.
    assert [(p.x, p.y) for p in studs] == [
        (pytest.approx(597.7), pytest.approx(-36.955)),
        (pytest.approx(597.7), pytest.approx(36.955)),
    ]
    assert hardware.mounting.pivot_hole_diameter == 10.0
    recess, fine_tuners = hardware.top_cavities
    front = 597.7 - 7.62
    # One shallow pocket over the whole footprint, deepened behind the
    # stud shelf by a step inside it.
    assert recess.name == "Floyd Rose recess" and recess.depth == 6.73
    assert recess.min_x == pytest.approx(front)
    assert recess.max_x == pytest.approx(front + 79.38)
    # 95.25 wide, 3.56 mm more on the treble (+Y, arm) side.
    assert recess.min_y == pytest.approx(-45.85)
    assert recess.max_y == pytest.approx(49.4)
    assert fine_tuners.depth == 11.18
    assert fine_tuners.min_x == pytest.approx(front + 15.88)
    assert fine_tuners.max_x == pytest.approx(recess.max_x)
    assert max(p.y for p in recess.outline if p.x > front + 50) == (
        pytest.approx(35.56)
    )
    # Full width to 42.44 mm behind the front wall, then 71.12 wide.
    assert max(p.y for p in fine_tuners.outline if p.x > front + 50) == (
        pytest.approx(35.56)
    )
    assert max(p.y for p in fine_tuners.outline if p.x < front + 40) == (
        pytest.approx(49.4)
    )
    block = hardware.through_cavities[0]
    assert block.name == "Floyd Rose block route" and block.depth == 29.59
    assert block.min_x == pytest.approx(front + 15.88)
    assert block.max_x == pytest.approx(front + 15.88 + 20.96)
    # The slot sits inside the deeper clearance, not in the stud shelf.
    assert fine_tuners.min_x <= block.min_x and block.max_x < fine_tuners.max_x
    assert block.min_y == pytest.approx(-45.85 + 9.86, abs=0.01)
    assert block.max_y == pytest.approx(49.4 - 2.54, abs=0.01)
    spring = hardware.rear_cavities[0]
    assert spring.cavity.name == "Floyd Rose spring cavity"
    assert spring.cavity.depth == 16.13 and spring.cover_recess.depth == 2.0
    assert spring.cavity.length_x == 123.19 and spring.cavity.length_y == 56.64
    assert spring.cavity.max_x == pytest.approx(front + 48.27)
    (pocket,) = spring.steps
    assert pocket.depth == 28.19 and pocket.length_x == 11.43
    assert pocket.max_x == pytest.approx(spring.cavity.max_x)
    assert pocket.min_x == pytest.approx(block.max_x)
    assert spring.depth == 28.19


def test_floyd_rose_mirrors_for_the_other_handedness() -> None:
    lefty = FloydRoseSpec().hardware(609.6, 44.0)
    righty = FloydRoseSpec(treble_side="-y").hardware(609.6, 44.0)

    assert righty.top_cavities[0].min_y == pytest.approx(-49.4)
    assert righty.top_cavities[0].max_y == pytest.approx(45.85)
    assert righty.through_cavities[0].min_y == pytest.approx(
        -lefty.through_cavities[0].max_y
    )


def test_floyd_rose_rejects_a_body_too_thin_for_its_spring_cavity() -> None:
    with pytest.raises(BodyGeometryError, match="too thin"):
        FloydRoseSpec().hardware(609.6, 30.0)


def test_floyd_rose_rejects_a_body_too_thick_for_its_block_route() -> None:
    with pytest.raises(BodyGeometryError, match="too thick"):
        FloydRoseSpec().hardware(609.6, 46.0)


def test_floyd_rose_rejects_an_impossible_layout() -> None:
    with pytest.raises(BodyGeometryError, match="inside the recess width"):
        FloydRoseSpec(block_route_width=100.0).hardware(609.6, 44.0)
    with pytest.raises(BodyGeometryError, match="full-width part"):
        FloydRoseSpec(block_route_length=30.0).hardware(609.6, 44.0)


def test_tune_o_matic_is_four_holes_behind_the_scale_line() -> None:
    hardware = TuneOMaticSpec().hardware(609.6, 44.0)

    names = {hole.name: hole for hole in hardware.holes}
    assert set(names) == {
        "Bridge post bass",
        "Bridge post treble",
        "Tailpiece stud bass",
        "Tailpiece stud treble",
    }
    assert names["Bridge post bass"].center_x == pytest.approx(612.6)
    assert names["Bridge post bass"].center_y == pytest.approx(-37.0)
    assert names["Tailpiece stud treble"].center_x == pytest.approx(654.6)
    assert names["Tailpiece stud treble"].center_y == pytest.approx(41.0)
    assert hardware.top_cavities == () and hardware.rear_cavities == ()


def test_hardtail_strings_through_and_pilot_holes() -> None:
    hardware = HardtailSpec().hardware(609.6, 44.0)

    strings = [hole for hole in hardware.holes if "String" in hole.name]
    screws = [hole for hole in hardware.holes if "screw" in hole.name]
    assert len(strings) == 6 and len(screws) == 5
    assert all(hole.depth == 44.0 for hole in strings)
    assert sorted(round(hole.center_y, 2) for hole in strings) == [
        -26.25, -15.75, -5.25, 5.25, 15.75, 26.25
    ]
    assert all(hole.center_x == pytest.approx(599.6) for hole in screws)


def test_specs_round_trip_through_dicts() -> None:
    import dataclasses

    for kind, spec_class in BRIDGE_KINDS.items():
        spec = spec_class()
        rebuilt = bridge_spec_from_dict(dataclasses.asdict(spec))
        assert rebuilt == spec and rebuilt.kind == kind
    assert bridge_spec_from_dict(
        {"kind": "floyd_rose", "fine_tuner_depth": 12.0}
    ) == FloydRoseSpec(fine_tuner_depth=12.0)


def test_unknown_kind_or_field_is_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="Unknown bridge kind"):
        bridge_spec_from_dict({"kind": "banjo"})
    with pytest.raises(BodyGeometryError, match="Unknown kahler_7300 bridge field"):
        bridge_spec_from_dict({"kind": "kahler_7300", "springs": 3})


def test_non_positive_dimensions_are_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="positive"):
        KahlerBridgeSpec(baseplate_depth=0.0).hardware(609.6, 44.0)
