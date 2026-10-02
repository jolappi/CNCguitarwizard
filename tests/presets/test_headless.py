"""Tests for headless guitars and basses: no headstock, tuners at the bridge."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.body import HeadlessBridgeSpec
from cncguitarwizard.geometry.exceptions import BodyGeometryError, NeckGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import headstock_editor_layout


@pytest.mark.parametrize(
    ("instrument", "strings"), [("headless_guitar", 6), ("headless_bass", 4)]
)
def test_a_headless_instrument_has_a_headpiece_and_no_tuners(
    instrument: str, strings: int
) -> None:
    parameters = Prototype001Parameters.for_instrument(instrument)  # type: ignore[arg-type]
    geometry = parameters.build()

    assert parameters.headless and parameters.string_count == strings
    # A flat headpiece, as wide as the nut, headless_length long.
    plan = geometry.headstock.plan
    assert plan.length == parameters.headless_length
    assert plan.shoulder_width == plan.tip_width == parameters.nut_width
    assert geometry.headstock.angle.angle_degrees == 0.0
    assert geometry.tuner_layout.holes == ()
    # The tuners are at the bridge.
    bridge = parameters.body_bridge
    assert isinstance(bridge, HeadlessBridgeSpec)
    assert bridge.string_count == strings


def test_the_headless_bridge_is_a_screwed_plate_on_the_top() -> None:
    spec = HeadlessBridgeSpec()
    hardware = spec.hardware(609.6, 44.0)

    screws = [h for h in hardware.holes if h.name.startswith("Bridge screw")]
    assert len(screws) == 4 and not hardware.top_cavities
    xs = [p.x for p in hardware.footprint]
    ys = [p.y for p in hardware.footprint]
    assert min(xs) == pytest.approx(609.6 - spec.front_reach)
    assert max(xs) - min(xs) == pytest.approx(spec.length)
    assert max(ys) == pytest.approx(5 * 10.5 / 2 + spec.side_margin)
    assert all(point_in_polygon(h.center, hardware.footprint) for h in screws)
    assert hardware.mounting.reference_x == 609.6


def test_the_headless_bridges_strings_must_match_the_instrument() -> None:
    with pytest.raises(BodyGeometryError, match="headless bridge has 6 strings"):
        replace(
            Prototype001Parameters.for_instrument("headless_bass"),
            body_bridge=HeadlessBridgeSpec(),
        ).build()


def test_the_bridge_humbucker_clears_the_headless_plate() -> None:
    layout = Prototype001Parameters.for_instrument("headless_guitar").body_layout()
    assert layout.bridge_pickup is not None
    pickup_end = max(p.x for p in layout.bridge_pickup.outline)
    assert pickup_end < min(p.x for p in layout.bridge_footprint) - 5.0


def test_a_headpiece_too_short_is_refused() -> None:
    with pytest.raises(NeckGeometryError, match="headless_length"):
        replace(
            Prototype001Parameters.for_instrument("headless_guitar"),
            headless_length=10.0,
        ).build()


def test_the_cam_freecad_and_editor_handle_a_headless_neck() -> None:
    geometry = Prototype001Parameters.for_instrument("headless_guitar").build()

    plan = plan_neck_machining(geometry, NeckMachiningParameters())
    assert all(
        "Tuner" not in path.name for setup in plan.setups for path in setup.toolpaths
    )
    script = FreeCADScriptExporter().render_prototype001(geometry)
    assert "NeckBack" in script
    editor = headstock_editor_layout(
        {"prototype": {"instrument": "headless_guitar", "headless": True}}
    )
    assert editor["holes"] == []
