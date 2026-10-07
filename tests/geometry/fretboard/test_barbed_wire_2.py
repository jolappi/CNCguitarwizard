"""Tests for the ``barbed_wire_2`` marker: a barbed-wire knot traced from a
drawing, one piece at every marker fret."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import FretboardMachiningParameters
from cncguitarwizard.cam.inlays import inlay_fit_outline, plan_inlay_machining
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.fretboard.barbed_wire_2 import (
    BARBED_WIRE_2_ALONG,
    BARBED_WIRE_2_EDITOR_OUTLINE,
    BARBED_WIRE_2_OUTLINE,
)
from cncguitarwizard.geometry.fretboard.inlay_layout import (
    BARBED_WIRE_2_FRET_CLEARANCE,
    BARBED_WIRE_2_SPAN,
)
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters

KNOT = replace(Prototype001Parameters(), inlay_style="barbed_wire_2")


def _area(outline: tuple[Point2D, ...]) -> float:
    return 0.5 * sum(
        a.x * b.y - b.x * a.y for a, b in zip(outline, (*outline[1:], outline[0]))
    )


def _crossing(outline: tuple[Point2D, ...]) -> bool:
    def turn(a: Point2D, b: Point2D, c: Point2D) -> float:
        return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)

    count = len(outline)
    for i in range(count):
        a, b = outline[i], outline[(i + 1) % count]
        for j in range(i + 2, count):
            if i == 0 and j == count - 1:
                continue
            c, d = outline[j], outline[(j + 1) % count]
            if (turn(a, b, c) > 0) != (turn(a, b, d) > 0) and (turn(c, d, a) > 0) != (
                turn(c, d, b) > 0
            ):
                return True
    return False


def test_the_traced_knot_is_one_simple_piece() -> None:
    for outline in (BARBED_WIRE_2_OUTLINE, BARBED_WIRE_2_EDITOR_OUTLINE):
        points = tuple(Point2D(along, across) for along, across in outline)
        assert _area(points) > 0.0
        assert not _crossing(points)
    acrosses = [across for _, across in BARBED_WIRE_2_OUTLINE]
    assert (min(acrosses), max(acrosses)) == (-1.0, 1.0)
    assert max(abs(along) for along, _ in BARBED_WIRE_2_OUTLINE) == BARBED_WIRE_2_ALONG


def test_every_marker_fret_gets_one_knot_across_the_board() -> None:
    layout = KNOT.build().inlay_layout
    # One each at the double-marker frets too: 3 ... 21, 12 and 24.
    assert [marker.fret_number for marker in layout.markers] == [
        3, 5, 7, 9, 12, 15, 17, 19, 21, 24,
    ]  # fmt: skip
    surface = KNOT.fretboard_surface()
    frets = {
        fret.number: fret.distance_from_nut
        for fret in FretCalculator.calculate(surface.scale_length, surface.fret_count)
    }

    def half_width_at(position: float) -> float:
        taper = (surface.last_fret_width - surface.nut_width) * position / frets[24]
        return (surface.nut_width + taper) / 2.0

    third = layout.markers[0]
    ys = [point.y for point in third.outline]
    # BARBED_WIRE_2_SPAN of the board's width there, centred.
    assert max(ys) - min(ys) == pytest.approx(
        2.0 * BARBED_WIRE_2_SPAN * half_width_at(third.position), rel=0.01
    )
    assert max(ys) + min(ys) == pytest.approx(0.0, abs=0.01)
    # In the short last fret spaces the knot is drawn smaller, its barbs
    # BARBED_WIRE_2_FRET_CLEARANCE from the frets either side.
    for marker in layout.markers:
        xs = [point.x for point in marker.outline]
        front, back = frets[marker.fret_number - 1], frets[marker.fret_number]
        assert min(xs) >= front + BARBED_WIRE_2_FRET_CLEARANCE - 1e-6
        assert max(xs) <= back - BARBED_WIRE_2_FRET_CLEARANCE + 1e-6
    last = layout.markers[-1]
    ys = [point.y for point in last.outline]
    assert max(ys) - min(ys) < 2.0 * BARBED_WIRE_2_SPAN * half_width_at(last.position)


def test_a_left_handed_knot_is_the_mirror_image() -> None:
    right = KNOT.build().inlay_layout.markers[0].outline
    left = replace(KNOT, handedness="left").build().inlay_layout.markers[0].outline
    assert _area(left) > 0.0
    assert sorted((round(p.x, 6), round(-p.y, 6)) for p in right) == sorted(
        (round(p.x, 6), round(p.y, 6)) for p in left
    )


@pytest.mark.parametrize(
    "instrument", ["electric_guitar", "seven_string_guitar", "bass_guitar"]
)
def test_a_1_mm_end_mill_cuts_each_knot_whole(instrument: str) -> None:
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument), inlay_style="barbed_wire_2"
    )
    layout = parameters.build().inlay_layout
    for marker in layout.markers:
        fitted = inlay_fit_outline(marker.outline, 0.5)
        # One piece, barely smaller: only the barbs' tips and the slits
        # narrower than the tool are lost.
        assert not _crossing(fitted)
        assert _area(fitted) == pytest.approx(_area(marker.outline), rel=0.15)
    pieces = plan_inlay_machining(layout, FretboardMachiningParameters())
    assert pieces is not None


def test_the_inlay_editor_starts_from_the_knots_corners() -> None:
    layout = KNOT.build().inlay_layout
    points = layout.editable_points()
    assert len(points) == len(BARBED_WIRE_2_EDITOR_OUTLINE)
    # Drawn on as a custom marker, it builds.
    custom = replace(KNOT, inlay_style="custom", inlay_points=points)
    assert len(custom.build().inlay_layout.markers) == 10


def test_the_original_barbed_wire_is_kept() -> None:
    layout = Prototype001Parameters().build().inlay_layout
    assert layout.style == "barbed_wire"
    assert len(layout.markers) == 12
    assert BARBED_WIRE_2_FRET_CLEARANCE == 1.5
