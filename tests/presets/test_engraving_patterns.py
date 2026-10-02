"""Tests for the engraving's other patterns: EVH stripes, flame, ripples, crackle."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.engraving import (
    ENGRAVING_PATTERNS,
    MIN_PATTERN_LINE,
    ROW_STEP,
    STRIPE_WIDTHS,
    EngravingArea,
    engraving_lines,
    pattern_lines,
)
from cncguitarwizard.webapp import parameter_schema

OTHERS = ("evh_stripes", "flame", "ripples", "crackle")


def _square(size: float) -> tuple[Point2D, ...]:
    half = size / 2.0
    return (
        Point2D(-half, -half),
        Point2D(half, -half),
        Point2D(half, half),
        Point2D(-half, half),
    )


def _length(line: tuple[Point2D, ...]) -> float:
    return sum(
        math.dist((a.x, a.y), (b.x, b.y)) for a, b in zip(line, line[1:], strict=False)
    )


AREA = EngravingArea(
    _square(300.0), 10.0, (_square(60.0),), ((Point2D(100.0, 100.0), 5.0),), 4.0
)


def test_the_scroll_is_the_drawings_pattern() -> None:
    assert ENGRAVING_PATTERNS[0] == "scroll"
    assert pattern_lines("scroll", AREA, 3, 50.0) == engraving_lines(AREA, 3, 50.0)
    with pytest.raises(ValueError, match="Unknown engraving pattern"):
        pattern_lines("tartan", AREA, 3, 50.0)


@pytest.mark.parametrize("pattern", OTHERS)
def test_every_pattern_is_seeded_and_stays_in_the_area(pattern: str) -> None:
    lines = pattern_lines(pattern, AREA, 3, 50.0)

    assert len(lines) > 5
    assert lines == pattern_lines(pattern, AREA, 3, 50.0)
    assert lines != pattern_lines(pattern, AREA, 4, 50.0)
    inside = _square(300.0 - 2 * 10.0 + 2 * ROW_STEP)
    for line in lines:
        assert _length(line) >= MIN_PATTERN_LINE - 1e-9
        for p in line:
            assert point_in_polygon(p, inside)
            # Clear of the kept-out square, grown round its corners.
            assert (
                math.hypot(max(abs(p.x) - 30.0, 0.0), max(abs(p.y) - 30.0, 0.0)) > 3.9
            )
            assert math.dist((p.x, p.y), (100.0, 100.0)) > 5.0 + 3.9


def test_evh_stripes_are_straight_bands_with_both_edges() -> None:
    open_area = EngravingArea(_square(300.0), 10.0, (), (), 4.0)
    lines = pattern_lines("evh_stripes", open_area, 5, 50.0)

    # Every piece is straight: its points on the chord between its ends.
    directions = []
    for line in lines:
        a, b = line[0], line[-1]
        chord = math.dist((a.x, a.y), (b.x, b.y))
        assert chord == pytest.approx(_length(line), rel=1e-6)
        directions.append(math.atan2(b.y - a.y, b.x - a.x) % math.pi)
    # An edge has a parallel partner a stripe's width away (its other
    # edge), unless a later stripe covers it there.
    paired = 0
    for line, angle in zip(lines, directions, strict=True):
        for other, other_angle in zip(lines, directions, strict=True):
            if other is line or abs(angle - other_angle) > 1e-6:
                continue
            ux, uy = math.cos(angle), math.sin(angle)
            gap = abs((other[0].x - line[0].x) * -uy + (other[0].y - line[0].y) * ux)
            if STRIPE_WIDTHS[0] - 1e-6 <= gap <= STRIPE_WIDTHS[1] + 1e-6:
                paired += 1
                break
    assert paired >= len(lines) // 2


def test_flame_lines_never_cross() -> None:
    open_area = EngravingArea(_square(300.0), 10.0, (), (), 4.0)
    lines = pattern_lines("flame", open_area, 2, 50.0)
    # Whole lines across the square, in order along X, never touching.
    whole = sorted(
        (line for line in lines if _length(line) > 250.0), key=lambda line: line[0].x
    )
    assert len(whole) > 10
    for first, second in zip(whole, whole[1:], strict=False):
        assert min(b.x for b in second) - max(a.x for a in first) > -8.0
        assert all(b.x - a.x > 4.0 for a, b in zip(first, second, strict=False))


def test_the_body_takes_any_pattern() -> None:
    for pattern in ENGRAVING_PATTERNS:
        body = (
            replace(
                Prototype001Parameters(),
                body_engraving=True,
                body_engraving_pattern=pattern,
            )
            .build()
            .body
        )
        assert body.engraving is not None and body.engraving.lines


def test_the_web_form_offers_the_patterns() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    pattern = fields["body_engraving_pattern"]
    assert pattern["type"] == "choice" and not pattern["advanced"]
    assert pattern["options"] == list(ENGRAVING_PATTERNS)
    assert pattern["labels"]["evh_stripes"].startswith("EVH stripes")
