"""Tests for the complete Prototype001 parameter preset."""

from dataclasses import FrozenInstanceError, replace

import pytest

from cncguitarwizard.geometry.body import FloydRoseSpec, HardtailSpec, TuneOMaticSpec
from cncguitarwizard.geometry.exceptions import (
    HeadstockGeometryError,
    NeckGeometryError,
)
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters


def test_default_preset_builds_every_locked_component() -> None:
    parameters = Prototype001Parameters()
    geometry = parameters.build()

    assert geometry.neck_outline.scale_length == 609.6
    assert geometry.neck_outline.fret_count == 24
    assert geometry.neck_outline.nut_width == 42.0
    assert geometry.neck_outline.heel_width == 56.0
    assert geometry.neck_outline.heel_length == 4.0
    assert parameters.heel_mounting_length == 54.0
    assert geometry.neck_surface.heel_flat_start_offset == pytest.approx(50.0)
    assert geometry.fretboard_surface.radius == 430.0
    assert geometry.fretboard_surface.center_thickness == 6.0
    assert geometry.neck_surface.first_fret_thickness == 11.0
    assert geometry.neck_surface.twelfth_fret_thickness == 13.0
    assert (
        geometry.neck_surface.first_fret_thickness
        + geometry.fretboard_surface.center_thickness
        == 17.0
    )
    assert (
        geometry.neck_surface.twelfth_fret_thickness
        + geometry.fretboard_surface.center_thickness
        == 19.0
    )
    assert geometry.neck_surface.final_fret_thickness == 20.0
    assert geometry.neck_surface.nut_transition_thickness == 16.0
    assert geometry.neck_surface.nut_shelf_length == 5.0
    assert parameters.headstock_volute_length == 12.0
    assert geometry.neck_surface.nut_transition_length == 12.0
    assert geometry.neck_surface.nut_volute_depth == 0.0
    assert geometry.neck_surface.nut_volute_peak_fraction == 0.25
    assert parameters.headstock_root_side_extension == 15.0
    assert geometry.neck_surface.nut_root_side_extension == 15.0
    assert parameters.nut_end_u_trim_depth == 12.0
    assert geometry.nut_end_u_trim_depth == 12.0
    assert parameters.nut_end_u_side_fillet_radius == 2.0
    assert geometry.nut_end_u_side_fillet_radius == 2.0
    assert parameters.headstock_outer_d_profile_guide_extension == 0.0
    assert geometry.headstock_outer_d_profile_guide_extension == 0.0
    assert geometry.neck_surface._nut_transition_blend_at(-6.0) == 1.0
    assert geometry.neck_surface._nut_transition_blend_at(-5.0, 0.0) == 1.0
    assert geometry.neck_surface._nut_transition_blend_at(-5.0, 1.0) == 0.0
    assert geometry.neck_surface._nut_transition_blend_at(0.0, 0.0) == 0.0
    assert geometry.neck_surface._nut_transition_blend_at(12.0) == 0.0
    assert parameters.heel_root_length == 45.0
    assert geometry.neck_surface.heel_transition_length == 45.0
    assert parameters.heel_root_center_extension == 15.0
    assert geometry.neck_surface.heel_root_center_extension == 15.0
    assert geometry.neck_surface.heel_scoop_depth == 1.5
    assert geometry.neck_surface.preserve_d_profile_at_heel is False
    assert geometry.neck_surface.exponent == 2.0
    assert geometry.fretboard_surface.end_extension == 4.0
    assert geometry.fret_layout.fretboard.nut_corner_radius == 0.0
    assert geometry.fretboard_surface.station_positions[-1] == pytest.approx(
        geometry.neck_outline.last_fret_position + 4.0
    )
    assert geometry.neck_surface.station_positions[-1] == pytest.approx(
        geometry.neck_outline.last_fret_position + parameters.heel_length
    )
    assert geometry.truss_rod_channel.length == 440.0
    assert geometry.headstock.thickness == 16.0
    assert parameters.headstock_root_length == 45.0
    assert parameters.headstock_shoulder_distance == 45.0
    assert len(geometry.tuner_layout.holes) == 6
    assert geometry.tuner_layout.station_distances == (55.0, 85.0, 110.0)
    assert geometry.tuner_layout.side_offsets == (15.0, 12.0, 10.0)
    assert geometry.tuner_layout.minimum_side_edge_clearance >= 8.0
    assert geometry.tuner_layout.minimum_side_edge_clearance == pytest.approx(
        9.901099,
        abs=0.000001,
    )
    assert len(geometry.fret_layout.slots) == 24
    assert geometry.fret_slot_width == 0.6
    assert geometry.fret_slot_depth == 2.7
    assert geometry.inlay_layout.depth == 2.0
    assert geometry.inlay_layout.fretboard_surface is geometry.fretboard_surface
    assert len(geometry.inlay_layout.markers) == 12
    assert {
        marker.fret_number
        for marker in geometry.inlay_layout.markers
    } == {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}
    assert geometry.body.thickness == 44.0
    assert geometry.body.neck_pocket.max_x == pytest.approx(
        geometry.neck_outline.last_fret_position + parameters.heel_length
    )
    # The pocket is the neck's own tapered outline plus clearance: as
    # wide as the heel at its tail wall, narrower at its nut-ward end.
    pocket = geometry.body.neck_pocket
    clearance = parameters.body_neck_pocket_clearance
    assert pocket.max_x - pocket.min_x == pytest.approx(
        parameters.body_neck_pocket_length
    )
    assert pocket.max_y == pytest.approx(parameters.heel_width / 2.0 + clearance)
    nut_end_half_width = max(
        point.y for point in pocket.outline if point.x == pytest.approx(pocket.min_x)
    )
    assert nut_end_half_width < parameters.heel_width / 2.0
    assert nut_end_half_width > parameters.nut_width / 2.0
    # The DXF's own pickup placements, verbatim: neck route starts 10 mm
    # past the pocket's tail wall.
    neck_pickup = geometry.body.neck_pickup
    assert neck_pickup.min_x == pytest.approx(
        geometry.body.neck_pocket.max_x + 10.0, abs=0.01
    )
    assert neck_pickup.min_y + neck_pickup.max_y == pytest.approx(0.0, abs=0.01)
    # The DXF's own route: 41 wide, 85.9 long over the mounting ears.
    assert neck_pickup.max_x - neck_pickup.min_x == pytest.approx(41.0)
    assert neck_pickup.max_y - neck_pickup.min_y == pytest.approx(85.916)
    bridge_pickup = geometry.body.bridge_pickup
    assert bridge_pickup.min_x + bridge_pickup.max_x == pytest.approx(2 * 587.87)
    assert geometry.body.bridge_mounting.reference_x == 609.6
    assert geometry.body.bridge_mounting.pivot_holes == ()
    # Fixed Kahler: no sustain block, no rear bridge cavity.
    assert geometry.body.bridge_mounting.sustain_block_cavity is None
    # Rear-routed electronics, both straight from the DXF: the almond
    # control cavity behind the bridge and the round switch cavity at
    # the upper-horn root, each 8 mm short of the top with a 2 mm cover
    # ledge (the drawing's own outer ring/circle).
    control = geometry.body.control_cavity
    assert control is not None
    assert control.cavity.min_x > geometry.body.bridge_pickup.max_x
    # Left-handed: controls on the +Y lower bout, switch on the -Y horn.
    assert control.cavity.min_y > 0.0
    assert control.depth == pytest.approx(36.0)
    assert control.cover_recess.depth == 2.0
    assert control.cover_recess.min_x < control.cavity.min_x
    assert control.cover_recess.max_x > control.cavity.max_x
    switch = geometry.body.switch_cavity
    assert switch is not None
    assert switch.cavity.diameter == pytest.approx(43.972)
    assert switch.cover_recess.diameter == pytest.approx(59.452)
    assert switch.cavity.center_y < 0.0
    assert switch.depth == pytest.approx(36.0)
    assert switch.cover_recess.depth == 2.0
    assert geometry.body.battery_cavity is None
    assert geometry.body.rear_cavities == (control, switch)
    assert len(geometry.body.extra_cavities) == 1
    assert geometry.body.extra_cavities[0].name == "Bridge baseplate cutout"
    assert geometry.body.extra_cavities[0].depth == 25.0
    # Shaft holes clean through the top wall into their rear cavities,
    # plus a screw-tip recess under each pickup mounting ear.
    holes = {hole.name: hole for hole in geometry.body.holes}
    assert len(holes) == 7
    assert holes["Switch shaft hole"].depth == parameters.body_thickness
    assert holes["Switch shaft hole"].center_x == switch.cavity.center_x
    assert holes["Switch shaft hole"].center_y == switch.cavity.center_y
    assert holes["Pot 1 shaft hole"].depth == parameters.body_thickness
    assert holes["Pot 2 shaft hole"].diameter == 10.0
    recess = holes["Bridge pickup treble screw recess"]
    assert recess.center_x == pytest.approx(
        parameters.scale_length - parameters.body_bridge_pickup_offset
    )
    assert recess.center_y == pytest.approx(39.95)
    assert recess.depth == pytest.approx(30.0)
    assert geometry.joint_fillet_radius == 3.0
    assert geometry.headstock_root_swell == 0.0
    assert geometry.heel_nose_radius == 0.0
    assert geometry.heel_block_start_offset == pytest.approx(50.0)
    assert (
        geometry.heel_block_start_offset
        - geometry.neck_surface.heel_flat_start_offset
        == 0.0
    )


def test_preset_headstock_thickness_is_configurable_in_supported_range() -> None:
    geometry = replace(
        Prototype001Parameters(),
        headstock_thickness=14.0,
    ).build()

    assert geometry.headstock.thickness == 14.0


def test_preset_keeps_an_explicit_native_volute_depth() -> None:
    geometry = replace(
        Prototype001Parameters(),
        headstock_volute_depth=2.0,
    ).build()

    assert geometry.neck_surface.nut_volute_depth == 2.0


def test_preset_keeps_an_explicit_root_swell_as_an_optional_volute() -> None:
    geometry = replace(
        Prototype001Parameters(),
        headstock_volute_depth=0.0,
        headstock_root_swell=1.25,
    ).build()

    assert geometry.neck_surface.nut_volute_depth == 1.25



def test_preset_rejects_unsupported_headstock_thickness() -> None:
    with pytest.raises(HeadstockGeometryError):
        replace(
            Prototype001Parameters(),
            headstock_thickness=13.9,
        ).build()


def test_preset_rejects_fretboard_thicker_than_neck_total() -> None:
    with pytest.raises(NeckGeometryError):
        replace(
            Prototype001Parameters(),
            first_fret_thickness=5.0,
        ).build()


def test_preset_rejects_heel_mounting_block_shorter_than_40_mm() -> None:
    with pytest.raises(NeckGeometryError, match="at least 40 mm"):
        replace(
            Prototype001Parameters(),
            heel_mounting_length=39.9,
        ).build()


@pytest.mark.parametrize("length", (4.9, 30.1))
def test_preset_rejects_volute_outside_supported_range(length: float) -> None:
    with pytest.raises(NeckGeometryError, match="between 5 and 30 mm"):
        replace(
            Prototype001Parameters(),
            headstock_volute_length=length,
        ).build()


@pytest.mark.parametrize("length", (4.9, 150.0))
def test_preset_rejects_headstock_root_outside_supported_range(
    length: float,
) -> None:
    """The plan root must lie inside the tapered headstock blank."""
    with pytest.raises(NeckGeometryError, match="Headstock root length"):
        replace(
            Prototype001Parameters(),
            headstock_root_length=length,
        ).build()


@pytest.mark.parametrize("swell", (-0.1, 3.1))
def test_preset_rejects_headstock_root_swell_outside_supported_range(
    swell: float,
) -> None:
    with pytest.raises(NeckGeometryError, match="Headstock root swell"):
        replace(Prototype001Parameters(), headstock_root_swell=swell).build()


@pytest.mark.parametrize("extension", (-0.1, 30.1))
def test_preset_rejects_outer_d_profile_guide_outside_supported_range(
    extension: float,
) -> None:
    with pytest.raises(NeckGeometryError, match="Outer D-profile guide"):
        replace(
            Prototype001Parameters(),
            headstock_outer_d_profile_guide_extension=extension,
        ).build()


def test_preset_uses_root_lengths_without_reducing_flat_heel() -> None:
    """Root tuning must never shorten the user-facing bolt-on block."""
    parameters = replace(
        Prototype001Parameters(),
        headstock_root_length=50.0,
        headstock_root_side_extension=10.0,
        heel_root_length=40.0,
        heel_root_center_extension=12.0,
    )
    geometry = parameters.build()

    assert geometry.headstock.plan.shoulder_distance == 50.0
    assert geometry.neck_surface.nut_root_side_extension == 10.0
    assert geometry.neck_surface.heel_transition_length == 40.0
    assert geometry.neck_surface.heel_root_center_extension == 12.0
    assert geometry.neck_surface.heel_flat_start_offset == pytest.approx(50.0)


def test_preset_parameters_are_immutable() -> None:
    parameters = Prototype001Parameters()

    with pytest.raises(FrozenInstanceError):
        parameters.scale_length = 647.7


@pytest.mark.parametrize(
    ("spec", "overrides"),
    [
        (FloydRoseSpec(), {}),
        (TuneOMaticSpec(), {}),
        (HardtailSpec(), {}),
    ],
)
def test_every_bridge_kind_fits_the_prototype_body(spec, overrides) -> None:  # type: ignore[no-untyped-def]
    geometry = replace(Prototype001Parameters(), body_bridge=spec, **overrides).build()
    body = geometry.body

    if isinstance(spec, FloydRoseSpec):
        # Floyd Rose studs sit 11.9 mm ahead of the scale line.
        assert body.bridge_mounting.reference_x == pytest.approx(609.6 - 11.9)
    else:
        assert body.bridge_mounting.reference_x >= 609.6
    for hole in body.holes:
        assert point_in_polygon(hole.center, body.outline.points)
    if isinstance(spec, FloydRoseSpec):
        assert [c.name for c in body.through_cavities] == ["Floyd Rose block route"]
        assert "Floyd Rose spring cavity" in [r.name for r in body.rear_cavities]
        assert len(body.bridge_mounting.pivot_holes) == 2
    else:
        assert body.through_cavities == ()


def test_the_bridge_pickup_moves_forward_to_make_room_for_a_floyd_rose() -> None:
    parameters = replace(Prototype001Parameters(), body_bridge=FloydRoseSpec())
    body = parameters.build().body
    recess = body.extra_cavities[0]

    assert recess.name == "Floyd Rose recess"
    assert body.bridge_pickup.max_x == pytest.approx(
        recess.min_x - parameters.body_bridge_pickup_clearance
    )
    # The Kahler default keeps the DXF's own placement.
    assert Prototype001Parameters().build().body.bridge_pickup.max_x == (
        pytest.approx(609.6 - 21.73 + 20.5)
    )


def test_the_bridge_pickup_can_still_be_moved_further_by_hand() -> None:
    body = replace(
        Prototype001Parameters(),
        body_bridge=FloydRoseSpec(),
        body_bridge_pickup_offset=50.0,
    ).build().body

    assert body.bridge_pickup.max_x == pytest.approx(609.6 - 50.0 + 20.5)


@pytest.mark.parametrize("style", ["barbed_wire", "dot", "block"])
def test_inlay_styles_build(style: str) -> None:
    geometry = replace(Prototype001Parameters(), inlay_style=style).build()  # type: ignore[arg-type]

    assert geometry.inlay_layout.style == style
    assert len(geometry.inlay_layout.markers) == (10 if style == "block" else 12)


def test_body_follows_the_neck_and_bridge_follows_the_scale() -> None:
    """A longer scale moves the pocket with the heel and the bridge with the scale."""
    base = Prototype001Parameters().build()
    longer = replace(Prototype001Parameters(), scale_length=647.7).build()

    heel_shift = (
        longer.neck_outline.last_fret_position - base.neck_outline.last_fret_position
    )
    assert heel_shift > 0.0
    assert longer.body.neck_pocket.max_x == pytest.approx(
        longer.neck_outline.last_fret_position + longer.neck_outline.heel_length
    )
    assert longer.body.outline.points[0].x - base.body.outline.points[0].x == (
        pytest.approx(heel_shift)
    )
    assert longer.body.neck_pickup.min_x - base.body.neck_pickup.min_x == (
        pytest.approx(heel_shift)
    )
    assert longer.body.control_cavity is not None
    assert base.body.control_cavity is not None
    assert (
        longer.body.control_cavity.cavity.min_x - base.body.control_cavity.cavity.min_x
    ) == pytest.approx(heel_shift)
    baseplate = longer.body.extra_cavities[0]
    assert baseplate.min_x - base.body.extra_cavities[0].min_x == pytest.approx(
        647.7 - 609.6
    )
    assert longer.body.bridge_pickup.min_x - base.body.bridge_pickup.min_x == (
        pytest.approx(647.7 - 609.6)
    )
    assert longer.body.bridge_mounting.reference_x == 647.7


def test_fewer_frets_keep_the_neck_in_its_pocket() -> None:
    # A 22-fret neck is shorter, so the physical 440 mm truss rod no longer
    # fits; a shorter rod is a separate hardware choice.
    geometry = replace(
        Prototype001Parameters(), fret_count=22, truss_rod_length=400.0
    ).build()
    assert {marker.fret_number for marker in geometry.inlay_layout.markers} == {
        3, 5, 7, 9, 12, 15, 17, 19, 21
    }

    assert geometry.body.neck_pocket.max_x == pytest.approx(
        geometry.neck_outline.last_fret_position + geometry.neck_outline.heel_length
    )
    assert geometry.body.neck_pocket.max_x < 461.2
    assert geometry.body.bridge_mounting.reference_x == 609.6
