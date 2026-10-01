"""Tests for the output jack: on the edge, into the controls, its housings."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import JACK_CAVITY_OVERRUN


def _along(jack, distance):  # type: ignore[no-untyped-def]
    import math

    radians = math.radians(jack.direction_degrees)
    return Point2D(
        jack.start_x + distance * math.cos(radians),
        jack.start_y + distance * math.sin(radians),
    )


@pytest.mark.parametrize("key", list(YOUR_DESIGN_TEMPLATES))
def test_the_jack_starts_on_the_edge_and_runs_into_the_controls(key: str) -> None:
    shape = YOUR_DESIGN_TEMPLATES[key][1]
    body = replace(Prototype001Parameters(), body_shape=shape).build().body
    jack = body.jack_hole
    outline = body.outline.points

    # Just inside the edge it is in the body, just outside it is not.
    assert point_in_polygon(_along(jack, 0.5), outline)
    assert not point_in_polygon(_along(jack, -0.5), outline)
    # It ends JACK_CAVITY_OVERRUN past the control cavity's wall.
    cavity = body.control_cavity.cavity.outline
    assert point_in_polygon(_along(jack, jack.depth), cavity)
    assert not point_in_polygon(
        _along(jack, jack.depth - JACK_CAVITY_OVERRUN - 0.5), cavity
    )


def test_a_cup_jack_gets_its_counterbore() -> None:
    geometry = replace(Prototype001Parameters(), body_jack="cup").build()
    jack = geometry.body.jack_hole

    assert (jack.cup_diameter, jack.cup_depth) == (22.2, 25.0)
    assert jack.depth > jack.cup_depth
    assert "jack cup cut" in FreeCADScriptExporter().render_prototype001(geometry)


def test_a_strat_jack_is_a_cavity_from_the_top() -> None:
    body = replace(Prototype001Parameters(), body_jack="strat").build().body
    (cavity,) = [c for c in body.top_cavities if c.name == "Jack cavity"]
    jack = body.jack_hole

    # The bore runs on from the cavity's centre into the controls.
    xs = [p.x for p in cavity.outline]
    ys = [p.y for p in cavity.outline]
    assert (jack.start_x, jack.start_y) == pytest.approx(
        ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0), abs=0.01
    )
    assert max(xs) - min(xs) == pytest.approx(25.4, abs=0.1)
    assert all(point_in_polygon(p, body.outline.points) for p in cavity.outline)


def test_a_fixed_depth_overrides_the_reach_and_a_bad_jack_is_refused() -> None:
    fixed = replace(Prototype001Parameters(), body_jack_depth=30.0).build()
    assert fixed.body.jack_hole.depth == 30.0
    with pytest.raises(BodyGeometryError, match="Unknown jack"):
        replace(Prototype001Parameters(), body_jack="banana").build()  # type: ignore[arg-type]
