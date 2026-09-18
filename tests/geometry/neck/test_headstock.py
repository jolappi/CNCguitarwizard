"""Tests for tapered headstock reference geometry."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import HeadstockGeometryError
from cncguitarwizard.geometry.neck import (
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
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


def test_plan_side_boundary_uses_smooth_sampled_curves() -> None:
    plan = make_plan()

    assert len(plan.boundary) == 34
    assert plan.width_at_distance(0.0) == pytest.approx(42.0)
    assert plan.width_at_distance(30.0) == pytest.approx(65.0)
    assert plan.width_at_distance(150.0) == pytest.approx(40.0)


def test_eight_degree_reference_calculates_tip_drop() -> None:
    reference = HeadstockAngleReference(150.0, 8.0)

    assert reference.tip_drop == pytest.approx(21.081, abs=0.001)
    assert reference.reference_line.start.x == 0.0
    assert reference.reference_line.end.x == -150.0
    assert reference.reference_line.end.y == pytest.approx(-reference.tip_drop)


def test_headstock_solid_uses_sixteen_millimetre_default() -> None:
    solid = HeadstockSolid(
        make_plan(),
        HeadstockAngleReference(150.0, 8.0),
    )

    assert solid.thickness == 16.0
    assert solid.top_boundary[0].z == pytest.approx(0.0)
    assert min(point.z for point in solid.top_boundary) == pytest.approx(
        -21.081,
        abs=0.001,
    )
    vector_length = (
        solid.extrusion_vector.x**2
        + solid.extrusion_vector.y**2
        + solid.extrusion_vector.z**2
    ) ** 0.5
    assert vector_length == pytest.approx(16.0)


@pytest.mark.parametrize("thickness", [14.0, 15.0, 16.0])
def test_headstock_solid_accepts_supported_thicknesses(
    thickness: float,
) -> None:
    solid = HeadstockSolid(
        make_plan(),
        HeadstockAngleReference(150.0, 8.0),
        thickness,
    )

    assert solid.thickness == thickness


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
        lambda: HeadstockPlan(150.0, 42.0, 30.0, 65.0, -40.0),
        lambda: HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0, 1),
        lambda: HeadstockAngleReference(0.0, 8.0),
        lambda: HeadstockAngleReference(150.0, 0.0),
        lambda: HeadstockAngleReference(150.0, 90.0),
        lambda: HeadstockSolid(
            make_plan(),
            HeadstockAngleReference(149.0, 8.0),
        ),
        lambda: HeadstockSolid(
            make_plan(),
            HeadstockAngleReference(150.0, 8.0),
            13.9,
        ),
        lambda: HeadstockSolid(
            make_plan(),
            HeadstockAngleReference(150.0, 8.0),
            16.1,
        ),
    ],
)
def test_headstock_rejects_invalid_dimensions(
    create_geometry: Callable[
        [], HeadstockPlan | HeadstockAngleReference | HeadstockSolid
    ],
) -> None:
    with pytest.raises(HeadstockGeometryError):
        create_geometry()
