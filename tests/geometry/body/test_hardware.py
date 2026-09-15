"""Tests for routed body cavities and bridge hardware."""

from typing import Callable

import pytest

from cncguitarwizard.geometry.body import (
    BridgeMounting,
    CircularCavity,
    DrilledHole,
    JackHole,
    RearCavity,
    RectangularCavity,
    TracedCavity,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D


def test_rectangular_cavity_bounds_match_its_center_and_size() -> None:
    cavity = RectangularCavity("Test cavity", 100.0, -20.0, 40.0, 60.0, 10.0)

    assert cavity.min_x == pytest.approx(80.0)
    assert cavity.max_x == pytest.approx(120.0)
    assert cavity.min_y == pytest.approx(-50.0)
    assert cavity.max_y == pytest.approx(10.0)
    assert len(cavity.outline) > 4


def test_rectangular_cavity_with_zero_radius_is_a_plain_rectangle() -> None:
    cavity = RectangularCavity(
        "Test cavity", 0.0, 0.0, 10.0, 20.0, 5.0, corner_radius=0.0
    )

    assert len(cavity.outline) == 4


@pytest.mark.parametrize(
    "make_invalid_cavity",
    [
        lambda: RectangularCavity("Test", 0.0, 0.0, 0.0, 10.0, 5.0),
        lambda: RectangularCavity("Test", 0.0, 0.0, -10.0, 10.0, 5.0),
        lambda: RectangularCavity("Test", 0.0, 0.0, 10.0, 10.0, 0.0),
        lambda: RectangularCavity("Test", 0.0, 0.0, 10.0, 10.0, 5.0, corner_radius=6.0),
        lambda: RectangularCavity("Test", float("nan"), 0.0, 10.0, 10.0, 5.0),
    ],
)
def test_rectangular_cavity_rejects_invalid_dimensions(
    make_invalid_cavity: Callable[[], RectangularCavity],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_cavity()


def test_circular_cavity_bounds_match_its_center_and_diameter() -> None:
    cavity = CircularCavity("Control cavity", 100.0, -20.0, 56.0, 20.0)

    assert cavity.min_x == pytest.approx(72.0)
    assert cavity.max_x == pytest.approx(128.0)
    assert cavity.min_y == pytest.approx(-48.0)
    assert cavity.max_y == pytest.approx(8.0)
    assert len(cavity.outline) == 32


@pytest.mark.parametrize(
    "make_invalid_cavity",
    [
        lambda: CircularCavity("Test", 0.0, 0.0, 0.0, 10.0),
        lambda: CircularCavity("Test", 0.0, 0.0, -10.0, 10.0),
        lambda: CircularCavity("Test", 0.0, 0.0, 10.0, 0.0),
        lambda: CircularCavity("Test", float("nan"), 0.0, 10.0, 10.0),
    ],
)
def test_circular_cavity_rejects_invalid_dimensions(
    make_invalid_cavity: Callable[[], CircularCavity],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_cavity()


def test_bridge_mounting_pivot_holes_straddle_the_reference_line() -> None:
    bridge = BridgeMounting(600.0, pivot_stud_spacing=80.0)

    left, right = bridge.pivot_holes
    assert left.x == pytest.approx(600.0)
    assert right.x == pytest.approx(600.0)
    assert left.y == pytest.approx(-40.0)
    assert right.y == pytest.approx(40.0)


def test_bridge_mounting_has_no_pivot_holes_for_a_flat_mount_bridge() -> None:
    bridge = BridgeMounting(600.0, pivot_stud_spacing=None)

    assert bridge.pivot_holes == ()


def test_rear_cavity_exposes_its_cavity_name_and_depth() -> None:
    rear = RearCavity(
        CircularCavity("Control cavity", 457.0, 70.0, 44.0, 36.0),
        CircularCavity("Control cavity cover recess", 458.0, 70.0, 59.0, 2.0),
    )

    assert rear.name == "Control cavity"
    assert rear.depth == 36.0


def test_rear_cavity_rejects_a_cover_recess_as_deep_as_the_cavity() -> None:
    with pytest.raises(BodyGeometryError, match="shallower"):
        RearCavity(
            CircularCavity("Control cavity", 457.0, 70.0, 44.0, 2.0),
            CircularCavity("Control cavity cover recess", 457.0, 70.0, 59.0, 2.0),
        )


def test_rear_cavity_rejects_a_cover_recess_that_does_not_enclose_it() -> None:
    with pytest.raises(BodyGeometryError, match="enclose"):
        RearCavity(
            CircularCavity("Control cavity", 457.0, 70.0, 44.0, 36.0),
            CircularCavity("Control cavity cover recess", 480.0, 70.0, 50.0, 2.0),
        )


def test_bridge_mounting_can_omit_the_sustain_block_cavity() -> None:
    bridge = BridgeMounting(600.0, has_sustain_block=False)

    assert bridge.sustain_block_cavity is None


def test_bridge_mounting_builds_its_sustain_block_cavity() -> None:
    bridge = BridgeMounting(600.0, sustain_block_offset=25.0, sustain_block_length=40.0)

    assert bridge.sustain_block_cavity.center_x == pytest.approx(625.0)
    assert bridge.sustain_block_cavity.center_y == pytest.approx(0.0)
    assert bridge.sustain_block_cavity.length_x == pytest.approx(40.0)


@pytest.mark.parametrize(
    "make_invalid_bridge",
    [
        lambda: BridgeMounting(600.0, pivot_stud_spacing=0.0),
        lambda: BridgeMounting(600.0, sustain_block_depth=-1.0),
        lambda: BridgeMounting(float("nan")),
    ],
)
def test_bridge_mounting_rejects_invalid_dimensions(
    make_invalid_bridge: Callable[[], BridgeMounting],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_bridge()


def test_drilled_hole_exposes_its_centre() -> None:
    hole = DrilledHole("Pot 1 shaft hole", 642.0, 86.0, 10.0, 44.0)

    assert hole.center == Point2D(642.0, 86.0)


@pytest.mark.parametrize(
    "make_invalid_hole",
    [
        lambda: DrilledHole("Hole", 642.0, 86.0, 0.0, 44.0),
        lambda: DrilledHole("Hole", 642.0, 86.0, 10.0, -1.0),
        lambda: DrilledHole("Hole", float("nan"), 86.0, 10.0, 44.0),
    ],
)
def test_drilled_hole_rejects_invalid_dimensions(
    make_invalid_hole: Callable[[], DrilledHole],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_hole()


def test_jack_hole_accepts_valid_dimensions() -> None:
    jack = JackHole(700.0, -140.0, 200.0, diameter=12.5, depth=30.0)

    assert jack.diameter == 12.5
    assert jack.depth == 30.0


@pytest.mark.parametrize(
    "make_invalid_jack",
    [
        lambda: JackHole(700.0, -140.0, 200.0, diameter=0.0),
        lambda: JackHole(700.0, -140.0, 200.0, depth=-1.0),
        lambda: JackHole(float("nan"), -140.0, 200.0),
    ],
)
def test_jack_hole_rejects_invalid_dimensions(
    make_invalid_jack: Callable[[], JackHole],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_jack()


def test_traced_cavity_bounds_match_its_points() -> None:
    cavity = TracedCavity(
        "Test cavity",
        (Point2D(10.0, -5.0), Point2D(20.0, -5.0), Point2D(15.0, 8.0)),
        12.0,
    )

    assert cavity.min_x == 10.0
    assert cavity.max_x == 20.0
    assert cavity.min_y == -5.0
    assert cavity.max_y == 8.0


@pytest.mark.parametrize(
    "make_invalid_cavity",
    [
        lambda: TracedCavity("Test", (Point2D(0.0, 0.0), Point2D(1.0, 0.0)), 10.0),
        lambda: TracedCavity(
            "Test",
            (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(float("nan"), 1.0)),
            10.0,
        ),
        lambda: TracedCavity(
            "Test",
            (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)),
            0.0,
        ),
    ],
)
def test_traced_cavity_rejects_invalid_dimensions(
    make_invalid_cavity: Callable[[], TracedCavity],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_cavity()


def test_bridge_mounting_accepts_a_traced_sustain_block_override() -> None:
    traced = TracedCavity(
        "Sustain-block relief",
        (Point2D(600.0, -10.0), Point2D(650.0, -10.0), Point2D(625.0, 30.0)),
        32.0,
    )

    bridge = BridgeMounting(609.6, sustain_block_cavity_override=traced)

    assert bridge.sustain_block_cavity is traced
