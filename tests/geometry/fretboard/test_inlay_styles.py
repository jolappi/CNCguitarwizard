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
        3,
        5,
        7,
        9,
        12,
        15,
        17,
        19,
        21,
        24,
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


def _span(marker, axis: str) -> tuple[float, float]:  # type: ignore[no-untyped-def]
    values = [getattr(p, axis) for p in marker.outline]
    return min(values), max(values)


def _area(marker) -> float:  # type: ignore[no-untyped-def]
    points = marker.outline
    return 0.5 * sum(
        a.x * b.y - b.x * a.y for a, b in zip(points, (*points[1:], points[0]))
    )


@pytest.mark.parametrize(
    "style", ["trapezoid", "sharktooth", "parallelogram", "diamond", "split_block"]
)
def test_every_board_style_spans_the_board_between_its_frets(style: str) -> None:
    block = InlayLayout(surface(), 2.0, style="block")
    layout = InlayLayout(surface(), 2.0, style=style)
    pieces = 2 if style == "split_block" else 1

    assert len(layout.markers) == pieces * len(block.markers)
    for marker in layout.markers:
        # Counter-clockwise, simple outlines inside the block's bounds.
        assert _area(marker) > 0.0
        (bx0, bx1), (by0, by1) = (
            _span(
                next(b for b in block.markers if b.fret_number == marker.fret_number),
                axis,
            )
            for axis in "xy"
        )
        lean = 0.35 * (bx1 - bx0) + 1.0 if style == "parallelogram" else 0.0
        x0, x1 = _span(marker, "x")
        y0, y1 = _span(marker, "y")
        assert bx0 - lean - 1e-6 <= x0 and x1 <= bx1 + 1e-6
        # (A shape moved along the tapered board reaches a hair wider.)
        assert by0 - 0.05 <= y0 and y1 <= by1 + 0.05


def test_the_trapezoid_and_sharktooth_are_long_on_the_bass_side() -> None:
    for bass_sign in (-1.0, 1.0):
        for style in ("trapezoid", "sharktooth"):
            (marker, *_) = InlayLayout(
                surface(), 2.0, style=style, bass_sign=bass_sign
            ).markers
            points = marker.outline
            cross = [
                a.x * b.y - b.x * a.y for a, b in zip(points, (*points[1:], points[0]))
            ]
            centre_y = sum(
                (a.y + b.y) * c
                for a, b, c in zip(points, (*points[1:], points[0]), cross)
            ) / (3.0 * sum(cross))
            # The area lies toward the bass side.
            assert centre_y * bass_sign > 1.0


def test_a_split_block_leaves_a_gap_along_its_diagonal() -> None:
    first, second = [
        m
        for m in InlayLayout(surface(), 2.0, style="split_block").markers
        if m.fret_number == 3
    ]

    def to_segment(point, a, b) -> float:  # type: ignore[no-untyped-def]
        dx, dy = b.x - a.x, b.y - a.y
        t = max(
            0.0,
            min(
                1.0, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)
            ),
        )
        return math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy)

    edges = list(zip(second.outline, (*second.outline[1:], second.outline[0])))
    gap = min(to_segment(p, a, b) for p in first.outline for a, b in edges)
    assert gap == pytest.approx(1.5, abs=0.1)


def test_the_web_form_offers_every_inlay_style() -> None:
    from cncguitarwizard.geometry.fretboard.inlay_layout import INLAY_STYLES
    from cncguitarwizard.webapp import parameter_schema

    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["inlay_style"]["options"] == list(INLAY_STYLES)
