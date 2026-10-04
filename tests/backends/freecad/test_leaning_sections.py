"""Tests for leaning sections (slanted or fanned frets) in the FreeCAD script.

The script's coordinates are rounded (``SERIAL_DECIMALS``), which leaves a
leaning section a hair off its plane; FreeCAD then makes an invalid
fretboard loft and fails the fret slots' faces. The script puts each
section back onto its plane (``flattened``) first.
"""

from __future__ import annotations

import ast
import math
import re
import types
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.presets import Prototype001Parameters


class _Vector:
    """Just enough of ``FreeCAD.Vector`` for the script's ``flattened``."""

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x, self.y, self.z = x, y, z

    def __add__(self, other: _Vector) -> _Vector:
        return _Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: _Vector) -> _Vector:
        return _Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, factor: float) -> _Vector:
        return _Vector(self.x * factor, self.y * factor, self.z * factor)

    def dot(self, other: _Vector) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    @property
    def Length(self) -> float:  # noqa: N802 - FreeCAD's name
        return math.sqrt(self.dot(self))

    def normalize(self) -> None:
        length = self.Length
        self.x, self.y, self.z = self.x / length, self.y / length, self.z / length


def _off_plane(points: list[_Vector]) -> float:
    """Return how far the points stray from the plane through three of them."""
    a, b, c = points[0], points[len(points) // 3], points[2 * len(points) // 3]
    u, v = b - a, c - a
    normal = _Vector(
        u.y * v.z - u.z * v.y, u.z * v.x - u.x * v.z, u.x * v.y - u.y * v.x
    )
    normal.normalize()
    return max(abs((p - a).dot(normal)) for p in points)


@pytest.mark.parametrize(
    "overrides",
    [
        {"bass_scale_length": 863.6 + 50.8},
        {"fret_slant_angle": 5.0},
    ],
)
def test_leaning_sections_are_put_back_onto_their_planes(
    overrides: dict[str, float],
) -> None:
    base = Prototype001Parameters.for_instrument(
        "five_string_bass" if "bass_scale_length" in overrides else "electric_guitar"
    )
    source = FreeCADScriptExporter().render_prototype001(
        replace(base, nut_style="slot", **overrides).build()
    )
    sections = ast.literal_eval(
        re.search(r"^FRETBOARD_SECTION_POINTS = (.*)$", source, re.M).group(1)  # type: ignore[union-attr]
    )
    flattened_source = source[
        source.index("def flattened") : source.index("def make_loft")
    ]
    namespace: dict[str, object] = {"App": types.SimpleNamespace(Vector=_Vector)}
    exec(flattened_source, namespace)  # noqa: S102 - the script's own function
    flattened = namespace["flattened"]
    # Rounded, a leaning section strays off its plane...
    strays = [_off_plane([_Vector(*p) for p in section]) for section in sections]
    assert max(strays) > 1e-6
    # ...and goes back onto it.
    for section in sections:
        flat = flattened([_Vector(*p) for p in section])  # type: ignore[operator]
        assert _off_plane(flat) < 1e-9
        assert (
            max(
                abs(q.x - p[0]) + abs(q.y - p[1]) + abs(q.z - p[2])
                for p, q in zip(section, flat, strict=True)
            )
            < 1e-3
        )
    # The loft, the fret slots and the board's run-on behind a slotted nut
    # all use it.
    assert "vectors = flattened([App.Vector(*point) for point in points])" in source
    assert "profile = flattened(profile)" in source
    assert "board_end = flattened(" in source
