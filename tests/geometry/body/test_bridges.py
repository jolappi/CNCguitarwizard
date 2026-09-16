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


def test_floyd_rose_adds_studs_recess_block_route_and_spring_cavity() -> None:
    hardware = FloydRoseSpec().hardware(609.6, 44.0)

    studs = hardware.mounting.pivot_holes
    assert [(round(p.x, 1), p.y) for p in studs] == [(609.6, -37.0), (609.6, 37.0)]
    assert hardware.mounting.pivot_hole_diameter == 10.0
    recess = hardware.top_cavities[0]
    assert recess.name == "Tremolo recess" and recess.depth == 16.0
    assert recess.min_x == pytest.approx(603.6)
    block = hardware.through_cavities[0]
    assert block.depth == 44.0
    assert recess.min_x < block.min_x and block.max_x < recess.max_x
    spring = hardware.rear_cavities[0]
    assert spring.cavity.depth == pytest.approx(44.0 - 16.0 - 6.0)
    assert spring.cover_recess.depth == 2.0
    assert spring.cavity.length_y == 95.0


def test_floyd_rose_rejects_a_body_too_thin_for_its_spring_cavity() -> None:
    with pytest.raises(BodyGeometryError, match="too thin"):
        FloydRoseSpec().hardware(609.6, 24.0)


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
    assert bridge_spec_from_dict({"kind": "floyd_rose", "recess_depth": 14.0}) == (
        FloydRoseSpec(recess_depth=14.0)
    )


def test_unknown_kind_or_field_is_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="Unknown bridge kind"):
        bridge_spec_from_dict({"kind": "banjo"})
    with pytest.raises(BodyGeometryError, match="Unknown kahler_7300 bridge field"):
        bridge_spec_from_dict({"kind": "kahler_7300", "springs": 3})


def test_non_positive_dimensions_are_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="positive"):
        KahlerBridgeSpec(baseplate_depth=0.0).hardware(609.6, 44.0)
