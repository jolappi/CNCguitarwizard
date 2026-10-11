"""Tests for the vintage truss rod laid in from the neck's back."""

import math

import pytest

from cncguitarwizard.geometry.exceptions import TrussRodGeometryError
from cncguitarwizard.geometry.neck import NeckOutline, TrussRodChannel, VintageTrussRod
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon

ROD = VintageTrussRod(-9.5, 470.0, 6.0, 4.76, 4.0, 2.5, 11.0, 30.0)


def test_the_rod_lies_deeper_in_the_middle_than_at_its_ends() -> None:
    middle = (ROD.start + ROD.end) / 2.0

    assert ROD.axis_depth(ROD.start) == pytest.approx(4.0)
    assert ROD.axis_depth(ROD.end) == pytest.approx(4.0)
    assert ROD.axis_depth(middle) == pytest.approx(6.5)
    # Beyond its ends it keeps its ends' depth.
    assert ROD.axis_depth(ROD.end + 10.0) == pytest.approx(4.0)
    # The channel reaches the rod's side nearest the fretboard; the walnut
    # starts at its side nearest the back.
    assert ROD.ceiling_depth(middle) == pytest.approx(6.5 - 2.38)
    assert ROD.strip_depth(middle) == pytest.approx(6.5 + 2.38)


def test_the_plug_is_a_teardrop_over_the_anchor_and_the_strip_runs_on() -> None:
    plug = ROD.plug_outline

    xs = [point.x for point in plug]
    ys = [point.y for point in plug]
    assert min(xs) == pytest.approx(ROD.start)
    assert max(xs) == pytest.approx(ROD.strip_start)
    assert max(ys) == pytest.approx(5.5)
    assert min(ys) == pytest.approx(-5.5)
    # Counter-clockwise and convex: every turn to the left.
    for a, b, c in zip(plug, (*plug[1:], plug[0]), (*plug[2:], *plug[:2])):
        assert (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x) > 0.0
    # Narrowed to the channel at its end, where the strip starts.
    assert {(round(p.x, 6), round(abs(p.y), 6)) for p in plug if p.x == max(xs)} == {
        (round(ROD.strip_start, 6), 3.0)
    }
    assert ROD.strip_outline[0].x == pytest.approx(ROD.strip_start)
    assert max(p.x for p in ROD.strip_outline) == pytest.approx(ROD.end)
    assert point_in_polygon(Point2D(ROD.start + 5.5, 0.0), plug)
    # Its floor at the rod's back side where that lies deepest under it.
    assert ROD.plug_depth == pytest.approx(ROD.strip_depth(ROD.strip_start))
    assert all(
        ROD.strip_depth(ROD.start + ROD.plug_length * k / 10) <= ROD.plug_depth + 1e-9
        for k in range(11)
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"width": math.nan}, "finite and positive"),
        ({"bow": -1.0}, "bow"),
        ({"end": -20.0}, "end past its start"),
        ({"rod_diameter": 6.0}, "narrower than its channel"),
        ({"plug_width": 5.0}, "wider than its channel"),
        ({"plug_length": 10.0}, "longer than it is wide"),
        ({"end": 15.0}, "shorter than the rod"),
        ({"end_depth": 2.0}, "below the neck's top"),
    ],
)
def test_a_rod_that_cannot_be_laid_in_is_refused(
    changes: dict[str, float], message: str
) -> None:
    values = {
        "start": -9.5,
        "end": 470.0,
        "width": 6.0,
        "rod_diameter": 4.76,
        "end_depth": 4.0,
        "bow": 2.5,
        "plug_width": 11.0,
        "plug_length": 30.0,
    } | changes
    with pytest.raises(TrussRodGeometryError, match=message):
        VintageTrussRod(**values)


def test_a_channel_laid_in_from_the_back_may_start_in_the_headstock() -> None:
    outline = NeckOutline(647.7, 22, 42.0, 56.0, 56.0, 4.0)

    def channel(routed_from: str) -> TrussRodChannel:
        return TrussRodChannel(
            outline,
            -9.5,
            470.0,
            6.0,
            6.4,
            adjustment_side="heel",
            routed_from=routed_from,  # type: ignore[arg-type]
        )

    assert channel("back").start_position == -9.5
    # One routed from the top starts on the nut's shelf at the earliest.
    with pytest.raises(TrussRodGeometryError, match="nut shelf"):
        channel("top")
    with pytest.raises(TrussRodGeometryError, match="top or the back"):
        channel("side")
