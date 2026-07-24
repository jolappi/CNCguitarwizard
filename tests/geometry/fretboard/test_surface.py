"""Tests for the loft-ready three-dimensional fretboard surface."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fretboard import FretboardSurface


def make_surface() -> FretboardSurface:
    """Return a compact Prototype001 fretboard test surface."""
    return FretboardSurface(
        scale_length=609.6,
        fret_count=24,
        nut_width=42.0,
        last_fret_width=56.0,
        radius=430.0,
        center_thickness=6.0,
        profile_sample_count=5,
    )


def test_surface_has_one_row_at_nut_and_each_fret() -> None:
    surface = make_surface()

    assert len(surface.station_positions) == 25
    assert surface.station_positions[0] == 0.0
    assert surface.station_positions[-1] == pytest.approx(457.2)


def test_surface_mesh_has_expected_resolution() -> None:
    surface = make_surface()

    assert surface.mesh.vertex_count == 25 * 5
    assert surface.mesh.face_count == 24 * 4


def test_surface_tapers_from_nut_to_final_fret_width() -> None:
    surface = make_surface()
    nut_row = surface.mesh.rows[0]
    final_row = surface.mesh.rows[-1]

    assert nut_row[-1].y - nut_row[0].y == pytest.approx(42.0)
    assert final_row[-1].y - final_row[0].y == pytest.approx(56.0)


def test_surface_preserves_center_thickness_and_radius_drop() -> None:
    surface = make_surface()
    center_index = surface.profile_sample_count // 2
    final_row = surface.mesh.rows[-1]
    expected_edge_thickness = 6.0 - (
        430.0 - (430.0**2 - 28.0**2) ** 0.5
    )

    assert final_row[center_index].z == pytest.approx(6.0)
    assert final_row[0].z == pytest.approx(expected_edge_thickness)
    assert final_row[-1].z == pytest.approx(expected_edge_thickness)


def test_surface_is_immutable() -> None:
    surface = make_surface()

    with pytest.raises(FrozenInstanceError):
        surface.radius = 400.0


@pytest.mark.parametrize(
    "create_surface",
    [
        lambda: FretboardSurface(0.0, 24, 42.0, 56.0, 430.0, 6.0),
        lambda: FretboardSurface(609.6, 0, 42.0, 56.0, 430.0, 6.0),
        lambda: FretboardSurface(609.6, 24, 57.0, 56.0, 430.0, 6.0),
        lambda: FretboardSurface(609.6, 24, 42.0, 56.0, 28.0, 6.0),
        lambda: FretboardSurface(609.6, 24, 42.0, 56.0, 430.0, 0.1),
        lambda: FretboardSurface(
            609.6,
            24,
            42.0,
            56.0,
            430.0,
            6.0,
            profile_sample_count=4,
        ),
    ],
)
def test_surface_rejects_invalid_parameters(
    create_surface: Callable[[], FretboardSurface],
) -> None:
    with pytest.raises(FretboardGeometryError):
        create_surface()
