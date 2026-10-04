"""Tests for the set (glued) neck."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.body import TuneOMaticSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import parameter_schema

SET = replace(Prototype001Parameters(), neck_joint="set")


def test_a_set_neck_is_glued_into_a_tight_pocket() -> None:
    geometry = SET.build()
    bolted = Prototype001Parameters().build()
    assert geometry.set_neck and not bolted.set_neck
    # No bolts, no ferrules.
    assert not geometry.body.rear_holes and bolted.body.rear_holes
    # The pocket set_neck_glue_gap a side round the heel, not the bolt-on
    # clearance.
    heel = geometry.neck_outline.heel_width / 2.0
    pocket = geometry.body.neck_pocket
    assert pocket is not None
    assert max(p.y for p in pocket.outline) == pytest.approx(heel + 0.05)
    bolted_pocket = bolted.body.neck_pocket
    assert bolted_pocket is not None
    assert max(p.y for p in bolted_pocket.outline) == pytest.approx(heel + 0.15)
    notes = " ".join(plan_neck_machining(geometry, NeckMachiningParameters()).top.notes)
    assert "glue its heel into the body's pocket" in notes


def test_a_set_neck_takes_an_angle_but_no_buried_adjuster() -> None:
    angled = replace(SET, body_bridge=TuneOMaticSpec(), neck_angle=4.0).build()
    assert angled.neck_tilt[0] == 4.0
    with pytest.raises(NeckGeometryError, match="buries a heel adjuster"):
        replace(SET, truss_rod_spoke_wheel="no").build()
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert "set" in fields["neck_joint"]["options"]
    assert fields["set_neck_glue_gap"]["default"] == 0.05
