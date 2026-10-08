"""Tests for the engraving's other patterns: EVH stripes, flame, ripples, crackle,
and the camo relief."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import EngravedPocket, Engraving
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.engraving import (
    CAMO_GAP,
    CAMO_KEEP,
    CAMO_LEVELS,
    CAMO_SMALLEST,
    ENGRAVING_PATTERNS,
    MIN_PATTERN_LINE,
    ROW_STEP,
    STRIPE_WIDTHS,
    EngravingArea,
    engraving_lines,
    pattern_lines,
    pattern_pockets,
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


def _bounds(points: tuple[Point2D, ...]) -> tuple[float, float, float, float]:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def test_camo_is_a_relief_of_closed_shapes_at_four_levels() -> None:
    open_area = EngravingArea(_square(260.0), 10.0, (), (), 4.0)
    shapes = pattern_pockets("camo", open_area, 3, 50.0, 2.0)
    assert pattern_lines("camo", open_area, 3, 50.0) == ()
    assert len(shapes) > 25
    assert shapes == pattern_pockets("camo", open_area, 3, 50.0, 2.0)
    assert shapes != pattern_pockets("camo", open_area, 4, 50.0, 2.0)
    # Every level of the four, 0.5 mm apart down to the depth.
    assert {shape.depth for shape in shapes} == {0.5, 1.0, 1.5, 2.0}
    assert CAMO_LEVELS == 4
    inside = _square(260.0 - 2 * 10.0 + 2 * ROW_STEP)
    boxes = [_bounds(shape.outline) for shape in shapes]
    overlapping = 0
    for index, shape in enumerate(shapes):
        assert all(point_in_polygon(p, inside) for p in shape.outline)
        # Lobed and armed, not round: dented in two places at least.
        outline = shape.outline
        bends = [
            (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x) < 0.0
            for a, b, c in zip(
                (outline[-1], *outline[:-1]),
                outline,
                (*outline[1:], outline[0]),
                strict=True,
            )
        ]
        dents = sum(1 for k, bend in enumerate(bends) if bend and not bends[k - 1])
        assert dents >= 2
        # The smallest no smaller than a round about CAMO_SMALLEST across.
        area = 0.5 * abs(
            sum(
                a.x * b.y - b.x * a.y
                for a, b in zip(outline, (*outline[1:], outline[0]), strict=True)
            )
        )
        assert area > math.pi * (CAMO_SMALLEST * 0.9) ** 2
        if shape.within is not None:
            # Wholly inside a shallower one, cut on from its floor.
            parent = shapes[shape.within]
            assert parent.depth < shape.depth
            assert all(point_in_polygon(p, parent.outline) for p in outline)
        x0, y0, x1, y1 = boxes[index]
        for other, (u0, v0, u1, v1) in zip(shapes[:index], boxes[:index], strict=True):
            if u0 > x1 + 5 or x0 > u1 + 5 or v0 > y1 + 5 or y0 > v1 + 5:
                continue
            overlap = any(
                point_in_polygon(p, other.outline) for p in outline[::2]
            ) or any(point_in_polygon(p, outline) for p in other.outline[::2])
            if overlap and other.depth != shape.depth:
                # Levels lie over one another: the deeper shows.
                overlapping += 1
                continue
            # One level's shapes never merge, nor do two side by side leave
            # a thin wall between them.
            assert not overlap
            gap = min(
                math.dist((a.x, a.y), (b.x, b.y))
                for a in outline[::3]
                for b in other.outline[::3]
            )
            assert gap > CAMO_GAP - 1.5
    assert overlapping > 10
    # Each still shows, about CAMO_KEEP of its outline out from under the
    # deeper ones over it.
    for shape in shapes:
        deeper = [other for other in shapes if other.depth > shape.depth]
        points = shape.outline[::3]
        shown = sum(
            1
            for p in points
            if not any(point_in_polygon(p, other.outline) for other in deeper)
        )
        assert shown >= (CAMO_KEEP - 0.1) * len(points)


def test_camo_lies_over_a_level_face_only() -> None:
    # A step down across the middle: no shape crosses it, those beyond it
    # lie that much lower.
    stepped = EngravingArea(
        _square(400.0),
        10.0,
        (),
        (),
        4.0,
        lambda point: 1.5 if point.x > 0.0 else 0.0,
    )
    shapes = pattern_pockets("camo", stepped, 3, 50.0, 2.0)
    assert {shape.face_drop for shape in shapes} == {0.0, 1.5}
    for shape in shapes:
        sides = {p.x > 0.0 for p in shape.outline}
        assert len(sides) == 1 and shape.face_drop == (1.5 if True in sides else 0.0)


def test_a_relief_must_be_cut_from_its_parent_down() -> None:
    square = _square(20.0)
    with pytest.raises(BodyGeometryError, match="no deeper than"):
        Engraving((), 2.0, (EngravedPocket(square, 2.5),))
    with pytest.raises(BodyGeometryError, match="after it, deeper"):
        Engraving(
            (),
            2.0,
            (EngravedPocket(square, 1.0), EngravedPocket(square, 0.5, within=0)),
        )
    with pytest.raises(BodyGeometryError, match="three points"):
        Engraving((), 2.0, (EngravedPocket(square[:2], 1.0),))


DRAWN = (((60.0, -60.0), (200.0, -60.0)), ((60.0, 60.0), (120.0, 90.0), (200.0, 60.0)))
"""Two lines drawn on the default body, clear of its pickups."""


def test_the_body_takes_any_pattern() -> None:
    for pattern in ENGRAVING_PATTERNS:
        body = (
            replace(
                Prototype001Parameters(),
                body_engraving=True,
                body_engraving_pattern=pattern,
                body_engraving_lines=DRAWN if pattern == "drawn" else (),
            )
            .build()
            .body
        )
        assert body.engraving is not None
        # Lines, or a relief's shapes.
        assert bool(body.engraving.lines) != bool(body.engraving.pockets)
        assert bool(body.engraving.pockets) == (pattern == "camo")


def test_drawn_lines_are_cut_back_where_the_top_may_not_be_engraved() -> None:
    # One straight line across the square keep-out: cut in two at it (a
    # millimetre at a time, not only at its ends), its clearance kept.
    across = (Point2D(-120.0, 0.0), Point2D(120.0, 0.0))
    circle = [
        Point2D(
            100.0 + 20.0 * math.cos(k * math.pi / 8), 20.0 * math.sin(k * math.pi / 8)
        )
        for k in range(16)
    ]
    ring = (*circle, circle[0])
    lines = pattern_lines("drawn", AREA, 1, 50.0, drawn=(across, ring))
    pieces = [line for line in lines if all(abs(p.y) < 1e-9 for p in line)]
    assert len(pieces) == 2
    assert max(p.x for p in pieces[0]) <= -30.0 - 4.0 + 1e-6
    assert min(p.x for p in pieces[1]) >= 30.0 + 4.0 - 1e-6
    # A closed ring, wholly in the area, stays one closed line.
    (closed,) = [line for line in lines if line not in pieces]
    assert closed[0] == closed[-1]
    assert pattern_lines("drawn", AREA, 1, 50.0) == ()


def test_a_drawn_pattern_needs_its_lines_and_is_mirrored_left_handed() -> None:
    drawn = replace(
        Prototype001Parameters(),
        body_engraving=True,
        body_engraving_pattern="drawn",
        body_engraving_lines=DRAWN,
    )
    right = drawn.body_layout().engraving
    left = replace(drawn, handedness="left").body_layout().engraving
    assert right is not None and left is not None
    assert [[(p.x, -p.y) for p in line] for line in right.lines] == [
        [(p.x, p.y) for p in line] for line in left.lines
    ]
    with pytest.raises(BodyGeometryError, match="drawn engraving has no lines"):
        replace(drawn, body_engraving_lines=()).body_layout()


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
