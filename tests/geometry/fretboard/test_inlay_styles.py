"""Tests for the dot and block inlay styles."""

import math

import pytest

from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.fretboard import FretboardSurface, InlayLayout


def surface() -> FretboardSurface:
    return FretboardSurface(609.6, 24, 42.0, 56.0, 430.0, 6.0, 9)


def test_dot_style_makes_round_markers_with_double_dots_at_the_octave() -> None:
    layout = InlayLayout(surface(), 2.0, style="dot", dot_diameter=6.0)

    assert len(layout.markers) == 12
    marker = layout.markers[0]
    centre_x = sum(p.x for p in marker.outline) / len(marker.outline)
    centre_y = sum(p.y for p in marker.outline) / len(marker.outline)
    assert centre_y == pytest.approx(0.0, abs=1e-9)
    assert all(
        math.hypot(p.x - centre_x, p.y - centre_y) == pytest.approx(3.0)
        for p in marker.outline
    )
    twelfth = [m for m in layout.markers if m.fret_number == 12]
    assert len(twelfth) == 2
    offsets = sorted(sum(p.y for p in m.outline) / len(m.outline) for m in twelfth)
    assert offsets[0] == pytest.approx(-offsets[1])
    assert offsets[1] > 6.0


def test_block_style_makes_one_tapered_block_per_fret() -> None:
    layout = InlayLayout(
        surface(), 2.0, style="block", block_length_fraction=0.5, block_edge_margin=5.0
    )

    assert len(layout.markers) == 10
    assert [m.fret_number for m in layout.markers] == [
        3, 5, 7, 9, 12, 15, 17, 19, 21, 24
    ]
    block = next(m for m in layout.markers if m.fret_number == 12)
    xs = [p.x for p in block.outline]
    ys = [p.y for p in block.outline]
    # Half a fret spacing long, and 5 mm inside each board edge (tapered).
    positions = {
        fret.number: fret.distance_from_nut
        for fret in FretCalculator.calculate(609.6, 24)
    }
    spacing = positions[12] - positions[11]
    assert max(xs) - min(xs) == pytest.approx(0.5 * spacing, abs=0.05)
    assert max(ys) < 28.0 - 5.0 and max(ys) > 21.0 - 5.0
    front_half = max(p.y for p in block.outline if p.x < min(xs) + 1.5)
    back_half = max(p.y for p in block.outline if p.x > max(xs) - 1.5)
    assert back_half > front_half


def test_invalid_style_settings_are_rejected() -> None:
    with pytest.raises(FretboardGeometryError, match="Unknown inlay style"):
        InlayLayout(surface(), 2.0, style="star")  # type: ignore[arg-type]
    with pytest.raises(FretboardGeometryError, match="fit inside"):
        InlayLayout(surface(), 2.0, style="dot", dot_diameter=50.0)
    with pytest.raises(FretboardGeometryError, match="fraction"):
        InlayLayout(surface(), 2.0, style="block", block_length_fraction=1.5)
