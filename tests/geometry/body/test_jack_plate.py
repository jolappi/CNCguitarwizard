"""Tests for the Les Paul style jack plate on the body's side."""

import re
from dataclasses import replace

import pytest

from cncguitarwizard.cam import MachiningParameters, plan_cover_machining
from cncguitarwizard.geometry.body import les_paul_jack_plate
from cncguitarwizard.geometry.body.jack_plate import JACK_PLATE_SIZE
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.render.dxf import render_covers_dxf, render_plan_dxf


def les_paul() -> Prototype001Parameters:
    values = STYLES["les_paul"].prototype_values("electric_guitar")
    return replace(Prototype001Parameters.for_instrument("electric_guitar"), **values)


def test_the_plate_is_gibsons_square_with_four_screws_round_the_jack() -> None:
    plate = les_paul_jack_plate(2.0, 44.0)

    assert plate.face == "side" and not plate.recessed and plate.thickness == 2.0
    xs = [point.x for point in plate.outline]
    ys = [point.y for point in plate.outline]
    assert max(xs) - min(xs) == pytest.approx(34.13)
    assert max(ys) - min(ys) == pytest.approx(34.13)
    # Rounded corners: no point reaches the square's corner.
    assert all(abs(p.x) + abs(p.y) < JACK_PLATE_SIZE - 1.0 for p in plate.outline)
    jack, *screws = plate.holes
    assert (jack.center.x, jack.center.y, jack.diameter) == (0.0, 0.0, 9.52)
    # On a 1 in square, at its corners.
    assert sorted((s.center.x, s.center.y) for s in screws) == [
        (-12.7, -12.7),
        (-12.7, 12.7),
        (12.7, -12.7),
        (12.7, 12.7),
    ]


def test_a_side_lower_than_the_plate_is_refused() -> None:
    with pytest.raises(BodyGeometryError, match="does not fit"):
        les_paul_jack_plate(2.0, 30.0)


def test_the_les_paul_style_has_one_cut_from_sheet() -> None:
    parameters = les_paul()
    geometry = parameters.build()

    assert parameters.body_jack == "side" and parameters.body_jack_plate
    plates = [cover for cover in geometry.covers if cover.name == "Jack plate"]
    assert len(plates) == 1 and plates[0].thickness == 2.0
    plan = plan_cover_machining(geometry.covers, MachiningParameters())
    assert plan is not None
    setup = next(s for s in plan.setups if s.name == "Cover_jack_plate")
    assert any("body's side over the jack's bore" in note for note in setup.notes)
    # Laid out with the covers for cutting; not in the plan, seen from
    # above: its five holes are not among the covers' there.
    assert "Jack plate (2 mm)" in (render_covers_dxf(geometry.covers) or "")
    drawn = re.findall(r"CIRCLE\n\s*8\nCOVER_HOLES\n", render_plan_dxf(geometry))
    above = [cover for cover in geometry.covers if cover.face != "side"]
    assert len(drawn) == sum(len(cover.holes) for cover in above)


def test_only_a_side_jack_takes_the_plate() -> None:
    cup = replace(les_paul(), body_jack="cup").build()
    off = replace(les_paul(), body_jack_plate=False).build()
    plain = Prototype001Parameters().build()

    for geometry in (cup, off, plain):
        assert "Jack plate" not in [cover.name for cover in geometry.covers]
