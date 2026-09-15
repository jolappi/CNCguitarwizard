"""Tests for tapered fretboard outline geometry."""

from dataclasses import FrozenInstanceError

import pytest

from cncguitarwizard.geometry.fretboard import Fretboard
from cncguitarwizard.geometry.neck import Centerline
from cncguitarwizard.geometry.primitives import Line2D, Point2D


@pytest.fixture
def fretboard() -> Fretboard:
    """Return a standard tapered fretboard."""
    return Fretboard(609.6, 42.0, 63.0, Centerline(609.6))


def test_fretboard_constructs_nut_and_bridge_lines(fretboard: Fretboard) -> None:
    assert fretboard.nut_line == Line2D(Point2D(0.0, 21.0), Point2D(0.0, -21.0))
    assert fretboard.bridge_line == Line2D(
        Point2D(609.6, 31.5),
        Point2D(609.6, -31.5),
    )


def test_fretboard_constructs_left_and_right_edges(fretboard: Fretboard) -> None:
    assert fretboard.left_edge == Line2D(
        Point2D(0.0, 21.0),
        Point2D(609.6, 31.5),
    )
    assert fretboard.right_edge == Line2D(
        Point2D(0.0, -21.0),
        Point2D(609.6, -31.5),
    )


def test_fretboard_outline_contains_the_four_boundary_lines(
    fretboard: Fretboard,
) -> None:
    assert fretboard.outline == (
        fretboard.nut_line,
        fretboard.right_edge,
        fretboard.bridge_line,
        fretboard.left_edge,
    )


def test_fretboard_boundary_lines_match_the_requested_widths(
    fretboard: Fretboard,
) -> None:
    assert fretboard.nut_line.length == 42.0
    assert fretboard.bridge_line.length == 63.0


def test_fretboard_uses_an_eight_millimetre_nut_corner_radius_by_default(
    fretboard: Fretboard,
) -> None:
    assert fretboard.nut_corner_radius == 8.0


def test_fretboard_accepts_a_custom_nut_corner_radius() -> None:
    fretboard = Fretboard(609.6, 42.0, 63.0, Centerline(609.6), 6.0)

    assert fretboard.nut_corner_radius == 6.0


def test_fretboard_is_immutable(fretboard: Fretboard) -> None:
    with pytest.raises(FrozenInstanceError):
        fretboard.nut_width = 43.0
