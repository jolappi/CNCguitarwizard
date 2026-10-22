"""The volute seen from behind and above, shaded, for drawing it.

The back round the nut is drawn as lofted (its rows, the volute's wood
under them): seen at a slant from behind the neck, from the body's side
and above, the headstock at the top, lit from over the viewer's
shoulder, so the volute's crest and outline read as they would on the
guitar.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ...geometry.primitives import Point3D

VIEW_WIDTH = 520.0
"""The drawing's width, in its own units."""

VIEW_MARGIN = 12.0
"""Paper left round the drawing."""

VIEW_EYE = (0.55, -0.35, -0.76)
"""Toward the viewer, in the model frame: behind the neck (the back is
at negative ``z``), toward the body and the bass side."""

VIEW_LIGHT = (0.75, -0.5, -0.45)
"""Toward the light, in the model frame."""

VIEW_WOOD = (233, 211, 168)
"""The wood's colour, fully lit."""


Vector = tuple[float, float, float]


def render_volute_view_svg(rows: Sequence[Sequence[Point3D]]) -> str:
    """Return the back through ``rows`` seen from behind and above.

    Args:
        rows: The loft's rows round the nut, ordered along the neck, each
            across the back from one top edge to the other.

    Returns:
        A standalone SVG, the headstock at the top.
    """
    eye = _unit(VIEW_EYE)
    # Up on the paper is toward the headstock (the model's -x).
    up = _unit(_minus((-1.0, 0.0, 0.0), _scaled(eye, -eye[0])))
    right = _cross(up, eye)
    light = _unit(VIEW_LIGHT)
    faces: list[tuple[float, list[tuple[float, float]], float]] = []
    for near, far in zip(rows, rows[1:], strict=False):
        for index in range(len(near) - 1):
            corners = [
                _vector(near[index]),
                _vector(near[index + 1]),
                _vector(far[index + 1]),
                _vector(far[index]),
            ]
            normal = _cross(
                _minus(corners[1], corners[0]), _minus(corners[3], corners[0])
            )
            if _length(normal) == 0.0:
                continue
            normal = _unit(normal)
            if _dot(normal, eye) < 0.0:
                normal = _scaled(normal, -1.0)
            shade = 0.25 + 0.75 * max(0.0, _dot(normal, light))
            depth = sum(_dot(corner, eye) for corner in corners) / 4.0
            flat = [(_dot(corner, right), -_dot(corner, up)) for corner in corners]
            faces.append((depth, flat, shade))
    if not faces:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'
    xs = [x for _, flat, _ in faces for x, _ in flat]
    ys = [y for _, flat, _ in faces for _, y in flat]
    scale = (VIEW_WIDTH - 2.0 * VIEW_MARGIN) / (max(xs) - min(xs))
    height = (max(ys) - min(ys)) * scale + 2.0 * VIEW_MARGIN
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_WIDTH:g} '
        f'{height:.1f}" class="volute-view">',
        "<title>The volute seen from behind and above, as it is lofted</title>",
        f'<rect width="{VIEW_WIDTH:g}" height="{height:.1f}" fill="#f4efe4"/>',
    ]
    for _, flat, shade in sorted(faces, key=lambda face: face[0]):
        colour = "rgb({},{},{})".format(
            *(round(c * (0.35 + 0.65 * shade)) for c in VIEW_WOOD)
        )
        points = " ".join(
            f"{(x - min(xs)) * scale + VIEW_MARGIN:.1f},"
            f"{(y - min(ys)) * scale + VIEW_MARGIN:.1f}"
            for x, y in flat
        )
        parts.append(
            f'<polygon points="{points}" fill="{colour}" stroke="{colour}" '
            'stroke-width="0.6"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _vector(point: Point3D) -> Vector:
    return (point.x, point.y, point.z)


def _minus(a: Vector, b: Vector) -> Vector:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scaled(a: Vector, factor: float) -> Vector:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def _dot(a: Vector, b: Vector) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vector, b: Vector) -> Vector:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(a: Vector) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Vector) -> Vector:
    return _scaled(a, 1.0 / _length(a))
