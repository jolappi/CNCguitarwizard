"""Tests for the seven- and eight-string Floyd Rose and Kahler, the
single-string bridges and the top-loaded hardtail."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.body import (
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    SingleStringBridgeSpec,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.presets import Prototype001Parameters

SEVEN = Prototype001Parameters.for_instrument("seven_string_guitar")
EIGHT = Prototype001Parameters.for_instrument("eight_string_guitar")
BASS = Prototype001Parameters.for_instrument("bass_guitar")


def test_the_six_string_floyd_rose_keeps_its_sheet() -> None:
    assert FloydRoseSpec().widths() == pytest.approx(
        (73.91, 45.845, 49.405, 71.12, 82.85, 28.19)
    )
    # A width set by hand stays; the ones left empty follow the studs.
    widths = FloydRoseSpec(pivot_stud_spacing=74.0, fine_tuner_width=70.0).widths()
    assert widths.bass_half_width == pytest.approx(37.0 + 8.89)
    assert widths.fine_tuner_width == 70.0


def test_the_seven_string_floyd_rose_follows_its_routing_sheet() -> None:
    """Floyd Rose's FR 7-String Routing sheet (mm)."""
    hardware = FloydRoseSpec(string_count=7).hardware(647.7, 44.45)
    studs = hardware.mounting.pivot_holes
    assert [p.y for p in studs] == pytest.approx([-42.29, 42.29])  # 84.58
    recess, fine_tuners = hardware.top_cavities
    # 105.92 wide: 8.89 + 84.58 + 12.45.
    assert recess.min_y == pytest.approx(-51.18)
    assert recess.max_y == pytest.approx(54.74)
    front = studs[0].x - 7.62
    # 81.79 wide behind the full-width part.
    assert max(p.y for p in recess.outline if p.x > front + 50) == (
        pytest.approx(81.79 / 2.0)
    )
    # The block slot: 93.52 wide, 9.86 in from the bass wall and 2.54
    # from the treble one.
    block = hardware.through_cavities[0]
    assert block.max_y - block.min_y == pytest.approx(93.52, abs=0.01)
    assert block.min_y == pytest.approx(-51.18 + 9.86, abs=0.01)
    assert block.max_y == pytest.approx(54.74 - 2.54, abs=0.01)
    assert block.depth == 29.59 and fine_tuners.depth == 11.18
    # Drawn with no block pocket deeper than the spring cavity.
    spring = hardware.rear_cavities[0]
    assert spring.steps == () and spring.depth == 16.13
    assert any("7-String Routing sheet" in note for note in hardware.notes)
    assert any("block_pocket_depth to 28.19" in note for note in hardware.notes)


def test_the_eight_string_floyd_rose_is_widened_to_its_studs() -> None:
    hardware = FloydRoseSpec(string_count=8).hardware(685.8, 44.45)
    assert [p.y for p in hardware.mounting.pivot_holes] == pytest.approx(
        [-47.75, 47.75]
    )
    recess = hardware.top_cavities[0]
    assert recess.max_y - recess.min_y == pytest.approx(95.5 + 8.89 + 12.45)
    assert hardware.through_cavities[0].length_y == pytest.approx(95.5 + 8.94)
    assert hardware.rear_cavities[0].steps == ()
    assert any("publishes no 8-string routing" in n for n in hardware.notes)


def test_floyd_rose_sizes_that_do_not_exist_are_refused() -> None:
    with pytest.raises(BodyGeometryError, match="6, 7 or 8 strings"):
        FloydRoseSpec(string_count=9).hardware(685.8, 44.45)
    with pytest.raises(BodyGeometryError, match="at least as deep"):
        FloydRoseSpec(block_pocket_depth=10.0).hardware(647.7, 44.45)
    # As deep as the spring cavity: no pocket.
    flat = FloydRoseSpec(block_pocket_depth=16.13).hardware(647.7, 44.45)
    assert flat.rear_cavities[0].steps == ()
    with pytest.raises(BodyGeometryError, match="pivot_stud_spacing"):
        FloydRoseSpec(pivot_stud_spacing=-1.0).widths()


def test_the_kahler_widens_for_seven_and_eight_strings() -> None:
    for strings, width in ((6, 65.04), (7, 85.36), (8, 85.36)):
        hardware = KahlerBridgeSpec(string_count=strings).hardware(647.7, 44.45)
        (cutout,) = hardware.top_cavities
        assert cutout.length_y == pytest.approx(width)
        assert cutout.length_x == 55.45 and cutout.depth == 25.0
    note = KahlerBridgeSpec(string_count=8).hardware(685.8, 44.45).notes[0]
    assert "Kahler 7328 (8 strings)" in note
    custom = KahlerBridgeSpec(string_count=7, baseplate_width=80.0)
    assert custom.hardware(647.7, 44.45).top_cavities[0].length_y == 80.0
    with pytest.raises(BodyGeometryError, match="6, 7 or 8 strings"):
        KahlerBridgeSpec(string_count=5).hardware(647.7, 44.45)


def test_seven_and_eight_string_guitars_take_them_with_their_nuts() -> None:
    for base, strings, nut in ((SEVEN, 7, "7-string"), (EIGHT, 8, "8-string")):
        geometry = replace(
            base, body_bridge=FloydRoseSpec(string_count=strings)
        ).build()
        assert geometry.locking_nut is not None
        assert geometry.locking_nut.spec.name == f"Floyd Rose {nut}"
        assert geometry.locking_nut.spec.width <= base.nut_width
        stud = geometry.body.bridge_mounting.pivot_stud_spacing
        assert stud == {7: 84.58, 8: 95.5}[strings]
        kahler = replace(base, body_bridge=KahlerBridgeSpec(string_count=strings))
        assert kahler.build().locking_nut is None
    # The eight-string nut is held by three screws.
    geometry = replace(EIGHT, body_bridge=FloydRoseSpec(string_count=8)).build()
    nut = geometry.locking_nut
    assert nut is not None
    assert [p.y for p in nut.screw_centres()] == pytest.approx([-13.3, 0.0, 13.3])
    plan = plan_neck_machining(geometry, NeckMachiningParameters())
    assert any("Drill its 3 screws'" in note for note in plan.top.notes)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert '"locking nut screw 3 in the neck"' in source


def test_a_bridge_for_other_strings_is_refused() -> None:
    with pytest.raises(BodyGeometryError, match="set for 6 strings"):
        replace(SEVEN, body_bridge=FloydRoseSpec()).body_layout()
    with pytest.raises(BodyGeometryError, match="made for 6 to 8 strings"):
        replace(BASS, body_bridge=FloydRoseSpec(string_count=4)).body_layout()
    with pytest.raises(BodyGeometryError, match="single-string bridges are 5 units"):
        replace(BASS, body_bridge=SingleStringBridgeSpec(string_count=5)).body_layout()


def test_single_string_bridges_stand_each_at_its_own_scale() -> None:
    fanned = replace(
        BASS,
        body_bridge=SingleStringBridgeSpec(),
        bass_scale_length=BASS.scale_length + 50.8,
    )
    geometry = fanned.build()
    holes = {hole.name: hole for hole in geometry.body.holes}
    skew = fanned.fret_skew
    lengths = []
    for string in range(1, 5):
        front = holes[f"String {string} bridge screw front pilot"]
        rear = holes[f"String {string} bridge screw rear pilot"]
        through = holes[f"String {string} bridge string through hole"]
        # Square to its string: the holes in a row along it.
        assert front.center_y == rear.center_y == through.center_y
        assert rear.center_x - front.center_x == pytest.approx(60.0 - 12.0)
        assert through.depth == fanned.body_thickness
        saddle = front.center_x - 6.0 + 15.0
        nut_y = front.center_y / 28.5 * 1.5 * fanned.nut_string_spacing
        lengths.append(saddle - skew.at(0.0) * nut_y)
    # The outer strings' saddles on the bass and treble scales.
    assert sorted(lengths) == pytest.approx(
        sorted([914.4, 897.467, 880.533, 863.6]), abs=0.01
    )
    notes = SingleStringBridgeSpec().hardware(863.6, 44.0, lean=0.5).notes
    assert "on the fanned bridge line" in notes[0]


def test_single_string_bridges_check_their_units() -> None:
    top_load = SingleStringBridgeSpec(string_through=False).hardware(863.6, 44.0)
    assert len(top_load.holes) == 8
    assert not any("through" in hole.name for hole in top_load.holes)
    plain = SingleStringBridgeSpec().hardware(863.6, 44.0)
    xs = [p.x for p in plain.footprint]
    assert (min(xs), max(xs)) == pytest.approx((863.6 - 15.0, 863.6 + 45.0))
    with pytest.raises(BodyGeometryError, match="overlap"):
        SingleStringBridgeSpec(unit_width=20.0).hardware(863.6, 44.0)
    with pytest.raises(BodyGeometryError, match="between its screws"):
        SingleStringBridgeSpec(string_hole_offset=50.0).hardware(863.6, 44.0)
    with pytest.raises(BodyGeometryError, match="scale point"):
        SingleStringBridgeSpec(front_reach=70.0).hardware(863.6, 44.0)
    # A guitar takes narrower units.
    guitar = replace(
        Prototype001Parameters(),
        body_bridge=SingleStringBridgeSpec(
            string_count=6,
            string_spacing=10.5,
            unit_width=10.0,
            unit_length=40.0,
            string_hole_offset=10.0,
        ),
    ).build()
    assert sum("bridge screw" in hole.name for hole in guitar.body.holes) == 12


def test_a_hardtail_can_be_top_loaded() -> None:
    top_load = HardtailSpec(string_through=False).hardware(647.7, 44.0)
    assert not any("through hole" in hole.name for hole in top_load.holes)
    assert len(top_load.holes) == 5
    assert "top-loaded" in top_load.notes[0]
    geometry = replace(
        BASS, body_bridge=replace(BASS.body_bridge, string_through=False)
    ).build()
    assert not any("through hole" in hole.name for hole in geometry.body.holes)
