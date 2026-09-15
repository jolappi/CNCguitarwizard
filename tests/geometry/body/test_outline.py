"""Tests for the parametric double-cutaway body outline."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.body import BodyOutline
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon


def make_outline(**overrides: object) -> BodyOutline:
    """Return the Prototype001-sized body outline for tests."""
    defaults: dict[str, object] = {
        "scale_length": 609.6,
        "neck_pocket_start": 407.2,
        "neck_pocket_half_width": 28.0,
    }
    defaults.update(overrides)
    return BodyOutline(**defaults)  # type: ignore[arg-type]


def _self_intersections(points: tuple) -> int:
    def ccw(a, b, c) -> bool:
        return (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)

    def crosses(p1, p2, p3, p4) -> bool:
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(
            p1, p2, p4
        )

    count = len(points)
    total = 0
    for i in range(count):
        a1, a2 = points[i], points[(i + 1) % count]
        for j in range(i + 1, count):
            b1, b2 = points[j], points[(j + 1) % count]
            if len({a1, a2, b1, b2}) < 4:
                continue
            if crosses(a1, a2, b1, b2):
                total += 1
    return total


def test_outline_is_a_closed_simple_polygon() -> None:
    outline = make_outline()

    assert _self_intersections(outline.points) == 0


def test_neck_pocket_region_is_solid_full_width() -> None:
    from cncguitarwizard.geometry.primitives import Point2D

    outline = make_outline()

    assert point_in_polygon(Point2D(430.0, 0.0), outline.points)
    assert point_in_polygon(Point2D(430.0, 20.0), outline.points)
    assert point_in_polygon(Point2D(420.0, -25.0), outline.points)


def test_horn_tip_region_leaves_a_gap_for_the_neck() -> None:
    from cncguitarwizard.geometry.primitives import Point2D

    outline = make_outline()

    # Between the two horn tips and the pocket, the centerline itself is
    # where the neck runs — only each horn's own wing (well off-centre)
    # is solid there.
    assert not point_in_polygon(Point2D(350.0, 0.0), outline.points)
    assert not point_in_polygon(Point2D(350.0, 20.0), outline.points)


def test_tail_position_follows_scale_length_and_extension() -> None:
    outline = make_outline(scale_length=650.0, tail_extension=100.0)

    assert outline.tail_position == pytest.approx(750.0)


def test_outline_is_immutable() -> None:
    outline = make_outline()

    with pytest.raises(FrozenInstanceError):
        outline.tail_extension = 200.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "make_invalid_outline",
    [
        lambda: make_outline(tail_extension=0.0),
        lambda: make_outline(treble_horn_tip_half_width=-1.0),
        lambda: make_outline(horn_tip_radius=-5.0),
        lambda: make_outline(treble_horn_tip_half_width=1.0),
        lambda: make_outline(bass_horn_tip_half_width=1.0),
        lambda: make_outline(treble_horn_tip_position=500.0),
        lambda: make_outline(bass_shoulder_position=200.0),
        lambda: make_outline(tail_extension=float("nan")),
    ],
)
def test_outline_rejects_invalid_parameters(
    make_invalid_outline: Callable[[], BodyOutline],
) -> None:
    with pytest.raises(BodyGeometryError):
        make_invalid_outline()
