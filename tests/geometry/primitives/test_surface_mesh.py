"""Tests for immutable three-dimensional surface primitives."""

from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.primitives import Point3D, QuadFace, SurfaceMesh


def test_surface_mesh_reports_vertex_and_face_counts() -> None:
    first_row = (Point3D(0.0, -1.0, 0.0), Point3D(0.0, 1.0, 0.0))
    second_row = (Point3D(1.0, -1.0, 0.0), Point3D(1.0, 1.0, 0.0))
    face = QuadFace(first_row[0], first_row[1], second_row[1], second_row[0])
    mesh = SurfaceMesh((first_row, second_row), (face,))

    assert mesh.vertex_count == 4
    assert mesh.face_count == 1


def test_point3d_is_immutable() -> None:
    point = Point3D(1.0, 2.0, 3.0)

    with pytest.raises(FrozenInstanceError):
        point.z = 4.0
