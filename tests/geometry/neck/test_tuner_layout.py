"""Tests for symmetric 3+3 tuner-hole placement."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import HeadstockGeometryError
from cncguitarwizard.geometry.neck import HeadstockPlan, TunerLayout


def make_headstock() -> HeadstockPlan:
    """Return the locked Prototype001 headstock plan."""
    return HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0)


def test_layout_creates_three_ten_millimetre_holes_per_side() -> None:
    layout = TunerLayout(make_headstock())
    bass_holes = tuple(hole for hole in layout.holes if hole.side == "bass")
    treble_holes = tuple(hole for hole in layout.holes if hole.side == "treble")

    assert len(bass_holes) == len(treble_holes) == 3
    assert all(hole.diameter == 10.0 for hole in layout.holes)


def test_layout_is_symmetric_about_the_headstock_centerline() -> None:
    layout = TunerLayout(make_headstock())
    bass_holes = layout.holes[:3]
    treble_holes = layout.holes[3:]

    for bass, treble in zip(bass_holes, treble_holes, strict=True):
        assert bass.index == treble.index
        assert bass.center.x == pytest.approx(treble.center.x)
        assert bass.center.y == pytest.approx(-treble.center.y)


def test_layout_uses_locked_station_positions() -> None:
    layout = TunerLayout(make_headstock())

    assert tuple(-hole.center.x for hole in layout.holes[:3]) == (
        60.0,
        95.0,
        130.0,
    )
    assert tuple(hole.center.y for hole in layout.holes[:3]) == (
        21.0,
        18.0,
        15.0,
    )


def test_layout_is_immutable() -> None:
    layout = TunerLayout(make_headstock())

    with pytest.raises(FrozenInstanceError):
        layout.hole_diameter = 9.0


@pytest.mark.parametrize(
    "create_layout",
    [
        lambda: TunerLayout(make_headstock(), hole_diameter=0.0),
        lambda: TunerLayout(
            make_headstock(),
            station_distances=(60.0, 130.0, 95.0),
        ),
        lambda: TunerLayout(
            make_headstock(),
            station_distances=(60.0, 95.0, 145.0),
        ),
        lambda: TunerLayout(
            make_headstock(),
            side_offsets=(25.0, 18.0, 15.0),
        ),
        lambda: TunerLayout(
            make_headstock(),
            station_distances=(60.0, 70.0, 130.0),
        ),
        lambda: TunerLayout(make_headstock(), minimum_edge_clearance=-1.0),
    ],
)
def test_layout_rejects_clearance_violations(
    create_layout: Callable[[], TunerLayout],
) -> None:
    with pytest.raises(HeadstockGeometryError):
        create_layout()
