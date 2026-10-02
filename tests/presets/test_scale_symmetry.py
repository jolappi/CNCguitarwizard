"""The 12th fret sits halfway: nut to 12th fret equals 12th fret to saddles.

Every bridge is placed from the scale line, where its saddles sit (at the
middle of their intonation travel), and the nut's front face, where the
strings break, stands on the nut line at X = 0 — a locking nut's too.
"""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body.bridges import (
    FloydRoseSpec,
    HardtailSpec,
    HeadlessBridgeSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
)
from cncguitarwizard.presets import Prototype001Parameters


def _saddle_line(parameters: Prototype001Parameters) -> float:
    """Return the X of the bridge's saddles, from its mounting."""
    bridge = parameters.body_bridge
    reference = parameters.body_layout().bridge_mounting.reference_x
    if isinstance(bridge, FloydRoseSpec):
        # The mounting is the pivot studs' line, ahead of the saddles.
        return reference - bridge.pivot_offset
    if isinstance(bridge, TuneOMaticSpec):
        # The posts sit their compensation behind the saddles' line.
        return reference - bridge.compensation
    return reference


@pytest.mark.parametrize(
    "bridge",
    [
        KahlerBridgeSpec(),
        FloydRoseSpec(),
        TuneOMaticSpec(),
        HardtailSpec(),
        HeadlessBridgeSpec(),
    ],
)
@pytest.mark.parametrize("scale_length", [609.6, 628.65, 647.7])
def test_the_12th_fret_is_as_far_from_the_nut_as_from_the_saddles(
    bridge: object, scale_length: float
) -> None:
    parameters = replace(
        Prototype001Parameters(), scale_length=scale_length, body_bridge=bridge
    )
    geometry = parameters.build()
    twelfth = geometry.fret_layout.slots[11].start.x
    nut = 0.0  # the nut line, a locking nut's front face included

    assert twelfth - nut == pytest.approx(scale_length / 2.0, abs=0.01)
    if parameters.neck_angle_degrees == 0.0:
        assert _saddle_line(parameters) - twelfth == pytest.approx(
            twelfth - nut, abs=0.01
        )
    else:
        # A tilted neck (a Tune-o-matic's): measured along the strings'
        # tilted line, over the fret tops, from where the nut and the 12th
        # fret lie on the body to the saddles.
        height = parameters.fretboard_thickness + parameters.fret_height
        nut_point = parameters.neck_to_body(nut, height)
        twelfth_point = parameters.neck_to_body(twelfth, height)
        saddle_x = _saddle_line(parameters)
        saddle_z = parameters.neck_to_body(parameters.centre_scale, height)[1]
        assert math.dist(twelfth_point, (saddle_x, saddle_z)) == pytest.approx(
            math.dist(nut_point, twelfth_point), abs=0.01
        )
    if isinstance(bridge, FloydRoseSpec):
        assert geometry.locking_nut is not None


def test_a_bass_keeps_the_12th_fret_halfway_too() -> None:
    parameters = Prototype001Parameters.for_instrument("bass_guitar")
    geometry = parameters.build()
    twelfth = geometry.fret_layout.slots[11].start.x

    assert twelfth == pytest.approx(parameters.scale_length / 2.0, abs=0.01)
    assert _saddle_line(parameters) - twelfth == pytest.approx(twelfth, abs=0.01)
