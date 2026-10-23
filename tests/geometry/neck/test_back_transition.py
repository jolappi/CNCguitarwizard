"""Tests for where the neck's back turns into a flat block, drawn."""

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import (
    DEFAULT_HEEL_LINES,
    BackTransition,
    default_transition_lines,
    drawn_back_line,
)
from cncguitarwizard.geometry.primitives import Point2D


def heel() -> BackTransition:
    """A heel's: the block's flat at 400 down the middle and 410 at the
    sides (rounded toward the nut), the neck's profile from 350."""
    return BackTransition(
        drawn_back_line(((10.0, 0.0), (5.0, 15.0), (0.0, 30.0)), 410.0),
        drawn_back_line(((60.0, 0.0), (60.0, 30.0)), 410.0),
        20.0,
        1.0,
    )


def test_drawn_lines_are_measured_from_their_origin_and_mirrored() -> None:
    line = drawn_back_line(((10.0, 0.0), (0.0, 30.0)), 410.0)

    assert line[0] == Point2D(410.0, -30.0) and line[-1] == Point2D(410.0, 30.0)
    assert Point2D(400.0, 0.0) in line
    with pytest.raises(NeckGeometryError, match="two points"):
        drawn_back_line(((10.0, 0.0),))


def test_the_back_turns_from_the_neck_line_to_the_flat_one() -> None:
    transition = heel()

    # The neck's own on its side of the neck line, the block's past the
    # flat line (further toward the body at the sides, by its rounding).
    assert transition.share(340.0, 0.0) == 0.0
    assert transition.share(350.0, 0.0) == 0.0
    assert transition.share(401.0, 0.0) == 1.0
    assert transition.share(405.0, 25.0) < 1.0 and transition.share(411.0, 25.0) == 1.0
    # Between, evenly: halfway there, half turned, and easing in and out.
    assert transition.share(375.0, 0.0) == pytest.approx(0.5)
    shares = [transition.share(x, 0.0) for x in range(350, 401, 5)]
    assert shares == sorted(shares)
    assert transition.share(351.0, 0.0) < 0.01 and transition.share(399.0, 0.0) > 0.99
    assert transition.span == (350.0, 410.0)


def test_a_transition_that_cannot_be_shaped_is_refused() -> None:
    lines = heel()
    with pytest.raises(NeckGeometryError, match="two points"):
        BackTransition(lines.flat, lines.neck[:1], 20.0, 1.0)
    with pytest.raises(NeckGeometryError, match="depth"):
        BackTransition(lines.flat, lines.neck, 0.0, 1.0)
    with pytest.raises(NeckGeometryError, match="1 or -1"):
        BackTransition(lines.flat, lines.neck, 20.0, 0.5)


def test_drawing_starts_from_the_default_lines_scaled_across() -> None:
    lines = default_transition_lines(DEFAULT_HEEL_LINES, 28.0)

    assert lines["flat"] == ((0.0, 0.0), (0.0, 30.8))
    assert lines["neck"][0] == (60.0, 0.0) and lines["neck"][-1] == (45.0, 30.8)
