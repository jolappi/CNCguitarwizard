"""Tests for the neck angle: a tilted neck pocket floor and the moved bridge."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.cam.body import FLOOR_TERRACE_STEP
from cncguitarwizard.geometry.body import TuneOMaticSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import parameter_schema

FLAT = Prototype001Parameters()
TUNE_O_MATIC = replace(FLAT, body_bridge=TuneOMaticSpec())


def test_a_tune_o_matic_tilts_the_neck_by_default() -> None:
    assert FLAT.neck_angle_degrees == 0.0
    assert TUNE_O_MATIC.neck_angle_degrees == 2.0
    assert replace(TUNE_O_MATIC, neck_angle=0.0).neck_angle_degrees == 0.0
    assert replace(FLAT, neck_angle=1.5).neck_angle_degrees == 1.5
    with pytest.raises(NeckGeometryError, match="neck_angle"):
        replace(FLAT, neck_angle=8.0).build()


def test_the_pocket_floor_sinks_toward_its_mouth() -> None:
    pocket = TUNE_O_MATIC.build().body.neck_pocket
    slope = math.tan(math.radians(2.0))
    assert pocket.floor_slope == pytest.approx(slope)
    # heel_thickness deep at the heel end, deeper at the mouth.
    assert pocket.depth_at(pocket.max_x) == pytest.approx(20.0)
    assert pocket.deepest == pytest.approx(20.0 + slope * (pocket.max_x - pocket.min_x))
    assert FLAT.build().body.neck_pocket.floor_slope == 0.0


def test_the_floor_is_cut_in_thin_terraces() -> None:
    geometry = TUNE_O_MATIC.build()
    pocket = geometry.body.neck_pocket
    plan = plan_body_machining(geometry.body, MachiningParameters())
    paths = [path for setup in plan.setups for path in setup.toolpaths]
    terraces = [path for path in paths if path.name.startswith("Neck pocket floor")]
    assert terraces
    depths = [path.deepest_z() for path in terraces]
    assert depths == pytest.approx(
        [-(20.0 + FLOOR_TERRACE_STEP * k) for k in range(1, len(depths) + 1)]
    )
    # Never below the tilted floor: each terrace stops where it is that deep.
    assert -depths[-1] <= pocket.deepest + 1e-9
    flat = plan_body_machining(FLAT.build().body, MachiningParameters())
    assert not any(
        path.name.startswith("Neck pocket floor")
        for setup in flat.setups
        for path in setup.toolpaths
    )


def test_the_bridge_moves_to_keep_the_scale_along_the_tilted_strings() -> None:
    height = FLAT.fretboard_thickness + FLAT.fret_height
    saddles = TUNE_O_MATIC.bridge_scale_line()
    nut = TUNE_O_MATIC.neck_to_body(0.0, height)
    saddle = TUNE_O_MATIC.neck_to_body(TUNE_O_MATIC.centre_scale, height)
    assert saddles == pytest.approx(saddle[0])
    assert math.dist(nut, saddle) == pytest.approx(TUNE_O_MATIC.centre_scale)
    # About a millimetre toward the nut on the default 24 in scale.
    assert TUNE_O_MATIC.centre_scale - saddles == pytest.approx(1.04, abs=0.01)
    assert FLAT.bridge_scale_line() == FLAT.centre_scale


def test_the_freecad_script_tilts_the_neck_and_the_pocket_floor() -> None:
    tilted = FreeCADScriptExporter().render_prototype001(TUNE_O_MATIC.build())
    flat = FreeCADScriptExporter().render_prototype001(FLAT.build())

    assert "neck pocket angled floor cut" in tilted
    assert "neck_tilt = App.Placement(" in tilted
    assert "App.Rotation(App.Vector(0.0, 1.0, 0.0), -2.0)" in tilted
    assert "neck_tilt" not in flat and "angled floor" not in flat


def test_the_web_form_offers_the_neck_angle() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    angle = fields["neck_angle"]
    assert angle["type"] == "optional_float" and not angle["advanced"]
    assert angle["default"] is None
