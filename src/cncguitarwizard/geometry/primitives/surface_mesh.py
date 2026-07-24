"""Immutable quad-based surface mesh primitives."""

from __future__ import annotations

from dataclasses import dataclass

from .point3d import Point3D


@dataclass(frozen=True, slots=True)
class QuadFace:
    """Represent one ordered four-corner surface face."""

    first: Point3D
    second: Point3D
    third: Point3D
    fourth: Point3D


@dataclass(frozen=True, slots=True)
class SurfaceMesh:
    """Represent a backend-independent quad surface mesh.

    Args:
        rows: Ordered cross-section rows of equal point count.
        faces: Quad faces connecting adjacent rows.
    """

    rows: tuple[tuple[Point3D, ...], ...]
    faces: tuple[QuadFace, ...]

    @property
    def vertex_count(self) -> int:
        """Return the number of row vertices, including shared vertices."""
        return sum(len(row) for row in self.rows)

    @property
    def face_count(self) -> int:
        """Return the number of quad faces."""
        return len(self.faces)
