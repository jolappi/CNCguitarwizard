"""Tests for the volute carved into the headstock's back behind the nut."""

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import (
    Volute,
    default_volute_lines,
    drawn_volute_line,
    side_share,
)
from cncguitarwizard.geometry.neck.volute import _fall


def test_it_is_fullest_behind_the_nut_its_point_on_the_neck() -> None:
    volute = Volute(4.0, 30.0, 21.0)

    # Fullest down the middle 9 mm behind the nut, in the headstock.
    assert volute.fullest == pytest.approx(-9.0)
    assert volute.extra(-9.0, 0.0) == pytest.approx(4.0)
    # Its point 10 mm onto the neck; rising from it to the fullest.
    assert volute.point == pytest.approx(10.0)
    assert volute.extra(10.0, 0.0) == 0.0
    assert 0.0 < volute.extra(5.0, 0.0) < volute.extra(0.0, 0.0) < 4.0
    # Fading into the headstock's back 30 mm behind the nut.
    assert 0.0 < volute.extra(-25.0, 0.0) < volute.extra(-15.0, 0.0) < 4.0
    assert volute.extra(-30.0, 0.0) == 0.0
    assert volute.extra(20.0, 0.0) == 0.0 and volute.extra(-40.0, 0.0) == 0.0


def test_seen_from_behind_its_nose_is_a_rounded_arrow_onto_the_neck() -> None:
    volute = Volute(4.0, 30.0, 21.0)

    # Halfway from its fullest to its point its sides have curved in to
    # 0.8 of the neck's width, and its tip is round, not a sharp point.
    halfway = (volute.fullest + volute.point) / 2.0
    side = 21.0 * (1.0 - 0.5**1.5) ** 0.5
    assert volute.extra(halfway, side - 0.1) > 0.0
    assert volute.extra(halfway, side + 0.1) == 0.0
    near_tip = volute.point - 0.5
    assert volute.extra(near_tip, 2.0) > 0.0
    # The neck's whole width from its fullest into the headstock.
    assert volute.extra(-9.0, 20.9) > 0.0 and volute.extra(-20.0, 20.9) > 0.0
    assert volute.extra(-9.0, 21.0) == 0.0
    # A rounded crest down the middle, its faces falling away either side.
    crest = volute.extra(-9.0, 0.0)
    assert crest > volute.extra(-9.0, 6.0) > volute.extra(-9.0, 12.0) > 0.0
    assert volute.extra(-9.0, 6.0) == volute.extra(-9.0, -6.0)
    # No ridge across it where the nose meets the rest: as full either
    # side of its fullest.
    assert volute.extra(-8.9, 5.0) == pytest.approx(volute.extra(-9.1, 5.0), abs=0.01)


@pytest.mark.parametrize(
    "depth, length, half_width",
    [(0.0, 30.0, 21.0), (4.0, -1.0, 21.0), (4.0, 30.0, 0.0)],
)
def test_a_volute_that_cannot_be_carved_is_refused(
    depth: float, length: float, half_width: float
) -> None:
    with pytest.raises(NeckGeometryError, match="volute"):
        Volute(depth, length, half_width)


def drawn(half_width: float = 21.0) -> Volute:
    lines = default_volute_lines(half_width)
    return Volute(
        3.0,
        30.0,
        half_width,
        *(drawn_volute_line(lines[name]) for name in ("crest", "headstock", "neck")),
    )


def test_a_drawn_volute_falls_from_its_crest_to_both_its_ends() -> None:
    volute = drawn()

    # Its height on the crest, 7 mm onto the neck down the middle.
    assert volute.extra(7.0, 0.0) == pytest.approx(3.0)
    # Falling to where it ends: 30 mm into the headstock, 22.5 mm onto the
    # neck down the middle; nothing past them.
    toward_headstock = [volute.extra(x, 0.0) for x in (0.0, -10.0, -20.0, -28.0)]
    assert toward_headstock == sorted(toward_headstock, reverse=True)
    assert toward_headstock[-1] > 0.0
    assert volute.extra(-30.5, 0.0) == 0.0 and volute.extra(-40.0, 0.0) == 0.0
    assert 0.0 < volute.extra(20.0, 0.0) < volute.extra(15.0, 0.0) < 3.0
    assert volute.extra(23.0, 0.0) == 0.0 and volute.extra(40.0, 0.0) == 0.0
    # Mirrored either side of the centre line.
    assert volute.extra(-10.0, 8.0) == pytest.approx(volute.extra(-10.0, -8.0))


def test_its_crest_is_sharp_its_ends_level_a_log_between() -> None:
    volute = drawn()
    step = 0.05

    # An edge on the crest: steep down either side of it.
    crest = volute.extra(7.0, 0.0)
    assert crest - volute.extra(7.0 + step, 0.0) > 0.01
    assert crest - volute.extra(7.0 - step, 0.0) > 0.01
    # Level where it ends: hardly anything a millimetre before the end.
    assert volute.extra(21.5, 0.0) < 0.01 and volute.extra(-29.0, 0.0) < 0.01
    # A logarithmic fall: two thirds of its height gone a third of the way.
    assert _fall(0.1) == pytest.approx(0.686, abs=1e-3)
    assert _fall(1.0 / 3.0) < 1.0 / 3.0 and _fall(0.0) == 1.0


def test_its_sides_come_down_evenly_to_the_face() -> None:
    # All its wood down the middle, half where the back is half as deep,
    # none at the edges, level with the face.
    assert side_share(15.0, 15.0) == 1.0
    assert side_share(7.5, 15.0) == pytest.approx(0.5)
    assert side_share(0.0, 15.0) == 0.0
    # Never more than all of it, nor any with no back below the face.
    assert side_share(20.0, 15.0) == 1.0
    assert side_share(1.0, 0.0) == 0.0
