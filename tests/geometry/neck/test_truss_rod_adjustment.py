"""Tests for the truss rod's adjusting end: nut pocket, access and cover."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.exceptions import (
    NeckGeometryError,
    TrussRodGeometryError,
)
from cncguitarwizard.presets import Prototype001Parameters

HEEL = Prototype001Parameters()
HEADSTOCK = replace(HEEL, truss_rod_adjustment="headstock")


def test_a_heel_adjusted_rod_steps_down_to_its_adjuster_at_the_heel() -> None:
    geometry = HEEL.build()
    truss = geometry.truss_rod_channel
    heel_end = (
        geometry.neck_outline.last_fret_position + geometry.neck_outline.heel_length
    )

    assert truss.adjustment_side == "heel"
    step, pocket = truss.pockets
    spans = [
        (min(p.x for p in part.boundary), max(p.x for p in part.boundary))
        for part in (step, pocket)
    ]
    widths = [max(p.y for p in part.boundary) * 2.0 for part in (step, pocket)]
    assert truss.channel_start + truss.channel_length == pytest.approx(spans[0][0])
    assert spans[0][1] - spans[0][0] == pytest.approx(14.0)
    assert spans[1] == (pytest.approx(spans[0][1]), pytest.approx(heel_end - 12.0))
    assert widths == [pytest.approx(7.5), pytest.approx(9.0)]
    assert (step.depth, pocket.depth) == (10.5, 11.0)
    # The sleeve's 12 mm bore on the rod's axis, 7.5 mm below the glue face
    # (as measured on the rod), is drilled by hand.
    assert truss.bore is not None
    assert (truss.bore.start, truss.bore.end) == (
        pytest.approx(heel_end - 12.0),
        pytest.approx(heel_end),
    )
    assert (truss.bore.diameter, truss.bore.axis_depth) == (9.0, 7.5)
    assert truss.adjuster_boundary == ()
    # The 15 mm head, 0.5 mm clear below it.
    assert truss.adjuster_depth == pytest.approx(7.5 + 7.5 + 0.5)
    # Left at 0 the axis is half the pocket's width above its floor.
    derived = replace(HEEL, truss_rod_axis_depth=0.0).build().truss_rod_channel
    assert derived.axis_depth == pytest.approx(11.0 - 4.5)
    with pytest.raises(TrussRodGeometryError, match="break out of the neck"):
        replace(HEEL, truss_rod_axis_depth=4.0).build()


def test_the_body_gets_a_notch_for_the_adjusters_head() -> None:
    body = HEEL.build().body
    access = body.truss_rod_access
    assert access is not None
    heel_end = body.neck_pocket.max_x

    assert access.name == "Truss rod access"
    assert (access.min_x, access.max_x) == (
        pytest.approx(heel_end - 3.0),
        pytest.approx(heel_end + 6.0 + 2.0),
    )
    assert access.max_y == pytest.approx(7.5 + 1.0)
    assert access.depth == pytest.approx(15.5)
    assert access in body.top_cavities
    assert (
        replace(HEEL, truss_rod_nut_diameter=0.0).build().body.truss_rod_access is None
    )


def test_the_rod_fits_every_neck_length() -> None:
    for instrument in ("seven_string_guitar", "bass_guitar"):
        geometry = Prototype001Parameters.for_instrument(instrument).build()
        outline = geometry.neck_outline
        heel_end = outline.last_fret_position + outline.heel_length
        assert geometry.truss_rod_channel.end_position == pytest.approx(heel_end - 12.0)
    with pytest.raises(TrussRodGeometryError, match="short of its adjuster"):
        replace(HEEL, truss_rod_length=400.0).build()


def test_a_headstock_adjusted_rod_runs_under_the_nut_into_a_trough() -> None:
    geometry = HEADSTOCK.build()
    truss = geometry.truss_rod_channel
    xs = [p.x for p in truss.adjuster_boundary]

    assert truss.adjustment_side == "nut"
    assert truss.start_position == pytest.approx(-5.0)
    assert (min(xs), max(xs)) == (pytest.approx(-37.0), pytest.approx(-5.0))
    heel_end = (
        geometry.neck_outline.last_fret_position + geometry.neck_outline.heel_length
    )
    # A 460 mm stock rod: its head in the trough, its anchor end just short
    # of the longest route, 12 mm before the heel end.
    assert truss.end_position == pytest.approx(-5.0 + 460.0 - 6.0)
    assert truss.end_position <= heel_end - 12.0
    # No access notch in the body.
    assert geometry.body.truss_rod_access is None
    (cover,) = [c for c in geometry.covers if c.name == "Truss rod cover"]
    assert cover.face == "top" and len(cover.holes) == 3
    assert max(p.x for p in cover.outline) < -5.0
    assert min(p.x for p in cover.outline) < min(xs)
    without = replace(HEADSTOCK, truss_rod_cover=False).build()
    assert all(c.name != "Truss rod cover" for c in without.covers)


def test_the_trough_keeps_clear_of_the_tuners() -> None:
    with pytest.raises(NeckGeometryError, match="too close to tuner"):
        replace(HEADSTOCK, truss_rod_access_length=48.0).build()


def test_the_neck_program_cuts_the_steps_and_trough_and_notes_the_bore() -> None:
    heel = plan_neck_machining(HEEL.build(), NeckMachiningParameters())
    paths = {path.name: path for path in heel.top.toolpaths}
    assert min(m.z for m in paths["Truss-rod channel"].moves) == pytest.approx(-7.5)
    assert min(m.z for m in paths["Truss-rod step"].moves) == pytest.approx(-10.5)
    assert min(m.z for m in paths["Truss-rod pocket"].moves) == pytest.approx(-11.0)
    assert any("sleeve bore by hand" in note for note in heel.top.notes)
    head = plan_neck_machining(HEADSTOCK.build(), NeckMachiningParameters())
    paths = {path.name: path for path in head.top.toolpaths}
    assert min(m.z for m in paths["Truss-rod access trough"].moves) == pytest.approx(
        -15.5
    )
    assert not any("sleeve bore" in note for note in head.top.notes)


def test_the_sleeve_bore_can_be_left_out() -> None:
    geometry = replace(HEEL, truss_rod_sleeve_bore=False).build()

    assert geometry.truss_rod_channel.bore is None
    # The head still needs its notch in the body.
    assert geometry.body.truss_rod_access is not None
    notes = " ".join(plan_neck_machining(geometry, NeckMachiningParameters()).top.notes)
    assert "sleeve bore" not in notes


def test_the_headstock_trough_and_its_cover_can_be_left_out() -> None:
    geometry = replace(HEADSTOCK, truss_rod_trough=False).build()

    assert geometry.truss_rod_channel.adjuster_boundary == ()
    assert all(cover.name != "Truss rod cover" for cover in geometry.covers)
    names = [
        path.name
        for path in plan_neck_machining(
            geometry, NeckMachiningParameters()
        ).top.toolpaths
    ]
    assert "Truss-rod access trough" not in names
    assert "Truss-rod access trough" in [
        path.name
        for path in plan_neck_machining(
            HEADSTOCK.build(), NeckMachiningParameters()
        ).top.toolpaths
    ]


def test_a_route_under_the_nut_asks_for_a_filler_before_the_nut_is_glued() -> None:
    # Routed from the top, a headstock-adjusted rod's pocket opens the
    # middle of the nut seat: the neck's notes ask for a filler over it.
    def filler_notes(parameters: Prototype001Parameters) -> list[str]:
        notes = plan_neck_machining(parameters.build(), NeckMachiningParameters())
        return [note for note in notes.top.notes if "filler" in note]

    (note,) = filler_notes(HEADSTOCK)
    assert "9 mm wide and 5 mm long" in note
    # At the heel the route starts well past the nut: the seat is whole.
    assert filler_notes(HEEL) == []
