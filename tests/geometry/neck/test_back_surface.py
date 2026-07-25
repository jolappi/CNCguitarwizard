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


def test_flat_heel_has_vertical_sides_and_level_underside() -> None:
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

    assert heel_row[0].y == heel_row[1].y
    assert heel_row[-2].y == heel_row[-1].y
    assert {point.z for point in heel_row[1:-1]} == {-20.0}
    assert heel_row[0].z == heel_row[-1].z == 0.0


def test_flat_heel_can_begin_before_the_final_fret() -> None:
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

    assert {point.z for point in row[1:-1]} == {-20.0}
    assert row[0].y == row[1].y
    assert row[-2].y == row[-1].y


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
    assert {point.z for point in surface.mesh.rows[0][1:-1]} == {-16.0}


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
    ],
)
def test_surface_rejects_invalid_parameters(
    create_surface: Callable[[], NeckBackSurface],
) -> None:
    with pytest.raises(NeckGeometryError):
        create_surface()
