"""Tests for the order a part's NC programs run in: the cut that frees it
always last, whatever else the design asks for."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    MachiningParameters,
    plan_body_machining,
    plan_fretboard_machining,
    plan_neck_machining,
)
from cncguitarwizard.cam.neck import NeckMachiningParameters
from cncguitarwizard.presets import Prototype001Parameters

DESIGNS = {
    "plain": Prototype001Parameters(),
    "edges and belly cut": replace(
        Prototype001Parameters(),
        body_top_edge_radius=6.0,
        body_back_edge_radius=6.0,
        body_belly_cut_depth=10.0,
    ),
    "hardtail, locking nut": replace(Prototype001Parameters(), locking_nut="r2"),
}


@pytest.mark.parametrize("design", list(DESIGNS), ids=list(DESIGNS))
def test_the_cut_that_frees_a_part_runs_last(design: str) -> None:
    # Regression: the body's back programs (electronics, small holes, the
    # edges' ball nose) ran after its outline was cut through, the body
    # held only by its tabs.
    geometry = DESIGNS[design].build()
    machining = MachiningParameters()
    plans = {
        "body": plan_body_machining(geometry.body, machining),
        "neck": plan_neck_machining(geometry, NeckMachiningParameters(), machining),
        "fretboard": plan_fretboard_machining(geometry, FretboardMachiningParameters()),
    }

    for part, plan in plans.items():
        tabbed = [
            index
            for index, setup in enumerate(plan.setups)
            if any("with tabs" in path.name for path in setup.toolpaths)
        ]
        assert tabbed == [len(plan.setups) - 1], (part, [s.name for s in plan.setups])
