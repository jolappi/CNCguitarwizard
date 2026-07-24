"""Tests for tapered headstock reference geometry."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import HeadstockGeometryError
from cncguitarwizard.geometry.neck import (
    HeadstockAngleReference,
    HeadstockPlan,
)


def make_plan() -> HeadstockPlan:
    """Return the locked Prototype001 headstock plan."""
    return HeadstockPlan(
        length=150.0,
        nut_width=42.0,
        shoulder_distance=30.0,
        shoulder_width=65.0,
        tip_width=40.0,
    )


def test_plan_uses_locked_widths_and_length() -> None:
    plan = make_plan()

    assert plan.nut_line.length == pytest.approx(42.0)
    assert plan.shoulder_line.length == pytest.approx(65.0)
    assert plan.tip_line.length == pytest.approx(40.0)
    assert plan.tip_line.start.x == plan.tip_line.end.x == -150.0


def test_plan_is_symmetric_about_its_centerline() -> None:
    plan = make_plan()

    for line in (plan.nut_line, plan.shoulder_line, plan.tip_line):
        assert line.start.x == pytest.approx(line.end.x)
        assert line.start.y == pytest.approx(-line.end.y)


def test_eight_degree_reference_calculates_tip_drop() -> None:
    reference = HeadstockAngleReference(150.0, 8.0)

    assert reference.tip_drop == pytest.approx(21.081, abs=0.001)
    assert reference.reference_line.start.x == 0.0
    assert reference.reference_line.end.x == -150.0
    assert reference.reference_line.end.y == pytest.approx(-reference.tip_drop)


def test_headstock_geometry_is_immutable() -> None:
    plan = make_plan()

    with pytest.raises(FrozenInstanceError):
        plan.tip_width = 45.0


@pytest.mark.parametrize(
    "create_geometry",
    [
        lambda: HeadstockPlan(0.0, 42.0, 30.0, 65.0, 40.0),
        lambda: HeadstockPlan(150.0, 42.0, 150.0, 65.0, 40.0),
        lambda: HeadstockPlan(150.0, 66.0, 30.0, 65.0, 40.0),
        lambda: HeadstockPlan(150.0, 42.0, 30.0, 65.0, 65.0),
        lambda: HeadstockAngleReference(0.0, 8.0),
        lambda: HeadstockAngleReference(150.0, 0.0),
        lambda: HeadstockAngleReference(150.0, 90.0),
    ],
)
def test_headstock_rejects_invalid_dimensions(
    create_geometry: Callable[[], HeadstockPlan | HeadstockAngleReference],
) -> None:
    with pytest.raises(HeadstockGeometryError):
        create_geometry()
