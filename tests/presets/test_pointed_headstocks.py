"""Tests for the Jackson and ESP Alexi pointed six-in-line headstocks."""

from dataclasses import replace

import pytest

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import (
    ALEXI_NECK,
    JACKSON_NECK,
    NECK_TEMPLATES,
)
from cncguitarwizard.presets.styles import STYLES


@pytest.mark.parametrize(
    ("neck", "reach", "tip_across"),
    [(JACKSON_NECK, 171.2, 84.3), (ALEXI_NECK, 180.5, 34.2)],
)
def test_a_pointed_headstock_points_to_the_treble_side(
    neck: dict[str, object], reach: float, tip_across: float
) -> None:
    parameters = replace(Prototype001Parameters(), **neck)  # type: ignore[arg-type]
    plan, tuners = parameters.headstock_design()
    assert plan.is_drawn and plan.reach == pytest.approx(reach, abs=0.5)
    # Its point well out on the treble side, past the tuners.
    treble = -parameters.bass_sign
    # Each edge's half-width is toward its own side: the bass edge ends
    # past the centreline, the point between the two.
    assert plan.treble_edge[-1][1] == pytest.approx(tip_across, abs=1.5)
    assert -plan.bass_edge[-1][1] == pytest.approx(tip_across, abs=1.5)
    # Six posts in a straight row along the tuner edge, the low E's
    # nearest the nut on the bass side, the last across the centreline.
    holes = sorted(tuners.holes, key=lambda hole: -hole.center.x)
    assert len(holes) == 6
    across = [hole.center.y * treble for hole in holes]
    assert across[0] < -20.0 and across[-1] > 25.0
    steps = [b - a for a, b in zip(across, across[1:], strict=False)]
    assert max(steps) - min(steps) < 0.5
    assert parameters.headstock_angle == 13.0
    parameters.build()


def test_the_rr_and_alexi_styles_take_their_necks_for_six_strings_only() -> None:
    for key, neck in (("jackson_rr", "jackson"), ("alexi_hexed", "alexi")):
        style = STYLES[key]
        assert style.neck == neck
        six = style.prototype_values("electric_guitar")
        for name, value in NECK_TEMPLATES[neck][1].items():
            assert six[name] == value
        # Drawn round six tuners: a seven-string keeps its own headstock.
        seven = style.prototype_values("seven_string_guitar")
        assert "headstock_bass_edge" not in seven


@pytest.mark.parametrize("key", ["jackson_rr", "alexi_hexed"])
def test_a_pointed_neck_through_style_plans_a_laminated_blank(key: str) -> None:
    # Its 13 degree headstock is deeper than the 44 mm body the neck runs
    # through: the style asks for a block glued under it, and its neck is
    # then planned.
    from cncguitarwizard.cam import MachiningParameters
    from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
    from cncguitarwizard.webapp import load_design, style_design

    design = style_design("electric_guitar", key)
    assert design["machining"] == {"neck_blank": "laminated"}
    assert style_design("seven_string_guitar", key)["machining"] == {}
    loaded = load_design(design)
    machining = loaded.machining
    assert machining.neck_blank == "laminated"
    plan_neck_machining(
        loaded.parameters.build(),
        NeckMachiningParameters(blank="laminated"),
        MachiningParameters(),
    )
