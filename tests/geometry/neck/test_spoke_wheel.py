"""Tests for the truss rod's adjuster with and without a spoke wheel."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import TELECASTER_NECK
from cncguitarwizard.webapp import parameter_schema


def build(**values: object):  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), **values).build()  # type: ignore[arg-type]


def heel_end(geometry) -> float:  # type: ignore[no-untyped-def]
    outline = geometry.truss_rod_channel.neck_outline
    return outline.last_fret_position + outline.heel_length


def test_auto_fits_a_wheel_at_the_heel_and_none_at_the_headstock() -> None:
    parameters = Prototype001Parameters()
    assert parameters.truss_rod_spoke_wheel_fitted
    assert not replace(
        parameters, truss_rod_adjustment="headstock"
    ).truss_rod_spoke_wheel_fitted


def test_the_heel_wheel_turns_past_the_heel_end_in_a_body_notch() -> None:
    geometry = build()
    channel = geometry.truss_rod_channel
    assert channel.end_position == pytest.approx(heel_end(geometry) - 12.0)
    assert channel.bore is not None
    assert geometry.body.truss_rod_access is not None


def test_without_a_wheel_the_heel_adjuster_sits_at_the_heel_end() -> None:
    geometry = build(truss_rod_spoke_wheel="no")
    channel = geometry.truss_rod_channel
    # The route runs out through the heel's end: no bore, no body notch.
    assert channel.end_position == pytest.approx(heel_end(geometry))
    assert channel.bore is None
    assert geometry.body.truss_rod_access is None
    notes = " ".join(plan_neck_machining(geometry, NeckMachiningParameters()).top.notes)
    assert "adjuster nut sits at the heel's end face" in notes
    assert "sleeve bore" not in notes


def test_a_headstock_wheel_sits_in_an_open_trough() -> None:
    geometry = build(
        **{
            **TELECASTER_NECK,
            "truss_rod_adjustment": "headstock",
            "truss_rod_spoke_wheel": "yes",
        }
    )
    trough = geometry.truss_rod_channel.adjuster_boundary
    # Behind the board's end, the wheel's length + 4 mm, its width + 2 mm.
    assert max(p.x for p in trough) == pytest.approx(-9.5)
    assert min(p.x for p in trough) == pytest.approx(-19.5)
    assert 2.0 * max(p.y for p in trough) == pytest.approx(17.0)
    assert all(cover.name != "Truss rod cover" for cover in geometry.covers)


def test_a_slotted_nut_without_a_wheel_gets_a_key_notch() -> None:
    geometry = build(nut_style="slot", truss_rod_adjustment="headstock")
    channel = geometry.truss_rod_channel
    trough = channel.adjuster_boundary
    # Only the open start of the key's hole, behind the board's end.
    assert max(p.x for p in trough) == pytest.approx(-9.5)
    assert min(p.x for p in trough) == pytest.approx(-17.5)
    assert 2.0 * max(p.y for p in trough) == pytest.approx(8.0)
    assert channel.adjuster_depth == pytest.approx(channel.axis_depth + 4.0)
    assert all(cover.name != "Truss rod cover" for cover in geometry.covers)
    notes = " ".join(plan_neck_machining(geometry, NeckMachiningParameters()).top.notes)
    assert "8 mm notch behind the nut" in notes


def test_a_shelf_nut_without_a_wheel_gets_a_covered_key_notch() -> None:
    geometry = build(truss_rod_adjustment="headstock")
    trough = geometry.truss_rod_channel.adjuster_boundary
    assert (min(p.x for p in trough), max(p.x for p in trough)) == (
        pytest.approx(-13.0),
        pytest.approx(-5.0),
    )
    assert 2.0 * max(p.y for p in trough) == pytest.approx(8.0)
    assert any(cover.name == "Truss rod cover" for cover in geometry.covers)


def test_a_headstock_wheel_must_not_break_through_an_angled_root() -> None:
    with pytest.raises(NeckGeometryError, match="break through"):
        build(truss_rod_adjustment="headstock", truss_rod_spoke_wheel="yes")
    # A flat headstock is set down: its root is deep enough.
    build(
        truss_rod_adjustment="headstock",
        truss_rod_spoke_wheel="yes",
        headstock_angle=0.0,
    )


def test_the_web_form_offers_the_spoke_wheel() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    wheel = fields["truss_rod_spoke_wheel"]
    assert wheel["type"] == "choice" and not wheel["advanced"]
    assert wheel["options"] == ["auto", "yes", "no"]
