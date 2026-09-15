"""Tests for the loft-ready three-dimensional neck-back surface."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import NeckBackSurface, NeckOutline


def make_outline() -> NeckOutline:
    """Return the locked Prototype001 neck outline."""
    return NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)


def make_surface() -> NeckBackSurface:
    """Return a compact Prototype001 test surface."""
    return NeckBackSurface(
        make_outline(),
        17.0,
        19.0,
        20.0,
        profile_sample_count=5,
        segments_per_region=2,
    )


def test_surface_contains_all_locked_reference_stations() -> None:
    surface = make_surface()

    assert surface.station_positions_reference(1) in surface.station_positions
    assert surface.station_positions_reference(12) in surface.station_positions
    assert surface.neck_outline.last_fret_position in surface.station_positions
    assert surface.station_positions[-1] == pytest.approx(
        surface.neck_outline.last_fret_position
        + surface.neck_outline.heel_length
    )


def test_surface_center_depths_match_reference_thicknesses() -> None:
    surface = make_surface()
    center_index = surface.profile_sample_count // 2
    rows_by_position = dict(
        zip(surface.station_positions, surface.mesh.rows, strict=True)
    )

    assert rows_by_position[surface.station_positions_reference(1)][
        center_index
    ].z == pytest.approx(-17.0)
    assert rows_by_position[surface.station_positions_reference(12)][
        center_index
    ].z == pytest.approx(-19.0)
    assert rows_by_position[surface.neck_outline.last_fret_position][
        center_index
    ].z == pytest.approx(-20.0)
    assert surface.mesh.rows[-1][center_index].z == pytest.approx(-20.0)


def test_surface_mesh_has_expected_resolution() -> None:
    surface = make_surface()

    assert len(surface.station_positions) == 9
    assert surface.mesh.vertex_count == 9 * 5
    assert surface.mesh.face_count == 8 * 4


def test_surface_rows_follow_the_neck_taper() -> None:
    surface = make_surface()

    nut_width = surface.mesh.rows[0][-1].y - surface.mesh.rows[0][0].y
    final_width = surface.mesh.rows[-1][-1].y - surface.mesh.rows[-1][0].y

    assert nut_width == pytest.approx(42.0)
    assert final_width == pytest.approx(56.0)


def test_heel_rows_remain_parallel_and_constant_depth() -> None:
    surface = make_surface()
    final_fret_index = surface.station_positions.index(
        surface.neck_outline.last_fret_position
    )
    center_index = surface.profile_sample_count // 2

    for row in surface.mesh.rows[final_fret_index:]:
        width = row[-1].y - row[0].y
        assert width == pytest.approx(surface.neck_outline.heel_width)
        assert row[center_index].z == pytest.approx(
            -surface.final_fret_thickness
        )


def test_heel_terminal_section_remains_a_valid_rounded_profile() -> None:
    surface = NeckBackSurface(
        make_outline(),
        17.0,
        19.0,
        20.0,
        heel_transition_length=35.0,
        profile_sample_count=5,
        segments_per_region=2,
    )
    heel_row = surface.mesh.rows[-1]

    assert heel_row[0].y < heel_row[1].y
    assert heel_row[-2].y < heel_row[-1].y
    assert heel_row[2].z < heel_row[1].z
    assert heel_row[2].z == pytest.approx(-20.0, abs=2.0)
    assert heel_row[0].z == heel_row[-1].z == 0.0


def test_heel_terminal_profile_can_begin_before_the_final_fret() -> None:
    surface = NeckBackSurface(
        make_outline(),
        17.0,
        19.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        profile_sample_count=5,
        segments_per_region=2,
    )
    flat_start = surface.neck_outline.last_fret_position - 50.0
    row = surface.mesh.rows[surface.station_positions.index(flat_start)]
    expected_width = 42.0 + (56.0 - 42.0) * (
        flat_start / surface.neck_outline.last_fret_position
    )

    assert row[2].z == pytest.approx(-20.0, abs=2.0)
    assert row[0].y < row[1].y
    assert row[-2].y < row[-1].y
    assert row[-1].y - row[0].y == pytest.approx(expected_width)


def test_heel_uses_a_tangent_three_dimensional_blend_not_a_bevel() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        profile_sample_count=5,
        segments_per_region=2,
    )
    flat_start = surface.neck_outline.last_fret_position - 50.0
    transition_start = flat_start - 35.0
    midpoint = transition_start + 17.5
    midpoint_row = surface.mesh.rows[
        surface.station_positions.index(midpoint)
    ]
    center_depth = -midpoint_row[surface.profile_sample_count // 2].z
    first_position = surface.station_positions_reference(1)
    twelfth_position = surface.station_positions_reference(12)
    playing_slope = (13.0 - 11.0) / (
        twelfth_position - first_position
    )
    start_depth = 13.0 + playing_slope * (
        transition_start - twelfth_position
    )
    straight_bevel_midpoint = (start_depth + 20.0) / 2.0

    assert start_depth < center_depth < 20.0
    assert center_depth != pytest.approx(straight_bevel_midpoint)
    assert surface._heel_transition_blend_at(transition_start) == 0.0
    assert surface._heel_transition_blend_at(flat_start) == 1.0


def test_heel_intermediate_section_is_a_widening_rounded_rectangle() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        profile_sample_count=9,
        segments_per_region=4,
    )
    flat_start = surface.neck_outline.last_fret_position - 50.0
    transition_start = flat_start - 35.0
    midpoint = transition_start + 17.5
    start_row = surface.mesh.rows[
        surface.station_positions.index(transition_start)
    ]
    midpoint_row = surface.mesh.rows[
        surface.station_positions.index(midpoint)
    ]
    center_index = surface.profile_sample_count // 2
    shoulder_index = 1

    assert midpoint_row[center_index].z < start_row[center_index].z
    assert abs(midpoint_row[shoulder_index].y) > abs(
        start_row[shoulder_index].y
    )
    assert midpoint_row[shoulder_index].z < 0.0
    assert midpoint_row[shoulder_index].z > midpoint_row[center_index].z


def test_heel_scoop_curves_inward_without_changing_end_tangencies() -> None:
    base = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        profile_sample_count=9,
        segments_per_region=4,
    )
    scooped = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        heel_scoop_depth=1.5,
        profile_sample_count=9,
        segments_per_region=4,
    )
    flat_start = base.neck_outline.last_fret_position - 50.0
    transition_start = flat_start - 35.0
    midpoint = transition_start + 17.5

    assert scooped._depth_at(midpoint) > base._depth_at(midpoint)
    assert scooped._depth_at(transition_start) == pytest.approx(
        base._depth_at(transition_start)
    )
    assert scooped._depth_at(flat_start) == pytest.approx(
        base._depth_at(flat_start)
    )
    assert scooped._depth_at(transition_start + 0.9 * 35.0) < 20.0


def test_rounded_heel_entry_preserves_the_d_profile() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        heel_flat_start_offset=50.0,
        preserve_d_profile_at_heel=True,
        profile_sample_count=5,
        segments_per_region=2,
    )
    heel_start = surface.neck_outline.last_fret_position - 50.0
    row = surface.mesh.rows[surface.station_positions.index(heel_start)]

    assert surface._heel_transition_blend_at(heel_start) == 0.0
    assert row[0].y != row[1].y
    assert row[-2].y != row[-1].y
    assert row[2].z == -surface.final_fret_thickness
    assert row[1].z > -surface.final_fret_thickness


def test_headstock_transition_blends_from_flat_sixteen_to_d_profile() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_transition_length=30.0,
        heel_transition_length=35.0,
        profile_sample_count=5,
        segments_per_region=2,
    )
    nut_row = surface.mesh.rows[0]
    transition_row = surface.mesh.rows[
        surface.station_positions.index(30.0)
    ]

    assert {point.z for point in nut_row[1:-1]} == {-16.0}
    assert transition_row[2].z == pytest.approx(-11.0)
    assert transition_row[1].z > -11.0


def test_headstock_volute_adds_smooth_local_back_depth() -> None:
    plain = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_transition_length=30.0,
        heel_transition_length=35.0,
    )
    volute = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_transition_length=30.0,
        nut_volute_depth=1.0,
        nut_volute_peak_fraction=0.35,
        heel_transition_length=35.0,
    )

    assert volute._depth_at(0.0) == pytest.approx(plain._depth_at(0.0))
    assert volute._depth_at(30.0) == pytest.approx(plain._depth_at(30.0))
    assert volute._depth_at(10.5) > plain._depth_at(10.5)


def test_scarf_root_starts_at_the_outer_d_profile_extension() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_transition_length=12.0,
        nut_root_side_extension=12.0,
        heel_transition_length=35.0,
    )

    assert surface.headstock_root_start_position == -12.0


def test_headstock_root_extends_the_side_profiles_toward_headstock() -> None:
    """The D profile must begin earlier at the sides than at the center."""
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_shelf_length=5.0,
        nut_transition_length=20.0,
        nut_root_side_extension=12.0,
        heel_transition_length=35.0,
    )

    assert surface._nut_transition_blend_at(-6.0, 0.0) == 1.0
    assert 0.0 < surface._nut_transition_blend_at(-6.0, 1.0) < 1.0
    assert surface._nut_transition_blend_at(-5.0, 0.0) == 1.0
    assert surface._nut_transition_blend_at(-5.0, 1.0) == 0.0
    assert surface._nut_transition_blend_at(0.0, 0.0) == 0.0
    assert surface._nut_transition_blend_at(0.0, 1.0) == 0.0
    assert surface._nut_transition_blend_at(20.0, 1.0) == 0.0


def test_headstock_root_extension_reaches_the_broad_side_shoulders() -> None:
    """The U runout must be visible before the outermost profile point."""
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_shelf_length=5.0,
        nut_transition_length=12.0,
        nut_root_side_extension=12.0,
        heel_transition_length=35.0,
    )
    plain_surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_shelf_length=5.0,
        nut_transition_length=12.0,
        heel_transition_length=35.0,
    )

    row = surface._build_profile_row(-8.0)
    plain_row = plain_surface._build_profile_row(-8.0)
    center_index = surface.profile_sample_count // 2
    shoulder_index = center_index + surface.profile_sample_count // 4

    assert row[center_index].z == pytest.approx(-16.0)
    assert row[shoulder_index].z > plain_row[shoulder_index].z


def test_fixed_nut_shelf_keeps_center_flat_but_lets_sides_reach_d_profile() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_shelf_length=5.0,
        nut_transition_length=30.0,
        heel_transition_length=35.0,
    )

    assert surface._nut_transition_blend_at(-5.0, 0.0) == 1.0
    assert surface._nut_transition_blend_at(-5.0, 1.0) == 0.0
    assert surface._nut_transition_blend_at(-2.5, 0.0) > 0.0
    assert surface._nut_transition_blend_at(-2.5, 1.0) == 0.0
    assert surface._nut_transition_blend_at(0.0, 0.0) == 0.0


def test_heel_root_starts_at_the_center_before_the_side_edges() -> None:
    """The heel root must form one rounded, center-leading runout."""
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        heel_transition_length=35.0,
        heel_flat_start_offset=50.0,
        heel_root_center_extension=15.0,
    )
    flat_start = surface.neck_outline.last_fret_position - 50.0
    before_side_runout = flat_start - 40.0

    assert surface._heel_transition_blend_at(
        before_side_runout,
        0.0,
    ) == 0.0
    assert surface._heel_transition_blend_at(
        before_side_runout,
        1.0,
    ) > 0.0
    assert surface._heel_transition_blend_at(flat_start, 0.0) == 1.0
    assert surface._heel_transition_blend_at(flat_start, 1.0) == 1.0


def test_nut_shelf_extends_six_millimetres_before_fretboard() -> None:
    surface = NeckBackSurface(
        make_outline(),
        11.0,
        13.0,
        20.0,
        nut_transition_thickness=16.0,
        nut_shelf_length=6.0,
        nut_transition_length=30.0,
        heel_transition_length=35.0,
        profile_sample_count=5,
        segments_per_region=2,
    )

    assert surface.station_positions[0] == -6.0
    assert surface.station_positions_reference(1) == pytest.approx(
        34.214219,
        abs=0.000001,
    )
    center_index = surface.profile_sample_count // 2
    first_row = surface.mesh.rows[0]

    assert first_row[center_index].z == -16.0
    assert first_row[1].z > -16.0
    assert first_row[-2].z > -16.0


def test_surface_is_immutable() -> None:
    surface = make_surface()

    with pytest.raises(FrozenInstanceError):
        surface.exponent = 4.0


@pytest.mark.parametrize(
    "create_surface",
    [
        lambda: NeckBackSurface(make_outline(), 20.0, 19.0, 20.0),
        lambda: NeckBackSurface(make_outline(), 17.0, 21.0, 20.0),
        lambda: NeckBackSurface(make_outline(), 17.0, 19.0, 20.0, exponent=1.0),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            profile_sample_count=4,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            segments_per_region=0,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            nut_transition_thickness=16.0,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            heel_transition_length=500.0,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            heel_flat_start_offset=500.0,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            nut_shelf_length=-1.0,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            nut_transition_length=30.0,
            nut_root_side_extension=30.1,
        ),
        lambda: NeckBackSurface(
            make_outline(),
            17.0,
            19.0,
            20.0,
            heel_transition_length=35.0,
            heel_flat_start_offset=50.0,
            heel_root_center_extension=100.0,
        ),
    ],
)
def test_surface_rejects_invalid_parameters(
    create_surface: Callable[[], NeckBackSurface],
) -> None:
    with pytest.raises(NeckGeometryError):
        create_surface()
