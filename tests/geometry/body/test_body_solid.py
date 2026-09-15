"""Tests for the complete parametric solid-body assembly."""

import pytest

from cncguitarwizard.geometry.body import (
    BodyOutline,
    BodySolid,
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


def make_body(**cavity_overrides: object) -> BodySolid:
    """Return a Prototype001-sized body assembly for tests."""
    outline = BodyOutline(609.6, 407.2, 28.0)
    cavities: dict[str, object] = {
        "outline": outline,
        "thickness": 44.0,
        "neck_pocket": RectangularCavity(
            "Neck pocket", 434.2, 0.0, 54.0, 56.0, 20.0, corner_radius=2.0
        ),
        "bridge_pickup": RectangularCavity(
            "Bridge pickup route", 570.0, 0.0, 38.1, 88.9, 22.0, corner_radius=6.0
        ),
        "neck_pickup": RectangularCavity(
            "Neck pickup route", 500.0, 0.0, 38.1, 88.9, 22.0, corner_radius=6.0
        ),
        "bridge_mounting": BridgeMounting(609.6),
        "control_cavity": make_rear_cavity("Control cavity", 610.0, 90.0),
        "jack_hole": JackHole(700.0, 140.0, 160.0, diameter=12.5, depth=30.0),
    }
    cavities.update(cavity_overrides)
    return BodySolid(**cavities)  # type: ignore[arg-type]


def make_rear_cavity(
    name: str, center_x: float, center_y: float, depth: float = 30.0
) -> RearCavity:
    """Return a rear-routed rectangular cavity with a 5 mm cover ledge."""
    return RearCavity(
        RectangularCavity(
            name, center_x, center_y, 70.0, 55.0, depth, corner_radius=8.0
        ),
        RectangularCavity(
            f"{name} cover recess",
            center_x,
            center_y,
            80.0,
            65.0,
            2.0,
            corner_radius=8.0,
        ),
    )


def test_body_solid_builds_from_valid_hardware_placements() -> None:
    body = make_body()

    assert body.thickness == 44.0
    assert body.neck_pocket.name == "Neck pocket"
    assert body.rear_cavities == (body.control_cavity,)


def test_body_solid_accepts_a_circular_control_cavity() -> None:
    body = make_body(
        control_cavity=RearCavity(
            CircularCavity("Control cavity", 610.0, 90.0, 44.0, 36.0),
            CircularCavity("Control cavity cover recess", 610.0, 90.0, 59.0, 2.0),
        )
    )

    assert body.control_cavity.cavity.diameter == 44.0


def test_body_solid_accepts_a_rear_switch_cavity() -> None:
    # Shallow enough to leave wood under the sustain-block cavity above it.
    switch = make_rear_cavity("Switch cavity", 680.0, 20.0, 10.0)
    body = make_body(switch_cavity=switch)

    assert body.rear_cavities == (body.control_cavity, switch)


def test_body_solid_accepts_a_bridge_without_a_sustain_block() -> None:
    body = make_body(
        bridge_mounting=BridgeMounting(609.6, has_sustain_block=False),
        # Deep enough that it would collide with the default sustain block.
        switch_cavity=make_rear_cavity("Switch cavity", 680.0, 20.0),
    )

    assert body.bridge_mounting.sustain_block_cavity is None
    assert body.switch_cavity is not None


def test_body_solid_accepts_a_rear_battery_cavity() -> None:
    battery = make_rear_cavity("Battery cavity", 680.0, 20.0, 10.0)
    body = make_body(battery_cavity=battery)

    assert body.rear_cavities == (body.control_cavity, battery)


def test_body_solid_rejects_a_rear_cavity_breaking_into_a_top_cavity() -> None:
    # Directly under the bridge pickup route (22 mm deep): 22 + 30 >= 44.
    with pytest.raises(BodyGeometryError, match="break through"):
        make_body(switch_cavity=make_rear_cavity("Switch cavity", 570.0, 0.0))


def test_body_solid_allows_a_rear_cavity_under_a_shallow_top_cavity() -> None:
    body = make_body(switch_cavity=make_rear_cavity("Switch cavity", 570.0, 0.0, 20.0))

    assert body.switch_cavity is not None


def test_body_solid_rejects_a_cover_recess_outside_the_outline() -> None:
    with pytest.raises(BodyGeometryError, match="cover recess"):
        make_body(
            control_cavity=RearCavity(
                RectangularCavity("Control cavity", 610.0, 90.0, 70.0, 55.0, 30.0),
                RectangularCavity(
                    "Control cavity cover recess", 610.0, 90.0, 400.0, 400.0, 2.0
                ),
            )
        )


def test_body_solid_cuts_extra_traced_cavities() -> None:
    extra = TracedCavity(
        "Bridge baseplate cutout",
        (Point2D(640.0, -20.0), Point2D(660.0, -20.0), Point2D(650.0, 10.0)),
        12.0,
    )

    body = make_body(extra_cavities=(extra,))

    assert body.extra_cavities == (extra,)


def test_body_solid_rejects_an_extra_cavity_outside_the_outline() -> None:
    extra = TracedCavity(
        "Bridge baseplate cutout",
        (Point2D(2000.0, 0.0), Point2D(2010.0, 0.0), Point2D(2005.0, 10.0)),
        12.0,
    )

    with pytest.raises(BodyGeometryError):
        make_body(extra_cavities=(extra,))


def test_body_solid_allows_omitting_the_control_cavity() -> None:
    body = make_body(control_cavity=None)

    assert body.control_cavity is None


def test_body_solid_rejects_a_cavity_deeper_than_the_slab() -> None:
    with pytest.raises(BodyGeometryError):
        make_body(control_cavity=make_rear_cavity("Control cavity", 610.0, -90.0, 50.0))


def test_body_solid_rejects_a_pivot_hole_deeper_than_the_slab() -> None:
    with pytest.raises(BodyGeometryError):
        make_body(bridge_mounting=BridgeMounting(609.6, pivot_hole_depth=50.0))


def test_body_solid_rejects_a_jack_bore_through_the_whole_body() -> None:
    with pytest.raises(BodyGeometryError):
        make_body(
            jack_hole=JackHole(700.0, -140.0, 200.0, diameter=12.5, depth=500.0)
        )


def test_body_solid_rejects_a_cavity_outside_the_outline() -> None:
    with pytest.raises(BodyGeometryError):
        make_body(control_cavity=make_rear_cavity("Control cavity", 610.0, -300.0))


def test_body_solid_allows_a_neck_pocket_opening_onto_the_horn_gap() -> None:
    """A bolt-on pocket's nut-ward end may lie in the gap between the horns."""
    body = make_body(
        neck_pocket=RectangularCavity(
            "Neck pocket", 380.0, 0.0, 80.0, 56.0, 20.0, corner_radius=2.0
        )
    )

    assert body.neck_pocket.min_x == pytest.approx(340.0)


def test_body_solid_rejects_a_neck_pocket_entirely_off_the_body() -> None:
    with pytest.raises(BodyGeometryError, match="tail-ward wall"):
        make_body(
            neck_pocket=RectangularCavity(
                "Neck pocket", 300.0, 0.0, 54.0, 56.0, 20.0, corner_radius=2.0
            )
        )


def test_body_solid_accepts_drilled_holes() -> None:
    hole = DrilledHole("Pot 1 shaft hole", 610.0, 90.0, 10.0, 44.0)
    body = make_body(holes=(hole,))

    assert body.holes == (hole,)


def test_body_solid_rejects_a_hole_deeper_than_the_body() -> None:
    with pytest.raises(BodyGeometryError, match="deeper"):
        make_body(holes=(DrilledHole("Pot 1 shaft hole", 610.0, 90.0, 10.0, 44.1),))


def test_body_solid_rejects_a_hole_outside_the_outline() -> None:
    with pytest.raises(BodyGeometryError, match="outside"):
        make_body(holes=(DrilledHole("Pot 1 shaft hole", 610.0, -300.0, 10.0, 30.0),))


def test_body_solid_rejects_non_positive_thickness() -> None:
    with pytest.raises(BodyGeometryError):
        make_body(thickness=0.0)
