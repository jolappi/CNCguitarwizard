"""Tests for the outline of lines drawn with a round pen."""

import math
import os
import subprocess
import sys

import pytest

from cncguitarwizard.geometry.fretboard.runes import (
    RUNE_CELL,
    RUNE_EDITOR_TOLERANCE,
    RUNE_TOLERANCE,
    RUNES,
    rune_outlines,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.geometry.primitives import stroke_outlines as outlines


def area(points: tuple[Point2D, ...]) -> float:
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


def narrowest_gap(outline: tuple[Point2D, ...]) -> float:
    """Return how near a closed outline's sides come where they do not
    meet: none where two cross."""

    def turn(p: Point2D, q: Point2D, r: Point2D) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    def to_segment(p: Point2D, a: Point2D, b: Point2D) -> float:
        ex, ey = b.x - a.x, b.y - a.y
        t = ((p.x - a.x) * ex + (p.y - a.y) * ey) / (ex * ex + ey * ey)
        t = min(1.0, max(0.0, t))
        return math.hypot(a.x + ex * t - p.x, a.y + ey * t - p.y)

    sides = list(zip(outline, (*outline[1:], outline[0]), strict=True))
    gaps = []
    for i, (a, b) in enumerate(sides):
        for j in range(i + 2, len(sides)):
            if i == 0 and j == len(sides) - 1:
                continue  # The last side ends where the first starts.
            c, d = sides[j]
            if (
                turn(a, b, c) * turn(a, b, d) < 0.0
                and turn(c, d, a) * turn(c, d, b) < 0.0
            ):
                return 0.0
            gaps += [
                to_segment(a, c, d),
                to_segment(b, c, d),
                to_segment(c, a, b),
                to_segment(d, a, b),
            ]
    return min(gaps)


def test_one_stroke_is_a_capsule() -> None:
    (capsule,) = outlines([[Point2D(0.0, 0.0), Point2D(10.0, 0.0)]], 1.0, 0.1, 0.005)

    # A 10 x 2 rectangle and two half circles, counter-clockwise.
    assert area(capsule) == pytest.approx(20.0 + math.pi, rel=0.01)
    for point in capsule:
        nearest = math.hypot(max(0.0, point.x - 10.0, -point.x), point.y)
        assert nearest == pytest.approx(1.0, abs=0.02)


def test_strokes_that_cross_merge_and_apart_stay_apart() -> None:
    cross = outlines(
        [
            [Point2D(0.0, 0.0), Point2D(6.0, 10.0)],
            [Point2D(0.0, 10.0), Point2D(6.0, 0.0)],
        ],
        0.6,
        0.05,
        0.005,
    )
    apart = outlines(
        [
            [Point2D(0.0, 0.0), Point2D(0.0, 5.0)],
            [Point2D(3.0, 0.0), Point2D(3.0, 5.0)],
        ],
        0.5,
        0.05,
        0.005,
    )

    assert len(cross) == 1
    assert len(apart) == 2
    assert all(area(outline) > 0.0 for outline in (*cross, *apart))


def test_an_area_closed_in_is_filled() -> None:
    (triangle,) = outlines(
        [[Point2D(0.0, 0.0), Point2D(10.0, 0.0), Point2D(5.0, 8.0), Point2D(0.0, 0.0)]],
        0.5,
        0.05,
        0.005,
    )

    assert point_in_polygon(Point2D(5.0, 3.0), triangle)
    assert area(triangle) > 40.0  # the triangle's own 40, and the stroke round it


@pytest.mark.parametrize(
    ("strokes", "half_width"),
    [([], 1.0), ([[Point2D(0.0, 0.0)]], 1.0), ([[Point2D(0.0, 0.0)] * 2], 0.0)],
)
def test_nothing_to_draw_is_refused(
    strokes: list[list[Point2D]], half_width: float
) -> None:
    with pytest.raises(ValueError):
        outlines(strokes, half_width, 0.1, 0.01)


@pytest.mark.parametrize("tolerance", [RUNE_TOLERANCE, RUNE_EDITOR_TOLERANCE])
@pytest.mark.parametrize("name", list(RUNES))
def test_an_outline_never_comes_near_itself(name: str, tolerance: float) -> None:
    # Regression: the runes are drawn on round numbers, which put grid
    # points on the outline itself; thinned, algiz's sides then touched
    # where its arm leaves the staff, crossed once fitted to a fret space,
    # and FreeCAD's inlay cut failed, the body never built after it.
    for piece in rune_outlines(name, tolerance):
        assert narrowest_gap(piece) > RUNE_CELL / 10.0


def test_the_same_strokes_give_the_same_outlines_in_every_run() -> None:
    # Regression: each loop started wherever a set's order put it, which
    # changes from run to run, so one design gave a different inlay each
    # build (and now and then one that crossed itself).
    script = (
        "from cncguitarwizard.geometry.fretboard.runes import RUNES, rune_outlines\n"
        "print([rune_outlines(name) for name in RUNES])\n"
    )
    runs = [
        subprocess.run(
            [sys.executable, "-c", script],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("1", "2")
    ]

    assert runs[0] == runs[1]
